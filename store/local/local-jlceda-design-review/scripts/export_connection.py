#!/usr/bin/env python3
"""导出原理图审查数据 —— 基于 easyeda-agent connector 的 typed 命令。

用法:
  python export_connection.py <outDir> [--project NAME] [--mode netlist|parts|connectivity|check|drc|all]
                              [--include-shielded]

  netlist      官方 ENET 网表（`sch netlist` 产出的 .enet 工件）-> netlist.enet.json   ★连通性真值
  parts        原理图器件（默认已排除屏蔽区）-> sch_parts.json + sch_parts_all.json + sch_list.raw.json
  connectivity 布局无关连通性 IR -> connectivity.json（命令失败时自动用 ENET 合成）
  check        重建式逐项检查 -> sch_check.json（悬空脚/几何-网络不一致/零长线…，比 SDK DRC 细）
  drc          官方 SDK DRC -> sch_drc.json
  all = netlist + parts + connectivity + check（推荐）

**屏蔽区域处理**（connector 的三个命令口径不一致，这里统一）：
  - `sch netlist`(ENET)       排除屏蔽区 ✅
  - `sch list`                不排除 ❌
  - `sch connectivity`        不排除，且屏蔽区里的重名件会让它整体拒绝导出 ❌

  本脚本的做法：
  1. 先拿 ENET，用它的 `props["Unique ID"]` 集合作为"有效器件"白名单
     （ENET 是编译器视角，屏蔽区不进网表）；
  2. `parts` 只把白名单里的写进 `sch_parts.json`；全量另存 `sch_parts_all.json`
     （每条带 `netlisted` 字段），需要看屏蔽区就加 `--include-shielded`；
  3. `connectivity` 先试官方命令，失败时**直接由 ENET 合成同 schema 的 IR**
     —— 天然排除屏蔽区，也绕开"重名件直接拒绝"这个死结。

前置: easyeda-agent daemon 已起、connector 已连接。本脚本会**自动把前台切到原理图页**
（sch_* 命令要求前台是原理图，否则报 "获取所有器件失败"）。
"""
import argparse
import hashlib
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eda_conn import activate_doc, run_cli, run_json  # noqa: E402

POWER_NETS = {"GND", "VBAT", "VBUS", "+3.3", "VCC", "VDD", "+5V", "VSS"}


def _enet_path(out_dir):
    return os.path.join(out_dir, "netlist.enet.json")


def _load_enet(out_dir):
    """读 ENET；返回 (uniqueId 白名单, enet dict)。没有文件时返回 (None, None)。"""
    p = _enet_path(out_dir)
    if not os.path.isfile(p):
        return None, None
    with open(p, encoding="utf-8") as fh:
        enet = json.load(fh)
    ids = set()
    for v in (enet.get("components") or {}).values():
        uid = (v.get("props") or {}).get("Unique ID") or ""
        if uid:
            ids.add(uid)
    return ids, enet


def _ensure_netlist(out_dir, base):
    """parts/connectivity 依赖 ENET 做屏蔽区过滤 —— 缺了就先拉一次。"""
    if os.path.isfile(_enet_path(out_dir)):
        return
    print("  (未见 ENET，先导出一次用于屏蔽区过滤)")
    do_netlist(out_dir, base)


def do_netlist(out_dir, base):
    dst = _enet_path(out_dir)
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


def fetch_parts(base):
    """先读器件清单。

    必须**在 netlist 导出之前**调用：`sch netlist`（及其 debug exec 回退）会把文档留在
    "unknown or non-sync transaction" 状态，随后 `sch list` 会返回 0 个器件。
    """
    _proc, data = run_json(["sch", "list", "--include-pins", *base])
    comps = (data or {}).get("components", [])
    if not comps:
        # 连接器偶发空返回，稍等再试一次
        import time
        time.sleep(1.5)
        _proc, data = run_json(["sch", "list", "--include-pins", *base])
        comps = (data or {}).get("components", [])
        if not comps:
            print("  ! sch list 返回 0 器件（文档可能处于非同步状态，试 `easyeda doc reload`）")
    return data


