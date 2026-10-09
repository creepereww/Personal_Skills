---
name: wgc-work1-px
description: 公司电脑 WGC-WORK1-PX 的本机环境事实 —— 机型（Lecoo）、HOME 与 %USERPROFILE% 错位（HOME 在 D:\AppData\Roaming\SPB_Data）、git 装在 D:\Git（与 bash 的 PortableGit git 是两套）、装了哪些 agent（WorkBuddy/ZCode/QClaw/Codex/MarsCode/Trae，QClaw 在 D 盘）、磁盘余量、**推送 GitHub 的正确姿势**（github.com 被 Watt Toolkit 劫持到 127.0.0.1，致 TLS 校验失败、push 静默 exit 128，需放宽校验 + 预置认证头；已固化成 scripts/push.ps1）、Everything 在 D:\ 但没装 es.exe。判断"工具在哪、网络通不通、怎么 push"时看这里。通用规则见 local-windows-shell-conventions。
version: v0.7
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
> 查目录时两个都要试。通用查法见 `local-memory-map`。

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

## 记忆与 skills 目录（本机实测）

| agent | 位置 | 形式 |
|---|---|---|
| WorkBuddy 用户级 | `C:/Users/cgw06/.workbuddy/MEMORY.md` | Markdown（`sync-preferences.ps1` 写入） |
| WorkBuddy 项目级 | `<工作区>/.workbuddy/memory/YYYY-MM-DD.md` | Markdown，每个工作区一份 |
| ZCode 全局指引 | `C:/Users/cgw06/.zcode/AGENTS.md` | Markdown（偏好分发目标之一） |
| ZCode 记忆 | `C:/Users/cgw06/.zcode/cli/db/db.sqlite` | SQLite，**不可直读** |
| QClaw 记忆 | `D:/AppData/Roaming/SPB_Data/.qclaw/memory/lossless/lcm.db` | SQLite，不可直读 |
| QClaw 状态 | `D:/AppData/Roaming/SPB_Data/.openclaw/state/openclaw.sqlite` + `identity/` | SQLite + json |
| Codex CLI | `C:/Users/cgw06/.codex/memories_1.sqlite`（`memories/` 为空目录） | SQLite，不可直读 |

**skills 目录**（哪些是我们的 junction、哪些是自带预置）：

| 目录 | 归属 |
|---|---|
| `~/.workbuddy/skills/` | ✅ 我们的 junction → `~/.skills/store` |
| `~/.agents/skills/` | ✅ 我们的 junction（ZCode 走这个公共位） |
| `~/.codex/skills/` | 自带 `.system/`（imagegen / openai-docs / plugin-creator） |
| `~/.marscode/builtin_skills` | 豆包 IDE 预置 |
| `~/.trae-cn/builtin/global/skills` | Trae CN 预置 |
| `D:/.../.qclaw/` | 只见到 `memory/`，**没有 skills 目录** |

**其他实测**：

- `~/.codebuddy/` **不存在** —— WorkBuddy 主客户端走 `~/.workbuddy/`，`.codebuddy` 是 CodeBuddy Code 的约定
- `C:/Users/cgw06/AppData/Local/Doubao/` 存在，但那是**豆包个人版**（只有 User Data），不是「豆包工作」
- `routing.json` 里 QClaw 那条写的是 `%USERPROFILE%\.qclaw`，**注定探测不到**（它实际在 D 盘、跟 `HOME` 走）。
  当前 `enabled:false`（不接管）所以无影响；将来若要接管，必须把探测路径改成按 `HOME` 解析

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

### ★★ github.com 被 Watt Toolkit 劫持到 127.0.0.1（push 失败的头号元凶）

**这是本机最要命的一条** —— 它会伪装成「网络不通」「证书错」「凭证错」，全都不对。

**硬证据**（`GIT_CURL_VERBOSE=1` 抓的）：

