"""`scripts/check_h2_selfcontained.py` 的回归。

这道检查是 `h2-02` 的**机械那一半** —— 它替代不了复核，但它替代了
「逐页人工确认三节在不在」。所以它自己必须是会红的：每一节分别挖掉看红。

⚠️ 本文件**不断言任何一道题答得对不对**。那不是这道检查的职责，
也不是它能知道的事（`AC-05` 已知盲区：抓不到「证据不相关」）。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "src"))

import check_h2_selfcontained as chk  # noqa: E402

PACKETS = REPO_ROOT / "docs" / "agent" / "h2-02" / "packets.md"


@pytest.fixture
def 题包():
    assert PACKETS.is_file(), "h2-02 题包不在，先跑 `python -m eval.h2 --out docs/agent/h2-02`"
    return chk.split_packets(PACKETS.read_text(encoding="utf-8"))


def test_当前题包每一页都自足(题包):
    """`h2-02` 的机械读数。红了说明 `D-038` 补的三节有一节没落到某类页面上。"""
    结果 = {t: chk.check_one(t, b) for t, b in 题包.items()}
    坏 = {t: g for t, g in 结果.items() if g}
    assert not 坏, 坏
    assert len(题包) == 15, "题数变了，`EVAL_CASES` §4 的判定门是按 15 题写的"


def test_十五题覆盖了四类页面(题包):
    """光「全都自足」不够 —— 如果 15 题全是同一类，这道检查只测了四分之一。"""
    类型 = {chk.classify(b) for b in 题包.values()}
    assert "answered" in 类型
    assert "no_metric" in 类型
    assert "rule_hit" in 类型
    assert "incomplete" in 类型
    assert "unknown" not in 类型, "有页面认不出类别 —— 拒答措辞改过？"


# ── 负控制：每一节分别挖掉 ──────────────────────────────────────────────


def _挖掉(body: str, 抬头: str) -> str:
    """把某一小节的抬头改名，等价于那一节不存在。"""
    return body.replace(抬头, "被挖掉的小节", 1)


def test_作答页挖掉输入取值那一节要报红(题包):
    tag = next(t for t, b in 题包.items() if chk.classify(b) == "answered")
    gaps = chk.check_one(tag, _挖掉(题包[tag], chk.H_INPUTS))
    assert any("G1" in g for g in gaps), gaps


def test_触发条件页挖掉字段取值那一节要报红(题包):
    tag = next(t for t, b in 题包.items() if chk.classify(b) == "rule_hit")
    gaps = chk.check_one(tag, _挖掉(题包[tag], chk.H_WHY_HIT))
    assert gaps, "挖掉 G2 却没报"


def test_说没有这个指标却不给清单要报红(题包):
    tag = next(t for t, b in 题包.items() if chk.classify(b) == "no_metric")
    gaps = chk.check_one(tag, _挖掉(题包[tag], chk.H_REGISTRY))
    assert any("G3" in g for g in gaps), gaps


def test_任何一页挖掉出处都要报红(题包):
    """`D-010`：把合成夹具说成真实年报，比数据本身更严重。"""
    for tag, body in 题包.items():
        gaps = chk.check_one(tag, _挖掉(body, chk.H_WHERE))
        assert any(chk.H_WHERE in g for g in gaps), (tag, gaps)


def test_只有字段名没有取值要报红(题包):
    """`h2-01` 里 13 题「无法判断」的形状：知道它触发了，不知道触发得对。"""
    tag = next(t for t, b in 题包.items() if chk.classify(b) == "answered")
    body = 题包[tag]
    # 把取值抹掉，只留字段名。
    # ⚠️ 分隔符是**普通空格**不是全角空格 —— `_input_lines` 拼的是全角，
    #    但 `wrap()` 会把空白归一化。首写这条测试时按全角切，切不动，测试空转。
    行 = []
    for l in body.splitlines():
        s_ = l.strip()
        if s_.startswith("·") and re.search(r"[0-9]$", s_):
            行.append(l.rsplit(" ", 1)[0])
        else:
            行.append(l)
    gaps = chk.check_one(tag, "\n".join(行))
    assert any("只有字段名" in g for g in gaps), gaps


# ── 判据与渲染器必须同步 ────────────────────────────────────────────────


def test_渲染器写得出的每一种取值本检查都认(题包):
    """🔴 这条把 `_has_value` 与 `agent.answer._shown` 钉在一起。

    `_shown` 的 docstring 写明三种「没有」必须分开写死。它们**都是有效取值** ——
    首跑时 `H2-04` 的「营业收入　（缺失：数据源里没有这一行）」被误报成缺口，
    因为当时的判据是「有没有数字」。

    `_shown` 哪天改了措辞而 `VALUE_MARKERS` 没跟着改，这条会红；
    没有它，那种情况下检查器会**安静地开始误报**，而误报会让人跳过这个检查。
    """
    from agent.answer import _shown

    for 取值 in (None, "", 0, 123, True, False, "0.5"):
        一行 = "· 营业收入　" + _shown(取值)
        assert chk._has_value(一行), "渲染器写得出 " + repr(_shown(取值)) + "，检查器却不认"


def test_空的或缺失的小节一律不算有取值():
    assert chk._has_value(None) is False
    assert chk._has_value("") is False
    assert chk._has_value("· 营业收入") is False


# ── 它不许声称自己证明了 AC-06 ──────────────────────────────────────────


def test_脚本自己写明它证明不了什么():
    """`AC-05` 的已知盲区是「抓不到证据不相关」。一道只查「材料齐不齐」的检查
    如果不写明这一点，读的人会把它当成 `AC-06` 的证据。
    """
    doc = (REPO_ROOT / "scripts" / "check_h2_selfcontained.py").read_text(encoding="utf-8")
    assert "查不了" in doc
    assert "AC-06" in doc
    # 输出里也要说，不能只写在 docstring 里 —— 跑的人未必去读源码
    assert "不等于" in doc
