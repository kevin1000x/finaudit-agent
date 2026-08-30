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

**R4 —— 已登记的门禁必须真的出现在 CI 工作流里。**
`GATES` 里每条 `entry` 的命令必须能在 `.github/workflows/gates.yml` 里找到。
2026-08-23 落地第五道门时**漏了整整一天没进 CI**，而工作流步骤名已经改成「五道门」、
`echo` 仍写「四道门」、实际跑四条——**三者不一致，没有任何检查会发现**。
注册表里本来就有命令行字面量，这一条把那个回归钉死。

**R5 —— 已落地的条目必须在 `references/` 里留下可追溯的回标。**
`LANDING-BACKLOG` §5 中状态为「已落地 / 部分落地 / 已关闭」的每个 `L-nn`，
它的编号必须在 `references/` 里至少出现一次。

台账 N-35 当初判定「难点是『已含』无法机械判定——不像交叉引用那样有编号可比对」，
于是留了「宁可不做，改为靠清单纪律」。**那个判断在 2026-08-24 被推翻了两次**：
同一天里，规则刚写下（「落地后必须同时回标」），T-2 / T-3 落地的五条一条都没回标。
**靠人记得，在写下规则的当天就失败了。**

而「无法机械判定」这个前提本身也不成立了：回标时把 `L-nn` 写进 `references/` 正文，
比对就退化成一次 grep——**和交叉引用是同一个形状**。
这不检查回标内容对不对，只检查**有没有回标**；见「明确抓不到什么」。

**R6 —— 恒真断言本身就是问题，逐条查。**（2026-08-31 新增，台账 `N-40` 判据 2）
R3 只是让恒真断言**不计入** R1 的可失败点，管的是「这个函数整体能不能红」。
R6 管的是**每一条断言**：一条 `assert x or True` 与两条真断言并排站着时，
R1 判「能红」是对的，而那一行**看起来在检查、实际什么都不检查**。
`N-40` 的实例在仓库里活了若干轮，本脚本每轮都放行。
⚠️ **只查语法上恒真，不查运行时恒真** —— 后者需要求值，
那条路通向一个自己会出错的检查器。宁可漏判，不许误报。

**R3 —— 恒真断言不算断言。**
`assert True` / `assert 1` / `assert "x"` / `assert x == x` 这类**构造上不可能红**的断言
不计入 R1 的可失败点。`invariants.md:5` 逐字禁止「断言 service/method 存在」这类恒真物。

**R1 的唯一合法例外：断言就是「不抛异常」。**
这类测试确实没有可写的断言（例：非 UTF-8 文件不能让扫描器崩）。
**给它编一个断言就是 F-2 本身**——拿手边能求值的东西凑一个。
harness 对这种情况给了正解（**`invariants.md:59`**，逐字见
`references/deepseek-harness-docs-part2.md`）：必须写显式的、该模块特有的、
**固定前缀开头**的理由（对方用的是 `No runtime invariant:`），
**模板化措辞由脚本拒绝**。照办：
（初版此处误写 `invariants.md:5`——那一条管的是**断言对象白名单**
「never service or method presence」，即本脚本的 R3，不含前缀与反模板。
2026-08-24 独立复核抓出；`rules/failure-modes.md` 那处分对了。）

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
- **R2 只保证「有一条具名负控制」，不保证它覆盖这道门的全部判据。**（2026-08-31 实测，台账 `N-45`）
  实例是真的：`verify_deps.py` 的 `DENIED_LICENSE_PATTERNS` 有**两条**模式
  （`AGPL` 与 `affero`），而登记的负控制 `test_pymupdf_is_rejected_via_classifier`
  用的 classifier 是「GNU **Affero** General Public License v3」——
  **只考得到 `affero` 那条**。把 `AGPL` 打掉，登记的负控制**照样绿**
  （覆盖它的是另外两条**没有登记**的测试）。
  ⇒ 「R2 通过」读作「这道门有一条被证明会红的用例」是对的，
  读作「这道门每条判据都有负控制」是**错的**。与 `N-40` 是同一族的粒度问题，
  只是发生在 R2 上而不是 R1 上。
