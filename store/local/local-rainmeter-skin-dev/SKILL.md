---
name: local-rainmeter-skin-dev
description: Rainmeter 桌面皮肤开发经验与踩坑指南。用于开发 Rainmeter 皮肤（.ini）、动态生成皮肤脚本、集成外部 API（如 Notion）、实现交互功能（折叠/打勾/同步）、解决中文乱码、窗口自适应、命令行弹窗、变量污染等常见问题。当用户需要在 Rainmeter 上开发自定义皮肤、对接外部数据源、实现桌面小组件时使用。
version: v0.1
---

# Rainmeter 皮肤开发指南

基于真实项目（Notion Todo 桌面小组件）踩坑总结，覆盖从皮肤结构到 API 集成的全流程。

## 核心工作流

1. **确定数据来源**：外部 API（Notion/GitHub）、本地文件、系统信息
2. **设计皮肤结构**：标题栏 + 内容区 + 底部栏，用 MeterShape 自定义背景
3. **动态生成皮肤**：用 PowerShell/Python 脚本读取数据，动态生成 .ini 文件
4. **实现交互**：折叠、打勾、同步按钮，通过 LeftMouseUpAction 触发
5. **后台同步**：乐观更新本地显示 + 静默同步到外部 API
6. **编码处理**：严格区分皮肤文件和脚本文件的编码要求

## 快速避坑清单

| 问题 | 现象 | 解决方案 |
|------|------|----------|
| 中文乱码 | 皮肤显示？？？或方块 | 皮肤文件保存为 **UTF-16 LE** 编码（Unicode） |
| 脚本中文乱码 | PowerShell 输出或 API 请求中文乱码 | 脚本保存为 **UTF-8 with BOM** 编码 |
| 窗口不收缩 | DynamicWindowSize=1 隐藏 meter 后窗口大小不变 | 用 **MeterShape** 自定义背景 + `!SetOption` 动态改高度 |
| 条件语法不解析 | `[#Var?True:False]` 显示原始文本 | Rainmeter 不支持三元表达式，用**两个独立 meter 切换显示** |
| 弹出命令行窗口 | 点击按钮闪一下黑色 cmd 窗口 | 用 **VBScript 包装器**（RunHidden.vbs）隐藏 PowerShell 窗口 |
| 点击不刷新 | 点击后内容不更新，需手动刷新 | 脚本执行完成后**自己调用 Rainmeter !Refresh**，不要用皮肤中的 `[!Refresh]` |
| 变量污染 | 点号引用脚本后参数值被篡改 | 点号引用脚本前**保存参数值到新变量**，后续使用保存的值 |
| API 中文 400 错误 | 调用 Notion API 报 Bad Request | 请求体显式转 **UTF-8 字节数组**，Content-Type 加 `charset=utf-8` |
| 响应慢 | 点击后 3-5 秒才生效 | **乐观更新**：先本地更新显示（瞬间），后台再同步 API |

## 详细参考

- **编码与文件格式**：见 [references/encoding.md](references/encoding.md)
- **皮肤结构与动态生成**：见 [references/skin-structure.md](references/skin-structure.md)
- **交互与性能优化**：见 [references/interaction-performance.md](references/interaction-performance.md)
- **外部 API 集成**：见 [references/api-integration.md](references/api-integration.md)
- **完整项目模板**：见 [references/project-template.md](references/project-template.md)

## 关键路径

- Rainmeter 皮肤目录：`C:\Users\<用户名>\Documents\Rainmeter\Skins\`
- 皮肤配置文件：`C:\Users\<用户名>\AppData\Roaming\Rainmeter\Rainmeter.ini`
- 刷新皮肤命令：`Rainmeter.exe !Refresh "皮肤名"`
- 皮肤文件编码：**UTF-16 LE**（Unicode）
- PowerShell 脚本编码：**UTF-8 with BOM**
