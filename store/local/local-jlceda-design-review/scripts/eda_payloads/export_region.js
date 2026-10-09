// 在 EDA 端执行：把**框选区域**导出为 `jlc-schematic-region` JSON。
// 复刻《让AI看看你的原理图》的「导出连接关系」，字段兼容其「导入连接关系」。
// 用法：先在原理图中框选区域，再运行本 payload。
// 由 `new AsyncFunction('eda', code)` 执行 → 支持多行与注释；必须 return。
// 实测（JLCEDA Pro，本机 bridge 执行环境）：下列全局枚举 **undefined**，
// 且 getState_ComponentType() 返回**小写**字符串：'part'（普通器件）/ 'netflag'（网络标签）/ 'sheet'（图纸）。
// 因此不能用 ESCH_PrimitiveComponentType.COMPONENT 判等，须按小写字面量判断（并兼容 'component'）。
const NET_TYPE =
  (typeof ESYS_NetlistType !== 'undefined' && ESYS_NetlistType && ESYS_NetlistType.JLCEDA_PRO) || 'JLCEDA';
const isPart = function (t) { const s = String(t).toLowerCase(); return s === 'part' || s === 'component'; };
const isNetFlag = function (t) {
  const s = String(t).toLowerCase().replace(/[_\s]/g, '');
  return s === 'netflag' || s === 'netport' || s === 'netlabel';
};

const ids = await eda.sch_SelectControl.getAllSelectedPrimitives_PrimitiveId();
if (!ids || ids.length === 0) {
  return { ok: false, error: '请先在原理图中框选至少一个图元。' };
}
const sel = await eda.sch_Primitive.getPrimitivesByPrimitiveId(ids);
const asComp = sel.filter(function (p) {
  try { return typeof p.getState_ComponentType === 'function'; } catch (e) { return false; }
});

const comps = asComp.filter(function (c) { return isPart(c.getState_ComponentType()); });
const anchors = asComp
  .filter(function (c) { return isNetFlag(c.getState_ComponentType()); })
  .map(function (c) { return { net: c.getState_Net() || '' }; })
  .filter(function (a) { return a.net; });
if (comps.length === 0) return { ok: false, error: '框选区域中没有普通器件。请框选一个完整功能区。' };

// 位号必须存在且唯一（否则无法建立稳定引用）
const seen = {};
const dups = [];
for (const c of comps) {
  const d = c.getState_Designator();
  if (!d) return { ok: false, error: '框选区域中存在没有位号的器件。' };
  if (seen[d]) dups.push(d);
  seen[d] = true;
}
if (dups.length > 0) return { ok: false, error: '框选区域存在重复位号：' + dups.join('、') };

// 官方 ENET 网表
const file = await eda.sch_ManufactureData.getNetlistFile('review-netlist', NET_TYPE);
if (!file) return { ok: false, error: '网表读取失败。' };
let root;
try {
  root = JSON.parse((await file.text()).replace(/^\uFEFF/, ''));
} catch (e) {
  return { ok: false, error: '网表不是有效 JSON：' + String(e) };
}

// 索引 ENET：成员(位号.脚号) -> 网名；网名 -> 成员[]
const pinByMember = {};
const membersByNet = {};
for (const comp of Object.values(root.components || {})) {
  const d = String((comp.props || {}).Designator || '').trim();
  if (!d) continue;
  for (const entry of Object.entries(comp.pinInfoMap || {})) {
    const num = String(entry[1].number || entry[0]).trim();
    const member = d + '.' + num;
    pinByMember[member] = { number: num, name: String(entry[1].name || ''), net: String(entry[1].net || '') };
    const net = String(entry[1].net || '');
    if (net) { (membersByNet[net] = membersByNet[net] || []).push(member); }
  }
}

// 器件 + 引脚
const selectedMembers = {};
const components = [];
for (const c of comps) {
  const d = c.getState_Designator();
  const pins = (await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(c.getState_PrimitiveId())) || [];
  const outPins = pins.map(function (p) {
    const num = p.getState_PinNumber();
    selectedMembers[d + '.' + num] = true;
    return {
      number: num,
      name: p.getState_PinName() || '',
      type: String(p.getState_pinType()),
      noConnected: Boolean(p.getState_NoConnected()),
    };
  });
  const sub = c.getState_SubPartName();
  const fp = c.getState_Footprint();
  const rawName = c.getState_Name() || '';
  const m = /^=\{(.+)\}$/.exec(rawName);
  const rec = { designator: d, name: m ? m[1] : rawName, pins: outPins };
  if (sub) rec.subPart = sub;
  if (fp && fp.name) rec.footprint = fp.name;
  components.push(rec);
}
components.sort(function (a, b) { return a.designator.localeCompare(b.designator, undefined, { numeric: true }); });

// 网络：只保留含选中成员者；含区域外成员 -> external
const isGenerated = function (n) { return /^(?:N\$\d+|\$\d+(?:N\d+)?)$/i.test(n); };
const nets = [];
const netNames = Object.keys(membersByNet).sort();
for (const name of netNames) {
  const all = membersByNet[name];
  const inSel = all.filter(function (mm) { return selectedMembers[mm]; });
  if (inSel.length === 0) continue;
  const outside = all.filter(function (mm) { return !selectedMembers[mm]; });
  const net = { name: name, scope: outside.length ? 'external' : 'internal', generated: isGenerated(name) };
  if (outside.length) net.direction = 'BI';
  net.members = inSel.sort(function (a, b) { return a.localeCompare(b, undefined, { numeric: true }); });
  nets.push(net);
}
for (const a of anchors) {
  if (!nets.some(function (n) { return n.name === a.net; })) {
    nets.push({ name: a.net, scope: 'external', direction: 'BI', generated: false, members: [] });
  }
}
nets.sort(function (a, b) { return a.name.localeCompare(b.name, undefined, { numeric: true }); });

return { ok: true, region: { format: 'jlc-schematic-region', version: 1, components: components, nets: nets } };
