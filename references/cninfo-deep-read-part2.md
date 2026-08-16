# cninfo-financial-analyzer 深读 Part 2

目标仓库：`C:\Users\Kevin\Desktop\excel\学校\求职\秋招\cninfo-financial-analyzer`
（只读，本轮未修改任何文件）
读取日期：2026-08-16 ｜ HEAD：`8e47956 Stamp SSE events with monotonic ids...`

---

## 0. 读到什么程度（自报）

| 文件 | 读到什么程度 |
|---|---|
| `src/metrics.py` | **读完** 1–393 |
| `src/utils.py` | **读完** 1–357 |
| `src/downloader.py` | **读完** 1–873 |
| `src/financial_data_sources.py` | **读完** 1–292 |
| `supabase/migrations/20260710170119_financial_metrics_cache.sql` | **读完** 1–27（`supabase/` 下**只有**这一个文件） |
| `scripts/build_sentiment_dictionary.py` | **读完** 1–121 |
| `scripts/smoke_real.sh` | **读完** 1–93（`scripts/` 下**只有**这两个文件） |
| `tests/test_metrics.py` | **读完** 1–273 |
| `tests/test_financial_data_sources.py` | **读完** 1–166 |
| `tests/test_supabase_migration.py` | **读完** 1–18 |
| `tests/test_downloader.py` | **读完** 1–471 |
| `tests/test_api.py` | **读完** 1–407 |
| `tests/test_pipeline.py` | **读完** 1–839 |
| `src/pipeline.py` | **本轮重新读完** 1–1315（为独立回答勾稽问题，不采信上一轮结论） |
| `config.yaml` | **本轮重读完** 1–161 |
| `src/pdf_parser.py` | **本轮只读 283–442**（表格抽取 + 财报识别段）。其余段落是上一轮读的，本轮未复核 |
| `api/runner.py` | **本轮只读 202–313**（grep 上下文）。其余为上一轮所读，本轮未复核 |
| `examples/financial_data.csv` | **读完** 13 行 |
| `src/text_analyzer.py` / `api/main.py` / `data/dictionaries/NOTICE.md` / `LICENSE` / `requirements.txt` / `CLAUDE.md` / `tests/test_text_analyzer.py` / `tests/test_pdf_parser.py` | **本轮未读**（上一轮已读，本轮不重复） |
| `README.md` `PROJECT_SUMMARY.md` `USAGE_GUIDE.md` `INSTALLATION.md` `examples/full_analysis_example.py` `Dockerfile` `docker-compose.yml` `Makefile` `setup.py` `mypy.ini` `.gitignore` `docs/frontend-handoff/*` `src/__init__.py` | **完全未读** |

本轮另有一次**真实执行**（见 §1.3、§2.2），命令与输出在正文内贴出。

---

## 1. 头号问题：pipeline 里有没有做过任何形式的勾稽校验？

### 1.1 结论：**没有**

我读了以下文件的全文，其中**没有出现任何形式的会计恒等式校验**：

- `src/pipeline.py` 1–1315（完整）
- `src/metrics.py` 1–393（完整）
- `src/financial_data_sources.py` 1–292（完整）
- `src/utils.py` 1–357（完整）
- `src/downloader.py` 1–873（完整）
- `src/pdf_parser.py` 283–442（表格抽取与财报识别段）
- `config.yaml` 1–161（完整）
- `supabase/migrations/*.sql`（完整，仅 1 个文件）
- `tests/` 下 6 个测试文件全文

具体地，以下检查在上述范围内**一处都没有**：

| 恒等式 | 有无 |
|---|---|
| 资产 = 负债 + 所有者权益 | 无 |
| 流动资产分项之和 = 流动资产合计（任何小计/合计的加总校验） | 无 |
| 营业利润 → 利润总额 → 净利润 逐级推导 | 无 |
| 本期期初数 = 上期期末数 | 无 |
| 现金流量表期末现金 = 期初现金 + 净增加额 | 无 |
| ROA 与「净利润 / 总资产」交叉验算 | 无 |
| 抽出来的任意两个数字之间的自洽检查 | 无 |

`src/pipeline.py` 的五个阶段是 **download → parse → analyze(tone/fog) → metrics(TNI) → save**（`run()` L841–944，`run_streaming()` L950–1075）。第 4 阶段 `metrics_phase` L637–669 只做两件事：调 `calculate_all_metrics`、打印描述性统计。没有任何校验分支、没有 raise、没有 warning 级别的一致性检查。

**注意边界**：这只是「我读过的这些文件里没有」。配置、部署、密钥、运行时环境、数据内容这四类天然不在代码仓库里；我也未读 README/USAGE_GUIDE 等文档，不排除文档里描述了某种人工复核流程（`examples/full_analysis_example.py:239` 出现过一句 `"5. Validate results by spot-checking a few reports manually"`，这是打印给用户看的提示文字，不是代码）。

### 1.2 「形似但不是」的两处

