#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""推荐表批量编辑后的核对 —— 计数比对 + 抽查。

把 skill 场景四「验证清单」固化成一次执行。

用法:
    python check_rec_tbl.py <html文件>
    python check_rec_tbl.py <html文件> --header "预算（参考）" --cell-class rbudget --note "本章预算参考"

默认值对应「给推荐表加预算列」那次操作的约定；换别的列就传对应参数。

核对:
  * 表头含目标列的表数（应等于推荐表数）
  * 该列数据单元格（带 cell-class 的 td）数 vs 表内数据行总数
  * 章节级注释出现次数（应等于有推荐表的章节数）
  * 对比表（无「推荐型号」表头）不该含该列

纪律（见 local-script-first）: 只读；退出码恒 0。
"""
import argparse
import io
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
        print("❌ 不是 UTF-8 编码: %s" % e)
        sys.exit(0)


def tables_of(html):
    return [(m.start(), m.group(0)) for m in re.finditer(r'<table\b[^>]*>.*?</table>', html, re.S)]


def main():
    ap = argparse.ArgumentParser(description="推荐表批量编辑后的核对")
    ap.add_argument("file")
    ap.add_argument("--header", default="预算（参考）", help="目标列表头文字")
    ap.add_argument("--cell-class", default="rbudget", help="该列数据单元格的 class")
    ap.add_argument("--note", default="本章预算参考", help="章节级注释文字")
    a = ap.parse_args()

    a.file = norm_path(a.file)
    html = load(a.file)
    tl = tables_of(html)

    rec_hdr = []
    cmp_tbl_wrong = []
    for pos, t in tl:
        head = t[:900]
        is_rec = 'rec-tbl' in head or '推荐型号' in head
        if is_rec:
            rec_hdr.append((pos, t))
        elif '<th' in head and a.header in head:
            cmp_tbl_wrong.append(pos)

    # 章节边界（用于判断"有推荐表的章节数"）
    secs = [(m.start(), m.group(1)) for m in re.finditer(r'<section class="chapter" id="(c\d+)">', html)]

    def chap_of(pos):
        cur = None
        for s, i in secs:
            if s <= pos:
                cur = i
            else:
                break
        return cur

    # 每张推荐表：表头有没有目标列 / 数据行数（只数含 <td> 的行，表头行不算）
    detail = []
    hdr_ok = 0
    row_total = cell_total = 0
    chaps_with_rec = set()
    for pos, tbl in rec_hdr:
        head_part = tbl.split('</thead>', 1)[0]
        has_col = a.header in head_part
        rows = len(re.findall(r'<tr[^>]*>\s*<td', tbl))
        cells = len(re.findall(r'<td[^>]*class="[^"]*%s[^"]*"' % re.escape(a.cell_class), tbl))
        hdr_ok += 1 if has_col else 0
        row_total += rows
        cell_total += cells
        chaps_with_rec.add(chap_of(pos))
        ln = html[:pos].count("\n") + 1
        detail.append("   L%-6d %-4s 表头%s  数据行 %-3d  该列单元格 %-3d" % (
            ln, chap_of(pos) or "?", "✅" if has_col else "❌缺", rows, cells))

    notes = len(re.findall(re.escape(a.note), html))

    L = ["核对: %s" % a.file, ""]
    L.append("推荐表 %d 张，其中表头含「%s」的: %d 张 %s" % (
        len(rec_hdr), a.header, hdr_ok, "✅" if hdr_ok == len(rec_hdr) else "⚠️ 不一致"))
    L.append("该列单元格合计 %d 个 / 数据行合计 %d 行 %s" % (
        cell_total, row_total, "✅" if cell_total == row_total else "⚠️ 对不上（可能漏填或结构被吃）"))
    L.append("章节级注释「%s」出现 %d 次 / 有推荐表的章节 %d 个 %s" % (
        a.note, notes, len(chaps_with_rec),
        "✅" if notes == len(chaps_with_rec) else "⚠️ 对不上"))
    L.append("")
    L.append("逐表：")
    L += detail if detail else ["   （没找到推荐表 —— 确认下 rec-tbl 类或「推荐型号」表头是否还在）"]
    if cmp_tbl_wrong:
        L.append("")
        L.append("⚠️ 以下对比表意外含了该列（不该加）: %s" % ", ".join("L%d" % (html[:p].count("\n") + 1) for p in cmp_tbl_wrong))
    print("\n".join(L))


if __name__ == "__main__":
    main()
