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
| SC-2 | 30 个字段中 ≥24 个能抽出并映射，**计数口径 = 取到的值经逐个人工核对正确** | 人工逐字段核对 | Task 4 的检查点（`01.5-06-PLAN.md`），2026-08-30 抽查 9 字段 + 2 指标手算 | ≥24 | **2026-08-30 抽查后仍不足 24，判定不变。** 抽查 9 字段（`bs.total_equity` 及四个「行在格子空」有息负债分项、`is.net_profit`、`is.net_profit_attributable_to_parent`、`is.operating_revenue_current`、`is.operating_revenue_prior_as_presented`）逐字对照茅台 2023 年报原文（`data/raw/600519_2023.pdf`，pdfplumber 空密码打开），**9/9 与 `PROBE-14.md` / `TRACER-EVIDENCE.md` 记录逐字一致，零不一致**；其中 4 个是 wave 2 字段（此前只有 `PROBE-14.md` 自报「正确」，未经独立人工核对），今日起计入分母。累计：wave 1 `bs.*` 15（`C.3` 既有）+ 今日新增 wave 2 字段 4 = **19 / 29**，**仍 < 24**。其余 10 个字段（`is.operating_cost`、`is.selling_expense`、`is.administrative_expense`、`is.financial_expense`、`cfs.*` 2 个、`notes.*` 3 个、`kpi.roe_weighted_average_disclosed`）尚未独立核对。**➜ 2026-08-31（§D.17）把这 10 个一次核完，10/10 一致，零不一致 ⇒ 累计 29 / 29 ≥ 24，门槛达成。**其中四处是真正的辨析测试而非「数字碰巧相同」：`营业成本` vs `二、营业总成本`（差 4 倍、标签前缀包含）、`34.19` vs 干扰项 `34.20`（差 0.01、标签整体包含）、`非经常性损益合计` 有一次跨页算术互证（p5 两行相减 = p6 合计，逐字相同）、`加权平均净资产收益率` 有第二次互证（34.19 − 30.26 = 版面自印的「增加3.93个百分点」）。⚠️ **状态栏未自行改判** —— legwork 是执行者产出的，签署由操作者做（§C.13） | `N-37`、`D-026`、§D.14、§D.16、**§D.17** | ✅ **PASS**（2026-08-31 由操作者签署，29/29 ≥ 24；效力限定同 `SC-8`，见 §C.13 —— 核对由执行者执行、操作者审阅接受） |
| SC-3 | 区分「行在但格子空 = 0」与「整行不存在 = 缺失」，各有真实样本驱动的回归用例 | 全量测试 | `python -m pytest tests/test_missing_semantics.py -q` | 两类各有用例且全绿 | 格子空 4 条（短期借款 / 交易性金融负债 / 长期借款 / 应付债券，茅台 2023 实测）+ 整行不存在 2 条 + 「空格子是一次成功的抽取而不是失败」1 条；有息负债率在两种批次上分别**算得出**与**拒答**，EXIT=0 | `tests/test_missing_semantics.py`、§D.1 | **PASS** |
| SC-4 | 抽取产物带出处：PDF 的 SHA-256 + 巨潮源 URL + 页码 + 计量单位与币种 | 打印一条真实记录的全部出处 | 见 §D.13 | 四件套齐全 | 四件套全部非空，且**多于** SC-4 的要求：另带 `anchor_page`（D-019）、`column_header`（D-016）、`header_inherited`（继承留证）、`mapping_version`（L-38）、`selection` 三元组（D-023）、`batch_id`（D-024）。`AC-05` 齐全率 **210/210 = 1** | §D.13 | **PASS** |
| SC-5 | ≥5 个指标算出真实数值，并与 AKShare 交叉校验；不一致时置标记而不是静默选一个 | 端到端算一次 + 跨源对照 | 见 §D.11 / §D.12 | ≥5 个有数值；对照有逐字段判定 | **8 个指标全部算出数值**（跨三张合并报表一个批次）；跨源对照 **24 个字段**：`AGREES` 20 / `INCOMPARABLE` 4 / `DISAGREES` 0，触发占比 0/20，未超 `D-029` 的 1/3 阈值，EXIT=0 | §D.11、§D.12 | **PASS** |
| SC-6 | 默认不保留 PDF，`--keep-pdf` 是显式开关 | 读签名 + 读调用点 | `grep -rn 'keep_pdf' src/` | 默认 `False`，且 CLI 有显式开关 | `download.py:356` `keep_pdf: bool = False`；`__main__.py:46` 是显式 `dest="keep_pdf"` 的开关；`pipeline.extract_batch` 用 `TemporaryDirectory` 接，`with` 退出即删。`.pdf` 同时在 `.gitignore` 与 `scan_rules.yaml` 的 `forbidden_tracked_file_types` 里 | `src/extractor/download.py:356`、§D.1 | **PASS** |
| SC-7 | 勾稽校验是**阻断式**的：不通过即拒答而非记日志；一条真实通过用例 + 一条构造失败用例 | 全量测试 + 负控制 | `python -m pytest tests/test_reconciliation.py -q` | 阻断且两类用例都在 | `formula.py:541/549` 不通过即返回 `Refusal(RECONCILIATION_FAILED)`（`D-025` 第 9 支拒答码），不是日志；真实通过用例跑在茅台 2023 上，构造失败用例差额 `-1.00`；**负控制已按三步程序实跑**（§A.1–A.2） | §A、`tests/test_reconciliation.py`、§D.1 | **PASS** |
| SC-8 | 抽取器的验收看「取到的值」，不看「命中数」 | **人工**逐字段核对 | Task 4 检查点（`gate="blocking"`），§D.16 | 操作者逐字段看取到的值 | ✅ **2026-08-30 由操作者签署 `PASS`。** 抽查 9 字段逐字对照茅台 2023 年报原文，**9/9 一致，零不一致**；两处历史高风险点都没有复现 —— `bs.total_equity` 没有重演 `A-4` 的「匹配到章节小标题而数值为空」，净利润两行的全角 `－`（U+FF0D）与半角 `-`（U+002D）与 `PROBE-14.md` §1(c) 的描述逐字符相符。2 个指标手算复算与 `COMPUTED-VALUES.md` 的差额在 `1e-30` 量级，是十进制截断/舍入，不是真实不一致。⚠️ **留痕必须写清的一点**：翻 PDF 读数这一步是**执行者做的**（§D.16 自陈），操作者**复核该报告后接受结论并明确授权执行者代为落笔签署**。⇒ 本行的效力是「**操作者审阅并接受了一份执行者产出的核对报告**」，**不是**「操作者本人逐页看过 PDF」。两者在证据强度上不同，不合并表述 —— `SC-8` 当初写进 ROADMAP 的用意正是让**非抽取器的一方**去查抽取器 | §D.16 | **PASS**（限定见左栏与 §C.13） |
| AC-01 | 20 份口径定义字段齐全且合规 | 自动校验 | `python -m semantic_layer validate` | 20/20 合规 | `合计 0 项不合规，涉及 0 / 20 份定义`，EXIT=0 | §D.3 | **PASS** |
| AC-05 | 每条回答产出证据链，字段齐全率 100% | `pipeline.completeness_report()` | 见 §D.13 | 齐全率 = 1 | 真实批次 **210/210 = 1**，`meets_ac05 = True`。计数按 `PROJECT_SPEC` §9 写死的口径（有真值才算，空串 / null / 占位值 / 恒零计数不计）。⚠️ **覆盖面见 §C.2 的盲区** | §D.13、`tests/test_evidence_ids.py` | **PASS**（限定见 §C.2） |
| AC-10 | 仓库内零非公开数据 | 自动扫描 | `python -m semantic_layer scan` | findings 空 | `未扫出非公开数据风险（规则版本 2）`，EXIT=0 | §D.2 | **PASS** |
| `J-6` | 证据标识的字面存在性可机械检查 | 新增测试 | `python -m pytest tests/test_evidence_ids.py -q` | 正向 + 负向都在 | 14 条全绿；负向用例把 `field_id` 换成映射表里没有的串后被抓住且失败信息点名那个串。三条负控制按三步程序实跑（见 `b0aebf9` 提交信息） | `tests/test_evidence_ids.py`、§D.1 | **PASS** |
| `J-7` / `L-2` | 取数口径三元组齐全，缺任一项判失败 | 同上 | 同上 | 三项非空 | 真实批次三项全非空；逐项各造一次空值，每次都拉低齐全率并在 `gaps` 里点名 | `tests/test_evidence_ids.py` | **PASS** |
| `D-018` / `D-016` | 两道闸门各有一条负控制，且红的原因正确 | 造回归 → 看红 → 回退 | 见 §A | 都会红且原因正确 | 见 §A 四段实跑输出 | §A | **PASS** |

