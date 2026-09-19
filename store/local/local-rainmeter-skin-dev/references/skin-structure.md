# 目录结构

## 三层关系

```
Skins\                      ← 皮肤根（可在设置里改；本机是 Documents\Rainmeter\Skins\）
└── MySuite\                ← 根配置（root config）
    ├── @Resources\         ← 套件共享：图片/字体/光标/Lua/脚本
    ├── Clock\
    │   └── Clock.ini       ← 一个皮肤
    └── Net\
        └── Net.ini         ← 同一根配置下的另一个皮肤，与 Clock 共享 @Resources
```

## config name（最容易搞错的地方）

**config name = 从皮肤根到 ini 的路径**（不含 `Skins\`，也不含文件名）：

| ini 实际路径 | config name |
|---|---|
| `Skins\illustro\Clock\Clock.ini` | `illustro\Clock` |
| `Skins\NotionTodo\NotionTodo.ini` | `NotionTodo` |

`!Bang` 命令、配置目录里的皮肤设置，都用 **config name** 指代皮肤。

⚠️ **重命名目录 = 换 config name** → 该皮肤的窗口位置、透明度等设置会丢。

## 变体 vs 独立皮肤

```
Clock\12HrClock.ini + Clock\24HrClock.ini    → 同一皮肤的两个「变体」（同时只激活一个）
Clock\Clock.ini     + Net\Net.ini            → 两个「独立皮肤」（各有各的设置）
```

**变体共享设置**；想独立就分目录。

## 本机现有

| 目录 | 是什么 |
|---|---|
| `illustro\` | Rainmeter 自带示例（Clock / Disk / Network / System / Welcome） |
| `NotionTodo\` | 自建，**由脚本生成 ini**（见 `project-template.md`） |
| `@Vault\` | 只有 `Plugins\` —— 第三方插件存放处 |

## `@Resources\` 里放什么

- 图片、图标
- **自定义字体**（Rainmeter 自动加载，`FontFace` 直接写字体名即可）
- **自定义光标**（配合 `MouseActionCursor`）
- Lua 脚本（`ScriptFile` 引用）
- 其他支撑脚本 / 数据

**只在根配置放一份**，子皮肤用 `#@#`（`@Resources` 的简写变量）引用。

## 常用内置变量

| 变量 | 指向 |
|---|---|
| `#@#` | 当前根配置的 `@Resources\` |
| `#SKINSPATH#` | 皮肤根目录 |
| `#CURRENTPATH#` | 当前 ini 所在目录 |
| `#CURRENTFILE#` | 当前 ini 文件名 |
| `#SETTINGSPATH#` | 配置目录（AppData 里那个） |

写路径优先用这些，**别硬编码盘符** —— 换机器/换便携版就废了。
