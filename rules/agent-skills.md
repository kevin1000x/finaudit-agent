# Agent skills 与 Hook 分工

## Agent skills

### Issue tracker

GitHub Issues on `kevin1000x/finaudit-agent`（私有），用 `gh` CLI。与 `.planning/`（阶段）职责不重叠：**推阶段 → GSD；其余 → issue。**（~~改规格 → OpenSpec~~ 已随 `D-042` 删除。） 见 `docs/agents/issue-tracker.md`。

### Triage labels

五个 canonical 标签，仓库原先无 label 故无冲突：`needs-triage` / `needs-info` / `ready-for-agent` / `ready-for-human` / `wontfix`。见 `docs/agents/triage-labels.md`。

### Domain docs

Single-context，但**不建 `CONTEXT.md` 与 `docs/adr/`**——决策权威是 `DECISIONS.md`，术语表是 `PROJECT_SPEC.md` §2.1，另建会造出第二个决策落点（D-009）。ADR 以追加 D-0xx 条目的形式落在 `DECISIONS.md`。见 `docs/agents/domain.md`。

## Skill 与 Hook 的分工

- **Prompt = preference，Hook = policy。** 必须每次执行的动作写进 hook，不要写进提示词。
- 计划配置的 hook（等真实失败模式出现后再加，不要一次配 30 个）：
  - `PostToolUse(Edit|Write)` → 非公开数据扫描（D-010 的机械执行）
  - `Stop` → 若本轮改了 `metrics/` 下的口径定义，要求给出版本号变更说明
- 重复出现的多步骤流程 → 做成 Skill，不要塞进 CLAUDE.md。
