#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单文件 HTML 知识库：在指定章节后插入新章，并把后续章节整体重编号。

通用版（替换原先写死在「插入 c06 全屋净水」那次任务上的脚本）。

用法:
    python insert_chapter.py <html> --after c05 --title "全屋净水系统" [选项]

常用:
    --emoji 💧               h2 里的图标（可选）
    --body <文件>            新章正文 HTML。不给则只生成带骨架的空章
    --toc-label 全屋净水      侧边目录/顶部导航里的短名（默认取 --title）
    --dry-run                只报告会改什么，不写文件
    --no-backup              跳过自动备份（默认会在同目录生成 .备份-时间戳.html）

它做什么（按顺序）:
    1. 自动备份原文件
    2. 算出重编号映射：--after 之后的所有 cNN 整体 +1（c06→c07 这种，单调递增所以不会级联错乱）
    3. 同步更新 section id（两种属性顺序都认）、data-ch、href="#cNN"、可见文本里的 cNN 引用
       （跳过 <script>/<style>），最后把 <a> 的链接文字与 href 对齐
    4. 插入新章（在重编号后的第一个旧章之前）
    5. 修正所有 <h2> 的序号，使其与所在 section id 一致
    6. 更新静态章节计数
    7. 在侧边目录与顶部导航里插一条

**不处理**：part 副标题（自由文本，位置得人工判断）—— 会提示你手工补。

