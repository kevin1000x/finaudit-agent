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
from eval.run import MAX_VOID_RATIO, verify_freeze  # noqa: E402

__all__ = [
    "judge_case",
    "run_suite",
    "render",
    "main",
    "void_record",
    "VOIDED_FILENAME",
    "EXIT_SUITE_VOIDED",
]

#: 整批作废的标记文件。**存在即不许报分数。**
VOIDED_FILENAME = "VOIDED.yaml"

#: 整批作废时的退出码。**与「有题没过」（1）和「套件不存在」（2）分开** ——
#: 三件事不是一回事，而把它们挤进同一个非零码，下一个读 CI 日志的人分不出来。
EXIT_SUITE_VOIDED = 3


def void_record(suite_dir: Path):
    """这套题整批作废了没有。返回作废记录，或 `None`。

    🔴 **为什么是一个文件而不是 `FREEZE.md` 里的一句话**：`D-012` 修订三说
    「整批作废重建，且必须公开记录作废率」。写在散文里的作废**挡不住下一次
    `python -m eval.verify_run --suite frozen-03` 打出一行分数** ——
    而那行分数会被引用。⇒ 作废必须是机器读得到的。
    """
    path = Path(suite_dir) / VOIDED_FILENAME
    if not path.is_file():
        return None
    got = yaml.safe_load(path.read_text(encoding="utf-8"))
    return got if isinstance(got, dict) else {}


def _normalize(text) -> str:
    return " ".join(str(text or "").split())


