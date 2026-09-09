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
        # 简称
        "华鑫科技": "900001",
        "华鑫股份": "900002",
        "长风制造": "900003",
        "startup 新元": "900004",
        # 全称（2026-09-10 一并登记；说明性括注剥掉）——
        # 不登的话，用户打公司自己的注册全称会被右边界当成「另一家更长的公司」拒掉。
        "华鑫科技股份有限公司": "900001",
        "华鑫控股股份有限公司": "900002",
        "长风精密制造股份有限公司": "900003",
        "新元生物科技股份有限公司": "900004",
    }


def test_真实年报文件的简称也进表():
    """两种文件形状不同：合成夹具是 `entities:` 列表，真实抽取结果是 `meta` 单条。"""
    if not REAL.is_file():
        pytest.skip("真实抽取结果不在，跑 `python -m extractor export`")
    assert FixtureSource(REAL).entity_names == {
        "贵州茅台": "600519",
        "贵州茅台酒股份有限公司": "600519",
    }


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


def test_只给共同前缀时拒答(registry, source):
    """⚠️ **它走的不是「多家公司」那条分支**，别被名字骗了。

    「华鑫」是华鑫科技与华鑫股份的共同前缀，但代码根本不把它看成歧义 ——
    表里没有「华鑫」这个键，于是一个都没命中，走的是「认不出这家公司」那条路。
    真正守住「多家公司」分支的是下面那条 `test_题面里出现两家公司时拒答`。

    这条仍然有价值：它守的是**不许拿前缀去凑一家**（比如把匹配改成
    「表里哪个名字以题面里的字串开头」，这条会立刻红）。
    """
    a = answer_question("华鑫 2023 年的资产负债率是多少？", registry, source=source)
    assert a.refused
    assert a.refusal["code"] == "INTENT_INCOMPLETE"
    assert "没有认得出的公司" in a.refusal["detail"], "走的应当是「认不出」那条分支"


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
    # ⚠️ 断的是**新旧两句里只有旧的才有**的那几个字。
    #    只断「六位股票代码」是空转 —— 新措辞里也有这五个字，
    #    把 `if entity_names:` 那个分支删掉让它永远走新措辞，照样绿。
    assert "没有主体" in got.detail
    assert "简称" not in got.detail


# ── 证据页要说出这一步 ──────────────────────────────────────────────────


def test_查表查到的主体要印在证据页上(registry, source):
    """多走了一步就得说出来 —— 与 `metric_resolved_by` 同一个理由。
    读者得能核「它认成的那家，是不是我问的那家」。
    """
    a = answer_question("华鑫科技 2023 年的资产负债率是多少？", registry, source=source)
    page = render_answer(a, registry.resolve(a.metric_id))
    # ⚠️ 不断「"华鑫科技" in page」—— 那是**恒真**的：`render_answer` 第一件事
    #    就是把题面原样印在「问的是什么」下面。要断就断**出处那一节里**有它。
    出处 = page.split("这个数是从哪儿来的")[1].split("用的是哪个口径")[0]
    assert "华鑫科技" in 出处
    assert "查表查到的" in 出处
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


# ── 左边必须是边界（独立复核 2026-09-09 实测出来的） ────────────────────


def test_名字左边紧挨着汉字时拒答(registry, source):
    """🔴 **本文件最要紧的一条。** 独立复核实测出来的一个真危险。

    修这条之前，「**南**华鑫科技 2023 年的资产负债率是多少？」**答出了 0.55** ——
    华鑫科技的数，页面上一句异常都没有。那正是 `intent.py` 抬头写的
    「一个看起来完全正常的错误答案」。

    「南华鑫科技」里确实含有「华鑫科技」四个字，但它几乎一定是另一家公司。
    """
    for q in ("南华鑫科技 2023 年的资产负债率是多少？",
              "新华鑫科技 2023 年的资产负债率是多少？"):
        a = answer_question(q, registry, source=source)
        assert a.refused, q + " 又开始答了"
        assert a.refusal["code"] == "INTENT_INCOMPLETE"
        assert "一部分" in a.refusal["detail"]


