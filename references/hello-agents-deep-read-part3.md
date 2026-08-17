# Hello-Agents 深读 part3 —— 补齐未读章节

> 读取日期：2026-08-17
> 语料：`scratchpad/ha_md/chNN_zh.md`（各章转好的 markdown）。行号均指该目录下 `_zh` 文件的行号。
> 本文件**边读边追加**。下面「读到什么程度」表随读随更新。
>
> 关切不是读书笔记，而是三个针对 finaudit-agent 的检查项：
> - **Q1** 「声称的结果」与「可核验的产物」是否一致
> - **Q2** 是否把「失败/无法判断」静默转成某个正常值
> - **Q3** 是否有「看起来可追溯，实际不可复核」的机制
>
> 框架源码：`scratchpad/hello-agents/` 是空的 stalled clone（只有 `.git`，无 commit），
> **本轮所有断言只基于书稿正文里贴出的代码**，不基于框架实现。凡是正文没贴的实现细节，一律标注为不可核验。

---

## 1. 读到什么程度（逐章逐节自报）

| 章 | 范围 | 本轮读了 | 状态 |
|---|---|---|---|
| Ch13 智能旅行助手 | L1–1581（全章） | 全文逐行 | ✅ 读完 |
| Ch15 构建赛博小镇 | L1–1899（全章） | 全文逐行 | ✅ 读完 |
| Ch16 毕业设计 | L1–1011（全章） | 全文逐行 | ✅ 读完 |
| Ch14 自动化深度研究智能体 | L1–2152（全章） | 全文逐行 | ✅ 读完 |
| Ch3 语言模型与 Transformer | L1–1022（全章） | — | ⏳ |
| Ch7.2 | — | — | ⏳ |
| Ch8.2 | — | — | ⏳ |
| Ch9.6.3 | — | — | ⏳ |
| Ch10.5 | — | — | ⏳ |
| Ch4.3 Plan-and-Solve | — | — | ⏳ |
| Ch10.3 A2A / 10.4 ANP | — | — | ⏳ |
| Ch1 / Ch2 / Ch5 / Ch6 剩余 | — | — | ⏳ |

---

## 2. 逐章发现

### 第十三章 智能旅行助手（全章 1581 行，已读完）

章节主题：用 4 个 SimpleAgent + 高德 MCP + Unsplash，做一个 FastAPI + Vue3 的旅行规划 Web 应用。
结构：13.1 架构 / 13.2 Pydantic 数据模型 / 13.3 多智能体协作 / 13.4 MCP 集成 / 13.5 前端 / 13.6 功能实现 / 13.7 结语。

#### Q1：声称与可核验产物不一致

**① 同一章内 `SimpleAgent` 的构造签名自相矛盾，且有裸语法错误（L568 vs L800）。**

L565–571（13.3.3 协作流程）：

```python
self.attraction_agent = SimpleAgent(name="景点搜索"prompt=ATTRACTION_PROMPT)
self.weather_agent = SimpleAgent(name="天气查询", prompt=WEATHER_PROMPT)
```

L800–804（13.4.3 共享 MCP 实例）：

```python
self.attraction_agent = SimpleAgent(
    name="AttractionSearchAgent",
    llm=self.llm,
    system_prompt=ATTRACTION_AGENT_PROMPT
)
```

两处差异：(a) L568 `name="景点搜索"prompt=` 缺逗号，是 `SyntaxError`，这行 Python 无法解析；
(b) 参数名一处叫 `prompt`、一处叫 `system_prompt`；(c) 一处不传 `llm`、一处传。
**结论：13.3.3 那段"协作流程"代码没有被执行过。** 正文把它写成完整可运行的 `TripPlannerAgent` 实现，但它连语法都过不了。
对读者而言这是"看起来是产物、实际是伪代码"的典型。

**② 工具名前缀不一致（L495/L515 vs L1436）。**
13.3.2 里工具一律带 `amap_` 前缀（`amap_maps_text_search`、`amap_maps_weather`），
L723–724 也印证 `auto_expand` 后的工具名是 `['amap_maps_text_search', 'amap_maps_weather', ...]`；
但 L1436 建议"调用 `maps_staticmap` 工具"，无前缀。
这个不是致命错，但说明正文里的工具名没有跟同一份工具清单对过。

**③ "16 个工具"这一具体数字不可核验（L715、L722–724）。**
正文两处断言"Agent 却获得了 16 个工具"，但工具清单（表 13.1、图 13.7）以图片形式给出，
markdown 语料里只有 `<img src=...13-table-1.png>`，没有文本清单。
`print(list(agent.tools.keys()))` 的输出被写成 `['amap_maps_text_search', 'amap_maps_weather', ...]` —— 用省略号截断，
没有一处能核对到 16 这个数。这是"具体数字 + 不可核验产物"的组合。

#### Q2：失败/无法判断被静默转成正常值 —— 本章命中三处，其中一处严重

**① 温度解析失败 → 静默返回 0（L360–369）。这是 Ch12「解析失败静默归入 Tie」的同类，且更隐蔽。**

```python
@field_validator('day_temp','night_temp',mode='before')
def parse_temperature(cls,v):
    """解析温度字符串："16°C" -> 16"""
    if isinstance(v,str):
        v = v.replace('°C','').replace('℃','').replace('°','').strip()
        try:
            return int(v)
        except ValueError:
            return 0  # 容错处理
    return v
```

`0` 是一个**完全合法的摄氏温度**。下游（前端天气卡片、PlannerAgent 的行程建议）无法区分
「今天 0℃」与「上游返回了 `--` / `暂无数据` / `16~20°C` 这类解析不了的串」。
正文注释直接写"容错处理"，把丢失信息当成了鲁棒性。
**这是本轮在 Ch13 找到的最干净的 Q2 命中。**

**② 图片检索失败 → 返回空列表（L872–874），下游变成 `image_url = None`（L897–901）。**

```python
except Exception as e:
    logger.error(f"搜索图片失败: {e}")
    return []
```

这里捕获的是**裸 `Exception`**，把网络超时、401 鉴权失败、配额耗尽、JSON 结构变化全部压成同一个空列表。
`get_photo_url` 返回 `None`，`attraction.image_url` 保持 `None`，前端就是不显示图片。
危害比温度那处小（`image_url` 本就是 `Optional`），但失败原因只进了日志、没有进数据，
产物本身不携带"这里失败过"的痕迹。

**③ 预算缺失 → 前端整块隐藏（L1311）。**
`v-if="tripPlan.budget"`。正文自己解释："如果 LLM 没有生成预算信息，这个卡片就不会显示。
这体现了前端对数据的容错处理。"
用户看到的是"这个应用没有预算模块"，而不是"预算这次没算出来"。
**把缺失渲染成不存在**，是 finaudit 绝对不能抄的做法。

