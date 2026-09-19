#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单文件 HTML 知识库结构速探 —— 动手前先跑，摸清目标文件。

把 skill 场景一第 1 步那三条 grep 固化成一次执行。

用法:
    python probe_kb.py <html文件>
    python probe_kb.py <html文件> --json

输出:
  * 体积 / 章节数 / 章节 id → 行号（定位锚点用）
  * <details> 各类计数
  * callout 各变体计数
  * new-tag 已有风格（避免写出不存在的标签）
  * 表格总数 / 推荐表数 / 带 colgroup 的表数
  * <script> 块数

纪律（见 local-script-first）: 只读；退出码恒 0。
"""
import argparse
import io
import json
import re
import sys
from collections import Counter


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


def probe(html):
    secs = [(m.group(1), html[:m.start()].count("\n") + 1)
            for m in re.finditer(r'<section class="chapter" id="(c\d+)">', html)]

    details = Counter(re.findall(r'<details class="([a-z-]+)"', html))
    callouts = Counter(re.findall(r'<div class="callout ([a-z-]+)">', html))
    newtags = sorted(set(re.findall(r'<span class="new-tag">([^<]*)</span>', html)))

    tables = re.findall(r'<table\b[^>]*>.*?</table>', html, re.S)
    rec_tbl = [t for t in tables if 'rec-tbl' in t[:200] or '推荐型号' in t[:600]]
    with_colgroup = [t for t in tables if '<colgroup' in t]

    scripts = len(re.findall(r'<script\b', html))

    return {
        "chars": len(html),
        "sections": secs,
        "details": dict(details),
        "callouts": dict(callouts),
        "new_tags": newtags,
        "tables_total": len(tables),
        "tables_rec": len(rec_tbl),
        "tables_with_colgroup": len(with_colgroup),
        "scripts": scripts,
    }


def main():
    ap = argparse.ArgumentParser(description="单文件 HTML 知识库结构速探")
    ap.add_argument("file")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    a.file = norm_path(a.file)
    html = load(a.file)
    p = probe(html)

    if a.json:
        print(json.dumps(dict(file=a.file, **p), ensure_ascii=False, indent=2))
        return

    L = ["速探: %s   (%.2f MB)" % (a.file, p["chars"] / 1048576), ""]
    L.append("章节 %d 个：%s" % (len(p["sections"]), " ".join(i for i, _ in p["sections"])))
    L.append("")
    L.append("章节 id → 行号（定位锚点用）:")
    for i, ln in p["sections"]:
        L.append("   %-6s L%d" % (i, ln))
    L.append("")
    if p["details"]:
        L.append("<details> 类: " + " · ".join("%s %d" % (k, v) for k, v in sorted(p["details"].items())))
    if p["callouts"]:
        L.append("callout 变体: " + " · ".join("%s %d" % (k, v) for k, v in sorted(p["callouts"].items())))
        L.append("   ⚠️ 只写以上出现过的变体，别新增未定义的")
    L.append("表格: 共 %d 张（推荐表 %d 张，带 colgroup 的 %d 张）" % (
        p["tables_total"], p["tables_rec"], p["tables_with_colgroup"]))
    if p["tables_total"] - p["tables_with_colgroup"] > 0:
        L.append("   ⚠️ 新增表必须带 <colgroup>，否则长文本列会被压成一字一行")
    L.append("<script> 块: %d 个" % p["scripts"])
    if p["new_tags"]:
        L.append("已有 new-tag 风格: " + " · ".join(t.strip() for t in p["new_tags"][:12]))
    print("\n".join(L))


if __name__ == "__main__":
    main()
