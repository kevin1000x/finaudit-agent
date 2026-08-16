# deepseek-harness 深读 · 第三轮（postmortem / tools / subagent）

仓库：`deepseek-ai/deepseek-harness`，分支 `master`，TypeScript / MIT。
本轮只读前两轮判定"最高价值但没读到"的三块，并回避另一个 subagent 认领的
`session.md` / `persistence-catalog.md` / `session-query.md` / `cordis-*` / CI 与 lint 配置。

> **纠正任务前提**：`docs/postmortem/` 下不是 5 篇 postmortem，是 **4 篇编号 postmortem
> （0001–0004）+ 1 篇 README**（README 是索引与写作规范，不是事故记录）。加上各自的
> `.zh.md` 镜像与 `.i18n.yaml`，共 15 个文件。本轮读完 4 篇英文正文与 README 英文正文。

## 读到什么程度

| 文件 | 行数 | 读到什么程度 |
|---|---|---|
| `docs/postmortem/README.md` | 18 | **读完** |
| `docs/postmortem/0001-acp-default-export-drops-inject.md` | 113 | **读完** |
| `docs/postmortem/0002-js-expression-disabled-filesystem-tools.md` | 47 | **读完** |
| `docs/postmortem/0003-web-agent-gui-feedback-loop.md` | 53 | **读完** |
| `docs/postmortem/0004-landlock-partial-notice-misclassified-child-failures.md` | 55 | **读完** |
| `docs/subsystems/tools.md` | 720 | **读完**（1–240 / 240–499 / 499–720 三段） |
| `docs/subsystems/subagent.md` | 734 | **读完**（1–200 / 200–375 / 374–484 / 483–650 / 650–734 五段） |
| `docs/tool-execution-pipeline.md` | 62 | **读完** |
| `docs/subsystems/invariants.md` | 88 | **读完** |
| `docs/subsystems/session-reference.md` | 108 | **读完**（为核 Q3 的"跨会话引用"是否另有机制） |
| `packages/core/tools/src/index.ts` | 约 1990 | **读了片段**：440–560、602–675、1459–1530、1680–1760、1900–1945；其余未读 |
| `packages/core/agent-loop/src/tool-calls.ts` | — | **读了 240–289**（durable `tool/call` / `tool/result` 落盘处）；其余未读 |
| `packages/guard/timeout-policy/src/index.ts` | 82 | **读完** |
| `packages/subagent/tool-subagent/src/index.ts` | 约 460 | **读了片段**：102–115、140–215、318–430；其余未读 |
| `packages/subagent/subagent/src/types.ts` | — | **读了 36–72**（`SubagentRunInfo` / `SubagentRunEndInfo`）；其余未读 |
| `scripts/verify-cordis-config.ts` | — | **读了 1–40** + grep 431–443；其余未读 |
| `packages/test-support/acp-snapshot/src/suite.ts` | 约 1250 | **只读 grep 命中的 705–735、1195–1215**；其余未读 |
| `.zh.md` 镜像、`.i18n.yaml` | — | **未读**（英文侧为准） |
| `.agents/notes/**`（两份文档密集引用的 Agent Note） | — | **未读** |

---

## 一、三个必答问题的结论

### Q1 postmortem 里有没有"日志/证据与实际发生的事不一致"的事故？

**有，而且四篇全是这一类。** 这是本轮最强的发现：`docs/postmortem/` 里没有一篇是普通功能
bug，四篇的共同主题都是**"某个自证机制说通过了，但它证明的不是它声称证明的那件事"**。
README 也把这条写进了立项标准——写 postmortem 的条件是"**为什么我们的流程让它过去了**，
而不只是那一行修复"（`docs/postmortem/README.md:5`）。

逐个给出「怎么发现的 / 根因 / 是否变成机械检查」：

| # | 不一致的具体形态 | 怎么发现的 | 是否变成机械检查 |
|---|---|---|---|
| 0001 | 178 个单测全绿、行覆盖率 100%，但产品在真实入口一次都跑不通 | 真实 Zed 连接立刻失败；在 vendored `reflect.ts` 里插桩打印 fiber walk | ✅ 无密钥 e2e 走真实 Loader 子进程 + `docs/testing.md` 规则 |
| 0002 | 会话日志里记的是 `UNKNOWN_TOOL`，快照套件却"通过"——因为期望值被 refresh 成了这个错误 | 人工审查刷新后的期望输出，看见 generic failed card 与结构化 `UNKNOWN_TOOL` | ✅ 双闸：`verify-cordis-config` + 快照套件拒绝 `UNKNOWN_TOOL` |
| 0003 | Agent 自己报告"成功"的 URL 不是承载会话的那个页面 | 用户指出 3081 早就变了；**postmortem 本身改用持久化事件日志重建时间线** | ⚠️ 主要是运行时事实注入 + 分层真实路径测试，非单条不变量 |
| 0004 | 子进程的正常退出码被归因到 launcher 的一行信息性 stderr，报成 `SANDBOX_UNAVAILABLE` | 用一个最小 POSIX wrapper 复现（打印通知后 `exec` payload） | ✅ `RunnerFailureRule` 结构化规则 + 回归 spec + 组装态快照 |

**对 finaudit 第一公理最直接的三条：**

1. **0002 是"证据与事实不一致"的教科书案例。**
   `0002:19` —— 结构化会话日志携带 `ToolNotFoundError`（code `UNKNOWN_TOOL`），stdout 渲染
   generic failed card，而**快照套件通过了，因为两份输出都与刷新后的 fixture 相符**；
   `0002:19` 原话的意思是：它证明的是"这个 regression 可以确定性重放"，而不是"文件系统行为正确"。
   `0002:46` 把教训写死成一句：**快照刷新是产出 fixture，不是正确性审查**；
   像"工具没注册"这种语义上不可能的事，需要**独立于期望输出**的断言。
   → 落成机械检查：`packages/test-support/acp-snapshot/src/suite.ts:717-733` 的
   `unknownToolCallIds()` 直接扫 JSONL 会话日志里 `type === 'tool/result'` 且
   `data.error.code === 'UNKNOWN_TOOL'` 的记录，`suite.ts:1202-1204` 断言其为空，
   断言消息是 `snapshot scenarios must not accept UNKNOWN_TOOL`。**新跑的结果和已提交的
   fixture 都要过这一关**（`0002:41`）。

