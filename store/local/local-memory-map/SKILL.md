---
name: local-memory-map
description: 各 agent 的记忆、技能、专家、偏好分别存在哪、能不能统一同步。含通用查法（先分类再定位）、WorkBuddy 的三级记忆与技能/专家三层存储（plugins 各子目录职责、实际加载源看 .skill-list-cache.json）、不能用 junction 统一记忆的四条原因、偏好靠 preferences.md 分发的三条通道，以及按官方文档整理的六类资产（自建技能·用户偏好·内置索引·自建专家·云端记忆·项目记忆）默认目录，覆盖 Claude Code/Codex/Gemini CLI/ZCode/Cursor/Windsurf/Trae/OpenClaw/QClaw/豆包/WorkBuddy，含跨工具公共位 ~/.agents/skills 与各家优先级。触发：记忆在哪、记忆存哪、个性化设置存哪、跨 agent 读记忆、同步记忆、用户偏好放哪、项目记忆怎么找、专家文件在哪、内置技能在哪、skills 默认目录、各 agent 资产位置、Gemini CLI 有没有 skills。机器专属实测见 store/machine/<主机名>/。
version: v0.9
---

# 记忆与各类资产的存放地图

skill 已经统一（`~/.skills` + junction，见 `local-skills-hub`），**记忆没有，也不该强行统一**。本 skill 说明各 agent 的**记忆**、**内置技能**、**专家**分别在哪、以及正确的处理方式。

> WorkBuddy 的技能/专家**机制**（从哪个目录加载、`plugins/` 各子目录职责、专家包结构）
> 也一并收录在本 skill 后半部分 —— 位置和机制放在一起才好查。
> Windows 通用约定（路径格式、junction、命名）见 `local-windows-shell-conventions`。
>
> **两种口径要分清**：本 skill 只讲**机制**和**官方文档口径**（换台机器照样成立）。
> 「这台机器上实际装了什么、`$HOME` 有没有错位」这类**实测偏差**写在
> `store/machine/<主机名>/SKILL.md`，本文件不假设具体机器 —— 通用 skill 跟随 Git 同步到所有机器，
> 写死某一台的实况，到别的机器上就变成错误信息（`local-wgc-machine` 犯过这个错，已拆解）。

## 先分清两种东西

| | 记忆 | 全局指引（AGENTS.md） |
|---|---|---|
| 谁写 | agent 自己积累 | 人来维护 |
| 内容 | 项目过程、临时结论 | 规则、约束、偏好 |
| 例子 | 今天做了什么、排查过程 | "不要用 Bash 做文件操作" |

**别把 AGENTS.md 当记忆**——它是规则文件，不是流水账。

## 查之前先看：`~` 到底展开成什么

**各 agent 用的环境变量并不统一**：多数（ZCode、WorkBuddy、豆包）走 `%USERPROFILE%`，
**QClaw/OpenClaw 跟 `$HOME` 走**。一旦这台机器的 `HOME` 与 `USERPROFILE` 不一致
（被数据重定向工具改过），同一个 `~/.qclaw` 就会落在两个完全不同的盘上。

→ **查 agent 目录时两个变量都要试**。只查 `%USERPROFILE%` 会漏掉 QClaw，只查 `HOME` 会漏掉其余几个。

各台机器上 `HOME` 到底指哪、谁错位、错到哪个盘 → 见 `store/machine/<主机名>/SKILL.md`。

## 怎么查某个 agent 的记忆在哪

按这个顺序走，别靠记忆：

1. **判断它属于六类资产中的哪一类** → 查文末官方口径表（先分清是「记忆」还是「指引」还是「缓存」）
2. **取该 agent 的官方默认路径** → 同表
3. **两个变量都试**：`%USERPROFILE%` 与 `$HOME`（见上节）
4. **SQLite 类读不了** —— ZCode `db.sqlite`、QClaw `lcm.db`、Codex `memories_1.sqlite`
   都不能直接读文本，只能走该 agent 自己的检索通道

