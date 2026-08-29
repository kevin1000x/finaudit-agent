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
from fractions import Fraction
from pathlib import Path
from typing import Mapping, Sequence

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
    "PLACEHOLDER_TEXTS",
    "REQUIRED_EVIDENCE_KEYS",
    "CompletenessReport",
    "evidence_completeness",
    "completeness_report",
]

DEFAULT_STATEMENT = "合并资产负债表"

#: **本模块只处理从「某一行取某一列」的两个类别。**
#:
#: 另外三支（`NOTE_CHECKBOX` / `COLUMN_HEADER_PRESENCE` / `REPORT_METADATA`）
#: 结构上不取行值，在 `extractor.notes` 里实现。**三支都已有实现**
#: （`NOTE_CHECKBOX` 由 `01.5-05`；另两支由 `01.5-07`），
#: 但**尚未接进本函数的批次产出** —— 见下方 `NotImplementedError` 的文案。
#:
#: ⚠️ **本行 2026-08-28 更正**（`N-43`）：原文写「由 `01.5-05` 实现」，指的是三支。
#: 那是**这条注释自己编出来的排期** —— 它写于 `db8ab4d`（08-27），
#: 而 `01.5-05-PLAN.md` 早在 `72612ec`（08-25）就已存在，且**通篇没提另外两支**
#: （`COLUMN_HEADER_PRESENCE` / `REPORT_METADATA` 在六份 PLAN 里全部零命中）。
#: 这句注释后来被 `COMPUTED-VALUES` 与交接文档照抄，成了「wave 5 要做三支 kind」这个说法的源头。
#: **余下两支目前不属于任何一份计划**，见台账 `N-43`。
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
            "三支都已在 extractor.notes 里有实现："
            "NOTE_CHECKBOX → read_scope_change（01.5-05）；"
            "COLUMN_HEADER_PRESENCE → read_restatement_flag（01.5-07）；"
            "REPORT_METADATA → derive_reporting_period_months（01.5-07）。"
            "⚠️ **但它们还没有接进本函数的批次产出** —— 调用方目前要直接调那三个入口。"
            "接进来需要先回答一个真问题：ExtractionRecord 的 column_header / unit / "
            "currency 对一个复选框字段意味着什么。**编一个值填进去就是 F-2。**"
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


# --------------------------------------------------------------------------
# AC-05：证据链的字段齐全率（口径 2026-08-22 写死，见 `PROJECT_SPEC.md` §9）
# --------------------------------------------------------------------------

#: 「有键但没真值」的文本取值。命中即**不计入齐全**。
#:
#: 反面实证是 hello-agents 的会话记录：八键齐全率 100%，其中 `llm_provider`
#: **恒为 `"unknown"`**（`references/hello-agents-framework-core.md` §7）。
#: 键在、类型对、非空 —— 三条全过，而它一个字的信息也没有。
#: ⇒ 「齐全」的判据不能是「键存在」，也不能只是「非空串」。
PLACEHOLDER_TEXTS: frozenset[str] = frozenset(
    {
        "unknown",
        "n/a",
        "na",
        "null",
        "none",
        "nil",
        "tbd",
        "-",
        "--",
        "—",
        "–",
        "未知",
        "待定",
        "暂无",
        "不详",
        "无",
    }
)

#: 计入齐全率的键。**这是一份显式清单，不是「`to_dict` 的全部键」。**
#:
#: 为什么不取全部键 —— 四类被**刻意排除**，每类的理由不同：
#:
#: 1. **`value` / `cell_state`** 是「被报告的事实」，不是关于它的证据。
#:    它们有合法的 `None` 态（`ROW_ABSENT` 不带值、`ATTEMPTED_UNKNOWN` 两者都 None），
#:    由 `record._check_state_coherence` 绑死。把它们计进来，一条正确的
#:    「这张表没有这一行」记录会被判成证据不齐 —— 那会让 `AC-05`
#:    这条**保证类**标准（<100% 即失败）变成一个正确的抽取器永远达不到的标准。
#:
#: 2. **`kind` / `status` / `retrieval` / `basis_confirmation`** 在
#:    `ExtractionRecord.__post_init__` 里已被强制为枚举成员，报告时判「是不是枚举」
#:    **构造上恒真**。计进来只会给分母加上一个永远不会失败的项 ——
#:    那正是 `AC-05` 自己要防的「用一堆必然通过的字段把齐全率刷到 100%」。
#:    `source_freshness` 是这组里**唯一**留下的：它有一个真正表示「没有值」
#:    的成员（`UNKNOWN` = 无法判定取回时点），判它非 `UNKNOWN` 是有辨析力的。
#:
#: 3. **`header_inherited`** 是布尔留证，`False` 本身就是真值 ——
#:    「有真值」在它上面没有辨析力。它由 `tests/test_evidence_ids.py` 的
#:    序列化覆盖检查看着（那条检查抓的是**键有没有被丢掉**，不是值满不满）。
#:
#: 4. **`truncation_stats`** 是条件必需，不是恒必需：`SUCCESS` 时它**必须**为空。
#:    按「非空才算齐全」计，一条正确的成功记录会被判不齐。它走
#:    `_truncation_problems()` 那条单独的合法性判定。
REQUIRED_EVIDENCE_KEYS: tuple[str, ...] = (
    "field_id",
    "page",
    "anchor_page",
    "pdf_sha256",
    "source_url",
    "unit",
    "currency",
    "column_header",
    "mapping_version",
    "selection.sampling",
    "selection.order_key",
    "selection.truncation",
    "batch_id",
    "source_freshness",
)

