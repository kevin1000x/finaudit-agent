# 01-08 SUMMARY —— Phase 1 收口验证

**模式**：`VERIFY`　｜　**日期**：2026-08-16　｜　**结果**：三个 Task 全部完成，Phase 1 收口

**未修改任何实现、词表或冻结产物**：
`git status --porcelain metrics/_flags.yaml eval/frozen-01/ docs/agent/poc-01/` 输出为空。

---

## Task 1 — 全量门禁实测与三项阶段末判定 ✅

八条门禁全部通过，逐字输出（含退出码）存于 `docs/agent/VERIFICATION.md` §Phase 1 · 附录 A。

| 门禁 | 结果 |
|---|---|
| 指标数量 | `20`，EXIT=0 |
| 全量测试 | `350 passed`，EXIT=0 |
| `validate --json` | `definitions_checked: 20`、`definitions_failing: 0`、`findings: []`，EXIT=0 |
| `scan --json` | `rules_version: 2`、`findings: []`，EXIT=0 |
| `stats --json --fail-over 0.5` | `advisory_ratio: 0.19008264462809918`、`unclassified: 0`，EXIT=0 |
| poc-01 冻结 | 5 行 OK，EXIT=0 |
| frozen-01 冻结 | 21 行 OK，EXIT=0 |
| C2 评测 | `4/4　门成立：True`，作废率 `0.0%`，EXIT=0 |

### 判定一：`advisory_only` 元规则 —— **未失效**

19.0% < 50%。121 条陷阱中 98 条 enforced / 23 条 advisory，未分类 0。
占比最高的两份是 `accounts_payable_turnover_days` 与 `accounts_receivable_turnover_days`
（各 0.2857），原因是实质性的（采购额不单列、增值税与收入不配比），不是写得潦草。

**限定**：这个数说明「大部分陷阱写成了可求值规则」，**不说明规则会正确触发**——
要到 Phase 1.5 接上真实字段才验得了。

### 判定二：H1 停止条件 —— **严格读法计 5，不触发（压线）**

三条迹象逐份核查：
- 迹象一（触发过停止协议）：**1** —— `net_profit_attributable_excl_nonrecurring`（OQ-04）
- 迹象二（承认无法机械消解的口径分支）：**1** —— `free_cash_flow`（无准则定义，组合方式是本层的选择）
- 迹象三（因**语法边界**未能表达已知约束）：**3** —— 三个 `*_turnover_days` 的 365 基数，受限 DSL 不含算术

去重后 **5**，判据「> 5 触发」，**不触发**。

宽松读法（把「因**缺字段**而无法机械执行」也算进来，加 `gross_profit_margin` 计量单位、
`net_working_capital` 单位）计 **7，会触发**。

**操作者 2026-08-16 裁决：严格。** 由此确立一条此后适用的边界：
**「口径写不出来」与「口径写得出但当前数据执行不了」是两件事**，§10 管前者，
后者归数据层走台账（B-3 → Phase 1.5 输出 `unit` / `currency`）。

⚠️ **压线必须随结论传递**：5 是阈值边缘，再多一份即触发；换一种同样合理的读法已经越阈值。
这与 POC-01「4/5 压线 PASS」叠加在同一条假设上——**H1 的全部证据都停在阈值边缘**。

### 判定三：flag 词表 —— **零新增请求**

`docs/agent/phase-01/` 下无任何 `flag-requests-*.md`。19 份定义全程未请求新增 flag，
10 条词表未产生阻塞。评审见 `docs/agent/phase-01/flag-vocabulary-review.md`。

**但「零请求」不等于「零缺口」**：写定义的人发现没有合适 flag 时，
可以选择标 `advisory_only` 而不提请求——那条路更短且完全合规。评审据此找到两处：

1. `minority_interest_share`：`bs.total_equity` 已声明且 `== 0` 已在用，
   `< 0` 同样可求值，而「负权益导致占比符号反转」仍是 advisory。
   符号反转是**方向性错误且数值看起来正常**，与 POC-01 的 C4 同型。
