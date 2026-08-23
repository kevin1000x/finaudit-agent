# hello-agents 第六章「框架开发实践」精读

**语料**
- 书稿：`datawhalechina/hello-agents` @ `45dd84e`，`docs/chapter6/第六章 框架开发实践.md`（**1357 行**）。
  下文简写 `ch6:行号`。
- 章节配套代码：同一仓库 `code/chapter6/`，**16 个文件** = 9 个 `.py` + 4 份 `requirements.txt` +
  **2** 份 README + 1 份 `.env copy`（按扩展名统计：`py` 9 / `txt` 4 / `md` 2 / `env copy` 1）。
  *（本行原写「3 份 README」，2026-08-22 补读时按 `git ls-tree` 实际计数更正为 2。）*
  下文简写 `code/chapter6/<路径>:行号 @45dd84e`。
  取法：`git -C <ha_fw> show 45dd84e:code/chapter6/<路径>`。
- 本轮**起点为 0%**（此前 `references/hello-agents.md` 记录 Ch1-6 未读）。

**读法**：四个框架小节各自「书稿正文 → 配套代码 → 二者对不上的地方」三遍。
本项目关心的是**骨架**，所以对提示词正文（大段 system message）只确认存在与结构，不逐字复述。

## 覆盖表

| 小节 | 行号范围 | 读到什么程度 |
|---|---|---|
| §6.1 从手动实现到框架开发 | `ch6:7-45` | 全文 |
| §6.2 AutoGen | `ch6:46-397` | 全文 + `AutoGenDemo/` 全部 5 个文件 |
| §6.3 AgentScope | `ch6:398-703` | 全文 + `AgentScopeDemo/` 全部 **7** 个文件（`README.md` 为补读，见 §9） |
| §6.4 CAMEL | `ch6:704-942` | 全文 + `CAMEL/` 全部 2 个文件 |
| §6.5 LangGraph | `ch6:943-1287` | 全文 + `Langgraph/` 全部 2 个文件 |
| §6.6 本章小结 | `ch6:1288-1305` | 全文 |
| 习题 | `ch6:1306-1346` | 全文（6 大题 / 17 小问） |
| 参考文献 | `ch6:1347-1357` | 全文（5 条） |

**覆盖度**：书稿 `1357 / 1357` 行全部读过；`code/chapter6/` **16 个文件全部读过**
（9 个 `.py` + 4 份 `requirements.txt` + 2 份 README + 1 份 `.env copy`）。
其中 `AgentScopeDemo/README.md` 是 2026-08-22 补读的最后一个文件，
**独立佐证了 2 条已有结论、新增 2 条**（含一条与代码正相反的「容错机制」宣传语），见 §9。
本文件 §6 的三份全章统计（持久化 / 回调 / `print`）是**逐文件 grep 出来的**，不是抽样。

---

## 1. §6.1 从手动实现到框架开发（`ch6:7-45`）

### 1.1 书对「框架」的定义

> 「一个框架的本质，是提供一套经过验证的"规范"。」（`ch6:11`）

紧接着列出被抽象走的四件事：**主循环、状态管理、工具调用、日志记录**（`ch6:11`）。
注意这份清单里**没有「校验」「拒绝」「证据」**——这不是措辞疏忽，是全章的基调：
本章的框架都把「Agent 系统」切成**执行层面**的块（谁说话、谁调工具、状态存哪），
没有一个框架把**「这个输入该不该被接受」**当成一等抽象。
这条贯穿后面四节，见 §6「四框架的边界守法对照」。

### 1.2 三层解耦（`ch6:18-21`）—— 与 D-015 的关系

书给的模块化建议是三层：

| 层 | 职责（原文） | 出处 |
|---|---|---|
| 模型层 Model Layer | 与 LLM 交互，可替换不同模型 | `ch6:19` |
| 工具层 Tool Layer | 标准化的工具定义、注册和执行接口，「添加新工具不会影响其他代码」 | `ch6:20` |
| 记忆层 Memory Layer | 短期/长期记忆，可切换策略 | `ch6:21` |

**这三层是按「技术设施」切的，不是按「领域职责」切的。**
D-015 要的「抽取器与语义层平级、依赖方向单向」是**领域切分**——
抽取器和语义层都会用到模型层/工具层/记忆层，所以本章这套分层
**既不支持也不反对 D-015，它在另一个维度上**。
真正与 D-015 同维度的是 LangGraph 的 `State` 契约与 AgentScope 的 `Msg` 契约，见 §5、§3。

书对工具层的断言值得钉住：**「添加新工具不会影响其他代码」**（`ch6:20`）。
这是一句**没有代码支撑的宣传语**——本章四个 Demo 里，
只有 LangGraph 的 `Dialogue_System.py` 真的注册了工具（见 §5），另外三个一个工具都没注册，
所以「添加新工具不会影响其他代码」在本章内**不可验证**。

### 1.3 可观测性那一条是空头支票（`ch6:23`）—— 与 D-003 直接冲突

原文：

> 「通过引入事件回调机制（Callbacks），我们可以在智能体生命周期的关键节点（如 `on_llm_start`, `on_tool_end`, `on_agent_finish`）自动触发日志记录或数据上报……这远比在代码中手动添加 `print` 语句要高效和系统化。」（`ch6:23`）

**全章唯一一次出现 callback。** 证据：

```
$ grep -nc -E "Callback|callback|on_llm_start|on_tool_end|on_agent_finish" "第六章 框架开发实践.md"
1
```

命中数 1，就是 `ch6:23` 本身。**四个框架小节没有一个演示回调机制。**
四个 Demo 的可观测性实现全部是 `print` 家族（AutoGen 的 `Console`、AgentScope 的 `print`、
CAMEL 的 `print`、LangGraph 的 `print` + `stream`）。
也就是说，书用「远比 print 高效」批评的东西，正是它自己四个案例全部在用的东西。

**对本项目的意义**：这正是 D-003「证据链是第一类产物，不是日志」要防的那种滑坡。
本章提供了一个反面样本——**把可观测性写进理念、落地成 print**。
证据链如果不是**返回值**（不是回调、不是日志、不是流式输出），它就会退化成 print。
（ARCHITECTURE.md §8 把闸门放进调用签名 `resolve_scope() -> ScopeSpec | Refusal` 而不是事件顺序，
理由与此完全同构：**回调是「链条上的一环」，可绕过、可漂移、可静默失效**。）

### 1.4 四框架的一句话定位（`ch6:37-42`）

| 框架 | 书给的核心比喻 | 出处 |
|---|---|---|
| AutoGen | 「通过对话实现协作」，多智能体系统 = 一个**群聊** | `ch6:39` |
| AgentScope | 「专为多智能体应用设计的开发平台」，卖点是**易用性 + 工程化** | `ch6:40` |
| CAMEL | **角色扮演 Role-Playing**，两个 Agent + 初始提示 Inception Prompting | `ch6:41` |
| LangGraph | 把执行流程建模为**图**，Node + Edge，天然支持 **Cycles** | `ch6:42` |

`ch6:40` 那条（AgentScope）是四条里**唯一一条没有给出机制的**——
「易用性」「工程化」「内置的消息传递机制」「支持分布式部署」都是形容词，
没说清楚它凭什么。§3 会拿代码对这条。

`ch6:31-35` 处有一张对比表（表 6.1），但**是图片**（`docs/images/6-figures/01.png`），不是 Markdown 表格。
即：**书里唯一的四框架横向对比是一张我读不到的图。**
本章正文此后没有再引用表 6.1 的内容，所以这张图不影响其余结论；但凡是需要「书怎么横向比」的地方，我都无法核实。

---

## 2. §6.2 AutoGen（`ch6:46-397`）

配套代码 `code/chapter6/AutoGenDemo/`：`autogen_software_team.py`(193 行)、`output.py`(38 行)、
`requirements.txt`(10 行)、`README.md`、`.env copy`。

### 2.1 AutoGen 把「Agent 系统」切成哪几块（问题 1）

书给的切分（`ch6:60-89`）：

| 抽象 | 职责 | 出处 |
|---|---|---|
| `autogen-core` | 底层：与 LLM 交互、**消息传递** | `ch6:64` |
| `autogen-agentchat` | 上层：对话式智能体的高级接口 | `ch6:65` |
| `AssistantAgent` | **思考**：封装一个 LLM，靠 System Message 分角色 | `ch6:72` |
| `UserProxyAgent` | **行动 + 人类代言**：执行代码/调工具、发起任务 | `ch6:73` |
| `Team` / `RoundRobinGroupChat` | **协调**：谁下一个说话 | `ch6:75-84` |
| `TextMentionTermination` | **终止**：关键词命中即结束 | `ch6:272` |
| `max_turns` | **安全阀**：防无限循环 | `ch6:273` |

书自己点明了这个切分的核心比喻：**「思考」（`AssistantAgent`）与「行动」（`UserProxyAgent`）分离**（`ch6:73`）。
外加一条架构演进的说法：0.7.4「从类继承设计转向了更灵活的组合式架构」（`ch6:48`）。
**这句没有代码支撑**——Demo 里四个 Agent 都是直接 `AssistantAgent(...)` 构造，
既没演示继承版旧写法，也没演示组合式新写法
（`code/chapter6/AutoGenDemo/autogen_software_team.py:47-51,72-76,97-101,105-114 @45dd84e`）。
读者无从对比，只能接受这句转述。

### 2.2 边界靠什么守住（问题 2）：**全靠中文提示词里的口令**

这是本节最重要的一条。AutoGen Demo 的流程推进机制是：

- 顺序由 `participants` **列表顺序**决定（`ch6:271`，代码 `autogen_software_team.py:137-142`）；
- 每个角色的 system message 结尾**用中文写一句口令**，把球传给下一个人：
  - ProductManager：「请简洁明了地回应，并在分析完成后说"请工程师开始实现"。」（`autogen_software_team.py:45`）
  - Engineer：「……并在完成后说"请代码审查员检查"。」（`:70`）
  - CodeReviewer：「……完成后说"代码审查完成，请用户代理测试"。」（`:95`）
  - UserProxy：「完成测试后请回复 TERMINATE。」（`:113`）

**这四句口令是纯粹的约定，没有任何机制强制。** 具体地：

1. **口令与顺序是两个来源、可以互相矛盾。** 发言顺序其实由 `participants` 列表硬编码，
   与提示词里说的「请工程师开始实现」毫无因果关系——就算 PM 说「请审查员先来」，
   下一个发言的仍然是 Engineer。**一个事实两个来源**（见问题 3）。
2. **终止条件是全局子串匹配。** `TextMentionTermination("TERMINATE")`（`:133`）
   对**任何**消息生效。任何一个 Agent 在讨论中提到 "TERMINATE" 这个词，
   整场协作立刻结束。书把它描述为「在我们的设计中，这个指令由 `UserProxy` 在完成最终测试后发出」（`ch6:272`）——
   **「在我们的设计中」就是「靠自觉」的同义词**，代码里没有任何东西限定发出者。
3. **没有任何类型/签名参与边界维护。** 全 Demo 零 `TypedDict`、零 Pydantic 模型、
   零返回值校验。角色的「输出规范」（PM 要输出 5 个小节，见 `:38-43`）只是提示词里的一段中文。

**结论（问题 2 的 AutoGen 答案）：边界 100% 靠约定，0% 靠类型。**
这是 ARCHITECTURE.md §8「不把闸门放事件顺序」那条决策的**教科书级反例**：
AutoGen 把闸门（谁能终止、什么时候进入下一环节）完全放在事件顺序 + 文本约定上，
后果在书自己的运行日志里就能看到，见 §2.4。

### 2.3 状态与消息（问题 3）

