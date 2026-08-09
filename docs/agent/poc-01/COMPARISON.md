# POC-01 机械比对与判定

- 比对时间（UTC）：`2026-08-09T16:56Z`
- 输入：`answers/answer-A.md`、`answers/answer-B.md`（均为逐字原始输出）
- 比对维度：按 `POC.md` 第 5 步规定的三项 —— `source_fields` 集合 / `formula` 结构 / `period_semantics`
- 判定阈值：取自 `POC.md`，**冻结于实验前，本次未作任何调整**

---

## 1. 逐题比对

### Q1 — 扣非归母净利润（口径层级歧义）

| 维度 | A | B | 一致 |
|---|---|---|---|
| metric_id | `net_profit_attributable_excl_nonrecurring` | 同 | ✅ |
| answerable | yes | yes | ✅ |
| source_fields | `{is.net_profit_attributable_to_parent, notes.nonrecurring_pl_net_attributable_to_parent}` | 同 | ✅ |
| formula | `A − B` | 同 | ✅ |
| period_semantics | 时段 | 时段 | ✅ |
| flags | NONE | NONE | ✅ |

**完全一致。** 两方都避开了两个陷阱：未使用 `is.net_profit`（含少数股东损益），未使用 `notes.nonrecurring_pl_total_pretax`（税前合计）。

### Q2 — 经营现金流量比率（分母歧义）

| 维度 | A | B | 一致 |
|---|---|---|---|
| metric_id | `operating_cash_flow_ratio` | 同 | ✅ |
| answerable | yes | yes | ✅ |
| source_fields | `{cfs.net_cash_flow_from_operating_activities, bs.total_current_liabilities_period_end}` | 同 | ✅ |
| formula | 分子 / 分母 | 同 | ✅ |
| period_semantics | 混合（分子时段，分母期末时点） | 混合（分子时段，分母期末时点） | ✅ |
| flags | NONE | NONE | ✅ |

**完全一致。** 措辞不同（"时段数" vs "时段值"），归一化后取值相同。两方都主动排除了 `bs.total_liabilities` 与期初期末平均，且都主动声明了分母 > 0 的前置校验。

### Q3 — 营收同比增长率（追溯重述）

| 维度 | A | B | 一致 |
|---|---|---|---|
| metric_id | `revenue_growth_yoy` | 同 | ✅ |
| answerable | yes | yes | ✅ |
| source_fields | `{is.operating_revenue_current, is.operating_revenue_prior_as_presented}` | 同 | ✅ |
| formula | `(本期 − 上期) / 上期` | 同 | ✅ |
| period_semantics | 时段 | 时段 | ✅ |
| flags | restated | restated | ✅ |

**完全一致。** 两方都拒绝使用 `is.operating_revenue_prior_as_originally_reported`，都标记了 `restated`。

### Q4 — 比较期缺失（新上市）

| 维度 | A | B | 一致 |
|---|---|---|---|
| metric_id | `revenue_growth_yoy` | 同 | ✅ |
| answerable | **no** | **no** | ✅ |
| source_fields | NONE | NONE | ✅ |
| formula | NONE | NONE | ✅ |
| period_semantics | **NONE** | **时段** | ❌ |
| flags | undefined | undefined | ✅ |
| 拒答理由 | 命中"比较期缺失 → 拒答"，不得按 0 处理 | 同 | ✅（实质相同） |

**不完全一致。** 唯一分歧在 `period_semantics`，且该项属于 `POC.md` 明列的三个比对维度，因此不计为一致，不做宽松处理。

**分歧根因**：输出契约未规定 `answerable: no` 时 `period_semantics` 指的是**指标固有语义**（B 的读法）还是**本次回答的语义**（A 的读法）。这是**输出契约缺陷，不是口径定义缺陷**——取数字段与公式两方完全一致，没有任何取数或计算上的分歧。

### Q5 — 未定义指标（拒答测试）

