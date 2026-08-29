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
    strip_invisible,
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


# --------------------------------------------------------------------------
# COLUMN_HEADER_PRESENCE —— 判某个列头在不在，不取任何行的值（01.5-07）
# --------------------------------------------------------------------------

#: 章节正文，不含序号。茅台 2023 排「七、」，跨公司会变（`C-2`）。
RESTATEMENT_SECTION_TITLE = "近三年主要会计数据和财务指标"

#: 区间右端点。实测下一章是「八、境内外会计准则下会计数据差异」（p6 y=77.7）。
RESTATEMENT_NEXT_SECTION_TITLE = "境内外会计准则下会计数据差异"

#: 判定要找的两个列头。**逐字**，取自 `data/mappings/pdf/notes.yaml` 的口径。
RESTATEMENT_HEADERS = ("调整后", "调整前")


@dataclass(frozen=True)
class RestatementReading:
    """「调整后 / 调整前」列头是否在场的一次判定。

    `restated is None` ⟺ `undecidable is True`。**两者必须同进同出** ——
    留下一个「判不了但给了个布尔」的中间态，下游没有任何办法察觉。
    """

    restated: bool | None
    anchor_page: int | None
    matched_lines: tuple[str, ...]
    matched_pages: tuple[int, ...]
    undecidable: bool
    undecidable_reason: str = ""

    def __post_init__(self) -> None:
        if self.undecidable != (self.restated is None):
            raise ValueError(
                f"undecidable={self.undecidable} 与 restated={self.restated!r} 不一致。"
                "判不了就必须没有布尔值，有布尔值就必须是判出来的。"
            )
        if self.undecidable and not self.undecidable_reason:
            raise ValueError("undecidable 为真时必须给出理由（L-9）")
        if self.restated is False and self.matched_lines:
            raise ValueError("判 False 却带着命中行，两者矛盾")

    def to_dict(self) -> dict:
        return {
            "field": "notes.restatement_flag",
            "restated": self.restated,
            "anchor_page": self.anchor_page,
            "matched_lines": list(self.matched_lines),
            "matched_pages": list(self.matched_pages),
            "undecidable": self.undecidable,
            "undecidable_reason": self.undecidable_reason,
        }


def restatement_from_lines(
    rows: "list[tuple[int, str]]",
    anchor_page: int | None,
    span_pages: "tuple[int, int] | None" = None,
) -> RestatementReading:
    """纯函数内核：吃 `(page, text)`，判两个列头在不在。

    ## 为什么 `False` 只在锚点定位成功时才允许返回

    🔴 **这一支的风险与复选项不同。** 复选项有 `√` / `□` 两个互斥标记，
    读不到标记就是读不到，二者在数据上可分。
    而列头只有「在」与「不在」—— **「不在」和「没读到」长得一样**。

    所以锚点没定到时返回的是 `undecidable`，不是 `False`。
    返回 `False` 等于宣称「这家公司本期没有追溯重述」，
    而我们其实只是没找到那一章。

    ## 为什么必须限定区间

    实测：整份茅台 2023 里「调整后」命中 **3 页 5 行**（p5 / p78 / p107），
    只有 p5 那 3 行在本章节内。**干扰项与目标字面完全相同** ——
    这比 p77 的会计政策段落更难查，因为连人工复核都分不出来。

    ⚠️ **单样本，跨排版未验证。** 「有 调整后/调整前 列 ⟺ 发生追溯重述」
    这条规则在茅台 2023 上成立，且与 p5 y=487.2 逐字写着的
    「本公司对比较期间相关财务数据进行追溯调整」互证；
    但**反例形态**（未重述却拆两列，或重述了却没拆）**一次都没观察到，也没有去找**。
    按 `F-1`，此处不写成「已验证」。
    """
    if anchor_page is None:
        return RestatementReading(
            restated=None,
            anchor_page=None,
            matched_lines=(),
            matched_pages=(),
            undecidable=True,
            undecidable_reason=(
                f"定位不到章节 {RESTATEMENT_SECTION_TITLE!r} 的锚点。"
                "**不据此判 False** —— 列头「不在」与「没读到」在数据上长得一样，"
                "而全篇「调整后」另有两页命中（p78 / p107），退回全篇搜索必然误判。"
            ),
        )

    lo, hi = span_pages if span_pages else (anchor_page, None)
    matched: list[str] = []
    pages: list[int] = []
    for page, text in rows:
        if page < lo or (hi is not None and page > hi):
            continue
        cleaned = strip_invisible(text)
        if any(header in cleaned for header in RESTATEMENT_HEADERS):
            matched.append(text)
            pages.append(page)

    return RestatementReading(
        restated=bool(matched),
        anchor_page=anchor_page,
        matched_lines=tuple(matched),
        matched_pages=tuple(dict.fromkeys(pages)),
        undecidable=False,
    )


