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

### 组 B：`testing/`（22 篇；本节先落 5 篇全文精读的高价值篇目）

主题 6（「声称通过但实际没证明」）在这一组里最密集，而且**这个仓库自己把它当成一类专门的失效模式在治理**。

---

#### B-1 `implemented/testing/2026-06-19-real-api-e2e-ci.md`（100 行，全文）
**主题 6 的「镇馆之宝」＋ 主题 2（fail-closed）**

- `:9` **他们的标准反例（standing proof）**：
  > 「a no-key suite proves the plumbing but not the product, and the
  > [ACP inject postmortem](docs/postmortem/0001-acp-default-export-drops-inject.md) is the standing proof —
  > **178 keyless tests stayed green while a real ACP client session crashed instantly.**」

  > **这是第五个外部实例，也是量化最清楚的一个：178 个测试全绿 ↔ 真实会话瞬间崩溃。**

- `:11` **「自跳过的套件」是假绿的制度性来源**：
  `test:e2e` 用 `describe.skipIf(!process.env.DEEPSEEK_API_KEY)` 自跳过，
  「so adding it there **would report green without exercising the real suite**」。
- `:44` **对策：把「跳过」变成「响亮失败」**（小标题原文就叫 *Preflight: fail loud, never false-green*）：
  > 「a deleted/renamed/misconfigured secret would make `test:e2e` skip every real suite and report all-green —
  > **a silent regression of the entire safety net**. The guard turns "secret missing" from an
  > **invisible false pass** into a **visible failure**.
  > **(Its correctness was verified live: the run before the secret existed failed at exactly this step.)**」

  > 括号里那句是全篇最该学的：**他们验证了守卫本身**，并且把「守卫被真实触发过」这件事写进了记录。
  > 「我加了一个防假绿的守卫」本身也是一个需要证据的断言。

- `:59` **显式记录覆盖缺口，不假装覆盖**：
  > 「The DeepSeek native `web_search` probe is **registered but skipped**. The live endpoint can return a
  > successful response **without** structured source blocks, so its positive-source assertion is
  > **not a reliable merge signal**; unit coverage still pins response parsing, but
  > **CI does not prove the live source-block wire shape.**」

  > 对应 README 里「named coverage gap」是删除笔记前必须逐项保留的东西之一——
  > **覆盖缺口在这个体系里是一等公民，有名字、有位置、不许被沉默。**

- `:38` 一条容易忽略的机制细节：**job-level `if:` 跳过会报告为「成功」的检查**
  （与 workflow/trigger-level 跳过不同，后者会一直 pending）。所以「绿」可能来自三种完全不同的原因：
  真跑通了 / 被 job-level 跳过 / 套件自跳过。**「绿」不是单一含义。**
- `:91`/`:92` Alternatives 记了两条被否决的：把带 secret 的 job 塞进 `ci.yml`（否决：
  「different lifecycles, different files」）、去掉 `pull_request` 触发器（否决：为了 pre-merge 信号，
  并把接受的暴露面分析写进 Security 段）。
- `:98` 明确写出**这篇笔记是「改触发器或翻可见性之前必须重读的地方」**，而不是让后人重推 fork/secret 模型。

---

#### B-2 `implemented/testing/2026-07-30-web-browser-snapshot-ci-gate.md`（35 行，全文）
**主题 5 ＋ 6 —— 找到了「断言机制被改成生成器」的精确命名**

- `:13` 决策：`run-gates.ts` **显式注入 `DSH_SNAPSHOT=replay`**，
  「**CI never runs in `record` or `refresh` mode**, so when the committed goldens disagree with the
  currently assembled application, the tests **fail directly instead of silently rewriting them on the
  runner and then passing**.」
- `:27` **被否决的方案（本篇最值钱）**：
  > 「**Run CI in `refresh` mode and then check the working tree.** Rejected:
  > **checking after writing turns the assertion mechanism into a generator**;
  > if the working-tree check is wired incorrectly, it **can turn a regression into a passing
  > expected-output update**. Replay compares the existing goldens directly and has a
  > **smaller failure surface**.」
- `:25` 另一条否决：「Continue requiring only local runs. Rejected:
  **execution depends on developer memory**, which is precisely why stale goldens drift across PRs」。