### §C 本阶段明确的证据缺口（不留白、不粉饰）

**C.1 样本覆盖是单公司单年为主 —— 2026-08-31 把「为什么」查清楚了。**
三张报表的**全部数值**取自贵州茅台 2023（`600519_2023.pdf`，143 页）。

⚠️ **本条原来只写到「没跑过，所以没有证据」。跑了。** 把完整的抽取 + 计算链
拉到万华化学 2019（`600309_2019.pdf`，213 页）上，**逐层撞出三道障碍，现在它们有名字了**：

| # | 障碍 | 状态 |
|---|---|---|
| 1 | **报表锚点不唯一** —— 「合并资产负债表」定位到 **3 个**：p71 是真标题，另两个在 p112（一句附注正文 + 一张对照表的列头行）⇒ 「恰好 1 个」判定不过，整条计算拒答 | ✅ **已修**：锚点限定在 `[二、财务报表, 三、公司基本情况)` 区间内。两家实测 —— 茅台 p58–p75、万华 p71–p87，八个报表锚点各自都在区间内 |
| 2 | **映射表的 `label_fragments` 是茅台专属的** | ✅ **已解决**：量了才知道 25 个里 21 个直接命中，只有 4 个要补变体，且**零代码改动**。详见 §C.1.1 |
| 3 | **数值列不止两列** —— 万华那一行是 `43,931,258,971.63 / 39,582,324,008.33 / 27,853,995,769.94` **三列**（与它 `restated = True` 一致，列出了调整后/调整前）；现有列绑定按「期末 / 期初」两列建模 | ✅ **不是障碍**：列绑定按会计年度文字解析，第三列不被绑成任何取数角色。⚠️ **但量的过程里查出一处真缺陷**（两列同 role 时静默挑一个），已修。详见 §C.1.3 |

⇒ **顺序是固定的**：不解决 1 就撞不到 2，不解决 2 就撞不到 3。**三道全部走完，整条链在第二家公司上跑通**（§C.1.4）。⚠️ 三道里有**两道**我事先的判词是错的 —— 见 §C.1.1 / §C.1.3。

### C.1.1 ✅ 第 2 层已解决 —— 但先记两次我自己的错判

**错判一**：把它记成「25 个字段的数据工作」。量了之后，**25 个里 21 个用茅台的变体直接命中万华**
（报表格式是规范化的，标签大面积相同），**只有 4 个不命中**。

**错判二**：把其中两个记成「要新的缝合模式，该是一件单独的任务」。
**再量：不需要动缝合器。** 万华那两行的**数值就印在第一行上**，
`label_lines` 只有前半截 —— 一条普通的**单片段变体**即可：

```
购建固定资产、无形资产和其他长期    17,814,814,580.17  10,545,415,710.37   ← 值在这一行
资产支付的现金                                                            ← 续行不参与匹配
```

⇒ **四个全部用数据变体解决，零代码改动。**
**25 个字段在两家公司上全部命中，且无一多命中。**

⚠️ 补 `bs.total_equity` 时有一处真陷阱：万华同页上方还有 `所有者权益（或股东权益）：`
—— **小节标题，只差一个全角冒号**。逐字整行相等把它挡在外面；
改成子串或前缀匹配取到的就是那个数值为空的标题行 —— 那正是 `A-4` 的真实失手。
⇒ 这些是「多一种措辞」，**不是「放宽匹配」**。

### C.1.2 ⬜ 那条「显然该加」的缝合规则量过了，是错的

虽然第 2 层已经不需要它，这次测量仍要留档 —— **它挡住了一个会弄坏一切的改动**。

模拟「值行 + 纯标签行 ⇒ 合并」：**万华会误并 48 处、茅台会误并 32 处**，例如
`货币资金` + `结算备付金`、`存货` + `持有待售资产`、`短期借款` + `向中央银行借款`。

⇒ **根因是「空行项目」**：标准模板里列着、而本公司没有金额的那些行，
**本身就是纯标签行，一张表里有几十个**，与「续行」在版面上**完全同形**。
「不以全角冒号结尾」这类判别式只挡得住小节标题（3–4 处）。

