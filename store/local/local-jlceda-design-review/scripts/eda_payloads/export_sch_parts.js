// 在 EDA 端执行：导出**原理图全部器件**（sch_PrimitiveComponent.getAll()）。
// 目的：补 ENET 网表的盲区 —— ENET 以 Unique ID 为 key，**会漏掉 UniqueId 为空的器件**，
// 因此「重复位号 / 游离器件 / 未转 PCB」这类检查不能用 ENET，必须用 getAll()。
// 由 new AsyncFunction('eda', code) 执行 → 支持多行与注释；必须 return。
const G = function (fn, fb) { try { const v = fn(); return v === undefined ? fb : v; } catch (e) { return 'ERR:' + String(e); } };

const all = await eda.sch_PrimitiveComponent.getAll();
const parts = [];
for (const c of all) {
  // 实测：getState_ComponentType() 返回小写 'part' / 'netflag' / 'sheet'
  const t = String(G(function () { return c.getState_ComponentType(); }, '')).toLowerCase();
  if (t !== 'part' && t !== 'component') continue;
  const other = G(function () { return c.getState_OtherProperty(); }, {}) || {};
  const fp = G(function () { return c.getState_Footprint(); }, null);
  parts.push({
    designator: G(function () { return c.getState_Designator(); }, ''),
    name: G(function () { return c.getState_Name(); }, ''),
    subPart: G(function () { return c.getState_SubPartName(); }, ''),
    uniqueId: G(function () { return c.getState_UniqueId(); }, ''),
    primitiveId: G(function () { return c.getState_PrimitiveId(); }, ''),
    footprint: fp && typeof fp === 'object' && fp.name ? fp.name : (typeof fp === 'string' ? fp : ''),
    x: G(function () { return c.getState_X(); }, null),
    y: G(function () { return c.getState_Y(); }, null),
    convertToPcb: other['Convert to PCB'],
    addIntoBom: other['Add into BOM'],
  });
}
parts.sort(function (a, b) { return String(a.designator).localeCompare(String(b.designator), undefined, { numeric: true }); });

const byDes = {};
for (const p of parts) { (byDes[p.designator] = byDes[p.designator] || []).push(p); }
const dupDesignators = Object.keys(byDes)
  .filter(function (d) { return byDes[d].length > 1; })
  .map(function (d) { return { designator: d, count: byDes[d].length, entries: byDes[d] }; });

return {
  ok: true,
  count: parts.length,
  parts: parts,
  dupDesignators: dupDesignators,
  blankDesignator: parts.filter(function (p) { return !p.designator; }).map(function (p) { return p.primitiveId; }),
  noUniqueId: parts.filter(function (p) { return !p.uniqueId; }).map(function (p) { return p.designator || ('(' + p.primitiveId + ')'); }),
  notConvertToPcb: parts.filter(function (p) { return String(p.convertToPcb).toLowerCase() === 'no'; }).map(function (p) { return p.designator; }),
};
