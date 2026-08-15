# datawhalechina/hello-agents

**读到什么程度**：⚠️ **16 章只读了第 7 章（框架架构）+ README。严重不足。**
操作者已指出「借鉴会不会太少了」——成立。待补见 §4。

**基本信息**：Datawhale 的中文开源教程，16 章 + 实战项目，强调 **AI-native agent**
（区别于 Dify 那类软件工程编排），从零手写框架而不是只教用现成的。

---

## 1. 它的框架分层（第 7 章）

四层，「分层解耦、单一职责、统一接口」：

```text
core/     agent.py      抽象基类，强制统一契约
          llm.py        统一 LLM 接口
          message.py    标准消息格式（role 限四种，对齐 OpenAI 规范）
          config.py / exceptions.py
agents/   具体 agent 实现，继承抽象 Agent
tools/    ToolRegistry —— 注册、执行、管理
tools/builtin/  计算器、搜索等
```

`Agent` 抽象基类强制：统一初始化参数（name / llm / system_prompt / config）、
抽象 `run()` 作为唯一入口、`add_message()` / `get_history()` 管理对话历史。

## 2. 四个范式

| 范式 | 机制 |
|---|---|
| `SimpleAgent` | 基础对话，可选工具调用 |
| `ReActAgent` | 推理-行动循环，prompt 强制单步执行 |
| `ReflectionAgent` | 初次生成 → 自我反思 → 迭代改进 |
| `PlanAndSolveAgent` | 分解阶段（输出 Python list 格式的计划）→ 逐步执行 |

**对本项目**：主循环用 **ReAct**，外面套一层 **Reflection** 做「自查引用」——
「给出答案 → 反思引用的准则条号与口径版本对不对 → 修正」。
审计场景里这个回路是贴的，因为错误往往不在算术而在引错口径。

`PlanAndSolve` 暂不需要：本项目的问题多为单指标查询，不需要任务分解。

## 3. 刻意不借的：「万物皆 Tool」

它把 memory、RAG、RL 全部统一进 `ToolRegistry`，用一个概念覆盖所有扩展。
**对教学是好设计，对本项目是致命的。**

理由：如果口径查询只是「LLM 可以调的一个工具」，那 LLM 就**可以不调**——
直接用参数记忆答一个数出来。而「口径未定义时拒答而不是猜」是本项目的**全部论点**。
一个能被绕过的闸门等于没有闸门。

**本项目的做法**：语义层是**强制前置的闸门**，不是可选工具。
先解析口径 → 解析不到就拒答 → LLM 根本没机会开口。
具体形状见 `deepseek-harness.md` §3.1（`agent/pre-step` 的 reject 语义）。

这个偏离必须写进 Phase 2 的 `ARCHITECTURE.md` 并给出理由，
否则下一个人会以为是疏漏，然后「顺手修好」它。

## 4. 待读（按对本项目的价值排序）

| 章 | 内容 | 为什么要读 |
|---|---|---|
| **Ch12** | 性能评测框架 | **优先级最高**。评测是本项目的脊柱（`EVAL_CASES.md` 是三份权威文档之一），需要对照别人的分层与指标设计 |
| **Ch8** | 记忆系统与 RAG | 直接对应 Phase 3 知识层（准则 RAG、引用可追溯） |
| **Ch10** | 通信协议 MCP / A2A / ANP | 影响 Phase 2 的取数层如何与外部数据源交互 |
| Ch9 | 上下文工程 | 年报是超长文档，上下文策略直接影响可行性 |
| Ch4 | 经典范式详解 | 已知结论（ReAct + Reflection），细节待补 |
| Ch11 | Agentic RL（SFT → GRPO） | **不读**。D-011 明确不做训练与微调 |
| Ch13-16 | 实战项目与 capstone | 低优先，形态与本项目差异大 |
