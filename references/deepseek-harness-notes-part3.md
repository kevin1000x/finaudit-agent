# deepseek-harness `.agents/notes` 精读 —— 第三轮：`implemented/simplification` + `implemented/bug-fix`

**语料快照 commit：`47f9438`。** 本文所有 `路径:行号` 均绑定该 commit。
语料本地路径（临时 scratchpad，非本仓库）：
`…/scratchpad/deepseek-harness/.agents/notes/`
本文引用一律省略该前缀，从 `implemented/…` 写起。

**只读英文 `*.md`，不读 `*.zh.md`，不读 `*.i18n.yaml`。**

## 本轮范围与为什么是这两个目录

上一轮普查（`deepseek-harness-notes-survey.md` §5.1）自己给出的优先级：

- `implemented/simplification` 记录「**删掉了什么、为什么删得起**」，
  与已全文读完的 `rejected/simplification`（10 篇，survey §3 组 A）**互补**——
  一边是「提了但没删」，一边是「真的删了」，两边合起来才是完整的删除判据。
- `implemented/bug-fix` 藏着**真实踩过的坑**，尤其是静默失败那一类。

`implemented/feature`(169) 与 `archived/*`(142) **本轮明确不读**。

## 覆盖表

| 目录 | 英文 `.md` 总数 | 本轮读了几篇 | 全文 / 部分 | 此前已读 | 累计未读 |
|---|---:|---:|---|---:|---:|
| `implemented/simplification` | 46 | 46 | **全文** | 0 | 0 |
| `implemented/bug-fix` | 76 | 75 | **全文** | 1（survey C-2） | 0 |
| **本轮合计** | **122** | **121** | 全文 | 1 | **0** |

计数命令（在语料根 `.agents/notes/` 下执行）：

```
ls implemented/simplification/*.md | grep -v '\.zh\.md$' | wc -l   # -> 46
ls implemented/bug-fix/*.md        | grep -v '\.zh\.md$' | wc -l   # -> 76
cat $(ls implemented/simplification/*.md | grep -v '\.zh\.md$') | wc -l  # -> 1856
cat $(ls implemented/bug-fix/*.md        | grep -v '\.zh\.md$') | wc -l  # -> 3004
```

> 已读过、本轮不重读：`implemented/bug-fix/2026-08-09-filesystem-absence-observation.md`
> （survey §3 组 C 的 C-2）。

> **⚠️ 就地更正（2026-08-23 补写 §C 时发现）：上表的「本轮读了几篇」与正文实际写出的条目数对不上。**
> `implemented/bug-fix` 一栏写的是 75/76，但**正文只写到 `B-24`**，其后还有 **52 篇没有正文条目**。
> 这 52 篇是否被读过**无法核实**，状态记为 `UNVERIFIED`。逐条说明与计数命令见文末 **§L**。
> `implemented/simplification` 的 46/46 有逐篇条目，可核对，不受影响。

## 阅读台账（READ-LEDGER）

台账在正文写完之后才填，见文末 §L。

---

# §A `implemented/simplification`（46 篇，全文）

每条格式：`S-nn 篇名（行数）` → **删了什么** / **判据** / **备选** / **对本项目的关系**。
「原文未记录备选」是原文确实没有 `## Alternatives considered` 一节时的写法，
部分篇目末尾自带 `<!-- agent-note-format: alternatives-not-recorded -->` 标记，会注明。

引用写法：`S-01:13` 表示该条对应原文件的第 13 行。文件全路径见 §L 台账。

## S-01 `2026-06-19-drop-mutable-session-summary.md`（35 行）

**删了什么**：会话持久化层的可变摘要 `SessionSummary`（`updatedAt` / `title` / `firstPrompt`）、
`SessionMeta` 这个名字、抽象服务上的第七个方法 `SessionPersistence.update()`，
以及两个后端各自的实现（JSONL 的 `.summary.json` sidecar 全套机械、SQLite 的三列 + 每次 append 的 `updated_at` 自增）。

**判据（这是全目录里写得最硬的一条「删得起」判据）**——第 11-17 行逐项列出审计结果：

- `SessionPersistence.update()` **零生产调用者**（`.update(` 的每一处命中不是 `createHash().update()` 就是测试）（:13）
- `firstPrompt` 在生产代码里**从未被读**（:14）
- 会话标题来自持久的 `session/title` 事件，工具卡标题来自 tool presenter，**两者都不读可变元数据**（:15）
- 持久化列表的消费者用的是不可变 header 的身份/创建时间/血缘/cwd（:16）
- 决定性证据：**活的 `Session.header` 本来就是 `SessionHeader` 类型而不是 `SessionMeta`**——
  摘要从来没出现在活对象上，只活在持久化层里，写它读它的只有它自己的契约测试（:17）

**第二条判据是「可从别处重建」**（:23）：摘要要提供的东西**都能从 append-only 日志推导**
（`firstPrompt` = 第一条 `user/message`；recency = 最后一个事件的 `time` 或文件 mtime），
或者已经在不可变 header 里（`createdAt` / `cwd`）。
唯一**推不出来的**是「用户手工编辑过的标题」——而它**根本没有实现**，属于纯 YAGNI，
如果真有功能需要，它可以作为自己的日志事件或 header 字段回来。

**留下的原则**（:33，本项目最该抄的一句）：

> a passing test pins current behavior, not necessarily correct behavior;
> behavior can be an artifact of a past compromise

——**测试通过只是把「当前行为」钉住了，不等于把「正确行为」钉住了；行为本身可能是过去某次妥协的产物。**
这条被单独写进了 root `AGENTS.md` 作为约定，本次改动是它的样例。

**没有迁移**（:29）：未发布软件，磁盘上没有要保的库。SQLite **不迁移 v1**——
`openDatabase` 直接拒绝任何非当前 `user_version`（`onDisk !== 0 && onDisk !== SCHEMA_VERSION`），
**比当前旧或比当前新都拒**，宁可干净拒绝也不半读。这是 fail-closed 在「格式版本」上的形态。

**备选**：原文未记录备选（文末自带 `alternatives-not-recorded (pre-format Agent Note)` 标记，:35）。

**对本项目**：这是 D-007「图谱必须由问题驱动」最直接的外部对照——
他们把「为未来的 session picker 准备的缓存」判为死重，理由不是「用不上」而是**逐条搜过零消费者**。

## S-02 `2026-06-20-collapse-trace-only-session-events.md`（41 行）

**删了什么**：会话事件词表里两个「只做 trace」的一等事件——独立的 `usage` 事件与独立的 `error` 事件。

**判据**：不是「信息没用」，而是**同一事实已有承载者、独立记录是平行副本**（:9）：
`usage` 在 loop 追加独立事件之前，已经作为 model stream chunk 存在；
`error` 重复了 `turn/end { kind:'error', message, code }`——ACP 读 turn-end 的 reason，
消息与 UI 投影则跳过独立 `error` 事件。
这些事件让规范化 transcript 看起来比它实际更像遥测，代价是事件变体、不变量、测试、快照、持久化分支（:11）。

**关键手法：删的是记录，不是信息**（:11 明写 the simplification is to fold those facts into
nearby events consumers already must understand, **not to record less information**）。折叠去向（:17-20）：

- 成功步的 usage 折进对应 `assistant/message`（`{turn, step, content, usage?}`）——产出与计量同行
- **失败/中止但有 usage 无内容的步**，用空内容的 `assistant/message { content: [], usage }` 承载，
  「没有任何持久化的 usage chunk 失去表示」。这是**唯一有信息丢失风险的路径**（max-tokens 截断），
  他们专门为它写了回归测试，且 `deriveMessages()` 跳过空内容 assistant 事件以免污染 provider transcript——
  **一个测试同时断言两件事：usage 仍被表示 AND 派生历史未被污染**（:18）
- 独立 `error` 事件的 step 号折进 `turn/end.reason`（`{kind:'error', step, message, code?}`）（:19）

**备选**（:26）：**保留独立行当遥测**——被否，理由是若分析需求成真，形态应是投影 helper
或有自己保留策略的专用遥测存储，**而不是会话日志里的重复 trace 行**。

**验证段是可核对的**（:30）：`SessionEventMap` 不含独立 `usage`/`error`；
ACP 快照与持久化测试断言不存在 trace-only 行；录制 fixture 全部迁到新事件形状。

**后果诚实写了代价**（:34）：消费者不能再过滤日志拿独立 usage 行，必须从承载事件里读。

**对本项目**：这是**「证据不能减，但证据的载体可以合并」**的样板，与 `ARCHITECTURE §8.5`
（证据指针必须被下游强制消费）互为反面：他们删的正是**没有下游强制消费者**的那一类记录。

## S-03 `2026-06-20-public-agent-stop-api.md`（37 行）

**删了什么**：公共 `Agent` 句柄上的 `abort()`（只中止当前步），只留 `cancel(cause, options?)`。

**判据**：两个动词的**行为差异是真的**，但**没有任何在跑的代码需要那个更窄的动词**（:11）。
`cancel(cause, { keepInbox: true })` 已经覆盖了生产 Web 的停止策略，
ACP 用宽 `cancel()`，生命周期所有者用 `AgentHandle.dispose()`。

**这一篇最有价值的是「反向」的部分**（:19 + :25）：
原提案还要删 `whenIdle()`，**在拿代码验证前提之后被推翻了**——
`whenIdle()` 是承载性的静默观测原语，安全处理 waiter 结算与替换-turn 竞态；
把消费者推去手工观察 `running`→`idle` 转换「正是防御性模式警告过的脆弱路径」。
且原文诚实标注：生产 ACP bridge 自己拥有 agent、走 `dispose()`，
所以 `packages/acp/acp/src` 本身没有 `whenIdle()` 调用，活的消费者是 ACP 测试与 agent 测试（:19）。

→ **「零生产调用者」不等于「可删」**：这里零生产调用者但被判定为必须留，因为它是**公共契约里
让非所有者安全观测的唯一正确路径**，删了会把消费者推向脆弱替代。
把它与 S-01 并读，删除判据其实是两条的合取：**零消费者 ∧ 没有把消费者推向更差替代**。

**备选**（:25）：**连 `whenIdle()` 一起删**——原提案形状，被否，理由如上。

## S-04 `2026-06-20-remove-agent-boundary-mirror-events.md`（38 行）

**删了什么**：四个「持久边界的镜像事件」`agent/turn-start` / `agent/turn-end` /
`agent/step-start` / `agent/step-end`。

**判据**：**镜像让消费者在同一个持久事实上面对两个真相源**（:9）。
ACP 早已选了会话日志（唯一持久、可重放的记录），消费镜像反而要去对齐它与日志里已存边界的时序。
重复不是免费的：每次生命周期改动都要同时改会话事件、镜像事件、文档、不变量、测试、快照期望（:11）。

**这一篇有一个专门给本项目看的失败形状**（:11）：

> a turn can be durably closed before a live `agent/turn-end` listener runs,
> so a post-boundary listener failure has no valid in-log position left and must be reported out of band.

——**持久边界已经关闭之后才跑的监听器，一旦失败，日志里已经没有合法位置能放它了，只能带外汇报。**
这是「留痕体系自身的漏洞」的典型：不是没记，是**没地方记**。

**范围段（:21-29）值得单独学**：明写「删了什么」之外还明写 **RETAINED 及其理由**——
`agent/steering`（镜像的是控制记录不是边界，由自己的后续决策删除）、
`agent/stream-chunk`（活的 token 流，同上）、
`agent/created/disposed/status/error/queued`（生命周期/控制事件，不是 transcript 数据；
其中 `agent/queued` 在任何持久事件存在之前就触发——**被取消的排队工作可能永远不进日志**——所以刻意只活在内存）。

**备选**（:33-34）：
① **把 `agent/steering` 一起删**——原提案形状，作为 scope creep 被剔出去，后来由它自己的决策删除；
② **为 stdio UI 保留 turn 镜像**——这是更早那篇 `architecture/2026-06-30-event-domain-semantics.md` 的立场，
这里被推翻，理由是 `dsh-ui-stdio` 是**一次性的测试 REPL，不是承载性消费者**，
「ui-stdio 需要它」不构成保留镜像的理由（:19）。

→ **判据补充第三条：消费者的分量要算。** 一个可丢弃的调试界面不足以让一条重复真相源活下来。

## S-05 `2026-06-20-unify-agent-and-session-id.md`（39 行）

**删了什么**：agent id 与 session id 两套身份，以及「唯一职责是在两个本地 id 之间翻译」的 map 与字段（:19）。

**判据**：**给工厂两个独立输入会允许出现任何生产路径都用不到的配对**，
同时逼所有消费者在同一个生命周期的两个名字之间做选择或翻译（:9）。
且第二身份不代表独立的存活性、回滚或静默状态，它只是在同一个事务周围加 API 与翻译状态（:13）。

**保留的部分同样有判据**（:21）：config 里的 `agents[].id` 保留为**稳定的配置标签**，
不是活的路由身份；普通冷启动铸造组合 id `${label}-session-${randomUUID()}` 以免持久重启撞车。
→ **「显示用标识」与「路由/持久用标识」分离，但只有后者是身份。**

**备选**（:27）：**保留分离的路由身份与日志身份**——被否，理由是这个诉求可以由
「标签留作配置/显示元数据 + 每次运行的组合 `SessionId` 独占路由与持久化」满足，
保留两个 id 只会留下翻译 map 并允许不可能的配对，**却不增加任何生命周期能力**。

**后果段是诚实的负面清单**（:39）：这一删**堵死了**潜在的 multi-session-actor 与 session-handoff 设计，
并把「持久化的、客户端选定的会话身份」变成注册表身份。如果分离的路由身份真成为需求，
需要一个显式的生命周期设计，而不是不受约束的调用者自选配对。

## S-06 `2026-06-26-fsspec-style-fs-seam.md`（130 行，本目录最长）

严格说这是**拆分**而非删除，但它记录了一次**删除 + 反转既有决策**，判据非常密。

**删了什么**（:68）：`dsh-fs` 里的 `readPage`、`FsExpectation`、`FsView`、`FsStateSource`、
`FsReadRequest`、`FsTextLine`、行/窗口常量、`formatReadBody`、观测状态 `WeakMap`；
`applyEdit` 被更窄的 `editText` 取代；
**并且 `FS_PARTIAL_OBSERVATION` 这个错误码退出了 `FsErrorCode` taxonomy——
因为新鲜度授权没有 partial/full 之分，所以没有任何东西能抛出它**。

→ **删枚举值的判据 = 没有任何代码路径能到达它。** 这条比「零调用者」更强，值得抄。

**为什么删得起**（:16）：旧策略「部分视图不能授权 edit」制造了一个**真实的死路**——
模型读了大文件的 100-150 行就无法编辑第 120 行，除非先拿到一次 `full` 读，
而超过读取上限的文件根本拿不到。原文的判断是：**字面编辑需要的只是新鲜度，不是视图完整性。**
→ **删除的第四条判据：这个约束保护的东西，不是它声称保护的东西。**

**层次划分**（:24-29）四层：tool（模型可见 schema + 读窗口 + 渲染，执行者）/
policy（观测状态 + 读后写/编辑 + 新鲜度，**通过 `fs/*` 事件门贡献，不是服务**）/
provider 契约（`ctx.fs`：文本 IO + 原子变更原语）/ provider 实现。

**必须留在一起的东西**（:64 + :129）：
`editText` 的**版本守卫 + 字面匹配 + 原子重写必须待在 provider 的变更临界区里**，
且**陈旧检查必须发生在字面匹配之前**——否则一个基于旧读的编辑会报 `FS_EDIT_NOT_FOUND`
或 `FS_AMBIGUOUS_EDIT`（针对新内容匹配失败），而不是正确的 `FS_STALE_VERSION`。
→ **这是错误归因正确性的要求，不是性能要求。** 顺序错了不会崩，只会**把错误报在错误的地方**——静默错误的一种。

**策略层零 IO**（:82）：「你观测过这个文件吗」是 `WeakMap` 查表；
「你读到的版本还是当前的吗」由 `ctx.fs.editText/writeText` 在执行变更的同一把原子锁里判定，
策略层只提供 `vObserved` 作为基准。

**默认不耦合**（:90）：策略通过带 `undefined` 默认值的事件贡献，
所以插件缺席时每个 intent waterfall 落到 `undefined`（无条件裸 provider 写/编辑），`fs/observed` 无监听者。
→ **注意这是 fail-OPEN 的默认**，与本项目 D-018 的 fail-closed 方向相反；
他们把它当作「策略是可插拔层」的代价明写在 Consequences（:127）：
直接用 `ctx.fs.readText` 不发 `fs/observed`，于是默认策略下后续 `edit` 会以 `FS_NOT_OBSERVED` 拒绝，
「**这个失败是显式的、有文档的**」。

**并发边界写了能力上限**（:94-98）：进程内安全（每目标变更锁）；
跨进程创建**只是尽力而为**（本地 stat-then-rename 守卫无法给出可移植的 create-exclusive 保证）；
跨进程写是「尽力新鲜度 + 原子替换」，`mtime:size` **通常**能抓到编辑器保存，
但**同 tick 同大小的写会漏**；原子 temp+rename 防撕裂文件，**但不防每一次丢失更新**。
→ **能力上限被当成一等产物写下来了**，不是藏在代码里。

**备选**（:120-122）三条，全部记录：
① 字节级 fsspec（`cat`/`open` 返回裸字节）——否，seam 刻意停在「文本存储」这半级之上；
② 具体的 `ctx.fileContext` 方法服务——这是本篇原始形状，被 event-gate 那篇改成门插件；
③ 在 provider 上保留 `readPage` 与 full/partial 视图授权——被 Supersedes 段反转。

## S-07 `2026-07-04-drop-image-content-block.md`（29 行）

**删了什么**：`ImageBlock` 内容块类型、它在 `ContentBlockMap` 里的条目、adapter 与压缩里的图像分支。

**判据（本目录里对本项目最重要的一条）**（:9）：
`ImageBlock` **没有生产端生产者，而且每条路径上的每个消费者都把它丢掉了**——
DeepSeek adapter 的序列化器跳过它（有文档的 MVP 限制），pi-ai 转换器跳过它（不可表示），
压缩估算器按一个固定 token 常量计费并渲染成 `[image]`；ACP 则独立拒绝图像 prompt 内容。
所以当时构造一个 `ImageBlock`，它会**在通往 provider 的线路上无声消失**——

> the vocabulary advertised a capability no path honored,
> which is **the silent-data-loss shape** AGENTS.md's defensive patterns warn against

——**词表宣告了一个没有任何路径兑现的能力**。唯一的构造点是「钉住 skip/drop/estimate 分支」的测试。

→ 注意这里的形状：**测试是存在的、而且是通过的，它钉住的恰恰是「静默丢弃」这个错误行为。**
与 S-01:33 那句「passing test pins current behavior, not necessarily correct behavior」正好互证。

**为什么删而不是修**（:19）：保留一个「唯一实现是拒绝」的核心类型，等于对外宣传一个不可用的界面；
**类型缺席会让生产者立刻拿到编译期失败**，这比运行时静默丢弃好。

**明写的退路**（:21，本篇最该抄的一句）：如果这个槽位要在完整功能之前回来，做法是
**保留 `ImageBlock` 但把每一次静默跳过换成大声拒绝**，并把该策略写进词表——

> the silent drop was **the one state with no defender**

——**静默丢弃是唯一一个没有任何人能为它辩护的状态。**
（要么兑现能力，要么让它编译不过，要么大声拒绝；唯独「悄悄扔掉」不可接受。）

## S-08 `2026-07-04-tighten-hook-protocol-contract.md`（32 行）

一次「四件小事一起收紧」的记录，每一件都带独立判据。

1. **`HookDialect` 的 `'native'` 变体**（:11）：**零生产者**——bridge 只会打 `'claude'` 或 `'codex'`，
   唯一构造 `'native'` 的地方是库自己的单元测试。
   而且字段自己的 JSDoc 把 `dialect` 定义为「跑它的那个 bridge」，**native 不是 bridge**。
   → 判据不只是「没人用」，还包括**「它与字段自身的定义相矛盾」**。
2. **`HookOutput.suppressOutput`**（:12）：**被 codec 解析、然后在每条路径上被丢弃**——
   没有 bridge 分支、没有 merge fold、没有 warn、没有 deferred 清单行。
   原文特意做了对照：它的每一个「被解析但未兑现」的兄弟字段**都带着明写的延期说明**
   （`updatedInput` → 一条 warn 日志 + 一个 proposal；`systemMessage` → warn + README 延期行；
   `continue`/`stopReason` → 一个 `TODO(hook-continue-false)` 锚点 + `'stop'` 决策记录），
   **只有 `suppressOutput` 什么都没有**。而且结构上根本没有东西可抑制
   （hook 的 stdout 从不进入任何 transcript），所以
   **一个 hook 作者设 `suppressOutput: true` 得到的是「静默的什么都没发生，连 warn 都没有」**。
   → **判据：不是「没被使用」，而是「被消费流程接受了却什么都不做，且不告诉任何人」。**
3. **`defaultTimeoutMs` 双重默认**（:13）：schema `.default(600_000)` **和** `?? 600_000` 兜底，
   两个 bridge 各有两个家，同一个协议级常量共四处浮动字面量，
   「两个 bridge 可能在共享默认值上**静默地漂开**」。
   注意他们**没有**把这个旋钮删掉——按 no-hardcoded-tunables 规则它仍是 bridge 拥有的显式配置，
   **改的只是字面量的家**（`DEFAULT_HOOK_TIMEOUT_MS`）。
4. **`hook/result` 的语义住在两个 bridge 里，各一份，而不是住在拥有该事件的库里**（:14）：
   `summarize()`（stderr 截断规则）在两个 bridge 里**逐字节相同**，
   决策字符串规则 `output.decision ?? (output.continue === false ? 'stop' : 'pass')` 也是；
   而 `dsh-hook-protocol` 声明了 `hook/result`、把 `stderrSummary` 记为「已截断」却不拥有截断逻辑。
   → **「一个持久事件的语义有两份副本」= 该事件的含义可以静默分叉。**
   修法是把摘要与决策派生收归 `HookResultRecord` / `appendHookResult`。

**留下来的东西也有判据**（:24，与 S-03 同构，**本项目要抄的一条**）：

> `durationMs` remains because **durable audit timing is useful independently of a current reader**

——**持久的审计计时，其价值独立于「当前有没有读者」。**
→ 这条把「零消费者 ⇒ 可删」明确地**排除在审计字段之外**。

**备选**（:22-24）：「为什么不留着？」——不被支持的词表可以在真有消费者时回来；
bridge 专有的负载构造留在各自 bridge，共享的持久事件规范化归协议库。

## S-09 `2026-07-12-simplify-session-log-representation.md`（35 行）

**删了什么**：两个「机械成本高于消费者需求」的表示——
① `SurfaceManager` 的伪链表（数组 + seq map + 可变 `prev`/`next` 三份同序）；
② 请求头的自定义 system/tool 增量编解码器（`SystemDelta`、`ToolsDelta`、round-trip 兜底、
持久的 `request/header-delta` 变体）。

**判据①**（:11）：**生产代码从不读那两个链接**；
且替换操作本来就用 `indexOf`，**链接并没有把它的主导操作变成常数时间**——
即「这个优化并没有优化到它声称优化的地方」（与 S-06 的第四条判据同型）。

**判据②**（:13）：增量编码的**契约自己就说**它是「编码优化，不是可重建性要求」。
保留每个 loop 实例边界上的完整快照 + 该实例装配头变化时写一条规范全量 `request/header`，
就**保住了重放**，同时删掉整个编解码层。
原文一句话说清删除的粒度：
> **Codec-only vocabulary disappears with the codec, not because its individual arms were invalid.**
（只属于编解码器的词表随编解码器一起消失，不是因为它的某个分支不成立。）

**保留的部分，判据与 S-08 完全一致**（:15，**本项目要抄的第二处**）：
实现**保留**了追加与替换的 `sourceEventSeqs`、崩溃修复结果引用的 `tool/call` seq、
以及全部 `SessionStartSource` 变体，理由是

> those fields have an **audit/interception role** that **zero current readers does not overturn**

——**这些字段有审计/拦截角色，「当前零读者」推翻不了它。**

**fail-loud 边界**（:23）：`SESSION_FORMAT_VERSION` 仍钉在 `0`，
于是 seed、append、持久化加载校验**显式拒绝**旧的 `request/header-delta` 事件
和带已删除 `fallback` 原因的全量快照。**没有兼容折叠，没有迁移。**
JSONL 与 SQLite 测试**钉住这条 fail-loud 边界**。

**备选**（:27）：**为可能的规模保留链表节点与紧凑增量**——
链接对未来的 cursor API 可能有用，增量在大工具 schema 小改动时能减小日志。
被否，理由是**没有已发布的 cursor 用到链接**，而全量快照是「用磁盘换显著更简单的正确性」；
若头部体量真成问题，「可以围绕**真实 trace**设计压缩或有测量依据的规范化增量方案」。

**后果**（:35）：诚实写了代价——日志变大、超大 surface 上线性替换可能更慢；
但替换本来就是线性的（旧实现就在调 `indexOf`），**基准测试推迟到真实 trace 显示它是瓶颈时再做**。

## S-10 `2026-07-17-one-send-one-turn.md`（45 行）

**删了什么**：普通 `send()` 的**隐式批处理**——两次 `send()` 因为「读队列时两条都在等」而被合成一个 turn。

**判据（这是一条「静默行为改变」的判据，不是「死代码」判据）**（:9-13）：
分组依据的是**时序而不是调用者意图**；同一个同步栈、相邻微任务、事件监听器、模型回调
可能被分成不同的组，**尽管每个调用者用的是同一个 API**。
更关键的是**分组改变的是行为，不只是模型调用次数**：

> If message B shares message A's turn, B can enter A's model request
> **instead of first seeing A's closed result in the session log.**

——B 会进入 A 的模型请求，**而不是先在会话日志里看见 A 已关闭的结果**。
→ 对本项目：**「批处理」把「因果顺序」变成了「调度顺序」，而证据链依赖的是前者。**

**决策的精确措辞值得学**（:17）：每次成功的 `send()` 生成一个独立 FIFO 队列项；
若该项运行，它是该 turn 里唯一的普通消息。
但**一个项可能在开始前被丢弃，所以确切保证是「至多一个 turn」而不是「恰好一个 turn」**；
两次 send **绝不会被静默合并**。
→ **保证的措辞被削到能被实现真正满足的强度**，而不是好听的强度。

