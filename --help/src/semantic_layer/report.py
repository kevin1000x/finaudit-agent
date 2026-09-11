"""Finding 的渲染。

text 渲染有一条硬要求：`enforced_by` 用下标指向 `undefined_conditions` 时，
必须把**被引用条目的原文**一并打印。下标形式的已知代价是重排列表会静默指向别处，
让复核者在报告里看见承载体本身而不是一个数字，是对这条代价的缓解（见 01-01-PLAN.md）。
"""

from __future__ import annotations

import json
from pathlib import Path

from .definition import MetricDefinition
from .validate import Finding

__all__ = ["render_text", "render_json"]


def render_text(results: dict[str, list[Finding]], definitions: dict[str, MetricDefinition] | None = None) -> str:
    lines: list[str] = []
    total = 0
    for path, findings in results.items():
        name = Path(path).name
        if not findings:
            lines.append(f"OK    {name}")
            continue
        total += len(findings)
        lines.append(f"FAIL  {name}  ({len(findings)} 项)")
        for f in findings:
            lines.append(f"        [{f.code}] {f.where}")
            lines.append(f"          {f.message}")
            extra = _referenced_source(f, (definitions or {}).get(path))
            for line in extra:
                lines.append(f"          ↳ {line}")
    lines.append("")
    lines.append(f"合计 {total} 项不合规，涉及 {sum(1 for v in results.values() if v)} / {len(results)} 份定义")
    return "\n".join(lines)


def _referenced_source(finding: Finding, defn: MetricDefinition | None) -> list[str]:
    """把 enforced_by 指向的承载体原文带出来，避免报告里只剩一个下标。"""
    if defn is None or not finding.where:
        return []
    out: list[str] = []
    for idx, pf in enumerate(defn.common_pitfalls):
        if f"common_pitfalls[{idx}]" not in finding.where:
            continue
        ref = str(pf.enforced_by or "")
        if ref.startswith("undefined_conditions."):
            tail = ref.split(".", 1)[1]
            if tail.isdigit() and int(tail) < len(defn.undefined_conditions):
                uc = defn.undefined_conditions[int(tail)]
                out.append(f"{ref} → expr: {uc.expr}")
                out.append(f"{' ' * len(ref)}   reason: {uc.reason}")
        elif ref.startswith("flags."):
            name = ref.split(".", 1)[1]
            for fd in defn.flags:
                if fd.name == name:
                    out.append(f"{ref} → trigger: {fd.trigger}")
    return out


def render_json(results: dict[str, list[Finding]]) -> str:
    payload = {
        "findings": [
            {"path": path, **f.to_dict()} for path, findings in results.items() for f in findings
        ],
        "summary": {
            "definitions_checked": len(results),
            "definitions_failing": sum(1 for v in results.values() if v),
            "findings_total": sum(len(v) for v in results.values()),
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
