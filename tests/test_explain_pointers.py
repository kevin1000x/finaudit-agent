"""「由哪一条把关」指向的东西，读者必须在同一页上找得到（`N-68` 第 2 条）。

盲审复核者**照着指引翻回去扑空三次**。去查了一遍，扑空有三种不同的形状，
`enforced_by` 在 20 份定义里出现 89 次，其中 28 次落在这三种上：

| 形状 | 出现次数 | 毛病 |
|---|---|---|
| `derivation.note` | 11 | 内容渲染了，**但标签叫错**：它被渲染成「加总范围说明」，
  而 `inventory_turnover_days` 的这段 note 讲的是天数基数取 365。
  读者去找「加总范围」，找到的是 365，于是判定这条引用指错了地方 |
| `source_fields.sign_convention` | 8 | `_source_lines()` 的文档字符串自己写着
  「**只用 `line_item` 与 `statement`**」⇒ 符号约定**一个字都没渲染**到页面上 |
| `derivation.allow_from_components` | 9 | 正文只渲染 `derivation.note`，
  这条声明同样**从没出现在页面上** |

⚠️ **指向空处的指引比没有指引更糟** —— 没有指引，读者知道自己得自己判断；
指向空处，读者会以为是自己没找到。

本文件钉的是「指到的东西在不在页面上」，**不钉措辞**。措辞变了不该红。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from semantic_layer.definition import iter_definition_paths, load_definition
from semantic_layer.explain import _resolve_ref, render_explanation

REPO = Path(__file__).resolve().parent.parent
METRICS = REPO / "metrics"


def _all_definitions():
    return [load_definition(p) for p in iter_definition_paths(METRICS)]


@pytest.mark.parametrize("path", iter_definition_paths(METRICS), ids=lambda p: p.stem)
def test_每条把关引用指向的取值都出现在正文里(path):
    """`enforced_by` 指向 `source_fields.<key>` / `derivation.<key>` 时，
    **那个键的取值必须出现在正文里**，否则读者翻回去是空的。

    这条是机械可判的，所以它比「读起来清不清楚」更适合当门。
    """
    defn = load_definition(path)
    body = render_explanation(defn)

    for pitfall in defn.common_pitfalls:
        ref = pitfall.enforced_by
        if not ref:
            continue

        if ref.startswith("source_fields."):
            key = ref.split(".", 1)[1]
            if key == "id":
                # ⚠️ `source_fields.id` 指的是「列出来的**那几行**」，不是字段标识符本身 ——
                # 标识符按 `D-032` 本来就不许出现在正文里。所以这一支只要求
                # 这一节确实有内容；要求 `bs.inventory` 出现在页面上是判反了方向。
                assert _source_section(body).strip(), (
                    f"{path.stem}：「{ref}」指向「取数出处」那一节，而这一节是空的"
                )
                continue
            values = {
                getattr(sf, key, None)
                for sf in defn.source_fields
                if getattr(sf, key, None)
            }
            if not values:
                continue  # 该栏在这份定义里全为空，另有一条测试管它
            # 🔴 **只在「取数出处」那一节里找。** 第一版在整页里找，
            # 结果 `绝对值列报` 在**抱怨它的那条陷阱正文里**被找到，测试变绿 ——
            # 而复核者翻的正是这一节。在整页里找等于把要测的那件事绕开了。
            section = _source_section(body)
            assert any(
                _rendered_somehow(v, section) for v in values
            ), f"{path.stem}：「{ref}」指向的取值 {sorted(values)} 没渲染进「取数出处」那一节"

        if ref == "derivation.allow_from_components":
            assert isinstance(defn.derivation, dict) and "allow_from_components" in defn.derivation
            assert _allow_declaration_rendered(body), (
                f"{path.stem}：「{ref}」指向的「能不能由分项推导」这条声明没渲染到正文里"
            )


def _rendered_somehow(value: str, body: str) -> bool:
    """取值可能被换成中文再渲染，所以不要求逐字相等。

    判据放松到「取值本身，或它去掉下划线之后的样子，出现在正文里」——
    严到逐字会把一次合理的中文化判成红。
    """
    # ⚠️ 折行后再比：中文可以在任意两字之间断开，且断处没有连字符提示，
    #    所以逐字比对会把一次纯排版变化判成红。
    #    两边都要压平：`line_item` 自己带着「短期借款 —— 期末余额」这样的空格，
    #    只压正文不压取值，比出来的红是假的。
    flat = "".join(body.split())
    text = "".join(str(value).split())
    return text in flat or text.replace("_", "、") in flat


def _allow_declaration_rendered(body: str) -> bool:
    """🔴 **只在「这是什么」那一节里找。**

    第一版在整页里找「由分项」，摘掉声明之后测试**照样绿** —— 因为
    「由哪一条把关： 上面「这是什么」里关于「能不能由分项推导」的声明」
    这一行**标签自己就含这几个字**。那等于用指针本身证明了它指到的东西存在。
    """
    head, _, _ = body.partition("什么时候不给答案")
    return "由分项" in head or "分项加总" in head


def _source_section(body: str) -> str:
    """把「取数出处」那一节单独切出来。

    切法：从标题行往下收缩进的行，遇到空行停 —— 与渲染器的排版一致。
    切不出来就返回空串，让断言红在「这一节根本不存在」上。
    """
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if "取数出处（" in line:
            out = []
            for nxt in lines[i + 1 :]:
                if not nxt.strip():
                    break
                out.append(nxt)
            return "\n".join(out)
    return ""


def test_derivation_note的标签不许把它叫成一个更窄的名字():
    """🔴 这是复核者三次扑空里最难查的一次 —— **内容在，名字不对**。

    `derivation.note` 是这份定义的口径说明，里面写什么由定义自己决定：
    `inventory_turnover_days` 写的是天数基数取 365，
    `quick_ratio` 写的是本定义只扣存货。**都不是「加总范围」。**

    把一个通用槽位叫成它某一次的内容，等于替读者预判了他要找什么。
    """
    defn = load_definition(METRICS / "inventory_turnover_days.yaml")
    label = _resolve_ref(defn, "derivation.note")
    assert "加总范围" not in label, (
        "`derivation.note` 不是「加总范围说明」：这份定义的 note 讲的是天数基数取 365。"
        f"当前标签：{label!r}"
    )
    # 反方向也要钉：不能因此改成一个指不出位置的空话
    assert "这是什么" in label, "标签仍须指出它在哪一节，否则读者照样找不到"


def test_符号约定在取数出处那一节看得见():
    """8 条 `enforced_by: source_fields.sign_convention` 的落点。

    ⚠️ 这一节此前**只渲染 `line_item` 与 `statement`**（它的文档字符串写着），
    所以「上面「取数出处」里各行的符号约定」指向的是一片不存在的东西。
    """
    defn = load_definition(METRICS / "quick_ratio.yaml")
    body = render_explanation(defn)
    section = _source_section(body)
    assert section, "「取数出处」那一节切不出来"
    assert "绝对值列报" in section, "存货按绝对值列报这条符号约定必须渲染进这一节"
    # 不许把 schema 里的下划线枚举名原样打给财务读者（`D-032`）
    assert "收益记正_损失记负" not in body
