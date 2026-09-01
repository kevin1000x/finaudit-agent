"""`scripts/check_gates.py` 的回归测试（落地待办 L-4 / L-5）。

这道门禁的对象是**我们自己的门禁与测试**，所以它自己最容易变成
它要防的那个东西：一个不会红的检查。

因此每条规则都配一条负向用例：**把缺陷造出来，看它变红**
（`references/deepseek-harness-docs-part2.md` 记的 `testing.md:34` 逐字
`A guard only guards if the regression actually fails it`）。
"""

from __future__ import annotations

import importlib.util
import os
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
def scratch(tmp_path, monkeypatch):
    """样本写进 tmp_path，**不落进真实的 `tests/`**。

    初版把样本写在 `REPO/tests/test___gate_scratch__.py`，靠 teardown 删。
    2026-08-24 独立复核指出风险：进程被 Ctrl-C 或 OOM 杀掉时会残留一个
    「无断言测试」文件，第六道门此后永久变红，且红的原因与真实代码无关
    ——**一道会因为自己的测试残渣而红的门禁，人会去改门禁而不是改代码**。

    `check_module` 只要求路径在 `REPO` 之下（它调 `relative_to(REPO)` 生成报错信息），
    并不要求在 `tests/` 之下，所以把 `cg.REPO` 指向 tmp_path 即可。
    """
    monkeypatch.setattr(cg, "REPO", tmp_path)
    monkeypatch.setattr(cg, "TESTS_DIR", tmp_path / "tests")
    (tmp_path / "tests").mkdir()
    return tmp_path / "tests" / "test_sample.py"


def _src(*lines: str) -> str:
    """按行拼测试源码。

    不用嵌了换行转义的单个字符串字面量：那样写出来的 `<换行>@pytest.mark.skip`
    会被 AC-10 扫描判成邮箱形态（局部名 + 点分域名），产生真误报。
    2026-08-24 实际撞上一次。**没有去放宽扫描规则**——为迁就自己的测试
    放宽门禁，正是本项目禁止的那件事。
    """
    return "\n".join(lines) + "\n"


def _problems(path: Path) -> list[str]:
    return cg.check_module(path)[0]


def _declared(path: Path) -> dict[str, str]:
    return cg.check_module(path)[1]


# --------------------------------------------------------------------------
# 扫描范围 —— **视野的缺口不会以红的形式表现出来**（N-42 那一族）
# --------------------------------------------------------------------------


def test_门禁的扫描范围与pytest的收集范围一致():
    """🔴 **2026-09-02 实测出来的视野缺口。**

    原实现只扫 `test_*.py`，而 pytest 的默认 `python_files` 是
    `test_*.py` **和** `*_test.py`，`pyproject.toml` 也没有覆盖它。
    ⇒ 一份叫 `foo_test.py` 的测试，**pytest 会跑它，第六道门看不见它**。

    本仓当前 `*_test.py` 有 0 个文件，所以它一直表现为一切正常 ——
    这正是 `N-42` 的形状：**门禁看不见的东西，在证据里与「不存在」不可区分**。

    ⚠️ 这条红了**不要去改 `PYTEST_FILE_PATTERNS` 让它变绿** ——
    先看是不是有人在 `pyproject.toml` 里写了 `python_files`。
    两个声明必须对上，**改哪一个是另一回事**。
    """
    import tomllib

    cfg = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    ini = cfg.get("tool", {}).get("pytest", {}).get("ini_options", {})
    # 没有覆盖 ⇒ 实际生效的就是 pytest 的默认两条。
    declared = ini.get("python_files")
    expected = tuple(declared) if declared else ("test_*.py", "*_test.py")
    assert tuple(cg.PYTEST_FILE_PATTERNS) == expected, (
        f"check_gates 扫 {cg.PYTEST_FILE_PATTERNS}，而 pytest 收 {expected} —— "
        "两者一旦不同，差集里的测试会被跑、但不被 R1 检查"
    )


