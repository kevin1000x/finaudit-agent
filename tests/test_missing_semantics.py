"""「行在但格子空 = 0」与「整行不存在 = 缺失」（SC-3 / 台账 A-2）。

## 这两件事被混成一个「缺失」的代价，有实测

茅台 2023 的合并资产负债表上，**四个有息负债分项的行项目印在报表上，
而值的格子是空的**（短期借款 / 交易性金融负债 / 长期借款 / 应付债券）。
按 `is_missing` 一律拒答的话，有息负债率会对一家**实际几乎没有有息负债**的公司拒答，
而正确答案是可算的 —— 本模块实跑得 `0.0011869876`。

## 修的是抽取层，`metrics/` 一个字都不动

`metrics/interest_bearing_debt_ratio.yaml` 的 `undefined_conditions` 保持原样。
格子空时抽取层给出的是一个**有值的 0**，不是缺失哨兵，于是 `is_missing(...)`
自然为假，定义里那条拒答条件不触发。这就是 `A-2` 判据原话
「抽取层区分两者，定义侧不改」。

## `ROW_ABSENT` 只能靠构造，这一点必须写明

茅台 2023 的实测事实是**整行不存在的字段 0 个**（`CONTEXT` §3.3）。
所以反向那一半没有真实样本，只能从固件里把某一行删掉来造。
⚠️ 造的时候**保留 `all_label_sequences` 里的那条标签** —— 否则触发的是
`L-36` 的「整份 PDF 零命中 = 规则写错了」，那是另一件事：

- `ROW_ABSENT`：**这张表**确实没印这一行（别处印了）
- `L-36` 零命中：这条规则在**整份 PDF** 上一次都没匹配上 ⇒ 只可能是规则写错了

混为一谈会把 SC-3 要区分的「整行不存在」变成一次崩溃。
"""

from __future__ import annotations

import dataclasses
import json
from decimal import Decimal
from pathlib import Path

import pytest

from extractor.formula import compute_metric
from extractor.mapping import load_pdf_mapping
from extractor.pipeline import ExtractionSource, StatementView, extract_records
from extractor.reconcile import reconcile_batch
from extractor.record import CellState, ExtractionStatus, SourceFreshness
from semantic_layer.resolve import Refusal

FIXTURE = Path(__file__).parent / "fixtures" / "maotai_2023_bs_rows.json"


@pytest.fixture
def view() -> StatementView:
    return StatementView.from_dict(json.loads(FIXTURE.read_text(encoding="utf-8")))


@pytest.fixture
def source() -> ExtractionSource:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))["source"]
    return ExtractionSource(
        stock_code=data["stock_code"],
        fiscal_year=data["fiscal_year"],
        pdf_sha256=data["pdf_sha256"],
        source_url="file://fixture",
        freshness=SourceFreshness.REUSED_CACHED,
    )


@pytest.fixture
def batch(view, source):
    return extract_records(view, load_pdf_mapping("bs"), source)


# --------------------------------------------------------------------------
# 六个有息负债分项，**逐个**断言取到的值
# --------------------------------------------------------------------------
#
# ⚠️ 逐个断言，**不写一条「四个都是 EMPTY_CELL」的聚合断言**。
# SC-8 的要求是验收看取到的值，而聚合断言恰好是命中数的另一种写法。


def test_短期借款是行在格子空(batch):
    record = batch.by_field("bs.short_term_borrowings")
    assert record.cell_state is CellState.EMPTY_CELL
    assert record.value == Decimal("0")


def test_交易性金融负债是行在格子空(batch):
    record = batch.by_field("bs.trading_financial_liabilities")
    assert record.cell_state is CellState.EMPTY_CELL
    assert record.value == Decimal("0")


def test_长期借款是行在格子空(batch):
    record = batch.by_field("bs.long_term_borrowings")
    assert record.cell_state is CellState.EMPTY_CELL
    assert record.value == Decimal("0")


def test_应付债券是行在格子空(batch):
    record = batch.by_field("bs.bonds_payable")
    assert record.cell_state is CellState.EMPTY_CELL
    assert record.value == Decimal("0")


def test_一年内到期的非流动负债有真值(batch):
    record = batch.by_field("bs.non_current_liabilities_due_within_one_year")
    assert record.cell_state is CellState.VALUE_PRESENT
    assert record.value == Decimal("57054879.48")


def test_租赁负债有真值(batch):
    record = batch.by_field("bs.lease_liabilities")
    assert record.cell_state is CellState.VALUE_PRESENT
    assert record.value == Decimal("266636234.04")


