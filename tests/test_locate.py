"""章节定位与行重组的回归 —— 台账 A-6 的三条**实测**失效模式各一条。

固件是 `tests/fixtures/maotai_2023_bs_rows.json`，即贵州茅台 2023 年报
（SHA-256 `2125ff97…`）经 `python -m extractor extract --dump-view` 产出的**抽取产物**。
PDF 本身永远不进版本控制（`.gitignore` 与 `scan_rules.yaml` 两处都挡着），
所以回归跑在产物上，不跑在 PDF 上。

A-6 明写「探测跑通 ≠ 有回归用例」。本文件就是把那次探测变成回归用例的地方。
"""

from __future__ import annotations

import json
from decimal import Decimal
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

REPO = Path(__file__).resolve().parent.parent

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


# --------------------------------------------------------------------------
# 报表锚点限定在「财务报表」这一节内（2026-08-31，万华 2019 实测逼出来的）
# --------------------------------------------------------------------------


def test_报表锚点被限定在财务报表那一节内():
    """🔴 **这条不是假想风险，是万华 2019 上的真实拒答。**

    `find_statement_anchors` 按**整词逐字**认标题，于是**附注正文里提到的报表名
    也会成为锚点**。万华 600309 · 2019 上「合并资产负债表」定位到 **3 个**：
    p71 是真标题，另外两个在 p112 ——
    一句 `2018年12月31 日受影响的合并资产负债表和母公司资产负债表：`
    与一张对照表的列头行 `合并资产负债表    母公司资产负债表`。

    ⇒ `read_statement` 的「恰好 1 个」判定不通过，
    **整条计算在第二家公司上直接拒答**（`RefusalCode.UNAVAILABLE`，退 3）。

    限定区间 `[二、财务报表, 三、公司基本情况)` 之后：
    茅台 p58–p75、万华 p71–p87，两家的八个报表锚点都落在各自区间内，
    p112 / p116 那三处被挡在外面。
    """
    import pdfplumber

    from extractor import locate
    from extractor.mapping import load_pdf_mapping, match_row
    from extractor.pipeline import _statements_section_span, read_statement

    for code, year, expect in (("600519", 2023, (58, 75)), ("600309", 2019, (71, 87))):
        path = REPO / "data" / "raw" / f"{code}_{year}.pdf"
        if not path.exists():
            pytest.skip(f"本机语料不在：{path}（PDF 永不进版本控制）")
        with pdfplumber.open(str(path), password="") as pdf:
            span = _statements_section_span(pdf, locate.DEFAULT_Y_TOLERANCE)
            assert span is not None, f"{code} 定位不到「财务报表」这一节"
            start, end = span
            assert (start.page, None if end is None else end.page) == expect
            # 三张合并报表在**两家**上都各自恰好定位到一个锚点。
            for statement in ("合并资产负债表", "合并利润表", "合并现金流量表"):
                view = read_statement(pdf, statement, year)
                assert start.page <= view.anchor.page < end.page
                assert view.rows, f"{code} {statement} 区间内零行"

            # 顺带在**同一次解析**上考映射覆盖 —— 不另开一次 PDF（213 页解析不便宜）。
            # `bs` 的 15 条在两家上都必须全命中且**不多命中**：
            # 多命中意味着标签变体互相串了，那比零命中更危险（会静默取错行）。
            bs_view = read_statement(pdf, "合并资产负债表", year)
            table = load_pdf_mapping("bs", REPO / "data" / "mappings" / "pdf")
            for entry in table.for_statement("合并资产负债表"):
                hits = [r for r in bs_view.rows if match_row(r, entry)]
                assert len(hits) == 1, f"{code} {entry.field_id} 命中 {len(hits)} 行，期望恰好 1"


