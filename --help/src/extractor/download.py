"""巨潮资讯网年报下载 —— 三步链路，只用标准库。

## 三步链路（CONTEXT §3.4，2026-08-15 实跑，**不需要 cookies**）

1. `GET  www.cninfo.com.cn/new/data/szse_stock.json`   取 `orgId`
2. `POST www.cninfo.com.cn/new/hisAnnouncement/query`  取 `adjunctUrl`
3. `GET  static.cninfo.com.cn/{adjunctUrl}`            下载 PDF

## 为什么用 `urllib` 而不是 `requests`

`eval/llm_client.py` 已经示范过这条路并写明理由：「零新增依赖，因此不触发
`scripts/verify_deps.py` 的供应链门禁——**不是绕过它，是没有新增供应链**」。
本模块照办，顺带省掉一次包合法性审计。
它记下的那个坑一并继承：**默认 UA（`Python-urllib/x.y`）会被 CDN 按浏览器签名封掉**，
表现像鉴权失败而实际不是。所以这里带一个显式 UA。

## 异常与 `Refusal` 的界线（D-022 决策二）

判据是「**这件事能不能写进文档告诉用户「这可能会发生」**」。

| 走 `Refusal(UNAVAILABLE, source=…)` | 走异常 |
|---|---|
| 巨潮超时 / 连不上 / 返回 5xx / 返回 4xx | 股票代码不在 `szse_stock.json` 里 |
| 响应不是合法 JSON（上游改了形状） | 调用方传了非法的年度 |
| 按代码+年度筛不到年报公告 | —— |
| `adjunctUrl` 指向白名单之外的主机 | —— |
| 响应体超过 64 MiB 上限 | —— |

左列都是「**够不着**」，对复核者而言是可理解的答案，应当进证据链、可机读、
被 AC-05 计入（D-022 决策一）。右列是「**我们写错了**」，写不进用户文档。

**4xx 也划在左列**，理由要写清楚：从本层看不出「巨潮改了接口」与「一次瞬时故障」的区别，
两者都是「取不到那份年报」，不是「记录构造错了」。**不假装能分辨。**

每个 `Refusal` 都带非空 `source`（L-9）：只说「证据不足」不合格，
复核者据此才知道该去修哪一处。

## 三处安全约束（威胁 T-01.5-01 / T-01.5-02 / T-01.5-04）

- **主机白名单**固定为 `{www.cninfo.com.cn, static.cninfo.com.cn}`。
  `adjunctUrl` 是上游返回的**不可信输入**，解析出的主机不在白名单即拒绝，
  **且不发起那次请求**。重定向同样受这道白名单管——重定向后的主机由
  `_SafeRedirectHandler` 在跟随之前拦下。
- **单次下载 64 MiB 上限 + 30 秒超时**。茅台一份 143 页是 3.5 MB，
  余量足够而畸形响应挡得住。上限在**流式读取过程中**判，不是读完再看长度。
- **默认抽完即删**（台账 N-3）。`--keep-pdf` 是显式开关，且只写 `data/raw/`
  ——该目录同时在 `.gitignore` 与 `scan_rules.yaml` 的必需隔离条目里。

## 本模块明确**不**做

- 不做公告全文检索（`/new/fulltextSearch/*`）
- 不取季报 / 半年报 / 摘要 / 英文版
- 不分页遍历全市场
- 不做任何写操作、订阅或登录态。本项目不持有任何巨潮账号
"""

from __future__ import annotations

import hashlib
import json
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from semantic_layer.resolve import Refusal, RefusalCode

__all__ = [
    "ALLOWED_HOSTS",
    "MAX_DOWNLOAD_BYTES",
    "SOCKET_TIMEOUT_SECONDS",
    "UnknownStockCode",
    "DisallowedHost",
    "DownloadResult",
    "CninfoClient",
    "fetch_annual_report",
]

# --------------------------------------------------------------------------
# 常量。**同名口径常量只允许一个定义点**（L-39）——这里是抽取侧网络口径的唯一定义点。
# --------------------------------------------------------------------------

ALLOWED_HOSTS = frozenset({"www.cninfo.com.cn", "static.cninfo.com.cn"})
MAX_DOWNLOAD_BYTES = 64 * 1024 * 1024
SOCKET_TIMEOUT_SECONDS = 30.0