⚠️ **现有三行缝合之所以安全，正是因为它要求中间是纯数值行 ——
一个空行项目不会产出纯数值行。** 已写进 `_stitch` 的 docstring。

### C.1.3 🔴 第 3 层不是障碍，但它藏着一个静默歧义（已修）

万华的合并资产负债表确实**有三列**，而列绑定按会计年度文字解析，
所以**第三列没有被绑成任何取数角色** —— 三张表的取数全部正确。
⇒ 「按两列建模会破」也是一句没量过的话。**这是同日第三次。**

**但量的过程里查出一处真的**：三列中**两列被解到同一个口径**——

```
2019年12月31日 -> 期末余额
2018年12月31日 -> 期初余额
2018年1月1日   -> 期初余额     ← 与上一列同 role
```

而 `by_role` 原实现是「返回第一个匹配的」⇒ **静默挑一个**。
今天没有字段映射到 `期初余额`，所以没有产出错数 —— **但那是运气，不是设计**。
✅ **已修**：同一口径解出多列即抛 `AmbiguousColumnRole`，**不挑一个**；
「取不到」仍返回 `None` —— 两者原因不同、处置也不同，不合并。

### C.1.4 ✅ 成果：完整链路在第二家公司上跑通

万华 2019 六个指标全部算出（含跨表的毛利率与自由现金流），`restated` 正确置位。

**两个值独立手算核对过**（从版面读数，不是照抄抽取器输出）：

| 指标 | 版面依据 | 手算 | 抽取器 |
|---|---|---:|---:|
| 资产负债率 | p73：总计 `96,865,322,655.29`、所有者权益 `43,931,258,971.63` | 0.5465 | 0.5465 ✓ |
| 毛利率 | p75：营业收入 `68,050,668,650.78`、营业成本 `48,997,610,501.85` | 0.27998 | 0.27998 ✓ |

➜ **2026-09-02 补齐**：25 个取值已逐字段核对，**25 / 25 一致，零不一致**（§D.18）。
上面那句「没有人逐字段核对过万华那 25 个取值」**至此不再成立**。

⚠️ 但**限定三条，一条都不能省**：

1. **效力与 `SC-2` / `SC-8` 同档**（§C.13）：读数路径独立于抽取器（走 `pdfplumber` 原始版面文本），
   **执行者不独立**。25/25 是 legwork，**不自行改判任何状态栏**。
2. **这不等于「`SC-2` 在万华上成立」**：`SC-2` 的分母是茅台那 29 个（含 `kpi` / `notes` 四支），
   万华这 25 个只是三张合并报表那一路。**两个分母不是同一个集合。**
3. 🔴 **25 个里有 2 个的干扰项与目标同值**（`营业收入` = `营业总收入`、`净利润` = `持续经营净利润`），
   **取错了也看不出来** —— 「25/25 一致」这句话会盖住这件事，所以点名写在这里。

**C.2 `AC-05` 抓不到「证据不相关」。**
这是写在 `PROJECT_SPEC.md` §9 里的**已知盲区**，不是本轮新发现的：
`AC-05` 只覆盖「证据**缺失**」。实证是 hello-agents 的 `arun_stream` 每步调两次 LLM，
屏幕上读到的推理与实际执行的 `tool_calls` 在 `temperature > 0` 时**无因果关系**，
而字段齐全率仍是 100%。同源性由 `AC-06` 的人工复核承担，**目前无自动判据**。
⇒ 上表 `AC-05` 那行的 `PASS` 只能读成「字段都有真值」，**不能读成「证据链是对的」**。

**C.3 `SC-2` 的分母里有 10 个字段从未经人工核对。**（2026-08-30 更新）
计数口径写死的是「取到的值经逐个人工核对正确」。此前经人工核对的只有 wave 1 的
15 个 `bs.*`；2026-08-30 抽查新增 4 个 wave 2 字段（`is.net_profit` /
`is.net_profit_attributable_to_parent` / `is.operating_revenue_current` /
`is.operating_revenue_prior_as_presented`，见 §D.16），累计 **19 / 29**，
**仍 < 24**。`N-37` 记的「29/29 达成」**是按抽取器能取到值来数的**，
不是按口径数的。剩余 10 个字段（`is.operating_cost` / `is.selling_expense` /
`is.administrative_expense` / `is.financial_expense` / `cfs.*` 2 个 / `notes.*` 3 个 /
`kpi.roe_weighted_average_disclosed`）尚未独立核对，`SC-2` 仍判 `UNVERIFIED`。

**➜ 2026-08-31 更新：那 10 个已一次核完（§D.17），10/10 一致，零不一致，累计 29 / 29 ≥ 24。**
**⇒ 本条描述的「覆盖缺口」已消除，但 `SC-2` 的状态栏仍未改判**，原因不是覆盖，
而是 §C.13 那一条：**29 个字段的核对全部是执行者做的**。
计数口径的字面是「**人工**核对」，而实际执行的是「执行者读 PDF 原始版面文本、操作者审阅报告」。
读数路径确实独立于抽取器（走 `pdfplumber` 原始文本，不经 `locate` / `mapping` 任何一层，
抽取器若在行缝合、列绑定、区间归属上有错会在这里表现为对不上）——
**这是代码路径级的独立，不是执行者级的独立。**
⇒ 签署由操作者做；若要把证据强度补到 `SC-2` / `SC-8` 的设计意图那一档，
需要一次由**非本抽取器产出方**独立翻页的复核。

**➜ 2026-08-31 操作者已签署 `SC-2` = `PASS`（29/29）。本条从「覆盖缺口」降级为「效力限定」**：
覆盖的问题没有了，**独立性的问题还在**，且它不会因为签署而消失。
记在这里是为了让下一个读 `SC-2 = PASS` 的人知道这个 `PASS` 是怎么来的。

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

**C.7 `restated` 的跨排版验证：去找了，找到了一个反例。**（2026-08-31 更新）

⚠️ **本条原来写的是「反例形态从未被观察到，也没有去找过」。那句话已经过期。**

去找了 —— 本机三份年报，两个交易所模板：

| 样本 | 章节标题措辞 | 判定 | 与年报自述互证 |
|---|---|---|---|
| 茅台 600519 · 2023（上交所） | `七、 近三年主要会计数据和财务指标` | `True` | p5「本公司对比较期间相关财务数据进行追溯调整」 |
| 万华 600309 · 2019（上交所） | 同上 | `True` | 区间内命中 4 行 |
| **顺丰 002352 · 2021（深交所）** | `主要会计数据和财务指标`，**无「近三年」** | 🔴 **`False`** | p12「**公司无需追溯调整或重述以前年度会计数据**」 |

