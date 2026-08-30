"""证据指针字段的「谁产生 / 谁消费」矩阵 —— `ARCHITECTURE` §8.5.3，登记册 `L-6`。

**这不是一道门禁，是一个生成器。** 它把「哪些证据字段算出来了却没人读」这件事
**从代码里解析出来**，而不是靠一条「必须记得接线」的纪律。

## 为什么是生成的而不是手写的

`ARCHITECTURE` §8.5.3 逐字写着：手写矩阵是「派生数据的第二份拷贝」，会与代码分叉。
外部实证是 harness 从 TypeScript Program 解析生成事件矩阵，
一次报出 **56 条事件里 7 条零监听** —— 那 7 条是**矩阵自己报出来的**，
不是有人想起来去查的。

## 为什么现在才写（原本的阻塞理由已经过期）

§8.5.3 与登记册 `L-6` 都写着「待 Phase 1.5 抽取器产出真实字段后再写 ——
现在写会写成一个查不到东西的空壳，那是 `F-2` 本身」。
**那个前提已于 2026-08-31 消失**：抽取器一个批次产出 28 条真实记录、五支 `kind` 全部接通，
`field_id` / `page` / `anchor_page` / `selection` 各自都有真实的产生点与消费点。

## 它能抓什么 —— **以及它抓不到本会话那两个实例（实测，不是推测）**

它抓的是**一个字段有产生点、却零消费点**：算出来了，全仓没有任何地方读它。

🔴 **写完当场验了一次，结论是否定的**：本会话手工抓到的两个「算出来却被丢掉」——
`header_inherited` 没进 `to_dict()`、派生值没并进求值行 —— **本工具都抓不到**。
把 `to_dict()` 里那一行删掉重跑，矩阵从 `14 产生 / 5 消费` 变成 `13 / 4`，
**退出码仍是 0**。因为那两个都是「**少了一个**消费点」，不是「**零**消费点」。

⇒ **原来的 docstring 声称它能抓这两个，那句话是错的，已删。**
声称的范围不许大于被证明的范围 —— 这条纪律对这个工具自己一样适用。

**为什么不改成「消费点数下降即报警」**：那需要一个基线，
而基线会随正常重构波动（一次合并调用点就会让计数下降）。
那条路产出的是噪音，而**噪音会让人停止阅读门禁输出**。
「零消费点」是一个**不需要基线**的判据，所以它是这里唯一能站住的那条。

## 明确抓不到什么

⚠️ 四条，一条都不许被读成「接线都对」：

1. **只看「有没有被读」，不看「读得对不对」。** 一处 `record.page` 被读进一个
   从不输出的局部变量，在本表里照样算消费点。
2. **按属性名匹配，不做类型推断。** `x.page` 里的 `x` 是不是 `ExtractionRecord`，
   本工具不判 —— **宁可多算消费点（漏判断线），不许少算（误报断线）**：
   误报会让人去删表里的行，而那会让它退化。
3. **字典字面量里的键**（`{"page": ...}`）算**产生**不算消费 ——
   `to_dict()` 正是这个形状，而它确实是在往外产出。
4. **跨模块的动态访问**（`getattr(record, name)`）看不见。
   本仓 `record.evidence_identifiers` 就是这么写的，它对本表是隐形的。
"""

from __future__ import annotations

import ast
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent

#: 要盯的证据指针字段。取自 `ARCHITECTURE` §8.5.3 点名的四个，
#: 外加本会话实际出过事的两个（`header_inherited` / `truncation_stats`）。
#:
#: ⚠️ **这张清单是手写的，而矩阵是生成的** —— 两者不矛盾：
#: 「要盯哪些字段」是一个判断（不能从代码里推出来），
#: 「它们有没有被消费」是一个事实（必须从代码里读出来）。
#: 把后者也手写，才是 §8.5.3 反对的那种「派生数据的第二份拷贝」。
TRACKED_FIELDS = (
    "field_id",
    "page",
    "anchor_page",
    "selection",
    "header_inherited",
    "truncation_stats",
    "pdf_sha256",
    "column_header",
    "mapping_version",
    "batch_id",
)

