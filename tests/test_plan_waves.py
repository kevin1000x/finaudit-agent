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

## 扫描范围（2026-09-05 扩大，`N-42` 的第 8 处）

本文件此前把 `PHASE_DIR` **硬编码为 `.planning/phases/01.5-data-ingestion`**，
glob 也写死 `01.5-0*-PLAN.md`。于是它锁的那个不变式明明对每个阶段都成立，
**而 Phase 0 / 1 / 2 的 PLAN 一份都没有被检查过** —— 门禁一直是绿的，
因为它根本没看那三个目录。实测：改之前扫 **7 / 17** 份，改之后 **17 / 17**。

这正是 `N-42` 那一族：**一道门禁的「绿」只对它的视野成立，
而视野的缺口不会以红的形式表现出来，它表现为一切正常。**
⇒ 扫描范围现在由 `.planning/phases/` 的目录列表决定，不由任何硬编码常量决定；
`test_每个阶段目录都进了扫描范围` 把这一点单独锁住。
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ROADMAP = REPO_ROOT / ".planning" / "ROADMAP.md"
PHASES_DIR = REPO_ROOT / ".planning" / "phases"

#: ROADMAP 条目的起始行，形如 `- [x] 01.5-03-PLAN.md — …`。
#: 阶段号可以带小数（`01.5`），所以不是一句 `\d+`。
_ROADMAP_ENTRY_RE = re.compile(r"^- \[[ x]\] (\d+(?:\.\d+)?-\d+)-PLAN\.md")

#: 条目块里的 wave 标注。**不要求 `）` 紧跟在数字后面** ——
#: `02-03` 写的是 `（wave 3，**H2 判定门**）`，旧正则 `（wave (\d)）` 匹配不到它。
_ROADMAP_WAVE_RE = re.compile(r"（wave (\d+)")

#: PLAN frontmatter 里的三个字段。
_FRONTMATTER_WAVE_RE = re.compile(r"^wave:\s*(\d+)\s*$", re.M)
_FRONTMATTER_PLAN_RE = re.compile(r"^plan:\s*(\d+)\s*$", re.M)
_FRONTMATTER_PHASE_RE = re.compile(r"^phase:\s*(\S+)\s*$", re.M)


def _plan_paths() -> list[Path]:
    """**全部**阶段目录下的 PLAN。扫描范围本身就是判据的一部分。

    ⚠️ 不要退回成「某个阶段目录 + 写死编号前缀」的写法：那正是
    2026-09-05 修掉的那个缺口，见模块 docstring。
    """
    return sorted(PHASES_DIR.glob("*/*-PLAN.md"))


def _key(path: Path) -> str:
    """`01.5-05-PLAN.md` → `01.5-05`。"""
    return path.name[: -len("-PLAN.md")]


def _roadmap_entries() -> dict[str, tuple[bool, int | None]]:
    """ROADMAP 里每个 PLAN 条目的 `(是否已勾选, wave)`。

    **按条目块解析，不用一个跨条目的非贪婪正则。** 旧写法是
    `(01\\.5-0\\d)-PLAN\\.md(.*?)（wave (\\d)）` 配 `re.S`：某个条目忘了写 wave 标注时，
    `.*?` 会一路吃到**下一个条目**的标注，把别人的 wave 号安在它头上 ——
    一个解析器悄悄编出一个不存在的事实，比解析失败更糟。
    这里改成：条目起始行 + 其后所有缩进的续行 = 一个块，只在块内找 wave。
    """
    entries: dict[str, tuple[bool, int | None]] = {}
    lines = ROADMAP.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        m = _ROADMAP_ENTRY_RE.match(line)
        if not m:
            continue
        block = [line]
        for nxt in lines[i + 1:]:
            if not nxt.startswith((" ", "\t")):
                break
            block.append(nxt)
        wave = _ROADMAP_WAVE_RE.search("\n".join(block))
        entries[m.group(1)] = (line.startswith("- [x]"), int(wave.group(1)) if wave else None)
    return entries


def _roadmap_waves() -> dict[str, int]:
    return {k: w for k, (_, w) in _roadmap_entries().items() if w is not None}


def _plan_waves() -> dict[str, int]:
    out: dict[str, int] = {}
    for path in _plan_paths():
        text = path.read_text(encoding="utf-8")
        match = _FRONTMATTER_WAVE_RE.search(text)
        assert match, f"{path.name} 的 frontmatter 里没有 wave:"
        out[_key(path)] = int(match.group(1))
    return out


def test_每个阶段目录都进了扫描范围():
    """🔴 **本条锁的是「视野」本身，不是视野里的内容**（`N-42` 第 8 处）。

    基准集合是 `.planning/phases/` 的**目录列表** —— 它独立于被检查物
    （PLAN 文件与 ROADMAP 文本），符合 `pitfalls` 第 19 条。
    哪天有人把扫描窄回某一个阶段，下面几条测试仍然全绿，只有这一条会红。

    ⚠️ 这条红了不要往这里加豁免。一个阶段目录里有 PLAN 却不该被检查，
    是**规则变更**，得先说清为什么这个不变式对它不成立。
    """
    phase_dirs = sorted(p.name for p in PHASES_DIR.iterdir() if p.is_dir())
    assert len(phase_dirs) >= 4, f"只看到 {phase_dirs}，`.planning/phases/` 可能被挪走了"

    covered = {p.parent.name for p in _plan_paths()}
    missing = [d for d in phase_dirs if d not in covered]
    assert not missing, (
        f"这些阶段目录一份 PLAN 都没进扫描范围：{missing}。"
        "若它们确实没有 PLAN，`test_阶段目录里的PLAN份数与磁盘一致` 会说明；"
        "若有而没扫到，说明 glob 又被窄化了。"
    )


