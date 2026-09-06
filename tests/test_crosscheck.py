"""AKShare 对照通路的回归 —— `D-013` / `D-016` / `D-029`，与 `C-6`…`C-9`、`L-12`。

每条测试对应一个**已经写下来的判据**，不是「覆盖率」。

**全部用例离线跑**：走固件 `tests/fixtures/akshare_600519_2023.json` 回放，
不 import akshare、不发任何网络请求。理由不只是快 —— 一条要联网才能红的测试，
在网络抖动时红的原因不是它要查的那件事（`b0afe00` 的教训）。
"""

from __future__ import annotations

import ast
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from extractor.crosscheck import (
    DISAGREEMENT_TOLERANCE,
    MISCALIBRATION_THRESHOLD,
    SOURCE_AKSHARE,
    AkshareMappingTable,
    CrossCheckVerdict,
    IncomparableReason,
    ReferenceValue,
    assert_akshare_mapping_within_definitions,
    cross_validate,
    cross_validate_batch,
    load_akshare_mapping,
    load_all_akshare_mappings,
    load_reference_payload,
    references_from_payload,
    source_disagreement_flag,
)
from extractor.record import (
    BasisConfirmation,
    CellState,
    ExtractionBatch,
    ExtractionRecord,
    ExtractionStatus,
    RecordKind,
    RetrievalOutcome,
    Selection,
    SourceFreshness,
    make_batch_id,
)
from semantic_layer.resolve import Refusal, RefusalCode

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).parent / "fixtures" / "akshare_600519_2023.json"
SHA_A = "a" * 64

FULL_TABLE = Selection(sampling="full", order_key="page_then_y", truncation="none")


def _record(**overrides) -> ExtractionRecord:
    kwargs = dict(
        field_id="bs.total_assets",
        kind=RecordKind.STATEMENT_LINE,
        value=Decimal("272699660092.25"),
        status=ExtractionStatus.SUCCESS,
        retrieval=RetrievalOutcome.GOT_VALUE,
        basis_confirmation=BasisConfirmation.CONFIRMED,
        source_freshness=SourceFreshness.FETCHED_THIS_RUN,
        cell_state=CellState.VALUE_PRESENT,
        page=60,
        anchor_page=59,
        pdf_sha256=SHA_A,
        source_url="https://static.cninfo.com.cn/finalpage/x.PDF",
        unit="元",
        currency="人民币",
        column_header="期末余额",
        header_inherited=False,
        mapping_version=1,
        selection=FULL_TABLE,
        truncation_stats={},
        batch_id=make_batch_id("600519", 2023, SHA_A),
    )
    kwargs.update(overrides)
    return ExtractionRecord(**kwargs)


def _reference(**overrides) -> ReferenceValue:
    kwargs = dict(
        field_id="bs.total_assets",
        column_name="资产总计",
        raw=272699660092.25,
        present=True,
        statement="balance_sheet",
        source=SOURCE_AKSHARE,
        mapping_version=1,
        unit="元",
        currency="人民币",
        period="20231231",
        scope="合并期末",
        scope_required="合并期末",
    )
    kwargs.update(overrides)
    return ReferenceValue(**kwargs)


# --------------------------------------------------------------------------
# 一、映射表：逐字相等，且与 PDF 侧物理分开（D-016 / C-8）
# --------------------------------------------------------------------------


def test_三份映射文件都能加载且都声明了版本号():
    tables = load_all_akshare_mappings()
    assert set(tables) == {"balance_sheet", "income_statement", "cash_flow"}
    for table in tables.values():
        assert isinstance(table, AkshareMappingTable)
        assert table.mapping_version >= 1


def test_流动负债合计不匹配总负债():
    """cninfo 的真实错误映射之一（`references/cninfo.md:204-213`）。

    子串匹配下「流动负债合计」含「负债合计」⇒ 会被错配到 `bs.total_liabilities`。
    逐字相等下不会。**这不是假设性风险，是别人已经犯过的错。**

    ⚠️ **2026-08-28 补强（`RV-4`，独立复核查出）**：本条原来**没有辨析力**。
    把 `field_for_column` 的 `==` 改成 `in`（子串包含）之后它**仍然绿** ——
    因为 `流动负债合计` 在 entries 里排在 `负债合计` 前面（索引 11 vs 12），
    子串匹配器扫到的第一条恰好还是对的。把这两行 YAML 对调位置，
    这条测试就会变成假阴性而没有任何东西发现。

    ⇒ 补的是**反方向**那一条：拿 `负债合计` 去查。子串匹配下
    `"负债合计" in "流动负债合计"` 为真，扫到索引 11 就会返回流动负债字段 ⇒ 必红。
    **这一条与 entries 的先后顺序无关。**
    """
    table = load_akshare_mapping("balance_sheet")
    assert table.field_for_column("流动负债合计") == "bs.total_current_liabilities_period_end"
    assert table.field_for_column("流动负债合计") != "bs.total_liabilities"
    assert table.column_for_field("bs.total_liabilities") == "负债合计"
    # ↓ 这一条才是真正咬住「逐字相等 → 子串包含」的那把锁
    assert table.field_for_column("负债合计") == "bs.total_liabilities"


def test_应付票据及应付账款不匹配应付账款():
    """cninfo 的第三处错误映射：把合并列映射到本项目明文禁止合并的字段。

    ⚠️ **这份样本上两列的数值恰好相等**（茅台没有应付票据）——
    也就是说错配在这份数据上**不会被数值对照发现**。
    逐字相等是唯一能在这里挡住它的东西，数值一致性挡不住。
    """
    table = load_akshare_mapping("balance_sheet")
    assert table.column_for_field("bs.accounts_payable") == "应付账款"
    assert table.field_for_column("应付票据及应付账款") is None

    row = load_reference_payload(FIXTURE)["balance_sheet"]["row"]
    assert row["应付票据及应付账款"] == row["应付账款"]


