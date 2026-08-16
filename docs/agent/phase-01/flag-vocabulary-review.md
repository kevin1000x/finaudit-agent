# Phase 1 flag 词表评审

> 模式：**VERIFY**。本文件**不修改** `metrics/_flags.yaml`——
> `openspec/changes/archive/2026-08-15-extend-metric-definition-schema/design.md` D2 要求
> 新增 flag 走独立评审，不由单个指标定义顺手引入。**本文件只产出建议。**
>
> 日期：2026-08-16　｜　对应计划：`01-08-PLAN.md` Task 1 第四步

---

## 1. 本阶段实际提出的新增 flag 请求：**零请求**

```
$ ls docs/agent/phase-01/flag-requests-*
ls: cannot access 'docs/agent/phase-01/flag-requests-*': No such file or directory
EXIT=2
```

`docs/agent/phase-01/` 下只有 `dependency-audit.md` 与 `open-questions.md`，
**没有任何 `flag-requests-*.md`**。19 份定义（wave 3 的三个批次）在编写过程中
一次都没有请求新增 flag。

### 这说明 01-01 的 10 条词表预估是准的——但要说清「准」在什么意义上

01-01 一次性定下 10 条受控 flag，此后 19 份定义零新增请求。
**这个信号是真的，但它只证明「够用」，不证明「没漏」。**
零请求也可能出自另一种机制：写定义的人发现没有合适的 flag 时，
**选择把风险标成 `advisory_only` 而不是提请求**——那条路更短，且完全合规。

下面第 3 节就找到了两处这样的例子。所以准确的结论是：

> 10 条词表在 Phase 1 的 20 个指标上**没有产生阻塞**，
> 但「零请求」不等于「零缺口」，两者之间隔着 `advisory_only` 这条泄压阀。

### 与 01-02 检查点预判的对照

`01-02-SUMMARY.md` 是本阶段唯一留下人工覆盖度预判的检查点记录。
**如实标注一处证据缺口**：01-01 / 01-04 / 01-05 / 01-07 **没有 SUMMARY 文件**
（`.planning/phases/01-semantic-layer/` 下只有 01-02 / 01-03 / 01-06 三份），
因此「各批次执行中是否曾考虑过提请求」这一点**无书面记录可查**，
本评审无法回答，记为未知而不是「没有」。

---

## 2. 10 条词表的实际引用情况

| flag | scope | 被几份定义引用 | 备注 |
|---|---|---|---|
| `restated` | definition | 多份 | 主力，`notes.restatement_flag` 可诚实求值 |
| `scope_change` | definition | **1**（`minority_interest_share`） | 见 §3.2 |
| `unaudited` | definition | 0 | B-3：留着等有字段承载 |
| `parent_only_scope` | definition | 0 | B-3 |
| `unit_scale_mismatch` | definition | 0 | B-3，**已找到承载字段**（年报页头「单位:元 币种:人民币」），待 Phase 1.5 抽取器输出 |
| `currency_mismatch` | definition | 0 | B-3 |
| `period_length_mismatch` | definition | 0 | B-3 |
| `basis_version_mismatch` | system | —— | OQ-04 裁决为 system 域，**不在定义内声明** |
| `metric_version_mismatch` | system | —— | 同上 |
| `source_disagreement` | system | —— | 同上，Phase 1.5 交叉校验时启用 |

4 条零引用的 definition 域 flag 已在台账 B-3 记录，**结论未变：留着，不删**。
删掉它们等于把「已识别的风险类别」从词表里抹掉，而承载字段的缺失是数据层问题不是词表问题。

---

## 3. 本评审的两个实际发现

这两条不是「需要新增 flag」，而是**已有 flag 或已有字段能诚实触发，却被标成了 `advisory_only`**。

它们是 `rules/failure-modes.md` **F-2 的镜像**：
F-2 是「没有字段却凑一个 trigger」，这里是「有能诚实求值的字段却不用」。
两者都让元规则的实际效力低于它的账面数字。

### 3.1 `minority_interest_share` —— `bs.total_equity < 0` 是可表达的

**实况**（我核过定义文件）：

```
fields: ['bs.minority_interests', 'bs.total_equity', 'notes.business_combination_type']
undef : is_missing(bs.total_equity)
undef : bs.total_equity == 0
```

而它的 advisory 条目原文是：

> 所有者权益合计为负（资不抵债）时，本占比在数学上仍可计算，但经济含义失真：
> 分母为负会使占比符号反转。此时应先判断持续经营能力，不宜直接解读该比率。

**`bs.total_equity` 已是声明字段，且 `== 0` 已经在用**——
这证明比较运算符在该字段上可求值。因此 `bs.total_equity < 0` 同样可求值。

