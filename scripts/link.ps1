# link.ps1 —— 把 store/ 下的 skill 实体挂载到各 agent 的 skills 目录
# 用法（PowerShell 7）：
#   pwsh .\link.ps1                 同步全部已启用的 client
#   pwsh .\link.ps1 -Client zcode   只同步指定 client
#   pwsh .\link.ps1 -DryRun         只报告将要做什么，不动磁盘
#
# 规则：
#   - 只建 junction（目录联接），不用 symlink —— 实测非管理员即可创建
#   - 遇到真实目录（非联接）一律跳过并报 CONFLICT，绝不覆盖用户文件
#   - 摘链接用 [IO.Directory]::Delete(link,$false)；Remove-Item -Recurse 会误删源内容

param(
    [string]$Client = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$cfg  = Get-Content (Join-Path $root "routing.json") -Raw -Encoding UTF8 | ConvertFrom-Json

function Get-ExpandedPath($p) { [Environment]::ExpandEnvironmentVariables($p) }

function Remove-JunctionOnly($link) {
    # 只摘链路，绝不动目标内容
    [System.IO.Directory]::Delete($link, $false)
}

# 收集 store 里的实体（local = 纯本地，fork = 有上游）
$entities = @()
foreach ($kind in @("local", "fork")) {
    $dir = Join-Path $root "store\$kind"
    if (Test-Path $dir) {
        Get-ChildItem $dir -Directory -ErrorAction SilentlyContinue | ForEach-Object {
            $entities += [PSCustomObject]@{ Name = $_.Name; Target = $_.FullName; Kind = $kind }
        }
    }
}

# 远程 skill：registry 里 mount=true 且已缓存的，目录名就是它的 id（不带 local- 前缀）
$regPath = Join-Path $root "registry.json"
if (Test-Path $regPath) {
    $reg = Get-Content $regPath -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($r in $reg.remote) {
        if ($r.PSObject.Properties['_example'] -and $r._example) { continue }
        if (-not $r.mount) { continue }
        if (-not $r.cached) { continue }
        $d = Join-Path $root "store\cache\$($r.id)"
        if (Test-Path $d) {
            $entities += [PSCustomObject]@{ Name = $r.id; Target = $d; Kind = "remote" }
        }
    }
}

$report = @()
$report += "entities: " + $entities.Count + " (" + (($entities | Group-Object Kind | ForEach-Object { $_.Name + ":" + $_.Count }) -join " ") + ")"

foreach ($prop in $cfg.clients.PSObject.Properties) {
    $name = $prop.Name
    $def  = $prop.Value

    if ($Client -and ($name -ne $Client)) { continue }

    if (-not $def.enabled) {
        $report += ("SKIP     {0,-10} disabled (mode={1})" -f $name, $def.mode)
        continue
    }
    if ($def.mode -ne "junction") {
        $report += ("SKIP     {0,-10} mode={1} -> 由原生配置负责，不建联接" -f $name, $def.mode)
        continue
    }

    $dir = Get-ExpandedPath $def.dir
    if (-not (Test-Path $dir)) {
        if (-not $DryRun) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
        $report += ("MKDIR    {0,-10} {1}" -f $name, $dir)
    }

    $created = 0; $ok = 0; $conflict = 0; $rebuilt = 0; $pruned = 0

    # 先清理孤儿：本系统建的 junction，但 store 里已经没有这个实体了（改名/删除后残留）
    $known = @($entities | ForEach-Object { $_.Name })
    Get-ChildItem $dir -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        $attrs = $_.Attributes
        if (($attrs -band [System.IO.FileAttributes]::ReparsePoint) -eq 0) { return }
        $target = $null
        try { $target = $_.LinkTarget } catch { $target = $null }
        if (-not $target) { return }
        if (-not $target.StartsWith((Join-Path $root "store"), [StringComparison]::OrdinalIgnoreCase)) { return }
        if ($known -contains $_.Name) { return }

        if (-not $DryRun) { Remove-JunctionOnly $_.FullName }
        $pruned++
        $report += ("PRUNE    {0,-10} {1} (store 中已不存在)" -f $name, $_.Name)
    }

    foreach ($e in $entities) {
        $link = Join-Path $dir $e.Name

        if (Test-Path $link) {
            $item = Get-Item $link -Force
            $isLink = (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)

            if (-not $isLink) {
                $conflict++
                $report += ("CONFLICT {0,-10} {1} 是真实目录，未改动" -f $name, $e.Name)
                continue
            }

            # PowerShell 7 有 LinkTarget，指向正确就跳过，避免无谓重建
            $cur = $null
            try { $cur = $item.LinkTarget } catch { $cur = $null }
            if ($cur -and ($cur.TrimEnd('\') -eq $e.Target.TrimEnd('\')) -and $item.LinkType -eq "Junction") {
                $ok++
                continue
            }

            if ($DryRun) { $rebuilt++; continue }
            Remove-JunctionOnly $link
            New-Item -ItemType Junction -Path $link -Target $e.Target | Out-Null
            $rebuilt++
        }
        else {
            if ($DryRun) { $created++; continue }
            New-Item -ItemType Junction -Path $link -Target $e.Target | Out-Null
            $created++
        }
    }

    $report += ("DONE     {0,-10} created={1} rebuilt={2} unchanged={3} pruned={4} conflict={5}" -f $name, $created, $rebuilt, $ok, $pruned, $conflict)
}

$report -join "`n"
