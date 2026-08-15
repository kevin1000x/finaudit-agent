# deepseek-harness 深读报告（subagent 独立上下文产出，2026-08-15）

**读到什么程度**（子 agent 自报，未删改）：

| 文档 | 程度 |
|---|---|
| `agent-lifecycle.md` | 读完 |
| `capability-seams.md` | 定义段 + 服务表全部，跳过生成的 mermaid 节点定义 |
| `subsystems/core.md` | 1–389 行；`ctx.agentPresets` 之后的生成 catalog 未读 |
| `subsystems/persistence.md` | 读完 |
| `subsystems/compaction.md` | 读完 |
| `subsystems/llm-streaming.md` | 前 220 行；生成 catalog 未读 |
| `event-producer-consumer.md` | 读完 |
| `AGENTS.md`（根） | 读完 |
| `subsystems/invariants.md` | 读完（自选） |
| `defensive-patterns.md` | 前 7 条 pattern |
| `cookbook/adding-a-conversation-node.md` | 前 2 节 |
| `subsystems/spill.md` / `token-meter.md` | 各前 55–60 行 |

**完全没读**：`api-gateway` `config-catalog` `glossary` `graph-atlas` `module-graph`
各类生成 catalog、`testing` `development` `cordis-primer` `rescope` `postmortem/` `user/`，
以及 `subsystems/` 下其余约 30 篇（approval / session-projection / scope / skills /
system-prompt / jobs …）。

---

## ⚠️ 它推翻了主文件里我原先的判断

`references/deepseek-harness.md` §3.1 原写「语义层闸门是 `agent/pre-step` 的一个 listener」。
**这个判断不够强，已在主文件更正。** 子 agent 的理由（我核过，成立）：

> waterfall 意味着任一监听者短路即绕过，而**是否调 `next()` 只能靠 review 检查** ——
> 这恰好是「LLM 若能不调它整个论点就没了」的失效模式。

waterfall 中注册顺序在闸门之前的 listener 一旦不调 `next()`，闸门根本不会执行；
而注册顺序是运行时/配置问题。**正解是把闸门放进调用签名**，见下方 §2.10。

---

## 1. 最值得优先落地的三条

1. **把「模型可见 ⟺ 已记录」写成 CI gate，并生成一张「谁能写哪个证据字段」的矩阵**（§1.1 + §1.12）
2. **证据节点做成按 `source_kind` 判别的闭合联合，字段随 kind 强制**（§1.9 + §3）
3. **口径解析独立成 `resolve_scope() -> ScopeSpec | Refusal`，计算函数签名只接受 `ScopeSpec`**（§1.10）
   —— 让绕过闸门成为**类型错误**而非策略问题

## 2. 可借鉴的机制（编号沿用报告）

### 1.1 「模型可见 ⟺ 已记录」是可机械检查的硬规则

> **Model-visible ⟺ logged**: anything that reaches a model request must be reconstructable
> from the session log; a new model-visible input requires a session event.（`AGENTS.md`）

它被写成仓库级 convention 并由 gate 检查，不是口号。
**用法**：改写为 finaudit 第一公理——**凡进入答案的事实 ⟺ 有一条证据事件**，反向亦然。
进 CI gate：扫描所有构造 prompt 的代码路径，任一未经证据事件的字符串拼接直接 fail。

### 1.2 光有原始输出不能证明它走了受审计的路径

`compaction/summary` 载荷含 `{summary, rawOutput?, llmStreamCall?, provider, model, usage…}`，
并注明「**unmarked `rawOutput` does not identify the call path**」。

**用法**：每条「模型参与」的证据必须带 `via_audited_path: true`；无此标记的输出
即便字节完全一样也**不得**计入证据链。堵住「手工塞一段文本冒充模型输出」。

### 1.3 锁括号最后释放，让崩溃留下可检测的孤儿

> Releasing the lock last turns a crash mid-operation into a **detectable orphaned lock**
> rather than a `compaction/end` that falsely claims compaction finished.

**用法**：`derivation/start` → 证据事件… → `derivation/end`，**end 最后写**。
孤儿 start ⇒ 该指标结论**不可用**，复核工具必须拒绝呈现，并阻塞该指标重算入口直到人工裁决。

