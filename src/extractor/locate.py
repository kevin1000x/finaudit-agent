"""章节定位、列绑定与行重组 —— 三条**实测**失效模式各有对策。

本模块把一份年报 PDF 的版面变成「锚点 + 列绑定 + 重组行」三样结构化事实。
它**不认识任何字段**：`bs.total_assets` 这类 id 只出现在 `mapping.py`，
本模块只产出「第几页第几行印着哪些字，落在哪一列里」。

## 三条失效模式（CONTEXT §3.2 / 台账 A-6，2026-08-16 实测撞出来的）

**第一版探测因为它们直接零命中。** 逐条对策：

1. **表标题印在页脚位置，数据落在其后的页上。**
   ⇒ 任何「标题与数据必须同页」的规则必然落空。
   本模块的处置是：锚点只记 `(page, y)`，行区间是 `[本锚点, 下一锚点)`，
   **跨页**。锚点所在页与数值所在页天然可以不同 —— 这正是 D-019 要拆
   `page` 与 `anchor_page` 两个整数的原因。
   *本样本上的实际形态*：茅台 2023 的「合并资产负债表」标题印在 p58 的
   `top=662.3 / 841.9`（页面下五分之一），其后同页只跟得下一行数据，
   `资产总计` / `负债合计` / `所有者权益（或股东权益）合计`
   分别落在 p59 / p60 / p61。若要求「标题与数据同页」，这三个字段全部取不到。

2. **合并表与母公司表的边界落在页内。**
   ⇒ 按「页」定位必然混表。这正是 cninfo `extract_financial_statements()`
   「最后一个匹配的表静默胜出」的成因（D-013）。
   本模块的处置是：区间按 `y` 切，**允许页内切分**。
   *本样本上的实际形态*：p61 的 `top<234.3` 是合并资产负债表的尾巴
   （含 `所有者权益（或股东权益）合计`），`top>234.3` 是母公司资产负债表的开头。

3. **行项目标签折行，数值行夹在两个标签片段之间。**
   ⇒ 逐行读会得到「一个没有数的标签」加「一个没有标签的数」。
   本模块的处置是 `标签行 → 纯数值行 → 标签行` 三行缝合，
   `label_lines` 保留**两个片段**且保持原顺序，**不做拼接** ——
   拼接就等于本模块替映射表决定了折行处该不该补字，那是 `mapping.py` 的事。
   *本样本上的实际形态*（p61）：
       归属于母公司所有者权益
       215,668,571,607.43   197,480,041,239.46
       （或股东权益）合计

## 表头识别是**显式判定 + 留证**，不是默认

CONTEXT §6 记着 cninfo `pdf_parser.py:302` 无条件把第 0 行当表头
（`pd.DataFrame(table[1:], columns=table[0])`），续页表格因此**静默吃掉一行真实数据**，
而它的文档宣称「支持跨页表格识别」。

所以这里：表头行由「含 `项目` 这个词」显式判定；续页没有表头时**不重新猜**，
而是继承首页绑定并把 `header_inherited` 置 True，让证据链看得见这次继承。

## 列的语义角色不靠列序号，也不靠猜

`ColumnBinding.role` 只由两条**写死的**规则产生，且把用了哪条记进 `resolution`：

- `literal` —— 表头文字逐字就是「期末余额」/「期初余额」
- `fiscal-year-match` —— 表头文字形如 `2023年12月31日`，其**年份等于本次抽取的会计年度**
  即为期末余额，等于会计年度减一即为期初余额

第二条不是「取靠右那一列」也不是「取较晚的日期」这类启发式：会计年度是调用方传进来的
已知量，年份相等是一个**事实比对**。两条都不适用时 `role` 为 None，
由调用方 fail-closed，**不取一个「合理默认」**（L-34）。

## 本模块明确**不**做

- 不做 OCR（CONTEXT §5：先只处理文本型 PDF）
- 不跨页缝合折行标签。三行必须同页，否则不缝。跨页折行在本样本上未观察到，
  **没观察到的形态不预先写对策** —— 那会得到一条永远不会正确触发的规则（F-2）。
- 不认识字段 id，不做任何标签匹配。那是 `mapping.py` 的事。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

__all__ = [
    "STATEMENT_TITLES",
    "CONSOLIDATED_TITLES",
    "DEFAULT_Y_TOLERANCE",
    "NUMERIC_CELL_RE",
    "SheetHeaderNotFound",
    "Cell",
    "StatementAnchor",
    "ColumnBinding",
    "SheetHeader",
    "ReconstructedRow",
    "find_statement_anchors",
    "bind_columns",
    "rows_in_span",
    "parse_amount",
]

# --------------------------------------------------------------------------
# 常量。**同名口径常量只允许一个定义点**（L-39）——版面口径的唯一定义点在这里。
# --------------------------------------------------------------------------

#: 八条报表标题。**顺序即证监会披露顺序**，但定位不依赖顺序。
STATEMENT_TITLES = (
    "合并资产负债表",
    "母公司资产负债表",
    "合并利润表",
    "母公司利润表",
    "合并现金流量表",
    "母公司现金流量表",
    "合并所有者权益变动表",
    "母公司所有者权益变动表",
)

CONSOLIDATED_TITLES = frozenset(t for t in STATEMENT_TITLES if t.startswith("合并"))

#: y 容差。CONTEXT §3.1 实测 2.0–5.0 之间结果稳定，取中值。
DEFAULT_Y_TOLERANCE = 3.0

#: 数值单元格。**要求两位小数** —— 附注编号列的 `5` / `56(1)` 天然不匹配。
#: 这只是第一道防线：A-6 明写它是单样本结论，遇到列出整数金额的报表会失效。
#: 真正的列筛选靠 `bind_columns` 的表头绑定，本正则只负责排掉明显不是金额的格子。
NUMERIC_CELL_RE = re.compile(r"^-?[\d,]+\.\d{2}$")

#: 「单位:元 币种:人民币」。**抽不到即 fail-closed，不设默认值**（L-34 / SC-4）。
#:
#: 负向前视 `(?<!编制)` 是实测踩出来的：同一屏里还有一行「编制单位:贵州茅台酒股份
#: 有限公司」，不排除它就会把公司名当成金额单位 —— 而那个错误**不会报任何错**，
#: 它只是让每条记录的 `unit` 变成一句公司名，恰是 L-34 说的「静默取一个值」的形态。
_UNIT_RE = re.compile(r"(?<!编制)单位[:：]\s*(\S+)")
_CURRENCY_RE = re.compile(r"币种[:：]\s*(\S+)")

#: 表头行的判定锚：报表表头第一格逐字是「项目」。
_HEADER_MARKER = "项目"

#: 表头文字 → 语义角色的两条规则（见模块 docstring）。
_LITERAL_ROLES = {
    "期末余额": "期末余额",
    "期初余额": "期初余额",
    "上年年末余额": "期初余额",
}
_DATE_HEADER_RE = re.compile(r"^(\d{4})年\d{1,2}月\d{1,2}日$")

#: 非数据行：书眉与页脚。**显式按文字形态剔除，不按 y 的魔法阈值剔除。**
#: 页脚形如 `58 / 143`，被 `extract_words` 拆成三个词，故按整行文本判。
_RUNNING_HEAD_RE = re.compile(r"^\d{4}年年度报告$")
_PAGE_FOOTER_RE = re.compile(r"^\d+\s*/\s*\d+$")

#: 表头之后、数据之前的说明行，不参与行重组。
_SHEET_META_PREFIXES = ("编制单位", "单位:", "单位：", "币种")


class SheetHeaderNotFound(LookupError):
    """在锚点之后找不到表头行 / 单位 / 币种。

    **不是配置缺陷**：这说明这份 PDF 的版面与实测形态不符，即「够不着那份数据」。
    由 `pipeline` 转成 `Refusal(UNAVAILABLE)`，不抛给用户看 traceback（D-022 决策二）。
    """


# --------------------------------------------------------------------------
# 结构
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Cell:
    """一个数值单元格连同它的横向位置。位置是列归属的唯一依据。"""

    text: str
    x0: float
    x1: float

    @property
    def amount(self) -> Decimal:
        return parse_amount(self.text)


@dataclass(frozen=True)
class StatementAnchor:
    """一条报表标题，**带 y 坐标**。行区间 = `[本锚点, 下一锚点)`。

    `y` 用 pdfplumber 的 `top`（自页顶向下），故同页内 `y` 越小越靠上。
    """

    title: str
    page: int
    y: float
    is_consolidated: bool

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "page": self.page,
            "y": round(self.y, 2),
            "is_consolidated": self.is_consolidated,
        }


@dataclass(frozen=True)
class ColumnBinding:
    """一列，由**表头文字**绑定，不由列序号绑定（D-016 补充节）。

    `header_inherited` 是留证字段：续页不重复表头时它为 True，
    证据链据此看得见「这一行的列归属是继承来的，不是这一页上读到的」。
    """

    header_text: str
    role: str | None
    x0: float
    x1: float
    page: int
    header_inherited: bool
    resolution: str

    def inherited_to(self, page: int) -> "ColumnBinding":
        """把首页绑定继承到续页。**产出一个新对象并留证**，不就地改。"""
        if page == self.page:
            return self
        return ColumnBinding(
            header_text=self.header_text,
            role=self.role,
            x0=self.x0,
            x1=self.x1,
            page=page,
            header_inherited=True,
            resolution=self.resolution,
        )

    def overlap(self, cell: Cell) -> float:
        """与一个单元格的横向重叠宽度。

        **不用「包含」判定**：实测中数值右缘超出表头右缘 9–13 pt
        （表头 `2023年12月31日` x=[307,395]，其下数值 x=[313,408]，右对齐到 408）。
        用包含会一个格子都归不进去。
        """
        return max(0.0, min(self.x1, cell.x1) - max(self.x0, cell.x0))

    def to_dict(self) -> dict:
        return {
            "header_text": self.header_text,
            "role": self.role,
            "x0": round(self.x0, 2),
            "x1": round(self.x1, 2),
            "page": self.page,
            "header_inherited": self.header_inherited,
            "resolution": self.resolution,
        }


@dataclass(frozen=True)
class SheetHeader:
    """一张报表的表头：单位、币种与全部列绑定。

    `unit` / `currency` 没有默认值。抽不到就抛 `SheetHeaderNotFound`，
    绝不取「元 / 人民币」这个看起来一定对的默认 —— L-34 要防的正是这个动作。
    """

    unit: str
    currency: str
    columns: tuple[ColumnBinding, ...]
    page: int
    y: float

    def by_role(self, role: str) -> ColumnBinding | None:
        for column in self.columns:
            if column.role == role:
                return column
        return None

    @property
    def label_max_x(self) -> float:
        """标签区的右边界 = 最左一列表头的左缘。

        CONTEXT §3.2 写着「按列位置剔除更稳妥」。这就是那个列位置：
        它左边的字是行项目标签，右边的是附注编号与金额。
        """
        return min(column.x0 for column in self.columns)

    def to_dict(self) -> dict:
        return {
            "unit": self.unit,
            "currency": self.currency,
            "page": self.page,
            "y": round(self.y, 2),
            "columns": [c.to_dict() for c in self.columns],
        }


@dataclass(frozen=True)
class ReconstructedRow:
    """一个行项目。折行的标签保留**多个片段**，不拼接。

    `page` / `y` 取**数值所在那一行**的位置：证据链要指的是数印在哪儿，
    而不是标签的第一个片段印在哪儿。无数值时取第一个标签片段的位置。
    """

    label_lines: tuple[str, ...]
    cells: tuple[Cell, ...]
    page: int
    y: float

    def cell_in(self, column: ColumnBinding) -> Cell | None:
        """落在该列里的单元格；**取重叠最大的那个**，无重叠即 None。"""
        best, best_overlap = None, 0.0
        for cell in self.cells:
            overlap = column.overlap(cell)
            if overlap > best_overlap:
                best, best_overlap = cell, overlap
        return best

    def to_dict(self) -> dict:
        return {
            "label_lines": list(self.label_lines),
            "cells": [{"text": c.text, "x0": round(c.x0, 2), "x1": round(c.x1, 2)} for c in self.cells],
            "page": self.page,
            "y": round(self.y, 2),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ReconstructedRow":
        return cls(
            label_lines=tuple(data["label_lines"]),
            cells=tuple(Cell(c["text"], float(c["x0"]), float(c["x1"])) for c in data["cells"]),
            page=int(data["page"]),
            y=float(data["y"]),
        )


def parse_amount(text: str) -> Decimal:
    """`-6,061,727.51` → `Decimal('-6061727.51')`。

    用 `Decimal` 不用二进制浮点：金额上的舍入漂移会直接污染勾稽差额的判定。
    """
    try:
        return Decimal(text.replace(",", ""))
    except InvalidOperation as exc:  # pragma: no cover - 正则已挡住，留作防御
        raise ValueError(f"{text!r} 不是可解析的金额") from exc


# --------------------------------------------------------------------------
# 版面原语
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class _TextLine:
    """一条按 y 聚簇出来的原始行。内部用，不出模块。"""

    words: tuple[dict, ...]
    page: int
    y: float

    @property
    def text(self) -> str:
        return "".join(w["text"] for w in self.words)


def _cluster_lines(page, page_number: int, y_tolerance: float) -> list[_TextLine]:
    """把一页的词按 `top` 聚簇成行，容差 `y_tolerance`。

    折行标签的三行间距实测约 6.8 pt，正常行距约 14.4 pt，
    都大于容差 3.0，所以缝合靠的是**行序模式**，不是靠把它们聚成一行。
    """
    words = sorted(page.extract_words(), key=lambda w: (w["top"], w["x0"]))
    lines: list[list[dict]] = []
    anchor_top: float | None = None
    for word in words:
        if anchor_top is None or word["top"] - anchor_top > y_tolerance:
            lines.append([word])
            anchor_top = word["top"]
        else:
            lines[-1].append(word)
    out = []
    for group in lines:
        group.sort(key=lambda w: w["x0"])
        out.append(_TextLine(words=tuple(group), page=page_number, y=group[0]["top"]))
    return out


def _is_chrome(line: _TextLine) -> bool:
    """书眉 / 页脚 / 表头说明行 —— 不是数据行。"""
    text = line.text
    if _RUNNING_HEAD_RE.match(text) or _PAGE_FOOTER_RE.match(text):
        return True
    return text.startswith(_SHEET_META_PREFIXES)


# --------------------------------------------------------------------------
# 锚点
# --------------------------------------------------------------------------


def find_statement_anchors(pdf, y_tolerance: float = DEFAULT_Y_TOLERANCE) -> list[StatementAnchor]:
    """八条报表标题的锚点，按 `(page, y)` 升序。

    判定是**整词逐字相等**，不是子串包含。理由是实测的反例：茅台 2023 的 p55
    审计报告正文里有一句「……月31日的合并及母公司资产负债表，2023年度的合并及母公司
    利润表、合并及母公司现金流量……」，`extract_words` 把它整段当成**一个词**。
    子串包含会把审计报告正文认成一个锚点，随后整张表定位到错误的区间。
    """
    anchors: list[StatementAnchor] = []
    for page_number, page in enumerate(pdf.pages, start=1):
        for word in page.extract_words():
            title = word["text"]
            if title in STATEMENT_TITLES:
                anchors.append(
                    StatementAnchor(
                        title=title,
                        page=page_number,
                        y=float(word["top"]),
                        is_consolidated=title in CONSOLIDATED_TITLES,
                    )
                )
    anchors.sort(key=lambda a: (a.page, a.y))
    return anchors


def next_anchor_after(
    anchors: list[StatementAnchor], anchor: StatementAnchor
) -> StatementAnchor | None:
    """区间右端点。**允许与 `anchor` 同页**（失效模式 2）。"""
    ordered = sorted(anchors, key=lambda a: (a.page, a.y))
    for candidate in ordered:
        if (candidate.page, candidate.y) > (anchor.page, anchor.y):
            return candidate
    return None


# --------------------------------------------------------------------------
# 列绑定
# --------------------------------------------------------------------------


def _role_of(header_text: str, fiscal_year: int) -> tuple[str | None, str]:
    """表头文字 → `(role, resolution)`。两条规则都不适用时 `role` 为 None。"""
    if header_text in _LITERAL_ROLES:
        return _LITERAL_ROLES[header_text], "literal"
    match = _DATE_HEADER_RE.match(header_text)
    if match:
        year = int(match.group(1))
        if year == fiscal_year:
            return "期末余额", "fiscal-year-match"
        if year == fiscal_year - 1:
            return "期初余额", "fiscal-year-match"
        return None, "fiscal-year-mismatch"
    return None, "unrecognized"


def bind_columns(
    pdf,
    anchor: StatementAnchor,
    fiscal_year: int,
    y_tolerance: float = DEFAULT_Y_TOLERANCE,
    search_lines: int = 12,
) -> SheetHeader:
    """锚点之后第一屏里显式找表头，连同单位与币种。

    找不到表头、找不到单位或币种，一律抛 `SheetHeaderNotFound`。
    **不补默认值** —— 「单位大概是元」这种默认正是 L-34 点名要防的动作，
    它会让一份以万元列报的报表静默产出小 10000 倍的结论。
    """
    page = pdf.pages[anchor.page - 1]
    lines = [line for line in _cluster_lines(page, anchor.page, y_tolerance) if line.y > anchor.y]
    lines = lines[:search_lines]

    # 逐**词**匹配，不逐行匹配：`单位:元` 与 `币种:人民币` 是同一行上的两个词，
    # 拼成一行后 `\S+` 会贪掉后半截，把单位读成 `元币种:人民币`（实测踩过）。
    unit = currency = None
    for line in lines:
        for word in line.words:
            text = word["text"]
            if unit is None:
                m = _UNIT_RE.search(text)
                if m:
                    unit = m.group(1)
            if currency is None:
                m = _CURRENCY_RE.search(text)
                if m:
                    currency = m.group(1)

    header_line = None
    for line in lines:
        if any(word["text"] == _HEADER_MARKER for word in line.words):
            header_line = line
            break

    if header_line is None:
        raise SheetHeaderNotFound(
            f"锚点 {anchor.title!r}（p{anchor.page} y={anchor.y:.1f}）之后 "
            f"{search_lines} 行内找不到含 {_HEADER_MARKER!r} 的表头行。"
            "表头必须显式判定 —— 无条件拿第一行当表头正是 cninfo pdf_parser.py:302 "
            "静默吃掉一行真实数据的成因（CONTEXT §6）。"
        )
    if unit is None or currency is None:
        raise SheetHeaderNotFound(
            f"锚点 {anchor.title!r}（p{anchor.page}）之后读不到"
            f"{'单位' if unit is None else ''}{'与' if unit is None and currency is None else ''}"
            f"{'币种' if currency is None else ''}。"
            "口径类开关缺失即在读入边界 fail-closed，不取「元 / 人民币」这个合理默认（L-34 / SC-4）。"
        )

    columns = []
    for word in header_line.words:
        text = word["text"]
        if text == _HEADER_MARKER:
            continue
        role, resolution = _role_of(text, fiscal_year)
        columns.append(
            ColumnBinding(
                header_text=text,
                role=role,
                x0=float(word["x0"]),
                x1=float(word["x1"]),
                page=anchor.page,
                header_inherited=False,
                resolution=resolution,
            )
        )
    return SheetHeader(
        unit=unit,
        currency=currency,
        columns=tuple(columns),
        page=anchor.page,
        y=header_line.y,
    )


# --------------------------------------------------------------------------
# 行重组
# --------------------------------------------------------------------------


def _split_line(line: _TextLine, label_max_x: float) -> tuple[str, tuple[Cell, ...]]:
    """一条原始行 → `(标签文本, 数值单元格)`。

    标签是**表头最左一列左缘以左**的字。这条界线来自表头绑定，不是猜的，
    也不是按「第几个词」切的 —— 附注编号列与金额列的词数逐行都不一样。
    """
    label_parts, cells = [], []
    for word in line.words:
        text = word["text"]
        if float(word["x1"]) <= label_max_x:
            label_parts.append(text)
        elif NUMERIC_CELL_RE.match(text):
            cells.append(Cell(text=text, x0=float(word["x0"]), x1=float(word["x1"])))
    return "".join(label_parts), tuple(cells)


def rows_in_span(
    pdf,
    anchor: StatementAnchor,
    next_anchor: StatementAnchor | None,
    header: SheetHeader,
    y_tolerance: float = DEFAULT_Y_TOLERANCE,
) -> list[ReconstructedRow]:
    """`[anchor, next_anchor)` 区间内的重组行。**跨页，且允许页内切分。**

    区间的两端都按 `(page, y)` 比较，所以：

    - `next_anchor` 与 `anchor` 同页时，只有 `y` 小于它的行属于本区间（失效模式 2）
    - `next_anchor` 在若干页之后时，中间整页都属于本区间（失效模式 1）

    `header` 的表头行本身以及它上面的说明行不算数据行。
    """
    last_page = len(pdf.pages) if next_anchor is None else next_anchor.page
    label_max_x = header.label_max_x

    raw: list[tuple[str, tuple[Cell, ...], int, float]] = []
    for page_number in range(anchor.page, last_page + 1):
        page = pdf.pages[page_number - 1]
        for line in _cluster_lines(page, page_number, y_tolerance):
            position = (page_number, line.y)
            if position <= (anchor.page, anchor.y):
                continue
            if next_anchor is not None and position >= (next_anchor.page, next_anchor.y):
                continue
            if page_number == header.page and line.y <= header.y:
                continue
            if _is_chrome(line):
                continue
            label, cells = _split_line(line, label_max_x)
            if not label and not cells:
                continue
            raw.append((label, cells, page_number, line.y))

    return _stitch(raw)


def _stitch(raw: list[tuple[str, tuple[Cell, ...], int, float]]) -> list[ReconstructedRow]:
    """缝合失效模式 3：`标签行 → 纯数值行 → 标签行` 三行属同一个行项目。

    三行**必须同页**。跨页折行在本样本上没有观察到，
    没观察到的形态不预先写对策 —— 那会得到一条永远不会正确触发的规则（F-2）。
    """
    rows: list[ReconstructedRow] = []
    index = 0
    while index < len(raw):
        label, cells, page, y = raw[index]
        is_label_only = bool(label) and not cells
        if is_label_only and index + 2 < len(raw):
            mid_label, mid_cells, mid_page, mid_y = raw[index + 1]
            tail_label, tail_cells, tail_page, _tail_y = raw[index + 2]
            numeric_only = not mid_label and bool(mid_cells)
            tail_is_label_only = bool(tail_label) and not tail_cells
            same_page = page == mid_page == tail_page
            if numeric_only and tail_is_label_only and same_page:
                rows.append(
                    ReconstructedRow(
                        label_lines=(label, tail_label),
                        cells=mid_cells,
                        page=mid_page,
                        y=mid_y,
                    )
                )
                index += 3
                continue
        rows.append(
            ReconstructedRow(
                label_lines=(label,) if label else (),
                cells=cells,
                page=page,
                y=y,
            )
        )
        index += 1
    return rows
