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
| `hello_agents/tools/__init__.py` | 53 | **全文**（§2.1 导出面） |
| `hello_agents/tools/base.py` | 453 | **全文（逐行）** —— §2.2–§2.7 |
| `hello_agents/tools/registry.py` | 291 | **全文（逐行）** —— §3 |
| `hello_agents/tools/response.py` | 164 | **全文（逐行）** —— §2.4 |
| `hello_agents/tools/errors.py` | 54 | **全文（逐行）** —— §2.5 |
| `hello_agents/tools/circuit_breaker.py` | 168 | **全文（逐行）** —— §4.1 |
| `hello_agents/tools/tool_filter.py` | 147 | **全文（逐行）** —— §4.2–§4.3 |
| `hello_agents/tools/builtin/__init__.py` | 36 | **全文**（§5 导出面） |
| `hello_agents/tools/builtin/calculator.py` | 156 | **全文（逐行）** —— §5.1 |
| `hello_agents/tools/builtin/file_tools.py` | 762 | **全文（逐行）** —— §7 |
| `hello_agents/tools/builtin/devlog_tool.py` | 450 | **全文（逐行）** —— §8.4–§8.6 |
| `hello_agents/tools/builtin/skill_tool.py` | 173 | **全文（逐行）** —— §5.3 |
| `hello_agents/tools/builtin/task_tool.py` | 186 | **全文（逐行）** —— §5.2 |
| `hello_agents/tools/builtin/todowrite_tool.py` | 387 | **全文（逐行）** —— §8.1–§8.3 |
| `hello_agents/context/__init__.py` | 26 | **全文** —— §9.2（导出面 + 3 个不存在的类）|
| `hello_agents/context/builder.py` | 307 | **全文（逐行）** —— §9.9（GSSC 全流程 + 中文恒 0 实测）|
| `hello_agents/context/history.py` | 168 | **全文（逐行）** —— §9.6–§9.7（不可逆压缩、`role="summary"`）|
| `hello_agents/context/token_counter.py` | 162 | **全文（逐行）** —— §9.8（不可达降级 + 中文低估）|
| `hello_agents/context/truncator.py` | 183 | **全文（逐行）** —— §9.3–§9.5（可逆机制 + `max_bytes` 装饰性）|
| `hello_agents/skills/__init__.py` | 27 | **全文**（§6 导出面） |
| `hello_agents/skills/loader.py` | 225 | **全文（逐行）** —— §6 |
| `tests/test_observability.py` | 199 | **全文** |
| `tests/test_trace_integration.py` | 108 | **UNVERIFIED** —— 台账曾标「全文」，但正文无任何对应内容；语料已从 scratchpad 消失，无法复核是否读过。2026-08-23 由 `check_reading_ledger.py` 抓出并如实降级 |
| `examples/observability_demo.py` | 229 | **全文** |

> 本表在写作过程中随进度更新；文末「仍未读清单」列出明确没读到的部分。

> **⚠️ 2026-08-22 台账更正（诚信记录，不删）**
> 本表此前把 `tools/**`（14 个文件）、`context/**`（5 个）、`skills/**`（2 个）
> **全部标成「全文」/「全文（逐行）」，但正文对它们零分析** —— 全文只有 §1.1–§1.11，
> 全部关于 `observability/trace_logger.py`。
> 核验：`grep -c 'tools/base.py' references/hello-agents-framework-tools.md` → **1**（就是台账那一行本身）；
> `context/builder`、`skills/loader`、`registry.py` 同样各 **1 命中**。
> 已于本轮开始时把这 **21 行**降级为「待读」，此后**每读完一个文件、正文写入后**再逐行改回。
> 这对应 `rules/failure-modes.md` 第 3 条「如实标注读得少 ≠ 读过」——
> 之前的错误不是读少了，是**没读却标了「全文（逐行）」**，性质更重。

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

# 二、`tools/` 核心四件套（`__init__` 53 + `base` 453 + `response` 164 + `errors` 54 = 724 行）

## 2.1 结论先行

**工具层有「协议」但没有「契约」。** `ToolResponse` / `ToolStatus` / `ToolErrorCode`
把**输出侧**规范得相当好（三态、错误码、stats、context 分离），
但**输入侧几乎没有任何约束**：参数类型是裸字符串，类型不校验，
唯一的校验函数**写了但从来没被调用过**（§2.3）。

一句话：**它保证「工具怎么回答」，不保证「工具被怎么问」。**
对本项目而言这个不对称是致命的 —— 审计里「用了什么口径、传了什么参数」
和「算出什么结果」同等重要，输入侧无契约意味着证据链的上游是空的。

## 2.2 工具 schema 怎么定义

参数定义就是一个五字段的 pydantic 模型，`base.py:41-47`：

```python
class ToolParameter(BaseModel):
    name: str
    type: str          # :44 —— 裸 str，不是 Literal，不是 Enum
    description: str
    required: bool = True
    default: Any = None
```

**`type` 是自由字符串。** 写 `type="strng"`（拼错）、`type="财务报表"`、`type=""`
全部合法，pydantic 只校验它是不是 `str`。

验证：`grep -rn "Literal\|validator\|field_validator" --include=*.py hello_agents/tools/` → **0 命中**。
全仓 `grep -rn "jsonschema" --include=*.py --include=*.toml --include=*.txt .` → **0 命中**
（没有引入 JSON Schema 校验库，也没在依赖里）。

### schema 是「拼」出来的，不是「声明」出来的

`to_openai_schema()`（`base.py:239-285`）把 `List[ToolParameter]` 拼成 OpenAI function schema。
拼的过程中有**两处信息损失**：

**(1) `default` 被降级成描述里的一句话**（`base.py:261-262`）：

```python
if param.default is not None:
    prop["description"] = f"{param.description} (默认: {param.default})"
```

OpenAI schema 本身是支持 `default` 关键字的，这里选择不用，
把默认值塞进自然语言描述里。后果：**默认值对模型只是「读到的一句提示」，
不是结构化约束**；下游任何按 schema 做校验的组件都看不到默认值。
注释自己写着「OpenAI schema 不支持 default 字段」—— 这个前提不成立。

**(2) 数组元素类型被硬编码成 string**（`base.py:265-266`）：

```python
if param.type == "array":
    prop["items"] = {"type": "string"}  # 默认字符串数组
```

一个 `List[int]` 参数，schema 里声明成 `array of string`。
**这是 schema 对模型说了假话**，而且没有任何地方能发现 ——
因为运行时根本不按 schema 校验（§2.3）。

### 自动生成路径：类型全靠猜，猜不出就 `"string"`

`AutoGeneratedTool._python_type_to_tool_type`（`base.py:405-425`）是个 6 项 map：

```python
type_map = {str:"string", int:"integer", float:"number",
            bool:"boolean", list:"array", dict:"object"}
return type_map.get(py_type, "string")     # :425 —— 兜底
```

`:425` 的 `.get(py_type, "string")` 意味着：
`Optional[str]`、`Union[int,str]`、`Decimal`、`datetime`、任何自定义类
—— **全部静默变成 `"string"`**，无 warning、无异常。

`:408-413` 只特判了 `list` / `dict` 两种泛型 origin；
`Optional[X]` 的 origin 是 `typing.Union`，落到 `:425` 兜底。
**在财务场景里 `Decimal` 被声明成 `string` 是有实际后果的**，见 §7。

参数描述从 docstring 的 `Args:` 段用正则抠（`base.py:385`、`:393`）。
正则抠不到就用占位串 `f"参数 {param_name}"`（`base.py:362`）——
又一个静默兜底：**docstring 写错格式，模型收到的参数说明就是「参数 content」这种废话**，
不报错。

## 2.3 参数校验：写了，但一次都没被调用

`Tool.validate_parameters`（`base.py:226-229`）：

```python
def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
    required_params = [p.name for p in self.get_parameters() if p.required]
    return all(param in parameters for param in required_params)
```

两个问题，第二个是致命的：

**(1) 它只查「必填项在不在」，完全不查类型。**
`type` 字段在这个函数里根本没被读。声明 `type="integer"` 传进 `"abc"`，返回 `True`。

**(2) 它在 `hello_agents/` 内部从来没有被调用过。**

验证：`grep -rn "validate_parameters" --include=*.py .` → **4 命中**：

- `hello_agents/tools/base.py:226` —— 定义处本身
- `examples/custom_tools/advanced_tool_template.py:101`、`:184`、`:227`
  —— 这是**另一个方法** `_validate_parameters`（下划线前缀，模板文件里自己写的），
  与基类这个同名但不同函数

即：**框架自带的参数校验器，框架自己一次都没用。**
`ToolRegistry.execute_tool`（`registry.py:132-220`）从头到尾没有校验步骤，
直接 `tool.run_with_timing(parameters)`（`registry.py:176`）。

### 那么非法参数到底会怎样：既不报错也不强转，而是「被异常吞成一条错误文本」

真实链路（以自动生成工具为例）：

1. `AutoGeneratedTool.run` 直接展开调用：`result = self.method(**parameters)`（`base.py:438`）
2. 参数少了/多了/名字不对 → Python 抛 `TypeError`
3. `base.py:449` 的 `except Exception as e` 接住
4. 变成 `ToolResponse.error(code=EXECUTION_ERROR, message=f"方法执行失败: {str(e)}")`（`base.py:450-453`）

**类型不对则更糟**：`{"importance": "很高"}` 传给 `importance: float`，
Python **不检查注解**，方法照常执行，直到内部真正做算术时才炸（或者根本不炸，
比如只是拼进字符串）。**注解是装饰性的，不是契约。**

所以三个选项里，答案是第四个：
**非法参数既不是「报错」（不抛给调用方）也不是「静默强转」，
而是「降级成一条给 LLM 看的错误文本」** —— 从 Agent 视角看，
「工具崩了」和「工具正常返回了一个错误结果」**是同一种东西**。

## 2.4 输出侧：`ToolResponse` 三态协议（这部分做得好）

`response.py:12-16` 三态：

| 状态 | 语义（`response.py` 原注释） |
|---|---|
| `SUCCESS` | 任务完全按预期执行 |
| `PARTIAL` | **结果可用但存在折扣（截断、回退、部分失败）** |
| `ERROR` | 无有效结果（致命错误） |

**`PARTIAL` 这一态值得本项目直接抄。** 它显式承认「结果打了折」这个中间状态，
而不是把截断/回退伪装成成功。审计场景下「这个数是全量算的还是抽样算的」
正是必须显式表达的。

字段分离也做得对（`response.py:45-50`）：
`text`（给 LLM 读的） / `data`（结构化载荷） / `error_info` / `stats` / `context` 五路分开。
**`text` 与 `data` 分离**意味着结构化结果不必被拍平成散文 ——
这正是 §1.5 第 4 条指出 trace 层丢掉的东西：**协议层有 `data`，
但 `react_agent.py:298` 往 trace 里写的是 `result['content']`，`data` 在进 trace 前就被丢了。**
不是协议不够，是消费端没用。

### 缺陷：`from_dict` 把「没有 status 字段」默认成成功

`response.py:74`：

```python
status_str = data.get("status", "success")
```

一个缺 `status` 的 dict（截断的 JSON、别的系统传来的半成品）
**反序列化出来是 `SUCCESS`**。`:75` 的 `ToolStatus(status_str)` 只在
status 是**未知非空值**时才抛 ValueError；**字段整个缺失反而最安全地滑向成功**。
典型的「默认值兜底把数据缺失变成正向结论」。

## 2.5 错误码：15 个常量，但它不是枚举

`errors.py:7-40` 定义 `class ToolErrorCode`，15 个类属性字符串常量
（`:18` `NOT_FOUND` 起，`:40` `RATE_LIMIT` 止），分五组：资源 / 参数 / 执行 / 状态 / 网络。

**它是普通 class，不是 `Enum`。** 所以 `ToolResponse.error(code=...)` 的 `code: str`
（`response.py:143`）接受任何字符串，写 `code="OOPS"` 完全合法。

框架提供了 `is_valid_code`（`errors.py:51-53`）但**只有测试在用**：
`grep -rn "is_valid_code\|get_all_codes" --include=*.py .` → 命中
`errors.py:43`/`:51`/`:53`（定义与自调用）、`tests/test_tool_response_protocol.py:117`/`:119`/`:124`/`:126`/`:127`。
**生产路径 0 命中。** 又一个「有校验器不用」。

`get_all_codes`（`errors.py:43-49`）用 `vars(cls).items()` 过滤非下划线的 str（`:46`），
所以**未来任何人往这个类里加一个字符串类属性（哪怕是文档串），都会自动变成一个"合法错误码"**。

## 2.6 `run_with_timing`：把参数记进了 context（本项目可用的钩子）

`base.py:101-143`。除了计时，它做了一件对证据链有用的事（`base.py:137-141`）：

```python
if response.context is None:
    response.context = {}
response.context["params_input"] = parameters    # :140
response.context["tool_name"] = self.name        # :141
```

**工具的输入参数被原样挂回响应对象上。** 这是框架里唯一一处
「输入与输出被绑在同一个结构里」的地方 —— 本项目的证据链正需要这个形状。

**但它有三个断点：**

1. **异常路径也记**（`base.py:127`），这是对的；
2. **`arun` 默认实现绕过它**：`base.py:157-161` 的 `arun` 调的是 `self.run(parameters)`，
   **不是** `run_with_timing`。异步路径若直接用 `arun`，`params_input` 不会被写入。
   （`arun_with_timing`（`:163-198`）补了，但调用方必须自己选对方法。）
3. **这个 context 到不了 trace。** §1.3 的表里 `tool_result` 的 payload 只有
   `tool_name`/`tool_call_id`/`status`/`result`，`context` 与 `data` 都没进去。
   **框架在协议层收集了输入证据，又在可观测层把它扔了。**

`arun` 还有个小问题：`base.py:157` 用 `asyncio.get_event_loop()`，
Python 3.10+ 在无运行 loop 时会 DeprecationWarning，3.12 起行为进一步收紧。

## 2.7 本节的错误处理清单（逐处，带行号）

| 位置 | 形态 | 后果 |
|---|---|---|
| `base.py:120-128` | `except Exception` → `INTERNAL_ERROR` 响应 | 工具崩溃与工具返回错误不可区分 |
| `base.py:176-183` | 同上（异步路径） | 同上 |
| `base.py:449-453` | `except Exception` → `EXECUTION_ERROR` 响应 | 参数错误被吞成文本 |
| `base.py:362` | `param_descriptions.get(name, f"参数 {name}")` 默认值兜底 | docstring 格式错 → 模型收到废话说明，无警告 |
| `base.py:425` | `type_map.get(py_type, "string")` 默认值兜底 | 未知类型静默变 string |
| `base.py:266` | 硬编码 `items={"type":"string"}` | schema 对模型说假话 |
| `response.py:74` | `data.get("status","success")` 默认值兜底 | 缺字段 → 判成 SUCCESS |
| `errors.py:95-101` | `vars(cls)` 反射取常量 | 任何新增 str 类属性自动成为合法错误码 |

`base.py` / `response.py` / `errors.py` 三个文件里 **`print(` 0 命中**
（`grep -rc "print(" hello_agents/tools/base.py hello_agents/tools/response.py hello_agents/tools/errors.py` → 均 `0`）。
`print` 代替 `raise` 的问题集中在 `registry.py`（10 处）与 `circuit_breaker.py`（3 处），见 §3、§4。

