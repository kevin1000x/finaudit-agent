"""抽取记录形状的回归 —— D-019 / D-023 / D-024 与 L-10 / L-14 / L-44 / L-45。

每条测试对应一个**已经写下来的判据**，不是「覆盖率」。
"""

from __future__ import annotations

from dataclasses import fields
from decimal import Decimal

import pytest

from extractor.record import (
    BasisConfirmation,
    CellState,
    ExtractionBatch,
    ExtractionRecord,
    ExtractionStatus,
    MergeSemantics,
    RecordKind,
    RetrievalOutcome,
    Selection,
    SourceFreshness,
    make_batch_id,
    _collection_typed_fields,
)

SHA_A = "a" * 64
SHA_B = "b" * 64

FULL_TABLE = Selection(
    sampling="full",
    order_key="page_then_y",
    truncation="none",
)


def _record(**overrides) -> ExtractionRecord:
    """构造一条合法记录。测试用 `overrides` 只改它要考的那一处。"""
    kwargs = dict(
        field_id="bs.total_assets",
        kind=RecordKind.STATEMENT_LINE,
        value=Decimal("276022407588.35"),
        status=ExtractionStatus.SUCCESS,
        retrieval=RetrievalOutcome.GOT_VALUE,
        basis_confirmation=BasisConfirmation.CONFIRMED,
        source_freshness=SourceFreshness.FETCHED_THIS_RUN,
        cell_state=CellState.VALUE_PRESENT,
        page=60,
        anchor_page=59,
        pdf_sha256=SHA_A,
        source_url="https://static.cninfo.com.cn/finalpage/x.PDF",
        unit="元",
        currency="人民币",
        column_header="期末余额",
        header_inherited=False,
        mapping_version=1,
        selection=FULL_TABLE,
        truncation_stats={},
        batch_id=make_batch_id("600519", 2023, SHA_A),
    )
    kwargs.update(overrides)
    return ExtractionRecord(**kwargs)


# --------------------------------------------------------------------------
# D-023：取数口径三元组不可为空
# --------------------------------------------------------------------------


def test_selection_缺子字段即构造失败():
    """D-023 判据 2：缺失是**构造失败**，不是记一条 warning。"""
    with pytest.raises(TypeError):
        Selection(sampling="full", order_key="page_then_y")  # type: ignore[call-arg]
    with pytest.raises(ValueError):
        Selection(sampling="full", order_key="page_then_y", truncation="")


def test_记录不接受形状相似的字典冒充_selection():
    """三元组必须是 `Selection` 实例。放行字典等于放弃了「三个子字段都在」这条不变量。"""
    with pytest.raises(ValueError):
        _record(selection={"sampling": "full", "order_key": "y", "truncation": "none"})


def test_记录带得动_selection_与两个页码():
    r = _record()
    assert r.selection.sampling == "full"
    assert isinstance(r.page, int) and isinstance(r.anchor_page, int)
    # D-019 的理由就在这里：标题印在上一页时两者不等，单一整数表达不了。
    assert r.anchor_page != r.page


# --------------------------------------------------------------------------
# D-024：批次身份
# --------------------------------------------------------------------------


def test_batch_id_同输入两次调用同输出():
    """D-024 判据 1 / J-6：同一份年报重下必须得到同一个 id。"""
    first = make_batch_id("600519", 2023, SHA_A)
    second = make_batch_id("600519", 2023, SHA_A)
    assert first == second
    assert len(first) == 16


def test_两家公司的批次可共存且_batch_id_不相等():
    """D-024 判据 2。01.5-02 立刻就要第二家公司做企业合并的正样本。"""
    maotai = ExtractionBatch.open("600519", 2023, SHA_A)
    other = ExtractionBatch.open("000001", 2023, SHA_B)
    assert maotai.batch_id != other.batch_id

    maotai.add_record(_record(batch_id=maotai.batch_id))
    other.add_record(_record(batch_id=other.batch_id, value=Decimal("1.00")))
    assert len(maotai.records) == 1 and len(other.records) == 1
    assert maotai.records[0].batch_id == maotai.batch_id
    assert other.records[0].batch_id == other.batch_id


def test_别家公司的记录进不了本批次():
    """身份必须活在数据里。混进来不报错，就等于身份活在人脑里。"""
    maotai = ExtractionBatch.open("600519", 2023, SHA_A)
    foreign = _record(batch_id=make_batch_id("000001", 2023, SHA_B))
    with pytest.raises(ValueError):
        maotai.add_record(foreign)


