"""9 条 Requirement 的机械校验。

glob 参数化：01-04/05/06 新增的 19 份定义**无需修改本文件**即自动纳入校验。
反向参数化：POC-01 的三份 version: 1 定义必须在同一校验器下被判不合规，
且不合规项覆盖红测矩阵的四条通过判据 R1 / R2 / R4 / R8。
"""

import copy
from pathlib import Path

import pytest

from semantic_layer.definition import (
    is_definition_file,
    iter_definition_paths,
    load_definition,
)
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


def test_metrics的扫描范围没有被子目录绕过():
    """🔴 `iter_definition_paths` 用的是**非递归** glob（`N-42` 的第 8 处，2026-09-05）。

    `python -m semantic_layer validate` 校验的就是这个集合。
    谁把一份定义放进 `metrics/sub/foo.yaml`，**它一条 Requirement 都不过，
    而门禁绿** —— 与 `N-42` 同族：门禁看不见的东西，在证据里与「不存在」不可区分。

    ⚠️ **基准集合必须独立于被检查物**（`rules/pitfalls.md` 第 19 条）：
    这里用 `rglob` 重新枚举，不拿 `iter_definition_paths` 自己报的数当基准。
    过滤两侧都用 `definition.is_definition_file()` —— **这是「是不是定义」的唯一权威判据**，
    在这里另写一个下划线判断，就是 2026-09-04 那个「同一目录两个入口读法不一致」的复发。

    **明确抓不到**：子目录里只放了下划线开头的文件（`metrics/sub/_flags.yaml`）时
    两侧都排除它，这条不红。共享注册表按固定路径加载，那种文件是散落物不是定义。
    """
    flat = iter_definition_paths(METRICS_DIR)
    deep = sorted(p for p in METRICS_DIR.rglob("*.yaml") if is_definition_file(p))
    strays = [p.relative_to(METRICS_DIR).as_posix() for p in deep if p not in flat]
    assert flat == deep, (
        f"这些定义落在 `metrics/` 的子目录里，`validate` 的非递归 glob 看不见它们："
        f"{strays}。它们一条 Requirement 都没过。"
    )
    assert len(flat) >= 20, f"只扫到 {len(flat)} 份定义，glob 可能被窄化了"


def test_子目录里的定义会让上一条红(tmp_path):
    """负控制：把缺陷造出来，证明上一条真的会红。

    连带证明 `is_definition_file` 在两侧的行为一致 —— 下划线开头的
    **在根下和在子目录下都不算定义**，所以它不会制造假红。
    """
    (tmp_path / "sub").mkdir()
    (tmp_path / "top.yaml").write_text("metric_id: top", encoding="utf-8")
    (tmp_path / "sub" / "buried.yaml").write_text("metric_id: buried", encoding="utf-8")
    (tmp_path / "sub" / "_shared.yaml").write_text("flags: []", encoding="utf-8")

    flat = iter_definition_paths(tmp_path)
    deep = sorted(p for p in tmp_path.rglob("*.yaml") if is_definition_file(p))
    assert [p.name for p in flat] == ["top.yaml"]
    assert [p.name for p in deep] == ["buried.yaml", "top.yaml"]
    assert flat != deep, "视野缺口没有被这条比较暴露出来"


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


# --------------------------------------------------------------------------
# N-41 判据 2：陈旧字节码在 src/ 上不可能存在（2026-08-31）
# --------------------------------------------------------------------------


def test_本次会话不写字节码():
    """`conftest.py` 的第 1 条。**只做这一条等于没做** —— 见下一条。"""
    import sys as _sys

    assert _sys.dont_write_bytecode is True, (
        "本次会话仍会写 .pyc —— conftest 的那一行没生效或被谁改回去了（N-41）"
    )


def test_src下没有任何陈旧字节码():
    """`conftest.py` 的第 2 条，**要紧的是这一条**。

    骗过「造回归 → 看红 → 回退」的是**读**到上一轮留下的 `.pyc`，不是写。
    `.pyc` 的失效判据是源文件的 `(mtime, size)`，而 **mtime 是秒级** ——
    等长变异在同一秒内改完又回退时，Python 继续跑缓存的字节码，
    而 `grep` 与 `inspect.getsource()` 读文件不读字节码，**证明不了任何事**。

    ⚠️ 本条断言的是一个**当前状态**：会话开始时 conftest 清过，且此后不再写。
    它红了说明有东西在测试运行期间往 `src/` 写了 `.pyc` —— 那正是要防的。
    """
    from pathlib import Path as _Path

    src = _Path(__file__).resolve().parent.parent / "src"
    caches = sorted(p.relative_to(src).as_posix() for p in src.rglob("__pycache__"))
    assert caches == [], (
        f"`src/` 下出现了字节码缓存：{caches}。"
        "陈旧字节码能让「造回归 → 看红 → 回退」整段失效（N-41）—— "
        "两个方向都会被骗，而「造回归后是绿」那个方向会产出一条"
        "「我验过了、这道门不设防」的结论，**而验证根本没发生**。"
    )


