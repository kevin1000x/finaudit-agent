# hello-agents 第九章「上下文工程」精读

**对象**：`datawhalechina/hello-agents` 书稿 `docs/chapter9/第九章 上下文工程.md`，**共 2819 行**。
**引用格式**：`ch9:行号`。
**书稿钉的框架版本**：`pip install "hello-agents[all]==0.2.8"`（ch9:8）。
本文所有「书 vs 代码」比对，**基准是 `V0.2.8` tag**，不是 1.0.0。
框架仓库：`jjyaoao/helloagents`，本地 `scratchpad/ha_fw2`，HEAD `5432566`（= `V1.0.0`）。
章节配套代码：书仓 `datawhalechina/hello-agents` @ `45dd84e`，`code/chapter9/`。

**前置事实（本轮第一条结论，先摆出来因为它决定了整章怎么读）**：

```
$ git -C ha_fw2 ls-tree -r --name-only V0.2.8 -- hello_agents/context/
hello_agents/context/__init__.py
hello_agents/context/builder.py

$ git -C ha_fw2 ls-tree -r --name-only V1.0.0 -- hello_agents/context/
hello_agents/context/__init__.py
hello_agents/context/builder.py
hello_agents/context/history.py
hello_agents/context/token_counter.py
hello_agents/context/truncator.py
```

`references/hello-agents-framework-tools.md` §9 里读出的三条硬问题，
有两条（`truncator.py` 丢弃 `full_output_path`、`history.py:144` 压缩后原文不落盘）
出自 **1.0.0 才存在的文件**——**书稿第九章根本没有对应章节**，
不是「书讲对了实现没跟上」，而是**书没讲**（详见 §10 差异表 D-1/D-2）。
第三条（中文 split 相关性恒 0）**书稿自己就是这么写的**（ch9:396-398），属于**书本身讲错**。

---

## 覆盖表

| 小节 | 行号范围 | 读到什么程度 |
|---|---|---|
| 章首导言 | 1-24 | **全文** |
| 9.1 什么是上下文工程 | 25-45 | **全文** |
| 9.2 为什么上下文工程重要（含 9.2.1-9.2.3） | 46-124 | **全文** |
| 9.3.1 设计动机与目标 | 129-146 | **全文** |
| 9.3.2 核心数据结构 | 147-216 | **全文** |
| 9.3.3 GSSC 流水线详解 | 217-581 | **全文** |
| 9.3.4 完整使用示例 | 582-771 | **全文** |
| 9.3.5 最佳实践与优化建议 | 772-787 | **全文** |
| 9.4.1 NoteTool 设计理念 | 792-880 | **全文** |
| 9.4.2 存储格式详解 | 881-950 | **全文** |
| 9.4.3 核心操作详解 | 951-1315 | **全文** |
| 9.4.4 与 ContextBuilder 的深度集成 | 1316-1553 | **全文** |
| 9.4.5 最佳实践 | 1554-1584 | **全文** |
| 9.5.1 TerminalTool 设计理念与安全机制 | 1591-1730 | **全文** |
| 9.5.2 核心功能详解 | 1731-1842 | **全文** |
| 9.5.3 典型使用模式 | 1843-1952 | **全文** |
| 9.5.4 与其他工具的协同 | 1953-2029 | **全文** |
| 9.6.1 场景设定与需求分析 | 2039-2048 | **全文** |
| 9.6.2 系统架构设计 | 2049-2058 | **全文** |
| 9.6.3 核心实现 | 2059-2468 | **本轮不重读** —— 见 `hello-agents-deep-read-part4.md` §4 |
| 9.6.4 完整使用示例 | 2469-2739 | **全文** |
| 9.6.5 运行效果分析 | 2740-2747 | **全文** |
| 9.7 本章总结 | 2748-2775 | **全文** |
| 习题 | 2776-2813 | **全文** |
| 参考文献 | 2814-2819 | **全文** |

---

## 1. 章首导言 + 9.1 什么是上下文工程（ch9:1-45）

导言把本章的三个新增件点名了（ch9:13-15）：
`ContextBuilder`（`hello_agents/context/builder.py`）、
`NoteTool`（`tools/builtin/note_tool.py`）、`TerminalTool`（`tools/builtin/terminal_tool.py`）。
**注意这个清单里没有 truncator / history / token_counter**——与前置事实一致。

9.1 的立论是把上下文工程定义成提示工程的自然演进（ch9:40）：
提示工程管「怎么写指令」，上下文工程管「**在推理阶段策划与维护最优的信息集合（tokens）**」，
范围覆盖系统指令、工具、MCP、外部数据、消息历史（ch9:42）。
落到一句可操作的话（ch9:44）：**从持续扩张的「候选信息宇宙」中甄别哪些内容应当进入有限的上下文窗口。**

这一节是纯观点，无代码。对本项目的价值在于它给了一个**取舍框架**，
但它的取舍标准全部是「效用 / 信号密度」，**没有一个字涉及可核验性**——
这是整章的基调，后面每一节都会重复出现。

## 2. 9.2 为什么上下文工程重要（ch9:46-124）

### 2.1 上下文腐蚀（ch9:48-56）

核心概念 **context rot**（ch9:48）：随上下文 token 增加，模型**从上下文中准确回忆信息的能力反而下降**。
给了两条机制解释：
- Transformer 的 \(n^2\) 两两注意力随长度被「拉薄」（ch9:52）；
- 训练数据里短序列远多于长序列，模型对「全上下文依赖」的经验与专用参数都少（ch9:52）。
- 位置编码插值能外推长度，但**牺牲对 token 位置的精确理解**（ch9:54）。

结论是「性能梯度而非悬崖」（ch9:54）。
**这一条对 finaudit 是直接可用的反面论据**：如果把整份年报 PDF 文本塞进上下文让模型「自己找」，
即使窗口装得下，召回精度也是梯度下降的——这正好支持 D-017（自建封闭解析器）
与 ARCHITECTURE §8.1-8.5 的「先结构化抽取再进上下文」，而不是「长窗口硬塞」。

### 2.2 有效上下文的解剖学（ch9:58-82）

目标句（ch9:60）：**用尽可能少、但高信号密度的 tokens，最大化获得期望结果的概率。**

三个组件：
- **系统提示**（ch9:62-65）：两极误区是「过度硬编码 if-else」与「过于空泛」。
  建议分区组织（`<background_information>` / `<instructions>` / 工具指引 / 输出描述），
  追求「**能完整勾勒期望行为的最小必要信息集**」，并明确「**最小不等于最短**」（ch9:65）。
- **工具**（ch9:67-71）：工具是「智能体与信息/行动空间的**契约**」（ch9:67）。
  要求职责单一、低重叠、对错误鲁棒、入参无歧义。
  失败模式叫「臃肿工具集」，有一句很好的判据（ch9:71）：
  **「如果人类工程师都说不准用哪个工具，别指望智能体做得更好」**，
  并提出「最小可行工具集（MVTS）」。
- **示例（Few-shot）**（ch9:73）：要「多样且典型」，不要罗列所有边界条件。

### 2.3 上下文检索与智能体式搜索（ch9:83-97）——**本章与本项目最相关的一节**

ch9:87 是全章唯一一处正面讲「**引用而非全文**」的地方：

> 工程实践正在从「推理前一次性检索（embedding 检索）」逐步过渡到「**及时（Just-in-time, JIT）上下文**」。
> 后者不再预先加载所有相关数据，而是维护**轻量化引用**（文件路径、存储查询、URL 等），
> 在运行时通过工具动态加载所需数据。

注意这正是 `truncator.py` 的 `{preview, full_output_path}` 形状的**理论出处**——
形状对，是因为书里（或者说书抄的那篇 Anthropic 工程博客）讲对了这个模式。
但**书稿并没有把它写成 ContextBuilder 的一部分**，
`full_output_path` 这个字段在 2819 行里 **0 命中**：

```
$ grep -c 'full_output_path' 第九章\ 上下文工程.md
0
$ grep -c 'truncator\|Truncator' 第九章\ 上下文工程.md
0
```

ch9:89 补了一条容易被忽略的观察：**引用的元数据本身就是信息**——
目录层级、命名约定、时间戳隐含地传达「目的与时效」，
例子是 `tests/test_utils.py` 与 `src/core/test_utils.py` 语义暗示不同。

ch9:91 提出**渐进式披露（progressive disclosure）**：每一步交互产生新上下文，
反过来指导下一步；只在工作记忆里保留当前必要子集，用「记笔记」做持久化补充。

ch9:93 诚实地写了代价：运行时探索**比预计算检索慢**，且需要「有主见的工程设计」，
否则智能体会误用工具、追死胡同、错过关键信息，**造成上下文浪费**。

ch9:95 给的解法是**混合策略**：前置加载少量高价值上下文保速度，再允许按需探索；
工程手段是预放 README/约定说明 + 提供 `glob`/`grep` 原语。

### 2.4 面向长时程任务的三种手段（ch9:98-124）

书给了三选一的经验法则（ch9:117-121），三种手段是：

| 手段 | 定义（行号） | 适用 |
|---|---|---|
| 压缩整合 Compaction | ch9:103 接近上限时**高保真总结**，用摘要**重启新窗口** | 需要长对话连续性 |
| 结构化笔记 Structured note-taking | ch9:108 定频把关键信息写入**上下文外的持久化存储**，后续**按需拉回** | 有里程碑的迭代开发/研究 |
| 子代理架构 Sub-agent | ch9:113 子代理在干净窗口里深挖，**只回传凝练摘要（1000-2000 tokens）** | 复杂研究/并行探索 |

**压缩整合的三条实践细节（ch9:104-105），是本章离「可逆性」最近的地方**：
- 保留「架构性决策、未解决缺陷、实现细节」，丢弃「重复的工具输出与噪声」；
- 新窗口携带 **压缩摘要 + 最近少量高相关工件**（如「最近访问的若干文件」）；
- 调参顺序：**先优化召回（不遗漏），再优化精确度（剔冗余）**；
- 「一种安全的**轻触式**压缩是对『深历史中的工具调用与结果』进行清理」。

**但它止步于此。** 书说了「丢弃噪声」，**没有说被丢弃的东西去了哪里、还能不能找回**。
全章对可逆性的表述是零：

```
$ for p in 可逆 不可逆 还原 恢复原文 原文 回滚; do printf '%-8s %s\n' $p $(grep -c -- $p 第九章\ 上下文工程.md); done
可逆     0
不可逆   0
还原     0
恢复原文 0
原文     0
回滚     0
```

「结构化笔记」那一条（ch9:108）**在概念上**是有落盘的：「写入上下文外的持久化存储……按需拉回」。
但它的定位是「智能体主动记的要点」，不是「被压缩掉的原文的存档」——
**主动摘要与原文归档是两件事，书把前者写了，后者没有。**
这一区分就是 `rules/pitfalls.md` 第 11 条（不可逆压缩）在书里找不到对应物的原因。

## 3. 9.3.1-9.3.2 ContextBuilder 设计动机与数据结构（ch9:129-216）

### 3.1 四条设计目标（ch9:133-145）—— 第 4 条是本章对本项目最刺眼的一句

1. **统一入口**：把 GSSC（Gather-Select-Structure-Compress）抽象成可复用流水线（ch9:133）。
2. **稳定形态**：输出固定骨架，便于调试、A/B 测试与评估（ch9:135）。六个分区：
   `[Role & Policies]` / `[Task]` / `[State]` / `[Evidence]` / `[Context]` / `[Output]`。