# 三、`registry.py`（291 行）—— 注册、命名空间与调用链

## 3.1 两个注册表，一个命名空间，无交叉查重

`ToolRegistry.__init__` 建了**两个互不相干的 dict**（`registry.py:21-22`）：

```python
self._tools: dict[str, Tool] = {}                    # :21  Tool 对象
self._functions: dict[str, dict[str, Any]] = {}      # :22  裸函数
```

查重是**各查各的**：

- `register_tool` 只查 `_tools`（`registry.py:51`）
- `register_function` 只查 `_functions`（`registry.py:103`）

**所以「同名」是可以成立的。** 注册一个名为 `search` 的 `Tool`，
再注册一个名为 `search` 的函数，**两次都不会有任何警告**，
因为各自的 dict 里都是首次出现。

后果有三层，一层比一层严重：

**(1) `list_tools()` 返回重复名字。** `registry.py:243`：

```python
return list(self._tools.keys()) + list(self._functions.keys())
```

单纯拼接，不去重。`search` 出现两次。

**(2) 送进提示词的工具清单出现两条同名不同描述的条目。**
`get_tools_description()`（`registry.py:222-239`）分两个循环拼：
`:232-233` 遍历 `_tools`，`:236-237` 遍历 `_functions`，中间不去重。
模型收到的工具列表里 `- search: 描述A` 和 `- search: 描述B` **并排出现**。
模型无从知道调哪个，而且**无论它想调哪个，结果都由下面第 (3) 条决定**。

**(3) `_tools` 永久遮蔽 `_functions`，被遮蔽的一方无法调用也无法察觉。**
`execute_tool` 的分派是 if/elif（`registry.py:159` / `:185`）：

```python
if name in self._tools:        # :159  先查 Tool
    ...
elif name in self._functions:  # :185  再查函数
```

`_tools` 命中就 `return`，函数版本**永远执行不到**。
没有警告、没有日志、没有事件。**一个注册成功、出现在工具清单里、
模型看得见的工具，实际上是死的。**

> 对本项目：命名空间必须是**单一权威表 + 注册即查重 + 重名直接 raise**。
> 「两个表共用一个名字空间」在审计场景里意味着
> **「证据说用了 X 工具」和「实际跑的是哪段代码」可能对不上** —— 证据链断在这里。

## 3.2 重名的处理：`print` 警告 + 静默覆盖，不是异常

三处，形态一致（`registry.py:45`、`:52`、`:104`）：

```python
if tool.name in self._tools:
    print(f"⚠️ 警告：工具 '{tool.name}' 已存在，将被覆盖。")   # :52
self._tools[tool.name] = tool                                  # :54
```

**警告完照样覆盖。** 没有 `raise`，没有 `strict` 开关，没有返回值告知调用方发生了覆盖。
在 stdout 被重定向/吞掉的场景（SSE、pipe、Jupyter 后台、pytest 默认捕获）
**这个警告等于不存在**，覆盖是完全静默的。

`registry.py` 全文 `print(` **10 命中**（`grep -c "print(" hello_agents/tools/registry.py` → `10`），
包括注册成功（`:47`、`:55`、`:110`）、注销（`:116`、`:119`）、
不存在（`:121`）、清空（`:253`）。**注册表把状态变更全部经由 stdout 汇报，
没有一处走 logging，也没有一处进 trace。**

## 3.3 参数解析：这里才是真正的「静默强转」

§2.3 说非法参数会被吞成错误文本。但在**到达工具之前**，`execute_tool`
还有一层更隐蔽的转换（`registry.py:162-173`）：

```python
if isinstance(input_text, str):
    try:
        parameters = json.loads(input_text)          # :166
    except json.JSONDecodeError:
        parameters = {"input": input_text}           # :169  ← 静默强转
elif isinstance(input_text, dict):
    parameters = input_text                          # :171
else:
    parameters = {"input": str(input_text)}          # :173  ← 静默强转
```

**两处凭空造出一个名叫 `input` 的参数。** 这个键名
**不来自任何工具的 `get_parameters()` 声明** —— 它是解析失败时的兜底约定。

真实后果：一个声明了参数 `expression` 的工具，
如果模型传了非 JSON 的裸字符串，收到的是 `{"input": "..."}`，
**声明过的参数一个都没有**。工具内部 `parameters.get("expression")` 拿到 `None`，
于是走进自己的「参数缺失」分支 —— **报出来的是「表达式不能为空」，
而真实原因是「注册表把你的参数改名了」**。归因完全错位。

还有一个更硬的坑：`json.loads` 对**标量**也是成功的。
`json.loads("42")` → `int 42`，`json.loads('"abc"')` → `str`，`json.loads("[1,2]")` → `list`。
这三种情况 `:166` 都不抛异常，于是 `parameters` **根本不是 dict**，
直接被送进 `tool.run_with_timing(parameters)`（`:176`）。
工具里第一次 `parameters.get(...)` 就 `AttributeError`，
被 `base.py:120` 吞成 `INTERNAL_ERROR`。**一个能被解析的合法 JSON 反而更容易炸。**

顺带：`execute_tool` 的类型标注是 `input_text: str`（`registry.py:132`），
但 `:170` 明确处理 `dict` 分支 —— **标注与实现不符**，标注不可信。

## 3.4 函数工具与 Tool 对象的调用约定完全不同

- Tool 对象：`tool.run_with_timing(parameters)`，参数是 **dict**（`registry.py:176`）
- 函数工具：`func(input_text)`，参数是**原始的单个位置参数**（`registry.py:190`）

**函数工具完全没有参数映射**：不解析 JSON、不拆字段、不看声明。
`register_function` 也**从不提取参数签名** —— `registry.py:89-101` 只抠了 name 和
description 的第一行，`get_parameters()` 这类东西压根不存在。

于是函数工具：

- 没有参数 schema → **不可能出现在 `to_openai_schema()` 里**
- 但**会出现在 `get_tools_description()` 的提示词里**（`:236-237`）

即 **ReAct（读提示词）能看见它，function calling（读 schema）看不见它。**
两条 Agent 路线看到的工具集不一样，且没有任何地方声明这个差异。

## 3.5 熔断结果记录在所有路径上，包括「工具不存在」

`registry.py:218` 无条件执行：

```python
self.circuit_breaker.record_result(name, response)
```

它在**四条路径的汇合点**之后：Tool 成功/失败、函数成功/失败、
以及 `:210-215` 的**「未找到工具」**分支。

所以：**连续 3 次调用一个不存在的工具名，熔断器会为这个从未注册过的名字开闸。**
之后再调，`is_open` 命中（`:144`），返回的错误码从 `NOT_FOUND` 变成 `CIRCUIT_OPEN`，
消息变成「工具当前被禁用，由于连续失败，N 秒后可用」（`:148`）。

**这条消息是假的**：它承诺若干秒后可用，但那个工具根本不存在，永远不会可用。
模型读到「稍后可用」很可能选择等待或重试，而正确行为是立刻放弃并换工具。
**错误码从「事实」退化成「误导」，这是熔断器放错位置的直接代价。**

## 3.6 `global_registry`：import 期建立的可变单例

`registry.py:291` —— `global_registry = ToolRegistry()`，模块级，导入即构造。
经由 `hello_agents/__init__.py:30` 与 `:54` 提升为顶级公开 API。

它自带一个**默认启用的熔断器**（`:28`），所以这个单例携带**跨 Agent 共享的可变失败计数**。
两个 Agent 用同一个 `global_registry`，A 把某工具打熔断，B 立刻也用不了。
`_tools` 同理 —— 而这正是 §4.3 那个洞的前提。

---

# 四、两个「闸门」：`circuit_breaker.py`（168）与 `tool_filter.py`（147）

> 本节是本项目 `ARCHITECTURE.md` §8「闸门放进调用签名」决策的**直接对照物**。
> 结论先说：**hello-agents 两个闸门用了两种不同的放法，
> 而且两种都不是「放进调用签名」，两种都出了问题。**

## 4.1 闸门 A：熔断器 —— 链条上的一环，且不可绕过

**放置方式：注册表的实例属性，在 `execute_tool` 内部被读。**

```python
# registry.py:20   构造签名
def __init__(self, circuit_breaker: Optional[CircuitBreaker] = None):
# registry.py:28   永远有一个
    self.circuit_breaker = circuit_breaker or CircuitBreaker()
# registry.py:144  调用链上被读
    if self.circuit_breaker.is_open(name):
```

**执行方法的签名里没有闸门**：`execute_tool(self, name, input_text)`（`registry.py:132`）。
闸门是**环境状态**，不是调用参数。

三个直接后果：

1. **`None` 不等于「不要闸门」。** `registry.py:28` 的 `or` 意味着
   `ToolRegistry(circuit_breaker=None)` 得到的是**默认启用的熔断器**。
   要真正关掉，必须显式传 `CircuitBreaker(enabled=False)`。
   「传 None 关闭」是最自然的猜测，而它是错的。
2. **无法按调用决定。** 同一个注册表里，「这一次调用请绕过熔断」表达不出来。
   重试、健康探测、人工复核这类场景没有出口。
3. **闸门状态不进证据。**
   `grep -rn "circuit" --include=*.py hello_agents/ | grep -i "log_event\|trace"` → **0 命中**。
   熔断只经由 `print`（`circuit_breaker.py:100`、`:113`、`:119`，
   `grep -c "print(" hello_agents/tools/circuit_breaker.py` → `3`）。
   **「这次回答之所以没用某工具，是因为它被熔断了」——
   这个事实在 trace 里完全不存在。** 对审计而言这是关键信息的丢失：
   证据链看起来是完整的，但缺了「本可以用而没用」的原因。

### 熔断器自身的四个实现问题

**(1) `PARTIAL` 被算作成功**（`circuit_breaker.py:85`）：

```python
is_error = response.status == ToolStatus.ERROR
```

`:87-90` 非 ERROR 即走 `_on_success`，而 `_on_success`（`:102-105`）
把失败计数**清零**。所以一个永远返回 `PARTIAL`（永远截断、永远降级）的工具
**不但不会熔断，还会把之前累积的失败计数抹掉**。
ERROR/PARTIAL 交替出现的工具，计数永远到不了阈值，**熔断器形同虚设**。

考虑到 `PARTIAL` 的定义就是「结果可用但存在折扣（截断、回退、部分失败）」
（`response.py:15`），**这恰恰是最需要被计入健康度的那一类**。

**(2) 没有半开态，恢复即满信任。** 类 docstring 写着状态机
`Closed → Open → Closed`（`:18-19`），实现里确实**只有两态**。
`is_open` 在超时后直接 `close()`（`:66-69`），而 `close` 把计数清零（`:117`）。
没有「先放一个探测请求」的环节 —— **恢复期一到，工具带着干净的账本回来**，
再坏也要重新攒够 `failure_threshold` 次。

**(3) `is_open()` 是有副作用的查询，而且会打印。**
`:68` 在查询过程中调用 `self.close(tool_name)`，`close` 里 `:119` 无条件 `print`。
一个名为 `is_open` 的谓词，**读它会改状态并往 stdout 写字**。

**(4) `get_status` 不尊重 `enabled`。**
`is_open` 在禁用时早退返回 False（`:57-58`），
但 `get_status`（`:135`）直接读 `open_timestamps`，**没有 enabled 检查**。
先熔断、再设 `enabled=False`，此时 `is_open()` → `False` 而
`get_status()["state"]` → `"open"`。**两个 API 对同一问题给出相反答案。**

附带：`get_status` 的返回标注是 `Dict[str, any]`（`:121`），
小写 `any` 是内置函数不是 `typing.Any` —— 标注写错了。

## 4.2 闸门 B：工具过滤器 —— 签名里有，执行链上没有

**放置方式：`run_as_subagent` 的可选形参。**

```python
# core/agent.py:880-886
def run_as_subagent(
    self,
    task: str,
    tool_filter: Optional['ToolFilter'] = None,   # :883  ← 在签名里
    return_summary: bool = True,
    max_steps_override: Optional[int] = None
) -> Dict[str, Any]:
```

看起来正是「闸门放进调用签名」。**但实现把它退化成了对共享状态的破坏性改写。**

`_apply_tool_filter`（`core/agent.py:990-1021`）的做法是
**从注册表里把不允许的工具 `del` 掉**：

```python
original_tools = self.tool_registry.list_tools()          # :1003
filtered_tools = tool_filter.filter(original_tools)       # :1006
for tool_name in original_tools:
    if tool_name not in filtered_tools:
        self.tool_registry._temp_disabled_tools = getattr(
            self.tool_registry, '_temp_disabled_tools', {} # :1011-1013 猴补属性
        )
        tool = self.tool_registry.get_tool(tool_name)      # :1014
        if tool:
            self.tool_registry._temp_disabled_tools[tool_name] = tool
            if tool_name in self.tool_registry._tools:
                del self.tool_registry._tools[tool_name]   # :1019  ← 真删
```

**注意 `_temp_disabled_tools` 不是 `ToolRegistry` 的字段。**
`grep -rn "_temp_disabled_tools" --include=*.py .` → **6 命中，全部在 `core/agent.py`**
（`:1011`、`:1012`、`:1016`、`:1033`、`:1034`、`:1038`），
`registry.py` 里 **0 命中**。这是 Agent 层往 Registry 对象上**猴补**的一个属性。

于是「隔离」不是隔离，是**全局副作用 + 事后回滚**：

- **不可重入。** 嵌套子代理共用同一个扁平 `_temp_disabled_tools` dict。
  内层 `_restore_tools`（`:1033-1038`）把字典里的**所有**工具塞回 `_tools`（`:1035`）
  并清空（`:1038`），**包括外层本想继续屏蔽的那些**。外层的隔离窗口就此破裂。
- **不是线程安全的。** 配合 §3.6 的 `global_registry` 单例，
  子代理跑期间，**主 Agent 或另一个 Agent 看到的注册表是被挖空的**。
- **异常路径依赖 `_restore_tools` 被调到。** 一旦回滚没执行，
  工具就**永久消失**在这个进程里了。

## 4.3 过滤器有个真实的绕过：函数工具完全不受管

`_apply_tool_filter` 的删除只作用于 `_tools`：
`:1014` 的 `get_tool` 只读 `_tools`（`registry.py:123-125`），
`:1018-1019` 的 `del` 只删 `_tools`。

**`_functions` 从头到尾没被碰过。**
验证：`grep -rn "_functions" --include=*.py hello_agents/` → **12 命中**，
全在 `registry.py`（`:22`/`:103`/`:106`/`:117`/`:118`/`:129`/`:185`/`:186`/`:236`/`:243`/`:252`，共 11 处）
与 `core/agent.py:557`（读 `function_map` 供 function calling 用），
**`_apply_tool_filter` / `_restore_tools` 所在的 `:990-1038` 区间 0 命中。**

而 `list_tools()`（`registry.py:243`）**是包含 `_functions` 的**，
所以过滤器**算出了**该禁用某个函数工具，**却没有能力禁用它** ——
`:1015` 的 `if tool:` 判空后直接跳过，静默。

