# deepseek-harness `.agents/notes/**` 普查 · 第二轮（proposed/ 全量 + implemented 主题筛选）

> 承接 `deepseek-harness-notes-survey.md`（第一轮：制度本身 + rejected 11 篇 + testing 5 篇 + fail-closed 6 篇）。
> 本轮阅读日期：2026-08-19。语料快照（只读）：
> `C:\Users\Kevin\AppData\Local\Temp\claude\C--Users-Kevin-Desktop-excel----------07-finaudit-agent\e42d96be-821c-4748-aada-cf8e97e4a4a6\scratchpad\deepseek-harness\.agents\notes`
>
> **语料版本（重要）**：本文与 `deepseek-harness-notes-survey.md` 的**全部行号引用**，
> 都指向该 clone 的 commit **`47f9438`**（全哈希
> `47f943859bef60e4160492346772ded9b24f765a`，由另一 agent 从 `.git/objects/pack` + reflog
> 取到并交叉验证）。**本轮结论引自该 commit。**
> 之所以要写死版本：这份语料在本项目里**已经丢失过一次**（`survey/` 目录连同
> `inventory.tsv`、`read-full.txt` 被清空），`路径:行号` 只有绑定到具体 commit 才能回指。
> 换 commit 后行号可能全部漂移，复核时请先 checkout 到 `47f9438`。
>
> **诚实标注约定**：每篇标「全文」= 从第 1 行读到最后一行；标「部分（Lxx–Lyy）」= 只读了该行段。
> 凡笔记原文没有写「Alternatives considered」的，一律写「原文未记录备选」，**不替作者补**。
> 引用格式 `路径:行号`，行号来自 `cat -n` / `sed -n` 的原始行号。

---

## 0. 本轮阅读清单（先给账，再给内容）

### 0.1 `proposed/`（24 篇正式笔记，其中 2 篇 testing 已在第一轮读过）

**结论：`proposed/` 24 篇已 100% 全文读完**（本轮 22 篇 + 第一轮 2 篇 testing）。
下表逐篇标注，标「全文」= 从第 1 行读到最后一行。

| # | 路径（相对 `.agents/notes/`） | 行数 | 读到什么程度 | 本文位置 |
|---|---|---|---|---|
| 1 | `proposed/architecture/2026-06-16-typed-event-schemas.md` | 75 | **全文** | P-A1 |
| 2 | `proposed/architecture/2026-07-24-domain-kv-storage-and-workspace.md` | 331 | **全文** | P-A2 |
| 3 | `proposed/architecture/2026-07-25-client-settings-locale-theme.md` | 130 | **全文** | P-A4 |
| 4 | `proposed/architecture/2026-07-27-session-projection-and-command-log.md` | 187 | **全文** | P-A3 |
| 5 | `proposed/architecture/2026-07-28-storage-root-and-derived-medium-recovery.md` | 59 | **全文** | P-A5 |
| 6 | `proposed/architecture/2026-07-29-durable-last-activity-index.md` | 67 | **全文** | P-A6 |
| 7 | `proposed/architecture/2026-08-08-cordis-web-dynamic-packages.md` | 270 | **全文** | P-A7 |
| 8 | `proposed/architecture/2026-08-08-semantic-composer-chain-phases.md` | 46 | **全文** | P-A8 |
| 9 | `proposed/architecture/2026-08-10-unary-apiproxy-remote-migration.md` | 124 | **全文** | P-A9 |
| 10 | `proposed/feature/2026-06-30-pre-tool-input-rewrite.md` | 53 | **全文** | P-F1 |
| 11 | `proposed/feature/2026-07-06-recallable-compaction.md` | 110 | **全文** | P-F2 |
| 12 | `proposed/feature/2026-07-08-interactive-side-sessions.md` | 41 | **全文** | P-F3 |
| 13 | `proposed/feature/2026-08-04-task-surface.md` | 289 | **全文** | P-F4 |
| 14 | `proposed/process/2026-06-11-api-extractor-reports.md` | 32 | **全文** | P-P1 |
| 15 | `proposed/process/2026-06-11-architectural-conformance.md` | 36 | **全文** | P-P2 |
| 16 | `proposed/process/2026-06-11-supply-chain-and-vendor-drift.md` | 35 | **全文** | P-P3 |
| 17 | `proposed/process/2026-06-20-discover-package-inventory.md` | 35 | **全文** | P-P4 |
| 18 | `proposed/process/2026-07-13-human-review-skill-maintenance.md` | 85 | **全文** | P-P5 |
| 19 | `proposed/process/2026-07-26-remove-packed-session-fixture-migrator.md` | 38 | **全文** | P-P6 |
| 20 | `proposed/process/2026-08-04-artifact-first-npm-baseline-publication.md` | 114 | **全文** | P-P7 |
| 21 | `proposed/simplification/2026-07-04-prune-dead-core-spine-api.md` | 63 | **全文** | P-S1 |
| 22 | `proposed/simplification/2026-07-19-make-jsonrpc-directional.md` | 46 | **全文** | P-S2 |
| 23 | `proposed/testing/2026-06-11-deterministic-and-stress-testing.md` | 33 | **全文（第一轮）** | survey B-5 |
| 24 | `proposed/testing/2026-06-11-mutation-testing.md` | 36 | **全文（第一轮）** | survey B-3 |

**「原文未记录备选」的篇目（带 `alternatives-not-recorded` 标记）**：#15、#17 两篇。
本文对这两篇一律写「原文未记录备选」，未替作者补。

### 0.2 `implemented/architecture` + `implemented/process` 主题命中篇目

这两个目录**不做全量**（125 + 69 = 194 篇，远超本轮预算），做**主题筛选**：
先用 `grep -ril` 在这两个目录里筛七个主题词族，再对命中篇目全文读。

七个主题（下表「主题」列用 (1)-(7) 指代）：
(1) 证据链与审计留痕 (2) append-only / 不可变追加 (3) 事件字段形状
(4) 拒绝如何建模为封闭类型 (5) 模块边界与「谁拥有某个事实」
(6) schema 与结构化字段 vs 自由字符串 (7) gate 在什么边界执行

**行数经 `wc -l` 实测**（commit `47f9438`）。「全文」= 从第 1 行读到最后一行。
**本表只列正文里真有条目的篇目**；本文档分批增写，每批先落正文再补本表。

#### `implemented/architecture`（本轮命中并读完 32 篇 / 共 125 篇；其中 31 篇全文、1 篇部分）

| # | 路径（相对 `.agents/notes/`） | 行数 | 主题 | 读到什么程度 | 本文位置 |
|---|---|---|---|---|---|
| 1 | `implemented/architecture/2026-06-11-event-sourced-sessions.md` | 28 | (2)(3) | **全文** | I-A1 |
| 2 | `implemented/architecture/2026-07-05-reconstructable-requests.md` | 55 | (1)(3) | **全文** | I-A2 |
| 3 | `implemented/architecture/2026-07-31-goal-owned-durable-events.md` | 33 | (2)(5) | **全文** | I-A3 |
| 4 | `implemented/architecture/2026-07-30-settings-write-path-integrity.md` | 35 | (5)(7) | **全文** | I-A4 |
| 5 | `implemented/architecture/2026-07-20-unified-json-value-schema-dsl.md` | 37 | (6) | **全文** | I-A5 |
| 6 | `implemented/architecture/2026-08-10-message-feedback-sidecar.md` | 43 | (2)(5) | **全文** | I-A6 |
| 7 | `implemented/architecture/2026-08-10-session-log-version-mechanism.md` | 30 | (2)(6) | **全文** | I-A7 |
| 8 | `implemented/architecture/2026-07-28-api-browser-trust-boundary.md` | 31 | (5)(7) | **全文** | I-A8 |
| 9 | `implemented/architecture/2026-08-04-configuration-source-ownership.md` | 73 | (5) | **全文** | I-A9 |
| 10 | `implemented/architecture/2026-07-30-session-end-seed-log-boundary.md` | 55 | (2)(5) | **全文** | I-A10 |
| 11 | `implemented/architecture/2026-07-02-tool-render-intent-union.md` | 82 | (4)(6) | **全文** | I-A11 |
| 12 | `implemented/architecture/2026-07-19-package-owned-invariant-service.md` | 105 | (5)(7) | **全文** | I-A12 |
| 13 | `implemented/architecture/2026-06-26-file-context-as-event-gate.md` | 173 | (3)(7) | **全文** | I-A13 |
| 14 | `implemented/architecture/2026-06-11-structured-error-taxonomy.md` | 26 | (4)(6) | **全文** | I-A14 |
| 15 | `implemented/architecture/2026-06-11-runtime-arg-validation.md` | 24 | (6)(7) | **全文** | I-A15 |
| 16 | `implemented/architecture/2026-06-11-microkernel-event-taxonomy.md` | 31 | (3)(5) | **全文** | I-A16 |
| 17 | `implemented/architecture/2026-06-11-content-block-vocabulary.md` | 28 | (3)(6) | **全文** | I-A17 |
| 18 | `implemented/architecture/2026-06-30-event-domain-semantics.md` | 39 | (3)(5) | **全文** | I-A18 |
| 19 | `implemented/architecture/2026-07-05-windows-jsonl-durable-publish.md` | 35 | (2)(7) | **全文** | I-A19 |
| 20 | `implemented/architecture/2026-07-19-zstandard-jsonl-session-logs.md` | 57 | (2)(6) | **全文** | I-A20 |
| 21 | `implemented/architecture/2026-07-26-packed-chunk-rows-by-default.md` | 59 | (2)(6) | **全文** | I-A21 |
| 22 | `implemented/architecture/2026-08-06-agent-event-payload-objects.md` | 27 | (3)(6) | **全文** | I-A22 |
| 23 | `implemented/architecture/2026-07-20-canonical-tool-output-contract.md` | 79 | (4)(6) | **全文** | I-A23 |
| 24 | `implemented/architecture/2026-08-11-repository-naming-contract-and-rename-ledger.md` | 386 | (1)(5) | **部分（`:1`–`:111` + `:340`–`:386`）** | I-A24 |
| 25 | `implemented/architecture/2026-07-28-identified-immutable-message-values.md` | 50 | (2)(3) | **全文** | I-A25 |
| 26 | `implemented/architecture/2026-06-11-dev-invariants-over-deep-readonly.md` | 60 | (2)(7) | **全文** | I-A26 |
| 27 | `implemented/architecture/2026-06-14-session-persistence.md` | 36 | (2) | **全文** | I-A27 |
| 28 | `implemented/architecture/2026-06-18-shared-persistence-write-coordinator.md` | 47 | (5) | **全文** | I-A28 |
| 29 | `implemented/architecture/2026-08-09-cordis-event-walk-backstop.md` | 38 | (3)(7) | **全文** | I-A29 |
| 30 | `implemented/architecture/2026-07-29-terminal-llm-stream-failures.md` | 37 | (4) | **全文** | I-A30 |
| 31 | `implemented/architecture/2026-06-20-branded-ids.md` | 69 | (6) | **全文** | I-A31 |
| 32 | `implemented/architecture/2026-06-21-mandatory-app-attribution-headers.md` | 82 | (1) | **全文** | I-A32 |

#### `implemented/process`（本轮命中并全文读完 17 篇 / 共 69 篇）

| # | 路径（相对 `.agents/notes/`） | 行数 | 主题 | 读到什么程度 | 本文位置 |
|---|---|---|---|---|---|
| 1 | `implemented/process/2026-06-11-quality-gates.md` | 30 | (7) | **全文** | I-P1 |
| 2 | `implemented/process/2026-07-26-frozen-agent-note-archive.md` | 45 | (1)(2) | **全文** | I-P2 |
| 3 | `implemented/process/2026-08-09-committed-artifact-citations.md` | 37 | (1) | **全文** | I-P3 |
| 4 | `implemented/process/2026-08-08-browser-gif-evidence-chain.md` | 37 | (1) | **全文** | I-P4 |
| 5 | `implemented/process/2026-08-09-concrete-prose-names-actors-and-recorded-facts.md` | 35 | (1) | **全文** | I-P5 |
| 6 | `implemented/process/2026-07-14-typescript-program-backed-semantic-gates.md` | 65 | (7) | **全文** | I-P6 |
| 7 | `implemented/process/2026-07-27-explicit-change-scope-report.md` | 41 | (1)(5) | **全文** | I-P7 |
| 8 | `implemented/process/2026-07-05-uniform-agent-note-format.md` | 30 | (1)(6) | **全文** | I-P8 |
| 9 | `implemented/process/2026-06-20-agent-note-classification.md` | 48 | (1)(5) | **全文** | I-P9 |
| 10 | `implemented/process/2026-07-19-require-agent-notes-for-non-trivial-changes.md` | 46 | (1)(7) | **全文** | I-P10 |
| 11 | `implemented/process/2026-07-19-remove-generated-agent-note-index.md` | 31 | (1)(5) | **全文** | I-P11 |
| 12 | `implemented/process/2026-07-06-parallel-pre-push-gates.md` | 41 | (7) | **全文** | I-P12 |
| 13 | `implemented/process/2026-08-06-coverage-uncovered-locations.md` | 42 | (1)(7) | **全文** | I-P13 |
| 14 | `implemented/process/2026-07-10-readme-known-limitations-gate.md` | 29 | (1)(7) | **全文** | I-P14 |
| 15 | `implemented/process/2026-07-30-cordis-config-source-plane-resolution-gate.md` | 27 | (5)(7) | **全文** | I-P15 |
| 16 | `implemented/process/2026-08-09-md-fragment-anchor-gate.md` | 32 | (7) | **全文** | I-P16 |
| 17 | `implemented/process/2026-06-20-core-data-structures-catalog.md` | 61 | (6) | **全文** | I-P17 |

**合计**：`implemented/` 本轮读完 **49 篇**（architecture 32 + process 17），
其中 **48 篇全文、1 篇部分**（I-A24，386 行的命名台账，只读了 Problem/Decision/
Alternatives/Verification/Consequences，中间 14 组逐条重命名映射表未逐行读）。
连同 `proposed/` 22 篇，本文正文共 **71 条**笔记条目。

**「原文未记录备选」的篇目**（正文中已按 `alternatives-not-recorded` 标记如实标注）：
I-A14、I-A15、I-A18 —— 共 3 篇，均为 2026-07-05 格式决策（I-P8）之前的旧笔记，
带原文的 `<!-- agent-note-format: alternatives-not-recorded (pre-format Agent Note) -->` 注释。
其余 46 篇原文均写有 `## Alternatives considered` 段，本文逐篇转录了被否决方案与理由，
**未替作者补写任何一条**。另有 I-A31 的「Out of scope / possible extensions」
按原文标注为**延后而非否决**（原文自称 "deferred with a reason, not a commitment"）。

**⚠️ 两篇与第一轮重复（如实记录）**：

| 路径 | 第一轮 | 第二轮 |
|---|---|---|
| `implemented/architecture/2026-06-14-session-persistence.md` | survey §3 **C-4** | 本文 **I-A27** |
| `implemented/architecture/2026-08-09-cordis-event-walk-backstop.md` | survey §3 **C-3** | 本文 **I-A29** |

第一轮的已读记录只存在于 survey §3 的散文里（机器可读的 `survey/read-full.txt` 已随语料丢失），
主题筛选按内容 `grep` 命中时没能自动排除它们。两份条目切入角度不同，都保留；
但在 `deepseek-harness-notes-survey.md` §1.3 的覆盖度计数里**只算一篇**
（两轮合并去重后全文读完 = **91 篇 / 674**）。

---

## 1. `proposed/architecture`（9 篇）

---

### P-A1 `proposed/architecture/2026-06-16-typed-event-schemas.md`（75 行，**全文**）
**标题**：Runtime schemas for the event vocabulary (Zod vs the merge-extensible-map pattern)
**命中主题**：schema / 结构化字段 vs 自由字符串；校验在什么边界执行

**它主张什么**：**推迟（Defer）**。不把事件词表从「编译期 merge-extensible map」改成「运行时 schema 注册表」；
如果确实要在**持久化边界**加运行时校验，只做 **Option B**——用仓库已有的 schemastery 校验那些**本来就封闭**的
header / metadata 形状，替掉手写 type guard，**不动可扩展事件联合体**。

关键论证（本篇最有迁移价值的一句）：

- `:20` **「a plugin cannot declaration-merge a Zod schema」** —— 声明合并是编译期机制，Zod schema 是运行时值。
  于是「给序列化加 Zod」这个看似局部的改动，**结构性地**升级成「全仓库把编译期词表换成运行时注册表」：
  > 「That registry — not the persistence backend — becomes the source of truth for the vocabulary,
  > replacing the merge-extensible interface.」
  → `:22`「So the real proposal is: **replace the compile-time merge-extensible-map pattern with a runtime
  schema registry, repo-wide.** That is a core-vocabulary redesign.」
- `:13` 现状的诚实描述：持久化把 `event.data` 当**不透明 JSON**，唯一的运行时守卫是 `isJsonValue`
  （只查「能否往返序列化」——拒 BigInt / 函数 / 循环 / 非有限数），**不是结构校验**。
  「A corrupted-but-still-JSON event datum (wrong field types, missing fields) **round-trips silently**
  and is only caught later, if at all, by a consumer's `switch`.」
- `:24`–`:35` **「Blast radius (measured)」**：不是"感觉很大"，是**数出来的**——6 张 merge 表（~370 LOC）、
  ~10 处 `declare module` 增补点、16 处 `session.append` 生产点、~7 个 switch 消费者、`defineTool` 的
  `InferArgs` DSL、以及 architecture.md 与相关 Agent Note。

**它否决了什么备选及理由**（原文 `:37`–`:56` 明写三个）：

| 备选 | 原文判定 | 理由（原文） |
|---|---|---|
| A. 维持现状：编译期 merge 表 + durable 边界 `isJsonValue` | 采纳为默认 | 零改动；插件扩展是一行 `interface` 增补，全类型推断，无运行时注册仪式；`defineTool` DSL 与 `assertNever` 穷尽性照旧。**代价：持久化边界与插件边界都没有运行时结构校验，畸形-但仍是-JSON 的数据被晚捕获**（`:43`） |
| B. 只校验封闭形状（schemastery），事件仍不透明 | **推荐的适度步骤** | 小、贴合既有约定（用仓库已有的 schemastery，不引第二个 schema 库）；把封闭形状上的手写 guard 换成声明式 schema；不动核心。缺点：**不解决 event-data 校验，只有固定元数据记录变好**（`:49`） |
| C. 整个词表上运行时注册表（Zod 或 schemastery） | 否决/推迟 | 全量 blast radius；**Zod 当前不是直接依赖**（只是 `@earendil-works/pi-ai` 的传递依赖），而仓库选定的 schema 库是 schemastery，「adopting Zod broadly is itself a dependency decision」；声明合并的人机工程（一行扩展 + 完整推断）被换成运行时注册 + 手工类型接线；**`assertNever` 穷尽性保证减弱——运行时变体不是静态穷尽的**（`:55`） |

- `:63` **验收判据本身就是一条流程门禁**：
  > 「Option C proceeds **only through its own implementation Agent Note, never as a persistence side effect**.」
- `:68` **风险栏诚实写下了被接受的代价**：「The deferral leaves event `data` structurally unvalidated at the
  durable boundary … the status-quo cost, **accepted deliberately**.」
- `:71`–`:75` Open questions 保留三条真问题：库选型（schemastery vs Zod，「Adopting two schema libraries is a
  cost in itself」）、能否混合（编译期推断 + **可选**运行时 schema，**只在持久化/线上边界校验，不在每次进程内 append 时校验**）、
  以及 `ctx.invariants` 是否已经覆盖到「只有真正不可信输入（外部改过的日志重载）才需要边界校验」。

> **对 finaudit 的可迁移点**：证据链事件如果只做「能序列化」校验，等于没校验；
> 但「全量上 schema」是**词表重设计**而不是序列化细节。原文给出的中间解是
> **只在 durable 边界、只对封闭形状做 schema 校验**（`:59`、`:74`）。

---

### P-A2 `proposed/architecture/2026-07-24-domain-kv-storage-and-workspace.md`（331 行，**全文**）
**标题**：Domain KV storage capability seam and the workspace entity
**命中主题**：谁拥有某个事实（单一权威载体）；模块边界与包拆分；schema 在边界校验；fail-closed 的位置

**它主张什么**：新建 `packages/storage/` 组——`ctx.storage` 注册中枢 + 两个后端（json / sqlite）+ 一个
domain 数据形态层 + `dsh-workspace` 消费者包。核心是把**介质（medium）**与**业务语义**切开。

**四条对 finaudit 直接有用的原则**：

1. **`:11` 「谁拥有某个事实」的判据**（本篇最锋利的一句）：
   > 「Ownership belongs to the workspace — **"which sessions belong to this workspace" is not any single
   > session's fact, so writing it into the session log is semantically wrong.**」
   → 事实归属靠**语义**判定，不靠"写哪儿方便"。
2. **`:L117`（原文第 117 行，Proposal §`dsh-domain` open 步骤 5）durable 边界单向校验**：
   > 「every record passes `valueSchema.parse` … A failure → `DomainError('invalid-record', { table, key })`
   > (**the durable boundary must validate; the write side does not re-validate**)。」
   → **校验只发生在一个边界**，不到处重复。
3. **`:L144` 版本不一致直接 fail-closed，不做兼容**：
   > 「**Version fails loud**: a stored version differing from the spec throws outright; **no migration,
   > no rebuild** (the data is not regenerable; pre-release rejects old formats)。」
4. **`:L145` 变更事件的字段形状约定**：「new snapshot + operation discriminant」——
   `DomainChanged` 是 put/deleted 的**判别联合**，put 分支带新快照，deleted 分支不带值，**一律不带旧值**。

**一致性教义（`:L250`–`:L255`，表格）** —— 每一行都是「不一致时怎么办」的封闭枚举：

| 情形 | 行为（原文） |
|---|---|
| 台账里的 id 在磁盘上没有对应 session | `list()`/实体投影处过滤；下次 mutate 时剪掉；**不报错**（删除崩溃一致性的正常产物） |
| 某 session 的 cwd 匹配某 workspace 但不在台账里 | **不算拥有：不合并、不收养。**（GUI 以后可以做「孤儿 session」区） |
| 一个 session 出现在两个台账里 | 写侧结构性阻止（attach 检查）；加载时检出 → **throw**（外部手改过的数据，**绝不掩盖**） |
| workspace 目录不存在 | 记录与台账保留；`status()` 返回 `'missing-dir'`；**存储层永不自动删除**（目录可能只是临时移走） |

**它否决了什么备选及理由**（原文 `:L305`–`:L317`，13 条，全部照录要点）：

| 被否决方案 | 理由（原文） |
|---|---|
| 复用 session-persistence 的 coordinator/backends | 事件日志语义（append-only、turn 崩溃修复、惰性物化）与 KV 覆写语义不匹配；只借「分层思想」 |
| 先做 workspace 专用存储包，以后再抽 seam | 第二个消费者（session sidecar）已可预见；**以后再泛化 = 动两次接口** |
| 把 domain 层与 storage 层合并 | 后端会被迫处理 schema 校验、变更事件、写序列化——都是 domain 关切；拆开后**后端只实现不透明原语（最小可替换面），domain 单实现集中全部领域逻辑（zod/事件/序列化只写一次，不按后端翻倍）** |
| JSON 后端做成 jsonl append + 墓碑 + 压实 | temp+fsync+rename 的崩溃安全等价于 append；**整写让文件始终是当前净状态、人类可读、无需折叠/压实/容忍半行**；在 domain 量级整写与追加一行成本相同 |
| JSON 每表一个文件 | 整写下文件粒度不影响写成本；按 domain 合并文件更少，且给 global 单例一个家 |
| SQLite 把整个 domain 存成一个 blob 行 | 任一记录改动都要重写整个 domain，**丢掉按键精确更新——SQLite 相对 JSON 的唯一优势归零** |
| SQLite 从 schema 生成类型化列 | DDL 生成器是过度设计；文档-每行足够，等真有查询需求再说 |
| 每个 domain 一个 sqlite 文件 | 违反仓库「一库多表」约定 |
| 全库单一后端选择（照抄 session-persistence 的单槽模式） | 否决——中枢会承载多种数据形态，其后端偏好（人类可读 vs 高频点更新）**注定分化**，单槽会逼出「全量换 + 手工迁数据」这种粗动作。代价只是多一次名字查找，由 fail-loud 兜底 |
| 用 path 当 workspace 主键 | 规范化/符号链接解析会重写 path；**引用锚点必须稳定** |
| 从 cwd 推导归属（或与台账合并） | **两个真相源**；cwd 无法表达顺序；归属本来就是 workspace 侧的事实 |
| 变更事件携带旧值 | 仓库约定是「新快照 + 操作判别式」；唯一例外（fs 的 before/after）是**方法返回值而非事件**，因为旧值事后不可恢复且有 diff 消费者；**需要 diff 的消费者自己持有上一份快照** |
| 删除时自动取消运行中的 session | 持久化/编排层反向伸回运行时会**弄脏分层**；cancel 已存在，调用方自己组合 |

**其它可直接搬的**：

- `:L188` **调用顺序被写成规则而不是建议**：「callers cancel first then delete —
  **the persistence layer never reaches back into the runtime**」。
- `:L190` **递归删除自下而上**：「a mid-way crash leaves only "half the subtree deleted, ancestors intact";
  **re-running the same delete converges**, and no dangling parent exists at any moment」——
  崩溃后重跑收敛，而不是补偿事务。
- `:L286`–`:L301` **「Out-of-scope list」是一张四列表：不做什么 / 触发条件 / 返工点 / 已铺的地基。**
  这是我在这个仓库里见过的最好的「范围外」写法——**每条不做的事都绑一个明确的重启触发器**，
  与第一轮 A-1 的「重评触发条件」同源。

---

### P-A3 `proposed/architecture/2026-07-27-session-projection-and-command-log.md`（187 行，**全文**）
**标题**：Session projections and command lifecycle logging
**命中主题**：证据链/审计留痕字段形状；append-only 事件落盘；单一计算点；schema 在边界

**它主张什么**：把「从会话日志派生的每会话状态」抽成一个**宿主侧投影注册表** `dsh-session-projection`，
并把**斜杠命令的生命周期本身写进日志**（`command/run` / `command/done`）。

**问题陈述里最值得抄的一句**（`:13`，这条几乎就是 finaudit 的证据链问题）：

> 「**Command results are unrecoverable.** … Nothing reaches the session log: a refresh, another tab,
> resume, or fork **loses the record that the command ever ran**. The domain *state* changes are durable
> …, but **the command invocation and its verdict are not**.」

→ **状态是持久的、但"谁在什么时候请求了什么、判定是什么"不是持久的**——这正是"有结果没证据"。

**几条硬规则**：

- `:23` **Whole-value event rule（整值事件规则）**：
  > 「A state-carrying log event **MUST carry the complete post-change state, never a bare delta**.」
  收益写得很具体：每个 domain 的转移都廉价、**值在线上自描述**、任何消费者都可以把最新推送值当作最终值
  ——「out-of-order immunity by seq comparison, **self-healing because a missed update is corrected by
  the next one**」。
- `:29` 注册的是**状态驱动的计算单元**（三个纯函数 + 声明），**不是不透明 getter**：
  「The framework owns driving it (subscription, watermark, caching, and later checkpointing);
  **the domain owns only the mathematics**。」
  契约见 `:34`–`:45`：`key` / `schema: ZodType<…>`（**「validates the payload before it leaves the host」**）/
  `init()` / `apply(state, event)` / `view(state)` / `stateVersion`。
- `:54` **「State is always computed, never logged.」** 日志只存事件；状态活在按会话的水位缓存里，
  后续再落一个持久化投影缓存 `(sessionId, key, ver, seq, val)`。
  > 「**A row is never wrong, only possibly stale — its `seq` says exactly how stale.**」
  唯一读法（冷热一致）：取缓存态（或 `init()`）→ 只前向重放水位之后的事件 → `view`。
  写策略：节流 + 两个**强制点**（`turn/end` 与 detach）；「A crash between writes costs a longer tail
  replay, **never a wrong value**。」
- `:71` **一致切面**：api-proxy 同步走一遍注册表，**全程无 `await`**，「so every key's value and `asOfSeq`
  form **one consistent cut**」。
- `:88` 客户端只有一条规则：**higher seq wins**。
  「Replayed baselines cannot roll a newer frame back; a lost frame costs **staleness until the next frame
  or baseline, never wrongness**。」
- `:119`–`:126` **命令留痕的字段形状**（直接对标 finaudit 的证据链事件）：
  ```
  'command/run':  { commandId, name, args?, source: CommandSource }
  'command/done': { commandId, kind: 'success' | 'error', text? }
  ```
  - 两个都是 **log-only（非 surface、模型不可见）**，形状**镜像 `tool/call`/`tool/result` 的配对**；
  - **不被 turn 包裹**（「turns describe model-loop executions only」）；
  - **commands 包自己的 invariant companion 强制 run/done 配对**；
  - **payload 是结构化的**：`name` 与 `args` 来自解析器自己的切分，
    「so a consumer … **never re-parses a line**」；
  - 一个命令若其权威领域事件已经拥有 payload，就设 `recordInput: false`，
    `command/run` **省略 `args` 而不是重复它**；
  - `text` 是 handler 的逐字结果，**「factual data of the same nature as `tool/result.content`,
    not presentation」**，如何排版仍在渲染期客户端计算——
    原文把这条叫 **红线：「presentation never enters the log」**。

**它否决了什么备选及理由**（原文 `:142`–`:168`，12 条，全部照录）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 专用 `session.projections` RPC | 需要新基线的时刻与拉取 tail page 的时刻**精确重合**；单独 unary 换来第二次往返、第二个要对齐的 seq、以及一个客户端「何时重取」的决策——rider 设计把这个决策**直接删掉** |
| 不透明的 `get(agent)` provider 契约 | 计算模型藏在 domain 内部 → 框架**永远无法 checkpoint、无法服务冷会话**（没有 agent、没有加载的日志，`get` 无从运行）、无法从日志中段恢复。注册 `(init, apply, view)` 把驱动权交给框架，domain 只剩纯数学 |
| 给 plan 的 pending 意图加 live-only 覆盖钩子 `live?(agent, base)` | 它**只因为「用户的 plan 选择没进日志」才存在**。把选择走标准命令通道后 `command/run` 上账，pending 变成纯重放量，投影契约保持恰好三个纯函数 |
| 注册 API 命名为 `registerFold` | 被单元契约取代：仓库里 `fold*` 指纯 `(events) => state` 辅助函数，而此注册表接受**带键、带 schema、带版本**的单元；projection 是事件溯源里读模型角色的既定术语 |
| 客户端侧折叠（每 domain 一个带 `fromEvent` 的投影 cell） | 一旦 plan 的单元要折叠两种事件，客户端 cell 就得在浏览器里**重复宿主的转移逻辑——同一个 fold 写两遍、各自演化** |
| 对日志尾部做有界反向扫描（absorber 声明） | 今天没有任何东西支持它；**只服务于「每个事件都带完整折叠态」的 domain**；持久化投影缓存用统一配方覆盖同一冷读需求。**「Revisit only if a real cold-read path emerges that checkpointing cannot serve.」** |
| `invalidate` 式 cell（标脏 + 领域事件时重取） | 它**只为增量事件而存在**。整值规则让每个 domain 都是 last-wins；goal 的重取循环、合并、陈旧读围栏全部消失 |
| 把注册表挂在 `ctx.apiProxy` 上 | 会话投影**不是 web 专属**（TUI/ACP/headless 是未来消费者），且 domain 包不得依赖 apiproxy 包 |
| 单独的客户端 `SessionProjectionViews` 类型表 | 一张 `SessionProjectionMap` 端到端贯通才是 wire-passthrough 纪律（**不要第二套 DTO 词表**）；值是 JSON payload，渲染归 slot |
| 用事件广播收集代替走注册表 | **异步监听器给不出那一个同步切面**，而正是它让 `asOfSeq` 成为跨所有 key 的一致快照；注册表是本仓库表达「贡献」的固定形状 |
| 专用 `plan/select` 选择事件（结构化领域事件，替代折叠命令记录） | 命令通道已有结构化 `{name, args}`；`/plan` 语法与其折叠**在同一插件内**（领域内耦合，不是跨领域）；少一个事件类型。附带一条**领域内排序约束**：handler 必须在任何可失败路径之前调用 `set()`，**否则「记下的请求」与「实际运行」会分叉** |
| 保留 `setPlanMode` 专用 RPC | plan 选择就是普通用户命令；走命令通道即免费获得**持久留痕、流式渲染、多标签可见性、准入语义** |
| 让 mutation RPC 的响应喂状态 | 已提交的 mux 事件立刻到达且带同样的整值和 seq；**「响应喂状态」正是当初需要写修订号围栏的原因** |

**风险栏里最值得抄的一条**（`:181`）：

> 「**Whole-value rule is load-bearing**: a future domain logging bare deltas cannot serve consumers from
> its latest event and complicates its own unit.」——并且缓解措施是**把规则写进 note 和包 README，
> 让单元契约在每次转移处强制显式全状态**，而不是靠评审记得。


---

### P-A4 `proposed/architecture/2026-07-25-client-settings-locale-theme.md`（130 行，**全文**）
**标题**：Client Settings, Locale, and Theme layering
**命中主题**：模块边界与「谁拥有某个事实」；schema/结构化字段；单一写入口