⇒ **反例形态已观察到一个**，且规则给出的 `False` 与年报自述一致。
这也是 `restated is False` 这条分支**第一次被真实数据走到**
（它的不变量「判 `False` 不得带命中行」此前只有构造样本验过）。

🔴 **找它的过程本身查出一个真缺陷**：顺丰那份**原来判 `undecidable`** ——
不是因为读不出来，而是因为**章节标题少了「近三年」三个字**，锚点对不上。
**一个本来知道的答案，被一处措辞差异变成了「判不出」。**
已补入第二种措辞（两种都逐字列出，**没有退化成子串匹配** ——
本模块的锚点判定靠的正是「整行逐字相等（或序号 + 逐字相等）」，
而 `近三年…` 恰好包含 `主要会计数据…`，改子串会同时命中正文里任何提到这几个字的行）。

⚠️ **仍然不写成「已验证」，三条限定照旧**：
1. **三家公司、两个模板**，不叫「跨排版已验证」。
2. **另一种反例仍是零样本**：「重述了却没拆两列」—— 三家里没有这一形态，
   且没有已知的办法去构造它（要一份真实年报）。
3. 顺丰那份**是靠补入第二种措辞才判得出来的**；第四家公司完全可能有第三种措辞。

**验证方式**：`tests/test_report_metadata.py::test_三份真实年报上的判定与年报自述一致`
（三条，期望值照抄**年报自己说的话**，不是照抄抽取器的输出）。
⚠️ 这三条把本地全量套件从约 77 秒拉到约 162 秒（638 页 PDF 解析）；
**CI 不受影响** —— `data/raw/` 从不进版本控制，CI 上一律 `skip`。

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

**C.13 `SC-8` 的 `PASS` 是「审阅并接受」，不是「亲自逐页看过」。**（2026-08-30）
`SC-8` 加进 ROADMAP 的起因是 `A-4`：`bs.total_equity` 匹配到章节小标题而数值为空，
**报表上算命中、实际取错行**，而一个只会数命中的验收者会放过它。
⇒ 这条标准的设计意图是让**非抽取器的一方**去查抽取器。
本轮实际发生的是：**执行者翻 PDF 读数、执行者报数、操作者审阅并接受**。
零不一致是真的，A-4 没有复现也是真的（有逐字摘录为证）；
但「查的人独立于被查的人」这一层**比设计意图弱**。
不把它写成「操作者逐字段看过」，是因为那句话会让下一个读者高估这份证据的强度。
⇒ 若要把它补到设计意图那一档，需要一次由操作者本人（或任何非本抽取器产出方）
独立翻页的复核；那也是把 `SC-2` 从 19 推到 ≥24 的同一个动作。

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

#### D.16 2026-08-30 人工抽查：9 字段逐字对照 PDF 原文 + 2 指标手算复核

**背景**：`01.5-06-PLAN.md` Task 4（`gate="blocking"`）要求操作者本人翻 PDF 逐字核对，
执行者代答无效。本节记的是执行者受操作者直接指派完成的**抽查 legwork**（读 PDF、报数），
**不是操作者本人的签署**——`SC-8` 那一行的最终判定仍待操作者过目本节后自己签。

**样本**：`data/raw/600519_2023.pdf`（贵州茅台 600519 2023 年报，143 页）。
Read 工具直接打开报密码保护错误；用项目自带 `.venv` 的 pdfplumber 以空密码 `password=''`
打开成功，说明这是所有者密码（限编辑/打印）而非用户密码（限查看）。
`pdfplumber.pages[N-1].extract_text(layout=True)` 的输出页脚逐字印着 `N / 143`，
确认「打印页码 N」= `pages[N-1]`，无前置偏移。

**抽查字段（9 个）逐字对照结果**：

| 字段 | PDF 页 | 原文（逐字摘录） | 列 | PDF 上的值 | 与 `PROBE-14.md`/`TRACER-EVIDENCE.md` 记录 | 判定 |
|---|---:|---|---|---:|---|---|
| `bs.total_equity` | 61 | `所有者权益（或股东权` \| 数值行 \| `益）合计`（三行缝合） | 2023年12月31日 | 223,656,469,294.82 | 逐字相同 | **一致**。紧邻上一行「归属于母公司所有者权益（或股东权益）合计」= 215,668,571,607.43 是不同的行，`bs.total_equity` 取的不是那一行——本次未复现 `A-4` 的「匹配到章节小标题、数值为空」 |
| `bs.short_term_borrowings` | 59 | `短期借款`，行内两列均无数字 | 2023年12月31日 | （空） | `EMPTY_CELL` | **一致**，确认行在格子空 |
| `bs.trading_financial_liabilities` | 59 | `交易性金融负债`，行内两列均无数字 | 2023年12月31日 | （空） | `EMPTY_CELL` | **一致**，确认行在格子空 |
| `bs.long_term_borrowings` | 60 | `长期借款`，行内两列均无数字 | 2023年12月31日 | （空） | `EMPTY_CELL` | **一致**，确认行在格子空 |
| `bs.bonds_payable` | 60 | `应付债券`，行内两列均无数字 | 2023年12月31日 | （空） | `EMPTY_CELL` | **一致**，确认行在格子空 |
| `is.net_profit` | 64 | `五、净利润（净亏损以"－"号填` \| `列）` | 2023年度 | 77,521,476,277.80 | 逐字相同 | **一致**（wave 2 字段，今日首次独立核对） |
| `is.net_profit_attributable_to_parent` | 64 | `1.归属于母公司股东的净利润` \| `（净亏损以"-"号填列）` | 2023年度 | 74,734,071,550.75 | 逐字相同 | **一致**（wave 2 字段，今日首次独立核对）。括号内减号字符现场确认：`净利润` 行是全角 `－`（U+FF0D），本行是半角 `-`（U+002D），与 `PROBE-14.md` §1(c) 的描述逐字符相符 |
| `is.operating_revenue_current` | 63 | `其中：营业收入` | 2023年度 | 147,693,604,994.14 | 逐字相同 | **一致**（wave 2 字段，今日首次独立核对）。上方 `一、营业总收入` = 150,560,330,316.45 是另一行，现场确认两行不是同一个数 |
| `is.operating_revenue_prior_as_presented` | 63 | 同上（`其中：营业收入`） | 2022年度 | 124,099,843,771.99 | 逐字相同 | **一致**（wave 2 字段，今日首次独立核对） |