- **状态 = 对话历史本身。** 没有独立的状态对象。`ch6:84`：「群聊将新的回复加入对话历史，并激活下一个智能体」。
- **能否重放**：6.2 全节没有任何关于持久化 / 快照 / 重放的内容（全章统计见 §6.3）。
- **「一个事实两个来源」**：有，且很明显。**流程顺序**同时存在于
  ① `participants` 列表（`autogen_software_team.py:137-142`）
  ② 四段 system message 结尾的口令（`:45/:70/:95/:113`）。
  改任一处而不改另一处，系统不会报错，只会行为漂移。

### 2.4 书自己的运行日志推翻了书自己的结论（问题 5 的最强证据）

`ch6:310-352` 是「预期协作效果」的完整终端输出。按书的叙述，这段应该展示
「**完整的开发闭环**」（`ch6:354`）。实际它展示的是：

1. UserProxy 收到「代码审查完成，请用户代理测试」后，回复的是 **「已经完成需求」**（`ch6:334`）——
   **没有执行任何代码，没有验证任何东西**。
2. 然后 PM、Engineer、CodeReviewer 各自又发了一轮**纯客套话**
   （「感谢您的反馈」「很高兴听到项目顺利完成」「再次感谢团队的合作」，`ch6:335-343`）。
   这三轮是 `RoundRobinGroupChat` 轮询机制的直接产物：**轮到你了你就得说话**，
   即使没有任何事情要做。这是轮询协调的固有成本，书没提。
3. 最后一行是 **`Enter your response: TERMINATE`**（`ch6:345`）——
   `Enter your response:` 是 `UserProxyAgent` 向**真人**要输入的提示符。
   **也就是说这场"自动化协作"是靠一个人在终端里手敲 TERMINATE 才停下来的。**

而 `code/chapter6/AutoGenDemo/README.md` 明写案例特点是
「**自动化流程：智能体间自动传递任务，无需人工干预**」。
**书稿正文的日志与配套 README 的宣传语直接矛盾**，矛盾在书自己给的证据里。

### 2.5 交付物的质量：两个角色都没接住（可独立复核）

任务书（`autogen_software_team.py:152`）要求：
「显示24小时价格变化趋势（**涨跌幅和涨跌额**）」——两个量。

团队产出的 `code/chapter6/AutoGenDemo/output.py` 只显示了**涨跌幅**：
`st.metric(label="24小时变化 (%)", value=f"{price_change_percentage:.2f}%")`，
数据源只取了 `data['bitcoin']['usd_24h_change']`。**涨跌额从头到尾没出现。**

这条漏检**同时穿过了 CodeReviewer 和 UserProxy 两道关**，
而 CodeReviewer 的 system message 里写着「5. 评估代码的整体质量」、
UserProxy 的 description 里写着「3. 验证功能是否符合预期」（`:93`、`:110`）。

**这是「多智能体交叉审查 ≈ 质量保证」这一叙事的直接反证，且完全可在仓库内复核。**
对本项目的含义：**审查角色不产生审查能力**。给一个 LLM 贴上 "Reviewer" 的 system message，
不会让它真的对照验收标准逐条打勾。要对照，就得有**机器可判定的验收项**——
这正是 `EVAL_CASES.md` 的判定门存在的理由，也是 D-018「拒绝理由是封闭枚举」的理由：
**枚举可以被程序穷举检查，中文里的「验证功能是否符合预期」不能。**

（另有一处：`output.py` 用 `st.experimental_rerun()`，
而 `requirements.txt:5` 要求 `streamlit>=1.28.0`。该 API 在较新的 Streamlit 中已被 `st.rerun` 取代并移除——
**此版本判断出自我的既有知识，本轮未实跑验证，记 `UNVERIFIED`**。
但「CodeReviewer 放过了一个 `experimental_` 前缀的 API」这一事实本身在仓库内可核。）

### 2.6 依赖声明的两个硬伤（可独立复核）

`code/chapter6/AutoGenDemo/requirements.txt @45dd84e`（10 行，全文）：

```
1  # AutoGen 软件开发团队案例依赖 (v0.7.4)
2  autogen-agentchat
3  autogen-ext[openai,azure]
4  openai>=1.0.0
5  streamlit>=1.28.0
6  requests>=2.31.0
7  pandas>=2.0.0
8  plotly>=5.15.0
9  asyncio
10 dotenv
```

1. **版本只写在注释里。** 正文反复强调「我们将以 `0.7.4` 版本为例」（`ch6:48`）、
   「在 0.7.4 版本中需要……」（`ch6:373`），但 `requirements.txt` 对 autogen **一个版本号都没钉**。
   下一次 `pip install` 装到的是当天的最新版，书里的 API 是否还在，无从保证。
2. **`asyncio` 和 `dotenv` 是错的依赖名。** `asyncio` 是标准库，PyPI 上同名包是一个早已废弃的
   backport；代码里 `from dotenv import load_dotenv`（`autogen_software_team.py:8`）
   需要的包叫 `python-dotenv`，PyPI 上的 `dotenv` 是另一个包。

另：`README.md` 的文件清单里列了 `llm_client.py - HelloAgentsLLM 客户端实现`，
但 `git ls-tree -r 45dd84e code/chapter6/AutoGenDemo/` 只有 5 个条目
（`.env copy` / `README.md` / `autogen_software_team.py` / `output.py` / `requirements.txt`），
**没有 `llm_client.py`。README 描述的是一个不存在的文件。**

### 2.7 书对 AutoGen 的评价：哪些有代码支撑（问题 5）

| 书的说法 | 出处 | 有无代码支撑 |
|---|---|---|
| 「无需设计复杂的状态机或控制流逻辑」 | `ch6:362` | **有**。Demo 确实只有一个 `participants` 列表 |
| 「角色专业化，一个精心设计的智能体可以在不同项目中被复用」 | `ch6:363` | **无**。Demo 只有一个项目；「可复用」是断言 |
| 「`UserProxyAgent` 为人类在环提供天然接口」 | `ch6:364` | **有**，而且比书说的更强——它是**强制**人类在环（`ch6:345` 的 `Enter your response:`） |
| 「基于 LLM 的对话本质上具有不确定性……甚至陷入循环」 | `ch6:368` | **有**，书自己的日志里就是三轮客套话（`ch6:335-343`） |
| 「对话式调试的难题：得到的不是错误堆栈，而是一长串对话历史」 | `ch6:369` | **有**，且这是本节最诚实的一句 |
| 「0.7.4 从类继承设计转向组合式架构」 | `ch6:48` | **无代码支撑**（见 §2.1） |
| 「异步优先……显著提升了并发处理能力」 | `ch6:66` | **无**。Demo 是一条严格串行的轮询链，`await` 从头到尾只有一处（`:167`），**没有任何并发** |

最后一条值得单独说：书用 `async/await` 论证「避免了线程阻塞，显著提升了并发处理能力」（`ch6:66`），
但 `RoundRobinGroupChat` 的语义就是**串行**。整个 Demo 里不存在两个 Agent 同时工作的时刻。
**异步在这里买到的是「不阻塞事件循环」，不是「并发」**——书把二者混为一谈了。

---

## 3. §6.3 AgentScope（`ch6:398-703`）

配套代码 `code/chapter6/AgentScopeDemo/`（**7 个文件**）：
`main_cn.py`(383 行)、`utils_cn.py`(172 行)、`structured_output_cn.py`(137 行)、
`game_roles.py`(113 行)、`prompt_cn.py`(56 行)、`requirements.txt`(17 字节，一行 `agentscope==1.0.2`)、
`README.md`。
*（本节初读时漏了 `README.md`，故原写「6 个文件」；2026-08-22 补读，结论单列在 §9。）*

**这一节是全章对本项目最有价值的一节**，因为它是四个框架里**唯一真的用类型守边界的**，
同时它也**在同一个文件里给出了「守住了」和「没守住」的对照组**——对照组的失败还印在书自己的日志里。

### 3.1 AgentScope 把「Agent 系统」切成哪几块（问题 1）

书给的是四层（`ch6:415-421`，配图 `03.png` 我读不到，只能读文字）：

| 层 | 内含 | 出处 |
|---|---|---|
| 基础组件层 Foundational Components | `Message` / `Memory` / `Model API` / `Tool` | `ch6:415` |
| 智能体基础设施层 Agent-level Infrastructure | 预构建 Agent、ReAct 范式、**智能体钩子**、并行工具调用、状态管理 | `ch6:417` |
| 多智能体协作层 Multi-Agent Cooperation | **`MsgHub`**（消息路由 + 状态管理）、**`Pipeline`**（顺序/并发编排） | `ch6:419` |
| 开发与部署层 Deployment & Development | `AgentScope Runtime`、`AgentScope Studio` | `ch6:421` |

这是四个框架里**唯一一个把「消息」提升为一等抽象**的切法：
交互不是函数调用，是 `Msg` 的收发（`ch6:425`）。核心数据结构 `Msg` 有四个字段
`name / content / role / metadata`（`ch6:427-441`）。

**注意 `ch6:417` 提到「智能体钩子」**——这是全章第二次、也是最后一次触碰回调机制，
同样**没有任何代码演示**。加上 `ch6:23`，全章两次提到钩子/回调，两次都是名词。

### 3.2 边界靠什么守住（问题 2）：**一半靠类型，一半靠约定，而且两半在同一个文件里**

`structured_output_cn.py` 里有七个结构化输出模型。**它们的强度分成截然不同的两档**：

**A 档——闸门在类型里（`Literal` 封闭枚举，且由存活名单动态生成）：**

```python
def get_vote_model_cn(agents: list[AgentBase]) -> type[BaseModel]:
    class VoteModelCN(BaseModel):
        vote: Literal[tuple(_.name for _ in agents)] = Field(...)
```
（`code/chapter6/AgentScopeDemo/structured_output_cn.py:24-41 @45dd84e`；
`get_seer_model_cn` `:65-82`、`get_hunter_model_cn` `:85-103` 同构）

这三个是**工厂函数**：每次调用都拿**当前存活名单**重新造一个类型出来。
调用点 `main_cn.py:291`（`structured_model=get_vote_model_cn(self.alive_players)`）、
`:171`（预言家）、`:238`（猎人）。
**投票给一个已死的人、投票给一个不存在的名字，都会在 Pydantic 校验处失败，不可能静默通过。**

这正是 **ARCHITECTURE.md §8 想要的形状**：合法范围被编码进**类型**，
而类型由**调用时的真实数据**生成——闸门在签名里，不在流程的某一环。
也正是 **D-018「拒绝理由是封闭枚举」** 的同构物：`Literal[...]` 就是一个封闭枚举，
枚举之外的一切**没有表示形式**，因此不需要靠谁记得去检查。

**B 档——闸门只在描述文字里（裸 `str`）：**

```python
class WerewolfKillModelCN(BaseModel):
    target: str = Field(description="要击杀的玩家姓名")
```
（`structured_output_cn.py:106-118`）

同样是「选一个玩家」，狼人击杀用的是**裸 `str`**。
没有 `Literal`、没有工厂、没有校验。**「玩家姓名」这四个字只写在 `description` 里给 LLM 看。**

**后果就在书自己的运行日志里。** `ch6:635-636` 明确写着孙权与周瑜**都是狼人**：
> 游戏主持人: 📢 【孙权】你在这场三国狼人杀中扮演狼人……
> 游戏主持人: 📢 【周瑜】你在这场三国狼人杀中扮演狼人……

而 `ch6:649` 是狼人私聊频道里的第一句话：
> 孙权: 今晚我们应该除掉周瑜，此人智谋过人，对我们威胁很大。

**狼人在密谈频道里提议杀自己的队友，而队友就在频道里。**
（周瑜随后在 `ch6:650` 用第三人称谈论自己：「但周瑜虽智，却未必是今晚的最大威胁」。）

这不是 LLM 不够聪明的问题，是**类型没有把它挡住**：
`target: str` 允许任何字符串，包括队友名、死人名、乱码。
如果 `WerewolfKillModelCN` 也用 `Literal[tuple(非狼人存活者)]`，这句话根本无法被序列化出来。

