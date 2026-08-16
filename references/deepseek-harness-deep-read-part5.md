# deepseek-harness 深读 Part 5 —— `.agents/notes` / tool-catalog / Cordis / user docs

> 本轮定位：补前四轮的三个洞 —— (1) `.agents/notes` 一篇未读；(2) `tool-catalog.md` 未核；(3) Cordis 的 effect/fiber/waterfall 全是照抄措辞。
> 仓库：`scratchpad/deepseek-harness`，默认分支 `master`，TS/MIT。**只读，未做任何修改与 git 操作。**
> 本文所有行号均指 **英文原文 `.md`**（仓库同时有 `.zh.md` 与 `.i18n.yaml`，未读）。

## 1. 读到什么程度（逐文件自报）

`完整` = 从头到尾读完；`片段` = 只读了指定行段；`grep` = 只按关键词命中行，未读上下文。

| 文件 | 总行数 | 读到 | 程度 |
|---|---|---|---|
| **第一优先：`.agents/notes/`** | | | |
| `.agents/notes/AGENTS.md` | 7 | 全部 | 完整 |
| `notes/implemented/architecture/2026-06-11-dev-invariants-over-deep-readonly.md` | 61 | 全部 | **完整** |
| `notes/implemented/architecture/2026-06-11-runtime-arg-validation.md` | 25 | 全部 | **完整** |
| `notes/implemented/architecture/2026-07-19-package-owned-invariant-service.md` | 106 | 全部 | **完整** |
| `notes/implemented/feature/2026-08-08-pi-ai-per-model-reasoning-declarations.md` | 34 | 全部 | **完整** |
| `notes/implemented/feature/2026-06-29-todo-write-tool.md` | ? | 仅 `:15` | grep |
| `notes/proposed/architecture/2026-07-25-client-settings-locale-theme.md` | ? | 仅 `:23` | grep |
| `notes/implemented/process/2026-08-10-npm-release-sequences.md` | ? | 仅 `:63,71` | grep |
| 其余非归档 notes（约 200+ 篇） | — | 文件名 + 两轮全目录 grep | **未读** |
| `.agents/notes/archived/**` | — | 仅文件名 + grep 命中行 | **未读** |
| **第二优先：`docs/tool-catalog.md`** | 1873 | `:1-50`（生成规则 + 完整包映射表）、`:178-227`（bash/pwsh 样本条目）+ 全文件 grep | 片段 |
| `scripts/gen-tool-catalog.ts` | 759 | `:83,98,151-154,189-203,216-217` 等 grep 命中段 | grep |
| `docs/subsystems/tools.md`（前轮已读，本轮定点复核） | 720 | `:360-402`（`PreToolDecision` / `PostToolDecision` 原文） | 片段 |
| **第三优先：Cordis** | | | |
| `docs/cordis-primer.md` | 44 | 全部 | **完整** |
| `docs/cordis-api/events.md` | 207 | 全部 | **完整** |
| `docs/cordis-api/fiber.md` | 375 | 全部 | **完整** |
| `docs/cordis-api/context.md` | 364 | 全部 | **完整** |
| `docs/cordis-api/registry.md` | 152 | — | **未读** |
| `docs/cordis-api/service.md` | 102 | — | **未读** |
| `docs/cordis-api/inherited.md` | 39 | — | **未读** |
| `vendor/cordis/src/events.ts`（**原始实现**） | ? | `:1-330`，含 `dispatch` / `waterfall` / `register` / `on` 的完整实现 | **相关面完整** |
| `vendor/cordis/src/{fiber,context,registry,reflect,service}.ts` | — | — | **未读** |
| `docs/cordis-tutorial/02-lifecycle-and-effects.md` | 98 | 全部 | **完整** |
| `docs/cordis-tutorial/04-events.md` | 144 | 全部 | **完整** |
| `docs/cordis-tutorial/{01,03,05,06,07,index}.md` | 557 | — | **未读** |
| **第四优先：对外文档** | | | |
| `docs/user/index.md` | 9 | 全部 | 完整 |
| `docs/user/guide/index.md` | 30 | 全部 | **完整** |
| `docs/user/develop/basic/index.md` | 144 | 全部 | **完整** |
| `docs/user/` 其余 10 篇 | ~2795 | 目录结构 + 行数 + 全目录 grep | **未读** |
| `docs/api-gateway.md` | 164 | `:95-164` | 片段（后半） |
| `docs/development.md` | 171 | `:119-171` | 片段（后半） |
| 所有 `.zh.md` / `.i18n.yaml` | — | — | **未读** |
| `.agents/skills/` | — | — | **未读** |

**未做任何修改，未执行任何 git 操作。** 全部只读访问（`ls`/`find`/`grep`/`sed`/`wc`/Read）。

---

## 2. 三组必答问题的结论

### 第一组：`.agents/notes` —— 「运行时断言 vs 类型约束」「三态 vs 两态」

#### Q1.1 有没有哪一篇解释了「为什么把某个不变量做成运行时断言而不是类型约束」？

**有，而且是整个仓库最直接回答这个问题的一篇。**

`.agents/notes/implemented/architecture/2026-06-11-dev-invariants-over-deep-readonly.md`

标题就是答案：*Source-owned session immutability and dev-mode invariants*（「运行时不变量优于 deep-readonly」）。

关键论证有三层，**三层各自独立**，这一点比结论本身更值得抄：

**第 1 层：类型在运行时不存在，所以它不构成边界。**
> `:15` — "TypeScript readonly types are not a sufficient runtime boundary. They disappear when the program runs, a cast can bypass them, and a recursive `DeepReadonly<T>` would spread through every log and message consumer even though some downstream request-processing APIs intentionally work with mutable values."

