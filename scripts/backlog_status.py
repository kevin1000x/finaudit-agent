"""统计 docs/agent/LANDING-BACKLOG.md §5 的状态分布。

**为什么需要一个脚本而不是一条 grep**：状态被改过的行写成
`~~OPEN~~ → **已落地 2026-08-23**`，字面里 `OPEN` 与 `已落地` 同时存在。
裸 `grep -c OPEN` 会把它数成未落地，得 65 而真实是 62。
分类必须**按优先级短路**：先判终态（已关闭 / 部分落地 / 已落地），最后才判 OPEN。

明确抓不到什么：
- 不校验状态词是否拼对。写了个没见过的状态词会归入 `?` 一栏并打印出来，
  但脚本**不会因此非零退出**——它是统计工具不是门禁。
- 不校验 §1 的分布表是否与此处一致。**回写是人的动作**，本脚本只负责给出正确的数。
"""

from __future__ import annotations

import collections
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
DOC = REPO / "docs" / "agent" / "LANDING-BACKLOG.md"
ROW = re.compile(r"^\| (L-\d+) \|")

# 顺序即优先级，不可重排：终态在前，OPEN 兜底
RULES = [
    ("已关闭", lambda c: "已关闭" in c),
    ("部分落地", lambda c: "部分落地" in c),
    ("已落地", lambda c: "已落地" in c),
    ("BLOCKED", lambda c: "BLOCKED" in c),
    ("DECIDED", lambda c: "DECIDED" in c),
    ("依据", lambda c: c.startswith("依据")),
    ("OPEN", lambda c: "OPEN" in c),
]


def classify(cell: str) -> str:
    for name, hit in RULES:
        if hit(cell):
            return name
    return "?"


def main() -> int:
    rows = [l for l in DOC.read_text(encoding="utf-8").split("\n") if ROW.match(l)]
    counts: collections.Counter[str] = collections.Counter()
    unknown: list[str] = []
    for line in rows:
        cell = line.rstrip("|").rsplit("|", 1)[-1].strip()
        kind = classify(cell)
        counts[kind] += 1
        if kind == "?":
            unknown.append(f"{ROW.match(line).group(1)}: {cell[:60]}")

    print(f"条目总数 {len(rows)}")
    for name, _ in RULES:
        if counts[name]:
            print(f"  {name:6} {counts[name]}")
    if unknown:
        print("\n无法分类（状态词可能写错，不影响退出码）：")
        for u in unknown:
            print(f"  {u}")
    assert sum(counts.values()) == len(rows)
    print("\n把上面的数回写到 LANDING-BACKLOG.md §1 的分布表。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
