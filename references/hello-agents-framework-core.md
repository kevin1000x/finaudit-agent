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
| `hello_agents/core/lifecycle.py` | 144 | **全文** |
| `hello_agents/core/streaming.py` | 150 | **全文** |
| `hello_agents/core/session_store.py` | 251 | **全文** |
| `hello_agents/core/llm.py` | 292 | **全文** |
| `hello_agents/core/llm_adapters.py` | 885 | **全文** |
| `hello_agents/core/agent.py` | 1273 | **全文** |
| `hello_agents/agents/__init__.py` | 24 | **全文** |
| `hello_agents/agents/factory.py` | 184 | **全文** |
| `hello_agents/agents/simple_agent.py` | 436 | **全文** |
| `hello_agents/agents/reflection_agent.py` | 453 | **全文** |
| `hello_agents/agents/plan_solve_agent.py` | 546 | **全文** |
| `hello_agents/agents/react_agent.py` | 1241 | **全文** |
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

**逐行复核补出的两处（2026-08-22 本轮）：**

1. **`stream_invoke` 会把 `temperature=None` 显式发给后端，不回退到 `self.temperature`。**
   `llm.py:163` `temperature = kwargs.pop("temperature", None)`，第 171 行原样传
   `self._adapter.stream_invoke(messages, temperature=temperature, ...)`。
   对比 `invoke`（`llm.py:140` `kwargs.pop("temperature", self.temperature)`）与 `think`
   （`llm.py:99` `temperature if temperature is not None else self.temperature`）——**三个方法三种语义**。
   于是 `llm.stream_invoke(msgs)` 与 `llm.invoke(msgs)` 在同一个 `HelloAgentsLLM` 实例上用的是**不同的温度**：
   前者 `None`（交给后端默认，OpenAI 侧是 1.0），后者 `0.7`。构造时传的 `temperature=0.7` 对流式路径**静默失效**。
2. `think()`（80-117）**不接受 `max_tokens` 参数**，只用 `self.max_tokens`（101-102）；
   而 `invoke`/`stream_invoke`/`invoke_with_tools` 都在 `self.max_tokens` 为 `None` 时**跳过 pop**
   （`llm.py:142 / 167 / 211` 的 `if self.max_tokens:`），此时调用方传的 `max_tokens` 会经由
   `call_kwargs.update(kwargs)` 落到后端——**能否覆盖 `max_tokens`，取决于实例上有没有设过它**。

### 2.6 扩展一个新 Agent 需要实现什么

见 §3.2（`Agent` 基类抽象方法清单），读完 `core/agent.py` 后填。

---

### 2.7 `AgentEvent` / `EventType` / `ExecutionContext`（`core/lifecycle.py`，144 行，全文）

零包内依赖，纯 `dataclass` + `Enum`，144 行里注释与 docstring 占一半以上。三个导出物：

| 名字 | 行 | 实质 |
|---|---:|---|
| `EventType` | 15-40 | **14 个成员**的 Enum，值为 snake_case 字符串 |
| `AgentEvent` | 43-106 | 4 字段 dataclass：`type` / `timestamp` / `agent_name` / `data: Dict[str, Any]` |
| `LifecycleHook` | 110 | 类型别名 `Optional[Callable[[AgentEvent], Awaitable[None]]]` |
| `ExecutionContext` | 113-143 | `input_text` / `current_step` / `total_tokens` / `metadata` + 四个 setter |

**`data` 是无 schema 的 `Dict[str, Any]`（57 行）**，`AgentEvent.create`（59-89）用 `**data` 收所有关键字参数。
即：事件负载没有任何结构约束，`TOOL_CALL` 事件里到底有没有 `tool_name` 全靠调用方自觉。
`to_dict`（91-102）直接把这个 dict 塞进序列化结果。**要做可机读的证据链，这是反面样本**——见 §8。

**`ExecutionContext` 在框架内是死代码。**
`grep -rn 'ExecutionContext' hello_agents/ examples/ tests/ --include=*.py` 命中 4 处：
定义处 `lifecycle.py:114`、`core/agent.py:9`（只 import 不使用）、`tests/test_async_lifecycle.py:96 / 104`。
**`hello_agents/` 生产代码里没有任何一处构造或消费它**（`grep -rn 'ExecutionContext(' hello_agents/` → 0 命中）。
`current_step` / `total_tokens` 的实际累计发生在各 Agent 自己的循环变量里，不走这个上下文对象。

### 2.8 `StreamEvent` / `StreamEventType`（`core/streaming.py`，150 行，全文）—— 与 §2.7 平行的**第二套**事件系统

同样零包内依赖，同样 dataclass + Enum，结构与 `AgentEvent` **逐字段相同**
（`type` / `timestamp` / `agent_name` / `data`，见 `streaming.py:26-29` vs `lifecycle.py:54-57`），
`create` 分类方法（32-39）与 `to_dict`（64-71）也是同一份代码的两个副本。

**两套枚举的成员比对**（脚本比对，非目测）：

```
lifecycle.EventType        14 个成员
streaming.StreamEventType   9 个成员
交集 6：AGENT_START / AGENT_FINISH / STEP_START / STEP_FINISH / LLM_CHUNK / THINKING
仅 lifecycle 8：AGENT_ERROR / LLM_START / LLM_FINISH / TOOL_CALL / TOOL_RESULT / TOOL_ERROR / PLAN / REFLECTION
仅 streaming 3：ERROR / TOOL_CALL_START / TOOL_CALL_FINISH
```

**同一件事在两套枚举里叫不同名字**：工具调用开始，lifecycle 叫 `TOOL_CALL`，streaming 叫 `TOOL_CALL_START`；
错误，lifecycle 叫 `AGENT_ERROR`，streaming 叫 `ERROR`。**没有任何转换函数把两者对齐**
（`grep -rn 'StreamEventType(' hello_agents/` 与 `grep -rn 'def.*to_stream_event\|def.*to_agent_event' hello_agents/` 均 0 命中）。

实际用量严重倾斜：`grep -rn 'AgentEvent' hello_agents/ | wc -l` → **13**；`grep -rn 'StreamEvent' hello_agents/ | wc -l` → **102**。
四个 Agent 全部 import `streaming`（`simple_agent.py:10` / `reflection_agent.py:11` / `plan_solve_agent.py:10` / `react_agent.py:12`），
但只有 `react_agent.py:11` 同时 import 了 `lifecycle` 的 `AgentEvent`/`EventType`。
**`AgentEvent` 事实上只在 `core/agent.py` 与 `react_agent.py` 两处活着，其余三个 Agent 只用 `LifecycleHook` 这个类型别名，从不构造 `AgentEvent`。**
于是 hook 的签名要求传 `AgentEvent`，而 SimpleAgent/ReflectionAgent/PlanSolveAgent 走的是 StreamEvent 流——
**类型别名与实际流经的数据类型不是同一个类**。

**`streaming.py` 的后半段是整段死代码。**
`StreamBuffer`(74-105) / `stream_to_sse`(108-127) / `stream_to_json`(130-149) 合计 **76 行**，
`grep -rln 'StreamBuffer\|stream_to_sse\|stream_to_json' .`（排除 `.git/`）**只命中 `hello_agents/core/streaming.py` 自身**——
仓库内 `hello_agents/` `tests/` `examples/` `docs/` 无任何调用方。
`StreamBuffer.add`(87-93) 的"背压控制"是 `if len > max: self.events.pop(0)`——**静默丢弃最旧事件，不计数、不告警、不抛异常**。
若将来接上，这是一条证据链会无声缺页的路径。

另有 `streaming.py:4` `from dataclasses import dataclass, asdict` —— `asdict` 全文未使用
（`grep -c 'asdict' hello_agents/core/streaming.py` → 1，即 import 那一行）。

### 2.9 `SessionStore`（`core/session_store.py`，251 行，全文）—— 存什么、能不能重建

单类 `SessionStore`(19)，构造只做 `mkdir(parents=True, exist_ok=True)`(56)。六个方法：
`_generate_session_id`(58) / `save`(70) / `load`(128) / `list_sessions`(146) / `delete`(175) /
`check_config_consistency`(190) / `check_tool_schema_consistency`(229)。

**落盘的 JSON 结构（`session_store.py:104-116`，八个键）：**