**WorkBuddy 的项目记忆是分散的**：每个工作区各自一份 `<工作区>/.workbuddy/memory/YYYY-MM-DD.md`，
互不可见。要找某个项目当时的过程记录，**得先定位工作区目录**。

## 怎么查某个 agent 的 skills 目录

1. 官方默认路径见文末表①。**跨工具公共位 `~/.agents/skills`** 已被 Codex / Gemini CLI / ZCode 采用 ——
   一个 junction 挂一次就能被多家同时认领（各家优先级不同，见表①备注）
2. **装没装这个 agent**：本机看 `store/machine/<主机名>/SKILL.md`，或跑
   `~/.skills/scripts/link.ps1 -ListClients`（它会逐个报探测判据）
3. **WorkBuddy 实际从哪加载**：不看目录名，看 `~/.workbuddy/.skill-list-cache.json`（见下）
4. `.codex/skills/.system/`、`.marscode/builtin_skills`、`.trae-cn/builtin/global/skills`
   这类是**它们自带的预置技能**，不是我们的仓库内容，别去动

**ZCode 的 CLI 是 Claude Code 系**（认 `claude-plugins-official` 市场、用 `~/.zcode/cli/plugins/`
的市场-缓存-已装三层结构），和 WorkBuddy 的插件机制形似但**不通用**。

## WorkBuddy 的三种「记忆」别混

官方「设置 → 记忆与进化」管的是**记忆数据**，它和本地文件**不是一回事**：

| 名称 | 位置 | 谁写 | 能否本地改 |
|---|---|---|---|
| **记忆数据**（对话记忆） | **云端**（无本地明文文件） | 服务端每晚自动抽取，从会话历史提炼偏好/习惯/人物关系/跟进事项 | ❌ 只能在「设置 → 记忆」里通过对话增删改，或关掉 |
| **云端 profile 缓存** | `~/.workbuddy/memory/<uid>_memory.md` | 上面那份的**本地只读镜像** | ❌ 改本地会被下次覆盖（另有 `.bak`） |
| **用户级记忆文件** | `~/.workbuddy/MEMORY.md` | 我们脚本写入（`sync-preferences.ps1`） | ✅ 可改（走 `preferences.md` 分发） |

**官方文档要点**（`Function-Description/Memory`）：
- 默认开启；**每晚**整理当天会话，仅本人可见
- 提取范围：事实信息、偏好习惯、人物关系、近期跟进事项
- 使用方式：① 注入系统提示词作为上下文；② 支持会话历史检索（「上周做过什么」）
- **不消耗积分/token**（WorkBuddy 自费）；不涉及第三方共享
- 支持「导入记忆」——从其他 AI 产品同步使用习惯（复制示例提示词过去，粘贴结果回来）

⚠️ **「生成对话记忆」开关只管云端那份**，和我们脚本维护的 `MEMORY.md` 是两条独立链路。

## WorkBuddy 的个性化设置存哪

截图里的「设置 → 个性化」（回复风格 / 加载欢迎语 / 自定义指令 / 称呼与身份 / 人设描述）
**没有明文本地文件** —— 走 `storage/` 里的分片存储，且多数同步云端：

```
~/.workbuddy/storage/
├── user-<uid>-personal/
│   ├── global/preferences.json      # 全局偏好（实测内容：{"theme":"light"}）
│   └── scoped/<hash>/               # 按作用域分片（hash 对应某种 scope）
│       ├── preferences.json         # 实测：{"language":"zh-CN"}
│       ├── expert-picker.json       # 专家选择器状态（置顶/最近使用）
│       ├── skills-installed-store.json
│       ├── buddy-app.json / industry.json / swr.json（前端缓存）
├── skeleton/account-snapshot.json   # 账号快照（uid/昵称/套餐）
└── device/
```

