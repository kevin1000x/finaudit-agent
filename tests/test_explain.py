"""`semantic_layer.explain` 的回归（`N-20`）。

这个视图的价值全在「它说的就是定义说的」。一旦它开始加工内容，
读者读到的是渲染器的观点而不是定义本身，那比读不懂更糟 ——
读不懂至少是显性的。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from semantic_layer.definition import load_definition
from semantic_layer.explain import _formula_in_chinese, _resolve_ref, render_explanation

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture
def defn():
    return load_definition(REPO / "metrics" / "period_expense_ratio.yaml")


def test_陷阱被完整二分不丢不重(defn):
    """🔴 **这条是本模块存在的理由。**

    原来「有机械后果」与「只是提示」的区别只在一条陷阱写的是
    `enforced_by` 还是 `advisory_only: true` —— 七条要逐条比对键名。
    这里拆成两节，那么**二分必须是完备且互斥的**：
    少一条 = 有条陷阱在视图里消失了，而读者不会知道。
    """
    out = render_explanation(defn)
    enforced = [p for p in defn.common_pitfalls if not p.advisory_only]
    advisory = [p for p in defn.common_pitfalls if p.advisory_only]

    assert len(enforced) + len(advisory) == len(defn.common_pitfalls)
    assert f"会改变结果的注意事项（{len(enforced)} 条）" in out
    assert f"仅供参考，不影响计算（{len(advisory)} 条）" in out


def test_每条拒答条件都出现且带中文理由(defn):
    """「什么时候拒答」是判据的第一问。少列一条 = 读者以为它不会拒。"""
    out = render_explanation(defn)
    assert defn.undefined_conditions, "这份定义应当有拒答条件，夹具选错了"
    for cond in defn.undefined_conditions:
        assert cond.reason, "拒答条件缺 reason，视图就只能给表达式"
        assert cond.reason.split("；")[0] in out
        assert cond.expr in out, "机器判据必须一并留着，否则没法核对两版是否一致"


def test_下标引用被解析成原文而不是留一个数字(defn):
    """`report.py` 早就记过这条代价：下标「重排列表会静默指向别处」。

    `由这里执行：undefined_conditions.2` 对旁人是无意义的。
    """
    assert _resolve_ref(defn, "undefined_conditions.2").startswith("拒答条件「")
    assert defn.undefined_conditions[2].reason.split("；")[0] in _resolve_ref(
        defn, "undefined_conditions.2"
    )
    # 解不开的原样返回 —— 不编一个好看的说法，否则指错了也看不出来。
    assert _resolve_ref(defn, "something.unknown") == "something.unknown"


def test_公式换不动时返回None而不是给半中文半代码(defn):
    """换了一半的公式比原样更难读，还会让人以为剩下那半是特意保留的。"""
    assert _formula_in_chinese(defn) == "(销售费用 + 管理费用 + 财务费用) / 营业收入"

    # 去掉字段的中文行项目名之后，就换不动了 —— 此时必须是 None。
    for sf in defn.source_fields:
        sf.line_item = None
    assert _formula_in_chinese(defn) is None


def test_二十份定义全部渲染得出来不抛异常():
    """视图要能用在全部定义上，不是只在挑出来的两份上好看。"""
    paths = [p for p in sorted((REPO / "metrics").glob("*.yaml")) if not p.name.startswith("_")]
    assert len(paths) == 20
    for p in paths:
        out = render_explanation(load_definition(p))
        assert "这是什么" in out and "什么时候不给答案" in out
        # dataclass 的 repr 漏进输出过一次，锁住它。
        assert "StandardBasis(" not in out