```
session_id / created_at / saved_at / agent_config / history / tool_schema_hash / read_cache / metadata
```

- `session_id` 格式 `s-{YYYYmmdd-HHMMSS}-{uuid4 前 8 hex}`（66-68）。
- `history` 序列化用 **duck typing**：`msg.to_dict() if hasattr(msg,'to_dict') else msg`（110-111）。
  没有 `to_dict` 的对象**原样塞进 `json.dump`**，落到 111 行不会报错，报错点会推迟到 121 行的
  `json.dump` 抛 `TypeError`——错误位置与真实原因相隔 10 行且信息不含哪条消息有问题。
- 写入是**真原子**的：`temp_path = filepath + ".tmp"` → `json.dump` → `os.replace`（118-124）。
  这一点做得对，`os.replace` 在 POSIX 与 Windows 上都是原子替换。
  **但没有 fsync**，断电场景下 rename 可能先于数据落盘可见。

**能否重建：不能完全重建。** 存下来的 `agent_config` 是什么，由调用方 `core/agent.py:712 / 744` 决定（见 §5）；
`history` 是消息序列；**但没有存 LLM 的 `temperature` / `seed` / 实际返回的 `usage`，也没有存每一步的工具返回原文**。
`grep -n 'temperature\|seed\|usage' hello_agents/core/session_store.py` → **0 命中**。
即：**会话可以"接着聊"，但不可"重放验证"**——同样的 history 重跑一遍不保证得到同样结果，也无从判断差异来自模型还是来自配置。

**一致性检查是三个字段的字符串比对（190-227）**：`llm_provider` / `llm_model` / `max_steps`，
不一致时**只往 `warnings` 列表里塞中文字符串**，返回 `{"consistent": bool, "warnings": [...]}`，
**不抛异常、不阻断加载**。`check_tool_schema_consistency`(229-250) 同理，返回值里的
`"recommendation": "建议重新读取文件" if changed else "可以安全恢复"`（249）是**给人读的中文句子，不是机读的枚举码**。
调用方拿到它以后怎么处理，见 §4。

**"一个事实两个来源"：`tool_schema_hash` 是外部传入的字符串（74 行参数），`SessionStore` 自己不算哈希。**
`from hashlib import sha256` 在 `session_store.py:16`，但 **全文只出现这一次**
（`grep -c 'sha256' hello_agents/core/session_store.py` → 1，即 import 行本身）——
**导入了哈希库却从未调用**，哈希的计算责任在别处（见 §5 对 `core/agent.py` 的追查）。
这意味着"这份会话对应哪套工具"这个事实，存储层无法自证，只能相信写入方给的字符串。

`list_sessions`(146-173) 是本文件唯一的 `except`：**155-168 行 `try` 包住整个读文件+解析，
`except Exception as e: print(f"⚠️ 警告：无法读取 {filepath}: {e}")`（167-168）——
损坏的会话文件被静默跳过，返回的列表里直接没有它，调用方无法区分"没有这个会话"与"这个会话读不出来"。**


---

## 3. 注册、扩展点与冲突处理

### 3.1 LLM 提供商：**没有注册表，只有一个三分支 `if`**（`core/llm_adapters.py:860-884`）

```
create_adapter(api_key, base_url, timeout, model) -> BaseLLMAdapter
  874  if base_url:
  877      if "anthropic.com"      in base_url.lower(): return AnthropicAdapter(...)
  880      if "googleapis.com" in ... or "generativelanguage" in ...: return GeminiAdapter(...)
  884  return OpenAIAdapter(...)      # 兜底，无条件
```

`grep -rn 'register\|REGISTRY\|_registry' hello_agents/core/llm_adapters.py` → **0 命中**。
**扩展第四家提供商必须改这个函数**，无法从包外注入。`BaseLLMAdapter` 是真 ABC（`llm_adapters.py:13`，
`from abc import ABC, abstractmethod` 在第 6 行），但**有 ABC 不等于有扩展点**——
子类写出来了也接不进来，因为选路径写死在 `create_adapter` 里。

**兜底分支是静默的**：base_url 拼错（比如 `https://api.anthropc.com`，少个 i）不会报错，
会**默默落到 `OpenAIAdapter`**，然后在真正发请求时报一个来自 OpenAI SDK 的、与"选错适配器"毫无关系的错误。
`base_url` 为 `None` 时同样落到 OpenAI 分支——但 `llm.py:66-67` 在更上游已经拦掉了空 base_url，
所以这条路只有直接调 `create_adapter` 才走得到。

**路由键在被 Gemini 分支选中后就被丢掉了。**
`GeminiAdapter.create_client`（`llm_adapters.py:587-597`）只用 `api_key`：`genai.Client(api_key=self.api_key)`（596）。
`grep -c 'base_url'`（限 `GeminiAdapter` 类体 580-859 行）→ **0**。
即：`base_url` 唯一的作用是"把你路由到 Gemini"，之后 SDK 走官方默认端点。
**指向自建 Gemini 代理的 base_url 会被静默忽略，请求实际发往 Google**——这在合规/数据出境场景下是硬伤。
（`AnthropicAdapter.create_client:346-350` 与 `OpenAIAdapter.create_client:97-101` 都正常传了 `base_url`，只有 Gemini 丢。）

### 3.2 三个适配器的边界：**统一的是 OpenAI 方言，不是中立协议**

`llm_adapters.py` 885 行里，**约 320 行是格式转换**，转换方向清一色 "OpenAI 格式 → 各家格式"：

| 转换器 | 行 | 干什么 |
|---|---:|---|
| `AnthropicAdapter._convert_messages` | 352-397 | 抽出 system；`assistant+tool_calls` → `tool_use` block；`role:"tool"` → **伪装成 `role:"user"` 的 `tool_result`** |
| `AnthropicAdapter._convert_tools` | 399-416 | `function.parameters` → `input_schema` |
| `AnthropicAdapter._convert_tool_choice` | 418-428 | `"required"` → `{"type":"any"}`；`auto`/`none` **一律 → `None`** |
| `GeminiAdapter._convert_messages` | 599-655 | 同上 + `assistant` → `role:"model"` |
| `GeminiAdapter._convert_tool_choice` | 657-680 | `"none"` → `FunctionCallingConfig(mode="NONE")` |

**边界结论：这不是"多提供商抽象层"，是"以 OpenAI Chat Completions 为中心表示的翻译层"。**
中心表示的选择带来三处不可逆的语义损失，全部静默：

1. **`tool_choice="none"` 在 Anthropic 侧被吃掉。**
   `_convert_tool_choice:420-421` 把 `None`、`"auto"`、`"none"` 三者**映射到同一个返回值 `None`**，
   而 `invoke_with_tools:544-545` 是 `if tool_choice: request_params["tool_choice"] = tool_choice`——
   `None` 意味着不设置该参数，Anthropic 默认行为等价于 `auto`。
   **于是"强制不要调工具"在 Claude 后端变成"随你便调工具"，没有任何警告。**
   Gemini 侧则正确区分了（`663-666` 有独立的 `mode="NONE"` 分支）。同一个入参，两家后端两种行为。
2. **Anthropic 的 `max_tokens` 被硬编码兜底成 4096**（`443` / `491` / `539`，三处相同）。
   OpenAI 与 Gemini 侧不设默认（`llm_adapters.py:697-698 / 811-812` 只在 kwargs 里有才传）。
   同一段代码换个 base_url，输出长度上限从"后端默认"变成"4096"。
3. **Gemini 的 `tool_call.id` 是现造的时间戳**：
   `llm_adapters.py:835` `id=f"call_{int(time.time()*1000)}"`，且这行在 `for part in ...parts` 循环体内（832-838）。
   **同一次响应里返回多个工具调用时，它们极可能拿到完全相同的 id**（同毫秒内），
   而 id 正是后续把工具结果配回请求的唯一键（`_convert_messages:625-627` 用它建 `tool_call_id → tool_name` 映射）。
   **id 撞车 → 工具结果错配 → 证据链把 A 工具的结果记在 B 工具名下，且不会报错。**
   `grep -n 'uuid' hello_agents/core/llm_adapters.py` → **0 命中**，全文没有用过唯一 ID 生成器。