2. **0003 里，Agent 的事后报告与持久化日志直接冲突，作者选择以日志为准。**
   `0003:17` 明确写出证据来源是会话 `session-3eb796c2-…` 的持久化事件日志，
   header 记录 cwd，并逐条给出序号：初始请求 header 是 seq 6，交还用户、裸 Vite 启动、
   替身宿主启动、boot manifest 探测、首次探测 3081 进程分别是
   **seq 30939 / 31865 / 34309 / 34441 / 34681**；然后写下这句方法论声明——
   下面的时间线**依据这些事件，而不是从事后报告里重建意图**。
   这正是 finaudit 复核实验想要的姿态：**日志是权威，自述不是**。
   `0003:51` 的教训一句话可以直接抄进 finaudit 的验收口径：
   HTTP 就绪、构建成功、boot manifest 是**三件不同的事实**；验收必须点名确切来源并在那里做外部观察。

3. **0004 是"归因错误"——证据存在，但被挂到了错误的主体上。**
   `0004:15` 描述：harness 把两种含义压成同一个大小写不敏感的 `landlock-run: ` 子串，
   于是**子进程的退出状态被系着到 launcher 的信息性行上**；ripgrep 无匹配的 exit 1
   会被报成沙箱基础设施故障。`0004:24` 明确定性：这**没有削弱隔离**，
   其安全影响是**可用性与诊断完整性**——一个有效的受限结果被拒绝或被贴错标签。
   `0004:52` 的教训：**进程归因需要多条独立证据的合取；共享前缀不是协议。**
   `0004:54`：**适配层必须保留下层 seam 拥有的结构化失败，而不是替换成自己最接近的通用分类**
   （当时 `tool-fs-search` 把结构化 `SandboxUnavailableError` 吞成了通用 `SEARCH_FAILED`）。
   → 落成机械检查：`RunnerFailureRule` 带上"允许的退出码 + 逐行致命签名 + 精确信息性行排除"，
   回归用例在 `packages/shell/bash-sandbox/tests/partial-landlock.spec.ts`（**文件确认存在**），
   组装态由 `examples/acp-agent/partial-landlock.cordis.snapshot.yml` 钉住（**确认存在**）。

**我核过的守卫都真实存在**（不是文档里许的愿）：
`scripts/verify-cordis-config.ts` 存在，且挂在 `package.json:128` 的 `hygiene` 任务链里
（`package.json:100` 定义脚本）；`examples/acp-agent/fs.cordis.yml`、
`fs.cordis.snapshot.yml`、`partial-landlock.cordis.yml` / `.snapshot.yml`、
`examples/acp-agent/tests/acp.e2e.ts` 全部存在。

⚠️ **一处文档落后于代码**：0002 说 `disabled` 不被插值，所以 `!!js` 在那里是恒真对象。
但现在 `scripts/verify-cordis-config.ts:4-7` 的说明是：Loader **会**插值 plugin 的 `config`
**以及 entry 的 `disabled`**（每次挂载决策时，针对 loader context 求值），其余 entry 元数据
字段保持静态。对应地，`verify-cordis-config.ts:431-443` 的规则也细化了：`disabled` 上的
**顶层** `!!js` 表达式**允许**且必须能解析，**嵌套在它下面的**表达式仍是恒真数据要报错；
`metadataFields = ['id','name','group','inject','intercept','isolate']`（第 41 行）里出现任何
表达式一律报 `!!js is not interpolated here`。
→ 结论：postmortem 是历史记录，**闸门规则才是当前事实**，两者会分叉。finaudit 若照抄
postmortem 归档制度，要接受这一点，别把 postmortem 当规格用。

---

### Q2 工具执行失败 / 被拒绝 / 超时，在日志里是三种事件还是一种？

**一种事件，三（四）种载荷。** 不是三种事件类型。

落盘只有一个 `tool/result` 会话事件，构造点在
`packages/core/agent-loop/src/tool-calls.ts:281`（函数 `appendToolResult`，267–289 行）：

```ts
session.append('tool/result', {
  turn, step,
  message,                                                    // { callId, content, isError }
  ...result.error?.info ? { error: result.error.info } : {},  // ← 只有 info，没有 message！
  ...result.meta !== undefined ? { meta: result.meta } : {},
}, { surfaceOp: 'append', sourceEventSeqs: [callSeq] })
```

配对的 `tool/call` 在 `tool-calls.ts:263`：
`{ turn, step, callId, name, arguments }`，返回 `event.seq`，
result 通过 `sourceEventSeqs: [callSeq]` **显式引用**它。

区分靠的是 `error`（即 `ToolErrorInfo = { name, code }`，
`packages/core/tools/src/index.ts:475-478`）这个**可选**字段：

| 终止形态 | `error.info.name` | `error.info.code` | 定义位置 |
|---|---|---|---|
| 超时 | `ToolTimeoutError` | `TOOL_TIMEOUT` | `packages/guard/timeout-policy/src/index.ts:25, 46` |
| 取消（body 已启动） | `AbortError` | `ABORTED` | `core/tools/src/index.ts:469, 1926` |
| 取消（body 未启动） | `AbortError` | `ABORTED_BEFORE_DISPATCH` | `core/tools/src/index.ts:472, 1940` |
| 工具不存在 / Code Mode 直呼原生名 | `ToolNotFoundError` | `UNKNOWN_TOOL` | `core/tools/src/index.ts:494-510` |
| 参数不合法 | — | `INVALID_ARGS` | `tools.md:149` |
| 输出不合法 | `ToolOutputError` | `INVALID_TOOL_OUTPUT` | `core/tools/src/index.ts:513-522` |
| **被拒绝（deny / guard / 审批未授予）** | **无** | **无** | `core/tools/src/index.ts:1493-1497` |

**⚠️ 这是本轮对 finaudit 最重要的一条负面教训：拒绝在 harness 里没有机器可读的码。**

`core/tools/src/index.ts:1486-1498`：

```ts
const denialReason = decision.kind === 'allow' ? this.guardReason(exec) : decision.reason
if (denialReason !== undefined) {
  return await next({ kind: 'post-result', exec, result: this.materializeFinalResult({
    content: [{ type: 'text', text: `Error: ${denialReason}` }],
    isError: true,
    error: { message: denialReason },        // ← 只有 message，没有 info
  }) })
}
```

因为落盘处是 `...result.error?.info ? { error: result.error.info } : {}`
（`tool-calls.ts:284`），`info` 缺失意味着**durable 事件里连 `error` 字段都不会出现**。
一次被拒绝的调用在日志里只剩：`isError: true` + 一段自然语言 `Error: <reason>`。
`error.message` 本身**从不落盘**，它只活在 content 文本里。