| 维度 | A | B | 一致 |
|---|---|---|---|
| metric_id | NONE | NONE | ✅ |
| answerable | **no** | **no** | ✅ |
| source_fields | NONE | NONE | ✅ |
| formula | NONE | NONE | ✅ |
| period_semantics | NONE | NONE | ✅ |
| flags | undefined | undefined | ✅ |

**完全一致，且拒答正确。** 两方都未用行业惯例自行补写周转率定义，都额外指出即便补定义、现有字段也不足（缺期初余额与天数基数）。**无一方猜口径。**

---

## 2. 汇总

| 统计项 | 结果 |
|---|---|
| 五题全部三维度完全一致 | **4 / 5**（Q1、Q2、Q3、Q5） |
| 不完全一致 | 1（Q4，仅 `period_semantics`） |
| **取数字段（`source_fields`）一致** | **5 / 5** |
| **公式结构（`formula`）一致** | **5 / 5** |
| `period_semantics` 一致 | 4 / 5 |
| 实质性分歧（取数字段或公式结构不同）| **0** |
| 未定义指标（Q5）处理 | 两方均**正确拒答**，均未猜测 |
| 定义内 undefined 条件（Q4）处理 | 两方均**正确拒答**，均未按 0 处理 |

---

## 3. 判定

阈值原文（`POC.md`，冻结未改）：

```text
PASS          5 道题中 ≥ 4 道两份回答完全一致，且未定义指标被正确拒答
FAIL          ≥ 3 道题出现实质性分歧（取数字段或公式结构不同）
INCONCLUSIVE  介于两者之间
```

- 完全一致题数 = **4**，满足 `≥ 4`
- 未定义指标（Q5）**被正确拒答**
- 实质性分歧 = **0**，远未触及 FAIL 的 `≥ 3`

### 判定：**PASS**

**但这是刚好压线的 PASS，不是宽裕通过。** 完全一致题数恰为阈值下限 4，再少一题即落入 INCONCLUSIVE。记录此点是为了防止后续把这个结果当作比它实际更强的证据。

---

## 4. 结果的效力边界（判定前已记录于 `FREEZE.md`，此处重申）

1. **两位回答者是同一基座模型的两个独立会话，错误相关。** 因此"两份一致"对 H1 的支持强度**弱于**两位独立的人类财务从业者。本次结果应读作 **H1 的必要条件检验通过**：不一致 → H1 确定有问题；一致 → H1 未被证伪，但未被强证实。
2. **补强方式（不在本次范围）**：用同一套冻结输入，找一位真人财务背景回答者复跑，与 A/B 三方比对。这是把 H1 从"未被证伪"推向"被支持"的唯一途径。
3. **样本极小**：3 个指标、5 道题。`PROJECT_SPEC.md` §10 的停止条件是按 20 个指标设的（"20 个指标里超过 5 个无法给出无歧义口径 → 停止"），本次不构成对该条件的检验。
4. **字段清单为替代品**，非 cninfo 真实字段（见 `FREEZE.md` §已记录偏离）。

---

## 5. 定义暴露的缺陷

两位回答者独立列出的缺陷中，**9 条收敛**（两方都独立提出）。收敛项的可信度高于单方项，Phase 1 应优先处理。

### 5.1 双方收敛（9 条）——Phase 1 必须解决

