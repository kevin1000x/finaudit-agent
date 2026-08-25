"""巨潮下载链路的回归 —— D-022 的两侧、三处安全约束、台账 N-3 的抽完就删。

**不联网。** 出网点 `download._urlopen` 被换成一个记录请求的假实现，
因此「不发起第二次请求」这类断言是可机械检查的，不靠观察网络。
"""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from extractor import download as dl
from semantic_layer.resolve import Refusal, RefusalCode

ORG_ID = "gssh0600519"
ADJUNCT = "finalpage/2024-04-09/1219546600.PDF"
PDF_BYTES = b"%PDF-1.7\n" + b"x" * 500
PDF_SHA = hashlib.sha256(PDF_BYTES).hexdigest()

STOCK_LIST = {"stockList": [{"code": "600519", "orgId": ORG_ID, "zwjc": "贵州茅台"}]}
ANNOUNCEMENTS = {
    "announcements": [
        {
            "announcementTitle": "2023年年度报告摘要",
            "adjunctUrl": "finalpage/2024-04-09/1219546601.PDF",
            "announcementTime": "1712592000000",
        },
        {
            "announcementTitle": "2023年年度报告（英文版）",
            "adjunctUrl": "finalpage/2024-04-09/1219546602.PDF",
            "announcementTime": "1712592000000",
        },
        {
            "announcementTitle": "2023年年度报告",
            "adjunctUrl": ADJUNCT,
            "announcementTime": "1712592000000",
        },
    ]
}


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body
        self._pos = 0

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            chunk, self._pos = self._body[self._pos:], len(self._body)
            return chunk
        chunk = self._body[self._pos: self._pos + size]
        self._pos += len(chunk)
        return chunk

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc) -> bool:
        return False


class _Recorder:
    """记录每一次实际发起的请求。「没发起第二次请求」由它来证。"""

    def __init__(self, routes: dict, pdf_body: bytes = PDF_BYTES) -> None:
        self.routes = routes
        self.pdf_body = pdf_body
        self.urls: list[str] = []

    def __call__(self, opener, request: urllib.request.Request):
        url = request.full_url
        self.urls.append(url)
        if url in self.routes:
            handler = self.routes[url]
            if isinstance(handler, Exception):
                raise handler
            return _FakeResponse(handler)
        if url.startswith(dl.STATIC_BASE):
            return _FakeResponse(self.pdf_body)
        raise AssertionError(f"测试没有为 {url} 准备响应")


def _install(monkeypatch, routes=None, pdf_body: bytes = PDF_BYTES) -> _Recorder:
    routes = routes if routes is not None else {
        dl.STOCK_LIST_URL: json.dumps(STOCK_LIST).encode("utf-8"),
        dl.QUERY_URL: json.dumps(ANNOUNCEMENTS).encode("utf-8"),
    }
    recorder = _Recorder(routes, pdf_body=pdf_body)
    monkeypatch.setattr(dl, "_urlopen", recorder)
    return recorder


# --------------------------------------------------------------------------
# D-022 决策一：数据源不可达 → Refusal(UNAVAILABLE)，带非空责任方
# --------------------------------------------------------------------------


def test_refusalcode_有九支且_unavailable_语义逐字取自_d022(monkeypatch):
    """D-022 判据 1 + D-025 判据 1。取值域是 AC-02 的契约，成员数要被锁住。"""
    assert len(RefusalCode) == 9
    assert RefusalCode.UNAVAILABLE.value == "口径服务或数据源不可达"
    assert RefusalCode.RECONCILIATION_FAILED.value == "该抽取批次的会计恒等式校验未通过"


def test_网络不可达返回带责任方的拒答而不是抛异常(monkeypatch):
    """D-022 判据 2 + L-47 + L-9。

    抛异常的话，这一情境在证据链里是**一片空白**——而 D-003 要求
    「任何回答如果给不出证据链，视为失败，不视为降级成功」。
    """
    _install(monkeypatch, routes={dl.STOCK_LIST_URL: urllib.error.URLError("timed out")})
    outcome = dl.fetch_annual_report("600519", 2023)
    assert isinstance(outcome, Refusal)
    assert outcome.code is RefusalCode.UNAVAILABLE
    assert isinstance(outcome.source, str) and outcome.source.strip()
    assert outcome.source == dl.SOURCE_STOCK_LIST


