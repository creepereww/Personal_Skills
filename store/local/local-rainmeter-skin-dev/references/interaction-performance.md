# 交互与性能

## 更新周期

`[Rainmeter]` 里的 `Update`（毫秒，默认 **1000**）决定整个皮肤的刷新节奏。

**降频用 `UpdateDivider`** —— 某个 Measure/Meter 每 N 个周期才更新一次：

```ini
[MeasureCPU]
Measure=CPU
UpdateDivider=5        ; 默认周期 1s 时 = 每 5 秒取一次
```

`UpdateDivider=-1` = **只更新一次**（适合静态数据、启动时取一次的东西）。

## 性能陷阱

| 陷阱 | 后果 | 做法 |
|---|---|---|
| 高频测量不加 divider | CPU 占用高、笔记本费电 | CPU / 网络 / 磁盘类 一律 `UpdateDivider` ≥ 5 |
| `WebParser` 抓得太勤 | 拖慢皮肤、可能被服务端限流 | `UpdateRate` 设 60 秒起，或改用脚本定时生成 |
| 满屏 `DynamicVariables=1` | 每帧重建，明显吃资源 | 只在**确实需要动态**的节上开 |
| 大图整张渲染 | 内存与重绘开销大 | 用 `ImageCrop` 只取需要的区域 |
| 在 Meter 里写计算 | 每帧重复算 | 计算挪到 `[MeasureXxx]` + `Measure=Calc` |

## 鼠标交互

```ini
[MeterButton]
Meter=String
Text=点我
LeftMouseUpAction=["notepad.exe"]
RightMouseUpAction=[!Refresh]
MouseOverAction=[!SetOption MeterButton FontColor "255,0,0,255"]
MouseLeaveAction=[!SetOption MeterButton FontColor "255,255,255,255"]
MouseActionCursor=1
```

可用动作：`LeftMouseUpAction` / `LeftMouseDownAction` / `RightMouseUpAction` / `MiddleMouseUpAction`
/ `MouseOverAction` / `MouseLeaveAction` / `MouseScrollUpAction` …

**一个动作里可以串多个 bang**：`[!Update][!Redraw]`

## 常用 !Bang

| bang | 作用 |
|---|---|
| `!Refresh` | 重载皮肤并应用 ini 改动（**改完必须用它**） |
| `!Update` | 立即触发一次更新，不等周期 |
| `!Redraw` | 强制重绘 |
| `!SetOption` | 运行时改某个选项 |
| `!SetVariable` | 运行时改变量（需 `DynamicVariables=1`） |
| `!ShowMeter` / `!HideMeter` | 显隐某个 Meter |
| `!Move` | 移动皮肤 |
| `!ToggleConfig` | 开关另一个皮肤（参数用 config name） |

⚠️ **`!SetOption` / `!SetVariable` 改的值不写回 ini** —— 刷新后就还原。
要持久化：改文件 → `!Refresh`。

## 调试

| 手段 | 看什么 |
|---|---|
| **皮肤目录的 `error.log`** | 所有报错（本机 `NotionTodo\error.log` 就是它） |
| 右键皮肤 → 皮肤菜单 | 当前生效的配置项 |
| 托盘右键 → **About** | 每个 Measure 的实时取值 —— 排查"数据没出来"最快 |
| 右键 → Skins | 目录树，能直接看到 config name |
