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

#### `plan.md`（88 行，全读）—— 明写「这不是门禁」的样本

- **`:5` 一句话把自己降级**：「Plan mode is **soft guidance**. [Sandbox mode] and [approval policy]
  enforce restrictions independently; **neither reads or writes plan state**, so deployments
  configure them separately.」
  → 这是本轮最值得抄的一条自我定位。一个在 UI 上看起来像"限制模式"的东西，
  文档第一段就说明它只是往系统提示里插一段文字，真正的强制在两个完全不读它的子系统里。
  对应 finaudit-agent：**提示词里写「请核对口径」不是门禁**，把它写进 prompt 与把它写成校验器
  是两件事，文档必须像这里一样把区别写在最显眼处。
- **未知配置键在加载期硬失败**（`:29`）：「A missing, blank, or non-string `section` and
  **any unknown key fail at plugin load rather than being ignored**.」→ fail-closed 默认，记入 §5.1。
- **工具面稳定 + 运行期拒绝**（`:33`）：`exit_plan_mode`「stays registered while plan mode is
  inactive, so entering or leaving plan mode changes only the prompt section,
  **never the request tool catalog**; execution outside plan mode fails」。
  → 不用动态增删工具来表达模式，而是工具恒在、越界执行时失败。
  好处是请求的工具目录跨模式恒定（可复现、可缓存），坏处要自己承担（模型看得见一个当前用不了的工具）。
- **`set()` 返回四态而非 boolean**（`:81`）：`'committed' | 'queued' | 'cancelled' | 'noop'`。
  → 与 sandbox 的 `SandboxEnforcement` 同构：**把"发生了什么"如实返回，不塌缩成成功/失败**。
- **⚠️ 一处明写的静默丢失**（`:17`，记入 §5.2）：
  「An **append failure cannot block the turn**, and the selection remains pending」；
  且「A selection made after a turn's final accepted pre-step remains **process-local and is lost**
  if the process exits before another accepted in-turn pre-step」。
  → 用户的一次模式选择可以无声消失。作者把它写进 README 的 known-limitations，
  属于"已知且已披露"，但仍是本项目要避免的形状：**证据链的写入失败绝不能"不阻塞主流程"**。

#### `permission-presets.md`（131 行，全读）—— 聚合层不得拥有强制力

- **`:5` 的分工声明**：preset 把 sandbox mode 与 approval policy 两个独立开关捆成一个 UI 选择器，
  但「**it owns no enforcement**: execution, prompt narration, and replay keep reading their knob folds,
  and a preset switch only **records intent** and **writes through each knob's canonical setter**」。
  → 借鉴形状：**便捷聚合层只能写穿到各自的权威 setter，不能自己维护一份"当前权限状态"**。
  否则就会出现聚合层说 A、真实开关是 B 的经典不一致。
- **加载期硬失败两条**（`:44`）：表项名为 `custom` 抛错（保留名）；
  **在一个不做 confine 的 bash executor 上组合本服务抛错**（缺 `sandboxMode` capability fact）。
  → 第二条尤其好：预设承诺了 sandbox 语义，若底层执行器根本不具备该能力，
  **拒绝加载，而不是加载后让预设变成装饰**。记入 §5.1。
- **`custom` 是派生第三态**（`:48`）：当实际开关值不匹配任何预设时返回 `CUSTOM_PRESET`，
  且「`custom` is derived-only: clients may display it as the current value,
  but it is **never a switch target or an event payload**」。
  → 与 sandbox 的 `partial` 同构：**"当前状态不属于任何已命名档位"是一个必须能表达的值**，
  不能就近吸附到最像的那个预设上。同时它不可被写入，杜绝"把 custom 存下来"造成的假状态。
- **⚠️ 默认表自带一个"两个门禁一起关"的预设**（`:11`，记入 §5.4）：
  出厂 `danger-full-access` = sandbox `danger-full-access` + approval `never`。
  即默认配置里就存在一个单击即可同时废掉沙箱与审批的选项。
