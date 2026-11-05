---
name: local-jlceda-design-review
description: 嘉立创EDA(EasyEDA)工程的原理图 + PCB 设计审查方法与流程 —— 不止看 DRC，而是重建网表做电路级审查（电源/充电拓扑、端接 Rd、悬空脚、去耦、BOM 误绑、重复位号）与布局布线审查（线宽载流、去耦距离、缝合过孔、铺铜与板框、环宽、散热）。当用户说"帮我检查/审查原理图""PCB 布局布线有没有要优化的""原理图原理有没有错""做个设计评审""出一份检查报告"，或在嘉立创EDA/EasyEDA 里对着某个工程要做设计审查时使用。取数依赖 easyeda-agent（connector）的 CLI/daemon。
version: v0.7
---

# 嘉立创EDA 原理图/PCB 设计审查

> **给改我的人**：成熟度 `v0.x`（完善中）→ 可直接改，改完回报"改了哪个文件、改了什么"即可。
> 本 skill 是**通用**的（跨机器成立）：**别写死**本机磁盘路径、端口、工程名、器件位号 —— 那些属于项目/机器，
> 放项目工作区或 `store/machine/`。仓库规则见 `local-skills-hub`。
>
> **本 skill 只读**。要动设计（建板/改板/布线/铺铜/导出）走 `local-jlceda-board-build`。

本 skill 只管**审查的方法与流程**。与 EDA 的连接与取数交给 **`easyeda-agent`（connector）**——
具体命令见 `references/connector-commands.md`，这里不重复。

审查分三层，**别只做第三层**：
1. **原理层**（DRC 不会告诉你）—— 电路拓扑对不对
2. **布局布线层** —— 好不好、有没有余量
3. **一致性/规范层** —— DRC、原理图↔PCB 是否同步

---

## 0. 前置：数据通道

走 `easyeda-agent` 的 typed 命令（CLI + daemon + Connector 扩展）：

- 健康：`easyeda daemon health`（看 `windows` 是否非空、`connector` 版本）。CLI 不在 PATH 时用全路径或 `$EASYEDA_BIN`；
  `scripts/eda_conn.py` 会按 `$EASYEDA_BIN` > PATH > `~/.local/bin/easyeda[.exe]` 自动探测。
- **前台文档决定命令可用性**：`sch_*` 要前台是**原理图**、`pcb_*` 要前台是 **PCB**；`--project` 只做路由、不切前台。
  本项目两个 export 脚本会**自动切前台**，省掉手动 `doc open`。
- 认 uuid：`easyeda doc ls --project <名>`（`★` = 激活）。多开工程时先确认各栈绑的是哪个窗口。
- 送 `debug exec` 的 JS 由 EDA 端执行 → **多行、注释、`await` 都正常**，最后必须 `return`（`result.value` 即结果）。

---

## 1. 数据获取：连通性真值优先

### 首选 —— 一条命令导出全部（内置、免手动）

```bash
python scripts/export_connection.py <工作目录>/<项目名>/ --project <项目名> --mode all
python scripts/parse_enet.py <工作目录>/<项目名>/netlist.enet.json   # 规范化 + 可读打印
python scripts/export_pcb.py     <工作目录>/<项目名>/ --project <项目名> --mode all
```

- 约定：**在工作目录下按工程名建文件夹**，产物都落这里。
- 产物：`netlist.enet.json`（**连通性真值**）、`sch_parts.json`（**已排除屏蔽区**的有效器件+引脚网）、
  `sch_parts_all.json`（全量，每条带 `netlisted` 标记）、`connectivity.json`（IR，带 `issues[]`）、
  `sch_check.json`（逐项检查）、`pcb_dump.json`（几何+焊盘网络）、`pcb_drc.json`、`pcb_check.json`（DFM）等。

**为什么用官方 ENET 网表**：它已是**抽象层**（网络↔引脚），从根上避开"连通性重建"，且覆盖**全工程**。

> ⚠️ **ENET 有盲区**：按 Unique ID 建索引，**漏掉 UniqueId 为空的器件**（遗留占位/屏蔽区域占位）。
> 所以"**重复位号 / 游离器件 / 器件数对账**"要看 `sch_parts.json`（源自 `sch list` 全量），不能只看 ENET。

### ⚠️ 屏蔽区域：三个命令口径不一致（脚本已统一）