「分母为负导致符号反转」是**方向性错误且数值看起来正常**，
与 POC-01 的 C4 缺陷同型——正是本项目声称要消灭的那类静默错误。
把它留在 advisory 里，意味着系统会照常给出一个符号相反的数而不作任何标记。

**建议处置：改为可求值规则。** 两种形态二选一，由 Phase 2 的词表变更流程定：
- (a) 追加 `undefined_conditions: bs.total_equity < 0` —— 直接拒答；
- (b) 追加一条 definition 域 flag —— 给出数值但标记不可解读。

**倾向 (a)**：本项目的立场一贯是「宁可拒答不可静默出错」，
而符号反转的占比不是「需要谨慎解读」，是**错的**。

### 3.2 `revenue_growth_yoy` —— `scope_change` 就是为这条情形设的

`scope_change` 在 `_flags.yaml` 里的描述**逐字**是：

> 合并范围发生变动（同一控制下合并追溯调整比较期）　`introduced_by: POC-01 C7`

而 `revenue_growth_yoy` 的 advisory 条目原文是：

> 同一控制下企业合并会追溯调整比较期，数值可比但含合并范围变动，
> 此时的同比增长不应被解读为内生增长。**本定义不自动识别合并范围变动。**

**两段说的是同一件事。** 而 `minority_interest_share` 已经用
`notes.business_combination_type != "无"` 触发了 `scope_change`——
说明该字段在本项目里已被认定为可获取。

`revenue_growth_yoy` 恰恰是**最需要**这条 flag 的定义：
同比增长率的比较基数直接受合并范围变动影响，而少数股东权益占比只是间接受影响。
**该用的地方没用，不该说是覆盖度不足。**

**建议处置：`revenue_growth_yoy` 追加 `notes.business_combination_type` 字段与
`scope_change` flag，把该条 advisory 改为 `enforced_by`。**

**须一并回答的前置问题**（不回答就不要动手）：
`notes.business_combination_type` 能否真的从年报附注抽出、取值域是什么？
目前它只在一份定义里出现，且 `notes.<任意词>` 在校验器里**不受封闭词表约束**
（同台账 B-1 记录的 `standard_basis.<任意词>` 问题）。
若该字段实际抽不出来，那么 3.2 就会变成一条 F-2 式的假规则——
**这正是必须先回答再动手的理由。**

---

## 4. 正确地留在 `advisory_only` 的部分（逐条核过，不是默认放行）

以下 advisory 条目**没有**可诚实求值的字段，标注是对的：

| 定义 | advisory 内容 | 为什么无法机械化 |
|---|---|---|
| `gross_profit_margin` | 分子分母计量单位不一致 | 报表无承载单位的字段。定义原文已明写「本定义**无法**对此设可求值规则」——这是诚实标注的范例 |
| `accounts_receivable_turnover_days` | 收入不含增值税 / 应收含税 | 无税率字段；且这是会计口径的固有偏差，任何抽取器都补不上 |
| `accounts_payable_turnover_days` | 采购额用营业成本近似 | 报表不单独列示采购额 |
| `roe_weighted_average` | 归母权益为负时含义失真 | **该定义未声明 `bs.equity_attributable_to_parent`**，其 fields 只有 `kpi.roe_weighted_average_disclosed` 与 `notes.restatement_flag`。字段不在，规则无从写起 |
| 其余 ~14 条 | 行业可比性、商业模式差异、期限结构等 | 属**解读提示**，本就不该机械化。强行做规则就是 F-2 |

⚠️ **注意 `roe_weighted_average` 与 §3.1 的 `minority_interest_share` 表面相似、结论相反。**
两者都是「权益为负」，但前者没有声明相应字段、后者声明了。
不逐份查字段而按「都是权益为负」一并处理，就会造出一条求不出值的规则——F-2 的原样重演。

---

## 5. 给 Phase 2 的处置清单

| # | 事项 | 处置建议 | 前置条件 |
|---|---|---|---|
| 1 | `minority_interest_share` 负权益 | 改为 `undefined_conditions: bs.total_equity < 0`（倾向）或 definition 域 flag | 无，字段已在 |
| 2 | `revenue_growth_yoy` 合并范围变动 | 追加字段 + `scope_change` flag | **先确认 `notes.business_combination_type` 可从附注抽出且取值域已定** |
| 3 | 新增 flag | **零条** | —— |
| 4 | 删除零引用 flag | **不删**（B-3） | —— |
| 5 | `notes.<任意词>` 命名空间未封闭 | 并入台账 B-1 一并处理 | —— |

**本文件不执行以上任何一条。** 词表与定义的变更走 OpenSpec 提案流程。
