"""H2 复核实验的器械（`02-03`，`EVAL_CASES` §4，`AC-06` / `SC-2` / `SC-3`）。

`EVAL_CASES` §4 第一句就写着：**「这是本项目最重要、也最容易被跳过的评测」**。
本模块做的是让它**能被做**、且做完之后**结论站得住**的三件事：

1. **题包**：复核者手上那一页。正文逐字就是 `agent.answer.render_answer()` 的输出 ——
   `D-032` 定的就是这条（「`AC-06` 的复核者读的就是这个」）。**不另写一版给复核者的排版**：
   另写一版就等于测了一个不会上线的东西。
2. **空白答卷** + 回填后算数。
3. **`D-037` 的三条强制标注**，缺一条就不给结论。

## 本模块不做的事

**它不复核。** `EVAL_CASES` §4.1 第 2 步要的是「有审计或财务背景的复核者」，
而 `N-20` 立过同款判据：**执行者代答无效**。器械做完就停。

## 为什么题包必须来自某一次具体运行

复核者看的那一页，和拿来跟他比对的 `PASS`/`FAIL`，**必须同源**。
所以这里走 `run_suite(..., collect=...)` 拿那一次真实产出的 `Answer`，
而不是「用同样的输入再算一遍」。今天两者等价（意图解析之后全程确定性），
但那是一个会悄悄失效的前提。

## 不泄题：探针查什么、以及**刻意不查什么**

见 `leak_probes` 的 docstring。这一段是本模块最容易被「顺手补全」改坏的地方。
"""

from __future__ import annotations

import json
import random
import sys
from dataclasses import dataclass
from pathlib import Path

EVAL_ROOT = Path(__file__).resolve().parent
REPO_ROOT = EVAL_ROOT.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from .run import FAIL, PASS, load_cases, run_suite  # noqa: E402

__all__ = [
    "REQUIRED_ANNOTATIONS",
    "VERDICTS",
    "Packet",
    "blank_sheet",
    "build_packets",
    "keymap",
    "leak_probes",
    "no_leak_problems",
    "render_packets",
    "score",
]

#: 复核者的取值域（`EVAL_CASES` §4.1 第 3 步逐字）。
VERDICTS = ("对", "错", "无法判断")

#: `D-037` / `EVAL_CASES` §4.1.1 强制要求的标注。**缺一项即视为未按 §4.1 执行**，
#: 于是 `score()` 拒绝给结论 —— 这不是提醒，是门。
REQUIRED_ANNOTATIONS = (
    "sampling",                    # 「普查」，不是「随机抽样」
    "w",                           # 错题数的实际值
    "w_ge_5_satisfied",            # `≥5 题答错` 是否满足
    "resolution_floor_on_wrong",   # 错题子集上的分辨率下限 1/W
    "limitations",                 # 指向 `02-03-PLAN.md` 那三条限定，不复述
    # `N-75`（2026-09-09 新增）：这份题包是不是**盲出**的 ——
    # 出包时执行者有没有读过、报过跑分结果。不是盲出的，
    # 复核者可能已经知道答案，那时一致率这个数**不能当成 AC-06 的读数**。
    # 缺 `BUILD.json` ⇒ 记「未声明」，**不记「是」** —— fail-closed。
    "blind_build",
)

#: §4.2 的三档。**数值一个不动**（`D-037` 只改了「样本怎么取」与「报告说什么」）。
GATE_PASS, GATE_PARTIAL, GATE_FAIL = 0.80, 0.60, 0.0
#: §4.3 的反向检验：「无法判断」占比超过它，即使一致率达标也要补齐重测。
UNDECIDABLE_LIMIT = 0.20

_LIMITATIONS_REF = (
    ".planning/phases/02-execution-web/02-03-PLAN.md 的 <context> 三条限定"
    "（只有 5/15 是数字题；错题全是拒答形态；复核者不独立于本项目）"
)


@dataclass(frozen=True)
class Packet:
    """复核者拿到的一题。**没有一个字段来自题面的 `expected` / `judging`。**"""

    anon_id: str
    case_id: str
    body: str


# --------------------------------------------------------------------------
# 题包
# --------------------------------------------------------------------------


