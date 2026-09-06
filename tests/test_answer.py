"""`src/agent/answer.py` 的回归（`02-01` T3）。

两件产物：结构化答案对象（`AC-05` 数它）与人读渲染（`AC-06` 的复核者读它）。
本文件盯的是**两者各自的硬约束**，以及 `D-032` 那条「口径一节逐字一致」。
"""

from __future__ import annotations

import pathlib
from pathlib import Path

import pytest
import yaml

from agent.answer import (
    REQUIRED_ANSWER_EVIDENCE,
    _formula_field_refs,
    _walk_tree,
    Answer,
    FixtureSource,
    answer_question,
    evidence_gaps,
    evidence_stage,
    render_answer,
    required_answer_evidence,
)
from semantic_layer.explain import APPENDIX_TITLE, render_explanation
from semantic_layer.resolve import Registry

REPO = Path(__file__).resolve().parent.parent
FIXTURE = REPO / "eval" / "frozen-01" / "fixtures" / "synthetic-01.yaml"
CASES = REPO / "eval" / "frozen-01" / "cases"


@pytest.fixture
def registry():
    return Registry.load(REPO / "metrics")


@pytest.fixture
def source():
    return FixtureSource(FIXTURE)


def _stage(a: Answer) -> str:
    return evidence_stage(a)


# ── 结构化答案对象 ──────────────────────────────────────────────────


def test_frozen01_每条答案的证据链齐全率是百分之百(registry, source):
    """`AC-05` 是**保证类**：不齐全即失败，不许用「这道题特殊」解释。

    ⚠️ 齐全的口径是**字段有真值**，不是键存在（2026-08-22 写死）。
    它会红的场景：有人给某条路径少填一个键，或用 `"unknown"` 之类占位值糊上。
    """
    seen = 0
    for path in sorted(CASES.glob("*.yaml")):
        case = yaml.safe_load(path.read_text(encoding="utf-8"))
        a = answer_question(" ".join(str(case["question"]).split()), registry, source=source)
        gaps = evidence_gaps(a.evidence, required_answer_evidence(_stage(a)))
        assert gaps == [], f"{case['id']} 的证据链有缺口：{gaps}"
        seen += 1
    assert seen == 20


def test_拒答与作答是同一套字段(registry, source):
    ok = answer_question("华鑫科技（900001）2023 年的毛利率是多少？", registry, source=source)
    bad = answer_question("华鑫科技（900001）2023 年的 EBITDA 是多少？", registry, source=source)
    assert not ok.refused and bad.refused
    # ⚠️ `set(ok.to_dict()) == set(bad.to_dict())` 是**恒真**的：
    # `to_dict()` 返回字面量字典，键集由 dataclass 写死。
    # 2026-09-04 独立复核指出它是本测试里唯一的实质断言 ⇒ 换成会红的那种。
    assert set(ok.to_dict()) == set(bad.to_dict())
    for rec in (ok, bad):
        d = rec.to_dict()
        # ⚠️ `metric_id` / `metric_version` **不在**这张表里：题面里根本没有可认的指标时
        # 它们为空是**事实**，不是缺字段。把它们要求成非空，等于逼实现去编一个。
        for key in ("question", "question_sha256", "gate"):
            assert d[key] not in (None, "", [], {}), f"{key} 在 {'拒答' if rec.refused else '作答'} 路径上是空的"
        assert set(d["evidence"]) == set(REQUIRED_ANSWER_EVIDENCE)
        # 出处与执行指纹两条**两条路径上都必须有真值**
        assert d["evidence"]["data_source"]
        assert d["evidence"]["execution_hash"]


def test_拒答也带执行指纹(registry, source):
    """拒答是**正常业务结果**不是降级（`D-003`），因此同样要可复现。

    frozen-01 的 C2 题面自己也要求 `execution_hash`。
    """
    a = answer_question("华鑫科技（900001）2023 年的 EBITDA 是多少？", registry, source=source)
    assert a.refused
    h = a.evidence["execution_hash"]
    assert isinstance(h, str) and len(h) == 64
    again = answer_question("华鑫科技（900001）2023 年的 EBITDA 是多少？", registry, source=source)
    assert again.evidence["execution_hash"] == h, "同样的输入必须给出同样的指纹"


