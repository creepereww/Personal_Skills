# API / 数据接入

三种路子，按"数据多久变一次、处理多复杂"选。

## ① WebParser（皮肤内直接抓）

适合：**简单 HTTP GET + 正则提取**。

```ini
[MeasureApi]
Measure=WebParser
URL=https://api.example.com/status
RegExp=(?siU)"value":\s*"(.+)"
UpdateRate=60            ; 单位是「秒」，不是周期数！别太勤

[MeasureValue]
Measure=WebParser
URL=[MeasureApi]
StringIndex=1
```

- `UpdateRate` 单位是**秒**（与 `UpdateDivider` 的"周期数"不同，别混）
- `RegExp` 常用三件套 `(?siU)`：`s` 让 `.` 匹配换行、`i` 忽略大小写、`U` 非贪婪
- 需要认证头、复杂 POST、多步请求 → **别硬用 WebParser**，走 ② 或 ③

## ② 插件

本机插件在 `Skins\@Vault\Plugins\`。常用的：

- **RunCommand** —— 跑外部命令，把 stdout 喂给 Measure（配合外部脚本很顺）
- **Lua**（内置，见 ③）
- 第三方插件：下载后丢进 `@Vault\Plugins\`

```ini
[MeasureCmd]
Measure=Plugin
Plugin=RunCommand
Program=python
Parameter=script.py
OutputType=ANSI
```

## ③ Lua 脚本（皮肤内写逻辑）

```ini
[MeasureLua]
Measure=Script
ScriptFile=#@#\logic.lua
UpdateDivider=10
```

Lua 能读写 Measure 的值、发 bang，适合**需要状态与循环**的逻辑。`#@#` 是 `@Resources` 的简写。

## 什么时候该「用脚本生成 ini」而不是这三种

| 数据特征 | 选 |
|---|---|
| 简单 GET、返回小而稳定 | WebParser |
| 要跑本地命令、解析复杂输出 | 插件 + 外部脚本 |
| 皮肤内需要少量状态逻辑 | Lua |
| **数据复杂 / 要多步处理 / 要落中间文件 / 系统里已有现成脚本能算** | **脚本生成 ini** ← 本机 NotionTodo 走的就是这条 |

**判据**：**能在皮肤外算清楚，就别把逻辑塞进皮肤。**
皮肤里只留"显示"这一件事 —— 越薄越好维护，也越不容易踩性能坑。

具体怎么做见 `project-template.md` 的「方式二」。