**④（次要）导出时静默丢地图（L1434–1441）。**
这一处正文是**坦诚**的："我们采用了简化方案，在导出时暂时隐藏地图部分，只导出行程的文字内容和景点信息。
虽然这不是最理想的方案，但可以保证导出功能的可用性。"
但坦诚只写在书里，导出的 PDF 本身不带"地图已省略"的标记。产物与文档分离。

#### Q3：看起来可追溯、实际不可复核

**① 预算是 LLM 直接编的数字，与 `Attraction.ticket_price` 没有任何勾稽关系。这是本章对 finaudit 最要命的一处。**

- `Budget` 模型（L321–328）五个字段 `total_attractions / total_hotels / total_meals / total_transportation / total` 全是 `int`，**没有任何 validator**。
- 预算的产生方式：写在 PlannerAgent 的提示词里让 LLM 输出（L1252–1272），要求是自然语言的
  「7. 包含预算信息,根据景点门票、酒店价格、餐饮标准和交通方式估算」。
- 正文 L1275 举例说"故宫(门票 60 元)、天坛(15 元)、颐和园(30 元)，那么景点门票总费用就是 105 元"，
  **但全章没有任何一行代码做这个求和**。`Attraction.ticket_price`（L291）确实存在，
  却从未被读取用于计算 `Budget.total_attractions`。
- `total` 同理：示例值 `180+1200+480+200 = 2060`（L1261–1266）恰好对得上，
  但没有任何代码或校验强制 `total == 四项之和`。LLM 给出 `total: 9999` 也会原样通过 Pydantic 并渲染成红色大字（L1298–1303）。

前端呈现方式（L1280–1306）用 `a-statistic` 分四栏 + 分隔线 + 总计，**外观完全是一张可核对的费用明细表**，
但它的四个分项和总计之间、分项与底层景点数据之间，都没有约束。
**"看起来可复核的明细表，实际是不可复核的一段生成文本"** —— 与本项目 Ch14 `source_urls` 的问题同构。

**② 加载进度条是纯前端假进度（L1107–1116、L1317、L1328–1337）。**

```javascript
// 模拟进度更新
const progressInterval = setInterval(() => {
  if (loadingProgress.value < 90) {
    loadingProgress.value += 10
    if (loadingProgress.value <= 30) loadingStatus.value = '🔍 正在搜索景点...'
    else if (loadingProgress.value <= 50) loadingStatus.value = '🌤️ 正在查询天气...'
    else if (loadingProgress.value <= 70) loadingStatus.value = '🏨 正在推荐酒店...'
    else loadingStatus.value = '📋 正在生成行程计划...'
  }
}, 500)
```

状态文案精确到"正在查询天气"这种**阶段级别的具体断言**，但驱动它的只有一个 500ms 的定时器，
与后端真实执行到哪一步毫无关系。正文 L1317 自己承认"现在只是模拟进度"。
后果：如果 WeatherQueryAgent 实际失败了，进度条照样会显示"🌤️ 正在查询天气..."然后走到"✅ 完成！"（L1343）。
**这是一条会主动说谎的"执行痕迹"。**

**③ 提示词里的「必须使用工具，不要编造信息」没有任何执行侧保障（L501–504）。**

```
**重要:**
- 必须使用工具搜索,不要编造信息
```

全章没有任何机制检查 Agent 是否真的产生过 `[TOOL_CALL:...]`、工具是否真的返回过内容。
如果 LLM 直接凭记忆列出"故宫、天安门、颐和园"，`_build_planner_query`（L607–637）会原样把这段
自然语言塞进 PlannerAgent 的 `**景点信息:**` 段落，后续流程完全无法区分它来自高德 API 还是来自模型记忆。
**约束写在提示词里 = 没有约束。** 这条和本项目 `rules/failure-modes.md` 里「只有真实字段能诚实触发时才声明 flag」是同一件事的两面。

**④ 坐标只做范围校验，不做归属校验（L270–274 + L1194–1203）。**
`Location` 校验 `-180 ≤ lng ≤ 180`、`-90 ≤ lat ≤ 90`。
LLM 编造的坐标只要落在这个范围（几乎必然），就会被 Pydantic 放行，并被 `AMap.Marker` 画到地图上（L1196–1201）。
地图上有个点 ≠ 这个点是真的。**可视化会给伪造数据背书。**

#### 本章还值得记的两点（非缺陷）

- **13.4.3 共享 MCP 实例（L774–822）**：三个 Agent 共享同一个 `MCPTool`，理由是避免起 3 个 server 进程、
  避免超 API 速率限制。这个模式对 finaudit 有直接用处（多个分析 Agent 共享同一个数据访问句柄，
  才有唯一的调用计数与审计点）。
- **13.4.1 为什么不直接调 API（L644–673）**：给了四条理由，其中"Agent 无法自主调用"和"工具管理混乱"两条成立；
  但"响应解析困难"这条其实并没被 MCP 解决——MCP 服务器返回的仍是一段自由文本（L756–768 的 `content[0].text`
  是 `"找到以下景点：\n1. 故宫博物院 - 地址：..."` 这种人读格式），
  下游还是得靠 LLM 去解析。**MCP 在这里把结构化解析问题往后推了一层，没有消除它。**

---

### 第十五章 构建赛博小镇（全章 1899 行，已读完）

章节主题：Godot 4.5 前端 + FastAPI 后端 + HelloAgents SimpleAgent 做 AI NPC，含记忆系统、好感度系统、批量对话生成。

> 前置声明：本章正文贴的是**代码摘录**，仓库实际代码不可核验（`scratchpad/hello-agents/` 是空 clone）。
> 下面所有"对不上"的断言，**只针对正文印出来的这几段代码**，不是对仓库的断言。
> 但正文把这些代码呈现为"实现"，并在 L1822 宣告"至此，前后端通信的所有功能都已实现"，所以这个层面的核对是成立的。

#### Q1：声称与可核验产物不一致 —— 本章是三章里最严重的

**① 前后端 API 契约至少五处对不上；照正文印出来的代码，这个应用一次对话都跑不通。**

后端（15.4.2，L762–811）：

```python
@app.post("/dialogue", response_model=DialogueResponse)
async def dialogue(request: DialogueRequest):
    ...  # 用 request.npc_id / request.player_message / request.player_name
    return DialogueResponse(npc_reply=reply, affinity_level=..., affinity_score=...)
```

前端（15.6.1，L1488–1532）：