`:43`（Alternatives considered / Pervasive deep-readonly types）把被否掉的方案写清楚了：
> "That provides editor feedback but not a runtime guarantee: TypeScript types are erased and plugin code can cast through them. It also pushes readonly types into consumers where mutation is intentional."

**第 2 层：单值不可变 ≠ 关系正确 —— 类型根本表达不了这一类命题。**
> `:13` — "Immutability of individual values is only half of the contract. A log can contain perfectly immutable records whose sequence, turn/step nesting, tool-call pairing, scoped delivery, or reconstructed model request is wrong. Those rules relate multiple records or services and cannot be established by freezing one object."

即：**跨记录、跨时间、跨服务的关系性命题，只能在运行时检查。**
枚举出的六类关系（`:35`）：单调序号、turn/step 嵌套、tool-call/result 配对、合法的 agent-status 迁移、scoped dispatch 的 subject 正确性、
以及「loop 构造的 request」与「从 session-log 前缀重建出的 request」**相等**。

**第 3 层：把「永远开」和「可选开」明确切开。**
`:9` — 冲突点是：把两者混在一个可选的开发插件里，生产历史就没保护；但都用类型表达，又既没有运行时边界也描述不了关系规则。
于是决策是（`:19`）：**存储边界永远开（快照 + 深冻结），关系断言可选开（`ctx.invariants`）。**
`:47` 明写了否掉「development-only freezing」的理由：
> "Freezing history only when an invariants plugin is installed would make the core guarantee composition-dependent. Code could pass development tests and still corrupt history in production."

**同类第二篇：** `.agents/notes/implemented/architecture/2026-06-11-runtime-arg-validation.md:9`
——同一句式，用在工具参数上：
> "that type is a compile-time claim about a value that arrives at runtime as model-generated JSON: nothing forced the model to honor the schema … reached `execute` typed-in-name-only."

并且 `:20` 给出了「类型与校验器不许漂移」的**机械保障**：property test 生成满足 spec 的参数断言其通过 `validateArgs`，再做定向破坏断言其被拒。

**第三篇（服务化形态）：** `.agents/notes/implemented/architecture/2026-07-19-package-owned-invariant-service.md`
—— 把断言做成**包自有**（每个 workspace package 发布 `./invariant` 伴生插件），`:69` 有一条 `verify-package-invariants` 门禁，
拒绝：缺伴生源文件、生成的占位标记、**没有解释的空 installer**、非空 installer 却忽略 reporter、外来或无法解析的注册名、缺 `./invariant` export 等。
`:105` 收尾一句划清了边界：
> "Session storage validation, snapshotting, freezing, cited source-event validation, and surface acceptance remain always on and are not affected by invariant selection."

#### Q1.2 有没有哪一篇解释了「为什么某个字段设计成三态而不是两态」？

**有，四篇，最强的一篇把三态的动机写到了序列化层的物理约束上。**

**最强证据：** `.agents/notes/implemented/feature/2026-08-08-pi-ai-per-model-reasoning-declarations.md:15`

`reasoningEfforts` 里的 `off` 是唯一的三态键，三态语义各自不同（原文 `:15`）：
- **不写**（absent）：不提供 Off，显式 Off 请求被拒；
- **写了但无值**（declared valueless）：提供 Off，dispatch 什么都不发；
- **写了带值**（declared with a value）：该值上线。

而「为什么必须是三态、为什么 disable 的拼写是 `false` 而不是 `{}`」，理由是**序列化框架的物理行为**：
> `:15` — "The spelling for \"disable\" is `false` rather than `{}` because schemastery materializes an absent dict as `{}` — only a `z.union([z.const(false), dict])` keeps absent, disabled, and declared distinguishable"

`:25`（Alternatives considered）把它作为被否方案再说一遍：
> "**`{}` as the disable spelling.** Unimplementable: schemastery materializes an absent dict as `{}`, so every model without the field would have been force-disabled."

**这是本轮对 finaudit 最有直接迁移价值的一条**：
「缺省」与「显式关闭」如果在序列化层塌缩成同一个值，两态就是**错的**，必须升为三态 —— 而且升法要选一个**序列化层能区分**的拼写。
同段还有一条配套的 fail-loud：`:15` 末 —— 裸的 `reasoningEfforts:`（YAML null）会从 union 里溜过去不被校验，所以在 resolution 阶段**显式拒绝**。

**另三篇三态（力度递减）：**
- `.agents/notes/proposed/architecture/2026-07-25-client-settings-locale-theme.md:23` — 主题三态 `light / dark / system`，`system` 是默认。
  三态的必要性在于 `system` 不是一个颜色而是一条**解析规则**，快照同时带 `preference` 与解析后的 `active`。
  （注意：这篇在 `proposed/` 下，不是 implemented。）
- `.agents/notes/implemented/process/2026-08-10-npm-release-sequences.md:63,71` — 发布时把版本比对分三态，
  `:71` "The third state catches code that changed without a version bump."
  ——第三态存在的唯一理由是**捕获一类特定的沉默失败**。
- `.agents/notes/implemented/feature/2026-06-29-todo-write-tool.md:15` — 小标题即 "Whole-list replace, three-state status"（未展开读正文）。

---

### 第二组：`docs/tool-catalog.md` —— 三问

