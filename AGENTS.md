# AGENTS.md — finaudit-agent

跨 Agent 的项目地图。**这是地图，不是手册**：只放不可推断的事实与入口，知识存在 Artifact 里，按需读取。

## 这个项目是什么

**可审计的财务分析 Agent。** 给定公开上市公司年报与财务数据，用自然语言提问，Agent 给出答案，**并且每个答案都附带可独立复核的证据链**：用了哪张表、哪个指标口径、依据哪条准则、执行了什么、结果哈希是什么。

它不是通用 data agent，不是 ChatBI，不是 NL2SQL 包装。差异化在于：**通用 Agent 答不出「这个口径对不对」，它能答，而且能证明。**

## 文档优先级（冲突时上位覆盖下位）

1. `PROJECT_SPEC.md` — 规格、假设、验收标准 AC-01…、停止条件
2. `DECISIONS.md` — 已接受决策 D-001…，提任何设计变更前先查
3. `EVAL_CASES.md` — 评测协议、问题集、失败归因分层、判定门
4. `.planning/` — GSD 阶段状态（ROADMAP / STATE / phases），**只汇总与路由，不覆盖上面三份**
5. `openspec/` — 变更提案（proposal / tasks / design），单个变更的落地契约

`docs/agent/` 是阶段 Artifact（IDEA / RESEARCH / ARCHITECTURE / POC / PROGRESS / VERIFICATION），是跨阶段接口，不是规格。

## 硬规则

- **数据来源只允许公开数据**（巨潮资讯网年报、AKShare 公开财务指标）。任何雇主内部数据、实习期间接触的数据、客户数据一律禁止进入本仓库——包括脱敏后的。见 D-010。
- **不复制 `data secret` 的代码、语料或评测结论。** 可以复用其机制思想（SHA-256 双校验、fail-closed、证据隔离），但两个项目的仓库、语料、结论完全隔离。见 D-004。
- **证据链是第一类产物，不是日志。** 任何回答如果给不出证据链，视为失败，不视为"降级成功"。见 D-003。
- **不设时间预算上限。** 每次会话在 `docs/agent/PROGRESS.md` changelog 记录**实际做了什么**（已发生的事实，不是计划）。范围决策依据产出与假设验证进度，不依据剩余小时数。见 D-008（2026-08-10 修订）。
- **阶段模式必须显式声明**：`DISCOVER / RESEARCH / ARCHITECT / POC / PLAN / IMPLEMENT / VERIFY / REVIEW`。不要在 RESEARCH 模式里写实现，不要在 IMPLEMENT 模式里改架构。
- **完成必须有证据。** 不接受"应该可以了"。见 `PROJECT_SPEC.md` §完成定义。

## 工作流入口

| 我要做什么 | 用什么 |
|---|---|
| 把一个模糊想法变成问题定义 | Superpowers `brainstorming` skill → 写入 `docs/agent/IDEA.md` |
| 规划一个阶段 | GSD `/gsd-plan-phase` → `.planning/phases/` |
| 执行一个阶段 | GSD `/gsd-execute-phase` |
| 做一个小改动 | GSD `/gsd-quick` |
| 提一个功能变更提案 | OpenSpec `/opsx:propose` → `openspec/changes/` |
| 实现已批准的提案 | OpenSpec `/opsx:apply` |
| 写实现代码 | Superpowers `test-driven-development` skill |
| 调 bug | Superpowers `systematic-debugging` skill |
| 独立复核 | Superpowers `requesting-code-review` + fresh context |
| 声明完成前 | Superpowers `verification-before-completion` skill |

三套方法论的分工（D-009）：
- **GSD** 拥有阶段状态与进度（`.planning/`）
- **Superpowers** 提供行为门禁（设计澄清、TDD、完成前验证、独立评审）
- **OpenSpec** 提供单个变更的规格契约（proposal → tasks → apply → archive）

三者不得为同一件事创建重复的权威文档。

## 环境

- Python 3.11+（本项目独立于 `data secret` 的 3.8.5 冻结环境，不受其约束）
- 上游数据源：巨潮资讯网、AKShare
- 已有可复用资产：`kevin1000x/cninfo-financial-analyzer`（PUBLIC，Python，23 文件 / 8310 行）
  —— 已于 2026-08-10 克隆到 `../cninfo-financial-analyzer`（与本仓库平级，**不在本仓库内**）
  —— **有**：Fog 指数（中文适配 Gunning-Fog，`src/text_analyzer.py`）、中文金融情感词典
     （`data/dictionaries/`，按 NOTICE.md 引用）、年报下载与 PDF 解析、pipeline + CLI、AKShare + Supabase 缓存
  —— **没有**：审计意见数据（零命中）；README 无任何实证结论
  —— **财务字段极窄**：`METRIC_COLUMNS = ["stock_code","year","roa","ocf"]`，只有 ROA 与 OCF，
     没有三表明细字段。Phase 1 的语义层**不能直接建在它现有数据层上**，须先扩数据层
  —— **PDF 侧能力比数据侧强**：`src/pdf_parser.py` 已有 pdfplumber/PyMuPDF/OCR 三条文本路径、
     表格抽取（pdfplumber，可选 camelot/tabula）、章节抽取（`extract_mda_section`）、
     以及 `identify_financial_statement` / `extract_financial_statements` 雏形。
     **数据源的正解是年报 PDF 本身，不是 AKShare**——见 D-013。
- 易混淆仓库（别搞错）：
  - `cninfo-analyzer-web`（TypeScript）是上面那个的 **Web 前端**，已克隆到 `../cninfo-analyzer-web`，用于演示
  - `privacy-preserving-agent-poc`（PRIVATE）就是 `data secret`，**D-004 禁止读取、复制、引用**
- 仓库：`kevin1000x/finaudit-agent`，默认分支 `main`，remote 走 HTTPS + `gh` 凭据助手
- **可见性：PRIVATE。** D-005 约束至 Phase 4。改为公开是**决策变更**，必须先修订 D-005，不得顺手 `gh repo edit --visibility public`
- `.gitattributes` 强制 LF 入库：冻结文件的 SHA-256 必须跨平台稳定，这是 D-012 的物理保障，不要改

## 当前状态

见 `.planning/STATE.md`。当前阶段：**Phase 0 — cninfo 实证结论**（不写新代码）。