**结论：用 `register_function` 注册的工具，绕过全部 `ToolFilter`。**
`FullAccessFilter` 的黑名单 `{"Bash","BashTool","Terminal",...}`（`tool_filter.py:86-90`）
与 `ReadOnlyFilter` 的白名单（`:51-57`）**对函数工具一律无效**。
一个「只读子代理」照样能调用注册为函数的任意副作用代码。

### 过滤器自身的问题

- **黑名单按字面名匹配且大小写敏感**（`tool_filter.py:106-108`，`not in self.denied_tools`）。
  同一个危险工具改名注册成 `bash` / `Shell` / `RunCmd` 即通过。
  **黑名单式安全边界在「名字由注册方自选」的系统里不成立。**
- **`ReadOnlyFilter` 白名单收了 `Skill` / `SkillTool`**（`tool_filter.py:56`）。
  这一条要跟 §6 的 `SkillTool` 一起看 —— 若 skill 能执行脚本，
  「只读」过滤器就放进了一个任意执行入口。
- **`CustomFilter()` 无参 = 拒绝一切。** `mode` 默认 `"whitelist"`（`:117-135` 区间），
  `allowed` 为 None 时 `self.allowed = set()`，`is_allowed` 恒 False（`:143-144`）。
  行为上是 fail-closed（方向对），但**没有任何文档或警告说明**，
  容易被误读成「没配置就是不限制」。
- `CustomFilter.__init__` 的 mode 校验（`tool_filter.py:135` `raise ValueError`）
  是这两个闸门文件里**唯一一处 `raise`**。
  `grep -c "raise" hello_agents/tools/circuit_breaker.py` → `0`。

## 4.4 对照本项目「闸门放进调用签名」

把两个闸门摆在一起看，**hello-agents 恰好演示了这条决策要防的两种失败**：

| | 熔断器 | 工具过滤器 |
|---|---|---|
| 闸门在哪 | 注册表实例属性（`registry.py:28`） | `run_as_subagent` 形参（`agent.py:883`） |
| 执行时怎么生效 | 调用链内部读（`registry.py:144`） | **改写共享注册表**（`agent.py:1019`） |
| 能否按次覆盖 | **不能** | 名义上能，实际是全局副作用 |
| 覆盖是否完全 | 是（所有路径都过 `:144`） | **否**，`_functions` 全部漏掉（§4.3） |
| 是否进证据 | **否**（trace 0 命中） | **否** |

**签名里有一个 `Optional[Gate]` 形参，不等于闸门在调用签名上。**
判据应当是：**闸门是否作为不可省略的输入参与那次调用的求值，
并且它的取值是否随该次调用一起被记录。** 按这个判据，
`run_as_subagent` 的 `tool_filter` 不合格 —— 它只是个开关，
真正决定行为的是它对全局字典造成的副作用，而那个副作用没有出现在任何证据里。

---

# 五、`builtin/` 之一：`calculator` / `task_tool` / `skill_tool`（36+156+186+173 = 551 行）

## 5.1 `calculator.py`：安全的求值器，不安全的数值语义

**做对的部分：没有用 `eval()`。** `run` 走 `ast.parse(expression, mode='eval')`（`:72`）
再由 `_eval_node`（`:104-130`）递归求值，操作符白名单 7 项（`:16-24`）、
函数白名单 13 项（`:27-41`），不在白名单一律 `raise ValueError`（`:123`、`:128`、`:130`）。
这是求值类工具的正确写法。

**但对财务场景有三个硬伤：**

**(1) 除法是 `operator.truediv`（`:20`），全程 IEEE-754 双精度浮点。**
没有 `Decimal`，没有精度控制，没有舍入策略。
`0.1+0.2` 得 `0.30000000000000004`，而 `_eval_node` 会把它原样返回，
`:74` `str(result)` 直接给模型。**金额、比率、同比增速在这条路径上全是浮点。**
审计口径里「保留两位、四舍五入还是银行家舍入」是有规定的，这里一个都没有。

**(2) `ast.Pow` 在白名单里（`:21`），没有任何幂次上限。**
模型生成 `9**9**9**9` 会直接把进程拖死 —— CPython 的大整数幂没有超时。
`run_with_timing` 只**测量**耗时（`base.py:116`），**不设超时**，
`ToolErrorCode.TIMEOUT`（`errors.py:30`）这个错误码在 `tools/` 内**从未被任何工具返回过** ——
`grep -rn "TIMEOUT" --include=*.py hello_agents/tools/` → **1 命中，就是 `errors.py:30` 的定义本身**。

**(3) 参数名的两副面孔。** `:60`：

```python
expression = parameters.get("input", "") or parameters.get("expression", "")
```

它同时接受 `input` 和 `expression`，**但 `get_parameters()` 只声明了 `input`**（`:136-141`）。
`expression` 是一个**未声明却被接受**的参数。

这行代码是 §3.3 那个「注册表把参数改名成 `input`」的**创可贴**：
内置工具知道要兼容 `input`，所以看起来一切正常。
**第三方按 `get_parameters()` 的声明写工具就会踩坑** ——
声明 `expression`、只读 `expression`，遇到非 JSON 输入就永远拿到空值。
**框架用内置工具的特殊适配，掩盖了协议层的缺陷。**

其他：`print` 4 处（`:68`、`:76`、`:89`、`:97`），把计算过程打到 stdout；
`ast.Num`（`:108`）在 3.12 已废弃；
`:118` `node.func.id` 遇到 `a.b()` 形式会 AttributeError，落进 `:95` 的宽 except。

**便捷函数 `calculate` 的返回类型标注是错的**（`:145-156`）：
签名写 `-> str`，`:156` 返回的是 `tool.run({...})` 即 **`ToolResponse` 对象**。
调用方按标注当字符串用会拿到 `ToolResponse(...)` 的 repr。

## 5.2 `task_tool.py`：子代理沙箱在拼写错误时 fail-open

`TaskTool` 是 §4.2 那条链的**起点** —— 模型通过它触发 `run_as_subagent`。

**闸门在这里是一个字符串参数**（`:69-75`）：

```python
ToolParameter(
    name="tool_filter",
    type="string",
    description="工具过滤策略：readonly（只读工具）、full（完全访问）、none（无过滤）",
    required=False,
    default="none"          # :74  ← 默认不过滤
)
```

映射发生在 `_create_tool_filter`（`:168-185`）：

```python
if filter_type == "readonly":   return ReadOnlyFilter()    # :177-178
elif filter_type == "full":     return FullAccessFilter()  # :179-180
elif filter_type == "none":     return None                # :181-182
else:
    # 默认无过滤
    return None                                            # :183-185
```

**`else` 分支把任何无法识别的取值降级成「无过滤」。**
`"read-only"`、`"readonly "`（尾随空格）、`"ro"`、`"restricted"`
—— 全部静默变成**完全无限制**。`:99` 只做了 `.lower()`，不做校验、不报错、不警告。

这是**安全控制上的 fail-open**，而且触发它的字符串由**模型**生成。
模型想收紧权限却拼错了一个字符，得到的是最宽的权限，而且它不会知道。

对比 `CustomFilter` 在 mode 非法时 `raise ValueError`（`tool_filter.py:135`）——
**同一个代码库里，同一类问题，一处 raise 一处静默放行**，取的是最松的那条路径。

于是子代理沙箱有**两条独立的失效路径**：

1. 本节：`tool_filter` 拼错 → 无过滤
2. §4.3：即使过滤器正确构造，`register_function` 注册的工具也完全不受管

**任何一条成立，「只读子代理」的承诺就不成立。**

其余：

- 子任务失败返回 `ToolResponse.partial`（`:144-152`）。结合 §4.1(1)，
  **PARTIAL 会重置熔断计数** —— 一个每次都失败的子代理**永远不会被熔断**，
  还会顺手把别的失败记录抹掉。
- `max_steps` 从参数直接透传（`:100` → `:122`），无上下界校验。
- `data` 里带了完整 `task` 与 `**result["metadata"]`（`:134-138`），
  对证据链是好事；但 `**` 展开可能被 metadata 里的同名键覆盖 `agent_type`/`task`。
- `print` 3 处（`:116`、`:130`、`:142`）。

## 5.3 `skill_tool.py`：纯文本注入，不执行任何东西

**先澄清一个容易误判的点。** §4.3 提过 `ReadOnlyFilter` 的白名单里有
`Skill` / `SkillTool`（`tool_filter.py:56`），看起来像是「只读过滤器放进了执行入口」。
**逐行读完后，这个指控不成立** —— 至少在框架层不成立：

`SkillTool.run`（`:77-141`）做的全部事情是：
取 skill 名 → `skill_loader.get_skill()` 读文件 → 字符串替换 → 拼文本 → 返回。
**没有任何执行动作。**

全仓验证：`grep -rn "subprocess\|os.system\|exec(\|popen\|run_script" --include=*.py hello_agents/`
→ **0 命中**。**框架从不执行 skill 目录下的任何脚本。**

`_get_resources_hint`（`:143-172`）也只是 `glob("*")` 后**列出文件名**（`:162-167`），
不读内容、不运行。

**所以真实风险不是「执行」，是「注入」** —— 而这一层确实有问题：

**(1) `$ARGUMENTS` 是无转义的原始字符串替换**（`:109`）：

```python
content = skill.body.replace("$ARGUMENTS", args)
```

`args` 由模型给（`:87`），被原样插进**将要作为指令交给模型的文本**里。
`args` 里写什么都行，包括 `</skill-loaded>` 加一段新指令。

**(2) 包装标签里的 `skill_name` 同样不转义**（`:115`）：

```python
full_content = f"""<skill-loaded name="{skill_name}">
```

`skill_name` 来自模型（`:86`）。含 `"` 或 `>` 即可破坏这个伪 XML 边界。

**(3) 返回的 `text` 直接是完整技能正文**（`:126`），
末尾还附「请严格遵循上述技能说明来完成用户任务」（`:123`）。
即 **tool_result 的内容被明确赋予了指令效力**。
结合 (1)(2)，一个受污染的 skill 文件或一段构造过的 `args`，
就是一条把指令送进模型的通道。

**(4) `token_estimate` 是字符数，不是 token 数**（`:131`）：

```python
"token_estimate": len(full_content)
```

中文按字符数近似 token 会高估 1~1.5 倍，英文会高估约 4 倍。
这是又一个**名字与语义不符的指标**（同 §1.9(3) 的 `total_cost`）。
`data` 字段名叫 `token_estimate`，下游若拿它做预算控制会系统性算错。

做对的地方：`:93`、`:105`、`:140` 三处都把 `params_input` 写进了 `context`，
与 §2.6 的约定一致。

---

# 六、`skills/`（`__init__.py` 27 + `loader.py` 225 = 252 行）—— 扩展契约

## 6.1 契约本身：一个目录 + 一个 `SKILL.md`

外部加一个 skill 的**全部要求**（`loader.py:87-108`、`:110-142`）：

1. 在 `skills_dir` 下建**一级子目录**（`:89` `iterdir()`，**不递归**）
2. 目录里放 `SKILL.md`（`:93-95`，文件名硬编码，大小写敏感）
3. 文件以 YAML frontmatter 开头，`---` 包裹（`:125` 正则）
4. frontmatter **必须**含 `name` 与 `description`（`:139-140`），缺一即整个 skill 被丢弃
5. `---` 之后的全部内容是 body（`:185`、`:190`），无格式要求、无长度限制

可选：目录下再放 `scripts/` `references/` `assets/` `examples/`
—— 这四个名字硬编码在 `skill_tool.py:154-159`，**只被列出文件名，不被读取**。

**契约就这么多。没有 schema 校验、没有版本号、没有依赖声明、没有能力声明。**
`grep -rni "version\|sha\|hash\|checksum" hello_agents/skills/loader.py` → **0 命中**。

## 6.2 边界在哪：skill 只能提供「文字」，不能提供「代码」

这是这套设计里**最值得本项目学的一点**，也是最容易被误解的一点。

- skill 提供的是 **body 文本**，经 `SkillTool` 作为 tool_result 注入（`skill_tool.py:126`）
- skill 目录里的脚本**框架永远不执行**（§5.3 的 0 命中 grep）
- `Skill` 类虽然提供了 `scripts` / `examples` / `references` 三个属性
  （`loader.py:25-47`，共 23 行），**但全仓无人调用**：
  `grep -rn "\.scripts\b\|\.examples\b\|\.references\b" --include=*.py hello_agents/` → **0 命中**。
  **这 23 行是死代码。**

所以边界是清晰的：**skill 是知识，不是插件。**
它扩展的是「模型知道什么」，不是「系统能做什么」。
能力边界仍然由工具注册表决定，skill 无法越过它。

**这个切分对本项目直接可用**：审计准则、指标口径定义、行业惯例
正是「知识」而非「能力」，适合走 skill 这条路；
而「读哪张表、怎么算」必须是工具，受注册表与证据链管辖。

## 6.3 加载路径上的五处静默失败

`_parse_frontmatter_only`（`:110-142`）有**四个 `return None` 出口**，
调用方 `_scan_skills` 一律 `continue`（`:99-100`）：

| 行号 | 触发条件 | 形态 |
|---|---|---|
| `:119-122` | 读文件抛任何异常 | `except Exception: return None` —— **宽 except，吞掉权限/编码/IO 全部错误** |
| `:127-128` | 没有 frontmatter | 静默 |
| `:135-136` | YAML 语法错 | `except yaml.YAMLError: return None` |
| `:139-140` | 缺 `name` 或 `description` | 静默 |

`get_skill`（`:158-210`）另有三处同形态出口：`:181-182`（宽 except）、`:187-188`、`:195-196`。

**后果：一个写坏的 skill 是完全隐形的。**
不打印、不记日志、不计数、不抛异常。
运维者无法区分「我有 17 个 skill」和「我有 20 个，其中 3 个解析失败」。

`loader.py` 全文 `print(` **1 命中**，`raise` **0 命中**
（`grep -c "raise" hello_agents/skills/loader.py` → `0`）。
**这个加载器没有任何一条路径会让调用方知道出了问题。**

## 6.4 skill 重名：比工具重名更糟，连警告都没有

`_scan_skills:102-103`：

```python
name = metadata.get("name", skill_dir.name)
self.metadata_cache[name] = {...}
```

**键是 frontmatter 里的 `name`，不是目录名。** 两个不同目录声明同一个 `name:`，
后扫描到的**直接覆盖**先扫描到的。

而 `:89` 的 `self.skills_dir.iterdir()` **不保证顺序**（取决于文件系统），
所以**哪一个胜出是不确定的** —— 同一份代码在两台机器上可能加载到不同的 skill 内容。

对比 §3.2：工具重名至少还 `print` 一句警告。
**skill 重名连警告都没有。**

对审计的意义很直接：**「本次回答依据了哪份口径说明」这个问题，
在 skill 重名时无法回答**，因为连系统自己都不知道加载的是哪个目录下的那一份。
这正是本项目必须用「内容哈希 + 唯一 id」而不是「人取的名字」来标识依据的原因。

## 6.5 其余四个实现问题

**(1) 构造即建目录。** `:76` `self.skills_dir.mkdir(parents=True, exist_ok=True)`。
路径写错 → 悄悄创建一个空目录 → 扫出 0 个 skill → **无任何报错**，
`get_descriptions()` 返回「（暂无可用技能）」（`:151`）。
**配置错误与「确实没有 skill」表现完全一致。**