**(a) `identify_financial_statement`（`src/pdf_parser.py:390–411`）——只是子串匹配，连「这是不是资产负债表」都没验证**

```python
keywords = self.financial_keywords.get(statement_type, [])
table_text = table.astype(str).to_string()
for keyword in keywords:
    if keyword in table_text:
        return True
```

关键词来自 `config.yaml:45–57`，`balance_sheet` 就三个词：`资产负债表 / 合并资产负债表 / Balance Sheet`。做法是**整张表 DataFrame 转成一个大字符串再找子串**。后果：

- 目录页、附注里任何提到「资产负债表」三个字的表格都会被判定为资产负债表。
- `extract_financial_statements` L413–434 用 `statements['balance_sheet'] = table` 直接赋值，**后命中的覆盖先命中的**，最终每类只留最后一张，没有候选记录、没有置信度、没有页码留痕，日志只打一句 `Identified N financial statements`（L433）。

这是「识别」的失败，还没走到「校验」。所以谈不上部分勾稽。

**(b) 上一层：这些 `financial_statements` 根本没有进入指标计算**

`pdf_parser.parse_pdf` 把它放进 `result['financial_statements']`（L478），`save_parsed_data` 把它落成 CSV（L522）。但 `pipeline.metrics_phase` 的入参是 `analysis_results`（tone/fog）与 `financial_data`（外部 CSV / AKShare），**从不读 `financial_statements`**。`_load_parsed_results` 甚至把它硬编码成空字典（`pipeline.py:757–758`：`'tables': [], 'financial_statements': {}`）。

也就是说：**这个项目从 PDF 里抽出来的财务报表，与它最终算出来的财务指标，是两条不相交的路径。** 不存在「抽出来的数字之间要自洽」的场景，因为抽出来的数字压根没被用。

### 1.3 唯一一处「数量级基线校验」（不是勾稽，但思路同类）

`scripts/build_sentiment_dictionary.py:40–42, 107–115`：

```python
EXPECTED_POS_RAW = 3338
EXPECTED_NEG_RAW = 5890
RAW_DRIFT_TOLERANCE = 50  # alarm if upstream shifts beyond this
...
if pos_drift > RAW_DRIFT_TOLERANCE or neg_drift > RAW_DRIFT_TOLERANCE:
    print("WARNING raw row counts drift more than ...", file=sys.stderr)
```

对上游资源记住期望规模、超容差告警。**行为是 print 到 stderr 并 `return 0`——不阻断、不非零退出。** 这是全仓库唯一一处「拿实际数跟预期数对账」的代码，且对象是情感词典而非财务数字。

---

## 2. 逐文件发现

### 2.1 `src/metrics.py`（读完 1–393）

**算了哪些指标**

| 函数 | 行号 | 产出 |
|---|---|---|
| `standardize_series` | 33–69 | zscore / minmax；std==0 或 max==min 时返回**全 0** 并 warning（L49–51、60–62） |
| `calculate_performance_change` | 71–96 | `groupby('stock_code')[metric].diff()`，**一阶绝对差分**，不是同比增长率 |
| `calculate_performance_score` | 98–137 | `perf_score`：以 `roa_change` 为主，缺失时回退 `ocf_change` |
| `calculate_tni` | 139–175 | `TNI = Z(tone) × (-1) × Z(perf)` |
| `merge_tone_and_financial` | 177–213 | 以 tone 为左表 `how='left'` 按 (stock_code, year) 合并 |
| `calculate_all_metrics` | 215–273 | 上述编排 + `tone_normalized`、`perf_score_normalized` |
| `generate_summary_statistics` | 275–327 | mean/std/min/max/median，TNI 另加正负计数 |
| `handle_missing_data` | 329–356 | skip / interpolate / forward_fill |
| `load_financial_data_from_csv` | 359–392 | 读 CSV、列名小写化、`stock_code` 补零到 6 位 |

**取数字段从哪来**：只有两条路。① 用户给的 `financial_data_csv`（`load_financial_data_from_csv` L359）；② `api/runner.py:223–246` 用 AKShare provider 生成的临时 CSV。**没有一个数字来自本项目抽的 PDF 表格。**

**口径是否写死**：写死，而且比配置更死。

- `config.yaml:88–92` 声明了四个指标 `roa / ocf / roe / profit_margin`；
- 但 `financial_data_sources.py:16` 的 `METRIC_COLUMNS = ["stock_code","year","roa","ocf"]` 只支持两个；
- 而 `calculate_all_metrics` L244–248 又把 `primary_metric='roa', secondary_metric='ocf'` **硬编码在调用点**。

配置里的 `roe` / `profit_margin` 永远不会生效——**这是一个「看起来可配置、实际不可配置」的假配置项**，与本项目 `rules/failure-modes.md` 第 2 条（假 flag）是同一类错误，可以直接引用为外部实例。

口径细节全部缺失：

