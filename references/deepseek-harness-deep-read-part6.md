# deepseek-harness 深读 Part 6 —— 剩余 subsystems / Cordis / user 文档 / 生成物

读取范围：本轮分配的 **61 篇**（详见 §1）。
读取方式：逐篇读英文原文（`.md`，非 `.zh.md`、非 `.i18n.yaml`）。
行号引用均指英文原文文件。

> 纪律声明：本文件只对**我实际读过的行**下断言。生成物中若只出现类型别名而无字段集，
> 明确写「知道类型名，不知道字段集」，不猜。前几轮结论若与原文冲突，以原文为准并注明出处。

---

## 1. 完整清单与覆盖度

### 1.1 分母是怎么数出来的

`docs/subsystems/` 下每个子系统有三个文件（`X.md` / `X.zh.md` / `X.i18n.yaml`），
只算英文 `.md`，共 **46 篇**（含 `README.md`）。

已在「已读，不要重读」清单里的 subsystems 共 17 篇：
`approval` `compaction` `core` `invariants` `jobs` `llm-streaming` `persistence`
`scope` `session-projection` `session-query` `session` `skills` `spill`
`subagent` `system-prompt` `token-meter` `tools`

→ 本轮 subsystems 待读 **29 篇**（任务书点名的 5 篇只是其中一部分，
实际未读的比点名的多 24 篇，已全部纳入）。

### 1.2 本轮分配总清单（61 篇）

| # | 组 | 篇数 | 文件 |
|---|---|---|---|
| A | `docs/subsystems/` 剩余 | 29 | README, attachment, client-modules, code-runtime, commands, credentials, extensions, feedback, filesystem, goal, lsp, permission-presets, plan, sandbox, schedule, session-reference, session-telemetry, session-title, settings, shell, storage, subprocess, terminal, typert, user-questions, web, web-server, workflow, workspace |
| B | Cordis primer + API | 7 | cordis-primer, cordis-api/{context, events, fiber, inherited, registry, service} |
| C | Cordis tutorial | 8 | cordis-tutorial/{index, 01-first-plugin, 02-lifecycle-and-effects, 03-services, 04-events, 05-config, 06-composition-and-hmr, 07-into-the-harness} |
| D | `docs/user/` | 13 | index; develop/basic/{index,config,publish,tool}; develop/framework/{index,service,events}; develop/practice/{index,llm-adapter}; guide/{index,python-sdk,providers} |
| E | 三篇根文档 | 3 | api-gateway, architecture, module-graph |
| F | 生成物定向查询 | 1 | config-catalog（3151 行，定向查，不逐行读） |

**覆盖度结论见 §6（末尾），那里逐个列出读完 / 未读完的篇目。**

---

## 2. 【最重要】`cordis-api/registry.md` 对「waterfall 能否作闸门」的最终判断

### 2.1 结论

**上一轮的担心是对的，而且比原来更严重。Cordis 没有提供任何可以把 waterfall 变成闸门的机制。**

具体核实三项：

| 上一轮设想的「翻案条件」 | 核实结果 | 出处 |
|---|---|---|
| Cordis 提供**监听器优先级**（数字 priority / order） | **不存在。** 唯一的顺序控制是布尔 `prepend` | `docs/cordis-api/events.md:177-185` |
| Cordis 提供**加载顺序保证** | **不存在。** `inject` 只保证「所需服务已存在」，不保证同级插件之间的注册先后 | `docs/cordis-api/registry.md:8-31, 123-152` |
| Cordis 提供**不可卸载的 guard** | **不存在。** 所有注册一律可撤销，这是框架的明示设计目标 | `docs/cordis-api/events.md:125-147`；`docs/cordis-primer.md:13` |

### 2.2 逐条证据（读原文所得）

**(a) `Plugin.Base` 的字段集里没有优先级。**
`registry.md:70-83` 给出了完整字段集（这是字段集，不是类型别名，可以下断言）：

```
name?      : string        显示名，仅用于诊断与 logger 名
Config?    : StandardSchemaV1  配置校验器
inject?    : Inject        依赖的服务；只在这些服务都可用时加载
provide?   : string | string[] 提供的服务名
intercept? : Dict<boolean>     声明消费哪些服务的 intercept 配置
```