**注意**：`storage/` 里只有"语言/主题"这类**界面偏好**是明文的。
回复风格、自定义指令、称呼与身份、人格描述这些**看不到明文落盘**（要么在别处、要么只存云端），
涉及跨设备同步。想改这些，走 UI，别去翻文件。

`~/.workbuddy/settings.json`（38KB）只存 **插件启用状态**（`enabledPlugins`）、
沙箱白名单（`sandbox`）、Claw 通道配置等，**不含**个性化人设。

## WorkBuddy 的技能与专家：三层存储

| 资产 | 实体位置 | 登记/元数据 | 跨 agent |
|---|---|---|---|
| **技能**（自建） | `~/.skills/store/` → junction 到 `~/.workbuddy/skills/` | 无独立登记，扫目录 | ✅ 可（只要对方认 skills 目录） |
| **技能**（插件携带） | `plugins/marketplaces/<市场>/plugins/...` 或 `.../skills/` | `marketplace.json` | ✅ 可降级 |
| **技能**（已安装副本） | `plugins/cache/<市场>/<插件>/<版本>/` | `installed_plugins.json` | — |
| **专家**（自建） | `~/.workbuddy/plugins/marketplaces/my-experts/plugins/<名>/` | `my-experts` 里的 `marketplace.json` | ❌ 不可（别的 agent 无专家机制） |
| **专家**（内置 448 个） | **实体在远端 CDN，本地无实体** | `~/.workbuddy/app/cache/experts/manifest.json`（索引） | ❌ 不可 |

**为什么专家不能跨 agent**：`plugin.json` + `marketplace.json` + `installed_plugins.json`
三层登记是 WorkBuddy 私有协议；ZCode/opencode/豆包只有 **skills 目录 + AGENTS.md**，
没有"专家"这个插槽。**格式转换也救不了** —— 是对方没这个概念，不是格式不兼容。
唯一降级路径：把专家的 `agents/<name>.md`（就是个 markdown）转成 `SKILL.md` 挂成技能，
代价是丢头像、卡片展示、"选中即注入"的强制生效。

**专家包结构**（`open.workbuddy.cn/docs/expert` 官方规范）：
```
my-expert/
├── .codebuddy-plugin/plugin.json   # name/version/expertType/agentName/displayName/tags/quickPrompts...
├── avatars/expert.png              # 512×512 PNG，≤500KB
├── agents/my-expert.md             # 系统提示词（frontmatter: name/description/displayName/profession/maxTurns）
└── README.md
```
自建入口：**专家·技能·连接器 → 我的专家 → 创建专家**，由内置专家管理工具对话引导生成。
注意：**专家名称创建后不可改**，要换名只能重建。

### 各 agent 的内置技能/规则目录（官方 `.codebuddy` 规范可类推）

WorkBuddy 是 CodeBuddy 系，其**代码开发模式**会加载 CodeBuddy Code 的 `.codebuddy` 用户级配置
（官方 `cli/codebuddy-dir` 明确写了「自动识别并加载用户级 `.codebuddy` 配置：规则、技能、命令、MCP」）：

```
~/.codebuddy/
├── CODEBUDDY.md          # 用户级记忆文件
├── settings.json         # 用户级全局配置（含 memory.autoMemoryEnabled）
├── agents/               # 用户级子代理（.md）
├── rules/                # 用户级规则（.md，自动加载）
├── skills/               # 用户级技能（<名>/SKILL.md）
├── plugins/              # 已安装插件
└── projects/ sessions/ plans/ logs/ traces/ tasks/ teams/ ...
```

**记忆加载顺序**（官方）：用户级 `CODEBUDDY.md` → 用户级 `rules/*.md` → 项目级 `CODEBUDDY.md`（向上递归）
→ 项目级 `.codebuddy/rules/*.md` → 项目本地 `CODEBUDDY.local.md` → 子目录 `CODEBUDDY.md`。

⚠️ 实测 `~/.codebuddy/` 在有的机器上**不存在**、有的机器上只有 `diagnostics/` `logs/`
（WorkBuddy 主客户端走 `~/.workbuddy/` 那套，`.codebuddy` 是 CodeBuddy Code 的约定，别混淆）。
具体有没有、里面有什么 → 见 `store/machine/<主机名>/SKILL.md`。

