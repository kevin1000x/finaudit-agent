# RESEARCH — 现状调研

> 模式：`RESEARCH`　｜　状态：**已完成**，2026-08-09
> 规则：只描述现状，不推荐方案。每条结论标注 `FACT` / `INFERENCE` / `ASSUMPTION` / `UNKNOWN`。
> 来源：2026-08-09 多渠道调研（GitHub gh CLI、知乎、B站、YouTube、X、小红书、Web）。

---

## 1. 执行摘要

通用企业 Data Agent 赛道已有成熟且快速增长的开源实现，**"多数据源 + 统一语义 + Trace 可审计"这个位置已被占据**。但公开可见的实现里，语义层普遍是"让用户自己配"，**没有把口径绑定到准则依据**，也没有把"口径未定义时拒答"作为一等行为。这是本项目切口的来源。

## 2. 竞品与先例

| 项目 | Star | 最近推送 | 能力 | 等级 |
|---|---|---|---|---|
| [`datagallery-lab/datafoundry`](https://github.com/datagallery-lab/datafoundry) | 648 | 2026-08-06 | 28 数据源、统一语义层、Trace 可审计可追溯；Apache-2.0；2026-06-18 创建 | `FACT` |
| [`fengyede79/text-to-sql-agent-system`](https://github.com/fengyede79/text-to-sql-agent-system) | 77 | 2026-07-11 | 中文；语义预检、多路元数据召回、LangGraph 编排、SQL 安全校验、有界纠错、Recovery Agent、真实链路评测闭环 | `FACT` |
| [`Snowflake-Labs/ReFoRCE`](https://github.com/Snowflake-Labs/ReFoRCE) | 140 | — | Self-Refinement + Format Restriction + Column Exploration | `FACT` |
| [`db-agent/db-agent`](https://github.com/db-agent/db-agent) | 27 | 2026-08-03 | 生产级 text-to-SQL，带安全护栏，一键部署 | `FACT` |
| [`langchain-ai/text-to-sql-agent`](https://github.com/langchain-ai/text-to-sql-agent) | 29 | 2026-08-05 | LangChain 官方参考实现 | `FACT` |

**`FACT`**：`datafoundry` 用 7 周达到 648 star，说明这个方向有真实需求且竞争激烈。
**`INFERENCE`**：一个校招生的个人项目做通用版无法在功能上竞争，且在面试里回答不了"你和它的区别是什么"。
**`UNKNOWN`**：这些项目的语义层是否绑定了行业准则依据。已读 README，未读源码，不能断言。

## 3. 领域卡点（一线从业者的公开判断）

来源：知乎《别再把 Data Agent 做成 NL2SQL：从一个开源数据智能体工作台，聊聊企业 Agent 平台该怎么落地》，2026

> "企业里真正让人头疼的往往不是'能不能生成 SQL'，而是另一些更细碎、更现实的事情：指标口径是不是对的？表和字段有没有选错？查询会不会越权？结果能不能复盘？模型到底看到了什么上下文？一次分析过程里调用了哪些工具、执行了哪些 SQL、产出了哪些证据？"
> "这些问题不解决，Data Agent 很容易停留在 demo 阶段。看起来像是企业数据分析助手，真正进生产环境时却发现，它既不像 BI 那样稳定可控，也不像数据开发流程那样可审计。"

**等级**：`INFERENCE`（一线从业者的经验判断，非受控研究，但与另一篇 DataFunTalk《落地数据 Agent，如何解决指标口径、实时数据、知识和权限等卡点？》独立一致）

**对本项目的意义**：六个卡点里，"指标口径""能否复盘""证据在哪"三条正是本项目要打的点；"多数据源""越权""实时"三条明确不做。

## 4. 方法论侧的现状

### 4.1 AI 产品的工作流正在"从 evals 开始"

- **来源 1**（`FACT`，有视频出处）：Satya Nadella，Davos 2026 All-In Podcast。LinkedIn 把产品经理、设计师、前端、后端合并为 "full-stack builder"，明确 AI 产品新工作流 `evals → science → infrastructure`，并停掉 Associate Product Manager 项目换成 Associate Product Builder。
- **来源 2**（`FACT`，全字幕已获取）：Ankit Chaklai《AI Evals Masterclass》（Aakash Gupta × HelloPM，2 万观看）。原话：
  > "The way the best AI companies work is that the **AI PM defines these Evals, and that is basically the PRD for the AI engineers**."
  > "If you are not doing offline Evals correctly, then you have not even created a product that can be actually launched to the real audience."

- 该课程给出的**原型上不了生产的 5 个原因**（`INFERENCE`，讲者经验总结）：
  1. **Data drift** —— 开发时的条件与上线后的客户、数据、上下文、知识都变了
  2. **Cost considerations** —— 原型用最贵的模型，上线后成本不线性，管理层砍掉
  3. **Engineering limitations** —— 没做压力测试、扩展性、异步行为
  4. **Missing guardrails** —— 原型数据量小，没想反馈闭环、兜底逻辑、法务红线
  5. **Collaboration failure** —— 不只是团队之间，还有你和用户之间

  讲者对第 2 条的展开值得单独记：**有了 evals 才敢换便宜模型**——因为能证明便宜模型输出质量相当。没有 evals，模型选型只能拍脑袋。

### 4.2 官方教材

- **`FACT`**：DeepLearning.AI × Snowflake《Building and Evaluating Data Agents》。讲师 Anupam Datta、Josha Reini。内容：multi-agent workflow（planner + plan executor + 专用子 agent）、trace 与评估、运行时 inline evaluation。前置只要 Python 基础。
- **`FACT`**：DeepLearning.AI《Evaluating AI Agents》、吴恩达《Agentic AI》。

### 4.3 评测框架先例

| 项目 | Star | 用途 |
|---|---|---|
| [`openai/evals`](https://github.com/openai/evals) | 19.1k | 评测框架 + benchmark 注册表 |
| [`confident-ai/deepeval`](https://github.com/confident-ai/deepeval) | 17.5k | LLM 评测框架，2026-08-09 仍活跃推送 |
| [`benchflow-ai/awesome-evals`](https://github.com/benchflow-ai/awesome-evals) | 805 | 评测资源索引 |
| [`stanford-crfm/helm`](https://github.com/stanford-crfm/helm) | 2.9k | 整体性评测框架 |
| [`modelscope/evalscope`](https://github.com/modelscope/evalscope) | 3.2k | 中文场景友好 |

**等级**：全部 `FACT`（gh CLI 直接读取）。

## 5. 岗位侧的现状（为什么这个项目对求职有用）

- **`FACT`**：携程 AI Agent 产品经理一面原题："解释 Skill、Hook 以及 Multi-Agent 的本质与服务场景"（小红书，2026-06-24）。
- **`FACT`**：美国 AI PM 面试 2026 增速最快的两个题型是 **agentic AI 与 evals**；具体题目包括"为 LLM 功能构建 eval set""RAG 何时优于 fine-tuning""模型 80% 正确率时产品怎么设计"。
- **`FACT`**：滴滴财务 BP 一面二面**都问**"你 AI 用得多吗，用哪家大模型"；面试官对该岗位的能力预期包含"**具有对数据准确性进行校验的意识**"。
- **`INFERENCE`**：财务岗普遍加装 AI 面/AI 测评（OPPO、京东、毕马威、滴滴，四家独立来源），"财务 + 能写 AI 项目"是结构性稀缺。

## 6. 已有资产盘点

**`FACT`**（gh CLI 读取 README）：`kevin1000x/cninfo-financial-analyzer`（public，Python）已实现：
- 巨潮资讯网年报/公告批量异步下载（限速、重试、断点续传）
- PDF 结构化解析（段落、MD&A、财务表格）
- jieba + 自定义金融词典分词
- 中文金融情感词典（姜富伟、孟令超、唐国豪 2020），去重后 8815 词条
- 中文适配 Gunning-Fog 可读性指数
- TNI（Tone-Normalized Innovation）得分
- AKShare 年度财务指标接入 + Supabase 缓存（RLS，权限收敛至 service_role）
- pytest 覆盖核心解析与指标计算

**`FACT`**：README 通篇讲"怎么算"，**没有任何一条"算出来发现了什么"的结论**。

## 7. 关键发现

1. **`FACT`** 通用 Data Agent 赛道已被占位，且增长很快。
2. **`INFERENCE`** 公开实现的语义层是"用户自配"模式，未见绑定行业准则依据的先例。
3. **`INFERENCE`** "口径未定义时拒答"未见有实现把它作为一等行为——大多数系统的默认行为是尽力猜。
4. **`FACT`** evals 正在成为 AI 产品岗的核心能力项，有两个独立高可信来源。
5. **`FACT`** `cninfo` 已经具备完整的数据层，缺的只是结论。

## 8. 我们还不知道的

- **`UNKNOWN`** 一份财务指标口径定义能否做到让两个专业人士看完无分歧。**这是 H1，尚无任何证据。**
- **`UNKNOWN`** 证据链需要哪些字段才够复核。
- **`UNKNOWN`** 会计准则的公开语料从哪来、再分发是否受限。
- **`UNKNOWN`** `datafoundry` 等竞品的语义层内部设计（只读了 README）。
- **`ASSUMPTION`** 第二圈层用户存在——**完全无证据**，不得作为设计依据。

## 9. 对架构的含义

（仅陈述含义，不做选择。选择在 `ARCHITECTURE.md`。）

- 通用方向的竞争已经饱和 → 任何方案都必须回答"和 `datafoundry` 的区别是什么"
- 口径与准则的绑定是**目前未见先例**的空隙，但也可能意味着它没价值
- 数据层已完成 → 增量工作集中在 L1 以上
- evals 是这条线上最被验证的能力项 → 评测协议不应是附属品，应与实现同权重

---

**Gate 判定**：关键架构决策所需的事实是否基本明确？——**通过**，但带一个显著缺口：H1 完全无证据，必须由 POC 补上。