def judge_case(case: dict, report) -> dict:
    """一道题的判定。**六样都要对**：读成什么、切成几条、每条判什么、
    抽出来的那个数、该不该承接、读成提问时答出了什么。

    🔴 **切分本身就是被判分的一部分**（`D-041` §5 的连带缓解）。
    只判最终五态而不判切分，等于允许「把一段话切错、但每一片碰巧判对」
    拿满分 —— 而那种报告在读者眼里是错的。

    ## 后三样是 `N-86` 补的，补的是独立复核实测出来的三处盲区

    | 原先判不到 | 实测 | 现在的判据 |
    |---|---|---|
    | `read_as: QUESTION` 那几题**不判答案内容** | 把 `V-001`（速动比率 3.6704）的报告换成**万华化学的资产负债率 0.5465**，照样 `passed: True` | `expected.answer.metric_id` / `.value` |
    | **抽出来的那个数**不进判分 | 「第 4 季度速动比率 3.67」曾抽出季度序号 `4` —— 切分对、判定"对"、抽的数完全是另一个东西 | `expected.claims[i].stated_text` |
    | 没有一道题断言「这一条**不该**承接」 | `inherited` 只有正向判据，而**错误承接是本层最危险的失效模式**（三个 P0 全是它） | `claims[i].inherited: false` / `claims[i].not_inherited` |

    ⚠️ 三者都是**题面声明了才判**。不声明不判 —— 否则 14 道老题会一起变成
    「缺字段」，那是把判分器的扩张伪装成题目的失败。
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
            # 抽出来的那个数（`N-86` ②）。**声明了就必须逐字相同。**
            # 判「一致」而抽的是另一个数，那个「一致」是巧合不是核查。
            if "stated_text" in want:
                要的数 = _normalize(want.get("stated_text"))
                得到的数 = _normalize(None if got.stated is None else got.stated.text)
                if 要的数 != 得到的数:
                    问题.append(
                        f"第 {i + 1} 条抽出来的数：要「{要的数}」，得到「{得到的数}」"
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
            # 🔴 **反方向（`N-86` ③）：题面可以声明「这一条一个字都不许承接」。**
            #    `inherited: false` 与「没写 inherited」不是一回事 —— 后者不判。
            elif want.get("inherited") is False and got.inherited:
                问题.append(
                    f"第 {i + 1} 条：题面要求一个字都不许承接，实际承接了「{got.inherited}」"
                )

            # 🔴 **更要紧的那一半：某一维不许承接。**
            #    「万华化学的资产负债率 62%」接在一句茅台后面时，**期间该承、主体绝不能承** ——
            #    承错了报告会拿茅台的数去否定一条关于万华的声明，还印一句「承自前一句」当交代。
            for 不许 in want.get("not_inherited") or []:
                if got.inherited and str(不许) in got.inherited:
                    问题.append(
                        f"第 {i + 1} 条：「{不许}」不许被承接，而实际承接的是"
                        f"「{got.inherited}」"
                    )

    # 读成提问时，题面可以声明这一问该不该被拒答。
    if 要的 == "QUESTION" and "refused" in expected and report.answer is not None:
        if bool(report.answer.refused) != bool(expected["refused"]):
            问题.append(
                f"拒答与否：要 refused={expected['refused']}，"
                f"得到 refused={report.answer.refused}"
            )

    # 🔴 **读成提问时的答案内容（`N-86` ①）。**
    #    `D-041` §1 的核心主张是「问答能力就在核查里面」，而这套题原先对它
    #    只验了「拒没拒答」—— 实测把速动比率的报告换成万华化学的资产负债率，
    #    照样满分。期望里的取值出自 `COMPUTED-VALUES.md`（已签署的手算复核），
    #    **不是抄系统输出**。
    要的答案 = expected.get("answer")
    if 要的答案 and report.answer is not None:
        if "metric_id" in 要的答案:
            if str(report.answer.metric_id) != str(要的答案["metric_id"]):
                问题.append(
                    f"答案的指标：要 {要的答案['metric_id']}，得到 {report.answer.metric_id}"
                )
        if "value" in 要的答案:
            if str(report.answer.value) != str(要的答案["value"]):
                问题.append(
                    f"答案的取值：要 {要的答案['value']}，得到 {report.answer.value}"
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
    voided: list = []
    for path in sorted((suite_dir / "cases").glob("*.yaml")):
        case = yaml.safe_load(path.read_text(encoding="utf-8"))
        # §2.2 构造错误作废：移出分母，**但必须单独列出，不静默消失**。
        # 与 `run.py` 同一个键名、同一条纪律（`D-012` 修订二）。
        if str(case.get("voided", "")).strip():
            voided.append({"id": case.get("id"), "reason": str(case["voided"]).strip()})
            continue
        report = read_input(
            _normalize(case.get("conclusion")),
            registry,
            source=source,
            ask_model=asker,
        )
        results.append(judge_case(case, report))

    passed = sum(1 for r in results if r["passed"])
    authored = len(results) + len(voided)
    void_ratio = (len(voided) / authored) if authored else 0.0
    return {
        "suite": suite_dir.name,
        "run_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        # §2.2：作废率上限 10%，超了整批判为构造失败（`D-012` 修订三）。
        # 🔴 这一位此前**只在 `run.py` 里有**，核查套件这一侧完全没有 ——
        # 而 `N-84` 第一次用到它时，作废率就是 3/14 = 21.4%。
        "void_ratio": round(void_ratio, 4),
        "void_ratio_within_limit": void_ratio <= MAX_VOID_RATIO,
        "voided_cases": voided,
        # 🔴 `N-78` 的直接产物：这一跑到底接没接上模型，写在报告里。
        # 接不上不是错误，**把接不上的分数报成线上的分数才是**。
        "model_wired": asker is not None and not asker.error,
        "model_note": None if asker is None else (str(asker.error) or None),
        "counts": {
            "authored": authored,
            "voided": len(voided),
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
        f"共出题 {report['counts']['authored']} 题（作废 {report['counts']['voided']}）："
        f"计分 {report['counts']['total']}，"
        f"通过 {report['counts']['passed']}，未通过 {report['counts']['failed']}",
        "",
    ]
    for r in report["results"]:
        mark = "PASS" if r["passed"] else "FAIL"
        L.append(f"[{mark}] {r['id']}（{r['category']}）　{r['read_as']}　{r['verdicts']}")
        for p in r["problems"]:
            L.append(f"        · {p}")
    if report["voided_cases"]:
        L += ["", f"作废（移出分母，构造错误作废率 {report['void_ratio']:.1%}）："]
        for v in report["voided_cases"]:
            L.append(f"[VOID] {v['id']}　{v['reason']}")
        if not report["void_ratio_within_limit"]:
            L += [
                "",
                f"🔴 构造错误作废率 {report['void_ratio']:.1%} > "
                f"{MAX_VOID_RATIO:.0%}（`D-012` 修订三）⇒ **本批次判为构造失败，"
                "整批作废重建**。上面这个分数不许引用。",
            ]
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

    # 🔴 **整批作废的套件不许报分数**，连一行都不许 —— 那行分数会被引用。
    #    冻结校验排在它前面：套件作废了，文件被动过这件事照样要说。
    作废 = void_record(suite_dir)
    if 作废 is not None:
        print(f"套件 {suite_dir.name} **已整批作废**，拒绝判分（`D-012` 修订三）：")
        for key in ("voided_at", "reason", "void_ratio", "decision", "replaced_by"):
            if 作废.get(key):
                print(f"  {key}: {作废[key]}")
        for cid, why in (作废.get("cases") or {}).items():
            print(f"  - {cid}：{why}")
        print(f"\n详见 {suite_dir / VOIDED_FILENAME} 与 {suite_dir / 'FREEZE.md'}")
        return EXIT_SUITE_VOIDED

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

    # 作废率超限与「有题没过」同样非零 —— 一个粉饰过的满分不比一道红题好。
    return 1 if (report["counts"]["failed"] or not report["void_ratio_within_limit"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