另有一处**跨轮次的静默降级**：`GeminiAdapter._convert_messages:605` 的 `tool_call_names` 字典
**在每次调用时从空重建**，只收集本次 `messages` 列表里出现过的 assistant tool_calls。
第 639 行 `tool_call_names.get(msg.get("tool_call_id"), "tool_result")` ——
**历史被截断（发生在 `core/agent.py` 的上下文压缩里）后，工具结果的函数名会静默退化成字符串 `"tool_result"`**，
Gemini 收到一个名字对不上任何已声明函数的 function_response。

### 3.3 失败处理：**12 处 `raise HelloAgentsException(f"...: {str(e)}")`，零处异常链**

`grep -c 'raise HelloAgentsException' hello_agents/core/llm_adapters.py` → **12**。
每个适配器的每个方法都是同一个模板：`except Exception as e: raise HelloAgentsException(f"<厂商> <动作>失败: {str(e)}")`。

- **`grep -rn 'raise .* from ' hello_agents/ --include=*.py` → 0 命中**：全包**没有一处显式 `raise ... from e`**。
  （隐式 `__context__` 还在，traceback 仍能看到原因；但**异常类型被拍平**，上层拿不到 `RateLimitError` / `APITimeoutError`
  这类可分支处理的类型，只能拿到一个基类异常 + 一个中文字符串。）
- **异常体系是装饰性的。** `core/exceptions.py:7-21` 定义了 `LLMException` / `AgentException` /
  `ConfigException` / `ToolException` 四个子类，逐个 grep `raise <类名>` 全包命中数：

  ```
  ConfigException: 0    LLMException: 0    ToolException: 0    AgentException: 0
  ```

  **四个子类一次都没有被 raise 过。** 所有异常都塌缩到基类 `HelloAgentsException`。
  想按错误类别做重试/降级/拒答分流，必须去 match 中文字符串。**这是 D-003"拒答可机读"的精确反例**（见 §8）。

### 3.4 其余零散但会咬人的点（`llm_adapters.py`）

- **`usage` 缺失与 `usage` 为零不可区分**：`145 / 202 / 261 / 462 / 506 / 715 / 765 / 841` 一律
  `if hasattr(...) and ...: usage = {...}`，否则保持 `usage = {}`。
  下游拿到 `{}` 无法判断是"后端没返回用量"还是"这次调用没花 token"。
- **`_is_thinking_model`（77-81）是无边界的子串匹配**：`["reasoner","o1","o3","thinking"]`，
  不区分大小写、不做词边界、**没有任何配置项可以覆盖**（`grep -n 'thinking_keywords' hello_agents/` 仅 1 处，即定义处）。
  这个判断是 `reasoning_content` 是否被抽取的**唯一开关**（`135` / `194` / `253`）——
  **命中不了的推理模型，它的推理过程被静默丢弃**，`LLMResponse.reasoning_content` 恒为 `None`，不报错。
- **死变量**：`collected_content` 在 `178`/`190`（同步流）与 `237`/`249`（异步流）被创建并 append，
  **两处都从未被读取**（`grep -n 'collected_content'` 共 4 命中，全是赋值与 append）。
  流式路径因此**不保留完整响应文本**——`StreamStats`（212/271/515/774）只存 model/usage/latency/reasoning，
  **不存 content**。想在证据链里留下"模型到底说了什么"，流式路径拿不到，只能靠调用方自己拼 chunk。
- **默认 `astream_invoke`（43-70）在 3.12 上是弃用路径**：`49` 行 `asyncio.get_event_loop()`；
  `61` 行 `loop.run_in_executor(None, _stream_to_queue)` **返回的 future 未被持有也未被 await**，
  内部 `asyncio.run_coroutine_threadsafe(...)`（54/56/58）返回的三个 future 同样从不检查——
  队列写入失败时无人知晓。**Anthropic 与 Gemini 的"异步流式"走的就是这条路**（二者均未覆盖 `astream_invoke`，
  `grep -n 'async def astream_invoke' hello_agents/core/llm_adapters.py` → 仅 `43`（基类）与 `222`（OpenAI））。
- **`OpenAIAdapter.invoke_with_tools`（281-282）把 `tool_choice` 提成了显式形参**，
  而基类抽象签名（`73`）与另外两家（`524` / `783`）都是 `**kwargs`。
  能跑通只因为 `llm.py:209` 是按关键字传的；改成位置参数即刻在 Anthropic/Gemini 上炸。


### 3.5 `Agent` 基类的扩展契约（`core/agent.py`，1273 行，全文）

**是真 ABC，但抽象面积只有一行。**
`class Agent(ABC)`（`agent.py:17`），`grep -rn '@abstractmethod' hello_agents/core/agent.py` → **仅 1 处，第 145 行**：

```python
145  @abstractmethod
146  def run(self, input_text: str, **kwargs) -> str:
```

**扩展一个新 Agent 的最小契约 = 实现 `run(self, input_text, **kwargs) -> str`，
再在 `__init__` 里 `super().__init__(name, llm, system_prompt, config, tool_registry)`。**
其余一切（`arun` / `arun_stream` / 工具 schema 构建 / 工具执行 / 会话存取 / 子代理 / 摘要压缩）都有默认实现。
四个子类：`SimpleAgent`(`simple_agent.py:16`) / `ReflectionAgent`(`reflection_agent.py:46`) /
`PlanSolveAgent`(`plan_solve_agent.py:262`) / `ReActAgent`(`react_agent.py:42`)。

**这个契约弱到几乎不成为契约。** 「返回 `str`」是唯一的输出约定——
没有结构化返回、没有置信度、没有证据字段、没有"我拒绝回答"的表达方式。
Agent 只能把失败编码进那个字符串（实际做法见 §4：`return f"❌ 工具调用失败：{exc}"`）。
**基类层面就不存在"可机读的拒答"这个概念**，这是 §8 第 1 条启示的根。

三个**非抽象但期望被覆盖**的方法（duck typing，覆盖与否无检查）：

| 方法 | 行 | 默认行为 | 谁真的覆盖了 |
|---|---:|---|---|
| `arun` | 152-214 | 线程池跑同步 `run()` | 四个子类全部覆盖 |
| `arun_stream` | 216-263 | 只发 START/FINISH 两个事件 | 四个子类全部覆盖（改发 `StreamEvent`，见 §2.8 的类型错配） |
| `_generate_smart_summary` | 385-455 | docstring 写"需要子类实现"（348、353 行注释），但基类给了完整实现 | **无人覆盖** |

### 3.6 基类超载的实测口径

`agent.py` 单个 `class Agent` 里有 **41 个方法定义、39 个不重名**（AST 统计）。
`__init__`（32-131）在 **100 行内串起 8 个可选子系统**，每个都是"函数内延迟 import + config 开关"：
HistoryManager/Truncator(49-62)、TokenCounter(65-67)、TraceLogger(70-87)、SkillLoader(89-102)、
SessionStore(104-110)、TaskTool(122-123)、TodoWriteTool(126-127)、DevLogTool(130-131)。

**其中一批 import 是无条件执行的**（49/50/65/70/90/91/105/106），
即使 `trace_enabled=False`、`skills_enabled=False` 也照样 import 整个 `observability` 与 `skills` 包。
开关只控制**是否实例化**，不控制**是否加载**。装了 `hello-agents` 就得吃下全部可选依赖的 import 成本。

**`_register_task_tool` 被定义了两次**（AST 确认）：

```
DUPLICATE: _register_task_tool  [1139, 1180]
DUPLICATE: _history             [134, 139]   ← 这个是正常的 property/setter 对
```

`1139-1178` 的那份**是死代码**——Python 后定义覆盖先定义，实际生效的永远是 `1180-1214` 那份。
两份的差别在造轻量 LLM 的方式：死掉的那份在 `1153-1157` 内联 `HelloAgentsLLM(provider=..., model=...)`，
活着的那份在 `1194` 调 `self._create_light_llm()`。**没有任何 linter 拦下这个**（仓库无 flake8/ruff 配置，见 §6）。

---

## 4. 错误处理与静默降级 —— 逐处行号

### 4.1 两个**永远不会正确触发**的 flag（本节最重要的发现）

本项目 `rules/failure-modes.md` 第 2 条说的就是这个：**拿手边能求值的东西凑一个 trigger，造出的是永远不会正确触发的假规则。**
`core/agent.py` 里有两个现成样本。

