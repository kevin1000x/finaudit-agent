"""计量单位 —— **口径类开关缺失即 fail-closed**（`L-34` / SC-4）。

## 这个模块守的是一个「不会报错的错」

「单位大概是元」这个默认看起来永远安全 —— 直到遇到一份以**万元**列报的报表。
那时每个数都小 10000 倍，**而没有任何东西会不通过**：
资产负债表照样平（等式两边同时缩小 10000 倍），比率照样对（约掉了），
只有绝对金额是错的，且错得像一个正常的数。

⇒ 本模块的每一条负向用例，验的都是「读不出来时**抛错**而不是返回默认值」。
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from extractor.units import (
    UnitMismatchError,
    UnitScale,
    parse_unit_header,
    same_scale,
    scale_of,
    to_yuan,
)


# --------------------------------------------------------------------------
# 正向：真实版面上印的那几种写法
# --------------------------------------------------------------------------


def test_茅台资产负债表的表头(  ):
    """半角冒号。逐字取自茅台 2023 p58 的实测版面。"""
    assert parse_unit_header("单位:元 币种:人民币") == (UnitScale.YUAN, "人民币")


def test_全角冒号同样认得():
    """`(二) 主要财务指标` 那张表用的是全角冒号（p5 y=187.0 实测）。"""
    assert parse_unit_header("单位：万元 币种：人民币") == (UnitScale.WAN_YUAN, "人民币")


def test_编制单位不会被当成计量单位():
    """同一屏里还有「编制单位:贵州茅台酒股份有限公司」。

    不排除它就会把**公司名**当成计量单位 —— 而那个错误**不会报任何错**，
    它只是让每条记录的 `unit` 变成一句公司名。
    `locate.py` 实测踩过这个坑，这里是同一条负向前视的第二个消费点。
    """
    text = "编制单位:贵州茅台酒股份有限公司 单位:元 币种:人民币"
    assert parse_unit_header(text) == (UnitScale.YUAN, "人民币")


# --------------------------------------------------------------------------
# 负向：读不出来一律抛错，**不返回默认值**
# --------------------------------------------------------------------------


def test_空表头抛错而不是返回默认单位():
    """`L-34` 的核心用例：缺失即 fail-closed。"""
    with pytest.raises(UnitMismatchError, match="读不出计量单位与币种"):
        parse_unit_header("")


def test_只有空白的表头同样抛错():
    with pytest.raises(UnitMismatchError):
        parse_unit_header("   \n  ")


def test_只有单位没有币种抛错():
    """半边齐全**不算齐全** —— 缺币种时不补「人民币」。"""
    with pytest.raises(UnitMismatchError, match="币种"):
        parse_unit_header("单位:元")


def test_只有币种没有单位抛错():
    with pytest.raises(UnitMismatchError, match="计量单位"):
        parse_unit_header("币种:人民币")


def test_没见过的单位词抛错而不是猜一个系数():
    """`千元` 不在穷举表里。**不推断** —— 猜一个系数会让整批金额差若干个数量级。"""
    with pytest.raises(UnitMismatchError, match="不在穷举表"):
        parse_unit_header("单位:千元 币种:人民币")


def test_取值域里没有UNKNOWN成员():
    """加一个「未知」等于给调用方一个可以往下走的值。

    这里要的恰恰是走不下去 —— 未知的表达方式是**抛异常**，不是一个枚举值。
    """
    assert {m.name for m in UnitScale} == {"YUAN", "WAN_YUAN", "YI_YUAN"}


# --------------------------------------------------------------------------
# 归一化：跨源比较的前置
# --------------------------------------------------------------------------


def test_万元归一化到元是乘一万():
    assert to_yuan(Decimal("1.5"), UnitScale.WAN_YUAN) == Decimal("15000.0")


def test_亿元归一化到元():
    assert to_yuan(Decimal("2"), UnitScale.YI_YUAN) == Decimal("200000000")


def test_元归一化是恒等():
    assert to_yuan(Decimal("272699660092.25"), UnitScale.YUAN) == Decimal("272699660092.25")


def test_拒绝浮点入参():
    """二进制浮点的舍入漂移会直接污染「差多少算不一致」的判定。"""
    with pytest.raises(UnitMismatchError, match="必须是 Decimal"):
        to_yuan(1.5, UnitScale.WAN_YUAN)  # type: ignore[arg-type]


def test_单位系数就写在枚举值里():
    """`L-39`：同名口径常量只允许一个定义点。

    「元 / 万元 / 亿元」与它们的换算系数是同一个事实的两半，
    拆成「一个枚举 + 一张映射表」两处就会分叉。
    """
    assert UnitScale.YUAN.value == Decimal(1)
    assert UnitScale.WAN_YUAN.value == Decimal(10_000)
    assert UnitScale.YI_YUAN.value == Decimal(100_000_000)
    assert UnitScale.WAN_YUAN.printed == "万元"


# --------------------------------------------------------------------------
# 同一次运算里单位必须一致
# --------------------------------------------------------------------------


def test_单位一致时返回那个单位():
    assert same_scale("元", "元", "元") is UnitScale.YUAN


def test_单位不一致时抛错而不是替调用方换算():
    """换算会掩盖「这两个数本来就不该放在一起」这件事。"""
    with pytest.raises(UnitMismatchError, match="单位不一致"):
        same_scale("元", "万元")


def test_万元不会被元的子串匹配命中():
    """`scale_of` 是逐字相等，不是子串包含。

    子串包含的话「万元」会被「元」命中 —— 那正是 cninfo 用子串匹配对齐列名
    产出三处静默错误的形状。
    """
    assert scale_of("万元") is UnitScale.WAN_YUAN
    assert scale_of("元") is UnitScale.YUAN
    assert scale_of("万元") is not scale_of("元")


# --------------------------------------------------------------------------
# 接进计算路径：混单位的批次拒答
# --------------------------------------------------------------------------


def test_两条不同单位的记录参与同一次运算时拒答():
    """`compute_metric` 在读入边界拦下，不产出数值。"""
    import dataclasses
    import json
    from pathlib import Path

    from extractor.formula import compute_metric
    from extractor.mapping import load_pdf_mapping
    from extractor.pipeline import ExtractionSource, StatementView, extract_records
    from extractor.reconcile import reconcile_batch
    from extractor.record import SourceFreshness
    from semantic_layer.resolve import Refusal

    fixture = Path(__file__).parent / "fixtures" / "maotai_2023_bs_rows.json"
    data = json.loads(fixture.read_text(encoding="utf-8"))
    view = StatementView.from_dict(data)
    source = ExtractionSource(
        stock_code=data["source"]["stock_code"],
        fiscal_year=data["source"]["fiscal_year"],
        pdf_sha256=data["source"]["pdf_sha256"],
        source_url="file://fixture",
        freshness=SourceFreshness.REUSED_CACHED,
    )
    batch = extract_records(view, load_pdf_mapping("bs"), source)
    reconcile_batch(batch)
    # 先确认它本来算得出来 —— 否则下面那条断言可能是因为别的原因红的
    assert not isinstance(compute_metric("debt_to_asset_ratio", batch), Refusal)

    # 把其中一条记录的单位改成「万元」
    poisoned = dataclasses.replace(
        batch,
        records=[
            dataclasses.replace(r, unit="万元") if r.field_id == "bs.total_assets" else r
            for r in batch.records
        ],
    )
    outcome = compute_metric("debt_to_asset_ratio", poisoned)
    assert isinstance(outcome, Refusal), outcome
    assert "单位" in outcome.detail
    assert "万元" in outcome.detail
