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

from .crosscheck import (
    CrossCheckVerdict,
    cross_validate_batch,
    fetch_reference,
    load_all_akshare_mappings,
    load_reference_payload,
    references_from_payload,
)
from .download import UnknownStockCode, fetch_annual_report
from .formula import compute_metrics
from .mapping import load_pdf_mapping
from .pipeline import DEFAULT_EXTRACTION_PLAN, MappingZeroHit, extract_batch
from .reconcile import check_column_binding, reconcile_batch


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

    c = sub.add_parser("compute", help="过勾稽闸门后算指标，输出完整证据链")
    c.add_argument(
        "--metric",
        required=True,
        action="append",
        dest="metrics",
        help="指标 id 或别名，例如 debt_to_asset_ratio。**可重复**，一次算多个",
    )
    c.add_argument("--stock", required=True)
    c.add_argument("--year", required=True, type=int)
    c.add_argument(
        "--namespace",
        default=None,
        help="只抽一张表时用；不给则按三张合并报表全抽（跨表指标需要）",
    )
    c.add_argument("--statement", default=None)
    c.add_argument("--metrics-dir", default="metrics")
    c.add_argument("--pdf", default=None, help="用本地 PDF 复跑，不联网")
    c.add_argument("--json", action="store_true", dest="as_json")

    x = sub.add_parser(
        "crosscheck",
        help="拿 AKShare 作对照源核 PDF 抽取值。**只产出判定，不改写任何值**（D-013）",
    )
    x.add_argument("--stock", required=True)
    x.add_argument("--year", required=True, type=int)
    x.add_argument("--pdf", default=None, help="用本地 PDF 复跑，不联网")
    x.add_argument(
        "--reference",
        default=None,
        metavar="PATH",
        help="读一份录制好的 AKShare 响应做回放。**默认就该给这个** —— 不给才联网",
    )
    x.add_argument(
        "--record",
        default=None,
        metavar="PATH",
        help=(
            "联网取一份真实响应并写成固件。"
            "**这是全仓唯一会 import akshare 并发网络请求的入口**"
        ),
    )
    x.add_argument("--json", action="store_true", dest="as_json")

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

    # 闸门对**一次抽取批次整体**跑一次，结果写进批次元数据，随后批次闩死（D-018 / L-13）。
    gate = reconcile_batch(batch)
    payload = {
        "batch_id": batch.batch_id,
        "entity": batch.entity,
        "period": batch.period,
        "pdf_sha256": batch.pdf_sha256,
        "mapping_namespace": args.namespace,
        "statement": args.statement,
        "reconciliation": gate.to_dict(),
        "sealed": batch.sealed,
        "records": [r.to_dict() for r in batch.records],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _cmd_compute(args) -> int:
    """`extract` → 闸门 → 封闭算术解析器 → 证据链 JSON。**抽取路径与计算路径是同一条。**

    cninfo 的病根是这两条路径不相交（`pipeline.py:758` 硬编码空报表字典，
    计算侧从不读它）。这里 `compute_metric` 的唯一输入就是 `extract_batch` 的产物，
    没有第二条路。
    """
    single = args.namespace is not None or args.statement is not None
    plan = None if single else DEFAULT_EXTRACTION_PLAN
    try:
        batch = extract_batch(
            args.stock,
            args.year,
            namespace=args.namespace or "bs",
            statement=args.statement or "合并资产负债表",
            pdf_path=args.pdf,
            plan=plan,
        )
    except (UnknownStockCode, MappingZeroHit, ValueError) as exc:
        print(f"调用错误：{exc}", file=sys.stderr)
        return 2
    if isinstance(batch, Refusal):
        return _print_refusal(batch, args.as_json)

    gate = reconcile_batch(batch)
    # 两道闸门**并列跑，都留证**：勾稽证明「同一列内部自洽」，
    # 列绑定证明「取的是对的那一列」。二者不可互相替代（A-9 / D-016 补充节）。
    namespaces = [ns for ns, _ in plan] if plan else [args.namespace or "bs"]
    bindings = {
        ns: check_column_binding(batch, load_pdf_mapping(ns), args.year)
        for ns in namespaces
    }
    results = compute_metrics(args.metrics, batch, args.metrics_dir)

    payloads = []
    refused = 0
    for outcome in results:
        if isinstance(outcome, Refusal):
            refused += 1
            payloads.append(outcome.to_dict())
            continue
        item = outcome.to_dict()
        item["reconciliation"] = gate.to_dict()
        item["column_binding"] = {ns: r.to_dict() for ns, r in bindings.items()}
        payloads.append(item)

    if args.as_json:
        print(json.dumps(payloads, ensure_ascii=False, indent=2))
    else:
        for outcome in results:
            if isinstance(outcome, Refusal):
                print(f"拒答 [{outcome.code.name}] {outcome.metric_id}：{outcome.detail}")
            else:
                print(f"{outcome.metric_id} = {outcome.value}（{outcome.unit}）")
    # **一个拒答不让整批退出码变成 0**：拒答是正确行为，但调用方要看得见。
    return 3 if refused and refused == len(results) else 0


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


def _cmd_crosscheck(args) -> int:
    """`extract` → 对照 → 判定 JSON。**PDF 侧的值一个字节都不改。**

    退出码沿用本文件顶部的约定。⚠️ **对照源取不到时退 3 而不是 0**：
    「这一批没有对照结论」与「这一批对照通过了」在证据上是两件事，
    退 0 会让下游脚本把前者读成后者。
    """
    try:
        batch = extract_batch(
            args.stock,
            args.year,
            namespace="bs",
            statement="合并资产负债表",
            pdf_path=args.pdf,
            plan=DEFAULT_EXTRACTION_PLAN,
        )
    except (UnknownStockCode, MappingZeroHit, ValueError) as exc:
        print(f"调用错误：{exc}", file=sys.stderr)
        return 2
    if isinstance(batch, Refusal):
        return _print_refusal(batch, args.as_json)

    if args.record:
        payload = fetch_reference(args.stock, args.year)
        if isinstance(payload, Refusal):
            return _print_refusal(payload, args.as_json)
        Path(args.record).write_text(
            json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        print(f"已写出固件：{args.record}", file=sys.stderr)
    elif args.reference:
        payload = load_reference_payload(args.reference)
    else:
        payload = fetch_reference(args.stock, args.year)
        if isinstance(payload, Refusal):
            return _print_refusal(payload, args.as_json)

    tables = load_all_akshare_mappings()
    references = references_from_payload(payload, tables)
    outcome = cross_validate_batch(batch, references, period=f"{args.year}1231")

    if args.as_json:
        print(json.dumps(outcome.to_dict(), ensure_ascii=False, indent=2))
    else:
        for result in outcome.results:
            if result.verdict is CrossCheckVerdict.INCOMPARABLE:
                detail = result.incomparable_reason.name
            else:
                detail = f"差 {result.difference}"
            print(f"{result.field_id:<52} {result.verdict.name:<13} {detail}")
        print(outcome.note)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "fetch":
        return _cmd_fetch(args)
    if args.command == "extract":
        return _cmd_extract(args)
    if args.command == "compute":
        return _cmd_compute(args)
    if args.command == "crosscheck":
        return _cmd_crosscheck(args)
    raise AssertionError(f"未接线的子命令：{args.command!r}")


if __name__ == "__main__":
    raise SystemExit(main())