3. **预算守护**：token 预算内保留高价值信息，超限时「兜底压缩」（ch9:143）。
4. **最小规则**（ch9:145）——原文照抄：

   > **不引入来源/优先级等分类维度，避免复杂度增长。**
   > 实践表明，基于相关性和新近性的简单评分机制，在大多数场景下已经足够有效。

**这一条是本章与 D-003 的正面冲突点。**
书把「来源（provenance）」当成一个**可以为了降复杂度而砍掉的维度**；
本项目把它当成**第一类产物**。两边不是程度差异，是方向相反。
后面 §4.3 的 `_structure` 会看到后果：`[Evidence]` 分区里只有 `packet.content` 拼接，
**没有任何一个字段记录这段内容来自哪个库、哪次检索、哪个 chunk。**

### 3.2 ContextPacket（ch9:159-181）

字段只有五个：`content` / `timestamp` / `token_count` / `relevance_score`（默认 0.5）/ `metadata`。
**没有 source / id / uri / hash。**
`metadata` 是自由 dict，理论上能塞来源，但**流水线的任何一步都不把它当来源用**——
`_structure`（ch9:458-466）只读 `metadata["type"]` 做分区归类。
即「metadata 能装证据指针，但下游不消费」——
这正是 `ARCHITECTURE §8.5`（证据指针必须被下游强制消费）要避免的形态。

`__post_init__` 把 `relevance_score` clamp 到 [0,1]（ch9:180）。

### 3.3 ContextConfig（ch9:185-215）

默认值：`max_tokens=3000`、`reserve_ratio=0.2`、`min_relevance=0.1`、
`enable_compression=True`、`recency_weight=0.3`、`relevance_weight=0.7`。
`__post_init__` 有三条 assert（ch9:209-214），其中一条要求两个权重之和为 1.0。
**记住 `min_relevance` 默认 0.1**——它在 §4.2 会和相关性算法合起来变成一个硬故障。

---

## 4. 9.3.3 GSSC 流水线详解（ch9:217-581）—— 本章的技术主体

### 4.1 Gather（ch9:221-311）

五个来源依次入包：系统指令（`relevance_score=1.0` 固定）、MemoryTool 检索、
RAGTool 检索、对话历史（最近 5 条，每条一个包，基础分 0.6）、自定义包。

**失败处理是本章第一个「降级不留痕」实例**（ch9:258-269 记忆支、272-284 RAG 支）：

```python
try:
    memory_results = self.memory_tool.run({...})
    ...
except Exception as e:
    print(f"[WARNING] 记忆检索失败: {e}")     # ch9:269
```

RAG 那一支同构（ch9:284）。书把这个写成优点（ch9:308）：

> **容错机制**：每个外部数据源的调用都被 try-except 包裹，确保单个源的失败不会影响整体流程。

**代价是没有被记录到产物里**：`_gather` 返回 `List[ContextPacket]`，
**没有任何字段说「RAG 这次挂了」**；`build()` 最终返回一个 `str`，
**下游拿到的上下文与「RAG 正常但零命中」在形态上完全无法区分。**
`print` 到 stdout 不是留痕——它不进产物、不进返回值、不可被断言。

```
$ grep -c '留痕' 第九章\ 上下文工程.md   → 0
$ grep -c '审计' 第九章\ 上下文工程.md   → 0
$ grep -c '降级' 第九章\ 上下文工程.md   → 1   （命中在 ch9:669，讲 int64→int32 内存优化，与本主题无关）
```

对本项目的意义很直接：**这正是 D-018（fail-closed 在读入边界）要拦的形态。**
书选的是 fail-open + print；本项目在读入边界必须 fail-closed，
或至少把「哪一路证据源失败了」写进证据链本身。

### 4.2 Select（ch9:317-429）—— **本章最严重的技术问题**

打分是 `combined = relevance_weight × relevance + recency_weight × recency`（ch9:357-360），
但过滤用的是**裸相关性**而不是复合分（ch9:363-364）：

```python
if packet.relevance_score >= self.config.min_relevance:
    scored_packets.append((combined_score, packet))
```

**新近性无法把一条相关性低的信息救回来**，权重设计在过滤这一步就失效了。

相关性算法（ch9:395-407），原文：

```python
# 分词(简单实现,可以使用更复杂的分词器)
content_words = set(content.lower().split())
query_words = set(query.lower().split())
if not query_words:
    return 0.0
# Jaccard 相似度
intersection = content_words & query_words
union = content_words | query_words
return len(intersection) / len(union) if union else 0.0
```

**中文恒为 0**：无空格的中文串 `.split()` 得到长度为 1 的列表，与查询词集合交集为空。
与 `rules/pitfalls.md` 第 8 条完全同源。
书的注释只说「简单实现,可以使用更复杂的分词器」（ch9:396）和
「生产环境中,可以替换为向量相似度计算」（ch9:387），
**全章没有一句提到中文会失效**：

```
$ grep -c '中文分词' 第九章\ 上下文工程.md  → 0
$ grep -n '中文' 第九章\ 上下文工程.md
572:    # 简单估算:中文 1 字符 ≈ 1 token,英文 1 单词 ≈ 1.3 tokens
```

**全章唯一一处提到「中文」的是 token 计数器**（ch9:572）——
也就是说**同一个类里 `_count_tokens` 专门处理了中文，`_calculate_relevance` 没有**，
两者相隔约 180 行。这不是「没想到」，是**想到了一半**。
因此本条判为「**书本身就讲错了**」，不是「书讲对了实现没跟上」。

**更狠的一点：书里的 Jaccard 比它自己钉的 0.2.8 代码还差。**
`V0.2.8:hello_agents/context/builder.py:210-217` 用的是**包含度**而非 Jaccard：

```python
overlap = len(query_tokens & content_tokens)
packet.relevance_score = overlap / len(query_tokens)      # 分母是 query，不是 union
```

实测两个公式（`min_relevance` 取默认 0.1）：

| 用例 | 书稿 Jaccard `∩/∪` | V0.2.8 代码 包含度 `∩/query` |
|---|---|---|
| 中文短句 | **0.0000** | **0.0000** |
| 英文短句 | 0.5000 | 0.7143 |
| 英文长文档（300 词噪声 + 查询词全命中） | **0.0161 → 被 min_relevance=0.1 滤掉** | 0.7143 → 保留 |

**结论：书稿版本在长英文证据上同样失效，不只是中文。**
分母取 union 意味着「内容越长分数越低」，
而 RAG 检索回来的证据块天然比查询长一到两个数量级——
**书稿的公式与它自己的使用场景（`[Evidence]` 分区来自 RAG）是互斥的。**

预算填充（ch9:379-380）用的是 `break`：

```python
for score, packet in scored_packets:
    if current_tokens + packet.token_count <= available_tokens:
        selected.append(packet); current_tokens += packet.token_count
    else:
        break        # ch9:379
```

**一个大包会把它后面所有小包全部挡掉。**
0.2.8 代码这里是 `continue`（builder.py:250-252），跳过装不下的、继续尝试后面的小包。
**又一处书比代码差。**

### 4.3 Structure（ch9:442-490）

按 `metadata["type"]` 三分类：`system_instruction` → `[Role & Policies]`；
`rag_result` / `knowledge` → `[Evidence]`；其余 → `[Context]`（ch9:458-466）。

**三个问题：**

1. **`[State]` 分区没被实现。** 9.3.1 明确列了六个分区含 `[State]`（ch9:135），
   `_structure` 只产出五个（Role / Task / Evidence / Context / Output）。
   对照 `V0.2.8` 代码，`[State]` 是**实现了**的（builder.py:288-293，`type == "task_state"`）。
   **书漏了自己承诺的分区。**

2. **`[Evidence]` 只是内容拼接**（ch9:479）：
   ```python
   sections.append("[Evidence]\n" + "\n---\n".join(evidence))
   ```
   `\n---\n` 是唯一分隔符。**没有编号、没有来源标签、没有可回指的 id。**
   模型即使想说「依据第 2 条证据」，上下文里也不存在「第 2 条」这个可指称对象。
   这是 ch9:145「不引入来源维度」的直接后果。

3. **`[Output]` 被书稿降级了。** 书里是一行（ch9:486）：
   ```python
   sections.append("[Output]\n请基于以上信息,提供准确、有据的回答。")
   ```
   而 `V0.2.8` 代码是四段式（builder.py:308-314），**第 2 条明确要求列出来源**：
   ```
   1. 结论（简洁明确）
   2. 依据（列出支撑证据及来源）
   3. 风险与假设（如有）
   4. 下一步行动建议（如适用）
   ```
   **代码里那句「列出支撑证据及来源」是整个 ContextBuilder 唯一一处要求引用来源的地方，
   书稿把它删成了「有据的回答」四个字。**
   本轮最意外的一条：**这次是代码比书讲得对。**

### 4.4 Compress（ch9:497-577）—— 不可逆，且丢弃无痕

```python
sections = context.split("\n\n")
for section in sections:
    if current_total + section_tokens <= max_tokens:
        compressed_sections.append(section); current_total += section_tokens
    else:
        remaining_tokens = max_tokens - current_total
        if remaining_tokens > 50:
            truncated = self._truncate_text(section, remaining_tokens)
            compressed_sections.append(truncated + "\n[... 内容已压缩 ...]")
        break                                    # ch9:538
```

四个问题，按严重程度排：

1. **被丢弃的内容不写任何地方。** `_truncate_text` 就是 `return text[:max_chars]`（ch9:561）。
   尾部直接消失，**没有路径、没有归档、没有 id。**
   `truncator.py` 至少有 `{preview, full_output_path}` 这个形状，**书稿连形状都没有。**

2. **`remaining_tokens <= 50` 时连标记都没有。** 标记 `[... 内容已压缩 ...]` 只在
   `> 50` 分支里拼上（ch9:537）。走 `else` 且剩余不足 50 token 时直接 `break`，
   **完全静默地丢掉整个分区及其后所有分区。**

3. **`break` 而非 `continue`：第一个装不下的分区之后所有分区一并丢弃。**
   由于分区顺序是 Role → Task → Evidence → Context → **Output**，
   **`[Output]` 永远是第一个被牺牲的**——上下文越紧张，输出格式约束越先消失。

4. **标记文本不可机读。** `[... 内容已压缩 ...]` 是塞进正文的中文字符串，
   不是返回值里的结构化字段。调用方不做字符串匹配就无法知道「这次压缩了」。

`_count_tokens`（ch9:563-577）是手写估算：
```python
chinese_chars = sum(1 for ch in text if '一' <= ch <= '鿿')
english_words = len([w for w in text.split() if w])
return int(chinese_chars + english_words * 1.3)
```
中英混排会**重复计数**（中文 run 既算进 `chinese_chars`，整段又算作一个 english word）。
实测 `"净利润 net profit 12.3"` → 8（3 个中文字 + 4 词 × 1.3）。
对照 `V0.2.8` 代码：用的是 **`tiktoken.get_encoding("cl100k_base")`**，
异常时才降级到 `len(text)//4`（builder.py:345-353）——**又一处代码比书严谨**，
但那个 `except Exception` 降级同样**只 return，不记录**（第三个「降级不留痕」实例）。

---

## 5. 9.3.4 完整使用示例 + 9.3.5 最佳实践（ch9:582-787）