**排序屏障**（:21）：B 的 turn 只在 A 记录 `turn/end` **且 A 的持久化检查点结算之后**才开始；
检查点错误会被汇报，但**结算只释放这个排序屏障，不会把一次失败的写变成持久的**。
→ 这句是本项目 D-018 的近亲：**屏障通过 ≠ 写成功**，两者不能混为一谈。

**备选**（:31）：**保留自动批处理以减少模型调用**——被否。
承认它在生产者快过驱动时能提升吞吐，但它让 turn 边界依赖调度，
并让后一条消息在前一个 turn 关闭并到达检查点之前就跑起来。
「本决策保留可预测的边界并接受额外的调用。
**未来任何批处理特性都需要一个显式的、调用者可见的契约，并有测量支撑。**」

**验证段是五条可执行断言**（:35-39），包括「延迟的与被拒绝的首轮检查点让下一个 turn 继续等待，
**并证明它的请求看得见前一条 assistant 结果**」——这是一条**因果可见性**的测试，不是时序测试。

## S-11 `2026-07-20-remove-stdio-and-echo-agents.md`（49 行）

**删了什么**：两个冗余的产品级 agent（面向行的 stdio agent、无网络 mock 模型 Echo），
**以及它们的全部支撑面**：UI 插件、app 包、SDK 接口、REPL leaf、prompt 协议、Loader 测试、
可运行命令、mock adapter、工具、CI demo gate、graph 条目、教学引用、共享测试 fixture。

**判据（删除范围的判据）**（:11，本项目要抄）：

> Keeping any of those product paths would **preserve the redundant agent indirectly.**

——**留下其中任何一条产品路径，就等于间接留住了那个冗余 agent。**
→ 删除的边界不是「那个类」，而是**「所有能让它复活的入口」**。

**同时明写不删什么**（:13）：stdin/stdout 仍是 ACP、JSON-RPC、MCP、子进程的协议边界；
确定性模型 adapter 在测试内部仍然有效。
「这些机制**不构成**一个面向行的或只有 mock 的产品级 agent 的正当理由。」
→ **「机制」与「产品面」被明确分开：删产品面不等于删机制。**

**备选（五条，全部记录）**（:37-41）：
① 只为管道保留行 agent——否，Headless 已有有界任务契约、纯净 stdout、持久完成与进程退出码；
② 把 readline helper 保留/折叠/提升为包——否，它只有一个 app 消费者、没有可独立替换的契约；
**「未来若要独立的行 UI，需要先有真实的第二个消费者，才谈重新引入那个包」**；
③ 把 Echo 留作无 key 快速上手——否，第一次产品体验应该跑真模型；
④ 只把 Echo 留作 CI demo 命令——否，测试自有的 Headless fixture 覆盖同样的边界；
⑤ 删掉每一个 stdio 或 mock 机制——否（见上，机制是独立基础设施）。

**后果**（:45-49）：诚实列出失去的东西——仓库里**不再有无 key 的用户可见 demo**，
本地 demo 需要 `DEEPSEEK_API_KEY`；旧的 stdio 配置与 Echo 命令**直接失败而不是被翻译**；
单进程内的管道式多轮交互与非 TTY 的 readline 提问 provider「**是有意去掉的**」。

## S-12 `2026-07-20-unwrap-injected-content-envelopes.md`（41 行）

**删了什么**：注入内容在模型 transcript 里的 XML 信封——
`<steering source="…">…</steering>` 与 `<context source="…">…</context>`，
以及 `ContextEnvelope` 类型、贯穿 `InjectOptions` / `HookContext` / `context/message` 事件 / loop 的
`envelope` 字段、`renderTagged` / `renderContextEnvelope` helper。

**判据①（有实证）**（:13）：**没有模型是在这些标签上训练过的**。
`<steering>` 与 `<context>` 是任意标记，加 token 而无可靠效果，甚至会主动误导——

> recorded transcripts show a model treating a `<steering>` instruction as
> **third-party metadata and refusing it** while answering only the original prompt.

——**录下来的 transcript 里，模型把 `<steering>` 指令当成第三方元数据拒绝执行**，只回答原始 prompt。

**判据②（层次归属）**（:14）：会话 surface 的职责是把持久日志投影成模型 transcript，
**「决定内容怎么措辞不是它的工作」**。想要特定框架的调用者自己格式化——
唯一的重度生产者 `agent-instructions` 本来就这么做（自己拥有完整 `<system-reminder>` 框架，
并用 `envelope: 'raw'` 退出 `<context>` 包装）。

**信息没丢**（:22）：信封携带的 `source` 归属**仍在持久事件上**，只是不再渲染进 transcript。
（与 S-02 同一手法：删表示，不删事实。）

**最有价值的一句在 Consequences**（:34，**直接回答本轮问题 4**）：

> The `hook-{cc,codex}-stop-continue` ACP snapshots were re-recorded:
> **the old recordings captured the model refusing steering as third-party metadata, the fix's exact failure mode.**

——**旧快照录下来的、并且一直「通过」的，正是这个 bug 本身的失败模式。**
快照测试全绿，bug 全程在里面。这是「测试通过但 bug 仍在」的教科书案例。

**备选（三条）**（:26-28）：
① 只解开 steering、留着 `<context>` 信封——否，为一个没有模型会读的框架位留着整套机械；
② 只对插件来源的内容保留信封字段——否，按 `source.kind` 把一个投影劈成两个而没有可观测收益；
③ 把解包挪到 adapter 里——否，规范投影就是「模型可见 ⟺ 已记录」这个契约，
**各 adapter 各自分叉会让派生 transcript 变成 adapter 相关的**。

**延期方案写得很具体**（:39）：若以后还要带标签的框架，
统一走事件的 `meta`（生产者附加、模型不可见的元数据），由一个专门 renderer 消费，
**而不是在 `deriveEventMessage` 里重新硬编码标签**。

## S-13 `2026-07-22-plan-specific-collaboration-state.md`（71 行）

**删了什么**（:39-42「Deleted API」一节）：为「未来可能的协作模式」建的**通用具名模式注册表**——
任意定义 map、模式名正则、保留名规则、每定义的命令循环、`ModeDefinition`、
已解析定义 map、`ctx.modes.list()`、字符串值的 get/set、未知/退役模式处理、
**只存在于测试里的 `review` 模式**、以及「可以通过配置添加更多模式」这个说法本身。

**判据**（:9）：产品**只发布了 `plan` 一个模式**，通用注册表里的一切
「只为支持假想中的未来协作模式而存在」；而且 plan 专有的行为（引导、`/plan`、`exit_plan_mode`）
**还是住在同一个包里**，所以**这个通用 API 并没有把可复用机制与 plan 策略隔开**——
它付出了抽象的代价却没拿到抽象的好处。

**第二条判据是词义污染**（:11）：「mode」这个词跨了不相干的域——
sandbox mode 是 `ctx.sandboxPolicy` 拥有的**强制策略**，plan mode 是**协作姿态**。
把两者当成同一个具名模式抽象的实例会**遮蔽它们各自独立的所有权**。
并且：**「一个传输协议的通用词表，不构成 harness 需要一个通用模式域的证据」**。
→ 对本项目：**别因为上游/外部协议里有个通用概念，就在自己这里建一个同名的通用层。**

**备选（七条，全目录最多）**（:46-58），其中三条对本项目直接有用：
- **保留一个私有通用注册表、今天只暴露 plan**——否，
  「没有第二个生产消费者，那些用不上的名字/配置机械仍然要维护和测试。
  **未来的协作状态可以从两个具体案例里确立正确的共享 seam。**」
  → **抽象要等第二个具体案例**，这是「减法触发条件」的正面表述。
- **把 sandbox 或 approval 策略折进 plan 状态**——否，理由里有一句静默失败的判词（:48）：
  > A mode-owned sandbox cap also makes a user's explicit sandbox selection
  > **appear to succeed while silently doing nothing.**
  ——由模式拥有的 sandbox 上限，会让用户显式的 sandbox 选择**看起来成功了、实际什么也没做**。
- **按每个 plan 的工具名白名单过滤工具**——否，
  「可变性是每个工具自身的属性（包括未来的与 MCP 的工具），而不是每个 plan 部署都得维护的清单。
  **在有具体消费者之前，plan mode 是引导，不是安全边界。**」
  → **明确拒绝把「引导」冒充成「强制」**，这与本项目「证据链不是日志」是同一类正名。

**fail-closed 出现在评审路径上**（:35）：`exit_plan_mode` 的评审
在「user-questions provider 缺席或失败、评审失败、评审挂起时插件被销毁」时**fail closed**，
把手工 `/plan off` 留作人类逃生出口。

**后果诚实**（:71）：一个空闲的挂起选择会在进程于下个边界前退出时丢失；
且**一个无视引导的模型仍然可以改东西**，除非部署另行配置 sandbox / approval / 文件系统策略。

## S-14 `2026-07-23-acp-automation-only-protocol.md`（53 行）

**删了什么**：ACP bridge 里的整套「第二个交互式产品 UI」——
编辑器卡片、终端元数据、diff、plan、标题、推理、命令、模式、模型与权限选择器、
会话导航、人类征询；以及 session load/list/delete、命令、模式、配置选择器、模型切换、plan 评审。

**判据**（:9）：这些职责**重复了 TUI 与 Web 客户端**，同时把一个自动化传输
耦合到 UI 服务、持久化查询、呈现策略和编辑器特有约定上。
保留的是 ACP **唯一有用的角色**（:11）：另一个 agent 或自动控制器可以启动 harness 进程、
建隔离会话、发文本、收已提交答案、取消、回答权限请求。

**删除时对测试的处理值得抄**（:13 + :29-33）：
「快照套件让删除变复杂。**大多数 ACP 场景演练的是装配后的 agent 后端，而不是 ACP 呈现**，
所以把套件连同编辑器 bridge 一起删掉，会丢弃大量无 key 的行为覆盖。」
→ 处理办法：**只有「驱动方式是被删掉的 UI 方法」的场景离开套件**，其余保留；
语义检查点恢复改走 headless `stream-json` 示例。
→ **删除功能时，测试的去留按「它实际测的是什么」判定，不按「它挂在谁下面」判定。**

**fail-closed 保留在机器权限通道上**（:21）：一次性 `session/request_permission` 保留，
但明确是「**机器策略通道，不是人类审批 UI**」：应答者只接受 bridge 活会话映射里的精确 agent 对象，
外来或无 call 的请求转交，**失败的 RPC 映射到 fail-closed 的 unavailable 结果**，
且 bridge **绝不把该响应变成持久授权**。

**备选（五条）**（:37-45），其中第二条是**对已有良好设计的诚实处理**：
「保留早前那个在有纪律的服务边界后面的编辑器 bridge」——**被否，尽管**那个 bridge
正确使用了接口服务、工具自有的渲染意图、审批与 user-questions 应答者、harness 自有的执行、
纯净 stdout 组合；它的终端卡片是能力门控的、仅显示用的 Zed `_meta` 投影（带文本兜底），
所以 shell 执行从未离开 harness……**「那些边界是自洽的，但它们没法让编辑器卡片、会话导航、
配置选择器和人类征询属于一个自动化协议。」**
→ **「实现得对」不能救「归属错」。**

## S-15 `2026-07-23-collapse-persistence-flush-state.md`（49 行）

**删了什么**：一个活会话写生命周期的**三个平行容器**（buffer / initialization / retirement）
折成一个 per-session 的 flush 控制器；活控制器 map **同时就是退役注册表**，
「不需要单独的退役集合来重新发现未完成的工作」（:23）。

**判据**：那些结构「**镜像了同一个事实**：这个确切的 `Session` 是否还有初始化或事件
必须先结算，它的状态才能释放」（:11）。
→ **与 S-04 同型：多个结构表示同一个事实 = 可以静默分叉的真相源。**

**篇头有一条「本篇被后续决策部分取代」的自我标注**（:7）：
批处理节奏被 `architecture/2026-08-08-bounded-session-persistence-write-batching.md` 取代，
但单控制器所有权、失败保留、按 id 串行、退役、静默销毁四项决策仍然有效。
→ **笔记体系自己维护「哪一段还算数」**，这比整篇作废或整篇保留都精确。

**备选（四条）**（:27-33），两条与本项目的 fail-closed 讨论直接相关：
- **只在 checkpoint 时写回**——否，那让持久性依赖一个另行挂载的检查点策略，
  并**把两次检查点之间的崩溃丢失窗口最大化**；
- **永久闩住第一个后台错误**——否。承认它让之后每次 flush 都是确定性的，
  但**会阻止现有的 teardown 重试从一次瞬时存储故障中恢复**。
  最终选择是「保留批次但不闩住错误，**可观测性与重试两者都保住**」。
  → **fail-closed 的粒度选择：闩死整个通道 vs 保留失败批次 + 允许重试**，
  他们选了后者，并明确写出这是在「确定性」与「可恢复性」之间的取舍。

**验证段有一条特别的**（:41）：一个 AgentLoop 回归测试**让 `resume()` 与一个活的未关闭 turn 赛跑**，
证明原 agent 仍能持久地完成它，**而不会被注入一个 `interrupted` 边界**。
→ **测的是「不会伪造一个收尾记录」**——正是本项目最怕的那类「补一条看起来正常的证据」。

## S-16 `2026-07-24-agent-loop-observable-state-machine.md`（58 行）

**删了什么**：agent loop 把内部控制流当成一大堆 Cordis 事件公开出去——
`agent/post-step`、`agent/session-prefix`、`agent/step-result`、
`agent/turn-continuation`、`agent/turn-stop`，以及旧的 prompt 准备/提交与串行 step 钩子。

**判据①**（:11）：这些事件**把内部阶段公开化了，即便持久会话日志已经拥有对应的 turn/step 事实**。
**判据②**（同行）：它们**混了两种扩展模型**——有的监听器观察边界然后下命令，
有的返回控制决策由 loop 解释；于是「理解这台公共状态机」要同时重建事件顺序、waterfall 优先级和特殊终止覆盖。
**判据③**（:13）：agent 存活期、整体活动、收件项进度、每 turn 结算**是四个独立的状态维度**，
把它们当成一个 status 或一条线性回调序列，会让普通问题变得有歧义
（一个 agent 可以跨多个 turn 保持 `running`；一个被接受的项可能不开 turn 就被丢弃；
一个 turn 可以结算而后续工作让 agent 继续活跃）。

**替代形态**（:26）：**「延续与终止是数据，不是返回的控制枚举。」**
工具调用与被接受的 steering 就意味着需要下一步；带 `concludesTurn` 的工具结果结束工具循环。
loop 不暴露通用 `ContinuationDecision` 或终止返回通道。
→ 对本项目：**把「下一步做什么」编码进可持久的数据，而不是编码进一次性的返回值**——
返回值不进日志，数据进。原文在 Consequences 里写死了这一点（:48）：
**「延续插件发布可持久的 steering，而不是返回一个未被记录的理由。」**

**备选（四条）**（:34-40）：
① 保留细粒度事件序列——否，那把 loop 的私有时序变成永久公共契约，
且让重叠的扩展点能表达互相冲突的决策；
② 把 disposal 表示为第三个 `AgentStatus`——否，与 `agent/disposed` 已表达的注册表生命周期重复；
③ 从 `agent/request-error` 返回 retry 决策——被 S-18 那篇取代；
④ 把持久 turn/step 边界镜像成 agent 事件——否（同 S-04）。

## S-17 `2026-07-26-merge-subagent-control-service.md`（41 行）

**删了什么**：独立的 `ctx.subagentControl` 服务与 `@deepseek-ai/dsh-subagent-control` 包，
合并进唯一公共服务 `SubagentRuntime`；两套错误分类合成一个 `SubagentError` taxonomy。

**判据（本目录最锋利的一条「隐式耦合」判据）**（:11）：
拆分本身有正当理由（provider 分派与 Jobs/持久化解耦），但实际上
「两个服务描述的是同一个能力族，每个 continuable 调用者都需要两个」，
而且绑定 provider 的委派工具**不得不从 `provider.resume` 推断策略，
并去检查 control 服务与 `send_message` 工具是否**碰巧**被加载了**——

> This made **sibling plugin presence decide execution semantics**

——**兄弟插件在不在场，决定了执行语义。** 这是一种极难排查的隐式依赖。

**备选（四条）**（:27-33），其中第二条直接命中本项目的「能力 vs 策略」：
**「从 `provider.resume` 推断 continuable 模式」——否**：
「方法存在**正确地陈述了冷恢复能力，但没有陈述部署策略**。
它逼每个可恢复 provider 进入 continuable 后台语义，**并把缺失的兄弟插件变成运行时错误**。
显式的工具配置把**选择**与**能力**分开。」
→ **「能做」≠「该做」。** 用能力探测替代显式策略声明，会造出无法解释的运行时行为。

**失败时机被明写**（:38）：configured provider 缺 `resume` 时，
continuable 模式**在 provider 挂载时就失败**；缺 Jobs / Agents / 持久化则
**在第一个真正需要它的操作上失败**。
→ **失败点被有意分层：能力不匹配 = 启动即失败；依赖缺失 = 用到时失败。**

## S-18 `2026-07-27-request-error-retry-action.md`（29 行）

**删了什么**：公共命令 `Agent.retry()` / `ReactLoopAgent.retry()`，
以及 loop 为它保留的可变 retry 窗口状态。

**判据**（:9）：恢复决策**在 `agent/request-error` 里做**，却**通过一个公共命令传达**。
那个命令只在一个很窄的 waterfall 窗口与 idle 期间有效，其他运行状态拒绝，
「恢复插件是唯一的生产调用者，所以这个更宽的 live-agent 能力
**暴露了与它们的策略决策无关的状态与行为**」。
→ **判据：决策的归属与传达的通道错位。** 修法是让 waterfall 直接返回 `{ kind: 'retry' }`。

**取消优先级被显式处理**（:15）：loop 在**消费 action 时重新检查 turn 信号**，
所以恢复期间发生的取消或销毁会阻止重试，**即便监听器之后返回了 retry**。
且「抛出异常的恢复永远不产生 action」。

**备选（两条）**（:21-23）：
① 保留 `Agent.retry()` 并用运行时守卫限制窗口——否，接口仍在宣传一个没有生产消费者的 idle 重召操作；
② **返回一个显式的终止 action `{ kind: 'fail' }`**——否，
「`undefined` 已经表示 waterfall 的未处理默认值，并且直接通过 `next()` 组合。
第二个值不会增加任何行为或所有权信息。」
→ **不为「对称好看」增加枚举值。**

## S-19 `2026-07-28-local-json-tree-renderer.md`（34 行）

**删了什么**：第三方依赖 `react-json-view-lite` **以及针对它编译产物的 pnpm patch**。

**判据**（:9）：那个库既不暴露自定义节点渲染也不暴露行身份，
所以要满足需求就得**打补丁改编译后的发行文件**，并且**靠 DOM 遍历从可见标签重建数据路径**；
「补丁的行为是一个无类型的 fork，而它的 source map 与上游源码保持不变」。

**这一篇对本项目的价值在一句实现约束**（:15）：
每个渲染行**直接拿到它的值与属性路径**，对象键与数组下标在递归时扩展该路径，
> so copy actions **never recover application data from rendered DOM text.**

——**复制动作绝不从渲染出来的 DOM 文本里回收应用数据。**
→ 这正是本项目证据链的同型要求：**证据必须来自数据侧，不能从展示层反解**。
一旦从渲染结果反解，展示层的任何截断/格式化都会静默污染「证据」。

**备选（四条）**（:22-28）：保留发行版补丁 / 用上游但放弃预览 /
渲染后再注入预览与行元数据（否——「会依赖同一个私有 DOM 结构，
并把一行劈成 React 所有权与命令式变更两半」）/ 换一个更大的 JSON 查看器
（否——编辑、搜索、主题系统都在只读契约之外，**多出来的依赖面并不能消掉 inspector 专有的复制与布局代码**）。

**后果诚实**（:32）：包现在自己拥有递归渲染、展开状态、ARIA 树结构与 roving focus，
**所以这些语义的改动需要有针对性的组件覆盖**。

## S-20 `2026-07-28-remove-synthetic-log-only-turns.md`（43 行）

**删了什么**：`SessionStore.appendOutOfBand()`、`OutOfBandSessionEventMap`、`OutOfBandSessionEventType`——
它们把一个「只进日志」的迟到事件**包进一对合成的 `turn/start` / `turn/end`** 再 flush。

**判据（对本项目最直接的一条「留痕污染」）**（:9-11）：
这个做法保住了「每个持久事件都必须活在一个 turn 里」的旧规则，
但它**让同一个标识符同时意味着「一次模型循环执行」和「一次仅持久化的更新」**。
而那条旧规则是在「持久化恢复把最后一个 `turn/end` 当作唯一已提交边界」的年代引入的；
现在扫描器保留每一段有效的连续事件，崩溃修复只对**真正打开的 turn** 反应。于是保留合成 turn 会：

> inflated turn counts, **produced execution outcomes for work that never ran the model**,
> and let a late metadata write **consume the next turn number**.

——**为从未跑过模型的工作产生了「执行结果」**，并让一次迟到的元数据写**吃掉下一个 turn 号**。
→ 这是「为了让日志看起来整齐而伪造记录」的典型，与本项目 D-003 正面冲突的那种做法。

**替代**（:17）：拥有 log-only 事件的插件**直接通过 `Session` 追加**；
当操作承诺持久性时，**显式 `await ctx.sessions.flush(session)`**。
**不为了拿到一个检查点而开 turn。**

**核心不变量的边界被重新划定**（:19）：核心继续强制**核心自己拥有的执行关系**
（turn/step 编号、steering/assistant/tool/todo/request-header 事件的包含关系、同 step 的 call/result 配对），
但**允许可合并扩展事件出现在 turn 之间**，
「因为只有声明它的插件知道它是执行域的还是独立的」。
插件的不变量伴随物负责自己的事件关系。
→ **不变量的所有权跟着语义所有权走**，核心不替插件断言它无法验证的东西。

**备选（四条）**（:29-35），四条都值得：
① 保留合成的零步 turn——否，「它报告了从未发生的执行、扰动 turn 编号，
并**逼每个 turn 消费者去过滤仅持久化的记录**。持久性本来就有独立的 `session/flush` 边界。」
② 保留一个通用的核心持久追加 helper（append+flush）——否，
「它的资格标记与并发承诺仍会**把插件策略集中到 session store 里**」；
③ 把标题存成可变会话元数据——否，那会在 append-only 日志旁边**再造一套变更/重放/持久化/fork 协议**
（与 S-01 同一判断）；
④ **要求每个插件事件向核心声明「独立资格」**——否，
「那保留了一个中心白名单，但**让「没声明」意味着一种核心无法验证的执行关系**」。
→ **不要让「缺省值」承担一个你验证不了的语义。** 这一条对本项目的 flag 设计直接有效。

**fork 边界随之放宽**（:23）：会话 fork 可以在**任何开放 turn 之外的稳定事件位置**结束，
不再只能停在 `turn/end`——这样默认 fork 才能保住独立的标题等插件自有的 log-only 记录，
同时仍拒绝切穿正在执行中的前缀。

## S-21 `2026-07-29-shared-base-config-overlays.md`（53 行）

**删了什么**：两棵完整配置树里 **43 行重复**（其中 38 行逐字节相同），
以及 `examples/tui-agent`、`examples/cordis-agent`、`examples/code-mode`、`packages/examples/tui-demo`。

**判据①：位置在撒谎**（:11）——
「两个文件都不是它所在位置声称的东西。`examples/tui-agent` 不是示例：
`apps/cli/src/tui.ts` 把它硬编码成产品默认配置……`dsh-tui-demo` 也不是 demo，
**它就是那个应用**，由发布出去的二进制从 `packages/examples/` 挂载。」
→ **目录名与实际角色不符本身就是一个缺陷**，不是命名品味问题。

**判据②：重复是承载性问题**（:13）——43 行里 38 行逐字节相同、5 行有可辩护的按面差异，
于是「每一次能力变更都得做两遍，而且**可能静默漂开**」。

**判据③：一个被反转的默认（静默 bug）**（:13）——
`composeTuiApp` 读的是 `config.goals ?? {}`，于是**发布出去的 TUI 挂载了 goals、`tool-goal`、
`goal-round-driver` 和 `/goal`，尽管没有任何配置键请求它们**。
→ **`?? {}` 把「没配置」变成了「配置了一个空对象」**，于是可选特性变成了默认开启。
这是本项目在写「flag 触发条件」时最容易犯的同型错误。

**一条真实踩到的框架坑（静默 no-op）**（:19 + :33）：
**include 的 patch 不跨 include 边界**。所以 overlay **必须在同一个 include 层级**作为兄弟 patch list 应用；
把 overlay 叠成嵌套 include 会**静默地停止触达 base 行**。
备选段写了实测结果：「三层链让 `tools` 无法被 patch，
而藏在一层 include 后面的 base **让每一个个人 patch 变成静默 no-op**」，
且外层文件的 patch **只带一条 warning 就被丢弃**。
→ 又一条「不报错、结果看起来正常」的形状。

**故意保留的 no-op**（:43）：`id` 匹配不到任何行的 patch **保持 no-op 而不是报错**——
这是**有意的**，因为一个个人 overlay 要跨多个面共享，`insert` 行按设计谁也不匹配。
→ 与上一条并读：**同样是 no-op，一个是缺陷、一个是设计**，区别在于**它是否被写下来并测试过**。

**`--config` 语义被改**（:23）：`--config <path>` 现在应用一个 overlay
**取代**个人 overlay，「这样 demo 或测试树永远不会继承用户的 provider 与 model」；
旧行为改名 `--config-replace`。两个 flag **都必须活过 `/resume` 的 execve 交接，
否则恢复会静默地改变 agent**。

**验证方式值得抄**（:49）：组合关系
> is checked by **booting each tree through the real Loader and inspecting settled entries, not by reading YAML**

——**用真实 Loader 启动每棵树、检查落定条目来验证，而不是读 YAML。**
两个面都以「零个未加载行」落定。

**「扁平化过程中浮出三个潜伏缺陷」**（:53，全是静默型）：
① TUI 在构造时**只捕获一次**可选的 `sessionQuery` 服务，于是赢了挂载竞态时会**永久禁用 `/resume`**；
② **发布出去的 session-store 根目录静默退回到项目本地的 `./.sessions`**；
③ `--config-replace` 被 resume 交接丢掉。
→ **「把重复合并成一份」这个动作本身就是缺陷探测器**——三个缺陷都是在合并时才现形的。

## S-22 `2026-07-29-simplify-web-image-input-v1.md`（37 行）