- `permission/preset` 事件是 durable log-only、不进模型 transcript（`:68`），
  存在的唯一理由是「当两个预设共享同一 bundle 时，保留用户选的是**哪一个**」。
  → 意图与后果分开记：后果由各 knob 事件记，意图由本事件记。**对审计极有价值的区分**。

#### `attachment.md`（116 行，全读）—— 「先落盘再落账」的干净范例

- **持久化先于事件**（`:5`、`:7`）：「the service publishes an immutable content-addressed reference
  **only after the object is durable**」；「Once the host accepts a user message, its images move below
  `<DSH_HOME>/attachments/v1` **before the user event is appended**. Structured model image output
  follows the same **persist-before-event** rule.」
  → 直接对应证据链：**先把证据本体固化，再写引用它的账**。反过来会产生指向不存在对象的账目。
- **事件里绝不放易失引用**（`:5`）：session 事件与模型可见的 `ImageBlock` 里只有引用与元数据，
  「never a browser object URL, host temporary path, provider URL, or base64 payload」。
  → 四类被点名禁止的东西，都是"当时能解析、事后解析不了"的引用。
- **内容寻址但标识不透明**（`:13`）：后端目前发 `sha256:<digest>`，
  但「consumers must **neither parse that representation nor derive a filesystem path** from it」。
  → 内容哈希用于完整性，不用于寻址约定。本项目的证据哈希应同样禁止被当路径用。
- **读时重校验，不信任已记录的元数据**（`:49`、`:111`）：
  「every authoritative read **still re-checks digest, media signature, dimensions, and metadata**
  against the object」；`readImage` 「returns bytes only after integrity verification」，
  验证失败抛 storage error。→ fail-closed，记入 §5.1。
- **声明与验证分离**（`:59`、`:29`）：`SaveImageAttachment.mediaType` 是
  「Caller-declared media type, **checked against fully decoded bytes**」，
  而 `ImageAttachmentRef.mediaType` 是「Media type **verified from the stored bytes**」。
  → 同一字段名，输入侧叫"声明"，输出侧叫"已验证"。**类型层面区分未核实与已核实**。
- **批量的全有全无**（`:72`）：`validateImage()` 跑同一套准入检查但不落盘，
  「batch callers validate every member through it **before saving any member**,
  so validation rejection **leaves no partial objects behind**」。
  → 先全验后全提交。对应我们的批量抽取：一份年报若有一页抽取失败，不应留下半份证据。
- **诚实标注未做**（`:72`，§5.3 正面）：「The service is **deliberately retention-neutral**...
  reference-aware garbage collection is **deferred** rather than tied to any one session's deletion.」
  → 写明"这件事我没做，且是故意没做，理由是 resumed/forked 会话可能共享对象"。

#### `session-reference.md`（109 行，全读）

- **入队前快照**（`:102`）：`prepare()` 「**Snapshot all references before enqueue** and return
  one **aggregated durable context**」。→ 跨会话引用被固化成不可变快照，而不是活链接。
  对证据链的直接含义：**引用外部材料必须固化当时内容**，否则事后复核看到的是变化后的源。
- **检索面被刻意收窄**（`:23`）：候选的 label 用最新会话标题，
  但「filtering still searches **only session id and cwd** and **never transcript text**」。
  → 显示用富信息、检索用窄信息，避免通过检索接口把 transcript 内容泄出去。
- **跨会话内容被标记为不可信**（`:5`）：包契约里包含「the **untrusted** model prompt」。
  → 引入的外部上下文自带不可信标签，而不是与本会话内容平权混入。
- **失败被分成 7 个稳定错误码**（`:59-67`）：`INVALID_CONFIG` / `INVALID_REFERENCE` /
  `SELF_REFERENCE` / `TOO_MANY` / `READ_FAILED` / `BUDGET_EXCEEDED` / `CANCELLED`。
  注意 **`READ_FAILED` 是一个错误码而不是"跳过这个引用"**——读不到源会话是失败，不是降级继续。
  记入 §5.1。

#### `README.md`（56 行，全读）—— 分母确认 + 一条自证机制

