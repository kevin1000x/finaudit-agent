# 语义层的数据接入契约（读源码得出，非推测）

**日期**：2026-08-16　｜　**依据**：通读 `src/semantic_layer/` 的
`definition.py`(215) / `resolve.py`(324) / `dsl.py`(462) 全文

**为什么要有这份文件**：Phase 1.5 的抽取器要把字段喂进语义层，
而在此之前，本项目对这个接口的全部认识都是**从 `eval/run.py` 的调用反推的**。
反推出来的契约会在第一次真实对接时崩。本文件是读实现得出的事实。

⚠️ **本文件不是规格。** 规格权威是 `PROJECT_SPEC.md` §5.1 与
`openspec/specs/semantic-layer/metric-definition/spec.md`。
本文件描述**当前实现实际接受什么**，两者不一致时以规格为准，并把不一致记为缺陷。

---

## 1. 抽取器要产出的东西：一个扁平 dict

```python
row = {
    "bs.total_assets": 272699660092.25,
    "bs.short_term_borrowings": 0,          # 行在、格子空 ⇒ 0
    # "bs.bonds_payable" 整个键不出现        # 整行不存在 ⇒ 缺失
    "notes.restatement_flag": False,
}
```

**键是字段 id，值是原始值。没有嵌套、没有单位包装、没有元数据。**
（单位与币种目前无处安放——见 §5 的缺口 1。）

## 2. 「缺失」与「零」是怎么区分开的（A-2 的机械落点）

`dsl.normalize_row(row, source_fields)` 是唯一的归一化入口，逻辑只有三条
（`dsl.py:388-406`）：

| 输入情形 | 结果 |
|---|---|
| **字段 id 不在 row 里** | `MISSING` |
| 值等于该字段声明的 `missing_representation`，**且类型相同** | `MISSING` |
| 该字段未声明 `missing_representation`，且值是 `None` | `MISSING` |
| 其余（含 `0`、`0.0`、`False`、`""`） | **原样保留** |

20 份定义全部声明 `missing_representation: null`。
`0 == None` 为假，且 `type(0) is type(None)` 为假 —— **所以 `0` 不会被吞成缺失**。

> **因此 A-2 的修法在抽取层是确定的，不需要再讨论**：
> 「行印在报表上但值的格子是空的」⇒ 输出 `0`；
> 「整行在报表上不存在」⇒ **不输出这个键**（或输出 `None`）。
> 茅台 2023 的短期借款 / 长期借款 / 应付债券属于前者，
> 抽取器输出 `0` 之后，`interest_bearing_debt_ratio` 就能算出接近零的正确值，
> 而不是按 `is_missing` 拒答。**定义侧一个字都不用改。**

`MISSING` 是单例哨兵，且 `__bool__` 会抛 `MissingOperandError`
（`dsl.py:53-54`）——**防止它在任何布尔上下文里被静默当成假值**。

## 3. 可调用的接口

```python
from semantic_layer.resolve import Registry, Refusal, evaluate_refusal, active_flags, check_comparable

registry = Registry.load(metrics_dir="metrics")     # 别名冲突在加载期抛 ValueError
outcome  = registry.resolve("毛利率")                # -> MetricDefinition | Refusal
```

| 函数 | 签名 | 语义 |
|---|---|---|
| `Registry.load(metrics_dir, vocabulary_path=None)` | → `Registry` | `metric_id` 重复或别名冲突**在加载期抛 `ValueError`**，不留到查询期 |
| `Registry.resolve(name)` | → `MetricDefinition \| Refusal` | 先查 `metric_id`，再查别名（`display_name` 与 `aliases` 都算别名）；命中后**先跑 `validate_definition`，不合规则拒绝消费** |
| `evaluate_refusal(defn, row)` | → `Refusal \| None` | 按 YAML 书写顺序逐条求值 `undefined_conditions`，**第一条为真即拒答**；`condition_index` 直接对应 YAML 里的第几条 |
| `active_flags(defn, row)` | → `set \| Refusal` | 求值不了**整体拒答**，不跳过 |
| `comparison_scoped_flags(defn)` | → `set` | 触发条件引用 `comparison_period.*` 的标记，单期语境不适用，**不静默丢弃** |
| `check_comparable(a, b)` | → `Refusal \| None` | 同一 `metric_id` 的两期；`metric_id` 不同直接抛 `ValueError`（那是调用方用错 API，不是"不可比"） |

