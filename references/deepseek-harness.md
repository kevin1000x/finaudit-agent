# deepseek-ai/deepseek-harness

**读到什么程度**：`docs/architecture.md` **读完**；`packages/` 与 `docs/` 清单看过。
未读：子系统文档（session / tools / core / llm-streaming）、Cordis primer、
`agent-lifecycle.md` 时序图、`tool-execution-pipeline.md`、代码。

**基本信息**：TypeScript，MIT，2026-08-13 开源，110k+ star。口号「Everything is a Plugin」。
底座是 **Cordis** 框架：插件向共享 context 贡献 service、typed event、**可撤销的 effect**。

---

## 1. 它的核心结构

**没有特权内核。** 模型适配器、工具注册表、会话日志、**agent loop 本身**都是插件，
全部可从配置替换。插件卸载时其注册作为 effect 自动回滚。

组装方式是 **profile → bundle → patch** 三层：

- **profile**：一个具名组合（`web` / `headless` 是模板），列出它叠哪些 bundle
- **bundle**：Cordis 配置行 + 挂载的代码的分发格式
- **patch**：按 id 定位某一行并整体替换其 config，或插入新行

叠加顺序：bundle（按 profile 列出的顺序）→ profile 的 `cordis.patch.yml` →
home 级 → `--patch` 覆盖层。`dsh --profile web --dump-config` 打印实际启动的树。

核心包与 `ctx` 键：

| 包 | 负责 | ctx 键 |
|---|---|---|
| `core/session` | append-only 的 `SessionEvent` 日志 | `ctx.sessions` |
| `core/system-prompt` | prompt 段落与 tool schema 装配 | `ctx.systemPrompt` |
| `core/tools` | 带作用域的工具注册表 + **受守卫的执行管线** | `ctx.tools` |
| `core/agent` | `Agent` 接口与 `agent/*` 事件 | `ctx.agents` |
| `core/agent-loop` | 默认驱动 | `ctx.agentLoop` |
| `llm/llm` | 消息与流式词汇 + 适配器缝 | `ctx.llm` |

## 2. turn / step 模型与事件瀑布（**本项目最该借的**）

**step** = 一次模型请求 + 它调用的工具。**turn** = 零个或多个 step。

```text
turn/start
  claim 下一步输入
  装配 prompt 段落 + tool schema
  -> agent/pre-step            reject | enter(messages)
     被 reject，或首次 enter 被改写为空 -> 不产生 step 直接关闭 turn
     step/start
     agent/request -> llm/stream -> assistant/chunk* -> assistant/message
     tool/call* -> tools/pre-execute -> tools/execute -> tools/post-execute -> tool/result*
     step/end
  -> agent/turn-stopping
turn/end
```

关键机制：

- `agent/pre-step`、`agent/request`、`llm/stream`、三个 `tools/*` 都是**瀑布（waterfall）**：
  **listener 必须显式调用 `next()` 才会往下传**。不调 `next()` 就是阻断。
- `agent/pre-step` 可以直接 **reject**，或改写模型将看到的消息。
- 被 reject 的 turn **仍然产生一条 durable 的 turn 记录**（log 里留下「尝试过」的痕迹），
  只是没花掉任何 step。
- 三类事件域分工明确：**session 事件**是必须活过重载的持久事实；
  **agent 事件**携带活的 `Agent` 句柄用于在途干预；
  **capability 事件**（`fs/*` `tools/*` `telemetry/*`）把策略挂到某个缝上而不必 import loop。

## 3. 对本项目的直接用处

### 3.1 语义层闸门找到了正确形状

本项目的核心主张是「口径未定义时**拒答**，而不是猜」。之前的难题是：
如果口径查询只是「LLM 可以调的一个工具」，LLM 就可以**不调**，直接用参数记忆答一个数——
论点就没了（见 `hello-agents.md` 里对「万物皆 Tool」的批评）。

Harness 的瀑布给出了答案：**语义层闸门是 `agent/pre-step` 的一个 listener，不是一个 tool。**

```text
agent/pre-step  →  解析问题里的指标名
                   ├─ 解析不到  → reject，turn 关闭，模型根本没被调用
                   └─ 解析到    → enter(messages)，把口径定义与版本注入 prompt
```

这比「让 LLM 自觉调用工具」强在**结构上无法绕过**。而且被 reject 的 turn 仍然入日志，
天然满足 D-003「拒答是第一类产物，要有记录」。

同理，**取数守卫**放 `tools/pre-execute`：字段不在 `source_fields` 声明里就不调 `next()`，
工具压根不执行。这落实 AC-09「`pre_execute` 拒绝全部已知危险样本」。

### 3.2 append-only session log ≈ 证据链的载体

`core/session` 的 `SessionEvent` 是 append-only 且可重放的。本项目的证据链（U-01 未定字段集）
正需要这个性质：**每一步都留痕、事后不可改、可独立重放核对**。
Phase 2 设计证据链时应参考它的事件分类（durable fact vs live hook），
而不是自己从零想一套。

### 3.3 profile / bundle / patch ≈ 交付形态的答案

操作者想要 Web + 本地 GUI 两个界面。Harness 的 `web` / `headless` 两个 profile
共用 `dsh-base`，只在最外层叠不同的 bundle——**同一个内核，两种壳**。

本项目可照此分层：语义层 + 执行层 + 证据链是内核，
Web 页面与本地 GUI 各是一层薄壳。这样「两个界面」的增量成本远小于做两遍。

## 4. 刻意不借的

- **不引入 Cordis / TypeScript 运行时。** 本项目是 Python，且核心价值在口径层不在框架层。
  借的是**事件瀑布 + 可拒绝的前置钩子**这个**形状**，用 Python 实现即可，
  不必要有插件树、profile 叠加、effect 回滚那一整套。
- **不做「一切可替换」。** Harness 连 agent loop 都能换，因为它是通用运行时。
  本项目恰恰相反：**语义层闸门必须不可替换、不可绕过**，那是它存在的理由。
  可配置性在这里是缺陷不是优点。
- **不抄 `dsh` 的包切分粒度**（30+ 个包）。本项目现在 14 个 `.py`，
  照它切会立刻触发 D-009 的 ceremony 红线。

## 5. 待读（按对本项目的价值排序）

1. `docs/subsystems/tools.md` — 受守卫的执行管线细节，直接对应 AC-09
2. `docs/subsystems/session.md` — append-only 日志的事件设计，直接对应 U-01 证据链字段集
3. `docs/tool-execution-pipeline.md` — `tools/*` 三段瀑布的具体契约
4. `docs/agent-lifecycle.md` — 时序图，取消与错误恢复
5. `docs/capability-seams.md` — 「capability 事件挂到缝上」这个抽象怎么定义的
