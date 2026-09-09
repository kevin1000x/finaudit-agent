"""H2 复核实验器械的回归（`02-03` T1–T3）。

H2 的价值全在**复核者手上那一页里没有答案**。一旦题包泄了题，
拿到的一致率量的是「他会不会读答案」，不是「证据链够不够用」——
而那个数会被当成 Phase 3 的准入门（`ROADMAP` Phase 3 的 `Depends on`）。

**本文件不得引用 `eval/frozen-01`**（同 `test_eval_runner.py` 的理由）：
测试依赖冻结集，人就会有动机去改冻结集，那正是 `D-012` 要防的事。
"""

from __future__ import annotations

import dataclasses
import hashlib
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from eval.h2 import (  # noqa: E402
    REQUIRED_ANNOTATIONS,
    VERDICTS,
    blank_sheet,
    build_packets,
    leak_probes,
    no_leak_problems,
    render_packets,
    score,
)

FIXTURE = (
    "meta:\n"
    "  fixture_id: h2test\n"
    "  nature: 合成数据\n"
    "rows:\n"
    '  - stock_code: "900001"\n'
    "    fiscal_year: 2023\n"
    "    period_type: annual\n"
    "    is.operating_revenue_current: 1000\n"
    "    is.operating_cost: 700\n"
    "    notes.restatement_flag: false\n"
)

#: 一道会**答对**的题（毛利率 = (1000-700)/1000 = 0.3）
GOOD = (
    "id: T-PASS\n"
    "category: C1\n"
    "question: 华鑫科技（900001）2023 年的毛利率是多少？\n"
    "expected:\n"
    "  metric_id: gross_profit_margin\n"
    "  metric_version: 2\n"
    "  value: 0.3\n"
    "  tolerance: {abs: 1.0e-6}\n"
    "  must_not_resolve_to: [__禁用指标哨兵__]\n"
    "  rationale: __标准答案的散文哨兵__\n"
    "required_evidence: [data_source, metric_definition_version, execution_hash]\n"
    "judging: {correctness: tolerance, refusal_expected: false}\n"
    "attribution_hint: __归因提示哨兵__\n"
)

#: 一道会**答错**的题：期望拒答，实际算得出来
BAD = (
    "id: T-FAIL\n"
    "category: C1\n"
    "question: 华鑫科技（900001）2023 年的毛利率是多少？\n"
    "expected:\n"
    "  metric_id: null\n"
    "  value: null\n"
    "  refusal_code: METRIC_NOT_DEFINED\n"
    "  rationale: __第二条标准答案哨兵__\n"
    "required_evidence: [data_source, metric_definition_version, execution_hash]\n"
    "judging: {refusal_expected: true, refusal_code: METRIC_NOT_DEFINED}\n"
    "attribution_hint: __第二条归因哨兵__\n"
)

SENTINELS = [
    "__禁用指标哨兵__",
    "__标准答案的散文哨兵__",
    "__归因提示哨兵__",
    "__第二条标准答案哨兵__",
    "__第二条归因哨兵__",
]


