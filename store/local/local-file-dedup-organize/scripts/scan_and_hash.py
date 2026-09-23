# -*- coding: utf-8 -*-
"""
阶段 1+2：扫描盘点 + MD5 全量查重

用法：
    python scan_and_hash.py --roots "G:\\" --out "G:\\整理工作区"
    python scan_and_hash.py --roots "G:\\,H:\\" --out "./work" --min-size 1024
    python scan_and_hash.py --roots "D:\\照片" --out "./work" --plan   # 额外产出移动方案

产出（都在 --out 目录）：
    files.csv        全量台账：path, size, ext, mtime
    scan_errors.txt  无法访问的文件（权限/损坏），逐个列出
    dup_groups.csv   重复组：group_id, path, size, mtime, action(keep/move)
    dup_move_plan.csv（--plan）只含要移走的条目，可直接驱动移动脚本

设计要点：
    - 幂等：重复运行结果一致（文件没变的话），可安全重跑
    - 失败要响：无法访问的文件单独落盘，不静默跳过
    - 退出码：0 正常；1 参数错误；2 扫描过程中出现无法访问的文件
"""

import argparse
import csv
import hashlib
import os
import sys
from collections import defaultdict

# Windows 下中文路径/文件名需要显式声明编码，否则 print 会抛 UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 这些目录名说明是备份/中转性质，作为保留方时优先级降低
BACKUP_HINTS = ("back", "backup", "bak", "备份", "旧", "temp", "tmp",
                "cache", "回收站", "recycle")


def md5_of(path, block=1 << 20):
    h = hashlib.md5()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(block), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def keep_rank(path):
    """保留优先级打分，越小越应该被保留"""
    depth = path.count(os.sep)
    penalty = 0
    low = path.lower()
    for hint in BACKUP_HINTS:
        if hint in low:
            penalty += 50
    return depth + penalty


def scan(roots, min_size, skip_dirs):
    rows = []
    errors = []
    for root in roots:
        if not os.path.isdir(root):
            errors.append(f"[根目录不存在] {root}")
            continue
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if d not in skip_dirs]
            for f in fn:
                p = os.path.join(dp, f)
                try:
                    st = os.stat(p)
                except OSError as e:
                    errors.append(f"{p}\t{e.__class__.__name__}: {e}")
                    continue
                if st.st_size < min_size:
                    continue
                rows.append({
                    "path": p,
                    "size": st.st_size,
                    "ext": os.path.splitext(f)[1].lower().lstrip("."),
                    "mtime": int(st.st_mtime),
                })
    return rows, errors


def main():
    ap = argparse.ArgumentParser(description="扫描盘点 + MD5 查重")
    ap.add_argument("--roots", required=True,
                    help="要扫描的根目录，多个用逗号分隔")
    ap.add_argument("--out", required=True, help="产出目录")
    ap.add_argument("--min-size", type=int, default=1,
                    help="小于此字节的文件跳过（默认 1，即跳过空文件）")
    ap.add_argument("--skip-dirs", default="$RECYCLE.BIN,System Volume Information",
                    help="跳过的目录名，逗号分隔")
    ap.add_argument("--plan", action="store_true",
                    help="额外产出 dup_move_plan.csv（只含待移走条目）")
    args = ap.parse_args()

    roots = [r.strip() for r in args.roots.split(",") if r.strip()]
    skip = {d.strip() for d in args.skip_dirs.split(",") if d.strip()}
    os.makedirs(args.out, exist_ok=True)

    if not roots:
        print("错误：--roots 为空", file=sys.stderr)
        return 1

    print(f"扫描 {len(roots)} 个根目录 ...")
    rows, errors = scan(roots, args.min_size, skip)
    print(f"  文件 {len(rows)} 个，无法访问 {len(errors)} 个")

    files_csv = os.path.join(args.out, "files.csv")
    with open(files_csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["path", "size", "ext", "mtime"])
        w.writeheader()
        w.writerows(rows)

    err_txt = os.path.join(args.out, "scan_errors.txt")
    with open(err_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(errors))
    if errors:
        print(f"  !! 无法访问的文件已写入 {err_txt}，建议先修权限再重扫")

    # --- 查重：先按大小分组 ---
    by_size = defaultdict(list)
    for r in rows:
        by_size[r["size"]].append(r)
    candidates = {s: v for s, v in by_size.items() if len(v) > 1}
    cand_count = sum(len(v) for v in candidates.values())
    print(f"  同大小候选 {cand_count} 个，开始算 MD5 ...")

    groups = defaultdict(list)
    done = 0
    for size, items in candidates.items():
        by_md5 = defaultdict(list)
        for it in items:
            m = md5_of(it["path"])
            done += 1
            if m:
                by_md5[m].append(it)
            if done % 2000 == 0:
                print(f"    已算 {done}/{cand_count}", flush=True)
        for m, g in by_md5.items():
            if len(g) > 1:
                groups[m] = g

    print(f"  重复组 {len(groups)} 组")

    # --- 决定保留方 ---
    out_rows = []
    plan_rows = []
    for gid, (m, items) in enumerate(sorted(groups.items()), 1):
        # 打分小的优先保留；同分取修改时间最新的
        ordered = sorted(items, key=lambda x: (keep_rank(x["path"]), -x["mtime"]))
        keeper = ordered[0]
        for k, it in enumerate(ordered):
            action = "keep" if k == 0 else "move"
            rec = {"group_id": gid, "md5": m, "path": it["path"],
                   "size": it["size"], "mtime": it["mtime"], "action": action}
            out_rows.append(rec)
            if action == "move":
                plan_rows.append(dict(rec, keep_path=keeper["path"]))

    with open(os.path.join(args.out, "dup_groups.csv"), "w", newline="",
              encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["group_id", "md5", "path", "size",
                                          "mtime", "action"])
        w.writeheader()
        w.writerows(out_rows)

    if args.plan:
        with open(os.path.join(args.out, "dup_move_plan.csv"), "w", newline="",
                  encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=["group_id", "md5", "path", "size",
                                              "mtime", "action", "keep_path"])
            w.writeheader()
            w.writerows(plan_rows)

    waste = sum(r["size"] for r in plan_rows)
    print()
    print(f"多余副本 {len(plan_rows)} 个，可回收 {waste/1024**3:.2f} GB")
    print(f"产出目录: {args.out}")

    return 2 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
