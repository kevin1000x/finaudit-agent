# VERIFICATION — 验收证据矩阵

> 模式：`VERIFY`　｜　状态：**模板，尚无任何验证记录**
> 规则：不接受"应该可以了"。没有真实执行证据的一律记 `UNVERIFIED`，不记 PASS。
> 禁止从代码阅读推断 `VERIFIED`——只要存在可执行的验证方式，就必须执行它。

---

## 使用方式

每个阶段结束时，把该阶段的阻塞性验收标准逐条填入下表。一行一条，不合并、不省略。

| 验收标准 | 验证方法 | 实际命令 / 动作 | 期望结果 | 实际结果 | 证据位置 | 状态 |
|---|---|---|---|---|---|---|

状态只有三种取值：

- `VERIFIED` —— 已执行验证并产出真实输出
- `FAILED` —— 已执行且未达标
- `UNVERIFIED` —— 未执行，或只做了代码阅读

**任一阻塞性标准为 `FAILED` 或 `UNVERIFIED` 时，不得声明阶段完成。**

---

## Phase 0 — cninfo 实证结论

| 验收标准 | 验证方法 | 实际命令 | 期望结果 | 实际结果 | 证据 | 状态 |
|---|---|---|---|---|---|---|
| AC-03 结论可复现 | 真实数据流水线 | — | 结论中每个数字可重跑得出 | — | — | `UNVERIFIED` |
| README 首屏含问题/方法/结论/怎么跑 | 人工检查 | — | 四项齐全 | — | — | `UNVERIFIED` |

## Phase 1 — 语义层

> **验证执行于 2026-08-16**（`01-08-PLAN.md` wave 5），模式 `VERIFY`，未修改任何实现。
> 下表是索引；**每条的逐字输出与退出码见 §Phase 1 · 附录 A**，可原样重跑。
> 本节不含任何「从代码阅读推断」的结论。

| # | 验收标准 | 验证方法 | 实际命令 | 期望结果 | 实际结果 | 证据 | 状态 |
|---|---|---|---|---|---|---|---|
| SC-1 / AC-01 | 20 指标字段齐全 | 自动校验 | `python -m semantic_layer validate --json` | 20/20，findings 空 | `definitions_checked: 20`、`definitions_failing: 0`、`findings: []`，EXIT=0 | 附录 §A.3 | `VERIFIED` |
| SC-1 补 | 指标数量确为 20 | 文件计数 | `ls metrics/*.yaml \| grep -v '_flags' \| wc -l` | 20 | `20`，EXIT=0 | 附录 §A.1 | `VERIFIED` |
| SC-2 | 存在机械校验器（非 Agent） | 全量测试 | `python -m pytest -q` | 全绿 | `350 passed`，EXIT=0 | 附录 §A.2 | `VERIFIED` |
| SC-3 / AC-02 | C2 拒答准确率 100% | 评测 C2 类 | `python -m eval.run --suite frozen-01 --category C2` | 4/4，门成立 | `C2 拒答准确率：4/4　门成立：True　存活题数满足下限`，EXIT=0 | 附录 §A.7 | `VERIFIED` |
| SC-4 / AC-04 | 问题集 ≥20 题且已冻结 | 哈希 + 时间戳 | `cd eval/frozen-01 && sha256sum -c SHA256SUMS` | 21 行 OK | 21 行 `OK`，无非 OK 行，EXIT=0 | 附录 §A.6、`eval/frozen-01/FREEZE.md` | `VERIFIED` |
| SC-5 / AC-10 | 仓库零非公开数据 | 自动扫描 | `python -m semantic_layer scan --json` | findings 空 | `rules_version: 2`、`findings: []`，EXIT=0 | 附录 §A.4 | `VERIFIED` |
| §7 门 5 | 构造错误作废率 ≤10% 且作废清单公开 | 评测运行器 | 同 SC-3 | ≤10% | `构造错误作废率 0.0%（上限 10%，未超限）`，作废 0 题 | 附录 §A.7 | `VERIFIED` |
| §5.1 元规则 | `advisory_only` 占比 ≤50% | 统计 + 阈值门 | `python -m semantic_layer stats --json --fail-over 0.5` | 退出码 0 | `advisory_ratio: 0.19008264462809918`（19.0%），`unclassified: 0`，EXIT=0 | 附录 §A.5 | `VERIFIED` |
| D-012 | POC-01 冻结产物未被改动 | 哈希 | `cd docs/agent/poc-01 && sha256sum -c SHA256SUMS` | 5 行 OK | 5 行 `OK`，EXIT=0 | 附录 §A.6 | `VERIFIED` |
| T-01-41 | VERIFY 模式未顺手改实现 | git 状态 | `git status --porcelain metrics/_flags.yaml eval/frozen-01/ docs/agent/poc-01/` | 输出为空 | 空，EXIT=0 | 附录 §A.8 | `VERIFIED` |
| **H1** | 20 指标里 >5 个无法给出无歧义口径 → 停止 | 逐份三迹象核查 | 见 §判定二 | 计数 ≤5 | **操作者 2026-08-16 裁决取严格读法 → 计 5，不 > 5，停止条件不触发** | §判定二 + §Task 3 复核记录 | `VERIFIED`（**压线**，见判定二末段） |
| AC-02 全貌 | C1/C3/C4/C5 四类的口径正确性 | 评测 | — | — | 本阶段**未执行**（能力缺口） | `eval/frozen-01/FREEZE.md` | `UNVERIFIED` |
| AC-05 证据链完整率 | — | — | — | — | 证据链在 Phase 2，本阶段零实现 | — | `UNVERIFIED` |
| AC-03 结论可复现 | — | — | — | — | 需真实数据，Phase 1.5 之后才具备 | — | `UNVERIFIED` |

### 判定一：`advisory_only` 元规则 —— **未失效**

`PROJECT_SPEC.md` §5.1 的规定是「Phase 1 结束时统计 `advisory_only` 占比，
**> 50% 视为元规则失效，须重新设计而非接受现状**」。

实测 **`advisory_ratio: 0.19008264462809918`**（121 条陷阱中 98 条 enforced / 23 条 advisory），
`unclassified: 0`，`--fail-over 0.5` 退出码 0。**19.0% < 50%，元规则成立。**

占比最高的两份是 `accounts_payable_turnover_days` 与 `accounts_receivable_turnover_days`
（各 `0.2857142857142857`，7 条中 2 条 advisory）。逐份分项见附录 §A.5。
**这两份占比高有其实质原因**（采购额不单列、增值税与收入不配比），
不是写得潦草——见 `docs/agent/phase-01/flag-vocabulary-review.md` §4。

⚠️ **这个数字有一个不在它本身的限制**：19.0% 说明「大部分陷阱被写成了可求值规则」，
但**不说明这些规则会正确触发**。规则是否真的能被数据触发，
要到 Phase 1.5 接上真实字段才验得了。

### 判定二：H1 停止条件 —— **未收敛，两种读法结论相反，须操作者裁决**

`PROJECT_SPEC.md` §10 的判据：「20 个指标里**超过 5 个**无法给出无歧义的机器可读口径 → 停止，重新定义问题」。
「超过 5」即 **≥6 触发**。

