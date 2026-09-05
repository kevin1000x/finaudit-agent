"""口径指纹：`D-034` 那条线的机器判据。

## 这条线是什么

2026-09-05 操作者裁 `N-58` 选 (b)：**改给人读的散文不算改口径，`version` 不动。**
那句话立刻带出一个必须回答的问题 —— **「只改了措辞」这句话谁来核？**
frozen-01 的 20 道题把标准答案钉在 `metric_version: 2` 上；
如果有人以「改措辞」为名动了 `formula`，那 20 个标准答案会在没人发现的情况下失效。

⇒ **语义载荷** = 定义文件**去掉三处纯散文**之后的全部内容
（`derivation.note` / `common_pitfalls[].text` / `undefined_conditions[].reason`，
见 `definition.PROSE_PATHS`）。它的 SHA-256 记在 `metrics/_fingerprints.json`。

⚠️ **剔除是按精确路径、白名单式的**：新加的键**默认进指纹**。
反过来做（列一张「语义键」白名单）会让新加的键默认逃出指纹，
那正好是这道门要防的方向。

## 有意的口径变更之后怎么办

**顺序不能反**：先改 `version`，再重算指纹，最后按 `N-46` 处理 frozen-01 ——
那 20 道题的标准答案是钉在旧版本上的，口径一动它们就失效。

重算的具体命令**故意不写在这里**。照着 `metrics/_fingerprints.json` 已有的形状
手写，或者临时跑一段再删掉。**顺手就能重算的门，等于没有门** ——
这道门唯一的作用就是逼一次「我到底改的是措辞还是口径」的自问。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from semantic_layer.definition import (
    PROSE_PATHS,
    fingerprint,
    iter_definition_paths,
    load_definition,
    semantic_payload,
)

REPO = Path(__file__).resolve().parent.parent
METRICS = REPO / "metrics"
TABLE = METRICS / "_fingerprints.json"


QSHA = "sha256"
QVER = "version"

def _table() -> dict:
    return json.loads(TABLE.read_text(encoding="utf-8"))["definitions"]


def test_指纹表覆盖的正好是全部定义_不多不少():
    """漏一份 = 那一份的口径可以被随便改；多一份 = 表里有个已经不存在的东西。"""
    on_disk = {load_definition(p).metric_id for p in iter_definition_paths(METRICS)}
    assert len(on_disk) == 20, f"磁盘上有 {len(on_disk)} 份定义，不是 20"
    assert set(_table()) == on_disk, (
        "指纹表与磁盘对不上："
        f"表里缺 {sorted(on_disk - set(_table()))}，"
        f"表里多 {sorted(set(_table()) - on_disk)}"
    )


def test_每份定义的指纹与版本都对得上表():
    """🔴 `D-034` 的落地判据。

    它会红的场景：有人以「改措辞」为名动了 `formula` / `expr` / `trigger` /
    `source_fields[].id`，而 `version` 没动 —— frozen-01 的 20 个标准答案
    会在没人发现的情况下失效。
    """
    table = _table()
    checked = 0
    bad = []
    for path in iter_definition_paths(METRICS):
        d = load_definition(path)
        want = table.get(d.metric_id)
        assert want is not None, f"{d.metric_id} 不在指纹表里"
        checked += 1
        got = fingerprint(path)
        if got != want["sha256"]:
            bad.append(f"{d.metric_id}：指纹 {want[QSHA][:12]} -> {got[:12]}")
        if d.version != want["version"]:
            bad.append(f"{d.metric_id}：版本 {want[QVER]} -> {d.version}")
    assert checked == 20, f"只查了 {checked} 份，这条断言在空转"
    assert bad == [], (
        "口径指纹或版本与表对不上：" + "；".join(bad) + "。",
        "如果这是有意的口径变更：改 version、重算指纹表、并按 N-46 处理 frozen-01。",
        "如果只是改措辞：那它碰到了 PROSE_PATHS 之外的东西，不算改措辞。",
    )


def test_改散文不动指纹_改公式动指纹(tmp_path):
    """🔴 **负控制，两个方向都验。**

    只有一个方向的话，一个「永远返回同一个常量」的指纹函数也能满足前半条。
    """
    src = (METRICS / "current_ratio.yaml").read_text(encoding="utf-8")
    base = tmp_path / "base.yaml"
    _write(base, src)
    before = fingerprint(base)
    n_pitfalls = len(load_definition(base).common_pitfalls)

    # ① 只改散文（往第一条陷阱的正文里加一句）⇒ 指纹必须不变
    out = []
    injected = False
    seen_pitfalls = False
    for line in src.split(chr(10)):
        out.append(line)
        if line.startswith("common_pitfalls:"):
            seen_pitfalls = True
        elif seen_pitfalls and not injected and line.strip() == "- text: >":
            out.append("      这一句是负控制加的，只改措辞。")
            injected = True
    assert injected, "没找到可注入的陷阱条目，这条会空转"
    prose = tmp_path / "prose.yaml"
    _write(prose, chr(10).join(out))

    改后 = load_definition(prose)
    assert len(改后.common_pitfalls) == n_pitfalls, "注入把陷阱条数改了，那不叫只改措辞"
    assert "负控制加的" in 改后.common_pitfalls[0].text, "散文没真的改动，这条会空转"
    assert fingerprint(prose) == before, "只改散文，指纹却变了 —— D-034 那条线画错了"

    # ② 改公式 ⇒ 指纹必须变
    formula = tmp_path / "formula.yaml"
    改公式 = src.replace("bs.total_current_assets /", "bs.inventory /", 1)
    assert 改公式 != src, "公式那一行没匹配上，这条会空转"
    _write(formula, 改公式)
    assert fingerprint(formula) != before, "改了公式，指纹却没变 —— 这道门是假的"


def _write(path: Path, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline=chr(10)) as fh:
        fh.write(text)


@pytest.mark.parametrize("prose_path", sorted(PROSE_PATHS))
def test_每一条被剔除的路径都真的在语料里存在(prose_path: str):
    """剔除清单里写了一条**根本不存在**的路径 = 那一行什么都没放过，
    却让读的人以为某处散文已经被豁免了。
    """
    keys = [seg for seg in prose_path.replace("[]", "").split(".") if seg]
    leaf = keys[-1]
    hits = 0
    for path in iter_definition_paths(METRICS):
        import yaml

        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        stripped = semantic_payload(path)
        if _has_leaf(raw, leaf) and not _has_leaf(stripped, leaf):
            hits += 1
    assert hits > 0, f"{prose_path} 在 20 份定义里一次都没被剔除过 —— 这一行是死的"


def _has_leaf(node, leaf: str) -> bool:
    if isinstance(node, dict):
        return leaf in node or any(_has_leaf(v, leaf) for v in node.values())
    if isinstance(node, list):
        return any(_has_leaf(v, leaf) for v in node)
    return False
