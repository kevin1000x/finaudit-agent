"""离线抽取导出：把抽取结果落盘，让服务能回答**真实公司**（`N-61`）。

## 这一步为什么必须存在

Phase 1.5 建成的抽取器一直是在测试与人工核对里**现跑**的，产物没留下来。
`src/service/` 因此只能读到合成夹具 —— 服务能答的全是虚构公司。
中间缺的就是这一步：跑一次抽取器，把结果写成
`data/extracted/<code>_<year>.yaml`，服务只读它。

**它不是计划任务**（人手动跑，加一家公司跑一次），
**也不是记录系统**（内容可由公开年报重新推导，删掉重跑得到同一份）。
⇒ 不碰 `D-021` 豁免三的两句判据。

## 🔴 准入清单：只导出**人工逐字段核对过的**字段

这个模块最要紧的一行不是「怎么写文件」，是**「不写哪些字段」**。

抽取质量在没核对过的字段上是**未知的**。产品一旦对外输出没人验过的数，
「可审计」这个卖点当场赔光 —— 那比答错一道题严重得多。

⇒ `data/verified/<code>_<year>.yaml` 是准入清单，**导出只认它**：

| 情形 | 处置 | 为什么 |
|---|---|---|
| 抽到了、清单里没有 | **丢掉**，并把丢了哪些写进产物的 `meta.dropped` | 抽取器合法地比核对过的多（万华那 3 个 `notes.*`）。丢掉是保守方向，且**留痕** |
| 清单里有、没抽到 | **整份拒绝导出** | 这是回归：昨天还能取到的字段今天取不到了 |
| 两边都有、值对不上 | **整份拒绝导出** | 要么抽取器变了，要么清单抄错了。**两种都不该继续往下走** |

第三条是这套设计的关键：清单里的取值**抄自签署过的核对记录，不是抄自抽取器**。
抄错的后果是导出失败，**不是**导出一个错的数 —— 失败方向是安全的。

## 产物里为什么要带出处

服务读到的每一行都要能回答「这个数是从哪一页哪一列来的」。
`provenance` 那一段就是给这个用的 —— `D-003` 说证据链是第一类产物不是日志，
那么把页码留在一个跑完就丢的进程内存里，等于没有。
"""

from __future__ import annotations

import hashlib
from decimal import Decimal
from pathlib import Path

from semantic_layer.resolve import Refusal

from .pipeline import DEFAULT_EXTRACTION_PLAN, extract_batch

__all__ = [
    "ExportRejected",
    "VERIFIED_DIR",
    "EXTRACTED_DIR",
    "export_one",
    "load_verified",
    "render_yaml",
    "verified_pairs",
]

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VERIFIED_DIR = REPO_ROOT / "data" / "verified"
EXTRACTED_DIR = REPO_ROOT / "data" / "extracted"


class ExportRejected(Exception):
    """导出被拒。**不是异常情况，是这个模块存在的理由** —— 见模块 docstring 的表。"""


def verified_pairs(verified_dir: Path | None = None) -> list:
    """有准入清单的 `(股票代码, 年度)`。**产品的覆盖面上限就是这个集合。**"""
    directory = VERIFIED_DIR if verified_dir is None else Path(verified_dir)
    if not directory.is_dir():
        return []
    out = []
    for path in sorted(directory.glob("*.yaml")):
        meta = (load_verified(path).get("meta") or {})
        code, year = meta.get("stock_code"), meta.get("fiscal_year")
        if code is not None and year is not None:
            out.append((str(code), int(year)))
    return out


