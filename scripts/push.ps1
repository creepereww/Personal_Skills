# push.ps1 —— 同步并推送本仓库（fetch 检测 -> 落后则 rebase -> push）
#
# ⚠️ 与 pull.ps1 的区别：pull.ps1 是「把上游 skill 拉到 store/cache/」，
#    本脚本是「把本仓库（~/.skills）自己的提交推上 GitHub」。两者无关，别混。
#
# 用法（用 PowerShell 7 的 pwsh 跑；别用 5.1 的 powershell.exe ——
#      无 BOM 的中文注释在 5.1 下会按 GBK 解析，可能报语法错）：
#   pwsh ~/.skills/scripts/push.ps1                 同步并推送 master
#   pwsh ~/.skills/scripts/push.ps1 -DryRun         只报告本地与远端差异，不 rebase、不推送
#   pwsh ~/.skills/scripts/push.ps1 -NoRebase       落后时只报告、不 rebase（想手工处理时用）
#   pwsh ~/.skills/scripts/push.ps1 -KeepProxy      保留环境里的 http(s)_proxy（默认自动绕开 127.0.0.1 的沙箱代理）
#   pwsh ~/.skills/scripts/push.ps1 -Branch dev -Remote origin
#   pwsh ~/.skills/scripts/push.ps1 -Log out.txt    额外把结果落盘（宿主工具里 stdout 会丢时用）
#
# 它一次做掉六件容易踩坑的事：
#   1. 绕开 WorkBuddy 沙箱注入的代理（127.0.0.1:<port>）—— 它对 github.com 返 502
#   2. TLS 后端在 openssl / schannel 之间自动互换重试（这俩随网络路径时好时坏）
#   3. github.com:443 时通时断 —— 自动重试（默认 6 次）
#   4. 推之前先 fetch 检测：远端领先就 rebase，免得 non-fast-forward 被拒
#   5. 远端 host 解析到**回环地址**时（被 Watt Toolkit / Steam++ 之类本地反代劫持）：
#      按后端自动放宽 TLS 校验（openssl -> sslVerify=false、schannel -> schannelCheckRevoke=false）
#   6. 承 5，push 改用「**预置 Basic 认证头**」—— 本机实测「401 -> 调凭证助手 -> 重试」这条
#      路会**静默 exit 128（stdout/stderr 全空）**，预置认证让第一次请求就带凭据，绕开重试。
#
# 退出码：0 = 已最新 或 已推送；1 = 出错（网络失败 / rebase 冲突 / 工作区脏）
#
# 前置：凭证助手要按仓库规范固化过（credential.helper 先空值重置、再只留 GCM），
#       否则**取 token 时会弹 GUI 框**把脚本卡死 —— 见 local-workbuddy-quirks。
#
# 安全提示：第 6 条的 token 会出现在 git 进程的命令行里（同机同用户可见）。
#       单人机可接受；多人共用机器请改用 SSH 或关掉本地反代。

