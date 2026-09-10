# 常用命令


```bash
# 阶段状态
cat .planning/STATE.md

# 校验已冻结实验输入未被改动（声明任何评测/POC 结论前必跑）
cd docs/agent/poc-01 && sha256sum -c SHA256SUMS

# 评测（Phase 1 起可用）
python -m eval.run --suite frozen-01 --report reports/
```

（评测命令在 Phase 1 实现前不存在，不要假装跑过。）

```bash
# H2 复核实验器械（02-03）。第一条出题包，第二条在答卷填完之后算数。
# 🔴 出题包**一律加 --blind**（`N-75`）：盲模式下跑分结果不出 `build_packets`，
#    于是执行者印不出 W、印不出逐题结果。2026-09-09 栽过一次 ——
#    读了结果又转述给复核者本人，§4.2 一致率当场作废。
.venv/Scripts/python -m eval.h2 --suite frozen-02 --seed 20260909 --out docs/agent/h2-xxx --blind
.venv/Scripts/python -m eval.h2 --suite frozen-01 --sheet docs/agent/h2-01/answer-sheet.yaml

# ⚠️ **复核做完之前不要跑下面这条。** `--blind` 管不着别的进程，
#    而这一条会把逐题结果和分布直接打在屏幕上 —— 规矩是「出包 → 复核 → 才跑、才报」。
# .venv/Scripts/python -m eval.run --suite frozen-02
```

⚠️ **第二条只有真人填完答卷才跑得出结论**：留空即 fail-closed，退出码 1 并逐题点名。
**执行者不得代填任何一格**（`N-20` 判据：执行者代答无效）。
⚠️ 出题包之前**不要**读 `docs/agent/h2-01/keymap.json` 或 `02-03-PLAN.md` 的 `<context>` —— 那里写着哪几道是错题。

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
- **R6**（2026-08-31 新增，台账 `N-40` 判据 2）**逐条**查断言：语法上恒为真的一律报红
  —— R3 只让恒真断言**不计入** R1 的可失败点（管「函数整体能不能红」），
  R6 管**每一条**。`assert x or True` 与两条真断言并排站着时 R1 判「能红」是对的，
  而那一行看起来在检查、实际什么都不检查。`N-40` 的实例在仓库里活了若干轮。
  ⚠️ **只查语法上恒真，不查运行时恒真** —— 后者要求值，那条路通向一个自己会出错的
  检查器。`assert len(xs) >= 0` 语义上恒真但语法上不是，**明确不抓**。宁可漏判，不许误报

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

**门禁测试里跑子进程时，必须强制子进程用 UTF-8 写 stdout。**
2026-08-24 实测：不设 `PYTHONIOENCODING` / `PYTHONUTF8` 时，Windows 子进程按系统代码页
（cp936）输出，父进程按 UTF-8 解码得到 mojibake，`assert "悬空引用" in r.stdout` 匹配不到
——**第一道门的负控制被一个环境变量翻红，而红的原因不是它要查的那件事**。
危险不在于红，在于**人看见它红会去改测试而不是改环境**。
Linux runner 默认 UTF-8，所以 CI 从不暴露这条：**这是「本地绿 ≠ CI 绿」的反向实例**
——CI 常绿而本地红，同样会让人误判。
⇒ 子进程一律传 `env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}`，
**不要靠调用者记得 export**。已落在 `tests/test_xrefs.py` 的 `_UTF8_ENV` 与 `tests/test_gates.py`。

**跑变异时必须设 `PYTHONDONTWRITEBYTECODE=1`（2026-08-28 实测，登记册 `N-41`）。**

✅ **2026-08-31 起，pytest 这条路上忘了设也没关系**（`N-41` 判据 2）：
`tests/conftest.py` 会在会话开始时 ① 关掉字节码写入、
② **删掉 `src/` 下已有的 `__pycache__`** —— 第 ② 条才是要紧的那条，
因为骗过验证的是**读**到上一轮留下的 `.pyc`，不是写。
⚠️ **本条规则不删**：它仍然管到 pytest 之外的场景 ——
直接用 `python -c` 驱动的探针、以及任何不经过 pytest 的变异脚本，
conftest 根本不会被加载。**「有一条路自动了」不等于「所有路都自动了」。**