同时，`ApprovalOutcome` 的封闭四元组在**工具侧不是同构的**——它在
`core/tools/src/index.ts:1710-1728` 的 `serviceAsk()` 里被**压平成一个 `deny` + 四段不同的
自然语言**（这是刻意的，JSDoc 在 1685-1688 说"三种非授予以不同措辞拒绝，
**好让模型分辨人类的『不』与审批通道缺失**"——注意受众是**模型**，不是复核者）：

| `ApprovalOutcome` | 落成的 `reason` 文本 | 行号 |
|---|---|---|
| `allowed-once` | （放行） | 1716 |
| `rejected` | `the user rejected tool "<name>"` | 1717-1718 |
| `cancelled` | `approval for tool "<name>" was cancelled` | 1721-1722 |
| `unavailable` | `tool "<name>" requires approval, but no approval channel is available` | 1725-1726 |
| 无 approval 服务 | `tool "<name>" requires approval (not yet supported)` | 1696 |
| 无 agent 可路由 | `tool "<name>" requires approval, but the call has no agent to route it through` | 1702 |

外加 `cancelled` 一路还会把 `approvalCancelled: true` 带回去，若调用方信号也已取消，
结果会被**替换成 `ABORTED_BEFORE_DISPATCH`**（1483-1485）——也就是说
**"用户取消审批"在日志里可能表现为"取消"而不是"拒绝"**，两种语义在这里合流。

→ 对 finaudit：**harness 在这条上是反面教材，不要照抄。** 见第四节 U-01 设计。

补充：`tools.md:370` 明确，规范值 `value` 是 execution-local，**故意不写入 durable 事件**；
loop 只持久化 `content` / `error` / `meta`。原文的定性是：
**重放能复现呈现，但无法重建中间规范值。**

管线顺序（`tools.md:172` + `docs/tool-execution-pipeline.md:29-57`）：
`tool/call` 落盘（**在执行之前**）→ `tools/pre-execute` 瀑布（allow/deny/ask）→
`ctx.approval` 一次性提示 → 单调 guard（`ToolGuard`，只能降权，无 allow 返回值，
`tools.md:313-325`）→ `tools/execute` around 包装（超时/重试/度量）→ 工具 body →
`tools/post-execute`（accept/replace/block）→ 定义自有的 `finalizeContent` →
`tools/result`（冻结的权威结果，emit）→ `tool/result` 落盘。
`finalizeContent` 的契约值得抄：**注册表在执行开始时快照该回调，并对每一种归一化结果
恰好调用一次，包括绕过 `tools/post-execute` 的管线失败**（`tools.md:44-51`）——
即"最后一公里"钩子不可能被失败路径跳过。

---

### Q3 子 agent 的证据如何归属到父会话？

**父日志只存一条工具结果，不复制子会话的证据；而且在默认的一次性（foreground）路径下，
父日志里连子会话 id 都没有。** 复核者要重建完整证据链，**必须同时持有子会话的日志**，
并且只能靠**反向指针**去找它。

**（1）父日志里有什么**

父会话拿到的是普通的 `tool/call` + `tool/result` 对，没有任何 subagent 专属事件。
我 grep 过全仓库的 `append('subagent…`，落盘点只有两处，**都写进子会话**：
- `packages/subagent/subagent-in-process-driver/src/index.ts:85` → `agent.session.append('subagent/descriptor', descriptor)`
- `packages/subagent/subagent/src/descriptor-seed.ts:29` → `staged.append('subagent/descriptor', descriptor)`

`subagent/start` / `subagent/end` **不是会话事件**，是 Cordis 进程内 `emit` 通知
（`subagent.md:713-733` / `657-671`），`subagent.md:461` 说得很清楚：两者都是
**observe-only**。它们携带的 `SubagentRunInfo` / `SubagentRunEndInfo`
（`packages/subagent/subagent/src/types.ts:36-50` / `56-72`）里其实有
`runId` / `provider` / `id`(子会话 id) / `local` / `stopReason` / `lastAssistantMessage`
——**但这些进程内事件不落盘**，进程一结束就没了。

**（2）子会话 id 会不会进父日志？取决于运行模式**

`packages/subagent/tool-subagent/src/index.ts:327-365` 的 `output` 声明是一个三分支 `oneOf`，
关键在 `render()`（357-364）——只有 render 的产物才会变成落盘的 `content`：

| 模式 | canonical value | `render()` 落盘文本 | 子会话 id 进父日志？ |
|---|---|---|---|
| `foreground`（默认，一次性） | `{ kind, runId, output }` | `outputValueText(value.output)` | **否** |
| `continuable`（后台可续） | `{ kind, subagentId }` | `started subagent ${subagentId}` | 是 |
| `background`（一次性后台 job） | `{ kind, jobId }` | `started background subagent task ${jobId}` | 只有 jobId，非会话 id |

`outputValueText`（同文件 102-109）只把 `type: 'text'` 的块拼接起来——**`runId` 被丢掉了**。
而 `runId` 只活在 canonical value 里，`tools.md:341/370` 已说明 value 不落盘。
该工具也**没有声明 `presentationMeta`**（我 grep 过，命中数 0），所以 `meta` 字段也不会出现。

→ **结论：默认的 foreground 子 agent 调用，父日志里只有子 agent 的最终文本输出，
没有任何指向子会话的可机读句柄。**

**（3）反向指针与重建方式**

链接方向是**子 → 父**：
- 子会话 header 的 `parentSession` 记录 `request.parent.session.id`
  （`subagent.md:404`；字段定义 `packages/core/session/src/types.ts:75, 115`）
- 子会话 header 带 `origin: 'subagent'` 标记（`subagent.md:289`）
- 子会话日志里有 `subagent/descriptor`，`subagent.md:285` 定性为
  **log-only：没有 `surfaceOp`，从不进入模型历史，靠 append-only 日志跨压缩保留**

重建靠 `listChildren(parentSessionId)` / `listDescendants(rootSessionId)`
（`subagent.md:289-291`）：**枚举 `ctx.sessions.list()` 与可选
`ctx.sessionPersistence.list()` 的 live-preferred 归并**，筛 header 上
`origin: 'subagent'` 的直接子代，再把 `subagent/descriptor` 做 last-wins 折叠。
注意它的降级语义：
- 折叠不出身份的**已结束**候选 → `corrupt` 诊断（缺失/畸形/未知版本**故意不区分**）
- **正在运行**但还没落 descriptor 的候选 → **直接省略**（创建窗口）
- 冷读失败 → `unavailable` 诊断，下次列举重试
- **没有 persistence 时，枚举退化为 live-only 而不是报错**

