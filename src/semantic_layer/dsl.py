"""受限布尔 DSL —— 自研词法器与递归下降解析器。

为什么不用 Python 的语法树模块：本项目的字段引用以报表前缀开头，其中 `is.` 与
Python 关键字 `is` 冲突，`is.net_profit_attributable_to_parent` 在 Python 语法下
直接是 SyntaxError。见 01-01-PLAN.md 的 resolved_design_questions。

更重要的理由是语法树的所有权：L3 的 pre_execute 要对条件做静态检查，检查对象必须是
本模块自己定义的封闭节点集，而不是 Python 的完整语法。

求值语义是 fail-closed 的：比较运算遇到缺失操作数抛错，不静默变 False。
`is_missing()` 是唯一允许接收缺失值的构造。这就是 R6「缺失与取值为零走不同分支」的机械实现。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Union

__all__ = [
    "DslError",
    "MissingOperandError",
    "MISSING",
    "ROOT_NAMESPACES",
    "INTRINSIC_NAMESPACES",
    "Condition",
    "parse_condition",
    "evaluate",
    "normalize_row",
]


class DslError(ValueError):
    """条件字符串不合语法，或使用了白名单之外的构造。"""


class MissingOperandError(RuntimeError):
    """比较运算的操作数缺失。fail-closed：不返回 False，直接抛错。"""


class _Missing:
    """缺失哨兵。与取值为零严格区分（R6）。"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "MISSING"

    def __bool__(self) -> bool:  # 防止被当成假值静默吞掉
        raise MissingOperandError("MISSING 不可用于布尔上下文")


MISSING = _Missing()

# 数据侧根命名空间：引用的是行数据里的字段，必须在定义的 source_fields 中声明
ROOT_NAMESPACES = frozenset({"is", "bs", "cfs", "notes"})
# 定义自身的元数据命名空间：不指向行数据，无需在 source_fields 声明
INTRINSIC_NAMESPACES = frozenset({"standard_basis", "comparison_period", "metric"})

_ALL_ROOTS = ROOT_NAMESPACES | INTRINSIC_NAMESPACES

_PREDICATES = frozenset({"is_missing"})
_KEYWORDS = frozenset({"and", "or", "not"})
_LITERAL_NAMES = {"true": True, "false": False, "null": None}
_COMPARE_OPS = frozenset({"==", "!=", "<", "<=", ">", ">="})


# --------------------------------------------------------------------------
# 语法树节点 —— L3 pre_execute 的静态检查对象就是这七个
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldRef:
    path: str

    @property
    def root(self) -> str:
        return self.path.split(".", 1)[0]


@dataclass(frozen=True)
class Literal:
    value: Any


@dataclass(frozen=True)
class IsMissing:
    operand: FieldRef


@dataclass(frozen=True)
class Compare:
    op: str
    left: Union[FieldRef, Literal]
    right: Union[FieldRef, Literal]


@dataclass(frozen=True)
class Not:
    operand: "Node"


@dataclass(frozen=True)
class And:
    left: "Node"
    right: "Node"


@dataclass(frozen=True)
class Or:
    left: "Node"
    right: "Node"


Node = Union[FieldRef, Literal, IsMissing, Compare, Not, And, Or]

_BOOLEAN_ROOTS = (IsMissing, Compare, Not, And, Or)


@dataclass(frozen=True)
class Condition:
    """一条已解析的条件。`source` 保留原文，供证据链与报告层原样展示。"""

    source: str
    tree: Node
    field_refs: frozenset = field(default_factory=frozenset)


# --------------------------------------------------------------------------
# 词法器
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class _Token:
    kind: str  # FIELD IDENT NUMBER STRING OP LPAREN RPAREN
    value: Any
    pos: int


def _is_ident_start(ch: str) -> bool:
    return ch.isalpha() or ch == "_"