- **不检查门禁本身是不是绿的。** 那是各道门自己的事，本脚本只看「它们会不会红」。
- **可达性只判到常量条件为止。** 2026-08-24 的独立复核抓出六类「构造上不会红却被放行」
  的形态，已全部修掉并有回归测试锁住（`pytest.xfail` 调用、`@pytest.mark.skip/skipif/xfail`、
  常量假分支、`return`/`raise` 之后、未被调用的嵌套函数）。**但下面这些仍然抓不到**：
  - 条件是运行时可求值的假（`if 1 > 2:` / `if os.environ.get("NEVER"):`）
  - 断言被 `try` 包住又被裸 `except` 吞掉
  - 通过 `conftest.py` 的 `pytest_collection_modifyitems` 之类在收集期被跳过的测试
  - 断言写对了但断言的对象不对（同上一条，无法机械判定）
- **R4 只查字面量出现，不查它在 CI 里是否真的会被执行。** 命令若被写进一个
  永远不满足 `if:` 条件的 step，或被 `continue-on-error: true` 吞掉退出码，
  R4 照样通过。**它挡的是「忘了加」，不是「加了但没生效」。**
- **R5 只查「有没有回标」，不查「回标写得对不对」。** 在 `references/` 里随手写一句
  `L-9 已落地` 就能骗过它。它挡的是**遗漏**——而遗漏正是实际发生过的那件事
  （五条落地，零条回标）；**它挡不住敷衍**。
  也不检查回标位置对不对：`L-nn` 出现在哪份产物、哪一节，R5 一律不管。

## 豁免

`EXEMPT_TESTS` **保持为空**。往里加东西 = 承认存在一个不能失败的测试，
必须在此写明为什么可以接受。豁免清单一旦长起来，本门禁就退化成一张
「已知例外」的目录——与它要防的毛病同型（第五道门 `check_reading_ledger.py` 同款约束）。

