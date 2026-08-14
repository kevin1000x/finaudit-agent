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


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "validate":
        return _cmd_validate(args)
    if args.command == "resolve":
        return _cmd_resolve(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