| # | 缺陷 | A | B | 性质 |
|---|---|---|---|---|
| C1 | 缺实体维度与期间维度字段（公司标识、会计年度、报告期类型），公式在工程上无法定位到具体一行 | #1 | #1 | 阻塞实现 |
| C2 | `flags` 无受控词表：拼写、取值域、多 flag 并存表示、undefined 是 flag 还是终止状态，均未规定 | #8 | #2 | 阻塞机械判定 |
| C3 | 口径 1 未规定是否允许由"税前合计 − 所得税影响 − 少数股东部分"倒推归母净额 | #3 | #4 | 静默分歧源 |
| C4 | 口径 1 未声明非经常性损益的**符号约定**（收益记正/损失记负 vs 绝对值） | #4 | #5 | **可产生方向性错误且不触发任何 undefined** |
| C5 | `restated` 判定路径缺失或重复：口径 1 的 `source_fields` 不含 `notes.restatement_flag`；口径 3 有两条判定路径且未定优先级 | #5 | #3 | 规则不可执行 |
| C6 | `is.operating_revenue_prior_as_originally_reported` 的字段描述自相矛盾（"上期"却写"本年金额"） | #6 | #8 | 字段清单缺陷 |
| C7 | `notes.business_combination_type` 无取值枚举，`scope_change` 无法机械判定 | #7 | #9 | 规则不可执行 |
| C8 | "跨准则版本不可比"没有对应字段（如 `standard_version`）或 flag，停留在提示层 | #9 | #10 | 规则不可执行 |
| C9 | 周转类指标整体缺位，且字段粒度不统一（流动负债有期初期末双值，存货/应收只有单值） | #11 | #11 | 字段设计缺规则 |

### 5.2 仅单方提出（7 条）——Phase 1 评估后决定

| # | 缺陷 | 来源 |
|---|---|---|
| S1 | 缺"字段缺失"的表示约定（null / 缺键 / 0），导致两条 undefined 条件在数据层不可判定 | A #2 |
| S2 | 口径 2 别名"现金流量比率"过宽，易把总负债口径/平均口径的提问错误路由过来 | A #10 |
| S3 | 口径 2 未规定分子恰为 0 或分子缺失时的处理 | A #12 |
| S4 | 口径 2 未规定分子为半年/季度累计时是否年化、分母取哪个时点 | B #6 |
| S5 | 口径 2 未显式声明禁用 `bs.total_current_liabilities_period_begin` | B #7 |
| S6 | 三份定义均未声明合并/母公司范围、计量单位与币种、审计状态 | B #12 |
| S7 | Q4 暴露：输出契约未规定 `answerable: no` 时 `period_semantics` 的含义（本次唯一分歧的根因） | 比对得出 |

### 5.3 对 `PROJECT_SPEC.md` §5.1 字段集的启示

现行 §5.1 字段集（`source_fields` / `formula` / `standard_basis` / `period_semantics` / `common_pitfalls`）**不足以支撑机械判定**。9 条收敛缺陷中有 5 条（C2、C4、C5、C7、C8）的根因是同一个：

> **`common_pitfalls` 是给人读的散文，不是给机器执行的规则。** 定义把"必须标记 restated"、"跨版本不可比"、"同一控制下合并要标记 scope_change" 全写进了 pitfalls，但没有任何字段承载这些规则的可执行形式。

这是本次实验最有价值的产出，也是 Phase 1 应当据以扩展字段集的依据。

> ⚠️ 这些缺陷**不得**用来回头修改本次已冻结的三份定义（`POC.md` kill criterion：定义可以无限细化到消除分歧，那时它已是答案而非口径）。
> 它们是 **Phase 1 的输入**，用于设计 20 个指标时的字段集，不是本次实验的重测材料。

---

## 6. 下一步（依 `POC.md` 的 PASS 分支）

> PASS → 口径可以被写成机器可读且人可复现的定义 → Phase 1 全量做 20 个指标；把这 3 个作为模板

1. Phase 1 扩展 `PROJECT_SPEC.md` §5.1 字段集，至少覆盖 C1–C9（走 OpenSpec `/opsx:propose`，因为这是对权威规格的变更）
2. 这 3 份定义作为模板保留，**版本号维持 version: 1 不动**；字段集扩展后产生的新定义记为 version: 2，与本次结果不可跨版本比较
3. 补强实验（可选，低成本）：同一套冻结输入交给一位真人财务背景回答者，三方比对
4. 并行推进 Phase 0（cninfo 实证结论）
