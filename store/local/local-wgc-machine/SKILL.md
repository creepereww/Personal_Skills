---
name: local-wgc-machine
description: 本机 WGC_MACHINE（MECHREVO KUANGSHI）的通用环境信息，对各个 agent 都适用。含路径坐标、MSYS 程序与 Windows 原生程序该用哪种路径格式、junction 目录联接的正确建删方式、四个 agent 各自读哪个 skills 目录、以及已排查确认无需处理的项。在这台机器上写 shell 脚本、建软链接、排查 skill 没生效时看这里。
version: v0.6
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

## 网络（GitHub 相关）

**直连实测**（这台机器 + 当前网络环境）：

| 目标 | 结果 |
|---|---|
| `github.com:443` | ❌ 超时 |
| `github.com:22` | ✅ 通 |
| `ssh.github.com:443` | ✅ 通 |
| `gitee.com:443` | ✅ 通 |

→ **GitHub 走 SSH 没问题，HTTPS 直连必挂**（要挂代理）。
注意第 1 行和第 3 行**同样是 443 端口**却一个不通一个通 —— 是 `github.com` 的**目标 IP 被阻**，不是端口被封。

**代理（两个别搞混）**：

- **系统持久代理**：`127.0.0.1:26561`（注册表 `ProxyEnable=1`，用户自装的）
- **WorkBuddy 会话内注入**：`HTTP_PROXY`/`HTTPS_PROXY` 指向它自己的沙箱代理，**端口随会话变**，别硬编码
- 给 git 配代理：`git config --global http.proxy http://127.0.0.1:26561`；不用了 `--unset http.proxy`

**本机两套 git**：

| 位置 | 版本 | 用途 |
|---|---|---|
| `D:\APP_CLOUD\PortableGit\cmd\git.exe` | 2.49 | 用户自装，**已加入用户 PATH**，日常走它 |
| `~/.workbuddy/binaries/PortableGit/versions/<ver>/cmd/git.exe` | 2.55 | 宿主自带。版本更新，但**在本环境写不进 remote-tracking ref**，且路径随版本变 ⇒ 别用 |

**⚠️ 在宿主的 Bash 工具里，git 用用户自装的（2.49），别用宿主自带那份**：

宿主自带（`<PortableGit>/versions/1.2.0/...`，2.55）**写不进 remote-tracking ref** ——
能连远端、能 fetch、能 push，但 `refs/remotes/origin/*` 不落盘，`git status` 永远 `[gone]`
（**数据不受影响**，`git ls-remote origin` 可核对）。

**已逐个排除、都不是原因**：环境变量（干净 `env -i` 也一样）、`credential.helper`
（它那份被改成非标准的 `helper-selector`）、`core.fscache`、目录不存在（手动 mkdir 后照样失败）、
`cmd/` 存根 vs `mingw64/bin` 真身。
**同一目录、同一环境，只有 git 二进制不同 —— 2.49 正常，2.55 不行，且 `update-ref` 还返回 0。**

⚠️ **尚未验证**：2.55 在**真实终端**（宿主之外）是否也这样。如果那里正常，
说明这是「宿主工具环境 × 2.55」的交互问题，**不是 git 版本本身的缺陷** ——
所以**别断言「2.55 有 bug」**（全世界跑 2.55 的人很多，普遍性 bug 不成立）。

**实用结论**：在宿主里就用 2.49。shim 已把 `D:\APP_CLOUD\PortableGit\cmd` 排到 PATH 最前，
并加了 `hash -r`（改 PATH 顺序必须清 bash 的命令 hash 缓存，否则 `command -v git` 仍指向旧的）。
**自己装的 git 升级后若换了路径，记得同步改 shim。**

SSH 配置在 `~/.ssh/config`（⚠️ **不能写成 `config.txt`**，那样 ssh 不读 —— 真踩过），
里面让 github.com 走 `ssh.github.com:443`。

## 环境坐标

四个客户端都装在 `D:\APP_MAGIC\`；`~` 即 `C:\Users\cgw06`；
skill 名称必须匹配 `^[a-z0-9]+(-[a-z0-9]+)*$`（opencode 强制校验，不符会静默加载失败）。

## 已排查过、确认不用管的

- **长路径**：`LongPathsEnabled=1`，超 260 字符的路径可用
- **磁盘**：C 盘剩约 70G、D 盘剩约 210G，不缺空间
- **用户/系统 PATH**：本身是干净的
