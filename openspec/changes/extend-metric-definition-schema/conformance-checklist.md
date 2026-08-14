# 合规检查表与红测结果

> 来源：`specs/semantic-layer/metric-definition/spec.md` 的 9 条 Requirement。
> 用途：**红测**——在契约定稿前，用它检验 POC-01 的 3 份 `version: 1` 定义。
> 这 3 份定义**必须不合规**。若全部合规，说明新契约未加强任何约束，本变更失败。
>
> 检验基线：`git b512d68`，冻结校验 `sha256sum -c SHA256SUMS` 5/5 OK（exit 0）。
> 被检对象**未被修改**（kill criterion 禁止改定义直到通过）。

## 检查表（C1–C9 对应 spec 的 9 条 Requirement）

| # | Requirement | 判定问题 |
|---|---|---|
| R1 | 必须声明数据粒度 | 是否有 `grain`，含实体维度与期间维度？ |
| R2 | 必须声明符号约定 | 参与加减的每个 `source_fields` 是否声明了正负号约定？ |
| R3 | 必须显式声明倒推策略 | 是否显式写明允许或禁止由分项倒推？（不得留空） |
| R4 | 标记须受控且触发条件可求值 | 用到的 flag 是否来自受控词表？是否附带只引用已声明字段的可求值触发条件？ |
| R5 | 准则依据须结构化且带版本 | `standard_basis` 是否为结构化条目，每条含名称 + 可定位条号 + 版本标识？ |
| R6 | 引用字段须声明取值域与缺失表示 | 是否规定「缺失」如何表达？枚举字段是否声明合法取值集合？ |
| R7 | 未定义条件须可机械求值 | 每条 `undefined_conditions` 是否可对给定数据求值？ |
| R8 | 陷阱须可执行或标注仅供参考 | 每条 `common_pitfalls` 是否要么有对应可求值规则，要么标了 `advisory_only`？ |
| R9 | 版本变更后跨版本不可比 | 定义是否承载版本 bump 规则与跨版本比较约束？ |

## 逐份检验

图例：`FAIL` 不合规 ｜ `PARTIAL` 部分满足 ｜ `PASS` 合规

| # | net_profit_..._excl_nonrecurring | operating_cash_flow_ratio | revenue_growth_yoy |
|---|---|---|---|
| R1 | `FAIL` | `FAIL` | `FAIL` |
| R2 | `FAIL` | `FAIL` | `FAIL` |
| R3 | `FAIL` | `FAIL` | `FAIL` |
| R4 | `FAIL` | `FAIL` | `FAIL` |
| R5 | `FAIL` | `FAIL` | `FAIL` |
| R6 | `FAIL` | `FAIL` | `FAIL` |
| R7 | `PARTIAL` | `PARTIAL` | `PARTIAL` |
| R8 | `FAIL` | `FAIL` | `FAIL` |
| R9 | `PARTIAL` | `PARTIAL` | `PARTIAL` |

### 证据（引自被检定义原文，未改动）

**R1 数据粒度 —— 三份全 `FAIL`**
三份定义均无 `grain` 字段。`source_fields` 只声明报表与行项，没有公司标识、会计年度、报告期类型。
后果：`formula` 无法定位到唯一一行数据。两位回答者都独立指出了这一条（POC-01 C1）。

**R2 符号约定 —— 三份全 `FAIL`**
无任何一份声明符号约定。最危险的是扣非归母净利润：公式为减法
`is.net_profit_attributable_to_parent - notes.nonrecurring_pl_net_attributable_to_parent`，
若附注按绝对值列报而非「收益记正、损失记负」，结果方向整体翻转，
**且不触发任何 `undefined_conditions`**——静默错误（POC-01 C4）。

**R3 倒推策略 —— 三份全 `FAIL`**
扣非归母净利润的 `undefined_conditions` 只写了「附注未披露归母净额（仅披露税前合计）→ 拒答」，
但字段清单同时提供 `notes.nonrecurring_pl_total_pretax` / `_tax_effect` / `_minority_effect`，
「税前合计 − 所得税影响 − 少数股东部分」的倒推路径**既未允许也未禁止**（POC-01 C3）。

**R4 标记受控词表 —— 三份全 `FAIL`**
`restated` / `scope_change` 只作为散文出现在 `common_pitfalls` 里，
例如「两者不一致时必须标记 restated=true」。无受控词表、无取值域、无可求值触发条件、
无多 flag 并存的表示约定（POC-01 C2 / C5）。

