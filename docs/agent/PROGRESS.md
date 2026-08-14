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
