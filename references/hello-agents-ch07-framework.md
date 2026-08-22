# hello-agents 第七章「构建你的智能体框架」精读

**语料**
- 书稿：`hello-agents` @ `45dd84e`，`docs/chapter7/第七章 构建你的Agent框架.md`（**2200 行**）。
  下文简写为 `ch7:行号`。
- 章节配套代码：同一仓库 `code/chapter7/`（13 个文件，含 `.env.example`）。
  下文简写为 `code/chapter7/xxx.py:行号 @45dd84e`。
- 框架真身：`github.com/jjyaoao/helloagents`。
  **书稿正文钉的是 `pip install "hello-agents==0.1.1"`（`ch7:101`）**，
  故凡拿书对代码，一律取 **tag `V0.1.1`**（`git show V0.1.1:<路径>`），下文简写为 `pkg@V0.1.1:<路径>:行号`。
  仓库 HEAD 为 `5432566`（= 1.0.0），仅在需要标注**版本差**时引用，简写 `pkg@1.0.0`。

**本轮读的范围**：§7.1 与 §7.3 起至章末。
§7.2（`ch7:154-458`）此前已在 `references/hello-agents-deep-read-part4.md` §2 读过，本轮不重读。

## 覆盖表

| 小节 | 行号范围 | 读到什么程度 |
|---|---|---|

---

## 1. §7.1 框架整体架构设计（`ch7:7-153`）

### 1.1 「为何自建」的四条理由（`ch7:9-36`）

书给的动机分三组，共九条，但真正影响骨架的是第一组（`ch7:17-20`）对既有框架的四条指控：

1. **过度抽象的复杂性** —— 点名 LangChain 的链式调用「灵活但学习曲线陡峭」（`ch7:17`）。
2. **快速迭代带来的不稳定性** —— API 频繁变更，版本升级即代码失效（`ch7:18`）。
3. **黑盒化的实现逻辑** —— 「开发者难以理解 Agent 的内部工作机制」；遇到问题只能等社区（`ch7:19`）。
4. **依赖关系的复杂性** —— 重依赖导致与其它项目集成时冲突（`ch7:20`）。

第三组里有一条与本项目直接相关：**「特定领域的优化需求：金融、医疗、教育等垂直领域往往需要针对性的提示词模板、特殊的工具集成、以及定制化的安全策略」**（`ch7:34`）。
书自己承认通用框架在垂直域要做二次开发——这是 finaudit-agent 不直接套用通用框架的一条外部佐证。

第三组还有一条：「学习与教学的透明性要求……这要求框架具有高度的可观测性和可解释性」（`ch7:36`）。
**注意这里的「可观测性」是教学意义上的**（让学习者看清每一步），不是审计意义上的（让第三方独立复核）。
后文（§7.4/§7.5）的实现会印证这个差别：书里的"可观测"落地成 `print()`，见 §4.1、§5.2。

### 1.2 四条设计理念（`ch7:38-58`）

| # | 理念 | 出处 | 我的读法 |
|---|---|---|---|
| 1 | 轻量级与教学友好的平衡：**按章节切分核心代码**；除 OpenAI SDK 外不引重依赖 | `ch7:46` | 「按章节切分」是**教学分层**，不是**职责分层**。两者在 §7.1.3 的目录树里被混为一谈 |
| 2 | 基于标准 API 的务实选择：不重新发明抽象接口，直接站在 OpenAI API 之上 | `ch7:48-50` | 这是本章最值得抄的一条 —— 见 §7 骨架启示 |
| 3 | 渐进式学习路径：**每一章的代码存为一个可 pip 下载的历史版本** | `ch7:54` | 「章 ↔ 版本号」一一对应。这是把教学进度直接编码进发布版本，代价见下方「版本即章节」批注 |
| 4 | **统一的"工具"抽象：万物皆为工具** | `ch7:56-58` | 全章最强的架构断言，也是最该谨慎借鉴的一条 |

理念 4 的原文值得完整记下：

> 「除了核心的 Agent 类，一切皆为 Tools。在许多其他框架中需要独立学习的 Memory（记忆）、RAG（检索增强生成）、RL（强化学习）、MCP（协议）等模块，在 HelloAgents 中都被统一抽象为一种"工具"。」（`ch7:58`）

即 **Memory / RAG / RL / MCP 四类东西全部塌缩进 `Tool` 这一个接口**。
书给的理由是「消除不必要的抽象层，让学习者回归到最直观的'智能体调用工具'这一核心逻辑」（`ch7:58`）——
理由是**教学的**，不是**工程的**。这一点在评估是否借鉴时是决定性的。

**「版本即章节」的代价**：理念 3 把版本号绑定到章节进度，意味着 `0.1.1` 不是"稳定的第一个可用版本"，
而是"第七章讲到哪儿就是哪儿"。后文多处书稿与 `V0.1.1` 代码对不上（见 §2.3、§4.1、§6），
根因就在这里——书稿描述的是**教学终态**，包发布的是**章节快照**。

### 1.3 目录树：它把框架切成了哪几块（`ch7:64-90`）

```
hello_agents/
├── core/        # 核心框架层  agent.py / llm.py / message.py / config.py / exceptions.py
├── agents/      # Agent实现层 simple / react / reflection / plan_solve
└── tools/       # 工具系统层  base.py / registry.py / chain.py / async_executor.py / builtin/
```

**三层，不是四层**。书自述原则是「分层解耦、职责单一、接口统一」（`ch7:92`）。逐块看职责边界：

- **`core/`——契约层**。五个文件全是"被继承/被引用"的东西：抽象基类、LLM 统一接口、消息值对象、
  配置对象、异常体系。它不含任何具体 Agent 行为。这一层的存在是整个骨架里最干净的决策。
- **`agents/`——范式层**。四个文件对应第 4~6 章讲过的四种范式（Simple / ReAct / Reflection / PlanAndSolve）。
  **切分维度是"推理范式"，不是"业务域"**。
- **`tools/`——能力层**。基类 + 注册表 + 链 + 异步执行器 + 内置工具。
  注意 `chain.py` 与 `async_executor.py` 在目录树里被列为**一等文件**（`ch7:84-85`），
  但正文 §7.5.4 只把它们当"高级特性"讲，且 `V0.1.1` 里两者都在（见 §5.4）。

**这个树与 `V0.1.1` 实际发布内容的差异**（`git ls-tree -r --name-only V0.1.1`）：
`V0.1.1` 实际多出 `core/exceptions.py`（树里有）、以及树里**没画**的 `utils/`（`helpers.py` / `logging.py` /
`serialization.py`）与 `version.py`。也就是说，**书稿的架构图省略了 utils 层**。
这是"图是理念、包是实物"的又一例，属版本/表述差，不是错误。

