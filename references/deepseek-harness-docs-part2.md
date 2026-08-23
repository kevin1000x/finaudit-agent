# deepseek-harness `docs/` 续读 · Part 2

> **语料**：`deepseek-ai/deepseek-harness`，commit **`47f943859bef60e4160492346772ded9b24f765a`**（短号 `47f9438`）。
> 该 commit 由上一轮 agent 从 `.git/objects/pack` + reflog 还原，本轮开头已用
> `git rev-parse HEAD` 复核（输出即上面这串 40 位哈希）。
> 只读英文 `*.md`，跳过 `*.zh.md` 与 `*.i18n.yaml`。
>
> **本轮定位**：读上一轮 docs agent 点名的「密度最高」部分。
> `subsystems/tools.md` 与 `subsystems/session.md` 在更早几轮已读过
> （见 `references/deepseek-harness.md` §5），**本轮只记增量**，重合处明写。
>
> 引用格式 `docs/xxx.md:行号`，行号对应上述 commit 的英文原文。

## 覆盖表（本轮实际读到的程度）

> 本表在**读完之后**填写。「全文」= 从第 1 行读到最后一行；
> 「部分」= 注明读了哪些行区间与大致行数；「仅标题」= 只看到它在某个索引页里的一行描述。

| 文档 | 行数 | 全文 / 部分 / 仅标题 |
|---|---|---|
| `docs/subsystems/tools.md` | 720 | **全文**（分 3 段读完 `1-260` / `260-520` / `520-720`） |
| `docs/tool-execution-pipeline.md` | 62 | **全文**（上一轮已全读，本轮重读取增量） |
| `docs/event-producer-consumer.md` | 76 | **全文** |
| `docs/testing.md` | 49 | **全文** |
| `docs/development.md` | 171 | **全文** |
| `docs/subsystems/invariants.md` | 88 | **全文** |
| `docs/subsystems/README.md` | 55 | **全文** |
| `docs/defensive-patterns.md` | 33 | **全文**（不在原范围，因 `testing.md:5` 指向而追加） |
| `docs/postmortem/README.md` | 18 | **全文**（同上，因 `testing.md:19` 指向而追加） |
| `docs/postmortem/0001-acp-default-export-drops-inject.md` | 113 | **全文**（同上） |
| `docs/subsystems/approval.md` | 170 | **部分**，约 90 行：`5-50`、`80-140`（跳过 `ApprovalRequest` 字段清单与 `approval/request` 事件签名） |
| `docs/subsystems/subagent.md` | 734 | **部分**，约 55 行：`55-110`（只为核实 `:68` 那句被截断的引用） |
| `docs/cookbook/extension-cookbook.md` | 129 | **部分**，2 行：`:9`、`:121`（只为核实 MCP 工具的注册入口） |
| `docs/subsystems/` 其余 **41** 页 | — | **仅标题**（只读到 `subsystems/README.md:9-53` 里各自的一行描述） |
| `docs/` 顶层其余 17 项（含 `capability-seams.md` 471 行、`config-catalog.md`、`module-graph.md`、`tool-catalog.md`、`cordis-*`、`user/`、`i18n/`） | — | **未读** |

本轮实读约 **1385 行全文 + 约 150 行选读**。完整未读清单见 §11。

---

## 1. `subsystems/tools.md`（720 行，全文读完）

### 1.0 与 `references/deepseek-harness.md` 重合的部分（不重复誊抄）

以下四点上一轮已记录，本节**不再展开**，只标注行号供复核：

| 已记内容 | 本 commit 行号 | 已落在哪 |
|---|---|---|
| `ToolGuard` 返回类型故意没有 allow（单调守卫） | `docs/subsystems/tools.md:313`、`:315-325` | `deepseek-harness.md` §5.1 |
| 「Arguments cannot be rewritten because history, audit, UI, and execution must agree」 | `docs/subsystems/tools.md:402` | `deepseek-harness.md` §5.2 |
| 完整执行管线七段 | `docs/subsystems/tools.md:172` | `deepseek-harness.md` §5.3 |
| `tools/pre-execute` 缺审批通道 ⇒ deny | `docs/subsystems/tools.md:402`、`:681` | `deepseek-harness.md` §5.3 |

下面全部是**增量**。

---

### 1.1 封闭 schema 的九种节点：`ValueSchemaSpec` 怎么穷举的（Q1 正面回答）

原文一句话把九支列全（`docs/subsystems/tools.md:100`）：

> `ValueSchemaSpec` supports `string`, `number`, `integer`, `boolean`, `null`, `array`,
> `object`, author-only `json`, and exact-one `oneOf`

类型定义本身就是一个**九支的裸联合**（`docs/subsystems/tools.md:104-116`）：

```ts
type ValueSchemaSpec =
  | StringValueSchemaSpec
  | NumberValueSchemaSpec
  | IntegerValueSchemaSpec
  | BooleanValueSchemaSpec
  | NullValueSchemaSpec
  | ArrayValueSchemaSpec
  | ObjectValueSchemaSpec
  | JsonValueSchemaSpec      // 「author-only」：只给一方插件作者用
  | OneOfValueSchemaSpec
```

**穷举方式不是「列了九个 case」，是「联合类型只有九个成员」。** 这是关键差别：
穷举性由类型系统保证，不是由某个 `switch` 的完整性保证。多写一个节点类型，
必须改这个联合的定义；而联合是 `packages/core/tools/src/schema.ts` 里的**单一声明点**
（`docs/subsystems/tools.md:102` 指明 Source）。

三条把「封闭」钉死的附加约束，都在 `:100`：

1. **`enum` / `const` 的标量值必须与节点类型匹配**——不允许 `{type:'string', const: 3}`
   这种「schema 自己内部矛盾」的东西存在。
2. **显式 object 节点必须声明 `additionalProperties: true | false`**——
   注意是 **must always declare**，不是「可以省略、默认 open」。
   把「开放/封闭」变成**必答题**，而不是一个可以忘记的默认值。
3. **参数根（`ParameterSchemaSpec`）是唯一的例外**：它是一个 implicit open object，
   requiredness 用**逐属性 `required: true`** 表达（`:118-132`），
   而不是根上一个 `required: string[]` 数组。理由后面 1.3 说。

**推断的边界被显式写死**（`docs/subsystems/tools.md:134`、`:136-142`）：

> `InferValue<S>` honors literal constraints and object openness through **16 container levels**,
> then falls back to `JsonValue` instead of exhausting TypeScript's type-instantiation stack.

而且**类型推断的退化不等于运行时校验的退化**（`docs/subsystems/tools.md:149`）：

> Inference stays exact through 16 container levels and then widens to `JsonValue`;
> **runtime validation keeps walking the complete schema.**

这一条对本项目直接可用：**静态保证有深度上限是可以接受的，
只要运行时校验没有同一个上限**。承认编译期能力有限、但不让运行期跟着降级。

---

### 1.2 外来 schema 在哪个边界被拒（Q1 正面回答）

原文点名了四个外来来源，全在同一句里（`docs/subsystems/tools.md:408`）：

> **Raw schemas from subagents, workflows, MCP, and dynamic registrations** use the
> wire-level counterpart of the author DSL. `assertSupportedJsonSchema()` accepts any
> JSON root, `validateJsonSchemaValue()` enforces it, and `JsonSchemaError` reports
> **every** unsupported or malformed schema path.

**边界在「注册」这一步，不在「调用」这一步。** 三条证据合起来才能确定这件事：

1. `ctx.tools.register()` 的契约（`docs/subsystems/tools.md:151`）：
   > The registry borrows the typed definition as readonly input, **requires `output`,
   > validates its raw schema**, and checks semantic requirements such as a positive
   > finite `timeoutMs`
2. MCP 工具走的正是这个入口——不是另开一条路。
   `docs/cookbook/extension-cookbook.md:9`：
   > Raw JSON-Schema `ToolDefinition`s are also accepted by `ctx.tools.register()`
   > directly (**that is how MCP-sourced tools arrive**); `defineTool` is the typed
   > helper for first-party tools.
   以及 `docs/cookbook/extension-cookbook.md:121` 的表格行：
   > `| MCP | one plugin per server: discover tools → ctx.tools.register() |`
3. 子 agent 侧同样在**启动**时拒（`docs/subsystems/subagent.md:68`）：
   > Object-rooted JSON Schema within `assertObjectJsonSchema`'s enforced subset.
   > **Start rejects** …（该行在此截断，本轮未展开读 subagent.md 上下文，见覆盖表）

所以结构是：**没有第二条入口。** `defineTool` 只是 first-party 的**打字机**，
不是唯一通道；外来 schema 直接进 `register()`，而 `register()` 本身就校验。
换句话说，封闭性靠的**不是**「所有人都用 `defineTool`」这种约定，
而是「唯一那扇门自己会检查」。

**拒绝时的错误是结构化的，不是自由文本。** 三层各有专门的错误类型：

| 层 | 错误类型 | 错误码 | 出处 |
|---|---|---|---|
| schema 本身不合法 | `JsonSchemaError` | 报出 **every** unsupported/malformed **schema path** | `:408` |
| 入参不匹配 schema | `ToolArgsError` | `INVALID_ARGS` | `:149` |
| 工具返回值 / post-policy 值不匹配 | `ToolOutputError` | `INVALID_TOOL_OUTPUT` | `:149` |

注意 `JsonSchemaError` 报的是 **path**（哪一条 schema 路径不合法），
不是「schema 无效」四个字。这正是 `ARCHITECTURE §8.2` 要求 `Refusal` 封闭枚举时
应该配套的东西：**枚举给「哪一类」，path/字段给「哪一处」**，两者都要有。

**默认方向是「拒绝」而不是「放行不管」**（`docs/subsystems/tools.md:149` 末句，
这句是本轮最该抄进本项目的一句）：

> Raw JSON Schema remains open by default;
> **unsupported keywords reject instead of being accepted without enforcement.**

这是 fail-closed 应用在**词汇表**上：遇到一个我不认识的 JSON Schema 关键字，
不是「忽略它，按没写处理」（那会**悄悄放宽**约束），而是**整个 schema 拒绝注册**。
对照 `deepseek-harness.md` §5.4 记的 `ignorable` 默认为必需——
这是同一个原则在两个不同层面（日志格式演进 / schema 词汇表）的两次应用。

> **一个反直觉但重要的分辨**：「open by default」（未声明的 key 允许出现）
> 与「unsupported keywords reject」（未支持的**关键字**拒绝）是两件相反方向的事，
> 原文把它们**并列在同一句**里。前者是对**数据**宽容，后者是对**约束语言**严格。
> 本项目容易搞混这两件事：口径定义里多一个说明性字段无所谓，
> 但口径定义里出现一个「我们的解析器不认识的约束写法」必须直接拒。

---

### 1.3 「参数不可改写」是怎么在类型上做到的（Q2 正面回答）

上一轮已从 `PreToolDecision` 读出「三分支没有一支能携带 args」。
**本轮的增量是：`tools.md` 把理由写在了类型的 doc comment 里，而不是写在别处的散文里。**

`docs/subsystems/tools.md:378-389`，注意注释的最后一句就在类型定义体内：