param(
    [string]$Branch = "master",
    [string]$Remote = "origin",
    [int]$MaxTry = 6,
    [switch]$DryRun,
    [switch]$NoRebase,
    [switch]$KeepProxy,
    [string]$Log = ""
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_common.ps1")

$root  = Split-Path -Parent $PSScriptRoot
$git   = Get-GitExe
$track = "$Remote/$Branch"
$out   = @()

function Say([string]$s) { $script:out += $s }
function SayLines($text) {
    foreach ($ln in ("$text" -split "`r?`n")) {
        if ($ln.Trim()) { $script:out += ("      " + $ln) }
    }
}
function Finish([int]$code) {
    $text = $script:out -join "`n"
    $text
    if ($script:Log) { $text | Out-File -FilePath $script:Log -Encoding utf8 }
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
    return [PSCustomObject]@{ Code = $code; Text = $text.Trim() }
}

# 按 TLS 后端生成参数；被本地反代劫持时额外放宽校验（见文件头第 5 条）
function Get-TlsArgs([string]$Backend) {
    $a = @("-c", "http.sslBackend=$Backend")
    if ($script:Hijacked) {
        if ($Backend -eq "schannel") { $a += @("-c", "http.schannelCheckRevoke=false") }
        else                         { $a += @("-c", "http.sslVerify=false") }
    }
    return $a
}

# 需要联网的操作：openssl / schannel 交替 + 重试
function Invoke-GitNet([string[]]$GitArgs) {
    $backends = @("openssl", "schannel")
    $last = ""
    for ($i = 1; $i -le $MaxTry; $i++) {
        $b = $backends[($i - 1) % 2]
        $r = Invoke-Git ((Get-TlsArgs $b) + $GitArgs)
        if ($r.Code -eq 0) { return [PSCustomObject]@{ Ok = $true; Try = $i; Backend = $b; Text = $r.Text } }
        $last = $r.Text
        Say ("      第 {0}/{1} 次失败（TLS 后端 {2}）" -f $i, $MaxTry, $b)
        Start-Sleep -Milliseconds 500
    }
    return [PSCustomObject]@{ Ok = $false; Try = $MaxTry; Backend = ""; Text = $last }
}

# 造「预置认证头」参数：从凭证助手取 token，拼成 Basic 头直接塞进请求。
# 为什么需要：被本地反代劫持时，"401 -> 调凭证助手 -> 重试" 这条路会静默 exit 128。
# 取不到 token（没配助手 / 取失败）时返回 $null，调用方退回常规路径。
function Get-PreAuthArgs {
    if (-not $script:RemoteHost) { return $null }
    $prevPrompt = $env:GIT_TERMINAL_PROMPT
    try {
        $env:GIT_TERMINAL_PROMPT = "0"
        $inp = "protocol=https`nhost=$($script:RemoteHost)`n`n"
        $raw = ($inp | & $git -C $root credential fill 2>&1 | Out-String)
    } catch {
        return $null
    } finally {
        $env:GIT_TERMINAL_PROMPT = $prevPrompt
    }
    $user = ""; $pass = ""
    foreach ($ln in ($raw -split "`r?`n")) {
        if     ($ln -match '^username=(.*)$') { $user = $matches[1] }
        elseif ($ln -match '^password=(.*)$') { $pass = $matches[1] }
    }
    if (-not $user -or -not $pass) { return $null }
    $b64 = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("$user`:$pass"))
    return @("-c", "credential.helper=", "-c", "http.extraHeader=Authorization: Basic $b64")
}

Say "仓库  ：$root"
Say "远端  ：$Remote    分支：$Branch    跟踪引用：$track"
Say ""

if (-not (Test-Path (Join-Path $root ".git"))) { Say "FAIL 不是 git 仓库：$root"; Finish 1 }

