"""`src/agent/` 的边界断言（`02-01` T1，`D-001` / `D-003`）。

🔴 **LLM 只允许出现在意图解析这一段，且必须由调用方注入。**
越过这条线，证据链就不再可复核 —— 答案里会出现一个「模型说的」环节，
而那个环节没有任何东西可以被独立复核。

**必须走语法树，不得用 `in` 子串或行首正则**（`RV-9`：注释就能满足 `in`；
`test_extractor_boundary.py` 头部记着更硬的实证 —— 依赖环整个藏在函数内 import 里）。

⚠️ 本文件断言的是 **`src/agent/` 整个包**，不只是计划点名的 `answer.py` / `gate.py`。
`intent.py` 拿的是**注入进来的可调用对象**，它自己也不该 import 任何客户端。
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
AGENT = REPO / "src" / "agent"

#: 禁止出现在 `src/agent/` 里的顶层模块。`eval.llm_client` 自己的 docstring 明写
#: 「**永远不会**被 `eval/run.py`（系统臂）导入」—— 那条边界在这里同样成立。
FORBIDDEN_ROOTS = {"eval", "openai", "anthropic", "httpx", "requests", "urllib"}


def _imported_modules(path: Path) -> list[tuple[int, str]]:
    """这个模块 import 的**全部**模块路径，含函数体、`TYPE_CHECKING` 与 `try` 块里的。"""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                out.append((node.lineno, a.name))
        elif isinstance(node, ast.ImportFrom):
            # `from . import x` 的 module 是 None；相对 import 不出包，不必查。
            if node.level == 0 and node.module:
                out.append((node.lineno, node.module))
    return out


def test_agent_包不引用任何_llm_客户端或网络库():
    """它会红的场景：有人在 `agent/` 里 `from eval.llm_client import complete`，
    或直接 `import requests` 去调一个模型端点 —— 哪怕写在函数体里。
    """
    files = sorted(AGENT.glob("*.py"))
    assert files, "src/agent/ 下没有模块，这条断言会空转"
    offenders = []
    for path in files:
        for lineno, module in _imported_modules(path):
            if module.split(".")[0] in FORBIDDEN_ROOTS:
                offenders.append(f"{path.name}:{lineno} import {module}")
    assert offenders == [], "agent 包越过了 LLM 边界：" + "; ".join(offenders)


def test_这条断言真的下降进函数体(tmp_path):
    """负控制：把 import 藏进函数体，`_imported_modules` 必须照样看得见。

    没有这一条，上面那条断言可能只是在检查文件头 —— 而实证表明
    依赖环恰恰不写在文件头（见本文件 docstring 引的那条）。
    """
    nl = chr(10)
    f = tmp_path / "藏起来.py"
    f.write_text(
        "def go():" + nl
        + "    from eval.llm_client import complete" + nl
        + "    return complete" + nl,
        encoding="utf-8",
    )
    assert _imported_modules(f) == [(2, "eval.llm_client")]