- `:9` 问题描述本身就是一个假绿机制：PR 改了用户可见输出但没刷 golden → **仍然绿**；
  等到后面某个分支跑 `refresh` 时，它**回填了前一个改动**，产生一份与该分支无关的 diff。
  → **假绿不仅是「没发现问题」，还会把问题的归属搬到无辜的后续变更上。**
- `:31` 第四条否决：「Replace real Chromium with jsdom snapshots. Rejected: jsdom does not cover the
  browser, HTTP/SSE carriage, or the composition of real client plugin bundles.」
- `:35` Consequences 里仍然自陈缺口：「The gate still **makes no claim of cross-platform browser consistency**」。

> **对 finaudit 的直接输入（评测/黄金样本设计）**：
> 1. 评测跑批**永远不能带「刷新期望值」的模式**；刷新只允许人在本地显式做，且要 review 每一条 diff、
>    再以只读模式复跑一遍确认无写入（`:17` 就是这么规定的）。
> 2. 「先写再校验工作区」这条路**已经被走过并被否决**，理由是它把断言器变成了生成器。
>    finaudit 若打算做「跑完自动更新 EVAL_CASES 期望值 + 校验 git diff 为空」，这就是那条死路。

---

#### B-3 `proposed/testing/2026-06-11-mutation-testing.md`（36 行，全文）
**主题 6 —— 直接点名了「Agent 写的测试」这个特定风险**

- `:9`：
  > 「The per-file **100% coverage gate** proves every line *executes* under test —
  > **not that any assertion would notice if the line were wrong**.
  > **Under agent-written tests, coverage pressure can produce execution-without-assertion.**
  > Mutation testing measures what coverage cannot: whether the suite *kills* deliberately injected bugs.」
- `:16` 阈值政策：**只许收紧**（「thresholds only ever tighten」），先记录基线再棘轮上调。
- `:18` **等价变异体（equivalent mutants）必须带理由注解豁免**，与 `/* v8 ignore */` 同政策——
  即「这条我豁免了」也必须留下为什么。

> **可搬**：finaudit 的判据体系里，「覆盖率/通过数」这类**执行型指标**必须配一个
> **杀伤型指标**（注入已知错误，看判据是否拒绝）。否则判据只证明代码跑过，不证明它会挑错。
> 这一条正好补上 A-2 暴露的洞（「判据 = 现有测试仍通过」不构成证据）。

---

#### B-4 `implemented/testing/2026-06-11-property-based-testing.md`（29 行，全文）
**主题 6 ＋ 4（类型 vs 运行时）**

- `:11`：「a block-assembly ordering bug **once survived 100% line coverage of the happy paths**.
  Per-file 100% coverage proves every line ran, **not that every interleaving is correct**.」
- `:7` 与 `:25` **给出了真实战果**（不是「应该有用」）：属性测试**首跑就发现**了
  BlockAssembler 重复 `block-end` 覆盖已完成块的真 bug，已修并配了回归测试。
- `:19` **主题 4 的一个具体做法**：`dsh-tools` 的属性测试断言的是
  「**编译期 schema 声明 ↔ 运行时 `validateArgs` ↔ `InferArgs` 三者的组合**」——
  生成的合法参数必须通过运行时校验，定向破坏（删必填键、顶层非对象）必须被拒。
  原文：「This closes the **compiler/validator/`InferArgs` drift risk**.」
  → **类型与运行时校验会各自漂移；要用测试把两者钉在一起，而不是假设它们一致。**
- `:26`：「A property flake from a timeout is **a finding, not something to retry away**.」
- `:15` 自陈未落地部分：夜间 100× 迭代的 job **没有 ship**，明写「remains possible future work」。

---

#### B-5 `proposed/testing/2026-06-11-deterministic-and-stress-testing.md`（33 行，全文）
**主题 6**

- `:9` 三条问题，第三条尤其对口：
  > 「the inbox wakeup race was **verified by hand exactly once; nothing re-verifies it continuously**.」
  第二条：核心架构承诺（任何 session log 重放得到相同派生历史）**只在两个测试里断言过**，
  而它「cheap to assert *everywhere*」。