**(2) 「热重载」是手动的。** 类 docstring `:58` 写「支持热重载」，
实现上 `skills_cache`（`:208`）与 `metadata_cache` 只有显式调用
`reload()`（`:220-224`）才会刷新。文件改了不会自动生效。
而且 `grep -rn "reload()" --include=*.py hello_agents/` → **0 命中** ——
**框架内部没有任何一处调用它**，刷新完全是调用方的责任，文档却宣称「支持热重载」。

**(3) body 无长度上限。** `:202` `body.strip()` 全量进 `Skill`，
再由 `skill_tool.py:126` 全量进上下文。一个 10 MB 的 SKILL.md 会被整份注入。
所谓「渐进式披露」只做到了**目录级**（元数据 vs 全文两层），
**没有做到文件内的分级**。

**(4) `get_skill` 的一致性校验是空的。** `:192` 注释写「解析 frontmatter（验证一致性）」，
但 `:194` 解析完之后**只是拿来取值**（`:200-201`），
**从未与 `metadata_cache` 里的元数据比对**。注释承诺了一个不存在的校验。
后果：`get_descriptions()` 送进提示词的描述，
与 `get_skill()` 实际加载时的描述**可以不一致**（文件在两次读之间被改动过），
而且这个不一致不会被发现。

---

# 七、`builtin/file_tools.py`（762 行）—— 四个文件工具

这是 `tools/` 里最长的文件，也是问题密度最高的。四个类
（`ReadTool` `:35`、`WriteTool` `:271`、`EditTool` `:419`、`MultiEditTool` `:591`）
共享大量复制粘贴的私有方法，而**复制过程中出现了分歧**（§7.6）。

## 7.1 `project_root` 不是沙箱 —— 它什么都不拦

四个类的构造函数都收 `project_root`，都 `.resolve()`
（`:62`、`:297`、`:445`、`:616`）。文档里写「相对项目根目录」（`:71`、`:454`、`:625`）。
**但它从不参与任何访问控制。**

`project_root` 在全文件的全部命中（`grep -n "project_root" file_tools.py`，14 处）里，
**实际被读取的只有两种用途**：

1. 作为 `working_dir` 的默认值（`:63`、`:298`、`:446`、`:617`）
2. `:200` 目录列表里 `entry.relative_to(self.project_root)` —— **纯显示用**

真正的路径解析是 `_resolve_path`（`:258-268` / `:412-416` / `:584-588` / `:757-761`）：

```python
if os.path.isabs(path):
    return Path(path)          # :264-265 —— 绝对路径直接放行
return self.working_dir / path # :268    —— 拼接，不 resolve，不校验包含关系
```

**两条逃逸路径，都不需要技巧：**

- **绝对路径直接生效。** `path="C:/Users/xxx/.ssh/id_rsa"` 或 `path="/etc/passwd"`
  被原样返回，`project_root` 完全不参与。
- **`..` 不被拦截。** `self.working_dir / "../../secrets.env"` 是合法 `Path`，
  没有 `.resolve()` 后的包含性检查。

验证：`grep -rn "is_relative_to\|commonpath\|startswith(str(self.project_root))" --include=*.py hello_agents/tools/`
→ **0 命中**（唯一被匹配到的 4 行是 `:63`/`:298`/`:446`/`:617` 那句 `working_dir` 赋值，不是校验）。

**这一条要和 §4 的过滤器一起看才知道有多严重：**
`ReadOnlyFilter.READONLY_TOOLS` 白名单里明确包含 `"Read"` / `"ReadTool"`
（`tool_filter.py:52`）。也就是说 —— **框架推荐用于「探索代码库」「规划任务」的只读子代理，
拥有一个可以读取文件系统上任意文件的工具**，而使用者会因为构造时传了 `project_root`
而认为它被限制在项目目录内。

> 对本项目：**「根目录」参数必须真的是边界，不能只是拼路径的前缀。**
> 正确做法是 `full = (root / path).resolve()` 之后强制 `full.is_relative_to(root)`，
> 否则直接 `ACCESS_DENIED`。本项目要处理的是年报 PDF 与财务数据，
> 一个能读任意路径的工具会把「证据来自受控语料」这个前提直接推翻。

## 7.2 截断被报成 SUCCESS —— `PARTIAL` 定义了却不用

`ReadTool` 默认 `limit=2000` 行（`:94`、`:86`）。截断逻辑（`:120-127`）：

```python
total_lines = len(lines)
if offset > 0: lines = lines[offset:]
if limit > 0:  lines = lines[:limit]
```

然后（`:142-143`）：

```python
return ToolResponse.success(
    text=f"读取 {len(lines)} 行（共 {total_lines} 行，{file_size_bytes} 字节）",
```

**读了 2000 行、丢了 3000 行，状态是 `SUCCESS`。**

而 `ToolStatus.PARTIAL` 的定义原文就是
「结果可用但存在折扣（**截断**、回退、部分失败）」（`response.py:15`）。
**框架定义了恰好描述这个场景的状态，然后在这个场景里没有用它。**

`tools/` 全文 `ToolResponse.partial` 只有 `task_tool.py:144` 一处在用。

三层后果：

1. **熔断器看到的是成功**（`circuit_breaker.py:85` 只认 ERROR），健康度统计失真。
2. **调用方要发现截断，必须自己比对 `data["lines"]` 与 `data["total_lines"]`**（`:146-147`）。
   截断这个事实只存在于 `text` 的散文里和两个需要相减的数字里，**不在 `status` 上**。
3. **这正是 §1.6 E6「原始产物被丢弃」的实证。** 被丢的 3000 行不进 `data`，
   也就不进 trace（§2.6 第 3 点：`context`/`data` 本来就到不了 trace）。
   复核者拿到的证据是「读取成功」，无从知道模型只看到了文件的 40%。

## 7.3 乐观锁是自愿的，不传就等于没有

冲突检测的入口条件（`:353`、`:517`、`:675`）都是同一个形状：

```python
if cached_mtime is not None and current_mtime_ms != cached_mtime:
    return ToolResponse.error(code=ToolErrorCode.CONFLICT, ...)
```

而 `file_mtime_ms` 三处都声明为 **`required=False`**（`:319`、`:473`、`:638`）。

**模型只要不传这个参数，冲突检测整条分支就被跳过，直接覆盖写入。**
没有警告，没有降级标记，返回的仍是 `SUCCESS`。

注册表里明明缓存着元数据 —— `ReadTool` 在 `:136-140` 写入
`registry.cache_read_metadata`，注册表也提供了 `get_read_metadata`（`registry.py:268-277`）
—— **但三个写工具没有一个去读它**。
`grep -n "get_read_metadata" hello_agents/tools/builtin/file_tools.py` → **0 命中**。

即：**框架费力缓存了乐观锁需要的令牌，然后要求模型自己把它抄回来。**
安全性依赖模型的自觉，而模型没有任何机制约束。

补充两个更细的问题：

- **缓存键是原始 `path` 字符串**（`:137`），不是解析后的绝对路径。
  `"a.txt"` 与 `"./a.txt"` 指向同一文件却是两个缓存条目。
- **mtime 分辨率**。`int(mtime*1000)` 看起来是毫秒，但底层文件系统
  可能只有 1 秒（部分 Linux 挂载）或 2 秒（FAT）粒度。
  **同一粒度窗口内的两次修改检测不到。**

## 7.4 `MultiEditTool` 的「原子性保证」两处都不成立

类 docstring 写「**原子性保证（要么全部成功，要么全部失败）**」（`:596`）。
逐行读下来，两个含义上都不成立。

### (1) 校验用的是原文，执行用的是滚动结果

校验循环（`:692-709`）对**未修改的 `content`** 逐项数匹配：

```python
for i, edit in enumerate(edits):
    matches = content.count(old_string)   # :703  content 此刻还是原文
    if matches != 1: return ...error
```

执行循环（`:712-713`）则是**顺序累积**的：

```python
for edit in edits:
    content = content.replace(edit["old_string"], edit["new_string"])  # :713
```

**第 2 个 edit 面对的是第 1 个 edit 改过之后的文本。**
所以：

- edit 1 可能**消灭**了 edit 2 的 `old_string` → `replace` 静默无操作，
  校验说「唯一匹配」，实际替换了 0 处，**返回仍是 SUCCESS**
- edit 1 可能**制造出**第 2 个 `old_string` 的副本 → `:713` 的 `replace`
  **不带 count 限制，会替换全部出现**，一次改掉 2 处，
  而校验时它只有 1 处

**校验的对象和执行的对象不是同一个东西**，「全部成功」的保证落空。

### (2) 写入根本不原子

对照三个写工具：

| 工具 | 写入方式 | 是否原子 |
|---|---|---|
| `WriteTool` | 临时文件 + `os.replace`（`:371-376`） | **是** |
| `EditTool` | `open(path,'w')` 直接截断重写（`:547-548`） | 否 |
| `MultiEditTool` | `open(path,'w')` 直接截断重写（`:719-720`） | 否 |

**唯一在文档里宣称原子性的那个，用的是最不原子的写法。**
`open(...,'w')` 先截断再写，进程在这中间死掉就得到一个残缺文件。
而 `WriteTool` 那个真正用了 temp+rename 的，docstring 里只写「原子写入」没强调保证。

顺带：`WriteTool` 的原子写也不完整 —— `:372-373` 写完没有
`f.flush()` + `os.fsync()` 就 `os.replace`（`:376`），
断电场景下可能 rename 出一个空文件。

## 7.5 备份：同一秒内的第二次备份会覆盖第一次

`_backup_file` 复制了三份（`:400-410`、`:572-582`、`:745-755`），内容完全一致：

```python
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")   # :405 秒级
backup_name = f"{full_path.name}.{timestamp}.bak"
backup_path = backup_dir / backup_name
shutil.copy2(full_path, backup_path)                   # :409 直接覆盖同名
```

**时间戳只到秒。** Agent 连续两次编辑同一文件（这在 ReAct 循环里非常常见）
若落在同一秒内，第二次备份**覆盖**第一次，
**第一次编辑前的原始内容永久丢失** —— 而这正是备份要防的情况。
没有序号、没有校验、`copy2` 也不会因为目标存在而报错。

## 7.6 复制粘贴出的两处分歧与一个「已改还报错」

**(1) `_resolve_path` 有四份，其中一份不一样。**
`ReadTool` 的版本多了一行斜杠归一化（`:261`）：

```python
path = path.replace('\\', '/')     # 只有 ReadTool 有
```

`WriteTool`（`:412-416`）、`EditTool`（`:584-588`）、`MultiEditTool`（`:757-761`）
**都没有这一行**。于是同一个 `"dir\\file.txt"`，
`Read` 能正确解析，`Write`/`Edit` 在非 Windows 上会当成一个含反斜杠的文件名。
**读写两端对同一个路径字符串的理解不一致。**

**(2) 副作用已发生却返回错误。**
`:557`、`:730`、`:385` 都调用：

```python
str(backup_path.relative_to(self.working_dir))
```

`Path.relative_to` 在目标不在基准路径下时**抛 `ValueError`**。
配合 §7.1 —— 只要 `path` 是绝对路径或用 `..` 逃出了 `working_dir`，
备份目录就在 `working_dir` 之外，这行必然抛异常。

抛出的位置在**文件已经备份（`:544`/`:716`）并且已经写入（`:547-548`/`:719-720`）之后**。
异常被 `:566`/`:739` 的宽 `except Exception` 接住，
返回 `INTERNAL_ERROR`「编辑文件失败」。

**文件确实被改了，返回值说失败。** 模型据此重试，就会改第二次。
这是本文件里最容易造成实际数据损坏的一条。

## 7.7 本文件的错误处理清单（逐处，带行号）

| 位置 | 形态 | 后果 |
|---|---|---|
| `:189-190` | **裸 `except:`** | 取不到文件大小 → 静默填 `"?"` |
| `:196-197` | **裸 `except:`** | 取不到 mtime → 静默填 `"?"` |
| `:209-211` | `except Exception as e: continue`（`e` 绑定后未使用） | **目录条目被静默跳过**，`total_files`/`total_dirs` 少计，仍报 SUCCESS |
| `:160-164` | `except Exception` → `INTERNAL_ERROR` | 读失败原因被压成一句话 |
| `:238-242` | `except Exception` → `INTERNAL_ERROR` | 同上（目录） |
| `:394-398` | `except Exception` → `INTERNAL_ERROR` | 同上（写） |
| `:566-570` | `except Exception` → `INTERNAL_ERROR` | **含 §7.6(2) 的「已改还报错」** |
| `:739-743` | `except Exception` → `INTERNAL_ERROR` | 同上（批量） |

裸 `except:` 全仓只有 3 处，本文件占 2 处
（`grep -rn "except:" --include=*.py hello_agents/` → `react_agent.py:1055`、
`file_tools.py:189`、`file_tools.py:196`）。

## 7.8 两个与本项目直接相关的细节

**(1) 换行符会被静默改写。**
`grep -rn "newline=" --include=*.py hello_agents/tools/` → **0 命中**。
所有读写都用默认 `newline=None`，即启用 Python 的通用换行转换：
读时 `\r\n` → `\n`，写时 `\n` → `os.linesep`。
**在 Windows 上，一个 LF 结尾的文件被 Read 再 Write，会变成 CRLF。**

本项目 `AGENTS.md` 明确要求 `.gitattributes` 强制 LF 入库，
理由是「冻结文件的 SHA-256 必须跨平台稳定」（D-012 的物理保障）。
**任何照抄这套文件工具的做法都会直接破坏这个保障** ——
哈希会因为写入端的平台不同而变化。写工具必须显式 `newline=""` 或 `newline="\n"`。

**(2) `edits` 参数是 §2.2 那个 schema 谎言的实例。**
`MultiEditTool` 声明 `edits` 为 `type="array"`（`:630`），
描述里说「每项包含 old_string 和 new_string」（`:631`）——
即元素是 **object**。

但 `to_openai_schema`（`base.py:265-266`）对所有 array 一律输出
`"items": {"type": "string"}`。
**模型收到的 schema 说这是字符串数组，实际需要对象数组。**
唯一能纠正它的只有 description 里那句中文自然语言。
`:654` 的 `isinstance(edits, list)` 只校验外层是列表，
不校验元素形状；元素不是 dict 时 `:693` 的 `edit.get` 会 AttributeError，
落进 `:739` 的宽 except。

这是本轮找到的**「声明与实现不一致」最完整的一条闭环**：
schema 生成器撒谎 → 没有运行时校验（§2.3 `validate_parameters` 从不被调用）→
错误在深处以 AttributeError 形式爆发 → 被宽 except 压成一句
「批量编辑失败」。**四层里没有一层能指出真正的原因。**

---

# 八、`builtin/` 之三：`todowrite_tool.py`（387）与 `devlog_tool.py`（450）

这两个是「Agent 自我管理」类工具。对本项目的价值在于：
**`DevLogTool` 是框架自己的「决策记录」实现** —— 正好可以拿来对照
本项目 `DECISIONS.md` / 证据链要求。结论是**它不能用作审计记录**，理由见 §8.4。