2. `revenue_growth_yoy`：`scope_change` 的词表描述**逐字**就是这条 advisory 所述情形，
   且 `minority_interest_share` 已在用 `notes.business_combination_type`。

这两条是 `rules/failure-modes.md` **F-2 的镜像**（F-2 是「没字段却凑 trigger」，
这里是「有字段却不用」）。**本计划不执行处置**，词表变更走 OpenSpec。

刻意区分了 `roe_weighted_average`：它同样是「权益为负」，但**未声明相应字段**
（fields 只有 `kpi.roe_weighted_average_disclosed` 与 `notes.restatement_flag`），
advisory 标注是对的。不逐份查字段而按「都是权益为负」一并处理，就会造出一条求不出值的假规则。

### Open Questions

`docs/agent/phase-01/open-questions.md` 的 OQ-01…OQ-04 均已裁决/关闭。
现金循环周期的复合指标能力缺口在 OQ-01 有完整记录，并已成为 frozen-01 的 C2 靶子。

---

## Task 2 — `VERIFICATION.md` Phase 1 章节 ✅

14 行验收矩阵（ROADMAP 五条 SC + AC-01/02/04/10 + §7 门五条 + §5.1 元规则 + H1 + D-012 + T-01-41），
三项判定，`UNVERIFIED` 清单五条，附录 A 九段逐字命令输出。

**明确记 `UNVERIFIED` 的**：
1. C1/C3/C4/C5 共 16 题仅冻结未执行（**能力缺口不是配置缺失**，接 API 也跑不通）
2. C3 基于合成夹具，结论只证明计算逻辑、不证明数据抽取
3. 元规则 19.0% 不保证规则会正确触发
4. `01-01 / 01-04 / 01-05 / 01-07` 无 SUMMARY，过程无书面记录可查
5. 对照臂结果不属于本阶段验收，其 C1/C3 分数不得作为本系统能力引用

---

## Task 3 — 人工检查点 ✅（含一处如实记录的缺口）

**第 1 步**：操作者指定复核 `SC-2` / `SC-3 (AC-02)` / `SC-4 (AC-04)` 三条，
执行者原样重跑并逐字比对，**三条全部一致**。允许不同的只有运行时间戳与测试耗时。

**第 2 步（只读 YAML 判断定义是否对人可读）—— 未完成。**
这是对可读性的人的判断，**执行者代答无效**（定义是执行者写的）。
已记为台账 **N-20**，Phase 2 前必须补做。不因未完成而阻塞收口，但也不标记为已通过。

**第 6 步**：操作者裁决「严格」+「按计划继续推进」⇒ **Phase 1 收口，进入 Phase 1.5。**

---

## 状态更新

- `.planning/ROADMAP.md`：Phase 1 条目与 8 份计划全部勾选；依赖图标注「✅ 全部完成」
- `.planning/STATE.md`：`current_phase` 01 → **01.5**，`completed_phases` 0 → 1，
  8/8 计划完成；重写「最危险的未验证假设」，把两处压线并列写出
- `docs/agent/PROGRESS.md`：追加 2026-08-16 changelog（记已发生的事实）

## 本阶段之外、本次会话顺带完成的

不属于 `01-08` 的范围，记在此处以免与阶段验收混淆：

- A-3 裁决落地为 **D-014**（换 pdfplumber，禁 AGPL），并由 `verify_deps.py` 的许可证禁列机器化（A-5 关闭）
- 接入 LLM **对照臂**，跑完 `deepseek-v4-pro` 与 `deepseek-v4-flash` 两个模型臂
- 修 AC-10 扫描的一个真实误报（npm 的 `包名@版本` 被当成邮箱），`rules_version` 1 → 2
- 两个外部项目续读完成，更正了上一轮关于 harness 的两条错误断言