```ts
/**
 * Pre-dispatch decision. `allow` runs the call; `deny` materializes an error;
 * `ask` runs only after an approval service returns `allowed-once` and otherwise
 * denies. Input rewriting is excluded because arguments are already logged and
 * presented.                                    // ← 理由钉在类型旁边
 */
type PreToolDecision =
  | { kind: 'allow' }
  | { kind: 'deny'; reason: string }
  | { kind: 'ask'; reason?: string }
```

**「因为参数已经被记录、已经被展示」——这是时序论证，不是道德论证。**
`tool/call` 事件在执行**之前**就写进 session（`deepseek-harness.md` §5.3 已记）。
所以到 `tools/pre-execute` 这一刻，参数**已经是既成事实**了：
日志里有它、UI 上显示的是它。此时再允许改写，唯一可能的结果就是四方分叉。
不是「我们规定不许改」，是「改了必然不一致，所以类型上不给这个口子」。

**类型上到底是怎么做到的——四道锁，缺一不可**（这是本轮真正的增量）：

| # | 机制 | 出处 | 挡住什么绕道 |
|---|---|---|---|
| 1 | `PreToolDecision` 三分支无一携带 args | `:385-389` | 「决策顺便带个新参数」 |
| 2 | `ToolExecution` 的参数**跨一次 lossless-JSON 物化边界后被 deep-freeze** | `:283-290` | 「不改决策，直接改对象」 |
| 3 | `ToolDispatchExecution = Omit<ToolExecution,'signal'> & {signal}`——**只有 signal 一个字段被摘出来变可写** | `:299-308` | 「around-dispatch 包装器顺手改」 |
| 4 | `ToolGuard: (execution: Readonly<ToolExecution>) => string \| undefined`——入参 `Readonly`，返回只有 string | `:315-324` | 「守卫返回一个修正后的调用」 |

第 2 条的原文（`:285-289`）：

> Parsed arguments cross **one lossless-JSON materialization boundary** before policy
> and **are deep-frozen**; call identity, the caller signal, and the registry-assigned
> `token` are readonly. The registry **freezes the complete object** before `tools/result`
> observers run.

第 3 条是四道锁里设计最漂亮的一条，值得单独说。
`tools/execute` 是 around-dispatch 包装器（超时、重试、指标），
它**必须**能换 signal（否则做不了超时）。
如果 `ToolDispatchExecution` 直接写成 `interface X { ...所有字段可写 }`，
那超时插件就顺带获得了改参数的能力。
harness 的写法是 `Omit<ToolExecution, 'signal'> & { signal: AbortSignal }`：
**用类型运算精确地只解冻一个字段**。原文的措辞（`:301-303`）：

> A `tools/execute` wrapper **may replace the signal for its delegated lifetime,
> but it cannot remove it.** The registry fuses every replacement with the captured
> caller signal.

「可以替换但不能移除」，而且**注册表会把替换后的 signal 与原始 caller signal 再融合一次**
（`:632-640` 重复强调：`The registry re-fuses the original caller signal before the body,
so replacement cannot detach caller cancellation`）。
即：**授予的权限本身也是单调收紧的**——你能加一个取消源，不能减掉一个。

> **对 `ARCHITECTURE §8.1`（闸门放进调用签名）的直接校正意见：**
> §8.1 现在的表述是「把闸门放进调用签名」。tools.md 说明这只是**第一道锁**。
> 光有签名不够——如果被传进签名的那个对象本身可写，签名就是装饰。
> 完整形态是：**签名闭合（1）+ 载荷冻结（2）+ 例外用类型运算精确开孔（3）+ 只读入参（4）**。
> 本项目的 `resolve()` 目前只做到 (1)。**(2)(3)(4) 未落地**——落点见末节。

---

### 1.4 证据/留痕在管线哪一步产生，能不能被绕过（Q3 正面回答）

`tools.md` 给出了一个上一轮没记到的、很硬的分层：**「执行局部值」与「持久化投影」是两个东西**。

`docs/subsystems/tools.md:339-349`，`ToolExecutionSuccess` 里这一行的注释是关键：

```ts
interface ToolExecutionSuccess {
  readonly isError: false
  /** Execution-local canonical value; deliberately omitted from durable events. */
  readonly value: JsonValue          // ← 故意不进持久事件
  readonly content: ContentBlock[]
  ...
}
```

原文的完整论述（`docs/subsystems/tools.md:370`）：

> Call identity remains on the **immutable `ToolExecution`** that accompanies it through
> every hook **and on the durable `tool/call` / `tool/result` session events**,
> so **wrappers cannot create a second, disagreeing identity**. The canonical `value`
> is execution-local: the loop persists only `content`, `error`, and `meta` …
> **Replay reproduces presentation but cannot reconstruct canonical intermediate values.**

拆开看有三层含义：

1. **身份（identity）是不可伪造的，因为它只有一个来源。**
   `ToolExecution` 是 registry 在 policy 之前就分配好 token 的（`:311`），
   同一个对象一路穿过所有 hook，并且**同一个身份也写进了持久事件**。
   包装器想「另造一个身份」做不到——它手上根本没有第二个 token 的铸造权
   （`ToolExecutionToken` 是 opaque `Symbol`，`:174-177`、`:311`）。
2. **留痕的产生点是 registry，不是任何 listener。**
   `:372`：`On success the registry snapshots and validates the body value, freezes it,
   and invokes the pure renderer …` `:374`：`The registry invokes that callback
   exactly once, then materializes and freezes the accepted result immediately before
   tools/result`。**是 registry 自己做的，插件没有跳过它的路径。**
3. **绕过的唯一后果是「降级成 isError」，不是「静默通过」。**
   `:372`：`an invalid value, renderer/projector failure, or non-JSON presentation
   becomes a JSON-safe isError.` `:374` 同样：物化失败 ⇒ isError ⇒ **仍然进 `finalizeContent`**。
   也就是说，**留痕环节自己出错，产生的是一条「失败的痕」，不是「没有痕」。**

**能不能被绕过：不能，且原文给了三处「即使 X 也仍然会 Y」的兜底表述**：

| 场景 | 兜底 | 出处 |
|---|---|---|
| 工具体抛异常 | `thrown tools still reach this waterfall as errors` | `:656` |
| 管线自己失败、跳过了 `tools/post-execute` | `finalizeContent` 仍被调用——`invokes it exactly once for every normalized outcome, **including pipeline failures that bypass tools/post-execute**` | `:41-45` |
| 未知工具 | `ToolNotFoundError` → `UNKNOWN_TOOL`，`so the call fails **without ending the turn**` | `:404` |
| `tools/result` 观察者自己抛 | `Listener failures are contained` | `:704` |

第二行是本轮**对本项目最有价值的一条**。它说的是：
**「后处理钩子被跳过」这件事本身不能导致「最后一道归一化也被跳过」。**
harness 把 `finalizeContent` 的调用点从「post-execute 之后」搬到了
「**每一个 normalized outcome 之后，包括那些绕过了 post-execute 的失败**」。

> **对照 `ARCHITECTURE §8.5`（证据指针必须被下游强制消费）与刚从 hello-agents
> 读出的反例（存证做对了、指针在接线时被丢掉）：**
> harness 防的正是这个。它的手法不是「要求下游记得消费」，
> 而是 **把消费点放在 registry 内部、放在所有失败路径的汇流处**。
> 「下游记得」是纪律，「汇流处强制」是结构。§8.5 目前写的是前者。**需要改写成后者。**

一个反向的、同样重要的细节（`docs/subsystems/tools.md:404`）：

> Content replacement is **presentation policy, not confidentiality policy**:
> a listener that must hide the programmatic value **blocks or replaces it**.

即：`PostToolDecision` 的 `accept{content}` 只换**展示**，`value` 原样保留。
想真正藏掉值，必须用 `block` 或 `accept{value}`——**两者只能二选一**
（`:396-400` 的类型用 `content?: never` / `value?: never` 强制互斥）。
**「看起来改了」和「真的改了」在类型上是两支。** 这对本项目的脱敏/摘要场景是直接告诫：
把一个数在界面上打码，不等于证据链里那个数被换掉了。

`tools/code-dispatch-log` 把这条推到极端（`:601-622`）：它允许 listener
**只改持久日志里的那份 content**，而程序拿到的完整 value 与模型看到的都不变。
原文明写 `Only the logged copy is affected`。
这是一个**故意让日志与真实值不同**的口子，用途是 spill（超大结果只记 preview + locator）。
**本项目不能抄这一条。** 证据链要的是日志与实际一致；harness 敢这么做，
是因为它的日志目标是「重建对话」，不是「独立复核计算」。见末节。

---

### 1.5 三个上一轮没记、但结构上有用的增量

**(a) `schemas()` 用显式 allowlist 防止内部字段泄漏到模型**（`docs/subsystems/tools.md:11`）：

> The registry's `schemas()` builds the model-facing `ToolSchema[]` by an **explicit allowlist**
> — `output`/`execute`/`finalizeContent`/`timeoutMs`/`isConcurrencySafe`/`presentCall`/`presentResult`
> **must never leak into a model request**.

`:60` 对 `timeoutMs` 再强调一次：`it is NEVER sent to the model — schemas() whitelists
only name/description/parameters`。
**同一个 `ToolDefinition` 对象服务两个受众（执行 / 模型），投影靠 allowlist 而非 denylist。**
`:544` 补一句：`one deep-cloned schema per visible tool`——投影出去的是深拷贝，不是引用。

**(b) 并发安全的分类器是 fail-closed 的**（`docs/subsystems/tools.md:61-74`、`:546-553`）：

> Only `true` opts in; **omission, exceptions, non-`true` returns, and invalid `defineTool`
> arguments are exclusive.** … `@returns the **fail-closed** scheduling mode.`

注意「**分类器自己抛异常 ⇒ 归为 exclusive（更保守的那一支）**」。
本项目的 `resolve()` 若将来加任何分类逻辑（比如「这个指标是否可并行取数」），
异常必须落到保守支，不能落到「默认可以」。

**(c) `ToolRestriction` 的两种语义不对称**（`docs/subsystems/tools.md:153-168`）：

> A **deny-only** filter admits later unlisted inherited tools, while an **allow-list**
> excludes them.

即：deny 名单对**将来新增的**工具是放行的，allow 名单对将来新增的是拒绝的。
这是同一个「封闭 vs 开放」的选择在权限层的复现。
另外：`the scope's OWN registrations … stay exempt`——
**限制只作用于继承来的，不作用于自己注册的**，理由是
`so a delegated child keeps the tools it answers through`。

---


## 2. `tool-execution-pipeline.md`（62 行，全文读完；上一轮已全读，本节只记增量）

上一轮已把七段管线抄进 `deepseek-harness.md` §5.3。**本轮增量集中在那张 Mermaid 图的「虚线边」**——
上一轮记的是正常路径，图里真正的信息量在异常路径。

### 2.1 五条 `-.->|throw|` 虚线：抛异常的去向是被规定死的

`docs/tool-execution-pipeline.md:35,41,43,49,50` 五条虚线，**全部指向同一个节点 `normalized`**：

