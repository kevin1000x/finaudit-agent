"""封闭算术解析器的回归 —— D-017 三条硬约束逐条有断言。

最重要的一条是**一致性测试**（D-017 判据 3）：`dsl` 与 `formula` 各有一套约 30–40 行
的字段引用词法逻辑，那份重复只有这条测试拦得住漂移。
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

import semantic_layer.dsl as dsl
from extractor.formula import (
    NODE_TYPES,
    ArithmeticError,
    BinOp,
    ComputeResult,
    Num,
    Ref,
    UnaryOp,
    compute_metric,
    evaluate_formula,
    field_refs,
    parse_formula,
)
from extractor.mapping import load_pdf_mapping
from extractor.pipeline import ExtractionSource, StatementView, extract_records
from extractor.reconcile import reconcile_batch
from extractor.record import (
    BasisConfirmation,
    CellState,
    ExtractionBatch,
    ExtractionRecord,
    ExtractionStatus,
    RecordKind,
    RetrievalOutcome,
    Selection,
    SourceFreshness,
    make_batch_id,
)
from semantic_layer.resolve import Refusal, RefusalCode

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = Path(__file__).parent / "fixtures" / "maotai_2023_bs_rows.json"
REAL_MAPPING_DIR = REPO_ROOT / "data" / "mappings" / "pdf"
METRICS_DIR = REPO_ROOT / "metrics"
FORMULA_SOURCE = (REPO_ROOT / "src" / "extractor" / "formula.py").read_text(encoding="utf-8")
#: 去掉整行注释后的源码。注释里当然会出现 `getattr` / `eval` 这些词 ——
#: 那正是在解释「为什么这里没有它们」。拿注释当证据会把说明文字读成实现。
FORMULA_CODE = "\n".join(
    line for line in FORMULA_SOURCE.splitlines() if not line.lstrip().startswith("#")
)

SELECTION = Selection(sampling="整表逐行", order_key="page,y", truncation="未截断")


@pytest.fixture(scope="module")
def raw() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def gated_batch(raw) -> ExtractionBatch:
    """真实抽取 + 过闸门的批次。计算层的唯一合法输入形态。"""
    view = StatementView.from_dict(raw)
    mapping = load_pdf_mapping("bs", REAL_MAPPING_DIR)
    batch = extract_records(
        view,
        mapping,
        ExtractionSource(
            stock_code=raw["source"]["stock_code"],
            fiscal_year=raw["source"]["fiscal_year"],
            pdf_sha256=raw["source"]["pdf_sha256"],
            source_url="https://static.cninfo.com.cn/finalpage/2024-04-03/1219506510.PDF",
            freshness=SourceFreshness.REUSED_CACHED,
        ),
    )
    reconcile_batch(batch)
    return batch


def _batch_with(field_id: str, **overrides) -> ExtractionBatch:
    sha = "e" * 64
    batch = ExtractionBatch.open("999999", 2023, sha)
    kwargs = dict(
        field_id=field_id,
        kind=RecordKind.STATEMENT_LINE,
        value=Decimal("1.00"),
        status=ExtractionStatus.SUCCESS,
        retrieval=RetrievalOutcome.GOT_VALUE,
        basis_confirmation=BasisConfirmation.CONFIRMED,
        source_freshness=SourceFreshness.UNKNOWN,
        cell_state=CellState.VALUE_PRESENT,
        page=59,
        anchor_page=58,
        pdf_sha256=sha,
        source_url="https://static.cninfo.com.cn/finalpage/x.PDF",
        unit="元",
        currency="人民币",
        column_header="2023年12月31日",
        mapping_version=1,
        selection=SELECTION,
        truncation_stats={},
        batch_id=make_batch_id("999999", 2023, sha),
    )
    kwargs.update(overrides)
    batch.add_record(ExtractionRecord(**kwargs))
    return batch


# --------------------------------------------------------------------------
# D-017 判据 3：两个词法器不许漂移
# --------------------------------------------------------------------------

#: 语料只放**字段引用字符串**，不放含算术的表达式。
#: 理由是两个词法器的语法边界本来就不同：`dsl` 不认四则运算符（`+` 在它眼里是
#: 「算术运算与其他符号不在白名单内」），`formula` 不认比较与逻辑。
#: 判据 3 要拦的漂移只发生在**两者重叠的那部分**——字段引用的词法逻辑，
#: 那约 30–40 行重复的代码。把不重叠的部分塞进语料，测的就不是漂移了。
CONSISTENCY_CORPUS = [
    "bs.total_assets",
    "is.net_profit_attributable_to_parent",
    "cfs.net_cash_from_operating",
    "notes.restatement_flag",
    "kpi.roe_weighted_average",
    "notes.a.b.c",
    "bs.a1_b2.c_3",
    "  bs.total_liabilities  ",
    "(bs.total_equity)",
    "((kpi.x))",
]


def _dsl_field_sequence(text: str) -> list[str]:
    return [t.value for t in dsl._tokenize(text) if t.kind == "FIELD"]


def _formula_field_sequence(text: str) -> list[str]:
    from extractor.formula import _tokenize

    return [t.value for t in _tokenize(text) if t.kind == "FIELD"]


@pytest.mark.parametrize("text", CONSISTENCY_CORPUS)
def test_两个词法器对同一组字段引用给出相同序列(text):
    """D-017 判据 3。

    `is.` 前缀那条是重点：它与 Python 关键字 `is` 冲突，
    `is.net_profit_attributable_to_parent` 在 Python 语法下直接是 SyntaxError。
    两个自研词法器都必须把它当成一个普通字段引用，且结果一致。
    """
    assert _formula_field_sequence(text) == _dsl_field_sequence(text)


def test_一致性测试的语料确实覆盖五个根命名空间():
    """负控制（J-5）：语料不覆盖就等于这条一致性测试在空转。"""
    roots = {ref.split(".", 1)[0] for text in CONSISTENCY_CORPUS for ref in _formula_field_sequence(text)}
    assert roots == set(dsl.ROOT_NAMESPACES)


def test_前缀集是只读导入而不是各写一份():
    """两处各写一份必然漂移，表现是同一个字段在条件里合法、在公式里非法。"""
    assert "ROOT_NAMESPACES" in FORMULA_SOURCE
    assert "frozenset({\"is\"" not in FORMULA_SOURCE


# --------------------------------------------------------------------------
# 语法边界：不含比较、不含逻辑、不含函数调用
# --------------------------------------------------------------------------


def test_四则运算与括号与一元负号在语法内():
    assert parse_formula("bs.total_liabilities / bs.total_assets") == BinOp(
        "/", Ref("bs.total_liabilities"), Ref("bs.total_assets")
    )
    assert parse_formula("-bs.total_assets") == UnaryOp("-", Ref("bs.total_assets"))
    assert parse_formula("(1 + 2) * 3") == BinOp(
        "*", BinOp("+", Num(Decimal("1")), Num(Decimal("2"))), Num(Decimal("3"))
    )


@pytest.mark.parametrize(
    "text",
    [
        "bs.total_assets > 0",
        "bs.total_assets >= 0",
        "bs.total_assets == 0",
        "bs.total_assets != 0",
        "bs.total_assets < bs.total_liabilities",
    ],
)
def test_比较运算符不在语法内(text):
    """比较属 `semantic_layer.dsl`。两者共用一套语法，MUST NOT 各自扩展。"""
    with pytest.raises(ArithmeticError):
        parse_formula(text)


@pytest.mark.parametrize(
    "text",
    [
        '__import__("os")',
        "__import__",
        "open('x')",
        "is_missing(bs.total_assets)",
        "bs.total_assets and bs.total_liabilities",
        "not bs.total_assets",
        "'os'",
        "bs.total_assets; import os",
    ],
)
def test_通往求值的入口一个都不留(text):
    """L-33：排除求值**不只是不调用它，而是不留任何能到达求值的入口**。

    本模块没有函数调用、没有字符串字面量、没有裸标识符。
    `__import__` 走「裸标识符」那条分支被拒，`"os"` 走「非法字符」那条被拒 ——
    两条路都堵着，不是靠黑名单挡住 `__import__` 这个名字。
    """
    with pytest.raises(ArithmeticError):
        parse_formula(text)


def test_双下划线路径解析成一个惰性字符串而不是属性访问():
    """`bs.total_assets.__class__` **不报错**，如实说明为什么这不构成逃逸。

    它的根命名空间是 `bs`，合法，所以解析成 `Ref("bs.total_assets.__class__")`。
    但 `Ref.path` 只被拿去 `batch.by_field(path)` 做一次字符串比对 ——
    全模块没有一处 `getattr`、没有一处属性访问，这个 dunder 到不了任何求值。
    求值结果是「批次里没有这个字段」的拒答。

    把它写成「会被拒绝」是好听但不真的说法；写成这样才是它的实际行为。
    """
    tree = parse_formula("bs.total_assets.__class__")
    assert isinstance(tree, Ref)
    assert isinstance(tree.path, str)
    assert "getattr" not in FORMULA_CODE
    batch = _batch_with("bs.total_assets")
    outcome = evaluate_formula(tree, batch)
    assert isinstance(outcome, Refusal)
    assert outcome.code is RefusalCode.UNAVAILABLE


def test_根命名空间之外的字段引用被拒():
    with pytest.raises(ArithmeticError, match="根命名空间"):
        parse_formula("os.path / bs.total_assets")


def test_括号未闭合与表达式残留都被拒():
    with pytest.raises(ArithmeticError):
        parse_formula("(bs.total_assets")
    with pytest.raises(ArithmeticError):
        parse_formula("bs.total_assets bs.total_liabilities")
    with pytest.raises(ArithmeticError):
        parse_formula("")


# --------------------------------------------------------------------------
# 封闭节点集与硬性排除
# --------------------------------------------------------------------------


def test_解析产物只含四种节点():
    """Phase 2 的 pre_execute 要静态检查的就是这四个。"""

    def walk(node):
        yield node
        for child in ("left", "right", "operand"):
            if hasattr(node, child):
                yield from walk(getattr(node, child))

    tree = parse_formula("(bs.total_assets - -1.5) / (is.revenue * 2)")
    kinds = {type(n) for n in walk(tree)}
    assert kinds <= set(NODE_TYPES)
    assert kinds == {BinOp, UnaryOp, Ref, Num} or Num in kinds


def test_源码里没有内建求值函数也没有语法树标准库():
    """D-017 明写这两条是硬性排除，不是选项讨论。

    连同上面的语法测试一起看：语法测试证明「没有入口」，
    这一条证明「也没有出口」——两头都堵上才叫封闭。
    """
    stripped = "\n".join(
        line for line in FORMULA_SOURCE.splitlines() if not line.lstrip().startswith("#")
    )
    assert "eval(" not in stripped
    assert "exec(" not in stripped
    assert "compile(" not in stripped
    assert "import ast" not in stripped
    assert "__import__" not in stripped


def test_数值一律十进制不用二进制浮点():
    tree = parse_formula("0.1 + 0.2")
    assert isinstance(tree.left.value, Decimal)
    batch = _batch_with("bs.total_assets")
    assert evaluate_formula(tree, batch) == Decimal("0.3")


# --------------------------------------------------------------------------
# 缺失语义：SC-3 的两侧
# --------------------------------------------------------------------------


def test_整行不存在的字段参与运算即拒答():
    """不静默当 0。当 0 会让「这张表没有这一行」被算成「这一项是零」。"""
    batch = _batch_with(
        "bs.total_assets",
        value=None,
        retrieval=RetrievalOutcome.ABSENT,
        cell_state=CellState.ROW_ABSENT,
    )
    outcome = evaluate_formula(parse_formula("bs.total_assets * 2"), batch)
    assert isinstance(outcome, Refusal)
    assert outcome.code is RefusalCode.UNEVALUABLE_CONDITION
    assert outcome.source


def test_行在格子空的字段按零参与运算():
    """A-2 的处置：茅台四个有息负债分项行在格子空，正确答案是 0 不是缺失。"""
    batch = _batch_with(
        "bs.total_assets",
        value=Decimal(0),
        retrieval=RetrievalOutcome.GOT_VALUE,
        cell_state=CellState.EMPTY_CELL,
    )
    assert evaluate_formula(parse_formula("bs.total_assets + 5"), batch) == Decimal("5")


def test_试过但判不出的字段参与运算即拒答():
    batch = _batch_with(
        "bs.total_assets",
        value=None,
        retrieval=RetrievalOutcome.ATTEMPTED_UNKNOWN,
        cell_state=None,
    )
    outcome = evaluate_formula(parse_formula("bs.total_assets"), batch)
    assert isinstance(outcome, Refusal)
    assert "判不出" in outcome.detail


def test_批次里没有的字段拒答而不是当零():
    batch = _batch_with("bs.total_assets")
    outcome = evaluate_formula(parse_formula("bs.total_liabilities"), batch)
    assert isinstance(outcome, Refusal)
    assert outcome.code is RefusalCode.UNAVAILABLE


def test_除数为零拒答而不是抛出内建异常():
    """本模块的 `ArithmeticError` 遮蔽了内建同名类，除零必须显式接住。"""
    batch = _batch_with("bs.total_assets", value=Decimal(0))
    outcome = evaluate_formula(parse_formula("1 / bs.total_assets"), batch)
    assert isinstance(outcome, Refusal)
    assert "除数为零" in outcome.detail


# --------------------------------------------------------------------------
# 端到端：算出第一个真实数值
# --------------------------------------------------------------------------


def test_茅台2023的资产负债率算得出真实数值(gated_batch):
    """人工核对：49,043,190,797.43 / 272,699,660,092.25 = 0.1798…（四位小数 0.1798）"""
    outcome = compute_metric("debt_to_asset_ratio", gated_batch, METRICS_DIR)
    assert isinstance(outcome, ComputeResult)
    assert outcome.value.quantize(Decimal("0.0001")) == Decimal("0.1798")
    assert outcome.formula == "bs.total_liabilities / bs.total_assets"
    assert outcome.definition_version == 2
    assert outcome.batch_id == gated_batch.batch_id


def test_算出来的值可由证据链里的记录独立复算(gated_batch):
    """SC「该数值可由证据链里的三条记录独立复算」的机械形态。"""
    outcome = compute_metric("debt_to_asset_ratio", gated_batch, METRICS_DIR)
    liabilities = gated_batch.by_field("bs.total_liabilities").value
    assets = gated_batch.by_field("bs.total_assets").value
    assert liabilities / assets == outcome.value


def test_派生值带着输入字段的指针且标了derived(gated_batch):
    """L-54：派生指标必须标 `derived` 并携带其输入字段的指针。"""
    outcome = compute_metric("debt_to_asset_ratio", gated_batch, METRICS_DIR)
    assert outcome.derived is True
    assert outcome.inputs == ("bs.total_liabilities", "bs.total_assets")
    assert all(gated_batch.by_field(f) is not None for f in outcome.inputs)


def test_比率的单位如实写成无量纲而不是照抄元(gated_batch):
    """照抄输入的「元」会让证据链声称一个比率的单位是元。"""
    outcome = compute_metric("debt_to_asset_ratio", gated_batch, METRICS_DIR)
    assert outcome.unit == "无量纲"
    assert outcome.currency == "不适用"


def test_未定义的指标名拒答(gated_batch):
    outcome = compute_metric("不存在的指标", gated_batch, METRICS_DIR)
    assert isinstance(outcome, Refusal)
    assert outcome.code is RefusalCode.METRIC_NOT_DEFINED


def test_field_refs_按出现顺序且可重复():
    assert field_refs(parse_formula("bs.a + bs.b - bs.a")) == ("bs.a", "bs.b", "bs.a")