五个字段，**没有 `priority`、没有 `order`、没有 `guard`、没有 `critical`**。
插件元数据层面不存在任何「我必须先于别人跑」的表达方式。

**(b) `inject` 的语义是「等待存在」，不是「排在后面」。**
`registry.md:137` 的类型是 `Inject<M> = (keyof M)[] | { [K in keyof M]?: M[K] }`，
`registry.md:11-19` 的语义是「Run a callback once the requested services are available」，
并且「the callback is unloaded and **re-run** whenever a required service changes」。

这句话本身就是闸门的反面：**依赖服务一变，回调被卸载再重跑**。
一个靠 `inject` 拿到位置的监听器，会在依赖服务重新加载时被摘下来重新注册——
它在监听器链条里的位置因此是**会漂移的**，不是固定的。

**(c) `EventOptions` 只有两个开关，都不解决顺序问题。**
`events.md:178-185`（同样是完整字段集）：

```
prepend?: boolean   插到同事件已有监听器之前
global? : boolean   无视 context filter 检查，照样收到事件
```

`prepend` 是「插到队首」，不是「优先级 N」。两个都声明 `prepend: true` 的插件之间，
**后注册的排在更前面**，谁在前取决于加载时序——而加载时序恰恰没有保证（见 b）。
primer 自己也只敢说 `prepend` 用于「must run before ordinary registrations」
（`cordis-primer.md:32`），措辞是「普通注册」，即它默认了不会有第二个 prepend 竞争者。

**(d) 每个监听器都自带卸载器，框架把「可撤销」当成设计目标。**
`events.md:134` — `ctx.on` 的返回值是「a disposer removing the listener」。
`cordis-primer.md:13` 把这一点提到五大理念之一：
「Registrations are reversible effects... so reload and teardown unwind them predictably」。
`fiber.md:102-111` 的 `fiber.dispose` 是 public 字段，任何拿到 fiber 的代码都能卸掉整个插件。
**框架里不存在「注册后不可摘除」这种东西。**

**(e) waterfall 的短路语义被两处原文确认，并且短路会吃掉内置行为。**
`events.md:114-116`：「calling `next()` invokes the next listener (**finally the built-in behavior**);
not calling it **vetoes**」。
`cordis-primer.md:30`：「Call `next()` to delegate...; return without `next()` to short-circuit.」

关键在括号里那句：链条的最末端才是**内置行为**。
所以任何一个排在你前面的监听器只要不调 `next()`，
不仅你的闸门不会执行，**系统自带的默认行为也不会执行**。
闸门要成立，前提是「没人能排在我前面」——而 (a)(b)(c) 已经证明这个前提无法保证。

### 2.3 我还找到两个上一轮没提、进一步削弱闸门的机制

**(f) `ctx.isolate()` 可以在子树里把服务整个换掉。**
`context.md:41-59`：「Below the returned context, reads and writes of the service `name`
resolve against the new label instead of the parent's, so a different implementation
can be provided **without affecting the parent scope**」。

含义：闸门若实现为某个服务（例如 `ctx.approval`），
任何代码都可以 `ctx.isolate('approval')` 造一个子上下文，在里面塞一个自己的实现，
**父作用域完全无感**。这不是绕过监听器链，这是把被守卫的对象整个替换掉。

**(g) `Context.filter` 让上下文可以决定某个监听器收不收得到事件。**
`context.md:179-186`：「Symbol key for a context's listener filter, **consulted on every event dispatch**」。
配合 `EventOptions.global`（「Receive the event regardless of context filter checks」，`events.md:183`）
反推：**默认情况下监听器是会被 context filter 挡掉的**，只有显式声明 `global: true` 才无视过滤。
也就是说，一个闸门监听器若忘了 `global`，它在某些上下文下会**静默地根本收不到事件**——
不是拒绝，不是报错，是压根没被调用。这正是本项目关切 §5.2「失败被静默转成正常值」的结构性温床。

### 2.4 落到 finaudit-agent 的判断

- 「waterfall 不能作闸门」的原判**维持，不需要更正**。
- 证据链闸门若要成立，必须放在**唯一入口的同步调用路径上**（函数调用、不可绕过的构造器），
  不能放在任何「可注册 / 可卸载 / 可换实现」的插件事件链上。
