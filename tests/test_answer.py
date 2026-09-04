"""`src/agent/answer.py` 的回归（`02-01` T3）。

两件产物：结构化答案对象（`AC-05` 数它）与人读渲染（`AC-06` 的复核者读它）。
本文件盯的是**两者各自的硬约束**，以及 `D-032` 那条「口径一节逐字一致」。
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from agent.answer import (
    REQUIRED_ANSWER_EVIDENCE,
    Answer,
    FixtureSource,
    answer_question,
    evidence_gaps,
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
    return "not_reached" if a.gate == "not_reached" else "reached"


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
    assert set(ok.to_dict()) == set(bad.to_dict())


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
    assert a.gate == "not_reached"
    assert a.evidence["metric_definition_version"] is None
    keys = required_answer_evidence("not_reached")
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
