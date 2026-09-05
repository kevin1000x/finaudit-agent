"""执行前的闸门（`02-01` T2，`PROJECT_SPEC` §5.2 的 `pre_execute`）。

## 为什么闸门与执行路径必须在同一次改动里做出来

「闸门不可绕过」是**结构性质**，不是一条检查。事后加上去的闸门天然有旁路 ——
所以本模块同时提供**唯一的执行入口** `execute()`，它无条件先过 `pre_execute()`，
计算函数由调用方注入、且只可能在闸门通过之后被调用。

## 检查对象是语法树，不是字符串

`PROJECT_SPEC` §5.1 逐字写着：静态检查的对象「**必须是一个封闭的节点集**，
而不是某个通用语言的完整语法树」。受限语法是这道闸门成立的**前提** ——
所以「树里出现了封闭集之外的节点」本身就是一条检查（`封闭节点集`），
它守的是前提，不是某个具体缺陷。

⚠️ **不要以为解析器已经挡住了这些。** 解析器只管**它自己解析出来的**树；
本模块拿到的树可能是任何人构造的。闸门检查的是**它实际拿到的那些**。

## 一个请求装的是「这次会被求值的全部树」，不是其中一棵

2026-09-05 独立复核发现：`GateRequest` 此前是单数 `tree`，而 `answer_question`
送进 `execute()` 的是第一条拒答条件那棵，`run` 求的却是**公式**那棵。
公式字段当时确实在别处逐棵过了闸，所以**不是**一个能算错数的洞 ——
但「`execute()` 无条件先过闸门」守的不是被执行的那个东西，
`ExecutionRecord.referenced_fields` 记的也是另一棵树的字段。
**这是 `N-42` 的同一个形状：门声称守住的集合 ≠ 它实际扫的集合。**
⇒ 改成 `trees`（复数），`execute()` 与显式的那次 `pre_execute` 用**同一个请求**。

## 五道检查里有一道今天守不到生产路径

`口径版本匹配` 需要调用方**声明**它要哪一版（`expected_version`）。
不声明就没有可比对的东西 ⇒ 这道检查在默认路径上不会触发。
仓库里今天没有会声明它的生产调用方（评测运行器**刻意不传**：
`expected.metric_version` 是题面的标准答案，喂回输入就是 `target_name` 那个错误）。
**如实记在 `N-57`**，不写成「五道门都在守着生产路径」。

## `AC-09` 的负控制做成了常跑的一对

`AC-09` 2026-08-27 加强过：不只要「危险样本被拒」，还要
「**把那道校验移除后该样本确实被放行**」，否则你验的不是这道闸门（`N-45`）。
⇒ 检查做成**具名注册表** `CHECKS`，`pre_execute(req, checks=...)` 可以抽掉其中一道。
`tests/test_gate.py` 里每个样本一对断言。

**这一对不可能被一个「从不触发的检查」满足**：从不触发的话第一条断言先红。

⚠️ **已知的措辞不精确**（记 `N-55`）：版本不匹配用的是 `CROSS_VERSION_COMPARISON`，
而那支码的语义原文写的是「**两期**结论由不同版本的口径定义产出」，
这里是单期。`detail` 里写明了实际情况，**没有靠码名去表达它**。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from semantic_layer import dsl
from semantic_layer.definition import MetricDefinition
from semantic_layer.resolve import Refusal, RefusalCode

__all__ = ["GateRequest", "GateCheck", "CHECKS", "pre_execute", "ExecutionRecord", "execute"]


@dataclass(frozen=True)
class GateRequest:
    """一次执行请求。闸门只看这里面的东西。

    `trees` 是**复数**，装的是这一次执行**会被求值的全部语法树** ——
    拒答条件、公式里的字段引用、可比性标记的 trigger，一个都不能落下。

    🔴 2026-09-05 独立复核发现的形状：此前这里是单数 `tree`，
    而 `answer_question` 送进 `execute()` 的是 `trees[0]`（第一条拒答条件），
    `run` 求的却是**公式**那棵树。于是「无条件先过闸门」守的不是被执行的那个东西，
    `ExecutionRecord.referenced_fields` 记的也是另一棵树的字段。
    公式的字段当时确实在别处过了闸，所以**不是**一个能算错数的洞 ——
    但那道门声称守住的和它实际守住的不是同一件事（`N-42` 的同一个形状）。

    `expected_version` 是**调用方声明它要哪一版口径**，`None` = 没声明。
    ⚠️ 见 `_check_version` 的注释：仓库里今天还没有会声明它的生产调用方。
    """

    defn: MetricDefinition
    expected_version: Any
    trees: tuple
    entity: str
    period: int
    question_sha256: str


@dataclass(frozen=True)
class GateCheck:
    """一道具名检查。**具名是为了能给它写负控制** —— 那正是 `AC-09` 加强前缺的东西。"""

    name: str
    fn: Callable[[GateRequest], "Refusal | None"]


_CLOSED_NODES = (dsl.FieldRef, dsl.Literal, dsl.IsMissing, dsl.Compare, dsl.Not, dsl.And, dsl.Or)


def _walk(node):
    """遍历语法树。**遇到封闭集之外的节点就停在那里并把它交出去** ——
    不抛异常，因为「树里有陌生节点」是一条要报告的检查结果，不是本函数的错误。
    """
    yield node
    if isinstance(node, dsl.IsMissing):
        yield from _walk(node.operand)
    elif isinstance(node, dsl.Compare):
        yield from _walk(node.left)
        yield from _walk(node.right)
    elif isinstance(node, dsl.Not):
        yield from _walk(node.operand)
    elif isinstance(node, (dsl.And, dsl.Or)):
        yield from _walk(node.left)
        yield from _walk(node.right)


def _field_refs(trees) -> list[str]:
    """全部树里引用到的字段路径，**去重保序**。

    留痕要的是「这一次执行碰了哪些字段」——一棵树漏掉，留痕就少记一部分出处。
    """
    out: list[str] = []
    for tree in trees:
        for n in _walk(tree):
            if isinstance(n, dsl.FieldRef) and n.path not in out:
                out.append(n.path)
    return out


def _check_definition_conformant(req: GateRequest):
    if req.defn.parse_error:
        return Refusal(
            RefusalCode.DEFINITION_NONCONFORMANT,
            f"口径定义本身不合规，不允许被消费：{req.defn.parse_error}",
            metric_id=req.defn.metric_id,
            source="gate:定义合规",
        )
    return None


def _check_version(req: GateRequest):
    """调用方声明的口径版本 vs 定义当前的版本。

    ⚠️ **如实记着这道门今天守不到生产路径。** 2026-09-05 独立复核实测：
    此前两个调用点都传 `expected_version=defn.version`（拿它自己跟它自己比），
    于是这道检查在生产上**永远不可能红**——`L-32` 点名的那种形状。
    现在 `None` 表示「调用方没声明要哪一版」，声明了才比对；
    `answer_question(..., expected_version=X)` 是那条声明入口。
    **但仓库里今天还没有会传它的生产调用方**（评测运行器**刻意不传**：
    `expected.metric_version` 是题面的标准答案，喂回输入就是 `target_name` 那个错误）。
    ⇒ 它有真实回归（`test_样本3` 与 `test_调用方声明的口径版本对不上就拒答`），
    但**没有**真实生产触发点，记在 `N-57`。
    """
    if req.expected_version is None:
        return None
    if req.expected_version != req.defn.version:
        return Refusal(
            RefusalCode.CROSS_VERSION_COMPARISON,
            f"请求声明的口径版本是 {req.expected_version!r}，"
            f"而 {req.defn.metric_id} 当前定义是 {req.defn.version!r} —— 不拿另一版的口径作答。",
            metric_id=req.defn.metric_id,
            source="gate:口径版本匹配",
        )
    return None


def _check_closed_node_set(req: GateRequest):
    for node in (n for tree in req.trees for n in _walk(tree)):
        if not isinstance(node, _CLOSED_NODES):
            return Refusal(
                RefusalCode.UNEVALUABLE_CONDITION,
                f"语法树里出现封闭节点集之外的节点：{type(node).__name__}。"
                "受限语法是这道闸门成立的前提，不放行。",
                metric_id=req.defn.metric_id,
                source="gate:封闭节点集",
            )
    return None


def _check_namespace(req: GateRequest):
    allowed = dsl.ROOT_NAMESPACES | dsl.INTRINSIC_NAMESPACES
    for path in _field_refs(req.trees):
        root = path.split(".", 1)[0]
        if root not in allowed:
            return Refusal(
                RefusalCode.UNEVALUABLE_CONDITION,
                f"字段 {path} 的命名空间 {root!r} 不在授权数据源里"
                f"（授权：{sorted(allowed)}）。",
                metric_id=req.defn.metric_id,
                source="gate:授权命名空间",
            )
    return None


def _check_declared(req: GateRequest):
    """引用了定义没声明的字段 = 越过口径去取数。

    `INTRINSIC_NAMESPACES` 指的是定义自身的元数据，不指向行数据，**无需声明**。
    """
    declared = {sf.id for sf in req.defn.source_fields if sf.id}
    for path in _field_refs(req.trees):
        root = path.split(".", 1)[0]
        if root in dsl.INTRINSIC_NAMESPACES:
            continue
        if path not in declared:
            return Refusal(
                RefusalCode.UNEVALUABLE_CONDITION,
                f"条件引用了 {path}，而 {req.defn.metric_id} 的定义没有声明这个字段 —— "
                "越过口径取数即拒答。",
                metric_id=req.defn.metric_id,
                source="gate:字段已在定义中声明",
            )
    return None


#: 顺序即执行顺序。**具名是负控制的前提**（`AC-09`）。
CHECKS: tuple[GateCheck, ...] = (
    GateCheck("定义合规", _check_definition_conformant),
    GateCheck("口径版本匹配", _check_version),
    GateCheck("封闭节点集", _check_closed_node_set),
    GateCheck("授权命名空间", _check_namespace),
    GateCheck("字段已在定义中声明", _check_declared),
)


def pre_execute(req: GateRequest, checks: tuple = CHECKS):
    """通过返回 `None`，否则返回说明是哪一道拦下的 `Refusal`。

    `checks` 可以被抽掉一道 —— 那是 `AC-09` 的负控制入口，**不是配置项**。
    生产路径永远用默认值：`execute()` 不接受 `checks`。
    """
    for check in checks:
        got = check.fn(req)
        if got is not None:
            return got
    return None


@dataclass(frozen=True)
class ExecutionRecord:
    """一次执行的留痕。**拒答与放行是同一套字段** ——
    拒答少记字段是最容易犯的，而拒答恰恰是最需要能复核的那一类。
    """

    question_sha256: str
    metric_id: str | None
    metric_version: Any
    entity: str
    period: int
    referenced_fields: list = field(default_factory=list)
    gate: str = "refused"
    refusal: dict | None = None
    result: Any = None

    def to_dict(self) -> dict:
        return {
            "question_sha256": self.question_sha256,
            "metric_id": self.metric_id,
            "metric_version": self.metric_version,
            "entity": self.entity,
            "period": self.period,
            "referenced_fields": list(self.referenced_fields),
            "gate": self.gate,
            "refusal": dict(self.refusal) if self.refusal else None,
            "result": self.result,
        }


def execute(req: GateRequest, run: Callable[[GateRequest], Any]) -> ExecutionRecord:
    """**唯一的执行入口。** 无条件先过闸门；`run` 只可能在闸门通过之后被调用。

    ⚠️ 本函数**不接受** `checks` 参数 —— 那是负控制入口，
    留一个参数出来就等于留了一条「配置掉一道检查」的旁路，
    而 `SC-6` 要的正是「不存在任何配置或插件路径能绕过它」。
    """
    refusal = pre_execute(req)
    base = dict(
        question_sha256=req.question_sha256,
        metric_id=req.defn.metric_id,
        metric_version=req.defn.version,
        entity=req.entity,
        period=req.period,
        referenced_fields=_field_refs(req.trees),
    )
    if refusal is not None:
        return ExecutionRecord(**base, gate="refused", refusal=refusal.to_dict(), result=None)
    return ExecutionRecord(**base, gate="passed", refusal=None, result=run(req))
