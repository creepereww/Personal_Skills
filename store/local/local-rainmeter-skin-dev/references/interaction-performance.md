# 交互与性能优化

## 命令行窗口问题

### 坑：点击按钮弹出黑色 cmd 窗口

**现象**：皮肤点击 checkbox 或按钮时，弹出一个黑色命令行窗口，闪烁一下。

**原因**：Rainmeter 的 LeftMouseUpAction 直接调用 `powershell.exe`，即使加了 `-WindowStyle Hidden`，启动时仍会短暂闪烁窗口。

**解决方案**：用 **VBScript 包装器** 隐藏窗口。

#### RunHidden.vbs

```vbscript
' VBScript wrapper - hide PowerShell window
' Args: script_path [arg1] [arg2] ...
Set WshShell = CreateObject("WScript.Shell")
strCmd = "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & WScript.Arguments(0) & """"
For i = 1 To WScript.Arguments.Count - 1
    strCmd = strCmd & " """ & WScript.Arguments(i) & """"
Next
WshShell.Run strCmd, 0, False
```

**要点**：
- `WshShell.Run` 第二个参数 `0` 表示隐藏窗口
- 第三个参数 `False` 表示不等待脚本执行完成
- 使用英文注释（VBScript 中文注释会乱码）
- 保存为 ASCII/ANSI 编码

#### 皮肤中的调用方式

```ini
[MeterCheck1]
Meter=String
Text=☐
LeftMouseUpAction=[wscript.exe "C:\path\to\RunHidden.vbs" "C:\path\to\Complete-Todo.ps1" "任务标题" "done"]
```

## 点击不刷新问题

### 坑：点击后内容不更新，需手动刷新

**现象**：点击 checkbox 后任务状态改变了，但皮肤显示不更新，必须右键手动刷新皮肤。

**原因**：
1. 皮肤中的 `[!Refresh]` 在脚本执行前就执行了，此时数据还没更新
2. 脚本执行完成后没有通知 Rainmeter 刷新

**解决方案**：
1. **去掉皮肤中的 `[!Refresh]`**：不要在 LeftMouseUpAction 末尾加 `[!Refresh]`
2. **脚本执行完成后自己刷新**：在 PowerShell 脚本最后调用 Rainmeter 命令行刷新：

```powershell
# 异步刷新，不等待
Start-Process -FilePath "D:\path\to\Rainmeter.exe" -ArgumentList "!Refresh `"SkinName`"" -WindowStyle Hidden
```

**关键**：用 `Start-Process` 异步发送刷新命令，不要用 `& Rainmeter.exe !Refresh`（会阻塞等待）。

## 响应速度慢的优化

### 优化 1：乐观更新（最有效）

**问题**：点击后要等 API 返回才更新显示，用户感觉很慢（2-5 秒）。

**解决方案**：**乐观更新**——先在本地立即更新显示（100-200ms），后台再同步到 API。

```powershell
# 第一步：乐观更新 - 立即本地修改并刷新
# 1. 修改本地数据文件
# 2. 重新生成皮肤
# 3. 调用 Rainmeter 刷新
# 用户瞬间看到变化

# 第二步：后台同步
# 1. 调用 API 更新远端状态
# 2. 同步成功后重新拉取真实数据，确保一致
# 3. 同步失败时保留本地乐观更新状态，不覆盖
```

**流程对比**：
- 传统：点击 → API → 更新本地 → 刷新皮肤（慢）
- 乐观更新：点击 → 立即更新本地 → 刷新皮肤（快）→ 后台 API 同步

### 优化 2：减少进程启动开销

```powershell
# 慢的方式：启动新 PowerShell 进程执行生成脚本
& powershell -File "Generate-Skin.ps1"

# 快的方式：点号引用，同一进程执行
. "Generate-Skin.ps1"
```

**注意**：点号引用会有**变量污染**问题，见下方"变量污染坑"。

### 优化 3：PowerShell 启动参数

```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden
```

- `-NoProfile`：不加载用户配置文件，加快启动
- `-NonInteractive`：不交互模式，减少开销
- `-WindowStyle Hidden`：隐藏窗口（仍可能闪烁，配合 VBScript 彻底隐藏）

### 优化 4：API 请求压缩

```powershell
# 用 -Compress 压缩 JSON，减少网络传输
$body = $data | ConvertTo-Json -Compress
```

## 变量污染坑

### 坑：点号引用脚本后参数值被篡改

**现象**：传入的参数是 "done"，但脚本执行到一半变成了 "undone"。

**原因**：用点号（.）引用另一个 PowerShell 脚本时，被引用脚本中的变量会污染当前脚本的作用域。如果被引用脚本中有同名变量（如 `$TargetState`、`$task` 等），会覆盖当前脚本的值。

**解决方案**：**在引用脚本前保存参数值到新变量**，后续全部使用保存后的变量：

```powershell
# 保存参数值（避免被点号引用的脚本污染）
$SavedTaskTitle = $TaskTitle
$SavedTargetState = $TargetState

# 后续全部使用 $SavedTaskTitle 和 $SavedTargetState
```

**验证方法**：在引用脚本前后分别写日志，对比变量值：

```powershell
Write-Log "引用前: TargetState=$TargetState"
. $GenScript
Write-Log "引用后: TargetState=$TargetState"
```

## 定时同步 vs 触发同步

| 方式 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| 定时同步（Windows 任务计划） | 后台自动更新 | 占用系统资源，可能在不需要时同步 | 数据变化频繁，需要实时性 |
| 触发同步（点击时同步） | 按需执行，资源占用低 | 需要手动触发 | 数据变化不频繁，用户点击频率低 |
| 乐观更新 + 后台同步 | 响应快，体验好 | 实现复杂 | 用户交互类皮肤（Todo、笔记） |

**推荐**：用户交互类皮肤用**乐观更新 + 触发同步**，不要设定时任务。