- 反过来，Cordis 这套「一切可撤销」的设计对**可观测性**是好的：
  `fiber.getEffects()`（`fiber.md:195-210`）能列出当前所有已注册效应及其嵌套树，
  这是一种可以借鉴的**「我现在到底装了哪些拦截器」自查能力**——
  证据链系统应该有等价物：能枚举当前生效的全部校验器，而不是相信它们都装上了。

---

## 3. 逐篇发现

（下面按阅读顺序追加。）

### 3.B Cordis primer + API（7/7 读完）

**`docs/cordis-primer.md`（44 行，全读）**

- `:19-25` 的 dispatch 模式表与 `events.md:189-204` 的 `DispatchMode` 类型**不一致**：
  primer 的表只列了 4 种（`emit` / `waterfall` / `parallel` / `serial`），
  而 `DispatchMode` 类型有 5 种，多一个 `bail`。
  primer 表里还把 `waterfall` 标成「Awaited? No」，但 `ctx.waterfall` 的返回值是
  `ReturnType<Events[K]>`（`events.md:110`），链式 `next()` 完全可以返回 Promise。
  → **这是文档生成物与手写文档之间的一处真实漂移**，且 primer 是给插件作者读的入门文档。
  借鉴点：手写概览与自动生成的类型目录并存时，漂移会出现在手写那一侧。
- `:26` 有一个值得抄的机制：「New harness events document it with an `@mode` tag
  **so the generated catalog can check declarations against dispatch sites**」——
  声明处的 `@mode` 标注会被拿去和实际派发点比对。这是**用生成器做一致性门禁**，
  不是靠人记。对应到本项目：口径声明与实际调用点应当可机器比对。
- `:38` Loader 会对 `config` 和 `disabled` 字段做表达式插值（`!!js`）。
  `disabled` 是「at every mount decision」求值的——**这意味着「插件是否启用」是运行时表达式**，
  不是静态配置。见 §5.4 的可配置项风险。

**`docs/cordis-api/registry.md`（152 行，全读）** — 见 §2。

**`docs/cordis-api/events.md`（207 行，全读）** — 见 §2。另记：
- `ctx.serial` 与 `ctx.bail` 的「bail 值」定义是「non-null, non-false, non-undefined」
  （`:59`、`:83`）。**返回 `false` 不算 bail，返回 `0` 或 `''` 算 bail**
  （因为 `0`/`''` 既非 null 也非 false 也非 undefined）。
  这是一个典型的「用 truthy 语义做控制流」的坑：一个返回 `0` 的正常结果会被当成「我做主了，停」。

**`docs/cordis-api/context.md`（364 行，全读）** — 见 §2(f)(g)。另记：
- `ctx.get(name, strict?)`（`:239-249`）：`strict` 默认 `true`，
  「only return implementations whose providing fiber is currently active」。
  **默认严格，要拿到未激活实现必须显式传 `false`** —— 这是一处 fail-closed 的默认值，记入 §5.1。
- `ctx.set`（`:263-274`）：「Only the fiber that provided the service may set it;
  setting an unprovided name **throws**」—— 越权写服务是抛异常，不是静默忽略。记入 §5.1。
- `ctx.provide`（`:288-302`）：「**Throws** if the name is already provided in this scope」——
  服务重名是硬失败。记入 §5.1。

**`docs/cordis-api/fiber.md`（375 行，全读）**

- `ctx.effect`（`:10-30`）：「Throws `CordisError('INACTIVE_EFFECT')` if the fiber is already disposed,
  and **`TypeError` if `execute` returns an invalid shape**」——
  返回形状不对是抛错而不是忽略。记入 §5.1。
- `:30` 「Calling the disposer twice is a **no-op**」—— 幂等释放。
- `fiber.await()`（`:212-227`）：「Wait for current lifecycle work and **rethrow startup errors**」。
  注意措辞是 rethrow —— 启动错误是被**存下来**的，需要显式 `await()` 才会重新抛出。
  **不调 `await()` 就看不到启动失败**。`ctx.plugin` 的返回值是 `Fiber & PromiseLike<Fiber>`
  （`registry.md:46`），只有 await 它才「rejecting on config or startup errors」。
  → 这是一个**「失败可以被静默持有」**的结构：插件启动失败了，fiber 对象照样在，
  只有主动去 await 才知道。记入 §5.2。