def _is_ident_char(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


def _tokenize(text: str) -> list[_Token]:
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
        if ch in "<>=!":
            two = text[i : i + 2]
            if two in _COMPARE_OPS:
                tokens.append(_Token("OP", two, i))
                i += 2
                continue
            if ch in "<>":
                tokens.append(_Token("OP", ch, i))
                i += 1
                continue
            raise DslError(f"位置 {i}：非法运算符 {text[i:i+2]!r}（赋值与单等号不被支持）")
        if ch in ("'", '"'):
            j = i + 1
            buf = []
            while j < n and text[j] != ch:
                buf.append(text[j])
                j += 1
            if j >= n:
                raise DslError(f"位置 {i}：字符串字面量未闭合")
            tokens.append(_Token("STRING", "".join(buf), i))
            i = j + 1
            continue
        if ch.isdigit() or (ch == "-" and i + 1 < n and text[i + 1].isdigit()):
            j = i + 1 if ch == "-" else i
            seen_dot = False
            while j < n and (text[j].isdigit() or (text[j] == "." and not seen_dot)):
                if text[j] == ".":
                    # 只有后面还是数字才算小数点，否则是字段引用的点
                    if j + 1 >= n or not text[j + 1].isdigit():
                        break
                    seen_dot = True
                j += 1
            raw = text[i:j]
            tokens.append(_Token("NUMBER", float(raw) if seen_dot else int(raw), i))
            i = j
            continue
        if _is_ident_start(ch):
            j = i
            while j < n and _is_ident_char(text[j]):
                j += 1
            word = text[i:j]
            # 字段引用：IDENT ('.' IDENT)+ —— 必须至少含一个点
            if j < n and text[j] == ".":
                parts = [word]
                k = j
                while k < n and text[k] == ".":
                    k += 1
                    m = k
                    while m < n and _is_ident_char(text[m]):
                        m += 1
                    if m == k:
                        raise DslError(f"位置 {k}：点号后缺少标识符")
                    parts.append(text[k:m])
                    k = m
                tokens.append(_Token("FIELD", ".".join(parts), i))
                i = k
                continue
            tokens.append(_Token("IDENT", word, i))
            i = j
            continue
        raise DslError(f"位置 {i}：非法字符 {ch!r}（算术运算与其他符号不在白名单内）")
    return tokens


# --------------------------------------------------------------------------
# 递归下降解析器：or < and < not < 比较 < 原子
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
            raise DslError("表达式意外结束")
        self._i += 1
        return tok

    def _accept_keyword(self, word: str) -> bool:
        tok = self._peek()
        if tok is not None and tok.kind == "IDENT" and tok.value == word:
            self._i += 1
            return True
        return False

    def parse(self) -> Node:
        node = self._parse_or()
        if self._peek() is not None:
            tok = self._peek()
            raise DslError(f"位置 {tok.pos}：表达式结束后仍有多余记号 {tok.value!r}")
        return node

    def _parse_or(self) -> Node:
        node = self._parse_and()
        while self._accept_keyword("or"):
            node = Or(node, self._parse_and())
        return node

    def _parse_and(self) -> Node:
        node = self._parse_not()
        while self._accept_keyword("and"):
            node = And(node, self._parse_not())
        return node

    def _parse_not(self) -> Node:
        if self._accept_keyword("not"):
            return Not(self._parse_not())
        return self._parse_compare()

    def _parse_compare(self) -> Node:
        left = self._parse_atom()
        tok = self._peek()
        if tok is not None and tok.kind == "OP":
            self._next()
            if tok.value not in _COMPARE_OPS:
                raise DslError(f"位置 {tok.pos}：不支持的比较运算符 {tok.value!r}")
            right = self._parse_atom()
            if isinstance(left, (And, Or, Not, IsMissing, Compare)) or isinstance(
                right, (And, Or, Not, IsMissing, Compare)
            ):
                raise DslError("比较运算的两侧必须是字段引用或字面量")
            return Compare(tok.value, left, right)
        return left

    def _parse_atom(self) -> Node:
        tok = self._next()
        if tok.kind == "LPAREN":
            node = self._parse_or()
            closing = self._peek()
            if closing is None or closing.kind != "RPAREN":
                raise DslError(f"位置 {tok.pos}：括号未闭合")
            self._next()
            return node
        if tok.kind == "FIELD":
            root = tok.value.split(".", 1)[0]
            if root not in _ALL_ROOTS:
                raise DslError(
                    f"位置 {tok.pos}：根命名空间 {root!r} 不在白名单 "
                    f"{sorted(_ALL_ROOTS)} 内"
                )
            return FieldRef(tok.value)
        if tok.kind in ("NUMBER", "STRING"):
            return Literal(tok.value)
        if tok.kind == "IDENT":
            word = tok.value
            if word in _LITERAL_NAMES:
                return Literal(_LITERAL_NAMES[word])
            if word in _KEYWORDS:
                raise DslError(f"位置 {tok.pos}：关键字 {word!r} 不能出现在此处")
            nxt = self._peek()
            if nxt is not None and nxt.kind == "LPAREN":
                if word not in _PREDICATES:
                    raise DslError(
                        f"位置 {tok.pos}：{word!r} 不在谓词白名单 {sorted(_PREDICATES)} 内"
                    )
                self._next()
                arg = self._parse_atom()
                if not isinstance(arg, FieldRef):
                    raise DslError("is_missing() 的参数必须是字段引用")
                closing = self._peek()
                if closing is None or closing.kind != "RPAREN":
                    raise DslError("is_missing() 的括号未闭合")
                self._next()
                return IsMissing(arg)
            raise DslError(
                f"位置 {tok.pos}：裸标识符 {word!r} 不是字段引用"
                "（字段引用必须含至少一个点，如 bs.total_assets）"
            )
        raise DslError(f"位置 {tok.pos}：无法解析的记号 {tok.value!r}")


def _collect_field_refs(node: Node) -> set[str]:
    if isinstance(node, FieldRef):
        return {node.path}
    if isinstance(node, Literal):
        return set()
    if isinstance(node, IsMissing):
        return {node.operand.path}
    if isinstance(node, Compare):
        return _collect_field_refs(node.left) | _collect_field_refs(node.right)
    if isinstance(node, Not):
        return _collect_field_refs(node.operand)
    if isinstance(node, (And, Or)):
        return _collect_field_refs(node.left) | _collect_field_refs(node.right)
    raise DslError(f"未知节点类型 {type(node).__name__}")


def parse_condition(text: str) -> Condition:
    """把一条条件字符串解析成受限语法树。不合白名单一律抛 DslError。"""
    if not isinstance(text, str) or not text.strip():
        raise DslError("条件字符串为空")
    tree = _Parser(_tokenize(text), text).parse()
    if not isinstance(tree, _BOOLEAN_ROOTS):
        raise DslError(
            "条件的根节点必须产出布尔值（比较 / is_missing / and / or / not），"
            "裸字段引用或字面量不是条件"
        )
    return Condition(source=text, tree=tree, field_refs=frozenset(_collect_field_refs(tree)))


# --------------------------------------------------------------------------
# 求值
# --------------------------------------------------------------------------


def normalize_row(row: dict, source_fields: list) -> dict:
    """按每个 source_field 声明的 missing_representation 把缺失编码统一成 MISSING。

    这是 R6 的落点：定义必须声明「缺失长什么样」，否则 0 与缺失无法区分。
    """
    out = dict(row)
    for sf in source_fields:
        fid = sf["id"] if isinstance(sf, dict) else sf.id
        has_repr = ("missing_representation" in sf) if isinstance(sf, dict) else True
        repr_val = (
            sf.get("missing_representation") if isinstance(sf, dict) else sf.missing_representation
        )
        if fid not in out:
            out[fid] = MISSING
        elif has_repr and out[fid] is not MISSING and out[fid] == repr_val and type(out[fid]) is type(repr_val):
            out[fid] = MISSING
        elif repr_val is None and out[fid] is None:
            out[fid] = MISSING
    return out


def _value_of(node: Node, row: dict) -> Any:
    if isinstance(node, Literal):
        return node.value
    if isinstance(node, FieldRef):
        return row.get(node.path, MISSING)
    raise DslError(f"{type(node).__name__} 不是取值节点")


def evaluate(condition: Condition | Node, row: dict) -> bool:
    """对给定行求值。比较遇缺失操作数抛 MissingOperandError，不静默变 False。"""
    node = condition.tree if isinstance(condition, Condition) else condition
    return _eval_node(node, row)


def _eval_node(node: Node, row: dict) -> bool:
    if isinstance(node, IsMissing):
        return row.get(node.operand.path, MISSING) is MISSING
    if isinstance(node, Compare):
        left = _value_of(node.left, row)
        right = _value_of(node.right, row)
        if left is MISSING or right is MISSING:
            missing_side = node.left if left is MISSING else node.right
            path = getattr(missing_side, "path", "<literal>")
            raise MissingOperandError(
                f"比较运算的操作数 {path} 缺失。"
                "请先用 is_missing() 判缺，或把该情形写进 undefined_conditions。"
            )
        return _compare(node.op, left, right)
    if isinstance(node, Not):
        return not _eval_node(node.operand, row)
    if isinstance(node, And):
        return _eval_node(node.left, row) and _eval_node(node.right, row)
    if isinstance(node, Or):
        return _eval_node(node.left, row) or _eval_node(node.right, row)
    raise DslError(f"{type(node).__name__} 不是布尔节点")


def _compare(op: str, left: Any, right: Any) -> bool:
    if op == "==":
        return left == right
    if op == "!=":
        return left != right
    if left is None or right is None:
        raise MissingOperandError(f"null 不支持序关系比较：{left!r} {op} {right!r}")
    if op == "<":
        return left < right
    if op == "<=":
        return left <= right
    if op == ">":
        return left > right
    if op == ">=":
        return left >= right
    raise DslError(f"不支持的比较运算符 {op!r}")
