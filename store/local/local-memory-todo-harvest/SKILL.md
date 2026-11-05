---
name: local-memory-todo-harvest
description: 扫描全部 agent（WorkBuddy / Qoder / Claude Code / Codex / Gemini / Windsurf / Trae / OpenClaw / QClaw / ZCode）记忆文件里散落的待办——待办章节 / checkbox / 行内待办句，连出处一起同步进「生活工作台·记忆待办」云表；正式看板是生活工作台里的「AI项目管理」模块（按来源 agent + 项目筛选、拖动排优先级、项目别名、纳入副业，没有勾选）。纯标准库、不联网、不回写原始记忆；扫描在任何 agent 里都能跑，只有写云表那一步需要 WorkBuddy 通道（别的 agent 用 --json 交接清单）。
version: v0.7
---

# 记忆待办归集 (memory-todo-harvest)

## 触发场景
用户说类似下面这些话时启用：
- 「把散落在记忆文件里的待办归集一下」
- 「汇总一下各项目记忆里的待办 / 下一步」
- 「更新一下记忆待办」
- 「记忆里有哪些还没做的待办」

## 它做什么
Agent 每天在各项目的记忆日志里写工作记录，里面散落着「待办 / 下一步 / 未完成」，写完就沉底、没人回头看。
本技能把它们扫出来，推进「生活工作台·记忆待办」云表；**正式看板是生活工作台里的「AI项目管理」模块**
（按项目分列，可按**来源 agent** 筛选，拖动卡片排优先级，「项目设置」里改别名 / 勾「纳入副业」；
没有勾选——源日志里 `- [x]` 划掉的事，下次同步自动进「已完成」）。勾了「纳入副业」的项目会同时出现在副业 →「AI 赋能项目」页。

## 数据源：内置全 agent 记忆表（`AGENT_SOURCES`）
路径按 `local-memory-map` 记的官方默认位置写死在 `harvest.py` 里，根目录 = `~`；**目录不存在就跳过**，
所以在一台没装某个客户端的机器上跑既不报错、也不会扫出别人的东西。

| agent | kind | 相对 HOME 的模式 |
|---|---|---|
| WorkBuddy | project / personal | `<根>/*/.workbuddy/memory/*.md`、`<根>/.workbuddy/user-*/*.md`（根见「默认扫描根」，走老逻辑不进这张表） |
| Qoder | project / personal | `.qoder/projects/*/memory/*.md` / `.qoder/memory/*.md` |
| Claude Code | project / personal | `.claude/projects/*/memory/*.md` / `.claude/agent-memory/*/MEMORY.md` |
| Codex | personal | `.codex/memories/*.md` |
| Gemini | personal | `.gemini/GEMINI.md` |
| Windsurf | project | `.codeium/windsurf/memories/*/*.md` |
| Trae | personal | `.trae-cn/memory/*.md`、`.trae/memory/*.md` |
| OpenClaw / QClaw | personal | `.openclaw/workspace/memory/*.md`、`.qclaw/workspace/memory/*.md` |
| ZCode | project | `.zcode/projects/*/memory/*.md` |

扫不到的：豆包（记忆在云端向量库，本机没有明文）、opencode（SQLite，不可直读）。
**WSL 里的 agent**（本机 opencode 就跑在 WSL）：`~` 是 Linux 家目录，`scan_homes()` 会额外把 `/mnt/c/Users/<用户>`
也纳入候选家目录，Windows 侧各 agent 的记忆同样扫得到；relpath 相对各自的家目录算，所以同一条记忆在哪边扫到都是同一个待办 id。
要加新源就在 `AGENT_SOURCES` 里添一行 `{agent, kind, pattern}`，别在扫描函数里写特例。

## 标准流程（每次跑技能）
1. **扫描预览**：`python harvest.py --scan`（分组标题带 `[agent]`；`--agent Qoder` 只扫一个来源）。
2. **同步上云**：`python <工作台项目>/workbench_build/memory_todo_sync.py`（`--dry-run` 只看差异）。
   **必须在 WorkBuddy 客户端里跑**——写云表走它的 agent 通道；在别的 agent 里跑会明确报
   `code=E_AUTH_FAILED` 并提示改用第 3 步，不会静默半同步。
   - 按「待办ID」diff：新增 / 内容变更 / 源里消失的删除；删除有保护——该项目在本次扫描里仍然存在才删它下面消失的项（D 盘没挂上之类整目录缺失不误删）。
   - **排序、别名、纳入副业是用户数据，同步永不覆盖**（看板上拖动/项目设置产生的）；新增行会继承同项目已有的「纳入副业」。
   - 新增行排序 = 当前最大 + 1（追加到列尾）。
   - 首次运行会自动给云表补建 `agent` 列（`get-database` 查结构 + `add-field` 建文本列），不用手工去表里加。
