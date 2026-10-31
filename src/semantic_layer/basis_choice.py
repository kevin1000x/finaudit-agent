"""「这个指标的正式名够不够确定口径」——每份定义自己说的那一位（`N-84` / `D-045`）。

## 这个模块为什么存在

核查层判 `AMBIGUOUS_BASIS` 原先唯一的判据是**命中的别名 ≠ `display_name`**。
独立复核（2026-09-11）把 20 份定义的正式名逐个喂进去核过，**20/20 都不触发** ——
那条判据测的是「用户打的字跟正式名不一样」，不是「这里发生过一次口径判断」。
漏掉的恰好是危险的那一侧：`自由现金流`（定义自己写着「结果差异可达数倍」）、
`速动比率`、`总资产收益率` 的正式名一律沉默。

⇒ 判据改成两条并联：**别名 ≠ 正式名**（保留）**或**本表说这个指标的口径是一次选择。

## 为什么是旁挂文件

这一位**不改变任何一个数**，所以它不属于口径本身，不进语义载荷（`D-034` 的指纹）。
把它写进定义 YAML 会落进指纹 ⇒ 必须改 `version` ⇒ `frozen-01` 有 14 道题的
标准答案钉在 `metric_version: 2` 上，为一位元数据作废 14/20 道冻结题，
70% ≫ `D-012` 修订三的 10% 上限。代价与理由逐条写在 `metrics/_basis_choice.yaml` 抬头。

## 它守得住的和守不住的

**守得住**：`quote` 真的出现在那份定义自己的散文里（`verify_quotes`），
以及 20 份定义一个不多一个不少都有表态（`missing` / `extra`）。
**守不住**：「该标而没标」。那需要一张外部事实表（哪些指标在实务里有几种口径），
本仓没有也不编 —— 编词表是 `intent.py` 抬头点名的错方向。
⇒ 每一条 `false` 都是可被推翻的判断，推翻的方式是引用那份定义的散文。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .definition import iter_definition_paths, load_definition

__all__ = [
    "BasisChoice",
    "BasisChoiceTable",
    "DEFAULT_BASIS_CHOICE_FILENAME",
    "load_basis_choices",
    "prose_of",
    "verify_quotes",
]

DEFAULT_BASIS_CHOICE_FILENAME = "_basis_choice.yaml"


@dataclass(frozen=True)
class BasisChoice:
    """一个指标的表态。`quote` 只在 `basis_is_a_choice` 为真时有意义。"""

    metric_id: str
    basis_is_a_choice: bool
    quote: str | None = None
    why: str | None = None


@dataclass(frozen=True)
class BasisChoiceTable:
    """整张表。**缺表时一律按 `false`**，不抛异常。

    ⚠️ 这条「缺表按 false」是刻意的，但它有代价：表文件没了，核查层会**静悄悄**
    退回到改之前的行为。所以守它的不是本模块，是 `tests/test_basis_choice.py`
    那条「20 份定义一个不多一个不少都在表里」—— 表没了，那条测试会红。
    """

    entries: dict
    path: Path | None = None

    def is_a_choice(self, metric_id) -> bool:
        got = self.entries.get(str(metric_id))
        return bool(got and got.basis_is_a_choice)

    def quote_for(self, metric_id) -> str | None:
        got = self.entries.get(str(metric_id))
        return got.quote if got and got.basis_is_a_choice else None


def load_basis_choices(path: Path | str) -> BasisChoiceTable:
    """读一张表。文件不存在 ⇒ 空表（全部按 `false`），见 `BasisChoiceTable` 抬头。"""
    path = Path(path)
    if not path.is_file():
        return BasisChoiceTable(entries={}, path=None)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    block = raw.get("definitions") or {}
    entries: dict[str, BasisChoice] = {}
    if isinstance(block, dict):
        for metric_id, body in block.items():
            body = body if isinstance(body, dict) else {}
            entries[str(metric_id)] = BasisChoice(
                metric_id=str(metric_id),
                basis_is_a_choice=bool(body.get("basis_is_a_choice")),
                quote=body.get("quote"),
                why=body.get("why"),
            )
    return BasisChoiceTable(entries=entries, path=path)


def _squeeze(text) -> str:
    """去掉**全部**空白再比。

    理由不是洁癖：定义文件里这些句子写在 YAML 折叠标量（`>`）里，折行处会被
    换成一个空格 —— 按「空白折叠成单空格」比对仍然会被那个空格骗过去，
    而被骗的方向是**引用核不上**（假红），那会诱使人去改引用而不是去改表。
    """
    return "".join(str(text or "").split())


def prose_of(defn) -> list[str]:
    """一份定义的全部散文。**与 `PROSE_PATHS` 是同一组路径**。

    这里不 import `PROSE_PATHS` 去反射取值：那三条路径在那边是**剔除指纹**用的
    字符串字面量（`"common_pitfalls[].text"`），拿来当取值器会要写一个小解释器。
    ⚠️ 两处必须对上，`tests/test_basis_choice.py` 有一条测试把它们钉在一起。
    """
    out: list[str] = []
    derivation = getattr(defn, "derivation", None)
    if isinstance(derivation, dict):
        if derivation.get("note"):
            out.append(str(derivation["note"]))
    elif derivation:
        out.append(str(derivation))
    for pit in getattr(defn, "common_pitfalls", []) or []:
        text = getattr(pit, "text", None)
        if text:
            out.append(str(text))
    for cond in getattr(defn, "undefined_conditions", []) or []:
        reason = getattr(cond, "reason", None)
        if reason:
            out.append(str(reason))
    return out


def verify_quotes(table: BasisChoiceTable, metrics_dir: Path | str) -> list[str]:
    """机械核对。返回问题清单，空列表表示通过。

    三件事：① 表与磁盘上的定义一个不多一个不少；② 每条 `true` 都有 `quote`；
    ③ 每条 `quote` 真的出现在**那一份**定义自己的散文里。
    """
    problems: list[str] = []
    on_disk: dict[str, object] = {}
    for path in iter_definition_paths(metrics_dir):
        defn = load_definition(path)
        if defn.metric_id:
            on_disk[str(defn.metric_id)] = defn

    missing = sorted(set(on_disk) - set(table.entries))
    extra = sorted(set(table.entries) - set(on_disk))
    if missing:
        problems.append(
            f"{DEFAULT_BASIS_CHOICE_FILENAME} 漏了 {len(missing)} 份定义：{missing} —— "
            "漏一份等于那一份默认按「口径无歧义」处理，而那正是 `N-84` 的缺陷本身"
        )
    if extra:
        problems.append(
            f"{DEFAULT_BASIS_CHOICE_FILENAME} 里有磁盘上不存在的指标：{extra}"
        )

    for metric_id, entry in sorted(table.entries.items()):
        if not entry.basis_is_a_choice:
            continue
        defn = on_disk.get(metric_id)
        if defn is None:
            continue
        if not entry.quote:
            problems.append(f"{metric_id}：标了 basis_is_a_choice 却没有 quote")
            continue
        haystack = _squeeze(" ".join(prose_of(defn)))
        if _squeeze(entry.quote) not in haystack:
            problems.append(
                f"{metric_id}：quote 不在这份定义的散文里 —— {entry.quote!r}。"
                "引用必须逐字出自 derivation.note / common_pitfalls[].text / "
                "undefined_conditions[].reason，编不出引用的不许标 true"
            )
    return problems
