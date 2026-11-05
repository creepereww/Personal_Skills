#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记忆待办归集 (memory-todo-harvest)
=================================
把散落在 WorkBuddy 各项目记忆文件里的「待办」扫出来，按项目分组，
生成一份可在本机勾选、且能追溯出处的待办看板。

设计原则（来自演示规格）：
- 纯标准库，单脚本，不联网，数据不出本机。
- 只认三类显式信号，不猜：
    1) 待办语义章节：日志里「## 待办 / ## 下一步 / ## 未完成」标题下的条目
    2) 未勾选 checkbox：- [ ] xxx（勾过的 - [x] 记为已完成）
    3) 行内待办句：**待办**：①…②…③…（编号自动拆成多条）
- 每条待办都带「出处」：来源日志文件、行号、归属项目、识别依据。
- 勾选判定存在独立的判定档案（data/judgments.json），与原始记忆文件
  完全解耦，不回写、不污染原始记录。

用法：
    python harvest.py                # 扫描 + 本地起服务 + 打开看板（推荐）
    python harvest.py --scan         # 只扫描并打印汇总，不起服务
    python harvest.py --build HTML   # 导出一份静态 HTML 到指定路径
    python harvest.py --root DIR     # 额外扫描指定根目录下的 .workbuddy/memory
