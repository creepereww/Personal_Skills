# qoder 自动跑 skills 更新（2026-10-22 立）

- **用户定位**：qoder 是 skills 仓库更新的执行 agent —— 在 qoder 里说「skills 更新」等意图即自动跑同步流程，不用再找人（WorkBuddy）代劳。
- **实现**：提示词资产在 `store/local/local-skills-hub/SKILL.md`「实例：让 qoder 自动跑 skills 更新」节（v0.18 起），全文自包含，落地到各机 `~/.qoder/AGENTS.md`（Qoder CLI 用户级静态记忆，官方出处 docs.qoder.com/zh/cli/memory；CN 版 `~/.qoder-cn/AGENTS.md`）。
- **双保险**：local-skills-hub 的 description 已强化「skills 更新/同步技能库/拉远端」触发词（v0.18）；AGENTS.md 常驻注入保证 100% 触发。
- **家那台已装 qoder 国际版**，提示词在家那台落地即可；本机（WGC-WORK1-PX）没装 qoder，不建空目录。