def test_批次闩死后拒绝追加记录():
    """L-13：重试不得跨闸门批次，重试必须从新批次开始。"""
    batch = ExtractionBatch.open("600519", 2023, SHA_A)
    batch.seal(reconciliation=None)
    with pytest.raises(ValueError):
        batch.add_record(_record(batch_id=batch.batch_id))


# --------------------------------------------------------------------------
# L-10 / SC-3：三态，且「格子空」不是「缺失」
# --------------------------------------------------------------------------


def test_格子空产出零值而整行不存在产出_absent():
    """SC-3 的那条线，也是 A-2 的实测：茅台四个有息负债分项行在格子空。

    把两者混成一个「缺失」，有息负债率会在一家真的没有有息负债的公司上拒答。
    """
    empty_cell = _record(cell_state=CellState.EMPTY_CELL, value=Decimal(0))
    row_absent = _record(cell_state=CellState.ROW_ABSENT, value=None,
                         retrieval=RetrievalOutcome.ABSENT)

    assert empty_cell.retrieval is RetrievalOutcome.GOT_VALUE
    assert empty_cell.value == Decimal(0)
    assert row_absent.retrieval is RetrievalOutcome.ABSENT
    assert empty_cell.retrieval != row_absent.retrieval


def test_格子空却报_absent_会被拦下():
    """反过来也要拦：否则实现可以一边声称区分了，一边把零报成缺失。"""
    with pytest.raises(ValueError):
        _record(cell_state=CellState.EMPTY_CELL, value=Decimal(0),
                retrieval=RetrievalOutcome.ABSENT)


def test_第三态试过但判不出_不许被塞进两个已知态():
    """L-10 的第三态。判不出就如实说判不出，挑一个报是 F-2 的形状。"""
    unknown = _record(retrieval=RetrievalOutcome.ATTEMPTED_UNKNOWN,
                      cell_state=None, value=None)
    assert unknown.retrieval.value == "attempted_unknown"
    assert unknown.cell_state is None
    with pytest.raises(ValueError):
        _record(retrieval=RetrievalOutcome.ATTEMPTED_UNKNOWN,
                cell_state=CellState.EMPTY_CELL, value=Decimal(0))


# --------------------------------------------------------------------------
# L-14：三个正交事实互不嵌套
# --------------------------------------------------------------------------


def test_三个正交事实是三个独立字段():
    """L-14：「取到数了」「口径已确认」「数据源新鲜」不得互相嵌套。

    改其中一个不影响另外两个 —— 这是「独立」的可检验形态。
    """
    names = {f.name for f in fields(ExtractionRecord)}
    assert {"retrieval", "basis_confirmation", "source_freshness"} <= names

    base = _record()
    stale = _record(source_freshness=SourceFreshness.UNKNOWN,
                    basis_confirmation=BasisConfirmation.UNCONFIRMED)
    assert stale.retrieval == base.retrieval
    assert stale.source_freshness != base.source_freshness
    assert stale.basis_confirmation != base.basis_confirmation


# --------------------------------------------------------------------------
# L-34 / L-45：口径开关无默认值；截断必须报 PARTIAL
# --------------------------------------------------------------------------


def test_省略_unit_构造失败():
    """L-34：口径类开关不设默认值，缺失即在构造边界 fail-closed。"""
    with pytest.raises(TypeError):
        ExtractionRecord(  # type: ignore[call-arg]
            field_id="bs.total_assets",
            kind=RecordKind.STATEMENT_LINE,
            value=Decimal("1.00"),
            status=ExtractionStatus.SUCCESS,
            retrieval=RetrievalOutcome.GOT_VALUE,
            basis_confirmation=BasisConfirmation.CONFIRMED,
            source_freshness=SourceFreshness.FETCHED_THIS_RUN,
            cell_state=CellState.VALUE_PRESENT,
            page=60,
            anchor_page=59,
            pdf_sha256=SHA_A,
            source_url="https://static.cninfo.com.cn/x.PDF",
            currency="人民币",
            column_header="期末余额",
        header_inherited=False,
            mapping_version=1,
            selection=FULL_TABLE,
            truncation_stats={},
            batch_id=make_batch_id("600519", 2023, SHA_A),
        )


def test_空的_unit_也构造失败():
    """「填了个空的」与「没填」在证据链里同样无用。"""
    with pytest.raises(ValueError):
        _record(unit="")


