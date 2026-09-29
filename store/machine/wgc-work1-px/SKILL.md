---
name: wgc-work1-px
description: 公司电脑 WGC-WORK1-PX 的本机环境事实 —— 机型（Lecoo）、HOME 与 %USERPROFILE% 错位（HOME 在 D:\AppData\Roaming\SPB_Data）、git 装在 D:\Git、装了哪些 agent（WorkBuddy/ZCode/QClaw/Codex/MarsCode/Trae，QClaw 数据在 D 盘）、两条磁盘余量、**推送 GitHub 的正确姿势**（github.com:443 时通时断 + schannel 坑：要绕开沙箱代理、用 openssl 后端、GIT_TERMINAL_PROMPT=0 走 GCM 已存凭证、多重试）、Everything 1.4.1.1029 在 D:\ 但没装 es.exe。在这台机器上要判断"某个工具/客户端在哪、网络通不通、怎么 push"时看这里。通用规则（路径格式、junction、命名）见 local-windows-shell-conventions。
version: v0.3
---

# wgc-work1-px（公司电脑）

> 本文件只对**主机名为 `WGC-WORK1-PX` 的这台机器**成立。
> 脚本只把与本机主机名匹配的 machine 档挂给 agent，所以这里可以放心写死绝对路径。
> 通用规则见 `local-windows-shell-conventions`；仓库规则见 `local-skills-hub`。

## 身份

| 项 | 值 |
|---|---|
| 主机名 | `WGC-WORK1-PX`（`%COMPUTERNAME%` 大写返回；旧名 `WGC`） |
| 用户 | `cgw06`，`%USERPROFILE%` = `C:\Users\cgw06` |
| **HOME** | ⚠️ `D:\AppData\Roaming\SPB_Data`（**不是** `C:\Users\cgw06`！被 SPB 重定向工具改过） |
| 机型 | **Lecoo**（`Win32_ComputerSystem.Model` 为空） |
| 内存 | 15.8 GB |
| 系统 | Windows 11 家庭版 中文版，build 26200 |

> ⚠️ **HOME 与 USERPROFILE 不一致**是这台的重要事实：`%USERPROFILE%` 指向 C 盘，
> 但 `HOME` 指向 `D:\AppData\Roaming\SPB_Data`。**有些程序（如 QClaw）跟 `HOME` 走，数据落在 D 盘**；
> 大多数 agent（WorkBuddy / ZCode / 豆包）跟 `%USERPROFILE%`，落在 C 盘。
> 查目录时两个都要试。详见 `local-memory-map` 的「$HOME 错位」节。

## 磁盘

| 盘 | 剩余 |
|---|---|
| C: | 约 22 GB（**偏紧，装东西优先用 D 盘**） |
| D: | 约 104 GB |

## git

| 位置 | 说明 |
|---|---|
| `D:\Git\cmd\git.exe` | **PATH 里的就是它**，日常走这个 |

- 家那台用的 `D:\APP_CLOUD\PortableGit\cmd\git.exe` **这台不存在**。
- 宿主自带的 PortableGit（`~/.workbuddy/binaries/PortableGit/versions/<ver>/cmd/git.exe`）也在，
  但别在脚本里写死版本号（随升级变）。定位 git 一律用 `scripts/_common.ps1` 的 `Get-GitExe`。

## 已装的 agent

| 客户端 | 装了 | 位置 / 判据 |
|---|---|---|
| WorkBuddy | ✅ | `~/.workbuddy/`（走 `%USERPROFILE%`，在 C 盘） |
| ZCode | ✅ | `C:/Users/cgw06/.zcode/`（含真实会话数据，走 `%USERPROFILE%`） |
| QClaw | ✅ | **在 D 盘**：`D:/AppData/Roaming/SPB_Data/.qclaw/`（`memory/lossless/lcm.db`）+ `.openclaw/`（`state/openclaw.sqlite`、`identity/`）。跟 `HOME` 走 |
| opencode | ❌ | 无安装痕迹、npm 全局目录都不存在 |
| 豆包工作 | ❌ | 无安装痕迹（`~/DoubaoWork`、`%LOCALAPPDATA%\DoubaoWork` 均不存在） |
| Codex CLI | ✅ | `C:/Users/cgw06/.codex/`（`memories_1.sqlite` 等） |
| MarsCode | ✅ | `C:/Users/cgw06/.marscode/`（预置 `builtin_skills`） |
| Trae CN | ✅ | `C:/Users/cgw06/.trae-cn/`（预置 `builtin/global/skills`） |