- 表格逐行列出 46 个子系统页，与 §1.1 我数出的英文 `.md` 数量一致（含本 README）。**分母核对无误**。
- `:55` 记录第二条可执行自证（第一条是 §3.B 的 `verify-cordis-catalog`）：
  「Type declarations and their JSDoc on these pages are **source-equivalent and drift-checked by
  `pnpm run verify-type-equiv`**... Ordinary blocks preserve **complete declarations**;
  `public-api` blocks preserve **body-stripped public class declarations**.」
  → 文档里 ```ts type-equiv``` 块与源码不一致会被 CI 抓。这解释了为什么本轮引用的字段集可以当字段集用：
  **它们不是手抄的摘要，是被机器比对过的完整声明**。§5.3 正面样本。
  同时也界定了我的断言边界：`type-equiv` 块可下断言，散文段落不受此校验保护。

#### `user-questions.md`（179 行，全读）—— 「不靠顺序推断语义」

- **`approve` 按名不按位**（`:41-43`）：`AskUserQuestionIntent` 的 `approve` 字段是
  「The option label that approves the plan; every other option declines it.
  **Named rather than positional so no UI infers the verdict from option order.**」
  → 直接可抄：审批/确认的肯定项必须**具名**。靠"第一个选项是同意"这种约定，
  在任何一次 UI 重排后都会静默反转语义。
- **运行期补齐类型表达不了的约束**（`:25`）：「`ask()` **rejects the two assertions no type can carry**:
  an `approve` naming none of its own question's options, and an intent on a question with no `detail`.」
  → 这句话本身是方法论：**先承认类型系统的边界，再在唯一入口处做运行期拒绝**。
  不是"类型保证了所以不用查"。
- **呈现意图不改协议**（`:25`、`:29-34`）：「An intent changes presentation only —
  a UI honouring it answers with **the same option labels** a generic UI would send,
  so the caller reads the same answer fields either way」；不认识 tag 的 UI 回退到通用选项列表。
  → 增强呈现与答案编码解耦，旧 UI 不会因为不认识新意图而给出格式不同的答案。
- **宁可抛错也不永久阻塞**（`:170-173`，fail-closed）：`ask()` 抛
  `CALLER_NOT_LIVE`（传入的 agent 不是注册表里那个确切的活实例）或
  `DELEGATED_CALLER`（该活 agent 被另一个 agent 拥有），理由原文：
  「an owned child **has no human answerer and would block forever**」。
  判据是「**Runtime ownership, not durable session lineage**」——
  用运行时所有权而不是持久化血统来判断"有没有人能回答"。
  → 对本项目：需要人工确认的环节，在无人可确认的运行形态（批处理、子 agent）下必须**立即失败**，
  不能挂起，更不能自动放行。
- **"跳过"是可表达的第三态**（`:89`）：「A UI may also use an item with **empty `selected` and no `custom`**
  to preserve a **skipped** question in an otherwise completed batch.」
  → 批量提问中"这一条没答"与"这一条答了空"被区分开。

#### `commands.md`（188 行，全读）—— 一处**不对称**的落账失败处理

- **先开账再执行**（`:144-151`）：「`command/run` is appended **before the handler is invoked**
  and `command/done` **after settlement** (a thrown or aborted handler settles as `kind: 'error'`)」。
  → 与 `session-title` 的"发请求前先记请求"同构。**执行前落账是这个仓库的通行做法，不是个例**。
- **⚠️ 不对称的失败策略**（`:149-151`，同时进 §5.1 与 §5.2）：
  「A `command/run` append failure **fails the execution loud**;
  a `command/done` append failure **on the handler-failure path is contained**
  so the handler's own error stays the reported failure.」
  → 开账失败 = 硬失败（没记上就不许做）；结账失败在"本来就已经失败"的路径上被吞，
  理由是不要用记账错误掩盖真正的业务错误。**这个取舍是有道理的，但后果必须认**：
  日志里会出现**有 `run` 无 `done` 的悬挂记录**，复核方必须把"悬挂"当作一种独立状态处理，
  不能默认"没有 done 就是没执行"。落到本项目：证据链的收尾写入失败要留下可识别的悬挂痕迹。
