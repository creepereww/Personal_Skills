---
name: local-wgc-machine
description: 本机 WGC_MACHINE（MECHREVO KUANGSHI）的通用环境信息，对各个 agent 都适用。含路径坐标、MSYS 程序与 Windows 原生程序该用哪种路径格式、junction 目录联接的正确建删方式、四个 agent 各自读哪个 skills 目录、以及已排查确认无需处理的项。在这台机器上写 shell 脚本、建软链接、排查 skill 没生效时看这里。
version: v0.5
---

# WGC_MACHINE 环境备忘

本机通用信息。**WorkBuddy 客户端特有的问题**（Bash 工具补丁、pwsh 输出不回显、安全策略、沙箱代理）
另见 `local-workbuddy-quirks` —— 那个 skill 只挂在 WorkBuddy 下，因为其他 agent 没有那些限制。

机型 MECHREVO KUANGSHI Series，用户 `cgw06`，HOME = `C:\Users\cgw06`。

## 路径格式：MSYS 程序 vs Windows 原生程序

bash 里设了 `MSYS_NO_PATHCONV=1`，**参数不会被自动转换**，所以要分清喂给谁：

| 程序类型 | 例子 | 该用的路径格式 |
|---|---|---|
| MSYS 程序 | `ls` `wc` `cat` `grep` `sha256sum` | `/c/Users/cgw06/...` ✅ |
| Windows 原生程序 | `git.exe` `python.exe` `node.exe` | `C:/Users/cgw06/...` ✅（给 `/c/...` 会报 `cannot change to '/c/...'`） |

`~` 在 bash 里展开成 `/c/Users/cgw06`（MSYS 格式）→ 只适合喂 MSYS 程序。
喂原生程序时写全 Windows 路径，或先 `cd` 过去再执行（cwd 会被传成 Windows 格式）。

## junction（目录联接）

- 不需要管理员权限，实测非管理员可创建，读取透传正常
- 建：`New-Item -ItemType Junction -Path <link> -Target <dir>`
- **删必须用 `[System.IO.Directory]::Delete($link, $false)`** —— `Remove-Item -Recurse` 会连带删掉源目录内容
- Git for Windows 会把 junction 当普通目录，**挂载目录必须写进 `.gitignore`**，否则仓库里会出现重复内容
- 判断是不是联接：`($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0`

## 几个 AI 客户端的 skills 目录

| 客户端 | skills 目录 | 认 `~/.agents/skills` 公共位 |
|---|---|---|
| WorkBuddy | `~/.workbuddy/skills` | ❌ |
| ZCode | `~/.zcode/skills` | ✅ 唯一认的 |
| QClaw | `~/.qclaw/skills` | ❌（但 `~/.qclaw/openclaw.json` 有 `skills.load.extraDirs` 和 per-agent 白名单） |
| opencode | `~/.config/opencode/skills` | ❌（npm 全局装在 `~/AppData/Roaming/npm/opencode`） |
| 豆包工作 | `~/DoubaoWork/skills` | ❌ |

统一入口在 `~/.skills`，详见 `local-skills-hub`。

## 环境坐标

四个客户端都装在 `D:\APP_MAGIC\`；`~` 即 `C:\Users\cgw06`；
skill 名称必须匹配 `^[a-z0-9]+(-[a-z0-9]+)*$`（opencode 强制校验，不符会静默加载失败）。

## 已排查过、确认不用管的

- **长路径**：`LongPathsEnabled=1`，超 260 字符的路径可用
- **磁盘**：C 盘剩约 70G、D 盘剩约 210G，不缺空间
- **用户/系统 PATH**：本身是干净的
