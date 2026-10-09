# easyeda-agent connector 命令地图（取数用）

本 skill 的取数层建在 `easyeda-agent` 的 **typed 命令**之上（CLI + daemon + Connector 扩展）。
CLI 的完整命令树用 `easyeda --help` / `easyeda sch --help` / `easyeda pcb --help` 查；这里只列**审查会用到**的。

## 0. 通用约定

- CLI 位置：`$EASYEDA_BIN` > PATH > `~/.local/bin/easyeda[.exe]`（脚本 `scripts/eda_conn.py` 已自动探测）。
- **前台文档决定命令可用性**：`sch_*` 要前台是原理图、`pcb_*` 要前台是 PCB。`--project` 只做路由、不切前台。
- 输出信封：多数命令返回 `{id,type,version,ok,result,context}`；`ok:false` 时看 `error.code/message/detail`。
  少数（`sch connectivity`）直接吐 IR；`pcb check` 不加 `--json` 是**文本**。
- 单位：PCB 坐标 = **mil**；原理图 = **0.01 in(10 mil)**。

## 1. 取数命令（按审查目的）

| 目的 | 命令 | 产物 / 关键字段 |
|---|---|---|
| **连通性真值（全工程网表）** | `easyeda sch netlist` | 落 `.enet` 工件（`result.artifactPath`），与官方 ENET 同源 |
| **器件全量 + 引脚网络** | `easyeda sch list --include-pins` | `result.components[]`：`componentType`(part/netflag/sheet)、`designator`、`device`、`footprint`、`uniqueId`、`pins[{pinNumber,pinName,net,noConnected}]`、`addIntoBom`、`addIntoPcb`、`otherProperty.Value` |
| **布局无关连通性 IR** | `easyeda sch connectivity` | `{schemaVersion,components[],nets[],connections[],issues[]}`；网络成员在 `connections`（`componentId`+`pinNumber`+`netId`），按 `nets[].id` 关联 |
| **逐项重建式检查** | `easyeda sch check --json` | `result.summary`（floatingPins/geomNetMismatches/zeroLengthWires/markerOverlaps/…）+ `result.findings[]` |
| **官方 SDK DRC（原理图）** | `easyeda sch drc --json` | `result` 里的规范化报告 |
| **并线短路 / 孤儿桩** | `easyeda sch bridge-check` | `wire-bridge`(真短路) / `orphan-stub` / `orphan-flag` / `wire-tree` |
| **跨页网名审计** | `easyeda sch nets` | 同轨多名 / 单引脚网 |
| **PCB 几何快照** | `easyeda pcb dump --include-copper --out FILE` | 自包含 JSON：`components[](含 pads[].net)`、`outline`、`silk`、`copperLayers`、`rules`、`copper`、`routedLines` |
| **PCB DRC（规范化）** | `easyeda pcb drc --json` | 一行一条违规（`rule`/`objType`/`message`/`x,y`/`layer`/`objs`），含 binding 提示 |
| **PCB DFM 审计** | `easyeda pcb check --json` | `summary`：danglingEnds/acuteAngles/nonOrthogonal/clearance/silkscreenFlipped/singleLayerVias/widthMismatches/duplicateSegments/parallelCoupling/powerNotPoured/widthUnderSpec/silkOverPad/viaInPad/fiducialMissing… |
| **板框** | `easyeda pcb outline-get` | `bbox` + `centerlineBBox` + `points`（**要求前台是 PCB**） |
| **网络清单（PCB）** | `easyeda pcb nets` | `{count,nets[{net,length,color}]}` |
| **Board 绑定** | `easyeda pcb board-info` | 原理图↔PCB 的绑定关系（`linked`、双方 uuid） |
| **文档列表 / 切换** | `easyeda doc ls` / `doc open <name>` | 文本表（★=激活）；切前台 |
| **任意 `eda.*` JS** | `easyeda debug exec --code "<JS>" [--timeout N]` | `result.value`；**逃生口**，typed 覆盖不到时的取证 |
| **电路块库（离线）** | `easyeda blocks ls` | 内置 block 库，无需 daemon |
| **官方 API 速查（离线）** | `easyeda api search <kw>` / `easyeda api list` | 查 `eda.*` 签名 |

## 2. 脚本封装

| 脚本 | 用法 | 产出 |
|---|---|---|
| `scripts/export_connection.py` | `<outDir> [--project X] [--mode netlist\|parts\|connectivity\|check\|drc\|all]` | `netlist.enet.json`、`sch_parts.json`(+`sch_list.raw.json`)、`connectivity.json`、`sch_check.json`、`sch_drc.json` |
| `scripts/export_pcb.py` | `<outDir> [--project X] [--mode dump\|drc\|check\|outline\|nets\|board\|all]` | `pcb_dump.json`、`pcb_drc.json`、`pcb_check.json`、`pcb_outline.json`、`pcb_nets.json`、`pcb_board.json` |
| `scripts/parse_enet.py` | `<in.json> [out.normalized.json]` | 归一化网表（吃 ENET / region / connectivity IR 三种格式）+ 打印器件/网络/悬空/单点网/IR issues |
| `scripts/eda_exec.py` | `<js文件> [--project X] [--timeout N]` | 跑任意 `eda.*` JS，打印 `result.value` |

两个 export 脚本都会**先自动切前台**（原理图 / PCB），免手动 `doc open`。

## 3. `debug exec` 的用法与边界

- 写 `debug exec` 的代码要**以 `return` 结束**；`await` 可用；默认超时 20s（慢调用用 `--timeout`）。
- **它不会替你切前台**（raw JS 不做路由）：`eda.sch_*` 要看原理图、`eda.pcb_*` 要看 PCB。
  读回 0 条/空对象而对象确实存在时，先查前台是不是被上一个命令切走了。要切就先 `doc open`。
- 用于 typed 命令不覆盖的取证，例如：
  - 读导线坐标复核几何接触：`const w = await eda.sch_PrimitiveWire.getAll(); return w.map(x=>({net:x.net,line:x.line}));`
  - 量电容到电源脚距离：读引脚坐标后本地算（`pcb dump` 的 `pads[].x/y` 也可用）
  - 复刻插件框选导出 / 查区域结构
- **不要**用它做批量写（改板属"写"操作，见 `pitfalls.md` §H）。