### 5.1 示例输出里的 `[Evidence]`（ch9:655-687）—— 全章唯一一次展示证据长什么样

书稿贴了一段「运行效果」输出。`[Evidence]` 分区实际长这样（ch9:663-670）：

```
[Evidence]
Pandas内存优化的核心策略包括:
1. 使用合适的数据类型(如category代替object)
...
---
数据类型优化可以显著减少内存占用。例如,将int64降级为int32可以节省50%的内存。
```

**两段证据之间只有一行 `---`。没有编号、没有文档名、没有 chunk id、没有分数。**
这就是 §3.1 那条「不引入来源维度」（ch9:145）在产物上的样子。
下面 `[Context]` 里的记忆条目倒是有个 `记忆: ` 前缀（ch9:676-677），
但那是**类型标签**，不是来源标识——两条记忆都叫「记忆:」，无法区分是哪一条。

### 5.2 两个关键函数在书里**只被调用、从未被定义**

```
$ grep -n '_parse_memory_results\|_parse_rag_results' 第九章\ 上下文工程.md
266:            memory_packets = self._parse_memory_results(memory_results, user_query)
281:            rag_packets = self._parse_rag_results(rag_results, user_query)

$ grep -c '_parse_memory_results\|_parse_rag_results' <V0.2.8 builder.py>
0
```

**这两个函数是把「工具返回的原始结果」变成「带 relevance_score 的 ContextPacket」的地方，
也就是唯一有机会把来源信息写进 packet 的地方——而它们在书里没有函数体，在 0.2.8 代码里根本不存在。**
0.2.8 的做法更粗：把 RAG 返回的**整个字符串**塞进一个 packet（builder.py:172-181），
`metadata={"type": "knowledge_base"}`，连拆分都没有。

顺带记一条 0.2.8 代码里的失败检测方式（builder.py:177）：

```python
if rag_results and "未找到" not in rag_results and "错误" not in rag_results:
```

**用中文自然语言子串匹配来判断检索是否成功。** 检索结果里正常出现「未找到」二字就会被当作失败。
这与 D-018 想在读入边界拦的东西是同一类：**没有结构化的成败信号，只有对人类可读文本的猜测。**

### 5.3 书稿自己的示例输出，跑不出来

书稿在 ch9:602 把配置写成 `min_relevance=0.2`，查询是中文的
`"如何优化Pandas的内存占用?"`（ch9:637）。按 `V0.2.8` 的 `_select` 实算：

```
query_tokens = {'如何优化pandas的内存占用?'}   # len = 1，中文无空格

packet                  relevance   min_relevance=0.2 通过?
instructions(P0)        0.0000      固定纳入(不过滤)
knowledge_base(RAG)     0.0000      否 -> 丢弃
related_memory          0.0000      否 -> 丢弃
history(P3)             0.0000      否 -> 丢弃
```

**按 0.2.8 代码，这个示例的真实输出只会剩 `[Role & Policies]` + `[Task]` + `[Output]` 三段，
`[Evidence]` 与 `[Context]` 都是空的。书里贴的那段输出复现不出来。**

按书稿自己的伪代码路径，结果略有不同但同样不成立：
对话历史包在 Gather 阶段被硬编码为 `relevance_score=0.6`（ch9:294），
而 `_select` 只在 `packet.relevance_score == 0.5` 时才重算相关性（ch9:349-351），
所以历史包带着 0.6 蒙混过关，`[Context]` 能出来；
但 `[Evidence]` 依赖未定义的 `_parse_rag_results`，**无法判定**——
也就是说**书稿示例中 `[Evidence]` 那一段的可复现性是不可验证的**，
因为产生它的函数没有函数体。

这里有一条对本项目直接可用的教训，属于**该刻意不借**那一栏：
**用「示例输出」当验收证据是不成立的**，除非示例是跑出来的、且跑法可复现。
`PROJECT_SPEC.md §完成定义` 要求的「完成必须有证据」在这里得到一个反面样本。

### 5.4 与 Agent 集成（ch9:694-770）里的两处

`ContextAwareAgent.run()`（ch9:719-760）：

1. **任务被送了两遍**（ch9:730-733）：
   ```python
   messages = [
       {"role": "system", "content": optimized_context},   # 里面已经有 [Task]\n{user_input}
       {"role": "user",   "content": user_input}           # 又送一遍
   ]
   ```
   与 9.2.2「信息充分但紧致」自相矛盾，虽然量很小。

2. **又一次不可逆截断，且被叫作「摘要」**（ch9:747-753）：
   ```python
   self.memory_tool.run({
       "action": "add",
       "content": f"Q: {user_input}\nA: {response[:200]}...",  # 摘要
       ...
   })
   ```
   `response[:200]` 是**前 200 字符**，注释却写「摘要」。
   完整 response 不写任何地方，**没有指针指回去**。
   这是本章第三处「截断即丢失」（前两处是 `_truncate_text`、`_compress` 的 break 分支）。

### 5.5 9.3.5 最佳实践五条（ch9:774-786）

原文五条：动态调整 token 预算 / 相关性计算优化 / 缓存机制 / 监控与日志 / A/B 测试。

两条值得单独记：

- 第 2 条（ch9:778）：「在生产环境中，将简单的关键词重叠替换为向量相似度计算」。
  **书知道关键词重叠不够用，但把它归因为「质量不够高」，而不是「在中文上恒为 0」。**
  定性错了：这不是精度问题，是**功能性失效**。
- 第 4 条（ch9:782）：「记录每次上下文构建的统计信息(**选中信息数量、token 使用率**等)」。
  **注意它记的是「选中了什么」的计数，不是「丢弃了什么」的清单。**
  这是全章离「留痕」最近的一句，但它记的是聚合指标，不是可回溯的丢弃记录。
  对 D-003 无用：统计量不能拿来复核某一条答案。

---

## 6. 9.4 NoteTool 结构化笔记（ch9:788-1584）

这一节是 9.2.3「结构化笔记」那条方法论的落地件，也是全章**唯一真正把东西写到上下文之外**的组件。

### 6.1 定位与格式（9.4.1-9.4.2，ch9:790-950）

定位（ch9:798）：MemoryTool 管**对话式记忆**，NoteTool 管**项目式任务**的长期追踪。
六种 `note_type`：`task_state` / `conclusion` / `blocker` / `action` / `reference` / `general`（ch9:970）。

存储形态是**每篇一个 `.md` 文件 + 一个 `notes_index.json`**（ch9:889-941）。
YAML 前置元数据的字段（ch9:891-897）：

```yaml
id: note_20250119_153000_0
title: 项目进展 - 第一阶段
type: task_state
tags: [refactoring, phase1, backend]
created_at: 2025-01-19T15:30:00
updated_at: 2025-01-19T15:30:00
```

**六个字段里没有 `source` / `derived_from` / `hash`。**
一篇笔记是一条**无出处的断言**：它不记录自己是从哪次对话、哪个工具输出、哪份文档来的。
在 finaudit 语境下这等于「结论不带底稿」。

**`notes_index.json` 这个形状本身是对的**（ch9:933-941）：
索引里放 `id / title / type / tags / created_at / updated_at / file_path`，
**正文留在文件里，索引只放指针**。这正是 D-016 映射表 schema 想要的分层
（轻量可查询的索引 + 重量级原文按 id 取回），也正是 ch9:87「轻量化引用」在本章唯一一次落到实处。

**但书紧接着给它安了一个它做不到的能力**（ch9:949）：

> **完整性校验**：可以检测文件缺失或损坏

索引里**只有 `file_path`，没有任何摘要/长度/校验和**。
`file_path` 能检测「缺失」（路径不存在），**检测不了「损坏」**——
文件被改一个字符、被截断一半，索引完全无感。
核对 `V0.2.8` 真实实现：

```
$ grep -c 'hashlib\|sha256\|md5\|checksum\|version' V0.2.8:hello_agents/tools/builtin/note_tool.py
0
```

**书和代码都没有校验和。这句「完整性校验」是空头支票。**
`校验` 二字在全章只出现 1 次，就是这一处：

```
$ grep -n '校验' 第九章\ 上下文工程.md
949:- <strong>完整性校验</strong>：可以检测文件缺失或损坏
```

对本项目：**D-012（冻结 + SHA-256 双校验）在这里找到了一个精确的反例**——
「有索引」不等于「可校验」，差的就是那一列摘要。

### 6.2 七个操作（9.4.3，ch9:951-1315）

`create` / `read` / `update` / `search` / `list` / `summary` / `delete`。三处要记：

**（a）`update` 就地覆盖，旧内容不留**（ch9:1135-1140）。
`updated_at` 被刷新，但**上一版内容直接被写掉**，没有版本、没有 diff、没有归档。
书在 ch9:803 说 NoteTool「版本友好：纯文本格式，天然支持 Git 等版本控制系统」——
**注意这是把版本能力外包给了使用者的 git，工具本身零版本能力**。
9.4.5 最佳实践第 4 条（ch9:1576）把这一点说白了：「使用 Git 进行版本控制，追踪笔记的演化」。
诚实，但对「Agent 自动改笔记」这个主用例来说，**默认路径就是不可逆的**。

**（b）`search` 用子串匹配，反而是中文安全的**（ch9:1190）：

```python
if query_lower in title.lower() or query_lower in content.lower():
```

这是全章少见的**中文能正常工作**的检索路径——因为它没有 `split()`。
**同一章里，NoteTool 的搜索对中文有效，ContextBuilder 的相关性对中文恒为 0。**
这个对照说明作者不是不知道怎么写中文安全的匹配，是在 ContextBuilder 那里没做。
（代价是子串匹配只能整句命中，把一整句自然语言问题当 query 会零命中——
 但那是精度问题，不是功能性失效。）

**（c）损坏的笔记被静默跳过**（ch9:1199-1201）：

```python
except Exception as e:
    print(f"[WARNING] 读取笔记 {note_id} 失败: {e}")
    continue
```

`_search_notes` 返回的列表里**不会包含任何「有 N 篇读不出来」的信息**。
这是本章第四处「降级不留痕」，而且它出现在**唯一声称做完整性校验的组件里**：
损坏被检出了，然后被吞掉了。

### 6.3 书稿 NoteTool 的 schema 与 0.2.8 代码对不上（版本差 + 书稿自身 bug）

| 项 | 书稿 ch9 | `V0.2.8` note_tool.py |
|---|---|---|
| 索引结构 | dict，key 是 note_id（ch9:933） | **list**：`self.notes_index["notes"]`（note_tool.py:317） |
| `file_path` 字段 | 索引与 metadata 里都有（ch9:940、1055） | **不存在**，路径由 `_get_note_path(note_id)` 现推（note_tool.py:124-126） |
| 笔记数量上限 | **0 命中**（`grep -c 'max_notes'` = 0） | `max_notes: int = 1000`，达上限**拒绝创建**（note_tool.py:80, 289-290） |

第二行连带一个**书稿独有的 bug**：`_create_note` 先 `_build_markdown(metadata, ...)`（ch9:993）
**再**给 `metadata` 加 `file_path`（ch9:1001），所以落盘的 YAML 里没有 `file_path`；
而 `_update_note` 从文件解析回来的 metadata 上直接取 `metadata["file_path"]`（ch9:1136）——
**第一次 update 就会 KeyError**。且 ch9:1142 又把这个缺字段的 metadata 写回索引，把索引也带坏。
0.2.8 代码没有这个问题，因为它压根不存 `file_path`。