def test_净利润与归母净利润是两个不同的字段():
    """cninfo 的第二处错误映射。两列在本样本上差 27.87 亿，错配会静默改变分子。"""
    table = load_akshare_mapping("income_statement")
    assert table.column_for_field("is.net_profit") == "净利润"
    assert (
        table.column_for_field("is.net_profit_attributable_to_parent")
        == "归属于母公司所有者的净利润"
    )
    row = load_reference_payload(FIXTURE)["income_statement"]["row"]
    assert row["净利润"] != row["归属于母公司所有者的净利润"]


def test_akshare_列名的括号是半角与_pdf_版面不是同一个串():
    """`C-8`：AKShare 印 `所有者权益(或股东权益)合计`，PDF 印全角 `（）`。"""
    table = load_akshare_mapping("balance_sheet")
    column = table.column_for_field("bs.total_equity")
    assert column == "所有者权益(或股东权益)合计"
    assert "（" not in column and "）" not in column
    assert table.field_for_column("所有者权益（或股东权益）合计") is None


def _write_mapping(directory: Path, statement: str, body: str) -> None:
    (directory / f"{statement}.yaml").write_text(body, encoding="utf-8")


def _minimal_mapping(statement: str, field_id: str, column_name: str) -> str:
    return (
        f"statement: {statement}\nmapping_version: 1\n"
        "currency:\n  reported: CNY\n  canonical: 人民币\n"
        "scope_required: 合并期末\n"
        f"entries:\n  - field_id: {field_id}\n    statement: {statement}\n"
        f"    column_name: {column_name}\n"
    )


def test_映射条目缺必需键即拒绝加载(tmp_path):
    _write_mapping(
        tmp_path,
        "balance_sheet",
        "statement: balance_sheet\nmapping_version: 1\n"
        "currency:\n  reported: CNY\n  canonical: 人民币\n"
        "scope_required: 合并期末\n"
        "entries:\n  - field_id: bs.total_assets\n    statement: balance_sheet\n",
    )
    with pytest.raises(ValueError, match="column_name"):
        load_akshare_mapping("balance_sheet", tmp_path)


def test_映射表未声明版本号即拒绝加载(tmp_path):
    _write_mapping(
        tmp_path,
        "balance_sheet",
        "statement: balance_sheet\n"
        "currency:\n  reported: CNY\n  canonical: 人民币\n"
        "scope_required: 合并期末\n"
        "entries:\n  - field_id: bs.total_assets\n    statement: balance_sheet\n"
        "    column_name: 资产总计\n",
    )
    with pytest.raises(ValueError, match="mapping_version"):
        load_akshare_mapping("balance_sheet", tmp_path)


def test_映射表不声明合并口径即拒绝加载(tmp_path):
    """不声明 `scope_required` 等于默认接受母公司数据参与对照 —— 那是另一种 `A-9`。"""
    _write_mapping(
        tmp_path,
        "balance_sheet",
        "statement: balance_sheet\nmapping_version: 1\n"
        "currency:\n  reported: CNY\n  canonical: 人民币\n"
        "entries:\n  - field_id: bs.total_assets\n    statement: balance_sheet\n"
        "    column_name: 资产总计\n",
    )
    with pytest.raises(ValueError, match="scope_required"):
        load_akshare_mapping("balance_sheet", tmp_path)


def test_一列映射到两个字段即拒绝加载(tmp_path):
    """取哪个由 `dict` 插入顺序决定，而那不是任何人的决定。"""
    _write_mapping(
        tmp_path,
        "balance_sheet",
        "statement: balance_sheet\nmapping_version: 1\n"
        "currency:\n  reported: CNY\n  canonical: 人民币\n"
        "scope_required: 合并期末\n"
        "entries:\n"
        "  - field_id: bs.total_assets\n    statement: balance_sheet\n"
        "    column_name: 资产总计\n"
        "  - field_id: bs.total_liabilities\n    statement: balance_sheet\n"
        "    column_name: 资产总计\n",
    )
    with pytest.raises(ValueError, match="重复"):
        load_akshare_mapping("balance_sheet", tmp_path)


def test_对照映射是子集而不是相等且不许有孤儿条目():
    """**与 PDF 侧方向不同**，这一条必须写清楚，否则下一个人会照抄相等断言。

    PDF 侧是**相等**（`assert_mapping_covers_definitions`）：它是权威源，
    少一条就有字段没人抽。

    AKShare 侧只能是**子集**：`notes.*` 的复选框、`kpi.*` 的披露值
    在三张报表里结构上就不存在，要求相等等于逼着编一条永远取不到的规则（`F-2`）。

    但**「多一条」在两侧同样是缺陷**：一条没有任何定义引用的对照规则
    不被任何东西校验，会一直活着直到有人当它是对的。
    """
    from extractor.mapping import declared_field_ids

    tables = load_all_akshare_mappings()
    mapped = {e.field_id for t in tables.values() for e in t.entries}
    declared = declared_field_ids()
    assert mapped <= declared, f"孤儿条目：{sorted(mapped - declared)}"
    # **方向不同这件事本身要锁住**：哪天有人把它改成相等断言，这一条会红。
    assert mapped != declared
    assert_akshare_mapping_within_definitions()


