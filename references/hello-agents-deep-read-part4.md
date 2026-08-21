# hello-agents 深读 · Part 4

**模式：RESEARCH。** 本轮补读 Ch3 全章 + 四个此前反复引用却一行未读的「空洞」小节（Ch7.2 / Ch8.2 / Ch9.6.3 / Ch10.5），
以及余力部分（Ch4.3 / Ch10.3 / Ch10.4）。

语料：`<scratchpad>/ha_md2/ch0X_zh.md`（以中文正文为准）。行号均指 `_zh` 文件。
> 路径更正（2026-08-22）：原写 `ha_md/`，该目录已被清空；本轮 §7–§9 用的是抢救出来的 `ha_md2/`，
> 并以 `<scratchpad>/ha_src/docs/chapter*/` 下的原始源文件做交叉核对（行号一致，差异仅 CRLF/LF）。
> §1–§6 成文时用的是 `ha_md/`。本轮在 `ha_md2/` 上抽查了它们的行号：
> **ch04 / ch08 / ch09 / ch10 抽查项全部命中，ch03 有多处偏差、ch07 有一处偏差——勘误见 §9.6。**
> 未逐条重核，只抽查。
承接 `hello-agents.md`(127) + `-deep-read.md`(268) + `-part2.md`(779) + `-part3.md`(848)。
Ch11 按 D-011（不做训练与微调）跳过，本轮未读、也不出现在下文任何结论里。

---

## 0. 本轮覆盖表（诚实标注）

| 目标 | 文件 | 行号范围 | 读到什么程度 |
|---|---|---|---|
| Ch3 全章 | `ch03_zh.md` | 1–1022 | **全文**（含习题与参考文献） |
| Ch7.2 HelloAgentsLLM 扩展 | `ch07_zh.md` | 154–458 | **全文**；小节编号存在，标题为「7.2 HelloAgentsLLM扩展」 |
| Ch8.2 记忆系统 | `ch08_zh.md` | 283–1084 | **全文**（正文见 §3）；行号已复核，8.3 起于 :1085 |
| Ch9.6.3 核心实现 | `ch09_zh.md` | 2059–2468 | **全文**（正文见 §4）；行号已复核，9.6.4 起于 :2469 |
| Ch10.5 构建自定义 MCP 服务器 | `ch10_zh.md` | 1885–2353 | **全文**（正文见 §5）；行号已复核，10.6 起于 :2354 |
| Ch4.3 Plan-and-Solve | `ch04_zh.md` | 586–863 | **全文**（正文见 §6）；本轮定位，4.4 起于 :864 |
| Ch10.3 A2A | `ch10_zh.md` | 1108–1654 | **全文**（正文见 §7）；行号已复核，10.4 起于 :1655；已与原始源文件交叉核对 |
| Ch10.4 ANP | `ch10_zh.md` | 1655–1884 | **全文**（正文见 §8）；行号已复核，10.5 起于 :1885；已与原始源文件交叉核对 |

> ⚠ **上表曾被提前填写。** Ch8.2 / Ch9.6.3 / Ch10.5 三行原写作「全文」并附了小节标题，
> Ch4.3 / Ch10.3 / Ch10.4 三行原写作「见下文」——但正文当时只写到 Ch7.2，这六行**都没有正文支撑**。
> 2026-08-21 已全部降级为「待读」。**本表此后只在正文落盘之后才允许改回「全文」。**
>
> 已读部分（Ch3 / Ch7.2）的小节编号确实在文件里定位到了，没有需要写「未找到」的。
> 唯一编号异常：`ch03_zh.md:426`（**原写 `:451`，本轮复核更正，见 §9.6**）
> 用 `<strong>3.1.2.5 位置编码</strong>` 冒充四级标题，
> 不是 markdown heading，所以不会出现在目录里——这是转换产物的格式瑕疵，不是内容缺失。
>
> **2026-08-22 补记**：Ch10.3 / Ch10.4 两行本轮改成「全文」，
> 顺序是**先把 §7 落盘 → 再改 Ch10.3 那行 → 再把 §8 落盘 → 再改 Ch10.4 那行**，
> 没有再犯提前填表。两行的行号也不是沿用上一轮的标注，是本轮用 `grep -n "^## 10\.[345] "`
> 重新取的（结果与上一轮一致），并与 `ha_src/` 原始源文件交叉核对过。

---

## 1. Ch3 大语言模型基础（全文，`ch03_zh.md:1-1022`）

Ch3 是纯背景章：N-gram → 神经网络语言模型 → RNN/LSTM → Transformer → Decoder-Only → 提示工程 → 分词 → 模型选择 → 缩放法则与幻觉。
对 finaudit-agent 而言，**3.1 基本无可迁移内容**（Transformer 手写实现），价值集中在 **3.2.1 提示工程**、**3.2.2 分词**、**3.2.4 模型选择**、**3.3.2 幻觉**。

### 1.1 §3.1 语言模型与 Transformer（`ch03_zh.md:5-511`）

- 3.1.1（`:7-185`）N-gram + 马尔可夫假设 + MLE 计数估计，手算 `P(datawhale agent learns)=0.167`，附 27 行可运行 Python（`:64-104`）。
  书里给出的正文数字 0.333 / 1.000 / 0.500 / 0.167 与代码块内嵌的 `>>>` 输出**一致**（`:99-104`）——这里没有对不上的问题。
- 词嵌入类比 `king - man + woman ≈ queen`（`:130-160`）：**这是一个被凑出来的演示**。
  代码里 `embeddings` 是手写死的四个二维向量（`:139-144`），
  `king-man+woman = [0.9,0.2]`，而 `queen` 恰好也被定义成 `[0.9,0.2]`，所以余弦相似度必然是 `1.0000`（`:163`）。
  正文把它写成「结果与 queen 的位置惊人地接近」（`:136`），但代码里那是**恒等式，不是发现**。
  这是本章唯一一处「演示的说服力来自数据被预先安排」的地方，值得记一笔（下文反面案例 R-1）。
- 3.1.2（`:186-475`）Encoder-Decoder 骨架 → 多头注意力 → FFN → Add&Norm → 位置编码，逐块补全 PyTorch 实现。
  自注意力公式 `softmax(QK^T/sqrt(d_k))V`（`:305`）。
  值得注意的是骨架代码里 `EncoderLayer.__init__` 写 `MultiHeadAttention()` **不传参**（`:241`），
  而 3.1.2(2) 补全的 `MultiHeadAttention.__init__(self, d_model, num_heads)` 是**必须传参**的（`:323`）——
  骨架与实现不兼容，照抄会 `TypeError`。书里没有回头修这个骨架。
- 3.1.3（`:476-511`）Decoder-Only 与因果掩码：训练期把未来位置的注意力分数置为极大负数，softmax 后归零（`:498`）。

### 1.2 §3.2 与大语言模型交互（`ch03_zh.md:512-899`）

这是 Ch3 里对本项目**真正有用**的部分。

**（a）采样参数的分层过滤顺序（`:520-537`）**——这条工程细节以前几轮没记过：

> 优先级顺序为：温度调整 → Top-k → Top-p。（`:535`）
> 「若同时设置，实际候选集为两者的交集」；「温度设为 0，则 Top-k 和 Top-p 变得无关紧要」（`:536`）。

书里给的温度分档建议（`:526-530`）：
- 低温 `0 ≤ T < 0.3`：事实性任务、**法律条文解读**、技术文档撰写、学术概念解释；
- 中温 `0.3 ≤ T < 0.7`：日常对话；
- 高温 `0.7 ≤ T < 2`：创意任务。

→ 对 finaudit-agent：「口径判定 / 准则条文解读」按书里的分类落在**低温档**。
这条可以直接写进我们的 LLM 调用默认配置理由，但**注意书里没给任何实验支撑**，这是经验建议不是实证结论。

**（b）零样本 / 单样本 / 少样本（`:539-583`）**——标准内容。
唯一值得记的是零样本案例（`:547-550`）把答案 `情感:正面` 直接写进了「提示」代码块里，
读起来像是把答案当成了提示的一部分。这是排版失误，不是方法。

**（c）指令调优（`:585-607`）**、**（d）角色扮演与上下文示例（`:609-643`）**：
`:632-643` 的 JSON 抽取示例是全书**最早出现的「结构化输出」范式**——
但它靠的是**在提示里给一条示范 JSON**，没有 schema、没有校验、没有解析失败的处理。
参见下文 §6 对 Ch7.4.5 FunctionCallAgent 的对照。

**（e）思维链（`:645-666`）**：CoT 案例是篮球胜率题，模型输出 `(60/95)*100% ≈ 63.16%`。
我手算：60/95 = 0.631578…，四舍五入到两位小数确实是 63.16%。**这个数字是对的。**

**（f）3.2.2 分词（`:666-765`）**：BPE 手推 + 20 行代码，四次合并输出与正文表述一致。
真正有用的是 3.2.2.3「分词器对开发者的意义」（`:760-765`）：

> 「模型的上下文窗口（如 8K, 128K）是以 **Token 数量**计算的，而不是字符数或单词数。
> 同样一段话，在不同语言（如中英文）或不同分词器下，Token 数量可能相差巨大。」（`:762`，复核后修正：原写 `:763`，那是「API 成本」条）
> 「模型可能很擅长计算 `2 + 2`，但对于 `2+2`（没有空格）就可能出错」（`:764`，复核后修正：原写 `:765`）

→ 对 finaudit-agent 直接相关：**年报 PDF 里的财务数字带千分位逗号、括号负号、全角字符**，
这些都会被分词器切成非常规 token 序列。我们做数值抽取时不能指望 LLM 直读原始表格文本，
必须先归一化再喂给模型——或者干脆让数值走确定性解析路径，不进模型。

**（g）3.2.4 模型选择（`:860-898`）**：八个维度（性能/成本/延迟/上下文窗口/部署方式/生态/可微调性/安全）。
里面唯一可核验的、也是**对我们最有用的一条**：

> 「使用 API 的方式最简单便捷，但数据需要发送给第三方，且受限于服务商的条款。」（`:874`）

→ 与 D-010（只用公开数据）叠加：因为我们只处理巨潮公开年报，这条约束对本项目**不构成阻塞**，
这正好是我们相对「企业内审 Agent」的一个可讲清楚的差异点。

### 1.3 §3.3 缩放法则与局限（`ch03_zh.md:900-936`）

- 3.3.1（`:904-912`）Kaplan 幂律 + Chinchilla 修正 + 能力涌现。
- 3.3.2 模型幻觉（`:914-936`）：三分类——事实性 / 忠实性 / 内在幻觉（`:918-920`）。
  缓解手段列了 RAG、多步推理与验证、外部工具（`:930-934`）。

**⚠ 参考文献编号存疑（`ch03_zh.md:1017`）**：
Chinchilla 一文被标为 `arXiv preprint arXiv:2203.07678`，作者写作 `Hoffmann, J., Borgeaud, E., ...`。
我记忆中 Chinchilla（Training Compute-Optimal Large Language Models）的 arXiv 号是 **2203.15556**，
第二作者是 Borgeaud **S.**（Sebastian）。**我没有联网核验，标记为 UNVERIFIED**，只作为「疑似错引」记录。
另外 `:1018` 把 Bender et al. 2021（Stochastic Parrots）的出处栏留空，只有标题。