### 1.4 快速开始与"完整测试文件"的承诺（`ch7:94-150`）

- 安装钉版本：`pip install "hello-agents==0.1.1"`，`Python >= 3.10`（`ch7:100-101`）。
- 学习路径二选一：体验式（pip 装了跑）/ 深度式（从零实现），建议「先体验，后实现」（`ch7:104-109`）。
- **关键承诺**（`ch7:109`）：

  > 「在本章中，我们提供了完整的测试文件，你可以重写核心函数并运行测试，以检验你的实现是否正确。」

  这句话是本轮五问之一，答案在 §6：**这些 `test_*.py` 不是测试**，是需要真实 API key、
  靠人眼看 `print` 的演示脚本；且 `V0.1.1` 的包里**根本没有 `tests/` 目录**。

**30 秒示例里的一处自相矛盾**（`ch7:113-150`）：

```python
# 需要实现7.4.1的MySimpleAgent进行调用，后续章节会支持此类调用方式
# agent.add_tool(calculator)          # ← ch7:141-142，被注释掉了

# 现在可以使用工具了                   # ← ch7:144
response = agent.run("请帮我计算 2 + 3 * 4")   # ← ch7:145
```

`add_tool` 被注释掉，紧接着的注释却说「现在可以使用工具了」。
实测 `V0.1.1`：`SimpleAgent` 只有 `__init__` / `run` / `stream_run` 三个方法，**没有 `add_tool`**
（`pkg@V0.1.1:hello_agents/agents/simple_agent.py`，全文 86 行）。
全包 grep 命中数 **0**：

```
for f in $(git ls-tree -r --name-only V0.1.1 | grep '^hello_agents/'); do \
    n=$(git show V0.1.1:$f | grep -c "add_tool"); [ "$n" != "0" ] && echo "$f: $n"; done
→ 无输出（0 个文件命中）
```

所以 `ch7:144-146` 那两行执行的是**不带工具的纯 LLM 对话**，读者会得到一个看似正确、
实则未经计算器验证的算术答案。**这正是 finaudit-agent 要防的那类失败**：
输出看起来对，但产生它的路径不是宣称的那条路径，且从输出上看不出来。

---

## 2. §7.3 框架接口实现（`ch7:459-604`）

本节只讲三个文件：`message.py` / `config.py` / `agent.py`（`ch7:461-465`）。
三段代码我逐字与 `pkg@V0.1.1` 对过，**书稿即实物**，唯一差异是书稿省略了 `agent.py` 末尾的
`__repr__`（`pkg@V0.1.1:hello_agents/core/agent.py:45-46`）。这一节是全章书码一致性最好的一节。

### 2.1 `Message`：一个只有两个字段能出门的值对象（`ch7:467-507`）

```python
MessageRole = Literal["user", "assistant", "system", "tool"]   # ch7:477
class Message(BaseModel):
    content: str; role: MessageRole
    timestamp: datetime = None
    metadata: Optional[Dict[str, Any]] = None
    def to_dict(self): return {"role": self.role, "content": self.content}   # ch7:494-499
```

书自己给的原则是 **「对内丰富，对外兼容」**（`ch7:507`）：`timestamp` / `metadata` 存在内部，
`to_dict()` 出门时**只留 `role` + `content`**。

**这条原则对 finaudit-agent 是反向的教训。** 「对外兼容」在这里的实现方式是**丢弃**：
`to_dict()` 是唯一通向 LLM 的出口，凡不在 OpenAI schema 里的字段一律在这一步蒸发。
于是 `timestamp` / `metadata` 天生只能活在进程内存里——它们既不进 prompt，也没有任何序列化落盘路径
（`utils/serialization.py` 在 `V0.1.1` 里存在，但 `hello_agents/__init__.py` 不导出它，
上层 Agent 也没有一处调用；见 §2.4 的 grep）。

对一个要求证据链的系统，这正是**证据丢失点**：模型看到的输入与我们记录的输入是两份东西，
且丢弃发生在一个 3 行的 `to_dict()` 里，没有任何显式声明。

> **该刻意不抄**：单一 `to_dict()` 兼作「送模型」与「记历史」。
> finaudit-agent 需要两条独立出口：`to_llm_payload()`（可有损，须记录丢了什么）与
> `to_evidence_record()`（无损，含 timestamp / 口径 / 来源）。落地点见 §7 启示 S-2。

另一个细节：`timestamp: datetime = None` 声明的是非 Optional 类型却给了 `None` 默认值
（`ch7:481`）。因为 `__init__` 被重写、总是塞入 `datetime.now()`，实践中不会触发；
但这是 pydantic 下的类型谎言，`Message.model_construct()` 之类的旁路会直接穿透。

### 2.2 `Config`：`V0.1.1` 里它是**死抽象**（`ch7:509-550`）

书说 `Config` 的职责是「将代码中硬编码配置参数集中起来」（`ch7:511`），
并夸 `from_env()`「允许用户通过设置环境变量来覆盖默认配置，无需修改代码」（`ch7:550`）。

**实测：整个 `V0.1.1` 包里没有任何一处消费它。** 全包逐文件 grep（命令与命中数）：

```
for f in $(git ls-tree -r --name-only V0.1.1 | grep '^hello_agents/'); do
    n=$(git show V0.1.1:$f | grep -c "<PAT>"); [ "$n" != 0 ] && echo "$f: $n"; done
```

| 模式 | 命中 | 说明 |
|---|---|---|
| `from_env` | 1（仅 `core/config.py` 自身的 `def`） | 框架内**零调用** |
| `max_history_length` | 1（仅自身声明） | 声明了历史上限，**没有任何地方裁剪历史** |
| `self.config` | 1（仅 `core/agent.py:22` 的赋值） | 赋完就再没被读过 |
| `config.temperature` | 0 | — |
| `Config()` | 1（仅 `core/agent.py:22`） | — |

也就是说：`Agent.__init__` 里 `self.config = config or Config()`
（`ch7:571` / `pkg@V0.1.1:hello_agents/core/agent.py:22`）是这个类**唯一**的生命迹象。

更麻烦的是**双份真相**：`temperature` / `max_tokens` 在 `Config` 里有一份
（`ch7:519-520`），在 `HelloAgentsLLM.__init__` 里**另有一份**
（`pkg@V0.1.1:hello_agents/core/llm.py:33-34,53-54`），实际生效的是后者
（`llm.py:280-281,307-308` 把 `self.temperature` 送进 API）。
把 `Config(temperature=0.1)` 传给 Agent **不会改变任何行为**，且不会报错。

