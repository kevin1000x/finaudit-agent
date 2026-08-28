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
import re
import sys
import sysconfig
import tomllib
import urllib.request
import zipfile
from importlib.metadata import PackageNotFoundError, distribution, distributions
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------
# 许可证禁列（D-014）
# --------------------------------------------------------------------------
# D-014 禁止 AGPL 组件进入本仓库：Web 演示是网络服务，AGPL v3 §13 的网络条款
# 要求向交互用户提供源码，与 D-005「主仓私有至 Phase 4」不能同时成立。
#
# 这条约束此前只写在文档里。**文档管不住 `pip install`。**
# 台账 A-5 要求把它变成机器检查，本节就是那个检查。
#
# 注意 PyMuPDF 这类双授权包（AGPL v3 或商业授权）在 PyPI 元数据里只声明 AGPL。
# 本门禁一律按 AGPL 处理并拒绝 —— 若将来真买了商业授权，那是**决策变更**，
# 应当先修订 D-014 再把包名加进 LICENSE_EXEMPTIONS，而不是在这里放宽正则。
DENIED_LICENSE_PATTERNS = [
    # 只要前导词边界，**不要**尾部 `\b` —— `AGPLv3` 这种写法里 `v` 是单词字符，
    # 加了尾边界就漏掉它（写这条测试时当场漏过一次）。
    # 前导边界仍然保证 `LGPL` 不会被误伤。
    re.compile(r"\bAGPL", re.I),
    re.compile(r"affero", re.I),
]

# 显式豁免名单。**空的**，且加东西进来必须同时给出 DECISIONS.md 的条目号。
LICENSE_EXEMPTIONS: dict[str, str] = {}


def license_fields(meta_info: dict) -> list[str]:
    """把一个包的所有许可证声明位置收集起来。

    三个位置都要看：`license`（自由文本，常为空）、`license_expression`（SPDX，较新）、
    以及 `classifiers` 里的 `License :: ...`。只看其中一个会漏——
    这正是 `rules/failure-modes.md` F-1「我查的范围能不能覆盖它可能存在的位置」。
    """
    out = []
    for key in ("license", "license_expression"):
        v = meta_info.get(key)
        if v:
            out.append(str(v))
    for c in meta_info.get("classifiers") or []:
        if str(c).startswith("License ::"):
            out.append(str(c))
    return out


def license_denied(name: str, fields: list[str]) -> str | None:
    """命中禁列则返回命中的那条声明原文；否则 None。"""
    if name.lower() in LICENSE_EXEMPTIONS:
        return None
    for field in fields:
        for pat in DENIED_LICENSE_PATTERNS:
            if pat.search(field):
                return field
    return None

# 期望的上游仓库。project_urls 里必须出现其中之一，否则判为身份不符。
EXPECTED_UPSTREAM = {
    "pyyaml": "github.com/yaml/pyyaml",
    "pytest": "github.com/pytest-dev/pytest",
    # 2026-08-26 登记（01.5-01 Task 0 的供应链核实，D-014 指定的 PDF 主库）：
    # 76 个版本自 2015-08-24 连续发布、无一 yanked；author 为 Jeremy Singer-Vine；
    # classifier 为 MIT；传递闭包 8 个包（pdfminer.six / Pillow / pypdfium2 /
    # charset-normalizer / cryptography / cffi / pycparser / typing-extensions）
    # 零 AGPL 命中，PyMuPDF / fitz 不在闭包内。
    "pdfplumber": "github.com/jsvine/pdfplumber",
    # 2026-08-27 登记（01.5-04 Task 0 的供应链人工审计，操作者放行）。
    #
    # **RESEARCH 判它 `SUS` 的那个理由已查清，是取数口径问题不是身份可疑**：
    # PyPI 上最早可见发行版是 `1.16.72` @ 2025-04-05，且**版本号从 1.16.x 起跳**；
    # 而 GitHub `akfamily/akshare` **创建于 2019-10-01**（22,258 stars / MIT /
    # 未归档 / 非 fork），GitHub tags 也只剩 214 个、最早同样是 v1.16.7x。
    # ⇒ 包与项目确实自 2019 年存在，PyPI 看不到早期版本是**维护者删了旧 release**
    # （219 版 / 16 个月 ≈ 每两天一版）。若是包名被撤回重发或转手，
    # GitHub 仓库创建日期会对不上 —— 它对得上。与 pdfplumber 那次同型。
    #
    # 219 个版本**无一 yanked**；MIT；wheel 419 个已装文件逐一比对 RECORD 一致。
    #
    # ⚠️ **两条随本次登记一起记的限定**：
    # ① 直接依赖 16 条，含 `curl_cffi`（原生 TLS 指纹）与 `mini-racer`（V8，原生二进制）；
    # ② `akracer>=0.0.13; platform_system == "Linux"` 是 akfamily 自己的 V8 绑定，
    #    **PyPI 上无任何许可证声明**。本机 Windows 装不到它，**CI 跑 Linux 会装**。
    #    见下方 `scan_installed_licenses` 的已知盲区注释。
    "akshare": "github.com/akfamily/akshare",
}