def build_packets(suite_dir: Path, seed: int, blind: bool = False):
    """跑一次评测，把**可计分**的每一题做成一个题包。返回 `(packets, report)`。

    ## `blind=True`：**报告对象不出这个函数**（`N-75`）

    2026-09-09 实际栽过的一次：出题包必须先有跑分结果，而
    `EVAL_CASES` §4.1 的「`W ≥ 5`」又要操作者裁 ⇒ 执行者跑了 `eval.run`、
    读了结果、把「21/21 全对」告诉了复核者本人。复核者知道答案全对之后，
    **他每判一个「对」都不含信息**，§4.2 一致率那一读数当场作废。

    `blind=True` 时返回 `(packets, None)` —— 调用方**拿不到** `report`，
    因此**印不出** `W`、印不出逐题结果。这不是提醒，是把那条路封掉。

    🔴 **它封不住的那条路，如实写在这里**：`python -m eval.run --suite X`
    仍然会把分布打在屏幕上。本函数管不着别的进程。
    ⇒ 真正的规矩是**「出包 → 复核 → 才跑、才报」**，`--blind` 只让这条规矩
    在这一个入口上**做得到**，做不到「别人绕不过」。
    ⚠️ 别把它当成保证。判据写在 `N-75`。

    ## 为什么盲出题包在信息上是够的

    §4.1 那句「≥5 题答错」约束的是**抽样**；而这里是**普查**（`D-037`），
    一道不挑 ⇒ 出包阶段根本不需要知道 `W`。`W` 只在**算数**时才需要
    （§4.2 附注要求报错题子集的原始计数），那时复核已经做完了。

    **普查，不抽样**（`D-037` / §4.1.1）：`status` 落在 `PASS`/`FAIL` 的题一道不落，
    挑题的余地在这里就不存在。`NOT_RUN`（C4 准则检索 / C5 图谱）没有答案可复核，
    进题包等于给复核者一页空白，所以不进。

    `seed` 只决定**定序**。不打乱的话 frozen-01 里 `Q-C2-*` 连着四道全是拒答，
    读到第三道就能猜出这一段的形状。种子记在 `keymap()` 里，可复现。
    """
    from semantic_layer.__main__ import _flag_descriptions
    from semantic_layer.resolve import Registry

    from agent.answer import render_answer

    answers: dict = {}
    report = run_suite(suite_dir, None, collect=answers)

    registry = Registry.load(REPO_ROOT / "metrics")
    flag_desc = _flag_descriptions(REPO_ROOT / "metrics")

    scored = [r["id"] for r in report["results"] if r["status"] in (PASS, FAIL)]
    missing = [cid for cid in scored if cid not in answers]
    if missing:
        # fail-closed：拿不到某一题的答案就整批不出题包。
        # 少一题而照样发出去，复核者那边看不出来，分母却已经变了。
        raise ValueError("这些已计分的题没有对应的答案对象：" + "、".join(missing))

    ordered = list(scored)
    random.Random(seed).shuffle(ordered)

    packets = []
    for i, cid in enumerate(ordered, start=1):
        ans = answers[cid]
        defn = registry.definitions.get(ans.metric_id) if ans.metric_id else None
        packets.append(
            Packet(
                anon_id="H2-%02d" % i,
                case_id=cid,
                body=render_answer(ans, defn, flag_desc),
            )
        )

    problems = no_leak_problems(packets, report, suite_dir)
    if problems:
        # 泄题的题包不许流出去。这道门比「测试红了」更靠前：
        # 测试守的是代码，这一句守的是**这一次真的要交出去的那份文件**。
        raise ValueError("题包泄题，拒绝产出：\n  " + "\n  ".join(problems))
    # 🔴 **盲模式下报告到此为止。** 不是「调用方自觉别看」——
    # 是它手上根本没有那个对象，于是印不出 W，也印不出逐题结果。
    return packets, (None if blind else report)


def render_packets(packets) -> str:
    """复核者拿到的那一份。**除了匿名号与正文，什么都不加。**"""
    L = [
        "H2 复核题包",
        "",
        "每题限时 5 分钟，只读这一页，判 `对 / 错 / 无法判断`，填进 answer-sheet.yaml。",
        "「对」= 你认为系统这次给出的结果是对的；拒答也算一种结果，判的是「这次拒答对不对」。",
        "「无法判断」= 这一页的信息不足以让你下结论 —— 它不是「不确定就选它」，",
        "它本身是一个被单独统计的读数（`EVAL_CASES` §4.3）。",
        "",
    ]
    for p in packets:
        L += ["=" * 68, p.anon_id, "=" * 68, "", p.body, ""]
    return "\n".join(L)