- **没有分子/分母定义**。`roa` 就是外部给的那个数。AKShare 侧取的是 `"总资产净利润率(%)"`（`financial_data_sources.py:17`），是否用平均总资产、是否年化，代码不知道也不记录。
- **没有期初/期末平均处理**。
- **没有年化**。
- **`change` 是绝对差分**（百分点差），不是增长率。
- **量纲混用**：`roa` 是百分数（examples 里 0.85 / 2.45，AKShare 列名带 `(%)`)，`ocf` 是绝对金额（元）。L131 让这两个量纲完全不同的数**互相 fillna**。

**同名指标的多候选列 / 有无留痕**

`financial_data_sources.py:17–18` + `_first_column` L102–107：

```python
ROA_COLUMN_CANDIDATES = ("总资产净利润率(%)", "总资产利润率(%)", "资产报酬率(%)")
OCF_COLUMN_CANDIDATES = ("经营现金净流量(元)", "经营活动产生的现金流量净额")

@staticmethod
def _first_column(frame, candidates) -> pd.Series:
    for name in candidates:
        if name in frame.columns:
            return pd.to_numeric(frame[name], errors="coerce")
    return pd.Series(pd.NA, index=frame.index, dtype="Float64")
```

按顺序取第一个存在的列，**返回值不带任何「实际命中了哪个候选」的信息，日志也不记，落库也不记**。OCF 还有第三个来源——`_abstract_operating_cash_flow` L109–135 从 `stock_financial_abstract` 的 `经营现金流量净额` 行取数。**三个不同口径的 OCF 写进同一列，事后无法区分。**

### 2.2 `src/utils.py`（读完 1–357）——重点：缺失 vs 零

**数值清洗：没有。** 整个文件涉及数字的只有 `normalize_company_code`（L78–95，正则去非数字后补零截断）、`parse_year_range`（L229–252）、`format_bytes`（L255–269）、`count_chinese_chars`（L292–303）。

具体地，以下**全部没有**：

- 千分位逗号剥离
- 百分号处理
- 括号负数（`(1,234)` 表示 -1234，中文年报常见）
- 全角数字 / 全角括号
- `—` `-` `不适用` `/` 这类占位符与真实 0 的区分
- 单位换算（万元 / 亿元 / 元）

**「缺失」与「零」的区分——这是本次深读最重要的发现。**

区分逻辑不在 utils.py，分散在两处，且**第二处把第一处做对的事情毁掉了**：

**做对的一层**：`financial_data_sources.py:60–64`

```python
normalized["year"] = pd.to_numeric(normalized["year"], errors="coerce")
normalized["roa"] = pd.to_numeric(normalized["roa"], errors="coerce")
normalized["ocf"] = pd.to_numeric(normalized["ocf"], errors="coerce")
```

无法解析 → NaN，空串 / `—` / `不适用` 都变 NaN，与真实 0 区分得开。这一层是对的。

**毁掉它的一层**：`metrics.py:131`

```python
perf_score = df[primary_change_col].fillna(df.get(secondary_change_col, 0))
```

当 `ocf_change` 列不存在时，`df.get(..., 0)` 返回**标量 0**，于是 `fillna(0)` 把**所有缺失的绩效变化静默变成「变化为零」**。

紧接着 `handle_missing_data` L339–342 的 `skip` 策略：

```python
df = df.dropna(subset=['tone_raw', 'perf_score'])
```

——`perf_score` 已经没有 NaN 了，这个 dropna 对绩效侧**一行都删不掉**。

**我实际跑了一遍验证**（在仓库根目录执行，只读，未写入仓库）：

```
$ python -c "... MetricsCalculator(cfg).calculate_all_metrics(tone, load_financial_data_from_csv('examples/financial_data.csv')) ..."

INFO | src.metrics:calculate_performance_score:135 - Calculated performance scores using roa and ocf
INFO | src.metrics:handle_missing_data:342 - Dropped rows with missing data: 12 remaining
INFO | src.metrics:calculate_tni:172 - Calculated TNI for 12 observations

   stock_code  year   roa  roa_change  perf_score           tni
0      000001  2020  0.85         NaN        0.00  2.233613e-16
3      000002  2020  2.45         NaN        0.00  2.233613e-16
6      600000  2020  0.75         NaN        0.00  2.233613e-16
9      600036  2020  1.35         NaN        0.00  2.233613e-16
   (每家公司 2021/2022 行的 roa_change 与 perf_score 一致，此处略)
```

输入 12 行，`Dropped ... 12 remaining` —— **一行没删**。每家公司首年 `roa_change` 是 NaN（正确：没有上一年），但 `perf_score` 是 `0.00`（错误：被当成「业绩没变」），并且**照常参与 z-score 标准化与 TNI 计算**。

对 finaudit 而言这是最直接的反面教材：**「无法计算」被静默降级成「计算结果是 0」**，且下游没有任何字段能区分这两者。

