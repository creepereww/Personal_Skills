#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""手机导出媒体库探针：扫描根目录，提取拍摄日期，产出 UTF-8-BOM CSV。

用法：
  python media_probe.py ROOT [ROOT ...] --out probe.csv
  python media_probe.py ROOT --out probe.csv --hash          # 额外算全量 MD5（慢）
  python media_probe.py ROOT --out probe.csv --bad-mtime 2026-06-25,2026-06-23

输出列：
  path, root, name, ext, kind, size, date, date_source, confidence, mtime, md5

日期优先级：EXIF DateTimeOriginal > 文件名 > EXIF DateTimeDigitized
          > 文件夹 > mtime > EXIF DateTime(306)（后两者低可信，需标注）
mtime 默认只作低可信兜底；--bad-mtime 列出的导出日会被整体跳过。
注意 TIFF 306 是 DateTime（图像被写入/后处理的时间），不是 Software(305)，
也不是拍摄时间，只能垫底。

只做只读扫描，不改任何源文件。EXIF 用标准库解析 JPEG APP1 / 裸 TIFF；
MP4/MOV 的 moov 可能在文件尾，按顶层原子遍历定位后再读 mvhd（1904 纪元）。
"""
import argparse
import csv
import datetime as dt
import hashlib
import os
import re
import struct
import sys

IMG_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic", ".heif",
           ".webp", ".bmp", ".gif", ".dng", ".cr2", ".arw", ".nef", ".jxl", ".avif"}
VID_EXT = {".mp4", ".mov", ".m4v", ".3gp", ".avi", ".mkv", ".wmv", ".mts", ".m2ts"}
EPOCH1904 = dt.datetime(1904, 1, 1, tzinfo=dt.timezone.utc)


# ---------- EXIF（标准库最小实现） ----------

def _tiff_ifd(buf, off, endian, base=0):
    """返回 {tag: (type, count, value_bytes_or_offset, raw_ifd_start)}"""
    if off + 2 > len(buf):
        return {}
    n = struct.unpack_from(endian + "H", buf, off)[0]
    out = {}
    for i in range(n):
        p = off + 2 + i * 12
        if p + 12 > len(buf):
            break
        tag, typ, cnt = struct.unpack_from(endian + "HHI", buf, p)
        raw = buf[p + 8:p + 12]
        out[tag] = (typ, cnt, raw, p)
    return out


def _ascii(buf, typ, cnt, raw, endian):
    if typ != 2 or cnt == 0 or cnt > 4096:
        return None
    off = struct.unpack(endian + "I", raw)[0] if cnt > 4 else 0
    pos = off if cnt > 4 else 0
    if cnt <= 4:
        data = raw[:cnt]
    else:
        pos = off
        if pos + cnt > len(buf):
            return None
        data = buf[pos:pos + cnt]
    try:
        return data.split(b"\0", 1)[0].decode("ascii", "ignore").strip()
    except Exception:
        return None


def _exif_date(s):
    if not s:
        return None
    m = re.match(r"(\d{4})[:\-](\d{2})[:\-](\d{2})[ T](\d{2}):(\d{2}):(\d{2})", s)
    if not m:
        return None
    try:
        return dt.datetime(*(int(x) for x in m.groups()))
    except ValueError:
        return None


def exif_dates(path):
    """返回 (orig, digi, exif_datetime_306)；读不到返回 (None, None, None)"""
    try:
        with open(path, "rb") as f:
            head = f.read(512 * 1024)
    except OSError:
        return None, None, None
    buf = None
    if head[:2] == b"\xff\xd8":                       # JPEG：找 APP1 / Exif
        p = 2
        while p + 4 <= len(head):
            if head[p] != 0xFF:
                p += 1
                continue
            marker = head[p + 1]
            if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                p += 2
                continue
            seg = struct.unpack_from(">H", head, p + 2)[0]
            if marker == 0xE1 and head[p + 4:p + 10] == b"Exif\0\0":
                buf = head[p + 10:]
                break
            if seg < 2:
                break
            p += 2 + seg
    elif head[:4] in (b"II*\0", b"MM\0*"):           # 裸 TIFF
        buf = head
    if not buf or len(buf) < 8:
        return None, None, None

    endian = "<" if buf[:2] == b"II" else ">"
    try:
        if struct.unpack_from(endian + "H", buf, 2)[0] != 42:
            return None, None, None
        ifd0_off = struct.unpack_from(endian + "I", buf, 4)[0]
        ifd0 = _tiff_ifd(buf, ifd0_off, endian)
        dt306 = None
        if 306 in ifd0:
            dt306 = _exif_date(_ascii(buf, *ifd0[306][:3], endian))
        orig = digi = None
        if 0x8769 in ifd0:
            sub_off = struct.unpack(endian + "I", ifd0[0x8769][2])[0]
            sub = _tiff_ifd(buf, sub_off, endian)
            for tag, dest in ((36867, "orig"), (36868, "digi")):
                if tag in sub:
                    s = _ascii(buf, *sub[tag][:3], endian)
                    d = _exif_date(s)
                    if dest == "orig":
                        orig = d
                    else:
                        digi = d
        return orig, digi, dt306
    except (struct.error, ValueError, IndexError):
        return None, None, None


# ---------- MP4 / MOV mvhd ----------

def _mvhd_from_chunk(chunk):
    i = chunk.find(b"mvhd")
    if i < 0 or i + 4 + 24 > len(chunk):
        return None
    p = i + 4                       # version(1) + flags(3)
    ver = chunk[p]
    try:
        if ver == 1:
            secs = struct.unpack_from(">Q", chunk, p + 4)[0]
        else:
            secs = struct.unpack_from(">I", chunk, p + 4)[0]
    except struct.error:
        return None
    if secs == 0 or secs > 2 ** 40:
        return None
    try:
        utc = EPOCH1904 + dt.timedelta(seconds=secs)
        return utc.astimezone().replace(tzinfo=None)
    except (OverflowError, ValueError):
        return None


def mp4_ctime(path, cap=32 * 1024 * 1024):
    """按顶层原子遍历定位 moov（moov 可能在文件尾），再读 mvhd。"""
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            head = f.read(min(size, 64 * 1024))
            d = _mvhd_from_chunk(head)
            if d:
                return d
            tail_start = max(0, size - 4 * 1024 * 1024)
            f.seek(tail_start)
            tail = f.read()
            d = _mvhd_from_chunk(tail)
            if d:
                return d

            f.seek(0)
            pos = 0
            while pos < size:
                f.seek(pos)
                hdr = f.read(16)
                if len(hdr) < 8:
                    break
                asize, atype = struct.unpack_from(">I4s", hdr, 0)
                hlen = 8
                if asize == 1:
                    if len(hdr) < 16:
                        break
                    asize = struct.unpack_from(">Q", hdr, 8)[0]
                    hlen = 16
                elif asize == 0:
                    asize = size - pos
                if asize < hlen or pos + asize > size:
                    break
                if atype == b"moov":
                    f.seek(pos + hlen)
                    d = _mvhd_from_chunk(f.read(min(asize - hlen, cap)))
                    if d:
                        return d
                    break
                pos += asize
    except (OSError, struct.error):
        pass
    return None


# ---------- 文件名 / 文件夹 ----------

def name_dt(name):
    stem = os.path.splitext(name)[0]
    if stem.isdigit():
        return None                                     # 纯数字 ID 不猜
    m = re.search(r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})[_\-T ]?(\d{2})[-_]?(\d{2})[-_]?(\d{2})", stem)
    if m:
        try:
            return dt.datetime(*(int(x) for x in m.groups()))
        except ValueError:
            pass
    for m in re.finditer(r"(?<!\d)(\d{13})(?!\d)", stem):
        try:
            return dt.datetime.fromtimestamp(int(m.group(1)) / 1000)
        except (ValueError, OSError, OverflowError):
            continue
    m = re.search(r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})(?!\d)", stem)
    if m:
        try:
            return dt.datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    return None


def folder_dt(rel):
    for seg in rel.replace("\\", "/").split("/")[:-1]:
        m = re.search(r"(20\d{2})[-_年]?(\d{1,2})", seg)
        if m:
            try:
                return dt.datetime(int(m.group(1)), int(m.group(2)), 1)
            except ValueError:
                continue
    return None


# ---------- 主流程 ----------

def classify(ext):
    if ext in IMG_EXT:
        return "照片"
    if ext in VID_EXT:
        return "视频"
    return "其他"


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description="只读扫描媒体库并提取拍摄日期")
    ap.add_argument("roots", nargs="+", help="要扫描的根目录")
    ap.add_argument("--out", required=True, help="输出 CSV 路径")
    ap.add_argument("--hash", action="store_true", help="额外计算全量 MD5")
    ap.add_argument("--bad-mtime", default="", help="导出日/批量处理日，逗号分隔，命中则跳过 mtime 兜底")
    ap.add_argument("--exclude", default="", help="相对路径中含这些子串的目录跳过，逗号分隔")
    a = ap.parse_args()

    bad = {x.strip() for x in a.bad_mtime.split(",") if x.strip()}
    excl = [x.strip() for x in a.exclude.split(",") if x.strip()]
    rows = []
    for root in a.roots:
        root = os.path.abspath(root)
        for cur, dirs, files in os.walk(root):
            rel_dir = os.path.relpath(cur, root)
            dirs[:] = [d for d in dirs if not any(x in os.path.join(rel_dir, d) for x in excl)]
            for name in files:
                full = os.path.join(cur, name)
                rel = os.path.relpath(full, root)
                ext = os.path.splitext(name)[1].lower()
                kind = classify(ext)
                try:
                    st = os.stat(full)
                except OSError:
                    continue
                mt = dt.datetime.fromtimestamp(st.st_mtime)
                orig = digi = dt306 = None
                if kind == "照片":
                    orig, digi, dt306 = exif_dates(full)
                elif kind == "视频":
                    orig = mp4_ctime(full)

                date, src, conf = None, "", ""
                if orig:
                    date, src, conf = orig, "exif:orig" if kind == "照片" else "mvhd", "高"
                if not date:
                    date = name_dt(name)
                    if date:
                        src, conf = "filename", "高"
                if not date and digi:
                    date, src, conf = digi, "exif:digi", "高"
                if not date:
                    date = folder_dt(rel)
                    if date:
                        src, conf = "folder", "中"
                if not date and mt.strftime("%Y-%m-%d") not in bad:
                    date, src, conf = mt, "mtime(低可信)", "低"
                if not date and dt306:
                    date, src, conf = dt306, "exif:datetime306(低可信)", "低"

                rows.append({
                    "path": full, "root": root, "name": name, "ext": ext,
                    "kind": kind, "size": st.st_size,
                    "date": date.strftime("%Y-%m-%d %H:%M:%S") if date else "",
                    "date_source": src, "confidence": conf,
                    "mtime": mt.strftime("%Y-%m-%d %H:%M:%S"),
                    "md5": md5_of(full) if a.hash else "",
                })

    cols = ["path", "root", "name", "ext", "kind", "size",
            "date", "date_source", "confidence", "mtime", "md5"]
    with open(a.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    dated = sum(1 for r in rows if r["date"])
    low = sum(1 for r in rows if r["confidence"] == "低")
    print(f"扫描 {len(rows)} 个文件 -> {a.out}")
    print(f"定时成功 {dated} / 其中低可信 {low} / 无法定时 {len(rows)-dated}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
