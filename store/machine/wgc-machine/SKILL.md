---
name: wgc-machine
description: 家里那台电脑（主机名 WGC_MACHINE，机型 MECHREVO KUANGSHI）的本机环境事实 —— 四个客户端装在 D:\APP_MAGIC、HOME 无错位（= USERPROFILE）、已装 ZCode/opencode/豆包工作/QClaw/Codex/Trae/Qoder 各自在哪、git 用 D:\APP_CLOUD 自装的 2.49、直连 github.com:443 超时需走 SSH 或代理、系统代理 127.0.0.1:26561、Everything 在 图吧工具箱 下且 es.exe 已装。在那台机器上判断"工具在哪、网络通不通、某个 agent 装没装"时看这里。通用规则见 local-windows-shell-conventions。
version: v0.4
---

# wgc-machine（家里的电脑）

> 本文件只对**主机名 `WGC_MACHINE` 的这台机器**成立。脚本只把与本机主机名匹配的 machine 档挂给 agent，
> 所以在这台（公司电脑 `WGC-WORK1-PX`）上**不会**被加载 —— 里面的绝对路径在这边是无效的。
> 通用规则见 `local-windows-shell-conventions`；仓库规则见 `local-skills-hub`。
>
> **目录名为什么是 `wgc-machine`**：脚本按主机名匹配目录名（`%COMPUTERNAME%` 转小写），
> 所以目录名只能跟着主机名走。这台的 `%COMPUTERNAME%` 是 `WGC_MACHINE`，目录就必须叫 `wgc-machine`
> （小写、符合命名正则）—— 曾漏掉 `-machine` 后缀而叫 `wgc`，导致本机档案一直挂不上，已订正。
> 详见本目录的 `NOTE.md`。

## 身份

| 项 | 值 |
|---|---|
| 主机名 | `WGC_MACHINE`（曾记为 `WGC`，已实测订正） |
| 用户 | `cgw06`，HOME = `C:\Users\cgw06` |
| 机型 | **MECHREVO KUANGSHI Series** |

## git（两套并存，注意别用错）

| 位置 | 版本 | 用途 |
|---|---|---|
| `D:\APP_CLOUD\PortableGit\cmd\git.exe` | 2.49 | 用户自装，**已加入用户 PATH**，日常走它 |
| `~/.workbuddy/binaries/PortableGit/versions/<ver>/cmd/git.exe` | 2.55 | 宿主自带。**别用** —— 路径随版本变 |

**⚠️ git 在宿主的 Bash 工具里要用用户自装的 2.49**：

实测对照（同一仓库、同一环境，只有 git 二进制不同）：

| 环境 | 2.55（宿主自带） | 2.49（用户自装） |
|---|---|---|
| 用户的 git-bash（真实终端） | ✅ ref 正常落盘 | ✅ 正常 |
| 宿主的 Bash 工具（AI 在用） | ❌ ref 不落盘 | ✅ 正常 |

→ **2.55 本身没问题**（真实终端里好好的），是「宿主 Bash 工具环境 × 2.55」这个组合不行：
能连远端、能 fetch、能 push，但 `refs/remotes/origin/*` 不落盘，`git status` 永远 `[gone]`
（**数据不受影响**，`git ls-remote origin` 可核对）。`update-ref` 甚至返回 0 却不写。

**已逐个排除、都不是原因**：环境变量（干净 `env -i` 也一样）、`credential.helper`
（它那份被改成非标准的 `helper-selector`）、`core.fscache`、目录不存在（手动 mkdir 后照样失败）、
`cmd/` 存根 vs `mingw64/bin` 真身。

**实用结论**：升级 git **不会因此出问题**（官方发行版在真实终端一切正常）；
只有在宿主的 Bash 工具里，才需要让 PATH 优先指向 2.49。shim 已这么配，
并加了 `hash -r`（改 PATH 顺序必须清 bash 的命令 hash 缓存，否则 `command -v git` 仍指向旧的）。
**自装 git 升级后若换了路径，记得同步改 shim。**

## 客户端安装位置（本机实测）

