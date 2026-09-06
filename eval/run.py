"""评测运行器。

三条纪律直接落在代码里，不靠人记：

1. **fail-closed 冻结校验**（D-012 的物理保障）。`verify_freeze` 是运行的前置门：
   哈希对不上、清单缺失、文件缺失，任一发生即拒绝运行，**且一道题都不执行**。
   改了题面就跑不了评测，而不是跑完了才发现题面被改过。

2. **未执行 ≠ 通过**。Phase 1 不具备数值执行、准则检索、图谱能力，
   相应类别在报告里标 `NOT_RUN`，绝不标 PASS。把没跑的当通过是评测报告最常见的谎。

3. **归因不改分数**（EVAL_CASES §5.1）。归因是诊断投影：一道失败题无论归到哪一层
   都仍然是失败，不因归因而从分母里消失。唯一能离开分母的是 §2.2 的**构造错误作废**，
   而那必须不看系统输出即可认定。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

EVAL_ROOT = Path(__file__).resolve().parent
REPO_ROOT = EVAL_ROOT.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

CATEGORIES = ["C1", "C2", "C3", "C4", "C5"]

# Phase 1 只具备口径解析与拒答判定，没有数值执行、准则检索、图谱。
# 这个集合是**能力声明**，不是偷懒开关——不在其中的类别一律 NOT_RUN。
EXECUTABLE_IN_PHASE_1 = {"C2"}

# Phase 2（`02-01`）接上了 `src/agent/` 的问答路径：意图 → 闸门 → 计算 → 证据链。
# C1 / C3 都是「某主体某期某指标」的形状，**有路径可走** ⇒ 进执行集。
# ⚠️ **进执行集不等于会通过。** C3 里有跨期比较、只给公司简称不给代码这类题，
#    我们的路径答不了 —— 那是 **FAIL**，不是 NOT_RUN。
#    把有路径可走的题标成「未执行」，正是本文件开头第 2 条纪律禁的那种谎。
# C4（准则检索）与 C5（图谱）确实没有路径 ⇒ 仍然 NOT_RUN。
EXECUTABLE_IN_PHASE_2 = {"C1", "C2", "C3"}

# `EVAL_CASES` §5 的归因分层。不允许「未知」。
# 🔴 **2026-09-05 起是五层，且判分函数不再自己写层名**（`D-035` / `02-02` T1）：
#    层由 `eval/attribution.py` 从**机读状态**算出来 —— `RefusalCode` 封闭枚举、
#    `Answer.gate` 三态、`metric_id` / `metric_version`，一概不碰 `detail` 的措辞（§5.3）。
#    判分函数只报「这次为什么判失败」（`FailureKind`），它不知道层。
from .attribution import LAYERS, FailureKind, attribute, reachable_layers  # noqa: E402

PASS, FAIL, NOT_RUN, VOIDED = "PASS", "FAIL", "NOT_RUN", "VOIDED"

#: 题面的 `expected` 块，按 case id 索引。由 `run_suite` 在每次运行开始时重填 ——
#: **只读题面，不写题面**（`D-012`：frozen-01 一个字节都不许改）。
_EXPECTED: dict = {}

# §2.2：单批次构造错误作废率上限
MAX_VOID_RATIO = 0.10
# §7 Phase 1 门第 2 条：C2 存活题数低于此值时，拒答准确率门不成立
MIN_C2_SURVIVORS = 3


# --------------------------------------------------------------------------
# 冻结校验
# --------------------------------------------------------------------------


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def verify_freeze(suite_dir: Path) -> tuple[bool, list[str]]:
    """校验套件目录下的 SHA256SUMS。返回 (是否通过, 问题清单)。

    任一不符、清单缺失、文件缺失都返回 False —— 不抛未捕获异常，也不当作通过。
    """
    problems: list[str] = []
    manifest = suite_dir / "SHA256SUMS"
    if not manifest.is_file():
        return False, [f"冻结清单缺失：{manifest}"]

    listed: set[str] = set()
    for line in manifest.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            problems.append(f"清单格式不可解析：{line!r}")
            continue
        want, rel = parts[0], parts[1].lstrip("*").strip()
        listed.add(rel)
        target = suite_dir / rel
        if not target.is_file():
            problems.append(f"清单所列文件缺失：{rel}")
            continue
        got = _sha256(target)
        if got != want:
            problems.append(f"哈希不符：{rel}\n    清单 {want}\n    实际 {got}")

    # 反向检查：目录里多出清单未收录的题面，同样是冻结集被动过
    for path in sorted((suite_dir / "cases").glob("*.yaml")):
        rel = path.relative_to(suite_dir).as_posix()
        if rel not in listed:
            problems.append(f"题面未被冻结清单收录：{rel}")

    return (not problems), problems


# --------------------------------------------------------------------------
# 判定
# --------------------------------------------------------------------------


@dataclass
class CaseResult:
    case_id: str
    category: str
    status: str
    detail: str = ""
    layers: list[str] = field(default_factory=list)
    #: 这次归因**是从哪个机读状态算出来的**。没有它，复核者看到的
    #: 只是一个层名加一句「相信我」（`EVAL_CASES` §5.3 要的可复核性）。
    attribution_basis: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.case_id,
            "category": self.category,
            "status": self.status,
            "detail": self.detail,
            "attribution": self.layers,
            "attribution_basis": self.attribution_basis,
        }


def _fail(cid: str, cat: str, detail: str, kind: FailureKind, answer=None) -> CaseResult:
    """一次失败。**层不在这里写死** —— 交给 `attribute()` 从机读状态算。

    判分函数只知道「比对的是什么对不上」（`kind`）；
    「那属于哪一层」是归因模块的事，两件事分开才验得了
    「换一套归因，分数一个字不变」（`EVAL_CASES` §5.1）。
    """
    got = attribute(kind, answer)
    return CaseResult(cid, cat, FAIL, detail, list(got.layers), got.basis)


def judge_refusal_case(case: dict, outcome, refusal_cls) -> CaseResult:
    """C2 类判定，严格按 EVAL_CASES §3.2。

    拒答且理由码正确 → PASS
    拒答但理由码不符 → FAIL
    强行给出答案     → FAIL，**即使数值碰巧正确也算失败**

    ⚠️ **本函数不写层名。** 它报 `FailureKind`，层由 `attribution.attribute()` 算。
    """
    cid, cat = case["id"], case["category"]
    want_code = case.get("judging", {}).get("refusal_code") or case.get("expected", {}).get(
        "refusal_code"
    )

    if not isinstance(outcome, refusal_cls):
        return _fail(
            cid, cat,
            f"期望拒答，实际返回了指标定义 {getattr(outcome, 'metric_id', '?')!r}。"
            "按 §3.2，强行作答即使数值碰巧正确也算失败。",
            FailureKind.ANSWERED_BUT_SHOULD_REFUSE,
        )

    got_code = outcome.code.name
    if want_code and got_code != want_code:
        return _fail(
            cid, cat,
            f"拒答理由码不符：期望 {want_code}，实际 {got_code}",
            FailureKind.WRONG_REFUSAL_CODE,
        )
    return CaseResult(cid, cat, PASS, f"正确拒答，理由码 {got_code}")


def judge_answer_case(case: dict, answer) -> "CaseResult":
    """数值题的判定。**容差由题面自己声明**，不是运行器发明的。

    `expected.tolerance` 形如 `{abs: 1.0e-4, rel: 1.0e-9}`，20 份题面里逐题写着
    （`EVAL_CASES` §3.1 的 schema）。运行器**不许**自己挑一个容差 ——
    那等于事后为难看的结果放宽标准。
    """
    from decimal import Decimal

    cid, cat = case["id"], case["category"]
    exp = case.get("expected") or {}
    want = exp.get("value")

    if answer.refused:
        # 🔴 层由**拒答码**决定，不再一律记口径层（`D-035` ③）：
        #    `INTENT_INCOMPLETE` 是意图层 —— 题面缺主体 / 多期间，
        #    与口径无关，闸门之后一步都没走。
        return _fail(
            cid, cat,
            f"期望数值 {want}，实际拒答（{answer.refusal['code']}）：{answer.refusal['detail'][:80]}",
            FailureKind.REFUSED_BUT_SHOULD_ANSWER, answer,
        )
    if answer.value is None:
        return _fail(cid, cat, "既没拒答也没给出数值", FailureKind.NO_VALUE_NO_REFUSAL)

    if isinstance(want, (dict, list, set, tuple)):
        # `Q-C3-004` 的标准答案是**两期的一个映射**。本路径只产单期标量 ——
        # 如实判 FAIL 并说清楚，**不要在这里 `Decimal(str(dict))` 崩掉**：
        # 崩掉会让整批评测终止，而一道答不了的题不该拖垮另外十九道。
        return _fail(
            cid, cat,
            f"标准答案是集合/多期结构（{type(want).__name__}），本路径只产单期标量",
            FailureKind.EXPECTED_NON_SCALAR,
        )

    tol = exp.get("tolerance") or {}
    abs_tol = Decimal(str(tol.get("abs", 0)))
    rel_tol = Decimal(str(tol.get("rel", 0)))
    got, target = Decimal(str(answer.value)), Decimal(str(want))
    diff = abs(got - target)
    ok = diff <= abs_tol or (target != 0 and diff / abs(target) <= rel_tol)
    if not ok:
        return _fail(
            cid, cat,
            f"数值不在容差内：算出 {got}，标准答案 {target}，差 {diff}",
            FailureKind.VALUE_OUT_OF_TOLERANCE,
        )

    want_metric = exp.get("metric_id")
    if want_metric and answer.metric_id != want_metric:
        return _fail(
            cid, cat,
            f"数值对了但口径不对：用的是 {answer.metric_id}，应为 {want_metric}",
            FailureKind.WRONG_METRIC,
        )
    want_version = exp.get("metric_version")
    if want_version is not None and answer.metric_version != want_version:
        return _fail(
            cid, cat,
            f"口径版本不符：用的是 {answer.metric_version}，应为 {want_version}",
            FailureKind.WRONG_VERSION,
        )
    return CaseResult(cid, cat, PASS, f"数值 {got} 在容差内，口径与版本均相符")


def load_cases(suite_dir: Path) -> list[dict]:
    cases = []
    for path in sorted((suite_dir / "cases").glob("*.yaml")):
        cases.append(yaml.safe_load(path.read_text(encoding="utf-8")))
    return cases


def run_suite(
    suite_dir: Path, only_category: str | None = None, collect: dict | None = None
) -> dict:
    """系统臂。**Phase 2 起走 `src/agent/` 的完整问答路径。**

    `collect` 给进来的话，会填上 `{case_id: Answer}`。
    ⚠️ 它存在的理由只有一个：`eval/h2.py` 的题包**必须来自产出这份报告的那一次运行**，
    不是「拿同样的输入再算一遍」。重算在今天是等价的（整条路径确定性），
    但那是一个会悄悄失效的前提 —— 复核者看的那页和拿来比对的判定必须同源。

    ⚠️ 本函数**不 import 任何 LLM 客户端**。意图解析的模型是注入式的，
    这里不注入 ⇒ 整条路径离线跑完（`D-033`）。
    `eval/llm_client.py` 只服务对照臂，它自己的 docstring 明写「永远不会被系统臂导入」。
    """
    from agent.answer import (
        answer_question,
        evidence_gaps,
        evidence_stage,
        required_answer_evidence,
    )
    from agent.answer import FixtureSource
    from semantic_layer.resolve import Refusal, Registry

    registry = Registry.load(REPO_ROOT / "metrics")
    cases = load_cases(suite_dir)
    # 夹具按目录发现，**不硬编码文件名** —— 写死 `synthetic-01.yaml` 会让
    # 任何别的套件（含 `eval/testdata/sample-suite`）静默拿不到数据源，
    # 于是每道题都以 `UNAVAILABLE` 拒答：**红是红了，红的原因却不是它要测的那件事。**
    fixtures = sorted((suite_dir / "fixtures").glob("*.yaml"))
    if len(fixtures) > 1:
        raise ValueError(
            f"{suite_dir.name}/fixtures 下有 {len(fixtures)} 份夹具，"
            "运行器不替人挑一份 —— 挑错了整批结论都建立在错的数据上"
        )
    source = FixtureSource(fixtures[0]) if fixtures else None

    _EXPECTED.clear()
    for c in cases:
        _EXPECTED[c["id"]] = dict(c.get("expected") or {})

    answers: dict = {}
    evidence_gap_by_case: dict = {}
    evidence_notes: list = []
    results: list[CaseResult] = []
    for case in cases:
        cid, cat = case["id"], case["category"]

        # §2.2：构造错误作废的题移出分母，但必须在报告里单独列出，不静默消失
        if str(case.get("voided", "")).strip():
            results.append(CaseResult(cid, cat, VOIDED, str(case["voided"])))
            continue

        if only_category and cat != only_category:
            results.append(CaseResult(cid, cat, NOT_RUN, f"--category {only_category} 未选中本类"))
            continue

        if cat not in EXECUTABLE_IN_PHASE_2:
            results.append(
                CaseResult(cid, cat, NOT_RUN, "本阶段不具备该类所需能力（准则检索 / 图谱）")
            )
            continue

        question = " ".join(str(case.get("question", "")).split())
        answer = answer_question(question, registry, source=source)
        answers[cid] = answer

        # 证据链完整率：**用题面自己声明的 `required_evidence`**，不是运行器发明的一套。
        # ⚠️ 一处如实披露的收窄：**题面连指标都没解析出来时**（判据是 `metric_id is None`，
        #    不是 `gate` 的取值 —— 后者把「没解析出指标」与「数据源没这一行」混成了一件事），
        #    `metric_definition_version` 不适用（没有指标哪来的版本）。
        #    这照搬 `extractor.pipeline.required_evidence_keys` 的先例 ——
        #    照字面数会让 AC-05 这条**保证类**标准变成一个正确实现永远达不到的标准。
        #    **不静默**：收窄逐条记进报告的 `evidence_scope_notes`。
        declared = tuple(case.get("required_evidence") or ())
        stage = evidence_stage(answer)
        applicable = tuple(k for k in declared if k in required_answer_evidence(stage))
        if set(applicable) != set(declared):
            evidence_notes.append(
                {
                    "case": cid,
                    "stage": stage,
                    "dropped": sorted(set(declared) - set(applicable)),
                    "why": "该题在解析出指标之前就拒答了，这些键不适用；已反向要求它们为空",
                }
            )
        # `Answer` 是 frozen dataclass —— 旁挂，不往上塞属性。
        evidence_gap_by_case[cid] = evidence_gaps(answer.evidence, applicable)

        expects_refusal = bool(
            (case.get("judging") or {}).get("refusal_expected")
        ) or (case.get("expected") or {}).get("value") is None
        if expects_refusal:
            outcome = _as_refusal(answer, Refusal)
            results.append(judge_refusal_case(case, outcome, Refusal))
        else:
            results.append(judge_answer_case(case, answer))

    # ── T3：`attribution_hint` 的事后对照 ────────────────────────────
    # 🔴 **判分时不可见**（`EVAL_CASES` §3.1）：本段在**判分循环结束之后**
    #    才第一次读 `attribution_hint`，`judge_*` 一次都没碰过它
    #    （`tests/test_attribution.py` 用语法树钉死了这一点）。
    # ⚠️ **不许把它折成一个准确率数字。** hint 是**出题时预判**的陷阱，
    #    实际归因是**这一次真实**的失败点 —— 两者不一致不是失败信号。
    #    折成百分比会立刻被读成「归因准了几成」，那是个不存在的东西。
    hint_rows = _hint_comparison(cases, results)

    if collect is not None:
        collect.update(answers)

    return _summarize(
        suite_dir, results, only_category, answers, evidence_gap_by_case, evidence_notes,
        hint_rows,
    )


def _hint_comparison(cases: list, results: list) -> list:
    """失败题的「实际归因 vs 出题时的 `attribution_hint`」逐条对照。

    只列**失败题** —— 通过的题没有归因，拿 hint 去对一个空集合毫无意义。
    """
    by_id = {c["id"]: c for c in cases}
    rows = []
    for r in results:
        if r.status != FAIL:
            continue
        hint = (by_id.get(r.case_id) or {}).get("attribution_hint")
        rows.append(
            {
                "case": r.case_id,
                "actual_layers": list(r.layers),
                "basis": r.attribution_basis,
                "hint": " ".join(str(hint).split()) if hint else None,
            }
        )
    return rows


def _as_refusal(answer, refusal_cls):
    """把 `Answer` 折成 `judge_refusal_case` 认得的形状。

    没拒答时返回 `answer` 本身 —— 那条判定分支要的正是「不是 Refusal」。
    """
    if not answer.refused:
        return answer
    from semantic_layer.resolve import RefusalCode

    return refusal_cls(
        RefusalCode[answer.refusal["code"]],
        answer.refusal["detail"],
        metric_id=answer.refusal.get("metric_id"),
    )


# 🔴 `_target_from_question` 已删除（2026-09-05）。
# 它读的是 `expected.target_name` —— **把标准答案喂回系统输入**。
# Phase 2 起系统臂真的解析题面，这个函数在那次改动里就没有调用点了，
# 但**留着**等于在运行器里搁一把上了膛的枪：任何人想让某道题过，
# 手边就有一个现成的兜底。`tests/test_eval_runner.py` 有一条测试钉死
# 「运行器不许偷看 target_name」，这里把它可能被偷看的入口一并去掉。


def _summarize(
    suite_dir: Path,
    results: list[CaseResult],
    only_category: str | None,
    answers: dict | None = None,
    evidence_gap_by_case: dict | None = None,
    evidence_notes: list | None = None,
    hint_rows: list | None = None,
) -> dict:
    voided = [r for r in results if r.status == VOIDED]
    scored = [r for r in results if r.status in (PASS, FAIL)]
    not_run = [r for r in results if r.status == NOT_RUN]

    total_authored = len(results)
    void_ratio = len(voided) / total_authored if total_authored else 0.0

    by_cat = {}
    for cat in CATEGORIES:
        rs = [r for r in results if r.category == cat]
        surviving = [r for r in rs if r.status != VOIDED]
        passed = [r for r in rs if r.status == PASS]
        ran = [r for r in rs if r.status in (PASS, FAIL)]
        by_cat[cat] = {
            "authored": len(rs),
            "voided": len([r for r in rs if r.status == VOIDED]),
            "surviving": len(surviving),
            "executed": len(ran),
            "passed": len(passed),
            "status": (
                NOT_RUN if not ran else (PASS if len(passed) == len(ran) else FAIL)
            ),
        }

    c2 = by_cat["C2"]
    c2_gate = {
        "surviving": c2["surviving"],
        "executed": c2["executed"],
        "passed": c2["passed"],
        "accuracy": f"{c2['passed']}/{c2['executed']}" if c2["executed"] else "N/A",
        # §7 Phase 1 门第 2 条：存活题数 < 3 时本门不成立
        # ——否则作废到只剩 1 题再报 100% 就是钻空子
        "gate_holds": c2["executed"] > 0
        and c2["surviving"] >= MIN_C2_SURVIVORS
        and c2["passed"] == c2["executed"],
        "gate_note": (
            f"C2 存活题数 {c2['surviving']} < {MIN_C2_SURVIVORS}，本门不成立"
            if c2["surviving"] < MIN_C2_SURVIVORS
            else "存活题数满足下限"
        ),
    }

    return {
        "suite": suite_dir.name,
        "run_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "filter_category": only_category,
        "counts": {
            "authored": total_authored,
            "voided": len(voided),
            "scored_denominator": len(scored),
            "not_run": len(not_run),
            "passed": len([r for r in scored if r.status == PASS]),
            "failed": len([r for r in scored if r.status == FAIL]),
        },
        # §2.2：作废率上限 10%，超了整批判为构造失败
        "void_ratio": round(void_ratio, 4),
        "void_ratio_within_limit": void_ratio <= MAX_VOID_RATIO,
        "voided_cases": [r.to_dict() for r in voided],
        "by_category": by_cat,
        "c2_refusal_gate": c2_gate,
        # §6 的指标名。本阶段不具备条件的一律 N/A，不填 0 也不省略
        "metrics": {
            "口径正确率": _rate(*_definition_hits(answers, results)),
            "拒答准确率": c2_gate["accuracy"],
            "答案正确率": _rate(*_value_hits(results)),
            "证据链完整率": _evidence_metric(evidence_gap_by_case, evidence_notes),
            # ⚠️ 这一格**不由本运行器产出**，也不许在这里硬写一个数 ——
            #    H2 是人做的实验，数在 `docs/agent/VERIFICATION.md` §F，
            #    由 `python -m eval.h2 --sheet …` 算出。
            #    （2026-09-06 之前这里写的是「H2 复核实验在 02-03」，
            #      而那时 02-03 已经做完且判定**不成立** —— 一个会过期的字符串。）
            "复核一致率": "不由本运行器产出：见 VERIFICATION.md §F（`python -m eval.h2 --sheet …`）",
            "引用可定位率": "N/A（准则检索是 Phase 3 的 L2）",
            "归因覆盖率": _rate(*_attribution_hits(scored)),
        },
        # ⚠️ 收窄要**逐条摆出来**，不静默。见 `run_suite` 里那段注释。
        "evidence_scope_notes": list(evidence_notes or []),
        # `AC-08` 的门（`02-02` T2）：出现一道未归因的失败即不满足。
        # **保证类标准**，不是统计目标 —— `main()` 据此非零退出并点名。
        # ⚠️ **`AC-08` 的分母是「失败题」，不是「非通过题」。**
        #    `NOT_RUN` 是**能力缺口的声明**不是失败；`VOIDED` 按 §2.2 已在分母之外。
        #    给它们挂层会让那一层的数字虚高 —— 与 §5.0 给 `UNPARSEABLE` 立的是同一条规则。
        "unattributed_failures": [
            r.case_id for r in results if r.status == FAIL and not r.layers
        ],
        # 事后对照，**不是准确率**。见 `_hint_comparison` 的注释。
        "attribution_hint_comparison": list(hint_rows or []),
        # 每一层实际吃到几道失败题。**零产出的层要看得见** ——
        # 一个定义了却从没被吐出来过的层是 `L-25` 那种死抽象，
        # 而它藏在「归因覆盖率 100%」后面完全看不出来。
        "layer_usage": {
            layer: sum(1 for r in results if r.status == FAIL and layer in r.layers)
            for layer in LAYERS
        },
        # 🔴 **「本批零产出」与「结构上不可达」是两件事。**
        #    前者是数据（这一次没有这类失败），后者是 `L-25` 那种死抽象
        #    （当前实现里没有任何一条路能产出它）。混成一句，读的人会以为
        #    再多跑几批就有了 —— 而不可达的那个再跑一万批也不会有。
        "unreachable_layers": [ell for ell in LAYERS if ell not in reachable_layers()],
        "results": [r.to_dict() for r in results],
    }


def _rate(hit: int, total: int) -> str:
    """`N/M（xx.x%）`。**分母为 0 时说「无可计分题」，不写 0% 也不写 100%** ——
    两者都会被读成一个结论，而事实是这一批没有可判的题。
    """
    if total == 0:
        return "N/A（本批没有可计分的题）"
    return f"{hit}/{total}（{hit / total:.1%}）"


def _definition_hits(answers: dict | None, results: list) -> tuple:
    """口径正确率 = 选对指标定义**且版本匹配**的题目占比（`EVAL_CASES` §6）。

    分母是**声明了 `expected.metric_id` 的已计分题**：没声明靶子的题
    （C2 那几道 `metric_id: null`）无从判「选对没有」。
    """
    if not answers:
        return 0, 0
    scored_ids = {r.case_id for r in results if r.status in (PASS, FAIL)}
    hit = total = 0
    for cid, ans in answers.items():
        if cid not in scored_ids:
            continue
        want = _EXPECTED.get(cid) or {}
        if not want.get("metric_id"):
            continue
        total += 1
        if ans.metric_id == want["metric_id"] and ans.metric_version == want.get("metric_version"):
            hit += 1
    return hit, total


def _value_hits(results: list) -> tuple:
    """答案正确率 = 数值在容差内匹配标准答案的占比。

    分母是**声明了 `expected.value` 的已计分题** —— 拒答题不在其中。
    """
    total = hit = 0
    for r in results:
        want = _EXPECTED.get(r.case_id) or {}
        if want.get("value") is None or r.status not in (PASS, FAIL):
            continue
        total += 1
        hit += r.status == PASS
    return hit, total


def _attribution_hits(scored: list) -> tuple:
    """归因覆盖率 = **失败题**中已归因的占比（`AC-08`，目标 100%）。

    ⚠️ 2026-09-04 修：此前写的是 `"100%" if all(...) else "<100%"`，
    而 `all()` 对**空**生成器为真 —— 于是一批**零失败**的运行会报「归因覆盖率 100%」。
    同一个函数里 `_rate()` 在分母为 0 时明写「不许报 0% 也不许报 100%」，
    这一格却没照走。**「没有失败题」与「失败题全都归了因」是两件事**，
    而 `100%` 会被读成后者 —— 正是本文件开头第 2 条纪律禁的那种谎。

    由独立复核发现（子 agent，`02-02` 起草过程中），实跑
    `run_suite(sample_suite, "C4")` 复现：计分分母 0、失败 0，却报 100%。
    """
    failed = [r for r in scored if r.status == FAIL]
    return sum(1 for r in failed if r.layers), len(failed)


def _evidence_hits(gap_by_case: dict | None) -> tuple:
    """证据链完整率 = 必需字段齐全的题目占比（目标 100%，Phase 2 门第 1 条）。"""
    if not gap_by_case:
        return 0, 0
    return sum(1 for g in gap_by_case.values() if not g), len(gap_by_case)


def _evidence_metric(gap_by_case: dict | None, notes: list | None) -> str:
    """证据链完整率这一格的文字。**收窄的题数与分数写在同一格里。**

    🟡 2026-09-05 独立复核指出：`15/15（100.0%）` 这个读数底下，
    有 8 题走的是**收窄后**的键集（题面连指标都没解析出来 ⇒
    `metric_definition_version` 不适用）。收窄本身逐条记进了
    `evidence_scope_notes`，但**那个字段只在 JSON 里，`render()` 不打印它** ——
    于是人读报告里只剩一个满分。

    ⚠️ 分子分母不因此改变（收窄不是豁免，见 `required_answer_evidence`），
    改变的是**这个数字旁边有没有写清它是怎么数出来的**。
    """
    base = _rate(*_evidence_hits(gap_by_case))
    n = len(notes or [])
    if not n:
        return base
    return f"{base}；其中 {n} 题按收窄后的键集计（见 evidence_scope_notes）"


# --------------------------------------------------------------------------
# 渲染与入口
# --------------------------------------------------------------------------


def render(report: dict) -> str:
    lines = [
        f"套件 {report['suite']}   运行于 {report['run_at']}",
        "",
        f"  题量 {report['counts']['authored']}"
        f"   作废 {report['counts']['voided']}"
        f"   计分分母 {report['counts']['scored_denominator']}"
        f"   未执行 {report['counts']['not_run']}",
        f"  通过 {report['counts']['passed']}   失败 {report['counts']['failed']}",
        f"  构造错误作废率 {report['void_ratio']:.1%}"
        f"（上限 {MAX_VOID_RATIO:.0%}，"
        f"{'未超限' if report['void_ratio_within_limit'] else '**已超限，整批判为构造失败**'}）",
        "",
        "按类别：",
    ]
    for cat, v in report["by_category"].items():
        lines.append(
            f"  {cat}  {v['status']:<8} 题量 {v['authored']}  存活 {v['surviving']}"
            f"  已执行 {v['executed']}  通过 {v['passed']}"
        )
    g = report["c2_refusal_gate"]
    lines += [
        "",
        f"C2 拒答准确率：{g['accuracy']}   门成立：{g['gate_holds']}   {g['gate_note']}",
        "",
        "§6 指标：",
    ]
    for k, v in report["metrics"].items():
        lines.append(f"  {k:<12} {v}")
    if report.get("evidence_scope_notes"):
        # ⚠️ 收窄必须出现在**人读报告**里。只写进 JSON 等于没写：
        #    读报告的人看到的是 `15/15（100.0%）`，看不到它是怎么数出来的。
        lines += ["", "证据链键集收窄（逐条，不静默）："]
        for n in report["evidence_scope_notes"]:
            lines.append(
                f"  {n['case']:<12} 阶段 {n['stage']}"
                f"   不适用的键 {'、'.join(n['dropped'])}   {n['why']}"
            )
    if report.get("attribution_hint_comparison"):
        lines += [
            "",
            "失败题的归因 vs 出题时的 attribution_hint（**事后对照，不是准确率**）：",
        ]
        for row in report["attribution_hint_comparison"]:
            lines.append(f"  {row['case']:<12} 实际 {' + '.join(row['actual_layers'])}"
                         f"   判据 {row['basis']}")
            lines.append(f"               出题时预判 {row['hint'] or '（这道题没写 hint）'}")
        lines.append("  ⚠️ 不一致**不是**失败信号：hint 是出题时预判的陷阱，"
                     "实际归因是这一次真实的失败点。")
    if report.get("layer_usage"):
        zero = [k for k, v in report["layer_usage"].items() if not v]
        lines += ["", "各层实际吃到的失败题数："]
        lines.append("  " + "   ".join(f"{k} {v}" for k, v in report["layer_usage"].items()))
        unreachable = set(report.get("unreachable_layers") or [])
        empty_but_reachable = [k for k in zero if k not in unreachable]
        if empty_but_reachable:
            lines.append(
                "  · 本批零产出（但结构上产得出来）：" + "、".join(empty_but_reachable)
            )
        if unreachable:
            lines.append(
                "  ⚠️ **结构上不可达**：" + "、".join(sorted(unreachable))
                + " —— 当前实现里没有任何一条路能产出它。"
                "这是 L-25 那种死抽象的形状，再跑一万批也不会有。"
            )
    if report["unattributed_failures"]:
        lines += [
            "",
            "🔴 **AC-08 不满足** —— 下列失败题没有归因（「不允许未知」是规则，不是统计目标）：",
        ]
        for cid in report["unattributed_failures"]:
            lines.append(f"  {cid}")
    if report["voided_cases"]:
        lines += ["", "作废题（移出分母，公开列出）："]
        for c in report["voided_cases"]:
            lines.append(f"  {c['id']}  {c['detail']}")
    lines += ["", "逐题："]
    for r in report["results"]:
        mark = f"  {r['status']:<8} {r['id']:<12} {r['detail']}"
        if r["attribution"]:
            mark += f"   [归因 {' + '.join(r['attribution'])}]"
        lines.append(mark)
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="eval.run", description="按冻结套件运行评测")
    ap.add_argument("--suite", required=True, help="套件目录名，如 frozen-01")
    ap.add_argument("--category", choices=CATEGORIES, default=None)
    ap.add_argument("--report", default=None, help="报告输出目录，默认 eval/runs/")
    args = ap.parse_args(argv)

    suite_dir = EVAL_ROOT / args.suite
    if not suite_dir.is_dir():
        print(f"套件目录不存在：{suite_dir}", file=sys.stderr)
        return 2

    ok, problems = verify_freeze(suite_dir)
    if not ok:
        # fail-closed：一道题都不执行。这是 D-012 的物理保障。
        print("冻结校验未通过，拒绝运行评测：", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    report = run_suite(suite_dir, args.category)
    print(render(report))

    out_dir = Path(args.report) if args.report else (EVAL_ROOT / "runs")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = report["run_at"].replace(":", "").replace("-", "")
    out_path = out_dir / f"{report['suite']}-{stamp}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n报告已写入 {out_path}")

    if report["unattributed_failures"]:
        # `AC-08` 是**保证类**标准（`PROJECT_SPEC` §9.1）：一道未归因的失败即不满足。
        # 用一个**与「有失败题」不同的**退出码 —— 两件事混成同一个 1，
        # CI 里就分不出「系统答错了」和「评测自己坏了」。
        print(
            "AC-08 不满足：以下失败题没有归因 —— "
            + "、".join(report["unattributed_failures"]),
            file=sys.stderr,
        )
        return 3
    if not report["void_ratio_within_limit"]:
        return 1
    if report["counts"]["failed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
