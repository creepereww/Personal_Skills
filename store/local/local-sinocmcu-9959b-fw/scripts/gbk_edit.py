#!/usr/bin/env python3
"""Byte-safe search/replace for GBK-encoded source files.

Editing these sources as UTF-8 destroys every Chinese comment (the invalid
GBK bytes get replaced by U+FFFD = EF BF BD and the result is written back).
This script only ever touches bytes and refuses to corrupt anything.

Usage:
    python3 gbk_edit.py <file> <old-text> <new-text> [--count N] [--dry-run]
    python3 gbk_edit.py <file> --check

<old-text> / <new-text> are written as Python str and encoded with the file's
own codec (GBK) before matching, so you can type Chinese normally.
"""
import argparse
import os
import shutil
import sys
import tempfile

FFFD = b"\xef\xbf\xbd"


def detect_codec(data):
    for enc in ("gbk", "utf-8"):
        try:
            data.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    return "gbk"


def check(path, data):
    ok = True
    n = data.count(FFFD)
    if n:
        print("!! %s: %d 个 U+FFFD(EF BF BD)，中文注释已损坏" % (path, n))
        bad = [i + 1 for i, l in enumerate(data.split(b"\n")) if FFFD in l]
        print("   受损行:", bad[:20], "..." if len(bad) > 20 else "")
        ok = False
    try:
        data.decode("gbk")
    except UnicodeDecodeError as e:
        print("!! %s: 不是合法 GBK: %s" % (path, e))
        ok = False
    if ok:
        print("OK  %s: %d bytes, 无损坏字符, GBK 合法" % (path, len(data)))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("old", nargs="?")
    ap.add_argument("new", nargs="?")
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-backup", action="store_true")
    ap.add_argument("--check", action="store_true", help="只体检，不修改")
    args = ap.parse_args()

    path = args.file
    with open(path, "rb") as f:
        data = f.read()

    if args.check or args.old is None:
        sys.exit(0 if check(path, data) else 1)

    if args.new is None:
        print("必须同时给出 new-text", file=sys.stderr)
        return 2

    enc = detect_codec(data)
    old = args.old.encode(enc)
    new = args.new.encode(enc)

    found = data.count(old)
    if found < args.count:
        print("!! 只找到 %d 处 <%d 处要求的匹配，未做修改" % (found, args.count),
              file=sys.stderr)
        return 1
    if found > args.count:
        print("注意: 找到 %d 处匹配 > 要求的 %d 处" % (found, args.count))

    out = data.replace(old, new, args.count)

    # ---- safety gates before touching the file -------------------------------
    if FFFD in out and FFFD not in data:
        print("!! 新内容会引入 U+FFFD，放弃修改", file=sys.stderr)
        return 1
    try:
        out.decode("gbk")
    except UnicodeDecodeError as e:
        print("!! 新内容不是合法 GBK，放弃修改: %s" % e, file=sys.stderr)
        return 1
    if len(out.split(b"\n")) != len(data.split(b"\n")):
        print("!! 行数会变化（%d -> %d），请单独确认后手工处理"
              % (len(data.split(b"\n")), len(out.split(b"\n"))), file=sys.stderr)
        return 1

    if args.dry_run:
        print("(dry-run) 将替换 %d 处，未写入" % args.count)
        return 0

    if not args.no_backup:
        bak = os.path.join(tempfile.gettempdir(),
                           os.path.basename(path) + ".bak")
        shutil.copy2(path, bak)
        print("已备份:", bak)

    with open(path, "wb") as f:
        f.write(out)

    check(path, out)
    print("已替换 %d 处" % args.count)
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)