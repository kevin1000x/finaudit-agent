"""一段财报分析结论 → 一份逐条判定的核查报告（`D-041`）。

🔴 **这一层不算数，也不判口径。** 算数在 `gate.execute()`，口径在 `metrics/`。
本模块只做三件事：**把一段话切成声明、把每条声明交给 `answer_question`、
把回来的东西判成五态之一**。它一个新指标都不产生，一个数都不算。

## 为什么是这个形态

核查是问答的**超集**：要核「净利率 50.6%」，系统必须先把净利率算出来
⇒ 问答能力就在核查里面，区别只在用户带没带那个数。所以**没有模式开关**，
`read_input()` 自己判，判据是 `D-041` 写死的那一条：

> 题面里有没有一个**没被 `_PERIOD` 或 `_ENTITY` 消耗掉的数值**。

## 五态是封闭集

`Verdict` 只有五个成员，**不许出现第六种**（`D-041` §3）。
`NOT_COVERED` 与 `NOT_CHECKABLE` 是**成功的判定**，不是失败 ——
「核不了」是正当输出，这正是深度换广度在新形态下反过来成为优势的地方。

## 判错了不藏

报告第一行写「我把这段话读成什么」，与证据页印 `metric_resolved_by` /
`matched_alias` 是同一个做法（`D-032`）。**读者要能一眼看出它理解错了**，
而不是拿到一个莫名其妙的结果。承接上下文（主体/期间承自前一句）同样印出来。

## `D-010` 的边界就是这个模块的签名

`read_input()` 只吃**一个 `str`**。不接受文件、不接受结构化载荷、不落盘。
用户粘进来的数字是**被判定的对象**，任何时候都不当事实用 ——
`answer_question` 拿到的永远只有「主体 / 期间 / 指标」，那个数只进比较，不进取数。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum

from semantic_layer.explain import wrap

from .answer import Answer, answer_question, render_answer
from .intent import (
    _AMBIGUOUS_PREFIX,
    _AMBIGUOUS_SUFFIX,
    _ENTITY,
    _PERIOD,
    _match_entities,
)

__all__ = [
    "Verdict",
    "ReadAs",
    "Claim",
    "StatedValue",
    "VerifyReport",
    "numbers_in",
    "read_input",
    "split_segments",
    "stated_value",
    "render_report",
]


class Verdict(Enum):
    """一条声明的判定。**封闭集，五个，不许加第六个**（`D-041` §3）。

    加第六个之前先读 `D-041`：那条决策把「五态是封闭集」写进了决策本身，
    而不是写成一句注释 —— 因为「再加一态」永远看起来很划算。
    """

    CONSISTENT = "可核，且与本系统算出的数一致"
    INCONSISTENT = "可核，但与本系统算出的数不一致"
    AMBIGUOUS_BASIS = "口径未声明 —— 本系统按某一个口径解释了它，换一个口径是另一个数"
    # ⚠️ 措辞刻意宽。独立复核（2026-09-11）指出：`INTENT_INCOMPLETE`
    #    （多主体 / 多期间 / 认不出公司）也落在这一格，于是报告会对一条
    #    **在覆盖面里**的声明印「不在覆盖范围内」—— 那句话是假的，
    #    而覆盖面窄正是这个产品对外的核心说法。
    #    不加第六态（`D-041` §3 写死），改成两者都容得下，由 `reason` 承担区分。
    NOT_COVERED = "核不了：数据或指标不在覆盖范围内，或这句话我没解析出主体与期间"
    NOT_CHECKABLE = "不是可核声明"


class ReadAs(Enum):
    """系统把整段输入读成了什么。**印在报告第一行**（`D-041` §2）。"""

    QUESTION = "一个提问"
    STATEMENT = "待核声明"


#: 断句。**顿号不切** —— 「营业收入、净利润都增长了」是一条声明的两个主语，
#: 切开会造出两条谁都不完整的碎片。
#: ⚠️ 这张表列的是**标点**，不是词。本仓的纪律是不靠编词表做语义判断
#: （见 `intent.py` 抬头），标点不在那条禁令里：它是书写约定，不是语义猜测。
_SPLIT = re.compile(r"[。；;！!？?\n，,]+")

#: 数值。**逗号分组**（`1,477`）要在小数点之前一并吃掉，
#: 否则 `1,477.5` 会被切成 `1` 与 `477.5` 两个数 —— 两个都是假的。
_NUMBER = re.compile(
    r"(?<![\d.])(-?\d+(?:,\d{3})*(?:\.\d+)?)\s*(个百分点|百分点|%|％|亿元|亿|万元|万)?"
)

#: 单位 → 倍率。
_SCALE = {
    None: Decimal(1),
    "%": Decimal("0.01"),
    "％": Decimal("0.01"),
    "个百分点": Decimal("0.01"),
    "百分点": Decimal("0.01"),
    "亿": Decimal(10) ** 8,
    "亿元": Decimal(10) ** 8,
    "万": Decimal(10) ** 4,
    "万元": Decimal(10) ** 4,
}

#: 🔴 **这两个单位说的是「差」，不是「水平」。**
#: 「同比提升 1.2 个百分点」断言的是两年净利率之**差**，而本系统这一层
#: 只算得出**某一年的水平值** —— 拿 0.012 去跟某一年的净利率比，
#: 是一个看起来完全正常的错判定。⇒ 一律 `NOT_COVERED`，并说清为什么。
_DELTA_UNITS = frozenset({"个百分点", "百分点"})

#: 表示「这是一个变动」的说法。**单位挡不住这一类**：
#: 「资产负债率同比下降 3.5%」写的是 `%`，而它说的仍然是一个**差**，
#: 拿 0.035 去跟 0.1798 比会判出一个理直气壮的「不一致」——
#: 而用户那句话可能完全正确。2026-09-11 实测出来的。
#:
#: ⚠️ **这确实是一张词表，而本仓的纪律是「不靠编词表做语义判断」**
#: （`intent.py` 抬头）。为什么这里不违反那一条：
#:
#: | | 那条禁令针对的 | 这一张 |
#: |---|---|---|
#: | 用途 | 判**这个说法是哪个指标** | 判**这句话该不该拒** |
#: | 命中的后果 | 产出一个**答案** | 产出一次**拒答** |
#: | 漏判的后果 | 答错 | 退回原路径，仍要过其余各道 |
#:
#: **它只会让系统少答，不会让系统多答。** 同一条不对称在 `intent.py` 的
#: `_BOUNDARY_CHARS` 上已经用过一次：那也是一张人列的字表，也只用于拒答方向。
#:
#: 🔴 **例外见 `_says_change()`**：词命中在**指标名自己里面**时不算 ——
#: 「营业收入同比增长率 18%」里的「同比」「增长」是那个指标的名字，不是一个变动修饰。
#: **比年度更细的期间**。`metrics/` 20 份定义全是 `period_type: annual`，
#: 拿一个年度值去核一条季度 / 半年度声明，是又一个「看起来完全正常的错判定」——
#: 独立复核（2026-09-11）实测：「600519 2023 年前三季度速动比率 3.67」
#: 当场判「✅ 一致」，而那个 3.67 是**全年**的数，报告一个字都没提期间对不上。
#: 与 `_DELTA_WORDS` 同一条理由（只用于拒答方向），也同一条限制（是一张人列的表）。
_SUB_ANNUAL_WORDS = (
    "季度",
    "季报",
    "半年",
    "中期",
    "上半年",
    "下半年",
    "前三季",
    "Q1",
    "Q2",
    "Q3",
    "Q4",
    "H1",
    "H2",
)

#: 金额单位。跟在一串数字后面时，那串数字是**金额**，不是股票代码。
#: 「自由现金流 639735 万元」里的 `639735` 曾被 `_ENTITY` 当成六位代码遮掉，
#: 于是整段被降级成「一个提问」，再被拒成「数据源里没有 639735 的 2023 年数据」。
#: 券商结论里「万元」口径的六位数金额极常见（`747340`、`639735`）。
_MONEY_UNITS = ("万元", "亿元", "万", "亿", "元")

_DELTA_WORDS = (
    "同比",
    "环比",
    "增长",
    "下降",
    "提升",
    "提高",
    "上升",
    "回落",
    "增加",
    "减少",
    "改善",
    "恶化",
)


@dataclass(frozen=True)
class StatedValue:
    """用户在这句话里写下的那个数。**它是被判定的对象，永远不是取数输入。**"""

    text: str
    unit: str | None
    value: Decimal
    #: 半个末位。「50.6%」说的是 50.55%–50.65%，**声明的精度自己定义了容差**，
    #: 不由本模块拍一个 `1e-6`。拍一个数会让「写两位小数」与「写六位小数」
    #: 承担同样的举证责任，那不对。
    tolerance: Decimal

    @property
    def is_delta(self) -> bool:
        return self.unit in _DELTA_UNITS


@dataclass(frozen=True)
class Claim:
    """一条声明，以及它的判定。"""

    text: str
    verdict: Verdict
    #: 交给 `answer_question` 的那句话。与 `text` 不同时说明**承接了上下文**，
    #: 而那件事必须印出来（`D-041` §2）。
    asked: str | None = None
    stated: StatedValue | None = None
    answer: Answer | None = None
    #: 一句给人读的理由。**不是把 `verdict` 翻译一遍**，是这一条**为什么**是这个判定。
    reason: str = ""
    #: 承接来的上下文（主体 / 期间）。`None` 表示这一条自己就写全了。
    inherited: str | None = None

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "verdict": self.verdict.name,
            "verdict_meaning": self.verdict.value,
            "asked": self.asked,
            "stated_value": None if self.stated is None else str(self.stated.value),
            "stated_text": None if self.stated is None else self.stated.text,
            "reason": self.reason,
            "inherited": self.inherited,
            "answer": None if self.answer is None else self.answer.to_dict(),
        }


@dataclass(frozen=True)
class VerifyReport:
    """一次核查的完整产物。"""

    text: str
    read_as: ReadAs
    claims: list = field(default_factory=list)
    #: `read_as is QUESTION` 时，这就是今天那条问答路径的产物，一字未改。
    answer: Answer | None = None

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "read_as": self.read_as.name,
            "claims": [c.to_dict() for c in self.claims],
            "counts": self.counts(),
            "answer": None if self.answer is None else self.answer.to_dict(),
        }

    def counts(self) -> dict:
        """五态各几条。**五个键恒在**，为零也写出来 ——
        缺键与零在读的人眼里不是一回事。"""
        got = {v.name: 0 for v in Verdict}
        for c in self.claims:
            got[c.verdict.name] += 1
        return got


def _is_money(text: str, end: int) -> bool:
    """`text[end:]` 是不是紧跟着一个金额单位（允许中间有空格）。"""
    tail = text[end:].lstrip()
    return any(tail.startswith(u) for u in _MONEY_UNITS)


def _mask(text: str) -> str:
    """把六位代码与年份**换成等长的占位**，这样剩下的数字才是「用户写的那个数」。

    等长是要紧的：换成不等长会让匹配到的位置对不回原文。
    占位用全角空格而不是别的字符 —— 它不是数字、不是汉字、也不构成新的词。

    🔴 **后面紧跟金额单位的六位数不遮**（`_MONEY_UNITS`）：那是金额，不是代码。
    不加这一条，「自由现金流 639735 万元」整段会被读成「一个提问」——
    独立复核 2026-09-11 实测。
    """

    def 遮代码(m):
        if _is_money(text, m.end()):
            return m.group(0)
        return "　" * len(m.group(0))

    out = _ENTITY.sub(遮代码, text)
    return _PERIOD.sub(lambda m: "　" * len(m.group(0)), out)


def numbers_in(text: str) -> list:
    """这句话里**所有**用户写下的数（先遮掉主体与期间）。

    🔴 **不是只找第一个。** 一句话里剩下两个数时，「要核的是哪一个」没有答案：

        「600519 2023 年流动比率在 4.5~5.0 之间。」

    只取第一个会拿 4.5 去比，而真值 4.6239 **落在这个区间里** ——
    用户那句话是对的，系统却理直气壮地判「不一致」。
    2026-09-11 实测出来的，是本仓最典型的那种「看起来完全正常的错判定」。

    ⇒ 交出**全部**，由 `_judge()` 在多于一个时拒答。
    """
    masked = _mask(text)
    return [m for m in _NUMBER.finditer(masked)]


def _as_stated(m):
    raw, unit = m.group(1), m.group(2)
    try:
        base = Decimal(raw.replace(",", ""))
    except InvalidOperation:  # pragma: no cover - 正则已经保证它是个数
        return None
    scale = _SCALE[unit]
    # 末位所在的十进制位：`Decimal("50.6").as_tuple().exponent` 是 -1。
    ulp = Decimal(10) ** base.as_tuple().exponent
    return StatedValue(
        text=m.group(0).strip(),
        unit=unit,
        value=base * scale,
        tolerance=ulp * scale / 2,
    )


def stated_value(text: str):
    """这句话里**第一个**用户写下的数，没有就返回 `None`。

    只用来回答「这句话里有没有一个待核的数」（`D-041` §1 的读法判据）。
    **要判定一条声明时不要用它**，用 `numbers_in()` —— 见那个函数的抬头，
    只看第一个数会在区间断言上判出一个理直气壮的错结论。
    """
    got = numbers_in(text)
    return _as_stated(got[0]) if got else None


def _says_change(seg: str, alias) -> str | None:
    """这句话是不是在说一个**变动**而不是一个水平值。返回命中的那个词。

    判据不是「句子里有没有那个词」，是**那个词在不在指标名之外** ——
    「营业收入同比增长率 18%」里的「同比」「增长」是那个指标自己的名字，
    把它读成变动就把一个本来能核的声明拒掉了。
    ⇒ 先把命中的别名从句子里挖掉，再看剩下的部分。
    """
    剩下 = seg
    if alias:
        剩下 = 剩下.replace(str(alias), "")
    for 词 in _DELTA_WORDS:
        if 词 in 剩下:
            return 词
    return None


def split_segments(text: str) -> list:
    """一段话 → 若干条候选声明。**只按标点切，不按语义切。**

    按语义切要么靠模型（那就把口径权威交给了模型），要么靠词表
    （那是 `intent.py` 抬头点名的错方向）。⇒ 只切标点，切多了由
    `NOT_CHECKABLE` 兜住 —— 多出一条「不是可核声明」是**正当输出**，
    不是缺陷。
    """
    return [seg for seg in (s.strip() for s in _SPLIT.split(text)) if seg]


#: 一次请求最多核几条。**这不是礼貌边界，是一道真的闸门。**
#:
#: 独立复核（2026-09-11）实测：8000 字节的输入切出 **533 段**，
#: 每一段带数的都要**完整走一遍取数 + 求值**，接上模型时还是 533 次模型调用 ——
#: 而 `service/model.py` 的超时是 8 秒，533 × 8s ≈ 71 分钟，
#: 卡在**一条同步请求**上，而 `serve()` 是单线程的。
#:
#: `model.py` 抬头拒用 `eval/llm_client.py` 的理由逐字是
#: 「放到一条同步请求路径上，意味着一次请求最长可以卡五分钟」——
#: 扇出把那件事放大了两个量级，所以这里必须有一个数。
#:
#: 超出的段落判 `NOT_COVERED` 并**说清楚是被这条闸门拦的**，不静默截断。
MAX_CHECKABLE_CLAIMS = 24

#: 「这一句里认出的东西不止一个，或者它踩了边界」。**不是 `None`** ——
#: 「没写」与「写了但我不敢认」是两件事：前者可以承接上一句，后者必须停下来。
AMBIGUOUS = object()


def _period_in(seg: str):
    """这一句自己写了哪一年。没写 `None`；写了不止一年 `AMBIGUOUS`。

    多个年份**不挑一个**。`intent.py` 对同一件事的原话是
    「本路径一次只答一个期间的一个数，不替你挑一个」——
    在这里挑一个的后果更隐蔽：报告会拿另一年的数去否定一条关于这一年的声明。
    """
    years = {int(y) for y in _PERIOD.findall(seg)}
    if not years:
        return None
    return years.pop() if len(years) == 1 else AMBIGUOUS


def _entity_in(seg: str, source, registry):
    """这一句自己写了哪个主体。没写 `None`；认不准 `AMBIGUOUS`。

    🔴 **公司名不在这里自己认，整条委托给 `intent._match_entities`。**

    独立复核（2026-09-11）实测：本函数原来用的是一行裸子串匹配，
    于是 `intent.py` 为公司名边界付过代价才立起来的两道防线被整个绕过 ——
    **而下面那一层的回归全是绿的，因为新层从旁边绕过去了**：

    | 输入 | 绕过之前（`intent`） | 绕过之后（本层曾经的行为） |
    |---|---|---|
    | 「南华鑫科技 2023 年…，资产负债率 0.55」 | 拒答：前面还连着别的字 | ✅ **一致**，主体认成 900001 |
    | 「华鑫科技集团有限公司…」 | 拒答：后面还连着别的字 | ✅ **一致**，主体认成 900001 |

    这正是 `intent.py` 抬头逐字写的「一个看起来完全正常的错误答案」，第三次。
    ⇒ **判据只能有一处实现。** 顺序也照搬：先六位代码，后公司简称。
    """
    # 与 `_mask` 同一条判据：后面紧跟金额单位的六位数是金额，不是代码。
    codes = sorted(
        {m.group(1) for m in _ENTITY.finditer(seg) if not _is_money(seg, m.end())}
    )
    if len(codes) > 1:
        return AMBIGUOUS
    if codes:
        return codes[0]

    表 = getattr(source, "entity_names", None) or {}
    if not hasattr(表, "items") or not 表:
        return None
    命中 = _match_entities(seg, 表, registry)
    # 左边界 / 右边界踩线：`_match_entities` 返回的是哨兵，不是列表。
    if 命中 is _AMBIGUOUS_PREFIX or 命中 is _AMBIGUOUS_SUFFIX:
        return AMBIGUOUS
    got = sorted({str(表[n]) for n in 命中 if 表.get(n)})
    if not got:
        return None
    return got[0] if len(got) == 1 else AMBIGUOUS


def _judge(
    answer: Answer,
    stated: StatedValue,
    registry,
    seg: str,
    extra: list,
    own_entity=None,
) -> tuple:
    """`(判定, 理由)`。**这是全模块唯一决定五态的地方。**

    `extra` 是这句话里**除 `stated` 之外**还剩的数；非空即拒答。
    `own_entity` 是本层认出的主体（`None` = 这句话里没有）——
    用来发现「下游把一串金额认成了股票代码」，见下面那一段。
    """
    # 比年度更细的期间：本层只有年度值，拿它核季度声明是又一个静默错判。
    # **排在最前**，因为它是整句的性质，与这句话里有几个数无关。
    for 词 in _SUB_ANNUAL_WORDS:
        if 词 in seg:
            return (
                Verdict.NOT_COVERED,
                "这句话里的「" + 词 + "」说明它讲的是一个**比年度更细的期间**，"
                "而本系统的 20 份口径定义全部是年度口径（`period_type: annual`）。"
                "拿一个全年的数去核它会判出一个看起来正常的错结论，所以不核。",
            )

    if extra:
        别的 = "、".join(m.group(0).strip() for m in extra)
        return (
            Verdict.NOT_COVERED,
            "这句话里不止一个数（还有 " + 别的 + "），"
            "我判不出要核的是哪一个 —— 区间（「在 4.5~5.0 之间」）与"
            "并列（「分别是 a 和 b」）都长这样。挑一个来核会得出一个"
            "看起来正常的错判定，所以不挑。一句一个数再试一次。",
        )
    if stated.is_delta:
        # 见 `_DELTA_UNITS` 的注释：「差」与「水平」不是一回事。
        return (
            Verdict.NOT_COVERED,
            "「" + stated.text + "」说的是一个变动幅度，而本系统这一层"
            "只算得出某一年的水平值。拿它跟一个水平值比会得出一个"
            "看起来正常的错判定，所以不比。",
        )
    if answer.refused:
        理由 = str((answer.refusal or {}).get("detail") or "（没有给出理由）")
        # 🔴 **下游把一串金额认成了股票代码时，说清楚。**
        #    「自由现金流 639735 万元」会拒成「数据源里没有 639735 的数据」——
        #    读者看不出 639735 是他自己写的金额。判错了不藏（`D-041` §2）。
        # 判据是「下游认的主体与本层认的不是同一个，而它恰好就是那串金额」。
        # 本层已经排除了紧跟金额单位的六位数（`_MONEY_UNITS`），下游没有。
        if answer.entity is not None and str(answer.entity) != str(own_entity or ""):
            if str(answer.entity) in stated.text:
                理由 += (
                    "　⚠️ 注意：「" + str(answer.entity) + "」是你写的**金额**，"
                    "而下游把这串六位数字当成了股票代码"
                    + ("，把「" + str(own_entity) + "」挤掉了" if own_entity else "")
                    + "。把金额换个写法（例如「63.97 亿元」）再试一次。"
                )
        return Verdict.NOT_COVERED, 理由

    defn = registry.definitions.get(answer.metric_id) if answer.metric_id else None
    display = getattr(defn, "display_name", None)
    alias = answer.evidence.get("matched_alias")

    # 单位挡不住「同比下降 3.5%」这一类：写的是 `%`，说的是**差**。
    # 判据见 `_says_change()` —— 词必须落在指标名之外。
    变动词 = _says_change(seg, alias)
    if 变动词:
        return (
            Verdict.NOT_COVERED,
            "这句话里的「" + 变动词 + "」说明 " + stated.text + " 是一个**变动**，"
            "不是某一年的水平值，而本系统这一层只算得出水平值。"
            "拿它跟 " + str(answer.value) + " 比会判出一个理直气壮的「不一致」，"
            "而你那句话可能完全正确 —— 所以不比。",
        )

    # 🔴 模型做过一次归一 ⇒ **无条件**算口径未声明。
    #    独立复核（2026-09-11）指出：不这样的话，同一句用户文本会因为
    #    模型这次返回「归母净利率」还是「净利率」而落到不同的五态 ——
    #    **判定由一个非确定性组件决定**，而用户一个字都没改。
    #    模型的归一本身就是一次替用户做的口径判断，那正是这一格的定义。
    if answer.evidence.get("metric_resolved_by") == "model":
        return (
            Verdict.AMBIGUOUS_BASIS,
            "你写的说法不在别名表里，是**模型**把它归到了「" + str(alias) + "」这一条上。"
            "那一步是替你做的一次口径判断 —— 本系统按「" + str(display) + "」算出 "
            + str(answer.value) + "。换一条别名就是另一个口径、另一个数，"
            "所以这里不写「一致」。",
        )

    ok = False
    try:
        ok = abs(Decimal(str(answer.value)) - stated.value) <= stated.tolerance
    except (InvalidOperation, ValueError, TypeError):  # pragma: no cover
        ok = False

    对上没 = "对得上" if ok else "对不上"
    本系统 = "本系统按「" + str(display) + "」算出 " + str(answer.value)

    # 🔴 **口径未声明优先于一致 / 不一致。**
    #    判据：**用户写的那个名字不是这个指标的正式名**。
    #    「净利率」的正式名是「归母净利率」，而那份定义自己写着：
    #    「上面别名里的『净利率』与『销售净利率』都不带口径限定，
    #      而本定义把它们解释为归母口径。这是一次口径判断，不是同义词收录。」
    #    ⇒ 那次判断是**系统替用户做的**，必须让用户看见。
    #
    #    ⚠️ **这条判据刻意宽**：`ROA` 的正式名是「总资产收益率」，
    #    于是打 `ROA` 也会被标成「口径未声明」，而 ROA 其实没什么歧义。
    #    宁可多标 —— 多标一次的代价是读者多看一行**真话**
    #    （「换个口径确实是另一个数」），漏标一次的代价是他相信了一个
    #    系统替他选过口径的结论。两种错不对称，守更危险的那一侧。
    #
    #    ⚠️ **明确不做的**：不编一张「哪些字算口径限定词」的词表去精确判断。
    #    那正是 `intent.py` 抬头点名的错方向，本仓已经为它返工过两次。
    if display and alias and str(alias) != str(display):
        return (
            Verdict.AMBIGUOUS_BASIS,
            "我在这句话里认出的指标名是「" + str(alias) + "」，而它不带口径限定。"
            + 本系统 + "，与这句话里的 " + stated.text + " " + 对上没 + "；"
            "但换一个口径就是另一个数，而这句话没说是哪一个。",
        )

    if ok:
        return Verdict.CONSISTENT, 本系统 + "，与这句话里的 " + stated.text + " 一致。"
    return (
        Verdict.INCONSISTENT,
        本系统 + "，而这句话说的是 " + stated.text + "。两者对不上。",
    )


def read_input(text: str, registry, source=None, ask_model=None) -> VerifyReport:
    """一段话 → 一份核查报告，或者（没有待核数值时）今天那条问答路径。

    🔴 **签名只吃一个 `str`**（`D-010` 边界补充）。不收文件、不收结构化载荷。

    `registry` / `source` / `ask_model` 与 `answer_question` 同义，原样透传 ——
    本模块**不自己 import 任何 LLM 客户端**，那条边界在这里与 `intent.py` 一样成立。
    """
    normalized = " ".join(str(text).split())
    segments = split_segments(normalized)

    # `D-041` §1 的判据：整段里有没有一个没被主体 / 期间消耗掉的数值。
    if not any(stated_value(seg) for seg in segments):
        return VerifyReport(
            text=normalized,
            read_as=ReadAs.QUESTION,
            answer=answer_question(
                normalized, registry, source=source, ask_model=ask_model
            ),
        )

    claims: list = []
    #: 上一句立下的 `(主体, 期间)`，供后面几句承接。
    ctx_entity = None
    ctx_period = None
    #: 已经打出去几次问。见 `MAX_CHECKABLE_CLAIMS` 的注释。
    问过 = 0

    for seg in segments:
        找到 = numbers_in(seg)
        stated = _as_stated(找到[0]) if 找到 else None
        extra = 找到[1:]

        # 🔴 **先认这一句自己写了什么，再决定要不要承接。**
        #    两件事分开认：一句话可以写了公司没写年份（「万华化学的资产负债率 62%」），
        #    那时该承接的只有年份，**主体绝不能承接** —— 否则报告会拿茅台的数
        #    去否定一条关于万华化学的声明，还印一句「承自前一句」当作交代。
        own_e = _entity_in(seg, source, registry)
        own_p = _period_in(seg)

        if stated is None:
            # 这一句不可核，但主体与期间可能就写在它里面，捡起来给后面用。
            if ctx_entity is None and own_e not in (None, AMBIGUOUS):
                ctx_entity = own_e
            if ctx_period is None and own_p not in (None, AMBIGUOUS):
                ctx_period = own_p
            claims.append(
                Claim(
                    text=seg,
                    verdict=Verdict.NOT_CHECKABLE,
                    reason="这句话里没有一个可以拿去核的数。",
                )
            )
            continue

        if 问过 >= MAX_CHECKABLE_CLAIMS:
            claims.append(
                Claim(
                    text=seg,
                    verdict=Verdict.NOT_COVERED,
                    stated=stated,
                    reason=(
                        "这一段里可核的声明超过 " + str(MAX_CHECKABLE_CLAIMS)
                        + " 条，后面的没有核。每一条都要完整走一遍取数与求值，"
                        "一次请求把它们全做完会把服务卡住。分几段贴进来。"
                    ),
                )
            )
            continue

        # 承接：**逐维承接，且只承接这一句自己没写的那一维**。
        # `AMBIGUOUS`（写了但认不准 —— 多家公司、多个年份、公司名边界踩线）
        # 一律**不承接**：那时停下来比猜一个更安全，`intent.py` 的原话是「不猜」。
        承 = []
        前缀 = ""
        if own_e is None and ctx_entity is not None:
            前缀 += ctx_entity + " "
            承.append("主体 " + ctx_entity)
        if own_p is None and ctx_period is not None:
            前缀 += str(ctx_period) + "年 "
            承.append("期间 " + str(ctx_period) + " 年")
        asked = (前缀 + seg) if 前缀 else seg
        inherited = "、".join(承) + " 承自前一句" if 承 else None

        answer = answer_question(asked, registry, source=source, ask_model=ask_model)
        问过 += 1

        if ctx_entity is None and own_e not in (None, AMBIGUOUS):
            ctx_entity = own_e
        if ctx_period is None and own_p not in (None, AMBIGUOUS):
            ctx_period = own_p

        verdict, reason = _judge(
            answer, stated, registry, seg, extra, own_entity=own_e
        )
        claims.append(
            Claim(
                text=seg,
                verdict=verdict,
                asked=asked,
                stated=stated,
                answer=answer,
                reason=reason,
                inherited=inherited,
            )
        )

    return VerifyReport(text=normalized, read_as=ReadAs.STATEMENT, claims=claims)


#: 判定 → 行首那个记号。与 `.planning/REPLAN-20260911.md` §2.1 的样例一致。
_MARK = {
    Verdict.CONSISTENT: "✅",
    Verdict.INCONSISTENT: "❌",
    Verdict.AMBIGUOUS_BASIS: "⚠️",
    Verdict.NOT_COVERED: "❌",
    Verdict.NOT_CHECKABLE: "⬜",
}


def render_report(report: VerifyReport, registry=None, flag_descriptions=None) -> str:
    """一份核查报告 → 一页给人读的文本。**内容全部来自 `report`，不新增。**

    每条可核声明后面挂的是 `render_answer()` 的**逐字输出**（`D-032`）：
    核查报告不另写一版证据页 —— 另写一版就是两套表达契约，而 `D-032` 只定义了一套。
    """
    L: list = []

    # 🔴 第一行：我把这段话读成什么。判错了不藏（`D-041` §2）。
    L.append("我把这段话读成：" + report.read_as.value)
    L.append("")

    if report.read_as is ReadAs.QUESTION:
        L.append("—— 这段话里没有待核的数值，所以它是一个提问，走的是问答路径。")
        L.append("")
        defn = None
        if registry is not None and report.answer is not None:
            defn = registry.definitions.get(report.answer.metric_id)
        L.append(render_answer(report.answer, defn, flag_descriptions))
        return "\n".join(L)

    L.append("拆出 " + str(len(report.claims)) + " 条，逐条判定：")
    L.append("")
    for i, c in enumerate(report.claims, 1):
        L.append(_MARK[c.verdict] + " " + str(i) + ". " + c.text)
        L.extend(wrap(c.verdict.value, indent="     "))
        if c.inherited:
            L.extend(wrap("（" + c.inherited + "）", indent="     "))
        if c.reason:
            L.extend(wrap(c.reason, indent="     "))
        L.append("")

    got = report.counts()
    L.append(
        "小计：一致 " + str(got["CONSISTENT"])
        + " ｜ 不一致 " + str(got["INCONSISTENT"])
        + " ｜ 口径未声明 " + str(got["AMBIGUOUS_BASIS"])
        + " ｜ 核不了 " + str(got["NOT_COVERED"])
        + " ｜ 不是可核声明 " + str(got["NOT_CHECKABLE"])
    )
    L.append("")
    L.extend(
        wrap(
            "「核不了」与「不是可核声明」都是正当输出，不是失败。"
            "本系统只覆盖人工逐字段核对过的公司与年度 —— 覆盖面窄是刻意的，"
            "换来的是每一个能核的数都有人签过字。",
            indent="",
        )
    )
    L.append("")

    # 证据页逐字挂在后面。**不另写一版**（`D-032`）。
    for i, c in enumerate(report.claims, 1):
        if c.answer is None:
            continue
        L.append("=" * 68)
        L.append("第 " + str(i) + " 条的证据链")
        L.append("=" * 68)
        defn = None
        if registry is not None:
            defn = registry.definitions.get(c.answer.metric_id)
        L.append(render_answer(c.answer, defn, flag_descriptions))
        L.append("")

    return "\n".join(L)
