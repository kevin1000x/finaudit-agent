#!/usr/bin/env python
"""字段探测器 —— **把原文摆出来，不替人判定**（01.5-02 wave 2）。

## 这不是门禁

它不产生通过/不通过判定，已登记在 `scripts/check_gates.py` 的 `NOT_GATES` 里。
它的产物是给人读的候选行，判定由人做，写进 `docs/agent/phase-01.5/PROBE-14.md`。

## 为什么它必须不判定

SC-8 是这么来的：上一轮有一次「15/15 命中」，其中 `bs.total_equity` 匹配到的是
**章节小标题**——看起来命中，其实取错行（台账 `A-4`）。命中数会骗人，取到的值不会。

所以本脚本**一行匹配逻辑都没有**。它不 import `mapping.py`，不认识任何 `field_id`。
它只回答一个问题：**这张表/这一节里，印着哪些行，各在第几页什么坐标，格子里是什么。**
一旦它开始替人判「这一行是不是那个字段」，SC-8 就在探测阶段先失守了。

## 为什么它必须在仓库里

台账 `A-10`：上一轮的探测语料与脚本**反复从 scratchpad 消失**（茅台 PDF、探测脚本、
两个外部仓的 clone 各丢过一次）。留在 scratchpad 里的探测等于没做过——
`A-4` 的「可复现技术起点」当时就因此不可复现。

## PDF 不进仓库

`--keep-pdf` 默认关闭，抽完即删（台账 `N-3`）。`.pdf` 同时在 `.gitignore` 与
`scan_rules.yaml` 的 `forbidden_tracked_file_types` 里，两处都挡着（AC-10）。

## 用法

    python scripts/probe_fields.py --stock 600519 --year 2023 --namespace is  --out probe_is.json
    python scripts/probe_fields.py --stock 600519 --year 2023 --namespace cfs --out probe_cfs.json
    python scripts/probe_fields.py --stock 600519 --year 2023 --namespace notes --out probe_notes.json
    python scripts/probe_fields.py --stock 600519 --year 2023 --namespace kpi --out probe_kpi.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

import pdfplumber  # noqa: E402

from extractor import locate  # noqa: E402
from extractor.download import fetch_annual_report  # noqa: E402
from extractor.pipeline import read_statement  # noqa: E402
from semantic_layer.resolve import Refusal  # noqa: E402

#: 固件里 `all_label_sequences` 只收这两张表的行项目标签，**窄于运行时的整份 PDF**。
#: 沿用 `extractor/__main__.py` 的 `FIXTURE_LABEL_SCOPE` 同一处置与同一理由
#: （威胁登记 `T-01.5-07`：固件不该把整份年报的文字都搬进版本控制）。
#: **后果如实记**：靠这份固件跑的 `L-36` 零命中判定，判据比运行时**宽松**——
#: 运行时的视野是整份 PDF，固件只有这两张表。
FIXTURE_LABEL_SCOPE = ("合并利润表", "合并现金流量表")

#: 命名空间 → 它的字段印在哪张报表上。
#: `is` / `cfs` 走 01.5-01 已跑通的报表锚点链路，**不重写**。
STATEMENT_OF_NAMESPACE = {
    "is": "合并利润表",
    "cfs": "合并现金流量表",
}

#: 章节标题**给不含序号的正文**。序号（`九、`）跨公司会变，正文不变；
#: `find_section_anchors` 对序号容差、对正文逐字，理由见该函数 docstring。
SECTION_TITLES = (
    "近三年主要会计数据和财务指标",
    "境内外会计准则下会计数据差异",
    "合并范围的变更",
    "非经常性损益项目和金额",
    "采用公允价值计量的项目",
    "在其他主体中的权益",
)

#: 「合并范围的变更」底下的六个固定子项（披露模板，CONTEXT §3.5）。
#: **给不含序号的正文**：序号形态跨公司不一致（茅台 2023 `1、`，万华化学 2019 `1.`）。
CONSOLIDATION_SCOPE_SUBITEMS = (
    "非同一控制下企业合并",
    "同一控制下企业合并",
    "反向购买",
    "处置子公司",
    "其他原因的合并范围变动",
    "其他",
)

#: 每个 `notes` / `kpi` 探测目标要 dump 哪一段：`(起始章节, 终止章节)`。
#: 终止章节显式给出，不靠「排序后的下一个」—— 同一份 PDF 里
#: 「十、非经常性损益项目和金额」（p6）与「九、合并范围的变更」（p120）相隔一百多页，
#: 按全局排序取下一个会把整整一百页都算进区间。
SECTION_SPANS = {
    "kpi": ("近三年主要会计数据和财务指标", "境内外会计准则下会计数据差异"),
    "nonrecurring": ("非经常性损益项目和金额", "采用公允价值计量的项目"),
    #: `notes.restatement_flag` 的证据**不在财务报表附注里**，在「主要会计数据」那张表上：
    #: 它的列头印着「调整后 / 调整前」，同节末尾还有一段追溯调整的说明。
    #: 命名空间前缀是 `notes`，印刷位置却是第三节 —— 这个错配本身是探测结论之一。
    "restatement": ("近三年主要会计数据和财务指标", "境内外会计准则下会计数据差异"),
}


def _line_to_dict(line) -> dict:
    return {
        "page": line.page,
        "y": round(line.y, 2),
        "text": line.text,
        "words": [
            {"text": w["text"], "x0": round(float(w["x0"]), 2), "x1": round(float(w["x1"]), 2)}
            for w in line.words
        ],
    }


def dump_section_lines(pdf, start_title: str, end_title: str | None, max_lines: int = 120) -> dict:
    """把一个章节区间内的原始行连同词坐标 dump 出来。

    **不做表头绑定。** `bind_columns` 要求行首逐字是 `项目` 且同屏有单位与币种，
    而「主要财务指标」这张表两样都没有（实测 p5：表头首格是 `主要财务指标`，
    单位行属于它上面的「主要会计数据」）。硬套会抛 `SheetHeaderNotFound`，
    **而那不是这张表的缺陷，是这条链路不适用于它**。区分这两件事正是本次探测的目的。
    """
    anchors = locate.find_section_anchors(pdf, SECTION_TITLES)
    starts = [a for a in anchors if a.title == start_title]
    if len(starts) != 1:
        return {
            "start_title": start_title,
            "anchor": None,
            "error": f"锚点命中 {len(starts)} 个，期望恰好 1 个",
            "lines": [],
        }
    start = starts[0]
    end = None
    if end_title is not None:
        ends = [a for a in anchors if a.title == end_title]
        end = ends[0] if len(ends) == 1 else None

    lines = []
    last_page = len(pdf.pages) if end is None else end.page
    for page_number in range(start.page, last_page + 1):
        for line in locate._cluster_lines(
            pdf.pages[page_number - 1], page_number, locate.DEFAULT_Y_TOLERANCE
        ):
            position = (page_number, line.y)
            if position <= (start.page, start.y):
                continue
            if end is not None and position >= (end.page, end.y):
                continue
            lines.append(_line_to_dict(line))
            if len(lines) >= max_lines:
                break
        if len(lines) >= max_lines:
            break
    return {
        "start_title": start_title,
        "end_title": end_title,
        "anchor": start.to_dict(),
        "end_anchor": end.to_dict() if end is not None else None,
        "truncated": len(lines) >= max_lines,
        "lines": lines,
    }


def dump_consolidation_scope(pdf) -> dict:
    """「九、合并范围的变更」六个子项的适用性，连同区间与原始行。

    区间是 `[合并范围的变更, 在其他主体中的权益)`。茅台 2023 p77 的
    `6.同一控制下和非同一控制下企业合并的会计处理方法` 是**会计政策**，
    落在区间外，**在构造上进不来**——不是靠关键词把它排除掉的。
    """
    anchors = locate.find_section_anchors(pdf, SECTION_TITLES)
    starts = [a for a in anchors if a.title == "合并范围的变更"]
    if len(starts) != 1:
        return {"anchor": None, "error": f"锚点命中 {len(starts)} 个，期望恰好 1 个"}
    start = starts[0]
    ends = [a for a in anchors if a.title == "在其他主体中的权益"]
    end = ends[0] if len(ends) == 1 else None
    try:
        verdicts = locate.read_applicability(
            pdf, start, end, CONSOLIDATION_SCOPE_SUBITEMS
        )
        error = None
    except locate.ApplicabilityUnreadable as exc:
        verdicts, error = None, str(exc)
    # `max_lines` 给足：本节在万华化学 2019 上跨 p169–p175 共 6 页，
    # 默认 120 行会在读到第 3 个子项之前就截断。
    span = dump_section_lines(pdf, "合并范围的变更", "在其他主体中的权益", max_lines=600)
    return {
        "anchor": start.to_dict(),
        "end_anchor": end.to_dict() if end is not None else None,
        "subitems": CONSOLIDATION_SCOPE_SUBITEMS,
        "applicability": verdicts,
        "error": error,
        # **`truncated` 必须传出来。** 初版把它丢了，于是一份被截断的 dump
        # 与完整的 dump 在产物里长得一模一样 —— 回放它会得到「找不到后四个子项」，
        # 而真实原因是行数被砍掉了，不是年报没印。
        "truncated": span["truncated"],
        "lines": span["lines"],
    }


def _narrowed_view(pdf, statement: str, year: int, scope_labels) -> dict:
    """一张报表的版面事实，`all_label_sequences` 收窄到 `scope_labels`。"""
    import dataclasses

    view = read_statement(pdf, statement, year)
    return dataclasses.replace(view, all_label_sequences=scope_labels).to_dict()


def build_fixture(pdf, stock: str, year: int, sha256: str) -> dict:
    """四个命名空间的探测产物合成一份固件。**回归用例跑在它上面，不跑在 PDF 上。**"""
    views = {s: read_statement(pdf, s, year) for s in FIXTURE_LABEL_SCOPE}
    scope_labels = frozenset(row.label_lines for v in views.values() for row in v.rows)
    import dataclasses

    start, end = SECTION_SPANS["kpi"]
    nr_start, nr_end = SECTION_SPANS["nonrecurring"]
    return {
        "source": {
            "stock_code": stock,
            "fiscal_year": year,
            "pdf_sha256": sha256,
            "label_scope": list(FIXTURE_LABEL_SCOPE),
            "label_scope_note": (
                "固件的 all_label_sequences 只收上列报表的行项目标签，窄于运行时的整份 PDF；"
                "理由见 probe_fields.FIXTURE_LABEL_SCOPE 的注释（威胁登记 T-01.5-07）。"
            ),
        },
        "statement_anchors": [a.to_dict() for a in locate.find_statement_anchors(pdf)],
        "section_anchors": [
            a.to_dict() for a in locate.find_section_anchors(pdf, SECTION_TITLES)
        ],
        "views": {
            statement: dataclasses.replace(
                view, all_label_sequences=scope_labels
            ).to_dict()
            for statement, view in views.items()
        },
        "kpi_section": dump_section_lines(pdf, start, end),
        "nonrecurring_section": dump_section_lines(pdf, nr_start, nr_end),
        "consolidation_scope": dump_consolidation_scope(pdf),
    }


def sha256_of(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe(stock: str, year: int, namespace: str, pdf_path: str | None = None) -> dict:
    """探一个命名空间。`pdf_path` 给了就读本地文件，不联网。

    **本地路径不是「跳过校验」的后门**：SHA-256 照样按字节算出来写进产物，
    与联网取到的那份对不对得上，由读报告的人比对。
    给这条路径的理由是探测要反复跑，每次重下 3.5 MB 又慢又对上游不礼貌。
    """
    with tempfile.TemporaryDirectory() as tmp:
        if pdf_path is not None:
            local = pathlib.Path(pdf_path)
            if not local.is_file():
                return {"refusal": f"本地 PDF 不存在：{local}"}
            out: dict = {
                "stock_code": stock,
                "fiscal_year": year,
                "namespace": namespace,
                "pdf_sha256": sha256_of(local),
                "source_url": None,
                "source": "local-file",
                "title": None,
            }
            opened = local
        else:
            result = fetch_annual_report(stock, year, keep_pdf=True, keep_dir=tmp)
            if isinstance(result, Refusal):
                return {"refusal": result.to_dict() if hasattr(result, "to_dict") else str(result)}
            out = {
                "stock_code": stock,
                "fiscal_year": year,
                "namespace": namespace,
                "pdf_sha256": result.sha256,
                "source_url": result.source_url,
                "source": "cninfo",
                "title": result.title,
            }
            opened = result.pdf_path
        with pdfplumber.open(opened) as pdf:
            if namespace == "fixture":
                out.update(build_fixture(pdf, stock, year, out["pdf_sha256"]))
            elif namespace in STATEMENT_OF_NAMESPACE:
                statement = STATEMENT_OF_NAMESPACE[namespace]
                out["statement"] = statement
                out["view"] = read_statement(pdf, statement, year).to_dict()
            elif namespace == "kpi":
                start, end = SECTION_SPANS["kpi"]
                out["section"] = dump_section_lines(pdf, start, end)
            elif namespace == "notes":
                start, end = SECTION_SPANS["nonrecurring"]
                out["nonrecurring_section"] = dump_section_lines(pdf, start, end)
                start, end = SECTION_SPANS["restatement"]
                out["restatement_section"] = dump_section_lines(pdf, start, end)
                out["consolidation_scope"] = dump_consolidation_scope(pdf)
            else:  # pragma: no cover - argparse 已挡住
                raise ValueError(f"未知命名空间 {namespace!r}")
        return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--stock", required=True, help="股票代码，如 600519")
    parser.add_argument("--year", required=True, type=int, help="会计年度，如 2023")
    parser.add_argument(
        "--namespace",
        required=True,
        choices=sorted({"is", "cfs", "notes", "kpi", "fixture"}),
        help="要探测的字段命名空间；`fixture` 产出合并固件（四段一起，标签集收窄）",
    )
    parser.add_argument("--out", required=True, help="JSON 输出路径")
    parser.add_argument(
        "--pdf",
        default=None,
        help="读本地 PDF 而不联网下载。SHA-256 照样按字节算出来写进产物。",
    )
    args = parser.parse_args(argv)

    payload = probe(args.stock, args.year, args.namespace, args.pdf)
    path = pathlib.Path(args.out)
    if path.parent != pathlib.Path(""):
        path.parent.mkdir(parents=True, exist_ok=True)
    # 显式 newline：Windows 下 write_text 默认写 CRLF，而 .gitattributes 强制 LF 入库
    # —— 于是工作树里的文件与仓库里的逐字节不同。固件不在冻结集内所以不违反 D-012，
    # 但「工作树与仓库不一致」本身就是下一个哈希类结论的坑，在这里堵掉。
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    if "refusal" in payload:
        print(f"拒答：{payload['refusal']}", file=sys.stderr)
        return 1
    print(f"已写入 {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