| 命令 | 排除屏蔽区？ |
|---|---|
| `sch netlist`（ENET） | ✅ 排除 |
| `sch list` | ❌ 不排除 |
| `sch connectivity` | ❌ 不排除，**且屏蔽区里的重名件会让它整体拒绝导出** |

connector 没有开关可调，所以脚本自己处理（见 `export_connection.py` 顶部注释）：

1. 以 ENET 的 `props["Unique ID"]` 集合当"有效器件"白名单；
2. `sch_parts.json` 只写白名单内的器件，全量落 `sch_parts_all.json`（加 `--include-shielded` 可保留全量）；
   重复位号也只在**有效器件**内统计，屏蔽区重名只作提示、不算错；
3. `sch connectivity` 失败时**直接用 ENET 合成同 schema 的 IR**（`_source: "synth-from-enet"`，
   天然排除屏蔽区、无坐标、issues 只含 `unconnected-pin`），不再被"重名件"卡死；
4. **执行顺序必须是「先 `sch list`，再 `sch netlist`」** —— netlist 导出会把文档留在
   `unknown or non-sync transaction` 状态，之后 `sch list` 会返回 0 个器件。

> ⚠️ **重复 UniqueId 比重复位号更隐蔽**：`sch list` 会把两个不同位号报同一个 uid（复制粘贴残留），
> ENET 按 uid 建索引 ⇒ **直接漏掉其中一个器件**。脚本会打印 `! 重复 UniqueId ...: A / B`，见到就要改。


### 兜底 —— `debug exec` 取原始图元本地重建

typed 命令覆盖不到时（要一次性读导线坐标、量距离…），用 `scripts/eda_exec.py` 跑任意 `eda.*` JS：

```bash
python scripts/eda_exec.py <js文件> --project <项目名>   # 文件里最后 return
```

> ⚠️ **坐标重建有已知缺陷**，只能兜底：靠"引脚坐标 + 导线端点"做并查集时，**同名网络标签分散在不同导线簇里不会被合并**。
> 若必须用，**务必先用 ENET / PCB 焊盘网名交叉验证**。

**PCB 焊盘带真实网名**（`pcb_dump.json` 的 `components[].pads[].net`）——判断"某元件某脚接哪"时先看它，别只信坐标。

### 检查器会给"专业项"

`sch_check.json` / `pcb_check.json` 是**重建式逐项检查**，粒度比 SDK DRC 细（悬空脚、几何-网络不一致、零长线、
走线角度、clearance、decapTooFar、powerNotPoured…）。**但这些是"线索"不是"结论"** —— 高 severity 项要交叉验证（见 §5）。

---

## 2. 重建/核对网表

若用坐标兜底重建，按下面做，并**逐条自检**：

1. 并查集：把**同一根导线**的所有端点连到首点（`union(pts[0], pts[i])`，别把点跟自己 union）；
   `find` 要处理"未注册的点"（先注册），否则孤立点会塌进同一组。
2. **必须按网络标签名合并同名簇** —— 漏了这步会系统性误判连通性。
3. 引脚坐标是整数，键要带精度；**单位**：PCB 是 mil，原理图是 0.01英寸(10mil)，别混。
4. 交叉验证：重建出的每个网络，与 ENET / PCB 焊盘网名对一遍；对不上就**逐个查**。

---

## 3. 检查清单

> 📎 深挖：**DRC 报错→含义/修复方向**的对照表见 `references/drc-and-checklist.md` §1–2；
> 质量门、网标命名规范、"真元件/假元件"判据见同文件 §3–5。

### A. 原理层面（DRC 不会告诉你的高价值项）
- **电源/充电拓扑**：充电器输入(VBUS/VCC)有无去耦 —— **按本型号手册定值，不要套"≥1µF"泛规则**
  （例：SA4351 明确要求 VCC-GND 接 0.1µF/50V 串联 2.2Ω 以抗热插拔；别家 1A 充电 IC 则要 ≥1µF，
  拿谁的手册决定结论 —— 拿不到本型号手册就只能写 `待确认`，见 `references/pitfalls.md` §H）；
  PROG/ILIM 电阻决定的充电电流是否匹配电池容量。
- **端接电阻**：USB-C 的 CC1/CC2 是否有 **5.1k 对地 Rd**（下拉到 GND，**不是**只串到 MCU）；
  判断时看电阻**另一端是否落在 GND 网**，别只看它接了 MCU。