顺带一条**两边都有**的隐患：note_id = `note_{到秒时间戳}_{len(index)}`（ch9:980 / note_tool.py:118-122），
而 `delete` 会让 `len(index)` 变小（ch9:1310 / note_tool.py:407-410）。
**删一篇之后，同一秒内新建的笔记可以复用被删笔记的 id**，
`create` 直接 `open(path,'w')` 覆盖、索引直接赋值，**全程静默**。
窗口很窄（同秒），但对「id 是证据指针」的系统而言，**id 可复用是致命属性**——
D-016 的映射表 id 不能用这种生成方式。

值得记一条**正面的**：`create` 到达 `max_notes` 上限时是**拒绝**（返回错误串），
不是淘汰旧笔记（note_tool.py:289-290）。**这是 fail-closed，方向对**。
只是书里完全没提这个上限。

### 6.4 9.4.4 与 ContextBuilder 集成（ch9:1316-1553）—— 本章最有价值的一处发现

`_notes_to_packets`（ch9:1413-1431）把 `note_id` **写进了 packet 的 metadata**：

```python
content = f"[笔记:{note['title']}]\n{note['content']}"      # ch9:1418
packets.append(ContextPacket(
    content=content,
    ...
    metadata={"type": "note", "note_type": note['type'], "note_id": note['note_id']}   # ch9:1425-1429
))
```

**这是一个真正的证据指针。然后它就死在那里了。**
`_structure`（ch9:458-466）只读 `metadata["type"]`；`"note"` 落进 `else` 分支进 `[Context]`，
渲染时只取 `packet.content`（ch9:483）。
全章 `note_id` 的最后一次出现就是 ch9:1428 那个赋值：

```
$ grep -n "note_id" 第九章\ 上下文工程.md | tail -4
1406:            all_notes = {note['note_id']: note for note in blockers + search_results}
1428:                    "note_id": note['note_id']
2257:  (9.6.3，本轮不重读)
2290:  (9.6.3，本轮不重读)
```

**写进去了，没有任何一处读出来。**
这与 `truncator.py` 的 `full_output_path` 是**同一种病**：形状对，消费方不存在。
**`ARCHITECTURE §8.5`（证据指针必须被下游强制消费）在这一章找到了它最干净的反例。**

后果在书自己的示例输出里就爆了。示例里模型的回答结尾是（ch9:1526）：

```
[依据来源: 笔记 note_20250119_153000_0, 项目知识库]
```

**模型不可能知道这个 id。** 进入上下文的 `content` 只有 `[笔记:{title}]` + 正文（ch9:1418），
系统指令只说「在建议中说明依据来源(笔记、记忆或知识库)」（ch9:1468），**没给任何 id**。
**这段「运行效果展示」是编的，或者是把一次幻觉当成了正确行为展示。**
（模型在正文里引用的 `笔记[重构项目 - 第一阶段]` 倒是合法的——那是 title，确实在上下文里。
 但 title 不唯一、不稳定，不能当证据指针。）

这是本轮第二个「书稿示例跑不出来」的实例（第一个见 §5.3）。
**对本项目的用法：这两条正好可以写进 `EVAL_CASES §3.3` 的失败归因——
「引用了一个上下文中不存在的标识符」是一类可自动检测的幻觉，
判据是：答案里出现的每个证据 id，必须能在本次上下文的字面量中找到。**

### 6.5 集成层的另外三处静默降级

- `_retrieve_relevant_notes` 失败 → `return []`（ch9:1409-1411）。
  **比 print 更糟：调用方拿到一个形态完全合法的空列表**，与「确实没有相关笔记」不可区分。
- `_save_as_note` 失败 → print 后吞掉（ch9:1453-1455）。
  **笔记没存上，但 `run()` 照常返回答案**，用户以为记下来了。
- `_update_history` 只留最近 10 条（ch9:1483-1484），更早的直接丢，无归档。

加上 §4.1、§4.4、§6.2(c)，**全章共 6 处 fail-open 且不留痕**。

### 6.6 9.4.5 最佳实践五条（ch9:1554-1584）

其中第 2 条（ch9:1565-1568）对本项目是**明确要刻意不借**的：

> **定期清理和归档**：对于已解决的 blocker，更新为 conclusion；对于过时的 action，**及时删除或更新**。

书把「删除过时笔记」当成卫生习惯。
对一个可审计系统，**「过时」恰恰是必须保留的状态**——
一条后来被推翻的结论，是复核当时那次回答的必要材料。
本项目的笔记/证据只能追加与标记失效，**不能删除**。

第 3 条（ch9:1570-1574）有一条可借的：
「根据笔记类型设置不同的相关性分数（blocker > action > conclusion）」——
即**按类型给先验权重**，而不是全靠文本相似度。
这对中文场景尤其有用，因为文本相似度那条路在本章是坏的。

三处 token 计数口径不一致，顺手记一下：
`_count_tokens` 手写中英估算（ch9:572）｜`len(content) // 4`（ch9:1423）｜
0.2.8 代码里的 `tiktoken` cl100k_base（builder.py:345-353）。
**同一章三套口径**，预算守护建立在一个自己都不自洽的度量上。

---

## 7. 9.5 TerminalTool 即时文件系统访问（ch9:1585-2029）

这一节是 9.2.2「JIT 上下文」的落地件。立论（ch9:1589、1601-1608、1641）：
**用即时探索代替预先索引与向量化**——`rag_tool.add_document("./project/**/*.py")` 耗时且会过时，
`find` / `grep` / `head` 实时且精确。

对本项目，这个立论**部分成立、部分不成立**，见 §11 启示表。先记事实。

### 7.1 书稿宣称的四层安全机制（ch9:1643-1729）

| 层 | 机制 | 行号 |
|---|---|---|
| 1 | 命令白名单 | ch9:1649-1673 |
| 2 | 工作目录限制（沙箱） | ch9:1678-1697 |
| 3 | 超时控制（默认 30s） | ch9:1698-1712 |
| 4 | 输出大小限制（默认 10MB） | ch9:1713-1727 |

书对第一层的表述（ch9:1649）：

> **只允许安全的只读命令，完全禁止任何可能修改系统的操作**

### 7.2 **第一层和第二层，在它自己钉的 0.2.8 代码里都不成立**

**（a）白名单里有 `bash` / `sh` / `python` / `node`，书稿把这一整类删掉了。**

`V0.2.8:hello_agents/tools/builtin/terminal_tool.py:62-79` 的真实白名单，
最后一组是书稿里**完全不存在**的：

```python
        # 其他
        'echo', 'which', 'whereis',
        # 代码执行
        'python', 'node', 'bash', 'sh',
    }
```

书稿的清单（ch9:1649-1673）在 `'echo', 'which', 'whereis',` 处**戛然而止**。
在全章 2819 行里：

```
$ grep -c "'sh'"     第九章\ 上下文工程.md   → 0
$ grep -c 'node'     第九章\ 上下文工程.md   → 0
$ grep -c '代码执行' 第九章\ 上下文工程.md   → 0
$ grep -n 'bash'     第九章\ 上下文工程.md
7:```bash        （代码块围栏）
1510:```bash      （代码块围栏）
```

**`bash` 在书里只作为 markdown 代码块围栏出现过两次，从来不是白名单条目。**
而代码里 `bash` ∈ `ALLOWED_COMMANDS`，校验只看 `parts[0]`（terminal_tool.py:122-127），
随后 `_execute_command` 用 `shell=True` 执行（terminal_tool.py:191-200）。
**`{"command": "bash -c 'rm -rf ...'"}` 会通过白名单。**
代码自己的 tool description 也承认了（terminal_tool.py:89-90）：
「执行安全的文件系统、文本处理**和代码执行**命令」。

**结论：书稿的安全性论述与它自己 `pip install` 的那个版本不一致。**
这不是「书讲对了实现没跟上」，是**书稿删掉了实现里不好看的那一段，然后据此下了一个更强的安全结论**。

**（b）即使按书稿那份缩减白名单，`shell=True` + 只查首词也拦不住。**

`_execute_command`（ch9:1742-1751 / terminal_tool.py:191-200）：

```python
result = subprocess.run(command, shell=True, cwd=str(self.current_dir), ...)
```

`shlex.split("cat a; rm b")` → `['cat','a;','rm','b']` → `base_command='cat'` ∈ 白名单 → 放行 →
然后 `shell=True` 把 `;` 当分隔符执行。`&&`、`|`、`$(...)` 同理。
另外白名单里 `awk` / `sed` / `find` 本身就是执行原语
（`awk 'BEGIN{system(...)}'`、`find -exec`）——
**书稿自己的示例就在用 `find -exec`**（ch9:1941）：

```python
terminal.run({"command": "find . -name '*.py' -exec wc -l {} + | tail -n 1"})
```

所以「加参数过滤」也堵不上：`-exec` 是这个工具正常用法的一部分。

**（c）沙箱只管 `cd`，不管命令参数。**

`relative_to(self.workspace)` 在整个 `terminal_tool.py` 里**只出现 1 次**：

```
$ grep -c 'relative_to' V0.2.8:hello_agents/tools/builtin/terminal_tool.py
1
```

那一次在 `_handle_cd`（terminal_tool.py:173）。`_execute_command` 里**没有任何路径检查**。
而书稿明确宣称（ch9:1690）：

```python
terminal.run({"command": "cat /etc/passwd"})  # ❌ 不允许访问工作目录外的路径
```

**书稿展示的这个拒绝，在书稿自己给出的 `_execute_command` 代码里也找不到实现**
（ch9:1740-1774 全文没有路径校验），在 0.2.8 代码里同样没有。
这是本轮第四个「书里的示例输出跑不出来」的实例，而且这一个是**安全断言**。

补一条默认值：`workspace: str = "."`（terminal_tool.py:83），
即**不传参时沙箱就是当前工作目录**，并且构造时 `mkdir(parents=True, exist_ok=True)`（terminal_tool.py:102）。

**边界声明**：以上全部是**对仓库代码的判断**，我读了 `V0.2.8` 的 `terminal_tool.py` 全文（230 行）。
我**没有实跑**这些绕过，也没有在任何机器上执行过 `bash -c`。
上述属于**代码阅读得出的结论**，标 `UNVERIFIED-BY-EXECUTION`。

### 7.3 输出截断：形状比 ContextBuilder 好，仍然不可逆（ch9:1760-1762）

```python
if len(output) > self.max_output_size:
    output = output[:self.max_output_size]
    output += f"\n\n⚠️ 输出被截断（超过 {self.max_output_size} 字节）"
```

比 `_compress` 强的地方：**标记是无条件加的**，不像 ch9:537 那样只在某个分支里加。
仍然缺的：**被截掉的 10MB 之后的内容不写任何地方，没有 `full_output_path`。**
这正好是 1.0.0 的 `truncator.py` 后来补上的那半步——
**书稿这一版停在「截断 + 打标记」，没有走到「截断 + 落盘 + 给路径」。**

`_execute_command` 的兜底（ch9:1770-1773）把超时与任意异常都变成一个**字符串**返回：

```python
except subprocess.TimeoutExpired:
    return f"❌ 命令执行超时（超过 {self.timeout} 秒）"
except Exception as e:
    return f"❌ 命令执行失败: {e}"
```

