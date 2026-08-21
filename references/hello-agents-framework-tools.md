# hello-agents 框架源码精读 —— tools / context / observability / skills

> **本轮读的是框架源码，不是书稿。** 此前四轮读的全部是书稿正文，
> `hello_agents/` 包内的实现代码在本项目历次记录中**一行都没有被读过**。

## 钉死的版本坐标

| 项 | 值 |
|---|---|
| 仓库 | `github.com/jjyaoao/helloagents` |
| commit | **`5432566d01ea1c2095c4a717fe2a010aa1c3b0bd`（短 `5432566`）** |
| 提交时间 | 2026-06-08 13:35:39 +1000 |
| 提交信息 | `docs: update AtomGit mirror URL` |
| `__version__` | **`1.0.0`** |
| 语料位置 | 本会话 scratchpad 临时 clone，**会话结束即消失**；后续复核需重新 clone 并 `git checkout 5432566` |

**版本差声明（重要）：** 书稿各章钉的是旧 tag —— Ch10 钉 `V0.2.2`、Ch12 钉 `V0.2.7` 等，
仓库共有 12 个 tag。本文档读的是 **HEAD = 1.0.0**。
凡本文档指出的实现问题，**只对 1.0.0 成立**，不得用来指摘书稿里 0.2.x 的写法；
凡与书稿结论冲突处，正文中逐条注明「书稿版本 vs 1.0.0」。

## 分工声明

本轮由两个 agent 并行读。**本文档只覆盖下面覆盖表列出的范围**，
`hello_agents/core/` 与 `hello_agents/agents/` 由另一 agent 负责，本文档不做完整评估。
唯一例外：为确定 trace 事件的字段形状，对 `core/agent.py` 与 `agents/react_agent.py`
的 `log_event(` 调用点做了**定点 grep 摘录**（不是通读），文中已标注。

---

## 覆盖表

| 文件 | 行数 | 读到什么程度 |
|---|---|---|
| `hello_agents/observability/__init__.py` | 11 | **全文** |
| `hello_agents/observability/trace_logger.py` | 536 | **全文（逐行）** |
| `hello_agents/tools/__init__.py` | 53 | **全文** |
| `hello_agents/tools/base.py` | 453 | **全文（逐行）** |
| `hello_agents/tools/registry.py` | 291 | **全文（逐行）** |
| `hello_agents/tools/response.py` | 164 | **全文** |
| `hello_agents/tools/errors.py` | 54 | **全文** |
| `hello_agents/tools/circuit_breaker.py` | 168 | **全文** |
| `hello_agents/tools/tool_filter.py` | 147 | **全文** |
| `hello_agents/tools/builtin/__init__.py` | 36 | **全文** |
| `hello_agents/tools/builtin/calculator.py` | 156 | **全文** |
| `hello_agents/tools/builtin/file_tools.py` | 762 | **全文（逐行）** |
| `hello_agents/tools/builtin/devlog_tool.py` | 450 | **全文** |
| `hello_agents/tools/builtin/skill_tool.py` | 173 | **全文** |
| `hello_agents/tools/builtin/task_tool.py` | 186 | **全文** |
| `hello_agents/tools/builtin/todowrite_tool.py` | 387 | **全文** |
| `hello_agents/context/__init__.py` | 26 | **全文** |
| `hello_agents/context/builder.py` | 307 | **全文（逐行）** |
| `hello_agents/context/history.py` | 168 | **全文** |
| `hello_agents/context/token_counter.py` | 162 | **全文** |
| `hello_agents/context/truncator.py` | 183 | **全文（逐行）** |
| `hello_agents/skills/__init__.py` | 27 | **全文** |
| `hello_agents/skills/loader.py` | 225 | **全文（逐行）** |
| `tests/test_observability.py` | 199 | **全文** |
| `tests/test_trace_integration.py` | 108 | **全文** |
| `examples/observability_demo.py` | 229 | **全文** |