**幻觉一节的关键缺口（有 grep 支撑，见 §9）**：
3.3.2 通篇在讲「怎么减少幻觉」，但**没有一句在讲「怎么度量幻觉」**，
也没有「模型应当拒答」这一条。全书 16 章 `拒答`/`不可回答`/`无法回答` 三个词**总命中 0**。

---

## 2. Ch7.2 HelloAgentsLLM 扩展（全文，`ch07_zh.md:154-458`）

小节编号存在，标题为 **「7.2 HelloAgentsLLM扩展」**（`ch07_zh.md:154`）。三个子节：
7.2.1 支持多提供商（`:162-268`）、7.2.2 本地模型调用（`:270-349`）、7.2.3 自动检测机制（`:350-458`）。

### 2.1 7.2.1 多提供商：一个「继承示范」里的真实缺陷

书里教读者**通过继承而非改源码**来加 provider（`:171`「直接修改已安装的库源码是一种不被推荐的做法」）——原则是对的。
但示范代码本身有问题：

```python
if provider == "modelscope":
    self.provider = "modelscope"          # :203
    self.api_key = ...                     # :206
    self.base_url = ...                    # :207
    self.model = ...; self.temperature = ...; self.max_tokens = ...; self.timeout = ...
    self._client = OpenAI(...)
else:
    super().__init__(...)                  # :224
```

**`modelscope` 分支从头到尾没有调用 `super().__init__()`**，而是手工重新赋值了它猜测父类会设置的 8 个属性。
正文却说这样「保留了原有框架的全部功能」（`:228`）——**这句话只对 `else` 分支成立**。
父类以后只要多设一个字段（比如重试次数、日志句柄），`modelscope` 分支就会在运行时 `AttributeError`，
而且**是在第一次真正调用时才炸**，不是在构造时。

→ 对 finaudit-agent：这正是我们要避免的「构造期沉默、调用期爆炸」。
我们的 LLM 客户端如果要分 provider，应当**先 `super().__init__()` 再覆写差异字段**，
或者干脆把 provider 差异做成数据（一张 dict 表）而不是做成继承分支。

### 2.2 「库自己往 stdout 打印」的坏味道（`ch07_zh.md:262-264`）

调用示例里流式响应的消费循环是空的，注释写：

> `# chunk在my_llm库中已经打印过一遍，这里只需要pass即可`（`:263`）

也就是说 `llm.think()` **既 yield 又 print**。
对我们这种「回答必须附带可独立复核证据链」的系统，这是致命的：
模型原始输出被当作副作用冲进终端，调用方拿到的是生成器，
一旦调用方 `pass` 掉，**这次调用的原始响应就没有任何地方留档**。
证据链要求原始响应必须落盘（带 request/response 哈希），库层不能替我们决定往哪儿输出。

### 2.3 7.2.3 自动检测机制——本节对本项目最重要的一条

`_auto_detect_provider` 的优先级（`:354-366`，代码 `:369-399`）：

1. **环境变量存在性**（最高）：`if os.getenv("MODELSCOPE_API_KEY"): return "modelscope"` → 再 `OPENAI_API_KEY` → `ZHIPU_API_KEY`（`:374-376`）
2. **`base_url` 域名/端口匹配**：`:11434`→ollama，`:8000`→vllm（`:385-391`）
3. **API key 前缀**：`actual_api_key.startswith("ms-") → "modelscope"`（`:395`）
4. 兜底 `return "auto"`（`:399`）

书里称第 1 条是「最直接、最可靠的判断依据」（`:356`）。**我不同意，而且这一条对可审计系统是反面教材：**

- 它把「**用哪家模型**」这个决定，交给了**运行机器上恰好存在哪些环境变量**。
  开发机上因为别的项目残留了一个 `OPENAI_API_KEY`，就足以让本次运行悄悄换一个 provider——
  代码没变、配置文件没变、日志里也只有一行「检测到 provider 为 X」。
- 优先级是**硬编码的顺序**，不是用户意图。同时存在 `MODELSCOPE_API_KEY` 与 `OPENAI_API_KEY` 时，
  ModelScope 永远赢，且书里没有任何冲突告警。
- 这是典型的 **fail-open**：检测不出来就 `return "auto"` 继续跑（`:399`），而不是拒绝启动。

→ 对 finaudit-agent 的直接结论（**建议写入 D-系列或 PROJECT_SPEC 的证据链字段**）：
**provider + model id + base_url + 采样参数必须是证据链里的显式字段，由配置显式声明，缺失即 fail-closed 拒绝运行，
绝不允许从环境推断。** 否则同一个问题在两台机器上会得到两个答案，而证据链里看不出区别。
本书的自动检测是「为了少配一个参数」优化的，我们的场景是「为了别人能复现同一个答案」优化的，两者目标相反。

### 2.4 7.2.2 本地部署（`:270-349`）

VLLM（PagedAttention，`python -m vllm.entrypoints.openai.api_server`，默认 `:8000`）与
Ollama（`ollama run llama3`，默认 `:11434`），二者都暴露 OpenAI 兼容接口，所以接入成本≈0（`:311-349`）。
书里明说本地部署的动机是「数据隐私和成本控制」（`:159`）。
→ 对我们：D-010 只允许公开数据，所以**隐私不是我们上本地模型的理由**；
如果将来要上本地模型，理由只能是成本或可复现性（固定权重 = 结果可复现），这点要在决策里写清楚，别抄书里的动机。

---

## 3. Ch8.2 记忆系统（全文，`ch08_zh.md:283-1084`）

标题 **「8.2 记忆系统：让智能体拥有记忆」**（`ch08_zh.md:283`）。五个子节：
8.2.1 工作流程（`:285`）、8.2.2 快速体验（`:320`）、8.2.3 MemoryTool 详解（`:365`）、
8.2.4 MemoryManager 详解（`:632`）、8.2.5 四种记忆类型（`:701`）。

这是本轮最大的一块，也是**唯一一处我能拿仓库源码反查正文的**（见 §3.2）。

### 3.1 四类记忆的分工（`:312-318`）

认知科学的五阶段（编码/存储/检索/整合/遗忘，`:297-301`）映射成四个模块：

| 类型 | 存储 | 生命周期 | 实现类 |
|---|---|---|---|
| 工作记忆 Working | 纯内存，容量默认 50 + TTL | 会话级，重启即丢 | `:713` |
| 情景记忆 Episodic | SQLite + Qdrant | 长期 | `:768` |
| 语义记忆 Semantic | Neo4j 图 + Qdrant 向量 | 长期、高持久 | `:841` |
| 感知记忆 Perceptual | 按模态分三个 Qdrant collection | 按重要性动态 | `:984` |

对 finaudit-agent 有用的是**分层本身**，不是这套实现。我们的「记忆」其实是三类完全不同的东西：
会话上下文、已确认的口径结论、以及准则条文；把它们混进同一个 store 再用一个分数排序，是下面所有问题的根。

### 3.2 ⚠ 正文与仓库实际产物不一致（第 2 例，继 Ch12 之后）

**书里的入门代码调不通。** 8.2.2「30 秒上手记忆功能」全部写成：

```python
memory_tool.run("add", content="用户张三是一名Python开发者……", memory_type="semantic", importance=0.8)  # :343
```

但仓库里 `MemoryTool.run` 的真实签名是（`hello_agents/tools/memory_tool.py:51`，
从本地 git 对象里恢复的 blob `2eadd3d3`）：

```python
def run(self, parameters: Dict[str, Any]) -> str:   # 只接受一个 dict
    action = parameters.get("action")
    kwargs = {k: v for k, v in parameters.items() if k != "action"}
    return self.execute(action, **kwargs)           # :67
```

`run("add", content=..., memory_type=..., importance=...)` 传的是 **1 个位置参数 + 3 个关键字参数**，
真实签名是 **1 个 dict**，照抄必然 `TypeError: run() got an unexpected keyword argument 'content'`。
能跑的写法是 `run({"action": "add", "content": ...})` 或 `execute("add", content=...)`。

**统计（grep 支撑，范围 `NR>=283 && NR<=1084`）：**

```
grep -c "memory_tool\.run("      → 9    （:343 :347 :351 :357 :361 :448 :455 :464 :472，全部错）
grep -c "memory_tool\.execute("  → 8    （:537 :540 :547 :576 … 全部对）
grep -n "def execute\|def run"   → 只有 1 处 def execute（:370），本章 def run 命中 0
```

同一节里两种写法各占一半，而**正文从未提过它们不是一回事**。
这不是风格不统一，是**先写的那 9 行（读者最先复制的那 9 行）是坏的**。

→ 对 finaudit-agent：这条正好证明了我们那条「示例必须可执行」的门禁值得留着。
文档里的代码块如果不进 CI，它退化的速度和正文的自信程度无关。

### 3.3 四个评分公式，全是魔数，且**零评测**

四种记忆各有一套检索排序公式，形状完全一样：

- 工作记忆（`:752`, `:761`）：`(词法相关性 × 时间衰减) × (0.8 + 重要性 × 0.4)`
- 情景记忆（`:828-830`）：`(向量相似度 × 0.8 + 时间近因性 × 0.2) × (0.8 + 重要性 × 0.4)`
- 语义记忆（`:957`, `:973`）：`(向量相似度 × 0.7 + 图相似度 × 0.3) × (0.8 + 重要性 × 0.4)`
- 感知记忆（`:1054-1055`, `:1064`）：`(向量相似度 × 0.8 + 时间近因性 × 0.2) × (0.8 + 重要性 × 0.4)`

`0.7/0.3`、`0.8/0.2`、重要性权重区间 `[0.8, 1.2]`、consolidate 阈值 `0.7`（`:597`）、
forget 阈值 `0.1`（`:559`）——**没有一个数字给了来源**。
正文对 `[0.8, 1.2]` 的解释是「避免重要性过度影响相似度排序」（`:977`），这是事后合理化，不是标定。

**零命中记录（`NR>=283 && NR<=1084`）：**

```
评测 0    准确率 0    召回 0    命中率 0    基准 0    baseline 0    实验 0    消融 0
（评估 1 —— 出现在 :160 讲 importance 参数「模拟人类大脑对重要性的评估」，与检索质量无关）
```

**8.2 全节没有任何一句在问「这套排序检索得准不准」。** 四个公式、十几个常数，
一个都没有被验证过。这与 Ch3.3.2「只讲怎么减少幻觉、不讲怎么度量幻觉」是同一个病
（见 §1.3），只是这次落在了检索排序上。

→ 对 finaudit-agent 的直接结论：**任何进入证据链的排序权重必须可复现且可被评测。**
我们要么把权重固定并写进证据链字段（这样至少别人能复算），
要么就别做加权融合——单路检索 + 明确的过滤条件，比一个没人验证过的四因子公式更好辩护。

### 3.4 错误被当成正常返回值：字符串，不是异常

8.2 里每一个操作的失败路径都长这样（`:438` `:529` `:568` `:606`）：

