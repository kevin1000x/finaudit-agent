"""H2 题包的**自足性**检查：每一页有没有带够让人下结论的东西。

## 它回答的问题，以及**它回答不了的问题**

`h2-01` 的失败模式不是「答错了」，是**「说不出对错」**——15 题里 13 题判
`无法判断`，判「对」0 题、判「错」也 0 题（`A-14`）。也就是说当时缺的是
**页面自足性**，不是能力。`D-038` 因此补了三节（`G1` 计算输入取值 /
`G2` 触发条件的字段取值 / `G3` 指标清单快照）。

本脚本查的就是那件事，而且**只查那件事**：

- ✅ 能查：这一页有没有带着「重算一遍所需的东西」。
- 🔴 **查不了**：那个数对不对、那个口径在实务上合不合适、
  一个人读完之后是不是真的能判。**后者只有人（或一次盲审）能给。**

⚠️ 所以它通过**不等于** `AC-06` 通过。把它当成 `AC-06` 的证据，
就是把「材料齐了」说成「结论成立」—— 那正是 `AC-05` 已知盲区的同一形状。

## 每一类页面要带什么

分类**从拒答理由的措辞推**，不从题号硬编 —— 硬编等于把标准答案抄进检查器。

| 页面类型 | 必须带 | 为什么 |
|---|---|---|
| 作答 | 「这个数是拿哪几个数算出来的」且**每个字段都有取值** | `D-038 G1`：不给输入，读者只能选择信或不信 |
| 拒答·触发了口径里的某一条 | 「凭什么说满足了这一条」且带字段取值 | `D-038 G2`：只说「触发了」，读者确认不了「触发得对」 |
| 拒答·没有这个指标 | 「我们当时有哪些指标」清单 | `D-038 G3`：否则这是一句不可证伪的断言 |
| 拒答·题面缺主体/期间 | 理由里**点名缺的是哪一项** | 这类页面的自足性就在那句话里；`G3` 刻意不挂（`answer.py` 写明：那时 94 行清单与结论无关） |
| 拒答·数据源里没这一行 | 说清是哪个数据源、取的哪一行 | 读者要能分清「没有这家公司」与「这家公司没有这个指标」 |

## 用法

    .venv/Scripts/python scripts/check_h2_selfcontained.py docs/agent/h2-02/packets.md

退出码 0 = 每一页都带够了；1 = 有缺口，逐题列出。

## 它不是提交链上的门禁

见 `scripts/check_gates.py` 的 `NOT_GATES`。链上的判定点是
`tests/test_h2_selfcontained.py`（把每一节分别挖掉看红），而 pytest 已经是链的第一环。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

SPLIT = re.compile(r"={60,}\n(H2-\d+)\n={60,}")

# 🔴 小节抬头**从渲染器 import，不在这里抄一份**。
#
# 2026-09-09 教训：原来这里抄了六个常量，注释还写着「不在这里重写措辞」。
# 同一天改了拒答页的抬头（「这个数是从哪儿来的」→「查的是哪份数据」），
# **抄来的那份没跟着改** —— 拿当前渲染器重出一份题包再跑，15 题里 9 题报「缺出处」。
# 而存盘的那份题包照样全绿，因为它是用旧渲染器出的。
#
# ⇒ **只查存盘产物的检查，查不出渲染器变了。**（`N-42` 那个形态，第六次。）
from agent.answer import (  # noqa: E402
    _A_ANSWER as H_ANSWER,
    _A_INPUTS as H_INPUTS,
    _A_REFUSED as H_REFUSED,
    _A_REGISTRY as H_REGISTRY,
    _A_WHERE as H_WHERE,
    _A_WHERE_REFUSED as H_WHERE_REFUSED,
    _A_WHY_HIT as H_WHY_HIT,
)

#: 拒答理由的措辞 → 该页属于哪一类。**顺序有意义**，先匹配到的算。
#
# ⚠️ 每一条都要**够独特**。原来有一条是「里没有」（想匹配「…里没有 900001/2023
# 这一行」），而同日改过的「这句话**里没有**我认得出的指标名」也含这三个字 ——
# 于是「没有这个指标」被误判成「没有这一行」。而 `unknown` 那条兜底**没兜住**：
# 它确实匹配上了，只是匹配错了。**松的判据比没有判据更危险**，
# 因为它让「认不出」这个信号消失了。
REFUSAL_KINDS = (
    ("没有对应的口径定义", "no_metric"),
    ("认得出的指标名", "no_metric"),
    ("题面里没有主体", "incomplete"),
    ("没有认得出的公司", "incomplete"),
    ("题面里没有期间", "incomplete"),
    ("出现多个主体", "incomplete"),
    ("出现多家公司", "incomplete"),
    ("出现多个期间", "incomplete"),
    ("这一行", "no_row"),          # 「…里没有 900001/2023 这一行」
)


def split_packets(text: str) -> dict:
    parts = SPLIT.split(text)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}


def _section(body: str, head: str) -> str | None:
    """取某一小节的正文（到下一个顶格抬头或分隔线为止）。不存在返回 None。"""
    lines = body.splitlines()
    try:
        start = next(i for i, l in enumerate(lines) if l.strip() == head)
    except StopIteration:
        return None
    out = []
    for l in lines[start + 1:]:
        s = l.strip()
        if not s:
            if out:
                break
            continue
        if s.startswith("─") or s.startswith("="):
            break
        out.append(s)
    return "\n".join(out)


def _where(body: str) -> str | None:
    """出处那一节。**作答页与拒答页抬头不同**：拒答页那几页根本没有数，
    所以抬头是「查的是哪份数据」而不是「这个数是从哪儿来的」——
    一个抬头不该承诺页面里不存在的东西。
    """
    return _section(body, H_WHERE) or _section(body, H_WHERE_REFUSED)


#: 「没有值」的三种写法。**它们都是有效取值**，不是缺口 ——
#: `agent.answer._shown` 的 docstring 写明这三种必须分开写死、不许都显示成空白，
#: 因为「取到了是 0」与「根本没取到」对复核者是完全不同的两件事。
#: ⚠️ 这份清单与 `_shown` 必须同步：`tests/test_h2_selfcontained.py` 有一条
#:    直接拿 `_shown` 的输出来喂本函数，`_shown` 改了措辞而这里没跟着改就会红。
VALUE_MARKERS = ("缺失", "空值", "是", "否")


def _has_value(section: str | None) -> bool:
    """这一节里有没有**取值**，而不只是字段名。

    一个只列字段名不列取值的「输入」节，对复核者的价值等于零 ——
    那正是 `h2-01` 里 13 题「无法判断」的形状。

    ⚠️ 判据**不是「有没有数字」**。首跑就撞上了：`H2-04` 的那一行是
    「营业收入　（缺失：数据源里没有这一行）」—— 一个数字都没有，
    而它恰恰是这一页最要紧的一句话。按「有没有数字」判会把它误报成缺口，
    而误报会让人开始跳过这个检查。
    """
    if not section:
        return False
    for line in section.splitlines():
        if re.search(r"\d", line):
            return True
        if any(m in line for m in VALUE_MARKERS):
            return True
    return False


def classify(body: str) -> str:
    if _section(body, H_ANSWER) is not None:
        return "answered"
    why = _section(body, H_REFUSED) or ""
    if _section(body, H_WHY_HIT) is not None:
        return "rule_hit"
    for 措辞, kind in REFUSAL_KINDS:
        if 措辞 in why:
            return kind
    return "unknown"


def check_one(tag: str, body: str) -> list[str]:
    kind = classify(body)
    gaps: list[str] = []

    if kind == "answered":
        inputs = _section(body, H_INPUTS)
        if inputs is None:
            gaps.append("作答页缺「" + H_INPUTS + "」（D-038 G1）")
        elif not _has_value(inputs):
            gaps.append("「" + H_INPUTS + "」只有字段名、没有取值 —— 读者仍然只能选择信或不信")
    elif kind == "rule_hit":
        why = _section(body, H_WHY_HIT)
        if not _has_value(why):
            gaps.append("拒答页的「" + H_WHY_HIT + "」没有字段取值（D-038 G2）")
    elif kind == "no_metric":
        snap = _section(body, H_REGISTRY)
        if snap is None:
            gaps.append("说「没有这个指标」却没给「" + H_REGISTRY + "」清单（D-038 G3）—— 不可证伪")
    elif kind == "incomplete":
        why = _section(body, H_REFUSED) or ""
        if not any(w in why for w in ("主体", "期间")):
            gaps.append("说题面不全，却没点名缺的是哪一项")
    elif kind == "no_row":
        if _where(body) is None:
            gaps.append("说数据源里没有这一行，却没说清是哪个数据源")
    else:
        gaps.append("认不出这一页属于哪一类 —— 拒答理由的措辞可能改过，检查器要跟着改")

    if _where(body) is None:
        gaps.append(
            "缺出处（作答页「" + H_WHERE + "」／拒答页「" + H_WHERE_REFUSED + "」）："
            "任何一页都要说清数据是真实年报还是合成夹具（D-010）"
        )
    return gaps


def check(text: str) -> dict:
    return {tag: check_one(tag, body) for tag, body in split_packets(text).items()}


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("用法：check_h2_selfcontained.py <packets.md>")
        return 2
    path = Path(argv[1])
    packets = split_packets(path.read_text(encoding="utf-8"))
    if not packets:
        print("没解析出任何题包 —— 分隔线格式变了？")
        return 1

    结果 = check(path.read_text(encoding="utf-8"))
    坏 = {t: g for t, g in 结果.items() if g}

    print("题包：" + str(path) + "（" + str(len(packets)) + " 题）")
    for tag in sorted(packets):
        kind = classify(packets[tag])
        标记 = "OK " if not 结果[tag] else "🔴 "
        print("  " + 标记 + tag + "  " + kind)
        for g in 结果[tag]:
            print("        " + g)

    print()
    if 坏:
        print("🔴 " + str(len(坏)) + " 题自足性有缺口。")
        return 1
    print("每一页都带够了「重算一遍所需的东西」。")
    print("⚠️ 这**不等于** AC-06 通过 —— 材料齐了不等于结论成立，")
    print("   「一个人读完能不能判」只有人或一次盲审能给。")
    return 0


if __name__ == "__main__":  # pragma: no cover - 手工用
    sys.exit(main(sys.argv))
