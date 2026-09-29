# link.ps1 —— 把 store/ 下的 skill 实体挂载到各 agent 的 skills 目录
# 用法（PowerShell 7）：
#   pwsh .\link.ps1                    同步全部「已启用且已安装」的 client
#   pwsh .\link.ps1 -Client zcode      只同步指定 client
#   pwsh .\link.ps1 -DryRun            只报告将要做什么，不动磁盘
#   pwsh .\link.ps1 -Force             没检测到安装也强行建目录并挂载
#   pwsh .\link.ps1 -ListClients       列出各 client 的安装检测结果后退出
#
# 规则：
#   - 只建 junction（目录联接），不用 symlink —— 实测非管理员即可创建
#   - 遇到真实目录（非联接）一律跳过并报 CONFLICT，绝不覆盖用户文件
#   - 摘链接用 [IO.Directory]::Delete(link,$false)；Remove-Item -Recurse 会误删源内容
#   - 没装这个 agent 就跳过，不为它凭空建目录（判据见 _common.ps1 的 Test-ClientInstalled）

param(
    [string]$Client = "",
    [switch]$DryRun,
    [switch]$Force,
    [switch]$ListClients
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

. (Join-Path $PSScriptRoot "_common.ps1")

$plan = Get-ClientPlan $root
$cfg  = $plan.Config

function Get-ExpandedPath($p) { [Environment]::ExpandEnvironmentVariables($p) }

function Remove-JunctionOnly($link) {
    # 只摘链路，绝不动目标内容
    [System.IO.Directory]::Delete($link, $false)
}

# 收集 store 里的实体（local = 纯本地，fork = 有上游）
# 只有含 SKILL.md 的目录才算 skill —— 否则 skill-creator 之类工具留下的
# <name>-workspace/、evals 中间产物会被误当成 skill 挂给所有 agent
$entities = @()
$skipped = @()
foreach ($kind in @("local", "fork")) {
    $dir = Join-Path $root "store\$kind"
    if (Test-Path $dir) {
        Get-ChildItem $dir -Directory -ErrorAction SilentlyContinue | ForEach-Object {
            if (Test-Path (Join-Path $_.FullName "SKILL.md")) {
                $entities += [PSCustomObject]@{ Name = $_.Name; Target = $_.FullName; Kind = $kind }
            }
            else {
                $skipped += "$kind/$($_.Name)"
            }
        }
    }
}

# machine 档：store/machine/<主机名>/，只挂本机名匹配的那个
# 里面的内容是「只对某台机器成立」的事实（磁盘路径、机型、网络实测结果），
# 所以绝不能挂到别的机器上 —— 那会给出错误信息。
#
# 主机名匹配：%COMPUTERNAME% 统一大写返回，而目录名按命名规范是小写，
# 所以必须用大小写不敏感比较（-ieq），否则 WGC-WORK1-PX 匹不上 wgc-work1-px。
#
# host_aliases：临时等价表，把某个主机名指向另一个 machine 目录。
# 用于「主机名已改、但还没重启」的过渡期 —— 此时 %COMPUTERNAME% 还是旧名，
# 匹配不到新目录。重启后自然能匹配，届时应把该条删掉（它不会自己失效）。
$machineEntities = @()
$hostName = $env:COMPUTERNAME
$machineDir = Join-Path $root "store\machine"
$aliasNote = ""
if (Test-Path $machineDir) {
    # 解析别名（若配置了）
    $targetName = $hostName
    if ($cfg.PSObject.Properties['host_aliases']) {
        foreach ($ap in $cfg.host_aliases.PSObject.Properties) {
            if ($ap.Name.StartsWith('_')) { continue }
            if ($hostName -ieq $ap.Name) {
                $targetName = $ap.Value
                $aliasNote = "（经别名 $hostName -> $targetName）"
                break
            }
        }
    }

    Get-ChildItem $machineDir -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        $dirName = $_.Name
        # 大小写不敏感比较（Windows 主机名不区分大小写）
        if ($dirName -ieq $targetName) {
            if (Test-Path (Join-Path $_.FullName "SKILL.md")) {
                $machineEntities += [PSCustomObject]@{ Name = $dirName; Target = $_.FullName; Kind = "machine" }
            }
        }
    }
}

