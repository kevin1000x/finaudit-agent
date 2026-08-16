# cninfo 两仓库源码深读报告（subagent 独立上下文产出，2026-08-15）

**读到什么程度**（子 agent 自报）：

`cninfo-financial-analyzer`：`text_analyzer.py` 全文 1-444、`pdf_parser.py` 全文 1-583、
`api/runner.py` 全文 1-341、`pipeline.py` 全文 1-1315、`config.yaml` 全文、
`data/dictionaries/NOTICE.md` + `LICENSE` 全文、`tests/test_text_analyzer.py` 全文、
`test_pdf_parser.py` 40-189 精读、`docs/superpowers/plans/` 唯一一份计划全文 455 行、
`CLAUDE.md` / `docs/frontend-handoff/README.md` / `requirements.txt` / git log 25 条。

`cninfo-analyzer-web`：`StreamView.tsx` / `ResultCard.tsx` / `JobForm.tsx` / `api.ts` /
`types.ts` / `jobStore.ts` / `App.tsx` / `functions/api/proxy/[[path]].ts` /
`lib/financialData.ts` / `package.json` / `vite.config.ts` / `README.md` **均全文**。

**未读**：`downloader.py`、`metrics.py`、`utils.py`、`financial_data_sources.py`、
`supabase/`、`scripts/`；其余 6 个测试文件只读了函数名未读实现；
前端 `index.css` / `utils.ts` / `financialData.test.ts` / `main.tsx`。

> 已派续读任务（补测试实现、`metrics.py`、`utils.py`、`supabase/`、`scripts/`，
> 并追问 pipeline 有无勾稽校验），**因 API session limit 中断，未完成**。

---

## ⚠️ 最高优先级：PyMuPDF 是 AGPL v3

> **【事后批注，非子 agent 原文】2026-08-16 已裁决：D-014 选「换 pdfplumber」，
> PyMuPDF 禁入本仓库。本节以下内容保持原样，作为该决策的证据来源。**
> 本报告中一切「用 PyMuPDF 做全文定位」的技术建议**均已作废**，见 D-014 与台账 A-4。

`LICENSE` 第三方段第 3 条 + `requirements.txt` 的 `PyMuPDF>=1.23.0`。
cninfo 自己的 LICENSE 就写了「AGPL requires source disclosure for network services」。

**finaudit-agent 的 Web 演示是网络服务，链接 AGPL 组件要么开源整个服务、要么买商业授权
——这与 D-005「主仓私有到 Phase 4」直接冲突。**

而我 2026-08-15 的 PDF 探测**全程用的 fitz（PyMuPDF）**。
替代：pdfplumber（MIT）、pypdfium2（BSD/Apache）无此约束。
**这是写抽取器之前要定的事，不是之后。** 已记入 `OPEN-ITEMS.md` A-3。

---

## 1. Fog 指数（Phase 0）：当参考实现移植，不要当库 import

**入口** `text_analyzer.py:265` `calculate_fog_index(text) -> Dict`，
公式 `:309` = `0.4 * (avg_sentence_length + complex_word_pct)`。

**中文适配三件事**：`split_sentences:216`（`[。！？；…\n]+`）、
`segment_text:130`（jieba + 停用词 + `len(w)>=2`）、
`is_complex_word:235`（汉字数 <= 2 判非复杂；有 common_vocab 则「不在表中即复杂」，
否则退化为「汉字数 > 3」）。

**已知局限（按严重度）**：

1. **`common_vocab.txt` 根本不存在。** `config.yaml:73` 指向它，但 `.gitignore:77`
   忽略 `data/dictionaries/*` 且只白名单 3 个文件。任何 checkout 里 `common_vocab`
   都是空集，`is_complex_word` **静默降级**成「汉字数 > 3」。
   **该仓库产出的所有 Fog 值都是字数阈值变体，不是词表变体。** 唯一信号是 `:61` 一行 warning。
2. `stopwords.txt` 同样不存在（`config.yaml:64`），`remove_stopwords: true` 是空操作。
3. **`\n` 是分句符。** PDF 抽出的文本每 ~40 字一个硬换行，`sentence_count` 被灌爆、
   `avg_sentence_length` 塌陷。**对「Fog vs 非标审计意见」回归，这是最大的系统性偏误源。**
4. `min_word_length=2` 使词典里所有单字词永远匹配不上。
5. `_add_custom_financial_terms:117` 用 `jieba.add_word` 改**全局**词典，同进程多配置互相污染。
6. `analyze_text:377` 把异常吞成 `{'success': False}`，但 fog/tone 键**不存在**而非 None。
7. 空文本时 `:288-294` 返回的 dict 缺 `total_words` 键，形状与正常路径不一致。
8. 同一段文本分词两次（`:191` 与 `:297`），年报级文本 jieba 成本翻倍。

