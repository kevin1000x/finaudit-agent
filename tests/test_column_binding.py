"""列绑定 —— 「取的是对的那一列」这件事的机械保障（D-016 补充节 / 台账 A-9）。

## 本模块最要紧的一条测试，它的第二条断言看起来像写反了

`test_全取期初列时勾稽照样通过而列绑定不通过` 里有一句
`assert reconcile.passed is True`。**那不是笔误，它就是这条用例存在的理由。**

`A-9` 的推论在真实数据上确凿成立（茅台 2023 实测，两列都精确到 0.00）：

    期末列：272,699,660,092.25 = 49,043,190,797.43 + 223,656,469,294.82  差额 0.00
    期初列：254,500,826,096.02 = 49,562,744,832.16 + 204,938,081,263.86  差额 0.00

三个数**全取自期初列**时，勾稽闸门照样放行 —— 它证明的是「同一列内部自洽」，
不是「取的是对的那一列」。

`D-016` 补充节的判据原话是：存在一条回归用例，
**单独跑勾稽闸门不足以让该用例通过**——即证明这条用例查的是列绑定，不是恒等式。
上面那句 `passed is True` 就是这句话的可执行形态：它逐字证明了勾稽在这里无能为力。

⚠️ 后来的人若把它「修正」成 `is False`，这条用例就退化成又一次恒等式检查，
而列绑定从此无人看守 —— 那正是本项目反复记的那个形状
（自证机制说通过了，但它证明的不是它声称证明的事）。

## 固件

`tests/fixtures/maotai_2023_bs_rows.json`。它存的是**抽取产物**，
每一行连同**全部**单元格（期末列与期初列都在），所以「构造一个全取期初列的批次」
不需要额外造数据 —— 换一份 `column_header` 重跑即可。
"""

from __future__ import annotations

import dataclasses
import json
from decimal import Decimal
from pathlib import Path

import pytest

from extractor.mapping import load_pdf_mapping
from extractor.pipeline import ExtractionSource, StatementView, extract_records
from extractor.reconcile import check_column_binding, reconcile_batch
from extractor.record import SourceFreshness

FIXTURE = Path(__file__).parent / "fixtures" / "maotai_2023_bs_rows.json"
FISCAL_YEAR = 2023

#: 年报原文（p59 / p60 / p61 期末余额列），逐字。
PERIOD_END = {
    "bs.total_assets": Decimal("272699660092.25"),
    "bs.total_liabilities": Decimal("49043190797.43"),
    "bs.total_equity": Decimal("223656469294.82"),
}

#: 同三行的期初余额列。**它自己也平**——这正是勾稽闸门抓不到列错的原因。
PERIOD_BEGIN = {
    "bs.total_assets": Decimal("254500826096.02"),
    "bs.total_liabilities": Decimal("49562744832.16"),
    "bs.total_equity": Decimal("204938081263.86"),
}


@pytest.fixture
def view() -> StatementView:
    return StatementView.from_dict(json.loads(FIXTURE.read_text(encoding="utf-8")))


@pytest.fixture
def bs():
    return load_pdf_mapping("bs")


@pytest.fixture
def source() -> ExtractionSource:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))["source"]
    return ExtractionSource(
        stock_code=data["stock_code"],
        fiscal_year=data["fiscal_year"],
        pdf_sha256=data["pdf_sha256"],
        source_url="file://fixture",
        freshness=SourceFreshness.REUSED_CACHED,
    )


def _shifted_to_period_begin(mapping):
    """同一份映射表，把 `column_header` 全换成期初余额 —— 模拟「整列取错」。"""
    entries = tuple(
        dataclasses.replace(e, column_header="期初余额") for e in mapping.entries
    )
    return dataclasses.replace(mapping, entries=entries)


# --------------------------------------------------------------------------
# 正向：取到的是期末列，且值与年报原文逐字相等
# --------------------------------------------------------------------------


def test_三个恒等式字段取到的是期末余额列(view, bs, source):
    """逐个断言取到的**值**，不写一条「三个都对」的聚合断言（SC-8）。"""
    batch = extract_records(view, bs, source)
    assert batch.by_field("bs.total_assets").value == PERIOD_END["bs.total_assets"]
    assert batch.by_field("bs.total_liabilities").value == PERIOD_END["bs.total_liabilities"]
    assert batch.by_field("bs.total_equity").value == PERIOD_END["bs.total_equity"]


def test_记录里留的是版面上印的那串字不是口径名(view, bs, source):
    """`column_header` 记「2023年12月31日」而不是「期末余额」。

    理由写在 `pipeline._stamp_provenance` 的 docstring 里：这条记录要证明的是
    **取的是哪一列**，而口径名由 `field_id` + `mapping_version` 已可复原。
    记口径名等于把待证的结论当成证据。
    """
    batch = extract_records(view, bs, source)
    record = batch.by_field("bs.total_assets")
    assert record.column_header == "2023年12月31日"
    assert record.column_header != "期末余额"


def test_正常抽取时列绑定校验通过(view, bs, source):
    batch = extract_records(view, bs, source)
    result = check_column_binding(batch, bs, FISCAL_YEAR)
    assert result.passed is True
    assert result.checked == len(bs.entries)
    assert result.mismatches == ()


# --------------------------------------------------------------------------
# 🔴 核心用例：勾稽通过 ≠ 取对了列
# --------------------------------------------------------------------------


