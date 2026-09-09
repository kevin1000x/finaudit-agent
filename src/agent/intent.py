"""自然语言 → `(metric_id, 主体, 期间)`。**到此为止。**

🔴 **这是 LLM 在本系统里的唯一位置**（`02-01` T1，`D-001` / `D-003`）。
越过这条线，证据链就不再可复核 —— 所以模型在这里只做一件事：
**把一个说法归一到一个已经存在的指标名**。它不产生新指标，不判断口径，不算数。

## 三条硬约束

1. **先查别名表，再问模型。** 能确定性解决的不交给模型。
   模型是可选的：`ask_model=None` 时整条路径离线跑完。
2. **模型的答案仍要过别名表。** 模型说了一个表里没有的名字 ⇒ 照样拒答。
   否则等于把口径的权威交给了模型。
3. **解析不出来就拒答并说明缺哪一项，不猜**（`F-2`）。

## 近似命中：本模块最要紧的那段代码

2026-09-04 实测 frozen-01 `Q-C1-003`，题面是「**净**资产收益率」。
别名表里**没有**这一条，只有「资产收益率」（= `return_on_total_assets`，**总**资产收益率）。
裸子串匹配会把 ROE 静默答成 ROA —— **一个看起来完全正常的错误答案**。

判据不靠猜哪些字是修饰语（那是编一张词表），**靠别名表自己**：
若存在另一个别名 `b`，`b` 以命中的别名 `a` 结尾、且指向**不同的指标**，
而题面里 `a` 前面那几个字正好接得上 `b` 多出来的那截 ⇒ **命中的很可能不是 `a`**。
实例：`b` = 加权平均净资产收益率（`roe_weighted_average`），
`a` = 资产收益率（`return_on_total_assets`），题面里 `a` 前面是「净」⇒ 拒答。

⚠️ **它给出的是拒答，不是改判。** 把「净资产收益率」判成 `roe_weighted_average`
是一个**口径判断**（净资产收益率还有全面摊薄口径），不该由匹配算法替人做。
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from semantic_layer.resolve import Refusal, RefusalCode, Registry

__all__ = ["Intent", "parse_intent"]

#: 六位股票代码。四位的年份不会误命中。
_ENTITY = re.compile(r"(?<!\d)(\d{6})(?!\d)")
#: 报告期。**只认带「年」的**：光一个四位数可能是金额、条号或准则版本。
_PERIOD = re.compile(r"((?:19|20)\d{2})\s*年")


@dataclass(frozen=True)
class Intent:
    """一次提问被解析成的三元组，外加**它是怎么解析出来的**。

    `resolved_by` 不是调试信息：`D-003` 要求答案能被独立复核，
    而「这个指标名是查表查到的还是模型给的」正是复核者要问的第一个问题。
    """

    metric_id: str
    entity: str
    period: int
    question: str
    question_sha256: str
    resolved_by: dict = field(default_factory=dict)
    matched_alias: str | None = None

    def to_dict(self) -> dict:
        return {
            "metric_id": self.metric_id,
            "entity": self.entity,
            "period": self.period,
            "question_sha256": self.question_sha256,
            "resolved_by": dict(self.resolved_by),
            "matched_alias": self.matched_alias,
        }


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _near_miss(registry: Registry, question: str, alias: str, at: int):
    """命中的 `alias` 是不是另一个指标的名字被截了一段？

    返回 `(题面里那个更长的说法, 我们真正有的那条别名)`；不是就返回 `None`。
    多个候选都成立时取**最长**的那个。
    """
    target = registry.by_alias.get(alias)
    best = None
    for other, other_metric in registry.by_alias.items():
        if other == alias or other_metric == target or not other.endswith(alias):
            continue
        extra = other[: -len(alias)]
        # `extra` 的每一个非空后缀都试：题面里接得上就算命中。取最长的那个。
        for k in range(len(extra), 0, -1):
            tail = extra[-k:]
            if at >= k and question[at - k : at] == tail:
                cand = tail + alias
                # ⚠️ 比的是**候选串本身**的长度。写成 `len(cand[0])` 时
                # 两边恒为 1（那是首字符），比较恒假 ⇒ 取到的是第一个候选，
                # 而「第一个」由 `metrics/` 的加载顺序决定，不是任何人的决定。
                if best is None or len(cand) > len(best[0]):
                    # 一并把**触发碰撞的那条别名**带出去。
                    # 只报 `alias`（题面里那个子串）是没用的：读者要知道的是
                    # 「我们有的是哪一个」，而那是 `other`，不是 `alias`。
                    best = (cand, other)
                break
    return best


def _match_alias(registry: Registry, question: str):
    """(命中的别名, 近似命中) —— 两者不会同时非空。

    近似命中是一个二元组 `(题面里那个更长的说法, 我们真正有的那条别名)`。
    """
    for alias in sorted(registry.by_alias, key=len, reverse=True):
        at = question.find(alias)
        if at < 0:
            continue
        near = _near_miss(registry, question, alias, at)
        return (None, near) if near else (alias, None)
    return None, None


#: `_match_entities` 的第三种返回：命中了，但命中的很可能只是一个更长名字的一截。
_AMBIGUOUS_PREFIX = object()


def _is_ideograph(ch: str) -> bool:
    """CJK 表意文字。用码位判，不列字表。"""
    return "一" <= ch <= "鿿"


def _match_entities(q: str, entity_names):
    """题面里认得出哪几家公司。返回命中的名字列表，或 `_AMBIGUOUS_PREFIX`。

    🔴 **左边必须是边界。** 命中的名字紧挨着一个汉字时拒答 ——
    「**南**华鑫科技」里确实含有「华鑫科技」，但那几乎一定是另一家公司。
    2026-09-09 独立复核实测：修这一条之前，「南华鑫科技 2023 年的资产负债率」
    答出了华鑫科技的 0.55，页面上一句异常都没有。

    ⚠️ **右边没有同样的守卫，这是一个已知的、写下来的洞**（`N-70`）：
    「华鑫科技**集团**有限公司」今天仍会被认成华鑫科技。
    守右边的代价是误拒最自然的问法 —— 「贵州茅台**的**资产负债率是多少」
    里紧跟着的也是汉字。中文没有词边界，而**误拒会让人绕过这个功能，
    误答只会让人相信一个错数**：两种错都要避，但在拿不出一条能分开
    「的」与「集团」的判据之前，先守住更危险的那一侧。
    """
    命中 = {}
    for 名 in entity_names:
        if not 名 or not isinstance(名, str):
            continue
        at = q.find(名)
        if at >= 0:
            命中[名] = at
    # 一个名字被另一个包含时只留更长的那个（例如同时登记了简称与全称）。
    命中 = {n: at for n, at in 命中.items() if not any(n != o and n in o for o in 命中)}

    # 🔴 **先判「是不是两家」，再判「是不是只认出一截」。** 顺序反了会误伤：
    # 「华鑫科技**和**长风制造哪个高」里，「长风制造」左边紧挨着「和」——
    # 那是个连词，不是名字的一部分。2026-09-09 首版就是这么写的，
    # 一条已有的测试当场把它抓了出来。
    if len({str(entity_names[n]) for n in 命中 if entity_names[n]}) > 1:
        return list(命中)

    if any(at > 0 and _is_ideograph(q[at - 1]) for at in 命中.values()):
        return _AMBIGUOUS_PREFIX
    return list(命中)


def parse_intent(question: str, registry: Registry, ask_model=None, entity_names=None):
    """题面 → `Intent`，或说明缺什么的 `Refusal`。

    `ask_model` 是一个 `(question) -> str` 的可调用对象，**由调用方注入**。
    本模块不 import 任何 LLM 客户端 —— `eval/llm_client.py` 顶部明写它
    「永远不会被系统臂导入」，那条边界在这里照样成立。

    `entity_names` 是 `简称 -> 六位代码` 的表，**同样由调用方注入**，
    来源是那份数据源自己（`FixtureSource.entity_names`）。
    🔴 **这一步不交给模型**：本模块第一条硬约束就是「能确定性解决的不交给模型」，
    而「简称 → 代码」是一次查表。拿模型去做查表，等于把一个确定性映射
    换成一个会错的映射。
    """
    q = " ".join(str(question).split())
    digest = _sha256(q)

    alias, near = _match_alias(registry, q)
    if near:
        asked, have = near
        return Refusal(
            RefusalCode.METRIC_NOT_DEFINED,
            f"题面里的「{asked}」在语义层中没有对应的口径定义。"
            f"我们有的是「{have}」（{registry.by_alias[have]}）—— "
            f"它与「{asked}」不是同一个口径，不替提问者做这个判断。",
        )

    source = "alias_table"
    if alias is None and ask_model is not None:
        # 模型只做归一，答案仍要过别名表。
        guess = " ".join(str(ask_model(q)).split())
        if guess and guess in registry.by_alias:
            alias, source = guess, "model"
    if alias is None:
        # ⚠️ **不要把整个问句贴在冒号后面。** `h2-02` 的盲审有两个人读成了
        # 「这一整句话被当成了指标名」，愣了几秒才明白意思。
        # 而问句**已经印在这一页顶上的「问的是什么」里了** —— 在理由里再贴一遍，
        # 除了制造那次误读之外没有任何作用。
        return Refusal(
            RefusalCode.METRIC_NOT_DEFINED,
            "这句话里没有我认得出的指标名。下面列着当时全部可用的叫法，"
            "你要问的那个不在里面。",
        )

    entities = sorted(set(_ENTITY.findall(q)))
    periods = sorted({int(y) for y in _PERIOD.findall(q)})
    entity_source = "六位代码"

    # `N-65`：题面里没有六位代码时，再拿简称查一次表。
    # 顺序是**先代码后简称**，不是偏好问题：代码是唯一标识，简称会重名、会变更。
    if not entities and hasattr(entity_names, "items"):
        # `hasattr(items)` 而不是 `if entity_names`：调用方传了个列表进来时，
        # 旧写法会在 `entity_names[n]` 上抛 TypeError —— 而本模块的纪律是
        # **认不出就拒答**，不是崩。
        命中 = _match_entities(q, entity_names)
        if 命中 is _AMBIGUOUS_PREFIX:
            # 🔴 独立复核（2026-09-09）实测出来的一个真危险：
            # 「**南**华鑫科技 2023 年的资产负债率」当时答出 0.55，
            # 认成了「华鑫科技」—— 正是 `intent.py` 抬头写的
            # 「一个看起来完全正常的错误答案」。
            return Refusal(
                RefusalCode.INTENT_INCOMPLETE,
                "题面里那个公司名，我只认出了它的「一部分」 —— 它前面还连着别的字，"
                "很可能是另一家名字更长的公司。不猜。请给六位股票代码，"
                "或者把公司名单独隔开写。",
                # `L-9` 的责任方标识：**是简称表这一环拒的**。
                # 证据页据此挂上「当时认得出哪些公司」那一节 —— 见 answer.py 的 `G4`。
                source="intent:entity_table",
            )
        # 代码取不到值的表项直接丢 —— 否则 `str(None)` 会变成一个
        # 叫「None」的主体，证据页上印「取的是 None 的 2023 年那一行」。
        codes = sorted({str(entity_names[n]) for n in 命中 if entity_names[n]})
        if len(codes) == 1:
            # 取**最长**的那个命中，不取字典里第一个 —— 顺序由合表顺序决定，
            # 不由任何人决定（`_near_miss` 的注释警告过同一个形状）。
            entity_source = "公司简称「" + max(命中, key=len) + "」"
            entities = codes
        elif len(codes) > 1:
            名单 = chr(12289).join(sorted(命中))
            return Refusal(
                RefusalCode.INTENT_INCOMPLETE,
                "题面里出现多家公司：" + 名单 + "。本路径只处理单主体，不替提问者选一家。",
            )

    if not entities:
        # ⚠️ 措辞分两种。`h2-02` 的盲审有两个人被旧措辞误导过：
        # 题面里明明写着「华鑫科技」，而系统回「题面里没有主体」——
        # 读者会以为它连问的是哪家都没读出来。**缺的是代码，不是主体。**
        if entity_names:
            return Refusal(
                RefusalCode.INTENT_INCOMPLETE,
                "题面里没有认得出的公司。给一个六位股票代码，"
                "或者一个我们确实有数据的公司简称 —— 两样都没有时不猜。",
                # 同上：责任方是简称表。**这句话没有这一节就不可证伪** ——
                # 读者无从知道「认得出的」到底是哪几家（`G4`）。
                source="intent:entity_table",
            )
        return Refusal(RefusalCode.INTENT_INCOMPLETE, "题面里没有主体（六位股票代码）")
    if len(entities) > 1:
        return Refusal(
            RefusalCode.INTENT_INCOMPLETE,
            f"题面里出现多个主体：{chr(12289).join(entities)}。本路径只处理单主体，不取第一个。",
        )
    if not periods:
        return Refusal(RefusalCode.INTENT_INCOMPLETE, "题面里没有期间（形如「2023 年」）")
    if len(periods) > 1:
        years = chr(12289).join(str(y) for y in periods)
        # ⚠️ 旧措辞是「那是跨期比较，不是本路径的三元组」，而它**对其中一类是错的**
        # （`N-69`）：「2023 年的营业收入**比 2022 年**增长了多少」要的是**一个**
        # 同比数，第二个年份是**比较基准**，不是第二个查询期间 ——
        # 而同比类指标的定义**自己就知道**去取上期（只写一个年份照样算得出）。
        #
        # 这里**不去猜**是哪一类：判据只能是启发式的，而猜错的方向是
        # 「该拒答的时候答了」。⇒ 把两种读法都摆出来，并告诉提问者各自怎么办。
        return Refusal(
            RefusalCode.INTENT_INCOMPLETE,
            "题面里出现多个期间："
            + years
            + "。本路径一次只答一个期间的一个数，不替你挑一个。"
            + "如果你要的是这几年各一个数，那是跨期比较，本路径不做；"
            + "如果你要的是一个同比数，把基准年去掉再问一次 ——"
            + "同比类的指标自己会去取上期。",
        )

    return Intent(
        metric_id=registry.by_alias[alias],
        entity=entities[0],
        period=periods[0],
        question=q,
        question_sha256=digest,
        resolved_by={"metric": source, "entity": entity_source, "period": "题面年份"},
        matched_alias=alias,
    )
