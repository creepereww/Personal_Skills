# Skills Hub 装机 / 同步 · 傻瓜式手册

> 照着一步步做就行。每行命令都能直接复制粘贴。
> 命令前有 `>` 的是要你执行的。

---

## ⚠️ 动手前：先看你打开的是哪个终端

**这一步弄错，后面所有命令都会失败。** 命令里的 `~` 表示"用户主目录"，但**只有 bash 和 PowerShell 认它，cmd 不认**。

| 你看到的提示符 | 这是什么 | `~` 能用吗 |
|---|---|---|
| `PS C:\Users\xxx>` | **PowerShell** | ✅ 能用 |
| `cgw06@MACHINE MINGW64 ~` | **Git Bash** | ✅ 能用 |
| `C:\Users\xxx>` 或 `D:\xxx>` | **cmd（命令提示符）** | ❌ **不能用** |

**看到 `cmd` 的样子（纯盘符路径 + `>`），请立刻关掉**，改用下面任一种：

- **Win + X** → 选「终端」或「Windows PowerShell」
- 或开始菜单搜 **PowerShell**
- 或打开 PortableGit 目录，双击 **`git-bash.exe`**（⚠️ 不要选 `git-cmd.exe`，那是 cmd 环境，同样不认 `~`）

> 三个终端的区别：`git-bash.exe` 和 PowerShell 都能跑本手册的命令；
> `git-cmd.exe` 其实是套了 Git 环境的 cmd，`~` 依然不认——它和 `cmd.exe` 是一类的。

---

## 第 0 步：你需要准备的东西（一次性）

- [ ] 一个**私有 Git 仓库**地址（GitHub 私有仓库 / GitLab / Gitee 都行）
- [ ] 该仓库的**访问凭证**：
  - HTTPS 方式：用户名 + Personal Access Token（推荐，最省事）
  - SSH 方式：配好 SSH key
- [ ] 装了 **Git**（下面有判断方法）

> 建议：GitHub 新建仓库时选 **Private**，不要勾选任何初始化选项（不要 README / .gitignore），要一个完全空的仓库。

---

## 第 1 步：判断电脑上有没有 Git

在**上一步确认过的那种终端**里执行（本手册默认用 PowerShell）：

```
git --version
```

- 显示 `git version x.x.x` → 有 Git，**跳到第 3 步**
- 显示红字报错 / 找不到命令 → 没 Git，**继续第 2 步**

---

## 第 2 步：安装 Git（没有 Git 才做）

下载安装：**https://git-scm.com/download/win**

一路「下一步」即可，全部默认选项不用改。装完**关掉 PowerShell 重新打开**，再执行：

```
git --version
```

看到版本号就 OK 了。

---

## 第 3 步：在「老电脑」上首次上传

（就是现在已经配好的这台机器）

> ⚠️ **如果 push 时报 `Connection was aborted` / `Failed to connect` / 卡在网页登录**，
> 说明你的网络到 `github.com:443` 不通（国内常见）。**别在 HTTPS 上耗**，
> 直接跳到文末「连不上 GitHub 怎么办」，改走 SSH 通道。

**3.1** 打开 PowerShell，逐行执行（把 `<你的仓库地址>` 换成真实地址）：

```
cd ~/.skills
git remote add origin <你的仓库地址>
git remote -v
```

成功标志：`git remote -v` 打印出两行带你仓库地址的内容。

**3.2** 上传：

```
git push -u origin master
```

- 如果提示输入账号密码：**用户名**填你的，**密码**填 Personal Access Token（不是登录密码！）
- 成功标志：出现 `branch 'master' set up to track 'origin/master'`

> 如果本地分支叫 `main` 而不是 `master`，先执行 `git branch -M main`，然后 `git push -u origin main`。

**3.3** 确认上传成功：

```
git remote show origin
```

或去网页上刷新仓库页面，能看到 `README.md`、`routing.json`、`store/` 等文件。

---

## 第 4 步：在「新电脑」上拉取

**4.1** 按第 1、2 步确认 Git 已装。