def test_先判多家再判只认出一截(registry, source):
    """🔴 顺序。反了会误伤「A**和**B」——「和」是连词，不是名字的一部分。

    首版就是反的（先判左边界），而已有的
    `test_题面里出现两家公司时拒答` 当场把它抓了出来。
    这一条把顺序本身钉住。
    """
    a = answer_question(
        "华鑫科技和长风制造 2023 年的资产负债率哪个高？", registry, source=source
    )
    assert a.refused
    assert "多家公司" in a.refusal["detail"], "被误判成「只认出一截」了"
    assert "一部分" not in a.refusal["detail"]


def test_右边紧挨着别的汉字要拦(registry, source):
    """`N-70` 收口（2026-09-10）。**本条原先钉的是相反的行为**。

    原测试叫「右边紧挨着汉字今天不拦这是已知的洞」，记录的是一个当时补不上的洞，
    并写着「哪天有人把右侧也守上，它会红 —— 那时应当回来确认『的』那类问法
    没有被一起误拒」。右侧守上了，它红了，这里按它的指示翻过来 ——
    它点名要核的那件事由下一条 `test_最自然的问法不许被误拒` 守着。

    「华鑫科技集团有限公司」与「华鑫科技」很可能是两家（母公司与上市子公司
    在中国常常分立）。拿前者的问题答出后者的数，又是一个看起来完全正常的错数。
    """
    a = answer_question(
        "华鑫科技集团有限公司 2023 年的资产负债率是多少？", registry, source=source
    )
    assert a.refused, "「…集团有限公司」被认成了「华鑫科技」——那是另一家公司的数"
    # 🔴 **钉的是方向，不是「一部分」这三个字**（2026-09-10 独立复核抓到）。
    #    本条初版写 `assert "一部分" in detail`，而当时右边界复用了左边界的文案
    #    「它**前面**还连着别的字」—— 多出来的字明明在后面。
    #    于是这条测试把一句说反方向的诊断**钉成了行为**。
    #    本仓已为拒答措辞误导返工过两次（`N-65`、`h2-02` 盲审两人读错「指标名」）。
    assert "后面" in a.refusal["detail"], a.refusal["detail"]
    assert "前面" not in a.refusal["detail"]


def test_右边是别名时不算越界(registry, source):
    """判据靠**别名表自己**，不靠编一张修饰语词表。

    「华鑫科技资产负债率是多少」里，名字右边紧跟的是一个注册别名的开头
    ⇒ 那就是边界。若改成按「后面是不是汉字」一刀切，这条会红。
    """
    a = answer_question("华鑫科技资产负债率是多少？2023 年", registry, source=source)
    assert not a.refused, a.refusal
    assert a.entity == "900001"


def test_拿不到别名表时右边界只认前两类(registry):
    """fail-closed：`registry` 缺席时宁可误拒，不可误答。

    `parse_intent` 总会带上 registry，本条守的是 `_match_entities` 自己的契约 ——
    将来若有别的调用方不传，它不能悄悄退化成「什么都放行」。
    """
    from agent.intent import _AMBIGUOUS_SUFFIX, _match_entities

    表 = {"华鑫科技": "900001"}
    assert _match_entities("华鑫科技的毛利率", 表, None) == ["华鑫科技"]
    assert _match_entities("华鑫科技2023年", 表, None) == ["华鑫科技"]
    # 右边界越界返回的是 `_AMBIGUOUS_SUFFIX`，不是 `_PREFIX` ——
    # 两个哨兵分开，页面才说得出多的字在前面还是后面。
    assert _match_entities("华鑫科技集团有限公司", 表, None) is _AMBIGUOUS_SUFFIX
    # 没有别名表时，连「资产负债率」也认不出来 ⇒ 保守地拒
    assert _match_entities("华鑫科技资产负债率", 表, None) is _AMBIGUOUS_SUFFIX


def test_最自然的问法不许被误拒(registry, source):
    """「…的资产负债率是多少」——名字右边紧跟着「的」。这是最常见的问法。"""
    a = answer_question("华鑫科技的资产负债率是多少？2023 年", registry, source=source)
    assert not a.refused, a.refusal
    assert a.entity == "900001"


# ── 畸形入参不许崩（拒答是正常结果，崩不是） ────────────────────────────