**返回类型与成功时完全相同（都是 str）**，调用方要靠 `❌` 这个 emoji 做字符串匹配才能分辨成败。
与 §5.2 里 builder.py 用 `"未找到" not in rag_results` 判成败是同一个反模式。
本章第七处 fail-open。

### 7.4 9.5.3-9.5.4：`source` 字段出现了，然后又没人读（ch9:1843-2029）

9.5.3 是四组使用模式（探索式导航 / 数据文件分析 / 日志分析 / 代码库分析），
展示输出都是构造的样例，无新机制。

9.5.4 有两处要记：

**（a）`metadata` 里第一次出现 `source`**（ch9:2006-2020）：

```python
ContextPacket(
    content=f"代码库结构:\n{code_structure}",
    ...
    metadata={"type": "code_structure", "source": "terminal"}
),
ContextPacket(
    content=f"最近提交:\n{recent_changes}",
    ...
    metadata={"type": "git_history", "source": "terminal"}
)
```

两件事同时发生：
1. **书自己破了 ch9:145 定下的「不引入来源维度」规则**——例子里就写了 `source`；
2. **`_structure` 依然只读 `metadata["type"]`**（ch9:458-466），
   `"code_structure"` / `"git_history"` 都落进 `else` → `[Context]`，只渲染 `content`。
   **`source` 写进去了，没有任何一处读出来。**

这是 `ARCHITECTURE §8.5` 反例的第三次出现（前两次：ContextPacket 的 metadata 通道、
NoteTool 的 `note_id`）。**同一个病在一章里犯了三次，说明它不是笔误，是缺一条硬规则。**

**（b）示例调用了白名单外的命令**（ch9:2000）：

```python
recent_changes = terminal.run({"command": "git log --oneline -10"})
```

`git` **不在** `ALLOWED_COMMANDS` 里（书稿 ch9:1649-1673 与 terminal_tool.py:62-79 均无）。
这行实跑会返回 `❌ 不允许的命令: git`，`recent_changes` 拿到的是错误串，
然后被原样拼进 `content=f"最近提交:\n{recent_changes}"` 塞进上下文。
**第五个跑不出来的示例**，而且它演示了一个更实际的危害：
**失败的工具输出与成功的工具输出在 packet 里长得一模一样，会被当作证据送进 `[Context]`。**

---

## 8. 9.6 长程智能体实战（9.6.1 / 9.6.2 / 9.6.4 / 9.6.5，**9.6.3 本轮不重读**）

### 8.1 场景与架构（ch9:2030-2058）

场景：维护一个中型 Flask 应用，「约 50 个 Python 文件」（ch9:2043）。
三个挑战 → 三个工具的对应关系写得很清楚（ch9:2047）：

| 挑战 | 对策 |
|---|---|
| 信息量超出上下文窗口（数万行代码） | TerminalTool 即时按需探索 |
| 跨会话状态管理（重构持续数天） | NoteTool 记录进展/待办/关键决策 |
| 上下文质量与相关性 | ContextBuilder 筛选与组织 |

9.6.2「系统架构设计」只有一张外链图片 `9-3.png` 和一句「三层架构」（ch9:2051-2057），
**正文没有对架构的任何文字描述**。这一节实质是空的。

### 8.2 9.6.4 的整段演示是编的（ch9:2469-2739）—— 有硬证据

书里的三天工作流展示了具体数字与文件名：

| 书稿断言 | 行号 |
|---|---|
| 「约 50 个 Python 文件」 | ch9:2043 |
| 「总计约 3,500 行 Python 代码」 | ch9:2504 |
| 「总行数: 3,542 行」「最大文件: services/order_service.py (456 行)」 | ch9:2551-2553 |
| 「order_service.py::process_order 方法有 8 层嵌套」 | ch9:2562 |
| 「User (user.py) - 字段: id, username, email, password_hash, created_at」 | ch9:2518 |
| 「测试覆盖率仅 45%」 | ch9:2566 |

配套仓库里真实发的示例代码库（`datawhalechina/hello-agents` @ `45dd84e`，
`code/chapter9/codebase/`）是：

```
$ git ls-tree -r --name-only HEAD code/chapter9/codebase/
code/chapter9/codebase/__init__.py
code/chapter9/codebase/api_client.py
code/chapter9/codebase/data_processor.py
code/chapter9/codebase/models.py
code/chapter9/codebase/utils.py

$ wc -l *.py
  358 total          ← 5 个文件，358 行

$ grep -ril 'flask|order_service|process_order|password_hash' .
（零命中）
```

**5 个文件 / 358 行，没有 Flask、没有 `order_service.py`、没有 `process_order`、没有 `password_hash`。**
书稿演示的那个 `./my_flask_app` 代码库**在仓库里不存在**——
`code/chapter9/codebase_maintainer.py:448-449` 确实写着
`project_name="my_flask_app", codebase_path="./my_flask_app"`，指向一个不存在的目录。

而 `code/chapter9/06_three_day_workflow.py:162` 把路径写死成了**作者本机的绝对路径**：

```python
codebase_path="/Users/suntao/Documents/GitHub/hello-agents/code/chapter9/codebase",
```

（同一文件的 185 / 219 / 267 行重复了四次。）

**结论：9.6.4 那 270 行「运行效果」是构造的文本，不是任何一次真实运行的输出。**
这是本章第六个、也是最大的一个「示例不可复现」实例。
（配套 `README.md` 还列了一个 `logs/app.log`，`git ls-tree` 显示 `code/chapter9/logs/` 不存在。）

**这一条不是为了挑错，是因为它直接对应 `PROJECT_SPEC.md §完成定义` 与
`rules/failure-modes.md`：一份看起来很详实的「运行效果」如果没人跑过，
它比没有更危险——读者会拿它当验收基线。**

### 8.3 `generate_report()`：本章关于「留痕」的最终答案是三个计数器（ch9:2719-2737）

```json
{
  "session_info": { "session_id": "...", "project": "...", "duration_seconds": 172800 },
  "activity": { "commands_executed": 24, "notes_created": 8, "issues_found": 3 },
  "notes": { ... }
}
```

**执行了 24 条命令——哪 24 条？没有。** 发现 3 个问题——依据哪次命令输出？没有。
这是聚合指标，不是证据链。用它**没法复核任何一条结论**。
与 9.3.5 第 4 条「监控与日志」（ch9:782）记「选中信息数量、token 使用率」是同一层次。

### 8.4 9.6.5 运行效果分析（ch9:2740-2747）

五条特性总结（跨会话连贯性 / 智能上下文管理 / 即时文件访问 / 自动知识管理 / 人机协作）
全部是对 9.6.4 那段编造输出的复述，**没有新增可验证内容**。

末段的扩展方向里有一句自相矛盾（ch9:2746）：
「**通过 TerminalTool 执行 git 命令追踪代码变更**」被列为**未来扩展**——
但 9.5.4 的示例（ch9:2000）已经把 `git log --oneline -10` 当成能用的写法在演示了，
而 `git` 从来不在白名单里（见 §7.4b）。

---

## 9. 9.7 本章总结 / 习题 / 参考文献（ch9:2748-2819）

### 9-a 总结（ch9:2748-2775）

四条「核心收获」中的第三条是 **「安全第一：多层安全机制确保系统稳定」**（ch9:2770）。
结合 §7.2，这句话与它自己钉的 0.2.8 代码（白名单含 `bash`/`sh`/`python`/`node`、
`shell=True`、非 cd 命令零路径校验）**不成立**。

### 9-b 习题里的三处「习题与正文对不上」（ch9:2776-2812）

习题往往能反映作者认为自己写了什么。这一章有三处对不上：

1. **ch9:2792**：「GSSC流水线中的"压缩"阶段**使用了LLM进行智能摘要**」。
   **正文的 `_compress` 是字符截断**（ch9:497-544），书自己的注释写着
   「简单截断(**生产环境中可以使用** LLM 摘要)」（ch9:535）——是没做，不是做了。
2. **ch9:2798**：「NoteTool使用了**分层笔记系统（项目笔记、任务笔记、临时笔记）**」。
   **正文的 NoteTool 是六种平级类型**：`task_state / conclusion / blocker / action / reference / general`
   （ch9:970、1558-1563），**没有任何分层结构**，也没有「临时笔记」这个概念。
3. **ch9:2799**：「当前的安全机制（**路径验证**、命令白名单、**权限检查**）是否足够？」
   **「权限检查」正文里不存在**；「路径验证」只对 `cd` 有（§7.2c）。
   这道题问读者「够不够」，而**正确答案是「不够，而且其中两项没实现」**，书没说。

顺带：ch9:2805 那道「断点续传」题问「**如何验证恢复后的状态是否正确**」，
是全章唯一一次触碰「状态可验证性」——**但它是一道没有答案的习题**。

### 9-c 参考文献只有两条（ch9:2814-2818）

```
[1] Anthropic. Effective Context Engineering for AI Agents.
[2] David Kim. Context-Engineering (GitHub).
```

**这解释了整章的质量分布。**
9.1-9.2（ch9:25-124，约 100 行）基本是 [1] 那篇 Anthropic 工程博客的中文缩写——
`context rot`、注意力预算、JIT 上下文与轻量化引用、渐进式披露、
compaction / structured note-taking / sub-agent 三件套，连两张配图的英文标题
（「Prompt engineering vs Context engineering」ch9:33、「Calibrating the system prompt」ch9:79）
都是那篇博客的图。**这部分讲得对、也讲得准。**

9.3-9.6（ch9:125-2747，约 2600 行）是 HelloAgents 自己的实现，**没有任何外部参考**。
**理论是借来的，实现是自研的，两者之间没有对齐检查**——
9.2 讲了「轻量化引用 / 按需拉回」，9.3 的 `_compress` 就是 `text[:max_chars]`；
9.2 讲了「先优化召回再优化精确度」，9.3 的相关性在中文上恒为 0，召回直接是 0。

**这是本章最重要的一条结构性观察，也是本项目该从中拿走的：
「章节里写了正确的原则」与「代码实现了那条原则」之间必须有强制检查，
否则原则只是章首的装饰。** 对应到本项目就是
`ARCHITECTURE §8.5`（证据指针必须被下游**强制消费**）里的「强制」二字——
本章三次生产证据指针（`metadata` 通道、`note_id`、`source`），零次消费。

---

## 10. 书稿与框架实现的差异表

**版本基准**：书稿 ch9:8 钉 `hello-agents[all]==0.2.8`，比对对象是 `V0.2.8` tag。
`V1.0.0` 只在明确标注处出现。三种判定：
**「书没讲」** ｜ **「书讲错了」**（书与代码都错，或书比代码更错）｜ **「版本差」**（书对应的是 0.2.8，1.0.0 才有/才改）。

