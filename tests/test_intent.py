"""`src/agent/intent.py` 的回归（`02-01` T1）。

意图解析是 **LLM 在本系统里的唯一位置**（`D-001` / `D-003`）。
因此这份测试盯的不是「模型答得准不准」，而是**边界**：

- 能确定性解决的，一次模型都不许调
- 解析不出来就拒答并说明缺哪一项，**不猜**（`F-2`）
- 近似命中必须被发现 —— 这是本文件里最要紧的一条，见下

假客户端自建，不用 mock 框架（`L-65` 第 1 条）：确定性、可离线、
读起来本身就是一份行为规格。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agent.intent import Intent, parse_intent
from semantic_layer.resolve import Refusal, RefusalCode, Registry

REPO = Path(__file__).resolve().parent.parent


class 记账假模型:
    """记下被问过几次。**测试要断言的是这个数是 0。**"""

    def __init__(self, answers: list[str] | None = None):
        self.calls: list[str] = []
        self._answers = list(answers or [])

    def __call__(self, question: str) -> str:
        self.calls.append(question)
        return self._answers.pop(0) if self._answers else ""


@pytest.fixture
def registry():
    return Registry.load(REPO / "metrics")


def test_三要素齐全时一次模型都不调(registry):
    """`先查别名表再问模型`：能确定性解决的不要交给模型。

    它会红的场景：有人把「先查表」改成「先问模型再兜底」。
    """
    model = 记账假模型(["不该被调用"])
    got = parse_intent("华鑫科技（900001）2023 年的毛利率是多少？", registry, ask_model=model)

    assert isinstance(got, Intent)
    assert got.metric_id == "gross_profit_margin"
    assert got.entity == "900001"
    assert got.period == 2023
    assert model.calls == [], "别名表命中时不得调用模型"
    assert got.resolved_by["metric"] == "alias_table"


def test_近似命中必须拒答而不是静默换一个指标(registry):
    """🔴 **本文件存在的理由。**

    2026-09-04 实测 frozen-01 `Q-C1-003`：题面是「**净**资产收益率」，
    而别名表里没有这一条，只有「资产收益率」（= `return_on_total_assets`，**总**资产收益率）。
    子串匹配会把 ROE 静默答成 ROA —— **一个看起来完全正常的错误答案**，
    正是本项目要消灭的那一类（与 `N-47` 的静默挑选同型）。

    正确行为：发现命中的别名是一个更长术语的一部分 ⇒ 拒答，并把那个近似项说出来。

    它会红的场景：有人把匹配改回裸子串匹配。
    """
    got = parse_intent("新元（900004）2023 年的净资产收益率是多少？", registry)

    assert isinstance(got, Refusal)
    assert got.code is RefusalCode.METRIC_NOT_DEFINED
    assert "净资产收益率" in got.detail
    # 🔴 报出来的必须是**触发碰撞的那条别名**，不是题面里那个子串。
    # 初版报的是「资产收益率」—— 对读者没用：他要知道的是「我们有的是哪一个」。
    assert "加权平均净资产收益率" in got.detail
    assert "roe_weighted_average" in got.detail
    assert got.metric_id is None, "近似命中不得把那个指标记进拒答记录"


def test_缺主体或缺期间时说明缺的是哪一项(registry):
    """「解析不出来」不是一句话打发 —— 要说缺哪一项，否则提问者不知道该补什么。"""
    no_entity = parse_intent("2023 年的毛利率是多少？", registry)
    assert isinstance(no_entity, Refusal)
    assert no_entity.code is RefusalCode.INTENT_INCOMPLETE
    assert "主体" in no_entity.detail

    no_period = parse_intent("华鑫科技（900001）的毛利率是多少？", registry)
    assert isinstance(no_period, Refusal)
    assert no_period.code is RefusalCode.INTENT_INCOMPLETE
    assert "期间" in no_period.detail


def test_题面出现两个报告期时拒答不取第一个(registry):
    """frozen-01 `Q-C3-004`：「2023 年的期间费用率比 2018 年是上升还是下降」。

    那是跨期比较，不是本路径的三元组。**取第一个是猜**。
    """
    got = parse_intent(
        "华鑫科技（900001）2023 年的期间费用率比 2018 年是上升还是下降？", registry
    )
    assert isinstance(got, Refusal)
    assert got.code is RefusalCode.INTENT_INCOMPLETE
    assert "2018" in got.detail and "2023" in got.detail


def test_别名表落空时才问模型且模型答案仍须过别名表(registry):
    """模型只用来**归一到一个已存在的指标名**，不产生新指标。

    模型说了一个别名表里没有的名字 ⇒ 照样拒答。
    **这条挡的是「模型说是就是」** —— 那等于把口径的权威交给了模型。
    """
    好模型 = 记账假模型(["毛利率"])
    got = parse_intent("华鑫科技（900001）2023 年的销售毛利情况？", registry, ask_model=好模型)
    assert isinstance(got, Intent)
    assert got.metric_id == "gross_profit_margin"
    assert got.resolved_by["metric"] == "model"
    assert len(好模型.calls) == 1

    瞎编模型 = 记账假模型(["自由现金流收益率"])
    bad = parse_intent("华鑫科技（900001）2023 年的某个奇怪指标？", registry, ask_model=瞎编模型)
    assert isinstance(bad, Refusal)
    assert bad.code is RefusalCode.METRIC_NOT_DEFINED


def test_没给模型时不会去自己造一个(registry):
    """`ask_model=None` 是默认值：整条确定性路径必须能离线跑完。"""
    got = parse_intent("华鑫科技（900001）2023 年的某个奇怪指标？", registry)
    assert isinstance(got, Refusal)
    assert got.code is RefusalCode.METRIC_NOT_DEFINED