🔴 **这一条不是保险，是这个程序被真实骗过一次之后加的。**

变异 `entry.column_name == column_name` → `column_name in entry.column_name`
**两行字节数完全相同**（各 48 字节）。`.pyc` 的失效判据是源文件的
**(mtime, size)**，而 mtime 是**秒级**的：造回归与回退发生在同一秒内、
文件大小又一字不差 ⇒ **Python 继续用缓存里那份字节码**。

实测后果：回退之后复跑，`test_流动负债合计不匹配总负债` **仍然红**。
`grep` 看到源码里是 `==`，`inspect.getsource()` 打出来也是 `==`
（**它读的是文件，不是加载进来的字节码，所以它证明不了任何事**），
而跑起来的行为是子串包含。清掉 `__pycache__` 之后立刻变绿。

**两个方向都会被骗，而且危险程度不同**：

| 方向 | 表现 | 后果 |
|---|---|---|
| 回退后仍红 | 缓存里是变异版 | 会去「修」一个不存在的缺陷 —— 吵，但查得下去 |
| **造回归后是绿** | **缓存里是原版，变异根本没生效** | **会判定「这道门不设防」并动手加一道多余的门；反过来也可能把一道真的没设防的门记成有效** |

第二种是致命的：**它产出的是一条「我验过了」的结论，而验证根本没发生。**
这正是本项目已经记了七次的那个形状，这次出现在**用来检测那个形状的工具**自己身上。

⚠️ **等长变异不是罕见情况**，它恰恰是最常见的一类：
`==` ↔ `in`、`<=` ↔ `>=`、`and` ↔ `or`、`True` ↔ `None`（都不等长，但
`!=` ↔ `==` 加一个空格就等长）——**比较运算符的互换天然容易等长**。

写法上把回退做成 `trap ... EXIT`，别指望自己记得还原：

```bash
export PYTHONDONTWRITEBYTECODE=1        # ← 不是可选的，见上
cp tests/target.py /tmp/backup.py
trap 'cp /tmp/backup.py tests/target.py; rm -f /tmp/backup.py' EXIT
# ...造回归、看红...
```

**已经跑过的变异结论，如果当时没设这个变量、且变异是等长的，一律记 `UNVERIFIED`，
重跑一遍**——不要因为「当时看着是对的」就留着。

## 第 0 步：确认被测对象是**当前工作树**的产出（2026-08-27 新增，登记册 `L-22`）

**跑任何门禁之前先问一句：我刚才改的那份文件，是它读的那份吗？**

出处 `references/deepseek-harness-notes-part3.md` C-A15
（源 `HN-B13:82`；`HN-` 是来源前缀，指 harness `.agents/notes/implemented/bug-fix` 第 13 篇
——原编号裸写会被 `check_xrefs.py` 解析成本仓台账 B 区的条目）：
对方的 `WorkspaceBrowser.module.css` **从来不进 `apps/web/dist`**，
于是只重跑 `build:web` 的负控制跑的是**陈旧 bundle**，把那条声明整个删掉**照样通过**。
笔记自己的判词是「这读起来像一个空洞的测试，而不是一个无效的控制」。
**且 CI 从未暴露，只有本地脚本暴露。**

⇒ 它与本文件下面记的 UTF-8 那条是**镜像**：那条是「CI 常绿、本地红」，
这条是「本地绿、CI 会红」。两条合起来的结论不是「以哪边为准」，而是——
**「跑过了」这三个字必须连带说清跑的是谁的产出。**

### 本仓已经实地命中一次，就在写这一节的同一个会话里（2026-08-27）

在 `.claude/worktrees/` 的独立工作树里、用主仓 `.venv` 的解释器跑门禁：

