"""README 里的示例输出必须是系统**现在**的输出。

🔴 2026-11-01 实测：README「它长什么样」那段示例写着「资产负债率 17.98%」判 ✅、
「万华化学 2019 年资产负债率 62%」判 ❌ —— 而 `D-045`（2026-10-31）之后系统对两条都判 ⚠️。
README 说「逐字是系统的输出」，那一天起这句话就是假的，而没有任何东西会发现。

⇒ 这里把 README 的三段示例逐字对到 `POST /verify` 的 `page` 上（服务返回的就是它）。
系统输出变了而 README 没跟着改，这条就红。
"""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

import pytest

from service import api

REPO = Path(__file__).resolve().parent.parent
README = REPO / "README.md"


@pytest.fixture(autouse=True)
def _离线(monkeypatch):
    """README 印的是「没配模型」时的输出（「没配模型时整条路径离线跑完」）。
    本机环境变量里配了模型时，同一段话可能多认出一个说法 —— 那不是 README 过期。"""
    monkeypatch.setattr(api, "_provider", lambda: None)


def _text() -> str:
    return README.read_text(encoding="utf-8")


def _quote_after(text: str, marker: str) -> str:
    """`marker` 之后第一行以 `> ` 开头的引用 —— README 里示例的输入。"""
    for line in text.split(marker, 1)[1].splitlines():
        if line.startswith("> "):
            return line[2:].strip()
    raise AssertionError("README 里 " + marker + " 之后没有输入引用")


def _block_after(text: str, marker: str) -> list:
    """`marker` 之后第一个代码块的各行（去掉行尾空白）。"""
    after = text.split(marker, 1)[1]
    body = after.split("```", 2)[1]
    lines = body.splitlines()[1:]  # 第一行是 ``` 后面的语言标记（这里为空）
    return [line.rstrip() for line in lines]


def _page(text: str) -> list:
    status, body = api.verify_endpoint({"text": text})
    assert status == 200
    return [line.rstrip() for line in body["page"].splitlines()]


def _contiguous(needle: list, haystack: list) -> bool:
    n = len(needle)
    return any(haystack[i : i + n] == needle for i in range(len(haystack) - n + 1))


def test_首页同一读数的两种表述():
    section = _text().split("## 茅台净利率", 1)[1].split("\n## ", 1)[0]
    sample = _quote_after(section, "复制下面这一行")
    status, result = api.verify_endpoint({"text": sample})
    assert status == 200
    first, second = result["report"]["claims"]
    assert (first["verdict"], second["verdict"]) == ("AMBIGUOUS_BASIS", "CONSISTENT")
    answer = second["answer"]
    assert first["answer"]["value"] == answer["value"]
    assert answer["metric_id"] == "net_profit_margin_attributable"
    for field, label in (("is.net_profit_attributable_to_parent", "归母净利润"),
                         ("is.operating_revenue_current", "营业收入")):
        source = answer["provenance"][field]
        assert source["column_header"] in section
        amount = Decimal(answer["inputs"][field])
        assert re.search(rf"第 {source['page']} 页列示{label}\s*{re.escape(f'{amount:,.2f}')} 元", section)


def test_它长什么样_逐字是系统的输出():
    text = _text()
    输入 = _quote_after(text, "## 它长什么样")
    写着的 = _block_after(text, "输出（报告头部，逐字是系统的输出）")
    页 = _page(输入)
    小计 = next(i for i, line in enumerate(页) if line.startswith("小计："))
    assert 写着的 == 页[: 小计 + 1]


def test_取数那一节的节选在真实页面里():
    text = _text()
    写着的 = _block_after(text, "取数那一节长这样")
    assert 写着的 and "年报第" in "".join(写着的), "节选里没有页码，本条在空转"
    输入 = re.search(r"取数那一节长这样（节选自「(.+?)」那一页）", text)
    assert 输入, "README 没写这段节选取自哪一页"
    assert _contiguous(写着的, _page(输入.group(1)))


def test_问一个没有的口径时的节选在真实页面里():
    text = _text()
    输入 = _quote_after(text, "### 问一个系统没有的口径时")
    写着的 = _block_after(text, "### 问一个系统没有的口径时")
    assert _contiguous(写着的, _page(输入))


def test_对照_改一个字就不再对得上():
    """负控制：上面三条的比对真的会红，不是恒真。"""
    text = _text()
    写着的 = _block_after(text, "输出（报告头部，逐字是系统的输出）")
    改过的 = [line.replace("流动比率 4.0", "流动比率 4.6") for line in 写着的]
    assert 改过的 != 写着的, "示例里没有「流动比率 4.0」，负控制在空转"
    页 = _page(_quote_after(text, "## 它长什么样"))
    assert not _contiguous(改过的, 页)
