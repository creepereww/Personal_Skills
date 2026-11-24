# dotfiles-sync.ps1 —— 无人值守同步 Personal_Dotfiles（默认 ~/.dotfiles）
#
# 用法：
#   pwsh ~/.skills/scripts/dotfiles-sync.ps1                    默认仓库 ~/.dotfiles，master 分支
#   pwsh ~/.skills/scripts/dotfiles-sync.ps1 -Repo D:\dotfiles -Branch master
#   pwsh ~/.skills/scripts/dotfiles-sync.ps1 -NoExport          只做 git 同步，不刷 OneDrive 包
#
# 顺序：
#   1. 只提交**已跟踪**文件的改动（git add -u）—— dotfiles 仓库 README 明确要求别用 git add -A；
#      新出现的未跟踪文件只在报告里列出，不自动入库
#   2. push.ps1 -Repo —— fetch / 落后 rebase / push（网络重试沿用 skills 仓库那一份，不另写）
#   3. 刷 OneDrive 明文包：win\install.ps1 -Export
#      导出前先查「包里有、仓库没有」的文件 —— 导出会清掉这类文件，命中就跳过并报警
#   4. 复核 HEAD == origin/<分支>、已跟踪改动为零（未跟踪只告警）
#
# 日志：store/cache/logs/dotfiles-sync-<时间戳>.log（在 skills 仓库里，不进 Git）
# 退出码：0 = 成功；1 = 失败

param(
    [string]$Repo = "",
    [string]$Branch = "",
    [string]$Message = "",
    [switch]$NoExport
)

$ErrorActionPreference = "Stop"
$skillsRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "_common.ps1")
$git = Get-GitExe

if (-not $Repo) { $Repo = Join-Path $HOME ".dotfiles" }
$resolved = Resolve-Path -LiteralPath $Repo -ErrorAction SilentlyContinue
if (-not $resolved) { Write-Output "FAIL dotfiles 仓库不存在：$Repo"; exit 1 }
$repoPath = $resolved.ProviderPath

$logDir = Join-Path $skillsRoot "store\cache\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir ("dotfiles-sync-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".log")