def test_映射表里出现未声明字段即报错(tmp_path):
    _write_mapping(
        tmp_path,
        "balance_sheet",
        _minimal_mapping("balance_sheet", "bs.不存在的字段", "资产总计"),
    )
    _write_mapping(
        tmp_path,
        "income_statement",
        _minimal_mapping("income_statement", "is.net_profit", "净利润"),
    )
    _write_mapping(
        tmp_path,
        "cash_flow",
        _minimal_mapping(
            "cash_flow",
            "cfs.net_cash_flow_from_operating_activities",
            "经营活动产生的现金流量净额",
        ),
    )
    with pytest.raises(AssertionError, match="定义里没有"):
        assert_akshare_mapping_within_definitions(tmp_path)


# --------------------------------------------------------------------------
# 二、数值转换：全仓唯一一处，且走 Decimal(repr(v))（C-6 / D-029 判据 3）
# --------------------------------------------------------------------------


def test_参照值不把浮点尾巴带进来():
    """`Decimal(48697611501.2)` = `48697611501.2000007629...`，凭空造出差额。"""
    reference = _reference(
        field_id="bs.total_current_liabilities_period_end",
        column_name="流动负债合计",
        raw=48697611501.2,
    )
    assert reference.as_decimal() == Decimal("48697611501.2")
    assert reference.as_decimal() != Decimal(48697611501.2)


def _is_name(node, name: str) -> bool:
    return isinstance(node, ast.Name) and node.id == name


def _is_decimal(func) -> bool:
    return _is_name(func, "Decimal") or (
        isinstance(func, ast.Attribute) and func.attr == "Decimal"
    )


def test_全仓只有一个_akshare_数值转换点():
    """`D-029` 判据 3 的机械形态：AST 级，不是靠人记得。

    两个方向都查：
    ① `src/` 下 `Decimal(repr(...))` 只许出现一次，且必须在 `crosscheck.py` 里；
    ② `crosscheck.py` 里凡是参数不是字面量的 `Decimal(...)` 调用，只许是那一处。
    第二条拦的是「又加了一个 `Decimal(raw)`」——它不含 `repr`，第一条查不出来。
    """
    repr_sites = []
    for path in sorted((REPO_ROOT / "src").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and _is_decimal(node.func)):
                continue
            arg = node.args[0] if node.args else None
            if isinstance(arg, ast.Call) and _is_name(arg.func, "repr"):
                repr_sites.append((path.name, node.lineno))
    assert len(repr_sites) == 1, f"Decimal(repr(...)) 出现在多处：{repr_sites}"
    assert repr_sites[0][0] == "crosscheck.py"

    source = (REPO_ROOT / "src" / "extractor" / "crosscheck.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    converter = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_reference_decimal"
    )
    allowed = set(ast.walk(converter))
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and _is_decimal(node.func)):
            continue
        arg = node.args[0] if node.args else None
        if isinstance(arg, ast.Constant):
            continue
        assert node in allowed, (
            f"crosscheck.py:{node.lineno} 有第二个非字面量的 Decimal(...) 转换点。"
            "AKShare 侧的 float 必须全部走 _reference_decimal（D-029 判据 3）。"
        )


#: 全 `src/` 下**非字面量** `Decimal(...)` 的清点：`(文件, 函数, 一句话理由)`。
#:
#: **这不是豁免名单，是清单。** 豁免名单让某几处**不受检查**；
#: 本清单要求**每一处都被点名并写明理由**，多出一处就红。
#: 与 `record.MERGE_SEMANTICS` / `check_xrefs.KNOWN_COLLISIONS` 是同一个机制。
#:
#: 复核 `RV-7` 记的洞正是这里：原来方向②**只扫 `crosscheck.py`**，
#: 于是 `Decimal(v)`（正是 `D-029` 判据 3 要防的那个）放在 `src/` 下任何别的文件里，
#: 两道检查都看不见 —— 复核实测 M15：加进 `units.py`，41 passed 全绿。
DECIMAL_CONVERSION_SITES = {
    ("extractor/crosscheck.py", "_reference_decimal"): (
        "AKShare 侧 float → Decimal 的**唯一**转换点。用 repr() 而不是 str()，"
        "是为了拿到能唯一还原该 float 的十进制串（D-029 判据 3）。"
    ),
    ("extractor/formula.py", "_tokenize"): (
        "把**公式串**里的数字字面量转成 Decimal。输入是我们自己写的 metrics/*.yaml，"
        "不是任何外部数据源，与 AKShare 无关。"
    ),
    ("agent/answer.py", "by_field"): (
        "把**合成夹具**里的数值转成 Decimal，喂给全仓唯一的算术求值器。"
        "输入是 `eval/frozen-01/fixtures/` 下我们自己写的 YAML，与 AKShare 无关。"
        "⚠️ 走 str() 不是 repr()：夹具里写的本来就是十进制字面量，"
        "不是先经过二进制浮点的数 —— 用 repr() 反而会把 YAML 解析出的 float 误差固化进来。"
    ),
    ("extractor/locate.py", "parse_amount"): (
        "把**PDF 版面文本**里的金额串转成 Decimal（去掉千分位逗号）。"
        "输入是年报原文，与 AKShare 无关。"
    ),
    ("agent/answer.py", "_as_number"): (
        "把**真实年报抽取结果**（`data/extracted/*.yaml`，`kind: real`）里带引号的"
        "数值串转回 Decimal。输入是 `extractor export` 的产物，源头是年报 PDF，与 AKShare 无关。"
        "⚠️ 文件里之所以加引号，正是为了**不经过 float** —— "
        "14 位以上有效数字被 YAML 读成 float 会悄悄变掉。所以这里 str() 拿到的"
        "本来就是十进制字面量，不存在 repr() 要还原的二进制误差。"
    ),
    ("extractor/export.py", "_comparable"): (
        "只用来**比较**：把「人工核对清单里写的」与「抽取器给的」化到同一种可比形式，"
        "好让 `48697611501.20` 与 `48697611501.2` 判成同一个数。"
        "⚠️ 它的返回值**不进任何产物**，只用于相等判定 —— "
        "两侧输入分别是我们自己写的 YAML 清单与抽取记录，与 AKShare 无关。"
    ),
}


