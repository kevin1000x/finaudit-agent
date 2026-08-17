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
| Ch14 自动化深度研究智能体 | L1–2152（除引用机制段） | — | ⏳ |
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

```bash
git clone git@github.com:你的用户名/hello-agents.git
cd Hello-Agents
```

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
