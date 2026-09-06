"""答案组装：把计算结果与证据链拼成一个**可复核**的答案（`02-01` T3）。

## 两件产物，不是一件

1. **结构化答案对象** —— `AC-05` 的字段齐全率数的是它。
2. **人读渲染** —— `AC-06` 的复核者限时 5 分钟仅凭证据链判对错，**他读的就是这个**。
   `D-032`：`explain` 的表达契约上升为答案契约，口径一节**内嵌**
   `render_explanation` 的正文，不另写一份口径讲法。

⚠️ **「复用」指的是契约不是函数**：`render_explanation(defn)` 只吃定义、不吃计算结果。
所以答案特有的部分按同一套规矩**新写**，而附录**只有一个、在最末尾** ——
定义那份的附录内容并进来，不另起一段。

## 为什么不复用 `extractor.pipeline.evidence_completeness` 本身

那个函数按 `REQUIRED_EVIDENCE_KEYS` 数，而那套键是**PDF 抽取路径**的
（`page` / `anchor_page` / `pdf_sha256` / `column_header` …）。
frozen-01 走的是合成夹具，**没有 PDF、没有页码**。
给它们填一个数就是**伪造证据** —— 比缺证据严重得多。

⇒ 本模块用 frozen-01 题面自己声明的那套键，但**「齐全」的口径逐字沿用**：
键不存在、`null`、空串、占位值、恒零**一律不计入齐全**（`AC-05` 2026-08-22 写死）。
占位值词表**直接 import 同一个对象**，不抄一份 —— 有测试锁住它是同一个对象。

## 数据源适配器

`extractor.formula.evaluate_formula` 是全仓唯一的算术求值器（`D-017`），**不另写一个**。
它只通过 `by_field(path)` 取数、只读记录的 `retrieval` / `cell_state` / `value`
三个属性 ⇒ 夹具用一个同形的轻量记录接上去。
⚠️ 适配器**不冒充 `ExtractionRecord`**：它没有 `page` / `pdf_sha256`，
因为夹具确实没有这些东西。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

from extractor.formula import evaluate_formula, field_refs, parse_formula
from extractor.pipeline import PLACEHOLDER_TEXTS
from extractor.record import CellState, RetrievalOutcome
from semantic_layer import dsl
from semantic_layer.definition import MetricDefinition
from semantic_layer.explain import (
    appendix_blocks,
    render_appendix,
    render_explanation,
    rule,
    wrap,
)
from semantic_layer.resolve import (
    Refusal,
    RefusalCode,
    Registry,
    active_flags,
    comparison_scoped_flags,
    evaluate_refusal,
)

from .gate import GateRequest, execute, pre_execute
from .intent import Intent, parse_intent

__all__ = [
    "REQUIRED_ANSWER_EVIDENCE",
    "FixtureSource",
    "Answer",
    "answer_question",
    "evidence_gaps",
    "evidence_stage",
    "render_answer",
    "required_answer_evidence",
]

#: 答案层证据链的必填键。**取自 frozen-01 题面自己声明的 `required_evidence`**，
#: 不是本模块发明的 —— 那三个键在 20 份题面里逐题写着。
REQUIRED_ANSWER_EVIDENCE: tuple = (
    "data_source",
    "metric_definition_version",
    "execution_hash",
)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class _FixtureCell:
    """夹具里的一个格子。**只有 `_operand` 真正会读的那三个属性。**

    刻意不长成 `ExtractionRecord`：那份记录带 `page` / `pdf_sha256`，
    而夹具没有 PDF。**给它们编一个值就是伪造证据。**
    """

    retrieval: RetrievalOutcome
    cell_state: CellState
    value: Any


class FixtureSource:
    """一份合成夹具里的一行。接上 `evaluate_formula`，不改那个求值器。"""

    def __init__(self, path, stock_code=None, fiscal_year=None, _raw=None):
        import yaml

        self.path = Path(path)
        # `_raw` 只由 `at()` 传：换一行取数时**沿用已经读进来的那份字节**。
        # 再读一次的代价不是性能，是**出处哈希会静默换成另一个值** ——
        # 两次读之间文件若被改动，`batch_id` 指的就不是同一份夹具了。
        raw_bytes = self.path.read_bytes() if _raw is None else _raw
        self._raw = raw_bytes
        self.sha256 = hashlib.sha256(raw_bytes).hexdigest()
        data = yaml.safe_load(raw_bytes.decode("utf-8")) or {}
        self.fixture_id = (data.get("meta") or {}).get("fixture_id") or self.path.stem
        self.stock_code = None if stock_code is None else str(stock_code)
        self.fiscal_year = None if fiscal_year is None else int(fiscal_year)
        rows = [
            r
            for r in (data.get("rows") or [])
            if self.stock_code is not None
            and str(r.get("stock_code")) == self.stock_code
            and int(r.get("fiscal_year", -1)) == self.fiscal_year
        ]
        self.row: dict = dict(rows[0]) if rows else {}
        self.found = bool(rows)

    def at(self, stock_code, fiscal_year) -> "FixtureSource":
        """同一份夹具，换一行。**沿用同一份字节**，不重新读盘。

        2026-09-05 修：此前这里新建一个 `FixtureSource`，构造函数又读了一遍文件 ——
        注释写的「文件只读一次」当时是假的，且两次读之间文件被改动的话，
        证据链里那个出处哈希会**静默**换成另一个值。
        """
        return FixtureSource(self.path, stock_code, fiscal_year, _raw=self._raw)

    @property
    def batch_id(self) -> str:
        """出处标识。**说清它是合成夹具** —— 把合成数据说成真实数据比数据本身更严重。"""
        head = "fixture:" + self.fixture_id + "@" + self.sha256[:12]
        if self.stock_code is None:
            # 还没走到「取哪一行」这一步。**说清是哪一份夹具就够了**，不编一个行号。
            return head
        return head + "#" + self.stock_code + "/" + str(self.fiscal_year)

    def by_field(self, path: str):
        """`evaluate_formula` 的取数入口。不在夹具里就返回 `None`（上游给 `UNAVAILABLE`）。"""
        if path not in self.row:
            return None
        raw = self.row[path]
        if raw is None:
            return _FixtureCell(RetrievalOutcome.GOT_VALUE, CellState.EMPTY_CELL, None)
        try:
            return _FixtureCell(
                RetrievalOutcome.GOT_VALUE, CellState.VALUE_PRESENT, Decimal(str(raw))
            )
        except Exception:
            # 非数值（如 `notes.business_combination_type: 无`）照原样交出去，
            # `_operand` 会判它「不是十进制数，不参与算术」—— 那是对的。
            return _FixtureCell(RetrievalOutcome.GOT_VALUE, CellState.VALUE_PRESENT, raw)


def evidence_stage(answer) -> str:
    """这条答案该按哪一档必填键来数。

    🔴 **判据是「有没有解析出指标」，不是 `gate` 的取值。**
    2026-09-04 独立复核发现：`gate="not_reached"` 此前被同时用于两件事 ——
    「指标没解析出来」与「指标解析出来了但数据源没这一行」。
    收窄只对第一件成立；第二件里 `metric_definition_version` 是**合法已知**的，
    反方向检查却会报「这一步不该有版本」⇒ 一个完全正确的 `UNAVAILABLE` 拒答
    会让 `AC-05` 这条**保证类**门变红。
    """
    return "no_metric" if getattr(answer, "metric_id", None) is None else "full"


def required_answer_evidence(stage: str) -> tuple:
    """这条答案按它**走到了哪一步**该有哪些键。

    照搬 `extractor.pipeline.required_evidence_keys` 的做法（`KIND-WIRING` §3.3）：
    `NOTE_CHECKBOX` 上 `unit` / `currency` 不适用，于是不按行值类的键表去数 ——
    否则每条 note 平白记三处缺口，`AC-05` 这条**保证类**标准会变成
    一个正确的实现永远达不到的标准。

    这里同理：题面连指标都没解析出来时（`stage="not_reached"`），
    **`metric_definition_version` 不适用** —— 没有指标，哪来的版本。

    ⚠️ **这不是「拒答就少查几项」的豁免**：那个键换成了**另一个方向**的检查 ——
    `evidence_gaps` 要求它此时必须是 `None`，填了值反而报缺口。
    检查没有变松，只是换了方向。
    """
    if stage == "no_metric":
        return tuple(k for k in REQUIRED_ANSWER_EVIDENCE if k != "metric_definition_version")
    return REQUIRED_ANSWER_EVIDENCE


def evidence_gaps(payload: dict, keys: tuple = REQUIRED_ANSWER_EVIDENCE) -> list:
    """`AC-05` 的口径：**「齐全」= 字段有真值，不是「键存在」。**

    空串、`null`、占位值（`unknown` / `n/a` / `待定` …）、恒零一律不计入齐全。
    占位值词表**直接用 `extractor.pipeline.PLACEHOLDER_TEXTS` 这个对象**，不抄一份。
    """
    gaps = []
    if "metric_definition_version" not in keys and payload.get("metric_definition_version") is not None:
        # 反方向：这一步不该有版本，有了说明它是从别处抄来的
        gaps.append("metric_definition_version：这一步不该有版本，却填了值")
    for key in keys:
        if key not in payload:
            gaps.append(key + "：键不存在")
            continue
        value = payload[key]
        if value is None:
            gaps.append(key + "：键在但取值是 null")
        elif isinstance(value, str):
            if not value.strip():
                gaps.append(key + "：空字符串")
            elif value.strip().casefold() in PLACEHOLDER_TEXTS:
                gaps.append(key + "：占位值 —— 键在、非空，但一个字的信息也没有")
        elif isinstance(value, (int, float)) and not isinstance(value, bool) and value == 0:
            gaps.append(key + "：恒零")
    return gaps


@dataclass(frozen=True)
class Answer:
    """一次问答的完整产物。**拒答与作答是同一套字段。**

    ## `inputs` 与 `registry_snapshot` 是 `D-038` 加的，不是装饰

    2026-09-06 的 H2 第一轮判定**不成立**：一致率 13.3%、无法判断 86.7%、判「对」0 题。
    13 道「无法判断」的理由全部同形 —— **页面说了系统做了什么，没说它拿什么做的**。
    复核者的原话把判据说死了：**「执行哈希能标识一次执行，不能代替计算输入。」**

    - `inputs`：这次执行**真正读到的字段取值**。算数时是公式的输入（`G1`）；
      因为某条拒答条件成立而拒答时，是**那一条**引用的字段的取值（`G2`）。
      ⚠️ `G1` 的数据此前**早就算出来了** —— `execution_hash` 里就有 ——
      但只进了哈希、从未渲染。**「算进哈希」与「给人看」是两件事。**
    - `registry_snapshot`：说「没有这个指标」时，当时语义层里到底有哪些
      指标与别名（`G3`）。没有它，`METRIC_NOT_DEFINED` 是一句不可证伪的断言。
    """

    question: str
    question_sha256: str
    metric_id: Any = None
    metric_version: Any = None
    entity: Any = None
    period: Any = None
    value: Any = None
    refusal: Any = None
    flags: list = field(default_factory=list)
    deferred_flags: list = field(default_factory=list)
    evidence: dict = field(default_factory=dict)
    gate: str = "not_reached"
    #: `D-038 G1` / `G2`：字段路径 → 这次真正读到的取值（字符串化，`None` 表示缺失）
    inputs: dict = field(default_factory=dict)
    #: `D-038 G3`：`{"metric_count", "names", "sha256"}`，只在「说没有这个指标」时带
    registry_snapshot: Any = None

    @property
    def refused(self) -> bool:
        return self.refusal is not None

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "question_sha256": self.question_sha256,
            "metric_id": self.metric_id,
            "metric_version": self.metric_version,
            "entity": self.entity,
            "period": self.period,
            "value": None if self.value is None else str(self.value),
            "refused": self.refused,
            "refusal": dict(self.refusal) if self.refusal else None,
            "flags": list(self.flags),
            "deferred_flags": list(self.deferred_flags),
            "evidence": dict(self.evidence),
            "gate": self.gate,
            "inputs": dict(self.inputs),
            "registry_snapshot": (
                dict(self.registry_snapshot) if self.registry_snapshot else None
            ),
        }


def registry_snapshot(registry: Registry) -> dict:
    """当时语义层里有哪些指标与别名（`D-038 G3`）。

    没有它，`METRIC_NOT_DEFINED` 是一句**不可证伪**的断言 ——
    H2 第一轮 15 题里有 6 题栽在这上面（复核者：「无法独立证明它是正确判定」）。

    `sha256` 哈希的是那份**排好序的名字表**，所以两次快照能直接比对；
    它证明的是「这一页列出的就是当时那份表」，**不**证明那份表是对的。
    """
    names = sorted(str(a) for a in registry.by_alias)
    return {
        "metric_count": len(registry.definitions),
        "names": names,
        "sha256": _sha256_text(json.dumps(names, ensure_ascii=False)),
    }


def _condition_inputs(defn: MetricDefinition, refusal, row: dict) -> dict:
    """触发了拒答的**那一条**条件引用了哪些字段、它们当时是什么值（`D-038 G2`）。

    判据是 `Refusal.condition_index` —— 定义作者写的第几条，`evaluate_refusal`
    逐条按序求值时记下来的，**不靠拿 `detail` 的措辞去反查**。

    拿不到条件（`condition_index` 为空，或越界）就返回空 ——
    **不猜是哪一条**：猜错会让读者去核一条根本没触发的条件。
    """
    index = getattr(refusal, "condition_index", None)
    if index is None or not (0 <= index < len(defn.undefined_conditions)):
        return {}
    expr = defn.undefined_conditions[index].expr
    if not expr:
        return {}
    try:
        tree = dsl.parse_condition(expr).tree
    except Exception:
        return {}
    paths = sorted({n.path for n in _walk_tree(tree) if isinstance(n, dsl.FieldRef)})
    return {p: _shown(row.get(p)) for p in paths}


def _walk_tree(node):
    """遍历 dsl 树。与 `gate._walk` 同形，但这里只用来找 `FieldRef`，不做检查。"""
    yield node
    for attr in ("operand", "left", "right"):
        child = getattr(node, attr, None)
        if child is not None and not isinstance(child, (str, int, float, bool)):
            yield from _walk_tree(child)


def _shown(value) -> str:
    """把一个取值渲染成**复核者能对着年报核**的样子。

    🔴 三种「没有」必须分开写死，不许都显示成空白：
    `None`（这一行根本没取到）/ `0`（取到了，就是零）/ 空串。
    H2 第一轮 H2-06 与 H2-12 栽的正是这里 ——
    「只知道它触发了，不知道触发得对」。
    """
    if value is None:
        return "（缺失：数据源里没有这一行）"
    if isinstance(value, bool):
        return "是" if value else "否"
    text = str(value)
    return text if text.strip() else "（空值）"


def _refused(intent_or_q, digest, refusal, evidence: dict, gate: str,
             inputs=None, snapshot=None) -> Answer:
    """拒答也留**同一套**字段。少记字段是最容易犯的，而拒答最需要能复核。

    ⚠️ **拒答也有 `execution_hash`。** 拒答是**正常业务结果**不是降级（`D-003`），
    因此它同样要可复现：哈希的是「做出这个判断时手里有什么」——
    题面、指标（可能没有）、拒答码、数据源。
    frozen-01 的题面自己也是这么要求的：C2 那几道拒答题的
    `required_evidence` 里逐题写着 `execution_hash`。
    """
    it = intent_or_q if isinstance(intent_or_q, Intent) else None
    evidence = dict(evidence)
    evidence["execution_hash"] = _sha256_text(
        json.dumps(
            {
                "question_sha256": it.question_sha256 if it else digest,
                "metric_id": refusal.metric_id or (it.metric_id if it else None),
                "refusal_code": refusal.code.name,
                "data_source": evidence.get("data_source"),
            },
            ensure_ascii=False, sort_keys=True,
        )
    )
    return Answer(
        question=it.question if it else str(intent_or_q),
        question_sha256=it.question_sha256 if it else digest,
        metric_id=refusal.metric_id or (it.metric_id if it else None),
        metric_version=evidence.get("metric_definition_version"),
        entity=it.entity if it else None,
        period=it.period if it else None,
        refusal=refusal.to_dict(),
        evidence=evidence,
        gate=gate,
        inputs=dict(inputs or {}),
        registry_snapshot=snapshot,
    )


def _formula_field_refs(defn: MetricDefinition) -> tuple:
    if not defn.formula:
        return ()
    return field_refs(parse_formula(str(defn.formula)))


def answer_question(
    question: str,
    registry: Registry,
    source=None,
    ask_model=None,
    expected_version=None,
) -> Answer:
    """题面 → `Answer`。**每一步的失败都落成拒答，不抛异常**（`D-022`）。

    ⚠️ 计算只可能发生在 `gate.execute()` 里 —— 那是全仓唯一的执行入口。

    `expected_version` 是调用方**声明它要哪一版口径**；`None` = 不声明、不比对。
    声明了而定义已经不是那一版 ⇒ 拒答，不拿另一版的口径作答。
    ⚠️ **评测运行器刻意不传它**：`expected.metric_version` 是题面的标准答案，
    喂回输入就是 `target_name` 那个错误（`N-57` 记着这道门今天没有生产触发点）。
    """
    digest = _sha256_text(" ".join(str(question).split()))
    base = {
        "data_source": source.batch_id if source else None,
        "metric_definition_version": None,
        "execution_hash": None,
    }

    intent = parse_intent(question, registry, ask_model=ask_model)
    if isinstance(intent, Refusal):
        # `D-038 G3`：说「**没有这个指标**」的时候，必须一并交出当时那份指标清单 ——
        # 否则这是一句不可证伪的断言。H2 第一轮 6 道题栽在这里（`VERIFICATION.md` §F）。
        #
        # ⚠️ **只挂在 `METRIC_NOT_DEFINED` 上，不挂在 `INTENT_INCOMPLETE` 上。**
        #    后者说的是「题面缺主体/期间」，那时 94 行指标清单与结论无关，
        #    摆出来只会让复核者在 5 分钟里翻一页跟他要判的事没关系的东西。
        #    **证据要相关，不是要多**（`AC-05` 的已知盲区正是「抓不到证据不相关」）。
        snapshot = (
            registry_snapshot(registry)
            if intent.code is RefusalCode.METRIC_NOT_DEFINED
            else None
        )
        return _refused(question, digest, intent, dict(base), "not_reached", snapshot=snapshot)

    # 意图解析成功之后才知道取哪一行。**夹具文件只读一次**（`source.at`），
    # 所以在此之前 `data_source` 已经能说清「是哪一份夹具」—— 不留空。
    if source is not None and source.stock_code is None:
        source = source.at(intent.entity, intent.period)
        base["data_source"] = source.batch_id

    # 🔴 **走 `registry.resolve()`，不是 `definitions.get()`。**
    # 只有 `resolve()` 会跑 `validate_definition`（9 条 Requirement）并在不合规时
    # 返回 `DEFINITION_NONCONFORMANT`；`definitions.get()` 拿到的是**未经校验**的定义。
    # 2026-09-04 独立复核实测：清空 `common_pitfalls`（⇒ `R8.TOO_FEW_PITFALLS`）之后，
    # `resolve()` 判「不许被消费」，而这里照样算出了 0.3。
    # ⚠️ 仓库级 CI（`semantic_layer validate`）挡不住这件事 ——
    # 它管的是 `metrics/` 里的定义，管不到运行时拿到的那一份。
    defn = registry.resolve(intent.metric_id)
    if isinstance(defn, Refusal):
        return _refused(intent, digest, defn, dict(base), "not_reached")
    base["metric_definition_version"] = defn.version

    if source is None or not source.found:
        return _refused(
            intent, digest,
            Refusal(
                RefusalCode.UNAVAILABLE,
                "数据源里没有 " + str(intent.entity) + " 的 " + str(intent.period) + " 年数据",
                metric_id=defn.metric_id,
                source="answer:数据源",
            ),
            dict(base), "not_reached",
        )

    # ── 闸门：每一棵会被求值的树都过一遍 ──────────────────────────
    # 拒答条件走 `dsl` 树；**公式里的字段引用也包成 `dsl.FieldRef` 一并过闸** ——
    # 否则「授权命名空间」与「字段已声明」这两道就只管条件不管公式，那是个洞。
    trees = [dsl.parse_condition(c.expr).tree for c in defn.undefined_conditions if c.expr]
    trees += [dsl.FieldRef(p) for p in _formula_field_refs(defn)]
    # 🔴 **可比性标记的 trigger 也要过闸。** `active_flags()` 会 `dsl.evaluate`
    # 每一条 trigger —— 漏掉它们，闸门声称的「单调前置」在这条分支上不成立。
    # 2026-09-04 独立复核实测：同一个未声明字段，单独送闸门被拒，
    # 写进 flag trigger 就被读出来了，标记还会进人读渲染的「可比性标记」一节。
    trees += [dsl.parse_condition(f.trigger).tree for f in defn.flags if f.trigger]

    # 🔴 **一个 `GateRequest`，装这一次会被求值的全部树。**
    #    2026-09-05 独立复核发现：此前这里逐棵送闸门，而下面送进 `execute()` 的是
    #    `trees[0]`，`run` 求的却是公式那棵 —— 闸门守的和被执行的不是同一个东西，
    #    留痕里的 `referenced_fields` 也只记了第一棵树的字段。
    #    合成一个请求之后，`execute()` 里那次无条件的 `pre_execute` 校的正是这一套。
    req = GateRequest(
        defn=defn, expected_version=expected_version, trees=tuple(trees),
        entity=intent.entity, period=intent.period, question_sha256=digest,
    )
    # ⚠️ 这一次显式过闸**不是多余的**：它必须排在 `evaluate_refusal` 之前。
    #    引用了未授权字段的条件，连「求值一下看看」都不许发生。
    blocked = pre_execute(req)
    if blocked is not None:
        return _refused(intent, digest, blocked, dict(base), "refused")

    # ── 口径层：这份定义自己声明的拒答条件 ────────────────────────
    hit = evaluate_refusal(defn, source.row)
    if isinstance(hit, Refusal):
        # `D-038 G2`：把**触发了的那一条**引用的字段连同取值一起交出去。
        # 只报「触发了」而不报「凭什么触发」，复核者只能确认它触发过，
        # 确认不了它**触发得对** —— H2 第一轮 H2-06 / H2-12 就是这么卡住的。
        return _refused(
            intent, digest, hit, dict(base), "passed",
            inputs=_condition_inputs(defn, hit, source.row),
        )

    # ── 计算：唯一入口，无条件先过闸门 ────────────────────────────
    tree = parse_formula(str(defn.formula))
    # **同一个 `req`** —— `execute()` 会再无条件过一遍闸门，校的就是上面那一套树。
    record = execute(req, run=lambda _req: evaluate_formula(tree, source))
    value = record.result
    if isinstance(value, Refusal):
        return _refused(intent, digest, value, dict(base), "passed")

    flags = active_flags(defn, source.row)
    if isinstance(flags, Refusal):
        return _refused(intent, digest, flags, dict(base), "passed")

    # `D-038 G1`：公式真正读到的那几个数。
    # 🔴 **这份东西此前就在这里**，但只被喂进了下面那个哈希，从未渲染出来。
    #    H2 第一轮 5 道计算题**全部**判「无法判断」，理由逐字是：
    #    「执行哈希能标识一次执行，不能代替计算输入」。
    #    ⇒ 现在它是 `Answer` 的字段，`render_answer` 会把它印在正文里。
    inputs = {p: _shown(source.row.get(p)) for p in sorted(_formula_field_refs(defn))}

    evidence = dict(base)
    evidence["execution_hash"] = _sha256_text(
        json.dumps(
            {
                "metric_id": defn.metric_id,
                "metric_version": defn.version,
                "formula": " ".join(str(defn.formula).split()),
                "data_source": source.batch_id,
                "inputs": {p: str(source.row.get(p)) for p in sorted(_formula_field_refs(defn))},
                "value": str(value),
            },
            ensure_ascii=False, sort_keys=True,
        )
    )
    return Answer(
        question=intent.question,
        question_sha256=intent.question_sha256,
        metric_id=defn.metric_id,
        metric_version=defn.version,
        entity=intent.entity,
        period=intent.period,
        value=value,
        flags=sorted(flags),
        deferred_flags=sorted(comparison_scoped_flags(defn)),
        evidence=evidence,
        gate="passed",
        inputs=inputs,
    )


# --------------------------------------------------------------------------
# 人读渲染（`D-032`）
# --------------------------------------------------------------------------
#
# `AC-06` 的复核者限时 5 分钟仅凭证据链判对错 —— **他读的就是下面这个函数的输出**。
#
# 契约与 `explain` 同一套（`D-032` 及其 2026-09-04 收紧条）：
#   · 小标题用**问句**，不用字段名
#   · 中文说法在正文，**系统实际执行的那一版在末尾附录**
#   · 正文里不出现字段标识符、哈希这类东西
#   · **附录只有一个，在最末尾** —— 定义那份的附录内容并进来，不另起一段
#
# ⚠️ 排版件（`wrap` / `rule` / `render_appendix`）**从 `explain` import**，不重写。
#    两处渲染长得一样，是因为它们走同一段代码；各写一份必然漂移。

_A_ASKED = "问的是什么"
_A_ANSWER = "答案"
_A_REFUSED = "为什么不给答案"
_A_WHERE = "这个数是从哪儿来的"
_A_BASIS = "用的是哪个口径"
#: `D-038 G1` —— 算数时读到的那几个数
_A_INPUTS = "这个数是拿哪几个数算出来的"
#: `D-038 G2` —— 拒答条件成立时，凭什么说它成立
_A_WHY_HIT = "凭什么说满足了这一条"
#: `D-038 G3` —— 说「没有这个指标」时，当时有哪些
_A_REGISTRY = "我们当时有哪些指标"


def _input_lines(defn, inputs: dict) -> list:
    """`字段 → 取值` 渲染成给财务读者看的一行行。

    中文名来自 `source_fields[].line_item`（定义自己写的），
    **换不动就原样留着 id，不编** —— 与 `explain._prose` 同一条规矩。
    """
    names = {}
    for sf in getattr(defn, "source_fields", []) or []:
        if sf.id and sf.line_item:
            names[sf.id] = str(sf.line_item).split("——")[0].split("(")[0].strip()
    out: list = []
    for path in sorted(inputs):
        label = names.get(path, path)
        out.extend(wrap("· " + label + "　" + str(inputs[path]), indent="    "))
    return out


def render_answer(answer: Answer, defn=None, flag_descriptions: dict | None = None) -> str:
    """一次问答 → 一页给人读的答案。**内容全部来自 `answer` 与 `defn`，不新增。**"""
    L: list = []
    L.append(_A_ASKED)
    L.extend(wrap(answer.question))
    L.append("")

    if answer.refused:
        L.append(_A_REFUSED)
        L.extend(wrap("· " + str(answer.refusal.get("detail") or "（没有给出理由）")))
        L.append("")
        # `D-038 G2`：拒答条件成立时，把那一条引用的字段连同取值摆出来。
        # 只说「触发了」，读者确认不了「触发得对」。
        if answer.inputs:
            L.append(_A_WHY_HIT)
            L.extend(_input_lines(defn, answer.inputs))
            L.append("")
    else:
        L.append(_A_ANSWER)
        L.extend(wrap(str(answer.value)))
        L.append("")
        # `D-038 G1`：算出来的数必须能被人拿这几个输入重算一遍。
        # 🔴 这一节是 H2 第一轮 5 道计算题全判「无法判断」直接换来的。
        if answer.inputs:
            L.append(_A_INPUTS)
            L.extend(_input_lines(defn, answer.inputs))
            L.append("")

    # 可比性标记：`D-031` —— 一个没人看得见的标记等于没有标记
    if answer.flags or answer.deferred_flags:
        L.append("可比性标记（不影响算不算得出，影响能不能跨期比）")
        for name in answer.flags:
            L.extend(wrap("· " + str((flag_descriptions or {}).get(name) or name)))
        for name in answer.deferred_flags:
            L.extend(
                wrap("· " + str((flag_descriptions or {}).get(name) or name) + "（要有比较期才判得了）")
            )
        L.append("")

    L.append(_A_WHERE)
    src = answer.evidence.get("data_source")
    if src and str(src).startswith("fixture:"):
        # 说清它是**合成夹具** —— 把合成数据说成真实数据，比数据本身更严重（`D-010`）
        L.extend(wrap("· 合成夹具（虚构公司与数值），不是任何真实公司的年报"))
    elif src:
        L.extend(wrap("· " + str(src)))
    else:
        L.extend(wrap("· （这一步还没走到数据源）"))
    if answer.entity and answer.period:
        L.extend(wrap("· 取的是 " + str(answer.entity) + " 的 " + str(answer.period) + " 年那一行"))
    if answer.metric_version is not None:
        L.extend(wrap("· 口径定义版本 " + str(answer.metric_version)))
    L.append("")

    if defn is not None:
        L.append(_A_BASIS)
        L.append("")
        # 🔴 口径一节**内嵌 `render_explanation` 的正文，逐字一致**（`D-032`）。
        #    关掉它自带的附录 —— 附录只能有一个，在最末尾。
        L.append(render_explanation(defn, flag_descriptions, with_appendix=False))

    # `D-038 G3`：说「没有这个指标」时，把当时那份清单摆出来。
    # 不摆，`METRIC_NOT_DEFINED` 就是一句不可证伪的断言。
    snap = answer.registry_snapshot
    if snap:
        names = [str(n) for n in (snap.get("names") or [])]
        # 正文只列**中文叫法** —— 复核者要核的是「我说的那个词在不在里面」，
        # 而他脑子里那个词是中文。英文标识符是同一批东西的另一种写法，
        # 放附录（`D-032`：中文在正文，标识符在附录）。
        cjk = [n for n in names if any(ord(c) > 0x2E80 for c in n)]
        L.append(_A_REGISTRY)
        L.extend(
            wrap(
                "· 当时语义层里有 " + str(snap.get("metric_count")) + " 个指标定义，"
                "连同别名共 " + str(len(names)) + " 个可用的叫法，其中中文说法 "
                + str(len(cjk)) + " 个，全列在下面 ——"
                "可以直接核「你问的那个到底在不在里面」。"
                "英文标识符那一份在末尾附录。",
                indent="    ",
            )
        )
        for name in cjk:
            L.extend(wrap("· " + name, indent="      "))
        L.append("")

    blocks: list = []
    if defn is not None:
        blocks.extend(appendix_blocks(defn, flag_descriptions))
    if answer.inputs:
        # 正文给的是中文行项目名，附录给字段标识符 —— 同一条 `D-032` 规矩。
        blocks.append(
            ("这次读到的字段取值", [(k, str(v)) for k, v in sorted(answer.inputs.items())])
        )
    if snap:
        # 附录给**完整**清单（含英文标识符）与它的指纹 ——
        # 正文那份只列了中文，附录这份才是「可以逐条对」的那份。
        pairs = [("这份清单的指纹", str(snap.get("sha256")))]
        pairs += [("可用的叫法", str(n)) for n in (snap.get("names") or [])]
        blocks.append(("指标清单快照", pairs))
    blocks.append(("这次执行", _execution_pairs(answer)))
    L.extend(render_appendix(blocks))
    return "\n".join(L)


def _execution_pairs(answer: Answer) -> list:
    """附录里属于**这一次执行**的成对内容：左边中文说法，右边核对用的原值。"""
    ev = answer.evidence
    pairs = [
        ("这次提问的指纹", str(answer.question_sha256)),
        ("数据源", str(ev.get("data_source"))),
        ("口径定义版本", str(ev.get("metric_definition_version"))),
        ("这次执行的指纹", str(ev.get("execution_hash"))),
    ]
    if answer.refused and answer.refusal:
        pairs.append(("拒答理由码", str(answer.refusal.get("code"))))
    if answer.value is not None:
        pairs.append(("算出来的数", str(answer.value)))
    return pairs