def load_verified(path: Path) -> dict:
    import yaml

    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def _comparable(value) -> str | None:
    """把「清单里写的」与「抽取器给的」化到同一种可比形式。

    ⚠️ **数值一律走 `Decimal` 比大小，不比字符串**：`"48697611501.20"` 与
    `"48697611501.2"` 是同一个数，而字符串不相等。核对记录里两种写法都出现过
    （`COMPUTED-VALUES.md` §5.1 的 AKShare 列就有省略末位零的）。
    布尔与集合按字面比 —— 它们本来就没有格式歧义。
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return "bool:" + ("true" if value else "false")
    if isinstance(value, (list, tuple)):
        return "set:" + ",".join(sorted(str(v) for v in value))
    try:
        return "num:" + str(Decimal(str(value)).normalize())
    except Exception:
        return "text:" + str(value)


def _yaml_scalar(value) -> str:
    """写成 YAML 字面量。

    🔴 **数值必须加引号。** 不加引号 `yaml.safe_load` 会读成 float，
    14 位以上有效数字被悄悄改掉 —— 而这里每一个数都是 14 位以上。
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_yaml_scalar(str(v)) for v in value) + "]"
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def export_one(
    stock_code: str,
    year: int,
    pdf_path: Path | str | None = None,
    verified_dir: Path | None = None,
    plan=None,
) -> dict:
    """跑一次抽取，按准入清单过滤，返回**要写进文件的那份字典**（不落盘）。

    落盘与渲染分开，是为了让测试能在不写文件的情况下检查过滤逻辑。
    """
    directory = VERIFIED_DIR if verified_dir is None else Path(verified_dir)
    vpath = directory / (str(stock_code) + "_" + str(year) + ".yaml")
    if not vpath.is_file():
        raise ExportRejected(
            "没有 " + str(stock_code) + "/" + str(year) + " 的人工核对清单（" + str(vpath) + "）。"
            "**先核对，再导出** —— 没核对过的公司不许进产品，见 N-61。"
        )
    verified = load_verified(vpath)
    meta = verified.get("meta") or {}
    allow = verified.get("fields") or {}

    pdf = Path(pdf_path) if pdf_path is not None else REPO_ROOT / str(meta.get("source_pdf") or "")
    if not pdf.is_file():
        raise ExportRejected("找不到年报 PDF：" + str(pdf) + "（PDF 不进版本控制，得自己先取回来）")
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    expected_digest = meta.get("source_pdf_sha256")
    if expected_digest and digest != expected_digest:
        raise ExportRejected(
            "PDF 不是核对时的那一份：清单记 " + str(expected_digest)[:12]
            + "…，手上这份是 " + digest[:12] + "…。**核对结论只对那一份 PDF 成立。**"
        )

    batch = extract_batch(
        str(stock_code),
        int(year),
        pdf_path=pdf,
        plan=DEFAULT_EXTRACTION_PLAN if plan is None else plan,
    )
    if isinstance(batch, Refusal):
        raise ExportRejected("抽取拒答 [" + batch.code.name + "]：" + str(batch.detail))

    got = {r.field_id: r for r in batch.records}
    missing = sorted(set(allow) - set(got))
    if missing:
        raise ExportRejected(
            "清单里有、这次没抽到：" + "、".join(missing)
            + "。**这是回归，不是覆盖面变化** —— 先查抽取器，别改清单。"
        )

    mismatched = []
    for field_id, expected in sorted(allow.items()):
        actual = got[field_id].value
        if _comparable(expected) != _comparable(actual):
            mismatched.append(field_id + "：清单 " + repr(expected) + " ≠ 抽取器 " + repr(actual))
    if mismatched:
        raise ExportRejected(
            "取值对不上，整份不导出：\n  " + "\n  ".join(mismatched)
            + "\n**要么抽取器变了，要么清单抄错了 —— 两种都不该继续往下走。**"
        )

    # 🔴 **本机绝对路径不进产物。** 走本地 PDF 复跑时 `source_url` 是
    # `file://C:/Users/.../` —— 那会把操作者的目录结构写进一个要提交的文件里
    # （而这个仓库按 `D-005` 到 Phase 4 才决定要不要公开）。
    # 出处以 **PDF 的 SHA-256** 为准，它比一个本机路径可核验得多。
    url = next((r.source_url for r in batch.records if r.source_url), None)
    if url and not str(url).startswith("http"):
        url = None

    dropped = sorted(set(got) - set(allow))
    row = {"stock_code": str(stock_code), "fiscal_year": int(year)}
    provenance = {}
    for field_id in sorted(allow):
        record = got[field_id]
        row[field_id] = record.value
        provenance[field_id] = {
            "page": record.page,
            "column_header": record.column_header,
            "cell_state": None if record.cell_state is None else record.cell_state.name,
            "mapping_version": record.mapping_version,
        }
    return {
        "meta": dict(meta),
        "source_pdf_sha256": digest,
        "batch_id": batch.batch_id,
        "source_url": url,
        "dropped": dropped,
        "row": row,
        "provenance": provenance,
    }