3. **非 WorkBuddy 环境的交接**：`python harvest.py --json 待办.json` 出结构化清单（每条带 `agent` 字段），要上云就把活交给 WorkBuddy 跑第 2 步。
4. 向用户汇报：扫描 N 条（按 agent 分布）→ 新增/更新/删除各多少。

## 识别规则（只认信号，不猜）
1. **待办语义章节**：日志里 `## 待办` / `## 下一步` / `## 未完成` 等标题下的列表项。
2. **checkbox**：`- [ ] xxx` 为待办；`- [x] xxx` 记为已完成（同步进「已完成」列）。
3. **行内待办句**：`**待办**：①…②…③…`，编号自动拆成多条。
4. **笔记句过滤**：章节条目里以 `关键发现：/踩坑：/判定：/结论：/备注：/说明：/注意：` 等开头的是结论不是待办，自动跳过。

## 项目显示名（不用日期目录名 / 不用 slug）
扫描侧解析优先级：
1. **手工别名** `PROJECT_ALIASES`（代码内，推断自工作区内容，用户可随时改）：网盘整理 / 网盘补传 / Skills 管理 / 闲鱼。
2. **WorkBuddy 项目**：读 `<项目>/.workbuddy/memory/MEMORY.md` 的第一个 `#` 标题，兼容「项目长期笔记：human-atlas（D:\…）」「MEMORY.md · 项目长期笔记（日常集·生活工作台）」「MEMORY.md - Claw 渠道本地记忆（…）」三种写法；命中通用措辞（项目长期笔记/本地记忆/仅此/勿…）的候选丢弃；取不到才目录名兜底（老工作区目录名是时间戳，形如 `YYYY-MM-DD-HH-MM-SS`，所以必须走前两级）。
3. **其余 agent**：个人级归到「`<agent> 记忆`」（WorkBuddy 的个人级仍叫「个人记忆」——改名会让云表已有行的待办ID 变脸）；
   项目级取路径里 `memory/` 前那一段，Qoder/Claude 的 slug（形如 `C--Users-x-Desktop-proj`）会剥掉盘符与 `users/home/data/projects/workbuddy…` 这类噪声段，只留有意义的末段。
4. **用户备注别名最高优先**：在生活工作台「AI项目管理」的「项目设置」面板改，写云表「别名」列，扫描永不覆盖。
   注意该面板按**自动名**成组：不同 agent 恰好同名会被当成一个项目、共用别名与纳入副业（实际命名基本撞不上；撞了就去 `PROJECT_ALIASES` 给其中一个改名）。

同一项目的镜像工作区（C 盘旧位置 + D 盘主目录）会合并成一组，按「**同 agent** + 同项目 + 同日志文件 + 同行号 + 同文本」去重，出处保留 D 盘新位置。
待办 id = 项目|文件|文本（**不含行号、不含 agent**，日志里增删行不会让待办变脸丢排序）：agent 不进 id 是因为来源文件的相对路径
（`.qoder/…` vs `xxx/.workbuddy/…`）天然不撞，而改 id 公式等于全表重建（云表排序/别名全丢）。

## 本地预览页（harvest.py）
只读预览：近期未完成（按项目分组 + 进度）/ 历史遗留 · 超 14 天 / 已完成，每条带 signal 标签、**来源 agent 标签**、日期、文件:行号。没有勾选、没有别名面板——那些都在云表看板上。

```bash
python harvest.py                           # 127.0.0.1 起只读预览服务
python harvest.py --scan                    # 只打印汇总（带 agent 分布）
python harvest.py --agent Qoder --scan      # 只扫一个来源
python harvest.py --build 看板.html          # 导出静态看板
python harvest.py --json 待办.json           # 结构化清单，给不能上云的环境交接
python harvest.py --root D:/other-workspace  # 额外扫描 WorkBuddy 风格的根
```

默认扫描根（D 盘主项目在最前，与 C 盘镜像去重时保留新位置出处）：`D:\DATA\AI_DATA\LongTermPro\本地工作台构建`、`~/WorkBuddy`、`~`（个人记忆）。

