## Context

见 `proposal.md` §Why。与上一个变更最大的不同：**这次不是从零设计，而是把已经跑起来的东西固化。**

约束现状（2026-08-15）：

- `src/semantic_layer/dsl.py` 已实现并通过 40 tests。语法不是纸上设计，是有解析器的既成事实
- `metrics/_flags.yaml` 有 10 条真实 flag，超过 §5.1 自设的 5 条门槛
- `metrics/net_profit_attributable_excl_nonrecurring.yaml` 是唯一一份 `version: 2` 定义，已判合规
- 19 份定义即将开写。规格晚一个 wave 定，返工面就从 1 份变 20 份
- POC-01 的 3 份 v1 定义已冻结，本变更全程不得触碰

**本变更的取舍方向因此与上一个不同**：上一个是「设计一个更好的契约」，这一个是
「确认既成事实值得固化，还是趁便宜赶紧推翻」。所有 Decision 都要按这个问题作答。

## Goals / Non-Goals

**Goals：**

- 19 份定义的作者对着规格写条件表达式，而不是对着 `dsl.py` 猜
- flag 词表的物理位置从「待定」变成「确定」，且不因此产生第三份权威文档
- 语法的**能力边界**写成规范性条款——不只说「支持什么」，更要说「不支持什么」，
  因为后者才是作者撞墙时需要查的东西
- 求值语义中的 fail-closed 行为进规格。这是 R6「缺失与零走不同分支」在条件层的对应物

**Non-Goals：**

- 不扩展语法能力（见 proposal Non-goals）
- 不产出 JSON Schema / Pydantic 模型
- 不规定报告层如何渲染条件

## Decisions

### D1：条件表达式用单行字符串，不用 YAML 嵌套结构

| 方案 | 结果 |
|---|---|
| A. YAML 嵌套结构表示表达式 | **否决** |
| B. 单行字符串 + 受限解析器 | **采纳** |

否决 A 的理由两条：

1. **与既有权威示例不一致。** `PROJECT_SPEC.md` §5.1 的字段集示例本身就写作
   `trigger: notes.restatement_flag == true` 与 `expr: is_missing(notes.x)`——都是单行字符串。
   改用嵌套结构就要连带改权威文档的既有示例，而那些示例是上一个变更刚 apply 的。
2. **复核成本。** D-003 要求复核者仅凭证据链在 5 分钟内独立判断对错。
   `notes.restatement_flag == true` 摊成

   ```yaml
   trigger:
     op: eq
     left: {field: notes.restatement_flag}
     right: {literal: true}
   ```

   信息量相同、行数四倍、可读性下降。嵌套结构的收益（无需自研解析器）在 A 股口径这个场景里
   换不回这个成本——尤其是解析器已经写完并通过测试，那份收益现在等于零。

### D2：不用 Python 语法解析器做白名单校验

| 方案 | 结果 |
|---|---|
| A. `ast.parse` + 节点白名单 | **否决，有实测硬证据** |
| B. 自研词法器 + 递归下降解析器 | **采纳** |

否决 A 的证据（**2026-08-15 于本机 Python 3.14 实测**）：

```python
>>> import ast
>>> ast.parse("is.net_profit_attributable_to_parent > 0", mode="eval")
SyntaxError
```

原因是**合并利润表前缀 `is` 恰好是 Python 关键字**，`is.` 开头的字段引用在 Python 语法下根本不合法。

这不是可以绕开的巧合：`is.` 前缀同时出现在 `PROJECT_SPEC.md` §5.1 的字段集示例公式里、
和 `docs/agent/poc-01/field_inventory.md` 里——而后者**已冻结，一个字节都不许动**（D-012）。
改前缀意味着同时修改权威文档的既有示例并使冻结文件与在用约定脱节，代价远高于自研一个 200 行的解析器。

该实测已固化成回归测试 `test_python_ast_cannot_parse_is_prefix`，防止日后有人「优化」成用 `ast`。