- `:16` 对策：**通用重放夹具**——每个测试跑完后自动把 session log 重放进新 Session 并断言
  `deriveMessages()` 相等，于是「The invariant then gets checked **hundreds of times per CI run**
  across every scenario the suite produces, **not twice**」。
- `:17`：「**any flake found is a bug to fix, never a retry**」。
- `:15`：禁止测试里用 wall-clock `setTimeout`，用 lint 规则强制（允许清单外一律禁）。

> **可搬**：finaudit 的「证据链可独立复核」是同一类**全局不变量**。
> 不要只在两三个用例里断言它，而要做成**每个用例跑完自动复核一遍**的夹具，
> 让不变量的验证次数随用例数增长。

---

### 组 C：fail-closed / 拒绝建模 / 证据字段的核心篇目（6 篇全文）

---

#### C-1 `implemented/architecture/2026-07-06-timeout-deadline-library.md`（116 行，全文）
**主题 3（超时建模）＋ 4（类型 vs 运行时）＋ 5**

- `:19` **它刻意不是一个 service**：「a library of **pure functions**, **not** a cordis service or plugin:
  it takes no `ctx`, **registers nothing, holds no cross-call state, and emits no events**.
  There is deliberately **no central "timeout service" that would have to know how to stop every capability's work**。」
- `:75` **嵌套超时的归因**：`timeoutOf(signal, code)` 用 `code` 把分类**限定到本层的计时器**，
  「so an **outer nested deadline is treated as upstream cancellation rather than the inner capability's timeout**」。
  → **「谁超时了」必须能归因到具体层，否则外层超时会被误记成内层失败。**
- `:88` 超时 code 归各能力自己所有：`WEB_FETCH_TIMEOUT` ≠ `BASH_TIMEOUT`（**不是一个通用 `TIMEOUT`**）。
- `:90` **为什么 file read/write/edit 不接受 `timeoutMs`**（主题 3 里最锋利的一条）：
  > 「a local syscall is **best-effort-abortable at most**, a timeout **could not force `fsync`/`rename` to stop**,
  > and adding one would be an **implicit default that violates explicit-over-implicit**。」
  → **不提供一个无法真正生效的旋钮。** 这与 finaudit failure-mode #2（假 flag）同构。
- `:114` **最有价值的被否决方案**：
  > 「A `withTimeout(promise, ms)` wrapper instead of a signal factory. Rejected because racing a promise
  > against a timer **resolves the *tool-call* promise on deadline without stopping the underlying work** —
  > the child process or fetch socket **leaks on**. Handing out a signal and requiring the capability to
  > listen is what **forces a real termination path to exist**.
  > This mirrors the "**dispose must reach quiescence, not just request it**" defensive rule.」
  → **「超时了」≠「停了」。** 一个只返回超时结果的实现是假的。
- `:110` 另一条被否决：统一的 `ctx.timeout` service —— 会让共享层「知道每种能力怎么终止工作」，
  即「the **kernel knows too much**」。Codex 的 `ExecExpiration` 只作用于 exec 家族，正是同一个理由。
- `:100`/`:101` **两个字段设计判据**：
  - 原来 `timedOut` / `aborted` 两个布尔**独立锁存**，可以同时为真；现在互斥，只报**第一个**中止原因。
    **归因的单一性是设计选择，代价是丢失「两者都发生了」这条信息**——写在 Consequences 里，没藏。
  - `SpawnSpec.timeoutMs` / `SpawnOutcome.timedOut` / `aborted` **被删掉而不是留成恒 0 / 恒 false 的残迹**：
    「**An always-0 field read by nothing is dead weight**」。
- `:13` + `:106` **诚实的缺口标注**：`web_search` **根本没有超时**，并在 Consequences 里
  「Out of scope, **named to mark the boundary**」显式点名。

---

#### C-2 `implemented/bug-fix/2026-08-09-filesystem-absence-observation.md`（36 行，全文）
**主题 1 ＋ 2 ＋ 3 —— 本次普查里与 finaudit failure-mode #1（不许下「没有 X」的断言）最直接对应的一篇**

标题本身就是结论：**「Filesystem absence is an observation」**——「不存在」是一个**观测结果**，不是默认值。

