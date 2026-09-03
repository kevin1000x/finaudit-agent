"""把一份指标定义讲给**人**听。

## 它为什么存在（`N-20`，2026-09-03 实测）

`01-08` 留了一个检查点：让一个**没参与编写**的人只读定义，回答两问 ——
「触发条件读得懂吗」「陷阱里哪些有机械后果、哪些只是提示」。
2026-09-03 操作者读了随机抽的两份，答**读不懂**。

那条判据写得很硬：**读不懂时须回到定义的表达形式重新设计，不是补文档。**
所以本模块**不是**一份说明文档，它是定义的**另一种表达形式** ——
同一份内容，换一个给人看的排法。

## 三条硬约束

1. **只重排，不新增。** 本模块不得引入任何 YAML 里没有的说法。
   每一行输出都能指回定义里的某个字段；加一句「解释性的补充」就变成了补文档，
   而那正是判据点名禁止的。
2. **机械后果与提示必须结构性分开**，不能靠读者去比对键名。
   原来的区别只在一条陷阱写的是 `enforced_by` 还是 `advisory_only:  true` ——
   七条陷阱要逐条比对才分得出来。这里拆成两个各自带标题的小节。
3. **拒答条件先给中文。** `undefined_conditions` 的每一条本来就有 `reason`，
   只是 `expr` 排在前面、占了视觉主位。这里把中文提到前面，
   表达式作为机器那一版**附在后面**，不删 —— 删了就没法核对两者是否一致。

⚠️ **这不替代读 YAML。** 它替代的是「只能读 YAML」。
证据链指向的仍然是定义文件本身；本模块只是让人有能力去核对它。
"""

from __future__ import annotations

from .definition import MetricDefinition

__all__ = ["render_explanation"]

#: 输出里每一节的标题。**用问句，不用字段名** ——
#: 读者带着问题来，小节标题应当是他的问题，不是我们的 schema。
_H_WHAT = "这是什么"
_H_REFUSE = "什么时候不给答案"
_H_ENFORCED = "会改变结果的注意事项"
_H_ADVISORY = "仅供参考，不影响计算"
_H_BASIS = "依据"


def _rule(char: str = "─", width: int = 68) -> str:
    return char * width


def _plain(text) -> str:
    """去掉 Markdown 的强调标记。

    定义文件里的 `**不得纳入**` 是给读 YAML 的人加重语气用的；
    在纯文本视图里它只是噪声。**只去标记，不动一个字**。
    """
    return " ".join(str(text).replace("**", "").split())


def _formula_in_chinese(defn: MetricDefinition) -> str | None:
    """把公式里的字段 id 换成定义自己写的中文行项目名。

    ⚠️ **这仍然是重排，不是新增**：中文来自 `source_fields[].line_item`，
    是定义文件自己写的。本函数不发明任何一个词。

    换不动就返回 None —— **不猜**。一个换了一半的公式比原样更难读，
    而且会让人以为剩下那半是特意保留的。
    """
    if not defn.formula:
        return None
    text = " ".join(str(defn.formula).split())
    # 长的 id 先换，否则 `is.operating_revenue_current` 会被
    # `is.operating_revenue` 这类前缀先咬掉一截。
    fields = sorted(
        (sf for sf in defn.source_fields if sf.id and sf.line_item),
        key=lambda sf: -len(sf.id),
    )
    for sf in fields:
        # 行项目原文常带「—— 本期金额」这类列限定，读公式时是干扰，去掉。
        name = str(sf.line_item).split("——")[0].split("(")[0].strip()
        text = text.replace(sf.id, name)
    return text if "." not in text.replace(" ", "") else None


def _wrap(text: str, indent: str = "    ", width: int = 64) -> list[str]:
    """按显示宽度折行。中日韩字符占两格，其余占一格。

    不用 `textwrap`：它按字符数算，中文行会短掉将近一半。

    ⚠️ 不在 ASCII 词中间断行：早先断出过 `derivation.no / te` 与
    `收益记正 / _损失记负`，把一个标识符劈成两半比不折行更难读。
    """
    import re

    # 切成「整个 ASCII 词」与「单个宽字符」两种原子，只在原子之间断。
    atoms = re.findall(r"[A-Za-z0-9_.（）()\[\]<>=+\-*/]+|\s+|.", " ".join(str(text).split()))
    out: list[str] = []
    line = ""
    used = 0
    for atom in atoms:
        w = sum(2 if ord(c) > 0x2E80 else 1 for c in atom)
        if used + w > width and line:
            out.append(indent + line.rstrip())
            line, used = "", 0
            if atom.isspace():
                continue
        line += atom
        used += w
    if line.strip():
        out.append(indent + line.rstrip())
    return out


