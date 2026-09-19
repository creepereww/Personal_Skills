# 完整项目模板：Notion Todo 桌面小组件

## 项目结构

```
NotionTodo/
├── NotionTodo.ini      # 皮肤文件（UTF-16 LE，由 Generate-Skin.ps1 生成）
├── todo.txt             # 任务数据文件（UTF-16 LE）
├── Generate-Skin.ps1    # 皮肤生成脚本（UTF-8 BOM）
├── Update-Todo.ps1      # 手动同步脚本（UTF-8 BOM）
├── Complete-Todo.ps1    # 完成/取消完成任务脚本（UTF-8 BOM）
├── RunHidden.vbs        # VBScript 窗口隐藏包装器（ASCII）
└── error.log            # 运行日志（自动生成）
```

## 数据流

```
Notion API
    ↓ (Update-Todo.ps1 拉取)
todo.txt (UTF-16 LE)
    ↓ (Generate-Skin.ps1 读取并解析)
NotionTodo.ini (UTF-16 LE)
    ↓ (Rainmeter 加载)
桌面皮肤显示
```

## 交互流程

### 点击 checkbox 完成任务

```
用户点击 ☐
    ↓
wscript.exe RunHidden.vbs → Complete-Todo.ps1
    ↓
[第一步：乐观更新] 立即修改本地 todo.txt + 重新生成皮肤 + 刷新 Rainmeter（100-200ms）
    ↓
[第二步：后台同步] 调用 Notion API 更新状态 → 重新拉取真实数据 → 确保一致（2-3秒）
```

### 点击手动同步按钮

```
用户点击 🔄 同步
    ↓
wscript.exe RunHidden.vbs → Update-Todo.ps1
    ↓
调用 Notion API 拉取所有任务
    ↓
更新 todo.txt → 重新生成皮肤 → 刷新 Rainmeter
```

## 数据格式（todo.txt）

未完成任务每行一个标题，已完成任务加 `[done]` 前缀：

```
任务1
任务2
[done]任务3
[done]任务4
```

## 关键代码片段

### 1. RunHidden.vbs（窗口隐藏包装器）

```vbscript
Set WshShell = CreateObject("WScript.Shell")
strCmd = "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & WScript.Arguments(0) & """"
For i = 1 To WScript.Arguments.Count - 1
    strCmd = strCmd & " """ & WScript.Arguments(i) & """"
Next
WshShell.Run strCmd, 0, False
```

### 2. Generate-Skin.ps1 核心结构

```powershell
# 读取 todo.txt（UTF-16 LE）
$content = [System.IO.File]::ReadAllText($todoFile, [System.Text.Encoding]::Unicode)

# 解析任务
foreach ($line in $lines) {
    if ($line -match '^\[done\](.*)$') {
        $completedTasks += $Matches[1]
    } else {
        $pendingTasks += $line
    }
}

# 计算宽度和高度
$maxWidth = ($tasks | ForEach-Object { Get-TextWidth $_ } | Measure-Object -Maximum).Maximum
$contentWidth = $maxWidth + $padding * 2

# 生成 ini 内容
$sb = New-Object System.Text.StringBuilder
[void]$sb.AppendLine("[Rainmeter]")
# ... 所有 meter 定义 ...

# 写入皮肤文件（UTF-16 LE）
[System.IO.File]::WriteAllText($skinFile, $sb.ToString(), [System.Text.Encoding]::Unicode)
```

### 3. Complete-Todo.ps1 乐观更新核心

```powershell
# 保存参数（避免变量污染）
$SavedTaskTitle = $TaskTitle
$SavedTargetState = $TargetState

# 第一步：乐观更新
# 1. 修改本地 todo.txt
# 2. 点号引用 Generate-Skin.ps1 重新生成
. $genScript
# 3. 异步刷新 Rainmeter
Start-Process $rainmeterPath -ArgumentList "!Refresh `"NotionTodo`"" -WindowStyle Hidden

# 第二步：后台同步
# 1. 调用 Notion API 更新状态
# 2. 重新拉取真实数据
# 3. 更新本地 todo.txt 和皮肤
```

## 部署步骤

1. 在 `C:\Users\<用户名>\Documents\Rainmeter\Skins\` 下创建 `NotionTodo` 文件夹
2. 把所有脚本和文件放进去
3. 设置环境变量 `NOTION_TOKEN`（用户级）
4. 在 Notion 中创建 Todo 数据库，授权 Integration 访问
5. 右键 Rainmeter 托盘图标 → 皮肤 → NotionTodo → 加载
6. 右键皮肤 → 刷新

## 常见问题排查

| 问题 | 排查步骤 |
|------|----------|
| 中文乱码 | 检查皮肤文件编码是否 UTF-16 LE，脚本是否 UTF-8 BOM |
| 点击无反应 | 查看 error.log，确认 VBScript 路径和参数是否正确 |
| 点击不刷新 | 确认脚本最后有调用 Rainmeter !Refresh，且用 Start-Process 异步执行 |
| API 400 错误 | 确认请求体转 UTF-8 字节数组，Content-Type 加 charset=utf-8 |
| 任务状态同步不上 | 查看 error.log，确认 Token 有效、Integration 已授权数据库 |
| 窗口大小不对 | 确认用 MeterShape 自定义背景，折叠时 !SetOption 改高度 |
| 点击弹出黑窗口 | 确认用 wscript.exe RunHidden.vbs 包装，而不是直接 powershell.exe |
