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
    for entry in entries:
        scope = entry.get("scope")
        if scope not in _SCOPES:
            raise ValueError(
                f"{path}：flag {entry.get('name')!r} 的 scope {scope!r} 不在 {sorted(_SCOPES)} 内"
            )
        flag = Flag(
            name=entry["name"],
            description=entry.get("description", ""),
            scope=scope,
            affects_comparability=bool(entry.get("affects_comparability", False)),
            introduced_by=entry.get("introduced_by", ""),
        )
        flags[flag.name] = flag
    return Vocabulary(vocabulary_version=int(raw.get("vocabulary_version", 0)), flags=flags)
