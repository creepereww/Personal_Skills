---
name: local-skills-hub
description: 本机全局 skill 仓库（~/.skills）的使用规则与强制约束。动手前必读 —— 涉及新增/修改/删除任何 skill、用 skill-creator 创建 skill、排查 skill 没生效、把 skill 推送到其他电脑时。含一条不可违反的红线：不得直接编辑 store/ 下的文件，发现问题只能写 proposals/。
version: v0.8
---

# Skills Hub

全机器的 skill 只有一份实体，放在 `~/.skills/store/`，通过 junction 挂给各个 agent。

## 结构

```
~/.skills/store/local/   纯本地 skill
~/.skills/store/fork/    从 GitHub 派生的 skill（含 .upstream 溯源）
~/.skills/store/cache/   远程 skill 缓存（不进 Git）
~/.skills/routing.json   各 agent 挂载点
~/.skills/registry.json  远程 skill 清单
~/.skills/proposals/     待审批提案
```

## 🚫 修改 skill 的授权规则

skill 分两个成熟度，**权限不同**：

| 阶段 | version | 谁能改 |
|---|---|---|
| **完善中** | `v0.x` | 模型可**自由增删内容** —— 新建 skill、还在补充内容的阶段，不必每次确认 |
| **已完善** | `v1.0+` | 改动**必须先经用户确认**：说清改哪个文件、删什么、加什么 |

**晋级由用户点头，不看版本号走没走满。** `v0.x` 可以一直是 `0.10`、`0.11` 地往上加；
简单的 skill 也可能 `0.2` 之后直接跳 `1.0`。模型只能**建议**"它稳定了，要不要转 v1.0"，**不能自己升**。

**小改例外**（两种阶段都可直接做）：错别字、补一行说明、修失效的路径。

**大改必须确认**（针对已完善的 skill）：删章节、重写、拆分、改挂载范围/受众、动脚本或路由配置。

### ⚠️ 两类规则别混为一谈

**成熟度决定的是「流程」**（改之前要不要问用户），**不决定「内容」**。内容规范与成熟度无关，
`v0.x` 的 skill 一样要守：

- 不写日期、不写 changelog、不写改动原因、不写第一人称复盘
- 命名合规、`version: vX.Y` 格式正确、description 长度合规
- **只放稳定的方法，不放会过期的数据**（体积、条数、版本号这类 → 放到项目自己的文档里）

**教训**：曾有个 agent 单独加载某个 `v0.x` skill 做任务，往里塞了一整节"当前实况"（含日期和一堆会变的计数）——
它是好意（那些数字确实有用），但 ① 它没读到本 skill（skill 间无依赖，见下），② "完善中"被理解成了"随便写"。
结果：skill 里混进了会过期的内容，审计才抓出来。

### ⚠️ 每个 skill 都要能"自解释"

因为 skill 之间没有依赖机制（见下），**不能指望改某个 skill 时模型会去读本 skill**。
所以每个**会被单独加载**的 skill，都该在开头用几行写清"改我时要守什么"（尤其禁止项和易错点）。
派生版 skill-creator 就是这么做的（开头内嵌了本机适配说明）。

**红线不变**：任务执行过程中"路过"某个 skill、发现不好用就顺手改 —— **无论成熟度**，
一律只能写 `~/.skills/proposals/<skill>.md` 等人批准：

```markdown
# proposal: <skill 名>
## 症状
（哪一步失败或产出不对）
## 建议改动
（要增补/修改什么）
## 待插入位置
（在哪个章节）
```

判断标准只有一条：**用户是否知道并同意这次改动**。

**为什么这么分**：新建 skill 处于"边写边试"，每次确认会拖死迭代；
而已发布的 skill 是资产，一次误删就没了（尤其删掉的可能是"看起来没用但实际关键"的内容）。

### 版本号怎么配合成熟度

- **完善中（`v0.x`）**：无论局部补充还是结构重写，**都只动小数位**（`0.9` → `0.10` → `0.11`）。
  整数位保持 0，**直到用户点头**
- **已完善（`v1.0+`）**：局部补充 Y+1；结构重写 X+1（如 `v1.4` → `v2.0`）
- 一律**不写 changelog、不写日期、不写改动原因** —— skill 正文要占上下文，能省则省

## 常用操作

```powershell
pwsh C:\Users\cgw06\.skills\scripts\link.ps1            # 刷新挂载（新增/改名后必做）
pwsh C:\Users\cgw06\.skills\scripts\link.ps1 -DryRun    # 先看会做什么
pwsh C:\Users\cgw06\.skills\scripts\sync.ps1            # 拉取 + 刷新
pwsh C:\Users\cgw06\.skills\scripts\sync.ps1 -Commit "msg"   # 提交 + 同步
```

## 新增一个本地 skill

1. 在 `store/local/` 建目录 `local-<slug>/`
2. 写 `SKILL.md`，frontmatter 必须含 `name`（与目录名逐字符一致）、`description`、`version: v1.0`
3. 跑 `link.ps1` —— 四个 agent 同时就位

