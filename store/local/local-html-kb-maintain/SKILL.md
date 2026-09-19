---
name: local-html-kb-maintain
description: 维护单文件 HTML 装修知识库（如装修知识大全.html，数千行、内嵌 CSS/JS/base64 图片、章节 section id=cXX、折叠块 details/summary、callout 提醒块）的全套操作。四个场景：①增量接入——评审用户粘贴的内容→精简→写入对应章节；②插入新章节并整体重编号（目录/导航/href/data-ch 联动）；③批量结构重构与全文体检；④推荐表批量加列/填值（关键词启发式）。触发：把这段加进 html、插入新章节、重编号、章节搬家、批量改折叠块、推荐表加预算加列、排版错乱、知识库体检。
version: v0.4
---

> **改本 skill 时要守的**：
> 1. 只放**方法**，不放会变的状态（章节顺序、各类计数、体积 → 写文档同目录的 `_文档实况.md`）
> 2. 不写日期、不写 changelog、不写第一人称复盘
> 3. 改完跑 `pwsh ~/.skills/scripts/audit.ps1`
>
> 这几条**不因为本 skill 还是 `v0.x` 就可以违反**——「完善中」说的是改之前不用问用户，不是内容可以随便写。

# 单文件 HTML 知识库维护

适用于 `装修知识大全.html` 这类单文件知识库：内嵌 CSS/JS/base64 图片、章节为
`<section class="chapter" id="cXX">`、
折叠块为 `<details class="item-fold|sec-fold|point-group|vc-details|fig-gallery">` + `<summary>`、
提醒块为 `<div class="callout warn|tip|info|rec-box|err">` + `<div class="ctitle">`、
推荐表为 `<table class="ctable rec-tbl">`。

> **推荐表的「核验」列已删**，末列现为 `预算（参考）`；残留 `class="rv"` 是历史遗留，新增表别再套。

> **动手前先看文档同目录的 `_文档实况.md`** —— 章节顺序、各类计数、体积这些**会变**的状态放在那儿，
> 不写进本 skill（skill 只放方法，不放快照）。改完文档记得回去更新它。

**四个场景，先判断用户要干什么**：

| 场景 | 信号 |
|---|---|
| ① 增量接入 | 用户分批粘贴内容，要求「评审 + 精简 + 放进对应章节」 |
| ② 插入新章节 | 概念独立成章、新增章节导致后续 cXX 全部后移 |
| ③ 批量结构重构 | 章节搬家/对调、批量增删折叠块、批量改标题、修排版错乱、全文体检 |
| ④ 推荐表批量编辑 | 给每章推荐表统一加列（预算/价格）、按行填值 |

**所有场景的公共纪律**（先读这五条）：

1. **改前备份**：`cp 文件.html 文件.备份-YYYYMMDD-HHMMSS.html`；备份文件永远不要被脚本自身覆盖。
2. **用 Python 脚本改，不用 Edit 工具做大块插入**：内容长时易出错且难回滚。
3. **每步 assert 唯一性**：`assert html.count(anchor) == 1`；批量计数与预期不符就报错，绝不静默通过。
   `str.replace` 不匹配时**静默无操作**（曾因 `<li>` 间 6 空格缩进漏改一整轮）。
4. **改后回读校验**：`assert new in html` 或对比 count 前后差值。
5. **收尾跑校验三件套**（见文末）。

## 可用脚本（优先跑，别手工重做）

详细参数用 `--help` 看，这里只记"什么时候该跑它"：

| 脚本 | 什么时候跑 |
|---|---|
| `scripts/probe_kb.py` | **动手前** —— 结构速探：章节 id→行号、details/callout 计数、表格数、new-tag 风格 |
| `scripts/scan_kb.py` | 改完收尾、排查"排版错乱" —— 8 类结构问题一次体检 |
| `scripts/check_rec_tbl.py` | 推荐表批量改完 —— 计数核对（表头 / 该列单元格 vs 数据行 / 章节注释） |
| `scripts/insert_chapter.py` | 要插章时 —— 在指定章后插入并整体重编号（**先 `--dry-run` 看**，它会自动备份、防重跑） |

