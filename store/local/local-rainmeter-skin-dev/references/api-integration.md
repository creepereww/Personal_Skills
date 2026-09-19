# 外部 API 集成

## Notion API 集成（已验证）

### 基本配置

```powershell
$DatabaseId = "your-database-id"
$NotionVersion = "2022-06-28"
$Headers = @{
    "Authorization"  = "Bearer $Token"
    "Notion-Version" = $NotionVersion
    "Content-Type"   = "application/json"
}
```

### Token 获取

从用户环境变量读取，不要硬编码：

```powershell
$Token = [Environment]::GetEnvironmentVariable("NOTION_TOKEN", "User")
```

**注意**：Integration 需要授权访问数据库，否则返回 404。

### 坑：中文请求体 400 Bad Request

**现象**：调用 Notion API 更新数据时，请求体中包含中文（如属性名"事件"），返回 400 Bad Request，错误信息包含 `??`。

**原因**：PowerShell 默认把请求体编码为系统 ANSI 代码页（GBK），而 Notion API 期望 UTF-8 编码。

**解决方案**：**显式把请求体转换为 UTF-8 字节数组**：

```powershell
# 错误方式（中文会乱码）
Invoke-RestMethod -Uri $uri -Method Post -Headers $headers -Body $body

# 正确方式（UTF-8 编码）
$bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($body)
Invoke-RestMethod -Uri $uri -Method Post -Headers $headers -Body $bodyBytes -ContentType "application/json; charset=utf-8"
```

### 查询数据库

```powershell
# 查询所有任务
$queryBody = @{
    page_size = 100
} | ConvertTo-Json -Compress

$queryBytes = [System.Text.Encoding]::UTF8.GetBytes($queryBody)
$response = Invoke-RestMethod -Uri "https://api.notion.com/v1/databases/$DatabaseId/query" `
    -Method Post -Headers $headers -Body $queryBytes -ContentType "application/json; charset=utf-8"
```

### 查询特定任务

```powershell
$queryBody = @{
    filter = @{
        property = "事件"
        title = @{ equals = $TaskTitle }
    }
    page_size = 1
} | ConvertTo-Json -Compress
```

### 更新任务状态

```powershell
$updateBody = @{
    properties = @{
        Checkbox = @{ checkbox = $isDone }
    }
} | ConvertTo-Json -Compress

$updateBytes = [System.Text.Encoding]::UTF8.GetBytes($updateBody)
Invoke-RestMethod -Uri "https://api.notion.com/v1/pages/$PageId" `
    -Method Patch -Headers $headers -Body $updateBytes -ContentType "application/json; charset=utf-8"
```

### 提取任务标题

Notion 数据库中 title 属性的结构：

```powershell
foreach ($page in $response.results) {
    $titleProp = $page.properties."事件"
    if ($titleProp.title -and $titleProp.title.Count -gt 0) {
        $title = $titleProp.title[0].plain_text
    }
}
```

## API 调用性能优化

### 减少 API 调用次数

| 操作 | 调用次数 | 优化后 |
|------|----------|--------|
| 查询任务 ID + 更新状态 | 2 次 | 2 次（不可避免） |
| 更新后重新拉取所有任务 | 3 次 | 2 次（乐观更新 + 后台同步） |
| 切换状态 | 3 次 | 2 次（直接传目标状态，不先查当前状态） |

### 直接传目标状态（不先查当前状态）

**慢的方式**：
1. 查询任务当前状态
2. 根据当前状态决定要设置成什么
3. 更新状态
4. 重新拉取所有任务

**快的方式**：
1. 皮肤中已经知道当前状态，点击时直接传入目标状态
2. 更新状态
3. 重新拉取所有任务

```powershell
# 皮肤中的调用：未完成任务传 "done"，已完成任务传 "undone"
$targetState = if ($isDone) { "undone" } else { "done" }
LeftMouseUpAction=[...Complete-Todo.ps1 "任务标题" "$targetState"]
```

## 错误处理与日志

### 写日志方便调试

```powershell
$LogFile = Join-Path $PSScriptRoot "error.log"

function Write-Log($msg) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LogFile -Value "[$timestamp] $msg" -Encoding UTF8
}

# 使用
Write-Log "开始同步: $TaskTitle -> $TargetState"
Write-Log "更新成功"
catch {
    Write-Log "同步失败: $($_.Exception.Message)"
    if ($_.ErrorDetails) { Write-Log "错误详情: $($_.ErrorDetails.Message)" }
}
```

### 静默失败

皮肤触发的脚本应该静默失败，不要弹出错误窗口：

```powershell
try {
    # 正常逻辑
}
catch {
    # 记录日志，但不弹窗
    Write-Log "错误: $($_.Exception.Message)"
    exit 1
}
```

## 其他 API 注意事项

- **Notion API 版本**：用 `Notion-Version: 2022-06-28` 头
- **Integration 授权**：数据库必须分享给对应的 Integration，否则 404
- **Rate Limit**：Notion API 有频率限制，不要频繁调用
- **异步同步**：API 更新后可能有几百毫秒延迟，重新拉取数据时加 `Start-Sleep -Milliseconds 500` 等待
