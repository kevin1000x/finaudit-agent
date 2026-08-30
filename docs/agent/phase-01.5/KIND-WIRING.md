# `column_header` / `unit` / `currency` 对一个复选框字段意味着什么

`N-43` 判据 3 的前置设计问题。**回答它是接线的前提**——
拿手边能求值的东西给复选框字段凑一个 `unit`，就是 `F-2` 本身。

写于 2026-08-31，Phase 1.5 收口之后。

---

## 0. 一句话答案

**没有一个统一答案。三支 `kind` 的答案互不相同，而这件事本身就是结论。**

想要一个统一答案，就只能取「都填某个占位值」或「都留空」——
前者是 `F-2`，后者会把 `COLUMN_HEADER_PRESENCE` 真正有内容的那一格也抹掉。

## 1. 先把问题问准

`unit` 与 `currency` 回答的是：**这个数值的计量口径是什么。**
`column_header` 回答的是：**这个值取自版面上的哪一列。**

对一个布尔字段问「它的单位是什么」，**不是「答案未知」，是问题本身没有意义**——
它没有量纲。这与 `D-028` 拒绝掉的那个 `无` 哨兵值是**同一个范畴错误**：

> `D-028`：「在集合域里放一个『无』，是把『没有元素』写成『有一个叫「没有」的元素』。」

照搬到这里：**在 `unit` 里填一个表示「没有单位」的字符串，
是把「没有单位」写成「单位是『没有单位』」。**
⇒ 不许填 `"无"` / `"不适用"` / `"-"` / `"N/A"`。
（顺带一提，这几个串正好都在 `pipeline.PLACEHOLDER_TEXTS` 黑名单里，
`AC-05` 的齐全率会把它们判成缺口——**我们自己的门禁已经在拦这条路了**。）

## 2. 逐支 `kind` 的答案

| `kind` | 取值 | `column_header` | `unit` | `currency` | `page` / `anchor_page` |
|---|---|---|---|---|---|
| `STATEMENT_LINE` | 金额 | **有**：版面上印的那串字（`2023年12月31日`） | **有** | **有** | **都有** |
| `KPI_DISCLOSED` | 已披露指标值 | **有** | **有**（`%`） | **有**/无，看指标 | **都有** |
| `NOTE_CHECKBOX` | 布尔 / 集合 | **没有** | **没有** | **没有** | **都有** |
| `COLUMN_HEADER_PRESENCE` | 布尔 | 🔴 **有，而且它是本字段的核心** | **没有** | **没有** | **都有** |
| `REPORT_METADATA` | 整数（月） | **没有** | 「月」 | **没有** | 🔴 **都没有** |

### 2.1 `NOTE_CHECKBOX`：三个都没有

复选框不在任何「列」里。版面形态是 `□适用  √不适用` 紧跟在子项标题下面，
**它是一行的两个并列勾选框，不是一张表的某一列**。
布尔没有量纲，也没有币种。⇒ 三个都是**不适用**，不是「未知」。

它**有页码**：`ScopeChangeReading` 已经带着 `anchor_page`（章节标题页）
与 `page`（命中行页），形状与 `D-019` 完全对得上。

### 2.2 `COLUMN_HEADER_PRESENCE`：`column_header` 不但有，而且是全部内容

**这一支最容易被「三个都填不出来」一句话带过去，而那是错的。**

`notes.restatement_flag` 判的是「`调整后` 这个列头在不在」。
所以它的 `column_header` = **`调整后`**——**逐字就是被判存在性的那个串**。

⚠️ 但语义与行值类**方向相反**：
- 行值类：`column_header` 是「**我从哪一列取的数**」
- 本支：`column_header` 是「**我找的是哪个列头**」，而字段的值就是「找到了没有」

两者共用一个字段名而语义不同，是**必须写进 docstring 的一处歧义**，
不写的话下一个人会拿它去做「取数列」的下游推断。

`unit` / `currency` 仍然没有——「某个列头在不在」是布尔。

### 2.3 `REPORT_METADATA`：它根本不该进 `records`

`notes.reporting_period_months` 由**报告类型**决定，`PROBE-14 §3` 实测
整份 143 页逐行搜四个候选串**全部零命中**——**它不在纸上**。

