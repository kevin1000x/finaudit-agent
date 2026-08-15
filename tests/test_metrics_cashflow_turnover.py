"""01-06 批次：现金流与周转 7 个指标的行为测试。

行数据全部为**内存构造的合成样例**，不来自任何年报、AKShare 或其他第三方源，
也不引入任何外部数据文件（D-010）。数值只为触发/不触发特定分支而设，无真实公司含义。

本文件另有两条超出单批次的断言：
- 现金循环周期必须**打不中**（OQ-01：它是 C2 类拒答题的真实靶子，不是编造的）
- 三份周转天数的 365 基数与期末立场逐份显式，不靠继承批次约定
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from semantic_layer.definition import load_definition  # noqa: E402
from semantic_layer.resolve import (  # noqa: E402
    Refusal,
    RefusalCode,
    Registry,
    active_flags,
    evaluate_refusal,
)
from semantic_layer.stats import collect_pitfall_stats  # noqa: E402
from semantic_layer.validate import validate_definition  # noqa: E402
from semantic_layer.vocabulary import load_vocabulary  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
METRICS = REPO_ROOT / "metrics"
VOCAB = load_vocabulary(METRICS / "_flags.yaml")

BATCH = [
    "operating_cash_flow_ratio",
    "ocf_to_net_profit_attributable",
    "free_cash_flow",
    "inventory_turnover_days",
    "accounts_receivable_turnover_days",
    "accounts_payable_turnover_days",
    "total_asset_turnover",
]
BATCH_PATHS = [METRICS / f"{name}.yaml" for name in BATCH]

TURNOVER_DAYS = [
    "inventory_turnover_days",
    "accounts_receivable_turnover_days",
    "accounts_payable_turnover_days",
]


def _defn(name):
    return load_definition(METRICS / f"{name}.yaml")


@pytest.fixture(scope="module")
def registry():
    return Registry.load(METRICS)


# --------------------------------------------------------------------------
# 合规性与解析
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", BATCH)
def test_definition_is_conformant(name):
    findings = validate_definition(_defn(name), VOCAB)
    assert findings == [], f"{name} 不合规：{[f.code for f in findings]}"


@pytest.mark.parametrize(
    "alias,expected",
    [
        ("经营现金流量比率", "operating_cash_flow_ratio"),
        ("净现比", "ocf_to_net_profit_attributable"),
        ("自由现金流", "free_cash_flow"),
        ("存货周转天数", "inventory_turnover_days"),
        ("应收账款周转天数", "accounts_receivable_turnover_days"),
        ("应付账款周转天数", "accounts_payable_turnover_days"),
        ("总资产周转率", "total_asset_turnover"),
    ],
)
def test_alias_resolves(registry, alias, expected):
    got = registry.resolve(alias)
    assert not isinstance(got, Refusal), got
    assert got.metric_id == expected


def test_overly_broad_alias_not_registered(registry):
    """POC-01 S2：不收录「现金流量比率」——它也可指投资/筹资活动的现金流量比率。"""
    assert isinstance(registry.resolve("现金流量比率"), Refusal)


# --------------------------------------------------------------------------
# 经营现金流量比率：POC-01 三条单方缺陷的修复
# --------------------------------------------------------------------------


def _ocfr_row(**overrides):
    row = {
        "cfs.net_cash_flow_from_operating_activities": 500,
        "bs.total_current_liabilities_period_end": 2000,
        "notes.reporting_period_months": 12,
    }
    row.update(overrides)
    return row


def test_ocf_ratio_refuses_missing_numerator():
    """S3：缺失与为 0 分两条路径。"""
    row = _ocfr_row()
    del row["cfs.net_cash_flow_from_operating_activities"]
    refusal = evaluate_refusal(_defn("operating_cash_flow_ratio"), row)
    assert isinstance(refusal, Refusal)
    assert refusal.code is RefusalCode.UNDEFINED_CONDITION_HIT


def test_ocf_ratio_accepts_zero_numerator():
    """经营现金流恰为 0 是真实结论，不拒答。与上一条同时通过才算 S3 修好。"""
    row = _ocfr_row(**{"cfs.net_cash_flow_from_operating_activities": 0})
    assert evaluate_refusal(_defn("operating_cash_flow_ratio"), row) is None


def test_ocf_ratio_accepts_negative_numerator():
    """经营现金净流出是真实信号，方向由 sign_convention 承载，不拒答。"""
    row = _ocfr_row(**{"cfs.net_cash_flow_from_operating_activities": -800})
    assert evaluate_refusal(_defn("operating_cash_flow_ratio"), row) is None


def test_ocf_ratio_period_length_flag_fires_on_interim():
    """S4：半年报累计数不得与年度口径直接比较。"""
    row = _ocfr_row(**{"notes.reporting_period_months": 6})
    assert "period_length_mismatch" in active_flags(_defn("operating_cash_flow_ratio"), row)


def test_ocf_ratio_no_period_flag_on_annual():
    assert "period_length_mismatch" not in active_flags(
        _defn("operating_cash_flow_ratio"), _ocfr_row()
    )


# --------------------------------------------------------------------------
# 净现比：与净利率**相反**的立场，且理由必须写在定义里
# --------------------------------------------------------------------------


def test_ocf_to_profit_refuses_negative_denominator():
    """分母为负时比值符号与盈利质量方向相反，会把好情形显示成坏情形。"""
    row = {
        "cfs.net_cash_flow_from_operating_activities": 500,
        "is.net_profit_attributable_to_parent": -200,
        "notes.restatement_flag": False,
    }
    refusal = evaluate_refusal(_defn("ocf_to_net_profit_attributable"), row)
    assert isinstance(refusal, Refusal)
    assert refusal.code is RefusalCode.UNDEFINED_CONDITION_HIT


def test_net_margin_and_ocf_ratio_take_opposite_stances_on_purpose():
    """两处立场相反不是不一致，理由必须能在定义里查到。"""
    ocf = _defn("ocf_to_net_profit_attributable")
    texts = " ".join(p.text or "" for p in ocf.common_pitfalls)
    assert "归母净利率" in texts and "不是不一致" in texts


def test_ocf_to_profit_denominator_excludes_minority():
    assert "is.net_profit" not in _defn("ocf_to_net_profit_attributable").source_field_ids


# --------------------------------------------------------------------------
# 自由现金流：无准则定义，必须自己承认
# --------------------------------------------------------------------------


def test_fcf_admits_absence_of_standard_definition():
    """项目立论的展示物：anthropics/financial-services 恰恰没说这句。"""
    note = _defn("free_cash_flow").derivation["note"]
    assert "无会计准则定义" in note
    assert "不可比" in note


def test_fcf_does_not_refuse_on_negative_result():
    """扩张期资本开支大于经营现金流是常态，负 FCF 是真实信号。"""
    row = {
        "cfs.net_cash_flow_from_operating_activities": 300,
        "cfs.cash_paid_for_fixed_intangible_and_other_long_term_assets": 900,
    }
    assert evaluate_refusal(_defn("free_cash_flow"), row) is None


def test_fcf_refuses_missing_capex_not_zero_fill():
    """减项缺失按 0 处理会使 FCF 等于经营现金流——看起来完全正常的错误数字。"""
    row = {"cfs.net_cash_flow_from_operating_activities": 300}
    refusal = evaluate_refusal(_defn("free_cash_flow"), row)
    assert isinstance(refusal, Refusal)
    assert refusal.code is RefusalCode.UNDEFINED_CONDITION_HIT


def test_fcf_excludes_investing_net_cash_flow():
    ids = _defn("free_cash_flow").source_field_ids
    assert "cfs.net_cash_flow_from_investing_activities" not in ids


# --------------------------------------------------------------------------
# 三份周转天数：约定必须逐份显式，不靠继承批次规则
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", TURNOVER_DAYS)
def test_turnover_days_state_basis_and_point_in_time(name):
    note = _defn(name).derivation["note"]
    assert "365" in note, f"{name} 未显式声明天数基数"
    assert "期末" in note, f"{name} 未显式声明期末时点立场"


@pytest.mark.parametrize("name", TURNOVER_DAYS)
def test_turnover_days_shape(name):
    defn = _defn(name)
    assert defn.derivation["allow_from_components"] is False
    assert defn.period_semantics == "混合"


def test_inventory_turnover_uses_cost_not_revenue():
    ids = _defn("inventory_turnover_days").source_field_ids
    assert "is.operating_cost" in ids
    assert "is.operating_revenue_current" not in ids


def test_receivable_turnover_uses_revenue_not_cost():
    ids = _defn("accounts_receivable_turnover_days").source_field_ids
    assert "is.operating_revenue_current" in ids
    assert "is.operating_cost" not in ids


def test_payable_turnover_uses_cost_and_excludes_notes_payable():
    ids = _defn("accounts_payable_turnover_days").source_field_ids
    assert "is.operating_cost" in ids
    assert not any("notes_payable" in i or "bills_payable" in i for i in ids)


def test_inventory_turnover_accepts_zero_inventory():
    """零库存是真实可能的经营状态，周转天数为 0。"""
    row = {"bs.inventory": 0, "is.operating_cost": 5000}
    assert evaluate_refusal(_defn("inventory_turnover_days"), row) is None


def test_inventory_turnover_refuses_zero_cost():
    row = {"bs.inventory": 1000, "is.operating_cost": 0}
    refusal = evaluate_refusal(_defn("inventory_turnover_days"), row)
    assert isinstance(refusal, Refusal)
    assert refusal.code is RefusalCode.UNDEFINED_CONDITION_HIT


def test_inventory_turnover_refuses_missing_inventory():
    """与「存货为 0 不拒答」成对，两条同时通过才算 R6 成立。"""
    refusal = evaluate_refusal(_defn("inventory_turnover_days"), {"is.operating_cost": 5000})
    assert isinstance(refusal, Refusal)
    assert refusal.code is RefusalCode.UNDEFINED_CONDITION_HIT


def test_total_asset_turnover_refuses_zero_assets():
    row = {"is.operating_revenue_current": 8000, "bs.total_assets": 0}
    refusal = evaluate_refusal(_defn("total_asset_turnover"), row)
    assert isinstance(refusal, Refusal)
    assert refusal.code is RefusalCode.UNDEFINED_CONDITION_HIT


# --------------------------------------------------------------------------
# OQ-01：现金循环周期必须打不中（C2 类拒答题的真实靶子）
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["现金循环周期", "现金转换周期", "CCC"])
def test_cash_conversion_cycle_is_not_defined(registry, name):
    """它是真实的复合指标能力缺口，不是为了凑 C2 题编造的靶子。

    CCC = 存货周转天数 + 应收账款周转天数 − 应付账款周转天数，
    需要「指标引用指标」，现行 schema 的 source_fields 与受限 DSL 都只支持字段引用。
    三个分量都已在本批次定义，唯独 CCC 本身定义不出来——这个对比本身就是证据。
    """
    got = registry.resolve(name)
    assert isinstance(got, Refusal), f"{name} 竟然解析成功，C2 靶子失效"
    assert got.code is RefusalCode.METRIC_NOT_DEFINED


def test_ccc_components_all_exist(registry):
    """三个分量都在，唯独复合不出来——这才说明缺的是能力不是数据。"""
    for name in TURNOVER_DAYS:
        assert not isinstance(registry.resolve(name), Refusal)


# --------------------------------------------------------------------------
# 批次级断言
# --------------------------------------------------------------------------


def test_batch_field_provenance_within_controlled_sets():
    rules = yaml.safe_load((REPO_ROOT / "scan_rules.yaml").read_text(encoding="utf-8"))
    prov = rules["semantic_layer_provenance"]
    statements = tuple(prov["allowed_statements"])
    prefixes = set(prov["allowed_field_prefixes"])
    for name in BATCH:
        for sf in _defn(name).source_fields:
            assert sf.statement and sf.statement.startswith(statements), (
                f"{name}: statement {sf.statement!r} 不属于公开披露报表受控集"
            )
            assert sf.id.split(".", 1)[0] in prefixes, f"{name}: 字段前缀越界 {sf.id!r}"


def test_batch_advisory_ratio_under_half():
    stats = collect_pitfall_stats(METRICS, paths=BATCH_PATHS)
    assert stats.unclassified == 0
    assert stats.advisory_ratio < 0.5, stats.to_dict()


def test_batch_uses_only_definition_scoped_vocabulary_flags():
    for name in BATCH:
        for flag in _defn(name).flags:
            assert flag.name in VOCAB, f"{name} 使用了词表外的标记 {flag.name!r}"
            assert VOCAB.scope_of(flag.name) == "definition", (
                f"{name} 声明了 system 域标记 {flag.name!r}（R4 禁止）"
            )
