# ~/.skills —— 全局 Skill 仓库（单一实体，多 agent 共用）

## 结构

```
store/local/   纯本地 skill（Git 跟踪）
store/fork/    从 GitHub 派生的 skill（含 .upstream 溯源）
store/cache/   远程 skill 缓存（不进 Git，用完不删）
routing.json   各 agent 挂载点
registry.json  远程 skill 清单
proposals/     待审批提案（批准后删除）
scripts/       link / sync
```

## 日常

| 想做什么 | 命令 |
|---|---|
| 改动 skill 后刷新联接 | `scripts\link.ps1` |
| 换机器/同步 | `scripts\sync.ps1` |
| 本机改完要提交 | `scripts\sync.ps1 -Commit "描述"` |
| 新增/删除 skill 后 | 放进 `store\local\`，再跑 `link.ps1` |

## 铁律

1. **模型不得直接编辑 `store/` 下任何文件。** 发现问题只写 `proposals/<skill>.md`，由人批准后才改。
2. **skill 正文不写** changelog、日期、踩坑复盘、案例回溯、为"可能用得上"的兜底章节。
3. 版本号 `vX.Y`：局部补充 Y+1，结构重写 X+1。只改 frontmatter 一行。
4. 派生的 `.upstream` 里 `reason` ≤3 行 / 200 字。
5. `local-<slug>` 是纯本地，`local-<slug>-<reposlug>` 是派生。名字须匹配 `^[a-z0-9]+(-[a-z0-9]+)*$`，且 frontmatter `name` 与目录名一致。

## 挂载现状

| agent | 目录 | 方式 |
|---|---|---|
| WorkBuddy | `~/.workbuddy/skills` | junction |
| ZCode | `~/.agents/skills`（公共位） | junction |
| opencode | `~/.config/opencode/skills` | junction |
| 豆包工作 | `~/DoubaoWork/skills` | junction |
| QClaw | `~/.qclaw/skills` | extraDirs 配置（**当前冻结**） |

## 注意

- 联接是 **junction**，非管理员可建；删联接必须用 `[IO.Directory]::Delete($link,$false)`，`Remove-Item -Recurse` 会删掉源内容。
- Git for Windows 会把 junction 当普通目录，所以 `_active/`、`store/cache/`、`proposals/` 都在 `.gitignore` 里。