## 8.1 `_validate_todos`：全 `tools/` 树里唯一一处像样的入参校验

`TodoWriteTool._validate_todos`（`todowrite_tool.py:262-304`）逐项检查：

| 行号 | 检查 |
|---|---|
| `:268` | `isinstance(todos_data, list)` |
| `:274-280` | `in_progress` 数量 ≤ 1 |
| `:283` | 每个元素 `isinstance(todo, dict)` |
| `:292` | `content.strip()` 非空 |
| `:298` | `status in ["pending","in_progress","completed"]` |

**这正是 §2.3 里 `validate_parameters` 本该做而没做的事。**
框架有能力做逐字段校验，只是**把它做成了某一个工具的私有方法，而不是协议层的公共能力**。
于是 14 个工具里只有这一个有真校验，其余全靠 `except Exception` 兜底。

> 这是本项目应当反过来做的：**校验放协议层，工具只声明约束。**
> 否则每个工具作者都要自己重写一遍，而绝大多数人不会写。

两个瑕疵：

- **枚举值硬编码了三份**：`:37`（dataclass 注释）、`:160`（给模型看的描述文本）、
  `:298`（真正生效的检查）。**没有共享常量**，三处可以各自漂移。
- `:292` 的 `content.strip()` 假定 `content` 是 str。
  传 `{"content": 123}` 会 AttributeError，
  被 `:256` 的宽 except 捕成 `INTERNAL_ERROR`，
  而不是它本该返回的 `INVALID_PARAM`。**校验器自己没被校验保护。**

## 8.2 `action` 参数名不副实，未知取值静默覆盖

描述宣称三个取值：`create|update|clear`（`todowrite_tool.py:169`）。
实现（`:187-254`）只特判了 `"clear"`（`:190`）。

**`create` 与 `update` 走的是完全相同的代码路径**，都执行 `:239`：

```python
self.current_todos = TodoList(summary=summary, todos=todos)
```

即**整体替换**。`action="update"` **不做任何合并**，语义与 `create` 无异。

更糟的是**没有 else 分支**：`action="delete"`、`action="append"`、拼错的任何值，
都会落到同一段替换逻辑上，**把整个任务列表覆盖掉**，并返回 SUCCESS。
`data["action"]` 还会把那个无效值原样回显（`:250`），看起来像是被接受了。

与 §5.2 的 `_create_tool_filter` 同一个毛病：**未知取值不报错，取最激进的默认行为。**

## 8.3 两处「同一秒内互相覆盖」的持久化

`_persist_todos`（`:335-362`）每次调用**新建一个带时间戳的文件**：

```python
timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")   # :337  秒级
filename = f"todoList-{timestamp}.json"                # :338
```

**秒级粒度。** ReAct 循环里 TodoWrite 往往被连续调用，
同一秒内的第二次写入产生**同名文件**，`temp_path.replace(filepath)`（`:362`）
直接覆盖 —— 中间那一版进度记录消失。
与 §7.5 `_backup_file` 完全同型的缺陷，在两个不同文件里各写了一遍。

另外这份持久化**只写不读**：`run()` 从不加载历史，
新建实例的 `current_todos` 恒为空（`:137`）。
提供了 `load_todos`（`:364-386`）但**框架内部无人调用** ——
`grep -rn "load_todos" --include=*.py .` → 5 命中，
分别是定义处 `:364`、两个 `examples/`（`todowrite_demo.py:195`、
`todowrite_real_world.py:211`）与一个测试（`tests/test_todowrite.py:278`、`:300`），
**`hello_agents/` 包内 0 命中**。

且 `load_todos` **完全没有异常处理**（`:370-381` 直接 `json.load` 与 `t["content"]` 下标），
与同文件其它路径的宽 except 风格相反 —— 缺键直接 KeyError 抛给调用方。

## 8.4 `DevLogTool`：框架版的「决策记录」，且它有三个硬缺陷

### (1) `except Exception: pass` + 固定文件名 = 静默数据销毁

`_load_if_exists`（`devlog_tool.py:437-449`）：

```python
if filepath.exists():
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.store = DevLogStore.from_dict(data)
    except Exception:
        # 加载失败，使用新的存储
        pass                                    # :449
```

这是本轮找到的**唯一一处标准 `except Exception: pass`**。

单看只是「加载失败就用空的」。**但要和 `_persist` 一起看**（`:425-435`）：

```python
filename = f"devlog-{self.session_id}.json"     # :427  固定名，不带时间戳
...
temp_path.replace(filepath)                     # :435  覆盖
```

**文件名是固定的。** 于是完整链条是：

1. 日志文件因任何原因损坏（磁盘、并发、手工编辑、schema 变更）
2. 构造时 `_load_if_exists` 静默失败，`store` 变成空的（`:258` 那个新建的）
3. 下一次 `append` 触发 `_persist`
4. **用只含 1 条记录的新 store 覆盖掉原文件**

**历史决策记录被永久销毁，全过程零提示。**
对一个自称「跨会话知识积累」（`:203`）的工具，这是最坏的失败模式：
**它在你最需要历史的时候，安静地把历史删掉。**

`DevLogStore.from_dict`（`:177-187`）用 `data["session_id"]` 等硬下标，
`DevLogEntry.from_dict`（`:66-69`）用 `cls(**data)` ——
**字段增删都会抛异常**，也就都会走到 `:449` 的 `pass`。
即**日志格式一旦演进，旧日志全部静默作废并被覆盖**。

附带：`:446` 从文件里恢复的 `store` 带着**文件里的** `session_id` 与 `agent_name`，
可能与构造函数传入的不一致，此后 `to_dict()` 写回的也是文件里那个。**身份会漂移。**

### (2) `ToolErrorCode.INVALID_PARAMETERS` 这个常量不存在

`devlog_tool.py:314`：

```python
return ToolResponse.error(
    code=ToolErrorCode.INVALID_PARAMETERS,      # :314
    message=f"未知操作：{action}"                # :315
)
```

**`errors.py` 里没有 `INVALID_PARAMETERS`，只有 `INVALID_PARAM`。**

验证：
`grep -c "INVALID_PARAMETERS" hello_agents/tools/errors.py` → **0**；
`grep -rn "INVALID_PARAMETERS" --include=*.py .` → **全仓 1 命中，就是 `devlog_tool.py:314` 这个使用处本身**
（定义处不存在）。

实际执行确认（本机 Python 直接构造同形类）：

```
AttributeError: type object 'ToolErrorCode' has no attribute 'INVALID_PARAMETERS'
```

所以 `:314` **必然抛 AttributeError**，被 `:318` 的 `except Exception` 接住，
返回的是：

> `INTERNAL_ERROR` / 「DevLog 操作失败：type object 'ToolErrorCode' has no attribute 'INVALID_PARAMETERS'」

**`:315` 那句「未知操作：xxx」永远不会被任何人看到。**
错误码从本该的「参数无效」变成「内部错误」，
消息从可操作的提示变成一句 Python 内部报错。

这条能长期存在，根因就是 §2.5 说的
**`ToolErrorCode` 是普通 class 而非 `Enum`，且 `is_valid_code` 从不在生产路径被调用**
—— 写错一个常量名，只有真的走到那一行才炸，而那一行是最冷的 else 分支。

### (3) `enum=[...]` 被 pydantic 静默丢弃 —— 声明了约束，约束不存在

`get_parameters`（`:263-297`）里两处给 `ToolParameter` 传了 `enum`：

```python
ToolParameter(
    name="action", type="string", description="...", required=True,
    enum=["append", "read", "summary", "clear"]        # :270
),
ToolParameter(
    name="category", type="string", description="...", required=False,
    enum=list(CATEGORIES.keys())                        # :277
),
```

**但 `ToolParameter` 根本没有 `enum` 字段。**
`base.py:41-47` 的五个字段是 `name/type/description/required/default`。
验证：`grep -c "enum" hello_agents/tools/base.py` → **0**。

`ToolParameter` 是 pydantic v2 `BaseModel`（本机 pydantic **2.10.6**），
默认 `model_config.extra` 为 **`ignore`**。实际执行验证：

```
构造成功，未报错
model_dump -> {'name':'action','type':'string','description':'d','required':True,'default':None}
有 enum 属性吗: False
```

**多余的 `enum` 关键字被静默吞掉，不报错、不警告、不出现在 `model_dump()` 里。**

后果链条完整：

1. 作者认为自己声明了取值约束
2. pydantic 丢弃它
3. `to_openai_schema`（`base.py:239-285`）遍历的是 `get_parameters()` 返回的对象，
   **拿不到 enum**，生成的 schema 里没有 `"enum"` 关键字
4. **模型从未收到过这个约束**，只能从 description 的自然语言里猜
5. 模型猜错 → 落到 `:312` 的 else → 撞上 (2) 的 `INVALID_PARAMETERS` → INTERNAL_ERROR

**(2) 与 (3) 是同一条故障链的两端**：约束没生效，而没生效时的错误处理也是坏的。

> 这条对本项目的意义最直接，也最该记进 `rules/failure-modes.md`：
> **「写下了约束」不等于「约束生效」。**
> 一个宽松的模型层（`extra='ignore'`）会把你写的约束安静地扔掉。
> 本项目所有 schema 模型必须设 `model_config = ConfigDict(extra="forbid")`，
> 让这类拼写与字段错误在**构造时**炸掉，而不是在模型猜错时才暴露。

## 8.5 `DevLogTool` 其余问题（较轻）

- **`generate_summary(limit=10)` 的 `limit` 是死参数。**
  `:144` 算出 `recent = self.entries[-limit:]`，
  但 `:160` 只用 `recent[-3:]`。传 100 还是 1 结果一样，永远显示 3 条。
- **`filter_entries(limit=0)` 返回全部。** `:119` `if limit and limit > 0`，
  `0` 为假直接跳过截断。请求「0 条」得到「全部」。
- **`_handle_read` 假定 `filter` 是 dict**（`:371-375`）。
  模型传字符串 → `.get` AttributeError → `:318` → INTERNAL_ERROR。
  `filter` 声明为 `type="object"`（`:293`）但无运行时校验（同 §2.3）。
- **`metadata` 完全不受约束**（`:349` 直接取、`:59` 原样存）。
  声明 `type="object"`（`:287`），实际任何类型都能进，
  最终 `json.dump`（`:433`）时若含不可序列化对象才炸。
- **日志内容无长度上限**，`_handle_read` 把全部命中条目的完整内容拼进 `text`（`:388-397`）。
  日志积累后单次 read 可以把上下文撑爆，且**没有 `PARTIAL` 降级**（同 §7.2）。
- **`_persist` 每次 append 都全量重写整个 JSON**（`:433` `json.dump(self.store.to_dict())`）。
  O(n) 写放大，且**任何一次写入中断都危及全部历史**（虽有 temp+replace 保护原子性）。

## 8.6 为什么 `DevLogTool` 不能当审计记录用

把它对照本项目 D-003「证据链是第一类产物」的要求，缺口与 §1.6 高度一致，
但多了两条**更致命**的：

| # | 缺口 | 具体表现 |
|---|---|---|
| A1 | **可被静默销毁** | §8.4(1)：损坏 → 静默失败 → 被覆盖。审计记录的第一要求是**不可丢失**，它连这个都不满足 |
| A2 | **可被任意改写** | 固定文件名（`:427`）、无哈希、无签名、无 append-only 约束。`grep -rni "hash\|sha" devlog_tool.py` 无相关命中 |
| A3 | 时间戳由本地时钟给 | `:56` `datetime.now().isoformat()`，无时区、无单调性保证 |
| A4 | `clear` 无留痕 | `_handle_clear`（`:411-423`）直接 `self.store.entries = []` 然后持久化，**不记录"曾经清空过"这件事** |
| A5 | 与 trace 无关联 | `DevLogEntry` 没有 session/step/tool_call_id 之外的关联字段，`metadata` 是自由 dict。**无法把一条决策与产生它的那次执行对上** |

**A4 单独就足以否决它。** 一个记录系统，如果「清空」这个动作本身不进记录，
那么「记录里没有」与「记录被清掉了」就无法区分 —— 这正是审计要防的。

> 本项目的对应约束：证据存储必须 **append-only + 内容寻址**，
> 删除只能是「写一条 tombstone」，不能是「把数组置空」。

---

# 九、`context/`（846 行）—— 上下文如何裁剪，裁掉的还能不能找回

> 本节带着本项目最关心的一个问题读：**上下文裁剪是否可逆？**
> 因为 finaudit-agent 有一条硬约束——「证据全文不能进上下文，但必须可独立复核」（D-003）。
> 一个框架如果把裁掉的原文丢了，它就不能作为这条约束的骨架参考；
> 如果它保住了原文，那就要看**保到哪一层、指针有没有传下去**。

## 9.1 结论先行

框架里有**两条完全独立、可逆性相反**的裁剪路径，作者似乎没有意识到它们是同一类问题：

| 路径 | 位置 | 裁什么 | 原文去哪了 | 可逆？ |
|---|---|---|---|---|
| **A. 工具输出截断** | `context/truncator.py` | 单次工具返回的长文本 | **写入磁盘 JSON**（`truncator.py:116`、`:152-182`） | **组件层可逆** |
| **B. 对话历史压缩** | `context/history.py` | 旧的历史消息 | **直接丢弃**（`history.py:144` 整体重新赋值） | **不可逆，原文销毁** |
| （C. GSSC 流水线） | `context/builder.py` | 一切 | 直接丢弃（`builder.py:192`、`:207-208`、`:289-296`） | 不可逆，且**整条流水线是死代码**（§9.9） |

**但路径 A 的可逆性在集成层被切断了。** 截断器返回的 `full_output_path`
在**唯一两个调用点上被丢弃**（`react_agent.py:847`、`react_agent.py:1224`
均只取 `truncate_result.get('preview', ...)`）。
全仓 `grep -rn "tool_output_dir|tool-output" --include=*.py hello_agents/` → **3 命中，全部是写侧配置**
（`truncator.py:54` 默认值、`core/agent.py:61` 传参、`core/config.py:38` 配置项），
**零处读回**。也就是说：**框架把完整输出写到了磁盘上，然后没有任何人知道它在哪。**

一句话结论：**这是反面案例，但不是「没想到要存」那种反面案例，而是更值得记的一种——
存了，机制也对，可是指针没有传下去，于是等价于没存。**
对本项目的意义见 §9.11 与文末「骨架启示」。

## 9.2 模块结构与实际接线

```
context/__init__.py       26   导出 6 个名字（:18-25）
context/builder.py       307   ContextBuilder / ContextConfig / ContextPacket —— GSSC
context/history.py       168   HistoryManager
context/truncator.py     183   ObservationTruncator
context/token_counter.py 162   TokenCounter
```

`__init__.py:1-11` 的模块 docstring 列了 **7 个组件**，实际只实现了 4 个：
`Compactor`、`NotesManager`、`ContextObserver` 三个在 docstring 里（`:8`、`:9`、`:10`）但仓库里不存在。
核验：`grep -rn "class Compactor|class NotesManager|class ContextObserver" --include=*.py .` → **0 命中**。
（与 §1.11「文档与代码已经漂移」同类。）

实际接线（`grep -rn "ContextBuilder|HistoryManager|ObservationTruncator|TokenCounter" --include=*.py .`）：

