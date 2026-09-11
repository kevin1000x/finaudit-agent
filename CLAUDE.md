@AGENTS.md

# Claude Code 专属补充 —— 索引

`AGENTS.md`（上面已导入）是跨 Agent 的项目地图与硬规则。
**本文件只做索引。** 细则在 `rules/`，按需读，不要一次性全读。

保持本文件在 **50 行以内**。它是路由表，不是手册。

## 每次会话开始必做

1. **声明当前模式**（`DISCOVER / RESEARCH / ARCHITECT / POC / PLAN / IMPLEMENT / VERIFY / REVIEW`）。
   模式没声明时，默认拒绝写生产代码，先问清楚。规则见 `rules/modes.md`。
2. **读 `docs/agent/OPEN-ITEMS.md`** —— 未决事项台账。A 区是阻塞项。
3. 需要历史脉络时读 `docs/agent/PROGRESS.md`（append-only，最新进展在这）。

## 细则索引

| 文件 | 内容 | 什么时候读 |
|---|---|---|
| `rules/failure-modes.md` | **已经真实犯过的 7 类错**，含识别方法与硬规则 | **每次会话开始扫一遍**，尤其在要下「X 没有 Y」这类断言、要声明 flag、要说「读完了」之前 |
| `rules/modes.md` | 模式锁表、停止协议、完成的定义 | 切换模式、遇到计划与现实不符、要宣告完成时 |
| `rules/pitfalls.md` | 本项目的高代价陷阱（预防性） | 做架构决策、动数据源、做图、做界面之前 |
| `rules/commands.md` | 常用命令（含冻结校验、门禁） | 要跑验证时 |
| `rules/agent-skills.md` | issue tracker / triage labels / domain docs / Hook 分工 | 要建 issue 或配 hook 时 |
| `rules/repo-context.md` | 与秋招资料库的关系 | 需要外部背景时 |
| `../finaudit-workshop/references/` | 三个外部项目的可借鉴点，**每份标注读到什么程度**。⚠️ **2026-09-11 移出本仓**（`D-043`），在仓外同级目录 | 做架构、PDF 抽取、前端、评测设计之前 |

## 三条最容易违反的

摘自 `rules/failure-modes.md`，因为它们在一天内各犯了 3 次：

1. **不对操作者的系统下「没有 X」的判断。** 只能说「我在仓库里没搜到 X」——
   部署配置、密钥、运行时环境、数据内容这四类天然不在代码仓库里。
2. **只有真实字段能诚实触发时才声明 flag。** 拿手边能求值的东西凑一个 trigger，
   造出的是永远不会正确触发的假规则。
3. **如实标注读得少 ≠ 读过。** 被要求研读时读原文；上下文不够就开 subagent
   用独立上下文读，不要自己挑切片再标注「只读了一部分」。

## 两条流程纪律

- **台账里的「判据」是待办不是已办。** 会话结束前扫一遍 `OPEN-ITEMS.md` 的 A 区与 D 区。
- **有背景 agent 未返回时不宣告完成。** 如实说哪几个还在跑，不预测其结论。
