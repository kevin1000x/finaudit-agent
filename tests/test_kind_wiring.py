"""三支 `kind` 接进 `pipeline` 批次产出（`N-43` 判据 3）的回归。

设计推导在 `docs/agent/phase-01.5/KIND-WIRING.md`。本文件锁的是那份文档的每一条结论
**在代码里真的成立**，而不是「文档写了」。

## 本文件**抓不到**什么

⚠️ 两条，不许把这些测试绿了读成「接线是对的」：

1. **抓不到「读数器判错了」。** 这里考的是**接线**：`kind` 有没有被分派到对的读法、
   三个口径类字段有没有按 `kind` 双向 fail-closed、派生值有没有被求值器看见。
   `read_scope_change` / `read_restatement_flag` **自己判得对不对**，
   由它们各自的用例与 `VERIFICATION.md` §D.17 的人工核对承担。
2. **抓不到跨排版稳健性。** `restated` 的规则仍是单样本
   （`VERIFICATION.md` §C.7：反例形态一次都没观察到，也没有去找）。
   **接线不会让那条限定变弱** —— 它只是把一个单样本结论传导到了更下游。
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from extractor.mapping import load_pdf_mapping
from extractor.pipeline import (
    DEFAULT_EXTRACTION_PLAN,
    ExtractionSource,
    _ROW_VALUED_KINDS,
    extract_records,
    read_statement,
    required_evidence_keys,
)
from extractor.reconcile import check_column_binding, reconcile_batch
from extractor.record import (
    BASIS_FIELDS_BY_KIND,
    BasisConfirmation,
    CellState,
    ExtractionRecord,
    ExtractionStatus,
    RecordKind,
    RetrievalOutcome,
    Selection,
    SourceFreshness,
    make_batch_id,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
PDF = REPO_ROOT / "data" / "raw" / "600519_2023.pdf"
SHA = "d" * 64

SELECTION = Selection(sampling="整表逐行", order_key="page,y", truncation="未截断")


def _note_record(**overrides) -> ExtractionRecord:
    """一条合法的 `NOTE_CHECKBOX` 记录：三个口径类字段全是 `None`。"""
    kwargs = dict(
        field_id="notes.consolidation_scope_change",
        kind=RecordKind.NOTE_CHECKBOX,
        value=True,
        status=ExtractionStatus.SUCCESS,
        retrieval=RetrievalOutcome.GOT_VALUE,
        basis_confirmation=BasisConfirmation.CONFIRMED,
        source_freshness=SourceFreshness.REUSED_CACHED,
        cell_state=CellState.VALUE_PRESENT,
        page=121,
        anchor_page=120,
        pdf_sha256=SHA,
        source_url="file://x.pdf",
        unit=None,
        currency=None,
        column_header=None,
        header_inherited=False,
        mapping_version=1,
        selection=SELECTION,
        truncation_stats={},
        batch_id=make_batch_id("600519", 2023, SHA),
    )
    kwargs.update(overrides)
    return ExtractionRecord(**kwargs)


# --------------------------------------------------------------------------
# §3.2 三个口径类字段按 kind 双向 fail-closed
# --------------------------------------------------------------------------


def test_复选框记录的三个口径类字段必须是None():
    """`KIND-WIRING.md` §2.1：复选框不在任何「列」里，布尔没有量纲也没有币种。"""
    record = _note_record()
    assert record.unit is None
    assert record.currency is None
    assert record.column_header is None


@pytest.mark.parametrize(
    "field, value",
    [("unit", "元"), ("currency", "人民币"), ("column_header", "期末余额")],
)
def test_给复选框字段填一个口径值就构造失败(field, value):
    """**这是本次改动最要紧的一条**：`F-2` 从「靠人记得」变成「构造边界拦住」。

    改之前 `unit="元"` 盖在一条复选框记录上是**能构造出来的** ——
    一个没有量纲的字段带着「元」，而没有任何东西会说出来。
    """
    with pytest.raises(ValueError, match="必须是 None"):
        _note_record(**{field: value})


def test_行值类反过来仍然不许留空():
    """双向的另一半。放开 `None` **不能**变成「行值类也可以不填」。"""
    with pytest.raises(ValueError, match="unit"):
        _note_record(
            field_id="bs.total_assets",
            kind=RecordKind.STATEMENT_LINE,
            value=Decimal("1.00"),
            unit=None,
            currency="人民币",
            column_header="2023年12月31日",
        )


def test_REPORT_METADATA_不能构造成抽取记录():
    """`KIND-WIRING.md` §2.3：纸上不印这一行，它进 `batch.derived` 不进 `records`。

    一个从未被抽取过的值放进「一次抽取的记录」，是**记录类型本身的范畴错误**，
    不是「它的某几个字段填不出来」。
    """
    assert RecordKind.REPORT_METADATA not in BASIS_FIELDS_BY_KIND
    with pytest.raises(ValueError, match="不该进 records"):
        _note_record(field_id="notes.reporting_period_months", kind=RecordKind.REPORT_METADATA)


def test_AC05_齐全率按kind取键而不是照行值类那张表数():
    """否则每条 note 记录平白记 3 处缺口，齐全率**永远不可能是 1**。

    那会让 `AC-05` 这条保证类标准变成一个正确的抽取器永远达不到的标准 ——
    与 `value` / `cell_state` 被排除在外是同一个理由。
    """
    row_keys = required_evidence_keys("STATEMENT_LINE")
    note_keys = required_evidence_keys("NOTE_CHECKBOX")
    for key in ("unit", "currency", "column_header"):
        assert key in row_keys
        assert key not in note_keys
    # 判存在性那一支：`column_header` 有内容（被判的那个列头），另两个没有。
    presence_keys = required_evidence_keys("COLUMN_HEADER_PRESENCE")
    assert "column_header" in presence_keys
    assert "unit" not in presence_keys


def test_认不出的kind按最严的键表查():
    """「认不出就少查」是一条自我豁免的规则 —— 一条 `kind` 写坏的记录反而少查三项。"""
    assert required_evidence_keys("不是任何一支 kind") == required_evidence_keys(
        "STATEMENT_LINE"
    )
    assert required_evidence_keys(None) == required_evidence_keys("STATEMENT_LINE")


# --------------------------------------------------------------------------
# 端到端：跑在真实年报上
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def real_batch():
    """整份年报跑一次默认计划。**没有本机语料时 skip，不是编一个批次糊弄过去。**"""
    if not PDF.exists():
        pytest.skip(f"本机语料不在：{PDF}（PDF 永不进版本控制）")
    import hashlib

    import pdfplumber

    digest = hashlib.sha256(PDF.read_bytes()).hexdigest()
    source = ExtractionSource(
        stock_code="600519",
        fiscal_year=2023,
        pdf_sha256=digest,
        source_url=f"file://{PDF.as_posix()}",
        freshness=SourceFreshness.REUSED_CACHED,
    )
    mappings = {ns: load_pdf_mapping(ns) for ns, _ in DEFAULT_EXTRACTION_PLAN}
    with pdfplumber.open(str(PDF), password="") as pdf:
        batch = None
        for ns, stmt in DEFAULT_EXTRACTION_PLAN:
            entries = mappings[ns].for_statement(stmt)
            needs_view = any(e.kind in _ROW_VALUED_KINDS for e in entries)
            view = read_statement(pdf, stmt, 2023) if needs_view else None
            batch = extract_records(view, mappings[ns], source, stmt, batch=batch, pdf=pdf)
    return batch


def test_两支kind在真实年报上产出记录且取值与人工核对一致(real_batch):
    """取值取自 `VERIFICATION.md` §D.17 的人工逐字核对，不是照抄抽取器自己的输出。"""
    got = {r.field_id: r for r in real_batch.records}

    # p121 子项 5「其他原因的合并范围变动」√适用（定制营销公司清算注销）
    assert got["notes.consolidation_scope_change"].value is True
    # p120 子项 1/2/3 各印 `□适用  √不适用` ⇒ 空集（D-028：空集即表示本期无企业合并）
    assert got["notes.business_combination_type"].value == ()
    # p5 表头三处印着 `调整后` / `调整前`，且同页注文明写「进行追溯调整」
    assert got["notes.restatement_flag"].value is True


def test_reporting_period_months_进derived不进records(real_batch):
    """`KIND-WIRING.md` §2.3。**不静默跳过**：在批次里看得见，但不冒充抽取。"""
    assert "notes.reporting_period_months" not in {r.field_id for r in real_batch.records}
    derived = {d["field"]: d for d in real_batch.derived}
    assert "notes.reporting_period_months" in derived
    item = derived["notes.reporting_period_months"]
    assert item["value"] == 12
    # 留证里必须看得出它不是从版面上取来的 —— 否则复核者会去年报上找这一行，而它不存在。
    assert item["derived"] is True
    assert item["extracted_from_layout"] is False


def test_接上之后flag真的置位而不是判不了(real_batch):
    """`N-43` 判据 3 的判据原文：「`restated` 真取到值之后 `unevaluable` 还剩几个」。

    ⚠️ 这里断言的是**接线的效果**，不是「`restated` 判得对」——
    后者由 §D.17 的人工核对承担，见模块 docstring「抓不到什么」第 1 条。
    """
    from semantic_layer.definition import iter_definition_paths, load_definition
    from semantic_layer.resolve import Refusal

    from extractor.formula import compute_metrics

    reconcile_batch(real_batch)
    metric_ids = sorted(
        load_definition(p).metric_id for p in iter_definition_paths(REPO_ROOT / "metrics")
    )
    outcomes = compute_metrics(metric_ids, real_batch, REPO_ROOT / "metrics")

    unevaluable = [
        o.metric_id
        for o in outcomes
        if not isinstance(o, Refusal) and o.flags_status == "unevaluable"
    ]
    assert unevaluable == [], f"仍有指标判不了可比性标记：{unevaluable}"

    flagged = {
        o.metric_id: o.flags
        for o in outcomes
        if not isinstance(o, Refusal) and o.flags
    }
    # 一个都没置位的话上面那条也会绿 —— 那时它证明的是「没有 flag」不是「flag 能置位」。
    assert flagged, "一个 flag 都没有置位，上面那条断言因此没有辨析力"
    assert "restated" in flagged["debt_to_asset_ratio"]
    # `A-8` 那处真实假阴性的端到端确认：茅台 2023 企业合并三项全不适用，
    # 而「其他原因的合并范围变动」适用 ⇒ scope_change 必须置位。
    assert "scope_change" in flagged["minority_interest_share"]


def test_派生值不并进求值行时那条flag会判不了(real_batch):
    """负控制：证明上面那条 `unevaluable == []` 不是白给的。

    `period_length_mismatch` 的 trigger 是 `notes.reporting_period_months != 12`，
    而那个值只在 `batch.derived` 里。不并进求值行 ⇒ 操作数缺失 ⇒ 整条指标 `unevaluable`。
    """
    import dataclasses

    from semantic_layer.definition import load_definition
    from semantic_layer.resolve import Refusal

    from extractor.formula import compute_metric

    stripped = dataclasses.replace(real_batch, derived=[])
    stripped.records = real_batch.records
    stripped.reconciliation = real_batch.reconciliation
    stripped.sealed = real_batch.sealed

    outcome = compute_metric("operating_cash_flow_ratio", stripped, REPO_ROOT / "metrics")
    assert not isinstance(outcome, Refusal)
    assert outcome.flags_status == "unevaluable"
    assert "notes.reporting_period_months" in outcome.flags_note
    # 对照：带着 derived 的同一个批次是能求值的。
    ok = compute_metric("operating_cash_flow_ratio", real_batch, REPO_ROOT / "metrics")
    assert ok.flags_status == "evaluated"
    assert load_definition  # 引用一下，避免未使用告警掩盖真实的 import 错误


def test_列绑定闸门不对判存在性那一支报假不符(real_batch):
    """接线当天炸出来的假阳性，钉住。

    `notes.restatement_flag` 的 `column_header` 是 `调整后` —— **被判存在性的那个列头**，
    不是取数列。拿 `role_of` 去解它必然解出 `None` 并报一条**假的**不符
    （版面串与要的口径逐字相同却判不符，这本身就是判据用错了对象的信号）。
    """
    result = check_column_binding(real_batch, load_pdf_mapping("notes"), 2023)
    assert result.mismatches == (), f"报了假的列绑定不符：{result.mismatches}"
    # **不是静默跳过**：逐条记进 not_applicable 并给出理由（复核 RV-3 的形状）。
    skipped = {f for f, _ in result.not_applicable}
    assert "notes.restatement_flag" in skipped
    assert result.checked == 0
    assert "not_applicable" in result.to_dict()


def test_三大表那一路的记录数没有因为接线而变化(real_batch):
    """接线**只增不改**：三大表 25 条一条不少，新增的是 notes 那 3 条。"""
    by_ns = {}
    for record in real_batch.records:
        by_ns.setdefault(record.field_id.split(".", 1)[0], 0)
        by_ns[record.field_id.split(".", 1)[0]] += 1
    assert by_ns["bs"] == 15
    assert by_ns["is"] == 8
    assert by_ns["cfs"] == 2
    assert by_ns["notes"] == 3
    assert len(real_batch.records) == 28


def test_记录的证据链能被序列化并保持齐全(real_batch):
    """接线之后 `AC-05` 的齐全率不许被 note 记录拉下来。"""
    from extractor.pipeline import completeness_report

    report = completeness_report(real_batch)
    assert report.rate == 1, f"接线之后齐全率掉了：{report.gaps}"
    assert report.meets_ac05()
    # 证据链要能出得去 —— note 记录的 value 是 bool / tuple，别在这里炸。
    blob = json.dumps([r.to_dict() for r in real_batch.records], ensure_ascii=False)
    assert "notes.restatement_flag" in blob
