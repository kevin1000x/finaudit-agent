## Why

**这是上一个变更（`lock-condition-dsl-and-flag-vocabulary`，2026-08-15 apply）的缺陷修正，发现于 wave 3 开写第一批定义时。**

那次把 R4 的根命名空间白名单与 R8 的 `enforced_by` 类别集**照抄自实现**（`dsl.py` 与 `validate.py`），
反向核对也只比对了「规格 ↔ 实现」。**没有比对「规格 ↔ 下游消费者」**——
也就是 wave 3 那三份计划里写明要用的东西。结果锁进规格的两个集合都少了一项：

| 缺口 | 规格现状 | 下游实际需要 | 证据 |
|---|---|---|---|
| 根命名空间少 `kpi` | `is` / `bs` / `cfs` / `notes` | 还需 `kpi` | `scan_rules.yaml` 的 `allowed_field_prefixes` 有 5 项含 `kpi`；`01-04-PLAN.md` Task 2 明写用 `kpi.roe_weighted_average_disclosed` |
| `enforced_by` 类别少 `derivation` | `flags` / `source_fields` / `undefined_conditions` | 还需 `derivation` | 三份 wave 3 计划共 **4 处** 写 `enforced_by: derivation` |

两处都不是「想扩能力」，是**规格漏抄**：`kpi` 早在 01-03 就进了版本化的扫描规则，
`derivation` 早在 01-02 之前就写在 wave 3 的计划里。当前状态是同一个仓库里
两份版本化产物互相矛盾（`scan_rules.yaml` 放行 `kpi`，规格禁止它）。

**实测触发**：写 `metrics/roe_weighted_average.yaml` 时校验器报

```text
[R7.EXPR_UNPARSEABLE]   根命名空间 'kpi' 不在白名单 [...] 内
[R8.ENFORCED_BY_UNRESOLVED]  enforced_by='derivation.allow_from_components' 的类别 'derivation' 不被支持
```

不修则 wave 3 的 19 份定义中至少 5 份写不出来。

## What Changes

只动 R4 与 R7 共用的语法条款、以及 R8 的 `enforced_by` 类别集。不新增、不删除 Requirement。

**MODIFIED R4** —— 字段引用的数据侧根命名空间由四项扩为五项，增加 `kpi`：
指年报「主要会计数据和财务指标」章节中**公司已直接披露**的指标值。
它与三张报表、附注并列，是第五类公开披露来源，而不是从报表推算出来的东西。
这一项使「取披露值、禁止倒推」这条立场可被表达——`roe_weighted_average` 正是其实例。

**MODIFIED R8** —— `enforced_by` 的合法类别增加 `derivation`，
标识为 `allow_from_components` 或 `note`。
理由：`derivation.allow_from_components` 是**布尔字段、可机械读取**，
「本定义禁止倒推」是一条实打实的可判定约束，不是散文。
把它挡在 `enforced_by` 之外，会迫使「禁止倒推」类的陷阱只能标 `advisory_only`——
**恰好把最该有机械后果的一条降级成仅供参考**，与元规则的用意相反。

## Capabilities

### Modified Capabilities

- `semantic-layer/metric-definition`：补齐两个被漏抄的枚举项。契约的**判定强度不变**——
  不放宽任何一条既有约束，只是让规格与仓库里另外两份版本化产物（`scan_rules.yaml`、wave 3 计划）
  重新一致。

## Non-goals

- ❌ **不放宽元数据命名空间。** `standard_basis.<任意词>` 仍能通过校验，这是 **OQ-04** 的未竟部分，
  已明确记为 Phase 2 必办，不在本变更范围。
- ❌ **不新增其他前缀或类别。** 只补有下游实证需求的两项。`kpi` 有 `scan_rules.yaml` 与
  01-04 计划为证，`derivation` 有 4 处计划引用为证。没有证据的一律不加。
- ❌ **不改判定强度。** 本变更不使任何此前不合规的定义变为合规——除了那些**本来就该合规、
  只因规格漏抄而被误判**的。
- ❌ **不动实现之外的既有定义。** tracer 与 POC-01 冻结样本零改动。

## 与 DECISIONS.md 的关系

| 决策 | 关系 |
|---|---|
| **D-009**（不产生重复权威文档） | **修复**。当前 `scan_rules.yaml` 与规格对「合法前缀」给出两个不同答案，本变更消除该矛盾。 |
| **D-012**（冻结） | **遵守**。不触碰 `docs/agent/poc-01/`。 |
| **D-003**（证据链） | **支撑**。`kpi` 让「此数来自公司披露而非我们推算」在证据链里可区分。 |

## 过程教训（写进变更，因为它比变更本身更值得记）

01-02 的反向核对做的是「规格 ↔ 实现」，17 条断言全过，然后就 apply 了。
**漏掉的一维是「规格 ↔ 下游消费者」。** 规格是给 19 份尚未写出的定义用的，
只跟已有实现对齐，等于只验证了「规格描述了现在有什么」，
没验证「规格够不够写出接下来要写的东西」。

后续任何锁定枚举集的变更，反向核对必须同时比对**下游计划里已写明要用的取值**。