**删了什么**：第一个 Web 图像输入切片里**投机性的公共面**——
任意 CLI provider 挂载、输出模态发现、alt text、provider 中立的视觉 token 定价、
以及没有跨包消费者的浏览器生命周期 API。

**判据**（:9）：保留这些投机面会**把尚未选定的未来行为变成公共契约**，
并让第一个能力更难评审与维护。

**四条备选里两条对本项目直接有用**（:25-29）：
- **加存储事务或回滚协议**——否：**无存储的校验**（先全量校验、再一次性保存）
  「防止了后面的畸形成员让前面已有效的成员变成无引用对象」；
  更强的全有全无跨独立内容寻址对象需要所有权或回收语义，当前产品路径不需要。
  → **用「校验与写入分离」换掉「事务与回滚」**，是本项目做批次闸门时可抄的形状。
- **用一个统一 tile 公式估算每张图**——否（**本篇最该抄的一句**）：
  > A hard-coded provider-neutral estimate **would look authoritative while being wrong**;
  > provider usage is the authoritative accounting source.
  ——**一个硬编码的中立估算会「看起来权威而实际是错的」**；权威的记账源是 provider 报回来的用量。
  → 直接对应本项目：**口径必须来自权威源，不能用一个看起来合理的自算公式冒充。**

**后果里明写了这个取舍的代价**（:35）：
「请求前的 token 压力**可能低估视觉输入**，直到设计出 provider 感知的估算器；
**而报告出来的用量仍然精确。**」
→ **估算可以不准，但记账必须准，且两者要分开说。**

**重新引入的门槛被写死**（:37）：
「重新引入任何被删掉的面，**需要一个具体消费者以及它的失败、生命周期、重放与测试契约**，
而不是为了与这个预发布形状兼容。」

> 与 S-07 并读：S-07 删掉了 `ImageBlock`，本篇（三周后）把它**带回来了**，
> 但形态不同——`ImageBlock` 现在携带**持久附件引用**，可选显示名兼作无障碍文本，
> 核心块**没有单独的 alt-text 字段**（:17）。
> **这就是 S-07 说的「等到有路径能兑现它时再回来」的兑现过程**，且回来时更窄。

## S-23 `2026-07-30-private-agent-send.md`（27 行）

**删了什么**：公共 `Agent.send()` 与导出的 `SendTarget` / `SendOptions`——
把路由矩阵收回 `ReactLoopAgent` 的私有 helper。

**判据**（:9）：生产调用者只用语义化的 `followup()` / `steer()` / `inject()`；
路由矩阵的**第四种组合（`next-turn` + `wakeup: false`）除了测试没有任何消费者**。
保留这个潜伏能力还**逼所有替代 `Agent` 实现与测试假体去接受实现级的路由策略**。

**备选（两条）**（:19-21）：
① 保持路由矩阵公开——否，「暴露的是机制而不是调用者意图，并把它强加给每个替代驱动」；
② **加一个公开的 quiet-queue 方法**——否，「具名方法确实比裸路由标志清楚，
但**当前没有任何生产工作流需要「停在那里、等一次无关的投递把它叫醒」的工作**」。
→ **删除后如何回来也写死了**（:27）：「被移除的 quiet-queue 能力
只能带着**一个具名消费者与显式的生命周期语义**回来。」

## S-24 `2026-07-31-capability-neutral-sandbox-policy-context.md`（35 行）

**删了什么**：sandbox 策略上下文里的**两个能力族注册表**（enforced-family / escalatable-family）、
六处后端与工具的贡献点、token 集合、两表求交与排序、每次生命周期变化触发的 prompt 装配失效。

**判据（本项目做「口径声明」时必须记住的一条）**（:11）：
那份清单**既不是陈述文件策略所必需的，也不是模型可见能力的权威来源**——

> A backend contribution could name a family **whose model-facing tool was absent or hidden by request scope**,
> while tool schemas already told the model which exact operations were available.
> The registries therefore widened the public service and lifecycle contract
> **to maintain an approximate English sentence.**

——后端贡献可能命名一个「模型侧根本没有对应工具、或被请求作用域藏起来」的能力族；
而工具 schema 早已告诉模型确切可用的操作。
**这两个注册表把公共服务与生命周期契约撑大，只为了维护一句近似的英文句子。**
→ 对本项目：**「声明的能力」与「实际可用的能力」是两个东西**；
只要它们由不同来源维护，声明就会漂成一句「看起来对」的话。

**权威来源被逐条指名**（:19）：
工具 schema 是「哪些操作可用」的权威；工具结果是「具体操作的拒绝与被批准的更宽重试」的权威；
文件系统、一次性 bash、terminal 实现继续解析并强制同一套按调用的策略。
**只有多余的、面向模型的能力清单被删掉。**

**新文案的写法**（:17）：把能力声明**条件化**——
`read-only` 下说「这类操作在当前常驻模式下不能改文件，**你照常试一个可用工具，
然后遵循该工具返回的拒绝与升级指引**」；`workspace-write` 下说规范会话工作区与限定的临时区允许；
`danger-full-access` 下说 DSH 文件沙箱不限制。
→ **条件式陈述在「无可用操作」时也仍然为真**，这是它替代清单的关键（:29 也复述了这一点）。

**备选（三条）**（:25-29）：
① 保留注册表但减少测试——否，「**组合爆炸的测试反映了这个设计的成本，它们不是成本的来源**」；
② 从工具注册表**推导**一份精确清单——否，「当前策略只需要一句真实的条件陈述，
而精确可用性已经出现在装配好的工具 schema 里，且会随请求作用域变化。
把每个 schema 映射回一个执行后端，会引入**又一个没有当前消费者的派生关系**」；
③ 除非某个后端宣告执行能力，否则省略策略上下文——否，那会重建注册问题，
并**让策略的可见性依赖可选贡献者**。

**后果**（:35）：模型不再收到一份散文式的沙箱能力族清单，
它收到的是**精确的工具 schema + 一句常驻的文件策略陈述**。
「如果未来某个产品需要一份单独的能力清单，
**它必须从权威的按请求装配里派生，而不是通过后端注册的旁路重建。**」

## S-25 `2026-07-31-drop-user-message-edit-stub.md`（27 行）

**删了什么**：用户气泡上的 edit 按钮。

**判据**（:9）：**背后什么都没有**——没有点击处理器、没有客户端 mutation、
没有「重新发送一条被编辑过的消息」的宿主操作。
> A user who found it saw **an affordance the product cannot honor.**
（找到它的用户看见的是一个**产品兑现不了的可供性**。）
→ 与 S-07 同一族判据：**宣告了一个没有任何路径兑现的能力。**

**备选（两条，都很短但都精准）**（:21-23）：
① **把按钮禁用并加 tooltip**——否，「一个可见但死的控件**仍然在宣传编辑功能**，
解释成本一样，**移除才是诚实的状态**」；
② **接到队列编辑器上**——否，队列编辑的是**尚未发送**的消息，
而一条已结算的用户消息**已经在 transcript 里、也在模型的上下文里**，
复用那个编辑器「**会静默地意味着另一件事**」。

**缺失被记录在案**（:13）：包 README 把这个缺失的能力记进 Known Limitations，
web 的 message-actions golden **钉住「没有这个控件」的那一行**。
→ **删掉一个能力之后，用测试钉住「它不在」**，而不是靠人记得。

**重新引入的条件**（:17）：控件与能力**一起**回来——
需要一个能编辑已结算用户消息的客户端 mutation，
**以及宿主对「被编辑的消息对那个已经消费过它的 turn 意味着什么」的决定**。

## S-26 `2026-07-31-one-route-to-add-a-workspace.md`（57 行）

**删了什么**：添加 Workspace 的第二条路径（按名字创建 `<workspaceRoot>/<name>` 的对话框）
及其 `create.*` / `menu.createWorkspace` / `workspace.new` 文案、
网关的 `workspaceRoot` 配置、`dsh web` 的 `--workspace-root` flag；
`workspace.create` 的入参从 `{ name } | { path }` 收窄到 `{ path }`。

**判据**（:9）：两条入口**重叠**——浏览目录的占位本身带 **New folder** 可供性，
所以「选一个目录」已经覆盖了「新建一个」。两个入口意味着一个结果两套词汇、
一个自带重名规则的命名对话框，以及**一个操作者既看不见也选不了的创建目标**。

**由此引出的一条通用界面规则**（:17，值得抄进本项目的界面章节）：
> **A menu exists to disambiguate between targets.**
当只剩下添加这一个入口时，锚点手势**就是**那个动作：直接打开流程，不渲染 popover。
「一行的 popover 花掉一次点击，却没有任何可选的东西。」
规则是**一个谓词 `addIsTheOnlyEntry` 覆盖两个界面**，而不是每个界面写特例。

**两条从该规则掉出来的边界，被明写为规则的一部分**（:21-22）：
① **空列表只有在基线落地之后才算最终**——`phase` 还是 `pending` 时，
hero 保留菜单与加载状态，**而不是跳进一个「等 workspace 到了就没必要了」的流程**；
② **目录流程的洞没有占位时，就没有东西可以用来添加**——
侧边栏干脆**不渲染按钮**，而不是渲染一个死的；hero 的菜单在没有可列的东西时什么都不显示，
因为「**一个空的 popover 会声称存在一个并不存在的选择**」。

**一处「不静默」的处理**（:57）：hero 的锚点 chip 仍然宣告 `aria-haspopup="menu"`，
而直接打开路径弹的是对话框。要让这个宣告变成真的，需要把流程的呈现选择
沿着 `conversation.hero.workspace` 所有者契约往上路由（流程拥有决定，chip 拥有宣告，两者在不同包），
**所以它被登记为一个具名的后续项，而不是一处静默的不一致**。
→ **暂时修不了的不一致，要有名字。**

**备选（六条）**（:40-50），三条值得记：
- **为「以后可能加的入口」保留菜单外壳**——否，理由被命名为
  **「require a current owner and need」**（要有当前的所有者与需求）：
  「没有这样的入口存在，**等它来了再恢复菜单，比现在先发一个空壳更小**。」
- **在同一个改动里删掉线路上的 create-by-name 分支**——否，
  「UI 决策并不依赖后端与 CLI 的删除，后者有自己的契约与测试，**构成一个可独立评审的改动**。」
  → **删除也要按可评审单元切分**，不是一次删干净就好。
- **在 e2e 脚手架里通过宿主注册 workspace，而不是驱动对话框**——否（**测试设计的关键判据**）：
  「那会把全部 15 个场景与选择器解耦，于是**这条泳道里就没有任何东西能证明幸存的那条路径真的能到达一个活的 composer**。」
  现在每个场景都走真实对话框；只有「在选择器里新建文件夹」那一半集中在一个场景里，
  因为到处重复会让共享 helper 失去幂等性**而不带来额外信号**。

**一条环境依赖的测试被钉死**（:36）：`smoke-real.e2e.ts` 是唯一启动未打补丁的发布树的场景，
其中 `-auto` 行按宿主解析；现在通过 `--config` overlay **钉住 `-browse`**，
「这样**开发者的显示环境就不能决定这个 picker 究竟能不能被驱动**」。
→ 与本项目「评测集冻结」（D-012）同型：**让环境不能改变判定结果。**

## S-27 `2026-08-03-omit-invariants-from-shipped-config.md`（30 行）

**删了什么**：发布出去的 `dsh` 配置树里对 `@deepseek-ai/dsh-invariants` 服务
与各包自有 `./invariant` 伴随物的挂载；CLI 包因此不再直接依赖不变量服务。

**判据**（:9）：不变量是**可选的开发期诊断**。
发布的 TUI 挂了服务与四个有状态伴随物，而发布的 Web 树没挂，
于是**两个产品面有不同的诊断成本与失败行为**；
一次关系断言失败**可能终止一次普通的 TUI 运行**，
尽管「始终在线的产品边界仍然负责会话校验与不可变历史」。
→ **判据：诊断设施不能改变产品的失败行为，更不能在两个面上不一致。**

**分层被明写**（:15）：会话校验、快照、冻结、被引用源事件的校验**始终在线**，
不依赖那个可选服务。可选的只是关系断言。
→ 对本项目：**「必须始终成立的完整性检查」与「开发期诊断」要分开**，
前者不能挂在一个可以被配置掉的服务上。

**备选（三条）**（:21-23）：
① **用 `enabled: false` 挂载**——否，「发布树与 CLI 依赖仍然背着一份不装任何检查的诊断」；
② 保留只在 TUI 挂载——否，两个面失败行为仍不同；
③ 把不变量支持从仓库里删掉——否，包自有的检查在测试、示例、生成的 SDK、
显式开发组合里仍然有用，**「只有默认产品配置在范围之外」**。

**验证方式**（:17）：**已构建 CLI 的 config-dump 测试检查两个发布面，
并拒绝服务条目或任何 `@deepseek-ai/dsh-*/invariant` 条目。**
→ 「不该在的东西不在」是被自动化检查的，不是靠约定。

## S-28 `2026-08-04-drop-windows-powershell-picker-fallback.md`（38 行）

**删了什么**：win32 原生目录选择器下面的两级 PowerShell 兜底链
（`pwsh.exe` → `powershell.exe` 5.1，同一份 WinForms 脚本 + `SetProcessDPIAware`），
以及为它加宽的触发条件、三重失败的 `AggregateError`、每层的 abort 重检。

**判据（本目录里对本项目最有用的一条「兜底该不该存在」的判据）**（:9-13）：
这条链存在是为了在 koffi 层「不可用」时仍有可用的选择器，但
> every trigger it plausibly protected was **a failure of our own packaging or deployment, not of the operating system**

逐条拆：
- koffi 的原生二进制是普通可选依赖（无安装脚本），**装得上包的宿主就有二进制；
  装不上的宿主在安装包时就大声失败**——兜底代码两种情况下都不会被加载；
- 「老旧 Windows」不可能发生——本仓库支持的 Node 版本跑在远新于 Vista 时代 ABI 的 Windows 上；
- **koffi/COM 缺陷只会让对话框子进程崩溃（崩溃隔离），
  而「对我们自己的 bug 的正确反应是把失败暴露出来，不是静默降级到一个遗留对话框」。**

**由此提炼出的判据本身被写成规则**（:21，**本项目应直接借用**）：
> a fallback tier exists **only for tools the OS/desktop environment provides and may omit**
> (`zenity` → `kdialog` on Linux); **tools our own package ships (`koffi`) fail loud.**

——**兜底只为「操作系统/桌面环境提供、且可能不提供」的工具而存在；
我们自己打包发出去的东西，失败就大声失败。**

**处理被反转的旧笔记的方式值得学**（:23）：本篇「合并并删除」了那篇 pwsh-first 的 DPI 修复笔记，
「它的决策在这里被完全反转」，但**明写了那篇笔记里「真实成立的部分」**
（PowerShell 7 渲染现代 `IFileDialog` 而 5.1 的 `FolderBrowserDialog` 硬连到遗留控件；
`SetProcessDPIAware` 确实修正了 DPI 上限；pwsh→5.1 那一跳存在是因为可解析的 PowerShell 6 没有 WinForms，
退出码 1 而不是 `ENOENT`），并说明它「不再指导未来在 koffi-only 层上的工作」。
→ **反转一个决策时，把旧决策里经验事实的部分与判断的部分分开处理。**

**备选（三条）**（:27-31）：
① 只去掉 pwsh 质量层、保留 koffi → 5.1——否，剩下那层**仍然在为我们自己打包的依赖兜底**，
并**仍然把我们自己的 vtable/COM 缺陷藏在一个遗留对话框后面**；
② 原样保留——否，它「把一次失败的选择降级成一个 `AggregateError`，
**而其中最可执行的一条居然是一个 PowerShell 宿主**」；
③ 原生选择失败时运行时回落到 `browse`——否，会双挂两个后端并**模糊能力边界**。

**后果**（:35）：win32 的失败面变成「一层、一个错误」，
调用者看到的是**真实原因**（koffi 加载失败 / COM 拒绝 / 对话框崩溃），
而不是一个链式聚合出来的错误。
**重新引入的条件**（:38）：只有当出现一个**在我们打包链之外**的 win32 机制
（一个我们不发布的、系统提供的对话框宿主）时，才在同一判据下允许一层兜底。

## S-29 `2026-08-04-remove-tui-package.md`（39 行）

**删了什么**：整个 `packages/ui/tui` 包及其源码、包测试、终端快照、依赖声明、
被打过补丁的 `pi-tui` 产物、workspace 引用、生成的服务目录条目与文档，**没有兼容包也没有别名**。

**判据**（:9-11）：移除隐式的 `dsh` 终端应用之后，这个包**没有任何发布出去的组合**了；
它仍然背着渲染器、交互命令与提问适配器、扩展 overlay、快照 fixture、被打补丁的依赖、
以及「把 TUI 宣传成受支持的应用界面」的 SDK 脚手架。
「保留那个面就要维护一个产品规模的前端，**而它唯一剩下的消费者是项目生成器本身**。」
第二条判据：**这个包让仓库「受支持的应用清单」变得有误导性**。

**处理「随包一起消失的知识」的手法**（:21，本轮最值得抄的记录纪律之一）：
本篇**合并收纳了那些「只属于被删包、删完就无法继续保持当前性」的记录**——
终端 UI 曾经做对的事（长对话中保持会话身份可见、去掉重复模型标签、
给消息附上耗时与阶段状态、在 prompt 旁显示 workspace 与分支上下文、
**保守地解析完整 XML 包装以产出人类可读的兜底输出**）被逐条列出，
然后一句话定性：「这些选择改善了一个终端前端，**但不构成在没有部署的情况下保留它的理由**。」
并留下一条**跨越删除仍然有效的约束**：
> A future XML fallback **must still use a real parser rather than regular expressions.**

——**未来的 XML 兜底仍然必须用真正的解析器，而不是正则。**
→ 这条与本项目 **D-017（自建封闭解析器、`eval()` 硬性排除）** 是同一条原则的两个实例。

**备选（三条）**（:29-33）：
① 保留包但不发布——否，仍然把一个不受支持的终端前端**当成可复用的产品面呈现，
却没有一个真实组合去证明它的生命周期**；
② 为外部消费者保留 SDK 选项——否，生成器会脚手架出一个**仓库端到端不再接受**的应用；
③ 把包挪到 examples 或 experimental 组——否，
「**挪动代码并不提供当前的产品需求、被维护的部署或装配后的验收**。
未来的终端前端应该从它真实的宿主与交互需求出发，而不是默认继承这份实现。」
→ **「先挪到 experimental 再说」被明确否掉**，这是本项目最容易走的一条软路。

**重新引入的条件**（:39）：需要一个**具名的产品或部署**、一个显式包边界、
一个具体的交互 provider，以及**针对该前端的装配级生命周期与 transcript 验收**。

## S-30 `2026-08-06-buffer-free-feedback-telemetry.md`（29 行）

**删了什么**：feedback-only 遥测模式下「为每个投影事件保留一份深拷贝 + 已脱敏记录」的缓冲。

**判据**（:9）：那份保留**复制了规范会话日志**，
并且对一个**长期存活但从不记录 feedback 的会话无界增长**。

**替代做法**（:13-15）：on-demand 捕获**不注册任何 session / flush / 操作事件监听器、不保留任何投影记录**；
`captureSession(session, throughSeq?)` 在触发时**去读规范会话日志**
（从交接游标之后到一个可选的闭区间序号边界），再做投影、深拷贝、跑 waterfall、交给后端。
`FEEDBACK_ONLY` 用 `feedback/record` 事件的序号调用它——
「追加在 `session/event` 监听器运行时**已经提交**，所以重放里**包含该 feedback 事件、
且不可能包含更晚的后缀**」。
→ **用「规范日志 + 一个序号边界」取代「自己维护一份影子副本」**，
这与本项目「证据链以持久记录为唯一真相源」是同一形状。

**被诚实标注的语义变化**（:17 + :29）：
- on-demand 捕获**只读规范日志，所以它不再发出 `agent-error` 或 `shutdown` 这类操作性记录**；
- **脱敏在 feedback 时求值，而不是在追加时求值**；
  于是「**feedback 之前的一次脱敏策略变更会影响那次重放**」。
→ 这是一个**真实的语义差异被写下来而不是被抹平**的例子。

**备选（三条）**（:21-25）：
① 保留捕获期的已脱敏记录——否（它保住了逐事件观察到的确切脱敏策略与操作性记录，
但复制了无界前缀；「这个模式承诺的是 feedback 触发的会话日志上传，
**不是捕获期的策略快照，也不是 feedback 之前的操作性遥测**」）；
② 保留会话事件引用或序号——否，「规范日志已经同时提供顺序与身份。
第二份索引省下负载拷贝，**却增加生命周期状态而不使能任何必需行为**」；
③ 写一份持久的 pre-feedback 假脱机——**推迟**，直到某个部署真的需要 feedback 之前的崩溃恢复；
「它给一个『进程在 feedback 之前退出就什么都不上传』的模式增加了存储、清理与保密策略。」

## S-31 `2026-08-06-user-bubbles-drop-the-branch-action.md`（27 行）

**删了什么**：用户气泡与已消费 steering 气泡上的 branch（分叉）控件。

**判据①：那个门在这些气泡上实际上永远打不开**（:9）——
开启 turn 的用户消息后面必然跟着它自己 turn 的节点，被消费的 steering 按构造就在 turn 中间，
所以控件只能在「turn 结束时该消息后面一个节点都没有」时启用，即**第一个模型事件之前的一次取消**。
> Readers therefore saw **a control that never enables, with a tooltip promising a state the button cannot reach.**

**判据②：这个可供性即便读懂了也在误导**（同行，**本项目要特别记住的一条**）——
在某条消息 seq 上 fork，切的是**包住它的 `turn/end`**，
所以「在我的消息处分叉」**包含它下面的那个回答**，
「**与在自己气泡上看到这个控件所暗示的『分叉去重问』读法正好相反**」。
→ **控件位置暗示的语义 ≠ 实现的语义**，这是一种不会报错的错误。

**备选（三条）**（:19-23）：
① 只在不可用时隐藏——否，保住了那个几乎不可达的启用态，代价是
「一个只在 turn 还没产出任何东西就死掉时才出现在自己气泡上的图标」；
② 保持现状（可见但不可用）——否，之前那个决策选择「可见」是为了**让 tooltip 解释一个读者能到达的边界**；
在这些气泡上边界实际不可达，「于是解释在给一个本不该存在于此的控件撑腰」；
③ 「在消息之前分叉」的语义——**范围外**，它需要在消息前切一刀 + composer 预填，是不同的宿主操作。
> Removing the current control **keeps that seat free for such a feature instead of squatting on it with opposite semantics.**
（移除现有控件是**把这个位置腾空**，而不是让一个语义相反的东西占着。）

**保留的一侧也讲清楚了**（:15）：assistant 一侧「可见但不可用」的呈现**不变**——
在一个回答下面，不可用是**短暂且可达**的状态（当前 tail 被一个尾随的工具行或错误行占着），
「**这正是 tooltip 存在的意义**」。
→ **同一种「可见但禁用」的呈现，在可达边界上是对的，在不可达边界上是错的。**

## S-32 `2026-08-08-copy-only-preset-authoring.md`（36 行）

**删了什么**：agent-preset 设置页里的 web YAML 编辑器与 `agentPreset.write`
（接受任意组合文本），以及 `assertComposition` 本身。

**判据（本篇对本项目 D-017 是直接同型证据）**（:9）：
那个形状检查靠的是 Loader 自己的 `entryListSchema`——
> whose dialect includes `!!js`, so **"shape-checked text" was still arbitrary code on the next mount**.

——**这个 YAML 方言包含 `!!js`，所以「已做形状校验的文本」在下一次挂载时仍然是任意代码。**
再加一句定性：「作为编辑器很弱，作为能力很宽，而且是本节不得不防的 editor-vs-roster 竞态的来源。」
→ **schema 校验通过 ≠ 安全**，只要底层方言允许求值。
这与本项目 D-017 排除 `eval()`、自建封闭解析器是同一条理由，且他们是**踩到之后才删的**。

**替代形态**（:13）：**创作变成宿主端的一次复制，文件才是编辑器**。
`agentPreset.write` 变成 `agentPreset.copy { from, agentPreset, name? }`——
两个 id 由宿主对自己的根解析、整目录 `cp`（解引用符号链接、权限收紧到 owner-only）、
元数据重写为保留源的描述但**绝不保留它的名字或 `order`**。
页面变成：对发布组合的**只读查看器**、复制对话框作为唯一创建入口
（**没有空白的「新建 preset」——「从零写 YAML」不是人们真会做的事**）、
自定义行的删除、以及一个「带你去看文件」的位置动作。

**后果里的四条都是判据**（:17-20）：
- **两个方向上都没有组合文本、也没有路径穿过浏览器线路**；
  `entryListSchema`/`!!js` 这个隐患**随 `assertComposition` 一起消失**。
  特权集合现在是 `read`/`copy`/`openDocument`/`remove`——**没有一个接受文件系统目标**。
- 编辑器没了之后，手改 `agent.cordis.yml` 成为**唯一**的组合编辑方式，
  于是常驻挂载层增加了 **stamp-keyed 代次**（比较文件 mtime+size）：
  「**没有这个，一个被编辑过的文件会一直提供陈旧的组合，直到进程重启。**」
  → 又一处静默陈旧。
- 一份复制是**完整快照，会与升级后的发布源漂开**——**接受**，
  因为 preset 层没有 patch 语义，且发布出去的集合自己也付同样的代价，换来的是**一文件可读性**。
- `read` 去掉了 `writable`（没有编辑器要门控了），且**内建目录永不被打开**
  （`openDocument` 像 `remove` 一样拒绝非 `user` 信任级）：
  安装目录会被升级覆盖，「把编辑器指进去等于**邀请一次升级会静默丢弃的编辑**」。

**「承载性细节」一节（:24-26）有三条，第一条最值得抄**：
> **Copy target refusal is two checks on purpose.**
花名册检查拒绝任何某个根提供的 id——一个命名得像发布 preset 的用户目录会被遮蔽，
于是「创建」会落下一个**谁也不会列出来的文件**；
磁盘检查（`cp` 之前的 `PresetExistsError`，并以 `errorOnExist` 作为竞态兜底）
拒绝一个占着这个名字但不是 preset 的目录，**而这种目录是发现流程看不见的**。
→ **两道检查各自封住一种「看不见的冲突」**，不是冗余。

**备选**（:30）：保留 write 但换个更好的编辑器（CodeMirror 等）——
「仍然是跨线路的任意能力，仍然是竞态来源，**而且仍然比用户自己的编辑器差**」；
patch 语义的复制——「bundle 平面之下不存在这样一层」；
浏览器端 `host.openPath` 加返回路径——「**路径一旦成为请求参数，就打破了 README 的『无任意目标』不变量**」。

