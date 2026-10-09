#!/usr/bin/env python3
"""导出 PCB 审查数据 —— 基于 easyeda-agent connector 的 typed 命令。

用法:
  python export_pcb.py <outDir> [--project NAME] [--mode dump|drc|check|outline|nets|board|all]

  dump    板子只读几何快照（器件+焊盘+板框+铜/过孔/铺铜）-> pcb_dump.json   ★含网络名的权威几何
  drc     规范化 DRC 违规（一行一条，单位 mil）-> pcb_drc.json
  check   DFM 审计（dangling/acute/clearance/decapTooFar/powerNotPoured/…）-> pcb_check.json
  outline 板框（含真实中心线尺寸 + 渲染 bbox）-> pcb_outline.json
  nets    网络清单（名/长度/颜色）-> pcb_nets.json
  board   Board 绑定（原理图↔PCB 关联）-> pcb_board.json
  all = dump + drc + check + outline + nets + board（推荐）

前置: easyeda-agent daemon 已起、connector 已连接。本脚本会**自动把前台切到 PCB**
（pcb dump / outline 要求前台是 PCB，否则板框读回 null）。
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eda_conn import activate_doc, run_cli, run_json  # noqa: E402


def do_dump(out_dir, base):
    dst = os.path.join(out_dir, "pcb_dump.json")
    proc = run_cli(["pcb", "dump", "--include-copper", "--out", dst, *base], timeout=300)
    if not os.path.isfile(dst):
        raise RuntimeError("pcb dump 未产出文件: %s" % (proc.stdout or proc.stderr)[:200])
    with open(dst, encoding="utf-8") as fh:
        d = json.load(fh)
    outline = d.get("outline") or {}
    print("OK  板子几何 -> %s  (%d 器件, outline=%s, %d 字节)"
          % (dst, len(d.get("components", [])), outline.get("format", "none"), os.path.getsize(dst)))


def do_drc(out_dir, base):
    _proc, data = run_json(["pcb", "drc", "--json", *base], timeout=180)
    dst = os.path.join(out_dir, "pcb_drc.json")
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    n = len(data) if isinstance(data, list) else (data or {}).get("violations", "?")
    print("OK  PCB DRC -> %s  (passed=%s, violations=%s)"
          % (dst, (data or {}).get("passed") if isinstance(data, dict) else "?", n))


def do_check(out_dir, base):
    _proc, data = run_json(["pcb", "check", "--json", *base], timeout=180)
    dst = os.path.join(out_dir, "pcb_check.json")
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    s = (data or {}).get("summary", {})
    print("OK  DFM 审计 -> %s  (passed=%s)" % (dst, (data or {}).get("passed")))
    hot = " ".join("%s=%s" % (k, v) for k, v in s.items() if isinstance(v, int) and v > 0)
    if hot:
        print("  %s" % hot)


def simple(out_dir, base, cmd, fname, label):
    _proc, data = run_json([*cmd, *base], timeout=180)
    dst = os.path.join(out_dir, fname)
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    print("OK  %s -> %s" % (label, dst))


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("out_dir")
    ap.add_argument("--project", default=None)
    ap.add_argument("--mode", default="all",
                    choices=["dump", "drc", "check", "outline", "nets", "board", "all"])
    args = ap.parse_args()

    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)
    base = ["--project", args.project] if args.project else []

    doc = activate_doc(args.project, "pcb")
    if doc:
        print("(前台已切到 PCB: %s)" % doc["name"])

    is_all = args.mode == "all"
    if args.mode in ("dump",) or is_all:
        do_dump(out_dir, base)
    if args.mode in ("drc",) or is_all:
        do_drc(out_dir, base)
    if args.mode in ("check",) or is_all:
        do_check(out_dir, base)
    if args.mode in ("outline",) or is_all:
        simple(out_dir, base, ["pcb", "outline-get"], "pcb_outline.json", "板框")
    if args.mode in ("nets",) or is_all:
        simple(out_dir, base, ["pcb", "nets"], "pcb_nets.json", "网络清单")
    if args.mode in ("board",) or is_all:
        simple(out_dir, base, ["pcb", "board-info"], "pcb_board.json", "Board 绑定")


if __name__ == "__main__":
    main()
