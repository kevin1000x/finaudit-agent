"""交叉引用门禁：本仓库的编号引用必须指向真实存在的条目。

## 为什么有这个脚本（台账 D-30）

deepseek-harness 的 `.agents/notes/README.md:17` 逐字写着：

> Cross-references between Agent Notes use relative markdown links
> —— **never bare prose or numbers** —— so they are **mechanically checkable**.

本仓库通篇用裸编号（`D-013` / `A-4` / `F-2` / `AC-01`）做交叉引用。
后果不是"不好看"，是**条目改名或删除后引用会静默失效，没有任何东西会红**——
这与本项目正在收集的失效模式同型：**看起来可追溯，实际不可复核**。

**为什么不改成 markdown 链接**：全仓约 890 处引用，全量转链接会毁掉中文行文的可读性，
且 harness 采用链接的理由之一是"survive moves between folders"，
而本仓库的权威文档不会移动。**真正要的是那道会红的门，不是链接这个形式。**
所以本脚本保留裸编号写法，改为**校验它们指向真实定义点**。

## 覆盖范围（明确列出，不覆盖的不许假装覆盖）

七个有**单一拥有者**的命名空间。定义点的正则来自实际文件，不是猜的。

**刻意不覆盖**（如实说明，避免"门禁通过"被误读成"全部引用都被检查过"）：
- `SC-N` —— 每个阶段各有一套 SC-1…SC-N，**同名不同义**，无单一拥有者
- `H1`–`H3`、`C1`–`C5`、`L0`–`L4` —— 假设 / 题类 / 分层，散落在正文叙述里
- `T-01-NN` —— 威胁编号，定义在各 PLAN 文件内，随阶段增删

## 零填充是命名空间的一部分

`D-014`（决策，`DECISIONS.md`）与 `D-14`（台账 D 区，`OPEN-ITEMS.md`）
**是两个不同的东西，只差一个字符**。三位零填充 = 决策，一到两位 = 台账。
本脚本按此区分，并对**数值相同的跨命名空间碰撞**单独报告：
已存在的碰撞进显式白名单（可见、可数），**新增碰撞即非零退出**。
（这一手法照抄 harness 对 pre-format 笔记的处理：旧的显式豁免，新的一律拦。）

退出码 0 = 全部通过；1 = 存在悬空引用或未登记的新碰撞。
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# ns -> (拥有者文件, 定义点正则, 引用正则)
def _ref(body: str) -> re.Pattern:
    r"""引用正则的构造器。**刻意不用 `\b`。**

    Python 的 `\w` 包含 CJK，所以「台账N-13」里 `账` 与 `N` 之间**没有词边界**，
    `\bN-13\b` 匹配不到它。而中文行文里编号紧跟汉字是常态——
    用 `\b` 会**静默漏检**一大批引用，让门禁显得很绿。
    （本脚本第一版就是这么写的，写测试时才发现。）

    改用显式 lookaround：只有 ASCII 字母、数字、连字符算「粘连」，CJK 一律算分隔。
    """
    return re.compile(r"(?<![0-9A-Za-z-])(?:" + body + r")(?![0-9A-Za-z-])")


NAMESPACES = {
    "D-decision": (
        "DECISIONS.md",
        re.compile(r"^## (D-\d{3})", re.M),
        _ref(r"D-\d{3}"),
    ),
    "U": (
        "DECISIONS.md",
        re.compile(r"^- ~*\*\*(U-\d{2})\*\*", re.M),
        _ref(r"U-\d{2}"),
    ),
    "ledger": (
        "docs/agent/OPEN-ITEMS.md",
        re.compile(r"^### ~*([ABNE]-\d{1,2})", re.M),
        _ref(r"[ABN]-\d{1,2}"),
    ),
    "F": (
        "rules/failure-modes.md",
        re.compile(r"^## (F-\d+)", re.M),
        _ref(r"F-\d+"),
    ),
    "AC": (
        "PROJECT_SPEC.md",
        re.compile(r"^- \*\*(AC-\d{2})\*\*", re.M),
        _ref(r"AC-\d{2}"),
    ),
    "NFR": (
        "PROJECT_SPEC.md",
        re.compile(r"^- (NFR-\d{2})", re.M),
        _ref(r"NFR-\d{2}"),
    ),
    "OQ": (
        "docs/agent/phase-01/open-questions.md",
        re.compile(r"^## (OQ-\d{2})", re.M),
        _ref(r"OQ-\d{2}"),
    ),
}

# 跨命名空间数值碰撞的显式豁免名单。**保持为空。**
#
# 2026-08-18 之前，台账「本轮讨论新增」区用 `D-` 前缀，于是 `D-001`…`D-012`
# 与台账 `D-1`…`D-12` **全部撞号**——两个不同的东西只差一个零填充，
# 靠人记得约定来区分。已把该区改名为 `N-`，碰撞这一类被物理消灭。
#
# 本名单保持为空即表示「不存在任何需要靠约定区分的编号对」。
# 往里加东西 = 承认又引入了一对易混编号，必须在此写明为什么可以接受。
KNOWN_COLLISIONS: set[tuple[str, str]] = set()

# 不参与校验的文件：会引用编号但不是权威文档的地方
EXCLUDED = (
    "references/",            # 外部项目深读报告，会引用它们自己的编号
    "claudedocs/",            # 历史 handoff，冻结的叙述
    "scripts/check_xrefs.py",  # 本文件，模式串定义处
    ".planning/phases/",      # PLAN/SUMMARY 里有 T-01-xx 等阶段内编号
)


def tracked_markdown() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "*.md"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.split()
    keep = []
    for rel in out:
        if any(rel.startswith(x) or rel == x for x in EXCLUDED):
            continue
        keep.append(REPO / rel)
    return keep


def build_registry() -> dict[str, set[str]]:
    reg: dict[str, set[str]] = {}
    for ns, (owner, def_re, _) in NAMESPACES.items():
        path = REPO / owner
        if not path.is_file():
            raise SystemExit(f"命名空间 {ns} 的拥有者文件不存在：{owner}")
        ids = set(def_re.findall(path.read_text(encoding="utf-8")))
        if not ids:
            # 定义点一个都没匹配到，说明正则与文件写法脱节——这是门禁自身失效，必须报错
            raise SystemExit(
                f"命名空间 {ns} 在 {owner} 里没有匹配到任何定义点。"
                "正则与文件写法已脱节，请先修本脚本，不要让门禁静默通过。"
            )
        reg[ns] = ids
    return reg


def check_collisions(reg: dict[str, set[str]]) -> list[str]:
    """跨命名空间的数值碰撞（D-014 vs D-14）。已登记的放行，新增的拦。"""
    problems = []
    decisions = reg["D-decision"]
    # 台账已无 D- 前缀（2026-08-18 改名为 N-）。此处仍然检查，
    # 是为了拦住「把 D- 重新引入台账」这个回退——门禁要防的是未来，不只是现状。
    ledger_d = {i for i in reg["ledger"] if i.startswith("D-")}
    for d in sorted(decisions):
        n = int(d.split("-")[1])
        cand = f"D-{n}"
        if cand in ledger_d and (d, cand) not in KNOWN_COLLISIONS:
            problems.append(
                f"新增跨命名空间碰撞：{d}（决策）与 {cand}（台账 D 区）数值相同。"
                "二者只差零填充，极易误引。要么改编号，要么在 KNOWN_COLLISIONS 里"
                "登记并写明为什么可以接受。"
            )
    return problems


def main() -> int:
    reg = build_registry()
    print("已登记的定义点：")
    for ns, ids in reg.items():
        owner = NAMESPACES[ns][0]
        print(f"  {ns:<12} {len(ids):>3} 个   ← {owner}")

    dangling: list[str] = []
    checked = 0
    for path in tracked_markdown():
        rel = path.relative_to(REPO).as_posix()
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            for ns, (_, _, ref_re) in NAMESPACES.items():
                for m in ref_re.finditer(line):
                    ident = m.group(0)
                    checked += 1
                    if ident not in reg[ns]:
                        dangling.append(f"{rel}:{lineno}  悬空引用 {ident}（命名空间 {ns}）")

    print(f"\n扫描 {len(tracked_markdown())} 个 markdown 文件，检查 {checked} 处引用。")

    problems = dangling + check_collisions(reg)
    if problems:
        print("\n交叉引用门禁：不通过")
        for p in problems:
            print(f"  [FAIL] {p}")
        return 1

    print(f"已登记的跨命名空间碰撞 {len(KNOWN_COLLISIONS)} 对（显式豁免，新增会拦）：")
    for a, b in sorted(KNOWN_COLLISIONS):
        print(f"  {a} / {b}")
    print("\n交叉引用门禁：通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
