# references/ — 外部项目的可借鉴点

**这里只放「读过外部项目之后、对本项目有用的结论」，不放代码搬运。**

三条硬规则：

1. **不搬代码、不搬语料。** 只沉淀机制思想与踩过的坑（D-004 对 `data secret` 的规则，
   同样适用于这里的每一个外部项目）。
2. **每条必须标注**「已读到什么程度」。读了 1/16 章就写 1/16，不假装读完。
3. **每份产物必须指出落地点。**（2026-08-22 新增，因为量过一次账，发现沉淀严重不均）
   每条「可借鉴点」后面要写它**落到了哪个权威文档的哪一条**（`D-0xx` / `SC-x` / `AC-xx` /
   `EVAL_CASES` 某节 / 某个测试），或者明写 **`未落地`**。
   **只有 `未落地` 是允许的第二种答案，「读过了」不是。**
   理由：2026-08-22 量账发现——`OPEN-ITEMS.md` 里有 84 处外部证据引用，
   而 `EVAL_CASES.md` 里是 **0**，尽管 hello-agents 第 12 章 2743 行早已全文读完。
   笔记攒在台账里 ≠ 进了项目。

4. **区分「他们怎么做」与「我们要怎么做」。** 后者必须给理由，尤其是**刻意不借**的地方——
   偏离通用做法而不写理由，下一个人会以为是疏漏然后「修好」它。

| 文件 | 对象 | 读到什么程度 |
|---|---|---|
| `cninfo.md` | `kevin1000x/cninfo-financial-analyzer` + `cninfo-analyzer-web` | 下载链路与 PDF 抽取**实跑验证过**；`api/main.py` SSE 端点读原文；pipeline / metrics / financial_data_sources 读关键路径；web README 与部署链路读完。未读 `text_analyzer.py`、测试、`docs/superpowers/` |
| `hello-agents.md` | `datawhalechina/hello-agents` | **Ch12 评测（2743 行）读原文**；Ch7 只读过工具摘要（标注为二手）。Ch1-6 / 8-11 / 13-16 未读 |
| `hello-agents-ch09-context.md` | 同上，**第 9 章「上下文工程」（2819 行）** | **除 §9.6.3（410 行，见 `hello-agents-deep-read-part4.md` §4）外全章读原文**，逐节覆盖表见该文件开头。书稿钉 `hello-agents[all]==0.2.8`，比对基准为 `V0.2.8` tag（`V0.2.8:context/` 只有 `__init__.py`+`builder.py`，`truncator.py`/`history.py` 是 1.0.0 才有）。另读原文：`V0.2.8` 的 `builder.py`(353)、`note_tool.py`(518)、`terminal_tool.py`(230)，以及书仓 `code/chapter9/` 的 `codebase/`(5 文件 358 行)。**2026-08-23 已对正文 235 处 `ch9:` 引用做全量行号复核**，改正 10 处偏移 + 6 处区间，「原文未找到」0 处，见该文件 §12 勘误表 |
| `deepseek-harness.md` | `deepseek-ai/deepseek-harness` | `architecture.md`(129) + `subsystems/tools.md`(720) + `subsystems/session.md`(849) + `tool-execution-pipeline.md`(62) **均读原文**。Cordis primer、`agent-lifecycle.md`、源码未读 |
| `deepseek-harness-docs-part2.md` | 同上，`docs/` 续读第 2 轮（commit `47f9438`） | **全文读完 10 份**：`subsystems/tools.md`(720)、`tool-execution-pipeline.md`(62)、`event-producer-consumer.md`(76)、`testing.md`(49)、`development.md`(171)、`subsystems/invariants.md`(88)、`subsystems/README.md`(55)、`defensive-patterns.md`(33)、`postmortem/README.md`(18)、`postmortem/0001`(113)。**部分读 3 份**：`subsystems/approval.md`(170 读约 90)、`subsystems/subagent.md`(734 读约 55)、`cookbook/extension-cookbook.md`(读 2 行)。`subsystems/` 其余 **41 页仅标题**；`capability-seams.md` / `config-catalog.md` / `module-graph.md` / `tool-catalog.md` / `cordis-*` 等 **17 项未读**。逐份覆盖表见该文件开头 |
| `deepseek-harness-notes-part3.md` | 同上，`.agents/notes/` 精读第 3 轮（commit `47f9438`） | **`implemented/simplification` 46/46 有逐篇正文条目（S-01…S-46），可核对**；**`implemented/bug-fix` 只有 24/76 有正文条目（B-01…B-24），其余 52 篇状态 `UNVERIFIED`**（该文件覆盖表原写 75/76，与正文条目数不符，已在文首与 §L 就地更正）。§C 启示 27 条（20 借鉴 / 7 刻意不借），其中 `未落地` 13 条 |

## 为什么建这个文件夹

2026-08-15 的会话里，同一类错误犯了三次：**用「代码里没有」去断言「实际没有」**。

- 判「cninfo 审计意见零命中」→ 错，年报 PDF 里本来就有，缺的是抽取器
- 判「cninfo 只有 roa/ocf 两个字段」→ 错，那是 AKShare 路径的窄化选择，不是能力上限
- 判「cninfo 没用 HuggingFace」→ 错，后端部署在 Pages secret 里，仓库根本不写

三次都是**读了几行就下结论**。这个文件夹的存在是为了把「读到哪」和「据此能断言什么」
绑在一起：**没读到的部分不许出现在结论里。**

**第二次教训（同日）**：建完这个文件夹之后，我第一版三份文件里有两份是照着
**工具生成的摘要**写的，不是原文——然后如实标注了「只读了 1/16 章」就当交差了。
操作者指出「我让你研读的三个项目你又随便看看吗」。

**如实标注读得少 ≠ 读过。** 标注是为了防止越界断言，不是用来替代阅读的。
本轮已补读原文，各文件的「读到什么程度」已按原文重写。
