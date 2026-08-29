"""证据标识的字面存在性（`J-6`）与取数口径三元组的齐全性（`J-7` / `L-2` / `AC-05`）。

三件事各有一条会红的测试：**证据标识是不是系统自己编出来的**、
**取数口径三元组齐不齐**、**字段齐全率是不是被空值刷出来的**。

## 为什么 `J-6` 值得单独一条

`EVAL_CASES.md` §3.3 明写它是**唯一一条不需要 LLM 判分就能跑的证据链检查**，
与 `J-1` 天然互补：`J-1` 限制什么时候能用 LLM 判分，本条给出一个根本不需要 LLM 的判据。
依据是 hello-agents `ch9:1526` 的示例答案引用了一个**从未进入上下文的笔记 id**
（`references/hello-agents-ch09-context.md` 的 `C9-B10` 条）。
`J-6` 的原话还有一句必须照办：**不得因为最终数字正确而放过** ——
数字是被证明的东西，拿它去背书证据，顺序是反的。

## 明确不新增门禁

`J-6` 落成一条 pytest，**不落成第八道门**。`scripts/check_gates.py` 的 R2 / R4 / R5
对每道登记门禁都有连带要求（具名负控制 + 进 `gates.yml` + 同步 `rules/commands.md`），
为一条能用测试表达的检查再加一道门是净增流程开销，触及 `D-009` 的 30% 红线。
**这不是漏做**，写在这里免得下一轮当成欠账捡起来。
（`01.5-06-PLAN.md` 的「明确不新增门禁」一节是这条判断的出处。原文写「第七道门」，
是因为它写于第七道门 `tests/test_plan_waves.py` 落地之前；判断本身不变。）

## 本文件**抓不到**什么

⚠️ 三条，一条都不许被读成「这个测试绿了 = 证据链是对的」：

1. **抓不到「证据不相关」。** 这是 `AC-05` 写在 `PROJECT_SPEC.md` §9 里的**已知盲区**：
   它只覆盖「证据**缺失**」。实证是 hello-agents 的 `arun_stream` 每步调两次 LLM，
   屏幕上读到的推理来自第一次采样、实际执行的 `tool_calls` 来自第二次，
   `temperature > 0` 时两者**无因果关系**（`react_agent.py:946-988`，
   代码注释自承「简化处理」）—— 而字段齐全率仍是 100%。
   同源性由 `AC-06` 的人工复核承担，**目前无自动判据**。
2. **抓不到「标识对得上、但指的不是那一处」。** 本文件查的是 `field_id` 有没有
   逐字出现在映射文件里、页码是不是整数 —— **不查那一页上真的印着这个数**。
   那是 `locate` 的事，且最终要靠 `SC-8` 的人工逐字段验收。
3. **抓不到「映射条目本身写错了」。** `field_id` 在映射文件里找得到，
   只证明这个标识不是系统编的，不证明那条映射规则指向的是对的那一行。
   `C-14` 已经实证过一个更强的版本：数值一致都不能用来验证映射正确。
"""

from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path

import pytest