```gdscript
func send_chat(npc_name: String, message: String) -> void:
    var data = {"npc_name": npc_name, "message": message}
    ...
    if response.has("success") and response["success"]:
        var npc_name = response["npc_name"]
        var msg = response["message"]
```

逐条比对：

| # | 位置 | 不一致 | 后果 |
|---|---|---|---|
| 1 | L1490–1493 vs L765/787 | 请求体发 `npc_name`/`message`，后端要 `npc_id`/`player_message`/`player_name` | FastAPI 返 422，`player_name` 前端根本没发，而它是好感度的主键（L555 `key = f"{npc_id}_{player_name}"`） |
| 2 | L1526–1532 vs L807–811 | 前端读 `success`/`npc_name`/`message`，后端返 `npc_reply`/`affinity_level`/`affinity_score` | `response.has("success")` 永远为 false → 走 else 分支 `chat_error.emit("对话失败")`。**即使后端完全正常，玩家看到的也永远是"对话失败"** |
| 3 | L1719 vs L1488 | `dialogue_ui.gd` 调 `api_client.send_chat_request(...)`，`api_client.gd` 定义的是 `send_chat(...)` | Godot 运行时报 "Nonexistent function"。**前端自己内部就对不上** |
| 4 | L1633–1643 vs L1596 | `dialogue_ui.gd` 的 `_ready()` 只 connect 了三个按钮信号，**从未 connect `api_client.chat_response_received`**；但 L1596 正文明说"对话系统监听 `chat_response_received` 信号来接收 NPC 回复" | `on_chat_response_received`（L1721）永不触发，NPC 回复永不上屏 |
| 5 | L1207 vs L1633–1643 | `player.gd` 用 `call_group("dialogue_system", "start_dialogue", ...)` 唤起对话，但全章没有任何一处 `add_to_group("dialogue_system")`（player.gd 有 `add_to_group("player")` L1106，npc.gd 有 `add_to_group("npcs")` L1290） | 按 E 键什么也不会发生 |
| 6 | L1562 vs L746 | 前端 NPC 状态回调判 `response.has("dialogues")`，后端 `/npcs/status` 返 `{"npcs": [...]}` | 背景对话气泡永不更新 |
| 7 | L1789–1807 vs L866–893 | `main.gd` 按中文名 `"张三"/"李四"/"王五"` 分发；后端 `state_manager` 用 `npc_id`（`zhang_san` 等）建索引，而 L462–463 的 `update_npc_background_dialogue(npc_name, ...)` 又用中文名 | 后端状态表存在**两套互不相通的键空间** |

**这不是"摘录省略"能解释的**：第 3、4、5 条完全发生在前端内部两个文件之间，第 2 条是响应字段名的正面冲突。
正文 L86 标题是"快速体验：**5 分钟运行项目**"，L1822 宣告"所有功能都已实现"。
**这是本轮找到的与 Ch12「正文 4.2/5.0 vs 产物 3.32/5.0」同级别的问题。**

**② `RelationshipManager.get_affinity()` 被调用两次，但类定义里没有这个方法。**
调用点：L780–783（`/dialogue` 路由第 4 步）、L835（`/affinity/{npc_id}/{player_name}` 路由）。
类定义（L525–595）只有 `__init__` / `analyze_sentiment` / `update_affinity` / `get_affinity_level`。
`AttributeError`。

**③ 日志声称记录的字段，超出实现能产生的字段（L153 vs L967–981）。这是本章最像 Ch12 的一处。**

L153 正文原话（15.1.3 快速体验）：

> 日志文件会记录每次对话的详细信息，包括：当前好感度值、**检索到的相关记忆**、NPC 的回复、
> **好感度变化量(+2.0、+3.0 等)**、**变化原因(友好问候、正常交流等)**以及**情感分析结果(positive、neutral 等)**。

L967–981 的 `log_dialogue` 实际写进日志的：

```
NPC / 玩家 / 玩家消息 / NPC回复 / 好感度: {level} ({score}/100) / 互动次数
```

对照：
- **"检索到的相关记忆"** → 没有。`log_dialogue` 的参数里就没有记忆字段。
- **"好感度变化量"** → 没有。只写了变化**后**的 score，delta 从未落盘。
- **"变化原因(友好问候、正常交流等)"** → 没有，且**产生不出来**：`analyze_sentiment`（L532–550）返回的是一个 `int`，全程不产生任何原因文本。
- **"情感分析结果(positive、neutral 等)"** → 没有，且**产生不出来**：同上，返回 int，不存在 positive/neutral 这种标签。
- 连数字格式都对不上：L153 写 `+2.0、+3.0`（浮点），代码的档位是 `+5 / +2 / -3`（int，L539–541），**没有 +3 这一档**。

**正文把一份根本不存在的日志结构，写成"你可以在 `backend/logs/dialogue_YYYY-MM-DD.log` 里查看"的操作指引。**
对 finaudit 的对应风险：**在文档里描述证据链字段，而不是从证据链本身导出文档。**

**④ 「记忆系统」在实际对话路径上是断的（L607–638 vs L786）。**
15.2.1 的 `create_npc_agent`（L181–212）**带** `memory_manager=memory_manager`。
15.3.3 的 `create_npc_agent_with_affinity`（L607–638）**不带任何 memory_manager**：

```python
agent = SimpleAgent(
    name=name,
    llm=llm,
    system_prompt=system_prompt
)
```

而 `/dialogue` 路由走的是 L786 `agent_manager.get_agent(request.npc_id, affinity_info["level"])` —— 传了 level，
即需要按好感度重建提示词，对应的正是那个**不带记忆**的构造函数。
`NPCAgentManager.get_agent` 的实现正文没贴，**这一步我无法核验**，但正文贴出的两个构造函数里，
被好感度路径用到的那个确实没有记忆。
而 15.7.1 回顾（L1841）宣称"我们实现了两层记忆系统…通过向量数据库的语义检索，NPC 可以回忆起之前讨论过的话题"。

**⑤ 15.2.3 展示的记忆检索流程，在实际路由里没有被调用（L288–313 vs L439/L787）。**
L290–312 的 `process_dialogue` 手工做了三件事：取短期记忆、语义检索长期记忆、`agent.run(player_message, context=context)`。
但两条实际路由都是**裸调**：L439 `reply = agent.run(player_message)`、L787 `reply = agent.run(request.player_message)`，
不传 `context`，也不调 `process_dialogue`。**`process_dialogue` 是一个从未被引用的示意函数。**

**⑥ 语法错误与 API 不一致（同 Ch13 的模式）。**
- L334 `class NPCBatchGenerator：` —— **中文全角冒号**，`SyntaxError`。这段代码没被解释器碰过。
- L545 用 `self.llm.think([...])`，L354 用 `self.llm.invoke([...])` —— 同一个 `HelloAgentsLLM` 上两个不同的方法名。
  哪个对不可核验（框架源码取不到），但同章不统一本身就是证据。

