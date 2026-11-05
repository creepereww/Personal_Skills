---
name: local-jlceda-board-build
description: 在真实嘉立创EDA专业版里做「写」操作——建工程、放器件、连线与网络标签、功能分区框、布局、布线、铺铜、导出制造资料。与只读审查（local-jlceda-design-review）严格分工，本 skill 只管改。含写循环六步（基线→计划→dry-run→写→回读→保存重开）、S0–S5 阶段与 G0–G6 门禁、实测过的 sch/pcb 子命令地图。用户说"帮我画/改/布线/铺铜/出 Gerber/建板"时用。
version: v0.1
---

# 嘉立创EDA 建板 / 改板

> **成熟度 `v0.x`** → 模型可直接改，改完回报"改了哪个文件、改了什么"即可。
> **只做写**。只读审查、取数、检查清单走 `local-jlceda-design-review`；动手前先用它拿一遍现状。
> 本文件只放稳定方法，不放具体项目数据。

## 0. 硬边界

1. **无授权不写**。动手前说清「改哪个文档、删什么、加什么」，等用户确认。
2. **先读后写**。任何写入前先 `sch list --include-pins` / `pcb dump` 拿真实基线。
3. **一次一改**。一次只写计划内对象；部分成功或超时**先查真实状态，禁止整批盲重试**。
4. **写完必须回读**。`save` → `doc reload` → 再读一次，确认重开后还在，才算落地。
5. **删改类动作会被 connector 拦**（`page-delete` / `component delete` / `route delete` / `pour delete` /
   `outline` 设置等标 `needsConfirm`）—— 这不是故障，是设计。

## 1. 前置

```bash
easyeda daemon health            # windows 非空；connector 版本与 CLI 对齐
easyeda project info             # 确认工程 uuid
easyeda doc ls --project <P>     # ★ 为激活文档
```

- **文档 uuid 会轮换**（每次保存可能换新 uuid，工程里会攒出多个同名 `P1`）。
  一律取 `doc ls` 里带 ★ 的那条，**按 uuid 操作，别按名字**。
- 改扩展权限 / 升级 connector 后要**关掉所有 EDA 标签页重开**。
- 前台决定命令可用性：`sch_*` 要前台是原理图、`pcb_*` 要 PCB。`--project` 只路由不切前台。

## 2. 写循环（每次都走）

```
① 基线   sch list --include-pins / pcb dump          拿到 primitiveId、ref、pin-net
② 计划   明确动哪些、不动哪些（列 id 或 ref），说给用户听
③ 演练   支持 --dry-run 的先跑（destagger / apply / apply playbook / arrange / layout-plan）
④ 写入   真正执行
⑤ 回读   再读一次，逐项比对（数量、坐标、net 成员）
⑥ 保存    sch save / pcb save → doc reload → 再读，确认持久化
```

**调用成功 / 写入成功 / 保存成功 / 重开后仍在 / 质量通过 是五件不同的事**，
缺哪一项记 `NOT RUN`，不许合并成"已完成"。

## 3. 阶段与门禁

`S0 读取 → S1 需求/约束 → S2 方案/核算 → S3 原理图 → S4 PCB → S5 检查/交付`

门禁是**证据门，不是审批门**：自查、记录、继续，只有证据缺失才停。

| 门 | 硬规则 |
|---|---|
| G0 需求 | 关键规格（电压/电流/尺寸/接口）没定，不往下画 |
| G1 功能冻结 | 冻结后不增删器件；要改先解冻并说明 |
| G2 原理图 | **G2 未过不 `import-changes`、不布局 PCB** |
| G3 布局 | `layout-lint` 过 + 器件数与原理图对账 |
| G4 电源地 | 铺铜 / 过孔 / 地平面；与 G3 并列，是布线前置 |
| G5 布线 | 全部信号网连通 + PCB DRC 0 |
| G6 制造 | BOM / Gerber / 钻孔 / CPL 齐 + `.epro2` 恢复演练 |

- **G6 未过不说"可打样/可量产"**。导出能力以 `easyeda capabilities` 逐项状态为准，
  缺的记 `NOT RUN`，不要用"应该能导"糊过去。
- 结论只取 `PASS` / `PASS_WITH_WAIVER` / `BLOCKED` / `UNSUPPORTED`；缺证据一律 `BLOCKED`。

## 4. 命令地图（实测 `--help`，167 个 typed action / 102 个写入）

### 原理图 `easyeda sch <cmd>`

