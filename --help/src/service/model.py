"""服务侧的模型接线：给 `parse_intent` 注入那个 `(question) -> str` 可调用对象。

🔴 **边界一寸没动。** `src/agent/intent.py` 抬头写着「这是 LLM 在本系统里的唯一位置」，
本模块做的是**把那个位置接上电**，不是新开一个位置 —— `agent/` 仍然不 import 任何
LLM 客户端，注入仍然发生在服务的组装处（`service/api.py`）。

## 模型被允许做的唯一一件事

把题面里的说法，归一到**别名表里已经存在的一条别名**。
提示词把整张候选别名清单列出去，并要求「原样回一条，认不出回 NONE」。
即便它编一个表里没有的名字，`parse_intent` 那句 `guess in registry.by_alias`
照样挡掉 —— **提示词是为了提高命中率，不是安全边界；安全边界在别名表。**

## 为什么不复用 `eval/llm_client.py`

两条理由，任一条都够：

1. 那个模块顶上写着「它不是本系统的一部分…**永远不会**被 `eval/run.py`（系统臂）导入」。
   服务是系统臂。import 它，那句话就假了。
2. 它不在镜像里 —— `Dockerfile` 只 COPY `eval/frozen-01/fixtures/`。
   而且它的默认值（`max_tokens=8192` / `timeout=300` / 两次重试）是给**离线批量评测**的；
   放到一条同步请求路径上，意味着一次请求最长可以卡五分钟。

## 三件不做的事

1. **不重试、不长等。** 超时 8 秒，一次不成就算了 —— 用户就在那头等着。
2. **不吞掉「模型没接通」这件事。** 失败返回空串 ⇒ 整条路径退回离线态 ⇒
   认不出指标就**拒答**。拒答不是「降级成功」，它本来就是正确输出（`D-003`）；
   但「本来就没配模型」与「配了、这次没接通」是两回事，
   所以 `Asker` 把原因留在 `.error` 里，由服务在响应里说明白。
3. **不把密钥写进任何产物。** 只从环境变量或 gitignored 的 `.env` 读；
   本模块任何一条错误信息里都不出现密钥（只带异常类型与 HTTP 状态码）。

## 零新增依赖

只用 stdlib（`urllib`）。`Dockerfile` 抬头声称「服务端第三方闭包实测只有 PyYAML 一个」，
而 `D-014` 的**零 AGPL** 论证正是建立在「闭包本来就只有一个包」之上。
接一个模型进来**不能让那句话变假**。
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

#: 密钥。**没有它就没有模型** —— 不是报错，是退回离线态（离线态本来就能跑完）。
KEY_ENV = "FINAUDIT_MODEL_KEY"
#: 端点与模型名可以换，默认是 DeepSeek。换厂商不该要改代码。
BASE_ENV = "FINAUDIT_MODEL_BASE"
NAME_ENV = "FINAUDIT_MODEL_NAME"

DEFAULT_BASE = "https://api.deepseek.com"
DEFAULT_NAME = "deepseek-chat"

#: 同步请求路径上的超时。宁可退回离线拒答，也不让请求挂在那儿。
TIMEOUT_S = 8
#: 只可能回一条别名，几十个字符封顶。给 64 是留余量，不是留空间给它发挥。
MAX_TOKENS = 64
#: 模型说「认不出」的写法。它不在别名表里，所以就算原样透传也会被挡掉 ——
#: 这个常量是为了让提示词有话可说，不是一道过滤。
NONE_TOKEN = "NONE"

USER_AGENT = "finaudit-service/0.1"

# ## 提示词调过一轮，结论是「没有评测集就别调」
#
# 2026-09-07 用 `deepseek-chat` 实测三版提示词 × 8 个说法（`N-64`）：
# 原版 5/8、加了「选错口径比不选严重得多」的一版 5/8、折中版 4/8 ——
# **两个 5/8 错的还不是同几题**。也就是说三版之间的差异被单次波动盖住了，
# 8 个样本分不开它们。⇒ 保留最简单的那版，不按一次观察调参（`A-14` 同源教训）。
#
# 🔴 **24 次调用里，错的全是「没认出来」，没有一次认成别的指标。**
#    这才是要盯的那一面：没认出来 ⇒ 拒答 + 把 94 个可用叫法全列给用户（`D-038 G3`）；
#    认成别的指标 ⇒ 一个看起来完全正常的错答案。命中率可以慢慢提，方向不能错。
_SYSTEM = (
    """你是一个术语归一器。下面这张清单是全部候选，除此之外不存在别的选项。
