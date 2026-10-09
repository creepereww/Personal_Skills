#!/usr/bin/env python3
"""导出原理图审查数据 —— 基于 easyeda-agent connector 的 typed 命令。

用法:
  python export_connection.py <outDir> [--project NAME] [--mode netlist|parts|connectivity|check|drc|all]

  netlist      官方 ENET 网表（`sch netlist` 产出的 .enet 工件）-> netlist.enet.json   ★连通性真值
  parts        原理图全量器件（含引脚+网络）-> sch_parts.json + sch_list.raw.json      ★查重复位号/游离器件
  connectivity 布局无关连通性 IR -> connectivity.json
  check        重建式逐项检查 -> sch_check.json（悬空脚/几何-网络不一致/零长线…，比 SDK DRC 细）
  drc          官方 SDK DRC -> sch_drc.json
  all = netlist + parts + connectivity + check（推荐）

前置: easyeda-agent daemon 已起、connector 已连接。本脚本会**自动把前台切到原理图页**
（sch_* 命令要求前台是原理图，否则报 "获取所有器件失败"）。
"""
import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eda_conn import activate_doc, run_cli, run_json  # noqa: E402


def do_netlist(out_dir, base):
    dst = os.path.join(out_dir, "netlist.enet.json")
    try:
        _proc, data = run_json(["sch", "netlist", *base])
        ap = (data or {}).get("artifactPath")
        if ap and os.path.isfile(ap):
            shutil.copyfile(ap, dst)
            print("OK  ENET 网表 -> %s  (%d 字节)" % (dst, os.path.getsize(dst)))
            return
        raise RuntimeError("sch netlist 未产出工件路径: %s" % json.dumps(data, ensure_ascii=False)[:200])
    except Exception as exc:
        # 回退：直接用官方 API 拿同一份 ENET 文本
        print("  sch netlist 不可用（%s），回退 debug exec getNetlistFile…" % exc)
        code = ("const f = await eda.sch_ManufactureData.getNetlistFile('netlist.enet.json');"
                " return await f.text();")
        _proc, data = run_json(["debug", "exec", "--code", code, "--timeout", "60", *base], timeout=90)
        txt = data if isinstance(data, str) else (data or {}).get("value", "")
        if not txt:
            raise RuntimeError("getNetlistFile 返回空")
        with open(dst, "w", encoding="utf-8") as fh:
            fh.write(txt)
        print("OK  ENET 网表(回退) -> %s  (%d 字符)" % (dst, len(txt)))


def do_parts(out_dir, base):
    _proc, data = run_json(["sch", "list", "--include-pins", *base])
    comps = (data or {}).get("components", [])
    with open(os.path.join(out_dir, "sch_list.raw.json"), "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    parts = [c for c in comps if c.get("componentType") == "part"]
    rows = []
    for c in parts:
        rows.append({
            "designator": c.get("designator") or "",
            "device": (c.get("device") or {}).get("name", ""),
            "value": (c.get("otherProperty") or {}).get("Value", ""),
            "footprint": (c.get("footprint") or {}).get("name", ""),
            "uniqueId": c.get("uniqueId") or "",
            "addIntoBom": bool(c.get("addIntoBom")),
            "addIntoPcb": bool(c.get("addIntoPcb")),
            "pins": [{"number": p.get("pinNumber"), "name": p.get("pinName"),
                      "net": p.get("net") or "", "noConnected": bool(p.get("noConnected"))}
                     for p in (c.get("pins") or [])],
        })
    dst = os.path.join(out_dir, "sch_parts.json")
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=2)
    print("OK  原理图器件 -> %s  (%d 个 part；另有 %d 个 netflag/sheet)"
          % (dst, len(rows), len(comps) - len(parts)))

    counts = {}
    for r in rows:
        counts[r["designator"]] = counts.get(r["designator"], 0) + 1
    for d, n in sorted(counts.items()):
        if n > 1:
            print("  ! 重复位号 %s x%d（会导致 connectivity 导出失败，须先改位号）" % (d, n))
    if [r for r in rows if not r["designator"]]:
        print("  ! 无位号器件: %d 个" % len([r for r in rows if not r["designator"]]))
    no_uid = [r["designator"] for r in rows if not r["uniqueId"]]
    if no_uid:
        print("  ! 无 UniqueId（ENET 会漏掉）: %s" % ", ".join(no_uid))
    no_pcb = [r["designator"] for r in rows if not r["addIntoPcb"]]
    if no_pcb:
        print("  ! 未转 PCB: %s" % ", ".join(no_pcb))


def do_connectivity(out_dir, base):
    proc, data = run_json(["sch", "connectivity", *base])
    if not isinstance(data, dict) or "components" not in data:
        raise RuntimeError("connectivity 返回异常: %s" % (proc.stdout or proc.stderr)[:200])
    dst = os.path.join(out_dir, "connectivity.json")
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    print("OK  连通性 IR -> %s  (%d 器件 / %d 网络)"
          % (dst, len(data.get("components", [])), len(data.get("nets", []))))


def do_check(out_dir, base):
    _proc, data = run_json(["sch", "check", "--json", *base])
    dst = os.path.join(out_dir, "sch_check.json")
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    s = (data or {}).get("summary", {})
    print("OK  逐项检查 -> %s  (total=%s passed=%s)" % (dst, s.get("total", "?"), (data or {}).get("passed")))
    hot = " ".join("%s=%s" % (k, v) for k, v in s.items()
                   if k != "total" and isinstance(v, int) and v > 0)
    if hot:
        print("  %s" % hot)


def do_drc(out_dir, base):
    _proc, data = run_json(["sch", "drc", "--json", *base])
    dst = os.path.join(out_dir, "sch_drc.json")
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    print("OK  SDK DRC -> %s" % dst)


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("out_dir")
    ap.add_argument("--project", default=None)
    ap.add_argument("--mode", default="netlist",
                    choices=["netlist", "parts", "connectivity", "check", "drc", "all"])
    args = ap.parse_args()

    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)
    base = ["--project", args.project] if args.project else []

    doc = activate_doc(args.project, "schematic")
    if doc:
        print("(前台已切到原理图: %s)" % doc["name"])

    is_all = args.mode == "all"
    if args.mode in ("netlist",) or is_all:
        do_netlist(out_dir, base)
    if args.mode in ("parts",) or is_all:
        do_parts(out_dir, base)
    if args.mode in ("connectivity",) or is_all:
        do_connectivity(out_dir, base)
    if args.mode in ("check",) or is_all:
        do_check(out_dir, base)
    if args.mode == "drc":
        do_drc(out_dir, base)


if __name__ == "__main__":
    main()