**9/9 一致，零不一致。**

**指标手算复核（2 个，从今日在 PDF 上现场核对的原始数字独立起算，不是照抄 `COMPUTED-VALUES.md` 已算出的结果）**：

```
debt_to_asset_ratio = bs.total_liabilities / bs.total_assets
  = 49,043,190,797.43 / 272,699,660,092.25
  = 0.1798432413917914711797119101053209097979...（Decimal, prec=40）
  文档记录：0.1798432413917914711797119101（COMPUTED-VALUES.md §1.1）
  差额 ≈ 5.32e-30，纯截断误差，非真实不一致 → 一致

interest_bearing_debt_ratio = (非流动负债一年内到期57,054,879.48 + 租赁负债266,636,234.04) / bs.total_assets
  = 323,691,113.52 / 272,699,660,092.25
  = 0.001186987594375806682042917961766218623181...（Decimal, prec=40）
  文档记录：0.001186987594375806682042917962（COMPUTED-VALUES.md §1.5）
  差额 ≈ 2.34e-31，纯舍入误差，非真实不一致 → 一致
```

**SC-2 计数（按 `01.5-02-PLAN.md` 已裁决的口径：能抽出 = 取到的值经逐个人工核对正确）**：

- 抽查前累计（`C.3`，wave 1 `bs.*`）：**15**
- 今日新增独立核对且一致的字段（wave 2，此前只有 `PROBE-14.md` 自报「正确」）：`is.net_profit` /
  `is.net_profit_attributable_to_parent` / `is.operating_revenue_current` /
  `is.operating_revenue_prior_as_presented` = **4**
  （`bs.total_equity` 与四个有息负债分项已计入既有 15，今日重复核对不增量，但为四个分项首次补上
  了详细人工核对证据——此前 `COMPUTED-VALUES.md` 只记了 `EMPTY_CELL` 状态，没有逐字对照 PDF 的记录）
- **累计 19 / 29，< 24，门槛未达成**
- 尚未独立核对的 10 个字段：`is.operating_cost` / `is.selling_expense` /
  `is.administrative_expense` / `is.financial_expense` / `cfs.net_cash_flow_from_operating_activities` /
  `cfs.cash_paid_for_fixed_intangible_and_other_long_term_assets` /
  `notes.nonrecurring_pl_net_attributable_to_parent` / `notes.restatement_flag` /
  `kpi.roe_weighted_average_disclosed` / `notes.business_combination_type`

**`SC-2` 判定：`UNVERIFIED`**（19/29，未达 ≥24 门槛——不是发现了错误，是覆盖不够）。
~~**`SC-8` 判定：`UNVERIFIED`**（legwork 已交、9/9 无不一致，但按 `01.5-06-PLAN.md` 的阻塞式设计，
最终签署须由操作者本人完成，执行者不代签）。~~

✅ **2026-08-30 操作者签署：`SC-8` 判 `PASS`。** 操作者过目本节后确认「9 个字段 + 2 个手算指标
全部对得上，没有一个对不上的」，并**明确授权执行者代为落笔**。落笔即本次。
⚠️ **授权的是落笔，不是核对**：读 PDF 那一步仍是执行者做的（见本节开头的自陈），
操作者做的是**审阅并接受这份报告**。`SC-8` 行按此如实措辞，不写成「操作者逐页看过 PDF」。
**`SC-2` 判定不变：`UNVERIFIED`**（19/29 < 24）—— 缺的是覆盖，不是正确性，零不一致。

#### D.17 2026-08-31 剩余 10 字段逐字核对：`SC-2` 的覆盖补齐 legwork

**背景**：`SC-2` 于 08-30 记 `UNVERIFIED`（19 / 29 < 24），缺口是**覆盖不是正确性**。
本节把剩余 10 个字段一次核完。**与 §D.16 同样是执行者产出的 legwork**，
`SC-2` 那一行的判定仍待操作者过目本节后签 —— 理由见 §C.13。

**方法上的一点必须写清**：本次读数走的是
`pdfplumber.open(...).pages[N-1].extract_text(layout=True)` 的**原始版面文本**，
**不经过 `locate` / `mapping` 任何一层**。
⇒ 抽取器若在行缝合、列绑定、区间归属上有错，会在这里表现为**对不上**。
这是**代码路径级**的独立，不是**执行者级**的独立 —— 后者仍缺，见 §C.13。

**样本**：`data/raw/600519_2023.pdf`（贵州茅台 600519 2023 年报，143 页，pdfplumber 空密码打开）。

| # | 字段 | PDF 页 | 原文（逐字摘录） | PDF 上的值 | 文档记录 | 判定 |
|---|---|---:|---|---:|---|---|
| 1 | `is.operating_cost` | 63 | `其中：营业成本` \| 附注 `40` | 11,867,273,851.78 | `COMPUTED-VALUES.md` 同值 | **一致** |
| 2 | `is.selling_expense` | 63 | `销售费用` \| 附注 `43` | 4,648,613,585.82 | 同值 | **一致** |
| 3 | `is.administrative_expense` | 63 | `管理费用` \| 附注 `44` | 9,729,389,252.31 | 同值 | **一致** |
| 4 | `is.financial_expense` | 63 | `财务费用` \| 附注 `46` | -1,789,503,701.48 | 同值 | **一致**（负值；减号是 **ASCII U+002D**，现场用 `unicodedata` 确认，不是全角 `－`） |
| 5 | `cfs.net_cash_flow_from_operating_activities` | 67 | `经营活动产生的现金流量净额` | 66,593,247,721.09 | 同值 | **一致** |
| 6 | `cfs.cash_paid_for_fixed_intangible_and_other_long_term_assets` | 67 | `购建固定资产、无形资产和其他长` \| 数值行 \| `期资产支付的现金`（**三行缝合**） | 2,619,755,888.79 | 同值 | **一致** |
| 7 | `notes.nonrecurring_pl_net_attributable_to_parent` | 6 | `合计`（非经常性损益项目和金额表） \| 列 `2023年金额` | -18,492,874.77 | `PROBE-14.md` §11 同值 | **一致** |
| 8 | `notes.restatement_flag` | 5 | 表头三处印着 `调整后` / `调整前` | `True` | `PROBE-14.md` §12 同值 | **一致** |
| 9 | `kpi.roe_weighted_average_disclosed` | 5 | `加权平均净资产收益率（%）`（**三行缝合**） \| 列 `2023年` | 34.19 | `PROBE-14.md` §14 同值 | **一致** |
| 10 | `notes.business_combination_type` | 120 | 子项 1/2/3 各印 `□适用  √不适用` | **∅（空集）** | `D-028`：空集即表示本期无企业合并 | **一致** |