**(a) `llm_provider` 恒为字符串 `"unknown"`，"换了提供商"的一致性检查因此永远沉默。**

```
agent.py:830   "llm_provider": getattr(self.llm, 'provider', 'unknown'),
```

`grep -c 'provider' hello_agents/core/llm.py` → **0**。
`HelloAgentsLLM` 从未设置过 `self.provider`（`__init__` 只设 `model`/`api_key`/`base_url`/`timeout`/
`temperature`/`max_tokens`/`kwargs`，见 `llm.py:52-59`）。
于是 `getattr` 永远走默认值分支，`_get_agent_config()` 返回的 `llm_provider` **恒等于 `"unknown"`**。
下游 `session_store.py:207` 比的是 `saved.get("llm_provider") != current.get("llm_provider")`
→ `"unknown" != "unknown"` → **恒为 False → 这条 warning 永远不会产生**。
从 DeepSeek 换成 Claude 再恢复会话，检查器一声不吭。

**(b) 工具 Schema 哈希不含任何参数信息，"工具定义变了"的检查对参数改动完全失明。**

```
agent.py:862   "parameters": list(tool.parameters.keys()) if hasattr(tool, 'parameters') and tool.parameters else []
```

`Tool.__init__`（`tools/base.py:67-77`）只设 `self.name` / `self.description` / `self.expandable`。
`grep -rn 'self\.parameters *=' hello_agents/ --include=*.py` → **0 命中**，全包没有任何地方给工具对象赋 `.parameters`。
参数的真实入口是 `get_parameters()`（`tools/base.py:96-99`，抽象方法），返回 `List[ToolParameter]`。
**于是 `hasattr(tool,'parameters')` 对包内每一个工具都是 `False`，第 862 行恒为 `[]`。**

哈希（`agent.py:865-866`，sha256 取前 16 位）实际只覆盖：工具名 + **前 100 字符**的描述（`861`）。后果：

- 给工具**加一个必填参数** → 哈希不变 → `check_tool_schema_consistency` 返回 `changed=False`，
  `recommendation` 是 **"可以安全恢复"**（`session_store.py:249`）。恢复出来的会话会用旧参数调新工具。
- 改描述第 101 字符之后的内容 → 哈希不变。
- **函数工具（`tool_registry._functions`）完全不在哈希里**：`856` 行只遍历 `list_tools()`，
  而 `_build_tool_schemas` 明确知道还有 `_functions` 这一路（`agent.py:557-575`）。增删函数工具，哈希纹丝不动。

这两处合起来，就是 §5 要说的"会话可续、不可验"。

### 4.2 `core/` + `agents/` 全部吞异常点（AST 扫描，非目测）

扫描口径：遍历两个包内每个 `ExceptHandler`，凡 handler 子树里**没有任何 `raise`** 的即计入。
`SWALLOW` = 记了个日志或赋了个默认值就继续；`SWALLOW-return` = 直接返回兜底值。

| 位置 | 捕获类型 | 类别 | 兜底动作 |
|---|---|---|---|
| `core/llm_adapters.py:55` | `Exception` | SWALLOW | 把异常塞进 queue（**这处是对的**，消费端 `:69` 会 re-raise） |
| `core/llm_adapters.py:371` | `json.JSONDecodeError` | SWALLOW | `arguments = {}` |
| `core/llm_adapters.py:621` | `json.JSONDecodeError` | SWALLOW | `arguments = {}` |
| `core/session_store.py:167` | `Exception` | SWALLOW | print 一行警告，该会话从列表里消失 |
| `core/agent.py:285` | `asyncio.TimeoutError` | SWALLOW | 钩子超时 → 只写 trace 事件 |
| `core/agent.py:292` | `Exception` | SWALLOW | 钩子异常 → 只写 trace 事件 |
| `core/agent.py:452` | `Exception` | SWALLOW-return | print 后退回简单摘要 |
| `core/agent.py:528` | `Exception` | SWALLOW | `parameters = []` → **该工具的 schema 变成"无参数"** |
| `core/agent.py:613` | `Exception` | SWALLOW-return | `return param_dict` → 跳过类型转换 |
| `core/agent.py:642` | `(TypeError, ValueError)` | SWALLOW | `converted[key] = value` → 转换失败原样传 |
| `core/agent.py:680` | `Exception` | SWALLOW-return | `return f"❌ 工具调用失败：{exc}"` |
| `core/agent.py:699` | `Exception` | SWALLOW-return | 同上 |
| `core/agent.py:720` | `Exception` | SWALLOW | 自动保存失败，**仅在 `config.debug` 为真时才 print**（`722`） |
| `core/agent.py:950` | `Exception` | SWALLOW | 子代理执行失败 → `result = f"执行失败: {error_msg}"` |
| `agents/simple_agent.py:142` | `Exception` | SWALLOW | print "❌ LLM 调用失败" |
| `agents/simple_agent.py:203` | `json.JSONDecodeError` | SWALLOW | print "❌ 工具参数解析失败" |
| `agents/reflection_agent.py:232` | `Exception` | SWALLOW | 同上 |
| `agents/reflection_agent.py:266` | `json.JSONDecodeError` | SWALLOW | 同上 |
| `agents/plan_solve_agent.py:85` | `Exception` | SWALLOW-return | print "❌ 生成计划时发生错误" |
| `agents/plan_solve_agent.py:202` | `Exception` | SWALLOW | print "❌ LLM 调用失败" |
| `agents/plan_solve_agent.py:236` | `json.JSONDecodeError` | SWALLOW | 同上 |
| `agents/react_agent.py:121` | `Exception` | SWALLOW | print "❌ 保存失败" |
| `agents/react_agent.py:132` | `Exception` | SWALLOW | print "❌ 保存失败"（**嵌套的第二层**，见 §7.2） |
| `agents/react_agent.py:181` | `Exception` | SWALLOW | print "❌ LLM 调用失败" |
| `agents/react_agent.py:264` | `json.JSONDecodeError` | SWALLOW | print "❌ 工具参数解析失败" |
| `agents/react_agent.py:558` | `Exception` | SWALLOW | print "❌ LLM 调用失败" |
| `agents/react_agent.py:772` | `json.JSONDecodeError` | SWALLOW | 把中文错误串当**工具结果**塞回历史 |
| `agents/react_agent.py:818` | `json.JSONDecodeError` | SWALLOW-return | 同上 |
| `agents/react_agent.py:848` | `Exception` | SWALLOW | `result_content = f"❌ 工具执行失败: {str(e)}"` |
| `agents/react_agent.py:963` | `Exception` | SWALLOW | `error_msg = f"LLM 调用失败: {str(e)}"` |
| **`agents/react_agent.py:1055`** | **裸 `except:`** | SWALLOW | `final_answer = result_dict["content"]` |
| `agents/react_agent.py:1080` | `Exception` | SWALLOW | `error_msg = f"工具执行失败: {str(e)}"` |
| `agents/react_agent.py:1155` | `json.JSONDecodeError` | SWALLOW | 同 772 |
| `agents/react_agent.py:1195` | `json.JSONDecodeError` | SWALLOW-return | 同 818 |
| `agents/react_agent.py:1225` | `Exception` | SWALLOW | `result_content = f"❌ 工具执行失败: {str(e)}"` |

**合计 35 处吞异常，0 处 `except: pass`**（AST 扫描确认，`PASS` 类别一处未命中）。
裸 `except:` 全包共 3 处（`grep -rn 'except:' hello_agents/`）：`react_agent.py:1055` 与
`tools/builtin/file_tools.py:189 / 196`（后两处不在本篇范围）。
`react_agent.py:1055` 的裸 `except` 会**连 `KeyboardInterrupt` 与 `SystemExit` 一起吃掉**。

### 4.3 静默降级的四种形态（本仓库全都有）

1. **默认值兜底**：`arguments = {}`（`llm_adapters.py:371/621`）、`parameters = []`（`agent.py:528`）、
   `max_tokens=4096`（`llm_adapters.py:443/491/539`）、`usage = {}`（八处，见 §3.4）。
   共同点：**兜底值与合法值同型**，下游无法区分"没拿到"和"拿到的就是空"。
2. **`print` 代替 `raise`**：`grep -rc 'print(' hello_agents/core/*.py hello_agents/agents/*.py` 合计 **200+ 次**，全部直写 stdout。
   `grep -rn 'import logging' hello_agents/core/ hello_agents/agents/` → **0 命中**——
   **这两个包里没有一行用 logging**。库的错误信息无法被调用方捕获、分级或转发。