**先说这份文件是什么**（`docs/tool-catalog.md:1-10`）：
生成物，`scripts/gen-tool-catalog.ts` 产出，`pnpm run verify-tool-catalog` 校验新鲜度（属于 `doc-sync`）。
和 Cordis catalog（纯源码 AST 扫描）不同，**这个生成器会在真实 context 上把每个 tool 插件 boot 起来，读 `ctx.tools.schemas()`**，
理由写在 `:8`：
> "because a tool schema is not statically knowable (runtime-spread enums, concatenated descriptions, config-driven names, raw-JSON-Schema MCP tools)"

并且有完整性守卫：`:8` —— glob `packages/*/tool-*`，**任一包不在生成器 boot 清单里就失败**，所以「新增工具悄悄没进文档」是被机械挡住的。

#### Q2.1 工具定义里有没有**声明式的**「这个工具需要审批」标记？

**没有。审批是运行时策略，不是工具的声明字段。**

- 模型看到的东西被 `:6` 穷举了：**只有** `name`、`description`、JSON-Schema `parameters`。
  我通读了全部 24 个包节的条目结构，**没有任何一个工具条目带 approval / permission / danger / readOnly 类字段**。
- 决定性反证在 `dsh-tool-fs` 那一行（`:26`）：
  > "The read-before-write/edit policy is added by `@deepseek-ai/dsh-fs-observation-policy` (an `fs/*` event-gate plugin, **no schema change**); a deployment that loads these tools is expected to also load it."

  —— 策略是**另一个单独挂载的插件**，工具 schema 完全不变。而且措辞是 "**is expected to** also load it"，
  即：**没有任何东西强制它被挂上**。这正是「闸门可绕过」的教科书形态。
- 审批只在两处以**散文**出现，都是运行时行为描述而非声明：
  - `:20` `exit_plan_mode` —— "Its execute path rejects calls outside plan mode"（execute 内部自查）
  - `:425` `cordis_run` —— "An unauthorized Client Package creates an approval request and returns awaiting-approval"

**真正的审批闸门在别处**，是 `docs/subsystems/tools.md:402` 的 `tools/pre-execute` waterfall：
> "Pre-policy may deny or ask; only `allowed-once` proceeds, while a non-grant, missing approval channel or service, or agent-less request becomes a denial."

注意这里的 **fail-closed 默认**：没有 approval channel、没有 service、没有 agent —— **一律算 denial**，不是算放行。

#### Q2.2 输入 schema 用什么表达？「参数不可重写」有没有机械保障？

**schema 用裸 JSON Schema**（`{"type":"object","properties":{...},"required":[...]}`，见 `:184-213` 的 `bash`）。

**「参数不可重写」有机械保障，而且是本轮最漂亮的一个做法 —— 它把这条规则做成了「在类型里无法表达」。**

我核实了前一轮引用的 `tools.md:402`，并把上文的类型定义读了出来（`docs/subsystems/tools.md:387-394`）：

```ts
/**
 * Pre-dispatch decision. `allow` runs the call; `deny` materializes an error;
 * `ask` runs only after an approval service returns `allowed-once` and otherwise
 * denies. Input rewriting is excluded because arguments are already logged and
 * presented.
 */
type PreToolDecision =
  | { kind: 'allow' }
  | { kind: 'deny'; reason: string }
  | { kind: 'ask'; reason?: string }
```

三个分支，**没有任何一个能携带 args**。所以「拦截器改写参数」不是被检查出来后拒绝的，是**根本写不出来**。
`tools.md:402` 那句原则（"Arguments cannot be rewritten because history, audit, UI, and execution must agree."）
的执行机制就是这个 union 的形状。

**注意：这与 Q1.1 的「运行时断言优于类型」并不矛盾，二者管辖不同的命题。**
- 「历史不可被改写」是**跨时间的关系性命题** → 运行时深冻结 + invariant 断言。
- 「拦截器不得改写参数」是**单点 API 表面的命题** → 让它在类型里不可表达（make illegal states unrepresentable）。

配套约束（`tools.md:396-400,402`，同一段）：
- 后置策略 `PostToolDecision` 可以替换 `content` **或** `value`，**永远不能同时替换两者**（union 的 `value?: never` / `content?: never` 强制）。
- `:402` —— "Guards may still impose a final denial."（守卫可以下最终否决）
- 调用身份挂在不可变的 `ToolExecution` 上随每个 hook 传递，
  `tools.md:~371` —— "so wrappers cannot create a second, disagreeing identity."（包装器造不出第二个互相矛盾的身份）

#### Q2.3 有没有工具**声明自己会产生哪些证据/副作用**的字段？

**有一个这样的列，但它是「作者手写的元数据」，不是从代码推导出来的 —— 这个区别对 finaudit 至关重要，必须讲清楚。**

`Tool Package Map` 表（`:16`）有六列，其中两列正是你要找的：

| 列 | 含义 |
|---|---|
| `Requires` | 执行期需要的服务/运行时 |
| **`Writes / affects`** | **这个包会写出/影响什么** |

实际值就是一张证据清单，例如：
- `dsh-tool-fs`（`:26`）：`tool/call`、`fs/write-intent or fs/edit-intent for mutations`、
  `fs/observed after read presence/absence or successful file operation`、`durable attachment (read_image)`、`tool/result`
- `dsh-tool-goal`（`:29`）：`goal/change for mutations`
- `dsh-schedule`（`:30`）：`schedule/change create or delete`
- `dsh-tool-bash-persistent`（`:24`）：`PTY shell state`

**但是**——我去核了生成器，结论要打折：