**移植时必改四点**：换行不作分句符；显式提供并版本化 common_vocab，**缺失时报错而非降级**；
单次分词；把 Fog 的**配置指纹**（词表 hash、阈值、分句规则）写进每一行输出，否则数值不可复现。
`ChineseCommonVocabGenerator.generate_from_corpus:411` 可用于从语料自建词表。

## 2. 审计意见章节定位：复用 `extract_mda_section` 的四块模式

- **关键词按序试探** `pdf_parser.py:209`（词表在 `config.yaml:39-43`）
- **回退到行首** `:211` `text.rfind('\n', 0, match.start())` —— 锚到行边界使标题进入章节
- **章节末界** `_find_section_end:223`，边界正则
  `(?m)^\s*(?:第[一二三四五六七八九十百零〇两\d]+[章节][^\n]*|附件[^\n]*|财务报表[^\n]*)`，
  并跳过自身含关键词的候选标题
- **目录页排除** `_is_toc_like_line:240` 匹配 `[\.．·•…]{4,}\s*\d+\s*$`（点引导线+页码）；
  `_looks_like_table_of_contents:250` 取前 8 个非空行，命中 ≥ max(2, n/2) 即判目录

**适配审计意见**：
- 关键词按特异度排序：`审计报告正文` / `无法表示意见` / `保留意见` / `否定意见` /
  `带强调事项段的无保留意见` / `关键审计事项` / `审计意见`
- 边界正则要换锚点——审计报告通常是「第X节 财务报告」下的**子节**，`第X章/节` 触发不到。
  现成的 `财务报表[^\n]*` 反而是好终止符；再补 `会计师事务所`、`合并资产负债表`
- **目录过滤器是最高价值的可复用件**：「审计报告」出现在每份年报目录里，
  不排除的话第一个匹配永远命中目录条目
- **绝对不要抄「找不到 → 返回全文」的兜底**（`:220-221`）。cninfo 自己的计划 Task 4
  已认定它是溯源 bug 并规定改成 `Optional[str]` 返回 `None`，**但代码没改**，
  旧测试还在断言旧行为。对审计意见分类器，「未找到」必须是独立且被记录的状态
- **值得抄下游护栏**：`pipeline.py:61` `select_analysis_text` 拒绝
  「像目录 / <500 字 / 占全文 <2%」的候选，并把
  `analysis_text_source ∈ {mda_text, full_text, ''}` 写进输出行（`pipeline.py:305`）。
  **「记录这个数字来自哪段文本」这条纪律正是可审计 Agent 的必需项**

## 3. PDF 抽取器该怎么建

**三条文本路径的实况**：
- pdfplumber `:81` 逐页 `extract_text()`，**无 layout 参数**，多栏与表格密集页会串行；异常吞成 `""`
- PyMuPDF `:107` `get_text()` 默认模式，同样吞异常
- OCR `:164` 触发条件是 `not text.strip()` 且 `use_ocr=True`，而 `config.yaml:33` 是 `false`
  —— **出厂配置下 OCR 是死代码**
- 选择逻辑 `:134` 字符串分派，`'both'` = pdfplumber，仅在**完全为空**时退 PyMuPDF

**取舍建议**：
1. 「空串才 fallback」粒度太粗。做**逐页**判定：某页 chars/page 低于阈值 → 该页走 OCR
2. cninfo 没有任何 pdfplumber vs PyMuPDF 的对比逻辑或测试，**给不了选型证据**。
   子 agent 判断：PyMuPDF 做快速全文（章节定位只需文本+偏移），
   pdfplumber 做数字（暴露 char 级 bbox，正是把数值绑到页码+坐标做证据链所需）
   —— **但受 §0 的 AGPL 约束限制，PyMuPDF 这条可能整个不能用**
3. **表格抽取基本不可用**：`extract_tables_pdfplumber:283` 全默认参数，
   `pd.DataFrame(table[1:], columns=table[0])` 假定第 0 行是表头 —— 跨页续表会把数字当表头。
   `identify_financial_statement:390` 在 `df.to_string()` 上做子串匹配；
   `extract_financial_statements:413` 同类型**只保留最后一个匹配表**，且 if/elif 让多类型命中只归第一类。
   两个正向测试用的是手搓 2 行 DataFrame，**整个测试套件没有任何一个测试碰过真实 PDF**。
   结合 `pipeline.py:758` 硬写 `{}` —— **表格路径几乎肯定从未端到端跑通过，视为未验证代码**
4. **唯一有价值的设计**：`_page` / `_table_num` 两列，页码溯源活到了 DataFrame 里