```bash
.venv/Scripts/python -c "import semantic_layer; print(semantic_layer.__file__)"
# → ...07-finaudit-agent\src\semantic_layer\__init__.py       ← 主工作树
# 期望的是 ...\.claude\worktrees\<name>\src\semantic_layer\__init__.py
```

根因是 `.venv/Lib/site-packages/__editable__.finaudit_semantic_layer-0.1.0.pth`
——editable 安装把一个**固定绝对路径**钉进了解释器，`import` 从此不跟 cwd 走。
于是 `python -m semantic_layer scan` / `validate` 这两道门**读的是主工作树的代码与
`metrics/`**，而主工作树此刻正有另一个 agent 在写 Phase 1.5 的代码。

**同一个解释器、同一个 cwd，`pytest` 却没有这个问题**：
`pyproject.toml` 的 `[tool.pytest.ini_options] pythonpath = ["src"]`
让 pytest 把 **rootdir 下的 `src`** 插到 `sys.path` 最前面，而 rootdir 由
worktree 里的那份 `pyproject.toml` 决定（实测 `rootdir:` 打的就是 worktree 路径）。
⇒ **两条命令导入的是两份代码，而输出里没有任何东西会告诉你这件事。**

⇒ **在非主工作树里跑门禁，必须显式覆盖 `PYTHONPATH`**：

```bash
PYTHONPATH="$PWD/src" .venv/Scripts/python -m semantic_layer scan
PYTHONPATH="$PWD/src" .venv/Scripts/python -m semantic_layer validate
```

⚠️ **这不是「worktree 的坑」，是「editable 安装 + 多工作树」的坑。**
识别方法一句话：**跑之前先让它把 `__file__` 打出来**——
和 C-A15 原文的做法同型（先确认产物是刚构建出来的，再谈验证结果）。
⚠️ 目前**没有门禁强制这一步**：写一条「断言 `semantic_layer.__file__` 在 rootdir 下」
的测试是可行的，但它属于 `tests/`，本轮不动。**如实记在这里，不假装有覆盖。**

## 本项目的测试写法约定（2026-08-27 新增，登记册 `L-65`）

出处 `references/hello-agents-framework-core.md` FC-A3（该文 §7.3「回归型三件」）。
挑出来的三条是那套仓库里**唯一写对了的一批测试**的共同点——
同仓「演示型六件」174 条断言里 `==` 只占 76 条，回归型三件 50 条里占 46 条。

1. **自建假客户端，不用 mock 框架。**
   （`test_llm_streaming.py:27-75` 的 `FakeClient` / `FakeAsyncStream`）
   确定性、可离线、无需 mock 库，**读起来本身就是一份行为规格**。
   本项目的对应物：PDF 抽取的假页面、AKShare 的假响应，一律写成显式的假对象。
2. **精确等值断言，不用存在性断言。**
   （`:91` `assert chunks == ["hello"]`，`:92-96` 断言整个 usage 字典）
   与本文件第六道门的 R3、`pitfalls.md` 第 18 条是同一条：
   **`in` / `is not None` / `hasattr` 测的是形状，缺陷在生产者。**
3. **把「不该发生的事」升级成错误。**
   （`test_pydantic_v2_serialization.py:30-31`
   `warnings.simplefilter("error", PydanticDeprecatedSince20)`
   ——全套件唯一一处断言「某事不该发生」的写法）
   **本项目最该用这条的两处**：`AC-02`（口径缺失时拒答）与
   `AC-09`（静态校验拒绝危险样本）。两处都写成
   `pytest.raises` + **断言精确的理由码**，
   **不写「返回值非空」**——非空可以由一句错误字符串满足。

## 门禁断言的元判据：说不出它什么时候会红，就删掉（2026-08-27 新增，登记册 `L-32`）

出处 `references/hello-agents-framework-core.md` FC-B5（该文 §7.6）：
两个**构造上不可能失败**的测试
（`test_all_agents.py:238-249`、`test_context_engineering.py:357-419`）
都答不出「它在什么情况下会红」这句话，而它们**至今挂在套件里显示为绿**。

