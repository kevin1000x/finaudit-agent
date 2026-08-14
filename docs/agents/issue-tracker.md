# Issue tracker: GitHub

Issues and specs for this repo live as GitHub issues on `kevin1000x/finaudit-agent` (**private**). Use the `gh` CLI for all operations.

> **本仓库补充**：issue tracker 与 `.planning/`（GSD 阶段状态）、`openspec/changes/`（变更契约）
> **职责不重叠**——前者承载 bug、临时请求、待办线索；后者两个分别承载阶段与规格变更。
> 三者不得为同一件事创建重复记录（D-009）。
> 判断规则：**改规格 → OpenSpec；推阶段 → GSD；其余 → issue。**

## Conventions

- **Create an issue**: `gh issue create --title "..." --body "..."`. Use a heredoc for multi-line bodies.
- **Read an issue**: `gh issue view <number> --comments`, filtering comments by `jq` and also fetching labels.
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` with appropriate `--label` and `--state` filters.
- **Comment on an issue**: `gh issue comment <number> --body "..."`
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Close**: `gh issue close <number> --comment "..."`

Infer the repo from `git remote -v` — `gh` does this automatically when run inside a clone.

## Pull requests as a triage surface

**PRs as a request surface: no.** _(Set to `yes` if this repo treats external PRs as feature requests; `/triage` reads this flag.)_

> 本仓库为私有单人仓（D-005 约束至 Phase 4），无外部贡献者，因此保持 `no`。

## When a skill says "publish to the issue tracker"

Create a GitHub issue.

## When a skill says "fetch the relevant ticket"

Run `gh issue view <number> --comments`.

## 本仓库的硬约束（写 issue 前必读）

- **D-010 不可协商**：issue 正文中**禁止**出现任何雇主内部数据、实习期间接触的数据、客户数据——
  包括脱敏后的字段名与表结构。仓库私有不构成豁免。
- **D-012**：已冻结的评测题目与标准答案不得通过 issue 讨论修改。发现题目本身有误 →
  作废并公开记录（标 `VOIDED`），不修改后重用。
- 声明「完成/修好了」的 issue 评论必须附**真实命令与真实输出**，没跑就写 `UNVERIFIED`
  （见 `PROJECT_SPEC.md` §11）。
