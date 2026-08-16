# deepseek-harness 深读 Part 2

> 本轮目标：`subsystems/` 剩余文档 + 上一轮未读清单，重点核实三个断言。
> 仓库获取方式与元信息核实见 §0。所有 `文件:行号` 均相对 harness 仓库根。

---

## 0. 获取方式与元信息核实（不照抄上轮）

### 0.1 怎么拿到的

| 步骤 | 命令 | 结果 |
|---|---|---|
| 1 | `gh repo view deepseek-ai/deepseek-harness --json ...` | 成功，返回元信息 |
| 2 | `git clone --depth 1 https://github.com/deepseek-ai/deepseek-harness.git` | **失败**：2 分钟超时（Exit code 143） |
| 3 | `git clone --depth 1 --filter=blob:none --no-checkout` | 成功 |
| 4 | `git sparse-checkout disable`（全量检出） | **部分失败**：`Filename too long`，2 个 `packages/client/ui-primitives/tests/fixtures/markdown-dom/*.streaming.txt` 检出失败 |
| 5 | `git config core.longpaths true; git checkout -- .` | 成功，`git status --short` 为空，工作区干净 |

克隆位置：`<scratchpad>/deepseek-harness`（session 级临时目录，**不在 finaudit-agent 仓库内**）。
该目录会随 session 结束消失；本报告中所有引用都带行号，便于重新克隆后复核。

### 0.2 元信息（自己核实，不采信上轮）

| 项 | 上轮记录 | 本轮实测 | 判定 |
|---|---|---|---|
| 开源日期 | 2026-08-13 | `createdAt: 2026-08-13T11:56:32Z` | ✅ 属实 |
| 语言 | TypeScript | `primaryLanguage: TypeScript`；7412 个文件中 2319 个 `.ts` | ✅ 属实 |
| 许可 | MIT | `LICENSE:1` = `MIT License`，`Copyright (c) 2026 DeepSeek` | ✅ 属实 |
| — | 未记录 | **默认分支是 `master` 不是 `main`** | ⚠️ 上轮未记，易踩 |
| — | 未记录 | `pushedAt: 2026-08-13T13:00:21Z`；HEAD `47f9438`（2026-08-13 19:38 +0800，`Merge PR #2519 feat/npm-public`） | 补充 |
| — | 未记录 | 公开仓库，118742 stars | 补充 |
| — | 未记录 | 根包 `@deepseek-ai/dsh-root@0.1.0-rc.5`，pnpm workspace，`engines.node: ^22.19.0 \|\| >=24.0.0` | 补充 |
| — | 未记录 | CI 用 **GitLab CI**（`.gitlab-ci.yml`），不是 GitHub Actions | 补充 |

**注意 `SESSION_FORMAT_VERSION = 0`，预发布状态，官方明说「no compatibility implied」**
（`docs/persistence-catalog.md:10`）。它的设计可以借鉴，它的稳定性不能指望。

---

## 1. 读到什么程度

### 1.1 本轮新读文档

| 文档 | 程度 |
|---|---|
| `docs/subsystems/approval.md` | **读完**（1-170） |
| `docs/subsystems/session-projection.md` | **读完**（1-262） |
| `docs/subsystems/scope.md` | **读完**（1-59） |
| `docs/subsystems/system-prompt.md` | **读完**（1-207） |
| `docs/subsystems/jobs.md` | **读完**（1-290） |
| `docs/subsystems/skills.md` | **读完**（1-331） |
| `docs/subsystems/user-questions.md` | **读完**（1-178） |
| `docs/subsystems/plan.md` | **读完**（1-87） |
| `docs/subsystems/permission-presets.md` | **读完**（1-131） |
| `docs/glossary.md` | **读完**（1-45） |
| `docs/testing.md` | **读完**（1-49） |
| `docs/rescope.md` | **读完**（1-53） |
| `docs/persistence-catalog.md` | **读了 1-175 / 396-635 / 660-944**；未读 176-395（`assistant/*` `command/*` `compaction/*` 段）与 636-659（`session/title*`）。**44 个事件类型的完整名单与 surface/log-only 标记已全部获取**（`grep '^#### '`） |
| `docs/subsystems/session.md` | **读了 154-233 / 521-606**（`request/header`、`SessionEvent` 信封、`deriveMessages()`、`TurnEndReasonMap`、`session/end-seed`、耐久性契约）；其余 700 余行未读 |
| `docs/subsystems/session-query.md` | **读了 280-390**（`SessionEventTrace` + 错误码全集）；其余未读 |
| `docs/subsystems/goal.md` | **读了 1-120**；121-277 未读 |
| `docs/subsystems/invariants.md` | **读完**（1-88）—— 上轮已读，本轮为核实 Q3 重读 |

### 1.2 本轮新读源码（文档之外的一手证据）

| 文件 | 程度 |
|---|---|
| `packages/interaction/user-approval/src/types.ts` | **读完**（29 行） |
| `packages/interaction/user-approval/src/index.ts` | **读了 18-177** + 全文 grep 事件/方法声明 |
| `packages/interaction/user-approval/src/invariant.ts` | **读完**（约 110 行） |
| `packages/core/agent-loop/src/invariant.ts` | **读完**（63 行） |
| `packages/core/agent/src/invariant.ts` | **读完**（33 行） |
| `packages/core/session/src/invariant.ts` | **读了 1-80**；81-250 未读 |
| `packages/core/tools/src/index.ts` | **读了 585-601 / 1670-1729**；其余约 1800 行未读 |
| `scripts/run-gates.ts` | **读了 120-280** + `docSyncLeafGates` / `coverageGates` / `ciSharedStaticGates` 三个函数体 |
| `package.json` scripts | **全部 123 条读完** |
| `packages/runtime-diagnostics/invariants/README.md` | **只读了 grep 命中的 10 行** |

### 1.3 明确未读（不能置评，见 §5）

`api-gateway.md`、`config-catalog.md`(3151 行)、`development.md`、`postmortem/`(5 篇)、`user/`(13 篇)、
`architecture.md`、`module-graph.md`(1638)、`tool-catalog.md`(1873)、`cordis-*`(全部)，
以及 `subsystems/` 下 26 篇：`attachment` `client-modules` `code-runtime` `commands` `credentials`
`extensions` `feedback` `filesystem` `lsp` `sandbox` `schedule` `session-reference` `session-telemetry`
`session-title` `settings` `shell` `storage` `subagent` `subprocess` `terminal` `tools` `typert`
`web-server` `web` `workflow` `workspace`。

---

## 2. 三个必答问题

### Q1 — `approval` 里「被拒绝 / 待批准」是不是一等持久化状态？

**结论：「被拒绝」是一等持久化终止态，字段集齐全。「待批准」不是持久化状态，是进程内的一次 await。**

#### 1) 拒绝是一等终止态 —— 有独立事件类型

三个 `approval/*` 事件全部是 **log-only** 的持久化 session 事件
（`docs/persistence-catalog.md:142` / `:167` / `:185`；声明处 `packages/interaction/user-approval/src/index.ts:44-71`）：

```ts
// packages/interaction/user-approval/src/index.ts:44-58
'approval/asked': {
  id: ApprovalRequestId
  toolName: string
  callId?: CallId
  reason?: string          // 提问方对「为什么问」的人类可读解释
}
'approval/decided': {
  id: ApprovalRequestId
  outcome: ApprovalOutcome
}
```

```ts
// packages/interaction/user-approval/src/index.ts:67-71
'approval/policy': {
  policy: ApprovalPolicy          // 'ask' | 'never'
  source?: 'delegation'           // 标记「子 agent 继承来的」而非运行时切换
}
```

#### 2) 终止态的取值是**封闭四元组**，`rejected` 与失败严格区分

