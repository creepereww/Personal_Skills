---
name: local-skills-hub
description: 本机全局 skill 仓库（~/.skills）的使用规则与强制约束。动手前必读 —— 涉及新增/修改/删除任何 skill、用 skill-creator 创建 skill、排查 skill 没生效、把 skill 推送到其他电脑时。含授权规则：完善中（v0.x）可直接改并回报，已完善（v1.0+）必须先确认或写 proposals/。
version: v0.12
---

# Skills Hub

全机器的 skill 只有一份实体，放在 `~/.skills/store/`，通过 junction 挂给各个 agent。

## 结构

```
~/.skills/store/local/   纯本地 skill（跨机器成立）
~/.skills/store/fork/    从 GitHub 派生的 skill（含 .upstream 溯源）
~/.skills/store/cache/   远程 skill 缓存（不进 Git）
~/.skills/store/machine/ 机器专属 skill，一个主机名一个目录，只挂本机那个
~/.skills/routing.json   各 agent 挂载点 + 安装检测规则
~/.skills/registry.json  远程 skill 清单
~/.skills/proposals/     待审批提案（只有 v1.0+ 的 skill 才需要走这里）
~/.skills/scripts/_common.ps1  共用探测函数（别在各脚本里重复实现）
```

## ⚠️ 先分类：通用 / 机器专属 / agent 专属

写任何环境信息前先问两句：

| 这个事实… | 放哪 | 为什么 |
|---|---|---|
| 换台机器、换个 agent 都成立 | `store/local/` | 挂给所有已安装 agent |
| **只对某台机器成立**（磁盘路径、机型、网络实测） | `store/machine/<主机名>/` | 脚本只挂**本机主机名匹配**的那个，不会跑到别的机器上 |
| **只对某个 agent 成立** | `store/local/` + `routing.json` 的 `skills` 段限制 client | 别的 agent 读到是噪音 |

**机器专属信息绝不放 `store/local/`** —— 那会跟着 Git 跑到别的机器上，给出错误信息。
（真踩过：`local-wgc-machine` 把家那台的「github.com:443 超时」带到了公司电脑上，
而公司电脑直连是通的，会让人白折腾 SSH 和代理。）

`store/machine/<主机名>/` 的 `SKILL.md` 里 **frontmatter 的 `name` 必须等于目录名**（小写），
且 `%COMPUTERNAME%` 是大写返回 —— 脚本用**大小写不敏感**比较匹配，写小写没问题。

## ⚠️ 脚本不写死「本机事实」

仓库跟着 Git 在多台机器上跑，各机器的 git 位置、装了哪些 agent 都不同。
**凡是不通用的都得探测，不能硬编码** —— 两处已有现成函数（`scripts/_common.ps1`），别重新发明：

| 探测对象 | 函数 | 优先级 |
|---|---|---|
| git.exe | `Get-GitExe` | `$env:SKILLS_GIT` > PATH > 常见安装位置 |
| agent 装没装 | `Test-ClientInstalled` | `routing.json` 的 `detect` > 默认看 skills 目录的父目录 |

- **没装的 agent 不挂、也不给它建目录**（旧行为是 `enabled` 就建，会在干净机器上凭空造空壳目录）。
- `detect` 约定：不写 -> 看父目录；`[]` -> 不探测、永远视为已装；路径数组 -> 存在才算；`detect_any: true` -> 任一存在即可。
- 加新 agent 时**必须想清楚它的 `detect`**：skills 目录父目录不存在的（如 opencode），要显式给安装路径，否则永远挂不上。
- 调试用 `link.ps1 -ListClients`（列每个 client 的判定依据）；判错了用 `-Force` 强行挂或改 `detect`。

### 接新 agent 的四步核对（别省，省了必返工）

按这个顺序，别上来就改 `routing.json`：

1. **grep 我们的文档有没有它** —— 多半是"压根没记"，那问题就不是"记录错了"而是缺项
2. **本机 `ls` 实测** —— 但注意：**目录不存在 ≠ 不一致**。很多 agent（Qoder 就是）默认不预建 `skills/`，
   官方明说要自己 `mkdir`，所以"没有"是**正常状态**，别据此判定有问题
3. **查官方 docs，拿一手出处** —— 开源/CLI 类必有文档站（`docs.xxx.com`），查不到就换个产品线名再查
4. **三方整理只当线索** —— 社区整理的优先级、路径经常写反（Qoder 的"同名谁覆盖谁"就被写反过），
   必须回到官方确认；官方没给的（如 `~/.qoder/agents/`）标 ⚠️ 并注明"官方未给路径"

**两条产品线要分开注册**：同一个 agent 有国际版/CN 版之分时（Qoder: `~/.qoder` vs `~/.qoder-cn`），
配置根目录不同，**各注册一条 client**，让没装的那条被 `detect` 自动跳过 —— 只写一条的话，
换台装另一个版本的机器就会漏挂。

## 🚫 修改 skill 的授权规则

skill 分两个成熟度，**权限不同**：

| 阶段 | version | 谁能改 |
|---|---|---|
| **完善中** | `v0.x` | 模型**直接改**，不必事先确认 —— 改完回报"改了哪个文件、改了什么"即可 |
| **已完善** | `v1.0+` | 改动**必须先经用户确认**：说清改哪个文件、删什么、加什么 |

**晋级由用户点头，不看版本号走没走满。** `v0.x` 可以一直是 `0.10`、`0.11` 地往上加；
简单的 skill 也可能 `0.2` 之后直接跳 `1.0`。模型只能**建议**"它稳定了，要不要转 v1.0"，**不能自己升**。