**附带一处**：`is_valid_report` L306–331 只检查 `>= 100KB` 且 `.pdf` 后缀，**不检查 PDF 魔数、不检查内容**。

**另一处**：`calculate_file_hash` L115–132 定义了（支持 md5/sha256），但我 grep 全仓库确认**零调用点**。仓库里另外两处 `hashlib.md5` 是对**路径字符串**做哈希用于生成目录名（`pdf_parser.py:70`、`pipeline.py:501`），不是文件内容哈希。**这个项目从不对下载到的 PDF 做内容哈希。**

### 2.3 `src/downloader.py`（读完 1–873）

**完整链路**

1. `_load_org_id_map` L201–215 → 读本地缓存 `data/dictionaries/stock_org_map.json`；缺失则 `_refresh_org_id_map` L217–244 拉 `http://www.cninfo.com.cn/new/data/szse_stock.json` 建 `code → orgId` 映射并落盘。
2. `detect_exchange` L38–49：`6/9` 开头 → `sse`，其余 → `szse`。
3. `_build_se_date` L52–71：annual → `{Y}-10-01~{Y+1}-06-30`（**故意查宽**，注释 L60 明说依赖事后标题过滤）。
4. `query_announcements` L264–346：`POST http://www.cninfo.com.cn/new/hisAnnouncement/query`，`pageSize=30`，`max_pages=10` 硬上限（L298），`stock` 参数是 `"代码,orgId"`（L290），翻页间 `time.sleep(rate_limit)`（L334）。
5. `_filter_announcements` L348–391（见下）。
6. `build_download_url` L397–419：`https://static.cninfo.com.cn/{adjunctUrl}`；文件名 = `sanitize_filename(公告标题) + '.pdf'`。
7. `_download_one_async` L425–494：`retry_attempts` 次重试、指数退避 `2 ** attempt`（L483）、成功后 `await asyncio.sleep(rate_limit)`（L473）、`is_valid_report` 不过就删文件并抛 `ValueError("Invalid PDF file")` 触发重试（L475–477）。已存在且有效则跳过（resume，L446–450）。
8. 并发：`asyncio.Semaphore(concurrent_downloads)` L541 + `TCPConnector(limit=...)` L545。config 默认 `concurrent_downloads: 5, rate_limit: 2.0, retry_attempts: 3`（config.yaml L8–11）。

**是否需要 cookies：不需要。** `CNINFODownloader.__init__(config, cookies=None)` L149–165，无 cookie 可跑。`SeleniumDownloader` L640–763 与 `PlaywrightDownloader` L767–872 只在需要过验证码/登录时用来**导出 cookie jar** 交给 `requests`（`_download_with_browser_cookies` L114–136）。`api/runner.py` 从 `CNINFO_COOKIES_FILE` / `CNINFO_COOKIES_JSON` 环境变量读，前者优先（`test_api.py:321–343` 断言了优先级）。

**标题筛选规则**（L348–391，这是最值得细看的一段）

```python
if year_str not in title:                      # L373  必须含目标年份数字
    continue
if keywords and not any(kw in title for kw in keywords):   # L377  必须命中类型关键词
    continue
if report_type == 'annual' and '半' in title:  # L381  年报排除"半年度"
    continue
skip_words = ['摘要', '更正', '补充', '英文', 'H股']        # L385
if any(sw in title for sw in skip_words):
    continue
```

`type_keywords`（L361–365）：annual = `['年度报告','年报']`。

缺陷（我的判断，依据是上述代码本身）：

- 年份用**字符串子串**匹配，`二〇二〇年年度报告` 这类中文数字标题会被整条漏掉。
- `skip_words` **没有 `修订` / `修订版` / `更新后` / `重述`**。年报修订版会通过筛选，与原版并存。
- 是**黑名单**而非白名单，任何未预料到的后缀都会漏进来。
- 筛掉的公告**不留记录**，只在 L344 打一句 `Found N ... [raw: M]` 的数量差。**为什么筛掉、筛掉了哪些，事后无法复核。**

**产物命名与存放**

- 批量模式：`{download_path}/{stock_code}/{year}/{sanitize_filename(公告标题)}.pdf`（L602–609）。
- 流式模式：`{download_path}/_streaming_tmp/{filename}`（`pipeline.py:1103–1105`），分析完 `finally` 里 `os.remove`（`pipeline.py:1161–1165`）。
- `sanitize_filename`（`utils.py:135–155`）把 `<>:"/\|?*` 换成 `_`，超 200 字符截断到 190 + 扩展名。

**安全相关**：`verify=False` 出现在 L127、L224、L318；`ssl=False` 在 L458、L545；`urllib3.disable_warnings` 在 L24。**全线关闭 TLS 校验。**

### 2.4 `src/financial_data_sources.py`（读完 1–292）

**AKShare 之外有没有别的源：没有。** Supabase 是**缓存**（`FinancialMetricsStore` 协议 L21–26），不是独立数据源；`NullFinancialMetricsStore` L35–44 是无凭据时的空实现。