```ts
// packages/interaction/user-approval/src/types.ts:26-29
/**
 * Closed approval outcomes: a one-shot grant, explicit rejection, withdrawn
 * request, or unavailable answerer. Callers fail closed on `unavailable`.
 */
export type ApprovalOutcome = 'allowed-once' | 'rejected' | 'cancelled' | 'unavailable'
```

四个值的语义分工（`docs/subsystems/approval.md:21`）：

| 值 | 含义 | 对 finaudit 的对应 |
|---|---|---|
| `allowed-once` | **唯一**的放行，且只放行这一次这一个动作 | 通过 |
| `rejected` | 人明确说了「不」 | `Refuse[reason='user_rejected']` |
| `cancelled` | 问题被撤回（signal abort），迟到的回答被丢弃 | `Refuse[reason='withdrawn']` |
| `unavailable` | 没有 answerer / answerer 抛错 / 返回了词表外的值 | `Refuse[reason='no_channel']` —— **fail-closed** |

关键设计：**「问不到人」不是错误，是一个正常的终止值**。
`docs/subsystems/approval.md:21`：「A missing, non-owning, throwing, or non-conforming answerer becomes
`unavailable` rather than opening the gate.」词表外的返回值被规范化成 `unavailable`
（`packages/interaction/user-approval/src/index.ts:325`），而不是泄漏进调用方的 switch。

#### 3) 审计对必须成对，且必须被 turn 包住 —— 写不进日志就不给决定

`docs/subsystems/approval.md:120-132`（`request()` 的 JSDoc，源码 `index.ts:244-274`）：

> The request **requires an open turn** because the audit pair must be enclosed by the durable log's
> commit/replay boundary; an idle ask rejects before appending anything. […]
> **A failure that prevents either audit append from committing still rejects because returning an
> unlogged decision would violate the pair.**

turn 包围的理由写在 `index.ts:120-126`：turn 之间裸写的事件在重载时与崩溃残尾无法区分，会被静默丢弃。

`never` 策略在 waterfall 之前就被执行（`docs/subsystems/approval.md:86`），所以后注册的 answerer
即使 `prepend` 也绕不过去。

#### 4) 有运行时不变量机械检查这个成对关系

`packages/interaction/user-approval/src/invariant.ts` 是独立的 invariant companion，检查四条：

```
approval/asked appended outside any open turn
approval/asked toolName must be non-empty
approval/asked repeated open id <id>
approval/decided has no matching approval/asked for id <id>
approval/decided carries unknown outcome <outcome>
approval/policy carries unknown policy <policy>
```

而且它做的是 **pre-commit 校验**：在 `internal/dispatch` 阶段先验证再 staged，
`session/event` 到达时若没有对应的 staged 记录就报
`approval audit event published without pre-commit validation`。
—— 即「绕过校验直接发布审计事件」本身也是不变量违规。

#### 5) 拒绝**怎么到模型面前**：不是新事件，是派生的 tool result

这是 finaudit 最该注意的一处。`ApprovalOutcome` 是持久化的，但模型看到的是消费方派生出的
`PreToolDecision`：

```ts
// packages/core/tools/src/index.ts:588-591
export type PreToolDecision =
  | { kind: 'allow' }
  | { kind: 'deny'; reason: string }     // reason 是必填
  | { kind: 'ask'; reason?: string }
```

```ts
// packages/core/tools/src/index.ts:1713-1727
case 'allowed-once': return { decision: { kind: 'allow' }, approvalCancelled: false }
case 'rejected':     return { decision: { kind: 'deny', reason: `the user rejected tool "${exec.name}"` }, ... }
case 'cancelled':    return { decision: { kind: 'deny', reason: `approval for tool "${exec.name}" was cancelled` }, approvalCancelled: true }
case 'unavailable':  return { decision: { kind: 'deny', reason: `tool "${exec.name}" requires approval, but no approval channel is available` }, ... }
```

`index.ts:1684-1687` 的注释点明意图：
「the three non-grants deny with **distinct reasons so the model can tell a human "no" from an absent
approval channel**」。

还有两条更早的 fail-closed 分支（`index.ts:1693-1705`）：
没有 composed `ApprovalService` → deny；`exec.agent === undefined` → deny，理由是
「没有 agent 就没有 session 可审计、没有 UI 可路由」。**「审计不了就不许做」被写进了执行路径。**

#### 6) 「待批准」**不是**持久化状态 —— 这是与 finaudit 需求的分歧点

日志里没有 `pending` 事件。`approval/asked` 之后到 `approval/decided` 之前，这段等待
只存在于 `request()` 的 `await` 里。崩溃重启后，`approval/asked` 会有一条没有配对的 `decided`，
而 `session-persistence` 的崩溃修复只闭合 turn/step/tool 三种括号，
**不闭合 `approval/*`**（`docs/subsystems/session.md:589`：「crash repair closes turn/step/tool
boundaries and never `compaction/*`」，同理不含 approval）。

对 finaudit 的含义：如果「待人复核」要跨进程存活（提交给人、下周再来看），
**不能照抄 harness**。harness 的 approval 是同进程、同 turn 内的同步问答
（`ApprovalRequest` 的 JSDoc 明写 "Readonly **same-process** permission question"，`index.ts:150`）。

---

### Q2 — `session-projection` 遇到不认识的事件类型会怎样？

**结论：上轮记录**三条断言里**两条属实、一条张冠李戴**。逐条核对：

#### 断言 A：「`ignorable` 默认为『必需』」→ ✅ **属实**，且理由被写成了显式决策

```ts
// packages/core/session/src/types.ts:422（信封字段），同文见 docs/persistence-catalog.md:66-76
/**
 * Marks an event a reader may safely skip when it does not recognize
 * `type`. Absent means required: a reader meeting an unrecognized type
 * without this marker MUST refuse to reconstruct the session instead of
 * silently dropping the event, because an unrecognized required event may
 * change how the rest of the log is interpreted. A writer sets `true` only
 * on purely informational records whose loss cannot affect reconstruction;
 * defaulting to required means a forgotten marker over-refuses (an
 * inconvenience) rather than silently resuming a gutted session.
 */
ignorable?: true
```

决策记录 `.agents/notes/implemented/architecture/2026-08-10-session-log-version-mechanism.md:19` 把
权衡写得更直白：

> The default is *required*: forgetting the marker **over-refuses a resumable session (an
> inconvenience)**, while a default of ignorable would make the same mistake **silently resume a
> gutted one (a safety failure)**.

同一 note 的 `:28` 把反面方案列为被否决项：
「**Default-ignorable unknown events** — inverts the failure mode of a forgotten marker from visible
over-refusal into silent corruption.」

**补充一条上轮没有的事实**（`同 note :23`）：目前**没有任何 writer 会设置 `ignorable`**
（"writers do not yet set `ignorable` (no producer needs it)"）。所以今天的实际行为是：
任何仓库外插件的事件类型都会让 resume 直接拒绝。官方接受这个代价，理由是「refusal is loud rather
than silent」。

#### 断言 B：「读到不认识的事件必须拒绝重建（fail-closed）」→ ✅ **行为属实**，❌ **位置错了**

**不在 session-projection，在 persistence 的 load 边界。**

```ts
// packages/session/session-persistence/src/coordinator.ts:1063-1064
if (KNOWN_SESSION_EVENT_TYPES.has(event.type) || event.ignorable === true) continue
throw this.unsupported(meta, `session "${meta.id}" contains event type "${event.type}" (seq ${event.seq}) unknown to this harness and not marked ignorable; refusing to interpret the log — it was likely written by a newer harness`)
```

- 抛的是 `SessionFormatUnsupportedError`，与 `SessionPersistenceCorruptionError` **刻意分开**
  ——「nothing is damaged」（`docs/subsystems/persistence.md:94`）。
