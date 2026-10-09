// 在 EDA 端执行：拉取当前工程的官方 ENET 网表（连接关系真值）。
// 由网关 `new AsyncFunction('eda', code)` 执行 → 支持多行与注释；必须 return。
// 前置：当前激活文档必须是**原理图**（SCH_* API 的要求）。
const env = {
  isWeb: eda.sys_Environment.isWeb(),
  isClient: eda.sys_Environment.isClient(),
  isJLCEDAPro: eda.sys_Environment.isJLCEDAProEdition(),
  isEasyEDAPro: eda.sys_Environment.isEasyEDAProEdition(),
};

// ESYS_NetlistType.JLCEDA_PRO === 'JLCEDA'；枚举缺失时回落到字面量
const NET_TYPE =
  (typeof ESYS_NetlistType !== 'undefined' && ESYS_NetlistType.JLCEDA_PRO) || 'JLCEDA';

let file;
try {
  file = await eda.sch_ManufactureData.getNetlistFile('review-netlist', NET_TYPE);
} catch (e) {
  return { ok: false, error: 'getNetlistFile 调用失败：' + String(e), env };
}
if (!file) {
  return {
    ok: false,
    error: 'getNetlistFile 返回空：请确认当前激活的是原理图文档。',
    env,
  };
}

const text = await file.text();
return {
  ok: true,
  env,
  fileName: file.name || null,
  length: text.length,
  netlist: text,
};
