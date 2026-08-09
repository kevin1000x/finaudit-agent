# POC-01 回答者 A — 原始输出（逐字，未编辑）

- 回答者：独立 subagent 会话 A（`general-purpose`，与 B 并行启动，无共享状态）
- 输入：`FREEZE.md` 所列 5 个文件的冻结版本，全文内嵌于 prompt
- 未授予仓库读取权限，未见 `POC.md`、判定阈值、H1 表述，未见回答者 B 的输出
- 工具调用次数：0

---

## Q1
metric_id: net_profit_attributable_excl_nonrecurring
answerable: yes
source_fields: is.net_profit_attributable_to_parent, notes.nonrecurring_pl_net_attributable_to_parent
formula: is.net_profit_attributable_to_parent - notes.nonrecurring_pl_net_attributable_to_parent
period_semantics: 时段
flags: NONE
reason: 提问者要的"剔除卖厂房、政府补贴等一次性损益后主业赚到的利润"正是扣非归母净利润；被减项必须取归母净利润而非 is.net_profit（后者含少数股东损益），减项必须取附注中已扣所得税与少数股东影响的净额，不得用 notes.nonrecurring_pl_total_pretax；若 notes.restatement_flag 为真需追加 restated，若附注仅有税前合计则转为 undefined 拒答。

## Q2
metric_id: operating_cash_flow_ratio
answerable: yes
source_fields: cfs.net_cash_flow_from_operating_activities, bs.total_current_liabilities_period_end
formula: cfs.net_cash_flow_from_operating_activities / bs.total_current_liabilities_period_end
period_semantics: 混合（分子为本期累计时段数，分母为期末时点余额）
flags: NONE
reason: 提问语义即"一期经营活动净现金覆盖流动负债的比例"，分子固定取经营活动产生的现金流量净额（不得用 cfs.cash_inflow_from_operating_activities_subtotal 或 cfs.cash_received_from_sales_of_goods 替代），分母固定取流动负债合计期末余额（不得用 bs.total_liabilities，也不得与 bs.total_current_liabilities_period_begin 取平均）；须先校验分母 > 0，否则按 undefined 拒答，分子为负则是有效的负值结果。

## Q3
metric_id: revenue_growth_yoy
answerable: yes
source_fields: is.operating_revenue_current, is.operating_revenue_prior_as_presented
formula: (is.operating_revenue_current - is.operating_revenue_prior_as_presented) / is.operating_revenue_prior_as_presented
period_semantics: 时段
flags: restated
reason: 上期数固定取 2023 年报中列示的 2022 年比较金额（重述后数），不得取 is.operating_revenue_prior_as_originally_reported；提问已说明两者不一致，按 common_pitfalls 必须标记 restated=true；同时须确认报表列示的是"营业收入"而非仅有"营业总收入"，且分母 > 0，否则转 undefined。

## Q4
metric_id: revenue_growth_yoy
answerable: no
source_fields: NONE
formula: NONE
period_semantics: NONE
flags: undefined
reason: 比较期营业收入缺失（当年新上市、首次披露，notes.listing_first_disclosure_flag 为真），命中 undefined_conditions 中"is.operating_revenue_prior_as_presented 缺失 → 拒答"，且明确规定不得按 0 处理，因此不给出任何增长率。

## Q5
metric_id: NONE
answerable: no
source_fields: NONE
formula: NONE
period_semantics: NONE
flags: undefined
reason: 给定的三份口径定义中不存在存货周转天数与应收账款周转率，按"仅依据给定口径"要求不得用行业惯例自行补定义；且字段清单只有 bs.inventory、bs.accounts_receivable 的单一时点余额，没有期初余额或平均余额字段，也没有期间天数约定，即便补定义也无法计算。

## 定义缺陷

1. **缺少期间标识字段。** 三份定义都声明了 period_semantics，但字段清单中没有任何 fiscal_year / period_type / report_type 键。无法从字段层面确认取到的是 2023 年度数而非季度累计数，也无法机械保证口径 2 的分子（本期累计）与分母（期末余额）来自同一报告期。Q1、Q2 的"2023 年""一年"实际上是靠上下文假定的，不可验证。

