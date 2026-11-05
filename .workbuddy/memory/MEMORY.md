# qoder 自动跑 skills 更新（2026-10-22 立）

- **用户定位**：qoder 是 skills 仓库更新的执行 agent —— 在 qoder 里说「skills 更新」等意图即自动跑同步流程，不用再找人（WorkBuddy）代劳。
- **实现**：提示词资产在 `store/local/local-skills-hub/SKILL.md`「实例：让 qoder 自动跑 skills 更新」节（v0.18 起），全文自包含，落地到各机 `~/.qoder/AGENTS.md`（Qoder CLI 用户级静态记忆，官方出处 docs.qoder.com/zh/cli/memory；CN 版 `~/.qoder-cn/AGENTS.md`）。
- **双保险**：local-skills-hub 的 description 已强化「skills 更新/同步技能库/拉远端」触发词（v0.18）；AGENTS.md 常驻注入保证 100% 触发。
- **家那台已装 qoder 国际版**，提示词在家那台落地即可。
- **2026-10-27 订正**：公司电脑（WGC-WORK1-PX）也已装 qoder —— `~/.qoder` 存在，`link.ps1` 按 core/media/cloud + machine 画像挂了 8 个技能。本机 `~/.qoder/AGENTS.md` 已落地；家那台的落地情况以其本机记录为准。

# WSL 内 opencode 的 skills 挂载（2026-11-03 立）

- **方案（2026-11-05 改为 v2 配置直挂）**：本机 opencode 是 **v2（2.0.27）**，`~/.config/opencode/opencode.jsonc` 写 `skills: ["/mnt/c/Users/cgw06/.skills/_active/opencode"]` —— **不用软链**。旧结论「只扫一层」是 v1 规则；v2 支持嵌套最深六层 + `skills` 配置数组。视图 `_active/opencode` 仍由 link.ps1 维护（作用变为画像过滤），新增 skill 只跑 link.ps1、不用碰 opencode 配置。
- **v1 备选**：WSL `~/.config/opencode/skills` 软链 → 视图（两种方式别同时用，会重复注册）。
- **软链设施（v1 备选）**：WSL `~/bin/wsl2win` + `links.conf`，条目 `oc-skills` 已有；`wsl2win oc-skills` 即建软链（wsl.exe 被沙箱黑名单拦，我无法代建 Linux 软链；UNC 也建不了）。v2 配置直挂后这一步可跳过。
- **wsl2win / links.conf 不进仓库（2026-11-05 定）**：它们跨项目个人设施（links.conf 还混着 PXD-YS56 等无关路径），搬进仓库会带本机绝对路径、换机即失效。仓库里的**通用自举接法**在 `local-skills-hub`「视图模式」节（v0.19）：`cd /mnt/c/Users/<你>/.skills && ln -s "$PWD/_active/opencode" ~/.config/opencode/skills`（先跑 link.ps1 建视图；`$PWD` 免硬编码用户名）。
- **视图刷新（2026-11-05 起自动化）**：link.ps1 视图模式自动维护 —— routing.json 的 opencode 条目写 `view_dir=_active/opencode`，跑 link.ps1 即按画像建/摘/校 junction，新增 skill 不用再手工刷视图；WSL 侧配置不用动。
- **画像只留编程必需（2026-11-05 用户指定：这台 opencode 主要用来编程）**：link.ps1 新增 `clients.<name>.exclude_skills`（client 级单技能排除，优先级仅次于 skills 段）。opencode 现状 = `groups:["core","eda"]` 减 7 个排除项 → **只挂 4 个**：`local-script-first`、`local-plan-first-superpowers`（干活方式）、`local-sinocmcu-8bit-codegen`（网表→MCU 代码）、`easyeda-agent-connector`（读网表）。排掉：skills-hub / memory-map / windows-shell-conventions（仓库与环境元知识）、design-review / board-build / bom-purchase（画板采购非写代码）、machine 档。
- **没装 WSL 的电脑**：links.conf 在 WSL 的 home（不在仓库），不同步；视图目录被 gitignore，也不同步。那边只有 routing.json 的 opencode 画像会到，但 link.ps1 视图模式照样建视图（无害空目录），装 opencode 后自建软链即可。
- **穿透验证只能靠 WSL 内部**：WSL 软链在 `\\wsl.localhost\` 下不可见（9P 不解析），Windows 侧代验不了。

# Personal_Dotfiles 仓库（2026-11-05 立）

- **位置**：本地 `C:/Users/cgw06/.dotfiles`，远端 `creepereww/Personal_Dotfiles`（private，master，`90254b7`）。
- **为什么单开**：wsl2win 是跨项目工具、links.conf 全是本机绝对路径 —— 混进 skills 仓库会跑到别的机器给出错误信息。
- **WSL 侧**：`wsl/bin/wsl2win`（13KB 工具：真身留 Windows、WSL 建软链）、`wsl/bin/fix-perm.sh`、`wsl/install.sh`（~/bin 改软链到仓库 + links.conf 迁到 `~/.config/wsl2win/`）、`wsl/links.conf.example`（脱敏模板）。
- **Windows 侧（2026-11-05 加，用户问「Windows 需要管 dotfiles 吗」引出）**：只收三样手写资产 ——
  `win/vscode/settings.json`（554 行）、`win/vscode/keybindings.json`（89 行，含自制续行符宏）、
  `win/gitconfig.template`（`{{EDITOR}}` 由脚本探测替换）+ `extensions.txt`（51 个扩展，`cgw06.*` 两个是自制、市场装不回）。
  `win/install.ps1`：默认「仓库→本机」（备份 `*.bak-<时间戳>` + SHA256 校验），`-Push`「本机→仓库」，`-Extensions` 重导清单。
  **不收**：注册表类（Everything/Quicker/Watt）、ssh key/token、浏览器数据、各 agent 配置（归本仓库）。
- **Windows dotfiles 三个坑（已写进 dotfiles README）**：① 本机 `$env:HOME=D:\AppData\Roaming\SPB_Data` 而 `USERPROFILE=C:\Users\cgw06`，git 读 HOME、VS Code 读 `%APPDATA%`；`$env:HOME` 还带双反斜杠，Join-Path 前必须折叠。② 单文件不能 junction、跨盘 hardlink 不行、symlink 要管理员 → 只能「仓库当源+脚本复制」，不做自动同步。③ 路径写死用户名/安装位置，换机即废。
- **关键设计**：wsl2win 用 `readlink -f` 定位自身找 links.conf，软链后看到的是仓库目录（仓库不放本机路径）→ 配置必须走 `~/.config/wsl2win/links.conf` 兜底。`.gitattributes` 对 `.sh`、`win/` 下 json/template/ps1、`*.md`、`*.txt` 全锁 LF（本机 autocrlf=true，否则检出 CRLF → WSL bad interpreter / 整文件 diff）。
- **本机 WSL 侧尚未装**：wsl.exe 被沙箱黑名单拦，install.sh 需用户自己在 WSL 跑；跑之前一切照旧。Windows 侧已实跑验证（备份在 `*.bak-20261105-120515`）。
