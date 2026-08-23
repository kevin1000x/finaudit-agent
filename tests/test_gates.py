"""`scripts/check_gates.py` 的回归测试（落地待办 L-4 / L-5）。

这道门禁的对象是**我们自己的门禁与测试**，所以它自己最容易变成
它要防的那个东西：一个不会红的检查。

因此每条规则都配一条负向用例：**把缺陷造出来，看它变红**
（`references/deepseek-harness-docs-part2.md` 记的 `testing.md:34` 逐字
`A guard only guards if the regression actually fails it`）。
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "check_gates",
    Path(__file__).resolve().parent.parent / "scripts" / "check_gates.py",
)
assert _SPEC and _SPEC.loader
cg = importlib.util.module_from_spec(_SPEC)
# 必须先进 sys.modules 再 exec：`@dataclass` 会用 `sys.modules[cls.__module__]`
# 解析注解，模块不在表里时报 `'NoneType' object has no attribute '__dict__'`。
sys.modules["check_gates"] = cg
_SPEC.loader.exec_module(cg)

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture
def scratch():
    """写进真的 tests/ 目录——本门禁扫的就是这里，不能用 tmp_path 绕开。"""
    p = REPO / "tests" / "test___gate_scratch__.py"
    yield p
    if p.exists():
        p.unlink()


def _problems(path: Path) -> list[str]:
    return cg.check_module(path)[0]


def _declared(path: Path) -> dict[str, str]:
    return cg.check_module(path)[1]


# --------------------------------------------------------------------------
# R1 —— 每个 test_* 必须能失败
# --------------------------------------------------------------------------


def test_无断言的测试必须报红(scratch):
    """**这是本门禁自己的负控制**（登记在 check_gates.GATES 里）。

    hello-agents 的 6 个 `test_*.py` 共 370 行、0 个 assert，就是这个形状。
    """
    scratch.write_text("def test_看起来像测试():\n    x = 1 + 1\n", encoding="utf-8")
    problems = _problems(scratch)
    assert len(problems) == 1
    assert "没有任何可失败点" in problems[0]
    assert "test_看起来像测试" in problems[0]


def test_有断言就通过(scratch):
    scratch.write_text("def test_真的测了():\n    assert 1 + 1 == 2\n", encoding="utf-8")
    assert _problems(scratch) == []


@pytest.mark.parametrize(
    "body",
    [
        "    with pytest.raises(ValueError):\n        int('x')\n",
        "    pytest.fail('boom')\n",
        "    with pytest.warns(UserWarning):\n        pass\n",
    ],
)
def test_pytest_的失败点也算(scratch, body):
    """`assert` 不是唯一的可失败点，只认 assert 会产生大量假红。"""
    scratch.write_text("import pytest\n\n\ndef test_x():\n" + body, encoding="utf-8")
    assert _problems(scratch) == []


def test_非测试函数不被检查(scratch):
    """辅助函数没有断言是正常的，把它们算进来会让门禁不可用。"""
    scratch.write_text(
        "def _helper():\n    return 1\n\n\ndef test_x():\n    assert _helper() == 1\n",
        encoding="utf-8",
    )
    assert _problems(scratch) == []


def test_类内的测试方法也被检查(scratch):
    """按类组织的测试同样会漏断言，不能只扫顶层函数。"""
    scratch.write_text(
        "class TestGroup:\n    def test_空的(self):\n        pass\n",
        encoding="utf-8",
    )
    problems = _problems(scratch)
    assert len(problems) == 1
    assert "TestGroup::test_空的" in problems[0]


# --------------------------------------------------------------------------
# R3 —— 恒真断言不算断言
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "expr",
    ["True", "1", "'x'", "[1]", "{'a': 1}", "(1,)"],
)
def test_恒真字面量断言不算断言(scratch, expr):
    """`invariants.md:5` 禁止断言恒真物。构造上不可能红的断言等于没有断言。"""
    scratch.write_text(f"def test_x():\n    assert {expr}\n", encoding="utf-8")
    problems = _problems(scratch)
    assert len(problems) == 1, f"`assert {expr}` 应被判为恒真"


def test_自比较断言不算断言(scratch):
    """`assert x == x` 恒真，且是重构残留的常见形态。"""
    scratch.write_text("def test_x():\n    y = compute()\n    assert y == y\n", encoding="utf-8")
    assert len(_problems(scratch)) == 1


def test_假值字面量断言不算恒真(scratch):
    """`assert False` 恒假不恒真——它会红，属于合法可失败点，不该被 R3 吃掉。"""
    scratch.write_text("def test_x():\n    assert False\n", encoding="utf-8")
    assert _problems(scratch) == []


def test_空容器断言不算恒真(scratch):
    """`assert []` 恒假，同上。"""
    scratch.write_text("def test_x():\n    assert []\n", encoding="utf-8")
    assert _problems(scratch) == []


# --------------------------------------------------------------------------
# R1 的例外 —— NO-ASSERT-BY-DESIGN
# --------------------------------------------------------------------------


def test_显式声明的无断言测试可以通过(scratch):
    scratch.write_text(
        "def test_x():\n"
        "    'NO-ASSERT-BY-DESIGN: 这个测试的断言是不抛异常，抛了就说明解析器坏了。'\n"
        "    parse()\n",
        encoding="utf-8",
    )
    assert _problems(scratch) == []
    assert len(_declared(scratch)) == 1


def test_声明理由过短仍然报红(scratch):
    """光写前缀不写理由 = 用一个标记换掉一条规则，那是把门禁做成橡皮图章。"""
    scratch.write_text(
        "def test_x():\n    'NO-ASSERT-BY-DESIGN: 没啥'\n    parse()\n",
        encoding="utf-8",
    )
    problems = _problems(scratch)
    assert len(problems) == 1
    assert "理由过短" in problems[0]


def test_理由重复即模板化_必须报红():
    """反模板机制：复制粘贴必然产生重复的理由，重复即红。"""
    same = "断言是不抛异常，抛了整条链路不可用。"
    problems = cg.check_reasons_are_not_templated(
        {"tests/a.py::test_1": same, "tests/b.py::test_2": same}
    )
    assert len(problems) == 1
    assert "模板化措辞不算理由" in problems[0]
    assert "tests/a.py::test_1" in problems[0]
    assert "tests/b.py::test_2" in problems[0]


def test_理由各不相同则通过():
    problems = cg.check_reasons_are_not_templated(
        {"tests/a.py::test_1": "理由甲，说明为什么没有可断言的东西。",
         "tests/b.py::test_2": "理由乙，另一处完全不同的原因。"}
    )
    assert problems == []


# --------------------------------------------------------------------------
# R2 —— 每道门禁必须具名声明负控制
# --------------------------------------------------------------------------


def test_真实仓库的每道门禁都有具名负控制():
    """注册表与测试脱节时必须炸——否则一道门禁可以悄悄失去它的负控制。"""
    assert cg.check_gates_have_negative_controls() == []


def test_注册表指向不存在的负控制_必须报红(monkeypatch):
    """负向：这是 R2 唯一真正要防的东西。"""
    fake = cg.Gate(
        entry="python scripts/不存在.py",
        test_module="test_xrefs.py",
        negative_control="test_这个函数根本不存在",
    )
    monkeypatch.setattr(cg, "GATES", (fake,))
    problems = cg.check_gates_have_negative_controls()
    assert len(problems) == 1
    assert "不存在" in problems[0]
    assert "注册表与测试已脱节" in problems[0]


def test_注册表指向不存在的测试模块_必须报红(monkeypatch):
    fake = cg.Gate(
        entry="python scripts/x.py",
        test_module="test_根本没有这个模块.py",
        negative_control="test_x",
    )
    monkeypatch.setattr(cg, "GATES", (fake,))
    problems = cg.check_gates_have_negative_controls()
    assert len(problems) == 1
    assert "不存在" in problems[0]


def test_负控制自己没有断言_必须报红(scratch, monkeypatch):
    """一个不会红的负控制证明不了任何事——R2 必须连带查 R1。"""
    scratch.write_text("def test_假负控制():\n    pass\n", encoding="utf-8")
    fake = cg.Gate(
        entry="python scripts/x.py",
        test_module=scratch.name,
        negative_control="test_假负控制",
    )
    monkeypatch.setattr(cg, "GATES", (fake,))
    problems = cg.check_gates_have_negative_controls()
    assert len(problems) == 1
    assert "没有可失败点" in problems[0]


# --------------------------------------------------------------------------
# 现状锁定
# --------------------------------------------------------------------------


def test_豁免清单为空且间接断言清单为空():
    """两张清单一旦长起来，本门禁就退化成一张「已知例外」的目录。

    与它要防的毛病同型——`check_reading_ledger.py` 有同款约束。
    """
    assert cg.EXEMPT_TESTS == frozenset(), "无理由豁免不该存在，用 NO-ASSERT-BY-DESIGN 写明理由"
    assert cg.INDIRECT_ASSERT_HELPERS == frozenset()


def test_无断言声明的数量被锁住():
    """R1 的例外**只有一条在用**（`test_scan.py` 的二进制文件用例）。

    这个数字长起来就等于 R1 在退化。改动它必须是有意识的决定，不是顺手加。
    """
    declared: dict[str, str] = {}
    for path in sorted((REPO / "tests").glob("test_*.py")):
        declared.update(cg.check_module(path)[1])
    assert len(declared) == 1, f"NO-ASSERT-BY-DESIGN 声明变成了 {len(declared)} 条：{sorted(declared)}"
    assert "tests/test_scan.py::test_binary_tracked_file_does_not_crash_scanner" in declared


def test_真实仓库当前为绿_端到端():
    """跑真脚本，不是跑被导入的函数——退出码本身也是契约的一部分。"""
    r = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "check_gates.py")],
        capture_output=True, text=True, cwd=REPO, encoding="utf-8", errors="replace",
    )
    assert r.returncode == 0, f"门禁的门禁当前是红的：\n{r.stdout}\n{r.stderr}"


def test_非门禁脚本被显式声明():
    """`scripts/` 下每个 `.py` 要么是已登记门禁，要么被显式声明为非门禁。

    否则新增一个门禁脚本却忘了登记，R2 会静默放过它——
    「从现状派生的覆盖检查查不出被遗漏的那一类」（notes-part3 C-A16）。
    """
    on_disk = {p.name for p in (REPO / "scripts").glob("*.py")}
    registered = {g.entry.split("/")[-1] for g in cg.GATES if g.entry.endswith(".py")}
    accounted = registered | set(cg.NOT_GATES)
    missing = on_disk - accounted
    assert not missing, f"这些脚本既没登记为门禁也没声明为非门禁：{sorted(missing)}"