第二条理由与语法树的所有权有关：`PROJECT_SPEC.md` §5.2 规划的 L3 `pre_execute` 要对条件做静态检查，
检查对象必须是本项目自己定义的封闭节点集（当前 7 个：`FieldRef` / `Literal` / `IsMissing` /
`Compare` / `Not` / `And` / `Or`），而不是 Python 的完整语法树。用 `ast` 意味着白名单要追着
Python 版本演进跑。

### D3：flag 词表放独立文件 `metrics/_flags.yaml`，不内联进 `PROJECT_SPEC.md`

| 方案 | 结果 |
|---|---|
| A. 内联进 `PROJECT_SPEC.md` §5.1 | **否决** |
| B. 独立文件 `metrics/_flags.yaml` | **采纳** |

否决 A 的理由：词表要被**校验器机械消费**（`vocabulary.py` 加载它，R4 逐条比对）。
嵌在人读的 Markdown 文档里，等于让程序从散文里正则抠数据——**这正是上一个变更要消灭的失效模式**
（`common_pitfalls` 是散文所以不可执行）。在同一个 capability 上刚修好一次，不应立刻在词表上重犯。

采纳 B 的同时必须处理 D-009 的风险：多一个文件就多一个可能的权威落点。
缓解方式是**在规格里写死它的从属地位**——`metrics/_flags.yaml` 是 §5.1 的**可机读投影**，
只承载 flag 枚举，不定义字段语义、不作任何决策；与 `PROJECT_SPEC.md` 冲突时以后者为准。
**约束靠范围保证，不靠位置。** 把它放在 `metrics/` 而不是仓库根，也是为了让「它是数据不是文档」这件事在目录结构上就成立。

### D4：`system` 域标记不得在定义文件内声明，从注释升格为规范

`metrics/_flags.yaml` 的注释里已经写着这条，但注释不具规范性——校验器实现了它，规格却没有要求它。
这是典型的**实现严于规格**，一旦有人按规格重写实现就会丢掉。本变更把它写进 R4。

10 条 flag 里 `scope: system` 的恰有 2 条（`metric_version_mismatch` / `source_disagreement`），
它们由运行时在比较两期结论时产出，定义文件无从知晓，声明了也不可能有正确的 trigger。

### D5：求值遇缺失操作数判为不可求值并拒答，不静默按假处理

这条是 R6「缺失与取值为零走不同分支」在条件层的对应物，实现里已经是 `MissingOperandError`，
但 R7 的现有措辞只说条件「MUST 可对给定数据求值」，没说**求值不了时怎么办**。

留空的后果是具体的：`bs.total_assets > 0` 在 `total_assets` 缺失时，若静默按假处理，
「资产为零或负」这条未定义条件就不会命中，系统会继续往下算——**静默错误，正是本项目声称要消灭的东西**
（POC-01 C4 同类）。所以拒答是唯一正确行为，判缺必须显式写 `is_missing()`。

## Risks / Trade-offs

| 风险 | 缓解 |
|---|---|
| 10 条 flag 不够覆盖 20 个指标，后续批次频繁撞停止协议 | 由人在 checkpoint 判断覆盖度，判断结论抄进 SUMMARY，供 01-08 与实际发生的 flag 请求对照。词表膨胀本身是坏信号，不预先扩 |
| 语法过窄，某个指标写不出需要的约束 | 写不出来即按停止协议记入 `docs/agent/phase-01/open-questions.md`，不就地扩语法。CCC 已是先例 |
| 规格措辞与 `dsl.py` 行为不一致 | apply 后重跑全量测试；措辞逐项对照解析器的白名单常量（`ROOT_NAMESPACES` / `_COMPARE_OPS` / `_PREDICATES` / `_KEYWORDS`） |
| `metrics/_flags.yaml` 长成第三份权威文档 | D3 的从属声明写进规格与 §5.1 两处 |

## Open Questions

无。本变更关闭的正是上一个变更的两条 Open Question（OQ1 语法形式、OQ2 词表位置）。