def _enclosing_function(tree: ast.AST, target: ast.AST) -> str:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if any(sub is target for sub in ast.walk(node)):
                return node.name
    return "<模块级>"


def test_全_src_下每一处非字面量Decimal都被点名登记():
    """`RV-7` 的收口：把方向②从「只扫 crosscheck.py」扩到**全 `src/`**。

    ⚠️ **没有扩成「只许一处」**，因为那会误伤两处正当的转换：
    `formula` 解析公式串里的数字字面量、`locate` 解析 PDF 版面上的金额串 ——
    两者的输入都不是 AKShare，与 `D-029` 判据 3 无关。
    AST **看不出一个 `Decimal(...)` 的输入是从哪来的**，所以「只许一处」这条
    机械规则在这里表达不了要表达的东西。

    ⇒ 改成**逐处点名**：多一处就红，红了要么去掉，要么进清单并写明输入是什么。
    这样新增的 `Decimal(v)` 不可能再像 M15 那样悄悄躺在 `units.py` 里。

    ## 这条**证明不了**什么

    它保证的是「每一处转换都被点名」，**不是**「AKShare 的 float 只从一处流过」。
    后者需要数据流分析，AST 给不了。`D-029` 判据 3 的措辞已于 2026-08-31
    同步收窄到这个强度 —— **声称的范围不许大于被证明的范围**。

    ⚠️ **还有一条更具体的漏，是跑负控制时当场发现的**：
    `_is_decimal` 按**名字**认（`Decimal` / `x.Decimal`），
    所以 `from decimal import Decimal as _D` 之后写 `_D(v)`，**这条检查看不见**。
    实测：用别名写的探针本条**不红**，换成本模块已有的 `Decimal` 名字才红。
    ⇒ 它挡的是**无意间新增**的转换点，**挡不住有意绕开**的写法。
    不补这个洞是因为补法（追踪 import 别名）会把一条简单检查变成一个
    小型解析器，而它要防的是「顺手写了一个」不是「有人存心藏」——
    **但这句限定必须写在这里，不能让读者以为它挡得住后者。**
    """
    found = {}
    for path in sorted((REPO_ROOT / "src").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and _is_decimal(node.func)):
                continue
            arg = node.args[0] if node.args else None
            if isinstance(arg, ast.Constant):
                continue
            rel = path.relative_to(REPO_ROOT / "src").as_posix()
            found[(rel, _enclosing_function(tree, node))] = node.lineno

    unregistered = sorted(k for k in found if k not in DECIMAL_CONVERSION_SITES)
    assert unregistered == [], (
        f"这些非字面量 Decimal(...) 转换点没有登记：{unregistered}。"
        "要么去掉，要么进 DECIMAL_CONVERSION_SITES 并写明它的输入是什么 —— "
        "AKShare 侧的 float 只许走 _reference_decimal（D-029 判据 3）。"
    )
    stale = sorted(k for k in DECIMAL_CONVERSION_SITES if k not in found)
    assert stale == [], (
        f"清单里这些位置已经不存在了：{stale}。"
        "清单必须跟着代码走 —— 一份含过期条目的清单会让下一个人以为那里还有转换。"
    )


# --------------------------------------------------------------------------
# 三、判定：一致 / 不一致 / 不可比是三个取值（D-029）
# --------------------------------------------------------------------------


def test_容差是具名常量且等于一分钱():
    """`D-029` 判据 1：容差是具名常量，不是散落的字面量。"""
    assert DISAGREEMENT_TOLERANCE == Decimal("0.01")
    assert isinstance(DISAGREEMENT_TOLERANCE, Decimal)


def test_两值一致时不置任何_flag():
    result = cross_validate(_record(), _reference())
    assert result.verdict is CrossCheckVerdict.AGREES
    assert result.flags == ()
    assert result.difference == Decimal("0.00")


def test_差额恰好等于容差时判一致():
    """边界写死成测试：`<=` 不是 `<`。一分钱正好是报表的最小可分辨单位。"""
    result = cross_validate(_record(value=Decimal("272699660092.26")), _reference())
    assert result.difference == Decimal("0.01")
    assert result.verdict is CrossCheckVerdict.AGREES


def test_差额超出容差时置_source_disagreement_且两个值都在证据链里():
    result = cross_validate(_record(value=Decimal("272699660092.27")), _reference())
    assert result.verdict is CrossCheckVerdict.DISAGREES
    assert source_disagreement_flag() in result.flags
    assert result.pdf_value is not None
    assert result.reference_value is not None
    assert result.pdf_value == Decimal("272699660092.27")
    assert result.reference_value == Decimal("272699660092.25")


def test_不一致时_pdf_值不被参照值覆盖():
    """`D-013`：PDF 原文是权威源。对照只产出判定，不改写记录。"""
    record = _record(value=Decimal("1.00"))
    result = cross_validate(record, _reference())
    assert result.verdict is CrossCheckVerdict.DISAGREES
    assert record.value == Decimal("1.00")
    assert result.pdf_value == Decimal("1.00")
    assert result.pdf_value != result.reference_value
    assert result.to_dict()["pdf_value"] == "1.00"
    assert result.to_dict()["reference_value"] == "272699660092.25"