> **对 finaudit-agent 直接相关**：这是「配置看起来管用、实际不管用」的标准形态。
> 审计要求的是「参数 → 行为」可追溯；一个能被静默忽略的 `temperature` 会让复核者
> 拿着配置快照复现不出结果，且**看不出来哪一步断了**。
> 防御手段不是纪律，是构造：**配置对象必须是 LLM 调用参数的唯一来源**，
> 且证据链里记录的是**实际送出的参数**，不是配置里写的参数。落地点见 §7 启示 S-3。

### 2.3 `Agent` 抽象基类：只强制一个方法（`ch7:552-602`）

```python
class Agent(ABC):
    def __init__(self, name, llm, system_prompt=None, config=None)   # ch7:558-571
    @abstractmethod
    def run(self, input_text: str, **kwargs) -> str: ...             # ch7:573-576
    def add_message / clear_history / get_history                    # ch7:578-590
```

契约面只有 **`run(str) -> str`** 一个抽象方法。这是整章骨架里最关键的一条设计决策，
也是问题 1（职责边界）的直接答案：**`core/` 对 `agents/` 的约束只有「输入一个字符串、返回一个字符串」**。

代价是 `**kwargs`（`ch7:574`）——签名上开了一个无类型的口子，
四个子类各自往里塞不同的东西，基类无法约束，调用方也无法从类型上知道能传什么。

**历史记录是「基类给了、子类自便」**：基类提供 `add_message`，但**是否调用完全靠子类自觉**。
全包 grep `add_message` 命中 15 处，分布在四个 Agent 里（simple 4 / react 4 / plan_solve 4 / reflection 2）——
数量不同，意味着**四种范式记录进历史的粒度不一致**。
而 `get_history` / `clear_history` 全包各命中 1 次（都在 `core/agent.py` 的定义处），
即**框架内部从不读自己的历史**，历史只为外部 `print` 服务。

> **该刻意不抄**：把「是否留痕」交给子类自觉。
> finaudit-agent 的等价物是证据记录——必须在**基类的模板方法**里强制发生，
> 不能是子类可以忘记调用的一个 helper。落地点见 §7 启示 S-1。

### 2.4 异常体系：四个子类，零处抛出（`core/exceptions.py`）

书稿 §7.3 **没有讲 `exceptions.py`**（`ch7:461-465` 只列了三个文件），但 §7.1.3 的目录树里它是一等文件
（`ch7:70` 附近）。实物里它是这样的（`pkg@V0.1.1:hello_agents/core/exceptions.py`，全文 21 行）：

```
HelloAgentsException（基类）
├── LLMException  ├── AgentException  ├── ConfigException  └── ToolException
```

全包逐文件 grep 结果：

| 异常类 | 全包命中 | 实际抛出处 |
|---|---|---|
| `LLMException` | 1 | **仅自身定义**，零处抛出 |
| `AgentException` | 1 | **仅自身定义**，零处抛出 |
| `ConfigException` | 1 | **仅自身定义**，零处抛出 |
| `ToolException` | 2 | 自身定义 + `tools/builtin/calculator.py` 1 处 |
| `HelloAgentsException` | 15 | `llm.py` 3 处 `raise`，`registry.py` / `search.py` 各 1 处引用 |

即**四层分类是装饰性的**，实际错误一律塌缩成基类。`core/__init__.py:7,14` 也只导出基类。
`llm.py:294-296` 更进一步：

```python
except Exception as e:
    print(f"❌ 调用LLM API时发生错误: {e}")
    raise HelloAgentsException(f"LLM调用失败: {str(e)}")
```

`except Exception` 全捕 → 转成字符串 → 包进基类异常。**原始异常类型与 traceback 在这一步丢失**
（没有 `from e`）。对调用方而言，超时、鉴权失败、限流、模型不存在是同一个东西。

> **finaudit-agent 的 fail-closed 要求与此正相反**：证据链要能区分
> 「工具执行失败」「口径不适用」「数据缺失」「模型拒答」——因为这四种对结论的影响不同。
> 一个把所有失败压成一条字符串的异常层，会让「降级成功」在上层无法与真成功区分。
> 见 AGENTS.md 硬规则第 3 条（证据链是第一类产物）与 D-003。

### 2.5 §7.3 对「教学分层 vs 职责分层」判断的检验结果

§1.3 的判断是：目录树的切分是**教学分层**而非**职责分层**。
§7.3 这一节**是反例，不是佐证**——`core/` 的三个文件确实是干净的职责切分
（值对象 / 配置 / 抽象基类），与章节顺序无关。

但检验也暴露了一个更细的问题：**`core/` 干净是因为它基本不做事**。
`Config` 零消费、`Agent` 只约束一个方法、`Message` 出门只剩两字段、异常四层塌缩成一层。
「职责单一」在这里的实现方式是**职责稀薄**。真正的行为全在 `agents/` 与 `tools/` 里，
而那两层才是按章节切的。所以 §1.3 的判断在 §7.4 / §7.5 才会被真正检验（见 §3.6 与 §4.6）。

---

## 3. §7.4 Agent 范式的框架化实现（`ch7:605-1349`）

本节把第四章的三种范式（ReAct / Plan-and-Solve / Reflection）「框架化」，另加 `SimpleAgent`，
末尾用 §7.4.5 补了一个 **`V0.1.1` 里根本不存在**的 `FunctionCallAgent`。
书自述三个重构目标（`ch7:609-611`），第 2 条是本节最该被检验的：

> 「**接口与格式的标准化统一**：建立统一的Agent基类和标准化的运行接口，
> 所有Agent都遵循**相同的初始化参数**、方法签名和历史管理机制。」（`ch7:610`）

**这条不成立。** 见 §3.3。

### 3.1 `MySimpleAgent`：把工具协议做成一个正则（`ch7:613-957`）

书让读者继承框架 `SimpleAgent` 并重写 `run`，加上工具调用能力。关键点：

**（a）工具调用协议是自由文本里的方括号标记。** 系统提示词里教模型输出
`[TOOL_CALL:{tool_name}:{parameters}]`（`ch7:701-702`），解析端是一条正则（`ch7:766`）：

```python
pattern = r'\[TOOL_CALL:([^:]+):([^\]]+)\]'
```

这是本项目要重点看的地方。用正则从模型自由文本里捞调用，意味着：