- **准入未命中不记账**（`:150`）：「Admission misses (syntax or unknown name) **log nothing** —
  they never entered a handler.」→ 记账边界 = 是否进入了执行体，定义清晰且可复核。
- **⚠️ 一个可关掉原始输入记录的开关**（`:34-39`，记入 §5.4）：
  `recordInput?: boolean`「Whether `command/run` records `rawInput`. **Defaults to true.**
  A command whose domain event owns the payload sets this **false** to avoid duplicating
  that payload in the session log.」
  → 默认记录，可由命令作者关闭。理由正当（避免与领域事件重复），
  但它确实是一个**由被记录方自己控制的审计开关**——谁被审计谁决定记不记。
  本项目若引入类似开关，必须由记账方而非被记账方持有。
- **结构化回指而非文本解析**（`:75`）：`sourceEventSeq` 只在成功时出现，指向本会话日志中更早的
  非命令事件，`command/done` 持久化同一引用，「so a client can combine the command lifecycle
  with that domain projection **without parsing `text` or relying on adjacent rows**」。
  → 两条明确否定的反模式：解析人类可读文本、依赖相邻行。
- 影子机制（`:115`）：通过 agent 上下文注册的命令**遮蔽同名全局命令**。
  → 又一处"同名可被就近覆盖"的结构，与 §2(f) 的 `ctx.isolate` 同类。
- `commands/change` 是 `emit`（`:174`）：「Observer failures are contained and
  **cannot veto the registry mutation**」——观察者不能否决。与 §2 的结论一致。

#### `web-server.md`（109 行，全读）

- **诚实披露"没有认证"**（`:41`，§5.3 正面 + §5.4 风险）：`host` 只接受
  `127.0.0.1`（默认姿态）与 `0.0.0.0`（deliberate network exposure），
  「**there is no TLS, auth, or origin policy**, so a non-loopback bind
  **exposes the server to that network**」。
  → 一个字符串配置项即可把无认证的服务暴露到网络。文档把后果写明了，
  但这仍是"一个配置项能削弱安全姿态"的典型。
- **组合期冲突硬失败**（`:70`、`:78`、`:88`）：重复 `(kind, path)` 抛错、
  重复 upgrade 路径抛错（「one socket can have only one protocol owner」）、
  fallback 座位第二次注册抛错（「two fallbacks cannot compose」）。
  → 三处都选了"抛错"而非"后者覆盖前者"。**冲突不是可静默解决的**。记入 §5.1。
- **启动窗口期行为被明确定义**（`:61`）：fallback 未被认领前，
  「the fallback handler answers anything not yet claimed during startup with **404 until its owner registers**」。
  → 半初始化状态有确定语义，而不是未定义行为。
- **⚠️ 一处 404→200 的转换**（`:27`，记入 §5.2）：SPA dist server
  「**any miss falls back to `index.html` with HTTP 200** (SPA routing)」。
  这是 SPA 惯例，但形式上就是"找不到"被回成"成功"。
  同页其它分支反而是严的：非 GET/HEAD 为 405，越出 dist root 为 403，未知扩展名发 octet-stream。
- 请求处理抛错「is logged as a warning and answered **400** — or the socket destroyed when
  headers are already out — **never a process exit**」（`:47`）。
  监听失败则相反：「a listen failure (EADDRINUSE…) **rejects initialization**」（`:45`）。
  → 启动期失败硬、请求期失败软，边界划得很清楚。

#### `settings.md`（311 行，全读）—— 四件事全部命中，本轮信息密度第一

**(1) 「在写入点拒绝，而不是存下来让消费者静默失效」——这是本项目关切的正面解法**（`:29-48`）：
`SettingsRegisterOptions.validate` 的 JSDoc 原文：
> Reject a resolved section the owner could not act on, for constraints its schema cannot express...
> **Throwing here refuses the *write* that produced the value**, so a caller learns at
> `update`/`replace`/`mutate` **instead of storing something that would silently disable the owner**.