- **悬空/单点网络**：只有 1 个引脚的网络 = 悬空（如状态输出 `CHRG`）；名字含 `RST`/`EN` 的脚悬空是经典风险。
  工具侧：`sch_check.json` 的 `floatingPins` + `connectivity.json` 的 `issues[code=unconnected-pin]`。
- **死网络 / 孤儿支路**：一个串联支路（如 R–C）若两端都只连这两个元件本身、不接入别的引脚，要问清意图；
  但注意**串联 RC 的中点本来就只连这两个元件**，那不算"没接"——RC 滤波/吸收是合理用法，别误判为死元件。
- **器件设计值 vs 绑定物料**：逐个比对"Value"与绑定的立创编号描述（如设计 2.2Ω 却绑了 5.1kΩ = BOM 误绑）。
- **重复位号**：同名位号若非多子部件器件，必冲突，会导致原理图/PCB 器件数对不上，**且 `sch connectivity` 会整体拒绝导出**。
  **查它用 `sch_parts.json`（`sch list` 全量），不能用 ENET** —— ENET 会漏掉无 UniqueId 的那个。
- **未命名/自动网络**（`$1Nxxx`）成堆 → 网标不规范，后续维护易错。
- **测试点、跳线、网络标签**在原理图里是 `componentType` 为 `netflag`/1 脚器件，做器件统计时要分辨。

### B. PCB 布局布线
- **DRC 逐条核实**：把"真违规"和"疑似误报"分开。板框↔铜箔/槽孔为 0 间距是真问题（铣边切铜）。
- **DFM（`pcb_check.json`）**：danglingEnds（悬空铜）、acuteAngles（锐角）、clearance、
  silkscreenFlipped（丝印反）、singleLayerVias（单层过孔）、duplicateSegments（重复走线）、
  parallelCoupling（3W 耦合）、powerNotPoured（电源未铺铜）、widthUnderSpec（线宽不足）、
  decapTooFar（去耦太远）、silkOverPad（丝印压焊盘）、viaInPad、fiducialMissing（缺基准点）。
- **线宽 vs 载流**：电源/大电流网络是否够宽（对照走线与预期电流）；细线段单独列出。
- **去耦距离**：旁路电容到 IC 电源脚的距离（越近越好，工具侧看 `decapTooFar`）。
- **缝合过孔**：双面板 GND 缝合孔数量是否够；发热器件散热铜皮/散热孔是否足。
- **铺铜**：铺铜边界是否超出板框；死铜。
- **环宽/工艺**：小孔的焊盘环宽是否接近工艺下限。
- **孤立焊盘**：不属于任何器件的 pad，靠"按器件取焊盘"**收不到** —— 只能从全量 pad 反查
  （`pcb_dump.json` 的 `components[].pads[]` 之外，注意 `pad` 总数与器件内 pad 数的差额）。
- **板框**：看 `pcb_outline.json`（`bbox` / `centerlineBBox` / `points`）；**要求前台是 PCB**。

### C. 原理图 ↔ PCB 一致性
- **器件数**是否一致（不一致多半是重复位号或未转 PCB 的器件）。
- **引脚↔焊盘映射**：符号引脚数 vs 封装焊盘数、焊盘编号是否对齐（不一致会报 `PIN2PAD` / `Netlist Error`）。
  典型病征：4 脚符号只落到 3 个焊盘 → 某脚（常是 GND）悬空。
- **Board 绑定**（`pcb_board.json`）：`linked:true` 且原理图/PCB uuid 对得上；对不上会报 `Netlist Error`。

---

## 4. 输出

- 报告写到项目工作区，命名 `<项目名>_设计检查报告_<日期>.md`（原理/布局审查另起或合并均可）。
- 结构：先给**结论分级**（🔴必改 / 🟠建议 / 🟡待确认 / 🟢可选），每条给"**证据（网名/坐标/实测值）+ 判据 + 建议**"。
- 关键连通性结论**附上原始证据**（网名或坐标），方便用户复核——本流程出过错，证据是纠错的地基。
- 收尾把激活文档**切回**原文档。

### 4.1 证据口径（硬要求，详见 `references/evidence-and-gates.md`）

