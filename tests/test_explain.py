"""`semantic_layer.explain` 的回归（`N-20`）。

这个视图的价值全在「它说的就是定义说的」。一旦它开始加工内容，
读者读到的是渲染器的观点而不是定义本身，那比读不懂更糟 ——
读不懂至少是显性的。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from semantic_layer.definition import load_definition
from semantic_layer.explain import _formula_in_chinese, _resolve_ref, render_explanation

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture
def defn():
    return load_definition(REPO / "metrics" / "period_expense_ratio.yaml")


def test_陷阱被完整二分不丢不重(defn):
    """🔴 **这条是本模块存在的理由。**

    原来「有机械后果」与「只是提示」的区别只在一条陷阱写的是
    `enforced_by` 还是 `advisory_only: true` —— 七条要逐条比对键名。
    这里拆成两节，那么**二分必须是完备且互斥的**：
    少一条 = 有条陷阱在视图里消失了，而读者不会知道。
    """
    out = render_explanation(defn)
    enforced = [p for p in defn.common_pitfalls if not p.advisory_only]
    advisory = [p for p in defn.common_pitfalls if p.advisory_only]

    assert len(enforced) + len(advisory) == len(defn.common_pitfalls)
    assert f"会改变结果的注意事项（{len(enforced)} 条）" in out
    assert f"仅供参考，不影响计算（{len(advisory)} 条）" in out


def test_每条拒答条件都出现且带中文理由(defn):
    """「什么时候拒答」是判据的第一问。少列一条 = 读者以为它不会拒。"""
    out = render_explanation(defn)
    assert defn.undefined_conditions, "这份定义应当有拒答条件，夹具选错了"
    for cond in defn.undefined_conditions:
        assert cond.reason, "拒答条件缺 reason，视图就只能给表达式"
        assert cond.reason.split("；")[0] in out
        assert cond.expr in out, "表达式必须一并留着（在末尾附录里），否则没法核对两版是否一致"


def test_下标引用被解析成原文而不是留一个数字(defn):
    """`report.py` 早就记过这条代价：下标「重排列表会静默指向别处」。

    `由哪一条把关：undefined_conditions.2` 对旁人是无意义的。
    """
    assert _resolve_ref(defn, "undefined_conditions.2").startswith("拒答条件「")
    assert defn.undefined_conditions[2].reason.split("；")[0] in _resolve_ref(
        defn, "undefined_conditions.2"
    )
    # 解不开的原样返回 —— 不编一个好看的说法，否则指错了也看不出来。
    assert _resolve_ref(defn, "something.unknown") == "something.unknown"


def test_公式换不动时返回None而不是给半中文半代码(defn):
    """换了一半的公式比原样更难读，还会让人以为剩下那半是特意保留的。"""
    assert _formula_in_chinese(defn) == "(销售费用 + 管理费用 + 财务费用) / 营业收入"

    # 去掉字段的中文行项目名之后，就换不动了 —— 此时必须是 None。
    for sf in defn.source_fields:
        sf.line_item = None
    assert _formula_in_chinese(defn) is None


def test_二十份定义全部渲染得出来不抛异常():
    """视图要能用在全部定义上，不是只在挑出来的两份上好看。"""
    paths = [p for p in sorted((REPO / "metrics").glob("*.yaml")) if not p.name.startswith("_")]
    assert len(paths) == 20
    for p in paths:
        out = render_explanation(load_definition(p))
        assert "这是什么" in out and "什么时候不给答案" in out
        # dataclass 的 repr 漏进输出过一次，锁住它。
        assert "StandardBasis(" not in out


def test_共享注册表不是定义_explain必须拒绝而不是渲染空壳(capsys):
    """`_flags.yaml` 是标记注册表，不是指标定义。

    2026-09-04 实测：`explain _flags` **退出 0**，渲染出一份每节都空的「定义」——
    名称栏带着 `.yaml` 后缀、版本栏是 `None`、六个小节全空。
    `definition.iter_definition_paths` 早写明「下划线开头的不是定义」，
    而 `_cmd_explain` 自己拼路径绕开了那条规则，于是同一个目录两个入口读法不一致。

    这正是本仓反复记的那个形状：**一份看起来像答案、实际什么都没说的输出**。

    它会红的场景：有人再让 `_` 开头的文件走进 explain。
    反方向一并锁住 —— 「一律返回 2」也能满足前半条断言。
    """
    from semantic_layer.__main__ import main

    code = main(["explain", "_flags", "--metrics-dir", str(REPO / "metrics")])
    err = capsys.readouterr()
    assert code == 2
    assert err.out == ""
    assert "_flags" in err.err

    ok = main(["explain", "period_expense_ratio", "--metrics-dir", str(REPO / "metrics")])
    good = capsys.readouterr()
    assert ok == 0
    assert "期间费用率" in good.out


# ── 2026-09-04：`N-52` 第二轮 ──────────────────────────────────────
# 操作者读到 `系统实际执行： is.net_profit_attributable_to_parent - notes...`，
# 原话：「你给财务人看这种技术说辞吗，我辅修计算机肯定看得懂，正常财务呢？」
# ⇒ 表达式整体下沉到末尾附录，正文只用定义自己写的中文。**一个字都没删。**

APPENDIX_HEAD = "系统实际执行的表达式"


def _split(out: str) -> tuple[str, str]:
    """(正文, 附录)。附录必须存在 —— 它是可复核性的落点（`D-032`）。"""
    assert APPENDIX_HEAD in out, "附录不见了：两版并存是 D-032 的硬约束"
    body, _, appendix = out.partition(APPENDIX_HEAD)
    return body, appendix


def test_正文里不出现任何本定义声明过的字段标识符():
    """🔴 这条是第二轮的理由。

    正文归财务读者，字段 id 归附录。**判据取「本定义 `source_fields` 里
    有中文行项目名的那些 id」** —— 它们有中文可换，出现在正文就是渲染器的错。

    ⚠️ 故意不查「散文里所有形如 `ns.field` 的东西」：定义作者写「不得使用
    `bs.total_liabilities`」时，那个字段按定义**不在** `source_fields` 里，
    没有中文名可换。给它编一个，读者就没法发现禁的到底是哪一个（见 `_prose` docstring）。

    🔴 **2026-09-05 起这条在当前语料上是「预防性」的，不再是「证明性」的。**
    `N-58` 按 (b) 落地之后，20 份定义的散文里**一个字段 id 都不剩**（实测 0 处）——
    于是把 `_prose` 的字段替换整个拿掉，这条**照样绿**。
    实测过：改散文之前拿掉它这条会红，改之后不会。

    ⇒ **它现在守的是「将来有人往散文里写字段 id」**，不是「`_prose` 会不会替换」。
    后者由 `test_prose确实会把声明过的字段id换成中文` 独立守着 ——
    那条不依赖语料恰好含不含字段 id。
    **不许把这条读成「`_prose` 工作正常」的证据**（`L-32` 的同一条道理：
    一个说不出它什么时候会红的断言，要么删掉，要么另给它一条真会红的）。
    """
    paths = [q for q in sorted((REPO / "metrics").glob("*.yaml")) if not q.name.startswith("_")]
    assert len(paths) == 20
    checked = 0
    for q in paths:
        d = load_definition(q)
        body, _ = _split(render_explanation(d))
        mapped = [sf.id for sf in d.source_fields if sf.id and sf.line_item]
        assert mapped, f"{q.stem}：应当有带中文名的字段"
        for fid in mapped:
            assert fid not in body, f"{q.stem} 正文里漏出了字段标识符：{fid}"
            checked += 1
    # 只跑夹具一份会漏掉 `_prose` 那一半：`period_expense_ratio` 的散文里
    # 恰好没有可映射的字段 id，于是把 `_prose` 整个拿掉它也不会红。
    assert checked >= 60, f"覆盖太薄，只查了 {checked} 个字段"


def test_正文里剩下的字段标识符有多少_这个数被钉住():
    """🟡 2026-09-05 独立复核：模块 docstring 的硬约束第 3 条写着
    「**正文里不出现字段标识符**」—— 这句话**不成立**。

    上面那条测试守的是更窄、也是真正成立的那句：**本定义声明过、有中文可换的**
    字段 id 不出现在正文。剩下的那一类（定义作者写「禁止取 X」，而 X 按定义
    不在 `source_fields` 里 ⇒ 没有中文名可换）**确实还在正文里**。

    **2026-09-05：操作者裁 `N-58` 选 (b)，9 份定义的散文改写完毕，残留归零。**
    改的只有给人读的散文，`version` / `formula` / `expr` / `trigger` / `source_fields[].id`
    一个字节没动（`D-034` 划的那条线，有 `test_definition_fingerprint.py` 机械守着）。

    ⇒ 这个数继续钉着，两个方向都要能红：
    · **变大** = 有人往散文里塞回了字段 id，或让 `_prose` 少替换了
    · **变小** = 已经到 0，不可能再小；真变了说明这条断言自己坏了

    ⚠️ 残留不为零时**必须**全部属于「换不动」那一类（定义刻意不声明、没有中文名），
    由下面的循环逐条 assert。数字只是让文档里的说法有一个会自己报警的锚（`N-35`）。
    """
    import re

    from semantic_layer import dsl

    ns = sorted(dsl.ROOT_NAMESPACES | dsl.INTRINSIC_NAMESPACES)
    pat = re.compile(r"(?:" + "|".join(ns) + r")\.[a-z0-9_]+")

    paths = [q for q in sorted((REPO / "metrics").glob("*.yaml")) if not q.name.startswith("_")]
    assert len(paths) == 20
    有残留的定义, 残留次数 = 0, 0
    for q in paths:
        d = load_definition(q)
        body, _ = _split(render_explanation(d))
        hits = pat.findall(body)
        if not hits:
            continue
        有残留的定义 += 1
        残留次数 += len(hits)
        declared = {sf.id for sf in d.source_fields if sf.id and sf.line_item}
        assert not (set(hits) & declared), (
            f"{q.stem}：残留里混进了本定义声明过、本可换中文的字段："
            f"{sorted(set(hits) & declared)}"
        )
    assert (有残留的定义, 残留次数) == (0, 0), (
        f"实测 {有残留的定义} 份定义 / {残留次数} 处残留，"
        "与 explain.py docstring、D-032 的 N-58 收口节、PROGRESS 里写的 0 对不上 —— "
        "要么把散文里的字段 id 换成中文，要么三处数字一起改"
    )


def test_prose确实会把声明过的字段id换成中文(tmp_path):
    """🔴 这条**不依赖 20 份语料恰好含不含字段 id**。

    `N-58` (b) 落地后，真实语料里一个字段 id 都不剩 ⇒ 语料级那条扫描
    变成了预防性的守门人，**证明不了 `_prose` 还在工作**。
    这条自己造一份含字段 id 的散文，直接验渲染器的契约。

    它会红的场景：有人拿掉 `_prose` 的字段替换那一半，
    或让 `render_explanation` 不再对散文调 `_prose`
    （走的是渲染出口，不是单元调用）。
    """
    fid = "bs.total_current_assets"
    src = (REPO / "metrics" / "current_ratio.yaml").read_text(encoding="utf-8")
    assert fid in src, "夹具定义没有这个字段，这条会空转"

    # 往第一条陷阱的散文里塞一个**本定义声明过**的字段 id。
    # 逐行改，不用带转义的字面量 —— 反斜杠经过多层会被吃掉（`N-38`）。
    out = []
    injected = False
    for i, line in enumerate(src.split(chr(10))):
        out.append(line)
        if not injected and line.strip() == "- text: >" and "common_pitfalls" in chr(10).join(src.split(chr(10))[:i]):
            out.append("      禁止把 " + fid + " 当成流动负债。")
            injected = True
    assert injected, "没找到可注入的陷阱条目，这条会空转"

    q = tmp_path / "current_ratio.yaml"
    with open(q, "w", encoding="utf-8", newline=chr(10)) as fh:
        fh.write(chr(10).join(out))

    d = load_definition(q)
    assert any(fid in p.text for p in d.common_pitfalls), "注入没进到定义里，这条会空转"

    body, appendix = _split(render_explanation(d))
    assert fid not in body, "正文里漏出了声明过的字段标识符"
    assert "「流动资产合计」" in body, "没换成定义自己写的中文行项目名"
    # 下沉 != 删除：机器那一版仍然在附录里
    assert fid in appendix


def test_公式与判据都不在正文而在附录里一个不少(defn):
    """下沉 ≠ 删除。删了就没法核对翻译对不对（`D-032` 继承的约束）。"""
    body, appendix = _split(render_explanation(defn))

    formula = " ".join(str(defn.formula).split())
    assert formula not in body
    assert formula in appendix

    for cond in defn.undefined_conditions:
        if cond.expr:
            assert cond.expr not in body
            assert cond.expr in appendix

    for f in defn.flags:
        if f.trigger:
            assert f.trigger not in body
            assert f.trigger in appendix


def test_可比性标记在正文里显示中文而拿不到中文时退回原名(defn):
    """`restated` 对财务读者没有指称；中文来自 `metrics/_flags.yaml`。

    拿不到就退回原名 —— **不编**。
    """
    desc = "比较期数值经追溯重述或会计政策变更调整，与原始披露数不一致"
    body, appendix = _split(render_explanation(defn, {"restated": desc}))
    assert desc in body
    assert "· restated" not in body
    # 附录里两者都要有：读者要能把中文和它实际的标记名对上
    assert "restated" in appendix

    bare, _ = _split(render_explanation(defn))
    assert "restated" in bare, "拿不到中文时必须退回原名，不能凭空造一个"


def test_prose换不动的原样留着不编(defn):
    """`_prose` 只用定义自己的词。没有映射就不动它。"""
    from semantic_layer.explain import _prose

    assert _prose(defn, "禁止取 bs.从来没声明过的字段") == "禁止取 bs.从来没声明过的字段"
    # schema 键名换成本视图的小节名 —— 读者手上只有这一页
    assert "undefined_conditions" not in _prose(defn, "按 undefined_conditions 拒答")
