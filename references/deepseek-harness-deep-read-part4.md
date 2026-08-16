# deepseek-harness 深读 · 第四轮 —— 会话持久化与查询的完整契约

仓库快照：`deepseek-ai/deepseek-harness`，默认分支 `master`，TypeScript / MIT，`SESSION_FORMAT_VERSION = 0`
（`packages/core/session/src/types.ts:56`，字面量 `0`，pre-release 无兼容承诺）。

本轮目标：把前三轮反复出现的「所以我不能说 X 的确切字段集」补掉。

---

## 0. 读到什么程度（逐文件自报）

⚠️ **任务书给的两个路径不存在，已改用真实路径：**

| 任务书写的 | 真实路径 |
|---|---|
| `docs/subsystems/persistence-catalog.md` | **`docs/persistence-catalog.md`**（不在 `subsystems/` 下） |
| `docs/cordis-primer.md`（以为是大文档） | 存在，但**只有 44 行**；真正的 Cordis API 细节在 `docs/cordis-api/*.md` |

| 文件 | 总行数 | 读到什么程度 |
|---|---|---|
| `docs/subsystems/session.md` | 849 | **读完**（1-160 / 160-530 / 530-849 三段覆盖全文） |
| `docs/persistence-catalog.md` | 944 | **读完**（1-200 / 200-640 / 636-945） |
| `docs/subsystems/session-query.md` | 495 | **读完** |
| `packages/core/session/src/known-event-types.ts` | 64 | **读完**（本轮最关键的一手证据） |
| `packages/core/session/src/invariant.ts` | 251 | **读完**（任务书只要 81-250，我读了全文） |
| `packages/core/agent-loop/src/invariant.ts` | 63 | **读完** |
| `packages/session-query/session-query/src/tracing.ts` | 249 | **读完**（`traceEvent` 的真实实现） |
| `docs/subsystems/invariants.md` | 88 | **读完** |
| `docs/cordis-primer.md` | 44 | **读完** |
| `docs/cordis-api/fiber.md` | 375 | **读完** |
| `.gitlab-ci.yml` | 129 | **读完** |
| `.github/workflows/ci.yml` | 938 | **读完** |
| `lefthook.yml` | 62 | **读完** |
| `.agents/notes/implemented/simplification/2026-08-03-omit-invariants-from-shipped-config.md` | 31 | **读完**（直接回答 Q4 后半） |
| `packages/core/session/src/surface.ts` | 460 | **读了 15-27、170-269**（surface 类型常量 + 校验函数）；其余未读 |
| `packages/core/session/src/index.ts` | ~1400 | **读了 560-675**（`append` 全文 + `requestHeader` 开头）；其余未读 |
| `scripts/run-gates.ts` | 890 | **读了 185-280、354-430、497-610**（各 CI aggregate 的 gate 清单）；其余未读 |
| `.oxlintrc.json` | 321 | **只读了 1-60 + 结构 grep**；321 行规则表未逐条读 |
| `packages/core/agent-loop/src/tool-calls.ts` | ~300 | **只读了 270-290**（`tool/result` 的 append 点） |
| `packages/core/agent-loop/src/agent.ts` | ~600 | **只读了 375-395**（`assistant/message` 的 append 点） |
| `docs/subsystems/session-telemetry.md` | 194 | **只读了 1-70** |
| `docs/api-gateway.md` | 164 | **只读了 1-60** |
| `docs/cordis-api/context.md` | 364 | **未读** |
| `docs/cordis-api/events.md` | 207 | **未读** |
| `docs/cordis-api/registry.md` / `service.md` / `inherited.md` | 152/102/39 | **未读** |
| `docs/subsystems/credentials.md` | 133 | **未读** |
| `docs/subsystems/sandbox.md` | 218 | **未读** |
| `.oxlintrc.staged.json` | 12 | **未读**（命令链被前一条报错截断） |
| `docs/subsystems/persistence.md` | ? | **未读**（本轮不涉及后端落盘） |
| `docs/postmortem/`、`subsystems/tools.md`、`subsystems/subagent.md` | — | **按要求避开**，另一个 subagent 在读 |

---

## 1. 四个必答问题

### Q1 · `Session.append()` 的完整签名与前置条件

**签名**（`packages/core/session/src/index.ts:604-608`，与 `docs/subsystems/session.md:472-476` 的 public-api 块逐字一致）：

```ts
append<T extends SessionEventType>(
  type: T,
  data: SessionEventMap[T],
  ...opts: T extends SurfaceEventType ? [opts: SurfaceIntent] : []
): SessionEvent<T>
```

**类型层强制（前两轮的说法基本正确，但措辞要修正一处）：**

前两轮说「`sourceEventSeqs` 与 `surfaceOp` 用 `K extends SurfaceEventType ? ... : object` 在类型层强制」——
这个条件类型确实存在，但它在的是 **`SessionEvent` 的信封定义**（`types.ts:404` 附近，
`docs/subsystems/session.md:231-243`），**不是 `append` 的参数**。`append` 用的是另一个机制：
**可变参数元组** `...opts: T extends SurfaceEventType ? [opts: SurfaceIntent] : []`。
两者配合的效果是：

- `T` 是三个 surface 类型之一 → 第三个参数**必填**（元组长度 1）
- `T` 是其余 41 个 log-only 类型 → 第三个参数**编译期禁止**（元组长度 0）

**必填 / 条件必填的确切划分**（`SurfaceIntent`，`docs/subsystems/session.md:299-308`）：

```ts
interface SurfaceIntent {
  surfaceOp: SurfaceOp          // 必填（对三个 surface 类型而言）
  sourceEventSeqs?: number[]    // 可选
}
```

| 字段 | surface 事件 | log-only 事件 |
|---|---|---|
| `type` | 必填 | 必填 |
| `data` | 必填 | 必填 |
| `opts.surfaceOp` | **必填** | 编译期拒绝 |
| `opts.sourceEventSeqs` | 可选（见下面的空数组规则） | 编译期拒绝 |
| `seq` / `time` | **不由调用方给**，`append` 自己盖 | 同左 |
| `ignorable?: true` | 信封字段，**`append` 不接受**，只有外部写入者（更新版 harness）才会带 | 同左 |

`seq = this.log.length`、`time = Date.now()`，见 `index.ts:629-630`。

**append 时的运行时校验（按代码执行顺序，`index.ts:609-634`）：**

1. `snapshotJsonValue(data)` —— 无损 JSON 快照。返回 `undefined` 即拒绝。
   文档列举的拒绝清单（`session.md:458-462`）：BigInt、function、symbol、`undefined`、
   **负零**、非有限数、循环引用、稀疏数组、以及 Map/Set/Date/class 实例这类 exotic object。
   注意这是 **一次递归遍历同时完成读取+校验+拷贝**，所以「有状态 getter 给校验一个值、给存储另一个值」这条攻击路径被堵死（`session.md:463-465`）。
2. `assertSupportedRequestHeader(type, dataSnapshot, ...)` —— 拒绝 legacy v0 的
   `request/header-delta` 事件与 `fallback` reason（`session.md:176`）。
3. `snapshotJsonValue(surfaceMetadata)` —— surface 元数据也要过同一道 JSON 校验。
4. **重入检查**：`if (entry?.appending) throw` —— 「另一个 append 正在发布期间不得重入」（`index.ts:624-626`）。
5. `deepFreeze({...})` —— 事件与其嵌套 data 在接受时深冻结。
6. `this.surfaceManager.validateNext(event)` —— surface 契约校验，
   实现在 `packages/core/session/src/surface.ts:184-243`，具体见下面 Q3。

