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
    # ⚠️ 断的必须是**实际输出**，不是源码文本。断源码是空转：
    #    那三个词在 docstring 里本来就有，把 `main()` 里的 print 全删掉也不会红。
    import contextlib
    import io as _io

    缓冲 = _io.StringIO()
    with contextlib.redirect_stdout(缓冲):
        code = chk.main(["x", str(PACKETS)])
    输出 = 缓冲.getvalue()
    assert code == 0, 输出
    assert "不等于" in 输出 and "AC-06" in 输出, "跑的人未必去读源码，这句得印出来"
    assert "盲审" in 输出 or "人" in 输出, "要说清「谁才给得出那个判断」"


# ── 🔴 查活渲染器，不只查存盘产物 ──────────────────────────────────────


def test_拿当前渲染器现出一份题包也要全过():
    """🔴 **本文件最要紧的一条。**

    上面那些查的是存盘的 `docs/agent/h2-02/packets.md` —— 那份是 2026-09-09
    上午的渲染器出的。**只查存盘产物的检查，查不出渲染器变了。**

    实测：同日把拒答页抬头从「这个数是从哪儿来的」改成「查的是哪份数据」之后，
    存盘那份**照样全绿**，而拿当前渲染器现出一份来跑，15 题里 **9 题**报「缺出处」。
    检查器里抄的那份抬头常量没跟着改，而它的注释恰恰写着「不在这里重写措辞」。

    ⇒ 抬头常量改成从 `agent.answer` **import**，而这一条负责保证
    「改了渲染器就会红」。（`N-42` 那个形态，第六次。）
    """
    import eval.h2 as h2

    packets, _ = h2.build_packets(REPO_ROOT / "eval" / "frozen-01", seed=20260909)
    现出的 = chk.split_packets(h2.render_packets(packets))
    assert len(现出的) == 15

    结果 = {t: chk.check_one(t, b) for t, b in 现出的.items()}
    坏 = {t: g for t, g in 结果.items() if g}
    assert not 坏, 坏

    类型 = {chk.classify(b) for b in 现出的.values()}
    assert "unknown" not in 类型, "有页面认不出类别 —— 拒答措辞改过而 REFUSAL_KINDS 没跟上"


def test_分类判据不许松到互相串门():
    """🔴 也是实测出来的。

    原来有一条判据是「里没有」（想匹配「…里没有 900001/2023 这一行」），
    而同日改过的拒答理由「这句话**里没有**我认得出的指标名」也含这三个字，
    于是「没有这个指标」被误判成「没有这一行」。

    ⚠️ 更要命的是 `unknown` 那条兜底**没兜住**：它确实匹配上了，只是匹配错了。
    **松的判据比没有判据更危险** —— 它让「认不出」这个信号消失了。
    """
    页 = (
        "问的是什么\n    某个问题\n\n"
        "为什么不给答案\n    · 这句话里没有我认得出的指标名。下面列着当时全部可用的叫法。\n\n"
        "我们当时有哪些指标\n    · 毛利率\n\n"
        "查的是哪份数据\n    · 合成夹具（虚构公司与数值），不是任何真实公司的年报\n"
    )
    assert chk.classify(页) == "no_metric", "「没有这个指标」被判成了别的类"
    assert chk.check_one("H2-XX", 页) == []