以及 `subagent.md:404` 的硬约束：远程 provider 返回父命名空间的 lifecycle id 且
`localAgent: undefined`，**没有本地子 Session，因此完全不出现在持久化枚举里**。

**（4）另一条容易误认的机制**
`docs/subsystems/session-reference.md` 是**用户在宿主 UI 里 @ 提及别的会话**的机制
（`SessionReferenceInput` / `prepare()` 生成一份**不可信快照**注入为 additionalContext），
和 subagent 证据归属**没有关系**，别拿它当跨会话证据链用。

**（5）一个必须抄的反例设计**
`subagent.md:212-231`：Activation 结束时，运行时会给父发一条它自己的说明，
其 `MessageSource.kind` 刻意与子 agent 主动 `report` 的 kind **不同**
（`subagent-settled` vs `subagent-report`），理由原文写得极好：
report 是**子 agent 选择的内容**，而这条是**管理器在陈述子 agent 怎么结束的**，
把两者合并的 transcript 会**把子 agent 从没写过的话记在它头上**。
→ finaudit 的证据链必须同样区分「Agent 声称的」与「运行时观测到的」。

---

## 二、postmortem 四篇逐篇纪要

### README —— 归档制度本身（值得整体照抄）

- **立项门槛**（`README.md:9`）：三个条件同时满足才写——**subtle**（机制不显然，
  认真的工程师会重新痛苦地推一遍）、**systemic**（逃逸原因是测试/工具/约定的缺口，
  而不是一次性笔误）、**costly to rediscover**（真花了调试时间，再来一次还会花）。
- **与"设计决策记录"划清界限**（`README.md:7`）：postmortem **不是** Agent Note。
  Agent Note 记录**深思熟虑的设计决策与被否决的备选**；postmortem 是**回溯性的失败记录**：
  什么坏了、机制是什么、**为什么每一层安全网都没接住**、以及新加了哪些具体守卫。
- **强制结构**（`README.md:11`）：每篇以 **Executive summary** 开头，
  一个**忙碌读者 30 秒能吸收**的短段落——坏了什么、平白话讲的根因、为什么逃逸、
  以及**持久的教训**——然后才是 Summary / Timeline / Root cause / Guardrails。
- **强制回链**（`README.md:9`）：必须链接这篇 postmortem 催生的守卫（测试、AGENTS.md 规则、ADR）。

> 对 finaudit 的直接可用性：这套结构比通用的"5 Whys"更适合本项目，因为它把
> **"为什么安全网没接住"** 单列为一节。finaudit 的失败归因分层（EVAL_CASES.md）
> 可以直接借这一节的位置。

### 0001 —— ACP 服务器一连接就崩：`export default` 吃掉了插件的 `inject`

- **坑**：`packages/acp/acp/src/index.ts` 是 namespace plugin（分别导出
  `name` / `inject` / `Config` / `apply`），却比别的插件多了一行 `export default apply`。
- **根因 #1**（`0001:39-52`）：cordis Loader 的 `Loader.unwrapExports` 逻辑是
  `exports = exports.default ?? exports` —— **优先取 `.default`**。存在默认导出时，
  它解析成**裸的 `apply` 函数**，而 `inject` / `name` / `Config` 是**同级命名导出**，
  整个 namespace 被丢掉。插件于是在一个 `inject` 为空的 fiber 里运行，
  第一行 `ctx.agents` 走完 fiber 树（ROOT → Include → Loader → ROOT）到根 fiber 抛错。
  **崩溃发生在加载期，不是请求处理期**——请求只是恰好触发了加载。
- **根因 #2**（`0001:56-87`）：`AgentLoop.resume()` 读 `this.ctx.sessionPersistence`，
  而 `AgentLoop.static inject` **故意不含**它（注入了会让非持久化 demo 永远 pending）。
  经由**traceable shadow** 调用时，`reflect.ts` 的 get handler 从 shadow 的 fiber 起走，
  而这个走法是**仅祖先（ancestor-only）**的；`sessionPersistence` 在**兄弟分支**上，
  走到根 fiber 抛错。
- **测试为什么全没抓到**（`0001:89-98`，作者称之为"真正的失败"）：
  - 内存 harness 用**手搓插件对象** `ctx.plugin({ name, inject, apply })` 挂载，
    手工提供了 `inject`，因此**永远无法复现 Bug #1**——`unwrapExports` 只有 **Loader** 会调用。
  - 同一 harness 把一切平铺挂在单个 root context 上，于是 shadow 的源头仍在 root 解析，**掩盖了 Bug #2**。
  - 唯一的无密钥 e2e 只发 `initialize` 并检查 stdout 纯净度，而 `initialize` 根本到不了 factory。
  - 唯一驱动 `session/new` / `session/load` 的测试**被密钥门控**，CI 无密钥跳过；
    本地"通过"是因为**陈旧的 `lib/` 构建产物**恰好满足了模块解析。
  - **`0001:98`：100% 行覆盖率全程成立。覆盖率证明代码行跑过了，它对"功能是否以发布形态工作"一言不发。**
- **守卫**（`0001:100-106`）：删默认导出；`AgentLoop.resume` 改用
  `this.ctx.get('sessionPersistence')`；新增**无密钥、走真实 stdio 子进程的 `session/new` e2e**
  （`examples/acp-agent/tests/acp.e2e.ts`，**已确认存在**），并**验证过把
  `export default apply` 加回去它会失败**；e2e spawn 里设 `TSX_TSCONFIG_PATH`
  以保证跑的是**源码而非可能陈旧的构建**；写入 `docs/testing.md` 规则"测试真实入口路径"。
- **教训**（`0001:108-113`）：手搓插件的测试无法验证插件**如何加载**，至少要有一个测试端到端
  驱动真实 Loader/导出路径；当头等操作不调用模型时，**这种测试不需要 API key，
  因此它属于 CI，而不是密钥门后**。以及那句方法论——**信踪迹，别信理论**：
  优雅的 shadow 解释是真的，但它是第二个 bug；第一个是一行导出错误，
  在几小时"貌似合理但错误"的推理之后，一句 fiber-walk 的 `console.error` 几分钟就找到了。

