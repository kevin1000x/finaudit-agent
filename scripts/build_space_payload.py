"""组装推给 HF Space 的载荷，并在推之前把它扫一遍。

## 为什么要有这个脚本（`N-66` 收口时的两次事故）

2026-09-08 第一次推 Space，载荷是手工 `cp -r` 拼的。两件事因此出错：

1. **`src/finaudit_semantic_layer.egg-info/` 混了进去。**
   `.dockerignore` 里明明写着 `*.egg-info/` —— 但 `.dockerignore` 管的是
   「进不进**镜像**」，管不到「进不进那个**公开仓库**」。**这是两件事**，
   而 `cp -r` 两个都不读。（`D-005` 修订一硬约束三。）
2. **层级拼错过一次。** `service/api.py` 从**自己的模块路径**推数据根
   （`src/service/api.py` → 三层 parent），所以 `src/` 那一层不能塌，
   `metrics/` 与 `data/` 必须是它的兄弟。
   拼错的表现**不是报错**，是覆盖面全 0、每个问题都拒答 —— 一个看起来
   「服务活着只是没数据」的现场。

## 目录清单只有一份

`COPY` 目录**从 `Dockerfile` 现读**，不在这里另抄一份。抄一份就有了第二份真相，
而「一道闸的作用集 ≠ 它自称管住的集合」这个形态（`N-42`）在本仓已经出现四次。

## 它不是提交链上的第八环

见 `scripts/check_gates.py` 的 `NOT_GATES`。它**会**在发现泄漏时退非零 ——
那是**推之前给人直接跑**的那一道。链上的判定点是
`tests/test_space_payload.py`（含把密钥、构建残留、塌掉的层级分别种进去看红的负控制），
而 pytest 已经是链的第一环。同一件事登记两遍，`check_gates` 会要求它再配一套
具名负控制与 CI 步骤，而那套东西已经以测试的形式存在了。

## 用法

    .venv/Scripts/python scripts/build_space_payload.py <输出目录>

退出码 0 = 可以推；1 = 有发现，别推。
"""

from __future__ import annotations

import re
import shutil
import sys
import unicodedata
from pathlib import Path

#: 反斜杠。写成常量是因为它出现在正则里，而正则里的反斜杠数量最容易在编辑时被改错。
BS = chr(92)

REPO_ROOT = Path(__file__).resolve().parent.parent

#: 构建残留。**显式剔除**，因为 `.dockerignore` 对上传这件事没有约束力。
CRUFT_DIRS = ("__pycache__", ".pytest_cache")
CRUFT_SUFFIXES = (".pyc", ".pyo", ".pyd")
CRUFT_PATTERNS = ("*.egg-info",)

#: 载荷里必须存在的东西。**层级是承重的**，见抬头第 2 条。
SHAPE_REQUIRED = (
    "src/service/api.py",
    "src/semantic_layer/resolve.py",
    "metrics/_flags.yaml",
    "data/extracted",
)

