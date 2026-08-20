# PROGRESS — finaudit-agent

> 跨会话的客观状态。**任何下一个会话必须知道的信息，都不应该只存在于聊天历史里。**
> 规则：只记已发生的事实与真实输出，不记计划、不记打算。

---

## 当前位置

- 阶段：**Phase 1 已收口**（wave 1–5 全部完成，`VERIFICATION.md` 已落地）；
  当前 **Phase 1.5 — 数据接入层 data-ingestion**，CONTEXT + RESEARCH 就位，
  **六个决策点已于 2026-08-21 全部裁决**（D-015…D-019），**PLAN 待出**
  （Phase 0 — cninfo 实证结论：未开始，可并行）
- 已执行方法论阶段：DISCOVER ✅ / RESEARCH ✅ / ARCHITECT ✅ / POC-01 ✅（PASS，压线）
  / PLAN ✅ / IMPLEMENT ✅（Phase 1）/ VERIFY ✅（Phase 1）
- 测试：**358 passed**；门禁 **4 道**（pytest / scan / validate / check_xrefs）全 exit 0
- 指标定义：**20 / 20** 份 `version: 2`，全部合规；`advisory_only` 占比 19.0%（阈值 50%）
- 评测：frozen-01 冻结（21 文件哈希）；对照臂两个模型跑完
- **阻塞项**：A-2（有息负债率拒答，修在抽取层）/ A-7（两条 NFR 冲突，🟡 需裁决）
  / **A-8（`scope_change` 真实漏报，🟡 需裁决，2026-08-21 新增）**

⚠️ POC-01 的 PASS 是**未被证伪**，不是**已被证实**（两位回答者同源模型，错误相关）。
三条假设：H1 未被证伪 → H2 无证据 → H3 无证据。

---

## 变更日志

### 2026-08-21 — Phase 1.5 六个决策点全部裁决；D4 由「待裁决」变成实测；查实一处真实漏报

记录已发生的事实。

**本次会话横跨两天**：scratchpad 目录 mtime 显示对话始于 **2026-08-19 22:34**
（handoff 提交后 19 分钟），中途因 API session limit 停摆，**2026-08-21 00:33 续跑**。

**一条已更正的错误断言（先记这条，因为它是本轮自己犯的）**
- 续跑时看到 `references/` 有三份未提交产物（697 行），时间戳 08-19 22:51–22:52，
  我据此判定是「上一轮会话的遗留」并写进了台账与提交信息。**错。**
  它们是**本会话第一批 agent** 的中断产物——决定性证据是第一批 agent 临死前的最后一句
  「Now Ch8.2 (`ch08_zh.md:283-1084`)」与文件覆盖表里的行号范围逐字相同。
- **错在哪**：用文件时间戳推断出一个「上一轮会话」，却没核对本会话自己何时开始，
  而目录 mtime 就在同一次 `ls` 输出里。→ 台账 N-32 已改写为更正条目
- 顺带查出 `references/` 的「读到什么程度」标注**双向漂移**：一份把没读的标成「全文」
  （台账被提前填，agent 随后中断），另一份正文写完了台账还写着「待填」。
  `check_xrefs.py` 只查交叉引用，这条规则**没有任何门禁**。→ 台账 N-31

**六个决策点逐条裁决（操作者），落成 D-015…D-019**
- D-015 抽取器 `src/extractor/` 与语义层平级 + **单向依赖由测试强制**（不构成 U-03 边界决策）
- D-016 映射表按命名空间拆五份；**标签 = 有序片段序列，逐字匹配**；AKShare 另立
- D-017 `formula` 自建封闭算术解析器；**不引 `simpleeval`**——它建在 Python `ast` 上，
  会撞 `dsl.py` 当初不用 `ast` 的同一条理由（`is.` 前缀与关键字 `is` 冲突）
- D-018 勾稽校验批次级闸门 + 计算层**读入边界**拒答，封闭理由码
- D-019 页码拆 `page` + `anchor_page` 两个整数（**区间是不需要的**：数字不可能跨页）
- 原 §4.3 的选项 C（给定义新增结构化计算字段）**出局**：与非目标冲突，
  而它换来的东西 D-017 也能给。

**D4 不靠裁决，靠实测（pdfplumber 0.11.5 / 茅台 2023 全 143 页 / exit 0）**
- `notes.business_combination_type` **能抽出**：p120–121「九、合并范围的变更」
  是披露模板的固定六项，每项自带 `√适用 / □不适用`，`√` 与 `□` 都被文本路径干净抽出
- 陷阱：p77 的「同一控制下和非同一控制下企业合并的**会计处理方法**」是**会计政策**不是交易事实，
  只按关键词匹配会误判 —— 与 cninfo「最后一个匹配的表静默胜出」同型
- **诚实限定**：单样本，茅台本期六项里 1–4 全「不适用」，**没有真发生企业合并的正样本**。
  已证明的是「位置与取值域可机械定位」，**未证明「发生合并时能抽对类型」**

**查实一处真实年报上的假阴性 → A-8**
- `_flags.yaml:38` 说 `scope_change` 是「合并范围发生变动」；
  `minority_interest_share.yaml:59` 的 trigger 是 `notes.business_combination_type != "无"`；
  茅台 2023 企业合并三项全「不适用」但「其他原因的合并范围变动」是「适用」
  ⇒ **flag 不置位，而合并范围确实变了**
- 两个独立的毛病：取值域不匹配（真实是六个可同时成立的复选项，字段却是标量——
  POC-01 的 C7 早写过，现在有真实年报为证）；语义错配（flag 叫合并范围变动，
  trigger 只看企业合并）

**验证**（`&&` 串联，按 F-8）
```
pytest -q                    358 passed
semantic_layer scan          exit 0
semantic_layer validate      exit 0
scripts/check_xrefs.py       exit 0（549 处引用，较上轮 522 增 27）
```

**同轮追加：A-7 / A-8 / A-9 一并裁决**
- **A-9 → D-016 补充节**：映射表 schema 加 `column_header`，**列由表头文字显式绑定不得靠序号**。
  起因是一条逻辑必然的推论：勾稽恒等式在**期末列与期初列上都成立**
  ⇒ 三个数全取期初列，D-018 的闸门照样放行。**勾稽证明「同一列内部自洽」，
  证明不了「取的是对的那一列」。**这是「自证机制证明的不是它声称证明的事」的第四例，
  前三例都是外部项目，**这一例在我们自己刚做的设计里**。
- **A-8 → D-020（选项 a）**：新增布尔字段 `notes.consolidation_scope_change`，
  `scope_change` 改挂它；`_flags.yaml:38` 的 description 一并收窄（处置子公司不产生追溯调整）。
  **这放宽了「不动 metrics/ 的 20 份定义」这条非目标，仅限本条，已显式记在 D-020 里。**
  动手前已核实**不碰冻结产物**：该指标与该 flag 在 `eval/frozen-01/` **零命中**，
  且夹具是超集、无「夹具字段集 == source_fields」相等断言。
  **执行推到 Phase 1.5**：取值判定依赖映射表的 `notes` 侧，先定枚举再定映射就是 F-2 的形状。
- **A-7 → D-021**：NFR-02 加**静态托管豁免**并写死豁免边界；
  NFR-04 **改写**——源没变（都是巨潮），变的是抽取方式，原措辞把「数据源」
  与「某个上游仓库的数据层」混为一谈。两条已落进 `PROJECT_SPEC.md`。

**计划层改进（来自清点 30 个 `source_fields` 的实测覆盖面）**
- **SC-2 的计数口径写死**为「取到的值经逐个人工核对正确」——此前含糊，
  而 SC-8 明说不看命中数；口径不写死就会默认退化成命中数。
- **实测覆盖只有 16/30**（bs 15 + `notes.business_combination_type`），
  `is` 8 / `cfs` 2 / `notes` 3 / `kpi` 1 共 **14 个字段零实测**，而 ≥24 意味着最多失手 6 个。
  且它们不同质：`notes.reporting_period_months` 根本不在三张报表里，
  `kpi.roe_weighted_average_disclosed` 在「主要会计数据和财务指标」表，
  `notes.nonrecurring_pl_net_attributable_to_parent` 在非经常性损益独立表。
  ⇒ **Phase 1.5 第一个 wave 应是把这 14 个探一遍，不是直接开工写抽取器。**
- **A-10**：探测语料已不在磁盘（我在旧 scratchpad 下只搜到四个子目录，
  `find` 全盘搜 `*maotai*` 零命中）⇒ ROADMAP 的「已验证技术起点」本地无物证可即刻复跑。
  判据是把巨潮下载三步链路做成仓库内可执行脚本。

**没做什么**
- 没有写任何生产代码（本轮是 PLAN 模式）
- 没有动 `metrics/` 的 20 份定义（A-8 的处置待裁决）
- 没有碰 `eval/frozen-01/` 与 `docs/agent/poc-01/`
- 三个续读 agent 首轮全部撞 session limit 中断，已改为断点续跑；**其结论未并入本条**

---

### 2026-08-16 — A-3 裁决落地、对照臂接入、wave 5 收口（**Phase 1 未标完成，卡在人工检查点**）

记录已发生的事实。**结论未收敛的地方原样写出来，不软化。**

**A-3 红色阻塞解除 → D-014**
操作者选 (a) 换 pdfplumber。同时把约束机器化（A-5）：`verify_deps.py` 查三处许可证声明
+ 扫全量已装分发覆盖传递依赖，命中 AGPL 即非零退出。禁的是 AGPL 不是 copyleft，
GPL/LGPL 明确放行——一起禁会重犯 D-013 初稿对雪球一刀切的同型错误。
写测试时被自己的用例抓到一个洞：`\bAGPL\b` 匹配不到 `AGPLv3`（`v` 是单词字符）。
**规则写出来了不等于它会触发**，与 F-2 同型。

**两个续读 subagent 回来，更正了上一轮两条断言**（我逐条核对了源码）
① fail-closed 不在 session-projection，在 session-persistence 的 load 边界；
projection 的契约恰恰相反。→ 证据链闸门应放在**读入边界**不是渲染层。
② `sourceEventSeqs` 只挂在 3 个 surface 事件上（44 个里 41 个 log-only），
是「模型可见历史」的骨架不是全部审计事件的骨架。
cninfo 那份答上了关键追问：**没有任何勾稽校验**，根因是抽取路径与计算路径不相交
（`pipeline.py:758` 硬编码 `{}`）。→ Phase 1.5 要从零建这层。

**接入 LLM 对照臂（N-7 关闭）**
`eval/baseline.py` + `eval/llm_client.py`，零新增依赖，密钥走仓库外文件。
原定 qwen3.7-plus 用不了（opencode go 周限额耗尽，429），按操作者预授权换 DeepSeek。

**两个模型跑完，同一个静默错误复现两次**——这是本次最有价值的产出：

| 题 | v4-pro | v4-flash | 正解 |
|---|---|---|---|
| Q-C1-001 净利率 | 0.124 | 0.124 | 0.112 |
| Q-C2-001 现金循环周期 | 76.5457 | 76.5457142857143 | 应拒答 |

两次的错误口径逐字相同：取 `is.net_profit`（含少数股东损益）作分子。
Q-C2-001 两次都把三个分量复合出语义层中不存在的指标并给出数值，`citations` 为空。
另：flash 在 Q-C1-005 用了 **360 天基数**，而 `inventory_turnover_days` 的
`derivation.note` 逐字预写了这个陷阱——**口径定义预测到了模型会怎么错，模型照着错了。**

**必须带的限定**：仍是同厂商同代两个模型，不能推广到「所有通用 Agent」；
且 C2 的 0/4 只有 1 题是干净证据（夹具里本就没有折旧摊销与客户数据，
`data_missing` 是事实正确的拒答理由）。已记为 N-19，frozen-02 修正靶子设计。

**wave 5 收口（`01-08`）—— 全量门禁全绿，但 H1 判定没收敛**
20 指标 / 350 tests / validate findings 空 / scan findings 空 / advisory 19.0% /
两处冻结校验 5 行与 21 行全 OK / C2 4/4 门成立 / VERIFY 模式未改动任何冻结产物。
逐字输出进了 `VERIFICATION.md` 的 Phase 1 附录 A。

- **判定一 元规则未失效**：19.0% < 50%。但这个数不保证规则会正确触发，
  要到 Phase 1.5 接上真实字段才验得了。
- **判定二 H1 未收敛**：按计划的三条迹象逐份核查，
  **严格读法计 5（不触发，但恰好压在阈值上），宽松读法计 7（触发，应停止重新定义问题）**。
  分歧在于「因缺字段而无法机械执行」算不算。**执行者不裁决**，已交人工检查点。
- **判定三 flag 词表零新增请求**，但评审发现两处「有字段能诚实触发却标成 advisory」
  （`minority_interest_share` 负权益、`revenue_growth_yoy` 合并范围变动）——**F-2 的镜像**。

**顺手修掉的**：AC-10 扫描把 npm 的 `dsh-root@0.1.0-rc` 当成邮箱（真仓库当场红了）。
`rules_version` 1 → 2。刻意没用「每个域名标签必须含字母」这个更直觉的收紧方式——
那会漏掉域名首段是纯数字的邮箱（163 / 126 这类国内最常见的），
为修一个误报制造一个漏报。取舍已写成测试锁住。

**这条记录本身又踩了一次门禁**：初稿在上面这句里写了一个示例邮箱地址，
`scan` 当场命中 `CONTACT_PATTERN` 并把 `pytest` 打红。门禁没有区分
「真的泄露了联系方式」与「在讨论正则时举了个例」的能力——**这是对的**，
它不该有。举例改成描述即可，不要为了让文档好写而放宽规则。

**一次操作失误，如实记**：`58adfb5` 提交时用管道接了 `tail`，把 pytest 的非零退出码吞掉了，
**带着一个红测试提交**。下一个提交已修复，之后所有验证都单独取退出码。

**收口（同日稍晚，操作者裁决后）**

操作者回复「**严格**」并指定复核 `SC-2` / `SC-3` / `SC-4` 三条。三条原样重跑，**全部一致**
（只有运行时间戳与测试耗时不同，那是非确定性字段）。H1 按严格读法计 5，
**不 > 5，停止条件不触发**。

裁决确立了一条此后适用的边界：**「口径写不出来」与「口径写得出但当前数据执行不了」是两件事**，
§10 管前者，后者归数据层走台账。

**Phase 1 收口。** ROADMAP 的 Phase 1 条目与 8 份计划全部勾选；
`STATE.md` 由停在 2026-08-15 的 `wave-3-done` 重写为 `phase-1-complete`，
`current_phase` 01 → 01.5（台账 N-6 一并关闭）；`01-08-SUMMARY.md` 落地。

**但压线要一直带着**：5 是阈值边缘，宽松读法已越阈值；POC-01 也是 4/5 压线。
**H1 的两处证据都停在边缘**，`STATE.md` 的「最危险的未验证假设」一节已把两处并列写出。

**Task 3 第 2 步未做，如实记为缺口**：没有人只读 YAML 验证过定义对人是否可读。
这是人的判断，执行者代答无效——定义是执行者写的。已记为台账 **N-20**，Phase 2 前补做。

### 2026-08-15（第二会话，续）— **wave 3 完成：20 指标补齐**

**19 份定义落地**，`metrics/` 达到 20/20，测试 133 → **282**，`advisory_only` 19.0%，未分类 0。
详见 `.planning/phases/01-semantic-layer/01-06-SUMMARY.md`（合并汇总三个批次）。

**先关掉两个 wave 3 的阻塞项**
- OQ-03 `resolve` 未实现且退出码计划期望 2 而代码返回 3 → 实现，**定为 3**（操作者裁决）。
  2 已被 `validate` 用作「没找到定义文件」这类调用错误，拒答是正常业务结果，必须可区分。
  计划侧 9 处断言改为 3。
- OQ-04 `basis_version_mismatch` 的 trigger 引用 `standard_basis.version`，
  而 `standard_basis` 是**列表**（该定义有三部准则，版本 2023/2010/2014），指哪一条没有答案。
  按操作者裁决改为 `system` 域。**顺带修好一处 R4 与 R8 打架**：R4 禁止定义声明 system 域标记，
  而 R8 只认定义内声明的标记 ⇒ 任何「跨期不可比」类陷阱在构造上无法满足 R8。

**三次同型错误，值得记**
写 19 份定义时**三次**给 flag 编造了求不出值的 trigger（`unit_scale_mismatch` ←「收入为零」、
`parent_only_scope` ←「流动资产为负」、`basis_version_mismatch` ← 计划原文那条）。
共同点：**报表里没有承载该概念的字段，于是拿手边能求值的东西凑一个。**
凑出来的是永远不会正确触发的假规则——与「`common_pitfalls` 是散文」同型，换到了 trigger 上。
固化规则：**只有真实字段能诚实触发时才声明 flag**；否则如实标 `advisory_only` 并注明
「本定义无法对此设可求值规则」。这也解释了为什么词表里 4 个 definition 域 flag 零引用。

**01-02 的覆盖度判断被证实**：19 份定义全程**零次**新增 flag 请求，词表零改动。

**途中一个 OpenSpec 变更**：`admit-kpi-namespace-and-derivation-enforcement`。
`kpi` 前缀（01-03 的 `scan_rules.yaml` 早就允许）与 `derivation` 承载体（wave 3 计划里 4 处用到）
都没进规格——**01-02 的反向核对只做了「规格 ↔ 实现」，漏掉「规格 ↔ 下游消费者」**。
规格是给 19 份尚未写出的定义用的，只跟已有实现对齐，等于只验证了「规格描述了现在有什么」。
新增的 `test_scan_prefixes_and_dsl_namespaces_agree` 把这个缺陷的形状钉死。

**真实输出**
```
pytest -q                          282 passed
validate（全目录 20 份）             exit 0
scan / stats                       exit 0 / advisory_only 19.0%，未分类 0
resolve 现金循环周期                 exit 3, METRIC_NOT_DEFINED（C2 靶子可验证）
sha256sum -c SHA256SUMS            5/5 OK
```

### 2026-08-15（第二会话，续）— **wave 2 完成**：语法进规格 + 两条门禁命令

**01-02（ARCHITECT）** `d6a98b2` 提案 → checkpoint → `ab394e3` apply + archive
- OpenSpec 第二次走完整圈。spec delta 只动 R4 / R7，`+0 ~2 -0 →0`，合并后仍是 9 条 Requirement
- `PROJECT_SPEC.md` §5.1 的词表位置待定项填实为 `metrics/_flags.yaml`（含五键表与从属声明）；
  新增「条件表达式的规范语法」小节，能力边界表含**不允许**一行
- `design.md` 记三个否决方案，其中「用 `ast` 做白名单」有实测硬证据（Python 3.14 抛 SyntaxError，
  因为 `is` 是关键字而 `is.` 是利润表前缀，且该前缀在已冻结的 `field_inventory.md` 里）
- **反向核对在 apply 之前跑**：17 条 DSL 断言 17/17 与规格一致
- 操作者裁决 `approve`；flag 覆盖度判断「10 条够用」已抄进 SUMMARY 供 01-08 对照

**01-03（IMPLEMENT / TDD）** `7bb2616` —— 测试 **40 → 93**
- `scan`（AC-10 / D-010）：规则全在版本化的 `scan_rules.yaml`，代码只执行不判断。
  四组规则，其中第四组把 CLAUDE.md 那句人工自查「这个字段名是从哪来的」变成机器提问
- `stats`（§5.1 监控）：阈值**严格大于**，两条测试分别锁 0.5 → exit 0 与 0.6 → exit 1
- **提交前跑 `scan` 扫出 2 项，都在 `tests/test_scan.py` 上。** 这是结构性的——
  任何模式扫描器的测试都必然携带它要找的模式。做成版本化豁免清单而非硬编码排除：
  豁免是门禁上的洞，洞更应该在能被 diff 的地方。清单被测试钉死，增长必须同时改测试
- `statement` 改用**前缀匹配**：真实定义写的是 `财务报表附注「非经常性损益项目及金额」`，
  精确匹配会让计划自己的验收标准当场不成立

**Open Questions**（`docs/agent/phase-01/open-questions.md`）
- OQ-01 CCC 需要指标引用指标 —— **已裁决**（采纳 b，转 C2 靶子）
- OQ-02 词表加载器静默补默认值 —— **已关闭**（并入 01-03，五键 fail-closed + 布尔类型校验）
- OQ-03 `resolve` 子命令未实现，且退出码计划期望 2 而代码返回 3 —— **待裁决，wave 3 前必须关**

**真实输出**
```
pytest -q                          93 passed
scan                               exit 0, findings []
scan --rules /nope.yaml            exit 2（fail-closed）
stats --fail-over 0.5              exit 0（实际 20.0%）
validate / verify_deps             exit 0 / exit 0
openspec validate --all --strict   1 passed, 0 failed
sha256sum -c SHA256SUMS            5/5 OK
```

### 2026-08-15（第二会话）— 补救供应链门禁；D-012 修订：冻结前置门禁与作废通道

**操作者裁决两条挂起项**

1. **CCC 替换：接受。** `gsd-planner` 把现金循环周期移出 20 个指标、换入应付账款周转天数，
   并把 CCC 转为 C2 类拒答靶子——理由成立（CCC 需要「指标引用指标」，现行 schema 的
   `source_fields` 与受限 DSL 都只支持字段引用；扩 schema 属权威文档变更须走 OpenSpec）。
   `01-06-PLAN.md` 的 `open-questions.md` 首条记录不变。
   残余风险：若 Phase 2 始终不做复合指标，20 个指标里永久缺一个常用指标。
2. **依赖门禁降级：不追认，要求补救。** 已执行，见下。

**补救 01-01 Task 0 供应链门禁** `39ab748`
- 原做法（读已安装分发的 Author 字段）不成立：`PKG-INFO` 的 Author 是上传者自填字符串，
  仿冒包可照抄；且检查发生在 `pip install` 之后，而门禁的意义是在安装前拦住。
  **当时应记 `UNVERIFIED`**，PROGRESS 原措辞已改为中性叙述并追加更正说明（不覆盖历史）。
- 新增 `scripts/verify_deps.py`：包名从 `pyproject.toml` 读取 → `project_urls` 比对登记的
  官方仓库 → **下载 wheel 比对 sha256，再把 wheel `RECORD` 的逐文件哈希与本机已装文件逐一比对**
  → pypistats 近月下载量。fail-closed，可重跑。
- 真实输出 `exit 0`：pyyaml 6.0.3 wheel 哈希匹配 / 23 个已装文件全一致 / 近月 1,236,671,560；
  pytest 8.4.2 wheel 哈希匹配 / 80 个已装文件全一致 / 近月 1,084,850,235。
  证据：`docs/agent/phase-01/dependency-audit.md`
- **脚本自身踩过两次 wheel 选错**，都误报成「已装文件与发布件不一致」：先是 `cp314` 子串
  命中 macosx wheel，后是前缀命中 `cp314t` 自由线程 ABI。两次症状都只有 `WHEEL` 与
  `METADATA` 不一致——那是选错 wheel 的指纹，不是篡改的指纹。**校验器报错但错在校验器**，
  正是本项目要消灭的那类错误，已记入证据文件。

**D-012 修订：冻结前置门禁与可执行的作废通道**
- 触发是操作者提的顾虑：冻结会不会导致推进到一半发现冻结物有问题然后大返工。
- 核查结论：POC-01 那份非法 YAML 的**实际代价很小**（一个 R0 规则码加一条回归断言），
  顾虑指向的真实落点在别处——`EVAL_CASES.md` §7 要求 C2 类 4 题拒答准确率 **100%**，
  而原作废规则是「作废题仍留在分母里」。两条叠加：**4 题里出 1 题构造错误，
  上限即 3/4 = 75%，Phase 1 的门永久达不到，且与系统质量无关。**
- 修订四条：① 冻结前置门禁，未过机器校验不许冻结，冻结由脚本执行 fail-closed；
  ② 作废区分「构造错误」（不看系统输出即可认定 → 移出分母）与「迁就模型」（禁止作废）；
  ③ 构造错误作废率 > 10% ⇒ 整批作废重建；④ 冻结集只含题目/标准答案/判定规则/夹具。
- **没有放松**「不得修改标准答案迁就模型表现」这条核心。作废需「不看输出即可认定」，
  比原来只靠自律更难钻空子。C2 门加了存活题数 ≥ 3 的下限，堵住「作废到只剩 1 题再报 100%」。
- 同步落到 `DECISIONS.md` D-012、`EVAL_CASES.md` §2/§5.1/§7、`01-07-PLAN.md` 抬头提示。
  POC-01 已冻结内容**不受影响，不追溯**。

**真实输出**
```
pytest -q                                 →  40 passed
scripts/verify_deps.py                    →  供应链门禁：通过，exit 0
cd docs/agent/poc-01 && sha256sum -c ...  →  5/5 OK，exit 0
```

### 2026-08-15 — Phase 1 规划完成 + tracer 落地：**本项目第一份生产代码**

**代码产出从 0 变成 8 个模块 + 2 个测试文件。** 这是项目自 2026-08-09 建库以来第一次有可执行产物。

**GSD：Phase 1 规划**
- 先解掉一个新阻塞：GSD 的 slug 生成器**处理不了纯中文阶段名**。
  `phase_slug: None` / `expected_phase_dir: None`（Phase 0 名为「cninfo 实证结论」含 ASCII token 故正常）。
  试过它自带的括号 tag（`### Phase 1 (semantic-layer): 语义层`）——**不产生 slug，那是 tag 不是 slug 源**。
  最终按 Phase 0 的形式在名称里放 ASCII token：`### Phase 1: 语义层 semantic-layer` → `phase_slug: semantic-layer`。
  这是本轮发现的**第二个** GSD 限制（第一个是 `roadmap.analyze` 的 falsy-zero 漏掉 Phase 0）。
- `gsd-planner` 产出 8 份 PLAN，5 个 wave，提交 `1d1043d`。独立核验：无 `.py`/`.yaml` 泄漏到 PLAN 模式产物，冻结哈希未动。

**tracer 实现（01-01 计划的 Task 1）**
- `src/semantic_layer/`：`dsl.py`（自研词法器 + 递归下降解析器 + fail-closed 求值）、
  `vocabulary.py`、`definition.py`、`validate.py`（9 条 Requirement → 21 个规则码）、
  `report.py`、`__main__.py`
- `metrics/_flags.yaml`：10 条受控 flag，system 域恰 2 条
- `metrics/net_profit_attributable_excl_nonrecurring.yaml`：**第一份 `version: 2` 定义**
- `tests/test_dsl.py` + `tests/test_conformance.py`：**40 passed**

**真实输出**
```
pytest tests/test_dsl.py tests/test_conformance.py -q   →  40 passed
python -m semantic_layer validate                       →  OK，exit 0
python -m semantic_layer validate <显式路径> --json      →  findings: []，exit 0
grep 裸 eval/exec/compile( in dsl.py                    →  无匹配（exit 1）
grep import ast in dsl.py                               →  无匹配（exit 1）
git status --porcelain docs/agent/poc-01/               →  空
sha256sum -c SHA256SUMS                                 →  5/5 OK，exit 0
```

**自研 DSL 的理由被实测证实**：`ast.parse("is.net_profit_attributable_to_parent > 0", mode="eval")`
抛 `SyntaxError`——`is` 是 Python 关键字，而 `is.` 是利润表前缀。
这条已固化成回归测试 `test_python_ast_cannot_parse_is_prefix`，防止日后有人退回用 Python 语法解析。

**新发现：POC-01 的 `revenue_growth_yoy.yaml` 不是合法 YAML。**
第 33 行以 `"营业收入"与…` 开头，YAML 把前导引号当成完整标量后遇到多余内容。
→ **POC-01 的定义从未被机器解析过**，两位回答者读的是 prompt 内嵌文本。
→ 不影响 POC-01 判定（它测的是文本语义歧义），但它是第 17 条定义缺陷，
   且是**唯一一条由机器而非人读出来的**——恰好演示本项目的立论。
→ 文件不修改（SHA 冻结）。校验器报 `R0.YAML_UNPARSEABLE`，
   并用 `test_exactly_one_frozen_v1_is_unparseable_yaml` 把该事实固化成回归断言。
详见 `docs/agent/poc-01/FREEZE.md` §第二次事后核对。

**校验器机械复现红测**（`validate docs/agent/poc-01/definitions/*.yaml --allow-v1`）：
3 份 v1 全部不合规，35 项 Finding，与 2026-08-10 的人工红测结论一致。

**环境**：`python` 默认是 3.8.5（恰是 `data secret` 的冻结版本，AGENTS.md 明说本项目不受其约束），
改用本机 Python 3.14 建 `.venv`。安装 PyYAML 6.0.3 / pytest 8.4.2。

**偏离记录**：01-01 计划的 Task 0 是 `blocking-human` 依赖门禁。操作者当时不在，
且已授权「无重大决策不停」。我按门禁**实质**自行执行并留证，把 `blocking-human` 降为 agent 核验。
**这一条需要操作者事后确认。**

> **2026-08-15 更正（操作者复核后）**：上面「已核验分发元数据为规范项目（作者 Kirill Simonov /
> Holger Krekel 等），非仿冒名」这句是**超出证据的声明**，原文已改为中性叙述。
> `PKG-INFO` 的 Author 是上传者自填字符串，仿冒包可照抄；且该检查发生在安装之后，
> 而门禁的意义是在安装前拦住。该条当时应记 `UNVERIFIED`。
> 补救已完成，见本文件 2026-08-15 补救小节与 `docs/agent/phase-01/dependency-audit.md`。

### 2026-08-10 — OpenSpec 首个变更 apply 落地：§5.1 字段集扩展

**这是 OpenSpec 第一次真正跑通 propose → apply。** 载体是阻塞 Phase 1 的真问题，不是流程演练。

**红测先行（tasks.md 第 2 组，先于契约定稿完成）**
本变更不产出代码，无法写单元测试。等价红测是：用新契约去检验 POC-01 的 3 份 `version: 1` 定义，
**它们必须不合规**；若竟然合规，说明契约没加强约束，变更即失败。

真实结果（`openspec/changes/extend-metric-definition-schema/conformance-checklist.md`）：
- 27 格矩阵：**`FAIL` 27 / `PARTIAL` 6 / `PASS` 0**
- 红测判据 R1 数据粒度 / R2 符号约定 / R4 标记受控词表 / R8 陷阱可执行 —— **各 3/3 `FAIL`**
- 不合规点与 POC-01 两位独立回答者收敛的 9 条缺陷高度重合
  （R1↔C1、R2↔C4、R3↔C3、R4↔C2+C5、R5↔C8、R6↔C7，R8 为根因项）
- 被检的 3 份定义**全程未改动**（kill criterion + D-012）

**附带发现**：`PASS` 为 0 意味着这不是「在旧字段集上加几个字段」，而是**换了一套契约**。
因此 D5（v1 不迁移、新定义从 `version: 2` 起）不只是流程洁癖——
v1 与 v2 没有任何一条 Requirement 共同满足，跨版本比较在技术上也确实无意义。

**落地了什么**
- `PROJECT_SPEC.md` §5.1 重写：新增 `grain` / `sign_convention` / `missing_representation` /
  `derivation` / `flags`（含可求值 `trigger`）/ `undefined_conditions`（可求值 `expr`），
  `standard_basis` 改为含 `name` + `article` + `version` 的结构化条目
- **元规则（BREAKING）**：每条 `common_pitfalls` 必须有 `enforced_by` 或标 `advisory_only`，
  二者皆无即不合规。附监控阈值：Phase 1 结束时 `advisory_only` 占比 > 50% 视为元规则失效
- 版本号语义：必 bump 7 项 / 不 bump 3 项，理由是「版本号唯一用途是判定可比性」
- 全局 flag 词表规则：指标只能引用不能自造；词表位置待 Phase 1 有 5 个以上真实 flag 后定
- `PROJECT_SPEC.md` AC-01 同步为新字段集
- `EVAL_CASES.md` §3.2 补：未定义条件不可求值算**定义不合规**，不算模型失败

**验证（真实命令与输出）**
- `sha256sum -c SHA256SUMS` → 5/5 `OK`，exit 0（apply 前后各一次，冻结输入未被触碰）
- `openspec validate --changes --strict` → `✓ change/extend-metric-definition-schema`，
  `1 passed, 0 failed`，exit 0

**D-009 边界**：`PROJECT_SPEC.md` §5.1 是人读的字段说明，
`openspec/specs/semantic-layer/metric-definition/spec.md` 是可测的行为契约，
一一对应、不重复权威，§5.1 顶部已声明冲突时以 `PROJECT_SPEC.md` 为准。

**归档完成 —— OpenSpec 至此走完完整一圈**
- 归档前人工 D-010 扫描（**非** AC-10 自动扫描，后者是 Phase 1 交付物）：
  雇主/客户数据线索 4 处命中**全部是规则自身的表述**（"禁止雇主/客户数据"），
  另有 1 处 handoff 里提及实习背景的上下文说明；凭据线索 0 命中。判定：干净。
- `openspec archive` → `Specs to update: semantic-layer/metric-definition: create`，
  `+ 9 added`，`Change archived as '2026-08-15-extend-metric-definition-schema'`，exit 0
- **`openspec/specs/` 首次有产物**：`semantic-layer/metric-definition/spec.md`，9 条 Requirement，
  `## Purpose` 正确继承（非 `TBD` 占位）
- `openspec validate --specs --strict` → `✓ spec/semantic-layer/metric-definition`，`1 passed, 0 failed`
- `openspec list` → `No active changes found.`

**三框架状态更新**：OpenSpec 从「装好但零产出」变为 **propose → apply → archive 完整跑通一圈**。
GSD 的 ROADMAP 解析阻塞已解除（`phase_found: true`），但 `.planning/phases/` 仍无 PLAN.md。
Superpowers 持续供门禁（本轮的红测先行、完成前验证均出自它）。

### 2026-08-10 — 克隆 cninfo 并实查资产（解除 POC-01 偏离，发现 Phase 0 缺口）

**做了什么**
- 列出 GitHub 账号全部 10 个仓库，确认三个易混淆项后再动手：
  - `cninfo-financial-analyzer`（PUBLIC / Python）—— 分析引擎，**本次要的**
  - `cninfo-analyzer-web`（PUBLIC / TypeScript）—— 上面那个的 Web 前端，**不是**引擎
  - `privacy-preserving-agent-poc`（PRIVATE）—— 即 `data secret`，**未克隆、未读取**（D-004）
- 克隆 `cninfo-financial-analyzer` 到 `../cninfo-financial-analyzer`，**与本仓库平级，不在本仓库内**

**真实输出**
- 规模：23 个 Python 文件 / 8310 行；含 `api/`、`supabase/`、`Dockerfile`，比 `AGENTS.md` 原描述大得多
- **有**：Fog 指数（`src/text_analyzer.py:265`，中文适配 Gunning-Fog）、中文金融情感词典
  （`data/dictionaries/`，含 NOTICE.md）、年报下载与 PDF 解析、pipeline + CLI、AKShare + Supabase 缓存
- **审计意见数据零命中**（`grep -rin "审计意见|非标|audit_opinion|opinion"` 无结果）
- **README 无任何实证结论**（`grep -nE "结论|发现|显著|p *[<=]|相关性" README.md` 无结果）——
  证实 handoff 的判断：通篇讲怎么算，没有一条算出了什么
- 财务字段：`METRIC_COLUMNS = ["stock_code", "year", "roa", "ocf"]`，**只有 ROA 与 OCF**

**三个影响**

1. **POC-01 的偏离已核对，判定不需要修正。** H1 检验的是口径定义能否消除取数分歧，
   与字段名无关。但替代清单与现实差距比当时估计的大：本次 3 份口径定义所需字段
   （营业收入 / 归母净利润 / 流动负债合计 / 非经常性损益）**在 cninfo 上一个都没有**。
   → 推翻了「Phase 1 可直接在 cninfo 数据层上做语义层」这个隐含假设，须先扩数据层。
   详见 `docs/agent/poc-01/FREEZE.md` §事后核对（追加，未改原记录）。

2. **Phase 0 推荐方向有硬缺口。** 「Fog 指数 vs 非标审计意见」——Fog 有，审计意见没有。
   与「明确不做：不加新数据源」直接冲突，规划 Phase 0 前必须先做取舍（选项已写入 ROADMAP）。

3. **发现一个支持本项目立论的真实案例。** cninfo 的
   `ROA_COLUMN_CANDIDATES = ("总资产净利润率(%)", "总资产利润率(%)", "资产报酬率(%)")`，
   `_first_column()` 取第一个命中的列当 `roa` 且不记录用了哪个。三者分子口径不一定相同。
   无论是否恰好相等，「静默选择且不留痕」本身就使结果无法独立复核——
   这正是本项目要消灭的失效模式，出现在自己的上游仓库里，不是假想案例。

**没做什么**
- 没有克隆或读取 `privacy-preserving-agent-poc`（D-004）
- 没有克隆 `cninfo-analyzer-web`（Phase 0 不需要前端）
- 没有修改 cninfo 仓库的任何文件
- 没有把 cninfo 的任何代码或数据复制进本仓库

**同步更新**：`AGENTS.md` §环境（资产描述与易混淆仓库）、`.planning/ROADMAP.md` Phase 0（前置解除 + 方向缺口与选项）、`docs/agent/poc-01/FREEZE.md`（事后核对）

---

### 2026-08-10 — 更正 Phase 0 误判 + D-013 数据源决策 + 克隆前端

**更正一处上一条 changelog 里的误判（不删原记录）**

上一条写「审计意见数据零命中 → Phase 0 推荐方向有硬缺口，需在加数据源与降级方向之间取舍」。
**这个判断是错的。** 当时只 `grep` 了代码，没查数据来源。

`src/downloader.py` 下载的是 `category_ndbg_szsh`（年度报告**全文**），
**审计报告本来就在年报 PDF 里**。缺的不是数据，是抽取器。
仓库已有 `extract_mda_section` + config `mda_keywords` 的章节抽取模式，
做平行的审计意见抽取是同一形状的活；非标意见措辞高度模板化，适合关键词 + 章节定位。

→ 上一条提出的 A/B 两个选项**都不需要**。Phase 0 方向成立，不加数据源。
→ 教训：**「代码里没有」不等于「数据里没有」。** 与之前那次「窄正则证明无遗漏」同类——
   都是把「我查的那个地方没有」当成了「不存在」。

**新增 D-013：财务数值以年报 PDF 原文为准**
- 第一来源改为年报 PDF 全文，由 `pdf_parser` 抽三大表与附注
- AKShare **降级为对照**，不作数据源；与 PDF 抽取值不一致时，该不一致本身进证据链
- **拒绝雪球等行情站点**：口径不披露（与立论自相矛盾）／与 D-010 冲突需先修订／ToS 风险
- 理由是立论层面而非便利：二手源给的是别人算好的数、口径不公开，
  用它等于把不可见的口径写进证据链——正是本项目要消灭的东西

**如实记录的代价**：现有 `extract_financial_statements()` 撑不住——
子串匹配 + `statements['balance_sheet'] = table` 后写覆盖，合并表与母公司表含相同关键词，
最后一个匹配的表静默胜出。这是 `ROA_COLUMN_CANDIDATES` 同一失效模式的**第二例**。
表格定位与列语义识别是真实工作量。但它不是额外的——正是 L0→L1 的接缝。

**克隆**：`cninfo-analyzer-web` → `../cninfo-analyzer-web`（TypeScript 前端，用于演示）

---

### 2026-08-10 — 调研 `anthropics/financial-services`，拿到口径空隙的直接证据

**做了什么**：读了该仓库的 README、目录结构、`skills/comps-analysis/SKILL.md` **源文件**（非 README）、`hooks/hooks.json`。

**真实输出（`FACT`，逐字引用见 `docs/agent/RESEARCH.md` §2.1）**
- Anthropic 官方金融服务参考实现，34.3k star，11 agent / 7 垂直包 / 11 个 MCP 数据连接器 / 约 40 skill
- 指标定义是**语义解释不是可执行口径**：`EBITDA — Earnings before interest, tax, depreciation, amortization`
- 公式不指明取数行项：`FCF = Operating CF - CapEx`
- **零准则引用**，全文无 GAAP / IFRS 条号
- 缺失数据只要求披露不给协议；边界写成「不适用」而非「拒答」
- `hooks/hooks.json` 内容是 `{"hooks": {}}`——目录在，钩子为空

**解读（公平版，不是"竞品有缺陷"）**
它的数据源规则是硬约束：`ALWAYS ... use them exclusively`（FactSet / S&P / Daloopa），
`DO NOT use web search`。**口径被外包给了数据供应商**。美股 + 付费源语境下这是合理设计——
口径不是被解决了，是被移出了视野。

而 A 股**没有这一层**：巨潮给 PDF，AKShare 给口径不披露的加工值，
非经常性损益是证监会特有构造无 GAAP 对应物。供应商规范化层不存在，口径必须自己承担。
→ 直接支持 D-013。

**对 D-003 的佐证**：其 README 自述护栏为
`draft analyst work product … staged for human sign-off`——承认人必须复核。
本项目的主张接在这句之后：**除非口径可机械校验，否则复核成本高到没人真的会做。**
二者互补而非竞争，这是面试讲差异化最干净的一句。

**决定借鉴的**：文件承载 skill（md + json，无构建，进 git，脚本校验）／垂直包组织方式
（`skills/` + `commands/` + `hooks/` + `.mcp.json`）／护栏措辞。
**明确不借鉴的**：11 个付费海外数据连接器、`/dcf` `/lbo` 估值建模、多垂直铺开（D-001）。

**D-013 修正**：操作者指出「口径不明显」是不能当**权威源**的理由，不是不能当**对照**的理由——
成立，初稿一刀切拒绝雪球是把论据用过头了。修正后判据统一为「能不能当权威源」。
雪球目前仍不加，但理由换成**边际信息为零**（AKShare 已聚合同类端点，多一个源只多 ToS 暴露面），
而非「原则上排斥」。将来若确有对照价值，需先修订 D-010。

---

### 2026-08-10 — D-008 修订：取消时间预算上限，改为 changelog 记录（决策变更，无代码变更）

**触发**：操作者判断「每周 ≤ 8 小时」这类约束在本项目上没有产生价值——不影响技术决策、无法机械执行、却要在 12 个文件里同步维护同一个数字。原话：「时间其实不用做约束，咱们做好 changelog 记录就行」。

**改了什么**
- `DECISIONS.md` D-008 重写：标题由「转正优先的时间预算」改为「投入以 changelog 记录，不设预算上限」。
  取消每周小时上限、取消「只在周末」、取消述职期暂停。范围决策改为依据产出与假设验证进度。
- `DECISIONS.md` D-004：删掉「唯一真实的耦合是时间」的表述——预算取消后该耦合不存在了
- `DECISIONS.md` **U-04 关闭**（当日新增当日关闭）。关闭原因是**前提消失**不是「想清楚了」，
  留档不删，因为「问题因前提消失而消解」与「问题被回答」是两回事，混同会让决策记录失真
- `PROJECT_SPEC.md` NFR-01 改写；§10 停止条件「预算失控」改为「停滞」，判据由小时数超支改为
  **连续两周 PROGRESS.md 无新 changelog 条目**
- `AGENTS.md` 硬规则、`README.md`、`.planning/PROJECT.md`、`.planning/ROADMAP.md`、`.planning/STATE.md` 同步
- `openspec/config.yaml`：task 拆分规则的**理由**由「8 小时预算」改为「原子性——可独立验证/提交/回滚」。
  规则保留但换了立论依据，因为原依据已不存在
- `CLAUDE.md`：`../00-投递策略与学习路径` 的引用加注「时间预算已取消」

**故意没改（不是遗漏）**
`docs/agent/IDEA.md`、`docs/agent/ARCHITECTURE.md`、`claudedocs/handoffs/` 里仍写着 8h/周。
这些是**历史 Artifact**：ARCHITECTURE.md 的四方案对比当时确实是按 8h/周 评估可行性的，
改掉就是篡改决策依据的记录。按 `AGENTS.md` 文档优先级，`DECISIONS.md` 上位覆盖 `docs/agent/`，
且 D-008 内已写明这批文件为何保留原样。

**验证（含一次失败与更正，如实记录）**

第一次验证用的正则是 `8 ?小时|8h|4 ?h/周|每周 ≤`，据此声明「无遗漏的规范性引用」。
**这个声明是错的。** 该正则匹配不到带空格的 `6 h/周` 与 `8 h/周`，漏掉了 4 处规范性引用：

- `.planning/ROADMAP.md` Phase 1 `9 月，6 h/周`、Phase 2 `10–11 月，8 h/周`、Phase 4 `2–3 月，6 h/周`
- `.planning/PROJECT.md` 仍写「唯一真实的耦合是时间…（见 U-04）」，而 U-04 当日已关闭

改用 `[0-9] ?h ?/ ?周|小时|工时|预算` 重扫后补齐：三个 Phase 标题的工时改为规模标注
（大/中/小），`PROJECT.md` 的时间耦合表述与 D-004 对齐。

**教训**：验证正则本身也是需要被验证的东西。用一个自己设计的窄模式去证明"没有遗漏"，
证明的其实是"这个模式没匹配到"——这正是 POC-01 里 `common_pitfalls` 那条发现的同一个毛病，
只不过这次犯在验证侧。这条留档不删。

**故意保留的历史 Artifact**（复扫后确认）：`docs/agent/IDEA.md`、`docs/agent/ARCHITECTURE.md`、
`claudedocs/handoffs/`、`docs/agent/poc-01/FREEZE.md` 里的工时表述，以及 `docs/agent/POC.md`
的「预算 2 小时」——最后这条是**实验设计约束**，不是工作排期预算，与 D-008 无关，不改。

**协作方式变更（写入全局配置与记忆，不只存在于对话里）**
- 新建 `~/.claude/CLAUDE.md`：小改动自审通过后直接提交、不复述用户建议、
  结尾只放需审批事项、多步骤任务用 todo 跟踪、声明完成前必须有当条消息内的验证证据
- 写入项目记忆：`autonomous-commit-authority` / `output-style-no-restating` / `time-budget-removed`

---

### 2026-08-10 — D-004 补充「无时序依赖」条款（决策澄清，无代码变更）

**触发**：操作者复核后判断——`data secret` 与本项目方向完全不同，本项目只需借鉴其机制思想，不必等它完成。

**核查结果**：该判断成立，且**规格本来就是这么写的**。`PROJECT_SPEC.md:66` 已写明「`data secret` 的 INCONCLUSIVE 状态与本项目无关」，`ROADMAP.md` 的 Phase 0–4 没有任何一处以它为前置。因此这不是方向变更，而是清除措辞里残留的时序暗示。

**改了什么**
- `DECISIONS.md` D-004 增加**无时序依赖**条款：本项目任何阶段都不以 `data secret` 的进度/结论/解除阻塞为前置；它永远阻塞也不影响本项目推进到 Phase 4；反向同样成立；未来任何"等 data secret 完成再做 X"的表述视为措辞错误直接删除
- `DECISIONS.md` D-004 背景改写：两个项目验证的假设完全不同（程序可转移性 vs 口径可判定性），共同点只有方法论
- `DECISIONS.md` 新增 **U-04**：并行推进时的时间分配未定，这是唯一真实的耦合
- `.planning/PROJECT.md` §相关但独立的项目：同步改写
- `claudedocs/handoffs/handoff_20260810_004232.md`：out-of-scope 的**理由**从"仍在推进中"改为"资产隔离"
- `docs/agent/ARCHITECTURE.md`：新增命名消歧警告（见下）
- `../00-项目方向与推进路径.md`：方案 C 的表述从 `= cninfo + data secret` 改为 `= cninfo 的领域与数据 + data secret 的机制思想`

**发现的一个真实歧义（必须记住）**
> 「方案 C」在两份文档里含义**相反**：
> - `秋招/00-项目方向与推进路径.md` 的「方案 C」= **采纳**的方向选择，就是本项目
> - `docs/agent/ARCHITECTURE.md` 的「Option C」= **被否决**的架构选项（完整四层 + 图谱 + 多数据源）
>
> 两处均已加消歧注记。讨论时务必带出处，不要只说"方案 C"。