def test_万华2019的三个比率算得出且勾稽通过():
    """🔴 **第二家公司第一次算出真实财务比率。**

    2026-08-31 之前，`VERIFICATION.md` §C.1 记的是「万华只测过合并范围的变更那一节」。
    补了两条标签变体（`bs.total_equity` 无「合计」、`is.net_profit` 不折行）之后，
    `bs` 的 15 条在万华上全命中。

    ⚠️ **期望值独立可核**：万华 2019 p73 印着
    负债和所有者权益总计 `96,865,322,655.29`、所有者权益 `43,931,258,971.63`
    ⇒ 负债 = 52,934,063,683.66 ⇒ 资产负债率 = **0.5465**。
    本条断言的是这个数，不是照抄抽取器的输出。
    """
    import hashlib

    import pdfplumber

    from extractor.formula import compute_metrics
    from extractor.mapping import load_pdf_mapping
    from extractor.pipeline import ExtractionSource, extract_records, read_statement
    from extractor.reconcile import reconcile_batch
    from extractor.record import SourceFreshness

    path = REPO / "data" / "raw" / "600309_2019.pdf"
    if not path.exists():
        pytest.skip(f"本机语料不在：{path}（PDF 永不进版本控制）")

    source = ExtractionSource(
        stock_code="600309",
        fiscal_year=2019,
        pdf_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        source_url=f"file://{path.as_posix()}",
        freshness=SourceFreshness.REUSED_CACHED,
    )
    table = load_pdf_mapping("bs", REPO / "data" / "mappings" / "pdf")
    with pdfplumber.open(str(path), password="") as pdf:
        view = read_statement(pdf, "合并资产负债表", 2019)
        batch = extract_records(view, table, source, "合并资产负债表")

    gate = reconcile_batch(batch)
    assert gate.passed, f"万华勾稽不通过，差额 {gate.difference}"
    assert gate.difference == Decimal("0.00")

    outcome = compute_metrics(["debt_to_asset_ratio"], batch, REPO / "metrics")[0]
    assert round(outcome.value, 4) == Decimal("0.5465")


def test_定位不到那一节时退回今天的行为而不是拒答():
    """⚠️ 这与 `read_restatement_flag` 那条「不退回全篇搜索」看起来相反，实则不同。

    那里退回全篇会**产出一个错误答案**（区间外的「调整后」会让它误判 `True`）；
    这里退回全篇只是回到**加这一层之前就在跑的**那条路，
    而那条路遇歧义（锚点不唯一）**本来就拒答**。
    ⇒ 加这一层是**严格收窄**，不引入任何新的静默失败。**本条把这个性质钉住。**
    """
    import inspect

    from extractor import pipeline

    source = inspect.getsource(pipeline.read_statement)
    # 找不到区间时必须是「不过滤」，不是「抛异常」。
    assert "if span is not None:" in source
    assert "raise" not in source.split("if span is not None:")[0]


def test_同一口径解出多列时抛错而不是挑第一个():
    """🔴 **万华 2019 实测出来的静默歧义。**

    它的合并资产负债表**有三列**，而其中**两列被解到同一个口径**：

    ```
    2019年12月31日 -> 期末余额
    2018年12月31日 -> 期初余额
    2018年1月1日   -> 期初余额     ← 与上一列同 role
    ```

    原实现是「遍历，返回第一个匹配的」⇒ **静默返回排在前面的那一列**。
    今天没有任何字段映射到 `期初余额`，所以没有产出错数 —— **但那是运气，不是设计**。
    「在两个候选里挑一个报」正是 `F-2` 的形状，而它一旦发生，
    表现形式是「取到了一个看起来合理的数」，没有任何东西会说出来。

    ⚠️ 抛错而不是返回 `None`：两者原因不同、处置也不同 ——
    「表头里没有这个口径」是映射表或版面的问题；
    「同一个口径解出两列」是**我们的列解析规则在这份版面上不够细**。
    """
    import pdfplumber

    from extractor.locate import AmbiguousColumnRole
    from extractor.pipeline import read_statement

    path = REPO / "data" / "raw" / "600309_2019.pdf"
    if not path.exists():
        pytest.skip(f"本机语料不在：{path}（PDF 永不进版本控制）")

    with pdfplumber.open(str(path), password="") as pdf:
        view = read_statement(pdf, "合并资产负债表", 2019)

    # 唯一的那个仍然取得到 —— 不许因为「有歧义」把好的一并挡掉。
    assert view.header.by_role("期末余额").header_text == "2019年12月31日"
    with pytest.raises(AmbiguousColumnRole, match="解出了 2 列"):
        view.header.by_role("期初余额")
    # 取不到仍然是 `None`，不是抛错 —— 两条路径必须分开。
    assert view.header.by_role("不存在的口径") is None