- **调用与叙述不可区分**。模型在解释「你可以这样写 `[TOOL_CALL:search:xxx]`」时，这条正则会把它当成真调用执行。
  没有任何转义或围栏机制。工具返回文本会被原样塞回 `messages`（`ch7:745`），
  若返回内容里含 `[TOOL_CALL:...]`，模型很容易复读它——**这是一条完整的注入路径**。
- **参数没有 schema**。`([^\]]+)` 之后是纯字符串，参数类型、必填性、取值域全部不存在。

**（b）「万物皆为工具」的第一笔账：参数靠工具名猜。**
因为 `Tool` 没有参数 schema，`_parse_tool_parameters`（`ch7:802-825`）只能**按工具名硬编码推断**：

```python
if tool_name == 'search':   param_dict = {'query': parameters}
elif tool_name == 'memory': param_dict = {'action': 'search', 'query': parameters}
else:                       param_dict = {'input': parameters}     # ch7:820-825
```

上一层 `_execute_tool_call` 里还有一条 `if tool_name == 'calculator'` 的特判（`ch7:786-788`）。
**统一抽象在调用点被三个 `if tool_name ==` 拆回去了。**
这就是问题 3 的答案的第一部分：`Tool` 抽象越薄，调度层就越要靠工具名的 magic string 补偿；
每加一类工具就要回来改这个 `if/elif`，**统一抽象的收益被调用点的分支吃掉了**。

**（c）失败被塑形成一段正常文本。** `_execute_tool_call` 的兜底（`ch7:799-800`）：

```python
except Exception as e:
    return f"❌ 工具调用失败:{str(e)}"
```

返回值类型是 `str`，成功也是 `str`。这段字符串随后与成功结果一起进
`工具执行结果:\n{tool_results_text}`（`ch7:745`）喂回模型。
**调用方在类型层面无法区分「工具算出了 42」与「工具炸了」**，模型则会在失败文本上继续编答案。

> 这正是 D-003 禁止的「降级成功」。finaudit-agent 的工具返回必须是
> `Ok(value, evidence) | Err(kind, detail)` 两态，且 `Err` **不允许**被当作可用于推理的上下文。
> 落地点见 §7 启示 S-4。

**（d）一处逻辑漏洞**：`_run_with_tools` 在耗尽 `max_tool_iterations` 后，
用 `final_response = self.llm.invoke(messages, **kwargs)` 再取一次回答（`ch7:754-755`），
**这一次不再走 `_parse_tool_calls`**。若模型此时仍输出 `[TOOL_CALL:...]`，
它会作为最终答案原样返回给用户。

**（e）框架里根本没有这套东西。** `pkg@V0.1.1:hello_agents/agents/simple_agent.py`（全文 86 行）
只有 `__init__` / `run` / `stream_run`，无 `tool_registry`、无 `add_tool`、无 `[TOOL_CALL]`。
所以 §7.4.1 的全部工具能力都活在读者自己的 `my_simple_agent.py` 里，**不是包的能力**。
这与 §1.4 记的 `ch7:141-146` 那处自相矛盾同源。

### 3.2 `MyReActAgent`：书里印的版本比包里的版本更脆（`ch7:959-1091`）

书对这一节的总结是「提升了智能体执行思考-行动循环的**稳定性**」（`ch7:1091`）。
把书稿 `run`（`ch7:1040-1090`，与 `code/chapter7/my_react_agent.py:55-100 @45dd84e` 逐字相同）
与 `pkg@V0.1.1:hello_agents/agents/react_agent.py:82-163` 对齐后，结论是**反过来的**：
书稿版本是包内版本**删掉四处防护**后的产物。

| 包内 `V0.1.1` 有的防护 | 位置 | 书稿 / `code/chapter7` 版本 |
|---|---|---|
| `if not response_text: break`（LLM 空响应即停） | `react_agent.py:115-117` | **删除** |
| `if not action: print("未能解析出有效Action，流程终止"); break` | `react_agent.py:125-127` | **删除**，改为 `if action:` 静默跳过 |
| `if not tool_name or tool_input is None: history.append("Observation: 无效的Action格式"); continue` | `react_agent.py:142-144` | **删除**，直接 `execute_tool(tool_name, tool_input)` |
| `if thought: print(f"思考: {thought}")` | `react_agent.py:122-123` | **删除**，`thought` 赋值后从未使用 |

第 2 条的后果最严重：解析失败时 `self.current_history` **不追加任何东西**，
下一轮 `history_str` 完全相同 → **构造出与上一轮逐字相同的 prompt** →
循环空转到 `max_steps`，最后返回「抱歉，我无法在限定步数内完成这个任务。」（`ch7:1087`）。
**从返回值上完全看不出中间发生过 5 次解析失败。**

第 4 条对本项目最关键：**ReAct 的 `Thought` 从不进入执行轨迹**。
`current_history` 只收 `Action:` 与 `Observation:`（`ch7:1080-1081`）。
也就是说，**「为什么调这个工具」这半个 ReAct 被丢掉了**——
既不进入下一轮的上下文，也不留在任何可导出的记录里。
对 finaudit-agent，`Thought` 恰恰是证据链中「口径选择理由」的载体，是**必须持久化的一等字段**。

**解析器本身的脆弱面**（`pkg@V0.1.1:react_agent.py:165-185`）：

```python
re.search(r"Thought: (.*)", text)     # . 不匹配换行 -> 只取第一行；search 命中全文首个 "Action:"
re.match(r"(\w+)\[(.*)\]", action_text)   # \w+ -> 工具名不能含 - 或 . ；(.*) 贪婪
```

`\w+` 使 `get-price[600519]` 这类工具名直接返回 `(None, None)`；贪婪的 `(.*)` 使
`calculator[2+3] 然后 search[x]` 被解析成一个参数为 `2+3] 然后 search[x` 的调用。
**两种情况都不抛异常。**

### 3.3 「统一的初始化参数」是假的（`ch7:610` vs `pkg@V0.1.1`）

四个 Agent 在 `V0.1.1` 的实际签名：

| 类 | 位置 | 第 3 个位置参数 |
|---|---|---|
| `SimpleAgent` | `simple_agent.py:13-19` | `system_prompt` |
| `ReflectionAgent` | `reflection_agent.py:90-98` | `system_prompt` |
| `PlanAndSolveAgent` | `plan_solve_agent.py:137-144` | `system_prompt` |
| **`ReActAgent`** | **`react_agent.py:52-61`** | **`tool_registry`** — 唯一的例外 |

于是书稿 `ch7:1022` 的这一行：

