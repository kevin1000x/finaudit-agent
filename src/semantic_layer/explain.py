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
3. **正文里不出现字段标识符；机器那一版集中放到末尾的核对附录。**
   （2026-09-04 收紧，`N-52` 第二轮。）此前是「中文在上、表达式紧跟在下」，
   于是 `is.net_profit_attributable_to_parent - notes.nonrecurring_pl_net_...`
   这种东西夹在每一节正文里。操作者的原话：**「你给财务人看这种技术说辞吗」**。
   ⇒ 正文只用定义自己写的中文（`line_item` / `statement` / flag 的 `description`），
   表达式全部下沉到附录，**一个字都不删** —— 删了就没法核对翻译对不对。
   ⚠️ 附录不是「补充材料」，它是**可复核性的载体**：`D-032` 明写两版并存的理由。

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


#: 散文里出现的 schema 键名 → 本视图里那一节叫什么。
#: **不是翻译，是指路**：读者手上只有这一页，`undefined_conditions` 对他没有指称。
#: 长键在前，否则 `derivation` 会先咬掉 `derivation.note` 的一截。
_SCHEMA_IN_PROSE = {
    "derivation.note": "上面「这是什么」里的加总范围说明",
    "missing_representation": "「取数出处」里各行的缺失表示",
    "undefined_conditions": "「什么时候不给答案」那一节",
    "allow_from_components": "「能不能由分项推导」的声明",
    "common_pitfalls": "「会改变结果的注意事项」那一节",
    "sign_convention": "「取数出处」里各行的符号约定",
    "standard_basis": "「依据」那一节",
    "source_fields": "「取数出处」那一节",
    "advisory_only": "「仅供参考，不影响计算」那一节",
    "enforced_by": "「由哪一条把关」",
    "line_item": "「取数出处」里的行项目名",
    "derivation": "上面「这是什么」那一节",
}


def _prose(defn: MetricDefinition, text) -> str:
    """定义里的散文 → 财务读者读得下去的散文。**只换指称，不动一个论断。**

    2026-09-04 量过：**16 / 20 份定义的散文里写着字段 id 或 schema 键名**
    （`bs.total_current_liabilities_period_begin`、`按 undefined_conditions 拒答`……）。
    正文的表达式下沉到附录之后，这些就是剩下的技术噪声，
    而它们**不是渲染器加的，是定义文件自己写的**。

    两步替换，都用定义自己的词或本视图自己的小节名：
    1. 字段 id → `source_fields[].line_item`（与 `_formula_in_chinese` 同一份映射）
    2. schema 键名 → 本视图里那一节的标题

    ⚠️ **换不动的原样留着，不编。** 最典型的是「不得使用某字段」里那个
    **被禁用的**字段 —— 它按定义不会出现在 `source_fields` 里，于是没有中文名。
    编一个出来，读者就没法发现禁的到底是哪一个。
    """
    out = str(text)
    fields = sorted(
        (sf for sf in defn.source_fields if sf.id and sf.line_item),
        key=lambda sf: -len(sf.id),
    )
    for sf in fields:
        name = str(sf.line_item).split("——")[0].split("(")[0].strip()
        out = out.replace(sf.id, f"「{name}」")
    for key, where in sorted(_SCHEMA_IN_PROSE.items(), key=lambda kv: -len(kv[0])):
        out = out.replace(key, where)
    return _plain(out)


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


def _resolve_ref(
    defn: MetricDefinition, ref: str, flag_descriptions: dict | None = None
) -> str:
    """把 `enforced_by` 的 schema 路径换成读者认得的东西。

    `report.py` 的 docstring 早就点明了这条代价：下标形式「重排列表会静默
    指向别处」，所以报告里必须带出**被引用条目的原文**，而不是留一个数字。
    「由哪一条把关：undefined_conditions.2」对读 YAML 的人尚可，对旁人是无意义的。

    解不开就**原样返回**，不编 —— 编一个好看的说法出来，
    读者就没法发现这条引用其实指错了地方。
    """
    if ref.startswith("undefined_conditions."):
        _, _, idx = ref.partition(".")
        if idx.isdigit() and int(idx) < len(defn.undefined_conditions):
            cond = defn.undefined_conditions[int(idx)]
            # 与正文里那一条**逐字一致**，否则读者对不上是哪一条。
            return f"拒答条件「{_prose(defn, cond.reason)}」"
    if ref.startswith("flags."):
        name = ref.split(".", 1)[1]
        desc = (flag_descriptions or {}).get(name)
        # 有中文就用中文；没有就留原名 —— **不编**。
        return f"可比性标记「{desc}」" if desc else f"可比性标记「{name}」"
    if ref == "derivation.note":
        return "上面「这是什么」里的加总范围说明"
    if ref == "derivation.allow_from_components":
        return "上面「这是什么」里关于「能不能由分项推导」的声明"
    # `source_fields.<key>` 指的是「取数出处」那一节里各行的某一栏。
    # 直接把 schema 键名打出来（`字段声明里的 sign_convention`）等于给财务读者看代码。
    _SF = {
        "id": "上面「取数出处」列的那几行（取哪个字段是钉死的）",
        "line_item": "上面「取数出处」里的行项目名",
        "statement": "上面「取数出处」里的报表名",
        "sign_convention": "上面「取数出处」里各行的符号约定",
        "missing_representation": "上面「取数出处」里各行的缺失表示",
    }
    if ref.startswith("source_fields."):
        key = ref.split(".", 1)[1]
        if key in _SF:
            return _SF[key]
    return ref


