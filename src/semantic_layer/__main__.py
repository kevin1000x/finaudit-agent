"""CLI 入口。

`validate` 接受**可选的位置参数路径列表**：给出路径时只校验这些文件。
这不是可选项——wave 3 的三个批次计划并行往 metrics/ 写文件，
只能做全目录校验的话会读到别的批次尚未写完的半成品并误判失败。

退出码：有 Finding 时 1，无则 0。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .definition import iter_definition_paths, load_definition
from .report import render_json, render_text
from .validate import validate_definition
from .vocabulary import DEFAULT_VOCABULARY_PATH, load_vocabulary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="semantic_layer", description="L1 语义层工具")
    sub = parser.add_subparsers(dest="command", required=True)

    v = sub.add_parser("validate", help="按 9 条 Requirement 机械校验口径定义")
    v.add_argument("paths", nargs="*", help="定义文件路径；省略则校验 --metrics-dir 下全部")
    v.add_argument("--metrics-dir", default="metrics")
    v.add_argument("--vocabulary", default=None)
    v.add_argument("--json", action="store_true", dest="as_json")
    v.add_argument(
        "--allow-v1",
        action="store_true",
        help="放宽 R9 的 version >= 2 检查（用于检验 POC-01 的历史样本）",
    )

    r = sub.add_parser("resolve", help="按指标名解析口径定义（Task 2 实现）")
    r.add_argument("name")
    r.add_argument("--metrics-dir", default="metrics")
    r.add_argument("--json", action="store_true", dest="as_json")

    s = sub.add_parser("scan", help="非公开数据扫描（AC-10 / D-010）")
    s.add_argument("--root", default=".", help="仓库根目录")
    s.add_argument("--rules", default=None, help="规则文件；省略则用 scan_rules.yaml")
    s.add_argument("--json", action="store_true", dest="as_json")

    t = sub.add_parser("stats", help="陷阱元规则占比统计（§5.1 监控指标）")
    t.add_argument("paths", nargs="*", help="定义文件路径；省略则统计 --metrics-dir 下全部")
    t.add_argument("--metrics-dir", default="metrics")
    t.add_argument("--json", action="store_true", dest="as_json")
    t.add_argument(
        "--fail-over",
        type=float,
        default=None,
        metavar="RATIO",
        help="advisory_only 占比**严格大于**该值时退出码 1；省略则纯查看，恒退出 0",
    )

    return parser


def _cmd_validate(args) -> int:
    paths = [Path(p) for p in args.paths] or iter_definition_paths(args.metrics_dir)
    if not paths:
        print(f"没有找到任何定义文件（--metrics-dir={args.metrics_dir}）", file=sys.stderr)
        return 2
    vocab_path = Path(args.vocabulary) if args.vocabulary else DEFAULT_VOCABULARY_PATH
    vocab = load_vocabulary(vocab_path)

    results, defs = {}, {}
    for p in paths:
        defn = load_definition(p)
        defs[str(p)] = defn
        results[str(p)] = validate_definition(defn, vocab, require_v2=not args.allow_v1)

    print(render_json(results) if args.as_json else render_text(results, defs))
    return 1 if any(results.values()) else 0


def _cmd_resolve(args) -> int:
    from .resolve import resolve_metric, render_refusal

    outcome = resolve_metric(args.name, metrics_dir=args.metrics_dir)
    print(render_refusal(outcome, as_json=args.as_json))
    return 0 if outcome.resolved else 3


def _cmd_scan(args) -> int:
    import json

    from .scan import DEFAULT_RULES_PATH, ScanRulesError, load_scan_rules, scan_repository

    rules_path = Path(args.rules) if args.rules else Path(args.root) / DEFAULT_RULES_PATH
    try:
        rules = load_scan_rules(rules_path)
        findings = scan_repository(args.root, rules)
    except ScanRulesError as exc:
        # fail-closed：规则不可用不是「没扫到问题」，是「门禁没生效」
        print(f"扫描未能执行：{exc}", file=sys.stderr)
        return 2

    if args.as_json:
        print(
            json.dumps(
                {
                    "rules_version": rules.rules_version,
                    "findings": [
                        {"path": f.path, "rule": f.rule, "detail": f.detail} for f in findings
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    elif findings:
        print(f"扫出 {len(findings)} 项非公开数据风险（规则版本 {rules.rules_version}）：")
        for f in findings:
            print(f"  {f.path}\n    [{f.rule}] {f.detail}")
    else:
        print(f"未扫出非公开数据风险（规则版本 {rules.rules_version}）。")
    return 1 if findings else 0


def _cmd_stats(args) -> int:
    import json

    from .stats import collect_pitfall_stats

    paths = [Path(p) for p in args.paths] or None
    stats = collect_pitfall_stats(args.metrics_dir, paths=paths)

    if args.as_json:
        print(json.dumps(stats.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(
            f"陷阱条目 {stats.total} 条："
            f"enforced {stats.enforced} / advisory {stats.advisory} / 未分类 {stats.unclassified}"
        )
        print(f"advisory_only 占比 {stats.advisory_ratio:.1%}（§5.1 阈值：> 50% 视为元规则失效）")
        if stats.unclassified:
            print(f"⚠ {stats.unclassified} 条既无 enforced_by 又无 advisory_only —— R8 不合规")
        for name, s in stats.sorted_metrics():
            print(f"  {s.advisory_ratio:6.1%}  {name}  （{s.advisory}/{s.total}）")

    if args.fail_over is None:
        return 0
    # 严格大于。§5.1 写的是「> 50%」，等于阈值不算失效。
    return 1 if stats.advisory_ratio > args.fail_over else 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "validate":
        return _cmd_validate(args)
    if args.command == "resolve":
        return _cmd_resolve(args)
    if args.command == "scan":
        return _cmd_scan(args)
    if args.command == "stats":
        return _cmd_stats(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
