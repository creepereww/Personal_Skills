---
name: local-jlceda-design-review
description: 嘉立创EDA(EasyEDA)工程的原理图 + PCB 设计审查方法与流程 —— 不止看 DRC，而是重建网表做电路级审查（电源/充电拓扑、端接 Rd、悬空脚、去耦、BOM 误绑、重复位号）与布局布线审查（线宽载流、去耦距离、缝合过孔、铺铜与板框、环宽、散热）。当用户说"帮我检查/审查原理图""PCB 布局布线有没有要优化的""原理图原理有没有错""做个设计评审""出一份检查报告"，或在嘉立创EDA/EasyEDA 里对着某个工程要做设计审查时使用。依赖 easyeda-api skill 完成与 EDA 的连接与 API 调用。
version: v0.3
---

# 嘉立创EDA 原理图/PCB 设计审查

> **给改我的人**：成熟度 `v0.x`（完善中）→ 可直接改，改完回报"改了哪个文件、改了什么"即可。
> 本 skill 是**通用**的（跨机器成立）：**别写死**本机磁盘路径、端口、工程名、器件位号 —— 那些属于项目/机器，
> 放项目工作区或 `store/machine/`。仓库规则见 `local-skills-hub`。

本 skill 只管**审查的方法与流程**。"怎么连上 EDA、怎么在里面跑 API" 交给 `easyeda-api` skill，这里不重复。

审查分三层，**别只做第三层**：
1. **原理层**（DRC 不会告诉你）—— 电路拓扑对不对
2. **布局布线层** —— 好不好、有没有余量
3. **一致性/规范层** —— DRC、原理图↔PCB 是否同步

---

## 0. 前置：数据通道

按 `easyeda-api` skill 起桥接、连 EDA。要点：
- 健康检查：`curl http://127.0.0.1:<port>/health`（端口在 49620–49629 自选）。
- 送进 `/execute` 的代码在 EDA 端由 `new AsyncFunction('eda', code)` 执行 → **多行、注释、`await` 都正常**，
  最后必须 `return`（返回值即 `eda` 结果）。所以把片段写成正常的 `.js` 文件即可。
- 用 `scripts/eda_exec.mjs <js文件> [端口]` 执行 JS 片段，省掉 bash 转义。

在工程里先认清三样东西的 uuid：原理图页、PCB、项目。切文档用 `dmt_EditorControl.openDocument(uuid)`；
`SCH_*` API 要求激活的是原理图页，`PCB_*` 要求是 PCB，**跨域操作前先切、做完切回原文档**。

---

## 1. 数据获取：连通性真值优先

### 路线 A（首选，原理级审查）—— 用官方网表拿"连接关系"，**内置、免手动导出**

嘉立创官方网表 API（`eda.sch_ManufactureData.getNetlistFile(name, ESYS_NetlistType.JLCEDA_PRO)`，
`JLCEDA_PRO === 'JLCEDA'`）能直接给出**全工程**的**器件→引脚→网络** JSON（ENET 格式）。
**它不是已废弃的 `sch_Netlist.getNetlist()`** —— 那个才超时，这个可用。

一行命令即可导出（EDA 已连、激活文档是原理图）：

```bash
node scripts/export_connection.mjs <工作目录>/<项目名>/          # 落 netlist.enet.json
node scripts/parse_enet.mjs <工作目录>/<项目名>/netlist.enet.json  # 规范化 + 可读打印
```

- 约定：**在工作目录下按工程名建文件夹**（如 `<工作目录>/<项目名>/`），产物都落这里。
- 为什么优先：它已是**抽象层**（网络↔引脚），从根上避开"连通性重建"，最不容易错；且覆盖**全工程**。
- 若用户仍用插件《让AI看看你的原理图》手动导出了区域 JSON，也兼容：
  `scripts/parse_enet.mjs` 能识别 `format:"jlc-schematic-region"`。两种格式见
  `references/connection-json-formats.md`。
- 想复刻插件的"框选区域导出"：`export_connection.mjs <outDir> --mode region`（先在 EDA 里框选）。

### 路线 B（兜底 / 补充）—— API 取原始图元本地重建
原理图侧：`sch_PrimitiveComponent.getAll()` + 逐件 `getAllPins()`，`sch_PrimitiveWire.getAll()`；
PCB 侧：`pcb_PrimitiveComponent.getAll()` + `getAllPinsByPrimitiveId()`，`pcb_PrimitiveLine/Via/Pour/Pad.getAll()`。