# 见模块 docstring：默认 UA 会被 CDN 按浏览器签名封掉（`eval/llm_client.py` 2026-08-16 实测）。
USER_AGENT = "finaudit-agent/0.1 (+https://github.com/kevin1000x/finaudit-agent)"

STOCK_LIST_URL = "https://www.cninfo.com.cn/new/data/szse_stock.json"
QUERY_URL = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
STATIC_BASE = "https://static.cninfo.com.cn/"

# 年度报告全文的类目。摘要 / 季报 / 半年报都是别的类目，这里不碰。
ANNUAL_REPORT_CATEGORY = "category_ndbg_szsh"

# 责任方标识（L-9）。**稳定串，不是运行时拼的**——复核者要能逐字比对（J-6）。
SOURCE_STOCK_LIST = "cninfo:new/data/szse_stock.json"
SOURCE_QUERY = "cninfo:hisAnnouncement/query"
SOURCE_STATIC = "cninfo:static/adjunct"

# 标题里出现任一即排除。年报全文的标题不含这些词；
# 摘要与英文版**与年报全文同属一个类目**，光靠 category 筛不掉。
EXCLUDED_TITLE_TOKENS = ("摘要", "英文", "已取消", "取消")

DEFAULT_KEEP_DIR = Path("data") / "raw"


class UnknownStockCode(ValueError):
    """股票代码不在 `szse_stock.json` 里 —— 调用方写错了，属配置缺陷（D-022 决策二）。

    **刻意不做成 `Refusal`**：它写不进用户文档。
    「你可能会传一个不存在的股票代码」不是系统的可预期状态，是一个 bug。
    """


class DisallowedHost(RuntimeError):
    """请求目标不在主机白名单内。

    正常路径上由调用方转成 `Refusal`；作为异常存在是为了让**重定向处理器**
    能在 `urllib` 跟随重定向**之前**把它拦下来——那个位置没有返回值可用。
    """


@dataclass(frozen=True)
class DownloadResult:
    """一次成功的下载。`sha256` 与 `source_url` 是证据链的第一环。

    CONTEXT §6 记着 cninfo 的病根：文本路径根本没关联页码（`pdf_parser.py:94-98`
    裸拼接），**在结构上就不可能产出页级证据链**。出处必须在抽取第一步绑定，
    事后补不回来——所以它在这里，不在别处。
    """

    pdf_path: Path
    sha256: str
    source_url: str
    title: str
    org_id: str
    fetched_at: str

    def to_dict(self) -> dict:
        return {
            "pdf_path": str(self.pdf_path),
            "sha256": self.sha256,
            "source_url": self.source_url,
            "title": self.title,
            "org_id": self.org_id,
            "fetched_at": self.fetched_at,
        }


def host_of(url: str) -> str:
    return urllib.parse.urlsplit(url).hostname or ""