from extractor.mapping import load_pdf_mapping
from extractor.pipeline import (
    REQUIRED_EVIDENCE_KEYS,
    ExtractionSource,
    StatementView,
    completeness_report,
    evidence_completeness,
    extract_records,
)
from extractor.record import (
    EVIDENCE_IDENTIFIER_FIELDS,
    ExtractionRecord,
    ExtractionStatus,
    SourceFreshness,
    evidence_identifiers,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = Path(__file__).parent / "fixtures" / "maotai_2023_bs_rows.json"
REAL_MAPPING_DIR = REPO_ROOT / "data" / "mappings" / "pdf"

#: 映射表里没有的 `field_id`。**故意取一个人一眼看得出是编的串** ——
#: 负向用例要证明的正是「系统编出来的标识会被抓住」。
FABRICATED_FIELD_ID = "bs.这个字段不在任何映射文件里"


@pytest.fixture(scope="module")
def raw() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def batch(raw: dict):
    """从固件重跑一次**真实抽取**。字段与页码都是从版面里取出来的，不是手填的。"""
    view = StatementView.from_dict(raw)
    source = ExtractionSource(
        stock_code=raw["source"]["stock_code"],
        fiscal_year=raw["source"]["fiscal_year"],
        pdf_sha256=raw["source"]["pdf_sha256"],
        source_url="https://static.cninfo.com.cn/finalpage/2024-04-03/1219506510.PDF",
        freshness=SourceFreshness.REUSED_CACHED,
    )
    return extract_records(view, load_pdf_mapping("bs", REAL_MAPPING_DIR), source)


@pytest.fixture(scope="module")
def payloads(batch) -> list[dict]:
    """序列化后的证据链 —— **复核者手上拿到的就是这一份**。"""
    return [record.to_dict() for record in batch.records]


# --------------------------------------------------------------------------
# J-6：证据标识的字面存在性
# --------------------------------------------------------------------------


def _mapping_texts() -> dict[str, str]:
    """各命名空间映射文件的**原始文本**。比对逐字做，不解析成对象。

    解析成对象再比，比的是「我们的加载器认不认得它」；逐字比文本，
    比的才是 `J-6` 要的那件事：**这个串在人能读到的那份文件里有没有出现过**。
    """
    return {
        path.stem: path.read_text(encoding="utf-8")
        for path in sorted(REAL_MAPPING_DIR.glob("*.yaml"))
    }


def _undeclared_field_ids(payloads, mapping_texts) -> list[tuple[str, str]]:
    """返回 `(field_id, 原因)`，逐字对不上的都在里面。**本函数不抛异常。**

    判定与断言分开：抛异常的话，正向用例的唯一可失败点就藏进了 helper，
    `check_gates.py` 的 R1 抓不到（它明写「抓不到间接断言」），
    而那条规则不放宽正是为了不让 R1 退化。
    """
    findings: list[tuple[str, str]] = []
    for payload in payloads:
        field_id = payload.get("field_id")
        if not isinstance(field_id, str) or not field_id.strip():
            findings.append((repr(field_id), "field_id 缺失或不是非空字符串"))
            continue
        namespace = field_id.split(".", 1)[0]
        text = mapping_texts.get(namespace)
        if text is None:
            findings.append((field_id, f"命名空间 {namespace!r} 没有对应的映射文件"))
        elif field_id not in text:
            findings.append((field_id, f"在 {namespace}.yaml 里逐字找不到"))
    return findings


def _render(findings) -> str:
    return "J-6 字面存在性失败：" + "；".join(f"{fid} —— {why}" for fid, why in findings)


def test_每个_field_id_都逐字出现在对应映射文件里(payloads):
    """`J-6` 的正向：真实批次里的 15 个 `field_id` 全部对得上。"""
    findings = _undeclared_field_ids(payloads, _mapping_texts())
    assert findings == [], _render(findings)
    # 判据得跑在有东西的批次上 —— 空列表也能让上一行绿。
    assert len(payloads) >= 15


def test_编造的_field_id_会被抓住且失败信息里含那个串(payloads):
    """`J-6` 的负向：这才是它存在的理由。

    实证形态是 hello-agents `ch9:1526` —— 示例答案引用了一个**从未进入上下文的
    笔记 id**。把它搬到本项目：回答里出现一个映射表里根本没有的 `field_id`。
    """
    tampered = [dict(p) for p in payloads]
    tampered[0]["field_id"] = FABRICATED_FIELD_ID

    findings = _undeclared_field_ids(tampered, _mapping_texts())

    assert [fid for fid, _ in findings] == [FABRICATED_FIELD_ID]
    # 「抓住了」还不够，得**指出是哪一条** —— 只报个数就是 RV-3 那个形状。
    assert FABRICATED_FIELD_ID in _render(findings)


def test_两个页码是整数而_batch_id_全批一致(payloads):
    """`D-019` 的两个整数页码 + `D-024` 的批次身份，都是回答会直接引用的标识。"""
    batch_ids = {p["batch_id"] for p in payloads}
    assert len(batch_ids) == 1, f"同一批次出现了多个 batch_id：{batch_ids}"
    for payload in payloads:
        for key in ("page", "anchor_page"):
            value = payload[key]
            # `bool` 是 `int` 的子类，`True == 1` 会静默过关 —— 显式排掉。
            assert isinstance(value, int) and not isinstance(value, bool), (
                f"{payload['field_id']} 的 {key} 是 {value!r}，不是整数"
            )
            assert value >= 1


def test_证据标识全部能在序列化输出里逐字找到(batch):
    """`J-6` 的核心方向：标识必须能在**记录本身**里找到，不能只活在回答里。"""
    for record in batch.records:
        blob = json.dumps(record.to_dict(), ensure_ascii=False)
        for identifier in evidence_identifiers(record):
            assert identifier in blob, (
                f"{record.field_id} 的证据标识 {identifier!r} 在它自己的序列化输出里找不到"
            )
    assert len(EVIDENCE_IDENTIFIER_FIELDS) == 6


def test_序列化输出覆盖记录的每个字段(batch):
    """`to_dict()` 不许悄悄丢字段。

    **这条不是假想风险，是 2026-08-29 实际抓到的一个缺陷的回归**：
    `header_inherited` 是 2026-08-27 为了「算出来的留证不许在接线时被丢掉」
    才加进 `ExtractionRecord` 的，而它当时**没有进 `to_dict()`** ——
    `python -m extractor extract --json` 的 `records[]` 走的正是那个函数，
    于是复核者拿到的证据链里看不见「这一行的列是继承来的」。
    同一个形状（`ARCHITECTURE` §8.5：可选的出处一定会在接线时被丢掉），
    只是落在了下一层。靠记得没用，所以在这里机械锁住。
    """
    payload = batch.records[0].to_dict()
    declared = {f.name for f in fields(ExtractionRecord)}
    missing = sorted(declared - set(payload))
    assert missing == [], f"这些字段没有进 to_dict()：{missing}"


# --------------------------------------------------------------------------
# J-7 / L-2：取数口径三元组
# --------------------------------------------------------------------------


def test_取数口径三元组在真实批次上三项俱全(payloads):
    """`J-7`：缺任一项记 `FAIL`，归因证据层 —— 原话是「它不是证据少，是证据的含义被改了」。"""
    for payload in payloads:
        selection = payload["selection"]
        for part in ("sampling", "order_key", "truncation"):
            assert selection.get(part), f"{payload['field_id']} 的 selection.{part} 是空的"
    # 三元组的三个键必须都在计数口径里，否则上面三行绿了也不影响齐全率。
    for part in ("sampling", "order_key", "truncation"):
        assert f"selection.{part}" in REQUIRED_EVIDENCE_KEYS


def test_三元组任一项为空即判为不齐全(payloads):
    """逐项各造一次空值，每次都必须在 `gaps` 里指名道姓地出现。"""
    for part in ("sampling", "order_key", "truncation"):
        tampered = [dict(p) for p in payloads]
        tampered[0] = dict(tampered[0])
        tampered[0]["selection"] = dict(tampered[0]["selection"])
        tampered[0]["selection"][part] = ""

        report = evidence_completeness(tampered)

        assert report.rate < 1, f"selection.{part} 为空却没有拉低齐全率"
        assert (tampered[0]["field_id"], f"selection.{part}", "空字符串") in report.gaps


# --------------------------------------------------------------------------
# AC-05：字段齐全率的计数口径
# --------------------------------------------------------------------------


def test_真实批次的齐全率是_100(batch):
    """基线。**没有这条，下面几条「变成 < 1」证明不了任何事** —— 一直是 < 1 也能让它们绿。"""
    report = completeness_report(batch)
    assert report.rate == 1, f"真实批次就不齐全：{report.gaps}"
    assert report.meets_ac05()
    assert report.total == len(batch.records) * len(REQUIRED_EVIDENCE_KEYS)


def test_键全在但_unit_是空串时齐全率小于_100(payloads):
    """`AC-05` 写死的口径：「齐全」= **字段有真值**，不是「键存在」。

    反面实证是 hello-agents 的会话记录 —— 八键齐全率也是 100%，
    其中三个是假的。**没有这条测试，`completeness_report` 自己就会变成那个假 100%。**
    """
    tampered = [dict(p) for p in payloads]
    tampered[0] = dict(tampered[0])
    tampered[0]["unit"] = ""

    report = evidence_completeness(tampered)

    # 键还在 —— 这正是要点：按「键存在」数，它会是 100%。
    assert "unit" in tampered[0]
    assert report.rate < 1
    assert not report.meets_ac05()
    assert (tampered[0]["field_id"], "unit", "空字符串") in report.gaps


def test_恒定占位值不计入齐全(payloads):
    """`llm_provider` **恒为 `"unknown"`** 那条实证的直接对应。"""
    tampered = [dict(p) for p in payloads]
    tampered[0] = dict(tampered[0])
    tampered[0]["currency"] = "unknown"

    report = evidence_completeness(tampered)

    assert report.rate < 1
    reasons = [why for fid, key, why in report.gaps if key == "currency"]
    assert reasons and "占位值" in reasons[0]


def test_source_freshness_为_UNKNOWN_时记一处缺口(payloads):
    """`UNKNOWN` 是**如实声明判不出**，但 `AC-05` 数的是「有没有真值」，此时正是没有。

    两件事不冲突：构造边界要求它显式传入（`record.py` 不给默认值），
    齐全率则如实把它记成缺口。方向是保守的 —— 只会把率往下拉，不会往上刷。
    """
    tampered = [dict(p) for p in payloads]
    tampered[0] = dict(tampered[0])
    tampered[0]["source_freshness"] = SourceFreshness.UNKNOWN.name

    report = evidence_completeness(tampered)

    assert report.rate < 1
    assert any(key == "source_freshness" for _, key, _ in report.gaps)


def test_空批次的齐全率是_0_不是_1():
    """「一条记录都没有」不是「证据齐全」。

    返回 1 的话，一个什么都没抽到的批次会满足 `AC-05` ——
    那正是这条标准写死计数口径要防的那种满足方式。
    """
    report = evidence_completeness([])
    assert report.rate == 0
    assert not report.meets_ac05()


# --------------------------------------------------------------------------
# L-45：截断与状态在序列化边界上的交叉断言
# --------------------------------------------------------------------------


def test_success_带着非空_truncation_stats_判为不合法(payloads):
    """`L-45`：报了 `SUCCESS` 的话，证据链里根本不会出现 `truncation_stats`，
    `AC-05` 就会在一个**假成功**上判过。

    构造边界已经拦过这一条（`test_record.py::test_partial_必须带非空_truncation_stats_而_success_必须为空`）。
    这里不是重复：证据链是**读回来的 JSON**，它没有经过那个构造器。
    """
    tampered = [dict(p) for p in payloads]
    tampered[0] = dict(tampered[0])
    assert tampered[0]["status"] == ExtractionStatus.SUCCESS.name
    tampered[0]["truncation_stats"] = {"dropped_rows": 3}

    report = evidence_completeness(tampered)

    assert report.illegal, "SUCCESS + 非空 truncation_stats 没有被判为不合法"
    assert not report.meets_ac05()
    assert "SUCCESS" in report.illegal[0][1]


def test_partial_而计数恒零判为不合法(payloads):
    """`AC-05` 点名的**恒零计数**。这一条构造边界**没有**拦。

    `record._check_truncation_coherence` 只要求 `PARTIAL` 时 `truncation_stats` 非空，
    `{"dropped_rows": 0}` 照样构造得出来 —— 报了「我截断了」，却报不出截了什么。
    """
    tampered = [dict(p) for p in payloads]
    tampered[0] = dict(tampered[0])
    tampered[0]["status"] = ExtractionStatus.PARTIAL.name
    tampered[0]["truncation_stats"] = {"dropped_rows": 0}

    report = evidence_completeness(tampered)

    assert report.illegal
    assert "恒零计数" in report.illegal[0][1]