**它主张什么**：Settings 面板做成**纯组合面（pure composition surface）**——壳只声明 slot、渲染框架结构，
**零文案、不依赖 locale、既不 import 也不枚举任何 feature**；哪个 feature 要出现在设置里，
就由**它自己的插件**去注册进对应 slot。

**四条可直接迁移的所有权判据**：

1. `:13` **「feature owners self-register」** —— 并且明确否决了「为每个 feature 建一个 `ui-settings-*` 卫星包」：
   > 「the settings surface belongs to the feature package itself (shipping the Theme feature means
   > Theme's settings choices ship with ui-theme)」。
   **无主的内容也要有主**：chrome 文案 + General 骨架 + `settings` 字典归 `ui-settings-general`——
   原文自己下的定义是「**the owner of the ownerless copy, not a feature satellite package**」。
   → 「谁拥有某个事实」的一个补充规则：**没有自然归属的事实，要显式指派一个所有者包，而不是散落**。
2. `:23`–`:25` **「解析」与「呈现」严格分层**：theme 偏好是三态 `light|dark|system`，
   **解析 system 属于 theme 域**（ThemeRuntime 持 `prefers-color-scheme` 监听，原文称之为
   「environment sensing, not DOM presentation」），快照同时带 `preference` 与**已解析的** `active`；
   而 `ui-layout` 的 presenter **「has no notion of system — it consumes only resolved results」**。
   → 对 finaudit 的直接对应：**口径解析（哪个准则、哪个版本）属于口径域，渲染层只消费已解析结果**，
   不许在展示层再判一次口径。
3. `:19`、`:101` **单一写入口 + 未知值 fail**：`setLocale`/`setTheme` 是唯一写入点，
   「an unknown id fails」；持久化**只存 id**，坏值回落默认。
4. `:58` **「canonical home」规则**（跨包类型的归属判据）：一个 slot 的类型规范家安在
   **所有注册者的最低公共依赖**处，而不是安在声明者处（安在声明者会成环）；
   其它包通过 re-export outlet 消费。

**它否决了什么备选及理由**（原文 `:105`–`:115`，6 条，全部照录）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 应用壳集中订阅偏好并重渲染整棵 slot 树 | 语言/主题变更只需更新真正的消费者；整树刷新**放大爆炸半径**，还把业务偏好接进了壳 |
| theme service 直接操作 DOM | 注册表服务会因此依赖呈现环境，生命周期与全局样式归属都不清；Layout 已经拥有页面根呈现边界 |
| 在 Layout presenter 里解析 system | presenter 就得自带 matchMedia 订阅、还要从 themes 列表里挑具体定义，**逼呈现层理解偏好语义**；在服务侧解析则每个消费者拿到同一份已解析快照 |
| Settings 壳 import 并枚举各 section | 加一页就要改壳插件，破坏「每个 feature 从自己的插件占位」的组合模型 |
| 每个 section 一个 `ui-settings-*` 卫星包 | **把设置面与 feature 本身离婚**：改 Theme 行为要动两个包，包数随设置项线性增长，卫星包反向依赖 locale/theme 服务形成一个**纯粹为了拆包而存在的中间层** |
| 把 Locale/Theme 快照直接 inject 进 React | inject 结果按 entry identity 缓存，**易变值会陈旧**；每个服务手搓一个 React hook 还绕过 slot store 的统一绑定 |

- `:130` **风险栏里一条对 finaudit 有用的自省**：`settings.general.item` 的合并副本被复制在 locale 与
  ui-theme 两处，「must stay verbatim-identical … any drift means changing all three together」——
  **知道自己留了一处必须手工同步的重复，就把它写进 Risks**，而不是假装没有。

---

### P-A5 `proposed/architecture/2026-07-28-storage-root-and-derived-medium-recovery.md`（59 行，**全文**）
**标题**：Storage root placement and derived-medium recovery
**命中主题**：fail-closed 在什么边界执行；**谁拥有某个事实（「这份数据是权威的还是派生的」本身是一个要声明的事实）**

**这一篇是本轮最锋利的一篇。** 它提出的概念是：**「权威 vs 派生」必须由 domain 自己声明，
不能做成全局行为。**

- `:13` **问题陈述**：一个「内容完全可以从 session 日志重建」的文件，损坏时会**把整个进程的启动砖掉**
  （truncated / 手改 / 版本号 bump 的 `session_projcache.json` → `malformed-medium`/`version-mismatch`
  → domain open `invalid-record` → `Service.init` 拒绝 → fail-loud boot 拒绝启动）。
  而同一条路径对 `workspace.json` 是**正确的**——「workspace records are authoritative, not derivable」。
  作者的结论句值得整句抄：
  > 「the missing concept is **a per-domain declaration of authority, not a global behavior change**.」
- `:27` **落地形状**：`DomainSpec` 加一个字段 `recovery?: 'reject' | 'reset'`，**默认 `'reject'`**。
  为什么放在 spec 上，理由写得很干净：
  > 「The spec object is already the single source of a domain's identity and layout;
  > **whether its medium is authoritative or derived is the same kind of fact and lives in the same place.**」
  → **同一类事实放同一个地方**，这是「谁拥有某个事实」的另一种表述。
- `:29` **damage-class 是封闭枚举，重置只在这个封闭集合上触发**：
  只有 `StorageError('version-mismatch' | 'malformed-medium')` 或 `DomainError('invalid-record')` 三个
  **确定性的 parse-time code** 会触发 reset；
  > 「Every other failure (`backend-not-found`, `facet-unsupported`, `already-open`, I/O errors)
  > **stays loud regardless of the declaration: misconfiguration and environmental faults are not medium damage.**」
  并且 **retry 是单发的（single-shot）**——第二次失败照样抛，「a persistently failing medium cannot loop」。
- `:29` reset 时**必须留痕**：「logs one warning **naming the domain and the discarded medium**」。
- `:13` 还记了一条很诚实的自我指控：cache 包 README 与 domain spec 的 JSDoc 都写了
  「version bumps discard the whole medium」，但那**「today describes an aspiration, not the implementation」**
  ——**文档写的是意图、代码没实现，被当成一个要修的缺陷写进 Problem**，而不是当成已完成。

**它否决了什么备选及理由**（原文 `:34`–`:46`，7 条，全部照录）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 保持每个启动目录一个 `.storages`（改动前现状） | session 是全局的，所以**每一个「从 session 派生」的介质都会与自己的真相源劈叉**；缓存的立项场景（跨全部 session 的一次列表）**结构性地漏行** |
| launcher patch + `storageRoot` profile key | 一条 `!!js` yml 表达式就能拿到全局根；launcher patch 是**第二个重写点**，而 profile key 在真有消费者之前是**空座位** |
| 只把投影缓存挪到全局根，`workspace.json` 留在 per-cwd | workspace 注册表有完全相同的错配；一个 hub 根让介质共址、心智模型单一 |
| 在缓存插件自己的 `Service.init` 里 catch 损坏错误、删文件、重开 | 插件**说不出介质路径**（要绕过后端抽象），且**每个未来的派生 domain 都要重写同一个 catch**；facility 是唯一已经在分类 open 失败的地方 |
| 损坏时回落到一个内存态 domain | **静默降级**成只在内存里活一辈子，损坏文件永远不自愈，下次启动照样炸 |
| 把损坏介质改名留档（`<unit>.json.corrupt-<ts>`）而不是删除 | 派生介质的损坏字节**没有恢复价值**（日志才是真相源），留档会无界堆积；**delete is the honest operation**。但原文同时说明：如果将来有**权威** domain 想要 reset 语义，改名留档才是对的——**这正是 `recovery` 要按 spec 声明而不是全局的原因** |
| 全局无差别自动 reset（不加 spec 字段） | **直接否决**：`workspace.json` 是权威用户数据，版本 bump 时静默重置会毁掉 workspace。**「Authority is a property of the domain and must be declared by its owner.」** |

- `:57` 风险栏写了一条与「reset 的爆炸半径」直接绑定的缓解：「The single-shot retry
  **bounds the blast radius to one delete per open**。」
- `:59` 新增的破坏性原语 `destroy` 被显式关进笼子：「Its only caller is the facility's declared-reset path …
  **nothing model-facing or user-facing can reach it.**」

> **对 finaudit 的可迁移点（本轮最高优先级之一）**：证据链数据要分成**权威**（口径裁定、人工复核结论、
> 冻结快照）与**派生**（缓存、索引、投影）。派生的坏掉可以自动重建但**必须留痕**；权威的坏掉必须 fail-loud。
> 关键是**这个属性由数据的所有者声明**，不是由存储层统一决定。

---

### P-A6 `proposed/architecture/2026-07-29-durable-last-activity-index.md`（67 行，**全文**）
**标题**：Record last activity in the session index
**命中主题**：append-only 与「不可改写」的硬约束；同一事实的两处计算会漂移；**一个 note 的产出可能是「记录下不做」**

**它主张什么**：把「最近一次人类提问的时间」存进 session 索引，让冷路径列表不必读大日志、也不依赖缓存。
**但这篇最值得学的不是提案本身，是它对自己的三处诚实。**

- `:11` **「mtime 回答的是另一个问题」**——这是一条极好的口径论证：
  > 「mtime answers a different question: **when the artifact was last written**. Every durable write
  > refreshes it, including a truncate-repair of a torn tail, synthetic closers …, and the
  > `session/end-seed` boundary appended during pickup. That approximation **promoted a Session
  > merely because it was opened**.」
  → **拿一个「差不多」的字段当另一个语义用，错误不是精度问题，是口径问题。**
- `:24` **append-only 不是风格偏好，是被测试钉死的不变量**：
  > 「**JSONL cannot host a mutable header field.** The header is line 1, written once during
  > materialization … `jsonl.spec.ts` **pins that committed bytes are never rewritten**.
  > A per-append header field would **violate an asserted durability invariant, not merely
  > complicate the writer**.」
  → 于是提案**对两个后端刻意做成不对称的**（`:21`「the proposal is deliberately asymmetric about them」）：
  SQLite 加列，JSONL 只能考虑 sidecar 或干脆保持近似。
- `:26`–`:32` **三个未决问题被显式挂着，「none of them is settled here」**：谓词归谁拥有 /
  旧日志怎么回落 / JSONL 能不能接受 sidecar。
- `:28` **「同一规则两处计算必然漂移」的标准表述**：
  > 「A stored field encodes the rule at write time, where the writer sees one batch, while the attached
  > summary folds a whole log. **Both must use one exported event predicate or reducer** so new
  > message-source variants cannot make attached and cold ordering disagree.」
  对应的验收判据 `:48`：「The prompt-time rule has **one definition**: a test proves the stored field and
  attached fold **agree** over a log containing human prompts, injected user messages, boundaries, and closers.」
- `:60` **最值得抄的一条 Risk——允许提案的结论是「不做」**：
  > 「**Cost may exceed the defect.** … If the honest answer for JSONL is "keep the cache fallback",
  > **this note's outcome may be documenting that decision rather than implementing a field.**」
  → 一篇 proposed note 明写「我可能最后只是记录下我们不做这件事」。

**它否决了什么备选及理由**（原文 `:36`–`:42`，4 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 冷路径直接读日志 | 构造上正确、无需改格式，但**击穿了 header-only 列表**：`list()` 会随日志总字节增长，而 web session 树对全部 session 扇出 |
| 保留 mtime 但把边界写入排除在外 | **判为「不可能」而非「不想要」**：mtime 是文件系统的、不是后端的；除非每次边界写后把时间戳改回去——那会与并发读者竞争，**并且是在对制品撒谎** |
| 只在真的发生修复时才写边界 | 边界 note 已经否决过：**该谓词对有序重启也必须成立**；「Trading a correctness invariant for timestamp accuracy is **the wrong direction**」 |
| 从投影缓存派生活动时间（**当前的临时实现**） | 缓存是可选的、fail-soft 的；它的缺席或 checkpoint 延迟会让排序**依赖缓存的可用性与新鲜度**，所以**它不能提供这里要的权威值** |

---

### P-A7 `proposed/architecture/2026-08-08-cordis-web-dynamic-packages.md`（270 行，**全文**）
**标题**：Cordis Host/Client Dynamic Plugin Runtime
**命中主题**：审批/授权边界；不可变版本 + 运行留痕；拒绝如何建模；**能力发现必须是白名单而不是反射**

这是本轮最长的一篇（模型可以在运行期写插件并注入到 Host/浏览器）。对 finaudit 有用的不是这个功能，
而是它为「模型生成的东西要进入真实环境」建立的**一整套闸门形状**。

- `:19`–`:26` **Core principles**（七条，几乎逐条可迁移）：
  Host 是**唯一的进程级权威**；Client 只存本页事实；**「Define creates only immutable code versions;
  Run activates only a defined version.」**；版本指针**只有在目标完成必需的激活之后才提交**；
  写代码前必须先通过 Inspect Provider 查能力，且**「Inspect results assist coding and are not plugin
  runtime business data」**；Client 代码进页面前**必须用户授权**；
  **Tool 调用不等待审批**（`:26`：审批可能发生在当前 turn 结束之后）。
- `:51`、`:57` **三层身份（Plugin / Package / Run）**，这是「证据链要能指到哪一次」的教科书形状：
  Package **不可变**，「Every `cordis_define` creates a new Package; an existing Package **cannot be
  modified in place**」；**每一次激活尝试都拿一个新 Run id**，包括**失败的、重试的、版本更新的**：
  > 「`pluginRunId` associates approval, Host activation, Client loading, private RPC, Tool cards,
  > and errors **with the same attempt**.」
  → **失败的尝试也是一等公民、也有 id、也可被检视**（`:59`「A failed attempt may leave no live physical
  Run while remaining available for inspection.」）
- `:63`–`:68` **`current` 与 `next` 两个指针，失败不自动回滚**：
  > 「If an update target fails, **the old physical Run is not restarted automatically.** The previous
  > `currentPackageId` continues to identify the last successful version, and the failed target remains
  > `nextPackageId`.」
  对应否决理由 `:220`：**自动恢复会把「目标失败」和「旧版本又成功了」合并成同一个结果**——
  这条对 finaudit 的重算/回滚语义直接适用。
- `:81`–`:83` **明确声明「什么不进日志、也不恢复」**：Registry 不落盘、进程重启不恢复；
  「The Session Log may retain Tool calls, results, and metadata needed by cards, but **it does not
  replay dynamic code to restore the Registry**」；且**不写进 session 投影当作可恢复状态**，
  理由是自动恢复会重新引入连接身份、启动基线、跨页一致性协议——**「outside this design」**。
  → **把「不恢复」当成一个被声明的设计事实，而不是遗漏。**
- `:108`–`:114` **授权分两级且被写进 UI 约束**：单勾 = 只授权当前 Package；双勾 = 授权该 Plugin 的未来版本；
  Reject = **两半代码都不执行**，并且**「The model must not immediately request approval again unless the
  user asks for it.」**（拒绝之后模型不许立刻重问）。
  `:116` **待审批的行只显示三个审批动作，不同时给 run/stop/delete**——**审批态是排他的 UI 状态**。
- `:120`、`:224` **审批协议里最值得抄的一条：不广播源码**。
  请求只带「请求身份、Session、Plugin、Package、mode、name、purpose、是否需要审批」，
  **不广播源码**；授权页面再按 `pluginId + pluginRunId` **精确拉取那一次 Run 的源码**。
  否决理由整句：
  > 「Broadcasting sends source to every page **before authorization**. A timeout cannot distinguish
  > **no page, a slow page, and no user action**, and the Host would need compensating rollback.」
- `:128` **只接受「仍然是当前那一次精确 Run」的回报**：「The Host accepts the report **only for the
  still-current exact Run**」——陈旧回报被结构性丢弃。
- `:160`、`:230` **能力发现是白名单，不是反射**（这条对「Agent 能看到什么工具/什么字段」极其重要）：
  > 「Provider methods are **explicitly allowlisted queries, not arbitrary Service-method forwarding**;
  > the Registry has **no layered target** and does not automatically turn business Service methods
  > into executable Inspect methods.」
  否决理由 `:230`：自动暴露每个 Service 方法会**「turns capability discovery into a business-call proxy
  that bypasses plugin approval and lifecycle」**。
- `:179` **允许隐藏、不允许改写**——这是一条极好的「脱敏/裁剪」红线：
  > 「The allowlist **may hide** Services, members, `@deprecated` APIs … but it **must not rewrite
  > method names, parameters, or return types** for the remaining APIs. Guard may reject arguments,
  > fix sources, or hide members, but **it must respect source signatures**.」
- `:154` **禁止对活对象做整体序列化**：动态代码不得对 Host/Service/Event payload/Snapshot
  跑 `JSON.stringify`、`structuredClone`、递归枚举、整体拷贝或整体展示，
  「It reads **only leaf fields needed by the current task** and constructs minimal owned data
  without Host references.」
- `:206` **错误的结构化形状**（直接对标 finaudit 的失败留痕）：
  技术错误跨 Host/Client 时**保留原始 `message`、有 `stack` 就保留 `stack`**，
  结构化诊断带 `pluginId`, `packageId`, `pluginRunId`，**外加恰好一个 phase**：
  `approval | host-load | host-apply | client-load | client-apply | client-render`——**阶段是封闭枚举**。
  `:208`「A rendering error belongs to the exact Run and **does not contaminate the immutable Package**.」
- `:210` **失败与拒绝的处置被区分开**：技术失败 → 模型读诊断、自己改、自己重试；
  **用户拒绝 → 禁止自动重复请求**；用户在面板上手动 run/stop/remove → **只注入下一步上下文，不主动唤醒模型**。
- `:146`、`:266` **对自己的安全边界不吹牛**（本篇最诚实的一句）：
  > 「These contexts reduce misuse and provide instructional errors, but **they are not security
  > boundaries against malicious code.**」
  Risks 里再说一遍：「**Restricted contexts are not security sandboxes.** … Allowlists and approval
  reduce misuse but **do not isolate malicious code.**」

**它否决了什么备选及理由**（原文 `:214`–`:238`，12 条，要点照录）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| Define 与 Run 合并 | 会**删掉「已定义但未运行」这个可预览状态**，并把语法错误、审批、运行错误、重试**混进同一个动作** |
| 用 Package id 当 Plugin id | 单层 id 无法在稳定实例下追加不可变版本；更新就要 stop+undefine+新 define，**历史卡片与 `@` 引用保不住对象身份** |
| 单独提供 `cordis_update` | update 与 run 的加载、审批、UI、诊断、执行语义完全相同 → **重复协议**；用 `mode:"update"` 表达 |
| 更新失败后自动恢复旧 Run | **把「目标失败」和「旧版本又成功了」合并成一个结果** |
| `cordis_run` 阻塞等审批与最终 Client 结果 | 审批可能在本 turn 之后才发生；**无页面时会死锁并无限占用 Tool** |
| Host 广播源码 + 等 Client ack + 超时 | 授权前就把源码发给每个页面；**超时无法区分「没页面 / 页面慢 / 用户没动作」**，Host 还得写补偿回滚 |
| 页面启动时自动恢复每个 Host-active 的 Package | 需要连接身份、启动基线、跨页一致性；本设计**接受页面本地 Client 状态** |
| 用公开 Remote Service / `ctx.remote` 连接 Package 两半 | 会把动态 Package **暴露进产品 RPC 接口**；私有 `harness.handle`/`host.call` 足够且能按 `pluginRunId` 拒绝陈旧请求 |
| 自动把每个 Service 方法暴露成 Inspect 查询 | **把能力发现变成绕过审批与生命周期的业务调用代理** |
| 把完整 API 塞进 System Prompt 或 Skill | 静态文本会漂移且吃上下文；Prompt 只留稳定规则，**精确签名由 Provider/Catalog 返回** |
| 要求 Slot 所有者在运行期注册 props schema | props 已存在于 TS 类型与 JSDoc → **重复注册制造第二个权威** |
| 让历史 Run 卡片去扫后面的 Session Log 条目 | 把 Tool 视图**耦合到完整日志顺序与后续消息结构**；页面卡片索引/store 已经能告诉卡片它被更新的 Run 取代了 |

---

### P-A8 `proposed/architecture/2026-08-08-semantic-composer-chain-phases.md`（46 行，**全文**）
**标题**：Semantic phases for composer-chain election
**命中主题**：**用一个标量同时表达两种决策 = 结构性 bug**；封闭枚举；注册期 fail-loud

**它主张什么**：把「一个全局数字 `priority` 排序全部候选」换成**领域自有的、有序的 phase 元组**。
`conversation.composer` 声明 `['interaction', 'restriction']`，注册时**必须指名 phase**，
数字 priority **只在 phase 内部**排序；排序键是 `(phase 序号, 局部 priority, 稳定注册顺序)`。

**本篇最值得抄的是它对 bug 的定性**（`:11`，整句）：

> 「**The defect is not one incorrect number.** The chain currently uses **the same scalar for two
> different decisions**: whether a candidate resolves an existing interaction or restricts starting new
> work, and the local preference between candidates of the same semantic kind.
> **Any numeric repair preserves that hidden coupling and lets a later registrant recreate the bug.**」

→ **判断「这是不是一个结构性缺陷」的判据：修好这一个数字之后，下一个注册者会不会重新造出同一个 bug。**

- `:15` **注册期就 fail-loud**：「Registration **fails immediately** when a phased chain entry omits its
  phase or names one outside the declaration.」未声明 phase 的链保持原数字行为（**不强制迁移**）。
- `:17` **领域规则被写成一句可判定的话**，而不是「优先级更高」：
  > 「an **interaction** resolves a live Host wait that already exists; a **restriction** prevents the
  > user from initiating work through the ordinary composer.」
  并给出为什么 interaction 在前：「Resolving an existing wait is **not a new follow-up** to the one-shot child」。
- `:19` **词表归属**：「The phase vocabulary belongs to **the declaring slot, not to the slot framework
  globally**.」其它链**不获得 composer 术语、也不需要迁移**。
- `:21` **显式声明「本提案不取代谁」**：列出它扩展的三份契约，并写死
  「**No active Agent Note should be archived when this proposal lands.**」
- `:40` **一条罕见的验收判据：证明改动对模型不可见**——
  「The change modifies **no model-visible tool definition, system-prompt section, request routing,
  or session event**. Browser election therefore has **no token cost and no KV-cache invalidation**;
  tests **compare the model request header before and after** the client-only transition.」
  → **「这次改动不影响模型输入」不是断言，是一条要被测试比对证明的判据。**
- `:44` **风险栏自己预判了本方案的退化路径**：
  > 「**Phase names can become a vague substitute for design.** Each phased slot therefore owns a short
  > ordering rule and **rejects entries that cannot state which side they belong to**. A future hard
  > safety surface that must preempt answering **should not be mislabeled `restriction`**; it needs an
  > explicit earlier phase or a boundary outside this composer chain.」

**它否决了什么备选及理由**（原文 `:25`–`:31`，4 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 把 read-only 的 priority 挪到 question/approval 之后 | 最小战术修法，但**把语义支配关系编码成没有文档的数字间距**，下一个 composer 只能在同一个全局标量上猜 |
| 让 read-only selector 在 `interactions` 非空时自行退让 | 修好了当前这一对，但**逼一个 restriction 插件理解每一个可操作领域**，并把选举策略复制进各个 selector；新增一种 interaction 就要改无关的 restriction |
| 只靠运行时 child guard | guard 管的是新模型调用，**定义不了浏览器对已挂起的 wait 的排序**；「Runtime authority and presentation election are **separate invariants**」 |
| 把所有匹配的 takeover 堆成栈 | composer **只有一个动作席位**；堆叠会让键盘焦点与「谁负责回答」变得含混 |

---

### P-A9 `proposed/architecture/2026-08-10-unary-apiproxy-remote-migration.md`（124 行，**全文**）
**标题**：Migrate simple unary API Proxy calls to business Remote services
**命中主题**：模块边界与「谁拥有某个事实」；**权限检查必须跟着端点一起搬**（fail-closed 的位置）；迁移的提交边界

**它主张什么**：只迁移那些「业务操作已经有自然 Service 所有者、剩下的只是小参数/结果投影」的一元调用；
**大的 BFF 方法留在原地**。

**四条可迁移的判据**：

1. `:13` **「一元语法不等于简单」** —— 本篇的核心判据：
   > 「**Treating all unary syntax as evidence that a method is simple** would move product policy into
   > arbitrary Service packages or force new packages that have no independent business owner.」
   `:23` 给出**退出条件**（什么情况下一个方法退出本次迁移）：发现端点特有的生命周期策略、
   大量编排、Client 依赖某个**只在协议层存在的错误区分**、或者传输形状无法表达为一个小的所有者侧适配器。
2. `:19` **拒绝身份包装器**：「A new method is justified **only when it performs real adaptation**;
   an identity `remote*` forwarding wrapper is **not**.」
   验收判据 `:109` 把它变成可检查项：「no identity `remote*` wrapper remains」。
3. `:15`、`:81`–`:86` **本篇最重要的一条安全论证（fail-closed 的位置）**：
   Connection 当前把「仅 loopback 的特权方法名单」放在 **API Proxy 的 fallback 里**执行；
   而 **Typert 拦截器会在 fallback 之前认领端点**——于是：
   > 「migrating credential or preset authoring calls **without moving the privilege check** would
   > **grant trusted-LAN callers operations that are currently loopback-only**.」
   对策写成一条**非升级要求（non-escalation requirement）**：
   > 「**endpoint ownership may change, but the set of callers authorized to invoke the operation may not widen.**」
   并且检查必须**同时认得旧的点号名与新的斜杠端点**（`:81`）。
   → **搬家的时候，闸门不会自动跟着搬；而且新的分发路径可能绕过旧闸门。**
4. `:58`、`:100` **「等价」要做成实现事实，不是承诺**：
   同一个 `createApiRemoteAgentResolver()` **闭包**被同时装到新旧两条路径上，
   > 「Sharing the exact closure with legacy `agentFor()` makes equivalence **an implementation fact
   > rather than a promise**.」
   `:60`–`:67` 还把要钉住的 6 条集成测试结果逐条列出（复用不 resume / 冷 session 带 preset 恢复 /
   并发共享一次 resume / subagent 身份在业务调用前就 `agent-busy` / 缺失 id → `session-not-found` /
   解析失败保留既有 `RpcError`）。
- `:69` **策略粒度被显式说明**：「Lookup policy is **key-wide, not endpoint-specific**」——
  所以那些需要 live-only / 不许 resume 的方法**不能**用共享 lookup，只能留在原地
  「until Typert supports an explicit per-endpoint policy」。**能力不够就不搬，而不是搬了再将就。**
- `:54` **一条「为什么这三个方法必须一起搬」的所有权论证**：
  `workspace.delete` 与 `create`/`rename` 属于同一条序列化链，
  「Splitting one method out would make the Service and API Proxy **observe different operation orders**.」
- `:90` **提交边界被写成规则**：RFC 提交 + 每个 Service 一个纵向提交 + 一个最终集成提交；
  并**允许 Service 提交暂时是红的**（生成物与共享 fixture 在最终提交统一对账）——
  **把「中间态会红」写进计划，而不是假装每步都绿。**
- `:118` Risks 第一条对 finaudit 有直接类比：
  > 「Removing legacy schemas **also removes their protocol-specific error taxonomy.**
  > A hidden Client branch on one of those codes would make the call non-simple and
  > **must be discovered before its Service commit is accepted**.」

**它否决了什么备选及理由**（原文 `:96`–`:104`，5 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 简单方法继续留在中心 API Proxy | 保住了单一传输门面，但继续维持**接口/schema/路由行/桩/业务投影的重复**——正是引入 Typert 要消除的 |
| 把每个一元方法都搬走 | **一元语法不蕴含单一所有者行为**；会把 BFF 策略泄进通用 Service，或造出没有独立业务主人的包 |
| 给 Remote 方法另写一套 resume 实现 | 第二个 resolver 会在 preset 恢复、并发去重、subagent 归属上**漂移** |
| 保留每个旧 RPC 名与响应信封 | 会把业务包变成旧协议的复制品 |
| 相信 API Proxy fallback 会兜住特权方法 | **拦截器选择绕过了那个 fallback**，会静默扩大权限 |

---

## 2. `proposed/feature`（4 篇，全部全文）

---

### P-F1 `proposed/feature/2026-06-30-pre-tool-input-rewrite.md`（53 行，**全文**）
**标题**：Pre-tool input rewrite — a consistent design
**命中主题**：**证据链／审计留痕**（本轮与 finaudit 最贴的一篇）；同一事实的多个读者必须原子一致

**问题形状**（`:13`–`:19`，值得整段搬）：一个工具调用的参数在**执行之前**就已经被三个读者读走了：

1. `assistant/message` —— 先于工具派发被 append，是 `deriveMessages()` 重放的**模型历史来源**，
   它带的是**模型自己发出的**那份参数；
2. `tool/call` —— **持久的 AUDIT 记录**，在 `ctx.tools.execute()` 之前 append；
3. **面向人的呈现**读 `tool/call.arguments` —— UI renderer 传给 `presentResult`，
   `dsh-tool-bash` 从中派生卡片标题、rawInput、cwd、以及「终端 vs 后台」的处理方式。

于是（`:19`）：
> 「An **execution-only rewrite** would make the UI show one command while another ran and
> render the result against the wrong arguments.」

**它主张什么**（`:23`）：改写是一个**前身份一致性事务（pre-identity consistency transaction）**——
有效值必须**在 registry 构造出不可变 `ToolExecution` 之前**选定，并**原子地**反映到三个读者上。

**对 finaudit 证据链最直接的一句**（`:25`）：

> 「The `tool/call` audit event records the **REWRITTEN** arguments (with the **original retained in a
> sidecar field** for the audit trail — **a hook changed the call, and both the original and the
> effective arguments are facts worth keeping**).」

→ **被改写这件事本身是事实，原值和生效值都要留。** 这正是 finaudit「口径被覆盖/被人工调整」的留痕形状。

- `:29` **为什么不能在现有触发点上扩展**：到 `PreToolDecision` 触发时**两条持久记录都已经存在了**，
  且执行身份已被保护 → 必须**把决策移到日志提交之前**，或者**新增一个更早的专用改写决策点**。
  → **闸门的位置由「谁已经读过这个事实」决定，不由代码写起来方不方便决定。**
- `:35` **不许开可变逃生口**（Alternatives 只有这一条，原文只记录了这一条）：
  允许 pre-execute 监听器直接赋值 `exec.arguments` 只会得到**执行侧的改写**，
  模型历史、审计、呈现三者纹丝不动；
  > 「Keeping the identity protected makes such **partial behavior unrepresentable**.」
  → **让"部分正确"在类型上不可表达**，而不是靠约定不去用它。
- `:35` **能力没到位就诚实降级并留 TODO 锚**：在一致性事务存在之前，CC/Codex 桥
  「**logs and warns about `updatedInput` rather than claiming it was honored**」，
  并在 loop 派发点放一个 `TODO(pre-tool-input-rewrite)` 作为「缺失的更早阶段」的锚点。
- `:48`–`:53` **Open questions 四条全是真问题**（未替作者补答案）：改写 `assistant/message` 的
  tool-call 块会不会破坏某个 provider 的重放期望；原参数该不该留在 `tool/call` 上、留在哪个字段；
  改写决策是前移还是新增扩展点、既有 pre-tool 钩子如何避免跑两遍；以及**它与未来的权限 `ask` 流程
  如何交互（用户批准的是一个被改写过的调用）**。

---

### P-F2 `proposed/feature/2026-07-06-recallable-compaction.md`（110 行，**全文**）
**标题**：Recallable compaction — index checkpoints, a state checkpoint, and in-session history recall
**命中主题**：append-only 日志作为唯一真相源；**指针必须由代码确定性拼装，不能由模型写**；确定性重放

**问题的根因诊断**（`:11`，一句话定义了一类设计错误）：

> 「The root cause is **one artifact playing two conflicting roles**. An **index** wants to be frozen,
> chronological, and cheap; the model's **working memory** wants a global view, re-prioritization,
> and mutability. **A single summary can be neither well.**」

→ 与 P-A8（一个标量承担两种决策）是同一类判据的另一面：**一个产物承担两种相互冲突的角色 = 结构性缺陷**。

**几条可直接迁移的规则**：

- `:25` **指针由代码拼装，模型只读**：
  index stub 的页脚 `[checkpoint c<summarySeq>: shadows conversation span #<start>–#<end>;
  originals retrievable via history_read]` ——
  「**Code assembles these pointers** from the `compaction/summary` seq and `shadowedRange`;
  **the model never writes them.**」
  对应否决理由 `:88`：**「Model-authored pointers — rejected: pointers must be exact; deterministic
  assembly is.」**
  → 对 finaudit：**证据引用（表名、行号、准则条款号、哈希）必须由代码从结构化来源拼出，不能让模型写。**
- `:27` **提交后不可改写**：「A committed stub is **never rewritten** and **never re-enters a later
  compaction region**。」
- `:33` **inflation guard —— 不达标就整体不提交**：
  「if the post-compaction size is **not strictly below** the pre-compaction size, **nothing commits**
  and the turn proceeds」，并且**两侧用同一个度量比**（provider 报告的 usage，回落时两侧都用字符估计器）。
  → **比较必须 like-for-like**，这是 finaudit 做「前后对比/重算校验」的直接教训。
- `:40` **崩溃语义被写成两句可判定的话**：summarize 阶段崩溃 → **什么都不提交**；
  提交中途崩溃 → 留下一个**从左到右的前缀**，恢复后的 pass 从日志里最新的 state 类 `compaction/summary`
  读出 merge base 并**无条件**提交剩余区域——「**restoring `[stubs…][state][tail]` outranks shrinking**」。
  → **恢复时明确哪个目标优先**，而不是两个目标都想要。
- `:49` **不建第二个存储**：「There is **no new storage and no sidecar index**: the session log stores
  the content, `compaction/summary.shadowedRange` and `shadowedSeqs` identify what each checkpoint
  replaced, and the tools read both.」
- `:49` **进入模型的静态串必须字节稳定**：工具 schema 与系统提示段是静态字符串，
  **checkpoint id 只通过页脚到达模型**；验收判据 `:99` 要求「tool schemas and the prompt section are
  **byte-identical across passes**」。
- `:106` **Risks 里一条极其克制的效果声明**（值得抄的措辞）：
  > 「**Unknown unknowns remain**: a detail absent from summaries and keywords draws no recall.
  > Recall converts **"unreachable even when suspected" into "reachable when suspected"**.」
  → **准确描述一个机制到底解决了什么、没解决什么**，不吹成"解决了信息丢失"。

**它否决了什么备选及理由**（原文 `:81`–`:92`，13 条，要点照录）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 分阶段交付（先只上 recall 工具，按观察到的使用率再决定是否拆 checkpoint） | 未训练的模型对任何新工具都会**用得不足**，所以这个闸门**量到的是训练缺席、不是设计价值**；预发布窗口是改持久格式最便宜的时候；缓存经济学是**第一方知识、不是等遥测的假设**。（实现仍按 stacked PR、recall 工具先落——**那是施工顺序，不是决策闸门**） |
| 全冻结的完整摘要、不要 state checkpoint | 永久前缀**无界增长**，自我加速走向抖动，且**没有任何东西可以被重新排优先级** |
| 纯 stub、不要 state checkpoint | **预设模型知道自己缺什么**；对 unknown unknowns 失效 |
| 对冻结块做 LLM 老化/合并 | 摘要的摘要有损 + 冻结前缀churn；仅保留**纯代码 rollup** 这一形态并延后 |
| 把完整前缀当作块摘要器的输入 | **O(N²)**；state 文档以 O(state) 给出同样的背景 |
| 一次 summarize 调用输出全部结果 | summarize 路径**没有结构化输出强制**；把一段自由文本解析拆开正是 **fail-closed 设计要避开的脆弱边界** |
| 模型自选块边界 | 解析与校验成本对上未证实的价值 → 延后；块策略放配置 |
| 模型自己写指针 | **指针必须精确；确定性拼装才精确** |
| FTS/向量索引 sidecar | 会话内否决：活日志在内存里且有界，预算内的字面扫描够用；索引要到**跨会话**尺度才值 |
| recall 路径里做语义搜索/二级模型抽取 | 在那里放 LLM 或 embedding 调用**破坏无密钥重放的确定性**；**recall 必须是日志的纯函数** |
| 返回原始事件而不是渲染后的 transcript | 泄露 log-only 词表与块噪声；**「the model reads what a model once saw」** |
| 什么都不做（用 resume/fork 当恢复手段） | **它把恢复变成了一件人类的事** |

---

### P-F3 `proposed/feature/2026-07-08-interactive-side-sessions.md`（41 行，**全文**）
**标题**：Interactive side sessions and merge-back
**命中主题**：复用既有事件而不是新增事件类型；字节稳定的前缀

- `:15`–`:17` **整个功能不新增任何 core service、session-store 方法、或 session 事件**：
  fork 用 `ctx.agents.create({ seed, meta })` 组合；advisor 定位靠**注入一条 plugin-sourced
  `context/message`**；merge-back 也是**往父会话注入一条 plugin-sourced `context/message`**，
  「The next parent request sees it at its logged position, **preserving replay and request
  reconstructability without a new session event**.」
- `:16`、`:25` **「system prompt 字节相同」被当作一条硬约束**：
  advisor 框架**不改 system prompt**，因为「**any byte change invalidates the prefix cache from token
  zero**」；原文同时诚实写出「Deployments may still prefer that stronger separation」——
  **承认更强的隔离是有代价的另一种正确选择**。
- `:26` **新增事件类型的判据**：`sidechat/*` 事件被**延后**而非否决——
  「a sourced `context/message` already records the content, producer, and replay input durably.
  **A dedicated event is justified only by a client that needs distinct rendering.**」
  → **新增事件类型需要一个具体的消费者理由。**
- `:39` **诚实标注「目前只是劝告性的」**：
  > 「**Read-only behavior is advisory until a `tools/pre-execute` deny gate enforces it**」
  → **没有闸门强制的规则就明说它只是劝告**，不写成"已经只读"。
- `:40` 另一条诚实：被压缩过的源会 fork 出它**压缩后的视图**，所以绑定的 UI 应当**披露**
  子会话继承的是摘要而不是被替换掉的轮次。

**它否决了什么备选及理由**（原文 `:24`–`:27`，4 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 用 subagent seam | side session 是**用户驱动、客户端可见、可能活过父 turn** 的；subagent 是模型驱动、返回一个 tool result 的运行 |
| 改子会话的 system prompt | **任何字节变化都会从 token 0 起废掉前缀缓存**（默认否决，但允许部署方选择更强隔离） |
| 新增 `sidechat/*` 事件 | 延后：带 source 的 `context/message` 已经持久记录了内容、生产者与重放输入 |
| 现在就绑协议 API | 当前 UI 是客户端自有的；**活态呈现最终必须从持久消息派生，这样重放才渲染出同一份记录** |

---

### P-F4 `proposed/feature/2026-08-04-task-surface.md`（289 行，**全文**）
**标题**：Task Surface for structured session interaction
**命中主题**：**结构化字段 vs 自由字符串**（最完整的一篇）；schema 校验在什么边界；封闭的组件词表；提交的幂等与终态

这是本轮**对 finaudit 的「结构化交互面」最有参考价值的一篇**：让模型请求渲染一个**声明式**的临时面板
（对比选项、排序计划、审阅表格、填一组相关字段），用户提交后成为**一条普通的可见用户消息**。

**它主张什么**（`:17`、`:32`）：`TaskSurfaceModelV1` 是 **JSON**，并且**明确列出它不含什么**：

> 「it contains **no code, callbacks, selectors, HTML, CSS, URLs to executable assets, or expression
> language**.」

**六条可直接迁移的规则**：

1. `:19`–`:24` **适用条件被写成一个四项合取式**（而不是"看情况"）：属于当前会话与当前任务 /
   行为落在已声明的组件集合内 / 不需要后台执行或新的运行时权限 /
   **「the useful durable result is the user's submitted conclusion, not the panel itself」**。
   `:26` 并且强调**这是一个触发器、不是一族产品启发式**：
   「Products **do not inspect tool names or task topics** to open bespoke panels,
   and repeated use **does not automatically turn a Task Surface into a Plugin**.」
2. `:72`、`:76` **未知版本/未知联合分支一律走通用回退，绝不做部分解释**：
   「Unknown versions or union arms use the generic tool-result fallback **instead of partial
   interpretation**.」新增一种 block/field 是**协议变更**，必须在同一次改动里带上
   parser、renderer、无障碍行为、fallback、**重放 fixture**。
3. `:78` **限额是 schema 支持的配置，不是协议的一部分**：64 KiB 归一化模型 / 64 blocks / 32 fields /
   200 table rows / 32 KiB 提交；**id 在模型内唯一、字段值必须匹配声明、未知字段被拒绝**。
   「The limits bound log, DOM, and prompt costs **without changing the protocol**.」
4. `:74`、`:269` **对模型提供的 URL 的处置是一条明确的红线**：Task Surface 永远传 `alt-only`，
   图片语法只渲染 alt 文本；原始 HTML 与内嵌媒体不渲染；
   **「no model-supplied URL is dereferenced without explicit user activation」**——
   并且这条被写进验收判据要求浏览器测试证明。
5. `:82`、`:219`、`:257` **归一化只做一次，且被持久化**：Host 解析并归一化完整模型、
   铸 `surfaceId`、返回 canonical `{ surfaceId, model }`；
   **`presentationMeta` 持久化 `value.model`，「so the projector and executor cannot disagree about
   normalization」**。对应否决理由 `:257`：「Keep the model only in the canonical tool value —
   rejected because **canonical values are not persisted**. Replay requires the normalized model in
   `presentationMeta`.」
6. `:195` **结构化关联字段不得变成第二条隐藏指令**（本篇最锋利的一句）：
   提交后的用户消息保持 `kind: 'user'`，额外挂一个 `taskSurface` 关联（submissionId / callId /
   surfaceId / values）；消息正文是**产品格式化的可读摘要**，模型收到的就是同一段文本——
   > 「**The structured source is not a second hidden instruction.**」
   → 对 finaudit：**结构化留痕字段是给复核用的，不能成为模型看不见/看得见不一致的第二通道。**

**提交与终态的形状**（`:197`–`:205`，直接可搬）：

- **Dismiss 与 submit 分开，dismiss 不启动 turn**：dismiss 追加一条 `task-surface/dismissed` 会话事件；
  **重试复用 `dismissalId` 并返回原结果，不再追加事件**（幂等）。
- **提交在客户端边界是事务性的**：接受时返回精确 `messageId` 且 phase 为 `queued`；
  Dock 在 `queued` 与 `claiming` 期间**禁用一切变更**，且**只有在匹配的用户消息真正持久之后才清草稿**；
  被拒则**保留可编辑值并展示返回的原因**；双击与传输重试**复用 `submissionId` 返回首次结果**，
  另一个 submissionId 在第一个还活着时收到 `submission-pending`。
- `:201`–`:203` **`claiming` 是进程本地的协调状态，不是第二个持久权威**：
  > 「The record is **coordination state, not a second durable authority**; after a Host restart,
  > an uncommitted claim is absent and the still-open logged Surface **becomes editable again**.」
  并且 **Dock 绝不把「队列行消失」解释成任何一种结果**——它重读 `getActive`（`:203`）。
  → **不要从"某个东西不见了"推断结论**，去问权威。
- `:205` **哪些队列操作被禁止，理由是语义而非实现**：对一个 Task Surface 关联行，
  `edit` 与 `steer` 被拒——editing 会**把格式化内容与它 source 里携带的结构化值分开**，
  steering 会持久化一条**不满足提交生命周期**的 `steering/message`；`remove` 在 queued 期间允许。
- `:217` **同一时刻至多一个开着的 Task Surface**，且**关闭它的三种事件被枚举**：
  匹配的提交消息 / dismissal 事件 / **一条普通用户消息（显式绕过）**。
- `:285` Risks 里把这条协调状态的代价写清楚：「Every admission exit **must produce either the matching
  `user/message` or an explicit discard**; otherwise a reconnect could **retain a disabled Dock
  indefinitely**.」

**它否决了什么备选及理由**（原文 `:249`–`:259`，6 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 加产品专有的触发器与面板 | 每种新任务形状都会把 agent 行为**耦合到一个已发布的产品组件**；产品应只定义**一套被准入的组件词表与放置策略**，由 agent 显式选择 |
| 从工具调用渲染任意 HTML/CSS/JS | 会把一次临时交互变成**可执行的客户端插件代码**，却没有代码应有的构建、预览、评估、审批、回滚生命周期 |
| 把 `userInteraction.ask()` 扩成大表单 | `ask()` 是**阻塞式请求/响应**，用于「运行中的工具没有短答案就无法继续」；Task Surface **结束这一轮**、可以跨刷新存活、并以**下一次可见用户轮次**提交结果 |
| 每次调用注册一个动态 `conversation.view` | view 台账是**全局的**而渲染范围是**每会话的**；且会让**瞬时作业身份变成注册身份** |
| 模型只放在 canonical tool value 里 | **canonical 值不持久化**；重放需要归一化模型在 `presentationMeta` 里 |
| 把面板存进长期记忆 | 布局与草稿**不是可复用的事实**；记忆可以保留**用户提交的结论** |

- `:272` **一条验收判据把「模型输入稳定」变成可检查项**：
  「Prefix snapshots show **one stable tool definition regardless of the task-specific model**;
  only the call arguments and later user conclusion vary.」

---

## 3. `proposed/simplification`（2 篇，全部全文）

---

### P-S1 `proposed/simplification/2026-07-04-prune-dead-core-spine-api.md`（63 行，**全文**）
**标题**：Prune dead public API and result fields
**命中主题**：**「有没有生产消费者」怎么判定**；同一事实的重复副本要删；模型可见面本身是产品面

**它主张什么**：把一批没有生产消费者的公共导出、结果字段、便利方法**一次性、有边界地**删除或降级为包内私有。

**最值得迁移的是它对「证据」的定义**（`:11`，整段）：

> 「The production corpus is `packages/*/*/src`, example sources/config, and runtime scripts.
> **Tests, package READMEs, and Agent Note prose are evidence of publication but not fixed callers.**」

并且它**没有把「没有固定调用者」直接等同于「不可达」**：因为 `cordis_inspect` 让 API catalog
**对模型可见**、`cordis_mount` 能通过受守卫的真实服务代理调用被注入的服务，所以
「catalogued service methods and returned shapes are **a genuine dynamic product surface**」——
表格因此**显式区分**「没有固定仓库调用者」与「不可达」，并写明哪些行是**有意收缩模型能发现/能调用的东西**。

→ **对 finaudit 的直接迁移：判断一个接口/字段「没人用」之前，先把「谁算消费者」定义清楚，
并且要单独考虑「模型能看到它」这条动态路径。**（对照 `rules/failure-modes.md` 的第一条：
不对操作者的系统下「没有 X」的判断——这里给出的是一个可操作的、写明语料范围的判定法。）

**几条具体的删除理由，每条都是一个可复用的判据**：

- `:16` **重复字段必删**：`ToolExecutionResult.callId` —— 每个 hook 都已经收到不可变的 `ToolExecution`，
  loop 与 ACP 通过 call/session 事件关联；**删掉字段的同时删掉「证明这份重复不会互相矛盾」的守卫与测试**。
  → **消灭重复的正确方式是删掉副本，不是加校验保证两份一致。**
- `:26` **不接受两个身份**：`compactRegion` 的独立 `session` 参数被收窄到 `agent.session`——
  「accepting two identities **permits a mounted plugin to provide an incoherent pair**」。
- `:23` `assertSerializable` 被删的理由是**它复制了 coordinator append 边界的无损快照**
  ——**同一个校验只应该在一个边界上做一次**（与 P-A2 `:L117` 同源）。
- `:15` `SurfaceManager.invalidate()` 被删的理由写得很具体：**它的合约在结构上不可能发生**
  （seeding 在惰性创建的 manager 存在之前就完成了，session 也从不替换它的日志引用）
  → 「Delete it and **its impossible wholesale-replacement contract**.」
- `:24` `LlmError.status`：适配器/重放都在填它，但**生产代码分支在稳定的 error code/message 上，
  从不读原始 status** → 删字段与重放管道，**保留错误分类**。

**它否决了什么备选及理由**（原文 `:50`–`:52`，2 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 保留测试便利与自包含的结果字段 | 这些好处**是假设性的**；今天它们让每份实现与文档**去解释没有任何已发布调用者能观察到的状态**。真有消费者时，它可以引入**它需要的最小合约**，且所有权与失败语义是已知的 |
| 为「模型写的 mount」保留每一个被编目的成员 | 自指工具集**是真实的通用消费者路径、不是生成文档的噪声**；但它的价值来自**准确、可组合的服务 API，而不是无限期保留重复字段与不自洽的参数对**——每一次收缩都在同一次改动里更新 API 参考 |

- `:63` **Risks 里给出「为什么现在做」的理由**：「The repository is unreleased,
  so **carrying unsupported surface is the larger foundation cost**.」

---

### P-S2 `proposed/simplification/2026-07-19-make-jsonrpc-directional.md`（46 行，**全文**）
**标题**：Make JSON-RPC completion and transport directional
**命中主题**：**同一个事实的两种协议表示必须删掉一个**；对称性是想象出来的成本

**两条核心论证**：

1. `:9` **对称是假的**：JSON-RPC 桥把两端建模成对称 peer，**但实际发的协议是有方向的**；
   共享传输层实现了两半**没有任何端点在用**的方向（server 发起请求 / client 发起通知）。
   `:13` 代价被逐项数出来：pending-request map、生成 id、请求队列、关闭时的拒绝路径、
   响应助手、**以及第二个完成等待器**。
2. `:11` **一个已结算的 turn 被两种协议形状报告**：server 先发 `session.finished` 通知、
   再返回常量 `{ accepted: true }`；Python SDK **丢掉响应、去等通知**才能拿到状态。
   而且因为响应是在 handler 返回后才写的，**通知必然先于常量响应到达同一条流**。
   → 修法（`:19`）：**让 `session/prompt` 直接返回结算结果** `{ status, reason }`，
   删掉 `session.finished`、常量接受响应、以及 Python 那个「响应之后的完成循环」。

**它否决了什么备选及理由**（原文 `:31`–`:33`，2 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 为未来的方法保留一个通用对称 JSON-RPC peer | server 发起的请求将来也许会支撑交互式权限，但**今天没有任何类型化方法或生产消费者**；预发布协议可以**等那个特性被设计时再加上所需的最小方向**，而不是今天扛着一个从未被行使的 peer |
| 为流式客户端保留 `session.finished` | **turn 结算不是增量数据**：请求响应已经标记同一个边界，并且在有序流上跟在所有更早的通知之后；**第二条终态通知制造出两种客户端必须去调和的表示** |

- `:37`–`:38` 验收判据把「删干净」写成**能力不存在**而不是「不再使用」：
  「The TypeScript endpoint **cannot** originate requests or consume notifications.
  The Python endpoint **cannot** originate notifications or consume server requests.」
- `:25` 同时保留了一条**防御性**处置：Python 侧保留一个显式的 reader guard
  「**ignores unexpected server-request frames instead of allowing them to match a response waiter**」
  → **删掉一个方向之后，仍要防止陌生帧被错认成自己在等的响应。**
- `:46` Risks 里明写这是**故意收窄预发布线协议**，并给出未来的正确路径：
  「A future server-initiated request requires **a new typed protocol addition rather than reusing
  generic dormant machinery**.」

---

## 4. `proposed/process`（7 篇，全部全文）

> **先记一条制度观察**：这 7 篇里有 **2 篇**带着 `<!-- agent-note-format: alternatives-not-recorded
> (pre-format Agent Note) -->` 标记（`2026-06-11-architectural-conformance.md:35`、
> `2026-06-20-discover-package-inventory.md:35`）——即**原文自己声明「备选未记录」**。
> 本节对这两篇一律写「原文未记录备选」，**不替作者补**。
> 这正是第一轮 §2 记录的那条制度在语料里的真实分布证据：**宁可显式标注缺失，也不编造。**

---

### P-P1 `proposed/process/2026-06-11-api-extractor-reports.md`（32 行，**全文**）
**标题**：API extractor reports
**命中主题**：门禁；**「为什么延后」被写成一个独立段落**

- `:11` **问题定义**：公共 API 变更是**不可见的**——「nothing makes "this commit changed the public API"
  **an explicit, reviewable fact**」。评审者读 diff 时会漏掉一个导出类型多了一个字段。
- `:15` 提案：每个包一份**签入仓库**的 `etc/<pkg>.api.md`，CI 在重新生成结果与已提交版本不一致时失败。
  → **把一类隐式变化变成一行必须被看见的 diff。**
- `:30`–`:32` **本篇结构上最值得抄的一点：有一个专门的 `## Why deferred` 段**，
  并且给出**重启条件**：
  > 「Deferred when doc-sync landed: low value for an internal monorepo where reviewers already see the
  > source diff, and a heavy, finicky dependency. **Revisit if the packages are ever published
  > externally** — at that point a stable, diffable public API earns its keep.」
- `:7` 顶部还有一条**范围切分说明**：doc-block-typechecking 与 event-taxonomy 部分已经随
  doc-sync 落地并归档，**「this remaining API-report part is deferred as a standalone proposal」**
  ——一篇 note 的一部分落地、剩下的部分独立留在 proposed，边界写在开头。

**备选**（`:19`，原文只记录 1 条）：`tsc --emitDeclarationOnly` + 归一化的公共 API dump，
作为 api-extractor 过重时的轻量替代——「either satisfies the checked-in, diffable report shape」。

---

### P-P2 `proposed/process/2026-06-11-architectural-conformance.md`（36 行，**全文**）
**标题**：Architectural conformance — dependency rules and the adapter kit
**命中主题**：**把散文里的保证变成机械检查**（与 finaudit 的门禁思路同源）

- `:9` **问题定义一句话**：两条架构保证**目前只活在散文里**——(1) 没有任何东西依赖具体的 loop 包；
  (2) 每个 LlmAdapter 都正确地讲 chunk 协议。**「Both should be mechanical.」**
- `:13`–`:19` **dependency-cruiser 的五族规则**（可直接类比 finaudit 的模块边界门禁）：
  除 agent-loop 自身测试与 examples 外禁止 import `dsh-agent-loop`；
  禁止跨包深导入（`dsh-*/src/...`），只走公共入口；
  packages/ 内**任何**导入环都禁止；`vendor/*` 不得 import `packages/*`；
  以及**分层表本身被强制执行**（`packages/README.md` 里的依赖表）。
- `:21` **conformance kit 的形状值得直接搬**：一个**由适配器工厂参数化的可复用 vitest 套件**，
  断言 chunk 协议契约——每个 block 的 index 单调、`block-end` 之后该 index 不再有 delta、
  **恰好一个 `finish`**、usage 至多一次、每个 `tool-call-delta` 都带 call id、abort 被及时响应。
  「Run it against the mocks now; **the DeepSeek V4 adapter inherits it on day one.**」
  → **契约测试套件是给"未来的实现者"准备的，不是给现有实现补的。**
- `:25` **落地顺序被写成一句成本/收益**：「dependency-cruiser config + CI step first
  (**an hour of work, permanent guarantee**)」。
- `:34` Risk 与对策合成一条：规则维护成本 → **「keep rules pattern-based (`dsh-*`) rather than
  enumerated」**（用模式而不是枚举，避免每加一个包都要改门禁）。

**备选**：`:35` **原文未记录备选**（带 `alternatives-not-recorded (pre-format Agent Note)` 标记）。

---

### P-P3 `proposed/process/2026-06-11-supply-chain-and-vendor-drift.md`（35 行，**全文**）
**标题**：Supply chain checks and vendor drift verification
**命中主题**：**「正向被强制、反向没人查」**——这条对 finaudit 的冻结校验直接适用

- `:9` **问题定义（本篇最锋利的一句）**：vendor manifest 在提交时**只在正方向**被强制
  （vendored change ⇒ manifest update），
  > 「but **nothing verifies the manifest's *claims***: that `vendor/` actually equals
  > upstream-at-SHA plus **exactly** the logged modifications.」
  → **一个台账只被要求"改了要写"，没人验证"写的是不是真的"**，这正是 finaudit 冻结清单/证据台账
  必须自查的同一类漏洞。
- `:13` **对策的关键设计：把散文变成可验证制品**——
  夜间 CI 按 manifest SHA 浅克隆上游、拷对应包源码、与 `vendor/*/src` 做 diff，
  **除非 diff 恰好等于已记录的本地修改**（每条修改保存为一个**签入仓库的 patch 文件**）才通过。
  原文点出这一步的性质：
  > 「the log entries become **verifiable artifacts rather than prose**。」
- `:15` **许可证清单也是一条交叉校验门禁**：脚本断言每个 vendored 包都带 LICENSE，
  且 package.json 的 `license` 字段与 `vendor/README.md` 的清单**一致**（该仓库混用 vendored MIT 与自有 BSD-3）。
- `:20` **落地顺序按「成本 × 阻塞」排**：3（许可证脚本）trivial 先做；1 需要 CI 访问私有上游（要 token）
  并把两条已记录的修改转成 patch 文件；2 与 4 只是配置。
- `:35` **Risk 与 fallback 一起写**：上游是私有镜像，CI 凭据与可用性是主要摩擦；
  **「If blocked, run it as a local scheduled agent task instead of CI.」**

**备选**（`:24`–`:25`，原文记录 2 条，且都被标为「二选一皆可、留给实现决定」）：

| 备选 | 原文判定 |
|---|---|
| `pnpm audit` 替代 osv-scanner | **两者都满足「告警扫描」的形状；选型延到实现期** |
| 用计划任务型 agent 替代 Renovate | 对「提出小的更新 PR 并跑完整门禁套件」而言**等价**；两种做法下 vendored 包都排除在外（走 manifest 同步流程） |

---

### P-P4 `proposed/process/2026-06-20-discover-package-inventory.md`（35 行，**全文**）
**标题**：Discover package inventories instead of maintaining static lists
**命中主题**：**静态清单什么时候该留、什么时候该删**（一条很干净的判据）

- `:13` **本篇的核心判据，值得整句抄**：
  > 「**Static lists are appropriate when they encode policy; they are needless friction when they
  > duplicate manifest data or layout facts that already exist** in `package.json`, workspace globs,
  > or the package hierarchy.」
  → 对 finaudit 台账的直接适用：**编码"我们的决定"的清单要留；复述"已经存在的事实"的清单要生成。**
- `:11` **诚实划出「globbing 消不掉的那部分」**：已经手工消掉的部分点名列出
  （`publint-all.ts` 改为从 `packages/<group>/<pkg>` 布局派生、两张 tsconfig `paths` 塌成一个通配），
  **剩下的是 TypeScript 要求必须是显式数组、没有通配形式的 project `references`**。
  → **先说清楚哪些是真的做不了，再提方案。**
- `:17` **generate-and-verify 模式**（与仓库已有 `gen-module-graph` / `gen-cordis-catalog` 同款）：
  生成器写制品，`hygiene`/`doc-sync` 的 `--check` 模式在**已提交副本过期时失败**。
  并且**门禁清单本身也只有一个权威**：「`doc-sync` should be **the one command that defines and prints
  its sub-gates**, with docs **linking to that command rather than restating a second list**。」
- `:29` 一条很实用的验收判据：`knip.json` 只在**编码真实信息**时才保留 per-package override
  （额外入口文件、被忽略的依赖），**「never a restatement of the default stanza」**。
- `:33` **Risk 是对自己方案的反向约束**：
  > 「**Discovery scripts can become too clever.** The implementation should stay boring: read
  > manifests, filter on explicit fields, print the resolved list, and **fail loud**.
  > The payoff is **removing manual inventory drift, not inventing a build system**.」

**备选**：`:35` **原文未记录备选**（带 `alternatives-not-recorded (pre-format Agent Note)` 标记）。

---

### P-P5 `proposed/process/2026-07-13-human-review-skill-maintenance.md`（85 行，**全文**）
**标题**：Periodic human-review maintenance for dsh-code-review
**命中主题**：**「什么算证据」的最完整一篇**；双评审 fail-closed；不可信输入的隔离；证据链带 URL/ID

**这是本轮对 finaudit「可复核证据链」最有制度参考价值的一篇。** 它做的事是：
定期扫已合并 PR，从**人类**评审反馈里提炼出应当写进 `dsh-code-review` skill 的规则，
并且**只有在能证明"这条反馈真的被采纳了"时才提炼**。

**「什么不算证据」被逐条否掉**（`:9`、`:37`、`:63`）：

> 「**Merge status, a resolved thread, an author's "fixed" reply, or a same-file edit is context rather
> than adoption proof**; the PR author's own comments never reach the adapter as they cannot be
> adoption of themselves.」

对应否决理由 `:63`：「Treat merge or thread resolution as adoption — rejected:
**a PR can merge with rejected, superseded, or intentionally unresolved feedback.**」
→ **「合并了」「线程 resolved 了」「作者回了 fixed」三者都不是采纳证据。**

**「什么算证据」被构造成两张 PR 专属的补丁快照**（`:37`，本篇技术核心）：

设 `B` = 反馈基线提交，`T` = 落地 merge 的目标父提交，`M` = 落地 merge。
- 反馈时快照 = `merge-base(B, T)` → `B` 的树 diff；
- 最终快照 = `T` → `M` 的树 diff。
> 「A **target-only change** therefore **appears in neither** PR patch, while a change added to the PR
> after feedback **appears only in the final snapshot**.」
并且**明确不做**「基线直接与落地 merge 比」，因为那种 diff **包含目标分支推进带来的无关改动**。
→ **对 finaudit 的迁移：做"前后对比"时必须构造出两个都属于同一主体的快照，
否则你把别人的改动算进了自己的因果。**

**六条 fail-closed 细则**：

1. `:33` **准入唯一判据是可达性**：所选 PR 的 merge commit 必须是 `origin/master` 的祖先；
   **「Merge-commit reachability is the sole eligibility check」**——
   stacked PR 只要 base 已经到 master 就准入，理由是**评审者当时评的那段代码现在确实在 master 上**。
2. `:33` **单个 PR 失败不中止整轮**（skip 并记 `skipped-pulls.json`），
   但**搜索阶段在窗口会超过 GitHub 1000 条搜索上限时 fail loud**，
   「**so no merged PR is silently omitted**」——**「可能漏了」必须响，不许静默。**
3. `:33` **PR 会话评论一律不采集**，理由写得极干净：
   force-push 之后**GitHub 当前状态无法证明哪个存活提交先于该评论**，
   所以采纳合约会无条件排除它们——**与其采集了再排除，不如根本不采集。**
4. `:33` **只认 GitHub 报告 actor `type` 为 `User` 的反馈**，且**创建与最后编辑时间戳必须严格早于合并**
   （**时间戳相等按合并后处理**）；review submission 用 GraphQL `lastEditedAt`，因为 REST 表示**没有编辑时间**。
5. `:41` **双评审 + 批级 fail-closed**：两个独立配置的评审适配器分别判定
   「谁写的」（`human-authored` / `forwarded-automation` / `unclear`）与「是否被采纳」
   （`adopted` / `rejected` / `unclear`），**只有两边都是 human-authored + adopted 才继续**。
   某一批适配器输出违反 schema 或 id 校验 → **整批 fail-closed 标为 unclear 并路由到 `excluded`**
   （不中止整轮），原始输出留在私有制品里备查；
   若某个适配器对任何非空批**都没返回有效结果**，**整轮以非零退出并发出失败记录，
   而不是报告「没有候选」**。
   → **「没找到」与「没跑成」必须是两种不同的结局。**
6. `:47` **不可信输入被显式隔离**：评审子进程用**擦净的环境**启动，`cwd` 设在**私有运行目录而不是仓库根**，
   反馈被包在一个 **nonce 标记的 `<untrusted-feedback nonce="…">` 块**里，每个 prompt 都指示模型
   **把它当数据**；128 位 nonce **防止不可信正文伪造收尾标签**。
   并且诚实标注边界：「The `access` and `tools` fields are **contract markers on the adapter author,
   not an OS sandbox**」。

**其它可直接搬的**：

- `:43` **起草者只吃结构化的、已达成一致的 guidance，绝不吃原始评审文本**：
  「The primary adapter drafts **from structured agreed guidance, never raw review text**.」
  且它**tool-free、只读**，返回**完整候选文件内容**由工具校验后写入唯一目标。
- `:43` **工具在跑门禁之前与报告成功之前各检查一次**「有没有暂存改动、有没有目标 skill 之外的修改」，
  「so a gate or concurrent process that adds another path **cannot slip through**」——**同一个检查做两次，
  分别在两个时刻**（这与 `rules/failure-modes.md` F-8「跑了门禁但没让它挡住后面的动作」是同一个教训）。
- `:43` **成功时保存 candidate bundle**，内容清单本身就是一条证据链定义：
  源 `origin/master` commit、源 skill blob id、被评审过的 diff、完整候选、
  **源反馈 ID 与 URL**、落地证据范围、适配器判定、门禁结果；
  **「it never commits, pushes, opens, or merges a PR」**。
- `:51` **promotion 用 blob id 做乐观锁**：若当前 skill blob 与 bundle 记录的源 blob 不同就**拒绝应用**，
  「the helper **never replaces a newer `SKILL.md` with stale complete-file output**」。
  草稿 PR 正文必须列出**源反馈 URL/ID、被用作采纳证据的落地提交范围、发起的那次运行、门禁结果、
  以及操作者的编辑**——「repository reviewers receive those concrete inputs so they can judge
  whether each proposed rule **follows from adopted human feedback**」。
- `:70`–`:77` **验收判据里嵌了真实观测数据**（这一点非常值得学）：
  > 「**Observed on 2026-07-15:** 62 merged PRs scanned, 5 skipped …, **426 human feedback items
  > considered, 0 candidates surfaced.**」
  以及「distinct primary/secondary adapters completed adoption + analysis in ~8 minutes;
  **batch fail-closed handled one adapter id-hallucination without aborting the run**」。
  → **判据不是"应该能跑"，是"某天跑了，结果是这些数字"，并且把 0 候选如实写下来。**
  最后一条判据把「制度是否有用」也变成可检查项：
  「At least one candidate diff produced by this workflow is inspected by the operator and
  **promoted to `master` through a normal repository PR review**. **That PR is the evidence that the
  workflow can turn adopted feedback into shipped skill guidance.**」
- `:81` **Risk 第一条直指因果推断的软肋**：
  「**Causality inferred from committer timestamps.** … committer clock skew and rewrites still leave a
  **residual false-adoption window**.」——并说明更紧的做法（交叉引用 GitHub PR 事件流）**超出本工具范围**。

**它否决了什么备选及理由**（原文 `:59`–`:66`，8 条，全部照录）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 把工具放进本仓库 | 单维护者规模下，仓库维护开销（typecheck/lint/coverage/横切重构）**超过**签入源码与评审历史的价值。**保留为将来交接时的选项** |
| 记录每一次反馈时刻的 PR head | 因果隔离更好，但需要**持续运行的观察者、持久事件状态、重试、force-push 对账** |
| 持久化一个「已处理 PR」游标 | 重叠时间窗扫描便宜且**天然对当前 skill 幂等**，而游标状态**制造恢复与漏事件问题** |
| 每来一条评论就跑 | 评审波次会产生很多相关评论，且**缺少判断采纳所需的最终制品** |
| 把合并或线程 resolved 当作采纳 | **一个 PR 可以带着被拒绝的、被取代的、或有意未解决的反馈合并** |
| 自动创建或合并仓库改动 | 工具**先要有一段产出有用结果的记录**；维护者检视并通过正常评审晋升本地 diff |
| 从「被修掉的机器人发现」里学 | **源合约就是人类评审反馈**；作者类型在分析前就被过滤，**转发自动化发现的人类账号也被作者检查排除** |
| 用同一个评审者既当作者又当终审 | **独立判定能在没有根据的泛化进入 skill 之前把它暴露出来** |

---

### P-P6 `proposed/process/2026-07-26-remove-packed-session-fixture-migrator.md`（38 行，**全文**）
**标题**：Remove the packed-session fixture branch migrator
**命中主题**：**「临时的」与「永久的」必须能被区分**；删除的前置条件是活体证据而不是时间

- `:11` **问题定义**：过渡期结束后仍保留一个变更命令，会在**永久的只读快照检查**旁边
  「adds **a second apparent maintenance path**」——**两条看起来都对的路。**
- `:17` **精确切分：留什么、删什么**：保留 `session-fixture-layout.ts`、它的单测、以及快照检查
  （**它们定义并强制永久的规范布局**）；**只有面向分支的 writer 是临时的**。
  否决理由 `:25` 把这一点讲透：「Remove the canonicalization module with the CLI —
  **The module is not transition residue**: snapshot CI uses it to discover future fixtures,
  decode mixed physical records, and compare them with the canonical packed representation.
  **Removing it would also remove enforcement.**」
- `:15` **同一次改动里把所有指向该命令的链接一起删**（测试策略、ACP 快照 README、
  已实现的 packed-row Agent Note），并把 `session-fixture-layout.snapshot.ts` 里
  **命令相关的补救文案换成与命令无关的规范布局指引**。
  → **删一个命令 = 删掉所有指向它的引用 + 把诊断信息改写成不依赖它。**
- `:31`、`:38` **删除的前置条件是活体清点，不是"过了多久"**：
  > 「The removal therefore depends on **live pull-request evidence, not elapsed time**.
  > Retaining the command too long has a smaller operational cost but **obscures which mechanism is
  > permanent**.」

**它否决了什么备选及理由**（原文 `:23`–`:27`，3 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 无限期保留该命令 | 在唯一已知的迁移窗口关闭后，仓库里仍留着一个**全仓库范围的变更工具**；只读门禁已经提供了持久行为与诊断 |
| 把规范化模块与 CLI 一起删 | **该模块不是过渡残留**：快照 CI 用它发现未来的 fixture、解码混合物理记录、并与规范 packed 表示比较——**删了它等于删了强制** |
| packed rows 一到 master 就立刻删命令 | 更老的开放分支会被迫用**临时脚本或手工重生成快照**，冲突风险上升，且**已解码事件的保全更难评审** |

---

### P-P7 `proposed/process/2026-08-04-artifact-first-npm-baseline-publication.md`（114 行，**全文**）
**标题**：Artifact-first NPM baseline publication
**命中主题**：**「开发态能跑 ≠ 交付物能跑」**；不可变发布包；无原子事务时如何给出可实现的边界

**问题陈述的三段，每段都是一条可迁移的判据**：

1. `:9` **「源码能跑不证明发布物能跑」**：
   > 「Workspace links, TypeScript paths, tsx source loading, and residual `lib/` files in the working
   > tree **can supply files or dependencies that are absent from a published tarball**. Existing
   > built-artifact tests still read `lib/` **directly from the working tree**, so they do not verify
   > what `package.json#files` selects…」
   → **在你的开发环境里通过的测试，测的可能不是你要交付的那个东西。**
2. `:11` **没有跨包事务时，诚实地把承诺降级到能兑现的那一句**：
   > 「The npm registry has no cross-package transaction, so **"publish once" cannot promise an atomic
   > commit**. **It can promise** that the complete publication set is packed and validated
   > **before any remote write**, then published from that immutable set by one resumable
   > orchestration command.」
   → **这是本篇最值得抄的措辞法：先说清楚"我承诺不了什么"，再给出"我能承诺什么"。**
3. `:13` **要为将来的 CI 复用留接口**：将来的 GitHub Actions workflow 必须复用同一个发布包与校验逻辑，
   **「It must not rebuild a different, untested set of tarballs after publication is approved.」**

**核心机制：不可变发布包（immutable release bundle）作为边界**（`:17`）——
pack 阶段从**一个固定 Git commit** 构建、打包、校验内容、并跑通**已安装制品的集成测试**；
publish 阶段**只读那些 tarball 与它们的 manifest，被禁止重新构建或重新打包**。

**几条可直接迁移的细则**：

- `:19` **目标集合靠发现而不是手工名单**，且**发现本身要 fail-closed**：
  拒绝重名、拒绝混杂的 base 版本、拒绝非预期的发布私密状态、拒绝 bundle 里出现未知包——
  「instead of relying on another hand-maintained package-name list」。
- `:21` **版本号自带来源信息**：`<base>-<YYYYMMDDHHmmss>-<short-commit>`，
  且**重试同一个发布包必须保留其版本与 manifest；重新打包才产生新时间戳的版本**。
- `:26` **隔离掉调用者的工作区状态**：在**独立的 detached worktree** 里按冻结 lockfile 安装，
  「Uncommitted files and old build output from the caller's working tree **must not affect publication**.」
- `:31` **release manifest 记 commit / version / tag / registry / 每个 tarball 的路径、SHA-256、npm integrity**
  ——这就是一份「交付物证据链」。
- `:45`–`:47` **两个平面分开校验**（很精细的一条）：源码平面可以保留 `exports["./src/*"]`，
  但它**不进发布载荷、也不是消费者合约**；静态门禁必须**分别**检查源码平面与发布载荷，
  > 「**deleting the source export must not hide broken workspace resolution, and publishing `src` must
  > not repair missing build artifacts.**」
  并且除了静态 manifest 约束外，**还要有一个独立的 tarball 内容门禁**确认不存在
  `package/src/**` 或 `package/**/*.d.ts.map`——**防止 manifest 模式或 pack 行为绕过静态约束**。
- `:53` **集成测试把「被禁止的解析输入」列成清单**：tsx、tsconfig paths、workspace links、
  仓库源码路径、工作区 `lib/`、**以及"从已发布 registry 装同一个版本"**，全部禁止；
  必须用 plain Node 与包管理器产出的 `node_modules`，并断言关键模块与 bin
  **解析到临时消费者内部的真实路径**。
- `:60` **一条判据把"覆盖到了没有"变成可证伪**：安装后的默认 `dsh` 必须在 PTY 里完成一次无密钥 TUI 启动，
  「This path must load the real TUI dynamic chunk, so **a missing publication file such as
  `lib/tui-*.js` fails the gate**.」（验收判据 `:101` 更进一步：**删掉任一必需动态 chunk 必须让测试
  确定性失败**——**用"故意破坏能否被抓到"来验证门禁本身。**）
- `:64` **明确这类测试不替代什么**：「These tests prove executability;
  **they do not replace unit tests, snapshots, real-API e2e, or publint.**」
- `:68` **不让用户级配置改写操作**：每次 publish **显式传 registry 与派生的 tag**，
  「so a user-level `.npmrc` **cannot redirect the operation**」。
- `:70` **幂等恢复的三分支写成封闭枚举**：远端不存在 → 上传；存在且 integrity 与 manifest 一致 → 跳过；
  **存在但内容不同 → 立即失败**。
- `:72` **失败后的规矩**：pack/tarball 检查/集成测试失败 → **registry 收到零次写入**；
  publish 部分上传后失败 → **用同一个 release manifest 重跑，不许改打成另一个时间戳版本**。
- `:80` **凭据只注入 publish job**，pack-and-test job **读不到发布凭据**；
  且 publish 必须用**同一次 workflow run 产出的 bundle**，而不是**按版本号去某个不可信来源找 tarball**。
- `:114` **Risks 最后一条把"部分可见"这个不可消除的缺陷说明白，并给出操作规则**：
  > 「Recovery cannot remove npm's **partial visibility**. … Operators and automation must treat
  > **the final bundle verification, not one successful `npm publish`**, as the baseline-availability signal.」

**它否决了什么备选及理由**（原文 `:84`–`:94`，6 条，全部照录）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 从 workspace 递归发布 | **把打包与 registry 写入交织**，无法在第一次写入前证明整个集合，并且允许 workspace 解析与调用者工作区状态影响发布 |
| 只测工作区里构建好的 `lib/` | 那验证的是**构建树**而不是 `package.json#files` 选出的 tarball；**"工作区里有、tarball 里没有的动态 chunk"正是本提案要抓的失败** |
| 只跑 `dsh --help` | Commander 可以**在加载 TUI/Web/headless 动态入口之前就打印帮助并退出**；证明不了默认生产启动路径是完整的 |
| 发布 `src` 与 declaration map 来降低缺文件风险 | **源码平面不是生产运行时的兜底**；扩大载荷会**掩盖 bundle 闭包错误**，并把本地调试输出变成**意外的发布合约** |
| 要求真正的跨包原子发布 | npm registry **没有这种事务**；不可变发布包 + 完整的发布前校验 + integrity 比对 + 幂等恢复给出**可实现的边界**，同时**保留"部分上传可能被短暂看到"这条显式限制** |
| 审批之后在 publish job 里重新构建 | 已测试并上传的 tarball 会**失去内容同一性**；workflow artifact 与校验和必须**把测试输入直接带进发布** |

---

## 5. `implemented/architecture` 与 `implemented/process` 主题命中篇目

> **筛选方法（可复核）**：对 `implemented/architecture`（125 篇）与 `implemented/process`（69 篇）
> 跑五组 `grep -ril`（只对英文 `*.md`，排除 `*.zh.md`），对应本轮五个主题：
> ① 证据链/审计留痕/append-only/事件字段形状；② 拒绝建模为封闭类型；③ 模块边界与「谁拥有某个事实」；
> ④ schema 与结构化字段 vs 自由字符串；⑤ gate 在什么边界执行（fail-closed 的位置）。
> 命中面很宽（三组各命中 50–95 篇），因此**按「标题直接对应主题 + 多主题交叉命中」二次挑选**，
> 再对入选篇目**全文**读取。**未入选的命中篇目本轮只做了 grep 匹配，没有读**——见 §7 未读清单。

---

### I-A1 `implemented/architecture/2026-06-11-event-sourced-sessions.md`（28 行，**全文**）
**标题**：Event-sourced sessions with derived message history
**主题 ①③**

这是整个证据链体系的地基篇，短但每句都是约束。

- `:13` **单一真相源的定义**：
  > 「A `Session` is an **append-only log of typed `SessionEvent`s — the single source of truth**.
  > The LLM message history is ***derived*** from the log (`deriveMessages()`); raw stream chunks are
  > logged for token-level replay fidelity while **the assembled `assistant/message` event is
  > authoritative for derivation**.」
  → 注意它同时保留了**两种粒度**：原始 chunk（为了 token 级重放保真）与**装配后的权威事件**（为了派生）。
  **哪一个是权威被显式指定**，而不是留给读者猜。
- `:17` **顺序契约被写成一条可测的规则**：loop 在 `agent/pre-step` 之前认领 inbox 消息；
  只有在 enter 决定之后才开 `step/start`；然后在派生请求之前 append `user/message` 批次；
  provider 输出装配后作为 `assistant/message` **在工具派发之前** append，
  「**so the durable log records the exact message the tools follow**. **Regression tests pin that ordering.**」
  → **「日志里记的必须就是工具实际跟随的那条消息」**，且顺序由回归测试钉死。
- `:21` **唯一的备选与它的否决理由（本篇最锋利的一句）**：
  > 「A mutable message array with events fired as notifications — simpler, but **state and log can
  > diverge; with event-sourcing the log IS the state, so divergence is structurally impossible**.」
  → **不是"我们会小心保持一致"，而是"不一致在结构上不可能"。**
- `:28` **诚实写下代价**：派生成本随日志长度增长——
  「compaction is the intended mitigation, **not log mutation**」。

---

### I-A2 `implemented/architecture/2026-07-05-reconstructable-requests.md`（55 行，**全文**）
**标题**：Every LLM request is reconstructable from the session log
**主题 ①③⑤ —— 本轮对 finaudit 证据链最重要的一篇**

**核心原则一句话**（`:17`）：

> 「**Model-visible ⟺ durably referenced.** Anything that reaches a model request must be
> reconstructable from the session log and the immutable content-addressed objects it references.
> The **checkable consequence**: anyone holding the log, its referenced attachment objects, and the
> pinned code version reconstructs **every loop request byte-for-byte**.」

→ **这是「可独立复核」的最强形式**：不是"我们记录了输入"，而是**第三方拿着日志 + 引用对象 + 钉住的代码版本，
能逐字节重建出当时发给模型的请求**。对 finaudit 的直接映射：
**任何进入答案的东西，都必须能从证据链 + 内容寻址的不可变对象重建。**

**几条同样重要的次级设计**：

- `:17` **图片等二进制走内容寻址 + 双校验**：image-bearing 请求在适配器序列化期通过 `ctx.attachments`
  解析 `ImageAttachmentRef` 字节，「where **digest and recorded metadata verification** make the object
  lookup deterministic and **fail loud on missing or corrupt data**」。
  → **大对象不进日志，进的是引用 + 摘要；取的时候两头校验，缺失或损坏必须响。**
- `:17` **例外被显式圈出来并说明为什么**：compaction 的 summarize 一次性调用**不在该不变量内**，
  但它**把信封标量记进日志**（`compaction/summary.{provider, model, maxTokens}`），
  且其输入是「对已记录区域 + 被引用对象的确定性代码」——
  「outside the invariant **because only the loop marks request ownership**」。
  → **例外要有名字、有边界、有它自己的留痕方式。**
- `:19` **推论排序值得学**：前缀缓存稳定性是**推论 #1，不是标题**——
  「stability is **emergent, not managed**」；字节精确的审计/重放是推论 #2；
  带**可归因漂移**的 resume 与 fork 是推论 #3。
  → **把"我们真正在保证什么"和"由此免费得到什么"分开写。**
- `:23` **变更历史不可通过投影被篡改**：派生消息是**深冻结**的共享对象，
  「**mutating logged history through a projection is unrepresentable (it throws)**」；
  外部重建者折叠**同一个公共函数**在日志前缀上，「so **no two paths can disagree**」。
- `:25` **全量快照而不是增量**：`request/header` **总是写完整快照**，
  reason 三选一（`initial` / `resume` / `change`），`foldRequestHeader` 取最新那份；
  **legacy 的 `request/header-delta` 事件与被移除的 `fallback` reason 在 append 与 load 时都被拒绝。**
- `:29` **「开着的 step 就是重建边界」**：其 entered `user/message` 批次与任何新写的 `request/header`
  **先于请求派发**。原子认领之后再注入的，加入的是**后一个**请求。
- `:31` **强制手段是"自己不能给自己背书"**（本篇最值得抄的验证设计）：
  `dsh-agent-loop/invariant` companion **用一个全新的 `Session` 独立重建每个 loop 请求**，
  > 「**so the live cache cannot vouch for itself**」，
  然后在 `llm/stream` 处比对消息与折叠后的 header 字段。
  并且**正确性依赖序列有界的重建，而不是监听器顺序**。
- `:49` **后果第一条就是能力声明**：
  > 「A request that is not explained by the log **cannot be constructed by accident** — not by the loop,
  > not by a listener; **mutating a built request throws**; every header change is a
  > **durable, diffable log event**.」

**它否决了什么备选及理由**（原文 `:39`–`:45`，7 条，全部照录）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 客户端做真相源（字面照抄 MiniCode） | **日志之外的第二个可操作真相** —— 两者会漂移**而且没有任何东西会注意到** |
| 一个镜像日志的有状态传输客户端 | 复制会话状态，需要围绕监听器做回滚，**留下一条未记录的编辑路径**，且仍然重建不出 request header |
| 每次调用一份可自由变更的请求标量 | 一个监听器可以**零账目地**每次调用翻模型，**悄悄放弃了本设计要保护的 provider 缓存**。「Config is per-conversation logged state; **the waterfall proposes, the log records.**」 |
| 检测并报告（比对相邻请求、漂移时告警） | **事后才抓到；违规的请求已经构造出来并发出去了**。「Rejected for **interface-level unrepresentability**.」 |
| 事件驱动装配（只在收到变更信号时重渲染） | **一整类漏信号 bug**：中途注册的工具发的是 `tools/change` 而不是 `system-prompt/change`，第三方 provider 可能什么都不发。**每步渲染 + 值比对，零信号纪律依赖** |
| 自定义 header 增量编解码 | 减少了重复字节，但**复制了表示形式**及其 diff/apply/fallback 机器；全量快照**只保留一种重放表示** |
| 在 header 快照上加"变更字段"叙述列表 | **可由比较相邻快照派生**。`reason` 之所以保留，是因为**实例边界无法从快照值派生** |

---

### I-A3 `implemented/architecture/2026-07-31-goal-owned-durable-events.md`（33 行，**全文**）
**标题**：Goal-owned durable events
**主题 ①③ —— 「谁拥有某个事实」的一个干净样本**

- `:9`–`:11` **问题定义就是所有权错配**：把 goal 变更编码进一条 round-zero 的 inbox 消息，
  **让队列位置变成了领域提交点**，重放时还要去调和插入、准入、消息身份、来源元数据与渲染内容。
  一句话总结：
  > 「The goal domain needs durable state, but **it does not need ownership of pending model input.**」
- `:15` **每个事件带完整的变更后快照**（与 P-A3 的 whole-value rule 同源）：
  `goal/change` 「carries the **complete post-mutation goal snapshot** or a **revisioned clear tombstone**」；
  严格重放与 `goal` 投影**只折叠 `goal/change`**。
- `:17` **边界写成"永不"清单**：「The goal package **never inserts, claims, removes, or inspects inbox
  messages.**」
- `:19` **进程本地状态与持久权威被分开**：激活是进程本地的；
  **「The session log remains the only durable authority.」**
  且**重放的或外部 append 的变更默认是 disarmed**——**不因为重放而触发副作用。**
- `:21` **拒绝把持久化写成副作用**：领域**不自动**把每次变更投影进模型输入；
  将来若要"始终可见的 goal 上下文"，那是**一个单独的 context 插件、拥有它自己的 inbox 消息**，
  「**rather than a persistence side effect**」。
- `:31` **诚实标注残留风险**：「Direct session writers **remain trusted and can append malformed changes**,
  which the strict fold and invariant companion reject.」——**信任边界在哪儿、由谁兜底，都写出来。**

**它否决了什么备选及理由**（原文 `:25`–`:27`，3 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 保持 round-zero goal 消息作为持久记录 | **把领域提交耦合到队列变更**，并逼 goal fold 去理解认领与准入的调和——**而队列结果根本无法回滚领域状态** |
| 只从模型可见消息派生 goal 状态 | 一次变更**可以是有效且持久的却没有开 step**；**取消或策略拒绝不得抹掉它** |
| 把 goal 存进一个单独的数据库 | 有序会话日志已经提供持久化、重放与 fork 继承，**不需要第二个原子性边界** |

---

### I-A4 `implemented/architecture/2026-07-30-settings-write-path-integrity.md`（35 行，**全文**）
**标题**：settings write-path integrity and observer lifecycle
**主题 ①⑤ —— 「写入路径会毁掉它从未观察到的状态」**

- `:11` **问题被逐个具体化（不是"有并发问题"）**：两条独立的 promise 链 + 每次写都从缓存文本渲染整份下一版文档
  → **仍在 debounce 窗口内的外部编辑被覆盖**；而随后的 reload **no-op 了**，因为 rename 后的内容与缓存一致，
  于是**「erasing the edit without a trace」**。
  → **静默丢数据的完整因果链被写清楚**，这是 finaudit 该学的问题描述方式。
- `:15` **对策一：一条操作链 + 每次写都是 read-modify-write**：
  `persistSection` **先把磁盘文本调和进 seam、先把任何未被观察到的差异发布出去**，再针对这份新文本渲染。
  > 「A write can no longer resurrect a stale document, and **an on-disk document that turned invalid
  > fails the write loud rather than being overwritten**」
  并且**读路径与写路径的策略被分开**：共享的 `reconcileFromDisk` 抛出，**各调用方各自选策略**
  （reload 保持 warn-and-keep-last-good）。
- `:17` **对策二：跨进程写锁，且明确拒绝自动接管**：
  > 「A contender **times out without removing the existing lock** because **age cannot distinguish a
  > crashed owner from a paused live writer**; **orphan recovery is an operator action.**」
  读者**永不加锁**（rename 提交是原子的），所以争用只在写侧。
  **重试与截止常量是协议不变量，不是部署配置。**
- `:21` **对策四：写边界只接受 JSON 数据**：一次 `cloneJsonShaped` 走查，
  拒绝任何非 JSON 值（Date / Map / BigInt / 非有限数 / 函数 / symbol / 类实例 / `undefined` 数组项 / 循环引用），
  **并带上 `$` 根路径**。→ **在边界上拒绝，并把出错位置指给调用方。**
- `:23` **对策五：YAML 只做叶子级 diff**，注释/锚点/格式在每个未触碰节点上存活。

**它否决了什么备选及理由**（原文 `:27`–`:31`，5 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 用 `proper-lockfile` 而不是自己写锁 | **依赖优先政策被权衡过**：该库几乎无人维护，其所有权与重试策略**比这个单文件协议需要的宽**；「The policy favors dependencies that **delete owned code**; this one would replace a narrow protocol with **an opaque peer**」 |
| 用 revision/CAS 而不是锁 | **rename 表达不了 compare-and-swap**，CAS 需要版本 sidecar 或内容重哈希 + 每个写者一个重试循环；锁用一个原语达到同样的串行化**并让读者免锁** |
| 把外部编辑合并进在飞写入自己的 section | seam 在调用时刻可见的状态上合并 patch，同命名空间的外部编辑仍然是 last-write-wins；折进来需要**没有任何消费者要求过的三方合并**。**当前做法至少让失败者在被覆盖前被观察到** |
| 宣布不支持 async `settings/updated` 监听器 | 类型签名是 `void` 且 lint 会标记，但**未走 lint 的 JS 插件仍可注册 async 监听器**；**「a contract note cannot un-throw an unhandled rejection」**，运行期只有"包容"这一种防御成立 |
| 保留 `structuredClone`，改在 provider 侧校验 | Service Definition 才是**持久边界的所有者**；**在调用时刻拒绝能把出错路径给调用方**，provider 侧检查会在合并之后才拒，**把责任怪到被合并的 section 而不是调用方的值上** |

- `:35` **Consequences 里明确列出"仍然存在的问题"**：同命名空间并发编辑仍是 last-write-wins；
  OS 从未投递的 watcher 事件会让缓存陈旧到下一个信号或写入；
  被整体替换的数组里的注释、以及内联挂在被改标量上的注释**会随它描述的值一起消失**。
  → **把"没修的部分"写进 README 的 Known Limitations，而不是留白。**

---

### I-A5 `implemented/architecture/2026-07-20-unified-json-value-schema-dsl.md`（37 行，**全文**）
**标题**：Unified JSON-value schema DSL
**主题 ④ —— 「结构化字段 vs 自由字符串」最完整的实现篇**

- `:9` **问题定义**：工具参数用一套作者 DSL，subagent/workflow 的结构化输出用**另一套** JSON Schema 子集
  与另一个校验器，两套词表**在根类型、标量约束、校验上互相不一致**。
- `:13` **一套词表、两种表示**：`ValueSchemaSpec`（作者形式，任意 JSON 根）/
  `ParameterSchemaSpec`（其隐式的对象属性映射形式，逐属性 `required: true`）/
  `JsonSchemaNode`（原始线形式）。
- `:15` **本篇最锋利的一条：让「同一份声明被三个环节看成不同东西」在结构上不可能**：
  显式的作者对象**必须声明 `additionalProperties: true | false`；
  schema 记录只含自有可枚举字符串键；schema 数组是稠密的固有数组；关键字按自有属性读取**——
  > 「custom prototypes, inherited constraints, symbols, and JSON-invisible decorations therefore
  > **cannot make compilation, projection, and validation observe different declarations**.」
- `:17` **类型推断的深度上限被显式设定为一个设计选择**：`InferValue<S>` 精确推断**限 16 层容器**，
  之后退化为 `JsonValue`，「**preventing TypeScript's type-instantiation stack from becoming the
  authoring limit**」；而**运行期的 schema 强制在每一层都保持精确**（`:34`）。
  → **编译期能力有限是事实，就把它变成一条有界的、写明的退化规则，而不是让它变成隐形的写作上限。**
- `:17` **无损 JSON 边界的拒绝清单**：`validateJsonSchemaValue()` 拒绝
  `undefined`、负零、非有限数、稀疏数组、循环、异型对象、函数、symbol 及其它强制转换值。
- `:19` **「对象根」是消费者规则而不是词表限制**——subagent/workflow 用 `assertObjectJsonSchema()`，
  工具输出可用任意根。**同一个词表，不同消费者各自收紧。**

**它否决了什么备选及理由**（原文 `:23`–`:27`，5 条，全部照录）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 保持参数与结构化输出两套 schema 系统 | 每加一个输出构造都要**并行改推断、编译、校验、代码生成**，而**得不到有用的所有权边界** |
| 工具参数改用 Schemastery | Schemastery 面向的是**通过 Standard Schema 做校验与转换**，不是生成 JSON Schema；会加一层适配器却**产不出面向模型的线 schema**，也产不出共享的输出词表 |
| 采用完整 JSON Schema 或 Ajv | harness **必须对每一个它无法投影进生成 SDK 与校验器的构造失败**；接受更大的语言会让**强制与对模型的指引变得不诚实（dishonest）** |
| 让所有对象隐式开放或隐式封闭 | 两种选择**都会藏起一个有后果的作者决定**；只有旧形状的隐式参数根与外部原始 schema 保留有意的默认 |
| 把 `oneOf` 定义成 first-match | **分支顺序会改变校验语义**，并让重叠分支**藏起有歧义的值** |

- `:33`、`:35` 两条后果值得抄：
  「Explicit object openness and type-correct literal constraints make **malformed declarations fail
  during authoring or registration rather than during a later model call.**」
  「Raw tools may still register broader JSON Schema directly, but unified code generation treats
  **unsupported schemas as unknown instead of pretending to enforce them.**」
  → **不能强制的，就明确标为 unknown，不假装强制了。**

---

### I-A6 `implemented/architecture/2026-08-10-message-feedback-sidecar.md`（43 行，**全文**）
**标题**：Lifecycle-bound message feedback sidecar
**主题 ①③⑤ —— 「什么该进日志、什么该进 sidecar」的判据**

- `:9` **判据一：可编辑的东西不能进不可变的日志**。
  `/feedback` 记的是**不可变的 Session 级 `feedback/record` 事件**，而消息级评分**需要独立的更新与删除语义**，
  且**不得进入规范会话日志、不得改投影、不得进模型上下文、不得隐含同意遥测**。
- `:17` **判据二：sidecar 的键必须绑定生命周期身份，不能只绑 id**：
  每一行绑的是**被检视的 Session header 身份 `{createdAt, cwd}`**，不只是 `SessionId`；
  **身份不匹配一律视为不存在**（`list` 返回空，`put` 可以用当前身份的新行替换陈旧行）。
  > 「An id reused with a different header identity therefore **cannot inherit stale feedback**.」
  fork **不复制 sidecar**：「even when the fork seed contains the same assistant messages,
  **feedback remains attached to the Session in which the human recorded it**。」
  → 对 finaudit 直接适用：**人工复核结论绑的是"在哪次会话里做出的判断"，不能被 fork/重跑继承。**
- `:21` **判据三：留痕不得早于它引用的事实**（本篇最值得抄的一条）：
  `put` 提交 sidecar 行**之前**先把目标日志推过一道**持久化屏障**——
  活 Session 过 `ctx.sessions.flush` 检查点，然后**冷热两条路径都从序号 0 物理读取**，
  再检查一次 header 身份与目标。
  > 「A missing flush participant, changed identity, vanished target, or physical-read failure prevents
  > the sidecar write, so **a committed feedback item never precedes the durable assistant message it
  > references.**」
- `:23` **判据四：版本是等值令牌，不是计数器**：
  「Versions are **tokens for equality, not counters callers may order or synthesize**.」
  逐条目比对 `ifVersion`（**编辑一条消息不会作废另一条**）；
  **即便目标值已经等于期望值，比较仍然是严格的**——「preventing a stale request from **crossing an ABA
  value cycle**」；冲突时**返回权威的当前条目**，让调用方不用再读一次就能调和。
- `:25`、`:29` **两处诚实的能力边界声明**：
  「The underlying storage-domain API provides **no cross-process conditional write**, so the
  implementation **claims no cross-process linearizability or lost-update protection**.」
  「The service performs **no fake deletion cascade**. `session/disposed` and `host/session-removed`
  describe **detach from live ownership, not durable Session deletion**…」
  → **不做假的级联删除，不声称做不到的保证。**

**它否决了什么备选及理由**（原文 `:33`–`:39`，4 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 把编辑 append 进会话日志、派生一个投影 | **可编辑的 UI 元数据会变成规范的、与对话相邻的历史**；fork 会重放并继承它；删除要靠墓碑；**复用 `feedback/record` 会把消息评分静默耦合到遥测同意** |
| 用 `MessageId` 全局做键 / fork 时复制 / 用一个 Session 级 revision | 消息 id **只在一个 Session 生命周期内有意义**；fork 出的对话需要**独立的人类判断**；不相关的消息变更**不得制造假冲突** |
| 本次就给 `KvTable` 加跨进程 CAS | 已发布的存储后端**没有共同的条件写原语**；进程本地队列匹配当前单 Host 拓扑，真正的多进程保证**需要后端级原子契约，是独立工作** |
| Session 释放时删除反馈 | 释放包含**普通 detach 与回滚路径**；把它当持久删除会**在日志仍然存在时丢掉反馈** |

---

### I-A7 `implemented/architecture/2026-08-10-session-log-version-mechanism.md`（30 行，**全文**）
**标题**：Session log versioning — one integer, an upgrade chain, and a per-event ignorable marker
**主题 ①⑤ —— 「第一个发布的读取器就是所有后续决策的地板」**

**问题陈述里最值得抄的一句**（`:9`）：

> 「Session logs must be upgradable after release, and **the runtime that ships first is the floor for
> every later decision: whatever refusal and degradation behavior is missing from the first released
> reader can never be added to the copies users already run.**」

→ **对 finaudit 的直接迁移：证据链/冻结格式的"拒绝行为"必须在第一版就到位，
因为你没法给已经发出去的读取器补上"遇到不认识的东西要拒绝"。**

- `:13` **一个单调整数，不做 major/minor 拆分**：
  「Whether a version step is auto-upgradable is **a property of that step — expressed by whether its
  upgrader exists** — not something a two-level numbering scheme should promise in advance
  (**you rarely know at design time whether the next change will turn out "major"**).」
- `:15` **什么时候必须 bump，判据写得极清楚**：
  > 「**"Parses without error" is not the bar: silently skipping content that shapes reconstruction is a
  > wrong read.**」
  只有结构性变化才算（header 形状、事件信封、核心事件语义、surface 机制）；
  **「When unsure, bump: a near-identity upgrader is almost free, a missed bump silently corrupts old readers.」**
- `:17` **按方向分读规则**：版本相同 → 正常读；**比读取器新 → 拒绝，并指明方向**
  （"written by a newer harness — upgrade"）**并指向原始日志制品让用户仍能看到文本**，
  用的是**独立的错误类型** `SessionFormatUnsupportedError`（**与 `SessionPersistenceCorruptionError` 区分开，
  因为"没有任何东西损坏"**）；比读取器旧 → 内存里过 n→n+1 升级链**供查看**，
  **只有在会话真的被继续时才落盘转换后的日志**（原子临时文件替换，原件留备份）。
- `:19` **默认值的方向由失败后果决定**（本篇最锋利的设计论证）：
  未识别的事件类型**默认拒绝解释整个日志**，除非该事件在信封里带 `ignorable: true`。
  > 「The default is *required*: **forgetting the marker over-refuses a resumable session (an
  > inconvenience), while a default of ignorable would make the same mistake silently resume a gutted
  > one (a safety failure).**」
- `:23` **闸门放在读侧而不是写侧，理由是成本比较**：
  「an append-time refusal would **stall a live session's durability mid-flight**, which costs more than
  a loud refusal at the log's next load」。
  且 JSONL 后端**在校验今天的 header 形状或解码任何事件行之前，先从原始 header 行拒绝陌生版本**，
  「so a structurally different future format **still reports the upgrade direction instead of "corrupt"**」。
  → **报错要报对类别；把"格式更新"误报成"文件损坏"会把用户引向错误的处置。**

**它否决了什么备选及理由**（原文 `:27`–`:30`，4 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| major/minor 版本 | 「是否可转换」这个比特**活在每一步的 upgrader 上**；把它预先烧进数字形状**招致错误的承诺** |
| 未知事件默认可忽略 | 把"忘了标记"的失败模式**从可见的过度拒绝反转成静默损坏** |
| 查看时自动迁移 | **把一次读变成一次破坏性写**：转换器的 bug 会在浏览时损坏日志，且同目录下更老的运行时**仅仅因为新的看了一眼就失去访问** |
| 让插件在运行期注册已知事件类型 | 会让已知集合**依赖于组合**，于是**同一版本下更精简的组合会拒绝更完整的组合写出的日志** |

---

### I-A8 `implemented/architecture/2026-07-28-api-browser-trust-boundary.md`（31 行，**全文**）
**标题**：One carrier-level browser-trust boundary for all `/api` routes
**主题 ⑤ —— fail-closed 的位置：一次、在载体层、覆盖整个前缀**

- `:9` **威胁被具体到机制而不是"有安全风险"**：`session.prompt` 驱动一个会跑 bash 的 agent；
  浏览器把操作者变成 confused deputy 的两条经典路径被分别写出（`text/plain` 的"简单"跨站 POST 副作用会执行、
  以及 DNS 重绑定让 CORS 完全不适用，**只有 `Host` 头出卖攻击者的域名**）。
  改动前系统**唯一**的浏览器信任检查只守着一个**装饰性路由**，「**while every consequential method was
  unguarded**」。
  → **闸门守在最不重要的门上，是本轮反复出现的一类失败。**（与第一轮 C-5 的
  「把一个防护措施当成别的边界用就是错」同源。）
- `:13`–`:16` **对策是一次、在载体层、对整个 `/api` 前缀**，两半：
  **媒体类型栅栏**（每个 `/api` POST 必须声明 `application/json`，否则**在解析之前** 415）——
  于是「Cross-site "simple" requests **thereby stop existing**」；
  **权限栅栏**（每个请求的 `Host` 必须是 loopback 或匹配 `trustedHosts`）。
- `:16` **拒绝给"无标记请求"开捷径，理由必须整句抄**：
  > 「over plain HTTP a browser attaches **neither `Origin` nor Fetch-Metadata to reads** (EventSource,
  > images, navigations — those headers go only to trustworthy destinations), so an unmarked request
  > **may be a rebound browser read whose response the page can read**, and **Host is the one header
  > rebinding cannot forge**.」
  → **不能因为"看起来不像浏览器"就放行；要找到那个攻击者伪造不了的字段。**
- `:16` **配置本身也 fail-closed**：一个不是裸的、规范权威形式的 `trustedHosts` 条目
  **会让插件加载失败**——「WHATWG parsing would otherwise **quietly authorize the hostname inside a typo**
  or broaden an exact-port grant」。
- `:18` **两条边界被显式划到范围外并说明归属**：可达性是 webserver 绑定的策略；
  真正远程部署的认证是**记录在 connection README 里的待办**——
  「**the fence is a confused-deputy defense, not an auth layer.**」
  → **不把一个防御吹成另一个防御。**
- `:28` **后果第一条是"由构造保证"**：
  「Any future `/api` method is **covered by construction**; there is **no per-route trust decision left
  to forget**.」

**它否决了什么备选及理由**（原文 `:22`–`:24`，3 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 逐 RPC 加守卫（延续现状） | **守卫清单永远追在方法清单后面**；价值最高的方法本来就没被守；且对浏览目录类 RPC 加 loopback 规则**会打断它们存在的意义（远程部署）** |
| 加 CORS 头 + 省略凭据 | **我们根本不想要任何跨源读**，回答 preflight 只会**扩大攻击面**；拒绝它们**严格更强也更简单** |
| 现在就上 auth token | token 的铸造/存储/轮换**是真实的产品面**；栅栏**今天就堵上 deputy 漏洞，而不预先决定 auth 设计** |

---

### I-P1 `implemented/process/2026-06-11-quality-gates.md`（30 行，**全文**）
**标题**：Mechanical quality gates over prose guidelines
**主题 ⑤ —— 这条制度的立论根据**

- `:11` **立论**（对 finaudit 这种「主要由 agent 开发」的项目直接适用）：
  > 「This codebase is developed primarily by coding agents. **Agents follow enforced gates far more
  > reliably than prose conventions**, and **"a lot of work" is not a cost argument when agents do the
  > labor.** Early evidence: **tests that didn't typecheck shipped** (vitest doesn't typecheck) and were
  > only caught by a review.」
  → 「工作量大」在 agent 干活时**不构成反对理由**——这条可以直接搬进 finaudit 的门禁讨论。
