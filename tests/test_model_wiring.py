"""`N-64` —— 把模型接进服务这条路径上的回归。

盯三件事，按重要性排：

1. **接上电之后，证据链还认不认得出模型碰过它。**
   全系统只有 `agent/intent.py` 一个位置允许 LLM 介入。介入这件事一旦在产物里
   看不见，`D-003` 就名存实亡 —— 复核者拿到的是一页看起来完全确定性的证据。
2. **边界没有被这次接线挪动。** 校验仍只在别名表那一处；`agent/` 仍不 import 客户端；
   服务给模型看的清单与用来校验的是同一张。
3. **接不通的时候说人话，且不泄密钥。**
"""

from __future__ import annotations

import ast
import io
import sys
import urllib.error
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from agent.answer import _A_BY_MODEL, answer_question, render_answer  # noqa: E402
from service import api  # noqa: E402
from service import model  # noqa: E402

MODEL_PY = REPO_ROOT / "src" / "service" / "model.py"


@pytest.fixture
def 干净环境(monkeypatch, tmp_path):
    """把三个环境变量与本机 dotenv 都挪开 —— 否则本机真配了密钥时结论会翻。"""
    for name in (model.KEY_ENV, model.BASE_ENV, model.NAME_ENV):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(model, "REPO_ROOT", tmp_path)
    return tmp_path


# ── 没配模型是正常状态，不是错误 ────────────────────────────────────────


def test_没配密钥就没有模型而不是报错(干净环境):
    """与 `FINAUDIT_API_TOKEN` **刻意不同**：那个没配会拒绝启动。

    区别在后果：忘了配令牌 ⇒ 一个完全敞开的服务；忘了配模型 ⇒ 认不出的说法照旧拒答。
    后者本来就是正确行为，不该把服务拦在门外。
    """
    assert model.provider_from_env() is None


def test_密钥从环境变量读得到并带上默认端点(干净环境, monkeypatch):
    monkeypatch.setenv(model.KEY_ENV, "sk-测试用的假密钥")
    p = model.provider_from_env()
    assert p is not None
    assert p.api_key == "sk-测试用的假密钥"
    assert p.base_url == model.DEFAULT_BASE
    assert p.name == model.DEFAULT_NAME


def test_端点与模型名可以换掉不用改代码(干净环境, monkeypatch):
    """换厂商是配置动作。写死一个厂商，换的时候就得改代码、重跑门禁、重建镜像。"""
    monkeypatch.setenv(model.KEY_ENV, "k")
    monkeypatch.setenv(model.BASE_ENV, "https://example.invalid/v1/")
    monkeypatch.setenv(model.NAME_ENV, "某个别的模型")
    p = model.provider_from_env()
    # 末尾斜杠要吃掉 —— 拼出 `//chat/completions` 的地址有些网关会 404
    assert p.base_url == "https://example.invalid/v1"
    assert p.name == "某个别的模型"


def test_密钥不写进可外传的那一份(干净环境, monkeypatch):
    monkeypatch.setenv(model.KEY_ENV, "sk-绝对不能出现在任何产物里")
    red = model.provider_from_env().redacted()
    assert "sk-绝对不能出现在任何产物里" not in repr(red)
    assert red["key_len"] == len("sk-绝对不能出现在任何产物里")


# ── 校验只该有一处 ──────────────────────────────────────────────────────


def test_ask不替别名表做校验(monkeypatch):
    """模型编一个表里没有的名字，`ask` **原样返回**，不在这里挡。

    挡在 `parse_intent` 那句 `guess in registry.by_alias`。
    两处各写一遍，两处就会慢慢长得不一样，而那时没人知道以哪一处为准。
    """
    monkeypatch.setattr(model, "_post", lambda *a, **k: "根本不存在的指标名")
    p = model.Provider(base_url="x", name="y", api_key="z")
    assert model.ask(p, ["毛利率"], "问题") == "根本不存在的指标名"


def test_模型说不知道时给的是空串(monkeypatch):
    monkeypatch.setattr(model, "_post", lambda *a, **k: "  " + model.NONE_TOKEN + " ")
    p = model.Provider(base_url="x", name="y", api_key="z")
    assert model.ask(p, ["毛利率"], "问题") == ""


