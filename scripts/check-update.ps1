# check-update.ps1 —— 检查远程 skill 在上游有没有新提交
#
# 用法：pwsh ~/.skills/scripts/check-update.ps1
#
# ⚠️ 网络要求：要能访问 api.github.com（HTTPS 443）。
#    本机直连 443 不通（见 local-wgc-machine 的「网络」节），所以：
#      - 在 WorkBuddy 里跑 → 沙箱已注入代理，能通
#      - 在普通终端跑 → 需要先挂代理，或设好 GITHUB_TOKEN 走别的通道
#
# 设了 GITHUB_TOKEN 环境变量就用它（提高速率限制、也能少受未登录限制影响）

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$regPath = Join-Path $root "registry.json"

if (-not (Test-Path $regPath)) { "找不到 registry.json：$regPath"; exit 1 }

$reg = Get-Content $regPath -Raw -Encoding UTF8 | ConvertFrom-Json

$headers = @{ "User-Agent" = "skills-hub-check-update" }
if ($env:GITHUB_TOKEN) { $headers["Authorization"] = "Bearer $($env:GITHUB_TOKEN)" }

$rows = @()
$remoteList = @($reg.remote | Where-Object { -not $_.retired })

foreach ($s in $remoteList) {
    $q = "/repos/$($s.repo)/commits?per_page=1"
    if ($s.path) { $q += "&path=$($s.path)" }

    try {
        $c = Invoke-RestMethod -Uri ("https://api.github.com" + $q) -Headers $headers -TimeoutSec 30
        if (-not $c -or $c.Count -eq 0) { throw "上游返回空（可能路径已不存在）" }

        $sha7  = $c[0].sha.Substring(0, 7)
        $date  = ([datetime]$c[0].commit.committer.date).ToString("yyyy-MM-dd")
        $local = $s.commit
        $state = if (-not $local) { "未记录" }
                 elseif ($sha7 -ne $local) { "有更新" }
                 else { "最新" }

        $rows += [PSCustomObject]@{
            skill  = $s.id
            本地   = $local
            远程   = $sha7
            上游日期 = $date
            状态   = $state
        }
    } catch {
        $msg = $_.Exception.Message
        if ($msg.Length -gt 34) { $msg = $msg.Substring(0, 34) + "…" }
        $rows += [PSCustomObject]@{
            skill = $s.id; 本地 = $s.commit; 远程 = "-"; 上游日期 = "-"; 状态 = "查询失败: $msg"
        }
    }
}

$out = @()
$out += "远程 skill 共 $($remoteList.Count) 个"
$out += ""
$out += ($rows | Format-Table -AutoSize | Out-String).TrimEnd()

$needUpdate = @($rows | Where-Object { $_.状态 -eq "有更新" })
$out += ""
if ($needUpdate.Count -gt 0) {
    $out += "有更新的：$($needUpdate.skill -join ', ')"
    $out += "更新命令：pwsh ~/.skills/scripts/pull.ps1 -Id <skill> -Force"
} else {
    $out += "全部是最新 ✅"
}
$out -join "`n"

# 注意：这里**不要**用非零 exit code 表示“有查询失败” —— 宿主工具遇到非零退出码会把 stdout 丢掉，
# 反而看不到结果。失败情况已经写在表格里了。