| # | 事项 | 书稿 | 代码 | 判定 |
|---|---|---|---|---|
| **D-1** | 工具输出全文落盘 + 返回 `full_output_path` | **零命中**（`grep -c 'full_output_path'` = 0；`truncator` = 0）。ch9:13-15 的组件清单里也没有 `truncator.py` | `truncator.py` 是 **1.0.0 才有的文件**；`V0.2.8:hello_agents/context/` 只有 `__init__.py` + `builder.py` | **书没讲**（不是「实现没跟上」；本章根本没有对应章节） |
| **D-2** | 压缩后原文归档 | **零命中**（`可逆/不可逆/还原/回滚/原文` 各 0）。ch9:104 只说「丢弃重复的工具输出与噪声」 | `history.py` 同为 **1.0.0 才有**；`V0.2.8` 的 `_compress` 是按行截断，同样不归档 | **书没讲** + 两版实现都不可逆 |
| **D-3** | 中文相关性 | ch9:396-407 用 `set(...split())` + **Jaccard `∩/∪`** | `V0.2.8`/`V1.0.0` builder.py:210-217 用 `set(...split())` + **包含度 `∩/query`**（两版**逐字节相同**） | **书讲错了，而且比代码更错**：Jaccard 让长英文证据也跌到 0.0161 < `min_relevance` |
| **D-4** | token 计数 | ch9:563-577 手写 `chinese_chars + english_words*1.3`；ch9:1423 又用 `len//4` | builder.py:345-353 用 `tiktoken` cl100k_base，异常降级 `len//4` | **书讲错了**（代码更严谨；且书内部三套口径不一致） |
| **D-5** | 预算填充遇到装不下的包 | ch9:379 `break`（挡住后面所有小包） | builder.py:250-252 `continue` | **书讲错了** |
| **D-6** | `[Output]` 是否要求列出来源 | ch9:486 一行「请基于以上信息,提供准确、有据的回答。」 | builder.py:308-314 四段式，**第 2 条「依据（列出支撑证据及来源）」** | **书讲错了**（本轮唯一一处**代码比书对**的证据要求） |
| **D-7** | `[State]` 分区 | ch9:135 承诺六分区，`_structure`（ch9:470-488）只产出五个，无 `[State]` | builder.py:288-293 实现了 `type == "task_state"` → `[State]` | **书讲错了**（书漏实现自己承诺的分区） |
| **D-8** | `_parse_memory_results` / `_parse_rag_results` | ch9:266、281 **只调用，无函数体** | **不存在**；0.2.8 直接把整个结果串塞成一个 packet | **书讲错了**（唯一能写来源的环节被跳过） |
| **D-9** | NoteTool 索引结构与 `file_path` | ch9:933 dict 结构、索引与 metadata 都有 `file_path`；`_update_note` 取 `metadata["file_path"]`（ch9:1136）**必 KeyError** | note_tool.py:317 是 **list**；**没有 `file_path` 字段**，路径由 `_get_note_path()` 现推 | **书讲错了**（书稿独有的 bug + schema 与代码不符） |
| **D-10** | NoteTool 笔记数量上限 | **零命中**（`grep -c 'max_notes'` = 0） | note_tool.py:80 `max_notes=1000`，达上限**拒绝创建**（fail-closed） | **书没讲**（而且漏掉的正好是方向对的那条） |
| **D-11** | 「完整性校验」 | ch9:949 声称索引「可以检测文件缺失或**损坏**」 | note_tool.py 里 `hashlib/sha256/md5/checksum` **零命中**；索引也无摘要列 | **书讲错了**（两边都没有校验和，损坏检测不存在） |
| **D-12** | TerminalTool 白名单是否含代码执行 | ch9:1649-1673 的清单**止于 `'echo','which','whereis'`**；ch9:1649 断言「只允许安全的**只读**命令，完全禁止任何可能修改系统的操作」 | terminal_tool.py:62-79 白名单**含 `'python','node','bash','sh'`**，注释就叫「# 代码执行」；tool description 也写「和代码执行命令」 | **书讲错了**（书删掉了实现里的一整组，然后据此下了更强的安全结论） |
| **D-13** | 非 `cd` 命令的路径沙箱 | ch9:1690 展示 `cat /etc/passwd` → `❌ 不允许访问工作目录外的路径` | `grep -c 'relative_to'` = **1**，唯一一次在 `_handle_cd`；`_execute_command` 零路径检查，`shell=True` | **书讲错了**（书稿自己给出的 `_execute_command` 代码里也没有这个拒绝） |
| **D-14** | 输出截断留痕 | ch9:1760-1762 无条件加 `⚠️ 输出被截断` 标记；ch9:537 的 `_compress` 只在 `remaining>50` 分支加标记 | 与书一致 | **一致**；但两者都缺 `full_output_path`，见 D-1 |
| **D-15** | 示例可复现性 | ch9:655-687、1490-1550、1998、2469-2739 五处「运行效果」 | 配套 `code/chapter9/codebase/` 实为 **5 文件 / 358 行**，无 Flask/`order_service`/`process_order`；`06_three_day_workflow.py:162` 写死 `/Users/suntao/...` 绝对路径；`codebase_maintainer.py:449` 指向不存在的 `./my_flask_app` | **书讲错了**（构造的输出被当作运行结果展示） |

**结构性结论**：D-1、D-2、D-10 是「书没讲」；其余 12 条里 11 条是「书讲错了」，
且其中 **D-4/D-5/D-6/D-7/D-12 是「代码写对了、书写错了」**——
方向与常见的「书讲对了实现没跟上」**相反**。
**版本差只解释 D-1 与 D-2 两条**（`truncator.py` / `history.py` 是 1.0.0 新增），
其余不能用版本差搪塞。

---

## 11. 对 finaudit-agent 的骨架启示

**规则**：每条必须写落地点。已落地 → 具体编号；未落地 → 明写 **`未落地`** 并说明该落到哪里。

### 11.A 该借鉴

| # | 借鉴什么 | 出处 | 落地点 |
|---|---|---|---|
| A-1 | **轻量化引用替代全文入上下文**：维护文件路径/查询/URL，运行时按需加载 | ch9:87 | **已落地** —— `D-019`（抽取记录的 `page` + `anchor_page` 就是这种引用）+ `ARCHITECTURE §8.5`（指针必须被强制消费） |
| A-2 | **索引与正文分离**：`notes_index.json` 只放 id/type/tags/时间/路径，正文留在各自文件里 | ch9:933-941 | **已落地** —— `D-016`（映射表按命名空间拆分）已经是这个分层 |
| A-3 | **索引必须带内容摘要列**，否则「完整性校验」只能查缺失、查不了损坏 | 由 ch9:949 的空头支票反推 | **部分落地** —— `D-012` 只覆盖**评测集冻结**的 SHA-256。**运行期产物（抽取记录、证据文件）的索引是否带摘要列，`未落地`** → 应落到 `D-016` 增补一条：映射表/抽取记录的索引行必须含 `content_sha256`，读入时校验 |
| A-4 | **fail-closed 的容量上限**：笔记到达 `max_notes` 时**拒绝创建**，不淘汰旧笔记 | note_tool.py:289-290（书**没讲**，见 D-10） | **已落地** —— `D-018`（fail-closed 在读入边界）同向。作为「容量满时拒绝而非淘汰」的正面实证补进 `D-018` 的依据栏，**该补充动作 `未落地`** |
| A-5 | **按类型给先验权重**，不全靠文本相似度（blocker > action > conclusion） | ch9:1572 | ~~**`未落地`**~~ → **已落地 2026-08-26**（登记册 **`L-74`**，`rules/pitfalls.md` **第 8 条对策栏补充**）。⚠️ **落地当时漏了回标**，登记册状态一直挂 `OPEN`——内容早已在 pitfalls 第 8 条里，状态与标注两处都没改。这是登记册 §3.1 那个毛病的**反向实例**（做了但没回标），且第六道门的 R5 抓不到它：R5 只查「已落地的有没有回标」，不查「其实已落地却仍标 `OPEN` 的」。以下为原文，保留不改：应落到 `rules/pitfalls.md` 第 8 条的对策栏：中文场景下相似度不可靠时，检索排序必须有**非文本的**兜底信号（字段类型 / 报表科目层级 / 年度距离） |
| A-6 | **固定骨架的分区模板**（Role / Task / State / Evidence / Context / Output），便于调试与 A/B | ch9:135 | ~~**`未落地`**~~ → **已落地 2026-08-26**（登记册 **`L-75`**，`ARCHITECTURE` **§8.7**）：分区骨架 + `[Evidence]` 必带 `field_id` 前缀两条都写死了，另**加了一条本章 A-7 提供的约束**——`[Evidence]` 与 `[Output]` 不参与预算裁剪，反例正是 `ch9:538` 的 `break`（越要紧的契约越先被整段裁掉）。以下为原文，保留不改：应落到 `ARCHITECTURE` 新增一节「回答上下文的固定分区」，并规定 `[Evidence]` 的每条必须带 `field_id` 前缀 |
| A-7 | **输出约束里显式要求「依据（列出支撑证据及来源）」** | `V0.2.8` builder.py:308-314（书稿删掉了，见 D-6） | **已落地（方向）** —— `D-003` 证据链是第一类产物。但**「输出格式约束在预算紧张时最先被丢弃」这个反例（ch9:538 的 `break` + `[Output]` 排在最后）所对应的规则 `未落地`** → 应落到 `ARCHITECTURE §8.5` 增补：输出契约与证据分区**不参与预算裁剪**，裁剪只发生在证据条目内部 |
| A-8 | **上下文腐蚀是梯度而非悬崖**：窗口装得下 ≠ 召回准确 | ch9:48-55 | **已落地（方向）** —— `D-013`（数值以年报 PDF 原文为准）+ `D-017`（自建封闭解析器）都指向「先结构化抽取再进上下文」。**但「禁止把整份年报文本直接塞进上下文让模型自己找」这条明文约束 `未落地`** → 应落到 `D-013` 增补一条 |
| A-9 | **最小可行工具集（MVTS）**：「如果人类工程师都说不准用哪个工具，别指望智能体做得更好」 | ch9:71 | ~~**`未落地`**~~ → **已落地 2026-08-26**（登记册 **`L-76`**，`ARCHITECTURE` **§8.1.3**）。落地时写明它是**程序不是断言、无机械判据**，跑没跑要写进该阶段 `VERIFICATION.md`——否则「看起来工具不多」会被当成通过。以下为原文，保留不改：应落到 `ARCHITECTURE §8.1` 邻域：Phase 2 工具集定稿前，用「人类能否零歧义地选对工具」做一次自检 |

### 11.B 该刻意不借（每条写理由）