- `:15` **规则本身**：「**Every mechanically checkable AGENTS.md promise gets a command that exits
  non-zero.**」CI 跑穷尽集合，Git hook 只花预算在**便宜的本地缺陷**上。
- `:20` **一条很实用的覆盖率规则**：不可达的防御性分支带 `/* v8 ignore */` **并写明理由**，
  **而不是删掉它**。
- `:26`–`:28` **后果里有两条自我批评**：
  「**The gates themselves are code to maintain**」；
  「**100%-coverage pressure can produce assertion-free tests** — mutation testing is the planned
  counterweight」——**知道自己的门禁会产生什么副作用，并指名对冲手段。**
- `:7` 顶部一行**局部被取代声明**：hook/CI 对称性已被 2026-07-22 的 fast-local-git-hooks 取代，
  「**CI remains the exhaustive enforcement path**」。

**备选**：`:30` **原文未记录备选**（带 `alternatives-not-recorded (pre-format Agent Note)` 标记）。

---

### I-P2 `implemented/process/2026-07-26-frozen-agent-note-archive.md`（45 行，**全文**）
**标题**：Freeze low-future-value Agent Notes outside the active corpus
**主题 ①③ —— 冻结 + 哈希 + append-only manifest（与 finaudit 的冻结校验同构）**

