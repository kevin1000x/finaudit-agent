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