> 本表在写作过程中随进度更新；文末「仍未读清单」列出明确没读到的部分。

---

# 一、`observability/`（547 行）—— 本轮重点

## 1.1 结论先行

**它是日志，不是证据链。** 从审计角度看，这 547 行提供的是「执行过程的人类可读回放视图」，
不是「可独立复核的证据」。差距不是实现质量问题，是**设计目标不同**：
它要回答「Agent 刚才干了什么」，本项目要回答「这个答案凭什么成立」。

具体缺什么见 §1.6。**作为反面对照物它的价值极高** —— 它把「看起来很像审计」
和「真的能审计」之间那条线画得非常清楚：有时间戳、有事件流、有 HTML 面板、有脱敏、
有统计，**唯独没有任何一样东西能让第三方在不信任本次运行的前提下重新验证结论**。

## 1.2 模块结构

只有一个类。`observability/__init__.py` 11 行全是 re-export：

- `observability/__init__.py:8` — `from .trace_logger import TraceLogger`
- `observability/__init__.py:10` — `__all__ = ["TraceLogger"]`

**它没有被 top-level `__init__.py` 导出。**
验证：`grep -n "observability" hello_agents/__init__.py` → **0 命中**。
必须写 `from hello_agents.observability import TraceLogger`。

## 1.3 记录什么：事件形状

事件对象在 `trace_logger.py:97-103` 构造，**只有 5 个顶层字段**：

```python
event_obj = {
    "ts": datetime.now().isoformat(),   # :98
    "session_id": self.session_id,      # :99
    "step": step,                       # :100  ReAct 步号，可为 None
    "event": event,                     # :101  事件类型字符串
    "payload": payload                  # :102  完全自由的 dict
}
```

**`event` 与 `payload` 都没有 schema。** `log_event` 签名是
`event: str, payload: Dict[str, Any], step: Optional[int]`（`trace_logger.py:83-88`）。
事件类型是裸字符串，payload 是任意 dict。没有枚举、没有 TypedDict、没有 pydantic 模型。
验证：`grep -rn "class.*Event\|EventType\|TypedDict" hello_agents/observability/` → **0 命中**。

后果：**消费端只能靠字符串字面量硬编码**。`_compute_stats`（`:184-238`）正是这样：
`event["event"] == "session_start"`（:205）、`== "session_end"`（:208）、
`== "model_output"`（:215）、`== "tool_call"`（:222）、`== "error"`（:227）。
生产端改了字符串，统计静默归零，没有任何地方会报错。

### 实际被写入的事件类型（定点 grep `core/` 与 `agents/` 的调用点）

| 事件 | 写入位置 | payload 字段 |
|---|---|---|
| `session_start` | `core/agent.py:80-87` | `agent_name` / `agent_type` / `config`（**整个 `config.model_dump()`**） |
| `message_written` | `agents/react_agent.py:159-162`、`:532-535` | `role` / `content` |
| `model_output` | `react_agent.py:201-212`、`:575-586` | `content` / `tool_calls`(数量) / `usage.total_tokens` / `usage.cost` |
| `tool_call` | `react_agent.py:275-283` | `tool_name` / `tool_call_id` / `args` |
| `tool_result` | `react_agent.py:292-301`、`:342-350` | `tool_name` / `tool_call_id` / `status` / `result` |
| `session_end` | `react_agent.py:227-235`、`:314-322`、`:376-384` 等 | `duration` / `total_steps` / `final_answer` / `status` |
| `error` | `react_agent.py:184-188` | `error_type` / `message` |
| `hook_timeout` / `hook_error` | `core/agent.py:288-291`、`:295-298` | `event_type` / `timeout` 或 `error` |

**这张表里没有的东西**：没有 `model_input`。
验证：`grep -rn "model_input" --include=*.py hello_agents/` → **0 命中**。

**送进模型的 prompt 从来不被记录。** 只记录模型吐出来的 `content`。
这是「不可重放」的第一个也是最根本的原因（见 §1.5）。