## S-33 `2026-08-08-remove-cli-demo.md`（34 行）

**删了什么**：`@deepseek-ai/dsh-cli-demo` 整个包——bin、参数语法、app 组合、取消生命周期、
text/JSON/stream-JSON 输出契约、构建产物、文档面、测试套件，**没有别名也没有兼容包**。

**判据（本项目做 demo / 评测脚手架时必须记住的一条）**（:9）：
> The two entry points also assembled different trees,
> so **a successful demo did not prove the shipped `headless` profile**

——**两个入口装配的是不同的树，所以 demo 跑通并不能证明发布出去的 profile 能跑通。**
用户还得在两个重叠的命令之间选。

**保留测试需要的东西，但不保留产品面**（:11 + :17）：
「重放套件仍然需要规范会话事件来钉住装配后的后端行为。
**这个测试需要并不要求一个已发布的命令或兼容契约。**」
于是 `examples/headless-agent` 变成**显式的测试组合**——
把 agent-spine-demo、一个根 agent、JSONL 持久化、检查点策略**作为独立行挂载，
而不是藏在一个 app bundle 后面**；example 内部的驱动器**只被测试启动、没有 bin、
也不定义任何受支持的产品输出格式**。

**备选（四条）**（:21-24）：
① 保留成 `dsh --profile headless` 的别名/包装——否，第二个 bin 与包**保留两个可被发现的所有者却不增加能力**；
② 把 JSON / stream-JSON flag 挪到产品命令上——否，**没有当前产品消费者需要它们**，
「采纳旧 demo 协议会仅仅为了省测试机械而扩大规范 CLI 契约」；
③ 把规范事件快照跟包一起删——否，**它们钉住的是「模型可见的装配后行为」，
这是最终文本的产品验收观察不到的**；
④ 保留 app 插件只删 bin——否，隐藏的组合仍会复制显式的 headless profile，
并**掩盖测试 leaf 究竟挂了哪些服务**。

**重新引入的门槛**（:30）：一个独立的一次性包**只有在它拥有一个真正独立的、有版本的协议
（且那个协议不能属于产品启动器）时**才能回来；「换个拼写或加个输出垫片是不够的」。

## S-34 `2026-08-09-bounded-fixed-rate-schedule.md`（44 行）

**删了什么**：日历与 Cron 表达式、求值器依赖、解析器、规范化器、时区搜索、频率证明、
持久记录与分派变体、测试、快照、第三方声明条目；
以及跨记录的 300 秒准入门、持久化的门证据、延迟投递字段、门耗尽状态。

**判据**（:9-11）：初版把「固定间隔」与「日历表达式」当成一个通用子系统，
「即使被请求的行为只是『每 N 秒重复一次』」，也把持久协议与活的所有者撑大了。
第二条判据是**冷启动/繁忙会话无法有意义地重放每一个错过的间隔**：
那会造出一个**大小取决于停机时长**的模型 turn 积压；
而把下一个目标推到投递时间又会让固定频率漂移。

**替代做法**（:15）：只保留 `every_seconds`（安全整数，≥300）。
创建时存下第一个目标与间隔；每次分派存记录 id 与一个墙钟 `acceptedAt`，
**纯整数运算**选出「决策时刻或之前、对齐创建锚点的最新一次发生」，
然后直接推进到它之后的第一个对齐目标。
> **No missed occurrences are enumerated, persisted, or replayed.**

**旧数据的处理**（:21）：预发布期的旧 Cron 记录
**由严格的 version-1 解码器拒绝，而不是迁移、也不是通过兼容残留接受**。

**备选（五条）**（:25-33），两条对本项目直接有用：
- **重放每一个错过的发生**——否：「它保住了每一个名义事件，但停机后会造出无界积压，
  而且是糟糕的提醒行为。**只补最新一次**传达了当前该做的工作，
  **而不假装这个会话一直是活的**。」
  → **「只补最新」是一种诚实**：不伪造一段其实没发生的历史。
- **保留全局的重复准入门**——否，共享门虽然能限制模型 turn 总量，
  但**让互不相关的提醒互相拖延**，且需要持久的跨记录历史。
  改用「批处理 + 每规则最小频率」达到同样的有界性。
  → **限流的粒度选择：全局门需要跨记录持久状态，规则级门不需要。**

**验证**（:37）：包含「源码、依赖与生成目录审计**拒绝 Cron 与全局门的残留**」。

## S-35 `2026-08-09-conversational-schedule-delivery.md`（39 行）

**删了什么**：一条到期提醒的**第二份持久 Web 回执**——
Schedule 投影、持久化成功事件、宿主历史与实时 sidecar、客户端同序号升级、
通用事件视图槽位、专用 renderer，以及承载它们的额外包。

**判据①**（:9）：这条路径**把一个特性的确认 UI 摊到了 Session、持久化、Host、客户端运行时、
会话 UI 和一个额外包上面**。

**判据②（本轮全部 121 篇里对 D-003 最直接的一条）**（:11）：
> The receipt also created **a second meaning of delivery**.
> **It remained visible when the model turn failed**, while the conversation itself
> contained no successful reminder answer.

——**回执制造了「投递」的第二种含义：模型 turn 失败时它仍然可见，
而对话里根本没有一条成功的提醒回答。**
「用户需要的是被排期的对话继续下去；他们不需要一个单独的持久徽章
来证明**一次内部分派被尝试过**。」

**替代做法**（:15-17）：到期提醒**等 agent 的空闲维护阶段**，然后调 `followup()`——
走普通的后续 turn、出现在普通会话 transcript 里；
Schedule **绝不调 `steer()`，绝不打断当前 turn**。
`schedule/change` 仍是唯一的持久 Schedule 状态，它的分派操作**只记录「后续项已被同步入队」**，
> Dispatch **does not claim model success, user acknowledgement, or an external notification.**
并明写残留风险：「入队与持久分派之间那段狭窄的崩溃区间**仍然是 at-least-once**。」

**备选（四条）**（:23-29），其中第三条是本项目命名规范的直接教材：
- **保留「提交感知」的回执**——否，它能证明一次分派到达了持久化（即便模型失败），
  但「那是**实现层面的结果，不是用户的提醒**」；
- 在对话里渲染原始 `schedule/change` 事件——否，仍然把内部状态转换当用户可见消息暴露；
- **把分派当作提醒投递成功**——否：
  > The dispatch precedes the model request and cannot establish that an assistant answer exists or was read.
  > **Naming it delivery would overstate the durable fact.**
  ——**分派发生在模型请求之前，无法确立回答存在或被读过。把它命名为「投递」会夸大那条持久事实。**
- 到期时 steer 当前 turn——否，那让时序去打断不相关的工作。

**后果**（:38）：「**一次失败的模型 turn 就是一次失败的 turn，而不是一张自相矛盾的成功回执。**」
需要外部投递或已确认投递的消费者，「需要一个不同的产品边界，带它自己的通知与确认语义」。

## S-36 `2026-08-09-explicit-schedule-time-zone.md`（47 行）

**删了什么**：把浏览器时区**持久化成会话默认值**的整条链路——
`SessionHeader.timeZone`、create/resume/fork 的时区冲突规则、JSONL 元数据字段、
SQLite 列与迁移、客户端创建管线、Host 比较、以及为「省略的字段是否安全」而设的确认协议。

**判据**（:9-11）：隐式的本地 `at` 输入**把一个浏览器事实变成了共享的产品状态**；
「那些复杂度大多**坐在 Schedule 之外**」；
而且「模型在调用工具**之前**就已经解释了自然语言，
所以一个持久的会话默认值**复制了一个假设，而不是加强绝对时间的边界**」。

**替代做法（三层，每层的权威被点名）**（:15-19）：
- **浏览器时区是请求局部的 provenance（来源证据）**：Web 客户端**每次 prompt 都采样**，
  Host 在 RPC 边界校验并规范化，**记在那条确切的 `user-rpc` 消息上**；非法值**拒绝 prompt 准入**。
- **时间上下文从开放 turn 里的原始 user-rpc 消息派生出「唯一 / 混合 / 缺失」三态**：
  唯一 → 告诉模型按该时区解释未限定的日期时间；
  **混合或缺失 → 告诉模型去问用户**。
  > The configured or process zone is **only a display fallback and is never presented as user authority.**
  ——配置或进程时区**只是显示兜底，绝不作为用户权威呈现**。
- **Schedule 不接受任何隐式本地时区**：`at` 要么是带偏移的严格 RFC 3339，
  要么是精确的 `{ date, time, time_zone }`；
  **结构化形式必须带时区，即便时间上下文刚给模型看过一个浏览器时区**。
  Schedule 不 import 时间上下文、不检查用户消息的来源、不读会话 header、不产生确认错误。

→ 三层合起来是本项目最该抄的一条：
**「来源不唯一/缺失 → 不猜，去问」**，而且**下游不许把上游的展示性提示当成授权**。

**备选（五条）**（:25-33），三条值得：
- 把首个浏览器时区持久成不可变会话默认——否，「把所有权摊到核心与持久化，
  而旅行与并发标签页**仍然需要不匹配处理**」；
- 用最近一次浏览器时区作为可变会话状态——否，
  「**会让一个标签页静默改变另一个标签页的解释**，并让重放依赖更新顺序」；
- **让 Schedule 去检查最近一条时间上下文消息**——否（**本项目要抄的措辞**）：
  > A prose snapshot is **model-visible evidence, not a typed package seam.**
  ——**散文式快照是「模型可见的证据」，不是「有类型的包接缝」。** 消费它会把 Schedule 耦合到 AgentLoop 历史；
- **让 Host 把 `time_zone` 注入工具调用**——否，
  「Host 无法知道模型解释的是哪一句自然语言表达，也不知道用户是不是点了另一个时区。
  **改写模型参数是在错误的边界上隐藏语义。**」
- 要求模型对每一个未限定时间都发问——安全但不必要地打断常见情况。

**验证段有一条环境钉死**（:37）：装配后的 Web 场景**把 Playwright 固定到 `Asia/Shanghai`**，
经真实 composer 发送，**在模型请求里观察到同一个时区**，验证一次显式的本地工具调用，
再快照普通的提醒回复。
→ 与 S-26 的 `-browse` 钉死同型：**让环境变量不能左右判定。**

**后果里明写了保证的边界**（:47）：
> The model may still make an interpretation error;
> **the tool guarantees only that the explicit calendar value is valid and deterministic.**
——**模型仍然可能解释错；工具只保证「显式给出的日历值是合法且确定的」。**
→ **把保证的范围写死**，不让读者以为整条链路都被保证了。

## S-37 `2026-08-09-remove-repository-plugin.md`（44 行）

**删了什么**：专用的 repository Plugin 分发路径——`.dsh-plugin` 清单、生成的 wrapper、
准备用可执行文件、第二套 Git/包缓存、一个 Loader 内建、repository 专用的 Skill 与 MCP 适配器，
以及被 vendor 进来的 `@cordisjs/plugin-loader/repository` 子路径与它捆绑的 pnpm 依赖。

**判据**（:9-11）：它**复制了 profile bundle 路径**；
而且**这条重复路径暴露的配置比 bundle 还少**——
`repositories` 列表只能选源字符串，生成的 wrapper 挂的是一个**没有用户提供 Plugin 配置**的代码入口。
「于是 repository 专用的准备工作增加了大量代码与 CI 工作，
**却没有成为通用的外部 Plugin 分发机制**。」

**旧数据的处置写得很干净**（:17）：现存的 repository 缓存目录**是惰性的用户数据；
DSH 既不读也不删**。
→ **删除一条路径 ≠ 有权删用户磁盘上的东西。**

**「合并被删决策的动机」这一手法又出现了**（:21）：本篇收纳了被删掉的
「repository 缓存 / 静态格式 / 仅配置集成 / npm 支撑的准备 / 受信任代码入口」五份决策，
并明写「**它们最初的动机在这里存活下来**：
独立用户需要包管理器拥有的外部组合；Git 与 npm 依赖可以执行受信任的生命周期代码；
静态 Skill 与 MCP 贡献应当复用它们已有的所有者；源身份属于 profile 依赖声明与 lockfile。
**它们那些实现专有的 wrapper、缓存代次与准备协议不再约束产品。**」
→ **动机与实现分开继承**，这是本项目在归档 `openspec/changes/` 时可以直接抄的做法。

**备选（四条）**（:25-31）：
① 保留 repository plugin 作为 bundle 之上的便利包装——否，
「会保住两条安装命令、两种清单格式、**以及同一个包的两种失败/缓存身份**」；
② 教 repository wrapper 去加载 bundle patch——否，缓存与准备协议仍在复制 profile 依赖安装；
③ **为可能的未来消费者保留通用 Loader repository 缓存**——否，
包删掉之后它没有当前消费者，且**在一个贴近浏览器的 vendored 包里钉着一个包管理器运行时**；
「只有当**『配置期激活而无需显式安装』**成为 profile 依赖满足不了的产品需求时，
专用缓存才重新有正当性；**到那时那个消费者可以选择它自己的缓存契约**。」
④ 禁用 repository plugin 但保留磁盘格式用于迁移——否，
「保留一个解析器或兼容加载器会让**已删除的契约继续活着，而外部并没有兼容义务**。」

**测试段有一句「具名的覆盖缺口」**（:44）：
「声明式的、包相对的 Skill 与 MCP bundle 资源，在这一层移除里**仍是一个具名的覆盖缺口**。」
→ **缺口有名字**，而不是消失在字里行间。

## S-38 `2026-08-10-default-presets-single-editor.md`（25 行）

**删了什么**：`standard` / `code` / `cordis` 三个通用 preset 里的 `str_replace_editor` 工具挂载。

**判据**（:9）：它与 `read`/`write`/`edit` 在普通文件查看与编辑上**重叠**，
「所以每个请求都多带一份工具 schema，**却没有增加一个不同的默认能力**」。
→ **判据是「模型可见面的重叠」，不是「代码重复」。**
每多一个 schema 就是每个请求都要付的 token 与选择成本。

**没有一刀切**（:13）：`minimal` preset 的组合契约不同——
它那份精确的两工具花名册**有意包含 `str_replace_editor`**，所以保留；
部署或用户自写的 preset 仍可显式挂载。
**这次收窄的是 preset 花名册，不是删掉工具包或它的 Python 运行时支持。**

**备选（两条）**（:19-21）：两边都保留（否，重叠 schema 增加选择而不提供独立的默认操作）/
从每一个发布组合里删掉（否，`minimal` 有意暴露它）。

**验证**（:25）：preset 组合测试**同时钉住它在 standard/Cordis/Code Mode SDK 里的缺席
与它在 minimal 里的存在**。

## S-39 `2026-08-10-source-run-without-managed-installer.md`（31 行）

**删了什么**：仓库自有的源码安装器、它的测试套件，以及那些假定存在
「受管 `current` 符号链接 + 带时间戳的 staging worktree」的 skill。

**判据**（:9-11）：一个仓库自有的源码安装器确实能提供稳定启动器、隔离的 staging worktree、
原子升级、回滚存储与共享维护流程；**但它让仓库在包管理器之外多背一条生命周期**——
宿主依赖安装、凭据提示、checkout 收养、符号链接所有权、staging 分支协调、升级恢复，
以及**安装器与随包发布的维护 skill 之间的持续兼容**。
「那条生命周期**不是从源码 checkout 运行或开发本项目所必需的**。」

**备选（三条）**（:21-25）：
① 保留安装器同时把 `pnpm run` 文档化为另一条路——否，**两套生命周期契约都还活着**；
② 保留通用的定制与上游发布 skill——否（**判据值得抄**）：
「它们的安全规则可以超出 staging 布局适用，但**这些随包发布的工作流构成一个耦合的维护系统**：
定制去发现已安装的 staging checkout，升级执行切换，上游发布从那些个人改动里挑选。
通用的 Git 贡献指引本来就属于仓库指令，**不需要以产品内置 skill 的形式存在**。」
③ 用一个更小的启动器链接脚本替代——否，仍然让仓库负责宿主 PATH 变更与启动器所有权。

**重新引入的门槛写得很具体**（:29）：未来的分发机制必须
**为自己拥有安装与升级状态给出理由、定义恢复行为、加测试与用户文档，
并且不能让源码运行路径依赖它**。

## S-40 `2026-08-10-web-remove-steering-interjection-caption.md`（36 行）

**删了什么**：每个 steering 气泡上方的 `插话` / `Interjection` 标题行、
`message.steering` 文案键、`.steeringMark` 样式、`UserStyleBubble` 的 steering 标志。

**判据**（:9）：**那行文字重复了流程本身已经显示的东西**——
steering 气泡按位置就坐在被它打断的 assistant 内容之间，而开启 turn 的 prompt 坐在 turn 边界上。
「一行永久的三级文字**买不到一个懂位置的读者原本就没有的读法**」，
而且它是任何用户样式气泡上**唯一的一处装饰**，破坏了右对齐的统一节奏。

**这一篇最有价值的是它记录了一次「反复横跳」**（:17）：
> The caption **has flipped before**

——归档里的 `2026-07-31-web-ui-no-steer-entry-or-interjection-chrome` 在 composer 还不能 steer 时删过它；
`2026-08-04` 在 composer 拿到 Steer 手势后**又把它加回来**；本篇**再删一次**。
并且明确划定本次的范围：「本次移除**不重新讨论那个手势**——
steering 入口、Queue dock 的 steer-send 动作、pending 生命周期都保留各自的所有者；
**它只判断：transcript 不需要给结果命名。**」
→ **一个决策被反复推翻不是丑事，把每次翻转的触发条件写下来才是记录的价值。**

**运行时区分被明确保留**（:15）：`SteeringMessageNode` 从持久 `agent/inbox/spliced` 历史的投影、
`data-pending-steering` 属性、pending→durable 交接**全部保留**——
「pending 生命周期**不管呈现如何都需要这个节点身份**，测试也仍然靠该属性定位 pending 气泡」。
→ **删呈现不删事实**（与 S-02 / S-12 同一手法）。

**备选（三条）**（:21-25），第三条尤其精准：
「**用更安静的装饰来区分（着色、缩进、只在 hover 时出现的标签）**」——否，
「任何替代品都会用一套更弱的词汇**重新提出同一个问题**。
transcript 需要的区分是位置性的、而且已经可见；
加更微妙的装饰**保住了成本，却丢掉了文字标题唯一的优点——它是显式的**。」

**后果诚实**（:34）：重放的 transcript 不再给 steering 命名，
读者要从位置推断；「**这个推断对于快速扫 turn 边界的读者来说弱于一个显式标签；本决策接受这一点。**」

## S-41 `2026-08-11-cmdline-program-action.md`（29 行）

**删了什么**：`dsh-cmdline` 里自制的 `CmdlinePlan<T> = (program, ctx) => T` 回调、
它的 `ctx` 参数（**没有任何 plan 读过它**）、类型不安全的默认实现 `(() => ({}) as T)`
（**只有测试用过**）、以及 `T | undefined` 返回值。

**判据**（:9）：整个接缝**复制了 commander 已经定义的一个槽位**——
命令的 action handler 就在 `parse` 内部运行，从它抛出的 `program.error(...)`
**和语法拒绝一样遵守 `exitOverride`**。

**本篇对本项目最有价值的是那个「加载期守卫」的理由**（:13）：
因为 `Command` 类型无法表达「必须有 action」这个前置条件，
`parseCmdline` **结构化地读取 handler**，并在**加载时就拒绝**一个「没有任何命令声明 action」的 program。
没有这个守卫会怎样：

> a provider that forgot its action (or a stale caller still passing the deleted third argument)
> **parses successfully, publishes nothing, and surfaces only as dependent rows
> pending on the absent service at settlement.**

——**解析成功、什么也不发布，最后只以「依赖行在落定时挂起等待一个不存在的服务」的形式浮现。**
这是「静默失败 + 症状离原因很远」的标准形状。

**而对应的备选被否掉的理由，是本轮全部 121 篇里最该抄进本项目的一句**（:22）：
> **Accepting an action-less program and relying on the settlement diagnostic**:
> the assembled launcher does fail loud (`pending (waiting for service: …)`),
> but **that error names the consumers, not the misconfigured provider**,
> and an embedding host without the settlement assertion would hang silently;
> the load-time guard **reports the culprit program directly.**

——**装配后的启动器确实是 fail loud 的，但那个错误点名的是消费者，不是配错的提供者。**
→ **「有报错」不等于「报对了」。** 报错必须指向责任方，否则排查成本仍然在。

**另外两条真实的框架坑**（:13 + :29）：
- commander **只在注册时**把 `exitOverride` 与输出设置拷进子命令，
  所以「只在根上覆盖」会让一个**预先注册过的子命令**的拒绝直接调 `process.exit`，
  **绕过 `ctx.appExit`**。修法是对整棵命令树配置，而不只是根。
- **action 必须是同步的**：helper 调的是 `parse` 而不是 `parseAsync`，
  「所以一个被返回的 promise **会逃出 catch 且无人观察**」。

**「上线前在 commander 15 上验证过」被写进正文**（:15）：
action 在 `parse` 内运行且其 `program.error(...)` 经 `exitOverride` 抛出 `CommanderError`；
help 与 version 在 action 之前短路；有无 action 时多余参数的处理一致。
→ **对第三方库行为的假设，被当成需要实测的断言写下来**，而不是当常识。

**备选（五条）**（:19-23），另一条也值得：
「**返回解析好的 `Command` 让调用者自己读**」——否，
「调用者在解析后调 `program.error(...)` 会**作为未捕获的 `CommanderError` 逃出 helper 的 catch，
把一次用法拒绝变成一次插件加载失败**」。

## S-42 `2026-08-11-quickstart-documentation-home.md`（31 行）

**删了什么**：独立的文档站落地页。每个 locale 根变成重定向页（`/` → `./guide/quickstart`）。

**判据**（:9）：它**复制了产品落地页拥有的定位与特性摘要**；
「那些平行的说法需要同步与评审，**却不帮助读者到达技术说明**」。

**一个很小但很典型的实现判据**（:13 + :27）：重定向目标用**相对路径**，
「以便站点被托管在某个 origin 路径之下时仍保留配置的 `DOCS_BASE`」；
备选里「用 origin 绝对路径」被明确否掉——`/guide/quickstart` **会忽略 `DOCS_BASE` 并在子路径部署下失效**。

**备选（四条）**（:21-27）：保留文档 hero 并同步措辞（否，**第二套产品叙事会漂**）/
在根渲染文档索引（否，重复导航并在第一份可执行指南之前插入又一次选择）/
把 quickstart 内容复制到每个 locale 根（否，两条公共路由拥有同一份教程，**又需要一套同步机制**）/
origin 绝对重定向（否，见上）。

**验证**（:15）：**projector 测试验证两个 locale 根使用同一个 locale 相对的 quickstart 目标。**

## S-43 `2026-08-11-remove-empty-experimental-package-group.md`（36 行）

**删了什么**：为原型与内部插件保留、**但从来没有任何包用过**的 `packages/experimental/` 分组，
以及随之而来的放置、依赖、晋升与发布规则。

**判据**（:9-11）：「空分组在**没有当前包、也没有需要这些规则的发布机制**的情况下，
增加了放置、依赖、晋升与发布规则。」
最初的动机（让团队在真实插件图上共享原型而不暗示产品支持）**仍然可能成立，
但它不足以在具体包出现之前正当化一个永久的仓库分类。**

**备选（五条）**（:23-31），三条对本项目直接有用：
- 保留空分组——否，「它提供了一个显然的未来孵化位置，
  但也**保留了一批没有当前所有者、没有包、也没有强制机制的仓库规则**」；
- 把实验规则挪进通用包指令——否，「这**让每一次包改动都背上一个假想包类别的规则**」；
- **把具体的实验包放进产品角色分组，只用 README 标签区分**——否，
  「**标签本身无法强制发布与运行时依赖规则**」；但明写「未来的包可以拿它自己的发布机制来重估这个选项」。

**重新引入的条件**（:36）：第一个真正需要实验/内部待遇的包，
必须定义**它住在哪、发布如何排除它、允许哪些运行时依赖、什么条件晋升或移除它**。
「专用分组可以在这些规则**有了当前消费者与可强制的机制**之后回来。」

## S-44 `2026-08-11-remove-sdk-project-toolchain.md`（41 行）

**删了什么**：整条 SDK 项目工具链——`@deepseek-ai/create-sdk`、`dsh-scripts`、`dsh-helper`、
`dsh-telemetry` 四个包及其二进制、测试、模板、特性目录、项目编辑模型、包管理器支持、
启动器遥测与仓库创建 skill，**没有替代品也没有兼容层**。

**判据**（:11）：**没有任何项目是通过公开发行版创建的，也没有任何当前的仓库内或外部消费者需要那条生命周期。**
保留它意味着维护四个包、两个交互式命令产品、项目模板、包管理器适配器、配置协调、启动器遥测、
一个仓库 skill 及其测试与文档，
> **without evidence that the product boundary should exist.**
（**在没有证据表明这个产品边界应当存在的情况下。**）

**保留部分的边界被精确切开**（:13 + :19）：同一个 `scaffold/` 分组里还有
**独立被使用的** SDK 协议、TypeScript 客户端与 JSON-RPC server——
它们服务于 Python SDK、`dsh-sdk` 子 agent provider 与 JSON-RPC 示例，
「**它们的运行时协议不依赖生成的项目或被删掉的启动器**」，
于是**原封不动地从 `packages/scaffold/` 移到 `packages/sdk/`**，npm 名字与线路行为不变。

**被取消的提案怎么处置**（:21）：那些被取消的 proposal
**被删除，而不是保留成 active 或 rejected 记录**；
本篇「保存了它们共享的动机、不发布该产品的决定、**被放弃的能力**，以及重新考虑的条件」。
「冻结的归档 Agent Note 仍是历史快照，不被编辑。」
→ **删除提案时把「放弃了什么能力」写下来**，这是本项目 `openspec/changes/` 归档时的对照物。

**备选（四条）**（:29-35）：只删初始化器（否，其余三个包正是为了运营初始化器创建的项目而存在）/
保留只报错的包或命令别名（否，**没有任何命令公开发布过，墓碑只会保住包与可执行面而没有兼容义务**）/
把运行时 SDK 栈也删掉（否，有三个当前消费者）/
把运行时栈留在 `packages/scaffold/`（否，**那个分组里已经没有任何东西在 scaffold 项目了**；
`packages/sdk/` 直接陈述幸存下来的角色，因为 `SDK` 在本仓库只有一个含义）。