退出码 0 = 通过；1 = 存在不能失败的测试，或门禁缺具名负控制。
"""

from __future__ import annotations

import ast
import pathlib
import re
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
    "probe_fields.py": (
        "探测工具，只 dump 版面原文供人判定，不产生通过/不通过判定；"
        "它一旦开始替人判「这一行是不是那个字段」，SC-8 就在探测阶段先失守。其 docstring 已写明"
    ),
    "evidence_matrix.py": (
        "生成器（`ARCHITECTURE` §8.5.3 / 登记册 `L-6`）。⚠️ **措辞要准**：它**会**在发现断线时"
        "退非零 —— 那是给人直接跑时用的，**不是**把它当成提交链上的第八环。"
        "链上的判定点是 `tests/test_evidence_matrix.py::test_真仓库上当前零断线`，"
        "而 pytest 已经是链的第一环。**不单独登记的理由**：同一件事登记两遍，"
        "R2/R4/R5 会要求它再配一套具名负控制与 CI 步骤，"
        "而那套东西已经以测试的形式存在了（含两条在受控输入上证明它真会报断线的用例）"
    ),
}

# 把断言封进 helper 的测试。**保持为空**，见 docstring「抓不到什么」。
INDIRECT_ASSERT_HELPERS: frozenset[str] = frozenset()

# 允许不能失败的测试。**保持为空**——这一条是无理由豁免，与 R1 的例外不同：
# R1 的例外要求在测试自己的 docstring 里写明理由且理由全仓唯一，此处则不要求任何理由。
EXEMPT_TESTS: frozenset[str] = frozenset()

# R1 的合法例外前缀。见 docstring。
NO_ASSERT_PREFIX = "NO-ASSERT-BY-DESIGN:"

# R4 的检查对象。改路径要同步 `rules/commands.md` 的 CI 一节。
CI_WORKFLOW = pathlib.Path(".github") / "workflows" / "gates.yml"

# R5 的检查对象。
BACKLOG = pathlib.Path("docs") / "agent" / "LANDING-BACKLOG.md"
REFERENCES_DIR = pathlib.Path("references")

# 登记册里表示「这条已经做掉了」的状态词。R5 只对这些行生效。
_LANDED_STATES = ("已落地", "部分落地", "已关闭")

# 能让测试变红的 pytest 入口。
# **`xfail` 不在此列**：`pytest.xfail(reason)` 是命令式地把本次测试标成 xfailed 并
# 立即中止，它在任何情况下都不会红。初版把它写进来了——一个保证不会失败的调用
# 进了「可失败点」白名单，正是 F-2 的形状出现在为 F-2 而写的脚本里。
# 2026-08-24 独立复核抓出，实跑佐证：`pytest.xfail(...)` 的测试报 `1 xfailed`。
_PYTEST_FAILERS = {"raises", "fail", "warns", "deprecated_call"}

# 让整个测试不被执行的 mark。被它们装饰的测试，函数体里有多少断言都不会跑。
_SKIP_MARKS = {"skip", "skipif", "xfail"}

# 不下降进去的作用域：嵌套函数/类不属于「这个测试的函数体」。
# `_test_functions` 的 docstring 早就这么写了，而初版的 `_failure_points` 用
# `ast.walk` 走进了嵌套函数——两处对「函数体」的定义不一致，于是
# 「断言写在一个从未被调用的内部函数里」被判为有可失败点。
_OPAQUE_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)


def _is_tautological(node: ast.Assert) -> bool:
    """恒真断言：构造上不可能红。"""
    test = node.test
    if isinstance(test, ast.Constant):
        return bool(test.value)
    if isinstance(test, (ast.List, ast.Tuple, ast.Dict, ast.Set)) and _nonempty_literal(test):
        return True
    if isinstance(test, ast.Compare) and len(test.ops) == 1:
        if isinstance(test.ops[0], (ast.Eq, ast.Is)):
            left, right = test.left, test.comparators[0]
            # **只在两侧都无副作用时才判自比较**：`next(it) == next(it)` 结构相同
            # 但求值不同，会真的红。2026-08-24 独立复核指出这个误报风险——
            # 门禁误报的代价是有人去放宽 R1，而放宽会让 R1 退化。
            if _side_effect_free(left) and _side_effect_free(right):
                return ast.dump(left) == ast.dump(right)
    if isinstance(test, ast.BoolOp):
        # 2026-08-31 补（台账 `N-40`）。**这一支是 `N-40` 的原始实例**：
        # `assert pat.search(...) or True` —— `X or True` 恒为真，任何输入都不会红，
        # 而它在仓库里活了若干轮，本脚本每轮都放行。
        #
        # `or`：任一支恒真 ⇒ 整式恒真（短路后另一支根本不求值）。
        # `and`：**全部**恒真才恒真 —— 少一个都可能假。
        parts = [_truthy_expr(v) for v in test.values]
        return any(parts) if isinstance(test.op, ast.Or) else all(parts)
    return False


def _truthy_expr(node: ast.expr) -> bool:
    """这个**表达式**在语法上是否恒为真。

    ⚠️ **只判语法，不判运行时**（`N-40` 判据里逐字写着这条边界）：
    运行时恒真需要求值，而那条路通向一个**自己会出错的检查器** ——
    一个误报的门禁的代价是有人去放宽它，而放宽会让它退化。
    ⇒ 宁可漏判，不许误报。
    """
    if isinstance(node, ast.Constant):
        return bool(node.value)
    if isinstance(node, (ast.List, ast.Tuple, ast.Dict, ast.Set)):
        return _nonempty_literal(node)
    if isinstance(node, ast.BoolOp):
        parts = [_truthy_expr(v) for v in node.values]
        return any(parts) if isinstance(node.op, ast.Or) else all(parts)
    return False


def _side_effect_free(node: ast.expr) -> bool:
    """名字、常量、纯属性链、下标——求值两次结果相同。

    含任何调用/推导/await 即判为有副作用：宁可漏判恒真，也不误报。
    """
    for sub in ast.walk(node):
        if isinstance(sub, (ast.Call, ast.Await, ast.Yield, ast.YieldFrom, ast.NamedExpr)):
            return False
        if isinstance(sub, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            return False
    return True


def _nonempty_literal(node: ast.expr) -> bool:
    for field in ("elts", "keys"):
        vals = getattr(node, field, None)
        if vals is not None:
            return len(vals) > 0
    return False


def _is_skipped(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """被 `@pytest.mark.skip` / `skipif` / `xfail` 装饰 ⇒ 断言一条都不会跑。

    R2 声称「负控制存在且满足 R1」，但一个被 skip 的负控制既不会跑也不会红——
    加一行 `@pytest.mark.skip` 就能让它形同虚设而门禁照样说通过。
    2026-08-24 独立复核在第五道门的负控制上实测复现。

    `skipif` 的条件可能为假（那样测试会跑），但**判不出来**，按 fail-closed
    一律当作不可依赖：负控制不该有条件。
    """
    for dec in fn.decorator_list:
        node = dec.func if isinstance(dec, ast.Call) else dec
        if isinstance(node, ast.Attribute) and node.attr in _SKIP_MARKS:
            if isinstance(node.value, ast.Attribute) and node.value.attr == "mark":
                return True
    return False


def _falsy_constant(node: ast.expr) -> bool:
    """`if False:` / `while 0:` —— 分支体在语法上不可达。"""
    if isinstance(node, ast.Constant):
        return not node.value
    if isinstance(node, (ast.List, ast.Tuple, ast.Dict, ast.Set)):
        return not _nonempty_literal(node)
    return False


def _truthy_constant(node: ast.expr) -> bool:
    if isinstance(node, ast.Constant):
        return bool(node.value)
    if isinstance(node, (ast.List, ast.Tuple, ast.Dict, ast.Set)):
        return _nonempty_literal(node)
    return False


def _count_stmts(body: list[ast.stmt]) -> int:
    """按**可达性**数一段语句里的可失败点。

    三条排除（均由 2026-08-24 的独立复核实测抓出，此前一律放行）：
    - `return` / `raise` / `break` / `continue` 之后的语句
    - 常量假分支的 `if` 体、常量假条件的 `while` 体
    - 嵌套的 `def` / `class` / `lambda` 内部（见 `_OPAQUE_SCOPES`）

    **仍然抓不到**：条件为运行时可求值的假（`if 1 > 2:`）、
    被 `try` 包住又被裸 `except` 吞掉的断言。见模块 docstring 的「明确抓不到什么」。
    """
    count = 0
    for stmt in body:
        count += _count_expr_level(stmt)

        if isinstance(stmt, ast.If):
            if _truthy_constant(stmt.test):
                count += _count_stmts(stmt.body)
            elif _falsy_constant(stmt.test):
                count += _count_stmts(stmt.orelse)
            else:
                count += _count_stmts(stmt.body) + _count_stmts(stmt.orelse)
        elif isinstance(stmt, ast.While):
            if not _falsy_constant(stmt.test):
                count += _count_stmts(stmt.body)
            count += _count_stmts(stmt.orelse)
        elif isinstance(stmt, ast.Try):
            count += _count_stmts(stmt.body)
            for handler in stmt.handlers:
                count += _count_stmts(handler.body)
            count += _count_stmts(stmt.orelse) + _count_stmts(stmt.finalbody)
        elif isinstance(stmt, (ast.For, ast.AsyncFor)):
            count += _count_stmts(stmt.body) + _count_stmts(stmt.orelse)
        elif isinstance(stmt, (ast.With, ast.AsyncWith)):
            count += _count_stmts(stmt.body)
        elif isinstance(stmt, ast.Assert):
            if not _is_tautological(stmt):
                count += 1
        elif isinstance(stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
            break  # 本块后面的语句都不可达

    return count


def _header_exprs(stmt: ast.stmt) -> list[ast.expr]:
    """复合语句自身的表达式（不含它的子语句块）。

    **`with pytest.raises(...)` 的调用就在这里**——初版把复合语句整个跳过，
    于是它被漏判。子语句块由 `_count_stmts` 递归处理，两边不重叠也不重复。
    """
    if isinstance(stmt, (ast.If, ast.While)):
        return [stmt.test]
    if isinstance(stmt, (ast.For, ast.AsyncFor)):
        return [stmt.iter]
    if isinstance(stmt, (ast.With, ast.AsyncWith)):
        return [item.context_expr for item in stmt.items]
    return []


def _count_expr_level(stmt: ast.stmt) -> int:
    """数这条语句**自身表达式**里的失败调用，不下降进子语句块与嵌套作用域。"""
    if isinstance(stmt, _OPAQUE_SCOPES):
        return 0

    if isinstance(stmt, (ast.If, ast.While, ast.Try, ast.For, ast.AsyncFor, ast.With, ast.AsyncWith)):
        roots: list[ast.AST] = list(_header_exprs(stmt))
    else:
        roots = [stmt]

    count = 0
    for root in roots:
        for node in ast.walk(root):
            if isinstance(node, _OPAQUE_SCOPES):
                continue
            if not isinstance(node, ast.Call):
                continue
            if _inside_opaque_scope(root, node):
                continue
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


def _inside_opaque_scope(root: ast.AST, target: ast.AST) -> bool:
    """target 是否被 root 内部的某个嵌套函数/类包着。"""
    for node in ast.walk(root):
        if isinstance(node, _OPAQUE_SCOPES) and node is not root:
            for inner in ast.walk(node):
                if inner is target:
                    return True
    return False


def _failure_points(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """数这个函数体里有几处**可达且可能失败**的地方。"""
    if _is_skipped(fn):
        return 0
    return _count_stmts(fn.body)


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


def _tautological_asserts(tree: ast.AST, rel: str) -> list[str]:
    """R6：**逐条**查断言，不是「这个函数里有没有一条能红的」。

    ## R6 与 R3 的分工（两条都要，缺一不可）

    - **R3** 说的是「恒真断言**不计入** R1 的可失败点」——
      它管的是「这个函数**整体**能不能红」。
    - **R6** 说的是「恒真断言**本身就是问题**」——
      哪怕同一个函数里另有两条真断言、整体照样会红。

    ⇒ `N-40` 记的正是 R3 拦不住的那种：
    `tests/test_verify_deps_license.py` 里 `assert pat.search(...) or True`
    与两条真断言并排站着，R1 判「能红」（对的），
    而**那一行看起来在检查、实际什么都不检查**，长得和真的一模一样。
    它在仓库里活了若干轮，每轮都被放行。

    ## 边界：**只查语法上恒真，不查运行时恒真**

    `N-40` 判据里逐字写着这条边界。运行时恒真需要求值，
    而那条路通向一个**自己会出错的检查器**；一个误报的门禁的代价是
    有人去放宽它，而放宽会让它退化。⇒ **宁可漏判，不许误报。**

    ## 明确抓不到什么

    - `assert x or y`（`y` 是名字而不是字面量）—— 可能恒真，语法上判不出。
    - `assert f()`，其中 `f` 永远返回真 —— 那是运行时的事。
    - `assert len(xs) >= 0` —— 语义上恒真，语法上是一个普通比较。
      **这一条尤其要记住**：R6 抓的是「写法上就不可能假」，
      不是「这条断言有没有意义」。后者没有机械判据。
    """
    problems: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert) and _is_tautological(node):
            problems.append(
                f"{rel}:{node.lineno}  这条断言在**语法上恒为真**，任何输入都不会红 —— "
                "一段看起来在检查、实际什么都不检查的代码（台账 `N-40`）。"
                "要么写成真的断言，要么删掉；**不要加豁免**。"
            )
    return problems


def check_module(path: pathlib.Path) -> tuple[list[str], dict[str, str]]:
    """R1 + R3 + R6。

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

    # R6 扫**整个模块**的每一条断言，不只扫 `test_*` 函数体 ——
    # 一条恒真断言写在 helper 里同样什么都不检查，而 helper 正是它最容易藏的地方。
    problems.extend(_tautological_asserts(tree, rel))

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


