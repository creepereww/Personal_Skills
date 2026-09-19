# 编码与文件格式

## 皮肤文件（.ini）

### 必须使用 UTF-16 LE 编码

**现象**：皮肤显示中文乱码、？？？或方块

**原因**：Rainmeter 默认读取 .ini 文件时，如果是 UTF-8 编码，中文字符会被错误解析。Rainmeter 对 UTF-16 LE（Unicode）编码的中文支持最好。

**解决方案**：用 PowerShell 写入皮肤文件时，使用 Unicode 编码：

```powershell
[System.IO.File]::WriteAllText($SkinFile, $content, [System.Text.Encoding]::Unicode)
```

### 验证编码

```powershell
# 检查文件 BOM
$bytes = [System.IO.File]::ReadAllBytes($path)
# UTF-16 LE: FF FE
# UTF-8 BOM: EF BB BF
```

## PowerShell 脚本（.ps1）

### 必须使用 UTF-8 with BOM 编码

**现象**：脚本中的中文字符串（如 API 属性名）执行时报错，或 API 返回 400 Bad Request

**原因**：PowerShell 5.1 默认使用系统 ANSI 代码页（GBK）保存和读取脚本。如果脚本保存为无 BOM 的 UTF-8，中文会被错误解析。

**解决方案**：保存脚本时显式指定 UTF-8 with BOM：

```powershell
$utf8WithBom = New-Object System.Text.UTF8Encoding $true
[System.IO.File]::WriteAllText($path, $content, $utf8WithBom)
```

### 读取 UTF-8 文件

```powershell
# 读取 UTF-8 with BOM 文件
$content = Get-Content $path -Raw -Encoding UTF8
```

## VBScript 包装器（.vbs）

### 使用 ANSI/ASCII 编码

**现象**：VBScript 执行报错，或中文注释乱码导致代码异常

**原因**：VBScript 不支持 UTF-8 BOM 编码，中文注释会被错误解析，甚至导致代码行粘连。

**解决方案**：
- 使用英文注释，避免中文
- 保存为 ASCII 或 ANSI 编码
- 代码结构清晰，每行独立

## 数据文件（todo.txt 等）

### 皮肤读取的数据文件也用 UTF-16 LE

**现象**：Rainmeter WebParser 或皮肤读取数据文件时中文乱码

**解决方案**：和皮肤文件保持一致，用 UTF-16 LE 编码写入：

```powershell
[System.IO.File]::WriteAllText($dataFile, $content, [System.Text.Encoding]::Unicode)
```

## 常见编码错误对照

| 文件类型 | 错误编码 | 现象 | 正确编码 |
|----------|----------|------|----------|
| 皮肤 .ini | UTF-8 无 BOM | 中文显示？？？ | UTF-16 LE (Unicode) |
| PowerShell .ps1 | UTF-8 无 BOM | 中文参数报错、API 400 | UTF-8 with BOM |
| VBScript .vbs | UTF-8 有 BOM | 脚本执行失败 | ASCII/ANSI + 英文注释 |
| 数据 .txt | UTF-8 无 BOM | 皮肤读取乱码 | UTF-16 LE (Unicode) |
