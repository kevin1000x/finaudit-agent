"""`src/agent/verify.py` 的回归（`R-1`，`D-041`）。

盯四件事，逐条对应 `D-041` 的四条：

1. **一个输入框自己判**：`read_as` 的判据是「有没有一个没被主体/期间消耗掉的数值」；
2. **判错了不藏**：读成什么、承接了什么，都要在报告里印得出来；
3. **五态是封闭集**：枚举恰好五个，且五个**都真的可达** ——
   一个永远不会出现的判定与不存在的判定没有区别；
4. **不算数、不判口径**：这一层不产生任何新指标，比较用的数一律来自
   `answer_question`，用户写的那个数**只进比较，不进取数**。
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from agent.verify import (
    Claim,
    ReadAs,
    Verdict,
    read_input,
    render_report,
    split_segments,
    stated_value,
)
from service import api
from semantic_layer.resolve import Registry

REPO = Path(__file__).resolve().parent.parent
#: 真实的那一份：茅台 2023，29/29 字段人工核对签署（`VERIFICATION.md` §D.16/§D.17）。
REAL = REPO / "data" / "extracted" / "600519_2023.yaml"


@pytest.fixture
def registry():
    return Registry.load(REPO / "metrics")


@pytest.fixture
def source():
    """服务用的那一套数据源，不是单独造一份 —— 核查报告要跟线上是同一套。"""
    return api._pick_source()


# --------------------------------------------------------------------------
# 1. 数值抽取：判据是「遮掉主体与期间之后还剩不剩数」
# --------------------------------------------------------------------------


def test_六位代码不算待核数值():
    """`600519` 是主体，不是用户写下的那个数。"""
    assert stated_value("600519 的资产负债率是多少") is None


def test_年份不算待核数值():
    assert stated_value("2023 年的资产负债率是多少") is None


def test_主体与期间同时出现时仍然认不出数值():
    assert stated_value("贵州茅台 600519 在 2023 年的表现如何") is None


def test_百分数按百分之一折算并带上末位容差():
    got = stated_value("净利率 50.6%")
    assert got is not None
    assert got.value == Decimal("50.6") * Decimal("0.01")
    # 「50.6%」说的是 50.55%–50.65%，半个末位 = 0.0005。
    assert got.tolerance == Decimal("0.0005")


def test_逗号分组的数不被切成两个数():
    """`1,477.5` 切成 `1` 与 `477.5` 时两个都是假的。"""
    got = stated_value("营业收入 1,477.5 亿元")
    assert got is not None
    assert got.value == Decimal("1477.5") * (Decimal(10) ** 8)


def test_个百分点被认成变动而不是水平值():
    got = stated_value("同比提升 1.2 个百分点")
    assert got is not None
    assert got.is_delta is True


def test_百分号不被误认成变动():
    got = stated_value("净利率 50.6%")
    assert got is not None
    assert got.is_delta is False


# --------------------------------------------------------------------------
# 2. 断句
# --------------------------------------------------------------------------


def test_按标点切句():
    assert split_segments("甲。乙；丙，丁") == ["甲", "乙", "丙", "丁"]


def test_顿号不切():
    """「营业收入、净利润都增长了」是一条声明的两个主语，切开是两条碎片。"""
    assert split_segments("营业收入、净利润都增长了") == ["营业收入、净利润都增长了"]


def test_空片段被丢掉():
    assert split_segments("甲。。。乙。") == ["甲", "乙"]


# --------------------------------------------------------------------------
# 3. `read_as`：一个输入框，系统自己判（`D-041` §1）
# --------------------------------------------------------------------------


def test_没有待核数值时读成提问并走问答路径(registry, source):
    rep = read_input("贵州茅台 2023 年的资产负债率是多少？", registry, source=source)
    assert rep.read_as is ReadAs.QUESTION
    assert rep.claims == []
    # 🔴 问答能力没有消失 —— 它就在核查里面。
    assert rep.answer is not None and not rep.answer.refused


def test_带了一个数就读成待核声明(registry, source):
    rep = read_input("贵州茅台 2023 年的资产负债率是 17.98%。", registry, source=source)
    assert rep.read_as is ReadAs.STATEMENT
    assert rep.answer is None
    assert len(rep.claims) == 1


# --------------------------------------------------------------------------
# 4. 五态：**五个都要可达**
# --------------------------------------------------------------------------


def _verdicts(rep):
    return [c.verdict for c in rep.claims]


def test_可核且一致(registry, source):
    rep = read_input("600519 在 2023 年的资产负债率为 17.98%。", registry, source=source)
    assert _verdicts(rep) == [Verdict.CONSISTENT]


def test_可核但不一致(registry, source):
    """口径写全了（「归母净利率」是正式名），数写错了。"""
    rep = read_input("贵州茅台 2023 年归母净利率是 0.4525。", registry, source=source)
    assert _verdicts(rep) == [Verdict.INCONSISTENT]


def test_口径未声明时不判一致也不判不一致(registry, source):
    """「净利率」不带口径限定，而系统替用户选了归母口径 —— 这次选择要让用户看见。"""
    rep = read_input("贵州茅台 2023 年净利率 50.6%。", registry, source=source)
    assert _verdicts(rep) == [Verdict.AMBIGUOUS_BASIS]
    # 🔴 不是「不给结论」：比较结果仍然说出来，只是不写成「一致」。
    assert "对得上" in rep.claims[0].reason
    assert "换一个口径就是另一个数" in rep.claims[0].reason


def test_数据不覆盖(registry, source):
    rep = read_input("000651 在 2023 年的资产负债率为 55%。", registry, source=source)
    assert _verdicts(rep) == [Verdict.NOT_COVERED]


def test_不是可核声明(registry, source):
    rep = read_input(
        "贵州茅台 2023 年净利率 50.6%，盈利能力持续增强。", registry, source=source
    )
    assert _verdicts(rep)[-1] is Verdict.NOT_CHECKABLE


def test_五态全部可达(registry, source):
    """一个永远不会出现的判定与不存在的判定没有区别 —— 逐个走通。"""
    到过 = set()
    for text in (
        "600519 在 2023 年的资产负债率为 17.98%。",
        "贵州茅台 2023 年归母净利率是 0.4525。",
        "贵州茅台 2023 年净利率 50.6%。",
        "000651 在 2023 年的资产负债率为 55%。",
        "贵州茅台 2023 年净利率 50.6%，盈利能力持续增强。",
    ):
        到过.update(_verdicts(read_input(text, registry, source=source)))
    assert 到过 == set(Verdict)


def test_判定枚举恰好五个():
    """`D-041` §3：五态是封闭集，不许出现第六种。"""
    assert len(Verdict) == 5
    assert {v.name for v in Verdict} == {
        "CONSISTENT",
        "INCONSISTENT",
        "AMBIGUOUS_BASIS",
        "NOT_COVERED",
        "NOT_CHECKABLE",
    }


def test_变动幅度一律核不了并说清为什么(registry, source):
    """拿「同比提升 1.2 个百分点」跟某一年的水平值比，是一个看起来正常的错判定。"""
    rep = read_input(
        "贵州茅台 2023 年净利率 50.6%，同比提升 1.2 个百分点。", registry, source=source
    )
    第二条 = rep.claims[1]
    assert 第二条.verdict is Verdict.NOT_COVERED
    assert "变动幅度" in 第二条.reason


# --------------------------------------------------------------------------
# 5. 判错了不藏（`D-041` §2）
# --------------------------------------------------------------------------


def test_承接上下文时必须印出来(registry, source):
    rep = read_input(
        "贵州茅台 2023 年净利率 50.6%，资产负债率 17.98%。", registry, source=source
    )
    第二条 = rep.claims[1]
    assert 第二条.inherited is not None
    assert "600519" in 第二条.inherited and "2023" in 第二条.inherited
    # 承接了就得进人读页面，不能只躺在结构里。
    assert 第二条.inherited in render_report(rep, registry)


def test_自己写全了主体与期间时不承接(registry, source):
    rep = read_input(
        "贵州茅台 2023 年净利率 50.6%，600519 在 2023 年的资产负债率为 17.98%。",
        registry,
        source=source,
    )
    assert rep.claims[1].inherited is None


def test_报告第一行说清读成了什么(registry, source):
    页 = render_report(
        read_input("贵州茅台 2023 年的资产负债率是多少？", registry, source=source),
        registry,
    )
    assert 页.splitlines()[0] == "我把这段话读成：一个提问"

    页2 = render_report(
        read_input("600519 在 2023 年的资产负债率为 17.98%。", registry, source=source),
        registry,
    )
    assert 页2.splitlines()[0] == "我把这段话读成：待核声明"


def test_核不了被写成正当输出而不是失败(registry, source):
    页 = render_report(
        read_input("000651 在 2023 年的资产负债率为 55%。", registry, source=source),
        registry,
    )
    assert "正当输出" in 页


def test_每条可核声明后面挂的是_render_answer_的逐字输出(registry, source):
    """`D-032`：核查报告不另写一版证据页。"""
    from agent.answer import render_answer

    rep = read_input("600519 在 2023 年的资产负债率为 17.98%。", registry, source=source)
    页 = render_report(rep, registry)
    证据 = render_answer(
        rep.claims[0].answer, registry.definitions.get(rep.claims[0].answer.metric_id)
    )
    assert 证据 in 页


# --------------------------------------------------------------------------
# 6. 计数与序列化
# --------------------------------------------------------------------------


def test_计数五个键恒在(registry, source):
    got = read_input("600519 在 2023 年的资产负债率为 17.98%。", registry, source=source)
    assert set(got.counts()) == {v.name for v in Verdict}
    assert got.counts()["CONSISTENT"] == 1
    assert got.counts()["NOT_CHECKABLE"] == 0


def test_序列化带上判定与它的含义(registry, source):
    d = read_input(
        "600519 在 2023 年的资产负债率为 17.98%。", registry, source=source
    ).to_dict()
    claim = d["claims"][0]
    assert claim["verdict"] == "CONSISTENT"
    assert claim["verdict_meaning"]
    # 用户写的那个数原样带回去 —— 它是被判定的对象，读者要能看见判的是哪个数。
    assert claim["stated_text"] == "17.98%"


# --------------------------------------------------------------------------
# 7. `D-010` 的边界就是签名（不收文件、不落盘、不把用户的数当事实）
# --------------------------------------------------------------------------


def test_核查一整段话时一个字节都不落盘(registry, source, monkeypatch, tmp_path):
    """`D-010` 边界补充：**不落盘**。用真的写入拦截来验，不是抄一遍签名。

    ⚠️ 本条是独立复核（2026-09-11）点名换掉的。原来那一版三条断言全是把
    `read_input` 的签名抄了一遍（`参数[0] == "text"`、`annotation == "str"`），
    **只能因为有人改签名而红，对 `D-010` 一个字都没验** ——
    正是 `rules/failure-modes.md` 里那种「用指针本身证明指针指到的东西存在」。
    第六道门查不出它：`check_gates.py` 只查语法恒真。
    """
    写过: list = []

    真的open = open

    def 记一笔(file, mode="r", *a, **kw):
        if any(w in str(mode) for w in ("w", "a", "x", "+")):
            写过.append(str(file))
        return 真的open(file, mode, *a, **kw)

    monkeypatch.setattr("builtins.open", 记一笔)
    for name in ("write_text", "write_bytes"):
        monkeypatch.setattr(
            Path,
            name,
            lambda self, *a, **kw: 写过.append(str(self)),
        )

    read_input(
        "贵州茅台 2023 年净利率 50.6%，资产负债率 17.98%，盈利能力持续增强。",
        registry,
        source=source,
    )
    assert 写过 == [], 写过


def test_用户文本不进任何缓存键(registry, source):
    """同一段话核两次、中间核一段别的，结果必须逐字相同。

    缓存住用户文本等于开始留存它，而「把存储清空不丢任何东西」是
    `D-021` 豁免三的第二条判据。
    """
    一 = read_input("600519 2023 年资产负债率 17.98%。", registry, source=source)
    read_input("贵州茅台 2023 年净利率 50.6%。", registry, source=source)
    二 = read_input("600519 2023 年资产负债率 17.98%。", registry, source=source)
    assert 一.to_dict() == 二.to_dict()


def test_用户写的数不进取数只进比较(registry, source):
    """同一个问句，带不带那个数，系统算出来的必须是同一个数。"""
    带 = read_input("600519 在 2023 年的资产负债率为 99%。", registry, source=source)
    不带 = read_input("600519 在 2023 年的资产负债率是多少", registry, source=source)
    assert 带.claims[0].answer.value == 不带.answer.value
    # 而判定当然不同 —— 99% 是错的。
    assert 带.claims[0].verdict is Verdict.INCONSISTENT


#: 本模块**允许**出现的全部 import。白名单，不是黑名单。
#: ⚠️ 独立复核（2026-09-11）点名换掉的：原来是一张黑名单
#: （`llm` / `model` / `openai` 三个子串），`import anthropic`、`import httpx`
#: 照样穿得过去，传递导入更不查。**黑名单永远漏，白名单不会。**
_ALLOWED_IMPORTS = frozenset(
    {
        "__future__",
        "re",
        "dataclasses",
        "decimal",
        "enum",
        "semantic_layer.explain",
        ".answer",
        ".intent",
    }
)


def test_模块的import是一张白名单():
    """与 `intent.py` 同一条边界：LLM 由调用方注入，本模块不知道对面是什么。"""
    import ast

    源 = (REPO / "src" / "agent" / "verify.py").read_text(encoding="utf-8")
    名字 = set()
    for node in ast.walk(ast.parse(源)):
        if isinstance(node, ast.Import):
            名字.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            名字.add("." * (node.level or 0) + (node.module or ""))
    多出来的 = 名字 - _ALLOWED_IMPORTS
    assert 多出来的 == set(), (
        "本模块多了这些 import：" + str(sorted(多出来的)) + "。"
        "要加一个，先想清楚它会不会把 LLM 客户端、网络或磁盘带进这一层。"
    )


# --------------------------------------------------------------------------
# 8. 服务端点
# --------------------------------------------------------------------------


def test_verify_端点返回报告与人读页面():
    码, 体 = api.verify_endpoint({"text": "600519 在 2023 年的资产负债率为 17.98%。"})
    assert 码 == 200
    assert 体["report"]["read_as"] == "STATEMENT"
    assert 体["page"].startswith("我把这段话读成：")


def test_verify_端点核不了也是200():
    """`D-003`：核不了是正常业务结果，不是错误。"""
    码, 体 = api.verify_endpoint({"text": "000651 在 2023 年的资产负债率为 55%。"})
    assert 码 == 200
    assert 体["report"]["counts"]["NOT_COVERED"] == 1


@pytest.mark.parametrize(
    "载荷",
    [
        None,
        "不是对象",
        {},
        {"text": ""},
        {"text": "   "},
        {"text": 123},
        {"question": "走错门了"},
    ],
)
def test_verify_端点畸形输入一律400(载荷):
    assert api.verify_endpoint(载荷)[0] == 400


def test_verify_端点超长输入400():
    assert api.verify_endpoint({"text": "长" * 9000})[0] == 400


def test_verify_端点不看多余字段():
    """`D-010`：多给的字段一律不看 —— 不解释、不报错，也不接。"""
    码, 体 = api.verify_endpoint(
        {
            "text": "600519 在 2023 年的资产负债率为 17.98%。",
            "upload": "我的报表.xlsx",
            "rows": [{"total_assets": 1}],
        }
    )
    assert 码 == 200
    assert "upload" not in 体["report"]
    assert "我的报表" not in 体["page"]


def test_answer_端点没有被改动():
    """`D-012`：`frozen-01` / `frozen-02` 的评测臂打的是它，不许换掉它脚下的地面。"""
    码, 体 = api.answer_endpoint({"question": "600519 2023 年的资产负债率"})
    assert 码 == 200
    assert set(体) >= {"answer", "page"}
    assert "report" not in 体


def test_真实数据源确实在(source):
    """上面那些「一致」的读数建在这一份上，它不在就整组测试没有意义。"""
    assert REAL.is_file()
    assert source is not None
    assert "600519" in set(source.entity_names.values())


# --------------------------------------------------------------------------
# 9. 上下文承接：主体与期间写在一句「不可核」的话里时也要捡起来
# --------------------------------------------------------------------------


def test_上下文从不可核的那一句里也要捡起来(registry, source):
    """设计 `frozen-03` 时照出来的缺陷 —— 见 `_context_from_text` 的抬头。

    第一句没有待核数值（判 `NOT_CHECKABLE`、不产生 answer），
    而主体与期间**就写在它里面**。捡不起来，第二句会被说成「核不了」，
    那是**错的**，不是保守。
    """
    rep = read_input(
        "600519 2023 年的营业收入、营业成本都在增长，流动比率 4.62。",
        registry,
        source=source,
    )
    assert [c.verdict for c in rep.claims] == [
        Verdict.NOT_CHECKABLE,
        Verdict.CONSISTENT,
    ]
    assert rep.claims[1].inherited is not None


def test_上下文也能从公司简称里捡起来(registry, source):
    rep = read_input(
        "贵州茅台 2023 年表现不错，流动比率 4.62。", registry, source=source
    )
    assert rep.claims[1].verdict is Verdict.CONSISTENT
    assert "600519" in rep.claims[1].inherited


def test_认出多家公司时不猜主体(registry, source):
    """与 `intent.py` 同一条纪律：分不清就不猜。

    🔴 断言的是**主体那一维没被承接**，不是「整条都没承接」——
    承接是逐维的：期间只有一个（2023），承接它是对的；主体有两家，不许猜。
    """
    rep = read_input(
        "贵州茅台 与 万华化学 2023 年都在增长，流动比率 4.62。",
        registry,
        source=source,
    )
    第二条 = rep.claims[1]
    assert "主体" not in (第二条.inherited or "")
    # 拿不到主体 ⇒ 核不了，而不是挑一家算出个数来。
    assert 第二条.verdict is Verdict.NOT_COVERED
    assert "没有认得出的公司" in 第二条.reason


def test_公司名踩了边界时不猜主体(registry, source):
    """🔴 独立复核（2026-09-11）实测出来的绕过。

    `intent.py` 为「南**华鑫科技**」这类前缀歧义付过代价才立起一道边界，
    而本层原来用一行裸子串匹配从旁边绕了过去 —— 下面那层的回归全是绿的。
    """
    rep = read_input(
        "南华鑫科技 2023 年表现不错，资产负债率 0.55。", registry, source=source
    )
    第二条 = rep.claims[1]
    assert "主体" not in (第二条.inherited or "")
    assert 第二条.verdict is Verdict.NOT_COVERED


def test_公司名右边还连着字时不猜主体(registry, source):
    """同上，右边界那一侧（`N-70`：「…集团有限公司」与「…」常常是两个法人）。"""
    rep = read_input(
        "华鑫科技集团有限公司 2023 年表现不错，资产负债率 0.55。",
        registry,
        source=source,
    )
    assert "主体" not in (rep.claims[1].inherited or "")
    assert rep.claims[1].verdict is Verdict.NOT_COVERED


def test_多个年份时不猜期间(registry, source):
    """挑一个年份的后果最隐蔽：拿另一年的数去否定一条关于这一年的声明。"""
    rep = read_input(
        "600519 2022 年与 2023 年都在增长，流动比率 4.62。", registry, source=source
    )
    第二条 = rep.claims[1]
    assert "期间" not in (第二条.inherited or "")
    assert 第二条.verdict is Verdict.NOT_COVERED
    assert "没有期间" in 第二条.reason


def test_后面的句子自己写了别的公司时主体不被覆盖(registry, source):
    """🔴 独立复核实测：系统曾拿茅台的数去否定一条关于万华化学的声明。

    承接守卫原来只认六位代码，而 `N-65` 之后主体也可以是简称 ⇒
    任何用简称写主体的后续句子都会被前一句覆盖掉。
    """
    rep = read_input(
        "贵州茅台 2023 年毛利率 91.96%，万华化学 2019 年资产负债率 62%。",
        registry,
        source=source,
    )
    第二条 = rep.claims[1]
    assert 第二条.inherited is None
    # 万华化学 2019 的真值是 0.5465，不是茅台的 0.1798。
    assert 第二条.verdict is Verdict.INCONSISTENT
    assert "0.5464" in 第二条.reason


def test_没有年份时期间承接但主体不承接(registry, source):
    rep = read_input("贵州茅台 的表现不错，流动比率 4.62。", registry, source=source)
    第二条 = rep.claims[1]
    # 主体承自前一句（前一句只提了一家，认得准）；期间前一句没写，也就无从承接。
    assert "主体 600519" in (第二条.inherited or "")
    assert 第二条.verdict is Verdict.NOT_COVERED
    assert "没有期间" in 第二条.reason


# --------------------------------------------------------------------------
# 10. 两类「看起来完全正常的错判定」，2026-09-11 实测出来的
# --------------------------------------------------------------------------


def test_一句话里两个数时不挑一个来核(registry, source):
    """🔴 区间断言。真值 4.6239 **落在 4.5~5.0 里面**，用户那句话是对的。

    只取第一个数会拿 4.5 去比，判出一个理直气壮的「不一致」——
    本仓最典型的那种错：读者没有任何线索看得出它错了。
    """
    rep = read_input(
        "600519 2023 年流动比率在 4.5~5.0 之间。", registry, source=source
    )
    assert rep.claims[0].verdict is Verdict.NOT_COVERED
    assert "不止一个数" in rep.claims[0].reason
    # 另一个数要点名，不能只说「有别的数」。
    assert "5.0" in rep.claims[0].reason


def test_并列断言同样不挑(registry, source):
    rep = read_input(
        "600519 2023 年流动比率与速动比率分别是 4.62 和 3.67。",
        registry,
        source=source,
    )
    assert rep.claims[0].verdict is Verdict.NOT_COVERED
    assert "不止一个数" in rep.claims[0].reason


def test_同比下降百分之几是变动不是水平值(registry, source):
    """单位挡不住这一类：写的是 `%`，说的是**差**。"""
    rep = read_input(
        "600519 2023 年资产负债率同比下降 3.5%。", registry, source=source
    )
    assert rep.claims[0].verdict is Verdict.NOT_COVERED
    assert "同比" in rep.claims[0].reason
    assert "变动" in rep.claims[0].reason


def test_变动词落在指标名里面时不算变动(registry, source):
    """🔴 「营业收入同比增长率」里的「同比」「增长」是那个指标自己的名字。

    不做这个例外，一个本来能核的声明会被拒掉。
    """
    rep = read_input(
        "600519 2023 年营业收入同比增长率 18.04%。", registry, source=source
    )
    # 判成什么不重要（那取决于真值），重要的是**它没有因为「同比」被拒**。
    assert rep.claims[0].verdict in (Verdict.CONSISTENT, Verdict.INCONSISTENT)


def test_numbers_in_交出全部而不是第一个():
    from agent.verify import numbers_in

    assert len(numbers_in("流动比率在 4.5~5.0 之间")) == 2
    assert len(numbers_in("600519 2023 年速动比率 3.67")) == 1


# --------------------------------------------------------------------------
# 11. 每请求扇出闸门（独立复核 2026-09-11：8000 字节 → 533 次取数 + 533 次模型调用）
# --------------------------------------------------------------------------


def test_一次请求最多核二十四条(registry, source):
    from agent.verify import MAX_CHECKABLE_CLAIMS

    问过: list = []

    def 记一笔(q):
        问过.append(q)
        return ""

    rep = read_input("某指标 9%，" * 200, registry, source=source, ask_model=记一笔)
    真的核过 = [c for c in rep.claims if c.answer is not None]
    assert len(真的核过) == MAX_CHECKABLE_CLAIMS
    # 模型调用次数跟着一起被摁住 —— 那才是会把服务卡住的那一半。
    assert len(问过) <= MAX_CHECKABLE_CLAIMS


def test_被闸门拦下的条目说清楚是被拦的(registry, source):
    rep = read_input("某指标 9%，" * 200, registry, source=source)
    被拦 = [c for c in rep.claims if c.answer is None and c.stated is not None]
    assert 被拦, "应该有被闸门拦下的条目"
    assert all(c.verdict is Verdict.NOT_COVERED for c in 被拦)
    # 不静默截断：读者要知道后面的**没有核**，而不是以为都核过了。
    assert "后面的没有核" in 被拦[0].reason


# --------------------------------------------------------------------------
# 12. 期间口径 / 金额被当成代码 / 模型归一
# --------------------------------------------------------------------------


def test_比年度更细的期间一律不核(registry, source):
    """20 份定义全是年度口径，拿全年的数核季度声明是又一个静默错判。"""
    rep = read_input(
        "600519 2023 年前三季度速动比率 3.67。", registry, source=source
    )
    assert rep.claims[0].verdict is Verdict.NOT_COVERED
    assert "比年度更细" in rep.claims[0].reason


def test_六位数金额不被当成股票代码(registry, source):
    """「自由现金流 639735 万元」曾让整段被降级成「一个提问」。"""
    rep = read_input(
        "贵州茅台 2023 年自由现金流 639735 万元。", registry, source=source
    )
    # 首先：它是一条待核声明，不是一个提问。
    assert rep.read_as is ReadAs.STATEMENT
    assert rep.claims[0].stated.text.startswith("639735")
    # 其次：下游仍会把它认成代码，而报告要**说清楚**（`D-041` §2 判错了不藏）。
    assert "是你写的**金额**" in rep.claims[0].reason


def test_模型归一过就一律算口径未声明(registry, source):
    """🔴 不这样的话，判定由一个非确定性组件决定，而用户一个字都没改。"""
    一 = read_input(
        "600519 2023 年净利润率 50.6%。",
        registry,
        source=source,
        ask_model=lambda q: "归母净利率",
    )
    二 = read_input(
        "600519 2023 年净利润率 50.6%。",
        registry,
        source=source,
        ask_model=lambda q: "净利率",
    )
    assert 一.claims[0].verdict is Verdict.AMBIGUOUS_BASIS
    assert 二.claims[0].verdict is Verdict.AMBIGUOUS_BASIS
    assert "是**模型**把它归到了" in 一.claims[0].reason
