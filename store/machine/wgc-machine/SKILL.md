---
name: wgc-machine
description: 家里那台电脑（主机名 WGC_MACHINE，机型 MECHREVO KUANGSHI）的本机环境事实 —— 四个客户端装在 D:\APP_MAGIC、HOME 无错位（= USERPROFILE）、已装 ZCode/opencode/豆包工作/Codex/Trae/Qoder 各自在哪（QClaw 已停运卸载）、git 用 D:\APP_CLOUD 自装的 2.49、github.com 主站通但 release 下载被限速（走南大镜像或 SSH）、系统代理 26561 可能没开（用前先测）、Everything 在 图吧工具箱 下但 es.exe 已不在（CLI 搜索需重装）、外接 USB 硬盘带 WTG 便携系统（插着可能被固件优先启动）。在那台机器上判断"工具在哪、网络通不通、某个 agent 装没装"时看这里。通用规则见 local-windows-shell-conventions。
version: v0.6
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
| QClaw | ❌ | **2026-11-22 停运后已彻底卸载**（官方卸载器静默移除 `D:\APP_MAGIC\QClaw` 并连带删了 `~/.qclaw`、`Roaming\QClaw`；更新器缓存进回收站）。残留 `~/.openclaw\`（identity/state 几个小文件）暂留未删，别再当作 QClaw 配置目录用 |
| Codex CLI | ✅ | `~/.codex/`（含 `memories_1.sqlite`、`skills/.system/`；`skills/` 下无自建） |
| Trae CN | ✅ | `~/.trae-cn/`（含 `builtin/`、`extensions/`） |
| **Qoder** | ✅ | `~/.qoder/`（**国际版**；`~/.qoder-cn` 不存在 → 不是 CN 版）。项目落在 `~/Documents/Qoder/<日期>-<hash>/`。详见下节 |
| MarsCode | ❌ | `~/.marscode/` 不存在 |
| Quicker | ✅ | 主程序 `C:\Program Files\Quicker\QuickerStarter.exe`；数据 `%LOCALAPPDATA%\Quicker\`；动作库 `Documents\Quicker\` |

### Quicker 中转动作 ID（本机）

两个 quicker 系 skill 都依赖一个**本机中转动作**的 ID —— ID 是装完动作才生成的，各机不同，
填错不会报"ID 错"，而是静默跑到别人机器上（或回退到作者 ID）后才失败：

| skill | config 位置 | key | 本机值 |
|---|---|---|---|
| `quicker-skill`（Roslyn 脚本动作） | `store/cache/quicker-skill/config.json` | `wrench_action_id` | `fbbcb15c-bf85-4221-8a30-fe610a6a93b6`（QK扳手） |
| `qk-action-creator`（组合动作） | `store/cache/qk-action-creator/config.json` | `InjectorActionId` | `7583f9e1-27a4-4c8c-8ddb-64a4645b8032`（AI生成动作） |

⚠️ **这两个 config 会被 `pull.ps1` 冲掉**：`quicker-skill/config.json` 是上游文件，重拉会退回作者的
`3eebe8d9-7521-46fa-b2e1-502754bce14f`；`qk-action-creator/config.json` 是本机的（上游没带）。
重拉后按上表填回。`build.ps1` 在配置缺失时会**回退到作者 ID**，所以配错的报错很有迷惑性 ——
别往网络、权限、动作没装那边查。

### Qoder 本机实测

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

- **WorkBuddy 技能加载源**：`~/.workbuddy/.skill-list-cache.json` —— 绝大多数条目是
  `userSettings`（来自我们的 junction），另有少量 `plugin` 条目
- **自建专家**：`~/.workbuddy/plugins/marketplaces/my-experts/` 存在但**为空**（还没有自建专家）
- **`.codebuddy/`**：存在，但只有 `diagnostics/`、`logs/`，没有 `skills/`、`rules/`

## 网络（⚠️ 和公司电脑完全相反）

**直连实测**（那台机器 + 家用网络）：

| 目标 | 结果 |
|---|---|
| `github.com:443`（主站） | ✅ 通，响应快 |
| `api.github.com:443` | ✅ 直连快（查 release、asset SHA 用它） |
| GitHub release 资产 CDN | ⚠️ 通但**被限速**（~10KB/s 量级），大文件别走直链 |
| `github.com:22` / `ssh.github.com:443` | ✅ 通（SSH 路线可用） |
| `gitee.com:443` | ✅ 通 |

→ **git fetch/push 直连 HTTPS 没问题；下载 release 大文件必须换路线**：

- **GitHub release → 南大镜像**：`https://mirrors.nju.edu.cn/github-release/<owner>/<repo>/LatestRelease/<文件名>`
  （实测 MB/s 级满速；`LatestRelease` 可换成具体 tag，目录列表可直接浏览，`sha256.txt` 等校验文件也在）
