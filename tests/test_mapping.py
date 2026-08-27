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
    """15 条规则在合并资产负债表区间内**各自恰好命中 1 行**。

    ⚠️ 逐条断言，不写一条「15 条全命中」的聚合断言 —— SC-8 的要求是
    验收看取到的东西，而聚合断言恰好是命中数的另一种写法。
    """
    hits = {
        entry.field_id: [r for r in view.rows if match_row(r, entry)]
        for entry in bs.entries
    }
    多命中 = {k: len(v) for k, v in hits.items() if len(v) != 1}
    assert not 多命中, f"这些规则没有恰好命中 1 行：{多命中}"
    assert hits["bs.total_equity"][0].label_lines == ("所有者权益（或股东权", "益）合计")
    # 四个「行在但格子空」的字段照样命中了行 —— 空格子不是没匹配上（A-2）
    for field_id in (
        "bs.short_term_borrowings",
        "bs.trading_financial_liabilities",
        "bs.long_term_borrowings",
        "bs.bonds_payable",
    ):
        assert hits[field_id][0].cells == ()


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


def test_bs_映射表覆盖定义里全部bs字段且口径一致(bs):
    """`bs` 那一份的 `field_id` 集合 == `metrics/` 里全部 `bs.*` 的 `source_fields`。

    ⚠️ **右边那个集合是运行时从 `metrics/` 物化的**，测试里不写死清单（`L-37`）。
    上一版这条测试写死了三个 id（tracer 切片），映射表从 3 条扩到 15 条时它变红了
    —— 变红是对的，但它红的原因是「清单过期」而不是「覆盖不对」。
    """
    from extractor.mapping import declared_field_ids

    assert bs.namespace == "bs"
    assert bs.mapping_version == 1
    declared_bs = {i for i in declared_field_ids() if i.startswith("bs.")}
    assert {e.field_id for e in bs.entries} == declared_bs
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


# --------------------------------------------------------------------------
# D-016 判据 2：映射表与定义的**相等**断言（不是包含），两个方向各一条负向用例
# --------------------------------------------------------------------------


def test_五份映射文件的字段并集恰好等于定义的source_fields():
    """相等，不是包含。两个方向各有各的病，见 `assert_mapping_covers_definitions` 的 docstring。"""
    from extractor.mapping import (
        assert_mapping_covers_definitions,
        declared_field_ids,
        load_all_pdf_mappings,
    )

    tables = load_all_pdf_mappings()
    mapped = {e.field_id for t in tables.values() for e in t.entries}
    assert mapped == declared_field_ids()
    assert_mapping_covers_definitions()  # 不抛即通过


def test_映射表少一条时相等断言报红且指出缺的是哪个():
    """负向：从内存副本里删掉一条，异常消息必须**逐字含被删的那个 id**。

    只报「不相等」是不够的 —— 30 个 id 里少哪一个，靠人去比对就又回到了
    「派生集合与权威表并列存储」的老路。
    """
    import dataclasses

    from extractor.mapping import (
        MappingCoverageError,
        assert_mapping_covers_definitions,
        load_all_pdf_mappings,
    )

    tables = load_all_pdf_mappings()
    victim = tables["bs"].entries[0].field_id
    tables["bs"] = dataclasses.replace(tables["bs"], entries=tables["bs"].entries[1:])
    with pytest.raises(MappingCoverageError) as excinfo:
        assert_mapping_covers_definitions(tables=tables)
    assert victim in str(excinfo.value)
    assert "定义里有、映射表里没有" in str(excinfo.value)


def test_映射表多一条定义里没有的字段时同样报红():
    """负向：多出来的规则**不被任何东西校验**，会一直活着直到有人当它是对的。"""
    import dataclasses

    from extractor.mapping import (
        FieldMapping,
        MappingCoverageError,
        assert_mapping_covers_definitions,
        load_all_pdf_mappings,
    )

    tables = load_all_pdf_mappings()
    ghost = FieldMapping(
        field_id="bs.这个字段在metrics里不存在",
        statement="合并资产负债表",
        kind=RecordKind.STATEMENT_LINE,
        column_header="期末余额",
        label_variants=(("某一行",),),
    )
    tables["bs"] = dataclasses.replace(
        tables["bs"], entries=tables["bs"].entries + (ghost,)
    )
    with pytest.raises(MappingCoverageError) as excinfo:
        assert_mapping_covers_definitions(tables=tables)
    assert "bs.这个字段在metrics里不存在" in str(excinfo.value)
    assert "映射表里有、定义里没有" in str(excinfo.value)