def read_restatement_flag(pdf, y_tolerance: float | None = None) -> RestatementReading:
    """`notes.restatement_flag` —— 从 PDF 读。区间语义与 `read_scope_change` 相同。"""
    from .locate import DEFAULT_Y_TOLERANCE

    tolerance = DEFAULT_Y_TOLERANCE if y_tolerance is None else y_tolerance
    anchors = find_section_anchors(
        pdf, (RESTATEMENT_SECTION_TITLE, RESTATEMENT_NEXT_SECTION_TITLE), tolerance
    )
    section = [a for a in anchors if a.title == RESTATEMENT_SECTION_TITLE]
    if len(section) != 1:
        return restatement_from_lines([], anchor_page=None)

    anchor = section[0]
    nxt = next_anchor_after(anchors, anchor)
    texts, _ = _lines_in_span(pdf, anchor, nxt, tolerance)
    last_page = len(pdf.pages) if nxt is None else nxt.page
    rows = _rows_in_span(pdf, anchor, nxt, tolerance)
    return restatement_from_lines(
        rows, anchor_page=anchor.page, span_pages=(anchor.page, last_page)
    )


def _rows_in_span(pdf, anchor, nxt, y_tolerance) -> "list[tuple[int, str]]":
    """`[anchor, next_anchor)` 区间内的 `(page, text)`。"""
    from .locate import _cluster_lines

    out: list[tuple[int, str]] = []
    last_page = len(pdf.pages) if nxt is None else nxt.page
    for page_number in range(anchor.page, last_page + 1):
        for line in _cluster_lines(pdf.pages[page_number - 1], page_number, y_tolerance):
            position = (page_number, line.y)
            if position <= (anchor.page, anchor.y):
                continue
            if nxt is not None and position >= (nxt.page, nxt.y):
                continue
            out.append((page_number, line.text))
    return out


# --------------------------------------------------------------------------
# REPORT_METADATA —— 由报告类型派生，**不从版面取值**（01.5-07）
# --------------------------------------------------------------------------


class ReportType(Enum):
    """本项目实际处理的报告类型。**只登记真的会走到的那些。**

    多登记几种（半年报 / 季报）看起来更完备，实际是在为一条**没有任何代码路径
    会到达**的规则维护取值域 —— 那条规则不被任何东西校验，会一直活着
    直到有人当它是对的。要加，先让抽取链路真的支持那种报告。
    """

    ANNUAL = "annual"


#: 报告类型 → 报告期月份数。**穷举，没有 fallback。**
_PERIOD_MONTHS = {ReportType.ANNUAL: 12}


def derive_reporting_period_months(report_type) -> int:
    """`notes.reporting_period_months` —— **由报告类型派生，纸上不印这一行。**

    `PROBE-14 §3` 实测：整份 143 页逐行搜四个候选串**全部零命中**。它不在版面上。

    ⇒ 实现是一张穷举表加一条「不认识就抛」。**不许 fallback 到 12。**
    一个「大概是年报所以 12」的默认，与 `units.py` 那条「单位大概是元」
    是同一个形状：**错了也没有任何东西会报错。**
    """
    if not isinstance(report_type, ReportType):
        raise ValueError(
            f"报告类型 {report_type!r} 不在穷举表 {[t.value for t in ReportType]} 内。"
            "**不回退到 12** —— 一个猜出来的报告期会让所有时段类指标静默错档。"
        )
    return _PERIOD_MONTHS[report_type]


def reporting_period_months_provenance(report_type) -> dict:
    """这个值的出处。**留证里必须看得出它不是从版面上取来的。**

    混同「抽取到的」与「派生的」，复核者会去年报上找这一行 —— 而它不存在。
    """
    return {
        "field": "notes.reporting_period_months",
        "value": derive_reporting_period_months(report_type),
        "derived": True,
        "extracted_from_layout": False,
        "report_type": report_type.value,
        "note": (
            "由报告类型派生：年度报告 ⇒ 12。**这一行不在纸上** —— "
            "PROBE-14 §3 逐行搜四个候选串全部零命中。按 D-026 第 1 类，"
            "SC-2 计数时走作废通道。"
        ),
    }