2. **缺少"字段缺失"的表示约定。** 口径 2 的"报表未单独列示流动负债合计"、口径 3 的"仅列示营业总收入而无营业收入"都是 undefined 触发条件，但字段清单里这些字段一律存在。定义没有规定缺失如何表达（null / 缺键 / 0），导致这两条 undefined 条件在数据层不可判定——而 0 与缺失在这里的后果完全相反。

3. **口径 1 与附注分项字段的关系未定义。** 清单同时给了 notes.nonrecurring_pl_total_pretax、notes.nonrecurring_pl_tax_effect、notes.nonrecurring_pl_minority_effect。当归母净额未披露而三个分项齐全时，是否允许按"税前合计 − 所得税影响 − 少数股东部分"倒推？定义只禁止直接使用税前合计，对倒推既未允许也未禁止。当前只能 fail-closed 拒答，但这是定义漏洞而非有意选择。

4. **非经常性损益的符号约定未声明。** 公式是减法，但附注披露的"非经常性损益净额"在净损失年度是负数还是以绝对值列示，定义没有规定。符号约定错一次，扣非利润的方向就整体反了，这是可直接产生错误数值的歧义。

5. **restated 的判定路径重复且未定优先级。** 口径 3 可以用"is.operating_revenue_prior_as_presented ≠ is.operating_revenue_prior_as_originally_reported"判定，也可以用 notes.restatement_flag 判定。两者冲突时以哪个为准没有规定。口径 1 的 restated 更麻烦：它是单期指标，清单里只有 notes.restatement_flag（描述为"比较期是否经追溯重述"），没有"本期数是否为重述后数"的判定字段。

6. **is.operating_revenue_prior_as_originally_reported 的描述自相矛盾。** 字段名说"上期"，描述却写"上年年报当时原始披露的**本年**金额"。按口径 3 的语境应指上年年报中披露的上年自身金额（即本期报表的比较期对应年度），但字面读不通，需要澄清后才能安全用于 restated 判定。

7. **notes.business_combination_type 没有取值枚举。** 口径 3 要求"同一控制下合并 → scope_change=true，非同一控制不追溯"，但该字段的合法取值（同一控制 / 非同一控制 / 无 / 多类并存）未定义，也未说明一期内发生多笔不同类型合并时如何取值，无法机械判定。

8. **flags 没有取值域与序列化规范。** restated / scope_change / undefined 的确切拼写、多个 flag 并存时的表示方式、undefined 是 flag 还是终止状态，三份定义都没有统一规定，跨指标聚合时会不一致。

9. **口径 1 的"跨版本不可比"没有落到可执行约束上。** pitfall 说非经常性损益项目清单随证监会公告版本变化、跨版本年度不得直接比较，但既没有记录版本的字段（如 standard_version），也没有对应的 flag 名或 undefined 条件。这条警告目前无法机械执行。

10. **别名过宽，存在跨指标误匹配风险。** 口径 2 的 aliases 含"现金流量比率"，这是市场上多义的叫法（可指总负债口径、平均口径、利息保障类指标）。定义自己也承认该比率不由准则规定、分母口径存在多个变体，却用最泛的别名去接自然语言提问，容易把"用总负债"或"用平均数"的提问错误路由到本口径。

11. **营运能力类指标整体缺失，且字段结构不支持补齐。** 没有周转率/周转天数口径（Q5 因此拒答）。即使后续补写，清单只有 bs.inventory、bs.accounts_receivable 的期末时点值，缺期初余额与平均余额，也缺天数基数（365/360）与期间实际天数约定，补定义前必须先扩字段。

12. **口径 2 缺分子侧的边界规定。** 只规定了分母 ≤ 0 拒答、分子为负有效，但分子恰为 0、或经营活动现金流量净额本身缺失时如何处理未作规定。
