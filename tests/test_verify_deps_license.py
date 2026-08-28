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
    SKIPPED_CHECKS,
    check_download_floor,
    download_floor,
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
    # ⚠️ 2026-08-28 删掉了这里原有的一行 `assert pat.search(...) or True` ——
    # `X or True` **恒为真**，那一行任何输入都不会红，是一条假断言。
    # 第六道门没抓到它，因为同一个函数里还有两条真断言（它查的是
    # 「有没有一个能失败的断言」，不是「每一条断言都能失败」）。
    # ⇒ 这是 `check_gates.py` 的一处已知盲区的实例，已记进登记册。
    assert DENIED_LICENSE_PATTERNS, "禁列不能是空的，否则下面两条断言在保护一个空规则集"
    assert license_denied("p", ["agpl-3.0"])
    assert license_denied("p", ["AFFERO GENERAL PUBLIC LICENSE"])


# --------------------------------------------------------------------------
# 跳过的检查必须看得见（D-030 判据 2 的保护）
# --------------------------------------------------------------------------


def _drain_skips():
    """每条用例自己清干净——`SKIPPED_CHECKS` 是模块级的。"""
    SKIPPED_CHECKS.clear()


def test_下载量取不到时登记进跳过清单而不是静默放行():
    """🔴 2026-08-28 实测撞到的真实情形：pypistats 一次 429。

    此前的行为是：行级打一句 `[SKIP]`，然后总结行照样只写「供应链门禁：通过」。
    一次「全部检查都跑了且都过了」与一次「有检查根本没跑，剩下的过了」
    在退出码上相同、在最后一行上也相同 —— 而它们是两件事。
    """
    _drain_skips()

    def _boom(*args, **kwargs):
        raise RuntimeError("HTTP Error 429: Too Many Requests")

    assert check_download_floor("akshare", fetch=_boom) is True  # 不据此拦截
    assert SKIPPED_CHECKS == ["akshare:下载量"]
    _drain_skips()


def test_门槛被下调过的包在检查跳过时也要把下调说出来(capsys):
    """**输出不许在检查没跑的时候反而更干净。**

    「这个包跑在一条被放低的门槛上」不会因为门槛没被检查而不再成立 ——
    恰恰相反，那是最该说出来的时刻，因为 `D-030` 判据 2 这一次根本没有生效。
    """
    _drain_skips()
    floor, lowered = download_floor("akshare")
    assert lowered is not None, "本用例的前提是 akshare 确实是被下调过的那一个"

    def _boom(*args, **kwargs):
        raise RuntimeError("429")

    check_download_floor("akshare", fetch=_boom)
    out = capsys.readouterr().out
    assert "门槛是被下调过的" in out
    assert "D-030" in out
    assert "没有验证它是否仍在门槛之上" in out
    _drain_skips()


def test_没被下调过的包跳过时不打下调声明(capsys):
    """负向：别把这句话打在每个包上，那样它会退化成噪音。"""
    _drain_skips()
    assert download_floor("pdfplumber")[1] is None

    def _boom(*args, **kwargs):
        raise RuntimeError("429")

    check_download_floor("pdfplumber", fetch=_boom)
    out = capsys.readouterr().out
    assert "[SKIP]" in out
    assert "门槛是被下调过的" not in out
    _drain_skips()


def test_下载量低于门槛时仍然是红的(capsys):
    """`D-030` 判据 2 的正面：掉下去照样红。跳过机制没有把这条弄丢。"""
    _drain_skips()
    floor, _ = download_floor("akshare")
    low = {"data": {"last_month": floor - 1}}
    assert check_download_floor("akshare", fetch=lambda *a, **k: low) is False
    assert SKIPPED_CHECKS == [], "红不是跳过，不许进跳过清单"
    assert "低于门槛" in capsys.readouterr().out
    _drain_skips()


def test_门槛之上时把下调理由打进输出(capsys):
    """一次「门槛被放低后通过」与一次「本来就够」在输出上必须可区分。"""
    _drain_skips()
    floor, _ = download_floor("akshare")
    high = {"data": {"last_month": floor + 1}}
    assert check_download_floor("akshare", fetch=lambda *a, **k: high) is True
    out = capsys.readouterr().out
    assert "门槛已下调至" in out
    assert "D-030" in out
    _drain_skips()
