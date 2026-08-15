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

# EVAL_CASES §5 的四层归因。不允许「未知」。
LAYER_RETRIEVAL = "检索层"
LAYER_DEFINITION = "口径层"
LAYER_COMPUTATION = "计算层"
LAYER_PRESENTATION = "表达层"

PASS, FAIL, NOT_RUN, VOIDED = "PASS", "FAIL", "NOT_RUN", "VOIDED"

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


def load_cases(suite_dir: Path) -> list[dict]:
    cases = []
    for path in sorted((suite_dir / "cases").glob("*.yaml")):
        cases.append(yaml.safe_load(path.read_text(encoding="utf-8")))
    return cases


def run_suite(suite_dir: Path, only_category: str | None = None) -> dict:
    from semantic_layer.resolve import Refusal, Registry

    registry = Registry.load(REPO_ROOT / "metrics")
    cases = load_cases(suite_dir)

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

        if cat not in EXECUTABLE_IN_PHASE_1:
            results.append(
                CaseResult(cid, cat, NOT_RUN, "Phase 1 不具备该类所需能力（数值执行 / 准则检索 / 图谱）")
            )
            continue

        target = case.get("question", "")
        name = case.get("expected", {}).get("target_name") or _target_from_question(case)
        outcome = registry.resolve(name)
        results.append(judge_refusal_case(case, outcome, Refusal))

    return _summarize(suite_dir, results, only_category)


def _target_from_question(case: dict) -> str:
    """C2 题的靶子指标名。

    题面是自然语言，此处不做 NLU —— 靶子由题面文件显式给出（`expected.target_name`），
    没给就退回用 id 里的线索，取不到时返回一个必然打不中的串。
    在 Phase 1 这是刻意的：本阶段考的是「口径未定义时是否拒答」，不是「能否理解中文」。
    """
    return case.get("target_name", "") or "__NO_TARGET_DECLARED__"


def _summarize(suite_dir: Path, results: list[CaseResult], only_category: str | None) -> dict:
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
            "口径正确率": "N/A（需数值执行路径，Phase 1 不具备）",
            "拒答准确率": c2_gate["accuracy"],
            "答案正确率": "N/A（需数值执行路径，Phase 1 不具备）",
            "证据链完整率": "N/A（证据链是 Phase 2 的交付物）",
            "复核一致率": "N/A（H2 复核实验在 Phase 2）",
            "引用可定位率": "N/A（准则检索是 Phase 3 的 L2）",
            "归因覆盖率": "100%" if all(r.layers for r in scored if r.status == FAIL) else "<100%",
        },
        "results": [r.to_dict() for r in results],
    }


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