## S-45 `2026-08-12-separate-source-launch-from-build.md`（38 行）

**删了什么**：把「源码启动」与「仓库构建」绑在同一个包脚本里的做法。
根 `dsh` 脚本只跑 `node --import tsx/esm apps/cli/src/bin.ts`；`pnpm run build` 是独立操作。

**判据**（:9-11）：TypeScript 源码启动器**不需要每次调用都做一次完整仓库构建**，
而 Web 面**确实需要**已构建的前端与客户端插件产物；
让一个脚本同时拥有两件事，会给反复的 TUI/headless/Web 启动加上仓库级构建延迟，
并**模糊「浏览器产物什么时候被刷新」**。
第二条判据：经 tsx 到达的源模块与经构建产物到达的浏览器模块**有不同的新鲜度行为**，
把命令分开「**要求显式地拥有产物生产，并对缺失与陈旧的输出给出准确的失败模型**」。

**这一篇最值得本项目注意的是：它明确接受了一处静默行为，并把它写进文档**（:17 + :32）：
> The launcher **does not validate artifact freshness**: existing stale frontend or client-plugin
> bundles are accepted and **can run older browser code until the next build.**
> …existing stale frontend and client-plugin bundles **can silently serve older browser code.**

——启动器**不校验产物新鲜度**；已存在但陈旧的包会被接受，**可以静默地提供旧的浏览器代码**。
但注意配套（:34）：「根 onboarding 与 CLI 参考把构建与启动展示为两条命令，
**并把陈旧产物行为写进文档**。」
→ 与本轮其他篇合起来给出的规则是：
**静默行为本身不是罪，「静默且未被写下来」才是。**
（对照 S-07「静默丢弃是唯一没有辩护者的状态」——那里没有文档、没有 warn、也没有拒绝。）

**失败模型分了层**（:17）：缺失的 Typert 宿主产物**通过模块解析错误让 profile 启动失败，
且不给构建提示**；宿主产物存在之后，缺失的前端与客户端插件产物
**在启动时以「指向 `pnpm run build`」的诊断失败**。

**备选（三条）**（:23-27）：
① 每次源码启动前都构建——否，「给每次调用都收一次仓库级产物生成的费用」；
② **只在产物缺失时构建**——否（判据很准）：
「它避开了一些启动开销，但**让陈旧输出不被检测到，同时让构建行为变成隐式的、依赖当前文件系统内容的**」；
③ 从 `pnpm dsh` 启动 Web 产物 watcher——否，那把一次性启动器变成另一个长生命周期进程的所有者。

## S-46 `2026-08-13-remove-first-run-beta-notice.md`（25 行）

**删了什么**：GUI 首次启动的全视口内测声明（内测框架 + 通过 `DSH_TELEMETRY_MODE`
开启 Session Log 上传的说明）、通知组件、确认存储、文案所有者与 locale 键。

**判据**（:9）：会话遥测在模式未设置时**已经解析为 `DISABLED`**，
「所以关于遥测的唯一 onboarding 内容，是一份**教你怎么把它打开**的提示」；
而且「内测框架本身**不能出现在发行构建里**」。
→ **判据是「默认已经是安全的，那么这段文案唯一的作用就是劝人关掉安全默认」。**

**备选（三条）**（:17-21）：
① 保留通知只删遥测段落——否，「内测框架正是发行版不能呈现的东西，
而**一个没有任何实质陈述的强制首启插页就是纯粹的摩擦**」；
② **改成征求上传同意（一个带版本的同意步骤）**——本次发行版否决：
「首启时问是否开启上传**仍然是一次遥测提示**。
未来的同意流程可以通过**未改动的 `settings.onboarding` 接缝**注册，并用一个新的带版本字段重新确认。」
→ **删掉实现但保留接缝**，这是「留后路」的正确形态。
③ **顺手把 `ui-onboarding` 命名空间也注销**——否（**很实用的一条**）：
「现有的设置文档已经带着这个 section，而**设置接缝会拿已存储文档去校验已注册的命名空间**；
保留注册**能让那些文档保持有效，且不花任何代价**。」
→ **删代码时，别顺手让磁盘上已有的数据变成非法。**

**后来的恢复被写进同一篇**（:13 + :25）：后来的 shared-modal onboarding
在 `ui-settings-models` 里**恢复了一个新的、简洁的测试阶段声明**，
复用同一个字段与后端契约，**但没有恢复被删掉的接管式布局与遥测说明**；
「历史上那段遥测提示**仍然缺席**。」

---

# §B `implemented/bug-fix`（76 篇，本轮读 75 篇全文）

每条格式：`B-nn 篇名（行数）` → **症状** / **是不是静默** / **根因** / **修法与测试** / **对本项目**。
「静默」在本文的定义（与本项目主线一致）：**不报错、不抛异常、结果看起来正常**。
每条都标了 `静默：是/否/部分`。

> `2026-08-09-filesystem-absence-observation.md` 已在 survey §3 组 C-2 全文读过，本轮不重读，不在下面编号内。

## B-01 `2026-07-19-windows-atomic-write-dacl-preservation.md`（31 行）

**症状**：Windows 上的原子写（temp + rename）**会把目标文件原本更严格的 DACL 换成父目录的宽 DACL**。
**静默：是。** 写成功、rename 成功、文件内容对，只有访问控制被悄悄放宽了。

**根因**（:9）：POSIX 靠 `0o700`/`0o600` 保护 staging，
但 **Windows 的 mode bit 只暴露真实 DACL 的一个合成只读视图**；
在父目录下建 staging 并依赖继承，**对新文件够用，对替换一个 DACL 比父目录更窄的已有文件不够用**——
内容是在更宽的父 DACL 下写的，rename 又把 staging 的安全描述符带到了替换后的文件上。

**修法**（:13）：`GetFileSecurityW` 读出目标已有 DACL → **在写内容之前**把它应用到空 temp 文件上
并**保护继承** → 用 `ReplaceFileW` 发布。
并明写一条实现约束：`ReplaceFileW` 的 ACL 合并**可能重新序列化自动继承状态或复制等价的 ACE**，
所以「**自相对描述符的字节缓冲不是一个稳定的相等性契约**」——
测试要比较的是**有序、去重后的 ACE 策略**，不是字节。

**备选（五条）**（:19-27）里两条值得记：
- **每次写都装一个 owner-only DACL**——否，「那会丢弃刻意设置的项目共享。
  **复制目标的 DACL 是保留部署已有的访问策略，而不是发明一个。**」
- **用 `Get-Acl` / `icacls` 断言继承来的账户**——否，
  「那种测试**验证的是机器策略而不是包行为**，而且本地化的知名账户名让输出在不同宿主间不稳定。」

**对本项目**：这条给「测试该断言什么」提供了一个判据——
**断言语义等价物（有序去重后的策略），不断言字节；断言包行为，不断言宿主策略。**

## B-02 `2026-07-20-config-hot-reload-resilience.md`（44 行）

**症状**：一次无效的 `cordis.yml` 编辑不能杀死运行中的 agent；
但**「进程活着」还不够**——一次看起来有效的更新可能**先替换掉 Loader 树的一部分，
然后在更靠后的条目上失败**。
**静默：部分。** 进程不死，但树处于半新半旧的状态，调用者又无法把「活更新被拒」
与「未处理的启动失败」区分开。

**修法（这是本轮最完整的一个「补偿事务」记录）**（:17）：
Loader **在销毁活 fiber 之前先 import 变更后的模块名**；候选的应用是 await 的；
失败则销毁候选副作用并恢复先前的插件或配置；
分组协调并发启动候选、**等待每一个结果**，在拒绝之前恢复变更、新增、移除与移动。
**持久化只在程序化变更成功之后才发生。**
并且明写它是什么、不是什么：
> This is **a compensating transaction**: lifecycle effects may be briefly visible,
> and **a failed rollback is reported as an `AggregateError` rather than misrepresented as a retained tree.**

——**回滚失败被如实报成 `AggregateError`，而不是谎称树还是原来那棵。**

**一条「落定的语义」被写死**（:35）：
> Fibers waiting on declared dependencies remain valid pending entries:
> **lifecycle settlement means no current work failed, not that every dependency exists.**
——**「落定」只意味着当前没有工作失败，不意味着每个依赖都存在。**
→ 直接对应本项目：**「跑完了」不等于「都齐了」**，两种状态必须分开命名。

**备选（三条）**（:25-29），第三条最该抄：
- **承诺「不可见的原子替换」**——否：
  「**任意插件的副作用无法被快照。** await 的应用加显式补偿给出一个稳定的最终结果，
  **而不声称观察者看不到中间的生命周期转换。**」
  → **不承诺做不到的原子性**，而是承诺「最终态确定 + 中间态可见」。

**测试段列了两份真实的 spec 文件与它们覆盖的十几种失败**（:41-43），
包括解析拒绝、形状拒绝、import-before-dispose、插件/配置恢复、多条目回滚、
祖先禁用、overlay 收敛、失败的直接更新持久化、失败的程序化移动。

## B-03 `2026-07-20-error-cause-chain-diagnostics.md`（37 行）

**症状**（:9）：TUI 打一个不可达的 DeepSeek 端点，**唯一的提示是 `fetch failed`**，没有任何细节。
**静默：部分。** 有错，但错得毫无信息量——这是「留痕存在但无用」的形态。

**两个独立的缺口**（:11-12）：
① undici 的 `fetch` **把每一种传输失败（DNS、拒绝连接、TLS、代理）都包成一个裸的
`TypeError: fetch failed`**，可执行的细节（`ECONNREFUSED`、`bad port`、Happy Eyeballs 的 AggregateError）
**活在 `error.cause` 上**；而 harness 里**每一个诊断边界都只渲染 `error.message`**
（或 `String(error)`，对 Error 而言等价），于是包装器**同时遮蔽了 TUI 提示、持久的 `turn/end` 原因、
以及每一行日志**里的诊断。
② readline 入口**对失败原因什么都不渲染**——
`turn/end` 的 `reason.kind === 'error'` **只打印了下一个 `> ` 提示符**，
「所以同样的失败在 `demo:repl` 里是纯粹的沉默」。

**修法**（:16-19）：新增 `errorChain(value)`（渲染完整 `cause` 链 `outer: inner: …` 与
AggregateError 成员 `msg [m1; m2]`，含**循环 cause 与恶意强转的防护**），
**它只是诊断输出渲染器，路由仍然走 `HarnessError.code`**；
adapter 把响应前的传输失败包成 `LlmError('TRANSPORT')` 并把原始拒绝链在 `cause` 上；
**每一个诊断边界都改用 `errorChain`**；三个包里近乎相同的私有 `renderThrown` 副本被删除，合并成一个。

**备选（三条）**（:25-29），三条都是本项目会踩的：
- **在每个 error 的构造器里把 cause 烤进 `message`**——否：
  「一旦消费者也去走 `cause`，就会**双重渲染**（第一版 adapter 修复真的产生了
  `… fetch failed: bad port: fetch failed: bad port`），
  **而且它摧毁了那些想按内层错误路由的消费者所需的结构化链。**」
- **只做一个 cause 感知的 logger exporter**——否：
  「持久的 `turn/end` 原因与 TUI 提示**不是日志行**；
  被遮蔽的消息会**继续留在会话日志——那是一次 turn 内失败的唯一持久记录——以及主界面里**。」
  → **这一条直接就是 D-003 的论证方式：证据链上的失败信息不能只修日志。**
- 每个包各自升级 `renderThrown`——否，那是在巩固要被消掉的重复。

**后果里诚实记了一个损失**（:35）：`errorChain` 渲染 `message` 时**不带类名**
（`String(error)` 会渲染 `Error: <message>`），
所以日志里一个裸 `TypeError` **会失去它的类型标签**，除非 message 为空（那时用 name 兜底）。
「在这些诊断边界上，链的细节被判定为比类名更值钱。」
→ **取舍被写下来，而不是假装没有代价。**

**还留了一份「尚未覆盖」的清单**（:37）：`dsh-subagent`、`dsh-workflow`、`dsh-skill`、
`dsh-workflow-worker-thread` 里剩下的 `renderThrown` 副本**仍然不渲染链**，
理由是它们包装的是自带 message 的包内错误，「**等它们的诊断被证明不够用时再采用**」。

## B-04 `2026-07-20-jsonl-storage-identity.md`（29 行）

**症状**（:9）：JSONL 的查找是**跨项目目录**按会话 id 选一个物理日志，
而后续的修复与追加用的是**解析出来的 `SessionHeader`**。
两者不绑定时，**为会话 A 选中的日志可以声明会话 B 的 id 或 cwd，
把一次修复或后续追加重定向到 B 的路径上**。
**静默：是。** 写会成功，只是写到了别人的会话里。

**根因的对照很有价值**（:9）：「SQLite **不共享这个歧义**，
因为它的主键查询把元数据与事件绑定到了被请求的那个 id 上。」
→ **同一个逻辑契约，两个后端的安全性不同**，差别来自「身份是否由查询本身绑定」。

**修法**（:13-15）：`loadStored(id)` 是协调器**唯一**的存储前缀查找；
JSONL 后端扫描每个项目目录，**要求至多一个匹配的编码会话目录且带 transcript**，
解析后**校验 `header.id === id`**，并校验选中路径等于 `logPath(root, header.cwd, header.id)`
或经文件系统规范化后两种拼法解析到同一个 transcript；
`list()` 用同样的路径校验，并**拒绝跨项目目录的重复 id**。
协调器**再独立断言一次**返回的 id，并**在修复、状态发布或后缀持久化之前**比对存储的 cwd 与活会话的 cwd。

→ **两次独立断言（后端一次、协调器一次）**，与 S-32 的「两道检查是故意的」同型。

**备选（三条）**（:21-25）：按 id 扁平化存储（否，路径校验与重复拒绝已经封住缺陷，
不需要让检查依赖一个扁平全局命名空间）/
在协调器里传一个不透明的存储定位符（否，**会让每个实现都背上只有文件后端需要的概念**）/
协调多个活写者（否，那是在定义一个新的部署拓扑，而不是修复身份校验）。

**能力上限被明写**（:17 + :29）：后端**只支持每会话一个活写者**；
「另一个后端实例或进程**不得**在所有者完成销毁且所有写入停止之前变更该会话。」
「一个活写者的所有权仍然是一条显式的限制。」

## B-05 `2026-07-21-compaction-summary-prefix-cache-reuse.md`（45 行）

**症状**（:9）：自动压缩恰好在「loop 刚用最后一次路由请求（`system` + `tools` + 派生历史）
把 provider 的 KV cache 焐热」之后触发；
但默认摘要器发的是**一个前缀与那次热请求毫无共享的独立辅助请求**
（自制的摘要器 `system` prompt + 把旧历史压平成一个渲染好的 transcript 字符串）。
**provider 是按请求的前导 token 序列缓存的，所以第一个 token 一变（不同的 system prompt），
整个缓存前缀作废。**
**静默：是**（性能型静默）——功能完全正常，只是**每次压缩都把整段历史的 prompt 处理费付了两遍，
而且恰恰是在对话最长的时候**。

**修法**（:13）：把摘要指令**从请求的前面（一个新 `system`）挪到对话的末尾（最后一条 `user` 消息）**，
辅助调用**逐字复现最后一次路由请求的前缀**再追加一条指令，
于是它是那次热请求的**真前缀扩展**。
`SummarizationInput` 变成 `{ system?, tools?, messages }`，
由 `session.requestHeader()`（持久的 system 与 tools）加上经 `session.deriveEventMessage` 映射的
影子区间构建，**产出与 `deriveMessages()` 折进路由请求的 `Message` 对象逐字节相同**。
**`tools` 也要带上，尽管摘要器从不调用工具**——
「丢掉它们会缩短 token 序列并破坏与缓存请求的对齐」（:17）。

**「缓存复用是尽力而为，正确性不是」**（:23-25，标题就是这句）：
自动压缩总是锚在 surface 头部，所以影子区间就是路由请求的头部，**属于保证命中的情形**；
手动的中段 `compactRegion` **仍然复现真前缀并保持正确，但放弃复用**；
配置了不同 `summarizationProvider`/`Model` 的部署也放弃复用，
「**那是该部署显式的取舍，不是缺陷**」。
→ **把「保证」与「尽力而为」逐场景分类写清楚**，这正是本项目在证据链性能优化上要抄的做法。

**备选（四条）**（:29-32）四条全是「为什么不能只改一半」，其中：
「**只把 `system` 换掉但复用其余**」——否，「system 槽正是 provider 缓存所依赖的最前面那段 token 区域」；
「**省掉 `tools`**」——否，「工具 schema 是缓存 token 序列的一部分，
**省掉它们会让后面每一个 token 错位**」。

**顺手删掉的死面**（:37）：旧的压平路径 `renderTranscript` / `renderContentBlocks`
及其 spec「**没有剩余消费者**」，随之删除。

## B-06 `2026-07-21-semantic-session-checkpoints.md`（29 行）

**症状**（:9）：持久化把每个同步 `session/event` **缓冲到 loop 的最终 turn 检查点**。
turn 是正确的会话事务，但**作为唯一的崩溃恢复点太粗**——
一次在长模型请求或工具调用中的硬崩溃**会丢掉整个进行中的 turn，
包括「用来识别曾经尝试过什么」的请求信封**。
而且**一个有 call 无 result 的工具调用被用一个不加区分的中断错误修复**，
于是「恢复后的模型无法判断执行是否已经开始，**可能盲目重试一次有副作用的操作**」。
**静默：是**（在恢复侧）——恢复后的历史看起来完整，只是**语义被抹平了**。

**修法**（:13）：`dsh-session-checkpoint-policy` 作为**零配置插件**拥有语义化的持久屏障：
在 `agent/pre-step` 冲刷待处理的 prompt 输入或上一批响应/结果；
懒包装 `llm/stream`，**在 `request/header` 被记录之后、adapter 流被构造之前**冲刷；
包装顶层 `tools/execute`，**在工具体执行之前冲刷已记录的 `tool/call`**。

**fail-closed 被放在副作用边界上**（:17，与本项目 D-018 同型）：
- 被拒绝的**请求**检查点**阻止 adapter 分派**；
- 被拒绝的**工具**检查点**变成一个错误结果，且不调用工具体**；
- 如果取消在工具检查点挂起期间落地，策略**重新检查信号**并返回规范的 `ABORTED_BEFORE_DISPATCH`；
- 被拒绝的**步间**检查点在下一次模型请求之前关闭 turn；
- 被拒绝的**最终 turn** 检查点**实时上报，但不阻止后续排队工作**。

**崩溃修复区分持久证据（本篇对本项目最有价值的一段）**（:21）：
- assistant 发了工具请求但**没有 `tool/call`** → `TOOL_NOT_STARTED`，**仍需要就可以重试**；
- **有持久 `tool/call` 但没有结果** → `TOOL_OUTCOME_UNKNOWN`，
  其**模型可见的结果只允许对只读或幂等操作重试**，
  并**指示模型在决定有副作用的工作之前去核实外部状态或询问用户**；
- 支持幂等键的 provider 可以拿到稳定的 `callId`，
  但「**Harness 不声称通用的 exactly-once 效果**」。
→ **三态而不是两态：没开始 / 结果未知 / 已完成。** 「未知」被当成一等状态，不被折叠成「失败」。

**一个真实的生命周期竞态**（:19）：Cordis **并发**卸载兄弟插件的副作用，
所以独立挂载会让**持久化在 bridge 拆解还在关闭一个被中断的 turn 时就先分离**。
修法是把 bridge、检查点策略、持久化后端放进**一个有序的 Cordis effect**：
先卸 bridge，等它的 agent 静默并冲刷真实的 `step/end` 与 `turn/end`，再移除检查点调度与持久化。

**测试**（:29）：单测覆盖顺序、检查点期间的取消、fail-closed、嵌套分派、销毁、Loader 形状、
最终检查点顺序与失败containment；
**一个被 `SIGKILL` 杀掉的真实子进程**证明请求与工具意图能通过 JSONL 恢复；
而且崩溃 harness **等待预期的 marker 内容而不是路径存在**，
「**这样『先 open 后 write』的可见性就不会让 kill 提前触发**」。
→ 一条很实用的测试反模式警告：**用「文件存在」当同步点会让竞态测试自己变成假的。**

## B-07 `2026-07-22-pi-ai-transport-truncation-classification.md`（35 行）

**症状**（:9）：模型连接中途断掉，界面上只有 `terminated`；
被截断的 Anthropic 响应只有 `Anthropic stream ended before message_stop`。
两者都是传输截断，但 `classifyPiAiError` **两个都没映射**，落到 catch-all `PI_AI_ERROR`；
而 `PI_AI_ERROR` 不在 `llm-retry` 的默认可重试集合里，
**于是一个可恢复的断流被当成永久失败，从来不重试。**
**静默：部分。** 有错误信息，但**分类错误导致恢复机制不被触发**。

**根因不在自己家**（:11）：pi-ai **在推送终态 `error` 事件之前，
把捕获到的错误缩成 `error.message`**（原文给出了上游文件与那行代码的形状），
**丢掉了原始 `Error` 与它的 `cause` 链**；undici 把可执行的 `SocketError` 挂在 `cause` 上，
却只把一个裸的 `terminated` 交给 fetch 包装器，pi-ai 只留下那一个词。
且 pi-ai 的 `SimpleStreamOptions` **没有暴露任何 fetch/dispatcher/client 钩子**
能让他们在压平之前自己捕获 `cause`。

**修法（明确标为 workaround）**（:15-21）：识别两类措辞映射到 `TRANSPORT`；
并在分类器里放一条 `XXX(pi-ai upstream)` 注释，**点名压平发生的位置并写明想要的修法**
（如果 pi-ai 哪天转发原始 `Error` 或给出能捕获 `cause` 的钩子，就改按 `code`/`cause` 分类）；
`llm-pi-ai/README.md` 增加一条 Known-Limitations，记录
「pi-ai 压平了 cause 链，因此 harness 的 code 是**从消息文本**分类出来的」。

**残留风险被写在 Consequences 里**（:35，**这正是本项目要学的诚实**）：
> Classification remains string-matching and provider-wording-dependent:
> a future pi-ai release that rewords these errors **would silently fall back to `PI_AI_ERROR`**
> until the patterns are updated.

——**上游改个措辞，它就会静默退回 catch-all。** 他们知道，写下来了，并留了 `XXX` 指向根治方案。

**备选（三条）**（:25-29），第二条最重要：
- **两个都留成 `PI_AI_ERROR`，然后把 `llm-retry` 的可重试集合放宽**——否：
  「`PI_AI_ERROR` 是**真正未分类失败**的 catch-all，其中包含不可重试的
  （畸形的 provider 响应、意外的 SDK bug）。
  **让 catch-all 变成可重试，会去重试那些永远不会成功的失败；
  正确的修法是把可恢复的那一类分出来，而不是把桶搅浑。**」
- 像 DeepSeek adapter 那样包一层 `LlmError('TRANSPORT', { cause })`——**在这里被否**，
  因为 DeepSeek 那边包的是**响应前**的 fetch 拒绝，`cause` 还完好；
  pi-ai 这边**已经是压平的字符串，没有 cause 可链**，包一层「不恢复任何东西」。

## B-08 `2026-07-24-empty-model-response-is-retryable.md`（36 行）

**症状**（:9，**本轮最纯粹的静默 bug**）：provider 偶尔返回一个退化的完成——
**格式良好的流，带终态 `stop`，零个内容块**（无文本、无推理、无工具调用）。
如果 adapter 把它映射成成功的 `{kind:'stop'}`：

> the loop logs an empty `assistant/message` and ends the turn as `completed`.
> **Retry never runs, no failure reaches the caller**, and a driver such as goal-round-driver
> **consumes a round without progress.**

——loop 记下一条空的 assistant 消息、把 turn 标成 `completed`；
**重试从不运行，没有任何失败到达调用者**，而 goal-round-driver 这样的驱动**白白消耗一轮**。
**静默：是。** 全绿，什么都没发生。

**修法**（:15-18）：`dsh-llm` 导出规范码 `EMPTY_RESPONSE`；
两个 adapter 各自在自己的终态判定里把「`stop` + 零内容块」变成 `finish {kind:'error'}`；
**provider 自有的正常重试默认集合包含 `EMPTY_RESPONSE`**，
理由是「**这次尝试没有产生任何持久的东西，所以重复它是安全的**」。

**范围被刻意收窄**（:20）：只对 `stop` 终态检测。
`max-tokens` + 空内容保留原有含义，`tool-calls` 实践中不可能块为空，error/aborted 本来就失败。

**备选（三条）**（:26-30），第三条是本项目做「弃权判据」时的镜子：
- 在 loop 或 `BlockAssembler` 里检测——否，那把 provider 响应的判断搬进了 loop，
  「**adapter 才是线路事实变成 harness 分类的地方**」；
- 在 `llm/stream` waterfall 上做流转换插件——否，为一个「每个 adapter 几行就能陈述的边界事实」加一个包；
- **把「只有空白」或「只有推理」的响应也算空**——**否，判为过度**：
  「那些携带了模型产生的内容，
  **把一个合法（哪怕没用）的响应误分类成传输类失败，有让某些「推理完就停」的模型陷入重试循环的风险**。
  范围恰好是『零个内容块』。」
  → **判据必须落在客观可判定的事实上（块数为零），而不是落在「有没有用」的主观判断上。**

**被接受的代价被写下来**（:35）：一个**真的打算什么都不说**的模型（罕见但可能，比如在工具结果之后）
会被重试，且若持续为空则 turn 失败。
「这个取舍是**刻意接受**的：一条空的 assistant 消息**与 provider 缺陷不可区分**，且对用户没有价值。」

**测试**（:36）：`empty-response-retry` ACP 快照是一个**作者编写的无 key 场景**，
带**确定性的 1ms 零抖动重试 overlay**，钉住产品可见行为：
一条持久的 `llm/retry` 事件、**被丢弃的那次尝试没有 ACP 输出**、恢复后的回复、干净的完成 turn。
→ **重试的「被丢弃尝试」也必须在证据里可见（`llm/retry` 事件），但不能污染输出。**

## B-09 `2026-07-24-recursive-python-sdk-session-notifications.md`（29 行）

**症状**（:9）：Python SDK 把每条 turn 通知的 payload **直接与根会话 id 比较**来过滤。
这**放行了直接子代**（它的 parent id 就是根），
但**拒绝了孙代的生命周期以及每一条后代 `session.event`**。
JSON-RPC server 仍然在发这些通知，**于是它们堆积在低层全局队列上**，
而高层消费者**丢失了嵌套的轨迹关系与完成状态**。
**静默：是。** 没有报错，只是树被截断了，而且队列在悄悄涨。

