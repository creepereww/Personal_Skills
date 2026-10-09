#!/usr/bin/env python3
"""把 连接关系 JSON 规范化成统一网表并打印可读结果。支持三种输入：

  * ENET 网表            —— easyeda `sch netlist` 产出的 .enet（连通性真值）
  * jlc-schematic-region —— 插件《让AI看看你的原理图》框选导出的区域 JSON
  * connectivity IR      —— easyeda `sch connectivity` 导出（schemaVersion 1.x）

用法: python parse_enet.py <input.json> [out.normalized.json]

ENET 真实字段（JLCEDA Pro v2.0.0，实测）:
  器件: components[<uniqueId>].props = {
    Designator, Value, Name(模板，如 "={Value}"，勿直接显示),
    DeviceName, FootprintName(封装名，用它), "PCB Footprint", "Source Package",
    Supplier, "Supplier Part"(立创/LCSC 编号), "LCSC Part Name"(商品名),
    Manufacturer, "Manufacturer Part", "JLCPCB Part Class"(Basic/Extended),
    "Convert to PCB"(yes/no), "Add into BOM"(yes/no), Unique ID }
  引脚: components[].pinInfoMap[<序号>] = { number, name, net, ... }
注意: 部分器件 props 缺键（而非空串）。
"""
import json
import re
import sys


def _s(v):
    return "" if v is None else str(v).strip()


def _is_template(v):
    return bool(re.match(r"^=\{.*\}$", _s(v)))


def _nat_key(d):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", d)]