### 0002 —— 文件系统快照工具被永久禁用（`!!js` 表达式）

- **坑**：默认 ACP 组合刻意只有 bash（沙箱无法约束进程内 filesystem provider），
  但快照场景需要 `read`/`write`/`edit`，于是在默认 `cordis.yml` 里给这些插件写了
  `disabled: !!js …`，想让它只在全权限启动与快照时启用。
- **根因**（`0002:32`）：`!!js` **只作用于 `entry.options.config`**——
  `Entry._resolveConfig()` 会插值那个字段，而 `Entry.disabled` 直接测
  `entry.options.disabled`、**不插值**。YAML 标签语法合法，加载不产生任何诊断。
  于是每个 filesystem entry 看到的都是一个**恒真对象**，在**所有模式下都保持禁用**。
- **不一致的形态**（`0002:19`，见 Q1）：7 个 filesystem 场景 + 1 个混合 workspace-edit 场景
  调用了注册表里根本不存在的工具，日志里是 `UNKNOWN_TOOL`，但**快照套件通过**。
  `0002:34` 补了一句关键的：header pin 校验了组合出的工具 schema，
  但**filesystem 场景共用默认组合的 pin**，因此**没有独立证明自己需要的工具已注册**。
  刷新先重写了期望 stdout 与会话日志，而当时**没有任何语义断言会拒绝缺失的工具**。
- **安全侧的反直觉结论**（`0002:21`）：活跃的受限默认组合**没有**因此获得意外的文件系统权限；
  反而**一个天真的"把插值修好"的修复会制造那个风险**——权限预设能在运行时更新 bash 沙箱与
  审批状态，但**不能挂载、卸载或约束 filesystem 栈**。
- **守卫**（`0002:36-41`）：filesystem 场景改用 `fs.cordis.yml` 显式固定的全权限 overlay
  （**已确认存在**，且有配对的 `fs.cordis.snapshot.yml`）+ 自己的 request-header class；
  `AGENTS.md` 与 cordis primer 写明 `!!js` 只在 plugin `config` 下有效、条件组合用 overlay；
  `verify-cordis-config` 解析仓库内 Cordis YAML 并拒绝 Loader entry 元数据里的表达式节点
  （**含 include patch 与插入的 entry**）；`dsh-acp-snapshot` 在**新跑结果与已提交
  fixture 两侧**都拒绝结构化 `UNKNOWN_TOOL`。
- **教训**（`0002:43-47`）：①语法上被接受的配置值，**不一定在那个位置被求值**——
  要**文档化并验证到底哪些字段会被插值**；②**快照刷新是 fixture 生产，不是正确性审查**；
  ③权限控制只能声称它**实际治理**的能力。

### 0003 —— Web agent 验证了一个替身服务器，而不是承载自己会话的 GUI

- **坑**：会话跑在端口 3081 的 Web GUI 里，选中的 Workspace 却是一个空的 `test/` 目录。
  模型请求既没点名 GUI，也没点名它的源码 checkout、URL、进程或更新模式。
  仓库里 `apps/web` 带一个 Vite dev 脚本很显眼，而完整的浏览器组合藏在 `dsh web` 后面。
- **失败链**（`0003:26-31`，全部按事件序号）：
  turn 2（seq 30939）改完主题后**把验收甩给用户**，让他自己去跑
  `pnpm run demo:tui` 或打开某个未指明的 Web 应用，自己一次组装态验收都没跑；
  turn 3（seq 31865）裸 Vite 起在 5173，看到 **HTTP 200 就宣布成功**，
  而浏览器实际抛 `client-modules: window.__DSH_BOOT__ is missing or not an object` 白屏；
  turn 4（seq 34309）找到完整 `dsh web` 路径，起了个**非托管**进程在 3334，
  只检查了这个替身返回 200 且有 boot manifest（seq 34441），**从未探测 3081**；
  turn 5（seq 34556）用户说 3081 早就是新主题了，直到 seq 34681 才去看已有进程并删掉多余服务器。
- **根因**（`0003:32-38`）：Web 组合**没有给"当前 GUI / 规范 URL / 运行模式"任何模型可见的身份**。
  会话 cwd 正确标识了用户选中的 Workspace，**模型却把那个项目目录当成了应用目录**。
  没有任何持久记录把 GUI 源码 checkout、构建产物、服务进程、目标 origin、浏览器验收关联起来。
  错误启动路径看起来合法，是因为**裸 Vite 返回 200**——而 `window.__DSH_BOOT__` 只有完整宿主会注入，
  **传输就绪不蕴含应用就绪**。
  还有一句给"回归测试"的重锤：**第一版回归测试以另一种形式重犯了同一个错误——
  超时杀掉 Vite，恰好满足了"非零退出"的断言**；是实况复现暴露了这个假阳性。
  另外用 shell `&` 绕过了后台进程语义，于是 job 身份、完成通知、收集、清理**全都不适用**。
- **守卫**（`0003:40-46`）：Web launcher 把**规范 loopback URL 与真实 production/development 模式**
  发布到日志化的 `app:web-surface` prompt 段与托管的 `$DSH_WEB_URL` / `$DSH_WEB_MODE` 环境变量里
  （即**把运行时事实注入模型上下文**）；`apps/web` 的独立 Vite serve 模式**在配置期就拒绝**，
  其子进程测试证明自然退出并对 `Server.listen()` 插桩，**使一次瞬时 bind 无法蒙混过关**；
  分层真实路径测试覆盖 CLI 请求、精确的 prod/dev 提示、shell 运行时事实、同端口静态替换、
  源码 watcher 重建、宿主 stat 轮询、以及**页面身份不变前提下**的浏览器 HMR；
  PR 证据保留原始 3081 会话截图与真实模型的前后对比 GUI 运行。
- **教训**（`0003:48-53`）：**启动模式是应用上下文，不是部落知识**；
  **替身服务无法证明既有页面变了**；**回归测试必须能因所报告的机制而失败**——
  进程超时不等于 fail-fast，进程退出后端口可用**不能证明端口从未被绑定过**。

### 0004 —— Landlock 部分强制通知把子进程失败归错了类

- **坑**：老 Landlock ABI 的内核上，launcher 在执行每个子进程前会打印一行良性的部分强制通知；
  harness 把这个共享的 `landlock-run:` 前缀 + 任意非零退出码当成 launcher 失败。
