"""抽取器 CLI。argparse 风格照抄 `semantic_layer.__main__`（`--json` 用 `dest="as_json"`）。

退出码的约定与 `semantic_layer resolve` 一致，理由也一样（OQ-03）：

- `0` 拿到结果
- `2` **调用错误**（股票代码不认识、映射表写错了 —— 这些属配置缺陷，D-022 决策二）
- `3` **业务拒答**（数据源不可达、版面读不出来 —— `Refusal`，是正确行为不是降级，D-003）

2 与 3 必须可区分，否则评测脚本分不清「系统正确拒答」与「命令没跑起来」。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from semantic_layer.resolve import Refusal

from .download import UnknownStockCode, fetch_annual_report
from .mapping import load_pdf_mapping
from .pipeline import MappingZeroHit, extract_batch


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="extractor", description="年报 PDF 抽取器")
    sub = parser.add_subparsers(dest="command", required=True)

    f = sub.add_parser("fetch", help="从巨潮取回年报全文并给出 SHA-256 与源 URL")
    f.add_argument("--stock", required=True, help="股票代码，例如 600519")
    f.add_argument("--year", required=True, type=int, help="会计年度，例如 2023")
    f.add_argument(
        "--keep-pdf",
        action="store_true",
        dest="keep_pdf",
        help="保留 PDF 到 data/raw/；默认抽完就删（台账 N-3）",
    )
    f.add_argument("--json", action="store_true", dest="as_json")

    e = sub.add_parser("extract", help="定位报表并按映射表取字段，产出带出处的抽取记录")
    e.add_argument("--stock", required=True)
    e.add_argument("--year", required=True, type=int)
    e.add_argument("--namespace", default="bs")
    e.add_argument("--statement", default="合并资产负债表")
    e.add_argument("--pdf", default=None, help="用本地 PDF 复跑，不联网")
    e.add_argument(
        "--dump-view",
        default=None,
        metavar="PATH",
        help="把版面事实（锚点 / 列绑定 / 重组行）写成 JSON 固件，供回归用例使用",
    )
    e.add_argument("--json", action="store_true", dest="as_json")

    return parser


def _print_refusal(refusal: Refusal, as_json: bool) -> int:
    if as_json:
        print(json.dumps(refusal.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"拒答 [{refusal.code.name}] {refusal.detail}（责任方：{refusal.source}）")
    return 3


def _cmd_fetch(args) -> int:
    try:
        result = fetch_annual_report(args.stock, args.year, keep_pdf=args.keep_pdf)
    except UnknownStockCode as exc:
        print(f"调用错误：{exc}", file=sys.stderr)
        return 2
    if isinstance(result, Refusal):
        return _print_refusal(result, args.as_json)
    payload = result.to_dict()
    if not args.keep_pdf:
        payload["pdf_path"] = None
        payload["pdf_retained"] = False
    else:
        payload["pdf_retained"] = True
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _cmd_extract(args) -> int:
    try:
        batch = extract_batch(
            args.stock,
            args.year,
            namespace=args.namespace,
            statement=args.statement,
            pdf_path=args.pdf,
        )
    except (UnknownStockCode, MappingZeroHit, ValueError) as exc:
        print(f"调用错误：{exc}", file=sys.stderr)
        return 2
    if isinstance(batch, Refusal):
        return _print_refusal(batch, args.as_json)

    if args.dump_view is not None:
        _dump_view(args, batch)

    payload = {
        "batch_id": batch.batch_id,
        "entity": batch.entity,
        "period": batch.period,
        "pdf_sha256": batch.pdf_sha256,
        "mapping_namespace": args.namespace,
        "statement": args.statement,
        "records": [r.to_dict() for r in batch.records],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


#: 固件里 `all_label_sequences` 的取值范围。**刻意窄于运行时。**
#:
#: 运行时的 L-36 零命中判定扫**整份 PDF**（`pipeline._all_label_sequences`）。
#: 固件不能照抄那个集合：整份年报的标签序列有两千多条，绝大多数是正文叙述段落，
#: 把它们写进仓库违反威胁登记 T-01.5-04 / T-01.5-07 的处置
#: 「抽取产物固件只存数值行不存原文段落」。
#: 固件因此只收**资产负债表两张表**的行项目标签 —— 全是报表行，没有一行正文。
FIXTURE_LABEL_SCOPE = ("合并资产负债表", "母公司资产负债表")


def _dump_view(args, batch) -> None:
    """重跑一次版面读取并把结果写成固件。

    刻意**不复用** `extract_batch` 内部的 `StatementView`：那样要么把它挂到批次上
    （批次是给计算层看的，塞版面细节进去是给它加一个没人消费的字段），
    要么让 `extract_batch` 多一个只在 dump 时才有意义的返回值。
    固件是开发期产物，多读一遍 PDF 换一个干净的接口，划算。

    写的是**抽取产物**，不是 PDF：`.pdf` 同时在 `.gitignore` 与 `scan_rules.yaml`
    的 `forbidden_tracked_file_types` 里，而 JSON 不在黑名单里。
    """
    import dataclasses

    import pdfplumber

    from .locate import find_statement_anchors
    from .pipeline import read_statement

    if args.pdf is None:
        raise ValueError("--dump-view 需要同时给 --pdf：固件由本地 PDF 生成，避免每次联网重下")
    with pdfplumber.open(args.pdf) as pdf:
        anchors = find_statement_anchors(pdf)
        views = {
            statement: read_statement(pdf, statement, args.year)
            for statement in FIXTURE_LABEL_SCOPE
        }
    view = views[args.statement]
    scoped_labels = frozenset(
        row.label_lines for v in views.values() for row in v.rows
    )
    data = dataclasses.replace(view, all_label_sequences=scoped_labels).to_dict()
    data["anchors"] = [a.to_dict() for a in anchors]
    data["source"] = {
        "stock_code": batch.entity,
        "fiscal_year": batch.period,
        "pdf_sha256": batch.pdf_sha256,
        "statement": args.statement,
        "mapping_version": load_pdf_mapping(args.namespace).mapping_version,
        "label_scope": list(FIXTURE_LABEL_SCOPE),
        "label_scope_note": (
            "固件的 all_label_sequences 只收上列报表的行项目标签，窄于运行时的整份 PDF；"
            "理由见 __main__.FIXTURE_LABEL_SCOPE 的注释（威胁登记 T-01.5-07）。"
        ),
    }
    Path(args.dump_view).write_bytes(
        (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )
    print(f"已写出固件：{args.dump_view}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "fetch":
        return _cmd_fetch(args)
    if args.command == "extract":
        return _cmd_extract(args)
    raise AssertionError(f"未接线的子命令：{args.command!r}")


if __name__ == "__main__":
    raise SystemExit(main())
