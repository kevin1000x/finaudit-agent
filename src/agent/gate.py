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
本模块拿到的树可能是任何人构造的。闸门检查的是**它实际拿到的那棵**。

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
    """一次执行请求。闸门只看这里面的东西。"""

    defn: MetricDefinition
    expected_version: Any
    tree: Any
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


def _field_refs(node) -> list[str]:
    return [n.path for n in _walk(node) if isinstance(n, dsl.FieldRef)]


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
    for node in _walk(req.tree):
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
    for path in _field_refs(req.tree):
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
    for path in _field_refs(req.tree):
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
        referenced_fields=_field_refs(req.tree),
    )
    if refusal is not None:
        return ExecutionRecord(**base, gate="refused", refusal=refusal.to_dict(), result=None)
    return ExecutionRecord(**base, gate="passed", refusal=None, result=run(req))
