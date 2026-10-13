---
name: local-windows-shell-conventions
description: Windows 上跨机器通用的 shell 与链接约定 —— MSYS 程序的 /c/ 路径 vs Windows 原生程序的 C:/ 路径该用哪种、junction 目录联接的正确建删方式（含"不能指向 UNC 路径"这个静默坑）、Git for Windows 把 junction 当普通目录的坑、skill 目录命名正则、各 AI 客户端的 skills 目录、主机名大小写匹配。写 shell 脚本、建软链接、打通 WSL 与 Windows 目录（含 9P 上放 SQLite 数据库必被回退的坑）、排查路径报错或 skill 没生效时看这里。机器专属信息（机型、客户端装在哪个盘、网络情况）见 machine 档；WorkBuddy 的 skill/专家机制见 local-memory-map。
version: v0.10
---

# Windows Shell 与链接约定（跨机器通用）

本 skill 只放**换台 Windows 机器也成立**的规则。机型、磁盘、客户端安装位置、网络实测这类
**只对某台机器成立**的事实，放在 `store/machine/<主机名>/` 下，见文末。

## 路径格式：MSYS 程序 vs Windows 原生程序

若终端设了 `MSYS_NO_PATHCONV=1`，**参数不会被自动转换**，所以必须分清喂给谁：

| 程序类型 | 例子 | 该用的路径格式 |
|---|---|---|
| MSYS 程序 | `ls` `wc` `cat` `grep` `sha256sum` | `/c/Users/<用户名>/...` ✅ |
| Windows 原生程序 | `git.exe` `python.exe` `node.exe` | `C:/Users/<用户名>/...` ✅（给 `/c/...` 会报 `cannot change to '/c/...'`） |

`~` 在 bash 里展开成 `/c/Users/<用户名>`（MSYS 格式）→ **只适合喂 MSYS 程序**。

**⚠️ 别用 bash 变量把路径传给 python** —— bash 的 `/c/...` 传过去会变成 `\c\...`，
python 在 Windows 上把它当"当前盘符根路径" → **凭空造出 `C://c//Users//...` 这种垃圾目录树**。
（真踩过：`SRC = r"$SRC".replace("/", "\\")` 这种拼法，脚本后面报错了，但 `os.makedirs` 已经先执行，
垃圾留下了。）**正确做法**：路径直接在 python 里写成 `r"C://Users//<用户名>//..."`，
或从 `os.path.expanduser` 拿。

**⚠️ 同一个坑不用变量也会踩** —— 在 python 源码里直接写字面量 `"/home/cgw06/xxx"`（想写 WSL 侧文件时很容易这么写），
Windows python 会把它当成**当前盘根目录下的相对路径** → 静默写到 `C:\home\cgw06\xxx`，还打印"写入成功"。
（真踩过：给 WSL 写脚本，`open("/home/cgw06/...")` 落到了 `C:\home\...`，得靠 `ls` 回读才发现。）
给 WSL 侧写文件必须用 UNC：`r"\\wsl.localhost\Ubuntu\home\cgw06\..."`。

**⚠️ 反向：python 的 stdout 给 bash 用时，必须去 `\r`** —— Windows 版 python 输出是 `\r\n`，
bash 的 `read` / `case` 会把 `\r` 一起吃进去（变量实际是 `OK\r`，匹配不上 `case OK)`，
表现成"莫名失败 / 查不到结果"）。修法：管道后加 `tr -d '\r'`，或 `v="${v%$'\r'}"`。
（真踩过：`read -r latest state < <(python -c ...)` 拿到的 state 带 `\r` → case 永远落到默认分支，
而同一段 python 在交互式终端手测却是对的，极易误判成网络问题。）

**⚠️ 写给别人复制粘贴的命令，一律用正斜杠** —— bash 里 `\U` `\c` `\w` 会被当转义符吃掉，
`C:\Users\...` 会变成 `C:Users...` 然后报 command not found。

要引一个 Windows 程序的路径时，最稳的写法是**存变量再引用**：

```bash
EXE="C:/path/to/program.exe"
"$EXE" --version
```

喂原生程序时写全 Windows 路径，或先 `cd` 过去再执行（cwd 会被传成 Windows 格式）。

## junction（目录联接）