- `:15` **显式的观测联合类型**，落进 `fs/observed` 事件：
  ```
  { kind: 'present', version: FsVersion } | { kind: 'absent' }
  ```
  且规定得极细：成功的读与变更发 `present`；`read` / `view` / `str_replace` / `insert` 的
  **元数据 miss** 在返回 `FS_NOT_FOUND` **之前同步**发 `absent`；
  > 「**Other read failures do not manufacture absence.**」
  → **权限错误、IO 错误 ≠ 不存在。只有「确实查了且确实没有」才能产出 absent。**
- `:17` **三态而不是两态**（本篇最该搬的一条）：
  | 状态 | 含义 | write 映射 | edit 映射 |
  |---|---|---|---|
  | map 里没有条目 | **unseen（没看过）** | `createIfAbsent` | `FS_NOT_OBSERVED` |
  | `absent` | **confirmed absence（看过，确认没有）** | `createIfAbsent` | `FS_NOT_FOUND` |
  | `present(version)` | 有，且带版本 | `replaceIfVersion` | 版本守卫 |

  注意 write 把 unseen 与 absent 映射到同一意图，但 **edit 给出两个不同的错误码**——
  「没看过」与「确认没有」在需要区分的地方就必须区分。
- `:25` **被否决**：「Delete the cached version when a read returns not found. Rejected because it
  **conflates unseen with confirmed absence**, cannot give edit the correct `FS_NOT_FOUND` result,
  and **erases the state transition the event is meant to communicate**.」
- `:27` **被否决（证据的适用范围）**：「Let `replaceIfVersion` create when its target disappeared.
  Rejected because **a positive observation is evidence for replacement, not creation**;
  silently changing that provider intent would bypass the required missing reread。」
  → **一条证据只支持它实际支持的那个结论，不能顺手扩用。**
- `:28` **主题 2 最重要的反向证据——fail-closed 不是无条件正确**：
  > 「**Keep the deleted-target dead end fail-closed. Rejected because the model-facing
  > recovery instruction is then false** and a normal external cleanup cannot be recovered within the session.」
  → 原来的行为是「一直拒绝」，看起来很 fail-closed，**但它给出的补救指引（「重读文件再重试」）照做也恢复不了**。
  **当 fail-closed 让对外承诺变成假的时候，正确做法是补上缺失的状态转移，而不是死守拒绝。**
- `:21` **不夸大保证**：「This decision **does not claim** cross-process linearizability for `replaceIfVersion`…
  The **narrower guarantee is exact and sufficient** for absence recovery: guarded creation never
  clobbers a target that appears before publication.」
- `:19` fail-closed 的落点被移到**发布点而不是探测点**：「Every provider must enforce `createIfAbsent`
  **at the publication point, not only at its initial probe**」——因为两步之间有跨进程竞态。

---

#### C-3 `implemented/architecture/2026-08-09-cordis-event-walk-backstop.md`（38 行，全文）
**主题 2 ＋ 5 ＋ 6 —— 「守卫本身会静默失效」**

- `:9`–`:11` 问题：services 有一条**独立的 AST 扫描**作 backstop，events **没有**。
  结果 12 个已声明的 event「**vanished with no trace**」，而且
  「**nothing would ever notice a thirteenth**」。
  更狠的是：那条本来就是为了防止静默消失的扫描，自己的 glob 只匹配 `packages/*/*/src/*.ts`，
  **漏掉了嵌套目录，于是 13 个 Context key 对它不可见**。
  → **守卫有盲区，而且盲区是静默的。**
- `:17` **对策：加第三个分区方向来守卫扫描自身**：
  > 「every rendered service key and event name **must also be visible to the scan**,
  > so a **scan regression (glob, prefilter, block walk) is a hard error rather than a silent backstop decay**.」
  「**silent backstop decay**」这个词组直接可以进 finaudit 的词表。
- `:19` **fail-closed 是双向的**：未豁免的不可见 event、给已渲染 event 的豁免、
  以及**没有任何声明对应的豁免**，三种都是 hard error。→ **豁免清单过期本身就是错误。**
  同时否决了 scope 级豁免（会静默吞掉未来的 host-face event）。