def test_没解析出指标那一步不该有口径版本(registry, source):
    """分阶段必填键**不是豁免**：那个键换成了另一个方向的检查。

    它会红的场景：有人在意图失败的路径上从别处抄一个版本号填进去。
    """
    a = answer_question("这句话里没有任何指标名", registry, source=source)
    assert a.metric_id is None
    assert a.evidence["metric_definition_version"] is None
    keys = required_answer_evidence("no_metric")
    assert "metric_definition_version" not in keys
    伪造 = dict(a.evidence, metric_definition_version=2)
    assert evidence_gaps(伪造, keys) != [], "填了不该有的版本却没报缺口"


def test_齐全的口径逐字沿用不另抄一份占位词表():
    """`AC-05` 的反面实证：八键齐全率 100%，其中三个是假的。

    占位词表必须是 `extractor.pipeline` 里**那一个对象**，不是一份拷贝 ——
    拷贝会漂移，而漂移之后两处对「齐全」的判断就不一样了。
    """
    from extractor import pipeline
    import agent.answer as ans

    assert ans.PLACEHOLDER_TEXTS is pipeline.PLACEHOLDER_TEXTS

    base = {k: "x" for k in REQUIRED_ANSWER_EVIDENCE}
    assert evidence_gaps(base) == []
    for 坏值 in ("", "   ", "unknown", "N/A", "待定", None):
        bad = dict(base, data_source=坏值)
        assert evidence_gaps(bad), f"{坏值!r} 应当被判为缺口"
    assert evidence_gaps(dict(base, data_source=0)), "恒零应当被判为缺口"


# ── 人读渲染 ────────────────────────────────────────────────────────


def test_口径一节与explain的正文逐字一致(registry, source):
    """🔴 `D-032` 的落地判据。**不是「渲染里出现了指标名」**。

    它会红的场景：有人在答案里另写一份口径讲法 —— 那正是 `D-032` 禁的事。
    """
    a = answer_question("华鑫科技（900001）2023 年的毛利率是多少？", registry, source=source)
    defn = registry.definitions[a.metric_id]
    fd = {"restated": "比较期数值经追溯重述"}
    out = render_answer(a, defn, fd)
    嵌入 = render_explanation(defn, fd, with_appendix=False)
    assert 嵌入 in out


def test_整份答案只有一个附录且在最末尾(registry, source):
    """`D-032` 收紧条：附录只有一个、在最末尾。

    嵌一段自带附录的东西进正文，等于把附录塞回中间 ——
    那正是 2026-09-04 操作者指出的毛病。
    """
    a = answer_question("华鑫科技（900001）2023 年的毛利率是多少？", registry, source=source)
    out = render_answer(a, registry.definitions[a.metric_id])
    assert out.count(APPENDIX_TITLE) == 1
    body, _, appendix = out.partition(APPENDIX_TITLE)
    assert "is.operating_revenue_current" not in body, "正文里漏出了字段标识符"
    assert a.evidence["execution_hash"] not in body, "哈希属于附录，不属于正文"
    assert a.evidence["execution_hash"] in appendix


def test_拒答的渲染同样给得出理由与出处(registry, source):
    a = answer_question("华鑫科技（900001）2023 年的 EBITDA 是多少？", registry, source=source)
    out = render_answer(a, None)
    assert "为什么不给答案" in out
    assert "这个数是从哪儿来的" in out
    assert a.evidence["execution_hash"] in out


def test_合成夹具必须在渲染里被说成合成的(registry, source):
    """把合成数据说成真实数据，比数据本身更严重（`D-010` / `D-013`）。"""
    a = answer_question("华鑫科技（900001）2023 年的毛利率是多少？", registry, source=source)
    out = render_answer(a, registry.definitions[a.metric_id])
    assert "合成夹具" in out
    assert "不是任何真实公司的年报" in out


