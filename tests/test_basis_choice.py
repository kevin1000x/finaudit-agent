"""`metrics/_basis_choice.yaml` 这张表守得住什么（`N-84` / `D-045`）。

## 这张表为什么需要门禁

它直接决定核查层的判定：标了 `true` 的指标，用户写出它的**正式名**也会被判
「口径未声明」。一张可以凭感觉填的表，等于把五态判定交给填表人的记性。

⇒ 机器守两件事：
1. **引用真的出自那份定义自己的散文** —— 编不出引用的不许标 `true`；
2. **20 份定义一个不多一个不少都有表态** —— 漏一份就等于那一份默认按
   「口径无歧义」处理，而那正是 `N-84` 的缺陷本身。

## 它**守不住**什么（写在这里，免得「本文件全绿」被读成别的意思）

**「该标而没标」核不出来。** 那需要一张外部事实表（哪些指标在实务里有几种口径），
本仓没有，也不打算编（编词表是 `intent.py` 抬头点名的错方向）。
下面 `test_标了true的正好是这九个` 把当前判断**钉死**，于是改动必须是显式的；
它证明的是「没人悄悄改过」，不是「这九个就是对的」。
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from semantic_layer.basis_choice import (
    DEFAULT_BASIS_CHOICE_FILENAME,
    BasisChoice,
    BasisChoiceTable,
    load_basis_choices,
    prose_of,
    verify_quotes,
)
from semantic_layer.definition import (
    PROSE_PATHS,
    iter_definition_paths,
    load_definition,
)
from semantic_layer.resolve import Registry

REPO = Path(__file__).resolve().parent.parent
METRICS = REPO / "metrics"
TABLE_PATH = METRICS / DEFAULT_BASIS_CHOICE_FILENAME

#: 🔴 **当前的九条。改这个数字之前先读本模块抬头的「守不住什么」。**
#: 多一条或少一条都要在这里显式改，并在 `metrics/_basis_choice.yaml` 里
#: 留下那份定义的逐字引用。
标了的 = {
    "accounts_payable_turnover_days",
    "accounts_receivable_turnover_days",
    "debt_to_asset_ratio",
    "free_cash_flow",
    "inventory_turnover_days",
    "ocf_to_net_profit_attributable",
    "quick_ratio",
    "return_on_total_assets",
    "total_asset_turnover",
}


@pytest.fixture
def table():
    return load_basis_choices(TABLE_PATH)


def test_每条引用都真的出自那份定义的散文(table):
    """🔴 这是这张表唯一的硬保障：引用逐字可核。"""
    assert verify_quotes(table, METRICS) == []


def test_二十份定义一个不多一个不少都有表态(table):
    on_disk = {
        load_definition(p).metric_id for p in iter_definition_paths(METRICS)
    }
    assert len(on_disk) == 20, f"磁盘上有 {len(on_disk)} 份定义，不是 20"
    assert set(table.entries) == on_disk


def test_标了true的正好是这九个(table):
    got = {k for k, v in table.entries.items() if v.basis_is_a_choice}
    assert got == 标了的, (
        f"口径选择表变了：多出 {sorted(got - 标了的)}，少了 {sorted(标了的 - got)}。"
        "⚠️ 不要直接改这里的集合 —— 先确认那份定义的散文里真有那句话，"
        "并在 `metrics/_basis_choice.yaml` 留下逐字引用"
    )


def test_漏一份定义必须报红(table):
    """造回归：把一份定义从表里删掉。

    漏一份不是「少一条信息」，是**那一份默认按「口径无歧义」处理** ——
    `N-84` 的缺陷原样复活，而且一声不响。
    """
    坏 = BasisChoiceTable(entries=dict(table.entries))
    坏.entries.pop("free_cash_flow")
    问题 = verify_quotes(坏, METRICS)
    assert any("漏了" in p for p in 问题), 问题


def test_表里有磁盘上不存在的指标必须报红(table):
    坏 = BasisChoiceTable(entries=dict(table.entries))
    坏.entries["不存在的指标"] = BasisChoice(
        metric_id="不存在的指标", basis_is_a_choice=False, why="造出来的"
    )
    问题 = verify_quotes(坏, METRICS)
    assert any("磁盘上不存在" in p for p in 问题), 问题


def test_编出来的引用必须报红(table):
    """🔴 最要紧的一条负控制：引用不许是编的。

    把 `quote` 换成一句**没有写在那份定义里**的话 —— 它读起来完全合理，
    这正是危险之处：一句合理但不存在的引用，会让一次拍脑袋的判断
    看起来像有依据。
    """
    坏 = BasisChoiceTable(entries=dict(table.entries))
    原 = 坏.entries["quick_ratio"]
    坏.entries["quick_ratio"] = type(原)(
        metric_id=原.metric_id,
        basis_is_a_choice=True,
        quote="速动比率在实务中有多种口径，彼此不可比",  # 听起来对，但不在那份定义里
        why=原.why,
    )
    问题 = verify_quotes(坏, METRICS)
    assert any("quote 不在这份定义的散文里" in p for p in 问题), 问题


def test_标了true却没有引用必须报红(table):
    坏 = BasisChoiceTable(entries=dict(table.entries))
    原 = 坏.entries["quick_ratio"]
    坏.entries["quick_ratio"] = type(原)(
        metric_id=原.metric_id, basis_is_a_choice=True, quote=None, why=原.why
    )
    问题 = verify_quotes(坏, METRICS)
    assert any("没有 quote" in p for p in 问题), 问题


def test_引用的取值路径与指纹剔除的三条散文路径一致():
    """`prose_of()` 取的必须就是 `PROSE_PATHS` 那三条，不多不少。

    两处用的是同一组路径而写法不同（那边是字符串字面量、这边是取值器），
    **它们分叉时没有任何东西会报错** —— 这一条就是那个报错。
    """
    assert PROSE_PATHS == {
        "derivation.note",
        "common_pitfalls[].text",
        "undefined_conditions[].reason",
    }
    defn = load_definition(METRICS / "free_cash_flow.yaml")
    got = prose_of(defn)
    assert defn.derivation["note"] in got
    assert all(p.text in got for p in defn.common_pitfalls if p.text)
    assert all(c.reason in got for c in defn.undefined_conditions if c.reason)
    # 条数 = 1 + len(pitfalls) + len(undefined_conditions)，一个都不许多
    assert len(got) == 1 + len(
        [p for p in defn.common_pitfalls if p.text]
    ) + len([c for c in defn.undefined_conditions if c.reason])


def test_加这张表没有动任何一份定义的口径指纹():
    """🔴 这是选「旁挂文件」而不是「往定义里加一位」的全部理由。

    往定义 YAML 里加键会落进指纹（`D-034` 的剔除是白名单式的）⇒ 必须改
    `version` ⇒ 而 `frozen-01` 有 14 道题的标准答案钉在 `metric_version: 2` 上。
    为一位**不改变任何计算结果**的元数据作废 14/20 道冻结题，
    70% ≫ `D-012` 修订三的 10% 上限。
    """
    import json

    表 = json.loads((METRICS / "_fingerprints.json").read_text(encoding="utf-8"))
    for path in iter_definition_paths(METRICS):
        defn = load_definition(path)
        assert defn.version == 2, f"{path.name} 的 version 不是 2"
        assert 表["definitions"][defn.metric_id]["version"] == 2


def test_注册表真的把这张表装上了():
    """表在磁盘上对不算完 —— `Registry.load` 得真的读它。

    `_flags.yaml` 曾经就栽在这里：定义从 `metrics_dir` 读、词表从 **cwd** 读，
    同一个注册表的两半用了两个根（见 `Registry.load` 里那段注释）。
    """
    reg = Registry.load(METRICS)
    assert reg.basis_choice.path == TABLE_PATH
    assert reg.basis_choice.is_a_choice("quick_ratio") is True
    assert reg.basis_choice.is_a_choice("current_ratio") is False
    assert "跨来源引用速动比率前须确认对方口径" in reg.basis_choice.quote_for("quick_ratio")


def test_表不在时退回全部false而不是炸(tmp_path):
    """缺表按 `false`，但那意味着核查层**静悄悄**退回改之前的行为。

    守它在不在的是上面那条「一个不多一个不少」，不是加载器。
    这一条只钉住加载器不抛异常。
    """
    空 = load_basis_choices(tmp_path / "没有这个文件.yaml")
    assert 空.entries == {}
    assert 空.path is None
    assert 空.is_a_choice("quick_ratio") is False


def test_每条false都写了理由(table):
    """`false` 是一次可被推翻的判断 —— 推翻它要先知道当初为什么这么判。"""
    没写的 = sorted(
        k for k, v in table.entries.items() if not v.basis_is_a_choice and not v.why
    )
    assert 没写的 == [], f"这些 false 没写 why：{没写的}"


def test_表自己是合法YAML且版本号在():
    raw = yaml.safe_load(TABLE_PATH.read_text(encoding="utf-8"))
    assert raw["version"] == 1
    assert isinstance(raw["definitions"], dict)
