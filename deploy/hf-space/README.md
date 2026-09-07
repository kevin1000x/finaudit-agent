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

## 🔴 这个 Space 必须是 private

`D-005`：主仓保持私有到 Phase 4，可对外的是「**可访问的链接**」，不是源码。
而 Space 的构建源就是它的仓库内容 —— **建成 public 等于把主仓提前公开**。
那是一次 `D-005` 修订，不是一个部署细节。

## 两个环境变量

| 名字 | 谁用 | 说明 |
|---|---|---|
| `FINAUDIT_API_TOKEN` | 本服务 | 调用方要在 `X-Finaudit-Token` 头里出示同一个值 |
| `PORT` | 平台注入 | 不用手配；没有时默认 7860 |

⚠️ **没设 `FINAUDIT_API_TOKEN` 时服务会拒绝启动**（因为它绑 `0.0.0.0`）。
这是有意的：「设了才检查」会让「忘了配」变成一个完全敞开、且没有任何一处会响的服务。

## 令牌为什么不走 `Authorization`

private Space 的平台门禁自己要吃 `Authorization: Bearer <hf_token>`。
两个令牌塞一个头，只能塞进去一个。⇒ 本服务的令牌走 `X-Finaudit-Token`；
`Authorization: Bearer` 仍被接受，那是 Space 建成 public 时的兼容路径。

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
`.dockerignore` 挡了一道，这里再说一遍：两处都可能被人改。