def test_下划线test结尾的模块也在扫描范围里(tmp_path, monkeypatch):
    """负控制：把无断言的测试放进 `*_test.py`，**必须照样被抓住**。

    这一条与上一条是两件事：上一条锁「两个声明对得上」，
    这一条锁「扫描真的按两条 pattern 走」——
    只改常量不改 `rglob` 的话，上一条仍然绿。
    """
    monkeypatch.setattr(cg, "REPO", tmp_path)
    monkeypatch.setattr(cg, "TESTS_DIR", tmp_path / "tests")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "zz_probe_test.py").write_text(
        _src("def test_一个断言都没有():", "    x = 1 + 1"), encoding="utf-8"
    )

    modules = cg.iter_test_modules()
    assert [m.name for m in modules] == ["zz_probe_test.py"]
    assert len(cg.check_module(modules[0])[0]) == 1


def test_两条pattern匹配到同一个文件时不重复扫(tmp_path, monkeypatch):
    """`test_a_test.py` 同时满足 `test_*.py` 与 `*_test.py`。"""
    monkeypatch.setattr(cg, "REPO", tmp_path)
    monkeypatch.setattr(cg, "TESTS_DIR", tmp_path / "tests")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a_test.py").write_text(
        _src("def test_x():", "    assert True"), encoding="utf-8"
    )
    assert len(cg.iter_test_modules()) == 1

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
    # 断言的是**哪一条问题**，不是问题的**个数**。
    # 2026-08-31 加 R6 之后同一行会同时触发两条（R3 让它不计入可失败点
    # ⇒ R1 报「没有任何可失败点」；R6 报「这条断言语法上恒为真」），
    # 原来那句 `len(problems) == 1` 会因此变红 —— **红得没有道理**：
    # 本条考的是 R3，与新增的 R6 无关。按数量断言从一开始就比按内容断言脆。
    assert any("没有任何可失败点" in x for x in problems), (
        f"`assert {expr}` 应被判为恒真"
    )


def test_自比较断言不算断言(scratch):
    """`assert x == x` 恒真，且是重构残留的常见形态。"""
    scratch.write_text("def test_x():\n    y = compute()\n    assert y == y\n", encoding="utf-8")
    # 按内容断言，不按个数 —— 理由同上（R6 于 2026-08-31 新增）。
    assert any("没有任何可失败点" in x for x in _problems(scratch))


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
        # 同 `tests/test_xrefs.py` 的 `_UTF8_ENV`：不强制的话子进程按系统代码页写 stdout，
        # 断言中文串会匹配不到。这里当前只断言 returncode，但断言一旦加中文就会踩到。
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
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


# --------------------------------------------------------------------------
# 2026-08-24 独立复核抓出的盲区。**每一条此前都是「放行」。**
#
# 这一组不是补测试覆盖率，是把六类「构造上不会红但被判为有可失败点」的形态
# 钉死。它们全部由复核者与本会话各自独立实跑复现过，不是假想风险。
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name, src",
    [
        (
            "pytest.xfail 是命令式标记，永不变红",
            "import pytest\n\n\ndef test_x():\n    pytest.xfail('never fails')\n",
        ),
        (
            "@pytest.mark.skip 的测试根本不跑",
            _src("import pytest", "", "", "@pytest.mark.skip(reason='x')",
                 "def test_x():", "    assert 1 == 2"),
        ),
        (
            "@pytest.mark.skipif 同理，条件真假判不出来按 fail-closed 处理",
            _src("import pytest", "", "", "@pytest.mark.skipif(True, reason='x')",
                 "def test_x():", "    assert 1 == 2"),
        ),
        (
            "@pytest.mark.xfail 的测试红了也算通过",
            _src("import pytest", "", "", "@pytest.mark.xfail",
                 "def test_x():", "    assert 1 == 2"),
        ),
        (
            "断言在常量假分支里，语法上不可达",
            "def test_x():\n    if False:\n        assert 1 == 2\n",
        ),
        (
            "断言在 while False 里",
            "def test_x():\n    while False:\n        assert 1 == 2\n",
        ),
        (
            "断言写在 return 之后",
            "def test_x():\n    return\n    assert 1 == 2\n",
        ),
        (
            "断言写在 raise 之后",
            "def test_x():\n    raise SystemExit\n    assert 1 == 2\n",
        ),
        (
            "断言在一个从未被调用的嵌套函数里",
            "def test_x():\n    def helper():\n        assert 1 == 2\n",
        ),
    ],
)
def test_构造上不会红的形态必须报红(scratch, name, src):
    scratch.write_text(src, encoding="utf-8")
    assert _problems(scratch), f"这个形态应当被判为无可失败点：{name}"


