## Why

POC-01（2026-08-10，判定 PASS）在通过的同时暴露了一个更重要的结果：**现行 `PROJECT_SPEC.md` §5.1 的指标口径字段集不足以支撑机械判定。**

两位独立回答者列出 16 条定义缺陷，其中 9 条独立收敛。收敛项里有 5 条同一个根因：

> `common_pitfalls` 是给人读的散文，不是给机器执行的规则。「必须标记 restated」「跨准则版本不可比」「同一控制下合并要标记 scope_change」全写在 pitfalls 里，但**没有任何字段承载这些规则的可执行形式**。

其中最危险的一条（C4，符号约定未声明）会产生**方向性错误且不触发任何 undefined 条件**——静默错误，正是本项目声称要消灭的东西。

现在必须改：Phase 1 要做 20 个指标。字段集不修，等于把同一个缺陷复制 20 遍，且 AC-02（口径缺失时拒答且理由可机读）无法达成。

证据：`docs/agent/poc-01/COMPARISON.md` §5，冻结输入哈希见 `docs/agent/poc-01/SHA256SUMS`。

## What Changes

在 §5.1 的现有字段（`metric_id` / `source_fields` / `formula` / `standard_basis` / `period_semantics` / `common_pitfalls`）之上：

- **新增 `grain`**：声明实体维度与期间维度（公司标识、会计年度、报告期类型）。现行字段集无法把公式定位到具体一行数据，公式在工程上不可执行。（POC-01 C1）
- **新增 `sign_convention`**：声明取数字段的正负号约定。（C4）
- **新增 `derivation`**：显式声明是否允许由分项倒推缺失的合计项，二选一，不留空白。（C3）
- **新增 `flags`**：受控词表 + 每个 flag 的**可执行触发条件**。取代散落在 pitfalls 里的标记要求。（C2、C5）
- **`standard_basis` 结构化**：由自由文本改为带 `version` 的结构，并在跨版本比较时触发 flag。（C8）
- **`source_fields` 增加取值域与缺失表示约定**：枚举型字段必须声明合法取值；必须规定「缺失」如何表达（null / 缺键 / 0 后果完全不同）。（C7）
- **`undefined_conditions` 正式进入字段集**：POC-01 已实际使用并验证有效，但从未写进 §5.1。
- **BREAKING —— 新增元规则**：**每一条 `common_pitfalls` 必须要么有对应的可执行规则，要么显式标注 `advisory_only: true`。** 这条是本变更的核心，它防止「散文冒充规则」重新长回来。现有 3 份 POC-01 定义在新 schema 下不合规。

## Capabilities

### New Capabilities

- `semantic-layer/metric-definition`：指标口径定义的结构契约——一份口径定义必须包含哪些字段、每个字段的语义与取值约束、以及哪些约束必须可被机械校验而非仅供人阅读。

### Modified Capabilities

（无。`openspec/specs/` 当前为空，本变更建立第一个 capability。）

## Non-goals

- ❌ **不实现校验器。** 本变更只定契约，不写校验代码。校验器属于 L3，排在 Phase 1 之后。
- ❌ **不确定证据链字段集。** U-01 明确要求等 Phase 2 复核实验数据，不得在 Phase 1 提前拍板。本变更产生的 `flags` 与 `standard_basis.version` 是证据链的**上游输入**，不等于证据链字段本身。
- ❌ **不修改 POC-01 已冻结的 3 份定义。** `POC.md` 的 kill criterion 禁止「改定义直到通过」。它们停在 `version: 1`，作为旧 schema 的历史样本保留。新 schema 下的定义从 `version: 2` 起，跨版本不可比较。
- ❌ **不补 C6 与 C9。** C6（字段描述自相矛盾）属于数据字典问题，C9（周转类指标缺位、字段粒度不统一）属于覆盖度问题，两者都不是 schema 缺陷，留给 Phase 1 的字段清单工作。
- ❌ **不扩展指标数量。** 本变更不产出任何新的指标定义。

## 与 DECISIONS.md 的关系

| 决策 | 关系 |
|---|---|
| **D-002**（语义层先于 Agent） | **强化**。本变更只动 L1，不涉及任何 Agent 编排。 |
| **D-003**（证据链是第一类产物） | **支撑**。`flags` 与 `standard_basis.version` 让证据链能携带口径版本与口径变动标记。 |
| **D-012**（评测集冻结） | **遵守**。不触碰 POC-01 的冻结输入；`SHA256SUMS` 在 apply 前后均须校验通过。 |
| **U-01**（证据链字段集未定） | **不越界**。见 Non-goals 第 2 条。 |
| **D-008**（不设时间预算） | 无冲突。 |

**不与任何 Accepted 决策冲突，因此无需先提决策变更。**

## 架构层次

**L1 — 语义层。** 不涉及 L0（数据层）、L2（知识层）、L3（可信执行层）、L4（TUI）。

## Impact

- `PROJECT_SPEC.md` §5.1 —— 权威规格，本变更的落点
- `PROJECT_SPEC.md` AC-01 —— 「每个含字段映射、公式、准则依据、≥3 条常见陷阱」需同步为新字段集
- `docs/agent/poc-01/definitions/*.yaml` —— **不改**，作为 `version: 1` 历史样本保留
- `EVAL_CASES.md` —— C2 类拒答题的判定依赖 `undefined_conditions` 的可执行性，本变更使其可机械判定
- 无代码影响（当前仓库 0 个代码文件）