def test_阶段目录里的PLAN份数与磁盘一致():
    """自证扫描没有静默退化成空集或子集。

    基准是 `rglob`（**不经过本文件那个 glob**），两者必须逐个路径相等。
    """
    deep = sorted(p for p in PHASES_DIR.rglob("*-PLAN.md"))
    assert _plan_paths() == deep, (
        f"扫描集合 {[p.name for p in _plan_paths()]} 与递归基准 "
        f"{[p.name for p in deep]} 不同 —— 有 PLAN 落在扫不到的层级上"
    )
    assert len(deep) >= 17, f"只找到 {len(deep)} 份 PLAN，磁盘上应当不少于 17 份"


def test_门禁自身没有失效_两侧都解析到了东西():
    """先证明两侧都还能解析到东西。

    正则与文档写法脱节时，下面那条相等断言会因为**两边都是空 dict** 而通过 ——
    那是一道恒绿的门。`check_xrefs.py` 对定义点做过同样的自证，理由相同。
    """
    roadmap = _roadmap_waves()
    plans = _plan_waves()
    assert len(plans) >= 17, f"PLAN 侧只解析到 {len(plans)} 条：{sorted(plans)}"
    assert len(roadmap) >= 17, f"ROADMAP 侧只解析到 {len(roadmap)} 条，正则可能与写法脱节"


def test_每份磁盘上的PLAN都在ROADMAP里带wave标注():
    """覆盖方向是**单向**的，两侧不对称，这不是偷懒。

    - 磁盘上有 PLAN 而 ROADMAP 没标注 ⇒ **红**。一份没进路线图的计划，
      `N-43` 已经演示过它会被人凭文件名瞎推断。
    - ROADMAP 有条目而磁盘上没有文件 ⇒ 只在它**已勾选**时红。
      未勾选的是「还没写」，那是路线图的正常用法（当前 `02-02/03/04` 就是）。

    旧写法是 `set(roadmap) == set(plans)`，在只看一个阶段时恰好成立；
    扫全部阶段之后它会因为「路线图跑在前面」而恒红 —— **那时正确的修法是
    把规则说清楚，不是把 02-02/03/04 从路线图里删掉让它变绿。**
    """
    entries = _roadmap_entries()
    plans = _plan_waves()

    unannotated = sorted(k for k in plans if entries.get(k, (False, None))[1] is None)
    assert not unannotated, (
        f"这些 PLAN 在 `.planning/ROADMAP.md` 里没有「（wave N）」标注：{unannotated}。"
        "标注是判据的另一半，缺了这一半就只剩文件名可推断。"
    )

    ghosts = sorted(k for k, (done, _) in entries.items() if done and k not in plans)
    assert not ghosts, (
        f"ROADMAP 把这些条目勾成已完成，但磁盘上找不到对应的 PLAN 文件：{ghosts}。"
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
    numbers = {k: int(k.rsplit("-", 1)[1]) for k in plans}
    diverging = {k for k in plans if numbers[k] != plans[k]}
    assert diverging, (
        "现在每份 PLAN 的编号都等于它的 wave 号。"
        "本条测试存在的理由是防止「文件编号就是 wave 号」这个约定悄悄复活 —— "
        "若这确实是有意为之，请删掉本条并在提交信息里写明理由。"
    )
    # 具体是哪一份，写死。改动它需要有人明确意识到自己在改 wave 划分。
    # ⚠️ 扫描面扩大之后 `diverging` 里会有一堆（`01-03` 起整个 Phase 1 都不等），
    # **不要因此把下面三条删掉换成「反正有很多」** —— 它们钉的是 `N-43` 那个具体病例。
    assert "01.5-05" in diverging
    assert plans["01.5-05"] == 4, "01.5-05 属于 wave 4，不是 wave 5"
    assert plans["01.5-06"] == 5, "wave 5 是 01.5-06（收口），不是 01.5-05"


def test_plan_字段与文件名一致():
    """顺带锁住 frontmatter 的 `plan:` 与文件名 —— 这一个**应当**相等。"""
    paths = _plan_paths()
    assert paths, "一份 PLAN 都没扫到"
    for path in paths:
        text = path.read_text(encoding="utf-8")
        match = _FRONTMATTER_PLAN_RE.search(text)
        assert match, f"{path.name} 的 frontmatter 里没有 plan:"
        assert int(match.group(1)) == int(_key(path).rsplit("-", 1)[1]), path.name


def test_phase_字段与所在目录一致():
    """一份 PLAN 放错目录时，上面几条仍然全绿 —— 它的 key 只来自文件名。

    ⇒ 单独锁 frontmatter 的 `phase:` 与目录名。这是扫全部阶段之后才有意义的一条：
    只看一个目录时它恒真。
    """
    paths = _plan_paths()
    assert paths, "一份 PLAN 都没扫到"
    for path in paths:
        match = _FRONTMATTER_PHASE_RE.search(path.read_text(encoding="utf-8"))
        assert match, f"{path.name} 的 frontmatter 里没有 phase:"
        assert match.group(1) == path.parent.name, (
            f"{path.name} 声称 phase: {match.group(1)}，却放在 {path.parent.name}/ 下"
        )


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