## 用 skill-creator 创建 skill 时

本机用的是派生版 `local-skill-creator-anthropics-skills`（远程原版已停止挂载）。它开头**内置了本机适配说明** —— 落盘位置、命名正则、version 字段、workspace 该放哪、不打包 .skill，照它走就行，这里不重复。

## 内容要分清"跨 agent 通用"还是"某个 agent 专属"

skill 是**一份实体挂给所有 agent** 的（`routing.json` 的 `defaults.clients` 列了 4 个）。所以写之前先问一句：
**换成另一个 agent 来读，这段还有用吗？**

- **通用**（路径格式、junction 用法、目录位置、机器坐标…）→ 留在 skill 里
- **只对某个 agent 成立** → **拆出去**单独建 skill，并在 `routing.json` 里把它限制给那个 agent：

```json
"skills": {
  "local-workbuddy-quirks": {
    "clients": ["workbuddy"],
    "why": "内容全是 WorkBuddy 宿主特有的，别的 agent 读它纯属噪音"
  }
}
```

`link.ps1` 会照这个名单挂载：不在名单里的 client **不挂**；如果之前已经挂过，还会顺手摘掉（输出里显示 `UNMOUNT`）。

**反例（真踩过）**：`local-wgc-machine` 里塞了一半 WorkBuddy 宿主特有的东西（工具层输出拿不到、安全策略、沙箱代理），
而它挂给 4 个 agent —— ZCode / opencode 读到的全是"WorkBuddy 的毛病"，纯噪音，甚至误导（它们可能根本没这些限制）。
后来拆成 `local-wgc-machine`（通用）+ `local-workbuddy-quirks`（只挂 WorkBuddy）才算干净。

## description 长度规范

description 是唯一常驻上下文的字段，所有 skill 共享这笔预算（QClaw 那边 `maxSkillsPromptChars` 总和上限 20000，可在 `openclaw.json` 里调）。

- **目标 300~500 字符**
- 超 500 要有理由（如 agent-reach 要列举 16 个平台的触发词，955 字符）
- **硬上限 1024**（opencode 官方文档要求；实测它的实现里没有强制校验，但别的客户端可能截断，别越线）

写触发词，但别把同一个意思堆三遍。

## 什么时候该把上游 skill 派生成本地 fork

判据是**差异的性质**，不是大小：

1. **功能性差异** —— 它某一步在本机根本跑不通，必须换实现（不是"建议不合口味"）
2. **持续冲突** —— 上游更新频繁，且总撞在我们改动的位置
3. **上游停更** —— 没人维护，改动不会再有合并问题
4. **强制绑定需求** —— 需要它**无条件**遵守本地约束，而 skill 之间没有依赖机制、靠 description 触发只是概率事件（见下）

只是流程约定不合（比如"它不管 version""它建议写长描述"）**不值得 fork** —— 代价是从此背上游同步债，还会让溯源变脏。

正确的替代做法：写一个**我们自己的新 skill** 补那个洞，各司其职。

## ⚠️ skill 之间没有"必须读"的机制

这一点必须知道：**A skill 不能要求 B skill 先被加载**。`available_skills` 只给模型看 name + description，要不要真的去读某个 skill 由模型自己判断 —— 是概率，不是保证。

也就是说，用户直接调 `/skill-creator` 时，模型**不一定会**去读本 skill。补救只能靠这三层：

| 层次 | 手段 | 可靠性 |
|---|---|---|
| 1 | 在**被调用的那个 skill** 里加一行指针（= 对它做极小派生） | 100%（只要执行它就一定读到） |
| 2 | 强化本 skill 的 description，把触发场景写全 | 提高概率 |
| 3 | 写进 agent 的用户级指引文件（ZCode: `~/.zcode/AGENTS.md`、opencode: `~/.config/opencode/AGENTS.md`） | 100%，但仅对该 agent，且 WorkBuddy 没有全局通道（只读项目目录的 CODEBUDDY.md/AGENTS.md） |

- 它的"自动优化 description"依赖 `claude` CLI，**本机没有**，跑不了，靠人工判断。

命名必须匹配 `^[a-z0-9]+(-[a-z0-9]+)*$`（小写字母数字 + 单连字符），**禁止** `@` `.` 大写字母 下划线 连续连字符。opencode 会强制校验，不符合就静默加载失败。

派生自 GitHub 的用 `local-<slug>-<reposlug>` 放 `store/fork/`，并在 `.upstream` 记录 `upstream_repo/path/base_commit/reason`（reason ≤3 行）。

## skill 没生效怎么查

1. 是不是 junction 没刷新 → 跑 `link.ps1`
2. 目录名与 frontmatter `name` 是否逐字符一致
3. 命名是否符合上面的正则
4. 是否被改名为 `SKILL.md.disabled`
5. 该 agent 是否认这个目录（见 local-wgc-machine skill 里的挂载表）
