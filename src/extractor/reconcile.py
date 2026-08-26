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

from .record import CellState, ExtractionBatch, RetrievalOutcome

__all__ = [
    "BALANCE_SHEET_IDENTITY",
    "IDENTITY_FIELDS",
    "DEFAULT_TOLERANCE",
    "SOURCE_RECONCILE",
    "ReconcileResult",
    "reconcile_batch",
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
