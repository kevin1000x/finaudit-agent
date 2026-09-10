# finaudit-agent

**财务分析结论的核查入口。** 把一段财报分析结论（券商 AI、问财、雪球、任何 LLM 的输出）
粘进来，系统把它拆成可核声明**逐条判定**，并对每一条给出可独立复核的证据链：
用了哪张表、哪个指标口径（含版本）、执行了什么、结果哈希是什么。

判定标准：**一位有审计背景的人，只看证据链、不看 AI 的解释，能在 5 分钟内独立判断答案对不对。**

🔴 **「核不了」是正当输出，不是失败。** 覆盖面窄是刻意的 ——
换来的是每一个能核的数都有人逐字段核对并签过字。

> ⚠️ **当前状态（2026-09-11 校准，此前这一段长期停留在「骨架阶段、零生产代码」）**
>
> | | |
> |---|---|
> | 生产代码 | `src/` 四个包（语义层 / 抽取器 / agent / 服务），**1171 个测试通过**，六道门禁 exit 0 |
> | 真实数据覆盖 | **2 家公司**：贵州茅台 2023（29/29 字段人工核对签署）、万华化学 2019（25/25）。另有合成夹具 6 行，**永远标成合成** |
> | 评测 | `frozen-01` 12/15 ｜ `frozen-02` ｜ `frozen-03`（核查层）14/14 |
> | 最危险的假设 | **`A2`（证据链能让人 5 分钟独立复核）仍未验证** —— 三轮复核者都是模型或本人，规格要求的「有审计背景的人」**一次都没有** |
>
> **不粉饰的三条**：
> - `frozen-03` 的 14/14 是**回归不是检验**（出题人就是写实现的人，见 [`eval/frozen-03/FREEZE.md`](eval/frozen-03/FREEZE.md) §限定）；
> - 名字里的 `audit` **背后是空的** —— 准则检索模块 0 个，`AC-07` 零数据。改名已定但未做；
> - 仓库里有 **134 处** `UNVERIFIED`（2026-09-11 实测：`grep -rc UNVERIFIED --include='*.md'` 求和）与大量 🔴 自我批评，**这是取舍不是疏漏**：
>   没有真实执行证据的一律记 `UNVERIFIED`，不记 PASS。

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
├── docs/spec/           已生效的行为契约（9 条 Requirement）+ 三个归档变更
├── docs/agent/          阶段 Artifact
│   ├── IDEA.md          DISCOVER ✅
│   ├── RESEARCH.md      RESEARCH ✅
│   ├── ARCHITECTURE.md  ARCHITECT ✅（A/B/C/D 四方案 → 选 B）
│   ├── POC.md           POC-01 ✅ 已执行（PASS）／POC-02 ⬜ 未执行
│   ├── poc-01/          POC-01 全部证据（冻结哈希 / 定义 / 题目 / 两份原始回答 / 比对判定）
│   ├── PROGRESS.md      跨会话状态
│   └── VERIFICATION.md  验收证据矩阵（模板）
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
4. **不设时间预算上限**，实际投入以 `PROGRESS.md` changelog 记录（D-008）
5. **评测集在看到模型输出前冻结**（D-012）

## 与秋招资料库的关系

本项目位于 `秋招/07-finaudit-agent/`，独立演进，未来可 `git init` 后迁出。方向论证见 `../00-项目方向与推进路径.md`。