**最讽刺的是：这个约束在同一个仓库里是存在的，只是放错了地方。**
`main_cn.py:156` 的**兜底随机路径**明确排除了队友：

```python
valid_targets = [p.name for p in self.alive_players if p.name not in [w.name for w in self.werewolves]]
votes[self.werewolves[i].name] = random.choice(valid_targets) if valid_targets else None
```

**错误路径比正常路径严格。** 正常路径（LLM 返回合法 JSON）不检查队友，
错误路径（LLM 返回垃圾）反而排除队友。

**问题 2 的 AgentScope 答案**：类型确实在守边界，**但守得不均匀，而且不均匀之处没有任何机制能发现**。
对本项目：D-015 说「依赖方向单向且**由测试强制**」——
AgentScope 演示的正是「没有强制」的下场：**同一份代码里两种强度并存，谁也不会报错。**

### 3.3 书对「规则自动化约束」的断言是假的（问题 5 的最强证据）

`ch6:563` 原文：

> 「更重要的是实现了**游戏规则的自动化约束**。例如，**女巫智能体无法同时对同一目标使用解药和毒药**，预言家每晚只能查验一名玩家，这些约束都通过**数据模型的字段定义和验证逻辑自动执行**。」

**代码里不存在这条约束。** 三条证据：

1. `WitchActionModelCN`（`structured_output_cn.py:44-62`）是两个**互相独立**的 `bool`：
   `use_antidote: bool = False`、`use_poison: bool = False`，外加**一个共用的** `target_name`。
   两个都置 `True` 完全合法。
2. **全 `code/chapter6/` 目录零个 Pydantic 校验器**：
   ```
   $ git grep -c -E "validator|model_validator|field_validator|root_validator" 45dd84e -- code/chapter6/
   （无输出 = 零命中）
   ```
   书说的「验证逻辑」不存在。
3. 消费端 `main_cn.py:212-222` 是**两个平行的 `if`，不是 `if/elif`**：
   ```python
   if witch_action.metadata.get("use_antidote") and self.witch_has_antidote:
       ...  saved_player = killed_player
   if witch_action.metadata.get("use_poison") and self.witch_has_poison:
       poisoned_player = witch_action.metadata.get("target_name")
   ```
   于是 `use_antidote=True, use_poison=True, target_name=<今晚被杀的人>` 这组输入，
   会走成「救活他」+「毒死他」，同一回合同一目标，**恰恰是书说「无法」发生的那件事**。

真正被强制的只有「解药/毒药各一瓶」，而它靠的是 `self.witch_has_antidote` /
`self.witch_has_poison` 两个**可变实例标志**（`main_cn.py:52-53`）——
**是命令式代码里的状态，不是「数据模型的字段定义」。**

**这条对本项目的价值**：这是「**声称约束在类型里、实际约束在流程里**」的标准样本。
D-017 拒绝三方求值库、自建封闭算术解析器，理由同构：**能力边界要么写死在语法里，要么就是没写。**
「我们在调用点检查了」和「这个值不可能被构造出来」是两种强度，本项目要后者。

### 3.4 提示词与类型打架：一个事实三个来源（问题 3）

`prompt_cn.py:10-20` —— **每一个角色**的系统提示词开头都硬编码了同一段 JSON schema：

```
请严格按照以下JSON格式回复，不要添加任何其他文字：
{
    "reach_agreement": true/false,
    "confidence_level": 1-10的数字,
    "key_evidence": "你的证据或观点"
}
```

这是 `DiscussionModelCN` 的字段。但它被发给了**所有五种角色**（狼人/预言家/女巫/猎人/村民，
`prompt_cn.py:22-56` 五个分支都拼在同一个 `base_prompt` 后面）。
而实际运行时：

| 角色 | 提示词告诉它要输出 | 代码实际要求的 `structured_model` |
|---|---|---|
| 女巫 | `reach_agreement/confidence_level/key_evidence` | `WitchActionModelCN`（`main_cn.py:203`） |
| 预言家 | 同上 | `get_seer_model_cn(...)`（`:171`） |
| 猎人 | 同上 | `get_hunter_model_cn(...)`（`:239`） |
| 全员投票 | 同上 | `get_vote_model_cn(...)`（`:291`） |

**同一个「输出格式」这个事实有三个来源**：① 提示词里的硬编码 JSON、② Pydantic 模型、
③ 书稿 `ch6:569-589` 印的第三版提示词（写的是「重要规则：1. 你只能通过对话和推理参与游戏
2. 不要尝试调用任何外部工具或函数 3. 严格按照要求的JSON格式回复」，`ch6:574-577`）——
**书稿印的这一版和仓库里的 `prompt_cn.py` 不是同一段文字。**

三个来源里只有 ② 是被机器执行的。①③ 是给人和 LLM 看的，且已经和 ② 对不上了。
**这正是「一个事实两个来源」的教科书案例，而且它已经腐烂了。**

### 3.5 fail-open：无效输出时**编一个值出来**（与 D-018 正面冲突）

`main_cn.py` 对结构化输出失败有四处处理，**强度各不相同**：

| 位置 | 无效时的行为 | 性质 |
|---|---|---|
| 狼人击杀 `:153-157` | **随机挑一个目标** | **fail-open + 伪造** |
| 预言家 `:162-188`（`:171` 取模型）| 跳过本阶段 | fail-safe |
| 女巫 `:190-227`（`:203` 取模型）| 视为不使用技能 | fail-safe |
| 白天投票 `:296-304` | 视为弃票（写入 `None`） | fail-open |
| 猎人 `:229-256`（`:239` 取模型）| 视为放弃开枪 | fail-safe |

第一条是硬伤：LLM 没给出可用结果时，程序**自己替它做了一个决定**，
然后这个决定在后续日志里与真实决定**无法区分**。
书把这类处理统称为「容错处理」「确保游戏继续进行」（`ch6:607`、`ch6:617`）。

**这是 D-018「fail-closed 在读入边界」的正对立面。**
在狼人杀里代价是一局游戏；在财务审计里，「抽取器没读到这个字段，于是随机/默认填了一个值」
**就是伪造证据**。而且因为 `Msg.metadata` 里存的是最终值、不是「这个值怎么来的」，
下游**无法区分模型给的和程序编的**——这直接违反 D-003：
**证据链必须能区分「模型说的」与「系统补的」，否则它就不是证据链。**

第四条（弃票写 `None`）还带一个真实缺陷：`utils_cn.py:40-48` 的 `majority_vote_cn`
用 `Counter(votes.values()).most_common(1)[0]` 统计，**`None` 与真实姓名同处一个值域**，
弃票足够多时 `None` 会「当选」，`voted_out` 变成 `None`。
根因是**「弃票」没有被建模为一个与「投给某人」不同的类型**——
又一次「值域没有封闭」（D-018）。

### 3.6 状态与消息（问题 3）：能不能重放

- **状态存在哪**：`ThreeKingdomsWerewolfGame` 的实例属性上（`main_cn.py:40-53`）。
- **一个事实几个来源**：**四个**。`self.alive_players`（存活名单）、
  `self.werewolves/villagers/seer/witch/hunter`（五个阵营子列表）、`self.roles`（name→role）、
  `self.players`（name→agent）。
  `update_alive_players`（`main_cn.py:258-269`）必须**手工从六个列表里逐一剔除**同一个死者。
  漏掉任何一个 = 幽灵玩家。这是典型的「派生数据被物化成独立字段」。
- **能否重放**：**不能**。
  ```
  $ for f in main_cn.py utils_cn.py game_roles.py prompt_cn.py structured_output_cn.py; do
      git show 45dd84e:code/chapter6/AgentScopeDemo/$f | grep -c -iE "sqlite|mongo|persist|save|dump|序列化"; done
    3 0 0 0 0
  ```
  `main_cn.py` 的 3 处命中全部是局部变量名 `saved_player`，**不是持久化**。
  全 Demo **零持久化、零快照、零 seed 固定**（`random.sample` 分角色、`random.choice` 兜底都不设种子）。

  而书在 `ch6:479` 写：
  > 「**消息持久化**: 能够将所有消息自动保存到数据库（如 SQLite, MongoDB），确保了长期运行任务的状态可以被恢复。」

  **`MsgHub` 的持久化在本章零演示、零验证。** 同理 `ch6:480` 的「原生分布式支持……通过 RPC
  自动处理跨节点通信」也是零演示。这两条是转述宣传语。

### 3.7 书稿与代码对不上的其余四处（问题 5）

| # | 书稿 | 仓库代码 | 性质 |
|---|---|---|---|
| 1 | 「每个玩家都是一个基于 **`DialogAgent`** 的实例」（`ch6:496`） | `ReActAgent`（`main_cn.py:11,60`） | 类名就是错的 |
| 2 | `from agentscope.agents import AgentBase`（`ch6:455`） | `from agentscope.agent import AgentBase`（`structured_output_cn.py:5`、`utils_cn.py:8`），**单数** | 书上的 import 在 `agentscope==1.0.2` 下跑不通 |
| 3 | 「我们在关键环节加入了容错处理」+ 一段 `try/except` 包住 `await wolf(...)` 的代码（`ch6:607-623`） | `main_cn.py` **全文只有一处 `try/except`**（`:313`/`:362`），是 `run_game` 最外层的兜底。书上那段 try 不存在 | 示例代码是编的 |
| 4 | `DiscussionModelCN` 三个字段**都有 `default`**（`ch6:539-561`） | `reach_agreement` 与 `confidence_level` **无 default**（`structured_output_cn.py:11-17`） | 抄写不一致 |

第 3 条值得展开：书演示的「容错」写法是
`except Exception: default_response = DiscussionModelCN(reach_agreement=False, confidence_level=5, key_evidence="暂时无法分析")`——
**用一个编造的默认值冒充模型输出**。这段代码虽然没进仓库，但它是书**推荐的做法**，
而且与仓库里真实存在的狼人随机兜底（§3.5）同一个思路。
**书在两个地方独立地推荐了「失败就编一个」。** 对本项目这是明确的躲避对象。

### 3.8 AgentScope 值得抄的一条 / 最该躲的一条

- **最值得抄**：`get_vote_model_cn(agents) -> type[BaseModel]`
  这个**「用运行时真实数据生成类型，把合法范围编码进 `Literal`」**的模式。
  它让「投给不存在的人」这件事**没有表示形式**，而不是「会被发现」。
- **最该躲**：**同一类语义用两种强度实现**（`Literal` vs 裸 `str`），
  以及**失败时编造值**（狼人随机兜底 / 书推荐的 default_response）。
  前者的危害是「以为守住了」，后者的危害是「伪造的与真实的无法区分」。

### 3.9 书对 AgentScope 的评价：有代码支撑 vs 转述宣传语（问题 5 汇总）

| 书的说法 | 出处 | 判定 |
|---|---|---|
| 消息驱动、`MsgHub` 建临时私密频道 | `ch6:499-531` | **有**（`main_cn.py:125-144`、`:276-293` 两处真实使用） |
| `fanout_pipeline` 并行收集决策 | `ch6:595-607` | **有**（`main_cn.py:139-144`、`:288-293`）。四框架里唯一真正的并发 |
| 结构化输出「确保格式一致性」 | `ch6:563` | **有** |
| 结构化输出「实现游戏规则的自动化约束」 | `ch6:563` | **假**，见 §3.3 |
| 「消息持久化到 SQLite/MongoDB」 | `ch6:479` | **零演示**（转述宣传语） |
| 「原生分布式支持，RPC 自动跨节点」 | `ch6:480` | **零演示**（转述宣传语） |
| 「内置了分布式部署、容错恢复、可观测性等企业级特性」 | `ch6:400` | **零演示**。可观测性落地=`print` |
| 「AgentScope Runtime / Studio」 | `ch6:421` | **零演示**，全章不再出现 |
| 「以消息驱动**代替**状态机」 | `ch6:499` | **半假**。`run_game`（`main_cn.py:311-365`）就是一个手写的顺序状态机：夜→查验→女巫→判胜→白天→猎人→判胜。`MsgHub` 只换掉了「谁能听见谁」，没换掉阶段推进 |
| 局限性：「过度工程化的风险」「生态与社区待完善」 | `ch6:700` | 诚实，但与 `ch6:400` 的「内置企业级特性」自相矛盾 |

