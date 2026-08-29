"""封闭算术解析器 —— 从零手写，与 `semantic_layer.dsl` **物理隔离**（D-017）。

## 语法边界恰好是这些

**含**：字段引用（点号路径）、四则运算、括号、数值字面量、一元负号。
**不含**：比较运算符、逻辑运算符、`is_missing()`、字符串字面量、函数调用。

节点集封闭为四个：`Num` / `Ref` / `BinOp` / `UnaryOp`。
Phase 2 的 `pre_execute` 将来要静态检查的就是这四个 —— 检查对象必须是本模块
自己定义的封闭节点集，而不是 Python 的完整语法。

## 三条硬约束（D-017，逐条都有验收断言）

1. **不使用 Python 的内建求值函数。** D-017 明写这不是选项讨论，是硬性排除。
2. **不使用 Python 的语法树标准库模块。** 两条理由逐字记在 `dsl.py` 的
   docstring 第 1–12 行：其一，字段引用以报表前缀开头，`is.` 与 Python 关键字
   `is` 冲突，`is.net_profit_attributable_to_parent` 在 Python 语法下直接是
   SyntaxError，用它得在外面再包一层名字改写，省下的代码又吐回去；
   其二，用它就放弃了封闭节点集。两条对本模块同样成立。
3. **`src/semantic_layer/dsl.py` 在本计划的 diff 必须为空。**
   绝不复用 `dsl.parse_condition()` 这个公开入口 —— 复用了就等于让 `flags`
   与 `undefined_conditions` 也间接获得算术能力，直接违反
   「两者共用一套语法，MUST NOT 各自扩展」那条 Requirement。

`ROOT_NAMESPACES` 是**只读**导入的，不在本模块重新定义一份前缀集：
两处各写一份必然漂移，而漂移的表现是「同一个字段引用在条件里合法、在公式里非法」。

## 那 30–40 行重复的词法逻辑只有一条测试拦得住

D-017 判据 3：对同一组字段引用字符串，`dsl` 的词法器与本模块的词法器必须给出
**相同的字段引用序列**。见 `tests/test_formula.py` 的一致性测试。

## 缺失语义沿用 `dsl.py` 已确立的 fail-closed 精神

- `cell_state is ROW_ABSENT` 的字段参与运算即**拒答**，不静默当 0
- `cell_state is EMPTY_CELL` 的字段按 **0** 参与运算
  （A-2 的处置：茅台四个有息负债分项行在格子空，正确答案是 0 不是缺失）
- `retrieval is ATTEMPTED_UNKNOWN` 的字段参与运算即拒答 —— 判不出就是判不出

两者的区分是 SC-3。本模块把语义定死，真实回归用例在 `01.5-03-PLAN.md`。

## 一处命名上的雷，写在这里免得踩

`ArithmeticError` 这个名字**遮蔽了 Python 内建的同名异常**（D-017 与
`01.5-01-PLAN.md` 指定了这个类名）。于是在本模块内部，`except ArithmeticError`
指的是下面这个类，**捕不到** `decimal.DivisionByZero` 这类内建算术异常
（它们是内建 `ArithmeticError` 的子类）。所以本模块一律显式写
`decimal.DivisionByZero` / `decimal.InvalidOperation`，不写裸的 `ArithmeticError`。
"""

from __future__ import annotations

import decimal
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Union

from semantic_layer.dsl import ROOT_NAMESPACES  # 只读导入，防两个词法器的前缀集漂移
from semantic_layer.resolve import Refusal, RefusalCode

from .record import CellState, ExtractionBatch, RetrievalOutcome

__all__ = [
    "ArithmeticError",
    "Num",
    "Ref",
    "BinOp",
    "UnaryOp",
    "Node",
    "NODE_TYPES",
    "SOURCE_FORMULA",
    "parse_formula",
    "field_refs",
    "evaluate_formula",
    "InputPointer",
    "compute_metric",
    "compute_metrics",
    "ComputeResult",
]