计划把「无法给出无歧义口径」操作化为三条迹象。逐份核查结果：

**迹象一 —— 该定义在批次执行中触发过停止协议（flag-request 或 open-question 记录）：计 1**

| 定义 | 依据 |
|---|---|
| `net_profit_attributable_excl_nonrecurring` | OQ-04：该定义有三部准则版本（2023/2010/2014），`standard_basis.version` 是列表，标量引用无解。裁决为把 `basis_version_mismatch` 移到 system 域 |

`docs/agent/phase-01/` 下**没有任何 `flag-requests-*.md`**（附录 §A.9）。
OQ-01（现金循环周期）**不计入**——它已被移出 20 指标，换入应付账款周转天数，
现为 C2 拒答靶子。OQ-02 / OQ-03 是基础设施问题，不指向任何具体定义。

**迹象二 —— `derivation.note` 或陷阱中承认存在无法机械消解的口径分支：计 1**

| 定义 | 原文依据 |
|---|---|
| `free_cash_flow` | `derivation.note` 首句：「**本指标无会计准则定义。** 下方 standard_basis 支撑的是两个分项各自的列报依据，**不支撑**『两者相减即自由现金流』这一组合——该组合方式是本语义层的选择」 |

**这一条的计入是有争议的**，如实写明：`free_cash_flow` 的口径本身**是无歧义的**
（分项固定、组合方式写死、与常见变体的不可比性逐条列出）。它缺的是**准则依据**不是**明确性**。
按 §10 的字面（「无法给出无歧义的机器可读口径」）它**不该计入**；
计入是取了更保守的读法。

`roe_weighted_average`（「在数据层面本指标不可复算，只能取披露值。未披露即拒答」）
**不计入**：它的口径完全明确（取披露值），且已用 `undefined_conditions` 处理了取不到的情形——
这是口径成功的例子，不是失败的例子。

**迹象三 —— 因语法边界而未能表达某条已知约束：计 3**

| 定义 | 原文依据 |
|---|---|
| `inventory_turnover_days` | 「**受限 DSL 不含算术，基数无法参与条件求值，因此在此显式声明**」 |
| `accounts_receivable_turnover_days` | 同一 365 基数约束，同样只能写成散文 |
| `accounts_payable_turnover_days` | 同上 |

后两份的 `derivation.note` 里没有 `inventory_turnover_days` 那句自陈，
但**约束与限制完全相同**（都声明「天数基数取 365」，而 DSL 同样不含算术）。
只数写了自陈的那一份会低估计数，故三份全计。

#### 两种读法

| 读法 | 计入范围 | 计数 | 对 §10 的结论 |
|---|---|---|---|
| **严格**（按计划原文，迹象三限定「因**语法边界**」） | 上述三迹象，去重 | **5** | 5 不 > 5 → **不触发** |
| **宽松**（迹象三扩展为「已知约束**无法机械执行**」，含缺字段） | 再加 `gross_profit_margin`（计量单位，定义原文明写「本定义**无法**对此设可求值规则」）、`net_working_capital`（「单位必须随结果一并携带」无字段可依） | **7** | 7 > 5 → **触发，应停止并重新定义问题** |

**严格读法恰好压在阈值上：5，再多一份就触发。** 这与 POC-01 的「压线 PASS」是同一种处境，
必须原样记录，不得表述为「安全通过」。

**执行者倾向严格读法，理由与反理由都写出来**：

- 支持严格读法：§10 问的是「**口径**能否写成无歧义的机器可读形式」，
  而缺字段是**数据层**问题不是口径层问题。计量单位那两条已在台账 B-3 有明确排期
  （Phase 1.5 抽取器输出 `unit` 与 `currency`），届时可转为 enforced，**不是无解**。
- 反对严格读法：从复核者角度看，「写得出口径但执行不了」与「写不出口径」在
  **可审计性**上后果相同——两种情况下系统都不会拦住那个错误。
  本项目的主张是可审计性，按主张选，宽松读法更一致。

**这条不是执行者能定的**：§10 的动作是「停止，重新定义问题」，属项目范围变更。
已列入 `01-08` Task 3 的人工检查点。

#### 裁决（2026-08-16，操作者）

> **严格。**

**取严格读法：计数 5，不 > 5，§10 停止条件不触发，Phase 1 可以收口。**

裁决同时确立了一条本项目此后适用的判据边界：
**「口径写不出来」与「口径写得出但当前数据执行不了」是两件事**，
§10 管前者；后者归数据层，走台账（B-3 → Phase 1.5 抽取器输出 `unit` / `currency`）。

**但压线这件事必须随结论一起传递**，不得在任何转述中丢失：

- 严格读法计 5，判据是「> 5 触发」，**再多一份定义命中迹象三就会触发**；
- 宽松读法计 7，**已经越过阈值**。选严格读法是有理由的选择，不是「安全通过」；
- 这与 POC-01「4/5 压线 PASS」是同一种处境。两处压线**叠加**在同一条假设 H1 上：
  POC-01 压线通过 → Phase 1 又压线不触发。
  **H1 至今的全部证据都停在阈值边缘**，这是本项目最应当被质疑的地方。

**因此 H1 的结论仍然只能读作「未被证伪」，不是「已被证实」。**
理由现在有三条（原两条 + 本次新增）：
① POC-01 完全一致题数恰为阈值下限 4；② 两位回答者是同源模型、错误相关；
③ **Phase 1 的停止条件判定同样压在阈值上，且换一种同样合理的读法即触发。**

### Task 3 人工检查点复核记录（2026-08-16）

**第 1 步 —— 操作者指定复核 `SC-2` / `SC-3 (AC-02)` / `SC-4 (AC-04)` 三条，
由执行者原样重跑并逐字比对：三条全部一致。**

| 条目 | 表中记录值 | 复跑实测 | 结论 |
|---|---|---|---|
| SC-2 | `350 passed`，EXIT=0 | `350 passed in 10.34s`，EXIT=0 | **一致**（附录记 `10.33s`，耗时是非确定性字段） |
| SC-3 / AC-02 | `4/4　门成立：True`，作废率 `0.0%`，EXIT=0 | 同值；四题理由码均 `METRIC_NOT_DEFINED` | **一致**（仅运行时间戳由 `12:20:59Z` 变为 `13:04:14Z`） |
| SC-4 / AC-04 | 21 行 `OK`，无非 OK 行，EXIT=0 | `grep -c ': OK'` = 21，非 OK 行 0，EXIT=0 | **一致** |

**比对口径写清**：只有**运行时间戳**与**测试耗时**两个字段允许不同，
它们本就随每次运行变化；其余数值、计数、退出码、理由码要求逐字相同。三条均满足。

**第 2 步（读两份定义的 YAML 是否读得懂）—— 未完成，如实记为缺口。**
该步问的是「一个人只读 YAML 不看代码，能否看懂触发条件、能否分清哪些陷阱有机械后果」。
**这是对可读性的人的判断，执行者无法代答**——我读得懂不构成证据，我写的它。
操作者本次只指定了第 1 步的三条。
本项目 D-003 的可复核性前提正建立在这一点上，**该步应在 Phase 2 开始前补做**，
已并入台账。此处不因未完成而阻塞收口，但也不标记为已通过。

