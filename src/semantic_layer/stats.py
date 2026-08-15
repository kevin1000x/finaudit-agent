"""陷阱元规则的占比统计（PROJECT_SPEC.md §5.1 的监控出口）。

§5.1 的元规则要求每条 `common_pitfalls` 要么有 `enforced_by`，要么标 `advisory_only`。
它自带一个自我监控条款：

> 监控指标：Phase 1 结束时统计 `advisory_only` 占比。**> 50% 视为元规则失效**，
> 须重新设计而非接受现状。

本模块把它变成可执行的数。两处刻意的设计：

1. **阈值是严格大于。** 等于 50% 不算失效，与 §5.1 逐字一致。
2. **必须给出按定义的分项。** 只报总计的话，超阈值时不知道该重新设计哪几份——
   而 §5.1 要求的正是重新设计，不是接受现状。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .definition import iter_definition_paths, load_definition

__all__ = ["MetricPitfallStats", "PitfallStats", "collect_pitfall_stats"]


@dataclass(frozen=True)
class MetricPitfallStats:
    total: int
    enforced: int
    advisory: int
    unclassified: int

    @property
    def advisory_ratio(self) -> float:
        return self.advisory / self.total if self.total else 0.0


@dataclass(frozen=True)
class PitfallStats:
    total: int
    enforced: int
    advisory: int
    unclassified: int
    per_metric: dict = field(default_factory=dict)

    @property
    def advisory_ratio(self) -> float:
        return self.advisory / self.total if self.total else 0.0

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "enforced": self.enforced,
            "advisory": self.advisory,
            "unclassified": self.unclassified,
            "advisory_ratio": self.advisory_ratio,
            "per_metric": {
                name: {
                    "total": s.total,
                    "enforced": s.enforced,
                    "advisory": s.advisory,
                    "unclassified": s.unclassified,
                    "advisory_ratio": s.advisory_ratio,
                }
                for name, s in self.per_metric.items()
            },
        }

    def sorted_metrics(self) -> list[tuple[str, MetricPitfallStats]]:
        """按 advisory_ratio 降序——「是哪几份定义在把陷阱标成仅供参考」要一眼可见。"""
        return sorted(
            self.per_metric.items(), key=lambda kv: (-kv[1].advisory_ratio, kv[0])
        )


def collect_pitfall_stats(
    metrics_dir: Path | str = "metrics", paths: list[Path] | None = None
) -> PitfallStats:
    """统计口径是**陷阱条目数**，不是定义份数——与 §5.1 措辞一致，不自行换算。

    `paths` 用于只统计一批显式给出的定义：wave 3 的三个批次并行写 metrics/，
    全目录统计会读到别的批次尚未写完的半成品。
    """
    targets = list(paths) if paths is not None else iter_definition_paths(metrics_dir)

    per_metric: dict[str, MetricPitfallStats] = {}
    total = enforced = advisory = unclassified = 0

    for path in targets:
        defn = load_definition(path)
        m_enforced = m_advisory = m_unclassified = 0
        for pitfall in defn.common_pitfalls:
            if pitfall.advisory_only:
                m_advisory += 1
            elif pitfall.enforced_by:
                m_enforced += 1
            else:
                # 二者皆无 = R8 不合规。这里只统计不判定，但**不能算进 advisory**，
                # 否则占比虚低，反而掩盖问题。
                m_unclassified += 1
        name = defn.metric_id or Path(path).stem
        per_metric[name] = MetricPitfallStats(
            total=m_enforced + m_advisory + m_unclassified,
            enforced=m_enforced,
            advisory=m_advisory,
            unclassified=m_unclassified,
        )
        total += per_metric[name].total
        enforced += m_enforced
        advisory += m_advisory
        unclassified += m_unclassified

    return PitfallStats(
        total=total,
        enforced=enforced,
        advisory=advisory,
        unclassified=unclassified,
        per_metric=per_metric,
    )