**修法**（:13-15）：客户端**记录每一条有效的 `subagent.started` 子→父边**，
其他会话通知**沿着这张客户端生命周期内的祖先图走到被请求的根**。
关键的两条防御：
- 后来的 `subagent.finished` **按它自己不可变的 parent id 路由，但绝不改写当前的祖先关系**，
  「**这样一个在子 id 被复用之后才结算的旧 run，就不能顶掉替换它的那个会话**」；
- 只有 `sessionId` 等于被请求根的 `session.event` 才进入 `TurnResult.events` 或最终响应重建，
  「**后代事件因此可观测，但不允许一个子代响应替换根响应**」。
→ **「可观测」与「可参与结论」被分开**——这正是本项目证据链要的区分。

**备选（四条）**（:19-25），第二条是本项目「不要靠配置约束保证正确性」的镜子：
- **把子 agent 限制到一层**——「部署确实可以设 `maxDepth: 1`，
  但**让 SDK 去依赖那条策略，会在合法的递归组合上静默误报**」。

**测试**（:29）：无 key Python 测试覆盖两级委派、根响应隔离、
**树通知不在队列里堆积**、跨订阅的祖先复用、以及**被复用的子 id 且旧 run 乱序结算**。

## B-10 `2026-07-27-glob-sampling.md`（47 行）

**症状（本轮最值得本项目反复读的一条）**（:9）：
> Asked what a workspace contained, **an agent described one subfolder as if it were the whole project.**

工作区有 22 个顶层条目、11,485 个文件；`glob {"pattern":"*"}` 匹配到 10,030 条路径，
**但内联展示的 100 条全部落在同一个刚解压的子树下**，于是模型**从未看见另外 21 个条目**。
**静默：是，而且是最危险的一种**——工具成功、结果正确、模型的结论错。

**根因是三个各自正确的行为组合出来的**（:11，原文措辞值得抄：
「Three individually valid behaviors composed into the false impression」）：
① 不含 `/` 的 glob **在任意深度匹配 basename**，所以 `*` 意味着「树里的每个文件」，
而不是 shell 的当前目录展开；
② ripgrep 的 `--sort=modified` 是**升序**，一个归档恢复出来的旧时间戳把那棵子树排到了最前；
③ 内联页**取了那个顺序的头部，却没有说明它只代表一个高度集中的切片**。
→ **本项目直接对应：抽样口径 + 排序口径 + 截断口径，三者各自合理，合起来就是误导性证据。**

**修法**（:15-17）：
- 结果**没超上限时保持完整**且逐字节按修改时间排序；
- 超上限时由**必须显式配置**的 `sampleOverCapGlobResults` 决定：
  `false` = 保留修改时间头部；`true` = **在完整结果的顶层条目之间做 round-robin 抽样**
  （每个条目先拿到一个名额，用尽的组退出，组内相对顺序稳定，
  分组相对于**实际搜索根**，包括显式 `path`）；
- **抽样模式下页脚明说「这是跨条目抽样而不是修改时间头部」**，
  并在「这个事实能增加信息时」报告它触及了多少个顶层条目；
  顶层条目多于内联名额时，**告诉模型去收窄 `path`**；
- 两种模式下，**只要 spill 成功，完整排序列表都保留在 artifact 里**。
→ **页脚是「证据的元数据」**：这一页是怎么选出来的、代表什么、不代表什么。

**备选（八条，本目录最多）**（:23-37），四条对本项目直接有用：
- **给抽样选择一个默认值**——**否**：
  「没有任何产品级证据能确立其中一种顺序是隐含契约，
  **所以每个组合都必须选一个，配错则在加载时失败。**」
  → **不给默认，逼显式选择，misconfiguration fails at load。** 与 S-21 的 `?? {}` 反转默认正好相反。
- **对所有结果都抽样**——否，「完整结果没有因截断损失任何东西，
  所以修改时间顺序对『按新旧提问』仍然有用。**抽样只在头部不再描述整体时才开始。**」
- **只在偏斜超过阈值时抽样**——否，「没有当前证据支持一个部署级阈值，
  **而且模型无法知道哪一种顺序契约在生效**。现有的 cap 是那个可解释的转换点。」
  → **可解释性优先于自适应**：一个模型能推理的固定规则，胜过一个它无法观测的自适应阈值。
- **加一个模型可见的 `list` 工具**——**在实现评审之后否掉**：
  默认编码组合已经暴露了通用 bash 且模型懂 `ls`；
  「重复的工具会加上永久的 schema/prompt token，外加顺序、分页、符号链接、转义、UI 与快照契约，
  **却没有独立的安全或策略收益**。」

**后果诚实**（:41）：抽样模式的超上限页**不再能从内联路径回答「按新旧」的问题——页脚这么说了**；
抽样**只平衡搜索根下的第一段**，所以更深的热点子树仍可能在某个顶层条目内部占优；
head 模式**保留集中风险，作为一个显式的部署取舍**。

**测试**（:47）：包测试钉住必需配置、两种超上限模式、它们的 prompt 与 schema 描述、
集中与扁平结果、显式根、**组数多于 JavaScript 参数上限**、用尽的组、名额少于组数、工作目录之外的路径；
`fs-glob-sampling` ACP 场景**启真实 Loader/app/local-bash 组合，
对一个确定性的 `rg` 进程 fixture 跑真实搜索插件**，结果**横跨四个顶层条目而不是一个子树的头部**。

## B-11 `2026-07-27-stable-snapshot-refresh-volatiles.md`（35 行）

**症状**（:9）：ACP 快照**比较**时会归一化生成的 UUID、cwd 别名、spill 定位符、
内嵌事件时间与省略字节数，**但 refresh 写回时持久化的是新鲜的原始值**。
于是**一次行为上没有变化的 refresh，仍然会用新的随机值或宿主特有的路径拼写重写 fixture**，
尽管比较契约认为两份日志相等。
**静默：是**（对评审者而言）——diff 一片红，**但没有任何行为变化**，真正的改动被噪声淹没。

**修法**（:15-21）：在 record 或 refresh 写 fixture 之前，
共享的快照支撑把「fixture-ready 的日志」交给**一个结构化的 message-ID 所有者**：
它通过会话包**权威的 surface 类型谓词**识别 surface 载体与 `agent/inbox/spliced` 里的相关排队副本，
**把每条完整消息去掉顶层 `id` 之后做指纹**，记录所有父/子日志里的 ID↔指纹边，
**只在某个 UUID 的 ID 与指纹在新旧两张图里入度都为 1 时才复用它**。
refresh 写回则用 `normalizeSessionLog` 作为易变值的权威：
**归一化等价的叶子保留旧的原始值，归一化后不同的叶子采用新的语义值。**

**冲突时一律保守**（:19 + :33）：
「未能解释的记录不匹配或冲突的映射**会对该日志关闭归一化字符串复用**」；
后果段列出保守清单——未匹配的记录、冲突的字符串映射、长度变了的数组、
**同时含语义变化与易变变化的字符串**、畸形消息、任何 ID 或指纹不唯一的消息图，
**一律用新值，而不是冒险复用错位的数据**。
→ **不确定时不复用**，这是本项目在证据对齐上应有的默认。

**对齐规则被逐条写死**（:21）：对象字段按 key 对齐；
**数组元素只有在所有对应数组长度相同时才对齐，否则新数组胜出**；字符串是原子叶子。

**备选（三条）**（:25-29）：
- **在快照部署里用确定性 UUID 与 spill 文件名**——否，
  「替换掉生产的随机性**会削弱被测的安全形状**，或者要求存储与审批实现里出现只为测试而存在的行为」；
- **提交归一化后的 fixture**——否，「被 token 化的会话日志**就不再是原始重放输入**了」；
- **当整条记录的归一化形式不变时保留整条记录**——否，
  「那会在同一条记录里另一个字段发生语义变化时，churn 掉一个随机字段。
  **叶子级保留让这些决定彼此独立。**」

## B-12 `2026-07-28-load-pre-identity-session-messages.md`（39 行）

**症状**（:9-11）：消息表示从「四种持久事件负载」换成「完整消息值」之后，
已有的 v0 JSONL 与 SQLite 会话仍然是旧形状；
**它们的 header 仍然匹配 `SESSION_FORMAT_VERSION`**，
于是当前形状的校验在 resume 能构造出活 `Session` 之前就把它们拒了。
**静默：否**（是 fail-loud 的），但根因值得记：

> Changing the message representation **without a version bump** made those logs
> **indistinguishable at the header level** from current v0 logs.

——**改了表示却没有 bump 版本号，于是旧日志在 header 层面与新日志无法区分。**
→ 对本项目 D-012（评测集冻结）的直接对照：**格式变了就要能被识别出来，否则校验只能靠猜。**

**修法**（:15-19）：协调器在后端解码之后、当前消息校验之前，**归一化那四种确切的旧负载**，
并赋予**确定性**的导入 id `legacy-message:<session-id>:<event-seq>`；
同一套归一化对 `load` / `inspect` / 无主状态认领活会话 / HMR 前缀收养**都跑**，
「所以前缀比较**比的是活的当前形状种子与同一份归一化后的存储视图**」。
**升级是只读的**：存储记录不变，恢复后的会话只在其后追加当前形状的事件。

**边界写死了**（:17 + :33）：
「**看起来像当前形状但字段缺失或非法的包装不被修复**」；
不支持的事件词表、请求头、版本、surface 关系**保留各自现有的拒绝路径**；
> This is **one explicit same-version import exception, not a general v0 compatibility layer.**
> …**malformed current data continues to fail rather than being guessed into validity.**
——**畸形的当前数据继续失败，而不是被猜成合法。**

**备选（三条）**（:23-27）：按预发布兼容立场直接拒绝（否，会**搁浅真实的一方会话**，
而每个旧字段都能无歧义地映射）/ 原地重写整份存储日志（否，违反 append-only 契约，
且**把一次读兼容修复扩张成一套迁移系统**）/ **每次加载铸造随机 id**（否，
「消息会满足类型形状**但在 inspect、resume、重启与混合追加之间失去稳定身份**」）。

## B-13 `2026-07-28-themed-scrollbars-and-reserved-gutter.md`（84 行，全目录最长，是一份测试设计教材）

**症状**（:9-11）：`design-platform.css` 在两套调色板里声明了四个 `--dsw-alias-scrollbar-*` token，
**而客户端里没有任何规则读过它们**。
> **A defined token with no consumer is not a theme**

于是每个滚动区域画的都是浏览器自己的滚动条，**深色主题下是一条浅色原生滚动条压在深色表面上**。
真正被人看见的症状**在别处**：工作区会话列表里，覆盖式滚动条**画在相对时间戳上面**。
**静默：是。** 没有任何东西失败，token 就是死的。

**这一篇最值得本项目抄的是它的检查设计**（:23-29）：
- **重绑契约（rebinding contract）是「CSS 本身说不出来的那部分」**，
  所以由 `scrollbar-styles.client.spec.ts` **机械地**检查：
  「任何**既滚动又绘制抬升表面**的样式表都必须重绑」，
  于是这篇笔记**不再维护一份完整的表面清单**。
- **为什么必须机械检查**（:25）：`Menu`、`InputBar`、`QuestionComposer`、`TodoPanel`
  **四个表面一开始就被漏掉了**——「这就是为什么每表逐条的重绑契约是被机械检查而不是靠人看的」。
- **一个「检查本身不成立」的教训**（:27，**本轮最该抄进 `rules/failure-modes.md` 的一条**）：
  抬升表面的集合是从**调色板自己的深色抬升阶梯**（深色值落在 `bg-layer-2/3` 的表面 token）解析出来的。
  「**先前第一次尝试是从『已经重绑过的样式表』反推这个集合，那是不成立的**：
  这样的集合**只能确认某人已经记得的东西**，
  而一个还没有人重绑过的表面——**恰恰是这个检查存在的目的**——会把自己定义成『未抬升』。」
  并给了实证：`--dsw-specific-tip` 解析到菜单表面的那一阶，
  而 todo 面板就在它上面滚动且未重绑，**派生出来的检查却一直是绿的**。
  → **从现状派生的覆盖检查，永远查不出「被遗漏的那一类」。**

**几条真实的平台坑**（:17-21）：
- 规则必须在 `body` 而不是 `html` 上——token 声明在 `body`，**自定义属性只向下继承**；
  放 `html` 会让它们解析成「保证无效值」，此时 `scrollbar-color` 计算成 `auto`，**完全不生效**；
- 必须写成 `body, body *` 而不是只写一次靠继承——
  「继承传下去的是**已经在 `body` 上代入过的颜色**，
  于是一个想重绑间接层的后代**改不了自己的滚动条**」；
- 两条渲染路径**互斥且这个互斥被强制而不是被假定**：非 `auto` 的标准属性会让
  Chromium/Safari **丢弃该元素上的每一条 `::-webkit-scrollbar*` 规则**（包括 `:hover`），
  「**于是无条件同时声明两者，会让 hover token 哪儿都渲染不出来**」。
  所以标准属性被放进 `@supports not selector(::-webkit-scrollbar)`。

**测试段（:66-84）几乎每一段都是可迁移的方法**：
- **规则解析器会把 at-rule 拍平**，所以「gate 被删掉、或一条声明被挪到 gate 另一侧」时，
  **文件里其他每一条断言都还是绿的**——因此额外加了**按源码偏移量断言路径划分**（:66）；
- e2e 只断言「**只有真实引擎才能报告的事实**」：预留带宽与引擎走了哪条渲染路径（:68）；
- 提交一份 golden **记录解析后的样式与几何**，
  理由是「其他 web 场景提交的 aria golden **承载不了一次纯 CSS 改动**：
  它不改 DOM、不改可访问名，**规范化后的树加不加这个改动都逐字节相同**」（:70）；
  且**故意排除绝对坐标**——那样的 fixture「**记录的是平台而不是这次改动**」；
- **gate 有一个负控制**（:76）：把 `@supports` 包装从样式表里删掉、重新构建、重跑 e2e，
  那条 `scrollbar-width: auto` 断言会变红——「这正是 gate 要防的抑制」；
- **两条断言各抓一种回归，靠「一次只变一条声明、其余断言静音」建立**（:80）；
- **最后一段是本项目最该记住的「假通过」**（:82-84）：
  `WorkspaceBrowser.module.css` **从来不进 `apps/web/dist`**——
  ui-workspace 是运行时插件，它的 CSS 被内联进自己包的构建产物。
  「**一个只重跑 `build:web` 的负控制，跑的是一个陈旧的 bundle，
  于是在声明被删掉的情况下也通过——这读起来像一个空洞的测试，而不是一个无效的控制。**」
  修法是先 `pnpm --filter … run bundle`、**grep 产物确认声明在里面**、再 `build:web`。
  并且：`test:web` 原本只跑 `build:web`，「所以每一次滚动区域或插件 CSS 改动都会掉进这个陷阱；
  现在它先跑 `build`……**CI 从未暴露，只有本地脚本暴露——
  而那恰恰是『陈旧构建导致的通过』最容易被相信的地方。**」

→ **本项目直接可用的三条**：
① 从现状派生的检查只能确认已知；② 解析器拍平结构时要用位置断言补；
③ **验证之前先确认你测的是刚构建出来的产物**，否则「通过」是空洞的。

## B-14 `2026-07-28-web-agent-runtime-context.md`（33 行）

**症状**（:9）：共享 CLI base 配了一个**空的部署人设**，Web overlay 没有替换它，
Web 启动器也没加来源或交互界面的 section。
会话 header 为工具与持久化记录了工作目录，**但模型 prompt 里没有陈述那个目录，也没有说明这是 Web GUI**。
于是「把这个页面的主题改一下」会让 agent **去选中的项目里搜一个没指明的页面**，
哪怕用户指的就是正在跑这个会话的 GUI。
**静默：是。** agent 会认真地做错事，没有任何报错。

**修法**（:13-15）：Web bundle 提供简洁的 coding-agent 人设，
内含解析后的 `{{model}}` 与会话 `{{cwd}}`；`web-runtime` 插件在 `surfaceContext` 为真时加 `app:web-surface` section。
该 section 把「this page / this GUI / this app」的无限定引用**定义为**指 Web GUI，
**并且明说浏览器不提供隐式的 DOM、路由或截图上下文**，
「**这样模型就能识别产品，而不会声称自己拿到了并没有收到的视觉状态**」。
装配后的文本被记进 `request/header`，**保住「模型可见 ⟺ 已记录」这条不变量**。

**备选（四条）**（:23-29），两条值得：
- **每次 prompt 都带 URL / DOM / 截图**——否，「观察到的失败需要的是**稳定的产品定位**，
  而当前根 URL 并不能识别一个被选中的组件，消息契约里也不存在任何视觉捕获。
  加入动态页面状态**需要一套单独的、有记录的模型输入设计**，本次修复并不蕴含它。」
- **要求会话 Workspace 必须是 harness 的 checkout**——否，
  「Workspace cwd 是用户的任务目标，**可能合法地是一个空项目或另一个仓库**」。

## B-15 `2026-07-28-web-gui-feedback-loop.md`（39 行）

**症状（本项目做「验证」时最该读的一条）**（:9）：
Web agent 既认不出托管它会话的 GUI，也不知道用户正在看的 URL，
所以一次 GUI 编辑**没有可执行的验收目标**——源码编辑、产物构建、一个在监听的进程、
用户已经打开的页面，彼此是不相干的观察。
而**仓库自身的可供性让一个错误的替代品看起来是有效的**：

> `apps/web/package.json` exposed `vite` as its `dev` script and
> **bare Vite returned HTTP 200 even though it could not inject `window.__DSH_BOOT__`.**

——**裸 Vite 返回 HTTP 200，尽管它根本注入不了引导数据。**
**静默：是。** 检查绿了，验证的却是另一个东西。
（原文还指向一份独立的事后分析 `docs/postmortem/0003-…`，「拥有事件时间线与为什么原来的检查会接受错误的页面、进程和端口」。）

**修法**（:15-21）：`web-runtime` 插件**发布唯一一个规范的 loopback URL**，
**同时**作为模型可见的定位信息与受管 shell 事实（`DSH_WEB_URL` 进入每一次前台或受管后台 bash 调用）；
`apps/web` 的开发脚本与 Vite 配置**在打开端口之前就拒绝 serve 模式**，
诊断里点明 `apps/web` 是「只构建的壳」、只有 `dsh web` 会注入引导数据。
并把「隐藏的启动契约」的所有权从用户转给 agent：
自动客户端插件重载**额外要求同一 checkout 下的 `pnpm run dev:web` watcher**，
**agent 必须先验证它，才能承诺「不用刷新」**。

**两句直接可以进本项目 `rules/` 的话**（:21 + :25）：
> **Starting a separate server proves only that a separate server works.**
（启动另一个服务器只能证明另一个服务器能跑。）
> These assertions inspect **prompt state, process exit, shell output, DOM identity, and HTTP bytes
> rather than an agent's success statement.**
（这些断言检查的是 prompt 状态、进程退出、shell 输出、DOM 身份与 HTTP 字节，
**而不是 agent 自己说的「成功了」**。）

**验证段的每一条都是「对真实对象」的**（:25）：真实 CLI smoke 启动 `dsh web` 并捕获 provider 请求；
`dev:web` watcher 测试在源码变更后**重建一个隔离的客户端 bundle**；
浏览器 HMR 场景启动 `dsh web`、改一个初始 roster bundle、**在同一页面身份下观察到新 DOM**；
一个**真实的 Vite 子进程测试**要求 serve 模式自然退出，
并**给 `Server.listen()` 埋点以证明它从未被调用**；
真实 Loader 的 webserver 测试在进程绑定之后重写一个静态资源，**证明同一端口返回新字节**。

**备选（四条）**（:29-35）：
- 只扩展系统 prompt——否，「会让目标对工具不可用、**保留误导性的裸 Vite 路径**，
  且**无法证明一个已存在的进程如何观察到重建后的产物**」；
- 只删 `apps/web` 的开发脚本而不守卫 Vite——否，
  「**`npx vite` 正是那次事故的命令，它绕过包脚本。serve 模式本身必须失败。**」
  → **堵路径不等于堵能力**，与 S-11「留下任何一条产品路径就等于间接留住它」同型。
- 每次编辑后自动重启或替换当前 Web 进程——否（静态服务器本来就每次请求读当前产物，
  重启会打断那个请求编辑的会话）。

## B-16 `2026-07-29-atomic-web-image-admission.md`（29 行）

**症状**（:9）：图像 prompt 准入与 `session.selectModel` 各自跨异步查找读取会话模态状态。
没有统一的排序边界时：**一个图像 prompt 可能校验通过一个支持图像的目标，
而并发的选择正在装上一个纯文本目标**；
或者选择**在收件箱出队之后、其持久消息事件之前漏掉一个 prompt**。
**静默：是**（竞态型）。
而「扫描不可变事件日志」虽然避开了第二个竞态，
却**永久地挡住了纯文本选择——即使压缩已经把图像从当前模型历史里移走了**。

**修法**（:13-15）：每个活的 Web agent 有**一条私有 promise 链**，
被「带图像的 prompt 准入」与「模型选择」共享；**纯文本 prompt 绕过这条链**（它们改不了模态约束）。
待发布集合**在出队时记录排队项、在入队时就记录 steering 项**
（steering 从不进入排队 UI 镜像），并保留到它对应的持久事件发布为止；
准入没发布就结束时，**转入 idle 会退役这些条目**。
模型选择检查三处：待发布集合、排队 UI 镜像、以及 `Session.deriveMessages()`——
「**即压缩之后当前的模型可见历史**」。

**权威边界被点名**（:17）：
> **Provider adapters remain the final enforcement boundary.**
> The host ordering only prevents its mutable route and pending image state from contradicting each other
> before request assembly.
——宿主的排序只是防止「可变路由」与「待处理图像状态」在请求装配前自相矛盾；
**最终的强制边界仍然是 provider adapter。**
→ 与 S-24 同型：**上游的一致性检查不能自称是强制边界。**

**备选（三条）**（:21-25）：扫描每一个不可变会话事件（否，
「它抓得到已发布的图像，但**把已被压缩掉的内容当成永久模型可见**」）/
在出队时退役待发布镜像（否，那正好留下漏检区间）/
把每个 prompt 与会话变更都串行化（否，会加延迟与所有权而**不多关掉一个模态竞态**）。

## B-17 `2026-07-29-human-transcript-append-origin.md`（53 行）

**症状**（:9）：终端与宿主历史网关**都把「模型可见的 surface」当成了人类 transcript**。
一次成功的压缩会用一个检查点节点替换 surface 的一段区间，
**于是那次替换落地的瞬间，终端把它遮蔽掉的每条消息都丢掉了——那是用户已经读过的对话**；
后续每次替换还会再跑一遍这个破坏性重建。
分页也被波及：`maxMessages` 数了窗口里每一条 `user/message` 与 `assistant/message`，
**于是一份只给模型看的替换副本占掉了一个人类从没填过的页位**。

**根因的定性写得极准**（:11，**本项目要抄的一句**）：
> **Nothing was lost from the log.** `Session.events` still held every original message and full tool result;
> the surface only decides what the model is sent next.
> **The defect was entirely in the projection.**
——**日志里什么都没丢，缺陷完全在投影上。**
**静默：是。** 数据完好，展示错了，没有任何报错。
→ 对本项目：**证据链完整 ≠ 呈现正确**。这两件事要分别验收。

**修法**（:15-21）：模型投影与人类投影分开，
**由事件自己的 marker 决定它属于哪一个**——`dsh-session` 导出
`isAppendSurfaceEvent(event)` / `isReplacementSurfaceEvent(event)`；
**append-origin 事件是 transcript 的持久来源，替换副本只给模型**。
所有「必须发送模型确切看到的东西」的消费者（`deriveMessages`、token 计量、压缩后端、
工具配对、注入上下文的存活性、跨会话引用投影）**仍然读 `session.surface`**。
一次落地的压缩在自己的日志位置贡献**一行暗色的「…… 更早的上下文已被压缩 ……」**：
「**marker 报告的是模型在哪里停止看见那段历史，而不是把它抹掉。**」

**checkpoint 的识别方式是本篇的关键判据**（:19 + :33）：
通过压缩接缝**自己的契约** `isCompactCheckpointSource`（`CompactionEngine` 要求打在替换用户消息上的
后端无关 marker）来识别，「**所以终端依赖的是被声明的词表，而不是替换的形状**」。
对应的备选被否：
> **Recognize a checkpoint by shape (a replacement `user/message`).** Rejected:
> it reads **a coincidence of today's producers** instead of a declared contract,
> and any future producer that replaces a range with a user message
> **would silently inherit the compaction marker.**
——**按形状识别读的是「今天的生产者恰好长这样」这个巧合**；
将来任何用用户消息替换一段区间的生产者**都会静默地继承压缩标记**。
→ 这条对本项目「怎么识别一条证据的类别」是直接指导：**按声明的类型识别，不按形状猜。**

**其他备选（四条）**（:35-41）：
继续把 checkpoint 渲染成注入上下文卡片（否，「框起来的 checkpoint 是**写给模型的指令信封**，
不是人类对话内容。显示它却隐藏它替换掉的历史，**把读者需要的东西倒过来了**」）/
再持久化一份展示用 transcript（否，append-only 日志已含权威素材）/
从 `compaction/*` 括号派生 marker（否，括号是操作前后的两个时间点标记，
而 transcript 需要的是 **surface 实际改变的位置**）/
像 `session-query` 那样重折日志来分类（否，「折叠回答的是整份日志的问题，
而投影问的是逐事件的问题，**事件自己的 marker 已经在常数时间内回答了它**」）。

**后果里有一条罕见的、对未来读者的交代**（:47）：
`rebuildTranscript` 现在为整份日志里每个 append-origin 事件都物化一个组件，
**成本随会话长度增长而不再随 surface 增长**；
「这正是这次修复要做的交换——保住历史就是目的——
但**窗口化或复用策略属于第一个真正测到重建变慢的人，
而不属于日后某个纳闷『这活儿怎么变多了』的性能分析师**。」

**测试的两处改动被明写**（:51-53）：
- 原来的 surface 替换终端测试**钉的是「隐藏被遮蔽的工具调用」（即错误行为）**，
  现在改成钉「保留 + 恰好一个 marker」；
- **压缩快照场景原本写的是一个 `agent-instructions` 来源却声称在钉压缩**，
  现在改成写一个真正的 checkpoint 来源，三份 fixture 重录；
