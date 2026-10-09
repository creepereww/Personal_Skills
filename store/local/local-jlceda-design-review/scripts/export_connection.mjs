#!/usr/bin/env node
// 内置「导出连接关系」——无需手动点插件菜单，直接把工程网表/区域结构导到本地。
// 用法:
//   node export_connection.mjs <outDir> [--port 49620] [--mode netlist|region|both]
// 前置: easyeda-api 桥接已起、EDA 端已连接、且激活文档是**原理图**（region 模式还需先框选）。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const outDir = args[0];
if (!outDir) {
  console.error('usage: node export_connection.mjs <outDir> [--port 49620] [--mode netlist|region|both]');
  process.exit(2);
}
const flag = (name, dflt) => {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : dflt;
};
const port = flag('--port', '49620');
const mode = flag('--mode', 'netlist');

async function runPayload(payloadRel) {
  const code = fs.readFileSync(path.join(__dirname, 'eda_payloads', payloadRel), 'utf8');
  const res = await fetch(`http://127.0.0.1:${port}/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
  });
  const text = await res.text();
  let json;
  try {
    json = JSON.parse(text);
  } catch {
    throw new Error('桥接返回非 JSON：' + text.slice(0, 300));
  }
  if (json.success === false) throw new Error(json.error ?? text);
  return json.result;
}

fs.mkdirSync(outDir, { recursive: true });

if (mode === 'netlist' || mode === 'both') {
  const r = await runPayload('export_netlist.js');
  if (!r || r.ok !== true) { console.error('导出 ENET 网表失败：', (r && r.error) || r); process.exit(1); }
  const p = path.join(outDir, 'netlist.enet.json');
  fs.writeFileSync(p, r.netlist);
  console.log(`OK  ENET 网表 -> ${p}  (${r.length} 字节)`);
}

if (mode === 'region' || mode === 'both') {
  const r = await runPayload('export_region.js');
  if (!r || r.ok !== true) { console.error('导出区域结构失败：', (r && r.error) || r); process.exit(1); }
  const p = path.join(outDir, 'region.jlc-schematic-region.json');
  fs.writeFileSync(p, JSON.stringify(r.region, null, 2));
  console.log(`OK  区域结构 -> ${p}  (${r.region.components.length} 器件 / ${r.region.nets.length} 网络)`);
}