3. **错误串冒充结果**：`agent.py:662/675/677/681/694/696/699/702` 与
   `react_agent.py:772/818/848/1155/1195/1225` 把中文错误串当成**工具返回值**写回消息历史。
   模型看到的是 `"❌ 错误 [UNKNOWN]: ..."` 这样一段文本，与真实结果在同一个字段里，**没有 status 位**。
   （`tools/response.py` 其实有 `ToolStatus` 枚举，`agent.py:672-679` 读了它——**读完就拍扁成字符串**。
   结构化状态在跨过 Agent 边界的一瞬间被丢弃。）
4. **异常类型拍平**：见 §3.3，四个异常子类 0 次被 raise，全包 0 处 `raise ... from`。

### 4.4 钩子失败是静默的（`agent.py:265-298`）

`_emit_event` 用 `asyncio.wait_for(hook(event), timeout=...)`，超时（`285`）与异常（`292`）
**都只在 `trace_logger` 存在时写一条 trace 事件**（`287-291` / `294-298`）。
`trace_logger` 为 `None` 时（`config.trace_enabled=False`），**钩子彻底失败而无任何记录**。
超时值取自 `getattr(self.config,'hook_timeout_seconds', 5.0)`（`283`）——
用 `getattr` 兜底而不是直接 `self.config.hook_timeout_seconds`，说明**作者自己也不确定这个字段在不在 Config 里**。

---

## 5. 状态与可重放

### 5.1 落盘的八个键，与它们各自的来源

`SessionStore.save`（`session_store.py:104-116`）写八个键；填充它们的是 `core/agent.py`：

| 键 | 填充处 | 内容 | 可重建性 |
|---|---|---|---|
| `session_id` | `session_store.py:93` | `s-{时间}-{uuid8}` | 可 |
| `created_at` / `saved_at` | `session_store.py:106-107` | ISO 时间串 | 可 |
| `agent_config` | `agent.py:821-838` | **只有 4-5 个字段**：`name` / `agent_type` / `llm_provider`（恒 `"unknown"`）/ `llm_model` / 可选 `max_steps` | **不可**，见下 |
| `history` | `agent.py:714/746` | `history_manager.get_history()` → `Message.to_dict()` | 部分 |
| `tool_schema_hash` | `agent.py:840-866` | 名字 + 前 100 字描述的 sha256 前 16 位 | **不可**，见 §4.1(b) |
| `read_cache` | `agent.py:868-876` | `tool_registry.read_metadata_cache`（duck typing，缺则 `{}`） | 部分 |
| `metadata` | `agent.py:113-118` | `created_at` / `total_tokens` / `total_steps` / `duration_seconds` | **不可**，见下 |

**结论：可续聊，不可重放，更不可复核。** 三条硬理由：

1. **`agent_config` 里没有采样参数。**
   在 `_get_agent_config`(821-838) 范围内 grep `temperature|top_p|seed|max_tokens` → **0 命中**。
   `temperature` 明明是 `HelloAgentsLLM.__init__` 的入参（`llm.py:33`），**就是没被存**。
   同一份 history 换个 temperature 重跑，结果不同，而落盘文件里看不出来。
2. **`metadata["total_tokens"]` 只在初始化时被设为 0，此后再没被写过。**
   `grep -n '_session_metadata' hello_agents/core/agent.py` → `113`（初始化）、`717`/`749`（读出来存盘）、
   `742`（只更新 `duration_seconds`）、`802`（加载时整体覆盖）。
   **`total_tokens` 与 `total_steps` 从头到尾恒为 0。**
   真正在算 token 的是 `self._history_token_count`（`agent.py:67/309/325/363`），**它不进 metadata、不落盘**。
   这是标准的"一个事实两个来源，且落盘的那个是假的"。
3. **`history` 里没有工具调用的原始返回。** 工具结果在写进历史前已被
   `ObservationTruncator` 截断（`agent.py:57-62` 构造，按 `tool_output_max_lines` / `max_bytes`），
   且错误已被拍成中文串（§4.3 第 3 条）。
   落盘的是**加工后的观测**，不是原始证据。想复核"这个数字是从哪张表来的"，文件里没有。

### 5.2 `load_session` 的一致性检查：查了，但只 `print`（`agent.py:755-808`）

```
775-778  config_check = check_config_consistency(...)
780-783  if not consistent:  print("⚠️ 环境配置不一致：") + 逐条 print(warning)
786-789  tool_check   = check_tool_schema_consistency(...)
791-793  if changed:         print("⚠️ 工具定义已变化") + print(建议)
795-799  ← 无论上面结果如何，照常恢复历史
808      print("✅ 会话已恢复：{session_id}")
```

**没有任何分支会中止加载，也没有返回值告诉调用方检查结果。**
`load_session` 的签名是 `-> None`（`755`）。调用方拿不到 `config_check` / `tool_check`，只能去 scrape stdout。
`check_consistency=False` 时连 print 都没有。

**这是 fail-open。** 正确形态应是"检查不通过 → 抛异常，或返回带 `blocked=True` 的结构体"，
而不是"打两行字然后照常恢复"。

### 5.3 `run_as_subagent` 用的是"备份-覆盖-还原"，不是真隔离（`agent.py:880-988`）

它在**同一个 Agent 实例上**做：`original_history = ....copy()`(919) → `clear()`(924) →
跑任务(943) → `finally` 里 `clear()` + 逐条 append 回去(966-968)。
工具过滤同理：`_apply_tool_filter`(990-1021) **直接 `del self.tool_registry._tools[tool_name]`**(1019)，
把被删的塞进 `_temp_disabled_tools`(1016)，事后再塞回去(1034-1035)。

三个后果：

- **不可并发。** 两个子代理同时跑就会互相踩历史与注册表。`finally` 只保证单线程下能还原。
- **动的是别人的私有字段**：`tool_registry._tools`（`1018/1019/1035`）与
  `_temp_disabled_tools`（`1011-1016/1033-1038`）都是下划线开头的内部状态，
  由 `core/agent.py` 从外部改写。这是 §1.2 那条隐藏依赖边的具体形态。
- `KeyboardInterrupt` 被单独放行（`946-948` 先 `raise`），但 `finally` 仍会执行还原——这一处处理是对的。

`_get_subagent_metadata`（1040-1072）里的 `tokens` 是 **`总字符数 // 4`**（`1056-1057`），
`steps` 是 **assistant 消息条数**（`1053`）。两者都是估算，且与 `TokenCounter` 算出来的是两套数——
**又一处"一个事实两个来源"**。

### 5.4 三处 `provider=` 参数**根本不存在于被调用的构造函数里**

```
agent.py:490    HelloAgentsLLM(provider=provider, model=model, ...)                     ← _get_summary_llm
agent.py:1155   HelloAgentsLLM(provider=self.config.subagent_light_llm_provider, ...)   ← 死代码分支
agent.py:1267   HelloAgentsLLM(provider=self.config.subagent_light_llm_provider, ...)   ← _create_light_llm
```

`HelloAgentsLLM.__init__`（`llm.py:28-37`）的形参是
`model / api_key / base_url / temperature / max_tokens / timeout / **kwargs`——**没有 `provider`**。
`provider=` 因此落进 `**kwargs`，被 `llm.py:59` 存进 `self.kwargs`，**此后再无人读取**。

于是 `Config` 的三个 provider 字段全是死配置：

```
config.py:12  default_provider             → grep 全包，除定义行外 0 处使用
config.py:30  summary_llm_provider         → 只在 agent.py:486/490 被读出来，然后进 **kwargs 黑洞
config.py:67  subagent_light_llm_provider  → 只在 agent.py:1155/1267 被读出来，同上
```

更实质的问题：这三处**都没有传 `api_key` 与 `base_url`**，`HelloAgentsLLM` 会退回读环境变量
（`llm.py:53-54`）。**主 Agent 用显式 api_key 构造时，摘要 LLM 与轻量子代理 LLM 会去读环境变量，
读不到就抛 `HelloAgentsException`**（`llm.py:64-65`）——在 `_get_summary_llm` 这条路上，
该异常被 `agent.py:452` 吞掉，**静默退回简单摘要**，用户只看到一行 `⚠️ 智能摘要生成失败`。

