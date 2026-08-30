"""把「字节码缓存能让『造回归 → 看红 → 回退』整段失效」变成不可能 —— 台账 `N-41` 判据 2。

## 病例回顾（真实，2026-08-28 实测）

`.pyc` 的失效判据是源文件的 `(mtime, size)`，而 **mtime 是秒级的**。
**等长变异**（比较运算符互换天然等长）在同一秒内改完又回退时，
Python 会继续跑缓存的字节码 —— 而 `grep` 与 `inspect.getsource()` **读文件不读字节码，
证明不了任何事**。两个方向都会被骗，其中「造回归后是绿」那个方向是致命的：
它产出一条「我验过了、这道门不设防」的结论，**而验证根本没发生**。

## 判据 2 原本设想的路，走不通

`N-41` 判据 2 写着候选方案是「检测 `sys.dont_write_bytecode` 并在跑变异相关用例时报错」，
并自己警告：**「正在跑变异」这件事测试进程无从知道**，硬做会造出一条永远不触发的规则（`F-2`）。

**那条警告是对的，所以这里不走那条路。**

## 走的是另一条：不去检测，直接让它不可能

与其判断「这一次是不是变异运行」，不如**让任何一次运行都不可能读到陈旧字节码**：

1. `sys.dont_write_bytecode = True` —— 本次会话不再**写**新的 `.pyc`。
2. 会话开始时**删掉 `src/` 下已有的 `__pycache__`** —— 也不可能**读**到旧的。

两条合起来，「陈旧字节码」这个状态在 `src/` 上不存在，
于是它骗不了任何人 —— **包括忘了设那个环境变量的人**。

⚠️ **第 2 条才是要紧的那条。** `dont_write_bytecode` 只管**写**；
真正骗过验证的是**读**到上一轮留下的 `.pyc`。只做第 1 条等于没做。

⚠️ **只清 `src/`，不清 `tests/`。** 变异的对象是产品代码；
测试模块每次由 pytest 重新收集，且清它只会让每次运行更慢而不多挡任何东西。

**代价**：每次运行多花一次 `src/` 的编译（本仓约二十几个模块，相对 70 秒的套件可忽略）。
**换到的是**：`rules/commands.md` 那条「变异测试必须 `PYTHONDONTWRITEBYTECODE=1`」
从**靠人记得**变成**忘了也没关系**。那条规则不删 —— 它仍然管到 pytest 之外的场景
（例如直接 `python -c` 驱动的探针）。
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src"


def _purge_src_bytecode() -> list[str]:
    """删掉 `src/` 下所有 `__pycache__`。返回删掉的目录（供测试断言）。"""
    removed = []
    if SRC.is_dir():
        for cache in sorted(SRC.rglob("__pycache__")):
            shutil.rmtree(cache, ignore_errors=True)
            removed.append(cache.relative_to(REPO).as_posix())
    return removed


# **在收集测试模块之前执行** —— conftest 是 pytest 最先导入的东西，
# 而 `src/` 的模块要到收集/运行时才被 import，所以这两步都赶得上。
sys.dont_write_bytecode = True
PURGED_AT_STARTUP = _purge_src_bytecode()
