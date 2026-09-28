# -*- coding: utf-8 -*-
"""
照片查重：dHash 指纹库 + RGB/直方图精细比对 + complete-linkage 聚类

用法：
    python photo_dedup.py --roots "G:\\01_照片" --out "./work"
    python photo_dedup.py --roots "G:\\01_照片,G:\\02_视频" --out "./work" \\
        --exclude "05_软件工具,06_学习资料,08_游戏"

    # 只查「本地 G 盘」与「云盘导出目录」之间重复的（忽略各目录内部的重复）
    python photo_dedup.py --mode cross \\
        --roots "G:\\01_照片,D:\\一刻相册导出" --out "./work"

    # 云盘照片通常被压缩过，判定可略放宽
    python photo_dedup.py --mode cross --rgb-max 4 --hist-min 0.97 \\
        --roots "G:\\01_照片,D:\\一刻相册导出" --out "./work"

产出（都在 --out 目录）：
    photo_hash.csv   指纹库：path, dhash, w, h, size, std, topdir
    dup_groups.csv   重复组：group_id, verdict, max_rgb, min_hist, block_max,
                     path, size, w, h, action

判定标准（可用参数调）：
    确认重复：整组两两 rgb128 <= --rgb-max(2.5)
              且 直方图相关 >= --hist-min(0.99)
              且 block_max <= --block-max(1.5)
              且 文件名时间戳不冲突
    否则      ：疑似不同（仅供人工参考，不可据此删除）

设计要点：
    - 原始尺寸在 resize 之前取，否则记成缩放后的尺寸（典型 bug：全是 9x8）
    - 信息量门槛（灰度标准差）过滤纯色/近纯色图，它们对 dHash 无意义
    - 领域过滤：软件/教程目录不该作为候选，排除后误配大幅下降
    - 先用 dHash 粗筛再精细比对，避免 O(n^2) 的全量像素比对
    - **block_max 是挡连拍的关键**：全图平均差会把「只有人脸动了一点」摊平到看不见，
      直方图也无效（全局颜色分布几乎不变）。分块取最差那块才能识破。
      提高分辨率没用 —— 数值只是等比放大，相对间距不变。
    - 文件名时间戳冲突（`IMG_x_133141` vs `IMG_x_133142`）= 不同时刻拍的，直接否决。
      用文件名而不是 EXIF，后者被重新导出重写过。
    - complete-linkage 聚类，不用单链接（后者会因传递性合并出巨大错误组）
    - 组 ID 用路径哈希，保证多次运行稳定
    - 幂等、失败要响（读取失败计入 errors 并落盘）
    - 退出码：0 正常；1 参数错误；2 有文件读取失败
"""

import argparse
import csv
import hashlib
import os
import re
import sys
from collections import defaultdict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from PIL import Image, ImageStat

Image.MAX_IMAGE_PIXELS = None

IMG_EXT = {"jpg", "jpeg", "jpe", "jfif", "png", "gif", "bmp", "tif", "tiff",
           "webp", "heic"}
DEFAULT_SKIP_DIRS = {"$RECYCLE.BIN", "System Volume Information"}
N = 128          # 精细比对分辨率
MIN_STD = 8.0    # 灰度标准差下限，低于此视为纯色/近纯色


def dhash_and_meta(path):
    """返回 (dhash, 灰度标准差, 原始宽, 原始高)。原始尺寸必须在 resize 前取"""
    try:
        with Image.open(path) as im:
            w0, h0 = im.size
            g = im.convert("L")
            std = ImageStat.Stat(g.resize((64, 64), Image.LANCZOS)).stddev[0]
            # tobytes() 而非 getdata()：后者在 Pillow 14 会移除
            small = g.resize((9, 8), Image.LANCZOS)
            px = small.tobytes()
    except Exception:
        return None, None, None, None
    bits = 0
    for r in range(8):
        base = r * 9
        for c in range(8):
            bits = (bits << 1) | (1 if px[base + c] > px[base + c + 1] else 0)
    return bits, std, w0, h0


def rgb_bytes(path):
    try:
        with Image.open(path) as im:
            return im.convert("RGB").resize((N, N), Image.LANCZOS).tobytes()
    except Exception:
        return None


def rgb_mae(a, b):
    t = 0
    for i in range(len(a)):
        d = a[i] - b[i]
        t += d if d > 0 else -d
    return t / len(a)


