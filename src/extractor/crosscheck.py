"""AKShare 对照通路 —— **对照源，不是权威源**（`D-013`）。

## 这个模块存在的理由

`D-013` 写死了两件事：财务数值以年报 PDF 原文为准；口径不披露的二手源不得作权威源。
所以本模块**只产出判定，不改写任何抽取记录**。不一致时，两个值都进证据链，
PDF 值仍是那个被引用的值。不允许「取平均」「取更接近整数的那个」「取 AKShare 的」
这类静默选择 —— 那些都是在用一个没有口径说明的源覆盖一个有页码有出处的源。

## 为什么置位逻辑不塞进 `active_flags()`

`source_disagreement` 在 `metrics/_flags.yaml` 里 `scope: system`，**没有 trigger 字段**。
`resolve.active_flags()` 结构上只遍历定义文件里声明的 `definition` 域标记，
system 域标记按 `R4` 根本不会出现在那个列表里。

把「需要访问第二个数据源」的逻辑混进单期取数路径，会让 `active_flags` 承担
它结构上不该承担的事。惯例已有先例：`resolve.check_comparable()` 就是一个
与 `active_flags()` **平行的独立判定函数**。本模块的 `cross_validate()` 照那个形状写。

## 三个取值，不是两个

`AGREES` / `DISAGREES` / `INCOMPARABLE`。第三个不是「另一种不一致」——

把「不可比」混进「不一致」，`source_disagreement` 会在单位错配、口径错配、
参照列缺失时**几乎全部触发**，而那时看到的噪音会被当成数据质量问题去查。
`D-029` 决策 2 把这条写死了：单位无法确定时判「不可比」，`source_disagreement`
**不置位**，且「不可比」这件事本身要进证据链。

🔴 **最危险的那一支是 `REFERENCE_NAN`**：茅台四个「格子空 = 0」的字段
（短期借款 / 交易性金融负债 / 长期借款 / 应付债券）在 AKShare 侧全是 `NaN`。
把 `NaN` 当 0，它们会与 PDF 侧的 0 比出 `AGREES` —— **报出一个从未被建立过的跨源一致**。
那正是本项目已经记了六次的形状：自证机制说通过了，但它证明的不是它声称证明的事。

## 录制固件

⚠️ **本节 2026-08-28 改写过 —— 原文有两句是错的**（`RV-10`，独立复核查出）。
原文写「对照默认走离线固件」「`--record` 是唯一会 import akshare 的入口」，
**两句都不成立**：不给 `--reference` 也不给 `--record` 时，默认路径就是联网。
同一个文件里 `--reference` 的 help 写的「默认就该给这个 —— 不给才联网」才是对的，
两处自相矛盾。下面是照代码重写的。

**三条路径，只有第一条不联网**：

| 给的 flag | 行为 |
|---|---|
| `--reference PATH` | 读录制好的响应回放，**不联网、不 import akshare** |
| `--record PATH` | 联网取一份真实响应并写成固件 |
| 都不给 | **联网**（取不到则 `Refusal(UNAVAILABLE)`，退出码 3，不抛异常） |

**全部测试走第一条**，断网可跑；`import akshare` 只出现在 `_live_fetcher` 里一处。

    python -m extractor crosscheck --stock 600519 --year 2023 \
        --pdf data/raw/600519_2023.pdf --record tests/fixtures/akshare_600519_2023.json

⚠️ **`--record` 产出的是裁剪过的固件，不是原始返回。** 仓库里现有那份来自
`0b312da`，是**未裁剪**的原始返回（`AKSHARE-A2 §2` 逐字这么写的）。
重录会把它换成裁剪版 —— 裁剪边界见 `keep_columns()` 与 `EVIDENCE_COLUMNS`。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable, Mapping

import yaml

from semantic_layer.resolve import Refusal, RefusalCode

from .record import CellState, ExtractionBatch, ExtractionRecord, RetrievalOutcome
from .units import UnitMismatchError, scale_of, to_yuan

__all__ = [
    "DEFAULT_AKSHARE_MAPPING_DIR",
    "DISAGREEMENT_TOLERANCE",
    "MISCALIBRATION_THRESHOLD",
    "REQUIRED_ENTRY_KEYS",
    "SOURCE_AKSHARE",
    "AKSHARE_STATEMENTS",
    "AkshareEntry",
    "AkshareMappingTable",
    "BatchCrossCheck",
    "CrossCheckResult",
    "CrossCheckVerdict",
    "IncomparableReason",
    "ReferenceValue",
    "assert_akshare_mapping_within_definitions",
    "cross_validate",
    "cross_validate_batch",
    "fetch_reference",
    "load_akshare_mapping",
    "load_all_akshare_mappings",
    "load_reference_payload",
    "references_from_payload",
    "source_disagreement_flag",
]

#: 责任方标识（`L-9`）。稳定串，可逐字比对（`J-6`）。
SOURCE_AKSHARE = "akshare:stock_financial_report_sina"

#: 跨源不一致的判定容差（`D-029` 判据 1）。**一个具名常量，不是散落的字面量。**
#:
#: `Decimal("0.01")` 元 = 报表「精确到分」的最小可分辨单位。
#: 比较用 `<=`：差额恰好一分钱判**一致**，因为那正好是两个源各自舍入到分之后
#: 仍然能表示同一个数的极限。
#:
#: ⚠️ **必须随这个数一起转述的限定**（`D-029`）：标定它的样本（茅台 2023 九个科目）
#: 差额**全部精确为 0**，所以那份证据只证明「阈值不必为了容纳系统性偏移而放宽」，
#: **不证明 `0.01` 在别的公司 / 别的科目上不会误报**。
#: 自我纠错机制是下面那个比例，不是「觉得不对就改」。
DISAGREEMENT_TOLERANCE = Decimal("0.01")

#: `D-029` 的反转触发条件：同一批次里触发占比 **超过** 1/3 ⇒ 按「档位选错」处置。
#:
#: 用 `Fraction` 不用 `0.3333`：这个阈值要参与一次相等边界的比较，
#: 而 1/3 在二进制浮点里不可精确表示 —— 用浮点写，「恰好 1/3」这条边界
#: 会变成一次靠舍入决定的判断。`Fraction(1, 3)` 让它是准确的。
MISCALIBRATION_THRESHOLD = Fraction(1, 3)

DEFAULT_AKSHARE_MAPPING_DIR = Path("data") / "mappings" / "akshare"

#: 三张表的键。**穷举，不做发现式扫目录** —— 多一份文件应当是加载失败，
#: 不是静默多出一个谁也没审过的对照源。
AKSHARE_STATEMENTS = ("balance_sheet", "income_statement", "cash_flow")

#: 每条映射条目的必需键。缺一即拒绝加载（`D-016`）。
REQUIRED_ENTRY_KEYS = ("field_id", "column_name", "statement")

_FLAGS_PATH = Path("metrics") / "_flags.yaml"
_FLAG_NAME = "source_disagreement"


def source_disagreement_flag(flags_path: Path | str = _FLAGS_PATH) -> str:
    """从 `metrics/_flags.yaml` 里**逐字**取出 flag 名。

    为什么不写成一个字符串常量：写死一个拼写，改了 YAML 而代码没改时，
    代码会继续置一个**词表里已经不存在的 flag**，而没有任何东西会报错 ——
    `AC-04` 的「不得自造 flag」就从一条硬规则退化成一句注释。

    顺带校验 `scope` 仍是 `system`：一旦有人把它改成 `definition`，
    `active_flags()` 会开始遍历它，而本模块也在置它 —— 同一个标记被两条路径置位，
    且两条路径的判据不同。那时应当加载期报错，不是运行期出现两个来源的同名 flag。
    """
    raw = yaml.safe_load(Path(flags_path).read_text(encoding="utf-8"))
    for entry in raw.get("flags", []):
        if entry.get("name") == _FLAG_NAME:
            if entry.get("scope") != "system":
                raise ValueError(
                    f"{flags_path}：{_FLAG_NAME} 的 scope 是 {entry.get('scope')!r}，"
                    "不是 system。本模块与 resolve.active_flags() 会同时置它，"
                    "而两条路径的判据不同（R4）。"
                )
            return entry["name"]
    raise ValueError(
        f"{flags_path} 里没有 {_FLAG_NAME}。指标定义只能引用受控词表，不得自造 flag。"
    )


# --------------------------------------------------------------------------
# 映射表：AKShare 列名 → field_id
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class AkshareEntry:
    """一个字段在 AKShare 某张表上的列名。

    没有 `kind`、没有 `label_variants`：AKShare 返回的是一行扁平的列，
    没有版面、没有折行、没有列头选择。**结构比 PDF 侧简单，所以字段更少** ——
    照抄 PDF 侧的形状会引入一堆永远取不到值的键（`F-2`）。
    """

    field_id: str
    column_name: str
    statement: str


@dataclass(frozen=True)
class AkshareMappingTable:
    """一张表的全部条目，连同版本号与这个源的词汇表。

    `mapping_version` 随对照结论一起留证（`L-38` / `L-40`）：
    复核时按当时的版本求值，不按现在的配置。
    """

    statement: str
    mapping_version: int
    currency_reported: str
    currency_canonical: str
    scope_required: str
    entries: tuple[AkshareEntry, ...]

    def column_for_field(self, field_id: str) -> str | None:
        for entry in self.entries:
            if entry.field_id == field_id:
                return entry.column_name
        return None

    def field_for_column(self, column_name: str) -> str | None:
        """**逐字相等**，不是子串包含。

        松成子串包含就会重现 cninfo 的三处静默错误映射
        （`references/cninfo.md:204-213`）：「流动负债合计」含「负债合计」。
        """
        for entry in self.entries:
            if entry.column_name == column_name:
                return entry.field_id
        return None


def load_akshare_mapping(
    statement: str, mapping_dir: Path | str = DEFAULT_AKSHARE_MAPPING_DIR
) -> AkshareMappingTable:
    """读 `data/mappings/akshare/{statement}.yaml`。**任何形状问题一律抛异常。**

    这些都是「我们写错了」，写不进用户文档，故按 `D-022` 决策二走异常而不是 `Refusal`。
    YAML 一律 `safe_load`（`L-33`）。
    """
    path = Path(mapping_dir) / f"{statement}.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path}：映射表顶层必须是映射")

    version = raw.get("mapping_version")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise ValueError(
            f"{path}：mapping_version 必须是 ≥ 1 的整数，实际是 {version!r}。"
            "未声明口径版本的数据源条目一律拒绝（L-40）。"
        )
    declared = raw.get("statement")
    if declared != statement:
        raise ValueError(
            f"{path}：文件里声明的 statement 是 {declared!r}，"
            f"与文件名给出的 {statement!r} 不一致"
        )

    currency = raw.get("currency")
    if not isinstance(currency, dict) or not currency.get("reported") or not currency.get("canonical"):
        raise ValueError(
            f"{path}：currency 必须同时给出 reported 与 canonical。"
            "币种别名是这个数据源的词汇表，必须写在映射文件里随版本冻结，"
            "不许在代码里内置一张不被任何东西校验的换算表。"
        )
    scope_required = raw.get("scope_required")
    if not isinstance(scope_required, str) or not scope_required.strip():
        raise ValueError(
            f"{path}：scope_required 必须给出（如 `合并期末`）。"
            "不声明合并口径就等于默认接受母公司数据参与对照。"
        )

    raw_entries = raw.get("entries")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise ValueError(f"{path}：entries 必须是非空列表")

    entries: list[AkshareEntry] = []
    seen_fields: set[str] = set()
    seen_columns: set[str] = set()
    for index, entry in enumerate(raw_entries):
        where = f"{path}：第 {index + 1} 条"
        if not isinstance(entry, dict):
            raise ValueError(f"{where} 必须是映射")
        missing = [k for k in REQUIRED_ENTRY_KEYS if not entry.get(k)]
        if missing:
            raise ValueError(f"{where} 缺必需键：{missing}")
        if entry["statement"] != statement:
            raise ValueError(
                f"{where} 的 statement 是 {entry['statement']!r}，与文件的 {statement!r} 不一致"
            )
        if entry["field_id"] in seen_fields:
            raise ValueError(f"{where}：field_id {entry['field_id']!r} 重复")
        if entry["column_name"] in seen_columns:
            raise ValueError(
                f"{where}：column_name {entry['column_name']!r} 重复。"
                "一列映射到两个字段，取哪个由 dict 插入顺序决定，那不是任何人的决定。"
            )
        seen_fields.add(entry["field_id"])
        seen_columns.add(entry["column_name"])
        entries.append(
            AkshareEntry(
                field_id=entry["field_id"],
                column_name=entry["column_name"],
                statement=statement,
            )
        )

    return AkshareMappingTable(
        statement=statement,
        mapping_version=version,
        currency_reported=currency["reported"],
        currency_canonical=currency["canonical"],
        scope_required=scope_required,
        entries=tuple(entries),
    )


def load_all_akshare_mappings(
    mapping_dir: Path | str = DEFAULT_AKSHARE_MAPPING_DIR,
) -> dict[str, AkshareMappingTable]:
    return {s: load_akshare_mapping(s, mapping_dir) for s in AKSHARE_STATEMENTS}


def assert_akshare_mapping_within_definitions(
    mapping_dir: Path | str = DEFAULT_AKSHARE_MAPPING_DIR,
    metrics_dir: Path | str = "metrics",
) -> None:
    """对照映射的 `field_id` 必须是 `source_fields[].id` 的**子集**。

    ⚠️ **方向与 PDF 侧不同，这一句必须留着**，否则下一个人会照抄
    `mapping.assert_mapping_covers_definitions()` 的相等断言。

    - PDF 侧是**相等**：它是权威源，少一条就有字段没有任何抽取规则。
    - AKShare 侧只能是**子集**：`notes.*` 的复选框、`kpi.*` 的披露值、
      `is.operating_revenue_prior_as_presented` 这个「本期报表上印的上期数」
      在三张报表里**结构上就不存在**。要求相等等于逼着编三条永远取不到的规则，
      而 `F-2` 记的正是这件事：编出来的规则不会正确触发，只会让每批都失败。

    **但「多一条」在两侧同样是缺陷**：一条没有任何定义引用的对照规则
    不被任何东西校验，会一直活着直到有人当它是对的。所以这个方向照样报。
    """
    from .mapping import declared_field_ids

    tables = load_all_akshare_mappings(mapping_dir)
    mapped = {e.field_id for t in tables.values() for e in t.entries}
    declared = declared_field_ids(metrics_dir)
    extra = sorted(mapped - declared)
    if extra:
        raise AssertionError(
            "AKShare 对照映射里有、定义里没有：" + str(extra) + "。"
            "没有任何定义引用的对照规则不被任何东西校验。"
        )


# --------------------------------------------------------------------------
# 参照值
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ReferenceValue:
    """AKShare 侧的一个取值，连同判定可比性所需的全部前置事实。

    `present` 与 `raw is None` 是**两件事**：
    `present=False` 表示这一列在返回里根本不存在；
    `present=True, raw=None` 表示列在、值是 `NaN`。
    合并它们，`REFERENCE_COLUMN_ABSENT` 与 `REFERENCE_NAN` 就分不开了，
    而前者是「我们的映射可能写错了」，后者是「这个源这一期没这个数」——
    归因完全不同。
    """

    field_id: str
    column_name: str
    raw: float | int | None
    present: bool
    statement: str
    source: str
    mapping_version: int
    unit: str
    currency: str
    period: str
    scope: str
    #: 这张表要求的合并口径，**从映射文件的 `scope_required` 带出来**。
    #:
    #: 🔴 为什么它是一个字段而不是一个字面量（`RV-2`，独立复核 2026-08-28 查出）：
    #: 原实现把 `"合并期末"` 硬编码在 `cross_validate` 里，于是 `scope_required`
    #: 是一个**被加载、被校验、但从不被消费**的配置键 ——
    #: 三份 YAML 里把它改成任何别的值都零效果，而
    #: `test_映射表不声明合并口径即拒绝加载` 让它看起来是被锁住的。
    #: 那条测试锁的是「这个键必须存在」，不是「这个键起作用」。
    scope_required: str

    def as_decimal(self) -> Decimal | None:
        return _reference_decimal(self.raw)

    def to_dict(self) -> dict:
        value = self.as_decimal()
        return {
            "field_id": self.field_id,
            "column_name": self.column_name,
            "value": None if value is None else str(value),
            "present": self.present,
            "statement": self.statement,
            "source": self.source,
            "mapping_version": self.mapping_version,
            "unit": self.unit,
            "currency": self.currency,
            "period": self.period,
            "scope": self.scope,
        }


def _reference_decimal(raw: Any) -> Decimal | None:
    """**全仓唯一的 AKShare 数值转换点**（`C-6` / `D-029` 判据 3）。

    走 `Decimal(repr(v))`，不走 `Decimal(v)`：后者把二进制浮点的全部尾巴带进来，
    `Decimal(48697611501.2)` 得到 `48697611501.2000007629...`，
    **凭空造出一个不存在的差额**，而那个差额会正好超过一分钱的容差。

    固件里有一条肉眼可见的实例：现金流量表的 `期初现金及现金等价物余额`
    存的是 `152378738982.83002` —— 尾部的 `02` 就是这条尾巴。

    这里只有一个转换点这件事由 `tests/test_crosscheck.py` 的 AST 级检查锁住，
    不是靠人记得。
    """
    if raw is None:
        return None
    return Decimal(repr(raw))


def load_reference_payload(path: Path | str) -> dict:
    """读一份录制好的响应。**离线**，不 import akshare。"""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def references_from_payload(
    payload: Mapping[str, Any],
    tables: Mapping[str, AkshareMappingTable],
) -> dict[str, ReferenceValue]:
    """把录制的响应按映射表摊成 `field_id -> ReferenceValue`。

    **映射表里的每一条都会产出一个 `ReferenceValue`**，哪怕那一列不在返回里。
    不产出的话，「这一列缺了」会退化成「这个字段没做对照」——
    而后者在证据链里看不出区别，`F-1` 那类误判就是这么来的。
    """
    references: dict[str, ReferenceValue] = {}
    for statement, table in tables.items():
        block = payload.get(statement) or {}
        row = block.get("row") or {}
        source = block.get("api")
        source = f"akshare:{source}" if source else SOURCE_AKSHARE
        for entry in table.entries:
            present = entry.column_name in row
            references[entry.field_id] = ReferenceValue(
                field_id=entry.field_id,
                column_name=entry.column_name if present else "",
                raw=row.get(entry.column_name) if present else None,
                present=present,
                statement=statement,
                source=source,
                mapping_version=table.mapping_version,
                # AKShare 的单位由 `AKSHARE-A2.md` 实测定死为「元」，
                # 但**仍然走归一化那一步**：它防的是换一个源 / 换一家公司就不一样了。
                unit="元",
                currency=table.currency_canonical
                if str(row.get("币种", "")) == table.currency_reported
                else str(row.get("币种", "")),
                period=str(row.get("报告日", "")),
                scope=str(row.get("类型", "")),
                scope_required=table.scope_required,
            )
    return references


def fetch_reference(
    stock: str,
    year: int,
    fetcher: Callable[..., Any] | None = None,
) -> dict | Refusal:
    """取一份真实响应。**唯一会联网的入口。**

    取不到时返回 `Refusal(UNAVAILABLE, source="akshare:...")`，**不抛异常**，
    且不碰任何已经算出来的数值 —— 对照缺失不是计算失败（`D-013` / `D-022` 决策一）。

    两条降级路径都走这里：
    - akshare **没装**（它在 `crosscheck` extra 里，不是主依赖）⇒ `ImportError`
    - 装了但**调不通**（网络、接口改版、该期无数据）⇒ 其它异常

    两者都拒答，但 `detail` 不同 —— 复核者据此知道该去装包还是去查网络（`L-9`）。
    """
    if fetcher is None:
        fetcher = _live_fetcher
    try:
        return fetcher(stock, year)
    except ImportError as exc:
        return Refusal(
            RefusalCode.UNAVAILABLE,
            f"akshare 未安装（它在可选 extra `crosscheck` 里，不是主依赖）：{exc}。"
            "对照源缺失不影响 PDF 侧已经算出的数值。",
            source=SOURCE_AKSHARE,
        )
    except Exception as exc:  # noqa: BLE001 - 第三方库的异常类型不在我们的控制范围内
        return Refusal(
            RefusalCode.UNAVAILABLE,
            f"AKShare 调用失败：{type(exc).__name__}: {exc}。"
            "对照源缺失不影响 PDF 侧已经算出的数值。",
            source=SOURCE_AKSHARE,
        )


#: 报告级元数据列。判定要用（`报告日` / `币种` / `类型`），其余三列是留证。
METADATA_COLUMNS = frozenset(
    {"报告日", "币种", "类型", "数据源", "是否审计", "公告日期", "更新日期"}
)

#: 🔴 **不参与任何映射、但必须留在固件里的列**（`RV-6`，独立复核 2026-08-28 查出）。
#:
#: 它们是**负控制的证据本身**。`--record` 原先只保留「已映射的列 + 元数据列」，
#: 于是这四列全被裁掉，而：
#:
#: - `应付票据及应付账款` —— `test_应付票据及应付账款不匹配应付账款` 直接从固件读它，
#:   裁掉之后那条测试不是变红，是 **`KeyError` 直接 ERROR**。
#:   而它是本模块**唯一**咬得住「逐字相等 → 子串包含」这个变异的用例（见 `RV-4`）。
#: - `应收票据及应收账款` —— `balance_sheet.yaml` 注释拿它当「这一处子串匹配会被
#:   数值发现」的反例，与应付侧那处「不会被发现」正好成对。
#: - `营业总收入` —— `income_statement.yaml` 注释拿它当近义列陷阱的实例。
#: - `期初现金及现金等价物余额` —— `cash_flow.yaml` 头部拿它当**浮点尾巴肉眼可见**
#:   的实证（`152378738982.83002`），是 `C-6` 不是理论风险的唯一现场证据。
#:
#: ⇒ **一次「正规路径」的重录会静默删掉本模块四条论据里的四条。**
#: 这是「留证在接线时被丢掉」（`ARCHITECTURE §8.5`）的又一个形状，
#: 只不过丢它的是我们自己写的重录工具。
EVIDENCE_COLUMNS = frozenset(
    {
        "应付票据及应付账款",
        "应收票据及应收账款",
        "营业总收入",
        "期初现金及现金等价物余额",
    }
)


def keep_columns(table: AkshareMappingTable) -> set[str]:
    """`--record` 重录时保留哪些列。

    **不是「已映射的列」**：还要加上元数据列与 `EVIDENCE_COLUMNS`。
    裁剪本身是 `T-01.5-20` 要求的（原始三张表 103×147 / 103×83 / 99×71，
    整个 dump 进仓库既没必要也会让固件失去可读性），但裁剪的边界
    **不能只按「我们用得上的」画** —— 负控制用的正是我们**用不上**的那些列。
    """
    return {e.column_name for e in table.entries} | METADATA_COLUMNS | set(EVIDENCE_COLUMNS)


def _live_fetcher(stock: str, year: int) -> dict:
    """真正联网的那一段。**只在 `--record` 时被调用。**

    只取目标年度那一期与已映射的列 —— 三张表原始形状是
    `103×147` / `103×83` / `99×71`，整个 dump 进仓库既没必要也会让固件失去可读性
    （`T-01.5-20`）。
    """
    import akshare  # noqa: PLC0415 - 可选依赖，只在这一处 import

    prefix = "sh" if stock.startswith(("6", "9")) else "sz"
    symbols = {
        "balance_sheet": "资产负债表",
        "income_statement": "利润表",
        "cash_flow": "现金流量表",
    }
    tables = load_all_akshare_mappings()
    report_date = f"{year}1231"
    payload: dict[str, Any] = {}
    for key, symbol in symbols.items():
        frame = akshare.stock_financial_report_sina(stock=f"{prefix}{stock}", symbol=symbol)
        matched = frame[frame["报告日"].astype(str) == report_date]
        if matched.empty:
            raise LookupError(f"{symbol} 里没有报告日 {report_date} 的行")
        row = matched.iloc[0]
        keep = keep_columns(tables[key])
        payload[key] = {
            "api": "stock_financial_report_sina",
            "stock": f"{prefix}{stock}",
            "symbol": symbol,
            "report_date": report_date,
            "shape": list(frame.shape),
            "row": {
                k: (None if _is_nan(v) else v)
                for k, v in row.items()
                if k in keep
            },
        }
    return payload


def _is_nan(value: Any) -> bool:
    return isinstance(value, float) and value != value


# --------------------------------------------------------------------------
# 判定
# --------------------------------------------------------------------------


class CrossCheckVerdict(Enum):
    """三个取值。`INCOMPARABLE` 不是「另一种不一致」，见模块 docstring。"""

    AGREES = "两源在容差内给出同一个数"
    DISAGREES = "两源差额超出容差，该不一致本身作为证据记录"
    INCOMPARABLE = "这一次没有可比的对照结论"


class IncomparableReason(Enum):
    """判不了的原因。**穷举，没有 `OTHER`** ——

    一个兜底成员等于允许把任何判不了都塞进去，那时「不可比」这个取值
    就不再携带任何可归因的信息，而它存在的全部理由就是可归因。
    """

    UNIT_UNDETERMINED = "两侧至少有一侧的计量单位读不出来（D-029 决策 2）"
    CURRENCY_MISMATCH = "两侧币种不同，且不在映射文件声明的别名范围内"
    SCOPE_NOT_CONSOLIDATED = "参照行不是合并口径"
    PERIOD_MISMATCH = "参照行的报告期与本批次不是同一期"
    REFERENCE_COLUMN_ABSENT = "参照源返回里没有这一列"
    REFERENCE_NAN = "参照源这一格是 NaN —— 它不是零，也不等于缺失"
    PDF_VALUE_UNREADABLE = "PDF 侧这一格没有可参与比较的数值"


@dataclass(frozen=True)
class CrossCheckResult:
    """一个字段的一次对照的完整留证。

    `pdf_value` 与 `reference_value` **都在**，且 `pdf_value` 永远是 PDF 侧的那个数 ——
    `D-013` 的「不静默取其一」在数据结构上的形态：这里没有一个叫 `value` 的字段
    可以让下游分不清它是谁给的。
    """

    field_id: str
    verdict: CrossCheckVerdict
    pdf_value: Decimal | None
    reference_value: Decimal | None
    difference: Decimal | None
    tolerance_used: Decimal
    flags: tuple[str, ...]
    incomparable_reason: IncomparableReason | None
    reference_source: str
    reference_column: str
    mapping_version: int
    pdf_unit: str
    reference_unit: str

    def to_dict(self) -> dict:
        return {
            "field_id": self.field_id,
            "verdict": self.verdict.name,
            "verdict_meaning": self.verdict.value,
            "pdf_value": None if self.pdf_value is None else str(self.pdf_value),
            "reference_value": None
            if self.reference_value is None
            else str(self.reference_value),
            "difference": None if self.difference is None else str(self.difference),
            "tolerance_used": str(self.tolerance_used),
            "flags": list(self.flags),
            "incomparable_reason": None
            if self.incomparable_reason is None
            else self.incomparable_reason.name,
            "incomparable_meaning": None
            if self.incomparable_reason is None
            else self.incomparable_reason.value,
            "reference_source": self.reference_source,
            "reference_column": self.reference_column,
            "mapping_version": self.mapping_version,
            "pdf_unit": self.pdf_unit,
            "reference_unit": self.reference_unit,
        }


def _pdf_amount(record: ExtractionRecord) -> Decimal | None:
    """能参与对照的 PDF 侧数值；取不到即 None。

    与 `reconcile._readable_amount` 同一套三态语义（SC-3 / A-2）：
    `EMPTY_CELL`（行在、格子空）按 0 参与，`ROW_ABSENT` 与 `ATTEMPTED_UNKNOWN` 取不到。
    """
    if record.retrieval is RetrievalOutcome.ATTEMPTED_UNKNOWN:
        return None
    if record.cell_state is CellState.ROW_ABSENT:
        return None
    if record.cell_state is CellState.EMPTY_CELL:
        return Decimal(0)
    if not isinstance(record.value, Decimal):
        return None
    return record.value


def _incomparable(
    record: ExtractionRecord,
    reference: ReferenceValue,
    reason: IncomparableReason,
    pdf_value: Decimal | None = None,
    reference_value: Decimal | None = None,
) -> CrossCheckResult:
    return CrossCheckResult(
        field_id=record.field_id,
        verdict=CrossCheckVerdict.INCOMPARABLE,
        pdf_value=pdf_value,
        reference_value=reference_value,
        difference=None,
        tolerance_used=DISAGREEMENT_TOLERANCE,
        flags=(),
        incomparable_reason=reason,
        reference_source=reference.source,
        reference_column=reference.column_name,
        mapping_version=reference.mapping_version,
        pdf_unit=record.unit,
        reference_unit=reference.unit,
    )


def cross_validate(
    record: ExtractionRecord,
    reference: ReferenceValue,
    tolerance: Decimal = DISAGREEMENT_TOLERANCE,
    period: str | None = None,
) -> CrossCheckResult:
    """一条记录与一个参照值的对照。**与 `resolve.check_comparable()` 平行的独立函数。**

    顺序是硬的（`units` 模块 docstring）：先把可比性判掉、再归一化、最后才比数值。
    颠倒过来，单位错配会被报成「不一致」，而那是查错方向。

    **本函数不改写 `record`**，`record.value` 出去时是什么进来还是什么。
    """
    if not reference.present:
        return _incomparable(record, reference, IncomparableReason.REFERENCE_COLUMN_ABSENT)
    # **fail-closed**：`scope` 为空串（`类型` 列缺失或为空）时照样判不可比。
    # 原实现是 `if reference.scope and ...`，前半个 `and` 让空 scope 直接跳过整条判定，
    # 字段被当作合并口径参与对照 —— 而币种与报告期两条同类闸门在同样输入下都是
    # fail-closed。三条同类判定里两条一个行为、一条另一个行为，
    # 且恰好是加载器报错文案写着「不声明合并口径就等于默认接受母公司数据」的那一条。
    if reference.scope != reference.scope_required:
        return _incomparable(record, reference, IncomparableReason.SCOPE_NOT_CONSOLIDATED)
    if period is not None and reference.period != period:
        return _incomparable(record, reference, IncomparableReason.PERIOD_MISMATCH)
    if record.currency != reference.currency:
        return _incomparable(record, reference, IncomparableReason.CURRENCY_MISMATCH)

    try:
        pdf_scale = scale_of(record.unit)
        reference_scale = scale_of(reference.unit)
    except UnitMismatchError:
        # D-029 决策 2：单位读不出来判「不可比」，**不判「不一致」**，
        # 且 source_disagreement 不置位。
        return _incomparable(record, reference, IncomparableReason.UNIT_UNDETERMINED)

    raw_pdf = _pdf_amount(record)
    if raw_pdf is None:
        return _incomparable(record, reference, IncomparableReason.PDF_VALUE_UNREADABLE)

    raw_reference = reference.as_decimal()
    if raw_reference is None:
        # C-7：NaN 不是 0。当 0 会与 PDF 侧的「格子空 = 0」比出一个
        # 从未被建立过的一致 —— 那比判不了更糟，因为它看起来像证据。
        return _incomparable(
            record, reference, IncomparableReason.REFERENCE_NAN, pdf_value=raw_pdf
        )

    pdf_value = to_yuan(raw_pdf, pdf_scale)
    reference_value = to_yuan(raw_reference, reference_scale)
    difference = abs(pdf_value - reference_value).quantize(DISAGREEMENT_TOLERANCE)
    agrees = difference <= tolerance
    return CrossCheckResult(
        field_id=record.field_id,
        verdict=CrossCheckVerdict.AGREES if agrees else CrossCheckVerdict.DISAGREES,
        pdf_value=pdf_value,
        reference_value=reference_value,
        difference=difference,
        tolerance_used=tolerance,
        flags=() if agrees else (source_disagreement_flag(),),
        incomparable_reason=None,
        reference_source=reference.source,
        reference_column=reference.column_name,
        mapping_version=reference.mapping_version,
        pdf_unit=record.unit,
        reference_unit=reference.unit,
    )


@dataclass(frozen=True)
class BatchCrossCheck:
    """一批对照的汇总，**含 `D-029` 的反转条件所需的那个比例**。

    分子分母都留证，不只留一个比值：`1/3` 与 `100/300` 在证据上不是同一件事，
    而只有比值时复核者无从知道自己在看哪一种。
    """

    results: tuple[CrossCheckResult, ...]
    comparable: int
    incomparable: int
    disagreements: int
    disagreement_ratio: Fraction
    miscalibration_suspected: bool
    note: str

    def to_dict(self) -> dict:
        return {
            "results": [r.to_dict() for r in self.results],
            "comparable": self.comparable,
            "incomparable": self.incomparable,
            "disagreements": self.disagreements,
            "disagreement_ratio": str(self.disagreement_ratio),
            "miscalibration_threshold": str(MISCALIBRATION_THRESHOLD),
            "miscalibration_suspected": self.miscalibration_suspected,
            "tolerance_used": str(DISAGREEMENT_TOLERANCE),
            "note": self.note,
            "source": SOURCE_AKSHARE,
        }


def cross_validate_batch(
    batch: ExtractionBatch,
    references: Mapping[str, ReferenceValue],
    tolerance: Decimal = DISAGREEMENT_TOLERANCE,
    period: str | None = None,
) -> BatchCrossCheck:
    """整批对照，并算出 `D-029` 的反转条件所需的触发占比。

    **分母是「可比的」那些，不是全部。** 把不可比也算进分母，
    比例会被一堆判不了的字段稀释到永远触发不了 —— 那样这条反转条件就等于不存在。
    分子分母都写进证据链，复核者自己能看出分母有多小。

    ⚠️ **这里刻意不设最小分母门槛。** 分母为 1 时比例是 0 或 1，噪音很大 ——
    但补一个「至少 N 个字段才判」的门槛，就是又凭空定一个没有证据支撑的数，
    正是 `01.5-RESEARCH` 的 `A3` 警告的那件事。宁可把分母摆出来让人看见。
    """
    results: list[CrossCheckResult] = []
    for record in batch.records:
        reference = references.get(record.field_id)
        if reference is None:
            continue
        results.append(cross_validate(record, reference, tolerance, period))

    comparable = sum(1 for r in results if r.verdict is not CrossCheckVerdict.INCOMPARABLE)
    incomparable = len(results) - comparable
    disagreements = sum(1 for r in results if r.verdict is CrossCheckVerdict.DISAGREES)
    ratio = Fraction(disagreements, comparable) if comparable else Fraction(0)
    suspected = comparable > 0 and ratio > MISCALIBRATION_THRESHOLD

    if comparable == 0:
        note = (
            f"本批没有任何可比字段（{incomparable} 个判不了）。"
            "触发占比记 0 —— 它表示「没有对照结论」，不表示「两源一致」。"
        )
    elif suspected:
        note = (
            f"疑为档位选错：{disagreements}/{comparable} 超过 {MISCALIBRATION_THRESHOLD}。"
            "按 D-029 反转条件，这更像容差档位不对，不像数据真的不一致。"
            "处置是改用 tiered 并用本批数据标定金额门槛，不是逐条去查数据。"
        )
    else:
        note = (
            f"触发占比 {ratio}（{disagreements}/{comparable}），"
            f"未超过 D-029 的反转阈值 {MISCALIBRATION_THRESHOLD}。"
        )

    return BatchCrossCheck(
        results=tuple(results),
        comparable=comparable,
        incomparable=incomparable,
        disagreements=disagreements,
        disagreement_ratio=ratio,
        miscalibration_suspected=suspected,
        note=note,
    )


# --------------------------------------------------------------------------
# L-12 —— **本模块刻意不实现它**（`RV-5`，2026-08-28 操作者裁决删除）
# --------------------------------------------------------------------------
#
# 这里原本有一个 `align_references()`：给定上一次与本次的参照集，判断旧值能不能复用，
# 对不齐就整体用新的。它有四条测试、看起来是 `L-12` 的落地。
#
# 🔴 **独立复核实测它的语义是错的**：判据只看**字段集 / 列名 / `mapping_version`**
# 三样。于是字段集、列名、版本号全没变而 `period` 与 `raw` 变了的时候，
# 它返回 `aligned is previous`、`reason` 为空串 ——
# **换一期报告去对照，它会说「对齐了」并把上一期的数字交给调用方。**
# 那正是 `L-12` 原话「看起来有证据、实际指错地方」它自己要防的东西。
#
# **为什么处置是删掉而不是修**：它当时没有任何非测试调用点。
# 一个没人调用、语义又不对、却带着四条绿测试的函数，比没有它更危险 ——
# 那四条绿测试会让下一个接线的人以为对齐这件事已经解决了。
# **删掉之后 `L-12` 回到「未落地」这个如实状态**，与
# `CONTEXT §8` 末表原本就写的「`L-12` 被 `U-01` 正当挡着，Phase 2」重新一致。
# （这条不一致是本轮才暴露的：`01.5-04-PLAN` 的 Task 3 要求实现它，
#  而 `CONTEXT §8` 说它被挡着 —— 两份文档打架，我当时选了照 PLAN 做。）
#
# ⇒ 真要做时，判据必须先回答「证据链的字段集是什么」，而那是 `U-01`，Phase 2 的事。