最后一条（`ch6:499` 的「代替状态机」）对本项目有直接意义：
**AgentScope 并没有消灭状态机，它只是把状态机藏进了业务代码。**
书把「消息路由的灵活性」说成了「不需要显式流程」，这是两件事。
本项目的 pipeline 需要显式阶段（读入 → 校验 → 解析 → 计算 → 出证据），
**不要被「消息驱动就不用写流程了」这句话骗走**——AgentScope 自己也没做到。

---

## 4. §6.4 CAMEL（`ch6:704-942`）

配套代码 `code/chapter6/CAMEL/`（**2 个文件**）：
`DigitalBookWriting.py`(63 行)、`requirements.txt`(一行 `camel-ai==0.2.75`)。
**四个 Demo 里最小的一个**，63 行里有 20 行是 import 与配置。

### 4.1 CAMEL 把「Agent 系统」切成哪几块（问题 1）

**几乎没切。** 全部抽象只有三个（`ch6:710-730`、代码 `:36-51`）：

| 抽象 | 职责 | 出处 |
|---|---|---|
| `RolePlaying`（"社会"） | 一次性接收 `assistant_role_name` / `user_role_name` / `task_prompt`，**在内部把三者拼成两段 Inception Prompt** | `ch6:804-810`；`DigitalBookWriting.py:36-41` |
| `init_chat()` | 生成开场白（**由 AI 生成，不是人写的**） | `ch6:825`；`:47` |
| `step(input_msg) -> (assistant_response, user_response)` | 驱动一整轮：AI User 提需求 + AI Assistant 给方案 | `ch6:830`；`:51` |

角色是 **AI User（需求方/推动者）** 与 **AI Assistant（执行者/方案方）**（`ch6:712`）。
书特别提醒这两个名字与直觉相反：负责规划结构的「作家」被分配给 `user_role_name`，
负责内容的「心理学家」被分配给 `assistant_role_name`（`ch6:815`）。

**没有状态对象、没有工具注册、没有消息类型、没有终止条件对象。**
唯一的循环控制是调用方自己写的 `while n < chat_turn_limit`（`:49`）。

### 4.2 边界靠什么守住（问题 2）：**100% 提示词，且书自己承认**

书对「行为约束」的定义（`ch6:730`）是全章最坦白的一句：

> 「**设定行为约束和沟通协议**：这是最关键的一环。例如，指令会要求 AI 用户"一次只提出一个清晰、具体的步骤"，并要求 AI 助理"在完成上一步之前不要追问更多细节"，同时规定双方需在回复的末尾使用特定标志（如 `<SOLUTION>`）来标识任务的完成。」

**「最关键的一环」是一段自然语言指令。** 没有任何类型、签名、校验参与。
这是本项目在 D-015 / D-017 / D-018 / ARCHITECTURE §8 四处**同时**要避开的形态：
约束存在于「模型被要求怎么做」，而不是「系统允许什么被表示」。

而且这一环在本章内部就已经失效了两次：

1. **标志名对不上。** `ch6:730` 说标志是 `<SOLUTION>`；`ch6:840`/`ch6:850` 用的是
   `<CAMEL_TASK_DONE>`。同一节里两个「任务完成标志」。
2. **匹配方式是裸子串。** 仓库代码 `DigitalBookWriting.py:57`：
   ```python
   if "CAMEL_TASK_DONE" in user_response.msg.content:
   ```
   **连尖括号都没有。** 只要正文里出现这 15 个字符（包括「我还没有输出 CAMEL_TASK_DONE」
   这种否定句、或复述协议本身），协作立即终止。
   这是 AutoGen `TextMentionTermination`（§2.2）的同一个病，且更松。

### 4.3 书稿代码与仓库代码是两份不同的代码（问题 5）

`ch6:800-848` 印的代码与 `DigitalBookWriting.py @45dd84e` **有三处实质差异**，
每一处都让书稿版本看起来比真实版本更稳健：

| # | 书稿（`ch6`） | 仓库（`DigitalBookWriting.py`） | 后果 |
|---|---|---|---|
| 1 | `with_task_specify=False,  # 在本例中，我们直接使用给定的task_prompt`（`ch6:809`） | **该参数完全不存在**（`:36-41`） | 见下方「自证」 |
| 2 | `if assistant_response.msg is None or user_response.msg is None: break`（`ch6:833`），正文称之为「检查是否有消息返回，防止对话提前终止」 | **没有这个判空**，直接 `.msg.content`（`:53-54`） | 仓库版本在 `msg is None` 时 `AttributeError` 崩溃 |
| 3 | `if "<CAMEL_TASK_DONE>" in user_response... or "<CAMEL_TASK_DONE>" in assistant_response...`（`ch6:840`） | `if "CAMEL_TASK_DONE" in user_response.msg.content:`（`:57`）——**无尖括号、且只检查 user 一侧** | 助理宣告完成会被漏掉；同时误报面更大 |

**第 1 条可以用书自己的输出自证。** `ch6:812` 打印的是 `role_play_session.task_prompt`。
如果 `with_task_specify=False` 真的生效，这一行应该原样回显输入的 `task_prompt`。
但 `ch6:880-881` 的实际输出是**一段被改写压缩过的文字**：

> 具体任务描述:
> 为普通大众撰写8000–10000字短篇电子书《拖延症心理学》：实证为本、通俗易懂。结构：引言、成因（认知/情绪/奖励）、动机与决策、习惯形成与干预、实用策略与练习、三则案例分析、总结与资源。每章含研究引用与可操作步骤。

对比输入（`ch6:782-789`）的五条分行要求——**内容被 LLM 重写了**，
说明 task-specify 环节**实际是开着的**。
即：**书稿正文印的那份代码，不是产生书稿那段日志的代码。**
（此判断只用了书稿内部的两处输出对比，**不依赖我对 CAMEL 默认参数的记忆**。）

### 4.4 四阶段协作叙事没有任何证据（问题 5 的第二强证据）

`ch6:856-868` 用四段文字详细描述了协作的阶段划分，**还给了精确的轮次区间**：

- 第一阶段（**约 1-5 轮**）：框架搭建与目标对齐
- 第二阶段（**约 6-20 轮**）：核心内容生成与知识转译
- 第三阶段（**约 21-25 轮**）：迭代优化与质量保证
- 第四阶段（收尾）：总结与升华

紧接着 `ch6:870-898` 给出「执行上述代码后」的实际输出。**那段日志只有两轮**：
作家 Instruction → 心理学家 Solution + "Next request." → 作家 Instruction → `.....`。

**日志在第 2 轮就截断了，四阶段叙事里的第 6 轮之后全部没有证据。**
「心理学家再次扮演事实核查员」「作家把'现在偏见'比作只顾眼前糖果的任性孩子」（`ch6:862`）
这些具体细节，在日志里一个字都找不到。

**这是本章最典型的「转述宣传语」**：不是引用别人的宣传语，是**书自己编的运行叙事**。
判定方法很简单——**凡是给了轮次区间却没有对应日志的段落，都是叙事不是观测。**

对本项目的直接意义：`EVAL_CASES.md` 的失败归因分层如果只写「第 X 阶段表现良好」，
而没有可复现的 trace，那和 `ch6:856-868` 是同一类文本。
**判定门必须钉在可复现的输出上，不是钉在阶段描述上。**

### 4.5 状态与消息（问题 3）

- **状态**：全部藏在 `RolePlaying` 内部，调用方看不见也拿不到。
  对外唯一暴露的是 `role_play_session.task_prompt`（`:43`）和 `step()` 的两个返回值。
- **消息**：`response.msg.content` —— **一个字符串**。没有 schema，没有 metadata，
  没有结构化输出。CAMEL Demo 里全章零 Pydantic。
- **能否重放**：不能。无持久化、无 seed、无轮次快照。
  `input_msg = assistant_response.msg`（`:61`）之外，历史完全由 `RolePlaying` 内部持有。
- **一个事实两个来源**：有。**「任务完成」这个事实**同时存在于
  ① Inception Prompt 里对标志的约定（框架内部生成，调用方看不到全文）
  ② 调用方自己写的 `if "CAMEL_TASK_DONE" in ...`（`:57`）。
  ①改了②不会知道，②写错了①也不会报错。**书稿版与仓库版在②上就已经不一致了**（§4.3 第 3 条）。

### 4.6 扩展点与冲突处理（问题 4）：书把它留成了习题

CAMEL 节是全章唯一**正面承认**冲突问题的地方（`ch6:931`）：

> 「**冲突解决**：当多个智能体意见分歧时，缺乏有效的仲裁机制」

而且习题 `ch6:1329` 把它明确摊开：

> 「在案例中，协作会在检测到 `<CAMEL_TASK_DONE>` 标志时强制终止。但如果两个智能体意见分歧（一位认为可以终止，一位认为不应该终止），无法达成一致怎么办？请设计一个"冲突解决"的兼容机制。」

**书知道这是个洞，选择把它留给读者。** 全章没有给出任何仲裁机制的实现。

注意这个洞的形状：**"能否终止" 是一个被两方各自持有的布尔判断，没有单一权威。**
本项目 ARCHITECTURE.md §8 的 `resolve_scope() -> ScopeSpec | Refusal` 恰好是它的解药——
**判定权只有一个持有者，返回值只有两种形态，没有"两个 Agent 各自认为"的余地。**

### 4.7 书对 CAMEL 的评价：有代码支撑 vs 转述宣传语（问题 5 汇总）

| 书的说法 | 出处 | 判定 |
|---|---|---|
| 「轻架构、重提示」的设计哲学 | `ch6:906` | **有**。63 行代码是全章最短，属实 |
| `RolePlaying` 封装复杂提示工程，只需传两个角色名 + 任务 | `ch6:815` | **有**（`:36-41`） |
| 「自然涌现的协作行为，往往比硬编码的工作流更加灵活和高效」 | `ch6:906` | **无**。「往往」「更高效」没有任何对照实验；本章没有任何两框架同任务的对比 |
| 四阶段协作流程（含轮次区间） | `ch6:856-868` | **无证据**，见 §4.4 |
| CAMEL 已具备多模态 / 工具集成 / 模型适配 / 生态联动 | `ch6:910-913` | **纯转述**。原文自己写「从其 GitHub 仓库可以看到」——这是**抄 README 的功能清单**，本章零演示、零验证 |
| 局限性：提示设计门槛、调试复杂性、一致性挑战 | `ch6:921-923` | **诚实且与代码一致**（唯一的控制手段确实是提示词） |
| 局限性：缺乏对话路由 / 分布式状态 / **冲突解决** | `ch6:929-931` | **诚实**，见 §4.6 |
| 「严格流程控制场景 LangGraph 的图结构更合适」 | `ch6:937` | **有**（与 §5 一致），但仍是断言，无对照 |

### 4.8 CAMEL 值得抄的一条 / 最该躲的一条

- **最值得抄**：`step(input_msg) -> (assistant_response, user_response)` 这个**一次调用推进一整轮、
  并把双方产出一起返回**的签名。它让「一轮」成为一个有边界的、可被外部计数与截断的单位
  （`while n < chat_turn_limit`），而不是一个内部黑箱循环。
  本项目的批次级闸门（D-018「闸门放批次级」）需要的正是这种**外部可数的推进单位**。