读用户的问题，如果问题里的指标说法与清单里某一条是同一个口径，就原样输出那一条，一个字都不要改。
如果不确定、清单里没有、或者问题里根本没提到指标，只输出 """
    + NONE_TOKEN
    + """。
不要解释，不要加标点，不要输出第二行。

清单：
"""
)


class ModelUnavailable(RuntimeError):
    """这次没问上。**不是「模型说不知道」** —— 那种情况会正常返回 NONE。"""


@dataclass(frozen=True)
class Provider:
    base_url: str
    name: str
    api_key: str

    def redacted(self) -> dict:
        """可以写进日志与报告的那一份。**密钥只留长度。**"""
        return {"base_url": self.base_url, "model": self.name, "key_len": len(self.api_key)}


def _load_dotenv() -> dict:
    """读仓库根的 `.env`（已在 `.gitignore` 里）。不存在就返回空，不报错。

    与 `eval/llm_client._load_dotenv` 同形。**没有做成共享模块是有意的** ——
    见抬头「为什么不复用」：共享一个模块就是让系统臂 import 了对照臂那一侧。
    十几行的重复，换两条臂在 import 图上完全不相交。
    """
    path = REPO_ROOT / ".env"
    out: dict = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def provider_from_env():
    """配了就返回一个 `Provider`，没配就返回 `None`。**没配不是错误。**

    ⚠️ 与 `FINAUDIT_API_TOKEN` 的处理**刻意不同**：那个没配会让服务**拒绝启动**，
    因为「忘了配令牌」的后果是一个完全敞开的服务；而「忘了配模型」的后果是
    **认不出的说法照旧拒答** —— 那是本来就正确的行为，不该把服务拦在门外。
    """
    env = os.environ
    key = (env.get(KEY_ENV) or "").strip()
    if not key:
        key = (_load_dotenv().get(KEY_ENV) or "").strip()
    if not key:
        return None
    return Provider(
        base_url=(env.get(BASE_ENV) or DEFAULT_BASE).strip().rstrip("/"),
        name=(env.get(NAME_ENV) or DEFAULT_NAME).strip(),
        api_key=key,
    )


def _post(provider: Provider, system: str, user: str) -> str:
    payload = {
        "model": provider.name,
        "max_tokens": MAX_TOKENS,
        # 归一是个查表动作，不是创作。要的是同一个问题每次给同一个答案。
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    req = urllib.request.Request(
        provider.base_url + "/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "User-Agent": USER_AGENT,
            "content-type": "application/json",
            "Authorization": "Bearer " + provider.api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
            body = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        # ⚠️ **只带状态码，不带响应体。** 响应体里可能回显请求内容，
        #    而请求内容里有整张别名表和用户的问题；错误信息会进响应给调用方看。
        raise ModelUnavailable("HTTP " + str(e.code)) from None
    except Exception as e:
        raise ModelUnavailable(type(e).__name__) from None

    try:
        data = json.loads(body)
        return str(data["choices"][0]["message"]["content"])
    except Exception:
        raise ModelUnavailable("响应不是预期的形状") from None


def ask(provider: Provider, aliases, question: str) -> str:
    """问一次。返回模型说的那条别名（**未经校验**），或空串。

    🔴 「未经校验」是刻意的：校验发生在 `parse_intent` 里那句
    `guess in registry.by_alias`。**校验只该有一处** —— 在两处各写一遍，
    两处就会慢慢长得不一样，而那时没人知道以哪一处为准。
    """
    listed = "\n".join(str(a) for a in aliases)
    out = _post(provider, _SYSTEM + listed, str(question))
    out = " ".join(out.split())
    return "" if out == NONE_TOKEN else out


class Asker:
    """一次请求配一个。**不跨请求留状态** —— 无状态是 `D-021` 豁免三的前提。

    它就是 `parse_intent(ask_model=...)` 要的那个可调用对象。
    """

    def __init__(self, provider: Provider, aliases):
        self.provider = provider
        self.aliases = list(aliases)
        #: 被调过没有。`parse_intent` 只在别名表落空时才调它。
        self.consulted = False
        #: 调了但没问上的原因。`None` = 没这回事。
        self.error = None

    def __call__(self, question: str) -> str:
        self.consulted = True
        try:
            return ask(self.provider, self.aliases, question)
        except ModelUnavailable as e:
            self.error = str(e)
            # 空串 ⇒ `parse_intent` 那句 `if guess and ...` 直接跳过 ⇒ 拒答。
            return ""
