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

from .definition import is_definition_file, iter_definition_paths, load_definition
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

    r = sub.add_parser("resolve", help="按指标名解析口径定义并给出机读拒答（AC-02）")
    r.add_argument("name")
    r.add_argument("--metrics-dir", default="metrics")
    r.add_argument(
        "--row",
        default=None,
        metavar="PATH#KEY",
        help="一行数据的 YAML 文件与顶层键，例如 tests/fixtures/row_minimal.yaml#complete",
    )
    r.add_argument("--json", action="store_true", dest="as_json")

    s = sub.add_parser("scan", help="非公开数据扫描（AC-10 / D-010）")
    s.add_argument("--root", default=".", help="仓库根目录")
    s.add_argument("--rules", default=None, help="规则文件；省略则用 scan_rules.yaml")
    s.add_argument("--json", action="store_true", dest="as_json")

    # `N-20`：定义对机器可读不等于对人可读。2026-09-03 操作者读随机两份，答读不懂。
    # 判据要的是**换一种表达形式**，不是补一份说明文档 —— 见 `explain.py`。
    e = sub.add_parser("explain", help="把一份口径定义讲给人听（N-20 的表达形式）")
    e.add_argument("metric", help="metric_id 或定义文件路径")
    e.add_argument("--metrics-dir", default="metrics")

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


def _cmd_explain(args) -> int:
    from .explain import render_explanation

    target = Path(args.metric)
    if not target.exists():
        target = Path(args.metrics_dir) / f"{args.metric}.yaml"
    if not target.exists():
        # 不做模糊匹配：猜错一份定义比找不到更糟 —— 读者会以为自己读的是另一个指标。
        print(f"找不到定义：{args.metric}（试过 {target}）", file=sys.stderr)
        return 2
    if not is_definition_file(target):
        # 渲染一份空壳比报错更糟：读者会以为自己读到了一份「什么都没声明」的定义。
        print(
            f"{target.name} 是共享注册表，不是指标定义，没有可讲的口径",
            file=sys.stderr,
        )
        return 2

    defn = load_definition(target)
    if defn.parse_error:
        print(f"这份定义解析不了，先跑 validate：{defn.parse_error}", file=sys.stderr)
        return 2
    print(render_explanation(defn, _flag_descriptions(args.metrics_dir)))
    return 0


def _flag_descriptions(metrics_dir: Path | str) -> dict:
    """`metrics/_flags.yaml` 的 `name -> description`。

    有它，可比性标记才能在人读输出里显示成中文而不是 `basis_version_mismatch`。
    读不到就返回空字典 —— 上游会退回打原名，**不编中文**。
    """
    import yaml

    path = Path(metrics_dir) / "_flags.yaml"
    if not path.is_file():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {
        f["name"]: f["description"]
        for f in raw.get("flags", [])
        if isinstance(f, dict) and f.get("name") and f.get("description")
    }


def _load_row(spec: str) -> dict:
    """`path#key` → 该 YAML 文件里 key 对应的一行数据。键不存在是调用错误。"""
    import yaml

    raw_path, _, key = spec.partition("#")
    data = yaml.safe_load(Path(raw_path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise KeyError(f"{raw_path}：顶层必须是映射")
    if not key:
        return data
    if key not in data:
        raise KeyError(f"{raw_path}：没有顶层键 {key!r}，可选 {sorted(data)}")
    return data[key]


def _cmd_resolve(args) -> int:
    """退出码：0 已解析 / **3 业务拒答** / 2 调用错误。

    拒答用 3 而非 2：2 已被 `validate` 用作「没找到定义文件」这类调用错误，
    而拒答是**正常业务结果**（D-003：拒答是正确行为不是降级）。
    两者必须可区分，否则 01-07 的评测脚本无法判别「系统正确拒答」与「命令没跑起来」。
    见 docs/agent/phase-01/open-questions.md OQ-03。
    """
    from .resolve import (
        Refusal,
        Registry,
        active_flags,
        comparison_scoped_flags,
        evaluate_refusal,
        render_refusal,
    )

    try:
        registry = Registry.load(args.metrics_dir)
    except ValueError as exc:
        print(f"词表或定义目录不可用：{exc}", file=sys.stderr)
        return 2

    outcome = registry.resolve(args.name)
    if isinstance(outcome, Refusal):
        print(render_refusal(outcome, as_json=args.as_json))
        return 3

    deferred = comparison_scoped_flags(outcome)
    if args.row is None:
        print(render_refusal(outcome, as_json=args.as_json, deferred=deferred))
        return 0

    try:
        row = _load_row(args.row)
    except (OSError, KeyError) as exc:
        print(f"行数据不可用：{exc}", file=sys.stderr)
        return 2

    refusal = evaluate_refusal(outcome, row)
    if refusal is not None:
        print(render_refusal(refusal, as_json=args.as_json))
        return 3

    flags = active_flags(outcome, row)
    if isinstance(flags, Refusal):
        print(render_refusal(flags, as_json=args.as_json))
        return 3

    print(render_refusal(outcome, as_json=args.as_json, active=flags, deferred=deferred))
    return 0


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
    if args.command == "explain":
        return _cmd_explain(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