"""

import argparse
import glob
import hashlib
import html
import json
import os
import re
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SKILL_DIR, "data")

# 默认扫描的根：WorkBuddy 项目记忆 + 个人记忆 + 生活工作台主项目（2026-10-23 起在 D 盘）
# D 盘主项目放最前：与 C 盘旧工作区是同一项目的镜像，去重时保留新位置的出处
DEFAULT_ROOTS = [
    r"D:\DATA\AI_DATA\LongTermPro\本地工作台构建",
    os.path.join(os.path.expanduser("~"), "WorkBuddy"),
    os.path.expanduser("~"),
]

# 老工作区目录名是时间戳，看不出项目 → 手工别名（推断自工作区内容，用户可改）
PROJECT_ALIASES = {
    "2026-09-09-13-46-43": "网盘整理",
    "2026-09-14-21-51-09": "网盘补传",
    "2026-09-17-22-52-03": "Skills 管理",
    "2026-09-30-01-50-30": "闲鱼",
}
# MEMORY.md 首标题里的通用措辞，命中则不是项目名
_GENERIC_TITLE = ("项目长期笔记", "长期笔记", "本地记忆", "跨项目", "Cross-project", "仅此", "勿", "工作区")


def _name_from_memory_md(projdir):
    """从 <项目>/.workbuddy/memory/MEMORY.md 的首个一级标题提项目名。

    兼容三种写法：
      # MEMORY.md · 项目长期笔记（日常集·生活工作台）   → 取括号内
      # 项目长期笔记：human-atlas（D:\\...\\human-atlas） → 取冒号后、括号前
      # MEMORY.md - Claw 渠道本地记忆（仅此工作区使用…）  → 取首词
    """
    p = os.path.join(projdir, ".workbuddy", "memory", "MEMORY.md")
    if not os.path.isfile(p):
        return ""
    try:
        with open(p, encoding="utf-8") as f:
            first = f.readline().strip()
    except Exception:
        return ""
    m = re.match(r"^#\s+(.*)$", first)
    if not m:
        return ""
    title = re.sub(r"^MEMORY\.md\s*[·\-–—:：]?\s*", "", m.group(1).strip())
    cands = []
    for part in re.split(r"[：:]", title, maxsplit=1):
        part = part.strip()
        if "（" in part:
            before, inside = part.split("（", 1)
            cands.append(before.strip())
            cands.append(inside.rstrip("）").strip())
            head = before.strip().split()
            if head:
                cands.append(head[0])
        elif part:
            cands.append(part)
    for c in cands:
        if not c or len(c) > 24 or "\\" in c or "/" in c:
            continue
        if any(g in c for g in _GENERIC_TITLE):
            continue
        return c
    return ""


def friendly_project(dirname, projdir):
    """项目显示名：手工别名 > MEMORY.md 标题提取 > 目录名。"""
    if dirname in PROJECT_ALIASES:
        return PROJECT_ALIASES[dirname]
    return _name_from_memory_md(projdir) or dirname

# 待办语义章节标题匹配：标题含关键词即算（兼容「云盘待办清单」「下一步动作」等写法）
SECTION_KEYWORDS = re.compile(r"(待办|下一步|未完成|TODO|todo)", re.IGNORECASE)
# 排除技能自身的元信息（避免回扫自己构建日志造成的自指）
SKIP_MARKERS = ("memory-todo-harvest", "记忆待办归集", "记忆归集")

# 行内待办：仅认 **待办** 标签后跟冒号（演示规格：待办：①…②…③…），
# 不认散文里顺带提到的"待办"（如文件名 传完-待办清单.md、章节名"现状/待办"）。
INLINE_TODO = re.compile(r"(?:\*\*)?待办(?:\*\*)?\s*[:：]\s*(.*)$")

# 编号切分：圈码①-⑳㉑… 或 数字后跟 . ) 、 ）
NUM_MARKER = re.compile(r"(?:[⓪-⓿\u2460-\u24ff])|(?:[0-9]+[.、)）])")

# 章节条目里的「笔记句」前缀：这些是结论/发现/踩坑，不是待办（演示规格只收真待办）
NOTE_PREFIXES = (
    "关键发现：", "关键发现:", "踩坑：", "踩坑:", "判定：", "判定:", "结论：", "结论:",
    "备注：", "备注:", "说明：", "说明:", "注意：", "注意:", "发现：", "发现:",
    "重新分档：", "重新分档:", "架构是", "编码用了", "未做任何删除",
)


def _is_note(text):
    return text.startswith(NOTE_PREFIXES)


def _date_of(relpath):
    """从日志路径推日期：优先文件名 YYYY-MM-DD.md，回退工作区目录名前缀（MEMORY.md 等）。"""
    m = re.match(r"(\d{4}-\d{2}-\d{2})", os.path.basename(relpath))
    if m:
        return m.group(1)
    m = re.match(r"(\d{4}-\d{2}-\d{2})", relpath.split("/")[0])
    return m.group(1) if m else ""


def _is_skip(text):
    """是否应跳过：技能自身元信息（避免回扫自己的构建日志造成自指）。"""
    return any(m in text for m in SKIP_MARKERS)


def clean(text):
    """去掉常见 markdown 噪音，保留可读文字。"""
    t = text.strip()
    t = re.sub(r"\*\*(.*?)\*\*", r"\1", t)       # 粗体
    t = re.sub(r"`(.*?)`", r"\1", t)             # 行内代码
    t = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", t)    # 链接
    t = re.sub(r"<.*?>", "", t)                  #  html 标签
    return t.strip(" ：:　")


def split_numbered(content):
    """把 '①买菜②洗衣服③写作业' 这类按编号拆成多条。"""
    content = content.strip()
    if not content:
        return []
    matches = list(NUM_MARKER.finditer(content))
    if not matches:
        return [content] if content else []
    items = []
    for idx, mt in enumerate(matches):
        start = mt.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(content)
        chunk = content[start:end].strip()
        if chunk:
            items.append(chunk)
    return items


def make_id(project, relpath, line, text):
    # 不含行号：日志里增删行不会让待办「变脸」（排序/别名按 id 保留）；
    # 同一文件里同文本重复只算一条（去重时也会合并）
    raw = f"{project}|{relpath}|{text}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def extract_todos_from_file(path, project, relroot):
    todos = []
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return todos

    # 整篇跳过「关于本技能自身」的文档（避免回扫自己的构建/说明日志造成自指）
    if any("memory-todo-harvest" in ln for ln in lines):
        return todos

    relpath = os.path.relpath(path, relroot).replace(os.sep, "/")
    in_todo_section = False
    section_name = None

    for i, raw in enumerate(lines, start=1):
        line = raw.rstrip("\n")
        if not line.strip():
            continue

        # 1) 章节标题
        hm = re.match(r"^(#{1,6})\s+(.*)$", line)
        if hm:
            title = hm.group(2).strip()
            if SECTION_KEYWORDS.search(title) and not _is_skip(title):
                in_todo_section = True
                section_name = title
            else:
                in_todo_section = False
                section_name = None
            continue

        # 2) checkbox
        cb = re.match(r"^\s*[-*]\s*\[([ xX])\]\s+(.*)$", line)
        if cb:
            done = cb.group(1).lower() == "x"
            text = clean(cb.group(2))
            if text:
                todos.append(_mk(project, relpath, i, text, "checkbox", done, section_name))
            continue

        # 3) 行内待办句（仅 **待办**： 形式，且需带编号或单条短语）
        im = INLINE_TODO.search(line)
        if im and not _is_skip(line):
            content = im.group(1).strip()
            if content:
                for piece in split_numbered(content):
                    text = clean(piece)
                    # 丢弃纯标点/省略号等无实质内容的碎片（如示例语法 ①…②…③… ）
                    if text and re.search(r"[一-鿿A-Za-z0-9]", text):
                        todos.append(_mk(project, relpath, i, text, "inline", False, None))
            continue

        # 4) 待办章节下的列表项（过滤结论/发现类笔记句）
        if in_todo_section:
            li = re.match(r"^\s*[-*]\s+(.*)$", line)
            if li:
                text = clean(li.group(1))
                if text and not _is_note(text):
                    todos.append(_mk(project, relpath, i, text, "section", False, section_name))
                continue
            li2 = re.match(r"^\s*\d+[.)]\s+(.*)$", line)
            if li2:
                text = clean(li2.group(1))
                if text and not _is_note(text):
                    todos.append(_mk(project, relpath, i, text, "section", False, section_name))

    return todos


def _mk(project, relpath, line, text, signal, done, section):
    return {
        "id": make_id(project, relpath, line, text),
        "project": project,
        "file": relpath,
        "line": line,
        "date": _date_of(relpath),
        "text": text,
        "signal": signal,
        "section": section or "",
        "source_done": done,
    }


def discover_memory_files(extra_roots):
    roots = list(DEFAULT_ROOTS) + list(extra_roots)
    files = []
    seen = set()
    for root in roots:
        # 项目记忆：<root>/*/.workbuddy/memory/*.md
        for p in glob.glob(os.path.join(root, "*", ".workbuddy", "memory", "*.md")):
            ap = os.path.abspath(p)
            if ap not in seen:
                seen.add(ap)
                files.append((ap, "project", root))
        # 个人记忆：<root>/.workbuddy/user-*/MEMORY.md 及日志
        for p in glob.glob(os.path.join(root, ".workbuddy", "user-*", "*.md")):
            ap = os.path.abspath(p)
            if ap not in seen:
                seen.add(ap)
                files.append((ap, "personal", root))
    return files


def project_name(path, kind, root):
    if kind == "personal":
        return "个人记忆"
    # project 模式：取 <root>/<PROJECT>/.workbuddy/memory 里的 PROJECT
    parts = path.split(os.sep)
    # 找到 .workbuddy 前的那一段
    for idx, part in enumerate(parts):
        if part == ".workbuddy" and idx > 0:
            return parts[idx - 1]
    return os.path.basename(os.path.dirname(os.path.dirname(path)))


def scan(extra_roots):
    files = discover_memory_files(extra_roots)
    todos = []
    for path, kind, root in files:
        if kind == "personal":
            proj = project_name(path, kind, root)
        else:
            dirname = project_name(path, kind, root)
            # path = <root>/<项目>/.workbuddy/memory/x.md → 项目根要剥三层
            proj = friendly_project(dirname, os.path.dirname(os.path.dirname(os.path.dirname(path))))
        todos.extend(extract_todos_from_file(path, proj, root))
    for t in todos:
        t["done"] = t["source_done"]
        t["auto"] = t["project"]
    # 去重：同项目 + 同日志文件名 + 同行号 + 同文本只留一条
    # （同一项目的镜像工作区，如 C 盘旧位置与 D 盘主目录，会扫出重复内容）
    seen = {}
    for t in todos:
        key = (t["project"], os.path.basename(t["file"]), t["line"], t["text"])
        if key not in seen:
            seen[key] = t
    return list(seen.values())


# ---------------------------------------------------------------------------
# 看板 HTML 生成
# ---------------------------------------------------------------------------

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>记忆待办归集看板</title>
<style>
  :root {
    --bg:#f6f7f9; --card:#ffffff; --ink:#1f2329; --muted:#8a9099;
    --line:#e6e8eb; --accent:#2f6fed; --done:#23a06b; --warn:#e8820c;
  }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--ink);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }
  header { padding:20px 24px; background:var(--card); border-bottom:1px solid var(--line); }
  h1 { font-size:18px; margin:0 0 6px; }
  .stat { color:var(--muted); font-size:13px; }
  .stat b { color:var(--ink); }
  .toolbar { padding:12px 24px; display:flex; gap:10px; flex-wrap:wrap; align-items:center; }
  select, button { font:inherit; padding:6px 12px; border:1px solid var(--line);
    border-radius:8px; background:var(--card); color:var(--ink); cursor:pointer; }
  button.primary { background:var(--accent); color:#fff; border-color:var(--accent); }
  main { padding:0 24px 40px; max-width:860px; }
  .project { margin-top:20px; }
  .project h2 { font-size:15px; margin:0 0 4px; display:flex; align-items:baseline; gap:8px; flex-wrap:wrap; }
  .project h2 .cnt { font-size:12px; color:var(--muted); font-weight:normal; }
  .project h2 .prog { font-size:12px; color:var(--done); font-weight:600; }
  .bar { height:6px; border-radius:99px; background:var(--line); overflow:hidden; margin:0 0 10px; }
  .bar i { display:block; height:100%; background:linear-gradient(90deg,#3fbf8f,#23a06b); border-radius:99px; }
  .item { display:flex; gap:12px; align-items:flex-start; background:var(--card);
    border:1px solid var(--line); border-radius:10px; padding:10px 14px; margin-bottom:8px; }
  .item.done { opacity:.55; }
  .item.done .txt-main { text-decoration:line-through; }
  .box { width:18px; height:18px; margin-top:2px; flex:0 0 auto; cursor:pointer; accent-color:var(--done); }
  .txt { flex:1; font-size:14px; line-height:1.5; min-width:0; }
  .meta { margin-top:4px; font-size:12px; color:var(--muted); display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
  .tag { background:#eef1f5; border-radius:6px; padding:1px 7px; color:#5b6470; }
  .tag.s-checkbox { background:#e7f0ff; color:#2f6fed; }
  .tag.s-section { background:#eafaf1; color:#23a06b; }
  .tag.s-inline { background:#fff3e0; color:#e8820c; }
  .tag.sec { background:#f3ecf7; color:#7d5b75; }
  .tag.proj { background:#eef1f5; color:#5b6470; font-weight:600; }
  .sect-head { margin:26px 0 4px; font-size:15px; font-weight:700; display:flex; align-items:baseline; gap:8px; }
  .sect-head .cnt { font-size:12px; color:var(--muted); font-weight:normal; }
  .sect-head.stale { color:var(--warn); }
  .sect-head.done-sec { color:var(--done); }
  .sub-head { font-size:13px; color:#5b6470; margin:12px 0 6px; display:flex; gap:8px; align-items:baseline; }
  .sub-head .cnt { font-size:11px; color:var(--muted); }
  .empty { color:var(--muted); padding:40px; text-align:center; }
  footer { padding:16px 24px; color:var(--muted); font-size:12px; border-top:1px solid var(--line); }
</style>
</head>
<body>
<header>
  <h1>记忆待办归集看板</h1>
  <div class="stat" id="stat"></div>
</header>
<div class="toolbar">
  <select id="filter"><option value="__all__">全部项目</option></select>
  <button class="primary" onclick="location.reload()">刷新</button>
</div>
<main id="list"></main>
<footer>
  数据仅来自本机 WorkBuddy 记忆文件，纯本地、不联网、只读预览。
  正式看板在生活工作台「记忆待办」模块：由本技能扫描同步进云表，支持拖动排优先级、备注项目别名。
</footer>
<script>
const TODOS = __TODOS__;
const SERVER = __SERVER__;
const STALE_DAYS = 14;
const DAY_MS = 86400000;

function escapeHtml(s){
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function isStale(t){
  return !t.done && !!t.date && (Date.now() - new Date(t.date + 'T00:00:00').getTime()) > STALE_DAYS * DAY_MS;
}
function signalLabel(s){
  return s === 'checkbox' ? 'checkbox' : (s === 'section' ? '章节条目' : '行内待办');
}
function groupBy(list, keyFn){
  const m = {};
  list.forEach(t => { const k = keyFn(t); (m[k] = m[k] || []).push(t); });
  return m;
}
function itemEl(t, showProject){
  const el = document.createElement('div');
  el.className = 'item' + (t.done ? ' done' : '');
  const txt = document.createElement('div'); txt.className = 'txt';
  const main = document.createElement('div'); main.className = 'txt-main';
  main.textContent = t.text; txt.appendChild(main);
  const meta = document.createElement('div'); meta.className = 'meta';
  let html = '<span class="tag s-' + t.signal + '">' + signalLabel(t.signal) + '</span>';
  if (t.section) html += '<span class="tag sec">' + escapeHtml(t.section) + '</span>';
  if (showProject) html += '<span class="tag proj">' + escapeHtml(t.project) + '</span>';
  if (t.date) html += '<span>📅 ' + escapeHtml(t.date) + '</span>';
  html += '<span>📄 ' + escapeHtml(t.file) + ':' + t.line + '</span>';
  meta.innerHTML = html;
  txt.appendChild(meta);
  el.appendChild(txt);
  return el;
}
function progressBlock(name, items){
  const done = items.filter(t => t.done).length;
  const pct = items.length ? Math.round(done / items.length * 100) : 0;
  const h = document.createElement('h2');
  h.innerHTML = escapeHtml(name) +
    ' <span class="cnt">' + items.filter(t => !t.done).length + ' 条待办</span>' +
    ' <span class="prog">' + done + '/' + items.length + ' · ' + pct + '%</span>';
  const bar = document.createElement('div'); bar.className = 'bar';
  bar.innerHTML = '<i style="width:' + pct + '%"></i>';
  return [h, bar];
}
function render(filter){
  const list = document.getElementById('list');
  list.innerHTML = '';
  const scoped = filter === '__all__' ? TODOS : TODOS.filter(t => t.project === filter);
  const open = scoped.filter(t => !t.done);
  const doneItems = scoped.filter(t => t.done);
  const stale = open.filter(isStale);
  const recent = open.filter(t => !isStale(t));

  // ① 各项目：近期未完成（含进度）
  const byProj = groupBy(recent, t => t.project);
  Object.keys(byProj).sort().forEach(p => {
    const sec = document.createElement('div'); sec.className = 'project';
    progressBlock(p, scoped.filter(t => t.project === p)).forEach(el => sec.appendChild(el));
    byProj[p].forEach(t => sec.appendChild(itemEl(t, false)));
    list.appendChild(sec);
  });

  // ② 历史遗留 · 超 14 天未完成
  if (stale.length) {
    const head = document.createElement('div');
    head.className = 'sect-head stale';
    head.innerHTML = '历史遗留 · 超 ' + STALE_DAYS + ' 天未完成 <span class="cnt">' + stale.length + ' 条</span>';
    list.appendChild(head);
    const staleByProj = groupBy(stale, t => t.project);
    Object.keys(staleByProj).sort().forEach(p => {
      const sub = document.createElement('div');
      sub.className = 'sub-head';
      sub.innerHTML = escapeHtml(p) + ' · 遗留 <span class="cnt">' + staleByProj[p].length + ' 条</span>';
      list.appendChild(sub);
      staleByProj[p].forEach(t => list.appendChild(itemEl(t, true)));
    });
  }

  // ③ 已完成
  if (doneItems.length) {
    const head = document.createElement('div');
    head.className = 'sect-head done-sec';
    head.innerHTML = '已完成 <span class="cnt">' + doneItems.length + ' 条</span>';
    list.appendChild(head);
    const doneByProj = groupBy(doneItems, t => t.project);
    Object.keys(doneByProj).sort().forEach(p => {
      const sub = document.createElement('div');
      sub.className = 'sub-head';
      sub.innerHTML = escapeHtml(p) + ' <span class="cnt">' + doneByProj[p].length + ' 条</span>';
      list.appendChild(sub);
      doneByProj[p].forEach(t => list.appendChild(itemEl(t, true)));
    });
  }

  if (!scoped.length) {
    list.innerHTML = '<div class="empty">这个项目下还没有待办信号 🎉</div>';
  }
  document.getElementById('stat').innerHTML =
    '共 <b>' + scoped.length + '</b> 条 · 待处理 <b>' + open.length + '</b>（其中遗留 <b>' + stale.length + '</b>）· 已完成 <b>' + doneItems.length + '</b>';
}
const f = document.getElementById('filter');
[...new Set(TODOS.map(t => t.project))].sort().forEach(p => {
  const o = document.createElement('option'); o.value = p; o.textContent = p; f.appendChild(o);
});
f.onchange = () => render(f.value);
render('__all__');
</script>
</body>
</html>
"""


