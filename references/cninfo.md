# cninfo-financial-analyzer / cninfo-analyzer-web

**读到什么程度**：下载链路与 PDF 抽取**实跑验证过**（真下了茅台 2023 年报并取出数）；
`pipeline.py` / `metrics.py` / `financial_data_sources.py` 读过关键路径；
web 端 README 与生产部署链路读完。未读：`text_analyzer.py` 全文、测试、`docs/superpowers/`。

---

## 1. 年报下载链路（**已实跑，不需要 cookies**）

三步，全部标准库可完成：

```text
1. GET  http://www.cninfo.com.cn/new/data/szse_stock.json
        → stockList[] 里按 code 找 orgId（600519 -> gssh0600519）

2. POST http://www.cninfo.com.cn/new/hisAnnouncement/query
        form: pageNum/pageSize/column(sse|szse)/tabName=fulltext
              stock="600519,gssh0600519"
              category=category_ndbg_szsh        # 年报
              seDate="2024-01-01~2024-12-31"     # 年报在次年披露
              isHLtitle=true
        → announcements[] 每条含 announcementTitle 与 adjunctUrl

3. GET  http://static.cninfo.com.cn/{adjunctUrl}
        → PDF 字节流
```

**必须带的 header**：`User-Agent`、`Referer: http://www.cninfo.com.cn/new/disclosure`；
POST 另加 `Content-Type: application/x-www-form-urlencoded`、`Origin`、`X-Requested-With`。

**标题筛选不能只匹配「年度报告」**。实测 600519/2023 返回 3 条：正式年报、**年度报告摘要**、
**年度报告（英文版）**。摘要里没有完整报表，英文版行项目名对不上。
排除词至少要有：摘要 / 问询 / 更正 / 补充 / 英文 / 已取消。

**category 取值**：`category_ndbg_szsh` 年报、`category_bndbg_szsh` 半年报、
`category_jdbg_szsh` 季报。

## 2. PDF 取数（**已实跑，这是真正的技术内容**）

### 坑一：整页取文本直接用是不行的

页面纯文本流里，**表格是逐单元格一行**的：
「应收账款」在一行，它的本期数、上期数在另外几行。按行做正则只能抓到标签，抓不到数。

**正解：按坐标重组行。**

> ⚠️ **下面的实跑代码用的是 `fitz`（PyMuPDF），而 D-014（2026-08-16）已禁用该库**
> —— AGPL v3 与 D-005「主仓私有」冲突。**方法可移植，实现必须换成 pdfplumber。**
> 此处保留原始代码是为了让 9/12 这个数字可追溯到它实际产生的方式，
> **不是**让人照抄进生产代码。

```python
# 实跑版本（fitz，已禁用，仅存档）
words = page.get_text("words")     # (x0, y0, x1, y1, word, block, line, wordno)
buckets = {}
for x0, y0, x1, y1, word, *_ in words:
    buckets.setdefault(round(y0 / 3.0), []).append((x0, word))   # y 容差 3.0
for key in sorted(buckets):
    cells = [t for _, t in sorted(buckets[key])]                 # 行内按 x 排序
```

```python
# 迁移目标（pdfplumber，MIT）—— 结构同上，字段名不同，**尚未实测**
for w in page.extract_words():     # dict: x0, x1, top, bottom, text
    buckets.setdefault(round(w["top"] / 3.0), []).append((w["x0"], w["text"]))
```

`extract_words()` 默认按 `use_text_flow=False` 排序并做词切分，
`x_tolerance` / `y_tolerance` 是它自己的参数，**与上面那个 `/3.0` 的桶宽不是一回事**，
迁移时要重新标定，不能假设同一个容差值。

40 行代码，茅台 2023 资产负债表抓到 9/12 目标行项目 —— **该数字来自 fitz 实现。
换库后的命中数未测，见台账 A-4，判据是 ≥ 9/12。**

### 坑二：定位报表页

搜「合并资产负债表」会同时命中**目录页**。实测有效的排除法：正文页的
`text.count("合并") <= 6`，目录页会同时列出多个表名。
茅台 2023（143 页）定位结果：资产负债表 p57、利润表 p62、现金流量表 p65。