- `:33` **被否决（对 finaudit 的独立复核最关键）**：
  > 「Deriving exhaustiveness from Typert instead of a raw AST scan.
  > **The projection and the backstop must fail independently**: a Typert reachability bug is
  > precisely what the backstop exists to catch, so the scan deliberately stays a plain
  > `ts.createSourceFile` walk **with no shared machinery**.」
  → **复核者与被复核者不得共用机制，否则共同的 bug 会同时骗过两边。**
- `:27` **`## Verification` 段是真验证，不是声明**：
  > 从真实树里**删掉一条在用的豁免** → 生成器 fail loud 并报出 event 名与声明文件；
  > 恢复后重跑得到**字节相同的空操作（85 artifacts, 0 written）**，
  > 「which **also proves the new exemptions exactly cover today's surface**」。
  → **「重跑产出字节相同、写入 0 个文件」是一条可复用的、廉价的证据形式。**
- `:34` 另一条被否决，注意措辞：「Gating the transitive type closure of rendered signatures.
  **Measured before deciding**: every type name reachable in rendered signatures is already classified」
  —— **先测量再否决**。

---

#### C-4 `implemented/architecture/2026-06-14-session-persistence.md`（36 行，全文）
**主题 1（证据落盘）＋ 2**

- `:22` **正典日志 vs 派生视图**：不许过滤 chunk，因为 `seq = log.length` 与 `events[i].seq === i`
  要求日志**逻辑上连续**，过滤会留洞。
  > 「A chunk-filtered projection is possible later **as a derived view with its own renumbering,
  > but it is NOT the canonical log**.」
  → **精简版可以有，但它是派生物；正典必须无洞。**
- `:23` **append-only 的 fail-closed 边界划得非常清楚**：
  > 「**Only an incomplete final record is discarded** during committed repair;
  > **a parse error or sequence gap at or before the last real `turn/end` is corruption
  > and makes the session unloadable.**」
  → 尾部半条记录可容忍（写到一半崩了）；**中间的解析错误或序号缺口 = 损坏 = 拒绝加载**。
  这是「什么时候降级、什么时候拒绝」的一条可直接照搬的判据。
- `:23` 崩溃修复**明确标注为合成物**：补的是 `{ kind: 'interrupted' }` 的 `turn/end` 和
  「**risk-classified** error results」——即合成内容带风险分类，不伪装成真实结果（与 A-3 呼应）。
- `:24` **同一份契约测试跑在两个实现上**：SQLite 后端「passes the **same `runPersistenceContract` suite**
  as the JSONL backend… expressed **once over file bytes and once over rows**」。
- `:25` **元数据出日志**：格式版本、cwd、血缘属于存储关注点，「**metadata is not replayable state**」，
  放在 `SessionHeader` 里，**永不进 `SessionEventMap`，永不到 `deriveMessages()`**。
  显式否决了「in-log `session/meta` 作为第 0 行」。
- `:32` 「cold reads **reject any non-current version**」；同时诚实标注局限：
  append-only + flush「**not robust to fsync-less power loss mid-line**」。

---

#### C-5 `implemented/architecture/2026-07-30-config-plane-boundaries.md`（41 行，全文）
**主题 2（fail-closed 的定义）＋ 5 ＋ 6**

- `:13` **一个被点名的类别错误**：`trustedHosts` 只挡写不挡读，于是 LAN 客户端能读到全部配置。
  > 「That fence is a **DNS-rebinding defense and says so**;
  > treating it as an **authorization boundary for reads was a category error**.」
  → **一个防护措施只防它声称要防的东西；拿它当别的边界用就是错。**
- `:15` **实测复现的破坏性 bug（主题 6 的变体）**：编辑器读的是**脱敏后**的描述符
  （按构造省略 `role('secret')` 字段），清空一个字段时它用这份脱敏副本**重建整节**并发 `settings.replace`，
  于是「a stored literal `apiKey` **the wire had never returned** was deleted as a side effect.
  **Reproduced directly: `{baseURL, reasoning}` in, `apiKey` gone.**」
  → **拿一个不完整的视图做整体替换 = 静默删掉你看不见的东西。**
  且当时「nothing carried a version, so two tabs editing one namespace **silently overwrote each other**」。