- **live/replay 等价是被 fixture 钉住的，不只是在文里断言**：
  `surface-replayed-compaction` 以「替换已存储」的状态挂载，
  录出来与 live 路径的 `surface-after-compaction-wide` **逐字节相同**——
  「改动任一路径都会打破这个相等，**这正是要的**：
  用户遇到回归的正是 resume 投影，**这两份 fixture 必须一起动。**」

## B-18 `2026-07-29-pnpm-setup-runner-isolation.md`（27 行）

**症状**（:9）：`pnpm/action-setup@v4` 默认把安装目标放在 `~/setup-pnpm` 并在 setup 时**替换该目录**。
自建 CI 的六个 runner 服务跑在同一个 VM 用户下，**并发作业共享同一个目标**。
复现的那次运行里，**三个作业在 73 毫秒内进入 pnpm setup**，
一个 setup **删掉了另一个进程的当前工作目录**，两个作业在 Node 的 `uv_cwd` 初始化里失败。
**静默：部分**——失败是响的，但**归因是错的**：

> A retry on another runner passed, **making the failure timing-dependent rather than a repository-test regression.**

——在另一个 runner 上重试就过了，于是它看起来像时序问题而不是仓库测试回归。
→ **「重试能过」是最容易把人带偏的信号**，本项目在评测复现上要特别小心。

**修法**（:13-15）：每个 `pnpm/action-setup` 步骤都设 `dest: ${{ runner.temp }}/setup-pnpm`；
并且——**关键**——`scripts/ci-workflow.spec.ts` 这个**工作流回归测试
会发现 `ci.yml` 里每一个 `pnpm/action-setup` 步骤，并拒绝任何没有 runner 私有目标的步骤**，
「这让新加的作业留在同一个隔离边界内」。
→ **把「以后新增的也必须遵守」变成一条自动发现 + 拒绝的测试**，而不是一条 README 里的约定。

**备选（三条）**（:19-23）：串行化 failover 作业（否，丢掉六 runner 池的并行性，
**把一个 action 局部的目录冲突变成跨独立作业的排队**）/
给每个 runner 服务分配单独 Unix 用户（否，把不变量**挪到外部 VM 配置里**，
并让「刻意共享的持久 pnpm store」的所有权复杂化）/
**重试失败的 setup 步骤**（否，「重试**只降低观察到的碰撞率**，
另一个并发 setup 仍然可以再次删掉同一个共享目录」）。

## B-19 `2026-07-29-sticky-composer-conversation-scroll.md`（35 行）

**症状**（:9）：会话列把滚动劈成两半——聊天视图拥有 `overflow-y: auto`，
而 composer 栈是它的兄弟节点。于是**在统计行或输入框上滚滚轮什么都不会发生**；
长草稿更糟，因为 textarea 自己也是滚动口，滚轮会**被困在里面**。
**静默：是**（交互型）：没有任何错误，只是手势落在了不滚动的区域。

**修法**（:13-17）：`ConversationRoot` 永远拥有**一个** `data-conversation-scroll` 主体，
composer 座位用 `position: sticky; bottom: 0` 粘在同一个滚动口里；
视图组件**只有在挂载于该宿主之外时**（单元测试）才保留本地滚动器，
在宿主下则设 `overflow: visible` 并通过 `closest('[data-conversation-scroll]')` 解析底部跟随与前置锚定。
InputBar 的 textarea 在宿主内**链式处理 `wheel` 且 `{ passive: false }`**：
还能往那个方向滚时保留原生手势，**只有到了自己的边缘才 `preventDefault` 并把 `deltaY` 施加到宿主上**。

**分页锚定的判据值得抄**（:17）：历史前置**跟随读者意图，靠稳定的渲染节点/调用身份，
而不是整个滚动口的高度差**——记录第一个可见的 `data-chat-anchor-key` 及其相对位置，
**在请求在飞的期间每次读者滚动后重新选择当前可见的稳定锚点**，
再按该行前置后的矩形差补偿。
「**到达底部或追加读者自己的消息会取消分页锚点，
这样一个迟到的页面就不能把视图从最新内容那里拉走。**」
→ **补偿要绑在稳定身份上，不能绑在几何量上**——这与本项目「证据指针要绑 id 不绑偏移」同型。

**备选（五条）**（:21-29），最后一条是范围诚实：
**「给每一种浏览器滚动输入源建模」**——**在这个窄修复里被否**：
「复现的桌面路径用的是滚轮/触控板输入。指针/触摸滚动、拖原生滚动条、键盘滚动、
焦点导航、嵌套 overflow 所有权**被留在输入源模型之外，而不是加一台通用输入状态机**。」
并注明后来由 `2026-08-06-reader-scroll-attribution-observed-top-ledger`（本轮 B-46）
**通过 observed-top 台账把归因泛化，仍然没有引入输入状态机**。
→ **把「本次不做的范围」写清楚，并在它被真正关闭时回填链接。**

## B-20 `2026-07-29-web-details-session-lifecycle.md`（29 行）

**症状**（:9）：details 入口是**会话作用域**的，但它偏好的栅格宽度是**根作用域**的。
切换到另一个会话会替换内容**但不关闭那个根偏好**，
于是**新的所有者继承了陈旧的查看几何**。
**静默：是。** 布局看起来正常，只是它属于上一个会话。

**修法**（:13）：`AppFrame` **只在某个会话真的能拥有 details 时**才记录「最后一个非空白的选中 id」，
于是 hero 与其他未选中状态**既不触发关闭也不替换最后的会话所有者**；
它们渲染出来的 details 轨道**派生为零，而不改变已存储的偏好**。
→ **「派生为零」与「把偏好置零」被严格分开**——一个是呈现，一个是状态。

**备选（四条）**（:19-25），第一条与第四条同型且值得记：
「在 New Session 的点击处理器里关闭 details」——否，
「一个未选中的界面**没有会话作用域的 details，也就不得变更几何**。
**关闭属于两个已定义的会话所有者之间的那次比较。**」
「把每一次当前投影变化都当成会话切换」——否，
「启动物化、hero、清除选择与失效**都不是两个会话所有者之间的转换**。」
→ **触发条件要落在「两个确定的状态之间的转换」上，不落在「有事情发生了」上。**
（本项目声明 flag 的触发条件时是同一个陷阱。）

## B-21 `2026-07-30-approval-panel-command-cap.md`（52 行）

**症状（安全相关，且直接对应本项目的「人类复核」环节）**（:9）：
审批面板是 composer 的接管态：沙箱升级等待时，它用模型的理由 + 配对命令 + 拒绝/允许行替换输入框。
两段文本都是**无界的模型输出**，而卡片**没有高度上限**。
一条长命令（**这才是现实形状**，因为升级恰恰发生在沙箱刚拒绝的那条命令上，
而被拒的命令常常是一条长内联写入）把卡片撑到**操作行离开视口**：

> **The user could read the request and not answer it**: the buttons existed, off screen,
> in a sticky footer that had already used the whole column.

**静默：是。** 没有任何错误，审批 UI 只是**变得无法作答**。

**修法**（:15-21）：理由与命令放进一个**滚动区域**，上限与 composer 草稿区**同一个值**；
琥珀条与操作行**放在滚动区之外**，「于是两个按钮在任何内容长度下都在卡片里」。
上限是**一个值两个消费者**，声明为 `.composerSeat` 上的 `--dsh-composer-text-max-height: 336px`
（composer 链唯一的共同祖先），
「于是这个座位**没法把它的两个状态封成不同高度**：
设计师要的『与输入框最大高度统一』**现在是样式表的一个事实，而不是两个文件里重复的一个数字**」。
滚动区**是一个 tab 停靠点**（`tabIndex={0}` + `role="group"`），理由是（:19）：
「没有自己的 tab 停靠点，一个只用键盘的用户能到达按钮却永远到不了命令的尾部，
**从而批准了他们读不完的东西**。」

**备选（四条）**（:25-31），第三条对本项目的证据呈现是硬约束：
**「省略号截断命令」**——否：
> the command is **the thing being approved**: hiding its tail
> **asks the user to consent to text they cannot read.**
> Truncation is also unrecoverable here — the panel is the whole approval UI,
> so there is no "show more" surface to fall back to.
——**被审批的东西不能被截断**，因为那等于要求用户同意他读不到的文本；
而且这里的截断**不可恢复**，面板就是全部的审批 UI，没有「展开更多」可退。

**验证段里有三条可迁移的测试方法**（:38 + :42-50）：
- **「上限在没有超过它的内容时是不可证伪的」**（:38）：
  场景录的命令是一个 200-token 的大块，「**这个代价是刻意的**」——
  「**模型会把任何常规载荷压掉**（第一次录制把『alpha 重复 400 次』变成了
  `printf 'alpha %.0s' {1..400}`，一条**什么也证明不了**的单行命令）」。
  → **测试数据必须真的越过被测边界；而当被测系统里有模型时，它会替你把测试数据优化掉。**
- **几何断言被显式防「空洞通过」**（:42）：
  「区域必须**真的在滚动**，而且**测到的上限必须等于 composer 自己的上限**——
  这个值测试是**在发送之前从活的草稿滚动口上读出来的，而不是硬编码 px**。」
- **金样只留一个（等待中的面板），已作答状态改为对『世界』断言**（:50）：
  已决结果、被升级命令写出的文件、`DONE`、面板消失、composer 重新可用。
  理由：**已作答的 transcript 金样立不住**，因为被拒的第一次尝试渲染的是**操作系统自己的拒绝文本**，
  而那段文本是平台相关的（macOS 与 Linux 措辞不同）。
  > Any scenario whose transcript contains a sandbox-denied command inherits that,
  > so **the denial belongs in assertions, never in a golden.**
  → **平台相关的文本只能进断言，不能进金样。** 本项目做跨平台冻结时同理。
- **复现条件被写清楚**（:46）：要复现「按钮跑到屏幕外」，需要的是
  **卡片高过滚动口**，而不只是卡片很高——因为座位是 sticky，卡片还装得下时按钮仍可见。
- 最后又一次踩到 B-13 那个坑（:52）：面板以客户端模块 bundle 发布，
  **只跑 `build:web` 不会拾取它的改动**，「否则浏览器泳道断言的是一个比代码树更旧的客户端」。

## B-22 `2026-07-30-bounded-overwrite-diff-basis.md`（31 行）

**症状**（:9）：`dsh-fs-local` 在 `FsWriteOutcome.before` 里返回**完整的旧文件**，
供消费者构造上下文 diff。这个**只为呈现服务**的预读**没有界**：
一次大覆盖可能把整个旧文件分配进内存；
而**只查一次更早的路径 stat 无法强制这个限制**，
因为**外部进程可以在 stat 与 read 之间替换或增大该文件**。
**静默：是**（资源型）：功能正常，内存悄悄爆。

**修法（本条对本项目的「口径基准」有直接价值）**（:13）：
新增部署设置 `diffBasisMaxBytes`（默认 10 MiB）；
只有当 UTF-8 替换内容**严格小于**该上限、**且**为基准而打开的旧文件**也在上限之下**时才提供 `before`；
旧文件的读取**打开描述符、在该描述符上 stat、按可取消的分块最多读配置的字节数**，
到边界就返回 `null`。

**关键的一条**（同行）：
> **A size change after descriptor stat also returns `null`, even if the final size remains below the limit,
> because a partial prefix would be an incorrect diff basis.**
——**描述符 stat 之后大小变了就返回 `null`，即使最终大小仍在限制之内**，
因为**一个部分前缀会是一个错误的 diff 基准**。
→ 本项目的对照：**宁可给不出证据基准，也不给一个「看起来对」的基准。**
二进制或非法 UTF-8 的旧内容同样返回 `null`；描述符阶段的任何 errno 也返回 `null`——
「一个在调用者预检与基准打开之间被删掉或变得不可读的旧文件，
**不能让一次调用者已经承诺的写入失败**；只有取消与非 errno 故障才向上传播。」
**这些结果都不阻塞原子写。**

**备选（四条）**（:21-27），第三条是通用判据：
**「相信最初的 `probe()` 大小，然后做一次普通的整文件读」**——否：
> that size **can become stale before the read**.
> **The descriptor reader must enforce the bound on the object it actually reads.**
——**必须在你真正读的那个对象上强制这个界。**
（与 S-06 的「陈旧检查必须与变更在同一临界区」同一族。）
第一条也值得：**沿用读工具的流式阈值当硬编码门槛**——否，
「两个同值常量会造出一个**未被强制的跨包耦合**」。

**边界写清楚**（:17）：`before: null` 是**请消费者用它已有的整文件兜底**；
这个限制**只限制额外的旧内容获取与「有资格构成上下文对」这件事**，
不限制调用者提供的替换内容、返回的 `after`、或消费者的兜底渲染。

## B-23 `2026-07-30-composer-context-stack-order.md`（33 行）

**症状**（:9）：Goal / Todo / Queue 各自独立地贡献到同一个 dock 列表，
**但它们的注册顺序与间距规则没有编码组合矩阵**。
渲染器把 Todo 放在 Queue 与 Goal 之前，**而 Queue 与 Goal 都带着本意用于 composer 边界的负边距**；
三者同时存在时，Queue 贴上了 Goal、Goal 贴上了 composer，**把设计的层级颠倒了**。
**静默：是。** 每个组件单独看都对，组合起来错。（与 B-10「三个各自正确的行为」同型。）

**修法**（:13-17）：**顺序与重叠是两份分开的契约**——
「注册顺序确立语义层级；栈上的 CSS 变量确立共享几何」；
数字之间留空档，「让未来的条目**不依赖插件激活顺序**就能声明自己想要的位置」。
关键一句：
> Queue does not infer that it may overlap **merely from being the last visible entry**,
> because Goal or Todo can be the last visible context card when no queue exists.
——**Queue 不因为「碰巧是最后一个可见项」就推断自己可以重叠。**
→ **不要从运行时的偶然位置推断一条策略。**

**备选（三条）**（:25-29）：保留各自的负边距（否，「受影响的邻居会随槽位顺序变化；
**一个局部边距无法表达哪一种关系是被允许的**，除非语义顺序也被固定」）/
在根组件里逐个渲染已知的 dock id（否，**把一个可扩展的槽位变成硬编码的组件清单**）/
「把碰巧最后的那个 dock 项塞进去」（否，理由同上）。

## B-24 `2026-07-30-hover-popup-pointer-grace.md`（35 行）

**症状**（:9）：工作区行的两种浮层**都飘到了指针够不着的地方**——
`HoverCard` 在第一次 `pointerleave` 就关闭，且卡片是 `pointer-events: none`，
而卡片离锚点右缘 8px，**于是每条通往它的路径都要穿过「不属于任何一方」的地面，
卡片在到达之前就被杀掉了**；行动作菜单的离开处理器挂在**被 portal 出去的列表**上，
「**瞄准那个打开列表的 `...` 触发器反而会关掉列表**」。
**静默：是**（可用性型）。

**修法**（:13-17）：一个共享的 `usePointerGrace`（200ms 可取消延迟关闭）——
离开时**布防**、回来时**撤防**；卡片不再 `pointer-events: none`；
菜单的离开判定**从被 portal 的列表挪到包裹 span 上**，
理由很实在：「**React 的 enter/leave 遍历走的是 React 树**，
所以触发器与被 portal 的列表在那里是**同一个区域**」。

**一条很容易写错的 effect 依赖**（:17）：
所有者驱动的关闭（选择、Escape、外部点击）**在一个只以 `open` 为 key 的 effect 里**撤防挂起的 grace——
「把它折进外部点击的 effect 会**在每次重渲染时都取消 grace**，
因为所有者每次传的是一个新的 `onClose` 闭包」。

**备选（四条）**（:21-27），第三条是「半个修复更糟」的例子：
**「保持卡片 `pointer-events: none`，只加 grace」**——否，
「那样指针停在卡片上时命中的是它背后的东西，**于是 grace 会到期并关掉用户刚够到的卡片**」。

**测试的分工被写清楚**（:35）：jsdom 单测钉 grace 边界、返回取消、不二次计时、
所有者关闭时撤防、关闭状态下不布防；
而**可达性手势本身**（把指针移到卡片上、在打开的列表与其触发器之间移动）
**在真实浏览器 e2e 里钉**，「因为它们依赖 jsdom 不建模的命中测试与布局」。
→ **按「谁能真正观察到这个事实」分配测试层级**，与 B-13 同一原则。


---

# §C 对 finaudit-agent 的启示

**素材范围**：本节只从上面 §A（S-01…S-46）与 §B（B-01…B-24）的正文条目提炼，
不引用未在正文写过的篇目。引用一律回指本文的 `S-nn` / `B-nn` 与其原文行号。

先按五个问题归纳（§C.0），再折成「该借鉴 / 该刻意不借」两栏（§C.1、§C.2），
**每条带落地点：已落地 → 具体编号；未落地 → 明写 `未落地` 并说明该落到哪里**
（`references/README.md` 硬规则第 3 条）。

## §C.0 五问

### ① 删除的判据：有明写的标准吗？

**有，而且不止一条。** 从正文里能整理出九条互不重叠的「删得起」判据，
另有一条明确的**反判据**和一类明确的**豁免**：

| 判据 | 出处 | 一句话 |
|---|---|---|
| J-a **零生产消费者（逐条搜过）** | S-01:13、S-07:9、S-08:11 | 不是「我觉得没人用」，而是把每一处命中逐条分类（`.update(` 命中全是 `createHash().update()` 或测试） |
| J-b **可从别处重建** | S-01:23 | 摘要要提供的东西都能从 append-only 日志推导，或已在不可变 header 里 |
| J-c **没有任何代码路径能到达它** | S-06:68 | 删枚举值 `FS_PARTIAL_OBSERVATION` 用的判据，**比「零调用者」更强** |
| J-d **这个约束保护的东西，不是它声称保护的东西** | S-06:16 | 「部分视图不能授权 edit」实际保护的不是安全，字面编辑需要的只是新鲜度 |
| J-e **这个优化没有优化到它声称优化的地方** | S-09:11 | 伪链表并没有把主导操作（`indexOf` 替换）变成常数时间 |
| J-f **同一事实有多个结构表示 = 可静默分叉的真相源** | S-04:9、S-08:14、S-15:11 | 镜像事件、两份 `summarize()`、三个平行容器 |
| J-g **词表宣告了一个没有任何路径兑现的能力** | S-07:9、S-25:9 | `ImageBlock` 每条路径都丢弃；edit 按钮背后什么都没有 |
| J-h **被消费流程接受了，却什么都不做，且不告诉任何人** | S-08:12 | `suppressOutput` 被 codec 解析然后在每条路径上丢弃，连 warn 都没有 |
| J-i **模型可见面 / 用户可见面的重叠** | S-38:9、S-26:9 | 判据是「多一份 schema 却不多一个能力」，不是「代码重复」 |

**反判据（本项目最容易踩反的一条）**——`S-03`：
`whenIdle()` **零生产调用者，但被判定必须留**，因为它是公共契约里让非所有者安全观测的唯一正确路径，
删了会把消费者推向「手工观察 `running`→`idle` 转换」这条脆弱路径。
所以完整的删除判据是**合取**：**零消费者 ∧ 不会把消费者推向更差的替代**。
`S-04:19` 再补第三项：**消费者的分量要算**——「ui-stdio 需要它」不构成理由，因为它是一次性测试 REPL。

**豁免（对本项目最重要）**——审计字段不适用「零读者⇒可删」：

- `S-08:24`：`durationMs` 保留，因为 **durable audit timing is useful independently of a current reader**；
- `S-09:15`：`sourceEventSeqs`、崩溃修复引用的 `tool/call` seq、`SessionStartSource` 全部保留，
  因为**这些字段有审计/拦截角色，「当前零读者」推翻不了它**。

**删除范围的判据**（`S-11:11`）：`Keeping any of those product paths would preserve the redundant agent indirectly.`
——边界不是「那个类」，而是**所有能让它复活的入口**。`B-15:31` 是同一条的 bug 侧实证：
只删 `apps/web` 的开发脚本不够，`npx vite` 绕过包脚本，**serve 模式本身必须失败**。

**还有一条系统性的记录纪律**：46 篇里大量篇目带**「重新引入的门槛」**一节
（S-11:41、S-22:37、S-23:27、S-25:17、S-28:38、S-29:39、S-33:30、S-37:31、S-39:29、S-43:36、S-44:21），
措辞高度一致——**要回来必须带一个具名消费者 + 它自己的失败/生命周期/重放/测试契约**，
「换个拼写或加个输出垫片是不够的」（S-33:30）。
`S-22` 是这条纪律被兑现的实例：`S-07` 删掉 `ImageBlock`，三周后它带着**持久附件引用**回来，且更窄。

### ② 被否决的简化及理由

**先说计数口径。** 正文 70 条里，「原文未记录备选」只出现 **1 次**（S-01，文末自带
`alternatives-not-recorded (pre-format Agent Note)` 标记）。语料侧核对（本次会话实跑）：

```
# 在语料根 .agents/notes/ 下
grep -l 'alternatives-not-recorded' $(ls implemented/simplification/*.md | grep -v '\.zh\.md$') | wc -l   # -> 1
grep -l 'alternatives-not-recorded' $(ls implemented/bug-fix/*.md        | grep -v '\.zh\.md$') | wc -l   # -> 0
```

即**这两个目录几乎每一篇都记了备选**，「备选缺失」不是这批语料的特征。
下面这些是**提了但被否**的简化，按对本项目的价值排序：

1. **`S-03` 连 `whenIdle()` 一起删** —— 否。原提案形状，**在拿代码验证前提之后被自己推翻**。
   → 记录价值：一份笔记里同时留下「删了什么」和「原本还想删什么、为什么没删」。
2. **`S-14` 保留那个「在有纪律的服务边界后面的编辑器 bridge」** —— 否，**尽管它实现得对**
   （正确使用接口服务、工具自有渲染意图、审批应答者、纯净 stdout）。
   判词是：`那些边界是自洽的，但它们没法让编辑器卡片、会话导航、配置选择器和人类征询属于一个自动化协议。`
   → **「实现得对」不能救「归属错」。**
3. **`S-29` 把包挪到 `examples/` 或 `experimental/`** —— 否：
   `挪动代码并不提供当前的产品需求、被维护的部署或装配后的验收。`
   → 本项目最容易走的软路（「先降级放着」）被明确堵死。
4. **`S-11` 把 stdio / mock 机制也一起删** —— 否，**机制是独立基础设施**，
   删的是「面向行的产品级 agent」这个产品面。→ **删产品面 ≠ 删机制。**
5. **`S-27` 把不变量支持从仓库里删掉** —— 否，「只有默认产品配置在范围之外」。
   删的是**发布树上的挂载**，不是这套能力。
6. **`S-46` 顺手把 `ui-onboarding` 命名空间也注销** —— 否：
   设置接缝会拿**已存储的文档**去校验已注册的命名空间，注销会让磁盘上已有的设置文档变非法。
   → **删代码时别顺手让已有数据变成非法。**
7. **`S-38` 从每一个发布组合里删掉 `str_replace_editor`** —— 否，`minimal` preset 的两工具花名册**有意**包含它。
   → **删除要按「组合契约」逐个判，不能一刀切。**
8. **`S-13` 保留一个私有通用注册表、今天只暴露 plan** —— 否：
   `未来的协作状态可以从两个具体案例里确立正确的共享 seam.` → **抽象等第二个具体案例。**
9. **`S-43` 把实验规则挪进通用包指令** —— 否，那让**每一次包改动都背上一个假想包类别的规则**。
10. **`S-30` 写一份持久的 pre-feedback 假脱机** —— **推迟**（不是否决），
    直到某个部署真的需要 feedback 之前的崩溃恢复。→ 「推迟」与「否决」被分开记。
11. **`S-31` 「在消息之前分叉」的语义** —— **范围外**（第三种处置）。
    并说明移除现有控件是**把这个位置腾空**，而不是让一个语义相反的东西占着。

**一处被反复推翻的记录**（`S-40:17`）：steering 气泡的 `插话` 标题行被**删 → 加回 → 再删**三次，
每次的触发条件都被写下来（composer 能不能 steer 变了）。
→ **一个决策被反复推翻不是丑事，把每次翻转的触发条件写下来才是记录的价值。**

### ③ 静默型 bug（不报错、不抛异常、结果看起来正常）

正文 B-01…B-24 里标 `静默：是` 的 **17 条**、`静默：部分` 的 **4 条**、`静默：否` 的 **1 条**（B-12）。
按**失败形状**归为八类，每类给最锋利的一条：

| 形状 | 代表 | 为什么对本项目致命 |
|---|---|---|
| **F-i 抽样/排序/截断三个口径各自合理，合起来是误导性证据** | `B-10`：22 个顶层条目、11485 个文件，`glob {"pattern":"*"}` 匹配 10030 条，内联 100 条**全落在同一棵刚解压的子树**，模型**从未看见另外 21 个条目**。原文措辞：`Three individually valid behaviors composed into the false impression` | **工具成功、结果正确、模型的结论错**——本轮最危险的一种。财报抽取里「取前 N 行 / 按某列排序 / 页内截断」完全同构 |
| **F-ii 数据完好，投影错了** | `B-17`：`Nothing was lost from the log. … The defect was entirely in the projection.` 压缩替换 surface 一段区间，终端把用户已读过的对话全丢了 | **证据链完整 ≠ 呈现正确**，这两件事要分别验收 |
| **F-iii 成功语义被伪造** | `B-08`：provider 返回格式良好的流 + 终态 `stop` + **零内容块**，adapter 映射成成功 → loop 记一条空 `assistant/message`、turn 标 `completed`、**重试从不运行、没有任何失败到达调用者**；`S-20`：合成 turn **为从未跑过模型的工作产生了「执行结果」**；`S-35`：回执**在模型 turn 失败时仍然可见** | 直接对应「给不出证据链却记成 `completed`」 |
| **F-iv 身份未被查询绑定，写到别人那里** | `B-04`：JSONL 按会话 id 跨项目目录选物理日志，后续修复/追加却用**解析出来的 header**；SQLite 不共享这个歧义，因为主键查询把元数据与事件绑定到被请求的 id 上 | 同一个逻辑契约，**两个后端的安全性不同**，差别来自「身份是否由查询本身绑定」 |
| **F-v 缺省值承担了一个验证不了的语义** | `S-21:13`：`config.goals ?? {}` 把「没配置」变成「配了一个空对象」，于是发布出去的 TUI 挂载了 goals/`tool-goal`/`/goal` **尽管没有任何配置键请求它们**；`S-20` 备选④否掉「要求每个插件事件声明独立资格」，理由是那会**让「没声明」意味着一种核心无法验证的执行关系** | 本项目写 flag 触发条件时的同型错误 |
| **F-vi 陈旧被静默接受** | `S-32`：编辑器删掉后必须加 stamp-keyed 代次，`没有这个，一个被编辑过的文件会一直提供陈旧的组合，直到进程重启`；`S-21` 扁平化时浮出三个潜伏缺陷（`sessionQuery` 只捕获一次→永久禁用 `/resume`；session-store 根目录静默退回 `./.sessions`；`--config-replace` 被 resume 交接丢掉） | **「把重复合并成一份」这个动作本身就是缺陷探测器** |
| **F-vii 有报错，但报错指向错人** | `S-41:22`：装配后的启动器确实 fail loud（`pending (waiting for service: …)`），**但那个错误点名的是消费者，不是配错的提供者**；`B-03`：`fetch failed` 五个字，可执行细节全在 `error.cause` 上被遮蔽；`B-18`：pnpm setup 目录冲突**在另一个 runner 上重试就过了**，于是看起来像时序问题而不是回归 | **「有报错」不等于「报对了」** |
| **F-viii 资源/性能型静默** | `B-05`：摘要请求用了不同 `system` 前缀，**provider KV cache 整段作废，每次压缩把历史 prompt 费付两遍**，功能完全正常；`B-22`：`FsWriteOutcome.before` 的整文件预读**无界**，内存悄悄爆 | 不改变结果，只改变成本——最不容易被评测发现 |

