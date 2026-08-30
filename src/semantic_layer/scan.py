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
    """**已跟踪**的文件。用于 `forbidden_tracked_file_types`。

    ⚠️ **这里用「已跟踪」是对的，不要改成 `--others`**（2026-08-31 核过）：
    那条规则禁的是「`.pdf` 被**纳入版本控制**」，而**未跟踪的 PDF 是设计的一部分**
    —— `data/raw/*.pdf` 本来就该躺在工作树里不进库（台账 `N-3`）。
    换成 `--others` 会把它们全报成违规，**修一个漏报制造一堆误报**。
    """
    return _git_ls(root, ["--cached"])


def _scannable_files(root: Path) -> list[str]:
    """内容扫描的对象：**已跟踪 + 未跟踪但未被忽略**。

    与 `_tracked_files` 分开是 `N-42` 的处置（2026-08-31）：
    `AC-10` 问的是「仓库内有没有非公开数据」，而一份**刚写完还没 `git add`** 的
    markdown 里的邮箱地址，裸 `git ls-files` **看不见** ——
    门禁绿、随后 `git add -A && git commit`，数据就进库了。
    第一道门（`check_xrefs`）已于 2026-08-28 因同一形态修过，本函数是同型修复。

    `--exclude-standard` 让 `.gitignore` 里的东西（含 `data/raw/*.pdf`）仍然不进扫描面。
    """
    return _git_ls(root, ["--cached", "--others", "--exclude-standard"])


def _git_ls(root: Path, flags: list[str]) -> list[str]:
    """`git ls-files -z`，**NUL 分隔**。

    ⚠️ **`-z` 不是可选的。** 不加时 git 按 `core.quotepath`（默认 true）
    把非 ASCII 路径**转义成 `"å..."` 这种形式**并加引号 ——
    拿它去 `open()` 必然找不到文件，于是**那个文件静默地不被扫描**。
    与 `N-42` 是同一族：门禁看不见的东西，在证据里与「不存在」不可区分。
    本仓当前没有非 ASCII 文件名，所以这条一直没有表现出来 ——
    2026-08-31 写 `N-42` 回归测试时用了一个中文文件名，当场炸出来。
    `-z` 顺带也把带空格 / 换行的路径一并解决了。
    """
    proc = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", *flags],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise ScanRulesError(f"无法列出被跟踪文件（git ls-files 退出 {proc.returncode}）：{proc.stderr.strip()}")
    return [line for line in proc.stdout.split(chr(0)) if line]


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
    # **两个集合，各用各的**（`N-42` 的处置）：
    # 「哪些文件不许进版本控制」问的是已跟踪；
    # 「仓库里有没有非公开数据」问的是工作树上会被提交的一切。
    scannable = _scannable_files(root)
    findings = [
        *_check_file_types(tracked, rules),
        *_check_gitignore(root, rules),
        *_check_content(root, scannable, rules),
        *_check_provenance(root, scannable, rules),
    ]
    return sorted(findings, key=lambda f: (f.path, f.rule, f.detail))