```python
except Exception as e:
    return f"❌ 添加记忆失败: {str(e)}"     # :438
```

于是「记忆写入失败」和「记忆写入成功」在类型上**完全一样**——都是 `str`，都返回给 Agent。
Agent 唯一能区分二者的办法是去看字符串开头是 ✅ 还是 ❌。

更糟的两处是**连字符串都不返回**：

```python
except Exception:
    hits = []                # :1043-1044  感知记忆：编码失败 → 当作「没搜到」
```
```python
except Exception:
    return 0.5               # :1079-1080  时间戳解析失败 → 当作「中等新鲜度」
```

`:1043` 把**检索失败**和**检索到 0 条**压成了同一个结果；
`:1079` 把**解析失败**静默计成 0.5 分，让一条时间戳损坏的记忆稳稳排在中游。

→ 这三条直接命中我们关心的「解析失败如何计入」。本书的答案是：**不计入，伪装成正常值。**
对 finaudit-agent 必须反着来：抽取/解析失败是一等状态，
要在证据链里显式落 `status=parse_failed` 并让该条**退出**排序，而不是拿默认分参与竞争。
「查不到」与「查询本身炸了」在审计里是两个结论，不能合并。

### 3.5 记忆没有来源字段——对证据链是致命的

`MemoryItem` 一路带的是 `content` / `importance` / `timestamp` / `metadata` / `session_id`。

**零命中记录（`NR>=283 && NR<=1084`）：**

```
来源 0    出处 0    溯源 0    引用 0    provenance 0    source_id 0
```

也就是说：一条语义记忆「用户张三是 Python 开发者」被检索出来喂进提示之后，
**没有任何字段能回答「这句话当初是谁说的、在哪一轮、依据什么」**。
`session_id` 只能定位到会话，定位不到那一句的出处。

叠加 8.2.3 的 `auto_classify=False`（`:433`）——add 路径硬编码关掉了自动分类，
记忆类型完全由调用方随手指定，也没有校验。

→ 这是本节对本项目**最重要的一条**：记忆一旦无源，它进入答案就等于污染证据链。
finaudit-agent 的任何「记住的结论」都必须携带
`{源文档, 页码/表位, 抽取时间, 抽取器版本, 原文哈希}`，
否则宁可每次重新抽。**可复核性优先于省一次检索。**

### 3.6 工具 schema：有，但约束不到 action

值得肯定的是仓库里 `get_parameters()` 返回的是**真 schema**
（`memory_tool.py:69-96`，`ToolParameter(name/type/description/required/default)`）——
比 Ch3.2「在提示里塞一条示范 JSON」（见 §1.2(d)）强一个量级。

但有个缺口：`action` 声明成 `type="string", required=True`，
九个合法取值（add/search/summary/stats/update/remove/forget/consolidate/clear_all）
**只写在 description 的自然语言里，没有 enum**（`memory_tool.py:73-81`）。
`validate_parameters` 也只检查必填项在不在，不检查取值合法性。
所以模型吐一个 `action="delete"`，schema 层全部放行，一路走到 `execute` 的 if/elif 链尾部静默落空。

→ 对 finaudit-agent：**枚举必须落在 schema 的 enum 里，不能落在 description 里。**
description 是给模型看的提示，enum 才是给校验器看的约束；
只写前者等于把校验寄希望于模型的自觉。

### 3.7 一处该记的诚实（`:761`）

> 「TF-IDF 的向量化表示来自词频和逆文档频率，**并不等同于基于稠密嵌入的语义检索**。」（`:761`）

全书大多数地方乐于把任何检索都叫「语义检索」，这里专门停下来划清了界限。
这是本轮读到的**唯一一处主动降低自己说法强度**的地方，记一笔作为正面样本（对照 §1.1 的反面案例 R-1）。

---

## 4. Ch9.6.3 核心实现（全文，`ch09_zh.md:2059-2468`）

标题 **「9.6.3 核心实现」**（`ch09_zh.md:2059`），9.6.4 起于 `:2469`。
内容是单个类 `CodebaseMaintainer`（`:2074`）的完整代码——长程智能体的收官案例，
把 ContextBuilder + MemoryTool + NoteTool + TerminalTool 缝在一起。
**整节 410 行几乎全是代码，散文只有 3 行**（`:2061`、`:2179` 之类的一句话注释）。

### 4.1 第 6 行就是语法错误（`:2064`）

```python
from typing import Dict， Any, List, Optional     # :2064
```

`Dict` 后面那个逗号是**全角逗号 U+FF0C**，不是 ASCII 逗号。实测：

```
$ awk 'NR==2064' ch09_zh.md | cat -A
from typing import DictM-oM-<M-^L Any, List, Optional$        （M-oM-<M-^L = EF BC 8C = U+FF0C）

$ python -c "ast.parse(src)"
RESULT: SyntaxError: invalid character in identifier | offset 24
```

也就是说**这个收官案例的第一个代码块，从 import 行就跑不起来**。
全语料唯一一处（`grep -c "^from .*，\|^import .*，"`：ch03 0 / ch04 0 / ch07 0 / ch08 0 / **ch09 1** / ch10 0），
是个孤立的中文输入法事故，但它落在了「最终整合案例」上，说明这段代码**从未被执行过一次**。

### 4.2 ⚠ 最严重的一条：`issues_found` 统计的是模型说了几次「问题」

`_postprocess_response`（`:2345`）：

```python
if any(keyword in response.lower() for keyword in ["问题", "bug", "错误", "阻塞"]):   # :2349
    self.note_tool.run({... "note_type": "blocker" ...})
    self.stats["notes_created"] += 1
    self.stats["issues_found"] += 1                                                  # :2359
```

然后 `generate_report`（`:2455`）把它写进 JSON 报告落盘：

```python
"activity": { ..., "issues_found": self.stats["issues_found"] }                       # :2450
json.dump(report, f, ...)                                                             # :2462
```

**`issues_found` 不是「发现了几个问题」，是「模型的回答里出现过几次这四个词」。**
模型说一句「这段代码没有问题」——命中「问题」，`issues_found += 1`，
并且自动生成一条标题为「发现问题: …」的 **blocker 笔记**。

这条指标随后：① 进报告 JSON、② 进 `get_stats()`、③ 下一轮被 `_retrieve_relevant_notes`
以 blocker 最高优先级（`:2243-2247`，`relevance 0.9`）捞回来塞进上下文。
**一个由否定句触发的假阳性，会在后续每一轮里以最高权重污染上下文。**

正文对此**一个字都没说**。零命中记录（`NR>=2059 && NR<=2468`）：

```
评测 0    准确率 0    校验 0    验证 0    引用 0    来源 0
（评估 1 —— 出现在 :2322 的系统提示词里，是给模型的指令「评估代码质量」，不是对本系统的评估）
```

→ 对 finaudit-agent，这是**「指标必须与被测对象解耦」**的教科书反例。
用模型自己的输出做关键词匹配来统计「发现了多少问题」，判分者与被判者同源到了极致：
被测对象的措辞直接决定分数。我们的评测里任何计数型指标，
其触发条件都不能来自被评对象生成的自然语言——必须来自结构化字段或独立解析器。

顺带两处更小的不一致：`:2349` 检查的是 `response`，`:2365` 检查的是 `user_input`，
两个分支判据来源不同却写成 `if/elif`，所以「用户问了计划、模型回答里带『问题』」时，
action 笔记**永远不会被创建**。

### 4.3 引用只进不出（本项目最关心的一条）

笔记检索回来后（`:2239-2262`），`_notes_to_packets`（`:2264`）把它拼成字符串：

```python
content = f"[笔记:{note.get('title','Untitled')}]\n类型: {note_type}\n\n{note.get('content','')}"   # :2280
packets.append(ContextPacket(content=content, ..., metadata={"note_id": note.get('note_id') or note.get('id')}))  # :2282-2292
```

`note_id` **确实被放进了 metadata**（`:2290`）——这一步是对的。
但接下来 `context_builder.build(...)`（`:2152`）只消费 `content`，
`self.llm.invoke(context)`（`:2161`）拿到的是拼好的文本，
**回答生成之后，没有任何一步把 `note_id` 与回答里的具体句子对应起来**。

于是这套系统里所谓「基于历史笔记提供连贯的建议」（`:2303`，系统提示词原话）：
- 检索结果 → 原样回填进提示 ✅
- 回答 → 抽取引用 ❌ **不存在**

这正是本项目四条主线里「**『引用』是真从答案抽取，还是把检索结果原样回填**」的答案：
**本书全程是后者。** 从 Ch8.2（记忆无来源字段，见 §3.5）到 Ch9.6.3（note_id 进了 metadata 却没出口），
全书没有一处做过「answer → source span」的反向绑定。

→ finaudit-agent 的差异化就落在这里：证据链要求的是**回答里的每个数字能指回它的出处**，
而不是「我检索了这些东西然后回答了」。前者需要在生成后做归因，后者只是 RAG 的默认形态。

### 4.4 token 计数用 `len(s)//4` —— 与本书 Ch3 自己的警告直接矛盾

`token_count` 在 ch09 共 7 处全部写成字符数整除 4
（`:1423` `:2010` `:2017` `:2192` `:2212` `:2232` `:2285`，`:1423` 还自注「简单估算」）。

而 Ch3.2.2.3 明确警告过（`ch03_zh.md:762`）：

> 「模型的上下文窗口（如 8K, 128K）是以 **Token 数量**计算的，而不是字符数或单词数。
> 同样一段话，在不同语言（如中英文）或不同分词器下，Token 数量可能相差巨大。」

**同一本书，第 3 章说不能用字符数估 token，第 9 章七处全用字符数估 token。**
而且这里的内容是中文笔记与中文代码注释——中文的 chars/token 比值和英文差得最远，
`//4` 在英文上大致成立，在中文上会**严重低估**。
`ContextConfig(max_tokens=4000, reserve_ratio=0.15)`（`:2104-2105`）建立在这个估算之上，
所以那个 15% 的保留余量是拿一把不准的尺子量出来的。

零命中支撑：ch09 全文 `tiktoken` **0 次**（`grep -c tiktoken ch09_zh.md → 0`）。

### 4.5 其余静默失败点

- `:2260-2262`：`_retrieve_relevant_notes` 整体 try/except，失败 `print` 一行 WARNING 后 `return []`
  —— 又一次把「检索炸了」压成「没检索到」（同 §3.4 的 `:1043`）。
- `:2438`：`except:` **裸 except**，连 `KeyboardInterrupt` / `SystemExit` 都吃掉，
  然后 `note_summary = {}` 进报告。报告里 `"notes": {}` 既可能是真没笔记，也可能是查询崩了。
- `:2284`：`datetime.fromisoformat(note.get('updated_at', datetime.now().isoformat()))`
  —— 默认值只覆盖 **key 不存在**；`updated_at` 存在但格式损坏时直接抛，
  而 `_notes_to_packets` **没有 try/except**，会把整个 `run()` 打断。
- relevance 分数又是一组魔数：`0.6/0.7/0.8`（`:2193` `:2213` `:2233`）与
  `blocker 0.9 / action 0.8 / task_state 0.75 / conclusion 0.7`（`:2270-2275`），同样零依据、零评测。