def _strip_yaml_comments(text: str) -> str:
    """去掉 `#` 注释行再做字面量检查。

    **不去掉就会被自己的注释骗过**：`gates.yml` 里有一条注释写着
    「`check_reading_ledger.py`（2026-08-23 落地的第五道门）从未进过 CI」，
    命令即使被删掉，这个子串依然在文件里——R4 会静默通过。
    2026-08-24 跑 R4 自己的负控制时当场撞上，正是「检查存在 ≠ 检查有效」。

    只处理整行注释与行尾注释。YAML 的 `#` 在引号内不算注释，
    但门禁命令不会写在引号里，这个近似足够且偏保守（宁可少认字面量）。
    """
    out = []
    for line in text.splitlines():
        idx = line.find("#")
        out.append(line if idx < 0 else line[:idx])
    return "\n".join(out)


def check_gates_are_wired_into_ci() -> list[str]:
    """R4：每道已登记门禁的命令必须出现在 CI 工作流里。

    只做字面量包含检查——**它挡的是「忘了加」，不是「加了但没生效」**，
    见 docstring 的「明确抓不到什么」。
    """
    path = REPO / CI_WORKFLOW
    if not path.exists():
        return [f"CI 工作流 {CI_WORKFLOW.as_posix()} 不存在 —— R4 无法执行，不得静默通过"]

    text = _strip_yaml_comments(path.read_text(encoding="utf-8"))
    problems = []
    for gate in GATES:
        # `entry` 写成 `python xxx`，CI 里也是 `python xxx`；去掉前缀比整串更稳
        needle = gate.entry.removeprefix("python ").strip()
        if needle not in text:
            problems.append(
                f"门禁 `{gate.entry}` 没有出现在 {CI_WORKFLOW.as_posix()} 里 —— "
                f"它在本地跑而在 CI 不跑，两处门禁定义已分叉"
            )
    return problems