**失败时抛什么：** 全部是**普通 `Error`**，不是自定义 error 类，没有 `code` 字段。
实测到的消息串（`surface.ts` / `index.ts`）：

- `session event "<type>" carries non-JSON-serializable data`（`index.ts:616`）
- `session event "<type>" carries non-JSON-serializable surface metadata`（`index.ts:621`）
- `session append cannot reenter while another append is being published`（`index.ts:625`）
- `session event "<type>" is not surface-eligible and cannot carry surfaceOp`（`surface.ts:189`）
- `session event "<type>" is not surface-eligible and cannot carry sourceEventSeqs`（`surface.ts:192`）
- `session event "<type>" is surface-eligible and requires a surfaceOp marker`（`surface.ts:198`）
- `sourceEventSeqs must not be empty except on assistant/message`（`surface.ts:222`）
- `sourceEventSeqs must not contain duplicates`（`surface.ts:233`）
- `sourceEventSeqs must reference earlier events: <n> >= current seq <m>`（`surface.ts:236`）
- `surface replace: sourceEventSeqs must include every shadowed surface node; missing …`（`surface.ts:241`）
- `surface replace: start seq <n> not found in surface`（`surface.ts:252`）

**关键的 fail-closed 立场**（`session.md:465-467`）：
> 事件日志是持久真相源，所以坏事件在 **append 调用点**就失败，而不是稍后在后端 flush 时失败。

**一个容易误读的点：** append **不做**关系性校验（turn/step 嵌套、tool call/result 配对）。
那些在**可选的** `dsh-session/invariant` companion 里（见 Q4）。append 只保证
「JSON 无损 + surface 契约」，不保证「turn 编号连续」。

---

### Q2 · `SessionEventMap` 一共多少个事件类型 —— 前两轮的 44 / 41 / 3 **核实为正确**

**一手证据**：`packages/core/session/src/known-event-types.ts:19-64`，
这是 `scripts/gen-persistence-catalog.ts` **生成**的常量（文件头 1-6 行注明），
由 `pnpm run verify-persistence-catalog` 在 doc-sync gate 里验新鲜度。

我逐条数了 `KNOWN_SESSION_EVENT_TYPES` 这个 `ReadonlySet<string>`：**恰好 44 条**。

surface 类型的一手证据是 `packages/core/session/src/surface.ts:15-19`：

```ts
const SURFACE_EVENT_TYPES = new Set<string>([
  'user/message',
  'assistant/message',
  'tool/result',
])
```

**结论：44 个事件类型，3 个 surface，41 个 log-only。前两轮的数字正确。**

但要补三条前两轮没说的限定：

1. **44 ≠ 核心声明。** `dsh-session` 自己只声明 **13** 个
   （`docs/persistence-catalog.md` 里 source 指向 `packages/core/session/src/types.ts` 的那些）。
   另外 **31** 个是各插件通过 TypeScript **declaration merging** 并进来的。
2. **44 是「本 build 认识的词表」，不是「任一组合实际会写出的集合」。**
   `known-event-types.ts:9-17` 的原话是「Every `SessionEventMap` member declared in **this repository**」；
   仓库外的下游插件事件按构造不在此列。
3. **44 是 fail-closed 的读路径依据。** 持久化读路径遇到不在这个集合里的类型时**拒绝解释整个 log**，
   除非该事件带 `ignorable: true` 标记（`known-event-types.ts:10-14`）。
   `ignorable` 缺省即「必需」——「忘了标记导致过度拒绝（不便），好过静默恢复一个被掏空的 session」
   （`types.ts` 的信封 JSDoc，`session.md:220-229`）。

---

### Q3 · `SessionEventTrace` 的确切形状与回溯机制 —— **本轮最重要的发现**

**声明**（`docs/subsystems/session-query.md:307-323`，与
`packages/session-query/session-query/src/types.ts:105-118` 对应）：

```ts
interface SessionEventTrace {
  target: SessionEventRecord   // { sessionId, seq, type, time, surface }
  replacedBy?: number          // 直接把 target 顶掉的那个事件（target 被 shadow 时才有）
  replacementChain: number[]   // 从直接替换者一路到最终替换者 —— 唯一传递闭包的字段
  replacedEventSeqs: number[]  // target 自己作为替换者时，直接移除的 surface 节点
  sourceEventSeqs: number[]    // target 直接引用的更早事件（记录顺序）
  derivedEventSeqs: number[]   // 后来直接引用 target 的事件（log 顺序）
}
```

`SessionEventTraceObservation extends SessionEventTrace`，多一个 `session: SessionHeader`
（同一次 corpus 观测的 header 克隆，`session-query.md:325-331`）——
**这是原子性保证：trace 与它的 header 来自同一次观测，不会串。**

**它怎么回溯？答案是「两条腿，且都只走信封字段，不走业务 id」。**

看 `packages/session-query/session-query/src/tracing.ts:216-218` 的实现：

```ts
function eventSources(event: SessionEvent): readonly number[] {
  return (event as SessionEvent<SurfaceEventType>).sourceEventSeqs ?? []
}
```

**只读信封上的 `sourceEventSeqs`，没别的。** 两条腿分别是：

| 腿 | 机制 | 传递性 | 代码位置 |
|---|---|---|---|
| **来源引用** | `sourceEventSeqs`（后向）+ 全 log 扫描求逆得 `derivedEventSeqs`（前向） | **只一跳** | `tracing.ts:87-91, 102-103` |
| **位置替换** | `foldSurface()` 产出的 `replacedBy` map | `replacementChain` **是传递的**（while 循环） | `tracing.ts:80-85, 193-199` |

**它明确不走的：业务 id 配对。** 尽管负载里到处是配对 id ——
`callId`（`tool/call`↔`tool/result`）、`commandId`（`command/run`↔`command/done`）、
`handlerId`（`hook/invoked`↔`hook/result`）、`compactionId`、`subCallId`、
`ApprovalRequestId`（`approval/asked`↔`approval/decided`）——
**`traceEvent` 一个都不跟。**

**一个特别值得注意的近似陷阱：** `command/done` 的**负载**里有个字段叫
`sourceEventSeq`（**单数**，`persistence-catalog.md:255`），语义是「指向更早的权威 domain 事件」。
它跟信封上的 `sourceEventSeqs`（复数）**同名近似但完全无关**，`traceEvent` 不读它。
拿这个当证据链会静默漏掉。

**那么真实的证据链是怎么被写进去的？** 我查了全仓库的 `sourceEventSeqs` 生产者
（非测试代码只有 5 处）：

| 事件 | 引用了什么 | 代码位置 |
|---|---|---|
| `assistant/message` | `chunkSeqs` —— 组装出这条消息的全部 `assistant/chunk` 的 seq | `packages/core/agent-loop/src/agent.ts:389` |
| `tool/result` | `[callSeq]` —— **对应 `tool/call` 事件的 seq** | `packages/core/agent-loop/src/tool-calls.ts:288` |
| `tool/result`（剪枝替换） | `[seq]` | `packages/compaction/compaction-tool-result-pruner/src/index.ts:172` |
| `user/message`（压缩摘要替换） | `[startEvent.seq, summaryEvent.seq, ...shadowedSeqs]` | `packages/compaction/compaction-basic/src/region.ts:464` |
| `tool/result`（崩溃修复合成） | `[callSeq]` | `packages/core/session/src/repair.ts:122` |