---

## 5. Ch10.5 构建自定义 MCP 服务器（全文，`ch10_zh.md:1885-2353`）

标题 **「10.5 构建自定义 MCP 服务器」**（`ch10_zh.md:1885`），10.6 起于 `:2354`。
两个子节：10.5.1 创建第一个 MCP 服务器（`:1889`）、10.5.2 上传到 Smithery（`:2130`）。
案例是 wttr.in 天气查询服务器，从写服务器 → 测试 → 接进 Agent → 打包发布，是全书最完整的一条交付链。

### 5.1 工具 schema 从函数签名推导——机制是好的

注册方式是把普通 Python 函数丢进去（`:1976-1978`）：

```python
weather_server.add_tool(get_weather)          # :1976
weather_server.add_tool(list_supported_cities)
weather_server.add_tool(get_server_info)
```

schema 来自函数签名 + type hint + docstring（`def get_weather(city: str) -> str:` / `"""获取指定城市的当前天气"""`，`:1950-1951`）。
**这是全书最干净的工具定义方式**，比 Ch8.2 手写 15 个 `ToolParameter`（见 §3.6）省事，
也比 Ch3.2「在提示里塞一条示范 JSON」（§1.2(d)）强得多。单一事实来源就是函数本身。

**但这个优点在同一节里被亲手破坏了**——见下。

### 5.2 ⚠ 同一份工具清单被手抄了三遍

| 位置 | 形式 |
|---|---|
| `:1970` | `"tools": ["get_weather", "list_supported_cities", "get_server_info"]` —— `get_server_info()` 里**硬编码的字符串数组** |
| `:1976-1978` | `add_tool(...)` 三行 —— 真正生效的注册 |
| `:2181-2186` | `smithery.yaml` 的 `tools:` 段，又写一遍 name + description |

三份清单**没有任何一致性检查**。加一个工具要改三个地方，漏掉哪个都不会报错：
漏 `:1970` → 服务器自报家门时少一个工具；漏 `:2181` → 平台页面少一个。

→ 对 finaudit-agent：这正是我们「工具/指标口径只能有一个定义处」的反例。
`get_server_info` 那种「让服务自报能力」的接口**必须由注册表反射生成**，
不能手写——手写的自述一旦和实际能力分叉，Agent 会基于错误的能力清单做规划。

### 5.3 ⚠ 正文与产物不一致（第 3 例）：配置说明描述的不是这份 YAML

`:2189-2197` 的「配置说明」逐条解释 `smithery.yaml`，但其中两条与 `:2158-2187` 的 YAML 对不上：

```
:2195  说明写：- `runtime`: 运行时环境（python/node）
:2174  YAML 写：runtime: container            ← 既不是 python 也不是 node

:2196  说明写：- `entrypoint`: 入口文件
       YAML 里根本没有 entrypoint 这个键
```

grep 支撑：`grep -c "entrypoint" ch10_zh.md` → **1**，且唯一那次就是 `:2196` 的说明本身。
**这份说明在解释一个不存在的键。**

反过来，YAML 里实际存在却**完全没被解释**的键有：
`author` `homepage` `license` `categories` `tags` `build`（含 `dockerfile` / `dockerBuildPath`）`startCommand`（含 `type: http`）。
说明覆盖了 7 个键，其中 2 个是错的；YAML 有 13 个顶层键，6 个没提。

这一处比 §3.2 和 §4.1 更能说明问题：那两处是代码没跑过，
这一处是**说明文字和它正上方 10 行的 YAML 是两个版本**，连读一遍都没有。

### 5.4 「测试」在全部失败时也打印成功

测试脚本（`:2002-2033`）的断言长这样：

```python
weather = json.loads(await client.call_tool("get_weather", {"city": "北京"}))
if "error" not in weather:                       # :2018
    print(f"\n北京天气: {weather['temperature']}°C, {weather['condition']}")
# 没有 else，没有 assert
...
print("\n✅ 所有测试完成！")                       # :2026
```

而服务端把异常包成正常返回值（`:1955-1956`）：

```python
except Exception as e:
    return json.dumps({"error": str(e), "city": city}, ensure_ascii=False)
```

于是：**wttr.in 挂掉 / 网络不通 / 字段改名 → 两次查询都返回 `{"error": ...}` →
两个 `if` 都不成立、什么都不打印 → 照样走到 `✅ 所有测试完成！`。**
`:2028` 的 `except` 只 `print("❌ 测试失败")`，不 re-raise 也不 `sys.exit(1)`，
所以**进程退出码恒为 0**，CI 永远是绿的。

这条同时命中我们关心的两条主线：
- 「解析失败如何计入」——这里失败被计成**通过**；
- 「结构化输出失败怎么处理」——错误被塞进成功通道（`{"error": ...}` 与正常结果同为 200 + JSON），
  调用方必须靠**检查有没有 `error` 这个键**来判断成败，而这个约定没写进任何 schema。

→ finaudit-agent 的判定门必须反过来设计：
**失败要有独立通道**（异常/非零退出码/显式 status 字段），
**且「零条结果」与「执行失败」必须是两个不同的判定分支**。
一个在全部失败时仍然打印 ✅ 的测试，比没有测试更危险——它提供了虚假的安全感。

### 5.5 HEALTHCHECK 是个永远不会失败的空操作（`:2272-2273`）

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"
```

这条命令**不接触服务器**，只是启动一个新的 Python 解释器然后立刻退出 0。
无论 MCP 服务是否还活着、端口 8081 是否在监听，健康检查恒为 healthy。
配的 `--retries=3` 和 `--timeout=3s` 因此全无意义。

同一份 Dockerfile 里还有一处空操作（`:2252-2254`）：

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*
```

`apt-get install` **后面没有任何包名**——`apt-get update` 拉了索引，什么也没装，然后把索引删了。

→ 这两处和 §5.4 是同一个病：**存在一个「检查」的形状，但它不可能失败。**
finaudit-agent 的 fail-closed 要求里必须补一条判据：
*每一个门禁在上线前都要被证明「能挡住至少一个真实的坏输入」*，
否则它就是这个 HEALTHCHECK。（这也正是本项目 F-8「跑了门禁但没让它挡住后面的动作」的外部佐证。）

### 5.6 动机讲的是私有数据，例子里零安全措施

10.5.1(1) 列的四条建设动机里，第二条是（`:1898`）：

> 「**访问私有数据**：创建一个安全可控的接口或代理，用于访问内部数据库、API 或其他无法对公网暴露的私有数据源。」

**零命中记录（`NR>=1885 && NR<=2353`）：**

```
认证 0    鉴权 0    授权 0    密钥 0    token 0    权限 0    审计 0    限流 0
```

整节没有一处提到怎么让这个「安全可控的接口」变得安全可控。
而 10.5.2 教的是**把它 Docker 化后发布到公开平台 Smithery**（`:2290`），
`startCommand: type: http`（`:2178-2179`）暴露 HTTP 端口 8081，无任何认证。

→ 对 finaudit-agent 直接相关：D-010 已经把我们限死在公开数据上，
所以这个坑我们暂时踩不到。但如果将来做「本地跑、连内部数据」的演示版本，
**不能照抄这一节的部署形态**——它把「私有数据」当动机、把「无认证公开发布」当结论，中间那一步是空的。

---

## 6. Ch4.3 Plan-and-Solve（全文，`ch04_zh.md:586-863`）

标题 **「4.3 Plan-and-Solve」**（`ch04_zh.md:586`），4.4 Reflection 起于 `:864`。
四个子节：4.3.1 工作原理（`:592`）、4.3.2 规划阶段（`:628`）、4.3.3 执行器与状态管理（`:704`）、4.3.4 运行实例（`:810`）。
**行号更正**：上一轮台账写「未定位」，实际范围是 `:586-863`。

### 6.1 ⚠ 演示的说服力来自答案被预先写进了计划里（反面案例 R-2）

这是本轮**第二严重**的发现，性质和 §1.1 的 `king-man+woman≈queen`（R-1）完全一样。

4.3.4 展示的规划器输出（`:821`，原样）：

```python
["计算周一卖出的苹果数量： 15个",
 "计算周二卖出的苹果数量： 周一数量 × 2 = 15 × 2 = 30个",
 "计算周三卖出的苹果数量： 周二数量 - 5 = 30 - 5 = 25个",
 "计算三天总销量： 周一 + 周二 + 周三 = 15 + 30 + 25 = 70个"]
```

**计划里已经把四步的算式和答案全部算完了。**
（`grep -o "= [0-9]*个"` 于 `:821` → `= 30个` / `= 25个` / `= 70个`。）

于是所谓「执行阶段」（`:830-852`）实际发生的是：
把一段已含 `= 30` 的文本喂给模型，模型回 `30`；把已含 `= 70` 的文本喂进去，模型回 `70`。
**执行器一次也没有「求解」，它在复读计划。**

而正文对此的解读是（`:861`）：

> 「在每一步中，它都将历史结果作为上下文，确保了信息的正确传递
> （例如，步骤2正确地使用了步骤1的结果"15个"，步骤3也正确使用了步骤2的结果"30个"）」

**这个结论推不出来。** 步骤 2 的提示词里同时存在两个「15」：
一个来自 `history`（步骤 1 的结果），一个来自 `plan` 里那句 `15 × 2 = 30个`（`:757` 把完整 plan 也塞了进去）。
无法区分模型用的是哪一个。要证明状态传递有效，必须让**计划不含答案**——
比如计划写成「计算周二销量」而不是「计算周二销量：15 × 2 = 30个」，
再看去掉 `history` 之后是否失败。书里没做这个对照。

→ 这条对 finaudit-agent 的评测设计是直接教训：
**一个不能失败的演示不构成证据。** 我们的 EVAL_CASES 里每一条用例都要能回答
「如果被测机制被摘掉，这条用例会不会挂？」——挂不了的就不是这个机制的证据。
这与 §5.5 那个永远 healthy 的 HEALTHCHECK 是同一个病，只是换到了评测侧。

### 6.2 `ast` 从未被 import（`:693`）

```python
plan = ast.literal_eval(plan_str)     # :693
```

**零命中记录：**

```
$ grep -nE "import ast|from ast" ch04_zh.md      → 无命中（exit 1）
$ grep -n "ast\." ch04_zh.md                     → 只有 :692（注释）与 :693（调用）
$ grep -nE "^import |^from " ch04_zh.md          → os / openai / dotenv / typing / serpapi，无 ast
```

照抄即 `NameError: name 'ast' is not defined`。
这是本轮第三处「书里的代码没跑过」（前两处：§3.2 的 `.run()` 签名、§4.1 的全角逗号）。

### 6.3 但解析失败处理是全书最好的一处（`:689-701`）

要给的公道：这一段是本轮读到的**唯一一处认真对待解析失败**的代码。

```python
try:
    plan_str = response_text.split("```python")[1].split("```")[0].strip()
    plan = ast.literal_eval(plan_str)                      # 不是 eval
    return plan if isinstance(plan, list) else []          # 有类型检查
except (ValueError, SyntaxError, IndexError) as e:         # 窄异常元组，不是裸 except
    print(f"❌ 解析计划时出错: {e}")
    print(f"原始响应: {response_text}")                     # 打印原始响应，可排查
    return []
```

