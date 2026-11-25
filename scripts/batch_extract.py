#!/usr/bin/env python
"""整批读数器：在一个有抽样框的样本上数「抽成几份、拒答几份、为什么」（`D-048`，`R-4`）。

## 这不是门禁

它不产生通过/不通过判定，已登记在 `scripts/check_gates.py` 的 `NOT_GATES` 里。
退出码只说明脚本有没有跑完。读数由人写进 `docs/agent/phase-01.5/BATCH-SH2024.md`。

## 为什么在仓库里

理由同 `probe_fields.py` 抬头（台账 `A-10`）：留在 scratchpad 里的探测等于没做过。
2026-11-12 又丢了一次：`R-4` 第一遍整批的脚本和 171 行结果放在 scratchpad，
两天后目录被清空，只能重跑。

## 它不做什么

- 不改 PDF 侧的任何值（`D-013`），只记状态、拒答码、零命中的字段名和记录数。
- 不判「这份该不该抽成」。拒答是 fail-closed 的正常出口；`summarize` 只按结构归类
  （异常类型、锚点个数、零命中的字段），不看任何数值。
- PDF 不进仓库：读上游 `cninfo-financial-analyzer` 的 `data/raw/rvp/`，只读不写。
  结果写进 `data/results/`（已在 `.gitignore`）。

## 用法（仓库根目录）

    export PYTHONDONTWRITEBYTECODE=1
    python -X utf8 scripts/batch_extract.py extract \\
        --pdf-dir ../cninfo-financial-analyzer/data/raw/rvp \\
        --manifest ../cninfo-financial-analyzer/data/results/rvp_manifest.json \\
        --year 2024 --out data/results/batch-sh2024
    python -X utf8 scripts/batch_extract.py crosscheck --pdf-dir ... --manifest ... --year 2024 --out data/results/batch-sh2024
    python -X utf8 scripts/batch_extract.py summarize --out data/results/batch-sh2024 > summary.md

`crosscheck` 要联网（AKShare），每次取数后停 1.5 秒；响应存进 `<out>/akshare/`，再跑时回放。
每个输出目录对应一次实验。换年度、样本或抽取器版本时使用新目录。
抽取按股票续跑；对照会重试上次未取得响应的股票，汇总取每股最近一次结果。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

def _done(path: Path) -> set:
    if not path.is_file():
        return set()
    return {json.loads(line)["stock"] for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def _rows(path: Path) -> list:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _append(path: Path, row: dict) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def checked_pdfs(pdf_dir: Path, manifest_path: Path, year: int) -> dict:
    """计数前先检查样本完整性，包括断点续跑时已处理的文件。"""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {s for s, entry in manifest.items() if entry["status"] == "ok"}
    files = {p.name.split("_")[0]: p for p in pdf_dir.glob(f"*_{year}.pdf")}
    if not expected or set(files) != expected:
        raise ValueError("PDF 名单与清单下载成功的名单不符")
    for stock, pdf in files.items():
        with pdf.open("rb") as fh:
            if hashlib.file_digest(fh, "sha256").hexdigest() != manifest[stock]["sha256"]:
                raise ValueError(f"{stock} PDF SHA-256 与清单不符")
    return {s: (files[s], manifest[s]) for s in sorted(files)}


def phase_extract(pdf_dir: Path, manifest_path: Path, year: int, out: Path) -> None:
    from extractor.pipeline import DEFAULT_EXTRACTION_PLAN, extract_batch

    files = checked_pdfs(pdf_dir, manifest_path, year)
    target = out / "extract.jsonl"
    done = _done(target)
    for stock, (pdf, entry) in files.items():
        if stock in done:
            continue
        row = {"stock": stock, "title": entry.get("title"), "sha_ok": True}
        t0 = time.time()
        try:
            batch = extract_batch(stock, year, pdf_path=pdf, plan=DEFAULT_EXTRACTION_PLAN)
        except Exception as exc:  # 记下来，不吞：异常类型本身就是一类结果
            row.update(status="EXCEPTION", error=type(exc).__name__, detail=str(exc)[:300])
        else:
            if hasattr(batch, "records"):
                row.update(status="OK", n_records=len(batch.records),
                           fields=sorted(r.field_id for r in batch.records))
            else:
                row.update(status="REFUSED", code=batch.code.name, detail=str(batch.detail)[:300])
        row["seconds"] = round(time.time() - t0, 1)
        _append(target, row)
        print(stock, row["status"], row.get("code", row.get("error", "")), row["seconds"], "s", flush=True)


def phase_crosscheck(pdf_dir: Path, manifest_path: Path, year: int, out: Path, limit: int | None) -> None:
    from extractor.crosscheck import (
        CrossCheckVerdict,
        cross_validate_batch,
        fetch_reference,
        load_all_akshare_mappings,
        references_from_payload,
    )
    from extractor.pipeline import DEFAULT_EXTRACTION_PLAN, extract_batch

    files = checked_pdfs(pdf_dir, manifest_path, year)
    rows = _rows(out / "extract.jsonl")
    if (len(rows) != len(files) or {r["stock"] for r in rows} != set(files)
            or not all(r["sha_ok"] for r in rows)):
        raise ValueError("离线记录不完整或未通过哈希核对")
    ok = [r for r in rows if r["status"] == "OK"]
    target = out / "crosscheck.jsonl"
    fixtures = out / "akshare"
    fixtures.mkdir(exist_ok=True)
    done = {r["stock"] for r in _rows(target) if r["status"] == "OK"}
    tables = load_all_akshare_mappings()
    count = 0
    for r in ok:
        stock = r["stock"]
        if stock in done:
            continue
        if limit is not None and count >= limit:
            break
        count += 1
        row = {"stock": stock}
        fixture = fixtures / f"{stock}_{year}.json"
        if fixture.is_file():
            payload = json.loads(fixture.read_text(encoding="utf-8"))
            row["reference"] = "replayed"
        else:
            payload = fetch_reference(stock, year)
            time.sleep(1.5)
            if not isinstance(payload, dict):
                row.update(status="REFERENCE_REFUSED", detail=str(getattr(payload, "detail", payload))[:300])
                _append(target, row)
                print(stock, row["status"], flush=True)
                continue
            tmp = fixture.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
            tmp.replace(fixture)
            row["reference"] = "fetched"
        batch = extract_batch(stock, year, pdf_path=pdf_dir / f"{stock}_{year}.pdf", plan=DEFAULT_EXTRACTION_PLAN)
        outcome = cross_validate_batch(batch, references_from_payload(payload, tables), period=f"{year}1231")
        verdicts = {v.name: 0 for v in CrossCheckVerdict}
        reasons: dict = {}
        disagreements = []
        for res in outcome.results:
            verdicts[res.verdict.name] += 1
            if res.verdict is CrossCheckVerdict.INCOMPARABLE and res.incomparable_reason is not None:
                reasons[res.incomparable_reason.name] = reasons.get(res.incomparable_reason.name, 0) + 1
            if res.verdict is CrossCheckVerdict.DISAGREES:
                disagreements.append({
                    "field": res.field_id,
                    "pdf": None if res.pdf_value is None else str(res.pdf_value),
                    "ref": None if res.reference_value is None else str(res.reference_value),
                    "diff": None if res.difference is None else str(res.difference),
                    "ref_column": res.reference_column,
                })
        row.update(status="OK", verdicts=verdicts, incomparable=reasons, disagreements=disagreements,
                   unreferenced=list(outcome.unreferenced))
        _append(target, row)
        print(stock, verdicts, flush=True)


def category(row: dict) -> str:
    """只按结构归类：异常类型、零命中的字段、锚点个数。不看任何数值。"""
    if row["status"] == "OK":
        return "OK"
    detail = row.get("detail") or ""
    if row["status"] == "EXCEPTION":
        m = re.match(r"(\S+) 的 label 变体", detail)
        if row.get("error") == "MappingZeroHit" and m:
            return "MappingZeroHit:" + m.group(1)
        if "表头里绑不到口径" in detail:
            return "表头未能绑定期间列"
        return "EXCEPTION:" + str(row.get("error"))
    m = re.search(r"'([^']+)' 在这份 PDF 上定位到 (\d+) 个锚点", detail)
    if m:
        return f"锚点 {m.group(1)} = {m.group(2)}"
    if "找不到含 '项目' 的表头行" in detail:
        return "锚点后找不到表头"
    if "读不到单位与币种" in detail:
        return "缺单位或币种"
    return "REFUSED:" + str(row.get("code"))


def summarize(out: Path, financial_stocks: set[str]) -> str:
    rows = _rows(out / "extract.jsonl")
    if financial_stocks - {r["stock"] for r in rows}:
        raise ValueError("金融分组包含样本外股票代码")
    cats, cats_fin, members = Counter(), Counter(), defaultdict(list)
    for r in rows:
        c = category(r)
        financial = r["stock"] in financial_stocks
        (cats_fin if financial else cats)[c] += 1
        members[c].append(r["stock"] + ("*" if financial else ""))
    lines = [f"# 整批读数（{len(rows)} 份）", "",
             f"sha_ok：{sum(1 for r in rows if r['sha_ok'])} / {len(rows)}",
             f"单列金融样本（按传入的股票代码，带 *）：{len(financial_stocks)} 份", "",
             "| 结果 | 其余样本 | 单列金融样本 |", "|---|---:|---:|"]
    order = sorted(set(cats) | set(cats_fin), key=lambda k: (-(cats[k] + cats_fin[k]), k))
    lines += [f"| {c} | {cats[c]} | {cats_fin[c]} |" for c in order]
    lines += ["", "OK 的记录数分布：" + json.dumps(dict(Counter(r.get("n_records") for r in rows if r["status"] == "OK")))]
    secs = sorted(r["seconds"] for r in rows)
    if secs:
        lines.append(f"耗时：合计 {sum(secs):.0f} 秒，中位 {secs[len(secs) // 2]} 秒")
    lines += ["", "## 逐类名单", ""]
    lines += [f"- **{c}**（{len(members[c])}）：{', '.join(members[c])}" for c in order]

    crows = list({r["stock"]: r for r in _rows(out / "crosscheck.jsonl")}.values())
    if crows:
        tot, reasons, dis = Counter(), Counter(), []
        for r in crows:
            tot.update(r.get("verdicts") or {})
            reasons.update(r.get("incomparable") or {})
            dis += [(r["stock"], d) for d in r.get("disagreements") or []]
        lines += ["", f"## crosscheck（{len(crows)} 份）", "",
                  "判定合计：" + json.dumps(dict(tot), ensure_ascii=False),
                  "不可比原因：" + json.dumps(dict(reasons), ensure_ascii=False),
                  "无对照映射的记录：" + str(sum(len(r["unreferenced"]) for r in crows if r["status"] == "OK")),
                  "对照源拒答：" + str(sum(1 for r in crows if r.get("status") == "REFERENCE_REFUSED")), "",
                  "| 股票 | 一致 | 不一致 | 不可比 |", "|---|---:|---:|---:|"]
        for r in crows:
            v = r.get("verdicts") or {}
            lines.append(f"| {r['stock']} | {v.get('AGREES', '')} | {v.get('DISAGREES', '')} | {v.get('INCOMPARABLE', '')} |")
        if dis:
            lines += ["", "| 股票 | 字段 | PDF | AKShare | 差额 | AKShare 列 |", "|---|---|---:|---:|---:|---|"]
            lines += [f"| {s} | `{d['field']}` | {d['pdf']} | {d['ref']} | {d['diff']} | {d['ref_column']} |" for s, d in dis]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("phase", choices=("extract", "crosscheck", "summarize"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--pdf-dir", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--year", type=int)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--financial-stocks", nargs="+", default=[], help="汇总时单列的金融样本股票代码")
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    if args.phase == "extract":
        if not (args.pdf_dir and args.manifest and args.year):
            parser.error("extract 需要 --pdf-dir、--manifest、--year")
        phase_extract(args.pdf_dir, args.manifest, args.year, args.out)
    elif args.phase == "crosscheck":
        if not (args.pdf_dir and args.manifest and args.year):
            parser.error("crosscheck 需要 --pdf-dir、--manifest、--year")
        phase_crosscheck(args.pdf_dir, args.manifest, args.year, args.out, args.limit)
    else:
        sys.stdout.write(summarize(args.out, set(args.financial_stocks)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