### 5.5 `working_dir` 同样不存在

`agent.py:1225` 与 `1245`：`str(self.working_dir) if hasattr(self, 'working_dir') else "."`。
`grep -rn 'working_dir' hello_agents/core/ hello_agents/agents/` → **只有这两行**，
`Agent` 与四个子类都没有 `working_dir` 属性（有该属性的是 `tools/builtin/file_tools.py` 里的工具类，
`file_tools.py:63/298/446`）。
**`TodoWriteTool` 与 `DevLogTool` 的 `project_root` 恒为 `"."`**，即进程 cwd。

---

## 6. `hello_agents/agents/` —— 四个范式与工厂

### 6.1 `agents/__init__.py`（24 行，全文）

四个 Agent + 两个工厂函数（`3-9`），一个向后兼容别名 `PlanAndSolveAgent = PlanSolveAgent`（`12`）。
`__all__`（14-24）导出 7 个名字。零逻辑。

### 6.2 `agents/factory.py`（184 行，全文）—— 第二个"没有注册表的注册表"

`create_agent`（15-88）与 `create_adapter`（§3.1）是同一个模式：**`if/elif` 字符串比对，四个分支写死**。
`grep -n 'register\|REGISTRY' hello_agents/agents/factory.py` → **0 命中**。加第五种范式必须改这个文件。

**但它比 `create_adapter` 好一点：兜底分支是 `raise ValueError`**（`factory.py:84-88`），不是静默默认。
这是全仓库为数不多的 fail-fast 点之一（另一处是 `llm.py:62-67`）。

**三处仍然静默的地方：**

1. **`SimpleAgent` 分支不传 `tool_registry`**（`factory.py:75-82`）。
   另外三个分支（`47-53` / `57-63` / `67-73`）都传了。
   `create_agent("simple", ..., tool_registry=my_registry)` 会**静默丢掉工具注册表**，
   拿到一个没有工具的 Agent，没有警告。（`SimpleAgent.__init__` 明明接受 `tool_registry`，见 `simple_agent.py:31`。）
2. **`_get_system_prompt_for_type`（135-183）对未知类型静默回退**：
   `return prompts.get(agent_type.lower(), prompts["simple"])`（`183`）。
   在 `default_subagent_factory` 里它先于 `create_agent` 被调用（`116` vs `119`），
   所以未知类型最终还是会在 `create_agent` 撞上 `ValueError`——**这次运气好，顺序救了它**。
   但这个函数单独被复用时就是个静默默认。
3. `default_subagent_factory:129-130` 用 `if hasattr(subagent,'max_steps')` 决定要不要设 `subagent_max_steps`——
   `SimpleAgent` 没有 `max_steps`，于是 `config.subagent_max_steps` 对 simple 子代理**静默无效**。

### 6.3 工具重名怎么处理：**`print` 一行警告，然后覆盖。全程不 raise**

（`tools/registry.py` 属另一份精读的范围，此处只作为"注册与冲突"这一问的**事实核查**引用，不作实现评价。）

```
tools/registry.py:44-46   子工具重名  →  print("⚠️ 警告：工具 '{name}' 已存在，将被覆盖。") ; self._tools[name] = sub_tool
tools/registry.py:51-54   普通工具重名 →  print(同上)                                       ; self._tools[name] = tool
tools/registry.py:103-106 函数工具重名 →  print(同上)                                       ; self._functions[name] = {...}
```

`grep -c 'raise' hello_agents/tools/registry.py` → **0**。**整个注册表没有任何一条 `raise`。**

两个衍生问题：

- **`_tools` 与 `_functions` 是两个互不相干的命名空间**（`registry.py:44/51` vs `103`）。
  一个 Tool 对象叫 `"query"`、一个函数工具也叫 `"query"`，**两边都不会告警**。
  执行时 `agent.py:665` 先查 `get_tool` → Tool 胜出，函数工具被静默遮蔽。
- `SimpleAgent.remove_tool`（`simple_agent.py:315-319`）调的是 `self.tool_registry.unregister_tool(...)`，
  **而 `ToolRegistry` 上的方法叫 `unregister`（`registry.py:112`）**。
  `grep -rn 'unregister_tool' hello_agents/` → **只有 `simple_agent.py:318` 这一处调用，没有任何定义**。
  即 **`SimpleAgent.remove_tool()` 一调就 `AttributeError`**。这个方法从未被测试覆盖（见 §7）。

### 6.4 `SimpleAgent`（`agents/simple_agent.py`，436 行，全文）

结构：`run`(58-268) / `_build_messages`(270-294) / `add_tool`(296-313) / `remove_tool`(315-319) /
`list_tools`(321) / `has_tools`(327) / `stream_run`(331-361) / `arun_stream`(363-436)。

**(a) `status` 恒为 `"success"` —— trace 会为失败的执行写下"成功"。**

`simple_agent.py:116` 与 `263` 两处 `"status": "success"` 都是**字面量**，没有任何分支能让它变成别的值。
`grep -rn '"status": "success"' hello_agents/agents/` 全包 **8 处**（`simple_agent.py:116/263`、
`react_agent.py:233/297/320/614/670/796`），**没有一处出现过 `"status": "fail"` 或 `"error"`**
（`grep -rn '"status": "fail\|"status": "error' hello_agents/agents/` → 0 命中）。

具体的撒谎路径：LLM 调用抛异常 → `142-150` 打印 + 记 `error` 事件 + **`break`** →
跳到 `246`，此时 `current_iteration=1 < max_tool_iterations=3`，条件 `current_iteration >= max` 为 False →
**`final_response` 保持空字符串 `""`** → `252-253` 把空串当 assistant 消息写进历史 →
`255-266` 记 `session_end` 且 **`"status": "success"`** → `268` **`return ""`**。

**调用方拿到的是一个空字符串，trace 里写着 success，历史里多了一条空的 assistant 消息。**
D-003 说的"给不出证据链就算失败，不算降级成功"——这里是教科书级的反例。

**(b) 拒答被伪造成一句中文。** `simple_agent.py:176`：

```python
final_response = response.content or "抱歉，我无法回答这个问题。"
```

模型返回 `content=None`（工具调用轮次里很常见）时，框架**自己编了一句拒答**塞给用户，
与模型真的说了这句话**在返回值层面完全无法区分**——都是同一个 `str`。

**(c) 两个 TraceLogger 实例，两份 trace。**
基类 `__init__` 已经建了 `self.trace_logger` 并写了一条 `session_start`（`agent.py:72-87`），
`SimpleAgent.run` **又建了一个局部 `trace_logger`**（`simple_agent.py:75-88`），注释说是"避免多轮对话时文件已关闭"。
后果：`self.trace_logger` 那份**只有一条 `session_start`，永远不会 `finalize()`**；
`_emit_event` 的钩子超时/异常记录（`agent.py:287/294`）写进的是**基类那份**，
而 run 期间的所有业务事件写进的是**局部那份**。**同一次执行的证据被劈成两个文件，且互不引用。**

**(d) `arun_stream` 的返回类型与基类不一致（LSP 违反，静态可查）。**

```
core/agent.py:220        async def arun_stream(...) -> AsyncGenerator[AgentEvent, None]
simple_agent.py:370      async def arun_stream(...) -> AsyncGenerator[StreamEvent, None]
```

四个子类全部这样写。这是 §2.8"两套事件系统"在类型签名上的落地：
**基类承诺 `AgentEvent`，所有实现返回 `StreamEvent`，两者没有继承关系也没有转换函数。**
按基类类型注解写的消费方（比如判断 `event.type == EventType.AGENT_FINISH`）会**永远匹配不上**——
拿到的是 `StreamEventType.AGENT_FINISH`，两个 Enum 成员不相等。

**(e) `_build_messages` 丢掉 `tool_calls`。** `270-294` 只取 `msg.role` 与 `msg.content`，
而 `Message` 本身也没有 `tool_calls` 字段（`core/message.py:12-15` 四个字段）。
跨轮次的工具调用轨迹**不在历史里**——只在单次 `run` 的局部 `messages` 列表里（`180-194`），函数返回即丢。
这解释了为什么 `agent.py:1087` 的 `hasattr(msg,'tool_calls')` 恒为 False，
`_extract_tools_from_history` 实际只能靠正则抓 ReAct 格式的 `Action: xxx[`（`agent.py:1093-1096`）。

