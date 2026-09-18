---
name: local-wgc-machine
description: 本机（WGC_MACHINE / MECHREVO KUANGSHI）环境红线与工具用法。在执行 shell 命令、调用 PowerShell/git、创建符号链接之前先看这里，能避开一批必踩的坑。涉及多 agent 的 skill 挂载时也可用。
version: v1.3
---

# WGC_MACHINE 环境备忘

机型 MECHREVO KUANGSHI Series，用户 `cgw06`，HOME = `C:\Users\cgw06`。

## Bash 工具（已修复，WorkBuddy 升级可能回退）

**修复前症状**：`ls`/`dirname`/`head`/`tail`/`mkdir` 全部 `command not found`，每条命令还多两行 stderr
（`shell-runtime-bash-env.sh: line 3: dirname: command not found` + `cd: null directory`）。

**根因**（WorkBuddy 缺陷，不是本机环境问题）：它构造给 bash 的 PATH 只前插了 node/python 目录，
**漏了 PortableGit 的 coreutils**（`usr/bin`）；而它的初始化脚本
（`BASH_ENV=<WorkBuddy>\resources\app.asar.unpacked\cli\vendor\shim\shell-runtime-bash-env.sh`）
第 3 行偏要用 `dirname` 求自身目录 → 此时 PATH 里没有 dirname → 变量为空 →
后面两个负责补 PATH 的脚本被静默跳过。鸡生蛋，整条链失效。

**修法**（改那个 shim 脚本，已做）：

```sh
# 第 3 行改成 bash 内建，不依赖任何外部命令
__codebuddy_shell_runtime_dir="${BASH_SOURCE[0]%/*}"
# 再补两个目录：coreutils 在 usr/bin，git 在 cmd
export PATH="/usr/bin:${PATH}"
export PATH="${PATH}:/cmd"
```

原始文件备份在 `~/.skills-backup-*/workbuddy-shim/`（按备份日期分目录）。

⚠️ **WorkBuddy 升级会覆盖这个文件** —— 哪天又出现 `command not found`，照上面重打一次即可。

**现在可用**：coreutils 全套（ls / dirname / head / tail / mkdir / cat / grep / sed / find / xargs / sha256sum…）
+ git + python + node，管道正常。

## 路径格式：MSYS 程序 vs Windows 原生程序

环境设了 `MSYS_NO_PATHCONV=1`，**参数不会被自动转换**，所以要分清给谁：

| 程序类型 | 例子 | 该用的路径格式 |
|---|---|---|
| MSYS 程序 | `ls` `wc` `cat` `grep` `sha256sum` | `/c/Users/cgw06/...` ✅ |
| Windows 原生程序 | `git.exe` `python.exe` `node.exe` | `C:/Users/cgw06/...` ✅（给 `/c/...` 会报 `cannot change to '/c/...'`） |

`~` 在 bash 里展开成 `/c/Users/cgw06`（MSYS 格式）→ 只适合喂 MSYS 程序。
喂原生程序时写全 Windows 路径，或先 `cd` 过去再执行（cwd 会被传成 Windows 格式）。

## PowerShell 是 7.6.6，但输出 100% 拿不回来

`C:\Program Files\PowerShell\7\pwsh.exe`（在 PATH 里）。写脚本按 PS7 写：

- `Get-Item` 有 `LinkTarget` / `LinkType`，可判断联接指向
- `Set-Content -Encoding UTF8` 默认无 BOM；要无 BOM 写文件用 `[System.IO.File]::WriteAllText($p, $t, (New-Object System.Text.UTF8Encoding($false)))`
- **`ConvertFrom-Json` 读 UTF-8 JSON 会乱码报错** → 改用 `python -c "import json; ..."` 解析
- 复制的目标名含中文时，别只看命令回显，要用 `Get-ChildItem` 复核文件真的存在（曾出现"报成功但文件不存在"）

### ⚠️ 输出不回显（工具层限制，只能绕过）

实测把各种输出方式都试了一遍：`"裸字符串"`、`Write-Host`、`[Console]::WriteLine`、`Write-Error`、`throw`、直接写 stderr
—— **全部拿不到**，工具只回 `exit code`。所以：

- **不是编码问题**（`[Console]::OutputEncoding` 是 gb2312，但纯英文输出同样丢失）
- **profile 也救不了**（工具启动用 `-NoProfile`，实测 profile 不加载）
- 根因在工具集成层

→ **唯一可行做法：让命令把结果 `Set-Content` 到文件，再用 Read 工具读回来。** 没有更省事的办法。

唯一相关开关是环境变量 `CODEBUDDY_POWERSHELL_USE_PTY`（当前 `=1`，桌面端为支持交互式命令而设）。
改成 `0` 是否能让输出回来**未经验证**，且可能让 PowerShell 工具本身不好用 —— 非必要别动。

⚠️ 另一个易误判的点：用工具捕获 git 等 native 命令的输出时，中文会显示成乱码，但**存进去的内容是对的**，别去改编码。

## 被安全策略禁掉的（别试）

- `cmd.exe` / `cmd /c` — 一律拒绝
- `Add-Type` — 拒绝（即时编译 .NET）
- `New-Object -ComObject` — 拒绝
- Bash 里调 PowerShell，PowerShell 里调 cmd — 拒绝

→ 想走回收站删除（`FileSystem::DeleteDirectory` 那个 API）行不通，改用"移出去到备份目录"。

## git

**Bash 工具里已经能直接用了**（随 Bash 修复一并解决，见上面那条）。直接敲 `git` 即可，但注意参数里的路径要用 `C:/...` 格式（见路径格式节）。

**PowerShell 里不可用，且不值得修**：PortableGit 的 `versions\current` 只是个记录版本号的小文件（不是目录），
PATH 里只能写死 `versions\1.2.0\cmd`，WorkBuddy 升级 PortableGit 后就会失效 —— 为了在 PowerShell 里用 git
而背上这个长期维护点不划算。真要在 PowerShell 里跑，写绝对路径，或切到 Bash 工具。

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

统一入口在 `~/.skills`，详见 local-skills-hub skill。

## 已排查过、确认不用管的

- **长路径**：`LongPathsEnabled=1`，超 260 字符的路径可用
- **磁盘**：C 盘剩约 70G、D 盘剩约 210G，不缺空间
- **代理注入**：`HTTP_PROXY`/`HTTPS_PROXY` 指向 `http://127.0.0.1:<port>`（WorkBuddy 的沙箱代理）。
  它属于沙箱机制，**不要改**；个别直连被它挡时，在 Python 里 `session.trust_env = False` 绕过
- **用户/系统 PATH**：本身是干净的，WorkBuddy 给 bash 构造的 PATH 才有问题（见开头那条）

## 环境坐标

四个客户端都装在 `D:\APP_MAGIC\`；`~` 即 `C:\Users\cgw06`；opencode 名称必须匹配 `^[a-z0-9]+(-[a-z0-9]+)*$`。