**⑦ "成本降低到原来的 1/3"（L331）是一句没有产物支撑的性能断言。**
批量生成把 3 个 NPC 合成一次调用，省的是**请求次数**和重复的 system prompt；
3 个 NPC 的角色描述（L372–377）仍然全部进入 prompt，输出 token 也没少。
全章没有任何 token 计数、耗时测量或账单对照。这是"具体数字 + 零产物"。

#### Q2：失败/无法判断被静默转成正常值 —— 本章有一处比 Ch13 更糟

**① 情感分析解析失败 → 静默返回 +2 分，而且是正分（L545–550）。**

```python
response = self.llm.think([{"role": "user", "content": prompt}])
try:
    score_change = int(response.strip())
    return max(-3, min(5, score_change))
except:
    return 2  # 默认中立
```

三件事叠在一起：
1. **裸 `except:`**，连 `Exception` 都不写，会吞掉 `KeyboardInterrupt` / `SystemExit`。
2. 失败值 `2` 是"中立"档的**正分**。LLM 只要回一句 `"中立(+2分)"` 而不是纯数字 `2`，`int()` 就抛异常 → 返回 2。
   **即：解析持续失败的系统，好感度会稳定地一路涨到"挚友"，与玩家实际说了什么无关。**
3. 与 Ch12 的「解析失败静默归入 Tie」是同一个错误的两个实例，但这里更坏：Tie 至少是中性的，
   这里的默认值会**单向推动**被测量的指标。

**「无法判断」被写成了一个会累积的正向证据。** 这是本轮全部三章里最该记住的一条。

**② `max(-3, min(5, score_change))` 掩盖越界（L548）。**
LLM 若返回 `50`，会被 clamp 成 5，不留任何"这次输出异常"的痕迹。截断即静默。

**③ 批量生成失败 → 只 print，NPC 保留旧对话（L466–467）。**

```python
except Exception as e:
    print(f"❌ 背景对话更新失败: {e}")
```

后台任务每 5 分钟跑一次，失败了玩家看到的是**上一轮的旧气泡**，与"这次没更新"不可区分。
另外 L360 `dialogues = json.loads(response)` 没有任何 try，正文 L404 却说
"LLM 会严格按照这个格式生成回复，我们只需要解析 JSON 就能获得所有 NPC 的对话"——把提示词约束当成了格式保证。

**④ 计数式成功日志（L465）。**

```python
print(f"✅ 背景对话更新完成: {len(dialogues)}个NPC")
```

如果 LLM 只返回了 2 个 NPC，这里打印 `✅ 背景对话更新完成: 2个NPC`，**带对勾**。
缺的那个 NPC 静默保留旧对话。**用"做了几个"冒充"做全了"**，没有与期望数（3）比对。

#### Q3：看起来可追溯、实际不可复核

**① 好感度分数是一条不可复核的累积量。**
`affinity_data` 是纯内存 `dict`（L529 `self.affinity_data = {}`），进程重启即清零，无持久化。
每次变化的 delta、依据、LLM 原始输出都不落盘（见 Q1-③）。
最终呈现给用户的只有一个 `score: 73 / level: 亲密`。
**要复核"为什么是 73"，唯一的信息源已经被丢掉了。** 这正是 finaudit 里"指标值 vs 指标推导路径"的反面教材。

**② 五级等级表看起来是硬规则，实际只影响一段自然语言提示词（L612–628）。**
`affinity_prompts` 把等级映射成 `"你把这位玩家当作朋友,愿意分享更多信息。回复详细热情。"` 这样的句子塞进 system prompt。
没有任何机制检验模型是否真的照做。L508 却说"只有达到一定好感度，NPC 才会分享某些特殊信息"——
**这是一个由提示词"建议"的访问控制，不是访问控制。** 与 Ch13 的「必须使用工具，不要编造信息」同类。

**③ 前端的 `print("[INFO] 收到NPC状态更新: ", dialogues.size(), "个NPC")`（L1564）** 同样是计数式确认，
且由于第 6 条契约不匹配（前端找 `dialogues` 键、后端给 `npcs` 键），这条日志实际永不打印——
**一条永远不会触发的"成功证据"。**

#### 本章值得借鉴的（少，但有）

- **NPC 忙碌锁 + `try/finally` 释放（L771–776、L817–819）**：check → set → try → finally reset。
  值得注意的是它在**单进程 asyncio 下确实是原子的**——L772 的检查与 L776 的置位之间没有 `await`，
  事件循环不会在这中间切走。但 L720–726 若改成 `uvicorn.run(..., workers=N)` 就立刻失效（状态在进程内存里）。
  finaudit 若要做"同一份报表同时只允许一个分析任务"，这个模式可用，但必须把状态挪出进程内存。
- **双输出日志（L945–965）**：console + 按日期分文件。结构本身没问题，问题全在**写什么**（见 Q1-③）。

---

### 第十六章 毕业设计：构建属于你的多智能体应用（全章 1011 行，已读完）

章节主题：毕业设计的选题指南、Git/GitHub 流程、README 与 Notebook 模板、PR 规范、一个示例项目（CodeReviewAgent）。
这一章几乎全是**模板与流程**，恰恰因此它决定了社区里几百个学生项目的质量下限。**它教出来的正是 Ch12/Ch15 那类问题。**

#### Q1：声称与可核验产物不一致

**① README 声称"可直接运行"，代码里的 key 是占位符（L764–767 vs L958）。**

Notebook 代码（L764–767）：

```python
os.environ["LLM_API_KEY"] = "your_api_key_here"
```

同一节的示例 README（L956–958）：

> **方式2: 直接在Notebook中设置**
> 项目已预配置ModelScope API,**可直接运行**。如需修改,编辑main.ipynb第1部分的配置代码。

而 16.6 的 import 块（L754–758）里**没有 `load_dotenv()`**，也没有 `dotenv` 的 import，
所以 `.env.example`（L739）在这条路径上完全没被读。硬编码的 `your_api_key_here` 是唯一来源 → 必然 401。
**"可直接运行"是一句会被第一次执行就证伪的断言。**

**② 同一章内两套互不兼容的 Tool 接口（L384–393 vs L773–814）。**