## 1.4 落盘：双写，且是真落盘

不是只打日志。构造函数里就把两个文件句柄打开了：

- `trace_logger.py:56` — `self.output_dir.mkdir(parents=True, exist_ok=True)`
- `trace_logger.py:59` — `self.jsonl_path = self.output_dir / f"trace-{self.session_id}.jsonl"`
- `trace_logger.py:62` — `self.jsonl_file = open(self.jsonl_path, 'w', encoding='utf-8')`
- `trace_logger.py:65` — `self.html_path = ... f"trace-{self.session_id}.html"`
- `trace_logger.py:68` — `self.html_file = open(self.html_path, 'w', encoding='utf-8')`
- `trace_logger.py:71` — 立刻写 HTML 头

每条事件**双写且立即 flush**：

- `trace_logger.py:113-114` — JSONL：`write(json.dumps(...) + "\n")` 然后 `flush()`
- `trace_logger.py:117` → `_write_html_event`，内部 `:434-435` 同样 `write` + `flush`

**这个设计值得借鉴**：HTML 是**增量写**的，不是 finalize 时一次性渲染。
进程崩了，已写出的事件仍在磁盘上，HTML 虽缺尾巴但浏览器照样能打开看前半截；
JSONL 因逐行 flush，是完整有效的。

session id 格式 `s-YYYYMMDD-HHMMSS-xxxx`，`_generate_session_id`（`:73-81`），
后 4 位取 `uuid4().hex[:4]`（`:80`）。16^4 的碰撞空间只在同秒内有风险，实际安全。
注意 id 里编码的是本地时间且**没有时区**（`datetime.now()`，`:79`）。

默认输出目录 `memory/traces`（`:34`），且 **trace 默认开启**：
`core/config.py:42` — `trace_enabled: bool = True`。

## 1.5 能不能重放：不能

`grep -rni "replay\|重放\|reproduc" --include=*.py hello_agents/` → **0 命中**。

不是「没实现重放功能」这么简单，而是**记录的字段根本不足以支撑重放**：

1. **没有 prompt。** 只有 `model_output.content`，没有 `model_input`（见 §1.3 grep 结果）。
   无法知道模型看到了什么。
2. **没有模型标识与采样参数。** `model_output` 的 payload 只有 `content` / `tool_calls` / `usage`
   （`react_agent.py:201-212`）。没有 model name、没有 temperature、没有 seed、没有 top_p。
   模型名只可能间接出现在 `session_start` 的 `config.model_dump()` 里，
   但那是 `Config` 默认值，不是本次调用的实参。
3. **没有任何哈希。** 全仓 `grep -rn "sha256\|hashlib" --include=*.py hello_agents/` → **3 命中**，
   全部与 trace 无关：`core/agent.py:852`、`core/agent.py:866`（工具 schema 指纹，
   `sha256(...).hexdigest()[:16]`）、`core/session_store.py:16`（import）。
   **`observability/` 内 0 命中。** trace 文件本身没有内容哈希，工具输出没有哈希，
   数据快照没有哈希 —— 无法证明这份 trace 没被改过，也无法证明两次运行读的是同一份数据。
4. **`tool_result` 记的是渲染后的字符串，不是结构化结果。**
   `react_agent.py:298` 写 `result['content']`，`:347` 写 `result`（已是 str）。
   工具的原始返回值（`ToolResponse` 对象，见 §2.4）在进 trace 之前已被拍平成给 LLM 看的文本。
   复核者拿到的是「模型看到的那句话」，不是「工具算出来的那个值」。
5. **没有工具版本 / 代码版本。** trace 里没有任何字段标识执行时的框架版本或工具实现版本。

结论：**这份 trace 能让人「看懂」一次运行，不能让人「重做」一次运行，
更不能让人「反驳」一次运行。**

## 1.6 够不上「证据」还缺什么（对照本项目 D-003）

本项目主张「证据链是第一类产物，不是日志」。把 TraceLogger 当靶子，缺口是七条：

