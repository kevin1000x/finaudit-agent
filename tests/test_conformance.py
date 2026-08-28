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


def test_enforced_by_may_point_at_system_scoped_vocabulary_flag():
    """OQ-04：R4 禁止定义声明 system 域标记，R8 要求陷阱指向可求值规则。

    若 R8 只认定义内声明的标记，「跨期不可比」类陷阱在构造上无法满足元规则——
    两条 Requirement 直接打架。system 域标记的承载体在运行时，它确实存在。
    """
    defn = load_definition(METRICS_DIR / "net_profit_attributable_excl_nonrecurring.yaml")
    refs = {p.enforced_by for p in defn.common_pitfalls if p.enforced_by}
    assert "flags.basis_version_mismatch" in refs, "本用例的前提不再成立，需重写"
    assert "basis_version_mismatch" not in {f.name for f in defn.flags}, (
        "system 域标记不得在定义文件内声明（R4）"
    )
    findings = validate_definition(defn, VOCAB)
    assert not [f for f in findings if f.rule == "R8"], (
        f"指向 system 域标记的 enforced_by 被误判为不合规：{findings}"
    )


def test_kpi_namespace_is_parseable():
    """`kpi.` 承载「主要会计数据和财务指标」章节的已披露值。

    scan_rules.yaml 的 allowed_field_prefixes 从 01-03 起就含 kpi，
    而规格与 DSL 直到本次才补上——两份版本化产物曾互相矛盾。
    """
    from semantic_layer import dsl

    cond = dsl.parse_condition("is_missing(kpi.roe_weighted_average_disclosed)")
    assert "kpi.roe_weighted_average_disclosed" in cond.field_refs


def test_scan_prefixes_and_dsl_namespaces_agree():
    """两份版本化产物对「合法数据侧前缀」必须给出同一个答案（D-009）。"""
    import yaml

    from semantic_layer import dsl

    rules = yaml.safe_load((REPO_ROOT / "scan_rules.yaml").read_text(encoding="utf-8"))
    scan_prefixes = set(rules["semantic_layer_provenance"]["allowed_field_prefixes"])
    assert scan_prefixes == set(dsl.ROOT_NAMESPACES), (
        f"scan_rules.yaml 允许 {sorted(scan_prefixes)}，"
        f"而 DSL 白名单是 {sorted(dsl.ROOT_NAMESPACES)}"
    )


def test_derivation_can_enforce_a_pitfall():
    """derivation.allow_from_components 是布尔字段、可机械读取，够格做承载体。"""
    defn = load_definition(METRICS_DIR / "roe_weighted_average.yaml")
    refs = {p.enforced_by for p in defn.common_pitfalls if p.enforced_by}
    assert "derivation.allow_from_components" in refs, "本用例的前提不再成立，需重写"
    assert not [f for f in validate_definition(defn, VOCAB) if f.rule == "R8"]


def test_derivation_enforced_by_rejects_unknown_attribute():
    """放宽只针对 allow_from_components 与 note，不是对 derivation.* 一律放行。"""
    defn = load_definition(METRICS_DIR / "roe_weighted_average.yaml")
    defn.common_pitfalls[0].enforced_by = "derivation.whatever"
    findings = validate_definition(defn, VOCAB)
    assert any(f.code == "R8.ENFORCED_BY_UNRESOLVED" for f in findings)


def test_derivation_enforced_by_requires_the_key_to_exist():
    """指向一个本定义没声明的 derivation 属性，仍是不合规。"""
    defn = load_definition(METRICS_DIR / "roe_weighted_average.yaml")
    defn.derivation = {"allow_from_components": False}  # 没有 note
    defn.common_pitfalls[0].enforced_by = "derivation.note"
    findings = validate_definition(defn, VOCAB)
    assert any(f.code == "R8.ENFORCED_BY_UNRESOLVED" for f in findings)


