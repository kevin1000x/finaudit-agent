"""`L-26` 的落地：**文档里点名的符号必须在代码里存在**。

登记册原话是「文档里出现的字段名 / 类名必须在代码中存在（**文档也是一份派生数据**）」，
出处 `references/hello-agents-ch06-frameworks.md` §9.5。

## 它挡的是什么（真实的，不是假想）

**计划先于实现写成，于是计划里的名字与实现里的名字会分叉** ——
而分叉之后，后来的文档会**照抄计划**，把一个不存在的符号当成真的往下传。
`N-43` 记的就是这条路径的一个完整实例：一句代码注释编出来的排期
被 `COMPUTED-VALUES` 与交接文档照抄，成了「wave 5 要做三支 kind」这个说法的源头。

本检查建立当天（2026-08-31）**一次扫出 6 个已经分叉的名字**，其中 `locate.resolve_column`
是 2026-08-28 手工发现的（`01.5-06-PLAN` 点名它做变异对象，而它根本不存在），
另外 5 个此前**没有任何人发现**。

## 为什么不做成第八道门

与 `tests/test_evidence_ids.py`（`J-6`）、`tests/test_plan_waves.py` 同一判断：
`check_gates.py` 的 R2 / R4 / R5 对每道**登记**门禁都有连带要求
（具名负控制 + 进 `gates.yml` + 同步 `rules/commands.md`），
为一条能用 pytest 表达的检查再加一道登记门禁是净增流程开销，触 `D-009` 的 30% 红线。
**pytest 是那条 `&&` 链的第一环，跑不掉。**

## 明确抓不到什么

⚠️ 五条，一条都不许被读成「文档里的说法都对」：

1. **只查「符号存不存在」，不查「说法对不对」。**
   `L-47` 那条「已核 `RefusalCode` 目前仍为 7 支」（实际 9 支）**本检查抓不到** ——
   它是一个**计数断言**，里面的符号 `RefusalCode` 完全存在。
   这一类只能靠人核，**别指望这道检查**。
2. **只认反引号里形如 `模块.符号` 的写法。** 散文里写「那个 resolve_column 函数」抓不到。
3. **只认本仓 `src/` 与 `scripts/` 的模块名。** 外部项目的符号不参与。
4. **本检查有自指成本。** 一条**关于某个不存在符号的记述**（例如
   「那个名字已经改了」）如果把它写进反引号里，就会让它重新变成「在场」，
   于是必须登记。⇒ 说明性文字里提到不存在的符号时，**不要用反引号包成 `模块.符号`**。
   2026-08-31 建立当天就撞了一次：写「某条登记已过期并移除」时把那个名字写了出来。
5. **符号全集取自 AST 的定义点与属性名**，宽于「公开接口」——
   一个只在某个函数里出现过一次的局部变量名也算「存在」。
   **宁可漏判，不许误报**：误报会让人去放宽这道检查，而放宽会让它退化。
"""

from __future__ import annotations

import ast
import collections
import re
import subprocess
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent

#: 不参与检查的路径前缀，**每条都要给理由**。
EXCLUDED_PREFIXES = {
    # 冻结产物：`D-012` 不许改，里面的旧字段名**永远**修不了。
    # 把改不了的东西纳入检查，只会逼出一条豁免规则。
    "docs/agent/poc-01/": "冻结产物（D-012 不许改）",
    "eval/frozen-01/": "冻结评测集（D-012 不许改）",
    # 外部项目的阅读产物：里面的符号属于别人的代码库。
    "references/": "外部项目的阅读产物，符号不属于本仓",
    # 会话交接文档：写给下一轮读的快照，会大量引用当时的状态。
    "claudedocs/": "会话交接快照，非权威文档",
    # 归档的变更提案：已经归档，按定义不再跟着代码走。
    "docs/spec/archive/": "已归档的变更提案",
}