**所以真实的链条长这样：**

```
assistant/chunk[]  ──sourceEventSeqs──▶  assistant/message
                                              │
                                    (模型在消息里请求了工具)
                                              ▼
                                         tool/call  ← log-only！不能带 sourceEventSeqs
                                              │
                                     ──sourceEventSeqs──▶  tool/result
```

**这里有一个结构性缺口，对 finaudit 极其重要：**

`tool/call` 是 **log-only**（`persistence-catalog.md:726-741`），
而 `sourceEventSeqs` 在类型上**只存在于三个 surface 类型**上
（`types.ts` 的条件类型；`surface.ts:191-193` 运行时也拒绝）。
所以 **`tool/call` 在结构上无法引用产生它的 `assistant/message`。**
这一跳只能靠 `(turn, step)` 同属关系推断，**不是显式引用**。

换句话说：**deepseek-harness 的证据链在「模型决定调用工具」这一跳是断的**，
靠的是 turn/step 共处 + `dsh-session/invariant` 的同步校验
（`packages/core/session/src/invariant.ts:122-144`：`tool/call` 把 `callId` 加进
`pendingCalls`，`tool/result` 检查 `pendingCalls.has(callId)`，`step/end` 清空），
而那个 invariant **默认不挂**（见 Q4）。

`sourceEventSeqs` 的完整校验规则（`surface.ts:210-243`）：

- 必须是数组
- **空数组只有 `assistant/message` 允许**（语义：provider 流已知为空）；其余 surface 事件空数组即拒绝
- 元素必须是非负 safe integer
- **不得重复**
- **必须严格早于当前 seq**（`source >= event.seq` 即拒绝）
- 若是 `replace` 操作，**必须包含每一个被 shadow 的 surface 节点**，缺一个就拒绝
- 字段**缺席**与**存在但为空**语义不同：缺席 = 「本事件不记录它由什么产生」，
  是 legacy/foreign 事件的形态（`session.md:249, 313`）

**其余相关查询能力**（`session-query.md:390-495`，`ctx.sessionQuery` 抽象 seam）：

- `traceEvent(request, signal)` → `SessionEventTraceObservation`
- `readEvent(request, signal)` → `SessionEventWindow`：目标事件 + `before`/`after` 条原始邻居 + `startSeq`/`endSeq`
- `readSession(id)` → `SessionLogSnapshot`：**replay 校验过**的完整原始 log
- `readSurface(id)` → `SessionSurfaceSnapshot`：当前模型 surface + `capturedThroughSeq`
- `traceSession(id, signal)` → `SessionLineageTrace`：会话血缘（父链 + 后代森林），
  用 `complete: true/false` 判别式区分「根已知」与「父链走出可见语料」——
  **不会用 `undefined` 糊过去**
- `filterEvents(id, filters)` → `SessionEventSearchDocument[]`：ANDed 过滤，
  `text` 子句是「字面 Unicode、大小写不敏感、空白弹性」的正则扫描，**不依赖全文索引后端**
- 语义文本的来源（`session-query.md:141`）：messages、reasoning、tool calls/results、
  blocked prompts、todos、failure/status detail 贡献；**结构性事件与流 chunk 不贡献**

错误分类是**封闭 union**，17 个稳定码（`session-query.md:337-357`），
包括 `SESSION_QUERY_CORRUPT_SESSION`、`SESSION_QUERY_INVALID_SURFACE`、
`SESSION_QUERY_SOURCE_CONFLICT`、`SESSION_QUERY_STALE_CURSOR`。

---

### Q4 · 门禁的真实构成 —— 前两轮的推断**方向对但对象错了**

#### 4a. `.gitlab-ci.yml` 根本不是代码门禁

`.gitlab-ci.yml:1-4`：

```yaml
workflow:
  rules:
    - if: '$CI_COMMIT_TAG =~ /^python-v[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$/'
    - when: never
```

**只在 `python-v*` tag 上跑，其余一律 `never`。** stages 只有 `build` / `publish`，
5 个 job（`sdk-wheel`、`runtime-linux-x64`、`runtime-linux-arm64`、`runtime-macos-arm64`、
`publish-python`），干的全是 Python wheel 构建与 twine 发布。
**零 lint、零 typecheck、零 test。**

所以「从 `.gitlab-ci.yml` 读门禁构成」这个前提本身不成立。真正的门禁在
**`.github/workflows/ci.yml`**。

#### 4b. PR 必过的 job（确切答案）

`.github/workflows/ci.yml:915-937` 的 `all-checks-passed` 是**分支保护的唯一 required check**
（注释原话：单一稳定 required check，而不是枚举名字会变的 matrix leg）。它的 `needs`：

```yaml
needs: [node-24, node-24-coverage, node-24-consumers, node-compat, python-sdk, python-runtime, windows]
```

**7 个必过 job：**

| job | name | 跑什么 |
|---|---|---|
| `node-24` | node 24 / static | `pnpm run check:ci:static` |
| `node-24-coverage` | node 24 / coverage | `pnpm run check:ci:coverage` |
| `node-24-consumers` | node 24 / snapshots and artifacts | `pnpm run check:ci:consumers` |
| `node-compat` | node 22.19 / node 26（matrix 2 leg） | `pnpm run check:node-compat` |
| `python-sdk` | python 3.10 / keyless SDK | `pytest` |
| `python-runtime` | python runtime / release-shaped Linux x64 | 复用 `build-exe-for-python-sdk.yml` |
| `windows` | windows node 24 / wine blocking | `scripts/wine-windows-gates.sh`（**Wine 跑 Windows Node**，不是真 Windows） |

**明确不必过的：**

- `windows-native`（真 Windows 内核完整清单）—— 注释原话：**「deliberately absent from
  `all-checks-passed.needs`，所以它的独立结论永不延迟或改变必过判决」**（`ci.yml:441-443`）
- `serial-linux`、`serial-macos` —— **`if: false`**，已停用
  （`ci.yml:45` 有 `TODO(hosted-serial-ci): Re-enable ... before release`）
- `serial-linux-selfhosted`、`serial-windows` —— **只在 master push 触发**的自建池热备演练，
  PR 不阻塞
- `wine-apt-cache` —— 只在 master push
- 两个 `*-benchmark` —— 只在 `workflow_dispatch`

一个值得学的工程细节（`ci.yml:911-914`）：
`if: always()` 是 load-bearing 的 —— 没有它，依赖失败会让这个 job **skip**，
而 **GitHub 把 skipped 的 required check 算作通过**。所以它总是跑，并对
`failure` / `cancelled` / `skipped` 三种结果一律失败。

各 aggregate 的实际 gate 清单（`scripts/run-gates.ts`）：

- `ci-static`（`:354-372`）= runtime-closure、constraints、dsh-package-licenses、
  **package-invariants**、cordis-config、issue-management + 约 25 条 doc-sync leaf
  （含 **`verify-persistence-catalog`**、`verify-cordis-catalog`、`verify-type-equiv`、
  `verify-translation-pairing`、`verify-doc-budgets` 等）+ module-graph + knip
- `ci-coverage`（`:497-518`）= 两条 `vitest run --coverage`（主 + coverage-exempt-heavy）
- `ci-consumers`（`:387-414`）= build、node-compat、publint、built-package-invariants、
  lint+duplication、snapshot、web-snapshot、doc-typecheck、node-next-types、built-bin-smoke