**10 / 10 一致，零不一致。**

**四处是真正的辨析测试，不是「数字碰巧相同」** —— 这一段才是本节的价值所在：

1. **#1 `营业成本` vs `二、营业总成本`。** 同一页上并列两行：
   `二、营业总成本 46,960,889,468.54` 与 `其中：营业成本 11,867,273,851.78`，**相差约 4 倍**。
   标签是**前缀包含关系**（「营业总成本」含「营业成本」三字）。取到的是后者，分对了。

2. **#9 `34.19` vs `34.20`。** p5 上紧邻两行：
   `加权平均净资产收益率（%）` = **34.19**，
   `扣除非经常性损益后的加权平均净资产收益率（%）` = **34.20**。
   两个数**只差 0.01**，而后者的标签**整个包含**前者的标签字符串。
   映射表的 `label_fragments` 是「按顺序、逐字**整行**相等的片段序列，不是子串」——
   这条设计在这里第一次被真实数据检验：干扰项折行后的片段是
   `["扣除非经常性损益后的加权平", "均净资产收益率（%）"]`，与目标的
   `["加权平均净资产收益率（%）"]` **逐行比不相等**，因此分得开。
   ⚠️ **若当初写成子串匹配，这里会静默取错，而两个数都「看起来合理」。**

3. **#7 有一次独立算术互证。** p5 的两行：
   `归属于上市公司股东的净利润` 74,734,071,550.75
   − `归属于上市公司股东的扣除非经常性损益的净利润` 74,752,564,425.52
   = **−18,492,874.77**，与 p6「合计」行**逐字相同**。
   ⇒ 年报里**两个互相独立的位置**给出同一个数，这比「我读到了这个数」强一档。
   另：p6 与 p7 **各有一个 `合计` 行**（p7 那个是 4,403,151,962.50，属另一张表），
   映射条目的 `statement: 非经常性损益项目和金额` 区间限定把 p7 挡在外面 —— 又一个真实干扰项。

4. **#9 还有第二次算术互证。** p5 同一行印着 `增加3.93个百分点`，
   而 34.19 − 30.26（2022 年调整后）= **3.93**。⇒ 版面自带的差额栏与取到的两个值自洽。

**#6 是 `A-6` 失效模式 1 的真实复现并被正确处理**：
`购建固定资产、无形资产和其他长` / `2,619,755,888.79 5,306,546,416.54` / `期资产支付的现金`
——标签折行导致**数值自成一行**，行首规则永远匹配不上。三行缝合把它接了回来。

**#8 的判据是「列头存在性」，不是取行值**：p5 的三处表头
（主要会计数据、资产类、主要财务指标）各印一组 `调整后` / `调整前`；
同页第 40–44 行的注文逐字写着「本公司对比较期间相关财务数据进行**追溯调整**」，
**列头与文字互证**。⇒ `restated = True`。
⚠️ 限定不变（`C.7`）：**反例形态一次都没观察到，也没有去找。**

**#10 的读法要写清，免得被读成「没抽到」**：p120 子项 1/2/3
（非同一控制下企业合并 / 同一控制下企业合并 / 反向购买）**各自都是 `□适用  √不适用`**
⇒ 集合为空。按 `D-028`「**取消 `无` 这个哨兵值，空集即表示本期无企业合并**」，
∅ 是**一个正确的值**，不是缺失。
同时 p121 子项 5「其他原因的合并范围变动」是 `√适用`
（定制营销公司 2023-12-18 清算注销完成），
⇒ `notes.consolidation_scope_change = True`。
**同一份年报上两个字段取值不同，本身就是 `D-020` 把它们拆开的证明**，本次现场再次确认。

**`SC-2` 计数（按已裁决口径：能抽出 = 取到的值经逐个人工核对正确）**：

- 08-30 抽查后累计：**19 / 29**
- 本次新增独立核对且一致：**10**
- **累计 29 / 29 ≥ 24 —— 门槛达成**（作废 1 条 `notes.reporting_period_months` 已按 `D-026` 移出分母，作废率 3.33% ≤ 10%）

~~⚠️ **本节不自行改判 `SC-2` 的状态栏。** legwork 已交、10/10 无不一致，
但按 `01.5-06-PLAN.md` 的阻塞式设计与 §C.13 记的限定，**最终签署由操作者做**，执行者不代签。~~

✅ **2026-08-31 操作者签署：`SC-2` 判 `PASS`（29 / 29 ≥ 24）。**
⇒ **Phase 1.5 的八条 Success Criteria 至此全部成立，本阶段收口。**
⚠️ **效力限定与 `SC-8` 同**（§C.13）：29 个字段的核对由**执行者**执行、操作者审阅接受。
读数路径独立于抽取器（走 `pdfplumber` 原始文本），**但执行者不独立于抽取器的产出方**。
这条限定不随签署消失 —— 它是这份证据**是什么**，不是它**够不够**。

#### D.18 2026-09-02 万华 25 个字段逐字核对：`C-1` 的 `SC-2` legwork

**背景**：§C.1.4 记着「`SC-2` 在万华上仍不成立 —— 只手算核了两个**派生结果**，
没有人逐字段核对过那 25 个取值」。本节把 25 个一次核完。
**与 §D.16 / §D.17 同样是执行者产出的 legwork，签署仍由操作者做**（§C.13）。

**方法**（与 §D.17 一致，故意不换）：读数走
`pdfplumber.open(...).pages[N-1].extract_text(layout=True)` 的**原始版面文本**，
**不经过 `locate` / `mapping` 任何一层**。抽取器若在行缝合、列绑定、区间归属上有错，
会在这里表现为对不上。⇒ **代码路径级独立，不是执行者级独立。**

**样本**：`data/raw/600309_2019.pdf`（万华化学 600309 · 2019 年报，213 页，pdfplumber 空密码打开）。
抽取器侧读数来自 `extract_batch("600309", 2019, plan=(bs/is/cfs 三张合并报表))`，**25 条全部 `SUCCESS`**。

