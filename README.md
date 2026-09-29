# ~/.skills —— 全局 Skill 仓库（单一实体，多 agent 共用）

## 结构

```
store/local/   跨机器通用的本地 skill（Git 跟踪）
store/fork/    从 GitHub 派生、且做过本地改动的 skill（含 .upstream 溯源）
store/cache/   远程 skill 缓存 / 上游原样快照（不进 Git，用完不删）
store/machine/ 机器专属 skill，一台机器一个目录（按主机名），只挂本机那个
routing.json   各 agent 挂载点 + 安装检测规则 + 临时主机名别名
registry.json  远程 skill 清单（含原样快照的溯源信息）
proposals/     待审批提案（批准后删除）
scripts/       link / sync（_common.ps1 是共用探测函数）
```

**放哪的判断**：换台机器 / 换个 agent 还成立 → `store/local/`；
只对某台机器成立（磁盘路径、机型、网络实测）→ `store/machine/<主机名>/`；
只对某个 agent 成立 → `store/local/` + `routing.json` 的 `skills` 段限制 client；
上游原样快照（不改、直接覆盖更新）→ `store/cache/`。

## 日常

| 想做什么 | 命令 |
|---|---|
| 改动 skill 后刷新联接 | `scripts\link.ps1` |
| 换机器/同步 | `scripts\sync.ps1` |
| 本机改完要提交 | `scripts\sync.ps1 -Commit "描述"` |
| 新增/删除 skill 后 | 放进 `store\local\`，再跑 `link.ps1` |
| 检查 skill 是否合规 | `scripts\audit.ps1` |
| 改完偏好后分发到各 agent | `scripts\sync-preferences.ps1` |
| 拉取远程 skill | `scripts\pull.ps1 -Id <id>` 或 `-All` |
| 看各 agent 装没装 | `scripts\link.ps1 -ListClients` |
| 给没装的 agent 强行挂载 | `scripts\link.ps1 -Force` |

## 铁律

1. **模型不得直接编辑 `store/` 下任何文件。** 发现问题只写 `proposals/<skill>.md`，由人批准后才改。
2. **skill 正文不写** changelog、日期、踩坑复盘、案例回溯、为"可能用得上"的兜底章节。
3. 版本号 `vX.Y`：局部补充 Y+1，结构重写 X+1。只改 frontmatter 一行。
4. 派生的 `.upstream` 里 `reason` ≤3 行 / 200 字。
5. `local-<slug>` 是纯本地，`local-<slug>-<reposlug>` 是派生。名字须匹配 `^[a-z0-9]+(-[a-z0-9]+)*$`，且 frontmatter `name` 与目录名一致。
6. **上游原样快照放 `store/cache/`**，不放 `store/fork/` —— fork 要吃全套本地规范（必须有 `version` 等），
   而原样快照按定义不该有本地改动。放 cache 还有个好处：`audit.ps1` 对 cache 只查
   「有没有 SKILL.md / desc 有没有超 1024」，正是原样快照该受的待遇。
   代价是实体不进 Git，**溯源信息要转录到 `registry.json`**（cache 里的 `.upstream` 会被下次 pull 覆盖）。

## 跨机器适配（不写死本机事实）

脚本不假设「这台机器装了什么、装在哪」，两处都要靠探测：

| 探测对象 | 函数 | 优先级 |
|---|---|---|
| git.exe | `_common.ps1` 的 `Get-GitExe` | `$env:SKILLS_GIT` > PATH > 常见安装位置 |
| agent 装没装 | `_common.ps1` 的 `Test-ClientInstalled` | `routing.json` 的 `detect` > 默认看 skills 目录的父目录 |

- **没装的 agent 不挂、也不给它建目录**（旧行为是 `enabled` 就建，会在干净机器上凭空造空壳目录）。
- `detect` 写法：不写 -> 看父目录；写 `[]` -> 不探测永远视为已装；写路径数组 -> 存在才算；`detect_any: true` -> 任一存在即可。
- 探测结果被上次运行留下的目录污染时（如手工建过空目录），用 `link.ps1 -ListClients` 核对，必要时先清掉残留。

**机器专属信息**（磁盘路径、机型、网络实测）放 `store/machine/<主机名>/`，
`link.ps1` 只挂与 `%COMPUTERNAME%` 匹配（**大小写不敏感**）的那个，所以不会串台。
主机名已改但还没重启时（`%COMPUTERNAME%` 仍是旧名），用 `routing.json` 的 `host_aliases` 临时借道，
**重启后记得删掉那条别名**（`link.ps1` 会提醒）。

## 挂载现状

| agent | 目录 | 方式 |
|---|---|---|
| WorkBuddy | `~/.workbuddy/skills` | junction |
| ZCode | `~/.agents/skills`（公共位） | junction |
| opencode | `~/.config/opencode/skills` | junction |
| 豆包工作 | `~/DoubaoWork/skills` | junction |
| QClaw | `~/.qclaw/skills` | 不纳入（保留它自带的 extraDirs 配置） |

## 注意

- 联接是 **junction**，非管理员可建；删联接必须用 `[IO.Directory]::Delete($link,$false)`，`Remove-Item -Recurse` 会删掉源内容。
- Git for Windows 会把 junction 当普通目录，所以 `_active/`、`store/cache/`、`proposals/` 都在 `.gitignore` 里。
- **别用目录的 mtime 判断它是不是本次新建的** —— 往里写一个文件就会改父目录 mtime，容易把老目录误判成新产物（踩过：`~/.zcode/cli` 是 9/4 的真实数据，差点被当成今天的残留清掉）。
