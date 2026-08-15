"""非公开数据自动扫描（AC-10 / D-010）。

D-010 把「把非公开数据带进来」定为本项目**唯一不可挽回的错误**，并明确要求
「扫描规则本身也进版本控制」。因此本模块**不做判断，只做执行**——
所有规则在 `scan_rules.yaml` 里，代码读它、跑它、报告结果。
想知道扫什么，看那个文件，不用读这里。

fail-closed：规则文件缺失、解析失败或缺少任一规则组，一律抛错。
「规则读不到就当通过」等于关掉门禁，那比没有门禁更坏，因为它会让人以为有。
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import yaml

__all__ = [
    "ScanRules",
    "ScanFinding",
    "ScanRulesError",
    "load_scan_rules",
    "scan_repository",
    "DEFAULT_RULES_PATH",
]

DEFAULT_RULES_PATH = Path("scan_rules.yaml")

_REQUIRED_GROUPS = (
    "forbidden_tracked_file_types",
    "gitignore_required_entries",
    "content_patterns",
    "semantic_layer_provenance",
)


class ScanRulesError(ValueError):
    """规则文件不可用。fail-closed 的载体：抛出即扫描失败，不降级为通过。"""


@dataclass(frozen=True)
class ScanFinding:
    path: str
    rule: str
    detail: str


@dataclass(frozen=True)
class _ContentPattern:
    rule: str
    regex: re.Pattern
    description: str


@dataclass(frozen=True)
class ScanRules:
    rules_version: int
    forbidden_tracked_file_types: frozenset
    gitignore_required_entries: tuple
    content_patterns: tuple
    organization_tokens: list = field(default_factory=list)
    content_scan_excluded_paths: frozenset = frozenset()
    allowed_statements: tuple = ()
    allowed_field_prefixes: tuple = ()


def load_scan_rules(path: Path | str = DEFAULT_RULES_PATH) -> ScanRules:
    path = Path(path)
    if not path.is_file():
        raise ScanRulesError(f"扫描规则文件不存在：{path}。规则读不到即视为门禁失败，不予放行。")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ScanRulesError(f"扫描规则文件不是合法 YAML：{path}：{exc}") from exc
    if not isinstance(raw, dict):
        raise ScanRulesError(f"扫描规则文件顶层必须是映射：{path}")

    missing = [g for g in _REQUIRED_GROUPS if g not in raw]
    if missing:
        raise ScanRulesError(f"{path}：缺少规则组 {missing}。规则组不全即视为门禁不完整。")

    patterns = []
    for entry in raw["content_patterns"] or []:
        if not isinstance(entry, dict) or "rule" not in entry or "pattern" not in entry:
            raise ScanRulesError(f"{path}：content_patterns 条目须含 rule 与 pattern：{entry!r}")
        try:
            regex = re.compile(entry["pattern"])
        except re.error as exc:
            raise ScanRulesError(f"{path}：正则不合法 {entry['rule']}：{exc}") from exc
        patterns.append(
            _ContentPattern(entry["rule"], regex, str(entry.get("description", "")).strip())
        )

    tokens = raw.get("organization_tokens") or []
    for token in tokens:
        patterns.append(
            _ContentPattern("ORG_TOKEN", re.compile(re.escape(str(token))), f"机构名 token {token!r}")
        )

    prov = raw["semantic_layer_provenance"] or {}
    return ScanRules(
        rules_version=int(raw.get("rules_version", 0)),
        forbidden_tracked_file_types=frozenset(
            str(s).lower() for s in raw["forbidden_tracked_file_types"] or []
        ),
        gitignore_required_entries=tuple(raw["gitignore_required_entries"] or []),
        content_patterns=tuple(patterns),
        organization_tokens=list(tokens),
        content_scan_excluded_paths=frozenset(
            str(p) for p in (raw.get("content_scan_excluded_paths") or [])
        ),
        allowed_statements=tuple(prov.get("allowed_statements") or []),
        allowed_field_prefixes=tuple(prov.get("allowed_field_prefixes") or []),
    )


def _tracked_files(root: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(root), "ls-files"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise ScanRulesError(f"无法列出被跟踪文件（git ls-files 退出 {proc.returncode}）：{proc.stderr.strip()}")
    return [line for line in proc.stdout.splitlines() if line]


def _check_file_types(tracked: list[str], rules: ScanRules) -> list[ScanFinding]:
    out = []
    for rel in tracked:
        suffix = Path(rel).suffix.lower()
        if suffix in rules.forbidden_tracked_file_types:
            out.append(
                ScanFinding(
                    rel,
                    "FILE_TYPE_FORBIDDEN",
                    f"{suffix} 属于被跟踪文件扩展名黑名单；数据文件进仓库必须是显式决策",
                )
            )
    return out


def _check_gitignore(root: Path, rules: ScanRules) -> list[ScanFinding]:
    path = root / ".gitignore"
    lines = (
        {line.strip() for line in path.read_text(encoding="utf-8").splitlines()}
        if path.is_file()
        else set()
    )
    return [
        ScanFinding(
            ".gitignore",
            "GITIGNORE_COVERAGE_LOST",
            f"缺少隔离条目 {entry!r}；非公开数据的物理隔离被削弱（D-010）",
        )
        for entry in rules.gitignore_required_entries
        if entry not in lines
    ]


def _check_content(root: Path, tracked: list[str], rules: ScanRules) -> list[ScanFinding]:
    out = []
    for rel in tracked:
        if rel in rules.content_scan_excluded_paths:
            continue
        target = root / rel
        try:
            text = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue  # 二进制或读不到：内容模式无从适用，交给扩展名黑名单管
        for pattern in rules.content_patterns:
            match = pattern.regex.search(text)
            if match:
                out.append(
                    ScanFinding(
                        rel,
                        pattern.rule,
                        f"命中 {match.group(0)!r}：{pattern.description}",
                    )
                )
    return out


def _check_provenance(root: Path, tracked: list[str], rules: ScanRules) -> list[ScanFinding]:
    """把「这个字段名是从哪来的」变成机器提问：来自公开披露报表的哪一张。"""
    out = []
    for rel in tracked:
        p = Path(rel)
        if p.parent.name != "metrics" or p.suffix != ".yaml" or p.name.startswith("_"):
            continue
        try:
            raw = yaml.safe_load((root / rel).read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue  # 语法非法由 validate 的 R0 报告，不在此重复
        if not isinstance(raw, dict):
            continue
        for entry in raw.get("source_fields") or []:
            if not isinstance(entry, dict):
                continue
            statement = entry.get("statement")
            field_id = entry.get("id")
            if not statement or not any(
                str(statement).startswith(a) for a in rules.allowed_statements
            ):
                out.append(
                    ScanFinding(
                        rel,
                        "STATEMENT_NOT_PUBLIC",
                        f"字段 {field_id!r} 的 statement {statement!r} 不属于公开披露报表受控集"
                        f"{list(rules.allowed_statements)}",
                    )
                )
            prefix = str(field_id).split(".", 1)[0] if field_id else ""
            if prefix not in rules.allowed_field_prefixes:
                out.append(
                    ScanFinding(
                        rel,
                        "FIELD_PREFIX_UNKNOWN",
                        f"字段 {field_id!r} 的根命名空间 {prefix!r} 不属于受控前缀集"
                        f"{list(rules.allowed_field_prefixes)}",
                    )
                )
    return out


def scan_repository(root: Path | str, rules: ScanRules) -> list[ScanFinding]:
    """扫描一个 git 仓库。返回按 (path, rule) 稳定排序的 Finding 列表。

    排序稳定是硬要求：不稳定的话 CI 输出与人工对比会产生纯噪音 diff，
    而噪音会让人停止阅读门禁输出。
    """
    root = Path(root)
    tracked = _tracked_files(root)
    findings = [
        *_check_file_types(tracked, rules),
        *_check_gitignore(root, rules),
        *_check_content(root, tracked, rules),
        *_check_provenance(root, tracked, rules),
    ]
    return sorted(findings, key=lambda f: (f.path, f.rule, f.detail))
