"""`scripts/evidence_matrix.py` 的回归 —— 登记册 `L-6`。

这个生成器在真仓库上**当前是零断线的**。
⇒ **零断线的输出证明不了检测有效** —— 必须在受控输入上证明它会报断线，
否则「它说没问题」与「它坏了」不可区分。这与 `test_留痕采集点唯一这条断言不是空转`
是同一条：集合相等对空集也成立。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location(
    "evidence_matrix", REPO / "scripts" / "evidence_matrix.py"
)
assert _SPEC and _SPEC.loader
em = importlib.util.module_from_spec(_SPEC)
sys.modules["evidence_matrix"] = em
_SPEC.loader.exec_module(em)


@pytest.fixture
def sandbox(tmp_path):
    """一个只有两个模块的假 `src/`，写进 tmp_path 而不是真仓库。"""
    (tmp_path / "producer.py").write_text(
        "from dataclasses import dataclass\n"
        "@dataclass\n"
        "class R:\n"
        "    orphan_pointer: int\n"
        "    read_pointer: int\n"
        "def build():\n"
        "    return R(orphan_pointer=1, read_pointer=2)\n",
        encoding="utf-8",
    )
    (tmp_path / "consumer.py").write_text(
        "def use(r):\n    return r.read_pointer\n",
        encoding="utf-8",
    )
    return tmp_path


FIELDS = ("orphan_pointer", "read_pointer")


def test_有产生点零消费点的字段被识别为断线(sandbox):
    """**这是本文件的存在理由**：证明它真的会报断线。

    `orphan_pointer` 被声明、被构造时赋值，**全仓没有任何地方读它** ——
    正是 `ARCHITECTURE` §8.5.3 说的「算出来了，没人读」。
    """
    matrix = em.collect(fields=FIELDS, roots=(sandbox,))

    assert matrix["orphan_pointer"]["produce"], "连产生点都没找到，扫描器可疑"
    assert matrix["orphan_pointer"]["consume"] == [], "断线字段却被算出了消费点"
    # 对照组：另一个字段有消费点 —— 没有它，上一条可以靠「什么都扫不到」满足。
    assert matrix["read_pointer"]["consume"], "对照字段的消费点也没找到，扫描器坏了"


def test_把那次读取删掉之后对照字段也变成断线(sandbox):
    """负控制的另一半：**消费点是真的从代码里读出来的**，不是写死的。"""
    (sandbox / "consumer.py").write_text("def use(r):\n    return 0\n", encoding="utf-8")
    matrix = em.collect(fields=FIELDS, roots=(sandbox,))
    assert matrix["read_pointer"]["consume"] == []


def test_真仓库上当前零断线():
    """基线。**红了不要改这条测试** —— 先看是哪个字段没人读了。"""
    matrix = em.collect()
    broken = [
        f for f in em.TRACKED_FIELDS
        if matrix[f]["produce"] and not matrix[f]["consume"]
    ]
    assert broken == [], f"这些证据字段算出来了却没人读：{broken}"
    # 扫描面不能是空的 —— 否则上一条恒绿。
    assert sum(len(v["produce"]) for v in matrix.values()) >= 50


def test_它抓不到to_dict丢字段这一类而docstring如实写了这件事():
    """⚠️ **本条锁的是一句「我们抓不到什么」的自陈，不是一个能力。**

    2026-08-31 实测：把 `header_inherited` 从 `to_dict()` 删掉，
    矩阵从 `14 产生 / 5 消费` 变成 `13 / 4`，**退出码仍是 0** ——
    因为那是「少了一个消费点」，不是「零消费点」。

    原 docstring 声称它能抓本会话那两个实例，**那句话是错的**。
    本条把更正后的自陈钉住：谁把那段删掉或改回去，这里会红。
    **声称的范围不许大于被证明的范围** —— 这条纪律对这个工具自己一样适用。
    """
    doc = em.__doc__ or ""
    assert "本工具都抓不到" in doc
    assert "退出码仍是 0" in doc
    # 也不许把「为什么不做成计数下降报警」那段理由删掉：
    # 那是这个判据为什么只能是「零消费点」的全部依据。
    assert "需要一个基线" in doc