`ExtractionRecord` 的 docstring 第一句写的是
「一个字段的**一次抽取**，连同一次独立复核所需的全部出处」。
**一个从未被抽取过的值放进抽取记录，是记录类型本身的范畴错误**，
而不是「它的某几个字段填不出来」。

⇒ **本支不进 `batch.records`。**

但**不许静默跳过**——`pipeline` 现有注释已经点明这条：
「跳过会让那些字段静默地不出现在批次里，而调用方看到的是一个『成功』的批次，只是少了几条记录。」

⇒ 处置：批次新增一个**与 `records` 并列的** `derived` 集合，
装 `reporting_period_months_provenance()` 已经产出的那份 dict
（它自带 `derived: True` / `extracted_from_layout: False` / 逐字理由）。
**在批次里看得见，但不冒充抽取。**

## 3. 这对 `ExtractionRecord` 的形状意味着什么

### 3.1 关键区分：**必需参数 ≠ 非空值**

`ARCHITECTURE` §8.5 的实证是「**可选**出处一定会在接线时被丢掉」
（hello-agents 的 `full_output_path` 形状完全正确、唯二两个调用点全部丢弃）。
`record.py` 据此把每个字段都写成**必需位置参数，没有一个有默认值**。

**防丢的性质来自「没有默认值」，不来自「必须非空」。** 这两件事被现有实现合并了：
`_require_text` 同时拒绝 `None` 和空串。

⇒ 一个 `str | None` 的**必需位置参数**同样丢不掉：写入方必须**显式写 `None`**，
漏写仍然是 `TypeError`。**把「不适用」表达出来，不需要放弃防丢。**

### 3.2 fail-closed 改成**双向**且**按 kind**

现在只拦一个方向（不许为空）。改完之后两个方向都拦：

| `kind` | `column_header` | `unit` | `currency` |
|---|---|---|---|
| `STATEMENT_LINE` / `KPI_DISCLOSED` | 必须非空文本 | 必须非空文本 | 必须非空文本 |
| `COLUMN_HEADER_PRESENCE` | 必须非空文本 | 必须是 `None` | 必须是 `None` |
| `NOTE_CHECKBOX` | 必须是 `None` | 必须是 `None` | 必须是 `None` |

**这比今天更严，不是更松**：今天 `unit="元"` 盖在一个复选框记录上是**能构造出来的**，
改完之后它会 `ValueError`。⇒ `F-2` 在这个字段上从「靠人记得」变成「构造边界拦住」。

### 3.3 与已接受决策的关系（逐条核过，不是「应该没冲突」）

| 决策 | 是否受影响 | 理由 |
|---|---|---|
| **`D-019`**（页码拆两个整数） | **不受影响** | 上表两支进 `records` 的 `kind` **都有真实页码**。唯一没有页码的 `REPORT_METADATA` 按 §2.3 **不进 `records`**，因此 `page` / `anchor_page` 保持 `int`，不放开 `None` |
| **`D-023`**（`selection` 三元组不可为空） | **不受影响** | 三元组照填。复选框的取数口径是真实存在的：`sampling` = 该章节整节逐行、`order_key` = `page,y`、`truncation` = 未截断 |
| **`D-024`**（批次身份） | 不受影响 | 同批次同 `batch_id` |
| **`L-34`**（口径类开关不设默认值，缺失即 fail-closed） | 🟡 **细化，不是推翻** | 「不设默认值」**完全保留**（仍是必需位置参数）；「缺失即 fail-closed」也保留 —— 只是**「缺失」的定义变成按 `kind` 判**。对一个没有量纲的字段，`unit` 不是「缺失」，是**不适用**。⚠️ 这一条是本设计里唯一动了既有措辞的地方，**单独标出来** |
| **`L-35`**（类别由显式 `kind` 判定） | **被加强** | 新的校验表**按 `kind` 分支**，`kind` 从「只是个标签」变成「决定哪些字段必须在」的判据 |
| **`AC-05`** 齐全率 | 需同步 | `REQUIRED_EVIDENCE_KEYS` 必须**按 `kind` 取**，否则每条 note 记录会平白记 3 处缺口，把齐全率拉到永远不可能是 1 —— 与 `value` / `cell_state` 被排除在外是同一个理由（**不能让一个正确的抽取器达不到 `AC-05`**） |

