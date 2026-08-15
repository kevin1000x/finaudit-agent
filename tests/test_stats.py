"""陷阱元规则占比统计（PROJECT_SPEC.md §5.1 的监控出口）。

§5.1 原话：「监控指标：Phase 1 结束时统计 `advisory_only` 占比。> 50% 视为元规则失效，
须重新设计而非接受现状。」阈值语义是**严格大于**，等于 50% 不算失效——测试逐条锁住这一点，
因为「>」被写成「>=」是最容易发生也最难看出来的一种漂移。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from semantic_layer.stats import collect_pitfall_stats  # noqa: E402
from semantic_layer.__main__ import main  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


def _write(directory: Path, name: str, pitfalls: str) -> Path:
    path = directory / name
    path.write_text(f"metric_id: {name[:-5]}\ncommon_pitfalls:\n{pitfalls}", encoding="utf-8")
    return path


ONE_OF_THREE_ADVISORY = """\
  - text: 甲
    enforced_by: flags.restated
  - text: 乙
    enforced_by: source_fields.id
  - text: 丙
    advisory_only: true
"""

ALL_ENFORCED = """\
  - text: 甲
    enforced_by: flags.restated
  - text: 乙
    enforced_by: source_fields.id
"""

HALF_ADVISORY = """\
  - text: 甲
    enforced_by: flags.restated
  - text: 乙
    advisory_only: true
"""

THREE_OF_FIVE_ADVISORY = """\
  - text: 甲
    advisory_only: true
  - text: 乙
    advisory_only: true
  - text: 丙
    advisory_only: true
  - text: 丁
    enforced_by: flags.restated
  - text: 戊
    enforced_by: source_fields.id
"""


def test_ratio_one_third(tmp_path):
    _write(tmp_path, "a.yaml", ONE_OF_THREE_ADVISORY)
    stats = collect_pitfall_stats(tmp_path)
    assert stats.total == 3
    assert stats.enforced == 2
    assert stats.advisory == 1
    assert stats.advisory_ratio == pytest.approx(1 / 3)


def test_ratio_zero_when_all_enforced(tmp_path):
    _write(tmp_path, "a.yaml", ALL_ENFORCED)
    assert collect_pitfall_stats(tmp_path).advisory_ratio == 0.0


def test_no_pitfalls_does_not_divide_by_zero(tmp_path):
    (tmp_path / "a.yaml").write_text("metric_id: a\n", encoding="utf-8")
    stats = collect_pitfall_stats(tmp_path)
    assert stats.total == 0
    assert stats.advisory_ratio == 0.0


def test_per_metric_breakdown_present(tmp_path):
    """只有总计看不出是哪几份定义在拉高占比，而 §5.1 说超阈值要「重新设计」——
    重新设计的前提是知道该看哪几份。"""
    _write(tmp_path, "clean.yaml", ALL_ENFORCED)
    _write(tmp_path, "loose.yaml", THREE_OF_FIVE_ADVISORY)
    stats = collect_pitfall_stats(tmp_path)
    assert set(stats.per_metric) == {"clean", "loose"}
    assert stats.per_metric["clean"].advisory_ratio == 0.0
    assert stats.per_metric["loose"].advisory_ratio == pytest.approx(0.6)


def test_vocabulary_file_excluded(tmp_path):
    _write(tmp_path, "a.yaml", ALL_ENFORCED)
    (tmp_path / "_flags.yaml").write_text("vocabulary_version: 1\nflags: []\n", encoding="utf-8")
    assert set(collect_pitfall_stats(tmp_path).per_metric) == {"a"}


def test_explicit_paths_accepted(tmp_path):
    """01-06 要对「本批次的显式路径列表」统计，避免读到别的批次的半成品。"""
    a = _write(tmp_path, "a.yaml", ALL_ENFORCED)
    _write(tmp_path, "b.yaml", THREE_OF_FIVE_ADVISORY)
    stats = collect_pitfall_stats(tmp_path, paths=[a])
    assert set(stats.per_metric) == {"a"}
    assert stats.total == 2


def test_pitfall_with_neither_marker_counts_as_enforced_nowhere(tmp_path):
    """既无 enforced_by 又无 advisory_only 的条目是 R8 不合规，
    这里只统计不判定——但它不能被算进 advisory，否则占比会虚低、掩盖问题。"""
    _write(tmp_path, "a.yaml", "  - text: 甲\n")
    stats = collect_pitfall_stats(tmp_path)
    assert stats.total == 1
    assert stats.advisory == 0
    assert stats.enforced == 0
    assert stats.unclassified == 1


# --------------------------------------------------------------------------
# 阈值语义：严格大于
# --------------------------------------------------------------------------


def test_fail_over_exactly_at_threshold_passes(tmp_path, capsys):
    _write(tmp_path, "a.yaml", HALF_ADVISORY)
    code = main(["stats", "--metrics-dir", str(tmp_path), "--fail-over", "0.5"])
    capsys.readouterr()
    assert code == 0, "占比恰为 0.5 时不该失败——§5.1 写的是「> 50%」"


def test_fail_over_above_threshold_fails(tmp_path, capsys):
    _write(tmp_path, "a.yaml", THREE_OF_FIVE_ADVISORY)
    code = main(["stats", "--metrics-dir", str(tmp_path), "--fail-over", "0.5"])
    capsys.readouterr()
    assert code == 1


def test_without_fail_over_always_exits_zero(tmp_path, capsys):
    _write(tmp_path, "a.yaml", THREE_OF_FIVE_ADVISORY)
    code = main(["stats", "--metrics-dir", str(tmp_path)])
    capsys.readouterr()
    assert code == 0, "未给 --fail-over 时是纯查看模式"


def test_text_output_sorted_by_ratio_desc(tmp_path, capsys):
    _write(tmp_path, "clean.yaml", ALL_ENFORCED)
    _write(tmp_path, "loose.yaml", THREE_OF_FIVE_ADVISORY)
    _write(tmp_path, "mid.yaml", HALF_ADVISORY)
    main(["stats", "--metrics-dir", str(tmp_path)])
    out = capsys.readouterr().out
    assert out.index("loose") < out.index("mid") < out.index("clean")


def test_json_output_has_required_keys(tmp_path, capsys):
    import json

    _write(tmp_path, "a.yaml", ONE_OF_THREE_ADVISORY)
    main(["stats", "--metrics-dir", str(tmp_path), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert {"total", "enforced", "advisory", "advisory_ratio", "per_metric"} <= set(payload)


def test_real_repository_under_threshold(capsys):
    code = main(["stats", "--metrics-dir", str(REPO_ROOT / "metrics"), "--fail-over", "0.5"])
    capsys.readouterr()
    assert code == 0
