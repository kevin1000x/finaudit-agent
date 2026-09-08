"""`eval/attribution.py` 的回归（`02-02` T1 / T2 / T3，`D-035`）。

这个模块的价值全在「归因是**从机读状态算出来的**，不是判分分支里手写的一个层名」。
所以本文件盯四件事：

1. **封闭枚举穷举** —— 每一支 `RefusalCode` 都有落点，没有兜底分支
2. **归因不改分数**（`EVAL_CASES` §5.1）—— 换一套归因，除「归因覆盖率」外逐字不变
3. **判据不碰措辞**（§5.3）—— 语法树断言，不是 `in` 子串
4. **`attribution_hint` 判分时不可见**（§3.1）—— 语法树断言判分函数没读过它
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

from eval.attribution import (  # noqa: E402
    LAYERS,
    reachable_layers,
    REFUSAL_LAYERS,
    Attribution,
    FailureKind,
    attribute,
)
from eval.run import FAIL, PASS, main, run_suite  # noqa: E402
from semantic_layer.resolve import RefusalCode  # noqa: E402

FROZEN = REPO / "eval" / "frozen-01"


# ── 1. 封闭枚举穷举 ────────────────────────────────────────────────


def test_每一支拒答码都有归因落点():
    """🔴 **加第十一支时这条先红。**

    与 `resolve.py` 那两条锁枚举大小的测试同一个用意：让「多一支」
    必须先过一次归因决策，而不是被一个兜底分支静默吸收。
    """
    codes = list(RefusalCode)
    assert len(codes) == 10, f"枚举现在有 {len(codes)} 支，映射表与本断言要一起改"
    missing = [c.name for c in codes if c not in REFUSAL_LAYERS]
    assert missing == [], "这几支拒答码没有归因落点：" + "、".join(missing)
    extra = [c.name for c in REFUSAL_LAYERS if c not in codes]
    assert extra == [], "映射表里有已经不存在的码：" + "、".join(extra)


def test_映射表给出的层都在分层表里():
    """写错一个层名（比如「證據層」）不会有任何提示 —— 除非这条查着。"""
    for code, layers in REFUSAL_LAYERS.items():
        assert layers, f"{code.name} 的落点是空的"
        for layer in layers:
            assert layer in LAYERS, f"{code.name} 归到了一个不存在的层：{layer}"


def test_每一种失败都算得出层():
    """`FailureKind` 也是封闭枚举。加一种失败而忘了给它落点 ⇒ 这条红。"""
    kinds = list(FailureKind)
    assert len(kinds) == 8, f"失败种类现在有 {len(kinds)} 种，本断言要跟着改"

    class 假答案:
        refusal = {"code": "UNDEFINED_CONDITION_HIT"}

    for kind in kinds:
        got = attribute(kind, 假答案())
        assert isinstance(got, Attribution)
        assert got.layers, f"{kind.name} 算出来的层是空的"
        assert got.basis.strip(), f"{kind.name} 没说清判据来自哪个机读状态"
        for layer in got.layers:
            assert layer in LAYERS


def test_拒答但拿不到码时炸掉_而不是猜一个层():
    """没有机读状态就**不许猜**。悄悄归一个层 = 造一个查不出来的假归因。"""

    class 没有码:
        refusal = None

    with pytest.raises(ValueError):
        attribute(FailureKind.REFUSED_BUT_SHOULD_ANSWER, 没有码())


# ── 2. 意图层：`D-035` ③ 划的那条边界 ──────────────────────────────


def test_意图不完整归意图层_而认不出指标名归口径层():
    """🔴 `D-035` ③ 的边界，两边都验。

    `INTENT_INCOMPLETE`（题面缺主体 / 多期间）与口径无关；
    `METRIC_NOT_DEFINED`（别名表认不出这个说法）是**口径产物**没覆盖。
    只验一边的话，把两支都映到同一个层也能过。
    """

    def 答案(code):
        return type("A", (), {"refusal": {"code": code}})()

    intent = attribute(FailureKind.REFUSED_BUT_SHOULD_ANSWER, 答案("INTENT_INCOMPLETE"))
    definition = attribute(FailureKind.REFUSED_BUT_SHOULD_ANSWER, 答案("METRIC_NOT_DEFINED"))
    assert intent.layers == ("意图层",)
    assert definition.layers == ("口径层",)
    assert intent.layers != definition.layers


def test_frozen01_上那道意图题确实落在意图层():
    """不是构造出来的：`Q-C3-004`（题面里两个期间）。

    它会红的场景：有人把 `INTENT_INCOMPLETE` 改回口径层 ——
    那会让「归因覆盖率 100%」变成一句假话。

    ⚠️ **2026-09-09 从两道缩到一道，而且是好事**：原来还有 `Q-C3-003`
    （「华鑫科技 2023 年的资产负债率」，题面只有公司名没有代码）。
    `N-65` 落地之后它**不再 FAIL** —— 简称查表查到 900001，答出 0.55。
    这条断言当时立刻报红，报的是「`Q-C3-003` 不再是 FAIL，本断言要重新看」，
    正是它被写出来要做的事。⇒ 缩小的是**覆盖面**，不是纪律：
    剩下这一道仍然守着同一条性质。
    """
    report = run_suite(FROZEN)
    by_id = {r["id"]: r for r in report["results"]}
    assert by_id["Q-C3-003"]["status"] == PASS, (
        "`Q-C3-003` 又变回 FAIL 了 —— `N-65`（简称→代码）可能被改坏了"
    )
    for cid in ("Q-C3-004",):
        assert by_id[cid]["status"] == FAIL, f"{cid} 不再是 FAIL，本断言要重新看"
        assert by_id[cid]["attribution"] == ["意图层"], (
            f"{cid} 归到了 {by_id[cid]['attribution']}"
        )
        assert by_id[cid]["attribution_basis"] == "RefusalCode.INTENT_INCOMPLETE"


# ── 3. 归因不改分数（`EVAL_CASES` §5.1） ───────────────────────────


def test_换一套归因_分数逐字不变(monkeypatch):
    """🔴 §5.1 的硬约束，**这条本身就是负控制**。

    ⚠️ 不能写成「断言归因不为空」那种自证 —— 它要证的是**分数与归因无关**。
    做法：把归因函数整体换成「每道题都返回另一组层」，重跑同一套件，
    断言 `counts`、`by_category`、以及除「归因覆盖率」外的 §6 指标逐字不变。
    """
    before = run_suite(FROZEN)

    import eval.run as runner

    monkeypatch.setattr(
        runner, "attribute", lambda kind, answer=None: Attribution(("表达层",), "负控制")
    )
    after = run_suite(FROZEN)

    assert before["counts"] == after["counts"]
    assert before["by_category"] == after["by_category"]
    assert before["c2_refusal_gate"] == after["c2_refusal_gate"]
    assert before["void_ratio"] == after["void_ratio"]

    for name, value in before["metrics"].items():
        if name == "归因覆盖率":
            continue
        assert after["metrics"][name] == value, f"换了归因之后「{name}」变了"

    # 反空转：归因**确实**被换掉了，否则上面那些「不变」什么都没证
    changed = [r for r in after["results"] if r["status"] == FAIL]
    assert changed, "这一批没有失败题，本条在空转"
    assert all(r["attribution"] == ["表达层"] for r in changed)
    assert any(
        r["attribution"] != next(b["attribution"] for b in before["results"] if b["id"] == r["id"])
        for r in changed
    ), "换前换后归因一模一样，本条在空转"


# ── 4. `AC-08` 的门（`02-02` T2） ─────────────────────────────────


#: 只有 **1 道 FAIL** 的套件。`AC-08` 的负控制必须在这上面做 ——
#: 在 frozen-01（4 道 FAIL）上做，`main()` 本来就返回非零，
#: **红的原因不是它声称在查的那件事**（`EVAL_CASES` 的 `J-5`，本仓 2026-08-24 同型实例）。
SINGLE_FAIL_SUITE = "testdata/sample-suite"


def test_出现未归因的失败时评测非零退出并点名(monkeypatch, tmp_path, capsys):
    """🔴 `AC-08` 是**保证类**标准：一道未归因的失败即不满足。

    退出码用 `3`，与「有失败题」的 `1` **分开** ——
    混成同一个数，CI 里就分不出「系统答错了」和「评测自己坏了」。
    """
    import eval.run as runner

    baseline = main(["--suite", SINGLE_FAIL_SUITE, "--report", str(tmp_path)])
    assert baseline == 1, f"这个套件本来该因为有 1 道 FAIL 返回 1，实际 {baseline}"

    monkeypatch.setattr(runner, "attribute", lambda kind, answer=None: Attribution((), "负控制"))
    capsys.readouterr()
    code = main(["--suite", SINGLE_FAIL_SUITE, "--report", str(tmp_path)])
    assert code == 3, f"未归因的失败没有让评测走 AC-08 那条退出码，实际 {code}"

    err = capsys.readouterr().err
    assert "AC-08" in err
    assert "S-C2-002" in err, "非零退出了却没点名是哪一道题"


def test_归因齐全时不走AC08那条退出码(tmp_path):
    """反向：正常情况下退出码是 `1`（有失败题），不是 `3`。

    没有这一条，一个「永远返回 3」的实现也能满足上面那条。
    """
    code = main(["--suite", "frozen-01", "--report", str(tmp_path)])
    assert code == 1, f"frozen-01 有 4 道 FAIL，期望退出码 1，实际 {code}"


def test_未执行与作废的题一律不带层():
    """**`AC-08` 的分母是「失败题」，不是「非通过题」。**

    `NOT_RUN` 是**能力缺口的声明**不是失败；`VOIDED` 按 §2.2 已在分母之外。
    给它们挂层会让那一层的数字虚高 —— 与 §5.0 给 `UNPARSEABLE` 立的是同一条规则。
    """
    report = run_suite(FROZEN)
    not_run = [r for r in report["results"] if r["status"] == "NOT_RUN"]
    assert len(not_run) == 5, f"frozen-01 该有 5 道 NOT_RUN，实际 {len(not_run)}"
    for r in not_run:
        assert r["attribution"] == [], f"{r['id']} 是 NOT_RUN 却带了层 {r['attribution']}"
        assert r["attribution_basis"] == ""


def test_零产出的层在报告里看得见():
    """一个定义了却从没被吐出来过的层是 `L-25` 那种死抽象 ——
    它藏在「归因覆盖率 100%」后面完全看不出来。

    ⚠️ **这条不断言「哪几层是零」**：那会把当下的实测钉成规格。
    它断言的是**报告里有这个数**，且五层一个不少。
    """
    report = run_suite(FROZEN)
    usage = report["layer_usage"]
    assert set(usage) == set(LAYERS), "层用量表漏了层"
    assert sum(usage.values()) >= 1, "一层都没吃到失败题，本条在空转"
    # 实测（2026-09-05）：检索层与表达层零产出。这里只断言「数得出来」。
    assert all(isinstance(v, int) for v in usage.values())


def test_本批零产出与结构上不可达是两件事():
    """🔴 混成一句「零产出」，读的人会以为再多跑几批就有了 ——
    而**不可达**的那个再跑一万批也不会有。

    实测（2026-09-05）：`表达层` **结构上不可达** —— `J-6` / `J-7`
    要到 Phase 3 的真实抽取路径才可能触发，当前实现里没有任何一条路产得出它。
    `检索层` / `计算层` 是本批零产出，但结构上产得出来。
    """
    reachable = reachable_layers()
    assert "表达层" not in reachable, (
        "表达层现在产得出来了 —— 那是好事，但 EVAL_CASES §5.5、D-035 与本断言要一起改"
    )
    for layer in ("意图层", "检索层", "口径层", "计算层"):
        assert layer in reachable, f"{layer} 变成不可达了"

    report = run_suite(FROZEN)
    assert report["unreachable_layers"] == ["表达层"]


def test_可达层是从映射表算出来的_不是手写的(monkeypatch):
    """负控制：给 `RECONCILIATION_FAILED` 挂上表达层，它必须立刻变成可达。

    没有这一条，`reachable_layers()` 可以是一句写死的 `return LAYERS[:4]`。
    """
    assert "表达层" not in reachable_layers()
    monkeypatch.setitem(REFUSAL_LAYERS, RefusalCode.RECONCILIATION_FAILED, ("表达层",))
    assert "表达层" in reachable_layers(), "改了映射表，可达层却没跟着变 —— 它是写死的"


# ── 5. 判据不碰措辞、hint 判分时不可见（语法树，不用 `in` 子串） ────


def _fn(path: Path, name: str):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return next(
        n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name
    )


def test_归因模块一次都没读过detail():
    """🔴 `EVAL_CASES` §5.3 硬约束：判据不得建立在被抽取文本的措辞上。

    走语法树而不是 `in` 子串 —— 注释里出现 `detail` 就能满足 `in`（`RV-9`）。
    """
    src = REPO / "eval" / "attribution.py"
    tree = ast.parse(src.read_text(encoding="utf-8"), filename=str(src))
    hits = [
        n.lineno
        for n in ast.walk(tree)
        if (isinstance(n, ast.Attribute) and n.attr == "detail")
        or (isinstance(n, ast.Constant) and n.value == "detail")
    ]
    assert hits == [], f"归因模块读了 detail（行 {hits}）—— 那是措辞，不是机读状态"


@pytest.mark.parametrize("fn_name", ["judge_refusal_case", "judge_answer_case"])
def test_判分函数一次都没读过attribution_hint(fn_name: str):
    """`EVAL_CASES` §3.1：`attribution_hint` **判分时不可见**。

    它会红的场景：有人为了让归因「更准」，在判分时偷看出题人的预判 ——
    那会让 T3 那张对照表变成自证。
    """
    fn = _fn(REPO / "eval" / "run.py", fn_name)
    hits = [
        n.lineno
        for n in ast.walk(fn)
        if isinstance(n, ast.Constant) and n.value == "attribution_hint"
    ]
    assert hits == [], f"{fn_name} 读了 attribution_hint（行 {hits}）"


def test_hint对照表只列失败题且不折成一个准确率():
    """hint 是**出题时预判**的陷阱，实际归因是**这一次真实**的失败点。

    折成百分比会立刻被读成「归因准了几成」，那是个不存在的东西。
    """
    report = run_suite(FROZEN)
    rows = report["attribution_hint_comparison"]
    failed = {r["id"] for r in report["results"] if r["status"] == FAIL}
    assert failed, "这一批没有失败题，本条在空转"
    assert {r["case"] for r in rows} == failed, "对照表列的不是失败题那一批"
    for row in rows:
        assert row["actual_layers"], f"{row['case']} 实际归因是空的"
        assert row["basis"], f"{row['case']} 没记判据"
    # 报告里不许出现任何形如「归因一致率」的指标
    assert not [k for k in report["metrics"] if "一致" in k and "归因" in k]