$entities += $machineEntities

# remote skill：registry 里 mount=true 且已缓存的，目录名就是它的 id（不带 local- 前缀）
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

# per-skill 例外规则：routing.json 的 skills 段可以指定某个 skill 只挂给哪些 client
# （未列出 -> 走 defaults.clients；写成空数组 -> 完全不挂）
$skillClients = @{}
if ($cfg.PSObject.Properties['skills']) {
    foreach ($sp in $cfg.skills.PSObject.Properties) {
        if ($sp.Name.StartsWith('_')) { continue }
        if ($sp.Value.PSObject.Properties['clients']) {
            $skillClients[$sp.Name] = @($sp.Value.clients)
        }
    }
}

$report = @()
$report += "entities: " + $entities.Count + " (" + (($entities | Group-Object Kind | ForEach-Object { $_.Name + ":" + $_.Count }) -join " ") + ")"
if ($skillClients.Count -gt 0) {
    $report += "per-skill 例外: " + (($skillClients.Keys | ForEach-Object { $_ + " -> [" + ($skillClients[$_] -join ",") + "]" }) -join "; ")
}
if ($skipped.Count -gt 0) {
    $report += "跳过（无 SKILL.md，不算 skill）: " + ($skipped -join ", ")
}
# 机器档：显示本机主机名和匹配结果，方便确认「哪台的档案被挂上来了」
if (Test-Path $machineDir) {
    $allMachineDirs = @(Get-ChildItem $machineDir -Directory -ErrorAction SilentlyContinue | ForEach-Object { $_.Name })
    if ($allMachineDirs.Count -gt 0) {
        $matched = @($machineEntities | ForEach-Object { $_.Name })
        $report += "machine 档: 本机 $hostName -> " +
            $(if ($matched.Count -gt 0) { "挂载 [" + ($matched -join ", ") + "]" + $aliasNote } else { "无匹配（现有: " + ($allMachineDirs -join ", ") + "）" })
        if ($aliasNote) {
            $report += "         ⚠️ 这是临时别名（host_aliases），重启后请删除该条"
        }
    }
}

# -ListClients：只报安装检测结果，供人工核对
if ($ListClients) {
    $report += ""
    $report += "客户端安装检测："
    foreach ($c in $plan.Clients) {
        $flag = if ($c.Installed) { "已装  " } else { "未检测到" }
        $en   = if ($c.Enabled) { "enabled" } else { "disabled" }
        $report += ("  {0,-10} {1,-8} {2,-9} {3}" -f $c.Name, $flag, $en, $c.InstallReason)
    }
    return ($report -join "`n")
}

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

    # 存在性判定：这台机器没装这个 agent 就不为它建目录
    $info = $plan.Clients | Where-Object { $_.Name -eq $name } | Select-Object -First 1
    if (-not $info.Installed) {
        if ($Force) {
            $report += ("FORCE    {0,-10} 未检测到安装，但 -Force 指定照挂（{1}）" -f $name, $info.InstallReason)
        }
        else {
            $report += ("NOTFOUND {0,-10} 未检测到安装，跳过（{1}）" -f $name, $info.InstallReason)
            $report += ("         想强行挂载加 -Force；想确认判据用 -ListClients")
            continue
        }
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

        # routing 里给这个 skill 指定了 client 名单，而当前 client 不在名单里 -> 不挂，已有的顺手摘掉
        if ($skillClients.ContainsKey($e.Name) -and ($name -notin $skillClients[$e.Name])) {
            if (Test-Path $link) {
                $it = Get-Item $link -Force
                if (($it.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
                    $t2 = $null
                    try { $t2 = $it.LinkTarget } catch { $t2 = $null }
                    if ($t2 -and $t2.StartsWith((Join-Path $root "store"), [StringComparison]::OrdinalIgnoreCase)) {
                        if (-not $DryRun) { Remove-JunctionOnly $link }
                        $pruned++
                        $report += ("UNMOUNT  {0,-10} {1}（routing 规定此 client 不挂）" -f $name, $e.Name)
                    }
                }
            }
            continue
        }

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