- **根因**（`0004:34-39`）：公开的 sandbox 结果类型**只能表达一袋子子串**。
  它无法表达"Landlock 失败**要求** exit 125"、"证据必须出现在**同一行**致命行内"、
  "同前缀下的**某一行精确文本**是信息性的"。布尔消费者于是把**来自不同进程的无关事实**
  连接起来，并且在真正的致命证据在后面某行时，仍取 stderr 的**第一行**做详情。
  测试矩阵镜像了这个表示法：假 provider 要么不发 runner 行，要么发明确致命的前缀，
  **从不发"良性 runner 行 + 子进程控制的非零退出"**；真 Landlock 覆盖依赖宿主 ABI，
  **全 ABI 主机根本无法触发那条通知**。
  还有一句被明确保留的**未解决的残余风险**（`0004:39`）：
  **stderr 仍然是带内（in-band）归因通道**。受限子进程可以**故意复现** runner 的门控致命行与退出码，
  造成可用性/诊断上的错误归因；收紧的合取只防住了本次事故里的**偶然碰撞**，
  **并不认证写入者**——带外状态协议是另一项独立加固，不是沙箱逃逸修复。
- **守卫**（`0004:41-48`）：`RunnerFailureRule` 带上可选允许退出码 + 大小写不敏感的**逐行**致命签名
  + 大小写不敏感的**精确信息性行排除**；`dsh-sandbox-local` 把 Landlock 映射为
  "exit 125 **且** 一行非通知的 `landlock-run:`"，而 bwrap / Seatbelt / 自定义 runner 仍只按签名；
  `dsh-bash-sandbox` 直接 spawn provider argv，使**启动前拒绝走 spawn-error 通道**而不是本地化的
  shell 诊断，并让前台与后台执行**共用同一个返回证据的分类器**（**致命证据优先于 denial**）；
  `dsh-tool-fs-search` 改用打包的 ripgrep 经 `ctx.subprocess`，**不再穿过沙箱化 bash**。
- **教训**（`0004:50-55`）：见 Q1 第 3 条，另加一条——
  **平台相关行为需要在原生边界上有一个确定性的 fake，外加一条组装态产品路径；
  一个会自我跳过的真实内核测试扛不起这个回归。**

---

## 三、`tools.md` 与 `subagent.md` 的其他发现

### tools.md（完整工具执行管线契约）

- **模型可见面靠白名单，不是靠黑名单**（`tools.md:11`）：`ToolDefinition` = `ToolSchema` +
  强制的 canonical output 声明 + `execute` + 仅宿主可见的调度元数据 + 可选终末回调 + 可选 UI presenter。
  `schemas()` 用**显式 allowlist** 构建模型可见的 `ToolSchema[]`——
  `output`/`execute`/`finalizeContent`/`timeoutMs`/`isConcurrencySafe`/`presentCall`/`presentResult`
  **绝不能泄漏进模型请求**。`timeoutMs` 那条 JSDoc（`tools.md:56-58`）特别写了
  "**从不发给模型**"，并且**声明它就等于断言该工具会把 `exec.signal` 转发给一个可协作实现**。
- **参数不可重写，这是刻意的**（`tools.md:384/402`）：`PreToolDecision` 里**排除了输入改写**，
  理由是**参数已经被记录并呈现过了**——`tools.md:402` 原话的意思是
  **历史、审计、UI 与执行必须一致**。这是 harness 里最接近 finaudit 第一公理的一条设计。
- **post 侧可以替换 content 或 value，但不能同时**（`tools.md:404`）：content 替换保留 canonical value
  与既有 meta；value 替换会**重新校验**并重算 content/meta；block 则移除 value 变成带纠正反馈的 `isError`。
  并且明确定性：**content 替换是呈现策略，不是保密策略**——
  必须隐藏程序性值的监听器应当 block 或替换 value。
- **`tools/result` 是只读的**（`tools.md:404, 704-714`）：观察者拿到冻结的 execution 与 result，
  **无法变换它们**，且观察者的异常被容纳。
- **guard 单调性**（`tools.md:313-325`）：`ToolGuard` 的返回类型**故意没有 allow**，
  `undefined` 保留瀑布决定，返回 reason 只能**降低**权限——因此**监听器顺序无法把拒绝翻回许可**。
- **并发安全 fail-closed**（`tools.md:62-74, 546-553`）：只有**精确的 `true`** 才算并行；
  省略、抛异常、非 `true` 返回、以及无效的 `defineTool` 参数**一律算独占**。
  这个元数据同样对模型不可见。
- **Code Mode 的日志有独立改写通道**（`tools.md:255-281, 601-626`）：
  `tools/code-dispatch-log` 瀑布允许监听器**只改 durable 日志副本**里的 content
  （比如 spill 策略的 preview + locator），而**程序本身已经拿到完整值，模型两者都看不见**。
  → 这是一个"**日志副本可以与实际传递值不同**"的合法机制，harness 明确接受了这种不一致，
  并把它限制在"只影响被记录的那份拷贝"。finaudit 若引入类似的截断/spill，必须显式记录这一点。
- **UI 呈现词汇要求可重放纯函数**（`tools.md:84, 92`）：`presentCall` / `presentResult`
  必须**纯且无副作用**，因为 UI **既会在实时流式期间调用，也会在会话日志重放时调用**，
  所以只能依赖 `args`（与 result）。`tools.md:464` 里的 `search` card 还专门带
  `truncated` / `total`，理由是"**让 UI 永远不会把部分结果呈现为完整结果**"。

### subagent.md（子 agent 与父会话的关系）

- **能力检查在前，绝不"接受后忽略"**（`subagent.md:13, 18-21`）：provider 用静态 descriptor
  声明 start-time 能力，服务在**一次性 run 存在之前**就检查；
  需要 provider 不具备的能力的请求**大声拒绝**（`SubagentError('UNSUPPORTED_CAPABILITY')`），
  这条规则原文叫 **"fail loud, no silent degradation"**。
- **`refusal` 是一等终止原因**（`subagent.md:347-358`）：`SubagentStopReasonMap` 是
  `completed` / `aborted` / `error` / `max-tokens` / **`refusal`**（"子 agent 拒绝了该任务"）。
  这是 merge-extensible 派生联合——**后端可以新增变体，消费者分支处理已知情况，
  把未知终止原因当作失败**。