- `fiber.update()`（`:248-267`）：「Runs the `internal/update` waterfall first,
  so update hooks (and HMR) can **veto or replace** the restart」。
  配置更新本身也是一条可被第三方否决的 waterfall —— 再次印证 §2 的结论：
  这个框架里连「配置更新」都不是不可拦截的。
- `CordisError.Code`（`:349-351`）只有**一个**码：`INACTIVE_EFFECT`。
  框架级错误分类极窄，绝大多数失败走的是原生 `TypeError` / `ValidationError`。

**`docs/cordis-api/service.md`（102 行，全读）**

- 全篇只有 `service.name` 一个实例成员 + 6 个 static symbol key
  （`init` / `check` / `config` / `invoke` / `extend` / `tracker` / `resolveConfig`）。
- `Service.check`（`:38-46`）：「Symbol key of the **availability predicate** passed to `ctx.provide()`」。
  → 服务可以声明自己「当前是否可用」。这是一个可以借鉴的形状：
  能力对象自带可用性谓词，消费方 `ctx.get(name)` 在 strict 模式下拿不到不可用的实现。
  但**我只知道它是个谓词，不知道它的签名与被调用时机**——本页没给。如实标注。

**`docs/cordis-api/inherited.md`（39 行，全读）**

- `:8` 记录了一条自证机制：本文件「is GENERATED from source... and
  **verified fresh by `pnpm run verify-cordis-catalog`（part of `doc-sync`）**」。
  即：文档与源码不同步会被 CI 抓出来。这是**真实的自证**（有可执行校验命令），
  与 §5.3 收集的「声称通过但没证明」形成对照，属于正面样本。
- `:25-32` 列出 8 个 `internal/*` 事件，其中 4 个是 waterfall：
  `internal/update` / `internal/get` / `internal/set` / `internal/dispatch`。
  **`internal/get` 和 `internal/set` 是 waterfall** 意味着
  「从服务库读一个服务」这件事本身可以被第三方监听器包裹和替换。
  → 这是 §2 结论的最强证据：连服务解析都能被中间件改写，
  任何「我拿到的是真的那个服务」的假设都不成立。

### 3.A `docs/subsystems/` 剩余 29 篇

#### `sandbox.md`（218 行，全读）—— 本轮 fail-closed 密度最高的一篇

- **明写的 fail-closed 铁律**（`:154`）：「`ctx.sandbox.confine()` 返回 `ConfinedArgv`
  或抛 `SandboxUnavailableError`（code `SANDBOX_UNAVAILABLE`）when no usable backend exists.
  **Silent unconfined passthrough is never legal for a confined policy.**」
  `:170` 再说一遍：「confine must return enforcing argv or **fail closed** at wrap or
  runner-execution time; silent unconfined passthrough is forbidden.」
  → 同一条规则在同一页写两遍（一遍散文、一遍 JSDoc 进生成物），说明作者知道这条最容易被绕。
- **`SandboxEnforcement = 'full' | 'partial'`（`:32-38`）：把「我只管住了一部分」变成一等返回值。**
  `:30`：「Enforcement is a reported **fact**... consumers that require the absolute promise
  **must reject or surface that distinction**.」
  当前的 partial 实例：旧 Landlock ABI、Windows ACL runner 的 Everyone/硬链接边界。
  → 这是本项目最该抄的一条：**「部分成立」必须是可返回的第三态，不能塌缩成 true**。
  对应我们的证据链：口径校验「只核了 3/5 项」不能报 PASS。
- **`RunnerFailureRule`（`:100-115`）的证据纪律，三层，值得逐条抄**：
  1. `:106`「**Exit status alone never proves runner failure.**」退出码本身不构成证据。
  2. `informationalLines` **先按整行精确相等剔除**，再做致命特征匹配
     ——`:98`「a benign runner notice cannot prove failure by itself」。先排除良性噪声再判定。
  3. `:98`「The matched line remains available as error detail;
     **classification does not rewrite stderr**」——分类不改写原始证据。
  → 「判定层不得篡改原始证据，只能在其上附加结论」正是证据链该有的形状。