def _suite(tmp_path, cases: list, name: str = "s"):
    suite = tmp_path / name
    (suite / "cases").mkdir(parents=True)
    (suite / "fixtures").mkdir(parents=True)
    (suite / "fixtures" / "h2test.yaml").write_text(FIXTURE, encoding="utf-8")
    lines = []
    for i, body in enumerate(cases):
        p = suite / "cases" / ("C%d.yaml" % i)
        p.write_text(body, encoding="utf-8")
        lines.append(hashlib.sha256(p.read_bytes()).hexdigest() + " *cases/C%d.yaml" % i)
    (suite / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return suite


@pytest.fixture
def built(tmp_path):
    """`(packets, report, suite_dir)` —— `suite_dir` 也要交出来：
    `no_leak_problems` 把它列为必填，没有它那道检查只剩半套。
    """
    suite = _suite(tmp_path, [GOOD, BAD])
    packets, report = build_packets(suite, seed=20260905)
    return packets, report, suite


# ── 不泄题 ──────────────────────────────────────────────────────────────


def test_题面里的标准答案一个字都不进题包(built):
    """🔴 本文件存在的理由。

    哨兵是**构造上不可能**由系统自己算出来的串 —— 它出现在题包里，
    只可能是从题面 `expected` / `rationale` / `judging` / `attribution_hint` 抄过去的。

    ⚠️ 刻意**不**去搜 `expected.value` / `expected.metric_id` / `judging.refusal_code`：
    系统答对时它自己的输出就等于那几个值，搜它们必然误报；
    更要命的是**命中与否本身就泄露了这题的对错**。
    那几项由本条的哨兵结构性地覆盖，见 `leak_probes` 的 docstring。
    """
    packets, _, _ = built
    page = render_packets(packets)
    for s in SENTINELS:
        assert s not in page, "题包里漏出了标准答案：" + s


def test_题包里不出现本次运行的判定与归因(built):
    """`PASS` / `FAIL` / 归因层名 / 判定语，任何一个出现都等于直接把答案写在题面上。"""
    packets, report, _ = built
    page = render_packets(packets)
    for r in report["results"]:
        assert r["status"] not in page, "题包里出现了判定 " + r["status"]
        assert r["detail"] not in page, "题包里出现了判定语"
        for layer in r["attribution"]:
            assert layer not in page, "题包里出现了归因层 " + layer


def test_不泄题这条检查真的会红(built):
    """反空转。没有这一条，上面两条可能只是在检查一个恒不命中的集合。

    做法：把某一题的标准答案散文硬塞进它自己的题包正文，看检查器抓不抓得住。
    """
    packets, report, suite = built
    干净的 = no_leak_problems(packets, report, suite)
    assert 干净的 == [], "干净的题包不该有告警：" + str(干净的)

    脏的 = list(packets)
    脏的[0] = dataclasses.replace(脏的[0], body=脏的[0].body + "\n__标准答案的散文哨兵__")
    assert no_leak_problems(脏的, report, suite) != [], "把标准答案塞进题包，检查器没抓住"


def test_leak_probes_不把系统答对时会复现的值算成泄题(built):
    """判据写在这里，免得下一个人「顺手补全」把 `expected.value` 加进探针。

    加进去的后果有两层：① 系统答对时必然误报；
    ② **命中与否本身就是答案** —— 一个会因为「答对了」而变红的检查，
    等于把判定结果编码进了门禁。
    """
    _, report, _ = built
    case = {
        "expected": {"value": 0.3, "metric_id": "gross_profit_margin"},
        "judging": {"refusal_code": "METRIC_NOT_DEFINED"},
        "rationale": "__标准答案的散文哨兵__",
        "attribution_hint": "__归因提示哨兵__",
    }
    probes = leak_probes(case, report["results"][0])
    assert "__标准答案的散文哨兵__" in probes
    assert "__归因提示哨兵__" in probes
    assert "0.3" not in probes and "gross_profit_margin" not in probes
    assert "METRIC_NOT_DEFINED" not in probes


# ── 普查，不是抽样 ──────────────────────────────────────────────────────


def test_可计分的题一道不落全部进题包(built):
    """`D-037`：`N ≤ 15` 时按**普查**。挑题的余地必须在代码里就不存在。"""
    packets, report, _ = built
    scored = [r["id"] for r in report["results"] if r["status"] in ("PASS", "FAIL")]
    assert sorted(p.case_id for p in packets) == sorted(scored)
    assert len(packets) == 2


def test_未执行的题不进题包(tmp_path):
    """`NOT_RUN` 的题（C4 / C5）没有答案可复核，进题包等于给复核者一页空白。"""
    c4 = (
        "id: T-C4\ncategory: C4\nquestion: 随便\n"
        "expected: {metric_id: null, value: null}\n"
        "judging: {refusal_expected: true}\n"
        "attribution_hint: x\n"
    )
    packets, report = build_packets(_suite(tmp_path, [GOOD, c4]), seed=1)
    assert [p.case_id for p in packets] == ["T-PASS"]


def test_定序被打乱且种子记在案(tmp_path):
    """`Q-C2-*` 连着四道全是拒答，不打乱的话读到第三道就能猜出这一段的形状。"""
    cases = [GOOD, BAD, GOOD.replace("T-PASS", "T-P2"), BAD.replace("T-FAIL", "T-F2")]
    a, _ = build_packets(_suite(tmp_path, cases, "a"), seed=1)
    b, _ = build_packets(_suite(tmp_path, cases, "b"), seed=2)
    assert [p.anon_id for p in a] == [p.anon_id for p in b] == [
        "H2-01", "H2-02", "H2-03", "H2-04",
    ]
    assert [p.case_id for p in a] != [p.case_id for p in b], "换种子顺序没变，说明根本没打乱"
    again, _ = build_packets(_suite(tmp_path, cases, "c"), seed=1)
    assert [p.case_id for p in again] == [p.case_id for p in a], "同种子必须可复现"


# ── 答卷与算数 ──────────────────────────────────────────────────────────


def test_空白答卷不含匿名号以外的任何信息(built):
    packets, _, _ = built
    sheet = yaml.safe_load(blank_sheet(packets))
    assert [r["id"] for r in sheet["verdicts"]] == [p.anon_id for p in packets]
    for row in sheet["verdicts"]:
        assert row["verdict"] is None
        assert set(row) == {"id", "verdict", "note"}
    assert sheet["取值域"] == list(VERDICTS)


def test_答卷没填完就拒绝算数(built):
    """fail-closed。留空**不许**当成「无法判断」——
    「没填」和「填了无法判断」是两件事，混同会让 §4.3 那道反向检验失真。
    """
    packets, report, _ = built
    sheet = yaml.safe_load(blank_sheet(packets))
    sheet["verdicts"][0]["verdict"] = "对"
    got = score(sheet, report, packets)
    assert got["conclusion"] is None
    assert any("没填" in p for p in got["problems"])
    assert packets[1].anon_id in " ".join(got["problems"]), "没点名是哪一题没填"


def _filled(packets, report, override=None):
    status = {r["id"]: r["status"] for r in report["results"]}
    rows = []
    for p in packets:
        v = (override or {}).get(p.case_id)
        if v is None:
            v = "对" if status[p.case_id] == "PASS" else "错"
        rows.append({"id": p.anon_id, "verdict": v, "note": ""})
    return {"verdicts": rows}


def test_无法判断不计入一致率并单独统计(tmp_path):
    """§4.3 的反向检验数的就是它；把它算进一致率，两个指标就都失真了。"""
    cases = [GOOD, BAD, GOOD.replace("T-PASS", "T-P2"), BAD.replace("T-FAIL", "T-F2")]
    packets, report = build_packets(_suite(tmp_path, cases), seed=7)
    got = score(_filled(packets, report, {"T-P2": "无法判断"}), report, packets)
    assert got["n"] == 4
    assert got["agreed"] == 3, "「无法判断」被算成一致了"
    assert got["undecidable"] == 1
    assert got["undecidable_rate"] == pytest.approx(0.25)


def test_三条强制标注一条都不能少(built):
    """`D-037`：缺一项即视为未按 §4.1.1 执行 —— 那就不许给结论。"""
    packets, report, _ = built
    got = score(_filled(packets, report), report, packets)
    assert got["conclusion"] is not None, got["problems"]
    for key in REQUIRED_ANNOTATIONS:
        assert key in got["annotations"], "缺了强制标注 " + key
    assert got["annotations"]["sampling"] == "普查"
    assert got["annotations"]["w_ge_5_satisfied"] is False
    assert got["annotations"]["w"] == 1
    assert "1/1" in str(got["annotations"]["resolution_floor_on_wrong"])


def test_错题子集给的是原始计数不是只有百分比(built):
    """§4.2 附注：`W < 5` 时百分比读不出东西，必须能看见 `x / W`。"""
    packets, report, _ = built
    got = score(_filled(packets, report), report, packets)
    assert got["wrong_subset"] == {"agreed": 1, "total": 1, "raw": "1/1"}


# ──────────────────── `N-75`：盲出题包 ────────────────────


def test_blind_出包时报告对象根本不出函数(tmp_path):
    """判据不是「调用方自觉别看」，是**它手上没有那个对象**。

    2026-09-09 栽过的那次：执行者读了跑分结果、把「21/21 全对」告诉了复核者本人，
    §4.2 一致率当场作废（`N-75`）。拿不到 `report` 就印不出 `W`。

    它会红的场景：有人把 `blind` 参数忽略掉，或把 `report` 照样返回。
    """
    suite = _suite(tmp_path, [GOOD, BAD])
    packets, report = build_packets(suite, seed=1, blind=True)
    assert report is None, "盲模式下报告仍然被交了出来 —— 那条泄露路径没封住"
    assert len(packets) == 2, "盲不该改变收哪几题：普查，一道不落"


def test_blind_不改变题包内容(tmp_path):
    """盲的是「谁看得到结果」，不是「出哪些题」。**两者必须逐字节相同**，

    否则 `--blind` 就成了另一个实验，而不是同一个实验的安全出法。
    """
    a, _ = build_packets(_suite(tmp_path, [GOOD, BAD], "a"), seed=5, blind=True)
    b, rep = build_packets(_suite(tmp_path, [GOOD, BAD], "b"), seed=5, blind=False)
    assert rep is not None
    assert [p.anon_id for p in a] == [p.anon_id for p in b]
    assert [p.body for p in a] == [p.body for p in b]


def test_没有BUILD_json时blind_build记未声明而不是记是(tmp_path):
    """**fail-closed**：一份不知道是不是盲出的题包，必须当成可能已经泄底的来读。

    `h2-01` / `h2-02` 都产在这个字段存在之前 ⇒ 它们永远落在「未声明」这一档，
    这正确 —— 那两轮确实无从证明是盲出的。
    """
    suite = _suite(tmp_path, [GOOD, BAD])
    packets, report = build_packets(suite, seed=3)
    sheet = {"verdicts": [{"id": p.anon_id, "verdict": "对"} for p in packets]}

    got = score(sheet, report, packets, build_info=None)
    assert "未声明" in got["annotations"]["blind_build"]

    got2 = score(sheet, report, packets, build_info={"blind": False})
    assert "未声明" in got2["annotations"]["blind_build"], "blind=false 也不该记成盲出"

    got3 = score(sheet, report, packets, build_info={"blind": True})
    assert got3["annotations"]["blind_build"].startswith("是")


def test_blind_与sheet互斥(tmp_path, capsys):
    """算数必须读跑分结果，盲不了。**明确报错，不静默忽略。**

    静默忽略的后果是：使用者以为自己盲着算了一遍，其实没有。
    """
    from eval import h2

    suite = _suite(tmp_path, [GOOD, BAD])
    sheet = tmp_path / "s.yaml"
    sheet.write_text("verdicts: []\n", encoding="utf-8")
    rc = h2.main(["--suite", suite.name, "--sheet", str(sheet), "--blind"])
    assert rc == 2
    assert "不能同时给" in capsys.readouterr().err


# ──────────── 强制标注的**值**也要成立，不只是键在不在（2026-09-10） ────────────


def _sheet(packets, results_by_anon):
    return {"verdicts": [{"id": p.anon_id, "verdict": results_by_anon[p.anon_id]} for p in packets]}


def _all(packets, verdict):
    return {"verdicts": [{"id": p.anon_id, "verdict": verdict} for p in packets]}


def test_一致率达标但W为0时不给通过(tmp_path):
    """🔴 2026-09-10 实测出来的逻辑洞。

    `h2-frozen-02` 那一轮在同一屏上印出了「判定：H2 通过」与
    「blind_build: 未声明 —— 一致率不可当作 AC-06 读数」，**自己跟自己拧着**。
    根因：`W < 5` 那道守卫只挂在 60–80% 那一档，≥80% 直接放行 ——
    而 `W = 0` 恰恰是最该拦的情形：一致率整个落在正确答案上，
    测不到「证据页帮不帮得上抓错」。

    它会红的场景：有人把 `pass_blocked` 拿掉，或只在某一档里判 `w < 5`。
    """
    suite = _suite(tmp_path, [GOOD, GOOD])
    packets, report = build_packets(suite, seed=1)
    got = score(_all(packets, "对"), report, packets, build_info={"blind": True})

    assert got["agreement_rate"] == 1.0
    assert got["annotations"]["w"] == 0
    assert got["conclusion"] is not None
    assert "H2 通过" != got["conclusion"]
    assert got["pass_blocked"], "W=0 却没有挡下「通过」"
    assert any("W = 0" in r for r in got["pass_blocked"])


def test_非盲出的题包同样挡下通过(tmp_path):
    """`N-75`：复核者可能已知答案时，每个「对」都不含信息。

    与上一条**分开测**：两个前提各自独立成立，合在一条里，
    去掉其中一个判据测试照样绿。
    """
    suite = _suite(tmp_path, [GOOD, GOOD])
    packets, report = build_packets(suite, seed=1)
    got = score(_all(packets, "对"), report, packets, build_info={"blind": False})
    assert any("非盲出" in r for r in got["pass_blocked"])

    got_blind = score(_all(packets, "对"), report, packets, build_info={"blind": True})
    assert not any("非盲出" in r for r in got_blind["pass_blocked"]), (
        "盲出的题包不该因为这一条被挡"
    )


def test_停止信号不受这些前提影响(tmp_path):
    """⚠️ **不对称是刻意的。**

    「通过」是宽松结论，需要完整前提；「不成立」是停止信号 ——
    没有错题子集照样断定得了证据链不够用。把停止信号也一起挡掉才是危险的：
    那等于在证据链最差的时候让门禁沉默。

    它会红的场景：有人图省事，把 `pass_blocked` 改成对所有档位一律拦下。
    """
    suite = _suite(tmp_path, [GOOD, GOOD])
    packets, report = build_packets(suite, seed=1)
    # 全判「无法判断」⇒ 一致率 0%，落在 <60% 那一档
    got = score(_all(packets, "无法判断"), report, packets, build_info=None)

    assert got["agreement_rate"] == 0.0
    assert got["annotations"]["w"] == 0, "本例的 W 同样是 0"
    assert got["conclusion"] is not None, "停止信号被挡掉了 —— 这比放过一个「通过」更危险"
    assert "H2 不成立" in got["conclusion"]


def test_前提齐全时通过仍然给得出来(tmp_path):
    """**反方向的一半**：别把门修成永远不给「通过」，那样它就不是门了。

    5 道答错 + 5 道答对，全判对，盲出 ⇒ `W = 5` 满足、`blind_build` 是 ⇒ 应当给「通过」。
    """
    suite = _suite(tmp_path, [GOOD] * 5 + [BAD] * 5)
    packets, report = build_packets(suite, seed=2)
    assert len(packets) == 10

    # ⚠️ `case_id` 来自题面 YAML 里的 `id:`（`T-PASS` / `T-FAIL`），
    #    **不是** `_suite` 写出来的文件名 `C0…C9`。初版按文件名判，条件恒假，
    #    于是全判「对」得 50%，落进「不成立」那一档 —— 测试当场把它抓了出来。
    by_anon = {p.anon_id: ("错" if _is_fail(report, p.case_id) else "对") for p in packets}
    got = score({"verdicts": [{"id": a, "verdict": v} for a, v in by_anon.items()]},
                report, packets, build_info={"blind": True})

    assert got["annotations"]["w"] == 5, got["annotations"]
    assert got["annotations"]["w_ge_5_satisfied"] is True
    assert not got["pass_blocked"], got["pass_blocked"]
    assert got["conclusion"] == "H2 通过"


def _is_fail(report, case_id):
    from eval.run import FAIL as _F

    return {r["id"]: r["status"] for r in report["results"]}[case_id] == _F