**一次"审查"由五态分别成立**，不许合并成"已审查"：
`① 读取 → ② 网表编译 → ③ 交叉验证 → ④ 回读 → ⑤ 几何/质量`。
缺哪一态就在报告里标哪一态为 `NOT RUN` / `待确认`。

**每条结论必须挂状态**：`已验证` / `有条件满足` / `不满足` / `待确认` / `不适用`（须写理由）/
`NOT RUN`（工具跑不起来）/ `WAIVED`（用户暂不处理，**≠ 已解决**）。

**报告开头的数据来源行要写清五态结果**，例如：

```
数据来源：ENET ✅ / sch_parts ✅（已排除屏蔽区 7 件）/ connectivity ⚠ENET 合成 /
         sch_check ❌ NOT RUN / bridge-check ❌ NOT RUN
⇒ 本轮几何类结论全部 NOT RUN，仅连通性与器件级结论有效。
```

### 4.2 审查门禁 R0–R6（映射自 EasyCirq 的 G0–G6）

门禁是**阶段退出证据门，不是审批门** —— 自查、记录、继续，不新增等待点：

| 门 | 硬规则 |
|---|---|
| R0 规格 | 缺关键规格（电压/电流/温度）⇒ 相关条目只能 `待确认` |
| R1 原理拓扑 | **R1 未过不审布局** |
| R2 器件物料 | 错料/重复位号/重复 UniqueId 未处理 ⇒ 不出口"可打样" |
| R3 连通性 | **网表拉不出 ⇒ 后续几何结论全部 `NOT RUN`** |
| R4 图面几何 | **检查器崩 ⇒ `NOT RUN`，绝不能当"0 问题"** |
| R5 PCB | **R1 未冻结不审 PCB**；空板 ⇒ `NOT RUN` |
| R6 交付 | **R6 未过不说"可打样/可量产"** |

结论只取四档：`PASS` / `PASS_WITH_WAIVER` / `BLOCKED` / `UNSUPPORTED`；缺证据一律 `BLOCKED`。

**豁免**：电气 DRC、网表对账、PCB DRC、关键网连通、保存重开、BOM 身份 **不可豁免**；
命名/图面整洁/丝印/测试计划可豁免，但必须写「范围 + 理由 + 剩余风险 + 复验条件」。

---

## 5. 陷阱清单（都踩过）

1. 送 `debug exec` 的代码**最后必须 `return`**；默认 20s 超时，慢调用用 `--timeout`。
2. `sch_Netlist.getNetlist()` 已废弃、会超时；`sch_Net.getAllNets()` 返回空。
   **但网表并非拿不到** —— `sch netlist` / `getNetlistFile(..., ESYS_NetlistType.JLCEDA_PRO)`（见 §1）是权威真值。
3. 坐标重建**不合并同名网标**（见 §1），是误判连通性的头号来源。有官方网表就别用坐标法。
4. 并查集两个经典 bug：点跟自己 union；未注册点没初始化。
5. 单位：PCB=mil，原理图=0.01in。
6. 孤立焊盘只能从全量 pad 反查（见 §3B）。
7. 别把"照抄模板/看起来像"当结论 —— 每条判断都回读原始数据确认（网名、坐标、实测间距）。
8. **`componentType` 是小写字符串**：`'part'` / `'netflag'` / `'sheet'`。`ESCH_PrimitiveComponentType` 等全局枚举在
   `debug exec` 环境是 `undefined`。
9. **ENET 网表会漏器件**（无 UniqueId）→ 一致性检查以 `sch list` 全量（`sch_parts.json`）为准，ENET 只当**连通性**真值。
10. **前台文档决定命令可用性**（`sch_*` 要原理图、`pcb_*` 要 PCB）—— 报 `获取所有器件失败` 先查前台。
11. **`sch connectivity` 遇重复位号整体拒绝导出** —— 命令层没有 exclude/ignore 开关；修法是**改设计**（换位号/改非器件）。
12. **检查器会"报多"且可能自相矛盾**：`sch check` 报的 `wire-contact` 异网短路，`sch bridge-check` 判 0 真短路、
    坐标复核也 0 接触 ⇒ 高 severity 项**必须交叉验证**再下结论（见 §5 参考文件）。
13. 只读审查**不改设计**；任何改动都属"大改"，动手前先说明"改哪个文件、删什么、加什么"并等确认。
14. **"命令成功"不等于"读到了"**：`sch list` 会静默返回 0 个器件（文档处于非同步态），
    `sch check` 会静默返回 `null`。见到 0 问题先分清"查过没发现"还是"没查成"。
