"""批次级勾稽闸门（D-018）—— 对一次抽取批次整体跑一次，不嵌进指标的计算路径。

## 为什么是批次级

勾稽是**报表的性质**，不是某个指标的性质。嵌进每个指标的计算路径会有两个后果：
对同一批数据重复跑 N 次；失败时归因混乱（到底是这个指标的问题还是这批数据的问题）。
所以它跑一次，结果写进 `ExtractionBatch.reconciliation`，
计算层在**读入边界**读它（D-018 / ARCHITECTURE §8.4）。

## 这道闸门**证明不了**什么

必须写在这里，因为它是本项目自己设计里的第四个
「自证机制说通过了，但它证明的不是它声称证明的事」的实例（台账 A-9 原话）：

- 恒等式在**期末列**与**期初列**上都成立。三个数**全取自期初列**时它照样放行。
- 三个数全取自母公司报表时它也照样放行 —— 母公司表自己也是自洽的。

**它证明的是「同一列内部自洽」，不是「取的是对的那一列」。**
列的正确性靠 D-016 补充节的 `column_header` 绑定（`locate.bind_columns` 的显式判定
与 `ColumnBinding.resolution` 留证），二者**不可互相替代**。
A-9 明确要求列绑定的验收「单独跑勾稽闸门不足以让它通过」。

## 闩住整批（L-13）

判定完就 `seal()`。之后 `add_record` 一律拒绝：重试必须从新批次开始，
否则重试成功的部分会与失败的部分混进同一次回答。
证据提交点是分界线 —— 提交之前失败就作废整个结论、返回拒答，
不许「先给答案后补证据」；提交之后下游失败不得回改已提交的证据
（ARCHITECTURE §8.5.1）。
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from . import locate
from .record import CellState, ExtractionBatch, RecordKind, RetrievalOutcome

__all__ = [
    "BALANCE_SHEET_IDENTITY",
    "IDENTITY_FIELDS",
    "DEFAULT_TOLERANCE",
    "SOURCE_RECONCILE",
    "SOURCE_COLUMN_BINDING",
    "ReconcileResult",
    "ColumnBindingResult",
    "reconcile_batch",
    "check_column_binding",
]

#: 恒等式的**原文**。进证据链时逐字原样展示，不重新拼。
BALANCE_SHEET_IDENTITY = "bs.total_assets = bs.total_liabilities + bs.total_equity"

IDENTITY_FIELDS = ("bs.total_assets", "bs.total_liabilities", "bs.total_equity")

#: 报表精确到分，容差取一分。**不放宽**：放宽到元就盖得住一整类归类错误。
DEFAULT_TOLERANCE = Decimal("0.01")

#: 责任方标识（L-9）。稳定串，可逐字比对（J-6）。
SOURCE_RECONCILE = "reconcile:balance_sheet_identity"


@dataclass(frozen=True)
class ReconcileResult:
    """一次闸门判定的完整留证。

    `missing_fields` 是计划里没有列出的第七个字段，加它的理由：恒等式的三项
    只要缺一项就**算不出** `left` / `right`，而这三个字段的类型是 `Decimal`。
    不加这个字段的话，实现只能在缺项时随便填个 0 —— 那就等于把「取不到数」
    伪装成「差额为零」，正是这道闸门要防的那类静默。
    """

    passed: bool
    identity: str
    left: Decimal | None
    right: Decimal | None
    difference: Decimal | None
    tolerance: Decimal
    missing_fields: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "identity": self.identity,
            "left": None if self.left is None else str(self.left),
            "right": None if self.right is None else str(self.right),
            "difference": None if self.difference is None else str(self.difference),
            "tolerance": str(self.tolerance),
            "missing_fields": list(self.missing_fields),
            "source": SOURCE_RECONCILE,
        }


def _readable_amount(batch: ExtractionBatch, field_id: str) -> Decimal | None:
    """能参与恒等式的数值；取不到即 None。

    `EMPTY_CELL`（行在、格子空）按 0 参与 —— 那是「披露了这一行且本期为零」，
    不是缺失（SC-3 / A-2）。`ROW_ABSENT` 与 `ATTEMPTED_UNKNOWN` 一律取不到，
    **不当 0**：当 0 会让一张缺了负债合计的报表在恒等式上「差额 = 权益」而被
    如实报为不通过，看起来像数据错，实际是我们没取到 —— 归因就此错位。
    """
    record = batch.by_field(field_id)
    if record is None:
        return None
    if record.retrieval is RetrievalOutcome.ATTEMPTED_UNKNOWN:
        return None
    if record.cell_state is CellState.ROW_ABSENT:
        return None
    if record.cell_state is CellState.EMPTY_CELL:
        return Decimal(0)
    if not isinstance(record.value, Decimal):
        return None
    return record.value


def reconcile_batch(
    batch: ExtractionBatch,
    tolerance: Decimal = DEFAULT_TOLERANCE,
    seal: bool = True,
) -> ReconcileResult:
    """对**一次抽取批次整体**跑一次「资产总计 = 负债合计 + 所有者权益合计」。

    判定完就把结果写进批次并闩死（`seal=False` 只在测试里用，
    因为 `ExtractionBatch.seal` 拒绝重复闩）。
    """
    values = {f: _readable_amount(batch, f) for f in IDENTITY_FIELDS}
    missing = tuple(f for f, v in values.items() if v is None)

    if missing:
        result = ReconcileResult(
            passed=False,
            identity=BALANCE_SHEET_IDENTITY,
            left=None,
            right=None,
            difference=None,
            tolerance=tolerance,
            missing_fields=missing,
        )
    else:
        left = values["bs.total_assets"]
        right = values["bs.total_liabilities"] + values["bs.total_equity"]
        difference = left - right
        result = ReconcileResult(
            passed=abs(difference) <= tolerance,
            identity=BALANCE_SHEET_IDENTITY,
            left=left,
            right=right,
            difference=difference,
            tolerance=tolerance,
        )

    if seal:
        batch.seal(result)
    return result


# --------------------------------------------------------------------------
# 列绑定校验 —— 与勾稽闸门**并列且不可互相替代**（D-016 补充节 / A-9）
# --------------------------------------------------------------------------

#: 责任方标识（L-9）。与 `SOURCE_RECONCILE` 分开：两道闸门失败时归因不同。
SOURCE_COLUMN_BINDING = "reconcile:column_binding"


@dataclass(frozen=True)
class ColumnBindingResult:
    """一次列绑定判定的完整留证。

    `mismatches` 的每一项是 `(field_id, 版面上印的列头, 解出来的口径, 映射表要的口径)`
    —— 四样都留，因为「取错列」的复核**必须能看到版面原文**：
    只报「口径不符」的话，复核者无法判断是抽取器解错了还是映射表写错了。
    """

    passed: bool
    checked: int
    mismatches: tuple[tuple[str, str, str | None, str], ...] = ()
    #: `(field_id, 理由)` —— **被判定为「这条记录没有取数列可查」的记录**。
    #:
    #: 为什么要单列一栏而不是默默 `continue`：`checked` 只报「查了几条」，
    #: 一个静默跳过的字段在证据里与「不存在这个字段」**完全不可区分**。
    #: 这正是复核 `RV-3` 记的形状（批次 25 条进去 24 条出来，JSON 里看不出少了谁）。
    not_applicable: tuple[tuple[str, str], ...] = ()

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "checked": self.checked,
            "mismatches": [list(m) for m in self.mismatches],
            "not_applicable": [list(x) for x in self.not_applicable],
            "source": SOURCE_COLUMN_BINDING,
        }


def check_column_binding(
    batch: ExtractionBatch, mapping, fiscal_year: int
) -> ColumnBindingResult:
    """每条记录**版面上印的那列**，解回口径后是否等于映射表要的那一列。

    ## 为什么这道闸门不能被勾稽闸门替代

    `A-9` 的推论在真实数据上**确凿成立**（茅台 2023 实测）：

        期末列：272,699,660,092.25 = 49,043,190,797.43 + 223,656,469,294.82  差额 0.00
        期初列：254,500,826,096.02 = 49,562,744,832.16 + 204,938,081,263.86  差额 0.00

    三个数**全取期初列**时，`reconcile_batch` 照样 `passed=True`。
    **勾稽证明的是「同一列内部自洽」，不是「取的是对的那一列」。**

    ## 判定方式是事实比对，不是启发式

    记录里存的 `column_header` 是**版面上印的那串字**（如 `2023年12月31日`），
    不是口径名。这里把它交给 `locate.role_of` 用**本次抽取的会计年度**重新解一次，
    再与映射表条目声明的 `column_header`（口径名）逐字比对。
    会计年度是调用方传进来的已知量 —— 全程没有「取靠右那一列」这类位置约定。

    ## 不判定的情况

    映射表里没有对应条目的记录、以及 `column_header` 为 `None` 的记录（不取列的类别）
    **不计入 `checked`**。把它们算成通过会让 `checked` 变成一个虚高的数。

    `COLUMN_HEADER_PRESENCE` 的记录**也不计入**，但它与上面两类不同：它的
    `column_header` **非空**，只是语义相反（是「找的哪个列头」不是「取的哪一列」）。
    这一类**逐条记进 `not_applicable` 并给出理由**，不静默 `continue` ——
    静默跳过的字段在证据里与「不存在这个字段」不可区分（复核 `RV-3` 的形状）。
    """
    mismatches: list[tuple[str, str, str | None, str]] = []
    not_applicable: list[tuple[str, str]] = []
    checked = 0
    for record in batch.records:
        entry = mapping.by_field(record.field_id)
        if entry is None or entry.column_header is None:
            continue
        if record.column_header is None:
            continue
        if record.kind is RecordKind.COLUMN_HEADER_PRESENCE:
            # ⚠️ **这一支的 `column_header` 语义与行值类相反**，
            # 拿 `role_of` 去解它必然解出 `None` 并报一条**假的**不符。
            #
            # 行值类记的是「我从哪一列取的数」（版面上印的 `2023年12月31日`）；
            # 这一支记的是「**我找的是哪个列头**」（`调整后`），
            # 而这条记录的**值**就是「找到了没有」——它压根没有「取数列」这回事。
            # ⇒ 本闸门问的那个问题（「取的是不是对的那一列」）在它身上**不成立**。
            #
            # 2026-08-31 接线时当场炸出来的：接上之后 notes 命名空间立刻报
            # `passed=false`，唯一的 mismatch 是 `(notes.restatement_flag, 调整后, null, 调整后)`
            # —— 版面串与要的口径**逐字相同**却判不符，这本身就是判据用错了对象的信号。
            not_applicable.append(
                (
                    record.field_id,
                    "COLUMN_HEADER_PRESENCE：column_header 是被判存在性的那个列头，"
                    "不是取数列，本闸门的判据在它身上不成立",
                )
            )
            continue
        checked += 1
        resolved, _resolution = locate.role_of(record.column_header, fiscal_year)
        if resolved != entry.column_header:
            mismatches.append(
                (record.field_id, record.column_header, resolved, entry.column_header)
            )
    return ColumnBindingResult(
        passed=not mismatches,
        checked=checked,
        mismatches=tuple(mismatches),
        not_applicable=tuple(not_applicable),
    )