- **不需要管理员权限**，实测非管理员可创建，读取透传正常
- ⚠️ **目标只能是本地卷，不能是 UNC 路径**（`\\wsl.localhost\...`、`\\server\share` 都不行）。
  坑在于它**不会报错**：`New-Item -ItemType Junction` 返回成功、`Test-Path` 也是 True，
  但一访问就报「文件名、目录名或卷标语法不正确」。想跨到 UNC 只能用符号链接，
  而符号链接常规需要管理员/开发者模式；实测非管理员跑 `New-Item -ItemType SymbolicLink`
  会**静默降级成普通空目录**（不抛异常、`Attributes` 里没有 `ReparsePoint`）。
  → 结论：**别指望从 Windows 侧链接到 WSL 里的目录**，要打通就反过来 ——
  真身放本地 NTFS，让 WSL 侧 `ln -s` 指到 `/mnt/<盘>/...`。
- ⚠️ **反向也不通：WSL 里的符号链接，Windows 侧看不见。** 通过 `\\wsl.localhost\...` 访问时，
  那个软链在资源管理器里显示成一个 **1KB 的"文件"**，点不进去；实测 `head` 报 `Not a directory`、
  列目录报 `Input/output error` —— 9P 通道不解析 Linux 软链。
  **但 WSL 内部完全正常**（Linux 自己解析），`cd`/编辑器/编译都不受影响。
  → 给用户解释时别慌：这是预期行为，不是搞坏了。要在资源管理器里能点进去，
  只能改用 `mount --bind`（写进 `/etc/fstab`，会变成真目录），或者干脆直接看真身那份。
- ⚠️ **打通之后，别把 SQLite 数据库留在 `/mnt/<盘>` 上。** 9P 给不了 WAL 模式要的共享内存，
  工具通常会**自己绕开**：实测 VS Code C/C++ 扩展（cpptools 1.34）检测到工程 `.vscode/` 落在 9P 上，
  就把 `browse.VC.db` 自动挪到 `~/.cache/vscode-cpptools/<hash>/`（ext4），并提示
  "no compatible database location"。**与其让它回退，不如显式指定**：在 `c_cpp_properties.json` 里把
  `browse.databaseFilename` 写成 ext4 绝对路径（如 `/home/<用户>/.cache/vscode-cpptools/<项目>-browse.db`）——
  改完**即时生效并重建索引，不用重开 VS Code**；反之若指向 `/mnt/...`，Windows 侧看到的
  `${workspaceFolder}` 经软链落到 9P，就是被回退的那种情况。
- ⚠️ **从 Windows 侧对 WSL 文件做写/删操作不可靠，能回 WSL 做就回 WSL 做。** 实测：
  - **删不掉**：`rm`、Python `os.remove()` 都会走 WorkBuddy 的 safe-delete，而它在 UNC 上
    **进不了回收站 → fail-closed 直接拒绝删除**（报 `trash-failed` / `windows error -2147024894`）。
    唯一测通的是 PowerShell 的 `[System.IO.File]::Delete($path)`。
  - **元数据会假阴性**：同一时刻 bash `ls` 看得见，Python 的 `os.path.isdir/listdir` 却返回 `False`；
    `open(p,"w")` 甚至**报 `FileNotFoundError` 但文件其实已经建出来了**。
    遇到这种"说找不到、其实在"的情况，换正斜杠 `//wsl.localhost/...` 重试，
    别当成路径写错去排查。
  → 给 WSL 写文件用 UNC 就行；但**删除、改权限这类操作一律让用户在 WSL 终端里做**。
- ⚠️ **`~/bin/wsl2win` 和 `links.conf` 别在 Windows 侧用编辑器改**：可能存成 CRLF
  （shebang 失效）或丢执行位。改完回 WSL 里 `bash -n` 验语法、`chmod +x` 补权限。
- ⚠️ **9P 显示的权限位是假的，且 Windows 侧复制进 ext4 会丢执行位**（实测 2026-10-13）：
  `.NET Copy` 经 `\\wsl.localhost` 写进 WSL 的文件，Windows 侧 `ls` 照样显示 `rwxr-xr-x`，
  WSL 里真实是 644，一执行就 `Permission denied`；python `os.stat` 经 9P 则一律报 0666。
  **两个视图都不可信**。凡是 Windows 侧复制/新建到 ext4 的可执行文件，最后必须在 WSL 里
  `chmod +x`（`mv`/`cat >` 保 inode 不受此影响）
- 建：`New-Item -ItemType Junction -Path <link> -Target <dir>`
- **删必须用 `[System.IO.Directory]::Delete($link, $false)`** —— `Remove-Item -Recurse` 会连带删掉**源目录内容**
- Git for Windows 会把 junction 当普通目录，**挂载目录必须写进 `.gitignore`**，否则仓库里会出现重复内容
- 判断是不是联接：`($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0`
- PowerShell 7 有 `.LinkTarget` / `.LinkType` 可读目标；PowerShell 5.1 没有，得用 `cmd /c dir /AL`