```python
class MyReActAgent(ReActAgent):
    def __init__(self, name, llm, tool_registry, system_prompt=None, config=None, ...):
        super().__init__(name, llm, system_prompt, config)   # ch7:1022，位置传参
```

**参数错位**：`system_prompt` 被绑到父类的 `tool_registry` 形参上，`config` 被绑到 `system_prompt` 上，
父类 `config` 收到 `None`。之后 `self.tool_registry = tool_registry`（`ch7:1023`）把错的那个覆盖掉了，
所以**不会崩**；但 `self.system_prompt` 最终持有的是一个 `Config` 对象（或 `None`），
`self.config` 变成默认 `Config()`。因为 `MyReActAgent.run` 从不读 `self.system_prompt`
（prompt 全由模板拼），这个错误**永远不会表现出来**。

这是本章对 finaudit-agent 最有价值的一个「活体样本」：
**一处静默的参数错绑，在一个「输出看起来正常」的系统里可以永远不被发现。**
它同时命中三件事——签名不统一 + 位置传参 + 子类不读被污染的字段。
可核查性要求的不是「不出这种错」，而是「出了能被机器发现」：
构造上的答案是**关键字传参 + 运行时记录实际生效的参数值**（不是配置里写的值，见 §2.2）。

### 3.4 Reflection 与 PlanAndSolve：只给提示词，不给实现（`ch7:1093-1282`）

这两小节的正文**只印提示词模板**：`DEFAULT_PROMPTS`（`ch7:1105-1135`，三段 initial/reflect/refine）
与 `DEFAULT_PLANNER_PROMPT` / `DEFAULT_EXECUTOR_PROMPT`（`ch7:1171-1205`）。
实现让读者「尝试根据第四章的代码……构建出自己的 `MyReflectionAgent`」（`ch7:1136`）。

**但配套的两个测试文件是照着一个不存在的模块写的：**

```
ch7:1141   from my_reflection_agent import MyReflectionAgent
ch7:1213   from my_plan_solve_agent import MyPlanAndSolveAgent
```

```
$ git -C ha_fw ls-tree -r --name-only HEAD | grep -c "my_reflection_agent.py\|my_plan_solve_agent.py"
0
```

**全仓 0 命中**（不只是 `code/chapter7/` 下没有，整个书仓都没有）。
即 `test_reflection_agent.py` 与 `test_plan_solve_agent.py` **在 `ImportError` 处就终止**，
连 API key 都用不到。这两个文件占 6 个「测试」文件的 1/3。

**值得记一笔正面的东西**：`Planner.plan`（`pkg@V0.1.1:plan_solve_agent.py:63-81`）
是全章唯一一处像样的 fail-closed：

```python
plan_str = response_text.split("```python")[1].split("```")[0].strip()
plan = ast.literal_eval(plan_str)                      # 不是 eval
return plan if isinstance(plan, list) else []
except (ValueError, SyntaxError, IndexError): ... return []
```

用 `ast.literal_eval` 而非 `eval`，且解析失败返回 `[]`，上层 `run` 见到空计划就返回
「无法生成有效的行动计划，任务终止。」（`plan_solve_agent.py:183-191`）——
**拒绝执行，而不是带着半个计划往下跑**。这是本章唯一值得直接抄的错误处理形态。

### 3.5 §7.4.5 FunctionCallAgent：框架自己承认了「中间态 → 最终态」（`ch7:1283-1349`）

这一小节是问题 2 的直接答案，而且是书自己写的：

> 「FunctionCallAgent是hello-agents在 **0.2.8 之后**引入的Agent……」（`ch7:1285`）
>
> 「这些功能可以使其具备原生的 OpenAI Function Calling 的能力，
> **对比使用 prompt 约束的方式，具备更强的鲁棒性**。」（`ch7:1293`）

版本验证：

```
$ git -C ha_fw2 ls-tree -r --name-only V0.1.1 | grep -ci function_call      -> 0
$ git -C ha_fw2 ls-tree -r --name-only V0.2.8 | grep -i  function_call
    examples/agent/function_call_agent_demo.py
    hello_agents/agents/function_call_agent.py
```

**所以这条演进路径是有据可查的**：

| 阶段 | 工具调用的落地方式 | 出处 |
|---|---|---|
| 中间态（`V0.1.1`，即本章正文教的东西） | **提示词约束 + 正则解析自由文本**：`Thought:/Action:` 正则、`[TOOL_CALL:a:b]` 正则、Planner 的「请输出 Python 列表」 | `ch7:766` / `react_agent.py:165-185` / `ch7:1176` |
| 最终态（`≥0.2.8`） | **OpenAI 原生 Function Calling**：JSON Schema 描述参数、模型返回结构化 `tool_calls`、JSON 参数解析 + 类型转换 | `ch7:1287-1291` |

**放弃的理由只有一个词：鲁棒性。** 书列出的四个新增私有方法
（`_build_tool_schemas` / `_extract_message_content` / `_parse_function_call_arguments` /
`_convert_parameter_types`，`ch7:1288-1291`）正好逐条对应正则方案的四个缺口：
**没有参数 schema、响应格式不确定、参数无结构、参数无类型**。

对 finaudit-agent 的意义：**不要重走这条中间态**。本项目连「文本协议 + 正则」这一步都不该踩，
因为审计场景对「调用是否真的发生、用了什么参数」的要求比通用场景更硬。

**一处抽象泄漏值得记**：`_invoke_with_tools`（`ch7:1296-1313`）绕过了 `HelloAgentsLLM` 的公开接口，
直接掏私有属性：

```python
client = getattr(self.llm, "_client", None)
if client is None:
    raise RuntimeError("HelloAgentsLLM 未正确初始化客户端，无法执行函数调用。")
```

即 §7.2 精心包装的 `HelloAgentsLLM`（`invoke` / `think` / `stream_invoke`）**不足以表达 function calling**，
最终态只能把它拆开用底层 `OpenAI` client。这是 §1.2 理念 2（「站在 OpenAI API 之上，不重新发明抽象」）
被自己的封装绊了一下的证据：**包装层如果只覆盖了 chat completion 的一个子集，
新能力到来时唯一的出路就是穿透它**。

### 3.6 §7.4 对「教学分层 vs 职责分层」的检验结论

**判断成立。** `agents/` 四个文件的切分维度是**第四章讲过的四种范式**，
而 §7.4.5 的 `FunctionCallAgent` 是**能力维度**（原生 function calling）而非范式维度——
它与 ReAct 不是并列关系，ReAct 完全可以用 function calling 实现。
把两种维度并排放进同一个 `agents/` 目录，正是「按讲授顺序切分」的后果。

