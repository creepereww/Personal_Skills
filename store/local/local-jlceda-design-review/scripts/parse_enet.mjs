#!/usr/bin/env node
// 把 ENET 网表 或 插件区域 JSON 规范化成统一网表，并打印可读结果。
// 两者都是「连接关系」的抽象层，可直接当审查的连通性真值。
// 用法: node parse_enet.mjs <input.json> [out.normalized.json]
import fs from 'node:fs';

const inPath = process.argv[2];
if (!inPath) { console.error('usage: node parse_enet.mjs <input.json> [out.normalized.json]'); process.exit(2); }
const raw = JSON.parse(fs.readFileSync(inPath, 'utf8').replace(/^\uFEFF/, ''));
const isRegion = raw && raw.format === 'jlc-schematic-region';
const nat = (a, b) => a.localeCompare(b, undefined, { numeric: true });

const norm = { source: isRegion ? 'jlc-schematic-region' : 'enet', components: [], nets: {} };

if (isRegion) {
  for (const c of raw.components || []) {
    norm.components.push({
      designator: c.designator, name: c.name || '', value: '', footprint: c.footprint || '',
      pins: (c.pins || []).map((p) => ({ number: p.number, name: p.name || '', noConnected: !!p.noConnected })),
    });
  }
  for (const n of raw.nets || []) norm.nets[n.name] = (n.members || []).slice().sort(nat);
} else {
  const nets = new Map();
  for (const comp of Object.values(raw.components || {})) {
    const props = comp.props || {};
    const d = String(props.Designator || '').trim();
    if (!d) continue;
    const pins = [];
    const pim = comp.pinInfoMap || comp.pins || {};
    for (const [key, pin] of Object.entries(pim)) {
      const num = String(pin.number || key).trim();
      const net = String(pin.net || '');
      pins.push({ number: num, name: String(pin.name || ''), noConnected: false });
      if (net) { const arr = nets.get(net) || []; arr.push(d + '.' + num); nets.set(net, arr); }
    }
    norm.components.push({
      designator: d,
      name: String(props.Name || props.DeviceName || ''),
      value: String(props.Value || ''),
      footprint: String(props.Footprint || ''),
      manufacturer: String(props.Manufacturer || ''),
      supplierPart: String(props['Supplier Part'] || ''),
      pins,
    });
  }
  norm.components.sort((a, b) => nat(a.designator, b.designator));
  for (const [n, m] of [...nets.entries()].sort()) norm.nets[n] = m.sort(nat);
}

const outPath = process.argv[3];
if (outPath) fs.writeFileSync(outPath, JSON.stringify(norm, null, 2));

const netNames = Object.keys(norm.nets);
console.log(`# 来源 ${norm.source} | 器件 ${norm.components.length} | 网络 ${netNames.length}`);
console.log('\n== 器件 ==');
for (const c of norm.components) {
  const extra = [c.value && '= ' + c.value, c.footprint, c.supplierPart].filter(Boolean).join(' | ');
  console.log(`[${c.designator}] ${c.name}${extra ? '  ' + extra : ''}`);
}
console.log('\n== 网络（成员数降序）==');
const assigned = new Set();
for (const [n, m] of Object.entries(norm.nets).sort((a, b) => b[1].length - a[1].length || nat(a[0], b[0]))) {
  m.forEach((x) => assigned.add(x));
  console.log(`[${n}] (${m.length}) ${m.join(', ')}`);
}
const dangling = [];
for (const c of norm.components) {
  for (const p of c.pins) {
    const key = c.designator + '.' + p.number;
    if (!p.noConnected && !assigned.has(key)) dangling.push(key);
  }
}
console.log('\n== 未连接引脚（不在任何网 / noConnected=false）==');
console.log(dangling.length ? dangling.join(', ') : '(无)');
