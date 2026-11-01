# AGENTS.md — finaudit-agent

跨 Agent 的项目地图。**这是地图，不是手册**：只放不可推断的事实与入口，知识存在 Artifact 里，按需读取。

## 这个项目是什么

**可审计的财务分析 Agent，产品形态是「结论核查入口」**（`D-041`）：粘一段财报分析结论进来，
系统拆成可核声明、**逐条判定**（五态封闭集：一致 / 不一致 / 口径未声明 / 核不了 / 不是可核声明），
每条都附**可独立复核的证据链**：用了哪张表的哪一页哪一列、哪个指标口径（含版本）、依据哪条准则、
读到的字段取值、年报 PDF 的 SHA-256。不带数的输入就是提问，走同一条路径。

它不是通用 data agent，不是 ChatBI，不是 NL2SQL 包装。差异化在于：**通用 Agent 答不出「这个口径对不对」，它能答，而且能证明。**

## 文档优先级（冲突时上位覆盖下位）

1. `PROJECT_SPEC.md` — 规格、假设、验收标准 AC-01…、停止条件
2. `DECISIONS.md` — 已接受决策 D-001…，提任何设计变更前先查
3. `EVAL_CASES.md` — 评测协议、问题集、失败归因分层、判定门
4. `.planning/` — GSD 阶段状态（ROADMAP / STATE / phases），**只汇总与路由，不覆盖上面三份**
5. `docs/spec/` — **已生效的行为契约**（`semantic-layer/metric-definition/spec.md` 的 9 条 Requirement）
   与已归档的三个变更提案。⚠️ **OpenSpec 已于 2026-09-11 删除**（`D-042`）——
   这里保留的是它写下的**事实**，不是它的流程；新变更不再走提案，走 `DECISIONS.md`。

`docs/agent/` 是阶段 Artifact（IDEA / RESEARCH / ARCHITECTURE / POC / VERIFICATION / EVAL-REPORT + 各阶段证据），是跨阶段接口，不是规格。
⚠️ 其中的**工作记录**（PROGRESS / OPEN-ITEMS / LANDING-BACKLOG / DELEGATED-DECISIONS）
已于 2026-09-11 移出本仓到 `../finaudit-workshop/docs-agent/`（`D-044`）。

## 硬规则

- **数据来源只允许公开数据**（巨潮资讯网年报、AKShare 公开财务指标）。任何雇主内部数据、实习期间接触的数据、客户数据一律禁止进入本仓库——包括脱敏后的。见 D-010。
- **不复制 `data secret` 的代码、语料或评测结论。** 可以复用其机制思想（SHA-256 双校验、fail-closed、证据隔离），但两个项目的仓库、语料、结论完全隔离。见 D-004。
- **证据链是第一类产物，不是日志。** 任何回答如果给不出证据链，视为失败，不视为"降级成功"。见 D-003。
- **冻结评测集不可修改**：`eval/frozen-0*/` 的题面、夹具与 `SHA256SUMS`，`docs/agent/poc-01/`。作废走 `VOIDED.yaml` / `voided:`，不改题。见 D-012。
- **不设时间预算上限。** 每次会话在 `../finaudit-workshop/docs-agent/PROGRESS.md` changelog 记录**实际做了什么**（已发生的事实，不是计划）。⚠️ 该日志与未决事项台账**已移出本仓**（`D-044`）：它们是工作记录，不进公开仓。范围决策依据产出与假设验证进度，不依据剩余小时数。见 D-008（2026-08-10 修订）。
- **阶段模式必须显式声明**：`DISCOVER / RESEARCH / ARCHITECT / POC / PLAN / IMPLEMENT / VERIFY / REVIEW`。不要在 RESEARCH 模式里写实现，不要在 IMPLEMENT 模式里改架构。
- **完成必须有证据。** 不接受"应该可以了"。见 `PROJECT_SPEC.md` §完成定义。

## 工作流入口

| 我要做什么 | 用什么 |
|---|---|
| 把一个模糊想法变成问题定义 | Superpowers `brainstorming` skill → 写入 `docs/agent/IDEA.md` |
| 规划一个阶段 | GSD `/gsd-plan-phase` → `.planning/phases/` |
| 执行一个阶段 | GSD `/gsd-execute-phase` |
| 做一个小改动 | GSD `/gsd-quick` |
| 提一个设计变更 | 写进 `DECISIONS.md`（OpenSpec 已删除，`D-042`），再用 GSD 推阶段 |
| 写实现代码 | Superpowers `test-driven-development` skill |
| 调 bug | Superpowers `systematic-debugging` skill |
| 独立复核 | Superpowers `requesting-code-review` + fresh context |
| 声明完成前 | Superpowers `verification-before-completion` skill |

**两套**方法论的分工（`D-009`，2026-09-11 经 `D-042` 做减法后）：
**GSD** 拥有阶段状态与进度（`.planning/`）；**Superpowers** 提供行为门禁（设计澄清、TDD、完成前验证、独立评审）。
两者不得为同一件事创建重复的权威文档。放弃 OpenSpec 放弃了什么、什么条件下拿回来，写在 `D-042`。

## 环境

- Python 3.11+（本项目独立于 `data secret` 的 3.8.5 冻结环境，不受其约束）
- 数据：巨潮资讯网年报 PDF 是权威源，AKShare 只作对照（`D-013`）。真实数据目前两份：
  贵州茅台 600519·2023、万华化学 600309·2019（`data/extracted/`，只导出人工逐字段核对过的字段）
- 上游项目 `kevin1000x/cninfo-financial-analyzer`（克隆在 `../cninfo-financial-analyzer`，**不在本仓库内**）：
  **本仓不 import 它的任何代码**。年报下载与 PDF 定位在 `src/extractor/` 重写过，
  它的静默错误是反面教材（`D-013`）；它用的 PyMuPDF 是 AGPL，本仓不许链接（`D-014`）。
  它的 Fog 指数、情感词典、Supabase 缓存与本项目无关。借的是托管：核查端点挂在它的 `/audit/*` 下。
- 易混淆仓库（别搞错）：
  - `cninfo-analyzer-web`（TypeScript）是上面那个的 **Web 前端**，已克隆到 `../cninfo-analyzer-web`，用于演示
  - `privacy-preserving-agent-poc`（PRIVATE）就是 `data secret`，**D-004 禁止读取、复制、引用**
- 仓库：`kevin1000x/finaudit-agent`，默认分支 `main`，remote 走 HTTPS + `gh` 凭据助手
- **可见性：PUBLIC**（2026-09-11 经操作者明确指示执行，记在 `D-005` 修订三）。
  🔴 **执行者不得擅自把它改回 PRIVATE，也不得在没有同等明确指示时改动任何仓库的可见性。**
  转公开之后**不变的**：密钥只走 secret 永不进仓库；`data/raw/` 不进版本控制；
  `D-010`（只用公开数据）与 `D-004`（不碰 `data secret`）都不解除
- `.gitattributes` 强制 LF 入库：冻结文件的 SHA-256 必须跨平台稳定，这是 D-012 的物理保障，不要改

## 当前状态

以 `.planning/STATE.md` 为准，这里不抄 —— 抄过来的阶段名会过期（2026-11-01 之前这里一直写着
「Phase 0 — 不写新代码」，而项目早已过了那个阶段）。
