# deepseek-harness `docs/` 契约文档续读

> 读取日期：2026-08-19（第 1–3 节）／ 2026-08-21（第 4–10 节）
> 语料：`<scratchpad>\deepseek-harness\docs\`（只读英文 `*.md`，跳过 `*.zh.md` / `*.i18n.yaml`）
> 前序：`references\deepseek-harness-deep-read-part1..7.md`（事件与持久化契约、`PreToolDecision`、`vendor/cordis`、postmortem、tools/subagent）
> 本轮目标：`architecture.md` / `module-graph.md` / `api-gateway.md` / `config-catalog.md` / `capability-seams.md` / `persistence-catalog.md` / `user\` + 补充篇

## 阅读清单与诚实标注

| 文档 | 行数 | 标注 | 说明 |
|---|---|---|---|
| `architecture.md` | 129 | **全文** | 逐行读完 |
| `module-graph.md` | 1638 | **部分** | L1–7 散文全读；L8–1416 的 mermaid 与 L1418–1638 的 219 行依赖表**未逐行读**，改用脚本统计（49 subgraph / 1089 边 / 219 包 / invariants 入度 218 出度 0），首尾各抽读约 50 行 |
| `api-gateway.md` | 164 | **全文** | 逐行读完 |
| `config-catalog.md` | 3151 | **部分** | L1–14 全读；105 个 `##` 标题索引全扫；抽读 L169–207 / 433–470 / 806–824 / 1432–1466 / 1818–1838 / 1942–1966 / 2222–2249 / 2765–2801 / 2817–2848 / 3024–3030 / 3090–3120 / 3130–3151；全文 grep 校验/求值关键词。**未读约 2500 行逐包 Config 粘贴** |
| `capability-seams.md` | 471 | **全文** | 8–410 为生成的 mermaid 图（扫结构）；412–471 表格逐行读 |
| `persistence-catalog.md` | 944 | **部分** | L1–10 散文 + L12–93 envelope 全读；68 个标题索引全扫；抽读 L536–562 / 566–603 / 607–666 / 745–818。**未读其余约 33 个事件类型的逐条 payload** |
| `user/index.md` | 11 | **全文** | 只是一个 meta refresh 重定向到 quickstart |
| `user/guide/index.md` | 30 | **全文** | Web UI 上手四步 |
| `user/guide/providers.md` | 98 | **全文** | 见 7.3：「配置是声明不是检查」、fallback vs override |
| `user/guide/python-sdk.md` | 104 | **全文** | 最小组合的属性表；`danger-full-access` 的使用告诫 |
| `user/develop/basic/index.md` | 144 | **全文** | plugin 三种形态、`ctx.effect` 自动回收 |
| `user/develop/basic/config.md` | 106 | **全文** | 见 7.2：可配置性判据 + schema/DI 的校验分工 |
| `user/develop/basic/tool.md` | 52 | **全文** | `defineTool` 的 parameters/output/render/execute |
| `user/develop/basic/publish.md` | 183 | **全文** | 见 7.4/7.9：bundle vs profile、层叠顺序、`!!js` 求值时机 |
| `user/develop/framework/index.md` | 137 | **全文** | 见 7.6：Fiber 状态机与 disposer 顺序的诚实标注 |
| `user/develop/framework/events.md` | 143 | **全文** | 见 7.7：emit/bail/serial/waterfall 四模式 |
| `user/develop/framework/service.md` | 148 | **全文** | 见 7.8：`isolate` 让同一个 ctx 键有多份实例 |
| `user/develop/practice/index.md` | 155 | **全文** | 见 7.1：**「不要预先拆分」**、三角色依赖方向 |
| `user/develop/practice/llm-adapter.md` | 188 | **全文** | 见 7.5：不许静默降级三连；封闭动词/开放名词 |
| `glossary.md` | 45 | **全文** | 见 8.1：一概念一术语 + `agent-scope` 的可见性判据 |
| `defensive-patterns.md` | 33 | **全文** | 见 8.2：7 条真实 bug 类，与本项目 `rules/failure-modes.md` 同构 |
| `graph-atlas.md` | 24 | **全文** | 见 8.3：每张图自报 generated/hybrid/curated 维护模式 |
| `rescope.md` | 53 | **全文** | 见 8.4：改名脚本的四能力 + 「不动什么」六条 |

> 表格在阅读推进时就地更新。**「待填」= 尚未读，不得当作读过。**

