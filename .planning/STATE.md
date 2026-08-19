---
gsd_state_version: 1.0
milestone: v0.1
milestone_name: 骨架与 cninfo 延伸
current_phase: "01.5"
current_phase_name: 数据接入层
status: phase-1-complete-phase-1.5-not-planned
stopped_at: Phase 1 已收口（8/8 计划、五条 SC 全 VERIFIED、H1 严格读法未触发停止条件）；Phase 1.5 尚无 PLAN，待 /gsd-plan-phase；Phase 0 尚未开始
last_updated: "2026-08-16T13:10:00Z"
last_activity: 2026-08-16
last_activity_desc: A-3 裁决落地为 D-014（换 pdfplumber，禁 AGPL）+ 许可证禁列机器化；接入 LLM 对照臂并跑完 pro/flash 两个模型臂，Q-C1-001 静默口径错误在两模型上逐字复现；wave 5 收口，VERIFICATION.md 落地含九段逐字输出，H1 由操作者裁决取严格读法
progress:
  total_phases: 6
  completed_phases: 1
  total_plans: 8
  completed_plans: 8
  percent: 17
---

# 项目状态

## 项目引用

见 `.planning/PROJECT.md`。

**核心价值**：让 AI 给出的财务分析结论可以被人独立复核。
**当前焦点**：**Phase 1.5 — 数据接入层**（PDF 抽取器 + 数值执行层）
**权威文档**：`PROJECT_SPEC.md`、`DECISIONS.md`、`EVAL_CASES.md`。`.planning/` 只汇总与路由，不覆盖它们。

## 当前位置

- 阶段：**Phase 1 已完成**（2026-08-16 收口）；**Phase 1.5 待规划**，尚无 PLAN
- 计划：Phase 1 的 8 份 PLAN 全部执行完毕（5 个 wave）
- 下一个动作：`/gsd-plan-phase 01.5`

**Phase 1 收口证据**：`docs/agent/VERIFICATION.md` §Phase 1，
14 行验收矩阵 + 三项阶段末判定 + 附录 A 九段逐字命令输出（含退出码，可原样重跑）。
Task 3 人工检查点由操作者指定复核 SC-2 / SC-3 / SC-4 三条，**复跑全部一致**。

**唯一未完成的检查点子步骤**：Task 3 第 2 步「只读 YAML 判断定义是否对人可读」
——那是人的判断，执行者代答无效。已记为台账 **N-20**，Phase 2 前必须补做。

## 已执行的方法论阶段

| 阶段 | 状态 | Artifact |
|---|---|---|
| DISCOVER | ✅ 完成 | `docs/agent/IDEA.md` |
| RESEARCH | ✅ 完成 | `docs/agent/RESEARCH.md`、`references/`（6 份，含 3 份 subagent 深读 + 2 份续读） |
| ARCHITECT | ✅ 完成（Phase 2 架构待补） | `docs/agent/ARCHITECTURE.md` |
| POC | ✅ POC-01 已执行（PASS，压线） | `docs/agent/POC.md`、`docs/agent/poc-01/` |
| PLAN | ✅ Phase 1（8 份）；Phase 1.5 未做 | `.planning/phases/01-semantic-layer/` |
| IMPLEMENT | ✅ Phase 1 全部落地 | `src/semantic_layer/`、`metrics/`、`eval/` |
| VERIFY | ✅ Phase 1 已收口 | `docs/agent/VERIFICATION.md` §Phase 1 |
| REVIEW | ⬜ 未开始 | — |

POC-02（图谱必要性 H3）仍未执行，前置条件是 Phase 2 的 H2 判定门通过。

## 当前规模

| | |
|---|---|
| 指标定义 | **20 / 20** 合规，`advisory_only` 19.0%，未分类 0 |
| 测试 | **350 passed** |
| 提交 | 已推送至 `origin/main` |
| 评测集 | frozen-01 冻结 @ `2026-08-15T14:47:51Z`，21 文件哈希 |
| 系统臂 | C2 拒答 **4/4**，门成立；C1/C3/C4/C5 共 16 题 `NOT_RUN`（能力缺口） |
| 对照臂 | 裸 LLM 两个模型臂（`deepseek-v4-pro` / `v4-flash`），报告在 `eval/runs/baseline/`（gitignored） |
| OpenSpec | 3 个变更已归档，`specs/` 9 条 Requirement |
| 决策 | D-001…**D-014** |

## 累积上下文

### 关键决策

