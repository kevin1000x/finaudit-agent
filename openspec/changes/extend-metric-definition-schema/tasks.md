> `design.md` 的两条 Open Question 均已确认不影响本任务拆分（受限 DSL 的具体语法形式、全局 flag 词表的物理位置），无需在 apply 前解决。
>
> 关于「涉及行为的 task 必须先写失败测试」：本变更**不产出代码**，无法写单元测试。等价的红测在第 3 组——用新契约去检验 POC-01 的 3 份 `version: 1` 定义，它们**必须不合规**。若它们竟然合规，说明新契约没有真正加强约束，本变更即失败。这是可执行、可证伪、且先于契约定稿完成的检验。

## 1. 前置校验

- [x] 1.1 运行 `cd docs/agent/poc-01 && sha256sum -c SHA256SUMS`，记录输出。5/5 OK 才继续；任一 FAIL 立即停止并按 EXPECTED/FOUND/IMPACT/OPTIONS 报告
      → **5/5 OK，exit 0**
- [x] 1.2 确认 `git status` 干净，本变更从一个已知基线开始
      → **干净，基线 `b512d68`**

## 2. 红测：确认现有 v1 定义在新契约下不合规

- [x] 2.1 从 `specs/semantic-layer/metric-definition/spec.md` 的 9 条 Requirement 提取一份逐条可勾选的合规检查表，写入 `openspec/changes/extend-metric-definition-schema/conformance-checklist.md`
      → R1–R9 检查表已建
- [x] 2.2 用该检查表逐条检验 `docs/agent/poc-01/definitions/` 下的 3 份 `version: 1` 定义，逐项记录 PASS/FAIL 与失败理由，结果写入同一文件
      → 27 格矩阵 + 逐条原文证据，被检定义**未改动**
- [x] 2.3 **判定红测**：3 份定义必须至少在「数据粒度」「符号约定」「标记受控词表」「陷阱可执行或标注」四条上不合规。若全部合规 → 新契约未加强约束，**停止 apply**，回到 spec 重新设计
      → **红测通过**：R1/R2/R4/R8 各 3/3 `FAIL`。总计 `FAIL` 27 / `PARTIAL` 6 / **`PASS` 0**。
        附带发现：`PASS` 为 0 说明这是换契约而非加字段，佐证 D5（v1 不迁移）在技术上也成立

## 3. 契约落地

- [x] 3.1 改写 `PROJECT_SPEC.md` §5.1：在现有字段之上加入 `grain` / `sign_convention` / `derivation` / `flags` / `undefined_conditions`，并把 `standard_basis` 改为含 `version` 的结构化条目
      → 完整 YAML 示例已落地，含 `missing_representation`（R6）
- [x] 3.2 在 §5.1 写入元规则：每条 `common_pitfalls` 必须要么对应一条可求值规则，要么显式标注 `advisory_only`
      → 以 `enforced_by` / `advisory_only` 二选一落地，并写入 >50% 即失效的监控阈值
- [x] 3.3 在 §5.1 写入版本号语义（D4）：哪些字段改动必须 bump、哪些不必
      → 必 bump 7 项 / 不 bump 3 项，理由写明「唯一用途是判定可比性」
- [x] 3.4 在 §5.1 声明全局 flag 词表的位置约定与「指标只能引用不能自造」规则（D2），**不填词表内容**
      → 已声明，位置待 Phase 1 有 5 个以上真实 flag 后确定

## 4. 同步受影响的验收标准与文档

- [x] 4.1 更新 `PROJECT_SPEC.md` AC-01：字段要求由「字段映射、公式、准则依据、≥3 条常见陷阱」同步为新字段集
- [x] 4.2 在 `PROJECT_SPEC.md` §5.1 标注：POC-01 的 3 份定义停留在 `version: 1`，新定义从 `version: 2` 起，跨版本不可比（D5）
      → 并引用红测的 `PASS`=0 作为「跨版本比较技术上也无意义」的证据
- [x] 4.3 在 `EVAL_CASES.md` §3.2 补一句：C2 类拒答题的判定依赖 `undefined_conditions` 的可求值性，指向本 capability spec
      → 并明确：条件不可求值算**定义不合规**，不算模型失败

## 5. 收尾验证

- [x] 5.1 再次运行 `sha256sum -c SHA256SUMS`，确认 apply 全程未触碰 POC-01 冻结输入（5/5 OK）
      → **5/5 OK，exit 0**
- [x] 5.2 运行 `openspec validate --strict`，通过
      → `openspec validate --changes --strict` → `1 passed, 0 failed`，exit 0
- [x] 5.3 在 `docs/agent/PROGRESS.md` 追加 changelog 条目，记录真实输出（含红测结果），不记计划
- [x] 5.4 提交；随后 `openspec archive` 并确认 `openspec/specs/semantic-layer/metric-definition/spec.md` 已生成