> 各处目录的详细机制（记忆形式、是否认公共位）见 `local-memory-map`，本表只记"装没装、在哪"。

## 网络

**直连实测**（这台机器 + 公司网络）：

| 目标 | 结果 |
|---|---|
| `github.com:443` | ⚠️ **时通时断**（多数时刻超时/被拦，偶发通）—— 见下方"推送踩坑" |
| `github.com:22` | ✅ 通 |
| `ssh.github.com:443` | ✅ 通 |
| `gitee.com:443` | ✅ 通 |

代理状态：
- 系统代理 `ProxyEnable = 0`（**关闭**），注册表里残留 `ProxyServer=127.0.0.1:26561` 但没启用
- `~/.ssh/config` **不存在**（没配过 SSH 通道）
- 仓库 remote 是 HTTPS：`https://github.com/creepereww/Personal_Skills.git`

### ★ 在这台机推送 GitHub 的正确姿势（踩过坑）

**症状**：`git push` 报 `Failed to connect to github.com:443`，或（在 WorkBuddy 沙箱里）
`CONNECT tunnel failed, response 502`。看似网络不通，实则三个坑叠加：

1. **WorkBuddy 沙箱会注入代理**（`http_proxy=http://127.0.0.1:58185`），该代理对
   `github.com` 返回 **502**（但 `api.github.com`/`gitee.com` 却是通的）。→ 推送必须**绕开代理**。
2. **`http.sslBackend=schannel`（Git for Windows 默认）在本机会报**
   `schannel: server closed abruptly (missing close_notify)`。→ 要改用 **openssl** 后端。
3. **`credential.helper` 默认是 `helper-selector`**（来自 WorkBuddy PortableGit 的 system gitconfig），
   非交互环境下会**卡住等 GUI 选凭证**（表现为 push 挂起，直到 120s 超时被 SIGTERM）。
   → 但 **GCM 里已存了凭证**（`git-credential-manager get` 能取到 `creepereww` + token），
   所以配 `GIT_TERMINAL_PROMPT=0` 即可让它用已存凭证、不再弹窗。
4. `github.com:443` 本身**时通时断** —— 一次不行就**多重试几次**（实测第 4 次成功）。

**可用命令**（一次跑通；不行就重试）：
```bash
cd /c/Users/cgw06/.skills
env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY \
  GIT_TERMINAL_PROMPT=0 git -c http.sslBackend=openssl push origin master
```

**永久固化**（免得每次敲）—— 对仓库设 openssl 后端即可，代理和凭证按上面加：
```bash
git config http.sslBackend openssl
```

> `git-credential-manager` 路径：`/mingw64/bin/git-credential-manager`（Git for Windows 自带）。
> 查有没有存凭证：`echo -e "protocol=https\nhost=github.com\n" | git-credential-manager get`。

## Everything / es

| 工具 | 这台的情况 |
|---|---|
| Everything | ✅ 在跑，路径 `D:\Everything-1.4.1.1029.x64\everything.exe`（版本 **1.4.1.1029**） |
| `es.exe`（命令行搜索） | ❌ **没装**，不在 PATH |

→ 想在这台用 `es` 命令行搜文件，得先装 `es.exe`（GitHub `voidtools/es`）。
装之前只能用 `Get-ChildItem` 之类的方式找文件。

## 已排查过、确认不用管的

- **长路径**：`LongPathsEnabled=1`，超 260 字符的路径可用
- **PATH**：用户 PATH 30 条，本身干净