def render_yaml(payload: dict) -> str:
    """渲染成服务能直接读的那份 YAML。**手写渲染，不用 `yaml.dump`。**

    理由不是洁癖：`yaml.dump` 会把 `Decimal` 变成 `!!python/object` 或字符串，
    也不保证数值不被写成不带引号的 float。这里每一个数都必须**加引号**落盘。
    """
    meta = payload["meta"]
    L = [
        "# **真实年报抽取结果。由 `python -m extractor export` 生成，不要手改。**",
        "#",
        "# 手改这份文件等于绕过准入清单 —— 它存在的全部意义就是「只有核对过的数才到得了这里」。",
        "# 要加字段：先在 `data/verified/` 里核对并签署，再重跑导出。",
        "#",
        "# `kind: real` 是给渲染层看的：证据链里这一行会印年报出处与 PDF 哈希，",
        "# 而不是「合成夹具（虚构公司与数值）」那一句。**两者绝不能互相冒充。**",
        "",
        "meta:",
        "  fixture_id: " + _yaml_scalar("annual-report-" + str(meta.get("stock_code")) + "-" + str(meta.get("fiscal_year"))),
        "  kind: real",
        "  short_name: " + _yaml_scalar(meta.get("short_name")),
        "  full_name: " + _yaml_scalar(meta.get("full_name")),
        "  fiscal_year: " + str(meta.get("fiscal_year")),
        "  stock_code: " + _yaml_scalar(meta.get("stock_code")),
        "  source_pdf_sha256: " + _yaml_scalar(payload["source_pdf_sha256"]),
        "  source_url: " + _yaml_scalar(payload.get("source_url")),
        "  batch_id: " + _yaml_scalar(payload.get("batch_id")),
        "  signed_off: " + _yaml_scalar(meta.get("signed_off")),
        "  verification_sections: ["
        + ", ".join(_yaml_scalar(s) for s in (meta.get("verification_sections") or []))
        + "]",
    ]
    dropped = payload.get("dropped") or []
    L.append("  # 抽到了但**没经过人工核对**，因此没进这份文件。少答一道题，好过输出没人验过的数。")
    L.append("  dropped: [" + ", ".join(_yaml_scalar(d) for d in dropped) + "]")
    L.append("")
    L.append("rows:")
    row = payload["row"]
    L.append("  - stock_code: " + _yaml_scalar(row["stock_code"]))
    L.append("    fiscal_year: " + str(row["fiscal_year"]))
    for field_id in sorted(k for k in row if k not in ("stock_code", "fiscal_year")):
        L.append("    " + field_id + ": " + _yaml_scalar(row[field_id]))
    L.append("")
    L.append("# 每个字段是从哪一页哪一列来的。**证据链是第一类产物，不是日志**（`D-003`）——")
    L.append("# 把页码留在一个跑完就丢的进程内存里，等于没有。")
    L.append("provenance:")
    for field_id, p in sorted(payload["provenance"].items()):
        L.append(
            "  " + field_id + ": {page: " + str(p["page"])
            + ", column_header: " + _yaml_scalar(p["column_header"])
            + ", cell_state: " + _yaml_scalar(p["cell_state"])
            + ", mapping_version: " + str(p["mapping_version"]) + "}"
        )
    return chr(10).join(L) + chr(10)


def write_export(payload: dict, out_dir: Path | None = None) -> Path:
    """落盘。**强制 LF** —— `.gitattributes` 靠它保住跨平台稳定的哈希（`D-012`）。"""
    directory = EXTRACTED_DIR if out_dir is None else Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    meta = payload["meta"]
    path = directory / (str(meta["stock_code"]) + "_" + str(meta["fiscal_year"]) + ".yaml")
    with open(path, "w", encoding="utf-8", newline=chr(10)) as fh:
        fh.write(render_yaml(payload))
    return path