| 类 | 被谁用 | 是否进主链路 |
|---|---|---|
| `HistoryManager` | `core/agent.py:49`、`:52`（构造）+ 12 处调用 | **是** |
| `ObservationTruncator` | `core/agent.py:50`、`:57`（构造）；`react_agent.py:843`、`:1220`（调用） | **部分**，见 §9.4 |
| `TokenCounter` | `core/agent.py:65`、`:66`、`:308`、`:326`、`:363` | **是** |
| `ContextBuilder` / `ContextConfig` / `ContextPacket` | **只在 `context/` 包内部出现（6 处，含 docstring 与 `__all__`）** | **否 —— 包外零消费者**（§9.9） |

## 9.3 路径 A：`ObservationTruncator` —— 组件层的设计是对的

`truncate()`（`:72-130`）的返回形状值得记，因为它正好是本项目要的形状：

```python
# truncator.py:118-130
return {
    "truncated": True,
    "preview": preview,              # 进上下文的
    "full_output_path": output_path, # 不进上下文、但可复核的
    "stats": {...}                   # 裁了多少
}
```

`_save_full_output`（`:152-182`）把原文完整写成 JSON：
`{"tool", "output", "timestamp", "metadata"}`（`:172-177`），
文件名 `tool_{%Y%m%d_%H%M%S_%f}_{tool_name}.json`（`:168-169`）。
带微秒，**不会像 `DevLogTool`（§8.4(1)）和 `TodoWrite`（§8.3）那样同秒互相覆盖**——
这是本仓库全部持久化写法里唯一一处把时间戳精度做对的地方。

写文件处 `:179-180` **没有 try/except**，失败会向上抛。就组件本身而言这是 fail-loud，正确。
（但抛到调用点会被吞，见 §9.4(3)。）

**它与「证据链」还差什么**（对照 D-003）：

| 缺口 | 依据 |
|---|---|
| 无内容哈希 | `grep -n "hash|sha|digest" hello_agents/context/truncator.py` → **0 命中**。文件写完就是一份普通拷贝，改了看不出来 |
| 无调用关联 | `data` 里只有工具名和时间（`:172-177`）。没有 `tool_call_id` / `step` / `session_id`，**无法把这份原文与产生它的那次调用对上** |
| 时间戳有两个且不一致 | `:168` 生成文件名的 `datetime.now()` 与 `:175` 写进内容的 `datetime.now()` 是**两次独立调用**，可以差若干毫秒；均无时区 |
| 目录只写不读 | 见 §9.1 的 grep |

## 9.4 路径 A 的断点：可逆性在集成层被丢掉（本节最重要）

`grep -c "self.truncator.truncate" hello_agents/agents/react_agent.py` → **2**，
且这 2 处是**全仓仅有的两处**截断调用。两处写法逐字相同：

```python
# react_agent.py:843-847（异步工具路径） 与 :1220-1224（异步流式路径）
truncate_result = self.truncator.truncate(
    tool_name=tool_name,
    output=result_content
)
result_content = truncate_result.get('preview', result_content)
```

四个问题，逐条：

**(1) `full_output_path` 被丢弃。** 返回字典里唯一能让原文重新被找到的字段，
在 `:847` / `:1224` 这一行之后就永久离开了程序。
下一行（`:852-861`）写 trace 时记的是 `"result": result_content`——**记的是预览，不是路径**。
于是 trace 里留下一段被砍过的文本，磁盘上留下一份没人认领的原文，两者之间没有任何链接。

**(2) `metadata` 没传。** `truncate()` 的第三参数（`truncator.py:76`）留了元数据口子，
两个调用点都没用。而**同一作用域里 `tool_call_id` 是有的**（`:857` 就在用它写 trace），
只要多传一个 `metadata={"tool_call_id": tool_call_id}` 就能建立关联——**没传**。
这不是能力不足，是接线时漏了。

**(3) 截断失败会被记成「工具执行失败」。** `:838-849` / `:1215-1226`：

```python
try:
    tool_response = await tool.arun_with_timing(arguments)
    result_content = tool_response.text
    truncate_result = self.truncator.truncate(...)   # 磁盘满 / 目录只读 → 抛在这
    result_content = truncate_result.get('preview', result_content)
except Exception as e:
    result_content = f"❌ 工具执行失败: {str(e)}"     # ← 归因到工具头上
```

工具跑成功了、结果也拿到了，仅仅是**存证失败**，模型收到的却是「工具执行失败」。
`truncator.py:179` 那个正确的 fail-loud，到这里变成了**错误归因的静默降级**。
这是 §4.3 记的「静默降级四种形态」之外的第五种：**把 B 的失败报成 A 的失败。**

**(4) 六个工具执行点里只有 2 个走截断。** `_execute_tool_call`（`core/agent.py:647-700`）
是**同步**工具路径，全仓四个 Agent 都在用它——
`simple_agent.py:225`、`reflection_agent.py:276`、`plan_solve_agent.py:246`、`react_agent.py:338`——
而 `grep -n "truncat" hello_agents/core/agent.py` 在 `:647-700` 区间 **0 命中**。
所以 `truncator.py:4` 那句「统一截断工具输出（避免每个工具自己实现）」，
实际覆盖率是 **2/6 调用点、1/4 Agent、且只在该 Agent 的异步分支上**。
其余四条路径把工具原始输出**未经任何长度限制**直接拼进上下文。

## 9.5 截断器自身的两个真实缺陷（已实测复现）

**(1) `max_bytes` 是装饰性的。** `:97` 的判断是「行数 ≤ max_lines **且** 字节 ≤ max_bytes」，
但真正执行裁剪的 `_truncate_lines`（`:132-150`）**只按行裁，完全不看字节**。
于是「行数不超、字节超标」的输入（一个长 JSON、一段无换行的 PDF 抽取文本）会：
进入截断分支 → `lines[:2000]` 原样返回 → `preview == output`。

实测（复刻 `:97` + `:141-142` 的逻辑，纯字符串运算）：
```
单行 60000 字节: len(lines)=1<=2000 但 bytes=60000>51200 -> 进入截断分支
  head 截断后 preview 字节=60000, 原始字节=60000, 相等? True
```
结果是 `truncated: True` 而 `kept_bytes == original_bytes`（`:125` vs `:127`），
**统计块自己就自相矛盾**，60KB 原样进了上下文。
对本项目直接相关：**年报 PDF 抽出来的表格文本经常是超长少换行的**，正好命中这条。

**(2) `head_tail` 会把内容放大。** `:145-147`：
```python
half = self.max_lines // 2
return lines[:half] + ["...(中间省略)..."] + lines[-half:]
```
没有 `len(lines) > max_lines` 的前置检查。当因**字节**超标而进入截断、行数却远小于 `max_lines` 时，
`lines[:1000]` 与 `lines[-1000:]` 是**同一批行**，结果被复制两遍。
实测：`原始 10 行 -> 截断后 21 行, 放大 2.1x`。
一个名为「截断」的函数，在这条路径上让上下文**变大一倍**。

## 9.6 路径 B：`HistoryManager.compress()` —— 不可逆，且默认摘要不含任何内容

这是本节要给本项目留的**反面案例**。两段代码一起看：

```python
# context/history.py:136-144
summary_msg = Message(
    content=f"## Archived Session Summary\n{summary}",
    role="summary",
    metadata={"compressed_at": datetime.now().isoformat()}
)
self._history = [summary_msg] + self._history[keep_from_index:]
```

`:144` 是一次整体重新赋值。`self._history[:keep_from_index]` 那批原文
**没有被写到任何地方**——没有归档文件、没有路径指针、没有条数以外的任何痕迹。
`metadata`（`:140`）只记了「什么时候压的」，**没记「压掉了什么」「压掉了几条」「原文在哪」**。

`grep -n "path|save|dump|archive|open(" hello_agents/context/history.py` → **0 命中**。
同一个包里 `truncator.py` 明明写了落盘（`:179`），`history.py` 一行都没有。
**同一模块内两条裁剪路径，一条存原文一条不存，且没有任何注释解释这个差异。**

**更严重的是默认摘要的内容。** 驱动方在 `core/agent.py:344-359`：

```python
# core/agent.py:352-359
if self.config.enable_smart_compression:
    summary = self._generate_smart_summary(history)
else:
    summary = self._generate_simple_summary(history)   # ← 默认走这条
self.history_manager.compress(summary)
```

而 `_generate_simple_summary`（`core/agent.py:365-383`）返回的是：

```
此会话包含 {rounds} 轮对话：
- 用户消息：{user_msgs} 条
- 助手消息：{assistant_msgs} 条
- 总消息数：{len(history)} 条
（历史已压缩，保留最近 {min_retain_rounds} 轮完整对话）
```

**一个字的内容都没有，全是计数。**
所以在默认配置下，「压缩」这个动作的净效果是：
**把 N 条真实对话原地换成一句「这里曾经有 N 条对话」，原文销毁，不可恢复。**

这比「摘要有损」严重一个量级——它不是压缩，是**带回执的删除**。

> 与 §8.6 A4（`DevLogTool` 的 `clear` 不留痕）是同一个病：
> 记录系统里「内容没有」与「内容被清掉了」不可区分。
> 区别在于 `DevLogTool` 至少不假装自己压缩过；这里还留了一句「已压缩」当说明。

**智能摘要路径也不可逆，只是有损得体面些。** `_generate_smart_summary`（`core/agent.py:385-455`）
调 LLM 生成结构化摘要，但：
- `_format_history_for_summary`（`:457-472`）在送进 LLM 前**每条消息先砍到 500 字符**（`:469`），
  所以摘要是基于被砍过的输入生成的——**二次损失，且这一层的丢弃同样无记录**；
- `:452-455` 摘要失败 → `print` 警告 → **回退到上面那个纯计数摘要**。
  即「智能压缩」失败时行为退化成「删除并留回执」，调用者只会在 stdout 看到一行 ⚠️。

**docstring 与实现相反。** `history.py:19` 写「只追加，不编辑（缓存友好）」，
`:61` 再写一次「追加消息（只追加，不编辑）」。
但同一个类里 `compress()`（`:144`）整体重写列表、`clear()`（`:78`）清空列表。
**声称的 append-only 性质被同一个类的另外两个方法证伪。**

## 9.7 压缩产出的那条消息，三家 API 三种错法

`compress()` 造出的是 `role="summary"`（`history.py:139`）。
`MessageRole` 确实允许它（`core/message.py:7` 的 `Literal` 含 `"summary"`），
但**没有任何一层把它映射回三家 API 认识的角色**。
`grep -rn '"summary"' --include=*.py hello_agents/` → 12 命中，
除 `message.py:7` 声明与 `history.py:139` 构造外，其余全是 `devlog_tool` / `todowrite_tool` 里
同名但无关的字段，**零处角色映射**。

历史送进 LLM 的地方（`simple_agent.py:284`、`:349`、`:401`，`reflection_agent.py:339`）
一律是 `{"role": msg.role, "content": msg.content}` 原样透传。于是：

| 提供商 | 代码位置 | `role="summary"` 的实际下场 |
|---|---|---|
| OpenAI 方言 | 适配器内**无任何角色处理** | 原样发出 → **API 400 非法 role** |
| Anthropic | `llm_adapters.py:394-395` `else: converted_messages.append(msg)` | 原样发出 → **API 400** |
| Gemini | `llm_adapters.py:649` `role = "model" if msg["role"] == "assistant" else "user"` | **静默改成 `user`** —— 摘要被当成「用户说的话」喂回模型 |

前两家是压缩后**下一次调用就崩**；第三家**不崩，但把系统生成的摘要伪装成用户输入**——
后者更危险，因为它把会话推进了「模型以为用户确认过这些事实」的状态。
对本项目：**任何自动生成、又要回流进上下文的文本，必须携带不可伪装的来源标记；
靠一个自定义 role 值来承载来源，会在跨供应商的映射层被抹掉。**

## 9.8 `TokenCounter`：一个不可能触发的降级 + 对中文的系统性低估

**(1) 声明了、但永远不会触发的降级。** docstring 两处（`:7`、`:22`）都写
「降级方案（tiktoken 不可用时使用字符估算）」，
而 `:10` 是**模块顶层无保护的 `import tiktoken`**。
`grep -rn "import tiktoken" --include=*.py hello_agents/` → 2 命中（`token_counter.py:10`、`builder.py:15`），
**均无 try/except**；`requirements.txt:10` 与 `pyproject.toml:23` 都硬声明 `tiktoken>=0.5.0`。
所以「tiktoken 不可用」时 **`import hello_agents` 整个就失败了**，
`:135-137` 那个字符估算分支根本到不了。

> 这与 `core/` 篇 §4.1 记的「两个永远不会正确触发的 flag」是同一物种，
> 也正是本项目 `rules/failure-modes.md` 第 2 条要防的东西。
> 这里更微妙一点——降级分支本身写得没错，错的是**它的前置条件已被顶层 import 排除**。
> 识别方法：写下降级分支后，问一句「让它触发的那个世界，程序还活着吗？」

真正能走到 `:128` 的 `else` 只有一种情况：`tiktoken` 装了、但 `get_encoding("cl100k_base")`
也抛异常（`:60-63`），即离线且无缓存 BPE 文件。**那才是这个降级的真实触发条件，而 docstring 没写。**

**(2) 中文估算偏差。** `:134` 与 `:137` 的降级都是 `len(text) // 4`。
这个「1 token ≈ 4 字符」的经验值来自英文；中文在 `cl100k_base` 下大致 **1 字符 ≈ 1～1.5 token**。
一旦落到降级路径，中文文本的 token 数会被**低估约 4～6 倍**。
而 `_should_compress()`（`core/agent.py:341-342`）正是拿这个数与阈值比——
低估意味着**该压缩时不压缩**，直到真正发请求时被 API 拒。
本项目的语料是中文年报，这条不是理论风险。

**(3) 两个计数器，口径不同，同时在用。**
- `TokenCounter.count_message`（`:82-106`）：`encoding_for_model(model)` + **每条 +4**（`:101`）+ 缓存
- `builder.py:299-306` 的模块级 `count_tokens`：**恒用 `cl100k_base`**、不 +4、不缓存

同一段文本经两者得到不同的数，而框架里两者都在用（`core/agent.py` 用前者，`builder.py` 用后者）。

**(4) 缓存无上限、键里存了全文、无淘汰。** `:92` `cache_key = f"{message.role}:{message.content}"`，
`:104` 无条件写入。`grep -n "clear_cache" hello_agents/core/agent.py` → 仅 `:326`（`clear_history` 里）。
长会话中缓存持有**每一条历史消息的完整正文**，即使 `HistoryManager.compress()`
已经把它们从历史里删掉了。

> 这里有个反讽值得记：**被「压缩」掉的原文，唯一残留的副本在 token 计数器的缓存键里。**
> 它在内存里、没有读取 API、不可枚举（只能拿已知全文去命中），
> 所以既当不了证据，又实实在在把「已删除」的文本留在了进程里。
> **对合规是负债，对可复核是零资产**——两头不占。这是「半可逆」最糟的形态。

**(5) `count_text` 与 `count_message` 不等价。** `:108-117` 的公开 `count_text` 不加那 +4、也不入缓存。
`counter.count_text(msg.content) != counter.count_message(msg)`，差值恒为 4，无处说明。

