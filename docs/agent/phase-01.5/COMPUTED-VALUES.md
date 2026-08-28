# COMPUTED-VALUES —— 20 份口径定义第一次吃到真实数据

**阶段**：Phase 1.5 wave 4 Task 1（`01.5-04-PLAN.md`）　**日期**：2026-08-27
**样本**：贵州茅台（600519）2023 年年度报告
**PDF SHA-256**：`2125ff97a452ea79b0d784e2432f7d224b6aecc330b644b593477d69e22f4ed1`
**批次**：`61e881c77f3d4771`（跨三张合并报表，**25 条记录，一个批次**）
**勾稽闸门**：`272,699,660,092.25 = 49,043,190,797.43 + 223,656,469,294.82`，差额 **0.00**
**列绑定校验**：`bs` / `is` / `cfs` 三份映射表全部 `passed = true`

> **按 SC-8：本文件列值，不列「8/8 算出」。** 每个指标一节，每节含全部输入字段的
> 取值与页码、算出的数值、**手算复核**、以及可比性标记的判定结果。

**重跑命令**：

```bash
.venv/Scripts/python -m extractor compute --metric debt_to_asset_ratio --metric current_ratio --metric quick_ratio --metric net_working_capital --metric interest_bearing_debt_ratio --stock 600519 --year 2023 --json
```

`--metric` 可重复。不给 `--namespace` 时按三张合并报表全抽（跨表指标需要）；
加 `--pdf data/raw/600519_2023.pdf` 可读本地文件不联网。

---

## §1 逐指标

### 1. `debt_to_asset_ratio` 资产负债率 = **0.1798432413917914711797119101**

`formula`：`bs.total_liabilities / bs.total_assets`

| 输入字段 | 取值 | 页 | 列 |
|---|---:|---:|---|
| `bs.total_liabilities` | 49,043,190,797.43 | 60 | `2023年12月31日` |
| `bs.total_assets` | 272,699,660,092.25 | 59 | `2023年12月31日` |

**手算复核**：`49,043,190,797.43 ÷ 272,699,660,092.25 = 0.17984324139…` ✅ 一致。
两个被除数逐字在证据链里，复核者**不重跑就能验算**。

### 2. `current_ratio` 流动比率 = **4.623892443179299031292014007**

`formula`：`bs.total_current_assets / bs.total_current_liabilities_period_end`

| 输入字段 | 取值 | 页 | 列 |
|---|---:|---:|---|
| `bs.total_current_assets` | 225,172,517,821.28 | 59 | `2023年12月31日` |
| `bs.total_current_liabilities_period_end` | 48,697,611,501.20 | 60 | `2023年12月31日` |

**手算复核**：`225,172,517,821.28 ÷ 48,697,611,501.20 = 4.6238924431…` ✅ 一致。

### 3. `quick_ratio` 速动比率 = **3.670351116817004026158851655**

`formula`：`(bs.total_current_assets − bs.inventory) / bs.total_current_liabilities_period_end`

| 输入字段 | 取值 | 页 | 列 |
|---|---:|---:|---|
| `bs.total_current_assets` | 225,172,517,821.28 | 59 | `2023年12月31日` |
| `bs.inventory` | 46,435,185,061.53 | 59 | `2023年12月31日` |
| `bs.total_current_liabilities_period_end` | 48,697,611,501.20 | 60 | `2023年12月31日` |

**手算复核**：分子 `225,172,517,821.28 − 46,435,185,061.53 = 178,737,332,759.75`；
`178,737,332,759.75 ÷ 48,697,611,501.20 = 3.6703511168…` ✅ 一致。

### 4. `net_working_capital` 营运资本 = **176,474,906,320.08 元**

`formula`：`bs.total_current_assets − bs.total_current_liabilities_period_end`

| 输入字段 | 取值 | 页 | 列 |
|---|---:|---:|---|
| `bs.total_current_assets` | 225,172,517,821.28 | 59 | `2023年12月31日` |
| `bs.total_current_liabilities_period_end` | 48,697,611,501.20 | 60 | `2023年12月31日` |

**手算复核**：`225,172,517,821.28 − 48,697,611,501.20 = 176,474,906,320.08` ✅ 一致。
⚠️ 这是本批唯一**有量纲**的指标：单位 `元`、币种 `人民币`（不是「无量纲」）。
`_is_ratio` 只认最外层是除法，减法结果保留输入的单位 —— 这是对的。

### 5. `interest_bearing_debt_ratio` 有息负债率 = **0.001186987594375806682042917962**

