# 模式锁、停止协议、完成的定义

## 模式锁

每次会话开始时，先声明当前处于哪个模式，并只做该模式允许的事：

| 模式 | 允许 | 禁止 |
|---|---|---|
| `DISCOVER` | 提问、澄清、写 `docs/agent/IDEA.md` | 写代码、定架构 |
| `RESEARCH` | 只读探索、写 `docs/agent/RESEARCH.md` | 改任何生产文件、推荐方案 |
| `ARCHITECT` | 比较方案、写 `docs/agent/ARCHITECTURE.md` | 写实现代码 |
| `POC` | 写一次性实验代码 | 写生产架构、加抽象 |
| `PLAN` | 写 `.planning/phases/**/PLAN.md` | 实现 |
| `IMPLEMENT` | 只做当前一个 task | 顺手重构、改计划 |
| `VERIFY` | 跑真实命令、记录真实输出 | 修实现 |
| `REVIEW` | 读 diff 与证据、给发现 | 直接改代码 |

模式没声明时，默认拒绝写生产代码，先问清楚。

## 停止协议

计划与现实不符时**立刻停止**，不要即兴发挥。按这个格式报告：

```text
EXPECTED   计划里说的是什么
FOUND      实际看到的是什么
IMPACT     这个差异影响什么
OPTIONS    可选的处理方式（至少两个）
```

同一个 bug 连续 3 次修复失败 → 停止打补丁，回头怀疑架构或心智模型（Superpowers `systematic-debugging`）。

## 完成的定义

不接受"应该可以了"。声明完成必须给出：

```text
验收标准 → 验证方法 → 实际命令 → 真实输出 → 证据位置 → PASS / FAIL / UNVERIFIED
```

没有真实执行证据的一律记 `UNVERIFIED`，不记 PASS。声明完成前调用 `verification-before-completion` skill。