def test_上游返回_5xx_也走拒答(monkeypatch):
    err = urllib.error.HTTPError(dl.QUERY_URL, 503, "Service Unavailable", {}, None)
    _install(monkeypatch, routes={
        dl.STOCK_LIST_URL: json.dumps(STOCK_LIST).encode("utf-8"),
        dl.QUERY_URL: err,
    })
    outcome = dl.fetch_annual_report("600519", 2023)
    assert isinstance(outcome, Refusal)
    assert outcome.code is RefusalCode.UNAVAILABLE
    assert outcome.source == dl.SOURCE_QUERY


def test_拒答的责任方进得了机读字典与人看的正文():
    """L-9：只说「证据不足」不合格。责任方两面都要出现，否则它会被当成可选值丢掉。"""
    from semantic_layer.resolve import render_refusal

    refusal = Refusal(RefusalCode.UNAVAILABLE, "取不到", source=dl.SOURCE_QUERY)
    assert refusal.to_dict()["source"] == dl.SOURCE_QUERY
    assert dl.SOURCE_QUERY in render_refusal(refusal)


# --------------------------------------------------------------------------
# D-022 决策二 / 判据 3：配置缺陷抛异常，不变成 Refusal
# --------------------------------------------------------------------------


def test_股票代码不在清单里必须抛异常而不是返回拒答(monkeypatch):
    """D-022 判据 3 的负向用例。

    这条线的作用是**防止拒答码退化成万能错误袋**。没有它，`UNAVAILABLE`
    会迅速吸走所有 I/O 异常，AC-02「拒答理由可机读」就失去意义。
    """
    _install(monkeypatch)
    with pytest.raises(dl.UnknownStockCode):
        dl.fetch_annual_report("999999", 2023)

    # 并且它确实没走成 Refusal —— 只断言抛了异常，挡不住「两条路都通」。
    client = dl.CninfoClient()
    try:
        outcome = client.org_id("999999")
    except dl.UnknownStockCode:
        outcome = "raised"
    assert outcome == "raised"
    assert not isinstance(outcome, Refusal)


# --------------------------------------------------------------------------
# T-01.5-01：主机白名单，含重定向
# --------------------------------------------------------------------------


def test_adjunct_指向白名单外主机时不发起下载请求(monkeypatch):
    evil = dict(ANNOUNCEMENTS)
    evil["announcements"] = [
        {
            "announcementTitle": "2023年年度报告",
            "adjunctUrl": "https://evil.example.com/a.pdf",
            "announcementTime": "1712592000000",
        }
    ]
    recorder = _install(monkeypatch, routes={
        dl.STOCK_LIST_URL: json.dumps(STOCK_LIST).encode("utf-8"),
        dl.QUERY_URL: json.dumps(evil).encode("utf-8"),
    })
    outcome = dl.fetch_annual_report("600519", 2023)
    assert isinstance(outcome, Refusal)
    assert outcome.code is RefusalCode.UNAVAILABLE
    assert not any("evil.example.com" in u for u in recorder.urls)
    assert len(recorder.urls) == 2  # 只有前两步，第三步没发


def test_重定向到白名单外主机在跟随之前被拦下():
    """只检查最初的 URL 是不够的：上游回一个 302，白名单就形同虚设。"""
    handler = dl._SafeRedirectHandler()
    request = urllib.request.Request(dl.STOCK_LIST_URL)
    with pytest.raises(dl.DisallowedHost):
        handler.redirect_request(request, None, 302, "Found", {},
                                 "https://evil.example.com/x")


def test_重定向到白名单内主机允许跟随():
    """负控制的另一半：拦下一切等于没有白名单，只是换了种坏法。"""
    handler = dl._SafeRedirectHandler()
    request = urllib.request.Request(dl.STOCK_LIST_URL)
    redirected = handler.redirect_request(request, None, 302, "Found",
                                          {}, dl.STATIC_BASE + ADJUNCT)
    assert redirected is not None
    assert dl.host_of(redirected.full_url) in dl.ALLOWED_HOSTS


# --------------------------------------------------------------------------
# T-01.5-02：体积上限
# --------------------------------------------------------------------------