| # | 缺口 | 在 1.0.0 中的具体表现 |
|---|---|---|
| E1 | **无完整性** | trace 文件、工具输入、工具输出都无哈希（`observability/` 内 `sha256` 0 命中）。任何人可事后编辑 JSONL，无从发现 |
| E2 | **无输入侧记录** | 无 `model_input`（0 命中）；`tool_call.args` 有记，但 prompt 没有 |
| E3 | **无确定性锚点** | 无 model name / temperature / seed / 框架版本字段 |
| E4 | **无数据溯源** | 没有「这个数字来自哪张表哪一行」的概念，`tool_result` 只有一个 `result` 字符串 |
| E5 | **无口径/依据** | 框架层完全没有「指标定义」「准则条款」这类概念 —— 这是领域缺口不是框架缺陷，但正是本项目差异点所在 |
| E6 | **原始产物被丢弃** | 工具输出在 `base.py` 层就可能被截断（见 §2.6），trace 记的是截断后的 |
| E7 | **无 schema，无法校验** | 事件与 payload 都是自由 dict（`:83-88`）。一份 trace 是否「完整」无法机器判定 |

**反过来，它做对的三件事，本项目应当直接抄：**

- **双格式**：机器可读 JSONL + 人类可读 HTML，同一份数据两个出口（`:59` / `:65`）。
  审计场景下「给系统看的」和「给人看的」必须都有。
- **流式增量落盘 + 逐条 flush**（`:113-114`、`:434-435`）：崩溃安全，运行中可实时查看。
- **`__exit__` 里把异常本身写成事件再 finalize**（`:517-534`）：
  异常路径不是「日志断掉」，而是「日志里多一条 error 事件」。
  `:533` `return False` 不抑制异常 —— 这是对的，可观测性不能吞异常。

## 1.7 失败时怎么办：不 fail-closed，但也没有静默 except

**好消息：`observability/` 里没有一个 `try/except`。**
验证：`grep -n "except" hello_agents/observability/trace_logger.py` → **0 命中**。
写盘失败会直接抛，不会假装记录成功。这点比预期好。

**坏消息：它没有 fail-closed 的概念，因为它从不阻断主流程。**
调用侧全部是 `if self.trace_logger:` 守卫（`react_agent.py:158`、`:183`、`:200`… 共 20 余处）。
trace 关掉，Agent 照常跑、照常出答案。这是日志的正确姿态，
**但对本项目是致命的**：本项目要求「给不出证据链 = 失败」，
所以证据写入必须在**答案返回路径上**，而不是旁路。

### finalize 的顺序问题（真实缺陷）

`finalize()`（`:162-182`）先 `_compute_stats()`（`:171`）→ 写 footer（`:174`）→ 关文件（`:177-178`）。
若进程在 finalize 之前被 kill：

- JSONL：**完整可用**（逐条 flush）
- HTML：**没有 `</body></html>`，没有统计面板** —— 内容在，结构不闭合

而 `_compute_stats` 是**从内存里的 `self._events`**（`:53`、`:110`）算的，不是从 JSONL 重算。
所以**没有任何离线工具能从一份完整的 JSONL 重新生成统计面板**。
统计逻辑与写入逻辑耦合在同一个对象的生命周期里。

> 对本项目的启示：**统计/汇总必须是 JSONL 的纯函数**，可离线重跑。
> 写成 `def compute_stats(events: Iterable[dict]) -> Stats` 的自由函数，
> 而不是绑在 logger 实例上的私有方法。

### `finalize()` 用 `print` 而不是 logging

`:180-182`：

```python
print(f"✅ Trace 已保存:")
print(f"   JSONL: {self.jsonl_path}")
print(f"   HTML:  {self.html_path}")
```

**无条件 print 到 stdout**，没有开关。库代码往 stdout 打字是污染，
在 SSE / pipe / 结构化输出场景会破坏下游。（全仓通病，见 §6。）