| # | 不借什么 | 出处 | 理由 | 落地点 |
|---|---|---|---|---|
| B-1 | **「不引入来源/优先级等分类维度，避免复杂度增长」** | ch9:145 | 书把 provenance 当成可为降复杂度而砍掉的维度。对可审计系统，来源不是维度，是**产物本身**。方向相反，不是程度差异 | **已落地** —— `D-003` |
| B-2 | **证据指针只塞进 `metadata`、不进签名** | ch9:1428（`note_id`）、ch9:2012/2018（`source`）、ContextPacket 的 `metadata` 通道 | 本章**三次生产证据指针、零次消费**（`_structure` 只读 `metadata["type"]`）。「可选键」等价于没有 | **已落地** —— `ARCHITECTURE §8.5`。~~**本章这三个新实证应补进 §8.5 的依据栏（原文只引了 `truncator.py` 一例），该补充 `未落地`**~~ → **依据栏已补 2026-08-26**（登记册 **`L-20`**）：三条以表格逐条列进 §8.5，连同 `truncator.py` 共四个独立实例，四次形状一致 ⇒ 该节的强度已由「建议」升为「结构性要求」 |
| B-3 | **`text.split()` 算中文相关性** | ch9:396-398 | 中文恒 0 且静默 | **已落地** —— `rules/pitfalls.md` 第 8 条。**但第 8 条记的是 `∩/query` 版本；书稿的 Jaccard `∩/∪` 会让长英文证据也跌破阈值（实测 0.0161 < 0.1）——这个「不只中文会挂」的补强 `未落地`** → 应更新 pitfalls 第 8 条 |
| B-4 | **截断/压缩后原文不落盘**（`text[:max_chars]`、`response[:200]` 当摘要、`break` 后整段静默丢弃） | ch9:561、ch9:750、ch9:538 | 不可逆压缩 = 带回执的删除 | **已落地** —— `rules/pitfalls.md` 第 11 条 + `ARCHITECTURE §8.5` |
| B-5 | **「定期清理和归档：对于过时的 action，及时删除或更新」** | ch9:1565-1568 | 「过时」恰恰是复核当时那次回答的必要材料。一条后来被推翻的结论必须留着 | **`未落地`** → 应落到 `D-003` 增补一条：证据、抽取记录与笔记**只追加、只标失效，不删除**；或新开 `D-022` **→ 已落地 2026-08-26（登记册 `L-78`，`rules/pitfalls.md` 第 16 条）。** |
| B-6 | **id 生成用 `{时间戳}_{len(index)}`，而 delete 会让 len 变小** | ch9:980 / note_tool.py:118-122 + 407-410 | 同秒内删后新建可复用被删 id，`create` 直接覆盖文件与索引，全程静默。**id 可复用对「id 即证据指针」的系统是致命属性** | **`未落地`** → 应落到 `D-016`：映射表与抽取记录的 id 必须单调不复用（自增序列或内容摘要），禁止用集合长度参与构造 |
| B-7 | **把工具失败降级成一个「形态合法」的返回值**：`print` + 继续（ch9:261）、`return []`（ch9:1411）、`return "❌ …"` 字符串（ch9:1773）、用 `"未找到" not in result` 判成败（builder.py:177） | 全章共 **7 处 fail-open 不留痕** | 「RAG 挂了」与「RAG 正常但零命中」在下游完全不可区分；错误串会被当证据拼进 `[Context]`（ch9:2000 的 `git log` 就是实例） | **已落地（方向）** —— `D-018`。**但「证据源不可用必须单独计类、不得并入实质结果」这条判据 `未落地`** → 应落到 `EVAL_CASES §5 失败归因`，仿 `J-2` 的 `UNPARSEABLE` 增设 `SOURCE_UNAVAILABLE` 类 |
| B-8 | **命令白名单 + `shell=True` 当安全边界** | ch9:1649-1673 / terminal_tool.py:62-79、191-200 | 只查 `parts[0]`，`;`/`&&`/`$()` 全放行；白名单本身含 `bash`/`sh`/`python`/`node`；`awk`/`sed`/`find -exec` 都是执行原语——书自己的示例就在用 `find -exec`（ch9:1941） | **`未落地`** → 应落到新 `D-0xx`：**不给 Agent 通用命令执行能力**，文件访问一律走白名单化的具名函数。`D-017`（不引三方求值库、自建封闭算术解析器）已在**算术**这一处落地了同一原则，但没有一般化 **→ 已落地 2026-08-26（登记册 `L-81`，`rules/pitfalls.md` 第 17 条）。** |
| B-9 | **拿「运行效果展示」当验收证据** | ch9:655-687、1490-1550、2469-2739；实证见 §8.2 | 五处示例经核对都跑不出来（含一处安全断言 ch9:1690）。看起来详实的假输出比没有更危险——读者会拿它当基线 | **已落地（方向）** —— `PROJECT_SPEC §完成定义` + `rules/failure-modes.md`。**但「本仓文档里出现的任何运行输出必须附可复现命令，否则标 `UNVERIFIED`」这条对文档本身的硬规则 `未落地`** → 应落到 `references/README.md` 硬规则第 5 条 |
| B-10 | **答案引用上下文里不存在的标识符** | ch9:1526 的 `[依据来源: 笔记 note_20250119_153000_0, …]`——该 id 从未进入上下文（ch9:1418 只放 title） | 这是一类**可机械检测**的幻觉：答案中出现的每个证据 id，必须能在本次上下文的字面量里找到 | **`未落地`** → 应落到 `EVAL_CASES §3.3` 增设 **J-5**：证据 id 必须字面存在于该次上下文，不存在则该题记为失败而非扣分 |
| B-11 | **同一系统里三套 token 计数口径** | ch9:572（手写中英估算）、ch9:1423（`len//4`）、builder.py:345-353（tiktoken） | 预算守护建立在一个自己都不自洽的度量上；`rules/pitfalls.md` 第 9 条「判据看一个量、执行看另一个量」是同一个病的另一面 | ~~**`未落地`**~~ → **已落地 2026-08-26**（登记册 **`L-82`**，`rules/pitfalls.md` **第 9 条增补 (a)**）。**同 A-5，落地当日漏回标**，登记册状态直到 2026-08-26 第二轮才改。以下为原文，保留不改：应落到 `rules/pitfalls.md` 第 9 条增补：预算/阈值类度量全局单一口径，且需一条测试断言各调用点用的是同一函数 |
| B-12 | **过滤用裸相关性、排序用复合分**（ch9:363-364） | 新近性权重无法把低相关项救回来，权重设计在过滤这一步失效 | 打分与筛选用不同的量 = pitfalls 第 9 条 | ~~**`未落地`**~~ → **已落地 2026-08-26**（登记册 **`L-83`**，`rules/pitfalls.md` **第 9 条增补 (b)**）。**同 A-5，落地当日漏回标。** 另：登记册该行的「目的地」列原写 `Phase 3`——**那是阶段不是文档，无法落笔**，与 `L-76` 踩的是同一个坑，已就地更正为 `rules/pitfalls.md` 第 9 条。以下为原文，保留不改：与 B-11 合并落到 `rules/pitfalls.md` 第 9 条 |

### 11.C 小结

- **该借鉴 9 条**：已落地 4 条（A-1、A-2、A-4、A-7 方向 / B 栏另计），部分落地 1 条（A-3），**未落地 4 条**（A-5、A-6、A-8 的明文约束、A-9）。
- **该刻意不借 12 条**：已落地 5 条（B-1、B-2、B-3、B-4、B-9 方向），**未落地 7 条**（B-5、B-6、B-7 的判据、B-8、B-10、B-11、B-12）；
  另有 3 条属于「已落地但依据栏该补本章实证」（B-2、B-3、B-9）。
- **合计 21 条，其中 `未落地` 11 条。**

**最该先做的两条**（因为它们是本章最独特的产出，别处读不到）：
1. **B-10 → `EVAL_CASES §3.3`** —— **已落地 2026-08-24 为 `J-6`**（登记册 **`L-49`**；当时预留的号是 J-5，但 notes-part3 的负控制那条也要 J-5，已按登记册 §3.3 分配两个号，没有二选一）：ch9:1526 提供了一个完美的反面样本，
   而「证据 id 字面存在性」是**唯一一条不需要 LLM 判分就能跑的证据链检查**，
   与 `J-1`（判分者不得同源）天然互补。
2. **B-2 补进 `ARCHITECTURE §8.5` 的依据栏**：§8.5 目前只有 `truncator.py` 一个实证；
   本章又提供了三个（`note_id`、`source`、`ContextPacket.metadata`），
   **同一个病在一章里犯三次**，足以把 §8.5 从「一次观察」升级为「已验证的规律」。

---

## 12. 引用行号勘误表（2026-08-23 全量复核）

### 12.0 复核方法与语料来源

**本轮把正文 §1–§11 里出现的每一处 `ch9:行号` 与真实原文逐条比对，共 235 处引用（去重后 175 个行号/区间）。**

提取与比对命令（本次会话实跑；**必须只取 §1–§11，即本文第 1125 行之前**——
本 §12 自身含大量 `ch9:` 引用，连它一起数会重复计入）：

```
sed -n '1,1125p' references/hello-agents-ch09-context.md > /tmp/ch9body.md
grep -o 'ch9:[0-9]\+\(-[0-9]\+\)\?' /tmp/ch9body.md | wc -l            # -> 235   （出现次数）
grep -o 'ch9:[0-9]\+\(-[0-9]\+\)\?' /tmp/ch9body.md | sort -u | wc -l  # -> 175   （唯一行号/区间）

# 然后对每个唯一引用打印原文对应行（区间打印首尾两行），逐条人工比对
```

> 上面两个数是**改正之后**的现状值。改正只动行号数字、不增删引用，所以「235 处出现」在改正前后一致；
> 「唯一值」因个别行号被改到与既有引用重合/分离而会有 ±1 级别的浮动，不影响下表的逐条结论。

**语料来源说明（重要，因为路径变了）**：
上一轮记录的语料路径 `…/scratchpad/ha_src/docs/chapter9/` **本轮打开时是空目录**
（`ha_src/.git` 只剩 `objects/pack/` 与空的 `info/`，`git status` 报 `not a git repository`）。
本轮改从同一 scratchpad 下**完整的书仓克隆** `ha_fw` 取回原文：

```
git -C ha_fw rev-parse HEAD                      # -> 45dd84e626a91997294ac8d4d44f18b29a411c6e
git -C ha_fw ls-tree HEAD docs/chapter9/
# 100644 blob 017ad2c…  docs/chapter9/Chapter9-Context-Engineering.md        （英文版，2812 行）
# 100644 blob 311817b…  docs/chapter9/第九章 上下文工程.md                    （中文版，2819 行）
git -C ha_fw cat-file -p 311817b… | wc -l        # -> 2819
```

`45dd84e` 与 **2819 行**均与本文开头声明的基准一致，**语料同一性成立**，行号可比。
比对用的是**中文版** `第九章 上下文工程.md`（与本文正文一致），不是英文版。

### 12.1 结论

| 类别 | 数量 |
|---|---:|
| 引用出现总数（§1–§11） | 235 |
| 唯一行号/区间 | 175 |
| **A 类：所引原文不在所写行上（已就地改正）** | **10 类问题 / 改写 12 处引用字符串**（A-8 在 3 个小节各出现一次） |
| **B 类：区间越界或收窄，被引原文仍在或紧邻（已就地收紧）** | **7 类问题 / 改写 7 处** |
| **C 类：原文根本找不到（须写「未找到」）** | **0** |
| 本次未作改动、复核无误的唯一引用 | **157**（= 175 − 被改动的 18 个唯一行号/区间） |

**C 类为 0**：本轮**没有出现任何一处「引了但原文找不到」**。
10 处 A 类全部是**行号偏移**，被引的那句话/那行代码在原文里确实存在，只是位置不同；
**没有任何一条结论因为改行号而失效**。

> 补记一处**未改**的：本文 §9-b 第 2 点写「六种平级类型……（ch9:970、1558-1563）」，
> 其中 `ch9:1558-1563` 只列出 5 种（`task_state / conclusion / blocker / action / reference`，**无 `general`**），
> 六种齐全的是 `ch9:970`。两个行号都指向正确段落，**保留原样**，此处仅作说明。

### 12.2 A 类：所引原文不在所写行上（10 条，已改）

