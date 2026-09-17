# sync.ps1 —— 多机同步（Git 主干）
# 用法（PowerShell 7）：
#   pwsh .\sync.ps1                    拉取远端最新 + 刷新本机联接
#   pwsh .\sync.ps1 -Commit "msg"      先提交本机改动再拉取推送
#
# 注意：commit message 中文没问题（存进 git 的是 UTF-8）。
#       只是在某些工具里捕获 git 输出时会显示成乱码，看起来像坏了，其实是显示问题。
#
# 说明：本机 git 不在 PATH 里，脚本优先用 WorkBuddy 自带的 PortableGit。

param(
    [string]$Commit = "",
    [switch]$NoLink
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

$gitCandidates = @(
    "C:\Users\cgw06\.workbuddy\binaries\PortableGit\versions\1.2.0\cmd\git.exe",
    "C:\Program Files\Git\cmd\git.exe"
)
$git = $null
foreach ($c in $gitCandidates) { if (Test-Path $c) { $git = $c; break } }
if (-not $git) { throw "找不到 git.exe，请先安装 Git 或修正脚本里的路径" }

$log = @()

# 中文 commit message 需要显式告诉 git 用 UTF-8，否则会乱码
& $git -C $root config i18n.commitEncoding utf-8 2>&1 | Out-Null
& $git -C $root config i18n.logOutputEncoding utf-8 2>&1 | Out-Null

if ($Commit) {
    $r = & $git -C $root add -A 2>&1 | Out-String
    $r2 = & $git -C $root commit -m $Commit 2>&1 | Out-String
    $log += "COMMIT:"
    $log += $r2.Trim()
}

$remotes = & $git -C $root remote 2>&1 | Out-String
if ($remotes.Trim()) {
    $pull = & $git -C $root pull --rebase 2>&1 | Out-String
    $log += "PULL:"
    $log += $pull.Trim()
    if ($Commit) {
        $push = & $git -C $root push 2>&1 | Out-String
        $log += "PUSH:"
        $log += $push.Trim()
    }
}
else {
    $log += "NO REMOTE —— 当前只有本地仓库。加远端："
    $log += ("  & `"{0}`" -C `"{1}`" remote add origin <你的私有仓库地址>" -f $git, $root)
}

$status = & $git -C $root status --short 2>&1 | Out-String
$log += "STATUS:"
$log += $(if ($status.Trim()) { $status.Trim() } else { "  (clean)" })

if (-not $NoLink) {
    $linkOut = & (Join-Path $PSScriptRoot "link.ps1") 2>&1 | Out-String
    $log += "LINK:"
    $log += $linkOut.Trim()
}

$log -join "`n"