# --------------------------------------------------------------------------
# 独立复核（2026-09-04）发现的三处，逐条锁住
# --------------------------------------------------------------------------


def _mutated(registry, metric_id, **attrs):
    """复制一份定义并改几个字段，塞回一个浅拷贝的注册表。**不动 metrics/**。"""
    import copy

    defn = copy.deepcopy(registry.definitions[metric_id])
    for k, v in attrs.items():
        setattr(defn, k, v)
    reg = copy.copy(registry)
    reg.definitions = dict(registry.definitions)
    reg.definitions[metric_id] = defn
    return reg, defn


def test_不合规的定义不得被答案路径消费(registry, source):
    """🔴 R1：闸门的拒答文案写着「口径定义本身不合规，不允许被消费」。

    2026-09-04 实测它做不到：`answer_question` 走
    `registry.definitions.get()` 直接取定义，**从不调用 `Registry.resolve()`** ——
    而后者才是跑 `validate_definition`（9 条 Requirement）那一步。
    闸门的「定义合规」只看 `defn.parse_error`，那是 **YAML 解析层**的错。

    实测：`common_pitfalls` 清空 ⇒ `R8.TOO_FEW_PITFALLS` ⇒
    `Registry.resolve` 判 `DEFINITION_NONCONFORMANT`，而 `answer_question` 算出 0.3。

    ⚠️ 今天不可利用（`metrics/` 里没有不合规定义，且 validate 是常跑门禁），
    但那是**仓库级 CI**，不是**运行时 fail-closed** —— 而 `pre_execute`
    存在的全部理由就是后者。`02-04` 的 Web 壳一旦接受仓库外的定义就会命中。

    它会红的场景：有人把 `registry.resolve` 换回 `definitions.get`。
    """
    from semantic_layer.resolve import RefusalCode

    reg, _ = _mutated(registry, "gross_profit_margin", common_pitfalls=[])
    a = answer_question("华鑫科技（900001）2023 年的毛利率是多少？", reg, source=source)
    assert a.refused, "不合规的定义被消费了，算出了一个数"
    assert a.refusal["code"] == RefusalCode.DEFINITION_NONCONFORMANT.name


def test_可比性标记的trigger也要过闸门(registry, source, monkeypatch):
    """🔴 R2：`SC-6` 的实际反例。

    `answer_question` 此前只把 `undefined_conditions` 的树与公式字段送进闸门，
    而 `active_flags()` 会 `dsl.evaluate` 每一条 flag trigger —— **那些树从未过闸**。

    ⚠️ **这条测试直接验「闸门收到了哪些树」，不走端到端。** 原因是
    校验器的 `R4.TRIGGER_UNDECLARED_FIELD` 已经在**定义层面**禁止 trigger 引用
    未声明字段 ⇒ 端到端造不出一个「通过校验但 trigger 越界」的样本，
    端到端断言会被 `DEFINITION_NONCONFORMANT` 满足，**而那不是这条要证的事**。
    （闸门仍要覆盖它：仓库级校验不是运行时 fail-closed —— 与 R1 同一条理由。）

    它会红的场景：有人从 `trees` 里去掉 flag trigger 那一段。
    """
    import agent.answer as mod
    from semantic_layer import dsl

    seen = []
    real = mod.pre_execute

    def 记账(req, *a, **kw):
        seen.extend(req.trees)
        return real(req, *a, **kw)

    monkeypatch.setattr(mod, "pre_execute", 记账)
    a = answer_question("华鑫科技（900001）2023 年的毛利率是多少？", registry, source=source)
    assert not a.refused

    defn = registry.definitions["gross_profit_margin"]
    triggers = [f.trigger for f in defn.flags if f.trigger]
    assert triggers, "这份定义应当有带 trigger 的标记，否则本测试在空转"
    过闸的 = {dsl.parse_condition(t).tree for t in triggers}
    assert 过闸的 <= set(seen), "有 flag trigger 没过闸门"