- 已知词表 `KNOWN_SESSION_EVENT_TYPES` 是**从源码生成**的（`gen-persistence-catalog`），
  由 `verify-persistence-catalog` 保持新鲜（`packages/core/session/src/known-event-types.ts:12`）。
- 这个守卫是**只读侧的**：`appendCore` 不做词表检查。理由（`同 note :23`）：
  append 时拒绝会让活着的 session 在半途卡住耐久性，代价比「下次加载时大声拒绝」更高。
- 错误文案被快照测试钉死：`examples/headless-agent/tests/session-format-guard.snapshot.ts:100`。
- 契约测试证明两侧行为：`packages/session/session-persistence/tests/coordinator-contract.ts:1360`
  （未标记 → 拒绝）与 `:709-724`（标 `ignorable: true` → 放行）。

**而 `session-projection` 的行为恰恰相反：对不认识的事件必须静默无视。**

```ts
// docs/subsystems/session-projection.md:33-39（ProjectionDefinition.apply 的 JSDoc）
/**
 * Pure transition: previous state + one committed event → next state. A
 * unit uninterested in an event MUST return the same state reference — an
 * unchanged reference (`Object.is`) produces zero downstream work.
 */
apply(state: S, event: SessionEvent): S
```

这不是漏洞，是分层：projection 只跑在**已经通过 load 校验的 committed 事件**上
（`docs/subsystems/session-projection.md:5`：「The registry subscribes to `session/event` once and
folds every committed event through every unit」），fail-closed 的闸门在它上游。

**给 finaudit 的教训：fail-closed 要放在「日志→内存」的入口，不要放在「内存→视图」的投影里。**
投影层每个 unit 只认自己的事件，放在那里做词表校验会让每个 unit 都要认识全部词表。

#### 断言 C：「`SessionEvent.sourceEventSeqs` 是证据链骨架」→ ✅ **属实，但范围比上轮说的窄得多**

`sourceEventSeqs` **只存在于 3 个 surface 事件类型上**，日志里其余 41 个 log-only 事件**没有这个字段**：

```ts
// docs/persistence-catalog.md:23-27
export type SurfaceEventType =
  | 'user/message'
  | 'assistant/message'
  | 'tool/result'
```

```ts
// docs/persistence-catalog.md:77-89（条件类型，编译期强制）
} & (K extends SurfaceEventType ? {
  sourceEventSeqs?: number[]
  surfaceOp?: SurfaceOp
} : object)
```

`docs/subsystems/session.md:206-210` 说明这是**编译器在 `Session.append()` 调用点强制**的，
不是运行时约定。

它的校验规则（`.agents/notes/implemented/architecture/2026-06-18-session-surface.md:52`）：

> `Session` validates `sourceEventSeqs` and `surfaceOp` at the always-on seed/append boundary:
> only `assistant/message` may use an empty source-event list; references are **unique, earlier, and
> known**; replacement endpoints exist in surface order; and `sourceEventSeqs` **covers every shadowed
> node**. These are single-record acceptance and storage-projection rules, **not optional
> invariant-service contributions**.

三态语义（`docs/persistence-catalog.md:78-85`）：

| 状态 | 含义 |
|---|---|
| 非空数组 | 明确引用了这些 seq 作为来源 |
| 空数组 `[]` | **只有 `assistant/message` 合法** —— 记录「provider 流确实是空的」这个已知事实 |
| 字段缺席 | legacy 或外来事件，**不记录**来源（与「来源为空」严格区分） |

**「空」和「未知」被区分开**，这一点直接可搬到 finaudit。

上轮说它是「骨架」不算错，但它是 **surface（模型可见历史）的骨架**，不是全审计链的骨架。
log-only 的审计事件之间靠**业务 id 配对**，不靠 seq 引用：`approval/asked`↔`approval/decided`
靠 `id`，`hook/invoked`↔`hook/result` 靠 `handlerId`
（`docs/persistence-catalog.md:436` / `:456`），
`tool/call`↔`tool/result` 靠 `callId`（`docs/persistence-catalog.md:733`）。
`docs/subsystems/session.md:597` 把这条上升为规则：

> When several events in one plugin-owned family assemble into one Web Client Conversation Node,
> every start, update, result, resource, or interruption event in that family carries or independently
> derives **the same stable business id**. […] it lets the client group each event without guessing
> from adjacency or scanning history.

#### 补充：真正的「证据链查询 API」在 session-query，不在 projection

```ts
// docs/subsystems/session-query.md:308-322
interface SessionEventTrace {
  target: SessionEventRecord
  replacedBy?: number            // 直接位置替换者
  replacementChain: number[]     // 追到最终替换者
  replacedEventSeqs: number[]    // target 自己替换掉的 surface 节点
  sourceEventSeqs: number[]      // 直接引用的来源，按记录顺序
  derivedEventSeqs: number[]     // 反向：后续直接引用 target 的事件，按日志顺序
}
```

`docs/subsystems/session-query.md:295` 明说：**只有 `replacementChain` 是传递闭包，其余全是直接边；
「The query does not follow cited source events transitively.」**
错误码里有专门一个 `SESSION_QUERY_SOURCE_CONFLICT`（`:356`）——「contradictory source metadata」。

---

### Q3 — 有没有仓库级机械检查在强制「Model-visible ⟺ logged」？

**结论：有，但上轮的描述需要修正三处。**

- ✅ 这条规则确实被写成 repo convention。
- ✅ 确实有机械检查在跑，且确实在 CI 门禁里。
- ❌ 但它**不是 lint 规则**，是**运行时不变量**（runtime invariant）。
- ❌ 它**不在出厂组合里挂载** —— 我 grep 了全部 `*.yml`，**没有任何一个 shipped `cordis.yml`
  挂 invariants 插件**。它只在测试组合里挂。
- ❌ 名字叫 `verify-package-invariants` 的那个 CI gate **不检查这条规则本身**，它检查的是
  「每个包有没有按契约写 invariant companion」。

#### 1) 规则原文

```
# AGENTS.md:107
- **Model-visible ⟺ logged**: anything that reaches a model request must be reconstructable
  from the session log; a new model-visible input requires a session event.
```

上位原则见 `.agents/notes/implemented/architecture/2026-07-05-reconstructable-requests.md:17`
（**Model-visible ⟺ durably referenced**）：

> The checkable consequence: anyone holding the log, its referenced attachment objects, and the pinned
> code version **reconstructs every loop request byte-for-byte**.

repo 层面还有一条元规则（`AGENTS.md:139`）：

> **Wire mechanically checkable invariants into an executed top-level gate** and prove each changed
> acceptance path rejects an invalid case.

#### 2) 机械检查的实现位置：`packages/core/agent-loop/src/invariant.ts:19-54`

**这是本轮最重要的发现，全文抄录关键段：**

```ts
// packages/core/agent-loop/src/invariant.ts:19-54
const install: InvariantInstaller = Object.assign((ctx: Context, fail: InvariantFailure) => {
  // Prepend prevents a short-circuiting replay listener from silencing the check.
  ctx.on('llm/stream', (options: GenerateOptions, next) => {
    if (!isAgentLoopRequest(options)) return next()
    if (!Object.isFrozen(options)) fail('a loop-built request must be frozen')
    if (options.sessionId === undefined) fail('a loop-built request must carry a session id')
    const session = ctx.sessions.get(options.sessionId)
    if (!session) fail(`a loop-built request must carry a live session id, got "..."`)
    if (!Object.isFrozen(options.messages)) fail('a loop-built request must carry a frozen messages array')

    const events = session.events
    if (!events.some(event => event.type === 'step/start'))
      return fail('a loop-built request with no step/start in its session log')
    const header = foldRequestHeader(events)
    if (header === undefined)
      return fail('a loop-built request with no request/header event in its session log')

    const expected = session.deriveMessages()
    if (JSON.stringify(options.messages) !== JSON.stringify(expected)) {
      fail(`llm request for session "..." diverges from the dispatch-time durable derivation (log-reconstruction desync)`)
    }

    const headerMatches = options.model === header.config.model
      && options.system === header.system
      && options.temperature === header.config.temperature
      && options.maxTokens === header.config.maxTokens
      && JSON.stringify(options.stop) === JSON.stringify(header.config.stop)
      && JSON.stringify(options.tools ?? []) === JSON.stringify(header.tools ?? [])
    if (!headerMatches) {
      fail(`llm request for session "..." diverges from the folded request header`)
    }
    return next()
  }, { global: true, prepend: true })
}, { inject: ['sessions'] })
```

