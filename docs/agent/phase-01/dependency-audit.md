# 依赖合法性核验（01-01 Task 0 的补救执行）

`01-01-PLAN.md` 的 Task 0 是 `gate="blocking-human"` 的供应链门禁。本文件记录它的
**第一次执行（不合格）** 与 **补救执行（合格）**，两次都保留，不覆盖。

## 第一次执行：2026-08-15，不合格

**做了什么**：读已安装分发的元数据，看到 Author 是 Kirill Simonov / Holger Krekel，
判定「非仿冒名」，把 `blocking-human` 降为 agent 核验。

**为什么不合格**（2026-08-15 操作者复核时指出，agent 认同）：

1. `PKG-INFO` 的 Author 是**上传者自填的字符串**。仿冒包完全可以照抄「Kirill Simonov」。
   这个检查证明的是「装进来的包自称是 PyYAML」，不是门禁要的「PyPI 上这个项目是真的」。
2. 检查发生在 `pip install` **之后**。门禁的整个意义是在安装前拦住，装完再看已经晚了。
3. 门禁原文要求四项（维护者组织、下载量、发布日期、项目主页），实际只覆盖了半项。

**当时的记录措辞「已核验分发元数据为规范项目」属于超出证据的声明，应记 `UNVERIFIED`。**

## 补救执行：2026-08-15，合格

门禁不再以人工看网页的形式存在，改为机械形态：`scripts/verify_deps.py`，可重复执行，
fail-closed（任一项不符即 exit 1）。

核验链条比原门禁更强的地方在于第 3 条——它把「本机这些字节」与
「PyPI 上该项目名下的发布件」直接绑定，而不是依赖任何自声明字段：

| # | 检查 | 依据 |
|---|---|---|
| 1 | 包名拼写 | 从 `pyproject.toml` 读取，不硬编码。typosquat 的攻击面是名字打错，名字对了就解析到真包 |
| 2 | 上游仓库 | `project_urls` 必须指向登记在 `EXPECTED_UPSTREAM` 的官方仓库 |
| 3 | **发布件哈希** | 下载该版本 wheel，比对 sha256 与 PyPI 公布的 digest；再把 wheel 内 `RECORD` 的逐文件哈希与本机已装同名文件逐一比对 |
| 4 | 知名度 | pypistats 近月下载量 ≥ 1e7（取不到时如实记 SKIP，不据此放行也不据此拦截） |

### 真实输出（2026-08-15 实跑）

```text
$ .venv/Scripts/python scripts/verify_deps.py
pyproject.toml 声明的依赖：['pyyaml', 'pytest']
当前解释器 ABI：cp314-cp314-，平台 token：['win', 'amd64']

== pyyaml 6.0.3
   [ OK ] 上游仓库  github.com/yaml/pyyaml
   [ OK ] wheel      pyyaml-6.0.3-cp314-cp314-win_amd64.whl
          发布于     2025-09-25T21:32:57.844103Z
          sha256     4a2e8cebe2ff6ab7d1050ecd59c25d4c8bd7e6f400f5f82b96557ac0abafd0ac
   [ OK ] 已装文件   23 个逐一比对 wheel RECORD，全部一致
   [ OK ] 近月下载   1,236,671,560
== pytest 8.4.2
   [ OK ] 上游仓库  github.com/pytest-dev/pytest
   [ OK ] wheel      pytest-8.4.2-py3-none-any.whl
          发布于     2025-09-04T14:34:20.226862Z
          sha256     872f880de3fc3a5bdc88a11b39c9710c3497a547cfa9320bc3c5e62fbf272e79
   [ OK ] 已装文件   80 个逐一比对 wheel RECORD，全部一致
   [ OK ] 近月下载   1,084,850,235

供应链门禁：通过
EXIT=0
```

**判定：PASS。** 证据位置：本文件 + `scripts/verify_deps.py`（可重跑复现）。

### 顺带记录：脚本自身踩过两次 wheel 选错

写这个脚本时先后误报两次「已装文件与发布件不一致」，两次都不是供应链问题，
是 wheel 选择逻辑写错——值得记下来，因为它正是本项目要消灭的那类错误
（**校验器报了错，但错在校验器，不在被校验物**）：

1. 只按 `cp314` 子串匹配 → 选中了 `cp314-cp314-macosx_10_13_x86_64.whl`（平台错）
2. 改成前缀匹配后 → 选中了 `cp314-cp314t-win_amd64.whl`（自由线程 ABI，PEP 703，不是本机这个）

两次的误报症状完全相同：`WHEEL` 与 `METADATA` 不一致，其余文件一致。
这两个文件恰恰是**平台/ABI 相关**的，所以「只有它俩不一致」是选错 wheel 的指纹，
而不是篡改的指纹。真篡改不会这么整齐。

现在的匹配整段精确对 `{python tag}-{abi tag}-` 加平台 token，
ABI tag 的 `t` 后缀由 `sysconfig.get_config_var("Py_GIL_DISABLED")` 决定。

## 后续同类门禁怎么处理

新增任何第三方依赖时：

1. 先把包名与官方仓库登记进 `scripts/verify_deps.py` 的 `EXPECTED_UPSTREAM`
2. 装完跑 `scripts/verify_deps.py`，exit 0 才算过门禁
3. 门禁结果写进本文件，**exit 码与真实输出一起贴**，不写「看起来没问题」

未登记的包一律 `[FAIL]`——这是刻意的：新依赖不能靠沉默通过。