`formula`：六个分项之和 ÷ `bs.total_assets`

| 输入字段 | 取值 | 页 | 列 | 格子状态 |
|---|---:|---:|---|---|
| `bs.short_term_borrowings` | 0.00 | 59 | `2023年12月31日` | **EMPTY_CELL** |
| `bs.trading_financial_liabilities` | 0.00 | 59 | `2023年12月31日` | **EMPTY_CELL** |
| `bs.non_current_liabilities_due_within_one_year` | 57,054,879.48 | 60 | `2023年12月31日` | VALUE_PRESENT |
| `bs.long_term_borrowings` | 0.00 | 60 | `2023年12月31日` | **EMPTY_CELL** |
| `bs.bonds_payable` | 0.00 | 60 | `2023年12月31日` | **EMPTY_CELL** |
| `bs.lease_liabilities` | 266,636,234.04 | 60 | `2023年12月31日` | VALUE_PRESENT |
| `bs.total_assets` | 272,699,660,092.25 | 59 | `2023年12月31日` | VALUE_PRESENT |

**手算复核**：分子 `57,054,879.48 + 266,636,234.04 = 323,691,113.52`；
`323,691,113.52 ÷ 272,699,660,092.25 = 0.00118698759…` ✅ 一致。

🔴 **这是 `A-2` 的判据**：四个分项**行印在报表上、格子是空的**。
按 `is_missing` 一律拒答的话，这个数根本算不出来 ——
而正确答案就是这个接近零的比率。`metrics/` **一个字都没改**，修的是抽取层。

### 6. `gross_profit_margin` 毛利率 = **0.919649372413579757379092352**

`formula`：`(is.operating_revenue_current − is.operating_cost) / is.operating_revenue_current`

| 输入字段 | 取值 | 页 | 列 |
|---|---:|---:|---|
| `is.operating_revenue_current` | 147,693,604,994.14 | 63 | `2023年度` |
| `is.operating_cost` | 11,867,273,851.78 | 63 | `2023年度` |
| `is.operating_revenue_current`（第二次出现） | 147,693,604,994.14 | 63 | `2023年度` |

⚠️ **`inputs` 里同一个字段出现两次不是 bug**：`field_refs` 按**出现顺序、可重复**列出
语法树里的字段引用，而这条公式引用了 `operating_revenue_current` 两次（分子里一次、分母里一次）。
去重会让证据链与公式对不上。

**手算复核**：分子 `147,693,604,994.14 − 11,867,273,851.78 = 135,826,331,142.36`；
`135,826,331,142.36 ÷ 147,693,604,994.14 = 0.91964937241…` ✅ 一致（91.96%）。
🔴 **外部对照**：茅台公开披露的 2023 年毛利率为 **91.96%**，量级与小数点后两位吻合。

⚠️ **注意分母是「营业收入」不是「营业总收入」**。用营业总收入（150,560,330,316.45）
算出来是 92.12%，差 0.16 个百分点 —— 一个**看起来完全正常**的错数。
映射表逐字写的是 `其中：营业收入`，理由见 `PROBE-14.md` §1(a)。

### 7. `period_expense_ratio` 期间费用率 = **0.08523388089246972163777**

`formula`：`(销售费用 + 管理费用 + 财务费用) / is.operating_revenue_current`

| 输入字段 | 取值 | 页 | 列 |
|---|---:|---:|---|
| `is.selling_expense` | 4,648,613,585.82 | 63 | `2023年度` |
| `is.administrative_expense` | 9,729,389,252.31 | 63 | `2023年度` |
| `is.financial_expense` | **-1,789,503,701.48** | 63 | `2023年度` |
| `is.operating_revenue_current` | 147,693,604,994.14 | 63 | `2023年度` |

**手算复核**：分子 `4,648,613,585.82 + 9,729,389,252.31 − 1,789,503,701.48 = 12,588,499,136.65`；
`12,588,499,136.65 ÷ 147,693,604,994.14 = 0.08523388089…` ✅ 一致（8.52%）。

⚠️ **财务费用是负数**（利息收入大于利息支出），它**拉低**了期间费用率。
`sign_convention: 收益记正_损失记负` 在这里第一次真的起作用 ——
若按绝对值列报处理，结果会是 11.94%，高出 3.4 个百分点。

### 8. `free_cash_flow` 自由现金流 = **63,973,491,832.30 元**

`formula`：`cfs.net_cash_flow_from_operating_activities − cfs.cash_paid_for_fixed_intangible_and_other_long_term_assets`