**这就是「Model-visible ⟺ logged」的可执行定义**：每一个 loop 发出的 LLM 请求，
其 `messages` 必须与 `session.deriveMessages()` **JSON 逐字节相等**，
其 header 六个字段必须与 `foldRequestHeader(events)` 相等。不等就 throw。
`prepend: true` 的注释说明了防御意图：**防止短路的 replay listener 把检查静音掉**。

#### 3) 它怎么进 CI

挂载这个 companion 的 13 个文件里有 11 个是 spec：

```
packages/core/agent-loop/tests/invariant.spec.ts
packages/core/agent-loop/tests/contract-regressions.spec.ts
packages/compaction/compaction-basic/tests/compaction-loop-repro.spec.ts
packages/compaction/compaction-basic/tests/manual-compaction.spec.ts
packages/subagent/subagent-fork-in-process/tests/{multi-subagent,subagent-fork-in-process}.spec.ts
packages/subagent/subagent-in-process-driver/tests/{structured,subagent-in-process-driver}.spec.ts
packages/subagent/subagent-spawn-in-process/tests/subagent-spawn-in-process.spec.ts
packages/workflow/workflow-worker-thread/tests/integration.spec.ts
packages/examples/agent-spine-demo/tests/agent-core.spec.ts
```

这些 spec 跑在 `vitest run --coverage` 里，而 `coverageGates()` 是 `ciPrimaryGates()` 的组成部分
（`scripts/run-gates.ts:263`），`check-all` 也直接跑 `pnpm run test`（`scripts/run-gates.ts:226`）。
覆盖率门禁是 **`packages/*/*/src` 每文件 100%**（`docs/testing.md:10`），所以 invariant 文件
本身的每一条 `fail()` 分支都必须被测试触达。

#### 4) 三层门禁的分工（这是可直接搬的结构）

| 层 | 机制 | 检查什么 | 在哪个 gate |
|---|---|---|---|
| **静态·所有权** | `verify-package-invariants` | 每个 workspace 包必须有 `./invariant` companion；空 installer 必须带包内特异的 `No runtime invariant:` 注释解释；非空 installer 必须用 reporter；注册名必须等于 npm 包名；export/publish/依赖/bundle 接线必须完整 | `ciSharedStaticGates()`，`scripts/run-gates.ts:250` |
| **静态·词表新鲜度** | `verify-persistence-catalog`（= `gen-persistence-catalog --check`） | 从源码重新生成完整事件目录与 `KNOWN_SESSION_EVENT_TYPES`，与仓库内文件 diff | `docSyncLeafGates()`，`scripts/run-gates.ts` |
| **运行时·关系** | `agent-loop/invariant.ts` 等 219 个 companion | 真实的事件流关系（请求 ⟺ 日志派生、审计对配对、turn/step 编号、agent 状态无空转迁移…） | 随 `test:coverage` 执行 |

`docs/subsystems/invariants.md:59` 明确了「不许凑」的规则：

> Publication and registration are exhaustive, but **assertions are deliberately not synthetic**.
> A companion installs a check **only when its package owns an observable event or mutable-data
> relationship**; otherwise it exports an empty installer whose leading comment starts
> `No runtime invariant:` and explains, **package-specifically**, why nothing is checkable.

`AGENTS.md:103` 划了可断言对象的边界：

> **Runtime invariants assert owned relationships.** Check **authoritative event streams or mutable
> data**, not service or method presence, plugin metadata or effects, or fixed pure examples.
> Without a plausible relationship, **an explained empty companion is correct**.

> 这与 `rules/failure-modes.md` 里「只有真实字段能诚实触发时才声明 flag」是同一条规则的两种表述。
> harness 把它做成了 219 个包全覆盖的机械门禁 + 「没有就写明为什么没有」的豁免通道。

#### 5) 实测数据

- 219 个 `packages/**/src/invariant.ts`（`find` 计数）。
- 无一 shipped `cordis.yml` 挂 invariants（grep 全仓 `*.yml`，只命中 3 个文件且都是别的语境）。
  → **生产运行时默认不跑这些检查**，它们是开发期/测试期的验证装置。
- 服务本身可配置开关：`Config { enabled?, package_allowlist?, package_blocklist? }`
  （`docs/subsystems/invariants.md:11-21`），空白/重复/非法正则在启动时抛错，不静默跳过。

---

## 3. 逐文档发现

### 3.1 `approval.md` —— 审批的持久化形状

| 事实 | 出处 |
|---|---|
| `ApprovalRequestId` 是 branded 类型，专门为了「不和 tool-call id / agent id 互换」 | `approval.md:11-19`；`types.ts:14` |
| `ApprovalRequest` **故意不带工具参数**：answerer 通过 `callId` 挂到已经流式呈现过的 tool call 上，避免渲染第二份可能漂移的副本 | `approval.md:53` |
| `approval/*` 三个事件**都不进模型 transcript**；模型是通过 runtime-context 快照 + 切换通知知道当前策略的 | `approval.md:88`；`index.ts:60-63` |
| 策略变更走「追加新的完整快照到保留历史之后」，**不重写 request header 里的 system prompt** —— 为了 KV cache 安全 | `approval.md:49` |
| `never` 策略的模型可见句子是硬编码常量，且明确指示模型「不要请求 sandbox 提权」 | `index.ts:100` |
| `effectiveApprovalPolicy` 是**纯 fold**：从后往前找最后一条 `approval/policy`。注释：「replaying the log IS the state」 | `index.ts:104-118` |
| answerer 是 waterfall：返回 outcome = 认领，调 `next()` = 转交；**第一个回答占据唯一的决定槽** | `approval.md:86`, `:154` |
| scope 过滤：agent-scoped listener 只收到自己 agent 的请求 | `approval.md:154` |

### 3.2 `session-projection.md` —— 从事件流重建状态