路径可用 bash 的 `/c/...`，脚本自己转。
## 场景一：增量接入（评审 → 精简 → 写入）

### 工作流

1. **摸清结构**（首次）：跑 `python scripts/probe_kb.py <html>` —— 一次给出章节 id→行号、callout 变体、new-tag 风格、表格数。
2. **检索去重**（每批必做）：`grep -c '<关键词>'` 看内容是否已存在；
   已存在则新章节做深度展开 + 旧条目加交叉引用徽章，不重复堆砌。
3. **联网核实关键数据**：只核实影响结论的硬数据（国标号、性能分级、壁厚、功耗、价格区间、平台能力），
   纯经验描述不核实。来源分流：官方标准/厂商文档 → 直接采用；多个独立测评一致 → 采用；
   营销文/单一实测 → 文中标注「厂商标称」「第三方实测，仅作趋势参考」；无源对比数字（"强 N 倍"）→ 删或改定性。
4. **评审并列问题清单**（用户习惯的格式）：
   `✅ 判定正确予以保留（含核实依据）` / `⚠️ 发现问题已修正（N 处，表格：原文问题/处理）` /
   `🔴 关键遗漏已补充` / `✂️ 已删除（重复粘贴、看图笔记、对话式追问）`。
   重点排查：自相矛盾、口径不统一、类别不一致、单位混乱（W vs W/天）、无来源数字、AI 助手残留追问。
5. **写入**（Python + 唯一锚点）：

```python
import io
P = r'绝对路径'
s = io.open(P, encoding='utf-8').read()
anchor = '<唯一锚点字符串>'   # 插某节前 → 用该节 <h3 class="sub">xxx 开头；追加章末 → 用下一章 <section id="cXX"
assert s.count(anchor) == 1, s.count(anchor)
s = s.replace(anchor, BLOCK + anchor, 1)
io.open(P, 'w', encoding='utf-8').write(s)
```

6. **校验**：正则栈校验标签闭合（跳过 void 元素），要求 `unclosed: [] errors: 0`；
   再核对章节边界（`grep -n 'id="c15"\|id="c16"'`）确认没泄漏到下一章。
7. **更新工作区记忆**：本批归属章节 + 新增小节清单；**核实过的硬数据结论（下批复用不用重搜）**；修正的问题；验证结果。

### 坑位

- **重复粘贴**：用户常把同一段贴两遍，写入前先通读去重。
- **AI 助手残留**：原文末尾常有「你家现在是在装修还是…？」这类对话式追问，必须剔除。
- **看图笔记**：「先看图…盯这两个细节」是观感描述不是知识条目，只提炼结论。
- **美元口径**：外文换算的美元金额改人民币并注明估算依据。
- 文件含 base64 内嵌图时体积涨得快，每批记录体积变化。

---

## 场景二：插入新章节并重编号

### 工作流

1. **先与用户确认编号方案**：
   - 方案 A：整体后移（插为 cN，原 cN–cM 变 cN+1–cM+1）
   - 方案 B：逻辑位置插入但保持原编号（追加为 cM+1）
2. **备份**（公共纪律 1）。
3. **Python 脚本执行**（可用 `scripts/add_water_chapter_renumber.py` 作参考实现）：
   - `old_id → new_id` 映射覆盖：`<section class="chapter" id="cXX">`、`data-ch="cXX"`、`href="#cXX"`
   - 更新可见文本中的 `cXX` 引用（跳过 `<script>`/`<style>`/标签属性）
   - `<a href="#cXX">` 链接文本与 href 目标对齐
   - 在正确位置插入新章 `<section class="chapter" id="cN">`
   - 修正所有 `<h2>XX 标题</h2>` 与 section id 数字一致
   - 从原位置删除被抽出的卡片（如有）
   - 更新顶部导航、侧边目录、对应 part 副标题、静态章节统计