def _source_lines(defn: MetricDefinition) -> list[str]:
    """「取数出处」：每个字段一行，**只用定义自己写的 `line_item` 与 `statement`**。

    这一节替代的是此前正文里那条字段 id 表达式。读者要知道的是
    「这个数去年报的哪张表哪一行取」，而不是它在 schema 里叫什么。
    """
    out: list[str] = []
    for sf in defn.source_fields:
        name = _plain(sf.line_item) if sf.line_item else None
        where = _plain(sf.statement) if sf.statement else None
        if not name and not where:
            continue
        # 报表在前、行项目在后，读成一条出处引用。
        # ⚠️ 不要用「——」把两者连起来：`line_item` 自己就常带「—— 期末余额」，
        #    同一个分隔符并排三段，读者分不出哪一段是表名。
        text = name or "（这一行没写行项目名）"
        text = f"{where} · {text}" if where else text
        out.extend(_wrap(f"· {text}", indent="      "))
    return out


def _appendix(defn: MetricDefinition, flag_descriptions: dict | None) -> list[str]:
    """末尾的核对附录：中文说法在上，系统实际执行的那一版在下（`↳`）。

    ⚠️ **它不是补充材料，是可复核性的载体**（`D-032`）——
    只留中文，读的人就没法核对翻译对不对。所以这里一个表达式都不删。
    """
    blocks: list[tuple[str, list[tuple[str, str]]]] = []

    if defn.formula:
        chinese = _formula_in_chinese(defn) or "（这条公式换不成中文，见上）"
        blocks.append(("公式", [(chinese, " ".join(str(defn.formula).split()))]))

    ids = [(f"{_plain(sf.line_item)}" if sf.line_item else str(sf.id), str(sf.id))
           for sf in defn.source_fields if sf.id]
    if ids:
        blocks.append(("取数出处的字段名", ids))

    conds = [(_plain(c.reason) if c.reason else "（这一条没写理由）", str(c.expr))
             for c in defn.undefined_conditions if c.expr]
    if conds:
        blocks.append(("拒答条件", conds))

    flags = []
    for f in defn.flags:
        if not f.trigger:
            continue
        desc = (flag_descriptions or {}).get(f.name)
        flags.append((f"{desc}（{f.name}）" if desc else str(f.name), str(f.trigger)))
    if flags:
        blocks.append(("可比性标记", flags))

    if not blocks:
        return []

    L = ["", _rule(), "系统实际执行的表达式"]
    L.extend(_wrap(
        "放在这里，是为了让人能核对上面每一句中文有没有译错 —— 这是本视图可复核性的落点。"
        "看不懂可以跳过，它不影响读懂上面任何一句。", indent="  "))
    for title, pairs in blocks:
        L.append("")
        L.append(f"  {title}")
        for chinese, machine in pairs:
            L.extend(_wrap(chinese, indent="      "))
            L.append(f"      ↳ {machine}")
    return L


def render_explanation(
    defn: MetricDefinition, flag_descriptions: dict | None = None
) -> str:
    """一份定义 → 一页中文简介。**内容全部来自 `defn`，不新增。**

    `flag_descriptions` 是 `metrics/_flags.yaml` 的 `name -> description`，
    可以不给：不给就退回打 flag 的原名，**不编中文**。
    """
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
    # 机器那一版**不在这里** —— 它在末尾的核对附录里，一个字都没删。
    src = _source_lines(defn)
    if src:
        L.append("")
        L.append("    取数出处（都在年报里，可照着核）")
        L.extend(src)
    note = defn.derivation.get("note") if isinstance(defn.derivation, dict) else None
    if note:
        L.append("")
        L.extend(_wrap(_prose(defn, note)))
    L.append("")

    # ── 什么时候不给答案 ──
    # 只给中文：读者要的是「什么时候」，不是「怎么判」。判据在附录。
    L.append(f"{_H_REFUSE}（满足任一条即拒答，不猜）")
    if not defn.undefined_conditions:
        L.append("    （本定义没有声明拒答条件）")
    for cond in defn.undefined_conditions:
        reason = _prose(defn, cond.reason) if cond.reason else "（这一条没写理由）"
        L.extend(_wrap(f"· {reason}", indent="    "))
    L.append("")

    # ── 陷阱拆成两节 ──
    # 这是本模块存在的第二个理由：原来这个区别只在键名上。
    enforced = [p for p in defn.common_pitfalls if not p.advisory_only]
    advisory = [p for p in defn.common_pitfalls if p.advisory_only]

    L.append(f"{_H_ENFORCED}（{len(enforced)} 条）")
    for p in enforced:
        L.extend(_wrap(f"· {_prose(defn, p.text)}", indent="    "))
        if p.enforced_by:
            ref = _resolve_ref(defn, p.enforced_by, flag_descriptions)
            L.extend(_wrap(f"由哪一条把关： {ref}", indent="        "))
    L.append("")

    L.append(f"{_H_ADVISORY}（{len(advisory)} 条）")
    if not advisory:
        L.append("    （无）")
    for p in advisory:
        L.extend(_wrap(f"· {_prose(defn, p.text)}", indent="    "))
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
            desc = (flag_descriptions or {}).get(f.name)
            L.extend(_wrap(f"· {desc or f.name}", indent="    "))

    L.extend(_appendix(defn, flag_descriptions))
    return "\n".join(L)