| | 16.4.3 模板（L372–393） | 16.6 示例（L755–814） |
|---|---|---|
| 导入 | `from hello_agents.tools import BaseTool` | `from hello_agents.tools import Tool, ToolParameter` |
| 基类 | `BaseTool` | `Tool` |
| 元数据 | 类属性 `name = "tool_name"` | `super().__init__(name=..., description=...)` |
| 签名 | `run(self, query: str) -> str` | `run(self, parameters: Dict[str, Any]) -> str` |
| 参数声明 | 无 | 必须实现 `get_parameters() -> List[ToolParameter]` |
| 挂载 | `agent.add_tool(CustomTool())`（L410） | `SimpleAgent(..., tool_registry=tool_registry)`（L883–888） |

**学生照 16.4.3 的模板写出来的工具，在 16.6 的写法里用不了，反之亦然。**
框架源码不可核验，所以我无法判断哪一套是对的（也可能两套都存在），
但一本教材在相隔 400 行的地方给出两套不兼容的接口而不加说明，读者只能靠试错。
（旁证：Ch13 L720 用的是第三种 —— `agent.add_tool(mcp_tool)` 挂一个 `MCPTool`。）

**③ `cd` 目录名对不上（L155 vs L158）。**

```text
（原文是一条 SSH 形式的 git clone 命令，clone 的仓库名为小写 hello-agents）
cd Hello-Agents
```

> 上面第一行**照抄原文会触发本仓库的 AC-10 扫描**（SSH 形式的 `用户@主机` 与邮箱同形），
> 故改为描述。这与 `PROGRESS.md` 里那次的处置一致：**举例改成描述，
> 不为了文档好写而放宽门禁规则。**

clone 出来的目录是 `hello-agents`。在 Linux 上 `cd Hello-Agents` 直接失败。
（Windows / macOS 默认大小写不敏感的文件系统上侥幸能过。）小错，但又一次说明命令没在 Linux 上跑过。

#### Q2：失败/无法判断被静默转成正常值 —— 本章有一处是「未检查 → 合规」

**① `StyleCheckTool` 把"我检查的两条都过了"输出成"符合 PEP 8 规范"（L816–842）。这是全书对 finaudit 最直接的反面教材。**

工具自述（L822）：`description="检查代码是否符合PEP 8规范"`
实际实现（L831–842）只查两件事：

```python
for i, line in enumerate(lines, 1):
    if len(line) > 79:
        issues.append(f"第{i}行:超过79个字符")
    if line.startswith(' ') and not line.startswith('    '):
        if len(line) - len(line.lstrip()) not in [0, 4, 8, 12]:
            issues.append(f"第{i}行:缩进不规范")

if not issues:
    return "代码风格良好，符合PEP 8规范"
```

- PEP 8 有几十条规则（命名约定、空行、import 顺序、运算符空格、行继续、比较写法……），这里覆盖了**两条**。
- 返回的却是无条件断言 **"代码风格良好，符合 PEP 8 规范"**。
- 更糟的是这句话会被喂给 LLM（system_prompt L867–880 要求"基于分析结果，提供详细的审查报告"），
  于是**最终的 `review_report.md` 里会出现一句由"工具"背书的"符合 PEP 8"**。

**「我没查的部分」被渲染成「合规」。** 这正是本项目要解决的"这个口径对不对"问题的镜像：
一个审计工具最不能做的事，就是把未覆盖范围报告成通过。

顺带，那两条规则本身的覆盖面也没有声明边界：
- Tab 缩进完全查不到（`line.startswith(' ')` 为 False）。
- 16 空格缩进查不到（被外层 `not line.startswith('    ')` 排除掉了）。
  外层条件实际把范围缩到"缩进 1–3 个空格"，内层的 `not in [0,4,8,12]` 是冗余判断。

**② `CodeAnalysisTool` 的失败被编码成与成功同型的字符串（L788–804）。**

```python
try:
    tree = ast.parse(code)
    ...
    return str(result)          # 成功：一个 dict 的 repr
except SyntaxError as e:
    return f"语法错误:{str(e)}"  # 失败：一句中文
```

这比 Ch13/Ch15 的静默转正常值**好**——失败至少是可读、可区分的。
但它仍把「是成功还是失败」的判定责任推给了下游 LLM：两者都是 `str`，没有结构化的 ok/err 标记。
另外只捕 `SyntaxError`，`ValueError`（源码含 null byte）、`RecursionError`（深度嵌套）会直接向上抛穿。

#### Q3：看起来可追溯、实际不可复核

**① 审查报告是 LLM 原始输出的直接 dump（L904–910）。**

```python
review_result = agent.run(f"请审查以下Python代码:\n\n```python\n{sample_code}\n```")
...
with open("outputs/review_report.md", "w", encoding="utf-8") as f:
    f.write(review_result)
```

报告里那些看起来最硬的断言（"第 47 行超过 79 个字符"）**是 LLM 转述工具输出之后的产物，不是工具输出本身**。
工具的原始返回值没有被单独留存，报告里的每条断言无法回指到"哪个工具、什么参数、原始返回是什么"。
行号漂移、条目虚构、漏转述，都没有任何检测手段。

**对 finaudit 的直接映射：报告不能是 LLM 输出的 dump。**
必须是「工具原始输出（含调用参数与哈希）」+「LLM 生成的叙述」两层，且叙述里的每个数字可回指到第一层。

**② 两份"清单"都是荣誉制（L456–468、L684–691）。**

```markdown
- [ ] 代码能够正常运行，没有报错
- [ ] 输出结果符合预期
- [ ] 处理了常见的异常情况
```

由提交者自己勾选，全章没有任何 CI、lint、smoke test 或自动校验。
**看起来是门禁，实际是自我声明。** Ch15 那个跑不通的前后端如果走这个流程，"代码能够正常运行"照样会被勾上。

**③ README 模板鼓励填一个没有产生过程的性能数字（L293–298 vs L426–431）。这是 Ch12 那个 4.2/5.0 问题的制度性来源。**

README 模板（L293–298）：

```markdown
## 📊 性能评估
如果有评估结果，展示在这里:
- 准确率:XX%
- 响应时间:XX秒
- 其他指标
```

同一章的 Notebook 结构模板（L426–431）：

```python
# ========================================
# 第6部分:性能评估（可选）
# ========================================

# 评估代码
# ...
```

**产生数字的代码是「可选」且留空的，展示数字的位置却是 README 的固定栏目。**
模板没有任何一处要求写明评估方法、样本量、判定标准或可复现脚本。
这就是"正文写 4.2/5.0，产物是 3.32/5.0"这类问题在制度上被允许发生的地方。

