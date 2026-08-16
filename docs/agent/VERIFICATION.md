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
| SC-1 / AC-01 | 20 指标字段齐全 | 自动校验 | `python -m semantic_layer validate --json` | 20/20，findings 空 | `definitions_checked: 20`、`definitions_failing: 0`、`findings: []`，EXIT=0 | 附录 A-3 | `VERIFIED` |
| SC-1 补 | 指标数量确为 20 | 文件计数 | `ls metrics/*.yaml \| grep -v '_flags' \| wc -l` | 20 | `20`，EXIT=0 | 附录 A-1 | `VERIFIED` |
| SC-2 | 存在机械校验器（非 Agent） | 全量测试 | `python -m pytest -q` | 全绿 | `350 passed`，EXIT=0 | 附录 A-2 | `VERIFIED` |
| SC-3 / AC-02 | C2 拒答准确率 100% | 评测 C2 类 | `python -m eval.run --suite frozen-01 --category C2` | 4/4，门成立 | `C2 拒答准确率：4/4　门成立：True　存活题数满足下限`，EXIT=0 | 附录 A-7 | `VERIFIED` |
| SC-4 / AC-04 | 问题集 ≥20 题且已冻结 | 哈希 + 时间戳 | `cd eval/frozen-01 && sha256sum -c SHA256SUMS` | 21 行 OK | 21 行 `OK`，无非 OK 行，EXIT=0 | 附录 A-6、`eval/frozen-01/FREEZE.md` | `VERIFIED` |
| SC-5 / AC-10 | 仓库零非公开数据 | 自动扫描 | `python -m semantic_layer scan --json` | findings 空 | `rules_version: 2`、`findings: []`，EXIT=0 | 附录 A-4 | `VERIFIED` |
| §7 门 5 | 构造错误作废率 ≤10% 且作废清单公开 | 评测运行器 | 同 SC-3 | ≤10% | `构造错误作废率 0.0%（上限 10%，未超限）`，作废 0 题 | 附录 A-7 | `VERIFIED` |
| §5.1 元规则 | `advisory_only` 占比 ≤50% | 统计 + 阈值门 | `python -m semantic_layer stats --json --fail-over 0.5` | 退出码 0 | `advisory_ratio: 0.19008264462809918`（19.0%），`unclassified: 0`，EXIT=0 | 附录 A-5 | `VERIFIED` |
| D-012 | POC-01 冻结产物未被改动 | 哈希 | `cd docs/agent/poc-01 && sha256sum -c SHA256SUMS` | 5 行 OK | 5 行 `OK`，EXIT=0 | 附录 A-6 | `VERIFIED` |
| T-01-41 | VERIFY 模式未顺手改实现 | git 状态 | `git status --porcelain metrics/_flags.yaml eval/frozen-01/ docs/agent/poc-01/` | 输出为空 | 空，EXIT=0 | 附录 A-8 | `VERIFIED` |
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
（各 `0.2857142857142857`，7 条中 2 条 advisory）。逐份分项见附录 A-5。
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

`docs/agent/phase-01/` 下**没有任何 `flag-requests-*.md`**（附录 A-9）。
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

### Phase 1 · 附录 A —— 逐字命令输出

全部执行于 2026-08-16，工作目录为仓库根（除非命令自带 `cd`），
解释器为 `.venv/Scripts/python`（本机 Python 3.14；默认 `python` 是 3.8.5，**不可用**）。

**A-1 指标数量**
```
$ ls metrics/*.yaml | grep -v '_flags' | wc -l
20
EXIT=0
```

**A-2 全量测试**
```
$ .venv/Scripts/python -m pytest -q | tail -3
........................................................................ [ 82%]
..............................................................           [100%]
350 passed in 10.33s
EXIT=0
```

**A-3 定义校验（AC-01）**
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

**A-4 非公开数据扫描（AC-10）**
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

**A-5 元规则统计（§5.1）**
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

**A-6 两处冻结校验（D-012）**
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

**A-7 C2 类评测（AC-02 / §7 门 2、门 5）**
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

**A-8 VERIFY 模式未改动冻结产物与词表（T-01-41 / T-01-44）**
```
$ git status --porcelain metrics/_flags.yaml eval/frozen-01/ docs/agent/poc-01/
（无输出）
EXIT=0
```

**A-9 flag 新增请求（判定三）**
```
$ ls docs/agent/phase-01/flag-requests-*
ls: cannot access 'docs/agent/phase-01/flag-requests-*': No such file or directory
EXIT=2
```

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
