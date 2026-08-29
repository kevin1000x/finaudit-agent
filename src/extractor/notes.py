"""财务报表附注里的复选类字段 —— `RecordKind.NOTE_CHECKBOX` 的实现侧。

## 这个模块关掉的是一处真实年报上的假阴性（`A-8`）

三处原文各自可独立复核：

- `metrics/_flags.yaml` 说 `scope_change` 是「合并范围发生变动」；
- `metrics/minority_interest_share.yaml` 的 trigger 是
  `notes.business_combination_type != "无"`；
- 茅台 2023 p120–121，企业合并三项**全部「不适用」**，
  而「5、其他原因的合并范围变动」**是「适用」**（定制营销公司清算注销）。

于是字段取「无」→ trigger 为假 → **flag 不置位，而合并范围确实变了**。
`D-020` 的处置是新增 `notes.consolidation_scope_change` 并把 trigger 改挂它。

**两个字段在同一份年报上取值不同，这本身就是它们必须是两个字段的证明**：
`business_combination_type` 只表**企业合并类型**（六项里的 1、2、3），
`consolidation_scope_change` 表**合并范围有没有变**（六项任一）。
`D-020` 明写前者**保留原义、不被本条改写**。

## 三条硬约束，一条都不能松

1. **定位锚在章节区间内，不靠关键词满篇找。**
   茅台 2023 的 p77 有「6. 同一控制下和非同一控制下企业合并的会计处理方法」——
   那是**会计政策**，不是交易事实。按关键词匹配会把它算成「发生了企业合并」，
   与 cninfo `extract_financial_statements()`「最后一个匹配的表静默胜出」同型。
   本模块的区间是 `[anchor, next_anchor)`，**p77 在构造上就进不来**。

2. **判定读标记，不读关键词的出现与否。** 这是 `L-35` 在附注侧的同型约束：
   类别由显式的「√适用 / □不适用」判定，不靠「这一段看起来像在讲企业合并」反推。

3. **读不出来时返回 `undecidable=True`，不退回全文搜索兜底。**
   退回兜底就是把「读不出来」偷偷变成「读出来了一个可能是错的值」。
   `D-020` 的反转触发条件明写：若六个子项无法可靠判读，
   则改为在证据链里显式记录「该 flag 不可判定」，
   **不得**用一个求不出值的 trigger 冒充规则 —— `undecidable` 就是那个显式记录。

## 派生值用 `None` 表示判不了，不用 `False`

`None`（判不了）与 `False`（判出来没变动）**必须可区分**。
合并成 `False`，一次读不出来会被下游当成「本期合并范围没变」——
那与 `ComputeResult.flags_status` 那条「`evaluated` + 空集 ≠ `unevaluable`」
是同一个形状（`C-5`）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping

from .locate import (
    ApplicabilityUnreadable,
    SectionAnchor,
    find_section_anchors,
    next_anchor_after,
    read_applicability,
)
from .record import RecordKind

__all__ = [
    "NEXT_SECTION_TITLE",
    "SECTION_TITLE",
    "SUB_TITLES",
    "COMBINATION_ITEMS",
    "ScopeChangeItem",
    "ScopeChangeReading",
    "derive_business_combination_type",
    "derive_consolidation_scope_change",
    "read_scope_change",
    "scope_change_from_lines",
]

#: 章节标题的**正文**，不含序号。序号跨公司会变（茅台 `九、`、万华 `八、`、顺丰 `五、`），
#: 正文不变 —— `find_section_anchors` 对序号容差、对正文逐字（`C-2`）。
SECTION_TITLE = "合并范围的变更"

#: 区间右端点用的下一章正文。给 `find_section_anchors` 的 `titles` 必须**两个都给**，
#: 否则算不出区间右界，读取会一路吃到文末。
NEXT_SECTION_TITLE = "在其他主体中的权益"


class ScopeChangeItem(Enum):
    """证监会披露模板的**固定六项**。值是版面上印的子项正文（不含序号）。

    **穷举，没有兜底成员。** 多出一项应当是读取失败（`undecidable`），
    不是静默归进一个 `OTHER_UNKNOWN` —— 那会让「模板变了」这件事无声无息地过去。

    ⚠️ 第 6 项就叫「其他」，与第 5 项「其他原因的合并范围变动」**不是包含关系**，
    是模板里两个并列的子项。逐字相等匹配下不会串（子串匹配会）。
    """

    NON_COMMON_CONTROL_COMBINATION = "非同一控制下企业合并"
    COMMON_CONTROL_COMBINATION = "同一控制下企业合并"
    REVERSE_ACQUISITION = "反向购买"
    SUBSIDIARY_DISPOSAL = "处置子公司"
    OTHER_SCOPE_CHANGE = "其他原因的合并范围变动"
    OTHER = "其他"


#: 六项的正文，按模板顺序。
SUB_TITLES: tuple[str, ...] = tuple(item.value for item in ScopeChangeItem)

#: 属于**企业合并类型**的那三项（`D-028` 的元素取值域）。
#:
#: 后三项（处置子公司 / 其他原因 / 其他）属**合并范围变动**，不在此列。
#: 把六项混成一个字段，`A-8` 那处真实假阴性就修不掉。
COMBINATION_ITEMS: tuple[ScopeChangeItem, ...] = (
    ScopeChangeItem.NON_COMMON_CONTROL_COMBINATION,
    ScopeChangeItem.COMMON_CONTROL_COMBINATION,
    ScopeChangeItem.REVERSE_ACQUISITION,
)


@dataclass(frozen=True)
class ScopeChangeReading:
    """一次「合并范围的变更」读数的完整留证。

    `undecidable=True` 时 `items` **必须是空的** —— 半份读数比没有读数更糟：
    它看起来像证据，而其中哪几项可信没人知道。
    """

    items: Mapping[ScopeChangeItem, bool]
    anchor_page: int | None
    page: int | None
    raw_lines: tuple[str, ...]
    undecidable: bool
    undecidable_reason: str = ""

    def __post_init__(self) -> None:
        if self.undecidable and self.items:
            raise ValueError(
                "undecidable 为真时 items 必须为空。"
                "半份读数看起来像证据，而其中哪几项可信没人知道。"
            )
        if not self.undecidable and len(self.items) != len(ScopeChangeItem):
            raise ValueError(
                f"可判定的读数必须含全部 {len(ScopeChangeItem)} 项，"
                f"实际 {len(self.items)} 项。子项缺一即拒绝返回部分结果 —— "
                "一份只填了一半的适用性表，读起来与「其余都不适用」无法区分。"
            )
        if self.undecidable and not self.undecidable_reason:
            raise ValueError(
                "undecidable 为真时必须给出理由。"
                "一个只有布尔没有理由的「不可判定」，复核者无从下手（L-9）。"
            )

    def to_dict(self) -> dict:
        return {
            "section_title": SECTION_TITLE,
            "items": {k.name: v for k, v in self.items.items()},
            "anchor_page": self.anchor_page,
            "page": self.page,
            "raw_lines": list(self.raw_lines),
            "undecidable": self.undecidable,
            "undecidable_reason": self.undecidable_reason,
        }


def scope_change_from_lines(
    texts: list[str],
    anchor_page: int | None,
    page: int | None,
    on_unreadable: str = "undecidable",
) -> ScopeChangeReading:
    """`read_scope_change` 的纯函数内核：**只吃行文本，不碰 PDF**。

    分出这一层的理由与 `locate.applicability_from_lines` 相同：
    让回归用例跑在**抽取产物**上，而不是每次重下 3.5 MB 的 PDF。

    `on_unreadable`：
    - `"undecidable"`（默认）—— 把 `ApplicabilityUnreadable` 转成 `undecidable=True`，
      **理由逐字进 `undecidable_reason`**。转换点全模块只有这一处。
    - `"raise"` —— 原样抛出。给需要看见底层异常的调用方（以及锁住「异常没被吞掉」的测试）。

    ⚠️ **默认不是「吞掉异常」**：`undecidable` 是一个会被写进证据链、
    并让下游拒答的值，不是一个被忽略的错误。两者的区别在于**它有没有出口**。
    """
    if on_unreadable not in ("undecidable", "raise"):
        raise ValueError(f"on_unreadable 只能是 'undecidable' 或 'raise'，实际 {on_unreadable!r}")

    try:
        from .locate import applicability_from_lines

        verdicts = applicability_from_lines(
            texts, SUB_TITLES, where=f"章节 {SECTION_TITLE!r}"
        )
    except ApplicabilityUnreadable as exc:
        if on_unreadable == "raise":
            raise
        return ScopeChangeReading(
            items={},
            anchor_page=anchor_page,
            page=page,
            raw_lines=tuple(texts),
            undecidable=True,
            undecidable_reason=str(exc),
        )

    return ScopeChangeReading(
        items={ScopeChangeItem(title): verdicts[title] for title in SUB_TITLES},
        anchor_page=anchor_page,
        page=page,
        raw_lines=tuple(texts),
        undecidable=False,
    )


def read_scope_change(pdf, y_tolerance: float | None = None) -> ScopeChangeReading:
    """读「合并范围的变更」六个子项。

    **找不到锚点即 `undecidable`，不退回全文搜索。** 见模块 docstring 第 3 条。
    """
    from .locate import DEFAULT_Y_TOLERANCE

    tolerance = DEFAULT_Y_TOLERANCE if y_tolerance is None else y_tolerance
    anchors = find_section_anchors(pdf, (SECTION_TITLE, NEXT_SECTION_TITLE), tolerance)
    section = [a for a in anchors if a.title == SECTION_TITLE]
    if not section:
        return ScopeChangeReading(
            items={},
            anchor_page=None,
            page=None,
            raw_lines=(),
            undecidable=True,
            undecidable_reason=(
                f"整份 PDF 里定位不到章节 {SECTION_TITLE!r} 的锚点。"
                "**不退回全文关键词搜索** —— 那会把「读不出来」变成"
                "「读出来了一个可能是错的值」，而 p77 的会计政策段落正等在那里（D-020）。"
            ),
        )
    if len(section) > 1:
        return ScopeChangeReading(
            items={},
            anchor_page=section[0].page,
            page=None,
            raw_lines=(),
            undecidable=True,
            undecidable_reason=(
                f"章节 {SECTION_TITLE!r} 命中 {len(section)} 次"
                f"（页码 {[a.page for a in section]}）。"
                "这里不替调用方选一个：目录页与正文页同名是真实存在的形态。"
            ),
        )

    anchor = section[0]
    nxt = next_anchor_after(anchors, anchor)
    texts, page = _lines_in_span(pdf, anchor, nxt, tolerance)
    return scope_change_from_lines(texts, anchor_page=anchor.page, page=page)


def _lines_in_span(
    pdf, anchor: SectionAnchor, nxt: SectionAnchor | None, y_tolerance: float
) -> tuple[list[str], int | None]:
    """`[anchor, next_anchor)` 区间内的行文本，以及第一行所在页。

    与 `locate.read_applicability` 用同一套区间语义。这里另取一份文本是因为
    本模块要把 `raw_lines` 留进证据链，而 `read_applicability` 只返回判定结果。
    """
    from .locate import _cluster_lines

    out: list[str] = []
    first_page: int | None = None
    last_page = len(pdf.pages) if nxt is None else nxt.page
    for page_number in range(anchor.page, last_page + 1):
        for line in _cluster_lines(pdf.pages[page_number - 1], page_number, y_tolerance):
            position = (page_number, line.y)
            if position <= (anchor.page, anchor.y):
                continue
            if nxt is not None and position >= (nxt.page, nxt.y):
                continue
            if first_page is None:
                first_page = page_number
            out.append(line.text)
    return out, first_page


def derive_consolidation_scope_change(reading: ScopeChangeReading) -> bool | None:
    """`notes.consolidation_scope_change` —— **六项任一为「适用」即 True**。

    判不了时返回 `None`，**不是 `False`**：见模块 docstring 末段。
    """
    if reading.undecidable:
        return None
    return any(reading.items.values())


def derive_business_combination_type(
    reading: ScopeChangeReading,
) -> frozenset[ScopeChangeItem] | None:
    """`notes.business_combination_type` —— **集合值**（`D-028`），空集 = 本期无企业合并。

    只由 `COMBINATION_ITEMS` 那三项决定。后三项属合并范围变动，**不得混进来**。

    为什么是集合不是单值：万华化学 2019 年报「合并范围的变更」里
    第 1 项（非同一控制下）与第 2 项（同一控制下）**同时为「√适用」** ——
    单值三选一里没有一个是对的。`D-028` 明写**集合性在世界里，不在重载里**。

    判不了时返回 `None`，与「空集」区分：空集是「读出来了，本期没有企业合并」。
    """
    if reading.undecidable:
        return None
    return frozenset(item for item in COMBINATION_ITEMS if reading.items[item])


#: 本模块产出的记录类别。写成常量而不是每处字面量：同名口径常量只允许一个定义点（`L-39`）。
RECORD_KIND = RecordKind.NOTE_CHECKBOX