**顺带**：审计报告正文就在资产负债表前一页（p57 页首即审计意见段落与签字注册会计师、
事务所、日期）。Phase 0 要做的「非标审计意见抽取」，数据在同一份 PDF 里，位置还紧邻。

### 坑三（最重要）：空格子 ≠ 缺失

茅台 2023 的**短期借款 / 长期借款 / 应付债券**：

```text
p58: 短期借款          ← 整行只有标签，没有任何数字单元格
p59: 长期借款
p59: 应付债券
```

行项目**印在报表上**，值的格子**是空的**——茅台没有有息负债。

这直接决定了抽取器的语义：

| 报表实况 | 应输出 | 理由 |
|---|---|---|
| 行在，格子有数 | 该数值 | — |
| **行在，格子空** | **0** | 公司列示了该项目并声明其为零，这是一个**已知事实** |
| 整行不存在 | **缺失** | 报表未列示，无从判断是零还是并入他项 |

**本项目当前的 `interest_bearing_debt_ratio` 会在第二种情况下拒答**，而正确行为是算出接近零的值。
这条规则必须住在抽取层，`missing_representation` 字段就是为承载它设计的。
（台账 A-2）

### 坑四：计量单位就印在页头

报表页头有 `编制单位:贵州茅台酒股份有限公司` / `单位:元 币种:人民币`。
**`unit_scale_mismatch` 这个 flag 是有真实字段可承载的**——只要数据来自 PDF。
此前判「报表没有承载计量单位的字段」是照着 AKShare 的列在想，错了。

## 3. AKShare 能给什么（实测）

`ak.stock_financial_report_sina(stock="sh600519", symbol="资产负债表")`
→ **103 期 × 147 列**；利润表 103×83；现金流量表 99×71。数据是富的。

**但不要用子串匹配去映射列名。** 我试过，产出一批静默错误：

```
bs.total_liabilities  ← 流动负债合计        ✗ 流动负债不是负债合计
is.net_profit_attr..  ← 净利润              ✗ 那是含少数股东损益的
bs.accounts_payable   ← 应付票据及应付账款   ✗ 合并列，我们的定义明文禁止合并应付票据
```

这正是本仓库记录的 cninfo 缺陷（`_first_column()` 取第一个命中的列且不记录用了哪个）——
**我在探测脚本里原样重演了一遍。** 映射必须是逐条人工确认 + 版本化的映射表，不是模糊匹配。

**D-013 约束**：AKShare 只可作对照，不作权威源，财务数值以年报 PDF 原文为准。
所以 AKShare 的用途是**交叉校验**：PDF 抽出的数与 AKShare 不一致 → 触发
`source_disagreement`（system 域 flag，词表里已有）。这比只用其中一个更强。

## 4. cninfo 自身的架构（用于判断能复用什么）

- `METRIC_COLUMNS = ["stock_code","year","roa","ocf"]` 是 **AKShare 取数路径的窄化选择**，
  为它那个「语调 vs 业绩」研究裁的，**不是能力上限**。
- `metrics.py` 算的全是文本语调指标（TNI、performance score、tone×financial 合并），
  财务数据从**外部 CSV** 喂入（`load_financial_data_from_csv`）。
- `pdf_parser.extract_financial_statements()` 存在，但**只做关键词分类**
  （`identify_financial_statement` 是整表文本的子串匹配，会误判），
  且 `pipeline.py:758` 硬写 `'financial_statements': {}` —— **抽取器没接进管道**。

**结论：PDF 侧的能力是「脚手架」不是「成品」。** 三条文本路径（pdfplumber / PyMuPDF / OCR）、
表格抽取、章节抽取（`extract_mda_section`）都可借鉴思路，但「报表行项目 → 字段 id」
这一层它没有，而那正是本项目要建的。

**且这三条路径本项目只能用其中一条**：PyMuPDF 因 AGPL 被 D-014 排除，
OCR 被 ROADMAP Phase 1.5「明确不做」排除 —— **只剩 pdfplumber**。
注意 cninfo 的 pdfplumber 调用是 `:81` 逐页 `extract_text()` **无 layout 参数**、
异常吞成 `""`，`:134` 的选择逻辑仅在**完全为空**时才退回 PyMuPDF。
即：它从未在「pdfplumber 抽得不全但非空」的情形下做过任何补救，
**那恰好是财务报表页最可能出现的失败形态**。这条路径不能照搬。