⇒ **新增或修改任何门禁断言时，必须能用一句话说出它会红的那个场景。**
说不出来的两个处置，二选一，没有第三种：**删掉**，或**按上面的「造回归 → 看红 → 回退」
把那个场景真的造出来**。

**与第六道门 R2 的关系**：R2 是这条元判据的**机械化的一半**——
它要求每道门禁在 `GATES` 注册表里具名声明一个负控制，且那个负控制自己满足 R1。
**但 R2 只保证「存在一个会红的负控制」，保证不了「这条断言本身答得出那句话」。**
剩下那一半没有机械判据，只有这条人执行的规矩。
⚠️ 不许把「R2 通过」读成「每条断言都说得出它什么时候会红」。

## 已识别、但**尚未机械化**的门禁缺口（2026-08-27 新增）

**这一节记的是「约束已经成立、门禁还没写」，不是待办清单。**
写在这里而不是留在登记册里，理由是：**这些约束现在就在约束我们怎么写代码与文档**，
而门禁什么时候写是另一回事。⚠️ **不许把本节读成「已经有检查了」。**

### (1) 类型注解必须由 checker 执行；死抽象必须被发现（登记册 `L-25`，**部分落地**）

三份产物指向同一个缺口：

| 来源 | 实证 |
|---|---|
| `hello-agents-ch06-frameworks.md` X6-2 | LangGraph Demo 三个节点全部注解 `-> SearchState`，实际返回的是**部分字段的 dict**（`:42` / `:80` / `:132`）；`code/chapter6/` **零测试、零 mypy、零 pyproject** |
| `hello-agents-ch07-framework.md` C7-X13 | **死抽象：声明了但零消费**——`Config` 全包零消费，`max_history_length` 声明了历史上限而**没有任何地方裁剪历史** |
| 同上 C7-X9 | 位置传参 + 签名不统一 ⇒ **静默参数错绑**：`system_prompt` 被绑到父类的 `tool_registry` 形参上，因为子类从不读它，**这个错误永远不会表现出来** |

X6-2 的判词值得逐字留着：**有类型注解但不跑 checker，比没有类型更危险**
——它制造「我们有类型」的错觉，于是运行时校验被省掉。

⇒ **本项目现在就成立的三条约束**：
① 新增的类型注解必须是**能被 checker 验的**（不写 checker 验不了的注解来充数）；
② **公开接口声明了就必须有消费者**，没有消费者的先别声明；
③ **构造函数与跨模块调用一律关键字传参**。
⇒ **未做的那一半**：把 mypy / pyright 加进这份文件的门禁命令与 `gates.yml`。
`D-015` 已经用对了同一个机制（依赖方向由测试强制），但它只覆盖依赖方向。

### (2) 文档里出现的字段名 / 类名必须在代码中存在（登记册 `L-26`，**部分落地**）

出处 `references/hello-agents-ch06-frameworks.md` §9.5，它把 X6-7（派生数据被物化）
的适用范围扩大了一层：**文档也是一份派生数据。**
README 里的类定义、架构图、文件清单，全是从代码派生出来的事实的第二份拷贝，
**而且是唯一没有任何机制校验的那一份**——该章两份 README **全烂了**。

**本仓已经有一个成功对照**：`scripts/check_xrefs.py` 让 `D-0xx` / `AC-xx` / `OQ-xx`
这类交叉引用**悬空即非零退出**，所以这类引用不会腐烂；
而字段名、类名、文件清单**没有这类校验**。
（对方的做法是 `development.md:163-171` 的 `verify-type-equiv`：
一份 `{doc, symbol, source}` 清单 + 解析器提取 + 1:1 校验。
本项目若要做，**用 Python `ast` 而不是正则**。）

⇒ **现在就成立的约束**：文档里写死一个字段名 / 类名 / 枚举值时，
必须是**从代码里复制出来的**，且改代码时同步改文档。
⇒ **未做的那一半**：`verify-doc-symbol` 这道门。