```
guards   -.->|throw|          normalized     (:35)
approval -.->|throw|          normalized     (:41)
pre      -.->|throw|          normalized     (:43)
around   -.->|wrapper throws| normalized     (:49)
post     -.->|throw|          normalized     (:50)
```

`normalized` 节点自己的定义（`:22`）：
`Registry outer normalization / pipeline/result snapshot throws become isError`。
然后 `normalized --> finalize`（`:52`），与正常路径的 `post --> finalize`（`:51`）**汇流到同一点**。

**这就是 §1.4 里那句「including pipeline failures that bypass tools/post-execute」的图形版本。**
换句话说：**图里没有任何一条边能从管线中途直接跑到 `toolResult`**，
所有路径——包括五条异常路径——都必须经过 `finalize → final → toolResult`。
证据的产生点是**图上的割点（cut vertex）**，不是「记得调用一下」。

> 对本项目：这是 `ARCHITECTURE §8.5` 应该采用的表述方式。
> 与其写「下游必须消费证据指针」，不如画出这张图并证明
> **「不存在绕过证据节点到达输出的路径」**。前者可以被违反而不被发现，后者可以被检查。

### 2.2 `denied --> post`：被拒的调用**也走完后半段管线**

`docs/tool-execution-pipeline.md:42`：`denied --> post`。
`denied` 节点的说明是 `denied or approval refused / tool body skipped`（`:15`）。

即：**跳过的只是 `execute()` 函数体，不是管线。**
被拒的调用照样经过 `tools/post-execute` → `finalizeContent` → `tools/result` → `tool/result` 事件。
配合上一轮已记的「`tool/call` 在执行前就写日志」，得到一个完整的对称结构：

| | 被拒的调用 | 成功的调用 |
|---|---|---|
| `tool/call` 事件 | 有 | 有 |
| 走 post / finalize / result | 走 | 走 |
| `tool/result` 事件 | 有 | 有 |
| `execute()` 函数体 | **跳过** | 执行 |

**唯一的差别只有一格。** 拒答在日志里和成功一样完整，这正是 D-003
「拒答是第一类产物」在管线层面的具体做法：不是「额外记一条拒答日志」，
而是**让拒答走同一条管线，只是不执行本体**。

### 2.3 `approval --> guards`：审批通过后**仍然要过守卫**

`docs/tool-execution-pipeline.md:39`：`approval -->|allowed-once| guards`。

注意箭头指向的是 `guards`，**不是 `around`**。
即：人类审批「同意这一次」之后，单调守卫**仍然有机会拒绝**。
`:60` 明写理由：`ctx.approval` resolves asks **before** monotonic guards, and
**owner policy that must not be reordered remains a registered guard**。

**人的同意不能覆盖结构性守卫。** 对本项目：如果将来做「人工复核后放行」，
口径闸门必须排在人工审批**之后**，否则「审批通过」就成了闸门的旁路。

### 2.4 `toolBody --> fsGate --> toolBody`：副作用闸门在工具体**内部**

`docs/tool-execution-pipeline.md:44-45`：

```
toolBody --> fsGate
fsGate   --> toolBody
```

`fsGate` = `fs/write-intent` / `fs/edit-intent`，标注 `tool-fs mutations only`（`:19`）。
这是一个**回环**：工具体运行到「要写文件」那一刻，回调出去问 fs 闸门，得到许可再继续。

`:60` 的说明：`Filesystem read-before-edit checks stay **below** tool-fs on fs/* events.`

**关键在「below」**：读-改前置检查不放在通用 tools 管线上，而是下沉到 fs 这一层。
理由是通用管线看不懂「这次编辑之前有没有读过这个文件」这种领域不变量。
分层是：**通用管线管「能不能调」，领域闸门管「这次操作对不对」。**

> 对本项目直接对应：`tools/pre-execute` 类比「能不能取这张表」，
> `fs/*-intent` 类比「这个口径对不对」。**口径闸门不应该塞进通用工具闸门里**，
> 它需要自己那一层，且位置在工具体内部的副作用点上，而不是调用入口。
> 这与 `deepseek-harness.md` §3.1「闸门放 `agent/pre-step`」不矛盾——
> 那是**入口闸**（问题里没有可解析的指标 ⇒ 根本不进模型），
> 这里是**副作用闸**（要落一个数之前，口径必须已解析）。**两道闸，位置不同，都需要。**
> `ARCHITECTURE` 目前只有入口闸的描述。**副作用闸未落地。**

### 2.5 Code Mode 子调用的三条特殊规定

`docs/tool-execution-pipeline.md:60` 末句：

> Code Mode sends both the reserved `run_code` transport and its serialized sub-calls
> through the pipeline; sub-calls carry the parent token, log `tool/code-dispatch`,
> **return denials as binding rejections**, and **omit `additionalContexts` to preserve
> call/result adjacency**.

三点：

1. **子调用也走同一条管线**——没有「内部调用免检」这回事。
2. **拒绝是 binding rejection**，即在程序里表现为 reject（抛），不是返回一个错误值。
   程序不能把拒绝当成一个可以忽略的返回值继续跑。
3. **子调用不许带 `additionalContexts`**，理由是保持 call/result 相邻。
   这是为了让日志里「一次调用紧跟它的结果」这个不变量不被插入的上下文打断。

第 3 点对本项目的证据链有直接类比：**证据链条目之间不许插入非证据内容**，
否则「这条结论紧跟它的依据」这个可视化不变量就没了。

---

## 3. `event-producer-consumer.md`（76 行，全文读完）

**这份文档本身就是本轮对 Q3 最重要的发现，而且是以「工具」而非「规则」的形式出现的。**

### 3.1 它是什么

一张**生成的**事件矩阵：`Event | Mode | Declared in | Dispatchers | Listeners`，
56 行 harness 事件（`:10-65`）+ 4 行非 harness 事件（`:71-74`）。
生成方式写在末行（`docs/event-producer-consumer.md:76`）：

> Maintenance mode: generated: Cordis event declarations and producer/listener edges are
> **resolved from the repository TypeScript Program**.

不是人写的，是从 TS 编译器的 Program 里解析出来的。所以**它不会与代码漂移**。
`:6` 还补了一句：矩阵**故意覆盖那些绕过 `ctx.emit` 的 contained dispatch 点**
（例如 subagent 生命周期的 containment）——即「走后门发的事件也要出现在表里」。

### 3.2 它顺带暴露了「声明了但没人听」的事件

我按第 5 列（Listeners）为 `-` 统计，56 条事件里有 **7 条零监听者**：

```
$ awk -F'|' 'NR>=10 && NR<=65 {gsub(/^ +| +$/,"",$6); if ($6=="-") print NR": "$2}' \
    docs/event-producer-consumer.md
10:  `agent-loop/config-start-failed`
40:  `session-telemetry/record`
47:  `skills/change`
53:  `system-prompt/change`
54:  `tools/change`
63:  `workflow/log`
64:  `workflow/phase`
（该区间总行数 56）
```

这 7 条里有几条是**故意**留给外部插件的扩展点——例如 `tools/change` 在
`docs/subsystems/tools.md:584` 明写它是给「every agent's next assembly」用的通知，
`session-telemetry/record` 是遥测出口。所以「零监听」**不等于 bug**。
但重点是：**你能一眼看见它是零。**

**这正是本项目刚从 hello-agents 踩到的那个坑的解药。**
那个坑是：「存证机制做对了，指针在接线时被丢掉」。
这类 bug 的特征是**两端各自都对，中间那条边不存在**——
读任何一端的源码都看不出问题，只有把「谁发 / 谁收」并排列出来才看得见。

harness 的做法不是写一条规则说「记得接线」，而是
**生成一张必然暴露断线的表，并把它当文档提交进仓库**。

> **落地建议（未落地）**：本项目应生成一张
> `证据字段 | 产生点 | 消费点` 的表，从源码解析而来，作为 `docs/` 的一份生成产物。
> 消费点为空的行 = 一个被丢掉的指针。
> 落点：`ARCHITECTURE §8.5` 增加「证据指针矩阵」一节 + `rules/commands.md` 增加生成命令。
> 这比在 §8.5 里多写一句「必须被下游强制消费」有用得多。

### 3.3 它还有一个「未声明事件」小节——自曝家丑的部分

`docs/event-producer-consumer.md:67`：
`## Non-harness or undeclared event strings seen in package source`，
下面 4 条：`internal/dispatch`（22 个包监听）、`internal/plugin`、`internal/service`、`internal/status`。
全部 Dispatchers 列为 `-`——**有人听，没人发**（这些由 Cordis 框架自身发出，不在 harness 的声明表里）。

把「我的工具扫到了但我不认识的东西」单独列一节，而不是过滤掉——
这与 §1.2 的 `unsupported keywords reject` 是同一种品味：**不认识的东西要显形，不能静默吞掉。**

### 3.4 顺带证实的两件事（与 `deepseek-harness.md` 的记载对照）

- `agent/pre-step` 是 `waterfall`，有 **13 个监听者**（`:18`），是全表监听者最多的钩子之一。
  上一轮把「语义层闸门放 `agent/pre-step`」当成设计建议，
  **这里证实它是 harness 自己最常用的挂载点**：`plan-mode`、`repeat-tool-reminder`、
  `compaction-basic`、`session-checkpoint-policy` 都挂在这里。
  且 `repeat-tool-reminder` 的路径是 `packages/**guard**/repeat-tool-reminder`——
  **`packages/guard/` 这个目录名本身**说明「守卫」在 harness 里是一类一等公民的包。
- `tools/result` 只有 **2 个监听者**（`:59`：`agent-instructions`、`subagent-in-process-driver`），
  而 `session/event` 有 **23 个**（`:43`）。
  **权威结果的通知面很窄，持久事件的通知面很宽。** 这是有意的分工：
  想旁观就订持久事件，`tools/result` 是给必须在那一刻做事的少数人用的。

---

## 4. `testing.md`（49 行，全文读完）—— Q4 正面回答

**它要求测试证明的是：「发货的那个东西」的行为，不是「代码跑过了」。**
全文围绕这一条，且给了 6 条具名告诫。这份文档 49 行，**多数节标题本身就是一条断言**。

### 4.1 六条「测试通过但证明的不是它声称证明的事」

| # | 原文（`docs/testing.md:行号`） | 它防的是什么 |
|---|---|---|
| 1 | **「Line coverage is necessary, never sufficient — it proves lines ran, not that the feature works as shipped.」**（`:10`） | 覆盖率当验收 |
| 2 | 「An uncovered line is often **dead code the gate is correctly flagging for deletion**, not a missing test to bolt on.」（`:10`） | 为补覆盖率而写无意义测试 |
| 3 | 「A no-key test **proves plumbing**; only a with-key run proves the agent works against a real model.」，并点名 **「the "green unit tests, broken product" class that mocks cannot [catch]」**（`:19`） | 全 mock 的绿灯 |
| 4 | 「A hand-rolled stand-in **proves the bridge moves bytes**, not that the shipping tool behaves as asserted.」（`:23`） | 自造替身 |
| 5 | 「An e2e assertion **re-runs the command or re-reads the file externally**; a keyword probe on the agent's own output **lets a cheating agent pass**.」（`:29`；节标题即 **Verify the world, not the self-report**） | 拿 agent 自述当证据 |
| 6 | **「A guard only guards if the regression actually fails it.」**（`:34`） | 假闸门 |

