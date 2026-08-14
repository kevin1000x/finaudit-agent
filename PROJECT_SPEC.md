# finaudit-agent — 项目规格

## 1. 文档状态

- 状态：**草案**（Phase 0 尚未产出证据，本规格未冻结）
- 范围：Phase 0 – Phase 4
- 当前阶段：Phase 0 — cninfo 实证结论
- 主决策：垂直领域 + 证据链，而非通用 Data Agent（D-001）

本文件说明**要证明什么**，不是实现计划。实现计划在 `.planning/phases/`。

## 2. 问题陈述

财务与审计场景里，AI 给出的分析结论没人敢直接用。不是因为答案更容易错，而是因为**错了查不出来在哪一步错**。

具体的失效点（一线从业者的公开判断，非本项目原创）：

> 企业里真正让人头疼的往往不是"能不能生成 SQL"，而是：**指标口径是不是对的？表和字段有没有选错？查询会不会越权？结果能不能复盘？模型到底看到了什么上下文？一次分析过程里调用了哪些工具、执行了哪些 SQL、产出了哪些证据？**这些问题不解决，Data Agent 很容易停留在 demo 阶段。
> —— 知乎《别再把 Data Agent 做成 NL2SQL》，2026

本项目只解决其中财务领域的那一部分，不解决通用数据治理。

### 2.1 术语

| 术语 | 含义 |
|---|---|
| **语义层（Semantic Layer）** | 财务指标的机器可读定义：字段映射、计算公式、准则依据、常见陷阱。可版本化。 |
| **证据链（Evidence Chain）** | 一次回答附带的可独立复核记录：数据来源、口径版本、检索命中、执行内容、结果哈希、耗时与成本。 |
| **口径（Metric Definition）** | 一个指标"怎么算"的完整规定，包括分子分母、时点/时段、是否含非经常性损益等。 |
| **复核（Review）** | 人类在不看 Agent 解释的前提下，仅凭证据链独立判断答案对错的过程。 |

## 3. 核心假设

三条假设按依赖顺序排列，前一条不成立时后一条无意义。

### H1 — 口径可判定性

> 财务指标的口径能否被固化成机器可读的定义，使 Agent 的取数结论可以被机械判定对错，而不是靠人"看着像"？

这是本项目的地基。H1 不成立，整个方向作废。

### H2 — 证据链充分性

> 一条自动生成的分析结论，附带的证据链能否让一位有审计背景的人在 **5 分钟内**独立判断它对不对，且判断结果与标准答案一致？

H2 是产品价值所在。答案对但证据链不可复核，等于没解决原问题。

### H3 — 图谱必要性

> 是否存在一类财务问题，纯向量 RAG 答不了而知识图谱能答？

H3 是**证伪导向**的：如果找不到这样的问题，就不建图谱（D-007）。绝不为了技术展示而建图。

## 4. 边界

### 数据边界（不可协商）

- 仅使用**公开数据**：巨潮资讯网公开披露的年报与公告、AKShare 公开财务指标、公开发布的会计与审计准则文本。
- **禁止**任何雇主内部数据、实习期间接触的数据、客户数据进入本仓库，包括脱敏后的、聚合后的、改写后的。
- **禁止**将本项目与任何雇主内部系统对接。

### 与 `data secret` 的边界

- 可复用**机制思想**：SHA-256 双校验、fail-closed、评测器与标准答案隔离、append-only 证据。
- **不复用**：代码、评测语料、Trial 数据、任何 Iteration 结论。
- 两个项目的仓库、语料、结论完全隔离。`data secret` 的 INCONCLUSIVE 状态与本项目无关，本项目的任何结果也不能反向用于该项目。

### 外部输出边界

- 主仓库暂不开源（D-005）。
- 可开源的姊妹产物：**语义层定义文件** + **评测问题集**，两者均不含实现代码、不含未公开结论。

## 5. 架构

五层。每一层单独可讲、单独有价值，不依赖上层完成。

```text
L4  TUI 交互层        问答界面 · 证据链侧栏 · 逐步复核视图
L3  可信执行层        pre-hook 校验 / post-hook trace / eval
L2  知识层            准则 RAG（引用可追溯） + 关联方图谱（条件性）
L1  语义层            指标口径定义（YAML，可版本化）
L0  数据层            年报下载 · PDF 解析 · 情感词典 · Fog · TNI   [cninfo 已有]
```

### 5.1 L1 语义层

> 本节的**行为契约**是 `openspec/specs/semantic-layer/metric-definition/spec.md` 的 9 条 Requirement。
> 本节是人读的字段说明，二者一一对应、不重复权威（D-009）。冲突时以本文件为准。
>
> 字段集于 2026-08-10 由 OpenSpec 变更 `extend-metric-definition-schema` 扩展。
> 扩展依据：POC-01 暴露的 9 条双方收敛缺陷（`docs/agent/poc-01/COMPARISON.md` §5）。
> **旧字段集撑不住机械判定**，根因是 `common_pitfalls` 是散文而非可执行规则。