### (3) 不调模型的主流程必须有**无密钥、走真实入口**的 CI 测试（登记册 `L-27`）

出处 `references/deepseek-harness-docs-part2.md` HD2-15，逐字引自 `postmortem/0001:112`：

> When the headline operation does not call the model, that test needs no API key
> — so it belongs in CI, **not behind a key gate**.

**本项目的口径解析、拒答判定、证据链装配全部不调模型**，因此**整个主流程都属于这一类**。
⇒ **判据**：这三条链路的测试**不得**以「需要密钥」为由被排除在 `gates.yml` 之外；
若某条测试确实需要密钥，那说明它测的不是主流程，应当拆开。
现状：`gates.yml` 跑的六道门**全部无密钥**，本条**当前成立**；
它约束的是未来——接了模型之后，不许顺手把主流程测试挪到密钥门后面。

## CI（2026-08-22 新增，D-021 第二条豁免）

`.github/workflows/gates.yml` 在 push / PR 时跑**同一组门禁**，不新增检查项。
本地与 CI 是同一份命令的两个执行位置——**本地绿不等于 CI 绿**：
Linux 与 Windows 在换行符、路径大小写、locale 上都可能分叉，
而冻结产物的 SHA-256 跨平台稳定（D-012 的物理保障）**只有在 Linux runner 上才验得出来**。

改 `gates.yml` 等同于改门禁定义，**必须同步本文件**，反之亦然。
CI 只允许跑验证：不得构建产物、发布、部署，工作流已声明 `permissions: contents: read`。

## 往文件里写反斜杠：用 `chr(92)`，不要靠「多写一个」抵消（2026-08-29，第三次踩）

`\\` 在「Bash 工具 → shell → python heredoc → Python 字符串」这条链上**不是幂等的**：
源码里写两个反斜杠，到达 Python 的可能只剩一个，于是 `\b` 被求值成 **U+0008（退格）**
并静默写进 markdown。**写的人看不见、`print` 看不见、diff 看不见**，
只有 `tests/test_conformance.py::test_被跟踪的md里没有字面控制字符` 看得见（它抓到过三次）。

⇒ **凡是要往文件里写反斜杠，用 `chr(92)` 构造，不让它以字面量形式经过任何一层。**
「少写反斜杠」这条对策不够 —— 2026-08-28 避的是**修复动作**里的反斜杠，
08-29 栽在**被写入内容**里的反斜杠上。完整病例见台账 `N-38`。

## 提交前跑的必须是**整条七道门链**，不是其中几条（2026-08-31，实地踩到）

**这就是那条链**（2026-09-05 补上 —— 此前它只活在交接文件里，
每次会话都要重新拼一遍，拼漏一条正是本节记的那个事故）：

```bash
.venv/Scripts/python -m pytest -q   && .venv/Scripts/python -m semantic_layer scan   && .venv/Scripts/python -m semantic_layer validate   && .venv/Scripts/python scripts/check_xrefs.py   && .venv/Scripts/python scripts/check_reading_ledger.py   && .venv/Scripts/python scripts/check_gates.py   && .venv/Scripts/python -m pytest tests/test_plan_waves.py -q
```

三条配套纪律：

- **不要在任何一道门后面接管道。** `... | tail -30` 之后 `$?` 是 `tail` 的退出码，
  门红了你也看不见（`F-8`；2026-09-04 自己踩过一次）。要截输出就**重定向到文件再看**。
- **造回归时先 `export PYTHONDONTWRITEBYTECODE=1`**，否则字节码缓存能让
  「造回归 → 看红 → 回退」整段失效（`N-41`）。
- **供应链门禁 `scripts/verify_deps.py` 不串进这条链** —— 它走网络，单独跑。
  🔴 **已知它在 akshare 一项上红着**（近月下载 2,974,120 < 门槛 3,000,000）。
  这个红是 **`D-036` 裁过的、带反转触发条件的已知状态** ——
  **看到红不许下调门槛**，那正是 `D-030` 点名禁止的处置。
  末行有三个词：`通过` / `不通过` / **`未生效`**（有检查根本没跑到）。
  ⚠️ `未生效` 的退出码仍是 0，**哑与绿在退出码上不可区分**，看末行别只看退出码。

