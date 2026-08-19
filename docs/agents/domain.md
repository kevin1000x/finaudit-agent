# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

> **本文件对模板做了适配，不是原样照抄。**
> 模板默认让技能去读根目录 `CONTEXT.md` 与 `docs/adr/`。本仓库**不建这两处**——
> 它已经有了对应的权威文档，再建一份会造出第二个决策落点，直接违反 D-009
> （「三者不得为同一件事创建重复的权威文档」）。
> 因此下面把模板的读取目标重定向到既有权威。**布局：single-context。**

## Before exploring, read these

按此顺序，冲突时**上位覆盖下位**：

| 模板里的位置 | 本仓库的实际位置 | 承载什么 |
|---|---|---|
| — | **`PROJECT_SPEC.md`** | 规格、假设 H1–H3、架构 L0–L4、验收标准 AC-01…、停止条件 |
| `docs/adr/` | **`DECISIONS.md`** | 已接受决策 D-001…D-013、未解决 U-01…U-04。**决策的唯一权威** |
| — | **`EVAL_CASES.md`** | 评测协议、问题集结构、失败归因分层、阶段门 |
| `CONTEXT.md`（术语表） | **`PROJECT_SPEC.md` §2.1 术语** | 语义层 / 证据链 / 口径 / 复核 的受控定义 |
| — | **`AGENTS.md`** | 跨 Agent 项目地图、硬规则、工作流入口 |

行为契约（可测的那一层）在 `openspec/specs/**/spec.md`。它与 `PROJECT_SPEC.md` 一一对应、
不重复权威：`PROJECT_SPEC.md` 是人读的说明，spec 是可测的 Requirement/Scenario。冲突时以
`PROJECT_SPEC.md` 为准。

阶段状态与进度在 `.planning/`（GSD 拥有），跨阶段 Artifact 在 `docs/agent/`。
两者**只汇总与路由，不覆盖上面三份权威**。

若上述文件确实不存在，**静默继续**，不要提示缺失、不要主动建议创建。

## Use the glossary's vocabulary

输出里出现领域概念时（issue 标题、重构提案、假设、测试名），用 `PROJECT_SPEC.md` §2.1
定义的术语，不要漂移到同义词。

本项目对措辞特别敏感的几处：

- **口径 / metric definition** —— 指「怎么算」的完整规定，不要写成「指标」或「字段」
- **证据链 / evidence chain** —— 是第一类产物，**不是日志**（D-003）。不要称其为 trace/log
- **复核 / review** —— 特指「不看 AI 解释、仅凭证据链独立判断对错」，不是 code review
- **拒答 / refusal** —— 是正确行为，不是失败降级（D-003 / AC-02）

概念不在术语表里 → 这是个信号：要么你在发明项目不用的语言（重新考虑），要么确有缺口（记下来）。

## Flag decision conflicts

若输出与某条已接受决策矛盾，**显式指出，不要静默覆盖**：

> _与 D-007（图谱须由问题驱动）冲突 —— 但值得重开，因为……_

按 `AGENTS.md` 的规矩：**与任一 Accepted 决策冲突时，先提决策变更，再提功能变更。**
决策变更走 `DECISIONS.md`（修订条目并标注日期与理由），不要新建 ADR 文件。

## 不建 `docs/adr/` 的后果与补偿

代价：`/domain-modeling` 等技能若要「懒创建 ADR」，在本仓库应改为**向 `DECISIONS.md` 追加条目**，
编号在现有最大决策号之后顺延，并同步更新文件顶部的决策索引表。
（此处刻意不写具体的下一个编号——写死会变成一处指向不存在条目的引用，
交叉引用门禁 `scripts/check_xrefs.py` 会当场判它悬空。）

补偿：`DECISIONS.md` 已具备 ADR 的全部要素——状态词汇（Accepted / Provisional / Deferred /
Rejected）、背景、决策、被拒方案、主要风险、反转触发条件。它就是本项目的 ADR，只是集中成一份。
