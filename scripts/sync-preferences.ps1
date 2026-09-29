# sync-preferences.ps1 —— 把 preferences.md 里的 SYNC 块分发到各 agent 的用户级指引文件
#
# 用法：pwsh ~/.skills/scripts/sync-preferences.ps1
#       pwsh ~/.skills/scripts/sync-preferences.ps1 -Force     没装也照写
#       pwsh ~/.skills/scripts/sync-preferences.ps1 -DryRun    只报告不动盘
#
# 设计要点
#   * 源文件和目标文件都用 <!-- SYNC:BEGIN --> / <!-- SYNC:END --> 包裹，
#     本脚本**只替换目标文件里标记块内的内容，不动块外的任何东西** ⇒ 幂等、可反复跑。
#   * 提取时**取最后一个标记块**并做长度校验 —— 踩过坑：文档说明里字面引用过标记，
#     非贪婪正则会匹配到那一对（中间只有几个字符），于是分发出去一堆垃圾。
#   * 不用非零 exit code 表示失败 —— 宿主工具遇到非零退出码会丢掉 stdout，反而看不到结果。
#   * **只给这台机器上装了的 agent 分发**，不为没装的凭空造配置目录
#     （判据与 link.ps1 共用 _common.ps1 的 Test-ClientInstalled）。
#
# 为什么不直接做链接：用户级记忆是**单个文件**（不是目录），junction 只对目录生效；
# 文件级只能 hardlink/symlink，而 agent 写文件常"先删后建"会破坏链接。

param(
    [switch]$Force,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$src = Join-Path $root "preferences.md"

. (Join-Path $PSScriptRoot "_common.ps1")

if (-not (Test-Path $src)) { "❌ 找不到 $src"; return }

$text = [System.IO.File]::ReadAllText($src)
$ms = [regex]::Matches($text, "(?s)<!-- SYNC:BEGIN -->(.*?)<!-- SYNC:END -->")
if ($ms.Count -eq 0) { "❌ preferences.md 里没有 SYNC 标记块"; return }

# 取最后一个块（说明文字里若引用过标记，会被前面的匹配吃掉）
$body = $ms[$ms.Count - 1].Groups[1].Value.Trim()

if ($body.Length -lt 80) {
    "❌ 提取到的 SYNC 块只有 $($body.Length) 字符，明显不对。"
    "   检查 preferences.md 是不是有多处 SYNC 标记（说明文字里不要字面写标记）。"
    return
}

$block = "<!-- SYNC:BEGIN -->`n（本段由 ~/.skills/preferences.md 自动同步，勿直接编辑）`n`n" + $body + "`n<!-- SYNC:END -->"

$targets = [ordered]@{
    "WorkBuddy" = Join-Path $env:USERPROFILE ".workbuddy\MEMORY.md"
    "ZCode"     = Join-Path $env:USERPROFILE ".zcode\AGENTS.md"
    "opencode"  = Join-Path $env:USERPROFILE ".config\opencode\AGENTS.md"
    "豆包工作"  = Join-Path $env:USERPROFILE "DoubaoWork\AGENTS.md"
}

# 目标文件 -> 对应的 routing.json client 名（用于安装检测）
$clientOf = @{
    "WorkBuddy" = "workbuddy"
    "ZCode"     = "zcode"
    "opencode"  = "opencode"
    "豆包工作"  = "doubao"
}

$plan = Get-ClientPlan $root

$rows = @()
foreach ($k in $targets.Keys) {
    $p = $targets[$k]

    # 安装检测：没装这个 agent 就不给它写配置文件
    $cname = $clientOf[$k]
    $info  = $plan.Clients | Where-Object { $_.Name -eq $cname } | Select-Object -First 1
    if ($info -and -not $info.Installed -and -not $Force) {
        $rows += [PSCustomObject]@{
            Agent  = $k
            动作   = "跳过"
            文件   = $p.Replace($env:USERPROFILE, "~")
            字符数 = "-"
            说明   = "未检测到安装（$($info.InstallReason)）"
        }
        continue
    }

    $dir = Split-Path $p
    if (-not $DryRun) {
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    }

    $old = if (Test-Path $p) { [System.IO.File]::ReadAllText($p) } else { "" }

    if ($old -match "(?s)<!-- SYNC:BEGIN -->.*?<!-- SYNC:END -->") {
        $new = [regex]::Replace($old, "(?s)<!-- SYNC:BEGIN -->.*?<!-- SYNC:END -->", { $block })
        $state = "更新"
    } else {
        $new = $old.TrimEnd() + "`n`n" + $block + "`n"
        $state = "追加"
    }

    if (-not $DryRun) {
        [System.IO.File]::WriteAllText($p, $new, (New-Object System.Text.UTF8Encoding($false)))
    } else {
        $state = "预览" + $state
    }

    $rows += [PSCustomObject]@{
        Agent  = $k
        动作   = $state
        文件   = $p.Replace($env:USERPROFILE, "~")
        字符数 = $new.Length
        说明   = if ($Force -and $info -and -not $info.Installed) { "-Force 强制" } else { "" }
    }
}

$out = @()
$out += "源：~/.skills/preferences.md  （SYNC 块 $($body.Length) 字符，共找到 $($ms.Count) 处标记）"
if ($DryRun) { $out += "模式：-DryRun（未写盘）" }
$out += ""
$out += ($rows | Format-Table -AutoSize | Out-String).TrimEnd()
$out += ""
$out += "改完偏好记得 git 提交，这样新机器也能同步到。"
$out -join "`n"
