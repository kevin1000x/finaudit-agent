"""门禁的门禁：证明我们的检查**真的能失败**。（落地待办 L-4 / L-5）

## 为什么有这个脚本

两条外部实证，形状完全一致，都指向「检查存在 ≠ 检查有效」：

| 出处 | 逐字 | 形态 |
|---|---|---|
| `references/deepseek-harness-docs-part2.md`（`invariants.md:59`） | 门禁**机械拒绝**「非空但省略/忽略 reporter 的检查」 | 检查函数有函数体，却没有任何路径能报出问题 |
| 同上（`testing.md:34`） | `A guard only guards if the regression actually fails it` | 断言存在，但没人验证过它会红 |

以及一条反面样本：hello-agents 的 6 个 `test_*.py` 共 370 行，
`assert` / `pytest` / `unittest` **全部为 0**，`print` 60 个
（`references/hello-agents-ch07-framework.md` X-12）。
**文件名叫 `test_`、正文承诺「完整测试文件」，底下是 0 个断言。**

本仓自己也有先例：`rules/failure-modes.md` 的 **F-2**（给 flag 编造求不出值的 trigger）
与 **F-8**（跑了门禁但没让它挡住后面的动作），同属「规则写出来了不等于它会触发」。
F-2 此前**只有识别方法，没有执行机制**——本脚本是它的执行机制。

## 三条规则

**R1 —— 每个 `test_*` 必须能失败。**
测试函数体里必须至少有一处可失败点：`assert` / `pytest.raises` / `pytest.fail` /
`pytest.warns` / `self.assert*`。一个不能失败的程序不是测试。

**R2 —— 每道门禁必须**具名**声明它的负控制用例，且该函数存在、且满足 R1。**
声明写在下面的 `GATES` 注册表里，**按声明识别，不按形状猜**——
两道门禁一个用 `subprocess` 跑真脚本、一个直接调 `check_file()`，
形状启发式在这里必然二选一失手（这条判据本身出自 `notes-part3` 的 C-A9）。

**R3 —— 恒真断言不算断言。**
`assert True` / `assert 1` / `assert "x"` / `assert x == x` 这类**构造上不可能红**的断言
不计入 R1 的可失败点。`invariants.md:5` 逐字禁止「断言 service/method 存在」这类恒真物。

**R1 的唯一合法例外：断言就是「不抛异常」。**
这类测试确实没有可写的断言（例：非 UTF-8 文件不能让扫描器崩）。
**给它编一个断言就是 F-2 本身**——拿手边能求值的东西凑一个。
harness 对这种情况给了正解（`invariants.md:5`）：**必须写显式的、该模块特有的、
固定前缀开头的理由，模板化措辞由脚本拒绝。** 照办：

写法（此处用单引号示意，实际写在测试的 docstring 里）：

    def test_xxx():
        'NO-ASSERT-BY-DESIGN: 断言是不抛异常——抛了就等于扫描器不可用。'

**反模板的机制是「理由必须全仓唯一」**：复制粘贴必然产生重复，重复即报红。
这比长度阈值硬——凑字数容易，凑出一个不重复且说得通的理由要真想一遍。
声明数量会被打印出来并有测试锁住，**它长起来就等于 R1 在退化**。

## 明确抓不到什么（不许把「本门禁通过」读成「我们的门禁都有效」）

- **它证明不了负控制会抓住一个真实回归。** R2 只保证「有一个具名的、含真断言的负控制」，
  保证不了「把守卫删掉它就会红」。**那件事没有已知的机械判据**——
  harness 给的也是一条**人执行的程序**（造回归 → 看红 → 回退），
  已写进 `rules/commands.md`，**本脚本不能替代它**。
- **抓不到「断言了，但断言的不是它声称证明的事」。** 这正是本项目从三个外部项目
  收集到的那条模式，`references/` 里有四个实例。断言内容的正确性无法机械判定。
- **抓不到间接断言。** 若测试把断言封进一个 helper（`_expect_red(...)`），
  R1 会误报。目前仓库里没有这种写法；出现时应显式登记进 `INDIRECT_ASSERT_HELPERS`，
  **而不是放宽 R1**——放宽会让 R1 退化。
- **不检查门禁本身是不是绿的。** 那是那五道门自己的事，本脚本只看「它们会不会红」。

## 豁免

`EXEMPT_TESTS` **保持为空**。往里加东西 = 承认存在一个不能失败的测试，
必须在此写明为什么可以接受。豁免清单一旦长起来，本门禁就退化成一张
「已知例外」的目录——与它要防的毛病同型（第五道门 `check_reading_ledger.py` 同款约束）。

退出码 0 = 通过；1 = 存在不能失败的测试，或门禁缺具名负控制。
"""

from __future__ import annotations

import ast
import pathlib
import sys
from dataclasses import dataclass

REPO = pathlib.Path(__file__).resolve().parent.parent
TESTS_DIR = REPO / "tests"


@dataclass(frozen=True)
class Gate:
    """一道门禁，及它**具名声明**的负控制用例。

    `entry` 只用于报错时告诉人这道门怎么跑，不参与校验。
    """

    entry: str
    test_module: str
    negative_control: str


