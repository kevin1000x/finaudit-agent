"""`src/service/` 的回归（`02-04` T1 / T2）。

这一层直接对外。它坏起来的样子和内部模块不同：
**用户看到的是「它坏了」，而这个系统的正确行为是说清为什么给不出答案。**
所以本文件盯的头一件事不是功能，是**任何输入都不许 5xx**。
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from service import coverage as cov  # noqa: E402
from service.api import (  # noqa: E402
    MAX_QUESTION_BYTES,
    answer_endpoint,
    coverage_endpoint,
)

SERVICE = REPO_ROOT / "src" / "service"


# ── 任何输入都不许 5xx ──────────────────────────────────────────────────

#: 畸形输入。**不是安全测试** —— 是「`D-022` 那条纪律在 HTTP 边界上还成不成立」。
畸形输入 = [
    None,
    [],
    "",
    {},
    {"question": None},
    {"question": ""},
    {"question": "   "},
    {"question": 123},
    {"question": ["列表不是字符串"]},
    {"question": "x" * (MAX_QUESTION_BYTES + 1)},
    {"question": "毛利率"},                       # 缺主体缺期间
    {"question": "?" * 50},                        # 纯符号
    {"question": "SELECT * FROM users; --"},       # 注入形状
    # 控制字符。**用 `chr()` 构造，不写字面量** —— 字面控制字符会被
    # `tests/test_conformance.py::test_被跟踪的md里没有字面控制字符` 抓（那条抓过三次），
    # 而写进 `.py` 里更糟：直接让文件编译不了（第一版就是这么栽的）。
    {"question": chr(0) + chr(1) + " 控制字符"},
    {"question": "华鑫科技（900001）2023 年的毛利率是多少？", "上传的表格": "偷渡字段"},
]


@pytest.mark.parametrize("payload", 畸形输入)
def test_任何输入都不返回5xx(payload):
    """🔴 本文件存在的第一个理由。

    它会红的场景：有人在端点里让一个异常穿出去（比如直接 `int(...)` 用户输入），
    或者把「认不出指标」当成服务器错误。
    """
    status, body = answer_endpoint(payload)
    assert status < 500, f"{payload!r} 打出了 {status}"
    assert isinstance(body, dict)


def test_认不出指标是200的拒答不是4xx():
    """**拒答是正常业务结果，不是错误**（`D-003`）。

    返回 4xx 等于对用户说「你问错了」，而实际情况是「我们答不了，理由如下」。
    """
    status, body = answer_endpoint({"question": "华鑫科技（900001）2023 年的现金循环周期是多少天？"})
    assert status == 200
    assert body["answer"]["refused"] is True
    assert body["answer"]["refusal"]["code"] == "METRIC_NOT_DEFINED"


def test_只有两种4xx_请求体形状与长度():
    assert answer_endpoint({"question": ""})[0] == 400
    assert answer_endpoint("不是对象")[0] == 400
    assert answer_endpoint({"question": "毛" * MAX_QUESTION_BYTES})[0] == 400
    assert answer_endpoint({"question": "华鑫科技（900001）2023 年的毛利率是多少？"})[0] == 200


def test_多给的字段一律不看():
    """`D-010`：端点只收一个问题字符串。**没有文件上传、没有 CSV、没有表格粘贴。**

    它会红的场景：有人为了「顺手支持一下用户自己的数」加一个 `rows` 参数。
    """
    q = "华鑫科技（900001）2023 年的毛利率是多少？"
    干净 = answer_endpoint({"question": q})[1]
    带私货 = answer_endpoint({"question": q, "rows": [{"is.operating_revenue_current": 1}]})[1]
    assert 干净["page"] == 带私货["page"], "多给的字段影响了结果 —— 那就是收了用户的数据"


def test_端点没有任何读取上传内容的入口():
    """结构断言，不靠「这次没接」。走语法树查函数签名与参数名。"""
    tree = ast.parse((SERVICE / "api.py").read_text(encoding="utf-8"))
    禁用词 = ("upload", "file", "csv", "multipart", "rows", "data_rows")
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for arg in node.args.args + node.args.kwonlyargs:
                if any(w in arg.arg.lower() for w in 禁用词):
                    offenders.append(node.name + "(" + arg.arg + ")")
    assert offenders == [], "端点出现了接收上传内容的参数：" + "; ".join(offenders)


# ── 人读那一页不另写一版 ────────────────────────────────────────────────


def test_响应里的page逐字是render_answer的输出():
    """`D-032`：人读契约只有一套。另写一版就等于对外展示一个没被 `AC-06` 量过的东西。"""
    from agent.answer import render_answer
    from service.api import _flags, _pick_source, _registry

    from agent.answer import answer_question

    q = "华鑫科技（900001）2023 年的期间费用率是多少？"
    _, body = answer_endpoint({"question": q})

    reg = _registry()
    a = answer_question(q, reg, source=_pick_source())
    defn = reg.definitions.get(a.metric_id) if a.metric_id else None
    assert body["page"] == render_answer(a, defn, _flags())


def test_算出来的数在页面上带着它的输入():
    """`D-038 G1` 到了服务这一层还在。它会红的场景：有人为了「让响应小一点」裁掉这一节。"""
    _, body = answer_endpoint({"question": "华鑫科技（900001）2023 年的期间费用率是多少？"})
    assert "这个数是拿哪几个数算出来的" in body["page"]
    assert body["answer"]["inputs"], "结构化响应里也该有输入"


# ── 无状态 ─────────────────────────────────────────────────────────────


def test_同一个问题连问两次结果逐字节相同():
    q = "华鑫科技（900001）2023 年的毛利率是多少？"
    第一次 = answer_endpoint({"question": q})
    第二次 = answer_endpoint({"question": q})
    assert 第一次 == 第二次


def test_清空缓存之后答案不变():
    """`D-021` 豁免三第 2 句判据：**把存储全部清空，不许有东西永久丢失。**

    这里就是那句话的机械验证 —— 缓存清掉，同一个问题给出同一份答案。
    """
    from service.api import _flags, _registry, _source

    q = "华鑫科技（900001）2023 年的期间费用率是多少？"
    before = answer_endpoint({"question": q})
    for cached in (_registry, _flags, _source, cov.coverage):
        cached.cache_clear()
    assert answer_endpoint({"question": q}) == before


def test_模块里没有跨请求的可变状态():
    """`D-021` 豁免三第 1 句判据的结构面：模块级不许有可变容器，不许有 `global`。

    ⚠️ `lru_cache` **不算**：它缓存的是只读的、可由磁盘重推的东西，
    属于豁免三明确允许的「可丢弃缓存」。会红的是有人挂一个
    `_SESSIONS = {}` 或 `_HISTORY = []` 上去。
    """
    files = sorted(SERVICE.glob("*.py"))
    assert len(files) >= 3, f"只扫到 {len(files)} 个文件，这条断言在空转"
    offenders = []
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.Global):
                offenders.append(path.name + ": global")
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                value = node.value
                if isinstance(value, (ast.List, ast.Dict, ast.Set)) and (
                    value.elts if isinstance(value, (ast.List, ast.Set)) else value.keys
                ) == []:
                    offenders.append(path.name + ":" + str(node.lineno) + " 空的可变容器")
        for node in ast.walk(tree):
            if isinstance(node, ast.Global):
                offenders.append(path.name + ":" + str(node.lineno) + " global")
    assert offenders == [], "服务里出现了跨请求可变状态：" + "; ".join(offenders)


# ── 覆盖面 ─────────────────────────────────────────────────────────────


def test_覆盖清单由磁盘推导而不是手写():
    """`N-42` 的判据：这道门扫的集合必须等于它声称在检查的集合。

    手写清单会和真实数据源分叉，而分叉那一刻它看起来仍然是绿的。
    """
    rows = cov.coverage()
    assert rows, "一行覆盖都没有，这条断言在空转"
    import yaml

    磁盘上的 = set()
    for _, directory in cov.SOURCE_DIRS:
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.yaml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            for r in data.get("rows") or []:
                if r.get("stock_code") is not None and r.get("fiscal_year") is not None:
                    磁盘上的.add((str(r["stock_code"]), int(r["fiscal_year"])))
    assert {(r.stock_code, r.fiscal_year) for r in rows} == 磁盘上的


def test_合成夹具必须被标成合成():
    """🔴 把合成数据说成真实数据，比数据本身更严重（`D-010`）。

    2026-09-06 的实情是：**真实抽取结果一行都没有**（`data/extracted/` 不存在），
    能答的全是虚构公司。这条守住那句话会被说出来。
    """
    s = cov.summary()
    assert all(r["nature"] in ("real", "synthetic") for r in s["rows"])
    if s["counts"]["real"] == 0:
        assert "没有任何真实公司的数据" in s["notice"]
    assert "虚构公司" in s["notice"]


def test_没有这家公司与这家公司没有这个指标是两件事():
    """混同就是编。`why_not` 的措辞必须把「我们没有」讲成「我们没有」。"""
    text = cov.why_not("000001", 2023)
    assert "我们没有" in text
    assert "不是「这家公司没有这个指标」" in text


def test_有这家公司但没这一年时把有的年份列出来():
    rows = cov.coverage()
    assert rows, "没有覆盖行，这条在空转"
    code = rows[0].stock_code
    缺的年 = max(r.fiscal_year for r in rows if r.stock_code == code) + 100
    text = cov.why_not(code, 缺的年)
    assert "有的年份是" in text and str(rows[0].fiscal_year) in text


def test_覆盖面之外的提问拿到的是拒答不是一个数():
    """产品最容易犯、也最致命的错：对一家没有数据的公司编出一个数。"""
    status, body = answer_endpoint({"question": "某某公司（000001）2023 年的毛利率是多少？"})
    assert status == 200
    assert body["answer"]["refused"] is True
    assert body["answer"]["value"] is None
    assert body["answer"]["refusal"]["code"] == "UNAVAILABLE"
    assert "我们没有" in body["coverage_note"]


def test_coverage_端点先告诉人能问什么():
    status, body = coverage_endpoint()
    assert status == 200
    assert body["counts"]["total"] == len(cov.coverage())
    assert body["notice"]


def test_多份数据源时按哪一份有这一行来取(tmp_path, monkeypatch):
    """🔴 今天只有一份数据源（真实抽取结果还没落盘，`N-61`）——
    **正因为如此这条才必须现在写**：`data/extracted/` 放进第一个文件的那一刻，
    「只允许一份」的写法会当场把服务弄坏，而那时没人会想到是这里。

    它会红的场景：有人把多源取数改回「挑第一份」或「多于一份就报错」。
    """
    from service import api

    extra = tmp_path / "extra"
    extra.mkdir()
    (extra / "another.yaml").write_text(
        "meta:\n"
        "  fixture_id: another\n"
        "rows:\n"
        '  - stock_code: "900777"\n'
        "    fiscal_year: 2024\n"
        "    is.operating_revenue_current: 2000\n"
        "    is.operating_cost: 1200\n"
        "    notes.restatement_flag: false\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        cov, "SOURCE_DIRS", cov.SOURCE_DIRS + (("real", extra),), raising=True
    )
    cov.coverage.cache_clear()
    try:
        assert cov.covered("900777", 2024), "新加的那一份没进覆盖清单"
        # 原来那一份还在
        assert cov.covered("900001", 2023)

        # 新那一份能答：毛利率 =（2000-1200）/2000 = 0.4
        _, body = api.answer_endpoint({"question": "某公司（900777）2024 年的毛利率是多少？"})
        assert body["answer"]["refused"] is False, body["answer"].get("refusal")
        assert body["answer"]["value"] == "0.4"

        # 老那一份也还能答 —— 两份共存，不是二选一
        _, old = api.answer_endpoint({"question": "华鑫科技（900001）2023 年的毛利率是多少？"})
        assert old["answer"]["refused"] is False
    finally:
        cov.coverage.cache_clear()


# ── 「真实 / 合成」这条线：贴错标签比数据本身更严重（`D-010`） ──────────────


def _dir_with(tmp_path, name, body):
    d = tmp_path / name
    d.mkdir()
    (d / "x.yaml").write_text(body, encoding="utf-8")
    return d


ROW = 'rows:\n  - stock_code: "900888"\n    fiscal_year: 2024\n'


def test_落在真实目录里但没有kind标记的按合成算(tmp_path, monkeypatch):
    """**红的时候是什么样**：谁往 `data/extracted/` 里放了一份合成文件，
    它就被当成年报原文对外展示 —— 而页面上不会有任何一处露馅。

    `nature` 以文件自己的 `meta.kind` 为准，目录只是「去哪儿找」。
    这是 `N-42` 的形状：一道门扫的集合必须等于它声称在检查的集合。
    """
    d = _dir_with(tmp_path, "extracted", "meta:\n  fixture_id: 冒充的\n" + ROW)
    monkeypatch.setattr(cov, "SOURCE_DIRS", (("real", d),), raising=True)
    cov.coverage.cache_clear()
    try:
        assert [r.nature for r in cov.coverage()] == ["synthetic"]
        assert cov.summary()["counts"] == {"real": 0, "synthetic": 1, "total": 1}
    finally:
        cov.coverage.cache_clear()


def test_自称real但PDF指纹不合格的也按合成算(tmp_path, monkeypatch):
    """光写一句 `kind: real` 不够 —— 得给得出那份年报 PDF 的 SHA-256。

    指纹是这条证据链里**唯一能脱离本仓库独立验证**的锚点：
    去巨潮下同一份年报算一遍，对得上才说明读的是同一份文件。
    """
    d = _dir_with(
        tmp_path, "extracted", 'meta:\n  fixture_id: 半真\n  kind: real\n  source_pdf_sha256: "太短"\n' + ROW
    )
    monkeypatch.setattr(cov, "SOURCE_DIRS", (("real", d),), raising=True)
    cov.coverage.cache_clear()
    try:
        assert [r.nature for r in cov.coverage()] == ["synthetic"]
    finally:
        cov.coverage.cache_clear()


def test_一份文件判成合成不会连累后面的文件(tmp_path, monkeypatch):
    """**红的时候是什么样**：判定写成了覆盖循环变量，
    第一份文件是合成的，后面所有真实数据就都被标成合成 —— 悄无声息地少报覆盖面。
    """
    d = tmp_path / "extracted"
    d.mkdir()
    (d / "a-合成.yaml").write_text("meta:\n  fixture_id: a\n" + ROW, encoding="utf-8")
    (d / "b-真实.yaml").write_text(
        "meta:\n  fixture_id: b\n  kind: real\n  short_name: 某公司\n"
        '  source_pdf_sha256: "' + "a" * 64 + '"\n'
        'rows:\n  - stock_code: "900999"\n    fiscal_year: 2024\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cov, "SOURCE_DIRS", (("real", d),), raising=True)
    cov.coverage.cache_clear()
    try:
        assert cov.summary()["counts"] == {"real": 1, "synthetic": 1, "total": 2}
    finally:
        cov.coverage.cache_clear()


def test_合成夹具的公司简称不显示(tmp_path, monkeypatch):
    """合成夹具里的「公司名」是虚构的。把它当公司名显示出去，
    等于请人去搜一家不存在的公司 —— 而页面上它和真实公司长得一模一样。
    """
    d = _dir_with(tmp_path, "extracted", "meta:\n  fixture_id: x\n  short_name: 华鑫科技\n" + ROW)
    monkeypatch.setattr(cov, "SOURCE_DIRS", (("real", d),), raising=True)
    cov.coverage.cache_clear()
    try:
        assert cov.coverage()[0].short_name == ""
    finally:
        cov.coverage.cache_clear()


# ── 给人看的字符串里不许有 Markdown（浏览器实跑撞出来的） ──────────────────


def test_端点返回的文案里不许出现Markdown强调号():
    """**红的时候是什么样**：证据页是纯文本、网页把它当纯文本渲染，
    于是 `**我们没有**` 连着星号一起印在用户眼前。

    2026-09-06 在浏览器里第一次看真实答案时撞到的：那句
    「只导出了**人工逐字段核对过**的字段」在页面上带着四个星号。
    源头是写的人（我）默认这段文字会被 Markdown 渲染 —— 它不会。
    """
    import re

    bad = []
    for text in (
        cov.summary()["notice"],
        cov.why_not("000001", 2023),
        cov.why_not("900001", 1999),
    ):
        if re.search(r"\*\*", text):
            bad.append(text)
    _, body = answer_endpoint({"question": "600519 2023 年的资产负债率是多少"})
    if "**" in body["page"]:
        bad.append("render_answer 的正文")
    assert bad == [], f"这些给人看的文案里带着 Markdown 强调号：{bad}"


def test_没有这家公司时不许报出别家公司的年报出处():
    """🔴 **红的时候是什么样**：问「000651 2023 年的资产负债率」，证据页答
    「万华化学 000651 · 2023 年年度报告（年报 PDF SHA-256 87411c60…）」——
    公司名与指纹来自数据源文件，代码与年份来自提问，拼成一条**伪造的出处**。

    2026-09-06 在浏览器里实跑撞到的。它比答错一个数严重得多：
    这条产品线卖的就是「出处可独立核验」，而这里的出处是编的。
    """
    _, body = answer_endpoint({"question": "000651 2023 年的资产负债率是多少"})
    page, src = body["page"], body["answer"]["evidence"]["data_source"]
    assert body["answer"]["refusal"]["code"] == "UNAVAILABLE"
    # 别家公司的名字、别家年报的指纹，一个都不许出现
    for leaked in ("万华化学", "贵州茅台", "87411c60", "2125ff97"):
        assert leaked not in page, f"证据页泄漏了别家公司的出处：{leaked}"
        assert leaked not in str(src), f"data_source 泄漏了别家公司的出处：{leaked}"
    # 而且要说清「查了哪几份、都没有」，不是空着
    assert "都没有" in str(src)