## 可用脚本：打通 WSL 与 Windows 目录

`~/bin/wsl2win` —— 把 WSL 里的项目目录换成指向 Windows 真身的软链（即上面那个"反向方案"）。

- **在 WSL 里跑**，不能在 PowerShell/CMD 里跑（它要 `ln -s` 和 `/mnt/<盘>`）
- 用法看 `wsl2win --help`，别把参数表抄到这儿
- 配置表查找顺序：`$WSL2WIN_CONF` → **脚本同目录的 links.conf**（现用，用户嫌
  `~/.local` 多隔一层，全部集中在 `~/bin/`；Ubuntu 默认 `.profile` 里 `~/bin` 和
  `~/.local/bin` 都进 PATH 且 `~/bin` 优先）→ `~/.config/wsl2win/links.conf`（仅兼容保留）
- 换新项目就是加一行配置，不用重写脚本
- 改过脚本要自验：`wsl2win --selftest`（临时目录里跑建链/幂等/写穿透）
- ⚠️ **脚本本身必须保持 LF**。用 Windows 侧编辑器改会存成 CRLF，
  shebang 直接失效（`bad interpreter: /usr/bin/env bash^M`）。
  配置表沾上 CRLF 反倒没事 —— awk 的 `[[:space:]]` 会把行尾 `\r` 一起吃掉（实测）
- ⚠️ **别信 `ln -s` 的退出码**：MSYS 这类环境会静默降级成复制/空目录却返回 0。
  脚本已加防线：建完读回来断言 `-L` + `readlink` 一致，不对就**回滚改名**
- 为什么值得封成脚本而不是一行命令：**先 mv 备份再建链、失败要能回滚、建完要验证** ——
  这三步手工做很容易漏掉中间那步

## skill 目录命名

必须匹配 `^[a-z0-9]+(-[a-z0-9]+)*$` —— **小写字母、数字、单连字符**。
**禁止**大写字母、下划线、`@`、`.`、连续连字符。opencode 会强制校验，不符**静默加载失败**（不报错，最难查）。

## 几个 AI 客户端的 skills 目录

| 客户端 | skills 目录 | 认 `~/.agents/skills` 公共位 |
|---|---|---|
| WorkBuddy | `~/.workbuddy/skills` | ❌ |
| ZCode | `~/.agents/skills`（公共位），同时也扫 `~/.zcode/skills` | ✅ 唯一认的 |
| opencode | `~/.config/opencode/skills` | ❌（npm 全局装） |
| 豆包工作 | `~/DoubaoWork/skills` | ❌ |
| QClaw | `~/.qclaw/skills` | ❌（但 `openclaw.json` 有 `skills.load.extraDirs` 和 per-agent 白名单） |

统一入口在 `~/.skills`，路由与挂载规则见 `local-skills-hub`。
**各 agent 的记忆、内置技能、专家分别存哪**，见 `local-memory-map`（那才是讲"位置"的地方）。

## 主机名匹配要注意大小写

Windows 主机名（`%COMPUTERNAME%`）**统一大写返回**，但字符串比较是区分大小写的。
凡是用主机名做目录名匹配的地方，**必须用大小写不敏感的比较**，否则 `WGC-WORK1-PX` 匹不上 `wgc-work1-px`：

```powershell
$hostName -ieq $dirName      # 用 -ieq / -contains 的大小写不敏感变体
[StringComparer]::OrdinalIgnoreCase  # .NET 侧同理
```

## WorkBuddy 的 skill 与 expert 机制 → 见 local-memory-map

WorkBuddy 的 skill/expert 存储位置、从哪个目录加载（`.skill-list-cache.json` 判据）、
`plugins/` 各子目录职责、专家包结构 —— **全部移到 `local-memory-map`**。
本 skill 只管"换台 Windows 机器也成立"的约定（路径格式、junction、命名正则、主机名大小写），
WorkBuddy 是**单一产品**的机制，不属于 Windows 通用范畴。

## 本机/机器专属信息放哪

`store/machine/<主机名>/` 每个目录一个 SKILL.md，只记那台机器的事实。
`scripts/link.ps1` 只把**本机主机名匹配**的那个挂给 agent，别的机器的不会被挂上来。
所以在这类 skill 里可以放心写死磁盘路径、机型、网络实测结果 —— 它不会跑到别的机器上去。