# 显式注册表。新增门禁必须在此登记，否则它没有负控制也不会被发现。
GATES: tuple[Gate, ...] = (
    Gate(
        entry="python scripts/check_xrefs.py",
        test_module="test_xrefs.py",
        negative_control="test_checker_flags_unknown_id_end_to_end",
    ),
    Gate(
        entry="python scripts/check_reading_ledger.py",
        test_module="test_reading_ledger.py",
        negative_control="test_大文件声称全文而正文零出现_必须报红",
    ),
    Gate(
        entry="python scripts/verify_deps.py",
        test_module="test_verify_deps_license.py",
        negative_control="test_pymupdf_is_rejected_via_classifier",
    ),
    Gate(
        entry="python -m semantic_layer scan",
        test_module="test_scan.py",
        negative_control="test_contact_pattern_detected",
    ),
    Gate(
        entry="python -m semantic_layer validate",
        test_module="test_conformance.py",
        negative_control="test_removing_grain_triggers_r1",
    ),
    Gate(
        entry="python scripts/check_gates.py",
        test_module="test_gates.py",
        negative_control="test_无断言的测试必须报红",
    ),
)

# `scripts/` 下**不是门禁**的东西，写在这里以示这不是漏登记。
NOT_GATES: dict[str, str] = {
    "backlog_status.py": "统计工具，不产生通过/不通过判定，其 docstring 已写明",
}

# 把断言封进 helper 的测试。**保持为空**，见 docstring「抓不到什么」。
INDIRECT_ASSERT_HELPERS: frozenset[str] = frozenset()

# 允许不能失败的测试。**保持为空**——这一条是无理由豁免，与 R1 的例外不同：
# R1 的例外要求在测试自己的 docstring 里写明理由且理由全仓唯一，此处则不要求任何理由。
EXEMPT_TESTS: frozenset[str] = frozenset()

# R1 的合法例外前缀。见 docstring。
NO_ASSERT_PREFIX = "NO-ASSERT-BY-DESIGN:"

_PYTEST_FAILERS = {"raises", "fail", "warns", "deprecated_call", "xfail"}


def _is_tautological(node: ast.Assert) -> bool:
    """恒真断言：构造上不可能红。"""
    test = node.test
    if isinstance(test, ast.Constant):
        return bool(test.value)
    if isinstance(test, (ast.List, ast.Tuple, ast.Dict, ast.Set)) and _nonempty_literal(test):
        return True
    if isinstance(test, ast.Compare) and len(test.ops) == 1:
        if isinstance(test.ops[0], (ast.Eq, ast.Is)):
            try:
                return ast.dump(test.left) == ast.dump(test.comparators[0])
            except Exception:  # pragma: no cover - ast.dump 不应失败
                return False
    return False


def _nonempty_literal(node: ast.expr) -> bool:
    for field in ("elts", "keys"):
        vals = getattr(node, field, None)
        if vals is not None:
            return len(vals) > 0
    return False


def _failure_points(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """数这个函数体里有几处**可能失败**的地方。"""
    count = 0
    for node in ast.walk(fn):
        if isinstance(node, ast.Assert):
            if not _is_tautological(node):
                count += 1
        elif isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Attribute):
                if f.attr in _PYTEST_FAILERS and _root_name(f) == "pytest":
                    count += 1
                elif f.attr.startswith("assert") and _root_name(f) == "self":
                    count += 1
                elif f.attr in INDIRECT_ASSERT_HELPERS:
                    count += 1
            elif isinstance(f, ast.Name) and f.id in INDIRECT_ASSERT_HELPERS:
                count += 1
    return count


def _root_name(attr: ast.Attribute) -> str | None:
    node: ast.expr = attr
    while isinstance(node, ast.Attribute):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


def _parse(path: pathlib.Path) -> ast.Module | None:
    """解析测试模块；语法错返回 None 而不是抛出。

    2026-08-24 实跑 L-5 的「造回归 → 看红 → 回退」时发现：造回归的脚本
    把受害文件切成了语法错误，本门禁于是**以 traceback 崩掉**而不是报告问题。
    门禁红了，但红的原因不是它声称在查的那件事——正是本项目从三个外部项目
    收集到的那条失效模式，这次出现在自己身上。
    """
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return None


def _test_functions(tree: ast.Module) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    """收集顶层与类内的 `test_*`，**不含嵌套在测试内部的辅助函数**。"""
    out: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test_"):
                out[node.name] = node
        elif isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and sub.name.startswith("test_"):
                    out[f"{node.name}::{sub.name}"] = sub
    return out