## WorkBuddy 技能：到底从哪个目录加载（★ 最容易搞错）

**权威判据**：`~/.workbuddy/.skill-list-cache.json`

- `results[]` —— 当前**真正生效**的技能清单，每条带 `filePath`（**加载源**）+ `source`
- `watch.dirs` —— 被监视的目录（改文件触发重扫）

`source` 决定技能从哪来：

| source | 含义 | 典型 filePath |
|---|---|---|
| `userSettings` | 用户目录 / 定制的技能 | `~/.workbuddy/skills/<名>/SKILL.md` |
| `plugin` | 插件携带的技能 | `~/.workbuddy/plugins/marketplaces/<市场>/plugins/<插件>/.../SKILL.md` |
| `connector` | 连接器携带的技能 | `~/.workbuddy/connectors/skills/<名>/SKILL/SKILL.md` |

**⚠️ 实测结论（与直觉相反）：插件技能的加载源是 `plugins/marketplaces/`，不是 `plugins/cache/`。**
例：`agent-browser` 的 filePath = `marketplaces/codebuddy-plugins-official/plugins/agent-browser/SKILL.md`
（`cache/codebuddy-plugins-official/agent-browser/1.3.0/` 里那份**不是**加载源）。

### `plugins/` 各子目录的职责

| 目录 | 职责 | 会被加载吗 |
|---|---|---|
| `marketplaces/<市场>/plugins/` | 市场插件的**展开实体** | ✅ 是加载源 |
| `marketplaces/<市场>/skills/`（仅 builtin） | builtin 市场技能的源目录 | ⚠️ 仅当已进 `skill-list-cache` 才加载 |
| `cache/<市场>/<插件>/<版本>/` | **已安装副本 + 会话引用计数** | ❌ 不是加载源 |

**`cache/` 的真相**：它是"安装包展开 + 引用计数"，不是运行目录。
- `有 .in_use/<pid>`（内容 `{"pid":...,"procStart":...}`）→ 该版本正被若干会话引用
- 有 `.orphaned_at` → 已被新版取代，系统待清理

**名字对不上是正常的**：`marketplace.json` 里 `name` 是**市场名**（如 `skill-expert-manager`），
源目录名是 `expert-manager`（无前缀），靠 `source` 字段（`"./skills/expert-manager"`）关联。
前缀 `skill-` 是市场层加的。

## 为什么不能用 junction 统一记忆

skill 能统一是靠 junction，它恰好满足两个前提：**是目录** + **只读**（模型按需读，不会写坏链接）。记忆两条都不满足：

1. **是文件不是目录** —— `~/.workbuddy/MEMORY.md` 是文件，junction 只对目录生效；
   文件级只能 hardlink/symlink，而 **hardlink 会被"删除重建"破坏**（agent 写文件经常先删后建）
2. **路径随项目变** —— 项目记忆在 `<工作区>/.workbuddy/memory/`，工作区有几个就有几份，固定链接覆盖不了
3. **路径写死在 agent 的系统机制里** —— 我们改不了它们的系统提示
4. **WorkBuddy 没有全局指引通道** —— 它只读项目目录的 AGENTS.md，连"换个地方写记忆"这条路都没有

硬做会得到一堆"链接悄悄失效、两边内容对不上"的维护坑。**skill 能统一是巧合，不是可复制的范式。**

## 正确的做法：分层 + 记忆毕业

| 层 | 内容 | 处理 |
|---|---|---|
| **稳定知识**（反复用到的规则、方法、环境坑） | → **做成 skill** | 跨 agent 通用，唯一真正"统一"的方式 |
| **项目过程**（今天做了什么、排查过程） | → 留在各 agent | 不该统一，也不必 |
| **用户偏好** | → 各 agent 各记一份 | 内容一致即可，位置无需统一 |

