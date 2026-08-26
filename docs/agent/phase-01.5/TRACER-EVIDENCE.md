# Phase 1.5 tracer 切片 —— 逐条验收证据

> 格式按 `PROJECT_SPEC.md` §11：
> 验收标准 → 验证方法 → 实际命令 → 真实输出 → 证据位置 → PASS / FAIL / UNVERIFIED
>
> 记录于 2026-08-26。执行环境：`.venv`（Python 3.14.0），pdfplumber **0.11.10**。
> 样本：贵州茅台（600519）2023 年年度报告，143 页，
> SHA-256 `2125ff97a452ea79b0d784e2432f7d224b6aecc330b644b593477d69e22f4ed1`，
> 源 URL `https://static.cninfo.com.cn/finalpage/2024-04-03/1219506510.PDF`。

---

## 0. 一条路径的全貌

```text
巨潮 HTTP 三步链路 → PDF（SHA-256 绑定）→ 合并资产负债表锚点（p58, y=662.3）
→ 列绑定「2023年12月31日」= 期末余额 → 三条抽取记录（p59 / p60 / p61）
→ 批次级勾稽闸门（差额 0.00，通过）→ 封闭算术解析器
→ debt_to_asset_ratio = 0.1798…
```

**抽取路径与计算路径是同一条。** `compute_metric` 的唯一输入是 `extract_batch`
产出的那个批次对象，没有第二条路。这正是 cninfo 没做到的那一件事：
它的 `pipeline.py:758` 硬编码 `'financial_statements': {}`，计算侧从不读它。

---

## 1. 逐字段列出**取到的值**（SC-8：验收看取到的值，不看命中数）

| 字段 | 取到的值 | 报表列 | PDF 页 | 锚点页 | 人工核对结论 |
|---|---|---|---|---|---|
| `bs.total_assets` | `272,699,660,092.25` | 2023年12月31日 | 59 | 58 | **一致**。年报第 59 页（页脚印「59 / 143」）合并资产负债表「资产总计」行，期末列 |
| `bs.total_liabilities` | `49,043,190,797.43` | 2023年12月31日 | 60 | 58 | **一致**。第 60 页「负债合计」行，期末列 |
| `bs.total_equity` | `223,656,469,294.82` | 2023年12月31日 | 61 | 58 | **一致**。第 61 页「所有者权益（或股东权益）合计」行（**标签折行**，见 §4.3），期末列 |

**核对方式**：用 pdfplumber 把 p59 / p60 / p61 的全部词连同坐标逐行打印，
人工比对标签、数值与列位置三项。三个字段的期初列（2022年12月31日）也一并读了，
分别是 `254,500,826,096.02` / `49,562,744,832.16` / `204,938,081,263.86`
—— 记下来是为了 §5 的负控制。

**未取到的值**：本切片只取这三个字段，其余 12 个 `bs.*` 与另外四份映射文件
在 `01.5-03-PLAN.md`。**本文件不对未取的字段作任何断言。**

---

## 2. 验收：一条命令取回年报（A-10 判据）

- **验证方法**：真跑，看返回的 SHA-256 与源 URL；确认默认不留 PDF
- **实际命令**
  ```
  .venv/Scripts/python -m extractor fetch --stock 600519 --year 2023
  ```
- **真实输出**（`sha256` / `source_url` / `title` 逐字如下）
  ```json
  {
    "sha256": "2125ff97a452ea79b0d784e2432f7d224b6aecc330b644b593477d69e22f4ed1",
    "source_url": "https://static.cninfo.com.cn/finalpage/2024-04-03/1219506510.PDF",
    "title": "贵州茅台2023年年度报告",
    "org_id": "gssh0600519",
    "pdf_retained": false
  }
  ```
- **证据位置**：`src/extractor/download.py`、`tests/test_download.py`
- **判定**：**PASS**

---

## 3. 验收：三个字段取到真实值并算出真实数值

- **验证方法**：端到端真跑（联网重下，不用本地缓存），看输出里的 `value`
- **实际命令**
  ```
  .venv/Scripts/python -m extractor compute --metric debt_to_asset_ratio \
      --stock 600519 --year 2023 --json
  ```
- **真实输出**（节选；完整输出含三条 `ExtractionRecord` 的全部字段）
  ```json
  {
    "metric_id": "debt_to_asset_ratio",
    "definition_version": 2,
    "formula": "bs.total_liabilities / bs.total_assets",
    "value": "0.1798432413917914711797119101",
    "unit": "无量纲",
    "currency": "不适用",
    "batch_id": "61e881c77f3d4771",
    "derived": true,
    "reconciliation": {
      "passed": true,
      "identity": "bs.total_assets = bs.total_liabilities + bs.total_equity",
      "left": "272699660092.25",
      "right": "272699660092.25",
      "difference": "0.00",
      "tolerance": "0.01",
      "missing_fields": [],
      "source": "reconcile:balance_sheet_identity"
    },
    "input_field_ids": ["bs.total_liabilities", "bs.total_assets"]
  }
  ```
  退出码 `0`。
