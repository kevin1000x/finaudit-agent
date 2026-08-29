"""合并范围变更的复选项读取 —— `D-020` / `D-028` 与 `A-8` 查实的那处真实假阴性。

**这组测试关掉的是一个真实年报上的漏报**（`A-8`）：
`metrics/_flags.yaml` 说 `scope_change` 是「合并范围发生变动」，
而 trigger 挂的是 `notes.business_combination_type != "无"`；
茅台 2023 企业合并三项**全部不适用**，而「其他原因的合并范围变动」**是适用** ——
于是 flag 不置位，**而合并范围确实变了**。

全部用例跑在固件 `tests/fixtures/maotai_2023_notes_scope.json` 上，不下 PDF。
固件里记着它是从哪份 PDF 的哪一段抽出来的（含 SHA-256）。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from extractor.locate import ApplicabilityUnreadable
from extractor.notes import (
    NEXT_SECTION_TITLE,
    SECTION_TITLE,
    SUB_TITLES,
    ScopeChangeItem,
    ScopeChangeReading,
    derive_consolidation_scope_change,
    read_scope_change,
    scope_change_from_lines,
)
from extractor.record import RecordKind

FIXTURE = Path(__file__).parent / "fixtures" / "maotai_2023_notes_scope.json"

#: p77 的会计政策段落 —— **本章节区间之外**，一个字都不许进来。
POLICY_TRAP = "同一控制下和非同一控制下企业合并的会计处理方法"


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _lines() -> list[str]:
    return [row["text"] for row in _fixture()["lines"]]


def _reading() -> ScopeChangeReading:
    fx = _fixture()
    return scope_change_from_lines(
        [row["text"] for row in fx["lines"]],
        anchor_page=fx["anchor_page"],
        page=fx["lines"][0]["page"],
    )


# --------------------------------------------------------------------------
# 一、六项逐项读数（D-020 判据 3 的事实基础）
# --------------------------------------------------------------------------


def test_固件是合法_json_且含六项():
    fx = _fixture()
    assert fx["section_title"] == SECTION_TITLE
    assert fx["next_section_title"] == NEXT_SECTION_TITLE
    reading = _reading()
    assert len(reading.items) == 6
    assert set(reading.items) == set(ScopeChangeItem)


def test_茅台2023六项逐项读数():
    """**逐项断言，不写聚合断言。**

    写成 `assert sum(...) == 1` 之类，任何一项判错都可能被另一项判错抵消掉 ——
    那时测试还是绿的，而两处都错了。
    """
    items = _reading().items
    assert items[ScopeChangeItem.NON_COMMON_CONTROL_COMBINATION] is False
    assert items[ScopeChangeItem.COMMON_CONTROL_COMBINATION] is False
    assert items[ScopeChangeItem.REVERSE_ACQUISITION] is False
    assert items[ScopeChangeItem.SUBSIDIARY_DISPOSAL] is False
    # ↓ 唯一一个「适用」—— 定制营销公司清算注销
    assert items[ScopeChangeItem.OTHER_SCOPE_CHANGE] is True
    assert items[ScopeChangeItem.OTHER] is False


def test_复选行不一定紧跟子项标题():
    """`4、处置子公司` 与它的复选行之间隔着一行

    「本期是否存在丧失子公司控制权的交易或事项」。
    这是实测出来的版面事实，不是假设 —— 若实现改成「取标题的下一行」，本条会红。
    """
    texts = _lines()
    i = texts.index("4、处置子公司")
    assert texts[i + 1] == "本期是否存在丧失子公司控制权的交易或事项"
    assert texts[i + 2] == "□适用√不适用"
    assert _reading().items[ScopeChangeItem.SUBSIDIARY_DISPOSAL] is False


# --------------------------------------------------------------------------
# 二、p77 的会计政策段落 —— 已知陷阱，必须有测试守着
# --------------------------------------------------------------------------


def test_会计政策段落不出现在_raw_lines_里():
    """p77「同一控制下和非同一控制下企业合并的会计处理方法」是**会计政策**，不是交易事实。

    只按关键词匹配会把它算成「发生了企业合并」——
    与 cninfo `extract_financial_statements()`「最后一个匹配的表静默胜出」同型。
    本函数的区间是 `[anchor, next_anchor)`，p77 **在构造上就进不来**。
    """
    reading = _reading()
    assert POLICY_TRAP not in "".join(reading.raw_lines)
    for line in reading.raw_lines:
        assert POLICY_TRAP not in line


def test_固件的行全部落在章节区间内():
    """固件本身也要守住：它是从 `[anchor, next_anchor)` 里抽的，不是全篇搜出来的。"""
    fx = _fixture()
    for row in fx["lines"]:
        assert fx["anchor_page"] <= row["page"] <= fx["next_anchor_page"]
        if row["page"] == fx["anchor_page"]:
            assert row["y"] > fx["anchor_y"]
        if row["page"] == fx["next_anchor_page"]:
            assert row["y"] < fx["next_anchor_y"]


# --------------------------------------------------------------------------
# 三、读不出来时说「不可判定」，不编一个值（D-020 反转触发条件的载体）
# --------------------------------------------------------------------------


class _StubPage:
    def __init__(self, words):
        self._words = words

    def extract_words(self):
        return self._words


class _StubPdf:
    def __init__(self, pages):
        self.pages = pages


def _page_from_texts(texts, start_top=100.0):
    """一行一个词，`top` 逐行递增 —— 够 `_cluster_lines` 聚成独立行。"""
    return _StubPage(
        [
            {"text": t, "top": start_top + i * 20.0, "x0": 10.0}
            for i, t in enumerate(texts)
        ]
    )


def test_锚点不在时判不可判定而不是退回全文搜索():
    """**退回兜底就是把「读不出来」偷偷变成「读出来了一个可能是错的值」。**

    `D-020` 的反转触发条件明写：若六个子项无法可靠判读，
    则改为在证据链里显式记录「该 flag 不可判定」，
    **不得**用一个求不出值的 trigger 冒充规则。`undecidable` 就是那个显式记录。
    """
    texts = [t for t in _lines()]
    # 章节标题本来就不在这些行里（固件是区间内的行），再去掉整章锚点 ⇒ 定位不到
    pdf = _StubPdf([_page_from_texts(texts)])
    reading = read_scope_change(pdf)
    assert reading.undecidable is True
    assert reading.items == {}
    # **没有任何一项被判为「适用」** —— 不可判定不许泄漏出一个 True
    assert derive_consolidation_scope_change(reading) is None
    assert reading.undecidable_reason


def test_标记读不出来时也判不可判定():
    """六项中任何一项既不是「√适用」也不是「□不适用」⇒ `undecidable`。

    ⚠️ 注意它与「读出不适用」是两回事：`applicability_from_lines` 的原话是
    「不取『不适用』作默认 —— 读不出来与读出『不适用』是两回事」。
    """
    texts = [t for t in _lines() if t != "□适用√不适用"]
    reading = scope_change_from_lines(texts, anchor_page=120, page=120)
    assert reading.undecidable is True
    assert reading.items == {}


def test_子项缺一即不可判定而不是返回部分结果():
    """一份只填了一半的适用性表，读起来与「其余都不适用」无法区分。"""
    texts = [t for t in _lines() if not t.startswith("6、其他")]
    reading = scope_change_from_lines(texts, anchor_page=120, page=120)
    assert reading.undecidable is True
    assert reading.items == {}


def test_底层拒绝仍然是异常本身不被吞掉():
    """`scope_change_from_lines` 把 `ApplicabilityUnreadable` 转成 `undecidable`，

    但**转换点只有一处**，且理由进 `undecidable_reason`。
    这一条锁住「理由没丢」——一个只有布尔没有理由的不可判定，复核者无从下手。
    """
    reading = scope_change_from_lines([], anchor_page=1, page=1)
    assert reading.undecidable is True
    assert "找不到子项" in reading.undecidable_reason or reading.undecidable_reason

    with pytest.raises(ApplicabilityUnreadable):
        scope_change_from_lines([], anchor_page=1, page=1, on_unreadable="raise")


# --------------------------------------------------------------------------
# 四、D-020 判据 3：无企业合并但合并范围变动时 flag 会置位
# --------------------------------------------------------------------------


def test_茅台上派生值为真而企业合并类型为空集():
    """🔴 **这一条就是 `A-8` 那处真实假阴性的反面。**

    同一份年报上两个字段取值不同，**这本身就是它们必须是两个字段的证明**：
    - `notes.business_combination_type` = **空集**（1–3 项全不适用 ⇒ 本期无企业合并）
    - `notes.consolidation_scope_change` = **True**（第 5 项适用）

    旧 trigger 挂在前者上 ⇒ 不置位；新 trigger 挂在后者上 ⇒ 置位。
    """
    reading = _reading()
    assert derive_consolidation_scope_change(reading) is True

    from extractor.notes import derive_business_combination_type

    # D-028：集合值，空集 = 本期无企业合并
    assert derive_business_combination_type(reading) == frozenset()


def test_六项里任一为适用即为真_逐项驱动():
    """派生规则是「六项任一为适用」。**逐项各驱动一次**，不是只测那个真实为真的项。

    只测第 5 项的话，把规则写成 `items[OTHER_SCOPE_CHANGE]` 也能过 ——
    那是一条在本样本上正确、在别的公司上必错的实现。
    """
    for item in ScopeChangeItem:
        items = {i: False for i in ScopeChangeItem}
        items[item] = True
        reading = ScopeChangeReading(
            items=items, anchor_page=120, page=120, raw_lines=(), undecidable=False
        )
        assert derive_consolidation_scope_change(reading) is True, item

    none_applies = ScopeChangeReading(
        items={i: False for i in ScopeChangeItem},
        anchor_page=120,
        page=120,
        raw_lines=(),
        undecidable=False,
    )
    assert derive_consolidation_scope_change(none_applies) is False


def test_企业合并类型只由前三项决定():
    """`D-020` 明写 `business_combination_type` **保留原义**，只表企业合并类型。

    后三项（处置子公司 / 其他原因 / 其他）属合并范围变动，**不得**混进来 ——
    混进来就等于用一个字段承载两件事，而 `A-8` 那处漏报正是这么来的。
    """
    from extractor.notes import derive_business_combination_type

    for item in (
        ScopeChangeItem.SUBSIDIARY_DISPOSAL,
        ScopeChangeItem.OTHER_SCOPE_CHANGE,
        ScopeChangeItem.OTHER,
    ):
        items = {i: False for i in ScopeChangeItem}
        items[item] = True
        reading = ScopeChangeReading(
            items=items, anchor_page=120, page=120, raw_lines=(), undecidable=False
        )
        assert derive_business_combination_type(reading) == frozenset()
        assert derive_consolidation_scope_change(reading) is True

    both = {i: False for i in ScopeChangeItem}
    both[ScopeChangeItem.NON_COMMON_CONTROL_COMBINATION] = True
    both[ScopeChangeItem.COMMON_CONTROL_COMBINATION] = True
    reading = ScopeChangeReading(
        items=both, anchor_page=1, page=1, raw_lines=(), undecidable=False
    )
    # D-028 判据 2 的形态：两元素集合。**单值实现下这一条会红。**
    assert derive_business_combination_type(reading) == frozenset(
        {
            ScopeChangeItem.NON_COMMON_CONTROL_COMBINATION,
            ScopeChangeItem.COMMON_CONTROL_COMBINATION,
        }
    )


def test_不可判定时两个派生值都是_None_不是_False():
    """`None` 与 `False` 必须可区分：前者是「判不了」，后者是「判出来没变动」。

    合并成 `False`，一次读不出来会被下游当成「本期合并范围没变」——
    那正是 `flags_status` 那条 `evaluated + 空集 ≠ unevaluable` 的同型问题。
    """
    from extractor.notes import derive_business_combination_type

    reading = ScopeChangeReading(
        items={}, anchor_page=None, page=None, raw_lines=(), undecidable=True,
        undecidable_reason="测试构造",
    )
    assert derive_consolidation_scope_change(reading) is None
    assert derive_business_combination_type(reading) is None


# --------------------------------------------------------------------------
# 五、抽取记录（RecordKind.NOTE_CHECKBOX）
# --------------------------------------------------------------------------


def test_读数里带着页码且都是整数():
    reading = _reading()
    assert isinstance(reading.anchor_page, int)
    assert isinstance(reading.page, int)
    assert reading.anchor_page == 120


# --------------------------------------------------------------------------
# 六、另外两家公司 —— D-028 判据 2 与 D-020 补充节判据 4 的真实样本
# --------------------------------------------------------------------------

WANHUA = Path(__file__).parent / "fixtures" / "wanhua_2019_notes_scope.json"
SF = Path(__file__).parent / "fixtures" / "sf_2021_notes_scope.json"


def _reading_from(path: Path) -> ScopeChangeReading:
    fx = json.loads(path.read_text(encoding="utf-8"))
    return scope_change_from_lines(
        [row["text"] for row in fx["lines"]],
        anchor_page=fx["anchor_page"],
        page=fx["lines"][0]["page"] if fx["lines"] else None,
    )


def test_万华2019是两元素集合_单值实现下这一条会红():
    """🔴 `D-028` 判据 2 的**真实正样本**（不是构造的）。

    万华化学 600309 2019 年报「八、合并范围的变更」里，
    第 1 项（非同一控制下企业合并）与第 2 项（同一控制下企业合并）
    **同时为「√适用」**。

    而 `metrics/minority_interest_share.yaml` 原来的 `enum_values` 是
    `['同一控制下', '非同一控制下', '无']` —— **单值三选一，没有一个是对的**。
    `D-028` 的原话：**集合性在世界里，不在重载里。**

    ⚠️ 顺带注意序号：茅台排 `九、`、万华排 `八、`。
    序号跨公司会变，写死序号等于给第二家公司写了一条永远零命中的规则（`C-2`）。
    """
    reading = _reading_from(WANHUA)
    assert reading.undecidable is False

    from extractor.notes import derive_business_combination_type

    combination = derive_business_combination_type(reading)
    assert combination == frozenset(
        {
            ScopeChangeItem.NON_COMMON_CONTROL_COMBINATION,
            ScopeChangeItem.COMMON_CONTROL_COMBINATION,
        }
    )
    # **两个元素**——任何单值表示都装不下它
    assert len(combination) == 2
    assert reading.items[ScopeChangeItem.NON_COMMON_CONTROL_COMBINATION] is True
    assert reading.items[ScopeChangeItem.COMMON_CONTROL_COMBINATION] is True
    # 反向购买仍然零正样本，如实锁住现状
    assert reading.items[ScopeChangeItem.REVERSE_ACQUISITION] is False


def test_万华2019的合并范围也变动了_但理由与茅台不同():
    """两家公司都 `scope_change = True`，**路径完全不同**：

    - 茅台：企业合并三项全不适用，靠第 5 项（清算注销）
    - 万华：第 1、2 项就适用，本身就发生了企业合并

    锁住这一点是为了防止实现退化成「只看第 5 项」——
    那在茅台上正确，在万华上也碰巧正确（万华第 5 项也适用），
    **但理由是错的**。所以这里逐项断言而不是只看派生值。
    """
    reading = _reading_from(WANHUA)
    assert derive_consolidation_scope_change(reading) is True
    assert reading.items[ScopeChangeItem.OTHER_SCOPE_CHANGE] is True
    assert reading.items[ScopeChangeItem.SUBSIDIARY_DISPOSAL] is False


def test_顺丰2021不用复选框模板_判不可判定而不是返回_False():
    """🔴 `D-020` 补充节判据 4 的**真实反例**。

    顺丰控股 002352 2021 年报有「合并范围的变更」这一章（p250 定位得到），
    **但整节没有复选框模板** —— 六个子项一个都不在。

    ⇒ 正确处置是「判不了」，**不是「六项都不适用」**。
    返回 `False` 会让下游读成「本期合并范围没变」，
    而事实是我们根本没读到这个信息。**披露模板不是普遍格式。**
    """
    reading = _reading_from(SF)
    assert reading.undecidable is True
    assert reading.items == {}
    assert derive_consolidation_scope_change(reading) is None

    from extractor.notes import derive_business_combination_type

    assert derive_business_combination_type(reading) is None
    assert "找不到子项" in reading.undecidable_reason


def test_顺丰2021要异常时给异常():
    """`on_unreadable="raise"` 这条路径在真实样本上也要成立，不只在空输入上。"""
    fx = json.loads(SF.read_text(encoding="utf-8"))
    with pytest.raises(ApplicabilityUnreadable):
        scope_change_from_lines(
            [row["text"] for row in fx["lines"]],
            anchor_page=fx["anchor_page"],
            page=fx["lines"][0]["page"],
            on_unreadable="raise",
        )


def test_顺丰2021的章节标题里夹着不可见控制字符():
    """🔴 这是 `C-1` 的**现场证据**，不是理论风险。

    顺丰 p250 的章节标题，`extract_words` 取出来是 `'五\x07、合并范围的变更'` ——
    「五」与「、」之间夹着一个 **U+0007（BEL）**。
    它在任何打印输出里都看不见，`print()` 看不见，肉眼对照 PDF 也看不见。

    逐字相等匹配会**静默零命中**，而零命中的表现形式是
    「这份年报里找不到『合并范围的变更』这一节」—— 与「这家公司确实没披露」
    **在输出上完全不可区分**。

    锚点仍然定位成功（p250），**靠的就是 `strip_invisible` 在比对前把它剔掉**。
    """
    fx = json.loads(SF.read_text(encoding="utf-8"))
    printed = fx["printed_text"]
    assert "\x07" in printed, "固件里应当留着原始控制字符（留证用原文）"
    assert printed != "五、合并范围的变更"

    from extractor.locate import strip_invisible

    assert strip_invisible(printed) == "五、合并范围的变更"
    # 锚点确实定位到了 —— 控制字符没能让它零命中
    assert fx["anchor_page"] == 250
    assert fx["section_title"] == SECTION_TITLE