@pytest.mark.parametrize(
    "name, src",
    [
        ("普通断言", "def test_x():\n    assert 1 + 1 == 2\n"),
        ("断言在 for 体内", "def test_x():\n    for i in [1]:\n        assert i == 1\n"),
        ("断言在 if 真分支", "def test_x():\n    if True:\n        assert 1 == 2\n"),
        (
            "断言在 if False 的 else 分支",
            "def test_x():\n    if False:\n        pass\n    else:\n        assert 1 == 2\n",
        ),
        (
            "断言在 with 体内",
            "def test_x():\n    with open(__file__) as f:\n        assert f\n",
        ),
        (
            "with pytest.raises —— 失败点在 with 的 header 里，不在体内",
            "import pytest\n\n\ndef test_x():\n    with pytest.raises(ValueError):\n        int('x')\n",
        ),
        (
            "with pytest.warns 同理",
            "import pytest\n\n\ndef test_x():\n    with pytest.warns(UserWarning):\n        pass\n",
        ),
        (
            "断言在 try 体内",
            "def test_x():\n    try:\n        assert 1 == 2\n    except AssertionError:\n        raise\n",
        ),
        (
            "unittest 风格的 self.assert*",
            "import unittest\n\n\nclass TestX(unittest.TestCase):\n    def test_x(self):\n        self.assertEqual(1, 2)\n",
        ),
        (
            "断言写在 return 之前是可达的",
            "def test_x():\n    assert 1 == 2\n    return\n",
        ),
    ],
)
def test_可达的失败点必须放行(scratch, name, src):
    """误报的代价是有人去放宽 R1，而 docstring 自己写了「放宽会让 R1 退化」。

    `with pytest.raises` 那条是真踩过的坑：修可达性时把复合语句整个跳过，
    header 里的 `pytest.raises(...)` 就被漏判了。
    """
    scratch.write_text(src, encoding="utf-8")
    assert _problems(scratch) == [], f"这个形态是可达失败点，不该报红：{name}"


def test_有副作用的自比较不算恒真(scratch):
    """`next(it) == next(it)` 结构相同但求值不同，它会真的红。

    R3 只在两侧都无副作用时才判自比较——宁可漏判恒真，也不误报。
    """
    scratch.write_text(
        "def test_x():\n    it = iter([1, 2])\n    assert next(it) == next(it)\n",
        encoding="utf-8",
    )
    assert _problems(scratch) == []


def test_无副作用的自比较仍算恒真(scratch):
    scratch.write_text("def test_x():\n    y = 1\n    assert y == y\n", encoding="utf-8")
    # 按内容断言，不按个数 —— 理由同上（R6 于 2026-08-31 新增）。
    assert any("没有任何可失败点" in x for x in _problems(scratch))


def test_xfail_不在可失败点白名单里():
    """锁住这个集合本身：把 `xfail` 加回去，上面那条负向用例才会红，

    但那时已经晚了——直接断言集合内容，改动它必须是有意识的。
    """
    assert "xfail" not in cg._PYTEST_FAILERS
    assert cg._PYTEST_FAILERS == {"raises", "fail", "warns", "deprecated_call"}


# --------------------------------------------------------------------------
# R4 —— 已登记门禁必须真的接进 CI
#
# 2026-08-23 落地第五道门时漏了整整一天没进 CI，而步骤名、echo、实际命令
# 三者不一致这件事没有任何检查会发现。这一组把那个回归钉死。
# --------------------------------------------------------------------------


def test_真实仓库的门禁都接进了CI():
    assert cg.check_gates_are_wired_into_ci() == []


def test_门禁没进CI必须报红(monkeypatch):
    """负向：注册了一道 CI 里根本没有的门禁。"""
    fake = cg.Gate(
        entry="python scripts/check_从未接进CI.py",
        test_module="test_gates.py",
        negative_control="test_无断言的测试必须报红",
    )
    monkeypatch.setattr(cg, "GATES", (fake,))
    problems = cg.check_gates_are_wired_into_ci()
    assert len(problems) == 1
    assert "没有出现在" in problems[0]
    assert "两处门禁定义已分叉" in problems[0]