- **最该躲**：**把协作协议全部写进 Inception Prompt，再用裸子串匹配读回来。**
  协议的定义端（框架内部生成的提示词）和执行端（调用方的 `if ... in ...`）
  是两个互不知情的地方——书稿版和仓库版在这一点上已经分叉了，这就是证据。

---

## 5. §6.5 LangGraph（`ch6:943-1287`）

配套代码 `code/chapter6/Langgraph/`（2 个文件）：
`Dialogue_System.py`(258 行)、`requirements.txt`(4 行，`langgraph==1.0.0a3` / `langchain_openai==0.3.33` /
`python-dotenv` / `tavily-python`)。

**这是四个 Demo 里唯一真的调了外部工具的**（Tavily 搜索 API），
也是唯一有 checkpoint 概念的。同时它也是**书稿吹得最响、案例落得最空的一节**。

### 5.1 LangGraph 把「Agent 系统」切成哪几块（问题 1）

三个抽象，加一个编译产物（`ch6:945-1041`）：

| 抽象 | 职责 | 出处 |
|---|---|---|
| **State**（`TypedDict`） | 全局共享状态；所有节点读写同一个对象 | `ch6:951-962` |
| **Node** | 一个 Python 函数：吃状态 → 吐状态更新 | `ch6:963-987` |
| **Edge** / **Conditional Edge** | 常规边固定跳转；**条件边**用一个函数按状态动态路由 | `ch6:989-1032` |
| `StateGraph(...).compile()` → `app` | 编译成可执行体；`app.stream()` / `astream()` 逐节点吐事件 | `ch6:1005-1041` |
| `checkpointer=`（`InMemorySaver`） | **快照/续跑**：按 `thread_id` 保存每步状态 | `ch6:1203,1220-1221`；`Dialogue_System.py:14,191-192,224` |

书自己把它定性为**状态机 + 有向图**（`ch6:947`），与 AutoGen/CAMEL 的「对话」范式对立。
这是四个框架里**唯一把「状态」而不是「消息」放在中心**的切法。

### 5.2 边界靠什么守住（问题 2）：**契约在类型里，但没有任何东西执行这个类型**

LangGraph 是四框架里**最接近本项目要求**的一个，理由有两条，代价也有两条。

**理由一：`Annotated[list, add_messages]` —— 合并策略写进字段类型**（`Dialogue_System.py:24`）

```python
class SearchState(TypedDict):
    messages: Annotated[list, add_messages]
    ...
```

`add_messages` 是一个 **reducer**：当某个节点返回 `{"messages": [...]}` 时，
框架不会覆盖旧值，而是按字段上声明的策略去**归并**。
**「这个字段怎么被更新」不再是调用方的自觉，而是字段类型的一部分。**

这是全章唯一一处「行为被编码进类型」的机制，也是本项目**最该抄的一条**：
证据链是**累加**的（每一步追加一条证据，不是覆盖），
把「累加」写进 `Evidence` 字段的类型，而不是指望每个写入方都记得 append，
正是 D-015「依赖方向由测试强制」的同一个思路——**别靠自觉**。

**理由二：State 是显式 schema，节点契约是「吃状态、吐状态」**，
比 AutoGen 的裸对话历史、CAMEL 的裸字符串强一个数量级。

**代价一：`TypedDict` 在运行时什么都不做，而仓库里的注解是错的。**

`Dialogue_System.py` 三个节点的签名都写成 `-> SearchState`（`:42`、`:80`、`:132`），
但它们**实际返回的是部分字段的 dict**：

```python
return {
    "user_query": response.content,
    "search_query": search_query,
    "step": "understood",
    "messages": [AIMessage(...)]
}          # ← 6 个字段的 SearchState 里只给了 4 个
```
（`:73-78`）

`SearchState` 是默认 `total=True` 的 `TypedDict`，缺字段就不是合法的 `SearchState`。
**这三个注解是错的**，而且**没有任何东西会发现**：
```
$ git ls-tree -r --name-only 45dd84e code/chapter6/ | grep -icE "test|mypy|pyproject|setup.cfg|conftest"
0
```
`code/chapter6/` 下 **零测试、零 mypy 配置、零 pyproject**。

有意思的是**书稿正文这里是对的**：`ch6:1073` 明说「返回一个包含更新后字段的字典」，
`ch6:1106` 的签名写的是 `def understand_query_node(state: SearchState) -> dict:`。
**书对，仓库错。** 这是本章唯一一处书稿比代码更严谨的地方。

**这一条对 D-015 是直接教训**：D-015 说「依赖方向单向且**由测试强制**」——
LangGraph 演示的是「有类型但不强制」会怎样：**注解变成注释，撒谎也没人知道。**
类型不跑 checker 就等于文档。

**代价二：§6.5.1 教的节点契约和 §6.5.2 教的是两套。**

- `ch6:967-986`：`def planner_node(state: AgentState) -> AgentState:`，函数体是
  `state["messages"].append(plan)` 然后 `return state` —— **就地改共享状态，返回整个状态**。
- `ch6:1073`：「返回一个包含更新后字段的字典」—— **返回增量，不改原状态**。

**同一小节里两种契约，书没有说明哪个是对的、什么时候用哪个。**
就地修改在有 reducer 的字段上会产生双写（append 一次 + reducer 归并一次）。

还有一处更该躲：`ch6:992-1000` 的路由函数**带副作用**：

```python
def should_continue(state: AgentState) -> str:
    if len(state["messages"]) < 3:
        return "continue_to_planner"
    else:
        state["final_answer"] = state["messages"][-1]   # ← 路由函数在写状态
        return "end_workflow"
```

**判定和副作用绑在一起了。** 这与 ARCHITECTURE.md §8 的
`resolve_scope() -> ScopeSpec | Refusal` 正好相反：那条决策要的是
**判定只返回判定，不顺手改世界**。书把这个反模式当范例印了出来，且未加任何提示。

### 5.3 状态与消息（问题 3）：全章唯一能重放的，但案例把它关掉了

- **状态存在哪**：`SearchState`，一个显式 schema（`:23-29`）。**六个字段，来源单一**。
  这是四框架里状态管理最干净的一个——没有 AgentScope 那种「同一个事实四份拷贝」。
- **能否重放**：**框架能，案例不能。**
  `workflow.compile(checkpointer=InMemorySaver())`（`:191-192`）给了按 `thread_id` 的逐步快照，
  这是全章**唯一**的重放机制（AutoGen/AgentScope/CAMEL 三家全零，见 §2.3 / §3.6 / §4.5）。

  但案例把它废掉了。`main()` 里：
  ```python
  session_count += 1
  config = {"configurable": {"thread_id": f"search-session-{session_count}"}}
  ```
  （`:223-224`）
  **每问一个问题就换一个新的 `thread_id`**，加上每轮都重建 `initial_state`（`:227-234`），
  于是 checkpointer 保存的历史**永远不会被读回来**。

  而 `ch6:1270` 写：
  > 「并且他是一个可以持续交互的助手，你也可以继续向他发问。」

  **「持续交互」只是「循环 `input()`」，不是「记得上一轮」。**
  第二个问题看不到第一个问题的任何上下文。`Annotated[list, add_messages]` 这个
  精心设计的归并器，在 Demo 里**每轮只归并一次就被丢弃**。

  另外 `InMemorySaver` 是进程内存，退出即失。
  书在 `ch6:1278` 说 LangGraph「对于构建需要高可靠性和**可审计性**的生产级应用至关重要」——
  **本章没有演示任何跨进程可留存的审计物。**

### 5.4 书吹得最响的一条，案例里根本没有（问题 5 的最强证据）

`ch6:1278` 原文：

> 「其最强大的特性在于对**循环（Cycles）的原生支持**。通过条件边，我们可以轻松构建"反思-修正"循环，**例如在我们的案例中，如果搜索失败，可以设计一个回退到备用方案的路径**。」

**案例里没有条件边，也没有循环。**

```
$ git show 45dd84e:code/chapter6/Langgraph/Dialogue_System.py | grep -c "add_conditional_edges"
0
```

`create_search_assistant()`（`:176-194`）是四条 `add_edge` 的**严格直线**：
`START → understand → search → answer → END`。

书说的「搜索失败就回退」在代码里是 `generate_answer_node` 里的**一个 `if`**（`:136`），
**在节点内部**，图上看不见。也就是说：
LangGraph 最值得看的两个特性（条件边、循环）在唯一的实战案例里**零使用**，
`add_conditional_edges` 只出现在 `ch6:1022` 的教学片段里。

注意书的措辞是「**例如在我们的案例中**」——不是「可以这样扩展」。这句是错的。

### 5.5 降级把自己的痕迹擦掉了（与 D-003 / D-018 正面冲突）

这是本节对本项目最重要的一条。看 `generate_answer_node` 的两个分支
（`Dialogue_System.py:132-173`）：

| 分支 | `search_results` | `step` 最终值 | `final_answer` 来源 |
|---|---|---|---|
| 搜索成功 | 真实搜索结果 | `"completed"` | 基于搜索结果 |
| 搜索失败 | `"搜索失败：{error_msg}"`（`:127`） | **`"completed"`**（`:148`） | **LLM 自身知识**（`:138-144`） |

**两条路径的终态字段完全相同。**
`step` 这个字段本来可以把降级编码进去（比如 `"completed_without_search"`），
但两条路径都写了 `"completed"`。于是：

**下游拿到 `final_answer` 时，无法判断这个答案有没有外部依据。**

书对此的处理是在 fallback prompt 里加一句中文：
「请提供一个有用的回答，并**说明这是基于已有知识的回答**」（`:142`）——
**又一次把机器可判定的事情交给模型自觉。** 模型说不说、说得对不对，没有任何东西检查。

而书的运行日志（`ch6:1232-1268`）走的是成功路径，
最终回答里报出了「明天（2025年9月17日）北京……17°C 到 25°C」这样的具体数字。
如果那次是降级路径，**同样的输出格式会给出同样自信的数字，而读者分辨不出来**。

**对 finaudit-agent 的直接对应**：
- 「抽取器没读到某张表 → 用模型知识补一个数」，与这里是同一个动作。
- D-003 要求证据链是第一类产物：**「这个数从哪来」必须是返回值的一部分，
  不是提示词里请求模型自述的一句话。**
- D-018 要求 fail-closed 在读入边界、拒绝理由是封闭枚举：
  这里的 `step: str` 是**开放字符串**，`search_results` 里既可能是结果也可能是错误消息（`:127`）——
  **同一个字段承载两种语义，值域没有封闭。** 换成
  `SearchOutcome = Ok(results) | Failed(reason: RefusalCode)` 这类封闭和类型，
  「把失败当成结果用下去」在语法上就不可能。

### 5.6 扩展点与冲突处理（问题 4）

LangGraph 是四框架里**唯一有真正注册表**的：`workflow.add_node("understand", fn)`（`:180-182`）
用**字符串名**注册，`add_edge("understand", "search")`（`:186`）用同样的字符串引用。

- **重名会怎样？书没有说，代码也没有演示。**
  ```
  $ grep -nc -E "重名|命名冲突|重复注册|覆盖已" "第六章 框架开发实践.md"
  0
  ```
  **全章零命中。** 四个框架的注册/重名/冲突语义**一个字都没写**。
  这是本章一个整体性的空白：**它教你怎么注册，不教你注册撞车了会怎样。**
- 更弱的一点：节点名是**裸字符串**，`add_edge` 引用一个不存在的节点名不会在写代码时被发现
  （编译期会报，但那是运行时的编译期）。**图的拓扑不受静态类型保护。**
- 书唯一触及冲突的是 CAMEL 节的「缺乏仲裁机制」（`ch6:931`）与习题 `ch6:1329`，见 §4.6。

### 5.7 书对 LangGraph 的评价：有代码支撑 vs 转述宣传语（问题 5 汇总）