def keymap(packets, seed: int) -> dict:
    """匿名号 → 原编号。**单独一份文件，复核者不拿到。**"""
    return {
        "seed": seed,
        "map": {p.anon_id: p.case_id for p in packets},
    }


# --------------------------------------------------------------------------
# 不泄题
# --------------------------------------------------------------------------


def leak_probes(case: dict, result: dict) -> list:
    """这一题**不许出现在题包里**的字符串。

    收的是两类，共同点是：**它们只存在于标准答案或判定输出里，
    系统自己的答案在任何情况下都产不出它们。**

    1. 题面的 `rationale` / `attribution_hint` —— 自由散文，写着正解和陷阱在哪。
    2. 本次运行的 `status` / `detail` / `attribution` / `attribution_basis` ——
       判定的产物。

    ⚠️ **刻意不收 `expected.value` / `expected.metric_id` / `judging.refusal_code`。**
    两个理由，第二个更要紧：

    - 系统**答对**的时候，它自己的输出就等于这几个值 ⇒ 必然误报。
    - 更糟的是**命中与否本身就是答案**：一个「因为系统答对了所以变红」的检查，
      等于把判定结果编码进了门禁，还会诱使人去改题包来消红。

    这几项由 `tests/test_h2.py` 的**哨兵测试**结构性地覆盖：
    题面里放一串构造上不可能被算出来的哨兵，它出现在题包里就只可能是抄过去的。
    那条测试连 `expected` / `judging` / `must_not_resolve_to` 一起覆盖，**且没有误报面**。
    """
    # ⚠️ `rationale` 在题面里是写在 **`expected:` 底下**的（frozen-01 二十份都是），
    #    只读顶层会拿到 `None` ⇒ 这条探针整个空转。
    #    2026-09-05 第一版就是这么写的，靠 `test_不泄题这条检查真的会红` 那条反空转抓出来的。
    expected = case.get("expected") or {}
    probes = []
    for source, key in (
        (case, "rationale"),
        (expected, "rationale"),
        (case, "attribution_hint"),
        (expected, "attribution_hint"),
    ):
        v = source.get(key) if isinstance(source, dict) else None
        if v and str(v).strip():
            probes.append(" ".join(str(v).split()))
    probes.append(result["status"])
    for key in ("detail", "attribution_basis"):
        v = result.get(key)
        if v and str(v).strip():
            probes.append(str(v))
    probes.extend(result.get("attribution") or [])
    return probes


def no_leak_problems(packets, report: dict, suite_dir: Path) -> list:
    """题包里泄了题就逐条报出来。空列表 = 干净。

    ⚠️ `suite_dir` **是必填的，不给默认值。** 早先它是可选的，不给就只查判定侧 ——
    于是调用方少写一个参数就静默降级成半套检查，而**降级看起来和通过一模一样**。
    这正是 `N-42` 那个形状：这道门扫的集合 ≠ 它声称在检查的集合。
    """
    cases = {c["id"]: c for c in load_cases(suite_dir)}
    results = {r["id"]: r for r in report["results"]}

    problems = []
    page = "\n".join(p.body for p in packets)
    for p in packets:
        result = results.get(p.case_id)
        if result is None:
            problems.append(p.anon_id + "：报告里找不到这一题的判定")
            continue
        for probe in leak_probes(cases.get(p.case_id, {}), result):
            if probe and probe in page:
                problems.append(
                    p.anon_id + "（" + p.case_id + "）泄题：题包里出现了 " + repr(probe)
                )
    return problems


# --------------------------------------------------------------------------
# 答卷
# --------------------------------------------------------------------------


def blank_sheet(packets) -> str:
    """空白答卷。**除了匿名号，一个字的提示都没有。**"""
    L = [
        "# H2 复核答卷。每题填 verdict，取值域见下；note 可写一句为什么（选填）。",
        "# 留空 = 没填。**「没填」和「填了无法判断」是两件事**，",
        "# 混同会让 EVAL_CASES §4.3 那道反向检验失真 —— 所以留空时拒绝算数。",
        "取值域: [" + ", ".join(VERDICTS) + "]",
        "verdicts:",
    ]
    for p in packets:
        L += ["  - id: " + p.anon_id, "    verdict:", '    note: ""']
    return "\n".join(L) + "\n"