def test_CI文件缺失时不得静默通过(monkeypatch, tmp_path):
    """一道查不了的门禁必须报红，不能因为查不了就当通过——那是 fail-open。"""
    monkeypatch.setattr(cg, "REPO", tmp_path)
    problems = cg.check_gates_are_wired_into_ci()
    assert len(problems) == 1
    assert "无法执行，不得静默通过" in problems[0]


def test_注释里的门禁名骗不过R4():
    """`gates.yml` 的注释里就写着 `check_reading_ledger.py`。

    不剥注释就会被自己的注释骗过——命令删掉了，子串还在，R4 静默通过。
    2026-08-24 跑 R4 自己的负控制时当场撞上。
    """
    yaml_with_only_a_comment = "jobs:\n  gates:\n    steps:\n      # python scripts/check_x.py\n      - run: echo hi\n"
    stripped = cg._strip_yaml_comments(yaml_with_only_a_comment)
    assert "check_x.py" not in stripped
    assert "echo hi" in stripped


def test_剥注释不误伤真实命令():
    """行尾注释要剥掉，命令本身要留下。"""
    stripped = cg._strip_yaml_comments("      - run: python scripts/check_x.py  # 说明\n")
    assert "python scripts/check_x.py" in stripped
    assert "说明" not in stripped


# --------------------------------------------------------------------------
# R5 —— 已落地的条目必须在 references/ 里留下可追溯的回标
#
# 台账 N-35 当初判定「『已含』无法机械判定」，留了「宁可不做，靠清单纪律」。
# 那个判断在 2026-08-24 被推翻两次：规则刚写下，同一天落地的五条一条没回标。
# 前提也不成立了——回标时把 L-nn 写进 references，比对就退化成一次 grep。
# --------------------------------------------------------------------------


def test_真实仓库的已落地条目都回标了():
    assert cg.check_landed_items_are_back_annotated() == []


def test_落地但未回标必须报红(monkeypatch, tmp_path):
    """负向：这是 R5 唯一要防的东西，且它实际发生过（五条落地零条回标）。"""
    (tmp_path / "docs" / "agent").mkdir(parents=True)
    (tmp_path / "references").mkdir()
    (tmp_path / "docs" / "agent" / "LANDING-BACKLOG.md").write_text(
        "| # | 内容 | 来源 | 目的地 | 状态 |\n"
        "| L-9 | 某条 | X | Y | ~~OPEN~~ → **已落地 2026-08-24** |\n"
        "| L-10 | 另一条 | X | Y | OPEN |\n",
        encoding="utf-8",
    )
    (tmp_path / "references" / "a.md").write_text("正文里没有提到任何编号。\n", encoding="utf-8")
    monkeypatch.setattr(cg, "REPO", tmp_path)

    problems = cg.check_landed_items_are_back_annotated()
    assert len(problems) == 1
    assert "L-9" in problems[0]
    assert "L-10" not in problems[0], "仍是 OPEN 的条目不该被要求回标"


def test_回标了就通过(monkeypatch, tmp_path):
    (tmp_path / "docs" / "agent").mkdir(parents=True)
    (tmp_path / "references").mkdir()
    (tmp_path / "docs" / "agent" / "LANDING-BACKLOG.md").write_text(
        "| L-9 | 某条 | X | Y | **已落地 2026-08-24** |\n", encoding="utf-8"
    )
    (tmp_path / "references" / "a.md").write_text(
        "~~未落地~~ → 已落地（登记册 `L-9`）。\n", encoding="utf-8"
    )
    monkeypatch.setattr(cg, "REPO", tmp_path)
    assert cg.check_landed_items_are_back_annotated() == []


def test_编号比对不被粘连误伤(monkeypatch, tmp_path):
    """`L-9` 不得被 `L-90` 满足——与 check_xrefs 同款的粘连问题。"""
    (tmp_path / "docs" / "agent").mkdir(parents=True)
    (tmp_path / "references").mkdir()
    (tmp_path / "docs" / "agent" / "LANDING-BACKLOG.md").write_text(
        "| L-9 | 某条 | X | Y | **已落地** |\n", encoding="utf-8"
    )
    (tmp_path / "references" / "a.md").write_text("回标了 `L-90`。\n", encoding="utf-8")
    monkeypatch.setattr(cg, "REPO", tmp_path)
    problems = cg.check_landed_items_are_back_annotated()
    assert len(problems) == 1, "L-90 不该满足 L-9"


