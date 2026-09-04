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


def _near_miss(registry: Registry, question: str, alias: str, at: int) -> str | None:
    """命中的 `alias` 是不是另一个指标的名字被截了一段？

    返回题面里那个更长的说法（⇒ 应当拒答）；不是就返回 `None`。
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
                if best is None or len(cand[0]) > len(best[0]):
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


def parse_intent(question: str, registry: Registry, ask_model=None):
    """题面 → `Intent`，或说明缺什么的 `Refusal`。

    `ask_model` 是一个 `(question) -> str` 的可调用对象，**由调用方注入**。
    本模块不 import 任何 LLM 客户端 —— `eval/llm_client.py` 顶部明写它
    「永远不会被系统臂导入」，那条边界在这里照样成立。
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
        return Refusal(RefusalCode.METRIC_NOT_DEFINED, f"题面里没有认得出的指标名：{q}")

    entities = sorted(set(_ENTITY.findall(q)))
    periods = sorted({int(y) for y in _PERIOD.findall(q)})

    if not entities:
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
        return Refusal(
            RefusalCode.INTENT_INCOMPLETE,
            f"题面里出现多个期间：{years}。那是跨期比较，不是本路径的三元组 —— 取第一个是猜。",
        )

    return Intent(
        metric_id=registry.by_alias[alias],
        entity=entities[0],
        period=periods[0],
        question=q,
        question_sha256=digest,
        resolved_by={"metric": source, "entity": "六位代码", "period": "题面年份"},
        matched_alias=alias,
    )