**记忆毕业**：同一主题的教训反复出现到第 3 次，就不是"最近踩的坑"了，而是稳定知识——
该从记忆里毕业成 skill（详见 `local-neat-freak-lite-khazix-skills`）。
稳定知识留在记忆里，等于每个 agent 各自持有一份、互不可见、随会话丢失。

## 已落地的机制：用户偏好可以统一

之前说"记忆不能统一"只对了一半 —— **用户偏好这条线已经打通了**，用「一个权威源 + 脚本分发」：

```
~/.skills/preferences.md            ← 权威源（进 Git、跨机器同步）
        ↓  scripts/sync-preferences.ps1
~/.workbuddy/MEMORY.md              ← WorkBuddy 每次会话自动注入
~/.zcode/AGENTS.md                  ← ZCode 每次会话注入
~/.config/opencode/AGENTS.md        ← opencode 每次会话注入
~/DoubaoWork/AGENTS.md              ← 豆包工作（若它认这个约定）
```

源与目标都用 `<!-- SYNC:BEGIN -->` / `<!-- SYNC:END -->` 包裹，脚本**只替换块内内容，
不动块外的任何东西** ⇒ 幂等、可反复跑。
改偏好就改 `preferences.md` 然后跑一次脚本。

**为什么不用链接**：用户级记忆是**单个文件**（不是目录），junction 只对目录生效；
文件级只能 hardlink/symlink，而 agent 写文件常"先删后建"会破坏链接。

**所以完整的三条通道**：

| 内容 | 载体 | 触达方式 |
|---|---|---|
| **稳定知识**（规则/方法/环境坑） | skill | 按需（description 触发，概率） |
| **用户偏好**（沟通/协作规则） | 用户级 `AGENTS.md` × 4 | **每次会话注入（100%）** |
| **项目过程**（做了什么/怎么查的） | 各 agent 自己的工作区记忆 | 不统一，也不必 |

注意 WorkBuddy 只有 `~/.workbuddy/MEMORY.md` 这条用户级通道；
它**读不到项目目录之外的 AGENTS.md**，所以别指望用同一份 AGENTS.md 覆盖它。

## ⚠️ 找东西的深度陷阱（真踩过）

有些路径**深达 8 层**，例如豆包工作的（某台机器上的实测，别台层数可能不同）：

```
%LOCALAPPDATA%\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\
```

搜文件时 `maxdepth` 给不够就会漏 —— 而且**漏了你不会知道**（结果为空 ≠ 不存在）。
我曾搜到第 7 层、目标在第 8 层，于是误报"本机没有这个目录"。

**三个做法**：

1. **深度给足**（≥ 10），或干脆不限深度
2. **优先用文件名特征搜**（比搜目录名容易命中）
3. 装了 **Everything** 就用它 —— 毫秒级，且有 `es.exe` CLI 可脚本调用
   （Everything 装在哪、`es.exe` 在不在 PATH → 见 `store/machine/<主机名>/SKILL.md`，别照抄别台的路径）
4. 常规目录搜不到时，**问用户**比继续猜快 —— 他一句"路径在 X"就解决了

### 豆包 `.user_skills` 的自动恢复机制（实测）

在豆包对话里生成的 skill 会**注册进豆包的系统**（「技能・连接器・伙伴」面板可见）。
**直接删文件夹没用** —— 检测到缺失就从配置源重建（实测 17:22 删、17:22 就回来了）。

**正确删除方式**：豆包工作 → 「技能・连接器・伙伴」面板 → 个人区 → 右键该 skill → **删除**。

**实测案例**（`rainmeter-skin-dev`，豆包在对话里生成的那份）：
- 面板里它**已关闭**（灰色开关），但**文件夹仍被自动重建**
- 我们维护的版本（`Local Rainmeter Skin Dev`，junction → `~/.skills/store`）**开启中** ✓
- → 要在面板里把旧的那个**删除**才算清净（面板右键有「删除」入口）