- **`denialSignatures` 反对「并集」（`:132-138`）**：只匹配**当前 backend 实际会产出的**
  拒绝特征（bwrap 下 EROFS、Landlock 下 EACCES、Seatbelt 下 EPERM），
  「a consumer that infers denials from a failed run's stderr matches against exactly these
  rather than a cross-backend union — **the union claims denials a given backend never produces**」。
  → 用跨后端并集去匹配，会宣称一个后端根本不会产生的拒绝，即**制造假阳性证据**。
- **路径规范化顺序（`:43`）**：workspaceRoot「is canonicalized with filesystem semantics
  **before** lexical normalization, so a cwd containing `symlink/..` identifies the directory
  where a spawned process **actually** runs」。先走文件系统语义再做字面规范化——
  纯字面 `path.normalize` 会被 `symlink/..` 骗过去。这是一处真实的边界正确性细节。
- **可配置的全绕过**（记入 §5.4）：`SandboxMode` 的第三值 `danger-full-access`
  「**bypasses confinement**」，且 `:23`「A `danger-full-access` consumer spawns its
  original argv and **does not call `ctx.sandbox`**」——
  即该模式下沙箱层根本不在调用路径上，上面所有 fail-closed 保证一并失效。
  优先级：`:197-200`「approved explicit mode **outranks** the session's last `sandbox/mode`
  event, which outranks the deployment default」——运行期审批可以压过部署默认值。
- 作用域诚实：`:11`「`SandboxMode` governs **filesystem effects only**...
  **Network and process visibility are outside this vocabulary.**」
  不假装管了没管的东西。记入 §5.3 正面样本。

#### `credentials.md`（133 行，全读）

- **「空值即缺失」是 seam 级铁律**（`:5`、`:64`）：「an empty stored value is absent everywhere
  — `resolve` skips it, `describe` reports it unconfigured — so **a blank never masquerades
  as a configured secret**.」→ 直接对应 §5.2：空串是最经典的「失败伪装成正常值」。
- **`describe()` 的 `writable` 字段是为了阻止一次「看起来成功了」**（`:34`）：
  当引用被进程环境变量遮蔽时报 `writable: false`，理由原文是
  「**a write would appear to succeed while resolution kept returning the shadowing value**,
  so the seam rejects it and the UI can render the reference read-only up front」。
  → 这是「预先拒绝一个会静默无效的写操作」，而不是写完再说。极好的反例样本。
- **每次操作重新解析，禁止跨操作缓存**（`:20`、`:67-74`）：轮换后的凭据下一次请求即生效。
  代价是没有一致性快照；收益是不存在「用了已失效凭据还以为有效」的窗口。
- **⚠️ 一处真实的不变量陷阱**（`:114`，记入 §5.2 与 §5.4）：
  `credentials/updated` 事件的监听器失败「are contained and logged — a sync throw and an
  async rejection alike — without changing the committed operation's outcome,
  **except `INVARIANT`-coded failures, which rethrow after every listener ran;
  that rethrow reaches the emitter only from synchronous listeners,
  so invariant checks on this event must not be async functions**」。
  → 把不变量检查写成 `async` 函数，它**永远不会向上传播**，检查看起来装上了、实际是哑的。
  这正是本项目 CLAUDE.md 里「造出的是永远不会正确触发的假规则」的同构陷阱，
  而且这里是**框架语义导致的**，不是作者疏忽——写对了也可能因为加个 `async` 而失效。

#### `session-telemetry.md`（194 行，全读）—— 明确「这不是审计日志」

- **交付是尽力而为，并且原文点名不可作账**（`:57`）：
  「Delivery is **best-effort**: the cursor marks **handed-off, not delivered**,
  records **can be lost** (crash, reload window) **and duplicated**
  (cursor-less re-adoption, SDK retries), so receivers dedupe ledger records on
  `(session.id, event.seq)`; ops records deliberately omit that identity —
  **they are signals to alert on, not entries to sum**.」
  → 对 finaudit-agent 的直接含义：**遥测流不能充当证据链载体**。
  能被丢、能被重、游标只记「交出去了」——三条任一都足以否掉可复核性。