第一轮 §2 已从 README 侧记过这条制度，本篇是**它自己的决策记录**，细节更硬。

- `:9` **成本论证**：implemented note 是**被维护的当前决策记录**，
  所以其中每一个路径、符号、默认值、翻译、代码块、包引用、外链**都是一项义务**。
- `:13` **保留边界（哪些永远不归档）**：
  「**Foundational boundaries, durable and wire semantics, security rules, recurring design temptations,
  and unresolved reintroduction conditions remain active regardless of age or word count.**」
  且**proposed 永不进档案**——**「an obsolete proposal becomes rejected」**（不许靠归档躲掉裁决）；
  rejected 只在它**还能阻止一个诱人且有意义的错误**时保留，否则**整个三元组删除**。
- `:15` **归档时只允许四种改动**：移动三元组、保留 `Status: implemented`、
  紧随其下插入 `Archived: YYYY-MM-DD`、以及 sidecar 重录与机械性的入链修复。
- `:19` **冻结之后的地位被写死**：
  > 「After archival, the triplet is **permanently frozen and is historical context rather than current
  > authority.** It is **not updated** for renamed packages, changed behavior, translation standards,
  > formatting rules, broken outbound links, or later documentation contracts.」
  并且**门禁的方向是单向的**：「Repository gates therefore **validate links into archived files but never
  treat archived files as link sources.**」
