# deepseek-ai/deepseek-harness

**读到什么程度**：`docs/architecture.md`（129 行）、`docs/subsystems/tools.md`（720 行，
重点读了执行管线与守卫契约、`ctx.tools` API、`tools/*` 事件）、
`docs/subsystems/session.md`（849 行，重点读了 `SessionEvent` 结构与耐久性契约）、
`docs/tool-execution-pipeline.md`（62 行，全读）**均已读原文**。
未读：Cordis primer 与 tutorial、`agent-lifecycle.md` 时序图、`capability-seams.md`、
`compaction.md` / `persistence.md`、任何源码。

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

## 5. 读了子系统文档之后的补充（这些才是真正能抄的）

### 5.1 `ToolGuard`：返回类型里**故意没有 allow**

```ts
type ToolGuard = (execution: Readonly<ToolExecution>) => string | undefined
```

原文：

> Its return type deliberately has no allow result: `undefined` preserves the waterfall
> decision, while a returned reason **can only reduce permission**, so a later listener
> cannot undo it.

这叫 **monotonic guard（单调守卫）**：注册再多守卫只会收紧、永远不会放宽，
且**没有任何守卫能强制放行另一个守卫已拒绝的调用**。

**对本项目**：口径闸门必须是这个类型。如果闸门的返回值里有 `allow` 这一支，
那早晚会出现「某个配置/某个插件把它打开」的路径，闸门就名存实亡。
`resolve()` 现在返回 `MetricDefinition | Refusal`——**已经是单调的**（拒答不可被覆盖），
这一点无意中做对了，应当在 ARCHITECTURE.md 里写明它是有意的而非偶然。

### 5.2 参数不可改写——一句直接适用于审计的话

> **Arguments cannot be rewritten because history, audit, UI, and execution must agree.**

`tools/pre-execute` 可以 allow / deny / ask，**但不能改写参数**。理由是四方必须一致：
日志、审计、界面、实际执行。任何一处允许改写，事后复核看到的就不是实际跑的。

**对本项目**：这条应当直接进 Phase 2 的架构约束。取数层可以拒绝，不可以「顺手修正」
一个字段名或一个单位——那样证据链记录的东西和实际算的东西就分叉了。

### 5.3 完整执行管线（`tool-execution-pipeline.md` 全图）

```text
tool/call（**执行前**就记入 session 事件）
  → tools/pre-execute 瀑布      hooks、权限、沙箱；allow / deny / ask
  → 注册的单调守卫              deny 或弃权；身份受保护
  → ctx.approval 一次性询问     缺审批通道或无法回答 ⇒ deny
  → tools/execute 瀑布          around-dispatch：超时、重试、指标
  → 工具本体 execute()
  → tools/post-execute 瀑布     accept / block / replace / 追加上下文
  → 注册表外层归一化            快照抛错转成 isError
  → finalizeContent             定义自有的最后不变量
  → tools/result                冻结的权威结果，同步通知
```

两个细节值得抄：

- **`tool/call` 在执行之前就写进日志**。所以被拒绝的调用**也留痕**。
  本项目的拒答同理：拒答事件必须在拒答判定之前就开始记录，不能「拒了就当没发生」。
- **缺审批通道 ⇒ deny，不是 ⇒ allow**。fail-closed 贯彻到基础设施缺失的情形。

### 5.4 `SessionEvent`：证据链的现成骨架（直接对应 U-01）

`Session` 是 **append-only 的 typed event 日志**，是唯一真相源。
关键一句：**LLM 的消息历史是从日志 derive 出来的，从不单独存储；replay 就是从同一批事件重新 derive。**

```ts
type SessionEvent<T> = {
  type: K
  seq: number          // 会话内单调序号，seq = log.length
  time: number         // epoch ms
  data: SessionEventMap[K]
  ignorable?: true     // 见下
} & (K extends SurfaceEventType ? {
  sourceEventSeqs?: number[]   // ← 这个字段就是证据链
  surfaceOp?: SurfaceOp
} : object)
```

**`sourceEventSeqs`：本事件引用了哪些更早事件作为来源**（例如一条 `assistant/message`
引用产生它的那些 `assistant/chunk` 的 seq）。
这是**机器可读的溯源链接**，不是散文式的「参考了某某」。
U-01 的证据链字段集应当照此设计：每个结论事件带一个指向其输入事件的 seq 列表，
复核者顺着 seq 就能一路回溯到取数与口径定义，不需要读任何自然语言说明。

**`ignorable` 默认为「必需」**——设计理由值得整段抄：

> 读到一个不认识的 `type` 且没有这个标记时，读者 **MUST 拒绝重建会话**，
> 而不是静默丢弃该事件，因为一个未被识别的必需事件可能改变整个日志其余部分的解读方式。
> 写入方只在「丢了也不影响重建」的纯信息记录上设 `true`。
> **默认为必需意味着忘记打标记会导致过度拒绝（一个不便），而不是静默地恢复出一个被掏空的会话。**

这是 fail-closed 应用在**日志格式演进**上。本项目的证据链一旦要跨版本读取，
这条就是现成答案：宁可拒绝重建，不可静默降级。

### 5.5 一个我们已经踩对、但应写明理由的点

`SessionEventMap` 是 merge-extensible 的，所以「switch over SessionEvent 时
**不能用 `assertNever`**」——插件加的变体是合法的未知值。
本项目的 `RefusalCode` 枚举目前是封闭的 7 项且有测试锁死数量，
这在当前阶段是对的（拒答理由必须穷举），但若将来允许插件扩展拒答码，
这条约束要同步放开，且要有 `ignorable` 式的兜底策略。

## 6. 待读（按对本项目的价值排序）

1. `docs/subsystems/tools.md` — 受守卫的执行管线细节，直接对应 AC-09
2. `docs/subsystems/session.md` — append-only 日志的事件设计，直接对应 U-01 证据链字段集
3. `docs/tool-execution-pipeline.md` — `tools/*` 三段瀑布的具体契约
4. `docs/agent-lifecycle.md` — 时序图，取消与错误恢复
5. `docs/capability-seams.md` — 「capability 事件挂到缝上」这个抽象怎么定义的