第 5 条的后半句还有一条很具体的补充：**「Assert untouched files are byte-identical.」**（`:29`）
——不仅要断言「该改的改了」，还要断言「不该改的一个字节都没动」。

### 4.2 第 6 条是本轮最该抄的一句，因为它附带了**可执行的程序**

`docs/testing.md:34` 全文：

> **A guard only guards if the regression actually fails it.** For a plugin without `inject`
> (bundle/composition plugins), a Loader smoke stays green when a default export replaces
> the required named exports — add an explicit `expect('default' in mod).toBe(false)` plus
> an `unwrapExports` round-trip assertion, and **prove it: introduce the regression,
> watch red, revert.**

三件事：

1. 它给了一个**真实发生过的**假闸门例子（默认导出替换具名导出，冒烟测试照样绿），
   并且这个例子指向 `docs/postmortem/0001-acp-default-export-drops-inject.md`（`:19` 引用）。
2. 它给了修法（两条具体断言）。
3. **它给了「验证修法是否有效」的程序：故意引入回归 → 看它变红 → 回退。**

**这条直接对上 `rules/failure-modes.md` F-2「只有真实字段能诚实触发时才声明 flag」。**
F-2 说的是「不要造假 trigger」，testing.md 说的是「**怎么证明你的 trigger 不是假的**」。
F-2 有识别方法但没有验证程序；这三步就是缺的那个程序。

> **落地（未落地）**：`rules/failure-modes.md` F-2 应补一条硬要求：
> 「声明一个 flag / guard / 闸门之前，必须走一遍
> **故意制造违规样本 → 确认闸门变红 → 回退** 三步，并在 PROGRESS 里贴出变红时的真实输出。」
> 同时强化 AC-09（`pre_execute` 拒绝全部已知危险样本）与 `EVAL_CASES §3.3`：
> AC-09 现在只要求「拒绝已知危险样本」，
> **没有要求先证明这些样本在闸门缺失时确实会通过**——否则可能拒的是本来就跑不通的东西。

### 4.3 「测试真正的入口路径」——三条，都是关于「你测的不是发出去的那个」

`docs/testing.md:33-35`：

- 「Product-visible plugins require a **non-unit REAL-composition** test.
  **Hand-built `ctx.plugin(...)` suites are insufficient**」——手搭的组装不算数，
  必须走真实配置文件 + Loader + app/process，并断言
  `model-visible request/log, durable state, or user-visible output`。
- 「**"Real entry path" means the published artifact**: a package `bin` runs built `lib/bin.js`
  under **plain `node`**, exposing failures **tsx masks** (settle races, module resolution,
  swallowed load failures).」——用 tsx 跑 `.ts` 会掩盖三类真实故障。
  还要求 `assert a genuinely-missing config exits non-zero`。
- 「Mock only the expensive or non-deterministic boundary (LLM adapter, network, clock);
  **keep everything downstream real**.」（`:23`）

第二条对本项目 Python 的等价物：**测试里的 `import src.xxx` 与用户实际的入口
（CLI entry point / 打包后的 wheel）是不是同一条路径。**
`docs/testing.md:39` 有一条相关的：测试解析只走 source plane，
理由是走 `exports` 到已构建的 `lib/` 时
`stale artifacts there **load a second copy of module singletons**`——
构建产物与源码同时可见会导致同一个单例被加载两份。

### 4.4 两条测试**所有权**规则（防的是测试自己污染自己）

`docs/testing.md:29`：

> e2e tests own their resources: create the harness in the test, dispose in `afterEach`
> (**even on failure/retry/timeout**); shared fixtures live in a plain `tests/harness.ts`,
> **never another `*.e2e.ts`** (importing a spec **re-registers its `describe` and
> duplicates real API calls**).

「从另一个 spec 文件 import 会重复注册 describe、重复真实 API 调用」——
这是只有真踩过才会写下来的坑。

`docs/testing.md:9`：**「Every registry gets an HMR-safety test (dispose the contributing
fiber, assert cleanup).」** 即**每一个注册表都必须有一条「卸载后确实清干净了」的测试**，
强制，不是可选。对应本项目：任何「注册/登记」型结构
（口径注册表、证据收集器）都要有一条「拆掉之后没有残留」的测试。

同一行还有一条选材偏好：
`Prefer edge cases, error paths, event ordering, concurrency races, and
**permanent tests for contract regressions**`——
契约回归测试是**永久**测试，不因为「这个 bug 早修好了」而删。

### 4.5 快照测试的门槛：**每一个** model / protocol / human 可见的变更都要带一条

`docs/testing.md:49`：

> Every non-trivial model-, protocol-, or human-visible change adds or updates a keyless
> scenario **in the same PR** … Package tests, e2e assertions, mock/test-only compositions,
> and **PR rationale do not replace the assembled transcript**

最后半句值得单独看：**「PR 里的说理不能代替真实装配出来的 transcript」**。
以及 `:12` 的一个取舍细节——`One ACP scenario (text-turn) pins full system-prompt/tool-schema
content; other fixtures tokenize it so an edit churns one line`：
**只让一个场景钉死全文，其余场景 tokenize**，避免改一个字导致几十个快照全变。

### 4.6 它没有说的（附 grep 与命中数）

- **没有出现 `flaky` / `flake`**——不只是 `testing.md`，**整个英文 `docs/` 树里一次都没有**：

  ```
  $ grep -c -i "flaky\|flake" docs/testing.md
  0
  $ grep -rl -i "flaky\|flake" --include="*.md" docs/ | grep -v "\.zh\.md" | wc -l
  0
  ```

  整份文档不讨论「不稳定测试怎么办」，只讨论「测试证明了什么」。
  这是个值得注意的**沉默**：一个有真实 API e2e、浏览器快照、PTY 场景的仓库
  不可能没遇到过不稳定测试，但文档选择不把「容忍不稳定」写成一条政策。

- **没有出现 `mutation testing` / `property-based` / `fuzz`**：

  ```
  $ grep -c -i "mutation testing\|property-based\|fuzz" docs/testing.md
  0
  ```

  §4.2 的「故意引入回归看它变红」是手工版的变异测试，
  但文档没把它上升为一种测试方法学，只作为一条针对性规则出现。


---

## 5. `development.md`（171 行，全文读完）

多数内容是 TS 单仓构建细节（Host/Client 双 aggregate、tsdown、Typert），对本项目 Python 栈无直接价值。
**只有三节值得抄，其中一节是本轮第二重要的发现。**

### 5.1 `ts type-equiv`：把「文档里的类型」与「源码里的类型」用 gate 焊死（本轮次重要发现）

`docs/development.md:163-171`。机制是这样的：

subsystems 文档里那些类型块不是手抄的散文，而是**注册在清单里、由 gate 校验的粘贴**。
`docs/development.md:165`：

> To keep a paste from drifting when source changes, fence it as ` ```ts type-equiv `
> (instead of ` ```ts `) and **register it in `scripts/type-equiv.manifest.json`**
> with the source file and symbol it mirrors

清单条目长这样（`:168`）：

```json
{ "doc": "docs/subsystems/session.md", "symbol": "SessionEvent", "source": "packages/core/session/src/types.ts" }
```

然后（`docs/development.md:171`）：

> `pnpm run verify-type-equiv` (part of `doc-sync`) then extracts that symbol's declaration
> and attached JSDoc from source **via the TypeScript parser** and asserts the block matches both.
> … Comparison ignores whitespace and non-JSDoc comments but **requires every original JSDoc
> comment, including member documentation** … The gate enforces a **1:1 correspondence**
> by document, symbol, and projection between primary blocks and manifest entries …
> **When you change a documented declaration or its JSDoc, the gate fails until you update
> the paste; when you add or remove a primary block, update the manifest in the same change.**

四个设计点：

1. **不是「生成文档」，是「校验粘贴」。** 文档里仍然是人放置的、有上下文的代码块，
   但内容必须与源码逐字（忽略空白）一致。保留了叙述性，去掉了漂移。
2. **JSDoc 也在校验范围内**，而且是 `requires every original JSDoc comment`。
   即「注释里的契约说明」也不许在文档里被简化。
3. **1:1 对应是双向的**：文档里有块而清单里没条目 → 失败；清单里有条目而文档里没块 → 失败。
   不存在「注册了但没人用」的孤儿条目。
4. 有一个 `public-api` 投影模式（`"projection": "public-api"`），
   对类只保留公开成员与 JSDoc、去掉方法体。**投影规则是声明式的，不是靠人手删。**

> **对本项目的直接对应（未落地）**：`references/` 与 `ARCHITECTURE.md` 里现在有大量
> 「粘贴自源码的类型/常量」，靠人肉同步。D-012 已经用 SHA-256 冻结了**文件级**的一致性，
> 但**没有覆盖「文档里引用的某个符号是否还与源码一致」这个粒度**。
> 落点建议：`rules/commands.md` 增加一条 `verify-doc-symbol` 校验，
> 清单形如 `{doc, symbol, source}`，用 Python `ast` 抽取而非正则。
> 尤其适用于 `RefusalCode` 这类「文档里说是 7 项、代码里可能已经 8 项」的枚举。

### 5.2 `FIXME / TODO / XXX` 三级标记，带发布语义

`docs/development.md:155-161`：

> - `FIXME` — an issue that **should block a new release**. A release should not ship with
>   an open `FIXME` unless reviewers explicitly agree the change can be merged anyway.
> - `TODO` — an issue that should be fixed soon, once we have the resources.
> - `XXX` — an issue that we may fix someday; lowest priority, **no commitment**.
>
> Pick the tag that matches the urgency so anyone scanning the code can tell
> **a release blocker from a someday-maybe.**

价值不在于「三个标签」，在于**只有一个标签有强制语义（阻塞发布），另外两个明确声明「不承诺」**。
本项目 `OPEN-ITEMS.md` 的 A 区（阻塞）/ D 区（判据）分区是同一个思路，
但 `XXX` 这一档——**明写「可能永远不做」**——是台账里缺的：
现在所有条目看起来都像迟早要做的，实际不是。

### 5.3 两条钩子/门禁的分工原则

`docs/development.md:115`：

> Apart from the scoped staged-record verification, the hooks **intentionally do not run
> tests, snapshots, documentation checks, builds, or hygiene.** Contributors run the checks
> relevant to the changed behavior **once**; **CI owns exhaustive coverage**, built-artifact
> smokes, and the Node 22.19/24/26 compatibility matrix.

即：**本地钩子只做「快速、与暂存内容强相关」的检查，穷举留给 CI。**
`pre-push` 只跑 `typecheck`（`:111`），连测试都不跑。

`docs/development.md:117` 还有一句很少见的话：

> Contributors can opt into the comprehensive local gate set with `pnpm run check:all`.
> The command is independent of the Git hooks and **is not an agent instruction.**