def build_html(todos, server=True):
    payload = json.dumps(todos, ensure_ascii=False).replace("</", "<\\/")
    return HTML_TEMPLATE.replace("__TODOS__", payload).replace("__SERVER__", "true" if server else "false")


# ---------------------------------------------------------------------------
# 本地服务（仅 127.0.0.1，勾选写回判定档案）
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    extra_roots = []

    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        raw = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        # 每次请求都重新扫描，保证刷新后与磁盘上的记忆文件一致
        todos = scan(self.extra_roots)
        html = build_html(todos, server=True)
        self._send(200, html)

    def log_message(self, *args):
        pass


def free_port():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def serve(todos, extra_roots):
    port = free_port()
    Handler.extra_roots = extra_roots
    httpd = HTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"看板已启动：{url}")
    print("按 Ctrl+C 停止服务。")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        httpd.server_close()


def main():
    ap = argparse.ArgumentParser(description="记忆待办归集 (memory-todo-harvest)")
    ap.add_argument("--scan", action="store_true", help="只扫描并打印汇总")
    ap.add_argument("--build", metavar="HTML", help="导出静态 HTML 到指定路径")
    ap.add_argument("--root", action="append", default=[], help="额外扫描根目录")
    args = ap.parse_args()

    todos = scan(args.root)

    if args.scan:
        by_proj = {}
        for t in todos:
            by_proj.setdefault(t["project"], []).append(t)
        print(f"扫描到 {len(todos)} 条待办，分布在 {len(by_proj)} 个项目：")
        for p in sorted(by_proj):
            print(f"\n▶ {p} （{len(by_proj[p])} 条）")
            for t in by_proj[p]:
                mark = "✓" if t["done"] else " "
                print(f"  [{mark}] {t['text']}   <{t['signal']} | {t['date'] or '无日期'} | {t['file']}:{t['line']}>")
        return

    if args.build:
        with open(args.build, "w", encoding="utf-8") as f:
            f.write(build_html(todos, server=False))
        print(f"已导出静态看板：{args.build}（{len(todos)} 条待办）")
        return

    serve(todos, args.root)


if __name__ == "__main__":
    main()
