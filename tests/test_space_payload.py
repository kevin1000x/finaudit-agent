"""`scripts/build_space_payload.py` 的回归。

这道扫描保护的是一个**不可逆**的动作：往一个 public 仓库推东西。
所以本文件的每一条都带负控制 —— 把该被抓的东西真种进去，看它红。
只断言「干净的载荷能过」是不够的：一个什么都不查的扫描器也能通过那条。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build_space_payload as bsp  # noqa: E402


@pytest.fixture
def 载荷(tmp_path):
    """按真仓库拼一份出来。**每条负控制都在它上面动手脚。**"""
    dest = tmp_path / "payload"
    bsp.compose(dest)
    return dest


# ── 清单只有一份 ────────────────────────────────────────────────────────


def test_目录清单现读自Dockerfile而不是另抄一份():
    """在脚本里另维护一份清单，就有了第二份真相。

    `N-42` 那个形态（一道闸的作用集 ≠ 它自称管住的集合）在本仓出现过四次，
    这条把「清单只有一份」钉死：改 `Dockerfile` 的 COPY，这里立刻跟着变。
    """
    读到的 = bsp.copy_targets()
    行 = [
        l.split()[1].rstrip("/")
        for l in (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8").splitlines()
        if l.startswith("COPY ") and len(l.split()) >= 3
    ]
    assert 读到的 == 行 and 读到的, "COPY 清单没有现读"


def test_改了Dockerfile的COPY载荷跟着变(tmp_path):
    """负控制：给一个假 Dockerfile 少写一行，载荷里就该少那一块。"""
    假仓 = tmp_path / "repo"
    (假仓 / "a").mkdir(parents=True)
    (假仓 / "b").mkdir()
    (假仓 / "a" / "x.txt").write_text("x", encoding="utf-8")
    (假仓 / "b" / "y.txt").write_text("y", encoding="utf-8")

    (假仓 / "Dockerfile").write_text("COPY a/ /app/a/\nCOPY b/ /app/b/\n", encoding="utf-8")
    两块 = bsp.compose(tmp_path / "out1", repo_root=假仓)
    assert {str(p).replace("\\", "/") for p in 两块} == {"a/x.txt", "b/y.txt"}

    (假仓 / "Dockerfile").write_text("COPY a/ /app/a/\n", encoding="utf-8")
    一块 = bsp.compose(tmp_path / "out2", repo_root=假仓)
    assert {str(p).replace("\\", "/") for p in 一块} == {"a/x.txt"}


# ── 层级是承重的 ────────────────────────────────────────────────────────


def test_真仓库拼出来的载荷层级正确(载荷):
    assert bsp.check_shape(载荷) == []


def test_塌掉src那一层就要报红(载荷):
    """🔴 负控制。2026-09-08 真拼错过一次。

    `service/api.py` 从自己的模块路径推数据根，`src/` 那一层塌掉之后
    数据根指到别处 —— **不报错**，只是覆盖面全 0、每个问题都拒答。
    一个「服务活着只是没数据」的现场，比崩溃难查得多。
    """
    # 把 `src/` 的顶层子目录整体挪上一层，再删掉 `src/` —— 这就是当时拼错的样子
    for child in list((载荷 / "src").iterdir()):
        child.rename(载荷 / child.name)
    (载荷 / "src").rmdir()
    problems = bsp.check_shape(载荷)
    assert problems, "层级塌了却没报"
    assert any("src/service/api.py" in p for p in problems)


# ── 七类清扫，每条都种一次 ──────────────────────────────────────────────


def test_干净的载荷扫不出东西(载荷):
    assert bsp.sweep(载荷) == []


def test_种一个密钥进去要报红(载荷):
    (载荷 / "src" / "service" / "泄漏.py").write_text(
        "KEY = " + repr("sk-" + "a" * 32), encoding="utf-8"
    )
    assert any("[密钥形状]" in f for f in bsp.sweep(载荷))


def test_种一个口令赋值进去要报红(载荷):
    (载荷 / "src" / "service" / "泄漏.py").write_text(
        'password = "hunter2hunter2"', encoding="utf-8"
    )
    assert any("[口令赋值]" in f for f in bsp.sweep(载荷))


def test_种一个本机用户名进去要报红(载荷):
    (载荷 / "src" / "service" / "泄漏.py").write_text(
        "# " + str(Path.home()), encoding="utf-8"
    )
    assert any("[本机用户名]" in f for f in bsp.sweep(载荷))


def test_讲规则的那条注释不算泄漏(载荷):
    """反面：`extractor/export.py` 的注释里写着 `file://C:/Users/.../`。

    那是在讲那条规则本身，路径是省略号，没有用户名。按字面量 `C:/Users` 查
    会把它误报掉，按**用户名**查才分得开 —— 而误报多了，扫描结果就没人看了。
    """
    出处 = 载荷 / "src" / "extractor" / "export.py"
    assert 出处.is_file()
    assert "C:/Users/" in 出处.read_text(encoding="utf-8"), "前提变了，这条测试要重写"
    assert bsp.sweep(载荷) == []


def test_种一个构建残留进去要报红(载荷):
    """`.dockerignore` 里写着 `*.egg-info/` —— 那管的是镜像，不管公开仓库。"""
    d = 载荷 / "src" / "假包.egg-info"
    d.mkdir()
    (d / "PKG-INFO").write_text("Name: x", encoding="utf-8")
    assert any("[构建残留]" in f for f in bsp.sweep(载荷))


def test_种一个邮箱进去要报红(载荷):
    # ⚠️ 地址是**拼出来的**，不是字面量。仓库级扫描（`T-01-16` 的 `CONTACT_PATTERN`）
    #    不区分「使用」与「提及」—— 而它那样是对的。与其让它为这一条开一个例外，
    #    不如让**本仓库里根本不存在一个完整的邮箱字面量**。
    #    落到载荷里的那份是完整的，所以这条断言仍然是实的。
    假地址 = "someone" + "@" + "realdomain" + ".cn"
    (载荷 / "src" / "service" / "泄漏.py").write_text(
        "# 联系 " + 假地址, encoding="utf-8"
    )
    发现 = bsp.sweep(载荷)
    assert any("[邮箱]" in f for f in 发现), 发现


def test_种一个控制字符进去要报红(载荷):
    (载荷 / "src" / "service" / "泄漏.py").write_text(
        "x = 1" + chr(12), encoding="utf-8"
    )
    assert any("[控制字符]" in f for f in bsp.sweep(载荷))


def test_把source_url改成file协议要报红(载荷):
    """`file://` 会把操作者的目录结构写进一个**公开**仓库。"""
    目标 = next((载荷 / "data").rglob("*.yaml"))
    文本 = 目标.read_text(encoding="utf-8")
    assert "source_url: null" in 文本, "前提变了，这条测试要重写"
    目标.write_text(
        文本.replace("source_url: null", "source_url: file:///D:/somewhere/x.pdf"),
        encoding="utf-8",
    )
    assert any("[source_url 非 http]" in f for f in bsp.sweep(载荷))


def test_真仓库当前推得出去(载荷):
    """把三件事合起来断言一次：层级、清扫、以及**载荷不是空的**。

    少了最后一句，一个 compose 什么都没拷的实现也能让上面每一条变绿。
    """
    assert bsp.check_shape(载荷) == []
    assert bsp.sweep(载荷) == []
    assert len(list(载荷.rglob("*.py"))) > 20


# --------------------------------------------------------------------------
# `N-88`：第一个位置参数是输出目录，所以不认的选项必须当场拒绝
# --------------------------------------------------------------------------


def test_传一个选项当输出目录必须拒绝且一个字节都不写(tmp_path, monkeypatch, capsys):
    """🔴 造回归：这件事 2026-09-11 真的发生过。

    `python scripts/build_space_payload.py --help` 当时把一整份
    58 文件 / 830 KB 的载荷写进了一个名叫 `--help` 的目录，**一声不吭**，
    还被下一条提交带进了仓库（已删，`494d101`）。
    这里把判据钉死：退 2、**且 cwd 下一个新目录都不许出现**。
    """
    monkeypatch.chdir(tmp_path)
    之前 = set(p.name for p in tmp_path.iterdir())

    assert bsp.main(["build_space_payload.py", "--help"]) == 0  # 它是正当请求
    assert bsp.main(["build_space_payload.py", "--推一下"]) == 2
    assert bsp.main(["build_space_payload.py", "-o"]) == 2
    assert bsp.main(["build_space_payload.py"]) == 2
    assert bsp.main(["build_space_payload.py", "a", "b"]) == 2

    之后 = set(p.name for p in tmp_path.iterdir())
    assert 之后 == 之前, f"什么都不该写，却多出了 {之后 - 之前}"
    assert "--help" not in 之后

    说了用法 = capsys.readouterr()
    assert "用法" in 说了用法.out + 说了用法.err


def test_用法行只有一份():
    """用法行从模块 docstring 现读，不另抄 —— 抄一份就有了第二份真相。"""
    assert bsp.USAGE in bsp.__doc__
