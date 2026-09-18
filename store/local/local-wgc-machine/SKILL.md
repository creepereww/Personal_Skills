---
name: local-wgc-machine
description: 本机（WGC_MACHINE / MECHREVO KUANGSHI）环境红线与工具用法。在执行 shell 命令、调用 PowerShell/git、创建符号链接之前先看这里，能避开一批必踩的坑。涉及多 agent 的 skill 挂载时也可用。
version: v1.1
---

# WGC_MACHINE 环境备忘

机型 MECHREVO KUANGSHI Series，用户 `cgw06`，HOME = `C:\Users\cgw06`。

## Bash 工具是残的

`ls` / `dirname` / `head` / `tail` / `mkdir` 全部 `command not found`，启动时还会报 `dirname: command not found`（这行可忽略）。

→ **不要用 Bash 做文件操作**。改用 Read / Write / Edit / Glob / Grep 工具，或 `python -c "..."`。

→ **不要给命令加管道**（如 `pip install ... | tail`）：缺 tail/head 会让整条命令被 SIGTERM 掉。
需要看长输出就 `2>&1` 重定向到文件再读，长命令挂后台。

## PowerShell 是 7.6.6

`C:\Program Files\PowerShell\7\pwsh.exe`（在 PATH 里）。写脚本按 PS7 写：

- `Get-Item` 有 `LinkTarget` / `LinkType`，可以判断联接指向
- `Set-Content -Encoding UTF8` 默认无 BOM
- 要 UTF-8 无 BOM 写文件：`[System.IO.File]::WriteAllText($p, $t, (New-Object System.Text.UTF8Encoding($false)))`
- **`ConvertFrom-Json` 读 UTF-8 JSON 会乱码报错** → 改用 `python -c "import json; ..."` 解析
- 输出经常**不回显**：exit code 0 但 stdout 是空的 → 结论一律写文件再用 Read 工具读回来
- 复制的目标名含中文时，别只看命令回显，要用 `Get-ChildItem` 复核文件真的存在（曾出现"报成功但文件不存在"）

⚠️ 通过某些工具捕获 git 等 native 命令的输出时，中文会显示成乱码，但**存进去的内容是对的**，别以为是损坏了就去改编码。

## 被安全策略禁掉的（别试）

- `cmd.exe` / `cmd /c` — 一律拒绝
- `Add-Type` — 拒绝（即时编译 .NET）
- `New-Object -ComObject` — 拒绝
- Bash 里调 PowerShell，PowerShell 里调 cmd — 拒绝

→ 想走回收站删除（`FileSystem::DeleteDirectory` 那个 API）行不通，改用"移出去到备份目录"。

## git 不在 PATH

```
C:\Users\cgw06\.workbuddy\binaries\PortableGit\versions\1.2.0\cmd\git.exe
```

（WorkBuddy 自带的 2.55.0）脚本里用绝对路径。

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

## 环境坐标

四个客户端都装在 `D:\APP_MAGIC\`；`~` 即 `C:\Users\cgw06`；opencode 名称必须匹配 `^[a-z0-9]+(-[a-z0-9]+)*$`。