**第 3–5 步**：冻结校验已在第 1 步的 SC-4 中覆盖（21 行 OK）；
`FREEZE.md` 的确认语一节本就如实记录了操作者的原话是「1.可以，按你方向来」
而非计划要求的仪式性措辞，并说明了为何不代填；
flag 词表评审见 `docs/agent/phase-01/flag-vocabulary-review.md`。

**第 6 步（是否进入下一阶段）**：操作者裁决「严格」+「按计划继续推进」
⇒ **不触发停止条件，Phase 1 收口，进入 Phase 1.5。**

无论哪种读法，**都必须同时记住**：H1 的结论只能读作「**未被证伪**」，不是「已被证实」。
理由沿用 `.planning/STATE.md` 已记录的两点——POC-01 是 4/5 压线通过（再少一题即 INCONCLUSIVE），
且两位回答者是**同源模型**、错误相关。

### 判定三：flag 词表 —— **零新增请求**，但发现两处「有字段却没用」

详见 `docs/agent/phase-01/flag-vocabulary-review.md`。此处只记结论，不重复内容：

- 19 份定义**零 flag 新增请求**，10 条词表未产生阻塞；
- 但「零请求」不等于「零缺口」——`advisory_only` 是一条更短的合规路径；
- 评审找到两处**已有字段能诚实触发却标成 advisory** 的条目
  （`minority_interest_share` 的负权益、`revenue_growth_yoy` 的合并范围变动）。
  这是 `rules/failure-modes.md` **F-2 的镜像**。处置建议已列，**本阶段不执行**。

### 本阶段明确 `UNVERIFIED` 的事项（不留白、不粉饰）

1. **C1 / C3 / C4 / C5 共 16 题仅冻结未执行。** 原因逐类见 `eval/frozen-01/FREEZE.md`：
   C1/C3 需数值执行路径（`formula` 目前只是字符串，受限 DSL 刻意不含算术）；
   C4 需准则检索（Phase 3 的 L2）；C5 需图谱或其对照实现（Phase 3，且 D-007 要求先证明「非图不可」）。
   **这是能力缺口，不是配置缺失**——接入 LLM API 并不能让本系统跑通它们。
2. **C3 的标准答案基于合成夹具**（`fixtures/synthetic-01.yaml`，虚构公司与数值）。
   因此基于它的任何数值结论**只证明计算逻辑正确，不证明数据抽取正确**。
   数据抽取属 Phase 1.5 的 PDF 抽取器（D-013），与本阶段无关。
3. **元规则的 19.0% 不保证规则会正确触发**（见判定一末段）。
4. **01-01 / 01-04 / 01-05 / 01-07 没有 SUMMARY 文件**，
   因此这四个计划执行过程中的检查点对话**无书面记录可查**。
   本次验证只能核对**产物**，无法核对**过程**，这一点如实记为证据缺口。
5. **对照臂（`eval/baseline.py`）的结果不属于本阶段验收。**
   它测的是不带语义层的裸 LLM，报告在 `eval/runs/baseline/`，
   其 C1/C3 分数**不得**作为本系统能力引用。

### 本阶段暴露但未解决的问题

不在此重复内容，指向两份文件：

- `docs/agent/phase-01/open-questions.md` —— OQ-01…OQ-04，含 OQ-04 的 (a) 分支「Phase 2 必办」
- `docs/agent/phase-01/flag-vocabulary-review.md` —— §5 的 5 条处置清单
- `docs/agent/OPEN-ITEMS.md` —— 跨阶段台账（A 阻塞 / B 已决待排期 / C 规格 U-0x / D 新增 / E 已关闭）

---

### Phase 1 · 附录 §A —— 逐字命令输出

全部执行于 2026-08-16，工作目录为仓库根（除非命令自带 `cd`），
解释器为 `.venv/Scripts/python`（本机 Python 3.14；默认 `python` 是 3.8.5，**不可用**）。

**§A.1 指标数量**
```
$ ls metrics/*.yaml | grep -v '_flags' | wc -l
20
EXIT=0
```

**§A.2 全量测试**
```
$ .venv/Scripts/python -m pytest -q | tail -3
........................................................................ [ 82%]
..............................................................           [100%]
350 passed in 10.33s
EXIT=0
```

**§A.3 定义校验（AC-01）**
```
$ .venv/Scripts/python -m semantic_layer validate --json
{
  "findings": [],
  "summary": {
    "definitions_checked": 20,
    "definitions_failing": 0,
    "findings_total": 0
  }
}
EXIT=0
```

**§A.4 非公开数据扫描（AC-10）**
```
$ .venv/Scripts/python -m semantic_layer scan --json
{
  "rules_version": 2,
  "findings": []
}
EXIT=0
```
> `rules_version` 于 2026-08-16 由 1 升为 2：`CONTACT_PATTERN` 原式把 npm 的
> `包名@版本`（`dsh-root@0.1.0-rc`）误判为邮箱。已收紧并补回归测试。

**§A.5 元规则统计（§5.1）**
```
$ .venv/Scripts/python -m semantic_layer stats --json --fail-over 0.5
{
  "total": 121,
  "enforced": 98,
  "advisory": 23,
  "unclassified": 0,
  "advisory_ratio": 0.19008264462809918,
  "per_metric": {
    "accounts_payable_turnover_days":    {"total": 7, "enforced": 5, "advisory": 2, "unclassified": 0, "advisory_ratio": 0.2857142857142857},
    "accounts_receivable_turnover_days": {"total": 7, "enforced": 5, "advisory": 2, "unclassified": 0, "advisory_ratio": 0.2857142857142857},
    "current_ratio":                     {"total": 6, "enforced": 5, "advisory": 1, "unclassified": 0, "advisory_ratio": 0.16666666666666666},
    "debt_to_asset_ratio":               {"total": 5, "enforced": 4, "advisory": 1, "unclassified": 0, "advisory_ratio": 0.2},
    "free_cash_flow":                    {"total": 5, "enforced": 4, "advisory": 1, "unclassified": 0, "advisory_ratio": 0.2},
    "gross_profit_margin":               {"total": 8, "enforced": 6, "advisory": 2, "unclassified": 0, "advisory_ratio": 0.25},
    "interest_bearing_debt_ratio":       {"total": 6, "enforced": 5, "advisory": 1, "unclassified": 0, "advisory_ratio": 0.16666666666666666},
    "inventory_turnover_days":           {"total": 6, "enforced": 5, "advisory": 1, "unclassified": 0, "advisory_ratio": 0.16666666666666666},
    "minority_interest_share":           {"total": 5, "enforced": 4, "advisory": 1, "unclassified": 0, "advisory_ratio": 0.2},
    "net_profit_attributable_excl_nonrecurring": {"total": 5, "enforced": 4, "advisory": 1, "unclassified": 0, "advisory_ratio": 0.2},
    "net_profit_margin_attributable":    {"total": 6, "enforced": 5, "advisory": 1, "unclassified": 0, "advisory_ratio": 0.16666666666666666},
    "net_working_capital":               {"total": 7, "enforced": 6, "advisory": 1, "unclassified": 0, "advisory_ratio": 0.14285714285714285},
    "ocf_to_net_profit_attributable":    {"total": 6, "enforced": 5, "advisory": 1, "unclassified": 0, "advisory_ratio": 0.16666666666666666},
    "operating_cash_flow_ratio":         {"total": 6, "enforced": 5, "advisory": 1, "unclassified": 0, "advisory_ratio": 0.16666666666666666},
    "period_expense_ratio":              {"total": 7, "enforced": 6, "advisory": 1, "unclassified": 0, "advisory_ratio": 0.14285714285714285},
    "quick_ratio":                       {"total": 7, "enforced": 6, "advisory": 1, "unclassified": 0, "advisory_ratio": 0.14285714285714285},
    "return_on_total_assets":            {"total": 6, "enforced": 5, "advisory": 1, "unclassified": 0, "advisory_ratio": 0.16666666666666666},
    "revenue_growth_yoy":                {"total": 6, "enforced": 5, "advisory": 1, "unclassified": 0, "advisory_ratio": 0.16666666666666666},
    "roe_weighted_average":              {"total": 5, "enforced": 4, "advisory": 1, "unclassified": 0, "advisory_ratio": 0.2},
    "total_asset_turnover":              {"total": 5, "enforced": 4, "advisory": 1, "unclassified": 0, "advisory_ratio": 0.2}
  }
}
EXIT=0
```
> `per_metric` 在原始输出中是逐行展开的 JSON，此处**仅压缩了缩进以便阅读，数值一字未改**。
> 原始未压缩输出可由上述命令原样重跑得到。

