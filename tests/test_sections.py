"""章节定位、不可见字符归一化、适用性复选项 —— 全部跑在**抽取产物**上。

固件是 `tests/fixtures/maotai_2023_probe_rows.json`（贵州茅台 600519 · 2023）
与 `tests/fixtures/combination_positive_probe_rows.json`（万华化学 600309 · 2019），
由 `scripts/probe_fields.py` 从真实年报 dump 出来，PDF 本身不进仓库。

**两份固件不是同一个样本的两次拍照，是两种排版**：
茅台的章节序号是 `九、`、子项是 `1、`、六项里只有第 5 项适用；
万华的章节序号是 `八、`、子项是 `1.`、第 1/2/5 项适用。
一条只在其中一份上绿的规则，会被另一份抓住。

本模块的每条断言都对应一个**实测撞出来的**失效模式，出处见
`docs/agent/phase-01.5/PROBE-COMBINATION.md` §3。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from extractor.locate import (
    CHECKBOX_APPLICABLE,
    CHECKBOX_NOT_APPLICABLE,
    ApplicabilityUnreadable,
    applicability_from_lines,
    strip_invisible,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures"
MAOTAI = FIXTURE_DIR / "maotai_2023_probe_rows.json"
WANHUA = FIXTURE_DIR / "combination_positive_probe_rows.json"

#: 「合并范围的变更」六个子项，**不含序号**：序号形态跨公司不一致。
SUBITEMS = (
    "非同一控制下企业合并",
    "同一控制下企业合并",
    "反向购买",
    "处置子公司",
    "其他原因的合并范围变动",
    "其他",
)


def _scope(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))["consolidation_scope"]


def _texts(path: Path) -> list[str]:
    return [line["text"] for line in _scope(path)["lines"]]


# --------------------------------------------------------------------------
# strip_invisible
# --------------------------------------------------------------------------


def test_剔除控制字符后章节标题才匹配得上():
    """顺丰控股 2021 的实测形态：U+0007 夹在「五」与「、」之间。

    这个字符 `print()` 看不见、PDF 阅读器看不见，只有 `repr()` 才暴露。
    不归一化就零命中，而零命中的表现形式与「这家公司确实没披露」**完全不可区分**。
    """
    raw = "五\x07、合并范围的变更"
    assert raw != "五、合并范围的变更"  # 未归一化时确实不相等 —— 这才是问题所在
    assert strip_invisible(raw) == "五、合并范围的变更"


def test_剔除的只有不可见字符_可见的一个都不动():
    """`Cc`/`Cf` 不是可打印字形，剔除它们没去掉任何人能看见的字。

    这条守的是**边界**：一旦有人为了「让匹配更宽松」把空格或标点加进剔除集合，
    两个肉眼可区分的串就会变成同一个 —— 那才是把匹配放松。
    """
    text = "1. 归属于母公司股东的净利润（净亏损以“-”号填列）"
    assert strip_invisible(text) == text


def test_零宽字符与BOM同样被剔除():
    """`Cf` 类覆盖 ZWSP / ZWNJ / BOM，它们比控制字符更常混进 PDF 文本层。"""
    assert strip_invisible("合并​范围﻿的变更") == "合并范围的变更"


# --------------------------------------------------------------------------
# 适用性复选项：两份固件，两种排版
# --------------------------------------------------------------------------


def test_茅台六项_只有第五项适用():
    """`A-8` 记的真实假阴性：企业合并三项全「不适用」，而合并范围**确实变了**。"""
    assert applicability_from_lines(_texts(MAOTAI), SUBITEMS) == {
        "非同一控制下企业合并": False,
        "同一控制下企业合并": False,
        "反向购买": False,
        "处置子公司": False,
        "其他原因的合并范围变动": True,
        "其他": False,
    }


def test_万华正样本_两类企业合并同时适用():
    """`D-020` 判据 3 缺的正样本。

    **同时**为「适用」这件事本身就是结论：`notes.business_combination_type`
    的单值枚举 `['同一控制下','非同一控制下','无']` 装不下它（台账 `N-39`）。
    """
    verdicts = applicability_from_lines(_texts(WANHUA), SUBITEMS)
    assert verdicts["非同一控制下企业合并"] is True
    assert verdicts["同一控制下企业合并"] is True
    assert verdicts["反向购买"] is False
    assert verdicts["处置子公司"] is False
    assert verdicts["其他原因的合并范围变动"] is True
    assert verdicts["其他"] is False


def test_两份固件的子项序号形态确实不同():
    """守住「序号容差」这条规则**有存在理由**。

    如果哪天两份固件的序号变成一样的，上面两个测试即使规则退化成
    「序号写死」也照样绿 —— 那时它们就不再守着任何东西。
    本测试让那个前提失效时当场报红。
    """
    maotai = "\n".join(_texts(MAOTAI))
    wanhua = "\n".join(_texts(WANHUA))
    assert "1、非同一控制下企业合并" in maotai
    assert "1.非同一控制下企业合并" in wanhua
    assert "1.非同一控制下企业合并" not in maotai
    assert "1、非同一控制下企业合并" not in wanhua


def test_章节序号在两份固件里不同():
    """茅台 `九、`、万华 `八、`。把序号写死等于给第二家公司写一条永远零命中的规则。"""
    assert _scope(MAOTAI)["anchor"]["numeral_prefix"] == "九、"
    assert _scope(WANHUA)["anchor"]["numeral_prefix"] == "八、"
    assert _scope(MAOTAI)["anchor"]["title"] == _scope(WANHUA)["anchor"]["title"]


def test_固件未被截断():
    """截断的 dump 与完整的 dump 在产物里长得一模一样 —— 除非把标志传出来。

    初版 `dump_consolidation_scope` 丢掉了 `truncated`，于是万华的固件在
    120 行处被砍断，回放报「找不到后四个子项」，**而真实原因是行数被砍了**。
    """
    assert _scope(MAOTAI)["truncated"] is False
    assert _scope(WANHUA)["truncated"] is False


# --------------------------------------------------------------------------
# 负向：读不出来必须大声失败，不许默认成「不适用」
# --------------------------------------------------------------------------


def test_没有复选行时抛异常而不是默认不适用():
    """顺丰控股 2021 的实测形态：这一节根本没有复选框，直接列交易明细表。

    **若默认成 `False`，一家真发生了 145 亿收购的公司会被记成「本期无企业合并」。**
    """
    texts = [
        "1、非同一控制下企业合并",
        "被购买方名称购买日股权取得成本",
        "嘉里物流及其子公司2021年9月28日14,550,982",
    ]
    with pytest.raises(ApplicabilityUnreadable, match="读不到"):
        applicability_from_lines(texts, ("非同一控制下企业合并",))


def test_子项缺失时拒绝返回部分结果():
    """只填了一半的适用性表，读起来与「其余都不适用」无法区分。"""
    texts = ["1、非同一控制下企业合并", CHECKBOX_APPLICABLE]
    with pytest.raises(ApplicabilityUnreadable, match="找不到子项"):
        applicability_from_lines(texts, SUBITEMS)


def test_子项重复时抛异常():
    texts = [
        "1、反向购买",
        CHECKBOX_NOT_APPLICABLE,
        "1、反向购买",
        CHECKBOX_APPLICABLE,
    ]
    with pytest.raises(ApplicabilityUnreadable, match="不止一次"):
        applicability_from_lines(texts, ("反向购买",))


def test_不适用不会被读成适用():
    """`□适用√不适用` 里也有一个 `√`。

    只看「行里有没有 `√`」会把方向**恰好读反**，且不报任何错。
    两个常量是**整行逐字相等**的判定，这条测试守的就是那个「整行」。
    """
    assert "√" in CHECKBOX_NOT_APPLICABLE  # 反面条件确实成立，测试才有意义
    verdicts = applicability_from_lines(
        ["1、反向购买", CHECKBOX_NOT_APPLICABLE], ("反向购买",)
    )
    assert verdicts["反向购买"] is False


def test_会计政策段落不会被当成子项():
    """茅台 p77 / 万华 p89 都有「同一控制下和非同一控制下企业合并的会计处理方法」。

    那是**会计政策**不是交易事实。两层都挡着：它在章节区间外，
    且剥掉序号后正文也不逐字等于任何子项。本测试守第二层。
    """
    texts = [
        "5.同一控制下和非同一控制下企业合并的会计处理方法",
        CHECKBOX_APPLICABLE,
        "1、反向购买",
        CHECKBOX_NOT_APPLICABLE,
    ]
    verdicts = applicability_from_lines(texts, ("反向购买",))
    assert verdicts == {"反向购买": False}


def test_序号前缀容差不会把任意数字开头的行认成子项():
    """`_SUBITEM_NUMERAL_RE` 剥掉前缀后，正文必须**逐字相等**。

    `3.反向购买业务的会计处理` 比子项多了五个字，不算命中。
    """
    texts = [
        "3.反向购买业务的会计处理",
        CHECKBOX_APPLICABLE,
        "3、反向购买",
        CHECKBOX_NOT_APPLICABLE,
    ]
    assert applicability_from_lines(texts, ("反向购买",)) == {"反向购买": False}