- **独立复算**：`49,043,190,797.43 ÷ 272,699,660,092.25 = 0.1798432413917914711797119101`，
  四位小数为 **0.1798**。两个被除数都逐字出现在上面的证据链记录里，复核者不需要重跑就能验算。
- **为什么不四舍五入到四位**：舍入位数是口径类开关，`L-34` 要求这类开关不设默认值。
  在口径定义里声明它之前，输出保留 `Decimal` 除法的完整精度，
  **由消费者按自己的口径舍入**，而不是在这里替它决定。
- **证据位置**：`src/extractor/formula.py`、`tests/test_formula.py::test_茅台2023的资产负债率算得出真实数值`
- **判定**：**PASS**

---

## 4. 验收：三条实测失效模式各有回归用例（A-6）

A-6 明写「探测跑通 ≠ 有回归用例」。三条各一条，跑在
`tests/fixtures/maotai_2023_bs_rows.json` 这份**抽取产物**固件上（不是 PDF）。

### 4.1 表标题印在上一页（页脚位置），数据落在其后的页上

- **真实形态**：「合并资产负债表」标题印在 p58 的 `top=662.3 / 841.9`，
  同页只跟得下两行（章节小标题「流动资产：」与第一个行项目「货币资金」）。
  三个目标字段落在 p59 / p60 / p61。
- **若不处理会怎样**：任何「标题与数据必须同页」的规则，这三个字段**全部取不到**。
  这正是 D-019 要把 `page` 与 `anchor_page` 拆成两个整数的原因。
- **回归用例**：`tests/test_locate.py::test_表标题印在上一页时行区间照样跨页归属`
- **判定**：**PASS**

### 4.2 合并表与母公司表的边界落在页内

- **真实形态**：p61 的 `top<234.3` 是合并资产负债表的尾巴（含 `bs.total_equity`），
  `top=234.3` 起是母公司资产负债表的标题。
- **若不处理会怎样**：按「页」定位必然混表。这正是 cninfo
  `extract_financial_statements()`「最后一个匹配的表静默胜出」的成因（D-013 / CONTEXT §6）。
- **负控制**：母公司的资产总计 `171,584,366,864.08` 不得落进合并区间；
  `资产总计` 在区间内必须恰好命中一行。
- **回归用例**：`tests/test_locate.py::test_合并与母公司的边界落在页内时按y归属`、
  `::test_母公司表的资产总计不得落进合并表区间`
- **判定**：**PASS**

### 4.3 行项目标签折行，数值行夹在两个标签片段之间

- **真实形态**（p61，逐字）：
  ```text
  所有者权益（或股东权
  223,656,469,294.82   204,938,081,263.86
  益）合计
  ```
  另一处同型：`归属于母公司所有者权益` / 数值 / `（或股东权益）合计`。
- **处置**：`标签行 → 纯数值行 → 标签行` 三行缝合，`label_lines` 保留**两个片段**、
  保持原顺序、**不拼接**。拼接会把「折行处该不该补字」这个判断塞进 `locate`，
  而那本是映射表要显式写清的事。
- **负控制**：连续的普通标签行不得被两两粘起来（p59 有一长串「行在、格子空」的项目）；
  三行跨页时不缝合。
- **回归用例**：`tests/test_locate.py::test_标签折行时三行缝合为一个行项目`、
  `::test_缝合只在标签行数值行标签行三连时发生`、`::test_缝合不跨页`
- **判定**：**PASS**

---

## 5. 验收：勾稽闸门真会拦，且它**证明不了**取的是对的那一列（A-9）

| 情形 | 结果 | 用例 |
|---|---|---|
| 茅台 2023 真实批次 | `passed=True`，差额 `0.00` | `test_茅台2023真实批次的恒等式差额为零` |
| 负债合计人为 +1.00 元 | `passed=False`，差额 `-1.00` | `test_负债合计人为加一元后闸门拦住` |
| 三项缺一 | `passed=False`，`missing_fields` 非空，`left/right` 为 `None`（不拿 0 凑数） | `test_缺一项时不拿零凑数` |
| 闸门未通过时算指标 | 返回 `Refusal`，无数值属性，理由码 `RECONCILIATION_FAILED`（枚举成员，不是字符串） | `test_闸门未通过时计算层拒答且不产出数值` |
| **压根没跑过闸门** | 同样拒答，`source="reconcile:not_run"` —— 没跑过 ≠ 通过 | `test_压根没跑过闸门也拒答` |

**A-9 的负控制**：三个数**全取自期初列**时恒等式照样成立
（`254,500,826,096.02 = 49,562,744,832.16 + 204,938,081,263.86`），闸门必然放行。
⇒ **「勾稽通过」推不出「取的是期末列」。** 列的正确性只能靠 `column_header` 的
显式绑定保证，二者不可互相替代。
用例：`tests/test_reconciliation.py::test_三个数全取自期初列时闸门照样放行`。

**判定**：**PASS**

---

