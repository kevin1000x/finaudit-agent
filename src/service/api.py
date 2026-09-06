"""无状态请求–响应端点（`02-04` T1）。

契约是**纯函数**，不是 HTTP：`answer_endpoint(payload) -> (状态码, 响应体)`。
HTTP 那一层由部署方给 —— 理由见包的 docstring。

## 三条硬约束，逐条有测试守着

1. **任何输入都不返回 5xx。** 这是 `D-022` 那条纪律延到 HTTP 边界：
   「每一步的失败都落成拒答，不抛异常」。一个 500 对用户来说是「它坏了」，
   而这个系统的正确行为是**说清为什么给不出答案**。
2. **响应里的 `page` 逐字是 `render_answer()` 的输出。** 不另写一版渲染 ——
   另写一版就等于对外展示了一个没被 `AC-06` 量过的东西（`D-032`）。
3. **只收一个问题字符串。** 没有文件上传、没有 CSV、没有表格粘贴（`D-010`）。

## 无状态

模块里没有任何跨请求的可变容器。唯一的缓存是只读注册表与覆盖清单，
两者都可由磁盘重新推导 —— `D-021` 豁免三里明确允许的**可丢弃缓存**。
`tests/test_service.py` 用语法树查「模块级没有可变容器、没有 `global`」。
"""

from __future__ import annotations

import hmac
import os
import sys
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT / "src") not in sys.path:  # pragma: no cover - 部署环境各不相同
    sys.path.insert(0, str(REPO_ROOT / "src"))

from agent.answer import FixtureSource, answer_question, render_answer  # noqa: E402
from semantic_layer.__main__ import _flag_descriptions  # noqa: E402
from semantic_layer.resolve import Registry  # noqa: E402

from . import coverage as cov  # noqa: E402

__all__ = [
    "MAX_QUESTION_BYTES",
    "TOKEN_ENV",
    "answer_endpoint",
    "authorized",
    "coverage_endpoint",
    "needs_token",
    "serve",
]

#: 令牌从环境变量读，**不进仓库**。cninfo 那边的 Pages Function 已经在发
#: `Authorization: Bearer <AUDIT_API_TOKEN>`，这里读的就是它对面那一半。
TOKEN_ENV = "FINAUDIT_API_TOKEN"


def needs_token(host: str) -> bool:
    """这次监听要不要令牌。**判据只有一句：外面够得着吗。**

    绑在回环地址上 = 只有本机能连 ⇒ 开发用，不要令牌。
    绑在别的地址上 = 网络上够得着 ⇒ **必须**有令牌。

    ## 为什么用「绑在哪」判，而不是「有没有设令牌」

    「设了就检查、没设就放行」是个**静默失败**的设计：部署时忘了配环境变量，
    服务照常起来，而且完全敞开 —— 没有任何一处会响。
    按监听地址判则相反：忘了配令牌，服务**起不来**并说明原因。
    **失败方向要选吵的那个。**
    """
    return host not in ("127.0.0.1", "::1", "localhost")


def authorized(header_value, token) -> bool:
    """`Authorization` 头对不对。

    ⚠️ **用 `hmac.compare_digest` 而不是 `==`**：字符串相等在第一个不同的字节上就返回，
    比较耗时随「猜对了几个字符」变化，可以被用来逐字节试出令牌。
    """
    if not token:
        return True  # 不需要令牌的那种监听，上游已经判过（`needs_token`）
    if not isinstance(header_value, str):
        return False
    prefix = "Bearer "
    if not header_value.startswith(prefix):
        return False
    return hmac.compare_digest(header_value[len(prefix):], str(token))

#: 问题字符串的上限。**不是安全边界，是礼貌边界** ——
#: 意图解析对超长输入不会崩，只会拒答；这条只是不让一次请求拖着几 MB 的正文走。
MAX_QUESTION_BYTES = 2000


@lru_cache(maxsize=1)
def _registry():
    """口径注册表。**只读，可丢弃** —— 清掉重新从 `metrics/` 加载得到同一份。"""
    return Registry.load(REPO_ROOT / "metrics")


@lru_cache(maxsize=1)
def _flags():
    return _flag_descriptions(REPO_ROOT / "metrics")


@lru_cache(maxsize=None)
def _source(path_str: str):
    """一份数据源。按路径缓存，**内容只读**。"""
    return FixtureSource(Path(path_str))