→ "存了一个会让消费者悄悄失效的值"被识别为独立的失效模式，并在写入路径上堵死。
`dsh-llm-pi-ai` 的实例（`:52`）：拒绝一个它服务不了的 provider profile，
「rather than storing one that **would disable every route in its namespace**」。

**(2) 为什么跨字段校验不并进 schema**（`:36-38`）——职责分离论证，值得抄：
> Kept separate from the schema because the schema is also **what a configuration surface renders**
> and **what an absent section resolves through**; folding a cross-field check into it would change both.

→ 一个校验器若同时承担渲染与缺省解析，就不能自由加约束。**校验职责必须与呈现/默认值职责分开**。

**(3) ⚠️ 一处明确且有理由的 fail-open，但代价很实**（`:40-45`，记入 §5.2）：
> Once the owner is registered, a stored section that fails this **keeps the namespace's
> last good value and warns**, exactly as a schema failure does, so an externally edited document
> **cannot strand a running owner**. At registration there is no last good value yet,
> so a stored section that already fails **rejects the registration itself**.

→ 同一个校验，**注册时硬失败、运行中软降级**。理由（外部编辑不能搞死运行中的组件）成立，
但后果是：**用户把配置改错了，配置界面显示的是新值，实际生效的是旧值，唯一的信号是一条 warning**。
这是"失败被静默转成正常值"的一个变体——不是转成默认值，是**转成上一个好值**，
比转成默认值更难被发现（因为看起来一切正常）。
本项目若有类似机制，必须让"当前生效值 ≠ 文档中的值"成为一个**可查询的显式状态**，而不只是日志。

**(4) ⚠️ 脱敏是"MUST"但实现成可选参数，默认不脱敏**（`:146-152`，记入 §5.4）：
> Strip `role('secret')` fields... **Every wire surface MUST pass this**;
> the verbatim default exists for same-process configuration UIs only.

→ `redactSecrets?: boolean`，不传即不脱敏。一个靠调用方记得传的门禁不是门禁。
与 §3.A `session-telemetry` 的"默认不脱敏"是同一个模式在两个子系统重复出现。

**(5) 但对"部分视图"的处理是正面样本**（`:129-141`）：`SettingsPathOp` 存在的唯一理由：
> a wholesale `replace` rebuilt from a redacted document **silently deletes every secret
> the wire never returned**.

→ 他们识别出"拿着不完整视图做整体替换会静默删掉看不见的字段"，于是提供**路径寻址写**，
并在 `mutate` 的 JSDoc 里点明「cannot delete fields it never saw」（`:245`）。
对应本项目：任何"拉下来改完再整体写回"的编辑流程，都会静默删掉当事人没权限看到的部分。

**(6) 「值没变但来源变了」被当成必须广播的事件**（`:265`）——对审计极重要：
`settings/document-updated` 与 `settings/updated` 是两个事件，后者 deep-equal 门控，前者不：
> configuration surfaces... must learn that a field went from **inherited to overridden
> (same resolved value, different meaning)** and that their held revision is stale.

→ **同一个值，来源从"继承默认"变成"用户显式覆盖"，是一次实质变更。**
落到 finaudit-agent：某个口径的取值从"内置默认"变成"人工指定为同一数值"，
必须留痕，不能因为数值没变就不记。这条我之前没想到。

**(7) 乐观并发也是可选的**（`:223-225`）：`expectedRevision?: number`，
匹配不上则 `SettingsConflictError`「refused rather than applied over the writer that landed first」。
但**不传就不检查**——又一个默认关闭的保护。

**(8) `applies` 明说自己不是机制**（`:54`，§5.3 正面）：
「`applies` is **a UI hint, not a mechanism**: a `restart` owner simply never watches」。
→ 不假装一个展示字段有强制力。

**(9) INVARIANT-async 陷阱在这里一字不差地重复**（`:288`）：
与 §3.A `credentials.md:114` 完全相同的措辞——「invariant checks on this event
**must not be async functions**」。
→ **更正/加强上一节的判断**：这不是 credentials 一处的特例，而是这套事件系统的**通用语义**。
凡是 `emit` 模式的事件，不变量检查写成 `async` 就永远不会向上传播。
一个跨子系统重复出现的语义陷阱，说明它是框架级的，且**只能靠人记住**——没有类型或 lint 拦它。

