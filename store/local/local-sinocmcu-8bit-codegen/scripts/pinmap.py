#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""网表 -> MCU 引脚配置表（pins.csv）。

干什么
    读嘉立创 EDA 网表，找到 MCU 器件，把每根 GPIO 拉成一行：
    port / phys / pin_name / net + 判定列（func,dir,init,pull,irq,irq_macro,role,note）。
    判定列按网络名做**启发式预填**，再由人或模型确认（这是流程里唯一要动脑的一步）。

怎么用
    python pinmap.py <netlist.enet.json> [-o pins.csv] [--mcu U3] [--device-regex "^MC\\d+"]
    不给 -o 时默认写到网表同目录的 pins.csv。

前置
    网表用 local-jlceda-design-review 的取数脚本拿：
        python export_connection.py <工作目录>/<项目>/ --project <项目> --mode netlist
    本脚本只读文件，不连 EDA。

认两种输入
    netlist.enet.json  —— ENET 网表，顶层 dict，components 是 dict
    sch_parts.json     —— `sch list` 导出，顶层是 list
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# 引脚名里的端口：最后一个合法的 P[0-2][0-7]（避开 [PCK0]/[PDT1] 这类）
PORT_RE = re.compile(r"(?<![A-Za-z0-9])P([0-2])([0-7])(?![0-9])")
PWM_RE = re.compile(r"PWM(3A|3B|3C|1|2)")
ALT_SPLIT_RE = re.compile(r"[/\[\]]+")

COLUMNS = ["port", "phys", "pin_name", "net", "func", "dir", "init",
           "pull", "irq", "irq_macro", "role", "note"]


def port_of(pin_name):
    """引脚名 -> 'Pxy' 或 None。"""
    ms = list(PORT_RE.finditer(pin_name or ""))
    if not ms:
        return None
    m = ms[-1]
    return "P%s%s" % (m.group(1), m.group(2))


def alt_funcs(pin_name):
    """引脚名 -> 复用功能列表，如 ['P06','PWM2','AN6']。"""
    parts = [p.strip() for p in ALT_SPLIT_RE.split(pin_name or "")]
    return [p for p in parts if p]