### 重复 finalize 会炸

`finalize()` 没有幂等保护。`react_agent.py` 里有 **6 处**调用
（`:236`、`:323`、`:385`、`:617`、`:673`、`:719`），分布在不同 return 分支上。
单次 run 只走一条，但**同一个 Agent 实例跑第二轮对话时 logger 已关闭**，
再 `log_event` 会 `ValueError: I/O operation on closed file`。

**框架自己知道这个坑并绕开了**，`agents/simple_agent.py:74-75` 有注释：

> `# 为每次 run 创建新的 TraceLogger（避免多轮对话时文件已关闭的问题）`

即 `SimpleAgent` 每次 `run()` 新建一个 TraceLogger（`simple_agent.py:77`），
而 `core/agent.py:74` 是在 `__init__` 里建的、`ReActAgent` 沿用。
**两个 Agent 对 trace 生命周期的处理不一致**：
`SimpleAgent` 一次 run 一个 trace 文件，`ReActAgent` 一个实例一个 trace 文件（且第二轮会炸）。

## 1.8 脱敏：正则四条，覆盖面窄

`_sanitize_event`（`:119-132`）→ `_sanitize_value`（`:134-160`）递归处理 str/dict/list。
`:127` 用 `copy.deepcopy` 先拷贝，**不污染调用方的 payload 对象** —— 这点做得对。

三条正则（`:146`、`:148`、`:150`）：

```python
value = re.sub(r'sk-[a-zA-Z0-9]+', 'sk-***', value)                      # :146
value = re.sub(r'Bearer\s+[a-zA-Z0-9_\-]+', 'Bearer ***', value)         # :148
value = re.sub(r'(/Users/|/home/|C:\\Users\\)[^/\\]+', r'\1***', value)  # :150
```

**漏的**：

- 非 `sk-` 前缀的 key（DeepSeek / 通义 / 智谱 / Azure 的格式各不相同）
- `sk-proj-...`、`sk_live_...`（下划线与第二个连字符不在 `[a-zA-Z0-9]+` 内，
  `sk-proj-ABC` 会变成 `sk-***-ABC`，**后半段泄漏**）
- 数据库连接串。`examples/observability_demo.py:103` 自己就放了
  `"postgresql://user:pass@localhost/db"` 进 payload，
  而同文件 `:116-119` 的断言**根本没检查它有没有被脱敏** —— 因为它不会被脱敏。