# —— 0. 绕开沙箱代理（只清指向本机回环的，真代理不动） ——
$cleared = @()
if (-not $KeepProxy) {
    foreach ($v in @("http_proxy", "https_proxy", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY")) {
        $val = [Environment]::GetEnvironmentVariable($v)
        if ($val -and $val -match "(?i)(127\.0\.0\.1|localhost)") {
            Remove-Item "Env:$v" -ErrorAction SilentlyContinue
            $cleared += $v
        }
    }
}
if ($cleared.Count -gt 0) { Say "代理  ：已绕开沙箱代理 —— $($cleared -join ', ')" }

# —— 0b. 探测远端 host 是否被本地反代劫持（Watt Toolkit / Steam++ 等） ——
# 判据：远端 URL 的 host 解析到**回环地址**（127.0.0.1 / ::1）。
#   本机的 github.com 被 Watt Toolkit 劫持到 127.0.0.1:443（自签 SteamTools 证书），
#   于是：openssl 报证书链失败、schannel 报吊销检查失败，且 push 会静默 exit 128。
#   → 命中时按后端放宽 TLS 校验；push 再改用「预置认证头」（见 Get-PreAuthArgs）。
$script:Hijacked   = $false
$script:RemoteHost = ""
$url = (Invoke-Git @("remote", "get-url", $Remote)).Text
if ($url) {
    try {
        $script:RemoteHost = ([uri]$url).Host
        if ($script:RemoteHost) {
            $ips = [System.Net.Dns]::GetHostAddresses($script:RemoteHost)
            $script:Hijacked = [bool]($ips | Where-Object { [System.Net.IPAddress]::IsLoopback($_) })
        }
    } catch { }
}
if ($script:Hijacked) {
    Say "⚠️   $($script:RemoteHost) 解析到回环地址 —— 疑似被本地反代劫持（Watt Toolkit / Steam++ 等）"
    Say "     → 放宽 TLS 校验；push 若走常规路径失败，将改用「预置认证头」重试。"
    Say "     根治办法：关掉该工具的 GitHub 加速（或退出它）再 push。"
}

# —— 1. 凭证助手体检（只提示，不改配置） ——
# 判据：system 层有 helper-selector（会弹 GUI 框），且本仓库**没做过空值重置**时才报警。
#   为什么不能只看 --get-all：它会把「已被 local 空值清掉」的 system 值也列出来，
#   直接匹配会误报。所以另用 --list 看 local 里有没有 `credential.helper=`（空值行）。
$sysH    = (Invoke-Git @("config", "--system", "--get-all", "credential.helper")).Text
$locList = (Invoke-Git @("config", "--local", "--list")).Text
$reseted = $locList -match "(?m)^credential\.helper=\s*$"
if ($sysH -match "helper-selector" -and -not $reseted) {
    Say "⚠️   凭证助手：system 层有 helper-selector，而本仓库没做空值重置 ——"
    Say "     需要凭证时会弹 GUI 框把 push 卡死。按 local-workbuddy-quirks"
    Say "     「git 凭证：会弹 GUI 框卡住 push」固化后再跑。"
}

# —— 2. fetch ——
Say ""
Say "fetch $Remote $Branch ..."
$f = Invoke-GitNet @("fetch", $Remote, $Branch)
if (-not $f.Ok) {
    Say "FAIL fetch 失败（试了 $($f.Try) 次）："
    SayLines $f.Text
    Finish 1
}
Say ("OK    fetch 成功（第 {0} 次，TLS 后端 {1}）" -f $f.Try, $f.Backend)

# —— 3. 差异 ——
$behind = [int]((Invoke-Git @("rev-list", "--count", "HEAD..$track")).Text)
$ahead  = [int]((Invoke-Git @("rev-list", "--count", "$track..HEAD")).Text)
Say ""
Say "本地 vs $track —— 领先 $ahead 个提交，落后 $behind 个提交"

# —— 4. 落后则 rebase ——
if ($behind -gt 0) {
    if ($DryRun) {
        Say ""
        Say "（dry-run）远端领先 $behind 个提交 —— 正式跑会自动 rebase 后再推。"
    }
    elseif ($NoRebase) {
        Say ""
        Say "SKIP  指定了 -NoRebase，已停在「落后 $behind」的状态，请手工处理。"
        Finish 1
    }
    else {
        $dirty = @((Invoke-Git @("status", "--porcelain", "--untracked-files=no")).Text -split "`r?`n" |
                   Where-Object { $_.Trim() })
        if ($dirty.Count -gt 0) {
            Say ""
            Say "FAIL 工作区有未提交改动，rebase 不安全，已中止："
            SayLines ($dirty -join "`n")
            Say "      先 commit（或 stash）再跑本脚本。"
            Finish 1
        }
        Say ""
        Say "rebase onto $track ..."
        $rb = Invoke-Git @("rebase", $track)
        if ($rb.Code -ne 0) {
            Say "FAIL rebase 冲突，已停在冲突现场（没有自动 abort）："
            SayLines $rb.Text
            Say "      继续：git rebase --continue     放弃：git rebase --abort"
            Finish 1
        }
        Say "OK    rebase 完成（本地提交已重放到 $track 之上）"
        $ahead = [int]((Invoke-Git @("rev-list", "--count", "$track..HEAD")).Text)
    }
}

# —— 5. dry-run 出口 ——
if ($DryRun) {
    Say ""
    if ($ahead -gt 0) { Say "（dry-run）有 $ahead 个本地提交待推 —— 正式跑会执行 git push $Remote $Branch。" }
    else              { Say "（dry-run）无待推送提交。" }
    Finish 0
}

# —— 6. push ——
Say ""
if ($ahead -eq 0) { Say "已是最新，无待推送提交。"; Finish 0 }

Say "push $Remote $Branch（$ahead 个提交待推）..."
$p = Invoke-GitNet @("push", $Remote, $Branch)

# 被本地反代劫持时，常规「401 -> 调凭证助手 -> 重试」可能静默失败（exit 128、无输出）
#   → 退化为「预置 Basic 认证头」：让第一次请求就带凭据。
if (-not $p.Ok -and $script:Hijacked) {
    $pre = Get-PreAuthArgs
    if ($pre) {
        Say "      常规路径失败 —— 改用「预置 Basic 认证头」重试 ..."
        $p = Invoke-GitNet ($pre + @("push", $Remote, $Branch))
    } else {
        Say "      常规路径失败，且取不到 token —— 无法退化为预置认证头。"
    }
}

if (-not $p.Ok) {
    Say "FAIL push 失败（试了 $($p.Try) 次）："
    SayLines $p.Text
    Finish 1
}
SayLines $p.Text
Say ("OK    push 成功（第 {0} 次，TLS 后端 {1}）" -f $p.Try, $p.Backend)

Say ""
Say ("HEAD          ：" + (Invoke-Git @("log", "--oneline", "-1")).Text)
Say ("$track ：" + (Invoke-Git @("rev-parse", $track)).Text)
Finish 0