def score(sheet: dict, report: dict, packets, build_info: dict | None = None) -> dict:
    """回填后的答卷 → 一致率 / 无法判断率 / §4.2 判定。

    **fail-closed 两处**：答卷没填完不给结论；`D-037` 的强制标注缺一项不给结论。

    `build_info` 是出包时写下的 `BUILD.json`（`N-75`）。**给不出就记「未声明」**，
    不记「是」—— 一份不知道是不是盲出的题包，必须当成可能已经泄底的来读。
    """
    results = {r["id"]: r for r in report["results"]}
    by_anon = {p.anon_id: p for p in packets}
    filled = {row["id"]: row.get("verdict") for row in (sheet.get("verdicts") or [])}

    problems = []
    missing = [a for a in by_anon if not str(filled.get(a) or "").strip()]
    if missing:
        problems.append("这几题没填：" + "、".join(sorted(missing)))
    bad = [a for a, v in filled.items() if v and v not in VERDICTS]
    if bad:
        problems.append("取值域之外的判定：" + "、".join(sorted(bad)))
    unknown = [a for a in filled if a not in by_anon]
    if unknown:
        problems.append("答卷里有题包之外的编号：" + "、".join(sorted(unknown)))

    n = len(packets)
    wrong_ids = [p.anon_id for p in packets if results[p.case_id]["status"] == FAIL]
    w = len(wrong_ids)

    agreed = undecidable = 0
    wrong_agreed = 0
    for p in packets:
        v = filled.get(p.anon_id)
        if v == "无法判断":
            undecidable += 1
            continue
        want = "对" if results[p.case_id]["status"] == PASS else "错"
        if v == want:
            agreed += 1
            if p.anon_id in wrong_ids:
                wrong_agreed += 1

    annotations = {
        # §4.1.1 第 1 条：说法必须与做法一致。这里永远是普查 —— `build_packets` 不抽样。
        "sampling": "普查",
        "w": w,
        # §4.1.1 第 2 条
        "w_ge_5_satisfied": w >= 5,
        # §4.1.1 第 3 条：错题子集上一致率的最小刻度
        "resolution_floor_on_wrong": (
            "1/%d = %.0f 个百分点" % (w, 100.0 / w) if w else "错题为 0，这一档无从分辨"
        ),
        "limitations": _LIMITATIONS_REF,
        # `N-75`：出包时有没有人读过 / 报过跑分结果。
        "blind_build": (
            "是（出包时未读跑分结果）"
            if (build_info or {}).get("blind") is True
            else "未声明 —— 复核者可能已知答案，一致率不可当作 AC-06 读数"
        ),
    }
    for key in REQUIRED_ANNOTATIONS:
        if key not in annotations:
            problems.append("缺强制标注：" + key)

    rate = agreed / n if n else 0.0
    undecidable_rate = undecidable / n if n else 0.0

    out = {
        "n": n,
        "agreed": agreed,
        "agreement_rate": rate,
        "undecidable": undecidable,
        "undecidable_rate": undecidable_rate,
        "undecidable_within_limit": undecidable_rate <= UNDECIDABLE_LIMIT,
        "wrong_subset": {
            "agreed": wrong_agreed,
            "total": w,
            "raw": "%d/%d" % (wrong_agreed, w),
        },
        "annotations": annotations,
        "problems": problems,
        "pass_blocked": [],
        "conclusion": None,
    }
    if problems:
        return out

    # 🔴 **强制标注不只是「在不在」，值也要成立**（2026-09-10 实测补上）。
    #
    # 此前只检查键存在，于是 `h2-frozen-02` 那一轮在同一屏上印出了
    # 「判定：H2 通过」与「blind_build: 未声明 —— 一致率不可当作 AC-06 读数」，
    # 自己跟自己拧着。一个看起来完全正当的「通过」，正是本项目反复栽的那个形状。
    #
    # ⚠️ **不对称是刻意的**：下面这些只挡「通过」，**不挡「不成立」**。
    #    「通过」是宽松结论，需要完整前提；「不成立」是停止信号，
    #    没有错题子集照样断定得了证据链不够用 —— 把停止信号也一起挡掉才是危险的。
    pass_blocked = []
    if w < 5:
        pass_blocked.append(
            "W = %d < 5：§4.1 要求样本含 ≥5 题答错。一致率整个落在**正确答案**上时，"
            "测不到「证据页帮不帮得上抓错」—— §4.2 附注说的分辨信号正来自错题子集。"
            "⇒ 这个数不构成 §4.2 的通过读数。" % w
        )
    if not str(annotations["blind_build"]).startswith("是"):
        pass_blocked.append(
            "题包非盲出（`N-75`）：复核者可能已知答案，"
            "那时每个「对」都不含信息 ⇒ 一致率不可当作 `AC-06` 读数。"
        )
    out["pass_blocked"] = pass_blocked

    if rate >= GATE_PASS and pass_blocked:
        out["conclusion"] = (
            "**不给「通过」。** 一致率 %.1f%% 达到了 §4.2 的 ≥80%%，"
            "但下面的前提不成立，所以它不是一次合格的 §4.2 读数（详见上）。"
            "⚠️ 仍然成立的是 §4.3 那个读数（「无法判断」占比），它不依赖错题子集。"
            % (rate * 100)
        )
        return out

    if rate >= GATE_PASS:
        verdict = "H2 通过"
    elif rate >= GATE_PARTIAL:
        # §4.2 附注：`W < 5` 时这一档分不开相邻两档，不许直接读成「部分成立」。
        verdict = "H2 部分成立"
        if w < 5:
            verdict += (
                "（⚠️ W=%d < 5，§4.2 附注：这一档在此分辨率下分不开相邻两档，"
                "必须连同错题子集原始计数 %s 一起交操作者判）"
                % (w, out["wrong_subset"]["raw"])
            )
    else:
        verdict = "H2 不成立 —— 停止，回到 ARCHITECT 重设计证据链，不得进入 Phase 3"
    out["conclusion"] = verdict
    return out


