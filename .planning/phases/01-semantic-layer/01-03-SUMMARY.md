# 01-03 SUMMARY —— 非公开数据扫描器 + 陷阱元规则占比统计

**模式：IMPLEMENT（TDD）。** 未改权威文档、未改 `metrics/` 下任何定义。

**结果：完成。** 两条门禁命令上线，外加操作者裁决并入的 OQ-02 修复。

## 交付物

| 文件 | 作用 |
|---|---|
| `scan_rules.yaml` | 全部扫描规则，版本化、可 diff、可质疑（D-010 明文要求） |
| `src/semantic_layer/scan.py` | 只执行不判断；规则不可用即 fail-closed |
| `src/semantic_layer/stats.py` | 陷阱占比统计，含 per-metric 分项 |
| `src/semantic_layer/__main__.py` | 追加 `scan` / `stats` 两个子命令 |
| `tests/test_scan.py` | 26 用例 |
| `tests/test_stats.py` | 13 用例 |
| `tests/test_vocabulary.py` | 10 用例（OQ-02 的回归锁） |

测试总数 **40 → 93**。

## Task 1：非公开数据扫描（AC-10 / D-010）

四组规则，全在 `scan_rules.yaml` 里：

1. `forbidden_tracked_file_types` — 8 个扩展名，判据是 `git ls-files`，不扫工作区未跟踪文件
2. `gitignore_required_entries` — 4 条隔离条目缺一即 `GITIGNORE_COVERAGE_LOST`
3. `content_patterns` — `CONTACT_PATTERN` / `NETWORK_PATTERN`；`organization_tokens` **留空**
4. `semantic_layer_provenance` — 6 个公开报表 + 5 个字段前缀

第 4 组是本项目特有的，把 CLAUDE.md 那句人工自查（「这个字段名是从哪来的？」）
变成机器提问：**来自公开披露报表的哪一张。答不上来就失败。**
字段名是最隐蔽的泄漏载体——内部系统的列名混进来，从内容上看不出任何异常。

### 两处实现判断，都不是计划里写的

**其一：`statement` 用前缀匹配，不用精确相等。** 真实定义写的是
`财务报表附注「非经常性损益项目及金额」`，精确匹配会把它判为不合规。
受控的是**出自哪张公开报表**，不是不许写得更精确。若用精确匹配，
计划自己的验收标准（`scan --json` 在当前仓库退出 0）当场就不成立。

**其二：新增 `content_scan_excluded_paths`，计划里没有这一组。**

发现路径：写完提交前跑 `scan`，扫出 2 项——都在 `tests/test_scan.py` 上。
这不是测试夹具没写好，是**结构性的**：任何模式扫描器的测试都必然携带它要找的模式。

处理没有硬编码排除，而是加了一组版本化的豁免清单，理由是 D-010 要求规则可审查——
豁免是门禁上的洞，洞更应该在能被 diff 的地方。三条约束防止它变成后门：

- 只豁免 `content_patterns`，其余三组照查（`test_exclusion_only_waives_content_patterns`）
- 清单被测试**钉死**，增长必须同时改测试（`test_content_scan_exclusion_list_is_pinned`）
- 文件里写明判据：只有「因为要测试/定义模式串本身，所以必然携带模式串」够格。
  「这个邮箱是无害的」不是理由——那种情况应该改掉那个邮箱

## Task 2：陷阱元规则占比统计（§5.1 监控指标）

阈值语义是**严格大于**，与 §5.1 的「> 50%」逐字一致。两条测试分别锁住
「恰为 0.5 → exit 0」与「0.6 → exit 1」——`>` 被写成 `>=` 是最容易发生也最难看出来的漂移。

一处偏离计划：`PitfallStats` 多了 `unclassified` 字段。既无 `enforced_by` 又无
`advisory_only` 的条目是 R8 不合规，若把它算进 `advisory` 会让占比虚低、**掩盖问题**；
算进 `enforced` 更错。单独一类，文本输出里单独告警。

## 顺带完成：OQ-02（操作者裁决并入本计划）

`load_vocabulary()` 现在五键缺一即 `raise`，并额外拒绝 `affects_comparability`
为非布尔值——写成字符串 `"false"` 会被 `bool()` 判成 `True`，比漏写更隐蔽。
**OQ-02 已关闭。**

## 新发现：OQ-03（未在本计划内解决）

`resolve` 子命令**未实现**（`src/semantic_layer/resolve.py` 不存在，
`_cmd_resolve` 的 import 抛 ModuleNotFoundError），且 `_cmd_resolve` 返回 3
而 01-06 三处断言期望 2。

wave 3 的 01-06 会在这条断言上失败，且失败原因是「命令不存在」而非「靶子不对」。
CCC 作为 C2 拒答靶子的整个论证挂在这条命令上，AC-02 的执行体也是它。
**倾向沿用代码的 3 并改计划**——2 已被 `_cmd_validate` 用作「调用错误」，
拒答是正常业务结果不该复用。**待裁决，最迟 01-06 执行前关闭。**

## 验证（2026-08-15 实跑）

```text
pytest -q                                    93 passed
semantic_layer scan                          exit 0，findings []
semantic_layer scan --json ×2                两次输出逐字节相同
semantic_layer scan --rules /nope.yaml       exit 2（fail-closed，不静默通过）
semantic_layer stats --fail-over 0.5         exit 0（实际占比 20.0%）
semantic_layer validate                      exit 0
scripts/verify_deps.py                       exit 0
openspec validate --all --strict             1 passed, 0 failed
sha256sum -c SHA256SUMS                      5/5 OK
git status --porcelain docs/agent/poc-01/    空
```

规则文件结构：`rules_version` 1 / `allowed_statements` 6 / `allowed_field_prefixes` 5
/ `organization_tokens` 0 / `forbidden_tracked_file_types` 8——全部符合验收。

**判定：PASS。** 三条 success criteria 均有真实命令与输出支撑。

## 下一步

wave 2 完成。wave 3（01-04 / 01-05 / 01-06，19 份定义，可并行）前须先关 **OQ-03**。