纪律（见 local-script-first）: 每步都 assert；失败明确报错；退出码恒为 0（信息写在正文）。
"""
import argparse
import io
import re
import shutil
import sys
from datetime import datetime


def norm_path(p):
    """把 MSYS 风格 /c/xxx 转成 Windows 路径（Python 是原生程序，不认 /c/）。"""
    if not p:
        return p
    p = p.strip().strip('"').strip("'")
    m = re.match(r"^/([a-zA-Z])/(.*)$", p)
    return "%s:/%s" % (m.group(1).upper(), m.group(2)) if m else p


def cid(n):
    return "c%02d" % n


# 插入时打在自己插的章上，用来区分"我上次插的"和"本来就有的章节"
MARK = "<!-- inserted-by:insert_chapter.py -->"


def main():
    ap = argparse.ArgumentParser(description="在指定章节后插入新章并整体重编号")
    ap.add_argument("file", help="HTML 文件")
    ap.add_argument("--after", required=True, help="插在这一章之后，如 c05")
    ap.add_argument("--title", required=True, help="新章标题，如 全屋净水系统")
    ap.add_argument("--emoji", default="", help="h2 里的图标，如 💧")
    ap.add_argument("--body", default="", help="新章正文 HTML 文件（不给则生成骨架）")
    ap.add_argument("--toc-label", default="", help="目录/导航里的短名（默认用 --title）")
    ap.add_argument("--dry-run", action="store_true", help="只报告，不写文件")
    ap.add_argument("--no-backup", action="store_true", help="跳过自动备份")
    ap.add_argument("--force", action="store_true", help="检测到重跑迹象也继续（会先备份）")
    a = ap.parse_args()

    path = norm_path(a.file)
    try:
        text = io.open(path, encoding="utf-8").read()
    except FileNotFoundError:
        print("❌ 找不到文件: %s" % path)
        return
    except UnicodeDecodeError as e:
        print("❌ 不是 UTF-8 编码: %s" % e)
        return

    steps = []

    # ── 解析 --after
    m = re.fullmatch(r"c?(\d+)", a.after.strip(), re.I)
    if not m:
        print("❌ --after 要写成 c05 这种形式")
        return
    after_n = int(m.group(1))
    new_n = after_n + 1
    new_id = cid(new_n)

    # ── 防重跑：只有"那个 id 上的章是本脚本上次插的"才算重跑。
    #    插在中间时目标 id 必然已被占用（原来的那章会被重编号），那是正常的，不该拦。
    m_sec = re.search(r'<section\b[^>]*?\bid="%s"' % re.escape(new_id), text)
    if m_sec and MARK in text[m_sec.start():m_sec.start() + 500]:
        print("⚠️ %s 上是本脚本上次插入的章 —— 再跑会重复插一章。" % new_id)
        print("   换个 --after 参数；确实要再插就加 --force（会先自动备份）。")
        if not a.force:
            return

    ids = [int(x) for x in re.findall(r'<section class="chapter" id="c(\d+)"', text)]
    if not ids:
        print("❌ 一个章节都没找到（section class=\"chapter\" id=\"cNN\"）—— 确认下文件结构")
        return
    max_n = max(ids)
    # 映射：new_n .. max_n → +1
    old_to_new = {cid(n): cid(n + 1) for n in range(new_n, max_n + 1)}

    steps.append("章节数 %d（c%02d–c%02d）→ 插入 %s 后共 %d 章" % (len(ids), min(ids), max_n, new_id, len(ids) + 1))
    if old_to_new:
        steps.append("重编号: %s 起的 %d 个章节整体 +1" % (cid(new_n), len(old_to_new)))
    else:
        steps.append("插在末尾，无需重编号")
    steps.append("将插入新章: %s「%s」" % (new_id, a.title))

    if a.dry_run:
        print("── DRY RUN（不写文件）── ")
        print("\n".join("  • " + s for s in steps))
        print("\n  提示：part 副标题是自由文本，脚本不管，插完记得手工补一句。")
        return

    # ── 备份
    if not a.no_backup:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        bak = re.sub(r"\.html?$", ".备份-%s.html" % ts, path)
        shutil.copy2(path, bak)
        steps.append("已备份 → %s" % bak.split("/")[-1])

    before = len(text)

    # ── 1. section id（两种属性顺序）
    def repl_sec(mo):
        c = mo.group(1) or mo.group(2)
        return mo.group(0).replace('id="%s"' % c, 'id="%s"' % old_to_new[c], 1) if c in old_to_new else mo.group(0)

    text, n_sec = re.subn(
        r'<section\b[^>]*?\b(?:id="(c\d{2})"[^>]*?class="chapter"|class="chapter"[^>]*?id="(c\d{2})")[^>]*>',
        repl_sec, text, flags=re.S)
    steps.append("section id 更新所在标签 %d 个" % n_sec)

    # ── 2. data-ch / href
    text, n_dc = re.subn(r'data-ch="(c\d{2})"',
                         lambda mo: 'data-ch="%s"' % old_to_new.get(mo.group(1), mo.group(1)), text)
    text, n_hf = re.subn(r'href="#(c\d{2})"',
                         lambda mo: 'href="#%s"' % old_to_new.get(mo.group(1), mo.group(1)), text)
    steps.append("data-ch %d 处、href %d 处" % (n_dc, n_hf))

    # ── 3. 可见文本里的章节号（整体 +1，跳过 script/style；标签属性不动）
    lo, hi = new_n, max_n

    def shift(s):
        return re.sub(r"\bc(0?%d|%d)\b" % (lo, hi), lambda mo: "c%d" % (int(mo.group(1)) + 1), s)

    def proc(s):
        parts = re.split(r"(<(?:script|style)\b[^>]*>.*?</(?:script|style)>)", s, flags=re.S)
        out = []
        for i, part in enumerate(parts):
            if i % 2 == 1:
                out.append(part)
                continue
            toks = re.split(r"(<[^>]+>)", part)
            out.append("".join(t if j % 2 == 1 else shift(t) for j, t in enumerate(toks)))
        return "".join(out)

    text = proc(text)
    steps.append("可见文本引用已整体 +1（跳过 script/style 与标签属性）")

    # ── 4. <a> 文字与 href 对齐
    def align(mo):
        pre, href, mid, txt, end = mo.groups()
        t = re.match(r"^#c(\d{2})$", href)
        if not t:
            return mo.group(0)
        return "%s%s%s%s%s" % (pre, href, mid, re.sub(r"\bc(0?\d{1,2})\b", "c%s" % t.group(1), txt), end)

    text, n_align = re.subn(r'(<a\b[^>]*?\bhref=")(#c\d{2})("[^>]*>)(.*?)(</a>)', align, text, flags=re.S)
    steps.append("<a> 链接文字对齐 %d 处" % n_align)

    # ── 5. 插入新章
    if a.body:
        bp = norm_path(a.body)
        try:
            body = io.open(bp, encoding="utf-8").read().strip()
        except Exception as e:
            print("❌ 读不了 --body 指定的文件: %s" % e)
            return
    else:
        body = ('<p class="lead">（待补：这一章要讲什么、给谁看、解决什么问题）</p>\n\n'
                '<h3 class="sub">待补小节</h3>\n'
                '<p>…</p>')

    label = a.toc_label or a.title
    head = "%02d %s %s" % (new_n, a.emoji + " " if a.emoji else "", a.title)
    new_chapter = '%s\n<section class="chapter" id="%s">\n<h2>%s</h2>\n%s\n\n</section>\n' % (MARK, new_id, head.strip(), body)

    marker = '<section class="chapter" id="%s">\n' % cid(new_n + 1)
    if marker not in text:
        # 容错：可能是别的插入点形态
        mm = re.search(r'<section\b[^>]*?\bid="%s"' % cid(new_n + 1), text)
        if not mm:
            print("❌ 找不到插入点（重编号后应存在 %s）—— 文件没被改动，已中止" % cid(new_n + 1))
            return
        text = text[:mm.start()] + new_chapter + text[mm.start():]
    else:
        text = text.replace(marker, new_chapter + marker, 1)
    steps.append("已插入新章 %s「%s」" % (new_id, a.title))

    # ── 6. h2 序号与 section id 对齐
    def fix_h2(mo):
        sec, c, _num, rest = mo.groups()
        return "%s%02d%s" % (sec, int(c[1:]), rest)

    text, n_h2 = re.subn(
        r'(<section\b[^>]*?\bid="(c\d{2})"[^>]*>.*?<h2>)(\d{2})(\s+.*?</h2>)',
        fix_h2, text, flags=re.S)
    steps.append("h2 序号校正 %d 处" % n_h2)

    # ── 7. 静态章节计数
    total = len(ids) + 1
    text, c1 = re.subn(r'(data-count="chapters">)\d+(</span>)', r"\g<1>%d\g<2>" % total, text)
    text, c2 = re.subn(r'(data-stat="chapters">)\d+(</div>)', r"\g<1>%d\g<2>" % total, text)
    if c1 or c2:
        steps.append("静态章节计数 → %d（%d 处）" % (total, c1 + c2))

    # ── 8. 目录 + 顶部导航插一条
    toc_pat = re.compile(r'(<li><a class="toc-ch" href="#%s"[^>]*>.*?</li>)' % cid(new_n + 1))
    if toc_pat.search(text):
        text = toc_pat.sub(
            lambda mo: ('<li><a class="toc-ch" href="#%s" data-ch="%s">%s</a></li>\n' % (new_id, new_id, label)) + mo.group(1),
            text, count=1)
        steps.append("侧边目录已插一条（在 %s 前）" % cid(new_n + 1))
    else:
        steps.append("⚠️ 没找到侧边目录对应条目，需手工补一条")

    nav_pat = re.compile(r'(<a href="#%s">[^<]*</a>)' % cid(new_n + 1))
    if nav_pat.search(text):
        text = nav_pat.sub(
            lambda mo: ('<a href="#%s">%s</a>' % (new_id, label)) + mo.group(1), text, count=1)
        steps.append("顶部导航已插一条")
    else:
        steps.append("⚠️ 没找到顶部导航对应条目，需手工补一条")

    io.open(path, "w", encoding="utf-8", newline="\n").write(text)

    print("── 完成 ──")
    print("\n".join("  • " + s for s in steps))
    print()
    print("  ⚠️ part 副标题是自由文本，脚本不管 —— 记得手工补一句。")
    print("  文件: %s → %s" % (path, bak if not a.no_backup else path))
    print("  建议接着跑: python %s/scan_kb.py \"%s\"" % (
        str(__file__).replace("\\", "/").rsplit("/", 1)[0], path))


if __name__ == "__main__":
    main()
