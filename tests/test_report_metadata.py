"""`COLUMN_HEADER_PRESENCE` 与 `REPORT_METADATA` 两支 `kind`（`01.5-07`）。

这两支此前**不属于任何一份 PLAN**（`N-43`）——「三支由 `01.5-05` 实现」
是一句比 PLAN 晚两天写的代码注释编出来的。操作者 2026-08-28 裁决新写一份并进 wave 5。

它们解掉的是 `COMPUTED-VALUES §2` 记的那个缺口：
**8 个指标里 6 个的数值算得出来，而它们的 `restated` 可比性标记判不了。**
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from extractor.notes import (
    RESTATEMENT_HEADERS,
    RESTATEMENT_NEXT_SECTION_TITLE,
    RESTATEMENT_SECTION_TITLE,
    ReportType,
    RestatementReading,
    derive_reporting_period_months,
    restatement_from_lines,
)

FIXTURE = Path(__file__).parent / "fixtures" / "maotai_2023_restatement.json"


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _rows() -> list[tuple[int, str]]:
    return [(r["page"], r["text"]) for r in _fixture()["lines"]]


def _reading() -> RestatementReading:
    fx = _fixture()
    return restatement_from_lines(_rows(), anchor_page=fx["anchor_page"])


# --------------------------------------------------------------------------
# 一、COLUMN_HEADER_PRESENCE：列头的字面在场
# --------------------------------------------------------------------------


def test_茅台2023判为已追溯重述且证据带列头原文与页码():
    reading = _reading()
    assert reading.undecidable is False
    assert reading.restated is True
    assert reading.anchor_page == 5
    assert reading.matched_lines, "证据不能为空 —— 判 True 却给不出依据等于没有证据"
    assert set(reading.matched_pages) == {5}
    # 列头原文逐字在证据里
    assert any(RESTATEMENT_HEADERS[0] in line for line in reading.matched_lines)


def test_章节区间外的调整后不被计入():
    """🔴 实测：整份茅台 2023 里「调整后」命中 **3 页 5 行**（p5 / p78 / p107）。

    只有 p5 那 3 行在「近三年主要会计数据和财务指标」区间内。
    按关键词全篇搜会多出两页的假阳性 —— 与 p77 会计政策段落是同一个陷阱，
    只不过这次干扰项与目标**字面完全相同**，连人工复核都分不出来。
    """
    rows = _rows()
    # 章节区间跨 p5–p6（下一章「八、境内外会计准则下会计数据差异」在 p6），
    # 而三处列头全在 p5。**区间是两页，命中是一页** —— 两者不该混为一谈。
    assert {page for page, _ in rows} == {5, 6}, "固件是区间内的行，区间跨两页"
    assert {page for page, text in rows if "调整后" in text} == {5}

    # 把区间外的两页塞进来，判定结果不变、证据里也不该出现它们
    polluted = rows + [(78, "调整后调整前"), (107, "调整后")]
    reading = restatement_from_lines(rows, anchor_page=5)
    polluted_reading = restatement_from_lines(polluted, anchor_page=5, span_pages=(5, 6))
    assert polluted_reading.restated is True
    assert 78 not in polluted_reading.matched_pages
    assert 107 not in polluted_reading.matched_pages
    assert polluted_reading.matched_pages == reading.matched_pages


def test_锚点缺失时判不了而不是判否():
    """🔴 **这一支的风险与复选项不同。**

    复选项有 `√` / `□` 两个互斥标记，读不到标记就是读不到。
    而列头只有「在」与「不在」——**「不在」和「没读到」长得一样**。
    所以 `False` 只在章节锚点定位成功的前提下才允许返回。
    """
    reading = restatement_from_lines(_rows(), anchor_page=None)
    assert reading.undecidable is True
    assert reading.restated is None
    assert reading.undecidable_reason


def test_章节在但区间内无列头时判否_这与判不了是两回事():
    reading = restatement_from_lines(
        [(5, "本年度未进行追溯调整"), (5, "营业收入")], anchor_page=5
    )
    assert reading.undecidable is False
    assert reading.restated is False
    assert reading.matched_lines == ()
    # 与上一条对照：同样是「没有 True」，但一个可判定一个不可判定
    assert reading.restated is not None


def test_两个列头名都逐字取自映射口径():
    assert RESTATEMENT_HEADERS == ("调整后", "调整前")
    assert RESTATEMENT_SECTION_TITLE == "近三年主要会计数据和财务指标"
    assert RESTATEMENT_NEXT_SECTION_TITLE == "境内外会计准则下会计数据差异"


def test_跨排版限定写在实现里而不是只写在文档里():
    """`F-1`：不许在任何地方把这条规则写成「已验证」。

    ⚠️ **本条 2026-08-31 换了锁的对象，因为被锁的那句话过期了。**
    原来锁的是「**反例形态一次都没观察到，也没有去找**」——
    **去找了**：顺丰控股 002352 · 2021 那份表一个「调整后」都没有，
    而 p12 注文逐字写着「公司无需追溯调整或重述以前年度会计数据」，
    **真值就是 `False`**，规则给出的也是 `False`。

    **前提消失不等于限定消失。** 现在锁的是更新之后那三条限定 ——
    三家公司两个模板不叫「跨排版已验证」、另一种反例仍是零样本、
    以及顺丰那份是靠补入第二种标题措辞才判得出来的。
    限定一旦从代码里消失，下一个人读到的就是一条无条件成立的规则。
    """
    import extractor.notes as notes

    source = Path(notes.__file__).read_text(encoding="utf-8")
    assert "不许写成「已验证」" in source
    assert "另一种反例仍是零样本" in source
    assert "三家公司、两个模板" in source
    # 旧那句必须**不在**了 —— 它现在是一句假话，留着比没有更糟。
    assert "一次都没观察到，也没有去找" not in source


# --------------------------------------------------------------------------
# 二、REPORT_METADATA：由报告类型派生，不从版面取值
# --------------------------------------------------------------------------


def test_年度报告的报告期是十二个月():
    assert derive_reporting_period_months(ReportType.ANNUAL) == 12


def test_不认识的报告类型抛异常而不是回退到十二():
    """**不许有 fallback 到 12。**

    一个「大概是年报所以 12」的默认，与 `units.py` 那条「单位大概是元」
    是同一个形状：错了也没有任何东西会报错。
    """
    with pytest.raises(ValueError, match="报告类型"):
        derive_reporting_period_months("interim")
    with pytest.raises(ValueError):
        derive_reporting_period_months(None)


def test_实现里没有任何在版面上搜这个值的代码路径():
    """`PROBE-14 §3` 实测：整份 143 页逐行搜四个串**全部零命中**。它不在纸上。

    这一支最容易做错的方式是**给它编一条版面规则**（`F-2`）。
    本条锁住实现里没有那条路径 —— 注释里提到这些词是允许的（要解释为什么不搜），
    但可执行代码里不许出现。
    """
    import ast

    import extractor.notes as notes

    tree = ast.parse(Path(notes.__file__).read_text(encoding="utf-8"))
    literals = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]
    # docstring 是 Constant，但它不是可执行的搜索路径；只查**非 docstring** 的字面量
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc:
                docstrings.add(doc)
    executable = [s for s in literals if s not in docstrings]
    for banned in ("月份数", "报告期涵盖", "报告期月", "涵盖的月"):
        assert not any(banned in s for s in executable), (
            f"实现里出现了版面搜索用的字面量 {banned!r} —— 这个值不在纸上（PROBE-14 §3）"
        )


def test_派生值标注为派生而不是抽取():
    """留证里必须看得出这个数**不是从版面上取来的**。

    混同「抽取到的」与「派生的」，复核者会去年报上找这一行，而它不存在。
    """
    from extractor.notes import reporting_period_months_provenance

    prov = reporting_period_months_provenance(ReportType.ANNUAL)
    assert prov["derived"] is True
    assert prov["extracted_from_layout"] is False
    assert prov["value"] == 12
    assert "不在纸上" in prov["note"] or "报告类型" in prov["note"]


# --------------------------------------------------------------------------
# 跨公司实证（2026-08-31）：三份真实年报，两个交易所模板
# --------------------------------------------------------------------------

_CORPUS = (
    ("600519", 2023, True, "上交所：`七、 近三年主要会计数据和财务指标`"),
    ("600309", 2019, True, "上交所：同上"),
    ("002352", 2021, False, "深交所：`主要会计数据和财务指标`，**无「近三年」**"),
)


@pytest.mark.parametrize("code, year, expected, note", _CORPUS)
def test_三份真实年报上的判定与年报自述一致(code, year, expected, note):
    """🔴 **这三条是 `VERIFICATION.md` §C.7 那条证据缺口的收口。**

    原本记着「反例形态从未被观察到，也没有去找过」。去找了：
    顺丰 002352 · 2021 那份表**一个「调整后」都没有**，
    而 p12 注文逐字写着「**公司无需追溯调整或重述以前年度会计数据**」——
    **真值就是 `False`**，这也是 `restated is False` 这条分支
    **第一次被真实数据走到**。

    ⚠️ 期望值不是照抄抽取器的输出，是照抄**年报自己说的话**：
    茅台 p5「本公司对比较期间相关财务数据进行追溯调整」⇒ `True`；
    顺丰 p12「公司无需追溯调整或重述以前年度会计数据」⇒ `False`。

    ## 为什么这三条必须跑真 PDF，而不是跑固件

    本模块其余的回归都跑在 `maotai_2023_restatement.json` 上 —— 那份固件存的是
    **区间内的行**，驱动的是 `restatement_from_lines`（判定逻辑）。
    **而 2026-08-31 改的是上一层：章节锚点的标题匹配。**
    固件从锚点之后才开始，**覆盖不到那处改动** ——
    拿固件去验它，等于验了一件与改动无关的事。

    ## 代价，如实写在这里

    这三条把本地全量套件从约 **77 秒**拉到约 **162 秒**（三份 PDF 共 638 页的解析）。
    ⚠️ **CI 不受影响**：`data/raw/` 从不进版本控制，CI 上这三条一律 `skip`。
    ⇒ 付这个时间的只有本机，而本机正是唯一有语料、也唯一能验这件事的地方。
    """
    pdf_path = Path(__file__).resolve().parent.parent / "data" / "raw" / f"{code}_{year}.pdf"
    if not pdf_path.exists():
        pytest.skip(f"本机语料不在：{pdf_path}（PDF 永不进版本控制）")
    import pdfplumber

    from extractor.notes import read_restatement_flag

    with pdfplumber.open(str(pdf_path), password="") as pdf:
        reading = read_restatement_flag(pdf)

    assert not reading.undecidable, f"{code} {year} 判不出（{note}）：{reading.undecidable_reason}"
    assert reading.restated is expected, f"{code} {year} 判成 {reading.restated}，与年报自述不符"
    # `False` 必须不带命中行 —— 这条不变量此前只有构造样本走过。
    if expected is False:
        assert reading.matched_lines == ()


def test_两种标题措辞都在册且不许退化成子串匹配():
    """`近三年…` 包含 `主要会计数据…`，子串匹配看起来能一石二鸟。

    **但本模块的锚点判定靠的正是「整行逐字相等（或序号 + 逐字相等）」**，
    改成子串会同时命中正文里任何提到这几个字的行 ——
    放弃逐字，就等于放弃 `C-2` 那条「对序号容差、对正文逐字」。
    """
    from extractor.notes import RESTATEMENT_SECTION_TITLE, RESTATEMENT_SECTION_TITLES

    assert RESTATEMENT_SECTION_TITLE in RESTATEMENT_SECTION_TITLES
    assert "主要会计数据和财务指标" in RESTATEMENT_SECTION_TITLES
    assert len(RESTATEMENT_SECTION_TITLES) == 2
    # 两种措辞是**包含关系**，这正是不能改成子串匹配的原因 —— 把这件事本身钉住。
    assert RESTATEMENT_SECTION_TITLES[1] in RESTATEMENT_SECTION_TITLE