**建 30 字段抽取器的路线**（不要基于 `extract_tables()` + 关键词分类）：
(a) 以**带「合并」限定词的标题文本**定位三张表，用锚点+页码区间，不用表内容子串；
(b) 只在该页码区间内抽表；(c) 行项目→字段用**人工维护的别名表**，不做模糊匹配；
(d) 每个字段保留 页码 + bbox + 原始单元格字符串；
(e) **用勾稽校验作准确率闸门**（资产=负债+所有者权益、期初+本期变动=期末、利润表逐级加总）
—— cninfo 完全没有这一层。

**章节定位的三个弱点**：边界正则只认 `第X章/节/附件/财务报表`，年报还大量用「一、」「（一）」
和裸标题；目录检测只看前 8 行；页眉页脚重复章节标题会产生伪匹配，而循环取第一个通过校验的、
**没有打分机制**。finaudit 要补：对所有候选打分（文档位置、候选长度、是否含预期兄弟短语）
取最优而非取首个，并记录候选的字符偏移区间。

## 4. 前端增量开发的接入点（具体到文件与行）

1. **`src/App.tsx`** —— **没有路由也没有路由抽象**：`:124-136` 直接条件渲染。
   最省的做法是加顶层 tab state（`'batch' | 'qa'`），不要为两个视图装 react-router。
   ⚠️ `:101-103` 的 `bootChecked` 门禁对**整个 app** 返回 `null`，QA 页要放在门禁之外
2. **新建 `QaPage.tsx` + `EvidenceCard.tsx`** —— `ResultCard` 是固定完成态横幅，不通用
3. **`src/lib/types.ts`** —— `JobEvent` 判别联合（`:5-16`）就是扩展点，
   `EventRow` 末尾 `return null`（StreamView `:192`）已优雅忽略未知类型
4. **`src/components/StreamView.tsx`** —— **两处必改**：
   (a) `es.addEventListener` 是**按事件名逐个注册**的（`:71-75`），
   **新事件名不加一行 addEventListener 就会被静默丢弃**（默认 `onmessage` 没接）；
   (b) `EventRow` 加分支。
   其余可原样复用：自动滚动 ref（`:89-92`）、只在 `readyState === CLOSED` 时报错的克制
   （`:77-83`）、用 duck-typing 区分原生 `error` 与服务端 `error` 的 `wrap()`（`:66-70`）
   —— 这三处是不显然的经验
5. **`src/lib/api.ts`** —— 加 `createQuestion()` / `qaStreamUrl()`；
   `ApiError:28` / `asJson:15` / `parseFilename:74` / `triggerDownload:80` 全可复用
6. **`functions/api/proxy/[[path]].ts`** —— **无需改动**。它是 catch-all，
   SSE 判定是 `upstreamPath.endsWith('/stream') || content-type 含 text/event-stream`（`:83-85`），
   所以**新流式路由命名以 `/stream` 结尾即可**。
   ⚠️ 非流式响应只透传 `Content-Type` 与 `Content-Disposition`（`:92-97`）
7. **`src/lib/jobStore.ts`** —— 单一硬编码 key，需泛化成 `save(key,id)`。
   **值得抄 App.tsx:30-65 的刷新恢复模式**：读 localStorage → 先 `GET /jobs/{id}` 验证
   后端还认得 → 失败静默丢弃 → 才挂 SSE。**「挂流前先验证」是关键**
8. **`vite.config.ts`** 无需改

### SSE 事件形状扩展（顺带要修的两个真 bug）

- **现有线格式** `{event, data, id: str(seq)}`（`api/main.py:260-286`）。
  `seq` 是**每连接**计数器；`:250-254` 的注释论证「history 第 k 项永远是 id k+1」
  —— **这只在没有淘汰时成立，而 `history` 是 `deque(maxlen=1000)`（runner `:35,:54`）。
  超过 1000 事件后每次重连 id 全体漂移，任何按 id 去重都会静默失效。**
  cninfo 自己的计划 Task 1 规定在 `_publish` 里分配 id —— 未实现。
  **推理流的事件密度远高于批处理日志，finaudit 必须在发布点分配 id**
- **前端去重也不存在**：`src/lib/sse.ts` 从未创建，StreamView 用本地 `seq.current++` 作 key。
  **今天刷新一次就把整段历史重新追加一遍**，做 token 流式后会立刻可见
- **值得保留的约定**：每个 payload 带 `type`；终止态 `done`/`error` 之后**另发一个 `eof`**，
  客户端据此 `es.close()`。这个三事件终止协议让客户端能区分「流正常结束」与「连接掉了」
- **不要继承的**：`done` 带 `result_path`、`error` 带 `trace`，
  `GET /jobs/{id}` 返回 `result_path` 且 ResultCard `:35` 把它渲染进 DOM
  —— **服务器文件系统路径进了浏览器**。计划 Task 2 规定改成 `result_ready: bool`，未实现
