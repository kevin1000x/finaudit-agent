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

## 第六道门：门禁的门禁（2026-08-24 新增，落地待办 L-4 / L-5）

```bash
.venv/Scripts/python scripts/check_gates.py
```

查的是**我们自己的门禁与测试会不会红**。三条规则：

- **R1** 每个 `test_*` 必须有可失败点（`assert` / `pytest.raises` / `pytest.fail` / …）
- **R2** 每道门禁必须在 `GATES` 注册表里**具名声明**它的负控制用例，且该函数存在、满足 R1
- **R3** 恒真断言（`assert True` / `assert x == x`）不算断言
- **R4** 已登记门禁必须真的出现在 `.github/workflows/gates.yml` 里
  —— 2026-08-23 第五道门漏进 CI 整整一天，这条把那个回归钉死
- **R5** 登记册里已落地的 `L-nn`，编号必须在 `references/` 里出现过
  —— 落地了没回标，`未落地` 标注会继续骗下一个读它的人

**R1 的唯一例外**：断言确实就是「不抛异常」时，在测试 docstring 首行写
`NO-ASSERT-BY-DESIGN: <该测试特有的理由>`。**反模板机制是理由必须全仓唯一**——
复制粘贴必然重复，重复即红。当前声明 **1 条**，有测试锁住这个数字。

首跑抓出一条真的（`test_scan.py` 的二进制文件用例，确实没有断言），
**按例外显式声明理由，没有给它编一个假断言**——编一个就是 F-2 本身。

**它明确抓不到**：负控制会不会抓住一个真实回归。那没有已知的机械判据，
只有下面这条人执行的程序。不许把「第六道门通过」读成「我们的门禁都有效」。

## 假闸门的验证程序：造回归 → 看红 → 回退（L-5）

> **`A guard only guards if the regression actually fails it`**
> ——`references/deepseek-harness-docs-part2.md` 逐字引自 harness `testing.md:34`，
> 并在 `postmortem/0001:104` 有真实执行记录（178 个单测全绿 + 100% 行覆盖，产品完全不可用）。

**新增或修改任何门禁时必须跑一遍，跑的记录写进提交信息。** 三步：

1. **造回归** —— 把这道门声称能挡住的缺陷**真的造出来**
2. **看红** —— 跑门禁，确认它非零退出，**并确认红的原因正是那个缺陷**
3. **回退** —— 还原，复跑，确认变绿

**第 2 步的后半句不是废话。** 2026-08-24 第一次对 `check_gates.py` 跑这个程序时，
造回归的脚本把受害文件切成了**语法错误**，门禁于是崩在 traceback 上——
它确实红了，但红的原因是解析失败，不是它声称在查的那件事。
**这正是本项目从三个外部项目收集到的那条失效模式，这次出现在自己身上。**
两个后果都已处理：改法改为「只替换前缀、其余一字不动」并在脚本里
先 `ast.parse` 自证语法仍合法；`check_gates.py` 增加 `_parse()`，
**语法错的测试模块报为一条 FAIL 而不是让门禁崩**。

写法上把回退做成 `trap ... EXIT`，别指望自己记得还原：

```bash
cp tests/target.py /tmp/backup.py
trap 'cp /tmp/backup.py tests/target.py; rm -f /tmp/backup.py' EXIT
# ...造回归、看红...
```

## CI（2026-08-22 新增，D-021 第二条豁免）

`.github/workflows/gates.yml` 在 push / PR 时跑**同一组门禁**，不新增检查项。
本地与 CI 是同一份命令的两个执行位置——**本地绿不等于 CI 绿**：
Linux 与 Windows 在换行符、路径大小写、locale 上都可能分叉，
而冻结产物的 SHA-256 跨平台稳定（D-012 的物理保障）**只有在 Linux runner 上才验得出来**。

改 `gates.yml` 等同于改门禁定义，**必须同步本文件**，反之亦然。
CI 只允许跑验证：不得构建产物、发布、部署，工作流已声明 `permissions: contents: read`。