### 1.4 崩溃恢复不截断，用一个「只有恢复能发」的保留原因收尾

`interrupted` 是唯一一个**任何正常循环都不发**的 `TurnEndReason`。
且「Repair applies only to cold sessions」——活跃 run 拒绝被合成收尾。

**用法**：拒答码里预留 `interrupted`，约定运行时正常路径一律不许发它。

### 1.5 「格式不支持」与「数据损坏」是两类错误

`SessionFormatUnsupportedError` 与 `SessionPersistenceCorruptionError` 分开，
理由是「nothing is damaged」，且报错要**指明方向**（"upgrade the harness to open it"）。

**用法**：拒答码不能只有一个 `refused`。至少分：口径未定义（产品缺陷，可补）/
数据缺失（源缺陷）/ 条件不可求值（逻辑）/ 版本不兼容（工具链）。每类给方向性提示。

### 1.6 决定历史含义的配置必须持久化，且不进事件流

`agentPreset` 是 durable 的，理由：「**the preset decides the session's tools and prompt**:
a resume that restored a different composition would replay history the model can no longer act on」。

**用法**：`semantic_layer_version`（20 份口径定义的哈希）、`standards_pack_version`、
`extractor_version` 必须进 run header 而**不是**事件。理由完全同构：
换了口径定义再回放同一条证据链，结论的含义已经变了。

### 1.7 只在「状态确实前进了」时才允许重试

`RequestErrorAction = { kind: 'retry' } | undefined`，默认终态；
且只在「pruning or summarization **advances** the surface replacement generation」时才开重试轮。

**用法**：自我修复（口径不明 → 查准则 → 重试）只有在**证据集合确实新增条目**时
才允许开第二轮，否则第一次拒答即最终答案。免疫死循环与「重试掩盖问题」。

### 1.8 错误路由靠枚举码，永不靠模型文本

> Consumers route on the code, **never provider text**.
> An empty completion is a **retryable error, not a silent success**.

**用法**：拒答原因全部闭合枚举；LLM 生成的自然语言只能挂在码旁边当 `human_message`，
绝不参与分支。模型返回空内容 / 「我不确定」/ schema 不合格的 JSON —— 一律按 error 处理。

### 1.9 `kind`（谁产生）与 `form`（是什么）是独立两轴，且 form 决定必填字段

> The vocabulary is **SEMANTIC, never visual** … Colors, icons, ordering must not enter this union.
> Discriminated by `form` so **a producer cannot select a form without the fields needed to present it**.

这是证据链字段集设计的最佳范式，见 §3。

### 1.10 默认值必须是显式 resolve 步骤，不许藏在 `?? default`

> **Explicit > implicit at package boundaries**: defaulting is an explicit `resolve(request): Spec`
> step, **never a hidden `?? default` inside `run()`**.
> **Misconfiguration fails loud** at load … **never silently skip a missing referent**.

**这条是本报告对 finaudit 最重要的贡献。** 口径默认值悄悄生效，是「口径未定义时拒答」
这个主张最现实的失效方式。

**用法**：
```python
resolve_scope(question) -> ScopeSpec | Refusal   # 返回值本身是一条证据事件
compute_metric(scope: ScopeSpec, ...)            # 签名根本不接受 None
```
绕过闸门 ⇒ **类型错误**，不是运行时策略。语义层加载时若某定义不完整，**load 期就抛**。

### 1.11 包自有不变量注册表 +「没有不变量必须书面解释」

没有可检查项时必须导出空 installer，且注释以 `No runtime invariant:` 开头并
**具体解释为什么没得查**；由 `verify-package-invariants` 机械拒绝占位与未解释的空实现。
检查对象限定为「**authoritative event streams or mutable data**，不是服务或方法是否存在」。

**用法**：20 个指标每个注册一条运行时不变量（如「毛利率分母必须来自与分子同期同表的营业收入行」），
或写一条具名理由。脚本 gate 住。失败信息带 `metric_id` 归属。

### 1.12 事件生产/消费矩阵是**生成**的，不是手写的