#: 密钥形状。宁可误报 —— 误报的代价是我多看一眼，漏报的代价是永久泄漏。
KEY_SHAPES = re.compile(
    r"sk-[A-Za-z0-9]{10}|hf_[A-Za-z0-9]{20}|ghp_[A-Za-z0-9]{20}|github_pat_"
    r"|AKIA[0-9A-Z]{16}|xox[baprs]-|BEGIN [A-Z ]*PRIVATE KEY"
)
#: 形如 `token = "..."` 的赋值。环境变量**名**不算（那不是秘密）。
SECRET_ASSIGN = re.compile(
    r"(?i)(password|passwd|secret|api_key|apikey|token)\s*[:=]\s*[\"'][^\"']{8,}"
)
EMAIL = re.compile(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", re.I)
#: 白名单：文档里举例用的域名不算泄漏。
EMAIL_OK = re.compile(r"(?i)example\.|noreply|@param|@return")


def copy_targets(dockerfile: Path | None = None) -> list[str]:
    """`Dockerfile` 里 `COPY <src> <dst>` 的第一个参数。

    🔴 **这是清单的唯一来源。** 加一个目录只改 `Dockerfile` 一处；
    在这里再维护一份，两份就会在某次改动后不一致，而不一致的表现是
    「镜像里有、公开仓库里没有」或者反过来 —— 后者是泄漏。
    """
    text = (dockerfile or REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    out = []
    for line in text.splitlines():
        if line.startswith("COPY "):
            parts = line.split()
            if len(parts) >= 3:
                out.append(parts[1].rstrip("/"))
    return out


def _is_cruft(path: Path) -> bool:
    if path.suffix in CRUFT_SUFFIXES:
        return True
    parts = set(path.parts)
    if parts & set(CRUFT_DIRS):
        return True
    return any(p.endswith(".egg-info") for p in path.parts)


def compose(dest: Path, repo_root: Path | None = None) -> list[Path]:
    """把载荷拼进 `dest`，返回实际写进去的文件清单。"""
    root = repo_root or REPO_ROOT
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    written: list[Path] = []
    for target in copy_targets(root / "Dockerfile"):
        src = root / target
        if not src.exists():
            raise SystemExit("Dockerfile 里的 COPY 目标不存在：" + target)
        for f in sorted(p for p in src.rglob("*") if p.is_file()):
            if _is_cruft(f):
                continue
            rel = f.relative_to(root)
            out = dest / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, out)
            written.append(rel)
    return written


def check_shape(dest: Path) -> list[str]:
    """层级对不对。拼错了不会报错，只会让整个服务安静地答不出东西。"""
    return [
        "载荷里缺 " + need + "（层级塌了？`src/` 那一层不能少）"
        for need in SHAPE_REQUIRED
        if not (dest / need).exists()
    ]


def sweep(dest: Path) -> list[str]:
    """七类清扫。返回发现（空 = 可以推）。

    ⚠️ 第 2 类查的是**本机用户名**，不是字面量 `C:/Users`：
    `extractor/export.py` 的注释里就写着 `file://C:/Users/.../`，
    那是在讲那条规则本身，不是泄漏。按用户名查才分得开。
    """
    findings: list[str] = []
    # ⚠️ 查的是**家目录路径**，不是裸用户名。首跑就证明了这个区别：
    #    `extractor/download.py` 里的 `github.com/kevin1000x/...` 是 GitHub 账号名，
    #    **本来就是公开的**，按裸用户名查会把它误报掉。泄漏的形状是「本机文件系统
    #    路径出现在产物里」，不是「这个人的名字出现过」。
    home = Path.home()
    username = (
        re.compile(
            # ⚠️ 字符类里要**两个**反斜杠：`[\/]` 会被读成「转义的斜杠」，
            #    反斜杠本身就没了 —— 那样 `C:\Users\Kevin` 反而匹配不上。
            "(?:[A-Za-z]:[" + BS + BS + "/]|/)(?:Users|home)[" + BS + BS + "/]"
            + re.escape(home.name),
            re.I,
        )
        if home.name
        else None
    )

    for f in sorted(p for p in dest.rglob("*") if p.is_file()):
        rel = str(f.relative_to(dest))
        if _is_cruft(f):
            findings.append("[构建残留] " + rel)
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if KEY_SHAPES.search(text):
            findings.append("[密钥形状] " + rel)
        if SECRET_ASSIGN.search(text):
            findings.append("[口令赋值] " + rel)
        if username and username.search(text):
            findings.append("[本机用户名] " + rel)
        for m in EMAIL.finditer(text):
            if not EMAIL_OK.search(m.group(0)):
                findings.append("[邮箱] " + rel + " → " + m.group(0))
        bad = [c for c in text if unicodedata.category(c) in ("Cc", "Cf") and c not in "\n\t"]
        if bad:
            findings.append("[控制字符] " + rel)

    # `source_url` 只允许 null 或 http(s)。`file://` 会把操作者的目录结构公开。
    for f in sorted((dest / "data").rglob("*.yaml")) if (dest / "data").exists() else []:
        for line in f.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("source_url:"):
                v = s[len("source_url:"):].strip()
                if v not in ("null", "~", "") and not v.startswith(("http://", "https://", "'http", '"http')):
                    findings.append("[source_url 非 http] " + str(f.relative_to(dest)) + " → " + v)
    return findings


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.strip().splitlines()[-3].strip())
        return 2
    dest = Path(argv[1]).resolve()
    written = compose(dest)

    problems = check_shape(dest) + sweep(dest)

    print("载荷：" + str(dest))
    print("  " + str(len(written)) + " 个文件，"
          + str(sum(f.stat().st_size for f in dest.rglob("*") if f.is_file()) // 1024) + " KB")
    print("  COPY 清单（现读自 Dockerfile）：" + "、".join(copy_targets()))
    print("\n全文件清单 —— **逐条过目**，这份内容会公开：")
    for rel in written:
        print("  " + str(rel).replace("\\", "/"))

    if problems:
        print("\n🔴 " + str(len(problems)) + " 条发现，别推：")
        for p in problems:
            print("  " + p)
        return 1
    print("\n七类清扫全空，层级正确。可以推。")
    return 0


if __name__ == "__main__":  # pragma: no cover - 手工用
    sys.exit(main(sys.argv))
