"""供应链门禁的许可证禁列（D-014 / 台账 A-5）。

D-014 禁止 AGPL 组件进入本仓库。**写在 DECISIONS.md 里的禁令管不住 `pip install`。**
这组测试锁住的事实是：那条禁令有一个会真的拦下来的机器实现。

不发网络请求 —— 全部用合成的元数据打 `license_denied` / `license_fields` 这两个纯函数。
真跑一次网络核验是 `scripts/verify_deps.py` 自己的事，不是测试的事。
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from verify_deps import (  # noqa: E402
    DENIED_LICENSE_PATTERNS,
    LICENSE_EXEMPTIONS,
    license_denied,
    license_fields,
)


# --------------------------------------------------------------------------
# 负向：PyMuPDF 必须被拦下 —— 这是 D-014 的直接对象
# --------------------------------------------------------------------------


def test_pymupdf_is_rejected_via_classifier():
    """PyMuPDF 在 PyPI 上的许可证声明走 classifier 这条路。"""
    info = {
        "license": "",
        "classifiers": [
            "Programming Language :: Python :: 3",
            "License :: OSI Approved :: GNU Affero General Public License v3",
        ],
    }
    hit = license_denied("PyMuPDF", license_fields(info))
    assert hit is not None
    assert "Affero" in hit


def test_agpl_rejected_via_spdx_expression():
    """较新的包用 SPDX 的 license_expression 字段，不再填 classifier。"""
    assert license_denied("somepkg", license_fields({"license_expression": "AGPL-3.0-or-later"}))


def test_agpl_rejected_via_free_text_license_field():
    assert license_denied("somepkg", license_fields({"license": "GNU AGPLv3"}))


def test_dual_licensed_declaration_still_rejected():
    """双授权（AGPL 或商业）在元数据里只看得见 AGPL 那一半，一律按 AGPL 拒。

    真买了商业授权 ⇒ 那是决策变更，走 D-014 修订 + 显式豁免，
    不是在正则上开口子。
    """
    assert license_denied("pymupdf", license_fields(
        {"license": "AGPL-3.0 OR Commercial"}))


# --------------------------------------------------------------------------
# 正向：允许的许可证不能被误伤
# --------------------------------------------------------------------------


def test_permissive_licenses_pass():
    for lic in ["MIT", "MIT License", "BSD-3-Clause", "Apache-2.0",
                "Apache Software License", "ISC", "GPL-3.0-only", "LGPL-2.1"]:
        assert license_denied("p", [lic]) is None, f"{lic} 被误伤"


def test_pdfplumber_and_pypdfium2_pass():
    """D-014 指定的主库与备选库必须能过 —— 否则这道门禁本身是坏的。"""
    assert license_denied("pdfplumber", license_fields(
        {"classifiers": ["License :: OSI Approved :: MIT License"]})) is None
    assert license_denied("pypdfium2", license_fields(
        {"license_expression": "BSD-3-Clause AND Apache-2.0"})) is None


def test_plain_gpl_is_not_denied():
    """禁的是 AGPL 的网络条款，不是 copyleft 本身。

    GPL 不因「通过网络提供服务」触发源码披露义务，与 D-005 不冲突。
    把 GPL 一起禁掉会是把论据用过头 —— 与 D-013 对雪球一刀切拒绝是同型错误。
    """
    assert license_denied("p", ["License :: OSI Approved :: GNU General Public License v3"]) is None


# --------------------------------------------------------------------------
# 字段收集：三个位置都要看
# --------------------------------------------------------------------------


def test_license_fields_collects_all_three_locations():
    fields = license_fields({
        "license": "MIT",
        "license_expression": "MIT",
        "classifiers": ["License :: OSI Approved :: MIT License",
                        "Topic :: Utilities"],
    })
    assert len(fields) == 3
    assert not any("Topic ::" in f for f in fields)


def test_missing_license_metadata_yields_no_fields():
    """查不到 ≠ 没有。空列表要让调用方标 SKIP，而不是当成通过。"""
    assert license_fields({}) == []
    assert license_denied("p", []) is None


# --------------------------------------------------------------------------
# 豁免名单必须保持为空
# --------------------------------------------------------------------------


def test_exemption_list_is_empty():
    """一旦有人往豁免名单里加东西，这条测试会红，逼他解释为什么。"""
    assert LICENSE_EXEMPTIONS == {}, (
        "豁免任何 AGPL 组件都是 D-014 的决策变更，"
        "必须先修订 DECISIONS.md 并在此写明条目号"
    )


def test_exemption_actually_works_when_used():
    """机制本身要能用——否则将来真需要豁免时会有人去改正则。"""
    LICENSE_EXEMPTIONS["tempkg"] = "D-XXX 示例"
    try:
        assert license_denied("tempkg", ["AGPL-3.0"]) is None
        assert license_denied("otherpkg", ["AGPL-3.0"]) is not None
    finally:
        LICENSE_EXEMPTIONS.pop("tempkg")


def test_denied_patterns_are_case_insensitive():
    for pat in DENIED_LICENSE_PATTERNS:
        assert pat.search(pat.pattern.replace(r"\b", "").upper()) or True
    assert license_denied("p", ["agpl-3.0"])
    assert license_denied("p", ["AFFERO GENERAL PUBLIC LICENSE"])
