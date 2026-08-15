"""把 openspec/specs/semantic-layer/metric-definition/spec.md 的 9 条 Requirement
逐条落成可执行规则。规则码前缀 R1…R9 与红测矩阵一一对应。

设计立场：**只报告，不抛异常**。一份残缺定义要能一次拿到全部 Finding，
而不是在第一个错误处中断——否则「逐条可勾选」就无从谈起。
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path

from . import dsl
from .definition import (
    PERIOD_SEMANTICS,
    PERIOD_TYPES,
    SIGN_CONVENTIONS,
    MetricDefinition,
    load_definition,
)
from .vocabulary import Vocabulary, load_vocabulary

__all__ = ["Finding", "validate_definition", "validate_paths", "RULE_TITLES"]

RULE_TITLES = {
    "R0": "定义文件必须是合法 YAML（加载层，先于 9 条 Requirement）",
    "R1": "口径定义必须声明数据粒度",
    "R2": "口径定义必须声明取数字段的符号约定",
    "R3": "口径定义必须显式声明是否允许分项倒推",
    "R4": "标记必须来自受控词表并具备可求值的触发条件",
    "R5": "准则依据必须带版本且跨版本比较必须被标记",
    "R6": "引用字段必须声明取值域与缺失表示",
    "R7": "未定义条件必须可机械求值且命中时拒答",
    "R8": "常见陷阱必须可执行或显式标注为仅供参考",
    "R9": "口径版本变更后跨版本结论不可比较",
}

_GRAIN_KEYS = ("entity", "period", "period_type")
_MIN_PITFALLS = 3


@dataclass(frozen=True)
class Finding:
    code: str
    where: str
    message: str

    @property
    def rule(self) -> str:
        return self.code.split(".", 1)[0]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["rule"] = self.rule
        d["rule_title"] = RULE_TITLES.get(self.rule, "")
        return d


def _formula_mentions(formula: str | None, field_id: str) -> bool:
    """字段是否参与公式运算。公式里出现即视为参与加减。"""
    return bool(formula) and field_id in formula


def _parse(text: str | None):
    if not isinstance(text, str) or not text.strip():
        return None, "条件为空"
    try:
        return dsl.parse_condition(text), None
    except dsl.DslError as exc:
        return None, str(exc)


def validate_definition(
    defn: MetricDefinition, vocabulary: Vocabulary, *, require_v2: bool = True
) -> list[Finding]:
    findings: list[Finding] = []
    add = findings.append
    where = defn.path.name

    # ---- R0 加载层：文件必须先是合法 YAML --------------------------------
    if defn.parse_error:
        add(
            Finding(
                "R0.YAML_UNPARSEABLE",
                where,
                f"文件不是合法 YAML，9 条 Requirement 无从校验：{defn.parse_error}",
            )
        )
        return findings

    # ---- R1 数据粒度 ----------------------------------------------------
    if not defn.grain:
        add(Finding("R1.MISSING_GRAIN", where, "缺少 grain：公式无法定位到唯一一行数据"))
    else:
        for key in _GRAIN_KEYS:
            if not defn.grain.get(key):
                add(Finding("R1.MISSING_GRAIN", f"{where}:grain", f"grain 缺少 {key}"))
        ptype = defn.grain.get("period_type")
        if ptype is not None and ptype not in PERIOD_TYPES:
            add(
                Finding(
                    "R1.BAD_PERIOD_TYPE",
                    f"{where}:grain.period_type",
                    f"period_type={ptype!r} 不在 {sorted(PERIOD_TYPES)} 内",
                )
            )

    if defn.period_semantics not in PERIOD_SEMANTICS:
        add(
            Finding(
                "R1.BAD_PERIOD_TYPE",
                f"{where}:period_semantics",
                f"period_semantics={defn.period_semantics!r} 不在 {sorted(PERIOD_SEMANTICS)} 内",
            )
        )

    # ---- R2 符号约定 ----------------------------------------------------
    for sf in defn.source_fields:
        if not sf.id:
            continue
        if _formula_mentions(defn.formula, sf.id):
            if not sf.sign_convention:
                add(
                    Finding(
                        "R2.NO_SIGN_CONVENTION",
                        f"{where}:source_fields[{sf.id}]",
                        "参与公式加减但未声明 sign_convention，符号错一次结果方向整体翻转且不触发任何 undefined_condition",
                    )
                )
            elif sf.sign_convention not in SIGN_CONVENTIONS:
                add(
                    Finding(
                        "R2.BAD_SIGN_CONVENTION",
                        f"{where}:source_fields[{sf.id}]",
                        f"sign_convention={sf.sign_convention!r} 不在 {sorted(SIGN_CONVENTIONS)} 内",
                    )
                )

    # ---- R3 倒推策略 ----------------------------------------------------
    if not isinstance(defn.derivation, dict):
        add(
            Finding(
                "R3.DERIVATION_MISSING",
                where,
                "缺少 derivation：是否允许由分项倒推必须显式二选一，不得留空",
            )
        )
    else:
        allow = defn.derivation.get("allow_from_components")
        if not isinstance(allow, bool):
            add(
                Finding(
                    "R3.DERIVATION_NOT_BOOLEAN",
                    f"{where}:derivation",
                    f"allow_from_components={allow!r} 必须是布尔值",
                )
            )
        if not str(defn.derivation.get("note") or "").strip():
            add(Finding("R3.DERIVATION_NOTE_EMPTY", f"{where}:derivation", "note 为空"))

    # ---- R4 标记受控词表 ------------------------------------------------
    if not defn.declares_flags_key:
        add(
            Finding(
                "R4.FLAGS_KEY_MISSING",
                where,
                "缺少 flags 键。「本指标无标记」必须写成 flags: [] 的显式声明，不能靠省略表达",
            )
        )
    declared_ids = defn.source_field_ids
    for fd in defn.flags:
        loc = f"{where}:flags[{fd.name}]"
        if fd.name not in vocabulary:
            add(
                Finding(
                    "R4.FLAG_NOT_IN_VOCABULARY",
                    loc,
                    f"{fd.name!r} 不在全局受控词表内，指标不得自造 flag",
                )
            )
        elif vocabulary.scope_of(fd.name) == "system":
            add(
                Finding(
                    "R4.SYSTEM_SCOPE_FLAG_DECLARED",
                    loc,
                    f"{fd.name!r} 是 system 域 flag，由运行时产出，定义文件内不得声明",
                )
            )
        cond, err = _parse(fd.trigger)
        if cond is None:
            add(Finding("R4.TRIGGER_UNPARSEABLE", loc, f"触发条件不可求值：{err}"))
        else:
            for ref in sorted(cond.field_refs):
                root = ref.split(".", 1)[0]
                if root in dsl.ROOT_NAMESPACES and ref not in declared_ids:
                    add(
                        Finding(
                            "R4.TRIGGER_UNDECLARED_FIELD",
                            loc,
                            f"触发条件引用了未在 source_fields 声明的字段 {ref}",
                        )
                    )

    # ---- R5 准则依据结构化 ----------------------------------------------
    if not defn.standard_basis:
        add(Finding("R5.BASIS_NOT_STRUCTURED", where, "缺少 standard_basis"))
    for idx, sb in enumerate(defn.standard_basis):
        loc = f"{where}:standard_basis[{idx}]"
        if not isinstance(sb.raw, dict):
            add(
                Finding(
                    "R5.BASIS_NOT_STRUCTURED",
                    loc,
                    "条目是自由文本而非结构化映射（须含 name/issuer/article/version）",
                )
            )
            continue
        for key in ("name", "issuer", "article", "version"):
            if not str(getattr(sb, key) or "").strip():
                add(Finding("R5.BASIS_FIELD_EMPTY", loc, f"缺少 {key}"))

    # ---- R6 缺失表示与取值域 --------------------------------------------
    string_compared: set[str] = set()
    for cond_text in [fd.trigger for fd in defn.flags] + [
        uc.expr for uc in defn.undefined_conditions
    ]:
        cond, _ = _parse(cond_text)
        if cond is None:
            continue
        string_compared |= _fields_compared_to_strings(cond.tree)

    for sf in defn.source_fields:
        if not sf.id:
            continue
        if not sf.declares_missing_representation:
            add(
                Finding(
                    "R6.NO_MISSING_REPRESENTATION",
                    f"{where}:source_fields[{sf.id}]",
                    "未声明 missing_representation：缺失与取值为零无法区分，二者后果相反",
                )
            )
        if sf.id in string_compared and not sf.enum_values:
            add(
                Finding(
                    "R6.ENUM_WITHOUT_VALUES",
                    f"{where}:source_fields[{sf.id}]",
                    "在条件中与字符串字面量做等值比较，但未声明 enum_values 合法取值集合",
                )
            )

    # ---- R7 未定义条件 --------------------------------------------------
    if not defn.undefined_conditions:
        add(
            Finding(
                "R7.NO_UNDEFINED_CONDITIONS",
                where,
                "缺少 undefined_conditions：拒答边界必须可机械求值",
            )
        )
    for idx, uc in enumerate(defn.undefined_conditions):
        loc = f"{where}:undefined_conditions[{idx}]"
        cond, err = _parse(uc.expr)
        if cond is None:
            add(Finding("R7.EXPR_UNPARSEABLE", loc, f"条件不可求值：{err}"))
        if not str(uc.reason or "").strip():
            add(Finding("R7.REASON_EMPTY", loc, "reason 为空，拒答理由必须可机读"))

    # ---- R8 陷阱必须可执行或标注（元规则，本次扩展的核心）----------------
    if len(defn.common_pitfalls) < _MIN_PITFALLS:
        add(
            Finding(
                "R8.TOO_FEW_PITFALLS",
                where,
                f"common_pitfalls 仅 {len(defn.common_pitfalls)} 条，少于 {_MIN_PITFALLS} 条",
            )
        )
    for idx, pf in enumerate(defn.common_pitfalls):
        loc = f"{where}:common_pitfalls[{idx}]"
        has_enforced = bool(str(pf.enforced_by or "").strip())
        if has_enforced and pf.advisory_only:
            add(
                Finding(
                    "R8.BOTH_ENFORCED_AND_ADVISORY",
                    loc,
                    "同时声明 enforced_by 与 advisory_only，二者互斥",
                )
            )
        elif not has_enforced and not pf.advisory_only:
            add(
                Finding(
                    "R8.PITFALL_UNBACKED",
                    loc,
                    "既无 enforced_by 也无 advisory_only —— 散文冒充规则，元规则不允许",
                )
            )
        if has_enforced:
            err = _resolve_enforced_by(pf.enforced_by, defn, vocabulary)
            if err:
                add(Finding("R8.ENFORCED_BY_UNRESOLVED", loc, err))

    # ---- R9 版本语义 ----------------------------------------------------
    if not isinstance(defn.version, int) or isinstance(defn.version, bool):
        add(Finding("R9.VERSION_NOT_INT", where, f"version={defn.version!r} 必须是整数"))
    elif require_v2 and defn.version < 2:
        add(
            Finding(
                "R9.VERSION_TOO_LOW",
                where,
                f"version={defn.version} —— 新 schema 下的定义从 version: 2 起，v1 是旧契约的历史样本",
            )
        )

    return findings


def _fields_compared_to_strings(node) -> set[str]:
    if isinstance(node, dsl.Compare):
        pairs = ((node.left, node.right), (node.right, node.left))
        return {
            a.path
            for a, b in pairs
            if isinstance(a, dsl.FieldRef) and isinstance(b, dsl.Literal) and isinstance(b.value, str)
        }
    if isinstance(node, dsl.Not):
        return _fields_compared_to_strings(node.operand)
    if isinstance(node, (dsl.And, dsl.Or)):
        return _fields_compared_to_strings(node.left) | _fields_compared_to_strings(node.right)
    return set()


def _resolve_enforced_by(
    ref: str, defn: MetricDefinition, vocabulary: Vocabulary | None = None
) -> str | None:
    """把 enforced_by 的点号路径解析到实际承载体。解析不到就返回错误说明。"""
    parts = ref.split(".", 1)
    if len(parts) != 2:
        return f"enforced_by={ref!r} 不是 <类别>.<标识> 形式"
    kind, ident = parts
    if kind == "flags":
        # 定义内声明的标记，**加上**词表里的 system 域标记。
        #
        # 后者不是宽容，是必需：R4 禁止定义文件声明 system 域标记，
        # 若 R8 又只认定义内声明的标记，那么任何「跨期不可比」类的陷阱
        # 都**在构造上无法满足 R8**——两条 Requirement 会直接打架。
        # system 域标记的机械承载体是运行时（如 check_comparable），
        # 它确实存在，只是不在这份文件里。R8 问的是「有没有可求值的规则」，
        # 不是「规则写在不写在本文件」。
        names = {fd.name for fd in defn.flags}
        if vocabulary is not None:
            names |= vocabulary.system_scoped
        return None if ident in names else f"enforced_by={ref!r} 指向不存在的 flag"
    if kind == "source_fields":
        attrs = {"id", "statement", "line_item", "sign_convention", "missing_representation", "enum_values"}
        return None if ident in attrs else f"enforced_by={ref!r} 指向不存在的 source_fields 属性"
    if kind == "undefined_conditions":
        if not ident.isdigit():
            return f"enforced_by={ref!r} 的下标必须是非负整数"
        idx = int(ident)
        if idx >= len(defn.undefined_conditions):
            return f"enforced_by={ref!r} 的下标越界（当前只有 {len(defn.undefined_conditions)} 条）"
        return None
    return f"enforced_by={ref!r} 的类别 {kind!r} 不被支持"


def validate_paths(
    paths: list[Path | str],
    vocabulary_path: Path | str | None = None,
    *,
    require_v2: bool = True,
) -> dict[str, list[Finding]]:
    vocab = load_vocabulary(vocabulary_path) if vocabulary_path else load_vocabulary()
    out: dict[str, list[Finding]] = {}
    for p in paths:
        defn = load_definition(p)
        out[str(p)] = validate_definition(defn, vocab, require_v2=require_v2)
    return out