**4.2** 克隆仓库到固定位置 `~/.skills`（**路径不要改**，脚本里是按这个写的）：

```
cd ~
git clone <你的仓库地址> .skills
```

> 如果提示 `.skills` 已存在 → 说明以前克隆过，改成执行：`cd ~/.skills; git pull`

**4.3** 确认拉下来了：

```
cd ~/.skills
ls
```

应该看到：`README.md` `registry.json` `routing.json` `store` `scripts`

---

## 第 5 步：把 skill 挂给各个 agent（关键一步）

**5.1** 确认 PowerShell 版本，需要 **PowerShell 7**：

```
$PSVersionTable.PSVersion
```

显示 `7.x.x` → 继续。显示 `5.1.x` → 装 PowerShell 7（https://aka.ms/powershell-release?tag=stable），装完重开终端。

**5.2** 执行挂载：

```
pwsh ~/.skills/scripts/link.ps1
```

成功标志：每个 agent 一行 `DONE`，类似这样：

```
entities: 5 (fork:1 local:4)
DONE     workbuddy  created=5 rebuilt=0 unchanged=0 pruned=0 conflict=0
DONE     zcode      created=5 rebuilt=0 unchanged=0 pruned=0 conflict=0
...
```

**5.3** 逐个 agent 验证：打开每个客户端的新会话，问它：

> "你能看到 local-skills-hub 这个 skill 吗？"

能看到就说明这台机器通了。

> ⚠️ **conflict 不等于失败**：输出里有 `CONFLICT` 说明那个 agent 的目录下已经有个同名的**真实文件夹**（比如客户端预置的 skill）。脚本不会动它，保留原样。你要接管的话，手动把那个文件夹改名或删掉，再跑一次 `link.ps1`。

---

## 第 6 步：日常同步（每次换机器都要做）

### 离开电脑 A 之前（保存改动）

```
pwsh ~/.skills/scripts/sync.ps1 -Commit "改了什么"
```

这一步会：提交本机改动 → 拉取远端 → 推送 → 顺手刷新挂载。

### 到了电脑 B（拉取）

```
pwsh ~/.skills/scripts/sync.ps1
```

> commit message 写中文没问题。某些终端里会显示成乱码，但存进仓库是对的，别慌。

### 只改了 skill 内容、不需要同步

```
pwsh ~/.skills/scripts/link.ps1
```

---

## 第 7 步：验证清单（一台新机器配完，逐项打勾）

- [ ] `git --version` 有输出
- [ ] `$PSVersionTable.PSVersion` 是 7.x
- [ ] `~/.skills` 目录存在，里面有 `README.md`、`store/`、`scripts/`
- [ ] `pwsh ~/.skills/scripts/link.ps1` 执行完没有红色报错
- [ ] WorkBuddy 新会话能看到 `local-skills-hub`
- [ ] ZCode 新会话能看到 `local-skills-hub`
- [ ] opencode 看到（如果装了）
- [ ] 豆包工作看到（如果装了）

---

## 连不上 GitHub 怎么办（实测有效的三条路）

### 先判断你属于哪种

在任一终端（pwsh / git-bash）里跑：

```
ssh -T git@github.com
```

- 回 `Hi <用户名>!` → SSH 已通，直接做「方案 A 的 A6」
- 回 `Permission denied (publickey)` → 网络通、只是公钥没加，从「A1」开始
- 卡住 / `Connection timed out` → SSH 也不通，看方案 B 或 C

### 方案 A：改用 SSH（推荐，一次配好永久免密）

**A1. 看有没有现成 key** — `ls ~/.ssh`，有 `id_rsa` + `id_rsa.pub`（或 ed25519 系列）就跳过 A2。

**A2. 没有就生成**（一路回车，密码留空）— `ssh-keygen -t ed25519 -C "你的邮箱"`

**A3. 公钥进剪贴板** — `cat ~/.ssh/id_rsa.pub | clip`
（key 若是 ed25519，文件名换成 `id_ed25519.pub`。`clip` 是 Windows 自带的复制到剪贴板，省得手选）