def test_超过体积上限中止下载并拒答(monkeypatch, tmp_path):
    monkeypatch.setattr(dl, "MAX_DOWNLOAD_BYTES", 1024)
    _install(monkeypatch, pdf_body=b"z" * 5000)
    outcome = dl.fetch_annual_report("600519", 2023)
    assert isinstance(outcome, Refusal)
    assert outcome.source == dl.SOURCE_STATIC


# --------------------------------------------------------------------------
# 台账 N-3：默认抽完就删；--keep-pdf 是显式开关
# --------------------------------------------------------------------------


def test_默认不保留_pdf_返回后文件已不存在(monkeypatch):
    _install(monkeypatch)
    result = dl.fetch_annual_report("600519", 2023)
    assert isinstance(result, dl.DownloadResult)
    assert result.pdf_path.exists() is False


def test_keep_pdf_为真时文件留在_data_raw(monkeypatch, tmp_path):
    _install(monkeypatch)
    result = dl.fetch_annual_report("600519", 2023, keep_pdf=True, keep_dir=tmp_path)
    assert isinstance(result, dl.DownloadResult)
    assert result.pdf_path.exists() is True
    assert result.pdf_path.parent == Path(tmp_path)
    assert result.pdf_path.read_bytes() == PDF_BYTES


# --------------------------------------------------------------------------
# 证据链的第一环：SHA-256 与源 URL 在抽取第一步就绑定
# --------------------------------------------------------------------------


def test_下载结果带_sha256_与源_url(monkeypatch):
    """cninfo 的病根是文本路径根本没关联页码，**结构上就不可能产出页级证据链**。

    出处必须在第一步绑定，事后补不回来。
    """
    _install(monkeypatch)
    result = dl.fetch_annual_report("600519", 2023)
    assert isinstance(result, dl.DownloadResult)
    assert result.sha256 == PDF_SHA
    assert len(result.sha256) == 64
    assert result.source_url.startswith("https://static.cninfo.com.cn/")
    assert result.org_id == ORG_ID


def test_摘要与英文版不被选中(monkeypatch):
    """摘要与英文版**与年报全文同属一个类目**，光靠 category 筛不掉。"""
    _install(monkeypatch)
    result = dl.fetch_annual_report("600519", 2023)
    assert isinstance(result, dl.DownloadResult)
    assert result.title == "2023年年度报告"
    assert "摘要" not in result.title
    assert result.source_url.endswith(ADJUNCT)


def test_标题筛选逐条判定():
    assert dl.is_annual_report({"announcementTitle": "2023年年度报告"}, 2023) is True
    assert dl.is_annual_report({"announcementTitle": "2023年年度报告摘要"}, 2023) is False
    assert dl.is_annual_report({"announcementTitle": "2023年年度报告（英文版）"}, 2023) is False
    assert dl.is_annual_report({"announcementTitle": "2022年年度报告"}, 2023) is False
    assert dl.is_annual_report({"announcementTitle": "2023年第三季度报告"}, 2023) is False


def test_筛不到年报时返回拒答而不是空结果(monkeypatch):
    _install(monkeypatch, routes={
        dl.STOCK_LIST_URL: json.dumps(STOCK_LIST).encode("utf-8"),
        dl.QUERY_URL: json.dumps({"announcements": []}).encode("utf-8"),
    })
    outcome = dl.fetch_annual_report("600519", 2023)
    assert isinstance(outcome, Refusal)
    assert outcome.code is RefusalCode.UNAVAILABLE


def test_上游返回非_json_算够不着而不是配置缺陷(monkeypatch):
    _install(monkeypatch, routes={dl.STOCK_LIST_URL: b"<html>502</html>"})
    outcome = dl.fetch_annual_report("600519", 2023)
    assert isinstance(outcome, Refusal)
    assert outcome.code is RefusalCode.UNAVAILABLE
    assert "JSON" in outcome.detail


def test_请求带显式_user_agent(monkeypatch):
    """`eval/llm_client.py` 记过的坑：默认 UA 被 CDN 按浏览器签名封掉，表现像鉴权失败。"""
    seen = []

    def _spy(opener, request):
        seen.append(request.get_header("User-agent"))
        return _FakeResponse(json.dumps(STOCK_LIST).encode("utf-8"))

    monkeypatch.setattr(dl, "_urlopen", _spy)
    dl.CninfoClient().org_id("600519")
    assert seen and seen[0] == dl.USER_AGENT
    assert "Python-urllib" not in (seen[0] or "")