def test_flag_名逐字取自_flags_yaml():
    """不许在代码里另写一个拼写。改了 YAML 而代码没改，应当是加载期报错。"""
    raw = yaml.safe_load(
        (REPO_ROOT / "metrics" / "_flags.yaml").read_text(encoding="utf-8")
    )
    names = {f["name"]: f for f in raw["flags"]}
    assert source_disagreement_flag() in names
    assert names[source_disagreement_flag()]["scope"] == "system"


def test_不可比与不一致是两个不同的取值且不合并():
    """`D-029` 判据 2 的负向用例。

    混同二者，`source_disagreement` 会在单位错配时几乎全部触发，
    而那时看到的噪音会被当成数据质量问题去查 —— 查错方向。
    """
    unreadable = cross_validate(_record(unit="担"), _reference())
    assert unreadable.verdict is CrossCheckVerdict.INCOMPARABLE
    assert unreadable.verdict is not CrossCheckVerdict.DISAGREES
    assert unreadable.incomparable_reason is IncomparableReason.UNIT_UNDETERMINED
    assert unreadable.flags == ()
    assert unreadable.to_dict()["verdict"] == "INCOMPARABLE"
    assert unreadable.to_dict()["verdict"] != "DISAGREES"


def test_单位不同但都读得出时先归一化再比():
    """`AKSHARE-A2 §5`：单位一致不等于可以删掉归一化那一步。"""
    result = cross_validate(
        _record(value=Decimal("27269966.009225"), unit="万元"),
        _reference(),
    )
    assert result.verdict is CrossCheckVerdict.AGREES
    assert result.pdf_value == Decimal("272699660092.250000")
    assert result.to_dict()["pdf_unit"] == "万元"


def test_参照值为_NaN_时判不可比而不是当零():
    """`C-7`。⚠️ 这一条挡的是一次**伪造出来的一致**：

    茅台四个「格子空 = 0」的字段（短期借款 / 交易性金融负债 / 长期借款 / 应付债券）
    在 AKShare 侧全是 `NaN`。把 `NaN` 当成 0，它们会与 PDF 侧的 0 比出 `AGREES` ——
    **报出一个从未被建立过的跨源一致**。那正是本项目记了六次的那个形状。
    """
    result = cross_validate(
        _record(
            field_id="bs.short_term_borrowings",
            value=Decimal("0"),
            cell_state=CellState.EMPTY_CELL,
            retrieval=RetrievalOutcome.GOT_VALUE,
        ),
        _reference(field_id="bs.short_term_borrowings", column_name="短期借款", raw=None),
    )
    assert result.verdict is CrossCheckVerdict.INCOMPARABLE
    assert result.incomparable_reason is IncomparableReason.REFERENCE_NAN
    assert result.verdict is not CrossCheckVerdict.AGREES
    assert result.flags == ()


def test_币种别名必须在映射文件里显式声明():
    """AKShare 印 `CNY`，PDF 印 `人民币`。这是**别名**，不是不可比 ——

    但它必须在映射文件里写出来、随 `mapping_version` 一起冻结，
    不许在代码里内置一张「大家都知道」的换算表。
    """
    table = load_akshare_mapping("balance_sheet")
    assert table.currency_reported == "CNY"
    assert table.currency_canonical == "人民币"

    mismatched = cross_validate(_record(currency="美元"), _reference())
    assert mismatched.verdict is CrossCheckVerdict.INCOMPARABLE
    assert mismatched.incomparable_reason is IncomparableReason.CURRENCY_MISMATCH


def test_非合并口径的参照行判不可比():
    """`类型` 列声明的是合并还是母公司。母公司数据与合并报表比是另一种 `A-9`。"""
    result = cross_validate(_record(), _reference(scope="母公司期末"))
    assert result.verdict is CrossCheckVerdict.INCOMPARABLE
    assert result.incomparable_reason is IncomparableReason.SCOPE_NOT_CONSOLIDATED


@pytest.mark.parametrize("empty_scope", ["", "None"])
def test_类型列缺失或为空时判不可比而不是默认放行(empty_scope):
    """🔴 `RV-1`（独立复核 2026-08-28 查出）：这里原来是 fail-**open**。

    原实现 `if reference.scope and reference.scope != "合并期末"` ——
    前半个 `and` 让空 scope **直接跳过整条判定**，字段被当作合并口径参与对照，
    输出里照样是 `AGREES`。

    而**币种与报告期两条同类闸门在同样输入下都是 fail-closed**。
    三条同类判定里两条一个行为、一条另一个行为，且不一致的恰好是
    加载器报错文案写着「不声明合并口径就等于默认接受母公司数据参与对照」的那一条。
    """
    result = cross_validate(_record(), _reference(scope=empty_scope))
    assert result.verdict is CrossCheckVerdict.INCOMPARABLE
    assert result.incomparable_reason is IncomparableReason.SCOPE_NOT_CONSOLIDATED
    assert result.verdict is not CrossCheckVerdict.AGREES