| 输入字段 | 取值 | 页 | 列 |
|---|---:|---:|---|
| `cfs.net_cash_flow_from_operating_activities` | 66,593,247,721.09 | 67 | `2023年度` |
| `cfs.cash_paid_for_fixed_intangible_and_other_long_term_assets` | 2,619,755,888.79 | 67 | `2023年度` |

**手算复核**：`66,593,247,721.09 − 2,619,755,888.79 = 63,973,491,832.30` ✅ 一致。

---

## §2 🔴 可比性标记的判定：8 个里 6 个**判不了**

`STATE.md` 点名要验的那件事：**元规则 19.0% 只说明大部分陷阱写成了可求值规则，
不说明规则会正确触发。** 接上真实字段跑一次 `active_flags()`：

| 指标 | `flags_status` | 置位的标记 |
|---|---|---|
| `debt_to_asset_ratio` | **`unevaluable`** | —— |
| `current_ratio` | **`unevaluable`** | —— |
| `quick_ratio` | **`unevaluable`** | —— |
| `net_working_capital` | **`unevaluable`** | —— |
| `gross_profit_margin` | **`unevaluable`** | —— |
| `period_expense_ratio` | **`unevaluable`** | —— |
| `interest_bearing_debt_ratio` | `evaluated` | **一个都没触发** |
| `free_cash_flow` | `evaluated` | **一个都没触发** |

**判不了的原因逐字**：

```
标记 'restated' 的触发条件求值失败：'notes.restatement_flag == true'：
比较运算的操作数 notes.restatement_flag 在数据中缺失
```

`notes.restatement_flag` 的 `kind` 是 `COLUMN_HEADER_PRESENCE`，
`pipeline` 的分派点对它抛 `NotImplementedError`（wave 5 实现），
所以它**不在批次里**。

### 这不是 bug，`active_flags` 正在做它该做的事

它的 docstring 写着「求值不了 → 整体拒答，不跳过」，理由是
「漏掉一个 `affects_comparability` 为真的标记，等于让一次本该被阻断的跨期比较悄悄通过」。
**它是对的。**

### 🔴 真正的缺口：数值算得出来，标记判不了，两者之间没有接线

`compute_metric` **本来根本不调 `active_flags`**。
补 `flags_status` 之前，一个「资产负债率 = 0.1798」被产出时，
**没有任何东西告诉调用方这个数的 `restated` 状态未知**。

那是 `ARCHITECTURE` §8.5 的形状，只是方向不同：
不是指针被丢掉，是**两条本该耦合的路径根本没接线**。

⚠️ **本轮把它接进证据链，但不让它阻断计算。** 理由如实写：
接上阻断就有 6 个指标全数拒答，SC-5 直接不成立。
该不该阻断要等 wave 5 把那三支 `kind` 实现之后、拿真实取值再定 ——
**现在定就是在没有数据的情况下拍板**。但缺口必须在证据链里看得见，
所以 `flags_status` 是 `ComputeResult` 的一等字段而不是一句注释。

⚠️ **`flags = []` 在两种情形下含义相反**：
`evaluated` 时它表示「一个都没触发」，`unevaluable` 时它表示「判不了」。
混成一个空集就再也分不开了 —— 这就是为什么必须有 `flags_status` 这个字段。

---

## §3 诚实的限定

1. **单公司单年。** 8 个数全部取自茅台 2023 一份年报。
2. **8 个指标里 6 个的可比性标记未判定**（§2）。SC-5 的「算出真实数值」达成，
   但**「这个数可不可以跨期比」这件事本轮零证据**。
3. ~~**只有毛利率有外部对照**（公开披露 91.96%）。其余 7 个是**手算复核**，
   即同一份年报数据的第二次算术，**不是跨源验证**。跨源对照是 Task 3 的事。~~
   → **Task 3 已做，见 §5。** 8 个指标的**输入字段**里有 20 个拿到了跨源结论；
   但**指标值本身仍然没有跨源对照** —— AKShare 给的是科目，不是比率。
   「输入全部跨源一致」不等于「这个比率被外部验证过」，二者之间隔着我们自己的口径。
4. **`notes` / `kpi` 两个命名空间的 5 个字段没有参与任何计算** ——
   三支 `kind` 未实现。`DEFAULT_EXTRACTION_PLAN` 因此只列三张合并报表：
   把它们写进计划会在分派点抛异常，而那不是「还没做」的正确表达方式。
5. **`net_working_capital` 是本批唯一有量纲的结果**，其余七个里六个是比率（无量纲）、
   一个（自由现金流）是金额。量纲推导只认「最外层是除法」这一种形态，
   更一般的推导需要每个字段声明量纲，那是 `U-01` 的活，**不在本阶段拍板**。

