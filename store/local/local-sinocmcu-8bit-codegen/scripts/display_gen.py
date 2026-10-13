#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""段码屏定义 -> DisplayScanService（LED 查理复用扫描）+ 符号/应用层宏。

干什么
    读段码屏定义表 segmap.csv，生成：
      1) DisplayScanService() —— 每轮把一条线拉低当共阴极，该阴极下"段位为 1"的
         各阳极线一起拉高，一次点亮多盏；
      2) 符号宏 / 应用层别名（可选，kind=icon / kind=app）。

怎么用
    python display_gen.py segmap.csv [-o display.c] [--pins pins.csv] [--tpl-dir templates]

前置
    - 线名（LED1..LEDn）来自 pinmap.py 出的 pins.csv（role 含 led，按 func 里的序号排）。
      `--pins` 给了就用它的线全集生成"全部释放"行并校验用到的线都存在。
    - **SEG <-> (阴线,阳线) 对应关系来自段码屏图纸/规格书，本脚本推不出来**（屏是外接件，
      网表里只有通孔焊盘，看不到屏内部接法）。

segmap.csv 列： kind,name,cathode,anode,bit,value,symbol,comment
    kind=scan  cathode=共阴极线  anode=阳极线  bit=段数据位名  symbol=符号集名  comment=注释
    kind=icon  name=宏名        value=定义值  comment=注释      （符号宏）
    kind=app   name=宏名        value=定义值  comment=注释      （应用层别名）

    bit 就是应用层段数据变量的位名（如 A0/B0/C0）；**同一 bit 允许出现在多行**
    （同一段位在不同阴极相位下点亮不同的灯，屏的接法决定）。
    **位名是自定义的**：约定「同一符号集（屏上的一个显示符号）放同一变量」，
    位名首字母 = 变量（A→Seg_SEGData1 / B→Seg_SEGData2 / C→Seg_SEGData3 …）。
    symbol 只用于生成文末「变量 ↔ 符号集」对照注释，可自由填（同一变量内多个值用 / 分隔）。