**§A.6 两处冻结校验（D-012）**
```
$ cd docs/agent/poc-01 && sha256sum -c SHA256SUMS
definitions/net_profit_attributable_excl_nonrecurring.yaml: OK
definitions/operating_cash_flow_ratio.yaml: OK
definitions/revenue_growth_yoy.yaml: OK
field_inventory.md: OK
questions.md: OK
EXIT=0

$ cd eval/frozen-01 && sha256sum -c SHA256SUMS
（21 行，全部 OK；`grep -c ": OK"` = 21，`grep -v ": OK"` 无输出）
EXIT=0
```

**§A.7 C2 类评测（AC-02 / §7 门 2、门 5）**
```
$ .venv/Scripts/python -m eval.run --suite frozen-01 --category C2 --report eval/runs/
套件 frozen-01   运行于 2026-08-16T12:20:59Z

  题量 20   作废 0   计分分母 4   未执行 16
  通过 4   失败 0
  构造错误作废率 0.0%（上限 10%，未超限）

按类别：
  C1  NOT_RUN  题量 6  存活 6  已执行 0  通过 0
  C2  PASS     题量 4  存活 4  已执行 4  通过 4
  C3  NOT_RUN  题量 5  存活 5  已执行 0  通过 0
  C4  NOT_RUN  题量 3  存活 3  已执行 0  通过 0
  C5  NOT_RUN  题量 2  存活 2  已执行 0  通过 0

C2 拒答准确率：4/4   门成立：True   存活题数满足下限

§6 指标：
  口径正确率        N/A（需数值执行路径，Phase 1 不具备）
  拒答准确率        4/4
  答案正确率        N/A（需数值执行路径，Phase 1 不具备）
  证据链完整率       N/A（证据链是 Phase 2 的交付物）
  复核一致率        N/A（H2 复核实验在 Phase 2）
  引用可定位率       N/A（准则检索是 Phase 3 的 L2）
  归因覆盖率        100%

逐题：
  PASS     Q-C2-001     正确拒答，理由码 METRIC_NOT_DEFINED
  PASS     Q-C2-002     正确拒答，理由码 METRIC_NOT_DEFINED
  PASS     Q-C2-003     正确拒答，理由码 METRIC_NOT_DEFINED
  PASS     Q-C2-004     正确拒答，理由码 METRIC_NOT_DEFINED
  （C1/C3/C4/C5 共 16 行均为 NOT_RUN「--category C2 未选中本类」，此处省略以免刷屏；
    原样重跑即可见全部 20 行）

报告已写入 eval\runs\frozen-01-20260816T122059Z.json
EXIT=0
```

**§A.8 VERIFY 模式未改动冻结产物与词表（T-01-41 / T-01-44）**
```
$ git status --porcelain metrics/_flags.yaml eval/frozen-01/ docs/agent/poc-01/
（无输出）
EXIT=0
```

**§A.9 flag 新增请求（判定三）**
```
$ ls docs/agent/phase-01/flag-requests-*
ls: cannot access 'docs/agent/phase-01/flag-requests-*': No such file or directory
EXIT=2
```

## Phase 1.5 — 数据接入层

### §A 两道闸门的负控制（`01.5-06` Task 1，`J-5` / `L-5`，2026-08-28 实跑）

> **`A guard only guards if the regression actually fails it.`**
> 本节四段输出全部是**当场跑出来的**，不是转述。
> 变异一律带 `PYTHONDONTWRITEBYTECODE=1`（`N-41`：等长变异会被字节码缓存骗过）。

⚠️ **一处与计划不符，如实记**：`01.5-06-PLAN` Task 1 的 `<files>` 写的是要动
`tests/test_reconciliation.py` 与 `tests/test_column_binding.py`，
而**两条负控制用例在 wave 1 与 wave 3 就已经写好了**。
本任务因此**没有产生任何代码改动**（`git status --porcelain` 全程为空），
只剩下「跑一遍程序并留下记录」这一半。计划高估了工作量，不是少做了事。

⚠️ 另一处：计划写的变异对象是 `locate.resolve_column`，**该函数不存在**；
实际的列角色判定在 `locate._role_of`（由 `bind_columns` 调用）。按实际符号做的变异。

#### A.1 勾稽闸门 —— 造回归

把 `reconcile.reconcile_batch` 的判定改成恒真（**只改判定那一行**，
且写入前先 `ast.parse` 自证语法仍合法 —— `rules/commands.md` 记的 2026-08-24
第一次实跑就是被语法错误骗过去的）：

```
-             passed=abs(difference) <= tolerance,
+             passed=True,  # NEGATIVE-CONTROL MUTATION

$ .venv/Scripts/python -m pytest tests/test_reconciliation.py -q
FAILED tests/test_reconciliation.py::test_负债合计人为加一元后闸门拦住
FAILED tests/test_reconciliation.py::test_差额恰好一分仍算通过而一分零一厘不算
FAILED tests/test_reconciliation.py::test_闸门未通过时计算层拒答且不产出数值
3 failed, 7 passed in 0.43s
```

**红的原因逐字核过**（`J-5` 要求的不只是「会红」，还要「红的原因正确」）：

```
>       assert result.passed is False
E       AssertionError: assert True is False
E        +  where True = ReconcileResult(passed=True, ...,
E                        difference=Decimal('-1.00'), tolerance=Decimal('0.01'), ...).passed
```

⇒ 差额 **`-1.00`** 被放行了。**是断言失败，不是 `ImportError` / 语法错误 / 解析失败。**

#### A.2 勾稽闸门 —— 回退