def do_parts(out_dir, data, include_shielded=False):
    comps = (data or {}).get("components", [])
    with open(os.path.join(out_dir, "sch_list.raw.json"), "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)

    ids, _enet = _load_enet(out_dir)
    parts = [c for c in comps if c.get("componentType") == "part"]

    rows_all = []
    for c in parts:
        uid = c.get("uniqueId") or ""
        # 无 UniqueId 的器件 ENET 本来就漏，不能断定它在屏蔽区 —— 保留并标注
        netlisted = True if (ids is None or not uid) else (uid in ids)
        rows_all.append({
            "designator": c.get("designator") or "",
            "device": (c.get("device") or {}).get("name", ""),
            "value": (c.get("otherProperty") or {}).get("Value", ""),
            "footprint": (c.get("footprint") or {}).get("name", ""),
            "uniqueId": uid,
            "netlisted": netlisted,
            "addIntoBom": bool(c.get("addIntoBom")),
            "addIntoPcb": bool(c.get("addIntoPcb")),
            "pins": [{"number": p.get("pinNumber"), "name": p.get("pinName"),
                      "net": p.get("net") or "", "noConnected": bool(p.get("noConnected"))}
                     for p in (c.get("pins") or [])],
        })

    dst_all = os.path.join(out_dir, "sch_parts_all.json")
    with open(dst_all, "w", encoding="utf-8") as fh:
        json.dump(rows_all, fh, ensure_ascii=False, indent=2)

    rows = rows_all if include_shielded else [r for r in rows_all if r["netlisted"]]
    dst = os.path.join(out_dir, "sch_parts.json")
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=2)

    shielded = [r for r in rows_all if not r["netlisted"]]
    print("OK  原理图器件 -> %s  (%d 个 part；另有 %d 个 netflag/sheet)"
          % (dst, len(rows), len(comps) - len(parts)))
    if shielded:
        print("    已排除屏蔽区 %d 个（全量见 %s）: %s"
              % (len(shielded), os.path.basename(dst_all),
                 ", ".join(r["designator"] or "(无位号)" for r in shielded)))
    elif ids is None:
        print("  ! 无 ENET，未做屏蔽区过滤（先跑 --mode netlist）")

    # 重复位号只在"有效器件"里算 —— 屏蔽区里的重名不影响网表，不算错
    counts = {}
    for r in rows:
        d = r["designator"]
        if d:
            counts[d] = counts.get(d, 0) + 1
    for d, n in sorted(counts.items()):
        if n > 1:
            print("  ! 重复位号 %s x%d（有效器件内重名，会导致 connectivity 导出失败，须先改位号）" % (d, n))

    shielded_dups = {}
    for r in shielded:
        shielded_dups[r["designator"]] = shielded_dups.get(r["designator"], 0) + 1
    for d, n in sorted(shielded_dups.items()):
        if d and d in counts:
            print("  · 提示: 屏蔽区里还有一个 `%s`（不计入网表，但会让 `sch connectivity` 整体拒绝导出）" % d)

    if [r for r in rows if not r["designator"]]:
        print("  ! 无位号器件: %d 个" % len([r for r in rows if not r["designator"]]))

    # 重复 UniqueId：ENET 以 uid 为键，重了会**直接漏器件**（比重复位号更隐蔽）
    uid_map = {}
    for r in rows_all:
        if r["uniqueId"]:
            uid_map.setdefault(r["uniqueId"], []).append(r["designator"] or "(无位号)")
    dup_uid = {k: v for k, v in uid_map.items() if len(v) > 1}
    for uid, refs in sorted(dup_uid.items()):
        print("  ! 重复 UniqueId %s: %s —— ENET 按 uid 建索引，这几个里会漏掉器件" % (uid, " / ".join(refs)))

    no_uid = [r["designator"] for r in rows if not r["uniqueId"]]
    if no_uid:
        print("  ! 无 UniqueId（ENET 会漏掉）: %s" % ", ".join(no_uid))
    no_pcb = [r["designator"] for r in rows if not r["addIntoPcb"]]
    if no_pcb:
        print("  ! 未转 PCB: %s" % ", ".join(no_pcb))


def _net_id(name):
    return "net-" + hashlib.sha1(name.encode("utf-8")).hexdigest()