| 书的说法 | 出处 | 判定 |
|---|---|---|
| 流程被显式定义为状态+节点+边，**可控可预测** | `ch6:1278` | **有**（`:176-194` 确实是显式四条边） |
| 「对循环（Cycles）的原生支持……**例如在我们的案例中**」 | `ch6:1278` | **假**。案例零条件边、零循环，见 §5.4 |
| 「对于需要高可靠性和**可审计性**的生产级应用至关重要」 | `ch6:1278` | **无演示**。唯一的持久化是 `InMemorySaver`，退出即失 |
| 「每个节点是独立 Python 函数，带来高度模块化」 | `ch6:1280` | **有** |
| 「插入一个等待人类审核的节点非常直接」 | `ch6:1280` | **无演示**。全章零 human-in-the-loop 节点（AutoGen 的 `UserProxyAgent` 是另一回事） |
| 「他是一个可以持续交互的助手」 | `ch6:1270` | **假**。每轮换 `thread_id`（`:223-224`），无跨轮记忆，见 §5.3 |
| 局限：Boilerplate 多，要思考「如何控制流程」而非「做什么」 | `ch6:1284` | **诚实**，与代码一致 |
| 局限：调试要盯三处——节点内部逻辑、**节点间传递的状态数据异变**、边跳转条件失误 | `ch6:1286` | **诚实，而且是全章最有价值的一句**。「状态异变」正是 §5.2 代价二（就地修改 + 路由函数副作用）的后果，书自己在优势里教了这两个写法，又在局限里点了它们的名 |

### 5.8 LangGraph 值得抄的一条 / 最该躲的一条

- **最值得抄**：**`Annotated[field_type, reducer]`——把「这个字段怎么被合并」写进字段类型。**
  证据链的累加、拒绝理由的收集、多批次结果的合并，全部适用。
  写进类型 = 新增写入方不需要知道规则，也不可能写错。
- **最该躲**：**降级路径与正常路径写同一个终态**（`step="completed"` 两处都写），
  以及**用注解假装有类型契约但不跑 checker**。
  前者销毁证据链，后者制造「我们有类型」的错觉——**比没有类型更危险**，
  因为它会让人省掉运行时校验。

---

## 6. 四框架的边界守法对照

本节不引入新材料，只把 §2–§5 已经落过的证据横过来排一次。
建它是因为 §1.1（`ch6:35`）与 §2.3（`ch6:158`）都向前引用了它，此前是悬空的。

### 6.1 边界靠什么守（问题 2 的横向答案）

| 框架 | 边界机制 | 类型参与度 | 本章内的失效证据 |
|---|---|---|---|
| AutoGen | ① `participants` 列表顺序 ② 四段 system message 结尾的中文口令 ③ `TextMentionTermination` 全局子串 | **0%**（零 TypedDict / 零 Pydantic） | `ch6:345` 的 `Enter your response: TERMINATE` —— 「自动化协作」靠真人手敲停下 |
| AgentScope | `Literal[tuple(存活名单)]` 工厂函数（投票 / 预言家 / 猎人 **3 处**）+ 裸 `str`（狼人击杀 **1 处**） | **不均匀**：同一类语义两种强度 | `ch6:649` 狼人在密谈频道提议杀队友（`target: str` 允许） |
| CAMEL | Inception Prompt 里的自然语言协议 + 调用方 `if "CAMEL_TASK_DONE" in ...` 裸子串 | **0%**（零 Pydantic） | 同一节里两个标志名：`<SOLUTION>`（`ch6:730`）vs `<CAMEL_TASK_DONE>`（`ch6:840`） |
| LangGraph | `TypedDict` 显式 schema + `Annotated[list, add_messages]` reducer | **有类型，无执行者** | 三个节点的 `-> SearchState` 注解全是错的（`Dialogue_System.py:42,80,132`），`code/chapter6/` 零 mypy 零测试 |

**排完之后的结论比单看任何一节都清楚**：本章四个框架，
**没有一个把「这个输入该不该被接受」放进类型**。
最接近的两个各差一步——AgentScope 有正确形状但只覆盖了 3/4 的调用点；
LangGraph 有正确形状但没有任何东西执行它。

### 6.2 「一个事实几个来源」横向汇总（问题 3）

| 框架 | 被复制的那个事实 | 来源数 | 出处 |
|---|---|---|---|
| AutoGen | **发言顺序 / 流程推进** | 2 | `participants` 列表（`autogen_software_team.py:137-142`）＋ 四段口令（`:45/:70/:95/:113`） |
| AgentScope | **输出格式** | 3 | `prompt_cn.py:10-20` 硬编码 JSON ＋ Pydantic 模型 ＋ 书稿 `ch6:569-589` 印的第三版（三份已互不一致） |
| AgentScope | **谁还活着** | 4 | `alive_players` / 五个阵营子列表 / `roles` / `players`（`main_cn.py:40-53`），`update_alive_players` 手工逐一剔除（`:258-269`） |
| CAMEL | **「任务完成」** | 2 | 框架内部生成的 Inception Prompt ＋ 调用方 `:57` 的子串判断（书稿版与仓库版已分叉） |
| LangGraph | **节点拓扑** | 1（裸字符串） | `add_node("understand", fn)` / `add_edge("understand", "search")`——单一来源但**不受静态类型保护** |

**LangGraph 是唯一一个「事实只有一个来源」的**，代价是那个来源是 magic string。
AgentScope 是最严重的一个：两处各 3、4 个来源，且**都已经腐烂**（不是"将来会漂"，是现在就对不上）。

### 6.3 持久化 / 快照 / 重放：全章统计（`ch6:158` 引用的那份统计）

`code/chapter6/` 下全部 **9 个 `.py` 文件**逐个 grep 持久化关键词：

```
$ for f in $(git ls-tree -r --name-only 45dd84e code/chapter6/ | grep '\.py$'); do \
    echo "$(basename $f): $(git show 45dd84e:$f | grep -cE 'sqlite|mongo|persist|checkpoint|Saver|pickle|json\.dump|\.save\(')"; done
  game_roles.py: 0        main_cn.py: 0          prompt_cn.py: 0
  structured_output_cn.py: 0                     utils_cn.py: 0
  autogen_software_team.py: 0                    output.py: 0
  DigitalBookWriting.py: 0
  Dialogue_System.py: 3     ← 唯一命中，全部是 InMemorySaver / checkpointer
```

**8/9 个文件零命中，唯一的 3 处命中是进程内存快照，退出即失，且被 §5.3 记的
「每轮换一个新 `thread_id`」废掉。**

与之对照，书在三处承诺了持久化能力：
`ch6:479`（AgentScope「自动保存到 SQLite / MongoDB」）、
`ch6:1203/1220-1221`（LangGraph checkpointer）、`ch6:1278`（「可审计性」）。
**三条里两条零演示，一条演示了但案例把它关掉了。**

> **对本项目**：AC-05 要求每条回答产出完整证据链、字段齐全率 100%，
> AC-06 要求复核者**仅凭证据链**独立判断。本章证明这两条不会从框架里白得——
> 四个框架加起来提供的可留存审计物是**零**。证据链必须是本项目自己写的一等产物（D-003），
> 不能指望"用了框架就有了 trace"。

### 6.4 回调 / 钩子 / 可观测性：全章统计

书里提了两次，**都是名词**：`ch6:23`（`on_llm_start` / `on_tool_end` / `on_agent_finish`）、
`ch6:417`（AgentScope「智能体钩子」）。代码侧：

```
$ 9 个 .py 逐个 grep -ciE "callback|on_llm|on_tool|on_agent|hook"   → 全部 0，无一文件命中
$ 9 个 .py 逐个 grep -cE "import logging|getLogger"                 → 全部 0，无一文件命中
$ 9 个 .py 逐个 grep -c  "print("
    main_cn.py: 14   utils_cn.py: 1   autogen_software_team.py: 12
    DigitalBookWriting.py: 4          Dialogue_System.py: 15        （合计 46）
```

**全章可观测性 = 46 个 `print`，0 个回调，0 个 logger。**
即 `ch6:23` 用「远比手动添加 `print` 语句高效」批评的做法，是本章四个案例**唯一**在用的做法。

---

## 7. §6.6 本章小结与习题（`ch6:1288-1346`）

### 7.1 小结把四个框架总结成了什么（`ch6:1288-1303`）

四条一句话定性（`ch6:1294-1297`），与 §1.4 的开篇定位对照着看：

| 框架 | 小结的定性 | 与开篇（`ch6:39-42`）比 | 与本章证据比 |
|---|---|---|---|
| AutoGen | 「多角色参与的、**可自动进行的**"群聊"」「以对话驱动协作」 | 一致 | **「可自动进行」被 `ch6:345` 自己的日志推翻**（真人敲 TERMINATE） |
| AgentScope | 「着眼于**工业级应用的健壮性与可扩展性**」「为构建高并发、分布式的多智能体系统提供了坚实的工程基础」 | 比开篇更强（开篇只说「易用性 + 工程化」） | **零演示**。分布式 / 持久化 / 容错三项全章 0 次落地（§3.6、§3.9） |
| CAMEL | 「用**最少的代码**激发两个专家智能体之间深度、自主的协作」 | 一致 | 「最少的代码」属实（63 行）；「深度、自主」无证据（日志 2 轮就截断，§4.4） |
| LangGraph | 「回归到更底层的"状态机"模型」「**尤其是其循环能力**，为构建可反思、可修正的智能体铺平了道路」 | 一致 | **案例零条件边、零循环**（`add_conditional_edges` 命中 0，§5.4）。小结把一个案例没演示的特性作为该框架的收束句 |

**四条里三条的关键限定词在本章内没有证据**（自动进行 / 工业级 / 循环能力）。
注意这不是"书说错了"——AgentScope 可能真支持分布式，LangGraph 真支持循环。
**问题是本章把「框架宣称支持」写成了「本章展示了」**，读者拿不到区分二者的线索。

### 7.2 小结引入的那条权衡轴（`ch6:1299`）

小结提炼的核心权衡是 **「涌现式协作」vs「显式控制」**：

> 「AutoGen 和 CAMEL 更多地依赖于定义智能体的"角色"和"目标"，让复杂的协作行为从简单的对话规则中"涌现"出来……但有时难以预测和调试。而 LangGraph 要求开发者明确地定义每一个步骤和跳转条件，牺牲了一部分"涌现"的惊喜，换来了高度的**可靠性、可控性和可观测性**。」（`ch6:1299`）

外加第二维 **工程化**（AgentScope 代表「从"能运行"到"能稳定服务"的关键跨越」）。

**这条轴对本项目是有用的，但它的刻度是错的。**
按这条轴，选了 LangGraph 就"换来了可观测性"——而 §6.4 的统计说明，
LangGraph 案例的可观测性同样是 15 个 `print`，它换来的是**流程可见**（图画出来了），
不是**结果可复核**（没有任何可留存的审计物）。

**「显式控制」与「可审计」是两件事，小结把它们并列成了一件。**
本项目要的是后者：D-003 要求证据链是返回值，ARCHITECTURE §8.1 把闸门放进调用签名而不是事件顺序——
**即便流程完全显式，只要判定不在返回值里，复核者依然拿不到东西。**

### 7.3 习题问的是什么（`ch6:1306-1346`）

六道大题、共 17 个小问。**按「问的是设计还是问的是事实」分类**：

| 题 | 涉及 | 小问 | 性质 |
|---|---|---|---|
| 1 | 四框架横向 | 3 | 一问要求「参照表 6.1」——**而表 6.1 是图片**（`ch6:31-35`，`docs/images/6-figures/01.png`），§1.4 已记 |
| 2 | AutoGen | 3 | **全部是补洞题**：动态回退、加 QA 角色、对话质量监控 |
| 3 | AgentScope | 3 | 消息驱动 vs 函数调用、**为猎人设计结构化输出模型「包括字段定义和验证规则」**、分布式一致性 |
| 4 | CAMEL | 2 | **冲突解决机制**（`ch6:1329`）、workforce 对比 |
| 5 | LangGraph | 3 | 画图、**加反思节点做条件边循环**、设计一个真用循环的场景 |
| 6 | 选型 | 3 个应用 | A 高并发客服 / B 双 Agent 深度协作 / **C 金融风控审批** |

