"""批次级勾稽闸门的回归 —— D-018 / A-9 / L-13。

一条真实数据驱动的通过用例、一条构造的失败用例、一条负控制（J-5）说明
**这道闸门证明不了什么**，以及计算层在读入边界的 fail-closed。
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from extractor.formula import compute_metric
from extractor.mapping import load_pdf_mapping
from extractor.pipeline import ExtractionSource, StatementView, extract_records
from extractor.reconcile import (
    BALANCE_SHEET_IDENTITY,
    DEFAULT_TOLERANCE,
    ReconcileResult,
    reconcile_batch,
)
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

SELECTION = Selection(sampling="整表逐行", order_key="page,y", truncation="未截断")


@pytest.fixture(scope="module")
def raw() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _source(raw: dict) -> ExtractionSource:
    return ExtractionSource(
        stock_code=raw["source"]["stock_code"],
        fiscal_year=raw["source"]["fiscal_year"],
        pdf_sha256=raw["source"]["pdf_sha256"],
        source_url="https://static.cninfo.com.cn/finalpage/2024-04-03/1219506510.PDF",
        freshness=SourceFreshness.REUSED_CACHED,
    )


def _real_batch(raw: dict) -> ExtractionBatch:
    """从固件重跑一次真实抽取。**不是手填的数**，是从版面里取出来的。"""
    view = StatementView.from_dict(raw)
    mapping = load_pdf_mapping("bs", REAL_MAPPING_DIR)
    return extract_records(view, mapping, _source(raw))


def _synthetic_batch(values: dict[str, str], **record_overrides) -> ExtractionBatch:
    """按给定数值造一个批次。构造用例专用。"""
    sha = "c" * 64
    batch = ExtractionBatch.open("999999", 2023, sha)
    for field_id, amount in values.items():
        batch.add_record(
            ExtractionRecord(
                field_id=field_id,
                kind=RecordKind.STATEMENT_LINE,
                value=Decimal(amount),
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
                header_inherited=False,
                mapping_version=1,
                selection=SELECTION,
                truncation_stats={},
                batch_id=make_batch_id("999999", 2023, sha),
                **record_overrides,
            )
        )
    return batch


# --------------------------------------------------------------------------
# 真实数据：通过
# --------------------------------------------------------------------------


def test_茅台2023真实批次的恒等式差额为零(raw):
    """CONTEXT §3.1 实测：资产总计 = 负债合计 + 所有者权益合计，差额 0.00。

    272,699,660,092.25 = 49,043,190,797.43 + 223,656,469,294.82
    """
    result = reconcile_batch(_real_batch(raw))
    assert result.passed is True
    assert result.identity == BALANCE_SHEET_IDENTITY
    assert abs(result.difference) <= DEFAULT_TOLERANCE
    assert result.difference == Decimal("0.00")
    assert result.left == Decimal("272699660092.25")
    assert result.missing_fields == ()


def test_判定完就闩死批次(raw):
    """L-13：重试不得跨闸门批次。闩死之后追加记录一律拒绝。"""
    batch = _real_batch(raw)
    assert batch.sealed is False
    reconcile_batch(batch)
    assert batch.sealed is True
    extra = batch.records[0]
    with pytest.raises(ValueError, match="已闩死"):
        batch.add_record(extra)


# --------------------------------------------------------------------------
# 构造数据：拦住
# --------------------------------------------------------------------------


def test_负债合计人为加一元后闸门拦住():
    """一分钱以上的差额就拦。容差是一分，不是一元。"""
    batch = _synthetic_batch(
        {
            "bs.total_assets": "272699660092.25",
            "bs.total_liabilities": "49043190798.43",  # 真实值 + 1.00
            "bs.total_equity": "223656469294.82",
        }
    )
    result = reconcile_batch(batch)
    assert result.passed is False
    assert abs(result.difference) == Decimal("1.00")
    # 符号约定：`difference = left - right`，负号说明右边（负债 + 权益）大。
    # 这不是可有可无的细节 —— 差额的方向能告诉复核者是哪一侧被高估了。
    assert result.difference == Decimal("-1.00")


def test_差额恰好一分仍算通过而一分零一厘不算():
    base = {
        "bs.total_assets": "100.00",
        "bs.total_equity": "50.00",
    }
    assert reconcile_batch(
        _synthetic_batch({**base, "bs.total_liabilities": "49.99"})
    ).passed is True
    assert reconcile_batch(
        _synthetic_batch({**base, "bs.total_liabilities": "49.98"})
    ).passed is False


def test_缺一项时不拿零凑数():
    """三项缺一就算不出 left / right。填个 0 等于把「取不到数」伪装成「差额为零」。"""
    result = reconcile_batch(
        _synthetic_batch(
            {"bs.total_assets": "100.00", "bs.total_liabilities": "50.00"}
        )
    )
    assert result.passed is False
    assert result.missing_fields == ("bs.total_equity",)
    assert result.left is None and result.right is None and result.difference is None


def test_整行不存在的字段不当零参与恒等式():
    """`ROW_ABSENT` 取不到；`EMPTY_CELL` 按 0 —— 两者是 SC-3 要区分的那条线。"""
    sha = "d" * 64
    batch = ExtractionBatch.open("999999", 2023, sha)
    common = dict(
        kind=RecordKind.STATEMENT_LINE,
        status=ExtractionStatus.SUCCESS,
        basis_confirmation=BasisConfirmation.CONFIRMED,
        source_freshness=SourceFreshness.UNKNOWN,
        page=59,
        anchor_page=58,
        pdf_sha256=sha,
        source_url="https://static.cninfo.com.cn/finalpage/x.PDF",
        unit="元",
        currency="人民币",
        column_header="2023年12月31日",
        header_inherited=False,
        mapping_version=1,
        selection=SELECTION,
        truncation_stats={},
        batch_id=make_batch_id("999999", 2023, sha),
    )
    batch.add_record(
        ExtractionRecord(
            field_id="bs.total_assets",
            value=Decimal("100.00"),
            retrieval=RetrievalOutcome.GOT_VALUE,
            cell_state=CellState.VALUE_PRESENT,
            **common,
        )
    )
    batch.add_record(
        ExtractionRecord(
            field_id="bs.total_liabilities",
            value=Decimal(0),
            retrieval=RetrievalOutcome.GOT_VALUE,
            cell_state=CellState.EMPTY_CELL,
            **common,
        )
    )
    batch.add_record(
        ExtractionRecord(
            field_id="bs.total_equity",
            value=None,
            retrieval=RetrievalOutcome.ABSENT,
            cell_state=CellState.ROW_ABSENT,
            **common,
        )
    )
    result = reconcile_batch(batch)
    assert result.missing_fields == ("bs.total_equity",), "ROW_ABSENT 必须算取不到"
    assert result.passed is False


# --------------------------------------------------------------------------
# 负控制（J-5）：这道闸门**证明不了**取的是对的那一列
# --------------------------------------------------------------------------


def test_三个数全取自期初列时闸门照样放行():
    """台账 A-9：自证机制说通过了，但它证明的不是它声称证明的事。

    茅台 2023 的**期初列**（2022年12月31日）三个数同样满足恒等式：
    254,500,826,096.02 = 49,562,744,832.16 + 204,938,081,263.86

    所以「勾稽通过」推不出「取的是期末列」。列的正确性只能靠
    `column_header` 的显式绑定来保证 —— 这条负控制就是那句话的机械形态，
    也是「单独跑勾稽闸门不足以让列绑定的验收通过」的证据。
    """
    batch = _synthetic_batch(
        {
            "bs.total_assets": "254500826096.02",
            "bs.total_liabilities": "49562744832.16",
            "bs.total_equity": "204938081263.86",
        },
        # 记录如实声明它取的是期初列 —— 闸门看不见这个字段，这正是问题所在。
    )
    result = reconcile_batch(batch)
    assert result.passed is True, "期初列自己也是自洽的，闸门必然放行"
    assert all(r.column_header == "2023年12月31日" for r in batch.records), (
        "本用例故意让 column_header 与实际取的列不一致；"
        "闸门通过而列绑定说谎，两者都不报错 —— 这就是 A-9"
    )


# --------------------------------------------------------------------------
# 计算层在读入边界 fail-closed（D-018 / ARCHITECTURE §8.4）
# --------------------------------------------------------------------------


def test_闸门未通过时计算层拒答且不产出数值():
    batch = _synthetic_batch(
        {
            "bs.total_assets": "272699660092.25",
            "bs.total_liabilities": "49043190798.43",
            "bs.total_equity": "223656469294.82",
        }
    )
    gate = reconcile_batch(batch)
    assert gate.passed is False
    outcome = compute_metric("debt_to_asset_ratio", batch, METRICS_DIR)
    assert isinstance(outcome, Refusal)
    assert not hasattr(outcome, "value"), "拒答对象不得带数值属性"
    assert isinstance(outcome.code, RefusalCode), "理由码必须是枚举成员而不是自由文本"
    assert not isinstance(outcome.code, str)
    assert outcome.code is RefusalCode.RECONCILIATION_FAILED
    assert outcome.source


def test_压根没跑过闸门也拒答():
    """没跑过 ≠ 通过。fail-closed 在读入侧，所有消费者都必须过这道门。"""
    batch = _synthetic_batch(
        {
            "bs.total_assets": "272699660092.25",
            "bs.total_liabilities": "49043190797.43",
            "bs.total_equity": "223656469294.82",
        }
    )
    assert batch.reconciliation is None
    outcome = compute_metric("debt_to_asset_ratio", batch, METRICS_DIR)
    assert isinstance(outcome, Refusal)
    assert outcome.code is RefusalCode.RECONCILIATION_FAILED
    assert outcome.source == "reconcile:not_run"


def test_闸门结果写进批次元数据而不嵌进指标的计算路径(raw):
    """D-018：勾稽是报表的性质，不是某个指标的性质。跑一次，写批次上。"""
    batch = _real_batch(raw)
    reconcile_batch(batch)
    assert isinstance(batch.reconciliation, ReconcileResult)
    import inspect

    import extractor.formula as formula_module

    source = inspect.getsource(formula_module)
    assert "reconcile_batch" not in source, (
        "计算层不得自己跑闸门 —— 那会对同一批数据重复跑 N 次且失败时归因混乱（D-018）"
    )