**junction 实测**：豆包的 `.user_skills` 里放 junction **可用**（面板里 `Local Rainmeter Skin Dev` 正常开启），
但**曾被展开成实体副本**（原因未明，用的时候留意是否又被物化）。

## 跨机器同步

用 **Git 私有仓库**，不用云盘：

- 云盘只解决"跨机器"，**不解决跨 agent**（那才是真正的痛点）
- 且云盘无版本历史、冲突只能覆盖、依赖 MCP 在线、个人记忆放公有云有隐私顾虑
- `~/.skills` 已经是 Git 仓库，将来加个私有远端即可覆盖 skill 的跨机器同步

### 各类资产能不能纳入 `~/.skills` 同步

| 资产 | 能否同步 | 怎么做 |
|---|---|---|
| **技能**（自建） | ✅ | 已在仓库 `store/local/`、`store/fork/` 里，天然同步 |
| **用户偏好** | ✅ | `preferences.md` 进 Git + `sync-preferences.ps1` 分发 |
| **内置技能/专家索引** | ❌ | 是客户端自动拉取的缓存，重装会自动回来，不该进 Git |
| **自建专家** | ⚠️ 待定 | 实体在 `~/.workbuddy/plugins/marketplaces/my-experts/`，**不在仓库内**。要同步得先在 `store/` 存一份源副本 + 脚本 copy 到 my-experts 并跑 `register_expert.py`。**当前还没有自建专家，先不做** |
| **云端记忆 / 个性化设置** | ❌ | 走账号云端同步，本地无明文，不归我们管 |
| **项目记忆**（`<工作区>/.workbuddy/memory/`） | ❌ | 每个工作区一份，跟着项目走，不集中同步 |

## 各 agent 的默认资产位置（★ 官方文档口径）

> 下面这张表**按各家官方文档的默认路径**整理 —— 所以**没装的 agent 也能查**，
> 且不受任何一台机器的 `$HOME` 错位影响。这台机器实际装了什么、有没有偏差 →
> 见 `store/machine/<主机名>/SKILL.md`。
> `~` 一律按各家文档的默认 home 解析（Windows 上通常 = `%USERPROFILE%`；但 QClaw/OpenClaw 跟 `$HOME`）。

### ① 自建技能（user-level skills）

| agent | 官方默认路径 | 备注 |
|---|---|---|
| **Claude Code** | `~/.claude/skills/<name>/SKILL.md` | 项目级 `.claude/skills/`（优先级更高）；另有 Enterprise（托管设置）、嵌套子目录、`--add-dir` 附加目录、插件、claude.ai 账号层。**目录可以是 symlink/junction**：指向同一目标时只加载一次；保留名 `synced`、`anthropic-skills` |
| **Codex CLI** | `~/.agents/skills/`（**官方推荐的跨 runtime 通用位**）与 `~/.codex/skills/`（本地安装 / 历史版本位）**两者都读**；项目级 `.codex/skills/`、`.agents/skills/`；管理员级 `/etc/codex/skills` | 官方未规定两者优先级；另读内置 System Skills |
| **Gemini CLI** | `~/.gemini/skills/` 或 `~/.agents/skills/`（**同层内后者优先**）；工作区 `.gemini/skills/` 或 `.agents/skills/` | **有** Agent Skills 机制（开放标准）；优先级 工作区 > 用户 > 扩展；需开 `experimental.skills` |
| **ZCode** | `~/.zcode/skills/` 与 `~/.agents/skills/`（**后者优先**） | 项目级 `.zcode/skills`、`.agents/skills`；`.zcode/skills` 覆盖同名 |
| **Cursor** | — | 用 Rules，非 skill（`.cursor/rules/`） |
| **Windsurf** | — | 用 Rules，非 skill（`.windsurf/rules/`） |
| **Trae** | 企业版可手动解压到 `.skills` 目录 | 社区版走 Rules |
| **OpenClaw / QClaw** | `~/.qclaw/skills/`（**跟 `$HOME` 走**，可能不在 `%USERPROFILE%`） | 走 `extraDirs` 配置 |
| **WorkBuddy** | `~/.workbuddy/skills/`（自建）；插件技能从 `plugins/marketplaces/...` 加载 | 权威清单看 `.skill-list-cache.json` |

