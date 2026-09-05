"""失败归因：从**机读状态**算出层，不从判分分支的措辞里捡（`EVAL_CASES` §5）。

## 为什么要单独一个模块

归因此前是**判分分支的副产品** —— 每个 `return CaseResult(...)` 里手写一个层名。
于是「这道题为什么归这一层」这个问题，答案散在七八个分支里，没法复核，
也没法验「换一套归因，分数一个字不变」（§5.1 的硬约束）。

## 判据只能是这三样（`EVAL_CASES` §5.3，硬约束）

1. **结构位置** —— `Answer.gate` 的三态（`not_reached` / `refused` / `passed`）
2. **口径标识** —— `metric_id` / `metric_version`，与 PDF 文本无关
3. **闸门返回值** —— `RefusalCode` 是封闭枚举

🔴 **不许拿 `detail` 的措辞做判据。** 理由写在 §5.3：上游排版每家每年都变，
靠措辞判出来的归因在排版一变时**静默退回「正常」**，而 §5.1 的
「归因不改分数」救不了它 —— 那条管「答错了不许赖」，管不到「根本没被判成答错」。

## 五层，不是四层（`D-035`，2026-09-05）

新增**意图层**：题面里的三元组没解析出来，闸门之后的四层一步都没走。
`EVAL_CASES` §5.4 此前写着「本轮不新增第五层（会动 `AC-08` 的口径）」——
**那个理由不成立**，`AC-08` 逐字对层数不置一词。真正会动它的是不加层：
2 / 4 条真实失败被硬塞进一个不对的层，那才让 100% 变成假的。

⚠️ **没有 `provisional` 字段。** `02-02-PLAN` 起草时它是必需的 ——
当时落点未裁，需要一个「临时落点 + 逐条登记」的通道。`D-035` 裁完之后
没有任何一条是临时的，**留一个永远为 `None` 的字段就是死抽象**。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from semantic_layer.resolve import RefusalCode  # noqa: E402

__all__ = [
    "LAYERS",
    "LAYER_INTENT",
    "LAYER_RETRIEVAL",
    "LAYER_DEFINITION",
    "LAYER_COMPUTATION",
    "LAYER_PRESENTATION",
    "FailureKind",
    "REFUSAL_LAYERS",
    "Attribution",
    "attribute",
]

LAYER_INTENT = "意图层"
LAYER_RETRIEVAL = "检索层"
LAYER_DEFINITION = "口径层"
LAYER_COMPUTATION = "计算层"
LAYER_PRESENTATION = "表达层"

#: 顺序即流水线顺序。意图层在最前 —— 它失败时后面四层一步都没走。
LAYERS: tuple = (
    LAYER_INTENT,
    LAYER_RETRIEVAL,
    LAYER_DEFINITION,
    LAYER_COMPUTATION,
    LAYER_PRESENTATION,
)


class FailureKind(Enum):
    """判分函数报的是「这次为什么判失败」，**不是层名**。

    层由本模块从机读状态算出来。判分函数只知道它比对的是什么对不上。
    """

    REFUSED_BUT_SHOULD_ANSWER = "期望数值，系统拒答了"
    ANSWERED_BUT_SHOULD_REFUSE = "期望拒答，系统给了答案"
    WRONG_REFUSAL_CODE = "拒答了，但理由码不是期望的那一支"
    NO_VALUE_NO_REFUSAL = "既没拒答也没给出数值"
    EXPECTED_NON_SCALAR = "标准答案是集合/多期结构，本路径只产单期标量"
    VALUE_OUT_OF_TOLERANCE = "数值不在题面声明的容差内"
    WRONG_METRIC = "数值对了但用的不是期望的那份口径"
    WRONG_VERSION = "口径对了但版本不是期望的那一版"


#: 每一支拒答码归哪一层。**全枚举穷举，没有兜底分支** ——
#: 加第十一支时 `tests/test_attribution.py` 先红，逼一次归因决策，
#: 而不是被一个兜底分支静默吸收（与 `resolve.py` 那两条锁枚举大小的测试同一个用意）。
REFUSAL_LAYERS: dict = {
    # —— 意图层：提问本身缺要素，闸门之后一步都没走 ——
    RefusalCode.INTENT_INCOMPLETE: (LAYER_INTENT,),
    # —— 口径层：口径产物（定义集、别名表、条件、版本）出的问题 ——
    #    `METRIC_NOT_DEFINED` 归这里而不是意图层：认不出这个说法，
    #    是**别名表**没覆盖，而别名表是口径产物（`D-035` ③ 划的边界）。
    RefusalCode.METRIC_NOT_DEFINED: (LAYER_DEFINITION,),
    RefusalCode.ALIAS_AMBIGUOUS: (LAYER_DEFINITION,),
    RefusalCode.DEFINITION_NONCONFORMANT: (LAYER_DEFINITION,),
    RefusalCode.UNDEFINED_CONDITION_HIT: (LAYER_DEFINITION,),
    RefusalCode.UNEVALUABLE_CONDITION: (LAYER_DEFINITION,),
    RefusalCode.CROSS_VERSION_COMPARISON: (LAYER_DEFINITION,),
    RefusalCode.CROSS_BASIS_VERSION_COMPARISON: (LAYER_DEFINITION,),
    # —— 检索层：该找的东西没找到 ——
    RefusalCode.UNAVAILABLE: (LAYER_RETRIEVAL,),
    # —— 双标签：勾稽不平说明至少有一个格子读错了，但它**分不出**是
    #    找错段落还是读错单元格（`EVAL_CASES` §5.4 第 ① 类逐字如此）。
    #    §5.2 允许多标签且明写「不选主要原因」⇒ 两个都记，不猜。
    RefusalCode.RECONCILIATION_FAILED: (LAYER_RETRIEVAL, LAYER_COMPUTATION),
}


@dataclass(frozen=True)
class Attribution:
    """一次归因。`basis` 说清它是**从哪个机读状态**算出来的。

    没有 `basis` 的话，复核者看到的是一个层名和一句「相信我」。
    """

    layers: tuple
    basis: str


def attribute(kind: FailureKind, answer=None) -> Attribution:
    """(为什么判失败, 这次的机读状态) → 落在哪一层。**纯函数。**

    `answer` 只在需要读 `RefusalCode` 时用到（`REFUSED_BUT_SHOULD_ANSWER`）。
    """
    if kind is FailureKind.REFUSED_BUT_SHOULD_ANSWER:
        code = _refusal_code(answer)
        if code is None:
            raise ValueError(
                "判成「期望数值却拒答了」，但这条答案里没有拒答码 —— "
                "归因的判据只能是机读状态，没有状态就不许猜一个层出来"
            )
        layers = REFUSAL_LAYERS.get(code)
        if layers is None:
            # 走不到：`test_attribution.py` 遍历整个枚举断言映射表齐全。
            # 留在这里是为了「万一」时**炸掉而不是静默归一个层**。
            raise KeyError(f"拒答码 {code.name} 没有归因落点 —— 加了新码却没定它归哪一层")
        return Attribution(layers, f"RefusalCode.{code.name}")

    if kind is FailureKind.ANSWERED_BUT_SHOULD_REFUSE:
        # 该拒未拒 —— `EVAL_CASES` §5.4 第 ③ 类，逐字归口径层
        return Attribution((LAYER_DEFINITION,), "该拒未拒（judging.refusal_expected）")
    if kind is FailureKind.WRONG_REFUSAL_CODE:
        # `D-035` ① —— 码就是对外可观测的判断本身，不是判断的排版
        return Attribution((LAYER_DEFINITION,), "拒答码与题面声明的不符")
    if kind is FailureKind.NO_VALUE_NO_REFUSAL:
        return Attribution((LAYER_COMPUTATION,), "既无 value 也无 refusal")
    if kind is FailureKind.EXPECTED_NON_SCALAR:
        return Attribution((LAYER_COMPUTATION,), "expected.value 是非标量结构")
    if kind is FailureKind.VALUE_OUT_OF_TOLERANCE:
        return Attribution((LAYER_COMPUTATION,), "value 超出 expected.tolerance")
    if kind is FailureKind.WRONG_METRIC:
        return Attribution((LAYER_DEFINITION,), "metric_id 与 expected 不符")
    if kind is FailureKind.WRONG_VERSION:
        return Attribution((LAYER_DEFINITION,), "metric_version 与 expected 不符")
    # 走不到：`FailureKind` 是封闭枚举，且有一条测试遍历它。
    raise KeyError(f"失败种类 {kind} 没有归因落点")


def reachable_layers() -> tuple:
    """当前实现**有可能吐出来**的层，由两张表机械算出，不是手写的一句话。

    区分这两件事很要紧：
    · **本批零产出** —— 这一次没有这类失败（比如没有一道题算错了数）
    · **结构上不可达** —— 当前实现里**没有任何一条路**能产出这个层

    前者是数据，后者是 `L-25` 那种死抽象。混成一句「零产出」，
    读的人会以为再多跑几批就有了 —— 而不可达的那个再跑一万批也不会有。
    """
    seen = set()
    for layers in REFUSAL_LAYERS.values():
        seen.update(layers)
    # `REFUSED_BUT_SHOULD_ANSWER` 已经在上面那一轮覆盖了（它的层来自拒答码）。
    class _无码:
        refusal = {"code": "UNDEFINED_CONDITION_HIT"}

    for kind in FailureKind:
        seen.update(attribute(kind, _无码()).layers)
    return tuple(layer for layer in LAYERS if layer in seen)


def _refusal_code(answer):
    """从 `Answer` 或 `Refusal` 里取出封闭枚举成员。**不碰 `detail`。**"""
    code = getattr(answer, "code", None)
    if isinstance(code, RefusalCode):
        return code
    refusal = getattr(answer, "refusal", None)
    if isinstance(refusal, dict) and refusal.get("code"):
        return RefusalCode[refusal["code"]]
    return None