**(6) `get_cache_stats()["total_cached_tokens"]`（`:160`）把缓存里所有历史条目求和**，
它既不是当前上下文的 token 数，也不是累计消耗，**不对应任何真实量**。
（同 §1.9(3) `total_cost` 恒为 0 的「假指标」家族。）

## 9.9 `ContextBuilder` / GSSC 流水线：整条是死代码，且对中文恒为空

**先说接线**：`grep -rn "ContextBuilder" --include=*.py .` → **6 命中，全部在 `hello_agents/context/` 包内**
（`builder.py:1` docstring、`:52` 类定义、`:59` 用法示例；`__init__.py:4` docstring、`:13` import、`:19` `__all__`）。
**排除该包自身后，全仓外部命中 = 0**：不在 `core/`、不在 `agents/`、不在 `tests/`、不在 `examples/`。
类 docstring `:55` 自己也写了「MemoryTool 和 RAGTool 已被移除，此类暂时不可用」——
**但 `__init__.py:18-21` 仍把它连同 `ContextConfig`、`ContextPacket` 作为公开 API 导出**。

即便如此，它的**结构**对本项目有参考价值（`_structure` 分了
`[Role & Policies] / [Task] / [State] / [Evidence] / [Context] / [Output]` 六段，`:214-267`），
所以仍逐行读了。读出来的问题如下。

**(1) `[Evidence]` 段与其它段走同一条有损流水线，没有任何豁免。**
`:241-249` 收的是 `type ∈ {related_memory, knowledge_base, retrieval, tool_result}` 的包。
这些包要先过 `:192` 的 `min_relevance` 过滤、再过 `:206-210` 的预算填充、
最后过 `:269-296` 的整体截断。**三道关卡，每一道都可能把证据整段丢掉，且三道都不留记录。**
唯一被豁免的是 `type == "instructions"`（`:187`、`:200-203` 固定纳入）。
对照本项目：**证据是唯一不能被相关性打分裁掉的东西，这里它恰恰是可以的。**

**(2) 相关性打分对中文恒为 0 —— 全部中文证据都会被丢弃。**
`:164-169`：
```python
query_tokens = set(user_query.lower().split())
content_tokens = set(packet.content.lower().split())
overlap = len(query_tokens & content_tokens)
packet.relevance_score = overlap / len(query_tokens)
```
`str.split()` 按空白切分。中文不用空格分词，**整段中文会被切成 1 个 token**，
与查询的交集除非两个字符串完全相同否则恒为 0。

实测（复刻 `:164-169`，纯字符串运算，未 import 框架）：
```
中文: query_tokens=1 relevance=0.0000  >= min_relevance(0.3) ? False
英文: query_tokens=7 relevance=0.7143  >= min_relevance(0.3) ? True
```
用的是「贵州茅台2023年的销售毛利率是多少」+ 一段含答案的中文年报摘录：**相关性 0.0**。
在默认 `min_relevance=0.3`（`:41`）下，`:192` 会把**每一个中文包**过滤掉，
`_select` 只剩系统指令。最终上下文里没有 `[Evidence]`、没有 `[Context]`，
**而且不会报错、不会警告**——`_structure` 的 `if p2_packets:`（`:245`）为假就是不生成那一段。

**这是本节对本项目最直接的一条警示**：不是「中文效果差一点」，是**恒为空且静默**。
任何基于英文空格分词做相关性 / 去重 / 关键词命中的组件，进中文语料前必须先证伪这一条。

**(3) `enable_mmr` / `mmr_lambda` 是完全没接线的开关。**
`grep -rn "mmr" --include=*.py .` → **2 命中**，全部在 `builder.py:42-43` 的字段声明上。
`_select` 里没有任何多样性计算。**声明了 MMR，实现里一行都没有。**
（同 §1.9(4) 的 `html_include_raw_response`。）

**(4) 新近性算了但不参与筛选。** `:174-184` 算出复合分 `0.7*相关性 + 0.3*新近性`，
`:188` 用它排序；但 `:192` 的过滤用的是 `p.relevance_score`（**原始相关性**），不是复合分。
所以新近性只影响顺序、从不影响去留。又，`_gather` 里现造的包（`:131`、`:147`）
`timestamp` 默认 `datetime.now()`（`:25`），`recency_score` 对它们恒 ≈ 1.0，
这一项对同批次内的包**是个常数**。

**(5) 预算只管 packet，不管模板。** `:195-210` 按 `available_tokens` 填充，
但 `_structure` 之后又加了段标题、`[Task]`（`:231`）和一段缩进的 `[Output]` 模板（`:259-264`），
**这些都不在预算内**。于是结构化之后大概率超预算，触发 `_compress`。

**(6) `_compress` 是无标记的行截断，且丢弃发生在尾部。**
`:285-296` 从头逐行累加，超预算就 `break`，**丢掉的部分连一个「…」都不留**
（`truncator.py:147` 至少还有个「...(中间省略)...」）。
由于 `[Output]` 是最后一段（`:265`），**第一个被砍掉的就是输出格式约束**。
即：一超预算，模型就悄悄不再被要求「列出支撑证据及来源」。
`:282` 只 `print` 一行 ⚠️，不抛异常、不写 trace、不进返回值。

**(7) `_compress` 每行都重建一次编码器。** `:290` 逐行调 `count_tokens`，
而 `count_tokens`（`:302`）每次调用都执行 `tiktoken.get_encoding("cl100k_base")`。
一份 5000 行的上下文 = **5000 次编码器构造**。
与此同时 `__init__` 里 `self._encoding = tiktoken.get_encoding("cl100k_base")`（`:76`）
**被赋值后全文再无引用**（`grep -n "_encoding" builder.py` → 只有 `:76` 与 `:302`，后者是局部变量）。

**(8) `:206-210` 用 `continue` 而非 `break`。** 装不下的包跳过，继续尝试后面分数更低但更小的包。
行为上未必错，但结果是**最终入选集合与分数序不一致**，而没有任何地方记录「谁因为装不下被跳过」。

## 9.10 本节错误处理与静默降级清单（逐处，带行号）

| # | 位置 | 形态 | 后果 |
|---|---|---|---|
| C1 | `truncator.py:97` vs `:141-150` | 判据看字节，执行只看行 | `max_bytes` 形同虚设，超大单行原样进上下文 |
| C2 | `truncator.py:145-147` | 缺 `len(lines) > max_lines` 前置检查 | `head_tail` 把内容放大 2.1x（实测） |
| C3 | `react_agent.py:847`、`:1224` | 丢弃 `full_output_path` | **原文写了盘，指针没了 = 等价于没存** |
| C4 | `react_agent.py:848`、`:1225` | `except Exception` 把存证失败报成工具失败 | 错误归因；模型以为工具坏了 |
| C5 | `core/agent.py:647-700` | 同步工具路径不接截断器 | 4/6 调用点无任何长度约束 |
| C6 | `history.py:144` | 整体重新赋值，旧消息不落盘 | **原文销毁，不可逆** |
| C7 | `core/agent.py:365-383` | 默认摘要只有计数、无内容 | 「压缩」= 带回执的删除 |
| C8 | `core/agent.py:452-455` | 智能摘要失败 → `print` + 回退到 C7 | 失败路径静默退化为删除 |
| C9 | `core/agent.py:469` | 摘要前每条砍到 500 字符 | 二次有损，无记录 |
| C10 | `history.py:139` + `llm_adapters.py:649` | `role="summary"` 在 Gemini 路径被改成 `user` | 系统摘要伪装成用户发言 |
| C11 | `llm_adapters.py:394-395`（Anthropic）/ OpenAI 无处理 | `role="summary"` 原样发出 | 压缩后下一次调用 API 400 |
| C12 | `token_counter.py:10` + `:135-137` | 顶层硬 import + 声称的降级 | 降级分支**不可达**，docstring 与现实相反 |
| C13 | `token_counter.py:58-66` | 三层 `except` 静默返回 `None` | 精确计数悄悄变成 `len//4` |
| C14 | `token_counter.py:104` | 缓存无上限、键含全文、无淘汰 | 被「压缩掉」的原文残留在进程内存里 |
| C15 | `builder.py:164-169` | 英文空格分词打分 | **中文相关性恒 0 → 证据全被静默丢弃**（实测） |
| C16 | `builder.py:42-43` | `enable_mmr` 无实现 | 假开关 |
| C17 | `builder.py:192` | 过滤用原始相关性，不用复合分 | 新近性从不影响去留 |
| C18 | `builder.py:282-296` | 超预算 `print` + 无标记行截断 | `[Output]` 约束最先消失，无痕 |
| C19 | `builder.py:302` | 逐行重建编码器 | O(n) 次 `get_encoding` |
| C20 | `context/__init__.py:8-10` | docstring 列了 3 个不存在的类 | 文档漂移（grep 0 命中） |

## 9.11 对照 D-003：这一节能给本项目什么

把 §9 的两条路径摆在 D-003「证据链是第一类产物，不是日志」旁边：

| D-003 的要求 | 路径 A（工具截断） | 路径 B（历史压缩） |
|---|---|---|
| 原文可独立复核 | **机制有**（`truncator.py:116`），**指针丢**（`react_agent.py:847`） | **无** |
| 内容寻址 / 防篡改 | 无（grep `hash|sha` → 0 命中） | 无 |
| 与执行关联（call_id / step） | **有口子没接线**（`truncator.py:76` 空着，`react_agent.py:857` 手边就有 id） | 无 |
| 删除留痕 | 不适用（不删） | **无**（`history.py:144` 直接覆盖） |
| 裁剪量可审计 | **有**（`stats`，`:122-129`），但在 C1 下自相矛盾 | 只有「N 条」这个数 |

最值得带走的一句：**路径 A 证明「先落盘、再把指针放进上下文」这个形状可行且轻量（30 行代码）；
路径 A 的断点证明「指针必须是被下游强制消费的，否则一定会在接线时丢掉」。**
本项目对应的做法见文末「骨架启示」B-1 与 B-2。

---

# 十、对 finaudit-agent 的骨架启示

> **本节遵守 `references/README.md` 第 3 条（2026-08-22 新增）：
> 每条必须写明落地点。只有「未落地」是允许的第二种答案，「读过了」不是。**
> 编号沿用现有权威文档；标「未落地」的条目一并写出**它应该落到哪里**。
> 现有决策编号到 `D-021` 为止，因此下面提到的新增决策一律记作「下一可用编号 D-022 起」，
> **不是已存在的编号**。
>
> 范围限定：本节只从本文档实读的 `tools/` `context/` `observability/` `skills/` 得出结论；
> `core/` `agents/` 的启示见另一份文档同名章节。

## 10.1 该借鉴的

### A-1　「preview 进上下文 + 全文落盘 + stats 记裁剪量」这个三件套

**依据**：`truncator.py:118-130`（§9.3）。三十行代码就做出了本项目最需要的形状——
**上下文里放摘要，磁盘上放全文，返回值里放「裁了多少」**。
本项目「证据全文不能进上下文但必须可复核」的问题，骨架就是这个。

**落地点：~~未落地~~ → **部分落地 2026-08-27**（登记册 **`L-70`**）：`truncation_stats` 与 `PARTIAL` 的双向绑定已落进 `record.ExtractionRecord.__post_init__`；**「全文落盘」那一半未做** —— 抽取器目前没有任何由系统自主决定路径的写盘，落盘语义由 `D-027` 定死，触发时点见该条判据 1。
应落到 **`PROJECT_SPEC.md` §5（架构）证据链字段集**，作为 `AC-05`「字段齐全率 100%」
所要求的固定字段之一：任何被截断的证据，其证据链条目必须同时含
`preview` / `full_ref` / `truncation_stats` 三者，缺一即判 AC-05 不达标。
注意与 **`SC-4`**（抽取产物带出处：SHA-256 + 巨潮 URL + 页码 + 单位币种）的关系——
`SC-4` 记的是「一条被抽取的报表行」的出处，A-1 记的是「一次回答里被截断的证据」的出处，
**粒度不同，不能互相替代**（这条边界 `01.5-RESEARCH.md:161` 已经划过，此处沿用）。

### A-2　指针必须被下游强制消费，否则一定丢

**依据**：§9.4(1)。框架**做对了存证**（`truncator.py:116`），却在唯一两个调用点
（`react_agent.py:847`、`:1224`）只取 `preview`、扔掉 `full_output_path`，
于是磁盘上躺着一份没人认领的原文，`tool-output/` 目录全仓**零处读回**。
**这是本轮最值得带走的一条**：可复核性不是靠「有没有存」保证的，是靠
**「不消费指针就编译不过 / 跑不通」** 保证的。

**落地点：已落地（同型），但需扩展。**
`ARCHITECTURE.md §8.1` 已经确立同一原理的另一半——
「闸门放进**调用签名**，绕过闸门在类型上不可表达」。
A-2 是这条原理在**证据侧**的镜像：**证据引用也要放进返回类型，让「丢掉引用」在类型上不可表达。**
具体做法：截断后的返回值不得是 `str`，必须是一个携带 `full_ref` 的封闭结构，
且下游把它转成上下文文本的函数**必须同时接收 evidence sink**。
**需要新增一条决策把这半边写死**（下一可用编号 D-022 起），
理由与 `ARCHITECTURE.md §8.1` 第 1、4 条同源：只要它是「链条上的一环」，就可被绕过、可被静默跳过。

### A-3　三态返回协议：`SUCCESS / PARTIAL / ERROR`

**依据**：`tools/response.py`（§2.4）。协议本身设计得好，是全仓少数值得直接抄的东西。
但框架自己**定义了 `PARTIAL` 却几乎不用**——`file_tools.py` 把截断报成 `SUCCESS`（§7.2），
`devlog_tool` 的长输出也不降级（§8.5）。

**落地点：~~未落地~~ → **已落地 2026-08-27**（登记册 **`L-45`**）：`record.ExtractionRecord.__post_init__` 里 `PARTIAL` 与 `truncation_stats` 的**双向**绑定校验 —— 报 `SUCCESS` 却带非空 `truncation_stats`、或报 `PARTIAL` 却带空 `truncation_stats`，两个方向都构造失败。
应新增一条决策（D-022 起）写死：**「被截断」必须报 `PARTIAL`，不得报 `SUCCESS`。**
这条与 `AC-05` 直接挂钩——如果截断被报成成功，证据链里就不会出现 `truncation_stats`，
`AC-05` 的「字段齐全率 100%」会在一个假成功上判过。
同时与 `ARCHITECTURE.md §8.2`（`Refusal` 必须是封闭枚举）配套：
**三态是「结果的封闭枚举」，`Refusal` 是「拒绝理由的封闭枚举」，两者不能用自由文本代替。**

### A-4　`run_with_timing` 把入参记进 context

**依据**：`tools/base.py`（§2.6）。它给出了一个**不侵入工具实现**就能拿到
「这次调用用了什么参数」的钩子位置——这正是证据链里「执行了什么」那一栏的来源。

