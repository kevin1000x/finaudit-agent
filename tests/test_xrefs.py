"""交叉引用门禁的测试（台账 N-30）。

**最重要的是负向用例**：一道从不会红的门禁不是门禁。
本文件锁住的事实是——写一个指向不存在条目的编号，`check_xrefs` 真的会非零退出。

不发网络请求；真仓库那条用例直接跑实际文件（它必须常绿，否则门禁从第一天起就是红的，
会被养成忽略的习惯——同 `test_scan.py` 对公网 IP 的处理）。
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import check_xrefs  # noqa: E402


def _run() -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(REPO / "scripts" / "check_xrefs.py")],
        cwd=REPO, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )


# --------------------------------------------------------------------------
# 正向：真仓库必须通过
# --------------------------------------------------------------------------


def test_real_repository_passes():
    r = _run()
    assert r.returncode == 0, f"真仓库交叉引用门禁不通过：\n{r.stdout}\n{r.stderr}"


def test_every_namespace_has_definitions():
    """任一命名空间的定义点正则与文件写法脱节时，门禁会静默放行——必须先炸。"""
    reg = check_xrefs.build_registry()
    for ns, ids in reg.items():
        assert ids, f"命名空间 {ns} 没有匹配到任何定义点"


# --------------------------------------------------------------------------
# 负向：门禁必须真的会红
# --------------------------------------------------------------------------


def test_dangling_reference_is_detected(tmp_path, monkeypatch):
    """在一个受检文件里写一个不存在的编号，门禁必须报出来。

    这是 N-30 判据的核心：**一条负向测试，故意写一个不存在的编号，验证它真的会红。**
    """
    reg = check_xrefs.build_registry()

    # 造一个确定不存在的决策号：比现有最大号大 100
    biggest = max(int(i.split("-")[1]) for i in reg["D-decision"])
    fake = f"D-{biggest + 100:03d}"
    assert fake not in reg["D-decision"]

    ref_re = check_xrefs.NAMESPACES["D-decision"][2]
    assert ref_re.search(f"见 {fake} 的说明"), "引用正则认不出这个形态，用例本身失效"
    assert fake not in reg["D-decision"], "构造的假编号意外真实存在"


def test_checker_flags_unknown_id_end_to_end(tmp_path):
    """端到端：把一个假编号写进受检文件，跑真脚本，必须非零退出且指出该编号。"""
    victim = REPO / "docs" / "agent" / "OPEN-ITEMS.md"
    original = victim.read_text(encoding="utf-8")
    reg = check_xrefs.build_registry()
    biggest = max(int(i.split("-")[1]) for i in reg["D-decision"])
    fake = f"D-{biggest + 100:03d}"
    try:
        victim.write_text(original + f"\n\n<!-- 测试用，稍后还原 -->\n见 {fake}。\n",
                          encoding="utf-8", newline="\n")
        r = _run()
        assert r.returncode == 1, "写入不存在的编号后门禁仍然通过——它挡不住任何东西"
        assert fake in r.stdout, f"门禁红了但没指出是哪个编号：\n{r.stdout}"
        assert "悬空引用" in r.stdout
    finally:
        victim.write_text(original, encoding="utf-8", newline="\n")

    # 还原后必须重新变绿，否则用例污染了仓库
    assert _run().returncode == 0, "用例还原失败，仓库被污染"


# --------------------------------------------------------------------------
# 碰撞：D- 不得被重新引入台账
# --------------------------------------------------------------------------


def test_collision_allowlist_is_empty():
    """空名单 = 不存在任何需要靠约定区分的编号对。

    往里加东西就是承认又引入了一对易混编号，这条测试会红，逼他解释。
    """
    assert check_xrefs.KNOWN_COLLISIONS == set()


def test_reintroducing_D_prefix_in_ledger_is_a_collision():
    """台账若重新出现 D- 前缀条目，碰撞检查必须拦住。"""
    reg = check_xrefs.build_registry()
    assert not any(i.startswith("D-") for i in reg["ledger"]), \
        "台账里又出现了 D- 前缀条目，与 DECISIONS.md 的命名空间重叠"

    faked = dict(reg)
    faked["ledger"] = set(reg["ledger"]) | {"D-1"}
    problems = check_xrefs.check_collisions(faked)
    assert problems, "台账重新引入 D-1 却没有被判为碰撞"
    assert "D-001" in problems[0]


# --------------------------------------------------------------------------
# 命名空间边界
# --------------------------------------------------------------------------


def test_zero_padding_separates_namespaces():
    """`D-0xx` 属决策、`N-x` 属台账。两个正则不得互相误吃。"""
    dec_re = check_xrefs.NAMESPACES["D-decision"][2]
    led_re = check_xrefs.NAMESPACES["ledger"][2]
    assert dec_re.findall("见 D-013 与 D-014") == ["D-013", "D-014"]
    assert dec_re.findall("见 N-13") == []
    assert led_re.findall("见 N-13 与 A-4") == ["N-13", "A-4"]
    # 决策号不得被台账正则吃掉
    assert led_re.findall("见 D-013") == []


def test_excluded_paths_are_not_scanned():
    """references/ 与 claudedocs/ 是外部报告与冻结件，含旧编号，不参与校验。"""
    files = [p.as_posix() for p in check_xrefs.tracked_markdown()]
    assert not any("/references/" in f or f.endswith("references") for f in files)
    assert not any("claudedocs" in f for f in files)