def test_合并口径取自映射文件而不是硬编码字面量():
    """🔴 `RV-2`（独立复核查出）：`scope_required` 原来是**被加载、被校验、
    但从不被消费**的配置键 —— 判定里硬编码 `"合并期末"`，
    三份 YAML 里把它改成任何别的值都零效果。

    而 `test_映射表不声明合并口径即拒绝加载` 让它看起来是被锁住的：
    那条锁的是**这个键必须存在**，不是**这个键起作用**。两者差得很远。

    本条锁的是后者：换一个 `scope_required`，判定必须跟着换。
    """
    # 映射文件说要「母公司期末」时，一份「合并期末」的参照行就该判不可比
    result = cross_validate(
        _record(), _reference(scope="合并期末", scope_required="母公司期末")
    )
    assert result.verdict is CrossCheckVerdict.INCOMPARABLE
    assert result.incomparable_reason is IncomparableReason.SCOPE_NOT_CONSOLIDATED

    # 反过来也要成立，否则上面那条可能只是「凡是不等于合并期末就红」
    ok = cross_validate(
        _record(), _reference(scope="母公司期末", scope_required="母公司期末")
    )
    assert ok.verdict is CrossCheckVerdict.AGREES

    # 且真实映射文件里那个值确实被带进了 ReferenceValue
    payload = load_reference_payload(FIXTURE)
    tables = load_all_akshare_mappings()
    references = references_from_payload(payload, tables)
    assert references["bs.total_assets"].scope_required == "合并期末"
    assert (
        references["bs.total_assets"].scope_required
        == tables["balance_sheet"].scope_required
    )


def test_报告期对不上时判不可比():
    result = cross_validate(_record(), _reference(period="20221231"), period="20231231")
    assert result.verdict is CrossCheckVerdict.INCOMPARABLE
    assert result.incomparable_reason is IncomparableReason.PERIOD_MISMATCH


def test_参照表里没有这一列时判不可比而不是判一致():
    result = cross_validate(
        _record(field_id="kpi.roe_weighted_average_disclosed", value=Decimal("34.19")),
        _reference(
            field_id="kpi.roe_weighted_average_disclosed",
            column_name="",
            present=False,
            raw=None,
        ),
    )
    assert result.verdict is CrossCheckVerdict.INCOMPARABLE
    assert result.incomparable_reason is IncomparableReason.REFERENCE_COLUMN_ABSENT


def test_pdf_侧取不到值时判不可比():
    result = cross_validate(
        _record(
            value=None,
            status=ExtractionStatus.REFUSED,
            retrieval=RetrievalOutcome.ATTEMPTED_UNKNOWN,
            cell_state=None,
        ),
        _reference(),
    )
    assert result.verdict is CrossCheckVerdict.INCOMPARABLE
    assert result.incomparable_reason is IncomparableReason.PDF_VALUE_UNREADABLE


# --------------------------------------------------------------------------
# 四、批次：触发占比写进证据链（D-029 判据 4，反转条件）
# --------------------------------------------------------------------------


def _batch_with(values: dict) -> ExtractionBatch:
    batch = ExtractionBatch.open("600519", 2023, SHA_A)
    for field_id, value in values.items():
        batch.add_record(_record(field_id=field_id, value=Decimal(value)))
    return batch


def test_每批算出触发占比并把分子分母都写进证据链():
    batch = _batch_with(
        {
            "bs.total_assets": "1.00",
            "bs.total_liabilities": "2.00",
            "bs.inventory": "3.00",
        }
    )
    references = {
        "bs.total_assets": _reference(raw=1.0),
        "bs.total_liabilities": _reference(
            field_id="bs.total_liabilities", column_name="负债合计", raw=2.0
        ),
        "bs.inventory": _reference(
            field_id="bs.inventory", column_name="存货", raw=999.0
        ),
    }
    outcome = cross_validate_batch(batch, references)
    payload = outcome.to_dict()
    assert payload["disagreements"] == 1
    assert payload["comparable"] == 3
    assert payload["disagreement_ratio"] == "1/3"
    assert outcome.miscalibration_suspected is False


def test_触发占比超过三分之一时标注疑为档位选错():
    """`D-029` 的反转条件：**可机械判定的比例**，不是「觉得不对就改」。"""
    batch = _batch_with({"bs.total_assets": "1.00", "bs.total_liabilities": "2.00"})
    references = {
        "bs.total_assets": _reference(raw=1.0),
        "bs.total_liabilities": _reference(
            field_id="bs.total_liabilities", column_name="负债合计", raw=999.0
        ),
    }
    outcome = cross_validate_batch(batch, references)
    assert outcome.disagreement_ratio > MISCALIBRATION_THRESHOLD
    assert outcome.miscalibration_suspected is True
    assert "疑为档位选错" in outcome.to_dict()["note"]


def test_不可比的字段不进占比的分母():
    """分母是**可比的**那些。把不可比也算进去，比例会被一堆判不了的字段稀释。"""
    batch = _batch_with({"bs.total_assets": "1.00", "bs.short_term_borrowings": "0.00"})
    references = {
        "bs.total_assets": _reference(raw=999.0),
        "bs.short_term_borrowings": _reference(
            field_id="bs.short_term_borrowings", column_name="短期借款", raw=None
        ),
    }
    outcome = cross_validate_batch(batch, references)
    assert outcome.comparable == 1
    assert outcome.incomparable == 1
    assert outcome.disagreement_ratio == 1


def test_一个可比字段都没有时占比是零而不是崩():
    batch = _batch_with({"bs.short_term_borrowings": "0.00"})
    references = {
        "bs.short_term_borrowings": _reference(
            field_id="bs.short_term_borrowings", column_name="短期借款", raw=None
        )
    }
    outcome = cross_validate_batch(batch, references)
    assert outcome.comparable == 0
    assert outcome.disagreement_ratio == 0
    assert outcome.miscalibration_suspected is False
    assert "没有任何可比字段" in outcome.to_dict()["note"]