```
$ .venv/Scripts/python -m pytest tests/test_reconciliation.py -q
10 passed in 0.27s
```

#### A.3 列绑定 —— 造回归（**本节最要紧的一段**）

把 `locate._role_of` 改成不看表头文字、按位置约定给角色 ——
即回到 `D-016` 补充节**明令禁止**的那种做法：

```
+     return "期末余额", "positional"  # NEGATIVE-CONTROL MUTATION：按位置，不看表头

$ .venv/Scripts/python -m pytest tests/test_column_binding.py -q
FAILED tests/test_column_binding.py::test_全取期初列时勾稽照样通过而列绑定不通过
FAILED tests/test_column_binding.py::test_不通过时留证含版面原文与两个口径名
FAILED tests/test_column_binding.py::test_营业收入本期与上期匹配同一行却取到不同的值
3 failed, 5 passed in 0.71s

$ .venv/Scripts/python -m pytest tests/test_reconciliation.py -q     ← 同一个变异下
10 passed in 0.28s
```

🔴 **后面那 `10 passed` 才是这条负控制的全部意义。**
它逐字证明了 `D-016` 补充判据要求的那件事：
**单独跑勾稽闸门不足以让列绑定用例通过** ——
列全取错了，而恒等式照样成立（同一列内部自洽），勾稽闸门**一条都没红**。
这正是 `A-9` 记的那个盲区，现在它有了可执行的证明而不只是一段推理。

#### A.4 列绑定 —— 回退

```
$ .venv/Scripts/python -m pytest tests/test_column_binding.py tests/test_reconciliation.py -q
18 passed in 0.75s

$ git status --porcelain src/extractor/
（无输出 —— 两处变异已全部回退）

$ .venv/Scripts/python scripts/check_gates.py
EXIT=0

$ .venv/Scripts/python -m pytest -q
699 passed in 21.59s
```

| 验收标准 | 验证方法 | 实际结果 | 状态 |
|---|---|---|---|
| `D-018` 判据 1：勾稽闸门真的会拦 | 造回归 → 看红 → 核因 → 回退 | 差额 `-1.00` 被放行时三条用例红 | **PASS** |
| `D-016` 补充判据：勾稽替代不了列绑定 | 同上，且同时跑勾稽 | 列绑定 3 红 / 勾稽 **10 全绿** | **PASS** |
| `J-5`：红的原因要正确 | 逐字读失败输出 | 是断言失败，非导入/语法错误 | **PASS** |

### §B 验收矩阵 SC-1…SC-8（`01.5-06` Task 3，命令 **2026-08-29 实跑**，本节 08-30 落文）

> 下表是索引；**每条的逐字输出与退出码见 §D 附录**，可原样重跑。
> **没有真实执行证据的一律记 `UNVERIFIED`，不记 `PASS`。**
> 本节不含任何「从代码阅读推断」的结论 —— 凡是只读了代码没跑过的，状态栏写 `UNVERIFIED`。

| # | 验收标准 | 验证方法 | 实际命令 | 期望结果 | 实际结果 | 证据 | 状态 |
|---|---|---|---|---|---|---|---|
| SC-1a | 能从巨潮下载指定公司指定年度的年报 PDF | 联网下载 | `python -m extractor fetch --stock 600519 --year 2023` | 取回 PDF 并给出 SHA-256 | **本轮未联网复跑**。下载链路已是仓库内代码（`src/extractor/download.py`），三份本机语料的 SHA-256 逐字记在 `PROBE-14.md` / `PROBE-COMBINATION.md`，但那是 wave 2 的执行记录 | `docs/agent/phase-01.5/PROBE-14.md` §1 | `UNVERIFIED`（本轮无执行证据） |
| SC-1b | 定位三张合并报表所在页 | 直接跑锚点定位 | 见 §D.10 | 三张合并表各定位到 1 个锚点，合并与母公司分离 | 8 个锚点全部定位：合并 BS p58 / 合并 IS p63 / 合并 CFS p66，母公司三张 p61 / p65 / p68 各自分开，EXIT=0 | §D.10 | **PASS** |
| SC-2 | 30 个字段中 ≥24 个能抽出并映射，**计数口径 = 取到的值经逐个人工核对正确** | 人工逐字段核对 | Task 4 的检查点 | ≥24 | **判定依赖 Task 4，本轮不代答。** 已定的部分：`N-37` 按 `D-026` 判作废 1 条（`notes.reporting_period_months`，第 1 类），作废率 **1/30 = 3.33% ≤ 10%**，分母 29；映射表实有 **31** 条（`bs 15 / is 8 / cfs 2 / notes 5 / kpi 1`，比 30 多出的 1 条是 `notes.consolidation_scope_change`）。其中经人工核对的只有 wave 1 的 15 个 `bs.*`，**其余未逐字段核对** | `N-37`、`D-026`、§D.14 | `UNVERIFIED`（口径要求人工核对，Task 4 未做） |
| SC-3 | 区分「行在但格子空 = 0」与「整行不存在 = 缺失」，各有真实样本驱动的回归用例 | 全量测试 | `python -m pytest tests/test_missing_semantics.py -q` | 两类各有用例且全绿 | 格子空 4 条（短期借款 / 交易性金融负债 / 长期借款 / 应付债券，茅台 2023 实测）+ 整行不存在 2 条 + 「空格子是一次成功的抽取而不是失败」1 条；有息负债率在两种批次上分别**算得出**与**拒答**，EXIT=0 | `tests/test_missing_semantics.py`、§D.1 | **PASS** |
| SC-4 | 抽取产物带出处：PDF 的 SHA-256 + 巨潮源 URL + 页码 + 计量单位与币种 | 打印一条真实记录的全部出处 | 见 §D.13 | 四件套齐全 | 四件套全部非空，且**多于** SC-4 的要求：另带 `anchor_page`（D-019）、`column_header`（D-016）、`header_inherited`（继承留证）、`mapping_version`（L-38）、`selection` 三元组（D-023）、`batch_id`（D-024）。`AC-05` 齐全率 **210/210 = 1** | §D.13 | **PASS** |
| SC-5 | ≥5 个指标算出真实数值，并与 AKShare 交叉校验；不一致时置标记而不是静默选一个 | 端到端算一次 + 跨源对照 | 见 §D.11 / §D.12 | ≥5 个有数值；对照有逐字段判定 | **8 个指标全部算出数值**（跨三张合并报表一个批次）；跨源对照 **24 个字段**：`AGREES` 20 / `INCOMPARABLE` 4 / `DISAGREES` 0，触发占比 0/20，未超 `D-029` 的 1/3 阈值，EXIT=0 | §D.11、§D.12 | **PASS** |
| SC-6 | 默认不保留 PDF，`--keep-pdf` 是显式开关 | 读签名 + 读调用点 | `grep -rn 'keep_pdf' src/` | 默认 `False`，且 CLI 有显式开关 | `download.py:356` `keep_pdf: bool = False`；`__main__.py:46` 是显式 `dest="keep_pdf"` 的开关；`pipeline.extract_batch` 用 `TemporaryDirectory` 接，`with` 退出即删。`.pdf` 同时在 `.gitignore` 与 `scan_rules.yaml` 的 `forbidden_tracked_file_types` 里 | `src/extractor/download.py:356`、§D.1 | **PASS** |
| SC-7 | 勾稽校验是**阻断式**的：不通过即拒答而非记日志；一条真实通过用例 + 一条构造失败用例 | 全量测试 + 负控制 | `python -m pytest tests/test_reconciliation.py -q` | 阻断且两类用例都在 | `formula.py:541/549` 不通过即返回 `Refusal(RECONCILIATION_FAILED)`（`D-025` 第 9 支拒答码），不是日志；真实通过用例跑在茅台 2023 上，构造失败用例差额 `-1.00`；**负控制已按三步程序实跑**（§A.1–A.2） | §A、`tests/test_reconciliation.py`、§D.1 | **PASS** |
| SC-8 | 抽取器的验收看「取到的值」，不看「命中数」 | **人工**逐字段核对 | Task 4 检查点（`gate="blocking"`） | 操作者逐字段看取到的值 | **未做。执行者不得代答** —— 这条标准的全部内容就是「由人看一遍」，代答等于把它删掉 | 待 Task 4 填 | `UNVERIFIED` |
| AC-01 | 20 份口径定义字段齐全且合规 | 自动校验 | `python -m semantic_layer validate` | 20/20 合规 | `合计 0 项不合规，涉及 0 / 20 份定义`，EXIT=0 | §D.3 | **PASS** |
| AC-05 | 每条回答产出证据链，字段齐全率 100% | `pipeline.completeness_report()` | 见 §D.13 | 齐全率 = 1 | 真实批次 **210/210 = 1**，`meets_ac05 = True`。计数按 `PROJECT_SPEC` §9 写死的口径（有真值才算，空串 / null / 占位值 / 恒零计数不计）。⚠️ **覆盖面见 §C.2 的盲区** | §D.13、`tests/test_evidence_ids.py` | **PASS**（限定见 §C.2） |
| AC-10 | 仓库内零非公开数据 | 自动扫描 | `python -m semantic_layer scan` | findings 空 | `未扫出非公开数据风险（规则版本 2）`，EXIT=0 | §D.2 | **PASS** |
| `J-6` | 证据标识的字面存在性可机械检查 | 新增测试 | `python -m pytest tests/test_evidence_ids.py -q` | 正向 + 负向都在 | 14 条全绿；负向用例把 `field_id` 换成映射表里没有的串后被抓住且失败信息点名那个串。三条负控制按三步程序实跑（见 `b0aebf9` 提交信息） | `tests/test_evidence_ids.py`、§D.1 | **PASS** |
| `J-7` / `L-2` | 取数口径三元组齐全，缺任一项判失败 | 同上 | 同上 | 三项非空 | 真实批次三项全非空；逐项各造一次空值，每次都拉低齐全率并在 `gaps` 里点名 | `tests/test_evidence_ids.py` | **PASS** |
| `D-018` / `D-016` | 两道闸门各有一条负控制，且红的原因正确 | 造回归 → 看红 → 回退 | 见 §A | 都会红且原因正确 | 见 §A 四段实跑输出 | §A | **PASS** |

