"""两组回归，都是 `frozen-02` 冻结之后当场照出来的（2026-09-09）。

1. **同名字段的截断**（`N-68` 第 1 条）——`explain.short_field_names`
2. **`G4`：说「认不出这家公司」时要给出当时认得出哪些**（`N-72`）

🔴 **为什么单开一个文件**：这两件事在 `tests/test_answer.py` 里都**没有**对应的钉子，
而那份文件当时有 1053 道测试全绿。截断 bug 在证据页上活了整整一轮
（`h2-02` 的复核者靠附录里的英文字段 id 才认出来，而那个附录后来被精简掉了）。
⇒ 新钉子放在一处，标题写明它守的是什么，别混进那份大文件里被当成又一条断言。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from agent.answer import FixtureSource, answer_question, render_answer
from semantic_layer.explain import _formula_in_chinese, short_field_names
from semantic_layer.resolve import Registry

REPO = Path(__file__).resolve().parent.parent
FIXTURE = REPO / "eval" / "frozen-01" / "fixtures" / "synthetic-01.yaml"


@pytest.fixture
def registry():
    return Registry.load(REPO / "metrics")


@pytest.fixture
def source():
    return FixtureSource(FIXTURE)


# ───────────────────────── 一、同名字段不许被截平 ─────────────────────────


def test_撞名的两个字段保留全称(registry):
    """`revenue_growth_yoy` 的两个取数字段都叫「营业收入」，靠列限定区分。

    去掉列限定之后它们**同名**⇒ 必须整组退回全称。
    它会红的场景：有人把 `short_field_names` 换回无条件 `split("——")[0]`。
    """
    defn = registry.definitions["revenue_growth_yoy"]
    names = short_field_names(defn)

    本期 = names["is.operating_revenue_current"]
    上期 = names["is.operating_revenue_prior_as_presented"]

    assert 本期 != 上期, "同比的本期与上期在页面上同名 —— 读者无法把值对上字段"
    # 不只是「不相等」：得真的把列限定留住，否则可能是被改成了别的编造名字。
    assert "——" in 本期 and "——" in 上期, "列限定被切掉了，而这里它正是区别本身"
    assert "本期" in 本期 and "上期" in 上期


def test_不撞名时仍然去掉列限定(registry):
    """**反向的一半**：不撞名就该读着清爽，否则这个修复等于把所有页面都变啰嗦。

    毛利率的三个字段短名互不相同 ⇒ 应当保持短名。
    它会红的场景：有人图省事，把所有定义一律改成全称。
    """
    defn = registry.definitions["gross_profit_margin"]
    names = short_field_names(defn)

    assert names["is.operating_revenue_current"] == "营业收入", names
    assert "——" not in names["is.operating_revenue_current"]
    assert len(set(names.values())) == len(names), "毛利率这份定义本来就不该有撞名"


def test_公式不会被渲染成恒等式(registry):
    """`(营业收入 - 营业收入) / 营业收入` 读起来像恒等于零。

    判据不是「字符串等于某个期望值」（那会被措辞改动误伤），
    而是**公式里不出现同一个中文名减它自己**这个结构性事实。
    """
    text = _formula_in_chinese(registry.definitions["revenue_growth_yoy"])
    assert text, "这份定义的公式没渲染出来，本测试在空转"

    左 = text.split(" - ")[0].lstrip("(").strip()
    右 = text.split(" - ")[1].split(") /")[0].strip()
    assert 左 != 右, f"公式渲染成了恒等式：{text}"


def test_G1_同比页上两个输入分得开(registry, source):
    """端到端：证据页的「这个数是拿哪几个数算出来的」两行必须可区分。

    `h2-01` 全部 5 道计算题判「无法判断」的理由就是这一节缺失；
    补上之后如果两行同名不同值，这一节等于**没补** —— 读者仍然重算不了。
    """
    a = answer_question("华鑫科技（900001）2023 年的营收增长率是多少？", registry, source=source)
    assert not a.refused, a.refusal
    assert len(a.inputs) >= 2

    page = render_answer(a, registry.definitions["revenue_growth_yoy"], None)
    节 = page.split("这个数是拿哪几个数算出来的", 1)[1].split("这个数是从哪儿来的", 1)[0]

    标签 = [l.strip().lstrip("· ") for l in 节.splitlines() if l.strip().startswith("·")]
    assert len(标签) >= 2, 节
    # 去掉行尾那个数值，剩下的**标签**必须互不相同，否则读者对不上字段。
    #
    # ⚠️ **不要按分隔符切。** `_input_lines` 用的是全角空格 `　`，
    #    而 `wrap()` 开头的 `" ".join(text.split())` 会把它归一成半角 ——
    #    初版这里写 `s.split("　")[0]`，于是切不开，比的是「标签+值」整串。
    #    值不同 ⇒ 恒绿。**造回归当场抓到它是空转的**（2026-09-09）。
    头 = [re.sub(r"[\s\d.\-]+$", "", s) for s in 标签]
    assert len(set(头)) == len(头), f"这一节有同名行，读者无法把值对上字段：{头}"


# ───────────────────────── 二、`G4` ─────────────────────────


def test_G4_说认不出公司时必须给出当时认得出哪些(registry, source):
    """`D-038 G3` 的同一条原理作用在**主体**这一维。

    「华鑫」是华鑫科技与华鑫股份的共同前缀，两家都不叫「华鑫」
    ⇒ 系统拒答。但光说「认不出」，读者不知道它认得出哪几家，**无从判断拒得对不对**。

    它会红的场景：有人把这一节从 `render_answer` 拿掉，
    或把 `intent.py` 那两处的 `source="intent:entity_table"` 去掉。
    """
    a = answer_question("华鑫 2023 年的毛利率是多少？", registry, source=source)
    assert a.refused, "「华鑫」不是任何一家的登记简称，本该拒答"
    assert a.entity_snapshot, "拒答了却没带主体快照 ⇒ 这句话不可证伪"

    names = a.entity_snapshot["names"]
    assert "华鑫科技" in names and "华鑫股份" in names
    assert "华鑫" not in names, "夹具变了：本测试依赖「华鑫」本身不是登记简称"

    page = render_answer(a, None, None)
    assert "我们当时认得出哪些公司" in page
    for n in ("华鑫科技", "华鑫股份"):
        assert n in page, f"清单没印全，缺 {n}"


def test_G4_不挂在与主体无关的拒答上(registry, source):
    """**证据要相关，不是要多**（`AC-05` 的已知盲区正是「抓不到证据不相关」）。

    缺期间的拒答与「认得出哪些公司」无关，摆出来只会让复核者在 5 分钟里
    翻一页跟他要判的事没关系的东西 —— 这与 `G3` 不挂在 `INTENT_INCOMPLETE` 上同理。
    """
    a = answer_question("华鑫科技（900001）的毛利率是多少？", registry, source=source)
    assert a.refused
    assert a.entity_snapshot is None, "缺期间的拒答不该带主体清单"
    assert "我们当时认得出哪些公司" not in render_answer(a, None, None)


def test_G4_判据是责任方标识不是拒答措辞(registry, source):
    """按措辞匹配正是 `EVAL_CASES` §5.3 / `L-50` 点名禁的那类判据。

    `N-65` 改过一次这句话的措辞（「没有主体」→「没有认得出的公司」），
    若判据挂在措辞上，那次改动会让这一节**静默消失**。
    """
    from agent.intent import parse_intent

    r = parse_intent("华鑫 2023 年的毛利率是多少？", registry, entity_names=source.entity_names)
    assert r.__class__.__name__ == "Refusal"
    assert r.source == "intent:entity_table", "责任方标识没挂上 ⇒ 证据页那一节会失效"


# ─────────── `G4` 必须标出虚构公司（2026-09-10 线上实测发现的自相矛盾） ───────────

REAL_FIXTURE = REPO / "data" / "extracted" / "600519_2023.yaml"


def test_G4_合成公司当场标成虚构(registry, source):
    """🔴 `coverage.py:106` 刻意**不显示**合成公司的简称（免得有人去搜一家
    不存在的公司），而 `G4` 把它们全列了出来 —— 两处对同一件事的处置相反。

    解法不是让 `G4` 也藏起来：藏了，「认不出这家公司」就重新变成
    不可证伪的断言，`G4` 的全部作用就没了。**列出来 + 标明**。

    它会红的场景：有人把标注去掉，或让 `entity_snapshot` 不再带 `natures`。
    """
    a = answer_question("华鑫 2023 年的毛利率是多少？", registry, source=source)
    assert a.refused
    snap = a.entity_snapshot
    assert snap["natures"], "快照没带 natures ⇒ 页面无从区分真假"
    assert set(snap["natures"].values()) == {"synthetic"}, snap["natures"]
    assert snap["synthetic_count"] == snap["entity_count"]

    page = render_answer(a, None, None)
    节 = page.split("我们当时认得出哪些公司", 1)[1]
    for n in ("华鑫科技", "华鑫股份"):
        assert n in 节
    # 每一个虚构公司都要带标注，不是只在抬头说一句。
    行 = [l for l in 节.splitlines() if l.strip().startswith("· ") and "认出" not in l]
    assert 行, 节
    for l in 行:
        assert "虚构" in l, f"这一行没标虚构：{l!r}"


def test_G4_真实公司不带虚构标注(registry):
    """**反方向的一半**：别把所有公司一律标成虚构，那样标注就没有信息了。

    真实年报抽取结果（`kind: real` 且带 64 位 PDF 指纹）不该被标。
    """
    if not REAL_FIXTURE.is_file():
        pytest.skip("没有真实抽取结果，跳过")
    src = FixtureSource(REAL_FIXTURE)
    assert src.is_real, "这份夹具不是 kind: real，本测试选错了文件"
    assert set(src.entity_natures.values()) == {"real"}, src.entity_natures

    a = answer_question("贵州 2023 年的毛利率是多少？", registry, source=src)
    assert a.refused, "「贵州」不是登记简称，本该拒答"
    page = render_answer(a, None, None)
    节 = page.split("我们当时认得出哪些公司", 1)[1]
    行 = [l for l in 节.splitlines() if "贵州茅台" in l]
    assert 行, 节
    assert not any("虚构" in l for l in 行), f"真实公司被标成虚构了：{行}"


def test_G4_来源认不出时按合成算(registry):
    """fail-closed 的方向：把真的标成虚构只是保守，把虚构的标成真的是 `D-010` 红线。"""
    from agent.answer import entity_snapshot

    snap = entity_snapshot({"甲": "900001", "乙": "900002"}, {"甲": "real"})
    assert snap["natures"] == {"甲": "real", "乙": "synthetic"}, snap["natures"]
    assert snap["synthetic_count"] == 1

    # 完全不给 natures ⇒ 全部按合成算
    snap2 = entity_snapshot({"甲": "900001"}, None)
    assert snap2["natures"] == {"甲": "synthetic"}


def test_G4_快照哈希不受标注影响(registry):
    """`sha256` 证明的是「这一页列的就是当时那份**名字表**」。

    把 `natures` 混进哈希，会让同一份表因为标注变化而换指纹 ——
    那句话就失去了指称。
    """
    from agent.answer import entity_snapshot

    a = entity_snapshot({"甲": "900001"}, {"甲": "real"})
    b = entity_snapshot({"甲": "900001"}, {"甲": "synthetic"})
    assert a["sha256"] == b["sha256"], "标注变了指纹也变 ⇒ 指纹指的不再是名字表"
    assert a["natures"] != b["natures"]