## 5. web 端与部署（决定前端怎么接）

```text
浏览器 → Cloudflare Pages（React 19 + Vite + Tailwind v4）
       → /api/proxy/*  Pages Function
       → 具名 Cloudflare Tunnel（API_BASE，Pages secret）
       → FastAPI 后端（uvicorn，单任务设计，并发返回 429）
```

- 组件只有三个：`JobForm`（股票代码/年份/报告类型）、`StreamView`（EventSource 消费 SSE）、
  `ResultCard`（完成态 + xlsx 下载）。**无路由、无状态管理库、无 UI 框架**（README 明说是刻意的）。
- `API_BASE` 必须是**具名** tunnel，quick tunnel（`*.trycloudflare.com`）不支持 SSE。
- 刷新恢复：`job_id` 存 localStorage，重载时先 `GET /jobs/{id}` 再重连 SSE，
  后端最多回放 1000 条事件。
- **后端跑在哪，仓库里不写**——那是 Pages secret。
  ⚠️ **不要从仓库内容推断部署环境。** 2026-08-15 我据此错判「没用 HuggingFace」。

**对本项目的意义**：`JobForm → StreamView → ResultCard` 这个三段式，
形态与「提问 → 流式推理过程 → 带证据链的答案卡」是**对得上的**，
增量加页面可行，SSE 那套可直接复用。

## 6. 后端 SSE 的三个正确性细节（读了 `api/main.py` 原文）

`api/main.py` 318 行 / `api/runner.py` 340 行。`stream_job` 那段写得很讲究，
三处注释解释的都是**踩过才知道**的坑，直接抄：

### 6.1 快照与订阅之间不能有 `await`

```python
snapshot = list(job.history)
already_finished = job.finished.is_set()
queue = None if already_finished else subscribe(job)
```

原注释：「Snapshot history and register subscriber **atomically — no `await`
between these two lines**, so a concurrent `_publish` on the loop cannot interleave
(asyncio is single-threaded per loop).」

中间只要有一次 `await`，并发的 publish 就能插进来，导致事件**既不在快照里、
也不在订阅队列里**——静默丢事件。

### 6.2 每条事件带确定性的单调 id，用于跨重连去重

```python
seq += 1
yield {"event": event_type, "data": json.dumps(payload, ensure_ascii=False), "id": str(seq)}
```

原注释：EventSource 在浏览器侧把它暴露成 `MessageEvent.lastEventId`，
而自动重连**总是重放完整历史**，所以前端靠这个 id 去重。
关键是「**Numbering is deterministic across reconnects: event at history index k
always carries id k+1**」——编号必须由历史下标决定，不能用时间戳或随机 id。

### 6.3 心跳必须走协议层，不能走 generator

```python
return EventSourceResponse(event_source(), ping=15)
```

原注释：`ping=15` 在**线路层**发 SSE 注释，不经过我们的 generator，
所以心跳流量「never enters `job.history` and never replays on reconnect」。
并且明说：「**Required to keep Cloudflare Tunnel and other intermediate proxies
from closing idle SSE connections.**」

**对本项目**：证据链的流式推送会比这个 job 日志更长（每一步都要留痕），
上面三条一条都不能省。特别是 6.3——本项目若也走 Cloudflare Tunnel，
不发心跳就会在长推理时被中间代理掐断。

### 6.4 后端形态对本项目的约束

- **单任务设计**：并发提交返回 `429`。本项目若要支持多人同时试用，这一层要改。
- **鉴权**：`API_TOKEN` 走 `Authorization: Bearer`，在请求时读环境变量
  （注释说是为了让测试 fixture 能改）。浏览器**永远看不到 token**，它只存在于 Pages Function 里。
- **路由**：`POST /jobs` → `GET /jobs/{id}` → `GET /jobs/{id}/stream` → `GET /jobs/{id}/result`。
  本项目的问答可沿用同一形状：提问建 job、流式看推理、结果取证据链。