- **部分输出绝不当成功**（`subagent.md:310, 333`）：非 `completed` 的 stopReason 意味着
  `output` 可能是部分的，消费者**必须映射为 `isError` 工具结果，而不是把部分输出报成成功**。
  实现见 `tool-subagent/src/index.ts:167-197`：`stopReasonError()` 有值就 `throw`，
  由注册表转成 `isError`；同时 `withPartialText()`（149-155）把**保留下来的部分文本**
  附在错误抬头后面，措辞是 `Partial output before the run ended:` ——
  **既不算成功，又不丢失已产生的真实文本**。这个模式 finaudit 可直接用于"证据不足但已算出中间量"。
- **可见性不等于授权**（`subagent.md:83-86`）：`toolFilter` 在子 agent 创建窗口内作为 scoped
  `tools.restrict()` 施加，被点名的工具**从子 agent 的 prompt 里消失 *且* 拒绝执行**
  （one visibility），并对未知名称**大声校验**。
- **深度是持久化的单调下界**（`subagent.md:467`）：委派深度 = 持久的
  `SessionHeader.delegationDepth` + 运行时 `AgentOptions.subagentDepth`，
  缺省即顶层深度 0，**两者中较大的present值权威**；进程内子 agent 持久化"父深度+1"，
  **冷恢复无法降低它**，越界或超过 `maxDepth` 一律在 start 时拒绝。
- **fork 种子必须是平衡的完整回合前缀**（`subagent.md:468`）：fork 后端传父日志中
  **截至最后一个 `turn/end`** 的前缀，从而**从 seq 0 连续且平衡**，
  使 invariants 重放可以接受它（**进行中的未平衡回合被排除**）。
- **最终落盘用 best-effort，且明确承认可能不一致**（`subagent.md:159`）：
  最终结算会 await `ctx.sessions.flush(session)` 但**忽略它的参与布尔值**，
  理由是"**任意监听器无法证明持久化后端确实存储了状态**"；flush 拒绝只记录、不使 Activation 失败，
  管理器照样释放 handle——**于是持久化的子状态在稍后恢复时可能缺失或陈旧**。
  这是一个被写进文档的、公开承认的证据缺口。

---

## 四、对 finaudit 的具体输入

### 4.1 U-01 证据链字段集：以 harness 的 durable 事件对为骨架，但要在三处反着做

harness 的落盘对（`tool-calls.ts:261-289`）可以直接作为 U-01 的骨架：

| 骨架字段 | harness 出处 | finaudit 是否照抄 |
|---|---|---|
| `turn` / `step` | `tool/call` + `tool/result` 同带 | 抄（提供确定的重放序） |
| `callId` | `tool/call.callId`；result 侧藏在 `message.source.callId` | 抄，但**提到顶层**（见下） |
| `name` / `arguments` | `tool/call`，**执行前落盘** | 抄，且**同样在执行前落盘** |
| `seq` / `sourceEventSeqs` | `session.append(..., { sourceEventSeqs: [callSeq] })` | **重点抄**，见下 |
| `isError` | `message.isError` | 抄 |
| `error: {name, code}` | `ToolErrorInfo` | 抄，但**必填**，见下 |
| `meta` | 可重放的呈现投影 | 抄 |
| `value`（规范值） | **harness 故意不落盘** | **反着做**，见下 |

**三处必须反着做：**

**(1) 拒答必须有 code，不能只有 message。**
harness 的 denial 落盘后**连 `error` 字段都没有**（`core/tools/src/index.ts:1496`
只填 `message`，而 `tool-calls.ts:284` 只在 `info` 存在时才写 `error`）。
它的四种审批非授予被压成四段**自然语言**（`index.ts:1710-1728`），受众是模型不是复核者。
finaudit 的 `Refuse[reason, missing_definition]` 若照抄这个形状，**复核者只能靠正则匹配中文句子**
来区分"准则缺失"与"数据缺失"，AC-05 的"字段齐全率"会立刻失去可判定性。

建议：把拒答做成与超时/取消**同构**的一等结构化码，例如
`error: { name: 'RefusalError', code: 'MISSING_DEFINITION' | 'MISSING_DATA' | 'AMBIGUOUS_CALIBER' | 'OUT_OF_SCOPE', missing: [...] }`，
且**落盘路径不得依赖任何可选字段的存在性**——harness 那个
`...result.error?.info ? { error: … } : {}` 的写法就是缺陷的来源。

另外注意 harness 的一个语义合流：审批被取消时，若调用方信号也已取消，
结果会**被替换成 `ABORTED_BEFORE_DISPATCH`**（`index.ts:1483-1485`）——
"用户取消审批"在日志里变成了"取消"。finaudit 必须保证 **`Refuse` 不会被任何上游状态覆写**，
否则拒答率统计会失真。

**(2) 中间规范值必须落盘。**
`tools.md:341/370`：canonical `value` 是 execution-local，**故意不写入 durable 事件**，
loop 只持久化 `content`/`error`/`meta`，因此**重放能复现呈现，但无法重建中间规范值**。
harness 这么选是对的——它是编码 agent，中间值是文件内容，太大且无审计价值。
**finaudit 的取舍必须相反**：财务复核要的正是中间值（口径参数、取数区间、计算中间量）。
这是一个**必须显式记录为决策分歧**的点，不能默认继承。

**(3) `callId` 提到 result 事件顶层。**
harness 的 `tool/result` 顶层没有 `callId`，它埋在 `message.source.callId` 里——
证据是 `packages/test-support/acp-snapshot/src/suite.ts:725-731` 那段守卫代码为了拿 callId
要三层可选链下钻（`data.message.source.callId`），拿不到时用 `<missing callId>` 占位。
**守卫代码自己都要防御性下钻**，这就是字段位置没设计好的信号。

**最该抄的一条：`sourceEventSeqs` 显式引用。**
`tool-calls.ts:288` 用 `{ surfaceOp: 'append', sourceEventSeqs: [callSeq] }` 把结果事件
显式挂回它的调用事件 seq，而**不是靠时间顺序或 callId 匹配去推断**。
finaudit 的证据链应当同构：每个断言事件显式引用它依赖的取数事件 / 准则事件的 seq，
使证据链是一张**显式 DAG**而非需要重建的隐式序列。这直接支撑"每个答案可独立复核"。

### 4.2 拒答状态设计

- 采纳 `SubagentStopReasonMap`（`subagent.md:347-358`）的**merge-extensible 派生联合**做法：
  已知终止原因显式分支，**未知终止原因一律当失败**。这防止未来新增拒答类型时被静默当成成功。