- **其他大文件 → 厂商官方下载站/国内 CDN**（实测 HotPE 官方站可达 ~600KB/s）
- 下载后**交叉校验 SHA256**（`Get-FileHash`）：对照 GitHub API 的 asset `digest` 字段或官方
  `sha256.txt` —— 镜像/CDN 都不例外

**代理（两个别搞混）**：

- **系统持久代理**：`127.0.0.1:26561`（用户自装）。⚠️ **可能没开**：实测遇到过 `ProxyEnable=0`、
  端口无监听，但 `ProxyServer` 值还留着 —— 别被注册表里的地址骗了。**用前先实测**
  （`curl -x http://127.0.0.1:26561 https://api.github.com/`），通了再依赖它
- **WorkBuddy 会话内注入**：`HTTP_PROXY`/`HTTPS_PROXY` 指向它自己的沙箱代理，**端口随会话变**，别硬编码
- 确认代理在跑后才给 git 配：`git config --global http.proxy http://127.0.0.1:26561`；不用了 `--unset http.proxy`

SSH 配置在 `~/.ssh/config`（⚠️ **不能写成 `config.txt`**，那样 ssh 不读 —— 真踩过），
里面让 github.com 走 `ssh.github.com:443`。

## Everything + es（CLI）

**Everything**（已装）：

```
D:\APP_HARDWARE\图吧工具箱202502\tools\其他工具\Everything\
  everything.exe    1.4.1.1026
  Everything.db     （索引）
```

- ✅ 桌面快捷方式：`C:\Users\cgw06\Desktop\everything.exe - 快捷方式.lnk` —— 指向上面这个
- ❌ `D:\APP_MAGIC\everything - 快捷方式.lnk` 是**旧的**，指向已失效的 `D:\APP_COMMON\...`；
  **别拿它判断"装没装"**（曾据此误报"没装"）
- ⚠️ **GUI 默认没在跑**：只有 `Services` 会话的 Everything.exe（索引服务）在，
  它不提供 es 要的 IPC。**agent 启动不了 GUI** —— 得让用户自己开

**es.exe：已不在本机** ❌

- 原记录 `D:\APP_MAGIC\es.exe`（1.1.0.38，曾在用户 PATH）—— 实测文件已不存在，PATH 里没有，
  Everything 目录里也没有（常见安装根目录都搜过）
- → **CLI 文件搜索当前不可用**。要用先从 GitHub `voidtools/es` 重装（release 走南大镜像，见网络节），
  再让用户把 Everything GUI 开起来
- 重装后的已知坑：es 与 Everything 1.4.1.1026 默认 IPC 直接兼容；"只搜文件夹"是 **`/ad`**
  （没有 `-folder`，写错报 `Error 6: Unknown switch`）；GUI 没开报 `Error 8: Everything IPC window was not found`

## 外接 USB 硬盘（带 WTG 便携系统）

- 型号 `ST500LT012-9WS142`（500GB 笔记本盘 + 硬盘盒），GPT 分区：MSR + EFI +
  **WTG 系统分区** + **数据分区**（盘符随挂载顺序变，别认死字母）
- WTG 是 **Win10 Pro 1909** 便携系统（`PortableOperatingSystem=1`，sysprep generalize 镜像部署，
  每次开机 `/respecialize` 重识别硬件）—— 教程式手工流程（diskpart + DISM + bcdboot）做的，
  不是 Rufus/WinToUSB/官方 pwcreator 的产物
- ⚠️ **插着它时 UEFI 可能优先从它启动**：Windows 更新自动重启后就曾直接进到便携系统。
  在便携系统里**别拔盘** —— 系统盘就是它，拔了必死机、关机必卡
- ⚠️ **数据分区是用户整理好的资料**。做 Ventoy/PE 会**格式化整盘** ——
  没用户明确确认前别动这块盘的分区；要玩 Ventoy 另找空闲 U 盘

## 已排查过、确认不用管的

- **长路径**：`LongPathsEnabled=1`，超 260 字符的路径可用
- **用户/系统 PATH**：本身是干净的