对 finaudit-agent 的直接结论：**不要按「范式」建目录**。
本项目的一级切分应该是**证据责任**（取数 / 口径判定 / 计算 / 引证 / 复核），
推理范式是这些模块内部的实现选择，不该出现在目录树的第一层。

---

## 4. §7.5 工具系统（`ch7:1350-2146`）

本节自述三个目标（`ch7:1354-1358`），第 1 条是「**统一的工具抽象与管理**」。
这一节是问题 3（「万物皆为工具」付出了什么代价）的主战场。

### 4.1 `Tool` / `ToolParameter` / `ToolRegistry`：schema 存在，但传不出去（`ch7:1360-1515`）

**（a）抽象本身是合格的。** `Tool` 有两个抽象方法（`ch7:1372-1380`）：

```python
@abstractmethod def run(self, parameters: Dict[str, Any]) -> str
@abstractmethod def get_parameters(self) -> List[ToolParameter]
```

`ToolParameter`（`ch7:1391-1398`）有 `name / type / description / required / default`。
`pkg@V0.1.1:hello_agents/tools/base.py` 里还多了书没印的两个方法：
`validate_parameters`（`base.py:32-35`）与 `to_dict`（`base.py:37-43`）。
**纸面上这是有参数 schema 的。**

**（b）但三条路径把 schema 全部丢掉了：**

**丢弃点 1 —— 提示词。** `get_tools_description()`（`ch7:1416-1430` / `registry.py:103-120`）
是唯一送进 Agent 提示词的工具信息，它只产出：

```python
descriptions.append(f"- {tool.name}: {tool.description}")
```

**`get_parameters()` 的结果一个字都不进 prompt。** 模型只知道工具叫什么、干什么，
不知道要几个参数、什么类型、哪个必填。这直接解释了 §3.1(b) 里
`_parse_tool_parameters` 为什么必须**按工具名硬编码猜参数**——
不是作者偷懒，是**调用侧根本拿不到 schema**。

**丢弃点 2 —— 执行入口。** `ToolRegistry.execute_tool` 的签名是
`(name: str, input_text: str) -> str`，实现里这一行（`registry.py:86-88`）是关键：

```python
# 简化参数传递，直接传入字符串
return tool.run({"input": input_text})
```

**无论 `get_parameters()` 声明了什么，注册表永远只传 `{"input": <一个字符串>}`。**
一个声明了 `expression: str` + `precision: int` 的工具，经由注册表调用时收到的永远是 `{"input": ...}`。
于是 `ToolParameter` 在**框架自带的执行路径上完全不可达**。
（这也是为什么 §7.4.1 的 `_execute_tool_call` 对非计算器工具要绕开注册表、
直接 `tool.run(param_dict)`，`ch7:791-793`——它别无选择。）

**丢弃点 3 —— 校验从不发生。** 全包 grep：

```
$ for f in $(git ls-tree -r --name-only V0.1.1 | grep '^hello_agents/'); do
      n=$(git show V0.1.1:$f | grep -c "validate_parameters"); [ "$n" != 0 ] && echo "$f: $n"; done
  hello_agents/tools/base.py: 1      ← 仅自身 def，全包零调用
```

`Tool.to_dict()`（能把完整 schema 序列化出来的那个方法）全包 `\.to_dict()` 命中 **0**。

> **这就是「万物皆为工具」的完整账单**：为了让 Memory / RAG / RL / MCP 都能塞进同一个 `Tool`，
> 接口必须窄到 `str -> str`；接口一窄，参数 schema 就无法穿过它；schema 穿不过去，
> 调度层只能靠工具名的 magic string 补偿，参数校验只能不做。
> **统一抽象的代价不是抽象本身，是它强制的最小公分母。**

**（c）两个命名空间，跨空间不查重。** `ToolRegistry` 有 `_tools` 与 `_functions` 两个 dict
（`ch7:1405-1407`）。`register_tool` 只查 `_tools`（`ch7:1409-1411`），
`register_function` 只查 `_functions`（`registry.py:43-44`）。所以同名的 Tool 与 function **可以共存**：

- `execute_tool` 走 `if name in self._tools ... elif name in self._functions`（`registry.py:84,93`），
  **静默偏向 Tool 对象**（注释写着「优先查找Tool对象」），函数版永远执行不到；
- `list_tools()` 返回 `list(_tools) + list(_functions)`（`registry.py:124`），**同一个名字出现两次**；
- `get_tools_description()` 会往提示词里写两行同名工具；
- `unregister` 用 `if/elif`（`registry.py:54-59`），只删掉 `_tools` 那一份，函数版残留。

对可审计系统，「同名工具静默遮蔽」意味着证据链里记的 `tool_name` **不足以确定实际执行的是哪段代码**。
finaudit-agent 的工具标识必须是 `(name, version, impl_hash)`，不是一个裸名字。

**（d）`global_registry` 是模块级可变单例。** `registry.py:137` 有
`global_registry = ToolRegistry()`，并从 `hello_agents/__init__.py:22` 导出。
任何一处 `register_*` 都会污染全进程；没有作用域隔离、没有快照、没有冻结。

**（e）`to_openai_schema` 是未标注的版本漂移。** 书把它印在 §7.5.1 第（4）小节
「工具发现与管理机制」里（`ch7:1432-1479`），上下文是 `ToolRegistry`；
但方法体用的是 `self.get_parameters()` / `self.name` / `self.description`，**是 `Tool` 的方法不是注册表的**。
版本核对：

```
$ 逐 tag grep "def to_openai_schema"
  V0.1.1: 0   V0.2.0: 0   V0.2.3: 0   V0.2.6: 0   V0.2.8: 0
  V1.0.0: hello_agents/tools/base.py: 1
```

即它在 `V0.2.8` 都还没有，**只存在于 1.0.0 的 `tools/base.py`**。
与 §7.4.5 不同的是，书这里**没有任何版本说明**（§7.4.5 至少写了「0.2.8 之后引入」）。
按 §1.2「版本即章节」的批注，这属版本差；但它同时是**归属错误**（Tool 方法印进了 Registry 小节）。

**这条 schema 通路是 `V0.1.1` 缺失能力中最要紧的一处**：`to_openai_schema` 正是把
`get_parameters()` 重新接回调用链的那座桥。它在 1.0.0 才出现，恰好印证 §3.5 的演进结论。

### 4.2 §7.5.2 自定义计算器：一个会「静默算错」的工具（`ch7:1517-1662`）