def _no_assert_reason(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    """取出 `NO-ASSERT-BY-DESIGN:` 声明的理由；没声明返回 None。"""
    doc = ast.get_docstring(fn)
    if not doc:
        return None
    first = doc.strip().splitlines()[0].strip()
    if not first.startswith(NO_ASSERT_PREFIX):
        return None
    return first[len(NO_ASSERT_PREFIX):].strip()


def check_module(path: pathlib.Path) -> tuple[list[str], dict[str, str]]:
    """R1 + R3。

    返回 `(问题列表, {测试全名: 无断言声明的理由})`。
    理由要拿到**模块之外**去查重——反模板机制是全仓唯一，见 docstring。
    """
    rel = path.relative_to(REPO).as_posix()
    problems: list[str] = []
    declared: dict[str, str] = {}

    tree = _parse(path)
    if tree is None:
        # 语法错的测试模块 pytest 收集不到 ⇒ 它的断言一条都不会跑。
        # **崩掉的门禁不是门禁**：这里必须报出来，而不是让 SyntaxError 冒到顶层。
        return [f"{rel}  语法错误，pytest 收集不到 —— 它的断言一条都不会执行"], {}

    for name, fn in _test_functions(tree).items():
        if f"{path.name}::{name}" in EXEMPT_TESTS:
            continue
        if _failure_points(fn) > 0:
            continue

        reason = _no_assert_reason(fn)
        if reason is None:
            problems.append(
                f"{rel}:{fn.lineno}  `{name}` 没有任何可失败点 —— "
                f"一个不能失败的程序不是测试。"
                f"若断言确实是「不抛异常」，在 docstring 首行写 "
                f"`{NO_ASSERT_PREFIX} <该测试特有的理由>`"
            )
        elif len(reason) < 12:
            problems.append(
                f"{rel}:{fn.lineno}  `{name}` 的 {NO_ASSERT_PREFIX} 理由过短"
                f"（{len(reason)} 字符）—— 理由要说清为什么没有可断言的东西"
            )
        else:
            declared[f"{rel}::{name}"] = reason

    return problems, declared


def check_gates_have_negative_controls() -> list[str]:
    """R2：每道门禁的具名负控制必须存在，且它自己满足 R1。"""
    problems = []
    for gate in GATES:
        path = TESTS_DIR / gate.test_module
        if not path.exists():
            problems.append(
                f"门禁 `{gate.entry}` 声明的测试模块 tests/{gate.test_module} 不存在"
            )
            continue
        tree = _parse(path)
        if tree is None:
            problems.append(
                f"门禁 `{gate.entry}` 的测试模块 tests/{gate.test_module} 语法错误 —— "
                f"它的负控制根本不会被执行"
            )
            continue
        fns = _test_functions(tree)
        fn = fns.get(gate.negative_control)
        if fn is None:
            problems.append(
                f"门禁 `{gate.entry}` 声明的负控制 "
                f"tests/{gate.test_module}::{gate.negative_control} 不存在 —— "
                f"注册表与测试已脱节"
            )
        elif _failure_points(fn) == 0:
            problems.append(
                f"门禁 `{gate.entry}` 的负控制 `{gate.negative_control}` 没有可失败点 —— "
                f"它证明不了这道门会红"
            )
    return problems


def check_reasons_are_not_templated(declared: dict[str, str]) -> list[str]:
    """反模板：`NO-ASSERT-BY-DESIGN:` 的理由必须全仓唯一。

    复制粘贴必然产生重复，重复即报红。这比长度阈值硬——
    凑字数容易，凑一个不重复且说得通的理由要真想一遍。
    """
    seen: dict[str, list[str]] = {}
    for where, reason in declared.items():
        seen.setdefault(reason, []).append(where)

    problems: list[str] = []
    for reason, wheres in sorted(seen.items()):
        if len(wheres) < 2:
            continue
        parts = [f'{NO_ASSERT_PREFIX} 的理由重复了 —— 模板化措辞不算理由：']
        parts.extend(f'        {w}' for w in sorted(wheres))
        parts.append(f'        重复的理由：{reason}')
        problems.append(chr(10).join(parts))
    return problems


def main() -> int:
    problems: list[str] = []
    declared: dict[str, str] = {}
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        module_problems, module_declared = check_module(path)
        problems.extend(module_problems)
        declared.update(module_declared)
    problems.extend(check_reasons_are_not_templated(declared))
    problems.extend(check_gates_have_negative_controls())

    scanned = sorted(p.name for p in TESTS_DIR.glob("test_*.py"))
    print(f"扫描 {len(scanned)} 个测试模块，{len(GATES)} 道已登记门禁。")
    print(f"已登记豁免 {len(EXEMPT_TESTS)} 条，间接断言 helper {len(INDIRECT_ASSERT_HELPERS)} 条（均应为 0）。")
    print(f"`{NO_ASSERT_PREFIX}` 声明 {len(declared)} 条 —— **它长起来就等于 R1 在退化**。")
    if NOT_GATES:
        print(f"显式声明为「非门禁」的脚本 {len(NOT_GATES)} 个：{', '.join(NOT_GATES)}")

    if problems:
        print("\n门禁的门禁：不通过")
        for p in problems:
            print(f"  [FAIL] {p}")
        return 1

    print("\n门禁的门禁：通过")
    print("  注意：本门禁证明不了负控制会抓住真实回归——那需要 `rules/commands.md`")
    print("        里那条人执行的程序（造回归 → 看红 → 回退）。见 docstring「抓不到什么」。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
