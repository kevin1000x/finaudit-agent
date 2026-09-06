"""离线抽取导出的回归（`N-61`）。

这份测试守的是**一件事**：产品对外说出口的每一个数，都在人工核对过的清单里。

抽取器本身跑一次要开一份几百页的 PDF，所以过滤逻辑用一个假批次测
（`_fake_batch`），**真实产物则直接对着提交进仓库的那两份文件断言** ——
后者不花时间，却是唯一能守住「实际发货的数据」的那一道。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from extractor import export as ex  # noqa: E402


@dataclass
class _Rec:
    field_id: str
    value: object
    page: int = 7
    column_header: str = "2023年12月31日"
    cell_state = None
    mapping_version: int = 1
    source_url: str = ""  """空串：假批次不联网，`export_one` 会因此把 `source_url` 落成 null。"""


class _Batch:
    batch_id = "batch-test"

    def __init__(self, records):
        self.records = records


def _write_verified(tmp_path, fields, pdf, extra_meta=None):
    import hashlib

    meta = {
        "stock_code": "600519",
        "fiscal_year": 2023,
        "short_name": "测试公司",
        "source_pdf": str(pdf),
        "source_pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
        "signed_off": "测试",
        "verification_sections": ["D.99"],
    }
    meta.update(extra_meta or {})
    path = tmp_path / "600519_2023.yaml"
    path.write_text(
        yaml.safe_dump({"meta": meta, "fields": fields}, allow_unicode=True), encoding="utf-8"
    )
    return path


@pytest.fixture
def pdf(tmp_path):
    p = tmp_path / "fake.pdf"
    p.write_bytes(b"%PDF-1.4 not really a pdf")
    return p


def _run(monkeypatch, tmp_path, allow, extracted, pdf, extra_meta=None):
    _write_verified(tmp_path, allow, pdf, extra_meta)
    monkeypatch.setattr(
        ex, "extract_batch", lambda *a, **k: _Batch([_Rec(f, v) for f, v in extracted.items()])
    )
    return ex.export_one("600519", 2023, pdf_path=pdf, verified_dir=tmp_path)


# --------------------------------------------------------------------------
# 准入清单：这四条是这个模块存在的理由
# --------------------------------------------------------------------------


def test_没核对过的字段不进产物(monkeypatch, tmp_path, pdf):
    """**红的时候是什么样**：抽取器新增一个字段，它没经过人工核对却出现在产物里，
    于是产品开始对外输出没人验过的数。这正是万华那 3 个 `notes.*` 曾经的处境。
    """
    payload = _run(
        monkeypatch,
        tmp_path,
        allow={"bs.total_assets": "100.5"},
        extracted={"bs.total_assets": Decimal("100.5"), "bs.没核对过的": Decimal("7")},
        pdf=pdf,
    )
    assert "bs.没核对过的" not in payload["row"]
    # 丢了什么必须留痕 —— 不留痕，「产品答不了这道题」就成了没人知道的事
    assert payload["dropped"] == ["bs.没核对过的"]


def test_取值对不上就整份不导出(monkeypatch, tmp_path, pdf):
    """**红的时候是什么样**：抽取器改了行缝合规则，某个字段悄悄取到了隔壁那一行。
    清单里的值抄自签署过的核对记录，所以这里会当场对不上。
    """
    with pytest.raises(ex.ExportRejected) as e:
        _run(
            monkeypatch,
            tmp_path,
            allow={"bs.total_assets": "100.5"},
            extracted={"bs.total_assets": Decimal("999")},
            pdf=pdf,
        )
    assert "bs.total_assets" in str(e.value)


def test_清单里有却没抽到是回归不是覆盖面变化(monkeypatch, tmp_path, pdf):
    with pytest.raises(ex.ExportRejected) as e:
        _run(
            monkeypatch,
            tmp_path,
            allow={"bs.total_assets": "100.5", "bs.total_liabilities": "40"},
            extracted={"bs.total_assets": Decimal("100.5")},
            pdf=pdf,
        )
    assert "bs.total_liabilities" in str(e.value)


def test_没有核对清单就不给导出(monkeypatch, tmp_path, pdf):
    monkeypatch.setattr(ex, "extract_batch", lambda *a, **k: _Batch([]))
    with pytest.raises(ex.ExportRejected):
        ex.export_one("000001", 2023, pdf_path=pdf, verified_dir=tmp_path)


def test_PDF不是核对时那一份就不给导出(monkeypatch, tmp_path, pdf):
    """核对结论**只对那一份 PDF 成立**。换一份 PDF 就是换了一份证据。"""
    with pytest.raises(ex.ExportRejected) as e:
        _run(
            monkeypatch,
            tmp_path,
            allow={"bs.total_assets": "100.5"},
            extracted={"bs.total_assets": Decimal("100.5")},
            pdf=pdf,
            extra_meta={"source_pdf_sha256": "0" * 64},
        )
    assert "不是核对时的那一份" in str(e.value)


def test_末位零不算不一致(monkeypatch, tmp_path, pdf):
    """`48697611501.20` 与 `48697611501.2` 是同一个数。

    核对记录里两种写法都出现过（`COMPUTED-VALUES.md` §5.1 的 AKShare 列省略末位零），
    按字符串比会把一致判成不一致，然后有人会去「修」清单 —— 那才是危险的。
    """
    payload = _run(
        monkeypatch,
        tmp_path,
        allow={"bs.total_assets": "48697611501.20"},
        extracted={"bs.total_assets": Decimal("48697611501.2")},
        pdf=pdf,
    )
    assert payload["row"]["bs.total_assets"] == Decimal("48697611501.2")


# --------------------------------------------------------------------------
# 渲染：数值必须加引号，否则精度被 YAML 悄悄改掉
# --------------------------------------------------------------------------


def test_数值加引号落盘_不经过float():
    """**红的时候是什么样**：`272699660092.25` 不加引号被读成 float，
    末几位悄悄变了 —— 而证据链上印着的是变过之后的数，没人看得出来。
    """
    payload = {
        "meta": {"stock_code": "600519", "fiscal_year": 2023, "short_name": "x", "full_name": "y"},
        "source_pdf_sha256": "a" * 64,
        "batch_id": "b",
        "source_url": None,
        "dropped": [],
        "row": {
            "stock_code": "600519",
            "fiscal_year": 2023,
            "bs.total_assets": Decimal("272699660092.25"),
            "notes.restatement_flag": True,
            "notes.business_combination_type": (),
        },
        "provenance": {},
    }
    text = ex.render_yaml(payload)
    back = yaml.safe_load(text)["rows"][0]
    assert back["bs.total_assets"] == "272699660092.25"      # 字符串，不是 float
    assert back["notes.restatement_flag"] is True            # 布尔还是布尔
    assert back["notes.business_combination_type"] == []


# --------------------------------------------------------------------------
# 对**真的提交进仓库的那两份产物**断言 —— 这是唯一守得住实际发货数据的一道
# --------------------------------------------------------------------------

EXTRACTED = REPO_ROOT / "data" / "extracted"
VERIFIED = REPO_ROOT / "data" / "verified"


def _pairs():
    return sorted(p.name for p in EXTRACTED.glob("*.yaml")) if EXTRACTED.is_dir() else []


@pytest.mark.parametrize("name", _pairs())
def test_产物里的每个字段都在核对清单里且取值一致(name):
    got = yaml.safe_load((EXTRACTED / name).read_text(encoding="utf-8"))
    allow = yaml.safe_load((VERIFIED / name).read_text(encoding="utf-8"))["fields"]
    row = got["rows"][0]
    fields = {k: v for k, v in row.items() if k not in ("stock_code", "fiscal_year")}
    assert set(fields) == set(allow), "产物的字段集必须**等于**核对清单，不多不少"
    for k, v in fields.items():
        assert ex._comparable(v) == ex._comparable(allow[k]), k


@pytest.mark.parametrize("name", _pairs())
def test_产物里不许出现本机绝对路径(name):
    """走本地 PDF 复跑时 `source_url` 是 `file://C:/Users/...`。

    那会把操作者的目录结构写进一个提交进仓库的文件 ——
    而这个仓库按 `D-005` 到 Phase 4 才决定要不要公开。
    """
    text = (EXTRACTED / name).read_text(encoding="utf-8")
    assert "file://" not in text
    assert "C:/Users" not in text and "C:\\Users" not in text


@pytest.mark.parametrize("name", _pairs())
def test_自称真实数据必须给得出PDF指纹(name):
    """`kind: real` 不是一句自我声明就算数。

    没有这条，往 `data/extracted/` 里放一份合成文件、写上 `kind: real`，
    它就会被当成年报原文对外展示 —— 那是这个项目最不能犯的错（`D-010`）。
    """
    meta = yaml.safe_load((EXTRACTED / name).read_text(encoding="utf-8"))["meta"]
    assert meta["kind"] == "real"
    assert len(str(meta["source_pdf_sha256"])) == 64
    assert meta["verification_sections"], "得说得出是哪一节核对的"
