> 本变更**不产出代码**，也**不改变任何已实现的行为**——它把 01-01 已实现且已测的事实写成规范。
> 因此等价红测不是「让某物不合规」，而是**反向核对**：规格逐条对照 `dsl.py` 的白名单常量，
> 若出现规格描述而实现没有、或实现有而规格没写的构造，即本变更措辞有误，改措辞不改实现。
> 判据是 apply 后 `pytest -q` 仍全绿（40 passed）——规格若真改了行为，测试会红。

## 1. 前置校验

- [ ] 1.1 `cd docs/agent/poc-01 && sha256sum -c SHA256SUMS`，5/5 OK 才继续；
      任一 FAIL 立即停止并按 EXPECTED/FOUND/IMPACT/OPTIONS 报告
- [ ] 1.2 `git status --porcelain` 干净，记录基线 commit
- [ ] 1.3 `.venv/Scripts/python -m pytest -q` 全绿，记录基线测试数

## 2. 反向核对：规格措辞 vs 实现白名单

- [ ] 2.1 规格里的根命名空间清单 ⇔ `dsl.py` 的 `ROOT_NAMESPACES` 与 `INTRINSIC_NAMESPACES`
- [ ] 2.2 规格里的六个比较运算符 ⇔ `_COMPARE_OPS`
- [ ] 2.3 规格里的逻辑运算符 ⇔ `_KEYWORDS`
- [ ] 2.4 规格里的唯一谓词 ⇔ `_PREDICATES`
- [ ] 2.5 规格里的字面量集合 ⇔ `_LITERAL_NAMES` 加数值与字符串记号
- [ ] 2.6 规格「根必须产出布尔值」⇔ `parse_condition` 的 `_BOOLEAN_ROOTS` 检查
- [ ] 2.7 规格的 fail-closed 求值语义 ⇔ `MissingOperandError` 的抛出点
- [ ] 2.8 规格的词表五键与 `scope` 取值 ⇔ `vocabulary.py` 的加载校验与 `metrics/_flags.yaml` 实际内容
- [ ] 2.9 **判定**：任一项对不上 → 记录差异，判断是规格写错还是实现少做；
      规格写错就改规格，实现少做则记入 open-questions 另提变更，**不在本变更里改实现**

## 3. 契约落地

- [ ] 3.1 把 spec delta 合并进 `openspec/specs/semantic-layer/metric-definition/spec.md`，
      确认合并后仍是 9 条 Requirement（不多不少）
- [ ] 3.2 改 `PROJECT_SPEC.md` §5.1「全局 flag 词表」段落：
      「位置在 Phase 1 有 5 个以上真实 flag 后确定（候选：本文件内 / 独立文件）」
      替换为确定结论 + 五个条目键 + 从属声明
- [ ] 3.3 在 §5.1 字段集示例之后补一小段「条件表达式的规范语法」，措辞与 R4 / R7 一致
- [ ] 3.4 核对 §9 的 AC-01 表述是否仍与新 spec 一致，有漂移在本变更内一并修正

## 4. 后置校验

- [ ] 4.1 `openspec validate --strict` 退出码 0
- [ ] 4.2 `grep -c 'metrics/_flags.yaml' PROJECT_SPEC.md` ≥ 1
- [ ] 4.3 `grep -c '候选：本文件内' PROJECT_SPEC.md` = 0
- [ ] 4.4 `.venv/Scripts/python -m pytest -q` 仍 40 passed
- [ ] 4.5 `.venv/Scripts/python -m semantic_layer validate` 退出码 0
- [ ] 4.6 `cd docs/agent/poc-01 && sha256sum -c SHA256SUMS` 5/5 OK；
      `git status --porcelain docs/agent/poc-01/` 为空
- [ ] 4.7 `git diff --stat` 不含 `src/`、`metrics/`、`tests/` 下任何路径

## 5. Archive

- [ ] 5.1 按 OpenSpec archive 流程移入 `openspec/changes/archive/`，前缀用 apply 当天 UTC 日期
- [ ] 5.2 `openspec list` 不再含本变更；`openspec validate --specs --strict` 退出码 0
