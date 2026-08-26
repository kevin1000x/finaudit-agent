"""映射表加载与匹配的回归 —— D-016 / SC-2 / L-36 / L-40。

**核心断言只有一条**：逐字整行相等，不是子串包含。
它同时解掉台账 A-4 的真实反例与一对极易混淆的行项目。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from extractor.mapping import (
    REQUIRED_ENTRY_KEYS,
    load_pdf_mapping,
    match_row,
)
from extractor.pipeline import (
    ExtractionSource,
    MappingZeroHit,
    StatementView,
    extract_records,
)
from extractor.record import CellState, RecordKind, RetrievalOutcome, SourceFreshness

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = Path(__file__).parent / "fixtures" / "maotai_2023_bs_rows.json"
REAL_MAPPING_DIR = REPO_ROOT / "data" / "mappings" / "pdf"


@pytest.fixture(scope="module")
def raw() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def view(raw) -> StatementView:
    return StatementView.from_dict(raw)


@pytest.fixture(scope="module")
def bs():
    return load_pdf_mapping("bs", REAL_MAPPING_DIR)


@pytest.fixture
def source(raw) -> ExtractionSource:
    return ExtractionSource(
        stock_code=raw["source"]["stock_code"],
        fiscal_year=raw["source"]["fiscal_year"],
        pdf_sha256=raw["source"]["pdf_sha256"],
        source_url="https://static.cninfo.com.cn/finalpage/2024-04-03/1219506510.PDF",
        freshness=SourceFreshness.REUSED_CACHED,
    )


def _write_mapping(tmp_path: Path, data: dict) -> Path:
    (tmp_path / "bs.yaml").write_text(
        yaml.safe_dump(data, allow_unicode=True), encoding="utf-8"
    )
    return tmp_path


def _valid_mapping_dict() -> dict:
    return yaml.safe_load((REAL_MAPPING_DIR / "bs.yaml").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# 逐字整行相等
# --------------------------------------------------------------------------


def test_章节小标题不匹配所有者权益合计的任何变体(bs):
    """台账 A-4 的真实反例。

    茅台 2023 p60 上有一行「所有者权益（或股东权益）：」——**章节小标题，没有数值**。
    子串包含会让 `bs.total_equity` 匹配到它，随后取到一个空值而「命中数」照样是 3/3。
    A-4 就是这么被骗过一次的，SC-8 因此要求验收看取到的值不看命中数。
    """
    equity = bs.by_field("bs.total_equity")
    assert equity is not None
    assert not equity.matches(("所有者权益（或股东权益）：",))
    # 反过来确认这条断言不是空转：真实的那一行确实匹配得上。
    assert equity.matches(("所有者权益（或股东权", "益）合计"))


def test_归属于母公司的那一行不冒名所有者权益合计(bs):
    """「归属于母公司所有者权益（或股东权益）合计」与「所有者权益（或股东权益）合计」。

    这一对极易混淆：前者是 215,668,571,607.43，后者是 223,656,469,294.82，
    差的正是少数股东权益 7,987,897,687.39。取错的话资产负债率会偏低，
    而勾稽恒等式**照样通不过也说不清是哪一项错了**。
    """
    equity = bs.by_field("bs.total_equity")
    assert not equity.matches(("归属于母公司所有者权益", "（或股东权益）合计"))
    assert not equity.matches(("负债和所有者权益", "（或股东权益）总计"))


def test_片段序列按顺序比对而不是当成集合(bs):
    equity = bs.by_field("bs.total_equity")
    assert equity.matches(("所有者权益（或股东权", "益）合计"))
    assert not equity.matches(("益）合计", "所有者权益（或股东权"))


def test_match_row_对固件里的真实行给出预期命中(view, bs):
    hits = {
        entry.field_id: [r for r in view.rows if match_row(r, entry)]
        for entry in bs.entries
    }
    assert {k: len(v) for k, v in hits.items()} == {
        "bs.total_assets": 1,
        "bs.total_liabilities": 1,
        "bs.total_equity": 1,
    }
    assert hits["bs.total_equity"][0].label_lines == ("所有者权益（或股东权", "益）合计")


# --------------------------------------------------------------------------
# fail-closed 加载：必需键缺一即拒绝
# --------------------------------------------------------------------------


def test_删掉_column_header_后加载抛异常(tmp_path):
    """负向用例。补默认值会让漏写变成**静默取错列**，且没有任何东西会报错。"""
    data = _valid_mapping_dict()
    del data["entries"][0]["column_header"]
    directory = _write_mapping(tmp_path, data)
    with pytest.raises(ValueError, match="column_header"):
        load_pdf_mapping("bs", directory)


@pytest.mark.parametrize("key", REQUIRED_ENTRY_KEYS)
def test_五个必需键缺任何一个都拒绝加载(tmp_path, key):
    data = _valid_mapping_dict()
    del data["entries"][0][key]
    directory = _write_mapping(tmp_path, data)
    with pytest.raises(ValueError, match=key):
        load_pdf_mapping("bs", directory)


def test_未声明口径版本的映射表被拒绝(tmp_path):
    """L-40：遍历数据源注册表时拒绝任何未声明口径版本的条目。"""
    data = _valid_mapping_dict()
    del data["mapping_version"]
    directory = _write_mapping(tmp_path, data)
    with pytest.raises(ValueError, match="mapping_version"):
        load_pdf_mapping("bs", directory)


def test_kind_只接受枚举成员名(tmp_path):
    """L-35：类别只能显式声明，不许由形状反推，也不许自造。"""
    data = _valid_mapping_dict()
    data["entries"][0]["kind"] = "看起来像三大表某一行"
    directory = _write_mapping(tmp_path, data)
    with pytest.raises(ValueError, match="kind"):
        load_pdf_mapping("bs", directory)


def test_field_id_必须带命名空间前缀(tmp_path):
    data = _valid_mapping_dict()
    data["entries"][0]["field_id"] = "total_assets"
    directory = _write_mapping(tmp_path, data)
    with pytest.raises(ValueError, match="命名空间前缀"):
        load_pdf_mapping("bs", directory)


# --------------------------------------------------------------------------
# 真映射表的形状
# --------------------------------------------------------------------------


def test_真映射表恰好三条且都指向合并资产负债表的期末余额(bs):
    assert bs.namespace == "bs"
    assert bs.mapping_version == 1
    assert [e.field_id for e in bs.entries] == [
        "bs.total_assets",
        "bs.total_liabilities",
        "bs.total_equity",
    ]
    assert all(e.statement == "合并资产负债表" for e in bs.entries)
    assert all(e.column_header == "期末余额" for e in bs.entries)
    assert all(e.kind is RecordKind.STATEMENT_LINE for e in bs.entries)


def test_映射表口径名不写成版面上的日期(bs):
    """写日期会让映射表变成逐年一份。日期与口径的对应由 locate 显式判定。"""
    assert all("2023" not in e.column_header for e in bs.entries)


# --------------------------------------------------------------------------
# L-36：零命中 vs 整行不存在
# --------------------------------------------------------------------------


def test_整份PDF零命中的规则判为写错了(tmp_path, view, source):
    """L-36：单一权威表里，一条匹配不到任何东西的规则只可能是写错了。"""
    data = _valid_mapping_dict()
    data["entries"] = [data["entries"][0]]
    data["entries"][0]["label_variants"] = [{"label_fragments": ["资产总计（打错的）"]}]
    directory = _write_mapping(tmp_path, data)
    mapping = load_pdf_mapping("bs", directory)
    with pytest.raises(MappingZeroHit, match="整份 PDF"):
        extract_records(view, mapping, source)


def test_别处匹配得上但本表没有的行判为整行不存在(tmp_path, view, source):
    """SC-3 的另一半：这张表确实没有这一行 ≠ 规则写错了。

    **这一条是构造出来的，如实说明为什么：** 茅台 2023 的母公司资产负债表行项目
    是合并资产负债表的**真子集**（实测：两表标签序列取差集为空），
    所以固件里找不到一个「别的表上有、这张表上没有」的天然样本。
    构造法是把某一行从区间里摘掉，但保留它在 `all_label_sequences` 里 ——
    这恰好就是「另一张表上有它」的形态。

    天然正样本要等 `01.5-03-PLAN.md` 接进第二家公司（茅台还缺企业合并正样本，
    见 CONTEXT §3.5 的诚实限定）。
    """
    import dataclasses

    dropped = ("长期股权投资",)
    assert dropped in view.all_label_sequences
    narrowed = dataclasses.replace(
        view, rows=tuple(r for r in view.rows if r.label_lines != dropped)
    )
    assert len(narrowed.rows) == len(view.rows) - 1, "构造的前提是确实摘掉了一行"

    data = _valid_mapping_dict()
    data["entries"] = [
        {
            "field_id": "bs.long_term_equity_investment",
            "statement": "合并资产负债表",
            "column_header": "期末余额",
            "kind": "STATEMENT_LINE",
            "label_variants": [{"label_fragments": list(dropped)}],
        }
    ]
    directory = _write_mapping(tmp_path, data)
    mapping = load_pdf_mapping("bs", directory)
    record = extract_records(narrowed, mapping, source).by_field(
        "bs.long_term_equity_investment"
    )
    assert record.cell_state is CellState.ROW_ABSENT
    assert record.retrieval is RetrievalOutcome.ABSENT
    assert record.value is None


def test_行在格子空取到的是零不是缺失(tmp_path, view, source):
    """SC-3 的那条线 / A-2 的实测：茅台四个有息负债分项**行在、格子空**。

    正确答案是 0 不是缺失。把两者混成一个「缺失」，有息负债率会在一家
    真的没有有息负债的公司上拒答。
    """
    from decimal import Decimal

    data = _valid_mapping_dict()
    data["entries"] = [
        {
            "field_id": "bs.short_term_borrowings",
            "statement": "合并资产负债表",
            "column_header": "期末余额",
            "kind": "STATEMENT_LINE",
            "label_variants": [{"label_fragments": ["短期借款"]}],
        }
    ]
    directory = _write_mapping(tmp_path, data)
    mapping = load_pdf_mapping("bs", directory)
    record = extract_records(view, mapping, source).by_field("bs.short_term_borrowings")
    assert record.cell_state is CellState.EMPTY_CELL
    assert record.retrieval is RetrievalOutcome.GOT_VALUE
    assert record.value == Decimal("0")


def test_区间内命中多行时如实报判不出(tmp_path, view, source):
    """L-10 的第三态有真实触发路径，不是凑数的枚举成员。

    「其中：优先股」在合并资产负债表区间内出现两次（负债侧与权益侧各一次）。
    在两个已知态里挑一个报就是 F-2 的形状。
    """
    data = _valid_mapping_dict()
    data["entries"] = [
        {
            "field_id": "bs.preferred_shares",
            "statement": "合并资产负债表",
            "column_header": "期末余额",
            "kind": "STATEMENT_LINE",
            "label_variants": [{"label_fragments": ["其中：优先股"]}],
        }
    ]
    directory = _write_mapping(tmp_path, data)
    mapping = load_pdf_mapping("bs", directory)
    matched = [r for r in view.rows if r.label_lines == ("其中：优先股",)]
    assert len(matched) > 1, "本用例的前提是该标签在区间内确实出现多次"
    batch = extract_records(view, mapping, source)
    record = batch.by_field("bs.preferred_shares")
    assert record.retrieval is RetrievalOutcome.ATTEMPTED_UNKNOWN
    assert record.cell_state is None
    assert record.value is None


def test_绑不到口径对应的列时fail_closed(tmp_path, view, source):
    """L-34：口径类开关缺失即在读入边界拒绝，不退而取某一列。"""
    data = _valid_mapping_dict()
    data["entries"] = [data["entries"][0]]
    data["entries"][0]["column_header"] = "本期发生额"
    directory = _write_mapping(tmp_path, data)
    mapping = load_pdf_mapping("bs", directory)
    with pytest.raises(MappingZeroHit, match="本期发生额"):
        extract_records(view, mapping, source)