4. **校验**：标签平衡 / 章节顺序唯一 / 失效锚点 / `node --check` JS 语法。
5. **更新工作区记忆**：需求、要点、校验结果、脚本路径、备份文件名。

### 坑位

- 文本引用正则 `\bc(0?\d{1,2})\b` 会匹配 `c6`/`c06`/`c25`；替换后保持 `cN` 无前导零风格。
- 新章内容用户未提供时，可基于原卡片搭骨架（系统链路、分类子项、预留/选购提示），不硬编未验证数据。
- **章节 id 重排用占位符法两级替换**，避免 `c12→c05` 与 `c05→c06` 级联错乱。
- 提取章节块须含 `<section>…</section>` 外壳，只取内层会丢 section 标签。

---

## 场景三：批量结构重构与全文体检

### 九步流水线（顺序不可省）

1. 备份（公共纪律 1）。
2. **打印原文 repr 再替换**：`print(repr(html[i:i+200]))`。匹配不上 90% 是换行/缩进/全角字符；
   `h3` 闭合常是 `\n</h3>`（换行在闭合标签**前**）。
3. 每步 assert（公共纪律 3）。
4. 替换后回读（公共纪律 4）。
5. **校验三件套**（见文末）。
6. **结构专项扫描**（章节搬动/新增后必做）：空 callout、空 ul/ol、`<summary>` 内混入块级内容、
   `</summary>` 后重复标题、断链与章号不一致。正则见下。
7. **新增表格必须带 `<colgroup>` 列宽**，否则浏览器自动布局把长文本列压成一字一行。
8. **小节插在折叠块「之前」时，锚点取 `<details>` 标签本身**，绝不能取 summary 内文本
   （曾把整节插进 `<summary>`，被 `display:flex` 压成竖排）。
9. **向某章新增内容前先 grep 该章现有卡片**，同名词合并而非并存
   （「骑马抽」曾同时存在于表格行和卡片，且口径打架）。

### 常用校验正则（临时查一下用）

成批检查请跑 `scripts/scan_kb.py`（8 类一次跑完）。下面几条留着手工抽查单点问题时用：

```python
# 空 callout
re.findall(r'<div class="callout [a-z-]+">\s*<div class="ctitle">[^<]+</div>\s*</div>', html)
# summary 内混入块级内容（排版错乱真因之一）
[m for m in re.finditer(r'<summary[^>]*>(.*?)</summary>', html, re.S)
   if any(t in m.group(1) for t in ['<table', '<p class="lead"', 'class="callout"', '<ul>'])]
# 断链
titles = {m.group(1) for m in re.finditer(r'<section class="chapter" id="(c\d+)">', html)}
[m.group(1) for m in re.finditer(r'href="#(c\d+)"', html) if m.group(1) not in titles]
```

### 折叠块结构标准

```html
<details class="sec-fold">
<summary><h3 class="sub">标题 <span class="new-tag">副标</span></h3></summary>
<div class="sec-body"> …内容… </div>
</details>
```

禁止「纯文本 `<summary>标题</summary>` + 正文重复同标题 `<h3 class="sub">`」的旧式结构（c24/c25 曾有 12 处）。
改计数时正则要带 `📖` 等 emoji，且替换后必须校验 `summary class` 未被吞掉。

---

## 场景四：推荐表批量加列 / 填值

### 目标表判定（不要误伤对比表）

满足任一即目标：① class 含 `ctable rec-tbl`；② 表头文本含 `推荐型号`（覆盖 class 仅为 `ctable` 的表）。
排除：「材料价/对比」表（class 仅 `ctable`、无推荐型号，本身已有单价，勿加列）。

### 核心规则

