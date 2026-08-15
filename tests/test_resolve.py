"""指标解析与机读拒答（AC-02 / FR-02）—— OQ-03 的关闭。

D-003 的立场：**拒答是正确行为，不是降级成功。** 因此 `resolve` 的返回是
`MetricDefinition | Refusal` 二选一——不返回 None、不向调用方抛异常。
拒答是正常返回值，这是那条决策在类型层的表达。

退出码：拒答为 **3**，不是 01-01/01-06 计划原写的 2。
2 已被 `_cmd_validate` 用作「没找到定义文件」这类**调用错误**；
拒答是正常业务结果，与调用错误必须可区分（OQ-03，2026-08-15 操作者裁决）。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from semantic_layer.__main__ import main  # noqa: E402
from semantic_layer.definition import load_definition  # noqa: E402
from semantic_layer.resolve import (  # noqa: E402
    Refusal,
    RefusalCode,
    Registry,
    active_flags,
    check_comparable,
    comparison_scoped_flags,
    evaluate_refusal,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
METRICS = REPO_ROOT / "metrics"
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "row_minimal.yaml"
TRACER = METRICS / "net_profit_attributable_excl_nonrecurring.yaml"

ROWS = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def registry() -> Registry:
    return Registry.load(METRICS)


# --------------------------------------------------------------------------
# 名称解析
# --------------------------------------------------------------------------


def test_resolve_by_alias(registry):
    got = registry.resolve("扣非归母净利润")
    assert not isinstance(got, Refusal), got
    assert got.metric_id == "net_profit_attributable_excl_nonrecurring"


def test_resolve_by_display_name(registry):
    """display_name 是规范名称，必须可解析——不该靠作者记得抄进 aliases。"""
    got = registry.resolve("毛利率")
    assert not isinstance(got, Refusal), got
    assert got.metric_id == "gross_profit_margin"


def test_resolve_by_metric_id(registry):
    got = registry.resolve("net_profit_attributable_excl_nonrecurring")
    assert not isinstance(got, Refusal)
    assert got.version == 2


@pytest.mark.parametrize("name", ["现金循环周期", "EBITDA", "自由现金流量折现值"])
def test_undefined_metric_is_refused(registry, name):
    """CCC 是真缺口而非编造靶子：它需要「指标引用指标」，schema 不支持（OQ-01）。"""
    got = registry.resolve(name)
    assert isinstance(got, Refusal)
    assert got.code is RefusalCode.METRIC_NOT_DEFINED


def test_refusal_is_json_serializable(registry):
    payload = registry.resolve("现金循环周期").to_dict()
    json.dumps(payload)  # 不抛即通过
    assert {"refused", "code", "detail", "metric_id"} <= set(payload)
    assert payload["refused"] is True


def test_alias_conflict_raises_at_load_time(tmp_path):
    """别名冲突在加载期就炸，不留到查询期——查询期才发现意味着它已经被用过一次了。"""
    for name in ("a", "b"):
        (tmp_path / f"{name}.yaml").write_text(
            f"metric_id: {name}\naliases: [共用别名]\nversion: 2\n", encoding="utf-8"
        )
    with pytest.raises(ValueError, match="别名"):
        Registry.load(tmp_path)


def test_nonconformant_definition_is_refused(tmp_path):
    """fail-closed：不合规的定义不许被消费，哪怕名字对得上。"""
    (tmp_path / "broken.yaml").write_text(
        "metric_id: broken\nversion: 2\naliases: [残缺指标]\n", encoding="utf-8"
    )
    reg = Registry.load(tmp_path)
    got = reg.resolve("残缺指标")
    assert isinstance(got, Refusal)
    assert got.code is RefusalCode.DEFINITION_NONCONFORMANT


# --------------------------------------------------------------------------
# 未定义条件求值
# --------------------------------------------------------------------------


def test_complete_row_is_not_refused():
    defn = load_definition(TRACER)
    assert evaluate_refusal(defn, ROWS["complete"]) is None


def test_missing_notes_field_hits_undefined_condition():
    defn = load_definition(TRACER)
    refusal = evaluate_refusal(defn, ROWS["missing_notes"])
    assert isinstance(refusal, Refusal)
    assert refusal.code is RefusalCode.UNDEFINED_CONDITION_HIT
    assert isinstance(refusal.condition_index, int)
    assert refusal.detail


def test_condition_index_points_at_the_hit_condition():
    defn = load_definition(TRACER)
    refusal = evaluate_refusal(defn, ROWS["missing_profit"])
    hit = defn.undefined_conditions[refusal.condition_index]
    assert "net_profit_attributable_to_parent" in hit.expr


def test_unevaluable_condition_is_refused_not_passed(tmp_path):
    """比较遇缺失操作数不得当成 False 放行——那正是本项目要消灭的静默错误。"""
    (tmp_path / "m.yaml").write_text(
        "metric_id: m\nversion: 2\n"
        "source_fields:\n  - id: bs.total_assets\n    missing_representation: null\n"
        "undefined_conditions:\n  - expr: bs.total_assets > 0\n    reason: 资产非正\n",
        encoding="utf-8",
    )
    refusal = evaluate_refusal(load_definition(tmp_path / "m.yaml"), {})
    assert isinstance(refusal, Refusal)
    assert refusal.code is RefusalCode.UNEVALUABLE_CONDITION
    assert "bs.total_assets" in refusal.detail


# --------------------------------------------------------------------------
# 跨版本比较（spec R9 / R5）
# --------------------------------------------------------------------------


def _defn_with(tmp_path, name, version, basis_version):
    path = tmp_path / f"{name}.yaml"
    path.write_text(
        f"metric_id: same_metric\nversion: {version}\n"
        "standard_basis:\n"
        f"  - name: 企业会计准则第 33 号\n    issuer: 财政部\n    article: 第五章\n"
        f"    version: '{basis_version}'\n",
        encoding="utf-8",
    )
    return load_definition(path)


def test_cross_metric_version_comparison_refused(tmp_path):
    a = _defn_with(tmp_path, "a", 2, "2014")
    b = _defn_with(tmp_path, "b", 3, "2014")
    refusal = check_comparable(a, b)
    assert isinstance(refusal, Refusal)
    assert refusal.code is RefusalCode.CROSS_VERSION_COMPARISON


def test_cross_basis_version_comparison_refused(tmp_path):
    a = _defn_with(tmp_path, "a", 2, "2014")
    b = _defn_with(tmp_path, "b", 2, "2023")
    refusal = check_comparable(a, b)
    assert isinstance(refusal, Refusal)
    assert refusal.code is RefusalCode.CROSS_BASIS_VERSION_COMPARISON


def test_same_version_is_comparable(tmp_path):
    a = _defn_with(tmp_path, "a", 2, "2014")
    b = _defn_with(tmp_path, "b", 2, "2014")
    assert check_comparable(a, b) is None


def test_different_metric_id_is_caller_error(tmp_path):
    a = _defn_with(tmp_path, "a", 2, "2014")
    b = load_definition(TRACER)
    with pytest.raises(ValueError):
        check_comparable(a, b)


# --------------------------------------------------------------------------
# 标记求值
# --------------------------------------------------------------------------


def test_active_flags_includes_triggered_flag():
    defn = load_definition(TRACER)
    got = active_flags(defn, ROWS["restated"])
    assert not isinstance(got, Refusal), got
    assert "restated" in got


def test_active_flags_excludes_untriggered_flag():
    defn = load_definition(TRACER)
    got = active_flags(defn, ROWS["complete"])
    assert "restated" not in got


def test_conformant_definition_has_no_comparison_scoped_flags():
    """OQ-04 修完之后，合规定义里不该再有引用 `comparison_period.*` 的自声明标记。

    这类标记已全部归入 system 域（R4 禁止定义文件声明），由 `check_comparable()` 负责。
    """
    defn = load_definition(TRACER)
    assert comparison_scoped_flags(defn) == set()
    assert not isinstance(active_flags(defn, ROWS["complete"]), Refusal)


def test_comparison_scoped_flag_is_deferred_not_refused(tmp_path):
    """安全网：万一有定义声明了引用 `comparison_period.*` 的标记。

    单期数据判不了它，但这**不是求值失败**——是问错了问题，
    所以应当推迟而非整体拒答。R4 现在基本堵住了这条路，此机制是兜底。
    """
    (tmp_path / "m.yaml").write_text(
        "metric_id: m\nversion: 2\n"
        "flags:\n"
        "  - name: some_comparison_flag\n"
        "    trigger: metric.version != comparison_period.metric.version\n",
        encoding="utf-8",
    )
    defn = load_definition(tmp_path / "m.yaml")
    assert comparison_scoped_flags(defn) == {"some_comparison_flag"}
    assert not isinstance(active_flags(defn, {}), Refusal)


def test_deferred_flags_are_surfaced_not_dropped(tmp_path, capsys):
    """推迟 ≠ 丢弃。调用方必须看得见有哪些待判项。"""
    (tmp_path / "m.yaml").write_text(
        "metric_id: m\nversion: 2\naliases: [某指标]\n"
        "flags:\n"
        "  - name: some_comparison_flag\n"
        "    trigger: metric.version != comparison_period.metric.version\n",
        encoding="utf-8",
    )
    defn = load_definition(tmp_path / "m.yaml")
    from semantic_layer.resolve import render_refusal

    payload = json.loads(
        render_refusal(defn, as_json=True, active=set(), deferred=comparison_scoped_flags(defn))
    )
    assert payload["deferred_comparison_flags"] == ["some_comparison_flag"]


def test_unevaluable_trigger_refuses_rather_than_dropping_flag(tmp_path):
    """求值不了的触发条件必须转成拒答，不能悄悄漏掉一个标记。

    漏掉一个 affects_comparability 的标记 = 本该阻断的比较悄悄放行。
    """
    (tmp_path / "m.yaml").write_text(
        "metric_id: m\nversion: 2\n"
        "source_fields:\n  - id: notes.restatement_flag\n    missing_representation: null\n"
        "flags:\n  - name: restated\n    trigger: notes.restatement_flag == true\n",
        encoding="utf-8",
    )
    got = active_flags(load_definition(tmp_path / "m.yaml"), {})
    assert isinstance(got, Refusal)
    assert got.code is RefusalCode.UNEVALUABLE_CONDITION


# --------------------------------------------------------------------------
# 拒答码枚举
# --------------------------------------------------------------------------


def test_refusal_codes_are_exactly_seven():
    assert {c.name for c in RefusalCode} == {
        "METRIC_NOT_DEFINED",
        "ALIAS_AMBIGUOUS",
        "DEFINITION_NONCONFORMANT",
        "UNDEFINED_CONDITION_HIT",
        "UNEVALUABLE_CONDITION",
        "CROSS_VERSION_COMPARISON",
        "CROSS_BASIS_VERSION_COMPARISON",
    }


# --------------------------------------------------------------------------
# CLI 与退出码（OQ-03 的落点）
# --------------------------------------------------------------------------


def test_cli_refusal_exit_code_is_three(capsys):
    """3 而非 2。2 已被 validate 用作「没找到定义文件」这类调用错误。"""
    code = main(["resolve", "现金循环周期", "--metrics-dir", str(METRICS), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 3
    assert payload["refused"] is True
    assert payload["code"] == "METRIC_NOT_DEFINED"


def test_cli_resolved_exit_code_is_zero(capsys):
    code = main(["resolve", "扣非归母净利润", "--metrics-dir", str(METRICS), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["metric_id"] == "net_profit_attributable_excl_nonrecurring"
    assert payload["version"] == 2


def test_cli_row_triggers_undefined_condition(capsys):
    code = main(
        [
            "resolve",
            "扣非归母净利润",
            "--metrics-dir",
            str(METRICS),
            "--row",
            f"{FIXTURE}#missing_notes",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert code == 3
    assert payload["code"] == "UNDEFINED_CONDITION_HIT"
    assert isinstance(payload["condition_index"], int)


def test_cli_row_complete_resolves_with_flags(capsys):
    code = main(
        [
            "resolve",
            "扣非归母净利润",
            "--metrics-dir",
            str(METRICS),
            "--row",
            f"{FIXTURE}#restated",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert "restated" in payload["active_flags"]


def test_cli_bad_row_key_is_caller_error(capsys):
    """行数据键不存在是调用错误，用 2，不是业务拒答的 3。"""
    code = main(
        [
            "resolve",
            "扣非归母净利润",
            "--metrics-dir",
            str(METRICS),
            "--row",
            f"{FIXTURE}#no_such_key",
            "--json",
        ]
    )
    capsys.readouterr()
    assert code == 2
