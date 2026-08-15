## MODIFIED Requirements

### Requirement: 标记必须来自受控词表并具备可求值的触发条件

定义中使用的每个标记（flag）MUST 来自一个受控词表，且 MUST 附带可求值的触发条件。触发条件 MUST 只引用已声明的字段。

受控词表的物理位置 MUST 为 `metrics/_flags.yaml`。该文件是 `PROJECT_SPEC.md` §5.1 的可机读投影：它只承载标记枚举，MUST NOT 定义字段语义或承载任何决策；与 `PROJECT_SPEC.md` 冲突时以后者为准。

词表中的每个条目 MUST 包含 `name`、`description`、`scope`、`affects_comparability`、`introduced_by` 五个键。`scope` 的取值 MUST 为 `definition` 或 `system` 之一。`scope` 为 `system` 的标记由运行时产出，MUST NOT 在口径定义文件内声明。

触发条件 MUST 为单行字符串，且 MUST 限于以下构造：

- **字段引用**：点号路径，至少含一个点。根命名空间 MUST 属于数据侧 `is` / `bs` / `cfs` / `notes` / `kpi`，或定义自身元数据侧 `standard_basis` / `comparison_period` / `metric`。数据侧引用的字段 MUST 已在该定义的 `source_fields` 中声明
- **比较运算符**：`==`、`!=`、`<`、`<=`、`>`、`>=`
- **逻辑运算符**：`and`、`or`、`not`，可用圆括号分组
- **字面量**：数值、字符串、`true`、`false`、`null`
- **谓词**：`is_missing()` 为唯一允许的谓词，其参数 MUST 为字段引用

数据侧根命名空间对应五类公开披露来源：`is` 合并利润表、`bs` 合并资产负债表、`cfs` 合并现金流量表、`notes` 财务报表附注、`kpi` 年报「主要会计数据和财务指标」章节中公司已直接披露的指标值。`kpi` 与前四者的区别是它承载**披露值**而非报表行项目，使「取披露值、禁止倒推」的口径立场可被表达。

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

#### Scenario: 引用已披露指标值

- **WHEN** 一份口径定义引用 `kpi.` 前缀的字段，并在 `source_fields` 中声明其 `statement` 为「主要会计数据和财务指标」
- **THEN** 该引用合规，且该字段被视为公司披露值而非可由报表推算的值

### Requirement: 常见陷阱必须可执行或显式标注为仅供参考

`common_pitfalls` 中的每一条 MUST 满足以下二者之一：对应到一条可求值的规则（标记触发条件、未定义条件、字段约束或倒推策略），或被显式标注为仅供参考。未标注且无对应规则的陷阱条目 MUST 使定义判定为不合规。

`enforced_by` 的取值 MUST 为 `<类别>.<标识>` 形式，类别 MUST 为以下之一：

- `flags.<标记名>` —— 标识 MUST 为该定义已声明的标记，或受控词表中 `scope` 为 `system` 的标记。允许后者是必需的而非宽容：本规格禁止定义文件声明 `system` 域标记，若此处只认定义内声明的，任何跨期不可比类的陷阱在构造上都无法满足本要求，两条要求会直接冲突
- `undefined_conditions.<下标>` —— 下标 MUST 为非负整数且不越界
- `source_fields.<属性名>` —— 属性名 MUST 为 `source_fields` 条目的合法属性
- `derivation.<属性名>` —— 属性名 MUST 为 `allow_from_components` 或 `note`

`derivation` 作为承载体成立的理由：`allow_from_components` 是布尔字段、可机械读取，「本定义禁止由分项倒推」是可判定约束而非散文。若将其排除在外，「禁止倒推」类陷阱只能标注为仅供参考，等于把最应当具备机械后果的一类降级。

#### Scenario: 陷阱既无规则也无标注

- **WHEN** 一份口径定义的某条 `common_pitfalls` 要求「必须标记某状态」，但定义中不存在对应的标记与触发条件，且该条未被标注为仅供参考
- **THEN** 该定义被判定为不合规

#### Scenario: 显式标注为仅供参考

- **WHEN** 一条陷阱描述的是业务背景而非可判定约束，且已被标注为仅供参考
- **THEN** 该定义在这一条上合规，且该条不参与任何机械校验

#### Scenario: 陷阱由倒推策略承载

- **WHEN** 一条陷阱描述「本定义禁止由分项倒推」，且 `enforced_by` 指向 `derivation.allow_from_components`，而该字段取值为 `false`
- **THEN** 该陷阱被视为有可求值规则承载，定义在这一条上合规

#### Scenario: enforced_by 指向不存在的承载体

- **WHEN** 一条陷阱的 `enforced_by` 指向一个既不在定义内、也不在受控词表 `system` 域中的标记名
- **THEN** 该定义被判定为不合规
