# 沉淀落地待办 — 单一入口

> **这份文件是路由表，不是内容。** 每一条「未落地」的正文都在 `references/` 的对应
> 「启示」节里，本文件只做两件事：**让它们可数、可找**。
>
> 建立于 2026-08-23，起因是操作者追问「花这么大精力读的东西有没有沉淀到项目，
> 不是 reference 浓缩，而是落实到计划与实施细节」。
> 量账结果记在台账 N-34：`EVAL_CASES.md` 当时的外部证据命中数是 **0**，
> 而 hello-agents 第 12 章 2743 行早已全文读完。

## 1. 数字与它的口径（先说清楚，否则会被高估）

```bash
grep -h '未落地' references/*.md | wc -l      # -> 131
grep -h '已落地' references/*.md | wc -l      # -> 见下方复跑
```

**131 是「未落地」三个字的出现次数，不是去重后的条目数。** 同一条启示可能在
启示表、正文批注、末尾小结里各出现一次；也有少数是正文散文里提到这个词。
**真实的去重条目数尚未逐条统计——这件事本身是下面 T-1 的内容，不许把 131 当成待办数。**

## 2. 来源分布（`references/` 里 26 份产物，10 份带落地标注）

| 产物 | 「未落地」出现次数 | 启示节位置 |
|---|---:|---|
| `deepseek-harness-notes-part3.md` | 30 | §C.1 / §C.2 |
| `deepseek-harness-docs-part2.md` | 28 | 末尾「对 finaudit-agent 的启示」 |
| `hello-agents-ch09-context.md` | 21 | §11 |
| `hello-agents-ch07-framework.md` | 16 | §7 |
| `hello-agents-ch06-frameworks.md` | 13 | §8 |
| `hello-agents-framework-tools.md` | 11 | §10 |
| `hello-agents-framework-core.md` | 7 | §8 |
| `README.md` / `notes-survey.md` / `hello-agents-deep-read-part2.md` | 5 | 散见 |

## 3. 目的地聚类（按同行提到的落点统计，指示优先级）

| 目的地 | 提及次数 | 说明 |
|---|---:|---|
| `D-018` 闸门批次级 + fail-closed 读入边界 | 10 | 多为「闸门位置」「留痕失败即作废」类 |
| `rules/failure-modes.md` | 9 | 多为「测试通过但 bug 仍在」的机制，F-2 的机械化尤其集中 |
| `D-016` 映射表 schema | 8 | 封闭取值域、运行时生成 `Literal` |
| `D-012` 评测集冻结 | 8 | 文档与代码焊死、产物级之外的粒度 |
| `rules/pitfalls.md` | 7 | 已从 12 行补到 52 行，仍有增量 |
| `rules/commands.md` | 7 | 门禁类，第五道门已落一条 |
| `D-017` 自建封闭解析器 | 6 | 封闭节点集、`eval()` 排除 |
| `ARCHITECTURE.md` §8 新增小节 | 6+ | 见下方 T-2 |
| `AC-05` 证据链字段 | 6 | 口径已于 2026-08-22 写死为「字段有真值」 |
| `D-015` / `D-003` / `D-013` / `D-009` / `AC-08` / `PROJECT_SPEC §5` | 各 2–5 | — |

## 4. 已经点名、可直接执行的具体条目

这几条在读的过程中被明确指认过，**不需要再判断该不该做**：

| # | 内容 | 目的地 | 出处 |
|---|---|---|---|
| **L-1** | `ARCHITECTURE §8.5` 缺上游那一半：**留痕写不进去 ⇒ 决定作废**（现在只写了「指针必须被下游消费」） | `ARCHITECTURE §8.5` | `docs-part2`（`approval.md:122-126`） |
| **L-2** | `ARCHITECTURE §8.5` 缺「**指针要说明自己是怎么被选出来的**」——glob 抽样三个各自正确的行为合成假象 | `ARCHITECTURE §8.5` | `notes-part3` §C.0 F-i（glob 抽样那一篇；**该文用 `B-nn` 编号自己的 bug-fix 条目，与台账 B 区无关，故此处不写裸编号**） |
| **L-3** | `ARCHITECTURE §8.1` 需校正：参数不可改写是**四道锁**，签名闭合只是第一道，载荷必须冻结 | `ARCHITECTURE §8.1` | `docs-part2`（`ToolDispatchExecution`） |
| **L-4** | **F-2 的机械化实现**：门禁应拒绝「非空但省略/忽略 reporter 的检查」与模板化空实现 | `rules/failure-modes.md` + 新门禁 | `docs-part2`（`invariants.md:59`） |
| **L-5** | 「**A guard only guards if the regression actually fails it**」升格为通用程序：造回归 → 看红 → 回退 | `rules/commands.md` | `docs-part2`（`testing.md:34`） |
| **L-6** | **生成式「谁发/谁听」矩阵**，用必然暴露断线的表代替「要求接线」的规则 | 新增决策（编号待分配） | `docs-part2`（`event-producer-consumer.md:76`） |
| **L-7** | 引用散文必须**同时贴可 grep 的原文字面量**——ch9 勘误 10 条里 7 条落在无代码的散文段 | `references/README.md` | `ch09-context` §12.5 |
| **L-8** | `D-012` 的 SHA-256 只到**产物级**，盖不住「文档说 7 项、代码已 8 项」这个粒度 | `D-012` | `docs-part2`（`development.md:163-171`） |

## 5. 任务（按依赖顺序，**均未开始**）

- **T-1 逐条去重归并**：把 10 份产物的启示节过一遍，产出去重后的条目清单
  （编号、内容、目的地、是否与已有决策冲突）。**这是其余任务的前置**，
  因为 131 这个数字现在还不能当待办数用。
- **T-2 `ARCHITECTURE §8` 补齐**：至少 L-1 / L-2 / L-3 三条已明确。
- **T-3 门禁类**：L-4（F-2 机械化）与 L-5（假闸门验证程序）。
  第五道门（阅读台账，N-31）已于 2026-08-23 落地，是这一类的第一条。
- **T-4 与 Phase 1.5 计划合流**：T-1 的清单里凡是影响抽取器/映射表/计算层设计的，
  必须在 `/gsd-plan-phase 1.5` 出 PLAN **之前**并入，否则又是「读了没用上」。

## 6. 这份文件的失效条件

当 T-1 完成、去重清单落进 `OPEN-ITEMS.md` 或各阶段 PLAN 之后，
**本文件降级为历史记录**，不再作为路由入口——避免它变成第二份权威。