### §C 本阶段明确的证据缺口（不留白、不粉饰）

**C.1 样本覆盖是单公司单年为主。**
三张报表的**全部数值**取自贵州茅台 2023（`600519_2023.pdf`，143 页）。
万华化学 2019（`600309_2019.pdf`，213 页）与顺丰控股 2021（`002352_2021.pdf`，282 页）
**只测过「合并范围的变更」那一节**，没有跑过三张报表的取数。
⇒ 「映射表在换一家公司的排版上仍然成立」这件事**没有证据**。

**C.2 `AC-05` 抓不到「证据不相关」。**
这是写在 `PROJECT_SPEC.md` §9 里的**已知盲区**，不是本轮新发现的：
`AC-05` 只覆盖「证据**缺失**」。实证是 hello-agents 的 `arun_stream` 每步调两次 LLM，
屏幕上读到的推理与实际执行的 `tool_calls` 在 `temperature > 0` 时**无因果关系**，
而字段齐全率仍是 100%。同源性由 `AC-06` 的人工复核承担，**目前无自动判据**。
⇒ 上表 `AC-05` 那行的 `PASS` 只能读成「字段都有真值」，**不能读成「证据链是对的」**。

**C.3 `SC-2` 的分母里有 14 个字段从未经人工核对。**
计数口径写死的是「取到的值经逐个人工核对正确」，而经人工核对的只有 wave 1 的
15 个 `bs.*`。`N-37` 记的「29/29 达成」**是按抽取器能取到值来数的**，
不是按口径数的。这个差别必须由 Task 4 消掉，不能由执行者代答。

**C.4 `notes.reporting_period_months` 被作废，作废率 3.33%。**
按 `D-026` 第 1 类（不是报表上印出来的值）判定，定性理由不引用抽取器输出：
报告期月数由报告类型决定，报表上不印这一行。
实测否定证据：整份 143 页逐行搜四个串全部零命中。**第 2 类（真实失手）0 条。**
⚠️ 作废通道是一次**类比迁移**（`EVAL_CASES` §2.2 本管评测题目），10% 上限一并继承 ——
不得写成「§2.2 本来就覆盖」。

**C.5 `DISAGREES` 与 `ROW_ABSENT` 在真实数据上仍是零样本。**
跨源对照 24 个字段全部 `AGREES` 或 `INCOMPARABLE`，`DISAGREES` 一条没有；
`ROW_ABSENT` 只在构造样本上出现过。
⇒ 这两条路径**只被构造用例走过**，没有真实数据背书。
另有一条更强的限定（`C-14`）：本样本上「应付票据及应付账款」与「应付账款」取值完全相等，
⇒ **数值一致不能用来验证映射正确**。

**C.6 `restated` 判得出来，但没有传导到 `flags_status`。**
三支 `kind`（`NOTE_CHECKBOX` / `COLUMN_HEADER_PRESENCE` / `REPORT_METADATA`）
都已在 `extractor.notes` 里实现，**都没有接进 `pipeline` 的批次产出**。
⇒ **6 个指标的 `unevaluable` 现状不变。**
接之前要先回答一个真问题：`ExtractionRecord` 的 `column_header` / `unit` / `currency`
对一个复选框字段意味着什么 —— **编一个值填进去就是 `F-2`**。见台账 `N-43` 判据 3。

**C.7 `restated` 的规则是单样本、跨排版未验证。**
「有『调整后 / 调整前』列 ⟺ 发生追溯重述」与茅台 2023 p5 的文字互证，
但**反例形态一次都没观察到，也没有去找**。限定写在源码里，有测试锁着。

**C.8 `N-41` 判据 3 是一次真实返工。**
既有的等长变异结论**一律记 `UNVERIFIED` 需重跑**（字节码缓存能让整段验证程序失效）。
`01.5-06` 本轮自己做的三次变异已在 `PYTHONDONTWRITEBYTECODE=1` 下重验，
**此前各轮的等长变异结论没有重跑**。

**C.9 `N-42` 未做的一半。**
`check_xrefs.py` 的视野缺口已修，但**其余六道门各自的扫描范围有没有同样缺口，本轮没查**，
记 `UNVERIFIED`。