def _resolve_ref(defn: MetricDefinition, ref: str) -> str:
    """把 `enforced_by` 的 schema 路径换成读者认得的东西。

    `report.py` 的 docstring 早就点明了这条代价：下标形式「重排列表会静默
    指向别处」，所以报告里必须带出**被引用条目的原文**，而不是留一个数字。
    「由这里执行：undefined_conditions.2」对读 YAML 的人尚可，对旁人是无意义的。

    解不开就**原样返回**，不编 —— 编一个好看的说法出来，
    读者就没法发现这条引用其实指错了地方。
    """
    if ref.startswith("undefined_conditions."):
        _, _, idx = ref.partition(".")
        if idx.isdigit() and int(idx) < len(defn.undefined_conditions):
            cond = defn.undefined_conditions[int(idx)]
            return f"拒答条件「{_plain(cond.reason)}」"
    if ref.startswith("flags."):
        return f"可比性标记「{ref.split('.', 1)[1]}」"
    if ref == "derivation.note":
        return "上面「这是什么」里的加总范围说明"
    if ref.startswith("source_fields."):
        return f"字段声明里的 {ref.split('.', 1)[1]}"
    return ref


def render_explanation(defn: MetricDefinition) -> str:
    """一份定义 → 一页中文简介。**内容全部来自 `defn`，不新增。**"""
    L: list[str] = []

    title = defn.display_name or defn.metric_id or defn.path.name
    L.append(f"{title}    {defn.metric_id or ''}    版本 {defn.version}")
    if defn.aliases:
        L.append(f"也叫：{'、'.join(str(a) for a in defn.aliases)}")
    L.append(_rule())
    L.append("")

    # ── 这是什么 ──
    L.append(_H_WHAT)
    chinese = _formula_in_chinese(defn)
    if chinese:
        L.extend(_wrap(chinese))
    if defn.formula:
        # 中文版在上、机器那版在下。**两版都留** ——
        # 只留中文，读的人就没法核对翻译对不对。
        L.append(f"        机器公式： {' '.join(str(defn.formula).split())}")
    note = defn.derivation.get("note") if isinstance(defn.derivation, dict) else None
    if note:
        L.append("")
        L.extend(_wrap(_plain(note)))
    L.append("")

    # ── 什么时候不给答案 ──
    # 中文在前、表达式在后：读者要的是「什么时候」，不是「怎么判」。
    L.append(f"{_H_REFUSE}（满足任一条即拒答，不猜）")
    if not defn.undefined_conditions:
        L.append("    （本定义没有声明拒答条件）")
    for cond in defn.undefined_conditions:
        reason = _plain(cond.reason) if cond.reason else "（这一条没写理由）"
        L.extend(_wrap(f"· {reason}", indent="    "))
        if cond.expr:
            L.append(f"        机器判据： {cond.expr}")
    L.append("")

    # ── 陷阱拆成两节 ──
    # 这是本模块存在的第二个理由：原来这个区别只在键名上。
    enforced = [p for p in defn.common_pitfalls if not p.advisory_only]
    advisory = [p for p in defn.common_pitfalls if p.advisory_only]

    L.append(f"{_H_ENFORCED}（{len(enforced)} 条）")
    for p in enforced:
        L.extend(_wrap(f"· {_plain(p.text)}", indent="    "))
        if p.enforced_by:
            L.append(f"        由这里执行： {_resolve_ref(defn, p.enforced_by)}")
    L.append("")

    L.append(f"{_H_ADVISORY}（{len(advisory)} 条）")
    if not advisory:
        L.append("    （无）")
    for p in advisory:
        L.extend(_wrap(f"· {_plain(p.text)}", indent="    "))
    L.append("")

    # ── 依据 ──
    L.append(_H_BASIS)
    if not defn.standard_basis:
        L.append("    （本定义没有声明准则依据）")
    for b in defn.standard_basis:
        # StandardBasis 是 dataclass，不是 dict —— 早先按 dict 取值时
        # 整个 repr 被打进了输出，那正是这一节要消灭的东西。
        name = getattr(b, "name", None) or str(b)
        article = getattr(b, "article", None)
        version = getattr(b, "version", None)
        tail = "　".join(x for x in (article, str(version) if version else None) if x)
        L.extend(_wrap(f"· {name}" + (f"　{tail}" if tail else ""), indent="    "))

    # 标记：它们改变的是「能不能比」，不是「算不算得出」，所以单独放最后。
    if defn.flags:
        L.append("")
        L.append("可比性标记（不影响算不算得出，影响能不能跨期比）")
        for f in defn.flags:
            L.extend(_wrap(f"· {f.name}", indent="    "))
            if f.trigger:
                L.append(f"        机器判据： {f.trigger}")

    return "\n".join(L)