| 事实 | 出处 |
|---|---|
| `ProjectionDefinition` 是 `{key, schema, init, apply, view, stateVersion}`，**三个函数必须同步**（异步会撕裂 carrier 的一致性切面），`state` 必须是纯 JSON（持久化缓存前提） | `session-projection.md:13-54` |
| **整值事件规则**（load-bearing）：带状态的日志事件携带**完整的变更后状态，绝不是裸 delta**。这让每次转移都便宜、每个值都自描述、消费者可以 last-wins | `session-projection.md:57` |
| `stateVersion` 是缓存失效版本号：序列化字段或 fold 语义一变就 bump，旧行**丢弃**而不是前向应用成垃圾 | `session-projection.md:48-53` |
| `ProjectionSnapshot { asOfSeq, values }`，`asOfSeq` 是共享水位线，空日志为 `-1` | `session-projection.md:61-72` |
| `snapshot()` **完全同步**：carrier 在同一 tick 里读它和页面切片，两次读共享一个 seq。异步 `view` 会返回 Promise，被 schema 校验拒绝 | `session-projection.md:89` |
| `checkpoint()` 返回的每个 `val` 都是 **detached structured clone**，绝不是活引用 —— 「a caller reaching the live reference could corrupt every subsequent snapshot and frame through it」 | `session-projection.md:190-198` |
| `restoreFloor` 的「低一格锚点」是刻意的：尾部读取因此能证明存储日志还延伸多远，从而识别**崩溃修复截断导致日志缩短**的情况，而不是把陈旧行当成当前值 | `session-projection.md:205-218` |
| 冷读阶梯：缓存行 → persistence `readFrom` 尾巴 → registry `restore` → 耐久写回。每次耐久写都是 fail-soft，失败只 warn 并在下次自愈；但 `write()` **不是** fail-soft（`docs/…:128`） | `session-projection.md:107`, `:124-132` |
| 一个 key 被丢弃且 `baseSeq > 0` 时**抛错**（从 `init` 重折只在全日志上成立），调用方从 seq 0 重读 | `session-projection.md:243-248` |
| domain 插件在 `ctx.inject(['sessionProjections'], …)` 下注册，headless 组合没有 registry 也不受影响；同 key 多次注册会计数，最后一个卸载时 key 才消失 | `session-projection.md:157` |

### 3.3 `scope.md` —— 作用域

| 事实 | 出处 |
|---|---|
| `ScopeKey = object`，**不透明的对象身份比较**。出厂 loop 用活的 `Agent` 对象当自己的 key，但原语从不检查这个对象 | `scope.md:11-16` |
| `Scoped<T>` 是编译期 brand，只做路由；**真正的主体作为显式参数传递**，carrier 不暴露主体属性 | `scope.md:18-27` |
| `Scope` 有两条拆卸路径：`rawDispose` 保留 Cordis disposer 的精确身份（用于嵌进有序复合 effect），`dispose()` 是公开的共享静默边界，竞态调用等同一个完成 | `scope.md:31-42` |
| 「一个注册上下文同时意味着**每 agent 可见性**和**共享生命周期所有权**」——一个事实驱动两件事 | `scope.md:5`, `:57` |
| 两层，扁平：**scoped 注册不向 subagent 继承**；子树行为用 lineage **数据**表达，从不用 scope 结构 | `glossary.md:13` |
| 被 restriction 过滤掉的全局工具，「absent from the prompt AND refuses execution，**与根本不存在的工具无法区分**」 | `glossary.md:19` |

### 3.4 `system-prompt.md` —— 提示词组装，「不可覆盖」段的做法

**有「不可覆盖」机制，但方向和直觉相反 —— 不是保护某段不被下游改，而是让某段一票通吃。**

| 事实 | 出处 |
|---|---|
| `PromptSection.complete?: boolean` —— 声明「把这份贡献当作完整的 system prompt」。组装**仍然跑协作 waterfall**（让 tools/contexts/variables 得以解析），然后**把这个 section 原样恢复成唯一的 prompt section**。多于一个生效的 complete section 会让组装失败 | `system-prompt.md:61-67` |
| 因此：`system-prompt/assemble` 的 listener **无法给该 scope 的 system prompt 添加或替换内容**——「A registered complete section is restored after this waterfall, so listeners cannot add to or replace that scope's system prompt」 | `system-prompt.md:169` |
| 排序约定：`-100` = harness 身份，`0` = 部署 persona，`100-199` = 工具指导；其他负数也排在 persona 之前。plan 模式的 `plan:policy` 用 50 | `system-prompt.md:50-54`；`plan.md:29` |
| `PromptContext` 是 `PromptSection` 的 **cache-safe 对偶**：动态内容不进 system prompt，而是**在保留的模型历史之后**物化成一条 durable 的 user-role 快照，且**只在它变了或被 compaction 移除时**才记 | `system-prompt.md:73` |
| `suppressRuntimeContext()` 可以压制某 scope 的全部动态 runtime-context 贡献，**但不改变拥有或强制这些事实的服务**。多个压制者各自独立可 dispose | `system-prompt.md:120-126` |
| `variable(name, provider)`：provider 可以返回 `undefined`，但引用了该值的 section 渲染时会失败（不是静默留空） | `system-prompt.md:138-145` |
| `ToolProviderResult` 区分 `schemas`（本次组装模型可见的集合）与 `knownNames`（限制前的名字全集），**专门为了区分「配置名写错了」和「已知工具在本 scope 被刻意隐藏」** | `system-prompt.md:28-37` |
| `AssembleContext.signal` **只控制这一次显式组装请求，不得留存去控制后续 turn** | `system-prompt.md:169` |

> 对 finaudit 的直接价值：**准则口径段应当是 `complete: false` 但 order 最负的 section**，
> 而「本次可用数据/口径快照」应当是 `PromptContext`（durable user-role 快照）而非 system prompt 的一部分。
> 后者可以被证据链引用，前者不能。

### 3.5 `jobs.md` —— 长任务

| 事实 | 出处 |
|---|---|
| `JobId` 是 `<kind>-N`，**顺序可猜**。「Access control relies on **owner authorization, not id secrecy**」 | `jobs.md:9`, `:176` |
| owned job 的访问由 owner 的 **session id** 围栏；owner 处置会取消并等待 job | `jobs.md:44-50` |
| `JobHooks.done` 「resolves after the producer **releases its resources**, not merely when work finishes」 | `jobs.md:60`, `:70-76` |
| 结算 first-wins：一条终止记录、释放等待者、一轮被容纳的 listener 通知，**即使 producer 迟到的 outcome 也不改** | `jobs.md:177` |
| `reported: boolean` —— 已有 reporter 交付或承诺交付终止态时抑制重复通知。**拆卸也会认领它**，因为「a record its owner is being destroyed for has no reader left」，否则每层拆卸要烧一次模型请求 | `jobs.md:130-137` |
| `start` 在**没有附着的 controller 服务该 owner 时拒绝启动**——「a producer cannot start work that owner cannot collect or stop」 | `jobs.md:178` |
| 本地实现 `maxConcurrentJobsPerOwner` 默认 10，按精确 owner 计 `running + stopping`，无主 job 共享一个桶 | `jobs.md:157` |

### 3.6 `skills.md` —— 技能

| 事实 | 出处 |
|---|---|
| Skills 是「optional instructions, **not session events**」，所以词表不放在 core | `skills.md:5` |
| registry 是 host + per-scope 分层；**最近层的同名条目直接胜出**，rank 顺序只在同一层内裁决重复 | `skills.md:13` |
| 本地发现 6 个 rank：`project-dsh`(100) / `project-agents`(200) / `custom`(300) / `user-dsh`(400) / `user-agents`(500) / `bundled`(600)。project root = 最近的含 `.git` 的祖先 | `skills.md:66-77` |
| `SkillInvocationPolicy { modelInvocable, userInvocable }` —— 两个独立开关归一成正向布尔。四种组合全部保留；`{false,false}` 意味着只有可信的 `ctx.skills.get()` 调用方能拿到 | `skills.md:96-126` |
| `SkillCatalogSnapshot.complete` **区分「权威的不存在」与「provider 暂时挂了 / 目录在发现期间一直在变」**。不完整的快照不缓存，消费者保留上次的好状态并重试 | `skills.md:128-137` |
| 模型看到的 session catalog **只含 `name` 和归一化 XML-转义的 `description`**，不含正文、路径、来源、provider、路由提示 | `skills.md:94`, `:231` |
| 目录变更检测靠**摘要 digest**：对完整快照中 `<available_skills>` 标签之间的确切渲染条目做摘要，与「插件自己 source 的最新可识别可见 catalog 消息」中的同样条目比。变了就 `agent.inject()` 一条 durable 全量替换；全删则发一条显式空替换 | `skills.md:233` |
| 「These catalog messages are **session history, not World State**」 | `skills.md:233` |