| # | 字段 | 页 | 版面原文（逐字） | PDF 上的值 | 抽取器 | 判定 |
|---|---|---:|---|---:|---:|---|
| 1 | `bs.accounts_receivable` | 71 | `应收账款 七5` | 4,433,077,609.63 | 同值 | **一致** |
| 2 | `bs.inventory` | 71 | `存货 七9` | 8,586,883,294.06 | 同值 | **一致** |
| 3 | `bs.total_current_assets` | 71 | `流动资产合计` | 23,483,577,397.65 | 同值 | **一致** |
| 4 | `bs.total_assets` | 72 | `资产总计` | 96,865,322,655.29 | 同值 | **一致** |
| 5 | `bs.short_term_borrowings` | 72 | `短期借款 七31` | 20,034,036,150.27 | 同值 | **一致** |
| 6 | `bs.trading_financial_liabilities` | 72 | `交易性金融负债`（**行在，格子空**） | ∅ | `0.00` / `EMPTY_CELL` | **一致** |
| 7 | `bs.long_term_borrowings` | 72 | `长期借款 七43` | 5,962,595,245.57 | 同值 | **一致** |
| 8 | `bs.bonds_payable` | 72 | `应付债券`（**行在，格子空**） | ∅ | `0.00` / `EMPTY_CELL` | **一致** |
| 9 | `bs.accounts_payable` | 72 | `应付账款 七35` | 8,024,420,861.29 | 同值 | **一致** |
| 10 | `bs.non_current_liabilities_due_within_one_year` | 72 | `一年内到期的非流动负债 七41` | 3,324,127,445.00 | 同值 | **一致** |
| 11 | `bs.lease_liabilities` | 72 | `租赁负债`（**行在，格子空**） | ∅ | `0.00` / `EMPTY_CELL` | **一致** |
| 12 | `bs.total_current_liabilities_period_end` | 72 | `流动负债合计` | 44,799,566,175.61 | 同值 | **一致** |
| 13 | `bs.total_liabilities` | 72 | `负债合计` | 52,934,063,683.66 | 同值 | **一致** |
| 14 | `bs.minority_interests` | 73 | `少数股东权益` | 1,567,164,415.90 | 同值 | **一致** |
| 15 | `bs.total_equity` | 73 | `所有者权益（或股东权益）` \| 续行 `合计` | 43,931,258,971.63 | 同值 | **一致** |
| 16 | `is.operating_revenue_current` | 75 | `其中：营业收入 七59` \| 列 `2019年度` | 68,050,668,650.78 | 同值 | **一致** |
| 17 | `is.operating_revenue_prior_as_presented` | 75 | 同行 \| 列 `2018年度` | 72,837,108,238.47 | 同值 | **一致** |
| 18 | `is.operating_cost` | 75 | `其中：营业成本 七59` | 48,997,610,501.85 | 同值 | **一致** |
| 19 | `is.selling_expense` | 75 | `销售费用 七61` | 2,782,908,073.79 | 同值 | **一致** |
| 20 | `is.administrative_expense` | 75 | `管理费用 七62` | 1,433,850,380.23 | 同值 | **一致** |
| 21 | `is.financial_expense` | 75 | `财务费用 七64` | 1,079,748,165.38 | 同值 | **一致** |
| 22 | `is.net_profit` | 76 | `五、净利润（净亏损以“－”号填列）` | 10,593,318,819.77 | 同值 | **一致** |
| 23 | `is.net_profit_attributable_to_parent` | 76 | `1.归属于母公司股东的净利润（净亏` \| 续行 `损以“-”号填列）` | 10,129,985,097.55 | 同值 | **一致** |
| 24 | `cfs.net_cash_flow_from_operating_activities` | 79 | `经营活动产生的现金流量净额` | 25,932,941,200.65 | 同值 | **一致** |
| 25 | `cfs.cash_paid_for_fixed_intangible_and_other_long_term_assets` | 79 | `购建固定资产、无形资产和其他长期` \| 续行 `资产支付的现金` | 17,814,814,580.17 | 同值 | **一致** |

**25 / 25 一致，零不一致。**

##### 哪几条是真正的辨析测试（而不是「数字碰巧只有一个」）

这一段才是本节的价值。**不写这一段，25/25 只是「我把数抄了一遍」。**

1. 🔴 **同一页上并列着另一张报表 —— 而且值不同。** p73 下半页起是**母公司**资产负债表，
   p75 上半页是它的续页：那里印着 `负债合计 45,431,055,319.24`、
   `所有者权益（或股东权益）合 19,030,546,302.02`。
   与合并口径的 `52,934,063,683.66` / `43,931,258,971.63` **是两组不同的数、同样的标签**。
   ⇒ #13 与 #15 取对，靠的是报表锚点 + 章节区间，不是标签本身。**这是最强的一组干扰项。**
2. **前缀包含关系一次撞上四对**：`流动负债合计` ⊂ `非流动负债合计`、`负债合计` ⊂ 两者、
   `营业成本` ⊂ `营业总成本`（48,997,610,501.85 vs 56,574,893,322.83，**差约 1.15 倍**）、
   `所有者权益（或股东权益）` ⊂ `归属于母公司所有者权益（或股东权益）合计`
   （43,931,258,971.63 vs 42,364,094,555.73，**差 1.57 亿**，两个都「看起来合理」）。
   逐行整行相等把它们分得开；**换成子串或前缀匹配，这四处会静默取错。**
3. 🔴 **`交易性金融负债` 空，而同一份表的 `交易性金融资产` 有值**（p71 = 30,367,333.35）。
   #6 判 `EMPTY_CELL` 而不是去够那个 30,367,333.35 —— **「资产 / 负债」只差一个字**。
   同理 `一年内到期的非流动负债`（有值）vs `一年内到期的非流动资产`（空）。
4. **#25 的干扰项是同表同形的折行行**：`处置固定资产、无形资产和其他长期` \| `资产收回的现金净额`
   = 17,442,462.15，与目标 `购建…` 只差**头两个字**，且**同样折行**。
   两条的续行文字还不同（`资产支付的现金` vs `资产收回的现金净额`）—— 取的是 `购建` 那条。
5. **三个 `EMPTY_CELL` 都验证了「行在、格子空」而不是「行不在」**：
   `交易性金融负债` / `应付债券` / `租赁负债` 三行在 p72 上**都印着标签、整行无数字**。
   ⇒ 这是 `SC-3` 分界里的第三态，不是 `ROW_ABSENT`。

##### 七组版面自带的算术互证（比「我读到了这个数」强一档）

下面每一条的两侧都**印在年报上**，与抽取器无关；核对脚本用 `Decimal` 逐条比，**七条全部相等**：

