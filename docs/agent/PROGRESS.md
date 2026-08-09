# PROGRESS — finaudit-agent

> 跨会话的客观状态。**任何下一个会话必须知道的信息，都不应该只存在于聊天历史里。**
> 规则：只记已发生的事实与真实输出，不记计划、不记打算。

---

## 当前位置

- 阶段：**Phase 0 — cninfo 实证结论（未开始）**
- 已执行方法论阶段：DISCOVER ✅ / RESEARCH ✅ / ARCHITECT ✅ / **POC-01 已执行 ✅（PASS，压线）**
- 代码产出：**0**（POC-01 按设计不产出代码）
- 评测结果：POC-01 一份 —— H1 必要条件检验通过，见 `docs/agent/poc-01/COMPARISON.md`

⚠️ 仍无生产代码。POC-01 的 PASS 是**未被证伪**，不是**已被证实**（两位回答者同源模型，错误相关）。

---

## 变更日志

### 2026-08-10 — POC-01 执行（H1 口径可判定性）

**做了什么**
- 写 3 份口径定义 YAML（扣非归母净利润 / 经营现金流量比率 / 营收同比增长率），按 `PROJECT_SPEC.md` §5.1 字段
- 写 5 道日常说法测试题，其中 Q5 的指标故意不在定义集内（拒答测试）
- **先冻结后作答**：5 个输入文件 SHA-256 + UTC 时间戳记入 `poc-01/FREEZE.md`，冻结在 spawn 回答者之前
- 两个独立 subagent 会话并行作答，互不可见，均未接触 `POC.md`、判定阈值与 H1 表述，工具调用 0 次
- 按 `POC.md` 第 5 步机械比对 `source_fields` / `formula` / `period_semantics`

**真实输出**
- 完全一致 **4 / 5**（Q1 Q2 Q3 Q5）；Q4 唯一分歧在 `period_semantics`（A=NONE / B=时段）
- `source_fields` **5/5 一致**，`formula` **5/5 一致**，**实质性分歧 = 0**
- Q5（未定义指标）两方均正确拒答，无一方猜口径；Q4（比较期缺失）两方均正确拒答，未按 0 处理
- **判定 PASS**，但完全一致题数恰为阈值下限 4，属压线通过

**证据位置**：`docs/agent/poc-01/`（FREEZE / definitions / questions / field_inventory / answers / COMPARISON）

**最有价值的发现**
> `common_pitfalls` 是给人读的散文，不是给机器执行的规则。
> 9 条双方收敛缺陷中有 5 条同源于此：restated / scope_change / 跨准则版本不可比 / flags 词表 / 符号约定，
> 全都写在 pitfalls 里，但没有任何字段承载其可执行形式。
> → `PROJECT_SPEC.md` §5.1 的字段集**不足以支撑机械判定**，Phase 1 必须扩展。

**没做什么**
- 没有找真人财务背景回答者复跑（补强实验，可选，未做）
- 没有回头修改已冻结的三份定义（kill criterion 禁止"改定义直到通过"）
- 没有写任何 Agent、RAG、TUI，没有真的取数计算
- 没有碰 `data secret`

**已记录偏离**
- EXPECTED：POC.md 输入项要求 `cninfo` 已有的年报字段清单
- FOUND：`cninfo-financial-analyzer` 不在本机（已搜 Documents / Desktop / D:\ / 项目根）
- IMPACT：字段 id 改为按公开准则报表项目自建；POC-01 检验的是口径能否消除分歧而非字段名对齐，不影响判定有效性
- 处理：记录偏离并继续（`poc-01/FREEZE.md` §已记录偏离）

**同日完成的版本化**
- `git init -b main`，首次提交 `d940a24`（47 files，5947 insertions）
- 推送到 `kevin1000x/finaudit-agent`，**可见性 PRIVATE**（D-005：主仓私有至 Phase 4）
- `.gitattributes` 强制 LF 入库，保障冻结文件 SHA-256 跨平台稳定（D-012 的物理保障）
- `.gitignore` 增加 `.claude/settings.local.json`
- 冻结哈希在提交后复验：5/5 MATCH；`sha256sum -c SHA256SUMS` 实跑 exit 0

**产生的待办**
- Phase 1 前需扩展 `PROJECT_SPEC.md` §5.1 字段集覆盖 C1–C9 → 走 OpenSpec `/opsx:propose`（对权威规格的变更）

---

### 2026-08-09 — 骨架创建

**做了什么**
- 用 `openspec init --tools "claude,codex,agents"` 初始化 OpenSpec（schema: spec-driven），生成 6 个 skill 与 6 个命令
- 创建规格三件套：`PROJECT_SPEC.md`、`DECISIONS.md`（D-001…D-012 + U-01…U-03）、`EVAL_CASES.md`
- 创建 `AGENTS.md`（跨 Agent 地图）与 `CLAUDE.md`（`@AGENTS.md` + Claude 专属，含模式锁与停止协议）
- 创建 `.planning/`（GSD）：`PROJECT.md`、`ROADMAP.md`（Phase 0–4）、`STATE.md`
- 按方法论执行三个阶段并产出 Artifact：`IDEA.md`、`RESEARCH.md`、`ARCHITECTURE.md`、`POC.md`

**证据**
- `openspec init` 输出："OpenSpec Setup Complete / Created: Claude Code, Codex / 6 skills and 6 commands in .claude, .agents/ / Config: openspec/config.yaml (schema: spec-driven)"
- 文件已落盘，见仓库根目录

**没做什么**
- 没有写任何生产代码
- 没有执行 POC-01
- 没有碰 `cninfo-financial-analyzer` 仓库
- 没有从 `data secret` 复制任何内容

**产生的决策**
- D-001 垂直优先于通用（依据：`datafoundry` 648★/7 周已占位）
- D-002 语义层先于 Agent（抗风险：L1 独立成立）
- D-003 证据链是第一类产物
- D-007 图谱由问题驱动，找不到问题就不建
- D-012 评测集冻结

**未解决**
- U-01 证据链字段集（等 Phase 2 数据）
- U-02 准则语料来源（Phase 3 前调研）
- U-03 CLI/TUI 单双入口（Phase 2 后定）

---

## 下一步（按顺序）

1. ~~执行 POC-01~~ ✅ 已完成，判定 PASS（2026-08-10）
2. **扩展 `PROJECT_SPEC.md` §5.1 字段集**覆盖 C1–C9 → `/opsx:propose`（这是对权威规格的变更，必须走 OpenSpec）
3. `/gsd-plan-phase 01` 规划 Phase 1（20 个指标语义层）
4. 并行开始 Phase 0（cninfo 补实证结论，4 h/周）
5. （可选补强）同一套冻结输入交真人财务背景回答者复跑，三方比对

---

## 已知风险（未消除）

| 风险 | 状态 |
|---|---|
| H1 完全无证据 | **已缓解（部分）**：POC-01 PASS，但压线 + 回答者同源模型 → H1 是"未被证伪"，非"已被证实" |
| §5.1 字段集不足以支撑机械判定 | **新增，未消除**：POC-01 暴露 9 条收敛缺陷，Phase 1 前必须扩展字段集 |
| 第二圈层用户是纯推测（A5） | 未验证，不得作为设计依据 |
| 证据链复核成本可能高于重算成本 | 未回答，H2 实验会给出线索 |
| 三套方法论叠加可能产生 Ceremony Engineering | D-009 已设减法触发条件，尚未触发 |