| 用途 | 命令 |
|---|---|
| 读现状 | `list --include-pins`、`read`、`nets`、`netlist`、`status` |
| 页管理 | `page-new`、`page-rename`、`pages`、`rename` |
| 器件 | `place`、`modify`、`replace`、`rebind-symbol`、`rebind-footprint`、`designators`、`resolve-lcsc` |
| 连线（首选） | **`connect`**（引脚出桩 + 远端放标签）、`autoconnect`、`disconnect`、`no-connect` |
| 连线（其它） | `block-apply`（整块电路：放件+内部网+绑端口）、`wire`（**逃生口**，常规别用）、`netflag` |
| 布局 | `autolayout`、`autoplace-free`、`align`、`distribute`、`group-move`、`group-arrange`、`destagger` |
| 布局评估 | `layout-lint`（重叠/间距）、`layout-score`（可读性）、`clusters` |
| 分区与图签 | `zones set` / `zone-draw` / `zone-plan` / `zone-arrange`、`titleblock`、`frame`、`sheet` |
| 校验 | `check`、`bridge-check`、`drc`、`reconcile`、**`gate`**（S5 一键：layout-lint→check→bridge-check→drc） |
| 收尾 | `save`、`export-image`、`prim-delete`（慎用）、`clear`（清页，危险） |

> 需要"块级复用"时走 `compose` / `block-apply`，别手搓一堆 `wire`。
> `wire` 的 help 自己写着 "ESCAPE HATCH；常规布线走 autoconnect / block-apply"。

### PCB `easyeda pcb <cmd>`

| 用途 | 命令 |
|---|---|
| 读现状 | `dump`、`list`、`board-info`、`layers`、`drc-rules`、`nets` |
| 建板 | `new-board`、`import-changes`（原理图 → PCB）、`add-component`、`sync-designators`、`sync-attrs` |
| 板框 | `outline-set` / `outline-get` / `outline-fit` / `outline-round`、`slot` |
| 布局 | `layout-plan`、`auto-place`、`arrange`、`align`、`distribute`、`grid-snap`、`modify`、`lock`、`place-constrained` |
| 布局评估 | `layout-lint`、`layout-score`、`floorplan`、`report` |
| 布线 | `route`、`route-short`、`route-critical`、`track`、`via`、`via-hop`、`via-stitch`、`via-fence` |
| 布线（外部） | `export-dsn` → 外部 Freerouting → `import-autoroute`；或 `autoroute` 一把梭 |
| 撤线 | `rip-up`（按网）、`track-delete` / `via-delete`（按 primitiveId）、`beautify`（圆角） |
| 铜 | `pour` / `pour-rebuild` / `pour-list`、`power-pour`、`power-planes`、`fill`、`region`、`pour-clean` |
| 丝印 | `silk-add` / `silk-set` / `silk-align` / `silk-import-svg`、`silk-zone-outline` |
| 校验 | `drc`、`check`、`drc-rules-set`、`net-path`（关键网连通证明） |
| 收尾 | `save`、`snapshot`、`stackup` |

### 其它

- 工程：`project create / open / info / export / export-source`
- 库：`lib`（搜索、绑料）
- BOM：`bom export / enrich`
- 产物：`artifact`

## 5. 坑（都实测过）

1. **`sch list` 必须在 `sch netlist` 之前调** —— netlist 导出（含 `debug exec` 回退）会把文档留在
   `unknown or non-sync transaction` 状态，之后 `sch list` 返回 **0 个器件**。
2. **`sch list` 返回 0 / `sch check` 返回 null 都不报错** —— 命令成功 ≠ 读到了。先分清"没发现问题"和"没查成"。
3. **屏蔽区域**：`sch netlist` 排除、`sch list` / `sch connectivity` 不排除，connector 无开关。
4. **重复 UniqueId 会让 ENET 漏器件**（两个不同位号共用一个 uid，复制粘贴残留），比重复位号更隐蔽。
5. **器件被放在非整数坐标上**会让导线变斜，`sch check` / `bridge-check` 直接崩
   （报 `Unknown wire contact … seg=[x1,y1,x2,y2]`，两端 x/y 都不相等）。修法是**删掉该器件重放**，
   只删线重画没用 —— 引脚本身就在非栅格位置。
6. **多份同名页**：切文档一律按 uuid，按名字会切到旧副本并报 `获取所有器件失败`。
7. `debug exec` 的 JS **最后必须 `return`**，默认 20s 超时；对 native 对象做 `for...in` 会卡死到超时。
8. 单位：PCB = mil，原理图 = 0.01in（10mil）。别混。

## 6. 交付前自检

- [ ] `sch gate` 四项全过（或逐项记 `NOT RUN`/豁免理由）
- [ ] `pcb check`（DFM）+ `pcb drc` 逐条真伪分拣，不是只看 passed
- [ ] 关键网有 `net-path` 连通证明，不靠"看起来连着"
- [ ] 器件数：原理图 ↔ PCB 对账一致
- [ ] `save` → `doc reload` → 回读，三者一致
- [ ] 导出物（BOM / Gerber / 钻孔 / CPL）真的存在，不是"应该能导"
- [ ] 报告写清每条的**状态**（`PASS` / `WAIVED` / `NOT RUN`），**`WAIVED` ≠ 已解决**