#: **文档里点名、但代码里没有**的符号 —— 逐条登记并写明「实际是什么」。
#:
#: **这不是豁免名单，是一张对照表。** 豁免名单让某几处不受检查；
#: 本表要求每一处都写出**它实际对应的东西**，于是下一个读到那份文档的人
#: 不会把它当成真的往下传。多一处未登记的就红。
KNOWN_ABSENT_SYMBOLS = {
    # —— 计划写于实现之前，名字后来变了 ——
    "record.SelectionProvenance": "实际是 `record.Selection`（`01.5-01-PLAN` 写于实现之前）",
    "crosscheck.ComparisonSource": (
        "**没有做成枚举**。对照源的标识是模块级常量 `crosscheck.SOURCE_AKSHARE` "
        "（`01.5-04-PLAN` 设想的是一个 PDF/AKSHARE 两支的枚举）"
    ),
    "crosscheck.AkshareColumnMapping": (
        "实际拆成了 `crosscheck.AkshareEntry` 与 `crosscheck.AkshareMappingTable` 两个"
    ),
    "formula.MetricResult": "实际是 `formula.ComputeResult`",
    "locate.resolve_column": (
        "**从来不存在**。列角色判定在 `locate._role_of`（由 `bind_columns` 调用）。"
        "`01.5-06-PLAN` 点名它做变异对象，2026-08-28 实跑时才发现 —— 见 `VERIFICATION.md` §A"
    ),
    # —— 曾经存在，已被删除 ——
    "crosscheck.align_references": "**已删除**（复核 `RV-5`，2026-08-28 操作者裁决）",
    "check_gates.iter_reference_docs": (
        "**已随 `references/` 一并移出本仓**（`D-043`，2026-09-11）。"
        "它是 R5 读阅读笔记用的非递归 glob；R5、它的 7 条测试、"
        "`check_reading_ledger.py` 与 CI 链上那一条同批移出，六道门减为五道门。"
        "台账 `OPEN-ITEMS.md` 那一条**留档不删** —— 它记的是当时的事实。"
    ),
    # —— 被淘汰的候选字段 id ——
    # （`notes.nonrecurring_pl_total_pretax` 曾登记在此，2026-08-31 由
    #   `test_对照表里没有过期条目` 判为过期并移除：它只出现在
    #   `docs/spec/archive/`，而那条路径已在 `EXCLUDED_PREFIXES` 里。）
    "notes.listing_first_disclosure_flag": "被淘汰的候选字段：在夹具里却不属于任何定义的 `source_fields`",
    "notes.nonrecurring_pl_net": "POC-01 期的旧名，现为 `notes.nonrecurring_pl_net_attributable_to_parent`",
}

#: `模块.符号` 里当 `符号` 是这些时，`模块.符号` 其实是**文件名**不是符号引用。
_FILE_SUFFIXES = frozenset({"py", "md", "yaml", "yml", "json", "txt", "toml", "cfg", "lock"})

_TOKEN = re.compile(r"`([a-z_][a-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)(\(\))?`")


def _code_symbols() -> tuple[set[str], set[str]]:
    """`(全部符号名, 全部模块名)`。走 AST，不用正则。"""
    symbols: set[str] = set()
    modules: set[str] = set()
    for path in sorted((REPO / "src").rglob("*.py")) + sorted((REPO / "scripts").glob("*.py")):
        modules.add(path.stem)
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                symbols.add(node.name)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                symbols.add(node.id)
            elif isinstance(node, ast.arg):
                symbols.add(node.arg)
            elif isinstance(node, ast.Attribute):
                symbols.add(node.attr)
    return symbols, modules


def _declared_field_ids() -> set[str]:
    """数据字段 id 的全集。

    **必须排掉**：`notes` 既是一个模块名（`extractor/notes.py`），
    又是一个字段命名空间（`notes.restatement_flag`）。不排的话
    每个 `notes.*` 字段引用都会被当成「模块里的符号不存在」。
    """
    out: set[str] = set()
    for path in (REPO / "data" / "mappings" / "pdf").glob("*.yaml"):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for entry in raw.get("entries") or []:
            out.add(entry.get("field_id"))
    for path in (REPO / "metrics").glob("*.yaml"):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for field in raw.get("source_fields") or []:
            out.add(field.get("id"))
    return {x for x in out if x}