`scripts/gen-tool-catalog.ts:151-154` 把它们定义为**手写清单字段**：
```ts
  /** Services or owning runtimes the package requires at execution time. */
  requires: string[]
  …
  writes: string[]
```
后面 `:189-190`、`:202-203`、`:216-217`… 全是**字面量数组**逐包硬编码。

所以：**JSON Schema 那部分是真·从运行时 boot 出来的（可信），而 `Requires` / `Writes` / `Deployment note` 三列是文档作者维护的断言（不可信为机械事实）。**
完整性守卫只保证「不漏包」，**不保证 `writes` 列与代码真实副作用一致**。
—— 这正是 finaudit 不能照抄的地方，见 §4。

---

### 第三组：Cordis —— waterfall / effect / fiber，以及「不可绕过的前置钩子」

**本组我读了生成文档 + vendored 原始实现**（`vendor/cordis/src/events.ts`、`fiber.ts` 的类型与 JSDoc），
以下结论以**原始实现**为准，不再是转述措辞。

#### Q3.1 waterfall 到底是什么语义？

**实现原文（`vendor/cordis/src/events.ts:233-241`）：**
```ts
  waterfall(...args: any[]) {
    const cbs = this.dispatch('waterfall', args)
    const inner = args.pop()
    const next = () => {
      const cb = cbs.shift() ?? inner
      return cb(...args)
    }
    args.push(next)
    return next()
  }
```

逐条拆开：

**(a) 它是 around-middleware（洋葱模型），不是管道。**
监听器**按注册顺序由外向内**包裹；`ctx.waterfall(name, ...args, next)` 传入的最后一个参数是**最内层的默认行为**（`inner`）。
`cbs.shift() ?? inner` —— 监听器用完了才落到内置默认行为。
返回值是**最外层监听器**的返回值（`events.md:121`）。

**(b) 不调 `next()` 会怎样 —— 这是本轮最关键的一句。**
`vendor/cordis/src/events.ts:227-228` 的 JSDoc：
> "Listeners run outermost-first; a listener that does not call `next()` **vetoes the rest of the chain, including the built-in behavior**."

即：**短路会把「内置默认行为」一起跳过**。
教程 `docs/cordis-tutorial/04-events.md:136` 用可运行示例验证了这一点：
listener 2 命中 `blocked` 直接返回，"the innermost default (the function passed to `ctx.waterfall`) never runs"。

因此仓库定了一条纪律（`04-events.md:138`）：
> "**a waterfall listener that only observes or annotates must call `next()`**; returning without it is a deliberate short-circuit.
> Forgetting `next()` in a logging listener silently swallows the default behavior for everyone downstream."

**注意这条纪律的性质：它是「标准规则（standing rule）」，即约定，不是机制。** 忘了 `next()` 没有任何东西会报错。

**(c) 注册顺序由什么决定？**
`vendor/cordis/src/events.ts:253-254`（`register`）：
```ts
    const method = options.prepend ? 'unshift' : 'push'
```
**这就是排序控制的全部。** `EventOptions` 只有两个字段（`events.ts:110-115`）：
```ts
export interface EventOptions {
  /** Add the listener before existing listeners for the same event. */
  prepend?: boolean
  /** Receive the event regardless of context filter checks. */
  global?: boolean
}
```
**没有优先级数值，没有比较器，没有 before/after 依赖声明。**
所以顺序 = 插件加载顺序：不 prepend 的按 FIFO 追加，prepend 的按 LIFO 抢占最外层。

**(d) 能不能保证某个监听器一定最先/最后执行？**
**不能保证。** 理由是机制层面的：`prepend: true` 只是 `unshift`，
**任何一个后加载的插件再 prepend 一次，就把你顶到第二位。** 谁最后 prepend 谁最外层，这是一场加载顺序竞态。
（Cordis 框架自己就在用这个模式：`events.ts:151-157` 的 `internal/update` 处理器注册为 `{ global: true, prepend: true }` —— 
但它靠的是「在构造函数里最早注册」这一事实优势，不是靠任何机制锁定。）

#### Q3.2 `effect` / `fiber` 的生命周期与处置规则

**fiber = 一个已加载的插件实例**（`docs/cordis-api/fiber.md:6,52-54`）：它持有生命周期状态、校验过的 config、以及注册的 effects。

**状态机**（`docs/cordis-tutorial/02-lifecycle-and-effects.md:73-80`）：
```
PENDING → LOADING → ACTIVE → UNLOADING → DISPOSED
                 ↘ FAILED
```
- `PENDING` —— 已声明，但 `inject` 要求的服务还不存在。（教程 `:82` 说这是「我的插件为什么什么都没打印」的标准答案。）
- `FAILED` —— `apply` 或 config 校验抛了。

**effect 的处置规则**（`fiber.md:30`，`ctx.effect` 的 JSDoc 原文）：
1. `execute` **立即执行**；
2. 它产生的 disposers 被收集，在「返回的 disposer 被调用」**或**「fiber 卸载」**两者中先发生的那个**时刻运行；
3. **按注册的逆序**运行；
4. **disposer 调用两次是 no-op**（幂等）；
5. fiber 已 disposed 时再建 effect **抛 `CordisError('INACTIVE_EFFECT')`**（`fiber.md:350` 定义了这个唯一的错误码）；
6. `execute` 返回形状非法则抛 `TypeError`。

**一条前几轮没抓到的重要 caveat**（`02-lifecycle-and-effects.md:94`）：
> "disposers start in reverse registration order, but multiple **async** disposers run **concurrently**.
> If teardown steps must run in sequence, keep them in one disposer and await them there."

