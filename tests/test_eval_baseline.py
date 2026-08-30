"""对照臂（裸 LLM）的判定逻辑测试。

**本文件不发任何网络请求，也不引用 `eval/frozen-01`。** 前者会让测试依赖额度与网络，
后者会制造「改冻结集就能让测试变绿」的动机（同 `test_eval_runner.py` 顶部的理由）。
题面一律在用例里现造。

最重要的一条是 `test_prompt_does_not_leak_answers`：题面文件里 `rationale` 写着正解、
`attribution_hint` 写着陷阱在哪。任何一个漏进提示词，整条对照臂就一文不值，
而且**从报告上看不出来**——分数会很好看。这正是需要机器锁住的那类事实。
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from eval.baseline import (  # noqa: E402
    ERROR,
    FAIL,
    NEEDS_HUMAN,
    NOT_COMPARABLE,
    PASS,
    build_user_prompt,
    judge,
    parse_answer,
)
from eval.llm_client import Provider, WIRE_OPENAI  # noqa: E402

FIXTURE = "rows:\n  - stock_code: '900001'\n    is.operating_revenue_current: 5000000000\n"


def _case(cid, cat, **kw):
    exp = kw.pop("expected", {})
    jud = kw.pop("judging", {})
    return {
        "id": cid, "category": cat,
        "question": "某公司 2023 年的某指标是多少？",
        "rationale": "正解是归母口径 0.112，取含少数股东会得到 0.124",
        "expected": {"rationale": "分子必须用归母净利润", **exp},
        "judging": jud,
        "attribution_hint": "口径层：分子在归母 / 含少数股东 / 扣非三者间选错",
        **kw,
    }


def _ans(**kw):
    base = {"refused": False, "refusal_kind": None, "value": None, "unit": "decimal",
            "metric_definition": "", "citations": [], "reasoning": ""}
    base.update(kw)
    return base


# --------------------------------------------------------------------------
# 提示词不得泄题 —— 本文件最重要的一条
# --------------------------------------------------------------------------


def test_prompt_does_not_leak_answers():
    case = _case("Q-X-001", "C1", expected={"value": 0.112})
    prompt = build_user_prompt(case, FIXTURE)

    assert case["question"].strip() in prompt
    for leaked in ("0.112", "0.124", "归母口径", "attribution", "口径层", "rationale",
                   case["rationale"], case["attribution_hint"],
                   case["expected"]["rationale"]):
        assert leaked not in prompt, f"提示词泄露了 {leaked!r}"


def test_c1_c2_c3_get_fixture_c4_c5_do_not():
    """C2 也必须拿到数据。

    否则模型可以用「你没给我数据」拒答，那是 data_missing 不是 metric_not_defined，
    两者的能力含义完全不同——首轮冒烟就是这么被糊弄过去的。
    """
    for cat in ("C1", "C2", "C3"):
        assert FIXTURE in build_user_prompt(_case("Q", cat), FIXTURE)
    for cat in ("C4", "C5"):
        assert FIXTURE not in build_user_prompt(_case("Q", cat), FIXTURE)


# --------------------------------------------------------------------------
# 输出解析：解析失败 ≠ 答错
# --------------------------------------------------------------------------


def test_parse_bare_json():
    ans, note = parse_answer('{"refused": false, "value": 1}')
    assert ans["value"] == 1 and note == ""


def test_parse_fenced_json():
    ans, _ = parse_answer('```json\n{"refused": true}\n```')
    assert ans["refused"] is True


def test_parse_json_embedded_in_prose():
    ans, note = parse_answer('我的回答如下：\n{"refused": false, "value": 2}\n希望有帮助')
    assert ans["value"] == 2 and "截取" in note


def test_parse_failure_is_not_a_wrong_answer():
    ans, note = parse_answer("我认为这个问题无法回答。")
    assert ans is None and note
    v = judge(_case("Q", "C1", expected={"value": 0.1}), ans, note)
    assert v["status"] == ERROR, "解析失败必须标 ERROR，不能记成 FAIL"


# --------------------------------------------------------------------------
# 拒答类：理由码必须对上，照抄系统臂 eval/run.py 的规则
# --------------------------------------------------------------------------


def test_refusal_with_matching_kind_passes():
    case = _case("Q", "C2", expected={"refusal_code": "METRIC_NOT_DEFINED"},
                 judging={"refusal_expected": True})
    v = judge(case, _ans(refused=True, refusal_kind="metric_not_defined"), "")
    assert v["status"] == PASS


def test_metric_ambiguous_also_counts_for_metric_not_defined():
    case = _case("Q", "C2", expected={"refusal_code": "METRIC_NOT_DEFINED"},
                 judging={"refusal_expected": True})
    v = judge(case, _ans(refused=True, refusal_kind="metric_ambiguous"), "")
    assert v["status"] == PASS


def test_refusal_for_wrong_reason_fails():
    """拒答理由不符 → FAIL。这是本条对照臂能否成立的关键。

    「我没数据所以不算」和「这个指标没有权威口径所以我不该自己拟一个」
    是两种完全不同的能力。前者在数据摆上桌之后就会消失。
    """
    case = _case("Q", "C2", expected={"refusal_code": "METRIC_NOT_DEFINED"},
                 judging={"refusal_expected": True})
    v = judge(case, _ans(refused=True, refusal_kind="data_missing"), "")
    assert v["status"] == FAIL
    assert "理由不符" in v["detail"]


def test_undefined_condition_requires_data_missing():
    case = _case("Q", "C3", expected={"refusal_code": "UNDEFINED_CONDITION_HIT"},
                 judging={"refusal_expected": True})
    assert judge(case, _ans(refused=True, refusal_kind="data_missing"), "")["status"] == PASS
    assert judge(case, _ans(refused=True, refusal_kind="metric_not_defined"), "")["status"] == FAIL


def test_answering_when_refusal_expected_fails():
    case = _case("Q", "C2", expected={"refusal_code": "METRIC_NOT_DEFINED"},
                 judging={"refusal_expected": True})
    v = judge(case, _ans(refused=False, value=123.4), "")
    assert v["status"] == FAIL and "强行作答" in v["detail"]


# --------------------------------------------------------------------------
# 数值类
# --------------------------------------------------------------------------


def test_numeric_within_tolerance_passes():
    case = _case("Q", "C1", expected={"value": 0.112, "tolerance": {"abs": 1e-6, "rel": 1e-9}},
                 judging={"refusal_expected": False})
    assert judge(case, _ans(value=0.112), "")["status"] == PASS


def test_wrong_caliber_value_fails():
    """0.124 是「取了含少数股东损益的净利润」——数值看起来完全正常的静默错误。"""
    case = _case("Q", "C1", expected={"value": 0.112, "tolerance": {"abs": 1e-6, "rel": 1e-9}},
                 judging={"refusal_expected": False})
    v = judge(case, _ans(value=0.124), "")
    assert v["status"] == FAIL


def test_percent_form_is_failed_but_annotated():
    """百分数写法算失败，但要在 detail 里注明是表达层不是口径层——归因不同。"""
    case = _case("Q", "C1", expected={"value": 0.112, "tolerance": {"abs": 1e-6, "rel": 1e-9}},
                 judging={"refusal_expected": False})
    v = judge(case, _ans(value=11.2), "")
    assert v["status"] == FAIL
    assert "表达层" in v["detail"]


def test_refusing_an_answerable_question_fails():
    case = _case("Q", "C1", expected={"value": 0.3}, judging={"refusal_expected": False})
    v = judge(case, _ans(refused=True, refusal_kind="data_missing"), "")
    assert v["status"] == FAIL and "模型拒答" in v["detail"]


def test_multi_period_expected_value():
    case = _case("Q", "C3", judging={"refusal_expected": False},
                 expected={"value": {"2023": 0.12, "2018": 0.153571428571429},
                           "tolerance": {"abs": 1e-6, "rel": 1e-9}})
    ok = judge(case, _ans(value={"2023": 0.12, "2018": 0.153571428571429}), "")
    assert ok["status"] == PASS
    bad = judge(case, _ans(value={"2023": 0.12, "2018": 0.99}), "")
    assert bad["status"] == FAIL and bad["sub_checks"]["2018"] is False
    shape = judge(case, _ans(value=0.12), "")
    assert shape["status"] == FAIL and "多期" in shape["detail"]


# --------------------------------------------------------------------------
# C4 / C5
# --------------------------------------------------------------------------


C4_CASE = dict(expected={
    "expected_citations": [{"name": "公开发行证券的公司信息披露解释性公告第 1 号——非经常性损益",
                            "issuer": "中国证券监督管理委员会",
                            "versions_required": ["2008", "2023"]}],
    "must_state": "跨版本年度的扣非净利润不可直接比较",
}, judging={"refusal_expected": False, "correctness": "set_equality"})


def test_c4_all_subchecks_hit_passes_but_flags_unverified():
    case = _case("Q", "C4", **C4_CASE)
    v = judge(case, _ans(citations=["公开发行证券的公司信息披露解释性公告第 1 号（2008 版 / 2023 版）"],
                         reasoning="两版项目清单不同，跨版本不可直接比较"), "")
    assert v["status"] == PASS
    # 字符串命中不证明引用真实存在——这一句必须留在报告里
    assert "不证明引用真实存在" in v["detail"]


def test_c4_partial_hit_needs_human():
    case = _case("Q", "C4", **C4_CASE)
    v = judge(case, _ans(citations=["公开发行证券的公司信息披露解释性公告第 1 号"],
                         reasoning="依据证监会公告"), "")
    assert v["status"] == NEEDS_HUMAN


def test_c4_refusal_is_a_failure():
    case = _case("Q", "C4", **C4_CASE)
    assert judge(case, _ans(refused=True, refusal_kind="metric_ambiguous"), "")["status"] == FAIL


def test_c5_is_not_comparable_not_a_score():
    v = judge(_case("Q", "C5", judging={"refusal_expected": False}), _ans(value=1), "")
    assert v["status"] == NOT_COMPARABLE
    assert "D-007" in v["detail"]


# --------------------------------------------------------------------------
# 密钥绝不进产物
# --------------------------------------------------------------------------


def test_redacted_provider_never_contains_the_key():
    secret = "sk-" + "b" * 61
    p = Provider("t", "https://example.invalid", WIRE_OPENAI, "m-1", secret)
    blob = repr(p.redacted())
    assert secret not in blob
    assert "sk-b" in blob, "指纹要够识别是哪把钥匙"
    assert str(len(secret)) in blob


# --------------------------------------------------------------------------
# frozen-02 待办：冻结夹具的取值域已与 D-028 不一致（2026-08-31 钉住）
# --------------------------------------------------------------------------


def test_冻结夹具与D028取值域的已知不一致被钉死():
    """**这条不是在说「一切正常」，是把一处已知的不一致钉在原地。**

    `D-028` 把 `notes.business_combination_type` 从单值枚举改成集合值，
    并**取消了 `无` 这个哨兵值**（空集即表示本期无企业合并）。
    而 `eval/frozen-01/fixtures/synthetic-01.yaml` 里仍有 **6 处** `无` ——
    **它们是冻结的，`D-012` 不许改**，所以这不是缺陷而是一笔**如实记着的欠账**
    （处置在 `frozen-02`，与 `N-19` 同批）。

    ## 为什么要写成一条测试而不是只写进文档

    文档写了会过期，而这处不一致**没有任何机制在看着它**：
    夹具值从不被校验取值域（`D-020` 把 trigger 移走之后无人读它），
    所以它可以一直躺着，直到某天有人拿新的 `enum_values` 去消费旧夹具。

    本条把**已知不一致的规模**钉住：
    - 多出第 7 处 ⇒ 红。有人在往冻结集里加东西，那是 `D-012` 的事。
    - 少于 6 处 ⇒ 红。**冻结集被改动了** —— 这比多一处更严重。
    - `enum_values` 里重新出现 `无` ⇒ 红。`D-028` 被悄悄推翻了。

    ⚠️ **红了不要改这条测试的数字**，先查是哪一边变了。
    """
    import yaml

    fixture = REPO_ROOT / "eval" / "frozen-01" / "fixtures" / "synthetic-01.yaml"
    stale = fixture.read_text(encoding="utf-8").count("notes.business_combination_type: 无")
    assert stale == 6, (
        f"冻结夹具里 `business_combination_type: 无` 有 {stale} 处，登记的是 6 处。"
        "多了 ⇒ 有人往冻结集里加东西；少了 ⇒ 冻结集被改动（D-012）。"
    )

    defn = yaml.safe_load(
        (REPO_ROOT / "metrics" / "minority_interest_share.yaml").read_text(encoding="utf-8")
    )
    field = next(
        f for f in defn["source_fields"] if f["id"] == "notes.business_combination_type"
    )
    assert field["value_shape"] == "set"
    assert "无" not in field["enum_values"], (
        "`无` 又回到 enum_values 里了 —— D-028 明写取消这个哨兵值："
        "在集合域里放一个「无」，是把「没有元素」写成「有一个叫『没有』的元素」。"
    )
    # 这两句合起来才是本条的意思：**定义侧已经改了，冻结侧没跟上，且不许跟上。**
    assert stale > 0 and "无" not in field["enum_values"]