**R5 准则依据结构化带版本 —— 三份全 `FAIL`**
三份的 `standard_basis` 均为自由文本列表，非结构化条目。版本标识**残缺不全**：

- 扣非归母净利润：前两条有（2023 年修订）（2010 年修订），
  第三条《企业会计准则第 33 号——合并财务报表》**无版本**
- 经营现金流量比率：三条**全部无版本**
- 营收同比增长率：《第 14 号——收入》有（2017 年修订），其余三条无版本

条号同样不齐：仅《第 30 号》在两处给到「第三章」「第十五、十六条」，其余只到准则名。
且无跨版本比较的 flag（POC-01 C8）。

**R6 取值域与缺失表示 —— 三份全 `FAIL`**
无一份规定「缺失」如何表达（null / 缺键 / 0）。
经营现金流量比率的枚举依赖尤其明显：`notes.business_combination_type` 被用于判定
`scope_change`，但**合法取值集合未声明**（同一控制 / 非同一控制 / 无 / 多类并存），
无法机械判定（POC-01 C7）。

**R7 未定义条件可求值 —— 三份 `PARTIAL`**
数值型条件可求值，例如
`bs.total_current_liabilities_period_end <= 0 → undefined，拒答`、
`is.operating_revenue_prior_as_presented <= 0 → undefined，拒答`。

但「披露存在性」型条件**不可求值**，因为 R6 未定义缺失表示：
`报表未单独列示「流动负债合计」→ undefined，拒答`、
`附注未披露「归属于母公司股东的非经常性损益净额」（仅披露税前合计）→ undefined，拒答`、
`报表仅列示「营业总收入」而无「营业收入」→ undefined，拒答`。
→ **R6 的缺失直接导致 R7 无法完全满足**，两者不是独立缺陷。

**R8 陷阱可执行或标注 —— 三份全 `FAIL`（本变更的核心）**
无一条 `common_pitfalls` 被标注 `advisory_only`，也无一条有对应的可求值规则。
其中**要求机械动作却无承载体**的至少有：

- 「存在追溯重述或会计政策变更的年度…必须标记 restated=true」（扣非归母净利润）
- 「跨版本年度的数值不得直接比较，必须记录所依据的公告版本」（扣非归母净利润）
- 「两者不一致时必须标记 restated=true 并记录差异，不得静默选一个」（营收同比）
- 「同一控制下企业合并…必须标记 scope_change=true」（营收同比）
- 「分母固定为流动负债合计，不得替换为负债合计」（经营现金流量比率）

这五条正是 POC-01 那句发现的直接实例：**`common_pitfalls` 是给人读的散文，不是可执行规则。**

**R9 版本语义 —— 三份 `PARTIAL`**
三份都有 `version: 1` 字段，`PROJECT_SPEC.md` §5.1 也写了「版本号变更即视为口径变更」。
但定义本身不承载 bump 规则（哪些字段改动必须 bump），
也不承载「拒绝跨版本比较」这一系统行为。判 `PARTIAL` 而非 `FAIL`，
是因为 R9 主要约束系统行为，单份定义无法独立满足——这一点在 spec 中已由 Scenario 表达。

## 红测判定

`tasks.md` 2.3 规定的通过条件：**3 份定义必须至少在「数据粒度」「符号约定」「标记受控词表」「陷阱可执行或标注」四条上不合规。**

| 判据 | 结果 |
|---|---|
| R1 数据粒度 | 3/3 `FAIL` ✅ |
| R2 符号约定 | 3/3 `FAIL` ✅ |
| R4 标记受控词表 | 3/3 `FAIL` ✅ |
| R8 陷阱可执行或标注 | 3/3 `FAIL` ✅ |

**红测通过：`FAIL` 27 项 / `PARTIAL` 6 项 / `PASS` 0 项（共 27 格）。**

新契约确实加强了约束——现有定义在其下一条都不合规，且不合规点与 POC-01 两位独立回答者
收敛出的 9 条缺陷高度重合（R1↔C1、R2↔C4、R3↔C3、R4↔C2+C5、R5↔C8、R6↔C7、R8 为根因项）。

**可以继续 apply。**

## 附带发现（非红测判据，但影响 Phase 1）

`PASS` 数为 **0**。这意味着新契约不是「在旧字段集上加几个字段」，而是**换了一套契约**。
因此 D5（v1 不迁移、新定义从 `version: 2` 起）不只是流程洁癖——
v1 与 v2 之间没有任何一条 Requirement 是共同满足的，**跨版本比较在技术上也确实无意义**。
