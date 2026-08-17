# deepseek-harness `.agents/notes/**` 系统性普查

> 目的：`.agents/notes/**` 是 deepseek-harness 全部设计决策的「为什么」存放地。
> 本文对其做**系统性覆盖普查**（不是关键词打捞），按六个主题抽取对 finaudit-agent 有用的输入。
>
> 仓库快照位置（只读）：`.../scratchpad/deepseek-harness`
> 普查日期：2026-08-18

---

## 1. 完整清单与覆盖度（第一等产物）

### 1.1 总数是怎么数出来的

```
find .agents/notes -type f            → 1985 个文件
find ... -name "*.md" ! -name "*.zh.md" → 679 个英文正文文件
```

1985 与 679 的差额来自**每篇笔记的三元组**：每个 note 都有
`X.md`（英文）+ `X.zh.md`（中文镜像）+ `X.i18n.yaml`（一致性记录 sidecar）。
中文与 sidecar 是同一决策的翻译/哈希记录，不是独立笔记。
**因此本普查的分母 = 679。**

679 里有 5 个不是 Agent Note 本体（`README.md` ×2 语言体系文件、
`AGENTS.md` ×3、`implemented/CLAUDE.md` ×1 —— 实际为 4 个 AGENTS/CLAUDE + README），
其余 **674 篇是带 `# Agent Note:` / `Status:` 头的正式笔记**。

### 1.2 按目录分布（英文正文，679）

| 目录 | 篇数 |
|---|---|
| `.agents/notes/`（README / AGENTS） | 2 |
| `archived/`（AGENTS.md） | 1 |
| `archived/architecture` | 14 |
| `archived/bug-fix` | 19 |
| `archived/feature` | 54 |
| `archived/process` | 20 |
| `archived/simplification` | 27 |
| `archived/testing` | 8 |
| `implemented/`（AGENTS.md + CLAUDE.md） | 2 |
| `implemented/architecture` | 125 |
| `implemented/bug-fix` | 76 |
| `implemented/feature` | 169 |
| `implemented/process` | 69 |
| `implemented/simplification` | 46 |
| `implemented/testing` | 12 |
| `proposed/architecture` | 9 |
| `proposed/feature` | 4 |
| `proposed/process` | 7 |
| `proposed/simplification` | 2 |
| `proposed/testing` | 2 |
| `rejected/feature` | 1 |
| `rejected/simplification` | 10 |
| **合计** | **679** |

### 1.3 覆盖度（分三档，如实标注）

<!-- COVERAGE-TABLE -->
（本节在普查过程中逐组更新，见文末 §5「未读清单」）

---

## 2. 体系本身：Agent Note 制度的设计（读自 `.agents/notes/README.md`，全文）

在进入六个主题之前，必须先记录**这套笔记制度本身**的设计——它就是一个
「决策证据链」系统，与 finaudit 要做的「答案证据链」同构。

- **路径即元数据**：`{lifecycle}/{class}/yyyy-mm-dd-topic-title.md`。
  生命周期（proposed / implemented / rejected / archived）与类别（feature / bug-fix /
  simplification / architecture / process / testing）**都编码在路径里**，
  且 class 是**封闭集合**，由 `scripts/agent-note-tree.ts` 定义，
  「classification gate rejects other folders」——即目录结构本身是被 gate 强制的封闭枚举。
- **`Status:` 行三选一**，且**必须与所在目录一致，gate 交叉校验**：
  `proposed` / `implemented` / `rejected — <一行理由>`。
  只有 rejected 这一种 status 带内容，理由是
  「a rejected Agent Note's verdict is the fact readers come for」。
- **`## Alternatives considered` 是强制段**：
  「A decision recorded without what it beat invites re-litigation — the failure Agent Notes exist to prevent.」
  且**「Alternatives are recorded, never invented」**——2026-07-05 格式化之前、
  确实无法从记录重建备选方案的老笔记，必须写死这一行注释：
  `<!-- agent-note-format: alternatives-not-recorded (pre-format Agent Note) -->`，
  gate 只对旧文件放行。**这是「不许编造证据、宁可显式标注缺失」的制度化实例。**
