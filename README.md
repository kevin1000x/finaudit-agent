# finaudit-agent

**可审计的财务分析 Agent。** 回答财务问题时同时产出可独立复核的证据链：用了哪张表、哪个指标口径（含版本）、依据哪条准则、执行了什么、结果哈希是什么。

判定标准：**一位有审计背景的人，只看证据链、不看 AI 的解释，能在 5 分钟内独立判断答案对不对。**

> ⚠️ **当前状态：骨架阶段 + POC-01 已执行，零生产代码。** 见 `.planning/STATE.md`。
> POC-01（H1 口径可判定性）判定 **PASS**，证据在 [`docs/agent/poc-01/`](docs/agent/poc-01/)。
> 这是"未被证伪"而非"已被证实"——压线通过，且两位回答者为同源模型。

## 从哪开始读

| 我想知道 | 读这个 |
|---|---|
| 这项目是什么、规则是什么 | [`AGENTS.md`](AGENTS.md) |
| 要证明什么、边界在哪 | [`PROJECT_SPEC.md`](PROJECT_SPEC.md) |
| 为什么这么设计 | [`DECISIONS.md`](DECISIONS.md) |
| 怎么判断做对了 | [`EVAL_CASES.md`](EVAL_CASES.md) |
| 现在做到哪了 | [`.planning/STATE.md`](.planning/STATE.md)、[`docs/agent/PROGRESS.md`](docs/agent/PROGRESS.md) |
| 接下来做什么 | [`.planning/ROADMAP.md`](.planning/ROADMAP.md) |
| 最危险的假设是什么 | [`docs/agent/POC.md`](docs/agent/POC.md) |

## 目录

```
finaudit-agent/
├── AGENTS.md            跨 Agent 地图 + 硬规则
├── CLAUDE.md            @AGENTS.md + Claude 专属（模式锁、停止协议、陷阱）
├── PROJECT_SPEC.md      假设 H1–H3、边界、架构 L0–L4、验收标准、停止条件
├── DECISIONS.md         D-001…D-012、未解决问题 U-01…U-03
├── EVAL_CASES.md        评测协议、问题集结构、失败归因分层、阶段门
├── .planning/           GSD 阶段状态（PROJECT / ROADMAP / STATE）
├── openspec/            OpenSpec 变更契约（config / changes / specs / archive）
├── docs/agent/          阶段 Artifact
│   ├── IDEA.md          DISCOVER ✅
│   ├── RESEARCH.md      RESEARCH ✅
│   ├── ARCHITECTURE.md  ARCHITECT ✅（A/B/C/D 四方案 → 选 B）
│   ├── POC.md           POC-01 ✅ 已执行（PASS）／POC-02 ⬜ 未执行
│   ├── poc-01/          POC-01 全部证据（冻结哈希 / 定义 / 题目 / 两份原始回答 / 比对判定）
│   ├── PROGRESS.md      跨会话状态
│   └── VERIFICATION.md  验收证据矩阵（模板）
├── .claude/  .agents/   OpenSpec 生成的 skills 与命令
└── .gitignore           非公开数据的物理隔离（D-010）
```

## 下一步

POC-01 已于 2026-08-10 执行完毕，判定 **PASS**（4/5 完全一致；取数字段与公式结构 5/5 一致；实质性分歧 0；未定义指标被两方正确拒答）。

它同时暴露了一个必须先解决的问题：**`PROJECT_SPEC.md` §5.1 的字段集不足以支撑机械判定**——
`common_pitfalls` 是给人读的散文，`restated` / `scope_change` / 跨准则版本不可比 / flags 词表 / 符号约定
这些规则没有任何字段承载其可执行形式。

因此下一步是**先扩展字段集（`/opsx:propose`），再规划 Phase 1（`/gsd-plan-phase 01`）**。

## 硬规则（详见 AGENTS.md）

1. **仅公开数据。** 任何雇主/客户数据禁止入库，包括脱敏后的（D-010，不可协商）
2. **不复制 `data secret` 的代码与语料。** 机制可借，资产隔离（D-004）
3. **给不出证据链 = 失败**，不算"降级成功"（D-003）
4. **每周 ≤ 8 小时**，转正优先，超时砍范围（D-008）
5. **评测集在看到模型输出前冻结**（D-012）

## 与秋招资料库的关系

本项目位于 `秋招/07-finaudit-agent/`，独立演进，未来可 `git init` 后迁出。方向论证见 `../00-项目方向与推进路径.md`。