"""
import argparse
import csv
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

LINE_RE = re.compile(r"^(LED)(\d+)$")


def render(tpl_text, mapping):
    out = tpl_text
    for k, v in mapping.items():
        out = out.replace("{{%s}}" % k, str(v))
    left = re.findall(r"\{\{(\w+)\}\}", out)
    if left:
        raise SystemExit("模板里还有没被替换的占位符：%s" % ", ".join(sorted(set(left))))
    return out


def line_key(name):
    """LED 线名自然排序：LED2 排在 LED10 前面。"""
    m = LINE_RE.match(name or "")
    return (0, int(m.group(2))) if m else (1, 0)


def load_rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k, v in list(r.items()):
            r[k] = (v or "").strip()
        r.setdefault("symbol", "")
    if not rows:
        raise SystemExit("segmap.csv 是空的。")
    need = ("kind", "name", "cathode", "anode", "bit", "value", "comment")
    missing = [c for c in need if c not in rows[0]]
    if missing:
        raise SystemExit("segmap.csv 缺列：%s（应为 kind,name,cathode,anode,bit,value,symbol,comment）"
                         % ", ".join(missing))
    return rows


VAR_NAMES = {i: "Seg_SEGData%d" % (i + 1) for i in range(6)}


def var_map_block(scan):
    """按位名首字母（=变量）聚合，出「变量 ↔ 符号集 ↔ 段名」对照注释。

    同一 bit 出现在多行时只算一次段名；符号集名从 symbol 列取（同一变量可多个，用 / 分隔）。
    """
    order, groups = [], {}
    for r in scan:
        if not r["bit"]:
            continue
        var = r["bit"][0].upper()
        if var not in groups:
            groups[var] = {"segs": [], "symbols": []}
            order.append(var)
        g = groups[var]
        if r["name"] and r["name"] not in g["segs"]:
            g["segs"].append(r["name"])
        for s in [x.strip() for x in (r["symbol"] or "").split("/") if x.strip()]:
            if s not in g["symbols"]:
                g["symbols"].append(s)

    lines = []
    for var in order:
        g = groups[var]
        if not g["segs"] and not g["symbols"]:
            continue
        varname = VAR_NAMES.get(ord(var) - ord("A"), "Seg_SEGData?")
        tail = " : " + ",".join(g["segs"]) if g["segs"] else ""
        lines.append("// %s (%s0-%s7) = %s%s"
                     % (varname, var, var, "/".join(g["symbols"]) or "-", tail))
    return "\n".join(lines)


def led_lines_from_pins(pins_csv):
    lines = []
    with Path(pins_csv).open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            role = (row.get("role") or "").strip().lower()
            if "led" in {x.strip() for x in role.split(",")}:
                lines.append((row.get("func") or "").strip())
    return lines


def main():
    ap = argparse.ArgumentParser(description="段码屏定义 -> DisplayScanService + 符号/应用层宏")
    ap.add_argument("segmap", help="segmap.csv")
    ap.add_argument("-o", "--out", help="输出 .c 路径（默认：segmap.csv 同目录/display.c）")
    ap.add_argument("--pins", help="pins.csv：用来取 LED 线全集并校验线名")
    ap.add_argument("--tpl-dir", default=str(Path(__file__).resolve().parent.parent / "templates"),
                    help="模板目录（默认 skill 的 templates/）")
    args = ap.parse_args()

    tpl_dir = Path(args.tpl_dir)
    for name in ("display_varmap.c.tpl", "display_scan.c.tpl", "display_macros.c.tpl"):
        if not (tpl_dir / name).is_file():
            raise SystemExit("模板缺失：%s" % (tpl_dir / name))

    rows = load_rows(args.segmap)
    scan = [r for r in rows if r["kind"].lower() == "scan"]
    icons = [r for r in rows if r["kind"].lower() == "icon"]
    apps = [r for r in rows if r["kind"].lower() == "app"]
    for r in rows:
        if r["kind"].lower() not in ("scan", "icon", "app"):
            raise SystemExit("未知 kind '%s'（应为 scan/icon/app）" % r["kind"])
    if not scan:
        raise SystemExit("segmap.csv 里没有 kind=scan 的行，没东西可生成。")

    known = led_lines_from_pins(args.pins) if args.pins else []
    if known:
        bad = sorted({x for r in scan for x in (r["cathode"], r["anode"]) if x not in known})
        if bad:
            raise SystemExit("segmap.csv 用到 pins.csv 里不存在的线：%s（现有 %s）"
                             % (", ".join(bad), ", ".join(sorted(known, key=line_key))))

    # 阴极顺序 = 线名自然序；"全部释放"行用 pins 全集（没有就用表里出现过的线）
    cathodes = sorted({r["cathode"] for r in scan}, key=line_key)
    release = sorted(set(known) | {r["cathode"] for r in scan} | {r["anode"] for r in scan},
                     key=line_key)
    if not known:
        print("提示：没给 --pins，\"全部释放\"行只用表里出现过的线（%s）"
              % ", ".join(release))

    for name in release:
        if not LINE_RE.match(name):
            raise SystemExit("线名 '%s' 不像 LED 线（应形如 LED1）" % name)

    cases = []
    for i, cat in enumerate(cathodes, start=1):
        body = ["case %d:  //公共阴极PIN%d" % (i, i), "%s_OL;" % cat]
        for r in scan:
            if r["cathode"] != cat:
                continue
            if not r["bit"]:
                raise SystemExit("scan 行缺 bit（阴线 %s / 阳线 %s）" % (cat, r["anode"]))
            line = "if (%s) { %s_OH; }" % (r["bit"], r["anode"])
            body.append((line + "  //" + r["comment"]) if r["comment"] else line)
        if i == len(cathodes):
            body.append("SEG_Cnt = 0;")
        body.append("break;")
        cases.append("\n".join(body))

    nothing = [c for c in cathodes if not [r for r in scan if r["cathode"] == c]]
    if nothing:
        print("!! 这些阴极没有任何段：%s" % ", ".join(nothing))

    parts = []
    varmap = var_map_block(scan)
    if varmap:
        parts.append(render((tpl_dir / "display_varmap.c.tpl").read_text(encoding="utf-8"), {
            "VAR_ROWS": varmap,
        }))
    parts.append(render((tpl_dir / "display_scan.c.tpl").read_text(encoding="utf-8"), {
        "ALL_RELEASE": ";".join("%s_IN" % n for n in release),
        "SCAN_CASES": "\n".join(cases),
    }))

    if icons or apps:
        def macro_block(items):
            texts = ["#define %s %s" % (r["name"], r["value"]) for r in items]
            pad = max([len(x) for x in texts] + [0]) + 1
            return "\n".join(t.ljust(pad) + "//" + r["comment"]
                             for t, r in zip(texts, items))
        parts.append(render((tpl_dir / "display_macros.c.tpl").read_text(encoding="utf-8"), {
            "ICON_MACROS": macro_block(icons),
            "APP_MACROS": macro_block(apps),
        }))

    text = "\n".join(p.rstrip("\n") for p in parts if p) + "\n"
    out = Path(args.out) if args.out else Path(args.segmap).with_name("display.c")
    out.write_text(text, encoding="utf-8", newline="\n")

    print("阴极 %d 个，段 %d 条（其中重复段位 %d 个）；线 %d 根"
          % (len(cathodes), len(scan),
             len(scan) - len({r["bit"] for r in scan}), len(release)))
    print("已写出: %s" % out)
    print("\n下一步：回读该文件，对着段码屏图纸核每一盏灯的（阴线,阳线）。")


if __name__ == "__main__":
    main()
