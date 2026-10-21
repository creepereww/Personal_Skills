#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pins.csv -> INIT_GPIO + 宏（严格按 templates/ 版式）。

干什么
    读引脚配置表 pins.csv，算出 IOP/OEP/PUP/PDP 寄存器值，生成
    输入宏 / 输出宏 / 屏幕(LED 查理复用)宏 / 雾化 PWM 通道选择，
    套 templates/*.tpl 拼成一个 .c。

怎么用
    python gpio_gen.py pins.csv [-o out.c] [--tpl-dir templates] [--title "..."]
    python gpio_gen.py --check out.c      # 只做自检：中断宏调用点 vs 定义名是否逐字一致

前置
    pins.csv 由 pinmap.py 生成，且判定列（func/dir/init/pull/irq/role）已人工确认。

口径（硬性）
    - 未出现在 CSV 的 IO 一律 output、低电平。
    - Pxy -> 寄存器 x 的第 y 位；OEP=1 为 out。
    - LED 是查理复用：一盏灯跨两根线，宏只提供"线 k 高/低/输出/高阻"。
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

PORT_RE = re.compile(r"^P([0-2])([0-7])$")
PWM_RE = re.compile(r"PWM(3A|3B|3C|1|2)")
# 用户模板里有两种命名：`<stem>_INTERRUPT_ENABLE`（旧）与 `<stem>_ENABLE`（如 KEY_CHANGE_ENABLE）。
# 两种都要认，否则 --check 会漏检，宏名不一致就抓不到了。
IRQ_DEF_RE = re.compile(r"#define\s+(\w+?_(?:INTERRUPT_)?(?:ENABLE|DISABLE))\b")
IRQ_CALL_RE = re.compile(r"^\s*(\w+?_(?:INTERRUPT_)?(?:ENABLE|DISABLE))\s*;")

PWM_KEYS = ["T1", "T2", "T3A", "T3B", "T3C"]
REGS = ["0", "1", "2"]


def render(tpl_text, mapping):
    """{{KEY}} 替换；有未消费的占位符就报错（避免模板改了脚本没跟上）。"""
    out = tpl_text
    for k, v in mapping.items():
        out = out.replace("{{%s}}" % k, str(v))
    left = re.findall(r"\{\{(\w+)\}\}", out)
    if left:
        raise SystemExit("模板里还有没被替换的占位符：%s" % ", ".join(sorted(set(left))))
    return out


def led_index(row):
    m = re.search(r"(\d+)", row.get("func", "") or "")
    return int(m.group(1)) if m else 999


def roles_of(row):
    """role 列支持逗号分隔（一个脚可同时进多段，如 'out,led'）。"""
    return {x.strip().lower() for x in (row.get("role") or "").split(",") if x.strip()}


def irq_stem(row):
    """中断宏主干：irq_macro 非空则用它（完整主干），否则 func + '_INTERRUPT'。

    GPIO 脚 k 的中断使能宏形如 <主干>_ENABLE / <主干>_DISABLE，
    即模板里的 KEY_MI_INTERRUPT_ENABLE / USB_INTERRUPT_ENABLE。
    """
    return row["irq_macro"] or (row["func"] + "_INTERRUPT")


def load_rows(csv_path):
    with Path(csv_path).open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k, v in list(r.items()):
            r[k] = (v or "").strip()
    return rows


def build_registers(rows):
    """返回 (iop, oep, pup, pdp, by_reg_pins)。未在表内的脚默认 output+低。"""
    iop = {r: 0 for r in REGS}
    oep = {r: 0xFF for r in REGS}   # 未用默认 output
    pup = {r: 0 for r in REGS}
    pdp = {r: 0 for r in REGS}
    pins = {r: [] for r in REGS}

    for row in rows:
        m = PORT_RE.match(row["port"])
        if not m:
            raise SystemExit("非法端口 '%s'（应为 P00..P21）" % row["port"])
        reg, bit = m.group(1), int(m.group(2))
        pins[reg].append((row["port"], row))

        is_out = row["dir"].strip().lower() != "in"
        if is_out:
            oep[reg] |= (1 << bit)
            if row["init"] == "1":
                iop[reg] |= (1 << bit)
            else:
                iop[reg] &= ~(1 << bit)
        else:
            oep[reg] &= ~(1 << bit)
            iop[reg] &= ~(1 << bit)

        p = row["pull"].strip().lower()
        if p == "up":
            pup[reg] |= (1 << bit)
        elif p == "down":
            pdp[reg] |= (1 << bit)

    return iop, oep, pup, pdp, pins


def fmt(v):
    return "0x%02X" % v


def pin_list(pins, pred):
    hit = [name for name, row in pins if pred(row)]
    return "/".join(sorted(hit))


def render_init_gpio(rows, tpl, title):
    iop, oep, pup, pdp, pins = build_registers(rows)
    mapping = {"TITLE": title}
    for r in REGS:
        ins = pin_list(pins[r], lambda x: x["dir"].lower() == "in")
        his = pin_list(pins[r], lambda x: x["dir"].lower() != "in" and x["init"] == "1")
        mapping["IOP%s" % r] = fmt(iop[r])
        mapping["C_IOP%s" % r] = ("//%s output high；其余 output low" % his) if his \
            else "// 全部 output low"
        mapping["OEP%s" % r] = fmt(oep[r])
        mapping["C_OEP%s" % r] = ("//%s input；其余 output" % ins) if ins else "// 全部 output"
        mapping["PUP%s" % r] = fmt(pup[r])
        ups = pin_list(pins[r], lambda x: x["pull"].lower() == "up")
        mapping["C_PUP%s" % r] = ("//%s pull-up" % ups) if ups else "//"
        mapping["PDP%s" % r] = fmt(pdp[r])
        dns = pin_list(pins[r], lambda x: x["pull"].lower() == "down")
        mapping["C_PDP%s" % r] = ("//%s pull-down" % dns) if dns else "//"

    calls = []
    for row in rows:
        if row["irq"].lower() == "yes":
            calls.append("%s_ENABLE;   // %s" % (irq_stem(row), row["note"] or row["func"]))
    mapping["IRQ_CALLS"] = "\n".join(calls)
    return render(tpl, mapping)


def render_io_macros(rows, tpl):
    def comment(row):
        text = row["note"] or row["func"]
        if "pwm" in roles_of(row):
            m = PWM_RE.search(row["pin_name"])
            if m:
                text += "  " + m.group(0)
        return text

    def width(accepted):
        texts = ["#define PIN_%s %sD" % (r["func"], r["port"])
                 for r in rows if roles_of(r) & accepted]
        return max([len(x) for x in texts] + [24]) + 1

    def block(accepted, pad):
        """先出全部 PIN_ 宏，再出全部中断宏（照模板版式）。

        accepted 是 role 集合：输出段同时收 'out' 与 'pwm'（加热脚的角色是 pwm）。
        加热使能宏固定出满 HEAT1/HEAT2/HEAT3 三个，没用到的填盲变量 dummy_pin。
        """
        pins, irqs = [], []
        heat_used = 0
        last_pwm = -1
        for row in rows:
            rs = roles_of(row)
            if not (rs & accepted):
                continue
            text = "#define PIN_%s %sD" % (row["func"], row["port"])
            pins.append(text.ljust(pad) + "// " + comment(row))
            if "pwm" in rs:
                heat_used += 1
                last_pwm = len(pins) - 1
            if "in" in accepted and row["irq"].lower() == "yes":
                stem = irq_stem(row)
                e = "#define %s_ENABLE" % stem
                d = "#define %s_DISABLE" % stem
                w = max(len(e), len(d)) + 1
                irqs.append(e.ljust(w) + "%sKE = 1" % row["port"])
                irqs.append(d.ljust(w) + "%sKE = 0" % row["port"])

        # 加热使能：HEAT1..HEAT3 三个都写上，缺的填 dummy_pin（用户口径）
        # 紧跟在最后一个 pwm 宏后面，不跟到段末
        if "pwm" in accepted and heat_used and heat_used < 3:
            at = last_pwm + 1
            for n in range(heat_used + 1, 4):
                text = "#define PIN_HEAT%d_CTL dummy_pin" % n
                pins.insert(at, text.ljust(pad) + "// 未用到的话使用盲变量")
                at += 1

        return "\n".join(pins + irqs)

    return render(tpl, {"IN_MACROS": block({"in"}, width({"in"})),
                        "OUT_MACROS": block({"out", "pwm"}, width({"out", "pwm"}))})


def render_led(rows, tpl):
    led_rows = sorted([r for r in rows if "led" in roles_of(r)], key=led_index)
    if not led_rows:
        return ""
    names = []
    for row in led_rows:
        m = re.search(r"(\d+)", row["func"])
        names.append(("LED%s" % m.group(1)) if m else None)
    if any(n is None for n in names):
        raise SystemExit("role=led 的脚，func 里必须带序号（如 LED1），当前: %s"
                         % ", ".join(r["func"] for r in led_rows))
    if len(names) != len(set(names)):
        raise SystemExit("LED 序号重复：%s" % ", ".join(names))
    if len(set(r["port"] for r in led_rows)) != len(led_rows):
        raise SystemExit("LED 线端口重复，查理复用每根线只能出现一次")

    lines = []
    for suffix, body in (("IN", "%sOE = 0"), ("OUT", "%sOE = 1"),
                         ("H", "%sD = 1"), ("L", "%sD = 0")):
        for name, row in zip(names, led_rows):
            lines.append("#define  %s_%s    %s//%s"
                         % (name, suffix, body % row["port"], row["net"] or row["func"]))
    for suffix, ref in (("OH", "%s_H;%s_OUT"), ("OL", "%s_L;%s_OUT")):
        for name in names:
            lines.append("#define %s_%s \t%s" % (name, suffix, ref % (name, name)))

    header = ("// %d 根线：" % len(names)) + " ".join(
        "%s=%s(%s)" % (n, r["port"], r["net"] or "-") for n, r in zip(names, led_rows))
    return render(tpl, {"LED_HEADER": header, "LED_MACROS": "\n".join(lines)})


def render_smoke_pwm(rows, tpl):
    on = set()
    for row in rows:
        if "pwm" not in roles_of(row):
            continue
        for m in PWM_RE.finditer(row["pin_name"]):
            on.add("T" + m.group(1))
    mapping = {k: (1 if k in on else 0) for k in PWM_KEYS}
    return render(tpl, mapping)


def check_file(path):
    """自检：中断宏的调用点是否都有对应定义。

    不用非零退出码表示失败（宿主工具遇非零码会丢 stdout）—— 结论写在正文，
    末行固定输出 STATUS=OK / STATUS=MISMATCH 供自动化解析。
    """
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    defined = set()
    for m in IRQ_DEF_RE.finditer(text):
        defined.add(m.group(1))
    called = set()
    for line in text.splitlines():
        m = IRQ_CALL_RE.match(line)
        if m:
            called.add(m.group(1))
    missing = sorted(called - defined)
    unused = sorted(defined - called)
    print("已定义中断宏 %d 个，被调用 %d 个" % (len(defined), len(called)))
    if missing:
        print("!! 调用但没有定义（会编译不过）：%s" % ", ".join(missing))
    if unused:
        print("  定义了但没调用：%s" % ", ".join(unused))
    print("STATUS=%s" % ("MISMATCH" if missing else "OK"))
    return missing


def main():
    ap = argparse.ArgumentParser(description="pins.csv -> INIT_GPIO + 宏（套 templates/）")
    ap.add_argument("csv", nargs="?", help="pins.csv")
    ap.add_argument("-o", "--out", help="输出 .c 路径（默认：pins.csv 同目录/INIT_GPIO.c）")
    ap.add_argument("--tpl-dir", default=str(Path(__file__).resolve().parent.parent / "templates"),
                    help="模板目录（默认 skill 的 templates/）")
    ap.add_argument("--title", default="", help="文件头注释，如 'PXS-FD07 GPIO 初始化（MCU: MC9959B0ZQ）'")
    ap.add_argument("--check", help="只做自检：检查该 .c 的中断宏调用点 vs 定义名")
    args = ap.parse_args()

    if args.check:
        check_file(args.check)
        return
    if not args.csv:
        raise SystemExit("需要 pins.csv（或用 --check <file.c> 做自检）")

    tpl_dir = Path(args.tpl_dir)
    for name in ("init_gpio.c.tpl", "io_macros.c.tpl", "led_charlie.c.tpl", "smoke_pwm.c.tpl"):
        if not (tpl_dir / name).is_file():
            raise SystemExit("模板缺失：%s" % (tpl_dir / name))

    rows = load_rows(args.csv)
    title = args.title or "GPIO 初始化"
    parts = [
        render_init_gpio(rows, (tpl_dir / "init_gpio.c.tpl").read_text(encoding="utf-8"), title),
        render_io_macros(rows, (tpl_dir / "io_macros.c.tpl").read_text(encoding="utf-8")),
        render_led(rows, (tpl_dir / "led_charlie.c.tpl").read_text(encoding="utf-8")),
        render_smoke_pwm(rows, (tpl_dir / "smoke_pwm.c.tpl").read_text(encoding="utf-8")),
    ]
    text = "\n".join(p.rstrip("\n") for p in parts if p) + "\n"

    out = Path(args.out) if args.out else Path(args.csv).with_name("INIT_GPIO.c")
    out.write_text(text, encoding="utf-8", newline="\n")

    iop, oep, pup, pdp, pins = build_registers(rows)
    print("寄存器： IOP=%s/%s/%s  OEP=%s/%s/%s  PUP=%s/%s/%s  PDP=%s/%s/%s"
          % (fmt(iop["0"]), fmt(iop["1"]), fmt(iop["2"]),
             fmt(oep["0"]), fmt(oep["1"]), fmt(oep["2"]),
             fmt(pup["0"]), fmt(pup["1"]), fmt(pup["2"]),
             fmt(pdp["0"]), fmt(pdp["1"]), fmt(pdp["2"])))
    print("已写出: %s" % out)
    print()
    check_file(str(out))
    print("\n下一步：回读该文件，逐脚比对网表（方向/初值/网络），确认无误再并入工程。")


if __name__ == "__main__":
    main()
