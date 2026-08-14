## Context

见 `proposal.md` §Why。

约束现状：
- 仓库 0 个代码文件，没有任何既有实现需要兼容
- `PROJECT_SPEC.md` §5.1 目前是散文式字段说明，没有可引用的结构契约
- POC-01 的 3 份 `version: 1` 定义是唯一的真实样本，且已冻结（`SHA256SUMS`）
- L3 可信执行层规划了 `pre_execute` 的 AST 静态检查（`PROJECT_SPEC.md` §5.2），本变更引入的任何表达式都要能被那一层检查

## Goals / Non-Goals

**Goals：**
- 让「触发条件」「未定义条件」成为可对数据求值的东西，而不是自然语言
- 让标记（flag）在 20 个指标之间保持一致，而不是各写各的
- 让版本号只对影响可比性的改动敏感，避免版本号通胀
- 保证新增结构能被 L3 的静态检查覆盖

**Non-Goals（设计层面，proposal 的范围之外再补）：**
- 不确定表达式 DSL 的完整语法细节（见 Open Questions）
- 不产出 JSON Schema / Pydantic 模型等任何实现物
- 不迁移 POC-01 的 v1 定义

## Decisions

### D1：触发条件用受限布尔 DSL，不用自然语言，也不用通用 Python 表达式

| 方案 | 结果 |
|---|---|
| A. 自由文本 | **否决。** 这正是 POC-01 C2/C5/C8 的病因，换个字段名装同样的散文没有意义 |
| B. Python 表达式 + `eval` | **否决。** 引入任意代码执行，与 `PROJECT_SPEC.md` §5.2 的 `pre_execute` AST 静态检查目标冲突；且复核者读不懂等于证据链失效（D-003） |
| C. 受限布尔 DSL | **采纳** |

DSL 的能力边界：字段引用、比较运算、逻辑运算（与/或/非）、`is_missing()`。不含函数调用、不含循环、不含赋值。

理由有两条，缺一不可：
1. **可静态检查。** 语法受限才检查得动，L3 的 `pre_execute` 才有实现路径。
2. **可被人读懂。** D-003 要求复核者仅凭证据链独立判断对错。触发条件如果是一段代码，复核成本会高于重算成本——那正是 `PROGRESS.md` 已登记的未消除风险之一。

### D2：flag 词表全局单一，指标只能引用不能自造

| 方案 | 结果 |
|---|---|
| A. 每个指标内联定义自己的 flags | **否决。** 那就没有词表了，拼写漂移会原样重现（POC-01 C2） |
| B. 全局词表文件，指标只能引用 | **采纳** |

词表的全部价值在于跨指标一致。允许内联即等于取消词表。新增 flag 是对词表的变更，走独立评审，不由单个指标定义顺手引入。

### D3：`undefined_conditions` 与 flag 触发条件共用同一套表达式机制

两者本质相同——都是「对给定数据求值的布尔条件」，差别只在命中后的动作：一个拒答，一个打标记。

分成两套语法会产生两处实现、两处静态检查、两处漂移。共用一套后，D1 的 DSL 只需实现一次。

### D4：版本号只对影响可比性的改动敏感

- **必须 bump**：`grain` / `source_fields` / `formula` / `sign_convention` / `derivation` / flag 触发条件 / `undefined_conditions` 的任何改动
- **不 bump**：`advisory_only` 陷阱文本、`display_name`、`aliases` 的措辞调整

理由：版本号在本项目里的唯一用途是判定「两期结论能不能比」（`PROJECT_SPEC.md` §5.1）。既然如此，它就该只对影响可比性的东西敏感。让版本号跟着错别字跳动，会让「跨版本不可比」这条规则很快被当成噪音忽略掉。

### D5：POC-01 的 v1 定义不迁移、不改写

保留为旧 schema 的历史样本。新 schema 下的定义从 `version: 2` 起。

理由：`POC.md` 的 kill criterion 明确禁止「改定义直到通过」；`SHA256SUMS` 冻结校验必须在 apply 前后都通过。迁移旧定义会同时踩这两条。

### D6：契约落在 `PROJECT_SPEC.md` §5.1 与本 capability spec，不新增第三份权威文档

`PROJECT_SPEC.md` §5.1 保留为**人读的字段说明**，本 capability 的 spec 是**可测的行为契约**，两者一一对应不重复。

理由：D-009 明确禁止三套方法论为同一件事创建重复权威文档。若再引入一份独立 schema 文件，就会出现三处描述同一个字段集、且必然不同步。

## Risks / Trade-offs

| 风险 | 缓解 |
|---|---|
| 受限 DSL 表达力不足，某些真实约束写不出来 | 用 POC-01 已知的 9 条收敛缺陷做覆盖测试。写不出来的**记为 Open Question，不许直接扩语法**——扩语法会一路滑回通用表达式，把 D1 的两条理由都放弃掉 |
| 元规则形同虚设：大量陷阱被随手标 `advisory_only` 绕过 | Phase 1 结束时统计 `advisory_only` 占比。**> 50% 即视为元规则失效**，需重新设计而不是接受现状 |
| schema 变复杂，写 20 个指标的成本显著上升 | 这是**有意支付的代价**。POC-01 已证明简单 schema 撑不住机械判定。若成本高到 Phase 1 做不完，正确反应是砍指标数量，不是砍字段 |
| 全局 flag 词表成为瓶颈，每加一个指标都要改词表 | 可接受。词表变更频繁本身就是信号——说明 flag 的抽象层次选错了 |
| 与 U-01（证据链字段集未定）边界模糊 | `flags` 与 `standard_basis.version` 是证据链的**上游输入**，不是证据链字段。Phase 2 定证据链字段集时不得反过来改本 schema |

## Migration Plan

当前仓库 0 个代码文件，无部署、无回滚对象。迁移即文档变更：

1. 校验 `docs/agent/poc-01/SHA256SUMS`（apply 前）
2. 改写 `PROJECT_SPEC.md` §5.1；同步 AC-01 的字段要求
3. 建立全局 flag 词表的位置约定（不填内容，Phase 1 边做边填）
4. 再次校验 `SHA256SUMS`（apply 后，确认没碰冻结输入）
5. `openspec validate` 通过后 archive

回滚：`git revert` 单个 commit 即可，无状态残留。

## Open Questions

- **受限 DSL 的具体语法形式**（YAML 嵌套结构 vs 单行字符串表达式）。不影响本 spec 的任何 requirement、不影响 D1–D6 的选择、不影响任务拆分，可在 Phase 1 写第一个 `version: 2` 定义时定下来。
- **全局 flag 词表的物理位置**（`PROJECT_SPEC.md` 内 vs 独立文件）。取决于词表最终规模，Phase 1 有了 5 个以上真实 flag 后再定。
