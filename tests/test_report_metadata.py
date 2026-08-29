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


def test_单样本这条限定写在实现里而不是只写在文档里():
    """`F-1`：「有 调整后/调整前 列 ⟺ 发生追溯重述」这条规则**反例形态一次都没观察到**。

    不许在任何地方把它写成「已验证」。这条测试锁住那句限定确实还在源码里 ——
    限定一旦从代码里消失，下一个人读到的就是一条无条件成立的规则。
    """
    import extractor.notes as notes

    source = Path(notes.__file__).read_text(encoding="utf-8")
    assert "跨排版未验证" in source
    assert "反例形态" in source


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