## 云表结构（生活工作台·记忆待办，9JwdAJ3DtgQe8g4DhalGev）
待办ID / 待办内容 / 自动名 / 别名 / **agent** / 信号(select) / 章节 / 日期 / 来源文件 / 行号 / 已完成 / 排序 / 扫描时间 / 示例数据 / 纳入副业。
同步脚本只写内容字段（含 agent）+ 扫描时间；排序/别名/纳入副业只在新增时初始化，之后永不覆盖。
看板侧只在 `agent` 有值时回写它——云表还没这一列时拖动排序也不会写坏。

## 依赖
- 仅 Python 标准库（`http.server` / `webbrowser` / `json` / `re` / `glob` 等）。
- 不联网、不读取任何外部服务，扫描数据全程不出本机；只有 memory_todo_sync.py 那一步经 agent API 写云表，
  而那步依赖 WorkBuddy 的 `_common.http_request`（脚本自己扫最新的 skill-library 目录，不写死版本号和用户名）。

## 备注
该技能由用户从「记忆归集待办看板」演示页确认的规格本地构建（当时 marketplace 未上架此技能）。
预览服务仅监听 `127.0.0.1`。

### 踩坑记录
- **模板双括号**：HTML 模板曾按 `.format` 习惯写了 `{{`/`}}`，但 `build_html` 用的是 `.replace`——产物 CSS/JS 全坏，看板白屏。模板里一律用单层括号。
- **Content-Length 必须按字节算**：`_send` 里 `len(body)` 是字符数，body 含中文时 UTF-8 字节数更大，浏览器按 Content-Length 截断（curl 不管这套所以发现不了）。必须 `len(body.encode("utf-8"))`。
- **query 接口字段名是驼峰**：`{"databaseId": …}`，不是 `database_id`；返回的是裸值（日期给带 `T00:00:00Z` 时间部分的完整 ISO 串），写入才是 `{date:…}` 包装——比对时要两边都归一。
- **待办 id 别含行号**：否则日志里增删一行，该待办就被当成新项（排序/别名全丢）。同理**别含 agent**——改 id 公式＝云表全表重建。
- **删除要加项目存在性保护**：整目录缺失（D 盘没挂上）时不能把它下面的待办全删了。
- JSON payload 注入前把 `</` 转义成 `<\\/`，防文本里的 `</script>` 提前闭合脚本。
- **TDZ**：模块里调用 `registerView()` 必须放在 `const VIEWS` 声明之后，否则整个 IIFE 启动即崩（白屏）。
- **`add-field` 的类型要包在 `config` 里**：`{"property":{"name":"agent","config":{"text":""}}}`，写成 `{"name":…,"type":"text"}` 服务端不认；`get-database` 的 `properties` 是**列表**不是 map——解析不出任何字段名时要报错退出，不能贸然建列（会建出重复列）。
- **`--json` 单独跑必须 return**：否则顺着走到 `serve()`，进程常驻监听不退出，看着就像卡死。
- **打印别指望 ✓ ▶ 这类字符**：Windows 终端默认 cp936，`UnicodeEncodeError` 会把整轮 `--scan` 崩在第一个分组标题上。`main()` 开头 `sys.stdout.reconfigure(errors="replace")` 兜住，图标换成 GBK 也编得出的 `■` 和 `x`（写文件仍显式 UTF-8，不受影响）。
- **skill-library 路径别写死版本号和用户名**：`5.8.3-wb.xxxx` 这种目录一升级就废。扫 `~/.workbuddy/plugins/cache/*/skill-library/*/` 取最新的、且确实有 `_common.py` 的那个；技能本体优先从 `~/.skills/store/local/…` 取（`~/.workbuddy/skills` 那份是 junction，两处任一能用即可）。
- **看板加一列要三处一起动**：云表列（同步脚本补建）+ 行转换（`rowToMemoryTodo`/`memoryTodoToProps`）+ 筛选条与卡片标签；少一处就是「数据在云上但页面看不见」。
- **`el.hidden` 常常藏不掉东西**：筛选条 `.mt-f` 自带 `display:flex`，会盖掉 UA 的 `[hidden]{display:none}`，必须补 `.mt-f[hidden]{display:none!important}`。判定要真渲染（Playwright `isVisible()`），别读 DOM 属性。
- **多 agent 别只测「文件扫到了」**：本机 Qoder/QClaw 的记忆文件确实在盘上，但一条待办都没有（那些日志没有待办章节也没有 checkbox）——这是真阴性。验证发现能力要用假 HOME 造样例（改 `harvest.HOME` 后再 `scan()`），别拿「0 条」当通过。
