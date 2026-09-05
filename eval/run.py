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

# EVAL_CASES §5 的四层归因。不允许「未知」。
LAYER_RETRIEVAL = "检索层"
LAYER_DEFINITION = "口径层"
LAYER_COMPUTATION = "计算层"
LAYER_PRESENTATION = "表达层"

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

    def to_dict(self) -> dict:
        return {
            "id": self.case_id,
            "category": self.category,
            "status": self.status,
            "detail": self.detail,
            "attribution": self.layers,
        }


def judge_refusal_case(case: dict, outcome, refusal_cls) -> CaseResult:
    """C2 类判定，严格按 EVAL_CASES §3.2。

    拒答且理由码正确 → PASS
    拒答但理由码不符 → FAIL（口径层）
    强行给出答案     → FAIL（口径层），**即使数值碰巧正确也算失败**
    """
    cid, cat = case["id"], case["category"]
    want_code = case.get("judging", {}).get("refusal_code") or case.get("expected", {}).get(
        "refusal_code"
    )

    if not isinstance(outcome, refusal_cls):
        return CaseResult(
            cid, cat, FAIL,
            f"期望拒答，实际返回了指标定义 {getattr(outcome, 'metric_id', '?')!r}。"
            "按 §3.2，强行作答即使数值碰巧正确也算失败。",
            [LAYER_DEFINITION],
        )

    got_code = outcome.code.name
    if want_code and got_code != want_code:
        return CaseResult(
            cid, cat, FAIL,
            f"拒答理由码不符：期望 {want_code}，实际 {got_code}",
            [LAYER_DEFINITION],
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
        return CaseResult(
            cid, cat, FAIL,
            f"期望数值 {want}，实际拒答（{answer.refusal['code']}）：{answer.refusal['detail'][:80]}",
            [LAYER_DEFINITION],
        )
    if answer.value is None:
        return CaseResult(cid, cat, FAIL, "既没拒答也没给出数值", [LAYER_COMPUTATION])

    if isinstance(want, (dict, list, set, tuple)):
        # `Q-C3-004` 的标准答案是**两期的一个映射**。本路径只产单期标量 ——
        # 如实判 FAIL 并说清楚，**不要在这里 `Decimal(str(dict))` 崩掉**：
        # 崩掉会让整批评测终止，而一道答不了的题不该拖垮另外十九道。
        return CaseResult(
            cid, cat, FAIL,
            f"标准答案是集合/多期结构（{type(want).__name__}），本路径只产单期标量",
            [LAYER_COMPUTATION],
        )

    tol = exp.get("tolerance") or {}
    abs_tol = Decimal(str(tol.get("abs", 0)))
    rel_tol = Decimal(str(tol.get("rel", 0)))
    got, target = Decimal(str(answer.value)), Decimal(str(want))
    diff = abs(got - target)
    ok = diff <= abs_tol or (target != 0 and diff / abs(target) <= rel_tol)
    if not ok:
        return CaseResult(
            cid, cat, FAIL,
            f"数值不在容差内：算出 {got}，标准答案 {target}，差 {diff}",
            [LAYER_COMPUTATION],
        )

    want_metric = exp.get("metric_id")
    if want_metric and answer.metric_id != want_metric:
        return CaseResult(
            cid, cat, FAIL,
            f"数值对了但口径不对：用的是 {answer.metric_id}，应为 {want_metric}",
            [LAYER_DEFINITION],
        )
    want_version = exp.get("metric_version")
    if want_version is not None and answer.metric_version != want_version:
        return CaseResult(
            cid, cat, FAIL,
            f"口径版本不符：用的是 {answer.metric_version}，应为 {want_version}",
            [LAYER_DEFINITION],
        )
    return CaseResult(cid, cat, PASS, f"数值 {got} 在容差内，口径与版本均相符")


def load_cases(suite_dir: Path) -> list[dict]:
    cases = []
    for path in sorted((suite_dir / "cases").glob("*.yaml")):
        cases.append(yaml.safe_load(path.read_text(encoding="utf-8")))
    return cases


def run_suite(suite_dir: Path, only_category: str | None = None) -> dict:
    """系统臂。**Phase 2 起走 `src/agent/` 的完整问答路径。**

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

    return _summarize(
        suite_dir, results, only_category, answers, evidence_gap_by_case, evidence_notes
    )


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
            "复核一致率": "N/A（H2 复核实验在 02-03）",
            "引用可定位率": "N/A（准则检索是 Phase 3 的 L2）",
            "归因覆盖率": _rate(*_attribution_hits(scored)),
        },
        # ⚠️ 收窄要**逐条摆出来**，不静默。见 `run_suite` 里那段注释。
        "evidence_scope_notes": list(evidence_notes or []),
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

    if not report["void_ratio_within_limit"]:
        return 1
    if report["counts"]["failed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