书稿 `ch7:1524-1585` 与 `code/chapter7/my_calculator_tool.py @45dd84e` **逐字一致**
（diff 仅差文件末尾换行）。

**做对的部分**：用 `ast.parse(expression, mode='eval')` + 白名单遍历，**没有用 `eval`**
（`ch7:1550-1551`）。运算符白名单 4 个（`+ - * /`），函数白名单 2 个（`sqrt` / `pi`）。

**做错的部分有两处，第二处很严重。**

**（i）裸 `except:`（`ch7:1553`）** ——

```python
except:
    return "计算失败，请检查表达式格式"
```

裸 except 连 `KeyboardInterrupt` / `SystemExit` 都吞。更要紧的是：
除零、语法错误、不支持的运算符、类型错误**全部塌缩成同一句中文**，
而这句中文接着会被当成"工具结果"喂回模型（见 §3.1(c)）。

**（ii）`_eval_node` 对未识别节点隐式返回 `None`（`ch7:1556-1572`）** ——
`ast.Call` 分支里若 `func_name not in functions`，`if` 不成立、**没有 else**，函数走到底返回 `None`；
`ast.Name` 分支同理。上层 `return str(result)` 于是把 `None` 变成字符串 `"None"`。

**我实跑了这段代码**（原样抄自 `code/chapter7/my_calculator_tool.py`，本机 Python 执行）：

```
'2 + 3'     -> '5'
'sqrt(16)'  -> '4.0'
'pi'        -> '3.141592653589793'
'cos(1)'    -> 'None'        ← 不是错误，是"结果"
'log(100)'  -> 'None'        ← 同上
'abs(-3)'   -> 'None'        ← 同上
'x'         -> 'None'        ← 同上
'2 ** 10'   -> '计算失败，请检查表达式格式'
'10 % 3'    -> '计算失败，请检查表达式格式'
'-5 + 3'    -> '计算失败，请检查表达式格式'   ← 负号不支持（UnaryOp 未处理）
'1/0'       -> '计算失败，请检查表达式格式'
```

**`cos(1) -> "None"` 是本章最危险的一行代码。** 它不抛异常、不返回错误串，
而是把一个合法的字符串塞进"计算结果"的位置。上游 `execute_tool` 会原样返回它，
Agent 会把 `"None"` 当作计算器的输出继续推理。

> **对 finaudit-agent 的意义**：这与 §1.4 记的「`add_tool` 被注释掉但注释说'现在可以使用工具了'」是**同一种失败**——
> 输出存在、格式正常、来源可疑。审计场景里等价的形态是：
> 某个口径的数据缺失，但计算层返回了 0 或空串，最终结论看不出这是"没有"而不是"等于零"。
> 防御是构造性的：**计算层不允许返回可被解释为值的失败**（Ok/Err 两态，见 §7 启示 S-4），
> 且**白名单之外的输入必须显式拒绝**，不能落到隐式 `None`。

**（iii）"集成测试"没有集成。** `test_my_calculator.py` 的 `test_with_simple_agent()`
（`ch7:1621-1652`）标题是「测试与SimpleAgent的集成」，但函数体里**从头到尾没有 `SimpleAgent`**：
它自己写死表达式 `"sqrt(16) + 2 * 3"` 调 `registry.execute_tool`，
再把结果塞进一句 prompt 让 `llm.think` 复述（`ch7:1638-1650`）。

也就是说，**它测的是"人把算好的数交给模型复述"，而不是"Agent 自己决定调用计算器"**——
后者才是唯一值得测的东西。这是问题 4 的一个具体样本：
测试文件的名字与它实际验证的东西不是一回事。

### 4.3 §7.5.3 多源搜索：为了"高可用"把来源丢了（`ch7:1664-1949`）

这一节先展示框架内置的 `SearchTool`（`ch7:1674-1755`），再让读者写一个"自己的"高级搜索工具
（`my_advanced_search.py`，`ch7:1757-1891`）。三处值得记：

**（a）读者写的"高级"版本不继承 `Tool`。** `ch7:1763`：

```python
class MyAdvancedSearchTool:      # ← 没有 (Tool)
```

它通过 `registry.register_function(name="advanced_search", ..., func=search_tool.search)`
（`ch7:1882-1886`）走的是**函数命名空间**，完全绕开了 §7.5.1 刚建好的 `Tool` ABC。
**书自己在下一小节就没有用自己的统一抽象。**
这不是疏忽——`register_function` 更省事，而 `Tool` 除了两个抽象方法之外并不提供任何好处
（校验不跑、schema 不进 prompt、参数进不去，见 §4.1）。
**一个不带来好处的抽象，作者自己都会绕开。**

**（b）降级判定靠中文子串匹配。** `search()` 的多源回退逻辑（`ch7:1834-1845`）：

```python
result = self._search_with_tavily(query)
if result and "未找到" not in result:
    return f"📊 Tavily AI搜索结果:\n\n{result}"
```

「这次搜索算不算成功」由 **`"未找到"` 这三个字在不在格式化后的输出里**决定。两个方向都会错：

- **假阴性**：Tavily 正常返回一篇正文里含「未找到」的网页 → 整个结果被丢弃，静默换源；
- **假阳性**：`_search_with_tavily` 在零结果时返回的是 `"🔗 相关结果:\n"`（`ch7:1858-1866`，
  `for` 循环零次迭代），这个串不含「未找到」→ **判为成功**，一次空搜索被当作有效证据返回。

**（c）读者版把来源 URL 删掉了。** 框架内置版两条后端都带来源：

```
pkg@V0.1.1:hello_agents/tools/builtin/search.py:144   result += f"    来源: {item.get('url', '')}\n\n"
pkg@V0.1.1:hello_agents/tools/builtin/search.py:180   result_text += f"    来源: {res.get('link', '')}\n\n"
```

读者版 `my_advanced_search.py` 全文 `grep -c "url"` → **0**。
`_search_with_tavily` 只留 `title` + `content[:150]`（`ch7:1862-1864`），
`_search_with_serpapi` 只留 `title` + `snippet`（`ch7:1877-1879`）。

> **这是全章对 finaudit-agent 最刺眼的一处。** 一个「更高级」的检索工具，
> 相对官方版的净变化是**删掉了引证**。对通用问答这只是体验降级；
> 对本项目这是**产物直接作废**——没有 URL 的检索结果无法进入证据链，AC 层面等于没做。
> 教训写成规则：**证据字段不允许在"格式化输出"这一步被裁剪**，
> 因为格式化是最容易被随手改的一层（对应 §2.1 `to_dict()` 的同类问题）。

