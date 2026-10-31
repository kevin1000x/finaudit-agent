"""`frozen-04`（核查层评测集，重建批次）的门禁与判分（`D-041` §5 / `D-045`）。

本文件是那道冻结前置门禁的**负控制**：逐条把它声称能挡住的缺陷造出来，看它红。
`rules/commands.md` 的「假闸门的验证程序」要求的就是这个 ——
**一道不会因为缺陷而红的门禁，等于没有门禁。**
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from eval.freeze import VERDICTS, _check_closed_verdicts, _pregate_verify_case, pregate
from eval.verify_run import judge_case
from agent.verify import ReadAs, Verdict, read_input
from semantic_layer.resolve import Registry
from service import api

REPO = Path(__file__).resolve().parent.parent
SUITE = REPO / "eval" / "frozen-04"
VOIDED_SUITE = REPO / "eval" / "frozen-03"


def _case(name="V-017"):
    return yaml.safe_load((SUITE / "cases" / f"{name}.yaml").read_text(encoding="utf-8"))


class _FakePath:
    name = "造出来的.yaml"


# --------------------------------------------------------------------------
# 1. 冻结前置门禁的负控制
# --------------------------------------------------------------------------


def test_题面本身过门禁():
    """先证明基线是绿的 —— 否则下面每条「红了」都可能红在别的原因上。"""
    assert pregate(SUITE) == []


def test_第六态必须报红():
    """`D-041` §3：五态是封闭集。题面里写一个不在集合里的判定，冻结就该拒绝。"""
    坏 = copy.deepcopy(_case())
    坏["expected"]["claims"][0]["verdict"] = "PROBABLY_FINE"
    问题 = _pregate_verify_case(_FakePath, 坏)
    assert any("不在五态封闭集里" in p for p in 问题), 问题


def test_期望的切分切不出来必须报红():
    """期望里那条声明如果根本不在题面里，它是一个永远不可能命中的期望。"""
    坏 = copy.deepcopy(_case())
    坏["expected"]["claims"][0]["text"] = "这句话题面里没有"
    问题 = _pregate_verify_case(_FakePath, 坏)
    assert any("不是这段话切出来的任何一段" in p for p in 问题), 问题


def test_读成提问却带着逐条判定必须报红():
    坏 = copy.deepcopy(_case())
    坏["expected"]["read_as"] = "QUESTION"
    问题 = _pregate_verify_case(_FakePath, 坏)
    assert any("不该有 claims" in p for p in 问题), 问题


def test_读成声明却没有逐条判定必须报红():
    坏 = copy.deepcopy(_case("V-015"))
    坏["expected"]["read_as"] = "STATEMENT"
    问题 = _pregate_verify_case(_FakePath, 坏)
    assert any("不能为空" in p for p in 问题), 问题


def test_read_as写了别的值必须报红():
    坏 = copy.deepcopy(_case())
    坏["expected"]["read_as"] = "MAYBE"
    问题 = _pregate_verify_case(_FakePath, 坏)
    assert any("read_as" in p for p in 问题), 问题


def test_门禁认的五态与实现里的必须一致():
    """🔴 门禁**硬编码**五态，不是从实现里读出来的。

    实现单方面加一个第六态时，这一条要红 —— 方向是拦住实现，不是迁就它。
    """
    assert _check_closed_verdicts() == []
    assert set(VERDICTS) == {v.name for v in Verdict}


def test_实现加了第六态时冻结门禁必须报红(monkeypatch):
    """把回归真的造出来：给实现塞一个第六态，看门禁红。"""
    import eval.freeze as fz

    class 假的:
        CONSISTENT = INCONSISTENT = AMBIGUOUS_BASIS = None
        NOT_COVERED = NOT_CHECKABLE = None

    假枚举 = [
        type("V", (), {"name": n})
        for n in list(VERDICTS) + ["PROBABLY_FINE"]
    ]
    假模块 = type("M", (), {"Verdict": 假枚举})
    monkeypatch.setitem(__import__("sys").modules, "agent.verify", 假模块)
    问题 = fz._check_closed_verdicts()
    assert 问题 and "五态封闭集被改动了" in 问题[0], 问题


# --------------------------------------------------------------------------
# 2. 判分器的负控制
# --------------------------------------------------------------------------


@pytest.fixture
def registry():
    return Registry.load(REPO / "metrics")


@pytest.fixture
def source():
    return api._pick_source()


def _report(case, registry, source):
    return read_input(
        " ".join(str(case["conclusion"]).split()), registry, source=source
    )


def test_判分器对真实产物给出通过(registry, source):
    case = _case("V-017")
    assert judge_case(case, _report(case, registry, source))["passed"] is True


def test_判分器抓得到判定错了(registry, source):
    case = copy.deepcopy(_case("V-017"))
    case["expected"]["claims"][0]["verdict"] = "INCONSISTENT"
    got = judge_case(case, _report(case, registry, source))
    assert got["passed"] is False
    assert any("判定" in p for p in got["problems"])


def test_判分器抓得到切分错了(registry, source):
    """🔴 切分本身是被判分的一部分 —— 只判五态会让「切错但碰巧判对」拿满分。"""
    case = copy.deepcopy(_case("V-025"))
    case["expected"]["claims"] = case["expected"]["claims"][:1]
    got = judge_case(case, _report(case, registry, source))
    assert got["passed"] is False
    assert any("切分" in p for p in got["problems"])


def test_判分器抓得到读成什么错了(registry, source):
    case = copy.deepcopy(_case("V-015"))
    case["expected"]["read_as"] = "STATEMENT"
    got = judge_case(case, _report(case, registry, source))
    assert got["passed"] is False
    assert any("读成什么" in p for p in got["problems"])


def test_判分器抓得到该承接而没承接(registry, source):
    """题面声明了「这一条要承接 600519/2023」，实际没承接就得红。"""
    case = copy.deepcopy(_case("V-017"))
    case["expected"]["claims"][0]["inherited"] = "600519/2023"
    got = judge_case(case, _report(case, registry, source))
    assert got["passed"] is False
    assert any("承接" in p for p in got["problems"])


def test_判分器抓得到拒答与否错了(registry, source):
    case = copy.deepcopy(_case("V-027"))
    case["expected"]["refused"] = False
    got = judge_case(case, _report(case, registry, source))
    assert got["passed"] is False
    assert any("拒答" in p for p in got["problems"])


# --------------------------------------------------------------------------
# 3. 套件本身的形状
# --------------------------------------------------------------------------


def test_五态在题面里都出现过():
    """一个题集若从不期望某个判定，那个判定在这套题里等于没被考。"""
    出现 = set()
    for path in sorted((SUITE / "cases").glob("*.yaml")):
        case = yaml.safe_load(path.read_text(encoding="utf-8"))
        for c in (case.get("expected") or {}).get("claims") or []:
            出现.add(c["verdict"])
    assert 出现 == set(VERDICTS), 出现


def test_两种读法都考到了():
    读法 = set()
    for path in sorted((SUITE / "cases").glob("*.yaml")):
        case = yaml.safe_load(path.read_text(encoding="utf-8"))
        读法.add((case.get("expected") or {}).get("read_as"))
    assert 读法 == {r.name for r in ReadAs}


def test_题面不重复():
    见过 = {}
    for path in sorted((SUITE / "cases").glob("*.yaml")):
        case = yaml.safe_load(path.read_text(encoding="utf-8"))
        正文 = " ".join(str(case["conclusion"]).split())
        assert 正文 not in 见过, f"{path.name} 与 {见过.get(正文)} 题面相同"
        见过[正文] = path.name


# --------------------------------------------------------------------------
# 4. 独立复核（2026-09-11）之后补的负控制
# --------------------------------------------------------------------------


def test_期望的切分不是真的一段时必须报红():
    """🔴 门禁原来做的是**子串包含**，而 FREEZE.md 把这条列成「要害」。

    `毛利率` 是题面的子串，但 `split_segments` 切不出这一段 ——
    措辞比实现强，就是一句不成立的话。现在它真的用切分器切。
    """
    坏 = copy.deepcopy(_case("V-017"))
    坏["expected"]["claims"][0]["text"] = "速动比率"  # 是子串，不是一段
    问题 = _pregate_verify_case(_FakePath, 坏)
    assert any("不是这段话切出来的任何一段" in p for p in 问题), 问题


def test_跑评测时也验一次封闭集(monkeypatch):
    """冻结之后实现单方面加第六态，跑评测也要红 —— 不能只在冻结时验。"""
    import eval.verify_run as vr

    monkeypatch.setattr(
        vr, "_check_closed_verdicts", lambda: ["造出来的：五态封闭集被改动了"]
    )
    码 = vr.main(["--suite", "frozen-04"])
    assert 码 == 1


def test_is_verify_suite_真的被用上了():
    """`is_verify_suite` 曾是死代码，判据在三处内联重复。"""
    import inspect

    import eval.freeze as fz

    源 = inspect.getsource(fz.pregate)
    assert "is_verify_suite(" in 源
    assert fz.is_verify_suite([{"category": "V1"}]) is True
    assert fz.is_verify_suite([{"category": "C1"}]) is False


# --------------------------------------------------------------------------
# 5. `N-86` 补上的三处判据，逐条造回归（2026-10-31，`D-045` 同一轮）
# --------------------------------------------------------------------------


def test_判分器抓得到抽出来的数错了(registry, source):
    """🔴 `N-86` ②：切分对、判定"对"、而抽出来的是另一个数。

    实测过的那个形状是「第 4 季度速动比率 3.67」抽出季度序号 `4`
    （见 `frozen-04/cases/V-032.yaml` 的题面）。判分器原先一个字都不看它。
    """
    case = copy.deepcopy(_case("V-017"))
    case["expected"]["claims"][0]["stated_text"] = "9.99"
    got = judge_case(case, _report(case, registry, source))
    assert got["passed"] is False
    assert any("抽出来的数" in p for p in got["problems"]), got["problems"]


def test_判分器抓得到不该承接的那一维被承接了(registry, source):
    """🔴 `N-86` ③：这是冻结题集里**第一条**反向承接判据。

    `V-031` 第 2 条实际承接的是期间（2023）。把 `not_inherited` 改成 `2023`
    就等于声明「这一维不许承接」，而它确实承接了 ⇒ 必须红。
    """
    case = copy.deepcopy(_case("V-031"))
    case["expected"]["claims"][1]["not_inherited"] = ["2023"]
    got = judge_case(case, _report(case, registry, source))
    assert got["passed"] is False
    assert any("不许被承接" in p for p in got["problems"]), got["problems"]


def test_判分器抓得到声明了一个字都不许承接而实际承接了(registry, source):
    """`inherited: false` 与「没写 inherited」不是一回事 —— 后者不判。"""
    case = copy.deepcopy(_case("V-025"))
    case["expected"]["claims"][1].pop("inherited")
    case["expected"]["claims"][1]["inherited"] = False
    got = judge_case(case, _report(case, registry, source))
    assert got["passed"] is False
    assert any("一个字都不许承接" in p for p in got["problems"]), got["problems"]


def test_没写承接判据时判分器不管承接(registry, source):
    """反方向：不声明就不判。否则 14 道承继来的老题会一起变成「缺字段」。"""
    case = copy.deepcopy(_case("V-025"))
    case["expected"]["claims"][1].pop("inherited")
    assert judge_case(case, _report(case, registry, source))["passed"] is True


def test_判分器抓得到答案的指标错了(registry, source):
    """🔴 `N-86` ①：读成提问那几题原先只验「拒没拒答」。

    实测：把 `V-001` 的报告换成万华化学的资产负债率，照样 `passed: True`。
    """
    case = copy.deepcopy(_case("V-015"))
    case["expected"]["answer"]["metric_id"] = "debt_to_asset_ratio"
    got = judge_case(case, _report(case, registry, source))
    assert got["passed"] is False
    assert any("答案的指标" in p for p in got["problems"]), got["problems"]


def test_判分器抓得到答案的取值错了(registry, source):
    case = copy.deepcopy(_case("V-015"))
    case["expected"]["answer"]["value"] = "3.67"
    got = judge_case(case, _report(case, registry, source))
    assert got["passed"] is False
    assert any("答案的取值" in p for p in got["problems"]), got["problems"]


def test_门禁拒绝抽不出来的stated_text():
    """与「切不出来的切分」同一条原理：抽不出来的期望永远不可能命中。"""
    坏 = copy.deepcopy(_case("V-017"))
    坏["expected"]["claims"][0]["stated_text"] = "题面里没有这个数"
    问题 = _pregate_verify_case(_FakePath, 坏)
    assert any("不在这一条声明" in p for p in 问题), 问题


def test_门禁拒绝不带引号的取值():
    """🔴 这一条是 2026-10-31 实地栽过一次之后加的。

    `value: 3.670351116817004026158851655` 不加引号时 YAML 读成 float，
    **静默截到 17 位**，而判分器比的是 `str(Decimal)` 的全位 ⇒ 永远不可能命中。
    frozen-04 的第一次冻结因此被整批丢弃重做，记录在 `frozen-04/FREEZE.md`。
    """
    坏 = copy.deepcopy(_case("V-015"))
    坏["expected"]["answer"]["value"] = 3.670351116817004026158851655
    问题 = _pregate_verify_case(_FakePath, 坏)
    assert any("必须写成带引号的字符串" in p for p in 问题), 问题


def test_门禁拒绝answer引用不存在的指标():
    坏 = copy.deepcopy(_case("V-015"))
    坏["expected"]["answer"]["metric_id"] = "口径界的不存在指标"
    问题 = _pregate_verify_case(_FakePath, 坏)
    assert any("在 metrics/ 中不存在" in p for p in 问题), 问题


def test_门禁拒绝answer挂在待核声明上():
    坏 = copy.deepcopy(_case("V-017"))
    坏["expected"]["answer"] = {"metric_id": "quick_ratio"}
    问题 = _pregate_verify_case(_FakePath, 坏)
    assert any("只在 read_as 是 QUESTION 时有意义" in p for p in 问题), 问题


def test_门禁拒绝not_inherited不是列表():
    坏 = copy.deepcopy(_case("V-031"))
    坏["expected"]["claims"][1]["not_inherited"] = "600519"
    问题 = _pregate_verify_case(_FakePath, 坏)
    assert any("非空字符串列表" in p for p in 问题), 问题


# --------------------------------------------------------------------------
# 6. 整批作废（`D-012` 修订三）的机械形态
# --------------------------------------------------------------------------


def test_整批作废的套件拒绝判分():
    """🔴 写在散文里的作废挡不住下一个人打出一行分数再去引用它。

    `frozen-03` 已按 `D-012` 修订三整批作废（3/14 = 21.4% > 10%）。
    """
    import eval.verify_run as vr

    assert vr.void_record(VOIDED_SUITE) is not None
    assert vr.void_record(SUITE) is None
    assert vr.main(["--suite", "frozen-03"]) == vr.EXIT_SUITE_VOIDED


def test_作废的那三题在作废记录里逐个点名():
    """作废必须公开列出，不许静默消失（`D-012` 修订二）。"""
    import eval.verify_run as vr

    rec = vr.void_record(VOIDED_SUITE)
    assert set(rec["cases"]) == {"V-003", "V-004", "V-012"}
    assert rec["replaced_by"] == "frozen-04"
    for why in rec["cases"].values():
        assert "矛盾" in why


def test_作废的那一批文件一个字节都没被改过():
    """🔴 作废不是修改。那 14 份题面是一份历史记录，哈希必须照旧对得上。"""
    from eval.run import verify_freeze

    ok, problems = verify_freeze(VOIDED_SUITE)
    assert ok, problems


def test_作废率超过上限时整批判为构造失败(tmp_path, monkeypatch):
    """造回归：拿 frozen-04 复制一份，作废 3/18 = 16.7% > 10%，必须非零退出。

    这一条此前**在核查套件这一侧完全不存在** —— `MAX_VOID_RATIO` 只在
    `run.py` 里被用上，而 `N-84` 第一次用到它时作废率就是 21.4%。
    """
    import hashlib
    import shutil

    import eval.verify_run as vr

    suite = tmp_path / "frozen-试"
    shutil.copytree(SUITE, suite)
    for cid in ("V-022", "V-023", "V-028"):
        p = suite / "cases" / f"{cid}.yaml"
        p.write_bytes(
            p.read_text(encoding="utf-8").encode("utf-8")
            + 'voided: "造出来的构造错误"\n'.encode("utf-8")
        )
    # 清单跟着重算 —— 这一条考的是作废率上限，不是哈希校验。
    lines = []
    for p in sorted((suite / "cases").glob("*.yaml")):
        lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()} *cases/{p.name}")
    (suite / "SHA256SUMS").write_bytes(("\n".join(lines) + "\n").encode("utf-8"))

    报告 = vr.run_suite(suite)
    assert 报告["counts"]["voided"] == 3
    assert 报告["counts"]["authored"] == 18
    assert 报告["void_ratio"] == pytest.approx(3 / 18, abs=1e-4)
    assert 报告["void_ratio_within_limit"] is False
    assert "整批作废重建" in vr.render(报告)

    # 退出码也要非零：一个粉饰过的满分不比一道红题好。
    monkeypatch.setattr(vr, "EVAL_ROOT", tmp_path)
    assert vr.main(["--suite", suite.name, "--report", str(tmp_path)]) == 1


def test_作废率在上限内时照常判分(tmp_path):
    """反方向：1/18 = 5.6% ≤ 10% ⇒ 移出分母、单独列出、照常报分数。"""
    import hashlib
    import shutil

    import eval.verify_run as vr

    suite = tmp_path / "frozen-试2"
    shutil.copytree(SUITE, suite)
    p = suite / "cases" / "V-022.yaml"
    p.write_bytes(
        p.read_text(encoding="utf-8").encode("utf-8")
        + 'voided: "造出来的构造错误"\n'.encode("utf-8")
    )
    报告 = vr.run_suite(suite)
    assert 报告["counts"]["voided"] == 1
    assert 报告["counts"]["total"] == 17
    assert 报告["void_ratio_within_limit"] is True
    assert "[VOID] V-022" in vr.render(报告)
    assert "整批作废重建" not in vr.render(报告)


# --------------------------------------------------------------------------
# 7. 承继关系：重建批次不许丢覆盖面
# --------------------------------------------------------------------------


def test_承继表里的十四题在本批里都有对应():
    """`frozen-03` 的 11 道存活题 + 3 道作废题，题面都必须在本批里找得到 ——
    否则「整批重建」会悄悄变成「整批缩水」。"""
    旧 = {}
    for path in sorted((VOIDED_SUITE / "cases").glob("*.yaml")):
        case = yaml.safe_load(path.read_text(encoding="utf-8"))
        旧[" ".join(str(case["conclusion"]).split())] = case["id"]
    新 = set()
    for path in sorted((SUITE / "cases").glob("*.yaml")):
        case = yaml.safe_load(path.read_text(encoding="utf-8"))
        新.add(" ".join(str(case["conclusion"]).split()))
    assert len(旧) == 14
    缺的 = {v: k for k, v in 旧.items() if k not in 新}
    assert 缺的 == {}, f"重建批次丢了这些题面：{缺的}"


def test_本批比旧批多出来的四题是新增的():
    assert len(list((SUITE / "cases").glob("*.yaml"))) == 18
