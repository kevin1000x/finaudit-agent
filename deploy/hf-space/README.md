---
title: finaudit answering service
emoji: 📑
colorFrom: gray
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# finaudit — 可审计财务分析问答服务

> ⚠️ **这份 README 是给 Hugging Face Space 用的，不是给本仓库用的。**
> 上面那段 YAML 前言是 HF Spaces 的配置（`sdk: docker` + `app_port`），
> 它必须位于 **Space 仓库根目录的 `README.md`**。放在本仓库这个位置只是为了让它
> 跟着版本控制走 —— 推 Space 的时候把它复制成 Space 根目录的 `README.md`。

无状态的请求–响应服务。给一个问题，返回一个数与一条可独立复核的证据链。

## 这个 Space 是公开的，主仓不是

`D-005` 修订一（2026-09-07）：private + docker 的 Space 要 PRO 订阅，
⇒ 放弃「Space 私有」，换一个能点开的链接。

公开的是**实现**（`src/` + `metrics/` + `data/extracted/` + 合成夹具，共 14483 行）；
**不公开**过程与结论（`docs/` / `tests/` / `references/` / `.planning/` / 评测题面，
另有 71887 行），GitHub 主仓 `kevin1000x/finaudit-agent` 仍 private 至 Phase 4。

🔴 **因此这个仓库里出现的任何一个密钥都是永久泄漏。**
两个令牌一律走 Space secret：`FINAUDIT_API_TOKEN`、`FINAUDIT_MODEL_KEY`。

## 两个环境变量

| 名字 | 谁用 | 说明 |
|---|---|---|
| `FINAUDIT_API_TOKEN` | 本服务 | 调用方要在 `X-Finaudit-Token` 头里出示同一个值 |
| `FINAUDIT_MODEL_KEY` | 指标名归一 | **可选**。没配就是没模型 —— 认不出的说法照旧拒答，不是报错 |
| `PORT` | 平台注入 | 不用手配；没有时默认 7860 |

⚠️ **没设 `FINAUDIT_API_TOKEN` 时服务会拒绝启动**（因为它绑 `0.0.0.0`）。
这是有意的：「设了才检查」会让「忘了配」变成一个完全敞开、且没有任何一处会响的服务。

## 令牌为什么不走 `Authorization`

这个 Space 是 public，平台自己没有门禁，`Authorization` 本可以给本服务用。
**仍然分成两个头**，因为改回去要动前端的 Pages Function，而那一头正好是
「哪天 Space 转私有、平台开始吃 `Authorization: Bearer <hf_token>`」时唯一要改的地方。
⇒ 本服务的令牌走 `X-Finaudit-Token`；`Authorization: Bearer` 也仍被接受。

## 两个端点

```
GET  /coverage   我们对哪些公司/年份真的有数据
POST /answer     {"question": "600519 2023 年的资产负债率是多少"}
```

**只收一个问题字符串** —— 没有文件上传、没有 CSV、没有表格粘贴（`D-010`）。

## 推一个 Space 需要哪些文件

Space 仓库 = 这份 README（改名为根目录 `README.md`）+ 本仓库的：

```
Dockerfile
.dockerignore
src/                      代码
metrics/                  口径定义
data/extracted/           真实年报抽取结果（只有人工核对过的字段）
eval/frozen-01/fixtures/  合成夹具（页面上标成合成）
```

**`data/raw/`（年报 PDF）不推** —— 几百 MB，而这个服务不解析 PDF。

🔴 **`.dockerignore` 不是上传清单。** 它管的是「进不进镜像」，管不到「进不进这个
**公开**仓库」。2026-09-07 组装载荷时 `src/*.egg-info/` 就是这么混进来的 ——
`.dockerignore` 里明明写着 `*.egg-info/`，而 `cp -r` 不读它。
⇒ 推之前显式剔除 `*.egg-info/`、`__pycache__/`、`*.pyc`，并把全文件清单过一遍眼。