> ⚠️ **路线 B 的重建是有已知缺陷的**，只能兜底，不能当唯一真值：
> 靠"引脚坐标 + 导线端点"做并查集时，**同名网络标签分散在不同导线簇里不会被合并**
> （例如两个都叫 `PDT` 的簇会被当成两条网）。若必须用 B，**务必用 PCB 焊盘网络名交叉验证**。

**PCB 焊盘 `getState_Net()` 返回真实网名（`GND`/`PDT`/`$1N140`…），是判断连通性最权威的一手数据** ——
判断"某元件某脚接哪"时先看它，别只信坐标重建。

产出的原始数据落到工作区的 `tmp/`，不要只留在对话里。

---

## 2. 重建/核对网表

若用路线 B，按下面做，并**逐条自检**：

1. 并查集：把**同一根导线**的所有端点连到首点（`union(pts[0], pts[i])`，别把点跟自己 union）；
   `find` 要处理"未注册的点"（先 `parent.set(a,a)`），否则所有孤立点会塌进同一组。
2. **必须按网络标签名合并同名簇** —— 漏了这步会系统性误判连通性。
3. 引脚坐标是 `(x,y)` 整数，键要带精度；**坐标单位**：PCB 是 mil，原理图是 0.01英寸(10mil)，别混。
4. 交叉验证：原理图重建出的每个网络，与 PCB 焊盘网名对一遍；对不上的地方**逐个查**，别放过。

---

## 3. 检查清单

> 📎 深挖：**DRC 报错→含义/修复方向**的对照表见 `references/drc-and-checklist.md` §1–2；
> 质量门、网标命名规范、"真元件/假元件"判据见同文件 §3–5。

### A. 原理层面（DRC 不会告诉你的高价值项）
- **电源/充电拓扑**：充电器输入(VBUS/VCC)有无去耦（≥1µF）；PROG 电阻决定的充电电流是否匹配电池容量。
- **端接电阻**：USB-C 的 CC1/CC2 是否有 **5.1k 对地 Rd**（下拉到 GND，**不是**只串到 MCU）；
  判断时看电阻**另一端是否落在 GND 网**，别只看它接了 MCU。
- **悬空/单点网络**：只有 1 个引脚的网络 = 悬空（如状态输出 `CHRG`）；名字含 `RST`/`EN` 的脚悬空是经典风险。
- **死网络 / 孤儿支路**：一个串联支路（如 R–C）若两端都只连这两个元件本身、不接入别的引脚，要问清意图；
  但注意**串联 RC 的中点本来就只连这两个元件**，那不算"没接"——RC 滤波/吸收是合理用法，别误判为死元件。
- **器件设计值 vs 绑定物料**：逐个比对"Value"与绑定的立创编号描述（如设计 2.2Ω 却绑了 5.1kΩ = BOM 误绑）。
- **重复位号**：同名位号若非多子部件器件，必冲突，会导致原理图/PCB 器件数对不上。
- **未命名/自动网络**（`$1Nxxx`）成堆 → 网标不规范，后续维护易错。
- **测试点、跳线、网络标签**在原理图里常表现为"1 脚器件"，做器件统计时要分辨。

### B. PCB 布局布线
- **DRC 逐条核实**：把"真违规"和"疑似误报"分开。板框↔铜箔/槽孔为 0 间距是真问题（铣边切铜）。
- **线宽 vs 载流**：电源/大电流网络是否够宽（对照走线宽度与预期电流）；细线段单独列出。
- **去耦距离**：旁路电容到 IC 电源脚的距离（越近越好）。
- **缝合过孔**：双面板 GND 缝合孔数量是否够；发热器件（MOS/发热片）散热铜皮/散热孔是否足。
- **铺铜**：铺铜边界是否超出板框；死铜。
- **环宽/工艺**：小孔（如 0.65mm）的焊盘环宽是否接近工艺下限。
- **孤立焊盘**：不属于任何器件的 pad，靠 `pcb_PrimitiveComponent.getAllPinsByPrimitiveId()` **收不到**，
  只能从 `pcb_PrimitivePad.getAll()` 反查 —— 否则会把"独立焊盘/测试盘"误判为死铜。
- **板框**：`pcb_PrimitivePolyline.getAll()` 过滤 `layer === 11`，配 `pcb_Primitive.getPrimitivesBBox([id])` 量尺寸。