#### `storage.md`（230 行，全读）—— 「内存永不领先于介质」

- **★ 写序纪律，本轮最该直接抄的一条**（`:98`）：
  「Every write — `put`, `delete`, `update`, `global.set` — queues on one per-domain chain and
  **reaches backend durability first, then mutates memory, then emits `domain/changed`**;
  a **rejected backend write leaves memory untouched, so reads never diverge from the medium**.」
  → 落盘 → 改内存 → 发事件，顺序不可换。写失败则内存不变，因此**读到的永远是真实落盘的值**。
  与 `attachment` 的 persist-before-event、`commands` 的 run-before-handler 是同一族纪律。
- **哨兵值与合法值冲突在声明期就被禁止**（`:67`）：`defineDomain` 会拒绝
  「a global schema that accepts `null`」，理由是
  「`null` is the medium's **"never written" sentinel**, so a stored nullable global
  **could not round-trip**」。
  → 这是 `credentials` 的"空值即缺失"在**类型声明层**的对应物：
  既然介质用 `null` 表示"从未写过"，就不允许业务把 `null` 当合法值存进去。
  **凡是用某个值当哨兵，就必须在 schema 层禁止该值作为业务值。** 直接可抄。
- **打开即全量校验，并报出具体位置**（`:102`、`:174`）：`open(spec)` 的严格序列中，
  「load and **validate every stored record** against the spec's zod schemas
  (`invalid-record` **with the offending table and key**)」。
  → 不是懒校验、不是抽样，是全量；且错误定位到表与键。fail-closed，记入 §5.1。
- **能力缺失硬失败**（`:33`、`:102`）：backend 不支持某类数据就省略该 facet，
  「**resolution fails loud instead**」（`facet-unsupported`）。
  `form(form)` 在拥有它的插件加载前抛 `form-not-mounted`，
  「assemblies order plugins accordingly **rather than silently deferring**」。
  → 两处都拒绝"先放行、以后再说"。
- **没有迁移就直说没有**（`:47`，§5.3 正面）：版本不符 `version-mismatch`，
  解析不了 `malformed-medium`，括号里写「**no migration, pre-release stance**」。
- **契约有可执行的一致性套件**（`:47`）：`backend.ts` 是「normative clause-by-clause contract」，
  且 `tests/contract.ts` 的共享套件「**checks every clause against each backend**」。
  → 第三条真实自证机制（前两条见 §3.B `verify-cordis-catalog`、README `verify-type-equiv`）。
  **契约不是散文，是逐条可跑的测试**，且每个实现都要过同一套。
- **同一问题在两个子系统里选了不同强度**（值得注意的不一致）：
  `settings` 的 resolved value 是「**deep-frozen** snapshots」（`settings.md:63`），
  而 `storage` 返回的是「the **stored objects themselves, not copies** —
  replace via `put`/`update`, **never mutate in place**」（`storage.md:98`）。
  → 前者有机制保护，后者只有文档约定。**一条只靠注释维持的不变量迟早会破。**
- `domain/changed` 是提交后通知（`:125`）：「the commit point **has passed** at emission,
  so a synchronously throwing listener is contained with a logged warning
  rather than rejecting the already-durable write」。
  → 与 §2 结论一致：**事件监听器不能当事务参与者，因此不能当闸门。**
- 诚实标注两处未做（`:125`，§5.3 正面）：事件「**in-process only**；
  cross-process change push is a **recorded limitation**」。

#### `workflow.md`（279 行，全读）—— 本轮最接近「真闸门」形状的一篇

- **★ 策略参数对被执行体不可见不可改**（`:13`）：调用方可以为一次运行指定
  `subagentProvider` 与更低的 `maxTotalAgents`，但
  「**the script cannot observe or replace either policy**」。
  → 这直接回答了 §2 遗留的问题："闸门该长什么样"。
  答案不是"排在监听器链前面"，而是**把约束做成被约束者根本拿不到的参数**。
  脚本无法读到自己的上限，也就无从绕过。