**小改例外**（两种阶段都可直接做）：错别字、补一行说明、修失效的路径。

**大改必须确认**（针对已完善的 skill）：删章节、重写、拆分、改挂载范围/受众、动脚本或路由配置。

### 任务中发现某个 skill 不好用，怎么办

| skill 成熟度 | 做法 |
|---|---|
| `v0.x` | **直接改** —— 包括 `store/` 下的实体文件、skill 自带的脚本。改完回报改了哪里。 |
| `v1.0+` | **不得直接改**，写 `~/.skills/proposals/<skill>.md` 等人批准 |

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
`v0.x` 的情况下，"知道"可以发生在**改动之后**（回报即知情）；`v1.0+` 必须发生在**之前**。

**为什么 v0.x 不走提案**：提案的意义是给用户一道审批手续，而完善中的 skill 本来就处于"边写边试"，
每次确认会拖死迭代 —— 顺手修掉、事后说清，比攒一份提案更省事也更准。

**为什么 v1.0+ 必须走**：已发布的 skill 是资产，一次误删就没了
（尤其删掉的可能是"看起来没用但实际关键"的内容）。

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
所以每个**会被单独加载**的 skill，都该在开头用几行写清"改我时要守什么"（尤其禁止项和易错点）——
包括**自己的成熟度**（`v0.x` 可直接改 / `v1.0+` 先确认），免得改的人还要跑回来查这张表。
派生版 skill-creator 就是这么做的（开头内嵌了本机适配说明）。

### 版本号怎么配合成熟度

- **完善中（`v0.x`）**：无论局部补充还是结构重写，**都只动小数位**（`0.9` → `0.10` → `0.11`）。
  整数位保持 0，**直到用户点头**
- **已完善（`v1.0+`）**：局部补充 Y+1；结构重写 X+1（如 `v1.4` → `v2.0`）
- 一律**不写 changelog、不写日期、不写改动原因** —— skill 正文要占上下文，能省则省

## 常用操作

```powershell
pwsh ~/.skills/scripts/link.ps1                 # 刷新挂载（新增/改名后必做）
pwsh ~/.skills/scripts/link.ps1 -DryRun         # 先看会做什么
pwsh ~/.skills/scripts/link.ps1 -ListClients    # 看各 agent 装没装、判定依据
pwsh ~/.skills/scripts/sync.ps1                 # 拉取 + 刷新
pwsh ~/.skills/scripts/sync.ps1 -Commit "msg"   # 提交 + 同步
pwsh ~/.skills/scripts/sync-preferences.ps1     # 分发偏好（sync.ps1 不含这步）
```

## ⚠️ 清理目录前：别信目录的 mtime

**往一个老目录里写一个文件，它的 mtime 就变成今天了。** 所以「目录显示今天建的」不能作为
「这是本次产物」的证据。实锤过一次：`~/.zcode` 的 mtime 是当天（因为被写了 `AGENTS.md`），
但里面 `cli/` 是 9/4 的 73MB 真实会话数据，差点被当残留清掉。

判断要看**目录里面**的内容和日期，不是目录本身的 mtime。
删除前先列出目标清单和依据，逐项确认 —— 尤其 `~/.zcode`、`~/.config` 这类可能混着真实数据的目录。

## 新增一个本地 skill

1. 在 `store/local/` 建目录 `local-<slug>/`
2. 写 `SKILL.md`，frontmatter 必须含 `name`（与目录名逐字符一致）、`description`、`version: v0.1`
3. 跑 `link.ps1` —— 所有**已安装**的 agent 同时就位

## 用 skill-creator 创建 skill 时

本机用的是派生版 `local-skill-creator-anthropics-skills`（远程原版已停止挂载）。它开头**内置了本机适配说明** —— 落盘位置、命名正则、version 字段、workspace 该放哪、不打包 .skill，照它走就行，这里不重复。

## 内容要分清"跨 agent 通用"还是"某个 agent 专属"

skill 是**一份实体挂给所有已安装 agent** 的（名单见 `routing.json` 的 `defaults.clients`）。所以写之前先问一句：
**换成另一个 agent 来读，这段还有用吗？**

> 别在文档里写死这个名单的数量 —— 新 agent（如 Qoder）接入后会变，看 `routing.json` 才是准的。

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

**反例（真踩过，两次同源）**：`local-wgc-machine`（已拆解）犯过两次同类错误 ——

1. **按 agent 混装**：里面塞了一半 WorkBuddy 宿主特有的东西（工具层输出拿不到、安全策略、沙箱代理），
   而它挂给了所有已安装 agent —— ZCode / opencode / Qoder 读到的全是"WorkBuddy 的毛病"，纯噪音甚至误导。
   后来拆出 `local-workbuddy-quirks`（只挂 WorkBuddy）才算干净。
2. **按机器混装**：它同时标着「本机 WGC_MACHINE」又住在跟随 Git 的 `store/local/` 里，
   于是公司电脑上读到的机型、磁盘、git 路径、网络结论**全是家那台的** —— 其中「github.com:443 超时」
   与实情（通）完全相反，会让人无谓地折腾 SSH 绕行和代理。
   后来按「通用 / 机器专属」两层拆开：`local-windows-shell-conventions` + `store/machine/<主机名>/`。

**教训**：写一个 skill 前先问「这个事实**换台机器 / 换个 agent** 还成立吗」。
只对某台机器成立的 → `store/machine/<主机名>/`（不会被挂到别的机器）；
只对某个 agent 成立的 → `routing.json` 的 `skills` 段限制 client。

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
5. 该 agent 是否认这个目录（见 `local-windows-shell-conventions` 的挂载表）
