"""frozen-01 的 **baseline 对照臂** —— 让一个不带语义层的通用 LLM answer 全部 20 题。

## 为什么要有这条臂

`AGENTS.md` 开篇写着本项目的差异化：「通用 Agent 答不出「这个口径对不对」，
它能答，而且能证明。」**这句话此前零证据。** 本模块就是去取那份证据。

## 它和 `eval/run.py` 的关系：两条臂，不合并

| | 系统臂 `eval/run.py` | 对照臂 `eval/baseline.py`（本文件） |
|---|---|---|
| 被测对象 | `semantic_layer.resolve`，确定性 | 裸 LLM，无语义层、无口径库、无证据链 |
| 本阶段可执行 | 仅 C2（4 题）——其余是**能力缺口**不是配置缺失 | 全部 20 题（其中 14 题可机械判定） |
| 报告目录 | `eval/runs/` | `eval/runs/baseline/` |

⚠️ **两条臂的分数永远不合并，也不互相替代。**
把对照臂跑出的 C1/C3 数字当成"本系统 C1/C3 通过了"，是本仓库能犯的最严重的谎——
那些数是 LLM 心算出来的，没有口径绑定、没有证据链，**恰好是本项目要证伪的东西**。
`eval/run.py` 里 C1/C3/C4/C5 标 `NOT_RUN` 的理由一个字都没变。

## 公平性：这条臂是被 steel-man 过的

为了让"通用 Agent 答不出"这个结论站得住，对照臂被刻意加强了：

1. **合成夹具全文喂给模型**。C1/C3 问的是虚构公司，不给数据谁也答不了。
   给全量而不是我挑过的子集，避免"我选的字段决定了它的成败"。
2. **显式告知拒答是被允许且被鼓励的**。若不告知，C2 的失败就太廉价了——
   那只证明它不知道可以拒答，不证明它分不清该不该拒答。
3. **要求结构化输出**，避免把"格式没对齐"误判成"答错了"。
4. `temperature=0`，并记录 `prompt_sha256`。

即便如此它仍然答错，那才是有效证据。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

EVAL_ROOT = Path(__file__).resolve().parent
REPO_ROOT = EVAL_ROOT.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from eval.llm_client import LLMError, PRESETS, complete, make_provider  # noqa: E402
from eval.run import verify_freeze  # noqa: E402  —— 复用同一道 fail-closed 冻结门

PASS, FAIL, REFUSED_WRONGLY = "PASS", "FAIL", "FAIL"
NEEDS_HUMAN = "NEEDS_HUMAN"
NOT_COMPARABLE = "NOT_COMPARABLE"
ERROR = "ERROR"

SYSTEM_PROMPT = """你是一名财务分析助手。请基于用户给出的数据回答财务指标问题。

**重要：拒答是被允许、且在恰当情形下是正确的行为。** 出现以下任一情况时你应当拒答，
而不是猜一个看起来合理的数：
- 问题所问的指标名称有多种常见口径，无法从问题本身确定该用哪一种；
- 数据缺失，无法计算（注意：缺失与零是两回事，不要把缺失当作零处理）；
- 该指标需要的分量在数据中不存在。

猜一个数值比拒答更糟。你不会因为拒答而被扣分。

**输出格式：只输出一个 JSON 对象，不要有任何其它文字，不要用 markdown 代码块包裹。**

{
  "refused": true 或 false,
  "refusal_kind": 拒答时必填，取以下之一；未拒答时填 null
      "metric_not_defined"  —— 我没有该指标的权威口径依据，不应自行拟定
      "metric_ambiguous"    —— 该指标名有多种通行口径，问题本身定不下用哪种
      "data_missing"        —— 计算所需的数据在给定数据中缺失
      "other"
  "value": 数值 或 null,
  "unit": "decimal" 或 "percent" 或 "days" 或 "ratio" 或 null,
  "metric_definition": "你实际采用的口径，写清分子与分母的确切取数项",
  "citations": ["你依据的准则/规范性文件名称与版本，没有就给空数组"],
  "reasoning": "简要理由"
}

