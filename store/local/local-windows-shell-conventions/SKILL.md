---
name: local-windows-shell-conventions
description: Windows 上跨机器通用的 shell 与链接约定 —— MSYS 程序的 /c/ 路径 vs Windows 原生程序的 C:/ 路径该用哪种、junction 目录联接的正确建删方式、Git for Windows 把 junction 当普通目录的坑、skill 目录命名正则、各 AI 客户端的 skills 目录、主机名大小写匹配。写 shell 脚本、建软链接、排查路径报错或 skill 没生效时看这里。机器专属信息（机型、客户端装在哪个盘、网络情况）见 machine 档；WorkBuddy 的 skill/专家机制见 local-memory-map。
version: v0.5
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
- 建：`New-Item -ItemType Junction -Path <link> -Target <dir>`
- **删必须用 `[System.IO.Directory]::Delete($link, $false)`** —— `Remove-Item -Recurse` 会连带删掉**源目录内容**
- Git for Windows 会把 junction 当普通目录，**挂载目录必须写进 `.gitignore`**，否则仓库里会出现重复内容
- 判断是不是联接：`($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0`
- PowerShell 7 有 `.LinkTarget` / `.LinkType` 可读目标；PowerShell 5.1 没有，得用 `cmd /c dir /AL`

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