def test_提示词里把候选别名整张列出去(monkeypatch):
    """列不全，模型就会被要求去挑一条它没见过的东西。"""
    捕获 = {}

    def 假发送(provider, system, user):
        捕获["system"] = system
        捕获["user"] = user
        return model.NONE_TOKEN

    monkeypatch.setattr(model, "_post", 假发送)
    别名 = ["毛利率", "资产负债率", "ROA"]
    model.ask(model.Provider(base_url="x", name="y", api_key="z"), 别名, "题面")
    for a in 别名:
        assert a in 捕获["system"], "候选 " + a + " 没进提示词"
    assert 捕获["user"] == "题面"


# ── 接不通的时候 ────────────────────────────────────────────────────────


def test_没问上时退回离线态而不是抛出去(monkeypatch):
    def 炸(*a, **k):
        raise model.ModelUnavailable("网络没通")

    monkeypatch.setattr(model, "ask", 炸)
    asker = model.Asker(model.Provider(base_url="x", name="y", api_key="z"), ["毛利率"])
    assert asker("随便问") == ""  # 空串 ⇒ parse_intent 跳过 ⇒ 拒答
    assert asker.consulted is True
    assert asker.error == "网络没通"


def test_错误信息里不出现密钥也不出现响应体(monkeypatch):
    """响应体可能回显请求，而请求里有整张别名表和用户的问题；错误信息是要给调用方看的。"""
    密钥 = "sk-这个字符串一旦出现在错误里就是泄漏"
    响应体 = "这段是上游回显的请求内容"

    def 假urlopen(req, timeout=None):
        raise urllib.error.HTTPError(
            req.full_url, 401, "Unauthorized", {}, io.BytesIO(响应体.encode("utf-8"))
        )

    monkeypatch.setattr(model.urllib.request, "urlopen", 假urlopen)
    p = model.Provider(base_url="https://example.invalid", name="m", api_key=密钥)
    with pytest.raises(model.ModelUnavailable) as e:
        model._post(p, "system", "user")
    assert 密钥 not in str(e.value)
    assert 响应体 not in str(e.value)
    assert "401" in str(e.value)


# ── 证据链认得出模型碰过它 ──────────────────────────────────────────────


@pytest.fixture
def registry():
    from semantic_layer.resolve import Registry

    return Registry.load(REPO_ROOT / "metrics")


@pytest.fixture
def source():
    from agent.answer import FixtureSource

    return FixtureSource(REPO_ROOT / "eval" / "frozen-01" / "fixtures" / "synthetic-01.yaml")


def test_模型归一出来的指标名要进证据链并印在正文(registry, source):
    """🔴 本文件最要紧的一条。

    把 `base["metric_resolved_by"] = ...` 那一行删掉，这条立刻红 ——
    而删掉之后系统**照样答得出数**，只是那一页不再说「这个指标名是模型给的」。
    那正是 `D-003` 要防的那种「看起来完全正常」的产物。
    """
    a = answer_question(
        "华鑫科技（900001）2023 年的毛利水平是多少？",
        registry,
        source=source,
        ask_model=lambda q: "毛利率",
    )
    assert not a.refused, a.refusal
    assert a.evidence["metric_resolved_by"] == "model"
    assert a.evidence["matched_alias"] == "毛利率"

    page = render_answer(a, registry.resolve(a.metric_id))
    assert _A_BY_MODEL in page
    assert "毛利率" in page
    # 附录那一份**每页都印** —— 缺一行是最容易被读漏的信号
    assert "指标名怎么定下来的" in page


def test_查表查到的时候正文不出现模型那一节(registry, source):
    """反面。少了它，上一条可以靠「这一节永远都印」蒙混过关。"""
    a = answer_question(
        "华鑫科技（900001）2023 年的毛利率是多少？", registry, source=source, ask_model=None
    )
    assert not a.refused
    assert a.evidence["metric_resolved_by"] == "alias_table"
    page = render_answer(a, registry.resolve(a.metric_id))
    assert _A_BY_MODEL not in page
    assert "指标名怎么定下来的" in page


