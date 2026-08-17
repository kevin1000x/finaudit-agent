# deepseek-harness `.agents/notes/**` 系统性普查

> 目的：`.agents/notes/**` 是 deepseek-harness 全部设计决策的「为什么」存放地。
> 本文对其做**系统性覆盖普查**（不是关键词打捞），按六个主题抽取对 finaudit-agent 有用的输入。
>
> 仓库快照位置（只读）：`.../scratchpad/deepseek-harness`
> 普查日期：2026-08-18

---

## 1. 完整清单与覆盖度（第一等产物）

### 1.1 总数是怎么数出来的

```
find .agents/notes -type f            → 1985 个文件
find ... -name "*.md" ! -name "*.zh.md" → 679 个英文正文文件
```

1985 与 679 的差额来自**每篇笔记的三元组**：每个 note 都有
`X.md`（英文）+ `X.zh.md`（中文镜像）+ `X.i18n.yaml`（一致性记录 sidecar）。
中文与 sidecar 是同一决策的翻译/哈希记录，不是独立笔记。
**因此本普查的分母 = 679。**

679 里有 5 个不是 Agent Note 本体（`README.md` ×2 语言体系文件、
`AGENTS.md` ×3、`implemented/CLAUDE.md` ×1 —— 实际为 4 个 AGENTS/CLAUDE + README），
其余 **674 篇是带 `# Agent Note:` / `Status:` 头的正式笔记**。

### 1.2 按目录分布（英文正文，679）

| 目录 | 篇数 |
|---|---|
| `.agents/notes/`（README / AGENTS） | 2 |
| `archived/`（AGENTS.md） | 1 |
| `archived/architecture` | 14 |
| `archived/bug-fix` | 19 |
| `archived/feature` | 54 |
| `archived/process` | 20 |
| `archived/simplification` | 27 |
| `archived/testing` | 8 |
| `implemented/`（AGENTS.md + CLAUDE.md） | 2 |
| `implemented/architecture` | 125 |
| `implemented/bug-fix` | 76 |
| `implemented/feature` | 169 |
| `implemented/process` | 69 |
| `implemented/simplification` | 46 |
| `implemented/testing` | 12 |
| `proposed/architecture` | 9 |
| `proposed/feature` | 4 |
| `proposed/process` | 7 |
| `proposed/simplification` | 2 |
| `proposed/testing` | 2 |
| `rejected/feature` | 1 |
| `rejected/simplification` | 10 |
| **合计** | **679** |

### 1.3 覆盖度（分三档，如实标注）

<!-- COVERAGE-TABLE -->
（本节在普查过程中逐组更新，见文末 §5「未读清单」）

---

## 2. 体系本身：Agent Note 制度的设计（读自 `.agents/notes/README.md`，全文）

在进入六个主题之前，必须先记录**这套笔记制度本身**的设计——它就是一个
「决策证据链」系统，与 finaudit 要做的「答案证据链」同构。

- **路径即元数据**：`{lifecycle}/{class}/yyyy-mm-dd-topic-title.md`。
  生命周期（proposed / implemented / rejected / archived）与类别（feature / bug-fix /
  simplification / architecture / process / testing）**都编码在路径里**，
  且 class 是**封闭集合**，由 `scripts/agent-note-tree.ts` 定义，
  「classification gate rejects other folders」——即目录结构本身是被 gate 强制的封闭枚举。
- **`Status:` 行三选一**，且**必须与所在目录一致，gate 交叉校验**：
  `proposed` / `implemented` / `rejected — <一行理由>`。
  只有 rejected 这一种 status 带内容，理由是
  「a rejected Agent Note's verdict is the fact readers come for」。
- **`## Alternatives considered` 是强制段**：
  「A decision recorded without what it beat invites re-litigation — the failure Agent Notes exist to prevent.」
  且**「Alternatives are recorded, never invented」**——2026-07-05 格式化之前、
  确实无法从记录重建备选方案的老笔记，必须写死这一行注释：
  `<!-- agent-note-format: alternatives-not-recorded (pre-format Agent Note) -->`，
  gate 只对旧文件放行。**这是「不许编造证据、宁可显式标注缺失」的制度化实例。**
- **归档 = 冻结 + 哈希**：`archived/` 一旦封存**永久冻结**，
  由 `scripts/verify-archived-agent-notes.ts` 校验
  「封闭 class 树、完整三元组、归档元数据、**sidecar 哈希**、**append-only 冻结内容 manifest**」。
  归档时只允许四种内容改动（移动三元组、保留 `Status: implemented`、
  插入 `Archived: YYYY-MM-DD`、重录 sidecar 并修复入链），别的一律不许。
  且明确规定：**归档笔记「不得作为当前行为的依据」**（`do not treat it as authority for current behavior`）。
- **删除的前置条件极重**：一篇 implemented 笔记只有被完全取代才可合并删除，
  且删除前 owner 必须**逐项保留**：每一条 rationale、alternative、consequence、
  required verification、named coverage gap；修复每一条入链；同步删中文与一致性记录。
  「**Consolidation must not rewrite the old file into its opposite or rely on git history as the only copy of rationale.**」
  —— 即 **git history 不算证据留存**。
- **没有 INDEX**：显式拒绝集中式索引（`implemented/process/2026-07-19-remove-generated-agent-note-index.md` 拥有该理由），
  理由是活的目录树本身就是清单。

> 对 finaudit 的直接映射：证据链目录结构、口径枚举、
> 「备选方案必须记录、不可编造、缺失要显式标注」、
> 「归档件冻结+哈希+append-only manifest」、
> 「历史版本控制不算证据副本」——这五条都可以直接搬。

---

## 3. 六个主题的命中篇目

（逐组读完后追加）

---

## 4. 对 finaudit 的具体输入

（逐组读完后追加）

---

## 5. 未读清单（我不能置评的部分）

（最终填写）
