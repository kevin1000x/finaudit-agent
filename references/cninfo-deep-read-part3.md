# cninfo 深读 第三轮（收尾）

读取日期：2026-08-16
目标仓库（本机，只读，**本轮未修改任何文件**，两个仓库 `git status` 均为 clean）：

- `C:\Users\Kevin\Desktop\excel\学校\求职\秋招\cninfo-financial-analyzer`（下称 **repo1**，HEAD `8e47956`）
- `C:\Users\Kevin\Desktop\excel\学校\求职\秋招\cninfo-analyzer-web`（下称 **repo2**）

---

## 0. 读到什么程度（逐文件自报）

### repo1 — 本轮任务清单内

| 文件 | 读到什么程度 |
|---|---|
| `README.md` | **读完**（1-472，全 472 行） |
| `PROJECT_SUMMARY.md` | **读完**（1-530，全 530 行） |
| `USAGE_GUIDE.md` | **读完**（1-610，全 610 行） |
| `INSTALLATION.md` | **读完**（1-541，全 541 行） |
| `api/main.py` | **读完**（1-318，全 318 行），含 `_validate_fin_csv` / `_validate_total_tasks` 实现体 |
| `api/runner.py` | 本轮读 **1-201** 与 **313-341**；202-312 为前两轮已读区间，本轮未重读 → **全文覆盖** |
| `src/pdf_parser.py` | 本轮读 **1-282**、**282-326**、**443-582**；327-442 为前两轮已读区间 → **全文覆盖**（并对全文做了针对性 grep，见 §3） |
| `examples/full_analysis_example.py` | **读完**（1-267，全 267 行） |
| `Dockerfile` | **读完**（57 行） |
| `docker-compose.yml` | **读完**（35 行） |
| `Makefile` | **读完**（111 行） |
| `setup.py` | **读完**（105 行） |
| `mypy.ini` | **读完**（10 行） |
| `.gitignore` | **读完**（129 行） |
| `.dockerignore` | **读完**（60 行） |
| CI 配置 | **文件不存在**（枚举证据见 §2） |
| `docs/frontend-handoff/README.md` | **读完**（56 行） |
| `docs/frontend-handoff/pages-function-proxy.ts` | **读完**（104 行） |
| `docs/frontend-handoff/vite-config.snippet.ts` | **读完**（32 行） |
| `data/dictionaries/cn_financial_sentiment.txt` | **未逐行读**（8818 行）。做了格式剖面 + 计数 + 哈希，见 §4.8 |
| `data/dictionaries/NOTICE.md` | **读完**（57 行） |
| `data/dictionaries/source/中文金融情感词典_姜富伟等(2020).xlsx` | **未读内容**（二进制），只取 SHA-256 |

### repo1 — 清单外但本轮顺带读了（都与三个必答问题直接相关）

| 文件 | 读到什么程度 | 为什么读 |
|---|---|---|
| `CLAUDE.md` | **读完**（54 行） | 回答 Q1 需覆盖全部 8 份 md |
| `docs/superpowers/plans/2026-07-10-phase1-web-mvp-hardening.md` | **读完**（455 行） | **回答 Q2 的关键证据**：它逐字写明了要建 CI |
| `examples/company_list.csv` | **读完**（11 行） | 验证 `CLAUDE.md:47` 的断言 |
| `examples/financial_data.csv` | **读完**（13 行） | 同上 |
| `examples/cn_financial_sentiment.txt` | 计数 + 头 8 行（全 197 行） | `Makefile:70-76` 会把它拷进运行时词典目录 |
| `config.yaml` | **本轮只 grep 了 8 个键**（前两轮已读全文），用于核对文档声称的配置项 | 核对文档漂移 |
| `src/text_analyzer.py:44-65, 250-265` | **只读了这两段**（前两轮已读全文） | 核对 Fog 复杂词口径 |

### repo2

| 文件 | 读到什么程度 |
|---|---|
| `src/index.css` | **读完**（27 行） |
| `src/lib/utils.ts` | **读完**（7 行） |
| `src/lib/financialData.test.ts` | **读完**（18 行） |
| `src/main.tsx` | **读完**（10 行） |
| `package.json` `scripts` 段 | 只读了 11-17 行（全文为前两轮已读） |
| CI 配置 | **文件不存在**（`git ls-files` 全量枚举，见 §2） |
| `src/lib/sse.ts` | **文件不存在** |

---

## 1. Q1 —— 文档里有没有任何实证结论？

### 结论：**没有。8 份 md 我全部读完，其中没有任何一条关于公司或年报的实证结论。**
### **Phase 0 的定义不需要改。**

逐份出处：

| 文件 | 是否有实证结论 | 依据 |
|---|---|---|
| `README.md` | 无 | 方法论段 `README.md:225-268` 只给公式与文献引用，**无样本量、无时间窗、无任何结果数值**。输出格式段 `README.md:355-383` 是列名字典，无数据。 |
| `PROJECT_SUMMARY.md` | 无（但有一句伪实证声明，见下） | `PROJECT_SUMMARY.md:292-315` 表格里确有数值（`tone_raw 0.5758`、`fog_index 24.5`、`tni -0.3421`、`平安银行 2021`），但该表第三列表头就是「**示例**」(`:293`)，是 schema 说明的占位值。 |
| `USAGE_GUIDE.md` | 无 | 所有统计输出都是 f-string 模板，值来自运行时变量：`USAGE_GUIDE.md:307-309`、`:434-436`。 |
| `INSTALLATION.md` | 无 | 全文为安装步骤与报错处置。 |
| `CLAUDE.md` | 无 | 全文为 api/ 层的约束条款。 |
| `NOTICE.md` | **有，且我复核通过** —— 但它是关于**词典数据本身**的，不是关于公司的 | 见下 |
| `docs/frontend-handoff/README.md` | 无 | 部署拓扑说明。 |
| `docs/superpowers/plans/2026-07-10-...md` | 无 | 全文 455 行为待办计划，每个 checkbox 都是未勾选的 `- [ ]`。 |