def test_清理确实做过而不是从来就没有缓存():
    """基线。**没有它，上一条在「本机从没跑过 Python」时也会绿。**

    与 `test_留痕采集点唯一这条断言不是空转` 同一道理：空集也满足相等。
    这里断言 conftest 的清理函数**本身可用** —— 而不是断言「本次清掉了几个」，
    那个数取决于上一轮留了什么，是非确定的。
    """
    import conftest

    assert hasattr(conftest, "PURGED_AT_STARTUP")
    assert callable(conftest._purge_src_bytecode)
    # 再跑一次必须返回空列表：第一次已经清干净，且此后不写。
    assert conftest._purge_src_bytecode() == []


# --------------------------------------------------------------------------
# 承重哈希的跨平台可移植性（2026-09-04，独立复核发现）
# --------------------------------------------------------------------------


def _manifests():
    """仓库里全部 `SHA256SUMS`。**基准是磁盘，不是一张写死的清单** ——
    写死的话，新增一个冻结目录就不在检查范围里了（`N-42` 的形状）。
    """
    import subprocess

    tracked = subprocess.run(
        ["git", "ls-files", "*SHA256SUMS"],
        capture_output=True, text=True, encoding="utf-8", cwd=REPO_ROOT,
    ).stdout.split()
    return [REPO_ROOT / t for t in tracked]


def _manifest_path(line: str) -> str:
    """一行清单里的**文件路径**。认 `hash *path` 与 `hash  path` 两种格式。

    ⚠️ 只认一种会让另一批清单静默落在检查范围之外 —— 正是这几条门要防的形状。
    实测：`eval/` 两份用 `*`（sha256sum 二进制模式），
    `docs/agent/poc-01/SHA256SUMS` 用两个空格（文本模式）。
    """
    parts = line.split(None, 1)
    if len(parts) < 2:
        return ""
    rest = parts[1]
    return rest[1:].strip() if rest.startswith("*") else rest.strip()


def test_被哈希覆盖的文件在工作树里不得含CRLF():
    """🔴 `D-012` 的物理保障要求哈希**跨平台稳定**，而 CRLF 会让它分叉。

    2026-09-04 实地踩到：用 `pathlib.write_text` 在 Windows 上重写
    `eval/testdata/sample-suite/` 的两份夹具（**文本模式默认写 CRLF**），
    再按**工作树字节**重算清单 —— 本机 `sha256sum -c` 全 OK、843 passed 全绿，
    而 `.gitattributes` 是 `* text=auto eol=lf`，**入库与任何新检出都是 LF**：

        S-C2-002.yaml   工作树 114a9586…（清单记的）   入库 9a7829a8…
        sample.yaml     工作树 b81f8282…（清单记的）   入库 16ffd711…

    ⇒ 那个提交声称的「七道门全 exit 0」**只在那一台机器的工作树上成立**，
    任何新检出与 Linux CI 上第一道门就是红的。
    这是 `rules/commands.md` 记的「本地绿 ≠ CI 绿」，这次活在 HEAD 上。

    **只查承重集合**（被某份 `SHA256SUMS` 覆盖的文件），不查全仓 ——
    全仓 70 个被跟踪文件工作树里含 CRLF，它们的哈希不承重，管它们是噪声。

    它会红的场景：有人在 Windows 上按工作树字节重算任何一份清单。
    """
    offenders = []
    for manifest in _manifests():
        for line in manifest.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rel = _manifest_path(line)
            target = manifest.parent / rel
            if target.is_file() and b"\r\n" in target.read_bytes():
                offenders.append(str(target.relative_to(REPO_ROOT)))
    assert offenders == [], "这些被哈希覆盖的文件含 CRLF，工作树哈希与入库哈希会分叉：" + "; ".join(offenders)


def test_每份清单在工作树上自校验通过():
    """反方向：光「没有 CRLF」不够，记的哈希还得真的对得上。

    没有这一条，上一条可以被一份**内容全错但都是 LF** 的清单满足。
    """
    import hashlib

    checked = 0
    for manifest in _manifests():
        for line in manifest.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            want = line.split()[0]
            rel = _manifest_path(line)
            target = manifest.parent / rel
            assert target.is_file(), f"{manifest} 记了一个不存在的文件：{rel}"
            got = hashlib.sha256(target.read_bytes()).hexdigest()
            assert got == want, f"{target} 哈希不符：清单 {want[:16]}… 实际 {got[:16]}…"
            checked += 1
    assert checked >= 26, f"覆盖太薄，只校了 {checked} 个文件（frozen-01 21 + poc-01 5 起）"
