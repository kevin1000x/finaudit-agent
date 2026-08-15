"""非公开数据自动扫描器（AC-10 / D-010）。

D-010 原话：「这不能只靠自觉。Phase 1 起加入自动扫描（AC-10），扫描规则本身也进版本控制。」
本文件测的就是那条命令。

每个用例在临时 git 仓库里注入一类违规——不在真仓库上造违规，
因为 CLAUDE.md 把「把非公开数据带进来」列为唯一不可挽回的错误，
测试数据也不例外：临时仓库随 tmp_path 消失，不可能被误提交。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from semantic_layer.scan import (  # noqa: E402
    ScanRules,
    load_scan_rules,
    scan_repository,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_RULES_PATH = REPO_ROOT / "scan_rules.yaml"


# --------------------------------------------------------------------------
# 临时仓库夹具
# --------------------------------------------------------------------------

_GITIGNORE = """\
data/raw/
data/private/
data/cache/
.env
"""


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """一个干净的临时仓库：有合规的 .gitignore 与一份合规的定义。"""
    _git(tmp_path, "init", "-b", "main")
    (tmp_path / ".gitignore").write_text(_GITIGNORE, encoding="utf-8")
    metrics = tmp_path / "metrics"
    metrics.mkdir()
    (metrics / "sample.yaml").write_text(
        "metric_id: sample\n"
        "source_fields:\n"
        "  - id: is.operating_revenue_current\n"
        "    statement: 合并利润表\n",
        encoding="utf-8",
    )
    _git(tmp_path, "add", "-A")
    return tmp_path


@pytest.fixture
def rules() -> ScanRules:
    return load_scan_rules(REAL_RULES_PATH)


def _codes(findings) -> set[str]:
    return {f.rule for f in findings}


# --------------------------------------------------------------------------
# 干净基线
# --------------------------------------------------------------------------


def test_clean_repository_yields_no_findings(repo, rules):
    assert scan_repository(repo, rules) == []


def test_real_repository_is_clean(rules):
    """真仓库必须扫得干净——否则本门禁从第一天起就是红的，会被养成忽略的习惯。"""
    findings = scan_repository(REPO_ROOT, rules)
    assert findings == [], f"本仓库扫出 {len(findings)} 项：{[(f.path, f.rule) for f in findings]}"


# --------------------------------------------------------------------------
# 第一组：被跟踪文件的扩展名黑名单
# --------------------------------------------------------------------------


@pytest.mark.parametrize("suffix", [".xlsx", ".pdf", ".csv", ".db", ".sqlite", ".parquet", ".docx"])
def test_tracked_forbidden_file_type(repo, rules, suffix):
    victim = repo / f"leak{suffix}"
    victim.write_bytes(b"whatever")
    _git(repo, "add", "-f", victim.name)
    assert "FILE_TYPE_FORBIDDEN" in _codes(scan_repository(repo, rules))


def test_untracked_forbidden_file_type_is_ignored(repo, rules):
    """只看被 git 跟踪的文件。工作区里放个 xlsx 不算违规——它进不了仓库。"""
    (repo / "scratch.xlsx").write_bytes(b"whatever")
    assert scan_repository(repo, rules) == []


# --------------------------------------------------------------------------
# 第二组：.gitignore 隔离条目
# --------------------------------------------------------------------------


def test_removing_gitignore_entry_is_detected(repo, rules):
    text = (repo / ".gitignore").read_text(encoding="utf-8")
    (repo / ".gitignore").write_text(text.replace("data/private/\n", ""), encoding="utf-8")
    _git(repo, "add", "-A")
    findings = scan_repository(repo, rules)
    assert "GITIGNORE_COVERAGE_LOST" in _codes(findings)
    assert any("data/private/" in f.detail for f in findings)


def test_missing_gitignore_entirely_is_detected(repo, rules):
    _git(repo, "rm", "--cached", ".gitignore")
    (repo / ".gitignore").unlink()
    assert "GITIGNORE_COVERAGE_LOST" in _codes(scan_repository(repo, rules))


# --------------------------------------------------------------------------
# 第三组：内容模式
# --------------------------------------------------------------------------


def test_contact_pattern_detected(repo, rules):
    (repo / "notes.md").write_text("联系人 zhang.san@some-corp.com.cn", encoding="utf-8")
    _git(repo, "add", "-A")
    assert "CONTACT_PATTERN" in _codes(scan_repository(repo, rules))


@pytest.mark.parametrize("host", ["10.20.30.40", "192.168.1.5", "172.16.0.1"])
def test_network_pattern_detected(repo, rules, host):
    (repo / "notes.md").write_text(f"内网地址 {host}", encoding="utf-8")
    _git(repo, "add", "-A")
    assert "NETWORK_PATTERN" in _codes(scan_repository(repo, rules))


def test_public_ip_is_not_flagged(repo, rules):
    """8.8.8.8 不是私网地址，不该命中——误报会让门禁被绕过（T-01-16）。"""
    (repo / "notes.md").write_text("公共 DNS 8.8.8.8", encoding="utf-8")
    _git(repo, "add", "-A")
    assert scan_repository(repo, rules) == []


def test_rules_file_does_not_match_itself(repo, rules):
    """规则文件自身携带模式串，必须自排除，否则它永远命中自己。"""
    (repo / "scan_rules.yaml").write_text(
        REAL_RULES_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    _git(repo, "add", "-A")
    findings = [f for f in scan_repository(repo, rules) if f.path.endswith("scan_rules.yaml")]
    assert findings == []


def test_content_scan_exclusion_list_is_pinned(rules):
    """豁免清单是门禁上的洞，锁死它，让每一次增长都必须改这条测试。

    只有「因为要测试/定义模式串本身，所以必然携带模式串」的文件够格进这个清单。
    """
    assert rules.content_scan_excluded_paths == frozenset(
        {"scan_rules.yaml", "tests/test_scan.py"}
    )


def test_exclusion_only_waives_content_patterns(repo, rules):
    """被豁免的文件仍受其余三组规则约束——豁免的是内容模式，不是整个门禁。"""
    excluded = repo / "scan_rules.yaml"
    excluded.write_text(REAL_RULES_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    (repo / "metrics" / "sample.yaml").write_text(
        "metric_id: sample\n"
        "source_fields:\n"
        "  - id: erp.internal_field\n"
        "    statement: 集团内部管理报表\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    codes = _codes(scan_repository(repo, rules))
    assert {"STATEMENT_NOT_PUBLIC", "FIELD_PREFIX_UNKNOWN"} <= codes


def test_binary_tracked_file_does_not_crash_scanner(repo, rules):
    """非 UTF-8 的被跟踪文件不能让扫描器抛异常——抛了就等于门禁不可用。"""
    (repo / "blob.bin").write_bytes(bytes(range(256)))
    _git(repo, "add", "-A")
    scan_repository(repo, rules)  # 不抛异常即通过


# --------------------------------------------------------------------------
# 第四组：语义层字段来源（本项目特有，D-010 在字段级的落点）
# --------------------------------------------------------------------------


def test_statement_outside_public_set_is_detected(repo, rules):
    (repo / "metrics" / "sample.yaml").write_text(
        "metric_id: sample\n"
        "source_fields:\n"
        "  - id: is.some_field\n"
        "    statement: 集团内部管理报表\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    assert "STATEMENT_NOT_PUBLIC" in _codes(scan_repository(repo, rules))


def test_unknown_field_prefix_is_detected(repo, rules):
    (repo / "metrics" / "sample.yaml").write_text(
        "metric_id: sample\n"
        "source_fields:\n"
        "  - id: erp.customer_margin\n"
        "    statement: 合并利润表\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    assert "FIELD_PREFIX_UNKNOWN" in _codes(scan_repository(repo, rules))


def test_statement_may_narrow_to_a_section(repo, rules):
    """允许在受控报表名之后细化到具体章节。

    真实定义就这么写：`财务报表附注「非经常性损益项目及金额」`。
    受控的是**来自哪张公开报表**，不是不许写得更精确。
    """
    (repo / "metrics" / "sample.yaml").write_text(
        "metric_id: sample\n"
        "source_fields:\n"
        "  - id: notes.nonrecurring_pl_net\n"
        "    statement: 财务报表附注「非经常性损益项目及金额」\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    assert scan_repository(repo, rules) == []


def test_missing_statement_is_detected(repo, rules):
    """漏写 statement 等于答不上「这字段从哪来」，与写了个非公开来源同样不可接受。"""
    (repo / "metrics" / "sample.yaml").write_text(
        "metric_id: sample\nsource_fields:\n  - id: is.some_field\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    assert "STATEMENT_NOT_PUBLIC" in _codes(scan_repository(repo, rules))


def test_vocabulary_file_is_not_scanned_as_definition(repo, rules):
    """metrics/_flags.yaml 不是定义，没有 source_fields，不该被当成缺 statement。"""
    (repo / "metrics" / "_flags.yaml").write_text(
        "vocabulary_version: 1\nflags: []\n", encoding="utf-8"
    )
    _git(repo, "add", "-A")
    assert scan_repository(repo, rules) == []


# --------------------------------------------------------------------------
# fail-closed 与确定性
# --------------------------------------------------------------------------


def test_missing_rules_file_raises(tmp_path):
    """规则读不到就当通过 = 门禁形同虚设。必须抛错。"""
    with pytest.raises(Exception):
        load_scan_rules(tmp_path / "nope.yaml")


def test_unparseable_rules_file_raises(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text('rules_version: 1\nbroken: "unclosed\n', encoding="utf-8")
    with pytest.raises(Exception):
        load_scan_rules(bad)


def test_rules_missing_required_group_raises(tmp_path):
    partial = tmp_path / "partial.yaml"
    partial.write_text("rules_version: 1\nforbidden_tracked_file_types: []\n", encoding="utf-8")
    with pytest.raises(Exception):
        load_scan_rules(partial)


def test_findings_are_stably_sorted(repo, rules):
    (repo / "z.xlsx").write_bytes(b"x")
    (repo / "a.pdf").write_bytes(b"x")
    (repo / "notes.md").write_text("a@b-corp.com 与 10.1.2.3", encoding="utf-8")
    _git(repo, "add", "-fA")
    first = scan_repository(repo, rules)
    second = scan_repository(repo, rules)
    assert first == second
    assert first == sorted(first, key=lambda f: (f.path, f.rule))


# --------------------------------------------------------------------------
# 规则文件本身的结构（D-010：规则要能被人审查）
# --------------------------------------------------------------------------


def test_real_rules_file_shape(rules):
    assert rules.rules_version >= 1
    assert len(rules.allowed_statements) == 6
    assert len(rules.allowed_field_prefixes) == 5
    assert rules.organization_tokens == [], "留空是有意的，待出现真实失效模式后再填"
    assert rules.forbidden_tracked_file_types
    assert set(rules.gitignore_required_entries) >= {
        "data/raw/",
        "data/private/",
        "data/cache/",
        ".env",
    }
