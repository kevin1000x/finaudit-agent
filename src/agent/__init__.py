"""`src/agent/` —— 把已有的零件串成一条问答路径（Phase 2 `02-01`）。

**这一层不新增任何口径知识。** 口径在 `semantic_layer`，取数在 `extractor`，
本包只负责：把问题解析成三元组（`intent`）、在执行前过闸门（`gate`）、
把结果与证据链拼成可复核的答案（`answer`）。

🔴 **LLM 只允许出现在 `intent` 这一段，且必须由调用方注入。**
`gate` 与 `answer` 连 import 都不许 —— 有一条 AST 断言锁着（`D-001` / `D-003`）。
"""