def test_送进execute的那个请求装着这次会求值的全部树(registry, source, monkeypatch):
    """🔴 2026-09-05 独立复核：`execute()` 校的树 ≠ `run` 求的树。

    此前 `answer_question` 逐棵送闸门，然后另建一个只装 `trees[0]`
    （第一条拒答条件）的请求送进 `execute()`，而 `run` 求的是**公式**那棵树。
    公式字段当时确实在别处过了闸，所以算不出错数 —— 但
    「`execute()` 无条件先过闸门」守的不是被执行的那个东西，
    `ExecutionRecord.referenced_fields` 记的也是另一棵树的字段。
    **门声称守住的和它实际守住的不是同一件事**（`N-42` 的同一个形状）。

    它会红的场景：有人又给 `execute()` 单独造一个请求。
    """
    import agent.answer as mod
    from extractor.formula import field_refs, parse_formula

    got = {}
    real = mod.execute

    def 记账(req, run):
        got["req"] = req
        return real(req, run)

    monkeypatch.setattr(mod, "execute", 记账)
    a = answer_question("华鑫科技（900001）2023 年的毛利率是多少？", registry, source=source)
    assert not a.refused

    defn = registry.definitions["gross_profit_margin"]
    公式字段 = set(field_refs(parse_formula(str(defn.formula))))
    assert 公式字段, "这份定义的公式没有字段引用，本测试在空转"

    from agent.gate import _field_refs

    过闸的字段 = set(_field_refs(got["req"].trees))
    assert 公式字段 <= 过闸的字段, (
        "送进 execute 的请求里没有公式那几个字段：" + str(sorted(公式字段 - 过闸的字段))
    )


def test_留痕里的字段是这次执行真的碰过的那些(registry, source):
    """`ExecutionRecord.referenced_fields` 是证据链的一部分（`D-003`），
    少记等于出处不全。这条直接从 `gate` 层验并集，不绕 `answer`。
    """
    from agent.gate import GateRequest, execute as gate_execute
    from semantic_layer import dsl

    defn = registry.definitions["current_ratio"]
    t1 = dsl.parse_condition("bs.total_current_liabilities_period_end > 0").tree
    t2 = dsl.FieldRef("bs.total_current_assets")
    rec = gate_execute(
        GateRequest(
            defn=defn, expected_version=None, trees=(t1, t2),
            entity="900001", period=2023, question_sha256="0" * 64,
        ),
        run=lambda _r: 1,
    )
    assert rec.gate == "passed"
    assert set(rec.referenced_fields) == {
        "bs.total_current_liabilities_period_end",
        "bs.total_current_assets",
    }


def test_调用方声明的口径版本对不上就拒答(registry, source):
    """🟡 2026-09-05 独立复核：「口径版本匹配」这道门在生产路径上永远不可能红 ——
    两个调用点都传 `expected_version=defn.version`，拿它自己跟它自己比。

    现在它是**调用方的声明**：不声明就不比对，声明了就必须对得上。
    这条测的是那条声明入口（`L-32`：一道你说不出它什么时候会红的门，
    要么删掉要么给它一条真实回归）。
    """
    q = "华鑫科技（900001）2023 年的毛利率是多少？"
    没声明 = answer_question(q, registry, source=source)
    assert not 没声明.refused, "不声明版本时不该比对"

    声明错的 = answer_question(q, registry, source=source, expected_version="不存在的版本")
    assert 声明错的.refused
    assert 声明错的.refusal["code"] == "CROSS_VERSION_COMPARISON"

    defn = registry.definitions["gross_profit_margin"]
    声明对的 = answer_question(q, registry, source=source, expected_version=defn.version)
    assert not 声明对的.refused