### ② 用户偏好（全局指引 / rules）

| agent | 官方默认路径 | 形式 |
|---|---|---|
| **Claude Code** | `~/.claude/CLAUDE.md` + `~/.claude/rules/*.md` | Markdown，每会话注入 |
| **Codex CLI** | `~/.codex/AGENTS.md`（覆盖：`AGENTS.override.md`）；项目级 `<repo>/AGENTS.md` | Markdown，32 KiB 上限 |
| **Gemini CLI** | `~/.gemini/GEMINI.md`（可配 `AGENTS.md`） | Markdown，层次加载 |
| **ZCode** | `~/.zcode/AGENTS.md` | Markdown，只认用户级 + 工作区级 |
| **Cursor** | `~/.cursor/rules`（**不同步**）/ Settings 里的 User Rules（**云同步**）；项目 `.cursor/rules/` | mdc/md |
| **Windsurf** | `~/.codeium/windsurf/memories/global_rules.md`（6000 字上限）；项目 `.windsurf/rules/*.md` | Markdown |
| **Trae** | **全局** `~/.trae-cn/user_rules`（Win：`%userprofile%/.trae-cn/user_rules`）；**项目** `.trae/rules/` | Markdown |
| **OpenClaw / QClaw** | `~/.qclaw/SOUL.md`（人设）+ `USER.md`（用户信息）+ `TOOLS.md` | Markdown，会话启动自动读 |
| **WorkBuddy** | `~/.workbuddy/MEMORY.md`（用户级，我们的脚本写） | Markdown，每会话注入 |

### ③ 内置技能 / 专家索引（client-managed cache）

| agent | 官方默认路径 | 说明 |
|---|---|---|
| **Claude Code** | 随包 bundled skills（`/doctor`、`/code-review` 等），由 `disableBundledSkills` 控制 | 无独立索引文件 |
| **Codex CLI** | `~/.codex/skills/.system/` | 预置（imagegen、openai-docs、plugin-creator） |
| **Trae** | `~/.trae-cn/builtin/global/skills` | 预置 |
| **MarsCode（豆包 IDE，已并入 Trae）** | `~/.marscode/builtin_skills` | 预置 |
| **WorkBuddy** | **索引** `~/.workbuddy/app/cache/experts/manifest.json`；技能源 `plugins/marketplaces/workbuddy-builtin/skills/`；已装副本 `plugins/cache/workbuddy-builtin/<plugin>/<ver>/` | 448 专家实体在**远端 CDN**，本地仅索引 |

> ⚠️ 这一类都是**客户端自动拉取/重装即回**的缓存，**不该进 Git 同步**。

### ④ 自建专家（Expert / 插件包）

| agent | 官方默认路径 | 说明 |
|---|---|---|
| **WorkBuddy** | `~/.workbuddy/plugins/marketplaces/my-experts/plugins/<name>/` | 包结构 `.codebuddy-plugin/plugin.json` + `agents/<name>.md` + `avatars/` + `README.md`（`open.workbuddy.cn/docs/expert`） |
| **Claude Code** | `~/.claude/agents/*.md`（子代理）；插件 `~/.claude/plugins/`（含 `installed_plugins.json`、`plugins/synced/`） | 概念近似：subagent + plugin |
| **Codex CLI** | `~/.codex/` 里 `[agents]`（config.toml）；插件 marketplace 由 cloud/system config 定 | subagent |
| **其他 agent** | **无「专家」概念** | 只有 skills + rules/AGENTS.md —— 这是专家不能跨 agent 的根因 |

### ⑤ 云端记忆 / 个性化