- D-001 不做通用 Data Agent
- D-002 语义层先于 Agent —— 抗风险设计，L1 单独成立
- D-003 证据链是第一类产物；给不出证据链 = 失败
- D-004 与 `data secret` 机制复用、资产隔离，**且无时序依赖**
- D-005 主仓私有至 Phase 4
- D-006 界面是交付形式不是卖点（2026-08-15 交付形态改为 **Web 为主**）
- D-008 **不设时间预算上限**，投入以 changelog 记录
- D-010 仅公开数据，不可协商
- D-012 评测集在看到模型输出前冻结
- D-013 财务数值以年报 PDF 原文为准，二手源只作对照
- **D-014（2026-08-16）PDF 抽取器不得链接 AGPL 组件，主库 pdfplumber**
  —— 已由 `scripts/verify_deps.py` 的许可证禁列机器化，不靠人记

### 待解决问题

完整台账在 `docs/agent/OPEN-ITEMS.md`（A 阻塞 / B 已决待排期 / C 规格 U-0x / D 新增 / E 已关闭）。
**A 区目前无红色阻塞项**（A-3 已于 2026-08-16 裁决关闭，A-5 已完成）。

此处只列跨阶段的三条：

- U-01 证据链字段集未定，等 Phase 2 复核实验数据。**已有三条具体输入**（台账 N-16）
- U-02 准则语料获取方式未定，Phase 3 前专项调研
- U-03 内核与壳的边界画在哪，等 Phase 2 的 ARCHITECTURE.md，**不得在 Phase 1.5 提前拍板**

### 最危险的未验证假设

**H1 口径可判定性 —— 两次压线通过，仍读作「未被证伪」。**

证据现在有两处，**两处都停在阈值边缘**：

1. POC-01 判定 PASS，但完全一致题数恰为阈值下限 4（再少一题即 INCONCLUSIVE），
   且两位回答者是同一基座模型的独立会话，错误相关；
2. Phase 1 的 §10 停止条件判定：严格读法计 **5**，判据是「> 5 触发」——**再多一份即触发**；
   而同样合理的宽松读法计 7，**已越阈值**。操作者 2026-08-16 裁决取严格读法。

**结论只能读作 H1 未被证伪，不是已被证实。** 任何转述都必须带上这两处压线。

**反向的新证据（2026-08-16，对照臂）**：H1 关心的是「口径能否被写成无歧义定义」，
而对照臂给出了「不写会怎样」的实例——两个模型在 Q-C1-001 上**错得逐字相同**
（都取含少数股东损益的净利润，答 0.124 而正解 0.112，且都不拒答）。
这不证明 H1 成立，但证明**它想解决的问题真实存在**。

### 已知的证据缺口（不粉饰）

- `01-01 / 01-04 / 01-05 / 01-07` **无 SUMMARY 文件**，这四个计划的执行过程无书面记录，
  只能核对产物，核对不了过程
- 元规则 19.0% 只说明「大部分陷阱写成了可求值规则」，**不说明规则会正确触发**
  —— 要到 Phase 1.5 接上真实字段才验得了
- 台账 **N-20**：无人只读 YAML 验证过定义对人可读，D-003 的可复核性前提在这一维度上零证据

## 下一步

1. **`/gsd-plan-phase 01.5`** —— Phase 1.5 六条成功标准已在 ROADMAP，
   方法记在 `references/cninfo.md` 与两份 cninfo 深读报告
   （下载三步链路、坐标重组、四个坑）。**注意 9/12 是 fitz 跑的，换 pdfplumber 后未实测**（A-4）
2. **修 A-2**：`interest_bearing_debt_ratio` 会拒答一家实际无有息负债的公司（茅台实证）。
   修在抽取层区分「行在格子空 = 0」与「整行不存在 = 缺失」，**定义侧不动**
3. **Phase 1.5 补一条勾稽校验成功标准**（台账 N-13）——cninfo 完全没有这层，要从零建
4. （可并行）**Phase 0** —— 审计报告正文就在年报 PDF 里、紧邻合并资产负债表，
   与 Phase 1.5 共用同一条下载定位链路。**但 Fog 实现要重写**（cninfo 的 `common_vocab`
   缺失导致静默降级、`\n` 作分句符）
5. **Phase 2 架构预备**：闸门放进**调用签名**（`resolve_scope() -> ScopeSpec | Refusal`），
   不用 waterfall listener 也不用「可选工具」；证据日志的 fail-closed 放在**读入边界**（台账 N-14）

推荐入口：`/gsd-plan-phase 01.5`