四个优点：用 `ast.literal_eval` 而非 `eval`（不可执行任意代码）、
显式窄异常元组、**把原始响应打出来**（可复盘）、返回值有类型校验。
而且调用方**真的检查了**（`:798`）：`if not plan: print("任务终止"); return`。

对照 §3.4（错误当字符串返回）、§4.5（裸 `except:`）、§5.4（失败照样打 ✅），
这里是全书唯一做对的样本。

**遗留缺口**：`return []` 仍然把「模型输出无法解析」和「不需要计划」压成同一个值。
finaudit-agent 应当区分成 `PlanParseError` 与 `EmptyPlan` 两种状态并分别记入证据链。

### 6.4 最终答案 = 最后一步的输出（`:771-773`）

```python
# 循环结束后，最后一步的响应就是最终答案
final_answer = response_text      # :772，靠循环变量泄漏
return final_answer
```

两个问题：
1. **靠 for 循环变量泄漏取值**。若直接调 `Executor.execute(q, [])`（绕过 `:798` 的守卫），
   `response_text` 未定义 → `UnboundLocalError`。
2. **答案正确性完全押在「规划器把汇总放在最后一步」上**。
   如果模型生成的计划最后一步是「验算」或「说明单位」，最终答案就是那句话，不是数。
   代码里**没有任何一处校验最后一步是不是汇总步**。

→ 对 finaudit-agent：多步计算的最终值**不能取「最后一次 LLM 输出」**。
必须由确定性代码在结构化中间结果上做汇总，
LLM 只负责产出步骤与中间量，最终数字由我们自己算——这样才能进证据链。

### 6.5 引文核对：这次是对的

`:594` 称「Plan-and-Solve Prompting 由 Lei Wang 在 2023 年提出<sup>[2]</sup>」，
参考文献 `:1309`：

> `[2] Wang L, Xu W, Lan Y, et al. Plan-and-solve prompting: Improving zero-shot chain-of-thought reasoning by large language models[J]. arXiv preprint arXiv:2305.04091, 2023.`

作者姓氏、年份与正文自洽，arXiv 号 2305.04091 与我记忆中的该文一致。
**未联网核验，标 UNVERIFIED**，但至少不存在 §1.3 那种正文与文献条目互相矛盾的情况。

---

## 7. Ch10.3 A2A 协议实战（全文，`ch10_zh.md:1108-1654`）

**行号复核结论：台账原写的 `1108–1654` 是对的。** 复核命令与命中：

```
$ grep -n "^## 10\.[345] " ch10_zh.md
1108:## 10.3 A2A 协议实战
1655:## 10.4 ANP 协议实战
1885:## 10.5 构建自定义 MCP 服务器
```

四个子节：10.3.1 协议设计动机（`:1112-1145`）、10.3.2 使用 A2A 协议实战（`:1146-1296`）、
10.3.3 使用 HelloAgents A2A 工具（`:1297-1460`）、10.3.4 在智能体中使用 A2A 工具（`:1461-1654`）。

**交叉核对**：`ha_src/docs/chapter10/第十章 智能体通信协议.md` 与本语料 `ch10_zh.md`
行数相同（均 2446 行）、小节行号一一对齐，全文 diff 差异仅为 CRLF/LF。
下文引用的所有行号在原始源文件里同样成立，**不是转换产物的偏移**。

一句话定性：**10.3 是全书「协议」味道最淡的一节。**
书自己也承认了（`:1148`）：「这里我们只采用<strong>模拟协议思想</strong>的方式」。
问题不在于它是模拟，而在于**正文描述的能力与代码实现的能力差了整整一层**，下面逐条。

### 7.1 ⚠ 正文声称的「身份验证」在代码里一处也没有（正文与产物不一致，第 4 例）

10.3.1 正文（`:1139`）：

> 「A2A 请求生命周期是一个序列，详细说明了请求遵循的四个主要步骤：
> 代理发现、<strong>身份验证</strong>、发送消息 API 和发送消息流 API。」

配图 10.8 的图注还专门写了「客户端、A2A 服务器和<strong>身份验证服务器</strong>之间的交互」（`:1139`）。

**零命中记录（全章范围）：**

```
$ grep -nE "认证|身份验证|签名|token|auth" ch10_zh.md
58        ← 10.1，讲传统方式的痛点，不是 A2A
229       ← 10.2，同上
564,565   ← GITHUB_PERSONAL_ACCESS_TOKEN 环境变量，属 MCP 节
1139      ← 就是上面这句正文
1690,1692 ← 属 10.4 ANP（DID 签名），不属 A2A
2163,2212 ← pyproject 里的 author 字段，误命中
2437      ← 习题：「请设计一个端到端加密方案」

$ grep -nE "鉴权|授权" ch10_zh.md        → 无命中（exit 1）
```

也就是说：**在 `1146–1654` 这 509 行 A2A 实战代码里，与认证相关的命中数为 0。**
四步生命周期里的第二步被正文郑重其事地介绍了一遍，然后整节代码全部是裸 HTTP，
`A2AClient("http://localhost:5000")` 不带任何凭据（`:1359`、`:1438-1440`、`:1484`、`:1557`、`:1565`）。
唯一提到访问控制的地方是习题（`:2437`）——**把没实现的东西留给读者做作业**。

→ 对 finaudit-agent：这正是我们不能犯的错。若 ARCHITECTURE 文档写了「证据链带签名」，
就必须有一条能跑的路径产生签名；否则那句话应当直接删掉，而不是留在文档里等 Phase N 补。

### 7.2 ⚠ 这个协议的「结构化输出」是 `str(dict)` + `eval()`

A2A 节里 Agent 之间传的所有结构化数据，**没有一处走 JSON**，全部是 Python 的 repr 字符串：

```
$ grep -n "return str(" ch10_zh.md
1331:    return str(result)
1389:    return str({"topic": topic, "findings": f"{topic}的研究结果"})
1429:    return str(result)
1624:        return str(result)
1626:        return str({"accepted": False, "message": "无效的提案格式"})
1646:        return str({"status": "negotiating", "proposal": proposal})
1648:        return str({"status": "error", "message": "无效的协商请求"})
```

**7 处命中，全部落在 `1108–1654`（A2A 节）之内。** 全章别处一次也没有。

接收侧用 `eval` 把它变回对象：

```
$ grep -n "eval(" ch10_zh.md
1275:                result = eval(expression)     ← 10.3.2 自定义 Agent
1404:        data = eval(content)                  ← 10.3.3 writer 解析 researcher 的输出
1611:        proposal = eval(proposal_str)         ← 10.3.4 协商提案
```

**全章 3 处 `eval(`，3 处全在 A2A 节。** 裸 `except:` 同理：

```
$ grep -n "except:" ch10_zh.md
1407:    except:
1625:    except:
```

**全章 2 处裸 except，2 处也全在 A2A 节。**

`:1404` 那处是最危险的：`writer` 服务监听 `http://localhost:5001`（`:1433`），
收到的报文里任意一段文本会被 `re.search(r'write\s+(.+)')` 抠出来直接 `eval`。
这不是「解析失败」的问题，是**任何能连上这个端口的人都能在 writer 进程里执行任意 Python**。
书里对此没有任何提示——它给这一段的注释是「尝试解析研究数据」（`:1402`）。

而 `:1272-1275` 那处更值得记，因为它**自称安全**：

```python
# 安全的计算（仅支持基本运算）                      # :1272
allowed_chars = set('0123456789+-*/(). ')          # :1273
if all(c in allowed_chars for c in expression):    # :1274
    result = eval(expression)                      # :1275
```

白名单挡住了字母，确实拦下了 `__import__`。但 `*` 在白名单里，所以 `**` 也在白名单里——**实测**：

```
$ python -c "allowed=set('0123456789+-*/(). ');
             print(all(c in allowed for c in '9**9**9'))"
True
```

`9**9**9` 通过白名单，`eval` 一执行就是把 CPU 与内存钉死的 DoS。
「仅支持基本运算」这句注释是错的：幂运算不在作者列举的四则运算里，却在白名单里。

→ 对 finaudit-agent 的三条硬约束（可直接写进 ARCHITECTURE）：
1. **跨进程 / 跨 Agent 的结构化数据只走 JSON + 显式 schema，永不 `eval`，也不用 `literal_eval` 兜底。**
   Ch4.3 至少用了 `ast.literal_eval`（见 §6.3），A2A 这一节连这层都没有，是全书最差的一处。
2. **schema 是协议的一部分，不是可选项。** 全章 `JSON Schema` 只有 1 次命中（`:484`），
   `schema` 共 4 次命中，全部落在 `:335`、`:456-460`、`:484`——**都在 MCP 节**。
   A2A 与 ANP 两节的 schema 命中数为 **0**。协议章写了两个没有 schema 的「协议」。
3. **解析失败必须是一个上游能看见的状态**，不能被裸 `except` 吞成一条正常返回值（下条与 7.4）。

### 7.3 ⚠ 编辑器永远批准，且它只看到文章的第一行（反面案例 R-3）

`editor` 的 `edit` 技能全文（`:1418-1429`）：

```python
@editor.skill("edit")
def edit_article(text: str) -> str:
    match = re.search(r'edit\s+(.+)', text, re.IGNORECASE)   # :1421
    article = match.group(1).strip() if match else text      # :1422
    result = {
        "article": article + "\n\n[已编辑优化]",               # :1425
        "feedback": "文章质量良好",                            # :1426
        "approved": True                                      # :1427
    }
    return str(result)
```

**两个问题叠在一起，而且互相掩盖。**

**（a）`approved` 是字面量 `True`。** 这个「编辑 / 审核」环节**在结构上不可能不通过**。
它和 §4.2 的 `issues_found`、§5.4 的「全部失败也打 ✅」、§5.5 的空 HEALTHCHECK 是同一个病的第四例：
**流水线里存在一个名字叫「审核」、但没有任何输入能让它输出「不通过」的节点。**
`feedback` 同理是硬编码的「文章质量良好」——无论 `article` 是一篇文章、一条报错，还是空串。

**（b）它拿到的根本不是整篇文章。** `re.search(r'edit\s+(.+)')` 里的 `.` 默认不匹配换行，
而上游 `write_article` 返回的正是带 `\n\n` 的多行 markdown（`:1411`）。

**实测**（复现 `:1443-1454` 的三步串联，脚本在 scratchpad `_verify_a2a.py`）：

```
$ python _verify_a2a.py
article_len = 43
captured_len = 12
dropped_chars = 31
captured_lines = 1 of 5
```

editor 实际收到的只有 `"# AI在医疗领域的应用"` 这一行标题，**正文 31/43 = 72% 的字符被正则丢掉了**。
然后它照样返回 `approved: True`、`feedback: "文章质量良好"`。

**这两个 bug 谁也发现不了对方。** 因为 `approved` 恒为 True，
截断导致的内容丢失不会体现在任何返回字段里；
因为返回值是 `str(dict)` 而不是带 schema 的对象，下游也没有「文章长度」这类字段可校验。
书里给这一段的定位是「协作流程」（`:1442`），正文没有任何一句提到这条流水线的输出被截断过。