**「这不是给 agent 的指令」——文档里显式标注哪些内容不是 agent 该照做的。**
本项目 `AGENTS.md` / `CLAUDE.md` 可以借这个做法：
对那些「人可以选择做，但 agent 不应自动执行」的命令加同样的显式标注。

### 5.4 fail-closed 在 Git 层面又出现了一次

`docs/development.md:103`：i18n 配对合并驱动
`It **fails closed** on owner conflicts, non-text merge configuration, or invalid records`。
`:105`：运行时不可用时，`writes Git's ordinary text result, **leaves the sidecar unresolved**,
and prints the recovery path` —— **宁可留一个未解决的冲突，也不猜一个结果**。

至此，fail-closed 在本轮读到的文档里出现了 **5 个不同层面**：
schema 词汇表（§1.2）、并发分类器（§1.5b）、审批通道缺失（上一轮已记）、
不变量配置校验（§6.1）、Git 合并驱动（此处）。**它不是一条规则，是一种贯穿的默认方向。**

---

## 6. `subsystems/invariants.md`（88 行，全文读完）—— **本轮最重要的发现**

这一份直接给出了 `rules/failure-modes.md` **F-2「只有真实字段能诚实触发时才声明 flag」
的机械化实现**。F-2 目前只有「识别方法 + 硬规则」，没有执行机制；harness 有。

### 6.1 它是什么

`ctx.invariants` 是一个**包自有的运行时不变量注册表**。
每个 workspace 包都**必须**发布一个 `./invariant` 伴生插件，
用自己的完整 npm 包名注册检查（`docs/subsystems/invariants.md:5`）。

选择器是正则 allowlist/blocklist（`:11-21`），
且**配置校验 fail-loud**（`:23`）：

> Validation fails loud at service startup: a blank, whitespace-padded, duplicate, or
> invalid entry **throws instead of being skipped**.

但同一行紧接着有一个**故意不报错**的情形，理由写得很清楚：

> A valid pattern **may match no currently loaded package**, so later loading and HMR
> stay deterministic; filters are fixed for the service lifetime.

**「格式错 ⇒ 抛；匹配为空 ⇒ 不抛，且说明为什么」**——
这是一个很值得学的分辨：不是所有「看起来可疑」的情况都该报错，
但**每一个决定不报错的情况都要写明理由**。

### 6.2 那条关键规则：「发布是穷举的，但断言不是合成的」

`docs/subsystems/invariants.md:59`，整段是本轮最该抄的一段：

> Every workspace package owns a `./invariant` companion; **publication and registration
> are exhaustive, but assertions are deliberately not synthetic.** A companion installs
> a check **only when its package owns an observable event or mutable-data relationship**;
> otherwise it exports an **empty installer whose leading comment starts
> `No runtime invariant:`** and explains, **package-specifically**, why nothing is checkable.
> `pnpm run verify-package-invariants` **mechanically rejects**:
> - generated markers,
> - unexplained empty installers,
> - **non-empty installers that omit or ignore the reporter**,
> - incorrect registration names,
> - and incomplete export, publication, dependency, or bundle wiring.

拆解成本项目能用的四条：

| harness 的做法 | 它防住的错 | 对应本项目 |
|---|---|---|
| **每个包都必须有 companion**（穷举） | 「这个模块没人想过要检查什么」 | 每个模块都要回答「你的不变量是什么」 |
| **没有可检查的东西时，写空实现 + `No runtime invariant:` 开头的、包特定的解释** | 「为了交差编一个检查」 | **诚实的「没有」是合法答案，但必须署名说明** |
| gate 拒绝 **generated markers** 与 **unexplained empty installers** | 「复制粘贴一句套话应付」 | 解释必须是这个模块特有的，不能是模板 |
| gate 拒绝 **non-empty installers that omit or ignore the reporter** | **写了一个永远不会失败的检查** | ← **这就是 F-2 的机械化版本** |

最后一条最硬：**一个「非空但从不调用 reporter」的检查，在 gate 眼里等于伪造。**
F-2 说的「拿手边能求值的东西凑一个 trigger，造出的是永远不会正确触发的假规则」——
harness 把这句话变成了一条可执行的检查。

### 6.3 还有一条限定「检查可以断言什么」

`docs/subsystems/invariants.md:5`：

> What a check may assert — **authoritative event streams or mutable data,
> never service or method presence**

**不许断言「某个 service 存在」「某个方法存在」。** 理由不难推：
这类断言在正常启动后恒为真，永远不会失败，等于没写——
正是 F-2 说的「拿手边能求值的东西凑」。
harness 直接在契约层把这类断言划为非法。

> **落地（未落地）**：`rules/failure-modes.md` F-2 应补两条可执行判据：
> 1. **断言对象白名单**：只能断言「真实数据关系」（口径版本与结果哈希的对应、
>    证据条目与结论的引用关系），**不得断言「某函数存在 / 某配置已加载 / 某字段非 None」**。
> 2. **「诚实的没有」是合法答案**：模块确实无可检查项时，写空实现 +
>    以固定前缀开头的、**该模块特有的**理由，并由检查脚本拒绝模板化措辞。
>
> 这两条同时也是 `EVAL_CASES §3.3` 的补充：
> 失败归因分层里应当能区分「闸门拒对了」与「闸门根本不可能触发」。

### 6.4 一个次要但好用的细节：名字预留与过滤解耦

`docs/subsystems/invariants.md:55`：

> The reservation holds **even when filters keep the installer inactive**, so two plugins
> can **never silently claim the same package name**

即：**即便某个检查被配置关掉了，它的名字仍然被占住。**
关掉一个检查不会腾出一个可以被别人悄悄顶替的位置。
对本项目：如果将来做「可配置关闭的口径校验」，被关掉的那一条的**标识必须仍然存在**，
否则「关掉 A」与「A 从未注册过」在日志里就分不开了。

---

## 7. `postmortem/0001-acp-default-export-drops-inject.md`（113 行，全文读完）+ `postmortem/README.md`（18 行，全文读完）

`testing.md:19` 点名引用了这份 postmortem，且它讲的**正是本项目刚从 hello-agents
读出的那个反例的同一类故障：两端都写对了，中间那条线被丢掉了。** 所以本轮把它读完。

### 7.1 postmortem 的**准入条件**是三条硬判据

`docs/postmortem/README.md:9`：

> Write one when a bug is **subtle** (the mechanism is non-obvious and a careful engineer
> would re-derive it the hard way), **systemic** (the reason it escaped is a gap in
> tests/tooling/conventions, **not a one-off typo**), and **costly to rediscover**
> (it cost real debugging time, and would cost it again).

`:7` 还划清了与 Agent Note 的边界：

> A post-mortem is NOT an Agent Note (which records a **deliberate design decision** and its
> rejected alternatives). It is a **backward-looking record of a failure**: what broke,
> the mechanism, **why every safety net missed it**, and the concrete guardrails added
> so the same class of bug **fails loudly next time**.

`:11` 规定每篇开头必须有 30 秒可读完的 Executive summary。

> **对本项目**：`rules/failure-modes.md` 现在是 F-1…F-8 的扁平清单，
> **没有准入条件**——什么错该进、什么错不该进没有判据，
> 长期会变成「所有犯过的错都往里堆」。
> 这三条（subtle / systemic / costly to rediscover）应当直接写进 `rules/failure-modes.md` 开头。
> 尤其第二条 **「not a one-off typo」**：F 类条目必须是**流程漏洞**，不是单次手滑。**未落地。**

### 7.2 故障本身：`inject` 声明是对的，被 loader 的一行 `??` 丢掉了

插件按仓库惯例导出 `name` / `inject` / `Config` / `apply` 四个具名导出，
但**多了一行 `export default apply`**（`docs/postmortem/0001-...md:29-37`）。

Loader 的归一化（`:41-48`）：

```ts
unwrapExports(exports: any) {
  if (isNullable(exports)) return exports
  exports = exports.default ?? exports        // ← prefers `.default`
  ...
}
```

`:50`：

> With a default export present, `exports.default ?? exports` resolves to the
> **bare `apply` function**. A bare function has **no `inject`, no `name`, no `Config`**
> — those lived as *sibling* named exports on the module namespace, and unwrapping to
> `.default` **threw the namespace away**.

结果是 `apply` 在一个 `inject` 为空的 fiber 里运行，第一行 `ctx.agents` 就炸。

**这与 hello-agents 那个反例是同构的**：
声明侧（`inject = [...]` / 证据指针）完全正确，
消费侧（fiber 建立 / 下游接线）也完全正确，
**中间的归一化步骤把声明侧的东西整个丢了，且不报错**。
两端各自读代码都看不出问题。

### 7.3 「为什么每一层测试都没接住」——四条，每条都是一种假绿灯

`docs/postmortem/0001-...md:89-98`，节标题就是 **Why every test missed it (the real failure)**，
开头一句（`:91`）：

> Both bugs share one root process gap: **no test exercised the plugin through its real
> load path or its real call topology.**

四条（`:93-96`）：

1. **手搭插件对象**：`ctx.plugin({ name, inject, apply })` **手动喂了 `inject`**，
   所以**结构上不可能复现 Bug #1**——`unwrapExports` 只有 Loader 会调，`ctx.plugin` 从不调。
   原文补了一句狠的：**「Even `ctx.plugin(NamespaceImport)` would not have caught it.」**
   （即使你把整个命名空间传进去也接不住，因为走的还不是 Loader。）
2. **测试把所有东西平铺挂在一个 root context 上**，于是 fiber 拓扑与真实情况不同，
   Bug #2 的祖先链遍历失败被掩盖。
3. **唯一的无密钥 e2e 只发了 `initialize`**，而 `initialize` 根本不触达 factory，
   「so it sailed past both bugs」。
4. **唯一驱动 `session/new`/`session/load` 的测试是 key-gated 的**，CI 无密钥直接跳过；
   而本地「通过」是因为
   **`a stale built lib/ (with the old code) happened to satisfy module resolution`**
   ——陈旧构建产物让测试假绿。

然后是那句总结（`:98`）：

> **100% line coverage was satisfied the whole time. Coverage proves lines *ran*;
> it says nothing about whether the feature works *the way it ships*.**

（178 个单测全绿 + 100% 行覆盖 —— `:13`。）

### 7.4 加的护栏里，有一条是「已验证它真的会红」

`docs/postmortem/0001-...md:104`：

> **No-key `session/new` e2e over real stdio**: boots the example as a subprocess through
> the real Loader and asserts `session/new` resolves. This fails loudly on Bug #1 with no
> API key. **Verified it fails when `export default apply` is restored.**

——最后这句就是 `testing.md:34` 那条「introduce the regression, watch red, revert」
**被实际执行并写进记录**的样子。不是「我们加了个测试」，是「我们把 bug 放回去看它变红了」。

另一条护栏（`:105`）也值得记：`TSX_TSCONFIG_PATH` in the e2e spawn ——
子进程从临时 cwd 启动时找不到 repo 根的 `tsconfig` paths，
于是 `dsh-*` 导入**静默回退到了已构建的 `lib/`**。
**「静默回退」本身就是故障源。** 这与 `testing.md:39` 的「a second copy of module singletons」
是同一件事的两面。

### 7.5 三条 Lessons 里，两条对本项目适用

