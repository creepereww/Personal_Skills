# link.ps1 —— 把 store/ 下的 skill 实体挂载到各 agent 的 skills 目录
# 用法：
#   .\link.ps1                 同步全部已启用的 client
#   .\link.ps1 -Client zcode   只同步指定 client
#   .\link.ps1 -DryRun         只报告将要做什么，不动磁盘
#
# 规则：
#   - 只建 junction（目录联接），不用 symlink —— 实测非管理员即可创建
#   - 遇到真实目录（非联接）一律跳过并报 CONFLICT，绝不覆盖用户文件
#   - 摘链接用 [IO.Directory]::Delete(link,$false)，Remove-Item -Recurse 会误删源内容

param(
    [string]$Client = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$cfg  = Get-Content (Join-Path $root "routing.json") -Raw -Encoding UTF8 | ConvertFrom-Json

function Expand-PathStr($p) { return [Environment]::ExpandEnvironmentVariables($p) }

function Remove-Junction($link) {
    # 只摘链路，不动目标内容
    [System.IO.Directory]::Delete($link, $false)
}

# 收集 store 里的实体
$entities = @()
foreach ($kind in @("local", "fork")) {
    $dir = Join-Path $root "store\$kind"
    if (Test-Path $dir) {
        Get-ChildItem $dir -Directory -ErrorAction SilentlyContinue | ForEach-Object {
            $entities += [PSCustomObject]@{ Name = $_.Name; Target = $_.FullName; Kind = $kind }
        }
    }
}

$report = @()
$report += "entities in store: " + $entities.Count

foreach ($prop in $cfg.clients.PSObject.Properties) {
    $name = $prop.Name
    $def  = $prop.Value

    if ($Client -and ($name -ne $Client)) { continue }

    if (-not $def.enabled) {
        $report += ("SKIP     {0,-10} disabled (mode={1})" -f $name, $def.mode)
        continue
    }
    if ($def.mode -ne "junction") {
        $report += ("SKIP     {0,-10} mode={1}, 由原生配置负责，不建联接" -f $name, $def.mode)
        continue
    }

    $dir = Expand-PathStr $def.dir
    if (-not (Test-Path $dir)) {
        if ($DryRun) { $report += ("MKDIR    {0,-10} {1} (dry)" -f $name, $dir) }
        else { New-Item -ItemType Directory -Path $dir -Force | Out-Null; $report += ("MKDIR    {0,-10} {1}" -f $name, $dir) }
    }

    $created = 0; $ok = 0; $conflict = 0; $rebuilt = 0

    foreach ($e in $entities) {
        $link = Join-Path $dir $e.Name

        if (Test-Path $link) {
            $attrs = (Get-Item $link -Force).Attributes
            $isLink = (($attrs -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)
            if (-not $isLink) {
                $conflict++
                $report += ("CONFLICT {0,-10} {1} 是真实目录，未改动" -f $name, $e.Name)
                continue
            }
            if ($DryRun) { $ok++; continue }
            Remove-Junction $link
            New-Item -ItemType Junction -Path $link -Target $e.Target | Out-Null
            $rebuilt++
        }
        else {
            if ($DryRun) { $created++; continue }
            New-Item -ItemType Junction -Path $link -Target $e.Target | Out-Null
            $created++
        }
    }

    $report += ("DONE     {0,-10} dir={1}" -f $name, $dir)
    $report += ("         created={0} rebuilt={1} untouched={2} conflict={3}" -f $created, $rebuilt, $ok, $conflict)
}

$report -join "`n"