每个指标一个 YAML 文件，字段集如下：

```yaml
metric_id: net_profit_attributable_excl_nonrecurring
display_name: 扣除非经常性损益后归属于母公司股东的净利润
aliases: [扣非归母净利润, 扣非净利润]
version: 2                    # 见下方「版本号语义」

grain:                        # 数据粒度 —— 缺此项公式无法定位到唯一一行
  entity: stock_code          # 实体维度
  period: fiscal_year         # 期间维度
  period_type: annual         # 报告期类型：annual / semi_annual / quarterly

source_fields:
  - id: is.net_profit_attributable_to_parent
    statement: 合并利润表
    line_item: 归属于母公司所有者（股东）的净利润
    sign_convention: 收益记正_损失记负   # 参与加减的字段必填
    missing_representation: null        # 「缺失」如何表达，须与「取值为零」可区分
  - id: notes.nonrecurring_pl_net_attributable_to_parent
    statement: 财务报表附注
    line_item: 归属于母公司股东的非经常性损益净额（已扣所得税及少数股东损益影响）
    sign_convention: 收益记正_损失记负
    missing_representation: null

formula: >
  is.net_profit_attributable_to_parent
  - notes.nonrecurring_pl_net_attributable_to_parent

period_semantics: 时段        # 时点 / 时段 / 混合

derivation:                   # 必填，二选一，不得留空
  allow_from_components: false
  note: 禁止由「税前合计 − 所得税影响 − 少数股东部分」倒推归母净额

standard_basis:               # 结构化条目，每条须含名称 + 条号 + 版本
  - name: 公开发行证券的公司信息披露解释性公告第 1 号——非经常性损益
    issuer: 中国证监会
    article: 全文
    version: "2023"
  - name: 企业会计准则第 33 号——合并财务报表
    issuer: 财政部
    article: 第五章
    version: "2014"

flags:                        # 只能引用全局词表，不得自造
  - name: restated
    trigger: notes.restatement_flag == true
  - name: basis_version_mismatch
    trigger: standard_basis.version != comparison_period.standard_basis.version

undefined_conditions:         # 每条须可对给定数据求值；命中即拒答
  - expr: is_missing(notes.nonrecurring_pl_net_attributable_to_parent)
    reason: 附注未披露归母非经常性损益净额

common_pitfalls:              # 每条须满足元规则，见下
  - text: 被减项必须是归母净利润，不是利润表底部的净利润
    enforced_by: source_fields.id            # 有可求值规则承载
  - text: 非经常性损益项目清单随证监会公告版本变化
    enforced_by: flags.basis_version_mismatch
  - text: 该指标在亏损年度的经济含义需结合行业判断
    advisory_only: true                      # 无机械后果，显式标注
```

#### 元规则（本次扩展的核心，BREAKING）

**每一条 `common_pitfalls` 必须要么由一条可求值规则承载（`enforced_by` 指向某个 flag 触发条件、
`undefined_conditions` 条目或字段约束），要么显式标注 `advisory_only: true`。**

既无 `enforced_by` 又无 `advisory_only` 的陷阱条目 → 该定义不合规。

这条规则防止「散文冒充规则」重新长回来。POC-01 的 9 条收敛缺陷中有 5 条同源于此。

监控指标：Phase 1 结束时统计 `advisory_only` 占比。**> 50% 视为元规则失效**，须重新设计而非接受现状。

#### 版本号语义

版本号在本项目里的**唯一用途**是判定「两期结论能不能比」。因此它只对影响可比性的改动敏感：

- **必须 bump**：`grain` / `source_fields` / `formula` / `sign_convention` / `derivation` /
  flag 触发条件 / `undefined_conditions` 的任何改动
- **不 bump**：`advisory_only` 陷阱文本、`display_name`、`aliases` 的措辞调整

版本号变更即视为口径变更，**历史结论不可跨版本比较**，证据链须携带 `metric_id` 与版本号。

#### 全局 flag 词表

flag 的价值在于跨指标一致，因此**词表全局唯一，指标只能引用不能自造**。
词表位置在 Phase 1 有 5 个以上真实 flag 后确定（候选：本文件内 / 独立文件）。
新增 flag 是对词表的变更，走独立评审，不由单个指标定义顺手引入。

#### 与 POC-01 定义的关系

POC-01 的 3 份定义停留在 `version: 1`，**不迁移、不改写**，作为旧 schema 的历史样本保留
（`POC.md` 的 kill criterion 禁止「改定义直到通过」；`SHA256SUMS` 冻结校验须始终通过）。

新 schema 下的定义**从 `version: 2` 起**。红测已确认：v1 与 v2 之间没有任何一条 Requirement
是共同满足的（27 格矩阵 `PASS` 为 0，见 `openspec/changes/extend-metric-definition-schema/conformance-checklist.md`），
因此跨版本比较在技术上也确实无意义。

### 5.2 L3 可信执行层

