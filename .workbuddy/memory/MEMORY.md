# qoder 自动跑 skills 更新（2026-10-22 立）

- **用户定位**：qoder 是 skills 仓库更新的执行 agent —— 在 qoder 里说「skills 更新」等意图即自动跑同步流程，不用再找人（WorkBuddy）代劳。
- **实现**：提示词资产在 `store/local/local-skills-hub/SKILL.md`「实例：让 qoder 自动跑 skills 更新」节（v0.18 起），全文自包含，落地到各机 `~/.qoder/AGENTS.md`（Qoder CLI 用户级静态记忆，官方出处 docs.qoder.com/zh/cli/memory；CN 版 `~/.qoder-cn/AGENTS.md`）。
- **双保险**：local-skills-hub 的 description 已强化「skills 更新/同步技能库/拉远端」触发词（v0.18）；AGENTS.md 常驻注入保证 100% 触发。
- **家那台已装 qoder 国际版**，提示词在家那台落地即可。
- **2026-10-27 订正**：公司电脑（WGC-WORK1-PX）也已装 qoder —— `~/.qoder` 存在，`link.ps1` 按 core/media/cloud + machine 画像挂了 8 个技能。本机 `~/.qoder/AGENTS.md` 已落地；家那台的落地情况以其本机记录为准。

# WSL 内 opencode 的 skills 挂载（2026-11-03 立）

- **方案：两级链接**。WSL `~/.config/opencode/skills` 软链 → Windows `_active/opencode/`（junction 视图×13）→ store 实体。不能直链 store：opencode 只扫 skills/<name>/SKILL.md 一层（官方 docs 确认，不递归）。
- **软链用现成设施**：WSL `~/bin/wsl2win` + `links.conf`，条目 `oc-skills` 已加；用户在 WSL 跑 `wsl2win oc-skills` 即生效（wsl.exe 被沙箱黑名单拦，我无法代建 Linux 软链；UNC 也建不了）。
- **视图刷新（2026-11-05 起自动化）**：link.ps1 视图模式自动维护 —— routing.json 的 opencode 条目写 `view_dir=_active/opencode`，跑 link.ps1 即按画像建/摘/校 junction（当前 14 个），新增 skill 不用再手工刷视图；WSL 侧软链始终不用动。
- **没装 WSL 的电脑**：links.conf 在 WSL 的 home（不在仓库），不同步；视图目录被 gitignore，也不同步。那边只有 routing.json 的 opencode 画像会到，但 link.ps1 视图模式照样建视图（无害空目录），装 opencode 后自建软链即可。
- **穿透验证只能靠 WSL 内部**：WSL 软链在 `\\wsl.localhost\` 下不可见（9P 不解析），Windows 侧代验不了。