四个客户端都装在 **`D:\APP_MAGIC\`**。

**`HOME` 无错位**：`$HOME` = `%USERPROFILE%` = `C:\Users\cgw06`，两个变量一致
（对比公司电脑 `wgc-work1-px`：`HOME` 被重定向到 `D:\AppData\Roaming\SPB_Data`）。

| agent | 装了 | 位置 / 判据 |
|---|---|---|
| WorkBuddy | ✅ | `~/.workbuddy/`，技能源 `~/.workbuddy/skills/`（junction → `~/.skills/store`） |
| ZCode | ✅ | `~/.zcode/`（含 `AGENTS.md`、`cli/`）；技能在公共位 `~/.agents/skills/`（junction） |
| opencode | ✅ | `~/.config/opencode/`（含 `AGENTS.md` + `skills/`） |
| 豆包工作 | ✅ | `~/DoubaoWork/`（含 `AGENTS.md` + `skills/`） |
| QClaw | ✅ | `~/.qclaw/`（有 `skills/`、`memory/`）。`SOUL.md`/`USER.md`/`TOOLS.md` 本就不在配置目录根 —— 它们属于 **agent 工作区**（OpenClaw 默认 `~/.openclaw/workspace/`），本机没见到该工作区 |
| Codex CLI | ✅ | `~/.codex/`（含 `memories_1.sqlite`、`skills/.system/`；`skills/` 下无自建） |
| Trae CN | ✅ | `~/.trae-cn/`（含 `builtin/`、`extensions/`） |
| **Qoder** | ✅ | `~/.qoder/`（**国际版**；`~/.qoder-cn` 不存在 → 不是 CN 版）。项目落在 `~/Documents/Qoder/2026-10-0x-<hash>/`。详见下节 |
| MarsCode | ❌ | `~/.marscode/` 不存在 |

### Qoder 本机实测（2026-10-04）

装的是**国际版**（目录 `~/.qoder/`）。默认状态**全部与官方口径一致** —— 官方说"需自己创建"的，本机就都没有：

| 路径 | 本机 | 与官方是否一致 |
|---|---|---|
| `~/.qoder/skills/` | ❌ 不存在 | ✅ 一致（官方：默认无，需 `mkdir` 自建） |
| `~/.qoder/AGENTS.md` | ❌ 不存在 | ✅ 一致 |
| `~/.qoder/rules/` | ❌ 不存在 | ✅ 一致 |
| `~/.qoder/agents/` | ❌ 不存在 | ⚠️ 官方未给该路径（第三方才这么说），本机无 —— 别照抄第三方 |
| `~/.qoder/memory/`（用户级自动记忆） | ✅ 存在但**空** | ✅ 一致（`QODER_MEMORY_USER` 未开，故无内容） |
| `~/.qoder/projects/<project>/memory/` | ✅ 4 个项目目录都有，但**全空** | ✅ 一致（`QODER_MEMORY=1` 未开） |
| `~/.qoder/settings.json` | ✅ 存在，**只有一个键 `enabledPlugins`** | ✅ 一致（权限/模型都没配） |
| `~/.qoder/mcp-router.json` `plugins/`（`cache`、`data`、`installed_plugins_v2.json`） | ✅ 存在 | 客户端自己的插件机制 |

→ **结论：Qoder 在本机是全新未配置状态**。要用 skills 得自己建 `~/.qoder/skills/`（可挂 junction 到
`~/.skills/store`，与 ZCode/opencode 那套一致）；要它记东西得设 `QODER_MEMORY=1`。

**其他实测**：

- **WorkBuddy 技能加载源**：`~/.workbuddy/.skill-list-cache.json` 里 45 条，
  44 条 `userSettings`（来自我们的 junction）+ 1 条 `plugin`
- **自建专家**：`~/.workbuddy/plugins/marketplaces/my-experts/` 存在但**为空**（还没有自建专家）
- **`.codebuddy/`**：存在，但只有 `diagnostics/`、`logs/`，没有 `skills/`、`rules/`

## 网络（⚠️ 和公司电脑完全相反）

**直连实测**（那台机器 + 家用网络）：

| 目标 | 结果 |
|---|---|
| `github.com:443` | ❌ **超时** |
| `github.com:22` | ✅ 通 |
| `ssh.github.com:443` | ✅ 通 |
| `gitee.com:443` | ✅ 通 |

→ **GitHub 走 SSH 没问题，HTTPS 直连必挂**（要挂代理）。
注意第 1 行和第 3 行**同样是 443 端口**却一个不通一个通 —— 是 `github.com` 的**目标 IP 被阻**，不是端口被封。

**代理（两个别搞混）**：

- **系统持久代理**：`127.0.0.1:26561`（注册表 `ProxyEnable=1`，用户自装的）
- **WorkBuddy 会话内注入**：`HTTP_PROXY`/`HTTPS_PROXY` 指向它自己的沙箱代理，**端口随会话变**，别硬编码
- 给 git 配代理：`git config --global http.proxy http://127.0.0.1:26561`；不用了 `--unset http.proxy`

SSH 配置在 `~/.ssh/config`（⚠️ **不能写成 `config.txt`**，那样 ssh 不读 —— 真踩过），
里面让 github.com 走 `ssh.github.com:443`。

## Everything + es（CLI）

**Everything**（已装、服务在跑）：

```
D://APP_HARDWARE//图吧工具箱202502//tools//其他工具//Everything//
  everything.exe    1.4.1.1026
  Everything.db     43 MB（索引）
```

- ✅ 桌面快捷方式：`C://Users//cgw06//Desktop//everything.exe - 快捷方式.lnk` —— 指向上面这个
- ❌ `D://APP_MAGIC//everything - 快捷方式.lnk` 是**旧的**，指向已失效的 `D://APP_COMMON//...`；
  **别拿它判断"装没装"**（曾据此误报"没装"）

**es.exe**（命令行搜索，找文件用它，毫秒级）：

```
D://APP_MAGIC//es.exe     1.1.0.38     已加入用户 PATH
```

```bash
es -n 20 关键词              # 最多 20 条
es /ad 关键词                # 只要文件夹（注意是 /ad，不是 -folder）
es -p "路径片段" 关键词        # 匹配完整路径
es -path "C://某目录" 关键词    # 限定在某目录下搜
es -get-everything-version   # 看它连到的 Everything 版本
es -json / -csv / -tsv       # 换输出格式
```

✅ **实测可用**：es 1.1.0.38 直接兼容 Everything 1.4.1.1026（默认 IPC 就通，`-ipc1` 也行）。
实测 **~0.5 秒**（含进程启动），中文路径**不乱码**。

⚠️ 参数写错会返回 `Error 6: Unknown switch` —— 比如"只搜文件夹"是 **`/ad`**，没有 `-folder`。

⚠️ **前提：Everything 的 GUI 客户端必须在跑**
- 只有 `Services` 会话的进程**不够**（那只是索引服务，不提供 es 要的 IPC）
- 症状：`Error 8: Everything IPC window was not found`
- **agent 启动不了它** —— 得让用户自己开

⚠️ 若哪天连不上，先查 GUI 在不在（见上）；真怀疑版本，GitHub `voidtools/es` 有 1.1.0.30~38 全部 tag 可换。

## 已排查过、确认不用管的

- **长路径**：`LongPathsEnabled=1`，超 260 字符的路径可用
- **用户/系统 PATH**：本身是干净的