**④ 教学生把 API key 写进要提交到公开仓库的 notebook（L764–767 + L956–958）。**
虽然示例里的值是占位符，但**教的动作**是"在 main.ipynb 第 0 部分用 `os.environ[...] = ...` 设置密钥"，
且 README 把它列为并列的"方式 2"。而这份 `main.ipynb` 正是要 PR 进 `datawhalechina/hello-agents` 公开主仓的产物（L19–29）。
16.5.1 的提交流程是 `git add .`（L587）—— 一把全加。
`.gitignore`（L740）只在项目结构图里出现，全章没有给出它的内容，也没有任何一处提醒"提交前检查 notebook 里有没有真 key"。
**这是一条会导致密钥泄露的教学示范。**

#### 本章值得记的（正面）

- **16.4.5 大文件处理指南（L470–570）** 是全章最扎实的一节：明确的 5MB 上限、三套方案（外链 / 独立资源仓 / 示例数据）、
  以及"主仓库只放 `sample.csv`（<1MB）+ `demo_result.png`（<1MB）"的具体形态。
  这套"小样本进仓 + 全量数据外链"的规矩对 finaudit 直接可用：年报 PDF 体积大，
  应当只入库抽取后的结构化产物与少量 fixture，原始 PDF 走外部存储 + 哈希登记。

---

### 第十四章 自动化深度研究智能体（全章 2152 行，本轮读完 L1–2152）

> 上一轮已定的 `source_urls` 结论不重做。本节是**除该段之外**的全章通读。
> 章节主题：TODO 驱动的研究范式，三个 Agent（TODO Planner / Task Summarizer / Report Writer）
> + 两个工具（SearchTool / NoteTool）+ FastAPI SSE + Vue3。
> 全章标题一路是「实现代码」「核心代码」，14.7 小结逐条宣告"我们实现了…"。

#### Q3（先放最重的一条）：整套工具调用审计机制在本应用里**结构上不可能触发**

这是本章最该记住的发现，比 `source_urls` 更根本。

14.3.2 用整整一节（L738–835）论证为什么需要 `ToolAwareSimpleAgent`：

> 在深度研究助手中，我们需要记录每个 Agent 的工具调用情况，用于：1 调试 2 日志 3 分析 4 进度展示（L742–747）

14.7 小结（L2104–2112）再次宣告：

> 这个 Agent 具有工具调用监听能力……**记录所有工具调用，便于调试**。这个 Agent 已经集成到 HelloAgents 框架中。

但把三个服务的构造函数并排看：

| 服务 | 行号 | 是否传 `tool_registry` |
|---|---|---|
| `PlanningService` | L1135–1140 | **否** |
| `SummarizationService` | L1341–1346 | **否** |
| `ReportingService` | L1437–1442 | **否** |

三个 Agent 全部 `tool_registry` 缺省（=None）。而 14.5.4 开头 L1502 明确写了架构选择：

> 在这里我们没有采用往常一样的使得 simpleAgent 直接调用工具的形式，而是将 SearchTool 的执行结果**通过中间层**来返回给 Agent

即：搜索由 `SearchService` 在 Agent 之外执行，笔记由 `NotesService` 直接 `self.note_tool.run(...)`（L1017）调用。
**本系统里没有任何一个 Agent 会产生工具调用**，于是 `_execute_tool_call` 永不被调用，
`tool_call_listener` 永不触发，L822–827 那个 `_emit_event({"type": "tool_call", ...})` 永不发出。

旁证（前端侧）：`useResearch.ts` 的 `switch (data.type)`（L1960–1991）只处理
`progress / plan / task_summary / report / error / completed` —— **没有 `tool_call` 分支**。
而 L835 写着"所有 Agent 的工具调用都会被记录，并通过 SSE 推送到前端，实时显示给用户"。

**一个从设计上就收不到任何事件的观测机制，被当作系统的审计与调试能力写进正文和小结。**
对 finaudit 的映射：证据链机制必须有"本次运行产生了 N 条证据、N=0 即失败"的自检，
否则"我们有完整审计"和"我们的审计一条都没记到"在产物上完全同形。

#### Q3（续）：监听器本身的三个设计缺陷（L792–809）

```python
def _execute_tool_call(self, tool_name: str, parameters: str) -> str:
    parsed_parameters = self._parse_parameters(parameters)      # 独立再解析一次
    result = super()._execute_tool_call(tool_name, parameters)  # 真正执行用的是原始串
    if self._tool_call_listener:
        self._tool_call_listener({... "parsed_parameters": parsed_parameters, "result": result})
    return result
```

1. **日志里的参数不是执行时用的参数。** `parsed_parameters` 由本方法**另行解析一遍**得到，
   真正传给 `super()._execute_tool_call` 的是未解析的 `parameters` 原始字符串。
   两次解析若有任何差异（版本、容错分支、默认值填充），审计记录与实际执行就会分叉，
   且**永远不会被发现**，因为没有任何一方留存对方的值。
   **审计记录必须是执行路径上的同一个值，不能是旁路重算出来的。**
2. **失败的工具调用不留痕。** 监听器在 `super()` 返回**之后**才调用。工具抛异常 → 直接向上传播 →
   监听器不执行 → 事件流里没有这次调用。**这是一份只记成功的日志。**
3. `call_info` 只有 `agent_name / tool_name / parsed_parameters / result` 四个字段：
   没有时间戳、没有耗时、没有 call id、没有成功/失败标志。无法排序、无法配对、无法判定结果好坏。

#### Q1：声称与可核验产物不一致

**① 前端 `EventSource` 永远连不上后端。方法不匹配，且路由名与架构图三方不一致。**

- 架构描述（L41、L55）：路由是 `/research/stream`
- 后端实现（L1923）：`@app.post("/api/research")`
- 前端（L1954）：`new EventSource('/api/research?topic=' + ...)`

`EventSource` 只能发 **GET**，且无法携带请求体。对着一个只注册了 POST 的路由建连 → 405。
三处名字对不上，其中前后端那一处是**协议层面**的不兼容，不是笔误。

**② 报告永远不会显示在界面上；且 SSE 会自动重连，导致整轮研究无限重跑。**

后端结束时发的是（L1917）：

```python
yield f"data: {json.dumps({'type': 'progress', 'stage': 'completed', 'percentage': 100, 'text': '研究完成！'})}\n\n"
```

前端的 `case 'completed':`（L1987–1990）匹配的是 `data.type === 'completed'`，
而这条事件的 `type` 是 `'progress'`、`completed` 在 `stage` 里。于是：

- 走 `case 'progress'` 分支 → 只更新百分比和文案
- `eventSource.close()` **不执行**，`isLoading` **不置 false**
- 服务端生成器耗尽后连接断开 → `EventSource` 语义是**自动重连** → `/api/research` 被再次请求
  → 若第 ① 条修好，整轮研究（含全部 LLM 调用与搜索 API 调用）会**周期性重跑，无限循环**