本地 `lefthook.yml` 只有轻量检查：pre-commit 跑 staged lint / 翻译配对 / 空白 / vendor manifest，
**pre-push 只跑 `pnpm run typecheck`**。文件头原话：本地检查点保持快，
**CI 拥有完整的仓库级 gate matrix**。

#### 4c. agent-loop 那条「llm messages 必须与 `deriveMessages()` JSON 逐字节相等」的检查，实际会跑吗？

**检查本身确实存在**，`packages/core/agent-loop/src/invariant.ts:39-42`：

```ts
const expected = session.deriveMessages()
if (JSON.stringify(options.messages) !== JSON.stringify(expected)) {
  fail(`llm request for session "..." diverges from the dispatch-time durable derivation (log-reconstruction desync)`)
}
```

同一个 listener 还额外校验：request 必须 frozen、必须带 session id、必须是 live session、
`messages` 数组必须 frozen、log 里必须有 `step/start`、必须有 `request/header`，
以及 header 六个字段（model / system / temperature / maxTokens / stop / tools）逐一相等
（`invariant.ts:23-52`）。用 `{ global: true, prepend: true }` 注册，
注释说明 `prepend` 是为了防止「短路的 replay listener 把检查静音掉」。

**但生产默认不挂。** 前两轮说「没有任何出厂 `cordis.yml` 挂 invariants」——
**核实为正确，且实际情况比这更强**。证据是一份专门的 Agent Note：
`.agents/notes/implemented/simplification/2026-08-03-omit-invariants-from-shipped-config.md`
（status: implemented），原文决策段：

> 出厂的 `dsh` 配置树（`apps/cli/config/`）既不挂 `@deepseek-ai/dsh-invariants`，
> 也不挂任何 package-owned `./invariant` companion。CLI 包因此对 invariant 服务
> **没有直接依赖**。

而且有**反向测试**兜底（同文第 17 行）：
> 构建后的 CLI config-dump 测试检查两个出厂 surface，
> **拒绝** service 条目或任何 `@deepseek-ai/dsh-*/invariant` 条目。

被否决的替代方案里明确包括「挂上但 `enabled: false`」——理由是那样出厂树和 CLI 依赖
仍会背着一个装不了任何检查的诊断组件。

我也 grep 了全部 `cordis*.yml` / `*.patch.yml`，**没有任何一个提到 invariants**
（唯一命中的是 `examples/headless-agent/tests/fixtures/e2b/e2b/cordis.yml:1` 一句注释里
的 "One-world invariant"，与本服务无关）。

**那它在 CI 里跑吗？跑，但只在测试里。** `@deepseek-ai/dsh-agent-loop/invariant`
被 9 个测试文件显式 import 并挂载：

- `packages/core/agent-loop/tests/invariant.spec.ts`、`tests/contract-regressions.spec.ts`
- `packages/compaction/compaction-basic/tests/manual-compaction.spec.ts`、`compaction-loop-repro.spec.ts`
- `packages/subagent/subagent-fork-in-process/tests/*.spec.ts`（2 个）
- `packages/subagent/subagent-in-process-driver/tests/*.spec.ts`（2 个）
- `packages/subagent/subagent-spawn-in-process/tests/subagent-spawn-in-process.spec.ts`
- `packages/workflow/workflow-worker-thread/tests/integration.spec.ts`
- 另有 `packages/examples/agent-spine-demo/src/index.ts:30` 在示例的**源码**里挂

这些 `.spec.ts` 走 `vitest run`，属于 `ci-coverage` aggregate，
而 `node-24-coverage` 是必过 job。

**所以确切答案是：**
> 这条不变量在 **CI 的测试 lane 里会跑**（`node-24-coverage` → `check:ci:coverage` → vitest，
> 由 9 个显式挂载它的 spec 覆盖），但**出厂产品默认不挂**，
> 且有一条 config-dump 测试**主动拒绝**它出现在出厂配置里。
> 生产环境的日志完整性靠的是另一套「永远在线」的机制：
> `Session.append` 的 JSON 校验、快照、深冻结、以及 cited source-event 校验
> （Agent Note 第 15 行明确点名这四项 remain always on）。

**一个我需要标注为「读不到」的点：** 我没有找到 `apps/cli/config/` 下的配置树本身，
也没读那个 config-dump 测试的源码。上面「出厂不挂」的结论来自
**Agent Note 的自述 + 我对全部 `cordis*.yml` 的 grep**，
不是来自我亲自读到那份出厂配置并确认其内容。

---

## 2. `SessionEventMap` 完整事件表（本轮主要交付物）

44 条，逐条来自 `docs/persistence-catalog.md`（生成文件）与
`packages/core/session/src/known-event-types.ts:19-64`。
「S」= surface（模型可见，必带 `surfaceOp`）；「L」= log-only。

### 2.1 核心声明（`packages/core/session/src/types.ts`）—— 13 条

| # | 类型 | S/L | 负载关键字段 | 源行 |
|---|---|---|---|---|
| 1 | `turn/start` | L | `{ turn }` | types.ts:243 |
| 2 | `turn/end` | L | `{ turn, reason: TurnEndReason }` | types.ts:252 |
| 3 | `step/start` | L | `{ turn, step }` | types.ts:254 |
| 4 | `step/end` | L | `{ turn, step }` | types.ts:256 |
| 5 | `user/message` | **S** | `UserMessage`（含 `content`、`source` 判别人类提示 / 注入上下文 / goal 续轮） | types.ts:264 |
| 6 | `assistant/chunk` | L | `{ turn, step, chunk: StreamChunk }` —— token 级重放保真 | types.ts:266 |
| 7 | `assistant/message` | **S** | `{ turn, step, message: AssistantMessage, usage?: TokenUsage }` —— **模型输出与其 token 计费同行，无独立 usage 事件** | types.ts:273 |
| 8 | `tool/call` | L | `{ turn, step, callId, name, arguments: string }` —— `arguments` 是模型原样产出的**未解析** JSON 串 | types.ts:279 |
| 9 | `tool/result` | **S** | `{ turn, step, message: ToolResultMessage, error?: { name, code }, meta?: JsonValue }` | types.ts:291 |
| 10 | `todo/write` | L | `{ todos: TodoItem[] }` —— 整表快照，last-write-wins | types.ts:299 |
| 11 | `request/header` | L | `{ header: EpochHeader, reason: RequestHeaderReason }`，reason ∈ initial/resume/change | types.ts:304 |
| 12 | `request/context` | L | `RequestContext { provider, model, contextWindow? }` | types.ts:309 |
| 13 | `session/end-seed` | L | `Record<string, never>` —— **空负载**，位置与 `time` 承载全部含义 | types.ts:332 |

`EpochHeader`（`session.md:164-173`）：`{ config: LlmCallConfig, adapterDefaults?, system?, tools?: ToolSchema[] }`。
**规范形态把空 system / 空 tool list 表示为字段缺席**，与请求构造方式一致。

`TurnEndReasonMap`（`session.md:549-573`）—— 可合并扩展的 sum type，6 个内建 reason：
`completed` / `aborted{reason: TurnEndCancelCause}` / `blocked` /
`error{error: LlmFailure}` / `max-tokens` / `interrupted`。
`interrupted` 是**唯一没有任何 loop 会发出的** reason，由崩溃恢复合成。
`max-tokens` 的语义值得抄：**一个 turn 里任何一 step 触顶，整个 turn 就结束在 `max-tokens` 而非 `completed`
——「被截断」这个事实压过后续的续跑**。