`docs/postmortem/0001-...md:112`：

> **A test that constructs a plugin by hand cannot validate how the plugin loads.**
> At least one test must drive the real Loader/export path end-to-end.
> **When the headline operation does not call the model, that test needs no API key
> — so it belongs in CI, not behind a key gate.**

后半句是一条很实用的分类原则：**「不调模型的那部分主流程，必须有无密钥 CI 测试」**。
本项目的口径解析、拒答判定、证据链装配**全部不调模型**，
所以它们**都应当有无密钥的、走真实入口的 CI 测试**，不能藏在需要 API key 的 e2e 后面。

`docs/postmortem/0001-...md:113`：

> **Trust the trace, not the theory.** The elegant shadow explanation was real but was the
> *second* bug; the *first* was a one-line export mistake that a fiber-walk `console.error`
> found in minutes **after hours of plausible-but-wrong reasoning**.

「优雅的解释是真的，但它是第二个 bug」——
这条对上 `rules/failure-modes.md` 里关于「不要基于推断下断言」的几条，
但角度不同：**它讲的不是「别猜」，是「先插桩看真实轨迹，再解释」。**
本项目的 `systematic-debugging` 纪律里应当有这一条的位置。

---

## 8. `defensive-patterns.md`（33 行，全文读完）

`:5` 自我定位：

> Hard-won bug-class rules: **each pattern below is a class of defect that actually shipped
> or nearly shipped here**, stated as **the rule that prevents its recurrence**.

**结构与本项目 `rules/failure-modes.md` 完全同构**（真实犯过的错 → 写成防复发规则），
而且它明确把测试层的对应物指向 `testing.md`（`:5` 末句），
即**「防御模式」与「测试政策」是同一套规则的两个投影**。

七条里，三条对本项目适用：

**(a) 正交结果要各自独立上报**（`:7-9`）：

> A result can be several things at once — a process can time out AND exit 0 because it
> trapped the signal. Surface each independent fact (`timedOut`, `signal`, `exitCode`)
> on its own; **never nest one flag's report inside another's branch**, or a caller reads
> a cut-short run as a clean success.

对本项目直接适用：**「取到数了」「口径已确认」「数据源新鲜」是三个正交事实**，
不能把后两个塞进第一个的 `if` 分支里。否则「取到数」会被读成「答案可信」。
这正是证据链存在的理由，但它必须体现在**返回结构的形状**上，而不只是文档措辞上。

**(b) 公开契约要在两侧都归一化**（`:11-13`）：

> When an implementation receives several representations of one outcome, **normalize them
> before returning through the public API.** … This keeps consumers from **guessing whether
> a caught exception came from the provider, a wrapper, chunk logging, or their own assembly.**
> Document the normalized contract **where the type is defined**; exercise every source form
> through the real consumer.

`LlmAdapter.stream()` 的实现可以抛、也可以发 `finish{kind:'error'}`，
但 `LlmRuntime.stream()` 对外**只以终止 chunk 的形式暴露模型请求失败**；
中间件与消费者自身的缺陷仍然是抛出的。
**即「外部世界的失败」与「我们自己的 bug」在类型上分开**——
这正是本项目 `Refusal`（业务性拒答）与异常（程序缺陷）必须分开的理由，
而 `ARCHITECTURE §8.2` 目前只规定了 `Refusal` 要封闭枚举，
**没有规定「哪些情况必须是异常而不是 Refusal」**。**未落地。**

**(c) 异步状态不是同步状态**（`:15-17`）：

> Never treat `agent/status` or `whenIdle()` as the result of one follow-up …
> An automation caller that truly owns a run **must define its interval explicitly** …
> and **describe any selected output as interval-wide rather than causally attributed
> to that message.** The guard cuts both ways: **if the awaited transition can never occur,
> the wait hangs, so handle the "nothing to wait for" branch explicitly.**

「把输出描述为区间性的，而不是因果归因到那条消息」——
对证据链是一条重要告诫：**如果不能证明某个输出是由某个输入引起的，
就不要在证据链里写成因果关系**，只能写成「同一区间内发生」。
本项目的证据链目前默认「结论 ← 依据」是因果的；
在有并发取数的场景下这个默认可能不成立。

另外四条（`Dispose must reach quiescence`、`Contain callback exceptions in the dispatcher`、
`Never hand untrusted output the ambient environment or predictable paths`、
`Unlink link-shaped paths`）是进程/文件系统层的，本项目当前阶段用不上，
记录在此以备 Phase 3 起子进程或写临时文件时回查。
其中 `:29` 的 `drop *KEY*/*SECRET*/*TOKEN*/*PASSWORD*` 环境变量擦洗
与 `0700 目录 + 随机名 + 'wx'/0o600 独占打开`，在做 PDF 抽取的临时文件时会用到。


---

## 9. `subsystems/approval.md`（170 行，读了 §Identity and outcome / §Per-session policy / §Dispatch and audit / `ctx.approval` 目录项，约 90 行；跳过 `ApprovalRequest` 字段清单与 `approval/request` 事件签名）

选读它是因为它在管线图上就是那个 `approval` 节点（§2.3），
且 grep 显示它是全 docs 里唯一集中讨论 **audit 事件**的子系统页
（`grep -n "audit\|Audit" subsystems/approval.md` → 11 处命中）。

### 9.1 **本轮对 Q3 最硬的一句：拿不到留痕就不许返回决定**

`docs/subsystems/approval.md:122-126`（`ctx.approval.request` 的 JSDoc 内）：

> **A failure that prevents either audit append from committing still rejects
> because returning an unlogged decision would violate the pair.**
> Session contains post-commit observer failures, so an authoritative append
> **cannot reject the request or suppress its matching audit event.**

拆开是两条相反方向的保护：

1. **留痕失败 ⇒ 决定作废。** 不是「决定照给，日志尽力而为」，
   而是「日志写不进去，这个决定就不存在」。
2. **留痕写进去之后，观察者出错不能反过来把决定作废，也不能吞掉配对事件。**
   即留痕的**提交点**是分界：提交前失败 ⇒ 整体失败；提交后失败 ⇒ 被 contain。

配合 `:117-119`：

> The request **requires an open turn** because the audit pair must be enclosed by the
> durable log's commit/replay boundary; **an idle ask rejects before appending anything.**

——**没有开着的 turn 就不许问**，因为那样这对审计事件无处安放。
「先确保留痕有地方放，再开始做事」，不是「做完了找个地方记一下」。

> **对 `ARCHITECTURE §8.5` 的直接可抄结论**：
> 本项目的证据链应当采用同一条契约——
> **「证据条目提交失败 ⇒ 该结论不返回」**，且要明确一个提交点，
> 提交点之后的观察者失败不得反噬结论。
> 现在 §8.5 写的是「证据指针必须被下游强制消费」，
> 这只约束了下游；**上游「写不进就不算数」这一半未落地。**

### 9.2 审计事件是**成对**的，且用专门的 branded id 配对

`docs/subsystems/approval.md:11`、`:13-19`：

> Every request receives a fresh `ApprovalRequestId`. The brand **pairs the
> `approval/asked` and `approval/decided` audit events without making approval ids
> interchangeable with tool-call or agent/session ids.**

```ts
type ApprovalRequestId = Branded<'ApprovalRequestId'>
```

两点：**(a)** 审计的单位是**一对**事件（问 / 答），不是一条；
**(b)** 配对键有自己的 brand，**类型上不能与 callId / sessionId 混用**。

这与上一轮记的 `sourceEventSeqs` 更正（只挂 3 个 surface 事件，
其余 log-only 审计事件靠业务 id 配对）**互为印证**：
harness 的审计溯源有两套机制，`sourceEventSeqs` 是模型可见历史那套，
**branded 配对 id 是 log-only 审计那套**。本项目的证据链更接近后者。

### 9.3 `ApprovalOutcome` 是封闭枚举，且「无法回答」也是其中一支

`docs/subsystems/approval.md:23-28`：

```ts
type ApprovalOutcome = 'allowed-once' | 'rejected' | 'cancelled' | 'unavailable'
```

`:21`：

> `ApprovalOutcome` is **closed and fail-closed**. `allowed-once` grants **only the
> asked-about action**; callers deny on `rejected`, `cancelled`, and `unavailable`.
> **A missing, non-owning, throwing, or non-conforming answerer becomes `unavailable`
> rather than opening the gate.**

`:119-122` 把归一化规则写得更细：
`an aborted signal yields 'cancelled'`，
`a missing or throwing answerer yields 'unavailable' (fail closed)`，
**`a rogue non-vocabulary return value is normalized to 'unavailable'`**。

**四支里三支都是拒绝**，而且「基础设施不可用」是一个**一等的结果值**，
不是异常、不是 `None`、不是「默认放行」。

> **直接对照 `ARCHITECTURE §8.2`（`Refusal` 必须封闭枚举）与 D-017（自建封闭算术解析器）：**
> 本项目的 `RefusalCode` 目前 7 项（且有测试锁死数量）。
> 需要核一件事：**「口径服务不可用 / 数据源不可达」有没有在这 7 项里？**
> 如果没有，它现在多半是走异常路径的——那就与 harness 的做法相反。
> harness 的判断是：**「我答不了」和「我拒绝」在调用方眼里必须同样是一个封闭的结果值**，
> 因为两者都必须导致同一个动作（不放行）。**待核，可能未落地。**

### 9.4 `never` 策略在**波瀑分发之前**执行，所以顺序无关

`docs/subsystems/approval.md:86`：

> The `never` policy is **enforced inside the service before waterfall dispatch**,
> so **even an answerer registered later with `prepend` cannot bypass it.**

即：能被「注册顺序」影响的东西，就一定会被某个人用注册顺序绕过。
真正不可绕的策略必须放在**分发机制之外、之前**。
这与 §2.3（审批通过后仍要过守卫）是同一个道理的两个方向：
**结构性策略不进插槽，进插槽的都是可被排序影响的。**

### 9.5 「不做第二份拷贝」再次出现

`docs/subsystems/approval.md:53`：

> `ApprovalRequest` **deliberately omits tool arguments**: an answerer attaches the prompt
> to the already-streamed tool call **through `callId`** instead of
> **rendering a second copy that could drift.**

与 §1.3 那条「Arguments cannot be rewritten because history, audit, UI, and execution
must agree」是**同一条原则的第二次应用**：
第一次是「不许改」，这次是「不许复制」。
两次的理由都一样：**多一份可能分叉的副本，就多一个「事后看到的不是实际发生的」的机会。**

> 对本项目：证据链展示层**不应该把口径定义、数据快照再存一份**，
> 只应存指针 + 哈希。这一点 D-012 的 SHA-256 冻结已经部分做到了，
> 但**展示层是否也遵守「只存指针」尚未在 ARCHITECTURE 里写死**。

### 9.6 审计事件不进模型上下文

`docs/subsystems/approval.md:88`：

> The audit events are **log-only and do not enter the model transcript.**
> Model-visible behavior is the caller's derived tool result plus the current
> runtime-context snapshot.

