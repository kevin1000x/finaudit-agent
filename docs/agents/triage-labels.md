# Triage labels

The five canonical triage roles and the label string each maps to in this repo's issue tracker.

仓库此前**没有任何 label**，不存在与既有命名冲突的问题，因此直接采用 canonical 名称。

| Role | Label | Meaning |
|---|---|---|
| Needs triage | `needs-triage` | 尚未分诊。新 issue 的默认状态。 |
| Needs info | `needs-info` | 缺少判断所需的信息，已向提出者回问，等待补充。 |
| Ready for agent | `ready-for-agent` | 描述足够清楚，agent 可以直接动手。 |
| Ready for human | `ready-for-human` | 需要人来做决定或操作（重大决策、不可逆动作、对外可见变更）。 |
| Won't fix | `wontfix` | 明确不做。关闭时必须写明理由。 |

## 本仓库的分诊补充规则

**判到 `ready-for-human` 而不是 `ready-for-agent` 的情形**（对应 `CLAUDE.md` 的自主执行边界）：

- 架构方向、技术选型、推翻已接受的决策、改变项目范围
- 不可逆或对外的动作：仓库可见性变更（D-005）、删除数据、发布、发消息
- 与任一 Accepted 决策（D-001…D-013）冲突 —— 须先提决策变更，不得先改实现

**直接 `wontfix` 的情形**：

- 要求引入非公开数据（D-010，不可协商）
- 要求从 `data secret` / `privacy-preserving-agent-poc` 复制代码、语料或结论（D-004）
- 要求为了好看而修改已冻结的评测题目或标准答案（D-012）
- 要求做通用 Data Agent / NL2SQL 引擎 / 多数据源（D-001）
- 要求在未证明「非图不可」前建知识图谱（D-007）

关闭时把对应的 D-0xx 编号写进 comment，便于日后复核。
