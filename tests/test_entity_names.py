"""`N-65` —— 公司简称认成六位代码。

来源是 `h2-02` 的一道 FAIL：题面「华鑫科技 2023 年的资产负债率是多少？」
该答 0.55，系统回「题面里没有主体（六位股票代码）」。
盲审三个人里有两个被那句措辞误导过 —— **题面里明明有公司名，缺的是代码**。

🔴 **这件事刻意不交给模型。** `intent.py` 第一条硬约束是
「能确定性解决的不交给模型」，而「简称 → 代码」是一次查表。
拿模型去做查表，等于把一个确定性映射换成一个会错的映射。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from agent.answer import FixtureSource, answer_question, render_answer  # noqa: E402
from agent.intent import parse_intent  # noqa: E402
from semantic_layer.resolve import Refusal, Registry  # noqa: E402

FIXTURE = REPO_ROOT / "eval" / "frozen-01" / "fixtures" / "synthetic-01.yaml"
REAL = REPO_ROOT / "data" / "extracted" / "600519_2023.yaml"


@pytest.fixture
def registry():
    return Registry.load(REPO_ROOT / "metrics")


@pytest.fixture
def source():
    return FixtureSource(FIXTURE)


# ── 表从数据源自己来 ────────────────────────────────────────────────────


def test_简称表来自数据源本身而不是另立一张名录(source):
    """🔴 **能解析的简称 = 我们真的有数据的公司。**

    另立一张公司名录，它迟早会包含我们答不了的公司 —— 而那时拒答理由会从
    「没有这家公司的数据」退化成「认不出主体」，读者反而更难判。
    """
    assert source.entity_names == {
        "华鑫科技": "900001",
        "华鑫股份": "900002",
        "长风制造": "900003",
        "startup 新元": "900004",
    }


def test_真实年报文件的简称也进表():
    """两种文件形状不同：合成夹具是 `entities:` 列表，真实抽取结果是 `meta` 单条。"""
    if not REAL.is_file():
        pytest.skip("真实抽取结果不在，跑 `python -m extractor export`")
    assert FixtureSource(REAL).entity_names == {"贵州茅台": "600519"}


def test_换一行取数之后简称表还在(source):
    """`at()` 会重建一个 `FixtureSource`。表掉了的话服务侧第二次请求就废了。"""
    assert source.at("900001", 2023).entity_names == source.entity_names


# ── 认得出、且不认错 ────────────────────────────────────────────────────


def test_简称能答出和代码一样的数(registry, source):
    按名 = answer_question("华鑫科技 2023 年的资产负债率是多少？", registry, source=source)
    按码 = answer_question("900001 2023 年的资产负债率是多少？", registry, source=source)
    assert not 按名.refused, 按名.refusal
    assert 按名.value == 按码.value
    assert 按名.evidence["entity_resolved_by"] == "公司简称「华鑫科技」"
    assert 按码.evidence["entity_resolved_by"] == "六位代码"


def test_两家近似简称各归各的(registry, source):
    """夹具里「华鑫科技」与「华鑫股份」是**故意**放的一对近似名。"""
    a = answer_question("华鑫科技 2023 年的资产负债率是多少？", registry, source=source)
    b = answer_question("华鑫股份 2023 年的资产负债率是多少？", registry, source=source)
    assert a.entity == "900001" and b.entity == "900002"
    assert a.value != b.value


def test_只给共同前缀时拒答而不是挑一家(registry, source):
    """🔴 与指标那边的近似命中同一条纪律：**分不清就拒答，不猜。**

    「华鑫」既可能是华鑫科技也可能是华鑫股份。挑一个，用户拿到的是一个
    看起来完全正常的错答案。
    """
    a = answer_question("华鑫 2023 年的资产负债率是多少？", registry, source=source)
    assert a.refused
    assert a.refusal["code"] == "INTENT_INCOMPLETE"


def test_题面里出现两家公司时拒答(registry, source):
    got = parse_intent(
        "华鑫科技和长风制造 2023 年的资产负债率哪个高？",
        registry,
        entity_names=FixtureSource(FIXTURE).entity_names,
    )
    assert isinstance(got, Refusal)
    assert "多家公司" in got.detail


def test_题面里有代码时不走简称(registry, source):
    """代码是唯一标识，简称会重名、会变更。**顺序不是偏好问题。**"""
    got = parse_intent(
        "华鑫股份（900001）2023 年的资产负债率是多少？",
        registry,
        entity_names=source.entity_names,
    )
    assert not isinstance(got, Refusal)
    assert got.entity == "900001"          # 代码说了算
    assert got.resolved_by["entity"] == "六位代码"


# ── 措辞：`h2-02` 盲审两个人被误导过的那一句 ────────────────────────────


def test_有简称表时的拒答措辞不再说没有主体(registry, source):
    a = answer_question("某某公司 2023 年的资产负债率是多少？", registry, source=source)
    assert a.refused
    detail = a.refusal["detail"]
    assert "没有主体" not in detail, "旧措辞：题面里明明有公司名，说「没有主体」会让人以为它没读出来"
    assert "简称" in detail and "六位股票代码" in detail


def test_没有数据源时退回旧措辞(registry):
    """离线解析（不给 source）时简称整条不生效，就不该承诺简称能用。"""
    got = parse_intent("某某公司 2023 年的资产负债率是多少？", registry)
    assert isinstance(got, Refusal)
    assert "六位股票代码" in got.detail


# ── 证据页要说出这一步 ──────────────────────────────────────────────────


def test_查表查到的主体要印在证据页上(registry, source):
    """多走了一步就得说出来 —— 与 `metric_resolved_by` 同一个理由。
    读者得能核「它认成的那家，是不是我问的那家」。
    """
    a = answer_question("华鑫科技 2023 年的资产负债率是多少？", registry, source=source)
    page = render_answer(a, registry.resolve(a.metric_id))
    assert "华鑫科技" in page
    assert "查表查到的" in page
    assert "主体怎么定下来的" in page


def test_题面直接给代码时不印那一句(registry, source):
    """反面。少了它，上一条可以靠「这句永远都印」蒙混过关。"""
    a = answer_question("900001 2023 年的资产负债率是多少？", registry, source=source)
    page = render_answer(a, registry.resolve(a.metric_id))
    assert "查表查到的" not in page
    assert "主体怎么定下来的" in page      # 附录那一份每页都印


# ── 服务侧：多份数据源合表 ──────────────────────────────────────────────


def test_服务侧把几份数据源的简称并起来():
    from service import api

    表 = api._pick_source().entity_names
    assert 表.get("贵州茅台") == "600519"      # 真实抽取结果
    assert 表.get("华鑫科技") == "900001"      # 合成夹具
    assert api._pick_source().ambiguous_names == frozenset()


def test_两份数据源对同一个简称给不同代码时那个简称整条丢掉(tmp_path):
    """🔴 与「只给共同前缀就拒答」同一条纪律：**分不清就不猜。**

    留下任意一个，用户拿到的是一个看起来完全正常的错答案；
    丢掉，他拿到的是一句「认不出这家公司」。后者可以被纠正，前者不会。
    """
    from service.api import _Sources

    甲 = tmp_path / "a.yaml"
    乙 = tmp_path / "b.yaml"
    甲.write_text(
        "meta: {fixture_id: a}\nentities:\n"
        "  - {short_name: 同名公司, stock_code: '900001'}\n"
        "  - {short_name: 只在甲里, stock_code: '900009'}\nrows: []\n",
        encoding="utf-8",
    )
    乙.write_text(
        "meta: {fixture_id: b}\nentities:\n"
        "  - {short_name: 同名公司, stock_code: '900002'}\nrows: []\n",
        encoding="utf-8",
    )
    合 = _Sources([甲, 乙])
    assert "同名公司" not in 合.entity_names
    assert 合.ambiguous_names == frozenset({"同名公司"})
    assert 合.entity_names.get("只在甲里") == "900009", "不冲突的那些不该被牵连"


# ── `N-69`：多期间的拒答措辞要对两种读法都成立 ──────────────────────────


def test_多个期间的拒答要把两种读法都说出来(registry, source):
    """🔴 旧措辞「那是跨期比较，不是本路径的三元组」**对其中一类是错的**。

    「2023 年的营业收入**比 2022 年**增长了多少」要的是**一个**同比数 ——
    第二个年份是比较基准，不是第二个查询期间，而同比类指标的定义
    自己就知道去取上期（只写一个年份照样算得出，见 `Q-C3-001`）。

    这里**不猜**是哪一类（判据只能是启发式的，猜错的方向是「该拒答时答了」），
    而是把两种读法都摆出来、各自告诉提问者怎么办。
    """
    a = answer_question(
        "华鑫科技（900001）2023 年的期间费用率比 2018 年是上升还是下降？分别是多少？",
        registry, source=source,
    )
    assert a.refused and a.refusal["code"] == "INTENT_INCOMPLETE"
    detail = a.refusal["detail"]
    assert "跨期比较" in detail, "要说清「各一个数」那条路走不通"
    assert "同比" in detail and "基准年" in detail, "要告诉提问者另一条路怎么走"
    assert "不是本路径的三元组" not in detail, "旧措辞：对带基准年的同比问法是错的"


def test_带基准年的同比问法今天够不到期间那一步(registry, source):
    """⚠️ 记录一个**当前事实**，不是主张它对。

    「2023 年的营业收入比 2022 年增长了多少」今天拒在**更早**的地方 ——
    `METRIC_NOT_DEFINED`（那句话里没有出现任何一条别名），根本走不到期间检查。

    也就是说上一条改好的措辞，这道题**读不到**。两件事都在 `N-69` 里：
    别名覆盖不够 + 期间语义不分。写这条是为了让「哪天别名覆盖上了」这件事
    有一处会红 —— 那时这条测试会失败，而失败正是提醒：
    该回去看看新的拒答理由对不对了。
    """
    a = answer_question(
        "华鑫科技（900001）2023 年的营业收入比 2022 年增长了多少？",
        registry, source=source,
    )
    assert a.refused
    assert a.refusal["code"] == "METRIC_NOT_DEFINED", (
        "别名覆盖上了？那就回去核 `N-69`：这道题现在会走到期间检查，"
        "而那句拒答理由对「带基准年的同比」是不是还成立，要重新看一遍"
    )
