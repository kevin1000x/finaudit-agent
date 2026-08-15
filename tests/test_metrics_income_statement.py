"""01-04 批次：利润表与盈利能力 6 个指标的行为测试。

行数据全部为**内存构造的合成样例**，不来自任何年报、AKShare 或其他第三方源，
也不引入任何外部数据文件（D-010）。数值只为触发/不触发特定分支而设，无真实公司含义。
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
    "revenue_growth_yoy",
    "gross_profit_margin",
    "net_profit_margin_attributable",
    "roe_weighted_average",
    "return_on_total_assets",
    "period_expense_ratio",
]
BATCH_PATHS = [METRICS / f"{name}.yaml" for name in BATCH]


def _defn(name):
    return load_definition(METRICS / f"{name}.yaml")


@pytest.fixture(scope="module")
def registry():
    return Registry.load(METRICS)


# --------------------------------------------------------------------------
# 合规性
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", BATCH)
def test_definition_is_conformant(name):
    findings = validate_definition(_defn(name), VOCAB)
    assert findings == [], f"{name} 不合规：{[f.code for f in findings]}"


@pytest.mark.parametrize("name", BATCH)
def test_version_and_grain(name):
    defn = _defn(name)
    assert defn.version == 2
    assert set(defn.grain) >= {"entity", "period", "period_type"}


# --------------------------------------------------------------------------
# 别名解析
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "alias,expected",
    [
        ("营收增长率", "revenue_growth_yoy"),
        ("毛利率", "gross_profit_margin"),
        ("净利率", "net_profit_margin_attributable"),
        ("加权平均ROE", "roe_weighted_average"),
        ("ROA", "return_on_total_assets"),
        ("三费占比", "period_expense_ratio"),
    ],
)
def test_alias_resolves(registry, alias, expected):
    got = registry.resolve(alias)
    assert not isinstance(got, Refusal), got
    assert got.metric_id == expected


# --------------------------------------------------------------------------
# 已知取数分歧必须有承载体（不是靠作者记得）
# --------------------------------------------------------------------------


def test_revenue_growth_excludes_originally_reported_field():
    """POC-01 两位回答者都独立避开的陷阱：上期数不得取上年年报原始披露值。"""
    ids = _defn("revenue_growth_yoy").source_field_ids
    assert "is.operating_revenue_prior_as_originally_reported" not in ids
    assert "is.operating_revenue_prior_as_presented" in ids


def test_gross_margin_excludes_total_operating_revenue():
    """营业收入 vs 营业总收入：后者含利息收入，不与营业成本配比。"""
    assert "is.total_operating_revenue_current" not in _defn("gross_profit_margin").source_field_ids


def test_net_margin_excludes_undifferentiated_net_profit():
    assert "is.net_profit" not in _defn("net_profit_margin_attributable").source_field_ids


def test_roa_uses_undifferentiated_net_profit_on_purpose():
    """与归母类指标相反的选择：分母是全部资产，分子必须含少数股东损益。"""
    ids = _defn("return_on_total_assets").source_field_ids
    assert "is.net_profit" in ids
    assert "is.net_profit_attributable_to_parent" not in ids


def test_period_expense_excludes_rd_expense():
    """研发费用不计入 —— 2018 年格式修订使前后年度不是同一个集合。"""
    ids = _defn("period_expense_ratio").source_field_ids
    assert not any("rd" in i or "research" in i for i in ids), ids
    assert {"is.selling_expense", "is.administrative_expense", "is.financial_expense"} <= ids


def test_roa_period_semantics_is_mixed():
    assert _defn("return_on_total_assets").period_semantics == "混合"


def test_roe_forbids_derivation():
    defn = _defn("roe_weighted_average")
    assert defn.derivation["allow_from_components"] is False
    assert defn.derivation.get("note")


def test_period_expense_allows_component_sum():
    assert _defn("period_expense_ratio").derivation["allow_from_components"] is True


# --------------------------------------------------------------------------
# 拒答行为
# --------------------------------------------------------------------------


def test_revenue_growth_refuses_zero_base():
    row = {
        "is.operating_revenue_current": 1000,
        "is.operating_revenue_prior_as_presented": 0,
        "notes.restatement_flag": False,
    }
    refusal = evaluate_refusal(_defn("revenue_growth_yoy"), row)
    assert isinstance(refusal, Refusal)
    assert refusal.code is RefusalCode.UNDEFINED_CONDITION_HIT


def test_revenue_growth_refuses_missing_base():
    """首次披露 / 当年新上市：无比较基数，拒答而不是按 0 处理。"""
    row = {"is.operating_revenue_current": 1000, "notes.restatement_flag": False}
    refusal = evaluate_refusal(_defn("revenue_growth_yoy"), row)
    assert isinstance(refusal, Refusal)
    assert refusal.code is RefusalCode.UNDEFINED_CONDITION_HIT


def test_revenue_growth_restated_flag_fires():
    row = {
        "is.operating_revenue_current": 1200,
        "is.operating_revenue_prior_as_presented": 1000,
        "notes.restatement_flag": True,
    }
    assert "restated" in active_flags(_defn("revenue_growth_yoy"), row)


def test_roe_refuses_when_disclosure_missing():
    """本批次最能体现立论的一条：未披露即拒答，不用期末净资产倒推一个出来。"""
    refusal = evaluate_refusal(_defn("roe_weighted_average"), {"notes.restatement_flag": False})
    assert isinstance(refusal, Refusal)
    assert refusal.code is RefusalCode.UNDEFINED_CONDITION_HIT


def test_roe_accepts_disclosed_value():
    row = {"kpi.roe_weighted_average_disclosed": 12.35, "notes.restatement_flag": False}
    assert evaluate_refusal(_defn("roe_weighted_average"), row) is None


def test_net_margin_does_not_refuse_on_negative_profit():
    """亏损年度分子为负是正常取值，不是未定义。

    把它列为未定义会让系统在最需要给出结论的年度拒答。
    """
    row = {
        "is.net_profit_attributable_to_parent": -50_000_000,
        "is.operating_revenue_current": 800_000_000,
        "notes.restatement_flag": False,
    }
    assert evaluate_refusal(_defn("net_profit_margin_attributable"), row) is None


def test_roa_refuses_zero_total_assets():
    row = {"is.net_profit": 100, "bs.total_assets": 0, "notes.restatement_flag": False}
    refusal = evaluate_refusal(_defn("return_on_total_assets"), row)
    assert isinstance(refusal, Refusal)
    assert refusal.code is RefusalCode.UNDEFINED_CONDITION_HIT


def test_gross_margin_refuses_missing_cost_not_treats_as_zero():
    """按 0 处理会得出毛利率 100% —— 一个看起来正常的错误数字。"""
    row = {"is.operating_revenue_current": 1000, "notes.restatement_flag": False}
    refusal = evaluate_refusal(_defn("gross_profit_margin"), row)
    assert isinstance(refusal, Refusal)
    assert refusal.code is RefusalCode.UNDEFINED_CONDITION_HIT


def test_period_expense_refuses_missing_component_not_zero_fill():
    """三费缺一即拒答。补 0 会得出偏低但看起来正常的费用率。"""
    row = {
        "is.selling_expense": 100,
        "is.administrative_expense": 200,
        "is.operating_revenue_current": 10_000,
        "notes.restatement_flag": False,
    }
    refusal = evaluate_refusal(_defn("period_expense_ratio"), row)
    assert isinstance(refusal, Refusal)
    assert refusal.code is RefusalCode.UNDEFINED_CONDITION_HIT


def test_period_expense_accepts_negative_financial_expense():
    """财务费用为负（利息收入 > 利息支出）是正常情形，不该拒答。"""
    row = {
        "is.selling_expense": 100,
        "is.administrative_expense": 200,
        "is.financial_expense": -30,
        "is.operating_revenue_current": 10_000,
        "notes.restatement_flag": False,
    }
    assert evaluate_refusal(_defn("period_expense_ratio"), row) is None


# --------------------------------------------------------------------------
# 批次级断言
# --------------------------------------------------------------------------


def test_batch_field_provenance_within_controlled_sets():
    """在批次内做这条断言而不是跑全仓 scan，是为了避开与并行批次的竞态。"""
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
    """§5.1 监控指标。用显式路径而非全目录，避开与并行批次的竞态。"""
    stats = collect_pitfall_stats(METRICS, paths=BATCH_PATHS)
    assert stats.unclassified == 0
    assert stats.advisory_ratio < 0.5, stats.to_dict()


def test_batch_uses_only_vocabulary_flags():
    """只引用词表，不自造；需新增即触发停止协议，不由单份定义顺手引入。"""
    for name in BATCH:
        for flag in _defn(name).flags:
            assert flag.name in VOCAB, f"{name} 使用了词表外的标记 {flag.name!r}"
            assert VOCAB.scope_of(flag.name) == "definition", (
                f"{name} 声明了 system 域标记 {flag.name!r}（R4 禁止）"
            )