### 闸门已经在调用签名里了

前几轮讨论 Phase 2 架构时的结论是「口径闸门应放进**调用签名**
（`resolve_scope() -> ScopeSpec | Refusal`），使绕过成为类型错误而非运行时策略」。

**`Registry.resolve()` 已经是这个形状**：返回 `MetricDefinition | Refusal`，
不返回 `None`、不抛异常（`resolve.py:1-12` 的模块 docstring 明写了这条立场）。
→ Phase 2 是**沿用这个模式往上层扩展**，不是发明它。这一点要写进 `ARCHITECTURE.md`，
否则下一个人会以为返回联合类型是疏漏然后"修好"它。

## 4. 拒答码的取值域（封闭枚举，7 项）

`RefusalCode`（`resolve.py:38-47`）：

| 码 | 含义 |
|---|---|
| `METRIC_NOT_DEFINED` | 指标名没有对应口径定义 |
| `ALIAS_AMBIGUOUS` | 别名指向多个指标 |
| `DEFINITION_NONCONFORMANT` | 定义自身不合规，不允许被消费 |
| `UNDEFINED_CONDITION_HIT` | 命中已声明的未定义条件 |
| `UNEVALUABLE_CONDITION` | 条件无法对给定数据求值 |
| `CROSS_VERSION_COMPARISON` | 两期口径版本不同 |
| `CROSS_BASIS_VERSION_COMPARISON` | 两期准则版本不同 |

`Refusal.to_dict()` 是 AC-02「拒答理由可机读」的交付形式，键固定：
`refused / code / code_meaning / detail / metric_id / condition_index`。

> 对照 deepseek-harness 的 `ApprovalOutcome`（封闭四元组、`unavailable` 也是一等值），
> 本项目的 `RefusalCode` 已经是同构的封闭枚举。**Phase 2 的证据链事件应当照此设计**，
> 不要退回自由文本 reason。

## 5. 三个必须在 Phase 1.5 处理的缺口

1. **单位与币种无处安放。** `row` 是扁平 `{field_id: 值}`，没有承载单位的位置。
   而 2026-08-16 实测确认 `单位:元 币种:人民币` 就印在报表表头（`references/cninfo.md`）。
   → 抽取器抽得到，但**当前接口接不住**。需要决定：值改成带单位的包装类型，
   还是另开一条旁路元数据。**这是接口变更，走 OpenSpec。**
2. **语义层不做任何算术。** `formula` 在 `resolve.py` 里从头到尾**没有被解析过一次**，
   它只是 `MetricDefinition.formula` 上的一个字符串。
   DSL 的词法器明确拒绝算术符号（`dsl.py:236`）。
   → 数值执行层是 Phase 1.5 要**新建**的东西，不是"打开某个开关"。
3. **`Registry.resolve()` 每次调用都重跑 `validate_definition`**（`resolve.py:128`）。
   语义上是对的（不合规不许被消费），但对批量取数是 O(n) 次全量校验。
   → 若 Phase 1.5 要跑全市场批量，这里需要缓存。**现在不改**，记下来。

## 6. 我没读因此不能置评

`validate.py`(389)、`scan.py`(245)、`stats.py`(119)、`report.py`(74)、
`__main__.py`(231)、`vocabulary.py`(92) —— 本轮未通读。
因此**不能断言** 9 条 Requirement 的具体实现细节、CLI 的全部子命令与退出码语义
（退出码 3 拒答 / 2 调用错误 / 0 已解析这条来自 OQ-03 的裁决记录，不是我读出来的）。