_TEXT_KEYS = frozenset(
    {
        "field_id",
        "pdf_sha256",
        "source_url",
        "unit",
        "currency",
        "column_header",
        "batch_id",
        "selection.sampling",
        "selection.order_key",
        "selection.truncation",
    }
)

_POSITIVE_INT_KEYS = frozenset({"page", "anchor_page", "mapping_version"})

_MISSING = object()


def _dig(payload: Mapping, key: str):
    """按 `a.b` 取值。取不到返回 `_MISSING` —— 与「取到了一个 `None`」区分开。

    两者的处置文案不同（「键不在」vs「键在但取值是 null」），合并成一个「取不到」
    就会在诊断里丢掉那一半信息 —— `notes.RestatementReading` 记的是同一件事。
    """
    node: object = payload
    for part in key.split("."):
        if not isinstance(node, Mapping) or part not in node:
            return _MISSING
        node = node[part]
    return node


def _judge(payload: Mapping, key: str) -> str | None:
    """这一个键在这条证据链里算不算「有真值」。齐全返回 `None`，否则返回原因。"""
    value = _dig(payload, key)
    if value is _MISSING:
        return "键不存在"
    if value is None:
        return "键在但取值是 null"

    if key in _TEXT_KEYS:
        if not isinstance(value, str):
            return f"应为字符串，实际是 {type(value).__name__}"
        if not value.strip():
            return "空字符串"
        if value.strip().casefold() in PLACEHOLDER_TEXTS:
            return f"占位值 {value!r} —— 键在、非空，但一个字的信息也没有"
        return None

    if key in _POSITIVE_INT_KEYS:
        if isinstance(value, bool) or not isinstance(value, int):
            return f"应为整数，实际是 {value!r}"
        if value < 1:
            return f"应 >= 1，实际是 {value}"
        return None

    if key == "source_freshness":
        if not isinstance(value, str):
            return f"应为字符串，实际是 {type(value).__name__}"
        if value == SourceFreshness.UNKNOWN.name:
            # 一条记录如实说「判不出取回时点」是**诚实的**，`record.py` 说得对。
            # 但 AC-05 数的是「这个字段有没有真值」，而它此时正是**没有**。
            # 两件事不冲突：构造边界要求它显式传入（不许默认取一个），
            # 齐全率则如实把它记成一处缺口。方向是保守的 —— 只会把率往下拉。
            return "UNKNOWN —— 如实声明判不出，但它不是一个值"
        return None

    raise AssertionError(f"{key!r} 在 REQUIRED_EVIDENCE_KEYS 里，却没有对应的判据")


def _truncation_problems(payload: Mapping) -> list[str]:
    """`L-45` 在**序列化边界**上的复查，以及 `AC-05` 的「恒零计数」那一条。

    `ExtractionRecord.__post_init__` 已经在**构造边界**拦了前两条
    （`tests/test_record.py::test_partial_必须带非空_truncation_stats_而_success_必须为空`），
    这里不是重复：证据链是**读回来的 JSON**，它没有经过那个构造器。
    复核者手上的就是这份 JSON，判据得在这一层也成立。

    第三条是构造边界**没有**的：`__post_init__` 只要求 `PARTIAL` 时 `truncation_stats`
    非空，`{"dropped_rows": 0}` 照样构造得出来 —— 那是 `AC-05` 点名的「恒零计数」，
    报了「我截断了」却报不出截了什么。
    """
    problems: list[str] = []
    status = _dig(payload, "status")
    stats = _dig(payload, "truncation_stats")
    if status is _MISSING or stats is _MISSING:
        problems.append("status 或 truncation_stats 键不存在，L-45 无从判起")
        return problems
    if not isinstance(stats, Mapping):
        problems.append(f"truncation_stats 应为映射，实际是 {type(stats).__name__}")
        return problems

    if status == ExtractionStatus.SUCCESS.name and stats:
        problems.append(
            f"status=SUCCESS 却带着非空的 truncation_stats {dict(stats)!r} —— "
            "被截断的抽取一律报 PARTIAL（L-45）"
        )
    if status == ExtractionStatus.PARTIAL.name:
        if not stats:
            problems.append("status=PARTIAL 但 truncation_stats 为空 —— 报不出截了多少（L-45）")
        elif not any(
            isinstance(v, int) and not isinstance(v, bool) and v > 0 for v in stats.values()
        ):
            problems.append(
                f"status=PARTIAL 而 truncation_stats {dict(stats)!r} 里没有一个正数 —— "
                "AC-05 点名的恒零计数：报了截断，却报不出截了什么"
            )
    return problems