**审计给人看和给复核用，不给模型看。** 这是一条清晰的分界：
证据链的完整性目标是「可独立复核」，不是「让模型看到更多」。
本项目容易犯的错是把证据链塞回 prompt 里当上下文——
那既浪费 token，又让证据链的内容影响模型输出，破坏独立性。

---

## 10. `subsystems/subagent.md`（734 行；**只读了 `SubagentStartRequest` 字段块 `:55-99` 与 `:101-110`，约 55 行**，为核实 §1.2 引用的那句被截断的话）

诚实标注：这份文档很长，本轮**只读了上述两段**，其余包括「start-time-vs-runtime
capability split」的完整论述都**未读**。

核实结果：§1.2 引用的 `docs/subsystems/subagent.md:68` 完整上下文是
`outputSchema` 这个字段的 JSDoc（`:67-72`）：

> Object-rooted JSON Schema within `assertObjectJsonSchema`'s enforced subset.
> **Start rejects unsupported schemas or providers without the capability.**
> Data must be plain host-realm JSON; a successful child returns the matching value
> as `SubagentResult.structured`.

**「Start rejects」= 在启动时拒，不是在子 agent 返回结果时才发现。** §1.2 的结论成立。

顺带读到两条与本项目相关的：

**(a) 能力（capability）不具备 ⇒ 启动时拒，三个字段用同一句式**
（`:73-79` `maxDepth`、`:80-87` `toolFilter`、`:88-95` `persona`）：
`Requires SubagentCapabilities.X; **rejected at start otherwise**`。
**同一句式重复三遍**——「可选能力」的默认答案是拒绝，不是静默忽略该字段。
这与 §1.2 的 `unsupported keywords reject` 是同一件事：
**「你要的东西我不支持」必须报错，不能当成「你没要」。**

**(b) 「one visibility」：可见性与可执行性同源**（`:80-87`）：

> In-process backends apply it as a scoped `tools.restrict()` in the child's creation window:
> the named tools **vanish from the child's prompt AND refuse to execute (one visibility)**,
> with **loud unknown-name validation.**

即：被过滤掉的工具**既不出现在 prompt 里，也拒绝执行**，
而且这两件事**来自同一个解析器**，所以不可能出现「prompt 里没有但还能调」
或「prompt 里有但一调就拒」。`:99` 把这条的设计理由命名为
**「visibility-not-authority rationale」**。

> **对本项目**：口径层同理——「模型在 prompt 里看到的可用指标集」
> 与「取数层实际允许的指标集」**必须由同一个解析器产出**。
> 如果是两处各写一份列表，早晚分叉，而分叉的表现是「模型答了一个它本不该能答的指标」。
> 检查一下 `PROJECT_SPEC` / `ARCHITECTURE` 里这两个集合是不是同源。**待核。**


---

## 11. 未读 / 只看了标题的清单（诚实标注）

`docs/subsystems/` 共 **46 页**（清单见 `docs/subsystems/README.md:9-53`，本轮全文读完该 README）。

| 状态 | 文件 |
|---|---|
| **本轮全文读完** | `subsystems/tools.md`、`subsystems/invariants.md`、`subsystems/README.md` |
| **本轮部分读** | `subsystems/approval.md`（170 行读约 90）、`subsystems/subagent.md`（734 行读约 55） |
| **更早几轮已读**（不在本轮范围） | `subsystems/session.md`、`architecture.md` |
| **只看了 `subsystems/README.md` 里的一行描述（= 只看了标题）** | 其余 **41** 页，即 46 减去上面已读的 5（`tools` / `invariants` / `README` / `approval` / `subagent`）。其中体量最大、也最可能有料的是 `core.md`(1070)、`typert.md`(336)、`session-query.md`、`session-projection.md`、`session-telemetry.md`、`sandbox.md`、`skills.md`、`compaction.md`、`extensions.md`、`filesystem.md` |
| **完全未读**（`docs/` 顶层） | `capability-seams.md`(471)、`config-catalog.md`(132k 字节)、`module-graph.md`(124k 字节)、`tool-catalog.md`(80k 字节)、`api-gateway.md`、`agent-lifecycle.md`、`persistence-catalog.md`、`glossary.md`、`graph-atlas.md`、`rescope.md`、`web-styling.md`、`cordis-primer.md`、`cordis-api/`、`cordis-tutorial/`、`user/`、`i18n/`、`AGENTS.md` |
| **本轮只读了 2 行**（为核实 MCP 入口） | `cookbook/extension-cookbook.md`（129 行，读了 `:9` 与 `:121`） |
| **本轮全文读完（不在原范围，因 `testing.md` 引用而追加）** | `postmortem/README.md`(18)、`postmortem/0001-...md`(113)、`defensive-patterns.md`(33) |
| **未读的 postmortem** | `0002-js-expression-disabled-filesystem-tools.md`(47)、`0003-web-agent-gui-feedback-loop.md`(53)、`0004-landlock-partial-notice-misclassified-child-failures.md`(55) |

**下一轮最该读的三份**（按对本项目四个问题的相关度）：

1. `docs/capability-seams.md`（471 行）—— 「capability 事件挂到缝上」这个抽象的定义；
   本项目的「口径层 / 抽取层 / 证据层」三缝分层直接对应。
2. 剩余三份 postmortem —— 每份都是一类「安全网全漏」的实证，
   `0002`（一个字面量把文件系统工具永久禁用了）与
   `0004`（部分强制的通知把子进程失败误分类了）听起来都与本项目的降级/误分类问题同构。
3. `docs/subsystems/session-telemetry.md` —— `session-telemetry/record` 是一个
   **redact waterfall**（`README.md:53`），即「外发前脱敏」的缝，
   与本项目「证据链可外发到什么程度」相关。

---

## 12. 对 finaudit-agent 的启示

**每条都标注落地点。已落地 → 具体编号；未落地 → 明写「未落地」并说明该落到哪里。**

### 已落地（本轮只是补上了「为什么」或提供了更强的论证）

| # | 启示 | 出处 | 落地点 |
|---|---|---|---|
| 1 | 拒答理由必须是封闭枚举 + 结构化定位（「哪一类」+「哪一处」都要有） | `tools.md:408`（`JsonSchemaError` 报 **every schema path**）、`:149`（三种错误码） | **已落地**：`ARCHITECTURE §8.2` + `src/semantic_layer/resolve.py:38-53`。已核：`RefusalCode` 7 项封闭，`Refusal` 另带 `metric_id` / `condition_index` 两个机读定位字段——**「哪一处」这一半本项目已经有了**，与 harness 同构 |
| 2 | 闸门不放事件顺序，放调用签名 | `tools.md:378-389`（`PreToolDecision` 三分支无一带 args） | **已落地**：`ARCHITECTURE §8.1`，四条源码级理由已在其中 |
| 3 | 拒绝要留痕，降级成功也要留痕 | `tool-execution-pipeline.md:42`（`denied --> post`，被拒调用走完整条管线） | **已落地**：`ARCHITECTURE §8.3` 的三分终态 `completed / completed_degraded{cause} / refused{code}`；D-003 |
| 4 | fail-closed 放在**读入边界**，不放写入侧 | 本轮又见 5 例（§5.4 汇总） | **已落地**：`ARCHITECTURE §8.4`、`D-018` |
| 5 | 「口径定义 / 数据快照只存指针 + 哈希，不存第二份拷贝」 | `approval.md:53`（`deliberately omits tool arguments … a second copy that could drift`） | **部分已落地**：`D-012` 的 SHA-256 冻结做到了产物级。**展示层「只存指针」未写进 ARCHITECTURE**，见下表第 12 条 |

### 未落地（本轮新增，按价值排序）