→ 对 finaudit-agent 的评测设计（承接 §6.1 R-2 的同一条纪律）：
**任何名为「校验 / 复核 / 审核」的环节，验收标准第一条是「构造一个必须让它失败的输入，看它是否真的失败」。**
构造不出这样的输入，这个环节就不是校验，是装饰。
这条要写进 `EVAL_CASES.md` 的判定门——我们的证据链校验器本身也必须有 negative case。

**多行文本被单行正则截断**这个具体坑对我们也直接相关：
年报 MD&A 段落、审计意见段落全部是多行；任何用 `.+` 从消息里抠 payload 的做法都会静默截断。
我们的 Agent 间传参一律走结构化字段，不从自然语言消息里正则抠。

### 7.4 ⚠ 「Agent 间协商」这一节没有协商

10.3.4（3）标题是「高级用法：Agent 间协商」（`:1586`），
正文说「A2A 协议还支持 Agent 间的协商机制」（`:1588`）。

`agent2` 的 `negotiate` 技能（`:1633-1648`）：

```python
        # 向agent1发送提案                                              # :1644
        proposal = {"task": task, "deadline": deadline}                # :1645
        return str({"status": "negotiating", "proposal": proposal})    # :1646
```

**注释说「向 agent1 发送提案」，下一行直接 return 了。没有发送。**

**零命中记录：**

```
$ awk 'NR>=1586 && NR<=1654' ch10_zh.md | grep -n "A2AClient"
6:from hello_agents.protocols import A2AServer, A2AClient      ← 即 :1591，只有 import
```

`A2AClient` 在这一段被 import 了但**从未实例化、从未调用**。
`agent1` 的 `propose` 技能（`:1601-1626`）写好了接受 / 还价的逻辑，
`agent2` 的 `negotiate` 写好了构造提案的逻辑，**两者之间没有任何一行代码把它们连起来**。
最后 `:1651-1652` 把两个服务各自起在 7000 / 7001 端口，然后代码块就结束了——
没有触发调用，没有输出示例，没有「预期结果」。

顺带两处：
- `:1612` `task = proposal.get("task")` 赋值后从未使用。
- `:1616` `if deadline >= 7`：若 `eval` 出来的 dict 缺 `deadline` 键，`deadline` 是 `None`，
  **实测** `None >= 7` → `TypeError: '>=' not supported between instances of 'NoneType' and 'int'`，
  被 `:1625` 的裸 `except` 捕获，返回 `{"accepted": False, "message": "无效的提案格式"}`。
  也就是**「字段缺失」被报告成「格式无效」**——两种完全不同的失败被压成同一条消息。
  这是 §6.3 结尾那条遗留缺口（`PlanParseError` vs `EmptyPlan`）的又一个实例。

### 7.5 10.3.2 的「测试」由测试代码自己做路由

`:1227-1239` 那段所谓「测试智能体技能」：

```python
for query in test_queries:
    if "信息" in query:      result = calc_agent.skills["info"](query)
    elif "+" in query:       result = calc_agent.skills["add"](query)
    elif "*" in query:       result = calc_agent.skills["multiply"](query)
```

**分发是测试代码里手写的 if-elif 干的，`A2AServer` 一次也没参与。**
`@calculator.skill("add")` 这个装饰器在这段演示里的全部作用，
就是把函数塞进 `calculator.skills` 字典（`:1213` 打印的也正是 `list(calculator.skills.keys())`），
然后测试代码自己按字符串匹配去字典里取。
既没有走网络，也没有走任何协议——**`A2AServer` 在这里退化成了一个 `dict`**。

这解释了为什么 10.3.2 的两个例子都不需要 `A2AServer.run()`：它们根本没有服务端行为。
书在节首（`:1148`）确实预告了「只采用模拟协议思想的方式」，
但**「模拟协议」和「把协议对象当字典用」是两回事**，正文没有区分。

同一个模式在 10.3.4（2）智能客服（`:1500-1583`）里换了个样子：
接待员是真的 LLM（`SimpleAgent` + 两个 `A2ATool`），路由靠工具 description 里的自然语言
（`:1559`「回答技术相关问题」/ `:1567`「回答价格、购买相关问题」）。
两个专家返回的是硬编码模板（`:1523`、`:1536`），
所以这个案例**理论上**可以判分——只要看回答前缀是「技术回答」还是「销售回答」。
但书里三条测试问题（`:1581-1583`）跑完只有 `print`，**没有断言、没有期望值、没有统计**。
一个本来能自动判分的例子，被写成了只能人眼看。

### 7.6 编号瑕疵：两个「（2）」，没有「（1）」

10.3.2 下面两个小标题都编号为 `（2）`：

```
$ awk 'NR>=1146 && NR<=1296' ch10_zh.md | grep -n "^<strong>（"
5:<strong>（2）创建简单的 A2A 智能体</strong>      ← 即 :1150
97:<strong>（2）自定义 A2A 智能体</strong>          ← 即 :1242
```

**这一节没有「（1）」**——上面这条命令扫的就是 10.3.2 的完整范围 `1146–1296`，只有两条命中，都是「（2）」。 我怀疑过是 md 转换丢了，去原始源文件交叉核对，结论是原书就这样：

```
$ grep -n "（2）创建简单的 A2A 智能体\|（2）自定义 A2A 智能体" \
      "ha_src/docs/chapter10/第十章 智能体通信协议.md"
1150:<strong>（2）创建简单的 A2A 智能体</strong>
1242:<strong>（2）自定义 A2A 智能体</strong>

$ sed -n '1150p' "ha_src/docs/chapter10/Chapter10-Agent-Communication-Protocols.md"
**(2) Creating a Simple A2A Agent**
```

中英两个版本都是 `(2)` 开头。**记录为原书编号错误，不是语料问题。**
（对照 §0 表里 `ch03_zh.md:451` 那处 `<strong>` 冒充四级标题——那个是转换瑕疵，这个不是。）

### 7.7 这一节唯一值得借鉴的一条

公道地说，10.3.1 对「中央协调器 vs 点对点」的三条批评
（`:1118-1120`：单点故障 / 性能瓶颈 / 扩展困难）
以及「任务（Task）+ 工件（Artifact）」这组抽象（`:1122`）本身是对的，也是真 A2A 规范的核心。

**「工件」这个概念对 finaudit-agent 直接可用**：
我们的证据链产物（用了哪张表、哪个口径、执行了什么、结果哈希）
应当建模成一个带生命周期状态的 Artifact，而不是散落在日志里的字段。
任务生命周期状态机（创建 / 协商 / 代理 / 执行中 / 完成 / 失败，`:1129`）也可借——
特别是**「失败」必须是一个显式终态**，而这恰恰是本节代码里唯一缺席的状态（见 7.3 / 7.4）。

但**这些都来自正文对官方 A2A 规范的转述**（`:1139` 明说图 10.8「借鉴了官网的流程图」），
**不来自本节的任何一行代码**。要借鉴就去读 A2A 官方规范，不要读这一节的示例。

---

## 8. Ch10.4 ANP 协议实战（全文，`ch10_zh.md:1655-1884`）

**行号复核结论：台账原写的 `1655–1884` 是对的**（复核命令见 §7 开头，10.4 起于 `:1655`，10.5 起于 `:1885`）。
本节共 **230 行**，是 Ch10 三个协议里篇幅最短的一个，
其中 10.4.1 协议目标（`:1661-1695`）占 35 行、
10.4.2 使用 ANP 服务发现（`:1696-1762`）占 67 行、
10.4.3 实战案例（`:1763-1884`）占 122 行。

一句话定性：**10.4 的正文讲的是 ANP 官方规范，代码写的是一个进程内的字典。两者没有交集。**

### 8.1 ⚠ 正文的三个核心机制，代码里一个都没有（正文与产物不一致，第 5 例）

10.4.1 用三段加粗文字介绍了 ANP 的整体流程（`:1688`、`:1690`、`:1692`），并总结于 `:1694`：

> 「该机制的核心是利用 DID 构建了一个<strong>去中心化的信任根基</strong>，
> 并借助标准化的描述协议实现了服务的动态发现。」（`:1694`）

三个机制分别是：
1. 爬取 `.well-known/agent-descriptions` 标准端点建立索引（`:1688`）；
2. **基于 DID 的身份验证**——私钥签名、解析 DID 取公钥、验签（`:1690`）；
3. 标准化接口与数据格式（`:1692`）。

**零命中记录（全章范围）：**

```
$ grep -nE "DID|well-known|私钥|公钥|去中心化|信任" ch10_zh.md
112   ← 10.1.2 协议理念比较，「去中心化服务发现」，是概述不是 ANP 节
1688  ← 10.4.1 正文
1690  ← 10.4.1 正文
1694  ← 10.4.1 正文
2438  ← 习题：「请设计一个信任评估系统」
```

**四条命中里三条是同一段正文，第四条是习题。`1696–1884` 这 189 行 ANP 代码中命中数为 0。**

再看代码到底做了什么：整节**没有任何一次网络调用**。

```
$ awk 'NR>=1655 && NR<=1884' ch10_zh.md \
  | grep -nE "threading|\.run\(|requests|httpx|aiohttp|urllib|socket"
1825:    response = scheduler.run(f"""      ← 唯一命中，而且是 LLM Agent 的 run，不是网络
```

`endpoint` 字段确实被登记了（`:1713`、`:1723`、`:1788`、`:1862`），
但除了 `:1754` 把它原样传给 `network.add_node` 之外，**没有任何一行代码去连接它**。
`http://node0:8000` … `http://node9:8000` 这些主机名根本不可解析——它们不需要解析，因为没人访问。

所以 10.4 演示的「大规模、开放的智能体网络」（`:1659`）实际形态是：
**一个 `ANPDiscovery` 对象，进程内，单机，无认证，无网络。**
去中心化信任根基这一层在代码里完全不存在。

→ 对 finaudit-agent：这是本轮第 5 例「正文声称 ≠ 仓库产物」（前四例见 §3.2 / §5.3 / §5.6 / §7.1）。
五例集中在同一本书里，说明这不是偶发笔误，而是**「先写想要的样子，再补一个能跑的最小例子，最后不回头对齐两者」**这种写法的系统性产物。
我们的 `docs/agent/ARCHITECTURE.md` 与 `PROGRESS.md` 必须有一条硬纪律：
**描述能力的句子，必须能指向一个当前可执行的入口（命令 / 测试 / 函数）；指不出来就标 `NOT-IMPLEMENTED`。**

### 8.2 ⚠ 声称的路由依据（能力、成本）在选择逻辑里从未被读取

10.4.1 把「智能路由」定义为（`:1666`）：

> 「如果多个智能体都能处理同一任务，如何选择最合适的一个（如<strong>根据负载、成本等</strong>）并向其分派任务？」

而实际写出来的选择逻辑只有两处，判据都只有 `load` 一个：

```python
best_service = min(nlp_services, key=lambda s: s.metadata.get("load", 1.0))   # :1740
best        = min(servers,      key=lambda s: s.metadata.get("load", 1.0))   # :1873
```

