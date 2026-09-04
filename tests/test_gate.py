"""`src/agent/gate.py` 的回归（`02-01` T2）。

两条结构性质，缺一条这道闸门就不成立：

1. **不存在任何配置或插件路径能绕过它** —— 执行入口只有一个，且无条件先过闸门。
2. **被拒答的请求同样留下完整日志** —— 与成功请求**同一套**出处字段。
   ⚠️ 拒答少记字段是最容易犯的：**拒答恰恰是最需要能复核的那一类**。

## `AC-09` 的负控制在这里是常跑的一对，不是手工程序

`AC-09` 2026-08-27 加强过：不只要求「危险样本被拒」，还要求
**「把那道校验移除后，该样本确实被放行」** —— 否则你验的不是这道闸门（`N-45`）。

本文件把它做成**每个样本一对断言**：带着该检查跑 ⇒ 拒；抽掉该检查跑 ⇒ 放行。
这一对不可能同时被一个「从不触发的检查」满足：
从不触发的检查会让第一条断言先红。
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest

from agent.gate import CHECKS, GateRequest, execute, pre_execute
from semantic_layer import dsl
from semantic_layer.definition import load_definition
from semantic_layer.resolve import Refusal, RefusalCode

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture
def defn():
    return load_definition(REPO / "metrics" / "current_ratio.yaml")


def _req(defn, tree=None, **kw):
    base = dict(
        defn=defn,
        expected_version=defn.version,
        # 默认那棵树必须是**这份定义真的声明过**的字段 —— 否则夹具自己就违规，
        # 于是每一条负控制都会被「字段未声明」那道检查接住，假红。
        tree=tree if tree is not None else dsl.parse_condition(
            "bs.total_current_liabilities_period_end > 0"
        ).tree,
        entity="600519",
        period=2023,
        question_sha256="0" * 64,
    )
    base.update(kw)
    return GateRequest(**base)


def _without(name: str):
    """抽掉一道检查 —— `AC-09` 的负控制。"""
    return tuple(c for c in CHECKS if c.name != name)


def _names():
    return [c.name for c in CHECKS]


# ── 结构性质 ────────────────────────────────────────────────────────────


def test_危险请求下计算函数一次都不会被调用(defn):
    """🔴 「闸门不可绕过」是结构性质。

    它会红的场景：有人把 `run` 挪到 `pre_execute` 之前，或加一条
    「校验失败也继续算，只是标一下」的旁路。
    """
    called = []
    rec = execute(_req(defn, tree=dsl.FieldRef("secret.api_key")), run=lambda r: called.append(r))
    assert called == [], "闸门未通过时计算函数被调用了"
    assert rec.gate == "refused"
    assert rec.result is None


def test_拒答与放行留下同一套出处字段(defn):
    """拒答少记字段是最容易犯的 —— 而拒答恰恰最需要能复核。"""
    ok = execute(_req(defn), run=lambda r: 1.23)
    bad = execute(_req(defn, tree=dsl.FieldRef("secret.api_key")), run=lambda r: 1.23)

    assert ok.gate == "passed" and bad.gate == "refused"
    assert set(ok.to_dict()) == set(bad.to_dict()), "两条路径的字段集合必须一样"
    for rec in (ok, bad):
        d = rec.to_dict()
        for key in ("question_sha256", "metric_id", "metric_version", "entity",
                    "period", "referenced_fields", "gate"):
            assert d[key] not in (None, "", [], {}), f"{key} 在 {rec.gate} 路径上是空的"
    assert bad.to_dict()["refusal"] is not None and ok.to_dict()["refusal"] is None


def test_每道检查都在注册表里具名(defn):
    """没具名就没法给它写负控制 —— 那正是 `AC-09` 加强前的漏洞形状。"""
    assert _names() == [
        "定义合规",
        "口径版本匹配",
        "封闭节点集",
        "授权命名空间",
        "字段已在定义中声明",
    ]


# ── 五个危险样本，每个一对（带检查 ⇒ 拒；抽掉检查 ⇒ 放行）────────────────


def test_样本1_未授权命名空间(defn):
    req = _req(defn, tree=dsl.FieldRef("secret.api_key"))
    got = pre_execute(req)
    assert isinstance(got, Refusal) and "secret" in got.detail
    assert pre_execute(req, checks=_without("授权命名空间")) is not None, (
        "抽掉这道检查后应当由下一道（字段未声明）接住"
    )


def test_样本1_负控制_两道都抽掉才放行(defn):
    """`secret.api_key` 同时违反两条 —— 负控制要把两道都抽掉才能证明它被放行。

    ⚠️ 这一条不是凑数：只抽一道就断言「放行」会**假绿**，
    因为放行它的是另一道检查的缺席。
    """
    req = _req(defn, tree=dsl.FieldRef("secret.api_key"))
    checks = tuple(c for c in CHECKS if c.name not in {"授权命名空间", "字段已在定义中声明"})
    assert pre_execute(req, checks=checks) is None


def test_样本2_已授权命名空间但定义没声明该字段(defn):
    req = _req(defn, tree=dsl.FieldRef("bs.从未声明过的字段"))
    got = pre_execute(req)
    assert isinstance(got, Refusal) and "从未声明过的字段" in got.detail
    assert pre_execute(req, checks=_without("字段已在定义中声明")) is None


def test_样本3_口径版本不匹配(defn):
    req = _req(defn, expected_version=1)
    got = pre_execute(req)
    assert isinstance(got, Refusal)
    assert got.code is RefusalCode.CROSS_VERSION_COMPARISON
    assert pre_execute(req, checks=_without("口径版本匹配")) is None


def test_样本4_定义本身不合规(defn):
    object.__setattr__(defn, "parse_error", "YAML 语法错误：模拟")
    req = _req(defn)
    got = pre_execute(req)
    assert isinstance(got, Refusal)
    assert got.code is RefusalCode.DEFINITION_NONCONFORMANT
    assert pre_execute(req, checks=_without("定义合规")) is None


def test_样本5_语法树里混进封闭节点集之外的东西(defn):
    """`PROJECT_SPEC` §5.1：静态检查的对象**必须是一个封闭的节点集**。

    受限语法是这条闸门成立的前提；有人塞进一个新节点类型 ⇒ 前提没了。
    """

    @dataclass(frozen=True)
    class 偷渡节点:
        payload: str

    req = _req(defn, tree=偷渡节点("os.system('rm -rf /')"))
    got = pre_execute(req)
    assert isinstance(got, Refusal)
    assert "偷渡节点" in got.detail
    assert pre_execute(req, checks=_without("封闭节点集")) is None


# ── 正向 ────────────────────────────────────────────────────────────────


def test_定义自己声明的条件全部过闸(defn):
    """闸门不能把正常的东西也拦下来 —— 那样它就只是个 `return False`。"""
    for cond in defn.undefined_conditions:
        if not cond.expr:
            continue
        req = _req(defn, tree=dsl.parse_condition(cond.expr).tree)
        assert pre_execute(req) is None, f"闸门拦下了定义自己的条件：{cond.expr}"


# ── 「唯一入口且无条件先过闸门」的结构断言 ────────────────────────────


def test_execute_里_pre_execute_排在调用_run_之前():
    """spy 测只证了「这一次拒答没调 run」；这一条证的是**结构**。

    走语法树：在 `execute` 的函数体里，`pre_execute(...)` 的调用必须
    出现在任何 `run(...)` 调用之前。

    它会红的场景：有人为了「先算出来再看要不要拦」把两句对调，
    或加一条 `if fast_path: return run(req)` 的旁路。
    """
    import agent.gate as gate

    tree = ast.parse(Path(gate.__file__).read_text(encoding="utf-8"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "execute")
    calls = [
        (n.lineno, n.func.id)
        for n in ast.walk(fn)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    ]
    gate_at = [ln for ln, name in calls if name == "pre_execute"]
    run_at = [ln for ln, name in calls if name == "run"]
    assert gate_at, "execute 里没有调用 pre_execute"
    assert run_at, "execute 里没有调用 run —— 那这条断言在空转"
    assert min(gate_at) < min(run_at), "run 出现在闸门之前"


def test_execute_不接受_checks_参数():
    """`checks` 是负控制入口。给 `execute` 留这个参数，
    就等于留了一条「配置掉一道检查」的旁路 —— 而 `SC-6` 要的正是没有这种路。
    """
    import inspect

    from agent.gate import execute as ex

    assert "checks" not in inspect.signature(ex).parameters


def test_模块里没有第二个会调用_run_的公开函数():
    """「执行入口只有一个」。第二个入口 = 第二条不受闸门管的路。"""
    import agent.gate as gate

    tree = ast.parse(Path(gate.__file__).read_text(encoding="utf-8"))
    callers = {
        n.name
        for n in tree.body
        if isinstance(n, ast.FunctionDef)
        and any(
            isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == "run"
            for c in ast.walk(n)
        )
    }
    assert callers == {"execute"}