| # | 启示 | 出处 | **该落到哪里** |
|---|---|---|---|
| 6 | **「假闸门」有机械化的识别规则**：非空但从不调用 reporter 的检查 = 伪造；不许断言「service/method 存在」这类恒真的东西；确实没有可检查项时必须写空实现 + 该模块特有的、以固定前缀开头的理由，模板化措辞由脚本拒绝 | `invariants.md:59`、`:5` | **未落地。** 落 `rules/failure-modes.md` **F-2**，补两条可执行判据（断言对象白名单 + 「诚实的没有」的合法形式）。这是本轮最高价值的一条——F-2 目前只有识别方法，没有执行机制 |
| 7 | **「闸门只有在回归真的被它挡住时才算闸门」**，且附三步验证程序：故意引入违规 → 看它变红 → 回退 | `testing.md:34`；实际执行的样子见 `postmortem/0001:104`「Verified it fails when `export default apply` is restored」 | **未落地。** 落 `rules/failure-modes.md` **F-2** 与 **F-8**（跑了门禁但没让它挡住后面的动作），并强化 **AC-09**：现在只要求「拒绝全部已知危险样本」，须补「先证明这些样本在闸门缺失时确实会通过」。同时进 `EVAL_CASES §3.3` 的失败归因分层：要能区分「闸门拒对了」与「闸门根本不可能触发」 |
| 8 | **生成一张「产生点 / 消费点」矩阵，让断线自己显形**，而不是写规则要求下游记得接线 | `event-producer-consumer.md:76`（从 TS Program 解析生成）+ 本轮统计出 56 条事件里 7 条零监听 | **未落地。** 落 `ARCHITECTURE §8.5` 新增「证据指针矩阵」一节 + `rules/commands.md` 增加生成命令（Python `ast` 解析 `field_id` / `anchor_page` 的产生与消费点）。**§8.5 目前的写法「必须被下游强制消费」是一条纪律，可以被违反而不被发现；矩阵是可检查的** |
| 9 | **留痕提交失败 ⇒ 结论作废**（上游那一半） | `approval.md:122-126`「returning an unlogged decision would violate the pair」+ `:117-119`「an idle ask rejects before appending anything」 | **未落地。** 落 `ARCHITECTURE §8.5`。§8.5 现在只约束下游消费，**上游「写不进就不算数」完全没写**。要连带明确一个提交点：提交前失败 ⇒ 整体失败，提交后观察者失败 ⇒ 被 contain，不得反噬 |
| 10 | **「基础设施不可用」必须是拒答枚举的一支，不是异常** | `approval.md:21`、`:28`（`unavailable` 是四支之一）、`:119-122`（rogue 返回值归一化为 `unavailable`） | **决策已落地（D-022 决策一，提交 `c6d5c6e`），实现待 Phase 1.5。** **回标（2026-08-23，T-5）**：已核 `RefusalCode` 目前仍为 7 支，`UNAVAILABLE` 尚未进代码——**这不是 `STALE`，是「决策已落、实现待阶段」**，见 `LANDING-BACKLOG` L-47。另：原文担心的「D-012 冻结校验与『枚举恰为 7 个』的测试会挡住这个改动」，D-022 已实测推翻——`len(RefusalCode)` / `list(RefusalCode)` 全仓零命中，不存在那条锁死测试。以下为原文，保留不改：**已核实缺口**：`grep -rn "UNAVAILABLE\|NOT_AVAILABLE\|SOURCE_MISSING" --include="*.py" src/` → **0 命中**。现有 7 个 `RefusalCode` 全是「口径/数据本身有问题」，没有一支表示「口径服务或数据源不可达」。落 `src/semantic_layer/resolve.py` 的 `RefusalCode`（**注意：D-012 的冻结校验与「枚举恰为 7 个」的测试会挡住这个改动，须先走决策变更**）+ `ARCHITECTURE §8.2` |
| 11 | **可见性与可执行性必须同源**：模型 prompt 里看到的指标集与取数层允许的指标集由**同一个解析器**产出 | `subagent.md:80-87`「vanish from the child's prompt AND refuse to execute (**one visibility**)」、`:99`「visibility-not-authority rationale」 | **未落地（且待核）。** 落 `ARCHITECTURE` 新增一节。先核：`PROJECT_SPEC` / `ARCHITECTURE` 里这两个集合现在是不是两处各写一份。分叉的表现是「模型答了一个它本不该能答的指标」——这类 bug 不会报错 |
| 12 | **两道闸，位置不同**：入口闸（问题里无可解析指标 ⇒ 不进模型）+ **副作用闸**（要落一个数之前，口径必须已解析，闸门在计算体内部的落数点上） | `tool-execution-pipeline.md:44-45`（`toolBody --> fsGate --> toolBody`）、`:60`（`read-before-edit checks stay **below** tool-fs`） | **未落地。** `ARCHITECTURE §8.1` 只描述了入口闸。落 `ARCHITECTURE` 新增 §8.6「副作用闸」。理由：通用管线看不懂领域不变量，领域闸门必须自己一层且贴着副作用点 |
| 13 | **文档里粘贴的类型/枚举，用 gate 与源码焊死**（清单 `{doc, symbol, source}` + 解析器提取 + 1:1 对应校验） | `development.md:163-171`（`ts type-equiv` + `verify-type-equiv`） | **未落地。** 落 `rules/commands.md` 新增 `verify-doc-symbol`，用 Python `ast` 而非正则。D-012 的 SHA-256 只覆盖**文件级**，覆盖不了「文档里说 `RefusalCode` 是 7 项、代码里已经 8 项」这个粒度——而第 10 条恰好就要动这个枚举 |
| 14 | **postmortem 的准入条件是三条硬判据**：subtle（机制非显然）+ systemic（漏网原因是流程/工具缺口，**not a one-off typo**）+ costly to rediscover | `postmortem/README.md:9`、`:7`（与「设计决策记录」划清界限） | **未落地。** 落 `rules/failure-modes.md` 开头。现在 F-1…F-8 是扁平清单、**没有准入条件**，长期会变成「所有犯过的错都往里堆」。尤其 `not a one-off typo` 这条 |
| 15 | **不调模型的主流程，必须有无密钥、走真实入口的 CI 测试** | `postmortem/0001:112`「When the headline operation does not call the model, that test needs no API key — so it belongs in CI, not behind a key gate」 | **未落地。** 本项目的口径解析、拒答判定、证据链装配**全部不调模型**，因此都属于这一类。落 `rules/commands.md` 与 `gates.yml`（D-021 已建 CI 门禁，此条是给它加内容） |
| 16 | **正交事实各自独立上报，不许把一个塞进另一个的分支里** | `defensive-patterns.md:7-9`（`timedOut` / `signal` / `exitCode`） | **未落地。**「取到数了」「口径已确认」「数据源新鲜」是三个正交事实，不能嵌套。落 `ARCHITECTURE §8.3`（终态三分已经是这个方向，但只分了终态，没分这三个正交维度） |
| 17 | **「外部世界的失败」与「我们自己的 bug」在类型上必须分开** | `defensive-patterns.md:11-13`（`LlmRuntime.stream()` 只以终止 chunk 暴露模型请求失败；中间件与消费者缺陷仍然抛出） | **已落地（D-022 决策二，提交 `c6d5c6e`）。** **回标（2026-08-23，T-5）**：本条写作时确为缺口；D-022 已把界线定为**「是否可预期结果」**——检验方法是「能不能写进文档告诉用户这可能会发生」，能写就是 `Refusal`，写不出来（意味着我们写错了）就是异常。并明写了不按「是否在语义层内部」划（会与第 10 条的 `UNAVAILABLE` 直接矛盾）、不按「是否可重试」划（那是运行时属性，契约会不稳）。**标注此前未回改，属 T-1 查出的 4 条 `STALE` 之一。** 以下为原文，保留不改： `ARCHITECTURE §8.2` 规定了 `Refusal` 要封闭枚举，但**没规定「哪些情况必须是异常而不是 Refusal」**。缺了这一半，第 10 条很容易被做成「把所有异常都塞进 RefusalCode」，那是反向的错 |
| 18 | **不能证明因果时，证据链只能写「同一区间内发生」，不能写成因果归因** | `defensive-patterns.md:15-17`（`describe any selected output as interval-wide rather than causally attributed to that message`） | **未落地。** 本项目证据链默认「结论 ← 依据」是因果的；并发取数时该默认不成立。落 `ARCHITECTURE §8.5` |
| 19 | **审计事件 log-only，不进模型上下文** | `approval.md:88` | **未落地。** 落 `ARCHITECTURE §8.5`。防的是「把证据链塞回 prompt 当上下文」——既费 token，又让证据内容影响模型输出，破坏复核的独立性 |
| 20 | **关掉一个检查 ≠ 该检查从未存在**：被过滤掉的注册仍然占住名字 | `invariants.md:55` | **未落地。** 落 `ARCHITECTURE §8.5`。若将来做可配置关闭的口径校验，被关掉那条的标识必须仍在日志里，否则「关掉 A」与「A 从未注册」分不开 |
| 21 | **`FIXME / TODO / XXX` 三级，其中 `XXX` 明写「可能永远不做、无承诺」** | `development.md:155-161` | **未落地。** 落 `docs/agent/OPEN-ITEMS.md`。现在 A 区（阻塞）/ D 区（判据）两分，缺「可能永远不做」这一档——导致所有条目看起来都像迟早要做 |

### 刻意不借的（附理由，遵守 `references/README.md` 第 4 条）

| 不借什么 | 出处 | 理由 |
|---|---|---|
| `tools/code-dispatch-log`：允许 listener **只改持久日志里的那份内容**，程序与模型看到的都不变 | `tools.md:601-622`（`Only the logged copy is affected`） | harness 的日志目标是「重建对话」，spill 场景下日志存 preview + locator 是合理的。**本项目的日志目标是「独立复核计算」，日志与实际值必须一致。** 抄了就等于给自己开了一个「日志上写的不是真算的」的合法口子——这与 D-003 直接冲突 |
| 「一切可替换」的插件化（连 agent loop 都能换） | 上一轮已记（`deepseek-harness.md` §4），本轮 `invariants.md` 的 allowlist/blocklist 又是一例 | 本项目的口径闸门**必须不可替换、不可绕过**，那是它存在的理由。可配置性在这里是缺陷。第 20 条借的是「被关掉的东西仍然留名」，**不是**「可以关掉」 |
| 46 页子系统文档 + 逐符号 gate 的文档规模 | `subsystems/README.md`、`development.md:163-171` | 第 13 条借的是**机制**（清单 + 解析器校验），不是**规模**。本项目 14 个 `.py`，照 harness 的粒度写文档会直接触发 D-009 的 ceremony 红线（任一阶段流程开销 > 产出时间 30% ⇒ 删掉贡献最小的一套） |

---

## 13. 四个带着读的问题 —— 直接回答

**Q1 封闭 schema 的边界怎么守？**
- **九种节点怎么穷举**：不是 `switch` 的完整性，是**联合类型只有九个成员**，且声明在单一文件
  （`tools.md:100`、`:104-116`）。附三条把封闭钉死的约束：`enum`/`const` 标量必须与节点类型匹配、
  显式 object 必须**显式声明** `additionalProperties`、参数根是唯一的 implicit open 例外。
- **外来 schema 在哪个边界被拒**：**注册边界**（`ctx.tools.register()`），不是调用边界。
  MCP 工具走的就是这个入口（`cookbook/extension-cookbook.md:9`、`:121`），
  子 agent 在 `start()` 时拒（`subagent.md:68`）。**没有第二条入口**——
  封闭性不靠「大家都用 `defineTool`」的约定，靠「唯一那扇门自己会检查」。
- **错误怎么报**：结构化。`JsonSchemaError` 报出**每一条**不合法的 schema path，
  `ToolArgsError`→`INVALID_ARGS`，`ToolOutputError`→`INVALID_TOOL_OUTPUT`（`tools.md:408`、`:149`）。
  且默认方向是拒：**`unsupported keywords reject instead of being accepted without enforcement`**。

**Q2 「参数不可改写」怎么在类型上做到？**
四道锁（`tools.md:385-389` / `:283-290` / `:299-308` / `:315-324`），详见 §1.3：
决策联合不带 args + 参数跨 lossless-JSON 边界后 deep-freeze +
`Omit<ToolExecution,'signal'> & {signal}` **用类型运算精确只解冻一个字段** + 守卫入参 `Readonly`。
理由是**时序论证**而非道德论证：`tool/call` 在执行前就已入日志、已上屏，
此刻改写必然导致四方分叉（`tools.md:378-389` 的 doc comment 内）。
**这对 `ARCHITECTURE §8.1` 是个校正**：签名闭合只是第一道锁，
若被传进签名的对象本身可写，签名就是装饰。

**Q3 证据/留痕在哪一步产生，能不能被绕过？**
- **产生点是 registry 自己**，不是任何 listener（`tools.md:372`、`:374`）。
- **不能绕过**，且有图形证明：`tool-execution-pipeline.md` 里五条 `throw` 虚线**全部汇流到
  `normalized`**，再与正常路径汇流到 `finalize`（`:35,41,43,49,50,51,52`）——
  **不存在从管线中途直接到达 `toolResult` 的边**。证据节点是图上的割点。
- **被拒的调用也走完整条管线**（`:42` `denied --> post`），唯一差别是不执行函数体。
- **留痕环节自己失败 ⇒ 产生一条「失败的痕」，不是「没有痕」**（`tools.md:372`）；
  `finalizeContent` 对**每一个** normalized outcome 都调用一次，
  **包括那些绕过了 `tools/post-execute` 的管线失败**（`tools.md:41-45`）。
- **最强的一句在 approval**：`approval.md:122-126`
  **「留痕写不进去 ⇒ 这个决定作废，因为返回一个没被记录的决定会破坏配对」**。

**Q4 `testing.md` 要求测试证明什么？有没有「测试通过但证明的不是它声称证明的事」的告诫？**
**有，六条**（§4.1 表格）。核心是「证明发货的那个东西的行为，不是证明代码跑过了」。
最硬的两条：`Line coverage … proves lines ran, not that the feature works as shipped`（`:10`）与
**`A guard only guards if the regression actually fails it`（`:34`）**，
后者附带可执行的三步程序：**故意引入回归 → 看它变红 → 回退**，
并且在 `postmortem/0001:104` 有真实执行记录（178 个单测全绿 + 100% 行覆盖的情况下，产品完全不可用）。
另有两条否定发现（附 grep）：整个英文 `docs/` 树里 **`flaky`/`flake` 零命中**，
`testing.md` 里 **`mutation testing`/`property-based`/`fuzz` 零命中**。