**落地点：~~未落地~~ → **已落地 2026-08-27**（登记册 **`L-55`**）：`extractor/pipeline.py` 的 `_stamp_provenance` 是全包**唯一**采集点，由 `tests/test_record.py::test_留痕采集点唯一` 用 AST 守着 —— `locate` / `mapping` / `record` 连 import 都没有。
应落到 **`PROJECT_SPEC.md` FR-05**（「执行前静态校验，执行后哈希留痕」）的实现说明：
留痕的**采集点**放在这个包装层，不放在每个工具内部。
理由与 §9.4(4) 实测到的教训一致——框架把截断放在调用点，结果 6 个调用点只覆盖了 2 个；
**凡是要求「每次都做」的事，就不能放在调用点。**

### A-5　入参校验要在边界上真的跑，而不只是定义

**依据**：§2.3 —— `tools/base.py` 写了参数校验函数，但**全仓一次都没被调用**；
§8.1 —— `_validate_todos` 是全 `tools/` 树里唯一一处真正执行的入参校验。
一个框架里「写了校验」与「校验会跑」是两件事。

**落地点：已落地。**
`D-018`（勾稽校验是批次级闸门；fail-closed 放在**计算层的读入边界**）就是这条的本项目版本，
且 `D-018` 选的位置（读入边界而非写入侧）恰好避开了框架踩的坑。
`ARCHITECTURE.md §8.4` 已复述该理由。**本节不新增约束，只补一条源码级旁证。**

### A-6　扩展点的能力边界要写死在「能提供什么」上

**依据**：§6.2 —— skill 只能提供**文字**，不能提供**代码**；`skill_tool.py` 是纯文本注入，
不执行任何东西（§5.3）。这个边界画得干净：扩展者能改变模型看到什么，不能改变进程执行什么。

**落地点：已落地。**
`D-017`（`formula` 的数值执行层自建封闭算术解析器，`eval()` 硬性排除）是同一条原理：
**外部提供的是待解释的数据，不是待执行的代码。**
框架的 `calculator.py`（§5.1）也走了自建求值器而非 `eval` 的路线，**与 D-017 选择一致**——
这是本轮唯一一处「框架的做法与本项目既有决策正面互证」的地方。
（但框架的数值语义本身有问题，见 §5.1，那部分不借。）

### A-7　时间戳精度决定持久化会不会互相覆盖

**依据**：`truncator.py:168` 用 `%Y%m%d_%H%M%S_%f`（带微秒），是全仓唯一做对的；
而 `DevLogTool`（§8.4(1)）与 `TodoWrite`（§8.3）用固定名或秒级名，**同秒内第二次写覆盖第一次**。
一个证据文件被覆盖，和没写过没有区别。

**落地点：~~未落地~~ → 已落地 2026-08-26**（登记册 **`L-71`**，`ARCHITECTURE` **§8.5.7**）。
**实际落点不是 `SC-4`**：`SC-4` 住在 `.planning/phases/01.5-*`，那是阶段成功标准、
不是跨阶段约束，把存储语义写进去会让它只在这一个阶段成立。
§8.5.7 把本条与 `FT-B7`（`DevLogTool` 的 `clear` 不留痕）合成三条约束：
**内容寻址 + append-only + 删除只写 tombstone**。
以下为原文，保留不改：
应落到 **`SC-4`** 的实现约束里：出处记录的落盘命名**必须内容寻址**（用内容 SHA-256 前缀），
**不用时间戳**——比微秒更强，且天然幂等。
`SC-4` 目前只要求「带出处」，没写「出处怎么存不会互相覆盖」，这是个真实缺口。

### A-8　「同一秒 / 同一批」的边界要显式，别靠隐式假设

**依据**：§8.3 两处「同一秒内互相覆盖」的持久化。
框架的错不在于没想到并发，而在于**把「不会同时发生」当成了默认前提**。

**落地点：已落地（同型）。**
`D-018` 把勾稽校验定为**批次级**闸门，正是把「批」这个边界显式写出来的做法。
本条不新增约束，作为 `D-018` 「为什么必须显式声明批次」的一条外部旁证记录。

## 10.2 该刻意不借的（每条必须写理由）

> `references/README.md` 第 4 条：**偏离通用做法而不写理由，下一个人会以为是疏漏然后「修好」它。**

### B-1　不借：`HistoryManager.compress()` 式的「压缩」

**框架怎么做**：`history.py:144` 一次整体重新赋值，被压缩的原文**不写任何地方**（§9.6）。

**本项目不借的理由**：这不是压缩，是**带回执的删除**。
`D-003` 要求「给不出证据链的回答判为失败，不判为降级成功」——
而这种压缩会制造一种特别难发现的失败：**回答看起来有据可依，但依据已经不存在了**。
`AC-06`（复核者仅凭证据链 5 分钟内独立判断对错）在这种状态下**结构上不可能通过**：
复核者点进去，原文没了。

**落地点：已落地（`rules/pitfalls.md` 第 11 条，提交 `10d2927`）。**
登记册编号 **`L-31`**（与 B-2「默认摘要只放计数」合并为一条）。
> **回标（2026-08-23，T-5）**：写本节时标注为「未落地」，实际已于 `10d2927` 落地。
> 第 11 条同时覆盖了本条与 B-2（默认摘要只放计数），并保留了「测试给它发合格证」这个要害。
应新增一条决策（D-022 起）：**上下文裁剪一律可逆——被移出上下文的内容必须先落盘并留下引用，
「先删后摘要」在本项目内禁止。** 删除只能是写一条 tombstone，不能是覆盖数组
（这句在本文档 §8.6 的末尾已经以「本项目的对应约束」写过，但**至今没有进任何权威文档**，
本轮把它标为待落地，不再让它停留在 references 里）。

### B-2　不借：默认摘要只放计数

**框架怎么做**：`core/agent.py:365-383`，默认摘要是「本会话包含 N 轮对话 / 用户消息 X 条」，
**零内容**（§9.6）。

**本项目不借的理由**：它把「摘要」这个词用在了一个不含任何被摘要内容的字符串上。
对本项目更危险的是它的**失败路径**——`core/agent.py:452-455` 智能摘要失败时
`print` 一行 ⚠️ 然后**退回到这个纯计数摘要**。
即：LLM 一超时，系统就从「有损保留」静默切换到「完全丢弃」，
调用方看不出区别。这正是 `D-003` 反对的「降级成功」。

**落地点：已落地（`rules/pitfalls.md` 第 11 条，与 B-1 合并成一条，提交 `10d2927`）。**
> **回标（2026-08-23，T-5）**：同 B-1，标注未及时回改。
应落到 **`EVAL_CASES.md §5 失败归因分层**：新增一类「证据不可达」失败，
与 `UNPARSEABLE`（§5.0）同级——**不进四层归因，单独计数**。
理由与 `J-2` 完全同构：`J-2` 说「解析失败不得并入任何实质结果」，
这里是「证据丢失不得并入任何实质结果」。目前 `EVAL_CASES.md` 里没有这一类。

### B-3　不借：用英文空格分词给中文内容打相关性分

**框架怎么做**：`builder.py:164-169`，`set(text.lower().split())` 求交集。

**本项目不借的理由**：**对中文恒为 0**（§9.9(2) 已实测：中文 relevance=0.0000，英文 0.7143），
在默认 `min_relevance=0.3` 下会把**每一段中文证据静默丢弃**，
且不报错、不警告——`_structure` 只是不生成 `[Evidence]` 那一段。
本项目全部语料是中文年报，照抄等于建一个**永远交不出证据的证据系统**。

**落地点：已落地（`rules/pitfalls.md` 第 8 条，提交 `10d2927`）。**
> **回标（2026-08-23，T-5）**：标注未及时回改。第 8 条含本会话的实测数字
> （中文 query → `relevance 0.0000`；同义英文 → `0.7143`），并要求 Phase 3 把「打分恒为 0」做成一条测试。
应落到 **`EVAL_CASES.md §7 阶段门 → Phase 2 门（证据链）**：
加一条准入检查——**任何用于证据召回/排序/去重的组件，
必须先用一条中文问答样本证明其得分不恒为 0**，未证明不得进入评测。
这是一个 5 行的检查，但它拦掉的是「整条链路对中文静默失效」这种一眼看不出来的失败。
登记册编号 **`L-30`**。

### B-4　不借：声明了却不接线的开关（假开关族）

**框架怎么做**：三个实例——
`enable_mmr` / `mmr_lambda` 全仓 2 命中且都是声明本身（§9.9(3)）；
`html_include_raw_response` 完全没接线（§1.9(4)）；
`enum=[...]` 被 pydantic 静默丢弃、声明了约束而约束不存在（§8.4(3)）。

**本项目不借的理由**：假开关比没有开关更糟——它让读代码的人相信某个保护存在。
这与本项目 `rules/failure-modes.md` 第 2 条（**只有真实字段能诚实触发时才声明 flag**）
是同一条，只是框架给了三个现成的反面样本。

**落地点：已落地。**
`rules/failure-modes.md` 第 2 条已覆盖。本条作为**外部实例**补充进该规则的「识别方法」：
`grep -c` 该开关名，**命中数 == 声明处数**即为假开关。
这个判据可以机械执行，比「凭感觉审」可靠。

### B-5　不借：写在 docstring 里、但前置条件已被排除的降级分支

> **→ 已落地 2026-08-26**（登记册 **`L-73`**，`rules/pitfalls.md` 第 15 条）。

**框架怎么做**：`token_counter.py:7`/`:22` 声称「tiktoken 不可用时降级到字符估算」，
而 `:10` 是顶层无保护 `import tiktoken`，`requirements.txt:10` 硬依赖——
**tiktoken 不可用时整个包 import 就失败了**，那个降级分支不可达（§9.8(1)）。

**本项目不借的理由**：这是 `rules/failure-modes.md` 第 2 条的一个**新变种**，
值得单独记：**降级分支本身写得没错，错的是它的触发条件已被上游排除。**
识别方法（本轮总结，建议补进规则）：写完降级分支后问一句——
**「让它触发的那个世界里，程序还活着吗？」** 答不上来就是假降级。

**落地点：未落地。**
应作为第 8 类（或第 2 类的子形态）补进 **`rules/failure-modes.md`**，
因为该文件的定位是「**已经真实犯过的错**」——本项目是否犯过这一类需要操作者确认；
若未犯过，则应改放 **`rules/pitfalls.md`**（预防性高代价陷阱）。**这个归属需要操作者裁决。**

### B-6　不借：把 `project_root` 当沙箱

**框架怎么做**：`file_tools.py` 的 `project_root` **什么都不拦**（§7.1）。

**本项目不借的理由**：`PROJECT_SPEC.md §8` 已明确「❌ 生产环境安全保证（静态校验不是沙箱）」，
即本项目**不假装有沙箱**。框架的问题不是没有沙箱，是**有一个名字像沙箱的参数**。
命名本身构成误导。

**落地点：已落地。**
`PROJECT_SPEC.md §8`（Non-goals）+ `AC-09`（执行前静态校验拒绝全部已知危险样本）
共同覆盖：本项目的边界是「静态校验」，且**它的名字就叫静态校验，不叫沙箱**。
本条不新增约束，作为命名纪律的旁证。

### B-7　不借：`DevLogTool` 作为决策/审计记录的形状

**框架怎么做**：固定文件名 + `except Exception: pass` + `clear` 不留痕（§8.4、§8.6 的 A1–A5）。

**本项目不借的理由**：§8.6 已逐条列出，其中 **A4（`clear` 不留痕）单独就足以否决**——
记录系统若无法区分「记录里没有」与「记录被清掉了」，它防不住审计要防的那件事。

**落地点：~~未落地~~ → 已落地 2026-08-26**（登记册 **`L-72`**，`ARCHITECTURE` **§8.5.7**）。
与 `FT-A7`（时间戳精度）合成一节：**内容寻址 + append-only + 删除只写 tombstone**。
**没有新开决策**——「`D-003` 只规定了字段固定、没规定存储语义」这个判断本节写对了，
但新建 `D-0xx` 是操作者的权限，因此约束先落在 `ARCHITECTURE`，
并在该节明写「是否升格为决策须操作者裁决」。
以下为原文，保留不改：
与 B-1 是同一条待落地决策的两个面（B-1 是历史压缩，B-7 是记录清空），
应合并写进同一条新增决策（D-022 起）：**证据存储 append-only + 内容寻址；
删除只能写 tombstone。** 目前 `D-003` 只规定了「证据链是第一类产物」和字段固定，
**没有规定存储语义**——这是 `D-003` 的一个真实空白。

### B-8　不借：两个口径不同的计数器同时在用

**框架怎么做**：`TokenCounter.count_message`（`encoding_for_model` + 每条 +4 + 缓存）
与 `builder.py:299` 的模块级 `count_tokens`（恒 `cl100k_base`、不 +4、不缓存）并存，
同一段文本得到不同的数，而框架里两者都在用（§9.8(3)）。

**本项目不借的理由**：本项目对「同一个量有两个口径」这件事已经有过一次代价——
`D-016` 之所以要把「标签 = 有序片段序列」当一等构造，正是因为
「留给每个调用点各自发明拼接规则」会产生互不一致的实现。
计数器是同一类问题：**口径分叉不会报错，只会让两处数字对不上，而没人知道哪个对。**

**落地点：已落地（同型原理）。**
`D-016`（映射表 schema：片段序列 + `column_header`，逐字匹配、不允许模糊匹配）
已经把「不允许各调用点自行发明口径」写死在映射侧。
**但计数/预算侧没有对应约束**——若 Phase 2 引入上下文预算，
需要在那时按 `D-016` 同样的原理补一条「全项目单一 token 口径」，**现在不预设编号**。

### B-9　不借：`max_bytes` 式的「判据与执行不一致」

**框架怎么做**：`truncator.py:97` 用字节做判据，`:141-150` 只按行执行，
于是 `max_bytes` 形同虚设（§9.5(1)，已实测）。

**本项目不借的理由**：这是**第二次**在同一个仓库里见到同型缺陷——
§7.4(1) 记的 `MultiEditTool`「校验用原文、执行用滚动结果」是同一个病：
**判据与执行读的不是同一个东西。**
本项目最可能踩它的地方是勾稽校验：**用抽取时的值判、用计算时的值算**，
两者之间隔着单位换算与符号规约。

**落地点：已落地（但值得复核）。**
`D-018` 把 fail-closed 放在**计算层的读入边界**，正是让「判据」与「执行」共用同一份输入。
**建议动作**：在 `docs/agent/OPEN-ITEMS.md` 的 D 区加一条判据——
「勾稽校验读入的数值，与 `formula` 求值读入的数值，是否为同一对象？」
若两者之间存在任何转换步骤，`D-018` 的保证就有缺口。**这是本节唯一一条需要操作者确认的动作项。**

## 10.3 一句话总结

框架在**组件层**反复做对（三态协议、截断器形状、封闭求值器、微秒时间戳），
在**接线层**反复做错（指针被丢、闸门只在签名里、校验从不被调用、6 个调用点只覆盖 2 个）。

**对本项目的意义**：`D-003` 目前保证的是「证据链有哪些字段」，
`ARCHITECTURE.md §8` 保证的是「闸门不能被绕过」，
**中间缺一条「证据引用不能在传递过程中丢失」**——
这恰好是本轮读出来的、框架栽得最彻底的地方（§9.4），
也是 10.1-A2 / 10.2-B1 / B-7 共同指向的那条待新增决策。