| # | 所在节 | 原写作 | 实为 | 该行号上实际是什么 | 被引原文是否仍成立 |
|---|---|---|---|---|---|
| A-1 | §1 | `ch9:33` | **`ch9:40`** | `ch9:33` 是图 9.1 的标题行 `<p>图 9.1 Prompt engineering vs Context engineering</p>` | **成立**。「上下文工程是提示工程的自然演进 / 在推理阶段策划与维护『最优的信息集合（tokens）』」原句在 `ch9:40` |
| A-2 | §1 | `ch9:36` | **`ch9:42`** | `ch9:36` 是「本节将探讨正在兴起的上下文工程，并给出一个……精炼心智模型。」 | **成立**。「系统指令、工具、MCP（Model Context Protocol）、外部数据、消息历史等」在 `ch9:42` |
| A-3 | §1 | `ch9:38` | **`ch9:44`** | `ch9:38` 是小标题 `<strong>上下文工程 vs. 提示工程</strong>` | **成立**。「从持续扩张的『候选信息宇宙』中，甄别哪些内容应当进入有限的上下文窗口」在 `ch9:44` |
| A-4 | §2.2 | `ch9:69` | **`ch9:67`** | `ch9:69` 是同一条 bullet 的子项「- 对错误鲁棒；」 | **成立**。「工具定义了智能体与信息/行动空间的契约」在 `ch9:67`（该 bullet 的首行） |
| A-5 | §2.2 | `ch9:75` | **`ch9:73`** | `ch9:75` 是「总的指导思想是：信息充分但紧致。如图9.2所示……」 | **成立**。「示例（Few-shot）……精挑细选一组多样且典型的示例」在 `ch9:73` |
| A-6 | §3.1 | `ch9:137` | **`ch9:133`** | `ch9:137` 是分区清单里的 `` - `[Task]`：当前需要完成的具体任务 `` | **成立**。「统一入口：将『获取(Gather)- 选择(Select)- 结构化(Structure)- 压缩(Compress)』抽象为可复用流水线」在 `ch9:133` |
| A-7 | §4.1 | `ch9:262-269、265-272` | **`ch9:258-269`（记忆支）、`272-284`（RAG 支）** | `265-272` 横跨记忆块尾部与 RAG 块首部，**不对应任何完整的 try/except** | **成立**。两个 `try/except` + `print` 分别在 `258-269` 与 `272-284`；文中单独引的 `ch9:269`（记忆 print）与 `ch9:284`（RAG print）**本来就是对的** |
| A-8 | §6.6 / §10 D-4 / §11 B-11（3 处） | `ch9:1428` | **`ch9:1423`** | `ch9:1428` 是 `"note_id": note['note_id']` | **成立**。`token_count=len(content) // 4,  # 简单估算` 在 `ch9:1423`。**注意 §6.4 里引 `ch9:1428` 说 `note_id` 赋值的那几处是对的，不改**——错的只有把 1428 当成 `len//4` 出处的那 3 处 |
| A-9 | §7 | `ch9:1638` | **`ch9:1601-1608` + `ch9:1641`** | `ch9:1638` 是场景 1 代码块里的 `head -n 1 data/sales.csv \| tr ',' '\n'` | **成立**。`rag_tool.add_document("./project/**/*.py")  # 耗时、占用大量存储` 在 `ch9:1603`，`find`/`grep`/`head` 三条对照在 `ch9:1606-1608`，「需要实时、轻量级的文件系统访问，**而不是预先索引和向量化**」在 `ch9:1641` |
| A-10 | §9-c | `ch9:31` | **`ch9:33`** | `ch9:31` 是 `<div align="center">` | **成立**。图 9.1 标题「Prompt engineering vs Context engineering」在 `ch9:33`。（同句里的 `ch9:79`=图 9.2 标题**原本就对**） |

### 12.3 B 类：区间越界或收窄（6 条，已改）

这一类不影响结论，改的是**区间边界**——原区间要么切进了下一个条目，要么没盖住被引的那句。

| # | 所在节 | 原写作 | 改为 | 理由 |
|---|---|---|---|---|
| B-1 | §2.2 | `ch9:62-67` | `ch9:62-65` | 「系统提示」bullet 实为 62-65；66 空行，67 已是「工具」条 |
| B-2 | §2.2 | `ch9:67-74` | `ch9:67-71` | 「工具」bullet 实为 67-71；72 空行，73 已是「示例（Few-shot）」条 |
| B-3 | §2.4 | `ch9:119-124` | `ch9:117-121` | 「方法取舍可以遵循以下经验法则：」在 117，三条法则在 119-121；123 是另一段结语，不属于法则 |
| B-4 | §3.1 标题 | `ch9:135-146` | `ch9:133-145` | 四条设计目标从 133（统一入口）起、到 145（最小规则）止；135 只是第 2 条 |
| B-5 | §6.1 | `ch9:796` | `ch9:798` | 796 是小标题「（1）为什么需要 NoteTool?」；「MemoryTool 主要关注对话式记忆……NoteTool 填补了这个 gap」在 798-800 |
| B-6 | §9-b 第 1 点 | `ch9:497-547` | `ch9:497-544` | `_compress` 函数体止于 544；546 起已是 `_truncate_text` |
| B-7 | §10 D-3 | `ch9:396-398` | `ch9:396-407` | 该格同时断言「`set(...split())`」**与**「Jaccard `∩/∪`」：split 在 396-398，`intersection`/`union`/除法在 403-407。**正文 §开头第 29 行的 `ch9:396-398` 只断言 split，成立，不改** |

（表内 7 行即 7 类独立改动。注意 B-7 只改 §10 D-3 那一处；本文开头第 29 行同样写 `ch9:396-398`，但那句只断言 `.split()`，**成立，保持原样**。）

### 12.4 复核确认无误的关键引用（抽样列举）

下列是本文结论最吃重的引用，**逐条核对过原文，全部命中**，列出来是为了让复核者不必重跑全表：

- `ch9:8` `pip install "hello-agents[all]==0.2.8"` ✓
- `ch9:13-15` 三个新增组件清单（13 ContextBuilder / 14 NoteTool / 15 TerminalTool），**清单里确实没有 truncator / history / token_counter** ✓
- `ch9:48` context rot ✓ ｜ `ch9:52` `\(n^2\)` + 训练分布 ✓ ｜ `ch9:54` 「性能梯度，而非『悬崖式』崩溃」 ✓
- `ch9:87` JIT 上下文 / 轻量化引用 ✓ ｜ `ch9:89` `tests/test_utils.py` vs `src/core/test_utils.py` ✓
- `ch9:145` 「不引入来源/优先级等分类维度」 ✓（本文与 D-003 的正面冲突点，**行号无误**）
- `ch9:349-351`（`== 0.5` 才重算）、`ch9:357-360`（复合分）、`ch9:363-364`（裸相关性过滤）✓
- `ch9:379` `break` ✓ ｜ `ch9:387` 「可以替换为向量相似度计算」 ✓ ｜ `ch9:396` 「简单实现,可以使用更复杂的分词器」 ✓
- `ch9:458-466`（`_structure` 只读 `metadata["type"]`）、`ch9:479` `[Evidence]`、`ch9:483` `[Context]`、`ch9:486` `[Output]` 一行版 ✓
- `ch9:535` / `ch9:537` / `ch9:538` / `ch9:561` / `ch9:563-577` / `ch9:572` ✓（§4.4 全节行号无误）
- `ch9:602` `min_relevance=0.2` ✓ ｜ `ch9:637` 中文查询 ✓ ｜ `ch9:294` `relevance_score=0.6` ✓
- `ch9:933` / `ch9:940` / `ch9:949`（「完整性校验」空头支票）/ `ch9:980`（`len(self.index)` 参与 id）/ `ch9:1310`（`del` 让长度变小）✓
- `ch9:993` → `ch9:1001` → `ch9:1136` → `ch9:1142`（书稿独有的 `file_path` KeyError 链）✓ **四个行号全部命中**
- `ch9:1418`（只放 title）/ `ch9:1425-1429`（写入 `note_id`）/ `ch9:1468`（系统指令要求写来源）/ `ch9:1526`（答案引用了上下文里不存在的 id）✓
  —— §6.4「本章最有价值的一处发现」所依赖的**四个行号全部命中**，该结论不受本次勘误影响
- `ch9:1649`（「只允许安全的只读命令，完全禁止任何可能修改系统的操作」）/ `1649-1673` / `1678-1697` / `1698-1712` / `1713-1727` / `1729` ✓
  —— §7.1 四层安全机制的区间**逐条命中**
- `ch9:1690` `cat /etc/passwd` 的拒绝示例 ✓ ｜ `ch9:1740-1774` `_execute_command` 全文 ✓ ｜ `ch9:1742-1751` `subprocess.run(..., shell=True, ...)` ✓
- `ch9:1941` `find -exec` ✓ ｜ `ch9:2000` `git log --oneline -10` ✓ ｜ `ch9:2006-2020` / `ch9:2012` `"source": "terminal"` ✓
- `ch9:2043` / `2504` / `2518` / `2551-2553` / `2562` / `2566`（9.6.4 编造演示的六个数字断言）✓ **全部命中**
- `ch9:2719-2737` `generate_report()` ✓ ｜ `ch9:2746` 自相矛盾的扩展方向 ✓ ｜ `ch9:2770` 「安全第一」✓
- `ch9:2792` / `2798` / `2799` / `2805`（习题与正文对不上的四处）✓ **全部命中**
- 本文正文里嵌在代码块中的行内注释 `# ch9:269`、`# ch9:379`、`# ch9:538` ✓ 三处均命中

### 12.5 这次勘误本身的教训

10 条 A 类里，**7 条的错误行号落在 ch9 的前 140 行**
（A-1/A-2/A-3/A-4/A-5/A-6 出自本文 §1–§3.1，A-10 出自 §9-c 引的图 9.1 标题），
而 ch9 的前 140 行几乎全是**散文，没有代码**。
`ch9:140` 之后、有代码的段落（本文 §4 起）行号命中率接近 100%——
因为代码行有唯一可 `grep` 的字面量（`break`、`text[:max_chars]`、`"note_id": note['note_id']`），
写的时候是搜出来的；而散文段落只能靠「读到第几段」记位置，**偏移全部发生在这里**。

→ **已落地 2026-08-27**（登记册 **`L-7`**，`references/README.md` **硬规则第 5 条 (a)**）。
**目的地与本行原写的不同**：本行原写 `rules/failure-modes.md`，登记册写的是
`references/README.md`——**按登记册落**，理由是这条要在「写产物的那一刻」被读到，
而 `references/README.md` 正是写产物前会翻的那份；`failure-modes.md` 记的是事故本身。
（这一条**确实也满足** `failure-modes.md` 2026-08-27 新增的三条准入条件
——subtle / systemic / costly 全中——是否另立一条 `F-9`，**留给操作者裁决**，
本轮不代拍：同一条规则落两处会制造 `D-009` 禁止的第二个权威落点。）
另：同表 B-9 的落地点也写 `references/README.md` 硬规则第 5 条，
已一并落成第 5 条 (b)，**但它在登记册里没有对应的 `L-nn` 行**（归并时并进了相邻条目）。
以下为原文，保留不改：可回填到 `rules/failure-modes.md` 的一条：
**引用散文时必须同时贴一段可 `grep` 的原文字面量，不能只写行号。**
本文 §1–§2 若当初每条都带上原句的三五个字，这 7 条偏移在写作当时就会自己暴露；
现在能被查出来，靠的正是那些**带了原文的**条目（§12.4 抽样列的那批）——它们一条都没错。

→ 与本项目的对应：这就是 `ARCHITECTURE §8.5` 说的「证据指针必须被下游强制消费」的**同一个道理**——
一个**无法被独立核验**的指针（只有行号、没有内容）等于没有指针，
它的正确性完全寄托在「写的人当时记对了」，而这恰恰是本次要复核的东西。