def test_数据源缺数据时不该被判成证据链缺口(registry, source):
    """🔴 R3：`AC-05` 是**保证类**（齐全率 <100% 即失败）。

    `gate="not_reached"` 此前被同时用于两件事：「指标没解析出来」与
    「指标解析出来了但数据源没这一行」。而分阶段必填键的收窄只对第一件成立 ——
    第二件里 `metric_definition_version` 是**合法已知**的，
    反方向检查却报「这一步不该有版本，却填了值」。

    ⇒ 一个完全正确的 `UNAVAILABLE` 拒答会让 `AC-05` 这条保证门红，
    正是 `required_answer_evidence` 的 docstring 自称在避免的那件事。

    它会红的场景：有人把收窄判据改回按 `gate` 取。
    """
    a = answer_question("华鑫科技（900001）1999 年的毛利率是多少？", registry, source=source)
    assert a.refused and a.refusal["code"] == "UNAVAILABLE"
    assert a.metric_id == "gross_profit_margin"
    assert a.evidence["metric_definition_version"] is not None
    assert evidence_gaps(a.evidence, required_answer_evidence(evidence_stage(a))) == []


def test_近似命中在多候选时取最长的那个(registry):
    """🔵→🟡 `_near_miss` 里写的是 `len(cand[0]) > len(best[0])`。

    `cand` 是 str，`cand[0]` 是**首字符**，两边 `len` 恒为 1 ⇒ 比较恒假 ⇒
    取的是**第一个**候选而不是最长的，结果取决于 `metrics/` 的加载顺序。

    当前别名表里 4 组碰撞每组只有一个候选，所以无可观察差异 ——
    **这条测试直接测那个取最长的判据**，不依赖别名表恰好有多候选。
    """
    from agent.intent import _near_miss

    class 假注册表:
        by_alias = {
            "收益率": "m_short",
            "净资产收益率": "m_mid",
            "加权平均净资产收益率": "m_long",
        }

    # 题面里「收益率」前面同时接得上 `净资产` 与 `加权平均净资产`，两个候选都成立
    got = _near_miss(假注册表(), "公司的加权平均净资产收益率是多少", "收益率", len("公司的加权平均净资产"))
    assert got is not None
    asked, have = got
    assert asked == "加权平均净资产收益率", f"没取最长的那个，取到的是 {asked!r}"
    assert have == "加权平均净资产收益率"


def test_必填证据键取自题面而不是本模块自己的那张表():
    """🟡 2026-09-05 独立复核：证据链那几条测试的基准全都来自
    `REQUIRED_ANSWER_EVIDENCE` 本身 —— 用一张表去证它自己，是自证。

    `REQUIRED_ANSWER_EVIDENCE` 的 docstring 明写它「**取自 frozen-01 题面自己
    声明的 `required_evidence`**，不是本模块发明的」。这条把那句话变成可失败的断言。

    它会红的场景：有人往题面加了第四个必填键而这张表没跟上
    （那个键于是永远不会被检查）；或有人往这张表塞了一个题面没要求的键。
    """
    declared = set()
    seen = 0
    for path in sorted(CASES.glob("*.yaml")):
        case = yaml.safe_load(path.read_text(encoding="utf-8"))
        keys = case.get("required_evidence") or []
        if keys:
            seen += 1
            declared |= set(keys)
    assert seen >= 15, f"只有 {seen} 道题声明了 required_evidence，这条断言在空转"
    assert declared == set(REQUIRED_ANSWER_EVIDENCE), (
        "题面要求的键集与本模块那张表对不上："
        f"题面多出 {sorted(declared - set(REQUIRED_ANSWER_EVIDENCE))}，"
        f"表里多出 {sorted(set(REQUIRED_ANSWER_EVIDENCE) - declared)}"
    )