- **归档 = 冻结 + 哈希**：`archived/` 一旦封存**永久冻结**，
  由 `scripts/verify-archived-agent-notes.ts` 校验
  「封闭 class 树、完整三元组、归档元数据、**sidecar 哈希**、**append-only 冻结内容 manifest**」。
  归档时只允许四种内容改动（移动三元组、保留 `Status: implemented`、
  插入 `Archived: YYYY-MM-DD`、重录 sidecar 并修复入链），别的一律不许。
  且明确规定：**归档笔记「不得作为当前行为的依据」**（`do not treat it as authority for current behavior`）。
- **删除的前置条件极重**：一篇 implemented 笔记只有被完全取代才可合并删除，
  且删除前 owner 必须**逐项保留**：每一条 rationale、alternative、consequence、
  required verification、named coverage gap；修复每一条入链；同步删中文与一致性记录。
  「**Consolidation must not rewrite the old file into its opposite or rely on git history as the only copy of rationale.**」
  —— 即 **git history 不算证据留存**。
- **没有 INDEX**：显式拒绝集中式索引（`implemented/process/2026-07-19-remove-generated-agent-note-index.md` 拥有该理由），
  理由是活的目录树本身就是清单。

> 对 finaudit 的直接映射：证据链目录结构、口径枚举、
> 「备选方案必须记录、不可编造、缺失要显式标注」、
> 「归档件冻结+哈希+append-only manifest」、
> 「历史版本控制不算证据副本」——这五条都可以直接搬。

---

## 3. 六个主题的命中篇目

### 组 A：`rejected/`（11 篇，全部全文读完）

这是任务里点名「最有价值」的一类，实际确实最密集。逐篇记录。

---

#### A-1 `rejected/simplification/2026-07-26-dependency-swaps-rejected-by-nih-audit.md`（78 行，全文）
**命中主题 5（被否决的方案）＋ 1（证据落盘理由）＋ 3 ＋ 4**

这是整个 `notes/` 里最重要的一篇——它是**「否决记录本身为什么要落盘」的元决策**。

- `:9`：一次全仓库 NIH 审计（2026-07-26，十个并行 survey）问每个手写实现「换成外部包能否净简化」。
  正面结论各自成了 proposed note。然后是关键句：
  > 「The negative verdicts carry **equal value** — each names a plausible-looking swap whose hand-rolled shape is load-bearing — but would otherwise **live only in a PR body**. This note freezes them.」
- `:13`：**再提门槛写死**——
  > 「a future proposal for any item must **beat its recorded reason**, not just re-cite the policy.」
- `:76`（Alternatives）：
  > 「Record nothing and let the PR body carry the verdicts. Rejected: **PR bodies are not part of the maintained record**, and the whole point of surveying is that the next audit starts from these verdicts instead of re-deriving them.」
- `:77`：**否决了「一项一篇」**——~30 篇仪式性文件，共享同一套证据标准与同一个结局；
  只有当某项带新证据被重提时才拆出单篇。
- `:78`：**否决了「折进各自 seam 的 note」**——部分做了（retry / token-meter / schema DSL / zstd /
  sandbox / node-pty 这些有 owning note 的改为**引用而不复制**），剩下的没有 owner 才记在这里。

其中几条对主题 3、4 直接有用：
- `:26` **超时建模**：`p-timeout` / `AbortSignal.timeout` 被否决，理由是
  「the builtin **cannot be disarmed early** and carries a **generic `TimeoutError`, not the capability-coded `TimeoutReason`** that distinguishes nested deadlines」。
  → **通用超时错误 vs 带能力编码的封闭原因枚举**，后者才能区分嵌套 deadline。
- `:36` **运行时校验 vs 类型**：zod/valibot 被否决用于 durable-event 解码器，因为现有是
  「**exact-key fail-loud decoders at durable boundaries** with event-specific messages」；
  换库是政策变更不是删代码。