AKShare 用了两个端点：

- `ak.stock_financial_analysis_indicator(symbol, start_year)` L89–92 —— 主源（新浪年度指标）
- `ak.stock_financial_abstract(symbol)` L100 —— **只在 OCF 缺失时**回补（L174–204）

**各源的口径披露程度：接近零。** 全部披露就是 L17–18 那两行候选中文列名字符串，没有一行注释说明这些指标的会计定义、是否用平均余额、是否年化、单位是什么。

其他关键行为：

- **年度筛选**：只保留 `日期` 的 `%m-%d == "12-31"` 的行（L154–157）。非 12-31 会计年度的公司会被**静默全部丢弃**，不 warning。
- **多取一年**：`CachedFinancialDataProvider.load` L221 `required_years = sorted({min(requested_years) - 1, *requested_years})`——因为下游要算同比。设计正确，且有测试（`test_financial_data_sources.py:55–92`）。
- **缓存失效判据有缺陷**：L230–235 只判断 `(code, year)` 这个键在不在缓存里，**不判断 `roa`/`ocf` 是不是 NaN**。而 `upsert_metrics` L286 `.where(pd.notna(normalized), None)` 会把 NaN 当 None 写进库。所以**某年一旦以 NaN 入库，就永远不会再去 AKShare 重取了**。
- 缓存失败降级：L227–229 catch 后 `logger.warning` 并继续用 AKShare（有测试 L104–127）。

### 2.5 `supabase/`（读完，只有 1 个文件）

`supabase/migrations/20260710170119_financial_metrics_cache.sql` 1–27：

```sql
create table public.financial_metrics (
    stock_code text not null check (stock_code ~ '^[0-9]{6}$'),
    year smallint not null check (year between 1990 and 2100),
    roa double precision,
    ocf double precision,
    source text not null default 'akshare' check (source = 'akshare'),
    fetched_at timestamptz not null default now(),
    primary key (stock_code, year)
);
alter table public.financial_metrics enable row level security;
revoke all on table public.financial_metrics from anon, authenticated;
grant select, insert, update, delete on table public.financial_metrics to service_role;
```

**有没有存溯源信息：没有。** 逐条列一下缺什么：

- 没有「来自哪一页 / 哪个文件 / 哪个 PDF」——因为这张表跟 PDF 完全无关。
- 没有「命中了哪个候选列名」（`总资产净利润率(%)` 还是 `资产报酬率(%)`）。
- 没有「OCF 来自主表还是 abstract 表」。
- 没有原始未清洗值、没有单位、没有抓取 URL、没有响应哈希。
- `source` 列被 `check (source = 'akshare')` **约束成常量**，等于零信息量。
- 唯一的溯源信息是 `fetched_at` 时间戳。

正面：RLS 启用 + 对 anon/authenticated 全撤销 + 只给 service_role（L14–17），以及 L21–27 那段撤销 `rls_auto_enable()` 公开执行权限的 DO 块。

### 2.6 `scripts/`（读完，共 2 个文件）

**没有一次性数据修补脚本。** 目录下只有：

- `build_sentiment_dictionary.py` 1–121：情感词典 xlsx → `POS:/NEG:` 文本。含去重（L82–84，上游 positive 重复约 144、negative 约 269，注释 L34–39）与上游行数漂移告警（见 §1.3）。
- `smoke_real.sh` 1–93：真实 CNINFO 冒烟脚本。`GET /healthz` → `POST /jobs` → `GET /jobs/{id}/stream`（SSE）→ `GET /jobs/{id}/result` 存 xlsx。需要 `jq`。注释 L38–41 记录了一个 bash 3.2 + `set -u` + 空数组展开的坑。

所以「修补脚本暴露 pipeline 缺陷」这条线索在本仓库**不成立**——不是因为 pipeline 没缺陷，而是因为**这个 pipeline 从没跑过需要修补的真实数据规模**（见 §2.7）。

### 2.7 六个测试文件的实现

**先答核心问题：有没有任何一个测试碰过真实 PDF 或真实数据？——没有。**

| 测试文件 | 真实 PDF | 真实网络/数据 | 说明 |
|---|---|---|---|
| `test_pipeline.py` | 否 | 否 | `StubStreamingDownloader.download_one_sync` L52–56 写字面量 `b'%PDF-1.4\n% streaming test placeholder\n'`，且 parser 也是 stub，这个「PDF」从不被真正解析 |
| `test_downloader.py` | 否 | 否 | 全 mock。**`test_download_with_browser_cookies` L406–407 直接 `patch('src.downloader.is_valid_report', return_value=True)`**——把唯一的文件有效性校验 patch 掉了 |
| `test_metrics.py` | 否 | 否 | 全手搓 DataFrame |
| `test_financial_data_sources.py` | 否 | 否 | 全手搓 DataFrame + 假 Store/Source/Client，从不真调 AKShare |
| `test_api.py` | 否 | 否 | `FakePipeline` 替换真 pipeline（L122），写 1 行 xlsx。真实的只有 FastAPI TestClient 与 openpyxl |
| `test_supabase_migration.py` | 否 | 否 | 18 行，读 .sql 文件文本断言含两个字符串（L14–18）。是文本 grep，不连数据库、不执行 SQL |

