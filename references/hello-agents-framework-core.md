# hello-agents 框架源码精读 —— `core/` 与 `agents/`

> **读的是源码，不是书稿。** 此前四轮读的全是 Hello-Agents 书稿正文，框架仓库一行没读过。本篇补的就是这个。

## 钉死的版本坐标

| 项 | 值 |
|---|---|
| 仓库 | `github.com/jjyaoao/helloagents` |
| commit | **`5432566d01ea1c2095c4a717fe2a010aa1c3b0bd`**（短 `5432566`），2026-06-08 13:35:39 +1000 |
| `hello_agents/version.py` | **`__version__ = "1.0.0"`** |
| `pyproject.toml:7` | `version = "1.0.0"` |
| `.python-version` | `3.12`（而 `pyproject.toml:14` 声明 `requires-python = ">=3.10"`） |

**版本差警告（贯穿全文）**：书稿各章钉的是旧 tag —— Ch7→`V0.1.1`、Ch10→`V0.2.2`、Ch11→`V0.2.5`、Ch12→`V0.2.7`。
本篇读的是 HEAD（1.0.0）。**凡与书稿对照处均显式标注版本差，不得把 1.0.0 的实现当作书里 0.2.x 的实现来指摘。**
仓库存在全部 12 个 tag（`V0.1.1`…`V1.0.0`）。

本篇范围：`hello_agents/core/`、`hello_agents/agents/`、顶层 `__init__.py` / `version.py`、根目录打包文件、`tests/` 中覆盖上述两块的部分。
**不含** `tools/` `context/` `observability/` `memory/` `skills/`（另有 agent 负责）——本篇引用到它们时只作为"依赖边"提及，不作实现判断。

---

## 覆盖表

| 文件 | 行数 | 读到什么程度 |
|---|---:|---|
| `hello_agents/__init__.py` | 58 | **全文** |
| `hello_agents/version.py` | 5 | **全文** |
| `hello_agents/core/__init__.py` | 17 | **全文** |
| `hello_agents/core/exceptions.py` | 21 | **全文** |
| `hello_agents/core/message.py` | 53 | **全文** |
| `hello_agents/core/config.py` | 103 | **全文** |
| `hello_agents/core/llm_response.py` | 107 | **全文** |
| `hello_agents/core/lifecycle.py` | 144 | 待填 |
| `hello_agents/core/streaming.py` | 150 | 待填 |
| `hello_agents/core/session_store.py` | 251 | 待填 |
| `hello_agents/core/llm.py` | 292 | 待填 |
| `hello_agents/core/llm_adapters.py` | 885 | 待填 |
| `hello_agents/core/agent.py` | 1273 | 待填 |
| `hello_agents/agents/__init__.py` | 24 | 待填 |
| `hello_agents/agents/factory.py` | 184 | 待填 |
| `hello_agents/agents/simple_agent.py` | 436 | 待填 |
| `hello_agents/agents/reflection_agent.py` | 453 | 待填 |
| `hello_agents/agents/plan_solve_agent.py` | 546 | 待填 |
| `hello_agents/agents/react_agent.py` | 1241 | 待填 |
| 根目录 `pyproject.toml` / `setup.py` / `requirements.txt` | 79/16/11 | **全文** |
| `tests/`（覆盖 core+agents 的部分） | — | 待填 |

**合计目标 6243 行**（core 3296 + agents 2884 + 顶层 63）。

---

## 1. 模块边界与依赖方向

### 1.1 实际 import 边（由 `grep -n '^from\|^import\|^\s\+from \|^\s\+import ' hello_agents/core/*.py hello_agents/agents/*.py` 提取，非印象）

**顶层包内边（模块级 import，非函数内延迟 import）：**

```
hello_agents/__init__.py:18-31
  → core.llm, core.config, core.message, core.exceptions
  → agents.simple_agent, agents.react_agent, agents.reflection_agent, agents.plan_solve_agent
  → tools.registry, tools.builtin.calculator

core/agent.py:6-9        → core.message, core.llm, core.config, core.lifecycle
core/llm.py:7-9          → core.exceptions, core.llm_response, core.llm_adapters
core/llm_adapters.py:9-10→ core.llm_response, core.exceptions
core/config.py           → （包内零依赖，只依赖 pydantic）
core/message.py          → （包内零依赖，只依赖 pydantic）
core/exceptions.py       → （零依赖，纯 stdlib Exception）
core/llm_response.py     → （零依赖，纯 dataclass）
core/lifecycle.py        → （零依赖，纯 dataclass/Enum）
core/streaming.py        → （零依赖，纯 dataclass/Enum）
core/session_store.py    → （零依赖，纯 stdlib）

agents/factory.py:7-9        → core.agent, core.llm, core.config
agents/simple_agent.py:6-11  → core.agent, core.llm, core.config, core.message, core.streaming, core.lifecycle
agents/reflection_agent.py:7-12  → 同上六项
agents/plan_solve_agent.py:6-11  → 同上六项
agents/react_agent.py:7-15   → 上述六项 **外加** tools.registry, tools.response, tools.errors
```

