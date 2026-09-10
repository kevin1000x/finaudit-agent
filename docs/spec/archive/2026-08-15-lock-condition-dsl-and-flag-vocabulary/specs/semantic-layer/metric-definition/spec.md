## MODIFIED Requirements

### Requirement: 标记必须来自受控词表并具备可求值的触发条件

定义中使用的每个标记（flag）MUST 来自一个受控词表，且 MUST 附带可求值的触发条件。触发条件 MUST 只引用已声明的字段。

受控词表的物理位置 MUST 为 `metrics/_flags.yaml`。该文件是 `PROJECT_SPEC.md` §5.1 的可机读投影：它只承载标记枚举，MUST NOT 定义字段语义或承载任何决策；与 `PROJECT_SPEC.md` 冲突时以后者为准。

词表中的每个条目 MUST 包含 `name`、`description`、`scope`、`affects_comparability`、`introduced_by` 五个键。`scope` 的取值 MUST 为 `definition` 或 `system` 之一。`scope` 为 `system` 的标记由运行时产出，MUST NOT 在口径定义文件内声明。

触发条件 MUST 为单行字符串，且 MUST 限于以下构造：

- **字段引用**：点号路径，至少含一个点。根命名空间 MUST 属于数据侧 `is` / `bs` / `cfs` / `notes`，或定义自身元数据侧 `standard_basis` / `comparison_period` / `metric`。数据侧引用的字段 MUST 已在该定义的 `source_fields` 中声明
- **比较运算符**：`==`、`!=`、`<`、`<=`、`>`、`>=`
- **逻辑运算符**：`and`、`or`、`not`，可用圆括号分组
- **字面量**：数值、字符串、`true`、`false`、`null`
- **谓词**：`is_missing()` 为唯一允许的谓词，其参数 MUST 为字段引用

触发条件 MUST NOT 包含算术运算、`is_missing()` 之外的函数调用、循环、赋值。整条表达式的根 MUST 产出布尔值——裸字段引用或裸字面量不构成条件。不满足上述任一约束的定义 MUST 被判定为不合规。

#### Scenario: 使用词表外的标记

- **WHEN** 一份口径定义使用了受控词表未收录的标记名
- **THEN** 该定义被判定为不合规

#### Scenario: 标记无触发条件

- **WHEN** 一份口径定义声明了某个标记，但未给出可求值的触发条件
- **THEN** 该定义被判定为不合规

#### Scenario: 触发条件命中时必须携带标记

- **WHEN** 某个标记的触发条件对当前数据求值为真
- **THEN** 该次回答的输出 MUST 携带该标记

#### Scenario: 定义文件内声明系统域标记

- **WHEN** 一份口径定义在 `flags` 中声明了词表里 `scope` 为 `system` 的标记
- **THEN** 该定义被判定为不合规，理由指出该标记由运行时产出而非定义声明

#### Scenario: 触发条件含算术运算

- **WHEN** 某个标记的触发条件写作 `bs.total_assets - bs.total_liabilities > 0`
- **THEN** 该定义被判定为不合规，理由指出算术运算不在触发条件的能力边界内

#### Scenario: 触发条件引用未声明的数据字段

- **WHEN** 某个标记的触发条件引用了一个数据侧字段，而该字段未出现在该定义的 `source_fields` 中
- **THEN** 该定义被判定为不合规

#### Scenario: 词表条目缺少可比性影响声明

- **WHEN** `metrics/_flags.yaml` 中某个条目缺少 `affects_comparability` 键
- **THEN** 该词表被判定为不合规，引用它的校验一律不予放行

### Requirement: 未定义条件必须可机械求值且命中时拒答

一份口径定义 MUST 声明其 `undefined_conditions`，每个条件 MUST 可对给定数据求值。任一条件求值为真时，系统 MUST 拒绝作答并给出可机读的拒答理由。

`undefined_conditions[].expr` MUST 使用与标记触发条件完全相同的表达式语法与能力边界。两者共用一套语法，MUST NOT 各自扩展。

求值语义 MUST 为 fail-closed：当比较运算的任一操作数缺失时，该条件 MUST 被判定为不可求值并拒答，MUST NOT 静默按假处理。判定字段是否缺失 MUST 显式经由 `is_missing()`，该谓词是唯一允许接收缺失值的构造。

#### Scenario: 零分母

- **WHEN** 某比率型指标的分母求值为零或负数，且该情况已列入未定义条件
- **THEN** 系统拒绝作答，不返回零、无穷或绝对值

#### Scenario: 拒答理由可机读

- **WHEN** 系统因命中未定义条件而拒答
- **THEN** 拒答理由标识出具体是哪一条未定义条件被命中

#### Scenario: 未定义条件不可求值

- **WHEN** 一份口径定义的某条未定义条件表述为自然语言且无法对数据求值
- **THEN** 该定义被判定为不合规

#### Scenario: 比较运算遇缺失操作数

- **WHEN** 某条未定义条件写作 `bs.total_assets > 0`，而 `bs.total_assets` 在当前数据中缺失
- **THEN** 系统拒绝作答，MUST NOT 把该比较判为假后继续计算

#### Scenario: 未定义条件与触发条件语法一致

- **WHEN** 一条 `undefined_conditions[].expr` 使用了标记触发条件所不允许的构造
- **THEN** 该定义被判定为不合规，判定理由与该构造出现在触发条件中时一致