**各测试实际断言了什么**

`test_pipeline.py`（839 行，最大的一个）：

- MD&A / 全文选择与回退：目录页样式的 MD&A 被拒（L120–143、159–170）、太短被拒（L172–184）、占全文比例过低被拒（L186–198）、有效 MD&A 被采用（L145–157）、pipeline 实例阈值可覆盖（L200–213）
- 导出类型规范化：`stock_code` 整数 1 → 字符串 `'000001'` 且 `cell.data_type == 's'`；`download_date` 毫秒时间戳 → `'2024-03-15'`（L216–247）
- 空 DataFrame 也写出完整 schema（L250–258）
- streaming audit 目录数量上限与「保留最新」（L261–307、L422–468）
- `delete_pdf` / `save_parsed_text` 四种组合的副作用（L310–420、L471–497）
- `finish_work` 无显式确认抛 ValueError、确认后保留 audit 与 results 目录（L500–557）
- 中间态 pickle 存 / 取 / 缺失返回空（L560–595）
- `run()` 的 restore 分支跳过前置阶段（L598–690）
- CLI 参数透传（L693–838）

**一条关于数字正确性的断言都没有。** tone/fog 全是 `StubAnalyzer` 返回的固定常量（L25–39）。

`test_metrics.py`：

- zscore 均值≈0 / std≈1（L58–67）、minmax 得 0 和 1（L70–77）、std=0 返回全 0（L80–86）
- `roa_change` 首行 NaN、第二行 ≈0.03（L89–101）
- **`test_calculate_performance_score` L104–111 只断言 `len(perf_score) == len(df)`——只验长度，不验值。** 这条测试正是 §2.2 那个 `fillna(0)` 缺陷长期不被发现的原因
- `test_calculate_tni` L114–125 断言 `len(tni)==5` 与 `tni.max() > 0 or tni.min() < 0`（后者对任何非常量序列几乎恒真）
- merge 行数与列存在（L128–137）
- `calculate_all_metrics` 必需列存在、`tni` 不全为 NaN（L140–150）
- summary 结构（L153–170）
- `handle_missing_data` skip 删掉 tone_raw 为 NaN 的行（L173–183）——注意它测的是 **tone 侧**，不是 perf 侧
- CSV 加载后 stock_code 补零（L186–206）
- TNI 语义（L209–226）：两种「语气与业绩背离」场景都应得正 TNI
- 多公司分组 diff（L229–248）、空 DataFrame（L251–258）、缺列（L261–269）

**测试量纲与生产量纲不一致**：fixture 用 `roa: [0.05, 0.08, ...]`（L52，像小数比率），而 `examples/financial_data.csv` 用 `0.85 / 2.45`、AKShare 列名是 `总资产净利润率(%)`（百分数）。测试用了「看起来对」的数据，把真实口径问题挡在外面。

`test_downloader.py`：交易所判定（L77–94）、`seDate` 区间字符串（L101–114）、orgId 缓存加载与缺失触发刷新（L129–145）、POST 参数 `stock='000001,gssz0000001'` / `column` / `isHLtitle`（L201–216、L256–261）、下载 URL 走 HTTPS（L268–279）、缺 `adjunctUrl` 返回 `(None, None)`（L282–291）、标题过滤（摘要/更正/补充/英文被剔除、半年报被剔除，L298–324）、stats 初值（L331–336）、session headers 含 UA/Content-Type/Referer/Origin（L354–360）、cookies 透传（L363–370）、Selenium/Playwright `download_with_login` 的调用序列与返回 cookie（L420–466）。

`test_api.py`：healthz 免鉴权（L138–141、198–201）；`API_TOKEN` 未设 = 开发模式放行（L144–149），设了则 401/403/200（L174–195）；输入校验 422（5 位/7 位代码、含字母、年份 1980/9999 越界、`report_types` 白名单、**`prospectus` 已从白名单移除**、任务数 200 > 100 上限，L204–228）；`financial_data_csv` 必须落在 `examples/` 或 `data/` 下（拒 `/etc/passwd`、拒 `../escape.csv`，L231–263）；同时只允许一个 job，第二个 429 并回传 `running_job_id`（L266–288）；SSE 每个事件带 **单调递增、唯一、从 1 开始** 的 id 且以 `eof` 结尾（L291–318）；心跳 `ping` 不进 history（L367–378）；**`result_path` 绑定到该 job 而不是「目录里 mtime 最新的文件」**（L381–406，专门造了一个更新的无关 xlsx 来验证不会被误绑）；cookies 文件优先于环境变量 JSON（L321–343）、坏 JSON 变成 job error（L356–364）。