# --------------------------------------------------------------------------
# 五、降级：对照源挂了不把已经算出来的数带下水
# --------------------------------------------------------------------------


def _raise(exc):
    def _fetcher(*args, **kwargs):
        raise exc

    return _fetcher


def test_akshare_取不到时返回拒答而不是抛异常():
    from extractor import crosscheck

    outcome = crosscheck.fetch_reference(
        "600519", 2023, fetcher=_raise(RuntimeError("Max retries exceeded"))
    )
    assert isinstance(outcome, Refusal)
    assert outcome.code is RefusalCode.UNAVAILABLE
    assert "akshare" in outcome.source
    assert outcome.source == SOURCE_AKSHARE


def test_akshare_没装时也是拒答不是_ImportError():
    from extractor import crosscheck

    outcome = crosscheck.fetch_reference(
        "600519", 2023, fetcher=_raise(ImportError("No module named 'akshare'"))
    )
    assert isinstance(outcome, Refusal)
    assert outcome.code is RefusalCode.UNAVAILABLE
    assert "crosscheck" in outcome.detail


def test_对照失败不改动已经算出的指标值():
    """`D-013` 的另一半：对照缺失不是计算失败。"""
    from extractor import crosscheck

    batch = _batch_with({"bs.total_assets": "272699660092.25"})
    before = [r.value for r in batch.records]

    outcome = crosscheck.fetch_reference(
        "600519", 2023, fetcher=_raise(RuntimeError("down"))
    )
    assert isinstance(outcome, Refusal)
    assert [r.value for r in batch.records] == before
    assert batch.records[0].value == Decimal("272699660092.25")


# --------------------------------------------------------------------------
# 七、固件回放：真实数据上的端到端对照
# --------------------------------------------------------------------------


def test_固件回放不联网也能把参照值全部取出来():
    payload = load_reference_payload(FIXTURE)
    tables = load_all_akshare_mappings()
    references = references_from_payload(payload, tables)
    assert not isinstance(references, Refusal)
    assert len(references) == sum(len(t.entries) for t in tables.values())
    assert references["bs.total_assets"].as_decimal() == Decimal("272699660092.25")
    assert references["bs.short_term_borrowings"].raw is None
    assert references["bs.short_term_borrowings"].present is True


def test_固件里九个已核对科目全部判一致():
    """`AKSHARE-A2 §2` 的九个科目，绝对差全部 0.00。这是**已核对过的基线**。"""
    payload = load_reference_payload(FIXTURE)
    tables = load_all_akshare_mappings()
    references = references_from_payload(payload, tables)
    checked = {
        "bs.total_assets": "272699660092.25",
        "bs.total_liabilities": "49043190797.43",
        "bs.total_equity": "223656469294.82",
        "bs.total_current_assets": "225172517821.28",
        "bs.total_current_liabilities_period_end": "48697611501.20",
        "bs.inventory": "46435185061.53",
        "is.operating_revenue_current": "147693604994.14",
        "is.operating_cost": "11867273851.78",
        "cfs.net_cash_flow_from_operating_activities": "66593247721.09",
    }
    batch = _batch_with(checked)
    outcome = cross_validate_batch(batch, references)
    assert outcome.comparable == 9
    assert outcome.disagreements == 0
    assert outcome.miscalibration_suspected is False
    for result in outcome.results:
        assert result.verdict is CrossCheckVerdict.AGREES
        assert result.difference == Decimal("0.00")


def test_重录固件不会删掉负控制赖以成立的那几列():
    """🔴 `RV-6`（独立复核 2026-08-28 查出）：`--record` 原先会毁掉固件。

    原 `keep` 只保留「已映射的列 + 元数据列」，于是：

    ```
    balance_sheet     147 列 -> 22 列（丢 125）
    income_statement   83 列 -> 14 列（丢 69）
    cash_flow          71 列 ->  9 列（丢 62）
    ```

    被丢掉的里面有四列**正是负控制的证据本身**。最狠的是
    `应付票据及应付账款` —— `test_应付票据及应付账款不匹配应付账款` 直接从固件读它，
    裁掉之后那条测试**不是变红，是 `KeyError` 直接 ERROR**，
    而它是本模块唯一咬得住「逐字相等 → 子串包含」这个变异的用例（`RV-4`）。

    ⇒ **一次「正规路径」的重录，会静默删掉四条论据里的四条。**
    这是「留证在接线时被丢掉」的又一个形状，只不过丢它的是我们自己写的重录工具。
    """
    from extractor.crosscheck import EVIDENCE_COLUMNS, keep_columns

    payload = load_reference_payload(FIXTURE)
    tables = load_all_akshare_mappings()

    for statement, table in tables.items():
        keep = keep_columns(table)
        row = payload[statement]["row"]
        survivors = {k for k in row if k in keep}
        # 已映射的列一个都不能丢
        for entry in table.entries:
            assert entry.column_name in keep, f"{statement}: 丢了已映射列 {entry.column_name}"
        # 判定要用的三列一个都不能丢
        for meta in ("报告日", "币种", "类型"):
            assert meta in keep, f"{statement}: 丢了判定用的元数据列 {meta}"
        assert survivors, statement

    # 四列证据必须全部活下来 —— 逐列点名，不是数个数
    all_keep = set().union(*(keep_columns(t) for t in tables.values()))
    for column in EVIDENCE_COLUMNS:
        assert column in all_keep, f"重录会删掉负控制的证据列 {column}"

    # 且这四列在**当前固件里确实存在** —— 否则上面那条锁的是一个空承诺
    present = {k for block in payload.values() for k in block["row"]}
    for column in EVIDENCE_COLUMNS:
        assert column in present, f"{column} 不在固件里，EVIDENCE_COLUMNS 记了一个不存在的列"