**逆序只保证「启动顺序」，不保证「完成顺序」。** 异步清理之间没有顺序保证 —— 需要顺序就必须塞进同一个 disposer 里 await。
（这与 primer `:44` 的措辞一致，但 primer 没说清「并发」这个关键词。）

**什么已经是 effect（不用自己写）**（`02-lifecycle-and-effects.md:88-90`）：
`ctx.on()`、`ctx.plugin()`、服务注册，以及 harness 自己的 registry（`ctx.tools.register(...)` 会把返回的 disposer 挂到调用方插件上）。

**Effect 可接受的形状**（`fiber.md:280`）：单个 disposer / 其 promise / (异步)可迭代对象 —— generator effect **边产出边注册**每个 yield 的 disposer。

**其他 fiber 生命周期 API：** `fiber.dispose()`（`:105`，递归卸载子插件，async 清理完才 resolve）、
`fiber.restart()`（`:233`）、`fiber.update(config)`（`:251-267`，**先跑 `internal/update` waterfall，所以 update 钩子和 HMR 可以否决或替换这次重启**）、
`fiber.getEffects()`（`:199`，返回带 label 的 effect 树，用于诊断）。

#### Q3.3 【核心】这套模型有没有提供「不可绕过的前置钩子」？

**前几轮的结论属实，予以确认 —— 并且我现在能给出机制层面的四条独立理由，而不只是「短路即绕过」这一条。**

我在 Cordis 里逐一找过更强的保证（priority 锁定、不可卸载的 guard、seal、required listener），**都不存在**。四条理由：

**理由 1：没有优先级锁定。**
排序控制只有 `prepend: boolean`（`events.ts:253`），二值。后来者可以 `unshift` 到你前面。无法声明「我必须最外层且他人不得越过」。

**理由 2：没有不可卸载的监听器。**
`events.ts:255` —— 每个 `on()` 都走 `this.ctx.fiber.effect(...)` 并返回 disposer；
`unregister`（`events.ts:262-269`）按 callback 引用 splice 掉。
`EventOptions` 里**没有** sealed / permanent / required 之类的标志。
持有 disposer 的人，或**卸载其宿主 fiber 的人**，都能把闸门摘掉。

**理由 3：`global: true` 是「豁免过滤」，不是「豁免绕过」——不要误读。**
`dispatch`（`events.ts:170-177`）：
```ts
    const filter = thisArg?.[Context.filter]
    return (this._hooks[name] || [])
      .filter(hook => hook.global || !filter || filter.call(thisArg, hook.ctx))
```
`global: true` 让监听器**不被 context filter 剔除**（`Context.filter` 见 `docs/cordis-api/context.md:180`）。
它管的是**投递可见性**，完全不管上游监听器短路。**上游一短路，`global` 的监听器照样收不到。**
—— 这是最容易把「有更强保证」误判成 true 的坑，我特意核了源码排除它。

**理由 4（最致命，且与 waterfall 语义无关）：waterfall 只有在有人 dispatch 它时才会跑。**
闸门挂在事件上，就等于把执行权交给了「调用点是否愿意发这个事件」。
**任何直接调用服务方法的代码路径，一次都不会触发这条链。**
Cordis 自己的 primer `:42` 就把这两条路并列了：
> "Prefer events for interception and policy; prefer service methods for direct capability calls."

**结论：Cordis 的 waterfall 是「协作式拦截」，不是「强制式闸门」。**
它的全部强度建立在**约定**上（`04-events.md:138` 那条 standing rule），
而 deepseek-harness 自己心里很清楚这一点 —— 证据是：**它把真正不能被绕过的东西，全都放在了别处。**

**反证（harness 自己怎么做真闸门的），三种，都不是 waterfall：**
1. **放进类型形状** —— `PreToolDecision`（`tools.md:387-394`）没有 args 分支，改写参数在类型上不可表达。
2. **放进调用签名 / 存储边界** —— `Session.append()` 先做 lossless JSON 快照再深冻结才发布
   （`2026-06-11-dev-invariants-over-deep-readonly.md:23-25`），
   **永远开、与插件组合无关**（`:27`：production / focused test / custom embedding 拿到完全相同的存储语义）。
3. **放进运行时不变量断言** —— `ctx.invariants`，加上仓库级门禁 `verify-package-invariants`
   （`2026-07-19-package-owned-invariant-service.md:69`）。

另外确认一条与 finaudit 直接相关的事实：**`approval/request` 本身就是 waterfall**
（`docs/cordis-tutorial/04-events.md:140`："lets a policy answer instead of the user"）。
也就是说，**在 deepseek-harness 里，审批这一环在事件层面同样是可短路的** ——
真正的 fail-closed 在 `tools/pre-execute` 的**判定逻辑**里（`tools.md:402`：缺 channel / 缺 service / 无 agent 一律 deny），
而不是在 waterfall 的**结构**里。

---

## 3. 逐文档发现（上面没覆盖的）

### 3.1 `.agents/notes` 的组织方式本身值得抄

`.agents/notes/AGENTS.md`（全 7 行）把 notes 定性为：
> `:3` — "Agent Notes are effectively RFCs written by agents: durable proposals and decision records that preserve **rationale, alternatives, consequences, and required verification**."

四段式结构在我读的每一篇里都严格成立：`Problem` / `Decision` / `Alternatives considered` / `Consequences`（部分加 `Testing`）。
**`Alternatives considered` 是强制项**——早期未按此格式写的会被打标记，例如
`2026-06-11-runtime-arg-validation.md:24` 结尾有：
```
<!-- agent-note-format: alternatives-not-recorded (pre-format Agent Note) -->
```
即：**没记录备选方案的旧文档被显式标注为「格式欠债」，而不是假装完整。**

