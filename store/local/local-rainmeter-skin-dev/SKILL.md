---
name: local-rainmeter-skin-dev
description: Rainmeter 桌面皮肤开发经验与踩坑指南。开发或修改 .ini 皮肤、用脚本动态生成皮肤、集成外部 API（Notion/GitHub）、实现交互（折叠/打勾/同步）、排查中文乱码、窗口不收缩、点击弹黑窗、变量污染、响应慢时使用。含本机坐标与官方硬规则。触发：Rainmeter 皮肤、雨滴皮肤、桌面小组件、皮肤中文乱码、皮肤不刷新、皮肤弹黑窗、动态生成皮肤、Notion 桌面待办。
version: v0.1
---

# Rainmeter 皮肤开发

基于真实项目（Notion Todo 桌面小组件）踩坑总结，覆盖从皮肤结构到 API 集成的全流程。

## 本机坐标

| 项 | 位置 |
|---|---|
| 程序 | `D:\APP_BEAUTIFY\Rainmeter\Rainmeter.exe` |
| **皮肤根** | `C:\Users\cgw06\Documents\Rainmeter\Skins\` |
| 配置 / 布局 | `C:\Users\cgw06\AppData\Roaming\Rainmeter\` |
| 第三方插件 | `Skins\@Vault\Plugins\` |
| 现有皮肤 | `NotionTodo\`（自建，**脚本生成 ini**）、`illustro\`（自带示例） |

## 核心工作流

1. **确定数据来源**：外部 API（Notion/GitHub）、本地文件、系统信息
2. **设计皮肤结构**：标题栏 + 内容区 + 底部栏，用 `MeterShape` 自定义背景
3. **动态生成皮肤**：用 PowerShell/Python 脚本读取数据，动态生成 `.ini` 文件
4. **实现交互**：折叠、打勾、同步按钮 → `LeftMouseUpAction` 触发
5. **后台同步**：乐观更新本地显示 + 静默同步到外部 API
6. **编码处理**：**严格区分**皮肤文件和脚本文件的编码要求（见下）

## 快速避坑清单

| 问题 | 现象 | 解决方案 |
|---|---|---|
| 中文乱码 | 皮肤显示？？？或方块 | 皮肤文件保存为 **UTF-16 LE**（Unicode） |
| 脚本中文乱码 | PowerShell 输出或 API 请求中文乱码 | 脚本保存为 **UTF-8 with BOM** |
| 窗口不收缩 | `DynamicWindowSize=1` 隐藏 meter 后窗口大小不变 | 用 **MeterShape** 自定义背景 + `!SetOption` 动态改高度 |
| 条件语法不解析 | `[#Var?True:False]` 显示原始文本 | Rainmeter **不支持三元表达式**，用两个独立 meter 切换显示 |
| 弹出命令行窗口 | 点击按钮闪一下黑色 cmd 窗口 | 用 **VBScript 包装器**（`RunHidden.vbs`）隐藏 PowerShell 窗口 |
| 点击不刷新 | 点击后内容不更新，需手动刷新 | 脚本执行完成后**自己调 Rainmeter `!Refresh`**，不要用皮肤里的 `[!Refresh]` |
| 变量污染 | 点号引用脚本后参数值被篡改 | 点号引用脚本前**保存参数值到新变量**，后续使用保存的值 |
| API 中文 400 错误 | 调 Notion API 报 Bad Request | 请求体显式转 **UTF-8 字节数组**，Content-Type 加 `charset=utf-8` |
| 响应慢 | 点击后 3–5 秒才生效 | **乐观更新**：先本地更新显示（瞬间），后台再同步 API |

## 官方硬规则（写错就静默不生效）

1. 节名与选项名**只用字母数字** —— 无空格、无标点
2. 节名全局唯一；同一节内选项名唯一
3. 选项值**必须在同一行**
4. 值**不要加引号**（Rainmeter 会忽略）

**至少要有 1 个 `Meter`**，其余节都可选。皮肤文件是标准 INI：`[Section]` + `Key=Value`。

## 目录与命名

```
Skins\<根配置>\<皮肤名>\<皮肤名>.ini
```

- **config name** = 从 `Skins\` 起的路径（如 `NotionTodo`）—— `!Bang` 命令用它指代皮肤，**不是文件名**
- **变体**：同目录多个 ini = 同一皮肤的不同变体（同时只激活一个）；要独立就**分目录**
- **`@Resources/`**：图片/字体/光标/Lua/脚本，放**根配置**下，子皮肤用 `#@#` 引用

改完**必须刷新**（右键 → Refresh 或 `!Refresh`）才生效；报错看**皮肤目录下的 `error.log`**。

## 详细参考

| 文件 | 讲什么 |
|---|---|
| `references/encoding.md` | **四种文件的编码要求各不相同**（皮肤 UTF-16 LE / ps1 UTF-8 BOM / vbs 必须 ANSI / 数据文件 UTF-16 LE） |
| `references/skin-structure.md` | 动态生成皮肤的结构、`DynamicWindowSize` 陷阱、三元表达式不支持 |
| `references/interaction-performance.md` | 黑窗、点击不刷新、乐观更新、变量污染、进程启动开销 |
| `references/api-integration.md` | Notion API 实战：Token、中文 400、查询/更新、性能优化、错误处理 |
| `references/project-template.md` | 完整项目模板：Notion Todo 的项目结构、数据流、交互流程、关键代码 |

## 关键命令

```ini
; 刷新皮肤
Rainmeter.exe !Refresh "皮肤名"
```

```powershell
; 脚本里异步刷新（不要用 & 阻塞等待）
Start-Process -FilePath "D:\APP_BEAUTIFY\Rainmeter\Rainmeter.exe" `
  -ArgumentList "!Refresh `"NotionTodo`"" -WindowStyle Hidden
```