**(f) `add_tool` 会在 `tool_registry` 为空时凭空造一个**（`306-309`），
同时把 `self.enable_tool_calling` 改成 `True`——**构造时显式传 `enable_tool_calling=False` 的意图被静默推翻**。

### 6.5 `ReflectionAgent`（`agents/reflection_agent.py`，453 行，全文）

**(a) `arun_stream` 调用了两个全仓库不存在的方法 —— 这条路一进反思循环就 `AttributeError`。**

```
reflection_agent.py:374   reflection_prompt = self._build_reflection_prompt(input_text, current_response)
reflection_agent.py:405   refinement_prompt = self._build_refinement_prompt(input_text, current_response, reflection)
```

`grep -rn '_build_reflection_prompt\|_build_refinement_prompt' hello_agents/ tests/ examples/ --include=*.py`
→ **只有上面这 2 处调用，0 处定义**（`grep -c 'def _build_reflection_prompt\|def _build_refinement_prompt'` → 0）。
本类实际定义的是 `_reflect_on_result`(166) 与 `_refine_result`(183)，名字对不上。
基类 `Agent` 也没有这两个方法（`agent.py` 的 39 个方法名里没有）。

**后果：`ReflectionAgent.arun_stream()` 在第一次反思时抛 `AttributeError`**，
被 `445` 的 `except Exception` 接住 → 发一个 `ERROR` 事件 → `453` re-raise。
文档里标为"真正的流式执行"（`301` 行 docstring）的那条路，**从未被执行过**。
这同时证明它**没有任何测试覆盖**（见 §7）。

**(b) 同步与异步两条路的停止条件不同。**

- `run`（108-156）在每轮反思后检查 `if "无需改进" in feedback or "no need for improvement" in feedback.lower()`（`140`）→ `break`。
- `arun_stream`（364-431）**完全没有这个检查**，无条件跑满 `max_iterations` 轮。

即：同一个 Agent，同步调用可能 1 轮结束，异步调用一定 3 轮，**成本与结果都不同**。

`140` 行的停止条件本身也脆：**中文子串匹配**。反思文本里出现「这份回答并非无需改进」同样会命中并停止。
`grep -n '无需改进' hello_agents/` 命中 3 处：`93`（写进默认 prompt 的约定）、`140`（判定）、`179`（复述给模型）——
约定与判定分散在三处字符串字面量里，没有常量。

**(c) `Memory`（17-44）是框架里的第三套状态存储。**

已有 `history_manager`（基类）与 `_session_metadata`（基类），这里再加一个 `self.memory`。
它在每次 `run` 开头被**整体丢弃重建**（`122` `self.memory = Memory()`）。
`grep -rn 'self.memory' hello_agents/agents/reflection_agent.py` → `104/122/127/135/137/147/149`，
**全部在内存里，没有一处落盘**。

于是"反思轨迹"——恰恰是这个 Agent 唯一的差异化产物——**不进会话文件，不进 trace，`run` 返回后即消失**。
落进 history 的只有 `input_text` 与最终结果两条（`153-154`）。
**要复核"它为什么改了这一版"，事后没有任何材料。**

**(d) `_get_llm_response` 在 LLM 失败时返回空串。**
`232-234` 捕获异常 → print → `break` → 落到 `286` 的 `if current_iteration >= self.max_tool_iterations` 判为 False
→ `290` `return ""`。与 `SimpleAgent` §6.4(a) 是同一个模式。

**(e) `arun_stream` 的反思/优化两次调用丢掉了 system_prompt。**
`375` `reflection_messages = [{"role":"user", ...}]`、`410` `refinement_messages = [{"role":"user", ...}]`，
都没带 `self.system_prompt`（对比同步路径 `169` / `186` 都带了）。

### 6.6 `PlanSolveAgent`（`agents/plan_solve_agent.py`，546 行，全文）

三个类：`Planner`(16-87) / `Executor`(89-260) / `PlanSolveAgent`(262-546)。

**(a) 每执行一个计划步骤，就 `new` 一个完整的 `SimpleAgent` —— 副作用被复制 N 次。**

```
plan_solve_agent.py:181-188
    from .simple_agent import SimpleAgent
    # 临时创建一个 SimpleAgent 实例来复用工具调用逻辑
    temp_agent = SimpleAgent(name="temp_executor", llm=self.llm_client, tool_registry=self.tool_registry)
    tool_schemas = temp_agent._build_tool_schemas()
```

这段在 `_execute_step` 里，而 `_execute_step` 被 `execute` 的 for 循环逐步调用（`142`）。
**N 步计划 = N 次 `Agent.__init__`（`agent.py:32-131`）**，每次都会：

- 新建一个 `TraceLogger` 并写一条 `session_start`（`agent.py:73-87`）——**N 份互不相干的 trace 会话**；
- 新建 `SkillLoader` / `SessionStore` / `HistoryManager` / `TokenCounter`；
- **往传进来的同一个 `tool_registry` 重复注册 SkillTool / TaskTool / TodoWriteTool / DevLogTool**
  （`agent.py:102 / 123 / 127 / 131`）。第二步开始，每次注册都会撞上 `registry.py:52` 的
  `print("⚠️ 警告：工具 'x' 已存在，将被覆盖。")`——**用重名覆盖告警刷屏，而这本来是一个真警报**。

注释写的是"复用工具调用逻辑"。它真正需要的只有两个基类方法（`_build_tool_schemas` / `_execute_tool_call`），
**却为此付出了整个 Agent 的构造副作用**。这是 §3.6"基类超载"的直接代价：
基类太重，导致任何想借一个方法的人都得吞下 8 个子系统的初始化。

**(b) 同步路径与异步路径是两个不同的算法。**

| | `run`（320-353） | `arun_stream`（355-546） |
|---|---|---|
| 执行器 | `self.executor.execute(...)`（有工具调用） | **完全不用 executor**，逐步 `self.llm.astream_invoke`（`470`），**无工具** |
| system_prompt | `Executor.system_prompt`（`171`） | **无**，只有 `{"role":"user"}`（`466`） |
| 最终答案 | **最后一步的结果**（`145` `final_answer = response_text`） | **额外一次汇总调用**（`504-514`） |

**同一个问题，`run()` 与 `arun_stream()` 会给出机制上不同的答案，且带不带工具都不一样。**
从"可审计"的角度看，这意味着**答案取决于调用方用了哪个入口，而这件事不在任何证据里**。

**(c) 计划生成失败 → 一句中文字符串，无机读标记。**

`Planner.plan` 在两条失败路径上都 `return []`：模型没返回工具调用（`82-83`）、异常（`85-87`）。
`PlanSolveAgent.run` 看到空计划就 `final_answer = "无法生成有效的行动计划，任务终止。"`（`336`）并**正常 return**（`343`）。

这是全框架**最接近"拒答"的一处实现**——而它的形态是：一个和正常答案同型的 `str`，
写进 history 当作 assistant 消息（`341`），调用方无法用 `if` 判断这是拒答还是答案。

异步路径更糟：`401-419` **先发 `ERROR` 事件，紧接着又发 `AGENT_FINISH` 且 `result=error_msg`**。
只看 `AGENT_FINISH` 的下游会认为任务成功完成，拿到的"结果"其实是错误文案。

**(d) `Executor.execute` 的 `history` 是第四套局部状态**（`119`），
只在 `execute` 调用栈内存活（`144` append，`134` 用于拼 prompt），**函数返回即丢**。
每一步的中间结果不进 `history_manager`，不进会话文件。
Plan-Solve 的中间产物与 Reflection 的反思轨迹一样，**都不可事后复核**。

### 6.7 `ReActAgent`（`agents/react_agent.py`，1241 行，全文）—— 三条互不等价的执行路径

它是唯一 import `tools/` 的 Agent（`react_agent.py:13-15` → `registry` / `response` / `errors`，模块顶层）。
三个入口：`run`(91) → `_run_impl`(136)、`arun`(483)、`arun_stream`(876)。
**这三条路的工具执行语义、终止语义、证据记录全都不一样。**

**(a) `arun_stream` 每一步调用 LLM 两次，用户看到的推理与实际执行的动作来自两次不同的采样。**

