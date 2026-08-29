"""01-05 批次：资产负债表与偿债 6 个指标的行为测试。

行数据全部为**内存构造的合成样例**，不来自任何年报、AKShare 或其他第三方源，
也不引入任何外部数据文件（D-010）。数值只为触发/不触发特定分支而设，无真实公司含义。

本文件的核心是两组对照，各自证明一条 Requirement 真的成立：
- 「缺失」与「取值为零」走不同分支（R6）—— quick_ratio 的存货、有息负债率的分项
- 「结果为负」不等于「未定义」—— net_working_capital
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
    "current_ratio",
    "quick_ratio",
    "debt_to_asset_ratio",
    "interest_bearing_debt_ratio",
    "minority_interest_share",
    "net_working_capital",
]
BATCH_PATHS = [METRICS / f"{name}.yaml" for name in BATCH]

INTEREST_BEARING_COMPONENTS = [
    "bs.short_term_borrowings",
    "bs.trading_financial_liabilities",
    "bs.non_current_liabilities_due_within_one_year",
    "bs.long_term_borrowings",
    "bs.bonds_payable",
    "bs.lease_liabilities",
]


def _defn(name):
    return load_definition(METRICS / f"{name}.yaml")


@pytest.fixture(scope="module")
def registry():
    return Registry.load(METRICS)


# --------------------------------------------------------------------------
# 合规性与形状
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", BATCH)
def test_definition_is_conformant(name):
    findings = validate_definition(_defn(name), VOCAB)
    assert findings == [], f"{name} 不合规：{[f.code for f in findings]}"


@pytest.mark.parametrize("name", BATCH)
def test_version_and_point_in_time(name):
    defn = _defn(name)
    assert defn.version == 2
    assert defn.period_semantics == "时点", "本批次全部是时点量"


@pytest.mark.parametrize(
    "alias,expected",
    [
        ("流动比率", "current_ratio"),
        ("速动比率", "quick_ratio"),
        ("资产负债率", "debt_to_asset_ratio"),
        ("有息负债率", "interest_bearing_debt_ratio"),
        ("少数股东权益占比", "minority_interest_share"),
        ("营运资金", "net_working_capital"),
    ],
)
def test_alias_resolves(registry, alias, expected):
    got = registry.resolve(alias)
    assert not isinstance(got, Refusal), got
    assert got.metric_id == expected


# --------------------------------------------------------------------------
# 期末时点立场与禁用项
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["current_ratio", "quick_ratio", "net_working_capital"])
def test_period_begin_field_is_not_declared(name):
    """POC-01 的 S5 单方缺陷：v1 没显式禁用期初值。"""
    assert "bs.total_current_liabilities_period_begin" not in _defn(name).source_field_ids


@pytest.mark.parametrize("name", ["current_ratio", "quick_ratio"])
def test_total_liabilities_not_used_as_denominator(name):
    """负债合计不是流动负债合计 —— POC-01 两位回答者都主动排除的陷阱。"""
    assert "bs.total_liabilities" not in _defn(name).source_field_ids


# --------------------------------------------------------------------------
# R6 对照组一：缺失 ≠ 零（存货）
# --------------------------------------------------------------------------


def _quick_row(**overrides):
    row = {
        "bs.total_current_assets": 5000,
        "bs.inventory": 1000,
        "bs.total_current_liabilities_period_end": 2500,
        "notes.restatement_flag": False,
    }
    row.update(overrides)
    return row


def test_quick_ratio_refuses_when_inventory_missing():
    """存货缺失按 0 处理会让速动比率**等于流动比率** —— 安静且错误。"""
    row = _quick_row()
    del row["bs.inventory"]
    refusal = evaluate_refusal(_defn("quick_ratio"), row)
    assert isinstance(refusal, Refusal)
    assert refusal.code is RefusalCode.UNDEFINED_CONDITION_HIT


def test_quick_ratio_accepts_zero_inventory():
    """存货恰为 0 是正常情形，不拒答。与上一条同时通过才算 R6 成立。"""
    assert evaluate_refusal(_defn("quick_ratio"), _quick_row(**{"bs.inventory": 0})) is None


@pytest.mark.parametrize("name", ["current_ratio", "quick_ratio"])
def test_zero_current_liabilities_refused(name):
    row = _quick_row(**{"bs.total_current_liabilities_period_end": 0})
    refusal = evaluate_refusal(_defn(name), row)
    assert isinstance(refusal, Refusal)
    assert refusal.code is RefusalCode.UNDEFINED_CONDITION_HIT


# --------------------------------------------------------------------------
# R6 对照组二：缺失 ≠ 零（有息负债分项）
# --------------------------------------------------------------------------


def _ibd_row(**overrides):
    row = {c: 100 for c in INTEREST_BEARING_COMPONENTS}
    row["bs.total_assets"] = 10_000
    row.update(overrides)
    return row


@pytest.mark.parametrize("dropped", INTEREST_BEARING_COMPONENTS)
def test_interest_bearing_refuses_when_any_component_missing(dropped):
    """未列示不等于为零：补 0 会系统性低估有息负债率，且结果看起来完全正常。"""
    row = _ibd_row()
    del row[dropped]
    refusal = evaluate_refusal(_defn("interest_bearing_debt_ratio"), row)
    assert isinstance(refusal, Refusal), f"漏掉 {dropped} 竟未拒答"
    assert refusal.code is RefusalCode.UNDEFINED_CONDITION_HIT


def test_interest_bearing_accepts_all_zero_components():
    """分项全为 0 是「无有息负债」，正常计算。与上一条同时通过才算成立。"""
    row = _ibd_row(**{c: 0 for c in INTEREST_BEARING_COMPONENTS})
    assert evaluate_refusal(_defn("interest_bearing_debt_ratio"), row) is None


def test_interest_bearing_allows_component_sum():
    """spec R3 的 true 分支的唯一真实实例，且允许范围被穷举而非含糊授权。"""
    defn = _defn("interest_bearing_debt_ratio")
    assert defn.derivation["allow_from_components"] is True
    note = defn.derivation["note"]
    for keyword in ["短期借款", "应付债券", "租赁负债", "应付账款"]:
        assert keyword in note, f"derivation.note 未提及 {keyword}"
    assert len(defn.source_fields) >= 7


def test_debt_to_asset_forbids_component_sum():
    """与上一条互补：spec R3 的 false 分支。"""
    assert _defn("debt_to_asset_ratio").derivation["allow_from_components"] is False


def test_debt_to_asset_refuses_zero_total_assets():
    row = {"bs.total_liabilities": 500, "bs.total_assets": 0, "notes.restatement_flag": False}
    refusal = evaluate_refusal(_defn("debt_to_asset_ratio"), row)
    assert isinstance(refusal, Refusal)
    assert refusal.code is RefusalCode.UNDEFINED_CONDITION_HIT


# --------------------------------------------------------------------------
# 负值 ≠ 未定义
# --------------------------------------------------------------------------


def test_net_working_capital_does_not_refuse_when_negative():
    """负营运资金是真实的经营信号，不是未定义。

    「负值即异常」是这里最常见的实现错误，它把一个提问者最想知道的信息变成拒答。
    """
    row = {
        "bs.total_current_assets": 1000,
        "bs.total_current_liabilities_period_end": 2500,
        "notes.restatement_flag": False,
    }
    assert evaluate_refusal(_defn("net_working_capital"), row) is None


def test_net_working_capital_refuses_on_missing_component():
    row = {"bs.total_current_assets": 1000, "notes.restatement_flag": False}
    refusal = evaluate_refusal(_defn("net_working_capital"), row)
    assert isinstance(refusal, Refusal)
    assert refusal.code is RefusalCode.UNDEFINED_CONDITION_HIT


# --------------------------------------------------------------------------
# 少数股东权益占比
# --------------------------------------------------------------------------


def test_minority_share_refuses_zero_total_equity():
    row = {
        "bs.minority_interests": 100,
        "bs.total_equity": 0,
        "notes.business_combination_type": "无",
    }
    refusal = evaluate_refusal(_defn("minority_interest_share"), row)
    assert isinstance(refusal, Refusal)
    assert refusal.code is RefusalCode.UNDEFINED_CONDITION_HIT


def test_minority_share_scope_change_flag_fires():
    """trigger 已由 `D-020` 改挂 `notes.consolidation_scope_change`。"""
    row = {
        "bs.minority_interests": 100,
        "bs.total_equity": 1000,
        "notes.consolidation_scope_change": True,
    }
    assert "scope_change" in active_flags(_defn("minority_interest_share"), row)


def test_minority_share_no_scope_change_when_none():
    row = {
        "bs.minority_interests": 100,
        "bs.total_equity": 1000,
        "notes.consolidation_scope_change": False,
    }
    assert "scope_change" not in active_flags(_defn("minority_interest_share"), row)


def test_minority_share_scope_change_fires_without_business_combination():
    """🔴 **`A-8` 那处真实假阴性的回归**（`D-020` 判据 3）。

    茅台 2023 的实际情形：企业合并三项**全部不适用**（本期无企业合并），
    而「5、其他原因的合并范围变动」**适用**（控股子公司清算注销）。

    ⚠️ **本条替换掉的旧测试，当初断言的正是那个缺陷**：
    旧的 `test_minority_share_no_scope_change_when_none` 断言
    `business_combination_type == "无"` 时 `scope_change` **不置位** ——
    而按 `_flags.yaml` 对该 flag 的描述（「合并范围发生变动」），
    茅台那种情形本就该置位。

    **也就是说这个 bug 有一条绿测试在为它背书。**
    这是本项目记的「自证机制证明的不是它声称证明的事」的又一个实例，
    而且是最直接的一种：测试把缺陷写成了规格。
    """
    row = {
        "bs.minority_interests": 100,
        "bs.total_equity": 1000,
        # 本期无企业合并 —— 旧 trigger 在这里为假
        "notes.business_combination_type": frozenset(),
        # 但合并范围确实变了
        "notes.consolidation_scope_change": True,
    }
    flags = active_flags(_defn("minority_interest_share"), row)
    assert "scope_change" in flags


def test_minority_share_trigger_no_longer_reads_business_combination_type():
    """trigger 只看新字段。**旧字段单独变化不再影响它。**

    锁住这一点是因为「保留旧字段」与「trigger 仍挂旧字段」是两回事：
    `D-020` 明写前者保留原义，而后者必须改。
    """
    base = {"bs.minority_interests": 100, "bs.total_equity": 1000}
    defn = _defn("minority_interest_share")

    fired = active_flags(
        defn,
        {**base, "notes.business_combination_type": frozenset({"非同一控制下"}),
         "notes.consolidation_scope_change": False},
    )
    assert "scope_change" not in fired, (
        "trigger 仍在读 business_combination_type —— D-020 要求它改挂新字段"
    )


def test_minority_share_denominator_is_total_equity():
    ids = _defn("minority_interest_share").source_field_ids
    assert "bs.total_equity" in ids
    assert "bs.equity_attributable_to_parent" not in ids


def test_minority_share_cites_consolidation_standard():
    basis = _defn("minority_interest_share").standard_basis
    hit = [b for b in basis if b.name and "合并财务报表" in b.name]
    assert hit and hit[0].version


# --------------------------------------------------------------------------
# 批次级断言
# --------------------------------------------------------------------------


def test_batch_field_provenance_within_controlled_sets():
    """在批次内断言而非跑全仓 scan，避开与并行批次的竞态。"""
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