**（d）框架版 `_search_hybrid` 有一处误导性诊断。** `ch7:1700-1725`：
Tavily 可用但调用失败、且 SerpApi 不可用时，控制流落到函数末尾的

```python
return "❌ 没有可用的搜索源，请配置TAVILY_API_KEY或SERPAPI_API_KEY环境变量"
```

——**明明有可用的源（只是这次失败了），却告诉用户去配置一个已经配好的密钥**。
书对这段的评语是「体现了高可用系统的核心理念……通过降级机制」（`ch7:1727`）。
降级本身没问题，问题是**降级的事实只进 `print`，不进返回值**，而返回值里给出的原因是错的。

### 4.4 §7.5.4 高级特性：工具链会在失败上宣布成功（`ch7:1951-2145`）

**（a）`ToolChain` 不是图，是列表。** 正文说「这里借鉴了第六章中提到的**图**的概念」（`ch7:1958`），
实际数据结构是 `self.steps: List[Dict[str, Any]]`（`ch7:1970`），
`execute` 就是一个 `for i, step in enumerate(self.steps, 1)`（`ch7:1995`）。
**严格线性，无分支、无条件、无回边。** 这是表述与实现的不符，不是版本差。

**（b）步骤之间零错误检查。** `ch7:2007-2009`：

```python
result = registry.execute_tool(tool_name, tool_input)
context[output_key] = result
print(f"  ✅ 步骤 {i} 完成，结果长度: {len(result)} 字符")
```

`execute_tool` 失败时返回的是**字符串**（`registry.py:90,98,101`，见 §4.1），
所以它会被当作正常结果存进 `context`，并作为**下一步的输入**。
链条不会中断，只会带着错误文本继续跑，最后打印「🎉 工具链 '...' 执行完成」（`ch7:2013`）并返回它。

**（c）书给的示例链本身就必然失败。** `create_research_chain()`（`ch7:2043-2064`）第二步：

```python
chain.add_step(
    tool_name="my_calculator",
    input_template="根据以下信息计算相关数值:{search_result}",   # ch7:2059
    output_key="calculation_result"
)
```

`my_calculator` 是 §7.5.2 那个 `ast.parse(mode='eval')` 求值器。
把「根据以下信息计算相关数值:🔗 相关结果:…」喂给它 → `SyntaxError` → 裸 `except` →
返回 `"计算失败，请检查表达式格式"`。而 `execute` 返回的正是最后一步的结果（`ch7:2011`）。

**所以这条示例链的确定性输出是：控制台打印两次「✅ 步骤 N 完成」和一次「🎉 工具链执行完成」，
返回值是「计算失败，请检查表达式格式」。** 这是「宣布成功 + 返回失败」的教科书样本，
而且是书自己作为**正面示例**给出的。

（`ToolChain` 在 `pkg@V0.1.1:hello_agents/tools/chain.py` 里比书稿版**多**了三处防护：
空链检查 `"❌ 工具链为空，无法执行"`（`chain.py:45`）、
模板替换失败返回（`chain.py:67`）、以及**每步 try/except**
`return f"❌ 工具 '{tool_name}' 执行失败: {e}"`（`chain.py:76`）。
与 §3.2 同一个模式：**书稿印的是删掉防护后的版本。** 但注意 `chain.py:76` 的 try 只能接住
真抛出的异常，接不住 `execute_tool` 已经吞掉并变成字符串的那些失败——防护补在了错的层。）

**（d）`AsyncToolExecutor`：并行掩盖失败。** `execute_tools_parallel`（`ch7:2095-2113`）用
`await asyncio.gather(*async_tasks)`，**没有 `return_exceptions`**。
但这不重要——因为 `execute_tool` 早已把所有异常转成了字符串，`gather` 永远看不到异常。
结果就是 4 个并行任务里失败几个、失败在哪，**返回的 `List[str]` 里没有任何结构化信号**。

书稿版 `execute_tools_parallel` 返回 `List[str]`（`ch7:2095`），而
`pkg@V0.1.1:hello_agents/tools/async_executor.py:29` 返回的是 `List[Dict[str, Any]]`——
包内版本用字典保留了每个任务的元信息。**又一处「书稿比包更弱」**（版本相同，非版本差）。

另：`loop = asyncio.get_event_loop()`（`ch7:2086`）在协程内取 loop，Python 3.10+ 起
应改用 `asyncio.get_running_loop()`；`__del__` 里做 `executor.shutdown(wait=True)`（`ch7:2116-2119`）
是在垃圾回收时阻塞。包内版本提供了 `close()` / `__enter__` / `__exit__`
（`async_executor.py:97-107`），书稿版没印。

### 4.5 §7.5 对问题 3（「万物皆为工具」的代价）的完整回答

把四小节的证据合起来，代价是一条链，不是一个点：

1. **接口被压到最小公分母**（`Tool.run(dict) -> str`，`ToolRegistry.execute_tool(name, str) -> str`）——
   因为 Memory / RAG / RL / MCP 要共用同一个壳；
2. **参数 schema 因此无法穿过注册表**（`tool.run({"input": input_text})`，`registry.py:88`）——
   证据是**框架自带的两个工具都把唯一参数命名为 `"input"`**
   （`builtin/calculator.py:105-115`、`builtin/search.py:225-231`），这是为了迁就注册表的固定形状；
3. **调度层只能靠工具名 magic string 补偿**（`if tool_name == 'calculator' / 'search' / 'memory'`，
   `ch7:786-788`、`ch7:820-825`）；
4. **校验与序列化因此成为死代码**（`validate_parameters` / `to_dict` 全包零调用）；
5. **失败与成功共用 `str` 返回类型**，于是错误在链式调用与并行执行里被逐级放大
   （§4.4(b)(c)(d)）；
6. **作者自己绕开这个抽象**（`MyAdvancedSearchTool` 不继承 `Tool`，`ch7:1763`）。

**结论**：「万物皆为工具」在教学上确实降低了概念数量（书的目的达成了），
但它把**类型信息**换成了**字符串约定**，把**结构化错误**换成了**错误文本**。
finaudit-agent 要的恰好是被换掉的那两样。

**该抄的**：`Tool` / `ToolRegistry` 这个**两层结构**本身（能力对象 + 显式注册表）是对的，
它给了一个天然的"本次回答用到了哪些能力"的枚举点。
**该刻意不抄的**：把注册表的执行入口收敛成 `(name, str) -> str`。
finaudit-agent 的执行入口必须是 `execute(name, params: Model) -> Result[Value, Error]`，
参数用 pydantic 模型而不是 dict，返回用两态而不是字符串。