def test_空格子是一次成功的抽取而不是失败(batch):
    """结论是 0，不是「没抽到」。

    `ExtractionStatus`（这次抽取的成败）与 `CellState`（格子的事实）是**正交**的两件事。
    把空格子记成 `REFUSED` 会让「披露了这一行且本期为零」变成一次抽取失败，
    而那正是 A-2 要修的那个错。
    """
    for field_id in (
        "bs.short_term_borrowings",
        "bs.trading_financial_liabilities",
        "bs.long_term_borrowings",
        "bs.bonds_payable",
    ):
        record = batch.by_field(field_id)
        assert record.status is ExtractionStatus.SUCCESS, field_id


# --------------------------------------------------------------------------
# 反向：整行不存在 = 缺失，**不是 0**
# --------------------------------------------------------------------------


def _drop_row(view: StatementView, label: str) -> StatementView:
    """从行集合里删掉某一行，**但保留 `all_label_sequences` 里的那条标签**。

    保留是关键：删掉的话触发的是 `L-36`（整份 PDF 零命中 ⇒ 规则写错了），
    而本用例要造的是 `ROW_ABSENT`（这张表没印这一行）。两者不是一回事。
    """
    kept = tuple(r for r in view.rows if "".join(r.label_lines) != label)
    assert len(kept) == len(view.rows) - 1, f"固件里应当恰好有一行 {label!r}"
    return dataclasses.replace(view, rows=kept)


def test_整行不存在时取到的是缺失不是零(view, source):
    """构造样本 —— 茅台 2023 上整行不存在的字段是 **0 个**（CONTEXT §3.3）。"""
    crippled = _drop_row(view, "租赁负债")
    batch = extract_records(crippled, load_pdf_mapping("bs"), source)
    record = batch.by_field("bs.lease_liabilities")
    assert record.cell_state is CellState.ROW_ABSENT
    assert record.value is None
    assert record.value != Decimal("0")


def test_删掉的那一行仍在整份PDF的标签集合里(view):
    """守住上面那个构造的**前提**。

    若哪天 `_drop_row` 连 `all_label_sequences` 一起删了，
    `test_整行不存在时取到的是缺失不是零` 会因为 `L-36` 抛异常而红 ——
    红是红了，但红的原因不是它要查的那件事（`b0afe00` 那次教训）。
    """
    crippled = _drop_row(view, "租赁负债")
    assert ("租赁负债",) in crippled.all_label_sequences


# --------------------------------------------------------------------------
# 一正一反跑同一个指标，缺一条这个语义就只被验了一半
# --------------------------------------------------------------------------


def test_有息负债率在真实批次上算得出数值而不是拒答(batch):
    """`A-2` 的判据。四个分项按 0 参与，两个有真值。

    实跑：`(0 + 0 + 57,054,879.48 + 0 + 0 + 266,636,234.04) / 272,699,660,092.25`
    """
    assert reconcile_batch(batch).passed is True
    result = compute_metric("interest_bearing_debt_ratio", batch)
    assert not isinstance(result, Refusal), result
    assert Decimal("0.0011") < result.value < Decimal("0.0013")


def test_有息负债率在整行不存在的批次上拒答而不是给零(view, source):
    """反向：`ROW_ABSENT` 一律取不到，**不当 0**。

    当 0 会让一张缺了某个分项的报表算出一个看起来正常的比率 ——
    「我们没取到」被伪装成「这一项确实是零」，而这两件事在证据链上后果相反。
    """
    crippled = _drop_row(view, "租赁负债")
    batch = extract_records(crippled, load_pdf_mapping("bs"), source)
    assert reconcile_batch(batch).passed is True  # 恒等式三项都还在，闸门照样过
    result = compute_metric("interest_bearing_debt_ratio", batch)
    assert isinstance(result, Refusal), result
    # 责任方与缺的是哪个字段都要在拒答理由里（L-9）——
    # 只说「证据不足」的话，复核者无从判断该去修哪一处。
    assert "bs.lease_liabilities" in result.detail


def test_定义侧一个字都没改():
    """`A-2` 判据原话：**抽取层区分两者，定义侧不改**。

    `undefined_conditions` 里那条 `is_missing(...)` 保持原样 ——
    格子空时抽取层给的是有值的 0，`is_missing` 自然为假，那条拒答条件不触发。
    """
    import yaml

    definition = yaml.safe_load(
        (Path(__file__).resolve().parent.parent / "metrics" / "interest_bearing_debt_ratio.yaml").read_text(
            encoding="utf-8"
        )
    )
    exprs = [c["expr"] for c in definition["undefined_conditions"]]
    assert any("is_missing(bs.short_term_borrowings)" in e for e in exprs), (
        "定义里那条按缺失拒答的条件应当原样保留 —— 本轮修的是抽取层，不是定义"
    )