**C.10 独立复核余下 5 条 findings 未修。**
`RV-7` / `RV-3` / `RV-8` / `RV-9` 四条低级未修（`RV-5` 已随函数删除），
逐条判据在 `docs/agent/phase-01.5/REVIEW-TASK3.md`。无 blocker。

**C.11 `D-030` 的余量在收窄，且趋势向下。**
akshare 近月下载量三次实测：
2026-08-27 **3,738,489** → 08-28 **3,662,055** → **08-29 3,583,229**（§D.8）。
门槛 3,000,000，余量由 24.6% → 22.1% → **19.4%**，日均约 −78,000。
按此斜率约 7 天后跌破。**跌破即红，处置不是再下调一次** ——
再下调就把这道门变成跟着实测值走的橡皮门槛。届时的选项是接受它红并停用
`crosscheck` extra，或另找对照源。

**C.12 `H1` 仍然只是「未被证伪」。**
Phase 1 的判定是**压线**通过（计 5，门槛 >5）。本阶段没有产生任何改变该判定的新证据。

### §D 附录 —— 逐字命令输出（2026-08-29，全部当场跑出）

> 环境变量全程 `PYTHONIOENCODING=utf-8`（不设时 Windows 子进程按 cp936 写 stdout，
> 中文断言匹配不到，**它会红但红的原因不是它要查的那件事**）与
> `PYTHONDONTWRITEBYTECODE=1`（`N-41`）。
> 七条按 `F-8` 用 `&&` 串联，**禁止 `;`，禁止在门禁命令后接管道**。

#### D.1 全量测试

```
$ .venv/Scripts/python -m pytest -q
........................................................................ [ 99%]
...                                                                      [100%]
723 passed in 21.86s
EXIT=0
```

#### D.2 非公开数据扫描（`AC-10`）

```
$ .venv/Scripts/python -m semantic_layer scan
未扫出非公开数据风险（规则版本 2）。
EXIT=0
```

#### D.3 口径定义校验（`AC-01`）

```
$ .venv/Scripts/python -m semantic_layer validate
OK    total_asset_turnover.yaml

合计 0 项不合规，涉及 0 / 20 份定义
EXIT=0
```

#### D.4 交叉引用门禁

```
$ .venv/Scripts/python scripts/check_xrefs.py
已登记的定义点：
  D-decision    30 个   ← DECISIONS.md
  U              4 个   ← DECISIONS.md
  ledger        56 个   ← docs/agent/OPEN-ITEMS.md
  F              8 个   ← rules/failure-modes.md
  RV            10 个   ← docs/agent/phase-01.5/REVIEW-TASK3.md
  AC            10 个   ← PROJECT_SPEC.md
  NFR            5 个   ← PROJECT_SPEC.md
  OQ             4 个   ← docs/agent/phase-01/open-questions.md

扫描 74 个 markdown 文件，检查 1183 处引用。
已登记的跨命名空间碰撞 0 对（显式豁免，新增会拦）：

交叉引用门禁：通过
EXIT=0
```

#### D.5 阅读台账门禁

```
$ .venv/Scripts/python scripts/check_reading_ledger.py
扫描 27 份 references 产物，检查 77 条「已读」台账行。
已登记豁免 0 条（显式，新增会拦）。

阅读台账门禁：通过
  注意：本门禁抓不到目录级聚合行（见脚本 docstring「明确抓不到什么」）。
EXIT=0
```

#### D.6 门禁的门禁

```
$ .venv/Scripts/python scripts/check_gates.py
扫描 31 个测试模块，6 道已登记门禁。
已登记豁免 0 条，间接断言 helper 0 条（均应为 0）。
`NO-ASSERT-BY-DESIGN:` 声明 1 条 —— **它长起来就等于 R1 在退化**。
显式声明为「非门禁」的脚本 2 个：backlog_status.py, probe_fields.py

门禁的门禁：通过
  注意：本门禁证明不了负控制会抓住真实回归——那需要 `rules/commands.md`
        里那条人执行的程序（造回归 → 看红 → 回退）。见 docstring「抓不到什么」。
EXIT=0
```

⚠️ **「6 道已登记门禁」与「七道门」不矛盾，两个数在数不同的东西**：
`GATES` 注册表登记的是**门禁脚本**（6 个），而提交前跑的那条 `&&` 链有 **7 条命令** ——
第七条 `tests/test_plan_waves.py` 是一个 **pytest 模块**，按 `01.5-06-PLAN`
「明确不新增门禁」一节的判断**刻意没有登记进 `GATES`**。
不要把这两个数中的任何一个当成对方写错了。

#### D.7 计划 / 路线图一致性（第七条）

```
$ .venv/Scripts/python -m pytest tests/test_plan_waves.py -q
....                                                                     [100%]
4 passed in 0.03s
EXIT=0
```

#### D.8 供应链门禁（**单独跑，不串进提交链** —— 它走网络，链式跑时会因抖动整条失败）

```
$ .venv/Scripts/python scripts/verify_deps.py
pyproject.toml 声明的依赖：['pyyaml', 'pdfplumber', 'pytest', 'akshare']
...
== akshare 1.18.94
   [ OK ] 上游仓库  github.com/akfamily/akshare
   [ OK ] wheel      akshare-1.18.94-py3-none-any.whl
   [ OK ] 近月下载   3,583,229
          ⚠️ 门槛已下调至 3,000,000 —— 【D-030】...
== 已装分发的许可证扫描（含传递依赖）
   [ OK ] 扫描 43 个已装分发，无 AGPL 系命中
   [ OK ] 零许可证声明的第三方分发：0 个

供应链门禁：通过（⚠️ 有 2 项检查未跑：pdfplumber:下载量, pytest:下载量）
EXIT=0
```

⚠️ **两项「下载量取不到（HTTPError）」是 `[SKIP]` 不是 `[OK]`** ——
脚本明写「不据此放行也不据此拦截」。门禁整体通过，但那两项**没有结论**。

#### D.9 两处冻结校验（声明任何结论前必跑）

```
$ cd eval/frozen-01 && sha256sum -c SHA256SUMS
（21 行，全部 OK，无非 OK 行）
cases/Q-C5-002.yaml: OK
fixtures/synthetic-01.yaml: OK
EXIT=0

$ cd docs/agent/poc-01 && sha256sum -c SHA256SUMS
（5 行，全部 OK）
definitions/revenue_growth_yoy.yaml: OK
field_inventory.md: OK
questions.md: OK
EXIT=0
```

#### D.10 报表锚点定位（`SC-1b`）

```
$ .venv/Scripts/python -c "... locate.find_statement_anchors(pdf) ..."
p58   consolidated=True  合并资产负债表
p61   consolidated=False 母公司资产负债表
p63   consolidated=True  合并利润表
p65   consolidated=False 母公司利润表
p66   consolidated=True  合并现金流量表
p68   consolidated=False 母公司现金流量表
p70   consolidated=True  合并所有者权益变动表
p72   consolidated=False 母公司所有者权益变动表
EXIT=0
```

