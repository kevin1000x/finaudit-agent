# 部署：挂进 cninfo 那个 Space，而不是自己占一个

> ⚠️ **本文件不再是 Space 根目录的 `README.md`。** `D-040` 修订二（2026-09-08）
> 之后本服务不再单独占一个 Space —— 它作为 `/audit/*` 挂进
> `RGT07/cninfo-financial-analyzer`。那个 Space 的 `README.md` 是 cninfo 自己的，
> 不要覆盖。本文件现在只是一份部署说明。

## 为什么不自己建一个

建不了。2026-09-07 实测（`RGT07`，`isPro=False`）：

| 新建 Space | 结果 |
|---|---|
| private / public + **static** | 可以 |
| private / public + **docker** | **402 Payment Required（要 PRO）** |
| 组织账号下的 docker | 同样不行 |
| 复制现有 Space | 同样不行 |

卡住的是 **docker**，与可见性无关。而 `RGT07/cninfo-financial-analyzer`
建于 2026-05-03，早于政策收紧，是这个账号唯一能跑的容器。

⇒ 共用它。**共用的是容器，不是代码库**：cninfo 仓库里只有挂载代码
（`api/audit_mount.py`）与一个 `finaudit/` 挂载点；本仓仍是权威副本。

## 载荷：推什么

```
finaudit/
  src/                      代码（PYTHONPATH 指向这里）
  metrics/                  口径定义
  data/extracted/           真实年报抽取结果（只有人工核对过的字段）
  eval/frozen-01/fixtures/  合成夹具（页面上标成合成）
```

🔴 **目录形状是有承重作用的。** `service/api.py` 从**自己的模块路径**推数据根
（`src/service/api.py` → 三层 parent），所以 `src/` 那一层必须保留，
`metrics/` 与 `data/` 必须是它的兄弟。`PYTHONPATH` 指 `finaudit/src`，不是 `finaudit`。

约 770 KB。**不推**：`data/raw/`（年报 PDF）、`docs/`、`tests/`、`references/`、
`.planning/`、`eval/frozen-01/cases/`。

🔴 **`.dockerignore` 不是上传清单。** 它管「进不进镜像」，管不到「进不进那个
**公开**仓库」。2026-09-07 组装载荷时 `src/*.egg-info/` 就是这么混进来的 ——
`.dockerignore` 里明明写着 `*.egg-info/`，而 `cp -r` 不读它。
⇒ 推之前显式剔除 `*.egg-info/` / `__pycache__/` / `*.pyc`，并把全文件清单过一遍眼。

## 推之前的安全清扫（七类，`D-005` 修订一的硬约束）

那个 Space 是 **public**，所以载荷里出现的任何一个密钥都是**永久泄漏**。

1. 密钥形状（`sk-` / `hf_` / `ghp_` / `AKIA` / PEM 头）
2. 本机绝对路径与用户名
3. 邮箱
4. 口令赋值式
5. 构建残留
6. 数据文件里的 `source_url`（必须是 `null` 或 http(s)，不能是 `file://`）
7. **全文件清单逐条过目**

## 两个 Space secret

| 名字 | 谁用 | 说明 |
|---|---|---|
| `FINAUDIT_API_TOKEN` | 本服务 | 调用方在 `X-Finaudit-Token` 头里出示同一个值 |
| `FINAUDIT_MODEL_KEY` | 指标名归一 | **可选**。没配就是没模型 —— 认不出的说法照旧拒答，不是报错 |

⚠️ **没设 `FINAUDIT_API_TOKEN` 时 `/audit/*` 根本不注册**（`api/audit_mount.py`）。
这是有意的：一个敞开的问答端点比一个不存在的端点糟。
注意它与 cninfo 自己的 `API_TOKEN` **刻意不同** —— 后者没配时是 fail-open（本地开发用）。

## 前端那两个 Cloudflare Pages 变量

| 名字 | 值 |
|---|---|
| `AUDIT_API_BASE` | `https://rgt07-cninfo-financial-analyzer.hf.space/audit`（**带 `/audit` 前缀**，无尾斜杠） |
| `AUDIT_API_TOKEN` | 与 Space secret `FINAUDIT_API_TOKEN` 同值 |

`AUDIT_PLATFORM_TOKEN` **不用配** —— Space 是 public，平台自己没有门禁。

## 三个端点

```
GET  /audit/coverage   我们对哪些公司/年份真的有数据
POST /audit/verify     {"text": "贵州茅台 2023 年净利率 50.6%，盈利能力持续增强。"}
POST /audit/answer     {"question": "600519 2023 年的资产负债率是多少"}
```

`/verify` 是 `D-041` 那个**入口**：一段结论 → 逐条判成五态之一。
`/answer` 保留 —— `frozen-01` / `frozen-02` 的评测臂打的是它，换掉它等于换掉
评测臂脚下的地面（`D-012`）。

**两个都只收一段字符串** —— 没有文件上传、没有 CSV、没有表格粘贴（`D-010`）。

🔴 **`/verify` 的扇出在挂载侧有一道线程池跳转，在上游有一道条数上限**
（`agent.verify.MAX_CHECKABLE_CLAIMS = 24`）。一次 `/answer` 最多一次阻塞模型调用，
一次 `/verify` 最坏 24 次串行 —— 跑在事件循环上会把同进程里每一条 `/jobs*` SSE
流卡住整个时长。**两道缺一不可。**

## 回退

Space 是 git 仓库。合体那次推送之前的 HEAD 是
`b6ff5428c323b63066bf4b845898bd4be90ba38e`，回退一次 push 即可。
