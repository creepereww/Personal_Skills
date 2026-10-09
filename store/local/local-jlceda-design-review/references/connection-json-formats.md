# 连接关系 JSON：两种格式与自行获取

审查原理图时，**连通性真值**有两条来源，都是"抽象层"，不必自己从坐标重建：

| 来源 | 是什么 | 覆盖 | 获取 |
|---|---|---|---|
| **ENET 网表** | 嘉立创官方网表（`ESYS_NetlistType.JLCEDA_PRO`） | **全工程** | `scripts/export_connection.mjs`（内置） |
| **jlc-schematic-region** | 插件《让AI看看你的原理图》的「导出连接关系」格式 | **仅框选区域** | 插件菜单，或 `--mode region`（内置复刻） |

---

## 1. 内置获取（无需手动导出）

```bash
node scripts/export_connection.mjs <outDir>            # 默认导全工程 ENET 网表
node scripts/export_connection.mjs <outDir> --mode region   # 复刻插件：先在 EDA 里框选再跑
node scripts/parse_enet.mjs <outDir>/netlist.enet.json [out.json]   # 规范化 + 可读输出
```

关键 API（都与 `easyeda-api` 桥接无关，是 EDA 官方 API）：

- `eda.sch_ManufactureData.getNetlistFile(name?, ESYS_NetlistType)` → `Promise<File>`，`.text()` 得网表文本。
  - `ESYS_NetlistType.JLCEDA_PRO === 'JLCEDA'`（另有 `EASYEDA_PRO='EasyEDA'`、`ALTIUM_DESIGNER='Protel2'`、`PADS`、`ALLEGRO`、`DISA`）。
  - ⚠️ **不是** `sch_Netlist.getNetlist()`（那个已废弃、会超时）。这是两回事，别混。
- 选区：`eda.sch_SelectControl.getAllSelectedPrimitives_PrimitiveId()` → ids → `eda.sch_Primitive.getPrimitivesByPrimitiveId(ids)`
- 器件引脚：`eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(primitiveId)`
  - 引脚取值为 `getState_PinNumber()` / `getState_PinName()` / **`getState_pinType()`（小写 p）** / `getState_NoConnected()`
- 器件判据：`primitive.getState_PrimitiveType() === ESCH_PrimitiveType.COMPONENT`；
  或 `component.getState_ComponentType() === ESCH_PrimitiveComponentType.COMPONENT`（另有 `NET_FLAG` / `NET_PORT` / `DRAWING`）

**前置**：SCH_* API 要求当前激活文档是原理图；`getNetlistFile` 返回空多半是激活的不是原理图页。

---

## 2. ENET 网表结构（`ESYS_NetlistType.JLCEDA_PRO`）

```jsonc
{
  "version": "…",
  "components": {                      // 对象，键为器件内部 id（非位号）
    "<id>": {
      "props": { "Designator": "R3", "Name": "Resistor", "Value": "5.1k",
                 "Manufacturer Part": "…", "Supplier Part": "C25905", "DeviceName": "…" },
      "pinInfoMap": {                  // 键为内部脚 key
        "<pinKey>": { "number": "1", "name": "…", "net": "PDT" }
      }
    }
  }
}
```

要点：
- `pinInfoMap[*].net` 为**空串**表示该脚未接线（与"接 GND"要分清）。
- 组件按 `props.Designator` 归并；**同名位号会对应多条记录**（多子部件器件或真冲突），需自行判别。
- 这是全工程网表：做整体审查用它是首选。

## 3. `jlc-schematic-region` 结构（插件导出）

```jsonc
{
  "format": "jlc-schematic-region",
  "version": 1,
  "components": [
    { "designator": "U1", "name": "AN4354",
      "subPart": "…",                                  // 可选
      "footprint": "SOT-23-5",                          // 本 skill 内置版附带；插件版放在 referenceProperties
      "pins": [ { "number": "1", "name": "CHRG", "type": "OUT", "noConnected": false } ] }
  ],
  "nets": [
    { "name": "VBUS", "scope": "external", "direction": "BI", "generated": false,
      "members": ["U1.4", "USB1.A4"] }
  ]
}
```

- `scope`：`internal`（只连区域内）/ `external`（还连区域外）；`external` 才带 `direction`（`IN`/`OUT`/`BI`）。
- `generated`：`true` 表示原网名是自动生成（`N$数字` / `$数字N数字`）。
- **不含坐标**：`primitiveId` / `x` / `y` / `rotation` / `line` 是插件明确禁止出现在正文里的字段。
- 插件版每个器件另带 `referenceProperties{key, more}`（只读物性，供 AI 识别型号/参数，导入时被忽略）。

---

## 4. 两份格式与审查的分工

- **ENET（全工程）** 当**连通性真值**：判断悬空脚、单点网、端接、重复位号、BOM 绑定的值，都靠它。
- **region** 用于**局部功能块**的读写往返（插件导入/修改流程）；做只读审查时，全工程 ENET 通常更合适。
- 若两者都有：**以 ENET 为准**（region 只是它的一个子集视图，且可能因框选不全而漏）。

---

## 5. 来源与许可

- `jlc-schematic-region` 格式逆向自插件《让AI看看你的原理图》（`schematic-structure-text-bridge`，Apache-2.0），
  上游 <https://github.com/2549850807/Let-the-AI-look-at-the-schematic>。本 skill 只做**格式说明 + 自行重写**的等价实现，
  未整包拷贝分发。
- 内置的 `export_region.js` 与插件导出的字段**基本兼容**；唯一差别：本实现把 `footprint` 直接放在 `components[]` 上
  （插件放在 `referenceProperties.key.footprint`，且导入时被忽略），因此不影响插件侧导入。
- ENET 格式来自嘉立创官方网表 API（`ESYS_NetlistType.JLCEDA_PRO`），字段名以实机导出为准（首次导出后如有出入请修正本节）。
