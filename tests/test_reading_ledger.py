"""`scripts/check_reading_ledger.py` 的回归测试（台账 N-31）。

这道门禁是为了拦住一个**已经连续发生四次**的失效模式：
`references/` 的覆盖表声称读过某文件，正文里却零对应内容。

**这些测试锁的不是「门禁能跑」，是「门禁真的会红」。**
`references/deepseek-harness-docs-part2.md` 记的 `testing.md:34` 逐字写着：
`A guard only guards if the regression actually fails it`
——所以每条正向断言都配一条负向用例：把缺陷造出来，看它变红。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "check_reading_ledger",
    Path(__file__).resolve().parent.parent / "scripts" / "check_reading_ledger.py",
)
assert _SPEC and _SPEC.loader
crl = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(crl)


@pytest.fixture
def scratch():
    p = crl.REPO / "references" / "__test_tmp__.md"
    yield p
    if p.exists():
        p.unlink()


LEDGER_HEAD = "| 文件 | 行数 | 读到什么程度 |\n|---|---:|---|\n"


def test_大文件声称全文而正文零出现_必须报红(scratch):
    """第 2 号事故的形状：tools/base.py 453 行标「全文」，正文里只有台账那一行。"""
    scratch.write_text(
        LEDGER_HEAD + "| `pkg/big_module.py` | 453 | **全文** |\n\n## 1. 别的内容\n正文没提它。\n",
        encoding="utf-8",
    )
    problems = crl.check_file(scratch)
    assert len(problems) == 1
    assert "big_module.py" in problems[0]


def test_正文提到了就通过(scratch):
    scratch.write_text(
        LEDGER_HEAD
        + "| `pkg/big_module.py` | 453 | **全文** |\n\n## 1. pkg/big_module.py 的结构\n它做了 X。\n",
        encoding="utf-8",
    )
    assert crl.check_file(scratch) == []


def test_正文只写短形式也算命中(scratch):
    """台账写全路径、正文写 basename 是常见写法，不该报红。"""
    scratch.write_text(
        LEDGER_HEAD
        + "| `hello_agents/agents/react_agent.py` | 1241 | **全文** |\n\n## 1. 范式\n见 `react_agent.py:338`。\n",
        encoding="utf-8",
    )
    assert crl.check_file(scratch) == []


def test_小文件允许并组讨论_不报红(scratch):
    """阈值的意义：逐个要求小文件有独立段落，会把门禁变成一张豁免清单。"""
    scratch.write_text(
        LEDGER_HEAD + "| `pkg/__init__.py` | 17 | **全文** |\n\n## 1. 导出面\n整体看过。\n",
        encoding="utf-8",
    )
    assert crl.check_file(scratch) == []


def test_台账没写行数时按大处理_宁可报红(scratch):
    scratch.write_text(
        LEDGER_HEAD + "| `pkg/unknown_size.py` | ? | **全文** |\n\n## 1. 别的\n没提它。\n",
        encoding="utf-8",
    )
    assert len(crl.check_file(scratch)) == 1


def test_章节区间_正文引区间内单行即算命中(scratch):
    scratch.write_text(
        LEDGER_HEAD + "| `ch6:1288-1305` | 18 | **全文** |\n\n## 1. 小结\n见 `ch6:1299`。\n",
        encoding="utf-8",
    )
    assert crl.check_file(scratch) == []


def test_章节区间_正文引区间外的行不算命中(scratch):
    """负向：1500 不在 1288-1305 内，不得被当成支撑。"""
    scratch.write_text(
        LEDGER_HEAD + "| `ch6:1288-1305` | 999 | **全文** |\n\n## 1. 别处\n见 `ch6:1500`。\n",
        encoding="utf-8",
    )
    assert len(crl.check_file(scratch)) == 1


@pytest.mark.parametrize("mark", ["待读", "待填", "未读", "UNVERIFIED"])
def test_未声称读过的标注一律跳过(scratch, mark):
    scratch.write_text(
        LEDGER_HEAD + f"| `pkg/big_module.py` | 453 | **{mark}** |\n\n## 1. 别的\n没提它。\n",
        encoding="utf-8",
    )
    assert crl.check_file(scratch) == []


def test_非台账表不被当成台账(scratch):
    """正文里的启示表、判据表同样是 markdown 表格，误判会产生大量假红。"""
    scratch.write_text(
        "## 1. 骨架启示\n\n| 条目 | 落地点 | 说明 |\n|---|---|---|\n"
        "| `pkg/big_module.py` | D-003 | 部分借鉴，全文见上 |\n",
        encoding="utf-8",
    )
    assert crl.check_file(scratch) == []


def test_显式豁免生效且是显式的(scratch):
    scratch.write_text(
        LEDGER_HEAD + "| `pkg/big_module.py` | 453 | **全文** |\n\n## 1. 别的\n没提它。\n",
        encoding="utf-8",
    )
    rel = scratch.relative_to(crl.REPO).as_posix()
    assert len(crl.check_file(scratch)) == 1
    crl.EXEMPT.add((rel, "pkg/big_module.py"))
    try:
        assert crl.check_file(scratch) == []
    finally:
        crl.EXEMPT.discard((rel, "pkg/big_module.py"))


def test_真实仓库当前为绿且零豁免():
    """锁住两件事：现状是绿的；且不是靠豁免堆出来的绿。

    豁免清单一旦长起来，这道门就退化成一张「已知例外」的目录——
    与它要防的「看起来可追溯、实际不可复核」是同一个毛病。
    """
    assert crl.EXEMPT == set(), "新增豁免必须连同理由一起写进 docstring 并更新本测试"
    problems: list[str] = []
    for path in crl.tracked_references():
        problems.extend(crl.check_file(path))
    assert problems == [], "\n".join(problems)
