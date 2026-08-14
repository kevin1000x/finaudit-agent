"""受限布尔 DSL 的解析与求值。

最重要的一条是 test_parses_is_prefixed_field —— 它单独证明自研解析器存在的理由：
`is.` 前缀在 Python 语法下是 SyntaxError，Python 的语法树模块解不了。
"""

import pytest

from semantic_layer import dsl
from semantic_layer.dsl import DslError, MissingOperandError, evaluate, parse_condition


# --------------------------------------------------------------------------
# 解析：合法构造
# --------------------------------------------------------------------------


def test_parses_is_prefixed_field():
    """`is` 是 Python 关键字，`is.xxx` 在 Python 语法下无法解析。自研解析器可以。"""
    cond = parse_condition("is.net_profit_attributable_to_parent > 0")
    assert cond.field_refs == frozenset({"is.net_profit_attributable_to_parent"})
    assert isinstance(cond.tree, dsl.Compare)


def test_python_ast_cannot_parse_is_prefix():
    """把「Python 解不了」这件事本身固化成回归测试，防止有人日后退回用 ast。"""
    import ast

    with pytest.raises(SyntaxError):
        ast.parse("is.net_profit_attributable_to_parent > 0", mode="eval")


def test_parses_boolean_literal():
    cond = parse_condition("notes.restatement_flag == true")
    assert isinstance(cond.tree, dsl.Compare)
    assert cond.tree.right == dsl.Literal(True)


def test_parses_or_with_is_missing():
    cond = parse_condition("is_missing(notes.x) or notes.y <= 0")
    assert isinstance(cond.tree, dsl.Or)
    assert cond.field_refs == frozenset({"notes.x", "notes.y"})


def test_parses_intrinsic_namespace_comparison():
    cond = parse_condition(
        "standard_basis.version != comparison_period.standard_basis.version"
    )
    assert isinstance(cond.tree, dsl.Compare)
    assert "comparison_period.standard_basis.version" in cond.field_refs


def test_parses_parenthesised_and_not():
    cond = parse_condition("not (bs.total_assets > 0 and is_missing(notes.x))")
    assert isinstance(cond.tree, dsl.Not)


# --------------------------------------------------------------------------
# 解析：越界构造一律拒绝
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "expr, why",
    [
        ("open('/etc/passwd')", "函数名不在谓词白名单"),
        ("__import__('os')", "函数名不在谓词白名单"),
        ("bs.total_assets + 1 > 0", "无算术运算"),
        ("x = 1", "无赋值"),
        ("total_assets > 0", "裸标识符不是字段引用"),
        ("foo.bar > 0", "根命名空间不在白名单"),
        ("is_missing(1)", "is_missing 的参数必须是字段引用"),
        ("bs.total_assets", "根节点必须产出布尔值"),
        ("", "空条件"),
    ],
)
def test_rejects_out_of_bounds(expr, why):
    with pytest.raises(DslError):
        parse_condition(expr)


# --------------------------------------------------------------------------
# 求值：fail-closed 与 R6（缺失 ≠ 零）
# --------------------------------------------------------------------------


def test_absent_key_is_missing():
    assert evaluate(parse_condition("is_missing(notes.x)"), {}) is True


def test_zero_is_not_missing():
    """R6 的核心：取值为零与缺失走不同分支，二者后果相反。"""
    row = {"notes.x": 0}
    assert evaluate(parse_condition("is_missing(notes.x)"), row) is False
    assert evaluate(parse_condition("notes.x == 0"), row) is True


def test_comparison_on_missing_raises():
    """fail-closed：缺失操作数不静默变 False。"""
    with pytest.raises(MissingOperandError):
        evaluate(parse_condition("notes.x <= 0"), {})


def test_or_short_circuits_before_missing_operand():
    """左侧为真时不触及右侧的缺失操作数。"""
    assert evaluate(parse_condition("is_missing(notes.x) or notes.x <= 0"), {}) is True


def test_and_short_circuits_on_false():
    row = {"bs.total_assets": 0}
    assert evaluate(parse_condition("bs.total_assets > 0 and notes.x == 1"), row) is False


def test_normalize_row_maps_declared_missing_encoding():
    source_fields = [{"id": "notes.x", "missing_representation": None}]
    row = dsl.normalize_row({"notes.x": None}, source_fields)
    assert row["notes.x"] is dsl.MISSING
    assert evaluate(parse_condition("is_missing(notes.x)"), row) is True