1. **插列保留闭合标签**：`re.sub(r'(</th>)\s*</tr>', r'\1<th>新列</th></tr>', hr)`、
   `re.sub(r'(</td>)\s*</tr>', r'\1<td class="x">值</td></tr>', row)`。
   绝不能整体替换 `</td></tr>`，否则吞掉末列 `</td>`，新列和最后一列合并。
2. **关键词匹配只用第一列（材料/品类名）**，不用整行 —— 「选用说明」列常提及多种材料，
   整行匹配会误命中（`防水涂料` 含「涂料」→误判乳胶漆；`淋浴隔断` 含「验收」→误判验收项）。
3. **防关键词碰撞**（具体品类名优先于宽泛词；品牌名不做触发词；宽泛词加负向预查）：

| 裸词会误命中 | 改用 |
|---|---|
| `砖` → 瓷砖胶 | `红砖\|砌块\|烧结普通砖\|砖块` |
| `博世`/`西门子` → 洗碗机 | 只留 `洗碗机`（去掉品牌名） |
| `激光` → 测距仪/水平仪 | `测距仪\|水平仪` |
| `涂料` → 乳胶漆 | `乳胶漆\|墙漆`（去掉 `涂料`） |
| `网线` → 全屋WiFi（无网线老房） | `网线(?!老房)` |
| `面板` → 饰面板 | `面板系列`（具体词） |
| `冰箱` → 冰箱内嵌（嵌入插座） | `冰箱(?!内嵌)` |

### 执行与校验

- `re.finditer(r'<table\b[^>]*>.*?</table>', s, re.S)` 取所有表；表头末列后插 `<th>`、每行末列后插 `<td>`。
- 重建文件用「按位置升序拼接 + 每章首个目标表前插注释」，避免索引错位。
- 价格格式：`¥下限–上限/单位`（如 `¥800–2500/米（台面）`、`—（验收项，无材料费）`）。
- 章节级汇总（「本章预算参考（100㎡）：约 X–Y 万元」）按章节字典插到该章首个目标表前。
- **流程纪律**：所有改动（含 CSS 宽度/单元格样式/横向滚动）要么一次性写进脚本跑一次，
  要么最后一次性重跑数据脚本再单独补 CSS，**中途不要 cp 覆盖**。
- 验证清单：预算表头 `<th>预算（参考）</th>` 数量 == 目标表数；`class="rbudget">` 数量 == 数据行总数；
  「本章预算参考」注释数 == 有推荐表的章节数；对比表不含「预算（参考）」。
- 人工抽查：验收类行应为 `—`、价格类行不应为 `—`、无明显错配（瓷砖行显示红砖价）。

---


- **成批核对跑** `python scripts/check_rec_tbl.py <html> --header "预算（参考）"` —— 自动比对表头数、该列单元格数 vs 数据行数、章节注释数 vs 有推荐表的章节数。
## 共用：校验三件套

> **结构问题先跑 `scripts/scan_kb.py`**（8 类一次跑完）；下面三件套是内容/JS 层的检查。


1. `python _figs/validate_html.py` —— 标签平衡 / 章节顺序唯一 / 内部锚点 / JS 语法
2. `python _figs/audit_counts.py` —— 折叠块「声明条数 vs 实际卡片数」（HTMLParser 计数）
3. `node C:\Users\<用户>\.workbuddy\binaries\node\workspace\jsdom_probe.js` —— 真实加载整页捕获 `window.onerror`
   （**必须用 Windows 反斜杠路径**；`/c/...` 含中文会编码损坏报 `SyntaxError`）

## 共用：排版标准（写内容时必须遵守）

判断「用卡片还是用正文」的硬规则：

