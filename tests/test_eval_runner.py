"""评测运行器的行为测试。

**本文件不得引用 `eval/frozen-01`。** 冻结套件只读，测试若依赖它，
一旦冻结集变动测试就会红，人就会有动机去改冻结集——那正是 D-012 要防的事。
全部用例走 `eval/testdata/sample-suite/`，或在 tmp_path 里现造。
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from eval.run import (  # noqa: E402
    FAIL,
    NOT_RUN,
    PASS,
    VOIDED,
    main,
    render,
    run_suite,
    verify_freeze,
)

SAMPLE = REPO_ROOT / "eval" / "testdata" / "sample-suite"


@pytest.fixture
def suite(tmp_path):
    """把样例套件复制到 tmp_path，篡改类用例只动副本。"""
    dst = tmp_path / "sample-suite"
    shutil.copytree(SAMPLE, dst)
    return dst


# --------------------------------------------------------------------------
# 冻结校验：fail-closed
# --------------------------------------------------------------------------


def test_verify_freeze_passes_when_intact(suite):
    ok, problems = verify_freeze(suite)
    assert ok, problems


def test_verify_freeze_fails_on_one_byte_change(suite):
    target = suite / "cases" / "S-C2-001.yaml"
    target.write_text(target.read_text(encoding="utf-8") + " ", encoding="utf-8")
    ok, problems = verify_freeze(suite)
    assert not ok
    assert any("哈希不符" in p for p in problems)


def test_verify_freeze_fails_when_manifest_missing(suite):
    """清单缺失不是「没什么可校验所以通过」，是拒绝运行。"""
    (suite / "SHA256SUMS").unlink()
    ok, problems = verify_freeze(suite)
    assert not ok
    assert any("清单缺失" in p for p in problems)


def test_verify_freeze_fails_when_listed_file_missing(suite):
    (suite / "cases" / "S-C2-002.yaml").unlink()
    ok, problems = verify_freeze(suite)
    assert not ok
    assert any("文件缺失" in p for p in problems)


def test_verify_freeze_fails_on_unlisted_extra_case(suite):
    """往冻结集里塞一道清单外的题，同样算冻结集被动过。"""
    (suite / "cases" / "S-C9-999.yaml").write_text(
        "id: S-C9-999\ncategory: C2\n", encoding="utf-8"
    )
    ok, problems = verify_freeze(suite)
    assert not ok
    assert any("未被冻结清单收录" in p for p in problems)


def test_main_refuses_to_run_any_case_when_freeze_broken(suite, capsys, monkeypatch):
    """fail-closed 的核心：非零退出，**且 stdout 里没有任何题目判定结果**。"""
    import eval.run as runner

    monkeypatch.setattr(runner, "EVAL_ROOT", suite.parent)
    target = suite / "cases" / "S-C2-001.yaml"
    target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    code = main(["--suite", suite.name])
    out = capsys.readouterr()
    assert code != 0
    assert "S-C2-001" not in out.out
    assert PASS not in out.out and FAIL not in out.out
    assert "拒绝运行" in out.err


# --------------------------------------------------------------------------
# 拒答判定（EVAL_CASES §3.2）
# --------------------------------------------------------------------------


def test_correct_refusal_passes(suite):
    report = run_suite(suite, "C2")
    got = {r["id"]: r for r in report["results"]}
    assert got["S-C2-001"]["status"] == PASS


def test_answering_when_refusal_expected_fails_with_definition_layer(suite):
    """强行作答记 FAIL 并归因口径层——即使数值碰巧正确也算失败。"""
    report = run_suite(suite, "C2")
    got = {r["id"]: r for r in report["results"]}
    assert got["S-C2-002"]["status"] == FAIL
    assert "口径层" in got["S-C2-002"]["attribution"]


def test_wrong_refusal_code_fails(tmp_path):
    """拒答对了但理由码不符，仍是 FAIL。"""
    from eval.run import judge_refusal_case
    from semantic_layer.resolve import Refusal, RefusalCode

    case = {
        "id": "X-1",
        "category": "C2",
        "judging": {"refusal_expected": True, "refusal_code": "METRIC_NOT_DEFINED"},
    }
    outcome = Refusal(RefusalCode.UNDEFINED_CONDITION_HIT, "别的理由")
    result = judge_refusal_case(case, outcome, Refusal)
    assert result.status == FAIL
    assert "理由码不符" in result.detail
    assert "口径层" in result.layers


# --------------------------------------------------------------------------
# 未执行 ≠ 通过
# --------------------------------------------------------------------------


def test_unselected_category_is_not_run_not_pass(suite):
    report = run_suite(suite, "C1")
    for r in report["results"]:
        assert r["status"] == NOT_RUN
        assert r["status"] != PASS


def test_report_marks_not_run_and_never_passes_them(suite):
    text = render(run_suite(suite, "C1"))
    assert text.count(NOT_RUN) >= 1
    for line in text.splitlines():
        if NOT_RUN in line:
            assert PASS not in line


def test_phase1_incapable_categories_are_not_run(tmp_path):
    """C1/C3/C4/C5 在 Phase 1 无执行能力，必须 NOT_RUN 而不是 PASS。"""
    suite = tmp_path / "s"
    (suite / "cases").mkdir(parents=True)
    (suite / "cases" / "A.yaml").write_text(
        "id: A\ncategory: C4\nquestion: x\nexpected: {}\n", encoding="utf-8"
    )
    import hashlib

    h = hashlib.sha256((suite / "cases" / "A.yaml").read_bytes()).hexdigest()
    (suite / "SHA256SUMS").write_text(f"{h} *cases/A.yaml\n", encoding="utf-8")
    report = run_suite(suite, None)
    assert report["results"][0]["status"] == NOT_RUN
    assert report["by_category"]["C4"]["status"] == NOT_RUN


def test_metrics_use_na_not_zero_for_unavailable(suite):
    """未具备条件的指标标 N/A，不填 0 —— 0 会被读成「测了但很差」。"""
    m = run_suite(suite, "C2")["metrics"]
    assert "N/A" in m["答案正确率"]
    assert "N/A" in m["引用可定位率"]


# --------------------------------------------------------------------------
# §2.2 作废通道
# --------------------------------------------------------------------------


def _suite_with(tmp_path, cases: list[str]):
    import hashlib

    suite = tmp_path / "s"
    (suite / "cases").mkdir(parents=True)
    lines = []
    for i, body in enumerate(cases):
        p = suite / "cases" / f"C{i}.yaml"
        p.write_text(body, encoding="utf-8")
        lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()} *cases/C{i}.yaml")
    (suite / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return suite


def test_voided_case_leaves_denominator_but_is_listed(tmp_path):
    """§2.2 修订：构造错误作废**移出分母**，但必须公开列出，不静默消失。"""
    suite = _suite_with(
        tmp_path,
        [
            "id: V1\ncategory: C2\nvoided: 题面歧义到无唯一解\nquestion: x\nexpected: {}\n",
            "id: G1\ncategory: C2\nquestion: x\n"
            "expected: {target_name: __nope__}\n"
            "judging: {refusal_expected: true, refusal_code: METRIC_NOT_DEFINED}\n",
        ],
    )
    report = run_suite(suite, "C2")
    assert report["counts"]["voided"] == 1
    assert report["counts"]["scored_denominator"] == 1, "作废题不应留在计分分母里"
    assert [c["id"] for c in report["voided_cases"]] == ["V1"]
    assert "V1" in render(report)


def test_void_ratio_over_limit_flags_batch_failure(tmp_path):
    """作废率 > 10% ⇒ 整批判为构造失败。挑几题剔掉再报分数就是粉饰。"""
    cases = ["id: V1\ncategory: C2\nvoided: 构造错误\nquestion: x\nexpected: {}\n"]
    for i in range(5):
        cases.append(
            f"id: G{i}\ncategory: C2\nquestion: x\n"
            "expected: {target_name: __nope__}\n"
            "judging: {refusal_expected: true, refusal_code: METRIC_NOT_DEFINED}\n"
        )
    report = run_suite(_suite_with(tmp_path, cases), "C2")
    assert report["void_ratio"] > 0.10
    assert report["void_ratio_within_limit"] is False
    assert "已超限" in render(report)


def test_c2_gate_does_not_hold_with_too_few_survivors(tmp_path):
    """作废到只剩 1 题再报 100% 是钻空子，§7 第 2 条堵的就是这个。"""
    cases = [
        "id: G0\ncategory: C2\nquestion: x\n"
        "expected: {target_name: __nope__}\n"
        "judging: {refusal_expected: true, refusal_code: METRIC_NOT_DEFINED}\n",
        "id: V1\ncategory: C2\nvoided: 构造错误\nquestion: x\nexpected: {}\n",
        "id: V2\ncategory: C2\nvoided: 构造错误\nquestion: x\nexpected: {}\n",
    ]
    report = run_suite(_suite_with(tmp_path, cases), "C2")
    gate = report["c2_refusal_gate"]
    assert gate["accuracy"] == "1/1"
    assert gate["gate_holds"] is False, "存活题数不足时不许宣称门成立"
    assert "不成立" in gate["gate_note"]


def test_c2_gate_holds_with_enough_survivors(suite, tmp_path):
    cases = [
        f"id: G{i}\ncategory: C2\nquestion: x\n"
        "expected: {target_name: __nope__}\n"
        "judging: {refusal_expected: true, refusal_code: METRIC_NOT_DEFINED}\n"
        for i in range(4)
    ]
    gate = run_suite(_suite_with(tmp_path, cases), "C2")["c2_refusal_gate"]
    assert gate["accuracy"] == "4/4"
    assert gate["gate_holds"] is True


# --------------------------------------------------------------------------
# 与冻结套件的隔离
# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# §2.1 冻结前置门禁：未过机器校验的内容不许进冻结集
# --------------------------------------------------------------------------


def _pregate_suite(tmp_path, case_body: str, fixture: str | None = None):
    suite = tmp_path / "s"
    (suite / "cases").mkdir(parents=True)
    (suite / "fixtures").mkdir(parents=True)
    (suite / "cases" / "A.yaml").write_text(case_body, encoding="utf-8")
    if fixture:
        (suite / "fixtures" / f"{fixture}.yaml").write_text("rows: []\n", encoding="utf-8")
    return suite


_GOOD_C2 = (
    'id: A\ncategory: C2\nfrozen_at: ""\nquestion: x\n'
    "expected: {target_name: __definitely_absent__}\n"
    "required_evidence: [data_source]\n"
    "judging: {refusal_expected: true, refusal_code: METRIC_NOT_DEFINED}\n"
)


def test_pregate_passes_on_wellformed_case(tmp_path):
    from eval.freeze import pregate

    assert pregate(_pregate_suite(tmp_path, _GOOD_C2)) == []


def test_pregate_catches_invalid_yaml(tmp_path):
    """POC-01 的教训：那份定义冻结之后才被发现不是合法 YAML。"""
    from eval.freeze import pregate

    # 用 POC-01 那份文件的**真实形状**：序列项以双引号开头，闭合引号后还有内容。
    # 作者想给「营业收入」加强调引号，YAML 把前导引号当成完整标量后撞见多余内容。
    body = 'id: A\ncategory: C2\npitfalls:\n  - "营业收入"与"营业总收入"不是同一项目\n'
    problems = pregate(_pregate_suite(tmp_path, body))
    assert any("不是合法 YAML" in p for p in problems)


def test_pregate_catches_missing_required_key(tmp_path):
    from eval.freeze import pregate

    problems = pregate(_pregate_suite(tmp_path, "id: A\ncategory: C2\nquestion: x\n"))
    assert any("缺必填字段" in p for p in problems)


def test_pregate_rejects_c2_target_that_actually_exists(tmp_path):
    """靶子是软柿子就等于没考——C2 引用的指标必须**真的**不存在。"""
    from eval.freeze import pregate

    body = _GOOD_C2.replace("__definitely_absent__", "毛利率")
    problems = pregate(_pregate_suite(tmp_path, body))
    assert any("在语义层中**存在**" in p for p in problems)


def test_pregate_rejects_nonexistent_metric_id(tmp_path):
    from eval.freeze import pregate

    body = (
        'id: A\ncategory: C1\nfrozen_at: ""\nquestion: x\n'
        "expected: {metric_id: no_such_metric_at_all}\n"
        "required_evidence: [data_source]\njudging: {correctness: exact}\n"
    )
    problems = pregate(_pregate_suite(tmp_path, body))
    assert any("不存在" in p for p in problems)


def test_pregate_rejects_missing_fixture(tmp_path):
    from eval.freeze import pregate

    body = (
        'id: A\ncategory: C3\nfrozen_at: ""\nquestion: x\n'
        "expected: {metric_id: gross_profit_margin, fixture: nope}\n"
        "required_evidence: [data_source]\njudging: {correctness: exact}\n"
    )
    problems = pregate(_pregate_suite(tmp_path, body))
    assert any("夹具不存在" in p for p in problems)


def test_pregate_catches_duplicate_ids(tmp_path):
    from eval.freeze import pregate

    suite = _pregate_suite(tmp_path, _GOOD_C2)
    (suite / "cases" / "B.yaml").write_text(_GOOD_C2, encoding="utf-8")
    assert any("重复" in p for p in pregate(suite))


def test_freeze_refuses_when_pregate_fails(tmp_path, monkeypatch, capsys):
    """门禁不过就拒绝冻结，且不写任何 SHA256SUMS。"""
    import eval.freeze as fz

    suite = _pregate_suite(tmp_path, "id: A\ncategory: C2\nquestion: x\n")
    monkeypatch.setattr(fz, "EVAL_ROOT", suite.parent)
    code = fz.main(["--suite", suite.name])
    assert code == 1
    assert "拒绝冻结" in capsys.readouterr().err
    assert not (suite / "SHA256SUMS").exists()


def test_freeze_fills_one_timestamp_then_hashes(tmp_path, monkeypatch):
    """顺序不能反：先填 frozen_at 再算哈希，否则清单立刻失效。"""
    import eval.freeze as fz
    from eval.run import verify_freeze

    suite = _pregate_suite(tmp_path, _GOOD_C2, fixture="f")
    (suite / "cases" / "B.yaml").write_text(_GOOD_C2.replace("id: A", "id: B"), encoding="utf-8")
    monkeypatch.setattr(fz, "EVAL_ROOT", suite.parent)
    assert fz.main(["--suite", suite.name]) == 0

    stamps = set()
    for p in (suite / "cases").glob("*.yaml"):
        stamps.add(yaml_load(p)["frozen_at"])
    assert len(stamps) == 1 and stamps != {""}, "全部题面须为同一个非空时间戳"

    ok, problems = verify_freeze(suite)
    assert ok, problems


def test_freeze_refuses_to_refreeze(tmp_path, monkeypatch, capsys):
    import eval.freeze as fz

    suite = _pregate_suite(tmp_path, _GOOD_C2, fixture="f")
    monkeypatch.setattr(fz, "EVAL_ROOT", suite.parent)
    assert fz.main(["--suite", suite.name]) == 0
    assert fz.main(["--suite", suite.name]) == 1
    assert "拒绝重复冻结" in capsys.readouterr().err


def yaml_load(path: Path) -> dict:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_this_file_does_not_reference_frozen_suite():
    """自指断言：本测试文件不得把冻结套件当作**代码里的路径**使用。

    散文里提到它是可以的（上面的模块 docstring 就在解释为什么不用它）；
    禁的是字符串字面量形式的引用——那才会真的去读冻结集。
    """
    text = Path(__file__).read_text(encoding="utf-8")
    frozen = "frozen" + "-01"
    for literal in (f'"{frozen}"', f"'{frozen}'", f"/{frozen}/"):
        assert literal not in text, (
            f"测试不得以代码路径形式引用冻结套件（发现 {literal}）——"
            "否则冻结集一变测试就红，人就会有动机去改冻结集"
        )
