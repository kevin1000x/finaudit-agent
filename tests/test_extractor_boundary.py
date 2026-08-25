"""D-015 判据 2：`semantic_layer` 不得依赖 `extractor`。

**必须走语法树，不得用行首正则。** 这不是风格偏好，是 D-015 里逐字写下的要求，
理由有实证：hello-agents 框架的依赖环**全部藏在函数内 import 与 `TYPE_CHECKING`
块里**（`core/agent.py:49-50,65,70`），行首 `^from|^import` 一个都扫不到
（`references/hello-agents-framework-core.md` §1）。
用 grep 实现这条判据，等于本决策自带一个洞。

检查对象是 `ast.Import` / `ast.ImportFrom` 的**全部出现位置**，
含函数体内、`if TYPE_CHECKING:` 块内、`try` 块内。

**反方向不断言**：`extractor` 引用 `semantic_layer` 是允许的（D-025 也依赖这一点）。
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SEMANTIC_LAYER = REPO / "src" / "semantic_layer"
EXTRACTOR = REPO / "src" / "extractor"

FORBIDDEN_ROOT = "extractor"


def _imported_modules(path: Path) -> list[tuple[int, str]]:
    """这个模块 import 的**全部**模块路径，含嵌套作用域里的。

    `ast.walk` 而不是只看 `tree.body`：藏在函数体、`TYPE_CHECKING` 块、
    `try/except ImportError` 里的 import 都要收进来。
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            # `from . import x` 的 module 是 None；相对 import 不可能跨包指到 extractor
            found.append((node.lineno, node.module or ""))
    return found


def _root_of(module: str) -> str:
    return module.split(".", 1)[0]


def test_语义层的任何模块都不引用抽取器():
    """D-015 判据 2。含函数体内与 TYPE_CHECKING 块内的 import。"""
    files = sorted(SEMANTIC_LAYER.rglob("*.py"))
    assert files, f"{SEMANTIC_LAYER} 下没有 .py，检查路径——扫了个空目录会让这条判据永远绿"

    offenders = []
    for path in files:
        for lineno, module in _imported_modules(path):
            if _root_of(module) == FORBIDDEN_ROOT:
                offenders.append(f"{path.relative_to(REPO).as_posix()}:{lineno} → {module}")
    assert offenders == [], f"语义层反向依赖了抽取器：{offenders}"


def test_遍历确实下降进函数体与_type_checking_块():
    """守卫自身的负控制：证明 `_imported_modules` 看得见藏起来的 import。

    这条不测产品代码，测的是**上面那条判据的检查手段**。
    没有它，`_imported_modules` 哪天退化成只看顶层，上面那条会继续绿。
    """
    source = (
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    from extractor.record import ExtractionRecord\n"
        "def f():\n"
        "    import extractor.download\n"
        "    try:\n"
        "        from extractor import mapping\n"
        "    except ImportError:\n"
        "        mapping = None\n"
    )
    tmp = REPO / "tests" / "_boundary_probe_tmp.py"
    tmp.write_text(source, encoding="utf-8")
    try:
        modules = [m for _, m in _imported_modules(tmp)]
    finally:
        tmp.unlink()
    hidden = [m for m in modules if _root_of(m) == FORBIDDEN_ROOT]
    assert len(hidden) == 3, f"藏起来的 import 没被全部看到：{modules}"


def test_抽取器可以引用语义层():
    """反方向是**允许**的，且实际用上了（D-025 让抽取层复用 RefusalCode）。

    断言它确实发生了，是为了防止有人「为了让边界更干净」把方向也一并禁掉——
    那会逼出一个平行的枚举，正是 D-025 否决的形态。
    """
    files = sorted(EXTRACTOR.rglob("*.py"))
    assert files, f"{EXTRACTOR} 下没有 .py"
    referenced = [
        m
        for path in files
        for _, m in _imported_modules(path)
        if _root_of(m) == "semantic_layer"
    ]
    assert referenced, "抽取器一处都没引用语义层——D-025 的 RefusalCode 复用没落地？"