$lines = [System.Collections.Generic.List[string]]::new()
function Say([string]$s = "") {
    $lines.Add($s)
    Write-Output $s
}
function Finish([int]$code) {
    Say "LOG   ：$logFile"
    ($lines -join "`n") | Out-File -FilePath $logFile -Encoding utf8
    exit $code
}
function Invoke-Git([string[]]$GitArgs) {
    $prev = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $text = (& $git -C $repoPath @GitArgs 2>&1 | Out-String)
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prev
    }
    [PSCustomObject]@{ Code = $code; Text = $text.Trim() }
}
function SayLines([string]$text) {
    foreach ($ln in ($text -split "`r?`n")) { if ($ln.Trim()) { Say ("  " + $ln) } }
}
# 目录下所有文件（排除 .git 与安装脚本留下的 *.bak-*），返回相对路径
function Get-RelFiles([string]$base) {
    $prefix = $base.TrimEnd('\') + '\'
    Get-ChildItem -LiteralPath $base -Recurse -File -Force |
        Where-Object { -not $_.FullName.StartsWith($prefix + '.git\') -and $_.Name -notlike '*.bak-*' } |
        ForEach-Object { $_.FullName.Substring($prefix.Length) }
}

$pwshExe = Join-Path $PSHOME "pwsh.exe"
if (-not (Test-Path $pwshExe)) { $pwshExe = "pwsh" }

Say ("== dotfiles-sync {0} @ {1} ==" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $env:COMPUTERNAME)
Say "仓库  ：$repoPath"

if (-not (Test-Path (Join-Path $repoPath ".git"))) { Say "FAIL 不是 git 仓库：$repoPath"; Finish 1 }

foreach ($marker in @(".git\rebase-merge", ".git\rebase-apply", ".git\MERGE_HEAD")) {
    if (Test-Path (Join-Path $repoPath $marker)) {
        Say "FAIL 仓库处于 rebase/merge 未完成状态（$marker）—— 人工处理后再跑"
        Finish 1
    }
}

if (-not $Branch) { $Branch = (Invoke-Git @("rev-parse", "--abbrev-ref", "HEAD")).Text }
Say "分支  ：$Branch"

# —— 1. 只提交已跟踪文件的改动 ——
$porcelain = (Invoke-Git @("status", "--porcelain")).Text
$untracked = @()
$tracked = @()
foreach ($ln in ($porcelain -split "`r?`n")) {
    if (-not $ln.Trim()) { continue }
    if ($ln.StartsWith("??")) { $untracked += $ln.Substring(3) } else { $tracked += $ln }
}

if ($tracked.Count -gt 0) {
    if (-not $Message) { $Message = "chore(auto-sync): $($env:COMPUTERNAME) $(Get-Date -Format 'yyyy-MM-dd HH:mm')" }
    Say ""
    Say "已跟踪文件的改动："
    foreach ($ln in $tracked) { Say ("  " + $ln) }
    $add = Invoke-Git @("add", "-u")
    if ($add.Code -ne 0) { Say "FAIL git add -u 失败："; SayLines $add.Text; Finish 1 }
    $commit = Invoke-Git @("commit", "-m", $Message)
    if ($commit.Code -ne 0) {
        Say "FAIL 提交失败："
        SayLines $commit.Text
        Finish 1
    }
    Say ("OK    commit：{0}" -f (($commit.Text -split "`r?`n")[0]))
} else {
    Say ""
    Say "OK    已跟踪文件无改动，跳过 commit"
}

if ($untracked.Count -gt 0) {
    Say ""
    Say ("WARN  未跟踪文件 {0} 个（按仓库规矩不自动入库，需要就自己 git add）：" -f $untracked.Count)
    foreach ($f in ($untracked | Select-Object -First 10)) { Say ("  ?? " + $f) }
}

# —— 2. 推送 ——
Say ""
Say "-- push.ps1 --"
$pushOut = (& $pwshExe -NoProfile -File (Join-Path $PSScriptRoot "push.ps1") -Repo $repoPath -Branch $Branch 2>&1 | Out-String)
$pushCode = $LASTEXITCODE
SayLines $pushOut
if ($pushCode -ne 0) {
    Say "FAIL push.ps1 退出码 $pushCode（网络 / rebase 冲突原因见上）"
    Finish 1
}

# —— 3. 刷新 OneDrive 明文包 ——
Say ""
if ($NoExport) {
    Say "SKIP  指定了 -NoExport，不刷 OneDrive 包"
} else {
    $pkg = if ($env:DOTFILES_PKG) { $env:DOTFILES_PKG }
           elseif ($env:OneDrive) { Join-Path $env:OneDrive "dotfiles" }
           else { $null }
    $installPs1 = Join-Path $repoPath "win\install.ps1"
    if (-not $pkg -or -not (Test-Path -LiteralPath $pkg)) {
        Say "WARN  找不到 OneDrive 包（`$env:OneDrive 为空或目录不在），跳过导出"
    } elseif ($pkg.TrimEnd('\') -eq $repoPath.TrimEnd('\')) {
        Say "WARN  包路径与仓库相同，跳过导出"
    } elseif (-not (Test-Path -LiteralPath $installPs1)) {
        Say "WARN  仓库里没有 win\install.ps1，跳过导出"
    } else {
        $repoSet = @{}
        foreach ($f in (Get-RelFiles $repoPath)) { $repoSet[$f] = $true }
        $pkgOnly = @(Get-RelFiles $pkg | Where-Object { -not $repoSet.ContainsKey($_) })
        if ($pkgOnly.Count -gt 0) {
            Say ("WARN  包里有仓库没有的文件 {0} 个 —— 导出会清掉它们，本次跳过导出：" -f $pkgOnly.Count)
            foreach ($f in ($pkgOnly | Select-Object -First 10)) { Say ("  " + $f) }
            Say "      处理办法：收进仓库，或移出包，或手工跑 pwsh win\install.ps1 -Export"
        } else {
            Say "-- install.ps1 -Export --"
            $exportOut = (& $pwshExe -NoProfile -File $installPs1 -Export 2>&1 | Out-String)
            $exportCode = $LASTEXITCODE
            SayLines $exportOut
            if ($exportCode -ne 0) { Say "FAIL 导出返回 $exportCode"; Finish 1 }
            Say "OK    OneDrive 包已刷新"
        }
    }
}

# —— 4. 复核 ——
Say ""
$head   = (Invoke-Git @("rev-parse", "HEAD")).Text
$remote = (Invoke-Git @("rev-parse", "origin/$Branch")).Text
$after  = (Invoke-Git @("status", "--porcelain")).Text
$trackedLeft = @(($after -split "`r?`n") | Where-Object { $_.Trim() -and -not $_.StartsWith("??") })
Say "HEAD            ：$head"
Say "origin/$Branch ：$remote"

if ($trackedLeft.Count -gt 0) {
    Say "FAIL 仍有未提交的已跟踪改动："
    foreach ($ln in $trackedLeft) { Say ("  " + $ln) }
    Finish 1
}
if ($head -ne $remote) {
    Say "FAIL 本机与远端不一致（有提交没推上去，或远端领先没拉到）"
    Finish 1
}

Say "OK    本机与 origin/$Branch 一致，同步完成"
Finish 0
