---
gsd_state_version: 1.0
milestone: v0.1
milestone_name: 骨架与 cninfo 延伸
current_phase: 01
current_phase_name: 语义层 semantic-layer
status: phase-1-wave-3-done-blocked-on-freeze-checkpoint
stopped_at: Phase 1 wave 1-3 完成（20/20 定义，310 tests）；wave 4 卡在 frozen-01 冻结检查点（one-way，待操作者确认）；Phase 0 尚未开始
last_updated: "2026-08-15T14:30:00Z"
last_activity: 2026-08-15
last_activity_desc: wave 3 落地 19 份指标定义（20/20 全部合规，advisory_only 19.0%）；关闭 OQ-01/02/03/04；补 kpi 命名空间与 derivation 承载体；评测集 20 题与运行器就位待冻结；实测跑通巨潮年报下载与 PDF 坐标取数
progress:
  total_phases: 5
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# 项目状态

## 项目引用

见 `.planning/PROJECT.md`。

**核心价值**：让 AI 给出的财务分析结论可以被人独立复核。
**当前焦点**：Phase 0 — cninfo 实证结论
**权威文档**：`PROJECT_SPEC.md`、`DECISIONS.md`、`EVAL_CASES.md`。`.planning/` 只汇总与路由，不覆盖它们。

## 当前位置

- 阶段：Phase 0（cninfo 实证结论）— **尚未开始**
- 计划：Phase 1 有 8 份 PLAN（5 个 wave），已执行 wave 1 的 tracer；Phase 0 计划尚未撰写
- 状态：POC-01 已执行（PASS），等待 `/gsd-plan-phase` 生成阶段计划

**已有第一份生产代码**（`src/semantic_layer/`，40 tests passed）。POC-01 本身按设计不产出代码。
不要把 POC-01 的 PASS 当作 H1 已被证实——两位回答者是同源模型，且完全一致题数恰为阈值下限。

## 已执行的方法论阶段

| 阶段 | 状态 | Artifact |
|---|---|---|
| DISCOVER | ✅ 完成 | `docs/agent/IDEA.md` |
| RESEARCH | ✅ 完成（复用 2026-08-09 多渠道调研） | `docs/agent/RESEARCH.md` |
| ARCHITECT | ✅ 完成 | `docs/agent/ARCHITECTURE.md` |
| POC | ✅ POC-01 **已执行**（PASS） | `docs/agent/POC.md` §执行记录、`docs/agent/poc-01/` |
| PLAN | ⬜ 未开始 | — |
| IMPLEMENT | ⬜ 未开始 | — |
| VERIFY | ⬜ 未开始 | — |
| REVIEW | ⬜ 未开始 | — |

POC-01 于 2026-08-10 执行完毕，判定 **PASS**（4/5 完全一致，压线；取数字段与公式结构 5/5 一致）。
POC-02（图谱必要性 H3）仍未执行，前置条件是 Phase 2 的 H2 判定门通过。

## 累积上下文

### 关键决策

- D-001 不做通用 Data Agent（竞品 `datafoundry` 7 周 648★ 已占位）
- D-002 语义层先于 Agent —— 抗风险设计，L1 单独成立
- D-003 证据链是第一类产物；给不出证据链 = 失败
- D-004 与 `data secret` 机制复用、资产隔离，**且无时序依赖**——本项目不以它的任何进度或结论为前置，它永远阻塞也不影响推进到 Phase 4（2026-08-10 补充）
- D-008 **不设时间预算上限**，投入以 changelog 记录（2026-08-10 修订，原 ≤8h/周 已取消）
- D-010 仅公开数据，不可协商
- D-012 评测集在看到模型输出前冻结

### 待解决问题

- U-01 证据链字段集未定，等 Phase 2 复核实验数据
- U-02 准则语料获取方式未定，Phase 3 前专项调研
- U-03 CLI 与 TUI 是否双入口，Phase 2 后再定

### 最危险的未验证假设

**H1 口径可判定性 —— 部分缓解，未证实。** POC-01 判定 PASS（证据：`docs/agent/poc-01/`）。
但两点必须随结论一起传递：① 完全一致题数恰为阈值下限 4，压线通过；
② 两位回答者是同一基座模型的独立会话，错误相关，支持强度弱于两位真人。
结论应读作 **H1 未被证伪**，不是 H1 已被证实。

**新增风险：`PROJECT_SPEC.md` §5.1 字段集不足以支撑机械判定。**
POC-01 暴露 9 条双方收敛缺陷，根因是 `common_pitfalls` 是散文而非可执行规则。Phase 1 前必须扩展字段集。

## 下一步

1. ~~执行 POC-01~~ ✅ PASS（2026-08-10）
2. **扩展 §5.1 字段集**覆盖 C1–C9（见 `docs/agent/poc-01/COMPARISON.md` §5）→ `/opsx:propose`
3. `/gsd-plan-phase 01` 规划 Phase 1（20 个指标语义层）
4. 并行开始 Phase 0（cninfo 实证结论）

推荐入口：`/opsx:propose`（先改规格），再 `/gsd-plan-phase 01`
