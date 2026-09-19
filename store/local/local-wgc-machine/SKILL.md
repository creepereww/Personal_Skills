---
name: local-wgc-machine
description: 本机 WGC_MACHINE（MECHREVO KUANGSHI）的通用环境信息，对各个 agent 都适用。含路径坐标、MSYS 程序与 Windows 原生程序该用哪种路径格式、junction 目录联接的正确建删方式、四个 agent 各自读哪个 skills 目录、以及已排查确认无需处理的项。在这台机器上写 shell 脚本、建软链接、排查 skill 没生效时看这里。
version: v0.8
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
**⚠️ 写给别人复制粘贴的命令，一律用正斜杠** —— bash 里 `\U` `\c` `\w` 会被当转义符吃掉，
`C:\Users\cgw06\...` 会变成 `C:Userscgw06...` 然后报 command not found。
（自己踩过：给用户一段含反斜杠的命令，他粘进 bash 就废了。）
要引一个 Windows 程序的路径时，最稳的写法是**存变量再引用**：

```bash
WB="/c/Users/cgw06/.workbuddy/binaries/PortableGit/versions/1.2.0/cmd/git.exe"
"$WB" --version
```


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

**⚠️ git 在宿主的 Bash 工具里要用用户自装的（2.49）；真实终端用哪个都行**：

**实测对照**（同一个仓库、同一环境，只有 git 二进制不同）：

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

SSH 配置在 `~/.ssh/config`（⚠️ **不能写成 `config.txt`**，那样 ssh 不读 —— 真踩过），
里面让 github.com 走 `ssh.github.com:443`。

## 找文件：Everything + es（CLI）

**Everything**（本机已装、服务在跑）：

```
D://APP_HARDWARE//图吧工具箱202502//tools//其他工具//Everything//
  everything.exe    1.4.1.1026
  Everything.db     43 MB（索引）
```

- ✅ 桌面快捷方式：`C://Users//cgw06//Desktop//everything.exe - 快捷方式.lnk` —— 指向上面这个
- ❌ `D://APP_MAGIC//everything - 快捷方式.lnk` 是**旧的**，指向已失效的 `D://APP_COMMON//...`；
  **别拿它判断"装没装"**（我曾据此误报"没装"）

**es.exe**（命令行搜索，找文件用它，毫秒级）：

```
D://APP_MAGIC//es.exe     1.1.0.38     已加入用户 PATH
```

```bash
es -n 20 关键词               # 最多 20 条
es -p "*\.user_skills\*"    # 按路径匹配
es -ipc1 -n 5 关键词          # Everything 1.4 要用 IPC 1（新版 es 默认 IPC 2/3）
```

⚠️ **前提：Everything 的 GUI 客户端必须在跑**
- 只有 `Services` 会话的进程**不够**（那只是索引服务，不提供 es 要的 IPC）
- 症状：`Error 8: Everything IPC window was not found`
- **agent 启动不了它** —— WorkBuddy 禁了 WMI/`Start-Process` 创建进程（防逃逸），**得让用户自己开**

⚠️ **版本**：本机 Everything 是 **1.4.1.1026**，而 es 1.1.0.38 是配 **1.5** 的。
先试 `-ipc1`；若仍连不上，换旧版 es（1.1.0.30 及更早，GitHub `voidtools/es` 有全部 tag）。

## 环境坐标

四个客户端都装在 `D:\APP_MAGIC\`；`~` 即 `C:\Users\cgw06`；
skill 名称必须匹配 `^[a-z0-9]+(-[a-z0-9]+)*$`（opencode 强制校验，不符会静默加载失败）。

## 已排查过、确认不用管的

- **长路径**：`LongPathsEnabled=1`，超 260 字符的路径可用
- **磁盘**：C 盘剩约 70G、D 盘剩约 210G，不缺空间
- **用户/系统 PATH**：本身是干净的
