"""口径定义的加载与结构化（PROJECT_SPEC.md §5.1 字段集）。

刻意保持「宽加载、严校验」：本模块不拒绝任何结构，缺什么留什么为 None，
判定合规与否全部交给 validate.py。这样校验器才能对残缺定义给出逐条 Finding，
而不是在加载阶段就抛异常、只能报告第一个错误。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

__all__ = [
    "SIGN_CONVENTIONS",
    "PERIOD_TYPES",
    "PERIOD_SEMANTICS",
    "SourceField",
    "StandardBasis",
    "FlagDecl",
    "UndefinedCondition",
    "Pitfall",
    "MetricDefinition",
    "load_definition",
    "iter_definition_paths",
    "is_definition_file",
    "PROSE_PATHS",
    "semantic_payload",
    "fingerprint",
]

SIGN_CONVENTIONS = frozenset({"收益记正_损失记负", "绝对值列报"})
PERIOD_TYPES = frozenset({"annual", "semi_annual", "quarterly"})
PERIOD_SEMANTICS = frozenset({"时点", "时段", "混合"})


@dataclass
class SourceField:
    id: str | None = None
    statement: str | None = None
    line_item: str | None = None
    sign_convention: str | None = None
    missing_representation: Any = None
    enum_values: list | None = None
    declares_missing_representation: bool = False
    raw: dict = field(default_factory=dict)


@dataclass
class StandardBasis:
    name: str | None = None
    issuer: str | None = None
    article: str | None = None
    version: str | None = None
    raw: Any = None


@dataclass
class FlagDecl:
    name: str | None = None
    trigger: str | None = None


@dataclass
class UndefinedCondition:
    expr: str | None = None
    reason: str | None = None


@dataclass
class Pitfall:
    text: str | None = None
    enforced_by: str | None = None
    advisory_only: bool = False
    declares_advisory: bool = False


@dataclass
class MetricDefinition:
    path: Path
    parse_error: str | None = None
    metric_id: str | None = None
    display_name: str | None = None
    aliases: list = field(default_factory=list)
    version: Any = None
    grain: dict | None = None
    source_fields: list = field(default_factory=list)
    formula: str | None = None
    period_semantics: str | None = None
    derivation: Any = None
    standard_basis: list = field(default_factory=list)
    flags: list = field(default_factory=list)
    declares_flags_key: bool = False
    undefined_conditions: list = field(default_factory=list)
    common_pitfalls: list = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    @property
    def source_field_ids(self) -> set[str]:
        return {sf.id for sf in self.source_fields if sf.id}


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def load_definition(path: Path | str) -> MetricDefinition:
    """宽加载：YAML 语法错误不抛异常，记录成 parse_error 交给校验器报告。

    这条不是洁癖。POC-01 的 `revenue_growth_yoy.yaml` 就是一份语法非法的 YAML
    （2026-08-15 由本校验器首次发现），而它是 SHA 冻结、不可修改的历史样本。
    加载阶段抛异常会让整个校验流程在它面前中断，什么都报不出来。
    """
    path = Path(path)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        where = f"第 {mark.line + 1} 行" if mark is not None else "位置未知"
        return MetricDefinition(
            path=path,
            parse_error=f"{where}：{getattr(exc, 'problem', str(exc))}",
        )
    if not isinstance(raw, dict):
        raw = {}

    source_fields = []
    for entry in _as_list(raw.get("source_fields")):
        if not isinstance(entry, dict):
            source_fields.append(SourceField(raw={}))
            continue
        source_fields.append(
            SourceField(
                id=entry.get("id"),
                statement=entry.get("statement"),
                line_item=entry.get("line_item"),
                sign_convention=entry.get("sign_convention"),
                missing_representation=entry.get("missing_representation"),
                enum_values=entry.get("enum_values"),
                declares_missing_representation="missing_representation" in entry,
                raw=entry,
            )
        )

    standard_basis = []
    for entry in _as_list(raw.get("standard_basis")):
        if isinstance(entry, dict):
            standard_basis.append(
                StandardBasis(
                    name=entry.get("name"),
                    issuer=entry.get("issuer"),
                    article=entry.get("article"),
                    version=str(entry["version"]) if entry.get("version") is not None else None,
                    raw=entry,
                )
            )
        else:
            standard_basis.append(StandardBasis(raw=entry))

    flags = [
        FlagDecl(name=e.get("name"), trigger=e.get("trigger"))
        for e in _as_list(raw.get("flags"))
        if isinstance(e, dict)
    ]

    undefined_conditions = [
        UndefinedCondition(expr=e.get("expr"), reason=e.get("reason"))
        if isinstance(e, dict)
        else UndefinedCondition(expr=None, reason=str(e))
        for e in _as_list(raw.get("undefined_conditions"))
    ]

    pitfalls = []
    for entry in _as_list(raw.get("common_pitfalls")):
        if isinstance(entry, dict):
            pitfalls.append(
                Pitfall(
                    text=entry.get("text"),
                    enforced_by=entry.get("enforced_by"),
                    advisory_only=bool(entry.get("advisory_only", False)),
                    declares_advisory="advisory_only" in entry,
                )
            )
        else:
            pitfalls.append(Pitfall(text=str(entry)))

    return MetricDefinition(
        path=path,
        metric_id=raw.get("metric_id"),
        display_name=raw.get("display_name"),
        aliases=_as_list(raw.get("aliases")),
        version=raw.get("version"),
        grain=raw.get("grain") if isinstance(raw.get("grain"), dict) else None,
        source_fields=source_fields,
        formula=raw.get("formula"),
        period_semantics=raw.get("period_semantics"),
        derivation=raw.get("derivation"),
        standard_basis=standard_basis,
        flags=flags,
        declares_flags_key="flags" in raw,
        undefined_conditions=undefined_conditions,
        common_pitfalls=pitfalls,
        raw=raw,
    )


def is_definition_file(path: Path | str) -> bool:
    """这份文件是不是一份**指标定义**。

    下划线开头的是共享注册表（`_flags.yaml`），不是定义。
    2026-09-04 之前这条规则只活在 `iter_definition_paths` 里，
    而 `explain` 自己拼路径绕开了它 —— 于是同一个目录两个入口读法不一致，
    `explain _flags` 退 0 并渲染出一份每节都空的「定义」。
    规则提到这里，是为了让它只有一个落点。
    """
    return not Path(path).name.startswith("_")


def iter_definition_paths(metrics_dir: Path | str = "metrics") -> list[Path]:
    """metrics/ 下的定义文件。下划线开头的（如 _flags.yaml）不是定义。"""
    directory = Path(metrics_dir)
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.glob("*.yaml") if is_definition_file(p))

# --------------------------------------------------------------------------
# 口径指纹（`D-034`）
# --------------------------------------------------------------------------

#: 定义文件里**纯粹给人读**的三处散文。改这三处**不算改口径**，`version` 不动。
#: 判据不是「读起来像不像散文」，而是**这三条精确路径**——
#: 靠感觉划线，下一个人就会把 `formula` 也划进来。
#:
#: ⚠️ 用**路径**不用键名：某天有人加一个语义上要紧、恰好也叫 `text` 的键，
#: 按键名剔除会把它一起放掉，而这份指纹就是用来防这件事的。
PROSE_PATHS: frozenset = frozenset({
    "derivation.note",
    "common_pitfalls[].text",
    "undefined_conditions[].reason",
})


def _strip_prose(node, path: str = ""):
    """按 `PROSE_PATHS` 剔除散文，其余原样保留。**默认保留** ——
    新加的键会自动进指纹，要放它出去必须显式往 `PROSE_PATHS` 里写一行。
    """
    if isinstance(node, dict):
        out = {}
        for key, value in node.items():
            child = f"{path}.{key}" if path else key
            if child in PROSE_PATHS:
                continue
            out[key] = _strip_prose(value, child)
        return out
    if isinstance(node, list):
        return [_strip_prose(v, path + "[]") for v in node]
    return node


def semantic_payload(path: Path | str) -> dict:
    """一份定义里**除散文之外的全部内容**。

    这是 `D-034` 那条线的机器判据：改动只碰散文 ⇒ 本函数的返回值逐字节不变。
    """
    import yaml

    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return _strip_prose(raw)


def fingerprint(path: Path | str) -> str:
    """口径指纹 = 语义载荷的 SHA-256（规范化 JSON，键排序、非 ASCII 不转义）。

    ⚠️ **它不替代人的判断**，它只保证「我只改了措辞」这句话是可核的：
    指纹变了而 `version` 没变 ⇒ `tests/test_definition_fingerprint.py` 红。
    """
    import hashlib
    import json

    blob = json.dumps(
        semantic_payload(path), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
