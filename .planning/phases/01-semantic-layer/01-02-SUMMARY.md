# 01-02 SUMMARY —— 锁定条件表达式语法与 flag 词表位置

**模式：ARCHITECT。** 全程未改 `src/` / `metrics/` / `tests/`（`git diff --numstat` 0 行）。

**结果：完成。** OpenSpec 变更 `lock-condition-dsl-and-flag-vocabulary` 已
propose → decision → apply → archive 走完一圈，归档为
`openspec/changes/archive/2026-08-15-lock-condition-dsl-and-flag-vocabulary`。

## 交付物

| | |
|---|---|
| 变更提案 | `proposal.md` / `design.md` / `tasks.md` / spec delta，已 archive |
| capability spec | R4 与 R7 被改写；合并后仍是 **9 条 Requirement**，`+0 ~2 -0 →0` |
| `PROJECT_SPEC.md` §5.1 | 词表位置待定项填实；新增「条件表达式的规范语法」小节 |
| `docs/agent/phase-01/open-questions.md` | 新建，含 OQ-01（CCC）与 OQ-02（词表加载器） |

## 操作者在 checkpoint:decision 的裁决

**选定 `approve`。** 另裁决 OQ-02 **并入 01-03**，wave 3 前关掉。

### flag 词表覆盖度判断（计划要求抄进 SUMMARY，供 01-08 对照）

**判断：10 条够用。** 理由——这 10 条覆盖的是**跨指标的可比性轴**
（重述 / 准则版本 / 合并范围 / 母公司口径 / 未审计 / 单位 / 币种 / 期间长度 / 口径版本 / 来源分歧）；
而单个指标的口径歧义（期间费用率含不含研发、有息负债含不含租赁负债、周转天数 365 还是 360）
应当在定义里**定死**，走 `derivation` 与 `undefined_conditions`，不该变成 flag。
最像缺口的是「期末值 vs 平均值」，但 01-04 / 01-06 的计划已用 `derivation` 处理。

**01-08 须拿这条判断与 wave 3 实际发生的 flag 请求对照。**
若 19 份定义在执行中提出 ≥ 3 次新增 flag 的请求，说明本判断错了，须在 VERIFICATION.md 记录。
词表膨胀本身是坏信号，但词表在独立文件里，真撞上缺口时加一条是小变更，不是 20 文件返工。

## 反向核对的发现（本计划最有价值的产出）

`tasks.md` §2 的反向核对在 **apply 之前**跑，17 条 DSL 断言 **17/17 与规格一致**。
词表侧查出一处**规格领先实现**，即 OQ-02：

`Flag` dataclass 把五个键都声明为必需，但 `load_vocabulary()` 只真强制两个
（`name` 抛 KeyError、`scope` 校验 raise）；`description` / `affects_comparability` /
`introduced_by` **静默补默认值**。`affects_comparability` 补 `False` 方向最坏——
漏写该键的 flag 会被当成「不影响可比性」，**本该阻断跨期比较的标记悄悄不阻断且不报错**，
与 POC-01 的 C4 同型。当前 10 条 flag 都写齐五键，故现无实际错误。

**处理**：spec 保留五键要求（那是正确契约），实现不在本变更内改——已在 `proposal.md`
「一处规格领先实现」小节显式声明，不隐藏。

## 顺带修正

- **AC-04 与本会话早些时候的 D-012 修订不一致**（未提前置门禁与作废率上限），已一并补上。
  这是那次修订的收尾遗漏，不是本变更引入的。
- 计划的验收命令 `openspec validate --strict` 在 archive 之后无活动变更，
  报 "Nothing to validate" 并返回非零。**是命令写错，不是校验失败**——
  等价命令 `--all --strict` 与 `--specs --strict` 均 exit 0。后续计划照抄该命令时需注意。

## 验证（2026-08-15 实跑）

```text
openspec validate --all --strict          1 passed, 0 failed, exit 0
openspec validate --specs --strict        exit 0
grep -c '^### Requirement:' <spec>        9
grep -c 'metrics/_flags.yaml' PROJECT_SPEC.md   1
grep -c '候选：本文件内' PROJECT_SPEC.md          0
pytest -q                                 40 passed
python -m semantic_layer validate         exit 0
sha256sum -c SHA256SUMS                   5/5 OK, exit 0
git status --porcelain docs/agent/poc-01/ 空
git diff --numstat HEAD -- src/ metrics/ tests/   0 行
```

**判定：PASS。** 全部 5 条 success criteria 有真实命令与输出支撑。

## 下一步

01-03（wave 2 的另一半）：AC-10 非公开数据扫描器 + `advisory_only` 占比统计，
**外加 OQ-02 的词表加载器 fail-closed**（操作者裁决并入）。