⚠️ **耗时不是判据。** 2026-09-05 同一棵树连跑四次：148s / 151s / 304s / 296s，
最慢的一次是最快的两倍。判据是 `866 passed`（当日读数）与**链路退出码 0**。

`F-8` 立的规矩是「验证与提交一律 `&&` 串联」—— 它管的是**短路**，
保证「验证失败时后面那条不执行」。**它不管「你跑的是不是全套」。**

2026-08-31 的实例：改完一批文档后只跑了 `check_xrefs` + `check_gates` +
`check_reading_ledger` 三条就提交（`a470137`），而**全量 `pytest` 是在那批改动之前跑的**。
`tests/test_conformance.py::test_被跟踪的md里没有字面控制字符` 属于 pytest 那一条，
于是两个控制字符**带着绿灯进了库**，下一轮才炸。

⇒ **判据很简单：最后一次改动之后，整条链必须从头跑一遍。**
「刚才跑过 pytest」不算 —— 要问的是「**跑的是不是当前这份工作树**」。
改的只是 markdown 也一样：本仓有三条 pytest 用例专门检查 markdown
（控制字符、计划与路线图一致性、references 台账），**文档改动一样会让 pytest 红**。

## 描述转义序列时，用汉字描述，不要复现它（2026-08-31，同日第四次）

`chr(92)` 那条解决的是「我要写一个反斜杠」。但如果要举的例子**由多个反斜杠组成**
（例如说明 git 会把非 ASCII 路径转义成什么样），每多一个反斜杠就多一次被吃的机会 ——
这次其中两个三位数字被当成八进制转义求值成了 `U+0088` 与 `U+009A` 两个控制字符，还被复制进两个文件。

⇒ **描述性写法零反斜杠、零风险**：写「每字节一个反斜杠加三位八进制数」，
不要把那串东西本身抄进文档。完整病例见台账 `N-38`。

### 第四次（2026-09-10）：这次是**换行转义**，在被写入的测试代码里

上面三次栽的是退格、是 git 的八进制转义。这次栽的是最普通的那个 ——
往 heredoc 里的 Python 字符串写「反斜杠加 n」，想让它以两个字符的形式落进
测试文件里当转义序列用。到达文件时它变成了**一个真的换行**，
把测试里的字符串字面量拦腰截断，`pytest` 收集期直接语法错误。

⚠️ **不要以为「只有奇怪的转义才会被吃」。** 被吃的是**反斜杠本身**，
后面跟什么字母无关。`chr(92)` 那条对**所有**反斜杠成立，包括最常见的那个。

## 🔴 用 Python 改文件：先写临时文件再 `os.replace`，不要 `open(p, "w")`（2026-09-10，真丢过一次）

`io.open(p, "w")` **打开即截断**。若随后的 `write()` 抛异常（编码错误、磁盘满、
中途被打断），文件就停在 **0 字节** —— 原内容没了，而异常栈看起来只是「写失败」。

2026-09-10 实地发生：改 `src/service/api.py` 时，替换文本里混进了一个孤立代理字符，
`write()` 抛 `UnicodeEncodeError`，**19 KB 的源文件当场变成 0 字节**。
当时它有未提交的改动，靠 `git checkout HEAD -- <file>` 找回了已提交的部分，
未提交的那段只能凭记忆重打。**再晚一步就是真丢失。**

⇒ 固定写法（本仓多处已在用）：

```python
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
os.close(fd)
io.open(tmp, "w", encoding="utf-8", newline=chr(10)).write(新内容)
os.replace(tmp, path)          # 原子替换；写失败时原文件一个字节没动
```

⚠️ 临时文件要落在**同一个目录**，否则 `os.replace` 跨卷会失败。
⚠️ 小改动优先用 Edit 工具，它不做整文件重写，根本不经过这条路径。