#: 本仓自己的分发。它们不是第三方依赖，许可证由本仓决定，
#: 不参与「零许可证声明」的拦截。**只收本仓自己的，加别的进来要写理由。**
SELF_DISTRIBUTIONS = frozenset({"finaudit-semantic-layer"})

# 近月下载量下限。门禁原文要求「千万级」，此处按月取 1e7。
MIN_MONTHLY_DOWNLOADS = 10_000_000

# 逐包下调的门槛。**这是把门槛调低，不是豁免** —— 被登记的包**仍然要过一个数字门槛**，
# 只是那个数字对它单独定，且必须写下理由与当时的实测值。
#
# ⚠️ **为什么不做成「豁免名单」**：豁免会让门禁对那个包**不再检查任何东西**，
# 而输出里照样是一句「通过」。那正是本项目反复记的形状
# （自证机制说通过了，但它证明的不是它声称证明的事）。
# 下调门槛保留了「掉下去就红」这个性质。
#
# ⚠️ **每加一条都是一次把门放低。** 加之前必须回答：
# 这个包为什么**在结构上**够不到通用门槛，而不是「它就是没那么流行」。
DOWNLOAD_THRESHOLD_OVERRIDES: dict[str, tuple[int, str]] = {
    "akshare": (
        3_000_000,
        "领域专用的中文金融数据库，用户面在结构上就窄于通用库 —— "
        "10,000,000/月 这个门槛是照 pytest（10.7 亿）/ pdfplumber（5,657 万）"
        "这类通用库定的，akshare 不可能与它们同尺度。"
        "2026-08-27 实测 3,738,489/月（≈12.5 万/日），GitHub 22,258 stars、"
        "219 个版本无一 yanked。门槛下调到 300 万而不是取消 —— 掉下去照样红。",
    ),
}


def download_floor(name: str) -> tuple[int, str | None]:
    """这个包要过的下载量门槛，以及下调理由（未下调时为 None）。"""
    override = DOWNLOAD_THRESHOLD_OVERRIDES.get(name.lower())
    if override is None:
        return MIN_MONTHLY_DOWNLOADS, None
    return override

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

    fields = license_fields(meta["info"])
    hit = license_denied(name, fields)
    if hit:
        print(f"   [FAIL] 许可证命中禁列（D-014）：{hit}")
        ok = False
    elif not fields:
        # 查不到 ≠ 没有。如实标 SKIP，不据此放行也不据此拦截。
        print("   [SKIP] PyPI 元数据里没有任何许可证声明，无从判定")
    else:
        print(f"   [ OK ] 许可证     {fields[0]}")

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
        floor, lowered = download_floor(name)
        if monthly < floor:
            print(f"   [FAIL] 近月下载量 {monthly:,} 低于门槛 {floor:,}")
            ok = False
        else:
            print(f"   [ OK ] 近月下载   {monthly:,}")
            if lowered:
                # **下调必须打出来。** 不打出来，一次「门槛被放低后通过」
                # 与一次「本来就够」在输出上完全不可区分。
                print(f"          ⚠️ 门槛已下调至 {floor:,} —— {lowered}")
    except Exception as exc:  # pypistats 会 429，取不到就如实说取不到
        print(f"   [SKIP] 下载量取不到（{type(exc).__name__}），不据此放行也不据此拦截")

    return ok


