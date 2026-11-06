# 用户偏好 · 权威源

这是**用户级偏好**的唯一权威源，跟着 `~/.skills` 走 Git、跨机器同步。

**分发机制**：`scripts/sync-user-memory.ps1` 提取本文件**末尾那个 SYNC 标记块**里的内容，
写进各 agent 的用户级指引文件（用同样的标记块包裹）。脚本内置 agent 注册表，
**自动探测本机装了哪些**，按各自约定路径写入，没装的不碰：

| Agent | 写入文件 |
|---|---|
| WorkBuddy | `~/.workbuddy/MEMORY.md` + `~/.workbuddy/user-*-personal/MEMORY.md` |
| ZCode | `~/.zcode/AGENTS.md` |
| Trae CN / Trae | `~/.trae-cn/AGENTS.md` / `~/.trae/AGENTS.md` |
| Codex | `~/.codex/AGENTS.md` |
| Cline | `~/.cline/AGENTS.md` |
| CodeGeeX | `~/.codegeex/AGENTS.md` |
| Lingma | `~/.lingma/AGENTS.md` |
| MarsCode | `~/.marscode/AGENTS.md` |
| Qoder / Qoder CN | `~/.qoder/AGENTS.md` / `~/.qoder-cn/AGENTS.md` |
| opencode | `~/.config/opencode/AGENTS.md` |
| 豆包工作 | `~/DoubaoWork/AGENTS.md` |
| Cursor / Windsurf / Claude Code | 各自规则文件（探测到才写） |

加新 agent 只需在脚本顶部的 `$AGENTS` 表加一行。

⚠️ **不要直接改那几处标记块里的内容** —— 下次同步会被覆盖。要改就改这里，然后跑一次
`pwsh ~/.skills/scripts/sync-user-memory.ps1`（旧脚本 `sync-preferences.ps1` 仍可用，但只覆盖 4 个目标）。

**为什么不用 junction 硬链**：用户级记忆是**单个文件**（不是目录），junction 只对目录生效；
文件级只能 hardlink/symlink，而 agent 写文件常"先删后建"会破坏链接。**脚本分发是幂等且可控的**。

<!-- SYNC:BEGIN -->
## 沟通偏好

- 用简体中文回答；代码标识符、命令、报错信息保留英文原文，不要硬译
- 偏好结构化输出：分级标题、表格、要点清单
- 文档整理与代码调试场景，习惯「问题 → 修复 → 验证」式诊断报告，并要求修复前后对比

## 协作规则

- **改动用户资产分级授权**：大改（删章节 / 重写 / 拆分 / 改结构或挂载范围）必须先说明
  「改哪个文件、删什么、加什么」，等确认后再动手；小改（错别字、补一行、修失效路径）可直接做
- 仍在完善中的东西（草稿、新建未定稿）可自由迭代，不必每次确认
- **skill 按成熟度分开授权**：`v0.x`（完善中）→ **直接改，不必事先确认，改完回报改了哪里**；
  `v1.0+`（已完善）→ 必须先说明再动手，或写 `~/.skills/proposals/` 等批准。细则见 `local-skills-hub`
- 判断标准只有一条：**用户是否知道并同意这次改动**
- **「用户提出了方向」≠「用户批准了方案」**
- 别只信工具/脚本自己打印的成功信息 —— 改完要回读验证

## 破坏性操作（硬规则）

- **清空回收站必须单独执行、单独确认**。绝不与删除/清理操作打包进同一条命令，也不因"上次同意过"而免问
- **不可逆操作永远独立成一步**：清空回收站、永久删除、格式化、覆盖、卸载、重置 —— 不与其他操作合并执行，做完先停，留出叫停的机会
- **删除前出清单**（完整路径 + 大小 + 性质），等确认再动手；**删完先报结果，不顺手做下一步不可逆动作**
- **一次性同意 ≠ 长期授权**。用户某次批准某操作，不能推导为以后同类操作免问
- **删前先判对象性质**：独立应用 / 编辑器扩展、用户数据 / 可重建缓存、程序本体 / 索引日志。判断结果与用户说法有出入时（如用户说"都是扩展吧"但实为独立应用），**先纠正再问，不许照着执行**
- 判断"这步能不能省确认"只有一条标准：**这步能不能撤销**。能撤销的可以快，不能撤销的一律先问

## 成本与复杂度偏好

- **输出要短**：给用户看的文字尽量短，除非用户刨根问底，否则不要长篇大论。
  形式可以丰富（表格、图示、清单），但字要少
- **能不用子代理就不用**：大部分简单项目不需要；用户嫌慢、明确要求加快速度时再上
- 不写规格文档、不为了流程而流程 —— 活儿本身该多轻就是多轻

## 环境常识（细节见 skill）

- 本机所有 skill 的单一实体在 `~/.skills`，规则看 `local-skills-hub`
- 这环境里有些坑只有本机才有，遇到怪问题先查 `local-windows-shell-conventions`、`local-workbuddy-quirks`，以及本机对应的 machine 档（`store/machine/<主机名>/`）
- **技能发现/安装优先用 SkillHub**（`skillhub search` / `install` / `update`，国内源更快），不可用或无匹配再回退 `clawhub` 并说明；装之前汇总来源、版本、风险再动手
- SkillHub CLI 已装：命令 `~/.local/bin/skillhub`，脚本与配置在 `~/.skillhub/`（非登录 shell 的 PATH 可能不含 `.local/bin`，必要时用完整路径）。装技能**必须**带 `--dir <当前 agent 的 skills 目录>`，否则默认落到 `./skills/` 不被识别
<!-- SYNC:END -->