def render_score(got: dict) -> str:
    L = ["H2 复核实验结果", ""]
    if got["conclusion"] is None:
        L.append("**没有结论。** 下面这些先解决：")
        L += ["  - " + p for p in got["problems"]]
        return "\n".join(L)
    L += [
        "  一致率        %d/%d（%.1f%%）" % (got["agreed"], got["n"], got["agreement_rate"] * 100),
        "  无法判断      %d/%d（%.1f%%，上限 %.0f%%，%s）"
        % (
            got["undecidable"], got["n"], got["undecidable_rate"] * 100,
            UNDECIDABLE_LIMIT * 100,
            "未超限" if got["undecidable_within_limit"] else "**已超限，即使一致率达标也要补齐重测**",
        ),
        "  错题子集      %s（原始计数，§4.2 附注强制）" % got["wrong_subset"]["raw"],
        "",
    ]
    if got.get("pass_blocked"):
        L.append("🔴 **这一次不构成 §4.2 的通过读数**，原因：")
        L += ["  - " + r for r in got["pass_blocked"]]
        L.append("")
    L += [
        "  判定：" + got["conclusion"],
        "",
        "强制标注（`D-037` / `EVAL_CASES` §4.1.1）：",
    ]
    for key in REQUIRED_ANNOTATIONS:
        L.append("  %-26s %s" % (key, got["annotations"][key]))
    return "\n".join(L)


#: 进 `SHA256SUMS` 的产物。**答卷不在其中** —— 它就是要被复核者改的，
#: 冻它等于让清单在实验开始的那一刻必然变红。
FROZEN_ARTIFACTS = ("packets.md", "keymap.json", "BUILD.json")


def _write(path: Path, text: str) -> None:
    """写盘一律 **LF**。

    🔴 不是洁癖：`.gitattributes` 强制 LF 入库，而 Windows 上 `write_text` 默认写 CRLF
    ⇒ 工作树字节 ≠ git blob 字节。2026-09-05 上午刚因为这个把一份清单做成了
    「只在本机成立」（见第三十三段）；同一天下午生成题包时 git 又warn了一次。
    这里把它按死在出口上。
    """
    with open(path, "w", encoding="utf-8", newline=chr(10)) as fh:
        fh.write(text)


def _manifest(out_dir: Path, names) -> str:
    """题包与对照表的哈希清单。

    它证明的是**这两份文件自生成之后没被改过**；「生成于复核之前」由 git 历史证明。
    两件事分开说 —— 清单证不了时间，历史证不了内容完整性。

    ⚠️ `tests/test_conformance.py` 的 `_manifests()` 按 `git ls-files *SHA256SUMS` 发现清单
    ⇒ 这份一旦入库就**自动**落进那两道守卫（不得含 CRLF / 工作树上自校验通过），
    不需要在任何地方登记。
    """
    import hashlib

    lines = []
    for name in names:
        digest = hashlib.sha256((out_dir / name).read_bytes()).hexdigest()
        lines.append(digest + " *" + name)
    return chr(10).join(lines) + chr(10)