| 情况 | 用什么 |
|---|---|
| **≥2 个并列的同类名词概念**（字典式速查） | 概念卡片：`item-fold` 折叠块，每条 1–3 句纯定义 |
| **单个复杂概念**（因果、流程、深入讲解） | `h3.sub` 小标题 + 段落正文 |
| **同一组并列概念** | 必须全组同形式，禁止一半卡片一半文字 |
| **只有 1 条概念的折叠块** | 不允许单独存在 → 转成 `h3.sub`+段落，或并入相邻同组卡片 |
| 对比 / 参数 | 表格（必须带 `<colgroup>` 列宽） |
| 有顺序的步骤 / 清单 | `ol.step-list`，不要塞进 callout |
| 警告 / 推荐强调 | callout |

例外：该折叠块所属**系列本身全是折叠块且形式统一**时（如 c14 瓦工验收「一~八」检查项、c02 visual-card 系列），单条也可保留。

**callout 类目定语义，图标可带语义化变体，但不得矛盾**：
`warn`+⚠️（必须避免的错误）· `tip`+💡（技巧/推荐）· `info`+ℹ️（补充说明/清单/索引）· `rec-box`（型号品牌推荐专用）· `err`（硬性禁止，全书仅 1 处）。
⚠️ `warn` 配 💡/✅、`tip` 配 ⚠️ 属矛盾；callout 要点若已抽入正文 `step-list`，不得再保留重复 callout。

## 共用：样式词汇表（写入时必须沿用）

| 用途 | 写法 |
|---|---|
| 小节标题 | `<h3 class="sub">标题 <span class="new-tag">标签</span></h3>` |
| 表格 | `<div class="table-wrap"><table class="ctable">…</table></div>` |
| 推荐表表头 | 主流（20/28）：`材料（按空间）｜推荐品牌/型号｜规格｜选用说明｜预算（参考）`；简版：`型号/系列｜适用与说明｜预算（参考）` |
| 推荐表列 class | `class="rn"`(名称/说明) `class="rb"`(品牌) `class="rs"`(规格) `class="rv"`(历史遗留·新增表停用) |
| 提示框 | `<div class="callout warn\|info\|tip\|rec-box"><div class="ctitle">图标 标题</div><p>…</p></div>` |
| 徽章 | `<span class="badge ok\|warn\|err\|info">✅ 推荐</span>` |
| 数据存疑注脚 | `<p class="rec-note">⚠️ 上表为第三方单一实测…</p>` |

## 共用：Python 环境坑

- `re.search(pat, html, pos)` 第三参是 flags 不是 pos → 抛 ValueError，用 `html.find(pat, pos)`。
- `match_tag_pair` 里源码写 `rf"<{tag}\\\\b"` 会变字面 `\\\\b` 匹配不到嵌套 `<div>`，源码须写单反斜杠 `\\b`。
- 章节对调的断言应为 `s1 < e1 <= s2 < e2`，写成 `s2 < e1` 会误判。
- agent-browser 在本机 daemon 起不来（SIGTERM），超时不要恋战，改用 jsdom 探针。
- **本机已验证的绝对路径**（脚本里写死，别用 `python` / `node` 裸命令）：
  Python `C:\Users\cgw06\.workbuddy\binaries\python\versions\3.13.12\python.exe`；
  Node `C:\Users\cgw06\.workbuddy\binaries\node\versions\22.22.2-3\node.exe`；
  jsdom 探针 `C:\Users\cgw06\.workbuddy\binaries\node\workspace\jsdom_probe.js`。
- **TOC / 悬浮按钮脚本必须独占一个 `<script>`**：全文共 3 块 script，目录生成（`cleanTitle`）与折叠开合状态机在同一块内，
  任一依赖报错就是整块 `ReferenceError`，症状是「目录点不开 / 悬浮按钮无反应 / 整页交互全失效」。
  改任何 JS 后必须跑 jsdom 探针确认 `window.onerror` 为 0。
- **本 skill 是 `~/.skills/store/local/local-html-kb-maintain` 的软链接**，改它就等于改实体，不需要复制或重挂载。
  当前 `v0.x`（完善中）可直接增删；只有升到 `v1.0` 才需要用户点头。