**`price` 的命中记录：**

```
$ grep -n "price" ch10_zh.md
1714:    metadata={"load": 0.3, "price": 0.01, "version": "1.0.0"}
1724:    metadata={"load": 0.7, "price": 0.02, "version": "1.1.0"}
```

**两处命中都在注册，读取处 0 次。** 正文点名的「成本」维度被登记进 metadata 之后就没人再看它了。

`capabilities` 更严重，因为它是 ANP 最核心的匹配依据：

```
$ grep -n "capabilities" ch10_zh.md
1170, 1259     ← A2A 节的 A2AServer 构造参数
1712, 1722, 1787, 1861   ← ANP 节，全部是 register_service(...) 的入参
```

**6 处命中全是写入，没有一处读取。** 10.4.2（3）那段的注释写着：

```python
# 建立连接（根据能力匹配）                                    # :1756
network.connect_nodes("nlp_agent_1", "nlp_agent_2")        # :1757
```

**注释说「根据能力匹配」，下一行是硬编码的两个 ID。** 没有匹配，没有比较，没有读 `capabilities`。
这与 §7.4 的 `# 向agent1发送提案` 后面直接 `return` 是同一种写法：
**注释描述的是设想中的机制，代码是占位符，而书没有标注它是占位符。**

实际被实现的匹配条件只剩一个：`service_type` 字符串相等（`:1736`、`:1869`）。
「基于语义或功能描述进行查询」（`:1688`）在代码里退化成了 `type == "nlp"`。

### 8.3 ⚠ 同一个操作有三套 API，本节内部自相矛盾

服务发现这一个动作，在 230 行里出现了三种写法：

```
$ grep -nE "discover_service|discover_services|list_all_services" ch10_zh.md
203 :services = anp_tool.run({"action": "discover_services"})     ← 10.1.4 快速体验，字符串 action
1733:from hello_agents.protocols import discover_service          ← 模块级函数，单数
1736:nlp_services = discover_service(discovery, service_type="nlp")
1753:for service in discovery.list_all_services():                ← 实例方法
1797:print(f"✅ 注册了 {len(discovery.list_all_services())} 个计算节点")
1869:    servers = discovery.discover_services(service_type="api")  ← 实例方法，复数
```

`:1736` 的 `discover_service(discovery, service_type=...)`（模块级函数，把 discovery 当第一个参数传进去）
与 `:1869` 的 `discovery.discover_services(service_type=...)`（实例方法，名字是复数）
**语义完全相同，写法完全不同，出现在同一小节相隔 130 行的两个代码块里**。
`:1848` 那个代码块甚至没有 import `discover_service`——因为它改用了方法形式。
**两种写法至多有一种是真实存在的 API**，书里没有说明哪种是规范写法，也没有说另一种是旧接口。

导入路径同样有三套：

```
$ grep -nE "from hello_agents\.tools" ch10_zh.md
184 :from hello_agents.tools import MCPTool, A2ATool, ANPTool          ← 10.1.4 快速体验
1469,1502:from hello_agents.tools import A2ATool                        ← A2A 节
1770:from hello_agents.tools.builtin import ANPTool                     ← ANP 节，多一层 builtin
2330:from hello_agents.tools.builtin.protocol_tools import MCPTool      ← 10.5.2，多两层
2370:from hello_agents.tools import MCPTool, A2ATool, ANPTool           ← 10.6 本章总结
```

**同一个 `ANPTool`，在 `:184` 和 `:2370` 是 `hello_agents.tools`，在 `:1770` 是 `hello_agents.tools.builtin`。**
章首快速体验和章末总结用的是短路径，唯独实战一节用长路径。
`MCPTool` 更是三种路径都出现过。这不是风格问题——**照抄其中一处就会 ImportError**，
而读者无从判断该信哪一处。

→ 对 finaudit-agent：这条属于「文档里的代码没跑过」的又一证据（前三处见 §3.2、§4.1、§6.2）。
我们自己的 `references/` 与 `docs/agent/` 里任何一段可执行片段，
入库前必须至少 import-level 跑通一次；跑不通的片段要么删，要么显式标 `# 伪代码，未执行`。

### 8.4 演示输入是未播种的随机数，所以这一节没有、也不可能有期望输出

10.4.3 的 10 个计算节点，四个属性全部随机生成（`:1789-1794`）：

```python
metadata={
    "load": random.uniform(0.1, 0.9),      # :1790
    "cpu_cores": random.choice([4, 8, 16]),  # :1791
    "memory_gb": random.choice([16, 32, 64]),# :1792
    "gpu": random.choice([True, False])      # :1793
}
```

**零命中记录：**

```
$ grep -n "random.seed\|seed(" ch10_zh.md      → 无命中（exit 1）

$ grep -n "random\." ch10_zh.md
1790:            "load": random.uniform(0.1, 0.9),
1791:            "cpu_cores": random.choice([4, 8, 16]),
1792:            "memory_gb": random.choice([16, 32, 64]),
1793:            "gpu": random.choice([True, False])
1863:        metadata={"load": random.uniform(0.1, 0.9)}
```

**全章 5 处 `random.`，5 处全在 ANP 节。**

没有 `random.seed`，意味着**每次运行的节点画像都不一样，任何人都无法复现书里的任何一次结果**。
与之呼应的是：

```
$ awk 'NR>=1655 && NR<=1884' ch10_zh.md | grep -n "输出"    → 无命中（exit 1）

$ grep -n "^# 输出\|# 输出示例\|# 输出：" ch10_zh.md
467:# 输出示例：                                        ← MCP 节
796:print(response)  # 输出：25 乘以 16 的结果是 400     ← MCP 节
1365:# 输出：                                            ← A2A 节
```

**全章 3 处「期望输出」标注，ANP 节 0 处。**
同一段落里也没有任何断言：

```
$ awk 'NR>=1655 && NR<=1884' ch10_zh.md | grep -nE "assert|期望|预期|正确"   → 无命中（exit 1）
```

于是 10.4.3 的调度演示（`:1820-1842`）实际形态是：
**随机输入 → LLM 自由文本输出 → `print` → 完。**
没有 ground truth，没有断言，没有可复现的输入，因此**这个案例在原理上无法判断调度是否选对了节点**。
它演示的是「LLM 会说出一段像调度理由的话」，不是「调度是对的」。

→ 这条直通 `EVAL_CASES.md`。我们的评测数据集必须满足两条书里全违反的要求：
1. **输入冻结**（固定语料 + SHA-256，不允许随机生成），否则失败无法归因、结论无法复现；
2. **每条用例有可机器判定的期望值**，而不是「打印出来看看」。
   这与 §6.1（R-2）「不能失败的演示不构成证据」是同一条纪律的数据侧表述。

### 8.5 「负载均衡」的负载是自己写给自己看的

`:1866-1882` 那段负载均衡：

```python
def get_best_server():
    servers = discovery.discover_services(service_type="api")   # :1869
    if not servers:
        return None                                             # :1871
    best = min(servers, key=lambda s: s.metadata.get("load", 1.0))
    return best

for i in range(10):
    server = get_best_server()
    print(f"请求 {i+1} -> {server.service_name} (负载: {server.metadata['load']:.2f})")  # :1879
    server.metadata["load"] += 0.1                              # :1882
```

三个问题：

**（a）`load` 从来没有被任何真实服务上报过。** 初值是 `random.uniform(0.1, 0.9)`（`:1863`），
增量是硬编码的 `0.1`（`:1882`），改的是本地注册表里的字典。
`http://api0:8000` 这些 endpoint 全程没被访问。
所谓「模拟请求分配」（`:1876`）分配的是一个不存在的请求给一个不存在的服务器，
再把一个虚构的负载值加上一个魔数。（魔数问题与 §3.3 的四个评分公式同源。）

**（b）那个 `None` 守卫没有保护任何人。** `:1870-1871` 检查了空列表并返回 `None`，
但调用方 `:1878-1879` 拿到 `server` 后立刻解引用 `.service_name`。**实测**（脚本 scratchpad `_verify_anp.py`）：

```
$ python _verify_anp.py
A  :1740 min() on empty -> ValueError: min() arg is an empty sequence
B  :1870 guard then :1879 -> AttributeError: 'NoneType' object has no attribute 'service_name'
```

**这个守卫做的唯一一件事，是把 `ValueError` 换成了三行之后的 `AttributeError`。**
「没有可用服务」这个状态既没有被处理，也没有被上报，只是换了个崩溃点。
对照 `:1740` 那处连守卫都没有——同一节里同一个操作，一处有无效守卫，一处无守卫。

**（c）同一个字段，上一行容忍缺失、下一行必崩。**

```python
best = min(servers, key=lambda s: s.metadata.get("load", 1.0))   # :1873 缺 load 也能跑
print(f"... (负载: {server.metadata['load']:.2f})")               # :1879 缺 load 直接 KeyError
```

`:1740` / `:1741` 是完全一样的一对。`.get(key, default)` 后面紧跟 `[key]`，
说明作者自己也不确定这个字段是否必需——**而这正是「应该有 schema」的信号**。
顺带：默认值 `1.0` 意味着**没有 load 字段的服务被静默当成满负载处理**，
永远排在最后、永远不被选中，而且不会有任何提示。
「字段缺失」再一次被压成了一个正常取值（同 §7.4 的 `deadline`、§3.5 的记忆来源字段）。

### 8.6 拒答缺席的又一处：调度提示词强制必须选一个

10.4.3 的调度提示词（`:1825-1834`）：

```
    要求：
    1. 列出所有可用节点          # :1830
    2. 分析每个节点的特点        # :1831
    3. 选择最合适的节点          # :1832
    4. 说明选择理由              # :1833
```

**四条要求里没有「若无合适节点则说明无法分配」。** 提示词把「选出一个」写成了硬性要求，
于是无论节点池里有没有 GPU 机器，模型都必须挑一台并给出理由。
`assign_task("训练一个大型深度学习模型，需要GPU支持")`（`:1840`）跑在一个
`gpu` 字段随机生成的节点池上，而代码**没有一处检查被选中的节点是否真的 `gpu=True`**。

这是全书「拒答」缺口在 Ch10 的具体落点。
配合 §1.3 的零命中记录（`拒答` / `不可回答` / `无法回答` 全书 16 章总命中 0），
可以下这样一个结论：
**本书从提示词设计到评测设计，都没有为「模型应当说做不到」保留位置。**

→ 对 finaudit-agent，这恰恰是我们最需要的能力。
财务问答里大量问题的正确答案是「该口径在本年报中未披露」「该科目不适用于本行业」。
我们的提示词必须显式给出拒答分支，`EVAL_CASES.md` 必须有一个**不可回答用例类别**，
且判分规则是：**对不可回答问题给出具体数字 = 失败**，而不是「差不多也行」。
这条与 D-003（给不出证据链就算失败）是同一原则的两面。

### 8.7 这一节可借鉴的部分