`S-07:21` 给出这一整类的总判词：

> the silent drop was **the one state with no defender**

——要么兑现能力，要么让它编译不过，要么大声拒绝；**唯独「悄悄扔掉」没有任何人能为它辩护**。

而 `S-45:17` 给出**唯一的例外形态**：源码启动器**不校验产物新鲜度**，
陈旧的前端包会被接受、可以静默提供旧的浏览器代码——**但这条被写进了 onboarding 与 CLI 参考**。
两条合起来：**静默行为本身不是罪，「静默且未被写下来」才是。**

### ④ 修复时有没有同时加回归测试？有没有「测试通过但 bug 仍在」的记录？

**回归测试：有，而且是硬要求。** 正文 24 条 bug-fix 每条都有 Verification 段。
更值得抄的是**测试形态本身**：

- **把「以后新增的也必须遵守」变成自动发现 + 拒绝的测试**（`B-18:13`）：
  `ci-workflow.spec.ts` 发现 `ci.yml` 里**每一个** `pnpm/action-setup` 步骤并拒绝没有 runner 私有目标的；
  同型的还有 `B-13:23`（机械检查「既滚动又绘制抬升表面」的样式表必须重绑，**于是笔记不再维护一份完整清单**）、
  `S-27:17`（config-dump 测试拒绝服务条目）、`S-34:37`（源码/依赖/生成目录审计拒绝 Cron 残留）。
- **删掉一个能力之后，用测试钉住「它不在」**（`S-25:13` 的 golden、`S-38:25` 同时钉缺席与存在）。
- **让环境不能决定判定结果**（`S-26:36` 用 `--config` overlay 钉死 `-browse`，
  「这样开发者的显示环境就不能决定这个 picker 究竟能不能被驱动」；
  `S-36:37` 把 Playwright 固定到 `Asia/Shanghai`）。
- **负控制**（`B-13:76`）：把 `@supports` 包装删掉、重新构建、重跑 e2e，**断言必须变红**。
- **live/replay 双 fixture 逐字节相等**（`B-17:53`）：改动任一路径都会打破这个相等，「这正是要的」。

**「测试通过但 bug 仍在」：有，而且是本轮最有价值的一组记录。** 六种不同机制：

1. **快照录下来的就是 bug 本身**（`S-12:34`，教科书案例）：
   > the old recordings captured the model refusing steering as third-party metadata, **the fix's exact failure mode.**

   ——`hook-{cc,codex}-stop-continue` 的 ACP 快照一直全绿，而它录的正是「模型把 `<steering>` 当第三方元数据拒绝」这个缺陷。
2. **测试钉住的正是错误行为**（`S-07:19`：唯一构造 `ImageBlock` 的地方是钉住 skip/drop/estimate 分支的测试；
   `B-17:51`：原终端测试钉的是「隐藏被遮蔽的工具调用」；
   `B-17:53`：压缩快照场景**写的是 `agent-instructions` 来源却声称在钉压缩**）。
   总判词在 `S-01:33`，已被写进对方的 root `AGENTS.md`：
   > a passing test pins current behavior, not necessarily correct behavior; behavior can be an artifact of a past compromise
3. **从现状派生的检查只能确认已知**（`B-13:27`，本轮最该进 `rules/failure-modes.md` 的一条）：
   第一次尝试从「已经重绑过的样式表」反推抬升表面集合——
   一个**还没有人重绑过的表面（恰恰是这个检查存在的目的）会把自己定义成「未抬升」**。
   实证：todo 面板未重绑，派生出来的检查**一直是绿的**。
4. **测的是陈旧产物**（`B-13:82`）：`WorkspaceBrowser.module.css` 从来不进 `apps/web/dist`，
   只重跑 `build:web` 的负控制跑的是陈旧 bundle，**声明被删掉也通过**——
   「这读起来像一个空洞的测试，而不是一个无效的控制」。且 **CI 从未暴露，只有本地脚本暴露。**
5. **上限在没有超过它的内容时不可证伪，而模型会替你把测试数据优化掉**（`B-21:38`）：
   第一次录制把「alpha 重复 400 次」变成了 `printf 'alpha %.0s' {1..400}`——一条**什么也证明不了**的单行命令。
6. **解析器拍平结构导致其余断言全绿**（`B-13:66`）：at-rule 被拍平后，
   「gate 被删掉、或一条声明被挪到 gate 另一侧」时文件里其他每条断言都还是绿的，因此额外加**按源码偏移量断言路径划分**。

另有一条**同步点选错让竞态测试自己变成假的**（`B-06:29`）：崩溃 harness 等待
**预期的 marker 内容**而不是路径存在，「这样『先 open 后 write』的可见性就不会让 kill 提前触发」。

### ⑤ 证据 / 留痕相关的 bug

按「证据链的哪一环坏了」分：

- **写进了错误的位置**：`B-04`（追加写到别人的会话里）。修法是**两次独立断言**——后端一次、协调器一次
  （同 `S-32:24` 「两道检查是故意的」）。
- **没地方可写**（`S-04:11`，本轮最尖锐的一条留痕漏洞）：
  > a turn can be durably closed before a live `agent/turn-end` listener runs,
  > so a post-boundary listener failure has **no valid in-log position left and must be reported out of band.**

  ——不是没记，是**持久边界已经关闭之后，日志里已经没有合法位置能放它了**。
- **写了但内容被遮蔽**（`B-03`）：`error.cause` 链被 `error.message` 吞掉，
  而被遮蔽的消息**继续留在会话日志——那是一次 turn 内失败的唯一持久记录——以及主界面里**。
  否掉的备选正是「只做一个 cause 感知的 logger exporter」，理由是**持久的 `turn/end` 原因与 TUI 提示不是日志行**。
- **状态被折叠成两态，「未知」消失了**（`B-06:21`）：崩溃修复区分
  `TOOL_NOT_STARTED`（可重试）/ `TOOL_OUTCOME_UNKNOWN`（只允许只读或幂等重试，且**指示模型先核实外部状态或问用户**）。
  **三态而不是两态，「未知」是一等状态。** 且明写 `Harness 不声称通用的 exactly-once 效果`。
- **被丢弃的尝试不可见**（`B-08:36`）：重试必须留下持久 `llm/retry` 事件，
  但**被丢弃的那次尝试没有 ACP 输出**——可见于证据、不污染输出。
- **「可观测」与「可参与结论」没分开**（`B-09:15`）：后代 `session.event` 可观测，
  但只有 `sessionId` 等于被请求根的事件才进 `TurnResult.events`，「不允许一个子代响应替换根响应」。
- **按形状猜类别，而不是按声明识别**（`B-17:33`）：
  > Recognize a checkpoint by shape … it reads **a coincidence of today's producers** instead of a declared contract,
  > and any future producer that replaces a range with a user message **would silently inherit the compaction marker.**
- **格式变了但版本没 bump，于是无法在 header 层面区分**（`B-12:9`）——直接对照 `D-012`。
- **证据从展示层反解**（`S-19:15`）：每个渲染行直接拿到值与属性路径，
  `so copy actions never recover application data from rendered DOM text.`
- **命名夸大了持久事实**（`S-35:29`）：
  > The dispatch precedes the model request and cannot establish that an assistant answer exists or was read.
  > **Naming it delivery would overstate the durable fact.**
- **口径来自「看起来权威」的自算公式**（`S-22:27`）：
  > A hard-coded provider-neutral estimate **would look authoritative while being wrong**; provider usage is the authoritative accounting source.
- **散文式上下文被下游当成授权**（`S-36:31`）：
  > A prose snapshot is **model-visible evidence, not a typed package seam.**
- **不确定时不复用**（`B-11:33`）：未匹配的记录、冲突映射、长度变了的数组、
  同时含语义与易变变化的字符串、畸形消息——**一律用新值，而不是冒险复用错位的数据**。

---

## §C.1 该借鉴

| # | 借鉴什么 | 出处 | 落地点 |
|---|---|---|---|
| C-A1 | **抽样/排序/截断的口径必须随结果一起呈现**：超上限时页脚明说「这是跨条目抽样而不是修改时间头部」，并报告触及了多少个顶层条目；只要 spill 成功，**完整排序列表保留在 artifact 里** | `B-10:15-17` | ~~**`未落地`**~~ → **部分落地 2026-08-23**（`LANDING-BACKLOG` L-2，`ARCHITECTURE` §8.5.2）：证据指针必须携带**取数口径三元组**（抽样方式 / 排序键 / 截断位置）且被下游强制消费——**已落**；`EVAL_CASES §3.3` 那条判据（引用截断页而未声明口径记失败）——**仍未落** |
| C-A2 | **同一事实的多个结构表示是「可静默分叉的真相源」，必须收敛到一个** | `S-04:9`、`S-08:14`、`S-15:11` | **已落地（方向）** —— `D-016`（映射表 schema 单一权威）。**但「同一口径不得在两处独立维护」这条可机械检查的规则 `未落地`** → 应落到 `D-015` 的 AST 测试：同名口径常量只允许一个定义点 |
| C-A3 | **审计字段豁免「零读者⇒可删」**：`durable audit timing is useful independently of a current reader` | `S-08:24`、`S-09:15` | **已落地（方向）** —— `D-003`。**但把它写成一条可执行的删除禁令 `未落地`** → 应落到 `D-003` 增补：证据链字段的删除必须单独立项，不适用「无消费者即死代码」的清理规则 |
| C-A4 | **删除的边界是「所有能让它复活的入口」，不是那个类**；bug 侧实证：**堵路径不等于堵能力，serve 模式本身必须失败** | `S-11:11`、`B-15:31` | **`未落地`** → 应落到 `D-017` 增补：排除 `eval()` 不只是不调用它，而是**不留任何能到达求值的入口**（含三方库的 YAML `!!js` 方言，见 C-A5），并由 `D-015` 的 AST 测试强制 |
| C-A5 | **schema 校验通过 ≠ 安全**：`entryListSchema` 的方言含 `!!js`，`"shape-checked text" was still arbitrary code on the next mount` | `S-32:9` | **已落地** —— `D-017`。这是 D-017 目前最强的一条**外部实证**（对方是踩到之后才删的）。**把它补进 D-017 依据栏的动作 `未落地`** |
| C-A6 | **不给默认，逼显式选择，配错则在加载时失败**：`sampleOverCapGlobResults` 必须显式配置，「没有任何产品级证据能确立其中一种顺序是隐含契约」 | `B-10:23` | **`未落地`** → 应落到 `D-018` 增补：口径类开关（口径版本、抽样策略、单位换算）**不设默认值**，缺失即在读入边界 fail-closed，而不是取一个「合理默认」 |
| C-A7 | **`?? {}` 把「没配置」变成「配了一个空对象」**，可选特性因此默认开启 | `S-21:13` | **`未落地`** → 应落到 `rules/failure-modes.md` 新增一条（与 F-2「只有真实字段能诚实触发才声明 flag」同族）：**空对象/空列表兜底会把「未声明」读成「已声明为空」**，配置读入处禁止 `?? {}` / `or []` |
| C-A8 | **「未知」是一等状态**：`TOOL_NOT_STARTED` / `TOOL_OUTCOME_UNKNOWN` / 完成，三态而不是两态；未知态**指示模型先核实外部状态或问用户** | `B-06:21` | **部分落地** —— `ARCHITECTURE §8.2`（`Refusal` 封闭枚举）+ `§8.3`（`completed_degraded`）已是三态骨架。**但「抽取尝试过但结果未知」与「未抽取」的区分 `未落地`** → 应落到 `§8.2` 增一个枚举值，并在 `EVAL_CASES §5.0` 与 `UNPARSEABLE` 并列 |
| C-A9 | **按声明的类型识别，不按形状猜**：`isCompactCheckpointSource` 是接缝自己的契约；按形状识别读的是「今天的生产者恰好长这样」这个巧合 | `B-17:19,33` | **`未落地`** → 应落到 `D-016`：抽取记录的类别由**显式 `kind` 字段**判定，禁止用「看起来像三大表某一行」这类形状启发式反推 |
| C-A10 | **命名不得夸大持久事实**：`Naming it delivery would overstate the durable fact`；分派 ≠ 投递，可见 ≠ 被读 | `S-35:29` | **已落地（方向）** —— `D-003` + `ARCHITECTURE §8.3`（`completed_degraded` 就是拒绝夸大）。**但「状态名必须是它能证明的那件事」这条命名规范 `未落地`** → 应落到 `§8.2` 的枚举命名约束 |
| C-A11 | **权威源逐条指名，自算公式只能是估算**：`A hard-coded provider-neutral estimate would look authoritative while being wrong` | `S-22:27`、`S-24:19` | **已落地（方向）** —— `D-013`（数值以年报 PDF 原文为准）。**但「估算值与记账值必须分字段、估算值不得进入证据链」`未落地`** → 应落到 `AC-05`（字段有真值）相邻：派生指标必须标 `derived` 并携带其输入字段的指针 |
| C-A12 | **把「以后新增的也必须遵守」写成自动发现 + 拒绝的测试**，而不是 README 里的约定 | `B-18:13`、`B-13:23`、`S-27:17` | **已落地（方向）** —— `D-015` 的 AST 测试就是这个形态。**但「新增数据源/新增口径必须被测试自动发现」`未落地`** → 应落到 `D-015` 扩一条：遍历数据源注册表，拒绝任何未声明口径版本的条目 |
| C-A13 | **让环境不能决定判定结果**：`-browse` 钉死、Playwright 固定 `Asia/Shanghai` | `S-26:36`、`S-36:37` | **已落地** —— `D-012`（评测集冻结）+ `D-021`（开发期 CI 不算部署基础设施）。作为 D-012 的正面同型实证 |
| C-A14 | **负控制**：把守卫删掉、重新构建、重跑，断言**必须变红**；否则你测的是一个空洞的东西 | `B-13:76` | **部分落地 2026-08-24**（`LANDING-BACKLOG` L-5 / L-48）：程序侧已落进 `rules/commands.md`（造回归 → 看红 → 回退），机械侧落成第六道门的 R2（每道门禁必须具名声明负控制且该负控制自己会红）。**`EVAL_CASES §3.3` 的判据编号仍未落**——且与 ch09 的证据 id 检查争 `J-5`，须分配两个号 |
| C-A15 | **验证之前先确认你测的是刚构建出来的产物**；`CI 从未暴露，只有本地脚本暴露` | `B-13:82` | **`未落地`** → 应落到 `rules/commands.md`：冻结校验与门禁命令前置一步「确认被测对象是当前工作树产出」，并在 `rules/failure-modes.md` 记为「陈旧产物导致的假通过」 |
| C-A16 | **从现状派生的覆盖检查，永远查不出「被遗漏的那一类」** | `B-13:27` | **`未落地`** → 应落到 `rules/failure-modes.md` 新增一条：覆盖率/完整性检查的**基准集合必须独立于被检查物**（不得从「已经处理过的字段」反推「应处理的字段」）。与 F-3「如实标注读得少 ≠ 读过」同族但更硬 |
| C-A17 | **不确定时不复用**：未匹配、冲突映射、长度变了的数组、同时含语义与易变变化的字符串 —— 一律用新值 | `B-11:19,33` | **已落地（方向）** —— `D-018`（fail-closed 在读入边界）。**「证据对齐失败时不得部分复用旧指针」这条 `未落地`** → 应落到 `ARCHITECTURE §8.4` |
| C-A18 | **保证的措辞削到实现真能满足的强度**：「至多一个 turn」而不是「恰好一个」；`Harness 不声称通用的 exactly-once 效果`；`缓存复用是尽力而为，正确性不是` | `S-10:17`、`B-06:21`、`B-05:23` | **`未落地`** → 应落到 `PROJECT_SPEC` 的验收标准措辞审查：每条 `AC-xx` 标注它是**保证**还是**尽力而为**，并写清失败时的可观测后果 |
| C-A19 | **「重新引入的门槛」作为删除记录的固定一节**：要回来必须带一个具名消费者 + 它自己的失败/生命周期/重放/测试契约 | S-11/S-22/S-23/S-25/S-28/S-29/S-33/S-37/S-39/S-43/S-44 共 11 篇 | **`未落地`** → 应落到 `D-009`（三方法论减法触发）：OpenSpec 归档模板增加「重新引入条件」必填节 |
| C-A20 | **「有报错」不等于「报对了」**：装配后确实 fail loud，但错误点名的是消费者不是配错的提供者；因此加**加载期守卫**直接报出责任方 | `S-41:13,22` | **`未落地`** → 应落到 `ARCHITECTURE §8.3`（拒绝留痕）：`Refusal` 必须携带**责任方标识**（哪个数据源 / 哪条口径规则拒绝的），不能只说「证据不足」 |

## §C.2 该刻意不借（每条写理由）

| # | 不借什么 | 出处 | 理由 | 落地点 |
|---|---|---|---|---|
| C-N1 | **策略层的 fail-OPEN 默认**：策略通过带 `undefined` 默认值的事件贡献，插件缺席时每个 intent 落到「无条件裸 provider 写/编辑」 | `S-06:90,127` | 他们把这当作「策略是可插拔层」的代价，并明写后果（默认策略下后续 edit 以 `FS_NOT_OBSERVED` 拒绝，「这个失败是显式的、有文档的」）。**方向与本项目相反**：他们缺策略时的代价是一次编辑走了裸路径；我们缺口径/证据时的代价是**一条无证据的结论被当成答案**。可插拔性不值这个价 | **已落地** —— `D-018` + `ARCHITECTURE §8.4`。本条作为**反向对照**补进 D-018 依据栏，该补充动作 **`未落地`** |
| C-N2 | **「静默但写进文档」作为可接受形态**：启动器不校验产物新鲜度，陈旧包可静默提供旧浏览器代码，配套做法是写进 onboarding 与 CLI 参考 | `S-45:17,32` | 对开发者工具，「文档 + 显式两条命令」是合理取舍。**对证据链不成立**：读者不读我们的 README，他读的是那条答案。陈旧口径必须在**读入边界**被拒，而不是在文档里被预告 | **已落地** —— `D-018` + `D-012`。**但「文档不能替代闸门」这条明文 `未落地`** → 应落到 `rules/pitfalls.md` 新增一条（接在第 11 条「不可逆压缩」之后） |
| C-N3 | **不闩住第一个后台错误**：保留失败批次但允许重试，「可观测性与重试两者都保住」 | `S-15:27-33` | 他们的取舍在「确定性」与「可恢复性」之间，选了后者，因为丢的是一次持久化写。本项目的**闸门是批次级**（`D-018`），一批里出现证据写入失败时**必须闩住这一批**，否则重试成功的部分与失败的部分会混进同一次回答 | **已落地** —— `D-018`（闸门批次级）。**「重试不得跨闸门批次」这条 `未落地`** → 应落到 `ARCHITECTURE §8.4` |
| C-N4 | **脱敏/口径在消费时求值，而不是在追加时固定**：「脱敏在 feedback 时求值……feedback 之前的一次脱敏策略变更会影响那次重放」 | `S-30:17,29` | 他们诚实标注了这个语义差异，对遥测可接受。**对可复核证据不可接受**：同一条证据在两个时间点复核会得到不同结果，`D-012` 的冻结就失去意义 | **`未落地`** → 应落到 `D-012` 增补：口径版本号必须**随抽取记录一起冻结**，复核时按记录里的版本求值，而不是按当前配置 |
| C-N5 | **匹配不到任何行的 patch 保持 no-op 而不是报错**（他们明写这是有意的，因为个人 overlay 要跨多个面共享） | `S-21:43` | 前提是「多面共享」。本项目的映射表是**单一权威**（`D-016`），一条匹配不到任何字段的映射规则只可能是写错了。同样是 no-op，他们那里是设计，我们这里是缺陷 | **`未落地`** → 应落到 `D-016`：映射表加载时**零命中的规则即加载失败**（同 C-A6 的「配错则在加载时失败」） |
| C-N6 | **靠匹配上游错误措辞做分类**（`terminated` / `stream ended before message_stop` → `TRANSPORT`） | `B-07:15,35` | 他们自己写死了残留风险：`a future pi-ai release that rewords these errors would silently fall back to PI_AI_ERROR`，并留了 `XXX` 与 Known-Limitations。**这个处置方式（承认 + 留锚点 + 写限制）该学**，但**分类本身不能用在证据链上**：`UNPARSEABLE` 之类的归因若依赖 PDF 文本措辞，上游排版一变就静默退回「正常」 | **部分落地** —— `EVAL_CASES §5.0` 的 `UNPARSEABLE` 已存在。**「归因分类不得依赖上游可变措辞」这条判据 `未落地`** → 应落到 `EVAL_CASES §5` |
| C-N7 | **被取消的提案直接删除，而不是保留成 active 或 rejected 记录**（只把动机、放弃的能力、重新考虑的条件合并进本篇） | `S-44:21` | 他们的做法在「笔记体系自洽」这个前提下成立（`S-15:7` 的自我标注、`S-37:21` 的动机继承都是配套机制）。本项目 `openspec/changes/` 的归档记录**本身就是产物**——决策轨迹要能被外部复核，删提案会让「为什么当初没这么做」变成不可复核的 | **已落地（方向）** —— `D-009`（OpenSpec 走 archive 而非删除）。**但「归档提案必须写清放弃了什么能力」这条 `未落地`** → 应落到 `D-009` 的归档模板（与 C-A19 合并做） |

## §C.3 小结

- **该借鉴 20 条**：已落地 **2** 条（C-A5、C-A13）；
  已落地（方向）但依据/规则待补 **6** 条（C-A2、C-A3、C-A10、C-A11、C-A12、C-A17）；
  部分落地 **1** 条（C-A8）；**明确 `未落地` 11 条**
  （C-A1、C-A4、C-A6、C-A7、C-A9、C-A14、C-A15、C-A16、C-A18、C-A19、C-A20）。2+6+1+11 = 20。
- **该刻意不借 7 条**：已落地 **3** 条（C-N1、C-N2、C-N3，依据栏待补本轮实证）；
  已落地（方向）**1** 条（C-N7）；部分落地 **1** 条（C-N6）；**`未落地` 2 条**（C-N4、C-N5）。3+1+1+2 = 7。
- **合计 27 条，其中 `未落地` 13 条**；另有 6 处属于「已落地但依据栏该补本轮实证」。

**最该先做的三条**（别处读不到，且都能直接变成可执行的检查）：

1. **C-A1 → `ARCHITECTURE §8.5` 的口径三元组**。`B-10` 是本轮唯一一条
   「工具成功、结果正确、模型结论错」的完整病例，而年报抽取里
   「取前 N 行 / 按某列排序 / 页内截断」与它逐项同构。
   §8.5 目前只要求「证据指针必须被下游强制消费」，**没有要求指针说明它是怎么被选出来的**。
2. **C-A16 + C-A15 → `rules/failure-modes.md` 两条新失败模式**。
   `B-13` 一篇里同时给出「从现状派生的检查只能确认已知」和「陈旧产物导致的假通过」，
   而后者**只在本地脚本暴露、CI 从未暴露**——这正是本项目「声明完成前必须跑验证命令」最容易被绕过的缝。
3. **C-A6 + C-N5 → `D-018` / `D-016` 的「加载即失败」**。
   `S-21:13` 的 `?? {}` 与 `B-10:23` 的「不给默认」是同一枚硬币的两面：
   **凡是能被「合理默认」填上的口径开关，都会在某天以「看起来正常」的形式错下去。**

---

# §L 阅读台账（READ-LEDGER）

**语料**：`…/scratchpad/deepseek-harness/.agents/notes/`，commit `47f9438`。
本文所有 `S-nn` / `B-nn` 的行号均绑定该 commit 下对应文件。

| 目录 | 英文 `.md` 总数 | 正文写了条目的篇数 | 条目编号 |
|---|---:|---:|---|
| `implemented/simplification` | 46 | **46** | S-01 … S-46 |
| `implemented/bug-fix` | 76 | **24** | B-01 … B-24 |

计数命令（在语料根 `.agents/notes/` 下执行，本次会话实跑）：

```
ls implemented/bug-fix/*.md | grep -v '\.zh\.md$' | wc -l                                            # -> 76
ls implemented/bug-fix/*.md | grep -v '\.zh\.md$' | sed -n '/hover-popup-pointer-grace/,$p' | wc -l   # -> 53
```

> **⚠️ 覆盖表与正文条目数的差额，如实记在这里。**
>
> 本文开头的覆盖表写「`implemented/bug-fix` 76 篇本轮读 75 篇全文」，
> 但**正文只写到 `B-24`（`2026-07-30-hover-popup-pointer-grace.md`）**，
> 按文件名排序其后还有 **52 篇没有正文条目**。
> 上一轮 agent 在写完 B-24 之后中断，没有写 §C 与本台账。
>
> **2026-08-23 这一轮只补写了 §C 与 §L，没有读那 52 篇，也无法核实它们是否被读过。** 因此：
>
> - `implemented/simplification` 的 **46/46 有逐篇正文条目，可核对**；
> - `implemented/bug-fix` 的**可核对覆盖是 24/76**，其余 52 篇状态为 **UNVERIFIED**；
> - §C 的全部结论**只从 S-01…S-46 与 B-01…B-24 提炼**，未使用无条目篇目。
>
> 若要补齐，下一轮的范围就是 `2026-07-30-hover-popup-pointer-grace.md` 之后的那 52 篇。