同时 `ResearchModal.vue` 里 `isLoading = ref(true)`（L1759）、`markdownContent = ref('')`（L1763）
是组件**本地**状态，与 `useResearch()` 没有任何连接（L1744–1790 没有 import useResearch）。
配合 L1728–1733 的 `v-if="isLoading"` 转圈 / `v-else` 渲染 Markdown，
**转圈图标会永远转下去，最终报告一次也不会上屏。**

**③ 四处 `await` 加在同步方法上。**

`research_stream`（L1885/1897/1900/1911）：

```python
todo_items = await planning_service.plan_todo_list(topic)
search_results = await search_service.search(task.query)
summary, source_urls = await summarization_service.summarize_task(task, search_results)
report = await reporting_service.generate_report(topic, task_summaries)
```

四个方法的定义全部是同步 `def`：`plan_todo_list`(L1142)、`search`(L1531)、
`summarize_task`(L1348)、`generate_report`(L1444)。`await` 一个 list / tuple / str →
`TypeError: object list can't be used in 'await' expression`。
这段被 L1919 的 `except Exception` 兜住，前端收到的是一条 `{"type":"error"}`。
**唯一的运行结果就是报错，而正文把它作为 14.6.2 的完整后端实现给出。**

**④ 参数类型对不上，两个调用点错法一致。**

`plan_todo_list(self, state: SummaryState)` 内部用 `state.research_topic`（L1154）。
两个调用点都传裸字符串：L859 `self.planner.plan_todo_list(research_topic)`、
L1885 `planning_service.plan_todo_list(topic)` → `AttributeError: 'str' object has no attribute 'research_topic'`。

**⑤ 14.3.1 与 14.5.1 的 `PlanningService.__init__` 签名不同。**
L497–504 只收 `llm`，且引用了一个类里不存在的 `self._on_tool_call`；
L1126–1140 收 `(llm, tool_call_listener)`。而 L830–832 按两参数调用。
14.3.1 那版直接 `TypeError`。同章前后两版实现不一致 —— 与 Ch13 L568/L800、Ch16 两套 Tool 接口同一模式。

**⑥ 示例的"结果"注释被写反了。这是本章最干净的一处「作者没跑过」证据。**

L1228–1245 的 `response1` 内容是**多模态模型**的两个任务，L1249 注释却写：

```python
tasks1 = service._extract_tasks(response1)
# 结果：[{"title": "Datawhale的基本信息", ...}, ...]
```

L1252–1257 的 `response2` 内容是 **Datawhale** 的两个任务，L1261 注释却写：

```python
# 结果：[{"title": "什么是多模态模型", ...}, ...]
```

**两个示例的输出注释整个对调了。** 顺带 L1244 那句结尾文字"这些任务涵盖了 Datawhale 组织的
基本信息和核心项目"贴在多模态模型的任务列表后面，也是同一次复制粘贴的残留。
把示例的"输出"手写进注释而不是跑一遍贴回来，正是 Ch12「正文数字 vs 产物数字」问题的微观版本。

**⑦ 第二个 `SearchService` 类把第一个覆盖掉了，并引用了不存在的方法。**
L1629 重新 `class SearchService:`，只定义 `__init__ / search / _generate_cache_key`，
其 `search` 里调 `self._execute_search(query, max_results)`（L1656）—— **全章没有这个方法**；
同时 `_deduplicate_sources` 与 `_limit_source_tokens` 在这一版里消失了。
正文没有任何"以下是在原类上追加"的说明，按印出来的代码就是 `AttributeError` + 去重逻辑丢失。

**⑧ "1-2 小时压缩到 5-10 分钟"（L23）与"整个研究过程大约需要 1-3 分钟"（L179）互相矛盾，且都无测量。**
全章没有任何计时、token 计数或对照实验。与 Ch15「成本降低到原来的 1/3」同类。

**⑨ `NotesService` 从未被调用；L985–993 那棵 `workspace/` 目录树没有任何代码路径会产生。**
`DeepResearchAgent.run`（L856–887）与 `research_stream`（L1873–1921）两条编排里
都没有出现 `NotesService` / `note_tool`。而 14.7 小结 L2119 写：
「**NoteTool**：持久化研究进度，**支持恢复和审计**」。
- "支持恢复"：L978 也说"研究过程中断时能够从上次的进度继续"。全章**没有任何读取笔记、
  检查断点、跳过已完成任务的代码**；`NotesService` 只有 `save_task_summary` 一个方法。
- "支持审计"：笔记内容（L1031–1044）记了任务信息、搜索结果、总结，但**没有**记搜索后端、
  是否命中缓存、时间戳、模型名与参数、LLM 原始响应。

**一个未接线的持久化层，被小结写成两项已交付能力。**

#### Q2：失败/无法判断被静默转成正常值

**① 搜索失败 → `return []` → 下游照常总结、照常报「任务完成」。本章最严重的 Q2。**

```python
except Exception as e:
    logger.error(f"搜索失败：{query}，错误：{e}")
    return []                      # L1565-1567
```

裸 `except Exception` 把超时、401、配额耗尽、JSON 结构变化压成同一个空列表。之后：

- `_format_sources` 拿到空列表 → 拼出**空字符串**
- `task_summarizer_instructions` 里 `搜索结果：\n{search_results}` 变成 `搜索结果：`（后面什么都没有）
- Agent 仍被要求"提取关键信息""**为每个观点添加来源引用（使用[1]、[2]等标记）**"（L562）

**没有资料时要求模型输出带编号引用的总结 —— 这是在直接索取捏造的引用。**
编排层（L1891–1905）对 `search_results` 是否为空**没有任何检查**，
照样 `yield {'type': 'task_summary', ...}`，照样推进百分比，最后照样发 `'研究完成！'`（L1917）。
`source_urls = []`，所以最终报告那一节的"来源"是空的，而正文里的 `[1][2]` 还在。

对 finaudit 的映射极直接：**"没查到"与"查到了但没有相关内容"必须在数据层可区分，
且必须能阻断下游生成。** 检索为空时继续生成分析结论，等同于要求模型编。

**② `evaluate_plan` 的 100 分底盘：没检查的维度自动满分（L1276–1305）。**

```python
score = 100
if len(todo_items) < 3:  score -= 20
elif len(todo_items) > 5: score -= 10
for task in todo_items:
    if len(task.query.split()) < 2: score -= 10
# 检查逻辑关系
# （这里可以添加更复杂的逻辑检查）
return {"score": score, "suggestions": suggestions}
```

