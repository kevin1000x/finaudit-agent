# Phase 1 Open Questions

本阶段发现的、**不许就地解决**的问题。格式用 `CLAUDE.md` 停止协议的四段式。

规则：发现即记，不在当前 task 里顺手修。每条要么被后续变更关闭，要么在 01-08 裁决时明确留到 Phase 2。

---

## OQ-01 — 现金循环周期需要「指标引用指标」，现行 schema 不支持

> 由 `01-06-PLAN.md` 指定为首条。该计划尚未执行，此处先行落位，
> 01-06 执行时核对本条内容与其 `<action>` 一致即可，无需重写。

```text
EXPECTED   20 个指标的候选清单中原本包含现金循环周期（CCC）。

FOUND      CCC = 存货周转天数 + 应收账款周转天数 − 应付账款周转天数，
           需要「一个指标引用另外三个指标的结果」。而现行 schema 的 source_fields
           与受限 DSL 都只支持**字段**引用，不支持**指标**引用。

IMPACT     该指标无法在不扩展 schema 的前提下定义。扩 schema 属权威文档变更，
           须走 OpenSpec，不属于 01-06 范围。
           同时它给 01-07 的 C2 类拒答题提供了一个**真实**靶子——
           C2 题要求引用「语义层里不存在的指标」，CCC 是真缺口而非编造。

OPTIONS    (a) Phase 2 提 OpenSpec 变更引入复合指标能力
           (b) 保持不定义，作为 C2 类拒答题的长期靶子
           (c) 用字段直接展开 —— **否决**：会重复三份定义的全部口径约定，
               任何一份改动都要手工同步，正是语义层要消灭的问题
```

**状态：已裁决（2026-08-15，操作者）。** 采纳 (b)，并保留 (a) 作为 Phase 2 候选。
CCC 移出 20 指标清单，换入应付账款周转天数（本就是 CCC 的一个分量）。
`01-06-PLAN.md` 已含断言 `resolve "现金循环周期"` 退出码 2 / `METRIC_NOT_DEFINED`。

**残余风险**：若 Phase 2 始终不做复合指标，20 个指标里永久缺一个常用指标。

---

## OQ-02 — 词表加载器把 3 个必需键静默补默认值，其中一个会造成静默错误

发现于 01-02 的反向核对（tasks.md §2），**在 apply 之前**。

```text
EXPECTED   metrics/_flags.yaml 的每个条目含 name / description / scope /
           affects_comparability / introduced_by 五个键。
           vocabulary.py 的 Flag dataclass 也确实把这五个都声明为必需字段
           （无默认值），说明这就是原本的意图。

FOUND      load_vocabulary() 与该意图不符 —— 五个键里只有两个真的被强制：

             name                    entry["name"]                          KeyError（未包装成 Finding）
             scope                   校验 in {definition, system}，raise    强制 ✅
             description             entry.get(..., "")                     **静默补空串**
             affects_comparability   bool(entry.get(..., False))            **静默补 False**
             introduced_by           entry.get(..., "")                     **静默补空串**

           见 src/semantic_layer/vocabulary.py:62-68。

IMPACT     description 与 introduced_by 补空串只损失可读性与溯源，后果有限。
           **affects_comparability 补 False 是静默错误**，且方向最坏：
           漏写这个键的 flag 会被当成「不影响可比性」，
           于是一个本该阻断跨期比较的标记**悄悄不阻断**，且不触发任何报错。
           这与 POC-01 的 C4（符号约定未声明 → 方向性错误且不触发 undefined）
           是同一失效模式，正是本项目声称要消灭的东西。

           当前 10 条 flag 全部显式写了五个键，所以**现在没有实际错误**。
           风险在将来：新增 flag 时漏写，不会有任何提示。

OPTIONS    (a) 让 load_vocabulary 对缺失的必需键 fail-closed（抛错或产出 Finding），
               并为三个键各加一条回归测试。改动小、方向明确。
           (b) 只对 affects_comparability fail-closed，另两个键保持宽松。
               理由是只有它会造成静默错误。但会留下「哪些键是真必需」的模糊地带。
           (c) 放宽 spec，不要求五键齐全 —— 否决：Flag dataclass 已把五个都声明为
               必需，放宽 spec 等于让规格去迁就实现里的一处疏漏。
```

**处理：spec 保留五键要求（这是正确契约），实现在 01-02 内不改动。**

依据 `01-02-PLAN.md` 的模式声明「ARCHITECT（规格变更），不写实现代码」
与 tasks.md §2.9「实现少做则记入 open-questions 另提变更，不在本变更里改实现」。

这使 `lock-condition-dsl-and-flag-vocabulary` 出现**一处规格领先实现**，
已在其 `proposal.md` §Non-goals 显式声明，不隐藏。

**状态：已关闭（2026-08-15，随 01-03 落地）。** 采纳 (a)。

`load_vocabulary()` 现在对五个必需键中任一缺失即 `raise ValueError`，
并额外拒绝 `affects_comparability` 为非布尔值——写成字符串 `"false"` 会被 `bool()` 判成 `True`，
比漏写更隐蔽。回归测试 `tests/test_vocabulary.py`：五个键各一条参数化用例、
布尔类型一条、坏 scope 一条，另加一条断言真词表 10 条全部写齐五键。

验证：`pytest -q` **93 passed**（此前 40）。

---

## OQ-03 — `resolve` 子命令未实现，且计划期望的退出码与代码不符

发现于 01-03 执行途中（顺手核验 `__main__.py` 时）。