**习题暴露的重点，与正文暴露的缺口高度重合——而且是同一批缺口：**

1. **题 2 的三个小问，全部在补 §2.2 记的那三个洞**（顺序硬编码 → 要动态回退；
   角色不够 → 加 QA；对话会漂 → 要监控）。作者知道 `RoundRobinGroupChat` 的固定顺序是限制。
2. **题 3 第二问要求「字段定义和**验证规则**」** —— 而 §3.3 已证明
   `code/chapter6/` 全目录 Pydantic 校验器命中数为 **0**。
   **习题要求读者写出书里声称已有、实际不存在的东西。** 猎人模型本身是存在的
   （`get_hunter_model_cn`，`structured_output_cn.py:85-103`），但它只有 `Literal`，没有 validator。
3. **题 4 第一问（`ch6:1329`）承认了终止判定没有仲裁机制**，§4.6 已记。
4. **题 5 第二问要求加条件边做「反思循环」** —— 正好是 §5.4 记的
   「书吹了循环、案例零条件边」那个洞。**书把自己没做的事留成了习题。**

> 这是一条可以直接复用的判定方法：**当一本书的习题在补它正文声称已经解决的问题时，
> 正文的那个声称就是假的。** 本章四道框架题里有三道命中这个模式。

### 7.4 题 6 应用 C 就是本项目的场景（`ch6:1344`）

> **应用C**：金融风控审批系统，需要按照严格的流程处理贷款申请：资料审核 → 风险评估 → 额度计算 → 合规检查 → 人工复核 → 最终决策。每个环节都有明确的判断标准和分支逻辑，要求**流程可追溯、可审计**。

书把「可追溯、可审计」的金融流程作为一道**选型题**提出来，选项是四个框架 + 从零开发。
按小结那条轴，标准答案显然是 LangGraph（显式控制 + 循环 + checkpointer）。

**而本章自己的证据说这个答案不成立**：
LangGraph 案例的 checkpointer 是 `InMemorySaver`（退出即失）、
每轮换 `thread_id`（历史读不回来）、降级路径与正常路径写同一个 `step="completed"`（§5.5）。
**照着本章选 LangGraph 去做应用 C，拿到的是「流程图可画」，不是「结论可复核」。**

这条对本项目是一次外部佐证，不是新结论：
**「可追溯」这个需求，四个通用框架没有一个原生提供**，它必须是自己造的一等产物。
对应 D-003 与 ARCHITECTURE §8.1—§8.4。

### 7.5 参考文献（`ch6:1347-1357`）

五条：AutoGen（COLM 2024）、AgentScope（arXiv 2402.14034）、CAMEL（NeurIPS 2023）、
LangGraph（GitHub）、AutoGen `UserProxyAgent` 文档。
**四个框架各一条一手来源，LangGraph 与 AutoGen 文档条是链接不是论文。**
本章正文里那些「零演示」的能力断言（分布式 / 持久化 / RPC / 企业级），
**在参考文献里也没有对应的出处**——它们既不是本章观测，也没标注是从哪篇文档转述的。

---

## 8. 对 finaudit-agent 的骨架启示

按 `references/README.md` 硬规则 3：**每条必须带落地点，或明写「未落地」并说明该落到哪里。**
编号 `S6-x`（该借鉴）/ `X6-x`（该刻意不借）仅本文件内使用。

### 8.1 该借鉴的

| # | 条目 | 出处 | 落地点 |
|---|---|---|---|
| **S6-1** | **把「这个字段怎么被合并」写进字段类型**，而不是指望每个写入方记得 append。`Annotated[list, add_messages]` 让 reducer 成为 schema 的一部分 | LangGraph，`Dialogue_System.py:24`；§5.2 理由一 | **未落地。** 应新增一条决策（`DECISIONS.md`，紧接 D-019 的编号）：*证据链字段的合并语义写进 schema，禁止由写入方自行决定覆盖还是追加*。在此之前先记入 `docs/agent/OPEN-ITEMS.md` N 区 |
| **S6-2** | **合法范围编码进封闭枚举，枚举之外的取值没有表示形式**——不是"会被发现"，是"构造不出来" | AgentScope `Literal[tuple(...)]`，`structured_output_cn.py:24-41`；§3.2 A 档 | **已落地。** `ARCHITECTURE.md §8.2`（`Refusal` 封闭枚举）＋ **D-018**（拒绝理由取自封闭枚举，`resolve.py` 的 `RefusalCode` 模式） |
| **S6-3** | **合法域由「本次调用的真实数据」在运行时生成**（工厂函数返回 `type[BaseModel]`），而不是写死一张常量表 | AgentScope `get_vote_model_cn(agents)`，`structured_output_cn.py:24-41`、调用点 `main_cn.py:171/238/291` | **未落地。** 本项目的同构物是「本次批次里**实际抽到**的科目名集合」。应落到 **D-016 的补充节**（映射表按命名空间拆分 → 合法标签集合应能按命名空间在读入时物化成封闭域），不是新决策 |
| **S6-4** | **一次调用推进一个有边界、外部可计数的单位**，而不是内部黑箱循环。`step() -> (a, b)` 让 `while n < limit` 成为调用方的权力 | CAMEL，`DigitalBookWriting.py:49-51`；§4.8 | **已落地。** **D-018**「勾稽校验是**批次级**闸门」——批次正是本项目的"外部可数推进单位" |
| **S6-5** | **状态是显式 schema、每个事实单一来源**；反面是把派生数据物化成并列字段 | LangGraph `SearchState` 六字段（`:23-29`）vs AgentScope 六个手工同步的列表（`main_cn.py:40-53`）；§6.2 | **已落地。** **D-016**（标签是有序片段序列，逐字匹配 → 单一来源）＋ **D-019**（页码拆成 `page` / `anchor_page` 两个整数，而不是一个字段承载两义） |
| **S6-6** | **显式注册表天然给出「本次用到了哪些能力」的枚举点**——这是证据链里 `tools_used` 的现成挂点 | LangGraph `add_node`/`add_edge` 字符串注册，`Dialogue_System.py:180-186`；§5.6 | **未落地。** 本项目 Phase 2 才会有工具层。应落到 `ARCHITECTURE.md §8` 新增小节，与 §8.1「闸门放调用签名」并列；**并且注册标识不能是裸名字**（理由见 X6-6） |
| **S6-7** | **书给的调试三分层**：① 节点内部逻辑错 ② 节点间传递的状态数据异变 ③ 边跳转条件失误。这是全章最有用的一句，且它正好点名了书自己在优势里推荐过的两个写法 | `ch6:1286`；§5.7 末行 | **未落地。** `EVAL_CASES.md §5 失败归因分层`已存在但分层维度不同。这三分法应作为**归因分层的一次外部对照**补进 `EVAL_CASES.md §5`——本项目的对应物是「抽取错 / 口径传递错 / 闸门判定错」 |

### 8.2 该刻意不借的（每条附理由）

| # | 条目 | 出处 | 为什么不借 | 落地点 |
|---|---|---|---|---|
| **X6-1** | **降级路径与正常路径写同一个终态** | LangGraph `generate_answer_node`，搜索成功与搜索失败都写 `step="completed"`（`Dialogue_System.py:148`）；§5.5 | 终态字段是下游**唯一**能机读的"这次是怎么完成的"。两条路径写同一个值，等于把降级事实从返回值里删掉——下游拿到 `final_answer` 无法判断它有没有外部依据。书的补救是在 fallback prompt 里请模型自述「这是基于已有知识的回答」，**把机器可判定的事情交给模型自觉**。审计场景的等价动作是「没抽到这张表 → 用模型知识补一个数」，那是伪造证据 | **已落地（`ARCHITECTURE.md §8.3` 的 2026-08-22 补充节，提交 `10d2927`）。** **回标（2026-08-23，T-5）**：本条写作时确为缺口，标注「未落地」在当时正确；缺口已于 `10d2927` 补上——§8.3 现规定终态至少三分 `completed ｜ completed_degraded{cause: 封闭枚举} ｜ refused{code: 封闭枚举}`，且 `cause` 不得因取值为空而从事件中消失。**标注此前未回改，属 T-1 查出的 4 条 `STALE` 之一。** 以下为原文，保留不改： `ARCHITECTURE.md §8.3` 只规定了**拒绝**事件必须带结构化理由码且不得因空消失，**没有覆盖「降级成功」**。应在 `ARCHITECTURE.md §8` 新增一条：*成功终态必须区分 `completed` 与 `completed_degraded{cause: 封闭枚举}`，且 `cause` 字段不得因取值为空而从事件中消失*。这条同时是 **AC-05**（字段齐全率 100%）与 **AC-08**（失败归因覆盖率 100%，不允许"未知"）的前置条件 |
| **X6-2** | **用类型注解假装有契约，但不跑 checker** | LangGraph Demo 三个节点全部注解 `-> SearchState`，实际返回部分字段 dict（`:42/:80/:132`）；`code/chapter6/` 零测试、零 mypy、零 pyproject；§5.2 代价一 | **比没有类型更危险**：它制造"我们有类型"的错觉，于是运行时校验被省掉。注解一旦不被执行就退化成注释，而注释可以撒谎且没人发现。注意书稿正文这里反而是对的（`ch7` 侧同理）——**错在仓库，不在理念**，说明这类腐烂是"写完没人查"造成的 | **未落地（本轮新发现的缺口）。** **D-015** 已经用对了同一个机制（「依赖方向单向且**由测试强制**」），但它只覆盖依赖方向。「类型注解必须由 checker 执行」缺一条**仓库级门禁**：应落到 `rules/commands.md` 的门禁一节（加 mypy/pyright 到冻结校验同一批命令里），Phase 1.5 起生效 |
| **X6-3** | **把边界写进提示词里的口令 / Inception Prompt** | AutoGen 四段 system message 结尾的中文传球口令（`autogen_software_team.py:45/70/95/113`）；CAMEL「最关键的一环」是一段自然语言（`ch6:730`）；§2.2、§4.2 | 约束存在于「模型被要求怎么做」而非「系统允许什么被表示」。AutoGen 的口令与真实顺序是两个来源、可矛盾且不报错；CAMEL 的协议定义端在框架内部、执行端在调用方，书稿版与仓库版已经分叉 | **已落地。** `ARCHITECTURE.md §8.1`（闸门放进调用签名，绕过在类型上不可表达）＋ **D-017**（能力边界写死在语法里：自建封闭算术解析器，硬性排除 `eval()`） |
| **X6-4** | **用全局裸子串匹配做终止 / 判定** | AutoGen `TextMentionTermination("TERMINATE")` 对任何消息生效（`:133`）；CAMEL `if "CAMEL_TASK_DONE" in user_response.msg.content`（`:57`，连尖括号都没有）；§2.2、§4.2 | 值域没有封闭：任何一段正文——包括否定句、包括复述协议本身——都能触发。而且发出者不受限定，书用「在我们的设计中」描述限制，那是"靠自觉"的同义词 | **已落地。** `ARCHITECTURE.md §8.2`（封闭枚举，不是自由文本）＋ **D-017**（同源理由：边界要么在语法里，要么没有） |
| **X6-5** | **fail-open，并在失败时编一个值出来** | AgentScope 狼人击杀失败 → `random.choice(valid_targets)`（`main_cn.py:153-157`）；书还在 `ch6:607-623` 推荐 `default_response = DiscussionModelCN(...)`；§3.5、§3.7 | 程序替模型做的决定，在后续日志里与真实决定**无法区分**（`Msg.metadata` 存的是最终值，不是"这个值怎么来的"）。狼人杀里代价是一局游戏，审计里就是伪造证据。**书在两个独立位置推荐了「失败就编一个」**，说明这是范式级默认，不是个案 | **已落地。** **D-018**（fail-closed 放在计算层的**读入边界**）＋ **D-003**（证据链必须能区分「模型说的」与「系统补的」） |
| **X6-6** | **同一个字段承载两种语义 / 值域不封闭** | LangGraph `search_results` 既装结果也装 `"搜索失败：{msg}"`（`:127`）；AgentScope 弃票写 `None`，与真实姓名同处一个值域，`Counter(...).most_common(1)` 会让 `None` 当选（`utils_cn.py:40-48`）；§5.5、§3.5 | 值域不封闭 = 下游必须靠"看内容猜语义"。这类缺陷不会报错，只会在极端分布下产生荒谬结果 | **已落地，而且本项目已经做过两次同样的拆分。** **D-019**（页码拆成 `page` / `anchor_page` 两个整数）＋ **D-020**（`scope_change` 改挂新字段 `notes.consolidation_scope_change`，不再复用旧字段） |
| **X6-7** | **把派生数据物化成多个并列字段，靠手工同步** | AgentScope 的存活状态同时存在于 `alive_players` / 五个阵营子列表 / `roles` / `players`；`update_alive_players` 必须逐一剔除同一个死者（`main_cn.py:258-269`），漏一个 = 幽灵玩家；§3.6 | 漏改不报错，只产生行为漂移。这与 X6-6 是一对：一个是"一个字段两种意思"，一个是"一个意思多个字段" | **未落地。** 本项目的风险面在映射表与抽取记录之间（同一个科目的标签、命名空间、页锚点可能各存一份）。应落到 **D-016 的补充节**，写明*派生集合不得与权威表并列存储，只能在读入时按需物化* |
| **X6-8** | **判定函数顺手改世界（路由函数带副作用）** | `should_continue` 在返回路由字符串前写 `state["final_answer"] = ...`（`ch6:992-1000`），书把它当范例印出且未加提示；§5.2 代价二 | 判定与副作用绑在一起，就无法单独测试判定、也无法在不执行副作用的前提下复核判定 | **已落地。** `ARCHITECTURE.md §8.1`：`resolve_scope(...) -> ScopeSpec \| Refusal`——**判定只返回判定** |
| **X6-9** | **相信「消息驱动就不用写显式流程了」** | `ch6:499` 称 AgentScope「以消息驱动**代替**状态机」，而 `run_game`（`main_cn.py:311-365`）就是一个手写的顺序状态机；`MsgHub` 只换掉了「谁能听见谁」；§3.9 末条 | 本项目的 pipeline 必须有显式阶段（读入 → 校验 → 解析 → 计算 → 出证据）。这句话如果被当真，会导致阶段边界被消息路由的灵活性掩盖掉——**而 AgentScope 自己也没做到** | **未落地（也不需要新决策）。** 它约束的是**阅读外部材料的方式**，不是机制。应记入 `rules/pitfalls.md`（本项目的高代价陷阱，预防性）：*「X 代替了 Y」类断言必须去代码里核对 Y 是否真的消失了* |
| **X6-10** | **把「审查角色」当成质量保证** | AutoGen 团队漏掉了任务书明写的"涨跌额"，这条漏检同时穿过 CodeReviewer（system message 写着「评估代码的整体质量」）与 UserProxy（description 写着「验证功能是否符合预期」）两道关；`output.py` 可独立复核；§2.5 | **审查角色不产生审查能力。** 给一个 LLM 贴 "Reviewer" 的 system message，不会让它对照验收标准逐条打勾。要对照就得有**机器可判定**的验收项——枚举可以被程序穷举，中文的「验证功能是否符合预期」不能 | **已落地，且是精确同构。** `EVAL_CASES.md §3.3 J-1`「判分者与被判者不得同源」——AutoGen 的失败正是**同源判分**的实例（同一批 LLM、同一场对话里互审）。另 **AC-08**（失败归因覆盖率 100%，不允许"未知"）要求的正是可穷举的判定项 |