#: 责任方标识（L-9）。稳定串，可逐字比对（J-6）。
SOURCE_FORMULA = "formula:closed_arithmetic"

_BINARY_OPS = frozenset({"+", "-", "*", "/"})


class ArithmeticError(ValueError):  # noqa: A001 - 类名由 D-017 指定，见模块 docstring
    """表达式不合本模块的语法，或用了语法边界之外的构造。

    与 `dsl.DslError` 同型但**刻意不共享基类**：共享基类会让「这两个解析器是
    同一套东西」这个错觉有落脚点，而 D-017 要的恰恰是它们物理隔离。
    """


# --------------------------------------------------------------------------
# 封闭节点集 —— 就这四个
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Num:
    value: Decimal


@dataclass(frozen=True)
class Ref:
    path: str


@dataclass(frozen=True)
class BinOp:
    op: str
    left: "Node"
    right: "Node"


@dataclass(frozen=True)
class UnaryOp:
    op: str
    operand: "Node"


Node = Union[Num, Ref, BinOp, UnaryOp]

#: 封闭性由 `tests/test_formula.py` 断言：解析产物里不许出现这四个之外的类型。
NODE_TYPES = (Num, Ref, BinOp, UnaryOp)


# --------------------------------------------------------------------------
# 词法器
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class _Token:
    kind: str  # FIELD NUMBER OP LPAREN RPAREN
    value: object
    pos: int


def _is_ident_start(ch: str) -> bool:
    return ch.isalpha() or ch == "_"


