> 本变更是上一个变更的缺陷修正。红测形式：**先让缺口以失败形式暴露**，
> 再修实现与规格，最后确认同一条命令由 FAIL 转 OK。
> 触发它的实物是 `metrics/roe_weighted_average.yaml`，写它时校验器报了两项。

## 1. 前置校验

- [x] 1.1 `cd docs/agent/poc-01 && sha256sum -c SHA256SUMS`
      → **5/5 OK**
- [x] 1.2 记录基线：`c05ec97`，`pytest -q` 124 passed

## 2. 红测：缺口以失败形式存在

- [x] 2.1 写 `metrics/roe_weighted_average.yaml`（用 `kpi.` 前缀与 `enforced_by: derivation.*`）
- [x] 2.2 `validate` 该文件，记录真实报错
      → `[R7.EXPR_UNPARSEABLE] 根命名空间 'kpi' 不在白名单 [...] 内`
        `[R8.ENFORCED_BY_UNRESOLVED] enforced_by='derivation.allow_from_components' 的类别 'derivation' 不被支持`
- [x] 2.3 确认缺口有下游实证需求，不是臆想
      → `scan_rules.yaml` 的 `allowed_field_prefixes` 含 `kpi`（01-03 落地，版本化）；
        wave 3 三份计划共 **4 处** 写 `enforced_by: derivation`；
        `01-04-PLAN.md` Task 2 明写 `kpi.roe_weighted_average_disclosed`

## 3. 实现

- [x] 3.1 `dsl.py` 的 `ROOT_NAMESPACES` 增加 `kpi`
- [x] 3.2 `validate.py` 的 `_resolve_enforced_by` 增加 `derivation` 类别，
      标识限于 `allow_from_components` / `note`
- [x] 3.3 回归测试：`kpi.` 可解析、非法 `derivation.<其他>` 仍被拒、
      `derivation.allow_from_components` 可承载陷阱

## 4. 契约落地

- [x] 4.1 spec delta 合并进 `openspec/specs/`，确认仍是 9 条 Requirement
- [x] 4.2 `PROJECT_SPEC.md` §5.1 的「条件表达式的规范语法」表补 `kpi`；
      元规则段补 `derivation` 为合法 `enforced_by` 类别
- [x] 4.3 核对 `scan_rules.yaml` 的 `allowed_field_prefixes` 与规格现已一致（本变更的目的之一）

## 5. 后置校验

- [x] 5.1 `validate metrics/roe_weighted_average.yaml` 由 FAIL 转 **exit 0**
- [x] 5.2 `pytest -q` 全绿且**多于**基线 124
- [x] 5.3 `openspec validate --all --strict` exit 0
- [x] 5.4 `scan` exit 0；`sha256sum -c SHA256SUMS` 5/5 OK；`git status docs/agent/poc-01/` 空
- [x] 5.5 tracer 定义未被本变更改动

## 6. Archive

- [x] 6.1 `openspec archive` 并确认 `openspec list` 不再含本变更

## 真实输出（2026-08-15 实跑）

```text
validate roe_weighted_average.yaml   FAIL 2 项  →  OK, exit 0
pytest -q                            124 → 133 passed（+9 条回归）
openspec validate --all --strict     1 passed, 0 failed
grep -c '^### Requirement:'          9（合并后仍是 9 条，+0 ~2 -0 →0）
semantic_layer validate（全目录）      exit 0
semantic_layer scan                  exit 0
sha256sum -c SHA256SUMS              5/5 OK
git status tracer 与 _flags.yaml      空（本变更未改动既有定义与词表）
```

新增的 9 条回归里有一条是**跨产物一致性断言**：
`test_scan_prefixes_and_dsl_namespaces_agree` —— `scan_rules.yaml` 的
`allowed_field_prefixes` 必须等于 `dsl.ROOT_NAMESPACES`。
这正是本次缺陷的形状（两份版本化产物给出不同答案），把它钉死，
下次再有人只改一边就会红。