### C. 原理图 ↔ PCB 一致性
- **器件数**是否一致（不一致多半是重复位号或未转 PCB 的器件）。
- **引脚↔焊盘映射**：符号引脚数 vs 封装焊盘数、焊盘编号是否对齐（不一致会报 `PIN2PAD`）。
  典型病征：4 脚符号只落到 3 个焊盘 → 某脚（常是 GND）悬空。

---

## 4. 输出

- 报告写到项目工作区，命名 `<项目名>_设计检查报告_<日期>.md`（原理/布局审查另起或合并均可）。
- 结构：先给**结论分级**（🔴必改 / 🟠建议 / 🟡待确认 / 🟢可选），每条给"**证据（网名/坐标/实测值）+ 判据 + 建议**"。
- 关键连通性结论**附上原始证据**（网名或坐标），方便用户复核——本流程出过错，证据是纠错的地基。
- 收尾把激活文档**切回**原文档。

---

## 5. 陷阱清单（都踩过）

1. 送桥接的代码**不能有注释**（会被拼成一行，`//` 把后面全注释掉）。
2. `sch_Netlist.getNetlist()` 已废弃、会超时；`sch_Net.getAllNets()`/`getCurrentProjectAllNets()` 返回空。
   **但网表并非拿不到** —— 用 `sch_ManufactureData.getNetlistFile(name, ESYS_NetlistType.JLCEDA_PRO)`
   （见 §1 路线 A），这是权威的连通性真值。别因为前者废了就退回到坐标重建。
3. 坐标重建**不合并同名网标**（见 §1），是误判连通性的头号来源。有官方网表就别用坐标法。
4. 并查集两个经典 bug：点跟自己 union；未注册点没初始化。
5. 单位：PCB=mil，原理图=0.01in。
6. 孤立焊盘只能从全量 pad 反查（见 §3B）。
7. 别把"照抄模板/看起来像"当结论 —— 每条判断都回读原始数据确认（网名、坐标、实测间距）。
8. 只读审查**不改设计**；任何改动都属"大改"，动手前先说明"改哪个文件、删什么、加什么"并等确认。

> 📎 **取数/判读陷阱与验收方法论**已系统整理在 `references/pitfalls.md`
> （连接与环境、单位与坐标、读错文档、铺铜判据、API 可用性、以及"假绿 / 自证循环 / 数量&位置对账 / DRC 真伪分拣 / 五步诊断法"）。
> **报结论前先过一遍**——尤其"DRC 结果必须实测确认并逐条真伪分拣"这一条。

---

## 6. 脚本与参考文件

**脚本**（`scripts/`）：

| 文件 | 用途 |
|---|---|
| `export_connection.mjs` | **内置「导出连接关系」**：`node export_connection.mjs <outDir> [--mode netlist\|region\|both] [--port 49620]`，直接落网表/区域 JSON，免手动点插件 |
| `eda_payloads/export_netlist.js` | EDA 端 payload：`getNetlistFile` 取全工程 ENET 网表 |
| `eda_payloads/export_region.js` | EDA 端 payload：复刻插件，把框选区域导成 `jlc-schematic-region` |
| `parse_enet.mjs` | 把 ENET 或 region JSON 规范化成统一网表，并打印器件/网络/未连接引脚 |
| `eda_exec.mjs` | 通用执行器：`node eda_exec.mjs <js文件> [端口]`，跑任意 EDA 端 JS 片段 |

**参考文件**（`references/`）：

| 文件 | 内容 | 来源 |
|---|---|---|
| `connection-json-formats.md` | ENET 与 `jlc-schematic-region` 两种连接关系格式、字段含义、内置导出用法 | 逆向《让AI看看你的原理图》插件（Apache-2.0 源码） |
| `pitfalls.md` | 取数与判读陷阱（连接/单位/读文档/铺铜/API 可用性）+ 验收方法论（自证循环、数量&位置对账、DRC 真伪、五步诊断法） | 提炼自 SkillHub `easyeda-sch-to-pcb` 的坑清单与验收体系 |
| `drc-and-checklist.md` | DRC 报错翻译表、修复优先级决策树、质量门（改造为审查检查项）、网标命名规范、"真元件/假元件"判据、交付物自洽 | 提炼自 SkillHub `pcb-design-assistant`（MIT） |

> 三份参考都是**只读审查视角**的提炼（去掉动手步骤）；改板（写）专属的坑（源文本手术、分批写入、页签额度、唯一 uuid 等）
> 只在 `pitfalls.md` §H 留了索引，真动手改板时再回看外部原 skill 的完整坑清单。