```
Host github.com:443 was resolved.
IPv4: 127.0.0.1                       ← github.com 被劫持到本机
Connected to github.com (127.0.0.1) port 443
issuer: CN=SteamTools Certificate; O=BeyondDimension; C=CN
server: WattToolkit                   ← Watt Toolkit（Steam++／瓦特工具箱）的本地反代
```

- 劫持**不是靠 hosts 文件**（`C:\Windows\System32\drivers\etc\hosts` 里没有 github 条目）——
  是 Watt Toolkit 自带的 DNS/加速，**别去改 hosts 找它**。
- **`api.github.com` 没被劫持**（走真实 GitHub）→ 所以 `curl` 打 API 一直正常，只有 git 用的
  `github.com` 中招。这也是「API 能干、git 不能干」这个怪现象的来源。
- 判据（脚本里用的）：**远端 host 解析到回环地址**（127.0.0.1 / ::1）即命中。

**由此派生的两个"假象"**（别被带偏）：

| 看着像 | 实际是 |
|---|---|
| openssl 报 `unable to get local issuer certificate (20)` | 被反代的**自签 SteamTools 证书**骗了，不是网络问题 |
| schannel 报 `CRYPT_E_NO_REVOCATION_CHECK`（curl 同理，要 `--ssl-no-revoke`） | 吊销检查（CRL/OCSP）在本机不可达 |

**真正的杀手**：`git push` 先请求 `info/refs?service=git-receive-pack` 拿 **401**（正常）→
调凭证助手取凭证 → **进程静默 exit 128，stdout/stderr 全空**。
反代本身是好的：用 **`Basic`** 认证 curl 同一 URL → **200** 并正确返回 `refs/heads/master`。
（❗ 用 `Bearer` 测会得到 401，那是**测错了** —— git 协议走 Basic。）

排除项（都验证过不是原因）：token 有效（`creepereww`，scopes `gist, repo, workflow`）、
`credential fill` 能取到凭证、网络通。

**✅ 解法（已验证）**：把 token 做成 Basic 头**预置**进请求（`http.extraHeader`），
让第一次请求就带认证，绕开「401 → 调助手 → 重试」这条走不通的路：

```powershell
$g="D:\Git\cmd\git.exe"; $repo="C:\Users\cgw06\.skills"
$r = ("protocol=https`nhost=github.com`n`n" | & $g -C $repo credential fill 2>&1 | Out-String)
$tok = (($r -split "`n") | Where-Object {$_ -like "password=*"}) -replace "^password=",""
$b64 = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("creepereww:$($tok.Trim())"))
& $g -C $repo -c "credential.helper=" -c "http.extraHeader=Authorization: Basic $b64" `
   -c http.sslBackend=openssl -c http.sslVerify=false push origin master
```

**根治（推荐）**：关掉 Watt Toolkit 的「GitHub 加速」，或退出 Watt Toolkit —— 之后走常规路径即可。

> ⚠️ 另有个 bash 侧的坑：**Bash 工具里的联网 git 操作会被静默吞掉**
> （`ls-remote` / `fetch` / `push` 一律 exit 0 + 零输出）。**同一个 git 在 PowerShell 里正常**。
> → 本机判断网络类 git 成败**必须走 PowerShell 工具**，Bash 里报「成功」是假象。

**为什么没能更早发现**：`Watt Toolkit` 是「加速工具」，平时开着不碍事（Web 访问、curl、API 全正常），
只在 git 的鉴权重试路径上把它自己撞坏了 —— 所以第一反应总是怀疑网络/凭证/证书，绕远路。

### ★ 在这台机推送 GitHub 的正确姿势（踩过坑）

**症状**：`git push` 报 `Failed to connect to github.com:443`，或（在 WorkBuddy 沙箱里）
`CONNECT tunnel failed, response 502`，或**静默 exit 128、什么都不打印**。
看似网络不通，实则下面几个坑叠加：

1. **WorkBuddy 沙箱会注入代理**（`http_proxy=http://127.0.0.1:58185`），该代理对
   `github.com` 返回 **502**（但 `api.github.com`/`gitee.com` 却是通的）。→ 推送必须**绕开代理**。