| agent | 官方默认路径 / 形式 | 同步 |
|---|---|---|
| **WorkBuddy** | **云端**（无本地明文）；本地只读镜像 `~/.workbuddy/memory/<uid>_memory.md`；个性化走 `~/.workbuddy/storage/user-<uid>-personal/` | 云端同步 |
| **Claude Code** | 子代理记忆 `~/.claude/agent-memory/`；自动记忆 `~/.claude/projects/<project>/memory/`（`MEMORY.md` 为索引） | 本地（部分随 claude.ai 账号同步） |
| **Codex CLI** | `~/.codex/memories/`（`memory_summary.md` / `MEMORY.md` / `raw_memories.md`）+ `memories_1.sqlite`；需开 `features.memories` | 本地 |
| **Gemini CLI** | 无独立记忆库；`/memory add` 写进 `~/.gemini/GEMINI.md` | 本地 |
| **ZCode** | 项目记忆（Settings→General→Memory 开启，**默认关**，**只在本机、不进 Git**） | 本地 |
| **Cursor** | User Rules 存 Cursor 账号（**云同步**）；`~/.cursor/rules` 本机不同步 | 部分云 |
| **Windsurf** | 自动 memories 存 `~/.codeium/windsurf/memories/`（workspace 级、**仅本机**） | 本地 |
| **Trae** | 全局记忆 `~/.trae-cn/memory/user_profile.md`；项目记忆按项目存储 | **本地，不跨机同步** |
| **OpenClaw / QClaw** | `~/.qclaw/workspace/memory/YYYY-MM-DD.md` + `MEMORY.md` + `lossless/lcm.db`；Dreaming 后台沉淀 | 本地 |
| **豆包** | 记忆走**云端向量库 + 用户画像**（设置页记忆开关控制） | 云端 |

### ⑥ 项目记忆（project-scoped）

| agent | 官方默认路径 | 形式 |
|---|---|---|
| **Claude Code** | `.claude/agent-memory/<name>/MEMORY.md`；会话记录 `~/.claude/projects/<project>/*.jsonl` | Markdown + jsonl |
| **Codex CLI** | `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`（会话 transcript）；记忆汇总在 `~/.codex/memories/` | jsonl + md |
| **Gemini CLI** | 项目上下文 `./GEMINI.md` 及上级目录（非"记忆"，是指令） | Markdown |
| **ZCode** | 工作区 `AGENTS.md`（人工）+ 项目记忆（Agent 自动，本机） | Markdown |
| **Windsurf** | 自动 memories 按 workspace 隔离（`~/.codeium/windsurf/memories/`） | 本地 |
| **Trae** | 项目记忆按项目路径独立存储 | 本地 |
| **OpenClaw / QClaw** | `<agentDir>/sessions/`；记忆 `~/.qclaw/workspace/memory/` | jsonl + md |
| **WorkBuddy** | `<工作区>/.workbuddy/memory/YYYY-MM-DD.md`（**每个工作区一份**） | Markdown 按天追加 |

**一句话规律**：①-④ 是"可搬的资产"（技能/规则/专家/内置缓存），⑥ 是"跟项目走的记录"，
⑤ 是"账号级的隐性状态"。**能跨机器同步的只有 ①② 的自建部分**，其余要么走云端、要么跟项目、要么重装即回。

## 实操：要找某个信息时怎么走

1. **是不是稳定规则/方法？** → 先查 skill（`~/.skills/store/`，或直接看本机的可用技能列表）
2. **是不是某个项目的过程记录？** → 定位工作区，读 `<工作区>/.workbuddy/memory/YYYY-MM-DD.md`
3. **是不是用户偏好？** → `~/.workbuddy/MEMORY.md`
4. **是不是 WorkBuddy 的对话记忆？** → 设置 → 记忆与进化（云端，本地只有只读镜像）
5. **QClaw 的历史？** → 数据库不可直读，走 QClaw 自身的检索
6. 找不到就说明**它还没毕业成 skill** —— 考虑补一个，别让它继续散着