## 6. 验收：解析器不能执行任意代码（D-017 / L-33 / 威胁 T-01.5-03）

| 判据 | 验证 | 结果 |
|---|---|---|
| `git diff --stat src/semantic_layer/dsl.py` 为空 | 真跑 | 输出为空，**PASS** |
| `grep -v '^#' src/extractor/formula.py \| grep -c 'eval('` | 真跑 | `0`，**PASS** |
| `grep -v '^#' src/extractor/formula.py \| grep -c 'import ast'` | 真跑 | `0`，**PASS** |
| `grep -v '^#' src/extractor/formula.py \| grep -c 'ROOT_NAMESPACES'` | 真跑 | `4`（≥1，只读导入），**PASS** |
| 含 `>` 的表达式被拒 | `pytest.raises` | **PASS** |
| `__import__("os")` 被词法器拒 | `pytest.raises` | **PASS** |
| 两个词法器对同一组字段引用给出相同序列 | 10 条语料 × 参数化 | **PASS** |

**一条如实的限定**：`bs.total_assets.__class__` **不报错** —— 它的根命名空间是 `bs`，
合法，于是解析成 `Ref("bs.total_assets.__class__")`。这不构成逃逸，理由是
`Ref.path` 只被拿去做一次字符串比对，全模块没有一处 `getattr`、没有属性访问
（由 `test_双下划线路径解析成一个惰性字符串而不是属性访问` 断言），求值结果是
「批次里没有这个字段」的拒答。**把它写成「会被拒绝」是好听但不真的说法。**

---

## 7. 验收：PDF 不进版本控制（AC-10 / T-01.5-04）

- **验证方法**：`semantic_layer scan` 的 `forbidden_tracked_file_types` 已含 `.pdf`
  且 fail-closed；另外直接查被跟踪文件
- **实际命令与真实输出**
  ```
  .venv/Scripts/python -m semantic_layer scan      # 退出码 0
  git ls-files | grep -ci '\.pdf$'                 # 0
  ```
- **默认不留盘**：`compute` 全程用临时目录接 PDF，命令结束后 `data/raw/` 为空目录。
- **判定**：**PASS**

---

## 8. 六道门与冻结校验

- **实际命令**（按 F-8 用 `&&` 串联，禁止 `;`）
  ```
  .venv/Scripts/python -m pytest -q \
    && .venv/Scripts/python -m semantic_layer scan \
    && .venv/Scripts/python -m semantic_layer validate \
    && .venv/Scripts/python scripts/check_xrefs.py \
    && .venv/Scripts/python scripts/check_reading_ledger.py \
    && .venv/Scripts/python scripts/check_gates.py \
    && .venv/Scripts/python scripts/verify_deps.py
  ```
- **真实输出**：`561 passed`，末端退出码 `0`
- **两处冻结产物**
  ```
  cd eval/frozen-01   && sha256sum -c SHA256SUMS   # 全部 OK
  cd docs/agent/poc-01 && sha256sum -c SHA256SUMS  # 全部 OK
  ```
- **判定**：**PASS**

---

## 9. 这份切片**没有**证明什么

写在这里，因为「自证机制说通过了，但它证明的不是它声称证明的事」是本项目
已经踩过四次的形状（A-9）。

- **单公司单年单样本。** 三条失效模式的对策在**茅台 2023 这一份**上成立。
  别的公司、别的年度、以万元列报的报表、以整数金额列报的报表，
  **一律 `UNVERIFIED`**。数值正则要求两位小数这一条，A-6 已明写是单样本结论。
- **未验证「跨页折行」。** 本样本上没有观察到标签折行跨页的形态，
  因此**没有为它写对策** —— 没观察到就写规则，得到的是永远不会正确触发的规则（F-2）。
- **未验证 `ROW_ABSENT` 的天然样本。** 茅台的母公司资产负债表行项目是合并表的
  真子集，固件里找不到「别的表上有、这张表上没有」的天然样本，
  该分支的用例是构造的（见 `tests/test_mapping.py` 里那条测试的 docstring）。
- **未验证除本切片三个字段以外的任何字段。** 其余 12 个 `bs.*` 与另外四份映射
  文件的可行性在 `01.5-02-PLAN.md` / `01.5-03-PLAN.md` 里探测，**此处不作预判**。
- **`BasisConfirmation.UNCONFIRMED` 在本切片里没有触发路径。** 它是 L-14 定的
  三个正交事实之一，形状已就位，但本切片的列绑定全部由显式规则解析成功，
  没有一条记录走到 UNCONFIRMED。这一支目前**只有形状，没有实证**。
- **pdfplumber 版本与实测不同。** CONTEXT §3 的 15/15 是 2026-08-16 用 **0.11.5**
  跑的，本仓库装的是 **0.11.10**（`>=0.11.5` 解析到最新）。
  8 个锚点、4 个合并、三个字段的取值在 0.11.10 上复现一致（见 §1 与 §4），
  但 15/15 那一组里的另外 12 个字段**没有在 0.11.10 上重跑过**。
