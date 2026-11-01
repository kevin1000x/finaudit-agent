@AGENTS.md

<!--
维护说明（块级 HTML 注释不进模型上下文，只给人看）：
- 依据 code.claude.com/docs/en/memory 与 /docs/en/best-practices（2026-11-01 读）：
  只写读代码推不出来、或每次会话都要重新挖一遍的东西；每一行都进每一次会话的上下文。
- @AGENTS.md 是导入，导入不省上下文。本文件 + AGENTS.md 合计控制在 200 行以内。
- 必须零例外的规矩做成 hook 或权限规则，不要在这里加粗、加感叹号。
- 本机才有的路径（仓外工作记录）写在 CLAUDE.local.md，已 gitignore。
- 新增一条之前问两句：读代码能不能发现？Claude 会不会真去读？两个都是「会」就不写。
-->

# Claude Code 补充

上面导入的 `AGENTS.md` 是跨 Agent 的地图与硬规则。这里只放 Claude Code 需要、读代码推不出来的东西，
每条写了来由。发现某条过期了就改它并写明新事实，不要绕过它，也不要守着它把事卡住。

## 怎么算做完

- 提交前跑 CI 的五道门，**最后一次改动之后从头跑一遍**。只改 markdown 也要跑：pytest 里有查 markdown 的用例。

  ```bash
  .venv/Scripts/python -m pytest -q && .venv/Scripts/python -m semantic_layer scan && .venv/Scripts/python -m semantic_layer validate && .venv/Scripts/python scripts/check_xrefs.py && .venv/Scripts/python scripts/check_gates.py
  ```

  读数是 pytest 的 `N passed` 加整条退出码 0。全量 pytest 要 3–5 分钟，放后台跑，输出重定向到文件。
- 动了 `src/agent/` 或 `eval/`：再跑 `.venv/Scripts/python -m eval.verify_run --suite frozen-04`，期望 18/18、退出 0。
  `--suite frozen-03` 退 3 是对的（整批作废，`D-045`），不要引用它的分数。
- 门禁后面不接管道：`| tail` 之后的退出码是 `tail` 的。截输出就重定向到文件再读。
- 会话结束前，测试数、门禁条数或决策编号变了，就同步 `.planning/STATE.md` 的 frontmatter 与「当前规模」表。
  那张表落后于事实已经三次（2026-08-28、09-11、11-01），每次都是做了没回标，没有检查会发现。
- 单个文件：`.venv/Scripts/python -m pytest tests/test_verify.py -q`

## 本仓特有的坑（都真栽过）

- **pytest 在跑时不要再起 python 进程，也别加 `-I`**：`-I` 让 `PYTHONDONTWRITEBYTECODE` 失效，
  字节码写进 `src/**/__pycache__`，`tests/test_conformance.py` 当场红两条（2026-10-31）。
  临时脚本写进 scratchpad，带 `PYTHONDONTWRITEBYTECODE=1` 跑。
- Bash 工具把中文输出显示成乱码：python 加 `-X utf8`，结果写进文件，用 Read 看。
- 往文件里写反斜杠用 `chr(92)`；用 Python 整文件改写时先写临时文件再 `os.replace`（病例在 `rules/commands.md`）。
- **冻结题的期望值不能从系统输出抄**，那是 `D-012` 禁止的「迁就模型」；拿不到独立来源就只钉 `metric_id`。
  长小数要加引号：YAML 读成 float 会静默截到 17 位（2026-10-31 因此丢弃过一次冻结）。
- **不要往 `metrics/*.yaml` 加新键**：新键默认进口径指纹 ⇒ 必须升 `version` ⇒ `frozen-01` 有 14/20 题
  钉在 `metric_version: 2` 上。不改变计算结果的元数据放 `metrics/_` 开头的旁表（`_flags.yaml`、`_basis_choice.yaml`，`D-045`）。
- `src/agent/intent.py` 与 `verify.py` 里的词表原则上只用于**拒答方向**；唯一放行方向的那张
  （`_SUBJECTLESS_WORDS`）门槛写在 `D-046`。改这两个文件先读模块抬头。
- 线上演示不随 `main` 更新：`scripts/build_space_payload.py` 只生成载荷，部署由操作者做。
  没在这一轮亲眼验过线上，就不说「线上已修好」。

## 判断上的三条纪律（各在一天里犯过三次）

1. 不对操作者的系统下「没有 X」的判断。部署配置、密钥、运行时环境、数据内容不在仓库里，
   只能说「我在仓库里没搜到 X」。
2. 只有真实字段能诚实触发时才声明 flag。拿手边能求值的东西凑一个 trigger，造出的是永远不会正确触发的假规则。
3. 被要求研读时读原文。没读完就说没读完，不要把读了一部分标成读过。

## 先问再做（本项目特有的那几件）

- 部署线上演示（对外可见）。
- 扩范围：例如加审计意见 / 关键审计事项抽取。名字里的 `audit` 指「可审计」，不是审计业务（README「已知边界」）；
  要不要往那边走是操作者的决定，不是执行者顺手做的事。
- 会话开始声明阶段模式（`rules/modes.md`）；没声明时不写生产代码。

## 细则在哪

| 文件 | 什么时候读 |
|---|---|
| `rules/commands.md` | 跑评测、冻结题集、H2 复核器械，或要「造回归 → 看红 → 回退」验证一道门时 |
| `rules/modes.md` | 切换模式、计划与现实不符、要宣告完成时 |
| `rules/pitfalls.md` | 做架构决策、动数据源、做图、做界面之前 |
| `rules/agent-skills.md` | 建 issue、配 hook 时 |
