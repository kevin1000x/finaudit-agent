"""计量单位与币种 —— **口径类开关，缺失即 fail-closed，不设默认值**（`L-34` / SC-4）。

## 为什么单独成一个模块

它是**跨源比较的前置步骤**，不是阈值问题的一部分（`01.5-RESEARCH.md` Q3 明确要求
把这两件事分开讨论）。把「单位不可比」混进「数值不一致」里，
`source_disagreement` 会在单位错配时**几乎全部触发**，
而那时看到的噪音会被当成数据质量问题去查 —— 查错方向。

**顺序是硬的**：先归一化，再比较。不先归一化的比较几乎全部误判为不一致。

## 为什么抽不到就抛错

`L-34` 的原话是「口径类开关（口径版本 / 抽样策略 / 单位换算）**不设默认值**，
缺失即在读入边界 fail-closed」。

「单位大概是元」这个默认看起来永远安全 —— 直到遇到一份以**万元**列报的报表。
那时每个数都小 10000 倍，**而没有任何东西会报错**：
资产负债表照样平（等式两边同时缩小 10000 倍），比率照样对（约掉了），
只有绝对金额是错的，且错得像一个正常的数。

⇒ 抽不到单位就 `UnitMismatchError`，**不猜**。

## 取值域穷举，不做「看起来像」的推断

`UnitScale` 只有三个成员，全部来自 A 股年报实际使用的列报单位。
**没有 `UNKNOWN` 成员** —— 加一个「未知」等于给调用方一个可以往下走的值，
而这里要的恰恰是走不下去。未知的表达方式是**抛异常**，不是一个枚举值。
"""

from __future__ import annotations

import re
from decimal import Decimal
from enum import Enum

__all__ = [
    "UnitScale",
    "UnitMismatchError",
    "parse_unit_header",
    "to_yuan",
    "same_scale",
]


class UnitScale(Enum):
    """列报单位。**值是「一单位等于多少元」的换算系数**，不是显示名。

    把系数放进枚举值而不是另建一张映射表：同名口径常量只允许一个定义点（`L-39`），
    而「元 / 万元 / 亿元」与它们的系数是同一个事实的两半，拆成两处就会分叉。
    """

    YUAN = Decimal(1)
    WAN_YUAN = Decimal(10_000)
    YI_YUAN = Decimal(100_000_000)

    @property
    def printed(self) -> str:
        """版面上印的那个词。归一化时用它逐字比对，不用枚举成员名。"""
        return {
            UnitScale.YUAN: "元",
            UnitScale.WAN_YUAN: "万元",
            UnitScale.YI_YUAN: "亿元",
        }[self]


class UnitMismatchError(ValueError):
    """单位读不出来，或两个要一起运算的量单位不同。

    **不是「返回一个默认单位」的替代品，是它的反面。**
    读不出来和读出「元」是两回事 —— 混同它们，一份以万元列报的报表
    会静默地产出小 10000 倍的绝对金额，而没有任何检查会不通过。
    """


#: 版面上印的单位词 → 换算系数。**逐字相等**，不做子串包含。
#:
#: ⚠️ 顺序在这里不重要（是个 dict 不是正则轮询），但**「万元」不能靠「元」的子串匹配**
#: 命中 —— 那正是 cninfo 用子串匹配对齐列名产出三处静默错误的形状。
_PRINTED_TO_SCALE = {
    "元": UnitScale.YUAN,
    "万元": UnitScale.WAN_YUAN,
    "亿元": UnitScale.YI_YUAN,
}

#: `单位:元 币种:人民币` / `单位：万元 币种：人民币` —— 半角与全角冒号都收。
#:
#: 负向前视 `(?<!编制)` 是 `locate.py` 实测踩出来的同一个坑：同一屏里还有
#: 「编制单位:贵州茅台酒股份有限公司」，不排除它就会把公司名当成计量单位。
#: 两处各自需要这条，但**正则本身只在这里定义一次**（`L-39`）。
_UNIT_RE = re.compile(r"(?<!编制)单位[:：]\s*(\S+?)(?=\s|币种|$)")
_CURRENCY_RE = re.compile(r"币种[:：]\s*(\S+)")


def parse_unit_header(text: str) -> tuple[UnitScale, str]:
    """`单位:元 币种:人民币` → `(UnitScale.YUAN, "人民币")`。

    **任何读不出来的情形一律抛 `UnitMismatchError`**：空串、只有单位没有币种、
    单位词不在穷举表里。不返回 `(UnitScale.YUAN, "人民币")` 这个「合理默认」。
    """
    if not isinstance(text, str) or not text.strip():
        raise UnitMismatchError(
            "单位表头为空，读不出计量单位与币种。"
            "口径类开关缺失即在读入边界 fail-closed，不取「元 / 人民币」这个合理默认（L-34）。"
        )
    unit_match = _UNIT_RE.search(text)
    currency_match = _CURRENCY_RE.search(text)
    if unit_match is None or currency_match is None:
        raise UnitMismatchError(
            f"从 {text!r} 里读不到"
            f"{'计量单位' if unit_match is None else ''}"
            f"{'与' if unit_match is None and currency_match is None else ''}"
            f"{'币种' if currency_match is None else ''}。"
        )
    printed = unit_match.group(1)
    if printed not in _PRINTED_TO_SCALE:
        raise UnitMismatchError(
            f"计量单位 {printed!r} 不在穷举表 {sorted(_PRINTED_TO_SCALE)} 内。"
            "**不推断**：一个没见过的单位词只可能是版面形态超出了实测范围，"
            "猜一个系数会让整批金额静默地差若干个数量级。"
        )
    return _PRINTED_TO_SCALE[printed], currency_match.group(1)


def scale_of(printed: str) -> UnitScale:
    """版面上印的单位词 → `UnitScale`。不认识就抛，**不返回 `YUAN`**。"""
    if printed not in _PRINTED_TO_SCALE:
        raise UnitMismatchError(
            f"计量单位 {printed!r} 不在穷举表 {sorted(_PRINTED_TO_SCALE)} 内。"
        )
    return _PRINTED_TO_SCALE[printed]


def to_yuan(amount: Decimal, scale: UnitScale) -> Decimal:
    """归一化到元。**跨源比较之前必须过这一步。**

    用 `Decimal` 乘法不用浮点：万元 → 元是乘 10000，浮点在这里的舍入漂移
    会直接污染「差多少算不一致」的判定。
    """
    if not isinstance(amount, Decimal):
        raise UnitMismatchError(
            f"待归一化的金额必须是 Decimal，实际是 {type(amount).__name__} —— "
            "二进制浮点的舍入漂移会污染跨源比较的判定。"
        )
    return amount * scale.value


def same_scale(*printed: str) -> UnitScale:
    """若干个版面单位词全都相同则返回那个 `UnitScale`，否则抛错。

    **不做「归一化后再比」的隐式修复**：参与同一次运算的两条记录单位不同时，
    正确的处置是拒答并置 `unit_scale_mismatch`，而不是替调用方换算 ——
    换算掩盖的是「这两个数本来就不该放在一起」这件事。
    """
    if not printed:
        raise UnitMismatchError("没有给出任何单位词")
    scales = {scale_of(p) for p in printed}
    if len(scales) != 1:
        raise UnitMismatchError(
            f"参与同一次运算的单位不一致：{sorted(set(printed))}。"
            "拒答并置 unit_scale_mismatch，不替调用方换算 —— "
            "换算会掩盖「这两个数本来就不该放在一起」这件事。"
        )
    return scales.pop()