def is_allowed(url: str) -> bool:
    return host_of(url) in ALLOWED_HOSTS


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """重定向也要过白名单，**在跟随之前**。

    只在最初的 URL 上检查是不够的：上游只要回一个 302，`urllib` 默认会乖乖跟过去，
    白名单就形同虚设。这正是 T-01.5-01 说的「主机名与响应体都可能被篡改」。
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        if not is_allowed(newurl):
            raise DisallowedHost(f"重定向目标 {host_of(newurl)!r} 不在白名单 {sorted(ALLOWED_HOSTS)} 内")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _build_opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(_SafeRedirectHandler)


def _urlopen(opener: urllib.request.OpenerDirector, request: urllib.request.Request):
    """唯一的出网点。测试把它换掉，就不需要真的联网。"""
    return opener.open(request, timeout=SOCKET_TIMEOUT_SECONDS)


class CninfoClient:
    """巨潮三步链路的客户端。**无状态、无登录态、无 cookies。**"""

    def __init__(self, opener: urllib.request.OpenerDirector | None = None) -> None:
        self._opener = opener if opener is not None else _build_opener()

    # -- 底层 --------------------------------------------------------------

    def _request(self, url: str, source: str, data: bytes | None = None) -> bytes | Refusal:
        """发一次请求。**白名单不过即不发**（T-01.5-01）。"""
        if not is_allowed(url):
            return Refusal(
                RefusalCode.UNAVAILABLE,
                f"目标主机 {host_of(url)!r} 不在白名单 {sorted(ALLOWED_HOSTS)} 内，未发起请求。",
                source=source,
            )
        headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
        if data is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        request = urllib.request.Request(url, data=data, headers=headers)
        try:
            with _urlopen(self._opener, request) as response:
                return response.read(MAX_DOWNLOAD_BYTES + 1)
        except DisallowedHost as exc:
            return Refusal(RefusalCode.UNAVAILABLE, f"{exc}", source=source)
        except urllib.error.HTTPError as exc:
            return Refusal(
                RefusalCode.UNAVAILABLE,
                f"上游返回 HTTP {exc.code}。从本层看不出「接口改了」与「瞬时故障」的区别，"
                "两者都是取不到那份年报。",
                source=source,
            )
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return Refusal(RefusalCode.UNAVAILABLE, f"网络不可达：{exc}", source=source)

    def _get_json(self, url: str, source: str, data: bytes | None = None) -> Any | Refusal:
        raw = self._request(url, source, data=data)
        if isinstance(raw, Refusal):
            return raw
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            # 上游返回了非 JSON。**不是我们写错了**——是够不着那份数据。
            return Refusal(
                RefusalCode.UNAVAILABLE,
                f"上游响应不是合法 JSON：{exc}",
                source=source,
            )

    # -- 第一步：orgId -----------------------------------------------------

    def org_id(self, stock_code: str) -> str | Refusal:
        """股票代码 → `orgId`。**代码查不到时抛异常，不返回 `Refusal`**（D-022 判据 3）。"""
        payload = self._get_json(STOCK_LIST_URL, SOURCE_STOCK_LIST)
        if isinstance(payload, Refusal):
            return payload
        entries = payload.get("stockList") if isinstance(payload, dict) else None
        if not isinstance(entries, list):
            return Refusal(
                RefusalCode.UNAVAILABLE,
                "股票清单响应里没有 stockList 数组，上游形状与实测不符。",
                source=SOURCE_STOCK_LIST,
            )
        for entry in entries:
            if isinstance(entry, dict) and str(entry.get("code", "")) == str(stock_code):
                org = str(entry.get("orgId", "")).strip()
                if org:
                    return org
        raise UnknownStockCode(
            f"股票代码 {stock_code!r} 不在巨潮的 szse_stock.json 里（共 {len(entries)} 条）。"
            "这是调用方写错了，属配置缺陷，不是数据源不可达（D-022 决策二）。"
        )

    # -- 第二步：找年报公告 -------------------------------------------------

    def find_annual_report(self, stock_code: str, year: int, org: str) -> dict | Refusal:
        """按代码 + 会计年度取年报全文公告。年报在**次年**发布，故窗口取 `year + 1` 全年。"""
        form = urllib.parse.urlencode(
            {
                "stock": f"{stock_code},{org}",
                "tabName": "fulltext",
                "pageSize": "30",
                "pageNum": "1",
                "column": "szse",
                "category": ANNUAL_REPORT_CATEGORY,
                "seDate": f"{year + 1}-01-01~{year + 1}-12-31",
                "isHLtitle": "true",
            }
        ).encode("utf-8")
        payload = self._get_json(QUERY_URL, SOURCE_QUERY, data=form)
        if isinstance(payload, Refusal):
            return payload
        announcements = payload.get("announcements") if isinstance(payload, dict) else None
        if not isinstance(announcements, list):
            return Refusal(
                RefusalCode.UNAVAILABLE,
                f"公告查询响应里没有 announcements 数组（{stock_code} / {year}）。",
                source=SOURCE_QUERY,
            )
        picked = [a for a in announcements if isinstance(a, dict) and is_annual_report(a, year)]
        if not picked:
            return Refusal(
                RefusalCode.UNAVAILABLE,
                f"{stock_code} 的 {year} 年年度报告全文在巨潮的公告列表里没找到"
                f"（{len(announcements)} 条候选，按标题排除摘要与英文版后为空）。",
                source=SOURCE_QUERY,
            )
        # 同一年可能有更正后重发的版本；取**最早**发布的原始年报，保证同输入同输出。
        picked.sort(key=lambda a: (str(a.get("announcementTime", "")), str(a.get("adjunctUrl", ""))))
        return picked[0]

    # -- 第三步：下载 ------------------------------------------------------

    def download(self, url: str, dest: Path) -> str | Refusal:
        """流式落盘并**在同一次读取里**算 SHA-256，不二次读文件。

        上限在读取过程中判：读完再看长度，畸形响应已经把内存吃光了。
        """
        if not is_allowed(url):
            return Refusal(
                RefusalCode.UNAVAILABLE,
                f"下载目标主机 {host_of(url)!r} 不在白名单内，未发起请求。",
                source=SOURCE_STATIC,
            )
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
        digest = hashlib.sha256()
        total = 0
        try:
            with _urlopen(self._opener, request) as response, dest.open("wb") as handle:
                while True:
                    chunk = response.read(1024 * 256)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_DOWNLOAD_BYTES:
                        return Refusal(
                            RefusalCode.UNAVAILABLE,
                            f"响应体超过 {MAX_DOWNLOAD_BYTES} 字节上限，已中止下载。",
                            source=SOURCE_STATIC,
                        )
                    digest.update(chunk)
                    handle.write(chunk)
        except DisallowedHost as exc:
            return Refusal(RefusalCode.UNAVAILABLE, f"{exc}", source=SOURCE_STATIC)
        except urllib.error.HTTPError as exc:
            return Refusal(
                RefusalCode.UNAVAILABLE, f"下载返回 HTTP {exc.code}。", source=SOURCE_STATIC
            )
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return Refusal(RefusalCode.UNAVAILABLE, f"下载失败：{exc}", source=SOURCE_STATIC)
        if total == 0:
            return Refusal(RefusalCode.UNAVAILABLE, "下载到 0 字节。", source=SOURCE_STATIC)
        return digest.hexdigest()


def is_annual_report(announcement: dict, year: int) -> bool:
    """标题筛选。**摘要与英文版与年报全文同属一个类目**，光靠 category 筛不掉。"""
    title = str(announcement.get("announcementTitle", ""))
    if not title:
        return False
    if any(token in title for token in EXCLUDED_TITLE_TOKENS):
        return False
    if str(year) not in title:
        return False
    return "年度报告" in title


def fetch_annual_report(
    stock_code: str,
    year: int,
    keep_pdf: bool = False,
    client: CninfoClient | None = None,
    keep_dir: Path | str = DEFAULT_KEEP_DIR,
) -> DownloadResult | Refusal:
    """三步链路的入口。返回 `DownloadResult` 或 `Refusal`，**不抛网络异常**。

    `keep_pdf=False`（默认）：落到临时文件，**返回前删除**（台账 N-3）。
    落库的是「结构化行 + PDF 的 SHA-256 + 巨潮源 URL + 页码」，PDF 本身不留。
    """
    if isinstance(year, bool) or not isinstance(year, int):
        raise ValueError(f"year 必须是整数，实际是 {year!r}")
    client = client if client is not None else CninfoClient()

    org = client.org_id(stock_code)  # 代码不认识时**这里抛 UnknownStockCode**
    if isinstance(org, Refusal):
        return org

    announcement = client.find_annual_report(stock_code, year, org)
    if isinstance(announcement, Refusal):
        return announcement

    adjunct = str(announcement.get("adjunctUrl", "")).lstrip("/")
    if not adjunct:
        return Refusal(
            RefusalCode.UNAVAILABLE,
            "选中的公告没有 adjunctUrl，无法定位 PDF。",
            source=SOURCE_QUERY,
        )
    source_url = urllib.parse.urljoin(STATIC_BASE, adjunct)
    if not is_allowed(source_url):
        # `adjunctUrl` 是上游返回的不可信输入（T-01.5-01）。
        # 拼出来的主机不对就**到此为止，不发起第二次请求**。
        return Refusal(
            RefusalCode.UNAVAILABLE,
            f"adjunctUrl 解析出的主机 {host_of(source_url)!r} 不在白名单 "
            f"{sorted(ALLOWED_HOSTS)} 内，未发起下载请求。",
            source=SOURCE_STATIC,
        )

    if keep_pdf:
        target_dir = Path(keep_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        dest = target_dir / f"{stock_code}_{year}.pdf"
        sha = client.download(source_url, dest)
        if isinstance(sha, Refusal):
            dest.unlink(missing_ok=True)
            return sha
    else:
        handle = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        handle.close()
        dest = Path(handle.name)
        sha = client.download(source_url, dest)
        # 无论成败都删：抽完就删是默认（台账 N-3），失败时更没有留着的理由。
        dest.unlink(missing_ok=True)
        if isinstance(sha, Refusal):
            return sha

    return DownloadResult(
        pdf_path=dest,
        sha256=sha,
        source_url=source_url,
        title=str(announcement.get("announcementTitle", "")),
        org_id=org,
        fetched_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )
