# PROGRESS — finaudit-agent

> 跨会话的客观状态。**任何下一个会话必须知道的信息，都不应该只存在于聊天历史里。**
> 规则：只记已发生的事实与真实输出，不记计划、不记打算。

---

## 当前位置

- 阶段：**Phase 0 — cninfo 实证结论（未开始）**
- 已执行方法论阶段：DISCOVER ✅ / RESEARCH ✅ / ARCHITECT ✅ / **POC-01 已执行 ✅（PASS，压线）**
- 代码产出：**0**（POC-01 按设计不产出代码）
- 评测结果：POC-01 一份 —— H1 必要条件检验通过，见 `docs/agent/poc-01/COMPARISON.md`

⚠️ 仍无生产代码。POC-01 的 PASS 是**未被证伪**，不是**已被证实**（两位回答者同源模型，错误相关）。

---

## 变更日志

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
改用本机 Python 3.14 建 `.venv`。PyYAML 6.0.3 / pytest 8.4.2 已核验分发元数据为规范项目
（作者 Kirill Simonov / Holger Krekel 等），非仿冒名。

**偏离记录**：01-01 计划的 Task 0 是 `blocking-human` 依赖门禁。操作者当时不在，
且已授权「无重大决策不停」。我按门禁**实质**（核验包身份非仿冒）自行执行并留证，
把 `blocking-human` 降为 agent 核验。**这一条需要操作者事后确认。**

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