@dataclass(frozen=True)
class CompletenessReport:
    """`AC-05` 的一次测量。**分子分母都进证据链**，不只给一个比率。

    只给比率的话，`0.98` 与 `49/50` 在复核者眼里是同一个数，
    而后者能直接问「少的那一条是哪条」。沿用 `D-029` 判据 4 的同一先例。
    """

    keys_checked: tuple[str, ...]
    filled: int
    total: int
    #: `(field_id, key, 原因)`。**逐条列出来**，不只报个数 ——
    #: 「25 条进去 24 条出来」在 JSON 里看不出少了谁，那是复核 `RV-3` 记的形状。
    gaps: tuple[tuple[str, str, str], ...]
    #: `(field_id, 原因)`。与 `gaps` 分开：**缺字段**和**字段之间自相矛盾**
    #: 是两类问题，合并成一个数就没法分别处置了。
    illegal: tuple[tuple[str, str], ...]

    @property
    def rate(self) -> Fraction:
        """齐全率。**空批次返回 0，不返回 1。**

        「一条记录都没有」不是「证据齐全」。返回 1 的话，一个什么都没抽到的批次
        会满足 `AC-05` —— 那正是这条标准写死计数口径要防的那种满足方式。
        """
        if self.total == 0:
            return Fraction(0)
        return Fraction(self.filled, self.total)

    def meets_ac05(self) -> bool:
        """`AC-05` 是**保证类**标准：齐全率 < 100% 即失败（`PROJECT_SPEC.md` §9.1）。"""
        return self.rate == 1 and not self.illegal

    def to_dict(self) -> dict:
        return {
            "keys_checked": list(self.keys_checked),
            "filled": self.filled,
            "total": self.total,
            "rate": f"{self.rate.numerator}/{self.rate.denominator}",
            "gaps": [
                {"field_id": fid, "key": key, "reason": reason} for fid, key, reason in self.gaps
            ],
            "illegal": [{"field_id": fid, "reason": reason} for fid, reason in self.illegal],
            "meets_ac05": self.meets_ac05(),
        }


def evidence_completeness(payloads: Sequence[Mapping]) -> CompletenessReport:
    """在**序列化后的证据链**上按 `AC-05` 写死的口径数一遍。

    ## 为什么判的是 payload 而不是 `ExtractionRecord` 对象

    因为在对象上这条检查**恒真**。`ExtractionRecord.__post_init__` 已经把
    每个文本字段 fail-closed 成非空（`L-34`），页码 fail-closed 成 `>= 1`，
    枚举 fail-closed 成成员 —— 一个能被构造出来的记录，对象层面必然「齐全」。
    在那上面数齐全率，得到的是一个**结构上只能是 100%** 的数字，
    而这正是 `AC-05` 的反面实证在讲的事。

    证据链是**给人读的 JSON**：它可以来自旧版本产物、来自手改的文件、
    来自一个还没有那些不变量的写入方。判据得在人真正拿到的那一层成立。
    """
    gaps: list[tuple[str, str, str]] = []
    illegal: list[tuple[str, str]] = []
    filled = 0
    total = 0
    for index, payload in enumerate(payloads):
        raw_id = _dig(payload, "field_id")
        if isinstance(raw_id, str) and raw_id.strip():
            where = raw_id
        else:
            where = f"<第 {index + 1} 条无 field_id>"
        for key in REQUIRED_EVIDENCE_KEYS:
            total += 1
            reason = _judge(payload, key)
            if reason is None:
                filled += 1
            else:
                gaps.append((where, key, reason))
        for problem in _truncation_problems(payload):
            illegal.append((where, problem))
    return CompletenessReport(
        keys_checked=REQUIRED_EVIDENCE_KEYS,
        filled=filled,
        total=total,
        gaps=tuple(gaps),
        illegal=tuple(illegal),
    )


def completeness_report(batch: ExtractionBatch) -> CompletenessReport:
    """一个批次的 `AC-05` 测量。序列化一次再数 —— 与复核者读到的是同一份东西。"""
    return evidence_completeness([record.to_dict() for record in batch.records])