- `:21` **冻结的机械保障（finaudit 冻结校验可直接对照）**：
  `verify-archived-agent-notes` **只接受封闭的 kind 集合**，要求完整三元组、implemented 状态、
  有效且匹配的归档日期，**对照当前 Git blob 哈希校验 sidecar**，
  并**在一个 append-only manifest 里按路径 + SHA-256 内容哈希封存每个制品**。
  `--write` 模式**先证明每一个既有封条未变，然后才追加新归档的制品**。
  > CI **supplies the trusted base SHA and checks out complete history** before running the verifier,
  > **so a reused runner's shallow checkout cannot omit the baseline manifest.**
  → **这条对 finaudit 极其重要：浅克隆会让基线清单缺失，从而让"全部通过"变成假阳性。**
- `:25` **取代检查发生在写新 note 的时候，不是延后到语料清理**：
  「**the author of a replacement note has the freshest evidence about ownership and overlap**」。

**它否决了什么备选及理由**（原文 `:29`–`:41`，7 条，全部照录）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 离开活跃语料的 note 一律删除 | 一份 implemented 记录**可以前向指导价值低、但仍提供关于一个已关闭决策的有用历史证据**；内容封存的档案保住证据**而不假装它仍然当前** |
| 所有 implemented 与 rejected 都保持活跃 | 维护成本与搜索噪声**随着不再帮助未来决策的记录一起增长**；rejected **只有靠阻止一个可信的谬误才赢得保留** |
| 让归档 note 留在默认搜索结果里 | 归档事实**按设计可能是陈旧的**，且**可能靠字面匹配盖过当前结果** |
| 把取代清理延后到周期性语料审计 | 替换 note 的作者**掌握着关于所有权与重叠的最新证据**；推迟会**留下冗余的活跃权威**并让后来的分类更贵 |
| 也归档 rejected 或 proposed | 档案状态的含义就是「**implemented 的历史决策**」；过时的提案需要一个**显式的拒绝**，而没有护栏价值的拒绝**需要的是删除，不是第二个低价值仓库** |
| 继续对归档 note 施加全部文档门禁 | 后来的格式/翻译/代码/包/链接规则**会要求重写历史快照** |
| 允许事实性刷新、只冻结论证 | 那会**重建活跃语料的判断与翻译负担**，并让**哪些从句是历史的变得不清楚** |

---

### I-P3 `implemented/process/2026-08-09-committed-artifact-citations.md`（37 行，**全文**）
**标题**：Cite committed artifacts, never design-session ordinals
**主题 ① —— 「引用必须能被独立解析」，与 finaudit 的证据链引用规则完全同构**

- `:9` **问题的具体形态（值得对照 finaudit 自查）**：大型设计/评审会话留下的工作简写——
  决策序号、审计条目代码、计划章节号、任务与 stack 序号、评审裁定——
  > 「**reads naturally while the session transcript is open and resolves to nothing after it closes**」。
  仓库级审计发现：`(decision 12/16/19/20/21)` 中**只有 decision 21 有一个已提交的所有者**；
  `(audit C2/S1/S3/S7)` **在任何地方都没有对应的审计文档**。
- `:13` **规则一句话**：
  > 「Durable prose … cites **only committed artifacts, resolvable in-repo without grep archaeology**.」
  可引用的三种：**拥有该决策的 Agent Note（每个文件至少出现一次它的路径 + 行内一个可搜索的名字）、
  文档页路径、GitHub issue 号**。PR / commit / branch / stack 位置在文档与代码里**一律禁止**。
- `:16` **有主的序号换成名字，无主的序号直接删掉并把事实从句改写成能独立成立**：
  「An ordinal **without an owner is deleted and its factual clause restated to stand alone**.」
- `:17` **已修复的回归写成现在时反事实，而不是仓库历史**：
  「**pinned as present-tense counterfactuals ("without X, Y happens"; "a naive X would…"),
  never as repo history ("used to Y")**」。
- `:19` **豁免清单是封闭的**：录制 fixture、快照、归档 note 豁免——
  「recorded model output and sealed history keep their original voice」。
- `:31` **Verification 段落诚实写出覆盖缺口**：
  > 「**Coverage gap: no gate rejects a new ordinal citation — review owns the rule.**」
  → **知道哪条规则没有机械门禁，就明写出来由谁兜着。**

**它否决了什么备选及理由**（原文 `:25`–`:27`，3 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 把设计台账与审计文档提交进仓库，好让序号能解析 | 会话记录是**工作制品、不是被维护的参考**；提交它们会在 Agent Note 旁边**造出一套平行的、无门禁的决策语料**，而且**它们内部的编号仍然会漂移** |
| 为被禁词表做一个机械门禁 | **延后**：该词表是**无界的自然语言**，审计的召回集需要判断力去区分泄漏与合法用语。给出了一个**高精度窄门禁的候选正则清单**，并说明**purge 自身的评审恰好在那些搜索漏掉的情形里抓到了残留**，所以它们排在候选首位 |
| 把引用了死制品的论证整段删掉 | 事实性从句被**保留或改写**了；**只删引用、评审编排与推导过程**（依"完整命题"规则） |

---

### I-P4 `implemented/process/2026-08-08-browser-gif-evidence-chain.md`（37 行，**全文**）
**标题**：Browser GIFs preserve one evidence chain
**主题 ① —— 「每一帧都真实」不等于「证明了一次真实执行」**

**问题陈述第一句就是本轮最可迁移的一句话**（`:9`）：

> 「A browser-demo storyboard can contain **individually truthful screenshots without proving one
> truthful execution**.」

→ 对 finaudit：**每一条证据单独看都成立，不等于它们来自同一次可复核的执行。**

- `:15` **一个 storyboard = 一条证据链，钉在一个精确的 PR head 上**：
  构建前要求**干净工作树并记录该 commit SHA**；每次运行用**全新的** `DSH_HOME`、`DSH_AGENTS_HOME`、
  workspace、session 与隔离的浏览器状态；**每一帧发布出来的画面都来自同一台服务器、同一次模型驱动的场景运行**。
  > 「**A failed capture run is discarded and repeated from fresh roots rather than combined with another
  > run.**」
- `:17` **要求暴露"不利证据"**：当结论涉及工具调用、拒绝或恢复时，
  storyboard **必须包含一帧**标明工具、显示其状态或**稳定的错误码**、并显示下游结果。
  → **不许只展示"成功的兜底"而藏起导致兜底的那次拒绝。**
- `:17` **验证对象是最终产物本身**：「The **final encoded GIF remains the verification subject**;
  when a viewer cannot animate it, representative frames are **decoded from that GIF** instead of
  treating source screenshots as equivalent evidence.」
  → **验证要针对交付物，不针对中间件。**（与 P-P7 的 artifact-first 是同一条原则的两个领域。）
- `:19` **什么不能作为"真实生产"的佐证，列成封闭清单**：
  「**Fixtures, mock transports, synthetic events, and test-only hooks do not substantiate a
  real-production claim.**」若必须替换某个原生界面，**只能通过正常的应用配置切到官方的、可被浏览器操作的
  生产后端，并且要在 GIF 旁边写明这个覆盖**。
- `:21` **发布环节再验一次边界**：私有仓库的资产要用**带认证的 API 或 raw 请求**检查
  **路径、字节大小、校验和、响应状态与媒体类型**；
  **在 PR 正文改动之前，live head 必须仍等于记录的 head；改完之后再查一次**，
  且 **GitHub 的 Markdown 渲染器必须真的产出预期的图片**。
  → **「推上去了」不等于「拿得到」；「拿得到」不等于「渲染出来了」。**

**它否决了什么备选及理由**（原文 `:25`–`:31`，4 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 当不同运行的帧"看起来状态一样"时允许混用 | **视觉相似性并不确立共享状态、因果顺序或同一次场景执行**；重录多花一轮真实成本，但**保住了 storyboard 所声称的那个命题** |
| 用聊天记录作为工具恢复的充分证明 | 最终答案只证明任务完成了，**它可以藏起哪个工具跑了、失败是否是结构化的、以及模型是否真的从那次失败中恢复** |
| 用 fixture 或测试钩子替换无法自动化的原生 UI | 那是**通过改变被观察的产品路径来让自动化更容易** |
| 相信一次成功的 assets 分支 push 或一次匿名 fetch | push **只证明 git 接受了字节**，而私有仓库**故意拒绝未认证的 raw 请求** |

---

### I-P5 `implemented/process/2026-08-09-concrete-prose-names-actors-and-recorded-facts.md`（35 行，**全文**）
**标题**：Concrete prose names actors and recorded facts
**主题 ①③ —— 「说清楚记录了什么、以及谁记录的」**

- `:9` **问题**：同一个抽象标签可以指**被某次替换引用的更早事件 seq、产出该消息的 provider 与 model、
  提供上下文的调用方、提供某行配置的文件、或构建二进制的 CI job**——
  「Readers had to **inspect code before they could tell which fact the sentence promised**.」
- `:15` **规则**：
  > 「Maintained prose names the exact **actor, action, source, event, field, file, or process** needed
  > by the local contract. **It states what was recorded and who or what recorded it.**」
  并附一条可操作的自检：**「a spoken-language check」**——把你不会用来向同事解释同一件事的词换掉。
- `:17` **审计粒度是句子级**：「An audit judges **each sentence separately**;
  it does **not replace a term across the repository with one preferred synonym**.」
  被编辑的句子必须保住**actor、action、条件、顺序、情态、例外、所有权、失败行为与后果**。
- `:19` **代码标识符不因文风改动而改名**：公共 API、持久字段、协议成员、类型名、文件名保持不变，
  「unless a coordinated contract rename is **independently required**」。
- `:21` **对三个高频抽象词给出替换检查表**（可直接搬进 finaudit 的写作规范）：
  用 `contract` / `boundary` / `shape` 之前，先检查这句话是不是指一个更具体的
  **规则、操作、数据结构、字段集合、校验点、时间点、API、类型或失败条件**；
  三个词各自"仍然正确"的场景也被列出（`contract` 用于前置/后置条件、不变量、兼容承诺；
  `boundary` 用于**字面**的安全、信任、线、进程、序列化、事务或生命周期划分；
  `shape` 用于结构形式本身就是主语、且没有更窄的词能表达时）。

**它否决了什么备选及理由**（原文 `:27`–`:31`，3 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 禁用一份固定的词表 | 一个词**可能就是精确的标识符**，或者在另一个语境下就是最清楚的说法；**句子级评审能抓到歧义而不误杀合法用法** |
| 把每个抽象标签都替换成 "source"/"origin"/"metadata" | **另一个宽泛标签仍然让读者去猜**这句话指的是文件、调用方、事件 seq、provider/model 对、commit 还是构建 job |
| 让标识符跟着散文一起改名 | **编辑性的清晰不足以正当化**无关的 API、协议、持久格式、类型或文件迁移；那些改动**需要它们自己的消费者审计与决策** |

---

### I-A9 `implemented/architecture/2026-08-04-configuration-source-ownership.md`（73 行，**全文**）
**标题**：One ordering for configuration sources, and what a discovered file may not decide
**主题 ③⑤ —— 「被发现的文件可以决定什么、不可以决定什么」**

- `:9`–`:15` **问题定义方式值得学**：一个改动（把 `$DSH_HOME/.env` 变成普通环境层）导致
  「the harness resolving user-facing values from a flattened `process.env`
  **that could no longer say where a value came from**」，随后**三条后果被分别写出**，
  其中第二条是真实的攻击面：
  > 「a `DEEPSEEK_BASE_URL` written into **a workspace the model can edit** would send the user's own
  > credential, and the prompts carrying their code, to whatever host that file named.
  > **Nothing about the flattened view could distinguish that from the operator exporting the same
  > variable.**」
  → **丢掉"这个值从哪来"这一信息，本身就是一个安全缺陷。**
- `:19`–`:28` **非机密值只有一套顺序**（六层，从"本次运行的显式值"到"默认值"），
  **各领域的差别只在"哪些层存在"**。
- `:32`–`:41` **机密保持一套更窄的、独立的顺序，而且明说本篇不统一它们**。
  为什么"启动环境赢"的理由写得极好：
  > 「because `DEEPSEEK_API_KEY=… dsh`, a CI secret, and a container `-e` are **the one override an
  > operator must be able to apply per run without editing machine state**, and because **it cannot be
  > edited from inside it must be *visibly* read-only**.」
  并且**配置只承载引用（resolve 哪个名字），那个名字走非机密的顺序**。
- `:45`–`:47` **本篇最重要的一条闸门：被发现的文件不得改变 harness 自身**。
  `loadLayeredEnv` **在加载时、在任何东西被物化之前**拒绝任何设置了以下变量的 `.env`：
  控制进程如何启动的（`PATH`/`SHELL`/`NODE_OPTIONS`/`LD_PRELOAD`）、
  控制运行时在跑目标程序**之前**先执行什么代码的（`BASH_ENV`/`PERL5OPT`/`PYTHONSTARTUP`/`RUBYOPT`/
  `JAVA_TOOL_OPTIONS`/Git hook 命令）、
  控制**模型可见指令从哪加载**的（**整个 `DSH_*` 命名空间**、`HOME`、`XDG_*`）、
  以及网络如何被到达与信任的（proxy 与 CA 变量）。**匹配大小写不敏感**，`https_proxy` 不是绕过口。
  判据整句：
  > 「The line is that these take effect **with no user action, before any turn, outside the permission
  > policy and the sandbox**. … **the project's code running under the agent's policy is the deal;
  > the project rewriting that policy is not.**」
  并且**明确拒绝开逃生口**：「**There is no opt-out: an escape hatch would have to be readable from
  somewhere, and anything a discovered file could set is the hole itself.**」
- `:58`–`:59` **Consequences 里有一节 "Not solved"**，如实列出没解决的：
  层仍然被物化进 `process.env`，所以普通项目变量仍会到达子进程；Exa/Perplexity 仍在加载时捕获密钥。

**它否决了什么备选及理由**（原文 `:63`–`:73`，6 条，全部照录）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 按"谁编写了这个来源"把机密统一进非机密顺序 | **试过并放弃**：settings seam 已经把 composition 固定在用户段**之下**，所以"由部署编写"**不是这个 seam 能表达的层级**；且把 `.credentials.yaml` 提到启动环境之上**会拿走 CI/容器/单次运行依赖的那一个覆盖**。「**Two orderings that each explain their precedence beat one that describes neither accurately.**」 |
| 在被显式信任之前，不把路由与凭据给调用它的项目 | 作为产品立场被否决：checkout 默认被信任、不弹窗、不存信任记录。**残留风险被显式命名**（clone 一个带 `.env` 指向别的端点或密钥的仓库会把该会话路由过去），且指明它归**将来的 project-trust 闸门**处理 |
| 审计一份 `DSH_*` 白名单允许 `.env` 设置 | 名单**每加一个开关都要重审，而遗漏的失败模式是静默的**。**否定整个命名空间才 fail safe** |
| 把 bootstrap 变量排在进程层之下而不是拒绝 | `PATH`/`NODE_OPTIONS` **没有有意义的"输家"行为**——用户把它写进 `.env` 就是认为它生效，**静默忽略正是本决策要消灭的"我的设置没效果"失败** |
| 把快照做成三包能力 seam | **过早**：生产者在 Cordis 存在之前就跑了，且**没有第二个实现可选**。仓库规则是**不预先拆分** |
| 停止把层物化进 `process.env` | **延后而非否决**：能彻底把项目变量挡在子进程外，但会**静默打断任何读 `!!js process.env.X` 的用户 patch 层** |

---

### I-A10 `implemented/architecture/2026-07-30-session-end-seed-log-boundary.md`（55 行，**全文**）
**标题**：the end-seed log boundary
**主题 ① —— 「死标记与活标记在存储字节上完全一样」**

- `:9` **问题一句话**（一个非常干净的证据链缺陷）：
  > 「on picking up a log whose last compaction event is an unmatched `compaction/start`,
  > **"the previous writer died mid-compaction" and "a compaction is running right now" are
  > byte-identical stored history**.」
  于是所有者只能二选一：**拒绝压缩一个其实空闲的日志（把会话卡死），或者压缩一个真的在忙的日志。**
- `:11` **答案已经存在但只在内存里**：`Session.firstLiveSeq` 精确持有答案（本生命周期第一次自有写入的 seq），
  「but **only in memory, so a consumer reading stored bytes could not see it**」。
  → **修法是给它一个持久孪生体**（`:49`「`firstLiveSeq` gains **a durable twin** rather than a second,
  competing notion of the same boundary」）——**不是造第二个概念。**
- `:13` **不把插件的语义搬进 core**：崩溃修复合成 turn/step/tool 边界是因为 **core 拥有那套词表**，
  而 `compaction/*` 属于 compaction seam；
  「A core repair pass that closed plugin brackets would **put every plugin's bracket semantics in core**.」
- `:17` **事件本身刻意为空**：`session/end-seed` 的 payload 是空的——
  「**position and `time` carry the whole meaning**」，且它**不是 `SurfaceEventType`**，
  所以不产生消息、**不能扰动派生历史**。
- `:19` **读法是位置性的**：一个未匹配的开标记如果 seq 小于 `session/end-seed`，
  就来自构造种子、属于**已经结束的生命周期**。
  「Core writes the boundary and **reads nothing from it**」——**写入者与解释者分离。**
- `:21` **放置点的论证是一次完整的枚举**：构造函数是**每个带种子的会话都必经的那个腰**，
  六个入口全部经过它；写在持久化加载处会**漏掉两条 fork 路径**（而 fork 子继承一个仍在运行的父的开着的
  `compaction/start` **恰恰是必须能被分类的那个情形**）；写在 loop 启动处会漏 `fork()` 与 `adopt()`，
  且**会让 `SessionStartSource` 这个字段失去区分能力**。
- `:23` **幂等性是承重的而不是整洁**：种子已经以它结尾就不重复写——
  「without the guard **repeated controls would grow the log even when they perform no work**」。
- `:29` **诚实标出这个放置点新增的唯一代价**：
  > 「**Attaching is not a pure read**, though — a pickup now writes where nothing was written before,
  > so a read-only or full disk **fails at `session/created` rather than at the first real turn**.」
- `:35` **保证范围被单独立一节**（`## Scope of the guarantee`）：
  该谓词只对**本会话继承的**bracket 成立，**不是关于其它写者的活性信号**；
  「A consumer that must tolerate concurrent writers **needs a liveness signal beyond the log and cannot
  omit it on the strength of this event**.」
  → **给一个机制单独写一节"它不保证什么"。**

**它否决了什么备选及理由**（原文 `:39`–`:45`，4 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 由持久化协调器的冷加载路径写边界（早期迭代真的做过 `session/resumed`） | **它覆盖不到任何 fork**——而 fork 正是继承 bracket 的所有者可能仍在运行的那个情形；且在加载期铸造标记**意味着在读路径上做持久写**：每次冷加载一次 revision bump、对一个平衡日志做一次无事可修的 `commitRepair`、一个存储时间下限、以及**对只读存储会失败的加载** |
| 在 loop 启动时追加边界 | 漏掉 `fork()` 与 `adopt()`；事件将不得不在 `'startup'` 上触发（**那正是 fork 子发布的来源**），于是 `SessionStartSource` 失去区分能力；而且**它会在标记被追加之前就发布会话** |
| 复用 `header.seedLength` | 那是持久的 **fork 血统**边界，且刻意在 resume 时保留原 fork 值。**两个事实不同，混同会同时丢掉两个** |
| 让崩溃修复顺带关掉 `compaction/*` | 把每个插件的 bracket 语义搬进 core 的修复流程，而**core 无法知道关掉另一个包的 bracket 应该记录什么** |

---

### I-A11 `implemented/architecture/2026-07-02-tool-render-intent-union.md`（82 行，**全文**）
**标题**：Tagged render-intent union for tool-call presentation
**主题 ②④ —— 「可选字段袋」→「带标签的封闭判别联合」**

- `:11`–`:15` **问题被命名为「a bag of optional fields」**，三条症状：
  调用侧与结果侧的 `terminal` 字段重叠、桥接层用**临时条件**把它们缝起来；
  **哪些组合是有效的从未被写下来**——「**The type permits nonsense.**」；
  以及**最想要的那个能力根本表达不出来**（diff 卡片），因为 `content` 是 LLM 的 `ContentBlock[]` 词表。
- `:39` **`card` 在每个变体上都是必填的**——「a real discriminant, **not an optional default**」，
  桥接层 `switch` + `assertNever`。
  **联合是封闭的**，理由整句：
  > 「a fourth render intent (a table, a chart) **needs new bridge code to render it anyway**, so a
  > plugin-added variant that the bridge **silently drops would be worse than a compile error**.
  > Adding a variant breaks compilation at the bridge switch — **exactly the signal we want**.」
- `:43` **三条收益，第一条是本轮反复出现的判据**：
  「**Invalid states become unrepresentable.**」
- `:57` **一条边界声明**：terminal 意图**只是展示**——
  「a UI **projects the completed call and never becomes a second execution backend**」。
- `:61` **纯函数约束与重放绑定**：`presentCall`/`presentResult` 必须是 `args`（+结果）的纯函数，
  「they run on live streaming AND session-log replay, so they must be **replay-deterministic**」。
- `:17`、`:65`、`:80` **一条很好的"何时可以重开一个被否决的提案"的制度实例**：
  更早一版的 collapse 提案**自己写下了重开门槛**——
  「return later as a tagged render-intent union **after there are at least two real tools and two real
  consumers to validate the vocabulary**」；本篇开头就核对**该门槛已达成**。
  → **被否决的方案要带着它自己的重启条件；重开时先核对条件。**
- `:7` 顶部一行**局部取代声明**：union 对 UI 传输仍然当前，**其 ACP 映射已被另一篇取代**。

**它否决了什么备选及理由**（原文 `:65`–`:68`，4 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 完全删掉工具自有的呈现 | 就是本篇取代的那个被否决提案；**它自己的裁定就是延后到本联合，且门槛现已达成** |
| 让 UI 执行 terminal 意图 | 会**绕过 harness 的 bash 策略与所有权契约**，并**把命令执行分叉到多个后端** |
| 做成可合并扩展的联合（`ContentBlockMap` 模式） | 新的渲染意图**本来就需要新的桥接代码**，所以**插件加进来却被桥接静默丢掉，比封闭联合在 `assertNever` 处抛的编译错更糟** |
| 保持可选字段袋（现状） | 无效状态可表达、字段交互无文档、**且根本无法请求一个 diff 卡片** |

---

### I-A12 `implemented/architecture/2026-07-19-package-owned-invariant-service.md`（105 行，**全文**）
**主题 ②③⑤ —— 「不变量由拥有它的包持有」，且门禁保证覆盖是穷尽的**

- `:9` **问题**：把所有运行时不变量检查放进一个诊断包，会让那个包**从无关领域 import 产品词表**、
  把测试**从它们的所有者身边挪走**、并且**每次某个产品包增删检查都要改中心包**。
- `:13` **第三段问题陈述对 finaudit 极其重要**：
  > 「Package ownership must also be **exhaustive**. Without a mechanical repository rule,
  > a new package can omit the companion, dependency, or publication wiring and
  > **remain invisible to diagnostics until a maintainer notices the gap**.」
  → **「新加的东西默认不在检查范围内」是一类静默失效。**
- `:21` **每个包都必须发布一个 `./invariant` 伴生插件**，注册它**精确的完整 npm 名**；
  没有有意义关系的包**也要有伴生**，并且**必须带一条针对本包的解释说明为什么它的 installer 是空的**——
  「**Generated ownership placeholders and synthetic API-shape assertions are forbidden**」。
  → **「不适用」也要写理由，而且不许用生成的占位符糊弄。**
- `:46` **配置校验规则里一条很反直觉但正确的**：
  「A source that **matches no loaded package remains valid** because **registration order,
  later loading, and HMR must not change config validity.**」
  对应否决理由 `:94`：拿"当前已加载的包集合"去校验 allow/block 会让**当前加载顺序决定配置是否有效**。
- `:54` **注册是事务性的**：installer 在注册监听器之后失败 → **子 fiber 被完整释放、名字预留被释放，
  然后失败才逃逸**；于是「Reloading a companion therefore **begins with one clean installer state**」。
- `:69` **`verify-package-invariants` 的拒绝清单本身就是一份覆盖判据**：
  缺失伴生源码、**生成的标记**、**没有解释的空 installer**、
  **非空 installer 却省略或忽略 reporter**、外来或无法解析的注册名、
  缺失 `./invariant` 导出或未发布文件、缺失 invariant 的 peer/dev 依赖与项目引用、
  以及**省略了伴生入口的 bundle 覆盖**。
- `:87` **测试也检查"真的调用了"而不是"源码里写了"**：
  「Gate tests also **execute every companion's `apply` function and verify that it calls `register`
  with its manifest name, rather than accepting source text alone.**」
  → **门禁要跑，不要只做文本匹配。**
- `:105` **最后一条 Consequences 划出"永远开着"的部分**：
  「Session storage validation, snapshotting, freezing, cited source-event validation, and surface
  acceptance **remain always on and are not affected by invariant selection**.」
  → **可选诊断与不可关闭的完整性校验必须分开。**

**它否决了什么备选及理由**（原文 `:91`–`:94`，4 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 所有检查都留在 `dsh-invariants` | 注册表会**继续 import 每一个被检查的产品领域**；所有者的改动**要求改中心包**；包的测试**与它们保护的契约分离** |
| 让根入口在 `ctx.invariants` 恰好存在时隐式注册检查 | 根行为会**依赖组合顺序与可选服务是否存在**，诊断无法被独立选择，且**包加载会藏起一个显式伴生之外的注册副作用** |
| 运行期自动发现每个 `invariant.ts` 文件 | **文件系统/包发现不是一个运行时所有权契约**，会让打包发布变得含混，也表达不了显式的 Cordis 加载顺序与依赖安装 |
| 拿当前已加载的包集合校验 allow/block 条目 | 零匹配的模式**可以有意针对一个更晚加载或 HMR 加载的贡献**；**当前加载顺序不得决定配置有效性** |

---

### I-A13 `implemented/architecture/2026-06-26-file-context-as-event-gate.md`（173 行，**全文**）
**主题 ②③⑤ —— 本轮关于「闸门放在哪里」的最完整案例**