```
946-961   async for chunk in self.llm.astream_invoke(messages, **kwargs):   ← 第 1 次：流式，文本被 yield 给用户
977-979   # 注意：流式输出后需要重新调用 LLM 获取 tool_calls
          # 这里简化处理：使用非流式调用获取工具调用
980-986   response = self.llm.invoke_with_tools(messages=messages, tools=tool_schemas, ...)  ← 第 2 次：非流式
988       tool_calls = response.tool_calls                                  ← 真正被执行的决策来自第 2 次
```

注释自己承认了这是"简化处理"。三个后果：

1. **每步 2× token、2× 延迟。**
2. **两次采样相互独立。** `temperature > 0` 时，用户在屏幕上读到的那段推理（`full_response`）
   与框架实际去执行的工具调用（`response.tool_calls`）**没有因果关系**。
   `992` 行甚至会把第一次的 `full_response` 当成最终答案返回（`response.content or full_response or "抱歉…"`）。
   **对一个要"可审计"的系统，这是致命形态：展示给人看的理由，不是产生动作的那个理由。**
3. `981` 是**同步阻塞调用写在 async 生成器里**，会卡住事件循环——`arun` 用的是 `ainvoke_with_tools`（`552`），
   这里退回了同步版。

**(b) 同步路径与异步路径的工具执行是两套代码，四项语义不一致。**

| | 同步 `_run_impl`（走基类 `_execute_tool_call`，`agent.py:647`） | 异步 `_execute_tools_async`(732) / `_execute_tools_async_stream`(1125) |
|---|---|---|
| 观测截断 | **不截断** | 截断（`843-847` / `1220-1224`） |
| 函数工具（`registry._functions`） | 支持（`agent.py:684`） | **不支持**，只查 `get_tool`（`834` / `1211`），落到 `"❌ 工具 x 不存在"` |
| 参数类型转换 | 做（`agent.py:668` → `_convert_parameter_types`） | **不做** |
| `ToolStatus` | 读了，转成 `❌ 错误 [code]:` / `⚠️ 部分成功:` 前缀（`agent.py:673-677`） | **完全忽略**，只取 `tool_response.text`（`840` / `1217`） |

证据：`grep -rn 'self.truncator' hello_agents/core/ hello_agents/agents/` → 构造在 `agent.py:57`，
**使用只有 `react_agent.py:843` 与 `1220` 两处**。
即 `Config` 的 `tool_output_max_lines` / `tool_output_max_bytes` / `tool_output_truncate_direction` /
`tool_output_dir` 四个字段，**对 SimpleAgent、ReflectionAgent、PlanSolveAgent 以及 ReActAgent 的同步路径完全无效**。
同理 `grep -rn 'get_function' hello_agents/core/ hello_agents/agents/` → **只有 `agent.py:684` 一处**。

**(c) 框架靠"字符串是不是以 ❌ 开头"来判断工具失败。**

```
react_agent.py:353    if result.startswith("❌"):
react_agent.py:863    if result_content.startswith("❌"):
react_agent.py:1228   if result_content.startswith("❌"):
```

这是 §4.3 第 3 条的直接证据：**结构化的 `ToolStatus` 在 `agent.py:673-677` 被拍成带 emoji 前缀的字符串之后，
下游只能靠嗅 emoji 把它认回来。** 工具自己返回一段以 ❌ 开头的正常文本，就会被误判为失败。
反过来，异步路径根本没读过 `ToolStatus`，一个 `status=ERROR` 但 `text` 不以 ❌ 开头的工具响应，
在异步路径里会被当成**成功的观测**喂给模型。

**(d) `arun_stream` 的 Finish 解析用了硬编码下标 `[0]`，外加一个裸 `except:`。**

```
1051  if tool_name == "Finish":
1052      try:
1053          args = json.loads(tool_calls[0].arguments)     ← 恒取第 0 个 tool_call
1054          final_answer = args.get("answer", result_dict["content"])
1055      except:                                            ← 全包 3 个裸 except 之一
1056          final_answer = result_dict["content"]
```

这段在 `for tool_name, tool_call_id, result_dict in tool_results:`（`1034`）循环体内。
**当 Finish 不是第一个工具调用时，它解析的是别的工具的参数**，`args.get("answer")` 取不到 →
回退到 `result_dict["content"]`。
而 `_execute_tools_async_stream` 给 Finish 的 content 是 `answer` 本身（`1177`），**这次侥幸是对的**；
但同一个 Agent 的 `arun` 路径走的是 `_handle_builtin_tool`，那里 content 是 `f"最终答案: {answer}"`（`471`）——
**同一段兜底逻辑在两条路径下会产出带前缀和不带前缀的两种最终答案**。

`1055` 的裸 `except:` 还会吞掉 `KeyboardInterrupt`。

**(e) `_execute_tools_async`(732-874) 与 `_execute_tools_async_stream`(1125-1239) 是近乎逐行重复的两份代码**，
差异只在内置工具的处理：前者调 `_handle_builtin_tool`(786)，后者**把逻辑内联重写**(1170-1179)，
且产出的文本不同：

```
_handle_builtin_tool:465    Thought → "推理: {reasoning}"          Finish → "最终答案: {answer}"（带前缀）
react_agent.py:1173         Thought → "已记录推理过程: {reasoning}"   Finish → "{answer}"（不带前缀）
```

后者返回的 dict **没有 `finished` 键**，这正是 `1051` 不得不去重新解析 `tool_calls[0]` 的原因。

**(f) LLM 调用失败被记录成 `"timeout"`。**
同步 `_run_impl:181-189` 与异步 `arun:558-566` 在 LLM 异常时都是 `break`，
`break` 之后落到"达到最大步数"的收尾块（`365-387` / `692-721`），
于是 trace 里写的是 `"status": "timeout"`（`382` / `716`），返回的是
`"抱歉，我无法在限定步数内完成这个任务。"`——**明明是 API 报错，证据里记成"步数用尽"。**

全仓库 `"status"` 字面量共 10 处，只有两个取值：
`"success"` 8 处（`react_agent.py:233/297/320/614/670/796`、`simple_agent.py:116/263`）与
`"timeout"` 2 处（`react_agent.py:382/716`）。
**`grep -rn '"status": "fail\|"status": "error' hello_agents/agents/` → 0 命中：没有任何一条路径会写下"失败"。**

**(g) `AGENT_FINISH` 事件的 payload schema 不稳定。**
`arun` 在超步时发 `_emit_event(EventType.AGENT_FINISH, on_finish, ..., status="timeout")`（`699-706`），
而正常结束的两处（`598-604` / `654-660`）**没有 `status` 键**。
`AgentEvent.data` 是无 schema 的 `Dict[str, Any]`（§2.7），
所以消费方要判断"这次是不是真的成功"，必须写 `event.data.get("status") != "timeout"` 这种依赖缺省语义的代码。

**(h) `_build_messages` 不带历史**（`389-406`：只有 system + 当前 user）。
对比 `SimpleAgent._build_messages`（`simple_agent.py:282` 遍历 `self._history`）。
**ReAct 在 prompt 层面是无状态的**，尽管它照样往 `history_manager` 里写（`222-223` 等）。
于是同一个 ReActAgent 连问两次，第二次看不到第一次——但会话文件里两轮都在。

**(i) `arun` 里的 Finish 早退会丢弃已执行工具的结果。**
`646-675` 遍历 `tool_results`，一旦遇到 `Finish` 就 `return`（`675`）。
`_execute_tools_async` 是先把**全部**工具并行跑完再返回结果列表（`871-872`），
且内置工具排在用户工具前面（`802` vs `872`）。
所以：**用户工具已经真的执行了（副作用已发生、钱已花），它们的结果却既不进 `messages` 也不进任何返回值。**

**(j) `run` 的异常兜底会写出一份"错误现场"会话，但写的是同一个固定文件名。**
`114-134`：`KeyboardInterrupt` → `save_session("session-interrupted")`；
其他异常 → `save_session("session-error")`。
`SessionStore.save` 用 `session_name` 直接当文件名（`session_store.py:96-99`），
**同名即覆盖**——同一个进程里第二次出错会覆盖第一次的错误现场。
`121-122` 与 `132-133` 这两层嵌套的 `except` 让"保存失败"也只 print 不抛。
