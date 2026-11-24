# auto-sync.ps1 —— 无人值守同步（定时任务入口）：提交 -> 推送 -> 刷新挂载 -> 复核
#
# 用法（PowerShell 7）：
#   pwsh ~/.skills/scripts/auto-sync.ps1                     自动提交 + 同步
#   pwsh ~/.skills/scripts/auto-sync.ps1 -Message "msg"      指定提交信息
#   pwsh ~/.skills/scripts/auto-sync.ps1 -NoLink             跳过挂载刷新
#
# 顺序：
#   1. 工作区有改动 -> git add -A + commit（pre-commit hook 会跑 audit.ps1，被拦即中止）
#   2. push.ps1 —— fetch / 落后自动 rebase / push（代理绕开、TLS 后端互换、重试都在它里面）
#   3. link.ps1 —— 刷新各 agent 挂载（新 skill 拉下来要挂上）
#   4. 复核：HEAD == origin/<分支>，且工作区干净
#
# 日志：store/cache/logs/auto-sync-<时间戳>.log（store/cache 不进 Git）
# 退出码：0 = 成功；1 = 失败（原因见输出与日志）
#
# ⚠️ 自动提交用 git add -A —— 仓库里所有未忽略的改动会进同一笔提交。
#    想分开提交的改动，先自己提交；遇到 rebase/merge 未完成会直接停下等人工处理。
# ⚠️ 提交被 hook 拦住时修 skill，别用 --no-verify 绕过（理由见 install-hook.ps1 头部）。

param(
    [string]$Message = "",
    [switch]$NoLink
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "_common.ps1")
$git = Get-GitExe

$logDir = Join-Path $root "store\cache\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir ("auto-sync-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".log")

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

# 跑一条 git 子命令（内部固定 -C $root，不受调用方 cwd 影响）
function Invoke-Git([string[]]$GitArgs) {
    $prev = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $text = (& $git -C $root @GitArgs 2>&1 | Out-String)
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prev
    }
    [PSCustomObject]@{ Code = $code; Text = $text.Trim() }
}
function SayLines([string]$text) {
    foreach ($ln in ($text -split "`r?`n")) { if ($ln.Trim()) { Say ("  " + $ln) } }
}

$pwshExe = Join-Path $PSHOME "pwsh.exe"
if (-not (Test-Path $pwshExe)) { $pwshExe = "pwsh" }

Say ("== auto-sync {0} @ {1} ==" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $env:COMPUTERNAME)
Say "仓库  ：$root"

if (-not (Test-Path (Join-Path $root ".git"))) { Say "FAIL 不是 git 仓库：$root"; Finish 1 }

# rebase / merge 进行中：自动提交会把半成品当正常改动，必须人工处理
foreach ($marker in @(".git\rebase-merge", ".git\rebase-apply", ".git\MERGE_HEAD")) {
    if (Test-Path (Join-Path $root $marker)) {
        Say "FAIL 仓库处于 rebase/merge 未完成状态（$marker）—— 人工处理后再跑"
        Finish 1
    }
}

$branch = (Invoke-Git @("rev-parse", "--abbrev-ref", "HEAD")).Text
if ($branch -ne "master") { Say "分支  ：$branch（非 master，照常同步该分支）" }

# —— 1. 有改动就提交 ——
$status = (Invoke-Git @("status", "--porcelain")).Text
if ($status.Trim()) {
    if (-not $Message) { $Message = "auto-sync($($env:COMPUTERNAME)): $(Get-Date -Format 'yyyy-MM-dd HH:mm')" }
    Say ""
    Say "本地改动："
    SayLines $status
    $add = Invoke-Git @("add", "-A")
    if ($add.Code -ne 0) { Say "FAIL git add 失败："; SayLines $add.Text; Finish 1 }
    $commit = Invoke-Git @("commit", "-m", $Message)
    if ($commit.Code -ne 0) {
        Say "FAIL 提交失败（pre-commit hook 会跑 audit.ps1，多半是内容不合规）："
        SayLines $commit.Text
        Say "      修好再提交，别用 --no-verify 绕过。"
        Finish 1
    }
    Say ("OK    commit：{0}" -f (($commit.Text -split "`r?`n")[0]))
} else {
    Say ""
    Say "OK    本地无改动，跳过 commit"
}

# —— 2. 推送（push.ps1 内含 fetch / rebase / 重试 / 代理绕开） ——
Say ""
Say "-- push.ps1 --"
$pushOut = (& $pwshExe -NoProfile -File (Join-Path $PSScriptRoot "push.ps1") -Branch $branch 2>&1 | Out-String)
$pushCode = $LASTEXITCODE
SayLines $pushOut
if ($pushCode -ne 0) {
    Say "FAIL push.ps1 退出码 $pushCode（网络 / rebase 冲突原因见上）"
    Finish 1
}

# —— 3. 刷新挂载 ——
if (-not $NoLink) {
    Say ""
    Say "-- link.ps1 --"
    $linkOut = (& $pwshExe -NoProfile -File (Join-Path $PSScriptRoot "link.ps1") 2>&1 | Out-String)
    SayLines $linkOut
}

# —— 4. 复核 ——
Say ""
$head   = (Invoke-Git @("rev-parse", "HEAD")).Text
$remote = (Invoke-Git @("rev-parse", "origin/$branch")).Text
$dirty  = (Invoke-Git @("status", "--porcelain")).Text
Say "HEAD            ：$head"
Say "origin/$branch ：$remote"

if ($dirty.Trim()) {
    Say "FAIL 工作区仍有未提交改动："
    SayLines $dirty
    Finish 1
}
if ($head -ne $remote) {
    Say "FAIL 本机与远端不一致（有提交没推上去，或远端领先没拉到）"
    Finish 1
}

Say "OK    本机与 origin/$branch 一致，同步完成"
Finish 0