def check_landed_items_are_back_annotated() -> list[str]:
    """R5：登记册里已落地的条目，编号必须在 `references/` 里出现过。

    只查存在性——见 docstring 的「明确抓不到什么」。
    """
    backlog = REPO / BACKLOG
    refs_dir = REPO / REFERENCES_DIR
    if not backlog.exists():
        return [f"{BACKLOG.as_posix()} 不存在 —— R5 无法执行，不得静默通过"]
    if not refs_dir.is_dir():
        return [f"{REFERENCES_DIR.as_posix()}/ 不存在 —— R5 无法执行，不得静默通过"]

    landed: list[str] = []
    row = re.compile(r"^\| (L-\d+) \|")
    for line in backlog.read_text(encoding="utf-8").splitlines():
        m = row.match(line)
        if not m:
            continue
        # 取状态列（最后一列）
        cell = line.strip().rstrip("|").rsplit("|", 1)[-1].strip()
        if any(s in cell for s in _LANDED_STATES):
            landed.append(m.group(1))

    annotated: set[str] = set()
    for path in sorted(refs_dir.glob("*.md")):
        annotated.update(re.findall(r"(?<![0-9A-Za-z-])(L-\d+)(?![0-9A-Za-z-])",
                                    path.read_text(encoding="utf-8")))

    missing = [x for x in landed if x not in annotated]
    if not missing:
        return []
    return [
        f"这些条目在登记册里已标为落地，但 `{REFERENCES_DIR.as_posix()}/` 里找不到它们的编号 "
        f"—— 落地了没回标，`未落地` 标注会继续骗下一个读它的人：{', '.join(missing)}"
    ]


def main() -> int:
    problems: list[str] = []
    declared: dict[str, str] = {}
    for path in sorted(TESTS_DIR.rglob("test_*.py")):
        module_problems, module_declared = check_module(path)
        problems.extend(module_problems)
        declared.update(module_declared)
    problems.extend(check_reasons_are_not_templated(declared))
    problems.extend(check_gates_have_negative_controls())
    problems.extend(check_gates_are_wired_into_ci())
    problems.extend(check_landed_items_are_back_annotated())

    scanned = sorted(p.name for p in TESTS_DIR.rglob("test_*.py"))
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
