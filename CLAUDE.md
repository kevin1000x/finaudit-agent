@AGENTS.md

# Claude Code 专属补充

上面导入的 `AGENTS.md` 是跨 Agent 的项目地图与硬规则。本文件只加 Claude Code 特有的部分。**保持在 200 行以内**——它是 Constitution + Map，不是 Workflow Dump。

## 模式锁

每次会话开始时，先声明当前处于哪个模式，并只做该模式允许的事：

| 模式 | 允许 | 禁止 |
|---|---|---|
| `DISCOVER` | 提问、澄清、写 `docs/agent/IDEA.md` | 写代码、定架构 |
| `RESEARCH` | 只读探索、写 `docs/agent/RESEARCH.md` | 改任何生产文件、推荐方案 |
| `ARCHITECT` | 比较方案、写 `docs/agent/ARCHITECTURE.md` | 写实现代码 |
| `POC` | 写一次性实验代码 | 写生产架构、加抽象 |
| `PLAN` | 写 `.planning/phases/**/PLAN.md` | 实现 |
| `IMPLEMENT` | 只做当前一个 task | 顺手重构、改计划 |
| `VERIFY` | 跑真实命令、记录真实输出 | 修实现 |
| `REVIEW` | 读 diff 与证据、给发现 | 直接改代码 |

模式没声明时，默认拒绝写生产代码，先问清楚。

## 停止协议

计划与现实不符时**立刻停止**，不要即兴发挥。按这个格式报告：

```text
EXPECTED   计划里说的是什么
FOUND      实际看到的是什么
IMPACT     这个差异影响什么
OPTIONS    可选的处理方式（至少两个）
```

同一个 bug 连续 3 次修复失败 → 停止打补丁，回头怀疑架构或心智模型（Superpowers `systematic-debugging`）。

## 完成的定义

不接受"应该可以了"。声明完成必须给出：

```text
验收标准 → 验证方法 → 实际命令 → 真实输出 → 证据位置 → PASS / FAIL / UNVERIFIED
```

没有真实执行证据的一律记 `UNVERIFIED`，不记 PASS。声明完成前调用 `verification-before-completion` skill。

## 本项目的高代价陷阱

1. **把非公开数据带进来。** 这是唯一不可挽回的错误（D-010）。任何来自实习、雇主内部系统、客户的字段名、表结构、数值——包括脱敏与聚合后的——都不允许出现。写代码前先问：这个字段名是从哪来的？
2. **从 `data secret` 复制代码或语料。** 机制思想可以借，资产不能搬（D-004）。两个项目的可信度是互相独立的，交叉污染会同时毁掉两边。
3. **先看模型输出再定评测标准。** 评测集一旦冻结就不许为了好看而改（D-012）。发现题目本身错了 → 作废并公开记录，不修改后重用。
4. **为了做图而做图。** 建图前必须先写出 3 个「纯向量 RAG 答不了」的具体问题并证明其答不了（D-007）。
5. **把 TUI 做上瘾。** 它是交付形式不是卖点（D-006），Phase 2 只做到能展示证据链为止。
6. **在语义层没做完时跑去搭 Agent 编排。** 语义层是唯一别人抄不走的一层（D-002）。
7. **流程超过项目。** 三套方法论叠加容易产生 Ceremony Engineering。任一阶段流程开销 > 产出时间的 30% → 删掉贡献最小的那套（D-009）。Harness 要定期做减法。

## 常用命令

```bash
# 阶段状态
cat .planning/STATE.md

# 校验已冻结实验输入未被改动（声明任何评测/POC 结论前必跑）
cd docs/agent/poc-01 && sha256sum -c SHA256SUMS

# OpenSpec：提一个变更 / 查看 / 应用 / 归档
openspec list
openspec show <change-id>
openspec validate

# 评测（Phase 1 起可用）
python -m eval.run --suite frozen-01 --report reports/
```

（评测命令在 Phase 1 实现前不存在，不要假装跑过。）

## Agent skills

### Issue tracker

GitHub Issues on `kevin1000x/finaudit-agent`（私有），用 `gh` CLI。与 `.planning/`（阶段）、`openspec/changes/`（规格变更）职责不重叠：**改规格 → OpenSpec；推阶段 → GSD；其余 → issue。** 见 `docs/agents/issue-tracker.md`。

### Triage labels

五个 canonical 标签，仓库原先无 label 故无冲突：`needs-triage` / `needs-info` / `ready-for-agent` / `ready-for-human` / `wontfix`。见 `docs/agents/triage-labels.md`。

### Domain docs

Single-context，但**不建 `CONTEXT.md` 与 `docs/adr/`**——决策权威是 `DECISIONS.md`，术语表是 `PROJECT_SPEC.md` §2.1，另建会造出第二个决策落点（D-009）。ADR 以追加 D-0xx 条目的形式落在 `DECISIONS.md`。见 `docs/agents/domain.md`。

## Skill 与 Hook 的分工

- **Prompt = preference，Hook = policy。** 必须每次执行的动作写进 hook，不要写进提示词。
- 计划配置的 hook（等真实失败模式出现后再加，不要一次配 30 个）：
  - `PostToolUse(Edit|Write)` → 非公开数据扫描（D-010 的机械执行）
  - `Stop` → 若本轮改了 `metrics/` 下的口径定义，要求给出版本号变更说明
- 重复出现的多步骤流程 → 做成 Skill，不要塞进 CLAUDE.md。

## 与秋招资料库的关系

本项目位于 `秋招/07-finaudit-agent/`，是求职资料库的一部分但独立演进。相关文档：

- `../00-项目方向与推进路径.md` — 为什么是这个方向、竞品格局、五阶段路线
- `../00-投递策略与学习路径（转正优先版）.md` — 投递节奏与优先级背景（**注意：D-008 的时间预算上限已于 2026-08-10 取消**，该文件里的工时假设不再是本项目的约束）
- `../03-简历与项目/项目资产盘点与改造方案.md` — 本项目如何写进简历

未来若迁出为独立仓库，删掉本节即可。