**一处必须警惕的伪实证声明：**

> `PROJECT_SUMMARY.md:328` —— 「已通过对中文财报的人工编码进行验证」

这句话在整个仓库里**没有任何支撑物**：没有样本量、没有编码手册、没有编码者间一致性指标、没有结果文件。
`data/results/` 只有一个 0 字节的 `.gitkeep`，且 `.gitignore:79` 明确排除 `data/results/**/*`，所以**任何运行产出都不可能在仓里**。
这是一句无证据的验证声明 —— 对 finaudit 而言这正是要在自己文档里禁止的句式。

**同类还有：** `USAGE_GUIDE.md:466` 用 `if analysis['tone_raw'] < -0.3` 作预警阈值，`-0.3` 在全仓无任何出处。

**唯一一类可核验的量化断言，是关于词典数据本身的，我实测复核通过：**

`NOTICE.md:19-23` 声称去重后 positive 3194 / negative 5621 / 合计 8815。实测：

```
wc -l  cn_financial_sentiment.txt      → 8818
grep -c "^POS:"                        → 3194
grep -c "^NEG:"                        → 5621
grep -c "^#"                           → 3
grep -vc "^POS:\|^NEG:\|^#"            → 0
```

3 + 3194 + 5621 = 8818 ✓。**这是全仓唯一一条"文档写了什么、我跑一条命令就能证伪"的量化断言。**
它的形态值得 finaudit 抄：断言 + 复现命令 + 可校验的分解数字。但它证明的是数据加工正确，不是任何财务/文本发现。

**`examples/full_analysis_example.py` 的补充证据：** 该脚本 `:143-204` 确实会打印 Tone/Fog/TNI 的 `describe()` 与 Top-5 榜单，`:199` 甚至定义了「高 TNI（>1.0）」的判读。**但仓库里没有任何一份这些输出的留档。** 也就是说：跑一次就能有实证结论，作者从没把结论写下来。

---

## 2. Q2 —— CI 里有没有任何额外的校验步骤？

### 结论：**两个仓库都没有任何 CI 配置文件。而且有正面证据表明 CI 是"写进计划但没建"。**

**我读/枚举了以下内容，其中没有 CI 配置：**

repo1，逐个 `ls` 确认不存在：`.github/`、`.gitlab-ci.yml`、`.circleci/`、`azure-pipelines.yml`、`.travis.yml`、`Jenkinsfile`、`.pre-commit-config.yaml`。
`git ls-files` 中全部点开头的受版本控制文件只有两个：`.dockerignore`、`.gitignore`。
`find` 全仓（排除 `.git`）的 `*.yml / *.yaml / *.toml / *.cfg / *.ini` 只有三个：`config.yaml`、`docker-compose.yml`、`mypy.ini` —— 三者都不是 CI。

repo2，`git ls-files` **全量 25 个文件**已完整枚举，无 `.github/`，无任何 workflow。

**正面证据（比"我没搜到"强得多）：**

1. `docs/superpowers/plans/2026-07-10-phase1-web-mvp-hardening.md:31` 与 `:41` 把 `Create .github/workflows/verify.yml` 列进两个仓库的交付物；`:386-424` 给出了逐字 YAML：

   - 后端 `backend-verify`：`actions/setup-python@v5` (3.12) → `pip install -r requirements.txt` → `python -m pytest tests -q`
   - 前端 `frontend-verify`：`actions/setup-node@v4` (node 24) → `npm ci` → `npm test` → `npm run lint` → `npm run build` → `npm audit --omit=dev --audit-level=high`

   **两个文件都不存在。计划里 Task 5 的 6 个 checkbox 全是未勾选状态。**

2. `.dockerignore:33-34` 写着 `# CI / Claude / agent artifacts` / `.github/` —— 排除一个不存在的目录。同段 `:25` 排除 `.pre-commit-config.yaml`、`:27` 排除 `.flake8`，两者同样不存在。**这三条是为尚未建立的基础设施预留的。**

3. `INSTALLATION.md:73-77` 指导贡献者执行 `pre-commit install`，但仓内无 `.pre-commit-config.yaml` —— 该命令会失败。`setup.py:85` 确实把 `pre-commit>=3.5.0` 装进 dev extras，只是没有配置文件。

**因此实际的"校验"只存在于本地手工命令**，全部集中在 `Makefile`：

- `Makefile:30-31` `test` → `pytest tests/ -v`
- `Makefile:36-38` `lint` → `flake8 src/ tests/` **且** `mypy --config-file mypy.ini src/`
- `Makefile:99-102` `check` → `make lint` + `make test`

**但 `mypy.ini` 的严格度接近于零**，`mypy.ini:6-10`：

```ini
allow_untyped_defs = True
ignore_missing_imports = True
follow_imports = silent
disable_error_code = import-untyped,var-annotated,assignment,return-value
```

关掉 `assignment` 与 `return-value` 之后，`make typecheck` 通过基本不构成任何保证。**不要把 cninfo 的 "make check 通过" 当成质量信号。**

---

## 3. Q3 —— `pdf_parser.py` 1-282 段的三条文本抽取路径

### 3.1 三条路径的入口 / 参数 / 异常处理