`test_financial_data_sources.py`：AKShare 只保留 12-31 行并映射到 roa/ocf（L6–23）；OCF 缺失时从 abstract 表 `经营现金流量净额` 行回补（L26–52）；缓存 provider 会额外取 `min(years)-1`（L55–92）；无凭据时 `from_env()` 返回 None（L95–101）；Supabase 抛异常时降级到 AKShare（L104–127）；upsert 用 `on_conflict="stock_code,year"`（L130–165）。

`test_supabase_migration.py`：仅断言 migration 文件存在，且文本里含 `to_regprocedure('public.rls_auto_enable()')` 与那句 `revoke execute on function ...`（L10–18）。

---

## 3. 对 finaudit-agent 的可借鉴点与必须避开的坑

只写有原文依据的，每条附行号。

### 3.1 可借鉴

1. **结果路径绑定到那一次执行，不是「扫目录取最新」**
   `api/runner.py:279` `job.result_path = pipeline.last_output_file`，配 `test_api.py:381–406` 专门造干扰文件验证。
   finaudit 的证据链有完全同构的需求：**证据必须绑定到产生它的那次运行**，绝不能靠「目录里最新的文件」推断。这条应当直接写成 finaudit 的验收测试。

2. **流式输出带单调唯一 id + 终止事件**
   `test_api.py:291–318`（id 从 1 开始、单调、唯一、末尾 `eof`）。长任务的可复核输出需要这个，EventSource 自动重连会重放全量历史，没有 id 就无法去重。

3. **对外部资源记住期望规模，超容差告警**
   `scripts/build_sentiment_dictionary.py:40–42, 107–115`。finaudit 对准则库、科目表、指标口径表可以同构——但**要改成阻断（非零退出），不要像它一样只 print 到 stderr 后 `return 0`**。

4. **计算所需的数据窗口由计算本身声明**
   `financial_data_sources.py:221` 多取一年，因为下游要算同比。finaudit 的「同比 / 环比 / 三年趋势」类问题应当由指标定义声明它需要哪些期间，而不是让取数层猜。

5. **输入路径白名单**
   `test_api.py:231–263`：绝对路径与 `../` 逃逸都拒。

6. **清理动作必须显式确认，且证据产物在白名单里**
   `pipeline.py:567–635`（`finish_work` 无 `confirm_work_complete=True` 直接抛 ValueError L577–580；audit 目录与 results 走 `keep_paths` L626–630），测试 `test_pipeline.py:500–557`。
   **「证据产物默认不可删」这个默认值是对的**，finaudit 应当沿用并加强。

7. **缓存层的最小权限配置**
   migration L14–17（RLS + 对 anon/authenticated 全撤销 + 只给 service_role）。

### 3.2 必须避开的坑

1. **【最严重】缺失被静默变成 0** —— `metrics.py:131`
   实测（§2.2）：12 行输入，每家公司首年 `roa_change=NaN` 但 `perf_score=0.00`，`dropna` 一行没删，TNI 照算。
   finaudit 的硬约束应当是：**「无法计算」是一等状态，必须贯穿到最终输出与证据链**。任何 `fillna` 都是需要留证据的决策，不是默认行为。

2. **量纲混用而无元数据** —— `metrics.py:131`，`roa`（百分数）与 `ocf`（元）互相 fillna；`config.yaml:88–92` 与 `financial_data_sources.py:16–18` 都没有单位声明。
   finaudit 的每个数值必须携带单位/量纲/币种，不能只是一个 float。

3. **候选列选择无留痕** —— `financial_data_sources.py:17–18, 102–107`，三个 ROA 候选取第一个命中的，不记录用了哪个；OCF 更有三个不同来源合进一列（L162–163 + L110–135）。
   finaudit 必须记录：**命中了哪条规则、来自哪个字段名/哪一页、被排除的候选是什么**。

4. **缓存不区分「没取过」与「取到的是空」** —— `financial_data_sources.py:230–235`（只看键存在）+ `L286`（NaN 转 None 写库）。NaN 一旦入库永不重取。
   finaudit 的缓存键必须包含取数结果状态。

5. **假配置项** —— `config.yaml:88–92` 声明 4 个指标，`financial_data_sources.py:16` 只支持 2 个，`metrics.py:244–248` 又把 `roa`/`ocf` 硬编码在调用点。`roe` / `profit_margin` 永远不生效。
   这正是本项目 `rules/failure-modes.md` 第 2 条「假 flag」的外部实例，可以直接引用。

6. **「识别」当成「校验」** —— `pdf_parser.py:390–411`（整表转字符串做子串匹配）+ `L425–431`（后命中覆盖先命中，最终每类只留一张，无置信度、无页码、无候选记录）。
   finaudit 若要做报表识别，**「这张表是不是资产负债表」本身就需要证据**，且必须早于任何数字校验。