### 2.2 插件 declaration-merge —— 31 条

| # | 类型 | S/L | 负载关键字段 | 声明位置 |
|---|---|---|---|---|
| 14 | `agent/inbox/spliced` | L | `{ target: InboxTarget, start, removedCount?, inserted: UserMessage[], outcome?: 'canceled' }` | core/agent/src/types.ts:19 |
| 15 | `agent-preset/selected` | L | `{ agentPreset: string }` | preset/agent-presets/src/session.ts:26 |
| 16 | `approval/asked` | L | `{ id: ApprovalRequestId, toolName, callId?, reason? }` | interaction/user-approval/src/index.ts:44 |
| 17 | `approval/decided` | L | `{ id, outcome: ApprovalOutcome }` —— **每 ask 恰好一条**，含 fail-closed 的 `'unavailable'` | 同上:55 |
| 18 | `approval/policy` | L | `{ policy: ApprovalPolicy, source?: 'delegation' }` —— **最后一条为准** | 同上:67 |
| 19 | `command/run` | L | `{ commandId, name, args?, source: CommandSource }` —— `args` 是 `parseCommand` 自己的切分，消费者**不再解析** | interaction/commands/src/types.ts:88 |
| 20 | `command/done` | L | `{ commandId, kind: 'success'\|'error', text?, sourceEventSeq? }` ⚠️ 见 Q3 的同名陷阱 | 同上:95 |
| 21 | `compaction/start` | L | `{ compactionId, sourceCommandId?, turn: number\|null }` —— 持锁至 end | compaction/compaction/src/types.ts:23 |
| 22 | `compaction/summary` | L | `{ compactionId, sourceCommandId?, summary: ContentBlock[], shadowedRange{start,end}, shadowedSeqs[], shadowedTokenCount, provider, model, maxTokens?, usage? }` **&** 判别式 `{rawOutput, llmStreamCall: true}` \| `{rawOutput?, llmStreamCall?: never}` | 同上:33 |
| 23 | `compaction/end` | L | `{ compactionId, sourceCommandId?, turn: number\|null, error? }` | 同上:71 |
| 24 | `compaction/prune` | L | `{ shadowedRange{start,end}, shadowedSeqs[], shadowedTokenCount }` | 同上:81 |
| 25 | `feedback/record` | L | `{ text }` —— 永不进模型上下文 | feedback/command-feedback/src/index.ts:62 |
| 26 | `goal/change` | L | `GoalChangeMeta`（完整变更后状态或 clear 墓碑） | goal/goal/src/domain.ts:66 |
| 27 | `hook/invoked` | L | `{ turn, point, dialect: HookDialect, matcher?, handlerId }` | hooks/hook-protocol/src/types.ts:19 |
| 28 | `hook/result` | L | `{ turn, point, handlerId, decision, exitCode?, stderrSummary?, durationMs }` | 同上:31 |
| 29 | `llm/retry` | L | `LlmRetryEventData` | llm/llm-retry/src/types.ts:9 |
| 30 | `llm/retry-started` | L | `LlmRetryStartedEventData` | 同上:11 |
| 31 | `permission/preset` | L | `{ preset: string }` | interaction/permission-presets/src/index.ts:50 |
| 32 | `plan/mode` | L | `{ active: boolean }` —— 最后一条为准，无则折叠为 inactive | plan/plan-mode/src/index.ts:53 |
| 33 | `sandbox/mode` | L | `{ mode: SandboxMode, source?: 'delegation' }` | sandbox/sandbox-policy/src/session-mode.ts:33 |
| 34 | `schedule/change` | L | `ScheduleChange`（带版本；owning package 在接受候选前校验完整的 session-local 转移流） | schedule/schedule/src/types.ts:219 |
| 35 | `session/title` | L | `SessionTitleEventData` —— latest-wins 快照 | session/session-title/src/index.ts:100 |
| 36 | `session/title-llm-request` | L | `SessionTitleLlmRequestEventData` —— **dispatch 前**记录 | session/session-title-llm/src/index.ts:43 |
| 37 | `subagent/descriptor` | L | `SubagentDescriptorData` —— 子 agent 的持久身份与生命周期模式，**在其首个 turn、首次请求之前**写一次，**能挺过压缩** | subagent/subagent/src/descriptor.ts:37 |
| 38 | `tool/code-dispatch-start` | L | `CodeDispatchStartEventData` —— `run_code` 内子调用启动；子调用 id 为确定性的 `<parent>:code:<n>`，**arguments 在 dispatch 前已 JSON 规范化，所以此 append 永不因负载形状失败** | core/tools/src/types.ts:40 |
| 39 | `tool/code-dispatch` | L | `CodeDispatchEventData` —— 子调用结算，用 `tool/result` 自己的词汇（`content` + `isError`），**每个 started 恰好一条**（abort 也算） | 同上:56 |
| 40 | `tool-workflow/run-start` | L | `ToolWorkflowRunStartData` | workflow/tool-workflow/src/types.ts:47 |
| 41 | `tool-workflow/agent-start` | L | `ToolWorkflowAgentStartData` | 同上:52 |
| 42 | `tool-workflow/agent-end` | L | `ToolWorkflowAgentEndData` | 同上:57 |
| 43 | `tool-workflow/run-end` | L | `ToolWorkflowRunEndData` | 同上:62 |
| 44 | `web/deepseek-search-llm-request` | L | `DeepSeekSearchLlmRequest` —— **secret-free**，dispatch 前记录 | web/web-search-deepseek/src/provider.ts:83 |

**⚠️ 关于 14-44 的负载深度：** 编号 26、29、30、34、35、36、37、38、39、40-44 的负载在 catalog 里
是**类型别名引用**（`GoalChangeMeta`、`LlmRetryEventData`、`ScheduleChange`…），
catalog 没展开其内部字段，我也**没有去各自的源文件展开**。
所以对这 14 条我只能说「负载类型名是什么」，**不能说它的确切字段集**。

### 2.3 从这张表读出的三条设计规律

1. **「dispatch 前记录请求」是一个反复出现的模式。**
   `request/header`（`session.md:156`：appended inside its step **before dispatch**）、
   `session/title-llm-request`（pre-dispatch）、
   `web/deepseek-search-llm-request`（recorded **before dispatch**）。
   动机（`session.md:156`）：**「每个 conversation request 都是 log 的纯函数」**。
2. **所有配对关系用显式 id，不用相邻性。** `session.md:597` 把这条写成了硬要求：
   > 当一个插件家族的若干事件组装成一个 Conversation Node 时，
   > 该家族里每个 start / update / result / resource / interruption 事件
   > 都必须携带或独立导出**同一个稳定 business id**，
   > 好让客户端**无需从相邻性猜测或扫描历史**就能分组。
3. **「最后一条为准」（latest-wins）是状态类事件的统一折叠语义。**
   `todo/write`、`plan/mode`、`approval/policy`、`sandbox/mode`、`session/title`、
   `request/header`、`request/context` 全部如此。
   代价：读一个状态要扫全 log；收益：没有增量补丁，没有「patch 丢了怎么办」。
   `request/header` 甚至明确**拒绝** legacy 的 `request/header-delta`（`session.md:176`）。

---

## 3. `Session` 公开 API 与不变量

### 3.1 公开面（`docs/subsystems/session.md:363-518`，与源码 body-stripped 同步）