| | pdfplumber | PyMuPDF | OCR |
|---|---|---|---|
| 函数 | `extract_text_pdfplumber` `:81-105` | `extract_text_pymupdf` `:107-132` | `extract_text_ocr` `:164-196` |
| 打开 | `pdfplumber.open(pdf_path)` `:94`（`with` 上下文） | `fitz.open(pdf_path)` `:120`，手动 `doc.close()` `:126` | `convert_from_path(pdf_path)` `:179` |
| 逐页调用 | `page.extract_text()` `:96` | `page.get_text()` `:124` | `pytesseract.image_to_string(image, lang=...)` `:183-186` |
| **传了什么参数** | **一个都没传** | **一个都没传** | 只传 `lang`（默认 `chi_sim`，`:185`） |
| 拼接 | `text += page_text + "\n\n"` `:98`，且有 `if page_text:` 空页守卫 `:97` | `text += page.get_text() + "\n\n"` `:124`，**无空页守卫** | `text += ... + "\n\n"` `:186` |
| 异常处理 | `except Exception as e:` `:102` → `logger.error` → **落到 `:105` 返回已累积的 `text`** | `:129-130` 同构 | `except ImportError` `:191` → 返回 `""`；`except Exception` `:194` → 返回 `""` |

**三条路径的异常处理都是"吞掉并返回部分结果"，没有一条会抛。**
最危险的是 pdfplumber 与 PyMuPDF：假如在第 300 页抛异常，函数返回前 299 页的文本，**调用方拿到的是一份被静默截断的年报，与"这份年报本来就短"在类型上完全不可区分**。上层 `parse_pdf` `:487-489` 也只是把异常记进 `result['error']`，而下游的文本长度门禁 `analysis.min_text_chars`（`README.md:174`）只能挡住"几乎全空"，挡不住"截断了 40%"。

**调度逻辑** `extract_text` `:134-162`：

- `:144-155` 按 `pdf_engine` 选路；未知值 → 警告后退回 pdfplumber `:154-155`
- `'both'` 模式 `:148-152`：**只在 `if not text:` 即完全空串时才切 PyMuPDF**。半残、乱码、只抽出目录都不会触发回退。
- OCR 回退 `:157-160`：条件是 `not text.strip() and self.use_ocr`，同样只在全空时触发。
- `config.yaml:145-149`（据 `README.md:145-149`）默认 `pdf_engine: "pdfplumber"`、`use_ocr: false` → **默认配置下 PyMuPDF 与 OCR 两条路径根本不会被走到**。

（顺带：`README.md:441` 与 `PROJECT_SUMMARY.md:521` 自己就标注了 `PyMuPDF：AGPL v3`。cninfo 是 MIT 仓，仍在 `pdf_parser.py:17` 顶层无条件 `import fitz`，`setup.py:44` 把它列进核心 `install_requires` —— 这就是 **D-014 要避开的那条线**，而且 cninfo 已经踩上去了：一个 MIT 声明的包，核心依赖一个 AGPL 库，且是顶层导入不是可选导入。）

### 3.2 有没有传 `layout` / `x_tolerance` / `y_tolerance`？

**没有。一个都没传。**

我对全文（582 行）做了针对性 grep，模式包含 `layout|x_tolerance|y_tolerance|table_settings|dedupe_chars|.crop|within_bbox|edges|.rects|.lines|.curves`：

**零命中。**

`page.extract_text()` `:96` 与 `page.extract_tables()` `:298` 都是零参数调用，全部走 pdfplumber 默认值。

### 3.3 有没有用到 `extract_words()` 或 char 级 bbox？

**没有。** 同一次 grep 中 `extract_words|extract_text_lines|\.chars|bbox|word_` **零命中**。

整个仓库对 PDF 的认知粒度只有两级：**整页纯文本字符串**，和 **pdfplumber 自己吐出来的 `list[list[str]]` 表格**。中间那层（word / char + 坐标）从未被触碰。

### 3.4 页码是怎么跟抽出的文本关联的？

**文本路径：根本没关联。** `:95-98` 把所有页拼成一个字符串，只留 `"\n\n"` 分隔符，**没有页码标记、没有偏移量表、没有任何可回溯的锚点**。`save_parsed_data:508-515` 落盘的 `full_text.txt` / `mda_text.txt` 也只是这个裸字符串。

→ **cninfo 的 tone / fog / TNI 全部计算于一个丢失了页码的字符串上。任何指标都无法回指到「第几页」。** 对 finaudit 而言这就是 D-003「证据链是第一类产物」的反例：这套流水线**在结构上**就不可能产出可复核的证据链，不是没做，是做不了。

**表格路径：有关联，但很脆。** `extract_tables_pdfplumber:296-305`：

```python
for page_num, page in enumerate(pdf.pages):
    page_tables = page.extract_tables()
    for table_num, table in enumerate(page_tables):
        if table:
            df = pd.DataFrame(table[1:], columns=table[0])   # :302
            df['_page'] = page_num + 1                        # :303
            df['_table_num'] = table_num + 1                  # :304
```

`_page` / `_table_num` 是全仓唯一的位置信息。但 `:302` 这一行是硬伤，见下。

### 3.5 cninfo 有没有碰到你实测的那三个失效模式？—— 逐条对照