def load_raw(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def build(raw):
    if isinstance(raw, dict) and raw.get("format") == "jlc-schematic-region":
        return _from_region(raw)
    if isinstance(raw, dict) and "schemaVersion" in raw and "components" in raw and isinstance(raw["components"], list):
        return _from_connectivity(raw)
    return _from_enet(raw)


def _from_region(raw):
    norm = {"source": "jlc-schematic-region", "components": [], "nets": {}}
    for c in raw.get("components", []):
        norm["components"].append({
            "designator": _s(c.get("designator")), "name": _s(c.get("name")), "value": "",
            "footprint": _s(c.get("footprint")),
            "pins": [{"number": _s(p.get("number")), "name": _s(p.get("name")),
                      "noConnected": bool(p.get("noConnected"))} for p in (c.get("pins") or [])],
        })
    for n in raw.get("nets", []):
        norm["nets"][n.get("name")] = sorted(n.get("members", []), key=_nat_key)
    return norm


def _from_connectivity(raw):
    # IR 结构：components[] / nets[]{id,name,...} / connections[]{componentId,pinNumber,netId} / issues[]
    norm = {"source": "connectivity", "components": [], "nets": {}}
    ref_of = {}
    for c in raw.get("components", []):
        dev = c.get("device") or {}
        cid = _s(c.get("id"))
        ref = _s(c.get("ref")) or cid
        ref_of[cid] = ref
        norm["components"].append({
            "designator": ref,
            "name": _s(dev.get("name")), "value": "", "footprint": "",
            "pins": [{"number": _s(p.get("number")), "name": _s(p.get("name")), "noConnected": False}
                     for p in (c.get("pins") or [])],
        })
    name_of = {_s(n.get("id")): _s(n.get("name")) for n in raw.get("nets", [])}
    nets = {}
    for cn in raw.get("connections", []):
        net = name_of.get(_s(cn.get("netId")))
        ref = ref_of.get(_s(cn.get("componentId")), _s(cn.get("componentId")))
        if net:
            nets.setdefault(net, []).append("%s.%s" % (ref, _s(cn.get("pinNumber"))))
    # 没有 connections 时退化为 nets[].pins/members
    if not nets:
        for n in raw.get("nets", []):
            members = n.get("pins") or n.get("members") or n.get("connections") or []
            nets[_s(n.get("name"))] = list(members)
    norm["nets"] = {k: sorted(v, key=_nat_key) for k, v in sorted(nets.items())}
    norm["issues"] = raw.get("issues", [])
    norm["components"].sort(key=lambda c: _nat_key(c["designator"]))
    return norm


def _from_enet(raw):
    norm = {"source": "enet", "components": [], "nets": {}}
    nets = {}
    for comp in (raw.get("components") or {}).values():
        props = comp.get("props") or {}
        d = _s(props.get("Designator"))
        if not d:
            continue  # 无位号（网络标签等）不进器件表
        pins = []
        pim = comp.get("pinInfoMap") or comp.get("pins") or {}
        for key, pin in pim.items():
            num = _s(pin.get("number") or key)
            net = _s(pin.get("net"))
            pins.append({"number": num, "name": _s(pin.get("name")), "noConnected": False})
            if net:
                nets.setdefault(net, []).append("%s.%s" % (d, num))
        norm["components"].append({
            "designator": d,
            "name": _s(props.get("DeviceName")) or ("" if _is_template(props.get("Name")) else _s(props.get("Name"))),
            "value": _s(props.get("Value")),
            "footprint": _s(props.get("FootprintName")) or _s(props.get("PCB Footprint")) or _s(props.get("Source Package")),
            "manufacturer": _s(props.get("Manufacturer")),
            "manufacturerPart": _s(props.get("Manufacturer Part")),
            "supplier": _s(props.get("Supplier")),
            "supplierPart": _s(props.get("Supplier Part")),
            "lcscName": _s(props.get("LCSC Part Name")),
            "jlcClass": _s(props.get("JLCPCB Part Class")),
            "convertToPcb": _s(props.get("Convert to PCB")) != "no",
            "addIntoBom": _s(props.get("Add into BOM")) != "no",
            "pins": pins,
        })
    norm["components"].sort(key=lambda c: _nat_key(c["designator"]))
    norm["nets"] = {k: sorted(v, key=_nat_key) for k, v in sorted(nets.items())}
    return norm


def stats(norm):
    assigned, single = set(), []
    for n, members in norm["nets"].items():
        for x in members:
            assigned.add(x)
        if len(members) == 1:
            single.append(n)
    dangling = []
    for c in norm["components"]:
        for p in c["pins"]:
            key = "%s.%s" % (c["designator"], p["number"])
            if not p.get("noConnected") and key not in assigned:
                dangling.append(key)
    has_bom = any("addIntoBom" in c for c in norm["components"])
    norm["stats"] = {
        "components": len(norm["components"]),
        "nets": len(norm["nets"]),
        "withSupplierPart": len([c for c in norm["components"] if c.get("supplierPart")]),
        "noLcscInfo": [c["designator"] for c in norm["components"]
                       if c.get("supplierPart") is not None and not c.get("supplierPart") and not c.get("lcscName")],
        "bomExcluded": [c["designator"] for c in norm["components"] if c.get("addIntoBom") is False] if has_bom else [],
        "pcbExcluded": [c["designator"] for c in norm["components"] if c.get("convertToPcb") is False] if has_bom else [],
        "singlePointNets": single,
        "danglingPins": dangling,
    }
    return norm


def main():
    if len(sys.argv) < 2:
        print("usage: python parse_enet.py <input.json> [out.normalized.json]", file=sys.stderr)
        sys.exit(2)
    norm = stats(build(load_raw(sys.argv[1])))
    if len(sys.argv) > 2:
        with open(sys.argv[2], "w", encoding="utf-8") as fh:
            json.dump(norm, fh, ensure_ascii=False, indent=2)

    st = norm["stats"]
    has_supplier = any("supplierPart" in c for c in norm["components"])
    extra = " | 立创编号 %d/%d" % (st["withSupplierPart"], st["components"]) if has_supplier else ""
    print("# 来源 %s | 器件 %d | 网络 %d%s" % (norm["source"], st["components"], st["nets"], extra))

    print("\n== 器件（位号 | 器件名 | 值 | 封装 | 立创编号 | BOM）==")
    for c in norm["components"]:
        print("[%s] %s | %s | %s | %s | %s" % (
            c["designator"], c.get("name") or "-", c.get("value") or "-",
            c.get("footprint") or "-", c.get("supplierPart") or "-",
            "BOM" if c.get("addIntoBom") else "noBOM"))

    print("\n== 网络（成员数降序，单点标 !）==")
    for n, members in sorted(norm["nets"].items(), key=lambda kv: (-len(kv[1]), _nat_key(kv[0]))):
        print("[%s] (%d)%s %s" % (n, len(members), " !" if len(members) == 1 else "", ", ".join(members)))

    print("\n== 未连接引脚（不在任何网）==")
    print(", ".join(st["danglingPins"]) if st["danglingPins"] else "(无)")
    print("\n== 单点网络（仅 1 个引脚，悬空/孤立信号）==")
    print(", ".join(st["singlePointNets"]) if st["singlePointNets"] else "(无)")
    if st["bomExcluded"]:
        print("\n== 未加入 BOM（%d）==\n%s" % (len(st["bomExcluded"]), ", ".join(st["bomExcluded"])))
    if st["pcbExcluded"]:
        print("\n== 未转 PCB（%d）==\n%s" % (len(st["pcbExcluded"]), ", ".join(st["pcbExcluded"])))
    if norm.get("issues"):
        print("\n== IR issues（connector 判定的连接问题，共 %d）==" % len(norm["issues"]))
        for it in norm["issues"][:60]:
            print("  [%s] %s" % (it.get("code"), it.get("message")))


if __name__ == "__main__":
    main()