- **序号空洞被设计成不可作为丢失信号**（`:57`）：每个 `(turn, step)` 只发第一个
  `assistant/chunk`，其余在捕获处丢弃，「so `seq` gaps are **routine** on the wire
  and **never a loss signal**」。→ 这是一处**主动放弃可检测性**的取舍：
  为了省流量，牺牲了「用空洞检测丢失」的能力。取舍本身是明写的，但代价要认。
- **脱敏默认关闭（fail-open 的一处）**（`:126`、`:169`）：
  `session-telemetry/record` waterfall「ships **NO** rules of its own: with no listener
  mounted, records reach the backend **exactly as captured**, so exported data is
  **precisely as clean as the rules a deployment mounts**」。
  → 默认导出未脱敏原文。这句话写得很诚实（把责任明确推给部署方），
  但它就是「隐私维度的 fail-open」：不配置 = 全量外发。记入 §5.4。
- 同一个 waterfall 里**有一处 fail-closed**（`:126`、`:169`）：
  「a **throwing** listener withholds that one record (**fail-closed**)
  and never reaches the agent loop」——脱敏规则抛错则该条记录不外发。
  即：脱敏规则「装了但崩了」→ 扣住；「压根没装」→ 全放。两种失败方向相反。
- 其余错误一律吞：`:88` `emit()`「Errors thrown here are contained by the coordinator
  and logged; they never reach the loop」；`:113` `shutdown()` 的 rejection
  「is logged as a warning and **never fails application teardown**」。
- `:61` 的声明纪律（§5.3 正面）：sharing 披露「states the **current policy**,
  **never delivery or retention**」——只承诺自己知道的那一层，不承诺投递与留存。
  且「consumers render 'not configured' **only when no telemetry service is mounted**」——
  区分「没装」与「装了但关了」，不把两者混成一个状态。

#### `session-title.md`（204 行，全读）—— 意外地是最像「证据链」的一篇

- **发请求之前先把请求本身落账**（`:67`）：`SessionTitleLlmRequestEventData`
  「records each validated, dispatchable title request **before calling the model**.
  The payload reproduces the model-visible system and message input, routing,
  output limit, provider ownership, and source-message attribution
  **even when generation later fails**.」
  字段集完整（`:71-84`）：`titleProvider` / `messageSeqs` / `route{provider,model}` /
  `system` / `messages` / `maxTokens`。
  → 这就是本项目要的形状：**先记「我打算用什么口径、喂了什么、限了多少」，再执行**；
  执行失败不擦除来源记录。一个连「给会话起标题」都这么记的系统，
  说明这套记账纪律是全局的，不是给关键路径特供的。
- **产出物携带出处的三态判别式**（`:29-41`）`SessionTitleSource` =
  `{kind:'fallback'}` | `{kind:'provider', provider, model?}` | `{kind:'user'}`。
  → 「这个结论是兜底来的 / 某个具体模型来的 / 人改的」被编码进数据本身，不是靠日志推断。
  对应我们的口径来源：内置规则 / 准则条文 / 人工覆盖，必须同样可判别。
- **结论反向指回输入**（`:47-52`）：`messageSeqs` 是
  「Exact human `user/message` seqs used to derive this title」，
  用户显式改名时为空数组。→ 产物 → 输入 seq 的精确反查链，且「人改的」用空集合诚实表达
  「这个标题不由任何输入推导而来」。
- **provider 不被信任，service 负责验收**（`:89`）：
  「A provider returns **only seqs from that request**; **service-owned acceptance**
  verifies ordering, normalizes the title, enforces the byte limit,
  and appends the title with its source-message seqs and source kind.」
  → 外部实现只提议，接受与否由本体判定。这是把「谁有权写账」收在一处。
- 人工覆盖是**钉死**的（`:38`、`:171-176`）：`kind:'user'` 会 pin 住标题，
  在途的自动生成被 supersede，后续消息不再排程；解钉必须显式调 `refresh()`。
  → 人工判断优先于自动判断，且「解除人工优先」也是一个需要显式动作的、可记录的事件。
