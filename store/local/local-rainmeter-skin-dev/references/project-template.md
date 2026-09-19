# 项目模板

## 方式一：手写 ini（适合静态的小皮肤）

`Skins\MySkin\MySkin.ini` —— 最小可跑：

```ini
[Rainmeter]
Update=1000
AccurateText=1

[Metadata]
Name=MySkin
Version=1.0

[Variables]
FontFace=Microsoft YaHei
FontSize=11
FontColor=255,255,255,255

[MeasureTime]
Measure=Time
Format=%H:%M

[MeterTime]
Meter=String
MeasureName=MeasureTime
FontFace=#FontFace#
FontSize=#FontSize#
FontColor=#FontColor#
AntiAlias=1
```

要点：
- `[Metadata]` 对外发布才必需，自己用可省
- 变量用 `#名字#` 引用
- 改完**刷新**才生效

## 方式二：脚本生成 ini（推荐 —— 本机 NotionTodo 就是这么做的）

当皮肤要显示**动态数据**（待办、API 结果、日志统计）时，**别手改 ini**：

```
NotionTodo\
├── Generate-Skin.ps1     ← 把数据渲染成 NotionTodo.ini
├── Update-Todo.ps1       ← 取数据（调 API）
├── Complete-Todo.ps1     ← 处理交互回写
├── RunHidden.vbs         ← 无窗口启动（避免闪黑框）
├── NotionTodo.ini        ← 【产物】别手改，会被覆盖
├── todo.txt              ← 中间数据
└── error.log             ← Rainmeter 的报错都在这
```

**为什么这么做**（对应 `local-script-first`）：数据每次都在变，手改 ini 不现实；
脚本把"取数 → 渲染 ini"固化成一次执行，**ini 降级成产物，人只维护脚本**。

### 五条纪律

1. **ini 是产物** —— 在 ini 顶部写一行注释提醒：`; 本文件由 Generate-Skin.ps1 生成，勿手改`（ini 注释用 `;`）
2. **生成后要刷新** —— 脚本末尾发 `!Refresh`，或提示用户右键 Refresh
   （`!Refresh` 可以用 `RunCommand` 插件或直接改 ini 后靠用户刷新）
3. **编码固定 UTF-16 LE + BOM** —— 生成时显式指定（见 `encoding.md`）
4. **别去写窗口坐标** —— 皮肤位置存在配置目录的 `Rainmeter.ini` 里，不在皮肤 ini 中；
   脚本重写皮肤 ini 不会影响用户拖好的位置 ✓
5. **无窗口启动用 `RunHidden.vbs`** —— 直接跑 PS1 会闪黑框

### 让 Rainmeter 定时跑生成脚本

两条路：
- **皮肤内定时**：`[MeasureRun]` + `RunCommand` 插件，配 `UpdateDivider` 控制频率
- **外部定时**：Windows 计划任务（更省事，且皮肤刷新不依赖它）

推荐**外部定时 + 脚本末尾触发刷新**：职责清楚，皮肤只管显示。

## 打包分发

皮肤作为一个**根配置目录**打包（含 `@Resources`）：
`Rainmeter` 右键托盘图标 → Skins → 打开皮肤文件夹，或官方 `SkinInstaller`（`.rmskin`）。
自己用的话，直接把目录拷进 `Skins\` 即可。