## §4 对 wave 5 的硬输入

1. **三支 `kind` 的实现**（`NOTE_CHECKBOX` / `COLUMN_HEADER_PRESENCE` / `REPORT_METADATA`）
   —— 不实现，6 个指标的可比性标记永远判不了。
2. **`flags_status` 该不该阻断计算**，等那三支实现之后拿真实取值定。
   ⚠️ 那时的判据应当是「`restated` 真的取到值之后，`unevaluable` 还剩几个」，
   而不是「要不要更严格」。
3. `metrics/` 的三处编辑（`D-020` 两处 + `D-028` 一处），见 `01.5-03-SUMMARY.md` §8。

---

## §5 跨源对照（Task 3，2026-08-28）

**对照源**：`akshare:stock_financial_report_sina`，`sh600519` / 报告日 `20231231`
**容差**：`abs Decimal("0.01")` 元（`D-029`，`DISAGREEMENT_TOLERANCE`）
**权威源仍是 PDF**（`D-013`）：本节的 `AKShare 值` 一个也没有被写回抽取记录。

**重跑命令**（离线，走固件）：

```bash
.venv/Scripts/python -m extractor crosscheck --stock 600519 --year 2023 \
    --pdf data/raw/600519_2023.pdf \
    --reference tests/fixtures/akshare_600519_2023.json --json
```

### 5.1 逐字段对照结论（24 条，**这是全部，没有省略**）

| `field_id` | AKShare 列名 | PDF 值 | AKShare 值 | 绝对差 | 判定 |
|---|---|---:|---:|---:|---|
| `bs.accounts_receivable` | `应收账款` | 60373410.41 | 60373410.41 | 0.00 | AGREES |
| `bs.inventory` | `存货` | 46435185061.53 | 46435185061.53 | 0.00 | AGREES |
| `bs.total_current_assets` | `流动资产合计` | 225172517821.28 | 225172517821.28 | 0.00 | AGREES |
| `bs.total_assets` | `资产总计` | 272699660092.25 | 272699660092.25 | 0.00 | AGREES |
| `bs.short_term_borrowings` | `短期借款` | 0 | — | — | **INCOMPARABLE / REFERENCE_NAN** |
| `bs.trading_financial_liabilities` | `交易性金融负债` | 0 | — | — | **INCOMPARABLE / REFERENCE_NAN** |
| `bs.long_term_borrowings` | `长期借款` | 0 | — | — | **INCOMPARABLE / REFERENCE_NAN** |
| `bs.bonds_payable` | `应付债券` | 0 | — | — | **INCOMPARABLE / REFERENCE_NAN** |
| `bs.accounts_payable` | `应付账款` | 3093091103.67 | 3093091103.67 | 0.00 | AGREES |
| `bs.non_current_liabilities_due_within_one_year` | `一年内到期的非流动负债` | 57054879.48 | 57054879.48 | 0.00 | AGREES |
| `bs.lease_liabilities` | `租赁负债` | 266636234.04 | 266636234.04 | 0.00 | AGREES |
| `bs.total_current_liabilities_period_end` | `流动负债合计` | 48697611501.20 | 48697611501.2 | 0.00 | AGREES |
| `bs.total_liabilities` | `负债合计` | 49043190797.43 | 49043190797.43 | 0.00 | AGREES |
| `bs.minority_interests` | `少数股东权益` | 7987897687.39 | 7987897687.39 | 0.00 | AGREES |
| `bs.total_equity` | `所有者权益(或股东权益)合计` | 223656469294.82 | 223656469294.82 | 0.00 | AGREES |
| `is.operating_revenue_current` | `营业收入` | 147693604994.14 | 147693604994.14 | 0.00 | AGREES |
| `is.operating_cost` | `营业成本` | 11867273851.78 | 11867273851.78 | 0.00 | AGREES |
| `is.selling_expense` | `销售费用` | 4648613585.82 | 4648613585.82 | 0.00 | AGREES |
| `is.administrative_expense` | `管理费用` | 9729389252.31 | 9729389252.31 | 0.00 | AGREES |
| `is.financial_expense` | `财务费用` | -1789503701.48 | -1789503701.48 | 0.00 | AGREES |
| `is.net_profit` | `净利润` | 77521476277.80 | 77521476277.8 | 0.00 | AGREES |
| `is.net_profit_attributable_to_parent` | `归属于母公司所有者的净利润` | 74734071550.75 | 74734071550.75 | 0.00 | AGREES |
| `cfs.net_cash_flow_from_operating_activities` | `经营活动产生的现金流量净额` | 66593247721.09 | 66593247721.09 | 0.00 | AGREES |
| `cfs.cash_paid_for_fixed_intangible_and_other_long_term_assets` | `购建固定资产、无形资产和其他长期资产所支付的现金` | 2619755888.79 | 2619755888.79 | 0.00 | AGREES |

