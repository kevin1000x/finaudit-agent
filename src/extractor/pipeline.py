"""抽取的包装层 —— **留痕的采集点只有这里一处**（L-55）。

## 为什么采集点在包装层而不在每个抽取函数里

实证，不是偏好。hello-agents 把截断放在**调用点**：`truncator.py` 的文档写着
「统一截断工具输出」，而实际 **6 个调用点只覆盖了 2 个**
（`references/hello-agents-ch07-framework.md` / 台账 `L-55`）。

⇒ **凡是要求「每次都做」的事，就不能放在调用点。**

所以 `_stamp_provenance` 只在本模块被调用。`locate.py` / `mapping.py` / `record.py`
内部一次都不调，它们连 import 都没有。这条由 `tests/test_record.py::test_留痕采集点唯一`
用 AST 守着，不靠自觉 —— 靠自觉的规则在写下它的当天就失败过（台账 N-35）。

## 抽取路径与计算路径是同一条

CONTEXT §6 记着 cninfo 的病根：`pipeline.py:758` 硬编码
`'financial_statements': {}`，计算侧从不读它 —— **它抽了报表，却用 AKShare 的
指标算结论**，两条路径不相交，所以它「完全没有勾稽校验」不是疏忽，是结构上做不到。

本模块产出的 `ExtractionBatch` 是 `reconcile` 与 `formula` 的**唯一**输入。
没有第二条路。

## 三处零命中语义（L-36 与 SC-3 的分界）

| 情形 | 处置 |
|---|---|
| 条目在**整份 PDF** 上一次都没匹配上 | 抛异常 —— 单一权威表里，一条匹配不到任何东西的规则只可能是写错了（L-36） |
| 条目在目标报表区间内没匹配上，但别处匹配得上 | `ROW_ABSENT` —— 这张表确实没有这一行（SC-3） |
| 条目在目标区间内匹配上**多行** | `ATTEMPTED_UNKNOWN` —— 试过但判不出是哪一行，不在两个已知态里挑一个报（L-10） |

## PDF 不落地

`extract_batch` 用临时目录接 `fetch_annual_report(keep_pdf=True, keep_dir=<临时目录>)`，
解析完随目录一起删。落库的是「结构化行 + PDF 的 SHA-256 + 巨潮源 URL + 页码」，
PDF 本身不留（台账 N-3）。`.pdf` 同时在 `.gitignore` 与 `scan_rules.yaml` 的
`forbidden_tracked_file_types` 里，两处都挡着。
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from semantic_layer.resolve import Refusal, RefusalCode

from . import locate
from .download import DownloadResult, fetch_annual_report
from .mapping import FieldMapping, PdfMappingTable, load_pdf_mapping, match_row
from .record import (
    BasisConfirmation,
    RecordKind,
    CellState,
    ExtractionBatch,
    ExtractionRecord,
    ExtractionStatus,
    RetrievalOutcome,
    Selection,
    SourceFreshness,
    make_batch_id,
)

__all__ = [
    "DEFAULT_STATEMENT",
    "FULL_TABLE_SELECTION",
    "SOURCE_PDF_LAYOUT",
    "MappingZeroHit",
    "ExtractionSource",
    "StatementView",
    "read_statement",
    "snapshot_definition_versions",
    "extract_records",
    "extract_batch",
    "DEFAULT_EXTRACTION_PLAN",
]

DEFAULT_STATEMENT = "合并资产负债表"

#: **本模块只处理从「某一行取某一列」的两个类别。**
#:
#: 另外三支（`NOTE_CHECKBOX` / `COLUMN_HEADER_PRESENCE` / `REPORT_METADATA`）
#: 结构上不取行值，由 `01.5-05` 在各自的模块里实现。
#: 这里只建**分派点**并对未实现的类别显式抛错 ——
#: 按 `L-35` 类别判定只能靠显式 `kind`，按 `L-55` 各类别的处理逻辑不该堆在包装层里。
#:
#: ⚠️ 抛 `NotImplementedError` 而不是跳过：跳过会让那些字段**静默地不出现在批次里**，
#: 而调用方看到的是一个「成功」的批次，只是少了几条记录。
_KIND_HANDLED_HERE = frozenset({RecordKind.STATEMENT_LINE, RecordKind.KPI_DISCLOSED})

#: 取数口径三元组（D-023 / L-2 / J-7）。整表逐行读时三个子字段取**显式值**，
#: 不留空 —— `sampling="整表逐行"` 陈述的是「这是整表」，本身是信息。
FULL_TABLE_SELECTION = Selection(
    sampling="整表逐行",
    order_key="page,y",
    truncation="未截断",
)

#: 责任方标识（L-9）。稳定串，可逐字比对（J-6）。
SOURCE_PDF_LAYOUT = "cninfo:pdf/layout"


class MappingZeroHit(ValueError):
    """一条映射规则在整份 PDF 上零命中（L-36）。

    **抛异常不返回 `Refusal`**：这是「我们写错了」，写不进用户文档（D-022 决策二）。
    """


@dataclass(frozen=True)
class ExtractionSource:
    """一次抽取的出处来源。**每个字段都会被盖进每一条记录**。"""

    stock_code: str
    fiscal_year: int
    pdf_sha256: str
    source_url: str
    freshness: SourceFreshness

    @property
    def batch_id(self) -> str:
        return make_batch_id(self.stock_code, self.fiscal_year, self.pdf_sha256)


@dataclass(frozen=True)
class StatementView:
    """一张报表的版面事实：锚点、表头、区间内的重组行，以及整份 PDF 的标签序列。

    最后一项只服务 L-36 的零命中判定 —— 它需要「整份 PDF」这个视野，
    而单张报表的区间给不了。
    """

    anchor: locate.StatementAnchor
    header: locate.SheetHeader
    rows: tuple[locate.ReconstructedRow, ...]
    all_label_sequences: frozenset[tuple[str, ...]]

    def to_dict(self) -> dict:
        return {
            "anchor": self.anchor.to_dict(),
            "header": self.header.to_dict(),
            "rows": [r.to_dict() for r in self.rows],
            "all_label_sequences": sorted(list(seq) for seq in self.all_label_sequences),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StatementView":
        """从固件重建。回归用例跑在**抽取产物**上，不跑在 PDF 上。"""
        return cls(
            anchor=locate.StatementAnchor(
                title=data["anchor"]["title"],
                page=int(data["anchor"]["page"]),
                y=float(data["anchor"]["y"]),
                is_consolidated=bool(data["anchor"]["is_consolidated"]),
            ),
            header=locate.SheetHeader(
                unit=data["header"]["unit"],
                currency=data["header"]["currency"],
                page=int(data["header"]["page"]),
                y=float(data["header"]["y"]),
                columns=tuple(
                    locate.ColumnBinding(
                        header_text=c["header_text"],
                        role=c["role"],
                        x0=float(c["x0"]),
                        x1=float(c["x1"]),
                        page=int(c["page"]),
                        header_inherited=bool(c["header_inherited"]),
                        resolution=c["resolution"],
                    )
                    for c in data["header"]["columns"]
                ),
            ),
            rows=tuple(locate.ReconstructedRow.from_dict(r) for r in data["rows"]),
            all_label_sequences=frozenset(
                tuple(seq) for seq in data["all_label_sequences"]
            ),
        )


def snapshot_definition_versions(metrics_dir: Path | str = "metrics") -> dict[str, int]:
    """抽取时刻 `metrics/` 里每份定义的 `version`（`L-38`）。

    **在建批次那一刻拍一次，之后不再读 `metrics/`。**
    复核时按批次里冻结的版本求值，不按当时的配置 ——
    否则同一条证据在两个时间点复核会得到不同结果，`D-012` 的冻结就没有意义。

    ⚠️ **拍的是全部定义，不是「这批用得上的」**：抽取的时候还不知道之后要算哪个指标，
    按需拍等于把一个「以后才知道」的条件塞进一个「现在必须做完」的动作里。
    """
    from semantic_layer.definition import iter_definition_paths, load_definition

    out: dict[str, int] = {}
    for path in iter_definition_paths(metrics_dir):
        definition = load_definition(path)
        if definition.metric_id and isinstance(definition.version, int):
            out[definition.metric_id] = definition.version
    return out


def _all_label_sequences(
    pdf, label_max_x: float, y_tolerance: float
) -> frozenset[tuple[str, ...]]:
    """整份 PDF 的标签片段序列集合。L-36 的判定对象。

    用目标报表的 `label_max_x` 扫全篇：别的版面上这条界线只是近似，
    但本集合只回答「这串标签在这份 PDF 里出现过没有」，不参与取数。
    """
    raw: list[tuple[str, tuple[locate.Cell, ...], int, float]] = []
    for page_number, page in enumerate(pdf.pages, start=1):
        for line in locate._cluster_lines(page, page_number, y_tolerance):
            if locate._is_chrome(line):
                continue
            label, cells = locate._split_line(line, label_max_x)
            if not label and not cells:
                continue
            raw.append((label, cells, page_number, line.y))
    return frozenset(row.label_lines for row in locate._stitch(raw))


def read_statement(
    pdf,
    statement: str,
    fiscal_year: int,
    y_tolerance: float = locate.DEFAULT_Y_TOLERANCE,
) -> StatementView:
    """定位一张报表并读出它的版面事实。找不到锚点 / 表头即抛 `LookupError`。"""
    anchors = locate.find_statement_anchors(pdf, y_tolerance)
    matching = [a for a in anchors if a.title == statement]
    if len(matching) != 1:
        raise locate.SheetHeaderNotFound(
            f"{statement!r} 在这份 PDF 上定位到 {len(matching)} 个锚点，期望恰好 1 个。"
        )
    anchor = matching[0]
    header = locate.bind_columns(pdf, anchor, fiscal_year, y_tolerance)
    next_anchor = locate.next_anchor_after(anchors, anchor)
    rows = locate.rows_in_span(pdf, anchor, next_anchor, header, y_tolerance)
    return StatementView(
        anchor=anchor,
        header=header,
        rows=tuple(rows),
        all_label_sequences=_all_label_sequences(pdf, header.label_max_x, y_tolerance),
    )


# --------------------------------------------------------------------------
# 留痕：**整个 src/extractor/ 下唯一的采集点**（L-55）
# --------------------------------------------------------------------------


def _stamp_provenance(
    *,
    entry: FieldMapping,
    mapping_version: int,
    source: ExtractionSource,
    view: StatementView,
    column: locate.ColumnBinding,
    matched: tuple[locate.ReconstructedRow, ...],
) -> ExtractionRecord:
    """把一次匹配结果盖上**一次独立复核所需的全部出处**，产出一条记录。

    这是全包唯一一处构造 `ExtractionRecord` 的地方。出处不是「记得填」的字段，
    而是**这里不填就构造不出来**的必需参数 —— `record.py` 那边全部字段无默认值，
    漏一个立刻 `TypeError`。

    `column_header` 记的是**版面上印的那串字**（例如 `2023年12月31日`），
    不是映射表里的口径名（`期末余额`）。理由：这条记录要证明的是
    「取的是哪一列」，而口径名由 `field_id` + `mapping_version` 已经可以复原。
    A-9 说得很清楚 —— 勾稽闸门证明不了取的是对的那一列，能证明的只有这串字。
    """
    if not matched:
        retrieval = RetrievalOutcome.ABSENT
        cell_state: CellState | None = CellState.ROW_ABSENT
        value = None
        page = view.anchor.page
    elif len(matched) > 1:
        # 试过、也扫到了，但判不出是哪一行。**不在两个已知态里挑一个报**（L-10 / F-2）。
        retrieval = RetrievalOutcome.ATTEMPTED_UNKNOWN
        cell_state = None
        value = None
        page = matched[0].page
    else:
        row = matched[0]
        page = row.page
        cell = row.cell_in(column)
        if cell is None:
            # 行在、格子空 = 披露了这一行且本期为零。**属 got_value 且值为 0**，
            # 不属 absent —— 这正是 SC-3 要区分的那条线（A-2 实测）。
            retrieval = RetrievalOutcome.GOT_VALUE
            cell_state = CellState.EMPTY_CELL
            value = locate.parse_amount("0.00")
        else:
            retrieval = RetrievalOutcome.GOT_VALUE
            cell_state = CellState.VALUE_PRESENT
            value = cell.amount

    return ExtractionRecord(
        field_id=entry.field_id,
        kind=entry.kind,
        value=value,
        status=ExtractionStatus.SUCCESS,
        retrieval=retrieval,
        basis_confirmation=BasisConfirmation.CONFIRMED,
        source_freshness=source.freshness,
        cell_state=cell_state,
        page=page,
        anchor_page=view.anchor.page,
        pdf_sha256=source.pdf_sha256,
        source_url=source.source_url,
        unit=view.header.unit,
        currency=view.header.currency,
        column_header=column.header_text,
        header_inherited=column.header_inherited,
        mapping_version=mapping_version,
        selection=FULL_TABLE_SELECTION,
        truncation_stats={},
        batch_id=source.batch_id,
    )


def extract_records(
    view: StatementView,
    mapping: PdfMappingTable,
    source: ExtractionSource,
    statement: str = DEFAULT_STATEMENT,
    batch: ExtractionBatch | None = None,
) -> ExtractionBatch:
    """把版面事实 + 映射表 → 一个批次的抽取记录。**不联网、不读盘。**

    分离出这一层是为了让回归用例跑在 `tests/fixtures/maotai_2023_bs_rows.json`
    这份**抽取产物**固件上，不必每次真下 PDF（PDF 永远不许进版本控制）。
    """
    entries = mapping.for_statement(statement)
    if not entries:
        raise MappingZeroHit(
            f"映射表 {mapping.namespace!r} 里没有任何声明 statement={statement!r} 的条目。"
        )
    unsupported = [e for e in entries if e.kind not in _KIND_HANDLED_HERE]
    if unsupported:
        raise NotImplementedError(
            "本函数只处理 "
            f"{sorted(k.name for k in _KIND_HANDLED_HERE)}；"
            f"以下条目的 kind 尚未实现：{[(e.field_id, e.kind.name) for e in unsupported]}。"
            "**分派点在这里，实现不在这里**（L-55：各类别的处理逻辑不该堆在包装层）。"
            "NOTE_CHECKBOX / COLUMN_HEADER_PRESENCE / REPORT_METADATA 三支由 01.5-05 实现。"
        )
    # `batch` 给了就往里并 —— 跨报表算指标时（如毛利率要 `is` 两个字段、
    # 而勾稽闸门建在 `bs` 三个字段上）必须是**同一个批次**：
    # 批次身份键是 `(stock_code, fiscal_year)`（D-024），一次抽取一家一年就是一批。
    # 拆成多批的话，闸门只闩得住其中一批，另一批的记录会绕过读入边界的 fail-closed。
    if batch is None:
        batch = ExtractionBatch.open(
            source.stock_code,
            source.fiscal_year,
            source.pdf_sha256,
            definition_versions=snapshot_definition_versions(),
        )
    for entry in entries:
        column = view.header.by_role(entry.column_header)
        if column is None:
            raise MappingZeroHit(
                f"{entry.field_id}：表头里绑不到口径为 {entry.column_header!r} 的列。"
                f"已绑定的列是 {[(c.header_text, c.role) for c in view.header.columns]}。"
                "口径类开关缺失即在读入边界 fail-closed，不退而取某一列（L-34）。"
            )
        matched = tuple(row for row in view.rows if match_row(row, entry))
        if not matched and not any(entry.matches(seq) for seq in view.all_label_sequences):
            raise MappingZeroHit(
                f"{entry.field_id} 的 label 变体 {entry.label_variants} "
                "在整份 PDF 上一次都没匹配上。单一权威表里，一条匹配不到任何东西的规则"
                "只可能是写错了（L-36）。"
            )
        record = _stamp_provenance(
            entry=entry,
            mapping_version=mapping.mapping_version,
            source=source,
            view=view,
            column=column.inherited_to(matched[0].page) if matched else column,
            matched=matched,
        )
        batch.add_record(record)
    return batch


#: 跨报表抽取的默认计划：`(namespace, statement)`。
#:
#: 只列三张**合并**报表：`notes` / `kpi` 的三支 `kind` 尚未实现（wave 5），
#: 现在写进来会在分派点抛 `NotImplementedError` —— 那不是「还没做」的正确表达方式，
#: 正确的表达是**这张表不在计划里**。
DEFAULT_EXTRACTION_PLAN = (
    ("bs", "合并资产负债表"),
    ("is", "合并利润表"),
    ("cfs", "合并现金流量表"),
)


def extract_batch(
    stock_code: str,
    year: int,
    namespace: str = "bs",
    statement: str = DEFAULT_STATEMENT,
    client=None,
    mapping_dir=None,
    pdf_path: Path | str | None = None,
    plan: tuple[tuple[str, str], ...] | None = None,
) -> ExtractionBatch | Refusal:
    """端到端：取回年报 → 定位 → 匹配 → 盖出处 → 一个批次。

    `pdf_path` 给出时不联网（复跑与调试用），此时 `source_freshness` 如实记
    `REUSED_CACHED`，**不谎称本次运行取回**。
    """
    import pdfplumber  # 局部 import：`fetch` 子命令不需要它，装不上时不该连下载都跑不了

    steps = plan if plan is not None else ((namespace, statement),)
    mappings = {
        ns: (load_pdf_mapping(ns) if mapping_dir is None else load_pdf_mapping(ns, mapping_dir))
        for ns, _ in steps
    }

    def _run(path: Path, source: ExtractionSource) -> ExtractionBatch | Refusal:
        try:
            with pdfplumber.open(str(path)) as pdf:
                batch: ExtractionBatch | None = None
                for ns, stmt in steps:
                    view = read_statement(pdf, stmt, year)
                    batch = extract_records(view, mappings[ns], source, stmt, batch=batch)
                assert batch is not None
                return batch
        except locate.SheetHeaderNotFound as exc:
            # 版面与实测形态不符 = 够不着那份数据，不是我们写错了（D-022 决策二）。
            return Refusal(RefusalCode.UNAVAILABLE, f"{exc}", source=SOURCE_PDF_LAYOUT)

    if pdf_path is not None:
        path = Path(pdf_path)
        import hashlib

        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return _run(
            path,
            ExtractionSource(
                stock_code=stock_code,
                fiscal_year=year,
                pdf_sha256=digest,
                source_url=f"file://{path.resolve().as_posix()}",
                freshness=SourceFreshness.REUSED_CACHED,
            ),
        )

    with tempfile.TemporaryDirectory(prefix="finaudit-pdf-") as tmp:
        downloaded = fetch_annual_report(
            stock_code, year, keep_pdf=True, client=client, keep_dir=tmp
        )
        if isinstance(downloaded, Refusal):
            return downloaded
        assert isinstance(downloaded, DownloadResult)
        return _run(
            downloaded.pdf_path,
            ExtractionSource(
                stock_code=stock_code,
                fiscal_year=year,
                pdf_sha256=downloaded.sha256,
                source_url=downloaded.source_url,
                freshness=SourceFreshness.FETCHED_THIS_RUN,
            ),
        )
    # 临时目录随 with 一起删除 —— PDF 不落地（台账 N-3）。
