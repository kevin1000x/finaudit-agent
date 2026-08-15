# references/ — 外部项目的可借鉴点

**这里只放「读过外部项目之后、对本项目有用的结论」，不放代码搬运。**

三条硬规则：

1. **不搬代码、不搬语料。** 只沉淀机制思想与踩过的坑（D-004 对 `data secret` 的规则，
   同样适用于这里的每一个外部项目）。
2. **每条必须标注**「已读到什么程度」。读了 1/16 章就写 1/16，不假装读完。
3. **区分「他们怎么做」与「我们要怎么做」。** 后者必须给理由，尤其是**刻意不借**的地方——
   偏离通用做法而不写理由，下一个人会以为是疏漏然后「修好」它。

| 文件 | 对象 | 读到什么程度 |
|---|---|---|
| `cninfo.md` | `kevin1000x/cninfo-financial-analyzer` + `cninfo-analyzer-web` | 下载链路与 PDF 抽取**实跑验证过**；pipeline / metrics 读过关键路径；web 端 README 与部署链路读完 |
| `hello-agents.md` | `datawhalechina/hello-agents` | **16 章只读了第 7 章 + README**，严重不足，待补 Ch8 / Ch10 / Ch12 |
| `deepseek-harness.md` | `deepseek-ai/deepseek-harness` | `docs/architecture.md` 读完；packages 清单看过；子系统文档未读 |

## 为什么建这个文件夹

2026-08-15 的会话里，同一类错误犯了三次：**用「代码里没有」去断言「实际没有」**。

- 判「cninfo 审计意见零命中」→ 错，年报 PDF 里本来就有，缺的是抽取器
- 判「cninfo 只有 roa/ocf 两个字段」→ 错，那是 AKShare 路径的窄化选择，不是能力上限
- 判「cninfo 没用 HuggingFace」→ 错，后端部署在 Pages secret 里，仓库根本不写

三次都是**读了几行就下结论**。这个文件夹的存在是为了把「读到哪」和「据此能断言什么」
绑在一起：**没读到的部分不许出现在结论里。**