`Session` 是**普通 class，不是 Service**。live 实例走 `ctx.sessions.create()`，
detached 实例走静态 `Session.create()`。

| 成员 | 签名 | 要点 |
|---|---|---|
| `surface` | `get(): SessionSurface` | `{ nodes: readonly number[], replaceGeneration: number }` |
| `header` | `readonly SessionHeader` | **deep-frozen**；含 format version / cwd / 血缘 / seed 边界。**刻意不进事件日志**——它是存储关切，不是可重放的会话状态 |
| `id` | `get(): SessionId` | 从 header 的**单一副本**导出 |
| `firstLiveSeq` | `readonly number` | **本进程**首个 append 的 seq。与 `header.seedLength`（持久的 fork 血缘边界）**不同** |
| `Session.create(id, seed?, header?)` | static | 校验并快照**借用**的 seed |
| `Session.fromRestore(id, seed, header)` | static | **接管**新鲜持久化值的所有权（调用方不得保留可变别名） |
| `events` | `get(): readonly SessionEvent[]` | 不可变快照，**下次 append 前复用**；已返回的数组永不后长 |
| `seq` | `get(): number` | **恒等于 log 长度**（`seq = log.length` 连续性契约） |
| `append(type, data, ...opts)` | 见 Q1 | — |
| `requestHeader()` | `(): EpochHeader \| undefined` | 增量折叠，每个 header 事件只折一次，单 step 读取 O(新事件) |
| `requestContext()` | `(): RequestContext \| undefined` | 同上 |
| `deriveMessages()` | `(): Message[]` | **有缓存**：每个 surface 节点只投影一次；`replace` 触发重建。**每次调用返回新数组**，但其中的 `Message` 对象是**共享且深冻结**的 |
| `deriveEventMessage(event)` | `(): Message \| null` | 纯函数 per-node 投影的实例面 |

`ctx.sessions`（`SessionStore`，`session.md:623-745`）额外提供
`create` / `prepare` / `enter` / `announce` / `flush` / `get` / `list` / `fork`。

`prepare` + `enter` + `announce` 三段式拆分的理由值得抄（`session.md:647-654`）：
调用方把 session 生命周期**折进自己的那一个 `ctx.effect`**，
使 fiber 卸载时 session + agent 作为**单条有序链**拆除，
而不是**互相竞争的兄弟 effect**——后者会在 driver 的收尾事件提交之前
就把发布 hook 摘掉，**把那些事件丢掉**。

### 3.2 四个 session 事件的 dispatch 模式（`session.md:751-849`）

| 事件 | mode | 语义 |
|---|---|---|
| `session/created` | `emit` | 同步 throw 可**否决并回滚**；返回的 promise rejection 只记日志，**不能追溯否决** |
| `session/disposed` | `emit` | listener 失败被记录并隔离 |
| `session/event` | `emit` | **post-commit、fire-and-forget**。listener 快照在 log push **之前**解析，回调在 push **之后**跑 |
| `session/flush` | `parallel` | **awaited** 持久化检查点，无 waterfall 否决 |

**「一个 log 事件不是一个 cordis 事件」**（`persistence-catalog.md:6` 原话）——
它通过单一的 `session/event` emit 到达 listener。

### 3.3 不变量（分三层，这个分层本身就是可借鉴的）

**第一层：永远在线，在 `Session.append` 内**（Q1 已列）——
JSON 无损、深冻结、surface 契约、`sourceEventSeqs` 校验、重入拒绝。
这层**不依赖任何可选服务**。

**第二层：可选的 `dsh-session/invariant` companion**
（`packages/core/session/src/invariant.ts`，全文 251 行，我读完了）。

它维护一个 per-session 的 `SessionTrace`：
`{ lastSeq, openTurn, openStep, nextTurn, nextStep, pendingCalls: Set<CallId> }`，
校验的关系有（`invariant.ts:55-166`）：

- `seq` **严格递增**
- `turn/start`：不得在已有 open turn 时开；编号必须等于 `nextTurn`
- `turn/end`：必须匹配 open turn；**不得在 step 仍开着时关**
- `step/start`：必须在 open turn 内；不得在已有 open step 时开；编号必须等于 `nextStep`
- `assistant/chunk` / `assistant/message` / `tool/call` / `tool/result`：
  必须指名**当前开着的** turn/step（`requireOpenStep`）
- `tool/call` → `pendingCalls.add(callId)`；
  `tool/result` → 检查 `pendingCalls.has(callId)`，否则失败
  「`tool/result` for X with no prior `tool/call` in this step」；
  `step/end` → `pendingCalls.clear()`
- `todo/write` / `request/header` / `request/context`：**必须被 turn 包住**
- `user/message`、`session/end-seed`：**刻意不约束**
  （注释：不平衡的 seed 合法地把它放进 open turn 里）
- `default:` 分支 —— **合并扩展的事件关系归其 owning plugin**，
  核心不因为「没有 open turn」就拒绝一个未知事件

一个我认为设计上很漂亮的地方（`invariant.ts:190-241`）：
它在 **`internal/dispatch`** 上做**预提交校验**并把 transition 暂存进一个
**弱键**（`WeakMap<SessionEvent, …>`）；在 `session/event` 上才**提交** transition。
注释解释了为什么：后来的 dispatch listener 可能否决，
而校验是纯的，所以放弃这个弱键 transition **既不推进也不保留** session 状态。
`session/event` 到达时若找不到匹配的预提交校验，直接
`fail('session/event reached publication without matching pre-commit validation')`。

还有一个**豁免**值得注意（`invariant.ts:127-135`）：
`tool/result` 若 `surfaceOp !== 'append'`（即它是个替换），
只要求「在某个 open turn 内」，**不要求配对 `tool/call`** ——
注释说明理由：那是「引用了被替换事件的内容改写，是持久的 turn 工作，
不是原调用的第二次执行」。

以及一个合成结果的豁免：`error.code === TOOL_NOT_STARTED` 且首个 content block
`isError === true` 的合成 `tool/result`，允许没有前置 `tool/call`（`invariant.ts:138-141`）。

**第三层：可选的 `dsh-agent-loop/invariant`**（Q4c 已详述）。

**注册契约**（`docs/subsystems/invariants.md:57-59`）——
这条机制我认为对 finaudit 直接可抄：

> 每个 workspace 包都拥有一个 `./invariant` companion；**发布与注册是穷尽的，
> 但断言刻意不是合成的**。一个 companion 只在其包**确实拥有**一个可观测事件或
> 可变数据关系时才装检查；否则它导出一个**空 installer**，其首行注释必须以
> `No runtime invariant:` 开头，并**逐包解释**为什么这里没有可检查的东西。

`pnpm run verify-package-invariants`（在必过的 `ci-static` 里）
机械地拒绝：生成的占位标记、无解释的空 installer、
**拿到 reporter 却不用的非空 installer**、注册名不对、导出/发布/依赖/打包接线不全。

**这正好是我们 rules/failure-modes.md 第 2 条「只有真实字段能诚实触发时才声明 flag」
的机制化版本**——他们不是靠纪律，是靠一条会拒 PR 的 gate。

---

## 4. Cordis 模型的要点

前两轮明说「凡涉及 effect 绑定 / fiber 处置 / waterfall 语义的转述都是照抄措辞，
不是理解后的判断」。本轮读了 `docs/cordis-primer.md`（44 行，全文）
和 `docs/cordis-api/fiber.md`（375 行，全文）。**`context.md` 与 `events.md` 未读**，
所以下面涉及 Context 继承链与事件注册细节的部分我会标注。