#: 不算进产生/消费点的目录。测试读得再多也不代表产品在用它。
EXCLUDED = ("tests/",)


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(REPO).as_posix()


def collect(
    fields: tuple[str, ...] = TRACKED_FIELDS,
    roots: tuple[pathlib.Path, ...] | None = None,
) -> dict[str, dict[str, list[str]]]:
    """`{字段: {"produce": [位置], "consume": [位置]}}`。

    **产生**：赋值给该名字的属性（`self.page = ...`）、`dataclass` 字段声明、
    以及字典字面量里以该名字作键（`{"page": ...}` —— `to_dict` 的形状）。
    **消费**：读该名字的属性（`record.page`）、或以该名字作字典下标读取。
    """
    out: dict[str, dict[str, list[str]]] = {
        f: {"produce": [], "consume": []} for f in fields
    }
    # 参数化是为了**能真正验证「它会报断线」** —— 零断线的输出证明不了检测有效，
    # 而在真仓库上造一个断线要往 `src/` 里塞垃圾。测试在 tmp 目录上驱动它。
    scan_roots = list(roots) if roots is not None else [REPO / "src", REPO / "scripts"]
    for root in scan_roots:
        for path in sorted(root.rglob("*.py")):
            try:
                rel = _rel(path)
            except ValueError:
                rel = path.as_posix()  # 测试传进来的 tmp 目录不在仓库里
            if any(rel.startswith(x) for x in EXCLUDED) or path.name == "evidence_matrix.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                # dataclass / 类体里的字段声明 ⇒ 产生
                if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                    if node.target.id in out:
                        out[node.target.id]["produce"].append(f"{rel}:{node.lineno}")
                # 字典字面量的键 ⇒ 产生（`to_dict()` 就是这个形状）
                elif isinstance(node, ast.Dict):
                    for key in node.keys:
                        if isinstance(key, ast.Constant) and key.value in out:
                            out[key.value]["produce"].append(f"{rel}:{key.lineno}")
                # 属性访问：Store ⇒ 产生，Load ⇒ 消费
                elif isinstance(node, ast.Attribute) and node.attr in out:
                    bucket = "produce" if isinstance(node.ctx, ast.Store) else "consume"
                    out[node.attr][bucket].append(f"{rel}:{node.lineno}")
                # 关键字实参 `page=...` ⇒ 产生（构造记录时盖出处）
                elif isinstance(node, ast.keyword) and node.arg in out:
                    out[node.arg]["produce"].append(f"{rel}:{node.lineno}")
                # 字典下标读取 `payload["page"]` ⇒ 消费
                elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                    if node.slice.value in out and isinstance(node.ctx, ast.Load):
                        out[node.slice.value]["consume"].append(f"{rel}:{node.lineno}")
    return out


def main() -> int:
    matrix = collect()
    print("证据指针字段的「谁产生 / 谁消费」矩阵（ARCHITECTURE §8.5.3 / 登记册 L-6）")
    print()
    print("| 字段 | 产生点数 | 消费点数 | 首个消费点 |")
    print("|---|---:|---:|---|")
    broken: list[str] = []
    for field in TRACKED_FIELDS:
        produce = matrix[field]["produce"]
        consume = matrix[field]["consume"]
        first = consume[0] if consume else "—"
        mark = "" if consume else "  🔴"
        print(f"| `{field}` | {len(produce)} | {len(consume)}{mark} | {first} |")
        if produce and not consume:
            broken.append(field)
    print()
    if broken:
        print(f"🔴 断线（有产生点、零消费点）：{broken}")
        print("   这正是 §8.5.3 要让它自己显形的东西 —— 算出来了，没人读。")
        return 1
    print("零断线：上表每个有产生点的字段都至少有一处消费点。")
    print("⚠️ 本工具只看「有没有被读」，不看「读得对不对」，也不做类型推断。")
    print("   详见模块 docstring 的「明确抓不到什么」四条。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
