# POC-01 回答者 B — 原始输出（逐字，未编辑）

- 回答者：独立 subagent 会话 B（`general-purpose`，与 A 并行启动，无共享状态）
- 输入：`FREEZE.md` 所列 5 个文件的冻结版本，全文内嵌于 prompt，与 A 的 prompt 逐字相同
- 未授予仓库读取权限，未见 `POC.md`、判定阈值、H1 表述，未见回答者 A 的输出
- 工具调用次数：0

---

## Q1
metric_id: net_profit_attributable_excl_nonrecurring
answerable: yes
source_fields: is.net_profit_attributable_to_parent, notes.nonrecurring_pl_net_attributable_to_parent
formula: is.net_profit_attributable_to_parent - notes.nonrecurring_pl_net_attributable_to_parent
period_semantics: 时段
flags: NONE
reason: 提问者要的是剔除卖厂房、政府补贴等一次性项目后的主业利润，对应「扣非归母净利润」口径；被减项必须取归母净利润（不是含少数股东损益的 is.net_profit），减项必须取附注中已扣所得税及少数股东损益影响后的归母非经常性损益净额（不得用 notes.nonrecurring_pl_total_pretax）。

## Q2
metric_id: operating_cash_flow_ratio
answerable: yes
source_fields: cfs.net_cash_flow_from_operating_activities, bs.total_current_liabilities_period_end
formula: cfs.net_cash_flow_from_operating_activities / bs.total_current_liabilities_period_end
period_semantics: 混合（分子为本期累计的时段值，分母为期末时点余额）
flags: NONE
reason: 提问语义即「经营活动净现金流 ÷ 流动负债」，分母固定取流动负债合计期末余额，不得替换为 bs.total_liabilities，也不得用 period_begin 与 period_end 求平均；计算前须校验分母 > 0，否则转 undefined 拒答。

## Q3
metric_id: revenue_growth_yoy
answerable: yes
source_fields: is.operating_revenue_current, is.operating_revenue_prior_as_presented
formula: (is.operating_revenue_current - is.operating_revenue_prior_as_presented) / is.operating_revenue_prior_as_presented
period_semantics: 时段
flags: restated
reason: 上期数固定取本期报表列示的比较期金额（重述后），提问者已指出其与 2022 年年报原始披露数不一致，故必须标记 restated=true，且不得使用 is.operating_revenue_prior_as_originally_reported。

## Q4
metric_id: revenue_growth_yoy
answerable: no
source_fields: NONE
formula: NONE
period_semantics: 时段
flags: undefined
reason: 当年新上市、报表无比较期，命中 undefined_conditions「is.operating_revenue_prior_as_presented 缺失 → 拒答」，不得按 0 或按增长率 100% 处理（可由 notes.listing_first_disclosure_flag 佐证首次披露）。

## Q5
metric_id: NONE
answerable: no
source_fields: NONE
formula: NONE
period_semantics: NONE
flags: undefined
reason: 给定的三份口径定义均不包含存货周转天数与应收账款周转率，且字段清单只有 bs.inventory、bs.accounts_receivable 的单一时点值、无对应期初余额，无法构造任何平均余额口径，故在现有口径与字段边界内一律拒答，需先立新的 metric_id 并补充期初字段。

## 定义缺陷

1. **缺少实体维度与期间维度字段。** 字段清单里没有任何公司标识（股票代码/统一社会信用代码）和报告期标识（会计年度、报告期类型：年报/半年报/季报、期间起止日）。Q1、Q3 明确问的是「2023 年」，但按现有清单无法定位到某公司某年度的一行数据，公式在工程上不可执行。

2. **flag 没有受控词表。** `restated` / `scope_change` 只出现在 common_pitfalls 的散文里，三份定义都没有统一的 flags 枚举、取值类型和触发判定规则，评测与实现无法机械对齐。

3. **口径 1 缺 restated 的判定字段。** 定义要求「追溯重述年度必须标记 restated=true」，但 source_fields 里没有 `notes.restatement_flag`，也没说明该标志由何处读取，规则不可执行。

4. **口径 1 未封堵「推算路径」。** 清单同时给出 `notes.nonrecurring_pl_total_pretax`、`notes.nonrecurring_pl_tax_effect`、`notes.nonrecurring_pl_minority_effect` 三个字段，天然诱导用「税前合计 − 所得税影响 − 少数股东部分」倒算出归母净额。undefined_conditions 只写了「仅披露税前 → 拒答」，没有明确说明该推算是否被允许。这是最容易产生实现分歧的地方，必须显式二选一。

5. **口径 1 未声明符号约定。** 未规定 `notes.nonrecurring_pl_net_attributable_to_parent` 是「收益记正、损失记负」还是按绝对值录入。若数据源采用后者，减法方向会整体翻转，且不会触发任何 undefined 条件，属于静默错误。

6. **口径 2 未处理期间频率不匹配。** period_semantics 标为混合，但没有规定当分子为半年/季度累计时是否年化、以及分母该取哪个时点。Q2 问的是「一年」，若数据实际来自中期报表，定义给不出处理规则。

7. **口径 2 未声明 `bs.total_current_liabilities_period_begin` 的禁用状态。** 定义只说「平均口径另立 metric_id」，但清单里恰好提供了期初余额字段，缺一条显式的「本 metric 不得引用该字段」，容易被误用。

8. **字段描述与口径表述不一致。** `is.operating_revenue_prior_as_originally_reported` 的清单描述是「上年年报当时原始披露的**本年**金额」，「本年」指代不清（是上年年报的本年，即比较期年度），而口径 3 的表述是「上年年报当时原始披露的数」。两处措辞不对齐，需统一为「上年年报中列示的该会计年度金额」。

9. **口径 3 的 scope_change 不可判定。** 定义要求同一控制下合并时标记 `scope_change=true`，依赖 `notes.business_combination_type`，但该字段既未进入 source_fields，也没有给出取值域（同一控制/非同一控制/无），无法机械判定。

10. **跨准则版本的不可比性没有落成可执行标志。** 口径 1 指出非经常性损益项目清单随证监会公告版本变化、跨版本年度不得直接比较，但没有对应的 `standard_version` 字段或 `basis_version_mismatch` 标志，规则停留在提示层面。

11. **周转类指标整体缺位，且字段粒度不一致。** 清单只为流动负债提供了期初/期末双值，存货与应收账款只有单一时点值。这既导致 Q5 无解，也说明字段清单的时点字段设计缺乏统一规则（哪些科目需要期初期末双值应由口径需求反推确定）。

12. **三份定义均未声明合并/母公司范围、计量单位与币种、审计状态。** 字段前缀 `bs./is./cfs.` 隐含合并报表，但未在 metric 层面显式约束；单位与币种缺失会在跨公司或跨期比较时产生量纲错误。
