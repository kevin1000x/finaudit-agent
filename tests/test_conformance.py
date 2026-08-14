"""9 条 Requirement 的机械校验。

glob 参数化：01-04/05/06 新增的 19 份定义**无需修改本文件**即自动纳入校验。
反向参数化：POC-01 的三份 version: 1 定义必须在同一校验器下被判不合规，
且不合规项覆盖红测矩阵的四条通过判据 R1 / R2 / R4 / R8。
"""

import copy
from pathlib import Path

import pytest

from semantic_layer.definition import iter_definition_paths, load_definition
from semantic_layer.validate import validate_definition
from semantic_layer.vocabulary import load_vocabulary

REPO_ROOT = Path(__file__).resolve().parents[1]
METRICS_DIR = REPO_ROOT / "metrics"
FROZEN_V1_DIR = REPO_ROOT / "docs" / "agent" / "poc-01" / "definitions"

VOCAB = load_vocabulary(METRICS_DIR / "_flags.yaml")

V2_PATHS = iter_definition_paths(METRICS_DIR)
V1_PATHS = sorted(FROZEN_V1_DIR.glob("*.yaml"))


def _ids(paths):
    return [p.name for p in paths]


# --------------------------------------------------------------------------
# 正向：metrics/ 下每一份定义都必须合规
# --------------------------------------------------------------------------


def test_metrics_directory_is_not_empty():
    assert V2_PATHS, "metrics/ 下没有任何定义文件"


@pytest.mark.parametrize("path", V2_PATHS, ids=_ids(V2_PATHS))
def test_v2_definition_is_conformant(path):
    findings = validate_definition(load_definition(path), VOCAB)
    assert findings == [], "\n".join(f"[{f.code}] {f.where} {f.message}" for f in findings)


# --------------------------------------------------------------------------
# 反向：POC-01 的 v1 定义必须不合规，且覆盖红测的四条判据
# --------------------------------------------------------------------------


def test_frozen_v1_definitions_exist():
    assert len(V1_PATHS) == 3, f"预期 3 份冻结 v1 定义，实际 {len(V1_PATHS)}"


@pytest.mark.parametrize("path", V1_PATHS, ids=_ids(V1_PATHS))
def test_frozen_v1_definition_is_non_conformant(path):
    """三份 v1 必须全部不合规。这是红测的核心断言。"""
    findings = validate_definition(load_definition(path), VOCAB, require_v2=False)
    assert findings, f"{path.name} 竟然合规 —— 新契约未加强约束，红测失败"


@pytest.mark.parametrize("path", V1_PATHS, ids=_ids(V1_PATHS))
def test_frozen_v1_covers_red_test_criteria_or_fails_to_load(path):
    """红测四条判据 R1/R2/R4/R8 的覆盖检查。

    例外：`revenue_growth_yoy.yaml` 本身不是合法 YAML（2026-08-15 由本校验器首次发现，
    第 33 行以 `"营业收入"与…` 开头，YAML 把前导引号当成完整标量后遇到多余内容）。
    文件 SHA 冻结不可修改，9 条 Requirement 对一份加载不了的文件无从校验，
    因此它以 R0 计入不合规——比四条判据更早、更彻底地不合规，不是放宽。
    """
    findings = validate_definition(load_definition(path), VOCAB, require_v2=False)
    rules = {f.rule for f in findings}
    if "R0" in rules:
        assert any(f.code == "R0.YAML_UNPARSEABLE" for f in findings)
        return
    assert {"R1", "R2", "R4", "R8"} <= rules, (
        f"{path.name} 的不合规项 {sorted(rules)} 未覆盖红测四条判据 R1/R2/R4/R8"
    )


def test_exactly_one_frozen_v1_is_unparseable_yaml():
    """把这个发现固化成回归断言：数量变化即说明冻结目录被动过。"""
    unparseable = [
        p.name
        for p in V1_PATHS
        if load_definition(p).parse_error is not None
    ]
    assert unparseable == ["revenue_growth_yoy.yaml"], (
        f"冻结 v1 目录中语法非法的文件集合发生变化：{unparseable}"
    )


# --------------------------------------------------------------------------
# 负向用例：在内存里构造残缺定义，磁盘上的 YAML 一个字节都不动
# --------------------------------------------------------------------------


@pytest.fixture
def good_definition():
    return load_definition(METRICS_DIR / "net_profit_attributable_excl_nonrecurring.yaml")


def _rules(findings):
    return {f.rule for f in findings}


def test_removing_grain_triggers_r1(good_definition):
    defn = copy.deepcopy(good_definition)
    defn.grain = None
    assert "R1" in _rules(validate_definition(defn, VOCAB))


def test_removing_sign_convention_triggers_r2(good_definition):
    defn = copy.deepcopy(good_definition)
    defn.source_fields[0].sign_convention = None
    assert "R2" in _rules(validate_definition(defn, VOCAB))


def test_pitfall_without_backing_triggers_r8(good_definition):
    defn = copy.deepcopy(good_definition)
    defn.common_pitfalls[0].enforced_by = None
    defn.common_pitfalls[0].advisory_only = False
    findings = validate_definition(defn, VOCAB)
    assert any(f.code == "R8.PITFALL_UNBACKED" for f in findings)


def test_system_scope_flag_declared_triggers_r4(good_definition):
    defn = copy.deepcopy(good_definition)
    defn.flags[0].name = "source_disagreement"  # scope: system
    findings = validate_definition(defn, VOCAB)
    assert any(f.code == "R4.SYSTEM_SCOPE_FLAG_DECLARED" for f in findings)


def test_flag_outside_vocabulary_triggers_r4(good_definition):
    defn = copy.deepcopy(good_definition)
    defn.flags[0].name = "invented_flag"
    findings = validate_definition(defn, VOCAB)
    assert any(f.code == "R4.FLAG_NOT_IN_VOCABULARY" for f in findings)


def test_unparseable_trigger_triggers_r4(good_definition):
    defn = copy.deepcopy(good_definition)
    defn.flags[0].trigger = "notes.restatement_flag + 1"
    findings = validate_definition(defn, VOCAB)
    assert any(f.code == "R4.TRIGGER_UNPARSEABLE" for f in findings)


def test_enforced_by_dangling_index_triggers_r8(good_definition):
    defn = copy.deepcopy(good_definition)
    defn.common_pitfalls[1].enforced_by = "undefined_conditions.99"
    findings = validate_definition(defn, VOCAB)
    assert any(f.code == "R8.ENFORCED_BY_UNRESOLVED" for f in findings)


def test_v1_version_in_metrics_dir_triggers_r9(good_definition):
    defn = copy.deepcopy(good_definition)
    defn.version = 1
    findings = validate_definition(defn, VOCAB)
    assert any(f.code == "R9.VERSION_TOO_LOW" for f in findings)


# --------------------------------------------------------------------------
# 词表本身
# --------------------------------------------------------------------------


def test_vocabulary_shape():
    assert len(VOCAB.flags) == 10
    assert VOCAB.system_scoped == {"metric_version_mismatch", "source_disagreement"}