def hist_corr(a, b, bins=16):
    ha, hb = [0] * (3 * bins), [0] * (3 * bins)
    for i in range(0, len(a), 3):
        for k in range(3):
            ha[k * bins + a[i + k] * bins // 256] += 1
            hb[k * bins + b[i + k] * bins // 256] += 1
    ma = sum(ha) / len(ha)
    mb = sum(hb) / len(hb)
    num = sum((ha[i] - ma) * (hb[i] - mb) for i in range(len(ha)))
    da = sum((x - ma) ** 2 for x in ha) ** 0.5
    db = sum((x - mb) ** 2 for x in hb) ** 0.5
    return num / (da * db) if da and db else 0.0


def ham(a, b):
    return bin(a ^ b).count("1")


TS_RE = re.compile(r"((?:19|20)\d{6})[_-](\d{6})")


def fname_ts(name):
    """从文件名抠出拍摄时刻，抠不到返回 None。

    用文件名而不是 EXIF date_time —— 后者在重新导出时会被重写，
    同一张照片的副本可能带着互不相同的时间。
    """
    m = TS_RE.search(name)
    return (m.group(1) + m.group(2)) if m else None


def block_max(a, b, blocks=8):
    """把 128x128 归一化图切成 blocks x blocks，返回**最差那块**的平均差。

    区分「连拍」和「重压缩副本」的关键：
      重压缩是整图均匀地差一点点；连拍是背景全对、只有人脸那块差很多。
    全图平均差两者可能一样大（实测都是 3.9 上下），只有分块取最大能把它们分开。

    注意：提高 N（128→256→384）不会拉开差距，数值只是等比放大。
    """
    step = N // blocks
    row = N * 3
    worst = 0.0
    for br in range(blocks):
        y0 = br * step * row
        for bc in range(blocks):
            x0 = bc * step * 3
            tot = cnt = 0
            for r in range(step):
                base = y0 + r * row + x0
                for c in range(step * 3):
                    d = a[base + c] - b[base + c]
                    tot += d if d > 0 else -d
                    cnt += 1
            m = tot / cnt
            if m > worst:
                worst = m
    return worst


def main():
    ap = argparse.ArgumentParser(description="照片查重")
    ap.add_argument("--roots", required=True, help="图片根目录，多个用逗号分隔")
    ap.add_argument("--out", required=True, help="产出目录")
    ap.add_argument("--exclude", default="",
                    help="排除的路径关键词，逗号分隔（如软件/教程目录）")
    ap.add_argument("--skip-dirs", default="", help="跳过的目录名，逗号分隔")
    ap.add_argument("--d-max", type=int, default=8, help="dHash 粗筛阈值")
    ap.add_argument("--rgb-max", type=float, default=2.5, help="RGB 平均差上限")
    ap.add_argument("--hist-min", type=float, default=0.99, help="直方图相关下限")
    ap.add_argument("--block-max", type=float, default=1.5,
                    help="分块最大差异上限 —— 挡住连拍/水印/局部改动。"
                         "真重复≈0，重压缩副本<1.5，连拍/水印/不同截图 10~48")
    ap.add_argument("--no-ts-guard", action="store_true",
                    help="关闭「文件名时间戳冲突」否决（默认开启）")
    ap.add_argument("--min-std", type=float, default=MIN_STD, help="信息量门槛")
    ap.add_argument("--mode", choices=["all", "cross"], default="all",
                    help="all=查所有重复（默认）；cross=只查【跨根目录】的重复，"
                         "用于「本地 vs 云盘导出目录」这类场景，"
                         "不会把各目录内部的重复混进来")
    args = ap.parse_args()

    roots = [r.strip() for r in args.roots.split(",") if r.strip()]
    if not roots:
        print("错误：--roots 为空", file=sys.stderr)
        return 1
    excludes = [e.strip() for e in args.exclude.split(",") if e.strip()]
    skip = set(DEFAULT_SKIP_DIRS) | {
        d.strip() for d in args.skip_dirs.split(",") if d.strip()}
    os.makedirs(args.out, exist_ok=True)

    # --- 阶段 1：指纹库 ---
    lib = []
    errors = []
    total = 0
    for ri, root in enumerate(roots):
        if not os.path.isdir(root):
            errors.append(f"[根目录不存在] {root}")
            continue
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if d not in skip]
            for f in fn:
                if os.path.splitext(f)[1].lower().lstrip(".") not in IMG_EXT:
                    continue
                p = os.path.join(dp, f)
                total += 1
                if any(e in p for e in excludes):
                    continue
                try:
                    sz = os.path.getsize(p)
                except OSError as ex:
                    errors.append(f"{p}\t{ex.__class__.__name__}")
                    continue
                if sz == 0:
                    continue
                h, std, w, hh = dhash_and_meta(p)
                if h is None:
                    errors.append(f"{p}\t读取失败")
                    continue
                if std is not None and std < args.min_std:
                    continue          # 纯色/近纯色，dHash 对它无意义
                lib.append({"path": p, "dh": h, "std": std,
                            "w": w, "h": hh, "size": sz, "root": ri,
                            "fts": fname_ts(os.path.basename(p)),
                            "topdir": p.replace(root, "").split(os.sep)[0]
                            if p.startswith(root) else ""})
                if total % 1000 == 0:
                    print(f"  已处理 {total} 张 ...", flush=True)

    print(f"扫描 {total} 张 -> 有效候选 {len(lib)} 张（排除 {total - len(lib)}）")

    with open(os.path.join(args.out, "photo_hash.csv"), "w", newline="",
              encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["path", "dhash", "w", "h", "size",
                                          "std", "topdir"])
        w.writeheader()
        for it in lib:
            w.writerow({"path": it["path"], "dhash": f"{it['dh']:016x}",
                        "w": it["w"], "h": it["h"], "size": it["size"],
                        "std": round(it["std"], 2), "topdir": it["topdir"]})

    # --- 阶段 2：粗筛（dHash）+ 精细比对 ---
    # 顺序按「便宜的先上、贵的放最后」：汉明距离 → 时间戳 → RGB 平均差 → 直方图 → block_max
    edges = defaultdict(set)
    checked = 0
    ts_blocked = 0
    cross_only = (args.mode == "cross")
    for i in range(len(lib)):
        for j in range(i + 1, len(lib)):
            # cross 模式：跳过同一个根目录内部的配对
            if cross_only and lib[i]["root"] == lib[j]["root"]:
                continue
            checked += 1
            if checked % 5_000_000 == 0:
                print(f"  粗筛 {checked//1_000_000} 百万对 ...", flush=True)
            if ham(lib[i]["dh"], lib[j]["dh"]) > args.d_max:
                continue
            # 文件名时间戳冲突 = 不同时刻拍的，不可能是重复
            if not args.no_ts_guard:
                ti, tj = lib[i]["fts"], lib[j]["fts"]
                if ti and tj and ti != tj:
                    ts_blocked += 1
                    continue
            a, b = rgb_bytes(lib[i]["path"]), rgb_bytes(lib[j]["path"])
            if a is None or b is None:
                continue
            if rgb_mae(a, b) > args.rgb_max:
                continue
            if hist_corr(a, b) < args.hist_min:
                continue
            # 最后一道：挡住连拍/水印这类「只差一块」的
            if block_max(a, b) > args.block_max:
                continue
            edges[i].add(j)
            edges[j].add(i)
    n_edges = sum(len(v) for v in edges.values()) // 2
    print(f"  精细比对后确认的相似边: {n_edges}"
          + (f"（文件名时间戳冲突否决 {ts_blocked} 对）" if ts_blocked else ""))

    # --- 阶段 3：complete-linkage 聚类 ---
    visited = set()
    groups = []
    for i in sorted(edges, key=lambda x: -len(edges[x])):
        if i in visited:
            continue
        grp = [i]
        cand = set(edges[i])
        while True:
            best = None
            for j in cand:
                if j in visited or j in grp:
                    continue
                # 必须与组内【所有】成员都相似，这是与单链接的关键区别
                if all(j in edges[x] for x in grp):
                    if best is None or len(edges[j]) > len(edges[best]):
                        best = j
            if best is None:
                break
            grp.append(best)
            cand |= edges[best]
        visited.update(grp)
        if len(grp) > 1:
            groups.append(grp)

    print(f"  聚类 {len(groups)} 组")

    # --- 输出 ---
    out_rows = []
    for grp in groups:
        paths = sorted(lib[x]["path"] for x in grp)
        gid = hashlib.md5("|".join(paths).encode("utf-8")).hexdigest()[:8]
        worst_rgb, worst_hist, worst_blk = 0.0, 1.0, 0.0
        ts_conflict = False
        for a in range(len(grp)):
            for b in range(a + 1, len(grp)):
                ia, ib = lib[grp[a]], lib[grp[b]]
                ra, rb = rgb_bytes(ia["path"]), rgb_bytes(ib["path"])
                if ra is None or rb is None:
                    continue
                worst_rgb = max(worst_rgb, rgb_mae(ra, rb))
                worst_hist = min(worst_hist, hist_corr(ra, rb))
                worst_blk = max(worst_blk, block_max(ra, rb))
                if (not args.no_ts_guard and ia["fts"] and ib["fts"]
                        and ia["fts"] != ib["fts"]):
                    ts_conflict = True
        verdict = ("确认重复" if worst_rgb <= args.rgb_max
                   and worst_hist >= args.hist_min
                   and worst_blk <= args.block_max
                   and not ts_conflict else "疑似不同")
        ordered = sorted(grp, key=lambda x: (-(lib[x]["w"] * lib[x]["h"]),
                                             -lib[x]["size"]))
        for k, x in enumerate(ordered):
            out_rows.append({
                "group_id": gid, "verdict": verdict,
                "max_rgb": round(worst_rgb, 2), "min_hist": round(worst_hist, 4),
                "block_max": round(worst_blk, 2),
                "path": lib[x]["path"], "size": lib[x]["size"],
                "w": lib[x]["w"], "h": lib[x]["h"],
                "action": "keep" if k == 0 else "move",
            })

    with open(os.path.join(args.out, "dup_groups.csv"), "w", newline="",
              encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["group_id", "verdict", "max_rgb",
                                          "min_hist", "block_max", "path", "size",
                                          "w", "h", "action"])
        w.writeheader()
        w.writerows(out_rows)

    err_txt = os.path.join(args.out, "photo_errors.txt")
    with open(err_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(errors))

    # 按 group_id 去重统计，不能数行数
    conf = len({r["group_id"] for r in out_rows if r["verdict"] == "确认重复"})
    print()
    print(f"重复组 {len(groups)}，其中确认重复 {conf} 组")
    print(f"产出目录: {args.out}")
    if errors:
        print(f"!! 读取失败的 {len(errors)} 个文件见 {err_txt}")
    return 2 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