### 8.3 计数

**该借鉴 7 条**：已落地 3（S6-2 / S6-4 / S6-5），未落地 4（S6-1 / S6-3 / S6-6 / S6-7）。
**该刻意不借 10 条**：已落地 **7**（X6-3…X6-6 / X6-8 / X6-10 / **X6-1**），未落地 **3**（X6-2 / X6-7 / X6-9）。
**合计 17 条，10 已落地 / 7 未落地。**

> **计数已于 2026-08-23（T-5）同步**：X6-1 由「未落地」改判为已落地（`10d2927`）。
> 紧接着的两段小结写于改判之前，**刻意不改**——它们记录的是当时的判断，而「X6-1 是本轮读出来的真缺口」这句在当时成立。

**八条未落地里，只有两条需要新决策**（S6-1 字段合并语义、X6-1 降级终态），
其余六条分别是既有决策的补充节（S6-3 / X6-7 → D-016）、
既有文档的新小节（S6-6 → ARCHITECTURE §8、S6-7 → EVAL_CASES §5）、
门禁配置（X6-2 → `rules/commands.md`）、阅读纪律（X6-9 → `rules/pitfalls.md`）。

**X6-1 与 X6-2 是本轮读出来的两个真缺口**——它们都是「本项目已经用对了同一个机制，
但覆盖面比这条教训窄」的形态：`ARCHITECTURE §8.3` 只管拒绝不管降级；
`D-015` 只管依赖方向不管类型注解。**部分覆盖比零覆盖更容易被误认为已完成。**

---

## 9. 补读：`AgentScopeDemo/README.md`（覆盖表补齐的最后一个文件）

这份 README 此前未读（§3 的文件清单里漏了它，覆盖表也因此写成「6 个文件」而目录里是 7 个）。
补读后它**独立佐证了两条已有结论、新增两条**——所以单列一节，而不是塞回 §3。

### 9.1 它把 §3.2 那个「最值得抄的机制」在文档里降级回了裸 `str`

README「技术亮点 → 结构化输出」小节印的是：

```python
class VoteModelCN(BaseModel):
    vote: str = Field(description="投票目标玩家姓名")          # ← 裸 str，模块级类
    reason: str = Field(description="投票理由")
    confidence: int = Field(ge=1, le=10, description="信心程度")
```

真身 `code/chapter6/AgentScopeDemo/structured_output_cn.py:24-41 @45dd84e`：

```python
def get_vote_model_cn(agents: list[AgentBase]) -> type[BaseModel]:
    class VoteModelCN(BaseModel):                              # ← 工厂函数内的嵌套类
        vote: Literal[tuple(_.name for _ in agents)] = Field(
            description="你要投票淘汰的玩家姓名",
        )
        reason: str = Field(description="投票理由，简要说明为什么选择此人")
        suspicion_level: int = Field(description="对被投票者的怀疑程度(1-10)", ge=1, le=10)
    return VoteModelCN
```

三处不一致，按严重性排：

| # | README | 真身 | 后果 |
|---|---|---|---|
| 1 | `vote: str` | `vote: Literal[tuple(存活名单)]` | **把 §3.2 的 A 档写成了 B 档。** 照 README 抄的人拿到的是「投给死人也能通过」的那个版本 |
| 2 | 第三个字段叫 `confidence` | 叫 `suspicion_level` | 字段名对不上，按 README 构造的 dict 会缺一个必填字段 |
| 3 | 模块级 `class` | 工厂函数内的嵌套类，需 `get_vote_model_cn(agents)` 取得 | README 的写法根本拿不到「随存活名单变化」这个能力 |

（`reason` 两边一致；`ge=1, le=10` 这类数值约束在代码里是真实存在的——
`structured_output_cn.py` 全文 `ge=|le=|gt=|lt=` 命中 **11**——只是挂在别的字段名上。）

**最荒唐的是同一份 README 的下一段「并发管道」里又写对了：**

```python
vote_msgs = await fanout_pipeline(
    self.alive_players,
    structured_model=get_vote_model_cn(self.alive_players),   # ← 工厂调用，正确
    ...
)
```

**同一个文件里，工厂调用和裸 `str` 类定义并存。**

这条把 §3.2 的结论推远了一步：**这个仓库里最强的那个机制（`Literal` 工厂），
连它自己的文档都没描述对。** 「合法域编码进类型」如果没有单一权威定义，
它会在文档层被悄悄降级回字符串——**而读者抄的是文档。**
§3.4 记的「一个事实三个来源」在这里变成了四个，且新增的这个是最弱的一版。

### 9.2 它把 `DialogAgent` 那个错误独立复现了一次

§3.7 第 1 条记：书稿 `ch6:496` 说「每个玩家都是一个基于 **`DialogAgent`** 的实例」，
而代码用的是 `ReActAgent`（`main_cn.py:11,60`）。

README 的「分层架构」图里，最底层写的是：

```
角色建模层 (DialogAgent)
    ├── 角色提示词
    ├── 结构化输出
    └── 行为约束
```

**同一个错误出现在两个独立位置**（书稿正文 + 配套 README），说明它不是排版事故，
而是**作者对自己代码的心智模型停在了旧版本**。
含义与 §3.4 同源：**当一个事实有 N 个来源时，错的那份会被复制，而不是被发现。**

### 9.3 它宣称的「容错机制」与代码正相反（新增，可独立复核）

README「案例特点」第五条：

> - **容错机制**：单个智能体异常不影响整体游戏流程

§3.7 第 3 条已用 grep 确认：`main_cn.py` **全文只有一处 `try/except`**（`:313`/`:362`），
是 `run_game` 的**最外层兜底**。

最外层兜底的语义恰恰相反：任何一个智能体抛出的异常都会一路冒泡到 `run_game`，
**整局游戏终止**。README 承诺的「单个智能体异常不影响整体流程」需要的是
**每个 `await agent(...)` 各自包 try**——而那正是书稿 `ch6:607-623` 印了、仓库里不存在的那段代码。

**所以这条宣传语描述的是书稿里那段不存在的代码，不是仓库里的代码。**

### 9.4 README 文件清单又漏了一个文件（新增）

README 的「📁 文件说明」列了 6 个文件（`main_cn.py` / `prompt_cn.py` / `game_roles.py` /
`structured_output_cn.py` / `utils_cn.py` / `README.md`），**漏了 `requirements.txt`**——
而它恰恰是这个 Demo 里唯一钉了版本的文件（`agentscope==1.0.2`），
也是 §3.7 第 2 条那个 import 错误（书上 `agentscope.agents` vs 代码 `agentscope.agent`）
之所以能被判定的依据。

与 §2.6 记的 AutoGenDemo README **多**列了一个不存在的 `llm_client.py` 合起来看：
**两份 README，一份多列、一份漏列，没有一份与 `git ls-tree` 一致。命中率 0/2。**

### 9.5 这一节对 finaudit-agent 加了什么

不是新机制，是把 **X6-7**（派生数据被物化成独立字段）的适用范围扩大一层：

> **文档也是一份派生数据。** README 里的类定义、架构图、文件清单，
> 全都是从代码派生出来的事实的**第二份拷贝**，而且是**唯一没有任何机制校验的那一份**。

**落地点**：与 X6-7 同一处（**D-016 的补充节**），但要把范围写全——
*派生集合不得与权威表并列存储*，这里的「并列存储」**包括写进文档**。

本项目已经有一个成功对照：`scripts/check_xrefs.py` 让 `D-0xx` / `AC-xx` / `OQ-xx` 这类
交叉引用**悬空即非零退出**，所以这类引用不会腐烂；
而字段名、类名、文件清单**没有这类校验**，所以本章两份 README 全烂了。
可行的最小动作是把「文档里出现的字段名 / 类名必须在代码中存在」纳入同一类门禁，
与 **X6-2**（有类型注解但不跑 checker）的门禁缺口**合并成一条待办**，
落到 `rules/commands.md` 的门禁一节。