| 你的失效模式 | cninfo 有没有处理 | 依据 |
|---|---|---|
| **① 长标签折行导致数值自成一行** | **完全没有处理，而且看不见这个问题。** | 折行是 `extract_text()` 的行合并行为决定的，只能靠 `x_tolerance` / `y_tolerance` / `layout=True` 或 `extract_words()` 自行重组行来干预 —— 这些 cninfo 一个都没用（§3.2/§3.3）。表格侧 `:298` 同样零参数，`table_settings` 从未出现。整个仓库没有任何一处代码试图把"标签行 + 孤立数值行"重新配对。 |
| **② 附注编号列被当成数值** | **没有处理。** | `pd.DataFrame(table[1:], columns=table[0])` `:302` 之后没有任何列类型推断、没有列语义识别、没有把"附注/注释"列剔除的逻辑。`identify_financial_statement` / `extract_financial_statements`（327-442，前两轮已读区间）是按**关键词匹配表格文本**来给整张表打标签的，不做列级语义。落盘 `:520` 直接 `to_csv`，附注编号列原样带走。 |
| **③ 续页不重复表头** | **没有处理，且 `:302` 会把这个问题放大成静默的数据损坏。** | `pd.DataFrame(table[1:], columns=table[0])` **无条件把每张表的第 0 行当表头**。续页表格的第 0 行是**数据行**，于是一行真实财务数据被提升为列名并从数据中消失。既没有 `len(table) > 1` 守卫，也没有跨页表头继承，更没有列名去重（合并单元格常产出 `None` 列名，pandas 会得到重复/空列名）。`PROJECT_SUMMARY.md:141` 却宣称「支持跨页表格识别」—— **这句在代码里没有对应实现**。 |

**给 finaudit 的直接结论：这三个失效模式，cninfo 一个都没解决，而且它的架构（零参数 `extract_text` + 无 bbox + 无页码）决定了它连观察到这些问题的手段都没有。不要指望从 cninfo 抄到任何解法；它是这三个坑的一个完整反面样本。**

---

## 4. 逐文件发现（本轮新读部分）

### 4.1 `api/main.py`（全 318 行）

**`_validate_fin_csv` 实现体 `:131-148`** —— 这是全仓质量最高的一段代码，值得直接借鉴：

```python
candidate = Path(v)
if candidate.is_absolute():                                      # :137
    raise ValueError("financial_data_csv must be a relative path")
cwd = Path.cwd().resolve()
resolved = (cwd / candidate).resolve()                           # :140  ← resolve 后再比
allowed_roots = [(cwd / root).resolve() for root in ALLOWED_FIN_CSV_ROOTS]
if not any(_is_within(resolved, root) for root in allowed_roots): # :142
    raise ValueError(...)
if not resolved.exists():                                        # :146
    raise ValueError(f"financial_data_csv not found: {v}")
return str(resolved)                                             # :148  ← 返回规范化后的绝对路径
```

四层门禁：**拒绝绝对路径 → `.resolve()` 之后再做前缀比较（这是防 `../` 穿越的正确写法，字符串 `startswith` 是错的）→ 白名单根目录（`ALLOWED_FIN_CSV_ROOTS = ("examples","data")`，`:50`）→ 存在性检查**。`_is_within` `:170-175` 用 `Path.relative_to` + `except ValueError` 实现，比手写字符串比较可靠。
最后一步 `:148` 返回 `str(resolved)` 而不是原始输入 —— **校验器同时是规范化器**，下游拿到的一定是已验证的绝对路径，不可能再被重新解释。

**`_validate_total_tasks` 实现体 `:160-167`** —— `@model_validator(mode="after")`，检查的是**笛卡尔积**：

```python
total = len(self.company_codes) * len(self.years) * len(self.report_types)
if total > MAX_TASKS:   # MAX_TASKS = 100，:49
```

关键在于：字段级上限已经有了（`:92` codes ≤100、`:93` years ≤20），但 100×20×3 = 6000 个任务全部合法。**只有乘积门禁能挡住这个**。这是"字段级校验 ≠ 组合级校验"的干净示例，finaudit 的批量提问接口会遇到同型问题。

其余：
- `:87-88` `_max_year()` 返回 `当前 UTC 年 + 1`，**每次请求现算**，不是模块常量 → 跨年不需要改代码。
- `:76-84` `require_token` 在**请求时**读 `os.environ`（注释 `:76-77` 明说是为了让测试 `monkeypatch.setenv` 生效）。副作用：`API_TOKEN` 为空 = 匿名放行 `:79-80`，**部署时漏设环境变量就是全开**，fail-open。finaudit 若做类似门禁应选 fail-closed。
- `:243-255` SSE 的 `snapshot = list(job.history)` 与 `subscribe(job)` 之间**刻意不放 `await`**，注释 `:243-245` 解释了原因（单线程事件循环内这两行原子）。这是一个真实并发 bug 的修复痕迹，思路可借鉴。
- `:249-254` 注释声称 id 编号「跨重连确定性：history 第 k 项永远带 id k+1」。**但 `seq` 是 per-stream 变量（`:255` `seq = 0`），一旦 `history` 触及 `HISTORY_CAP=1000`（`runner.py:35`）发生 deque 淘汰，同一条事件在重连后会拿到更小的 id。注释与实现不符。** 详见 §4.4。

### 4.2 `api/runner.py` 1-201

- `JobRegistry` `:71-105`：`threading.Lock` 保护的**单任务**注册表，`reserve` `:79-88` 在有活跃任务时抛 `JobAlreadyRunning`。模块 docstring `:5-8` 给了非常好的理由：**loguru sink 挂在全局 root logger 上，并发任务会互相污染日志**。这是"可观测性约束反过来限定了并发模型"的例子。
- `:12-15` docstring：`result_path` 取自 `pipeline.last_output_file`，**而不是扫描 `data/results/` 取最新 xlsx** —— 后者在任务背靠背时会把 A 的产物绑给 B。这个坑 finaudit 做产物落盘时一定会遇到。
- `_publish` `:115-129`：队列满时**丢最老的一条再塞新的** `:122-127`。即在压力下**静默丢日志**，且不留任何"这里丢过东西"的标记。对证据链场景是不可接受的策略。
- `_load_cninfo_cookies` `:163-199`：docstring `:171-172` 明确写了「cookie 值绝不可被 log / 返回 / 回显，只能提及来源路径与键数量」，实现 `:186` / `:198` 只 log `len(cookies)`。**这条纪律值得逐字抄进 finaudit。**
- `:182` / `:193` 只取 `exc.msg` 而丢弃 `exc.pos`/`exc.doc`，避免把文件内容片段带进异常信息 —— 细节到位。

