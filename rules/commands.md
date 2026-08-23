# 常用命令


```bash
# 阶段状态
cat .planning/STATE.md

# 校验已冻结实验输入未被改动（声明任何评测/POC 结论前必跑）
cd docs/agent/poc-01 && sha256sum -c SHA256SUMS

# OpenSpec：提一个变更 / 查看 / 应用 / 归档
openspec list
openspec show <change-id>
openspec validate

# 评测（Phase 1 起可用）
python -m eval.run --suite frozen-01 --report reports/
```

（评测命令在 Phase 1 实现前不存在，不要假装跑过。）

---

## 第五道门：阅读台账（2026-08-23 新增，台账 N-31）

```bash
.venv/Scripts/python scripts/check_reading_ledger.py
```

`references/` 的覆盖表声称读过的**大目标**（自报行数 ≥ 100），正文里必须单独出现。
拦的是已经连续发生**四次**的失效模式：台账标「全文」，正文零对应内容。
首次实跑就抓出一条（`tests/test_trace_integration.py`），已如实降级为 `UNVERIFIED`——
**不是加进豁免清单**。当前豁免为 0 条，且有一条测试锁住这一点。

**它明确抓不到**：目录级聚合行、悬空的前向引用、以及「正文提到了但其实没读」。
详见脚本 docstring 的「明确抓不到什么」一节，不许把「门禁通过」读成「台账全对」。

## CI（2026-08-22 新增，D-021 第二条豁免）

`.github/workflows/gates.yml` 在 push / PR 时跑**同一组门禁**，不新增检查项。
本地与 CI 是同一份命令的两个执行位置——**本地绿不等于 CI 绿**：
Linux 与 Windows 在换行符、路径大小写、locale 上都可能分叉，
而冻结产物的 SHA-256 跨平台稳定（D-012 的物理保障）**只有在 Linux runner 上才验得出来**。

改 `gates.yml` 等同于改门禁定义，**必须同步本文件**，反之亦然。
CI 只允许跑验证：不得构建产物、发布、部署，工作流已声明 `permissions: contents: read`。