def _is_ident_char(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


def _tokenize(text: str) -> list[_Token]:
    """字段引用的词法**与 `dsl._tokenize` 保持一致**（D-017 判据 3 的对象）。

    与 `dsl` 的差别只在两处，且都是刻意的：
    这里认四则运算符，`dsl` 不认；`dsl` 认比较运算符、字符串与裸标识符，这里不认。
    """
    tokens: list[_Token] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if ch == "(":
            tokens.append(_Token("LPAREN", "(", i))
            i += 1
            continue
        if ch == ")":
            tokens.append(_Token("RPAREN", ")", i))
            i += 1
            continue
        if ch in _BINARY_OPS:
            # 负号是不是一元由解析器按位置决定，词法器只管认出这个符号。
            # 数字字面量里的负号在下面的分支里被吃掉，不会走到这里。
            if ch == "-" and i + 1 < n and text[i + 1].isdigit() and _expects_operand(tokens):
                pass  # 落到数字分支
            else:
                tokens.append(_Token("OP", ch, i))
                i += 1
                continue
        if ch.isdigit() or (ch == "-" and i + 1 < n and text[i + 1].isdigit()):
            j = i + 1 if ch == "-" else i
            seen_dot = False
            while j < n and (text[j].isdigit() or (text[j] == "." and not seen_dot)):
                if text[j] == ".":
                    # 只有后面还是数字才算小数点，否则是字段引用的点（照抄 dsl 的判据）
                    if j + 1 >= n or not text[j + 1].isdigit():
                        break
                    seen_dot = True
                j += 1
            tokens.append(_Token("NUMBER", Decimal(text[i:j]), i))
            i = j
            continue
        if _is_ident_start(ch):
            j = i
            while j < n and _is_ident_char(text[j]):
                j += 1
            word = text[i:j]
            if j < n and text[j] == ".":
                parts = [word]
                k = j
                while k < n and text[k] == ".":
                    k += 1
                    m = k
                    while m < n and _is_ident_char(text[m]):
                        m += 1
                    if m == k:
                        raise ArithmeticError(f"位置 {k}：点号后缺少标识符")
                    parts.append(text[k:m])
                    k = m
                tokens.append(_Token("FIELD", ".".join(parts), i))
                i = k
                continue
            # 裸标识符在算术语法里没有位置。这条同时挡掉 `__import__("os")` 这类形态：
            # 本模块没有函数调用、没有字符串字面量，也没有名字查找 ——
            # L-33 要的是**不留任何能到达求值的入口**，不只是不调用求值函数。
            raise ArithmeticError(
                f"位置 {i}：{word!r} 不是字段引用（算术语法里没有裸标识符与函数调用）"
            )
        raise ArithmeticError(
            f"位置 {i}：非法字符 {ch!r}。比较运算、逻辑运算与字符串不在本语法内 ——"
            "它们属 semantic_layer.dsl，两者不得互相扩展。"
        )
    return tokens


def _expects_operand(tokens: list[_Token]) -> bool:
    """下一个 token 该是操作数吗？用来区分二元减号与负数字面量。"""
    if not tokens:
        return True
    last = tokens[-1]
    return last.kind in ("OP", "LPAREN")


# --------------------------------------------------------------------------
# 递归下降解析器：expr < term < factor < atom
# --------------------------------------------------------------------------


class _Parser:
    def __init__(self, tokens: list[_Token], source: str) -> None:
        self._tokens = tokens
        self._source = source
        self._i = 0

    def _peek(self) -> _Token | None:
        return self._tokens[self._i] if self._i < len(self._tokens) else None

    def _next(self) -> _Token:
        tok = self._peek()
        if tok is None:
            raise ArithmeticError(f"表达式意外结束：{self._source!r}")
        self._i += 1
        return tok

    def parse(self) -> Node:
        node = self._parse_expr()
        rest = self._peek()
        if rest is not None:
            raise ArithmeticError(f"位置 {rest.pos}：表达式解析后仍有剩余 {rest.value!r}")
        return node

    def _parse_expr(self) -> Node:
        node = self._parse_term()
        while True:
            tok = self._peek()
            if tok is not None and tok.kind == "OP" and tok.value in ("+", "-"):
                self._i += 1
                node = BinOp(op=str(tok.value), left=node, right=self._parse_term())
                continue
            return node

    def _parse_term(self) -> Node:
        node = self._parse_factor()
        while True:
            tok = self._peek()
            if tok is not None and tok.kind == "OP" and tok.value in ("*", "/"):
                self._i += 1
                node = BinOp(op=str(tok.value), left=node, right=self._parse_factor())
                continue
            return node

    def _parse_factor(self) -> Node:
        tok = self._peek()
        if tok is not None and tok.kind == "OP" and tok.value == "-":
            self._i += 1
            return UnaryOp(op="-", operand=self._parse_factor())
        return self._parse_atom()

    def _parse_atom(self) -> Node:
        tok = self._next()
        if tok.kind == "NUMBER":
            return Num(value=tok.value)  # type: ignore[arg-type]
        if tok.kind == "FIELD":
            path = str(tok.value)
            root = path.split(".", 1)[0]
            if root not in ROOT_NAMESPACES:
                raise ArithmeticError(
                    f"位置 {tok.pos}：字段引用 {path!r} 的根命名空间 {root!r} "
                    f"不在 {sorted(ROOT_NAMESPACES)} 内"
                )
            return Ref(path=path)
        if tok.kind == "LPAREN":
            node = self._parse_expr()
            closing = self._next()
            if closing.kind != "RPAREN":
                raise ArithmeticError(f"位置 {closing.pos}：括号未闭合")
            return node
        raise ArithmeticError(f"位置 {tok.pos}：这里期望一个操作数，得到 {tok.value!r}")


def parse_formula(text: str) -> Node:
    """公式字符串 → 封闭语法树。任何越界构造一律 `ArithmeticError`。"""
    if not isinstance(text, str) or not text.strip():
        raise ArithmeticError(f"公式必须是非空字符串，实际是 {text!r}")
    return _Parser(_tokenize(text), text).parse()


def field_refs(node: Node) -> tuple[str, ...]:
    """语法树里的字段引用，**按出现顺序、可重复**。证据链要逐条列出输入指针（L-54）。"""
    if isinstance(node, Ref):
        return (node.path,)
    if isinstance(node, BinOp):
        return field_refs(node.left) + field_refs(node.right)
    if isinstance(node, UnaryOp):
        return field_refs(node.operand)
    if isinstance(node, Num):
        return ()
    raise ArithmeticError(f"语法树里出现了封闭节点集之外的节点：{type(node).__name__}")


# --------------------------------------------------------------------------
# 求值
# --------------------------------------------------------------------------


def _operand(batch: ExtractionBatch, path: str) -> Decimal | Refusal:
    """一个字段引用的取值。缺失语义 fail-closed，见模块 docstring。"""
    record = batch.by_field(path)
    if record is None:
        return Refusal(
            RefusalCode.UNAVAILABLE,
            f"字段 {path!r} 不在批次 {batch.batch_id} 里，无从求值。",
            source=SOURCE_FORMULA,
        )
    if record.retrieval is RetrievalOutcome.ATTEMPTED_UNKNOWN:
        return Refusal(
            RefusalCode.UNEVALUABLE_CONDITION,
            f"字段 {path!r} 的抽取结果是「试过但判不出」，不参与运算。"
            "在两个已知态里挑一个报就是拿手边能求值的东西凑一个答案。",
            source=SOURCE_FORMULA,
        )
    if record.cell_state is CellState.ROW_ABSENT:
        return Refusal(
            RefusalCode.UNEVALUABLE_CONDITION,
            f"字段 {path!r} 整行不存在于该报表，不当 0 参与运算。"
            "「整行不存在」与「行在格子空」是两回事（SC-3）。",
            source=SOURCE_FORMULA,
        )
    if record.cell_state is CellState.EMPTY_CELL:
        return Decimal(0)
    if not isinstance(record.value, Decimal):
        return Refusal(
            RefusalCode.UNEVALUABLE_CONDITION,
            f"字段 {path!r} 的值 {record.value!r} 不是十进制数，不参与算术。",
            source=SOURCE_FORMULA,
        )
    return record.value


def evaluate_formula(node: Node, batch: ExtractionBatch) -> Decimal | Refusal:
    """封闭求值。**没有名字查找、没有函数调用、没有属性访问。**

    数值一律 `decimal.Decimal`，不用二进制浮点：金额上的舍入漂移会直接污染
    勾稽差额与交叉校验的判定。
    """
    if isinstance(node, Num):
        return node.value
    if isinstance(node, Ref):
        return _operand(batch, node.path)
    if isinstance(node, UnaryOp):
        operand = evaluate_formula(node.operand, batch)
        if isinstance(operand, Refusal):
            return operand
        return -operand
    if isinstance(node, BinOp):
        left = evaluate_formula(node.left, batch)
        if isinstance(left, Refusal):
            return left
        right = evaluate_formula(node.right, batch)
        if isinstance(right, Refusal):
            return right
        if node.op == "+":
            return left + right
        if node.op == "-":
            return left - right
        if node.op == "*":
            return left * right
        if node.op == "/":
            try:
                return left / right
            except (decimal.DivisionByZero, decimal.InvalidOperation):
                # 显式写内建异常名：本模块的 `ArithmeticError` 遮蔽了内建同名类，
                # 裸 `except ArithmeticError` 在这里捕不到它们（见模块 docstring）。
                return Refusal(
                    RefusalCode.UNEVALUABLE_CONDITION,
                    f"除数为零：{node.right}",
                    source=SOURCE_FORMULA,
                )
        raise ArithmeticError(f"未接线的二元运算符 {node.op!r}")
    raise ArithmeticError(f"语法树里出现了封闭节点集之外的节点：{type(node).__name__}")


# --------------------------------------------------------------------------
# 计算层的读入边界（D-018 / ARCHITECTURE §8.4）
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class InputPointer:
    """一条参与运算的抽取记录的**显式**指针（`L-54`）。

    ## 为什么不是一个 `field_id` 字符串

    字符串要靠「同一次抽取批次」「同一个写入顺序」这类**隐式假设**才能定位到记录。
    `01.5-RESEARCH` Q4 记着 harness 的 `sourceEventSeqs` 是**显式数组引用**
    而不是靠事件先后推断关联，理由同此。

    而 `ARCHITECTURE` §8.5 记的那个反面更直接：
    `full_output_path` 只是个**可选返回值**，于是在唯二两个调用点全被丢掉。
    ⇒ **指针只要不在返回类型里、且可为空，接线时一定会被丢掉。**
    所以 `ComputeResult.inputs` 不可为空、不可为可选，且每个元素是这个结构而不是一个名字。
    """

    field_id: str
    page: int
    anchor_page: int
    batch_id: str
    value: Decimal | str | None
    mapping_version: int
    #: 版面上印的那列的字（`2023年12月31日`）。列错是勾稽闸门抓不到的那一类（`A-9`）。
    column_header: str | None

    def to_dict(self) -> dict:
        return {
            "field_id": self.field_id,
            "page": self.page,
            "anchor_page": self.anchor_page,
            "batch_id": self.batch_id,
            "value": None if self.value is None else str(self.value),
            "mapping_version": self.mapping_version,
            "column_header": self.column_header,
        }


@dataclass(frozen=True)
class ComputeResult:
    """一个算出来的指标值，连同它的全部输入指针（L-54）。

    `derived` 恒为 True 且 `inputs` 非空：派生指标必须标 `derived` 并携带其
    输入字段的指针。**估算值不得进入证据链** —— 本模块只做算术，不做估算。
    """

    metric_id: str
    definition_version: int
    formula: str
    value: Decimal
    unit: str
    currency: str
    batch_id: str
    inputs: tuple[InputPointer, ...]
    #: 本期**置位**的可比性标记。`flags_status` 为 `unevaluable` 时它必为空 ——
    #: 空集在那种情形下表示「判不了」而不是「一个都没触发」，两者靠 `flags_status` 区分。
    flags: tuple[str, ...] = ()
    #: `evaluated` / `unevaluable`，外加 `unevaluable` 时的理由。
    #:
    #: 🔴 **这个字段是 2026-08-27 接上真实字段后补的，它记的是一个真实缺口**：
    #: 8 个指标里 6 个的 `restated` 触发条件引用 `notes.restatement_flag`，
    #: 而那个字段的 `kind` 是 `COLUMN_HEADER_PRESENCE` —— **至今未实现，且不属于任何计划**
    #: （2026-08-28 更正：原文写「wave 5 才实现」，那个排期是编出来的，见台账 `N-43`）
    #: ⇒ **数值算得出来，它的可比性标记判不了**。
    #:
    #: 补这个字段之前，`ComputeResult` 里没有任何东西透露这件事 ——
    #: 一个「资产负债率 = 0.1798」被产出时，调用方无从知道它的 `restated` 状态未知。
    #: 那正是 `ARCHITECTURE` §8.5 的形状，只是方向不同：不是指针被丢掉，
    #: 是**两条本该耦合的路径根本没接线**。
    #:
    #: ⚠️ **本轮不让它阻断计算**：接上就有 6 个指标全数拒答，SC-5 直接不成立。
    #: 该不该阻断要等 wave 5 把那三支 `kind` 实现之后、拿真实取值再定 ——
    #: 现在定就是在没有数据的情况下拍板。**但缺口必须在证据链里看得见。**
    flags_status: str = "evaluated"
    flags_note: str = ""
    #: `definition_version` 是从批次快照取的，还是回退到了当前 `metrics/`。
    #: **留证，不是调试开关**：回退意味着这次复核用的不是抽取时刻的口径，
    #: 而那正是 `L-38` 要防的事 —— 它必须在证据链里看得见。
    version_source: str = "batch-snapshot"
    derived: bool = True

    def __post_init__(self) -> None:
        if not self.inputs:
            raise ArithmeticError(
                f"{self.metric_id}：`inputs` 不可为空。派生值必须携带它的输入指针（L-54）。"
            )

    def to_dict(self) -> dict:
        return {
            "metric_id": self.metric_id,
            "definition_version": self.definition_version,
            "version_source": self.version_source,
            "formula": self.formula,
            "value": str(self.value),
            "unit": self.unit,
            "currency": self.currency,
            "batch_id": self.batch_id,
            "inputs": [p.to_dict() for p in self.inputs],
            "flags": list(self.flags),
            "flags_status": self.flags_status,
            "flags_note": self.flags_note,
            "derived": self.derived,
        }


def compute_metric(
    metric_id: str,
    batch: ExtractionBatch,
    metrics_dir: Path | str = "metrics",
) -> ComputeResult | Refusal:
    """算一个指标。**第一件事是读闸门标记，未通过即拒答且不产出任何数值。**

    fail-closed 放**读入侧**不放写入侧：放写入侧的话，任何绕过写入侧的路径都会
    静默逃逸；放读入侧，所有消费者都必须过这道门（ARCHITECTURE §8.4）。
    """
    # 闸门标记按**类型**读，不用 `getattr` 鸭子式地摸。理由不只是洁癖：
    # `getattr(gate, "passed", False)` 会让任何一个碰巧带 `passed` 属性的东西
    # 冒充闸门结果，而这里恰恰是本模块唯一的 fail-closed 判定点。
    # 顺带：全模块因此一处 `getattr` 都没有，「没有属性访问」这句话才立得住。
    from .reconcile import SOURCE_RECONCILE, ReconcileResult

    gate = batch.reconciliation
    if not isinstance(gate, ReconcileResult):
        return Refusal(
            RefusalCode.RECONCILIATION_FAILED,
            f"批次 {batch.batch_id} 没跑过勾稽闸门（reconciliation={gate!r}）。"
            "没跑过 ≠ 通过 —— 读入边界一律按未通过处置（D-018）。",
            metric_id=metric_id,
            source="reconcile:not_run",
        )
    if not gate.passed:
        return Refusal(
            RefusalCode.RECONCILIATION_FAILED,
            f"批次 {batch.batch_id} 的会计恒等式校验未通过："
            f"{gate.identity}，差额 {gate.difference}，缺项 {list(gate.missing_fields)}。"
            "闸门未通过时不产出数值。",
            metric_id=metric_id,
            source=SOURCE_RECONCILE,
        )

    from semantic_layer.resolve import Registry  # 局部 import：保持依赖方向单向且显式

    try:
        registry = Registry.load(metrics_dir)
    except ValueError as exc:
        return Refusal(RefusalCode.ALIAS_AMBIGUOUS, str(exc), metric_id=metric_id)
    defn = registry.resolve(metric_id)
    if isinstance(defn, Refusal):
        return defn
    if not defn.formula:
        return Refusal(
            RefusalCode.DEFINITION_NONCONFORMANT,
            f"口径定义 {metric_id!r} 没有 formula，算不出数值。",
            metric_id=metric_id,
        )

    tree = parse_formula(defn.formula)
    value = evaluate_formula(tree, batch)
    if isinstance(value, Refusal):
        return Refusal(
            value.code, value.detail, metric_id=metric_id, source=value.source
        )

    paths = field_refs(tree)
    records = [batch.by_field(path) for path in paths]
    missing = [p for p, r in zip(paths, records) if r is None]
    if missing:
        # 走到这里说明 `evaluate_formula` 没拦住 —— 属实现缺陷，但**仍然拒答**，
        # 绝不返回一个少了几项的数（`L-80`：失败不得降级成形态合法的返回值）。
        return Refusal(
            RefusalCode.UNEVALUABLE_CONDITION,
            f"批次 {batch.batch_id} 里找不到输入字段 {missing}，拒答。",
            metric_id=metric_id,
            source=SOURCE_FORMULA,
        )
    units = {r.unit for r in records}
    currencies = {r.currency for r in records}
    if len(units) != 1 or len(currencies) != 1:
        # 混单位的算术没有意义，且这个错误不会自己暴露出来。
        return Refusal(
            RefusalCode.UNEVALUABLE_CONDITION,
            f"输入字段的单位或币种不一致：单位 {sorted(units)}，币种 {sorted(currencies)}。"
            "拒答并置 unit_scale_mismatch，不替调用方换算。",
            metric_id=metric_id,
            source=SOURCE_FORMULA,
        )

    # `L-38`：口径版本取自**抽取时刻冻结在批次里的快照**，不取当前 `metrics/`。
    snapshot = dict(batch.definition_versions or {})
    if metric_id in snapshot:
        version, version_source = snapshot[metric_id], "batch-snapshot"
    else:
        # 快照里没有 = 这批是快照机制上线前建的，或该指标当时不存在。
        # 回退到当前定义，但**把回退这件事记进证据链** —— 见 `version_source` 的注释。
        version, version_source = int(defn.version), "current-metrics-dir"

    # 可比性标记：**求得了就记触发结果，求不了就记「判不了」**。
    # 两者都要在证据链里看得见 —— 「一个都没触发」与「根本判不了」
    # 在下游看来后果完全不同，混成一个空集就再也分不开了。
    from semantic_layer.resolve import active_flags

    row = {r.field_id: r.value for r in batch.records}
    flag_outcome = active_flags(defn, row)
    if isinstance(flag_outcome, Refusal):
        flags, flags_status = (), "unevaluable"
        flags_note = flag_outcome.detail
    else:
        flags, flags_status = tuple(sorted(flag_outcome)), "evaluated"
        flags_note = ""

    return ComputeResult(
        metric_id=metric_id,
        definition_version=version,
        version_source=version_source,
        flags=flags,
        flags_status=flags_status,
        flags_note=flags_note,
        formula=defn.formula.strip(),
        value=value,
        # 比率是无量纲的：两个同单位金额相除，单位与币种都被约掉。
        # 如实写「无量纲」，不照抄输入的「元」—— 那会让证据链声称一个比率的单位是元。
        unit="无量纲" if _is_ratio(tree) else units.pop(),
        currency="不适用" if _is_ratio(tree) else currencies.pop(),
        batch_id=batch.batch_id,
        inputs=tuple(
            InputPointer(
                field_id=r.field_id,
                page=r.page,
                anchor_page=r.anchor_page,
                batch_id=r.batch_id,
                value=r.value,
                mapping_version=r.mapping_version,
                column_header=r.column_header,
            )
            for r in records
        ),
    )


def compute_metrics(
    metric_ids, batch, metrics_dir: Path | str = "metrics"
) -> list["ComputeResult | Refusal"]:
    """算一批指标。**逐个独立求值，一个拒答不影响其余的。**

    不做「有一个失败就整批失败」：拒答是**正确行为**不是错误（`D-003`），
    把它传染给其余指标会让一次本可部分完成的回答退化成什么都答不出。
    批次级的 fail-closed 已经由勾稽闸门在每次 `compute_metric` 的第一步做掉了。
    """
    return [compute_metric(mid, batch, metrics_dir) for mid in metric_ids]


def _is_ratio(node: Node) -> bool:
    """最外层是除法 ⇒ 结果无量纲。

    刻意只看最外层、只认这一种形态：本阶段的指标只有 `A / B` 这一个形状，
    更一般的量纲推导需要每个字段都声明量纲，那是 U-01（证据链字段集）的活，
    **不在本阶段拍板**。多认一种形态就是在数据不足时提前定死量纲系统。
    """
    return isinstance(node, BinOp) and node.op == "/"
