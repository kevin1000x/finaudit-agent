# 可用字段清单 — POC-01

> ⚠️ **偏离说明**：`docs/agent/POC.md` 的输入项写的是「`cninfo` 已有的年报数据字段清单」。
> 执行时 `cninfo-financial-analyzer` 仓库不在本机（已搜 `Documents` / `Desktop` / `D:\` / 项目根，无结果）。
> 本清单改为按**中国企业会计准则规定的合并报表列报项目**构造，来源全部公开。
> POC-01 检验的是「口径定义能否消除取数分歧」，不是「字段名与 cninfo 是否一致」，
> 因此该替代不影响实验有效性，但属于已记录的偏离。

回答者只能从下列字段中选取。字段 id 为本清单约定，不是 cninfo 实际列名。

## 合并资产负债表（bs.*）—— 时点

| id | 报表项目 |
|---|---|
| `bs.total_assets` | 资产总计 |
| `bs.total_current_assets` | 流动资产合计 |
| `bs.total_non_current_assets` | 非流动资产合计 |
| `bs.inventory` | 存货 |
| `bs.accounts_receivable` | 应收账款 |
| `bs.total_liabilities` | 负债合计 |
| `bs.total_current_liabilities_period_end` | 流动负债合计（期末余额） |
| `bs.total_current_liabilities_period_begin` | 流动负债合计（期初余额） |
| `bs.total_non_current_liabilities` | 非流动负债合计 |
| `bs.short_term_borrowings` | 短期借款 |
| `bs.total_equity` | 所有者权益（或股东权益）合计 |
| `bs.equity_attributable_to_parent` | 归属于母公司所有者权益合计 |
| `bs.minority_interests` | 少数股东权益 |

## 合并利润表（is.*）—— 时段

| id | 报表项目 |
|---|---|
| `is.total_operating_revenue_current` | 营业总收入 —— 本期金额 |
| `is.total_operating_revenue_prior_as_presented` | 营业总收入 —— 本期报表列示的上期比较金额 |
| `is.operating_revenue_current` | 营业收入 —— 本期金额 |
| `is.operating_revenue_prior_as_presented` | 营业收入 —— 本期报表列示的上期比较金额 |
| `is.operating_revenue_prior_as_originally_reported` | 营业收入 —— 上年年报当时原始披露的本年金额 |
| `is.operating_cost` | 营业成本 |
| `is.operating_profit` | 营业利润 |
| `is.total_profit` | 利润总额 |
| `is.income_tax_expense` | 所得税费用 |
| `is.net_profit` | 净利润（含少数股东损益） |
| `is.net_profit_attributable_to_parent` | 归属于母公司所有者（股东）的净利润 |
| `is.minority_interest_income` | 少数股东损益 |

## 合并现金流量表（cfs.*）—— 时段

| id | 报表项目 |
|---|---|
| `cfs.cash_inflow_from_operating_activities_subtotal` | 经营活动现金流入小计 |
| `cfs.cash_outflow_from_operating_activities_subtotal` | 经营活动现金流出小计 |
| `cfs.net_cash_flow_from_operating_activities` | 经营活动产生的现金流量净额 |
| `cfs.net_cash_flow_from_investing_activities` | 投资活动产生的现金流量净额 |
| `cfs.net_cash_flow_from_financing_activities` | 筹资活动产生的现金流量净额 |
| `cfs.cash_received_from_sales_of_goods` | 销售商品、提供劳务收到的现金 |

## 财务报表附注（notes.*）

| id | 报表项目 |
|---|---|
| `notes.nonrecurring_pl_total_pretax` | 非经常性损益项目合计（税前） |
| `notes.nonrecurring_pl_net_attributable_to_parent` | 归属于母公司股东的非经常性损益净额（已扣所得税影响及少数股东损益影响） |
| `notes.nonrecurring_pl_tax_effect` | 非经常性损益的所得税影响额 |
| `notes.nonrecurring_pl_minority_effect` | 非经常性损益中归属于少数股东的部分 |
| `notes.restatement_flag` | 比较期是否经追溯重述 |
| `notes.business_combination_type` | 企业合并类型（同一控制 / 非同一控制 / 无） |
| `notes.listing_first_disclosure_flag` | 本期是否为首次披露（无上期比较数） |
