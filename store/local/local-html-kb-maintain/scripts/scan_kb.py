#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单文件 HTML 知识库结构体检 —— 一次跑完常见结构问题。

把 skill 里那 8 条「常用校验正则」固化成一次执行，省得每次复制粘贴组装。

用法:
    python scan_kb.py <html文件>
    python scan_kb.py <html文件> --json        # 机器可读

纪律（见 local-script-first）:
  * 幂等：只读，不改文件
  * 失败要响：找不到文件 / 解码失败都明确报出来，不静默跳过
  * 退出码恒为 0 —— 有问题写进输出正文（宿主工具遇到非零退出码会丢掉 stdout）
"""
import argparse
import io
import json
import re
import sys


def norm_path(p):
    """把 MSYS 风格 /c/xxx 转成 Windows 路径 —— Python 是原生程序，不认 /c/。

    （本机 bash 里传参常是 /c/... 或 ~ 展开后的形式，脚本要能直接吃。）
    """
    if not p:
        return p
    p = p.strip().strip('"').strip("'")
    m = re.match(r"^/([a-zA-Z])/(.*)$", p)
    if m:
        return "%s:/%s" % (m.group(1).upper(), m.group(2))
    return p


def load(path):
    path = norm_path(path)
    try:
        return io.open(path, encoding="utf-8").read()
    except FileNotFoundError:
        print("❌ 找不到文件: %s" % path)
        sys.exit(0)
    except UnicodeDecodeError as e:
        print("❌ 不是 UTF-8 编码，读不了: %s" % e)
        sys.exit(0)


def lineno(html, pos):
    return html[:pos].count("\n") + 1


def check(html):
    """返回 [(检查名, 为什么重要, [命中详情…]), …]"""
    out = []

    # 1. 空 callout（有标题没正文）
    pat = re.compile(r'<div class="callout ([a-z-]+)">\s*<div class="ctitle">([^<]*)</div>\s*</div>', re.S)
    out.append(("空 callout", "有标题没内容，多半是删正文时漏了外壳",
                ["[L%d] %s — %s" % (lineno(html, m.start()), m.group(1), m.group(2).strip())
                 for m in pat.finditer(html)]))

    # 2. 空列表
    pat = re.compile(r'<ul>\s*</ul>|<ol[^>]*>\s*</ol>', re.S)
    out.append(("空列表", "ul/ol 里没有 li",
                ["[L%d]" % lineno(html, m.start()) for m in pat.finditer(html)]))

    # 3. summary 内混入块级内容
    blocks = ['<table', '<p class="lead"', 'class="callout"', '<ul>', '<ol']
    hits = []
    for m in re.finditer(r'<summary[^>]*>(.*?)</summary>', html, re.S):
        bad = [t for t in blocks if t in m.group(1)]
        if bad:
            hits.append("[L%d] 含 %s" % (lineno(html, m.start()), ", ".join(bad)))
    out.append(("summary 内混入块级内容", "排版错乱真因之一：flex 会把内容压成一列", hits))

    # 4. </summary> 后重复标题（旧式折叠残留）
    pat = re.compile(r'</summary>\s*<h3 class="sub">[^<]*<span class="new-tag">')
    out.append(("summary 后重复标题", "旧式折叠结构残留：正文又写了一遍标题",
                ["[L%d]" % lineno(html, m.start()) for m in pat.finditer(html)]))

    # 5. 章节 id 重复
    ids = re.findall(r'<section class="chapter" id="(c\d+)">', html)
    dup = sorted({i for i in ids if ids.count(i) > 1})
    out.append(("章节 id 重复", "同一 id 出现多次，锚点会跳错", dup))

    # 6. 断链
    idset = set(ids)
    broken = sorted({m.group(1) for m in re.finditer(r'href="#(c\d+)"', html)
                     if m.group(1) not in idset})
    out.append(("断链", "href 指向了不存在的章节 id", broken))

    # 7. 章号与链接文字不一致
    mism = ["%s → 文字写的是 %s [L%d]" % (m.group(1), m.group(2), lineno(html, m.start()))
            for m in re.finditer(r'<a href="#(c\d+)"[^>]*>(c\d+)\s', html)
            if m.group(1) != m.group(2)]
    out.append(("章号与链接文字不一致", "点进去的章和显示的不是同一个", mism))

    # 8. 提醒块类目与图标冲突
    conflict = {"warn": {"💡", "✅", "ℹ️"}, "tip": {"⚠️", "🚨", "❌"}, "info": {"⚠️", "🚨", "❌"}}
    hits = []
    for m in re.finditer(r'<div class="callout (warn|tip|info)">\s*<div class="ctitle">([^<]*)</div>', html):
        kind, title = m.group(1), m.group(2)
        head = title.strip()
        for ic in conflict.get(kind, set()):
            # 只看 ctitle 开头的图标；正文里出现 ⚠️ 是正常表达（表示"短板/注意"）
            if head.startswith(ic):
                hits.append("[L%d] %s 配了 %s —— %s" % (lineno(html, m.start()), kind, ic, title.strip()[:24]))
    out.append(("提醒块类目与图标冲突", "warn 配 💡 / tip 配 ⚠️ 之类，语义打架", hits))

    return out


def main():
    ap = argparse.ArgumentParser(description="单文件 HTML 知识库结构体检")
    ap.add_argument("file")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    a = ap.parse_args()

    a.file = norm_path(a.file)
    html = load(a.file)
    results = check(html)
    total = sum(len(h) for _, _, h in results)

    if a.json:
        print(json.dumps({
            "file": a.file, "chars": len(html), "total_issues": total,
            "checks": [{"name": n, "why": w, "count": len(h), "hits": h} for n, w, h in results],
        }, ensure_ascii=False, indent=2))
        return

    lines = ["体检: %s   (%.2f MB)" % (a.file, len(html) / 1048576), ""]
    for name, why, hits in results:
        mark = "✅" if not hits else "⚠️"
        lines.append("%s %-24s %s" % (mark, name, ("%d 处" % len(hits)) if hits else "无"))
        if hits:
            lines.append("     %s" % why)
            for h in hits[:10]:
                lines.append("       · " + h)
            if len(hits) > 10:
                lines.append("       … 另有 %d 处" % (len(hits) - 10))
    lines += ["", ("共 %d 处问题" % total) if total else "结构干净 ✅"]
    print("\n".join(lines))


if __name__ == "__main__":
    main()
