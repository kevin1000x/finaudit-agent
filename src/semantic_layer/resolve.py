"""指标解析与机读拒答（AC-02 / FR-02）。

D-003 的立场是**拒答是正确行为，不是降级成功**。这一条在本模块体现为类型选择：
`resolve()` 返回 `MetricDefinition | Refusal` 二选一——不返回 `None`、不向调用方抛异常。
拒答走正常返回路径，调用方无法「忘了处理」它。

fail-closed 贯穿全模块：
- 定义不合规 → 拒绝消费，哪怕名字对得上
- 条件求值不了 → 拒答，不当成 False 放行
- 触发条件求值不了 → 整体拒答，不悄悄漏掉一个标记
  （漏掉一个 `affects_comparability` 的标记 = 本该阻断的比较悄悄放行）
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from . import dsl
from .definition import MetricDefinition, iter_definition_paths, load_definition
from .validate import validate_definition
from .vocabulary import DEFAULT_VOCABULARY_PATH, Vocabulary, load_vocabulary

__all__ = [
    "RefusalCode",
    "Refusal",
    "Registry",
    "resolve_metric",
    "evaluate_refusal",
    "check_comparable",
    "active_flags",
    "comparison_scoped_flags",
    "render_refusal",
]


class RefusalCode(Enum):
    """拒答的机读原因。AC-02 要求「拒答理由可机读」，这个枚举就是那个理由的取值域。"""

    METRIC_NOT_DEFINED = "指标名在语义层中没有对应的口径定义"
    ALIAS_AMBIGUOUS = "别名指向多个指标"
    DEFINITION_NONCONFORMANT = "口径定义本身不合规，不允许被消费"
    UNDEFINED_CONDITION_HIT = "命中已声明的未定义条件"
    UNEVALUABLE_CONDITION = "条件无法对给定数据求值"
    CROSS_VERSION_COMPARISON = "两期结论由不同版本的口径定义产出"
    CROSS_BASIS_VERSION_COMPARISON = "两期所依据的准则版本不同"
    # 以下两支由 Phase 1.5 加入。前七支**全部是「口径或数据本身有问题」**，
    # 接上真实数据源与真实报表之后会撞上另外两类，没有一支表达得了。
    UNAVAILABLE = "口径服务或数据源不可达"  # D-022 决策一
    RECONCILIATION_FAILED = "该抽取批次的会计恒等式校验未通过"  # D-025


@dataclass(frozen=True)
class Refusal:
    code: RefusalCode
    detail: str
    metric_id: str | None = None
    condition_index: int | None = None
    # 责任方标识（L-9）：**哪个**数据源或**哪条**口径规则拒的。
    # 只说「证据不足」不合格——复核者据此无从判断该去修哪一处。
    # 形如 `cninfo:hisAnnouncement/query` 或 `reconcile:balance_sheet_identity`。
    source: str | None = None

    def to_dict(self) -> dict:
        """AC-02 的交付形式：键名固定、可直接 json.dumps。"""
        return {
            "refused": True,
            "code": self.code.name,
            "code_meaning": self.code.value,
            "detail": self.detail,
            "metric_id": self.metric_id,
            "condition_index": self.condition_index,
            "source": self.source,
        }


# --------------------------------------------------------------------------
# 名称解析
# --------------------------------------------------------------------------


@dataclass
class Registry:
    definitions: dict
    by_alias: dict
    vocabulary: Vocabulary

    @classmethod
    def load(
        cls,
        metrics_dir: Path | str = "metrics",
        vocabulary_path: Path | str | None = None,
    ) -> "Registry":
        """别名冲突在**加载期**抛错，不留到查询期。

        查询期才发现冲突，意味着它此前已经悄悄解析成某一个了——而「某一个」是
        `dict` 插入顺序决定的，不是任何人的决定。
        """
        definitions: dict[str, MetricDefinition] = {}
        by_alias: dict[str, str] = {}
        for path in iter_definition_paths(metrics_dir):
            defn = load_definition(path)
            if not defn.metric_id:
                continue
            if defn.metric_id in definitions:
                raise ValueError(
                    f"metric_id 重复：{defn.metric_id!r} 同时出现在 "
                    f"{definitions[defn.metric_id].path} 与 {path}"
                )
            definitions[defn.metric_id] = defn
            # display_name 也是这个指标的正当名字——它是给人看的规范名称。
            # 用户输入「毛利率」拿到 METRIC_NOT_DEFINED 是荒谬的，
            # 而靠作者记得把 display_name 抄进 aliases 是把机械问题交给纪律。
            names = [defn.metric_id, defn.display_name, *defn.aliases]
            for alias in [n for n in names if n]:
                alias = str(alias)
                if alias in by_alias and by_alias[alias] != defn.metric_id:
                    raise ValueError(
                        f"别名冲突：{alias!r} 同时指向 {by_alias[alias]!r} 与 {defn.metric_id!r}"
                    )
                by_alias[alias] = defn.metric_id
        vocab_path = Path(vocabulary_path) if vocabulary_path else DEFAULT_VOCABULARY_PATH
        vocab = load_vocabulary(vocab_path) if Path(vocab_path).is_file() else Vocabulary(0, {})
        return cls(definitions=definitions, by_alias=by_alias, vocabulary=vocab)

    def resolve(self, name: str) -> MetricDefinition | Refusal:
        """精确 metric_id → 别名 → 拒答。命中后先校验合规，不合规不许被消费。"""
        metric_id = self.by_alias.get(str(name).strip())
        if metric_id is None:
            return Refusal(
                RefusalCode.METRIC_NOT_DEFINED,
                f"指标名 {name!r} 不在语义层的 {len(self.definitions)} 个口径定义中。"
                "口径未定义时拒答，不猜。",
            )
        defn = self.definitions[metric_id]
        findings = validate_definition(defn, self.vocabulary)
        if findings:
            codes = sorted({f.code for f in findings})
            return Refusal(
                RefusalCode.DEFINITION_NONCONFORMANT,
                f"口径定义 {metric_id!r} 自身不合规（{len(findings)} 项：{codes}），不允许被消费。",
                metric_id=metric_id,
            )
        return defn


def resolve_metric(name: str, metrics_dir: Path | str = "metrics") -> MetricDefinition | Refusal:
    try:
        registry = Registry.load(metrics_dir)
    except ValueError as exc:
        return Refusal(RefusalCode.ALIAS_AMBIGUOUS, str(exc))
    return registry.resolve(name)


# --------------------------------------------------------------------------
# 条件求值
# --------------------------------------------------------------------------


def _normalized(defn: MetricDefinition, row: dict) -> dict:
    return dsl.normalize_row(
        dict(row),
        [
            {"id": sf.id, "missing_representation": sf.missing_representation}
            if sf.declares_missing_representation
            else {"id": sf.id}
            for sf in defn.source_fields
            if sf.id
        ],
    )


def evaluate_refusal(defn: MetricDefinition, row: dict) -> Refusal | None:
    """按书写顺序逐条求值 `undefined_conditions`，第一条为真即拒答。

    顺序是定义作者写的顺序，不重排——`condition_index` 要能直接对回 YAML 里的第几条。
    """
    data = _normalized(defn, row)
    for index, condition in enumerate(defn.undefined_conditions):
        if not condition.expr:
            continue
        try:
            parsed = dsl.parse_condition(condition.expr)
        except dsl.DslError as exc:
            return Refusal(
                RefusalCode.UNEVALUABLE_CONDITION,
                f"第 {index + 1} 条未定义条件不可解析：{condition.expr!r}：{exc}",
                metric_id=defn.metric_id,
                condition_index=index,
            )
        try:
            hit = dsl.evaluate(parsed, data)
        except dsl.MissingOperandError as exc:
            return Refusal(
                RefusalCode.UNEVALUABLE_CONDITION,
                f"第 {index + 1} 条未定义条件求值失败：{condition.expr!r}：{exc}",
                metric_id=defn.metric_id,
                condition_index=index,
            )
        if hit:
            return Refusal(
                RefusalCode.UNDEFINED_CONDITION_HIT,
                condition.reason or condition.expr,
                metric_id=defn.metric_id,
                condition_index=index,
            )
    return None


def comparison_scoped_flags(defn: MetricDefinition) -> set:
    """触发条件引用了 `comparison_period.*` 的标记名。

    这类标记**本质上是两期比较的产物**，单期数据无从判定——不是数据缺失，是问错了问题。
    它们由 `check_comparable()` 在比较路径上负责，不由单期的 `active_flags` 负责。
    """
    out = set()
    for flag in defn.flags:
        if not flag.trigger or not flag.name:
            continue
        try:
            parsed = dsl.parse_condition(flag.trigger)
        except dsl.DslError:
            continue
        if any(ref.startswith("comparison_period.") for ref in parsed.field_refs):
            out.add(flag.name)
    return out


def active_flags(defn: MetricDefinition, row: dict) -> set | Refusal:
    """求值单期能判定的 flag 触发条件。求值不了 → 整体拒答，不跳过。

    跳过是不行的：漏掉一个 `affects_comparability` 为真的标记，
    等于让一次本该被阻断的跨期比较悄悄通过。

    **例外是比较域标记**（触发条件引用 `comparison_period.*`）。它们不是「求值失败」，
    是单期语境下根本不适用——由 `check_comparable()` 在比较路径上独立负责。
    调用方要知道有哪些被推迟了，用 `comparison_scoped_flags()` 取，不静默丢弃。
    """
    data = _normalized(defn, row)
    deferred = comparison_scoped_flags(defn)
    active = set()
    for flag in defn.flags:
        if not flag.trigger or not flag.name or flag.name in deferred:
            continue
        try:
            if dsl.evaluate(dsl.parse_condition(flag.trigger), data):
                active.add(flag.name)
        except (dsl.DslError, dsl.MissingOperandError) as exc:
            return Refusal(
                RefusalCode.UNEVALUABLE_CONDITION,
                f"标记 {flag.name!r} 的触发条件求值失败：{flag.trigger!r}：{exc}",
                metric_id=defn.metric_id,
            )
    return active


# --------------------------------------------------------------------------
# 跨版本比较（spec R9 / R5）
# --------------------------------------------------------------------------


def check_comparable(a: MetricDefinition, b: MetricDefinition) -> Refusal | None:
    if a.metric_id != b.metric_id:
        # 比较两个不同指标不是「不可比」，是调用方用错了 API。
        raise ValueError(
            f"check_comparable 只用于同一指标的两期：收到 {a.metric_id!r} 与 {b.metric_id!r}"
        )
    if a.version != b.version:
        return Refusal(
            RefusalCode.CROSS_VERSION_COMPARISON,
            f"口径版本不同（{a.version} vs {b.version}）：版本变更即口径变更，历史结论不可跨版本比较。",
            metric_id=a.metric_id,
        )
    b_versions = {sb.name: sb.version for sb in b.standard_basis if sb.name}
    for sb in a.standard_basis:
        if sb.name in b_versions and b_versions[sb.name] != sb.version:
            return Refusal(
                RefusalCode.CROSS_BASIS_VERSION_COMPARISON,
                f"准则《{sb.name}》两期版本不同（{sb.version} vs {b_versions[sb.name]}）。",
                metric_id=a.metric_id,
            )
    return None


# --------------------------------------------------------------------------
# 渲染
# --------------------------------------------------------------------------


def render_refusal(
    outcome, as_json: bool = False, active: set | None = None, deferred: set | None = None
) -> str:
    import json

    if isinstance(outcome, Refusal):
        payload = outcome.to_dict()
        if as_json:
            return json.dumps(payload, ensure_ascii=False, indent=2)
        lines = [
            f"拒答：{outcome.code.name}",
            f"  含义：{outcome.code.value}",
            f"  详情：{outcome.detail}",
        ]
        if outcome.source:
            # 责任方要在**人看的那一面**也出现（L-9）。只进 to_dict 不进正文，
            # 等于把它做成了一个可选返回值——ARCHITECTURE §8.5 的实证是那种字段会被丢掉。
            lines.append(f"  责任方：{outcome.source}")
        if outcome.metric_id:
            lines.append(f"  指标：{outcome.metric_id}")
        if outcome.condition_index is not None:
            lines.append(f"  命中第 {outcome.condition_index + 1} 条未定义条件")
        return "\n".join(lines)

    payload = {
        "refused": False,
        "metric_id": outcome.metric_id,
        "display_name": outcome.display_name,
        "version": outcome.version,
        "active_flags": sorted(active or []),
        # 比较域标记不静默丢弃：单期语境判不了，但调用方必须知道有这些待判项
        "deferred_comparison_flags": sorted(deferred or []),
    }
    if as_json:
        return json.dumps(payload, ensure_ascii=False, indent=2)
    lines = [
        f"已解析：{outcome.metric_id}（{outcome.display_name}）",
        f"  口径版本：{outcome.version}",
        f"  触发标记：{'、'.join(payload['active_flags']) or '无'}",
    ]
    if payload["deferred_comparison_flags"]:
        lines.append(
            f"  待比较期判定：{'、'.join(payload['deferred_comparison_flags'])}"
            "（单期语境不适用，由 check_comparable 负责）"
        )
    return "\n".join(lines)
