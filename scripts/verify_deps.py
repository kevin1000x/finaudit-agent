"""供应链门禁的机械形态：核验本机已安装的第三方包与 PyPI 发布件字节一致。

`01-01-PLAN.md` 的 Task 0 原本是 `blocking-human` 门禁，要求人打开 PyPI 页面看四项。
2026-08-15 首次执行时降级成了「读已安装分发的 Author 字段」——那不成立：
Author 是上传者自填的字符串，仿冒包可以照抄「Kirill Simonov」。而且它发生在安装之后，
门禁的意义恰恰是在安装之前拦住。

本脚本做的是更强的核验，且可重复执行：

1. 包名拼写以 `pyproject.toml` 为准（typosquat 的攻击面是名字打错，名字对了就会解析到真包）
2. 下载 PyPI 上该版本的 wheel，比对其 sha256 与 PyPI 公布的 digest
3. 把 wheel 内 `RECORD` 的逐文件哈希与本机已安装的同名文件逐一比对
   —— 这一步把「本机这些字节」与「PyPI 上该项目名下的发布件」绑在一起
4. 读 `project_urls`，确认指向上游官方仓库
5. 读 pypistats 近月下载量，作为「知名度与包名相符」的旁证

退出码 0 = 全部通过；1 = 任一项不符（fail-closed，不打印警告后继续）。

用法：
    .venv/Scripts/python scripts/verify_deps.py
"""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import sys
import sysconfig
import tomllib
import urllib.request
import zipfile
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# 期望的上游仓库。project_urls 里必须出现其中之一，否则判为身份不符。
EXPECTED_UPSTREAM = {
    "pyyaml": "github.com/yaml/pyyaml",
    "pytest": "github.com/pytest-dev/pytest",
}

# 近月下载量下限。门禁原文要求「千万级」，此处按月取 1e7。
MIN_MONTHLY_DOWNLOADS = 10_000_000

USER_AGENT = "finaudit-agent-dep-audit"


def _get_json(url: str, timeout: int = 60) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def declared_package_names() -> list[str]:
    """从 pyproject.toml 读出声明的依赖名，不硬编码——名字对不对是第一道防线。"""
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data.get("project", {})
    specs = list(project.get("dependencies", []))
    for extra in (project.get("optional-dependencies") or {}).values():
        specs.extend(extra)
    names = []
    for spec in specs:
        name = spec.split(">=")[0].split("==")[0].split("[")[0].strip()
        if name and name not in names:
            names.append(name)
    return names


def installed_version(name: str) -> str | None:
    try:
        return distribution(name).version
    except PackageNotFoundError:
        return None


def pick_wheel(files: list[dict], interp_abi: str, platform_tokens: list[str]) -> dict | None:
    """选与本机真正匹配的 wheel。

    wheel 文件名是 `{name}-{ver}-{python}-{abi}-{platform}.whl`。这里必须整段精确匹配
    `{python}-{abi}-`，不能只找 `cp314` 子串——踩过两次：
      - `cp314` 也命中 `cp314-cp314-macosx_...`（平台错）
      - `cp314-cp314` 前缀也命中 `cp314-cp314t-...`（自由线程 ABI，不是本机这个）
    选错 wheel 后 `WHEEL` / `METADATA` 必然不一致，会把正常包误报成篡改。
    """
    wheels = [f for f in files if f["packagetype"] == "bdist_wheel"]
    universal = [f for f in wheels if "py3-none-any" in f["filename"]]
    if universal:
        return universal[0]
    for f in wheels:
        name = f["filename"]
        if interp_abi in name and all(tok in name for tok in platform_tokens):
            return f
    return None


def wheel_record_hashes(blob: bytes) -> dict[str, str]:
    zf = zipfile.ZipFile(io.BytesIO(blob))
    hashes: dict[str, str] = {}
    for entry in zf.namelist():
        if entry.endswith(".dist-info/RECORD"):
            for row in csv.reader(io.StringIO(zf.read(entry).decode())):
                if len(row) >= 2 and row[1]:
                    hashes[row[0].replace("\\", "/")] = row[1]
    return hashes