```text
EXPECTED   01-06-PLAN.md 三处断言 `resolve "现金循环周期" --json` 退出码 2、
           `.code` 为 METRIC_NOT_DEFINED。CCC 作为 C2 类拒答靶子的整个论证
           都挂在这条命令上。

FOUND      两个问题，第二个更隐蔽：
           1. `src/semantic_layer/resolve.py` **不存在**。
              `_cmd_resolve` 里 `from .resolve import ...` 抛 ModuleNotFoundError。
              01-01 的 CLI 里把它标成「Task 2 实现」，但 01-01 只交付了 tracer。
           2. 即使实现了，`_cmd_resolve` 现在 `return 3`（未解析时），
              而 01-06 断言的是 **2**。规格与计划对不上。

IMPACT     wave 3 的 01-06 会在这条断言上直接失败，且失败原因是
           「命令不存在」而非「靶子不对」——排查会绕远路。
           退出码 2 与 3 的分歧更值得注意：`_cmd_validate` 已经用 2 表示
           「没找到定义文件」这类**调用错误**，用 2 表示「指标未定义」会与之撞车。
           拒答是**正常业务结果**，不是调用错误，用不同的码是对的。

OPTIONS    (a) 实现 resolve.py，退出码沿用代码里的 3，改 01-06 的三处断言为 3。
               理由：2 已被「调用错误」占用，拒答不该复用它。
           (b) 实现 resolve.py，退出码改成 2，与 01-06 一致。
               代价：与 _cmd_validate 的 2 语义冲突。
           (c) 不实现，把 CCC 的拒答靶子改用别的方式验证。
               否决：AC-02「口径定义缺失时拒绝作答且理由可机读」是 Phase 1
               的阻塞性验收标准，resolve 就是它的执行体，不能绕。
```

**状态：已关闭（2026-08-15，操作者裁决采纳 a）。**

`src/semantic_layer/resolve.py` 已实现，27 条用例。退出码定为 **3 拒答 / 2 调用错误 / 0 已解析**。
计划侧共 **9 处** 断言由 2 改为 3，分布在 01-01 / 01-06 / 01-07。

实现覆盖 01-01 Task 2 的全部规格：`Registry`（别名冲突加载期抛错）、
`resolve`（返回 `MetricDefinition | Refusal` 二选一，不返回 None 不抛异常——
D-003「拒答是正确行为」在类型层的表达）、`evaluate_refusal`、`check_comparable`、
`active_flags`、7 个 `RefusalCode`、`--row PATH#KEY`。

**实测**：`resolve "现金循环周期" --json` → exit 3，`code` = `METRIC_NOT_DEFINED`。
`pytest -q` 120 passed。

---

## OQ-04 — `standard_basis.version` 引用的是列表，语法上合法但语义上无解

发现于 OQ-03 的实现过程（写 `active_flags` 时求值失败）。

```text
EXPECTED   metrics/net_profit_attributable_excl_nonrecurring.yaml 的
           basis_version_mismatch 标记，触发条件写作
             standard_basis.version != comparison_period.standard_basis.version
           它通过了校验器，也通过了 01-02 反向核对的 17 条断言。

FOUND      两层问题，第二层更值得注意：

           1. `comparison_period.*` 是**两期比较**才有的语境，单期数据无从求值。
              这一层已在 OQ-03 内解决：`comparison_scoped_flags()` 把这类标记识别出来，
              单期 `active_flags` 推迟而非拒答，并通过 `deferred_comparison_flags`
              在输出里显式列出——推迟不等于丢弃。

           2. **`standard_basis` 是一个列表，不是一个对象。** 该定义有 3 条准则依据，
              版本分别是 2023 / 2010 / 2014。`standard_basis.version` 作为标量引用
              **指向哪一条是没有答案的**。这个触发条件即使给了比较期也求不出正确结果。

IMPACT     直接影响有限：check_comparable() 独立实现了跨准则版本检查
           （逐条按 name 配对比 version，返回 CROSS_BASIS_VERSION_COMPARISON），
           所以该能力本身没缺失，缺的是那条 flag trigger 写不对。

           **真正的问题在校验器**：R4 要求「触发条件 MUST 只引用已声明的字段」，
           而元数据命名空间（standard_basis / comparison_period / metric）
           被豁免于 source_fields 声明检查——于是任何 `standard_basis.<任意词>`
           都能通过校验。校验器接受了一个**永远解析不出值**的引用。

           这与本项目要消灭的失效模式同型：看起来有规则，实际不产生任何机械后果。
           wave 3 的 19 份定义若照抄这个写法，会复制 19 遍。

OPTIONS    (a) 给元数据命名空间定义**封闭的合法路径集**（如 metric.id / metric.version /
               standard_basis[].version 的显式下标或聚合谓词），校验器据此拒绝越界引用。
               需扩 DSL 与 spec R4，属权威文档变更，走 OpenSpec。
           (b) 从词表移除 basis_version_mismatch 的 definition 域身份，改为 system 域
               ——它本来就该由运行时在比较两期时产出，和 metric_version_mismatch 同类。
               改动最小，且与该 flag 的实际语义相符。
           (c) 保持现状，靠 check_comparable() 兜底。
               否决：留一个永远不触发的 flag 在定义里，正是「散文冒充规则」的变体。
```

**状态：待裁决。** 倾向 **(b) 先做、(a) 留给 Phase 2**——
`basis_version_mismatch` 与 `metric_version_mismatch` 语义同类而 scope 不同，
本身就是词表里的不一致；改 scope 是小改动且立刻消除 wave 3 的复制风险。
(a) 是更彻底的修法但要动 DSL 与规格，不该卡住 wave 3。

**wave 3 开写前需要一个决定**，因为 19 份定义会照抄现有那份的写法。