L1266–1271 声明的四条标准是「覆盖全面 / 逻辑清晰 / 查询精准 / 数量适中」。
实际检查的只有「数量」和「query 词数 ≥ 2」两条。
**"覆盖全面"和"逻辑清晰"从未被检查，却因为从 100 分起扣而各自默认满分。**
四个任务、每个 query 三个词、内容全是同义重复 —— 也会得 100 分。
这与 Ch16 `StyleCheckTool` 把"我只查了两条"输出成"符合 PEP 8"是同一个错误的两种形态：
**一个把未覆盖范围报成合规，一个把未覆盖范围计入满分。**
另外 `score` 无下限，可以扣成负数。而这个函数**全章没有任何调用点**，也没有任何阈值门禁。

**③ 计数式成功日志（L1561）。**

```python
logger.info(f"搜索成功：{query}，返回{len(results)}个结果")
```

搜索 API 正常返回但结果为空时，打印的是「**搜索成功**：xxx，返回 **0** 个结果」。
与 Ch15 L465「✅ 背景对话更新完成: 2个NPC」同型：用"做了几个"冒充"做对了"，
且不与期望数（`max_results=5`）比对。

**④ Token 截断无痕迹（L1596–1597）。**

```python
if len(snippet) > max_chars:
    snippet = snippet[:max_chars] + "..."
```

`"..."` 是唯一的信号，且它与摘要原文里本来就可能有的省略号无法区分；
截断量、原长度都不落任何字段。下游 Agent 和最终报告都不知道自己看的是残篇。
另外"1 个 Token 约等于 4 个字符"（L962、L1593）对中文是**大幅高估**（中文常见 1–2 字符/token），
所以 2000 token 的预算实际会放进 8000 字符的中文内容，限流目标失效但没有任何报警。

#### Q3（其余）：看起来可追溯、实际不可复核

**① 搜索缓存永不过期，且缓存命中在任何产物上都不可见（L1624–1669）。**

```python
cache_key = self._generate_cache_key(query, max_results)   # md5(query_maxresults_backend)
if use_cache and cache_file.exists():
    logger.info(f"从缓存读取搜索结果：{query}")
    return json.load(f)
```

缓存键 = `md5(query + max_results + backend)`，**不含日期**；文件存在即命中，**没有 TTL、没有写入时间戳**。
而本章的核心卖点是时效性：规划提示词专门注入 `current_date`（L458），
L490 解释"提示词包含当前日期以获取最新信息"，L23 卖点是"快速了解新的技术、概念或事件"。
**一个半年前的缓存会被当作今天的检索结果，喂给一个被告知"今天是 {current_date}"的模型。**
更关键的是：命中缓存只进 `logger.info`，**不进 SSE 事件、不进笔记、不进报告**。
最终报告里那份"参考文献"无法回答"这些来源是什么时候取的"。

对 finaudit 的映射：证据链必须携带 **as-of 时间**与**取数方式（实时/缓存/快照）**。
财务数据尤其如此——同一个"营业收入"在年报原文、更正公告、数据库快照里可以是不同的数。

**② 最终报告的"参考文献"是搜索结果 URL 的转储，与报告里的论断没有绑定。**
（这是上一轮 `source_urls` 结论的下游放大，机制不同故单列：）
`_format_summaries`（L1486–1494）把每个任务的 `source_urls` 全量列在 `**来源**：` 下，
`report_writer_instructions`（L661）要求"保留所有来源引用"，
最终渲染成 L2056–2065 那种按任务分组、带链接文字的「## 参考文献」。
**外观是学术引用，实质是"这次搜索引擎返回过的 5 条链接"的清单**，
其中有几条真正被 Summarizer 读进结论、正文里的 `[1]` 对应哪一条，全章没有任何机制建立映射。
与 Ch13 那张「看起来可核对、实际无勾稽」的预算明细表完全同构。

**③ 进度百分比在工作开始前就推进（L1893–1894）。**
`percentage = 10 + (idx / len(todo_items)) * 70`，在循环体**顶部** yield，
之后才执行 `search` 与 `summarize`。3 个任务时，第 3 个任务的搜索还没发起，
界面已经显示 80% + "正在研究任务3/3：{title}"。
比 Ch13 那个纯 `setInterval` 假进度好（至少与真实循环同步），但仍是**先报后做**。

**④ `_extract_tasks` 的贪婪正则（L1193）。**

```python
json_match = re.search(r'\[.*\]', response, re.DOTALL)
```

`.*` 贪婪 + `DOTALL` = 从响应里**第一个 `[` 一直吃到最后一个 `]`**。
`todo_planner_instructions` 自己就在提示词里给了一段含 `[` `]` 的示例（L472–480），
模型若复述示例再给答案，匹配会横跨两段 → `JSONDecodeError` → `ValueError`。
**这一处至少是响亮失败（raise 而不是返回默认值），是本章唯一一个失败处理做对了的地方**，
值得与前面那些 `return []` / `return 0` / `return 2` 对照。

#### 本章值得借鉴的

- **笔记的两层结构（L1031–1044）**：同一个文件里先写 `## 搜索结果`（逐条 title/URL/snippet 原文），
  再写 `## 总结`（LLM 产物）。**原始输入与派生结论同文件、可对照**，
  正是 Ch16 提到的"报告不能是 LLM 输出的 dump"的正确形态。
  finaudit 可直接借：每条结论旁边挂它所依据的原始抽取结果。
  唯一的问题是这段代码**没有被接进流程**（见 Q1-⑨）——好设计写了但没接线。
- **中间层执行工具（L1502）**：`SearchService` 在 Agent 之外执行搜索，把结构化结果喂给 Agent。
  这个选择对可审计性其实是**有利**的（调用参数、后端、结果都在确定性代码里，不由模型即兴决定），
  比让 Agent 自己发 `[TOOL_CALL:...]` 更容易留痕。
  但本章选了这条路之后，**没有把审计点跟着挪过来**，还留在 Agent 侧的 listener 上（见开头那条 Q3）。
  finaudit 的教训：**工具执行点在哪，审计点就得在哪。**
- **搜索结果去重按 URL（L1569–1580）**：`source.get("url", "")` + 空串跳过，写法本身没问题。
  但只按 URL 精确匹配，同一页面的 `http/https`、带 `?utm_source=` 的变体、
  末尾斜杠差异都会被当作不同来源。对 finaudit 意义不大（数据源固定），记一笔。

#### 一处语料损坏（如实标注）

L1381–1402：`SummarizationService._format_sources` 的 docstring 在 L1387 之后
代码块围栏破损，正文的「### 报告结构设计」「## 参考文献」被吃进了同一个 ``` 块里，
到 L1402 才闭合。因此 **`SummarizationService._format_sources` 的方法体在语料里读不到**，
我不对它下断言。（14.3.1 L620–629 有一个同名方法的早期版本，格式为 `[idx] title / URL / 摘要`。）

---