**它主张什么**：把「文件观察策略」从**在路径上的、必需的方法服务**（`ctx.fileContext`）
反转成**通过事件参与的 gate + recorder 插件**。工具直接调 `ctx.fs`，策略层只挂三个监听器。

**四条对 finaudit 直接可迁移的判据**：

1. `:11`–`:17` **三件事本该可分离，却被耦合成一件**：
   工具做什么 / 新鲜度与观察策略 / **观察状态的记录（一个副作用，永远不该阻止工具运行）**。
   耦合的后果一句话：
   > 「removing the policy layer is **a breaking change rather than a graceful loss of an *add-on***.
   > The policy is **load-bearing for the tool to even run, not an opt-in tightening**.」
   → **判断一个策略层设计得对不对：把它拿掉，系统是"少了约束"还是"跑不起来"。**
2. `:40`–`:47` **本篇最锋利的一条：检查必须放在原子区里，否则它是一个假保证**。
   策略层**从不调 `stat`、也从不自己比较版本**；它只决定"这个 owner 上次观察到了什么"（一次 `WeakMap` 查表、零 I/O），
   把"版本是否仍然当前"交给 **provider 的原子变更临界区**（CAS）。理由整句：
   > 「If `dsh-fs-observation-policy` stat-ed and compared versions in its waterfall handler, there would
   > be a **TOCTOU gap** between that check and the tool's actual write … so **the check would be a false
   > guarantee that the provider's lock has to back up anyway**.」
   → **对 finaudit：把"数据没被改过"的校验放在读取与使用之间，等于没校验；要放在使用它的那个原子边界里。**
3. `:69`–`:77` **事件词表的归属由「谁必须能编译」决定，而不是由「谁在用」决定**：
   事件住在 `dsh-fs` 而不是策略包，因为**发射者是工具**、工具必须能在策略包缺席时继续编译；
   `dsh-fs` 是两者都已经依赖的那个包，所以它是**唯一能让发射者与监听者共享词表而不让发射者依赖策略插件的家**。
   并且 actor 在 `dsh-fs` 里被类型化为 `object`——**一个纯不透明载体，provider 契约永不读它、永不收窄它**；
   `{ agent?: { session? } }` 这个结构形状**完全留在策略包内部**。
   → **跨层传递身份时，中间层持有的是不透明句柄，不是被解析过的结构。**
4. `:129` **记录型监听器的契约被写死**：`fs/observed` 的监听器**必须是同步的、只有副作用的、不抛的记录器**；
   工具**不保护这次 emit**，所以一个会抛的监听器会**替换掉待返回的读错误，或者在变更已经成功之后报告失败**。
   > 「**Async or fallible observation needs a separate event contract.**」
   → **留痕失败不得改写主操作的结果；做不到就换一套契约，而不是凑合。**

**其它可直接搬的**：

- `:75`、`:171` **单槽 waterfall 的诚实标注**：两个 `fs/*` 决策事件是**单槽、先到先得**，
  策略监听器**不调 `next()`**，于是在默认部署里独占该槽；
  但 Consequences 明写：
  > 「**a second decider registered first would bypass it. This is acceptable because a second
  > fs-version-policy decider is a misconfiguration, not a feature.**」
  并给出未来的正确路径：真需要**分层**策略时，那是**一篇新的 Agent Note（一个可组合的传值 waterfall）**，
  **不是在这些事件上悄悄加第二个监听器**。
- `:51`–`:67` **「无约束」被表达成省略而不是新增一个枚举值**：
  版本守卫变成可选（`expected?`），**`FsWriteIntent` 联合本身不变**——
  第三种"无条件"状态**由省略 `expected` 表达**，于是两个变更方法共享一个对称形状。
  且**原子性与版本前置条件被分开**：「"unconditional" drops the ***version* precondition, not the
  atomicity**」。
- `:139` **观察记录是判别值而不是布尔**：present（带版本）/ absent / 无记录（unseen）三态，
  各自允许的后续动作不同（unseen → 编辑报 `FS_NOT_OBSERVED`；absent → 只允许有守卫的创建）。
- `:173` **最后一条 Consequences 把裸模式的真实含义写出来，不粉饰**：
  > 「A deployment without `dsh-fs-observation-policy` **lets the model overwrite or edit any existing
  > file unconditionally.** … **that is not the intended stance for a config that ships the fs tools.**」

**它否决了什么备选及理由**（原文 `:163`–`:165`，3 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 保持 `ctx.fileContext` 作为在路径上的方法服务（原先落地的形状） | 工具**没有策略层就跑不起来**，使策略**对基本操作是承重的，而不是可选的收紧** |
| 策略侧做版本检查（在 waterfall handler 里 stat 并比较） | **TOCTOU 缺口**；provider 的变更临界区**是唯一无竞争的地方** |
| 每个工具一个 `/read`/`/write`/`/edit` 子路径插件 | 落地时**放弃**：没有消费者需要单工具部署，且子路径发布**逼出兄弟包都没有的定制构建处理** |

---

### I-P6 `implemented/process/2026-07-14-typescript-program-backed-semantic-gates.md`（65 行，**全文**）
**主题 ⑤ —— 「门禁靠语义事实，不靠命名约定与手工表」**

- `:9`–`:13` **问题**：门禁有时需要**语法本身不携带的事实**（接收者到底是不是 Cordis `Context`、
  哪些具体事件名到达了转发助手、声明合并有没有改过事件签名），
  而现有门禁靠**命名约定、手写表格、JSDoc** 维护这些事实。
  目标写得很克制：「one semantic source of truth **without introducing runtime package cycles,
  broad fallback heuristics, or machine-readable annotations that restate information already
  available to TypeScript**」。
  → **不要为了让门禁能查，去加一堆"重述已有信息"的注解。**
- `:29` **规则**：按**对真实类型的可赋值性**分类调用，
  「**Variable names and property spellings do not determine whether a call is an event operation.**」
- `:33` **一条很有价值的成本工程说明**：按需索引 + **"证明局部性"**（一个非导出的、
  位于真实 ES 模块中、且其同文件内每一处引用都是直接被调用的助手，**其全部调用点按模块作用域必然在该文件内**），
  任何**未被证明的前提**（有 export 修饰符、全局脚本文件、别名化或无法分类的引用）
  **回落到原来的全量索引**——
  > 「**the proof affects cost, never results.**」
  → **优化只能影响成本，不能影响结论**，这是一条可以直接搬进 finaudit 的优化纪律。
- `:35` **覆盖完整性被写成一条会失败的规则**：
  「**Every declared harness event must have a discovered producer.** A missing producer **fails
  generation** as dead vocabulary or an unsupported semantic dispatch shape」；
  同时**监听器为空的扩展点仍然合法**。
- `:41` **"扫不出来"必须显式标注，且标注不许夹带答案**：
  零匹配需要 `@dshScopeScan unsupported`，
  「The annotation **records an unsupported scan; it does not encode an event name, parameter index,
  property path, or replacement type**.」
  → **标注"我查不了"，而不是用标注去手写一个答案**——这与「Alternatives are recorded, never invented」同源。
- `:41` **多匹配是失败而不是取第一个**：「**Multiple matches are ambiguous and fail.**」
- `:49` **恢复路径故意做窄**：「Recovery through local helper call sites is **deliberately narrow**:
  exported or unresolved dataflow **requires a new semantic rule rather than a package-specific override**.」
  → **不许为个别包开后门。**

**备选**（原文 `:57`，只记录 1 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 保持只看语法的扫描 + 接收者白名单 + 手工覆盖 | 每个例外单独看都简单，但**改名与新的助手形状要去更新第二份表示**。「Completeness can detect a missing producer, but **it cannot prove that the override still describes the source**.」 |

---

### I-P7 `implemented/process/2026-07-27-explicit-change-scope-report.md`（41 行，**全文**）
**主题 ①⑤ —— 「范围选错会让证据漏掉受影响的路径」**

- `:11` **问题一句话**：
  > 「**An incorrect range undermines evidence selection because it can omit affected paths.**
  > A three-dot committed diff also **says nothing about Git's separate staged, unstaged, and untracked
  > layers**.」
  → **对 finaudit 的直接类比：比对范围（哪期、哪版、哪张表）选错，会让"我检查过了"变成假的。**
- `:15` **对策：`--base` 必填，不猜**。产出一份**版本化的 JSON 报告**，
  记录：仓库根（**不规范化合法的路径空白**）、输入 ref、解析后的 base/head/merge-base commit id，
  以及**排序后的 committed / staged / unstaged / untracked 四组路径集合**。
  路径按**原始 NUL 字节**切分，仓库根与每个路径**按严格 UTF-8 解码**；
  > 「An invalid value **aborts the report instead of substituting characters or collapsing distinct values**.」
  → **宁可中止，也不要用替换字符把两个不同的值折叠成一个。**
- `:17` **探测必须是惰性的**：每次 Git 探测都**禁用已配置的文件系统监视器与可选的加锁**；
  diff 配置**不能隐藏子模块、不能调用外部 diff 或文本转换驱动**；
  **重命名检测被关闭，好让重命名的两侧都可见**。
  → **取证时要关掉一切"为了好看"的功能。**
- `:19` **明确划出它不做什么**：「The command **never guesses or fetches a base, queries a hosting
  provider, or selects tests.**」调用方负责核实远端/stack 状态并**显式提供 base**。
- `:37` **Consequences 第一条把这个取舍讲透**：
  > 「The explicit input **makes an incorrect base possible but visible**: both input refs and all three
  > resolved commit IDs appear in the report.」
  → **可见的错 > 隐形的对。**
- `:39` **一条刻意的能力缺失**：字符串 schema **故意无法表示非 UTF-8 路径字节**，
  含这类路径的仓库**必须先改名才能产出报告**——
  「**preserving exact scope instead of returning a lossy one**」。

**它否决了什么备选及理由**（原文 `:25`–`:33`，5 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 保持临时 diff 命令 + 散文兜底 | 避免了一个脚本，但让**新 worktree 与 stacked base 这两种正常拓扑在各工作流之间不一致**，且**漏掉脏层** |
| 从配置的 upstream 推断 base | upstream 可能是首推前的 `origin/master`、推后的同名特性分支、或 PR 目标是另一条特性分支的 head 分支。**没有一种推断对所有拓扑都正确** |
| 在命令里查 GitHub 拿 base | 把一个**本地只读报告**耦合到某一个 forge 与网络凭据，**而且仍然解决不了没有 PR 的分支** |
| 从变更路径生成必须跑的测试 | **路径无法确立通过配置、动态加载、子进程、worker、构建产物或 provider 到达的行为**。证据选择仍然是判断题 |
| 报告当前分支与 upstream 并维护一个平行的人类可读渲染器 | 调用方在调用前已核实分支与 base，**没有消费者使用那些字段**，且**格式化散文复制了 JSON schema 却没有改善路径完整性** |

---

## 6. `implemented/` 第二批 —— 事件形状 / 封闭类型 / append-only 物理层

> 本节 10 条为本轮第二批（2026-08-22 续读），主题集中在
> 「事实用什么形状存」「失败怎么变成可路由的类型」「append-only 在文件系统上到底怎么落」。

---

### I-A14 `implemented/architecture/2026-06-11-structured-error-taxonomy.md`（26 行，**全文**）
**主题 (4)(6) —— 「失败不能是裸字符串」**

- `:9` **问题一句话**：
  > 「Failures crossed seams as bare strings. A tool error flattened to a text block —
  > **name, code, and stack lost** — so a future sandbox/retry plugin **couldn't tell ENOENT from EACCES**」

  同行还有更狠的一句：`LlmError` 曾是系统里**唯一**的类型化错误，没有共享基类，
  于是消费方**没有任何东西可以 `instanceof`**。
- `:13` **对策**：一个 `HarnessError extends Error` 基类，放在 `dsh-llm`——
  「the leaf package every other imports — **no new dependency edge**」。
  三个字段：**稳定的 `code`（与 `message` 分开）**、`cause` 链、`name` 默认取子类名。
  `isHarnessError` 在 seam 上做窄化。
- `:16` **结构化字段随事实一路走到日志**：`ToolExecutionResult` 增加可选
  `error: { name, code }`，agent loop 把它转发到 `tool/result` 会话事件上，
  「so the **structured failure survives into the log** for retry/sandbox plugins and replay.
  The model-facing text block is unchanged.」
- `:17` **连「抛错抛错了」都要有码**：非 Error 抛出被包成 `HarnessError`（`code: 'UNKNOWN'`，
  原值挂 `cause`），「so **even a bad throw carries a routable code**」。
- `:21` Consequences 的核心收益：
  > 「a plugin can **branch on `error.code` rather than substring-matching a message**.」
- `:23` **一条刻意的不对称**（本篇最值得抄的取舍）：
  `deriveMessages` **不把 `error` 送进模型历史**——模型看到的仍是文本块，
  **结构化字段是给代码和 replay 用的**。
  → **同一个失败事实有两个受众，两套表示，谁也不冒充谁。**

**备选**：`:26` 带 `<!-- agent-note-format: alternatives-not-recorded (pre-format Agent Note) -->`
标记，**原文未记录备选**。

**对 finaudit 的输入**：审计失败（口径不匹配、科目缺失、期间不可比）必须是**带稳定 code 的封闭类型**，
不是「数据有问题」这种字符串。而且要**双表示**：给人看的自然语言 + 给证据链存的 `{name, code}`。

---

### I-A15 `implemented/architecture/2026-06-11-runtime-arg-validation.md`（24 行，**全文**）
**主题 (6)(7) —— 「编译期类型是对运行时值的一个声称」**

- `:9` **本篇最有迁移价值的一句**：
  > 「that type is a **compile-time claim about a value that arrives at runtime as model-generated JSON**:
  > nothing forced the model to honor the schema, so a malformed call … reached `execute`
  > **typed-in-name-only**.」

  → **「类型上写了」≠「运行时是」。** 模型产出的东西一律当外部输入。
- `:13` **校验点选在哪**：`defineTool` 在**定义时**快照编译后的参数 schema，
  在**跑 typed body 之前**执行校验；违例抛 `ToolArgsError`（`INVALID_ARGS`），
  registry 把它变成**模型可以自己纠正的 error result**，不是崩溃。
- `:15` **校验器与编译器共享精确语义**（列了 7 条：隐式参数根是 open object、
  required 只来自 `required: true`、default 只是注解、显式嵌套对象各自决定开闭、
  数组走 `items` 递归、标量字面量约束类型正确、`oneOf` 恰好匹配一支）。
  最后一句划边界：「**Raw-registered tools own their input validation.**」
- `:20` **漂移风险被机械封住**：一个 property test 生成满足 spec 的参数、断言过校验，
  并用**定向 corruption** 断言被拒——
  「closing that drift risk **mechanically**」。
  → **两套实现要一致时，别靠人盯，靠生成式测试对拍。**

**备选**：`:24` 带 `alternatives-not-recorded` 标记，**原文未记录备选**。

---

### I-A16 `implemented/architecture/2026-06-11-microkernel-event-taxonomy.md`（31 行，**全文**）
**主题 (3)(5) —— 「扩展点是有 dispatch 语义的类型化事件」**

- `:13`–`:18` **四种 dispatch 模式，各自有明确用途**（这是本篇最可抄的部分）：

  | 模式 | 语义 | 用在哪 |
  |---|---|---|
  | **waterfall**（around-middleware） | 插件可 transform / **short-circuit** / recover / wrap | `agent/pre-step`、`agent/request`、`tools/pre-execute`、`tools/execute`、`tools/post-execute`、`llm/stream`、`system-prompt/assemble` |
  | **serial**（按监听顺序 await） | 有序检查点 | `agent/turn-stopping` |
  | **parallel**（fan-out 全部 await） | **每个监听者都必须拿到独立机会** | `session/flush` 持久化检查点 |
  | **emit**（同步 fire-and-forget） | 通知 | inbox 状态迁移、生命周期、错误、`tools/result` 观察 |

  `:18` 末句划死了归属：「**Durable session events own turn and step boundaries.**」
- `:20` **词表归属**：事件词表住在 contract 包里（`dsh-agent` 声明 `agent/*` 事件），
  `dsh-agent-loop` 是**唯一**的具体 loop 插件，且**它自己也可替换**——
  「**nothing outside it may depend on it**」。
- `:28` **一条证明义务**：每个 MVP 特性都要映射到一个 listener，
  「the feature → mechanism map **is the proof obligation, kept current**」。
  → **不是文档，是义务：说好了「一切皆插件」，就要能逐条指出每个特性落在哪个 listener。**
- `:30` 诚实记下代价：waterfall 语义（调 `next()` 还是短路）**不直观、必须教**。

**它否决了什么备选**（原文 `:24`）：
「purpose-built middleware stack（koa-compose 风格）」与「显式 phase 状态机」——
两者都会**重新实现 Cordis 原生事件系统已经提供的 dispatch / disposal / reload 语义**；
作为 Cordis effect，listener 免费获得 HMR 与 disposal。

---

### I-A17 `implemented/architecture/2026-06-11-content-block-vocabulary.md`（28 行，**全文**）
**主题 (3)(6) —— 「自己拥有内部语言，映射成本推给适配器」**

- `:9` 目标一句话：harness 需要**一种内部语言**，让 loop、会话日志、所有插件都讲同一种话。
- `:13` **决策**：消息 = 类型化 content block 数组（`text` / `reasoning` / `tool-call` / `tool-result`），
  联合类型由 merge-extensible 的 `ContentBlockMap` 导出，插件靠声明合并加块类型。
  **同一个 merge-extensible-map 模式给每一个「stringly」字段上类型**——
  `MessageSource`、`FinishReason`、`TurnTrigger`、`TurnEndReason`。
  > 「Adapters translate to provider wire formats — **mapping cost lives in adapters, where it belongs**.」
- `:15` **一个被后来推翻的设计，原文诚实留痕**：会话内上下文注入与中途 steering
  最初渲染成**带标签的 user-role 信封**（system-reminder 模式），
  现在改成**纯 user content、无包装**；并指向 `simplification/2026-07-20-unwrap-injected-content-envelopes.md`。
  同句还写明：这个渲染是**用实时 adapter 验证过的**，
  「a future provider-specific mismatch **belongs in that adapter rather than a new canonical role**」。
- `:28` **跨包边界的 ID 一律 branded**（`CallId`、共享的 `SessionId`）——
  「nominal typing at **zero runtime cost**」。

**它否决了什么备选**（原文 `:19`–`:20`）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 直接照搬 DeepSeek/OpenAI chat-completions 形状 | 第一家 provider 零映射成本，但**对富内容（reasoning、结构化 tool result）很别扭** |
| 原样采用 Anthropic Messages 块结构 | 久经考验，但**规范类型会去镜像一个本项目并不首要面向的第三方 API** |

---

### I-A18 `implemented/architecture/2026-06-30-event-domain-semantics.md`（39 行，**全文**）
**主题 (3)(5) —— 本轮最重要的一条：「一个事实只能有一个来源」**

- `:15` **问题的两个动机，第一个直击证据链**：
  好几个 turn/step 边界**同时**以持久 `SessionEvent` 和镜像 `agent/*` emit 存在，
  > 「A consumer had **two sources of truth for the same fact**, and every lifecycle change
  > had to update both.」
- `:21`–`:25` **三个域，各一份职责**：
  - **`session/*` —— 持久、可重放的 FACT 日志**。每条都是 **JSON-only（无活对象）**。
    每次 append 一个 `session/event` emit，外加 `session/flush` 并行持久化检查点。
    关键的一句：**它同时是实时 transcript 源**——
    「so **live rendering and replay projections share one path**」。
  - **`agent/*` —— LIVE 运行时面**。总是携带活的 `Agent`。拦截 waterfall 可 transform / reject / recover。
    「Turn and step BOUNDARIES are **NOT here**」。
  - **`tools/*` —— 工具注册与执行流水线**。
- `:27` **边界规则（一句话，可直接搬）**：
  > 「a **durable, replayable fact is a `SessionEvent`**; a **live interception or a transient/live-object
  > signal is an `agent`/`tools` Cordis event**.」
- `:29` **规则被真的执行了**：四个边界镜像事件（`agent/turn-start` / `turn-end` / `step-start` / `step-end`）
  **全部删除**。判据是**实证的**：「**No production consumer needs the live `Agent` at a boundary**」，
  并逐一点名 ACP bridge 如何改用 `session/event` 的 `turn/start`/`turn/end` 配对。
- `:33` **失败包容的边界画得极细**：`Session.append` 拥有 post-commit 观察者包容，
  所以**一个抛异常的边界观察者不能改变 turn 结果，也不能饿死后续消费者**；
  但**acceptance 或内部校验失败仍然在边界进入日志之前逃逸**。
  → **「进日志之前可以拒；进日志之后不许改」。**
- `:34` **测试跟着行为一起搬家或一起死**：
  观察被删 emit 的测试改读持久事件（**被钉住的行为不变，只是换了 feed**）；
  而那些专门测「抛异常的 turn-boundary emit 监听器」的测试**被删除**，因为**那条代码路径不存在了**。
  原文引 AGENTS.md：「**tests document behavior, not golden truth**」。
- `:35` **一个精确到令人不适的细节**：loop 只在 `append('step/start')` **返回之后**
  才把 step 标记为 open，所以「The marker therefore represents **exactly the committed boundary
  that owes a later `step/end`**」。
  → **标志位表示的是「已提交的、欠一个闭合的边界」，不是「我打算开始了」。**

**备选**：`:39` 带 `alternatives-not-recorded` 标记，**原文未记录备选**。

**对 finaudit 的输入（本轮最强的一条）**：
证据链事件必须是 **JSON-only 的持久事实**，实时 UI 与事后复核**读同一条流**。
凡是「为了界面方便」而镜像出来的第二份事实，迟早两边不一致——
deepseek-harness 的做法是**把镜像全删掉，并先证明没有生产消费者需要它**。

---

### I-A19 `implemented/architecture/2026-07-05-windows-jsonl-durable-publish.md`（35 行，**全文**）
**主题 (2)(7) —— 「append-only 的耐久承诺不许因为平台不同而偷偷降级」**

- `:9` POSIX 的发布协议：写临时文件 → fsync → link 到最终名 → **fsync 父目录** → 删临时 link。
  父目录 fsync **是耐久性契约的一部分**：崩溃后不能出现
  「lose the committed final name **while leaving callers believing the session log materialized**」。
- `:11` **本篇的判断点**：Windows 有原子命名空间操作，但 Node 在那里**没有暴露等价的父目录 fsync 契约**。
  > 「**Treating Windows directory sync failures as success would silently weaken a durable backend.**」

  → 所以不是在 `syncDir` 里加个 `if`，而是**换一条发布原语**。
- `:19` Windows 路径：在常量前缀 `.dsh-mkdir-` 下建随机同级目录，
  再用 `MoveFileExW(..., MOVEFILE_WRITE_THROUGH)` 发布，
  **不带 `MOVEFILE_REPLACE_EXISTING`，也不带 `MOVEFILE_COPY_ALLOWED`**。
  → **不许替换、不许退化成复制。**
- `:31` **对外契约跨平台唯一**：
  > 「first append **either publishes a complete log at the final name or fails without overwriting
  > an existing log**.」

  平台差异是实现细节。
- `:33` **对「能证明什么」极度诚实**（值得整段抄）：
  > 「**Power-loss behavior remains an API-contract property rather than something unit tests can prove**」

  ——于是列出**真正可测的**不变量：Windows materialization 上不调用目录 fsync、
  最终路径冲突会失败、最大长度路径分量仍可 materialize、临时日志在发布前已 fsync、产出的日志能正常加载。
- `:35` 回滚也是 append-only 的一部分：失败的 append **关掉 append-only 句柄、以读写重开、
  截断回到 append 前的字节数、fsync 这次回滚**——因为 Windows 拒绝对 append-only 句柄做 `ftruncate`。

**它否决了什么备选**（原文 `:23`–`:27`）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 忽略 Windows 目录 sync 失败 | **把首次 append 报告成 durable，却没有把已发布的命名空间条目强制写到稳定存储** |
| 用 `CreateHardLinkW` | 硬链接**依赖具体文件系统、无法发布目录、没有 write-through 选项** |
| 用替换类或事务类 API | `ReplaceFileW` 的替换语义**与「同 id 冲突必须拒绝」相冲突**；Transactional NTFS **不推荐用于新设计** |

---

### I-A20 `implemented/architecture/2026-07-19-zstandard-jsonl-session-logs.md`（57 行，**全文**）
**主题 (2)(6) —— 「压缩不许动 append/fsync 提交边界」**

- `:9` **约束先行**：压缩必须保留既有的 append/fsync 提交边界、冲突安全的首次 materialization、
  崩溃修复、**仅读元数据的 listing**；
  > 「rewriting a whole compressed file after every turn **would discard those properties**.」
- `:11` **编码必须在部署边界显式**：
  > 「a backend **cannot safely guess** between compressed and raw artifacts in one root
  > or **silently migrate** pre-release session data.」
- `:19` **fail-closed 的目录级不变量**：**每个持久化根只属于一种编码**。
  一次性 discovery preflight **拒绝任何反向后缀**；load / live-adoption / listing / materialization
  各路径在 preflight 初始为空时**再查一次**。
  错误信息**点名那个不兼容的 artifact**，并指向匹配配置或另建一个根。
  > 「There is **no migration, dual read, dual write, or extension-based fallback**.」
- `:23` **物理帧边界 = 逻辑提交边界**：一个 checksum 帧只装 header 行，
  之后**每个 durable append batch 一帧**。
  「Normal loop batches are turn commits, so frame boundaries **preserve the existing persistence
  checkpoint without making the storage layer depend on turn event types**.」
  → **存储层对齐提交边界，但不认识业务事件类型。**
- `:33` **专用 header 帧换来的能力**：listing 只读到第一个完整帧可用为止，
  「**never reads an event frame**」——超大日志也能只读元数据。
- `:35` **撕裂尾部的修复协议**（本篇最精细的部分）：文件末帧内 EOF 视为**可恢复的撕裂尾**；
  专用前缀解码器用 `finishFlush: ZSTD_e_flush`，**不要求帧或校验和完整**就吐出可得明文；
  **每一条完整的、以换行结尾的事件都被保留**。修复从该帧起始字节截断，
  追加一个新的 checksum 帧，内含恢复出的完整事件 + **协调器合成的 tool / step / turn 闭合子**。
  若撕裂发生在任何完整事件可解码之前，**丢弃该部分帧，保留此前全部完整帧**。
- `:31` **什么算腐坏、直接拒**：任一完整帧的 checksum/解压失败、完整帧的 JSONL 尾部畸形、
  帧结构非法——「**is corruption and rejects**」。

**它否决了什么备选**（原文 `:45`–`:49`，5 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 每条 JSONL 记录一帧 | 对高频 chunk 事件**成倍增加帧头与校验和**，且**让物理边界与 durable append batch 无关** |
| 每次 append 后重写整个压缩流 | **成本随日志增长**，且替换会**放弃 append/fsync 回滚与冲突安全的 materialization 机制** |
| 跨 append 用流式压缩器 | **被中断的编码器状态留不下「各自独立校验的 append 单元」**，使有界 listing 与帧起点修复复杂化 |
| 引入外部原生 Zstandard 依赖 | Node 版本下限**已自带所需编解码器**；再加原生产物只**放大安装与打包风险**而不带来必需行为 |
| 暴露压缩级别 / 保持 raw JSONL 为默认 | **没有部署证据支持第二套调参策略**；而 `'none'` 已经保住了 fixture 与集成需要的可逐行读路径 |

---

### I-A21 `implemented/architecture/2026-07-26-packed-chunk-rows-by-default.md`（59 行，**全文**）
**主题 (2)(6) —— 「逻辑事件与物理行分离」**

- `:9` **不可动摇的部分先说清楚**：日志必须**把每个 chunk 保留为不同的逻辑事件**——
  实时 `session/event` 投递、序号、`sourceEventSeqs`、replay、**取消证据**、UI 流式，全都依赖那些边界。
- `:11` **可动的部分**：连续三条及以上同 block 的 delta 事件可以压进一个存储行，
  「decoding **reconstructs every original event, timestamp, and sequence number**」。
- `:11` **一条关于「默认值怎么才算可信」的判断**（很好用）：
  > 「A credible default must cover runtime writers, app-level config, snapshot producers,
  > and committed fixtures **together; otherwise tests avoid the layout that deployments write**.」

  → **测试如果不走生产默认布局，那个默认值等于没被测。**
- `:17` **读永远与布局无关**：packed / unpacked / 混合文件加载成同一个连续 `SessionEvent[]`，
  所以默认值切换**不需要会话格式版本变更，也不需要磁盘迁移**。
  「The option controls newly appended batches only; **it never selects a reader mode.**」
- `:21` **词表归属划得很干净**：
  > 「A packed row is **storage vocabulary, not a `SessionEventMap` member**:
  > it **never enters `Session.events` or fires `session/event`**.」
- `:27` **canonical fixture 用无路径清单的门禁保证**：脚本**发现**仓库内所有被跟踪的 `*.jsonl`
  （加上未被 ignore 的未跟踪新增），挑出首记录是 `session` header 的，解码全部 body，
  **与 `packChunkRuns()` 输出不同即拒**。
  「The inventory therefore includes … **future fixture names without a maintained path list**.」
  → **门禁靠发现，不靠维护清单。**
- `:35` **过渡工具自带死期**：迁移脚本存在的唯一理由是在飞的分支；
  删除提案**在实测的 open-PR 清单显示所有受影响分支已合并/关闭/已规范之后**才执行。
  「The shared canonicalizer and snapshot gate **remain permanent**.」

**它否决了什么备选**（原文 `:45`–`:53`，5 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 只翻 backend schema 的默认值 | wrapper 默认、TUI/web 序列化器、既有 fixture、未来 fixture 策略**会不一致**。「A default is meaningful only when **shipping compositions and the tests representing them share it**」 |
| 为了可读性让快照保持 unpacked | packed 行**显式保留每个片段与时间戳**，共享解码器提供逻辑检视；让**最大的已提交消费者用另一种布局**会使快照覆盖**绕开生产写路径** |
| 干脆删掉 `packChunks` 永远 pack | 一行一事件对**诊断**与**混合布局兼容测试**仍有用；显式 opt-out 保住这些消费者而不削弱默认 |
| 把 chunk 批成逻辑会话事件 | 会**延迟或改变实时投递**、**重排 assistant 消息引用的 chunk seq**，并要求每个 UI/replay 消费者理解又一种流式单元 |
| 永久保留分支迁移器 | 只读的 canonicalizer 与快照门禁拥有持续执行；**变更类命令的价值有明确到期** |

---

### I-A22 `implemented/architecture/2026-08-06-agent-event-payload-objects.md`（27 行，**全文**）
**主题 (3)(6) —— 「事件签名用一个具名 payload，不用位置参数」**

- `:9` **问题**：agent 域事件曾用位置参数（前导 `agent` subject + 事件字段 + 尾部 `next`）。
  加一个字段或退休一个 context 类型，就要**改写所有包里的每个 listener 与 emitter**，
  而且「the contract **stayed spread across the parameter list instead of one named payload**」。
- `:13` **决策**：每个 agent 域事件**恰好一个 payload 对象作为第一参数**，
  payload 永远携带 subject（`agent`）、事件字段、以及**有取消语义时的 `signal`**；
  `next` 仍是 waterfall/serial 的最后一个参数。适用范围被数清楚了：12 个 `agent/*` 事件、
  `agent-loop/config-start-failed`（**唯一没有 subject 的**）、`goal/changed`。
- `:17` **本篇最值得抄的机制**：**dispatch 是融合的**。
  `agentEvents(ctx, agent)` 注入 subject，「so the **scope carrier key and the payload's `agent`
  cannot diverge**」，而且**注入的 subject 胜过 payload 里碰巧带的 `agent` 字段**。
  → **两个地方都写着「这是谁」时，让其中一个在结构上不可能说了算。**

**它否决了什么备选**（原文 `:21`–`:23`）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 保持位置参数签名 | 加字段/退休 context 类型会**继续改写每个 listener 与 emitter**，契约继续散在参数表里 |
| 在每个 dispatch 处手工构造 subject | loop 的中间设计手写 `{ agent: this, … }`，**避免了每次分发的分配开销，但重复了 subject 注入，并且让 scope key 与 payload subject 可能发散** |

---

### I-A23 `implemented/architecture/2026-07-20-canonical-tool-output-contract.md`（79 行，**全文**）
**主题 (4)(6) —— 本轮第二重要：「一个被校验的值，两个确定性投影」**

- `:9` **问题**：工具体过去直接写模型可见的 `ContentBlock[]`，
  于是「a programmatic caller **had no stable domain value**」——
  Code Mode 把块压回字符串、动态工具重复内容形状，
  而且**策略替换了「呈现」和替换了「结果」这两件事根本区分不开**。
- `:11` **拒绝把富值持久化的理由（三条，很干净）**：会**放大日志**、
  会**把实现数据暴露给压缩与迁移**、会**错误地把一个执行局部的 API 变成会话格式**。
- `:15`–`:27` **决策形状**：每个工具**必须**声明规范输出
  （`schema` + 纯 `render(args, value)` + 可选 `presentationMeta`），
  工具体**只返回该 schema 描述的值**。
  注册时**拒绝缺声明或不支持的 raw schema**——「there is **no content-return compatibility path**」。
  每次成功分发，registry 依次做：**快照成无损 `JsonValue` → 用 `output.schema` 校验 → 深冻结 →
  调纯渲染器**。渲染器/投影器/schema/无损 JSON 失败**都被包容成普通的 `ToolOutputError` 结果**。