### 4.3 `api/runner.py` 313-341

- `:316` `import api.runner as _self` 后用 `_self.run_job` 起线程，注释 `:314-315` 说明是为了让测试能 monkeypatch（闭包捕获会绕过 patch）。小技巧，可用。
- `:317-322` worker 是 `daemon=True` 线程 → **进程退出不等任务结束**。配合 `JobRegistry` 的「进程内存态、重启即丢」（`:72` docstring），意味着**没有任何任务是持久的**。

### 4.4 三条已写进计划但**没有实现**的事项（重要）

`docs/superpowers/plans/2026-07-10-phase1-web-mvp-hardening.md` 与实际代码的差异，我逐条用 grep 核实：

| 计划条目 | 计划出处 | 实际状态 | 核实方式 |
|---|---|---|---|
| SSE 事件 id 用 job 级 `EventEnvelope`，**明确禁止 per-connection 计数器**（`:124` 原文：Do not calculate IDs from `enumerate()` or a per-connection counter） | Task 1 `:77-124` | **未实现，且落地的正是被禁止的那个方案** —— `main.py:255` `seq = 0` 是 per-stream 计数器 | 全仓 grep `EventEnvelope|next_event_id` → **零命中** |
| 读取 `Last-Event-ID` 请求头做增量重放 | Task 1 `:105-122` | **未实现**，每次重连仍全量重放 | 全仓 grep `Last-Event-ID\|last_event_id` → 仅 `main.py:251` **一条注释**命中，无代码 |
| `GET /jobs/{id}` 用 `result_ready: bool` 替换 `result_path`，不向浏览器暴露服务器路径 | Task 2 `:173`, `:199` | **未实现** —— `main.py:226` 仍返回 `"result_path": job.result_path` | grep `result_ready` → **零命中** |
| `extract_mda_section` 改返回 `Optional[str]`，找不到时返回 `None` | Task 4 `:315`, `:338-342` | **未实现** —— `pdf_parser.py:220-221` 仍 `logger.warning(...); return text` | 直读源码 |
| `docs/production-access.md` | Task 5 `:366` | **文件不存在** | `ls` |
| 两个仓库的 `.github/workflows/verify.yml` | Task 5 `:386-424` | **文件都不存在** | 见 §2 |
| repo2 `src/lib/sse.ts` + `sse.test.ts` | Task 3 `:243-244` | **文件不存在** | `ls` |
| repo2 `package.json` 加 `"test": "vitest run"` | Task 3 `:258` | **已实现** —— `package.json:15` | 直读 |

**给 finaudit 的教训（这条比任何代码借鉴都重要）：**
这份计划写得极好 —— 有 Interfaces 契约、有 TDD 步骤、有逐条验证命令、有 Self-Review。**然后 8 项里落地了 1 项，而落地的那 1 项还只是最便宜的一步。** 更糟的是 Task 1 交付了计划里**被显式禁止的实现**（git log `8e47956` "Stamp SSE events with monotonic ids…" 听起来像做完了），文档端却留下了 `main.py:249-254` 那段自信的注释来描述一个不成立的性质。

→ **计划质量与落地率无关；"计划里写了" 与 "代码里有" 必须分开记账。** 这正是 `rules/failure-modes.md` 里那条规则的外部实证。finaudit 的 `OPEN-ITEMS.md` 判据栏要按这个标准审。

### 4.5 `Dockerfile` / `docker-compose.yml`

`Dockerfile` 质量不错：
- `:24-30` 系统依赖逐行注释了「为什么装」（tesseract→OCR、ghostscript+poppler→camelot、libgl1→opencv）。
- `:33-34` requirements 先 COPY 再 install，源码后 COPY → 依赖层缓存。
- `:37-41` **只 COPY 运行时需要的 5 项**，tests/docs/scripts 不进镜像。
- `:47-48` 建 uid 1000 用户并 `chown`，非 root 运行。
- `:56` 注释点明 `--host 0.0.0.0` 而非 `127.0.0.1` 的原因。

`docker-compose.yml` 明显是**旧的、没跟上的**：
- `:8-13` 只挂卷，**没有 `ports` 映射** → `Dockerfile:57` 里跑在 7860 的 uvicorn 通过 compose 起来后**从宿主机根本访问不到**。两份文件不是同一时期的产物。
- `:21-32` 一个 `postgres:15-alpine` 服务，**硬编码 `finuser` / `finpass`**，且 `:31-32` 把 5432 暴露到宿主机。而全仓没有任何代码连它（`setup.py:37-59` 无 sqlalchemy / psycopg）。**死服务 + 硬编码口令 + 端口暴露**，在一个 PUBLIC 仓里。
- `:1` `version: '3.8'` 是已废弃字段。

→ finaudit 若做 compose：**任何示例凭据都不写进版本控制**，哪怕是给死服务用的。

### 4.6 `setup.py` / `mypy.ini` / `Makefile`