class _NoRow:
    """「哪一份都没有这一行」时的取数位。

    它存在的唯一理由是**别去冒充一份真实年报**。上游拿到它会正常走到
    `UNAVAILABLE` 拒答（`D-003`：拒答是正确输出），而证据页上的出处一栏
    说的是「查过这几份，都没有这一行」—— 一句能被核对的实话。
    """

    def __init__(self, sources, stock_code, fiscal_year):
        self._sources = sources
        self.stock_code = None if stock_code is None else str(stock_code)
        self.fiscal_year = fiscal_year
        self.row: dict = {}
        self.found = False

    @property
    def batch_id(self) -> str:
        names = "、".join(s.fixture_id for s in self._sources) or "（一份都没有）"
        return (
            "查过的数据源：" + names
            + "；都没有 " + str(self.stock_code) + "/" + str(self.fiscal_year) + " 这一行"
        )

    def by_field(self, path):  # pragma: no cover - 没有行就不会取到字段
        return None


class _Sources:
    """把若干份数据源接成 `answer_question` 认得的那一个。

    ⚠️ **不是「挑一份」**：`eval/run.py` 那边多于一份就拒绝运行，理由是
    「运行器不替人挑一份，挑错了整批结论都建立在错的数据上」。
    那条理由在**评测**里成立（一次跑一整批，必须同源）；
    在**服务**里不成立 —— 每次请求只问一家公司一年，
    「哪一份有这一行」是确定的，不需要谁去挑。

    这个类今天只带一份文件（真实抽取结果还没落盘，见 `N-61`），
    但它必须现在就写对：`data/extracted/` 里放进第一个文件的那一刻，
    「只允许一份」的写法会当场把服务弄坏，而那时没人会想到是这里。
    """

    def __init__(self, paths):
        self._sources = tuple(_source(str(p)) for p in paths)
        self.stock_code = None
        self.fiscal_year = None
        self.row: dict = {}
        self.found = False

    @property
    def batch_id(self) -> str:
        """还没定位到某一行时，说清**手上有哪几份**，不编一个行号。"""
        return "sources:" + "+".join(s.batch_id for s in self._sources)

    def at(self, stock_code, fiscal_year):
        """哪一份有这一行就用哪一份。

        🔴 **都没有的时候不许退回「第一份」。** 那份文件是某一家真实公司的年报，
        退回它意味着证据页会印出**那家公司的名字与它的 PDF 指纹**，
        而提问问的是另一家 —— 拼出来就是一条伪造的出处。
        2026-09-06 浏览器实跑撞到过：问 000651，页面答「万华化学 000651 ·
        2023 年年度报告（年报 PDF SHA-256 87411c60…）」。

        ⇒ 都没有就返回一个**说清「查了哪几份、都没有」**的空位。
        """
        for s in self._sources:
            got = s.at(stock_code, fiscal_year)
            if got.found:
                return got
        return _NoRow(self._sources, stock_code, fiscal_year)

    def by_field(self, path):  # pragma: no cover - 未定位时不会被取数
        return None


def _paths() -> list:
    files: list = []
    for _, directory in cov.SOURCE_DIRS:
        if directory.is_dir():
            files.extend(sorted(directory.glob("*.yaml")))
    return files


def _pick_source():
    paths = _paths()
    return _Sources(paths) if paths else None


def answer_endpoint(payload) -> tuple:
    """`POST /answer`。返回 `(状态码, 响应体)`。

    **只有两种 4xx**：请求体不是一个带 `question` 字符串的对象、或者字符串太长。
    其余一切 —— 认不出指标、没有这家公司、口径不许作答 —— 都是 **200 + 一次拒答**，
    因为那些是**正常业务结果**，不是错误（`D-003`）。
    """
    if not isinstance(payload, dict):
        return 400, {"detail": "请求体要是一个 JSON 对象，且带一个 question 字段"}
    # `D-010`：只收问题字符串。多给的字段一律不看 —— 不解释、不报错，也不接。
    question = payload.get("question")
    if not isinstance(question, str) or not question.strip():
        return 400, {"detail": "question 要是一个非空字符串"}
    if len(question.encode("utf-8")) > MAX_QUESTION_BYTES:
        return 400, {"detail": "question 太长（上限 " + str(MAX_QUESTION_BYTES) + " 字节）"}

    answer = answer_question(" ".join(question.split()), _registry(), source=_pick_source())
    defn = _registry().definitions.get(answer.metric_id) if answer.metric_id else None
    body = {
        "answer": answer.to_dict(),
        # 逐字是 `render_answer()` 的输出。**不另写一版**（`D-032`）。
        "page": render_answer(answer, defn, _flags()),
    }
    # 拒答理由是「数据源里没这一行」时，补一句**覆盖面**的话 ——
    # 「我们没有这家公司」与「这家公司没有这个指标」是两件事（见 `coverage.why_not`）。
    refusal = answer.refusal or {}
    if refusal.get("code") == "UNAVAILABLE":
        body["coverage_note"] = cov.why_not(answer.entity, answer.period)
    return 200, body