@pytest.mark.parametrize(
    "坏表",
    [["华鑫科技"], {900001: "900001"}, {"华鑫科技": None}, "字符串不是表", 42],
)
def test_简称表畸形时拒答而不是抛(registry, 坏表):
    got = parse_intent("华鑫科技 2023 年的资产负债率是多少？", registry, entity_names=坏表)
    assert isinstance(got, Refusal), "畸形的表不该让它答出一个数"


def test_数据文件里entities写歪一行也不许崩(tmp_path):
    """这个构造在**每次请求**的路径上，抛出去就是 5xx。数据文件也是输入。"""
    p = tmp_path / "歪.yaml"
    p.write_text(
        "meta: {fixture_id: x}\nentities:\n  - 华鑫科技\n"
        "  - {short_name: 长风制造, stock_code: '900003'}\nrows: []\n",
        encoding="utf-8",
    )
    src = FixtureSource(p)
    assert src.entity_names == {"长风制造": "900003"}, "写歪的那一行应当被跳过，不是让它崩"


# ── 全称、组织形式后缀、两侧对称（2026-09-10 独立复核的 P1/P3） ──────────


def test_公司自己的注册全称不许被拒(registry, source):
    """🔴 独立复核抓到的 P1。

    「华鑫科技股份有限公司」是这家公司**自己的注册全称**，逐字写在
    同一份夹具的 `full_name` 里。而 `FixtureSource` 此前只登记 `short_name`
    ⇒ 用户打全称时，右边界看到「股份有限公司」几个字，判成「另一家更长的公司」。
    **它不是另一家。**

    它会红的场景：有人把 `full_name` 的登记去掉。
    """
    a = answer_question(
        "华鑫科技股份有限公司 2023 年的毛利率是多少？", registry, source=source
    )
    assert not a.refused, a.refusal
    assert a.entity == "900001"


def test_真实公司的全称也不许被拒(registry):
    """真实抽取结果那一侧同一件事。

    ⚠️ 这条**不能**只靠组织形式后缀表解决：「贵州茅台酒股份有限公司」
    比简称多出来的是「**酒**股份有限公司」，那个「酒」任何后缀表都盖不住。
    所以 `full_name` 必须真的登记进去。
    """
    if not REAL.is_file():
        pytest.skip("没有真实抽取结果")
    src = FixtureSource(REAL)
    assert "贵州茅台酒股份有限公司" in src.entity_names, src.entity_names
    a = answer_question("贵州茅台酒股份有限公司 2023 年的毛利率", registry, source=src)
    assert not a.refused, a.refusal


def test_全称里的说明性括注不进名录(registry, source):
    """夹具写的是「华鑫科技股份有限公司（虚构）」——那个括注是给读文件的人看的，

    用户不会把它打进提问里。登记时剥掉，**但只剥结尾整对全角括号**。
    """
    assert "华鑫科技股份有限公司" in source.entity_names
    assert "华鑫科技股份有限公司（虚构）" not in source.entity_names


def test_组织形式后缀不算越界而集团算(registry, source):
    """`公司` 是同一家的强信号，`集团` 不是 —— `X集团有限公司` 与 `X股份有限公司`

    在中国常常是两个法人（未上市母公司 vs 上市子公司）。
    """
    通 = answer_question("华鑫科技公司 2023 年的毛利率", registry, source=source)
    assert not 通.refused, 通.refusal

    拒 = answer_question("华鑫科技集团有限公司 2023 年的毛利率", registry, source=source)
    assert 拒.refused, "「集团」被当成了组织形式后缀 —— 那正是这道门要拦的"


def test_左边界也认分隔虚词(registry, source):
    """「2023**年**华鑫科技的毛利率」是最常见的中文语序之一。

    卡住它的那个「年」字本来就在 `_BOUNDARY_CHARS` 里，而左边界此前没用那张表
    ⇒ 一边严一边松。两侧现在用同一张表。

    ⚠️ **「南华鑫科技」仍然要拒** —— 「南」不在表里。
    """
    通 = answer_question("2023年华鑫科技的毛利率是多少", registry, source=source)
    assert not 通.refused, 通.refusal
    assert 通.entity == "900001"

    拒 = answer_question("南华鑫科技 2023 年的毛利率是多少？", registry, source=source)
    assert 拒.refused, "左边界被放松过头了"