def _markdown_files() -> list[str]:
    """`-z` + `--others --exclude-standard`，理由同 `check_xrefs`（台账 `N-42`）。"""
    proc = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "*.md"],
        cwd=REPO, capture_output=True, text=True, encoding="utf-8", check=True,
    )
    return [
        rel
        for rel in proc.stdout.split(chr(0))
        if rel and not any(rel.startswith(p) for p in EXCLUDED_PREFIXES)
    ]


def _scan() -> tuple[int, dict[str, list[str]]]:
    """`(命中数, {对不上的符号: [出处]})`。"""
    symbols, modules = _code_symbols()
    field_ids = _declared_field_ids()
    hits = 0
    missing: dict[str, list[str]] = collections.defaultdict(list)
    for rel in _markdown_files():
        text = (REPO / rel).read_text(encoding="utf-8")
        for match in _TOKEN.finditer(text):
            module, symbol = match.group(1), match.group(2)
            token = f"{module}.{symbol}"
            if module not in modules or symbol in _FILE_SUFFIXES or token in field_ids:
                continue
            if symbol in symbols:
                hits += 1
            else:
                line = text[: match.start()].count(chr(10)) + 1
                missing[token].append(f"{rel}:{line}")
    return hits, dict(missing)


def test_文档里点名的符号都在代码里存在或已登记为对照():
    """`L-26`。**未登记的对不上即红。**"""
    hits, missing = _scan()
    unregistered = sorted(k for k in missing if k not in KNOWN_ABSENT_SYMBOLS)
    assert unregistered == [], (
        "这些符号在文档里被点名，代码里却没有："
        + "；".join(f"{k}（{'、'.join(missing[k])}）" for k in unregistered)
        + "。要么改文档，要么它确实是个「实际叫别的名字」的历史引用 —— "
        "那就进 KNOWN_ABSENT_SYMBOLS 并写明**实际是什么**。"
    )


def test_扫描确实扫到了东西():
    """基线。**没有这一条，上面那条在扫描器坏掉时也会绿。**

    集合相等对空集也成立 —— 与 `test_留痕采集点唯一这条断言不是空转` 是同一个道理。
    """
    hits, _ = _scan()
    assert hits >= 50, f"只命中 {hits} 处符号引用，扫描范围可疑"
    assert len(_markdown_files()) >= 30


def test_对照表里没有过期条目():
    """登记了却已经不再出现的符号必须清掉。

    一张含过期条目的对照表，会让下一个人以为那份文档里还写着它。
    """
    _, missing = _scan()
    stale = sorted(k for k in KNOWN_ABSENT_SYMBOLS if k not in missing)
    assert stale == [], f"对照表里这些符号已经不在任何文档里了：{stale}"


def test_每条登记都写明了实际是什么():
    """**理由不许是空的，也不许是模板化的一句话。**

    这张表的价值全在「实际对应什么」那一栏 —— 只写「历史遗留」等于没写。
    """
    for token, reason in KNOWN_ABSENT_SYMBOLS.items():
        assert len(reason) >= 12, f"{token} 的理由过短：{reason!r}"
    # 反模板：理由必须两两不同。复制粘贴必然重复，重复即红。
    reasons = list(KNOWN_ABSENT_SYMBOLS.values())
    assert len(set(reasons)) == len(reasons), "对照表里有两条理由完全相同 —— 像是复制粘贴的"


def test_排除路径每条都有理由():
    """排除项是这道检查最容易被悄悄放宽的地方，所以每条都要写明为什么。"""
    assert EXCLUDED_PREFIXES, "排除表为空？那扫描范围的边界就没有被声明过"
    for prefix, reason in EXCLUDED_PREFIXES.items():
        assert prefix.endswith("/"), f"{prefix} 不是目录前缀"
        assert len(reason) >= 6, f"{prefix} 的排除理由过短：{reason!r}"