def test_换一行取数时夹具文件不会被重新读一遍(source, monkeypatch):
    """🔵 `FixtureSource.at()` 的注释写着「**文件只读一次** —— 出处哈希也就只算一次」。

    2026-09-05 独立复核：那句话当时是假的 —— `at()` 新建一个 `FixtureSource`，
    构造函数里又 `read_bytes()` 了一遍。两次读之间文件若被改动，
    `batch_id` 里的哈希会**静默换成另一个值**，而证据链正是靠它指认出处。
    """
    reads = []
    real = pathlib.Path.read_bytes

    def 记账(self):
        reads.append(self)
        return real(self)

    monkeypatch.setattr(pathlib.Path, "read_bytes", 记账)
    before = len(reads)
    row = source.at("900001", 2023)
    assert row.found
    assert len(reads) == before, f"at() 又读了 {len(reads) - before} 次文件"
    assert row.sha256 == source.sha256


# ── `D-038`：H2 第一轮量出来的三个证据缺口 ──────────────────────────────


def test_G1_算出来的数必须给出它的输入(registry, source):
    """🔴 H2 第一轮**全部 5 道计算题**判「无法判断」，理由逐字是：

    「有定义、有公式、有最终数字，但没有实际参与计算的原始字段值……
      执行哈希能标识一次执行，不能代替计算输入。」

    而那份数据**当时就在代码里** —— `answer_question` 把 `inputs` 喂进了
    `execution_hash`，从未渲染。**「算进哈希」与「给人看」是两件事。**

    它会红的场景：有人把这一节从 `render_answer` 拿掉，或不再填 `Answer.inputs`。
    """
    a = answer_question("华鑫科技（900001）2023 年的期间费用率是多少？", registry, source=source)
    assert not a.refused
    defn = registry.definitions["period_expense_ratio"]

    公式字段 = set(_formula_field_refs(defn))
    assert 公式字段, "这份定义的公式没有字段引用，本测试在空转"
    assert set(a.inputs) == 公式字段, "输入集合与公式引用的字段对不上"

    page = render_answer(a, defn, None)
    assert "这个数是拿哪几个数算出来的" in page
    # ⚠️ 夹具对象本身是**未定位**的（`source.row` 是空的）——
    #    `answer_question` 内部走 `source.at(主体, 期间)` 才拿到那一行。
    #    直接读 `source.row` 会得到一片 `None`，那是在验一个不存在的东西。
    row = source.at("900001", 2023).row
    for path in 公式字段:
        raw = row.get(path)
        assert raw is not None, f"夹具里没有 {path}，本条在空转"
        assert str(raw) in page, f"{path} 的取值 {raw} 没出现在页面上"


def test_G1_复核者能拿页面上的数重算一遍(registry, source):
    """判据不是「有没有这一节」，是「拿它能不能把答案重算出来」。

    期间费用率 =（销售 + 管理 + 财务）/ 营业收入。这条把它当场算一遍。
    """
    from decimal import Decimal

    a = answer_question("华鑫科技（900001）2023 年的期间费用率是多少？", registry, source=source)
    vals = {k: Decimal(str(v)) for k, v in a.inputs.items() if str(v).replace(".", "").isdigit()}
    assert len(vals) == 4, f"四个输入没都拿到数：{a.inputs}"
    分子 = sum(v for k, v in vals.items() if "revenue" not in k)
    分母 = next(v for k, v in vals.items() if "revenue" in k)
    assert 分子 / 分母 == a.value, "页面上给的输入算不出页面上给的答案"


def test_G2_拒答条件成立时给出那一条引用的字段取值(registry, source):
    """🔴 H2-06 / H2-12：「只知道系统触发了拒答条件，不能确认它触发得对」。

    它会红的场景：有人不再填 `inputs`，或改成拿 `detail` 的措辞去反查是哪一条
    （`condition_index` 才是判据 —— 措辞会变，序号不会）。
    """
    a = answer_question("新元（900004）2023 年的营业收入同比增长率是多少？", registry, source=source)
    assert a.refused
    assert a.refusal["code"] == "UNDEFINED_CONDITION_HIT"
    assert a.inputs, "触发了拒答条件，却没给出那一条引用的字段取值"

    defn = registry.definitions[a.metric_id]
    idx = a.refusal.get("condition_index")
    assert idx is not None, "拒答没记是第几条 —— 那就无从知道该摆哪些字段"
    from semantic_layer import dsl

    expr = defn.undefined_conditions[idx].expr
    引用的 = {n.path for n in _walk_tree(dsl.parse_condition(expr).tree)
              if isinstance(n, dsl.FieldRef)}
    assert set(a.inputs) == 引用的, "摆出来的字段不是触发那一条引用的那些"

    page = render_answer(a, defn, None)
    assert "凭什么说满足了这一条" in page