def _synth_connectivity(enet):
    """由 ENET 合成与 `sch connectivity` 同 schema 的 IR（天然排除屏蔽区）。

    schemaVersion 1.4 / components[] / nets[] / connections[] / issues[]
    注：ENET 不含坐标，pins 的 x/y 置 None —— 网表级审查用不到，需要坐标请用 sch list。
    """
    comps_out, conns, nets = [], [], {}
    for c in (enet.get("components") or {}).values():
        props = c.get("props") or {}
        ref = props.get("Designator") or ""
        cid = "cmp-%s" % ref
        pins = []
        for num, info in (c.get("pinInfoMap") or {}).items():
            nname = (info or {}).get("net") or ""
            pins.append({"number": str(num), "name": (info or {}).get("name") or "",
                         "x": None, "y": None})
            if nname:
                conns.append({"componentId": cid, "pinNumber": str(num),
                              "netId": _net_id(nname), "kind": "netlist"})
                nets.setdefault(nname, 0)
                nets[nname] += 1
        comps_out.append({
            "id": cid,
            "ref": ref,
            "device": {"name": props.get("DeviceName") or props.get("Name") or ""},
            "pins": pins,
            "placement": {"x": None, "y": None},
        })

    issues = []
    for c in comps_out:
        for p in c["pins"]:
            if not any(cn["componentId"] == c["id"] and cn["pinNumber"] == p["number"] for cn in conns):
                issues.append({"code": "unconnected-pin", "severity": "warning",
                               "componentId": c["id"], "pinNumber": p["number"],
                               "message": "%s pin %s has no net" % (c["ref"], p["number"])})

    return {
        "schemaVersion": "1.4",
        "projectId": enet.get("projectId") or "",
        "documentId": "",
        "_source": "synth-from-enet",
        "_note": "由 ENET 合成：已排除屏蔽区；不含坐标；issues 仅含 unconnected-pin",
        "components": comps_out,
        "nets": [{"id": _net_id(n), "name": n,
                  "scope": "local",
                  "role": "power" if n.upper() in {x.upper() for x in POWER_NETS} else "signal"}
                 for n in sorted(nets)],
        "connections": conns,
        "issues": issues,
    }


def do_connectivity(out_dir, base):
    dst = os.path.join(out_dir, "connectivity.json")
    try:
        proc, data = run_json(["sch", "connectivity", *base])
        if not isinstance(data, dict) or "components" not in data:
            raise RuntimeError((proc.stdout or proc.stderr or "").strip()[:200] or "返回不含 components")
        with open(dst, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        print("OK  连通性 IR -> %s  (%d 器件 / %d 网络)"
              % (dst, len(data.get("components", [])), len(data.get("nets", []))))
        return
    except Exception as exc:
        err = str(exc)
        dup = "duplicate component" in err
        print("  sch connectivity 失败（%s）%s" % (err, "—— 多半是屏蔽区里有重名件" if dup else ""))

    _ids, enet = _load_enet(out_dir)
    if not enet:
        raise RuntimeError("connectivity 失败且无 ENET 可合成，先跑 --mode netlist")
    ir = _synth_connectivity(enet)
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(ir, fh, ensure_ascii=False, indent=2)
    print("OK  连通性 IR(ENET 合成) -> %s  (%d 器件 / %d 网络 / %d 悬空脚)"
          % (dst, len(ir["components"]), len(ir["nets"]), len(ir["issues"])))
    if dup:
        print("    ↳ 已绕过重名阻塞；坐标字段为空，几何类判断请用 sch_parts + pcb_dump")


def do_check(out_dir, base):
    try:
        _proc, data = run_json(["sch", "check", "--json", *base])
    except Exception as exc:
        data = None
        print("  ! 逐项检查失败: %s" % str(exc)[:200])
    if not isinstance(data, dict) or "summary" not in data:
        print("  ! 逐项检查无有效返回（多半是图上存在非正交/斜导线，检查器几何算法会崩）")
        print("    定位方法：错误信息里的 seg=[x1,y1,x2,y2]，两端 x/y 都不相等即为斜线；删掉重画成水平/垂直即可。")
        return
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
    ap.add_argument("--include-shielded", action="store_true",
                    help="sch_parts.json 里保留屏蔽区器件（默认只输出有效器件）")
    args = ap.parse_args()

    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)
    base = ["--project", args.project] if args.project else []

    doc = activate_doc(args.project, "schematic")
    if doc:
        print("(前台已切到原理图: %s)" % doc["name"])

    is_all = args.mode == "all"

    # 顺序很重要：先读器件，再拉网表（netlist 导出会把文档留在非同步态）
    raw_parts = fetch_parts(base) if (args.mode in ("parts",) or is_all) else None

    if args.mode in ("netlist",) or is_all:
        do_netlist(out_dir, base)
    elif args.mode in ("parts", "connectivity"):
        _ensure_netlist(out_dir, base)

    if raw_parts is not None:
        do_parts(out_dir, raw_parts, include_shielded=args.include_shielded)
    if args.mode in ("connectivity",) or is_all:
        do_connectivity(out_dir, base)
    if args.mode in ("check",) or is_all:
        do_check(out_dir, base)
    if args.mode == "drc":
        do_drc(out_dir, base)


if __name__ == "__main__":
    main()
