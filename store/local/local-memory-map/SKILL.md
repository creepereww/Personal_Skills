---
name: local-memory-map
description: 本机各 agent 的记忆放在哪、怎么读、能不能统一。含 WorkBuddy 的用户级与项目级记忆位置、云端 profile 缓存、QClaw 的 SQLite 记忆库、ZCode 与 opencode 的 AGENTS.md 全局指引、豆包工作无记忆机制。讲清"记忆无法像 skill 那样用 junction 统一"的原因，以及"稳定知识毕业成 skill"的正确做法。触发：找记忆、记忆在哪、跨 agent 读记忆、同步记忆、合并记忆、用户偏好放哪、项目记忆怎么找。
version: v0.2
---

# 记忆地图

skill 已经统一（`~/.skills` + junction，见 `local-skills-hub`），**记忆没有，也不该强行统一**。本 skill 说明各 agent 的记忆在哪、以及正确的处理方式。

## 先分清两种东西

| | 记忆 | 全局指引（AGENTS.md） |
|---|---|---|
| 谁写 | agent 自己积累 | 人来维护 |
| 内容 | 项目过程、临时结论 | 规则、约束、偏好 |
| 例子 | 今天做了什么、排查过程 | "不要用 Bash 做文件操作" |

**别把 AGENTS.md 当记忆**——它是规则文件，不是流水账。

## 各 agent 的记忆位置（实测）

| agent | 位置 | 形式 | 可读吗 |
|---|---|---|---|
| **WorkBuddy** 用户级 | `~/.workbuddy/MEMORY.md` | Markdown | ✅ 直接读 |
| **WorkBuddy** 项目级 | `<工作区>/.workbuddy/memory/YYYY-MM-DD.md` | Markdown，按天追加 | ✅ 直接读（**每个工作区一份**） |
| **WorkBuddy** 云端 profile | `~/.workbuddy/memory/<uid>_memory.md` | 服务端生成、**只读** | ✅ 可读，但改本地会被覆盖 |
| **QClaw** | `~/.qclaw/memory/lossless/lcm.db` | **SQLite**（约 18MB） | ❌ 不能直读，要走 QClaw 自己 |
| **QClaw** 会话态 | `~/.qclaw/.auto-memory/` | 小 json | ⚠️ 只是会话状态 |
| **ZCode** | 无独立记忆文件 | — | 只有 `~/.zcode/workspace/default/AGENTS.md`（指引） |
| **opencode** | 无记忆 | — | 只有 `~/.config/opencode/AGENTS.md`（指引） |
| **豆包工作** | 无记忆机制 | — | 目录下只有 `chats/` 和 `skills/` |

**WorkBuddy 的项目记忆是分散的**：每个工作区各自一份 `.workbuddy/memory/`，互不可见。
要找某个项目当时的过程记录，得先定位工作区目录。

QClaw 另有两个空壳目录（`~/.qclaw/qmemory`、`.qclaw/memory/`，都是 4 月留下的），不是活跃记忆。

## 为什么不能用 junction 统一记忆

skill 能统一是靠 junction，它恰好满足两个前提：**是目录** + **只读**（模型按需读，不会写坏链接）。记忆两条都不满足：

1. **是文件不是目录** —— `~/.workbuddy/MEMORY.md` 是文件，junction 只对目录生效；
   文件级只能 hardlink/symlink，而 **hardlink 会被"删除重建"破坏**（agent 写文件经常先删后建）
2. **路径随项目变** —— 项目记忆在 `<工作区>/.workbuddy/memory/`，工作区有 8 个，固定链接覆盖不了
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

## 跨机器同步

用 **Git 私有仓库**，不用云盘：

- 云盘只解决"跨机器"，**不解决跨 agent**（那才是真正的痛点）
- 且云盘无版本历史、冲突只能覆盖、依赖 MCP 在线、个人记忆放公有云有隐私顾虑
- `~/.skills` 已经是 Git 仓库，将来加个私有远端即可覆盖 skill 的跨机器同步

## 实操：要找某个信息时怎么走

1. **是不是稳定规则/方法？** → 先查 skill（`~/.skills/store/`，或直接看本机的可用技能列表）
2. **是不是某个项目的过程记录？** → 定位工作区，读 `<工作区>/.workbuddy/memory/YYYY-MM-DD.md`
3. **是不是用户偏好？** → `~/.workbuddy/MEMORY.md`
4. **QClaw 的历史？** → 数据库不可直读，走 QClaw 自身的检索
5. 找不到就说明**它还没毕业成 skill** —— 考虑补一个，别让它继续散着
