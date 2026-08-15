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

**状态：待处理。** 倾向 (a)。关闭方式：wave 3 开始前单独提一个实现变更，
或并入 01-03。01-08 全量门禁时若仍未关闭，须在 VERIFICATION.md 明确记录。