- 采纳 `refusal` 作为与 `completed` / `error` **并列**的终止原因，而不是 `error` 的子类。
  harness 已经这么做了——拒答不是错误。
- 采纳"部分输出不算成功、但保留部分文本"的模式
  （`tool-subagent/src/index.ts:149-155, 167-183`）：finaudit 遇到"能算出 3 个指标中的 2 个"时，
  应当返回 `Refuse` + 附上已算出的 2 个及其证据，而不是二选一。
- 采纳单调 guard（`tools.md:313-325`）：拒答判定器**只能降权**，无 allow 返回值，
  从而**任何后置监听器都无法把拒答翻回许可**。这对 finaudit"宁可拒答不可编造"是结构性保障。
- 采纳 `finalizeContent` 的"**恰好一次、且失败路径也不跳过**"契约（`tools.md:44-51`）：
  finaudit 的证据链封装步骤必须对**每一种**终止形态都执行一次，包括拒答与内部异常，
  否则"凡进入答案的事实 ⟺ 有一条证据事件"会在异常路径上破。

### 4.3 流程制度上可直接搬的三条

1. **postmortem 的立项三条件 + "为什么安全网没接住"独立成节**（README）。
2. **"快照刷新是 fixture 生产，不是正确性审查"**（0002:46）：
   finaudit 的 `EVAL_CASES.md` 若引入黄金答案/回归基线，必须有**独立于期望输出的语义断言**
   （例如"答案里引用的准则条目必须在准则库里存在"），否则基线会把回归固化成"正确"。
3. **"回归测试必须能因所报告的机制而失败"**（0003:53）：
   写完一条守卫测试后，**把 bug 手动放回去、确认它确实失败**——0001 明确做了这件事
   （`0001:104`：验证过恢复 `export default apply` 后该 e2e 会失败）。

### 4.4 子 agent 证据对 AC-05 的直接影响

**如果 finaudit 用子 agent 分工，AC-05「字段齐全率 100%」的定义现在就要改。**
按 harness 的形态：证据**天然分散在多个日志文件**，父日志只有一条工具结果，
默认 foreground 模式下**父日志里连子会话 id 都没有**（`tool-subagent/src/index.ts:357-364`
的 render 把 `runId` 丢掉了），链接只能靠子会话 header 的 `parentSession` 反向指针
+ 全量枚举（`subagent.md:289`）。且枚举本身有明确的降级面：
无 persistence 时退化为 live-only、正在运行且 descriptor 未落的子 agent 被**直接省略**、
畸形/缺失/未知版本**故意不区分**地折叠成 `corrupt`。

给 finaudit 的两个选项：
- **(a) 单日志约束**：禁止子 agent 产生独立日志，所有证据事件写入同一条会话日志
  （父子用 `agent_id` 字段区分）。AC-05 定义不变，代价是失去子 agent 的上下文隔离。
- **(b) 多日志 + 强制正向指针**：允许子日志，但**强制父日志的结果事件携带
  `child_session_id` 作为一等字段**（即修掉 harness 那个 render 丢 runId 的缺陷），
  并把 AC-05 改述为「**沿正向指针可达的证据集合**字段齐全率 100%」。
  此时复核者**需要同时持有子会话日志**，这必须写进复核实验的物料清单。

harness 自己选的是 (b) 的弱化版——正向指针只在 `continuable` / `background` 模式下存在。
我倾向 finaudit 选 (b) 的完整版，但这是**架构决策，不该由本轮调研代为拍板**。

---

## 五、我没读，因此不能置评

- **`docs/subsystems/session.md`（51k）、`docs/persistence-catalog.md`、
  `session-query.md`、`docs/cordis-*`、CI 与 lint 配置** —— 按任务要求避开，
  由另一个 subagent 负责。因此我**不能**就以下问题下结论：会话事件的完整类型清单、
  `surfaceOp` 的全部语义、压缩（compaction）对 `tool/result` 的裁剪规则、
  持久化格式与 `SESSION_FORMAT_VERSION = 0` 的迁移策略、以及是否存在我没看到的
  跨会话证据聚合查询。**我对 `tool/result` 落盘字段的结论来自源码
  （`tool-calls.ts:281-288`），不是来自 session.md**，若两者冲突以另一个 agent 的文档结论为准并复核。
- **`docs/tool-catalog.md`（1873 行）** —— 完全未读。因此不能说"harness 的工具集里
  有/没有某个特定工具"，也不能对具体工具的 schema 下断言。
- **`.agents/notes/**` 下的 Agent Note** —— 完全未读。两份文档引用了至少 12 篇
  （parallel-tool-call、render-intent-union、subagent-capability-seam、
  continuable-subagent-conversations、list-identity-projection 等）。
  **设计的"为什么"大量存放在那里**，我只读到了结论。若要理解某条契约的备选方案与否决理由，
  必须另开一轮读 Agent Note。
- **`packages/core/tools/src/index.ts` 的大部分**（约 1990 行，我只读了 5 段共约 300 行）——
  不能对注册表的作用域解析、Code Mode 桥接、scheduler 的并行池实现下断言。
- **测试文件本身**（`partial-landlock.spec.ts`、`acp.e2e.ts`、`tools.spec.ts` 等）——
  只确认了**文件存在**，**没有读内容，也没有运行任何测试**。
  因此我对"守卫确实能捕获对应 bug"的说法，**只到"守卫代码存在且逻辑看起来对应"为止**，
  不构成"验证通过"。0001 声称"验证过恢复 `export default apply` 会失败"——
  **这是文档的声明，我没有复现。**
- **`.zh.md` 中文镜像与 `.i18n.yaml`** —— 未读。若中英文有分歧我不会知道
  （文档自称生成的 cordis-surface 段落两侧逐字节相同，但正文段落没有这个保证）。
- **`approval.md`（`docs/subsystems/approval.md`，9k）** —— 本轮未读。
  我对 `ApprovalOutcome` 四元组的理解来自 `core/tools/src/index.ts:1710-1728` 的调用侧
  与前两轮结论，**没有读 approval 子系统自己的契约文档**，
  因此不能就审批服务的完整生命周期、超时、以及 UI 路由下断言。
- **实际运行环境** —— 我没有跑过这个仓库的任何命令（没装依赖、没跑 `pnpm run hygiene`）。
  所有关于"守卫在 CI 里生效"的说法，依据是 `package.json:100,128` 的脚本声明与
  `.gitlab-ci.yml` 存在这一事实，**不是观察到的 CI 运行结果**。