def test_模型只能从别名表里挑挑不中照样拒答(registry, source):
    """提示词不是安全边界。模型回一个表里没有的名字，结果必须是拒答。"""
    a = answer_question(
        "华鑫科技（900001）2023 年的毛利水平是多少？",
        registry,
        source=source,
        ask_model=lambda q: "我编的一个指标",
    )
    assert a.refused
    assert a.refusal["code"] == "METRIC_NOT_DEFINED"


def test_近似命中时根本不问模型(registry, source):
    """🔴 这条挡的是一次**实测出来的**危险，不是假想的。

    2026-09-07 直接问 `deepseek-chat`「600519 2023 年的净资产收益率」，
    它回的是「加权平均净资产收益率」—— 而净资产收益率还有全面摊薄口径，
    在两者之间选一个是**口径判断**，正是 `intent.py` 抬头写明「不该由匹配算法替人做」的那件事。

    ⚠️ **别名表挡不住它**：`加权平均净资产收益率` 本身就是一条合法别名，
    `guess in registry.by_alias` 会放行。唯一挡住它的是**顺序** ——
    近似命中判据在问模型之前就返回了拒答。把这两步换个位置，
    系统就会开始替人做口径判断，而且**答得出一个数**。
    """
    问过 = []

    def 记下来再答(q):
        问过.append(q)
        return "加权平均净资产收益率"

    a = answer_question(
        "华鑫科技（900001）2023 年的净资产收益率是多少？",
        registry,
        source=source,
        ask_model=记下来再答,
    )
    assert a.refused
    assert a.refusal["code"] == "METRIC_NOT_DEFINED"
    assert 问过 == [], "近似命中的题面被送去问模型了 —— 顺序被换过"


# ── 服务组装处 ──────────────────────────────────────────────────────────


def test_服务给模型看的清单与用来校验的是同一张():
    api._aliases.cache_clear()
    assert set(api._aliases()) == set(api._registry().by_alias)


def test_没配模型时响应里不多一句话(monkeypatch):
    monkeypatch.setattr(api, "_provider", lambda: None)
    code, body = api.answer_endpoint({"question": "600519 2023 年的资产负债率是多少"})
    assert code == 200
    assert "model_note" not in body


def test_配了模型但没接通要在响应里说明(monkeypatch):
    """「本来就没配」与「配了、这次没接通」会给出**一模一样的拒答**。

    不说这一句，同一个问题两次不同结果就无从解释。
    """
    monkeypatch.setattr(
        api, "_provider", lambda: model.Provider(base_url="x", name="y", api_key="z")
    )

    def 炸(*a, **k):
        raise model.ModelUnavailable("HTTP 503")

    monkeypatch.setattr(model, "ask", 炸)
    code, body = api.answer_endpoint({"question": "600519 2023 年的毛利水平是多少"})
    assert code == 200
    assert "HTTP 503" in body.get("model_note", "")
    # ⚠️ **不进证据页**：那一页讲的是「这次回答的依据」，运行状况不是依据。
    assert body["model_note"] not in body["page"]


def test_模型接通了就不多那句话(monkeypatch):
    monkeypatch.setattr(
        api, "_provider", lambda: model.Provider(base_url="x", name="y", api_key="z")
    )
    monkeypatch.setattr(model, "ask", lambda p, aliases, q: "毛利率")
    code, body = api.answer_endpoint({"question": "600519 2023 年的毛利水平是多少"})
    assert code == 200
    assert "model_note" not in body


# ── 零新增依赖 ──────────────────────────────────────────────────────────


def test_模型接线只用标准库():
    """`Dockerfile` 抬头声称「服务端第三方闭包实测只有 PyYAML 一个」，
    而 `D-014` 的**零 AGPL** 论证正建立在那句话上。接一个模型进来不能让它变假。
    """
    树 = ast.parse(MODEL_PY.read_text(encoding="utf-8"))
    顶层 = set()
    for node in ast.walk(树):
        if isinstance(node, ast.Import):
            顶层.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            顶层.add(node.module.split(".")[0])
    第三方 = 顶层 - set(sys.stdlib_module_names) - {"service", "agent", "semantic_layer"}
    assert 第三方 == set(), "模型接线引进了第三方包：" + str(sorted(第三方))