7. **抽取路径与计算路径不相交** —— `pipeline.py:757–758` 把 `financial_statements` 硬编码成 `{}`；`metrics_phase` L637–669 从不读它。
   这是 cninfo 项目最大的结构性缺陷：**它抽了报表，却用别人的指标算结论**。finaudit 的立项前提（数字来自年报 PDF 本身，见 D-013）必须在架构上保证这两条路径是同一条。

8. **多候选公告只取第一个，无排序无理由** —— `pipeline.py:1038` `for announcement in announcements[:1]`，按接口返回顺序取，不按发布日期排序；`downloader.py:348–391` 的黑名单里**没有「修订」「重述」**，所以原版与修订版可能都通过筛选。被筛掉的公告只留一个数量差（L344），不留原因。
   finaudit 必须记录**候选集 + 选择规则 + 每个被排除项的排除原因**。

9. **文件有效性校验形同虚设，且被测试 patch 掉** —— `utils.py:306–331` 只看 ≥100KB + `.pdf` 后缀（不看 PDF 魔数）；`test_downloader.py:407` 直接 `patch(..., return_value=True)`。
   另：`calculate_file_hash`（`utils.py:115`）**零调用点**，本项目从不对下载物做内容哈希。
   finaudit 的 D-012（SHA-256 冻结）方向是对的，但要注意**哈希必须在入库路径上真的被调用**，不能像这里一样定义了不用。

10. **全线关闭 TLS 校验** —— `downloader.py:127, 224, 318`（`verify=False`）、`L458, L545`（`ssl=False`）、`L24`（禁 warning）。
    取证类系统不能这样：证据来源的传输完整性直接没有了。

11. **未被测试覆盖的缺失值策略分支很可能是坏的** —— `metrics.py:344–354`：
    - `interpolate` 分支 L346–348 用 `groupby().apply(...).reset_index(drop=True)`，会**重置 index**，而 `calculate_tni` L160–162 依赖 index 求交集对齐 —— 两者冲突。
    - `forward_fill` 分支 L353 `df.groupby('stock_code').fillna(method='ffill')`，在较新 pandas 上 `method=` 已废弃，且 `groupby.fillna` 的返回结构与原 df 不一致。
    - `test_metrics.py` **只测了 `skip`**（L173–183），另外两条分支零覆盖。
    finaudit 的教训：**配置里能选的每个分支都必须有测试**，否则它就是一个会在生产上炸的假选项。

12. **测试数据的量纲与生产不一致会掩盖真问题** —— `test_metrics.py:52`（`roa: 0.05`）vs `examples/financial_data.csv`（`0.85`）vs AKShare `总资产净利润率(%)`。
    finaudit 的测试夹具必须用**真实口径的样例值**，否则口径错误测不出来。

---

## 4. 我没读，因此不能置评的清单

- `README.md`、`PROJECT_SUMMARY.md`、`USAGE_GUIDE.md`、`INSTALLATION.md` —— 本轮完全未读。**不能断言「文档里没有描述勾稽校验/实证结论」**，只能说代码里没有。
- `examples/full_analysis_example.py` 1–267 —— 只见到 grep 命中的 L239 一行，未读全文。
- `api/main.py` 1–318 —— 本轮未读（上一轮亦未列入已读清单）。关于 `_validate_fin_csv` / `_validate_total_tasks` 的具体实现，我只从 `test_api.py` 的断言反推，**没有读过实现体**。
- `api/runner.py` 除 L202–313 外的部分 —— 本轮未复核。
- `src/pdf_parser.py` 除 L283–442 外的部分（1–282、443–582）—— 本轮未读，上一轮所读结论我未复核。
- `src/text_analyzer.py`、`tests/test_text_analyzer.py`、`tests/test_pdf_parser.py` —— 本轮完全未读。
- `Dockerfile`、`docker-compose.yml`、`Makefile`、`setup.py`、`mypy.ini`、`.gitignore`、`.dockerignore` —— 未读。**因此不能断言 CI 里没有额外校验步骤。**
- `docs/frontend-handoff/`（3 个文件）—— 未读。
- `data/dictionaries/cn_financial_sentiment.txt`（8818 行）与 `.xlsx` 源文件 —— 未读内容，只从 `build_sentiment_dictionary.py` 的注释与断言了解其规模。
- **Supabase 实际部署的库**：我只读了 migration SQL。实际线上表结构、是否有后续未入库的手工改动、是否有其他表，**不在代码仓库里，我无从知道**。
- **运行时行为**：除 §2.2 那一次 `metrics` 计算外，我没有真正跑过 downloader / parser / 完整 pipeline，也没有连过 CNINFO 或 AKShare。所有关于网络链路的描述都来自阅读代码，不是观察到的行为。
- **是否存在未提交的本地脚本 / notebook**：`git status` 在会话开始时是 clean，但我没有检查未跟踪文件之外的其他工作副本。