**分层结论：**
`exceptions / llm_response / lifecycle / streaming / message / config / session_store` 是**七个零包内依赖的叶子**，
`llm_adapters → llm → agent` 是唯一一条纵深链，`agents/*` 全部单向依赖 `core/*`。
**`core/*` 的模块级代码从不 import `agents/*`。** 这一层的方向是干净的。

### 1.2 环：存在，但被 `TYPE_CHECKING` 与函数内延迟 import 藏起来了

`core → agents` 的反向边真实存在，只是不在模块顶层：

- `core/agent.py:1144` `from ..agents.factory import default_subagent_factory`（函数体内）
- `core/agent.py:1186` `from ..agents.factory import default_subagent_factory`（函数体内）
- `agents/factory.py:7` `from ..core.agent import Agent`（模块顶层）

即 **`core.agent ⇄ agents.factory` 构成真实的双向依赖环**，靠"把一端塞进函数体"来规避 `ImportError`。
`core/agent.py:12-14` 另有三条 `TYPE_CHECKING` 边指向 `tools.registry` / `observability.trace_logger` / `tools.tool_filter`，
但同一文件在**运行期**又真的 import 了它们（`agent.py:100, 672, 691, 1145, 1185, 1221, 1236`），
所以 `TYPE_CHECKING` 在这里不是"仅类型依赖"的声明，而是**循环依赖的消音器**。

`core/agent.py` 里函数内延迟 import 触达的包：`context`（49/50/65）、`observability`（70）、`skills`（91）、
`tools`（100/672/691/1145/1185/1221/1236）、`agents`（1144/1186）。
**`core` 实际上依赖了 `tools` / `context` / `observability` / `skills` / `agents` 全部五个上层包**——
只是这些边在静态 import 图上不可见。想画准这张图，必须 grep 函数体内的 import，光看文件头会得到一张假的分层图。

### 1.3 `core` 与 `agents` 的职责切分

| | `core/` | `agents/` |
|---|---|---|
| 放什么 | 数据结构（Message / LLMResponse / AgentEvent / StreamEvent）、LLM 传输层（llm + llm_adapters）、`Agent` 抽象基类、会话落盘 | 四种推理范式的具体实现 + 工厂 |
| 不放什么 | 具体范式的 prompt 与循环 | 任何跨范式共享的基础设施 |

切分本身合理。**但 `core/agent.py` 1273 行严重超载**：它同时是抽象基类、Skills 加载器、Session 存取器、
SubAgent 装配器、TodoWrite/DevLog 挂载器、Trace 初始化器。基类里塞了 7 个可选子系统的开关逻辑
（见 `core/agent.py:49-106` 的构造函数延迟 import 块）。**这是 1.0.0 相对早期版本膨胀最厉害的地方。**

---

## 2. 核心抽象

### 2.1 `Message`（`core/message.py`，53 行，全文）

Pydantic v2 `BaseModel`，四个字段（12-15）。角色是 `Literal`（第 7 行）：
`"user" | "assistant" | "system" | "tool" | "summary"` —— **注意有 `summary`**，压缩产生的摘要与真实对话共用一条消息流。

两处值得记的坑：

- **`message.py:14` `timestamp: datetime = None`** —— 注解是非 Optional 的 `datetime`，默认值却是 `None`。
  能跑通只因为第 17-23 行自写的 `__init__` 总会填 `datetime.now()`。
- **`message.py:41-45` `from_dict` 会把 `timestamp=None` 显式传进去**：`data.get("timestamp")` 缺键时返回 `None`，
  而 `__init__` 第 21 行用的是 `kwargs.get('timestamp', datetime.now())` —— 键存在且值为 `None` 时**取到的是 `None`，不是默认值**。
  于是 `Message.from_dict({"content": "x", "role": "user"})` 会把 `None` 送进 pydantic 校验。
  （实测见本文 §7。）

### 2.2 `Config`（`core/config.py`，103 行，全文）

