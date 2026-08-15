"""全局受控 flag 词表的加载。

词表全局唯一，指标只能引用不能自造（PROJECT_SPEC.md §5.1）。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

__all__ = ["Flag", "Vocabulary", "load_vocabulary", "DEFAULT_VOCABULARY_PATH"]

DEFAULT_VOCABULARY_PATH = Path("metrics") / "_flags.yaml"

_SCOPES = frozenset({"definition", "system"})

# 五个键都是必需的（spec R4 / PROJECT_SPEC.md §5.1）。
#
# 这里必须 fail-closed，理由在 affects_comparability 上：它此前 `entry.get(..., False)`
# 静默补默认值，于是漏写该键的 flag 会被当成「不影响可比性」——
# 一个本该阻断跨期比较的标记**悄悄不阻断，且不报错**。
# 与 POC-01 的 C4（符号约定未声明 → 方向性错误且不触发任何 undefined 条件）同型，
# 正是本项目声称要消灭的静默错误。见 docs/agent/phase-01/open-questions.md OQ-02。
_REQUIRED_KEYS = ("name", "description", "scope", "affects_comparability", "introduced_by")


@dataclass(frozen=True)
class Flag:
    name: str
    description: str
    scope: str
    affects_comparability: bool
    introduced_by: str


@dataclass(frozen=True)
class Vocabulary:
    vocabulary_version: int
    flags: dict[str, Flag]

    def __contains__(self, name: str) -> bool:
        return name in self.flags

    def scope_of(self, name: str) -> str | None:
        flag = self.flags.get(name)
        return flag.scope if flag else None

    @property
    def definition_scoped(self) -> set[str]:
        return {n for n, f in self.flags.items() if f.scope == "definition"}

    @property
    def system_scoped(self) -> set[str]:
        return {n for n, f in self.flags.items() if f.scope == "system"}


def load_vocabulary(path: Path | str = DEFAULT_VOCABULARY_PATH) -> Vocabulary:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path}：词表顶层必须是映射")
    entries = raw.get("flags") or []
    flags: dict[str, Flag] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"{path}：第 {index + 1} 个 flag 条目不是映射：{entry!r}")
        missing = [k for k in _REQUIRED_KEYS if k not in entry]
        if missing:
            raise ValueError(
                f"{path}：flag {entry.get('name', f'#{index + 1}')!r} 缺少必需键 {missing}。"
                "五个键缺一即拒绝加载——补默认值会让漏写变成静默错误（OQ-02）。"
            )
        scope = entry["scope"]
        if scope not in _SCOPES:
            raise ValueError(
                f"{path}：flag {entry['name']!r} 的 scope {scope!r} 不在 {sorted(_SCOPES)} 内"
            )
        if not isinstance(entry["affects_comparability"], bool):
            raise ValueError(
                f"{path}：flag {entry['name']!r} 的 affects_comparability 必须是布尔值，"
                f"实际是 {entry['affects_comparability']!r}"
            )
        flag = Flag(
            name=entry["name"],
            description=entry["description"],
            scope=scope,
            affects_comparability=entry["affects_comparability"],
            introduced_by=entry["introduced_by"],
        )
        flags[flag.name] = flag
    return Vocabulary(vocabulary_version=int(raw.get("vocabulary_version", 0)), flags=flags)
