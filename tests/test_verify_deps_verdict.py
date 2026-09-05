"""供应链门禁的**判词**：三态，不是两态（`N-44` 2026-09-05 处置）。

## 病例（真实，2026-09-04）

同一天、同一份代码、同一个仓库，前后脚两次运行给出相反结论：

| 第几次 | akshare 下载量 | 门禁末行 | 退出码 |
|---|---|---|---|
| 第一次 | 2,974,120（**低于门槛**） | 「供应链门禁：不通过」 | 1 |
| 第二次（几分钟后） | 读不到（`HTTPError`）⇒ SKIP | 「供应链门禁：**通过**」 | 0 |

🔴 **抖动偏向放行** —— 一个已经跌破的事实被上游的不稳定洗成了「通过」。

## 改的是判词，不是退出码

「未生效」的退出码仍然是 0，这是**有意的**：让 pypistats 的一次 429 把门禁变红，
会得到一道「红的原因不是它要查的那件事」的门，而长期红着的门等于没有门。
⇒ 「哑与绿在退出码上不可区分」这一条**仍然成立**，如实记在 `N-44`，没有假装解决。
本文件盯的是**末行那个词**不再撒谎。
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import verify_deps as vd  # noqa: E402

WATCHED = "akshare:下载量"


def test_全跑了全过才叫通过():
    verdict, code, lines = vd.summarize([True, True, True], [])
    assert verdict == "通过"
    assert code == 0
    assert lines == ["供应链门禁：通过"]


def test_有检查判失败就是不通过():
    verdict, code, _ = vd.summarize([True, False, True], [])
    assert verdict == "不通过"
    assert code == 1


def test_没失败但有检查没跑到_不许叫通过():
    """🔴 **这条是 `N-44` 那个病例的直接回归。**

    它会红的场景：有人把三态改回两态（`"通过" if all(results) else "不通过"`）——
    那正是 2026-09-04 那次把「读不到」洗成「通过」的那一行。
    """
    verdict, code, lines = vd.summarize([True, True], [WATCHED])
    assert verdict == "未生效", f"有检查没跑到却叫「{verdict}」"
    assert "通过" not in lines[0].split("（")[0], "末行的判词里仍然出现了「通过」"
    # 退出码**故意不变** —— 理由见本文件 docstring 与 SKIPPED_CHECKS 的注释
    assert code == 0


def test_跳过的若是_D030_盯着的那一项_要单独打红字():
    """「这一次判据根本没有生效」最要紧的场合，就是它被盯着的那一项跳过的时候。"""
    assert WATCHED.split(":")[0] in vd.DOWNLOAD_THRESHOLD_OVERRIDES, (
        "akshare 不在下调门槛清单里了，本条要重新看"
    )
    _, _, lines = vd.summarize([True, True], [WATCHED])
    joined = "\n".join(lines)
    assert "D-030" in joined
    assert "没有生效" in joined


def test_跳过的不是被盯着的那一项时_不打那行红字():
    """反向：否则那行红字会出现在每一次 429 上，很快没人看。

    没有这一条，一个「永远打红字」的实现也能满足上面那条。
    """
    _, _, lines = vd.summarize([True, True], ["pyyaml:下载量"])
    joined = "\n".join(lines)
    assert "未生效" in joined
    assert "D-030" not in joined


def test_失败与跳过同时发生时_失败优先():
    """读到一个真失败**并且**有别的检查没跑到 ⇒ 仍然是「不通过」。

    反过来（判成「未生效」）会把一个真实的红洗成一句「这次没跑全」。
    """
    verdict, code, lines = vd.summarize([False, True], [WATCHED])
    assert verdict == "不通过"
    assert code == 1
    # 跳过仍然要说出来，不因为已经红了就省掉
    assert "未跑" in lines[0]