def load_components(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    comps = []
    if isinstance(data, dict) and isinstance(data.get("components"), dict):
        for _key, v in data["components"].items():
            p = v.get("props") or {}
            pins = []
            for num, pin in (v.get("pinInfoMap") or {}).items():
                pins.append({
                    "number": str(pin.get("number", num)),
                    "name": pin.get("name", "") or "",
                    "net": pin.get("net", "") or "",
                })
            comps.append({
                "designator": p.get("Designator", "") or "",
                "device": p.get("DeviceName") or p.get("Value") or "",
                "pins": pins,
            })
    elif isinstance(data, list):
        for v in data:
            comps.append({
                "designator": v.get("designator", "") or "",
                "device": v.get("device") or v.get("value") or "",
                "pins": [{
                    "number": str(p.get("number", "")),
                    "name": p.get("name", "") or "",
                    "net": p.get("net", "") or "",
                } for p in (v.get("pins") or [])],
            })
    else:
        raise SystemExit("无法识别的网表格式：顶层应是含 components(dict) 的 dict，或器件 list。")
    return comps


def find_mcu(comps, mcu, device_regex):
    if mcu:
        for c in comps:
            if c["designator"].upper() == mcu.upper():
                return c
        raise SystemExit("网表里没找到位号 %s。可用位号：%s"
                         % (mcu, ", ".join(sorted(x["designator"] for x in comps))))
    rx = re.compile(device_regex, re.I)
    best, best_score = None, -1
    for c in comps:
        n = sum(1 for p in c["pins"] if port_of(p["name"]))
        if n < 8:
            continue
        score = n * 10 + (5 if rx.search(c["device"] or "") else 0)
        if score > best_score:
            best, best_score = c, score
    if not best:
        raise SystemExit("没找到像 MCU 的器件（引脚名含 Pxx 的脚不足 8 个）。用 --mcu 指定位号。")
    return best


def guess(net):
    """按网络名预填判定列。返回 dict（缺省=未用/待确认）。"""
    n = (net or "").strip().upper()
    g = {"func": "", "dir": "out", "init": "0", "pull": "",
         "irq": "no", "irq_macro": "", "role": "", "note": ""}

    m = re.fullmatch(r"LED_PIN(\d+)", n)
    if m:
        g.update(func="LED%s" % m.group(1), dir="out", init="0",
                 role="led", note="查理复用线")
        return g

    if "PWM_OUT_CTL" in n:
        m = re.search(r"(\d+)$", n)
        g.update(func="HEAT%s_CTL" % (m.group(1) if m else ""), dir="out",
                 init="1", role="pwm", note="加热使能")
        return g

    if n in ("KEY_MI", "MI") or n.endswith("_MI"):
        g.update(func="KEY_MI", dir="in", init="0", irq="yes",
                 role="in", note="咪头输入")
        return g

    if any(k in n for k in ("CHG", "VBUS", "USB")):
        # 模板沿革：PIN_USB_IN 配的中断宏是 USB_INTERRUPT_ENABLE（不是 USB_IN_INTERRUPT），
        # 用 irq_macro 显式对齐，别让它自动拼成 "func + _INTERRUPT"。
        g.update(func="USB_IN", dir="in", init="0", pull="down", irq="yes",
                 irq_macro="USB_INTERRUPT", role="in", note="USB/VBUS检测")
        return g

    if n in ("", "-", "NC"):
        g.update(note="悬空/未用")
        return g

    g.update(note="待确认")
    return g


def main():
    ap = argparse.ArgumentParser(description="嘉立创网表 -> MCU 引脚配置表 pins.csv")
    ap.add_argument("netlist", help="netlist.enet.json 或 sch_parts.json")
    ap.add_argument("-o", "--out", help="输出 CSV 路径（默认：网表同目录/pins.csv）")
    ap.add_argument("--mcu", help="MCU 位号，如 U3（不填则自动识别）")
    ap.add_argument("--device-regex", default=r"^MC\d+",
                    help="自动识别 MCU 时的器件名正则（默认 ^MC\\d+）")
    args = ap.parse_args()

    comps = load_components(args.netlist)
    mcu = find_mcu(comps, args.mcu, args.device_regex)

    rows, skipped = [], []
    for p in mcu["pins"]:
        port = port_of(p["name"])
        if not port:
            skipped.append(p)
            continue
        g = guess(p["net"])
        rows.append({
            "port": port, "phys": p["number"], "pin_name": p["name"],
            "net": p["net"], **g,
        })

    rows.sort(key=lambda r: (r["port"][1], r["port"][2]))
    seen = {}
    for r in rows:
        if r["port"] in seen:
            print("!! 端口重复：%s（脚 %s 与 %s）—— ENET 漏器件时会这样，需人工确认"
                  % (r["port"], seen[r["port"]], r["phys"]))
        seen[r["port"]] = r["phys"]

    out = Path(args.out) if args.out else Path(args.netlist).with_name("pins.csv")
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)

    print("MCU: %s (%s)  |  GPIO: %d 根  |  非 GPIO 脚: %d"
          % (mcu["designator"], mcu["device"], len(rows), len(skipped)))
    if skipped:
        print("  非 GPIO: " + ", ".join("脚%s %s" % (p["number"], p["name"]) for p in skipped))
    print()
    print("%-5s %-5s %-26s %-16s %-8s %-4s %-4s %-5s %-4s %s"
          % ("port", "phys", "pin_name", "net", "func", "dir", "init", "pull", "irq", "role"))
    for r in rows:
        print("%-5s %-5s %-26s %-16s %-8s %-4s %-4s %-5s %-4s %s"
              % (r["port"], r["phys"], r["pin_name"][:26], r["net"][:16],
                 r["func"] or r["note"][:8], r["dir"], r["init"], r["pull"] or "-",
                 r["irq"], r["role"] or "-"))
    print()
    print("已写出: %s" % out)
    print("下一步：确认 func/dir/init/pull/irq/role 各列，再跑 gpio_gen.py。")


if __name__ == "__main__":
    main()