### 3.7 `user-questions.md` —— 与 approval 的关键不对称

**`user-questions` 在 44 个 session 事件类型里一个也没有。** 问了人什么、人答了什么，**不进日志**。

| 事实 | 出处 |
|---|---|
| `AskUserQuestionIntent` 是 tagged union，目前只有 `{kind:'plan-review', approve: string}`。「An intent changes **presentation only, never the protocol**」——不认识 tag 的 UI 渲染通用选项列表，答案编码完全相同 | `user-questions.md:25-44` |
| `approve` **按名字而非位置**指定肯定项：「Named rather than positional so **no UI infers the verdict from option order**」。`approve` 指向本问题没有的选项 → `ask()` 直接拒绝 | `user-questions.md:38-43` |
| 单选时 `custom` 覆盖选中项且 `selected` 为空；多选时 `custom` 补充 `selected`。空 `selected` + 无 `custom` = **被跳过的问题**（在整批完成的情况下保留这个事实） | `user-questions.md:89` |
| `ask()` 的两个专门错误码：`CALLER_NOT_LIVE`（不是 registry 的精确活实例）、`DELEGATED_CALLER`（该活 agent 被另一个 agent 拥有）。理由：「an owned child has **no human answerer and would block forever**」 | `user-questions.md:159-174` |

> **给 finaudit 的判断：这个不对称不要抄。**
> harness 里「问人要许可」被审计（approval/*），「问人要信息」不被审计（user-questions）。
> 对财务审计场景，**「向人确认了什么口径、人怎么答的」恰恰是必须进证据链的**。
> 应当把 user-questions 那一侧也做成一等日志事件。

### 3.8 `plan.md` / `permission-presets.md` —— 「模式」如何持久化

| 事实 | 出处 |
|---|---|
| `plan/mode: { active: boolean }` —— log-only、非 surface、**整值替换**。`foldPlanMode(events, end?)` 返回前缀里最后一个值，没有则 `false`。「the state in force is **always a pure fold of the session log**, so resume, fork, and compaction recover it with no live mirror」 | `plan.md:11` |
| plan mode 是**软引导**。sandbox mode 与 approval policy **独立强制**，「neither reads nor writes plan state」 | `plan.md:5` |
| 因为 session 事件是 turn 包围的，用户选择保持 pending 直到下一个被接受的 in-turn pre-step 才追加。`set()` 返回 `'committed' \| 'queued' \| 'cancelled' \| 'noop'` —— **四态返回值把「已落库/排队中/取消了一个反向 pending/本来就是这样」分开** | `plan.md:15`, `:76-81` |
| 模式切换**只在模型可见状态真的变了时**才叙述一次：与最后一条 `request/header` 处的 fold 比较。净零翻转（plan → back，都在边界前）什么也不叙述 | `.agents/notes/archived/feature/2026-07-07-plan-mode.md:134` |
| `exit_plan_mode` 在 plan mode 未激活时**仍然注册**，「so entering or leaving plan mode changes only the prompt section, **never the request tool catalog**」（KV cache 友好）；未激活时执行会失败 | `plan.md:33` |
| 「继续规划」是一次**失败的调用**，携带用户的反馈 —— 让模型带着方向修改后重新提交 | `plan.md:33` |
| `permission/preset` 是「durable, log-only **user intent**」，本身不执行任何东西；两个真正的旋钮（`sandbox/mode`、`approval/policy`）各自通过自己的 setter 写入，且**只在该旋钮生效值确实变化时**才写 | `permission-presets.md:66-68` |
| `custom` 是**派生**的「不是任何预设」状态，保留名，**永远不是切换目标也不是事件负载** | `permission-presets.md:48` |
| 组合期就 fail-fast：表里有名为 `custom` 的条目 → 抛；在不 confine 的 bash executor 上组合 → 抛 | `permission-presets.md:44` |

### 3.9 `persistence-catalog.md` —— 44 个事件类型的全名单

**只有 3 个是 surface（进模型历史），41 个是 log-only。**

surface（3）：`user/message`、`assistant/message`、`tool/result`

log-only（41）：
`agent/inbox/spliced`、`agent-preset/selected`、
`approval/asked`、`approval/decided`、`approval/policy`、
`assistant/chunk`、
`command/done`、`command/run`、
`compaction/end`、`compaction/prune`、`compaction/start`、`compaction/summary`、
`feedback/record`、`goal/change`、
`hook/invoked`、`hook/result`、
`llm/retry`、`llm/retry-started`、
`permission/preset`、`plan/mode`、
`request/context`、`request/header`、
`sandbox/mode`、`schedule/change`、
`session/end-seed`、`session/title`、`session/title-llm-request`、
`step/end`、`step/start`、
`subagent/descriptor`、`todo/write`、
`tool/call`、`tool/code-dispatch`、`tool/code-dispatch-start`、
`tool-workflow/{run-start,run-end,agent-start,agent-end}`、
`turn/end`、`turn/start`、
`web/deepseek-search-llm-request`

关键单条：

| 事件 | 要点 | 出处 |
|---|---|---|
| `request/header` | `{ header: EpochHeader; reason }`，`EpochHeader = { config, adapterDefaults?, system?, tools? }`。**每个请求的完整信封都进日志**，`foldRequestHeader` 选最新快照重建。空 system / 空 tools 用**字段缺席**表示（canonical form） | `session.md:154-176` |
| `request/context` | 路由容量元数据**刻意排除在 `EpochHeader` 之外**：「capacity describes a route, **not a request input**」，折进去会让容量变化被登记成请求信封的 `change`，并把 adapter 元数据拖进 loop 的重建不变量 | `session.md:180` |
| `tool/call` | `arguments` 是**模型原样产出的未解析 JSON 字符串** | `persistence-catalog.md:736` |
| `tool/result` | `meta?: JsonValue` 对 core 不透明（产出工具自己拥有形状），但**必须 JSON 可序列化**：`Session.append` 用 `isJsonValue` 运行时校验，「a non-serializable `meta` is **rejected at the source**, and the durable log reproduces the identical card on replay」 | `persistence-catalog.md:796-813` |
| `hook/invoked` / `hook/result` | 靠 `handlerId` 配对；result 带 `decision`、`exitCode?`、**`stderrSummary?`（有界）**、`durationMs` | `persistence-catalog.md:439-468` |
| `feedback/record` | `{ text: string }`。「Log-only and **independent of its trigger**; it **never enters model context or derived history**」 | `persistence-catalog.md:399-403` |
| `web/deepseek-search-llm-request` | 「**Secret-free** auxiliary DeepSeek search request recorded **before dispatch**」 | `persistence-catalog.md:940` |
| `turn/end` | `TurnEndReason` 是 merge-extensible 和类型：`completed` / `aborted{reason}` / `blocked` / `error{error: LlmFailure}` / `max-tokens` / `interrupted`。**`interrupted` 是唯一没有 loop 会发出的原因**，由崩溃恢复合成 | `session.md:549-575` |
| `session/end-seed` | 空负载，**位置和 `time` 承载全部含义**。「seed history and live work are otherwise **byte-identical**」 | `session.md:583-591` |

### 3.10 `session.md`（部分）—— 派生规则

`deriveMessages()` 的投影规则（`session.md:523-530`），三条对 finaudit 有用：

1. 原始 `assistant/chunk` 在派生时**被跳过**（组装好的 message 才是权威）——
   但它们仍然**必须无损持久化**，`seq` 必须连续，「chunks cannot be filtered out of the canonical log」
   （`session.md:603`）。**证据保留 ≠ 模型可见。**
2. **空内容的 `assistant/message` 也被跳过**：max-tokens 截断的 step 仍然记一条
   `assistant/message` 来存放 usage / provider / model，但「a content-less assistant turn
   **must not enter the provider transcript**」。
3. `deriveEventMessage(event)` 是**公开的**逐节点纯函数，「public so external reconstructors and the
   dev invariant project a log prefix with **exactly the same rules and cannot disagree with the
   cache**」。—— 独立复核方与内部缓存共用同一个函数，无法产生分歧。

耐久性契约（`session.md:603`）：全部 `event.data` 必须 JSON 可序列化，`Session.append` 在源头强制，
所以 `session.events` **永远等于** backend 能持久化的东西。
「Adding an event type that carries non-serializable data […] is a **breaking change to the on-disk
format**.」

### 3.11 `testing.md` —— 验证纪律（与 finaudit 的 VERIFY 模式同构）

| 规则 | 原文位置 |
|---|---|
| 覆盖率门禁是 `packages/*/*/src` **每文件 100%**。「An uncovered line is often **dead code the gate is correctly flagging for deletion**, not a missing test to bolt on.」而且「Line coverage is **necessary, never sufficient**」 | `testing.md:10` |
| **「验证世界，不验证自述」**：「An e2e assertion **re-runs the command or re-reads the file externally**; a keyword probe on the agent's own output **lets a cheating agent pass**.」还要断言未触碰的文件逐字节相同 | `testing.md:29` |
| **「守卫只有在回归真的能让它失败时才是守卫」**：「introduce the regression, **watch red**, revert」 | `testing.md:34` |
| 「Real entry path」= 已发布的构件：`bin` 跑构建后的 `lib/bin.js`，用**纯 node**，暴露 tsx 会掩盖的失败 | `testing.md:35` |
| 每个非平凡的模型/协议/人可见变更，**必须在同一个 PR 里**增改一个 keyless 场景快照。「Package tests, e2e assertions, mock/test-only compositions, and **PR rationale do not replace the assembled transcript**」 | `testing.md:49` |
| 只有一个 ACP 场景（`text-turn`）钉死完整 system-prompt / tool-schema 内容，其余 fixture 把它 token 化，「so an edit churns one line」 | `testing.md:12` |
| CI 强制 `DSH_SNAPSHOT=replay` 只读，**从不写期望输出**；record/refresh 只在本地做，每个 diff 都要人看 | `testing.md:13` |

---

## 4. 对 finaudit-agent 证据链字段集（U-01）的具体输入

**以下每条都有原文依据，出处标在括号里。没有依据的推论不写。**

### 4.1 结构层：把「证据」和「模型可见」彻底分开

harness 的比例是 **3 : 41**（3 个 surface 事件 vs 41 个 log-only）。
`docs/persistence-catalog.md:10` 的定义可以直接借词：

- **surface** = 产生 LLM message，并声明它如何加入 surface 列表
- **log-only** = 「a durable, replayable record with **no derived-history contribution**」

→ **finaudit 的证据链事件（口径选择、准则引用、执行哈希、拒答理由）全部应当是 log-only。**
它们进证据链，不进模型上下文。模型可见的只有回答本身与被引用的数据切片。
`assistant/chunk` 的处理是范本：**无损持久化，但派生时跳过**（`session.md:526`, `:603`）。

### 4.2 信封字段（可直接照搬的最小集）

```ts
// 依据 docs/persistence-catalog.md:58-90
{
  type: <事件类型>,
  seq:  number,        // 会话内单调；seq = log.length
  time: number,        // epoch ms
  data: <按 type 判别的负载>,
  ignorable?: true,    // 缺席 = 必需；未知类型且未标记 → 拒绝重建
}
& (type ∈ SurfaceType ? { sourceEventSeqs?: number[], surfaceOp?: SurfaceOp } : {})
```

四条必须一起搬的规则：

1. **`ignorable` 缺席 = 必需。** 论证见 `2026-08-10-session-log-version-mechanism.md:19`：
   忘写标记导致「过度拒绝（不便）」，默认可忽略导致「静默恢复一个被掏空的会话（安全失效）」。
   **finaudit 的结论：证据链事件默认全部 required，任何插件想加可跳过事件必须显式标记。**
2. **`sourceEventSeqs` 三态**：非空数组 / 空数组（只对特定类型合法，表示「确实没有来源」）/ 字段缺席
   （「不记录来源」）。**「空」和「未知」必须能区分**（`persistence-catalog.md:78-85`）。
3. **条件字段用类型层强制**，不用运行时约定。harness 用 `K extends SurfaceEventType ? {...} : object`
   让编译器在 `append()` 调用点就拒绝（`session.md:206-210`）。
4. **全部 `data` 必须 JSON 可序列化，在 `append` 源头运行时校验**，
   保证 `session.events` 恒等于 backend 能持久化的东西（`session.md:603`）。

### 4.3 拒答 / `Refuse` 的形状

harness 的对应物证实了 finaudit 的判断方向，但字段集要合并两处：

```ts
// 持久化侧（依据 user-approval/src/index.ts:44-58）
'audit/asked'   : { id, subject, callId?, reason? }
'audit/decided' : { id, outcome }

