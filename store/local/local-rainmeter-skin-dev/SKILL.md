---
name: local-rainmeter-skin-dev
description: 开发或修改 Rainmeter 桌面皮肤。含本机坐标（程序/皮肤根/配置目录）、ini 的五个节与官方硬规则、编码选择（中文用 UTF-16 LE BOM）、Update 周期与性能陷阱、WebParser/插件/Lua 集成，以及"用脚本生成 ini"的项目架构。触发：做/改 Rainmeter 皮肤、雨滴皮肤、.ini 皮肤文件、皮肤改了没反应、中文乱码、CPU 占用高、WebParser、Lua 脚本、皮肤打包。
version: v0.1
---

# Rainmeter 皮肤开发

## 本机坐标（实测）

| 项 | 位置 |
|---|---|
| 程序 | `D:\APP_BEAUTIFY\Rainmeter\Rainmeter.exe` |
| **皮肤根** | `C:\Users\cgw06\Documents\Rainmeter\Skins\` |
| 配置 / 布局 | `C:\Users\cgw06\AppData\Roaming\Rainmeter\` |
| 第三方插件 | `Skins\@Vault\Plugins\` |
| 现有皮肤 | `NotionTodo\`（自建，**由脚本生成 ini**）、`illustro\`（自带示例） |

## 一个皮肤长什么样

```
Skins\<根配置>\<皮肤名>\<皮肤名>.ini
```

- **config name** = 从 `Skins\` 起的相对路径（如 `NotionTodo`）—— 多数功能（尤其 `!Bang` 命令）用它指代皮肤，**不是文件名**
- **变体**：同一目录放多个 `A.ini`/`B.ini` = 同一皮肤的不同变体，**同时只能激活一个**；要当作独立皮肤就**必须分目录**
- **`@Resources/`**：图片、字体、光标、Lua、脚本等支撑文件，放在**根配置**目录下（`Skins\<根配置>\@Resources\`），子皮肤共享

详见 `references/skin-structure.md`。

## ini 的六个节

| 节 | 作用 |
|---|---|
| `[Rainmeter]` | 整个皮肤的选项（`Update` 周期等） |
| `[Variables]` | 变量 |
| `[Metadata]` | 名称 / 版本 / 许可（对外发布建议写） |
| `[Measure*]` | **取数据**：时间、CPU、`WebParser`、插件、Lua |
| `[Meter*]` | **显示**：`String` / `Image` / `Bar` / `Shape` … |
| `[Style*]` | 给 `MeterStyle` 复用的选项模板 |

**至少要有 1 个 `Meter`**，其余都可选。

## 官方硬规则（写错就静默不生效）

1. 节名与选项名**只用字母数字** —— 无空格、无标点
2. 节名**全局唯一**；同一节内选项名唯一
3. 选项值**必须在同一行**内
4. 值**不要加引号**（Rainmeter 会忽略引号）

## 开发循环

```
改 <皮肤>.ini  →  刷新（右键皮肤 → Refresh，或 !Refresh bang）  →  看 error.log
```

**改了不刷新 = 没生效**（这是最常见的"改了没反应"）。刷新会应用 ini 改动，并把所有值重置。

报错都写在**皮肤目录下的 `error.log`**（本机 `NotionTodo\error.log` 就是这个）。

## 编码（本机踩过的坑）

| 编码 | 能用吗 |
|---|---|
| **UTF-16 LE（带 BOM）** | ✅ **推荐** —— 本机自建的 `NotionTodo.ini` 就是它，中文稳 |
| 无 BOM 的 UTF-8 | ⚠️ 能跑（自带 illustro 就是），但含中文/特殊字符有风险 |
| ANSI / GBK | ❌ 中文必乱码 |

**结论**：写中文皮肤**一律 UTF-16 LE with BOM**。细节与排查见 `references/encoding.md`。

## 性能与交互

默认 `Update` 是 **1000ms**。高频测量（CPU、网络、WebParser）必须配 `UpdateDivider` 降频；
`DynamicVariables=1` 能开但**有代价**。

详见 `references/interaction-performance.md`。

## 细节参考

| 文件 | 讲什么 |
|---|---|
| `references/encoding.md` | 编码选择、BOM、中文乱码排查与批量转换 |
| `references/skin-structure.md` | 目录 / 变体 / `@Resources` / config name |
| `references/interaction-performance.md` | `Update` 周期、`UpdateDivider`、鼠标交互、性能陷阱 |
| `references/api-integration.md` | `WebParser` / 插件 / Lua 脚本 |
| `references/project-template.md` | 最小可用模板，以及本机 NotionTodo 的「脚本生成 ini」架构 |