> **2026-08-21 语料修复记录**：本轮开工时发现 scratchpad 里的 clone 已被部分清空——
> `docs/` 下只剩 `user/develop/**` 的 9 份英文 md，顶层 `architecture.md` / `config-catalog.md` 等全部消失，
> `.git/HEAD`、`.git/config`、`.git/index` 也不见了（`find .git -maxdepth 1` 只返回目录，无文件），
> 但 `.git/objects/pack/*` 与 `.git/logs/refs/heads/master` 幸存。
> 用 master 的 reflog 拿到 commit `47f943859bef60e4160492346772ded9b24f765a`，重建最小 `.git`
> （HEAD + refs/heads/master + config，objects 直接复制）后 `git archive HEAD docs` 还原出 110 份英文 md。
> **还原后 23 份目标文档的行数与上表逐一吻合**（129 / 164 / 471 / 3151 / 1638 / 944 / 45 / 33 / 24 / 53 / 11 / 30 / 98 / 104 / 144 / 106 / 52 / 183 / 137 / 143 / 148 / 155 / 188），
> 证明与前几轮读的是同一个 commit。本轮引用的行号基于还原产物
> `<scratchpad-bf95a062>\dsh-recover\wt2\docs\`。

---

## 1. `architecture.md`（全文，129 行）

整篇是「地图 + 扩展点索引」，不是手册。九个小节：Cordis / Profiles 与 bundles / 核心包 / 事件 / 回合流 / 会话日志 / 能力接缝 / 新行为该放哪 / cookbook 索引。

### 1.1 「没有特权内核」是明写的原则

> `architecture.md:13` — There is no privileged core to patch: you extend dsh by mounting a plugin beside the others, and registrations are effects that unwind when their plugin unloads.

`architecture.md:11` 把这条推到极端：**模型适配器、工具注册表、会话日志、agent loop 本身都是 plugin**，「所以每一部分都可以从配置替换」。

这是对本项目问题 1 的直接回应素材：harness 不需要事先划「内核 vs 壳」，因为它把边界问题**转成了另一个问题**——不是「谁在内核里」，而是「谁拥有哪个 `ctx.X` 键」。见 1.3。

### 1.2 三层组合：profile → bundle → patch

- `architecture.md:19` **profile** = 存放在 Harness home 的具名组合，列出它叠哪些 bundle，装哪些树外 plugin，并保存用户自己的 `cordis.patch.yml`。`web` 与 `headless` 作为模板发布。
- `architecture.md:21` **bundle** = Cordis config 行 + 它挂载的代码的分发格式，「so whatever it inserts stays patchable by the layers above it」（它插进去的东西仍然可被上层 patch）。
- `architecture.md:23` 两者都在自己的 `package.json` 的 `dsh` 字段里自述：`dsh.profile` 列 bundle，`dsh.bundle` 指向 patch 文件。
- `architecture.md:27` **叠加顺序**（从空 entry 列表开始）：profile 列出的每个 bundle（按序）→ profile 的 `cordis.patch.yml` → home 级的 → `--patch` overlay。**patch 按 row id 定位，整体替换该行的 config，或插入新行。**
- `architecture.md:32` 自查命令：`dsh --profile web --dump-config`，「Any row it prints can be replaced by a patch of your own」（`:35`）。

对本项目的价值：这是一套**「默认配置可被逐行覆盖且能 dump 出真实生效值」**的机制。见末尾迁移点 M-2。

### 1.3 所有权表：一个包拥有一个 `ctx` 键

`architecture.md:43-51` 是一张三列表：Package / Owns / `ctx` key。

| Package | Owns | `ctx` key |
|---|---|---|
| `core/session` | append-only `SessionEvent` 日志与内存 store | `ctx.sessions` |
| `core/system-prompt` | prompt 段落与工具 schema 装配 | `ctx.systemPrompt` |
| `core/tools` | scoped 工具注册表与守卫执行管线 | `ctx.tools` |
| `core/agent` | `Agent` 接口、活动注册表、`agent/*` 事件 | `ctx.agents` |
| `core/agent-loop` | 实现该接口的默认驱动 | `ctx.agentLoop` |
| `core/scope` | 每 agent 的 scoped 注册原语 | **library, no key** |
| `llm/llm` | 消息与流词汇 + 适配器接缝 | `ctx.llm` |

关键细节：`core/scope` 一栏明写 **「library, no key」**——即「它是库，不拥有事实」。**「拥有哪个事实」= 「拥有哪个 `ctx` 键」，纯库不进这个命名空间。** 这是一条可直接搬运的判据。

注意 `core/agent`（接口 + 注册表）与 `core/agent-loop`（默认驱动）**被拆成两个包两个键**：接口的拥有者和默认实现的拥有者不是同一个包。

### 1.4 事件域的选择是「大多数改动的第一个决策」

> `architecture.md:55` — Events are the extension points, and picking the right domain is the first decision in most changes.

三域判据（`:57-59`）：
- **Session events**：追加进日志并经 `session/event` 广播的**耐久事实**。判据 = 「这个事实必须活过一次 reload」。
- **Agent events**（`agent/*`）：携带活的 `Agent`（inbox / step / status / request / validation / continuation）。判据 = 「观察或拦截飞行中的工作」。
- **Capability events**（`fs/*`、`tools/*`、`telemetry/*`）：**在不 import loop 的前提下**把策略与适配器挂到接缝上。

第三条尤其重要：**capability event 的存在理由就是「解耦，使策略不必依赖主循环」**。

### 1.5 回合流的 ASCII 契约（`:67-82`）

```text
turn/start
  claim next-step input plus one queued message
  assemble prompt sections + tool schemas
  -> agent/pre-step                   reject | enter(messages)
     reject, or a first enter rewritten empty -> close the turn with no step
     step/start
     append entered messages as user/message
     derive model history from the log
     agent/request -> llm/stream -> assistant/chunk* -> assistant/message
     tool/call* -> tools/pre-execute -> tools/execute -> tools/post-execute -> tool/result*
     step/end
     tools owe another request, or next-step input arrived -> claim -> next step
  -> agent/turn-stopping
turn/end
```

- `:65` 定义：**step** = 一次模型请求加上它调用的工具；**turn** = 零个或多个 step，「在第一份输入被 claim 前打开，在没有任何欠账时关闭」。
- `:84` 明确哪些是耐久会话事件：`turn/*`、`step/*`、`user/message`、`assistant/*`、`tool/*`；其余是活的扩展点。
- `:84` **waterfall vs serial 的显式区分**：`agent/pre-step`、`agent/request`、`llm/stream`、三个 `tools/*` 是 **waterfall**，监听器必须调用 `next()` 才能委托下去；`agent/turn-stopping` 是 **serial，没有 `next()`**。
- `:88` 「被拒绝或空的首次 claim **仍然关闭一个耗费了零个 step 的耐久 turn**，因此日志记录下了这次尝试」——**拒绝也要留痕**。

### 1.6 「模型可见即已记录」（对本项目最有价值的一条）

> `architecture.md:96` — **Model-visible means logged.** Anything that reaches a model request must be reconstructable from the log, and a runtime invariant asserts it. This is why a new model-visible input requires a new session event: extend `SessionEventMap` and render from the log.

三层含义：
1. 是**不变量**，不是习惯——`a runtime invariant asserts it`（运行时断言，不是文档口号）。
2. 它反向约束了扩展方式：**想加一种新的模型可见输入，就必须加一个新的 session event 类型**，没有旁路。
3. `:94` 补充：`deriveMessages()` 从日志投影出模型历史，原始 `assistant/chunk` 事件保留 replay 与 UI 保真度；fork / resume / transcript / telemetry / persistence **全部从这一条流派生**。

对 finaudit-agent：把 "Model-visible means logged" 换成 **"Answer-visible means evidenced"**——任何进入最终答案的数字/口径/条文，必须能从证据链事件流重建，且由运行时不变量断言。这与 D-003（证据链是第一类产物）同构，但 harness 多给了两样东西：**运行时断言** + **「新增可见输入 = 新增事件类型」的扩展纪律**。

### 1.7 接缝的三角色定义（`:100`）

> A **seam** is a swappable capability with three roles: a **Service Definition** declaring the interface, a **Service Provider** implementing it, and a **Consumer** using it, commonly a model-facing tool. A package may combine roles, but one role alone is not a seam; adding a capability means designing all three.

「一个包可以兼任多个角色，但**单独一个角色不构成接缝**；加一个能力意味着把三个角色都设计出来。」

`:102` 给了接缝的收益证明：文件系统与子进程 provider 共享同一个执行世界，所以把它们指向远端沙箱就**同时**搬动了 Bash、PTY、LSP，**不需要 fork 任何 provider**。

### 1.8 「新行为放哪」映射表（`:108-127`）

20 行的 Goal → Mechanism 表。**这张表本身就是边界文档**：不写「模块在哪个目录」，而写「你的目标对应哪个已文档化的扩展点」。开头一句是硬规则：

> `architecture.md:106` — New behavior attaches to a documented extension point. **Changing the loop itself updates this map.**

即：**改动主循环必须同步更新这张表**——把「架构文档过期」变成了一条可执行的门禁条件。

摘几条与本项目同构的：
- Add a model-facing capability → 注册到 `ctx.tools`；**它的 schema 自动加入 prompt 装配**（`:111`）
- Give one session a different capability set → 组合一个 agent preset；**那里的 service 行需要一个 `isolate` realm**（`:112`）
- Add durable session state → 扩展 `SessionEventMap`；从日志渲染与重放（`:123`）
- Scope a registration to one agent → 用那个 agent 的 `agent.ctx`（`:127`）

---

## 2. `api-gateway.md`（全文，164 行）

Typert API Gateway 的现状参考。主题是「Host 侧业务服务如何声明 unary Remote 方法 → 构建期生成 Host/Client 契约 → 调用复用同一条 Connection RPC 与 `/api` 路由」。

### 2.1 选择性暴露是默认的（白名单，不是黑名单）

> `api-gateway.md:9` — Business services use `@Remote` or `@RemoteScope` to select the methods exposed to the Client. **Unmarked methods do not enter the generated Client types or runtime contributions and cannot be called through `ctx.remote`.**

没标注 = 既不在生成的类型里，也不在运行时贡献里，**根本无法被调用**。不是「运行时拒绝」，是「压根不存在」。

### 2.2 复杂对象不过线：`TypertLookupMap` 身份映射

`api-gateway.md:11`：复杂 Host 对象不能直接跨线。业务包必须通过 `TypertLookupMap` 声明它们与一个**wire identity**的关联，并在运行时向 `ctx.typert.lookups` 注册一个默认解析 provider。

例子：Host 签名里名为 `agent` 的 `Agent` 参数 → 产生 `agentId` wire 字段 → Gateway 在调用业务方法**之前**把 id 解析回 Host 对象。

关键的所有权切分（`:11` 后半）：Host 组合可以用 `ctx.typert.lookups.configure()` **覆盖某个 lookup key 的解析策略**，而**不改变**参数名、wire 字段、或业务包拥有的规范类型符号。
→ **「策略」归组合层，「名字与类型」归业务包。** 这是一条干净的所有权切分。

### 2.3 校验发生在哪里：全部在网关边界，业务代码内零校验

> `api-gateway.md:125` — For every call, the Gateway resolves the descriptor and live service **from the current registries instead of caching business objects**. It requires the fields in `args` to match the descriptor exactly, validates wire values with codecs, resolves objects or receivers through registered lookup or Context providers, invokes the service method targeted by the binding, and **validates the return value**. A missing provider, unknown identity, binding mismatch, missing or extra argument, schema failure, or missing method **fails before entering or after leaving business code**.

这是对本项目问题 4 最直接的一段。要点拆开：
- **入参与返回值都校验**（不是只校验入口）。
- 失败点被明确定位为「**进入业务代码之前，或离开业务代码之后**」——业务代码内部不承担校验职责。
- **每次调用都重新解析 descriptor 与活服务，不缓存业务对象**——避免「校验过的旧对象被复用」。
- 「多一个参数」和「少一个参数」同等失败（`missing or extra argument`）——**exact match，不是 superset match**。

### 2.4 降级不得悄悄削弱校验（fail-closed）

> `api-gateway.md:129` — Unloading a Client contribution removes its descriptors and concrete methods together, aborts its in-flight calls, and makes stale method handles retained by external code reject further calls. **A strict endpoint withdrawn on the Host also does not degrade to SRC inference, preventing a hot unload from silently weakening validation.**

即：有一条弱模式（SRC fallback）存在，但**强模式撤下时不会自动落到弱模式**。这正是本项目在证据链上要的语义：抽取器失效时不允许「降级成功」。

补充 `:137`：SRC 只解决「从源码跑的 Host 进程的分发」；**Client 拒绝挂载缺少严格 codec 的 SRC descriptor**，它的类型/codec/注册值永远来自最近一次生成的 `lib/typert.remote-client.*` 产物。→ **弱模式的作用域被显式钉死在一侧**，不允许扩散。

### 2.5 严格分析的「拒绝清单」（`:117`）

Remote 必须是**公开、非静态、有具体实现的实例方法**。并且：
- 方法**不能是泛型**
- 参数必须是**必填的、命名的简单标识符**
- **不能**用解构、默认值、rest 参数、可选参数

理由是可推断的：这些语法特性都会让「wire 字段 ↔ 参数」的映射变得不唯一。**为了让映射可静态生成，主动砍掉了一整片语言表达力。**

对本项目的映射：报表行标签 → 字段 id 的映射表，同样应该**砍掉表达力换取可静态校验**（例如禁止正则回引用、禁止条件分支），而不是做成一个小语言。

### 2.6 边界一节是「反向定义」（`:158-164`）

`## Boundaries` 一整节写的是**这个协议不管什么**：

> `:160` — Remote handles only unary method calls with one request and one result. Session event streams, pagination, incremental reduce, projection, and entity substreams require a separate data protocol and registration model; even when they reuse the Connection, **they must not masquerade as Remote methods or enter invocation descriptors**.

「即使复用同一条 Connection，也不得伪装成 Remote 方法、不得进入调用 descriptor。」——**共享传输 ≠ 共享契约**。这条对本项目有用：PDF 抽取与语义层可以共享同一条证据事件流，但不得让抽取结果伪装成已核对的指标。

`:162` 给了分层顺序与物理位置：`remotes → gateway → connection → webserver`；BFF 与 Typert RPC 在 `packages/api`，Connection 在 `packages/client/connection`，WebServer 在 `packages/host/webserver`。没有 Remote descriptor 的端点由 `packages/host/apiproxy` 处理（**兜底层是显式的一个包**）。

`:164` 一条罕见的「已知代价」自白：

> Lookup policy is configured per key, so all `agent` or `session` parameters share the cold-resume behavior. **Accepting live objects only would require an explicit per-parameter or per-endpoint policy, which does not exist**; the business method must not guess whether the object came from restoration.

即：粒度选在 key 级而非参数级，代价是**所有同名参数共享同一套冷恢复行为**；文档不但承认，还补了一条给业务方的硬规则——**业务方法不准去猜这个对象是不是恢复来的**。

### 2.7 构建顺序被写成契约（`:97`、`:150-156`）

- Host lib 阶段先 `tsc -b tsconfig.host.json`，再 `tsdown --env.DSH_BUILD_FACE host`；Typert 生成器在这一趟 tsdown 中运行，**以 Host 聚合体作为唯一的 `ts.Program` 种子**。
- `:101` **`api-remotes` 是唯一一个有分裂 TypeScript face 的包**——文档把「唯一的例外」显式点名，其余每个包都只注册在一个聚合体里。
- `:150` 什么时候需要重新生成写得很死：**只改 Remote 方法实现体、不改契约 → 不需要重新生成**；增删装饰器、改导出名/命名空间/参数/返回值/lookup/Context/取消签名 → 必须按序重跑 `pnpm run build:lib`。
- `:156` **「干净的工作树不能跳过 Host 阶段」**、「只重编前端源码无法从 Host 装饰器推出新类型」——把「顺序依赖」写成了显式失败模式，而不是让人自己踩。

---

## 3. `capability-seams.md`（全文，471 行；其中 8-410 行是生成的 mermaid 图，逐行扫过但只记结构；412-471 的表格逐行读）

**这份文档是生成的**：`capability-seams.md:1-2` 头部注释 —— `Generated by scripts/gen-doc-graphs.ts - do not edit by hand. Run pnpm run gen-doc-graphs to regenerate.`

### 3.1 三分类：`core` / `seam` / `bundle`

> `capability-seams.md:6` — A service can be a **core spine service**, a **swappable capability seam**, or a **bundle/composition point**. The graph shows the package that owns the service declaration, known implementation packages, and packages that consume the service directly.

我对 414-471 行的表格做了角色计数（命令：`sed -n '414,471p' capability-seams.md | grep -o '| \`[a-z]*\` |' | sort | uniq -c`）：

| Role | 条数 |
|---|---|
| `core` | 29 |
| `seam` | 26 |
| `bundle` | **1** |
| （另有 4 条 owner 字段未加链接被计数器误捕：`apiproxy`×2 / `connection` / `hmr`） |

**`bundle` 只有一条，就是 `ctx.agentLoop`。** 这一条的 Note 值得全抄：

> `capability-seams.md:444` — `ctx.agentLoop` | `bundle` | `agent-loop` | - | `agent-spine-demo` | - | **The one concrete loop plugin; extension packages depend on dsh-agent events and services, not on this package.**

→ **这是 harness 对「内核与壳的边界」给出的实际答案**：它不去定义「内核」，而是给唯一的具体主循环打上 `bundle` 标签，并写死一条依赖规则——**扩展包依赖 `dsh-agent` 的事件与服务，不依赖这个包。** 内核的特权被降级成「一个组合点」。

### 3.2 表格的七列 = 一张所有权账本

`capability-seams.md:412` 表头：

```
| ctx key | Role | Owner | Implementations | Direct consumers | Companion plugins | Note |
```

- **Owner**（谁声明接口）与 **Implementations**（谁实现）是两列，绝不合并。
- **Direct consumers** 单独一列 —— 谁在直接吃这个服务是公开事实，不是「谁想 import 就 import」。
- **Companion plugins** 一列，全表只有一条非空：`ctx.fs` 的 `fs-observation-policy`（`:456`）。

维护模式明写在末尾：

> `capability-seams.md:471` — Maintenance mode: **hybrid**: services are discovered from Cordis declarations; interface/implementation/consumer roles are classified in `scripts/gen-doc-graphs.ts` **with a completeness guard**.

→ 「服务清单」从代码自动发现，「角色分类」是人写在生成脚本里的**显式判断**，并有 completeness guard 防漏。**边界分类是人的决定，但它被固化在一个会失败的脚本里，不是固化在文档里。**

### 3.3 对本项目问题 4（校验在哪个边界）最直接的三条 Note

1. **同一策略源被两条执行路径共读，防止两边收敛到不同的根**
   > `:452` `ctx.sandboxPolicy` | `core` — The one home for the deployment default mode + workspace root; only the sandboxed executor and provider read the service (the tool layers use the pure `sandbox/mode` fold it also exports). **Both enforcing families read it so bash and fs cannot confine to different roots.**

   这条同时回答了问题 2 和问题 4：**策略数据放在唯一一个 home**，两个 enforcement 家族（bash 与 fs）读同一份，杜绝「两处各自实现、口径漂移」。工具层不读服务，只读它导出的**纯 fold**（`sandbox/mode`）——**读的人拿到的是投影，不是可变服务句柄。**

2. **缺省即失败，而不是缺省即放行**
   > `:453` `ctx.approval` | `seam` — One-shot permission decisions dispatched over the `approval/request` waterfall; answerers are listeners (the ACP bridge for its own agents), **absence fails closed to `unavailable`**.

3. **接缝不留协议逃生舱**
   > `:467` `ctx.lsp` | `seam` — Provider registration and selection plus normalized query execution over **exactly four operations**; **the seam offers no protocol escape hatch, so a backend translates into the normalized request and result.**

   这是本项目问题 3（封闭节点集）的最佳同构证据：**接口只暴露恰好四个操作，不提供 raw-protocol 通道，代价由 backend 承担（backend 必须翻译进归一化的请求/结果）。**

### 3.4 「刻意不做注册表」也被记录下来

> `:466` `ctx.workflowEngine` | `seam` — **One engine per context, as in bash, with no named-provider registry**; the general workflow and fixed Ralph consumers start runs whose `agent()` calls fan out through `ctx.subagents`.

对照 `ctx.web`（`:463`，多 provider 注册进一个 seam）与 `ctx.subagents`（`:461`，六个 provider）：**同一份文档里既有「多 provider 注册表」也有「刻意单实例、无注册表」，并把后者写成一句显式的取舍**（"as in bash"，即与 shell 一致）。

### 3.5 其他值得记的 Note

- `:424` `ctx.credentials`：**Configuration carries references to secrets; providers own the values.** Consumers resolve per operation, **so a rotated credential reaches the very next request**。→ 配置里只放引用，值归 provider；「每次操作现取」换来「轮换立即生效」。
- `:426` `ctx.storage`：backends 并列注册在名字下；**data forms（domain first）挂在 hub 上**，把类型化操作翻译成不透明的 KV-unit 原语。→ 两层：hub（不透明原语）+ form（类型化）。
- `:432` `ctx.sessionTitle`：Owns **the deterministic fallback**, latest-title fold, and **the sole optional asynchronous provider registration**。→ 确定性兜底归接缝自己所有，异步 provider 是可选且唯一的。
- `:440` `ctx.sessionProjectionCache`：throttled + **turn/end/detach mandatory points**，冷读阶梯 = 缓存行 + 持久化尾部重放，**so listings never load full logs**。
- `:437` `ctx.agentPresets`：挂载 preset 时**拒绝一个永不激活的行、或一个发布进 root service realm 的行**。→ 组合期就拒绝「写了但不会生效」的配置（与 postmortem 0002 同源）。

---

## 4. `config-catalog.md`（**部分**，3151 行）

### 实际读了哪些行（其余未读）

| 范围 | 内容 |
|---|---|
| L1–L14 | 生成头 + 全文契约说明（**全读**） |
| 全部 `##` 标题行 | 105 个 `## \`@deepseek-ai/dsh-*\`` 条目 + 3 个尾部分类节，**标题索引全扫**（`grep -n '^#\{1,3\} '`） |
| L169–207 | `dsh-agent-presets` |
| L433–470 | `dsh-code-runtime-worker-thread` |
| L806–824 | `dsh-invariants` |
| L1432–1466 | `dsh-repeat-tool-reminder` |
| L1818–1838 | `dsh-settings-file` |
| L1942–1966 | `dsh-storage-domain` |
| L2222–2249 | `dsh-system-prompt` |
| L2765–2801 | `dsh-tools` |
| L2817–2848 | `dsh-user-approval` |
| L3024–3030 / L3090–3120 / L3130–3151 | 三个尾部分类节（Loadable-with-no-config / Seam packages / Library packages） |
| 全文 | 用 grep 扫过 `reject|at load|fail(s|ed)? (closed|loud|at)|validat|invariant|fail-closed`（命中 40+ 行，见下），以及 `eval / parser / expression / ast / jsonpath / template / schemastery` |

**未读**：其余约 95 个包条目的正文（约 2500 行）。这些是逐包的 `Config` 接口粘贴，结构同质；我抽了 10 个覆盖不同子系统（preset / code-runtime / 诊断 / 守卫 / 设置 / 存储 / prompt / 工具注册表 / 审批）作为样本，不代表其余没有反例。

### 4.1 这份「配置目录」本身是生成的，而且有一条防漏的交叉校验

> `config-catalog.md:8` — This file is GENERATED from source (`scripts/gen-config-catalog.ts`) and verified fresh by `pnpm run verify-config-catalog` (part of `doc-sync`). … The generator also cross-checks the runtime schemastery schema against the pasted declaration — **every schema-validated key, nested keys included, must be locatable on the declared config type — so the paste cannot hide a loader-accepted field.**

三层机制，值得整套搬：
1. **文档从源码生成**（不是人写的清单）。
2. **有一条独立的 verify 命令**（`verify-config-catalog`，挂在 `doc-sync` 下），不是靠人记得重跑生成器。
3. **生成器自己做双向核对**：运行时 schema 的每一个 key（含嵌套）必须能在粘贴出来的声明类型上定位到。这句话的目的写得很直白——**「粘贴不能藏掉一个 loader 会接受的字段」**。也就是说，它防的是「文档看起来完整、实际运行时还接受别的字段」这种漂移。

`:6` 还有一条同源的判据：**「运行时 schema 故意排除掉的字段 = 一个 runtime-only seam（它自己的 JSDoc 会这么说），不可从 `cordis.yml` 设置」**。→ 「不可配置」不是靠省略表达的，是靠**字段自己的 JSDoc 明写**表达的。

### 4.2 对问题 2 的直接回答：**按包拆分，不是单一全局文件**

整份目录的组织单位就是**包**：一个 `##` 一个 npm 包，每个包粘贴它自己的 `Config` 接口。没有一张跨包的全局键表。

- `:10` **`Requires:` 行**列出该插件 `inject` 的 service key，「its `cordis.yml` tree must also load providers for those services」。→ 依赖是**每包自述**的，不是集中维护的依赖图。
- 跨包引用被显式表达为链接而非复制：`:293` 那种 `Depends on: [AgentLoopConfig](#...) · [GoalDomainConfig](#...) · …` 行，把「这个包的 config 里嵌了别的包的 config 类型」摊开写。
- `:6` 明确了这份目录的轴：「This is the **deployment**-axis reference」，并与另外两条轴分工——插件作者看 `subsystems/*` 的 Cordis API 区，模型可见的工具 schema 看 `tool-catalog.md`。**三份文档，三个读者，三条轴。**

**`config-catalog.md` 记录的代价**（问题 2 问的「记了什么代价」）——我在读过的部分里找到三处，都是**关于粒度的自白**，不是关于「拆分本身」的抱怨：

1. **路由粒度：域级，不是全局**
   > `:1946` `dsh-storage-domain` — Which backend serves which domain is decided here, **not globally on the hub**: `backend` is the default route and `routes` overrides it per domain name. **A route naming an unregistered backend fails loud at `open` with `backend-not-found`.**

   并且 `backend` 字段是 **required**，理由写在字段注释里：**「Required: there is no universally correct medium.」**——拒绝给一个默认值，因为不存在普适正确的默认。这比「给个默认再让人踩坑」诚实。

2. **拒绝隐藏的硬编码**
   > `:435` `dsh-code-runtime-worker-thread` — Plugin config: **every execution cap, changeable from `cordis.yml` (no hardcoded tunables).**

   四个上限（busy-time / wall-clock / output bytes / heap MiB）全部可配。其中 `maxWallMs` 的注释写了一条**边界值的载入期拒绝**：至多 `2_147_483_647`，「a longer value is **rejected at load** because `setTimeout` would clamp it to 1 ms」——**把宿主 API 的一个坑显式抬到配置校验层**，而不是让它在运行时变成一个荒谬的 1ms 超时。

3. **`settings-file` 与 `cordis.yml` 是两套东西**（`:1820`）：`dsh-settings-file` 的 config 只有 `path` / `dshHome` / `watch` / `debounceMs` —— 即「设置文档在哪、怎么热重载」。**它自己不定义任何设置项的语义。** → 用户设置（`settings.yaml`）与部署装配（`cordis.yml`）被拆成两层，插件配置层只负责「指到那个文件」。

### 4.3 对问题 4 的直接回答：**校验分布在多个边界，且每个边界的失败语义被逐条命名**

读过的部分里，至少四个不同边界各自承担校验：

| 边界 | 例子 | 明写的失败语义 |
|---|---|---|
| **生成期（构建/doc-sync）** | `verify-config-catalog` | schema key 必须能在声明类型上定位，否则 doc-sync 失败（`:8`） |
| **载入期（schema）** | 「validated by the same-named schemastery schema」（`:422`、`:847`、`:1436`） | 类型/形状不符即拒 |
| **载入期（`apply` 里的额外检查）** | `dsh-repeat-tool-reminder`（`:1436`） | 「**plus the load-time checks in `apply`（misconfiguration fails loud: an empty `thresholds` list, a non-integer, a value below 2, or a duplicate throws at plugin load, never a silent fall-back）**」 |
| **装配期 / 挂载期** | `dsh-system-prompt`（`:2237`） | 「**Invalid fields fail at load and unknown names fail at assembly**」——同一个字段 `toolOrder`，两类错误落在两个不同的时刻 |
| **首次使用期** | `dsh-storage-domain`（`:1948`） | 路由指向未注册 backend → `open` 时 `backend-not-found` |
| **每次调用期** | `dsh-agent-presets`（`:176`） | 「Preset id … **Missing at mount time fails loud**」 |

三条可搬走的原则：

1. **「schema 校验」与「语义校验」被显式分成两段，而且文档会写「plus」。** schemastery 管形状，`apply` 里的 load-time check 管语义（非空、整数、≥2、不重复）。文档不写「有校验」，写的是**具体拒哪四种输入**。
2. **`never a silent fall-back` 是明写的**（`:1437`）。配置错了不许悄悄用默认值顶上。
3. **「模式匹配不到东西」不算配置错误。** 同一段（`:1439`）：`include`/`exclude` 是**调用时**对工具名的 `*` 通配谓词，**不是对注册表条目的引用**——「a pattern matching no currently registered tool is valid（`exclude: [mcp_*]` must stay legal in a deployment that loads no MCP tools）」。→ **区分「引用一个不存在的实体」（错误）与「一个当前不匹配任何东西的谓词」（合法）**。这条在本项目做「指标口径过滤器 / 科目名匹配规则」时会直接用上：写了个匹配不到任何科目的规则不该当成配置错误，但引用一个不存在的口径 id 必须报错。

### 4.4 对问题 1 的补充：三个尾部分类节就是一张边界表

`config-catalog.md` 末尾把所有包分成三类（每类都给出包名 + 源码路径）：

1. **`## Loadable plugins with no config`**（`:3024`）——「These load from a `cordis.yml` entry with no `config:` block; they declare no configuration API.」包含 `dsh-agent`、`dsh-api-gateway`、`dsh-api-remotes`、`dsh-workspace` 等。→ **「可装载但无配置」是一个被命名的类别**，不是「忘了写文档」。
2. **`## Seam packages (not directly loadable)`**（`:3094`）——「Abstract service classes — a deployment loads a concrete implementation package instead.」15 个：`attachment` / `code-runtime` / `compaction` / `credentials` / `fs` / `host-directory-picker` / `jobs` / `sandbox` / `session-persistence` / `session-query` / `settings` / `shell` / `spill` / `subprocess` / `workflow`。每个都标注了它导出的抽象类名（`abstract FileSystem`、`abstract ShellExecutor`…）。
3. **`## Library packages (no plugin entry)`**（`:3114`）——「Imported as libraries by other packages; **a `cordis.yml` cannot load them.**」`dsh-scope`、`dsh-home-paths`、`dsh-timeout`、`dsh-typert-protocol` 等。

→ 与 `architecture.md:73`「`core/scope` = library, no key」完全对上：**`dsh-scope` 在这里被归入第三类。** 两份文档、两条独立路径、同一个判断，**没有矛盾**。这说明「谁拥有事实 / 谁只是库」这条线在这个项目里是被真正维护的，不是写一次就过期的。

**可搬运的判据（三分法）**：
- 有 `ctx` 键 + 有 config → 可配置的能力提供方
- 有 `ctx` 键 + 无 config → 装配点（无旋钮）
- 抽象类、不可装载 → 接缝定义
- 无插件入口、只能 import → 纯库，**不进 `ctx` 命名空间，也不进部署配置**

### 4.5 对问题 3 的第一批证据（详见第 9 节「问题 3」）

- `:543` `dsh-code-runtime-worker-thread` 有 `computeMs` 字段，注释写「**Maximum synchronous VM evaluation time in milliseconds**」——存在一个 VM。
- `:2771` `dsh-tools` 的 `mode: 'native' | 'code' | 'both'`：**`code` 模式下模型只被允许调用一个工具 `run_code`**，其余工具变成「生成的 SDK」里的函数。「Code modes require a `ctx.codeRuntime` whose `language` has a registered SDK renderer (TypeScript or Python) and **fail prompt assembly when it is absent or has no renderer**.」→ 缺渲染器不是降级，是**装配失败**。


---

## 5. `module-graph.md`（**部分**，1638 行）

### 实际读了哪些行

| 范围 | 内容 |
|---|---|
| L1–7 | 生成头 + 唯一一段散文（**全读**） |
| L8–1416 | 一整块 mermaid `flowchart TD`（**未逐行读**）。用脚本统计了结构：49 个 `subgraph`、1089 条 `-->` 边 |
| L1416–1638 | 依赖表（219 行）。**未逐行读**，但整列做了脚本统计与两次交叉核对，抽读了首尾各 ~50 行 |

**未读**：mermaid 的 1089 条边逐条、表格 219 行逐行。下面所有数字都是脚本统计，命令写在括号里。

### 5.1 这份文档只有一句散文，但那句话定义了「依赖」的口径

> `module-graph.md:6` — Inter-package dependencies among the `@deepseek-ai/dsh-*` harness packages, **derived from each package's `peerDependencies` (the canonical runtime-dependency signal)** and grouped by the `packages/<group>/<pkg>` hierarchy. An edge `a --> b` means package `a` depends on package `b`.

关键在括号里那句：**它明确声明了「哪一个字段才算运行时依赖的权威信号」= `peerDependencies`**，而不是 `dependencies`。这是一条口径声明——图不是「我们认为的依赖」，是「从一个指定字段机械推出来的依赖」。**口径先写死，图再生成。** 与本项目「指标口径必须可复核」是同一个动作。

### 5.2 规模数字（全部为脚本统计，非目测）

| 指标 | 值 | 命令 |
|---|---|---|
| 包总数 | **219** | `sed -n '1418,1638p' module-graph.md \| grep -c '^\| \['` |
| 分组（`packages/<group>`）数 | **49** | mermaid 的 subgraph 与表格的 group 列各取 unique 后 `diff` → **IDENTICAL** |
| 依赖边总数 | **1089** | `sed -n '8,1416p' module-graph.md \| grep -c -- '-->'` |
| 最大的一组 | `client`（39 个包） | group 列 `sort \| uniq -c` |

49 个分组，前几名：`client` 39 / `session` 13 / `subagent` 11 / `shell` 9 / `host` 8 / `core` 8 / `util` 7 / `fs` 7。
→ **`core` 只有 8 个包，前端 `client` 有 39 个。** 「核心」在包数量上是少数派，这与 `architecture.md:13`「没有特权内核」在结构上是一致的。

### 5.3 全图唯一的根：`invariants`（这是本轮最强的一条发现）

用两条互相独立的路径核对，结论一致：

| 检查 | 命令 | 结果 |
|---|---|---|
| 表格里依赖列为空（`—`）的行 | `... \| grep -cx '— \|'` | **1**，就是 `invariants` 自己 |
| 表格里依赖列提到 `invariants` 的行 | 剥掉前两列后 `grep -c 'invariants'` | **218** |
| mermaid 里指向 `pkg_invariants` 的边 | `grep -c -- '--> pkg_invariants'` | **218** |
| mermaid 里从 `pkg_invariants` 出发的边 | `grep -cE '^\s*pkg_invariants -->'` | **0** |

即：**219 个包里，218 个依赖 `@deepseek-ai/dsh-invariants`，而它自己零依赖。** 它占了全部 1089 条边的 20%。

这个包是什么？看 `config-catalog.md:806-820`——它的 config 只有三个字段：
```ts
readonly enabled?: boolean          // 全局开关，默认 true
readonly package_allowlist?: string[]  // 允许哪些包（正则源，空 = 全允许）
readonly package_blocklist?: string[]  // allowlist 匹配之后再排除
```
即「**运行时不变量断言**」的选择开关。

**这就是 `architecture.md:96`「Model-visible means logged … a runtime invariant asserts it」那句话的物理形态**：不变量断言不是散落在各处的 `assert()`，而是**一个被全仓库 218 个包依赖的独立包**，且它的启停可以按包名正则从 `cordis.yml` 配置。

三条推论，对 finaudit-agent 直接可用：
1. **「不变量检查」被当成一个基础设施包对待，而不是每个模块自己写 assert。** 依赖方向是「所有人 → invariants」，且 invariants 不依赖任何人——它不可能反向耦合到业务。
2. **可按包名正则关掉**，说明它默认是开的、有开销的、并且预期会在生产里保留而不是只在测试里跑。
3. 它排在整张依赖表的**第一行**（表按拓扑深度排序），`util/*` 与 `core/scope` 紧随其后。→ **本项目的证据链断言器应当放在同样的位置：零依赖、被所有人依赖、可配置粒度到模块。**

### 5.4 对问题 1 的补充：分组是「按能力域」，不是「按层」

49 个 group 名字全是能力域：`fs` / `shell` / `llm` / `session` / `sandbox` / `subagent` / `workflow` / `web` / `lsp` / `mcp` / `storage` / `credentials` / `preset` / `guard` / `interaction` / `feedback` / `identity` / `schedule` / `runtime-diagnostics` / `test-support` / `examples` / `extensions` …

没有 `layers/`、`common/`、`shared/`、`utils`（只有 `util`，且里面 7 个包各自单一职责：`atomic-write` / `brand` / `home-paths` / `launch-environment` / `native-command` / `output-retention` / `timeout`——**没有一个叫 `helpers` 或 `misc`**）。

同一个能力域内部再按「抽象 / 实现 / 工具」拆包，命名规律非常稳定：

| 模式 | 例子 |
|---|---|
| `<域>` = 抽象接缝 | `fs`、`shell`、`sandbox`、`storage`、`compaction`、`workflow`、`subprocess`、`spill` |
| `<域>-<实现>` = 具体 provider | `fs-local`、`fs-sandbox`、`fs-e2b`、`bash-local`、`bash-sandbox`、`pwsh-local`、`pwsh-sandbox`、`storage-json`、`storage-sqlite` |
| `tool-<域>` = 模型可见工具 | `tool-fs`、`tool-bash`、`tool-lsp`、`tool-web`、`tool-skill`、`tool-workflow`、`tool-subagent` |
| `<域>-policy` = 策略 | `sandbox-policy`、`spill-policy`、`fs-observation-policy`、`timeout-policy`、`session-checkpoint-policy` |
| `client-ui-<特性>` = 前端切片 | 20+ 个，每个特性一个包 |

→ **`architecture.md:100` 的「接缝三角色」在包名层面被机械地编码出来了**：Service Definition = `<域>`，Provider = `<域>-<实现>`，Consumer = `tool-<域>`。三个角色三个包，读包名就能判断它是哪个角色。这比任何架构文档都难过期。

**并且「策略」被单独拆成第四类包（`*-policy`）**——策略既不是接口也不是实现也不是消费者，它是挂在接缝上的旁路。这印证了 `architecture.md:59` 的 capability event 判据（「在不 import loop 的前提下把策略挂到接缝上」）：策略要能单独装卸，就必须是单独的包。

### 5.5 一个没有答案的观察

表格是**拓扑排序**的（根在最上，叶在最下），最后几行全是 `client-ui-*` 与 `examples/*`。`agent-spine-demo`（一个 examples 包）依赖 22 个包，`client-ui-conversation` 依赖 19 个。
→ 依赖最重的不是「核心」，是**示例与前端**。这与 `capability-seams.md:444` 把 `ctx.agentLoop` 标为 `bundle`（组合点）互相印证：**在这套架构里，「依赖很多东西」是组合层的特征，不是核心层的特征。核心的特征是「被很多东西依赖」。**


---

## 6. `persistence-catalog.md`（**部分**，944 行；与前几轮持久化契约重合处只记增量）

### 实际读了哪些行

| 范围 | 内容 |
|---|---|
| L1–10 | 生成头 + 全部散文（**全读**） |
| L12–93 | `## Event envelope` 整节，`SessionEventType` / `SurfaceEventType` / `SurfaceOp` / `SessionEvent` 四段声明（**全读**） |
| 全部 68 个 `###`/`####` 标题 | 24 个事件域 + 44 个事件类型，**索引全扫** |
| L536–562 | `request/context` · `request/header` |
| L566–603 | `sandbox/mode` · `schedule/change` |
| L607–666 | `session/end-seed` · `session/title` · `session/title-llm-request` |
| L745–818 | `tool/code-dispatch` · `tool/code-dispatch-start` · `tool/result` |

**未读**：其余约 33 个事件类型的正文（`agent/*` / `agent-preset/*` / `approval/*` / `assistant/*` / `command/*` / `compaction/*` / `feedback/*` / `goal/*` / `hook/*` / `llm/*` / `permission/*` / `plan/*` / `step/*` / `subagent/*` / `todo/*` / `tool-workflow/*` / `turn/*` / `user/*` / `web/*` 的逐条 payload）。

### 6.1 数字：**44 个事件类型，只有 3 个是 surface**

| 类别 | 数量 | 命令 |
|---|---|---|
| `— surface` | **3** | `grep -c ' — surface$'` |
| `— log-only` | **41** | `grep -c ' — log-only$'` |
| 事件域（`###`） | 24 | `grep -c '^### '` |

三个 surface 事件写死在类型里（`:19-22`）：
```ts
export type SurfaceEventType =
  | 'user/message'
  | 'assistant/message'
  | 'tool/result'
```

**93% 的日志事件不进模型上下文。** 这是本轮对本项目最有操作性的一条结构事实：**「留痕」与「喂给模型」被彻底分开，而且比例是 41:3。** 记录得多不等于上下文膨胀——`deriveMessages()` 只投影那 3 个。

对 finaudit-agent 的直接映射：证据链事件（用了哪张表、什么口径、哈希是多少）应当**全部是 log-only**，只有「答案文本」「引用片段」少数几类进模型可见面。写证据不占 token 预算，这条打消了「证据链会撑爆上下文」的顾虑。

### 6.2 增量之一：`ignorable` —— 前向兼容的默认是「拒绝」

envelope 里这个字段的 JSDoc 是整份文档写得最狠的一段（`:65-73`）：

> Marks an event a reader may safely skip when it does not recognize `type`. **Absent means required: a reader meeting an unrecognized type without this marker MUST refuse to reconstruct the session instead of silently dropping the event**, because an unrecognized required event may change how the rest of the log is interpreted. A writer sets `true` only on purely informational records whose loss cannot affect reconstruction; **defaulting to required means a forgotten marker over-refuses (an inconvenience) rather than silently resuming a gutted session.**

四层设计，每层都可以直接搬：
1. **默认值选在「拒绝」一侧**：字段缺失 = 必需 = 不认识就整个拒绝重建。
2. **理由被写出来**：不认识的必需事件**可能改变后面整条日志的解释方式**——不是「少一条记录」，是「后面全错」。
3. **明确谁能标 `true`**：只有「纯信息性、丢了不影响重建」的记录。
4. **对失败模式的取舍被明写**：忘记标记 → 过度拒绝（不便）；反过来 → 悄悄恢复一个被掏空的会话（灾难）。**「宁可过度拒绝」是被论证过的，不是保守习惯。**

→ 对本项目：证据链读取器遇到不认识的证据类型时，默认应当**拒绝出具答案**，而不是跳过那条继续算。这条与 D-003「给不出证据链视为失败，不视为降级成功」完全同向，但补上了 harness 才有的那一半——**怎么让「拒绝」成为字段缺省态，而不是靠人记得写 fail-closed 分支。**

### 6.3 增量之二：类型系统被用来禁止「非 surface 事件携带 surface 元数据」

`SessionEvent` 是一个映射类型加条件类型（`:52-88`）：

```ts
} & (K extends SurfaceEventType ? {
    sourceEventSeqs?: number[]
    surfaceOp?: SurfaceOp
  } : object)
```

JSDoc 明说（`:46-50`）：「Non-surface events (boundary markers, chunks, usage, errors) **never carry surface metadata — the compiler enforces this at `Session.append()` call sites**.」

并且强调这是**判别联合而非独立的 `type`/`data` 联合**（`:37`）：「A proper discriminated union over `type` … so `switch (event.type)` narrows `event.data` without casts.」

→ **一部分「校验」被前移到编译期，且是靠类型形状而不是靠运行时检查。** 这回答了问题 4 的一角：harness 的校验不只分布在运行时边界，还有一层在类型层——**能用类型排除的非法状态，就不写运行时校验。**

### 6.4 增量之三：`Session.append` 是一个真实的运行时校验闸门

两处独立提到它：
- `:10` — 「Every payload is **JSON-serializable (enforced at `Session.append`)**」
- `:800`（`tool/result`）— 「`meta` is opaque to the core … but MUST be JSON-serializable: **`Session.append` runtime-validates all event data with `isJsonValue`, so a non-serializable `meta` is rejected at the source**, and the durable log reproduces the identical card on replay.」

关键词是 **rejected at the source**：不可序列化的东西在**写入点**就被拒，不是等到落盘或重放时才炸。**「在写入点校验」= 日志里永远不会存在坏数据**，这比「读的时候小心处理」强一个数量级。

对应到 `tool/code-dispatch-start`（`:775`）还有一条同源设计：参数是「**normalized BEFORE dispatch, so this append can never fail on payload shape**」——**先归一化再派发，使得那次 append 在形状上不可能失败。** 顺序被反过来安排以消除一整类失败。

### 6.5 增量之四：`surfaceOp` 的 `replace` 与「被遮蔽者必须被引用」

`SurfaceOp`（`:33-42`）：
```ts
export type SurfaceOp =
  | 'append'
  | { op: 'replace'; start: number; end: number }
```
约束写在 JSDoc 里：`start`/`end` 都必须是当前 surface 里存在的节点；**「The node's `sourceEventSeqs` must include every shadowed surface node.」**

即：**压缩（compaction）可以替换一段历史，但替换者必须逐一列出它遮蔽了哪些 seq。** 追加式日志 + 显式遮蔽引用 = 既能压缩又不丢可追溯性。

`sourceEventSeqs` 本身的语义也很讲究（`:83`）：一个 `assistant/message` 可以携带**一个存在但为空的数组**表示「provider 流确实是空的」；**字段缺席**则表示「不记录是哪些事件产生了它」。→ **「空」与「未记录」被区分成两种状态**，没有用 `null` 含混过去。

对本项目：合并/汇总类的证据节点（例如「三年平均 ROA」）必须列出它引用的原始证据 seq；「引用了但结果为空」与「没记录引用关系」必须是两种不同的状态。

### 6.6 增量之五：三种「最新值」语义被显式命名

读过的部分里出现三种不同的 fold，且每种都在 JSDoc 里点名：
- `sandbox/mode`（`:571`）：「**The LAST such event is the session's override**」——latest-wins，且区分 `source: 'delegation'`（父会话种下的）与缺席（运行时切换）。
- `session/title`（`:642`）：「**Latest-wins** session title snapshot.」
- `request/header`（`:557`）：「**the latest snapshot reconstructs the request header**」，并且额外声明 `request/context`「**does not participate in request reconstruction or header equality**」——**明写哪条不参与重建**。

→ 三条都在说同一件事：**append-only 日志里，「当前值」是一个被命名的 fold，而不是隐含约定。** 而且会明写某个事件**不**参与某个 fold。本项目做「口径的当前生效版本」时应照抄这个写法。

### 6.7 增量之六：`session/end-seed` —— 一条承认自己无人保护的事件

`:607-631` 这条事件的 JSDoc 里有一句罕见的自白：

> `Session`'s constructor is the only legitimate writer. **The invariant companion deliberately constrains nothing here, so a plugin appending one would silently classify every live bracket before it as seed history.**

即：**「只有构造函数能写」这条规则没有被不变量强制，文档知道并写下了它的后果。** 结合 5.3 节发现的「218/219 个包依赖 invariants」，这说明 invariants 是**选择性覆盖**的，而不是全覆盖——**哪里没被覆盖，文档就在那里写明「这里没保护，后果是什么」。**

同一条还有第二句自白：「NOT a liveness signal about other writers — a concurrently live session holds its own boundary elsewhere, so **tolerating concurrent writers needs a signal beyond the log**.」→ **明说这个机制解决不了并发写。** 不假装通用。

### 6.8 增量之七：「日志事件不是 cordis 事件」

`:6` 括号里一句容易滑过去的话：

> the generated region of session.md (the live bus wiring — **a log event is NOT a cordis event; it reaches listeners via the single `session/event` emit**).

**两套事件系统被显式区分**：耐久日志事件（44 种）与活的 cordis 总线事件是两回事，前者只通过**一个** cordis 事件 `session/event` 到达监听者。
→ 这解释了 `architecture.md:57-59` 三类事件域的边界为什么能立得住：session event 根本不在总线的类型空间里，它是**一个** cordis 事件的载荷。**「44 种耐久事实」压缩成「1 个总线事件」，总线的类型面因此不随日志词汇增长而膨胀。**


---

## 7. `user\` 目录 13 篇（**全文**，合计 1499 行）

13 篇全部逐行读完：`index.md`(11) / `guide/index.md`(30) / `guide/providers.md`(98) / `guide/python-sdk.md`(104) / `develop/basic/index.md`(144) / `develop/basic/config.md`(106) / `develop/basic/tool.md`(52) / `develop/basic/publish.md`(183) / `develop/framework/index.md`(137) / `develop/framework/events.md`(143) / `develop/framework/service.md`(148) / `develop/practice/index.md`(155) / `develop/practice/llm-adapter.md`(188)。

这批是**面向外部作者的教程**，与前六节的生成式契约文档是两种文体。价值在于：**它把前面那些机械生成的表格背后的「原则」用人话写了出来**，而且写得比架构文档更硬。

### 7.1 对问题 1 的正面回答：**「不要预先拆分」是明写的设计点**

> `user/develop/practice/index.md:149` — **Do not split preemptively** — use separate packages only when the roles need to evolve independently. A simple tool plugin does not.

同页 `:9` 给了配套的判据：

> When a capability is general enough to need replaceable providers, such as Bash execution, Harness separates three roles… **Put the roles in separate packages when they need to evolve or be replaced independently; a package may otherwise own more than one role.** The complete capability is its seam. **No individual role is a seam.**

这就是本项目要找的那条「先落地、边界待定」原则的成熟版本，而且它比「先落地」更精确——它给的不是「以后再说」，而是**一条可判定的拆分触发条件**：

| | 判据 |
|---|---|
| **何时不拆** | 角色不需要独立演进 / 不需要被替换。「A simple tool plugin does not.」 |
| **何时拆** | 「need to evolve or be **replaced** independently」——注意是**替换**，不是「变复杂了」 |
| **拆成几份** | 三份：Service Definition / Service Provider / Consumer。不是两份，也不是按层数 |
| **一个包可以兼任** | 明写 "a package may otherwise own more than one role" |

配套的依赖方向也写死了（`:52-54`）：
- Provider → Definition
- Consumer → Definition
- **Provider 与 Consumer 互不依赖**

→ 这解释了为什么「先合后拆」在这套架构里是安全的：**拆分的边界早就由「三角色」定义好了，合并只是暂时把三个角色放在一个包里。** 拆的时候不需要重新想边界，只需要把已经分好的角色搬出去。

对 finaudit-agent 的直接用法：Phase 1 的语义层完全可以一个包写完，但**从第一天起就把「口径定义 / 口径实现 / 口径消费」在文件层面分开**，包边界留到真的需要换实现时再画。

同页 `:150-151` 还有两条：
- **「Service Definition 拥有 Request/Result 类型」**——类型的归属跟着接口走，不跟着实现走。
- > `:151` **Explicit > implicit** — resolve defaults in an explicit `resolve(request): Spec` step rather than hiding `?? default` expressions inside `run()`.

  即：**默认值必须在一个显式的 resolve 步骤里落定，不许散落在执行体里的 `?? 默认值`。** 这条对「口径默认值」尤其重要——审计场景下「这个数用了哪个默认口径」必须是一个可指认的步骤，不是一个藏在表达式里的 fallback。

### 7.2 对问题 2 的正面回答：**「两个部署可能想设成不同值的东西，必须是配置字段」**

> `user/develop/basic/config.md:80` — Harness requires **anything that two deployments may want to set differently to be a configuration field**.
>
> `:92` — **The test is whether `cordis.yml` can change the value without a code edit.**

这条给了一个**可执行的判定**，不是原则口号：拿一个常量问「换个部署会不会想改它」，会 → 它必须是配置字段；然后再问「改它要不要动代码」，要 → 没做到。

这与 `config-catalog.md:435` 的「every execution cap, changeable from `cordis.yml`（**no hardcoded tunables**）」是同一条规则的两端：教程写原则，生成的目录是它的执行证据。

**配置是「按域拆分」的第二个证据**：这条原则天然导致「每个包自带自己的 Config」，因为「哪些值该可配」只有包作者知道。没有全局配置文件的位置去放它们。

同页 `:94-96` 给了配套的失败纪律：

> ### Fail loudly on invalid configuration
> **Express self-contained constraints in the schema so invalid configuration fails while the plugin loads.** References to services or registered resources require dependency injection; the services tutorial introduces that contract.

**注意它划的那条线**（这是问题 4 的关键）：
- **自足的约束**（数值范围、枚举、必填、格式）→ 放进 schema，**载入期失败**。
- **引用服务或已注册资源的约束** → schema 管不了，必须走依赖注入。

即：**「能在不看别人的情况下判定的约束」和「必须看别人才能判定的约束」被分到两个不同的机制**。前者用声明式 schema 在载入期挡，后者用 DI 在依赖就绪期挡。这条判据非常干净，可以直接搬。

### 7.3 对问题 2 的补充：**「配置是一种声明，不是一种检查」被明写**

`user/guide/providers.md` 在讲模型的图像模态时写了一句罕见的自白（`:80`）：

> **Both fields state a claim about your endpoint rather than checking it.** A model that declares images its endpoint does not serve is not caught here; the provider rejects the request instead.

和它前面的理由（`:33`）：

> A model you enter by hand is treated as text-only until it says otherwise, **because nothing can ask an endpoint which modalities it accepts.**

三层都写清楚了：
1. **为什么不能自动检测**——协议里没有这个能力。
2. **所以默认值选在保守一侧**——手写的模型默认按纯文本处理，附图请求「**refused before it is sent, naming the model**」（发送前拒绝，并点名是哪个模型）。
3. **配置只是声明，错了在下游炸**——并且明说这里不负责抓。

`:67` 还区分了 fallback 与 override：

> `defaultInput` is **a fallback, not an override**, and defaults to `[text]`: on a catalog provider it answers only for models the catalog does not describe, **so it never removes images from a catalog model that has them.**

→ **兜底值不得反向削弱已知事实。** 这条在本项目做「行业默认口径 vs 公司实际披露口径」时是一模一样的问题：默认口径只能填补未知，不能覆盖已披露的。

`:78` 另有一条边界值的语义决定：「Every list must name at least one modality **except a model's own, where an empty list means the same as omitting it**. An unknown modality is refused wherever it is written.」→ **空列表在一个位置合法（等同省略）、在另一个位置非法**，且明写出来。

### 7.4 对问题 3 的核心证据：`!!js` —— 有「字符串当表达式求值」，是三方（Cordis）机制 + 本仓库扩展

三处独立出现，拼起来是完整图景：

1. **它长什么样**（`user/develop/practice/llm-adapter.md:131`）：
   ```yaml
   config:
     apiKey: !!js process.env.MY_API_KEY
   ```
2. **它在哪些字段生效 / 何时求值**（`user/develop/basic/publish.md:141-151`）：
   ```yaml
   - id: my-app
     name: '@example/my-app'
     inject: [myAppStartup]
     config:
       port: !!js ctx.myAppStartup.port ?? 8080
   ```
   > `:151` — On `--help`, the provider publishes no service, so those rows never activate. **Loader mounts the composition once, waits for each row's ordinary injections, and only then evaluates that row's `!!js` config against its injected context.**

   → **求值时机被写成契约**：挂载 → 等待注入就绪 → 才对该行的 `!!js` 求值。表达式能看见 `ctx`（它自己注入的那些服务）与 `process.env`。
3. **它的作用域边界，以及一次真实事故**（`cordis-tutorial/05-config.md:80`、`postmortem/0002`；这两份不在本轮清单内，我是 grep 命中后只读了命中行及其上下文）：
   > `cordis-tutorial/05-config.md:80` — `!!js` works only inside `config` and in an entry's `disabled` field. `disabled: !!js ...` evaluates against the loader context at every mount decision (**this repo's extension**)… the other metadata (`name`, `id`, `inject`, ...) stays static, where an expression is ordinary truthy data.

   > `postmortem/0002-js-expression-disabled-filesystem-tools.md:9` — The ACP example attempted to enable filesystem plugins conditionally with `disabled: !!js ...`, but **Cordis evaluates JavaScript expressions only inside plugin `config`. The raw expression object was truthy, so the filesystem stack was always disabled.**

**这是本轮找到的最重要的一条负面教训**，而且它被写成了 postmortem 的通用规则（`postmortem/0002:45`）：

> **A syntactically accepted configuration value is not necessarily evaluated at that location; document and verify exactly which fields are interpolated.**

即：`disabled: !!js <expr>` 在语法上被接受，但在**当时的 Cordis 里那个位置不求值**，于是那个表达式对象作为一个普通对象参与真值判断——**恒真**，文件系统栈永远被禁用。事故的第二段更糟：快照刷新把 `UNKNOWN_TOOL` 当成了新的期望输出。

→ 对应到本项目的 F-2（「只有真实字段能诚实触发时才声明 flag」）：**这是同一类错误在别人仓库里的实证版本**——「拿手边能求值的东西凑一个 trigger」和「在一个不求值的位置写表达式」是同构的，结果都是一条永远不会正确触发的假规则。harness 的修法值得抄：**加了 static-config guard 与 snapshot-result guard**（两道门禁，一道挡配置，一道挡「把错误结果录成期望值」）。

**封闭节点集的问题**：我在读过的 13 篇 `user/` 文档里**没有**找到对 `!!js` 表达式的语法子集限制、白名单节点集、或求值沙箱的描述。也就是说 **`!!js` 是完整的 JS 表达式求值，靠「只在 config 与 disabled 两个位置生效」来限制爆炸半径，而不是靠限制表达式本身。** 详见第 9 节「问题 3」的完整回答与 grep 记录。

### 7.5 对问题 4 的补充：教程层的「不许静默降级」三连

| 出处 | 规则 |
|---|---|
| `llm-adapter.md:113` | 「If the provider cannot honor a field, **throw `LlmError` with a stable code instead of silently dropping it**.」——不支持的字段必须抛，不许丢 |
| `llm-adapter.md:155` | 「The agent loop preserves the error and code for diagnostics and policy; **it does not convert an ordinary `Error` automatically**.」——不自动把普通 Error 升格成协议错误 |
| `llm-adapter.md:115` | 「**The service validates the aggregate and rejects unsupported explicit efforts before `stream()`**」——接缝在委托给 provider **之前**校验聚合体 |

第三条尤其对应问题 4：**校验发生在接缝边界、在委托之前**，与 `api-gateway.md:125`「fails before entering or after leaving business code」是同一个位置。

同段（`:115`）还有一条与问题 3 相关的反向选择：

> preserve the adapter's authoritative selectable list, including `off` when its upstream capability API returns it, **instead of promoting those values into a core enum**.

→ **不把 provider 的取值升格成核心枚举**：核心持有的是「不透明 id 的有序列表」，具体取值归 adapter。对照 `capability-seams.md:467` 的 `ctx.lsp`「exactly four operations, no protocol escape hatch」——**同一个仓库里，操作集是封闭的，取值集是开放的。** 封闭的是**动词**，开放的是**名词**。这是一条很精细的取舍，值得单独记下来。

### 7.6 生命周期：注册是 effect，卸载即回收（对本项目的门禁设计有用）

`framework/index.md:9-24` 的 Fiber 状态机：
```
PENDING → LOADING → ACTIVE
                 ↘ FAILED
ACTIVE → UNLOADING → DISPOSED
```
- `:38` **「If a required service disappears… the plugin unloads automatically (ACTIVE → DISPOSED) and loads again when the service returns.」** 依赖消失 → 依赖方自动卸载。`service.md:109` 给了理由：「**This prevents a plugin from calling a service that no longer exists.**」
- `:63` 一条容易忽略的诚实标注：「disposer invocation starts in reverse registration order, **but multiple async disposers run concurrently and have no serial completion guarantee**. Put order-dependent cleanup in one disposer returned from a single `ctx.effect()`.」→ **明说「反序」只保证启动顺序，不保证完成顺序**，并给出需要顺序时的写法。

对本项目：证据链的「校验器」如果依赖某个数据源服务，数据源撤下时校验器应当**跟着卸载**，而不是留在那里对着空气放行。「依赖消失 → 消费者自动下线」比「消费者自己判空」更 fail-closed。

### 7.7 事件模式四选一，且 waterfall 的 `next()` 是强制的

`framework/events.md:23-81` 把 `architecture.md:84` 那句压缩的 waterfall/serial 区分展开了：

| 模式 | 语义 |
|---|---|
| `emit` | 广播，同步，**返回值被忽略** |
| `bail` | 按序，**第一个非 `null`/`false`/`undefined` 的返回值成为最终结果** |
| `serial` | 按注册序，await 异步结果，第一个非空结果停止后续 |
| `waterfall` | 管道，**监听器必须调用 `next()` 才能向下游委托；不调用就短路** |

`:79-81` 用一个 warning 框强调：

> A waterfall listener **must call `next()`**. **Omitting it short-circuits the pipeline by design, enabling interception and gateway behavior.**

→ **「不调用 next 就短路」是被设计出来的能力，不是坑。** 拦截器与网关就是靠「故意不往下传」实现的。本项目的证据链门禁如果做成 waterfall，「拒绝」的实现方式就是**不调用 next**，而不是抛异常——语义上更干净。

`:106` 再次强调了 6.8 那条区分：

> `turn/*`, `step/*`, `tool/call`, `tool/result`, and `compaction/*` are **durable session-event types, not same-named Cordis events**. To observe them, listen to `session/event` and inspect `event.type`.

**同名但不同系统**，文档专门写一句防止混淆。

### 7.8 服务隔离：同一个服务的两份实例

`service.md:111-139` 展示了 `cordis.yml` 的 `isolate`：

```yaml
- id: group-a
  group: true
  isolate: { shell: true }
  config:
    - name: '@deepseek-ai/dsh-bash-local'
      config: { timeoutMs: 5000 }
    - name: './src/plugin-a.ts'
- id: group-b
  group: true
  isolate: { shell: true }
  config:
    - name: '@deepseek-ai/dsh-bash-local'
      config: { timeoutMs: 60000 }
    - name: './src/plugin-b.ts'
```

> `:139` — `plugin-a` and `plugin-b` each see the Bash instance in their own group, **with no cross-group effect**.

→ 这是 `architecture.md:112`「Give one session a different capability set → 那里的 service 行需要一个 `isolate` realm」的具体形态。**同一个 `ctx` 键在不同的 realm 里可以指向不同实例。** 「一个包拥有一个键」是**结构**上的唯一，不是**运行时实例**上的唯一——这两件事在 1.3 节没写清楚，这里补上了。

对本项目：「A 公司口径」与「B 公司口径」可以是同一个 `ctx.metricSpec` 键的两个隔离实例，而不需要把公司 id 塞进每一次调用的参数里。

### 7.9 两个不涉及本项目但值得记的事实

- `publish.md:16` — 「A bundle is what you author and distribute; a profile is what a user boots… **Nothing is both.**」 这是一句典型的**边界声明**：两个概念，两种 manifest（`dsh.bundle` / `dsh.profile`），**明确禁止兼任**。对照 7.1 里「a package may own more than one role」——**角色可以兼任，概念不可以。** 区别在于：角色是内部结构，概念是对外契约。
- `publish.md:173` — 允许 pnpm 跑 git 依赖的 `prepare` 脚本被定义成「**permission to execute the package's code on your machine at install time, outside any sandbox the agent runs under**」，并要求 pin commit sha。**把一个 pnpm 配置项翻译成它真实的安全语义**，而不是当成一个格式问题。

---

## 8. 补充四篇（**全文**）：`glossary.md`(45) / `defensive-patterns.md`(33) / `graph-atlas.md`(24) / `rescope.md`(53)

四份都逐行读完。

### 8.1 `glossary.md` —— 「一个概念一个规范术语」，而且会明写「不要用这个词指什么」

> `glossary.md:5` — Domain vocabulary for DeepSeek Harness uses **one canonical term per concept**. Terms link to their entries with standard Markdown anchors; **implementation detail stays in package READMEs and Agent Notes.**

只有六个词条组：`capability-seam` / `agent-scope` / `goal` / `human command` / `loop hierarchy` / `Ralph`。**术语表很短，这本身是个信号**——它只收「容易被误用的词」，不当百科。

三条对本项目直接可用的写法：

1. **词条会明写「保留这个词的这个含义，别用它指别的」**
   > `:9` — The seam is the complete capability, never one role; **reserve the term for that meaning and name a constituent by its role, class, service, contract, or extension point.**

   → 术语表不只定义「是什么」，还规定「**误用时该改用哪个词**」。这比单纯下定义有用得多。

2. **词条会明写「不是什么」，而且列举具体的易混淆项**
   > `:43` — **Ralph loop** … It is a model-facing tool policy composed from workflow and subagent primitives, **not a same-session goal, agent-loop mode, scheduler, or generic workflow-script feature.**

   一口气排除四个具体的错误归类。同样地 `:25`：「A goal is **state, not a scheduler or a separate conversation**; the session log remains its source of truth.」`:31`：human command「**is distinct from a model-facing tool and from shell command execution through `ctx.shell`**」。

3. **`:9` 补了一条 `architecture.md` 没写的类型约束**
   > a Service Definition is the Cordis `Service` that owns its `ctx.<key>` and vocabulary types — an abstract class such as `ShellExecutor`, or a concrete registry such as `WebRuntime`, **never a TypeScript `interface`**.

   → **接缝的定义必须是类（抽象类或具体注册表），不能是 interface。** 理由可推断：`Service` 有运行时身份（挂到 `ctx` 上、参与 Fiber 生命周期），interface 编译后什么都不剩。这与 `config-catalog.md:3094` 的 "Seam packages — abstract service classes" 一致。

**`agent-scope` 一组（`:13-21`）是本轮读到的第二强的一段**，因为它给了「权限/可见性」的一整套判据：

- `:13` **两层，扁平**：贡献要么全局，要么被恰好一个 scope key 拥有。「scoped registrations **do not inherit down to subagents**; subtree behavior is expressed with **lineage data, never scope structure**.」
  → **「谁能看见」与「谁是谁的孩子」被彻底分开**：可见性是两层扁平的，父子关系是数据。这条能防住一整类「权限随层级隐式继承」的 bug。
- `:15` **「one fact drives both」**：通过 `agent.ctx` 注册的东西，**可见范围与生命周期由同一个事实驱动**——不会出现「还看得见但已经死了」或反之。
- `:19` **被过滤掉的工具与不存在的工具不可区分**：
  > A filtered-away global tool is **absent from the prompt AND refuses execution, indistinguishably from a nonexistent one.**

  → **权限过滤必须同时作用于「描述面」与「执行面」**，且两者的失败表现要与「根本没这个东西」一致。只藏不禁（模型看不见但硬调能调通）或只禁不藏（看得见调不动）都是漏洞。这条对本项目的「某些口径在某些场景不可用」是直接适用的。
- `:21` **lineage 明写「never affects visibility」**。
- `:20` **setup window**：「Setup registers; **it never drives the agent.**」——组装期只准注册，不准驱动。

`loop hierarchy`（`:37-39`）补了 `architecture.md:65` 没有的第三层：**round**（外层策略迭代，含一个 turn）。并且明说「**Round counters belong to that policy and do not count every turn in a session.**」——计数器归策略所有，不是全局计数。

### 8.2 `defensive-patterns.md` —— 33 行，7 条「真实翻过车的 bug 类」

这份的定位与本项目 `rules/failure-modes.md` **完全同构**：

> `defensive-patterns.md:5` — Hard-won bug-class rules: **each pattern below is a class of defect that actually shipped or nearly shipped here, stated as the rule that prevents its recurrence.** Read this before writing lifecycle, concurrency, subprocess, or teardown code.

注意三个细节：（a）**「真实发生过或差点发生」是准入门槛**；（b）**写成「防止复发的规则」，不是「事故描述」**；（c）**明写什么时候该读它**（写生命周期/并发/子进程/拆卸代码之前）。第三点是我们的 `failure-modes.md` 也做到的，值得确认这条做法在别处也被独立采用。

七条规则里，四条与本项目同构：

1. **`:9` 正交结果必须各自独立上报**
   > A result can be several things at once — a process can time out AND exit 0 because it trapped the signal. Surface each independent fact (`timedOut`, `signal`, `exitCode`) on its own; **never nest one flag's report inside another's branch, or a caller reads a cut-short run as a clean success.**

   → **不要把一个标志的上报嵌进另一个标志的分支里。** 对本项目：「抽取成功」「口径匹配」「数值校验通过」是三个正交事实，不能写成「抽取成功 → 才去看口径」这种嵌套上报，否则「抽取失败」会被读成「口径没问题」。

2. **`:13` 公共契约要在两侧都遵守（归一化在实现侧完成）**
   > `LlmAdapter.stream()` implementations may throw or emit `finish {kind:'error'|'aborted'}`, but `LlmRuntime.stream()` **exposes model-request failures only as terminal finish chunks; middleware and consumer defects remain thrown.** This keeps consumers from guessing whether a caught exception came from the provider, a wrapper, chunk logging, or their own assembly.

   → **同一类失败只有一种表现形式，且不同来源的失败用不同通道**：模型请求失败 → 终结 chunk；中间件/消费者自己的 bug → 抛。消费者因此不需要猜异常来自哪里。这条对本项目的「抽取失败 vs 程序 bug」区分是直接可搬的。
   最后一句是配套的验证要求：「Document the normalized contract where the type is defined; **exercise every source form through the real consumer.**」

3. **`:17` 异步状态不是同步状态**（最长的一条）
   > Never treat `agent/status` or `whenIdle()` as the result of one follow-up… An automation caller that truly owns a run must **define its interval explicitly** — for example, from its message's durable inbox receipt through the next whole-agent `idle` — and **describe any selected output as interval-wide rather than causally attributed to that message.**

   → **不能把「区间内发生的输出」说成「这条消息造成的输出」。** 这是因果归属的诚实性问题，与本项目「证据链必须真的指向那条证据、不能只是时间上接近」同构。
   末句还有一条对称的警告：「**if the awaited transition can never occur, the wait hangs, so handle the "nothing to wait for" branch explicitly.**」——等待条件永不成立的分支必须显式处理。

4. **`:21` Dispose 必须到达静止，而不只是请求静止**
   > A teardown that issues kills/aborts but returns before the work stops leaves orphans. Make cleanup async and **await** the children's exit (kill → await `done`), and **close listener/notification registries BEFORE killing so late completions stay silent.**

   → 「发了信号就返回」= 留下孤儿。顺序也被写死：**先关监听注册表，再杀**，否则迟到的完成回调会说话。

另外三条（`:25` 把回调异常关在分发器里、`:29` 不给不可信输出环境变量与可预测路径、`:33` link 形状的路径用 `unlink` 不用 `rmSync`）是执行环境安全，本项目 Phase 2 若真的执行代码会用到，此处不展开。

`:29` 有一条可以现在就抄的：**spawn 出去的命令拿到的是洗过的环境变量（丢掉 `*KEY*` / `*SECRET*` / `*TOKEN*` / `*PASSWORD*`）**，理由是「harness credentials cannot leak into output, `env`, or spill files」——**注意它列了三个泄露面：输出、`env` 命令、以及 spill 文件。**

### 8.3 `graph-atlas.md` —— 一张「文档维护模式」的索引表

24 行，本身没有内容，但**它的表格结构值得抄**：九个图，每个标注 **mode**。

| Mode | 图 |
|---|---|
| `generated` | module-graph、tool-catalog |
| `hybrid generated` | capability-seams、三个 app composition、event-producer-consumer |
| `curated` | agent-lifecycle、tool-execution-pipeline |

> `:22` — Regenerate with `pnpm run gen-doc-graphs`; **verify freshness with `pnpm run verify-doc-graphs`.**
> `:24` — Maintenance mode: mixed: **each linked page declares generated, hybrid, or curated mode.**

三点：
1. **每一页自报维护模式**（生成 / 混合 / 人工），读者一眼知道该不该手改、能不能信它是新的。
2. **有独立的 freshness 校验命令**，与生成命令分开。
3. `:6` 说明了这些图存在的理由：「These diagrams show **relationships that the generated catalogs do not**」——图与目录分工，不重复。

→ 本项目 `references/` 已经在做「每份标注读到什么程度」，这里多一层：**每份产物还应标注「它是生成的、混合的、还是手写的」，以及「怎么验证它是新的」。** 我们目前只有前者。

### 8.4 `rescope.md` —— 一次改名的完整契约，价值在「不动什么」那一节

内容是把 vendored 的 Cordis 全家桶从上游名改到 `@deepseek-ai/*` 的映射表（9 个包）。理由（`:5`）：每个 harness 包都把框架声明为 peer dependency，发布 harness 就会连带发布这一层，**用上游名发布等于在 registry 上抢注（squat）别人的名字**。

真正值得记的是 `## What the rename does not touch`（`:23-31`）——**六条「不动」清单**：

| 不动的东西 | 理由 |
|---|---|
| 目录名与版本号 | 「so the vendored tree still **reads as an upstream snapshot**」——保持可与上游对账 |
| 依赖 range | 「A dependency entry **changes its key, never its range**」 |
| Loader 的 `cordis:` builtin 前缀 | 「a **protocol prefix, not a package name**」 |
| `cordis.yml` 配置文件族 | 含 `*.cordis.snapshot.yml`、`cordis.patch.yml` |
| 名字里含该词的自有包（`dsh-tool-cordis`） | — |
| 上游运行时标识符（`Symbol.for('schemastery')`） | — |
| `docs/` 之外的散文 | 「a bare `cordis` there **can also be the Python SDK's option name or an agent-preset id**」 |

**这是一份「同名不同物」的消歧清单**：同一个字符串 `cordis` 在七个不同位置分别是包名、协议前缀、文件名族、自有包名的一部分、runtime symbol、SDK 选项名、preset id。改名脚本必须逐一区分。

最后一节（`:42-53`）是执行契约：

> `scripts/rescope-vendor.ts` **owns the mapping above and performs the rename, so no reference is renamed by hand**
> ```
> pnpm run rescope-vendor            # report what would change
> pnpm run rescope-vendor --apply    # rewrite every reference
> pnpm run rescope-vendor:check      # assert the post-state; runs in the hygiene gate
> pnpm run rescope-vendor --apply --reverse   # return to the upstream names
> ```

四个能力齐全：**dry-run 报告 / 应用 / 事后断言（挂在门禁里）/ 可逆**。并且 `:53` 明写了后续必须跟着跑的三条重生成命令。

→ 对本项目：任何「批量重命名」类操作（例如台账编号 D 区改 N 区那次）都应当是**一个拥有映射表的脚本 + 一条 `:check` 断言挂进门禁 + 一个 `--reverse`**，而不是 sed 加人工核对。我们上一次做 N-30 时用的是人工核对；这份文档给了更好的形态。


---

## 9. 四个问题的回答（2026-08-21 本轮）

> **回答范围声明**：以下结论基于本文件第 1–8 节标注为「全文/部分」的那 23 份文档。
> 凡引用 `subsystems/*`、`cookbook/*`、`postmortem/*`、`cordis-tutorial/*`、`development.md`、`tool-catalog.md` 的地方，
> **都不在本轮阅读清单内**——那些是我为回答问题 3 跑 grep 时命中的，我只读了命中行及其上下文（每处 ±15 行），
> 一律标注为「grep 命中」，不得当作读过那些文档。

### 问题 1：模块/包边界怎么划、谁拥有哪个事实；对「先落地、边界待定」有无明写原则

**有，而且写得比我们的问题更精确。** 三个层面：

**(a) 「谁拥有哪个事实」= 「谁拥有哪个 `ctx` 键」。**
`architecture.md:43-51` 是一张 Package / Owns / `ctx` key 三列表。判据的关键在那一行例外：`core/scope` 的键栏写的是 **「library, no key」**——**纯库不拥有事实，因此不进 `ctx` 命名空间。**
这条判据在 `config-catalog.md:3114` 被独立复述了一次（`## Library packages (no plugin entry)`，「a `cordis.yml` cannot load them」，`dsh-scope` 在列）。**两份文档、两条独立生成路径、同一个判断，没有矛盾。**

四分法（综合 `architecture.md` + `config-catalog.md` 三个尾部分类节 + `capability-seams.md` 的 Role 列）：

| 类别 | 特征 | 例子 |
|---|---|---|
| 能力提供方 | 有 `ctx` 键 + 有 config | `dsh-fs-local`、`dsh-storage-sqlite` |
| 组合点 / 装配点 | 有 `ctx` 键 + 无 config | `dsh-agent`、`dsh-api-gateway`、`dsh-workspace` |
| 接缝定义 | 抽象 Service 类，**不可直接装载** | `dsh-fs`、`dsh-shell`、`dsh-sandbox`（15 个） |
| 纯库 | 无插件入口，只能 import，**无 `ctx` 键** | `dsh-scope`、`dsh-timeout`、`dsh-home-paths` |

`glossary.md:9` 还加了一条类型约束：接缝定义**必须是类**（抽象类或具体注册表），**「never a TypeScript `interface`」**。

**(b) 「先落地、边界待定」有明写原则，而且它不是「以后再说」，是一条可判定的拆分触发条件。**

> `user/develop/practice/index.md:149` — **Do not split preemptively** — use separate packages only when the roles need to evolve independently. A simple tool plugin does not.
>
> `:9` — Put the roles in separate packages **when they need to evolve or be replaced independently**; a package may otherwise own more than one role.

配套的三件事让「先合后拆」变得安全：
1. **边界形状预先定死**：任何能力都是三角色（Service Definition / Provider / Consumer），合并只是暂时把三个角色放进一个包。拆的时候不重新想边界。
2. **依赖方向预先定死**：Provider → Definition，Consumer → Definition，**Provider 与 Consumer 互不依赖**（`:52-54`）。
3. **命名把角色编码进包名**：`<域>` / `<域>-<实现>` / `tool-<域>` / `<域>-policy`（见 5.4 的统计）。**读包名就知道它是哪个角色**，这比架构文档难过期。

`glossary.md:9` 给了兼任的官方例子：`dsh-llm` 同时拥有 Service Definition 与 Consumer。

**(c) 边界分类是人的决定，但被固化在一个会失败的脚本里。**
> `capability-seams.md:471` — Maintenance mode: **hybrid**: services are discovered from Cordis declarations; **interface/implementation/consumer roles are classified in `scripts/gen-doc-graphs.ts` with a completeness guard.**

服务清单从代码自动发现，角色分类是人写的显式判断，**但它住在生成脚本里而不是文档里，并且有 completeness guard 防漏。**

**(d) 一条反直觉的结构事实**（5.5）：依赖最重的是示例与前端（`agent-spine-demo` 依赖 22 个包），不是核心（`core` 只有 8 个包）。
**核心的特征是「被很多东西依赖」，组合层的特征是「依赖很多东西」。** 用这条可以反过来检验一个包放错了层。

**(e) 最强的单点发现**：`invariants` 包被 219 个包中的 218 个依赖，自身零依赖（三种统计方法互相印证，见 5.3）。
→ **「运行时不变量断言」在这套架构里是最底层的基础设施包**，不是散落在各处的 `assert()`。对本项目：证据链断言器应当放在同样的位置。

---

### 问题 2：配置/映射类数据是单一全局文件还是按域拆分，`config-catalog.md` 记了什么代价

**按域拆分，而且是彻底的按包拆分。** 105 个可装载包，每个包自带自己的 `Config` 接口，没有任何跨包的全局键表。跨包引用用链接表达（`Depends on: [AgentLoopConfig](#…) · …`），不复制。

**明写的原则**（`user/develop/basic/config.md:80,92`）：

> Harness requires **anything that two deployments may want to set differently to be a configuration field**.
> **The test is whether `cordis.yml` can change the value without a code edit.**

这条原则**天然导致按域拆分**：「哪些值该可配」只有包作者知道，没有一个全局文件的位置能放它们。

**分层情况**（不是一个文件，是四层）：

| 层 | 位置 | 管什么 |
|---|---|---|
| 装配 | `cordis.yml` / bundle 的 `cordis.patch.yml` / profile 的 / home 的 / `--patch` | 装哪些插件、每个插件的 config |
| 用户设置 | `$DSH_HOME/settings.yaml` | 用户偏好；`dsh-settings-file` 只配「文件在哪、怎么热重载」，**不定义任何设置项语义** |
| 密钥 | `$DSH_HOME/.credentials.yaml` | `providers.md:13`「Keys are write-only… settings retain only its credential reference」 |
| 路由 | 各域自己的 config | `dsh-storage-domain`：「decided here, **not globally on the hub**」 |

层叠顺序写死在 `publish.md:114-119`（bundle 按列表序 → profile patch → home patch → `--patch` argv 序），且 **「a patch replaces a row's entire `config` value rather than deep-merging keys」**——**整行替换，不做深合并**，代价是「must restate every key the row needs」。自查命令 `dsh --profile web --dump-config` 能 dump 出真实生效值。

**`config-catalog.md` 记录的代价（问题问的是这个）——我在读过的部分里找到五条，全部是「关于粒度与默认值的自白」**：

1. **`config-catalog.md:1946`（storage-domain）**：路由粒度选在**域级**，且 `backend` 字段 **required**，理由写在注释里：**「Required: there is no universally correct medium.」**——拒绝给默认值，因为不存在普适正确的默认。代价：每个部署必须显式选一个默认后端。
2. **`api-gateway.md:164`**：lookup 策略配置粒度在 **key 级而非参数级**，代价是「**all `agent` or `session` parameters share the cold-resume behavior**」；并明说「Accepting live objects only would require an explicit per-parameter or per-endpoint policy, **which does not exist**」。**承认这个粒度做不到的事，并给业务方加了一条硬规则：不准去猜对象是不是恢复来的。**
3. **`config-catalog.md:452`（code-runtime）**：`maxWallMs` 至多 `2_147_483_647`，**「a longer value is rejected at load because `setTimeout` would clamp it to 1 ms」**——把宿主 API 的坑抬到配置校验层的代价，是配置里出现了一个看起来任意的魔数（并附理由）。
4. **`user/guide/providers.md:80`**：**「Both fields state a claim about your endpoint rather than checking it.」**——配置是声明不是检查，代价是错误配置在下游 provider 处才炸；文档明说「is not caught here」。理由（`:33`）：**「nothing can ask an endpoint which modalities it accepts」**。
5. **`user/guide/providers.md:67`**：`defaultInput` 是 **fallback 不是 override**，「so it never removes images from a catalog model that has them」——**兜底值不得反向削弱已知事实**，代价是想收窄必须写到那个模型自己的 `input` 上。

**另外，`config-catalog.md` 这份文档本身的维护代价被写成了三层机制**（`:8`）：从源码生成 + 独立的 `verify-config-catalog` 挂在 `doc-sync` + 生成器交叉核对运行时 schemastery schema 与粘贴的声明类型（**「every schema-validated key, nested keys included, must be locatable on the declared config type — so the paste cannot hide a loader-accepted field」**）。

---

### 问题 3：有没有「把字符串当表达式求值」的地方，自研还是三方库，封闭节点集是否显式要求

**有，而且是两套完全不同的机制，一套开放一套封闭。**

#### grep 记录（语料：还原后的 `docs/` 下 110 份英文 md）

命令模板：`find . -name '*.md' ! -name '*.zh.md' -print0 | xargs -0 grep -Eio -- "<pat>" | wc -l`

| 模式 | 命中数 | 命中文件数 |
|---|---|---|
| `eval` | 38 | 15 |
| `parser` | 6 | 6 |
| `expression` | 23 | 9 |
| `ast`（含 last/cast/fast 等误命中） | 180 | 55 |
| `\bAST\b`（词边界 + 剔除 last/cast/fast/past/broadcast/contrast/vast/master） | **1** | 1 |
| `sandbox` | 524 | 25 |
| `DSL` | 10 | 6 |
| `grammar` | 3 | 2 |
| `interpret` | 19 | 12 |
| `jsonpath` | **0** | 0 |
| `vm\.` | **0** | 0 |
| `new Function` | **0** | 0 |
| `Function(` | **0** | 0 |

#### (A) 开放的那套：`!!js` —— 完整 JS 表达式，**三方机制（Cordis loader）+ 本仓库扩展**

- **形态**：`apiKey: !!js process.env.MY_API_KEY`（`user/develop/practice/llm-adapter.md:131`）、`port: !!js ctx.myAppStartup.port ?? 8080`（`user/develop/basic/publish.md:148`）。
- **提供方**：Cordis loader（vendored，`rescope.md:14` 显示 `@deepseek-ai/cordis-plugin-loader` 1.0.0-rc.5）。**不是自研**，是三方 + 本仓库扩展。
- **求值时机（写成契约）**：`publish.md:151` — 「Loader mounts the composition once, **waits for each row's ordinary injections, and only then evaluates that row's `!!js` config** against its injected context.」
- **作用域**（grep 命中，`cordis-tutorial/05-config.md:80`，**该文档不在本轮清单**）：「`!!js` works only inside `config` and in an entry's `disabled` field. `disabled: !!js …` evaluates against the loader context at every mount decision (**this repo's extension**)…the other metadata (`name`, `id`, `inject`, …) **stays static, where an expression is ordinary truthy data**.」
- **封闭节点集？没有。** 在读过的 23 份文档里，我**没有**找到任何对 `!!js` 表达式语法子集、白名单节点、或求值沙箱的描述；上面 `vm\.` / `new Function` / `Function(` 三个模式在全部 110 份英文 md 里命中数均为 **0**。
  → **`!!js` 靠「只在两个位置生效」限制爆炸半径，而不是靠限制表达式本身。**
- **它造成过一次真实事故**（grep 命中，`postmortem/0002-js-expression-disabled-filesystem-tools.md:9,45`，**该文档不在本轮清单，前几轮读过**）：`disabled: !!js …` 在当时的 Cordis 里那个位置**不求值**，表达式对象作为普通对象参与真值判断 → 恒真 → 文件系统栈永远被禁用；快照刷新还把 `UNKNOWN_TOOL` 录成了新的期望输出。修法是**两道 guard**（static-config guard + snapshot-result guard）。通用规则写成：
  > **A syntactically accepted configuration value is not necessarily evaluated at that location; document and verify exactly which fields are interpolated.**

#### (B) 封闭的那套：工具参数与输出的 JSON-value schema DSL —— **自研，节点集显式封闭且被强制**

以下为 grep 命中 `subsystems/tools.md` 后阅读命中行上下文所得，**该文档不在本轮清单内**：

- `subsystems/tools.md:100` — `ValueSchemaSpec` 支持的节点**逐一列举**：`string`、`number`、`integer`、`boolean`、`null`、`array`、`object`、author-only `json`、exact-one `oneOf`。**九种，穷举，无 escape hatch。**
- `subsystems/tools.md:398` 的小节标题就叫 **`## The enforced raw JSON Schema subset`**（被强制的 JSON Schema 子集）。
  `:408` — 「`assertSupportedJsonSchema()` accepts any JSON root, `validateJsonSchemaValue()` enforces it, and **`JsonSchemaError` reports every unsupported or malformed schema path**. …`oneOf` requires **at least two branches** and a value must match **exactly one**.」
  → **「unsupported」这个词本身就证明支持集是封闭的**，而且错误报告会指出**每一条**不支持的 schema 路径。
- 来自 MCP / 子 agent / 工作流 / 动态注册的**原始 schema 也走同一个子集**（「Raw schemas from subagents, workflows, MCP, and dynamic registrations use the wire-level counterpart of the author DSL」）——**外来 schema 不能绕过这个封闭集**。
- **DSL 表达力不足的部分被明写**（grep 命中 `cookbook/adding-a-tool.md:42`，**不在本轮清单**）：「You still **hand-check constraints the DSL does not express**, such as non-empty strings, positive numbers, or cross-field rules.」→ **明确点名 DSL 不表达什么，让作者知道哪些必须手查。**

#### (C) 第三条相关线索：`run_code` —— 模型写程序，在 worker thread 里跑

- `config-catalog.md:2771`（`dsh-tools`）：`mode: 'native' | 'code' | 'both'`。**`code` 模式下模型只能调用一个工具 `run_code`**，其余工具变成生成的 SDK 里的函数（TypeScript 或 Python）。缺渲染器时**装配失败**，不降级。
- `config-catalog.md:543`：`computeMs` 的注释是「**Maximum synchronous VM evaluation time in milliseconds**」。四个上限全部可配（busy-time / wall-clock / output bytes / heap MiB），且计量的是 `worker.performance.eventLoopUtilization()` 测到的**忙时**而非墙钟——理由写得很清楚：「**fair**（等慢工具的程序不累积）**and ungameable**（热循环无论有没有诱饵派发都累积）」。
- `persistence-catalog.md:745,770`：`run_code` 里的每一次子派发都留两条 log-only 事件（start + settle，按 `subCallId` 配对），**「Every started sub-call settles with exactly one of these (abort included)」**，且**「Log-only: `deriveMessages()` ignores it, so sub-calls never re-enter model context; persistence and UIs get every call.」**
- **顺序被反过来安排以消除一整类失败**（`:775`）：参数「**normalized BEFORE dispatch, so this append can never fail on payload shape**」。

#### (D) AST / parser 的实际用途（都不是运行时求值）

`\bAST\b` 全语料**唯一一处**命中（`tool-catalog.md:8`，**不在本轮清单**）：
> Unlike the cordis catalog (**a pure source-AST pass**), this generator BOOTS each tool plugin on a real context and reads `ctx.tools.schemas()`, **because a tool schema is not statically knowable** (runtime-spread enums, concatenated descriptions, config-driven names, raw-JSON-Schema MCP tools).

→ **AST 用于文档生成，而且这一处专门说明了「为什么这里静态分析不够、改成真实启动」。** `parser` 的 6 处命中同样都是构建期/传输层（TypeScript parser 做 type-equiv 校验、SSE `eventsource-parser`、boot manifest parser、Typert 的 "SRC weak parser"），**没有一处是运行时把用户字符串当表达式求值**。

#### 结论（对本项目的取舍）

| | 开放（`!!js`） | 封闭（schema DSL） |
|---|---|---|
| 谁写 | **部署者**（人，写 `cordis.yml`） | **模型**（生成 arguments） |
| 表达力 | 完整 JS 表达式 | 九种节点，穷举 |
| 怎么限风险 | **限位置**（只在 config / disabled） | **限语法**（unsupported 路径逐条报错） |
| 出过事故 | 是（postmortem 0002） | 未见记载 |

→ **判据很清晰：人写的、可审阅的、在装配期一次性求值的东西可以开放；模型生成的、每次调用都不同的东西必须封闭。**
本项目的「指标口径映射表」是人写的配置，但它**会被自动执行且结果进入答案**——按这条判据应当归到**封闭**那一侧（对应 `api-gateway.md:194` 的做法：**主动砍掉一整片语言表达力换取可静态校验**），并且像 `cookbook/adding-a-tool.md:42` 那样**明写「DSL 不表达什么、哪些必须手查」**。

---

### 问题 4：校验/门禁在哪个边界执行：入口一次性，还是嵌进每一步

**都不是「入口一次性」。是分层的多道闸门，每一道有自己的失败语义、且每一道都被单独命名。** 在读过的文档里能数出**八个**不同的执行边界：

| # | 边界 | 出处 | 失败语义 |
|---|---|---|---|
| 1 | **编译期（类型形状）** | `persistence-catalog.md:46-50` | 非 surface 事件**永远不能**携带 surface 元数据——「**the compiler enforces this at `Session.append()` call sites**」 |
| 2 | **生成期 / doc-sync** | `config-catalog.md:8`、`graph-atlas.md:22` | `verify-config-catalog` / `verify-persistence-catalog` / `verify-doc-graphs`：schema key 必须能在声明类型上定位，否则门禁失败 |
| 3 | **构建期（顺序契约）** | `api-gateway.md:150-156` | 「**干净的工作树不能跳过 Host 阶段**」——顺序依赖被写成显式失败模式 |
| 4 | **载入期（声明式 schema）** | `user/develop/basic/config.md:74`、`config-catalog.md:422` | 「The schema runs while the plugin loads. **Invalid configuration fails the load with an actionable error.**」 |
| 5 | **载入期（`apply` 里的语义检查）** | `config-catalog.md:1436` | 「validated by the schemastery schema **plus the load-time checks in `apply`**（an empty list, a non-integer, a value below 2, or a duplicate throws at plugin load, **never a silent fall-back**）」 |
| 6 | **装配期 / 挂载期** | `config-catalog.md:2237`、`:176`、`:437` | 同一字段两个时刻：「**Invalid fields fail at load and unknown names fail at assembly**」；preset「Missing at mount time fails loud」；agent-presets 拒绝「永不激活的行」或「发布进 root realm 的行」 |
| 7 | **依赖就绪期（DI）** | `user/develop/basic/config.md:96`、`framework/index.md:38` | 「**References to services or registered resources require dependency injection**」；服务消失 → 依赖方自动卸载 |
| 8 | **每次调用（进入业务前 + 离开业务后）** | `api-gateway.md:125` | 「A missing provider, unknown identity, binding mismatch, missing or extra argument, schema failure, or missing method **fails before entering or after leaving business code**」——**入参与返回值都校验，且每次调用重新解析 descriptor 与活服务、不缓存业务对象** |
| 9 | **写入日志时** | `persistence-catalog.md:10,800` | 「Every payload is JSON-serializable (**enforced at `Session.append`**)」，非法值「**rejected at the source**」 |

**六条可直接搬运的判据：**

1. **「自足的约束」与「需要看别人的约束」用两套机制。**
   > `user/develop/basic/config.md:96` — **Express self-contained constraints in the schema** so invalid configuration fails while the plugin loads. **References to services or registered resources require dependency injection.**

   数值范围/枚举/必填/格式 → 声明式 schema，载入期挡；引用服务或已注册资源 → DI，依赖就绪期挡。**这条线画得非常干净。**

2. **`never a silent fall-back` 是明写的**（`config-catalog.md:1437`）。配置错了不许悄悄用默认值顶上。

3. **「引用不存在的实体」是错误，「匹配不到东西的谓词」是合法**（`config-catalog.md:1439`）：
   > `include`/`exclude` entries are `*`-wildcard predicates over tool names at call time, **not references to registry entries** — a pattern matching no currently registered tool is valid（`exclude: [mcp_*]` **must stay legal in a deployment that loads no MCP tools**）。

4. **缺省即失败，不是缺省即放行**（三处独立出现）：
   - `capability-seams.md:453` `ctx.approval`：「**absence fails closed to `unavailable`**」
   - `config-catalog.md:2825` `dsh-user-approval`：「'ask' delegates to the composed answerers（**fail-closed with none**）」
   - `persistence-catalog.md:65` `ignorable`：**字段缺失 = 必需 = 不认识就拒绝重建整个会话**，且理由写明（不认识的必需事件可能改变后面整条日志的解释方式），失败模式取舍也写明（**「defaulting to required means a forgotten marker over-refuses (an inconvenience) rather than silently resuming a gutted session」**）

5. **强模式撤下时不得自动落到弱模式**（`api-gateway.md:129`）：
   > A strict endpoint withdrawn on the Host **also does not degrade to SRC inference, preventing a hot unload from silently weakening validation.**

   并且弱模式的作用域被显式钉死在一侧（`:137`：Client 拒绝挂载缺少严格 codec 的 SRC descriptor）。**这正是本项目在证据链上要的语义：抽取器失效时不允许「降级成功」。**

6. **不许静默丢弃、不许隐式升格**（`user/develop/practice/llm-adapter.md:113,155`）：
   - 「If the provider cannot honor a field, **throw `LlmError` with a stable code instead of silently dropping it**.」
   - 「it **does not convert an ordinary `Error` automatically**.」

**两条与「审计」直接同构的补充：**

- **同一策略源被两条执行路径共读**（`capability-seams.md:452`）：`ctx.sandboxPolicy` 是 deployment 默认模式 + workspace root 的**唯一 home**，「**Both enforcing families read it so bash and fs cannot confine to different roots**」。工具层不读服务，只读它导出的**纯 fold**（`sandbox/mode`）——**读的人拿到的是投影，不是可变服务句柄。**
- **参数不可改写，理由是「几方必须一致」**（grep 命中 `subsystems/tools.md:400`，**不在本轮清单**）：
  > **Arguments cannot be rewritten because history, audit, UI, and execution must agree.**

  同段还有一条对称设计：post-policy 「**may replace either content or value, never both**」——内容替换保留规范值与元数据；值替换会**重新校验**并重算内容与元数据。**「改了什么就必须重新过一遍哪道校验」被逐条指定。**

**结论**：harness 的做法不是「入口一次性」也不是「嵌进每一步」，而是 **「每一类约束找到它最早能被判定的那个边界，在那里挡住，并给这道闸门起个名字」**。同一个字段可以在两个不同时刻各挡一次（`toolOrder`：载入期挡非法字段，装配期挡未知名字）。

---

## 10. 本轮阅读清单的收口

**本轮新读**（`references` 顶部台账表已同步）：

| 文档 | 标注 |
|---|---|
| `config-catalog.md`(3151) | **部分**（L1–14 全读 + 105 个标题索引 + 12 段抽读 + 全文 grep） |
| `module-graph.md`(1638) | **部分**（L1–7 全读 + 全图脚本统计 + 首尾抽读） |
| `persistence-catalog.md`(944) | **部分**（L1–93 全读 + 68 个标题索引 + 4 段抽读） |
| `user/` 13 篇（1499） | **全文** |
| `glossary.md`(45) / `defensive-patterns.md`(33) / `graph-atlas.md`(24) / `rescope.md`(53) | **全文** |

**本轮只改了台账、正文是前几轮写的**：`api-gateway.md`、`capability-seams.md`（正文已在文件中，台账此前落后于正文，本轮已改为「全文」）。

**仍未读**（`docs/` 下还原出 110 份英文 md，本文件覆盖 23 份，**未覆盖 87 份**）：

- `subsystems/` 全目录（本轮为回答问题 3/4 只 grep 命中并读了 `tools.md` 的 `:98-120`、`:398-412`、`:400`，以及 `shell.md:103`、`client-modules.md:11`、`typert.md:28`、`feedback.md:190`、`system-prompt.md:56,82,132,142`、`workflow.md:13` 等命中行）
- `cookbook/` 全目录（只读了 `adding-a-tool.md:42`、`adding-an-llm-adapter.md:5` 两处命中行）
- `cordis-api/`、`cordis-tutorial/` 全目录（只读了 `05-config.md:80`）
- `postmortem/` 全目录（前几轮读过一部分；本轮只读了 `0002:9,45`）
- 顶层未读：`agent-lifecycle.md`、`cordis-primer.md`、`development.md`（只读 `:171`）、`event-producer-consumer.md`、`testing.md`、`tool-catalog.md`（只读 `:8`）、`tool-execution-pipeline.md`、`web-styling.md`、`docs/AGENTS.md`
- `i18n/` 全目录（翻译流程，与本项目无关，建议不读）

**下一轮的优先级建议**（按对本项目的边际价值排序）：
1. `subsystems/tools.md` —— 本轮 grep 出的两段（封闭 schema 子集、参数不可改写因为 history/audit/UI/execution 必须一致）说明这份文档的密度最高
2. `tool-execution-pipeline.md` + `event-producer-consumer.md` —— 门禁与事件流的完整形态
3. `testing.md` —— `defensive-patterns.md:5` 点名它是测试层对应物（real entry path / world-verification / resource ownership）
4. `development.md` —— `:171` 显示它藏着 `verify-type-equiv` 这套「文档与源码等价性门禁」的完整规格
