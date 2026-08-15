"""全局受控 flag 词表的加载 —— OQ-02 的回归测试。

背景：01-02 的反向核对发现 `Flag` dataclass 把五个键都声明为必需，
但 `load_vocabulary()` 只真强制了 `name` 与 `scope`，另外三个静默补默认值。
其中 `affects_comparability` 补 `False` 方向最坏——漏写该键的 flag 会被当成
「不影响可比性」，一个本该阻断跨期比较的标记悄悄不阻断且不报错。

这些用例锁住修复：**五个键缺一即拒绝加载**。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from semantic_layer.vocabulary import load_vocabulary  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent

_COMPLETE = {
    "name": "restated",
    "description": "比较期数值经追溯重述",
    "scope": "definition",
    "affects_comparability": True,
    "introduced_by": "POC-01 C5",
}


def _write(tmp_path: Path, entry: dict) -> Path:
    import yaml

    path = tmp_path / "_flags.yaml"
    path.write_text(
        yaml.safe_dump({"vocabulary_version": 1, "flags": [entry]}, allow_unicode=True),
        encoding="utf-8",
    )
    return path


def test_complete_entry_loads(tmp_path):
    vocab = load_vocabulary(_write(tmp_path, dict(_COMPLETE)))
    assert vocab.flags["restated"].affects_comparability is True
    assert vocab.flags["restated"].introduced_by == "POC-01 C5"


@pytest.mark.parametrize("key", ["name", "description", "scope", "affects_comparability", "introduced_by"])
def test_missing_required_key_raises(tmp_path, key):
    entry = dict(_COMPLETE)
    del entry[key]
    with pytest.raises(ValueError, match="缺少必需键|scope"):
        load_vocabulary(_write(tmp_path, entry))


def test_affects_comparability_must_be_boolean(tmp_path):
    """写成字符串 "false" 会被 bool() 判成 True —— 比漏写还隐蔽，必须拒绝。"""
    entry = dict(_COMPLETE, affects_comparability="false")
    with pytest.raises(ValueError, match="必须是布尔值"):
        load_vocabulary(_write(tmp_path, entry))


def test_bad_scope_raises(tmp_path):
    entry = dict(_COMPLETE, scope="whatever")
    with pytest.raises(ValueError, match="scope"):
        load_vocabulary(_write(tmp_path, entry))


def test_real_vocabulary_loads_and_is_complete():
    """真词表的 10 条必须全部写齐五键——修复之后它就是这条的证明。"""
    vocab = load_vocabulary(REPO_ROOT / "metrics" / "_flags.yaml")
    assert len(vocab.flags) == 10
    assert len(vocab.system_scoped) == 2
    for name, flag in vocab.flags.items():
        assert flag.description, f"{name} 的 description 为空"
        assert flag.introduced_by, f"{name} 的 introduced_by 为空"
        assert isinstance(flag.affects_comparability, bool)