def coverage_endpoint() -> tuple:
    """`GET /coverage`。**先让人看清能问什么，再让他问。**"""
    return 200, cov.summary()


# --------------------------------------------------------------------------
# 运行器：**stdlib，零依赖**
# --------------------------------------------------------------------------
#
# `N-63` 裁定 (a)：找一个**按请求触发、能缩到零**的地方跑它。
# 那类平台（Cloud Run / Fly Machines / Render 之流）要的只有两件事 ——
# 监听 `$PORT`、绑 `0.0.0.0`。所以这个 stdlib 运行器就够用，
# **不需要为了上线引进一个 Web 框架**（服务端依赖闭包实测只有 PyYAML 一个）。
#
# ⚠️ 它是单线程的。这对本项目成立，因为一次请求就是读几个 YAML 加一次十进制算术；
# 但**这句话哪天不成立了，就该换运行器，而不是往这里加线程池** ——
# 加线程池等于开始在这一层维护并发状态，而无状态是 `D-021` 豁免三的前提。


def serve(host: str | None = None, port: int | None = None):  # pragma: no cover - 手工用
    """起服务。`python -m service.api` 就是它。

    `host` / `port` 不给时从环境读（`HOST` / `PORT`）—— 缩到零的托管平台
    是靠 `$PORT` 告诉你监听哪里的。
    """
    import json
    from http.server import BaseHTTPRequestHandler, HTTPServer

    host = host if host is not None else os.environ.get("HOST", "127.0.0.1")
    port = port if port is not None else int(os.environ.get("PORT", "8100"))
    token = os.environ.get(TOKEN_ENV) or ""

    # 🔴 **外面够得着就必须有令牌，否则拒绝启动。**
    # 这里刻意不是「没设令牌就放行」—— 那样部署时忘了配环境变量，
    # 服务会照常起来并且完全敞开，没有任何一处会响。
    if needs_token(host) and not token:
        raise SystemExit(
            "拒绝启动：监听 " + host + " 是网络上够得着的地址，但没有设 " + TOKEN_ENV + "。\n"
            "要么设一个令牌，要么绑回环地址（127.0.0.1）只给本机用。"
        )

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: dict):
            raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _ok(self) -> bool:
            """鉴权。**失败给 401，不给 200 + 拒答。**

            拒答是「你问的这个我答不了」，是业务结果；
            认证失败是「我不知道你是谁」，连业务都还没开始。两件事不混。
            """
            if authorized(self.headers.get("Authorization"), token):
                return True
            self._send(401, {"detail": "缺少或不正确的 Authorization: Bearer 令牌"})
            return False

        def do_GET(self):
            if not self._ok():
                return
            if self.path.rstrip("/").endswith("/coverage"):
                self._send(*coverage_endpoint())
            else:
                self._send(404, {"detail": "只有 GET /coverage 与 POST /answer"})

        def do_POST(self):
            if not self._ok():
                return
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            try:
                payload = json.loads(raw.decode("utf-8")) if raw else None
            except Exception:
                self._send(400, {"detail": "请求体不是合法 JSON"})
                return
            self._send(*answer_endpoint(payload))

        def log_message(self, *args):
            # 不打访问日志。**问题字符串是用户输入**，打进日志就等于开始留存它，
            # 而「把存储清空不丢任何东西」是 `D-021` 豁免三的第二条判据。
            pass

    HTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":  # pragma: no cover
    serve()
