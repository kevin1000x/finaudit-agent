"""抽取记录的形状 —— D-019 / D-023 / D-024 的落地。

本模块只定义**形状与它的不变量**，不做任何抽取。这样安排的理由是 ARCHITECTURE §8.5
的核心发现：**指针只要是可选返回值，就一定会在接线时被丢掉**。所以出处不是「写入方
记得填」的字段，而是**构造时不填就构造不出来**的必需参数。

## 落在这里的四条决策

- **D-019** —— 页码拆成 `page`（数值行所在页）与 `anchor_page`（表标题锚点所在页），
  两个整数。一个数字不可能横跨两页，所以数值页天然是单值；真正跨页的是标题锚点。
- **D-023** —— 取数口径三元组 `selection = {sampling, order_key, truncation}` 作为
  D-019 的**显式扩展**进入记录，与两个页码同级，**不可为空**。不放批次级元数据：
  截断是行级事实，批次级表达不了「哪一行被截了」。
- **D-024** —— 批次身份键 = `(stock_code, fiscal_year)`；`batch_id` 由该二元组
  加该份 PDF 的 SHA-256 派生。派生式而非随机式，是为了满足 J-6「同一份年报重下
  得到同一个 `batch_id`」。
- **D-022** —— 配置缺陷抛异常，不变成 `Refusal`。本模块的全部校验失败都属配置缺陷
  （调用方把记录构造错了），故一律 `raise`。

## 落在这里的五条登记册条目

- **L-10** —— 抽取结果是**三态**：`got_value` / `absent` / `attempted_unknown`。
  第三态是「试过但判不出」，与「没试」和「试了发现整行不存在」都不同。
  **「行在、格子空」属 `got_value` 且值为 0，不属 `absent`** —— 这正是 SC-3 要区分的那条线，
  也是 A-2 实测出来的：茅台 2023 四个有息负债分项行在格子空，正确答案是 0 不是缺失。
- **L-14** —— 三个正交事实**各占独立字段，不互相嵌套**：
  「取到数了」（`retrieval`）/「口径已确认」（`basis_confirmation`）/
  「数据源新鲜」（`source_freshness`）。嵌套会让「口径没确认」被读成「没取到数」。
- **L-34** —— 口径类开关（`unit` / `currency` / `mapping_version`）**不设默认值**，
  缺失即在构造边界 fail-closed。取一个「合理默认」正是这条要防的。
- **L-35** —— 记录的类别由**显式 `kind` 字段**判定。本模块不提供任何从标签文本或
  数值形状反推 `kind` 的入口，「看起来像三大表某一行」这类启发式在这里无处落脚。
- **L-44** —— 集合型字段的**合并语义写进 schema**（`MERGE_SEMANTICS`），
  不由写入方临时决定覆盖还是追加。未登记的集合型字段由测试报红。
- **L-45** —— 被截断的抽取报 `PARTIAL` 且 `truncation_stats` 非空，**永远不报 `SUCCESS`**。
  报成功的话证据链里根本不会出现 `truncation_stats`，AC-05 的字段齐全率会在一个假成功上判过。

## 本模块明确**不**保证什么

- 不保证 `value` 取自正确的那一列。列的正确性靠映射表条目的 `column_header` 显式绑定
  （D-016 补充节），本模块只忠实记录 `column_header` 是什么，不校验它对不对。
- 不保证 `page` / `anchor_page` 指向的页上真的印着这个数。那是 `locate` 的事。
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, fields
from decimal import Decimal
from enum import Enum
from typing import Any, ClassVar, Mapping

__all__ = [
    "RecordKind",
    "ExtractionStatus",
    "CellState",
    "RetrievalOutcome",
    "BasisConfirmation",
    "SourceFreshness",
    "MergeSemantics",
    "Selection",
    "ExtractionRecord",
    "ExtractionBatch",
    "make_batch_id",
]

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class RecordKind(Enum):
    """记录的类别。**只能由映射表条目的 `kind` 字段带出来**（L-35）。

    本枚举刻意不提供 `from_label()` 之类的构造器：一旦存在「由文本猜类别」的入口，
    形状启发式就有了落脚点，而 cninfo 的 `extract_financial_statements()`
    「最后一个匹配的表静默胜出」正是这么来的。
    """

    STATEMENT_LINE = "三大表的行项目"
    NOTE_CHECKBOX = "附注披露模板的适用性标记"
    KPI_DISCLOSED = "年报「主要会计数据和财务指标」章节的已披露值"

    # 下面两支由 wave 2 的实测逼出来（`docs/agent/phase-01.5/PROBE-14.md` §3 / §7 第 3 条）。
    # 它们与上面三支的**结构差别**是：上面三支都从「某一行取某一列的值」，
    # 这两支根本不取行值。硬把它们塞进 STATEMENT_LINE，就得给它们编一条
    # 必然零命中的 `label_variants` —— 那是 F-2 的形状，而且会与 L-36
    # 「整份 PDF 零命中即整批失败」直接对撞。

    COLUMN_HEADER_PRESENCE = "判某个列头在不在，不取任何行的值"
    REPORT_METADATA = "由报告类型决定的元数据，纸上不印这一行"


class ExtractionStatus(Enum):
    """**这次抽取本身**的成败。与 `CellState`（格子的事实）正交。"""

    SUCCESS = "抽取完整完成"
    PARTIAL = "抽取被截断，产物不完整"
    REFUSED = "抽取被拒答，无产物"


class CellState(Enum):
    """**格子的事实**。与 `ExtractionStatus`（这次抽取的成败）正交。

    `EMPTY_CELL` 与 `ROW_ABSENT` 的区分就是 SC-3：前者是「披露了这一行，本期为零」，
    后者是「这张表根本没有这一行」。把两者混成一个「缺失」，
    有息负债率会在一家真的没有有息负债的公司上拒答（A-2 实测）。
    """

    VALUE_PRESENT = "行在，格子里有数"
    EMPTY_CELL = "行在，格子空"
    ROW_ABSENT = "整行不存在"


class RetrievalOutcome(Enum):
    """L-10 的三态。**第三态不是凑数的**。

    `ATTEMPTED_UNKNOWN` 是「锚点定位到了、行也扫过了，但判不出这一行是空格子
    还是根本不存在」。没有这一态，实现只能在两个已知态里挑一个报——
    那是拿手边能求值的东西凑一个答案，正是 F-2 的形状。
    三态不在一开始设计进去，事后加会改动所有已产出的记录。
    """

    GOT_VALUE = "got_value"
    ABSENT = "absent"
    ATTEMPTED_UNKNOWN = "attempted_unknown"


class BasisConfirmation(Enum):
    """L-14 的第二个正交事实：这条记录的**口径**是否已确认。

    与「取到数了」独立：一个数可以取到了但口径未确认（例如列绑定是从上一页继承来的）。
    """

    CONFIRMED = "映射表条目与列表头均已显式绑定"
    UNCONFIRMED = "口径存在未确认之处，结论不得据此产出"


class SourceFreshness(Enum):
    """L-14 的第三个正交事实：数据源的新鲜度。

    `UNKNOWN` 是**如实声明判不出**，不是默认值——它必须由调用方显式传入。
    """

    FETCHED_THIS_RUN = "本次运行内从上游取回"
    REUSED_CACHED = "复用先前取回的产物"
    UNKNOWN = "无法判定取回时点"


class MergeSemantics(Enum):
    """L-44：集合型字段在 schema 层声明合并语义，不由写入方各写各的。"""

    REPLACE = "整体覆盖"
    APPEND = "追加，不丢弃已有项"


def _require_text(value: Any, name: str) -> str:
    """必需的非空文本。**不接受 `None`、不接受空串、不 strip 出空串。**"""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"{name} 必须是非空字符串，实际是 {value!r}。"
            "这里不补默认值：口径类开关缺失即在构造边界 fail-closed（L-34）。"
        )
    return value


def _require_page(value: Any, name: str) -> int:
    """页码必须是 ≥ 1 的整数。**`bool` 不算整数**（`True == 1` 会静默过关）。"""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} 必须是整数，实际是 {value!r}（D-019 要求两个整数）")
    if value < 1:
        raise ValueError(f"{name} 必须 ≥ 1，实际是 {value}")
    return value


@dataclass(frozen=True)
class Selection:
    """取数口径三元组（D-023 / L-2 / J-7）。三个子字段**缺一即构造失败**。

    「整表逐行读时三个都是固定值、像噪音」这条反对已在 D-023 里答复过：
    `sampling="full"` 陈述的是「这是整表」，本身是信息。
    """

    sampling: str
    order_key: str
    truncation: str

    def __post_init__(self) -> None:
        # 三个都是**必需位置参数**，省略任一个是 TypeError（Python 层面）；
        # 传空串则由这里拦下 —— 「填了个空的」与「没填」在证据链里同样无用。
        _require_text(self.sampling, "selection.sampling")
        _require_text(self.order_key, "selection.order_key")
        _require_text(self.truncation, "selection.truncation")

    def to_dict(self) -> dict:
        return {
            "sampling": self.sampling,
            "order_key": self.order_key,
            "truncation": self.truncation,
        }


def make_batch_id(stock_code: str, fiscal_year: int, pdf_sha256: str) -> str:
    """`(stock_code, fiscal_year, pdf_sha256)` 的**确定性**函数（D-024 判据 1）。

    同输入两次调用同输出 —— 这是 J-6 要的「可逐字比对的稳定标识」。
    **不用随机数、不用时间戳**：那样同一份年报重下会得到两个 id，
    复核者拿着旧报告里的 id 在新产物里找不到对应记录。
    """
    _require_text(stock_code, "stock_code")
    if isinstance(fiscal_year, bool) or not isinstance(fiscal_year, int):
        raise ValueError(f"fiscal_year 必须是整数，实际是 {fiscal_year!r}")
    _require_text(pdf_sha256, "pdf_sha256")
    if not _SHA256_RE.match(pdf_sha256):
        raise ValueError(
            f"pdf_sha256 必须是 64 位小写十六进制，实际是 {pdf_sha256!r}。"
            "批次身份由它派生，形状不对就等于身份不可复算（D-024）。"
        )
    payload = f"{stock_code}:{fiscal_year}:{pdf_sha256}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class ExtractionRecord:
    """一个字段的一次抽取，连同**一次独立复核所需的全部出处**。

    全部字段都是**必需位置参数，没有一个有默认值**。这不是风格选择：
    有默认值的出处字段等价于可选出处，而 ARCHITECTURE §8.5 的实证是
    可选出处一定会在接线时被丢掉（hello-agents 的 `full_output_path`
    形状完全正确、只有 30 行，唯二两个调用点全部丢弃，全包零处读回）。
    """

    field_id: str
    kind: RecordKind
    value: Decimal | str | None
    status: ExtractionStatus
    # 三个正交事实，**平铺三个字段，互不嵌套**（L-14）
    retrieval: RetrievalOutcome
    basis_confirmation: BasisConfirmation
    source_freshness: SourceFreshness
    # 格子的事实。`ATTEMPTED_UNKNOWN` 时**只能**是 None —— 判不出就如实说判不出，
    # 在三个已知态里挑一个报就是 F-2。这里没有默认值，None 必须显式传。
    cell_state: CellState | None
    page: int
    anchor_page: int
    pdf_sha256: str
    source_url: str
    unit: str
    currency: str
    column_header: str
    #: 这一行的列归属是不是**从首页表头继承来的**。
    #:
    #: 它是 `ColumnBinding.header_inherited` 的下游消费点。加这个字段是因为
    #: 2026-08-27 写列绑定回归时当场发现：`inherited_to()` 把这个布尔算了出来，
    #: 而 `_stamp_provenance` 只取了 `column.header_text` —— **算出来的留证在接线时被丢掉**。
    #: 那正是 `ARCHITECTURE` §8.5 记的形状：指针只要不是必填参数，就会在接线时被丢掉。
    #:
    #: 为什么这件事非记不可：cninfo `pdf_parser.py:302` 无条件把第 0 行当表头，
    #: 续页因此**静默吃掉一行真实数据**，而它的文档宣称「支持跨页表格识别」。
    #: 继承是允许的，但**继承这件事本身必须在证据里看得见**。
    header_inherited: bool
    mapping_version: int
    selection: Selection
    truncation_stats: Mapping[str, int]
    batch_id: str

    # L-44：集合型字段的合并语义写在 schema 里，**不由写入方临时决定**覆盖还是追加。
    # `ClassVar` 而非字段：它是 schema 的一部分，不是某条记录的数据。
    # 未登记的集合型字段由 `tests/test_record.py` 报红，不靠写入方自觉。
    MERGE_SEMANTICS: ClassVar[Mapping[str, MergeSemantics]] = {
        "truncation_stats": MergeSemantics.REPLACE,
    }

    def __post_init__(self) -> None:
        _require_text(self.field_id, "field_id")
        if not isinstance(self.kind, RecordKind):
            raise ValueError(
                f"kind 必须是 RecordKind 成员，实际是 {self.kind!r}。"
                "类别只能由映射表条目显式带出来，不许由形状反推（L-35）。"
            )
        if not isinstance(self.status, ExtractionStatus):
            raise ValueError(f"status 必须是 ExtractionStatus 成员，实际是 {self.status!r}")
        if not isinstance(self.retrieval, RetrievalOutcome):
            raise ValueError(f"retrieval 必须是 RetrievalOutcome 成员，实际是 {self.retrieval!r}")
        if not isinstance(self.basis_confirmation, BasisConfirmation):
            raise ValueError(
                f"basis_confirmation 必须是 BasisConfirmation 成员，实际是 {self.basis_confirmation!r}"
            )
        if not isinstance(self.source_freshness, SourceFreshness):
            raise ValueError(
                f"source_freshness 必须是 SourceFreshness 成员，实际是 {self.source_freshness!r}"
            )

        _require_page(self.page, "page")
        _require_page(self.anchor_page, "anchor_page")
        _require_text(self.pdf_sha256, "pdf_sha256")
        if not _SHA256_RE.match(self.pdf_sha256):
            raise ValueError(f"pdf_sha256 必须是 64 位小写十六进制，实际是 {self.pdf_sha256!r}")
        _require_text(self.source_url, "source_url")
        _require_text(self.unit, "unit")
        _require_text(self.currency, "currency")
        _require_text(self.column_header, "column_header")
        _require_text(self.batch_id, "batch_id")

        if isinstance(self.mapping_version, bool) or not isinstance(self.mapping_version, int):
            raise ValueError(f"mapping_version 必须是整数，实际是 {self.mapping_version!r}")
        if self.mapping_version < 1:
            raise ValueError(
                f"mapping_version 必须 ≥ 1，实际是 {self.mapping_version}。"
                "口径版本随记录一起冻结，复核按记录里的版本求值（L-38）。"
            )

        if not isinstance(self.selection, Selection):
            raise ValueError(
                f"selection 必须是 Selection 实例，实际是 {self.selection!r}。"
                "取数口径三元组不可为空，也不接受一个形状相似的字典（D-023 判据 1）。"
            )

        if not isinstance(self.truncation_stats, Mapping):
            raise ValueError(f"truncation_stats 必须是映射，实际是 {self.truncation_stats!r}")

        self._check_truncation_coherence()
        self._check_state_coherence()

    # -- 不变量 ------------------------------------------------------------

    def _check_truncation_coherence(self) -> None:
        """L-45：截断与状态的双向绑定。

        两个方向都要拦。只拦一个方向的话，「报 SUCCESS 但其实截了」这条
        （即 L-45 点名的那条）就漏了。
        """
        if self.status is ExtractionStatus.PARTIAL and not self.truncation_stats:
            raise ValueError(
                "status 是 PARTIAL 但 truncation_stats 为空。"
                "被截断必须报得出截了多少，否则 AC-05 的字段齐全率会在一个假成功上判过（L-45）。"
            )
        if self.status is ExtractionStatus.SUCCESS and self.truncation_stats:
            raise ValueError(
                "status 是 SUCCESS 却带着非空的 truncation_stats。"
                "被截断的抽取一律报 PARTIAL，不许报 SUCCESS（L-45）。"
            )

    def _check_state_coherence(self) -> None:
        """三态与格子事实的绑定（L-10 / SC-3 / A-2）。"""
        if self.retrieval is RetrievalOutcome.ATTEMPTED_UNKNOWN:
            if self.cell_state is not None:
                raise ValueError(
                    "retrieval 是 attempted_unknown，cell_state 只能是 None。"
                    "判不出就如实说判不出，在三个已知态里挑一个报是 F-2 的形状。"
                )
            if self.value is not None:
                raise ValueError("retrieval 是 attempted_unknown 时不得带值")
            return

        if self.cell_state is None:
            raise ValueError(
                f"retrieval 是 {self.retrieval.value} 时 cell_state 不得为 None"
            )

        if self.cell_state is CellState.VALUE_PRESENT:
            if self.retrieval is not RetrievalOutcome.GOT_VALUE:
                raise ValueError("cell_state 是 VALUE_PRESENT 时 retrieval 必须是 got_value")
            if self.value is None:
                raise ValueError("cell_state 是 VALUE_PRESENT 时必须带值")
        elif self.cell_state is CellState.EMPTY_CELL:
            # SC-3 的那条线：行在、格子空 = 披露了这一行且本期为零。
            # 它属 got_value 且值为 0，**不属 absent**（A-2）。
            if self.retrieval is not RetrievalOutcome.GOT_VALUE:
                raise ValueError(
                    "cell_state 是 EMPTY_CELL 时 retrieval 必须是 got_value —— "
                    "「行在格子空」是取到了一个零，不是没取到（SC-3 / A-2）"
                )
            if self.value != Decimal(0):
                raise ValueError(f"cell_state 是 EMPTY_CELL 时值必须是 0，实际是 {self.value!r}")
        elif self.cell_state is CellState.ROW_ABSENT:
            if self.retrieval is not RetrievalOutcome.ABSENT:
                raise ValueError("cell_state 是 ROW_ABSENT 时 retrieval 必须是 absent")
            if self.value is not None:
                raise ValueError("cell_state 是 ROW_ABSENT 时不得带值")

    # -- 序列化 ------------------------------------------------------------

    def to_dict(self) -> dict:
        """键名照抄 `semantic_layer.resolve.Refusal.to_dict()` 的风格，不另起一套。"""
        return {
            "field_id": self.field_id,
            "kind": self.kind.name,
            "value": None if self.value is None else str(self.value),
            "status": self.status.name,
            "retrieval": self.retrieval.value,
            "basis_confirmation": self.basis_confirmation.name,
            "source_freshness": self.source_freshness.name,
            "cell_state": None if self.cell_state is None else self.cell_state.name,
            "page": self.page,
            "anchor_page": self.anchor_page,
            "pdf_sha256": self.pdf_sha256,
            "source_url": self.source_url,
            "unit": self.unit,
            "currency": self.currency,
            "column_header": self.column_header,
            "mapping_version": self.mapping_version,
            "selection": self.selection.to_dict(),
            "truncation_stats": dict(self.truncation_stats),
            "batch_id": self.batch_id,
        }



@dataclass
class ExtractionBatch:
    """一次抽取批次。身份键是 `(entity, period)`，即 `(stock_code, fiscal_year)`（D-024）。

    批次是**可变的**（要往里加记录），但一旦 `seal()` 就闩死：
    L-13 要求重试不得跨闸门批次，重试必须从新批次开始，
    否则重试成功的部分会与失败的部分混进同一次回答。
    """

    batch_id: str
    entity: str  # stock_code
    period: int  # fiscal_year
    pdf_sha256: str
    records: list[ExtractionRecord] = field(default_factory=list)
    reconciliation: Any = None
    sealed: bool = False
    #: 抽取时刻 `metrics/` 里每份定义的 `version` 快照（`L-38`）。
    #:
    #: **为什么快照放批次而不是放每条记录**：`version` 是**指标**的属性，
    #: 而记录是**字段**级的 —— 一个字段可以被多个指标引用，把指标版本塞进字段记录
    #: 就得在每条记录里存一张表，那是同一事实的多个结构表示。
    #:
    #: **为什么必须冻结**：`L-38` 原话是「复核时按记录里的版本求值，而非按当前配置」。
    #: 不冻结的话，同一条证据在两个时间点复核会得到不同结果 ——
    #: `D-012` 的冻结就失去意义了。
    #:
    #: 空 dict 表示**这批没做快照**，与「快照里没有这个指标」是两回事：
    #: 前者是历史批次（快照机制上线前建的），后者是这个指标当时就不存在。
    #: 两者的处置不同，所以不合并成一个「取不到」。
    definition_versions: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_text(self.batch_id, "batch_id")
        _require_text(self.entity, "entity")
        if isinstance(self.period, bool) or not isinstance(self.period, int):
            raise ValueError(f"period 必须是整数（会计年度），实际是 {self.period!r}")
        expected = make_batch_id(self.entity, self.period, self.pdf_sha256)
        if self.batch_id != expected:
            raise ValueError(
                f"batch_id {self.batch_id!r} 与 (entity, period, pdf_sha256) 派生出的 "
                f"{expected!r} 不一致。身份必须活在数据里，不许活在人脑里（D-024）。"
            )

    @classmethod
    def open(
        cls,
        entity: str,
        period: int,
        pdf_sha256: str,
        definition_versions: Mapping[str, int] | None = None,
    ) -> "ExtractionBatch":
        return cls(
            batch_id=make_batch_id(entity, period, pdf_sha256),
            entity=entity,
            period=period,
            pdf_sha256=pdf_sha256,
            definition_versions=dict(definition_versions or {}),
        )

    def add_record(self, record: ExtractionRecord) -> None:
        """加一条记录。**批次已闩死时拒绝**，**记录不属本批次时拒绝**。

        第二条拦的是 D-024 判据 2 的反面：两家公司的记录混进同一个批次。
        """
        if self.sealed:
            raise ValueError(
                f"批次 {self.batch_id} 已闩死，不接受追加。"
                "重试必须从新批次开始 —— 重试成功的部分与失败的部分不得混进同一次回答（L-13）。"
            )
        if record.batch_id != self.batch_id:
            raise ValueError(
                f"记录 {record.field_id!r} 的 batch_id {record.batch_id!r} "
                f"不属批次 {self.batch_id!r}"
            )
        self.records.append(record)

    def seal(self, reconciliation: Any) -> None:
        """闸门判定完就闩死。之后 `add_record` 一律拒绝。"""
        if self.sealed:
            raise ValueError(f"批次 {self.batch_id} 已经闩死过一次，不允许重复闩")
        self.reconciliation = reconciliation
        self.sealed = True

    def by_field(self, field_id: str) -> ExtractionRecord | None:
        for record in self.records:
            if record.field_id == field_id:
                return record
        return None


def _collection_typed_fields() -> list[str]:
    """`ExtractionRecord` 里类型上是集合的字段名。L-44 的检查对象。"""
    out = []
    for f in fields(ExtractionRecord):
        annotation = str(f.type)
        if any(token in annotation for token in ("Mapping", "list[", "set[", "dict[", "tuple[")):
            out.append(f.name)
    return out