| # | 恒等式 | 覆盖的字段 |
|---|---|---|
| 1 | 流动资产合计 + 非流动资产合计 = 资产总计 | #3 #4 |
| 2 | 流动负债合计 + 非流动负债合计 = 负债合计 | #12 #13 |
| 3 | 归属于母公司所有者权益合计 + 少数股东权益 = 所有者权益合计 | #14 #15 |
| 4 | 负债合计 + 所有者权益合计 = 负债和所有者权益总计 | #4 #13 #15 |
| 5 | 营业成本 + 税金及附加 + 销售费用 + 管理费用 + 研发费用 + 财务费用 = 营业总成本 | #18 #19 #20 #21 |
| 6 | 利润总额 − 所得税费用 = 净利润 | #22 |
| 7 | 经营活动现金流入小计 − 流出小计 = 经营活动现金流量净额 | #24 |

⇒ **25 个里有 15 个被至少一条页内恒等式独立约束住**，剩下 10 个只有「逐字读到」这一层证据。

##### 两处**不构成**辨析测试，必须点名

- **#16 `其中：营业收入` 与上一行 `一、营业总收入` 的值完全相同**（68,050,668,650.78）。
  ⇒ 这一条**取错了也看不出来**。它在茅台上是辨析测试（那里两个数不同），在万华上不是。
- **#22 `五、净利润` 与下一行 `1.持续经营净利润` 的值完全相同**（10,593,318,819.77）。同上。

⚠️ **这两条写在这里，是因为「25/25 一致」这句话本身会盖住它们。**
一致不等于每一条都被检验过 —— **值相同的干扰项，核对时是免检的。**

##### 结论与限定

- **万华 25 / 25 逐字段一致，零不一致。** §C.1.4 里「没有人逐字段核对过万华那 25 个取值」这句**至此不再成立**。
- ⚠️ **效力限定与 `SC-2` / `SC-8` 完全相同**（§C.13）：读数路径独立于抽取器，**执行者不独立**。
  本节**不自行改判任何状态栏** —— 25/25 是 legwork，签署由操作者做。
- ⚠️ **这不等于「`SC-2` 在万华上成立」**：`SC-2` 的分母是**茅台**那 29 个（含 `kpi` / `notes` 四支），
  万华这 25 个只是三张合并报表那一路。**两个分母不是同一个集合，不要合并计数。**

### §E 六道登记门禁的变异扫描（`N-41` 判据 3 的返工，2026-08-31 实跑）

> `A guard only guards if the regression actually fails it.`
> 全程 `PYTHONDONTWRITEBYTECODE=1`（`N-41`），每次变异前 `ast.parse` / `yaml.safe_load`
> **自证仍合法** —— 2026-08-24 那次就是被语法错误骗过去的（门禁确实红了，
> 但红的原因是解析失败，不是它声称在查的那件事）。

**做法与 `N-41` 判据 3 的原文不同，先说清楚**：原文要求「复核**既有的**变异结论并重跑」。
实际做的是**对六道登记门禁逐道做一次当下的扫描** —— 那些历史变异针对的代码大多已经改过，
**复原出来的结论对今天的代码没有约束力**。考古能得到「当时那次验证不算数」，
得不到「今天这道门在守」。后者才是要的东西。
⚠️ **历史 prose 记录因此仍记 `UNVERIFIED`**，不写成「已复核」。

| # | 门禁 | 造的回归 | 该红的负控制 | 结果 |
|---|---|---|---|---|
| G1 | `check_xrefs.py` | `if ident not in reg[ns]:` → `if False:` | `test_checker_flags_unknown_id_end_to_end` | **红 → 回退绿** |
| G2 | `check_reading_ledger.py` | 把「记一条问题」那段禁用 | `test_大文件声称全文而正文零出现_必须报红` | **红 → 回退绿** |
| G3a | `verify_deps.py` | 打掉 `affero` 那条模式 | `test_pymupdf_is_rejected_via_classifier` | **红 → 回退绿** |
| G3b | `verify_deps.py` | 打掉 `\\bAGPL` 那条模式 | 同上（登记的那条） | 🔴 **仍绿 —— 见下** |
| G3c | `verify_deps.py` | 同 G3b | 另外两条**未登记**的测试 | **红 → 回退绿** |
| G4 | `semantic_layer scan` | `scan_rules.yaml` 的 `CONTACT_PATTERN` 正则打成永不命中 | `test_contact_pattern_detected` | **红 → 回退绿** |
| G5 | `semantic_layer validate` | `if not defn.grain:` → `if False:` | `test_removing_grain_triggers_r1` | **红 → 回退绿** |
| G6 | `check_gates.py` | `if _failure_points(fn) > 0:` → `if True:` | `test_无断言的测试必须报红` | **红 → 回退绿** |

**六道门，五道干净通过。第三道查出 `N-45`。**

### §E.1 🔴 G3 那一格：先下了个错结论，查清后是另一回事

扫描脚本对 G3b 打的是「**这道门的负控制不设防**」。**那个结论是错的。**

真相：`DENIED_LICENSE_PATTERNS` 有**两条**模式（`\\bAGPL` 与 `affero`），
而登记的负控制用的 classifier 是「GNU **Affero** General Public License v3」——
字符串里有 `Affero`，**没有 `AGPL`**。⇒ 打掉 `\\bAGPL` 对它毫无影响。
**是我的变异打错了地方，不是门禁的缺陷。**

G3c 把靶子换成另外两条测试，立刻红 ⇒ `\\bAGPL` 那条**确实有覆盖**，
只是覆盖它的两条测试**没有登记进 `GATES`**。

⇒ **真正的缺口在「`R2` 证明了什么」这句话上**（台账 `N-45`）：
`R2` 保证的是「这道门**有一条**被证明会红的用例」，
**不是**「这道门每条判据都有负控制」。已写进 `check_gates.py` 的「明确抓不到什么」。

⚠️ **这一格本身也是一条教训**：`rules/commands.md` 一直写着「**红的原因要正确**」，
而这次踩的是它的镜像 —— **绿的原因也要正确**。
「造回归后是绿」有两种解释：**门禁不设防**，或者**变异打错了地方**。
两者的处置完全相反，**必须查清是哪一种再下结论**。

### §E.2 顺带清掉的一处

`check_reading_ledger.py` 里有一个恒真的 `if True:` 包着「记一条问题」那段
（重构剩下的脚手架，包着的代码本来就无条件执行）。留着不会出错，
但它长得像一处「还有判据」，而这份脚本自己的 R3 讲的正是
「构造上不可能红的条件不算条件」。已去掉。

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
