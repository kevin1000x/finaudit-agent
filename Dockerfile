# 问答服务的容器定义（`N-63` 裁定 (a)：按请求触发、能缩到零的托管）。
#
# ## 它为什么长这么小
#
# 服务端运行时的第三方闭包**实测只有 PyYAML 一个**：
#
#     python -c "import service.api as a; a.answer_endpoint({'question': '...'})"
#     ⇒ 加载的第三方顶层包 = ['yaml']
#
# `pdfplumber` 从没被加载 —— `extractor.pipeline` 里那句 `import pdfplumber`
# 在函数体内，而服务只走「读已落盘的抽取结果 + 算术」这条路，不解析 PDF。
# ⇒ 镜像里不装 pdfplumber，也就不需要它那一串原生依赖。
#
# 🔴 **零 AGPL**（`D-014`）：闭包里只有 PyYAML（MIT）。这不是靠许可证扫描
# 「碰巧没命中」，是靠**闭包本来就只有一个包**。
#
# ## 无状态（`D-021` 豁免三的两句判据）
#
# ① 有没有进程在没人请求时运行？—— 平台缩到零时容器不存在。
# ② 把存储全部清空会不会永久丢东西？—— 镜像里全是只读的公开数据，
#    容器不写盘、不记日志（`log_message` 是空的），删掉重建得到同一份。
#
# ## 构建与运行
#
#     docker build -t finaudit-service .
#     docker run -e FINAUDIT_API_TOKEN=... -e PORT=8080 -p 8080:8080 finaudit-service
#
# 托管平台注入 `$PORT`；`HOST` 默认 `0.0.0.0`（见下），而绑非回环地址时
# **没有令牌会拒绝启动** —— 忘了配令牌的后果是服务起不来，不是服务敞开着。

FROM python:3.13-slim

# PyYAML 是唯一的运行时第三方依赖。**不装 pdfplumber**，理由见抬头。
RUN pip install --no-cache-dir "pyyaml>=6.0.3"

WORKDIR /app

# 只拷服务真正读的东西。
#   src/                        代码
#   metrics/                    口径定义（注册表启动时加载）
#   data/extracted/             真实年报抽取结果（只有人工核对过的字段）
#   eval/frozen-01/fixtures/    合成夹具 —— 页面上**标成合成**，用来展示陷阱处理
# ⚠️ `data/raw/`（年报 PDF）**不拷**：几百 MB，而且服务不解析 PDF。
#    `.dockerignore` 里也挡了一道 —— 两处都写，因为这两处都可能被人改。
COPY src/ /app/src/
COPY metrics/ /app/metrics/
COPY data/extracted/ /app/data/extracted/
COPY eval/frozen-01/fixtures/ /app/eval/frozen-01/fixtures/

ENV PYTHONPATH=/app/src \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8080

# 不用 root 跑。这个进程不需要写任何东西。
RUN useradd --create-home --uid 10001 app && chown -R app:app /app
USER app

EXPOSE 8080
CMD ["python", "-m", "service.api"]
