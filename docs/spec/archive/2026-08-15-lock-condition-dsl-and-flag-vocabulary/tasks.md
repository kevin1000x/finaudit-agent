> 本变更**不产出代码**，也**几乎不改变任何已实现的行为**——它把 01-01 已实现且已测的事实写成规范。
> 因此等价红测不是「让某物不合规」，而是**反向核对**：规格逐条对照 `dsl.py` 的白名单常量，
> 若出现规格描述而实现没有、或实现有而规格没写的构造，即措辞与实现不符。
> 判据是 apply 后 `pytest -q` 仍全绿（40 passed）——规格若真改了行为，测试会红。
>
> **反向核对确实查出一处（OQ-02），已在 `proposal.md` 显式声明，未隐藏。**

## 1. 前置校验

- [x] 1.1 `cd docs/agent/poc-01 && sha256sum -c SHA256SUMS`
      → **5/5 OK，exit 0**
- [x] 1.2 `git status --porcelain` 干净，记录基线
      → **干净，基线 `d6a98b2`**
- [x] 1.3 `.venv/Scripts/python -m pytest -q` 全绿
      → **40 passed**

## 2. 反向核对：规格措辞 vs 实现白名单

核对方式：直接 import `dsl` 打印白名单常量，再用 17 条断言实跑解析器与求值器。

- [x] 2.1 根命名空间 ⇔ `ROOT_NAMESPACES` / `INTRINSIC_NAMESPACES`
      → 数据侧 `['bs','cfs','is','notes']`、元数据侧 `['comparison_period','metric','standard_basis']`，**一致**
- [x] 2.2 六个比较运算符 ⇔ `_COMPARE_OPS`
      → `['!=','<','<=','==','>','>=']`，**一致**
- [x] 2.3 逻辑运算符 ⇔ `_KEYWORDS`
      → `['and','not','or']`，**一致**
- [x] 2.4 唯一谓词 ⇔ `_PREDICATES`
      → `['is_missing']`，**一致**
- [x] 2.5 字面量集合 ⇔ `_LITERAL_NAMES` 加数值与字符串记号
      → `['false','null','true']` + NUMBER / STRING，**一致**
- [x] 2.6 「根必须产出布尔值」⇔ `_BOOLEAN_ROOTS`
      → `[IsMissing, Compare, Not, And, Or]`，裸字段引用与裸字面量均被拒，**一致**
- [x] 2.7 fail-closed 求值语义 ⇔ `MissingOperandError`
      → `evaluate(parse("bs.total_assets > 0"), {})` 抛 `MissingOperandError`；
        `is_missing(bs.total_assets)` 对空行返回 `True`；`{total_assets: 0}` 返回 `False`
        （**零与缺失确实走不同分支**），**一致**
- [x] 2.8 词表五键与 `scope` 取值 ⇔ `vocabulary.py` 与 `metrics/_flags.yaml`
      → **不一致，见 2.9**
- [x] 2.9 **判定**
      → 17 条 DSL 断言 **17/17 与规格一致**，0 项不符。
        词表侧查出一处**规格领先实现**：`Flag` dataclass 把五个键都声明为必需，
        但 `load_vocabulary()` 只真强制 `name`（KeyError）与 `scope`（校验 raise）；
        `description` / `affects_comparability` / `introduced_by` 三个键**静默补默认值**。
        其中 `affects_comparability` 补 `False` 方向最坏——漏写该键的 flag 会被当成
        「不影响可比性」，本该阻断跨期比较的标记悄悄不阻断且不报错，与 POC-01 C4 同型。
        当前 10 条 flag 全部写齐五键，故**现无实际错误**；风险在将来新增时漏写。
        **按 ARCHITECT 模式不在本变更改实现**，记入 `docs/agent/phase-01/open-questions.md` OQ-02。
        操作者裁决：**并入 01-03，wave 3 开写 19 份定义前关掉。**

## 3. 契约落地

- [x] 3.1 spec delta 合并进 `openspec/specs/semantic-layer/metric-definition/spec.md`
      → `openspec archive` 输出 `+ 0, ~ 2, - 0, → 0`；合并后 `grep -c '^### Requirement:'` = **9**，不多不少
- [x] 3.2 §5.1「全局 flag 词表」段落的待定措辞替换为确定结论
      → 词表位置 `metrics/_flags.yaml` + 五键表格 + `scope` 语义 + 从属声明 + 放独立文件的理由
- [x] 3.3 §5.1 补「条件表达式的规范语法」小节
      → 能力边界表（含**不允许**一行）、根须产出布尔、fail-closed 求值语义、
        以及留空该语义的具体后果（与 C4 同型的静默错误）
- [x] 3.4 核对 §9 AC-01 是否与新 spec 漂移
      → **无漂移**，AC-01 原文「`flags`（引用全局词表，带可求值触发条件）/ `undefined_conditions`（可求值）」
        与新 spec 一致，只是更概括，不冲突，**未改动**。
        另发现 **AC-04 与本会话早些时候的 D-012 修订不一致**（未提前置门禁与作废率），
        属另一件事的收尾，已在同一提交内一并补上并注明。

## 4. 后置校验

- [x] 4.1 `openspec validate --all --strict`
      → **1 passed, 0 failed，exit 0**
        （计划原文写的是 `openspec validate --strict`，archive 之后无活动变更，
        该命令报 "Nothing to validate" 并返回非零。**这是计划里的命令写错，不是校验失败**，
        正确的等价命令是 `--all --strict` 或 `--specs --strict`，两者均 exit 0）
- [x] 4.2 `grep -c 'metrics/_flags.yaml' PROJECT_SPEC.md` → **1**（≥ 1）
- [x] 4.3 `grep -c '候选：本文件内' PROJECT_SPEC.md` → **0**
- [x] 4.4 `.venv/Scripts/python -m pytest -q` → **40 passed**
- [x] 4.5 `.venv/Scripts/python -m semantic_layer validate` → **exit 0**
- [x] 4.6 冻结 → **5/5 OK**；`git status --porcelain docs/agent/poc-01/` **为空**
- [x] 4.7 `git diff --numstat HEAD -- src/ metrics/ tests/` → **0 行**，本变更未触碰实现

## 5. Archive

- [x] 5.1 `openspec archive lock-condition-dsl-and-flag-vocabulary --yes`
      → 归档为 `2026-08-15-lock-condition-dsl-and-flag-vocabulary`
- [x] 5.2 `openspec list` 不再含本变更（grep 计数 0）；`openspec validate --specs --strict` **exit 0**
