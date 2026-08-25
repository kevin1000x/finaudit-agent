"""统计 docs/agent/LANDING-BACKLOG.md §5 的状态分布。

**为什么需要一个脚本而不是一条 grep**：状态被改过的行写成
`~~OPEN~~ → **已落地 2026-08-23**`，字面里 `OPEN` 与 `已落地` 同时存在。
裸 `grep -c OPEN` 会把它数成未落地，得 65 而真实是 62。
分类必须**按优先级短路**：先判终态（已关闭 / 部分落地 / 已落地），最后才判 OPEN。

分类前先删掉 `~~...~~` 的内容：删除线的语义是「这条不再成立」。

状态档位（顺序即优先级）：`已关闭` / `部分落地` / `已落地` 是终态；
**`已并进计划`** 表示条目已写进某份 PLAN 的约束里、**但代码还没写**——
它既不是已落地，也不该和「只躺在登记册里」混同；`BLOCKED` 被 U-0x 挡住；
`依据` 只差补一行出处；`OPEN` 是尚未路由到任何计划的。

明确抓不到什么：
- 不校验状态词是否拼对。写了个没见过的状态词会归入 `?` 一栏并打印出来，
  但脚本**不会因此非零退出**——它是统计工具不是门禁。
- 不校验 §1 的分布表是否与此处一致。**回写是人的动作**，本脚本只负责给出正确的数。
  ⇒ 这条链上没有任何一环会红：状态词写错 → 归入 `?` → 分布表数错 → 人照抄进 §1。
  而 §1 的数字是要转述出去的。**若这条链出过一次事故，就该把它升格为门禁**
  （2026-08-24 独立复核指出这个缺口，暂不做，如实记在这里）。
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
    # 「已并进计划」排在 OPEN 之前、终态之后：它**不是已落地**（代码还没写），
    # 但也不该和「只躺在登记册里」混为一谈——那个区分正是 2026-08-25 沉淀审计要回答的。
    ("已并进计划", lambda c: "已并进" in c),
    ("BLOCKED", lambda c: "BLOCKED" in c),
    ("DECIDED", lambda c: "DECIDED" in c),
    # 用 `startswith` 而非 `in`：「依据」二字在别的状态里也出现
    # （例：「已落地……补进依据栏」），用 `in` 会把它们误归到这一类。
    # 但必须先剥掉 markdown 强调符，否则 `**依据**` 会落到 `?`。
    # 2026-08-24 独立复核指出：六条规则用 `in`、唯独这条用 `startswith`，
    # 当前 4 条恰好都是裸写的所以没炸。
    ("依据", lambda c: _strip_emphasis(c).startswith("依据")),
    ("OPEN", lambda c: "OPEN" in c),
]


def _drop_struck(cell: str) -> str:
    """删掉 `~~...~~` 里的内容。

    **删除线的语义就是「这条不再成立」**，它是被取代的旧状态。
    不剥掉的话，`~~OPEN~~ → ~~部分落地~~ → **已落地**` 会先命中「部分落地」
    ——因为规则按优先级短路，而旧状态排在新状态前面。
    2026-08-24 落地 J-7 时当场撞上：L-2 明明是已落地，被数成部分落地。
    """
    return re.sub(r"~~.*?~~", "", cell)


def _strip_emphasis(cell: str) -> str:
    """剥掉 markdown 强调，只留状态词本身。"""
    return cell.lstrip("*~` ").strip()


def classify(cell: str) -> str:
    cell = _drop_struck(cell)
    for name, hit in RULES:
        if hit(cell):
            return name
    return "?"


def main() -> int:
    rows = [l for l in DOC.read_text(encoding="utf-8").split("\n") if ROW.match(l)]
    counts: collections.Counter[str] = collections.Counter()
    unknown: list[str] = []
    for line in rows:
        # `rstrip("|")` 对行尾是 `| ` （竖线后有空格）的行取不到状态列，
        # 会静默归到 `?`。先整体 strip 再剥竖线。
        cell = line.strip().rstrip("|").rsplit("|", 1)[-1].strip()
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
    # 原先这里有一条 `assert sum(counts.values()) == len(rows)`。
    # 它**恒真**（每行恰好 `counts[kind] += 1` 一次），构造上不可能红；
    # 而且 `python -O` 会把 assert 整条剥掉，拿它做运行时校验本就不可靠。
    # 2026-08-24 独立复核指出——第六道门的 R3 拒绝的正是这类恒真断言，
    # 只是它的作用域限于 `tests/`，没管到这里。已删除，不替换成别的假检查。
    print("\n把上面的数回写到 LANDING-BACKLOG.md §1 的分布表。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