- **三处 Python 版本互相打架**：`setup.py:36` `python_requires='>=3.8'`；`mypy.ini:2` `python_version = 3.11`；`Dockerfile:13` `python:3.12-slim`。没有单一事实源。
- `setup.py:41-42` 精确钉死 `akshare==1.18.64`、`supabase==2.31.0`（其余全是 `>=`）。但 **`INSTALLATION.md:282-315` 的依赖清单里 akshare 和 supabase 一个都没提** —— 文档漂移。
- `Makefile:70-76` `setup-dict` **在 `data/dictionaries/cn_financial_sentiment.txt` 不存在时，把 `examples/cn_financial_sentiment.txt` 拷过去**。而后者是个 **166 词的桩**（76 POS + 90 NEG，197 行），前者是 **8815 词的真词典**。`README.md:35` 警告过「缺失或替换会导致 tone 数值不可比」，**而 `make init`（`:104`）本身就是那个替换机制**，且替换后无任何警告。
  → **同一个字段名（tone）背后可以是两套完全不同的口径，切换发生在构建脚本里，运行时完全静默。** 这是 finaudit 「口径可证明」命题的教科书级反面案例。

### 4.7 文档 vs 代码/配置的漂移清单（逐条已核实）

| 文档声称 | 出处 | 实际 | 核实 |
|---|---|---|---|
| 复杂词 = 字符数 > 2 **且** 不在常用词表中 | `README.md:248`、`PROJECT_SUMMARY.md:169-172` | **常用词表文件不存在** → `text_analyzer.py:258` 的 `if self.common_vocab:` 为假 → `:263` `return char_count > 3`。**实际口径是「>3 字符」，且完全不查词表** | `config.yaml:73` 指向 `data/dictionaries/common_vocab.txt`；`ls` 该文件不存在；`git ls-files \| grep vocab` 零命中。仅 `text_analyzer.py:61` 打一条 warning |
| `parser: batch_size: 5` 可控制分批 | `INSTALLATION.md:365-366` | `config.yaml` 无 `batch_size` 键，代码无读取 | grep 零命中 |
| 支持跨页表格识别 | `PROJECT_SUMMARY.md:141` | 无任何实现，`pdf_parser.py:302` 反而每页独立取表头 | 见 §3.5 |
| 词典由「姜富伟团队扩展（**2016**）」 | `PROJECT_SUMMARY.md:326`,`:349`；`README.md:238`；`examples/cn_financial_sentiment.txt:3` | `NOTICE.md:5-8` 与 `README.md:29-30` 说是 **2020**，而 `README.md:37-38` 要求引的两篇是 **2019** (JFE) 与 **2021**（经济学季刊）。**同一件东西挂了三个年份** | 直读 |
| 财务 CSV schema `stock_code,year,ROA,operating_cash_flow` | `README.md:205` | 实际文件表头是 `stock_code,year,roa,roe,operating_cash_flow,total_assets,net_profit`（**小写 roa**，且多 4 列） | 直读 `examples/financial_data.csv:1` |
| 代码规模约 2,800 行；`pdf_parser.py` 约 370 行 | `PROJECT_SUMMARY.md:36`,`:61` | `pdf_parser.py` 实际 582 行；`AGENTS.md` 记录全仓 8310 行 | `wc -l` |
| 运行 `pre-commit install` | `INSTALLATION.md:76` | 无 `.pre-commit-config.yaml`，命令会失败 | `ls` |

**`README.md` 里还有一处应引以为戒的引用**：`:256` 把 Fog 指数中文适配的依据写成「多篇 CSDN / 学术博客讨论中文文本复杂性的做法」。**一个准则口径的依据是博客。** finaudit 的口径来源必须是准则条文号，这条对比可以直接写进 PROJECT_SPEC 的动机段。

### 4.8 `data/dictionaries/` 内容概况

**格式**（`cn_financial_sentiment.txt`，8818 行，UTF-8，无 BOM）：

```
# Chinese financial sentiment dictionary (POS:/NEG: format)      ← 3 行注释
# Source: Jiang Fuwei et al. (2020), see data/dictionaries/NOTICE.md
# Generated by scripts/build_sentiment_dictionary.py — do not edit by hand
POS:安定
...
NEG:哀悼
```

- **一行一词，`POS:` / `NEG:` 前缀，无权重、无词性、无强度、无领域标注。** 全文唯一含两个冒号的行是第 1 行注释本身（grep 确认）。
- 计数：3 注释 + 3194 POS + 5621 NEG = 8818 ✓，与 `NOTICE.md:19-23` 完全一致。
- 负面词是正面词的 **1.76 倍** —— 直接影响 `Tone = (P-N)/(P+N)` 的中心位置。README 与 NOTICE 都没有讨论这个不对称性对指标零点的影响。
- SHA-256（本轮实测，可作冻结基线）：
  - `cn_financial_sentiment.txt` = `d6b4d65d540dbbdf07d2a4d8e6daab1189bfc0a9702e60db11c420361dc9c4e7`
  - `source/中文金融情感词典_姜富伟等(2020).xlsx` = `0d2078ff28d2d38d3784a1c791c7efd220b5d9c40b46b2e358c0e6323ee384e4`

**来源标注：** `NOTICE.md` 做得很规范 —— 上游 URL `:8`、源文件字节级保留声明 `:10-12`、转换脚本 `:14-15`、去重前后计数表 `:19-23`、并解释了 xlsx 内部有重复（positive ~144 / negative ~269）`:25-27`、以及为什么打包而不是运行时下载 `:52-57`。

