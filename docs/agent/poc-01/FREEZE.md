# POC-01 冻结记录

**冻结时间（UTC）**：`2026-08-09T16:51:58Z`
**冻结方式**：`Get-FileHash -Algorithm SHA256`

冻结时刻**尚无任何回答者看过这些文件**。冻结之后，定义与题目不再修改。
若实验结果为 INCONCLUSIVE 需补写定义，补写后必须重新冻结并记为第 2 次冻结（POC.md 只允许一次）。

## 冻结清单

| SHA-256 | 文件 |
|---|---|
| `27d05e50a61b018ea03adca23cd3946aecc206dea4b7efaf367c67243e690a16` | `definitions/net_profit_attributable_excl_nonrecurring.yaml` |
| `1a969ed799382e4ffabf48b9c0d9273635e25c49550d9c0d89e385db92606996` | `definitions/operating_cash_flow_ratio.yaml` |
| `c5f8c2a92a47255df344dd15f65eecdb847788f74b400a0f0728d82cc37c9073` | `definitions/revenue_growth_yoy.yaml` |
| `912f89655ff2f24719e6103be69d28b5991d4135cb6bfc2b367ff7071a9969b1` | `field_inventory.md` |
| `2d2bf51065e2a20a4ea8c58327d73f728d22513c81ec2a9a673fd52b21fd82eb` | `questions.md` |

机器可读副本：`SHA256SUMS`。声明任何基于本次冻结的结论前先跑：

```bash
cd docs/agent/poc-01 && sha256sum -c SHA256SUMS
```

（已于 2026-08-10 实跑，5/5 `OK`，exit 0。）

## 回答者隔离条件

| 条件 | 落实方式 |
|---|---|
| 两位回答者互不可见 | 两个独立 subagent 会话，并行启动，无共享状态，不交换输出 |
| 回答者看不到判定阈值 | prompt 中不含 `POC.md`、不含 PASS/FAIL 门槛、不含 H1 表述 |
| 回答者看不到实验意图 | prompt 中不出现「实验」「一致性」「歧义」「假设」等提示词 |
| 回答者不接触仓库其余文档 | prompt 内嵌全部输入原文，未授予仓库读取路径 |
| 输入在作答前已冻结 | 见上表哈希；哈希在 spawn 之前计算 |

## 已记录偏离

**EXPECTED**　POC.md 输入项要求「`cninfo` 已有的年报数据字段清单」。
**FOUND**　　 `cninfo-financial-analyzer` 不在本机，已搜 `Documents` / `Desktop` / `D:\` / 项目根，无结果。
**IMPACT**　　字段 id 改为按公开准则报表项目自建（见 `field_inventory.md` 顶部说明）。
POC-01 检验的是口径定义能否消除取数分歧，不是字段名与 cninfo 是否对齐，故不影响判定有效性。
**OPTIONS**　 ①（已采用）用公开准则报表项目替代并记录偏离；②暂停 POC-01，先克隆 cninfo 仓库取真实字段名。
选 ① 的理由：D-008 时间预算；且 POC.md 明确「不真的去取数计算」。

### 事后核对（2026-08-10，克隆 cninfo 之后追加，不修改上方原记录）

`cninfo-financial-analyzer` 已克隆，可以核对当初那句「不影响判定有效性」是否成立。

**对 H1 判定：成立。** POC-01 检验的是「口径定义能否让两个独立读者给出相同取数路径」，
这个性质与字段名叫什么无关。替代清单在结构上（三表 + 附注 + 时点/时段区分）是合理的，
两位回答者在其上产生的一致性结论不受影响。判定 PASS 不需要修正。

**但替代清单与现实差距比当时估计的大，且这对 Phase 1 有实质影响：**
cninfo 现有财务数据层只有 `METRIC_COLUMNS = ["stock_code", "year", "roa", "ocf"]`
——只有 ROA 和 OCF 两个指标，**没有**营业收入、归属于母公司净利润、流动负债合计、
非经常性损益等本次三份口径定义所需的任何字段。

也就是说：**本次 3 份口径定义目前在 cninfo 上一个都取不到数。**
这不推翻 POC-01，但推翻了「Phase 1 可以直接在 cninfo 数据层上做语义层」这个隐含假设。
已记入 `AGENTS.md` §环境 与 `docs/agent/PROGRESS.md`。

**顺带发现（对本项目立论是正面证据）**：cninfo 的 `src/financial_data_sources.py` 里
`ROA_COLUMN_CANDIDATES = ("总资产净利润率(%)", "总资产利润率(%)", "资产报酬率(%)")`，
`_first_column()` 按顺序取第一个命中的列当 `roa`，**且不记录用了哪一个**。
这三个名称的分子口径不一定相同（净利润 / 利润总额 / EBIT 口径）。
无论它们是否恰好相等，「静默选择且不留痕」本身就使结果无法被独立复核——
这正是本项目要消灭的失效模式，出现在自己的上游仓库里，不是假想案例。

## 已知效力限制（判定前记录，不是事后辩解）

两位回答者均为同一基座模型的独立会话。同源模型的错误是相关的，
因此「两份回答一致」对 H1 的支持强度**弱于**两位独立的人类财务从业者。
本次结果应读作 **H1 的必要条件检验**：不一致 → H1 确定有问题；一致 → H1 未被证伪，但未被强证实。
补强方式（不在本次范围）：找一位真人财务背景回答者复跑同一套冻结输入。