def test_enforced_by_pointing_at_unknown_flag_still_fails():
    """放宽只针对词表里的 system 域标记，不是对 flags.* 一律放行。"""
    defn = load_definition(METRICS_DIR / "net_profit_attributable_excl_nonrecurring.yaml")
    defn.common_pitfalls[0].enforced_by = "flags.no_such_flag_anywhere"
    findings = validate_definition(defn, VOCAB)
    assert any(f.code == "R8.ENFORCED_BY_UNRESOLVED" for f in findings)


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
    # basis_version_mismatch 于 2026-08-15 由 definition 改为 system（OQ-04）：
    # 它只有比较两期时才判定得出，单份定义写不出能求值的 trigger。
    assert VOCAB.system_scoped == {
        "metric_version_mismatch",
        "basis_version_mismatch",
        "source_disagreement",
    }


# --------------------------------------------------------------------------
# 2026-08-27 新增：两条「存量已清零，现在加上去就是绿的」的检查
#
# 顺序是故意的：**先清干净再上门禁**。反过来（先上门禁再清）会得到一道
# 从第一天起就红的门，而一道长期红着的门等于没有门 —— 人会学会忽略它。
# --------------------------------------------------------------------------


def test_被跟踪的md里没有字面控制字符():
    """`Cc`/`Cf` 字符混进文档会静默改变逐字相等的比对结果。

    2026-08-27 全仓普查抓出 **6 个存量**：`OPEN-ITEMS.md` 4 个、
    `01.5-06-PLAN.md` 2 个，**全是 U+0008 退格符写在本该是正则 `\b` 字面的位置**。
    其中台账那 4 个正落在 `N-30` 描述「字面退格符混进源码使正则匹配数变成 0」
    的那几行里 —— **描述这个坑的文字本身就是一个实例**。
    `01.5-06-PLAN.md` 那 2 个更实：它们在一条 `grep -rhoE` 验收命令里，**照抄跑不通**。

    ⚠️ 换行与制表符不算 —— 它们是排版的一部分，不是「不可见的意外」。
    """
    import unicodedata

    repo = Path(__file__).resolve().parent.parent
    offenders = {}
    for path in repo.rglob("*.md"):
        parts = set(path.parts)
        if ".venv" in parts or ".git" in parts or "node_modules" in parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        bad = [
            (index, repr(ch))
            for index, ch in enumerate(text)
            if unicodedata.category(ch) in ("Cc", "Cf") and ch not in "\n\t"
        ]
        if bad:
            offenders[str(path.relative_to(repo))] = bad[:3]
    assert not offenders, (
        f"这些 md 里有字面控制字符（示例为 (偏移, repr) 前三个）：{offenders}。"
        "描述这类字符时**示例要写转义序列，不能写字符本身** —— "
        "2026-08-27 就是在写「不可见字符很危险」那份文档时把一个真的 BEL 写了进去。"
    )


def test_语义层导入的是当前工作树而不是主工作树():
    """`.venv` 的 editable `.pth` 钉了一条**指向主工作树的绝对路径**。

    后果（2026-08-27 实测，`rules/commands.md` 第 0 步）：在任何 worktree 里跑
    `python -m semantic_layer scan|validate` 读的都是**主树**的 `src/` 与 `metrics/`，
    而同一解释器同一 cwd 下 `pytest` 却读 worktree（`pythonpath` 走 rootdir）。
    **两条命令导入两份代码，输出里没有任何东西会告诉你。**

    这条断言把它变成一次会红的测试：`semantic_layer.__file__` 必须落在
    pytest 的 rootdir 之下。**它守的不是「代码对不对」，是「你测的是不是你改的那份」。**
    """
    import semantic_layer

    repo = Path(__file__).resolve().parent.parent
    module_path = Path(semantic_layer.__file__).resolve()
    assert repo in module_path.parents, (
        f"semantic_layer 导入自 {module_path}，而本次测试的 rootdir 是 {repo}。"
        "多工作树下 editable .pth 会把 import 钉在主树上 —— "
        "此时 pytest 与 `python -m semantic_layer` 导入的是两份不同的代码。"
        "处置见 rules/commands.md 第 0 步：显式覆盖 PYTHONPATH。"
    )