2. **`http.sslBackend=schannel`（Git for Windows 默认）在本机会报**
   `schannel: server closed abruptly (missing close_notify)`。→ 要改用 **openssl** 后端。
3. **`credential.helper` 默认是 `helper-selector`**（来自 WorkBuddy PortableGit 的 system gitconfig），
   非交互环境下会**卡住等 GUI 选凭证**（表现为 push 挂起，直到 120s 超时被 SIGTERM）；
   即使绕开它，也可能报 `could not read Username for 'https://github.com': terminal prompts disabled`。
   → 根治**不是**在命令行临时显式指定，而是**在仓库 local config 里"空值重置 + 只留 GCM"**
   （只 `--add` 一条 GCM **不清空 system 那条，弹框还会冒**）。详见 `local-workbuddy-quirks`
   「git 凭证：会弹 GUI 框卡住 push」。GCM 里**已存凭证**（`creepereww` + token，可用
   `echo -e "protocol=https\nhost=github.com\n" | /mingw64/bin/git-credential-manager get` 取到）。
4. `github.com:443` 本身**时通时断** —— 一次不行就**多重试几次**（实测第 2~4 次才成功）。
5. **`github.com` 被 Watt Toolkit 劫持到 `127.0.0.1`** —— 见上面「★★」那节。
   表现是「证书错 / 吊销检查错 / 静默 exit 128」，**不是网络不通**；解法是放宽 TLS 校验 +
   预置 Basic 认证头（`scripts/push.ps1` 已内置），或干脆关掉 Watt Toolkit 的 GitHub 加速。

> **⚠️ 这台机有两个 git，system 配置不一样**（实测）：
> - **bash 里** `which git` → PortableGit 的 `/mingw64/bin/git`（2.55），system config = **`helper-selector`**
> - **PowerShell 里** `Get-GitExe` → `D:\Git\cmd\git.exe`，system config = **`manager`**
>
> 所以「弹凭证框」只在 **bash** 下踩得到。PowerShell 里跑（含 `scripts/push.ps1`）走的是 D:\Git 的 git，
> system 那条不是 helper-selector，不会弹。两边读的**仓库级 `.git/config` 是同一份**（空值重置 + GCM），
> 所以实际生效的凭证链都干净。

**可用命令**（一次跑通；不行就重试）：
```bash
cd /c/Users/cgw06/.skills
env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY GIT_TERMINAL_PROMPT=0 \
  git -c credential.helper= -c credential.helper="/mingw64/bin/git-credential-manager" \
      -c http.sslBackend=openssl push origin master
```

**永久固化**（免得每次敲这么长 —— 已对本仓库设好）：
```bash
git config http.sslBackend openssl
git config --local --replace-all credential.helper ""     # 先清空 system 累积的列表（helper-selector）
git config --local --add credential.helper /mingw64/bin/git-credential-manager
```
之后只要绕开代理即可：`env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY git push`

> `git-credential-manager` 路径：`/mingw64/bin/git-credential-manager`（Git for Windows 自带）。

**一键推送**（推荐 —— 上面这些已固化成脚本）：
```bash
pwsh ~/.skills/scripts/push.ps1
```
它自动做六件事：绕开沙箱代理 → 在 openssl / schannel 之间交替重试 →
**先 fetch 检测**（远端领先就先 rebase 再推，免得 non-fast-forward 被拒）→
探测 **远程 host 是否被本地反代劫持**（解析到回环地址即命中，自动放宽 TLS 校验）→
push 若走常规路径失败，**退化为「预置 Basic 认证头」重试**（绕过 401 重试那条死路）→ push。
`-DryRun` 只看不推；`-Log out.txt` 结果落盘；`-NoRebase` 落后时停手让你手工处理。

> 安全性提醒：退化为预置认证头时，token 会出现在 git 进程的命令行里（同机同用户可见）。
> 单人机可接受；共用机器建议改用 SSH，或关掉本地反代走常规路径。

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