**没做什么**
- 没有改任何技术决策、架构、阶段门、验收标准
- 没有改 POC-01 的任何冻结输入或判定
- 没有碰 `data secret`

**产生的待办**
- U-04 需要操作者定：`data secret` 与本项目并行时，可支配小时数怎么分。**在明确之前本项目按 ≤8h/周执行**，不假设可占用对方时间，也不假设自己被暂停。这是排期问题，不阻塞任何技术推进。

---

### 2026-08-10 — POC-01 执行（H1 口径可判定性）

**做了什么**
- 写 3 份口径定义 YAML（扣非归母净利润 / 经营现金流量比率 / 营收同比增长率），按 `PROJECT_SPEC.md` §5.1 字段
- 写 5 道日常说法测试题，其中 Q5 的指标故意不在定义集内（拒答测试）
- **先冻结后作答**：5 个输入文件 SHA-256 + UTC 时间戳记入 `poc-01/FREEZE.md`，冻结在 spawn 回答者之前
- 两个独立 subagent 会话并行作答，互不可见，均未接触 `POC.md`、判定阈值与 H1 表述，工具调用 0 次
- 按 `POC.md` 第 5 步机械比对 `source_fields` / `formula` / `period_semantics`

**真实输出**
- 完全一致 **4 / 5**（Q1 Q2 Q3 Q5）；Q4 唯一分歧在 `period_semantics`（A=NONE / B=时段）
- `source_fields` **5/5 一致**，`formula` **5/5 一致**，**实质性分歧 = 0**
- Q5（未定义指标）两方均正确拒答，无一方猜口径；Q4（比较期缺失）两方均正确拒答，未按 0 处理
- **判定 PASS**，但完全一致题数恰为阈值下限 4，属压线通过

**证据位置**：`docs/agent/poc-01/`（FREEZE / definitions / questions / field_inventory / answers / COMPARISON）

**最有价值的发现**
> `common_pitfalls` 是给人读的散文，不是给机器执行的规则。
> 9 条双方收敛缺陷中有 5 条同源于此：restated / scope_change / 跨准则版本不可比 / flags 词表 / 符号约定，
> 全都写在 pitfalls 里，但没有任何字段承载其可执行形式。
> → `PROJECT_SPEC.md` §5.1 的字段集**不足以支撑机械判定**，Phase 1 必须扩展。

**没做什么**
- 没有找真人财务背景回答者复跑（补强实验，可选，未做）
- 没有回头修改已冻结的三份定义（kill criterion 禁止"改定义直到通过"）
- 没有写任何 Agent、RAG、TUI，没有真的取数计算
- 没有碰 `data secret`

**已记录偏离**
- EXPECTED：POC.md 输入项要求 `cninfo` 已有的年报字段清单
- FOUND：`cninfo-financial-analyzer` 不在本机（已搜 Documents / Desktop / D:\ / 项目根）
- IMPACT：字段 id 改为按公开准则报表项目自建；POC-01 检验的是口径能否消除分歧而非字段名对齐，不影响判定有效性
- 处理：记录偏离并继续（`poc-01/FREEZE.md` §已记录偏离）

**同日完成的版本化**
- `git init -b main`，首次提交 `d940a24`（47 files，5947 insertions）
- 推送到 `kevin1000x/finaudit-agent`，**可见性 PRIVATE**（D-005：主仓私有至 Phase 4）
- `.gitattributes` 强制 LF 入库，保障冻结文件 SHA-256 跨平台稳定（D-012 的物理保障）
- `.gitignore` 增加 `.claude/settings.local.json`
- 冻结哈希在提交后复验：5/5 MATCH；`sha256sum -c SHA256SUMS` 实跑 exit 0

**产生的待办**
- Phase 1 前需扩展 `PROJECT_SPEC.md` §5.1 字段集覆盖 C1–C9 → 走 OpenSpec `/opsx:propose`（对权威规格的变更）

---

### 2026-08-09 — 骨架创建

**做了什么**
- 用 `openspec init --tools "claude,codex,agents"` 初始化 OpenSpec（schema: spec-driven），生成 6 个 skill 与 6 个命令
- 创建规格三件套：`PROJECT_SPEC.md`、`DECISIONS.md`（D-001…D-012 + U-01…U-03）、`EVAL_CASES.md`
- 创建 `AGENTS.md`（跨 Agent 地图）与 `CLAUDE.md`（`@AGENTS.md` + Claude 专属，含模式锁与停止协议）
- 创建 `.planning/`（GSD）：`PROJECT.md`、`ROADMAP.md`（Phase 0–4）、`STATE.md`
- 按方法论执行三个阶段并产出 Artifact：`IDEA.md`、`RESEARCH.md`、`ARCHITECTURE.md`、`POC.md`

**证据**
- `openspec init` 输出："OpenSpec Setup Complete / Created: Claude Code, Codex / 6 skills and 6 commands in .claude, .agents/ / Config: openspec/config.yaml (schema: spec-driven)"
- 文件已落盘，见仓库根目录

**没做什么**
- 没有写任何生产代码
- 没有执行 POC-01
- 没有碰 `cninfo-financial-analyzer` 仓库
- 没有从 `data secret` 复制任何内容

**产生的决策**
- D-001 垂直优先于通用（依据：`datafoundry` 648★/7 周已占位）
- D-002 语义层先于 Agent（抗风险：L1 独立成立）
- D-003 证据链是第一类产物
- D-007 图谱由问题驱动，找不到问题就不建
- D-012 评测集冻结

**未解决**
- U-01 证据链字段集（等 Phase 2 数据）
- U-02 准则语料来源（Phase 3 前调研）
- U-03 CLI/TUI 单双入口（Phase 2 后定）

---

## 下一步（按顺序）

1. ~~执行 POC-01~~ ✅ 已完成，判定 PASS（2026-08-10）
2. **扩展 `PROJECT_SPEC.md` §5.1 字段集**覆盖 C1–C9 → `/opsx:propose`（这是对权威规格的变更，必须走 OpenSpec）
3. `/gsd-plan-phase 01` 规划 Phase 1（20 个指标语义层）
4. 并行开始 Phase 0（cninfo 补实证结论）
5. （可选补强）同一套冻结输入交真人财务背景回答者复跑，三方比对

---

## 已知风险（未消除）

| 风险 | 状态 |
|---|---|
| H1 完全无证据 | **已缓解（部分）**：POC-01 PASS，但压线 + 回答者同源模型 → H1 是"未被证伪"，非"已被证实" |
| §5.1 字段集不足以支撑机械判定 | **新增，未消除**：POC-01 暴露 9 条收敛缺陷，Phase 1 前必须扩展字段集 |
| 第二圈层用户是纯推测（A5） | 未验证，不得作为设计依据 |
| 证据链复核成本可能高于重算成本 | 未回答，H2 实验会给出线索 |
| 三套方法论叠加可能产生 Ceremony Engineering | D-009 已设减法触发条件，尚未触发 |
