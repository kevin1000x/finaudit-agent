"""按冻结套件运行**核查层**评测（`frozen-03`，`D-041` §5）。

## 为什么它单独一个文件，而不是并进 `eval/run.py`

`run.py` 打的是 `answer_question`，那是**下面那半**；`frozen-01` / `frozen-02`
的分数全建在它上面，而 `D-012` 不许动已冻结的东西。**在它里面加一条分支
去跑另一种题面，是拿评测臂脚下的地面换方便。**

⇒ 分开一个入口，但**冻结校验用的是同一份 `verify_freeze()`**（从 `run.py` 导入，
不复制）—— `D-012` 的物理保障只能有一个实现，两份迟早会漂。

## 它防的是 `N-64` / `N-78` 那个形状

两次栽在同一件事上：**生产接了什么，评测就得接什么**。

- `N-64`：生产路径没接模型；
- `N-78`：评测臂不传 `ask_model`，于是 `frozen-01` 的分数是「关掉说法归一之后」的分数。

⇒ 本运行器**走 `service.api` 那一套数据源与模型装配**，不自己造一份，
并把「这一跑到底接没接上模型」写进报告（`model_wired`）。
没接上就明说，**不把一次离线跑的分数报成线上的分数**。

用法：
    python -m eval.verify_run --suite frozen-03
    python -m eval.verify_run --suite frozen-03 --report eval/runs/
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

EVAL_ROOT = Path(__file__).resolve().parent
REPO_ROOT = EVAL_ROOT.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from eval.freeze import _check_closed_verdicts  # noqa: E402
from eval.run import verify_freeze  # noqa: E402

__all__ = ["judge_case", "run_suite", "render", "main"]


def _normalize(text) -> str:
    return " ".join(str(text or "").split())


def judge_case(case: dict, report) -> dict:
    """一道题的判定。**三样都要对**：读成什么、切成几条、每条判什么。

    🔴 **切分本身就是被判分的一部分**（`D-041` §5 的连带缓解）。
    只判最终五态而不判切分，等于允许「把一段话切错、但每一片碰巧判对」
    拿满分 —— 而那种报告在读者眼里是错的。
    """
    expected = case.get("expected") or {}
    问题: list = []

    要的 = str(expected.get("read_as"))
    得到 = report.read_as.name
    if 得到 != 要的:
        问题.append(f"读成什么：要 {要的}，得到 {得到}")

    要的切分 = [_normalize(c.get("text")) for c in (expected.get("claims") or [])]
    得到切分 = [_normalize(c.text) for c in report.claims]
    if 要的切分 != 得到切分:
        问题.append(f"切分：要 {要的切分}，得到 {得到切分}")
    else:
        # 切分一致才逐条比判定 —— 切分都不一样时，逐条比出来的是噪音。
        for i, want in enumerate(expected.get("claims") or []):
            got = report.claims[i]
            if got.verdict.name != str(want.get("verdict")):
                问题.append(
                    f"第 {i + 1} 条判定：要 {want.get('verdict')}，得到 {got.verdict.name}"
                )
            # 承接上下文是题面可以声明的一项。声明了就必须真的承接到那一对。
            要承接 = want.get("inherited")
            if 要承接:
                if not got.inherited:
                    问题.append(f"第 {i + 1} 条：题面要求承接 {要承接}，实际没有承接")
                else:
                    code, year = str(要承接).split("/")
                    if code not in got.inherited or year not in got.inherited:
                        问题.append(
                            f"第 {i + 1} 条：要承接 {要承接}，实际是「{got.inherited}」"
                        )

    # 读成提问时，题面可以声明这一问该不该被拒答。
    if 要的 == "QUESTION" and "refused" in expected and report.answer is not None:
        if bool(report.answer.refused) != bool(expected["refused"]):
            问题.append(
                f"拒答与否：要 refused={expected['refused']}，"
                f"得到 refused={report.answer.refused}"
            )

    return {
        "id": case.get("id"),
        "category": case.get("category"),
        "passed": not 问题,
        "problems": 问题,
        "read_as": 得到,
        "verdicts": [c.verdict.name for c in report.claims],
        "segmentation": 得到切分,
    }


def run_suite(suite_dir: Path) -> dict:
    """跑一整套。**数据源与模型装配走 `service.api`，不自己造一份。**"""
    from agent.verify import read_input
    from service import api

    registry = api._registry()
    source = api._pick_source()
    provider = api._provider()
    asker = None
    if provider is not None:
        from service import model

        asker = model.Asker(provider, api._aliases())

    results: list = []
    for path in sorted((suite_dir / "cases").glob("*.yaml")):
        case = yaml.safe_load(path.read_text(encoding="utf-8"))
        report = read_input(
            _normalize(case.get("conclusion")),
            registry,
            source=source,
            ask_model=asker,
        )
        results.append(judge_case(case, report))

    passed = sum(1 for r in results if r["passed"])
    return {
        "suite": suite_dir.name,
        "run_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        # 🔴 `N-78` 的直接产物：这一跑到底接没接上模型，写在报告里。
        # 接不上不是错误，**把接不上的分数报成线上的分数才是**。
        "model_wired": asker is not None and not asker.error,
        "model_note": None if asker is None else (str(asker.error) or None),
        "counts": {
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
        },
        "results": results,
    }


def render(report: dict) -> str:
    L = [
        f"核查层评测 —— {report['suite']} @ {report['run_at']}",
        "",
        f"接上模型：{'是' if report['model_wired'] else '否'}"
        + (f"（{report['model_note']}）" if report.get("model_note") else "")
        + "　—— 没接上时，下面的分数是「关掉说法归一之后」的分数，不是线上的分数",
        "",
        f"共 {report['counts']['total']} 题："
        f"通过 {report['counts']['passed']}，未通过 {report['counts']['failed']}",
        "",
    ]
    for r in report["results"]:
        mark = "PASS" if r["passed"] else "FAIL"
        L.append(f"[{mark}] {r['id']}（{r['category']}）　{r['read_as']}　{r['verdicts']}")
        for p in r["problems"]:
            L.append(f"        · {p}")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="eval.verify_run", description="按冻结套件运行核查层评测")
    ap.add_argument("--suite", required=True, help="套件目录名，如 frozen-03")
    ap.add_argument("--report", default=None, help="报告输出目录，默认 eval/runs/")
    args = ap.parse_args(argv)

    suite_dir = EVAL_ROOT / args.suite
    if not suite_dir.is_dir():
        print(f"套件目录不存在：{suite_dir}", file=sys.stderr)
        return 2

    _ok, problems = verify_freeze(suite_dir)
    # 🔴 **封闭集在这里也要验一次，不能只在冻结时验。**
    #    独立复核（2026-09-11）指出：冻结之后，实现单方面加一个第六态，
    #    跑评测不会红 —— 因为 `verify_freeze` 只校哈希。
    #    而 `frozen-03` 的全部意义就是给这一层装评测。
    problems = list(problems) + _check_closed_verdicts()
    if problems:
        # fail-closed：一道题都不执行。与 `run.py` 同一条纪律，同一份实现。
        print("冻结校验未通过，拒绝运行评测：", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    report = run_suite(suite_dir)
    print(render(report))

    out_dir = Path(args.report) if args.report else (EVAL_ROOT / "runs")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = report["run_at"].replace(":", "").replace("-", "")
    out_path = out_dir / f"{report['suite']}-{stamp}.json"
    out_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n报告已写入 {out_path}")

    return 1 if report["counts"]["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