- **★ 身份校验先于任何代码求值**（`:13`）：`meta` 与 `args` 是纯 JSON DATA，
  「the engine validates `meta` against its schema and **rejects loud BEFORE anything runs**
  — **no script text is ever evaluated to obtain it**」。
  → 元数据绝不从待执行的代码里求值取得。对应本项目：
  **口径声明、数据来源标注必须是外部提供的结构化数据，不能从被分析的内容里推导出来**，
  否则"声明"与"被声明物"之间就没有独立性可言。
- **★★ `fatal` 错误不得溶解进失败值域**（`:116`）——本轮反"静默转正常值"的最强样本：
  > Hook misuse inside a script — bad arguments, unknown/deferred `agent()` options,
  > a schema outside the structured-output subset, a tripped cap, a seam start failure,
  > cancellation — throws a `WorkflowError` with `fatal: true`.
  > The `parallel()`/`pipeline()` combinators **RE-THROW fatal errors instead of mapping the item to `null`**:
  > a typo'd option **must kill the script loudly, never dissolve into something that reads as
  > an ordinary child failure**. The per-item `null` is reserved for child-run failures... 
  → **把"数据失败"与"程序错误"分进两个通道**：前者可以被聚合成 `null` 继续跑，
  后者必须穿透组合子把整个脚本打死。
  落到 finaudit-agent：某页 PDF 抽不出表 → 记为该页失败，可继续；
  但口径名拼错、准则编号不存在、schema 越界 → **必须炸**，
  绝不能记成"该口径无数据"——那会让一个拼写错误看起来像一条真实的空结论。
- **★ 落账失败后停写整条链，保证日志是合法前缀**（`:124`）：
  「The **first append failure disables later writes for that run**, so the log remains
  **empty or a legal continuous prefix** and the tool result is unchanged.」
  → 比"尽力继续写"高明：**有洞的日志比截断的日志危险得多**，因为无法判断中间少了什么。
  直接抄进证据链：一旦某条证据写入失败，该证据链停止追加，留下可识别的截断，而不是继续记后面的步骤。
- **★ 区分"尾部缺失"与"中间损坏"**（`:126`）：`dsh-tool-workflow/invariant`
  「validates the same protocol **before live commit and when a Session is loaded**」，
  五条：一次 run 一个 start、成员序号为正且唯一、成员起止配对、run 结束时无未闭合成员、
  run 结束后无更新。关键判据：
  「A missing member ending or run ending **at the log tail** is
  **valid interruption evidence rather than corruption**.」
  → 这正好补上 §3.A `commands.md` 留下的悬挂 run/done 问题：**悬挂只在日志尾部合法**。
  这是一条可以直接落地的复核判据。
  另注意：**同一套不变量在"提交前"和"加载时"各跑一次**——写时校验 + 读时校验，两端都不信任。
- **观察者拿不到控制权，也拿不到可变别名**（`:120`）：
  所有 `workflow/*` 事件负载以 `WorkflowRunInfo`（id + meta）开头，
  「**never the live `WorkflowRun`**, so a subscriber **cannot gain `cancel`/`dispose`**」；
  `workflow/end` **故意不带 result value**，理由是
  「a listener observing outcomes **must not receive a mutable alias** of the caller's result」；
  且「every listener receives **its own payload clone**」。
  → 补充 §2：这个仓库是**清楚知道**"观察者不该有权力"的，并且在数据层面执行了（快照、克隆、剥离句柄）。
  所以 §2 的结论应精确表述为：**不是作者不懂，而是事件系统在架构上就不适合承载强制力，作者选择在别处强制。**
- **结果永不 reject，用封闭 stopReason 表达**（`:65`、`:95`）：
  `stopReason: 'completed' | 'cancelled' | 'error'`（closed union，consumers may exhaust it），
  非 `completed` 时携带 `error`，且消费者
  「maps it to an `isError` tool result **rather than reporting partial output as success**」。
  `result` 不 reject、`cancel` 后在有界宽限内**强制结算**、`dispose()` 「never hangs on a stuck script」。
  → "不会卡死"被写成契约的一部分，而不是希望。