def test_字段清单在仓库里只有一份权威来源():
    """`L-37`：改 `metrics/` 里的一个 `source_fields[].id`，`declared_field_ids()` 必须跟着变。

    这条测试的作用不是查当前值，是**证明那个集合真的是派生出来的**。
    若它是写死的，把 `metrics/` 改了它也不会动 —— 那时这条测试会红。
    """
    from extractor.mapping import declared_field_ids

    baseline = declared_field_ids()
    assert "bs.total_assets" in baseline

    import tempfile

    import yaml as _yaml

    with tempfile.TemporaryDirectory() as tmp:
        fake = Path(tmp)
        (fake / "只有一个指标.yaml").write_text(
            _yaml.safe_dump(
                {
                    "metric_id": "只有一个指标",
                    "source_fields": [{"id": "bs.仅此一条"}],
                },
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
        assert declared_field_ids(fake) == frozenset({"bs.仅此一条"})


# --------------------------------------------------------------------------
# 按 kind 的键校验（本轮新增两支 kind 逼出来的）
# --------------------------------------------------------------------------


def test_不取行值的两支kind不许带label_variants(tmp_path):
    """禁止键与必需键一样重要。

    `REPORT_METADATA` 若允许带 `label_variants`，下一个人会顺手填一条，
    而匹配路径永远不会读它 —— 一条**看起来在生效、实际从不求值**的规则。
    """
    data = {
        "namespace": "notes",
        "mapping_version": 1,
        "entries": [
            {
                "field_id": "notes.x",
                "statement": "某章节",
                "kind": "REPORT_METADATA",
                "derived_from": "由报告类型决定",
                "label_variants": [{"label_fragments": ["顺手填的一条"]}],
            }
        ],
    }
    path = tmp_path / "notes.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ValueError, match="不允许出现键"):
        load_pdf_mapping("notes", tmp_path)


def test_不取行值的两支kind必须给出derived_from(tmp_path):
    data = {
        "namespace": "notes",
        "mapping_version": 1,
        "entries": [
            {"field_id": "notes.x", "statement": "某章节", "kind": "REPORT_METADATA"}
        ],
    }
    path = tmp_path / "notes.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ValueError, match="derived_from"):
        load_pdf_mapping("notes", tmp_path)


def test_每个kind都在KEYS_BY_KIND里登记了必需键与禁止键():
    """新增类别必须同时登记，否则它**绕过全部按类别的校验**。

    加载器里也有一条同样的拒绝（`kind 没有在 KEYS_BY_KIND 里登记`），
    但那条只在真有人写了这样一条 YAML 时才触发；本测试在**加类别的那一刻**就红。
    """
    from extractor import mapping as mapping_module

    kinds_without_schema = [
        name for name in RecordKind.__members__ if name not in mapping_module.KEYS_BY_KIND
    ]
    assert not kinds_without_schema, (
        f"这些 kind 没有在 KEYS_BY_KIND 里登记必需键：{kinds_without_schema}"
    )


def test_未实现的kind在分派点显式抛错而不是被跳过(view, source):
    """跳过会让那些字段**静默地不出现在批次里**，而调用方看到一个「成功」的批次。"""
    import dataclasses

    from extractor.mapping import load_pdf_mapping as _load
    from extractor.pipeline import extract_records

    notes = _load("notes")
    checkbox = [e for e in notes.entries if e.kind is RecordKind.NOTE_CHECKBOX]
    assert checkbox, "notes.yaml 里应当有 NOTE_CHECKBOX 条目"
    table = dataclasses.replace(notes, entries=tuple(checkbox))
    with pytest.raises(NotImplementedError, match="NOTE_CHECKBOX"):
        extract_records(view, table, source, statement=checkbox[0].statement)