def test_R5的输入缺失时不得静默通过(monkeypatch, tmp_path):
    monkeypatch.setattr(cg, "REPO", tmp_path)
    problems = cg.check_landed_items_are_back_annotated()
    assert len(problems) == 1
    assert "不得静默通过" in problems[0]


# --------------------------------------------------------------------------
# R6：恒真断言**逐条**报（台账 N-40 判据 2，2026-08-31）
# --------------------------------------------------------------------------


def test_R6_抓住_N40_的原始实例(scratch):
    """`N-40` 的实例是真的，不是假想：`assert pat.search(...) or True`。

    它与两条真断言并排站着，所以 R1 判「这个函数能红」—— **判定本身没错**。
    错的是粒度：那一行看起来在检查、实际什么都不检查，而它长得和真的一模一样。
    它在仓库里活了若干轮，本门禁每轮都放行。
    """
    scratch.write_text(
        "import re\n"
        "def test_看起来在查大小写不敏感():\n"
        "    pat = re.compile('agpl', re.I)\n"
        "    assert pat.search('AGPL-3.0') or True\n"
        "    assert pat.pattern\n",
        encoding="utf-8",
    )
    problems = _problems(scratch)
    assert any("语法上恒为真" in p for p in problems), problems
    # **关键**：这个函数里另有一条真断言，R1 因此不会报它 ——
    # 若 R6 不存在，这段代码整体是「通过」的。
    assert not any("没有任何可失败点" in p for p in problems)


@pytest.mark.parametrize(
    "body",
    [
        "    assert True\n",
        "    assert 1\n",
        "    assert 'non-empty'\n",
        "    assert (1, 2)\n",
        "    assert x == x\n",
        "    assert x or True\n",
        "    assert x or 1\n",
        "    assert True and 1\n",
        "    assert x or (y and True) or True\n",
    ],
)
def test_R6_逐条形态都报(scratch, body):
    """语法上恒真的几种写法。`or` 任一支恒真即恒真，`and` 要全部恒真。"""
    scratch.write_text(f"def test_x():\n    x = 1\n    y = 2\n{body}", encoding="utf-8")
    assert any("语法上恒为真" in p for p in _problems(scratch))


@pytest.mark.parametrize(
    "body",
    [
        "    assert x\n",
        "    assert x or y\n",              # 两支都是名字 —— 语法上判不出
        "    assert x and True\n",          # `and` 少一支恒真就不是恒真
        "    assert len([x]) >= 0\n",       # 语义上恒真，**语法上不是** —— 明确不抓
        "    assert x == y\n",
        "    assert ()\n",                  # 恒**假**，是另一类问题，不归 R6
        "    assert []\n",
    ],
)
def test_R6_不误报(scratch, body):
    """**宁可漏判，不许误报。**

    误报的代价不是「多修一处」——是有人去放宽这道门，而放宽会让它退化。
    `assert len(xs) >= 0` 这一条尤其要留着：它语义上恒真，
    但 R6 抓的是「**写法上**就不可能假」，不是「这条断言有没有意义」。
    后者没有机械判据（见 `_tautological_asserts` 的「明确抓不到什么」）。
    """
    scratch.write_text(f"def test_x():\n    x = 1\n    y = 2\n{body}", encoding="utf-8")
    assert not any("语法上恒为真" in p for p in _problems(scratch))


def test_R6_扫的是整个模块不只是test函数(scratch):
    """恒真断言写在 helper 里同样什么都不检查，而 helper 正是它最容易藏的地方。"""
    scratch.write_text(
        "def _helper(v):\n"
        "    assert v or True\n"
        "    return v\n"
        "def test_x():\n"
        "    assert _helper(1) == 1\n",
        encoding="utf-8",
    )
    problems = _problems(scratch)
    assert any("语法上恒为真" in p for p in problems), problems


def test_R6_在全仓上当前零命中():
    """基线。**没有这一条，上面那些「会报」证明不了 R6 没在到处误报。**

    ⚠️ 这条断言的是**现状**，不是不变量：将来真写出一条恒真断言时它应该红，
    而红的处置是**改那条断言**，不是把这条测试删掉或加豁免。
    """
    hits = []
    for module in sorted((REPO / "tests").glob("test_*.py")):
        hits += [p for p in _problems(module) if "语法上恒为真" in p]
    assert hits == [], hits