// 封闭词表（依据 user-approval/src/types.ts:29）
type Outcome = 'allowed-once' | 'rejected' | 'cancelled' | 'unavailable'

// 消费侧（依据 core/tools/src/index.ts:588-591）
type Decision = { kind:'allow' } | { kind:'deny'; reason: string } | { kind:'ask'; reason?: string }
```

可搬的四条：

- **词表封闭，且区分「人说不」与「问不到人」。**
  `core/tools/src/index.ts:1684-1687` 的意图注释：「so the model can tell a human "no" from an
  **absent approval channel**」。
  → finaudit 的 `Refuse` 至少要三个 reason 分支：
  `missing_definition`（口径不存在）、`rejected_by_reviewer`（人否决）、`no_review_channel`（无复核通道）。
  最后一个必须 fail-closed，不是降级成功。
- **词表外的返回值归一成最保守的那个**（`index.ts:325`：非词表值 → `unavailable`），
  不要泄漏进调用方的 switch。
- **审计对写不进日志就不返回决定**（`approval.md:120-132`）。
  → finaudit：证据链落库失败 = 整个回答失败，不能「答了但没记」。这与 D-003 一致，harness 给了可执行形状。
- **`deny.reason` 是必填 string**（`index.ts:590`），`ask.reason` 才是可选的。
  → 拒答理由不能为空，这一点用类型强制。

### 4.4 「待人复核」的形状 —— harness 只做对了一半

- ✅ 可搬：`AskUserQuestionIntent` 的 **`approve` 按名字而非位置**指定肯定项
  （`user-questions.md:38-43`），且 `approve` 指向不存在的选项时 `ask()` 直接拒绝。
  → finaudit 的复核表单不要用「第一个选项 = 通过」。
- ✅ 可搬：**空 `selected` + 无 `custom` = 显式的「跳过」**（`user-questions.md:89`），
  在整批完成的语境下保留「这一条被跳过了」这个事实，而不是当成未答。
- ❌ **不可搬**：harness 的 user-questions **完全不进日志**（44 个事件类型里没有它）。
- ❌ **不可搬**：harness 的 approval 是 **same-process、同 turn 内**的同步问答
  （`index.ts:150` "Readonly same-process permission question"；`index.ts:120-126` turn 包围理由），
  且崩溃修复**不闭合** `approval/*`。
  → finaudit 若要「提交给人、跨会话再来看」，必须自己设计跨进程的 pending 持久化 + 恢复语义。
  harness 在这里没有可抄的东西。

### 4.5 口径 / 准则的持久化：抄 `plan/mode` + `permission/preset` 的双层

`permission-presets.md:66-68` 的双层拆分对 finaudit 的「口径预设」是精确对应：

| harness | finaudit 对应 |
|---|---|
| `permission/preset` = durable log-only **user intent**，**不执行任何东西**，存在的意义是「当两个 preset 共享同一组旋钮值时，仍能知道用户选的是哪一个」 | `metric_preset` = 用户选的口径包（如「证监会口径」/「IFRS 口径」），log-only |
| 两个真正的旋钮 `sandbox/mode`、`approval/policy` 各自通过自己的 setter 写，**只在生效值真的变化时写** | 具体口径参数（分母、期间、合并范围…）各自独立事件 |
| `custom` 是**派生**状态，永远不是切换目标也不是事件负载 | 「自定义口径」同理：能显示、不能作为选择目标 |

再叠上 `plan/mode` 的 fold 规则（`plan.md:11`）：
**整值替换 + 最后一条胜出 + 无则 fold 到默认值 + 没有活镜像。**
「replaying the log IS the state」（`user-approval/src/index.ts:108`）。
→ finaudit 的口径状态**不要另建一张表**，用日志 fold。resume / fork / compaction 自动正确。

### 4.6 「口径没变就不重写」—— 直接影响 finaudit 的可复核性与成本

`docs/subsystems/approval.md:49`：

> Both policies contribute their complete current meaning to the cache-safe runtime-context snapshot.
> The sourced `user/message` is the durable model-visible input; changing approval state **appends a
> new full snapshot after retained history without rewriting the request header's system prompt**.

`plan.md:33` 同理：`exit_plan_mode` **在 plan mode 未激活时仍然注册**，
「so entering or leaving plan mode changes only the prompt section, **never the request tool catalog**」。

→ finaudit：**口径变更用「在保留历史之后追加一条完整快照」表达，绝不回改 system prompt。**
这既是 KV cache 友好，更重要的是**证据链的单调性**：历史里的每条快照都能对应到当时真实用的口径。

### 4.7 「模型可见 ⟺ 已记录」的可执行定义（最高价值的一条）

`packages/core/agent-loop/src/invariant.ts:39-52` 给出了完全可移植的检查：

```
expected = derive_messages(log)
assert json(request.messages) == json(expected)      # 否则 log-reconstruction desync
assert request.{model,system,temperature,max_tokens,stop,tools} == fold_header(log)
```

三个附加防御同样可搬：

- `prepend: true` —— 「Prevents a **short-circuiting replay listener from silencing the check**」
- `Object.isFrozen(options)` / `Object.isFrozen(options.messages)` —— 请求对象必须冻结
- 派生函数 `deriveEventMessage` **公开导出**，「so external reconstructors and the dev invariant
  project a log prefix with exactly the same rules and **cannot disagree with the cache**」
  （`session.md:523`）

→ finaudit：写一个 `verify_answer_reconstructable(session_log) -> bytes`，
让**外部复核者和内部生成路径调用同一个函数**。这是 AC 级别的验收判据，不是测试用例。

### 4.8 门禁结构（对 `rules/` 的输入）

三层分工（详见 §Q3.4），对应到 finaudit：

1. **静态·所有权**：每个模块必须声明它拥有的不变量，或写明**为什么没有可检查的关系**。
   harness 的规则原文（`AGENTS.md:103`）：「**Without a plausible relationship, an explained empty
   companion is correct**」，且 `verify-package-invariants` 会**机械拒绝**未加解释的空实现、
   拒绝拿了 reporter 却不用的实现。
   → 这正是 `rules/failure-modes.md` 第 2 条（「只有真实字段能诚实触发时才声明 flag」）的可执行版本：
   **不是禁止空，是禁止「没有解释的空」和「凑出来的非空」。**
2. **静态·词表新鲜度**：从源码生成事件目录，`--check` 模式 diff。
   → finaudit 的证据链字段集应当**从代码生成文档**，而不是手写文档再对照代码。
3. **运行时·关系**：只断言权威事件流或可变数据，不断言服务存在、方法存在、插件元数据。

---

## 5. 我没读，因此不能置评

**文档：**

- `docs/api-gateway.md`（164 行）—— 不知道 API 网关如何暴露 session/approval
- `docs/config-catalog.md`（3151 行，生成物）—— 不知道任何配置项的确切默认值与校验规则
- `docs/development.md`（171 行）—— 不知道 TypeScript 工程布局与本地开发流程
- `docs/architecture.md`（129 行）、`docs/module-graph.md`（1638）、`docs/tool-catalog.md`（1873）
- `docs/postmortem/` 全部 5 篇 —— **不知道它真实踩过哪些坑**，这对 finaudit 本该是高价值的
- `docs/user/` 全部 13 篇 —— 不知道对外用户文档怎么组织，也不知道 Python SDK 的形状
- `docs/cordis-primer.md` / `cordis-api/*` / `cordis-tutorial/*` —— **不了解底层框架 Cordis 的
  Context/Service/Fiber/effect 模型**，所以本报告里凡涉及「effect 绑定」「fiber 处置」「waterfall 语义」
  的转述都是照抄文档措辞，不是我理解后的判断
- `subsystems/` 剩余 26 篇（清单见 §1.3）。其中对 finaudit 可能重要而我没读的：
  - `tools.md`（720 行）—— 工具注册/限制/执行管线的完整契约，我只读了 approval 相关的 60 行
  - `compaction.md` 上轮读过，但 `persistence-catalog.md` 里 `compaction/*` 四个事件的负载我没读
  - `session-telemetry.md`、`feedback.md`、`session-title.md` —— 不知道遥测与人工反馈的完整形状
  - `sandbox.md`、`credentials.md` —— 不知道沙箱与凭据的隔离机制
  - `subagent.md`（734 行）—— 不知道子 agent 的证据链如何与父会话关联，
    只从 `subagent/descriptor` 的一段 JSDoc 知道它「appended once by the establishing provider
    inside the child's initial turn, before its first request」

**具体未读片段：**

- `persistence-catalog.md` 176-395 —— `assistant/chunk`、`assistant/message`、`command/*`、
  `compaction/*` 的完整负载声明。**所以我不能说 `assistant/message` 的确切字段集。**
- `persistence-catalog.md` 636-659 —— `session/title`、`session/title-llm-request` 的负载
- `session.md` 1-153 / 234-520 / 607-849 —— `SessionEventMap` 词表全文、`Session` 公开 API
  （359-520）、`ctx.sessions` 生成段。**所以我不能说 `Session.append()` 的完整签名与前置条件。**
- `session-query.md` 1-279 / 390-495 —— 搜索/过滤/游标语义
- `goal.md` 121-277 —— 请求与通知类型的其余部分
- `packages/core/session/src/invariant.ts` 81-250 —— session 不变量的其余检查
  （我只读到 `turn/start` 分支）
- `packages/core/tools/src/index.ts` 的其余约 1800 行 —— 工具执行管线主体
- `.oxlintrc.json`（11040 字节）—— **我没有逐条读它的规则。所以 Q3 里「不是 lint 规则」这个判断，
  依据是「grep `model-visible` 在 `.oxlintrc.json` 中零命中」以及「未在 lint 配置中发现相关自定义规则」，
  而不是「我读完了全部 lint 规则并确认没有」。**
- `.gitlab-ci.yml`（5453 字节）—— 我从 `scripts/run-gates.ts` 推断了门禁聚合的构成，
  但**没有读 CI 配置本身**，所以不能断言这些 gate 在 CI 里的实际触发条件（哪些是 PR 必过、哪些是夜间）。

**因克隆失败而完全缺失的：**

- `packages/client/ui-primitives/tests/fixtures/markdown-dom/*.streaming.txt` 中的 2 个文件
  （Windows 路径长度限制，`core.longpaths=true` 后已修复，最终 `git status` 干净）——
  实际影响为零，但如实记录。