由脚本从 TypeScript Program 解析产出，带 completeness guard。

**用法**：生成「哪个模块可以写入证据链的哪些字段」的矩阵，从源码解析，进 CI。
**这是证明「语义层闸门不可绕过」的最直接工程证据**——矩阵上若出现
LLM 编排层直接写 `metric_value` 的边，gate 就红。比任何文档主张都有说服力。

### 1.13 值得原样抄进类型注释的短契约

- `SessionLocation`：**"it is a location hint, not authorization or a freshness guarantee."**
- `SpillSource`：**"Not interpreted for access control; purely descriptive."**
- 取消原因：持久化只留粗粒度 `{kind:'aborted'}`，因为记录「谁请求的取消」需要
  **a separate durable event rather than overloading the terminal result**
  → 不要把「谁/为何拒答」塞进答案对象，拒答理由是独立事件
- **"Report orthogonal outcomes independently"** —— never nest one flag's report inside
  another's branch, or a caller reads a cut-short run as a clean success
- Branded IDs → Python 用 `NewType` 做 `MetricId` `ClauseId` `RunId` `DerivationId`，
  禁止裸 `str` 跨边界
- 验证边界只在 7 类：parser/config、queued、model/tool JSON、durable/file、worker、process、wire。
  其余同进程边界信任类型系统，**别每层都写防御性校验**
- 增量事件禁止靠「最近一次未完成的那个」隐式关联，必须自带稳定业务 id

## 3. 证据链字段集建议（U-01 的直接输入）

### 3.1 三层，不要压成扁平 dict

**A. Run Header**（在事件日志之外）
```
format_version / run_id / created_at / question_text_hash
filing_ref {issuer, filing_id, period, source_url, doc_sha256}
semantic_layer_version    ★ 它决定了历史的含义
standards_pack_version    ★
extractor_version         ★
parent_run / seed_length  追问链的血缘
```

**B. 事件信封**
```
seq(单调) / time / type(判别式) / data
source_event_seqs         溯源
op                        'append' | 'replace{start,end}' | 'shadow'
```

**C. 证据节点 —— 按 `source_kind` 判别的闭合联合（核心）**

| `source_kind` | 该 kind **必填** | 可作事实来源 |
|---|---|---|
| `statement_line` | `filing_ref, statement, table_id, page, row_label, col_period, raw_text, value, unit, currency, sign_convention` | ✅ |
| `metric_definition` | `metric_id, definition_version, formula, formula_hash, required_inputs[], scope_qualifiers{consolidation, period_type, restated}` | ✅ |
| `standard_clause` | `standard_body, standard_id, clause_id, clause_text_hash, effective_from, applicability_note` | ✅ |
| `computation` | `engine, engine_version, expression, input_refs[], result, result_hash, deterministic, rounding_policy` | ✅ |
| `document_span` | `doc_sha256, page_range, char_range, text_hash, spill_locator` | ✅ |
| `model_inference` | `provider, model, usage, prompt_section_names[], raw_output_ref, via_audited_path=true` | ❌ **仅解释，永不作事实来源** |
| `refusal` | 见 3.2 | — |

判别式联合的意义：**引用一条准则却拿不出 `clause_id`，在类型层面就构造不出来。**

### 3.2 拒答是第一类节点

```
refusal_code        闭合枚举，不可合并扩展
metric_id?          归属
attempted_inputs[]  失败尝试也必须持久化
missing             缺什么：哪个口径限定符 / 哪张表 / 哪条准则
remedy_direction    方向性提示
human_message       自然语言，不参与任何分支
```

建议码：`undefined_metric` `ambiguous_scope` `missing_line_item` `unit_mismatch`
`period_mismatch` `restatement_conflict` `standard_not_applicable`
`condition_unevaluable` `stale_source` `interrupted`(★ 仅恢复路径可发)

### 3.3 正交标志位并列，不嵌套

`refused` / `used_estimate` / `source_stale` / `content_reduced` / `partial_scope`

### 3.4 每个数字自带「实测 vs 估算」锚