**A4. 添加到 GitHub** — 打开 https://github.com/settings/ssh/new → Title 随便写 → Key 框 Ctrl+V → Add SSH key

**A5. 让 GitHub 走能通的通道**（可选，防 22 端口被封）
文件 `~/.ssh/config`，**注意没有 `.txt` 后缀**（写成 `config.txt` 的话 ssh 根本不读，这是真踩过的坑）。内容：

```
Host github.com
User git
Hostname ssh.github.com
PreferredAuthentications publickey
IdentityFile ~/.ssh/id_rsa
Port 443
```

**A6. 换地址并推送**：

```
cd ~/.skills
git remote set-url origin git@github.com:<用户名>/<仓库名>.git
git remote -v
git push -u origin master
```

成功标志：`* [new branch]  master -> master` + `branch 'master' set up to track`。

### 方案 B：HTTPS + 代理（有代理才用）

先确认代理端口活着（`26561` 换成你自己的）：`curl -x http://127.0.0.1:26561 https://github.com`

能返回内容，再给 git 配上（两行都要）：

```
git config --global http.proxy http://127.0.0.1:26561
git config --global https.proxy http://127.0.0.1:26561
```

不用了就取消：`git config --global --unset http.proxy`（https.proxy 同理）。

### 方案 C：换成 Gitee（最省事）

`gitee.com` 国内直连可用，不需要任何代理。建个私有仓库，把 remote 换掉即可，本手册命令全不变。

### 为什么会这样

实测本机网络：

| 目标 | 结果 |
|---|---|
| `github.com:443`（HTTPS 默认走这条） | ❌ 超时 |
| `github.com:22`（SSH 默认走这条） | ✅ 通 |
| `ssh.github.com:443`（SSH 备用通道） | ✅ 通 |
| `gitee.com:443` | ✅ 通 |

注意第 1 行和第 3 行**同样是 443 端口**，一个不通一个通 —— 所以不是"443 被封"，
而是 **`github.com` 解析到的那个 IP 被阻断**。SSH 有别的可达入口，因此能绕过去。

另外要澄清：**HTTPS 并不必然要求网页登录**。卡住的那个网页是 Git Credential Manager 的 OAuth 流程，
它自己也要联网所以跟着失败；HTTPS 本来可以直接填 Personal Access Token，不走网页。

## 常见问题

**Q：`cd ~/.skills` 报错「系统找不到指定的路径」**
A：**你在 cmd 里**（提示符长这样：`C:\Users\xxx>` 或 `D:\xxx>`）。`~` 是 bash / PowerShell 的写法，cmd 不认。
关掉它，改用 PowerShell 或 `git-bash.exe`（见开头那张表）。它们俩 `~` 都能用。

如果你**必须**留在 cmd（不推荐），得写全路径且加 `/d` 才能跨盘符：
```
cd /d C:\Users\你的用户名\.skills
```

**Q：`pwsh` 不是命令**
A：PowerShell 7 没装或没加 PATH。装完重开终端，或直接用全路径：
`"C:\Program Files\PowerShell\7\pwsh.exe" C:\Users\你的用户名\.skills\scripts\link.ps1`

**Q：push 时被拒绝（rejected）**
A：远端有你本地没有的提交。先执行 `git pull --rebase` 再 `git push`。

**Q：某个 agent 看不到 skill**
A：按顺序查这四条：
1. 跑一次 `pwsh ~/.skills/scripts/link.ps1`，看有没有给这个 agent 建联接
2. 目录名和 `SKILL.md` 里的 `name` 是否**逐字符一致**
3. 名字是不是只含小写字母数字和单个连字符（不能有 `@` 大写 下划线）
4. 文件是不是叫 `SKILL.md`（全大写），有没有被改成 `SKILL.md.disabled`

**Q：想临时停用一个 skill**
A：把 `SKILL.md` 改名为 `SKILL.md.disabled`，跑一次 `link.ps1` 即可恢复/生效。
