"""阅读台账门禁：`references/` 里声称「读过」的东西，正文里必须真有对应内容。

## 为什么有这个脚本（台账 N-31）

`references/README.md` 第 2 条硬规则要求每份产物标注「读到什么程度」，
但在本脚本之前**没有任何机制检查这条规则**——`check_xrefs.py` 只查编号引用。

后果不是假想的。同一个失效模式在 2026-08-19 至 08-23 之间**连续发生四次**：

| # | 文件 | 形态 |
|---|---|---|
| 1 | `hello-agents-deep-read-part4.md` | 覆盖表把 Ch8.2 / Ch9.6.3 / Ch10.5 标成「全文」，正文只写到 Ch7.2 |
| 2 | `hello-agents-framework-tools.md` | `tools/**` 十个文件全标「全文」，正文零分析（`grep tools/base.py` 只命中台账行本身） |
| 3 | `hello-agents-ch07-framework.md` | 六处 `§7` 前向引用指向一个**不存在的**「骨架启示」小节 |
| 4 | `deepseek-harness-notes-part3.md` | 台账称 `bug-fix` 读了 75 篇，正文只到 `B-24` |

四次里有一次连主 agent 都照抄进了提交信息。**「先落正文再改台账」写在 prompt 里拦不住，
因为写 prompt 的人和违反它的人是同一个。**

## 规则（只有一条，且抓住过上表里的两次真实事故）

**R1 —— 声称读过的**大**目标，正文里必须单独出现。**
覆盖表中标注为「全文」或「部分」、且台账自报行数 ≥ 100 的行，
取其第一个反引号 token（文件路径 / 章节标识），
要求该 token 在**表格之外**的正文里至少出现一次。抓的是第 2、第 1 号事故。

**为什么设 100 行阈值**：小文件（`__init__.py` 17 行、`version.py` 5 行）被并进组讨论
是合理写法，逐个要求单独段落会把门禁变成一张豁免清单——而一张全是豁免的门禁
就是不门禁。第 2 号事故里的 `tools/base.py` 是 **453 行**：
**大文件声称「全文」却在正文里零出现，才是事故形态。**
台账没写行数时按「大」处理，宁可报红。

**（原计划的 R2 已撤销，理由记在下面「抓不到什么」。）**

## 明确抓不到什么（不许把「门禁通过」读成「台账全对」）

- **悬空的前向引用（第 3 号事故）**。初版曾设计一条「同文件 `§N` 引用必须指向真实小节」的规则，
  实跑后撤销：`references/` 里的 `§5.1` 绝大多数指的是**被读文档自己的小节**，不是本文件的，
  机械上无法区分，误报淹没真报。而且第 3 号事故的悬空引用形如 `S-1`…`S-4`（标识符），
  `§N` 形式本来也抓不到。**这一类目前无门禁，记为已知缺口。**
- **目录级聚合行**。`| implemented/bug-fix | 76 | 75 | 全文 |` 这种一行代表 75 篇的写法，
  R1 只会去找 `implemented/bug-fix` 这个 token，而它必然在正文里出现——
  **第 4 号事故本脚本抓不到**。要抓它得比对「声称篇数」与「正文条目数」，
  而条目编号格式各文件不一，无法机械通用。**这是已知缺口，不是疏漏。**
- 内容对不对。R1 只保证「正文里提到了」，不保证「真读了」。
- 跨文件的引用（那是 `check_xrefs.py` 的职责）。

## 豁免

个别行确实只在表内出现是合理的（例如被归入某个合并小节讨论）。
这类进 `EXEMPT`，**显式、可数、新增会拦**——手法与 `check_xrefs.py` 的
`KNOWN_COLLISIONS` 一致：旧的登记豁免，新的一律红。

退出码 0 = 通过；1 = 存在无正文支撑的台账行。
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCOPE = "references/"

# 台账行里表示「已读」的标注。「待读 / 待填 / 未读 / UNVERIFIED」不算声称读过，跳过。
CLAIM_READ = re.compile(r"(全文|部分)")
CLAIM_SKIP = re.compile(r"(待读|待填|未读|UNVERIFIED|不重读|见 part|见 §)")

# 行首反引号 token：`hello_agents/core/agent.py` / `ch08_zh.md` / `subsystems/tools.md`
TOKEN = re.compile(r"`([^`]+)`")

# 阅读目标的形状：路径或源文件名，且不含空格。
# 不含空格这一条排掉了命令字符串（`git sparse-checkout disable`）
# 与带行号区间的描述（`src/x.py:44-65, 250-265`）——它们不是「一个被读的目标」。
TARGET_SHAPE = re.compile(r"^[^\s]+$")
# 覆盖表的表头签名。只有表头命中这个的表才被当作台账表。
LEDGER_HEADER = re.compile(r"(读到什么程度|读到哪|标注|覆盖|全文 / 部分|全文/部分)")

TARGET_HINT = re.compile(r"(/|\.py$|\.md$|\.ts$|\.ya?ml$|^ch\d+)")

# 台账行里的「行数」列。规模阈值：小文件（如 `__init__.py` 17 行、`version.py` 5 行）
# 被并进组讨论是合理的写法，不该报红；**大文件声称「全文」却在正文里零出现，才是事故形态**
# （第 2 号事故的 `tools/base.py` 是 453 行）。取不到行数时按「大」处理，宁可报红。
SIZE_CELL = re.compile(r"\|\s*(\d{1,6})\s*\|")
# 章节行号区间 token：ch6:1288-1305
RANGE_TOKEN = re.compile(r"^(ch\d+):(\d+)-(\d+)$")
MIN_LINES_FOR_INDIVIDUAL_EVIDENCE = 100

# (文件名, 台账行里的 token) —— 显式豁免，新增会拦
EXEMPT: set[tuple[str, str]] = set()


def tracked_references() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", f"{SCOPE}*.md"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.split()
    return [REPO / rel for rel in out]


def check_file(path: Path) -> list[str]:
    rel = path.relative_to(REPO).as_posix()
    lines = path.read_text(encoding="utf-8").splitlines()

    # 只认「覆盖表」：表头必须带阅读程度类列名。正文里的启示表、判据表等同样是
    # markdown 表格，但它们不是台账，误把它们当台账会产生大量假红。
    table_rows: list[tuple[int, str]] = []
    prose: list[str] = []
    in_ledger_table = False

    for lineno, line in enumerate(lines, start=1):
        if line.lstrip().startswith("|"):
            if LEDGER_HEADER.search(line):
                in_ledger_table = True
            elif in_ledger_table:
                table_rows.append((lineno, line))
        else:
            if line.strip() == "" or line.lstrip().startswith(">"):
                pass  # 表格后的空行/引注不终止台账表
            else:
                in_ledger_table = False
            prose.append(line)

    prose_text = "\n".join(prose)
    problems: list[str] = []

    # --- R1 ---
    for lineno, row in table_rows:
        if not CLAIM_READ.search(row) or CLAIM_SKIP.search(row):
            continue
        toks = TOKEN.findall(row)
        if not toks:
            continue
        tok = toks[0]
        if not TARGET_SHAPE.match(tok) or not TARGET_HINT.search(tok):
            continue  # 不是一个「被读的目标」，跳过
        if (rel, tok) in EXEMPT:
            continue
        m = SIZE_CELL.search(row)
        if m and int(m.group(1)) < MIN_LINES_FOR_INDIVIDUAL_EVIDENCE:
            continue  # 小文件允许并组讨论
        # 台账常写全路径（`hello_agents/agents/react_agent.py`），正文常写短形式
        # （`agents/react_agent.py:338`）。检查的是「这个目标有没有被讨论」，
        # 不是「这个字符串在不在」，所以 basename 命中也算。
        basename = tok.rsplit("/", 1)[-1]
        if tok in prose_text or basename in prose_text:
            continue
        # 章节行号区间（`ch6:1288-1305`）：正文通常引单行（`ch6:1299`）。
        # 区间内任一行号被引到，就算这一段有正文支撑。
        rng = RANGE_TOKEN.match(tok)
        if rng:
            ch, lo, hi = rng.group(1), int(rng.group(2)), int(rng.group(3))
            cited = {int(x) for x in re.findall(rf"{re.escape(ch)}:(\d+)", prose_text)}
            if any(lo <= c <= hi for c in cited):
                continue
        if True:
            problems.append(
                f"{rel}:{lineno}  台账称已读 `{tok}`，但正文（表格之外）里找不到它"
            )

    return problems


def count_claims(path: Path) -> int:
    """与 check_file 同口径地数「已读」台账行，避免两处统计口径漂移。"""
    n = 0
    in_ledger = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("|"):
            if LEDGER_HEADER.search(line):
                in_ledger = True
            elif in_ledger and CLAIM_READ.search(line) and not CLAIM_SKIP.search(line):
                toks = TOKEN.findall(line)
                if toks and TARGET_SHAPE.match(toks[0]) and TARGET_HINT.search(toks[0]):
                    m = SIZE_CELL.search(line)
                    if not (m and int(m.group(1)) < MIN_LINES_FOR_INDIVIDUAL_EVIDENCE):
                        n += 1
        elif line.strip() and not line.lstrip().startswith(">"):
            in_ledger = False
    return n


def main() -> int:
    files = tracked_references()
    problems: list[str] = []
    claims = 0

    for path in files:
        problems.extend(check_file(path))
        claims += count_claims(path)

    print(f"扫描 {len(files)} 份 references 产物，检查 {claims} 条「已读」台账行。")

    if problems:
        print("\n阅读台账门禁：不通过")
        for p in problems:
            print(f"  [FAIL] {p}")
        return 1

    print(f"已登记豁免 {len(EXEMPT)} 条（显式，新增会拦）。")
    print("\n阅读台账门禁：通过")
    print("  注意：本门禁抓不到目录级聚合行（见脚本 docstring「明确抓不到什么」）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