### 4.1 我确实读懂并能自己复述的

**Fiber = 一个已加载的插件实例。** 不是协程，跟 JS 的 async 无关。
它持有：生命周期状态、已校验的 config、以及注册的 effect
（`fiber.md:6`、`fiber.md:50-56`）。`ctx.fiber` 是当前 fiber，`ctx.effect()` 委托给它。

**Effect = 带清理的注册。** 关键语义（`fiber.md:24-35`，我读的是签名与 JSDoc）：

- `execute` **立即执行**
- 它产出的 disposer 被**收集**起来
- 在两个时机之一**按注册的逆序**运行：显式调用返回的 disposer，或 fiber 卸载 —— **谁先到算谁**
- disposer 调**两次是 no-op**
- fiber 已被 dispose 时调 `effect()` 抛 `CordisError('INACTIVE_EFFECT')`
- `execute` 返回形状不合法抛 `TypeError`

`Effect` 的三种可接受形状（`fiber.md:276-293`）：单个 disposer、disposer 的 promise、
或一个（可能是 async 的）iterable 产出多个 —— **generator effect 每 yield 一个就注册一个**。
这解释了我在 `session.md:647-654` 看到的 `prepare/enter/announce` 模式：
调用方 `yield` detach disposer，**然后**才 `announce`，
于是一个抛异常的 `session/created` listener 会把 attach 回滚掉而不是泄漏它。

**Fiber 处置的确切含义**：`fiber.dispose()` 卸载插件，**然后**在清理完成后才 settle
（`fiber.md:105-109`，返回 `Promise<void>`）。disposer 可以是 async 的，
**卸载会 await 它们**（`fiber.md:301`）。`fiber.uid` 在 dispose 后变 `null`
（`fiber.md:61-65`），`assertActive()` 就是检查这个。

**Waterfall = around-middleware**（`cordis-primer.md:28-34`）。这个我原来确实理解错了。
它不是「依次变换值」的管道，而是**洋葱**：

- listener 收到 `(...args, next)`
- **调 `next()`** = 把（可能已被包装的）结果委托给下一个 service
- **不调 `next()` 直接 return** = **短路**
- 值通过 `next()` 的返回值传播

primer 明确说：对**单决策事件，短路就是设计意图**——
一个 policy listener 拥有决定权时就不调 `next()`；
而只做标注或观察的 listener **必须**委托。
`prepend: true` 只在「必须跑在普通注册之前」时用。

这一下子讲通了 `agent-loop/invariant.ts:21` 为什么写
`ctx.on('llm/stream', …, { global: true, prepend: true })`，
并且注释说 `prepend` 是「防止一个短路的 replay listener 把检查静音掉」——
因为在 waterfall 里，任何一个先注册的 listener 只要不调 `next()`，后面的就永远跑不到。

**四种 dispatch 模式**（`cordis-primer.md:19-24`，我核对过 session 四个事件的实际标注）：

| Mode | Awaited? | 顺序 | 有返回值? |
|---|---|---|---|
| `emit` | 否 | 注册顺序 | 否 |
| `waterfall` | 否 | 注册顺序 | **是** |
| `parallel` | **是** | 全部并行 | 否 |
| `serial` | **是** | 注册顺序 | **是** |

dispatch mode 是**事件公开契约的一部分**，新事件用 `@mode` 标注，
**生成的 catalog 会拿声明去核对 dispatch 点**。

**Service = 通过 key 找实现，不 import 具体类。** `inject` 声明依赖，
插件**等到那些 service 存在才加载**——加载顺序由服务需求表达，不由手工 boot 序列表达
（`cordis-primer.md:9-13`）。

### 4.2 我仍然只是照抄措辞、未真正验证的

- `internal/dispatch`、`internal/status`、`internal/update` 这三个内部事件的确切契约。
  我在 `session/invariant.ts:233` 见到 `ctx.on('internal/dispatch', (_mode, eventName, args) => …)`
  的**用法**，也在 `fiber.md:94-98`、`fiber.md:250-262` 见到 `internal/status` 与
  `internal/update` 的**提及**，但它们的完整签名在 `docs/cordis-api/events.md`（**未读**）。
- `Context` 的继承与 `ctx.extend` / scoped context 机制 —— `docs/cordis-api/context.md` **未读**。
  我见到 `Scoped<Session>` 与 `@dshScopeScan unsupported` 标注，但**不理解 scope 过滤的实现**。
- `@deepseek-ai/cordis-plugin-include` 的 `!!js` 表达式插值机制
  （`cordis-primer.md:36-38`）—— 只读了 primer 那一段，未读实现。

---

## 5. 对 finaudit 证据链字段集（U-01）的具体输入

背景约束：U-01 要定证据链字段集，AC-05 要求**字段齐全率 100%**，
且复核者必须能从一个答案一路回溯到取数与口径定义。

### 5.1 直接可抄的三个字段（强建议）

**(a) `sourceEventSeqs: number[]` —— 显式的、只指向更早事件的来源引用**

这是他们整个可回溯性的承重结构，而且校验规则很值得照抄
（`packages/core/session/src/surface.ts:210-243`）：

| 规则 | 为什么值得抄 |
|---|---|
| 必须**严格早于**当前 seq | 杜绝环，回溯必然终止 |
| **不得重复** | 让「引用了几次」不成为一个需要解释的量 |
| **空数组 ≠ 字段缺席** | 空 = 「我知道来源是空的」；缺席 = 「我不记录来源」。两种无知要分开 |
| 空数组**只对一种事件合法** | 默认不允许「我说不清」，只对一个有明确语义的场合开口子 |
| replace 时**必须覆盖每个被遮蔽的节点** | 摘要类替换不能悄悄吞掉输入 |

对 finaudit 的映射：一条「口径判断」结论事件的 `sourceEventSeqs`
应当指向【取数事件】+【口径定义事件】+【准则条文事件】的 seq。
**上面这五条校验规则可以逐条平移**，在 append 点 fail-closed。

**(b) `seq` 连续性契约：`seq === log.length`**

`Session.seq` 的 getter 就是 `return this.log.length`（`index.ts:565-567`）。
文档反复强调 seq **必须保持连续，chunk 也不能被过滤出规范 log**（`session.md:603`）。
好处对我们直接成立：**`events[seq]` 可以直接下标寻址**——
`tracing.ts:70` 的 `const target = events[seq]` 就是这么写的，
连查找都不需要，且「seq 有洞」本身就是一个可检测的损坏信号。

**(c) 「dispatch 前记录请求」**

`request/header` 在 step 内、**dispatch 之前** append（`session.md:156`），
目的是让**每个请求都是 log 的纯函数**。
对 finaudit：**每次取数/每次计算之前**先落一条「我打算用什么口径、查哪张表、什么参数」的事件，
而不是只在事后记录结果。这样即使执行崩溃，也留下了「打算做什么」的证据。
他们的 `session/title-llm-request` 和 `web/deepseek-search-llm-request` 都遵循同一模式。

### 5.2 必须避开的两个坑（他们踩了，我们别踩）

**(a) 不要把「结论」和「产生结论的决策」放在两个无法互相引用的类别里**

这是 Q3 挖出的结构性缺口：`tool/call` 是 log-only，
**在类型上就无法携带 `sourceEventSeqs`**，所以它不能引用产生它的 `assistant/message`。
`assistant/message → tool/call` 这一跳只能靠 `(turn, step)` 同属推断。