def test_固件覆盖率是子集不是全集_并把缺口点名():
    """24 / 30。缺的 6 个不是漏了，是 AKShare 三张表里结构上就没有。"""
    from extractor.mapping import declared_field_ids

    tables = load_all_akshare_mappings()
    mapped = {e.field_id for t in tables.values() for e in t.entries}
    missing = declared_field_ids() - mapped
    assert missing == {
        "is.operating_revenue_prior_as_presented",
        "kpi.roe_weighted_average_disclosed",
        "notes.business_combination_type",
        # ↓ 2026-08-28 wave 5 按 D-020 新增（30 → 31）。同样是附注复选项，
        #   AKShare 的三张报表里结构上不存在 —— 与上一条同因，不是漏了。
        "notes.consolidation_scope_change",
        "notes.nonrecurring_pl_net_attributable_to_parent",
        "notes.reporting_period_months",
        "notes.restatement_flag",
    }
    assert len(mapped) == 24
    assert len(declared_field_ids()) == 31


def test_RV3_没有参照值的记录不再被静默丢弃():
    """`RV-3`：`extract_batch` 25 条进去、`cross_validate_batch` 24 条出来，
    而 `to_dict()` 里**没有任何一项**告诉读者少了谁。

    与 `C-15`（「20 个里 0 个不一致」被读成「24 个全核过」）同形，且高了一层：
    **从 JSON 只能看到 24，看不到 25。**
    """
    batch = _batch_with({"bs.total_assets": "100.00", "bs.total_liabilities": "40.00"})
    refs = {"bs.total_assets": _reference(raw=100.0)}

    outcome = cross_validate_batch(batch, refs)
    payload = outcome.to_dict()

    assert outcome.unreferenced == ("bs.total_liabilities",)
    assert payload["unreferenced"] == ["bs.total_liabilities"]
    # 分子分母之外还要能看出**批次里到底有几条**。
    assert payload["records_in_batch"] == 2
    assert len(payload["results"]) == 1
    # 只加字段不改 note，读 note 的人仍然只看到那 1 条。
    assert "根本没进对照" in payload["note"]
    assert "bs.total_liabilities" in payload["note"]


def test_RV3_没进对照与不可比是两件事():
    """`unreferenced` **不是** `INCOMPARABLE`：
    前者「压根没进对照」，后者「进了对照但判不了」。合并会丢掉一半信息。
    """
    batch = _batch_with({"bs.total_assets": "100.00", "bs.total_liabilities": "40.00"})
    outcome = cross_validate_batch(batch, {"bs.total_assets": _reference(raw=100.0)})
    assert outcome.incomparable == 0
    assert len(outcome.unreferenced) == 1


def test_RV8_取flag那一行被锁住(monkeypatch):
    """`RV-8`：把 `source_disagreement_flag()` 换成硬编码字面量，**41 条全绿**。

    锁只存在一个方向 —— 改 YAML ⇒ 函数抛错 ⇒ `test_flag_名逐字取自_flags_yaml` 红。
    **改调用点则无人发现。** 本条补上另一个方向：
    monkeypatch 掉函数返回值，断言 `cross_validate` 的输出**跟着变**。
    """
    import extractor.crosscheck as cc

    monkeypatch.setattr(cc, "source_disagreement_flag", lambda *a, **k: "被换掉的标记名")
    record = _record(value=Decimal("100.00"))
    result = cc.cross_validate(record, _reference(raw=999.0))

    assert result.verdict is CrossCheckVerdict.DISAGREES
    assert result.flags == ("被换掉的标记名",), (
        "取 flag 那一行没有走 source_disagreement_flag() —— "
        "改调用点（换成硬编码字面量）不会被任何测试发现（RV-8）"
    )


def test_RV9_三态语义只有一个定义点():
    """`RV-9`：`_pdf_amount` 与 `reconcile._readable_amount` 曾是复制粘贴的两份实现，
    四态完全相同而**没有任何测试锁住两者一致**。

    分叉的表现形式是「同一条记录，勾稽闸门当 0、跨源对照当缺失」——
    两边各自都说得通，没有任何东西会报错。
    """
    import inspect
    import textwrap

    from extractor import crosscheck as cc
    from extractor import reconcile as rc
    from extractor.record import readable_amount

    def _delegates(fn) -> tuple[bool, int]:
        """走 AST，**不做源码子串匹配**。

        初版写的是 `assert "readable_amount" in inspect.getsource(fn)` ——
        造回归时当场发现它**不会红**：把四态重新内联回去之后，
        函数上方那段解释「语义全部在 record.readable_amount」的**注释**还在，
        子串照样命中。⇒ 一条查源码文本的断言，会被**注释**满足。
        这正是本仓反复记的那个形状，只不过这次出现在我自己写的负控制上。
        """
        tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
        calls = {
            n.func.id
            for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        }
        branches = sum(1 for n in ast.walk(tree) if isinstance(n, ast.If))
        return "readable_amount" in calls, branches

    for fn in (cc._pdf_amount, rc._readable_amount):
        delegates, branches = _delegates(fn)
        assert delegates, f"{fn.__name__} 没有委派给 record.readable_amount"
        # **委派之外不许再有分支**：四态判断只许有一份，重新内联回去就会带回 4 个 `if`。
        assert branches == 0, f"{fn.__name__} 里还有 {branches} 处分支，语义可能又分叉了"

    assert readable_amount(None) is None
