# 记忆与技能路径速查

> 由 `SKILL.md` 按需引用，**不进 Agent 上下文**。执行第一步盘点或判断"这条知识能不能跨 Agent 带走"时才读。

## 各平台记忆位置

| 平台 | 记忆位置 | 项目内规则文件 |
|---|---|---|
| **ZCode（当前）** | 无自动加载的记忆目录（本机实测 `~/.zcode/` 下无 `MEMORY.md` / `memory/`）；跨会话知识写指令文件 `AGENTS.md` | 用户级 `~/.zcode/AGENTS.md`，工作区 `<repo>/AGENTS.md`（两级都在时用户级先注入，工作区可收窄覆盖） |
| **WorkBuddy（当前）** | `~/.workbuddy/MEMORY.md`（全局）<br>`<工作区>/.workbuddy/memory/`（项目级，含每日日志） | `CLAUDE.md` / `AGENTS.md` |
| Claude Code | `~/.claude/projects/<编码项目路径>/memory/` + `MEMORY.md` 索引 | 项目根 `CLAUDE.md`（可层级嵌套），全局 `~/.claude/CLAUDE.md` |
| OpenAI Codex | 无独立记忆机制，全写 `AGENTS.md` | 项目根 `AGENTS.md`，全局 `~/.codex/AGENTS.md` 或 `$CODEX_HOME/AGENTS.md` |
| OpenCode | 无独立记忆目录 | `.opencode/`；也会扫 `.claude/` 和 `.codex/` |
| OpenClaw | 无独立记忆机制，跨会话信息放项目根 markdown | 项目根 `CLAUDE.md` / 等价文件 |

**关键结论**：上面每一行左侧的记忆位置，**各平台互不相通**。换 Agent 时唯一能带走的，是表格最右列——项目目录里的 markdown。

**本机现状**：`~/.workbuddy`（WorkBuddy）与 `~/.zcode`（ZCode）两套主目录并存，记忆与技能互不相通；读这份文件的是 ZCode，技能要装进 `~/.zcode/skills/` 它才发现得到。

## 各平台技能目录

| 平台 | Skills 目录 |
|---|---|
| **ZCode（当前）** | `~/.zcode/skills/<name>/SKILL.md`（用户级）<br>工作区 `.zcode/skills/`（从当前目录向上到项目根，每级都算，深者优先）<br>`~/.agents/skills/`、工作区 `.agents/skills/` 也会扫（同级内 `.zcode` 先于 `.agents`）<br>启用的插件技能优先级最低；同名技能按上述顺序只加载第一个 |
| **WorkBuddy（当前）** | `~/.workbuddy/skills/<name>/SKILL.md` |
| Claude Code | `~/.claude/skills/<name>/SKILL.md` |
| OpenAI Codex | `~/.codex/skills/<name>/SKILL.md` 或项目内 `.codex/skills/` |
| OpenCode | `~/.config/opencode/skills/`、`.claude/skills/`、`.codex/skills/` 都会扫 |
| OpenClaw | `~/.openclaw/skills/`（用户级）、`.openclaw/skills/`（项目级）、workspace `skills/` |

**停用某个技能**：把 `SKILL.md` 改名为 `SKILL.md.disabled` 即可——发现机制按文件名精确匹配 `SKILL.md`，改名后不再被发现。改回来即恢复（需新会话生效）。ZCode 还支持配置级停用：在 `~/.zcode/cli/config.json`（或工作区 `.zcode/config.json`）按绝对路径设 `enable: false`。

**会话快照**：ZCode 的技能清单在会话启动时生成，会话中途新增 / 停用 / 恢复技能都不生效，要新开会话。

## 补充

- Codex 还会看 `TEAM_GUIDE.md` / `.agents.md`（fallback 文件名）
- Codex 的 `AGENTS.override.md` 若存在，会覆盖同目录的 `AGENTS.md`
- Claude Code 记忆文件用 YAML frontmatter：`name`、`description`、`type`（user / feedback / project / reference）
- 若当前 Agent 没有独立记忆系统，跳过"记忆"那一层，把功夫全放在项目根 markdown、README、docs/ 上——记忆是锦上添花，文档才是最低保障