- `:27` **反重放/反串用的机制**：每个 canonical result 都**绑定到创建它的那个不可变 dispatch token**，
  「so returning a **cached result from another call or tool** triggers normalization
  under the active declaration **rather than bypassing it**」。
- `:35` **三条互斥的后处理语义，写得极清楚**：
  替换 `content` → **只改呈现**，保留 canonical 值与元数据；
  替换 `value` → **重新校验并重算两个投影**；
  block → **移除值，变成失败**。然后一句斩钉截铁的安全声明：
  > 「Content replacement is therefore **not a confidentiality mechanism**: policy that must
  > prevent programmatic access **blocks the call or replaces the value**.」
- `:37` **执行局部 vs 持久事实的分界**：loop 只用 `content`、`error`、可选 `meta` 持久化 `tool/result`；
  「Neither event stores the canonical intermediate value, so **replay reproduces presentation
  but cannot reconstruct the programmatic result**.」
  → 这是**明写出来的能力缺失**，不是漏洞。
- `:41`–`:62` 一张表逐个列出第一方工具的 canonical 值形状
  （如 `read` → `{ path, offset, lines: [{ number, text }], totalLines }`、
  `write` → `{ path, operation, before, after }`），
  **可直接作为 finaudit 工具返回值的形状模板**。
- `:63` **一条容易忽略但很关键的区分**：
  > 「**Formatting-only limits belong in `render`**」

  ——`glob`/`grep` 把每一个取到的条目都留在 `value` 里，只有 Native 投影保留配置的首页。
  → **「取到多少」和「显示多少」是两件事，别让显示上限污染事实。**
- `:79` **最后一段把边界重申为属性而非缺陷**：
  「These are **explicit properties of the execution-local contract, not accidental gaps**.」

**它否决了什么备选**（原文 `:69`–`:73`，5 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 给 Code Mode 返回渲染后的文本 | 调用方会**继续从散文里刮 job id、mount id、路径与结构化结果** |
| 把 canonical 值持久化到 `tool/result` | 嵌套执行值**不是模型历史**、**不需要在 replay 中存活**，会造成与 Native 重建无关的**会话格式与存储承诺** |
| 让工具同时返回 value 和 content | **两个作者自定的结果会互相矛盾，策略无法声明哪个权威**。渲染器让呈现成为被校验值的**确定性投影** |
| 把替换 content 当作值脱敏 | 呈现与程序访问是**不同的消费者**；只藏前者会**造出一个假的安全边界** |
| 要求工具输出必须是对象根 | 标量、数组、null **都是合法的 JSON API**；对象根是**调用方规则**（subagent/workflow 的结构化输出），不是通用规则 |

**对 finaudit 的输入**：这就是「答案 + 证据链」的形状原型——
**一个被 schema 校验过、深冻结的 canonical 值**（指标口径、取数、计算中间量），
**两个确定性投影**：给人看的叙述、给机器核的结构化记录。
且必须明写**哪些中间量不进日志**，而不是含糊地「都记下来」。

---

## 7. `implemented/` 第三批 —— 制度本身：笔记格式、分类、门禁、命名契约

> 本节 11 条为本轮第三批（2026-08-22 续读）。
> 与第二批不同，这批读的是**这套制度怎么自己管住自己**——
> 「什么时候必须写笔记」「笔记格式谁来查」「不写清备选算不算违规」「名字算不算契约」。
> 对 finaudit 而言，这批的迁移价值高于任何具体架构决策：
> **我们要建的也是一套「必须留下可复核痕迹」的制度。**

---

### I-P8 `implemented/process/2026-07-05-uniform-agent-note-format.md`（30 行，**全文**）
**主题 (1)(6) —— 「格式不被机器查，就会烂」**

- `:9` **问题**：路径已经编码了生命周期与类别，但**文件内容仍然混着**各种标题、状态格式、
  ADR 与 proposal 模板，`implemented/` 里还留着提案期的段落。
  > 「Authors copied whichever neighbor they found, and **lifecycle moves could skip the required
  > rewrite because no gate enforced an in-file contract**.」
- `:13` **文件内契约的完整形状**（可直接照抄成 finaudit 的证据文档契约）：
  - 头块：`# Agent Note: <title>` + **不带日期、且与所在文件夹一致**的 `Status:` 枚举
    （其唯一允许的内容是 rejection reason）；
  - 按生命周期的正文骨架：**到处都以 `Problem` 开头**；
    `proposed/` 用 `Proposal`/`Acceptance criteria`/`Risks`；
    `implemented/` 用**现在时**的 `Decision`/`Consequences`，**提案期标题被禁**；
    `rejected/` **冻结提案形状**；
  - **强制的 `Alternatives considered` 段**；
  - 规范段落词表之间，**定制技术段落保持自由格式**。

  执行者是 `pnpm run verify-agent-note-format`，作为 `doc-sync` 的一员，
  > 「so a lifecycle move that skips its rewrite **now fails CI instead of review memory**.」
- `:15` **本篇最关键的一段，也是本轮任务的直接依据**：
  整个语料在**定义格式的同一次变更里**被规范化——
  「the pre-release stance: **no transition period, no dual-format tolerance**」。
  唯一的 grandfather **是内容而不是格式**：
  > 「**alternatives are recorded, never invented**, so a pre-format Agent Note whose alternatives
  > are not reconstructible from the record carries the exact
  > `agent-note-format: alternatives-not-recorded` comment, which the gate accepts **only for files
  > dated before this Agent Note**.」

  → 这就是本文所有「原文未记录备选」标注的**制度来源**：
  **宁可在记录上留一个诚实的洞，也不补一段编造的理由。**
- `:30` Consequences 把「强制备选段」明说成**刻意的摩擦**：
  > 「a decision recorded without what it beat **invites the re-litigation Agent Notes exist to prevent**.」

  同段还写：把笔记在生命周期文件夹之间移动，现在是**移动时的真实工作**
  （那次移动本就欠的正文重写），而不是**没人跟踪的延后清理**。
  最后一句是实证：39 个债务标记消失了。

**它否决了什么备选**（原文 `:19`–`:26`，**8 条**，本轮见过最完整的一份）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 完全刚性的模板（每个生命周期一个固定段落序列） | 大型设计笔记带着 **8–15 个定制技术段**（包拓扑、wire 契约、schema），那些是**承重内容而不是漂移**；刚性序列会**现在强迫破坏性重写、以后永远跟模板打架** |
| 只规范化头部（H1 与 Status，正文不动） | 债务标记指向的**正是正文的体裁分裂**；让 `Context`/`Decision` 与 `Problem`/`Proposal` 无限期并存**什么都没解决** |
| 不要 `Status:` 行（文件夹本身就是状态） | 否决，改为**保持文件自描述**：促使删掉它的漂移风险，**用「把该行对着文件夹做门禁」来中和** |
| 带日期的状态（`Status: implemented (accepted YYYY-MM-DD)`） | 接受日期是**写作规则要求排除在文档之外的叙事史**；文件名带首次提出，git 带其余，**而门禁能查日期格式却永远查不了它是否属实** |
| 光秃秃的 `# <title>` | `Agent Note: ` 前缀让文件**被拿到树外阅读时仍自描述体裁** |
| 用 `## What we give up` 作为 implemented 的收尾 | 它**只点出代价**；诚实的 consequences 段**也要记下这个取舍换来了什么** |
| 有约定但不设门禁 | slop 清单早就用约定禁止了 `implemented/` 里的规格腔，**19 个文件说明了光靠约定能达到什么效果** |
| 单独一个 `FORMAT.md` 契约文件 | **一个入口同时承载布局、分类、格式**，比两个契约文件更容易发现与维护 |

---

### I-P9 `implemented/process/2026-06-20-agent-note-classification.md`（48 行，**全文**）
**主题 (1)(5) —— 「文件夹就是标签，标签与存储是同一个东西」**

- `:11` **本篇给出的判断准则**，直接引用了 quality-gates 那条立场：
  > 「the repo's standing bias is **mechanical quality gates over prose guidelines**:
  > **a convention that isn't machine-checked rots**. So a classification scheme here had to be
  > enforceable, **not an honor-system header**.」
- `:15` **决策**：加第二根轴——笔记的**类别**，并**编码进路径**：
  `{lifecycle}/{class}/yyyy-mm-dd-topic.md`。
  > 「**The folder *is* the label.**」封闭集合是「这些文件夹，没有别的」。
- `:19`–`:27` **六个类别的封闭集**（finaudit 可以照这个结构划自己的决策类别）：
  `feature` / `bug-fix` / `simplification` / `architecture` / `process` / `testing`。
  `:28` 特意把最容易混的一条线讲清楚：
  > 「**architecture** is about **the source we ship**; **process** is the surrounding tooling and workflow.」

  然后**当场自证**：本篇自己是 `process` 决策，所以它住在 `implemented/process/`。
- `:32`–`:35` **两个门禁**，都是 `doc-sync` 成员，都遵循
  「tsx ESM、**verify-don't-generate**、首个违例即非零退出」的风格：
  - `verify-agent-note-classification.ts` —— 断言每个文件都在规范集里的类别文件夹下
    （生命周期根目录下的散装 `.md`、或未知类别文件夹，**都失败**），并**拒绝集中式 `INDEX.md`**；
  - `verify-doc-refs.ts` —— **扫源码注释里引用的文档路径**。
    理由很实在：Agent Note 路径不仅被 Markdown 引用，也被 TypeScript 文档注释引用，
    「`verify-md-links` **does not see those**, so a reorganization **could silently orphan them**」。
    该门禁**要求 `.md` 扩展名**，好让无扩展名的散文不被误伤。
- `:47` **加一个类别是刻意行为**：要改 `scripts/agent-note-tree.ts` 里的 `const`
  和 README 的分类段，**而不是 `mkdir` 一个文件夹**。门禁拒绝未知文件夹，
  「so an **ad-hoc class can't slip in**」。

**它否决了什么备选**（原文 `:39`–`:41`，3 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 每个文件里写一行 `Classification:` 由门禁解析 | 可行，但**把路径已经能承载的事实复制进文件**，而**一行字可以和它所在的文件夹不一致**。路径编码让**标签和它的存储成为同一个东西——没有东西需要保持同步** |
| 增加 `refactor` 类 | 与 `simplification` **几乎完全重叠**；唯一有人想到的判别式是「可观察行为是否改变」，而 `simplification` **已经编码了这一点**（不变）。**一个类，不是两个** |
| 生成或手工维护的语料索引 | 生命周期/类别树**才是权威**；集中式清单**制造合并热点**，而不提供树导航或仓库搜索给不了的发现能力 |

---

### I-P10 `implemented/process/2026-07-19-require-agent-notes-for-non-trivial-changes.md`（46 行，**全文**）
**主题 (1)(7) —— 「什么时候必须留痕」的边界，以及它为什么不设门禁**

- `:9` **问题**：一个「看起来是否持久、有争议、令人意外」的**选择性门槛**，
  会让实质变更在**不保留其理由**的情况下落地。
  > 「Code and tests show **what** changed, but they cannot consistently preserve
  > **why an approach won, which alternatives lost, or what costs maintainers accepted**.」
- `:13` **规则**：每个非平凡变更**在同一个 PR 里**至少新增或更新一条 Agent Note。
  非平凡的范围被逐项数清楚：行为、架构、跨文件/跨包契约、流程与工具、测试策略、
  **磁盘格式 / wire 格式 / 配置格式**、以及维护者**可能合理重访**的其他决策。
- `:15` **两个减负条款**：更新**已经拥有该决策的那条笔记**即满足规则，
  只有在**没有笔记拥有它**时才需要新建；纯机械或纯局部编辑豁免。
- `:17` **「合并一条已被完全取代的笔记」的前置条件**（这段可以直接搬去做 finaudit 的档案合并规则）：
  只有在新的拥有者**保留了每一条独有的理由、备选、后果、验证契约、以及点名的覆盖缺口**之后，
  才允许删除旧笔记。同一次变更还要修好入链、删掉中文对照件与一致性记录。
  最后一句是硬约束：
  > 「consolidation **neither rewrites an old decision into its opposite nor leaves git history
  > as the only copy of rationale**.」
- `:19` **「删掉一个特性」时，谁成为当前拥有者**——判据是**可核验的缺席**：
  该特性在**生产代码、配置、schema、持久或 wire 格式、迁移与兼容行为**中都不存在；
  没有当前文档把它呈现为可用；没有测试把它当作被支持行为来跑。
  且删除拥有者必须保留六件事：原始动机、**为什么该动机不再证成这份表面**、
  全量删除之外的备选、**放弃了什么能力**、**重新引入的条件**、以及**完全缺席的验证**。
  一条精细的限定：只删掉某一种 transport / 默认值 / 实现 / 呈现，**仍属部分取代**。
- `:21` **本篇最值得抄的一句克制**：
  > 「Review enforces the semantic boundary. **No automated gate attempts to classify a diff as
  > trivial or non-trivial**, so this policy **adds no gate stage or runtime**.」

  → **该由人判断的语义边界，不要假装能自动化。**

**它否决了什么备选**（原文 `:25`–`:37`，**7 条**）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 只对「持久、有争议、令人意外」的决策要求写笔记 | 门槛**主观到足以让一个实质变更被当成显而易见或纯局部**，丢掉笔记存在的意义 |
| 每次变更都要求新建一条笔记 | 在已有笔记已拥有该决策时**制造重复**，并给纯机械编辑**加空仪式** |
| 无限期保留每一条被完全取代的笔记 | 部分决策仍现行时交叉引用是必要的；但**完全过时的 implemented 笔记与「当前状态」契约矛盾**，且复制了本该只有一个拥有者的理由 |
| 增加 `superseded/` 生命周期 | 又一个生命周期会**保留过时记录并扩大树、格式门禁与维护规则**，却**不减少重复** |
| 把旧笔记改写成替代决策 | 这会**抹掉决策边界及其被否决的备选**。合并的做法是**先把这些事实保存进当前拥有者**再删旧文件 |
| 保留被删特性的每一处实现与测试细节 | 那是**在替代者内部重建了那条过时笔记**；删掉的机制**在 git 历史里仍可取得** |
| 增加一个 CI diff 分类门禁 | 机械检查**无法可靠判定一个语义变更是否平凡**，还会**增加运行时并招来假阳性或表面合规** |

---

### I-P11 `implemented/process/2026-07-19-remove-generated-agent-note-index.md`（31 行，**全文**）
**主题 (1)(5) —— 「派生清单是合并热点」**

- `:9` **问题**：已提交的索引**复制了每个文件的生命周期/类别路径、文件名日期与 H1 已经编码的事实**。
  > 「Every branch that adds, moves, or renames an otherwise unrelated Agent Note rewrites the same
  > generated file, making that artifact a **predictable merge hotspot**.」
- `:15` **决策**：**文件系统树本身就是清单**。README 仍是**经过策展的入口与契约**，
  发现靠普通的树导航与仓库搜索。
- `:17` 门禁只做「验证不渲染」：`verify-agent-note-classification` 校验树、
  拒绝历史遗留位置与根 `INDEX.md`，「**it does not render or freshness-check a centralized list**」。
- `:31` **诚实记下失去了什么**：
  > 「Readers **give up a single chronological page** and use the lifecycle/class tree or
  > repository search instead.」

**它否决了什么备选**（原文 `:21`–`:25`，3 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 保留已提交的生成索引，冲突时重新生成 | 重新生成让冲突解决变机械，但**不能阻止无关分支修改同一个产物**，也不减少它造成的评审噪声 |
| 提供一个不提交的按需索引命令 | 避免了提交冲突，但**为一条已被树导航与仓库搜索服务的发现路径保留了渲染器与命令** |
| 恢复手工维护的索引 | 同样的共享文件争用，**再加上生成本可避免的完整性与顺序错误** |

**对 finaudit 的输入**：证据台账、`OPEN-ITEMS.md`、`DECISIONS.md` 这类文件天然是合并热点。
这条笔记给的判据是：**问这份清单里有没有一条事实是别处推不出来的**；
如果全都推得出来，它就只是热点，不是资产。

---

### I-P12 `implemented/process/2026-07-06-parallel-pre-push-gates.md`（41 行，**全文**）
**主题 (7) —— 「门禁调度器：先拒绝非法图，再启动任何子进程」**

- `:7` **一条格式上值得注意的做法**：文件在正文之前先写一句**取代声明**——
  「The local-hook portion of this record **is superseded by** [Fast local Git hooks]…
  The bounded gate scheduler and package-level `publint` parallelism **remain in force**」。
  → **部分取代要写在被取代者的开头，而不是只在取代者里提一句。**
- `:11` **问题**：聚合任务隐藏着**长串顺序执行**的只读独立成员；
  而在 workflow YAML 里复制它们的叶子清单，会**给未来的脚本变更留下多个漂移点**。
- `:15` **调度器的能力清单**（每一项都对应一个具体故障模式）：
  展开命名模式为叶子门禁、**在启动任何子进程之前拒绝空图或有歧义的依赖图**、
  尊重产物依赖、**缓冲可归因的输出**、**独立报告退出码与信号**、接受 `DSH_GATE_CONCURRENCY`。
- `:17` **一条很具体的排序理由**：lint 必须等 invariant 校验，
  因为「the invariant verifier **temporarily stages package views that the linter must not traverse**」。
  → **并行度不是越高越好；有些等待是正确性要求，不是性能妥协。**
- `:19` **并行不许打乱日志**：`publint-all.ts` 每个包缓冲结果，
  **按确定的包顺序打印**，「so parallel execution does not scramble each package's log block」。
- `:37` Consequences 一句总结：
  > 「Invalid graphs **fail before partial execution**.」

**它否决了什么备选**（原文 `:29`–`:33`，5 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 聚合任务保持串行 | 执行简单，但**墙钟时间等于各独立检查之和**，还重复命令包装的启动开销 |
| 每个叶子门禁一个 CI job | 暴露最大 workflow 并行度，但**重复 checkout/setup/install 开销**，并**把调度器清单复制进 YAML** |
| 在 shell 脚本里后台化子命令 | 能并行，但**失去逐门禁计时、确定性的失败分组与直截了当的信号处理** |
| 每个包一个 `publint` job | 暴露最大包级并行度，但**造出一份手工维护的包清单**，包一变就漂移 |
| `publint` 无界并发 | 只在小仓库上把耗时压到最低，代价是**拿进程数、内存压力、包 tarball 创建与日志可读性去赌** |

---

### I-P13 `implemented/process/2026-08-06-coverage-uncovered-locations.md`（42 行，**全文**）
**主题 (1)(7) —— 「一次红色的 CI 必须自足」**

- `:9` **问题描述得极准**：覆盖率门禁失败时，vitest 只给**文件级**错误行——
  「you learn **which file** fell short, **not which lines**」。
  内置 `text` 报告确实有 Uncovered Line #s 列，但它是**横跨数百个文件的一张巨表**：
  列宽截断、**只有行号没有列号**、**不区分 statement / branch / function**、
  而且**通过的文件照样占行**。净效果：
  > 「a red coverage run on CI **is not directly actionable**; the only way to locate the specific gap
  > is to **rerun the html report locally**.」
- `:13` **对策**：自定义 istanbul reporter，对每个未达 100% 的文件，
  为**每个未覆盖语句、未走到的分支路径、未调用函数**各发一条**自足的单行记录**——
  `<path>:<line>:<col> uncovered <kind> …`，**终端与 CI 日志里可直接点击，也易于 grep**。
  全部通过时**什么都不打印**。而且排序有讲究：istanbul 报告生成**在阈值校验之前**运行，
  「so the records land **exactly above the existing ERROR lines**」。
- `:19`–`:22` **输出约定里的四个细节**（每一个都是「让证据可被机器和人同时用」的实例）：
  0-based 列号转成 **1-based**（编辑器与终端链接的约定）；
  v8 对整行语句报 `end.column = Infinity`，**跨行 span 降级成只带行号的 `(to <line>)` 后缀**；
  **隐式分支臂**（比如缺失的 else）可能没有位置，则**回退到分支自身的 span 以保持可点击**，
  并标注分支类型与 `path k/n`；文件内按行、再按列排序，**不设条数上限**。
- `:36` **Verification 段是本轮见过最诚实的一份**：
  本地矩阵用**故意植入的失败**验证三种记录都出现且位置与植入缺口吻合；
  混合运行只对失败文件出记录；全绿运行**零输出、退出码 0**。
  CI 证据写明了受控条件：在 `clampTimeout` 里临时植入一个不可达语句/分支/函数后，
  **在「全部测试通过（632 文件 / 10326 用例）、只有阈值失败」的隔离条件下**，
  打印出那 4 条记录在 ERROR 行之上；并明确声明
  > 「the planted failure **is not in the committed tree**.」

  → **这是「完成必须有证据」的模板：说清楚测了什么、在什么隔离条件下、以及植入物已移除。**
- `:42` **不设上限是刻意的**：零覆盖文件会产出与语句数同量级的输出，
  「the gate demands zero gaps, so **the full listing is the action list**」。

**它否决了什么备选**（原文 `:30`–`:32`，3 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 依赖内置 `text` 报告的 Uncovered Line #s 列 | **这正是问题本身**：一张仓库级巨表、列宽截断、只有行号、不分种类、通过的文件同列——**在 CI 日志里不可行动** |
| 加 `json` reporter + 失败后读 `coverage-final.json` 的包装脚本 | 纯 ESM/TS 可行，但包装器要**同时包住两个入口**并**改变它们的命令形状**；自定义 reporter 只碰一处配置，**在两个入口自动生效** |
| 用 TypeScript/ESM 写这个 reporter | istanbul 用**管线之外的裸 `require`** 加载，排除了这条路；**为一个报告文件换掉加载机制不成比例** |

---

### I-P14 `implemented/process/2026-07-10-readme-known-limitations-gate.md`（29 行，**全文**）
**主题 (1)(7) —— 「区分『审计过的缺席』与『忘了写』」**

- `:9` **本篇最有迁移价值的一句**：
  > 「Without a shared shape, **an omitted section cannot distinguish an audited absence from
  > forgotten documentation**, and variant headings prevent a repository-wide search.」

  → **这正是 finaudit 要解决的同一类问题**：「这项没有」和「这项没查」在纸面上长得一样。
- `:13` **决策**：每个包 manifest 旁必须有 README，内含规范的
  `## Known Limitations and Deferred Work` 段。门禁**从 manifest 推导包集合**、拒绝缺失的 README、
  **要求恰好一个规范 h2 且至少一个顶层 bullet**。
  近似标题（`Limitations`、`Deferred`、`What is NOT here`、`Non-goals`）**一律失败**。
- `:15` **「真的没有限制」怎么表达**：列进 `NO_LIMITATIONS` 允许列表并省略该段。
  **新增一条限制就必须移除该条目**；重命名与删除都会失败，因为
  「**every entry must name a scanned package**」。
  → **允许列表本身是被门禁校验的，不是一份会腐烂的白名单。**
- `:17` **门禁与评审的分工写得极清楚**：
  > 「The gate checks **presence, shape, and the allowlist**. Review … owns **coverage and accuracy**.」

**它否决了什么备选**（原文 `:21`–`:23`，3 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 自由格式标题 | **无法统一搜索**，而且仍然需要做近似标题检测 |
| 要求写一个空段或写「None.」 | **包后来有了限制时样板可能还留在那儿**；允许列表让**缺席变成显式且可评审的** |
| 设字数上限 | 合理的限制条数本就不同，所以这一层 README **由评审治理、不设预算** |

---

### I-P15 `implemented/process/2026-07-30-cordis-config-source-plane-resolution-gate.md`（27 行，**全文**）
**主题 (5)(7) —— 「CI 从来没跑过那条路径」**

- `:9` **这是本轮最好的一个「门禁盲区」案例**，值得完整复述：
  一个配置项缺了 tsconfig `paths` 映射；通配符把整段替换进不存在的候选路径，
  于是源码启动**回退到 package `exports`**，解析到了 `lib/prompt.js`——**一个产物平面的文件**。
  结果是：**任何有已构建 `lib/` 的环境（`pnpm build` 之后的开发树）都启动正常**，
  而 e2e workflow 跑 TUI PTY 冒烟用的是 `lib` 模式，
  > 「so **CI never exercises the source vector at all** — while **every clean checkout failed**
  > `pnpm dsh` at startup」。

  一句话总结：「No gate checked the source plane, so the breakage **shipped silently and surfaced
  only in fresh worktrees**.」
  → **「测试通过」可能只说明测试和 bug 同处一个盲区。**
- `:13` **对策是静态门禁**：要求**每一个被配置的本地工作区包 specifier**
  都必须**经由 tsconfig `paths` 门面解析到 `.ts`/`.tsx` 源文件**。
  解析失败，或**命中 `.d.ts`（即 `exports` 回退进 `lib/types`）**，都判失败，并**点名配置文件与 specifier**。
  最后一句是自证：「**removing it reproduces the gate failure**」——
  **门禁被验证过它真的会红。**
- `:27` 诚实记下边界：门禁只用 `tsconfig.base.json` 的选项解析，
  一个需要 client-only 编译选项才能解析的 specifier **会被它判失败**——
  而这**符合该门面「作为 tsx 与 vitest 的唯一解析面」的角色**。

**它否决了什么备选**（原文 `:17`–`:21`，3 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 依赖 keyless TUI PTY 冒烟 | 默认源码模式下**确实能抓到**，但**只在干净树上**；CI 只跑 `lib` 模式，**没有一条 CI 线跑源码向量**，本地有陈旧 `lib/` 的开发树也被掩盖。加一条源码模式 CI 冒烟**每次只证明一种组合**；静态门禁**覆盖每一份已发布与示例配置** |
| 把 `dsh-source-launch-smoke` 兼容测试扩成完整启动 | 该冒烟**只断言 TTY 拒绝，发生在插件加载之前**；每条矩阵线跑一次完整无密钥启动**成本更高**，且同样**只证明一种组合** |
| 用 `@deepseek-ai/dsh-*/prompt` 式通配映射 | **修好这一个子路径但修不好这一类**；下一个单文件子路径导出会**同样回归** |

---

### I-A24 `implemented/architecture/2026-08-11-repository-naming-contract-and-rename-ledger.md`（386 行，**部分**）
**读到什么程度（诚实标注）**：**读了 `:1`–`:111`（Problem / Decision 全部 + 命名台账前两组）
与 `:340`–`:386`（Alternatives considered / Verification / Consequences 全部）。
中间 `:112`–`:339` 是逐组的重命名映射表（另外 14 组），只看了 `grep '^#'` 得到的小节标题，未逐行读。**
**主题 (1)(5) —— 「名字是契约」**

- `:11` **问题一句话**，把「命名」提升成架构问题：
  > 「These names are not harmless. **A name tells a contributor where a responsibility starts and stops.**
  > `Store` suggests data access. `Registry` suggests registrations and lookup. `Runtime` suggests live
  > execution and lifecycle. **When one word is used for all three, callers cannot tell which object
  > owns policy, work, or state without reading the implementation.**」
- `:15` **为什么现在做**：最后一个 pre-release 窗口让全仓库重命名很便宜。
  > 「Keeping weak names would have **turned accidental vocabulary into a compatibility contract**.」
- `:19` **范围被死死钉住**（这条纪律本身值得抄）：
  > 「This decision **changes names only**; package responsibilities, service boundaries, behavior,
  > defaults, and data models **stay the same**. A name that exposes a bad boundary requires
  > **a separate proposed Agent Note** for that boundary change.」
- `:21`–`:23` **一个词表，没有第二套**：
  > 「**No alias, compatibility package, duplicate service key, dual event name, or fallback parser
  > remains. The repository rejects the old name.**」「**No family exposes two public vocabularies.**」
- `:35` **命名规则的四句话**：用**普通、具体的名词**；命名**稳定的职责**，
  不是第一个实现、不是当前文件夹、不是可能的未来扩展；
  **不要加不携带信息的词**；**不要靠删掉那个区分作用域的词来缩短名字**。
- `:39` **一条极其具体、可直接迁移的规则**：
  单数 `ctx` key 给单个 engine/runtime/policy/controller/resolver/store/当前配置；
  复数 key 给 registry 或拥有多个具名成员的服务。**类的角色与 key 的单复数必须一致。**
  但紧跟一句反向澄清：
  > 「**A plural key does not by itself make an object a registry; its operations and ownership do.**」
- `:45`–`:63` **「角色词就是契约」表**——15 个词，每个都写明「什么时候用 / 什么时候不许用」。
  这是本篇对 finaudit 最直接的资产（下面摘 5 行，其余同格式）：

  | 词 | 什么时候用 | 什么时候**不许**用 |
  |---|---|---|
  | `Store` | 拥有一个数据集，主要提供 CRUD / 快照 / 订阅 | 它**校验状态机、仲裁权威、分派工作、拥有 provider 优先级、或协调多个域**。「**A map inside a class does not make the class a store.**」 |
  | `Registry` | 拥有一组具名注册，定义查找、重复/优先级规则、注册生命期与销毁 | 主要调用契约是**分派、执行、取消、策略执行或编排**。（runtime 可以内含 registry） |
  | `Runtime` | 跑活的工作，拥有跨调用的分派、取消、provider 协调或操作生命周期 | 只存记录、只返目录、只解析一个值、或只持有配置。「**`Runtime` is not a generic replacement for `Service`.**」 |
  | `Policy` | 决定**什么被允许、被选中、被限制、被观察** | 它去**执行**那个决定所许可的机制。「**Keep policy and executor names separate.**」 |
  | `Service` | 拥有一个内聚的域服务，其权威**无法诚实地归入上面任何一个更锐利的角色** | 名字之所以叫 Service，只是因为类继承了 Cordis `Service`，**或者因为想清楚真正的角色太费劲** |

- `:65` **判别方法是「看调用方主要在调什么」**：主要调 `register()` 并拿回 disposer → `Registry`；
  主要调 `run()`/`dispatch()`/`cancel()`/`execute()` → `Runtime`/`Engine`/`Executor`；
  主要在浏览选项 → `Directory`；只把域数据映射成 UI 数据 → `Presenter`，
  「**If it also changes state, it is not a presenter.**」
- `:69` **限定词必须携带信息**：不要把 `LLM` 放进压缩后端名里，因为**当前每个后端都已经走 LLM seam**；
  `basic` 是**在出现更具体算法名之前诚实的中性名**。
- `:79` **理由与规则分家**：「**This Agent Note owns the rationale and rejected alternatives;
  the guide owns the rule contributors follow.**」
  → **决策记录写「为什么」，操作指南写「怎么做」，不要互相复制。**
- `:380` Consequences 第一段是 fail-closed 的命名版：
  > 「Old on-disk names, wire values, tool names, and configuration entries named in the ledger
  > **do not work**. An owning parser that can identify stale configuration **fails clearly instead of
  > accepting both forms**.」
- `:382` **对「长名字」的辩护与反辩护写在同一段**：
  「The extra word is intentional **when it prevents a false claim about authority or mechanism**.
  A long name **remains wrong when every word does not constrain the role**.」
- `:384` **不许把角色后缀当成免检**：
  > 「**Role suffixes do not replace inspection of behavior.**」

**它否决了什么备选**（原文 `:344`–`:366`，**12 条**；下表摘其中 6 条最可迁移的）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 保持现名 + 加一份术语表 | **术语表无法让 `BashExecutor` 在 PowerShell 也实现它时变得属实**，也无法让 `ToolRegistry` 承认它其实在执行与强制。**区分必须由标识符本身承载** |
| 给每个 npm 包名加上组前缀 | 扁平 npm 名**不需要目录树的副本**；机械前缀**只加长度不解释角色** |
| 把整个仓库称为 SDK | 项目是 agent harness；SDK 是那套受支持的 JSON-RPC 客户端/服务端栈。**两个含义会让包名与产品散文都变歧义** |
| 给每个 Cordis service 类都用 `Service` | **Cordis 继承是实现事实**；类名必须告诉调用方它是注册、存储、解析、控制还是执行 |
| 一律偏好最短的名字 | **短只有在作用域已经清楚之后才有用**。`JobId` 短是因为 `Job` 已承载域，`BgTaskId` 短却晦涩 |
| 用宽泛的名字为可能的未来特性留位 | **给当前每一位读者收取一个未建成的未来的费用**。命名当前稳定角色；真要变边界，发布前再改名或发布后走新提案 |
| 保留旧名别名 | **没有已发布的消费者需要它们**；别名会保住两套词表，**让首个版本背上一次从未有过用户的迁移** |
| 在应用台账的同时顺手重命名或拆分边界 | **评审者必须能看出行为没变**。真正的边界缺陷需要它自己的提案、测试与后果 |

---

### I-A25 `implemented/architecture/2026-07-28-identified-immutable-message-values.md`（50 行，**全文**）
**主题 (2)(3) —— 「身份不是路由的副作用，是值的不变量」**

- `:11` **问题的精确表述**（本条是本轮排得上号的一句）：
  > 「This made **identity a routing side effect rather than a message invariant**.」

  同段还点出**不可变性从不同边界开始**：有的输入被 loop 冻结，有的只在 session append 时冻结。
- `:15` **决策**：一个 `Message` 值，`id` / `role` / `content` / `source` **全部必填**。
  > 「A message receives its id **at creation, before inbox routing, claim, pre-step rewriting,
  > durable append, or request projection**. **The same id survives every representation boundary.**」