**批次汇总**：可比 **20** / 不可比 **4** / 不一致 **0**。
触发占比 **0/20 = 0**，未超过 `D-029` 的反转阈值 `1/3` ⇒ **不疑档位选错**。

### 5.2 那 4 个「不可比」是本节最重要的结果

它们不是失败，是**一次被拦下来的伪造一致**。

这四个字段正是 `A-2` 那四个「行印在报表上、格子是空的」的字段。
PDF 侧按 `SC-3` 判为 `EMPTY_CELL` ⇒ 取值 **0**；
AKShare 侧这四列全是 **`NaN`**。

**把 `NaN` 当成 0，它们会与 PDF 侧的 0 比出 `AGREES`** ——
输出里会多出四条「跨源一致」，而那四条一致**从未被任何证据建立过**。
那正是本项目已经记了六次的形状：自证机制说通过了，但它证明的不是它声称证明的事。

⇒ `C-7` 要求的「`NaN` 语义显式决定」，决定是：
**`REFERENCE_NAN` 判不可比**，`source_disagreement` 不置位，且理由进证据链。

### 5.3 一处「数值对照挡不住、只有逐字相等挡得住」的实例

`应付票据及应付账款` = `3,093,091,103.67`，`应付账款` = `3,093,091,103.67` ——
**本样本上这两列的值完全相等**（茅台没有应付票据）。

cninfo 的第三处真实错误映射就是把这个合并列映射到 `bs.accounts_payable`
（`references/cninfo.md:204-213`）。若我们照抄，
**这一批的对照结论会是 `AGREES / 差 0.00`，看起来完全正常。**

⇒ **「跑一遍看数对不对」在这里是无效的验证方式。**
挡住它的只有映射表的逐字相等，以及 `tests/test_crosscheck.py` 里
那条断言两列取值相等、因而错配不可能被数值发现的负向用例。

### 5.4 覆盖度：24 / 30，缺的 6 个是结构性的不是漏

| 缺的字段 | 为什么 AKShare 给不出 |
|---|---|
| `notes.business_combination_type` | 附注复选框，不是报表行 |
| `notes.restatement_flag` | 判的是列头在不在，接口只返回一期 |
| `notes.reporting_period_months` | 报告元数据，纸上不印这一行 |
| `notes.nonrecurring_pl_net_attributable_to_parent` | 非经常性损益明细在附注 |
| `kpi.roe_weighted_average_disclosed` | 主要会计数据节的披露值，不在三张表里 |
| `is.operating_revenue_prior_as_presented` | 要的是**本期报表上印的上期数**；接口一行一期，只能给「上一期自己的本期数」。**发生追溯重述时两者恰好不同**，拿后者冒充前者会把重述抹平成一致 |

⇒ 对照映射的方向断言是**子集**（`assert_akshare_mapping_within_definitions`），
不是 PDF 侧那种**相等**。要求相等就得为这 6 个编出永远取不到值的规则，那是 `F-2`。

### 5.5 诚实的限定（必须随 §5 的结论一起转述）

1. **20 个 `AGREES` 全部来自同一家公司、同一年、同一个接口**（新浪源）。
   `AKSHARE-A2 §4` 的限定原样继续成立。
2. **本批差额全部精确为 `0.00` ⇒ 它仍然无法用来标定阈值。**
   容差取 `0.01` 还是 `1000`，在这份数据上结论一样。
   `D-029` 的自我纠错机制是那个占比，不是这批数据。
3. **`disagreement_ratio = 0` 的分母是 20，不是 24。** 分母只算可比的那些。
   报「占比 0」时必须同时说分母 —— 否则「20 个里 0 个不一致」
   会被读成「24 个字段全部核对通过」，而其中 4 个根本没核。
4. **`DISAGREES` 这一支在真实数据上零样本。** 它只有构造样本（测试里）。
   与 `ROW_ABSENT` 同一处境：路径写了、测试锁了，**但真实年报上没触发过**。
5. **指标值本身没有跨源对照。** AKShare 给的是科目不是比率；
   `gross_profit_margin` 与公开披露 91.96% 的吻合仍是本项目唯一一次指标级外部对照。
