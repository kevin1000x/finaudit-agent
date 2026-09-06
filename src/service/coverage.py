"""覆盖面：**我们对哪些公司/哪些年份真的有数据**（`02-04` T2）。

## 为什么这件事要单独有一个模块

`D-039` 要的是给用户用的产品，而产品最容易犯、也最致命的一个错是
**把覆盖面装大**。这个项目的卖点是可审计；一旦对一家没有数据的公司
编出一个数，卖点当场归零 —— 比答错一道题严重得多。

⇒ 覆盖面**由磁盘推导，不手写**（`N-42` 的判据：这道门扫的集合必须
等于它声称在检查的集合）。手写清单会和真实数据源分叉，而分叉的那一刻
它看起来仍然是绿的。

## 🔴 2026-09-06 实测：仓库里没有任何**已持久化**的抽取结果

`data/parsed/` `data/results/` `data/cache/` 三个目录**都不存在**
（`.gitignore` 里有它们，但从没被创建过）。Phase 1.5 建成的抽取器
是在测试与人工核对里现跑的，产物没有落盘。

⇒ **今天服务能作答的只有合成夹具**（frozen-01 的 `synthetic-01.yaml`，
虚构公司与数值）。真实公司要能答，前提是先有一步**离线抽取导出** ——
那不是本模块的事，也不是一个可以顺手做掉的事，记 `N-61`。

⚠️ **这个状态必须原样报出去**，不许拿合成夹具冒充「我们支持这些公司」。
`Answer` 的渲染里已经写死了「合成夹具（虚构公司与数值），不是任何真实公司的年报」，
本模块在覆盖清单里同样标出来。
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

#: 找数据源的地方，按优先级。**这是本模块唯一的「配置」，而且它是常量。**
#: 加一个目录进来就等于扩大覆盖面，那是要写在这里、能被 review 的一行。
SOURCE_DIRS = (
    # 真实抽取结果落盘之后放这儿。今天它不存在 —— 见模块 docstring 与 `N-61`。
    ("real", REPO_ROOT / "data" / "extracted"),
    # 合成夹具。**永远标成合成**，不许当成真实覆盖面。
    ("synthetic", REPO_ROOT / "eval" / "frozen-01" / "fixtures"),
)


@dataclass(frozen=True)
class Row:
    """覆盖清单里的一行：某个来源里的某家公司某一年。"""

    nature: str          # "real" | "synthetic"
    fixture_id: str
    stock_code: str
    fiscal_year: int
    #: 公司简称。**只有真实年报才有** —— 合成夹具的「公司名」是虚构的，
    #: 把它显示成公司名等于请人去搜一家不存在的公司。默认空串。
    short_name: str = ""

    def to_dict(self) -> dict:
        return {
            "nature": self.nature,
            "fixture_id": self.fixture_id,
            "stock_code": self.stock_code,
            "fiscal_year": self.fiscal_year,
            "short_name": self.short_name,
        }


def _scan(nature: str, directory: Path) -> list:
    """一个目录里所有 `*.yaml` 数据源声明了哪些 (公司, 年份)。

    读不动的文件**跳过并不报错**：覆盖面少列一行是保守方向，
    而抛异常会让整个 `/coverage` 挂掉 —— 那反而让人看不到还剩什么能用。

    🔴 **`nature` 以文件自己的 `meta.kind` 为准，不以它落在哪个目录为准。**
    传进来的 `nature` 只是这个目录的**声称**。二者不一致时取保守的那个：
    「合成」。这是 `N-42` 那个形状 —— 一道门扫的集合必须等于它声称在检查的集合；
    按目录贴标签的话，往 `data/extracted/` 里放一份合成文件就会被标成真实数据，
    而那正是这个项目最不能犯的错（`D-010`）。
    """
    import yaml

    if not directory.is_dir():
        return []
    out: list = []
    for path in sorted(directory.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        meta = data.get("meta") or {}
        fixture_id = meta.get("fixture_id") or path.stem
        # 自称真实还要给得出 PDF 指纹（64 位十六进制）—— 与 `FixtureSource` 同一条判据。
        claims_real = meta.get("kind") == "real" and len(str(meta.get("source_pdf_sha256") or "")) == 64
        # ⚠️ 写成局部变量，**不要覆盖 `nature` 这个参数** ——
        # 覆盖了的话第一份文件的判定会漏给后面所有文件。
        this = "real" if (nature == "real" and claims_real) else "synthetic"
        # 简称只在真实数据上取。合成夹具里的「华鑫科技」是虚构的，
        # 显示成公司名等于请人去搜一家不存在的公司 —— 而它在页面上和真公司长得一样。
        name = str(meta.get("short_name") or "") if this == "real" else ""
        for row in data.get("rows") or []:
            code, year = row.get("stock_code"), row.get("fiscal_year")
            if code is None or year is None:
                continue
            try:
                out.append(Row(this, str(fixture_id), str(code), int(year), name))
            except (TypeError, ValueError):
                continue
    return out


@lru_cache(maxsize=1)
def coverage() -> tuple:
    """全部覆盖行。

    ⚠️ **可丢弃缓存**（`D-021` 豁免三明确允许的那一类）：
    内容完全由磁盘上的公开数据推导，`coverage.cache_clear()` 之后重算得到同一份，
    清掉不丢任何东西。它不是记录系统。
    """
    rows: list = []
    for nature, directory in SOURCE_DIRS:
        rows.extend(_scan(nature, directory))
    return tuple(rows)


def covered(stock_code, fiscal_year) -> bool:
    if stock_code is None or fiscal_year is None:
        return False
    try:
        year = int(fiscal_year)
    except (TypeError, ValueError):
        return False
    return any(r.stock_code == str(stock_code) and r.fiscal_year == year for r in coverage())


def summary() -> dict:
    """`GET /coverage` 的响应体。**先让人看清能问什么，再让他问。**"""
    rows = coverage()
    real = [r for r in rows if r.nature == "real"]
    synthetic = [r for r in rows if r.nature == "synthetic"]
    return {
        "rows": [r.to_dict() for r in rows],
        "counts": {"real": len(real), "synthetic": len(synthetic), "total": len(rows)},
        # 🔴 这句话不许被前端吞掉。把合成数据说成真实数据，比数据本身更严重（`D-010`）。
        "notice": (
            "真实年报抽取结果 " + str(len(real)) + " 行；"
            "合成夹具 " + str(len(synthetic)) + " 行（虚构公司与数值，不是任何真实公司的年报）。"
            + (
                "**当前没有任何真实公司的数据** —— 抽取结果尚未落盘，见 N-61。"
                if not real else ""
            )
        ),
    }


def why_not(stock_code, fiscal_year) -> str:
    """覆盖面之外的提问，拿到的理由。

    ⚠️ **不许渲染成「该公司没有这个指标」** —— 那是两件事：
    「我们没有这家公司的数据」与「这家公司没有这个指标」，混同就是编。
    """
    rows = coverage()
    same_code = sorted({r.fiscal_year for r in rows if r.stock_code == str(stock_code)})
    if same_code:
        return (
            "我们有 " + str(stock_code) + " 的数据，但没有 " + str(fiscal_year) + " 年；"
            "有的年份是：" + "、".join(str(y) for y in same_code)
        )
    codes = sorted({r.stock_code for r in rows})
    return (
        "我们没有 " + str(stock_code) + " 这家公司的数据 —— "
        "这说的是**我们没有**，不是「这家公司没有这个指标」。"
        "当前有数据的是：" + ("、".join(codes) if codes else "（一家都没有）")
    )