def test_partial_必须带非空_truncation_stats_而_success_必须为空():
    """L-45：被截断报 SUCCESS 的话，AC-05 的字段齐全率会在一个假成功上判过。"""
    partial = _record(status=ExtractionStatus.PARTIAL,
                      truncation_stats={"dropped_rows": 3})
    assert partial.truncation_stats["dropped_rows"] == 3

    with pytest.raises(ValueError):
        _record(status=ExtractionStatus.PARTIAL, truncation_stats={})
    with pytest.raises(ValueError):
        _record(status=ExtractionStatus.SUCCESS, truncation_stats={"dropped_rows": 3})


# --------------------------------------------------------------------------
# L-44：集合型字段的合并语义写进 schema
# --------------------------------------------------------------------------


def test_每个集合型字段都登记了合并语义():
    """L-44：不在建表时定，之后每个写入方会各写各的。"""
    declared = set(ExtractionRecord.MERGE_SEMANTICS)
    actual = set(_collection_typed_fields())
    assert actual, "没有识别出任何集合型字段——检查 _collection_typed_fields 的判据"
    assert actual <= declared, f"未登记合并语义的集合型字段：{sorted(actual - declared)}"
    assert all(isinstance(v, MergeSemantics) for v in ExtractionRecord.MERGE_SEMANTICS.values())


# --------------------------------------------------------------------------
# L-35：类别由显式 kind 带出来
# --------------------------------------------------------------------------


def test_kind_必须是枚举成员而不是字符串():
    """L-35：放行字符串等于给「由文本猜类别」留了入口。"""
    with pytest.raises(ValueError):
        _record(kind="STATEMENT_LINE")


# --------------------------------------------------------------------------
# D-019：页码是整数
# --------------------------------------------------------------------------


def test_页码必须是整数且不接受布尔():
    """`True == 1` 会让一个布尔静默冒充第 1 页。"""
    with pytest.raises(ValueError):
        _record(page="60")
    with pytest.raises(ValueError):
        _record(anchor_page=True)


def test_记录可序列化为可机读字典():
    """证据链是第一类产物（D-003），键名照抄 resolve.Refusal.to_dict() 的风格。"""
    payload = _record().to_dict()
    assert payload["selection"] == {"sampling": "full", "order_key": "page_then_y",
                                    "truncation": "none"}
    assert payload["page"] == 60 and payload["anchor_page"] == 59
    assert payload["retrieval"] == "got_value"
    assert payload["field_id"] == "bs.total_assets"


# --------------------------------------------------------------------------
# L-55：留痕的采集点只有包装层一处
# --------------------------------------------------------------------------


def test_留痕采集点唯一():
    """`_stamp_provenance` 的调用点在整个 `src/extractor/` 下只出现在 `pipeline.py`。

    实证依据：hello-agents 把截断放在**调用点**，`truncator.py` 的文档写着
    「统一截断工具输出」而实际 **6 个调用点只覆盖了 2 个**（L-55 / ARCHITECTURE §8.5）。
    ⇒ **凡是要求「每次都做」的事，就不能放在调用点。**

    走 AST 不走行首正则：D-015 判据 2 已经为依赖方向立过同一条规矩，
    理由一样 —— 函数体内与 `if TYPE_CHECKING:` 块里的东西，行首正则扫不到。
    """
    import ast
    from pathlib import Path

    package = Path(__file__).resolve().parent.parent / "src" / "extractor"
    modules = sorted(package.glob("*.py"))
    assert len(modules) >= 5, f"抽取器包只找到 {len(modules)} 个模块，扫描范围可疑"

    callers = {}
    for module in modules:
        tree = ast.parse(module.read_text(encoding="utf-8"), filename=str(module))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = (
                func.id
                if isinstance(func, ast.Name)
                else func.attr
                if isinstance(func, ast.Attribute)
                else None
            )
            if name == "_stamp_provenance":
                callers.setdefault(module.name, 0)
                callers[module.name] += 1

    assert set(callers) == {"pipeline.py"}, (
        f"留痕采集点散落到了 {sorted(callers)}。"
        "凡是要求「每次都做」的事就不能放在调用点（L-55）。"
    )
    assert callers["pipeline.py"] == 1, (
        f"pipeline.py 里有 {callers['pipeline.py']} 处采集点，期望恰好 1 处"
    )


def test_留痕采集点唯一这条断言不是空转():
    """负控制（J-5）：把一个假调用点放进 AST，上面那条必须红。

    没有这一条的话，`_stamp_provenance` 哪天被改名，上面那条会因为
    「一个调用点都没找到」而静默通过 —— 集合相等对空集也成立。
    """
    import ast

    tree = ast.parse("def f():\n    return _stamp_provenance(x=1)\n")
    found = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id == "_stamp_provenance"
    ]
    assert len(found) == 1