`value_basis: 'reported' | 'derived' | 'estimated'` + `basis_log_revision`。
`estimated` 必须一眼可见，且「为什么没有实测锚」也要编码进去。

### 3.5 新鲜度用不透明 revision，**只比相等**

每份年报/每张表一个 `source_revision`（opaque token，callers compare it only for equality）。
不要试图比较大小或解析内容。

### 3.6 事务括号

`derivation/start` → 证据节点… → `derivation/result` → `derivation/end`。end 最后写。

## 4. 刻意不该借的

| 设计 | 为什么对通用 harness 合理 | 为什么对 finaudit 有害 |
|---|---|---|
| **waterfall + `next()` 委派** | 插件生态需要任意扩展点 | **闸门不能是 waterfall listener**：任一监听者短路即绕过，而是否调 `next()` 只能靠 review。闸门要放在调用签名上（§1.10） |
| **`SessionEventMap` declaration merging 无限扩展** | 插件无需改宿主包 | 证据 schema 必须**闭合**。harness 自己就区分：closed unions end in `assertNever` —— 证据链属于前者 |
| **`ignorable: true` 逃生舱** | 容纳纯装饰性事件 | 证据事件**一个都不许有**。审计产物里「读不懂但可跳过」不可接受 |
| **`SESSION_FORMAT_VERSION = 0`，无兼容承诺** | 预发布期无外部消费者 | 审计底稿要能几年后复核，必须有真正的迁移链。可借「拒绝优于误读」的态度，但要补迁移器 |
| **transport 层透明重试** | 对话产品要平滑 | 每次模型调用都必须是一条可见的编号尝试。harness 高层做对了（Agent-level recovery 开新的 durable numbered turn），但底层透明重试不要抄 |
| **compaction 用摘要替换原文进入模型可见面** | 对话只需保住可用性 | 摘要一旦进入可见面就会被引用成「证据」。**LLM 摘要永远不可作为可引用证据**，只能导航；引用必须回到原始定位（页/表/行） |
| **`whenIdle()` 无 per-message 结果** | 异步编排的诚实设计 | 审计需要「提问 ↔ 答案 ↔ 证据」的强因果绑定，不要用无法归因到单个请求的 API |
| **「插件里不许硬编码可调参数」** | 部署差异需要可调 | harness 自己留了例外：**Protocol constants, external specs, and security invariants stay fixed**。准则条文与指标口径公式属于此类，必须写死在受版本控制的定义文件里 |

## 5. 长文档（年报 100+ 页）

1. **确定性裁剪必须跑在 LLM 摘要之前，且要报账**。`toolResultPruner` 是 model-free 的，
   顺序是 prune → 重新测量 → **可能根本不需要摘要**。每次替换记
   `{originalSeq, replacementSeq, charsBefore, charsAfter}`。
   裁剪按 **Unicode code point** 计，不得切断代理对（中文同理防切断组合字符）。
2. **替换节点必须引用被遮蔽的原节点**，并单独发一条「影子计价」事件，
   使纯消费者能无状态做减法。
3. **「位置跨度」不是「seq 区间」**：多轮替换后 `start` 可能**大于** `end`；
   权威的是显式的 `shadowed_seqs` 列表。这是个很容易踩的坑。
4. **边界必须成对平衡**：裁剪不得切开「定位表格 → 取数 → 计算」三元组。
   提供 `derivation_balanced_before/after` 判定。允许在同一长推导内**已闭合的子步骤**上裁剪。
5. **两个触发器**：`pressure`（预估，跑在组装前）保守；`context-overflow`（已确认，
   跑在失败 step 关闭后）才激进。不要合并成一个。
6. **诚实地返回「做不到」**：单张超大合并报表本身就超上下文时，
   正确答案是拒答（`source_unit_too_large`），不是硬切。
7. **超长原文用 spill 不要截断**：内容 verbatim 落盘，证据节点只带
   `spill_locator + text_hash + 字节数`。**这比「截断后放进上下文」在审计上强一个量级**。
8. **冷读阶梯**：证据链概览用「检查点行 + 尾部重放」，不要每次全量回放。
   检查点强制落点选在 `derivation/end` 与 detach。