- **⚠️ 一处降级了但没有在类型上标记的字段**（`:82-89`，记入 §5.2）：
  `agentsStarted` 「On a graceful settlement this is the **script-side count**...;
  on a termination path (grace force-settle, worker death) it **degrades to the host-observed count**
  — calls queued inside a terminated script are **unknowable** then.」
  → 语义在两条路径下不同，文档诚实说明了，**但类型仍然只是 `number`**。
  消费者拿到 42 无法知道这是精确值还是降级值。
  对比 §3.A `sandbox.md` 的 `SandboxEnforcement = 'full' | 'partial'`——那里把降级编码进了返回值，这里没有。
  **同一仓库里对"部分可信的数值"处理不一致**，这是本项目要避免的：
  凡是可能降级的计数/结论，降级标记必须与值同行。
- 一个小而重要的一致性纪律（`:128`）：UI 折叠时
  「preserve exact strings, including the distinction between **an omitted phase and `''`**」。
  → "缺失 vs 空串"在本轮已第三次出现（`credentials` 空值即缺失、`storage` null 哨兵、这里）。
  **这个仓库把"空 / 缺失 / 未写"的区分当成一等问题。**

#### `extensions.md`（365 行，全读）—— 但内容 98% 是生成物，散文只有 6 行

**如实标注读取边界**：本页 `:1-6` 是全部手写散文，`:7-364` 全是 `gen-cordis-catalog` 生成的
方法签名与 JSDoc。因此：
- **我知道方法名与参数名，不知道请求/收据类型的字段集。**
  `DynamicCordisDefineRequest` / `DynamicCordisRunResponse` / `DynamicCordisInventoryRow` /
  `DynamicCordisReference` / `CordisInspectProviderManifest` 等在本页**只出现类型名，没有字段展开**，
  我不猜。沙箱行为与包生命周期本页明确外包给
  `packages/extensions/README.md`（**我没读，见 §6 未读清单**）。

在签名层面能确证的几点：
- **⚠️ 一次审批可覆盖此后所有版本**（`:116-119`，记入 §5.4）：
  `runHostHalf(..., approveFutureVersions: boolean)`；
  `run()` 的 JSDoc（`:98-99`）写明「An unauthorized Client Package waits for approval;
  **Plugin-wide authorization covers later versions**」。
  → 即：用户看了 v1 的代码点了同意，v2/v3 的代码**无需再次审批即可运行**。
  这是"审批一次、授权一类"的经典弱化。对本项目的意义：
  **人工确认的粒度必须与被确认物的粒度一致**——批准某一版口径规则，不等于批准该规则的后续修订。
- **源码与元数据分层暴露**：`listPlugins` 返回「**source-free** Plugin summaries」，
  `inspectPlugin` 「**without returning Package source**」，
  只有 `inspectPackage` 返回「Package metadata, **source**」（`:201-222`）。
  → 元数据可广泛读取，源码需显式且更窄的调用。
- **陈旧运行被拒 / 被忽略**：`invoke` 「Invoke an active Host method **while rejecting stale Client runs**」（`:245`）；
  但 `reportRenderFailure` 返回「Null after recording **or ignoring a stale report**」（`:230`），
  `reportClientGuardFailure` 同样「after reporting **or ignoring a stale/startup failure**」（`:240`）。
  → **调用路径拒绝陈旧，报告路径静默丢弃陈旧。** 后者记入 §5.2：
  一个来晚了的失败报告会被无声吃掉，调用方拿到 `null` 无法区分"记下了"与"扔了"。
- **竞态用"首个有效者胜"解决**：`resolveClientQuery`「Accept the **first valid** Client response
  for a pending query」，返回 `CordisInspectResolveAck`「whether this response **settled the still-pending query**」（`:54-60`）。
  → 至少返回值告诉调用方"你是不是那个赢家"，没有把败者伪装成成功。