Pydantic v2 `BaseModel`，**约 50 个扁平字段**（11-89 行），全部带默认值，**没有任何 `@field_validator` / `@model_validator`**
（`grep -c 'validator' hello_agents/core/config.py` → 0）。详见 §6。

### 2.3 `LLMResponse` / `StreamStats` / `LLMToolResponse` / `ToolCall`（`core/llm_response.py`，107 行，全文）

四个 `@dataclass`，纯数据，零行为。`LLMResponse.__str__`（48-50）直接返回 `content`——
**为向后兼容而设的隐式降级**：老代码 `print(llm.invoke(...))` 仍打印正文，但 `str(resp) == resp.content` 意味着
把响应对象当字符串用时，usage / latency / reasoning 全部静默丢失，且不会报错。

### 2.4 `BaseLLMAdapter`（`core/llm_adapters.py:13-81`）—— 唯一一个真正的 ABC 扩展点

```
抽象方法（必须实现）：create_client(25) / invoke(34) / stream_invoke(39) / invoke_with_tools(73)
可选覆盖（有默认实现）：create_async_client(29, 默认 return None) / astream_invoke(43, 默认用队列+线程池包同步流)
辅助：_is_thinking_model(77)
```

三个实现：`OpenAIAdapter`(84) / `AnthropicAdapter`(329) / `GeminiAdapter`(580)。
`grep -rn 'def astream_invoke' hello_agents/` 命中 3 处：`llm.py:242`、`llm_adapters.py:43`（基类默认）、`llm_adapters.py:222`（仅 OpenAI 覆盖）。
**即 Anthropic 与 Gemini 的"异步流式"实际走的是第 43 行的线程池桥接，不是原生异步。**

`last_stats` 不在 `BaseLLMAdapter.__init__`（16-22）里初始化，只在 `stream_invoke` 成功路径末尾赋值
（`llm_adapters.py:212 / 271 / 515 / 774`）。上层 `llm.py:112 / 175 / 266` 用 `hasattr(self._adapter, 'last_stats')` 判断——
**duck typing，不是契约**。首次流式调用前该属性不存在；流式调用抛异常时也不会被赋值，
于是 `llm.last_call_stats` 会**静默停留在上一次调用的值**，而不是变成 `None`。这是一个真实的"陈旧统计冒充本次统计"的坑。

### 2.5 `HelloAgentsLLM`（`core/llm.py`，292 行，全文）—— 不是抽象，是门面

`HelloAgentsLLM` 是**具体类，不是 ABC，也没有 Protocol**。`grep -rn 'class.*LLM.*Protocol\|Protocol' hello_agents/core/` 无命中。
换一个 LLM 后端的正确扩展点是写 `BaseLLMAdapter` 子类，**但 `create_adapter`（`llm_adapters.py:860-884`）是硬编码的
`if base_url 含某子串` 三分支，没有注册表**——见 §3。

构造函数（28-78）是全仓库**唯一严格的 fail-fast 校验点**：

- `llm.py:62-63` 无 model → `raise HelloAgentsException`
- `llm.py:64-65` 无 api_key → `raise HelloAgentsException`
- `llm.py:66-67` 无 base_url → `raise HelloAgentsException`

三条都抛**基类** `HelloAgentsException`，而不是已经定义好的 `ConfigException`（`exceptions.py:15`）。见 §4。

其余方法：`think`(80) / `invoke`(119) / `stream_invoke`(148) / `invoke_with_tools`(178) /
`ainvoke`(219) / `astream_invoke`(242) / `ainvoke_with_tools`(269)。

**异步是半真半假的**：`ainvoke`(236-240) 与 `ainvoke_with_tools`(288-291) 用 `run_in_executor` 包同步调用，
只有 `astream_invoke`(262) 走 adapter 的原生异步。两者都用 `asyncio.get_event_loop()`
（`llm.py:236, 288`；`llm_adapters.py:49`），在 `.python-version` 声明的 3.12 下这是 DeprecationWarning 路径，
正确写法是 `get_running_loop()`。

**`think()` 无条件 `print` 到 stdout**：`llm.py:95`（"🧠 正在调用…"）、`llm.py:105`（"✅ …响应成功"）、
`llm.py:107`（逐 chunk `print`）、`llm.py:116`（"❌ 调用LLM API时发生错误"）。库代码直接占用 stdout，无 logger 开关。

### 2.6 扩展一个新 Agent 需要实现什么

见 §3.2（`Agent` 基类抽象方法清单），读完 `core/agent.py` 后填。

---
