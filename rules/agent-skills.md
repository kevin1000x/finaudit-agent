# Agent skills 与 Hook 分工

## Agent skills

### Issue tracker

GitHub Issues on `kevin1000x/finaudit-agent`（公开仓，`D-005` 修订三；issue 同样公开可见），用 `gh` CLI。与 `.planning/`（阶段）职责不重叠：**推阶段 → GSD；其余 → issue。**（~~改规格 → OpenSpec~~ 已随 `D-042` 删除。） 见 `docs/agents/issue-tracker.md`。

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

## 冻结集的写入 deny 规则（`N-98`，2026-11-10）

`.claude/settings.json` 的 `permissions.deny` 把 `D-012` 的冻结集挡在 Claude Code 的内建编辑工具之外
（`Edit(...)` 规则同时作用于 Edit / Write / NotebookEdit）：

- `eval/frozen-01…04/` 各三条：`cases/**`、`fixtures/**`、`SHA256SUMS`。**逐套件列，不用 `frozen-0*` 通配**：
  通配会把冻结**之前**给新套件写题面的那一步也挡住。
- `docs/agent/poc-01/`：除 `FREEZE.md` 外逐项列出（定义、题目、字段清单、回答、对比、清单）。
- **仍然可写**：`VOIDED.yaml`（整批作废；`frozen-03` 就是这么作废的，`D-045`）与 `FREEZE.md`（只追加的冻结记录）。
- **实测**（2026-11-10，本机）：往 `eval/frozen-04/cases/` 新建文件被拒；单文件形式的规则同样被拒；
  同一套件根目录下不在规则里的文件照常可写。

**它挡不住的**：Bash 与脚本写入不走这些规则（`eval.freeze` 本身就是脚本）。真正的护栏仍是哈希校验
（`tests/test_conformance.py` 里的两条，加上 CI 的冻结校验）；deny 规则只把「一次手滑的 Edit」挡在发生之前。

**有意挡住的合法动作：逐题 `voided:`。** 逐题作废要改题面文件和 `SHA256SUMS`（`EVAL_CASES.md` §2.2–2.3），
这两处都在规则里。这是有意的：逐题作废正是「迁就模型」最容易混进来的口子。执行者写出 §2.2 的论证
（不看系统输出就能成立），由操作者动手；或者操作者在对话里明确指示执行者用脚本改，提交说明里写明是哪条指示。

**新冻结一个套件之后**补它的三条规则。漏了，`test_冻结集的承重文件都在写入deny规则里` 会一直红到补上：
它以磁盘上的 `SHA256SUMS` 为基准，不是写死的套件名。

没纳入的：`docs/agent/h2-*`（`answer-sheet.yaml` 要由复核人回填）与 `eval/testdata/`（测试夹具），
它们的哈希照样在校验里。
