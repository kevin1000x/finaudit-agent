"""`frozen-03`（核查层评测集）的门禁与判分（`D-041` §5）。

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
SUITE = REPO / "eval" / "frozen-03"


def _case(name="V-003"):
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
    坏 = copy.deepcopy(_case("V-001"))
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
    case = _case("V-003")
    assert judge_case(case, _report(case, registry, source))["passed"] is True


def test_判分器抓得到判定错了(registry, source):
    case = copy.deepcopy(_case("V-003"))
    case["expected"]["claims"][0]["verdict"] = "INCONSISTENT"
    got = judge_case(case, _report(case, registry, source))
    assert got["passed"] is False
    assert any("判定" in p for p in got["problems"])


def test_判分器抓得到切分错了(registry, source):
    """🔴 切分本身是被判分的一部分 —— 只判五态会让「切错但碰巧判对」拿满分。"""
    case = copy.deepcopy(_case("V-011"))
    case["expected"]["claims"] = case["expected"]["claims"][:1]
    got = judge_case(case, _report(case, registry, source))
    assert got["passed"] is False
    assert any("切分" in p for p in got["problems"])


def test_判分器抓得到读成什么错了(registry, source):
    case = copy.deepcopy(_case("V-001"))
    case["expected"]["read_as"] = "STATEMENT"
    got = judge_case(case, _report(case, registry, source))
    assert got["passed"] is False
    assert any("读成什么" in p for p in got["problems"])


def test_判分器抓得到该承接而没承接(registry, source):
    """题面声明了「这一条要承接 600519/2023」，实际没承接就得红。"""
    case = copy.deepcopy(_case("V-003"))
    case["expected"]["claims"][0]["inherited"] = "600519/2023"
    got = judge_case(case, _report(case, registry, source))
    assert got["passed"] is False
    assert any("承接" in p for p in got["problems"])


def test_判分器抓得到拒答与否错了(registry, source):
    case = copy.deepcopy(_case("V-013"))
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
    坏 = copy.deepcopy(_case("V-003"))
    坏["expected"]["claims"][0]["text"] = "速动比率"  # 是子串，不是一段
    问题 = _pregate_verify_case(_FakePath, 坏)
    assert any("不是这段话切出来的任何一段" in p for p in 问题), 问题


def test_跑评测时也验一次封闭集(monkeypatch):
    """冻结之后实现单方面加第六态，跑评测也要红 —— 不能只在冻结时验。"""
    import eval.verify_run as vr

    monkeypatch.setattr(
        vr, "_check_closed_verdicts", lambda: ["造出来的：五态封闭集被改动了"]
    )
    码 = vr.main(["--suite", "frozen-03"])
    assert 码 == 1


def test_is_verify_suite_真的被用上了():
    """`is_verify_suite` 曾是死代码，判据在三处内联重复。"""
    import inspect

    import eval.freeze as fz

    源 = inspect.getsource(fz.pregate)
    assert "is_verify_suite(" in 源
    assert fz.is_verify_suite([{"category": "V1"}]) is True
    assert fz.is_verify_suite([{"category": "C1"}]) is False