- `:17` **创建与导入被做成两个不可混淆的边界**（极好的机制设计）：
  `createMessage(input)` **铸造 id、detach 内容、深冻结整个值**再返回；
  所有创建 helper **都排除输入的 id**，
  「so callers **cannot accidentally present creation as import**」；
  而 `freezeMessage(message)` 是**独立的导入/变换边界**：
  detach 并深冻结一个**身份已存在**的消息，**不铸造替代品**。
- `:21` `Agent` 的 `followup`/`steer`/`inject` **接受完整消息**，
  「These operations **never allocate or return identity**」。
  内容重写产生一个**同 id 的冻结替代品**，而附加上下文是**另一个有自己 id 的新消息**。
- `:25` **一条判定「改的是表示还是语义」的规则**，可直接迁移到 finaudit 的口径调整：
  > 「Any operation that changes **only the representation** of an existing semantic message
  > **preserves its id**… An operation that creates **a new semantic message mints a new id**.」

  举例：压缩时的内容重写**保留被重写的 tool-result 身份**，而摘要检查点**是一条新消息**。
- `:43` **信封与语义分家**：事件信封仍然拥有**不属于消息语义的事实**——
  turn/step 位置、token 用量、内部工具失败身份、呈现元数据。

**它否决了什么备选**（原文 `:29`–`:35`，4 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 让 id 在基础消息上保持可选 | 能少迁移 fixture，但**保留了原来的歧义**：每个消费者都要分支判断身份是否存在，**没有任何类型能证明 admission / 记录 / 投影保住了它** |
| 让 agent 投递去分配 id | 身份被限定在 inbox 关联上，但**agent 调用成了生产者能给自己消息命名的最早时点**；提示构造、UI 附件、同步入队/丢弃协调**只能靠内容匹配或带外 token** |
| 让每个持久事件各分配一个新 id | **刻意打断与实时输入的关联**，让重放的请求**看起来包含不同的消息**。「**Identity belongs to the semantic value, not to each envelope that carries it.**」 |
| 只在 agent 或 session 准入时冻结 | 省掉一个创建 helper，但**留下一段「有身份却可变」的区间**，调用方代码可以在其中改变那个 id 所关联的含义。该决策**让「有 id」与「是不可变快照」重合** |

---

### I-A26 `implemented/architecture/2026-06-11-dev-invariants-over-deep-readonly.md`（60 行，**全文**）
**主题 (2)(7) —— 「值的不可变」与「事实之间的关系」是两件事**

- `:13` **本篇的核心区分，直接对应 finaudit 的两类校验**：
  > 「**Immutability of individual values is only half of the contract.** A log can contain
  > **perfectly immutable records whose sequence, turn/step nesting, tool-call pairing, scoped delivery,
  > or reconstructed model request is wrong.** Those rules **relate multiple records or services and
  > cannot be established by freezing one object**.」

  → 翻译到审计：**每一条取数都不可变**，不代表**期间可比、勾稽关系成立、口径一致**。
- `:15` **为什么不用类型系统解决**：TypeScript readonly **不是运行时边界**——
  「They **disappear when the program runs**, **a cast can bypass them**」，
  而递归 `DeepReadonly<T>` 会**扩散到每一个日志与消息消费者**，
  哪怕有些下游请求处理 API **是刻意要用可变值的**。
- `:23`–`:25` **存储边界的三步，一步都不能少**：
  `Session` **只在一次递归遍历产出了无损 JSON 快照之后**才接受事件——
  该遍历**拒绝不支持的值**，并**产出进入日志的那个精确的、已 detach 的记录**，
  「so validation and storage **cannot observe different values from a stateful getter**」。
  然后被接受的事件**及其全部后代在发布前深冻结**；
  `append()` 返回那个已拥有的冻结事件，观察者收到**同一条记录**，
  `session.events` 返回**冻结的数组快照**——
  「**A previously returned array does not grow after a later append.**」
- `:27` **为什么这条必须常开而不能做成插件**：
  > 「This guarantee belongs in `Session`, **not in an optional listener**, because
  > **every composition relies on trustworthy history**.」
- `:35` **关系型校验的归属设计**：`dsh-invariants` 只注册可配置的 `ctx.invariants` 服务，
  **本身不含任何产品检查**；**每个包各自发布 `./invariant` 归属伴生件**。
  当前的规则清单本身就是一份很好的「关系型不变量」样例：
  **单调序号、turn/step 嵌套、tool-call/result 配对、合法的 agent 状态迁移、
  subject 正确的 scoped dispatch、以及「loop 构建的请求」与「从会话日志前缀重建的请求」相等**。
- `:37` **热重载安全**：服务给每个贡献一个**可销毁的子 fiber**，
  「so hot reload is safe **in the middle of a turn** without **giving diagnostics ownership of
  session storage**」。

**它否决了什么备选**（原文 `:41`–`:51`，3 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 全面铺开 deep-readonly 类型 | 给编辑器反馈，**但不给运行时保证**（类型被擦除、插件可强转），还**把 readonly 推进那些刻意要变更的消费者**。在 `Session` 边界做运行时归属**保护了每个调用方而不需要类型扩散** |
| 只在开发期冻结 | 会让**核心保证依赖于组合方式**：代码可以**通过开发期测试却在生产或省略该插件的组合中损坏历史**。存储不可变因此**常开**，昂贵的关系型检查才是可选 |
| 只在 deriveMessages 时克隆 | 保护了最常见的请求路径，但**留下 `session.events`、append 返回值与事件观察者**仍能改动持久历史。「**The log must protect its own boundary**；派生投影是**额外**的隔离边界，不是替代」 |

**对 finaudit 的输入**：把校验分成两层，命名也分开——
**「记录级不可变」常开、无条件、在写入边界完成**；
**「关系级不变量」（勾稽、可比、口径一致）可配置、按模块归属、各自拥有自己的规则**。
不要把两者塞进同一个开关。

---

## 8. `implemented/` 第四批 —— 持久化协调、穷尽性后备、身份类型、归属声明

> 本节 8 条为本轮第四批（2026-08-22 续读）。
> 关注点：**「谁保证日志是完整的」「怎么证明一份生成清单没漏东西」
> 「怎么让『拿错了 id』变成编译错误」「对外声明自己是谁时能说什么、不能说什么」。**

---

### I-A27 `implemented/architecture/2026-06-14-session-persistence.md`（36 行，**全文**）
**主题 (2) —— 「持久单元就是既有事件本身，不许有第二个类型」**

- `:9` **问题里的一句自嘲式描述**，可以直接当 finaudit 早期原型的警示：
  那个示例插件是**只写的遥测**——「no read/replay path, **no crash-safety**（no fsync, no atomic write,
  a **fire-and-forget dispose drain**）, no listing, and **no format versioning**」。
- `:11` **对事件溯源模型的忠诚被写成硬约束**：
  > 「persist the existing `SessionEvent` **directly, with no parallel "persisted message" type
  > that the log is converted to and from**.」
- `:22` **本篇最值得抄的一条拒绝**——为什么不做「过滤掉 chunk 的规范日志」：
  Codex 的 `policy.rs` 形状**很诱人**，但 `seq = log.length` 与 `events[i].seq === i` 的校验
  **要求一个连续的逻辑日志**；过滤会**留下洞并同时破坏契约与 resume**。
  > 「A chunk-filtered projection is possible later **as a derived view with its own renumbering**,
  > but it is **NOT the canonical log**.」

  → **想要"精简视图"就去做派生视图，不要动规范日志。**
- `:23` **「崩掉的 turn 被闭合，从不被截断」**——这条对审计极重要：
  > 「Because **one interrupted turn may contain substantial valid work**, cold inspection preserves
  > its contiguous, parseable events and **adds risk-classified error results** for unanswered
  > assistant calls, a missing `step/end`, and `turn/end` with `{ kind: 'interrupted' }`」。

  而且划清了「可修复」与「腐坏」的界：**只有不完整的最后一条记录会在提交式修复中被丢弃**；
  **在最后一个真实 `turn/end` 处或之前**出现解析错误或序号缺口，**是腐坏，会话不可加载**。
- `:25` **元数据在日志之外**：格式版本、cwd、血缘是**存储关切，不是可重放的对话状态**，
  所以住在 `SessionHeader` 里，**永不进入 `SessionEventMap`，永不到达 `deriveMessages()`**。
  连 `createdAt` 都被钉死为**非负安全整数 Unix 毫秒**，三处各自校验（live 创建、JSONL 解码、SQLite 严格 `INTEGER` 列）。
- `:24` **换后端不换语义的证据**：SQLite 后端**跑同一套 `runPersistenceContract`**——
  「so the contract holds **both backends to identical semantics**…
  **expressed once over file bytes and once over rows**」。
  → **同一份契约测试跑在两种介质上，是"接口真的抽对了"的唯一硬证据。**

**它否决了什么备选**（原文 `:30` 集中列出 6 条，加 `:32` 的格式版本立场）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 过滤 chunk 的规范日志（Codex `policy.rs` 形状） | **破坏连续 seq 契约** |
| 截断崩掉的 turn | **静默销毁一次长自主运行的真实工作** |
| 把 `session/meta` 作为日志第 0 行的事件 | 它能**随 seed/fork 免费带走**，但**元数据不是可重放状态**，显式的日志外 header 是**更干净的代价** |
| 允许有限小数的 `createdAt` | **没有生产者**，且与整数毫秒的存储与查询列**发散** |
| 采用非全新的、无版本的 SQLite 文件 | **可能覆盖无关对象或身份** |
| 把 `sessionPersistence` 硬注入 loop | 会让**非持久化的 demo 永远挂起** |

`:32` 还留下一条诚实的能力边界：append-only + flush **对部分尾写是健壮的**
（冷准备阶段容忍），**但对没有 fsync 的断电中途写不健壮**——那种场景 DB/WAL 后端更强。

---

### I-A28 `implemented/architecture/2026-06-18-shared-persistence-write-coordinator.md`（47 行，**全文**）
**主题 (5) —— 「不透明标记：让协调器不需要知道存储介质的任何事」**

- `:9` **问题**：两个后端**故意在不同介质上证明同一份契约**，但写路径编排被复制了两份，
  「the remaining orchestration was still **correctness-heavy and received the same fixes twice**」。
- `:15` **组合而非继承，理由写得非常具体**：
  > 「a backend exposes **only the hooks** and **cannot reach the coordinator's private orchestration
  > state**」，而且**第三方后端仍可以完全不用协调器**直接实现抽象服务。
- `:27` **一个把"原子性"要求写清楚的 hook 注释**（值得逐字抄）：
  `appendBatch` 必须**在尚未 materialize 时原子地做 materialize**——
  > 「the materialize-write and the first event batch **must commit together** — a crash between them
  > **must not leave a materialized-but-empty session**; **this is why there is no separate
  > `materialize` hook**.」

  → **接口形状本身就是不变量的载体：把两件必须一起提交的事合成一个 hook。**
- `:28` **同时明写哪一步"不要求原子"**：`commitRepair` **NOT required to be atomic**——
  JSONL 合法地分两个 fsync 步骤先截断后追加，SQLite 在一个事务里 DELETE+INSERT。
  → **不要求的就说不要求，别让实现方去猜。**
- `:34` **本篇的核心机制，一句话**：
  > 「the crash-repair "**where is the torn tail**" token **is OPAQUE to the coordinator**.」

  协调器**只测 `tornMarker !== undefined`，然后原样传回**，**从不检视它**。
  JSONL 的标记携带**要截断到的字节偏移 + 从不完整末帧解出的完整事件**，
  SQLite 的标记携带**要删除起始的 seq**。
  「The coordinator therefore **knows neither byte lengths nor frame recovery state**.」
- `:19` **一条防止"完成擦掉更新的操作"的细节**：已结算的 per-id 链尾
  **只在它仍是当前的那一个时才自我移除**，
  「so a completion **cannot erase a newer operation for the same id**」。
- `:30` **关闭顺序也是契约**：可选的 `close?()` **在静默排空之后**才 await，
  「so **a close failure never masks a drain error**」。

**它否决了什么备选**（原文 `:42`–`:43`，2 条，其中第二条含 5 个子项）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 让后端继承一个基类 | 选组合：后端**只暴露 hook、够不到协调器的私有编排状态**，第三方后端还可以**完全不用协调器** |
| 更宽的 hook API | 每个候选 hook 都能折叠掉：**不需要 scope 专用的 live 查找**（`loadStored` + cwd 检查已保住冲突边界）；**不需要存储定位泛型**；**不需要独立的 `materialize` hook**（首批必须与 materialize 原子提交）；**不需要独立的创建冲突探测**（它就是 `loadStored(id) !== undefined`）；**`list()` 不需要走协调器**（列举不需要任何编排） |

---

### I-A29 `implemented/architecture/2026-08-09-cordis-event-walk-backstop.md`（38 行，**全文**）
**主题 (3)(7) —— 「生成器与后备必须能各自独立地失败」**

- `:11` **问题是一个非常典型的「静默消失」**：投影只走 host-face 包导出可达的文件，
  于是 client-face 里的 `interface Events` 合并**无声无息地消失**——
  > 「12 declared events … were documented nowhere generated and **nothing would ever notice
  > a thirteenth**.」

  更妙的是**连那个「防止静默消失」的扫描本身也有盲区**：它只 glob `packages/*/*/src/*.ts`，
  于是嵌套文件里的 13 个 Context key**对它不可见**。
  → **给"防漏"做的检查，自己也会漏。**
- `:17` **第三个方向的分区检查**（本篇最值得抄的一招）：
  除了「声明了但没渲染 → 必须豁免」「豁免了但其实渲染了 → 错」，还加了第三向——
  > 「**every rendered service key and event name must also be visible to the scan**, so a scan
  > regression (glob, prefilter, block walk) is **a hard error rather than a silent backstop decay**.」

  → **给检查器本身加一个"你还活着吗"的判据。**
- `:19` **豁免的粒度选择有理由**：`EVENT_WALK_EXEMPTIONS` 的 key 是**完整事件名而不是 scope**，
  因为 client-face 事件与 host 事件**共享 scope**，
  「so a scope-level exemption would **mask a host-face regression**」。
  三向 fail-closed：**未豁免的不可见事件、给已渲染事件写的豁免、以及没有任何合并声明的豁免，全是硬错误。**
- `:21` **判断逻辑被抽成纯函数**：分区判断从 `computeOutputs` 移进纯 `walkPartitionProblems(input, maps)`，
  「so **every acceptance path is provable by unit test without running the Typert projection**」。
- `:27` **Verification 里那条自证极漂亮**：
  从真实树里**删掉一条活着的豁免**会让生成器**带着事件名与声明文件大声失败**；
  **恢复它则让生成器回到字节相同的空转重生成（85 artifacts, 0 written）**，
  「which **also proves the new exemptions exactly cover today's surface**」。
  → **一次删除 + 一次恢复，同时证明了"门禁会红"和"豁免不多不少"。**

**它否决了什么备选**（原文 `:31`–`:34`，4 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 干脆把 client face 也渲染出来，不用豁免 | 那是**底层盲点的真正修法**，但它**改变了这份目录「是什么」**（host 层参考），并需要为浏览器专属表面做页面决策。「**The backstop is the guarantee; rendering is an upgrade behind it.**」 |
| scope 级的事件豁免 | 表更小，但 `commands/changed`（client）与已渲染的 host 事件共享 `commands` scope，**豁免一个 scope 会静默吞掉未来的 host-face 事件——正是本篇要消除的失效模式** |
| 用 Typert 而不是原始 AST 扫描来推导穷尽性 | **投影与后备必须独立失败**：**Typert 的可达性 bug 正是后备存在的理由**，所以扫描**刻意保持为一个不共享任何机制的朴素 `ts.createSourceFile` 遍历** |
| 对已渲染签名做传递类型闭包门禁 | **决定之前先量过**：已渲染签名里可达的每个类型名都已被分类，更深的字段之字段类型由页面手工策展的 `type-equiv` 与包 README 拥有；闭包门禁会**为内部类型强行安排页面归属而没有面向读者的需求** |

---

### I-A30 `implemented/architecture/2026-07-29-terminal-llm-stream-failures.md`（37 行，**全文**）
**主题 (4) —— 「一次尝试只有一种失败表示」**

- `:7` 又一个**部分取代声明写在开头**的例子，并逐项说明**旧笔记继续拥有什么**
  （结构化失败事实、重试策略、持久尝试、压缩恢复）。
- `:11` **问题**：适配器失败有**两种公开表示**——抛异常，和带内的
  `finish { kind: 'error' | 'aborted' }`。于是
  > 「correctness therefore depended on **proving which statement threw** and **consulting metadata
  > attached to the exact returned iterable**.」

  → **靠"是哪一行抛的"来判断语义，是不可维护的。**
- `:17` **决策**：`LlmRuntime` 是**一次适配器尝试的规范化边界**。
  它**只**捕获四种（最终适配器选择、同步 dispatch、迭代器构造、`next()` 失败），
  转成**不可变的 `LlmFailure`**，并**发出一个终结性 `finish`**。
- `:19` **捕获边界的终点写得极精确**：
  > 「**The adapter-owned catch ends before each yielded chunk.**」

  来自 `llm/stream` 中间件、嵌套调用、适配器清理、chunk 消费者、日志、信号检查、装配的错误
  **仍然作为 defect 或生命周期失败抛出；它们永不进入 model-request 恢复**。
  并配一条流不变量：**只有终结性 error/aborted 才允许留下未闭合的 block**，
  「**No assistant message or tool call is assembled from that incomplete output.**」
  → **半截的输出不许被装配成事实。**
- `:23` **消费方只消费一种表示**：agent loop **不再需要分类用的 catch**，
  它迭代并记录 chunk、检视终结 finish、把失败事实 + prepared policy 交给 `agent/request-error`。
  三个 sidecar API **被删除**（`isLlmAdapterFailure` / `llmFailureOf` / `llmRetryPolicyOf`）。
- `:37` **诚实记下放弃了什么**：
  > 「Recovery **gives up exact thrown-object identity** and exposes only **detached provider-neutral
  > facts**.」

**它否决了什么备选**（原文 `:27`–`:33`，4 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 保留 call-local 的错误打标 | 保住了抛出对象的身份，但**逼每个消费者去 catch 一个包含它自己可失败工作的区域**，并**把分类耦合到一个 iterable 包装器的身份**。「**The original error object has no durable role in recovery**；规范化的事实才是有用的边界值」 |
| 要求每个适配器都发失败 chunk、禁止抛异常 | 库迭代器、传输层与 JavaScript dispatch **仍然可以抛**。要求每个适配器复现同一个 catch 边界**重复了归属**，且**保护不了直接使用 `LlmRuntime` 的消费者** |
| 在 agent loop 里 catch 所有迭代错误 | loop **无法可靠地把 provider 失败与中间件/会话追加/取消/装配失败区分开**，除非恢复那张 sidecar 映射。「**Classification belongs where the adapter call is made.**」 |
| 在流开始前返回一个 `Result` | 流前的 result **无法表示部分输出之后的传输失败**，除非再加第二套响应生命周期。既有的终结 chunk **已经同时表示早期与晚期的尝试结果** |

---

### I-A31 `implemented/architecture/2026-06-20-branded-ids.md`（69 行，**全文**）
**主题 (6) —— 「让『拿错了 id 的种类』变成编译错误」**

- `:9` **本篇先引用了自己仓库里那条治理政策，再说它只被执行了一半**：
  > 「*Branding is for ids that **cross package boundaries and could plausibly be confused**;
  > **not every string needs a brand**.*」「That policy is right; the problem is that
  > **it is only half-applied**.」
- `:11` **Gap 1 讲得极具体**：后台 job id 是裸 `string`，由每个执行器的计数器生成
  `` `bash-${this.nextTaskId++}` ``，**与 `SessionId` 的默认形状 `` `session-${++counter}` `` 完全一样**。
  > 「A bash job id and a session id are **trivially swappable at a call site and the compiler says
  > nothing**. It is a **model-facing id** … so **a confusion here is reachable from untrusted input**.」
- `:13` **owner token 是更危险的子情形**：它被文档描述为**刻意不透明**的隔离 key，
  但**在每个活着的调用方它就是 `Agent.id`/`SessionId`，只是换了个 seam 局部的名字**；
  它被用于访问控制比较，所以
  > 「a **mismatched-but-well-typed string** here is a **cross-session isolation bug**
  > the type system currently cannot catch.」
- `:15` **Gap 2 —— 品牌在边界处侵蚀**：即使已加品牌的 `CallId`/`SessionId`，
  也**在最容易混淆的地方退化回裸 `string`**：registry/store 的 key 类型与公开方法参数。
  > 「**A brand that is dropped at a collection key buys nothing on lookups**」。
- `:49` **为什么不把 `owner` 直接标成 `SessionId`**（本篇最好的一段推理）：
  把 Service Definition 的字段标成 `SessionId`，会**把 `dsh-session` 的词表引进一个
  「必须不知道 owner token 意味着什么」的包**——
  「it would **couple a generic execution backend to the session model** and **contradict the
  opaque-token design**. A sandboxed or remote executor … **should not inherit a session dependency**.」
  于是 `dsh-shell` 只知道「owner 是某种不透明的品牌 token」，
  **由已经决定访问策略的那个消费者作为唯一边界去做转换**。
- `:53`–`:59` **「暂不做」清单，每条带理由而非承诺**（这个格式本身值得抄）：
  `ModelId`（合理的下一个，只为控制爆炸半径而略过）、
  `ToolName`（作者定义、人类可读、**最弱的候选，多半不值得**）、
  `ErrorCode`（**是封闭词表不是 per-instance id，字符串字面量联合更合适**）、
  数值序数（`Branded<string>` 不适用，且**是位置序数、极少跨边界，收益低**）、
  **带校验的构造**（品牌工厂是**纯 cast、没有运行时检查**；加 `parse()`/`isValid()`
  是**运行时行为变更、有自己的设计问题，属于它自己的决策**）。
- `:68` **Consequences 里最诚实的一句**：
  > 「**Brands do not validate.** A brand is a **confusability guard, not a correctness proof**:
  > a *wrong* session id that is still a well-formed string **passes the type checker exactly as before**.
  > … it only stops the **category** error of passing the wrong **kind** of id.」
- `:69` **连"边界在哪停"也承认是判断题**：
  「Branding `BashTaskId` but not `ToolName` … is **a taste call**」，
  并给出 tie-breaker：**倾向于面向模型的、或用于访问控制的 id**。

**它否决了什么备选**（原文 `:47`–`:49`）：
唯一正式否决的是**把 `owner` 直接类型化为 `SessionId`**，理由见上（会耦合执行后端到会话模型、
违背不透明 token 设计、让沙箱/远程执行器继承会话依赖）。
`:51`–`:59` 的「Out of scope / possible extensions」**是延后而非否决，原文明说
「deferred with a reason, not a commitment」**。

---

### I-A32 `implemented/architecture/2026-06-21-mandatory-app-attribution-headers.md`（82 行，**全文**）
**主题 (1) —— 「对外声明身份时，只说静态的公开产品事实」**

- `:11` **风险被一句话点破**（这是本篇最可迁移的判断）：
  采用某个供应商的确切 header 集合**就好像它是通用标准一样**，然后
  > 「**leaking provider-specific headers** to direct DeepSeek requests, future OpenAI/Anthropic/Vertex
  > adapters, test servers, or **proxies that log unknown fields indefinitely**.」
- `:13`–`:23` **有一整段 `## Investigation`**，逐条把「谁是标准、谁是惯例、谁是某家的产品特性」分开：
  RFC 9110 §10.1.5 的 `User-Agent` 是**唯一直接对应「哪个产品在发这个 HTTP 请求」的标准 header**；
  OpenRouter 的 `HTTP-Referer` **名字与含义都是它自己的**，尽管长得像标准 `Referer`；
  RFC 9110 §10.1.2 的 `From` 是标准但**不适合作强制默认**（隐私）；
  请求体的 `user`/`metadata` **标识的是终端用户而不是产品**；
  SDK 遥测 header **标识的是 SDK 而不是应用**。
  → **这一段是"先把概念分清再做决定"的范本；finaudit 在引用准则时应当同样区分
  「准则原文 / 行业惯例 / 某家事务所的做法」。**
- `:31`–`:37` **归属身份由 `dsh-llm` 拥有，不由各适配器拥有**；
  `AppIdentity` **只包含构造 `User-Agent` 所需的公开产品事实**；
  版本**从所属包 manifest 读取，绝不手抄常量**。
  然后是一条极硬的隐私边界：
  > 「There is **no per-request API for the model, user prompt, session id, cwd, user email,
  > API key owner, or local machine identity** to influence these fields.」
- `:29` **明确写下"故意不做什么"**：OpenRouter 的四个 header **刻意不实现**，
  「Until then, **even requests pointed at OpenRouter send only the shared `User-Agent`**」。
- `:48` **连"以后要做也必须显式"都先规定好**：若将来支持 OpenRouter，
  检测**必须显式**（专门的 provider 包，或显式 config），
  「**not arbitrary path fragments or model names**」。
- `:52`–`:60` **Verification 是一份可逐条核对的清单**，其中两条是负向断言：
  「**No adapter sends OpenRouter-specific attribution headers**」、
  「**No app-attribution field carries secrets, local paths, session ids, prompt text, model output,
  user email, or per-user stable identifiers.**」
  → **负向断言（"我们没有发送 X"）也要进验证清单，不能只列正向。**
- `:80` **抽象压力测试**：pi-ai 若升级后不再传递 header，**mock server 测试会变红**。
  > 「This is **useful pressure on the abstraction**: a provider adapter that **cannot set mandatory
  > headers cannot fully implement the harness LLM contract**.」

**它否决了什么备选**（原文 `:64`–`:74`，5 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 现在就做 OpenRouter app attribution | 那些 header 是**某供应商的产品特性，不是本决策要标准化的供应商中立请求归属**；应当是**显式的 OpenRouter 适配器/模式决策**，而不是**藏在第一个共享归属 helper 里** |
| 到处都发 OpenRouter header | 会**把一份自定义契约当成通用标准**，向**没有要求过的供应商发送语义误导的字段** |
| 只用供应商账号/项目身份 | 那些标识的是**谁付钱或谁拥有请求，不是哪个应用在发流量** |
| 用终端用户 `user`/`metadata` 字段 | 那些描述的是**请求背后的人或租户**；app attribution 必须是**静态产品身份且每次请求都安全可发** |
| 配置式 opt-in 归属 | **默认关闭正是适配器持续漂移的方式**。政策是**强制的默认归属 + 可覆盖的公开值**，不是可选归属 |
| 用 SDK 名做 `User-Agent` token | `deepseek-harness` 胜出，因为它**命名的是产品、匹配组织/仓库身份与包 scope**，且**不把整个产品称作 SDK** |

---

### I-P16 `implemented/process/2026-08-09-md-fragment-anchor-gate.md`（32 行，**全文**）
**主题 (7) —— 「人工 grep 的规则被实证推翻」**

- `:9` **问题带实测数字与三种衰减模式**：全语料扫描发现 **15 条链接的 fragment 在目标里没有对应锚点**——
  ① 链接写好后标题被改写；② 契约搬到了另一份拥有它的文档；
  ③ 中文对照件链接的是**其中文标题永远不会产生的英文 slug**。
  > 「**None of these fail any gate**, and each **silently strands the reader at the top of the target page**.」
- `:13` **门禁规则里的细节全部对齐 GitHub 的真实渲染**：
  slug 从**渲染后的标题文本**计算（标题里的链接、行内代码、强调都按 GitHub 的方式参与）；
  **下划线保留**；重复 slug 用 GitHub 的 occupied-set `-1`/`-2` 后缀；
  **大小写精确匹配**（因为元素 id 是大小写敏感的）。
  同时明写**不管什么**：指向非 Markdown 目标的 fragment（`file.ts#L10`）**语义由渲染器拥有，不在范围内**。
- `:15` **刻意不共用 slug 函数**：与 `gen-cordis-catalog` 的 slugger 规则不同
  （后者丢下划线），因为生成器的标题总是通过显式 `<a id>` 可达，
  「**the two need not share one rule**」。
- `:21` **Verification 里那句话最值钱**：
  > 「the gate runs over the full corpus … and **passes only after the 15 fixes —
  > the corpus itself is the red-to-green evidence for each decay mode**.」

  → **不是"我写了测试"，而是"真实语料本身就是这条门禁从红到绿的证据"。**

**它否决了什么备选**（原文 `:25`–`:28`，4 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 保留人工 grep 规则 | **它被实证证明没守住**：那 15 条 fragment **是在一个由门禁驱动的维护文化下衰减掉的**，因为标题改写发生在**从不看入链的 PR** 里。「**A mechanical invariant belongs in an executed gate.**」 |
| 让中文链接指向中文 slug 锚点 | GitHub 能给 CJK 标题正常 slug，但**语料现有约定已是显式 `<a id>` + 英文 fragment**，那还能**在剥离非 ASCII 的渲染器下存活**；采用第二套约定会**劈裂语料** |
| 与 typert 生成器共用 `githubSlug` | 一次函数导入会**把文档门禁耦合到包构建**，而**两套规则确实不同**，所以**分歧是设计而非漂移** |
| 顺便校验 VitePress slug | 站点自己的死链检查**已经在 `website:build` 里跑**；生成区域带显式锚点**正是为了让两个渲染器一致** |

---

### I-P17 `implemented/process/2026-06-20-core-data-structures-catalog.md`（61 行，**全文**）
**主题 (6) —— 「粘贴的类型定义如何被机械地保证不漂移」**

- `:9` **问题里那句判断，适用于 finaudit 的一切"口径说明文档"**：
  > 「a catalog that paraphrases or paste-copies type definitions **rots the instant a field changes** —
  > and **an out-of-sync type doc is worse than none, because a reader trusts it**.」
- `:21` **范围线是靠一个判例定的**，不是靠定义：
  `ShellExecRequest`/`ShellExecSpec`/`ShellRunResult` 是**决定性测试用例**——
  如果它们算 core，那 core 就等于**所有跨包词表**，目录就成了平铺倾倒；如果不算，core 就是**中央脊柱**。
  后者胜出，于是整个结构变成**分层文件夹而不是单张平文档**。
  → **划范围时先找一个能把两种理解逼出不同结论的判例。**
- `:23` **定下来的规则一句话**：
  > 「***the type you write, hold, or receive is core; the machinery that types it, renders it,
  > or persists it is a subsystem-page detail.***」

  两条刻意的例外也写清楚了：`ToolDefinition` 是 core **尽管 loop 从不持有它**
  （**作者重要性压过严格的"流经脊柱"规则**）；
  `ToolSchema` 是 core 尽管概念上属于工具流水线（**"流经脊柱"压过"概念归属"**）。
- `:34`–`:38` **`ts type-equiv` 机制**（本篇最可直接迁移的资产）：
  完整类型声明与其 JSDoc **逐字粘贴**进专用围栏；
  `verify-type-equiv.ts` 用 TypeScript parser 抽取每个块，
  **断言其声明结构与每一条 JSDoc 都与被声明符号匹配**，
  **只忽略格式空白与非 JSDoc 注释**。
  为什么不用编译期 `_Check` 断言：
  > 「**source names and documentation identity, not assignability, are the properties
  > the catalog preserves**.」

  每个块的 `{ doc, symbol, source }` 记在**中心 manifest**（不是散文里的指令注释），
  脚本强制 **1:1 对应**，
  「so **a block can never be silently unchecked and an entry can never rot**」。
- `:38` **中英对照的处理很讲究**：`.zh.md` 的块**只有在完整的被跟踪围栏序列
  在顺序、种类、字节上都与无后缀兄弟件一致时**才复用它的 manifest 条目；
  否则门禁独立检查它、找不到条目、**失败**。
- `:41`–`:43` **门禁与人的分工被明说**：
  > 「`verify-type-equiv` catches a **drifted paste** of an already-documented type,
  > but **it cannot tell you a brand-new core type went undocumented**. …
  > **the gate handles drift, the human handles new types.**」
- `:53` **一条被单独立成 `## Verification lesson` 的教训**：
  门禁**必须扫描完整的 Markdown 范围，而不只是 manifest 点名的文档**，
  否则**一个未登记的 `type-equiv` 块就逃过了那个号称 1:1 的检查**。
  于是门禁**把这类块报为 orphan**。
  → **"我检查了所有登记在册的" ≠ "我检查了所有存在的"。这条对审计抽样直接适用。**

**它否决了什么备选**（原文 `:47`–`:49`，3 条）：

| 被否决方案 | 理由（原文要点） |
|---|---|
| 平铺倾倒所有跨包词表 | **`ShellExecRequest` 这个判例杀死了它**：如果 seam 词表算 core，这份目录**对谁都没用** |
| 用编译期 `_Check` 可赋值性断言代替源码匹配 | **可赋值性不保留名字与 JSDoc**：**改名但同类型的字段、或改动过的契约注释都会通过** |
| 把每个类型块的来源写在指令注释里 | 选中心 manifest，因为**它强制的 1:1 对应意味着块不可能被静默跳过、条目也不可能腐烂** |

**对 finaudit 的输入**：财务指标口径文档就是这里的「类型目录」。
可迁移的三件事：**① 逐字引用准则原文而不是转述；② 用中心 manifest 记录
「哪段文字对应哪条准则的哪一版」并强制 1:1；③ 明确门禁只能抓漂移，
"新增了口径却没写文档"必须由人负责——并且把这条分工写进制度而不是指望自觉。**