| Hook 点 | 职责 |
|---|---|
| `pre_execute` | 校验所引用的指标口径存在且版本匹配；校验只访问授权数据源；对生成代码做 AST 静态检查 |
| `post_execute` | 写入 append-only trace：工具调用、执行内容、结果哈希、耗时、token 成本 |
| `on_failure` | 整轮标记为不可信，**禁止静默重试**；失败必须归因到具体层 |

Hook 是策略（policy），不是建议（preference）。Prompt 里写"请校验口径"不算实现了这一层。

## 6. 功能需求

- FR-01：从指标名称解析出唯一的口径定义与版本。
- FR-02：口径定义缺失或版本冲突时**拒绝作答**，而不是猜一个。
- FR-03：每次回答产出结构化证据链，字段固定。
- FR-04：准则检索结果必须携带可定位的引用（准则名 + 条号）。
- FR-05：执行前静态校验，执行后哈希留痕。
- FR-06：失败必须归因到检索层 / 口径层 / 计算层 / 表达层之一（可多标签）。
- FR-07：提供评测入口，对 held-out 问题集批量跑分并输出分层失败报告。

## 7. 非功能需求

- NFR-01：单人可实现。不设每周小时上限；实际投入以 `docs/agent/PROGRESS.md` changelog 记录（D-008，2026-08-10 修订）。
- NFR-02：不引入 SaaS、数据库服务、部署基础设施、生产沙箱。
- NFR-03：不训练、不微调模型。
- NFR-04：不做多数据源适配，Phase 0–4 只支持已有的 cninfo 数据。
- NFR-05：无网络时可用本地已下载语料完成评测。

## 8. 明确不做（Non-goals）

- ❌ 通用 Data Agent / ChatBI / 多数据源接入
- ❌ NL2SQL 通用引擎
- ❌ 企业数据治理、权限系统、SSO
- ❌ 模型训练、微调、蒸馏
- ❌ 生产环境安全保证（静态校验不是沙箱）
- ❌ 实时数据、流式计算
- ❌ 多租户、协作、SaaS 化
- ❌ 为了展示而建的知识图谱（见 H3 / D-007）

## 9. 验收标准

Phase 0–1 的阻塞性标准：

- **AC-01**：语义层覆盖至少 20 个核心财务指标，每个满足 §5.1 的完整字段集——
  `grain` / `source_fields`（含 `sign_convention` 与 `missing_representation`）/ `formula` /
  `period_semantics` / `derivation` / 结构化 `standard_basis`（名称 + 条号 + 版本）/
  `flags`（引用全局词表，带可求值触发条件）/ `undefined_conditions`（可求值）/
  ≥3 条 `common_pitfalls`，且**每条陷阱满足元规则**（有 `enforced_by` 或标 `advisory_only`）。
- **AC-02**：口径定义缺失时系统拒绝作答，且拒答理由可机读。
- **AC-03**：`cninfo` 产出至少一条可复现的实证结论，含数据范围、方法、显著性、局限。
- **AC-04**：评测问题集 ≥ 20 题，每题有标准答案与判定规则，且**在看到模型输出前冻结**。

Phase 2–4 的阻塞性标准：

- **AC-05**：每条回答产出完整证据链，字段齐全率 100%。
- **AC-06**：一位有审计背景的复核者仅凭证据链，在 5 分钟内独立判断对错，与标准答案一致率 ≥ 80%（H2 判定门）。
- **AC-07**：准则检索的每条引用可定位到具体条号，抽检 20 条准确率 ≥ 90%。
- **AC-08**：失败归因覆盖率 100%（每个失败都落到至少一层，不允许"未知")。
- **AC-09**：执行前静态校验拒绝全部已知危险样本。
- **AC-10**：仓库内零非公开数据（自动扫描）。

## 10. 停止条件

- **H1 不成立**：20 个指标里超过 5 个无法给出无歧义的机器可读口径 → 停止，重新定义问题。
- **H2 不成立**：复核者一致率 < 60% → 证据链设计失败，回到 ARCHITECT 阶段，不进入 L2。
- **H3 不成立**：找不到"非图不可"的问题 → **不建图谱**，这不是失败，是省下的工作量。
- **越界**：任何非公开数据进入仓库 → 立即停止，清理并复盘。
- **停滞**：连续两周 `PROGRESS.md` 无新 changelog 条目 → 说明范围估计错误，砍阶段目标。
  判据是**产出记录为空**，不是小时数超支（D-008 已取消时间预算上限）。
- **竞品覆盖**：若出现一个开源项目已经把"财务垂直 + 证据链"做完且质量更高 → 停止自建，转为使用并贡献。

## 11. 完成定义

任何阶段声明完成，必须提供：

```text
验收标准 → 验证方法 → 实际命令 → 真实输出 → 证据位置 → PASS / FAIL / UNVERIFIED
```

不接受"应该可以了"。没有证据的项目一律记为 `UNVERIFIED`，不记为 PASS。

## 12. 证据产物

- 语义层定义文件与其版本历史
- 评测问题集（冻结时间戳 + 哈希）
- 每次评测的分层失败报告
- 证据链样本（脱敏）
- 阶段 VERIFICATION.md
