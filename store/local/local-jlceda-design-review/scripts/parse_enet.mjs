#!/usr/bin/env node
// 把 ENET 网表 或 插件区域 JSON 规范化成统一网表，并打印可读结果。
// 两者都是「连接关系」的抽象层，可直接当审查的连通性真值。
// 用法: node parse_enet.mjs <input.json> [out.normalized.json]
//
// ENET 真实字段（JLCEDA Pro v2.0.0，实测）：
//   器件: components[<uniqueId>].props = {
//     Designator, Value, Name(模板，如 "={Value}"/"={Device}"，勿直接显示),
//     DeviceName, Footprint(ID,勿用), FootprintName(封装名,用它), PCB Footprint, Source Package,
//     Supplier, "Supplier Part"(立创/LCSC 编号), "LCSC Part Name"(商品名),
//     Manufacturer, "Manufacturer Part"(厂家料号), "JLCPCB Part Class"(Basic/Extended),
//     "Convert to PCB"(yes/no), "Add into BOM"(yes/no), Unique ID, Channel ID }
//   引脚: components[].pinInfoMap[<序号>] = { number, name, net, pinClass, ... }
// 注意: 部分器件 props 里没有 Supplier Part / Value（键缺失而非空串）。
import fs from 'node:fs';

const inPath = process.argv[2];
if (!inPath) { console.error('usage: node parse_enet.mjs <input.json> [out.normalized.json]'); process.exit(2); }
const raw = JSON.parse(fs.readFileSync(inPath, 'utf8').replace(/^\uFEFF/, ''));
const isRegion = raw && raw.format === 'jlc-schematic-region';
const nat = (a, b) => a.localeCompare(b, undefined, { numeric: true });
const str = (v) => (v === undefined || v === null ? '' : String(v).trim());
const isTemplate = (v) => /^=\{.*\}$/.test(str(v));   // "={Value}" / "={Device}"

const norm = { source: isRegion ? 'jlc-schematic-region' : 'enet', components: [], nets: {}, stats: {} };

if (isRegion) {
  for (const c of raw.components || []) {
    norm.components.push({
      designator: str(c.designator), name: str(c.name), value: '', footprint: str(c.footprint),
      pins: (c.pins || []).map((p) => ({ number: str(p.number), name: str(p.name), noConnected: !!p.noConnected })),
    });
  }
  for (const n of raw.nets || []) norm.nets[n.name] = (n.members || []).slice().sort(nat);
} else {
  const nets = new Map();
  for (const comp of Object.values(raw.components || {})) {
    const props = comp.props || {};
    const d = str(props.Designator);
    if (!d) continue;                       // 无位号（网络标签等）不进器件表
    const pins = [];
    const pim = comp.pinInfoMap || comp.pins || {};
    for (const [key, pin] of Object.entries(pim)) {
      const num = str(pin.number || key);
      const net = str(pin.net);
      pins.push({ number: num, name: str(pin.name), noConnected: false });
      if (net) { const arr = nets.get(net) || []; arr.push(d + '.' + num); nets.set(net, arr); }
    }
    norm.components.push({
      designator: d,
      name: str(props.DeviceName) || (isTemplate(props.Name) ? '' : str(props.Name)),
      value: str(props.Value),
      footprint: str(props.FootprintName) || str(props['PCB Footprint']) || str(props['Source Package']),
      manufacturer: str(props.Manufacturer),
      manufacturerPart: str(props['Manufacturer Part']),
      supplier: str(props.Supplier),
      supplierPart: str(props['Supplier Part']),      // 立创编号（可下单）
      lcscName: str(props['LCSC Part Name']),
      jlcClass: str(props['JLCPCB Part Class']),
      convertToPcb: str(props['Convert to PCB']) !== 'no',
      addIntoBom: str(props['Add into BOM']) !== 'no',
      pins,
    });
  }
  norm.components.sort((a, b) => nat(a.designator, b.designator));
  for (const [n, m] of [...nets.entries()].sort()) norm.nets[n] = m.sort(nat);
}

// ---- 统计 ----
const assigned = new Set();
const singlePointNets = [];
for (const [n, m] of Object.entries(norm.nets)) { m.forEach((x) => assigned.add(x)); if (m.length === 1) singlePointNets.push(n); }
const dangling = [];
for (const c of norm.components) for (const p of c.pins) {
  const key = c.designator + '.' + p.number;
  if (!p.noConnected && !assigned.has(key)) dangling.push(key);
}
norm.stats = {
  components: norm.components.length,
  nets: Object.keys(norm.nets).length,
  withSupplierPart: norm.components.filter((c) => c.supplierPart).length,
  noLcscInfo: norm.components.filter((c) => !c.supplierPart && !c.lcscName).map((c) => c.designator),
  bomExcluded: norm.components.filter((c) => !c.addIntoBom).map((c) => c.designator),
  pcbExcluded: norm.components.filter((c) => !c.convertToPcb).map((c) => c.designator),
  singlePointNets,
  danglingPins: dangling,
};

const outPath = process.argv[3];
if (outPath) fs.writeFileSync(outPath, JSON.stringify(norm, null, 2));

// ---- 打印 ----
console.log(`# 来源 ${norm.source} | 器件 ${norm.stats.components} | 网络 ${norm.stats.nets} | 立创编号 ${norm.stats.withSupplierPart}/${norm.stats.components}`);
console.log('\n== 器件（位号 | 器件名 | 值 | 封装 | 立创编号 | BOM）==');
for (const c of norm.components) {
  console.log(`[${c.designator}] ${c.name || '-'} | ${c.value || '-'} | ${c.footprint || '-'} | ${c.supplierPart || '-'} | ${c.addIntoBom ? 'BOM' : 'noBOM'}`);
}
console.log('\n== 网络（成员数降序，单点标 ⚠）==');
for (const [n, m] of Object.entries(norm.nets).sort((a, b) => b[1].length - a[1].length || nat(a[0], b[0]))) {
  console.log(`[${n}] (${m.length})${m.length === 1 ? ' ⚠' : ''} ${m.join(', ')}`);
}
console.log('\n== 未连接引脚（不在任何网）==');
console.log(dangling.length ? dangling.join(', ') : '(无)');
console.log('\n== 单点网络（仅 1 个引脚，悬空/孤立信号）==');
console.log(singlePointNets.length ? singlePointNets.join(', ') : '(无)');
if (norm.stats.bomExcluded.length) console.log(`\n== 未加入 BOM（${norm.stats.bomExcluded.length}）==\n${norm.stats.bomExcluded.join(', ')}`);
if (norm.stats.pcbExcluded.length) console.log(`\n== 未转 PCB（${norm.stats.pcbExcluded.length}）==\n${norm.stats.pcbExcluded.join(', ')}`);
