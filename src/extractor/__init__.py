"""年报 PDF 抽取器。与 `semantic_layer` 平级的普通包（D-015）。

**依赖方向单向**：本包可以 import `semantic_layer`；`semantic_layer` 的任何模块
不得 import 本包。该约束由 `tests/test_extractor_boundary.py` 的 AST 遍历强制，
不靠自觉——D-015 判据 2 明写「必须走 AST，不得用行首正则」。

**本决策不构成 U-03（内核与壳的边界）的提前拍板。**
"""

from __future__ import annotations

__all__: list[str] = []