def main(argv=None) -> int:
    import argparse

    import yaml

    ap = argparse.ArgumentParser(prog="eval.h2", description="H2 复核实验器械")
    ap.add_argument("--suite", default="frozen-01")
    ap.add_argument("--seed", type=int, default=20260905)
    ap.add_argument("--out", default=None, help="题包输出目录，默认 docs/agent/h2-01/")
    ap.add_argument("--sheet", default=None, help="回填后的答卷；给了就只算数不重出题包")
    ap.add_argument(
        "--blind",
        action="store_true",
        help="盲出题包：跑分结果不出 build_packets，因此印不出 W 与逐题结果（N-75）。"
        "与 --sheet 互斥 —— 算数本来就需要那份结果。",
    )
    args = ap.parse_args(argv)

    if args.blind and args.sheet:
        print(
            "--blind 与 --sheet 不能同时给：算数必须读跑分结果，盲不了。\n"
            "盲的是**出包**那一步，不是算数那一步（算数时复核已经做完了）。",
            file=sys.stderr,
        )
        return 2

    suite_dir = EVAL_ROOT / args.suite
    out_dir = Path(args.out) if args.out else (REPO_ROOT / "docs" / "agent" / "h2-01")

    packets, report = build_packets(suite_dir, args.seed, blind=args.blind)

    if args.sheet:
        sheet = yaml.safe_load(Path(args.sheet).read_text(encoding="utf-8")) or {}
        # `N-75`：出包时写下的自证。**读不到就当没盲过**，不猜。
        build_path = Path(args.sheet).parent / "BUILD.json"
        build_info = None
        if build_path.is_file():
            try:
                build_info = json.loads(build_path.read_text(encoding="utf-8"))
            except Exception:
                build_info = None
        got = score(sheet, report, packets, build_info)
        print(render_score(got))
        # 结论缺失、或「通过」被前提挡下 ⇒ 退非零。
        # 退 0 会让调用方以为这一轮拿到了合格读数。
        ok = got["conclusion"] is not None and not got.get("pass_blocked")
        return 0 if ok else 1

    out_dir.mkdir(parents=True, exist_ok=True)
    _write(out_dir / "packets.md", render_packets(packets))
    _write(out_dir / "answer-sheet.yaml", blank_sheet(packets))
    _write(
        out_dir / "keymap.json",
        json.dumps(keymap(packets, args.seed), ensure_ascii=False, indent=2) + chr(10),
    )
    # `N-75` 的自证。**只记出包这一步做了什么**，不记任何跑分结果 ——
    # `n` 是题包题数，复核者数一数就知道，不是剧透。
    _write(
        out_dir / "BUILD.json",
        json.dumps(
            {
                "blind": bool(args.blind),
                "suite": args.suite,
                "seed": args.seed,
                "n": len(packets),
                "note": (
                    "blind=true 表示出包时跑分结果没有离开 build_packets，"
                    "执行者印不出 W 与逐题结果。它管不住另起一个进程跑 eval.run —— "
                    "那条要靠「出包 → 复核 → 才跑才报」这条规矩。见 N-75。"
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
        + chr(10),
    )
    _write(out_dir / "SHA256SUMS", _manifest(out_dir, FROZEN_ARTIFACTS))
    print("题包 %d 题（普查，不抽样）已写入 %s" % (len(packets), out_dir))
    print("⚠️ keymap.json 是对照表，**复核者不拿到**；复核前也不要读 02-03-PLAN 的 <context>。")
    if args.blind:
        print("✅ 盲出：跑分结果未离开 build_packets，本进程印不出 W 与逐题结果。")
        print("⚠️ 但它拦不住 `python -m eval.run --suite %s` —— **复核做完之前别跑那个**。" % args.suite)
    else:
        print("⚠️ **非盲出**：本次没给 --blind。若执行者读过或转述过跑分结果，")
        print("   复核者可能已知答案 ⇒ 一致率不能当作 AC-06 的读数（N-75）。")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
