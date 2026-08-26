"""章节定位与行重组的回归 —— 台账 A-6 的三条**实测**失效模式各一条。

固件是 `tests/fixtures/maotai_2023_bs_rows.json`，即贵州茅台 2023 年报
（SHA-256 `2125ff97…`）经 `python -m extractor extract --dump-view` 产出的**抽取产物**。
PDF 本身永远不进版本控制（`.gitignore` 与 `scan_rules.yaml` 两处都挡着），
所以回归跑在产物上，不跑在 PDF 上。

A-6 明写「探测跑通 ≠ 有回归用例」。本文件就是把那次探测变成回归用例的地方。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from extractor.locate import (
    NUMERIC_CELL_RE,
    Cell,
    ColumnBinding,
    ReconstructedRow,
    StatementAnchor,
    _stitch,
    parse_amount,
)
from extractor.pipeline import StatementView

FIXTURE = Path(__file__).parent / "fixtures" / "maotai_2023_bs_rows.json"


@pytest.fixture(scope="module")
def raw() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def view(raw) -> StatementView:
    return StatementView.from_dict(raw)


@pytest.fixture(scope="module")
def anchors(raw) -> list[StatementAnchor]:
    return [
        StatementAnchor(
            title=a["title"],
            page=int(a["page"]),
            y=float(a["y"]),
            is_consolidated=bool(a["is_consolidated"]),
        )
        for a in raw["anchors"]
    ]


def _row(view: StatementView, *fragments: str) -> ReconstructedRow:
    hits = [r for r in view.rows if r.label_lines == fragments]
    assert len(hits) == 1, f"{fragments} 在区间内命中 {len(hits)} 行，期望恰好 1 行"
    return hits[0]


# --------------------------------------------------------------------------
# 锚点
# --------------------------------------------------------------------------


def test_茅台2023定位到八个锚点且合并恰有四个(anchors):
    """CONTEXT §3.1 实测：8 张报表标题全部定位，合并与母公司干净分离。

    2026-08-16 的探测用 pdfplumber 0.11.5，本仓库装的是 0.11.10，
    这条断言同时把「换了小版本结果没变」钉住。
    """
    assert len(anchors) == 8
    assert sum(1 for a in anchors if a.is_consolidated) == 4
    assert {a.title for a in anchors if a.is_consolidated} == {
        "合并资产负债表",
        "合并利润表",
        "合并现金流量表",
        "合并所有者权益变动表",
    }


def test_审计报告正文里的表名不构成锚点(anchors):
    """p55 审计报告正文含「……的合并及母公司资产负债表，2023年度的……」。

    `extract_words` 把那整段当成**一个词**，子串包含会认成一个锚点，
    随后整张表定位到错误的区间。整词逐字相等不会中招。
    """
    assert all(a.page != 55 for a in anchors)
    assert [a.page for a in anchors if a.title == "母公司资产负债表"] == [61]


# --------------------------------------------------------------------------
# 失效模式 1：表标题印在上一页
# --------------------------------------------------------------------------


def test_表标题印在上一页时行区间照样跨页归属(view):
    """失效模式 1：锚点所在页与数值所在页不同 —— D-019 拆两个整数的理由。

    茅台 2023 的「合并资产负债表」标题印在 p58 的 `top=662.3 / 841.9`
    （页面下五分之一，即页脚位置），其后同页只跟得下两行（章节小标题「流动资产：」
    与第一个行项目「货币资金」）。
    `资产总计` / `负债合计` / `所有者权益（或股东权益）合计` 分别落在 p59 / p60 / p61。

    若实现要求「标题与数据必须同页」，这三个字段全部取不到 —— 这正是
    第一版探测直接零命中的成因之一。
    """
    assert view.anchor.page == 58
    assert view.anchor.y > 0.75 * 841.9, "标题不在页面下四分之一，本用例的前提不成立"

    total_assets = _row(view, "资产总计")
    assert total_assets.page == 59
    assert total_assets.page != view.anchor.page

    pages = {r.page for r in view.rows}
    assert pages == {58, 59, 60, 61}, f"区间应跨 58–61 四页，实际 {sorted(pages)}"
    on_title_page = [r.label_lines for r in view.rows if r.page == 58]
    assert on_title_page == [("流动资产：",), ("货币资金",)], (
        f"标题同页应当只跟得下两行，实际 {on_title_page}"
    )


# --------------------------------------------------------------------------
# 失效模式 2：合并表与母公司表的边界落在页内
# --------------------------------------------------------------------------


def test_合并与母公司的边界落在页内时按y归属(view, anchors):
    """失效模式 2：p61 上半是合并表尾巴，下半是母公司表标题。

    按「页」定位必然混表 —— 这正是 cninfo `extract_financial_statements()`
    「最后一个匹配的表静默胜出」的成因（D-013 / CONTEXT §6）。

    负控制在下面一条：同页且 y 更大的母公司行**不得**落进本区间。
    """
    parent = next(a for a in anchors if a.title == "母公司资产负债表")
    assert parent.page == 61, "母公司表标题不在 p61，本用例的前提不成立"

    same_page_rows = [r for r in view.rows if r.page == 61]
    assert same_page_rows, "合并表在 p61 上应当还有尾巴"
    assert max(r.y for r in same_page_rows) < parent.y

    equity = _row(view, "所有者权益（或股东权", "益）合计")
    assert equity.page == 61 and equity.y < parent.y


def test_母公司表的资产总计不得落进合并表区间(view):
    """负控制（J-5）：混表时最先串味的就是这一行。

    母公司资产总计 171,584,366,864.08 印在 p62，与合并的 272,699,660,092.25
    只差一个区间右端点。按页定位会把它一起收进来，`资产总计` 随后命中两行。
    """
    hits = [r for r in view.rows if r.label_lines == ("资产总计",)]
    assert len(hits) == 1
    assert hits[0].cells[0].text == "272,699,660,092.25"
    assert all(c.text != "171,584,366,864.08" for r in view.rows for c in r.cells)


# --------------------------------------------------------------------------
# 失效模式 3：标签折行，数值行夹在两个片段之间
# --------------------------------------------------------------------------


def test_标签折行时三行缝合为一个行项目(view):
    """失效模式 3 的真实形态（茅台 2023 p61）：

        归属于母公司所有者权益
        215,668,571,607.43   197,480,041,239.46
        （或股东权益）合计

    逐行读会得到「一个没有数的标签」加「一个没有标签的数」。
    缝合后 `label_lines` 长度为 2，且**保持原顺序、不拼接**。
    """
    row = _row(view, "归属于母公司所有者权益", "（或股东权益）合计")
    assert len(row.label_lines) == 2
    assert row.label_lines[0] == "归属于母公司所有者权益"
    assert [c.text for c in row.cells] == ["215,668,571,607.43", "197,480,041,239.46"]
    assert row.page == 61


def test_缝合只在标签行数值行标签行三连时发生():
    """负控制：普通的「标签行 → 标签行」不得被缝合。

    茅台 p59 上有一长串「行在、格子空」的项目连续出现（结算备付金、衍生金融资产……）。
    如果缝合规则只看「相邻的两个标签行」，它们会被两两粘起来，
    整张表的行项目数会少掉一半，而没有任何东西会报错。
    """
    raw = [
        ("结算备付金", (), 59, 78.5),
        ("衍生金融资产", (), 59, 121.6),
        ("应收款项融资", (), 59, 164.7),
    ]
    rows = _stitch(raw)
    assert len(rows) == 3
    assert all(len(r.label_lines) == 1 for r in rows)


def test_缝合不跨页():
    """三行必须同页。跨页折行在本样本上没有观察到，故不预写对策（F-2）。"""
    raw = [
        ("归属于母公司所有者权益", (), 60, 800.0),
        ("", (Cell("1.00", 313.0, 408.0),), 61, 85.3),
        ("（或股东权益）合计", (), 61, 92.1),
    ]
    rows = _stitch(raw)
    assert len(rows) == 3, "跨页的三行不应被缝合"


# --------------------------------------------------------------------------
# 列绑定：显式判定 + 留证
# --------------------------------------------------------------------------


def test_列由表头文字绑定且判定依据被记下来(view):
    """列的语义角色不靠列序号。判定用了哪条规则记进 `resolution`。

    茅台的资产负债表表头印的是日期而不是「期末余额」，
    对应关系由「年份等于本次抽取的会计年度」这个**事实比对**给出，不是启发式。
    """
    end = view.header.by_role("期末余额")
    begin = view.header.by_role("期初余额")
    assert end.header_text == "2023年12月31日"
    assert begin.header_text == "2022年12月31日"
    assert end.resolution == "fiscal-year-match"
    assert view.header.by_role("不存在的口径") is None


def test_附注编号列不会被认成金额列(view):
    """附注列的表头是「附注」，两条角色规则都不适用 ⇒ `role` 为 None。

    它绝不能被当成期末余额列：那样取到的会是一串附注编号，
    而勾稽闸门对「1 = 25 + 30」这种式子只会报不通过，报不出「取错了列」。
    """
    note_column = next(c for c in view.header.columns if c.header_text == "附注")
    assert note_column.role is None
    assert note_column.resolution == "unrecognized"


def test_续页无表头时列绑定继承首页并留证(view):
    """茅台 p59–p60 是裸续页（不重复表头）。

    cninfo `pdf_parser.py:302` 无条件把第 0 行当表头，续页表格因此**静默吃掉
    一行真实数据**，而它的文档宣称「支持跨页表格识别」（CONTEXT §6）。
    这里继承是显式的，且 `header_inherited` 把这次继承记进了证据。
    """
    end = view.header.by_role("期末余额")
    assert end.page == 58 and end.header_inherited is False
    inherited = end.inherited_to(60)
    assert inherited.header_inherited is True
    assert inherited.page == 60
    assert inherited.x0 == end.x0 and inherited.header_text == end.header_text
    assert end.inherited_to(58) is end, "同页不产生继承"


def test_数值右缘超出表头右缘时仍归得进那一列(view):
    """实测：表头 `2023年12月31日` x=[307,395]，其下数值右对齐到 408。

    用「包含」判定列归属，这张表一个格子都归不进去。所以用横向重叠取最大。
    """
    end = view.header.by_role("期末余额")
    row = _row(view, "资产总计")
    cell = row.cell_in(end)
    assert cell is not None
    assert cell.x1 > end.x1, "本用例的前提是数值右缘确实超出表头右缘"
    assert cell.text == "272,699,660,092.25"


# --------------------------------------------------------------------------
# 单位与币种：抽不到即 fail-closed
# --------------------------------------------------------------------------


def test_单位与币种取自表头且不是编制单位那一行(view):
    """同一屏里还有「编制单位:贵州茅台酒股份有限公司」。

    不排除它就会把公司名当成金额单位 —— 而那个错误**不报任何错**，
    正是 L-34 说的「静默取一个值」。
    """
    assert view.header.unit == "元"
    assert view.header.currency == "人民币"


# --------------------------------------------------------------------------
# 数值格子的判定
# --------------------------------------------------------------------------


def test_数值正则要求两位小数因而排掉附注编号():
    for text in ("272,699,660,092.25", "-6,061,727.51", "0.00"):
        assert NUMERIC_CELL_RE.match(text), text
    for text in ("5", "56(1)", "2023年12月31日", "资产总计", "143"):
        assert not NUMERIC_CELL_RE.match(text), text


def test_金额用十进制解析不用二进制浮点():
    """金额上的舍入漂移会直接污染勾稽差额的判定。"""
    from decimal import Decimal

    assert parse_amount("-6,061,727.51") == Decimal("-6061727.51")
    assert parse_amount("0.10") + parse_amount("0.20") == Decimal("0.30")


def test_重叠为零的单元格不归入任何列():
    column = ColumnBinding(
        header_text="2023年12月31日",
        role="期末余额",
        x0=307.0,
        x1=395.0,
        page=58,
        header_inherited=False,
        resolution="fiscal-year-match",
    )
    row = ReconstructedRow(
        label_lines=("某行",),
        cells=(Cell("1.00", 430.0, 525.0),),
        page=59,
        y=100.0,
    )
    assert row.cell_in(column) is None