15. **`sch list` 必须在 `sch netlist` 之前调**：netlist 导出（含 `debug exec` 回退）会把文档留在
    `unknown or non-sync transaction` 状态，之后的 `sch list` 返回 0 器件。
16. **屏蔽区域**：`sch netlist` 排除、`sch list` / `sch connectivity` 不排除（connector 无开关，
    已在 `export_connection.py` 里用 ENET 白名单兜底）。
17. **重复 UniqueId 比重复位号更隐蔽**：`sch list` 里两个不同位号共用同一 uid（复制粘贴残留），
    ENET 按 uid 建索引 ⇒ **整条漏掉一个器件**。脚本会打印 `! 重复 UniqueId …`，见到就要查。
18. **非正交（斜）导线会让检查器整体崩溃**：`sch check` / `bridge-check` 报
    `Unknown wire contact … seg=[x1,y1,x2,y2]`，两端 x/y 都不相等即为斜线。
    此时**几何类检查全部 `NOT RUN`**，不能当 0 问题。

> 📎 **取数/判读陷阱与验收方法论**已系统整理在 `references/pitfalls.md`
> （连接与环境、单位与坐标、读错文档、铺铜判据、API 可用性、以及"假绿 / 自证循环 / 数量&位置对账 / DRC 真伪分拣"）。
> **报结论前先过一遍**——尤其"DRC/检查器结果必须实测确认并逐条真伪分拣"这一条。

---

## 6. 脚本与参考文件

**脚本**（`scripts/`，Python 标准库，无第三方依赖）：

| 文件 | 用途 |
|---|---|
| `eda_conn.py` | 共享层：定位 easyeda CLI（`$EASYEDA_BIN` > PATH > `~/.local/bin/…`）、执行、解析 JSON 信封、列/切文档 |
| `export_connection.py` | **一条命令导出原理图数据**：`<outDir> [--project X] [--mode netlist\|parts\|connectivity\|check\|drc\|all] [--include-shielded]`（自动切前台到原理图；**parts/connectivity 已排除屏蔽区**，connectivity 失败时自动用 ENET 合成） |
| `export_pcb.py` | **一条命令导出 PCB 数据**：`<outDir> [--project X] [--mode dump\|drc\|check\|outline\|nets\|board\|all]`（自动切前台到 PCB） |
| `parse_enet.py` | 把 ENET / connectivity IR / 插件 region JSON 归一化成统一网表，打印器件/网络/悬空/单点网/IR issues |
| `eda_exec.py` | 通用逃生口：`<js文件> [--project X] [--timeout N]`，跑任意 `eda.*` JS（经 `debug exec`） |

**参考文件**（`references/`）：

| 文件 | 内容 | 来源 |
|---|---|---|
| `connector-commands.md` | connector 取数命令地图（命令→产物→关键字段）+ `debug exec` 用法边界 | 实机实测 easyeda-agent v1.9.0 |
| `connection-json-formats.md` | ENET / connectivity IR / `jlc-schematic-region` 三种连接关系格式与字段含义 | 实机导出 + 逆向《让AI看看你的原理图》插件（Apache-2.0 源码） |
| `pitfalls.md` | 取数与判读陷阱（连接/单位/读文档/铺铜/检查器真伪）+ 验收方法论（自证循环、数量&位置对账、五步诊断法） | 提炼自 SkillHub `easyeda-sch-to-pcb` 的坑清单与验收体系 |
| `evidence-and-gates.md` | **证据口径与审查门禁**：五态证据、状态语汇（含 `WAIVED`/`NOT RUN`）、R0–R6 门禁映射、豁免规则、反自欺清单 | 改编自 `智构 · EasyCirq` 的 G0–G6 门禁 + 六态证据体系（Apache-2.0） |
| `drc-and-checklist.md` | DRC 报错翻译表、修复优先级决策树、质量门（改造为审查检查项）、网标命名规范、"真元件/假元件"判据、交付物自洽 | 提炼自 SkillHub `pcb-design-assistant`（MIT） |

> 参考都是**只读审查视角**的提炼（去掉动手步骤）；改板（写）专属的坑只在 `pitfalls.md` §H 留了索引。