数值请以**小数**形式给出（例如 12% 写作 0.12），天数类指标直接给天数。
"""


def _fixture_text(suite_dir: Path) -> str:
    return (suite_dir / "fixtures" / "synthetic-01.yaml").read_text(encoding="utf-8")


def build_user_prompt(case: dict, fixture: str) -> str:
    """构造题面。**不泄露 expected / rationale / attribution_hint**。

    只有 `question` 进提示词。`rationale` 里写着正解，`attribution_hint` 写着陷阱在哪，
    任何一个漏进去，这条臂就一文不值。
    """
    parts = [f"问题：\n{case['question'].strip()}"]
    # C1 / C2 / C3 都给全量夹具。**C2 也给**是关键：
    # 首轮冒烟发现 DeepSeek 对 C2 的拒答理由全是「你没给我数据」——
    # 那是「数据缺失」不是「口径未定义」，两者的能力含义完全不同。
    # 把数据摆上桌，「没数据」这个借口就不存在了，此时它是否还拒答才有意义。
    if case["category"] in ("C1", "C2", "C3"):
        parts.append(
            "以下是可用的财务数据（合成数据，虚构公司）。"
            "请只使用其中的数值，不要引入外部数据或自行假设：\n"
            f"```yaml\n{fixture}\n```"
        )
    return "\n\n".join(parts)


# 拒答理由码的对应关系。**这不是我发明的判定，是照抄系统臂**：
# `eval/run.py:146-151` 明写「拒答但理由码不符 → FAIL（口径层）」。
# 对照臂若不照同一把尺子量，两条臂的数字就不可比。
REFUSAL_KIND_FOR_CODE = {
    # 语义层里根本没有这个指标 ⇒ 裸模型的对应物是「我没有权威口径可依据」
    # 或「这名字有多种通行口径，定不下来」。二者都算命中。
    "METRIC_NOT_DEFINED": {"metric_not_defined", "metric_ambiguous"},
    # 指标有定义，但数据触发了未定义条件（缺失期 / 零分母）⇒ 只有「数据缺失」算命中
    "UNDEFINED_CONDITION_HIT": {"data_missing"},
}


_JSON_RE = re.compile(r"\{.*\}", re.S)


def parse_answer(text: str) -> tuple[dict | None, str]:
    """解析模型输出。解析失败**不当作答错**，单独标 ERROR —— 那是格式问题不是能力问题。"""
    raw = text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"\n?```\s*$", "", raw)
    try:
        return json.loads(raw), ""
    except Exception:
        pass
    m = _JSON_RE.search(raw)
    if m:
        try:
            return json.loads(m.group(0)), "（从自由文本中截取了 JSON）"
        except Exception as e:
            return None, f"JSON 解析失败：{e}"
    return None, "输出中找不到 JSON 对象"


def _num(x):
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        s = x.strip().replace(",", "").rstrip("%").strip()
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _within(got: float, want: float, tol: dict) -> bool:
    a = float(tol.get("abs", 1e-6))
    r = float(tol.get("rel", 1e-9))
    return abs(got - want) <= max(a, abs(want) * r)


def judge(case: dict, ans: dict | None, parse_note: str) -> dict:
    """按类别判定。**每一类的判定力度都如实标注**，不把不可判的说成可判的。"""
    cid, cat = case["id"], case["category"]
    exp = case.get("expected", {}) or {}
    jud = case.get("judging", {}) or {}
    out = {"id": cid, "category": cat, "detail": "", "sub_checks": {}}

    if ans is None:
        return {**out, "status": ERROR, "detail": parse_note or "无法解析模型输出"}

    refused = bool(ans.get("refused"))

    # ---- C5：本阶段结构上不可比 ----
    if cat == "C5":
        return {**out, "status": NOT_COMPARABLE,
                "detail": "题面本身已把闭环完整叙述在提示词里，模型不需要做多跳检索即可复述。"
                          "D-007 要求的证伪实验是「纯向量 RAG 在真实附注上能否浮现闭环」，"
                          "与本臂的自足式提问不是同一件事。此处只留档模型输出，不作分数。"}

    # ---- C2 / 期望拒答的 C1、C3 ----
    if jud.get("refusal_expected"):
        if not refused:
            v = _num(ans.get("value"))
            return {**out, "status": FAIL,
                    "detail": f"应拒答而强行作答，给出 {v!r}。"
                              f"采用口径：{str(ans.get('metric_definition',''))[:120]}"}

        want_code = exp.get("refusal_code")
        kind = (ans.get("refusal_kind") or "").strip().lower()
        allowed = REFUSAL_KIND_FOR_CODE.get(want_code)
        if allowed is None:
            return {**out, "status": PASS,
                    "detail": f"拒答（该题未声明 refusal_code）。理由：{str(ans.get('reasoning',''))[:100]}"}
        if kind in allowed:
            return {**out, "status": PASS,
                    "detail": f"正确拒答，理由类型 {kind}（期望 {want_code}）"}
        return {**out, "status": FAIL,
                "sub_checks": {"refused": True, f"kind∈{sorted(allowed)}": False},
                "detail": f"拒答了，但**理由不符**：期望 {want_code}（应为 "
                          f"{'/'.join(sorted(allowed))}），实际 {kind or '未声明'}。"
                          f"理由原文：{str(ans.get('reasoning',''))[:100]}"}

    # ---- C4：准则引用，机械子检查 + 明确的判定力度声明 ----
    if cat == "C4":
        cites = ans.get("citations") or []
        blob = json.dumps({"c": cites, "r": ans.get("reasoning", ""),
                           "m": ans.get("metric_definition", "")}, ensure_ascii=False)
        checks = {}
        for want in exp.get("expected_citations", []) or []:
            nm = want.get("name", "")
            key_frag = nm[:8]
            checks[f"文件名命中「{key_frag}…」"] = bool(key_frag) and key_frag in blob
            for ver in want.get("versions_required", []) or []:
                checks[f"版本 {ver} 出现"] = ver in blob
        must = exp.get("must_state")
        if must:
            # 关键词法：取 must_state 里的实词做包含检查，命不中不等于没说，故只作子项
            checks[f"提到「{must[:12]}…」要点"] = any(
                frag and frag in blob for frag in (must[:6], must[-6:], "不可直接比较", "不可比")
            )
        if refused:
            return {**out, "status": FAIL, "sub_checks": checks,
                    "detail": "C4 不应拒答（问的是准则依据，不是口径歧义），模型拒答了。"}
        all_ok = bool(checks) and all(checks.values())
        none_ok = not any(checks.values())
        if all_ok:
            return {**out, "status": PASS, "sub_checks": checks,
                    "detail": "全部机械子检查通过。**注意：子检查是字符串命中，不证明引用真实存在**——"
                              "模型可能引用了一份不存在的文件而恰好名字对。需人工复核真伪。"}
        if none_ok:
            return {**out, "status": FAIL, "sub_checks": checks,
                    "detail": "所有机械子检查均未命中。"}
        return {**out, "status": NEEDS_HUMAN, "sub_checks": checks,
                "detail": "部分子检查命中。set_equality 无法由字符串包含判定，需人工。"}

    # ---- C1 / C3 数值题 ----
    want = exp.get("value")
    tol = exp.get("tolerance") or {"abs": 1e-6, "rel": 1e-9}

    if refused:
        return {**out, "status": FAIL,
                "detail": f"本题有唯一正解 {want!r}，模型拒答。"
                          f"理由：{str(ans.get('reasoning',''))[:120]}"}

    # C3-004 这类要求多期数值的题
    if isinstance(want, dict):
        got_map = ans.get("value")
        if not isinstance(got_map, dict):
            return {**out, "status": FAIL,
                    "detail": f"本题要求给出多期数值 {want!r}，模型给的是 {got_map!r}"}
        checks = {}
        for k, wv in want.items():
            gv = _num(got_map.get(k) if k in got_map else got_map.get(str(k)))
            checks[f"{k}"] = gv is not None and _within(gv, float(wv), tol)
        ok = all(checks.values())
        return {**out, "status": PASS if ok else FAIL, "sub_checks": checks,
                "detail": f"期望 {want}，实得 {got_map}"}

    got = _num(ans.get("value"))
    if got is None:
        return {**out, "status": ERROR, "detail": f"value 不是数值：{ans.get('value')!r}"}

    wantf = float(want)
    if _within(got, wantf, tol):
        return {**out, "status": PASS, "detail": f"数值正确 {got}"}

    # 百分数形式：如实记录但**不算通过**。tolerance 就是 tolerance，
    # 记这一条是为了区分「口径选错」与「单位写法不同」——两者的归因层不一样。
    pct_note = ""
    if _within(got / 100.0, wantf, tol):
        pct_note = "（注意：got/100 落在容差内，这是单位写法问题不是口径问题，归表达层）"
    return {**out, "status": FAIL,
            "detail": f"期望 {wantf}，实得 {got}{pct_note}。"
                      f"模型采用口径：{str(ans.get('metric_definition',''))[:160]}"}


def run(suite: str, preset: str, model: str | None, key_file: str | None,
        only: str | None, limit: int | None, max_tokens: int = 8192) -> dict:
    suite_dir = EVAL_ROOT / suite
    ok, problems = verify_freeze(suite_dir)
    if not ok:
        raise SystemExit("冻结校验未通过，拒绝运行：\n  " + "\n  ".join(problems))

    provider = make_provider(preset, model, key_file)
    fixture = _fixture_text(suite_dir)
    cases = [yaml.safe_load(p.read_text(encoding="utf-8"))
             for p in sorted((suite_dir / "cases").glob("*.yaml"))]
    if only:
        cases = [c for c in cases if c["category"] == only]
    if limit:
        cases = cases[:limit]

    results, transcript = [], []
    for case in cases:
        user = build_user_prompt(case, fixture)
        try:
            comp = complete(provider, SYSTEM_PROMPT, user, max_tokens=max_tokens)
        except LLMError as e:
            results.append({"id": case["id"], "category": case["category"],
                            "status": ERROR, "detail": str(e), "sub_checks": {}})
            transcript.append({"id": case["id"], "error": str(e)})
            print(f"  {ERROR:<14} {case['id']:<12} {e}")
            continue
        ans, note = parse_answer(comp.text)
        verdict = judge(case, ans, note)
        results.append(verdict)
        transcript.append({
            "id": case["id"], "prompt_sha256": comp.prompt_sha256,
            "model_reported": comp.model, "latency_ms": comp.latency_ms,
            "usage": comp.usage, "raw_output": comp.text, "parsed": ans,
        })
        print(f"  {verdict['status']:<14} {case['id']:<12} {verdict['detail'][:110]}")

    return _summarize(suite, provider, results, transcript)


def _summarize(suite: str, provider, results: list[dict], transcript: list[dict]) -> dict:
    by_cat = {}
    for cat in ("C1", "C2", "C3", "C4", "C5"):
        rs = [r for r in results if r["category"] == cat]
        scored = [r for r in rs if r["status"] in (PASS, FAIL)]
        by_cat[cat] = {
            "asked": len(rs),
            "mechanically_scored": len(scored),
            "passed": len([r for r in scored if r["status"] == PASS]),
            "needs_human": len([r for r in rs if r["status"] == NEEDS_HUMAN]),
            "not_comparable": len([r for r in rs if r["status"] == NOT_COMPARABLE]),
            "error": len([r for r in rs if r["status"] == ERROR]),
        }
    scored_all = [r for r in results if r["status"] in (PASS, FAIL)]
    tok_in = sum(t.get("usage", {}).get("prompt_tokens", 0) or
                 t.get("usage", {}).get("input_tokens", 0) for t in transcript)
    tok_out = sum(t.get("usage", {}).get("completion_tokens", 0) or
                  t.get("usage", {}).get("output_tokens", 0) for t in transcript)

    return {
        # 这三个字段是防混淆的关键，不要删
        "arm": "baseline-llm-no-semantic-layer",
        "is_system_under_test": False,
        "warning": "本报告测的是**不带语义层的裸 LLM**，不是 finaudit-agent。"
                   "其 C1/C3 分数不得引用为本系统的能力。系统臂见 eval/runs/。",
        "suite": suite,
        "run_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "provider": provider.redacted(),
        "counts": {
            "asked": len(results),
            "mechanically_scored": len(scored_all),
            "passed": len([r for r in scored_all if r["status"] == PASS]),
            "failed": len([r for r in scored_all if r["status"] == FAIL]),
            "needs_human": len([r for r in results if r["status"] == NEEDS_HUMAN]),
            "not_comparable": len([r for r in results if r["status"] == NOT_COMPARABLE]),
            "error": len([r for r in results if r["status"] == ERROR]),
        },
        # D-10：评测指标此前全是质量维度，效率与成本整类缺失。这里先把原料记下来
        "cost": {"prompt_tokens": tok_in, "completion_tokens": tok_out,
                 "total_tokens": tok_in + tok_out},
        "by_category": by_cat,
        "results": results,
        "transcript": transcript,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="eval.baseline",
                                 description="frozen-01 的裸 LLM 对照臂（不是系统臂）")
    ap.add_argument("--suite", default="frozen-01")
    ap.add_argument("--preset", default="deepseek", choices=sorted(PRESETS))
    ap.add_argument("--model", default=None, help="覆盖预设的模型 id")
    ap.add_argument("--key-file", default=None, help="密钥文件路径（**不要放进仓库**）")
    ap.add_argument("--category", default=None, choices=["C1", "C2", "C3", "C4", "C5"])
    ap.add_argument("--limit", type=int, default=None, help="只跑前 N 题（渐进式评估，D-10）")
    ap.add_argument("--max-tokens", type=int, default=8192,
                    help="推理模型会把预算全烧在 reasoning 上，给少了会返回空正文")
    args = ap.parse_args(argv)

    # Windows 控制台默认 GBK，报告里的中文与符号会把 print 打崩。
    # 报告文件本身一直是 UTF-8，这里只修终端回显。
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    print(f"对照臂 baseline —— 套件 {args.suite}，预设 {args.preset}")
    report = run(args.suite, args.preset, args.model, args.key_file, args.category,
                 args.limit, args.max_tokens)

    c = report["counts"]
    print(f"\n机械判定 {c['mechanically_scored']}/{c['asked']} 题："
          f"通过 {c['passed']}   失败 {c['failed']}")
    print(f"需人工 {c['needs_human']}   结构上不可比 {c['not_comparable']}   出错 {c['error']}")
    print(f"token：入 {report['cost']['prompt_tokens']}  出 {report['cost']['completion_tokens']}")
    for cat, v in report["by_category"].items():
        if v["asked"]:
            print(f"  {cat}  提问 {v['asked']}  机械判定 {v['mechanically_scored']}"
                  f"  通过 {v['passed']}  需人工 {v['needs_human']}"
                  f"  不可比 {v['not_comparable']}  出错 {v['error']}")

    out_dir = EVAL_ROOT / "runs" / "baseline"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = report["run_at"].replace(":", "").replace("-", "")
    model_tag = re.sub(r"[^A-Za-z0-9._-]", "_", report["provider"]["model"])
    out = out_dir / f"{args.suite}-{model_tag}-{stamp}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n报告已写入 {out}")
    print("⚠️ 这是对照臂产物，**不得**当作 finaudit-agent 自身的评测结果引用。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
