"""最小 LLM 客户端 —— 只为评测的 **baseline 对照臂** 服务。

## 它不是什么

**它不是本系统的一部分。** 本项目的主张是「答案必须能追到口径」，
而口径解析走的是 `semantic_layer.resolve` 这条确定性路径，与 LLM 无关。
本模块存在的唯一理由是：要证明「通用 Agent 答不出这个」，就得让通用 Agent 真的答一次。

因此本模块**永远不会**被 `eval/run.py`（系统臂）导入。两条臂的产物不共用报告文件、
不共用目录、不合并分数。见 `eval/baseline.py` 顶部的说明。

## 三条约束落在代码里

1. **密钥不进仓库**（D-010 的延伸）。密钥只从环境变量或 gitignored 的 `.env` 读，
   且 `redacted()` 保证任何写进报告的配置都是脱敏的。
2. **零新增依赖**。只用 stdlib（`urllib`），因此不触发 `scripts/verify_deps.py` 的
   供应链门禁——不是绕过它，是**没有新增供应链**。
3. **请求可复核**。每次调用记录 `prompt_sha256`，与 D-003「证据链是第一类产物」同源：
   报告里出现的每个模型答案，都能指回产生它的那串确切输入。
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# opencode.ai 的 Cloudflare 会对 urllib 默认 UA（`Python-urllib/x.y`）返回
# **HTTP 403 + `error code: 1010`**（浏览器签名封禁），且发生在鉴权之前——
# 表现像"密钥无效"，实际不是。带上常规 UA 即恢复。2026-08-16 实测确认。
USER_AGENT = "finaudit-agent-eval/0.1 (+https://github.com/kevin1000x/finaudit-agent)"

# 两种线协议。选哪个由**模型**决定，不由厂商决定：
# 例如 opencode 的 qwen / minimax 走 anthropic 形状，glm / kimi / deepseek 走 openai 形状。
WIRE_OPENAI = "openai"
WIRE_ANTHROPIC = "anthropic"


class LLMError(RuntimeError):
    """调用失败。**不吞异常、不静默降级** —— 静默降级正是本项目要消灭的东西。"""


@dataclass(frozen=True)
class Provider:
    name: str
    base_url: str
    wire: str
    model: str
    api_key: str

    def redacted(self) -> dict:
        """可安全写进报告的配置。密钥只留前 6 位 + 长度，够识别是哪把、不够复用。"""
        k = self.api_key
        return {
            "provider": self.name,
            "base_url": self.base_url,
            "wire": self.wire,
            "model": self.model,
            "api_key_fingerprint": f"{k[:6]}…({len(k)} chars)" if k else "(empty)",
        }


# 已实测可用的预设。**不写死密钥**，密钥永远另行注入。
PRESETS: dict[str, dict] = {
    # 2026-08-16 实测：/models 与 /chat/completions 均 200。
    # 该平台当前只有 deepseek-v4-pro / deepseek-v4-flash 两个模型
    # （旧的 deepseek-chat 是别名，解析到 flash）。
    #
    # 默认选 **flash**（操作者 2026-08-16 指定）。
    #
    # ⚠️ 实测更正：**flash 同样是推理模型**，`completion_tokens_details.reasoning_tokens`
    # 在 `max_tokens=12000` 下有两题被打满、正文返回空串——比 pro 还多一题。
    # 全量 token 两者接近（pro 44,290 入 / 48,723 出；flash 41,303 / 45,197）。
    # 所以「选 flash 是为了预算更稳」这个理由**不成立**，不要这么写在别处。
    # 真正需要注意的是：这个平台上两个模型都会烧 reasoning 预算，
    # `--max-tokens` 给不够就会得到空正文（本框架已把它抛成 ERROR 而非记作答错）。
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "wire": WIRE_OPENAI,
        "model": "deepseek-v4-flash",
        "key_env": "DEEPSEEK_API_KEY",
    },
    # 2026-08-16 实测：需常规 UA，否则 CF 1010。qwen/minimax 走 anthropic 形状且需 x-api-key
    "opencode-go-anthropic": {
        "base_url": "https://opencode.ai/zen/go",
        "wire": WIRE_ANTHROPIC,
        "model": "qwen3.7-plus",
        "key_env": "OPENCODE_API_KEY",
    },
    "opencode-go-openai": {
        "base_url": "https://opencode.ai/zen/go",
        "wire": WIRE_OPENAI,
        "model": "glm-5.3",
        "key_env": "OPENCODE_API_KEY",
    },
}


def _load_dotenv() -> dict[str, str]:
    """读仓库根的 `.env`（已在 .gitignore 里）。不存在就返回空，不报错。"""
    path = REPO_ROOT / ".env"
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def resolve_key(env_name: str, key_file: str | None = None) -> str:
    """密钥解析顺序：显式文件 > 环境变量 > `.env`。**一律不写进任何产物。**"""
    if key_file:
        p = Path(key_file).expanduser()
        if not p.is_file():
            raise LLMError(f"指定的密钥文件不存在：{p}")
        return p.read_text(encoding="utf-8").strip()
    if os.environ.get(env_name):
        return os.environ[env_name].strip()
    dotenv = _load_dotenv()
    if dotenv.get(env_name):
        return dotenv[env_name]
    raise LLMError(
        f"未找到密钥。请设置环境变量 {env_name}，或在仓库根建 .env（已 gitignore）写入 "
        f"{env_name}=...，或用 --key-file 指向本机密钥文件。**不要把密钥写进仓库内任何文件。**"
    )


def make_provider(preset: str, model: str | None = None, key_file: str | None = None) -> Provider:
    if preset not in PRESETS:
        raise LLMError(f"未知预设 {preset!r}，可选：{', '.join(sorted(PRESETS))}")
    cfg = PRESETS[preset]
    return Provider(
        name=preset,
        base_url=cfg["base_url"],
        wire=cfg["wire"],
        model=model or cfg["model"],
        api_key=resolve_key(cfg["key_env"], key_file),
    )


def _post(url: str, headers: dict, payload: dict, timeout: int) -> tuple[int, str]:
    req = urllib.request.Request(
        url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # 网络层错误也要带出类型，不能只说"失败"
        raise LLMError(f"{type(e).__name__}: {e}") from e


@dataclass(frozen=True)
class Completion:
    text: str
    model: str
    usage: dict
    prompt_sha256: str
    latency_ms: int


def complete(p: Provider, system: str, user: str, max_tokens: int = 8192,
             temperature: float = 0.0, timeout: int = 300, retries: int = 2) -> Completion:
    """一次补全。**失败即抛**，绝不返回空串冒充答案。

    `temperature=0` 是刻意的：对照臂要尽量可复现，否则「模型答错了」与
    「这次恰好答错」分不开。但要注意 temperature=0 不等于确定性，
    报告里记 `prompt_sha256` 与 `usage` 就是为了让这一点可被追查。
    """
    # 指纹取「实际发出去的两段文本」，与线协议无关，两条臂之间可比
    fingerprint = hashlib.sha256(f"{system}\x00{user}".encode("utf-8")).hexdigest()

    if p.wire == WIRE_OPENAI:
        url = f"{p.base_url.rstrip('/')}/chat/completions"
        headers = {"User-Agent": USER_AGENT, "content-type": "application/json",
                   "Authorization": f"Bearer {p.api_key}"}
        payload = {"model": p.model, "max_tokens": max_tokens, "temperature": temperature,
                   "messages": [{"role": "system", "content": system},
                                {"role": "user", "content": user}]}
    elif p.wire == WIRE_ANTHROPIC:
        url = f"{p.base_url.rstrip('/')}/v1/messages"
        headers = {"User-Agent": USER_AGENT, "content-type": "application/json",
                   "x-api-key": p.api_key, "anthropic-version": "2023-06-01"}
        payload = {"model": p.model, "max_tokens": max_tokens, "temperature": temperature,
                   "system": system, "messages": [{"role": "user", "content": user}]}
    else:
        raise LLMError(f"未知线协议 {p.wire!r}")

    last = ""
    for attempt in range(retries + 1):
        t0 = time.monotonic()
        status, body = _post(url, headers, payload, timeout)
        latency = int((time.monotonic() - t0) * 1000)

        if status == 200:
            data = json.loads(body)
            if p.wire == WIRE_OPENAI:
                text = data["choices"][0]["message"]["content"] or ""
                model = data.get("model", p.model)
            else:
                text = "".join(b.get("text", "") for b in data.get("content", []))
                model = data.get("model", p.model)
            usage = data.get("usage", {}) or {}

            # 推理模型会把整个 max_tokens 预算烧在 reasoning 上，正文返回空串。
            # **空串绝不能当成"模型答不出"** —— 那是预算不够，是本框架的问题不是模型的。
            # 显式抛错，让它落进 ERROR 而不是 FAIL。
            if not text.strip():
                raise LLMError(
                    f"模型返回空正文（max_tokens={max_tokens}）。usage={usage}。"
                    "推理模型常把预算全用在 reasoning 上——请提高 --max-tokens 后重跑，"
                    "**不要**把这条记作模型答错。"
                )
            return Completion(text, model, usage, fingerprint, latency)

        last = f"HTTP {status}: {body[:400]}"
        # 429 / 5xx 退避重试；4xx（除 429）是配置问题，重试无意义
        if status == 429 or status >= 500:
            if attempt < retries:
                time.sleep(2 ** attempt * 3)
                continue
        break

    raise LLMError(f"调用失败（{p.name} / {p.model}）：{last}")