- `:34` `structuredClone` 被否决替换 `snapshotJsonValue`/`isJsonValue`，因为后者是
  「a **validator + detacher** enforcing the lossless-JSON boundary with **single-read-per-getter and cross-realm intrinsic checks**；
  `structuredClone` accepts Map/Date/-0 and **enforces nothing**」。
  → 「看起来等价的内置函数什么都不校验」。
- `:46` `shell-quote` 被否决：「**a safety boundary is the wrong place to save one line**」。
- `:47` `strip-ansi` 被否决，理由含一条实测：`stripVTControlCharacters`
  「**demonstrably leaks** unterminated-OSC payloads the session-title normalizer must strip (anti-spoofing)」。

---

#### A-2 `rejected/simplification/2026-07-26-builtin-timer-promises-for-hand-rolled-sleeps.md`（37 行，全文）
**命中主题 6（声称通过但实际没证明）—— 本次普查找到的最干净的一个实例**

- `:3` Status：
  > 「rejected — **implementation (PR #679) falsified the parity premise**: vitest's fake clock does not intercept `node:timers/promises`, so the swap costs deterministic fast tests for ~10 deleted lines」
- 提案自己在 `:19` 写「behavior is **identical**, including timer clearing on abort」，
  在 `:33` 把验收判据写成「test suites pass **unchanged** (behavioral parity)」，
  在 `:36` Risks 写「**Essentially none**: no model-visible output, no platform concerns, no new dependency」。
- 三处都断言了等价，**没有一处是实测**。真去实现才发现假清（fake clock）根本不拦截该模块。

> **这是第四个外部实例，且模式与前三个不同**：前三个多是「测试没真正覆盖」，
> 这一个是「**把『等价』写进验收判据，但判据本身依赖一个未验证的前提**」。
> 判据写成「测试不改就能过」看似严格，实际上当假设错误时它是**先失败于实现、而不是先失败于判据**。
> 对 finaudit 的直接教训：**A-4 这类「判据 = 现有测试仍通过」的写法不构成证据**，
> 因为它没有独立于被改动的前提。

---

#### A-3 `rejected/simplification/2026-06-20-truncate-interrupted-turns.md`（36 行，全文）
**命中主题 1（证据字段必需性）＋ 2（fail-closed）—— 对 finaudit 价值最高的一篇**

提案：崩溃后加载只保留最后一个完整 turn，丢弃未闭合的尾巴。**被否决。**

- `:3` Status：「a single turn can contain substantial real work…Preserving interrupted turns is
  preferable to **silently dropping that tail** on load.」
- 但提案的 Problem 段 `:11` 提出的批评被**部分采纳为约束**：
  > 现有修复路径「**invents events that never happened**. A synthetic tool result is useful because it
  > makes provider history valid, but it also means the resumed log contains **model-visible text that no tool produced**.」
- `:30` 的结论是本篇最值钱的一句：
  > 「A future "recover partial crashed work" feature should be designed as an **explicit user-facing recovery view**,
  > **not as synthetic events silently inserted into the canonical transcript**.」

> **对 finaudit 的直接输入**：证据链里出现的「补齐/推断/兜底」内容，
> 必须走**显式的、标记过的恢复视图**，绝不能以与真实观测同形的记录静默混入。
> 这两条张力（不许静默丢 / 不许静默造）同时成立，答案是**显式标注**，不是二选一。

---

#### A-4 `rejected/simplification/2026-06-20-drop-durable-step-boundaries.md`（32 行，全文）
**命中主题 1（为什么某字段必需）**

提案：删掉 `step/start` / `step/end`，因为每个 step 级事件都已带 `{turn, step}`，边界事件可推断。**被否决。**

- `:11`：「`step/end` is **concrete information**: a reader can tell whether a model request
  **finished, crashed, or is being repaired** without deriving that state from the next event.
  A bare `step/start` is likewise useful for a model request that **began but produced no chunks before failing**.」
- `:30`：「The log no longer records "a model request started but produced no event before the process died"
  as a durable fact… **That loss is not acceptable while the session log is the durable replay and audit surface.**」

> **判据**：一个字段是否冗余，取决于「**没有它时，某个真实状态是否还能被区分**」。
> `{turn, step}` 能表达「这些事件属于同一步」，但**不能**表达「这一步开始了但什么都没产出就死了」——
> 后者恰恰是失败态。**审计面的存在本身就抬高了字段的必需性门槛**（这句是显式写出来的理由，不是我的推论）。

---

#### A-5 `rejected/simplification/2026-06-20-assembled-assistant-messages-only.md`（36 行，全文）
**命中主题 1**

提案：只存组装好的 `assistant/message`，不存逐 token 的 `assistant/chunk`。**被否决。**

- `:3`：「Dropping chunks is only viable with a **no-information-loss replay/artifact replacement**.」
- `:11`：正常可恢复的会话状态确实不需要 chunk；**但失败/中断的流不同**——
  「partial assistant output **may exist only as chunks**, and empty max-token steps may produce **no `assistant/message` at all**」。
- `:30`：「That is **too much information loss** for the current resume, load, and snapshot contracts.」

> **规律与 A-4 同构**：成功路径上冗余的字段，在**失败路径上是唯一证据**。
> 判断字段能否删，必须**先枚举失败态**再看覆盖，不能只看 happy path。
> 这条对 finaudit 的抽取层证据设计直接适用（例：抽取成功时页码+表格 id 足够，
> 抽取失败/部分失败时可能只有原始 span 能说明发生了什么）。

---

#### A-6 `rejected/simplification/2026-06-20-drop-bash-output-spill-files.md`（31 行，全文）
**命中主题 1（证据必须是一等产物）**

提案：删掉大输出溢写文件，只留截断尾巴。**被否决**，但**否决理由带条件**：
「A future artifact/blob service may generalize it, but dropping spill files **before that replacement** would lose useful command output.」

- `:11` 的批评被保留为设计债：
  > 「A spill path is a **process-local filesystem artifact exposed to model output**,
  > **not a durable harness artifact with scoped access, retention, or UI affordances**.」

> **对 finaudit**：证据产物的合格标准 = **有 ownership、有 retention、有权限范围、有渲染方式**。
> 一个临时目录里的文件路径不算证据，哪怕内容是对的。
> 同时注意这里的**替换先行原则**：不许在替代品到位前先删旧证据通道。

---

#### A-7 `rejected/simplification/2026-07-12-collapse-workflow-to-foreground-core.md`（39 行，全文）
**命中主题 5 ＋ 直接命中 finaudit 自己的 failure-mode #2（假 flag / 假枚举）**

提案：砍掉 workflow 的整套进度观测系统（六个 `workflow/*` 事件、`phase()`、`log()` 等），
因为**零生产消费者**。**被否决**，理由是「Workflow progress is an intentional observation API;
make it useful **through a consumer** instead of deleting it.」

但它的 Problem 段是一份极精准的「假抽象」诊断，值得整段引用其结构：

- `:11`：**「The progress vocabulary is not merely unused; it cannot serve its only named future owner without redesign.」**
  证据是具体的：`WorkflowRunInfo` 只有 `{id, meta}`，**没有 parent agent / session / tool-call 身份**，
  而模型可见的工具从不暴露 run id ——**所以一个全局 ACP listener 根本无法把事件路由到正确的 client session**。
  `meta.phases` 从不被查询，`phase(title)` 也不对它校验。
- `:17`：**`WorkflowError.fatal` 的诊断**：
  > 「every production construction is fatal, **`fatal: false` exists only in tests**,
  > and combinators already distinguish workflow failures with `instanceof`.」

> **这正是 finaudit `rules/failure-modes.md` 第 2 条的外部实例**：
> 「只有真实字段能诚实触发时才声明 flag」。
> 这里给出了两个可机械执行的识别判据：
> **(a) 某个枚举值/布尔分支只在测试里被构造过 → 它是假的；**
> **(b) 某个观测字段缺少把观测结果路由回主体的身份信息 → 它的唯一 named owner 用不了它，
> 即使将来接上也得重设计。**
> 判据 (b) 尤其可搬：finaudit 的证据字段要自检「**这条证据能不能被独立复核者定位回它的主体**」。

---

#### A-8 `rejected/feature/2026-07-26-evaluate-landstrip-for-windows-sandbox-rung.md`（34 行，全文）
**命中主题 2（fail-closed）＋ 5**

- `:3` Status：「landstrip is **not battle-tested**（days-old single-maintainer project, ~48 GitHub stars at rejection）;
  **a security-invariant dependency must have proven adoption**」。
- `:18`：评估必须回答的问题之一是「Denial and runner-failure stderr dialects, and
  **fail-closed exit-code classification**, need **explicit mapping into the chain's vocabulary**」。
  → **fail-closed 不是一个布尔开关，而是「外部失败信号如何映射进本系统的封闭词表」这件事必须先做完。**
- `:20` 与 `:25` 的对照很关键：**已建成的 Linux 档位「do not swap it」**（安全不变量已结算），
  **未建成的 win32 档位才是 genuinely open question**。
  → 「已经付过代价并被验证的选择」与「还没建的选择」适用不同的重评门槛。
- `:29` 验收判据要求评估**先落盘**（probe / dialect / license / source repo / release process / binary build 六项答案）
  再写实现，且 go/no-go 要写回 sandbox note 的 deferred-phases 计划。

---

#### A-9 `rejected/simplification/2026-07-12-prune-unused-skill-registry-api.md`（29 行，全文）
**命中主题 5，含一条重要的「不许下『没有 X』断言」的方法论**

被否决（「Direct runtime skill registration is an intentional extension path for third-party plugins」）。
最有价值的是 `:15` 提案作者**自己给自己划的证据边界**：

> Agent-scoped system-prompt sections、tool providers、variables 明确排除在本提案之外，因为
> [agent-scope contributor contract] 允许它们在 `setup(agentCtx)` 期间通过 agent-owned context 注册，
> 所以「**absence of a fixed in-repo scoped registration is not evidence of non-consumption**」。

> **直接对应 finaudit 的 failure-mode #1**（不对操作者系统下「没有 X」的判断）。
> 这里给出了通用形式：**当注册路径是动态/外部的，仓库内搜不到调用点不构成「无消费者」的证据。**

---

#### A-10 `rejected/simplification/2026-06-20-fold-session-persistence-interface.md`（31 行，全文）
**命中主题 5（架构类，对 finaudit 弱相关）**

否决把 persistence 接口折回 `dsh-session`。`:29` 的自陈值得记：
「pre-release, the extra package looks like **abstraction before there is an external Consumer**」——
即否决方也承认提案的批评成立，只是权衡后保留边界。**Alternatives 未记录（pre-format 老文件）。**

---

#### A-11 `rejected/simplification/2026-07-19-fold-compaction-package-split.md`（37 行，全文）
**命中主题 5**

否决合并 compaction 的两个包。两条 Alternatives 都写了理由：
- `:23`：「**A possible future implementation does not justify the current package boundary.**」
  （注意：这条论证是**支持提案**的，但整体仍被否决——因为「更多 backend 已在计划中」，
  即「计划中」与「可能有」被区别对待。）
- `:25`：把 Service Definition 包改叫 `compaction-basic` 会让**主服务看起来像一个可选后端**——命名即契约。
- `:37` Risks 里写了**重评触发条件**：「acceptance should be revisited **if a second backend lands first**」。

> **可搬的机制**：否决/接受都附一个**明确的重评触发条件**，而不是无限期挂起。

---

## 4. 对 finaudit 的具体输入

（逐组读完后追加）

---

## 5. 未读清单（我不能置评的部分）

（最终填写）
