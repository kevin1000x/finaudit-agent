"""PLAN 的 `wave` 声明必须与 ROADMAP 的标注一致 —— `N-43`（2026-08-28 实测撞出来的）。

## 这条测试存在的理由

**`01.5-0X` 与 `wave X` 是两个东西，而它们在 01…04 上恰好相等。**

真实的对应关系是：

| PLAN | wave |
|---|---|
| `01.5-01` … `01.5-04` | 1 … 4（**编号与 wave 恰好相同**） |
| `01.5-05` | **4**（wave 4 有两份 PLAN） |
| `01.5-06` | **5** |

于是「文件编号就是 wave 号」这个约定**在前四份上成立，第五份开始不成立**，
而在它不成立的那一刻，**没有任何东西会说出来**。

后果是真实发生过的：交接文档、`STATE.md`、以及若干处代码注释都把
`01.5-05` 称作「wave 5」，进而把「wave 5 要做三支 `kind`」这个说法
安在了一份**根本没写那件事**的计划上。排查花掉的时间远超写这条测试的时间。

## 它属于本项目反复记的哪一类

**一个靠巧合成立的约定，与一个被验证过的约定，在成立期间完全不可区分。**
这与 `pitfalls` 第 19 条（覆盖检查的基准集合必须独立于被检查物）同族：
此处「被检查物」是文件名，而它恰好等于要检查的那个值，于是检查退化成恒真。

⇒ 判据只能来自**两个独立的声明**：PLAN 自己的 frontmatter，与 ROADMAP 的标注。
两者对不上即红。**不许从文件名推断任何一个。**
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ROADMAP = REPO_ROOT / ".planning" / "ROADMAP.md"
PHASE_DIR = REPO_ROOT / ".planning" / "phases" / "01.5-data-ingestion"

#: ROADMAP 里形如 `01.5-03-PLAN.md — …（wave 3）` 的标注。
_ROADMAP_RE = re.compile(r"(01\.5-0\d)-PLAN\.md(.*?)（wave (\d)）", re.S)

#: PLAN frontmatter 里的 `wave: N`。
_FRONTMATTER_WAVE_RE = re.compile(r"^wave:\s*(\d+)\s*$", re.M)
_FRONTMATTER_PLAN_RE = re.compile(r"^plan:\s*(\d+)\s*$", re.M)


def _roadmap_waves() -> dict[str, int]:
    text = ROADMAP.read_text(encoding="utf-8")
    return {m.group(1): int(m.group(3)) for m in _ROADMAP_RE.finditer(text)}


def _plan_waves() -> dict[str, int]:
    out: dict[str, int] = {}
    for path in sorted(PHASE_DIR.glob("01.5-0*-PLAN.md")):
        text = path.read_text(encoding="utf-8")
        match = _FRONTMATTER_WAVE_RE.search(text)
        assert match, f"{path.name} 的 frontmatter 里没有 wave:"
        out[path.name[: len("01.5-0X")]] = int(match.group(1))
    return out


def test_门禁自身没有失效_两侧都解析到了东西():
    """先证明两个正则都还能匹配到东西。

    正则与文档写法脱节时，下面那条相等断言会因为**两边都是空 dict** 而通过 ——
    那是一道恒绿的门。`check_xrefs.py` 对定义点做过同样的自证，理由相同。
    """
    roadmap = _roadmap_waves()
    plans = _plan_waves()
    assert len(roadmap) >= 6, f"ROADMAP 侧只解析到 {len(roadmap)} 条，正则可能与写法脱节"
    assert len(plans) >= 6, f"PLAN 侧只解析到 {len(plans)} 条"
    assert set(roadmap) == set(plans), (
        f"两侧覆盖的 PLAN 不同：ROADMAP {sorted(roadmap)} / 文件 {sorted(plans)}"
    )


def test_每份_plan_的_wave_与_roadmap_标注一致():
    """**两个独立声明必须对得上。** 对不上即红，不替任何一方选一个。"""
    roadmap = _roadmap_waves()
    plans = _plan_waves()
    mismatched = {k: (plans[k], roadmap[k]) for k in plans if plans[k] != roadmap[k]}
    assert not mismatched, (
        "PLAN frontmatter 与 ROADMAP 标注不一致（PLAN, ROADMAP）："
        f"{mismatched}。两者是同一事实的两个独立声明，分叉了必须先查清楚哪个对。"
    )


def test_文件编号不等于_wave_号这件事被锁住():
    """🔴 **本条是这组测试的核心。**

    它断言的不是「编号等于 wave」，恰恰相反：断言**至少有一份 PLAN 的编号与 wave 不等**。

    为什么要锁住一个「不相等」：如果哪天所有 PLAN 都恰好编号 == wave，
    上面两条测试仍然全绿，而「文件编号就是 wave 号」这个**错误约定**
    会重新变得看起来正确 —— 然后下一个人又会照它推断。

    这条测试的作用是让那个约定**永远无法悄悄复活**：
    真要变成全部相等，得有人来删掉这条测试并解释为什么。
    """
    plans = _plan_waves()
    numbers = {k: int(k.split("-")[1]) for k in plans}
    diverging = {k for k in plans if numbers[k] != plans[k]}
    assert diverging, (
        "现在每份 PLAN 的编号都等于它的 wave 号。"
        "本条测试存在的理由是防止「文件编号就是 wave 号」这个约定悄悄复活 —— "
        "若这确实是有意为之，请删掉本条并在提交信息里写明理由。"
    )
    # 具体是哪一份，写死。改动它需要有人明确意识到自己在改 wave 划分。
    assert "01.5-05" in diverging
    assert plans["01.5-05"] == 4, "01.5-05 属于 wave 4，不是 wave 5"
    assert plans["01.5-06"] == 5, "wave 5 是 01.5-06（收口），不是 01.5-05"


def test_plan_字段与文件名一致():
    """顺带锁住 frontmatter 的 `plan:` 与文件名 —— 这一个**应当**相等。"""
    for path in sorted(PHASE_DIR.glob("01.5-0*-PLAN.md")):
        text = path.read_text(encoding="utf-8")
        match = _FRONTMATTER_PLAN_RE.search(text)
        assert match, f"{path.name} 的 frontmatter 里没有 plan:"
        assert int(match.group(1)) == int(path.name.split("-")[1]), path.name


def test_STATE的frontmatter是合法yaml():
    """🔴 **2026-09-02 实测：它此前不是。**

    `.planning/STATE.md` 的 frontmatter 是 GSD 声称要机读的那份状态，
    而 `last_activity_desc` 的值以 `**` 开头 —— **YAML 会把 `*` 当成 alias 起始**，
    整段 frontmatter 因此解析失败。**这个状态在 HEAD 上已经存在，没有任何门禁解析过它。**

    ⇒ 一份「机读的状态文件」从来没有被机读过，与 `N-42` 是同一族：
    **没有人看的东西，坏了和好着在证据上不可区分。**

    ⚠️ 这条红了**不要把 frontmatter 里的强调号删掉了事** ——
    正确的修法是给值加引号；措辞是内容，引号是语法。
    """
    import yaml

    text = (REPO_ROOT / ".planning" / "STATE.md").read_text(encoding="utf-8")
    assert text.startswith("---"), "STATE.md 开头不是 frontmatter"
    front = text.split("---")[1]
    data = yaml.safe_load(front)   # 不合法就在这里抛
    assert isinstance(data, dict), "frontmatter 解析出来不是映射"
    for key in ("current_phase", "status", "last_updated"):
        assert key in data, f"frontmatter 缺 {key}"
