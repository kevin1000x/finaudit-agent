## Why

上一个变更 `extend-metric-definition-schema` 的 `design.md` §Open Questions 明确把两件事 defer 到 Phase 1：

> **OQ1**：受限 DSL 的具体语法形式（运算符集合、字段引用写法、是否支持括号）
> **OQ2**：全局 flag 词表的物理位置

`PROJECT_SPEC.md` §5.1 至今写着：

> 词表位置在 Phase 1 有 5 个以上真实 flag 后确定（候选：本文件内 / 独立文件）。

**defer 的条件现在已经满足。** 01-01 的 tracer（`7a1e7e7`）在一份真实的 `version: 2` 定义上把两件事都跑通了：
`src/semantic_layer/dsl.py` 是一个可工作的词法器 + 递归下降解析器，`metrics/_flags.yaml` 有 10 条真实 flag
（超过 §5.1 自己设的 5 条门槛），校验器 40 tests 全绿。

**现在必须把它们升格进权威文档，理由是时序：** wave 3 的 01-04 / 01-05 / 01-06 三个批次即将写 19 份定义。
此刻规格里没有任何一个字规定条件表达式怎么写——**19 份定义的作者只能去读 `dsl.py` 猜写法**。
这与 D-009 相悖（规格的权威落点是 `PROJECT_SPEC.md`，不是实现代码），且一旦事后否决当前语法，
返工面是 20 份定义的全部条件字符串，而不是现在的 1 份定义加 1 个模块。

**这是本阶段最后一个便宜的反悔点。** 现在改的代价是 1 份定义 + 1 个解析器；apply 之后再改是 20 倍。

证据：`src/semantic_layer/dsl.py`、`metrics/_flags.yaml`、`.planning/phases/01-semantic-layer/01-01-SUMMARY.md`。
冻结输入未被触碰，`docs/agent/poc-01/SHA256SUMS` 在本变更前后均须校验通过。

## What Changes

只动现有 9 条 Requirement 中的 2 条，其余 7 条一字不改。不新增、不删除、不重命名 Requirement。

**MODIFIED R4「标记必须来自受控词表并具备可求值的触发条件」** —— 补入两组规范性内容：

- **受控词表的物理位置**为 `metrics/_flags.yaml`；词表条目必须含 `name` / `description` / `scope` /
  `affects_comparability` / `introduced_by` 五个键；`scope` 取值为 `definition` 或 `system`；
  **`system` 域标记由运行时产出，定义文件内声明即不合规**（此前只在词表注释里写着，不具规范性）
- **触发条件的规范语法**：单行字符串，能力边界为字段引用、六个比较运算符、逻辑 `and` / `or` / `not`、
  以及唯一谓词 `is_missing()`。不含算术运算、不含 `is_missing` 之外的函数调用、不含循环与赋值

**MODIFIED R7「未定义条件必须可机械求值且命中时拒答」** —— 补入两组规范性内容：

- `undefined_conditions[].expr` 与标记触发条件**共用同一套语法**（沿用上一变更 `design.md` D3 的共用机制决定）
- **求值语义**：比较运算的任一操作数缺失时，该条件判为**不可求值并拒答**，
  MUST NOT 静默按假处理。判缺必须显式经由 `is_missing()`

## Capabilities

### Modified Capabilities

- `semantic-layer/metric-definition`：把条件表达式的语法与受控词表的物理位置由「实现里的事实」升格为「规格里的规范」。
  契约的**范围不变**——本变更不引入任何新字段、不改变任何一条判定的成立条件，只是把此前 defer 的两处空白填实。

## Non-goals

- ❌ **不扩语法能力。** 不加算术运算、不加聚合、不加「指标引用指标」。CCC（现金循环周期）需要后者，
  它已按 `01-06-PLAN.md` 转为 C2 类拒答靶子，扩语法须另提变更（`docs/agent/phase-01/open-questions.md`）。
- ❌ **不改实现。** 本变更不动 `src/`、`metrics/`、`tests/` 任何一行。规格描述的是 01-01 已实现且已测的行为，
  不是新行为——**唯一例外见下方「一处规格领先实现」，已显式声明，不隐藏。**
- ❌ **不动其余 7 条 Requirement。**
- ❌ **不迁移 POC-01 的 v1 定义。** 它们冻结在 `version: 1`，本变更前后 `SHA256SUMS` 均须 5/5 OK。
- ❌ **不把 `metrics/_flags.yaml` 变成第三份权威文档。** 见下方 D-009 一栏。

## 一处规格领先实现（本变更唯一的例外，OQ-02）

反向核对（`tasks.md` §2，在 apply 之前跑的）查出一处规格与实现不一致，**主动记录而非删规格**：

R4 要求词表条目含 `name` / `description` / `scope` / `affects_comparability` / `introduced_by` 五个键。
`vocabulary.py` 的 `Flag` dataclass 也确实把五个都声明为必需字段（无默认值）——意图一致。
但 `load_vocabulary()` 只真正强制了两个：

| 键 | 加载器行为 | 强制？ |
|---|---|---|
| `name` | `entry["name"]` | 是（抛 KeyError，未包装成 Finding） |
| `scope` | 校验 ∈ {definition, system}，不符即 raise | **是** |
| `description` | `entry.get(..., "")` | 否，静默补空串 |
| `affects_comparability` | `bool(entry.get(..., False))` | 否，**静默补 `False`** |
| `introduced_by` | `entry.get(..., "")` | 否，静默补空串 |

`affects_comparability` 静默补 `False` 方向最坏：漏写该键的 flag 会被当成「不影响可比性」，
于是一个本该阻断跨期比较的标记**悄悄不阻断，且不报错**——与 POC-01 的 C4 同一失效模式。
当前 10 条 flag 全部显式写齐五键，故现无实际错误；风险在将来新增 flag 时漏写。

**处理**：spec 保留五键要求（那是正确契约，且与 `Flag` dataclass 的意图一致），
实现不在本变更内改动——本计划的模式是 ARCHITECT。差异已记入
`docs/agent/phase-01/open-questions.md` OQ-02，倾向让加载器 fail-closed，
关闭前 01-08 的全量门禁须点名此项。

## 与 DECISIONS.md 的关系

| 决策 | 关系 |
|---|---|
| **D-002**（语义层先于 Agent） | **强化**。只动 L1。 |
| **D-003**（证据链是第一类产物） | **支撑**。单行字符串是为了复核者能读懂——把一条谓词摊成多行 YAML 会抬高复核成本。 |
| **D-009**（三者不得为同一件事创建重复权威文档） | **本变更的主要风险，已缓解**。`metrics/_flags.yaml` 被规定为 §5.1 的**可机读投影**：只承载 flag 枚举，不定义字段语义、不作决策，冲突时以 `PROJECT_SPEC.md` 为准。约束靠**范围**保证，不靠位置。 |
| **D-012**（评测集冻结） | **遵守**。不触碰冻结输入。 |
| **U-01**（证据链字段集未定） | **不越界**。本变更不规定证据链字段。 |

**不与任何 Accepted 决策冲突，无需先提决策变更。**

## 架构层次

**L1 — 语义层。** 语法受限这一点同时服务 L3（`PROJECT_SPEC.md` §5.2 的 `pre_execute` 静态检查需要一个封闭的节点集），
但本变更不实现 L3。
