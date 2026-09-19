# 皮肤结构与动态生成

## 为什么不用静态皮肤

静态皮肤无法适应动态数据（如任务列表长度变化）。需要用脚本动态生成 .ini 文件，根据数据量自动调整窗口大小和内容布局。

## 核心结构

```ini
[Rainmeter]
Update=1000
BackgroundMode=0          ; 透明背景，用 MeterShape 自己画
DynamicWindowSize=1
AccurateText=1

[Variables]
FontColor=230,230,240,255
AccentColor=100,180,255,255
BgColor=20,20,30,210

; 背景矩形 - 最底层
[MeterBackground]
Meter=Shape
Shape=Rectangle 0,0,{Width},{Height} | Fill Color #BgColor# | StrokeWidth 0
DynamicVariables=1
```

## 窗口自适应的坑

### 坑 1：DynamicWindowSize=1 不收缩窗口

**现象**：设置 `DynamicWindowSize=1`，隐藏 meter 后窗口大小不变或只扩大不缩小。

**原因**：DynamicWindowSize 只在 meter 内容变化时自动调整，但隐藏 meter 时收缩不可靠。

**解决方案**：用 **MeterShape 自定义背景矩形**，折叠/展开时用 `!SetOption` 动态修改背景高度：

```ini
; 展开时
LeftMouseUpAction=[!SetOption MeterBackground Shape "Rectangle 0,0,{Width},{ExpandedHeight} | Fill Color #BgColor# | StrokeWidth 0"]

; 折叠时
LeftMouseUpAction=[!SetOption MeterBackground Shape "Rectangle 0,0,{Width},{CollapsedHeight} | Fill Color #BgColor# | StrokeWidth 0"]
```

**关键**：修改后必须调用 `[!UpdateMeter *][!Redraw]`。

### 坑 2：条件语法不解析

**现象**：在 Text 中写 `[#Collapsed?▼:▲]`，皮肤显示原始文本而不是▼或▲。

**原因**：Rainmeter 的 String meter Text 不支持三元条件表达式。

**解决方案**：用**两个独立的标题 meter 切换显示**：

```ini
; 展开状态标题（默认显示）
[MeterTitleExpanded]
Meter=String
Text=今日任务  ▼
LeftMouseUpAction=[!HideMeter MeterTitleExpanded][!ShowMeter MeterTitleCollapsed]...

; 折叠状态标题（默认隐藏）
[MeterTitleCollapsed]
Meter=String
Text=今日任务  ▲
Hidden=1
LeftMouseUpAction=[!ShowMeter MeterTitleExpanded][!HideMeter MeterTitleCollapsed]...
```

### 坑 3：分组控制显示/隐藏

**现象**：需要批量隐藏/显示一组 meter（如所有任务项）。

**解决方案**：用 **Group 属性**分组，然后用 `!HideMeterGroup` / `!ShowMeterGroup` 批量控制：

```ini
[MeterItem1]
Group=Content

[MeterItem2]
Group=Content

; 折叠时隐藏所有内容
LeftMouseUpAction=[!HideMeterGroup Content]

; 展开时显示所有内容
LeftMouseUpAction=[!ShowMeterGroup Content]
```

## 宽度自适应

### 根据最长文本自动计算宽度

不要硬编码宽度，根据数据动态计算：

```powershell
function Get-TextWidth($text) {
    $width = 0
    foreach ($char in $text.ToCharArray()) {
        if ([int]$char -gt 127) {
            $width += 15  # 中文字符宽度
        } else {
            $width += 9   # 英文字符/数字宽度
        }
    }
    return $width
}

$maxWidth = ($tasks | ForEach-Object { Get-TextWidth $_ } | Measure-Object -Maximum).Maximum
$contentWidth = $maxWidth + $checkboxWidth + $padding * 2
```

## 动态生成皮肤的最佳实践

1. **用 PowerShell 脚本生成**：读取数据 → 解析格式 → 拼接 ini 字符串 → 写入文件
2. **背景用 MeterShape**：不用 BackgroundMode=1/2/3 的纯色背景，用 Shape 画矩形便于动态改大小
3. **Y 坐标用变量计算**：每个 meter 的 Y 坐标在生成时计算好，不要用相对 Y=10R（折叠时会错位）
4. **生成后调用 !Refresh**：脚本最后刷新 Rainmeter 皮肤
5. **每次全量重新生成**：不要在皮肤中做复杂的动态变量计算，直接重新生成整个 .ini 文件最可靠

## 文件结构

```
NotionTodo/
├── NotionTodo.ini      # 皮肤文件（UTF-16 LE，由脚本生成）
├── todo.txt             # 数据文件（UTF-16 LE）
├── Generate-Skin.ps1    # 皮肤生成脚本（UTF-8 BOM）
├── Update-Todo.ps1      # 同步脚本（UTF-8 BOM）
├── Complete-Todo.ps1    # 完成任务脚本（UTF-8 BOM）
├── RunHidden.vbs        # VBScript 包装器（ASCII，隐藏窗口）
└── error.log            # 错误日志
```