## 4. 接线之后实测到的效果（2026-08-31，同日落地）

**这一节是事后补的实测，不是设计时的预期。**

| | 接线前（只跑三大表） | 接线后（+ notes 两步） |
|---|---:|---:|
| 批次记录数 | 25 | **28** |
| `batch.derived` | 0 | **1** |
| `flags_status = evaluated` | 6 | **18** |
| `flags_status = unevaluable` | **12** | **0** |
| `RefusalCode.UNAVAILABLE` | 2 | 2 |

🔴 **`unevaluable` 是 12 不是 6。** 交接文档与台账此前都写「6 个指标的 `unevaluable`
现状不变」——**那个 6 是错的**，实测 12。数字来源已无从追溯，
但方向没错（接线前确实全判不了）。**在这里改正，不在别处沿用。**

**11 个指标真实置位了 flag**（不是「没有 flag」，是**判出来了且确实该置位**）：
`restated` 置位 10 个（`current_ratio` / `debt_to_asset_ratio` / `gross_profit_margin` /
`net_profit_margin_attributable` / `net_working_capital` / `ocf_to_net_profit_attributable` /
`period_expense_ratio` / `quick_ratio` / `return_on_total_assets` / `revenue_growth_yoy`），
`scope_change` 置位 1 个（`minority_interest_share`）。
⇒ **`A-8` 那处真实假阴性的端到端确认**：茅台 2023 企业合并三项全不适用、
而「其他原因的合并范围变动」适用，`scope_change` 现在真的置位了。

**剩下 2 个 `UNAVAILABLE` 不是本次没做完，是明确 out of scope**：
`net_profit_attributable_excl_nonrecurring` 要 `notes.nonrecurring_pl_net_attributable_to_parent`、
`roe_weighted_average` 要 `kpi.roe_weighted_average_disclosed` ——
**两个都是行值类**，要一个「非三大表章节」的 `StatementView`，
而 `read_statement` 找的是**报表**锚点，给不出。接它们要先让 `locate` 能对**章节**
做同样的锚点 + 行重组，那是另一件事。**不硬塞**：塞进来会抛 `SheetHeaderNotFound`，
而那个异常的字面意思是「版面与实测形态不符」——一个**与真实原因无关**的报错。

### 4.1 接线当天炸出来的两处，都是真的

1. **列绑定闸门报了一条假的不符。** 接上之后 `notes` 命名空间立刻 `passed=false`，
   唯一的 mismatch 是 `(notes.restatement_flag, 调整后, null, 调整后)` ——
   **版面串与要的口径逐字相同却判不符**，这本身就是判据用错了对象的信号。
   根因正是 §2.2 记的那处语义相反：拿 `locate.role_of` 去解一个「被判存在性的列头」，
   必然解出 `None`。已按 `kind` 显式排除，并**逐条记进 `not_applicable` 加理由**
   （不静默 `continue` —— 静默跳过的字段在证据里与「不存在这个字段」不可区分，
   复核 `RV-3` 的形状）。
2. **派生值不并进求值行，那条 flag 就判不了。** `period_length_mismatch` 的 trigger 是
   `notes.reporting_period_months != 12`，而该值只在 `batch.derived` 里。
   不并进去 ⇒ 操作数缺失 ⇒ `operating_cash_flow_ratio` 整条记 `unevaluable`,
   **而那个值其实是知道的**。「知道但没告诉求值器」和「不知道」在证据里长得一样。
   已并入求值行，**但仍不进 `records`** —— 证据侧照旧带 `derived: True` /
   `extracted_from_layout: False`，复核者不会被引去年报上找那一行。

## 5. 这条设计**没有**回答什么

- **不回答「`flags_status` 该不该阻断计算」。** 那是接线之后才谈得上的下一个问题，
  判据仍是「`restated` 真取到值之后 `unevaluable` 还剩几个」，不是「要不要更严格」。
- **不回答跨排版稳健性。** `restated` 的规则仍是单样本
  （`VERIFICATION.md` §C.7：反例形态一次都没观察到，也没有去找）。
  接线**不会**让那条限定变弱。
- **不引入任何新的 `kind`。** 五支就是五支。