8 个锚点全部定位，**合并与母公司干净分离** —— `A-6` 第 3 条失效模式
（宽页窗口静默混入母公司数）在这份样本上关掉了。

#### D.11 八个指标一次算完（`SC-5`）

```
$ .venv/Scripts/python -m extractor compute \
    --metric debt_to_asset_ratio --metric current_ratio --metric quick_ratio \
    --metric net_working_capital --metric interest_bearing_debt_ratio \
    --metric gross_profit_margin --metric period_expense_ratio --metric free_cash_flow \
    --stock 600519 --year 2023 --pdf data/raw/600519_2023.pdf --json
debt_to_asset_ratio            0.1798432413917914711797
current_ratio                  4.6238924431792990312920
quick_ratio                    3.6703511168170040261588
net_working_capital                     176474906320.08
interest_bearing_debt_ratio    0.0011869875943758066820
gross_profit_margin            0.9196493724135797573790
period_expense_ratio           0.0852338808924697216377
free_cash_flow                           63973491832.30
EXIT=0
```

跨**三张**合并报表一个批次（`D-024`：批次身份键是 `(stock_code, fiscal_year)`）。
数值用 `Decimal` 不用二进制浮点。

#### D.12 跨源对照（`SC-5` 的 AKShare 一半，离线走固件）

```
$ .venv/Scripts/python -m extractor crosscheck --stock 600519 --year 2023 \
    --pdf data/raw/600519_2023.pdf \
    --reference tests/fixtures/akshare_600519_2023.json --json
字段数 24  {'AGREES': 20, 'INCOMPARABLE': 4}
comparable = 20
disagreements = 0
disagreement_ratio = 0
note = 触发占比 0（0/20），未超过 D-029 的反转阈值 1/3。
EXIT=0
```

⚠️ **那 4 个「不可比」不是 4 个「一致」**：茅台四个「格子空 = 0」的字段在 AKShare 侧
全是 `NaN`，当 0 会比出四条**从未被建立过的跨源一致**。
⚠️ **不给 `--reference` 就会联网。** 取不到对照源时退 3 不是 0 ——
「这一批没有对照结论」与「这一批对照通过了」在证据上是两件事。

#### D.13 出处四件套与 `AC-05` 齐全率（`SC-4`）

```
$ .venv/Scripts/python -c "... completeness_report(batch) ..."
  field_id           = bs.accounts_receivable
  pdf_sha256         = 2125ff97a452ea79b0d784e2432f7d224b6aecc330b644b593477d69e22f4ed1
  source_url         = https://static.cninfo.com.cn/finalpage/2024-04-03/1219506510.PDF
  page               = 59
  anchor_page        = 58
  unit               = 元
  currency           = 人民币
  column_header      = 2023年12月31日
  header_inherited   = True
  mapping_version    = 1
  selection          = {'sampling': '整表逐行', 'order_key': 'page,y', 'truncation': '未截断'}
  batch_id           = 61e881c77f3d4771
  AC-05 齐全率      = 210/210 = 1  meets_ac05 = True
EXIT=0
```

`page=59` 与 `anchor_page=58` **不相等**，这正是 `D-019` 拆成两个整数的理由：
标题印在上一页时，单一整数表达不了。
`header_inherited=True` 说明这一行的列归属是**从首页表头继承来的** ——
这个留证 2026-08-29 之前**不在序列化输出里**（见 `b0aebf9`）。

#### D.14 映射表条目数（`SC-2` 的分母）

```
$ .venv/Scripts/python -c "... load_pdf_mapping(ns) ..."
bs     15  mapping_version=1
is      8  mapping_version=1
cfs     2  mapping_version=1
notes   5  mapping_version=1
kpi     1  mapping_version=1
TOTAL 31
EXIT=0
```

⚠️ **31 不是 30。** `SC-2` 的分母 30 来自 20 份定义的 `source_fields` 去重；
多出来的第 31 条是 `notes.consolidation_scope_change` —— 它由 `D-020`（`A-8` 的裁决）
从 `notes.business_combination_type` 里**拆出来的独立字段**，
不在原来那 30 个里。同一份年报上两个字段取值不同，本身就是它们必须分开的证明。


#### D.15 登记册状态：本任务**开始前**与**完成后**两次实测

```
$ .venv/Scripts/python scripts/backlog_status.py     # Task 3 开始前
条目总数 82
  已关闭    4
  部分落地   5
  已落地    60
  已并进计划  1
  BLOCKED 8
  DECIDED 1
  依据     3
EXIT=0

$ .venv/Scripts/python scripts/backlog_status.py     # Task 3 完成后
条目总数 82
  已关闭    4
  部分落地   5
  已落地    61
  已并进计划  1
  BLOCKED 8
  依据     3
EXIT=0
```

⚠️ **`已落地` 增量是 `+1`，而 Task 3 的验收判据写的是「≥ 12」。**
差异的完整解释在 `LANDING-BACKLOG` §1：那条判据假设 12 条到收口时都还挂着 `OPEN`，
而其中 **10 条在 wave 1–3 实现时就已改成 `已落地` 并回标**，`L-2` 早在 08-24 就是 `已落地`，
**真正发生状态迁移的只有 `L-47`**（`DECIDED` → `已落地`，它的「枚举仍为 7 支」是一条过期几天的记录）。
**12 条「回标齐了」这件事本身是达成的** —— `references/` 逐字 grep 去重后正好 12 个编号，
第六道门的 R5 也通过。**不改判据凑数**（`F-4`：判据是待办不是已办，对不上就如实写对不上）。

⚠️ **不要用裸 `grep -c OPEN` 数这个** —— `~~OPEN~~ → 已落地` 会被裸 grep 数成 `OPEN`。

## Phase 2 — 证据链

| 验收标准 | 验证方法 | 实际命令 | 期望结果 | 实际结果 | 证据 | 状态 |
|---|---|---|---|---|---|---|
| AC-05 证据链完整率 | 批量评测 | — | 100% | — | — | `UNVERIFIED` |
| **AC-06 复核一致率**（H2 门） | 复核实验，15 题限时 5 分钟 | — | ≥80% | — | — | `UNVERIFIED` |
| 「无法判断」占比 | 同上 | — | ≤20% | — | — | `UNVERIFIED` |
| AC-08 归因覆盖率 | 批量评测 | — | 100% | — | — | `UNVERIFIED` |
| AC-09 危险样本拒绝 | 静态校验测试集 | — | 全部拒绝 | — | — | `UNVERIFIED` |

## Phase 3 — 知识层

| 验收标准 | 验证方法 | 实际命令 | 期望结果 | 实际结果 | 证据 | 状态 |
|---|---|---|---|---|---|---|
| AC-07 引用可定位率 | 抽检 20 条 | — | ≥90% | — | — | `UNVERIFIED` |
| H3 图谱必要性 | C5 类实证对比 | — | 3 个实例或明确证伪 | — | — | `UNVERIFIED` |

---

## 每次验证还必须检查

- 相关回归测试是否通过
- 是否引入了与本阶段无关的改动
- 是否残留调试代码
- 测试是否真的覆盖了被改动的行为（而不是只覆盖了周边）
- **仓库是否仍然零非公开数据**（每次都查，不是只在 Phase 1 查）