`traceEvent` 因此**不能**回答「这次取数是哪次模型推理决定的」——
它只能回答「这个结果对应哪次调用」（`tool/result → tool/call`）。

**对 finaudit 的直接后果：** 如果我们照抄「只有 surface 事件能带来源引用」这个约束，
证据链会在**同一个位置**断掉。**建议：finaudit 的证据链字段不要跟「模型可见性」绑定。**
「这条记录进不进模型上下文」和「这条记录能不能引用它的来源」应当是两个**正交**的维度。
他们把两者耦合在 `SurfaceEventType` 上，是为了别的目的（surface 折叠），
我们没有那个约束，不该继承这个代价。

**(b) 不要让「负载里的业务 id」冒充证据链**

`command/done.sourceEventSeq`（单数，负载字段）与信封上的
`sourceEventSeqs`（复数）同名近似而语义无关，**`traceEvent` 不读前者**。
仓库里另有至少 6 套业务配对 id（`callId` / `commandId` / `handlerId` /
`compactionId` / `subCallId` / `ApprovalRequestId`），**通用回溯一个都不跟**。

**教训：证据链必须走一条唯一的、被工具认识的信封字段。**
业务 id 用来做 UI 分组可以，用来做复核回溯不行——
因为「谁负责跟这些 id」永远没有单一答案。
AC-05 的「字段齐全率 100%」应当只针对那条唯一的信封路径来度量。

### 5.3 一跳 vs 传递闭包 —— 需要我们做一个决策

`traceEvent` 的 `sourceEventSeqs` / `derivedEventSeqs` **只有一跳**
（`tracing.ts:87-91` 是单层扫描），只有 `replacementChain` 是传递的（while 循环）。

复核者要「从一个答案一路回溯到取数与口径定义」，
在他们的模型里需要**反复调用 `traceEvent` 自己爬**。

**这是一个真实的设计选择点，我建议我们显式做决定而不是默认继承：**
是提供一跳原语让复核者自己爬（他们的选择，实现简单、语义清晰、
但「一路回溯」这个用户故事没被 API 直接支持），
还是直接提供闭包（`traceChain`，一次拿到完整证据树，
但要处理深度上限、环检测——虽然「严格早于」规则已经杜绝了环）。
**给 AC-05 的建议：如果验收标准的措辞是「一路回溯」，那就该提供闭包 API，
否则「字段齐全率 100%」是满足了，但用户故事没满足。**

### 5.4 另外两个可抄的机制

**(a) `ignorable?: true` 的 fail-closed 未知类型策略**

（`known-event-types.ts:8-18`、`session.md:220-229`）
读到不认识的事件类型时：**缺省拒绝重建整个 session**，
只有事件显式带 `ignorable: true` 才允许跳过。
理由是「一个不认识的必需事件可能改变整个 log 后半段的解释方式」。
默认必需意味着「忘了标记」导致过度拒绝（**不便**），
而不是静默恢复一个被掏空的 session（**错误**）。

**对 finaudit：** 证据链遇到不认识的字段/记录类型时，
应当**拒绝出具结论**，而不是「降级成功」——
这跟 AGENTS.md 里 D-003「给不出证据链视为失败，不视为降级成功」是同一条原则，
他们给出了一个可实现的字段级机制。

**(b) 生成 + 校验新鲜度的文档管线**

`docs/persistence-catalog.md` 和 `packages/core/session/src/known-event-types.ts`
**都由 `scripts/gen-persistence-catalog.ts` 从源码生成**，
由 `pnpm run verify-persistence-catalog` 在**必过的** `ci-static` 里校验新鲜度
（`run-gates.ts:588`）。文档头两行就写着 do not edit by hand。

**对 finaudit：** 我们的「证据链字段集」文档如果是手写的，
它和实现漂移是**必然**而非偶然。这套「生成 + gate 校验新鲜度」是可直接平移的。
他们的 doc-sync 里有约 25 条这样的 verify gate。

---

## 6. 我没读，因此不能置评的清单

**明确没读的文件：**

1. `docs/cordis-api/context.md`（364 行）、`events.md`（207）、`registry.md`（152）、
   `service.md`（102）、`inherited.md`（39）——
   **所以我不能说 Context 继承链、scope 过滤实现、`internal/*` 事件的完整签名。**
2. `docs/subsystems/credentials.md`（133）、`sandbox.md`（218）—— 完全未读。
3. `docs/subsystems/persistence.md` —— 未读。**所以关于「log 怎么落盘、
   JSONL vs SQLite 后端、崩溃修复的确切行为」我一概不能置评**，
   只能转述 `session.md:601-605` 的耐久性契约那一段。
4. `docs/subsystems/session-projection.md`、`session-reference.md`、`session-title.md`、
   `compaction.md`、`core.md`、`llm-streaming.md` —— 未读。
   **所以 `StreamChunk`、`TokenUsage`、`ContentBlock`、`CallId`、`SessionTitleEventData`、
   `SessionTitleSnapshot` 的确切字段集我不知道。**
5. `.oxlintrc.staged.json` —— 未读（命令链被前一条报错截断）。
6. `apps/cli/config/` 下的出厂配置树本身 —— **未找到也未读**。
   Q4c「出厂不挂 invariants」的结论来自 Agent Note 自述 + 我对 `cordis*.yml` 的 grep，
   **不是我亲眼读到出厂配置并确认**。
7. 那条「config-dump 测试拒绝 invariant 条目」的测试源码 —— 未读，只有 Agent Note 的自述。

**只读了片段的：**

8. `.oxlintrc.json` 只读了 1-60 + 结构 grep。**所以我不能说 lint 规则的完整清单**，
   只能说：`plugins: []`、`categories.correctness: "off"`、
   `options.typeAware: true`、有 4 段 `overrides`、`vendor/**` 与 `native/**` 被忽略。
9. `scripts/run-gates.ts` 只读了 4 段（约 250/890 行）。
   **gate 之间的 `needs` 依赖图、失败聚合与并发调度逻辑我没读。**
10. `packages/core/session/src/surface.ts` 只读了 15-27、170-269。
    `foldSurface` / `SurfaceManager` 的增量推进实现未读。
11. `packages/core/session/src/index.ts` 只读了 115 行（约 1400 行的文件）。
    **`SessionStore` 的实现、`fork` 的实现、发布 hook 的实现我都没读**，
    只读了 `session.md` 里生成的签名与 JSDoc。
12. `docs/subsystems/session-telemetry.md` 只读 1-70，`docs/api-gateway.md` 只读 1-60。

**证据强度需要打折的两处：**

13. 事件表 2.2 里编号 26、29、30、34、35、36、37、38、39、40-44 共 14 条，
    catalog 只给了**类型别名名字**没展开字段。这 14 条我知道类型名，**不知道确切字段集**。
14. 「44 个事件里 3 个 surface」这个数是**本 build 的仓库内声明**。
    某个具体部署实际挂载哪些插件、因而实际会写出哪些事件类型，
    **属于部署配置，天然不在代码仓库里**——我不能对此下判断。

**按要求避开的（另一个 subagent 在读）：**
`docs/postmortem/`、`docs/subsystems/tools.md`、`docs/subsystems/subagent.md`。
所以工具管线、subagent 生命周期、以及他们自己复盘出来的教训，本报告一概未涉及。