def installed_license_fields(dist) -> list[str]:
    """本机已装分发的许可证声明。字段名与 PyPI JSON 不同，故单列一个函数。"""
    md = dist.metadata
    out = []
    for key in ("License-Expression", "License"):
        try:
            v = md.get(key)
        except Exception:
            v = None
        if v and str(v).strip() and str(v).strip().upper() != "UNKNOWN":
            out.append(str(v).strip().splitlines()[0])
    try:
        for c in md.get_all("Classifier") or []:
            if str(c).startswith("License ::"):
                out.append(str(c))
    except Exception:
        pass
    return out


def scan_installed_licenses() -> bool:
    """扫本机 venv 里**所有**已装分发，不只是 pyproject 声明的那几个。

    🔴 **已知盲区（2026-08-27 记，尚未修）：本函数分不清「查不到许可证」与
    「许可证不是 AGPL」。** `installed_license_fields` 对一个零许可证声明的分发
    返回空列表，空列表匹配不到任何 AGPL 模式 ⇒ **静默放行**。
    本 venv 里就有活例：`finaudit-semantic-layer`（我们自己）零许可证声明，
    这道扫描照样报 OK。
    真正会咬人的是 `akracer`（akshare 的 Linux 专用传递依赖，PyPI 上无许可证声明）
    —— 本机 Windows 装不到它，**CI 跑的是 Linux**。
    ✅ **2026-08-27 已修**：零许可证声明的分发现在**单独报出来并拦截**，
    不再混进「无 AGPL 命中」那句话里 —— 「查不到」与「不是 AGPL」从此是两个不同的输出。
    本仓自己的包在 `SELF_DISTRIBUTIONS` 里显式豁免。
    

    直接依赖走 PyPI 元数据检查（`check_package`），但 AGPL 也可能从**传递依赖**
    进来 —— 声明列表看不见它。这一步覆盖那个盲区。

    局限如实写清：它只看得见**本机这个 venv 此刻装了什么**。
    别的机器、别的环境、尚未安装的包，它都看不见，因此
    **本函数返回 True 不等于「本项目没有 AGPL 依赖」**，只等于「这个 venv 里没扫到」。
    """
    print("\n== 已装分发的许可证扫描（含传递依赖）")
    hits = []
    unlicensed = []
    total = 0
    for dist in distributions():
        name = (dist.metadata.get("Name") or "").strip()
        if not name:
            continue
        total += 1
        fields = installed_license_fields(dist)
        if not fields:
            unlicensed.append(name)
        hit = license_denied(name, fields)
        if hit:
            hits.append((name, dist.version, hit))
    if hits:
        for name, ver, hit in sorted(hits):
            print(f"   [FAIL] {name} {ver} 命中禁列（D-014）：{hit}")
        return False
    print(f"   [ OK ] 扫描 {total} 个已装分发，无 AGPL 系命中")
    print("          （局限：只覆盖本机此 venv，不能据此断言项目整体无 AGPL 依赖）")

    # **「查不到许可证」与「许可证不是 AGPL」是两件事。**
    # 不分开的话，一个零声明的分发会因为「匹配不到 AGPL 模式」而静默通过 ——
    # 而门禁输出里照样是一句 OK。那正是本项目反复记的形状。
    silent = sorted(x for x in unlicensed if x.lower() not in SELF_DISTRIBUTIONS)
    if silent:
        print(f"   [FAIL] {len(silent)} 个已装分发**没有任何许可证声明**：{silent}")
        print("          零声明 ≠ 不是 AGPL。查不到就是查不到，不据此放行。")
        return False
    print(
        f"   [ OK ] 零许可证声明的第三方分发：0 个"
        f"（本仓自身 {sorted(SELF_DISTRIBUTIONS)} 已豁免）"
    )
    return True


def main() -> int:
    interp_abi = local_interp_abi()
    platform_tokens = local_platform_tokens()
    names = declared_package_names()
    print(f"pyproject.toml 声明的依赖：{names}")
    print(f"当前解释器 ABI：{interp_abi}，平台 token：{platform_tokens}\n")
    results = [check_package(name, interp_abi, platform_tokens) for name in names]
    results.append(scan_installed_licenses())
    print()
    if all(results):
        print("供应链门禁：通过")
        return 0
    print("供应链门禁：不通过")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