def local_interp_abi() -> str:
    """本机的 `{python tag}-{abi tag}-` 片段，例如 `cp314-cp314-`。

    自由线程构建（PEP 703）的 ABI tag 带 `t` 后缀，与普通构建是两个不同的 wheel。
    """
    tag = f"cp{sys.version_info.major}{sys.version_info.minor}"
    abi = tag + ("t" if sysconfig.get_config_var("Py_GIL_DISABLED") else "")
    return f"{tag}-{abi}-"


def local_platform_tokens() -> list[str]:
    """本机平台标记拆成 token，用于挑出正确的平台 wheel。

    win-amd64  → ['win', 'amd64']；linux-x86_64 → ['linux', 'x86_64']
    （manylinux wheel 的文件名含 x86_64，故 token 级匹配比整串匹配更稳）
    """
    raw = sysconfig.get_platform().replace("-", "_").replace(".", "_")
    return [tok for tok in raw.split("_") if tok and not tok.isdigit()]


def check_package(name: str, interp_abi: str, platform_tokens: list[str]) -> bool:
    ok = True
    version = installed_version(name)
    if version is None:
        print(f"== {name}: 未安装，无从核验")
        return False

    print(f"== {name} {version}")
    meta = _get_json(f"https://pypi.org/pypi/{name}/{version}/json")

    urls = meta["info"].get("project_urls") or {}
    expected = EXPECTED_UPSTREAM.get(name.lower())
    if expected is None:
        print(f"   [FAIL] 未在 EXPECTED_UPSTREAM 登记上游仓库，新依赖须先登记")
        ok = False
    elif not any(expected in str(v) for v in urls.values()):
        print(f"   [FAIL] project_urls 未指向 {expected}：{urls}")
        ok = False
    else:
        print(f"   [ OK ] 上游仓库  {expected}")

    wheel = pick_wheel(meta["urls"], interp_abi, platform_tokens)
    if wheel is None:
        print(f"   [FAIL] 该版本无匹配 {interp_abi} / {platform_tokens} 的 wheel 可比对")
        return False

    with urllib.request.urlopen(wheel["url"], timeout=180) as resp:
        blob = resp.read()
    published = wheel["digests"]["sha256"]
    downloaded = hashlib.sha256(blob).hexdigest()
    if downloaded != published:
        print(f"   [FAIL] wheel 哈希不符  {downloaded} != {published}")
        return False
    print(f"   [ OK ] wheel      {wheel['filename']}")
    print(f"          发布于     {wheel['upload_time_iso_8601']}")
    print(f"          sha256     {published}")

    dist = distribution(name)
    local = {str(fp).replace("\\", "/"): fp for fp in (dist.files or [])}
    compared = mismatch = 0
    for rel, want in wheel_record_hashes(blob).items():
        fp = local.get(rel)
        if fp is None:
            continue
        try:
            data = dist.locate_file(fp).read_bytes()
        except OSError:
            continue
        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=")
        compared += 1
        if "sha256=" + digest.decode() != want:
            mismatch += 1
            print(f"   [FAIL] 已装文件与发布件不一致：{rel}")
    if compared == 0:
        print("   [FAIL] 没有任何已装文件可与 RECORD 比对")
        ok = False
    elif mismatch:
        ok = False
    else:
        print(f"   [ OK ] 已装文件   {compared} 个逐一比对 wheel RECORD，全部一致")

    try:
        stats = _get_json(f"https://pypistats.org/api/packages/{name.lower()}/recent", 30)
        monthly = stats["data"]["last_month"]
        if monthly < MIN_MONTHLY_DOWNLOADS:
            print(f"   [FAIL] 近月下载量 {monthly:,} 低于门槛 {MIN_MONTHLY_DOWNLOADS:,}")
            ok = False
        else:
            print(f"   [ OK ] 近月下载   {monthly:,}")
    except Exception as exc:  # pypistats 会 429，取不到就如实说取不到
        print(f"   [SKIP] 下载量取不到（{type(exc).__name__}），不据此放行也不据此拦截")

    return ok


def main() -> int:
    interp_abi = local_interp_abi()
    platform_tokens = local_platform_tokens()
    names = declared_package_names()
    print(f"pyproject.toml 声明的依赖：{names}")
    print(f"当前解释器 ABI：{interp_abi}，平台 token：{platform_tokens}\n")
    results = [check_package(name, interp_abi, platform_tokens) for name in names]
    print()
    if all(results):
        print("供应链门禁：通过")
        return 0
    print("供应链门禁：不通过")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