- Windows 路径只匹配 `C:\Users\`，`D:\` 或正斜杠形式的 `C:/Users/` 不匹配。
  demo `:102` 用的正是 `C:/Users/admin/...`，而 `:119` 的断言写成
  `assert "/Users/***/" in str(payload) or "C:/Users/***/project/config.py" in str(payload)`
  —— **用 `or` 兜住两种可能，说明作者自己也不确定哪条会命中**。

**脱敏发生在写盘前、进内存缓存前**（`:106-110`：先 sanitize，再 append 到 `_events`），
所以 `_compute_stats` 看到的也是脱敏后数据。顺序是对的。

## 1.9 HTML 生成：四个实打实的缺陷

### (1) 没有 HTML 转义 —— payload 可注入任意 HTML/JS

`:418` 序列化 payload：`payload_json = json.dumps(payload, indent=2, ensure_ascii=False)`
`:430` 直接插进 `<pre>{payload_json}</pre>`。

全仓验证：`grep -rn "html.escape" --include=*.py hello_agents/` → **0 命中**。

后果：任何工具返回的文本里带 `<script>` 或 `</pre>`，就会破坏 HTML 结构或执行脚本。
在本项目场景下这是**直接的安全与可信问题** —— 年报 PDF 抽出的文本、
网页抓取的内容进了 `tool_result`，trace HTML 就是一个 stored XSS 面板。
更要命的是：**审计报告如果能被被审计对象的内容篡改渲染，它就不是证据。**

同样未转义的还有 footer 里的错误列表：`:452`
`error_items += f"<li>Step {step}: <strong>{error_type}</strong> - {message}</li>\n"`
—— `message` 来自异常字符串，同样可控。

### (2) HTML 里的 `details_id` 依赖内存计数器

`:415` — `details_id = f"details-{len(self._events)}"`。
因为 `log_event` 里 `:110` 先 append 再 `:117` 渲染，id 从 1 开始且唯一。
**但这把 HTML 的正确性绑在了内存状态上** ——
任何「从 JSONL 重新渲染 HTML」的离线工具都必须复现这个计数逻辑。再次说明渲染与记录耦合。

### (3) `total_cost` 永远是 0（假指标）

`_compute_stats:218` — `stats["total_cost"] += usage.get("cost", 0.0)`
`_write_html_footer:476` — 面板上有一格「总成本 `${stats["total_cost"]:.4f}`」

但生产端写死了。`grep -rn '"cost"' --include=*.py hello_agents/` → **3 命中**：

- `agents/react_agent.py:208` — `"cost": 0.0`
- `agents/react_agent.py:582` — `"cost": 0.0`
- `observability/trace_logger.py:218` — 消费端

**真实运行时 `total_cost` 恒为 `$0.0000`。** 只有 `tests/test_observability.py:140`
和 `examples/observability_demo.py:201` 手工塞了 cost，测试才是绿的。

> 这正是本项目 `rules/failure-modes.md` 第 2 条要防的：
> **「只有真实字段能诚实触发时才声明」**。
> 这里 UI 上有一个永远显示 0 的成本统计，测试还给它盖了绿章。
> 一个永远不会正确触发的指标，比没有这个指标更糟 —— 它让人以为成本被监控着。

### (4) `html_include_raw_response` 是完全没接线的开关

`grep -rn "html_include_raw" --include=*.py hello_agents/` → **6 命中**：

- `core/config.py:45` — 配置项 `trace_html_include_raw_response: bool = False`
- `core/agent.py:77`、`agents/simple_agent.py:80` — 从 config 传进构造函数
- `trace_logger.py:36` — 构造函数形参
- `trace_logger.py:43` — docstring
- `trace_logger.py:47` — `self.html_include_raw = html_include_raw_response`

**`self.html_include_raw` 被赋值之后，全仓再也没有被读过一次。**
一个穿过三层（Config → Agent → TraceLogger）的死开关。
用户设 `True` 不会有任何效果，也不会有任何警告。

## 1.10 `_compute_stats` 的两个静默错误

`:211-212`：

```python
if event.get("step"):
    stats["total_steps"] = max(stats["total_steps"], event["step"])
```

用的是**真值判断**，`step=0` 会被当成没有 step。
框架自己的 ReAct 从 1 开始计数（`react_agent.py:167` `current_step += 1`），
所以现在不出错，但对外部调用者是陷阱 —— 应写 `is not None`。

`:216-217`：

```python
usage = event.get("payload", {}).get("usage", {})
stats["total_tokens"] += usage.get("total_tokens", 0)
```

**三层默认值兜底**。若 `model_output` 的 payload 结构变了（比如改名 `token_usage`），
统计静默变 0，没有任何 warning。典型的「默认值兜底掩盖数据缺失」。

## 1.11 文档与代码已经漂移

`grep -rn "core.observability" docs/` → **4 命中**，全部写的是

```python
from hello_agents.core.observability import TraceLogger
```

（`docs/function-calling-architecture.md:457`、`docs/logging-system-guide.md:20`、`:112`、`:277`）

而 `hello_agents/core/observability.py` **不存在**
（`ls hello_agents/core/` → `__init__.py agent.py config.py exceptions.py lifecycle.py llm.py
llm_adapters.py llm_response.py message.py session_store.py streaming.py`）。

正确路径是 `hello_agents.observability`。**照文档抄会 ImportError。**
`docs/observability-guide.md:112` 写对了，同一套文档里两种写法并存。

---