- `:25` **对策的措辞值得整句抄**：
  > 「**A caller with a partial view names the field it means.**」
  改为 `set`/`unset` 路径 op，客户端 diff「打开时的快照」与「草稿」，只提及自己看得见的字段：
  > 「a secret absent from both sides produces **no op and survives by construction, not by care**.」
  **「by construction, not by care」**——靠结构保证，不靠小心。
- `:27` **「Staleness is detected, not ordered away.」** 每个命名空间带单调 `revision`，
  写入可带 `expectedRevision`，不匹配就以 `SettingsConflictError` 拒绝并**附上两个 revision**；
  编辑器收到冲突后**让用户重新打开，而不是重放自己的快照**。
  → 序列化写队列能保证顺序，但**顺序不能区分「新写入」和「重放旧快照」**。
- `:29` **值相同但含义不同也是一次变更**：`settings/updated` 只在**解析后的值**变化时发；
  另设 `settings/document-updated (ns, revision)` 在**原始节**任何变化时发，因为
  「a configuration surface must learn that a field went **from inherited to overridden
  (same resolved value, different meaning)**」。
- `:37` **fail-closed 在这里被定义得最清楚**，而且是「已知缺陷不半修」的示范：
  作者逐条列出 redaction 的 5 个真实缺口（union/intersection/transform 后的 secret 原样返回且
  `secrets` 列表为空；`schema.toJSON()` 带出 secret 字段的 `.default(...)`；
  写拒绝消息回显的 schema 文本可能引用输入；客户端用 `new Function` 复水信封；
  pi-ai 的纯字符串 `headers` dict 可以合法地装 `Authorization`），然后：
  > 「**All real, all deliberately left for a fail-closed `describeForWire()`
  > that refuses a schema it cannot prove safe.**
  > They are recorded as `TODO(settings-wire-redaction)` and in the owning READMEs'
  > **Known Limitations rather than half-fixed here**.」
  → **fail-closed 的操作定义：拒绝一个自己无法证明安全的输入**（而不是尽力脱敏后放行）。
- `:35` 被否决：区分「未注册」与「已注册但未暴露」——诊断更好，但会变成**命名空间枚举 oracle**；
  「The **uniform answer is deliberate**.」→ **错误消息的信息量本身是攻击面。**

---

#### C-6 `implemented/architecture/2026-07-31-claimed-pre-step-inbox-lifecycle.md`（41 行，全文）
**主题 3（拒绝建模）**

- `:17` **拒绝是封闭联合的一支**：
  `PreStepDecision = { kind: 'reject' } | { kind: 'enter'; messages: UserMessage[] }`。
  Reject「opens **no step**, leaves the claimed batch **removed**, and closes the turn as
  **blocked without any step events**」——拒绝有自己的终态（blocked），不是「什么都没发生」。
- `:15` 拒绝之前先做**原子认领**（`Inbox.claim`），且在初始边界**先提交 `turn/start`**，
  「so the claim and its single `agent/pre-step` decision have **durable turn ownership**」。
  → **决定「拒绝」这件事本身也要有归属和落盘位置。**
- `:31` **被否决**：「Let rejection requeue the claimed batch. This preserves retry-like behavior but
  **turns a veto into hidden queue mutation**, duplicates later work unless every race is fenced,
  and **prevents claim from being an atomic ownership transfer**.」
  → **拒绝不得产生隐藏的状态变更。** 被拒的输入保持「已移除」，由调用方显式重投。
- `:33` **被否决（同一事实只能有一个权威载体）**：「Put placement and outcome on every live event.
  **Durable splices already own those facts. Repeating them on live notifications
  creates a second contract that can drift**」。
- `:19` 语义区分做到了操作层：普通移除记 `outcome: 'canceled'` 并发 `discarded`；
  **认领记的是「纯删除，无 outcome」**——因为认领不是取消。
  替换（`replace`）**先发旧消息 discarded、再发新消息 inserted**，因为替换可以改变身份。

---

## 4. 对 finaudit 的具体输入

（逐组读完后追加）

---

## 5. 未读清单（我不能置评的部分）

（最终填写）