- **心跳** `ping=15` 是线级 SSE 注释，不进 history 不重放，`CLAUDE.md §1` 列为硬规则。
  **保留** —— 推理流的思考间隙比日志流更长
- **建议的 QA 事件集**：`status` / `step{id,label,state}` / `token{text}`
  （**客户端要做合批**，现在的 `setEvents(prev => [...prev, x])` 是每事件 O(n)，
  token 速率下会抖死）/ `evidence{claim_id, source:{doc,page,bbox,quote}}` / `answer` / `error` / `eof`

**可原样复用**：`cn()`、`ApiError`/`asJson`、下载两件套、`StatusDot`（StreamView `:124-139`）、
`Field`/`YearInput` 表单原语（JobForm `:230-270`）、`parseCodes` 股票代码校验（`:272-288`）。

## 5. 许可与合规（必须遵守）

- **情感词典**：姜富伟等(2020) 衍生版，**上游无 OSI 许可证**，条款是 README 的
  「在尊重知识产权的前提下…免费使用」，条件是**必须引用两篇**：
  Jiang, Lee, Martin & Zhou, "Manager Sentiment and Stock Returns", *JFE* 132(1) 2019, 126-149；
  姜富伟、孟令超、唐国豪《媒体文本情绪与股票回报预测》，《经济学(季刊)》2021 年第 4 期, 1323-1344。
  **两条引用必须出现在 README 与任何报告产出里。** 词量：3194 正 / 5621 负
- 上游无明确许可，「打包再分发」是 cninfo 自己的判断。finaudit 若公开，
  **把 NOTICE.md 原样带过去并保留 source xlsx** —— 这份纸面记录本身就是合规凭证
- cninfo 代码是 MIT，但版权人写的是占位符 `[Your Name]`
- **PyMuPDF AGPL v3**，见 §0。jieba/pdfplumber MIT，pandas BSD-3，aiohttp/requests Apache-2.0
- `camelot-py[cv]`、`tabula-py` 在 requirements 里但未用未测 —— 别继承
- **数据权利**：保留 `config.yaml:9` 的 `rate_limit: 2.0` 秒间隔、不转发 PDF 原件、
  只引用实际引证的 span
- **不要抄** `_load_cninfo_cookies`（runner `:163-201`）及整条 cookie 路径 ——
  下载链路本就不需要 cookies，登录态路径是纯合规负债

## 6. cninfo 自己踩过的坑（计划文档 455 行，所有 checkbox 仍是未完成）

1. **SSE id 从重放位置推导** —— 全局约束明写「never derived from a reconnect's replay position」，
   当前代码违反。教训：**id 在事件创建处分配**
2. **服务器路径与 traceback 泄漏到浏览器** —— 教训：脱敏属于 **API 契约层**而非 UI 层
3. **解析器溯源丢失** —— `extract_mda_section` 失败返回全文。
   教训：每个派生数字携带其来源 span 标识，**「未找到」是一等值**
4. **私有访问是事后才想起的** —— Pages secret 只让代理向 FastAPI 认证，
   **不授权浏览器用户**；`/api/proxy/*` 部署前需 Cloudflare Access + 限流。
   `docs/production-access.md` 不存在。**演示若公开，这是第一个要补的洞**
5. **单任务全局锁的真实原因是日志** —— loguru sink 挂在全局 root logger，
   并发任务日志互相穿插所以抛 429。**finaudit 若要并发，一开始就用 contextvar 作用域的 logger**
6. **result_path 必须绑到 job，不能扫盘** —— 他们被「取最新 xlsx」把 A 的产物绑给 B 坑过
7. **事件循环拆除竞态** —— `_enqueue` 有 `loop.is_closed()` 分支和裸 `except RuntimeError`；
   修复（先创建协程，异常路径 `coro.close()`）未实现。抄修复别抄 bug
8. **没有任何测试碰真实 PDF** —— 19 个解析器测试全是合成数据。
   **对 finaudit，一个小的固定语料（2-3 份真实年报 PDF 或页面切片）+ 30 字段的 golden 期望值，
   是最高价值的测试资产**
9. **配置指向不存在的文件** —— 教训：指标定义依赖数据文件时，**缺文件要响亮失败**，
   或把文件 hash 写进输出行
10. **保留策略是后补的** —— 三套独立的限量清理实现。若缓存 PDF，保留策略一次性设计好
11. **「断点续跑」有缺口** —— 靠分阶段 pickle（版本脆弱、不安全）；
    且**没有逐条 checkpoint**，`run_streaming` 在内存 list 累积，第 99/100 条崩溃则全丢