`ANPDiscovery` 的注册字段设计本身是合理的，只是没被用起来：
`service_id` / `service_name` / `service_type` / `capabilities` / `endpoint` / `metadata`（`:1707-1715`）。
把 `capabilities` 与 `metadata` 分开（前者是能做什么，后者是当前运行状态）这个切分对我们有用——
finaudit-agent 若将来拆出多个执行器（PDF 抽取器 / 指标计算器 / 准则检索器），
「能力声明」与「运行时状态」确实应当分成两个字段族，前者进证据链，后者不进。

10.4.1 的三个挑战（服务发现 / 智能路由 / 动态扩展，`:1665-1667`）也是对的问题分解。
但**要学 ANP 就去读它引的官方入门指南**（`:1678` 给了链接：
`github.com/agent-network-protocol/AgentNetworkProtocol` 的中文入门指南），
本节代码除了字段命名之外没有可迁移的实现。

---

## 9. 附录：全书 16 章 grep 记录（本轮实跑）

**这一节是 §1.3 那句「全书 16 章总命中 0」的证据。** 之前几轮的零命中结论大多只跑在单章语料上，
本轮发现完整的 16 章中文正文就在 scratchpad 的 `ha_src/docs/chapter*/第*.md`（16 个文件），
于是把关键词一次性扫全，把「只在某一章没有」升级成「全书没有」。

**扫描范围与命令前缀**（下文所有命令都在 `<scratchpad>/ha_src/docs/` 下执行）：

```
$ ls chapter*/第*.md | wc -l
16
```

⚠ 说明两点：
- 这 16 个文件是**中文正文**。同目录另有 16 个英文版（`Chapter*.md`），本轮未扫。
- **grep 不等于读过。** 下面涉及 Ch11（D-011 已决定跳过训练与微调）与 Ch12（前几轮已在
  `-part2.md` 读完）的命中，本轮**只记录命中位置，没有重读正文**，也不据此下新的内容判断。

### 9.1 拒答 / 不可回答：全书零命中（**已升级为全书级结论**）

```
$ grep -rn "拒答\|不可回答\|无法回答" chapter*/第*.md
（无输出，exit 1）

拒答     : 0
不可回答 : 0
无法回答 : 0
不知道   : 8    ← 唯一沾边的词，且都是口语用法，不是一个可判分的输出类别
```

**16 章、无一命中。** 这是本轮把 §1.3 与 §8.6 两处观察合并后能下的最强结论：
**这本书从提示词设计（§8.6 的强制选择）到评测设计（Ch12 的四维打分）都没有为
「模型应当说做不到」保留位置。**

→ finaudit-agent 的动作项（写进 `EVAL_CASES.md`）：
设立**不可回答用例类别**，判分规则为「对不可回答问题给出具体数字 = 失败」。
这条与 D-003（给不出证据链即失败）同源。

### 9.2 判分偏差的整套词汇：全书零命中

书里**有** LLM-as-judge 的实践（`LLM Judge` 35 次命中，**全部集中在 Ch12 一章**，
`grep -rni judge` 的文件级分布是 `50 chapter12/第十二章 智能体性能评估.md`，其余 15 章为 0）。
但**判分偏差的方法论词汇一个都没有**：

```
位置偏差 / position bias : 0 / 0
自我偏好 / self-preference : 0 / 0
校准                      : 0
裁判                      : 0
判分                      : 0
标注一致                  : 0
Kappa                     : 0
人类评估                  : 0
黄金（黄金标准）           : 0
```

（`人工评估` 3 次、`评判` 1 次、`打分` 2 次、`评分` 46 次——都是操作性描述，不是偏差控制。）

这与 `-part2.md` 在 Ch12 单章里得到的零命中一致，本轮把它扩成了全书结论：
**判分者与被判者同源的问题，全书 16 章没有任何一处讨论过。**

→ 对我们：`EVAL_CASES.md` 里「判分者与被判者不得同源」这条不能指望从本书借鉴，
只能自己立规则并写进判定门。

### 9.3 数据集冻结与哈希：全书两处命中，均与评测无关

```
$ grep -rn "冻结\|哈希" chapter*/第*.md
chapter11/…:928  ← LoRA「保持原模型参数冻结」，是参数冻结，不是数据集冻结
chapter11/…:944  ← 同上
chapter14/…:1667 ← 「使用查询和最大结果数生成MD5哈希」，是缓存键，不是证据哈希

SHA-256 : 0
sha256  : 0
评测集   : 0
随机种子 : 0
可复现   : 1   ← Ch7 开篇讲「版本迭代」的连贯性，不是评测复现
```

**全书没有一处把数据集冻结或结果哈希当作评测的前提条件。**
这正好解释了 §8.4 观察到的现象：ANP 一节用未播种的 `random` 生成演示输入，
书里没有任何机制会认为这有问题——因为「输入必须可复现」这条要求全书都不存在。

→ 这是 finaudit-agent 相对本书**最清晰的差异点之一**，可以直接写进对外材料：
我们的评测语料冻结 + SHA-256 双校验，是从第一天就作为判定门存在的，不是事后补的。
（机制思想来源见 D-004 的边界说明，本项目独立实现，语料与结论完全隔离。）

### 9.4 证据链词汇的分布

```
引用   : 39     ← 数量不少，但需注意：Ch9 那处「引用」的实现是把检索结果原样回填
                  （见 §4.3「引用只进不出」），不是从答案里抽取
citation : 0
溯源     : 1    ← Ch1 概述性叙述，不是机制
```

`引用` 39 次命中与 §4.3 的结论并不矛盾：**书里频繁谈论「引用」，但唯一给出实现的那一处
（Ch9.6.3）是把检索到的片段原样附在答案后面，没有任何一步是从生成的答案里抽取被实际使用的来源。**
这是本项目最关心的一条，也是我们和本书路线分叉最大的一条。

### 9.5 本轮全书 grep 的一条元结论

上面四组零命中有一个共同点：**缺的都不是功能，是「如何知道它错了」的那一层。**
- 缺拒答类别 → 无法知道模型在编造；
- 缺偏差词汇 → 无法知道判分本身是否可信；
- 缺冻结与哈希 → 无法知道两次结果为什么不同；
- 缺答案侧引用抽取 → 无法知道答案到底用了哪条来源。

而本轮正文里那些具体缺陷——恒为 `True` 的编辑器（§7.3）、不会失败的 HEALTHCHECK（§5.5）、
把答案写进计划的规划器（§6.1）、随机输入无期望输出的调度演示（§8.4）——
全都是这同一层缺失在代码上的投影。

**对 finaudit-agent 的定位含义**：我们的差异化不在「能回答财务问题」，
而在「每个回答都能被独立复核，且错了能被指出来」。本书恰好整体缺这一层，
所以它可以做架构参考，**不能做评测方法论的参考**。


### 9.6 §1–§6 行号抽查与勘误（本轮实跑）

语料目录换到 `ha_md2/` 之后，我拿 §1–§6 正文里的具体引用回到新语料上抽查。
**没有逐条重核，只抽查；下面是原样结果，含我自己写错的部分。**

**结论先说：ch04 / ch08 / ch09 / ch10 抽查项全部命中；偏差集中在 ch03（§1），ch07（§2）一处。**

#### 命中的（抽查项，全对）

| 文件 | 抽查的行号 | 内容 | 结果 |
|---|---|---|---|
| `ch03_zh.md` | 全部小节边界 `:5 / 7 / 186 / 476 / 512 / 666 / 860 / 900 / 904 / 914`，共 1022 行 | 各级标题 | ✅ 全对 |
| `ch03_zh.md` | `:99` / `:139` / `:762` / `:764` / `:918` / `:930` / `:1018` | 0.167 手算 / embeddings 字典 / 上下文窗口 / `2+2` / 事实性幻觉 / 缓解手段 / Bender | ✅ |
| `ch04_zh.md` | `:586` / `:692` / `:693` / `:757` / `:772` / `:798` / `:1309` | 4.3 标题 / 注释 / `ast.literal_eval` / plan 传入 / `final_answer` / `if not plan` / 参考文献[2] | ✅ 全对 |
| `ch07_zh.md` | `:154` / `:203` / `:262` | 7.2 标题 / `self.provider` / 流式 chunk | ✅ |
| `ch08_zh.md` | `:283` / `:312` / `:761` / `:1085` | 8.2 标题 / 工作记忆 / TF-IDF 那句诚实 / 8.3 起点 | ✅ 全对 |
| `ch09_zh.md` | `:2059` / `:2064` / `:2469` | 9.6.3 标题 / **全角逗号 `Dict，`** / 9.6.4 起点 | ✅ 全对 |
| `ch10_zh.md` | `:1885` / `:2178` / `:2272` / `:2354` | 10.5 标题 / `startCommand:` / `HEALTHCHECK` / 10.6 起点 | ✅ 全对 |

`ch09_zh.md:2064` 那处特别值得确认，因为 §4.1 说「第 6 行就是语法错误」：
新语料上确实是 `from typing import Dict， Any, List, Optional`——**全角逗号在，结论成立。**

#### 偏差的（勘误）

| 出处 | 文中写的 | `ha_md2/` 实际 | 偏差 | 内容 |
|---|---|---|---|---|
| §0 备注 | `ch03_zh.md:451` | **`:426`** | −25 | `<strong>3.1.2.5 位置编码</strong>` |
| §1.1 | `ch03_zh.md:136` | **`:133`** | −3 | 「与 `vector('Queen')` 的位置惊人地接近」 |
| §1.1 | `ch03_zh.md:163` | **`:162`** | −1 | `该结果与 'queen' 的相似度: 1.0000` |
| §1.1 | `ch03_zh.md:241` | **`:240`** | −1 | `self.self_attn = MultiHeadAttention() # 待实现` |
| §1.2 | `ch03_zh.md:535` | **`:544`** | +9 | 「优先级顺序为：温度调整→Top-k→Top-p」 |
| §1.2 | `ch03_zh.md:526-530` | 中温档在 **`:531`** | +1…+5 | 温度分档建议 |
| §1.2 | `ch03_zh.md:874` | **`:876`** | +2 | 「使用 API 的方式最简单便捷…」 |
| §1.3 | `ch03_zh.md:1017` | **`:1014`** | −3 | Hoffmann / Chinchilla 那条参考文献 |
| §2.1 | `ch07_zh.md:171` | **`:166`** | −5 | 「直接修改已安装的库源码是一种不被推荐的做法」 |

**这些偏差不改变任何一条结论**——被引的原文我都在新语料上重新找到了，文字一字不差。
`MultiHeadAttention()` 不传参在 `:240`、`:263`、`:264` 三处出现，
`arXiv:2203.07678` / `Borgeaud, E.` 也确实写在 `:1014`（§1.3 的「疑似错引」记录依然成立，
仍标 **UNVERIFIED**，本轮同样没有联网核验）。

**但要如实说：偏差最大的一处差了 25 行，说明 §1 的部分行号当时不是逐条数出来的。**
本文件在 §0 已经因为「提前填表」被降级过一次；这一条是同一类问题的较轻版本——
**引用行号也是一种断言，也需要证据。** 后续几轮的行号一律用 `grep -n` 取，不靠目测。

（`ch10_zh.md` 全部抽查项命中这一点，反过来给 §5 与本轮 §7 / §8 的行号增加了可信度：
它们本来就是用 `grep -n` / `awk NR` 取的。）

---