def test_全取期初列时勾稽照样通过而列绑定不通过(view, bs, source):
    """**第二条断言 `reconcile.passed is True` 不是笔误。** 见模块 docstring。

    `D-016` 补充节判据原话：**单独跑勾稽闸门不足以让该用例通过**。
    """
    shifted = _shifted_to_period_begin(bs)
    batch = extract_records(view, shifted, source)

    # 取到的确实是期初列的值 —— 先证明这个批次真的「取错了」
    assert batch.by_field("bs.total_assets").value == PERIOD_BEGIN["bs.total_assets"]
    assert batch.by_field("bs.total_liabilities").value == PERIOD_BEGIN["bs.total_liabilities"]
    assert batch.by_field("bs.total_equity").value == PERIOD_BEGIN["bs.total_equity"]

    # ① 勾稽闸门**照样放行**：期初列自己也平，差额精确为 0
    reconcile = reconcile_batch(batch, seal=False)
    assert reconcile.passed is True
    assert reconcile.difference == Decimal("0.00")

    # ② 列绑定校验**不通过** —— 拿真映射表（要期末余额）去校验这个批次
    binding = check_column_binding(batch, bs, FISCAL_YEAR)
    assert binding.passed is False
    mismatched_fields = {m[0] for m in binding.mismatches}
    assert "bs.total_assets" in mismatched_fields
    assert "bs.total_liabilities" in mismatched_fields
    assert "bs.total_equity" in mismatched_fields


def test_不通过时留证含版面原文与两个口径名(view, bs, source):
    """只报「口径不符」不够：复核者要能分辨是抽取器解错了还是映射表写错了。"""
    batch = extract_records(view, _shifted_to_period_begin(bs), source)
    binding = check_column_binding(batch, bs, FISCAL_YEAR)
    field_id, printed, resolved, expected = next(
        m for m in binding.mismatches if m[0] == "bs.total_assets"
    )
    assert field_id == "bs.total_assets"
    assert printed == "2022年12月31日"  # 版面原文
    assert resolved == "期初余额"  # 解出来的口径
    assert expected == "期末余额"  # 映射表要的口径


# --------------------------------------------------------------------------
# 表头继承：允许，但必须在证据里看得见
# --------------------------------------------------------------------------


def test_合并资产负债表的每一行都是继承来的表头(view, bs, source):
    """茅台 2023 的资产负债表表头在 **p58**，而 15 个字段全部落在 p59–p61。

    ⇒ 这张表上**没有一条「首页行」**。本测试先把这个事实钉住，
    「首页行 `header_inherited is False`」那一面由利润表提供（见下一条）——
    **一张表给不出两面时，不许把断言写成只查得到的那一面**。
    """
    batch = extract_records(view, bs, source)
    assert view.header.page == 58
    assert {r.page for r in batch.records} == {59, 60, 61}
    for record in batch.records:
        assert record.header_inherited is True, record.field_id


def test_利润表上首页行不继承而续页行继承(_income_batch):
    """cninfo `pdf_parser.py:302` 无条件把第 0 行当表头，续页因此**静默吃掉一行真实数据**。

    **显式判定 + 留证**的意思是：继承是允许的，但继承这件事本身必须在证据里看得见。
    合并利润表的表头在 p63，`is.*` 八个字段跨 p63 与 p64 —— 两面都在这一张表上。

    ⚠️ 这个布尔值 2026-08-27 之前**根本没进记录**：`ColumnBinding.inherited_to()`
    把它算了出来，而 `_stamp_provenance` 只取了 `column.header_text`，
    **算出来的留证在接线时被丢掉**（`ARCHITECTURE` §8.5 的形状）。
    是写这条测试当场抓出来的。
    """
    batch = _income_batch
    首页记录 = [r for r in batch.records if r.page == 63]
    续页记录 = [r for r in batch.records if r.page == 64]
    assert 首页记录, "合并利润表的表头页 p63 上应当有记录"
    assert 续页记录, "合并利润表的续页 p64 上应当有记录"
    for record in 首页记录:
        assert record.header_inherited is False, record.field_id
    for record in 续页记录:
        assert record.header_inherited is True, record.field_id


# --------------------------------------------------------------------------
# 同一行的两列：列绑定这件事最直接的证明位
# --------------------------------------------------------------------------


PROBE_FIXTURE = Path(__file__).parent / "fixtures" / "maotai_2023_probe_rows.json"


@pytest.fixture
def _income_batch():
    """合并利润表的抽取批次，跑在 wave 2 的探测固件上。"""
    data = json.loads(PROBE_FIXTURE.read_text(encoding="utf-8"))
    view = StatementView.from_dict(data["views"]["合并利润表"])
    source = ExtractionSource(
        stock_code=data["source"]["stock_code"],
        fiscal_year=data["source"]["fiscal_year"],
        pdf_sha256=data["source"]["pdf_sha256"],
        source_url="file://fixture",
        freshness=SourceFreshness.REUSED_CACHED,
    )
    return extract_records(view, load_pdf_mapping("is"), source, statement="合并利润表")


def test_营业收入本期与上期匹配同一行却取到不同的值(_income_batch):
    """`is.operating_revenue_current` 与 `..._prior_as_presented` 匹配的是**同一行**。

    它们的区别**只在 `column_header`**。两个字段全取上期列时，
    `revenue_growth_yoy` 会算出 0，而没有任何恒等式会不平 —— 这是 A-9 的原型。
    """
    batch = _income_batch
    mapping = load_pdf_mapping("is")

    current = batch.by_field("is.operating_revenue_current")
    prior = batch.by_field("is.operating_revenue_prior_as_presented")

    assert current.value == Decimal("147693604994.14")
    assert prior.value == Decimal("124099843771.99")
    assert current.value != prior.value
    # 同一行、同一页 —— 区别只在列
    assert current.page == prior.page
    assert current.column_header == "2023年度"
    assert prior.column_header == "2022年度"
    assert check_column_binding(batch, mapping, FISCAL_YEAR).passed is True