**是否可商用：不能确定可以，应按"不可"处理。**
`NOTICE.md:42-47` 原文说明：上游仓库**没有声明任何 OSI 许可证**，README 只写了「在尊重知识产权的前提下，读者可以免费使用该词典」，并要求引用两篇文献。`:49-50` 自述「仅为研究与演示用途打包」。
→ **没有明确的商用授权，也没有明确的再分发授权。** finaudit 若要用这份词典，只能限定在研究/演示，且必须带 `NOTICE.md:34-38` 的两条引用；**任何走向商业化的路径都需要先回上游确认，不能默认 MIT 传染。**（repo1 自身 LICENSE 是 MIT，但那覆盖的是代码，不是这份数据 —— `README.md:443` 自己也把词典单列为「学术使用」。）

### 4.9 `docs/frontend-handoff/` 三件

- `README.md:17-31` 一张 ASCII 图把 dev / prod 两条链路并排画出来，点明**浏览器侧 URL 在两个环境完全一致**（`:33-34`），所以 React 代码不需要 env 分支。**这个"用代理抹平环境差异，而不是在前端写 if"的做法，finaudit 的 Web 演示可以直接照搬。**
- `pages-function-proxy.ts:37-46` 显式列出 hop-by-hop 头黑名单并逐个剔除 `:63-68`，同时**丢弃客户端的 `authorization` 和 `cookie`** 后再注入服务端 token `:69` —— 即客户端无法通过伪造头影响上游。
- `:82-91` SSE 直通 `new Response(upstream.body, ...)`，绝不 `await .text()`；并设 `X-Accel-Buffering: no`。
- `README.md:44-46`：`API_BASE` **必须是 named tunnel，quick tunnel 不支持 SSE**。这是踩过坑才写得出的一句。
- `README.md:48-56` 「What's intentionally not here」段说明了为什么不预生成 `package.json` / React 组件 —— **交接文档显式声明边界**，值得学。

### 4.10 repo2 剩余 4 个文件

- `index.css` 27 行，`:5` `color-scheme: light dark` + `:17-23` `prefers-color-scheme` 媒体查询，**没有主题切换开关，也没有 `data-theme`**，纯跟随系统。
- `utils.ts` 7 行，标准 shadcn `cn()`（`twMerge(clsx(...))`）。
- `financialData.test.ts` 18 行，**repo2 全仓唯一的测试**。两个用例，断言 `financialDataInput("akshare")` 不泄露 CSV 路径 `:5-10`、`"examples"` 保留显式本地源 `:12-17`。测试点选得好（**测的是"不该出现什么"**），但覆盖面就这两条。
- `main.tsx` 10 行，标准 `StrictMode` + `createRoot`。

### 4.11 `examples/` 数据文件

- `company_list.csv` 有 **10 家公司**，但 `financial_data.csv` 只覆盖 **4 家**（000001/000002/600000/600036）× 3 年 = 12 行。`CLAUDE.md:47` 对此有正确记录。
  → 按 `README.md:91` 的示例命令跑，是 10×3 = 30 个任务，其中 **18 个观测的 TNI 必然是 NaN**，而流水线不会因此报错。**"部分静默缺失"是 TNI 类衍生指标的默认结局。** finaudit 的指标层必须显式区分「算不出」与「算出来是 0」。
- `financial_data.csv` 的数值字段带**行尾空格**（`4200000000000 `），pandas 能吃，严格解析器不能。

---

## 5. 对 finaudit 的可借鉴点（只写有原文依据的）

1. **`_validate_fin_csv` 的四层路径门禁**（`api/main.py:131-148` + `:170-175`）：拒绝绝对路径 → `.resolve()` 后前缀比较 → 白名单根 → 存在性；**并返回规范化结果**。finaudit 任何"用户指定文件路径"的入口直接照抄这个形状。
2. **组合级上限校验**（`api/main.py:160-167`）：字段级 `max_length` 挡不住笛卡尔积爆炸，`@model_validator(mode="after")` 算乘积。finaudit 批量提问入口同型。
3. **秘密处理纪律的措辞**（`api/runner.py:171-172`）：「只能提及来源路径与键数量，值绝不可进入 log / 事件 / 响应」，且实现真的只 log `len()`（`:186`,`:198`）。这句可以逐字进 finaudit 的 rules。
4. **产物绑定用 `pipeline.last_output_file`，不扫目录取最新**（`api/runner.py:12-15` docstring 给出的理由：背靠背任务会错绑）。finaudit 的证据文件落盘会遇到完全相同的坑。
5. **并发模型由可观测性约束反推**（`api/runner.py:5-8`）：因为 loguru sink 是全局的，所以只能单任务。这个论证链条本身值得学 —— **先说清楚为什么不能并发，再限制并发**。
6. **`NOTICE.md` 的数据溯源模板**（`data/dictionaries/NOTICE.md` 全文）：上游 URL + 字节级保留声明 + 转换脚本 + 去重前后计数表 + 引用要求 + 许可分析 + 「为什么打包不是运行时下载」。finaudit 每一份外部语料/词表都应该有一份这个结构的 NOTICE，**再加上 SHA-256**（cninfo 缺这一项，我已在 §4.8 补出）。
7. **代理抹平环境差异**（`docs/frontend-handoff/README.md:17-34`）：dev 与 prod 浏览器侧 URL 完全一致，token 只在服务端注入。加上 `pages-function-proxy.ts:63-69` 丢弃客户端 `authorization`/`cookie` 再注入的写法。
8. **SSE 快照与订阅之间不放 `await`**（`api/main.py:243-248`）以避免丢事件 —— 若 finaudit 要做流式输出，这是必踩的坑。
9. **交接文档显式声明"故意没放什么"**（`docs/frontend-handoff/README.md:48-56`）。

## 6. 必须避开的坑（只写有原文依据的）