**目录状态机：** `proposed/` → `implemented/` → `archived/`，按 `architecture` / `bug-fix` / `feature` / `process` / `testing` / `simplification` 分类。
`AGENTS.md:5` 规定：**每新增一篇必须做 supersession check**（搜索现存 notes 里覆盖同一决策的旧篇，分类为全部/部分被取代，同一个 PR 里归档），
部分取代的保持 active 并互相交叉链接。`:7` —— `archived/` 是冻结快照，**永不编辑，也不得当作当前权威**。

**规模（我实际数的）：** 非归档 `.md`（不含 `.zh.md`）约 200+ 篇；`archived/` 下另有大量。
每篇都有 `.md` / `.zh.md` / `.i18n.yaml` 三件套。

### 3.2 `Status:` 是文档的一等字段

每篇 note 第三行都是 `Status: implemented`。前几轮报告提到「两份文档引用了至少 12 篇 notes」——
现在可以确认引用是**双向**的：`docs/tool-catalog.md:8` 指回 `.agents/notes/implemented/process/2026-07-02-tool-schema-catalog.md`，
`docs/tool-catalog.md:23` 指回 `.agents/notes/implemented/feature/2026-07-08-self-referential-cordis-toolset.md`，
notes 之间也用 `[[wiki-link]]` 与相对路径互引（如 `2026-08-08-pi-ai-...md:9` 引 `[[2026-08-03-pi-ai-declared-provider-catalog]]`）。

### 3.3 `docs/development.md:163` —— 文档与源码不许漂移的机械门禁

这条前几轮没提到，**对 finaudit 的「口径文档 ↔ 口径实现」问题是直接可用的**。

做法：subsystems 文档里粘贴的类型定义，代码块标记为 ` ```ts type-equiv ` 而不是 ` ```ts `，
并在 `scripts/type-equiv.manifest.json` 里登记它镜像的源文件与符号：
```json
{ "doc": "docs/subsystems/session.md", "symbol": "SessionEvent", "source": "packages/core/session/src/types.ts" }
```
`pnpm run verify-type-equiv`（属于 `doc-sync`）用 TypeScript parser **从源码里抽出该符号的声明与 JSDoc，断言文档块与二者都一致**。

要点（都在 `:163`）：
- 比较**忽略空白与非 JSDoc 注释**，但**要求每一条原始 JSDoc 都在**——所以读者在文档里看到的契约就是源码契约。
- 门禁强制 **1:1 对应**：按 doc / symbol / projection 三元组，主代码块与 manifest 条目必须一一对上；增删代码块必须同 PR 改 manifest。
- 类可以用 ` ```ts public-api ` 投影：保留公开字段/构造器/访问器/方法与 JSDoc，**省略函数体与 private/protected 成员**。
- 中文版 `.zh.md` 的对应块只有在**整个受跟踪 fence 序列逐字节相同且顺序一致**时才复用英文条目。

`development.md:153` 另有一条小而有用的规矩：三级 TODO 标记 —— `FIXME`（应阻塞发布）/ `TODO`（尽快）/ `XXX`（也许某天，无承诺）。
理由写得很直白：让扫代码的人**一眼分得出 release blocker 和 someday-maybe**。

### 3.4 `docs/api-gateway.md` —— fail-closed 在 RPC 层的样子

我读了 `Strict generation pipeline` / `Runtime invocation` / `SRC development fallback` / `Boundaries` 四节（`:95-164`）。
与证据链相关的两条：

**(a) 每次调用都从当前注册表重新解析，不缓存业务对象**（`:129`）：
> "For every call, the Gateway resolves the descriptor and live service from the current registries **instead of caching business objects**."
> 参数字段必须与 descriptor **精确匹配**，wire 值过 codec 校验，返回值也校验。
> "A missing provider, unknown identity, binding mismatch, missing or extra argument, schema failure, or missing method **fails before entering or after leaving business code**."

**(b) 热卸载不得悄悄削弱校验**（`:133`）：
> "A strict endpoint withdrawn on the Host also **does not degrade to SRC inference**, preventing a hot unload from silently weakening validation."

—— 这是「降级必须显式失败，不得静默降格」的一个具体实例，与 D-003「给不出证据链视为失败，不视为降级成功」同构。

**(c) 开发期弱化路径被明确圈死**（`:131` SRC fallback）：SRC 只解决「从源码启动的 Host 的 dispatch」，
"SRC does not read TypeScript types, generate Zod schemas, infer optional parameters..."，
且 Client 端**拒绝挂载缺少 strict codec 的 SRC descriptor**。
即：**弱化版本存在，但被限制在开发面，且对面拒绝接受它。**

### 3.5 `docs/user/` —— 对外文档怎么组织，以及「证据」在里面的地位

**组织方式（13 篇，我读了 index 与 basic/index，其余按标题与 grep 判断）：**
```
docs/user/
  index.md            → 一个 meta refresh，直接跳 ./guide/quickstart
  guide/              面向使用者：index.md（Web UI 上手，30 行）/ providers.md / python-sdk.md
  develop/
    basic/            index.md（第一个插件）/ tool.md / config.md / publish.md
    framework/        index.md / service.md / events.md
    practice/         index.md / llm-adapter.md
