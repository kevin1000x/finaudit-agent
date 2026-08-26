"""PDF 映射表的加载与匹配 —— **逐字整行相等，不是子串包含**（D-016 / SC-2）。

## 加载器的形状照抄 `semantic_layer.vocabulary`

必需键缺一即 `ValueError` 拒绝加载，**绝不补默认值**。
`vocabulary.py` 里那条注释写清了理由：`affects_comparability` 曾经
`entry.get(..., False)` 静默补默认，于是漏写该键的 flag 被当成「不影响可比性」——
一个本该阻断跨期比较的标记**悄悄不阻断，且不报错**。映射表同型：
漏写 `column_header` 若补个默认，取到的会是**另一列的数**，而没有任何东西会报错。

## 为什么是「逐字整行相等」而不是「包含」

这四个字同时解掉两个**真实**错误：

1. 台账 A-4：`bs.total_equity` 匹配到章节小标题「所有者权益（或股东权益）：」，
   而那一行**没有数值**。它与「所有者权益（或股东权益）合计」不相等，
   整行相等不会中招，子串包含会。
2. 「归属于母公司所有者权益（或股东权益）合计」与「所有者权益（或股东权益）合计」
   这对极易混淆的行：前者的第一个片段是「归属于母公司所有者权益」，
   与后者的第一个片段不相等，故不会互相冒名。

SC-2 明令「不允许模糊匹配」，这就是它的机械形态。

## 折行的表达：`label_fragments` 是一等构造（D-016 2026-08-21 补充节）

一条 `label_variants` 元素是 `{label_fragments: [...]}`，片段列表**按顺序、逐字整行相等**。
匹配对象是 `locate.ReconstructedRow.label_lines` —— 那是缝合器保留下来的原始片段，
**没有被拼接过**。拼接会把「折行处该不该补字」这个判断偷偷塞进 `locate`，
而那本来是映射表要显式写清的事。

**片段字面量取自真实版面，不取「读起来应该是这样」的形态。**
茅台 2023 p61 上「所有者权益（或股东权益）合计」的实际折行处在「权益」两字之间：

    所有者权益（或股东权
    223,656,469,294.82   204,938,081,263.86
    益）合计

映射表里写的就是 `["所有者权益（或股东权", "益）合计"]`。写一个更「整齐」的
折法（例如 `["所有者权益", "（或股东权益）合计"]`）会得到一条**永远匹配不上**的规则
—— 那正是 F-2「拿手边能求值的东西凑一个 trigger」的形状。

## `column_header` 是**口径名**，不是版面上的那串字

条目里写「期末余额」，而茅台 2023 的资产负债表表头印的是「2023年12月31日」。
两者的对应由 `locate.bind_columns` 的 `role` 显式判定并留证（`resolution` 字段），
不由本模块猜。把日期写进映射表会让映射表变成逐年一份，那才是真的错。

## 零命中（L-36）

一条在**整份 PDF** 上一次都没匹配上的规则只可能是写错了，判为失败。
判定在 `pipeline` 里做（那里才看得到整份 PDF），本模块只提供 `match_row`。
注意范围：**整份 PDF 零命中 ⇒ 规则写错了（抛异常）**；
在目标报表区间内没匹配上、但在别处匹配得上 ⇒ 这张表确实没有这一行（`ROW_ABSENT`）。
两者混为一谈会把 SC-3 要区分的「整行不存在」变成一次崩溃。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .record import RecordKind

__all__ = [
    "DEFAULT_MAPPING_DIR",
    "REQUIRED_ENTRY_KEYS",
    "FieldMapping",
    "PdfMappingTable",
    "load_pdf_mapping",
    "match_row",
]

DEFAULT_MAPPING_DIR = Path("data") / "mappings" / "pdf"

#: 五个键都是必需的（D-016）。缺一即拒绝加载。
REQUIRED_ENTRY_KEYS = ("field_id", "statement", "column_header", "label_variants", "kind")


@dataclass(frozen=True)
class FieldMapping:
    """一个字段在 PDF 上的取数口径。

    `kind` 是**显式**的类别（L-35）：本模块不提供任何由标签文本或数值形状
    反推类别的入口，「看起来像三大表某一行」这类启发式在这里无处落脚。
    """

    field_id: str
    statement: str
    column_header: str
    label_variants: tuple[tuple[str, ...], ...]
    kind: RecordKind

    def matches(self, label_lines: tuple[str, ...]) -> bool:
        return any(variant == tuple(label_lines) for variant in self.label_variants)


@dataclass(frozen=True)
class PdfMappingTable:
    """一个命名空间的全部条目，连同它的版本号。

    `mapping_version` 随抽取记录一起冻结（L-38）：复核时按记录里的版本求值，
    不按当时的配置。否则同一条证据在两个时间点复核会得到不同结果，
    D-012 的冻结就没有意义了。
    """

    namespace: str
    mapping_version: int
    entries: tuple[FieldMapping, ...]

    def by_field(self, field_id: str) -> FieldMapping | None:
        for entry in self.entries:
            if entry.field_id == field_id:
                return entry
        return None

    def for_statement(self, statement: str) -> tuple[FieldMapping, ...]:
        return tuple(e for e in self.entries if e.statement == statement)


def load_pdf_mapping(
    namespace: str, mapping_dir: Path | str = DEFAULT_MAPPING_DIR
) -> PdfMappingTable:
    """读 `data/mappings/pdf/{namespace}.yaml`。**任何形状问题一律抛异常。**

    这些都是「我们写错了」，写不进用户文档，故按 D-022 决策二走异常而不是 `Refusal`。
    YAML 一律 `safe_load`：`!!python/object` 这类方言是一条通往任意求值的入口，
    L-33 要求的是**不留任何能到达求值的入口**，不只是「不调用 eval」。
    """
    path = Path(mapping_dir) / f"{namespace}.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path}：映射表顶层必须是映射")

    version = raw.get("mapping_version")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise ValueError(
            f"{path}：mapping_version 必须是 ≥ 1 的整数，实际是 {version!r}。"
            "未声明口径版本的数据源条目一律拒绝（L-40）。"
        )
    declared_namespace = raw.get("namespace")
    if declared_namespace != namespace:
        raise ValueError(
            f"{path}：文件里声明的 namespace 是 {declared_namespace!r}，"
            f"与文件名给出的 {namespace!r} 不一致"
        )

    raw_entries = raw.get("entries")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise ValueError(f"{path}：entries 必须是非空列表")

    entries: list[FieldMapping] = []
    seen: set[str] = set()
    for index, entry in enumerate(raw_entries):
        where = f"{path}：第 {index + 1} 条"
        if not isinstance(entry, dict):
            raise ValueError(f"{where}不是映射：{entry!r}")
        missing = [k for k in REQUIRED_ENTRY_KEYS if k not in entry]
        if missing:
            raise ValueError(
                f"{where}（{entry.get('field_id', '未命名')!r}）缺少必需键 {missing}。"
                "五个键缺一即拒绝加载 —— 补默认值会让漏写变成静默取错列。"
            )

        field_id = entry["field_id"]
        if not isinstance(field_id, str) or not field_id.strip():
            raise ValueError(f"{where}的 field_id 必须是非空字符串")
        if field_id in seen:
            raise ValueError(f"{path}：field_id {field_id!r} 重复")
        seen.add(field_id)
        if not field_id.startswith(f"{namespace}."):
            raise ValueError(
                f"{where}的 field_id {field_id!r} 不以命名空间前缀 {namespace + '.'!r} 开头"
            )

        for key in ("statement", "column_header"):
            if not isinstance(entry[key], str) or not entry[key].strip():
                raise ValueError(f"{where}（{field_id}）的 {key} 必须是非空字符串")

        kind_name = entry["kind"]
        if kind_name not in RecordKind.__members__:
            raise ValueError(
                f"{where}（{field_id}）的 kind {kind_name!r} 不在 "
                f"{sorted(RecordKind.__members__)} 内。类别只能显式声明（L-35）。"
            )

        variants = entry["label_variants"]
        if not isinstance(variants, list) or not variants:
            raise ValueError(f"{where}（{field_id}）的 label_variants 必须是非空列表")
        parsed_variants: list[tuple[str, ...]] = []
        for v_index, variant in enumerate(variants):
            v_where = f"{where}（{field_id}）的第 {v_index + 1} 个 label 变体"
            if not isinstance(variant, dict) or "label_fragments" not in variant:
                raise ValueError(f"{v_where}必须是含 label_fragments 键的映射")
            fragments = variant["label_fragments"]
            if not isinstance(fragments, list) or not fragments:
                raise ValueError(f"{v_where}的 label_fragments 必须是非空列表")
            if not all(isinstance(f, str) and f.strip() for f in fragments):
                raise ValueError(f"{v_where}的 label_fragments 每一项都必须是非空字符串")
            parsed_variants.append(tuple(fragments))
        if len(set(parsed_variants)) != len(parsed_variants):
            raise ValueError(f"{where}（{field_id}）的 label 变体有重复")

        entries.append(
            FieldMapping(
                field_id=field_id,
                statement=entry["statement"],
                column_header=entry["column_header"],
                label_variants=tuple(parsed_variants),
                kind=RecordKind[kind_name],
            )
        )

    return PdfMappingTable(
        namespace=namespace, mapping_version=version, entries=tuple(entries)
    )


def match_row(row, mapping: FieldMapping) -> bool:
    """行的标签片段序列与该条目的某个变体**逐项逐字相等**即命中。

    相等而非包含，序列而非拼接串。两处都不能松：
    松成包含，A-4 的章节小标题会冒名；松成拼接串，
    「折行处该不该补字」这个判断会被偷偷塞进 `locate`。
    """
    return mapping.matches(tuple(row.label_lines))