1. **不要建一个丢失页码的文本层。** `pdf_parser.py:95-98` 把全篇拼成裸字符串，导致 cninfo **在结构上不可能**提供页级证据链。finaudit 的抽取层从第一行代码起就必须携带 `(page, bbox)`。
2. **不要零参数调 `extract_text()` / `extract_tables()`。** `:96` / `:298` 全默认，是你实测的三个失效模式全部无解的根因。
3. **不要 `pd.DataFrame(table[1:], columns=table[0])`。** `:302` 无条件把第 0 行当表头，续页表格会**静默吃掉一行真实数据**，同时可能产出重复/`None` 列名。至少要有 `len(table)>1` 守卫、跨页表头继承、列名去重。
4. **不要让"文档口径"和"运行口径"能悄悄分叉。** 复杂词定义文档写 ">2 且不在常用表"（`README.md:248`），实际因常用表文件不存在而变成 ">3 且不查表"（`text_analyzer.py:258-263`），代价只有一行 warning（`:61`）。finaudit 应做成 **fail-closed**：口径依赖的资源缺失就拒绝出数，不许降级。
5. **不要让构建脚本能替换指标口径。** `Makefile:70-76` 会用 166 词的桩替换 8815 词的真词典，静默改变 tone 的可比性，而 `README.md:35` 恰恰警告过这件事。
6. **不要 fail-open 的鉴权。** `api/main.py:78-80`：`API_TOKEN` 未设 = 全放行。漏配环境变量就是敞开。
7. **不要在压力下静默丢事件。** `api/runner.py:122-127` 队列满时丢最老一条，不留痕。证据链场景必须留"此处有丢弃"的标记。
8. **不要把示例凭据写进版本控制。** `docker-compose.yml:26-28` 的 `finuser/finpass` + `:31-32` 端口暴露，服务本身还是死的。
9. **不要在 MIT 仓里顶层无条件 import AGPL 库。** `pdf_parser.py:17` `import fitz` + `setup.py:44` 核心依赖，而 `README.md:441` 自己标注了 AGPL v3。**D-014 只用 pdfplumber 的决定，被 cninfo 反面证实是对的。**
10. **不要把"计划写了"当成"做了"。** §4.4 那张表：8 项计划，落地 1 项，且 Task 1 交付的是计划里被显式禁止的方案，同时留下了一段描述不成立性质的自信注释（`api/main.py:249-254`）。
11. **不要写没有支撑物的验证声明。** `PROJECT_SUMMARY.md:328`「已通过人工编码验证」，全仓零证据。
12. **不要拿博客当口径依据。** `README.md:256`。
13. **不要相信 cninfo 的 `make check` 是质量信号。** `mypy.ini:6-10` 关掉了 `assignment`/`return-value` 并允许 untyped defs。
14. **衍生指标要显式区分「算不出」与「0」。** 例子见 §4.11：示例数据跑一遍，18/30 观测的 TNI 静默为 NaN。

---

## 7. 我没读，因此不能置评的清单

**repo1：**
- `data/dictionaries/cn_financial_sentiment.txt` 的 **8815 个词条内容本身**（只做了格式剖面与计数）—— 不能评价词表的语义质量、领域覆盖、是否含歧义词。
- `data/dictionaries/source/*.xlsx` 的**内部内容**（二进制，只取了哈希）—— 不能评价 sheet 结构、是否含额外列（如强度分）。
- `src/pdf_parser.py:327-442`、`api/runner.py:202-312`、以及 `downloader.py` / `pipeline.py` / `metrics.py` / `utils.py` / `text_analyzer.py` / `config.yaml` / `supabase/` / `scripts/` / 全部 8 个测试文件 —— **前两轮已读，本轮未重读**。本报告中凡引用这些文件的地方，都是本轮为核实某条断言而定点重读的片段（已在 §0 表中标明具体行号）。
- `logs/` 目录内容 —— 未查看。
- `requirements.txt` —— 前两轮已读，本轮只通过 `setup.py` 交叉比对，**没有逐行核对两份依赖清单是否一致**。

**repo2：**
- `package-lock.json`（124 KB）、`eslint.config.js`、`tsconfig.json` / `tsconfig.app.json` / `tsconfig.node.json`、`index.html`、`.node-version`、`LICENSE`、`.gitignore` —— **未读**。因此**不能对 repo2 的 lint 规则强度、TS 严格度（`strict` 是否开启）、依赖漏洞状况置评**。
- `README.md`（repo2）—— 前两轮已读，本轮未重读。

**天然不在代码仓库里、因此我无法对其置评的四类：**
- **部署配置** —— Cloudflare Pages / Access 策略、named tunnel 配置、HF Space 设置，仓内只有 `docs/frontend-handoff/README.md:36-46` 的操作说明，实际部署态不可见。
- **密钥** —— `API_TOKEN` / `CNINFO_COOKIES_*` / `SUPABASE_SERVICE_ROLE_KEY` 是否已配、配了什么值。
- **运行时环境** —— 是否真的跑起来过、跑在哪、Python 实际版本。
- **数据内容** —— `data/raw` / `data/parsed` / `data/results` 在本机全为空（只有 `.gitkeep`），且被 `.gitignore:76-81` 排除。**我无法判断作者在自己机器上是否跑出过结果；我只能说仓库里没有留档。** §1 中「没有实证结论」的断言，范围严格限于**已提交的文档与代码**。

**关于 GitHub 侧：**
我只检查了本机克隆。**GitHub 上的仓库设置（Actions 是否通过 UI 配置、branch protection、required checks、Dependabot）不在本机克隆内，我不能对其置评。** §2 的结论准确表述是：**两个仓库的工作副本中不存在任何 CI 配置文件**，且计划文档证明它们本应存在而未被创建。