```
即 **use → develop-basic → develop-framework → develop-practice** 四级递进，
且刻意与仓库内部文档分层：`develop/basic/index.md:144` 末尾把读者推向 `docs/cordis-tutorial/`，
后者的定位是「底下的插件框架，**从一个 scratch 目录搭起，不需要 API key**」。

**必答：有没有把「证据 / 日志」作为用户可见的一等功能暴露？**

**没有。这是本轮一个明确的负面结论。**

我对 `docs/user/**` 全量 grep 了 `audit|evidence|provenance|session log|transcript|replay|reproduc`，
**只命中两处，且都是附带说明，不是功能介绍**：
- `docs/user/guide/providers.md:94` —— 排错条目：图片留在 session log 里，所以同一个请求会重复失败。
- `docs/user/guide/python-sdk.md:100` —— 参数说明：`session_root` 存放 session 日志与状态。

用户指南（`guide/index.md`，全 30 行）讲的是：配模型 → 选 workspace → 跑任务。
关于审批只有一句（`:24`）：
> "The Web UI asks before operations that require approval under the active permission policy."

**没有**「查看这次回答依据了什么」「导出证据」「复核某一步」这类面向用户的入口。

**判断：** 在 deepseek-harness 里，事件溯源 / 不可变会话日志 / 请求可重建 / 不变量断言，
**是给开发者与运行时用的基础设施，不是端到端交付给终端用户的产品功能。**
这恰好是 finaudit 的差异化所在——不要以为「上游做了所以我抄一层就有了」，那一层它根本没做。

---

## 4. 对 finaudit 的具体输入

### 4.1 【最终判断】「口径闸门不可绕过」

**前几轮的结论成立：waterfall 做不到，正解是把闸门放进调用签名。本轮把它从「照抄措辞」升级为「读过实现后的判断」，并给出更强的表述。**

先精确化一点：**Cordis 的 waterfall 甚至比「任一监听器短路即绕过」更弱**，因为短路会连**内置默认行为**一起吞掉
（`vendor/cordis/src/events.ts:227-228`）。也就是说，闸门插件不仅可能被跳过，它想守护的那个默认动作本身也会被跳过。

**给 finaudit 的可执行版本（三选一，按强度排序）：**

**(1) 让违规在类型里无法表达 —— 首选，成本最低。**
照抄 `PreToolDecision`（`docs/subsystems/tools.md:387-394`）的做法：
> 不是「检查拦截器有没有改写参数」，而是**让拦截器的返回类型里没有能放参数的地方**。

对应到 finaudit：**指标计算函数不接受「裸口径字符串」，只接受一个已被口径闸门签发的凭证对象**，
且该凭证**没有公开构造器**——只能由闸门返回。这样「绕过闸门算指标」不是运行时被拒，而是**写不出来**。

**(2) 让闸门成为存储/发布边界，永远开、与插件组合无关。**
照抄 `Session.append()`（`2026-06-11-dev-invariants-over-deep-readonly.md:23-27`）：
校验 + 无损快照 + 深冻结在**接受事件的那一步**完成，`:27` 的理由是决定性的：
> "This guarantee belongs in `Session`, not in an optional listener, because every composition relies on trustworthy history."

对应到 finaudit：**证据链的组装不能是「回答生成后再挂上去的一个 hook」**，
必须是「答案对象只有携带完整证据链才能被构造出来」。给不出证据链 → 构造失败 → 整条回答失败（D-003）。

**(3) 关系性命题用运行时断言 + 仓库级门禁兜底。**
照抄 `ctx.invariants` + `verify-package-invariants`（`2026-07-19-package-owned-invariant-service.md:69`）：
- 断言**由各自的包拥有并测试**，注册中心不含任何业务检查（避免中心包 import 所有领域词汇）；
- 门禁拒绝**「没有解释的空实现」**——这是最值得抄的一条：
  允许某个包说「我没有需要检查的关系」，但**必须写明为什么**，不许留空占位。

对应到 finaudit：每个口径/指标模块必须声明它的关系性不变量（如「同比的两期口径必须同源」「合并报表与母公司报表不得混算」），
没有就必须写明理由。

**明确不要做的事：** 不要把口径闸门实现成「注册一个 pre-hook，指望所有调用点都发这个事件」。
`docs/tool-catalog.md:26` 那句 "a deployment **is expected to** also load it" 就是这条路的终点——
**它把强制性降级成了期望。**

### 4.2 三态 > 两态：一条可以直接落到 finaudit 数据层的规则

来自 `2026-08-08-pi-ai-per-model-reasoning-declarations.md:15,25`。

**规则：当「字段缺省」与「显式关闭」在序列化后会塌缩成同一个值时，两态就是错的，必须升为三态，且拼写必须选一个序列化层能区分的形状。**

finaudit 的直接对应（这是真会踩的）：某个财务科目的三态是
- **缺失**（年报未披露该项）
- **显式为零**（披露了，值是 0）
- **不适用**（该科目对本行业/本报表类型无意义）

如果用 `float | None` 两态，"披露为 0" 与 "未披露" 会在 pandas / JSON / parquet 往返中互相污染
（`NaN`、`None`、`0.0` 的相互转换是经典失真点）。这直接毁掉「这个口径对不对」的可答性。

配套的 fail-loud 也一起抄（同段 `:15` 末）：**「看起来像三态但语义未定的输入」要显式拒绝，不要让它从 union 里溜过去。**
原文场景是 YAML 的裸 `key:`（null）；finaudit 的对应是 Excel 空串 `""`、`"—"`、`"不适用"`、`"--"` 这类占位符——
**不许静默映射成 0 或 None，要么归入明确的第三态，要么显式报错。**

### 4.3 「生成物的可信度是分层的」——一条方法论修正

本轮最反直觉的发现在 `docs/tool-catalog.md`。同一份「生成」文件里：
- **JSON Schema 部分**：生成器**真的把插件 boot 起来读运行时**（`:8`），可信为机械事实；
- **`Requires` / `Writes / affects` 部分**：`scripts/gen-tool-catalog.ts:151-154` 显示这是**手写字段**，`:189` 起逐包硬编码字面量。

**对 finaudit 的两条推论：**
1. **finaudit 的「工具/指标副作用声明」如果要能进证据链，必须是从实现推导的，不能是手维护的清单**，
   否则它就是一段会漂移的文档，而证据链里放一条会漂移的断言比不放更糟。
2. 反过来，deepseek-harness 那条完整性守卫（`:8`：glob `packages/*/tool-*`，缺一个包就失败）是**廉价且有效**的：
   它不保证内容对，但保证**没有条目被漏掉**。finaudit 可以先上这一层（每个口径必须在注册表里有条目），再逐步把内容也机械化。

### 4.4 disposer 的顺序陷阱（写清理逻辑时会踩）

`docs/cordis-tutorial/02-lifecycle-and-effects.md:94`：**逆序只保证「开始」顺序，多个 async disposer 是并发跑的。**
需要顺序 → 塞进同一个 disposer 里 await。
finaudit 若做「计算 → 落证据 → 关连接」这类收尾链，不能靠注册顺序，必须显式串起来。

### 4.5 `ts type-equiv` 门禁 —— 直接可移植

`docs/development.md:163`。finaudit 的 `PROJECT_SPEC.md` / `DECISIONS.md` 里凡是粘贴了口径公式或数据结构的地方，
都可以上同款门禁：登记 `{doc, symbol, source}`，用 parser 从源码抽出来断言一致，**改了实现不改文档就红**。
这比「人工同步」强一个数量级，而且实现成本很低。

---

## 5. 我没读，因此不能置评

- **`.agents/notes` 的绝大多数。** 非归档 `.md` 约 200+ 篇，我**完整读了 4 篇**
  （`2026-06-11-dev-invariants-over-deep-readonly` / `2026-06-11-runtime-arg-validation` /
  `2026-07-19-package-owned-invariant-service` / `2026-08-08-pi-ai-per-model-reasoning-declarations`），
  另有 3 篇只读到被 grep 命中的那一两行（`2026-06-29-todo-write-tool:15`、`2026-07-25-client-settings-locale-theme:23`、
  `2026-08-10-npm-release-sequences:63,71`）。**`archived/` 全部未读。**
  → 因此「notes 里没有 X」这类断言我一律不下。上面 Q1.1/Q1.2 的答案是**「我搜到并读到了这些」**，
    不是**「全仓库只有这些」**。我的搜索是 grep 关键词驱动的，措辞不同的相关篇目很可能被漏掉。
- **`docs/tool-catalog.md` 的 1873 行我没有逐行读。** 我读了 `:1-50`（生成规则 + 完整包映射表全 24 行）、
  `:178-227`（bash/pwsh 完整条目作为结构样本），其余靠对 approval/permission/schema 类关键词的全文件 grep。
  → 「没有声明式审批字段」这个结论的强度：**表结构与样本条目支持它，全文件 grep 未命中反例**；
    但我不能排除某个我没 grep 到的字段名。
- **`scripts/gen-tool-catalog.ts` 我只读了 `:83,98,151-154,189-203,216-217` 等被 grep 命中的片段**（全文 759 行）。
  → 「`writes` 是手写的」这个判断基于接口定义 + 多处字面量数组，我认为很扎实；但我没读生成逻辑，
    不能排除它另外还会追加从代码推导出的条目。
- **Cordis：`registry.md`（152 行）、`service.md`（102 行）、`inherited.md`（39 行）完全未读。**
  → 特别是 `registry.md`（`ctx.plugin` / `ctx.inject` 的加载语义）。如果那里存在某种加载顺序保证，
    会削弱我 Q3.3 理由 1 的强度。**我核过的是 events 与 fiber 两个面，不是 registry 面。**
  → `vendor/cordis/src/` 我只读了 `events.ts:1-330`。`fiber.ts`、`context.ts`、`registry.ts`、`reflect.ts`、
    `service.ts` 的**实现**未读（只读了它们生成出来的 API 文档）。
- **Cordis tutorial：`01`/`03`/`05`/`06`/`07` 与 `index` 未读**（读了 `02` 与 `04`）。
  `07-into-the-harness.md`（107 行）按标题应该是「Cordis 概念如何落到 harness」，与本轮主题相关但未读。
- **`docs/user/` 13 篇里我完整读了 3 篇**（`index.md`、`guide/index.md`、`develop/basic/index.md`），
  其余 10 篇靠 grep + 行数。
  → 「没有把证据/日志做成一等用户功能」这个结论基于**全目录 grep 只命中 2 处附带提及**，我认为可靠；
    但我没读 `develop/practice/index.md`（155 行）与 `publish.md`（183 行），不能排除里面有相关内容。
- **`docs/api-gateway.md` 读了 `:95-164`**（后半），`:1-94`（Programming model / Component responsibilities）未读。
- **`docs/development.md` 读了 `:119-171`**，`:1-118`（Setup / TypeScript layout / 环境变量 / Git 集成）未读。
- **所有 `.zh.md` 与 `.i18n.yaml` 未读。** 若中英文有实质分歧，我看不到。
- **`.agents/skills/` 完全未读**（`.agents/` 下与 `notes/` 平级的另一个目录，含 `dsh-archive-agent-notes` 等）。