def test_G2_缺失与零必须在页面上分得开():
    """「行不存在」「格子是空的」「就是 0」在这里会被读成同一件事，
    而它们在财务上完全不同 —— `A-2` 当年就是栽在这个区分上。
    """
    from agent.answer import _shown

    assert _shown(None) != _shown(0)
    assert "缺失" in _shown(None)
    assert _shown(0) == "0"
    assert _shown("") == "（空值）"
    assert _shown(False) == "否" and _shown(True) == "是"


def test_G3_说没有这个指标时必须给出当时的指标清单(registry, source):
    """🔴 H2 第一轮 **6 道**题判「无法判断」：

    「系统称某指标没定义，但页面没给当时语义层的指标·别名清单或可验证快照，
      因此无法独立证明 `METRIC_NOT_DEFINED` 是正确判定。」
    """
    a = answer_question("新元（900004）2023 年的净资产收益率是多少？", registry, source=source)
    assert a.refused and a.refusal["code"] == "METRIC_NOT_DEFINED"
    snap = a.registry_snapshot
    assert snap, "说了「没有这个指标」，却拿不出当时的清单"
    assert snap["metric_count"] == len(registry.definitions)
    assert set(snap["names"]) == {str(x) for x in registry.by_alias}

    page = render_answer(a, None, None)
    assert "我们当时有哪些指标" in page
    # 题面问的那个词**确实不在表里**，而它的近邻在 —— 两件事都要能在页面上核到
    assert "净资产收益率" not in snap["names"]
    assert "加权平均净资产收益率" in snap["names"]
    assert "加权平均净资产收益率" in page


def test_G3_快照的指纹跟着名字表走(registry):
    """指纹证明的是「这一页列出的就是当时那份表」。它跟着表变，否则就是个装饰。"""
    from agent.answer import registry_snapshot

    a = registry_snapshot(registry)
    b = registry_snapshot(registry)
    assert a["sha256"] == b["sha256"], "同一份注册表两次快照指纹不同"

    class 假注册表:
        definitions = dict(registry.definitions)
        by_alias = dict(registry.by_alias, 新加的一个别名="gross_profit_margin")

    assert registry_snapshot(假注册表())["sha256"] != a["sha256"], "表变了指纹没变"


def test_G3_题面缺主体时不摆指标清单(registry, source):
    """**证据要相关，不是要多。**

    `INTENT_INCOMPLETE`（缺主体 / 缺期间）与「有哪些指标」无关，
    摆 94 行清单只会让复核者在 5 分钟里翻一页跟结论无关的东西。
    `AC-05` 的已知盲区正是「抓不到证据不相关」—— 这条替它守一小块。
    """
    a = answer_question("华鑫科技 2023 年的毛利率是多少？", registry, source=source)
    assert a.refused and a.refusal["code"] == "INTENT_INCOMPLETE"
    assert a.registry_snapshot is None
    assert "我们当时有哪些指标" not in render_answer(a, None, None)


def test_没有输入时不留一个空标题(registry, source):
    """空标题比没有标题更糟：读者以为这里本该有东西，然后去找为什么没有。"""
    a = answer_question("新元（900004）2023 年的净资产收益率是多少？", registry, source=source)
    assert a.inputs == {}
    page = render_answer(a, None, None)
    assert "这个数是拿哪几个数算出来的" not in page
    assert "凭什么说满足了这一条" not in page
