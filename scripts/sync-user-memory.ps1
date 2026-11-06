# sync-user-memory.ps1 —— 把「通用用户记忆」同步到本机所有 AI agent
#
# 用法
#   pwsh ~/.skills/scripts/sync-user-memory.ps1           实际写入
#   pwsh ~/.skills/scripts/sync-user-memory.ps1 -DryRun   只看不动盘
#   pwsh ~/.skills/scripts/sync-user-memory.ps1 -Force     没探测到安装也写
#   pwsh ~/.skills/scripts/sync-user-memory.ps1 -List      只列 agent 探测结果
#
# 与 sync-preferences.ps1 的关系
#   后者把目标写死成 4 个（WorkBuddy / ZCode / opencode / 豆包）；
#   本脚本是它的超集：同一份源，自动覆盖全机 agent，并且修掉了 WorkBuddy 的路径问题。
#   两者读同一个源（preferences.md 的 SYNC 块），跑哪个都行，本脚本更全。
#
# 三个设计取舍（都是踩过坑才这么写的）
#   1. **不读 routing.json**。那份配置是给 skills 挂载用的，只登记了 7 个 client，
#      Trae / Codex / Cline / CodeGeeX / Lingma / MarsCode 都不在里面。
#      记忆同步需要的是「每个 agent 的记忆文件在哪」，和 skills 目录是两件事，故独立建表。
#   2. **WorkBuddy 要写两处**。脚本链路历史写在 ~/.workbuddy/MEMORY.md，
#      但当前版本实际注入的是 ~/.workbuddy/user-<id>-personal/MEMORY.md。
#      两个都写，兼容任何版本。
#   3. **只替换 SYNC 标记块，不动块外内容** ⇒ 幂等，可反复跑，不覆盖用户手写的东西。

param(
    [switch]$DryRun,
    [switch]$Force,
    [switch]$List
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$src  = Join-Path $root "preferences.md"

# ---------------------------------------------------------------------------
# agent 注册表
# ---------------------------------------------------------------------------
# Probe  : 相对 ~ 的路径，存在即视为该 agent 装了
# Targets: 相对 ~ 的记忆文件，顺序即写入顺序；支持一层通配（如 user-*\MEMORY.md）
#
# 加新 agent 只需在这里加一行，不用改下面任何逻辑。
$AGENTS = @(
    @{ Name = 'WorkBuddy'; Probe = '.workbuddy'
       Targets = @('.workbuddy\MEMORY.md', '.workbuddy\user-*\MEMORY.md') }

    @{ Name = 'ZCode';     Probe = '.zcode'
       Targets = @('.zcode\AGENTS.md') }

    @{ Name = 'Trae CN';   Probe = '.trae-cn'
       Targets = @('.trae-cn\AGENTS.md') }

    @{ Name = 'Trae';      Probe = '.trae'
       Targets = @('.trae\AGENTS.md') }

    @{ Name = 'Codex';     Probe = '.codex'
       Targets = @('.codex\AGENTS.md') }

    @{ Name = 'Cline';     Probe = '.cline'
       Targets = @('.cline\AGENTS.md') }

    @{ Name = 'CodeGeeX';  Probe = '.codegeex'
       Targets = @('.codegeex\AGENTS.md') }

    @{ Name = 'Lingma';    Probe = '.lingma'
       Targets = @('.lingma\AGENTS.md') }

    @{ Name = 'MarsCode';  Probe = '.marscode'
       Targets = @('.marscode\AGENTS.md') }

    @{ Name = 'Qoder';     Probe = '.qoder'
       Targets = @('.qoder\AGENTS.md') }

    @{ Name = 'Qoder CN';  Probe = '.qoder-cn'
       Targets = @('.qoder-cn\AGENTS.md') }

    @{ Name = 'opencode';  Probe = '.config\opencode'
       Targets = @('.config\opencode\AGENTS.md') }

    @{ Name = '豆包工作';  Probe = 'DoubaoWork'
       Targets = @('DoubaoWork\AGENTS.md') }

    @{ Name = 'Cursor';    Probe = '.cursor'
       Targets = @('.cursorrules', '.cursor\rules\user-memory.mdc') }

    @{ Name = 'Windsurf';  Probe = '.codeium\windsurf'
       Targets = @('.windsurfrules') }

    @{ Name = 'Claude Code'; Probe = '.claude'
       Targets = @('.claude\CLAUDE.md', 'CLAUDE.md') }
)

# ---------------------------------------------------------------------------
# 1. 从源文件提取 SYNC 块
# ---------------------------------------------------------------------------
if (-not (Test-Path $src)) { "❌ 找不到源文件：$src"; return }

$text = [System.IO.File]::ReadAllText($src)
$ms   = [regex]::Matches($text, "(?s)<!-- SYNC:BEGIN -->(.*?)<!-- SYNC:END -->")
if ($ms.Count -eq 0) { "❌ $src 里没有 SYNC 标记块"; return }

# 取最后一个块：文档说明里若字面引用过标记，前面的匹配会吃掉真块
$body = $ms[$ms.Count - 1].Groups[1].Value.Trim()

if ($body.Length -lt 80) {
    "❌ 提取到的 SYNC 块只有 $($body.Length) 字符，明显不对。"
    "   检查 preferences.md 是不是有多处 SYNC 标记（说明文字里别字面写标记）。"
    return
}

$block = "<!-- SYNC:BEGIN -->`n（本段由 ~/.skills/preferences.md 自动同步，勿直接编辑）`n`n" + $body + "`n<!-- SYNC:END -->"

# ---------------------------------------------------------------------------
# 2. 工具函数
# ---------------------------------------------------------------------------

# 解析目标路径：普通路径直接返回；含通配符的展开成实际存在的多个文件
function Resolve-Targets([string]$pattern) {
    $full = Join-Path $env:USERPROFILE $pattern
    if ($full -notmatch '[\*\?]') { return @($full) }

    $parent = Split-Path $full -Parent          # 例：~\.workbuddy\user-*
    $leaf   = Split-Path $full -Leaf            # 例：MEMORY.md
    if ($parent -notmatch '[\*\?]') { return @($full) }   # 通配在文件名上，暂不支持

    $grand = Split-Path $parent -Parent
    $pat   = Split-Path $parent -Leaf
    if (-not (Test-Path $grand)) { return @() }

    return @(
        Get-ChildItem $grand -Directory -Filter $pat -Force -ErrorAction SilentlyContinue |
        ForEach-Object { Join-Path $_.FullName $leaf }
    )
}

# 把块写进文件：有标记块就替换，没有就追加；块外内容一律不动
function Write-MemoryBlock([string]$path) {
    $parentDir = Split-Path $path -Parent
    if (-not (Test-Path $parentDir)) { New-Item -ItemType Directory -Path $parentDir -Force | Out-Null }

    $old = if (Test-Path $path) { [System.IO.File]::ReadAllText($path) } else { "" }

    if ($old -match "(?s)<!-- SYNC:BEGIN -->.*?<!-- SYNC:END -->") {
        $new   = [regex]::Replace($old, "(?s)<!-- SYNC:BEGIN -->.*?<!-- SYNC:END -->", { $block })
        $state = "更新"
    } else {
        $new   = $old.TrimEnd() + $(if ($old.Trim()) { "`n`n" } else { "" }) + $block + "`n"
        $state = if ($old) { "追加" } else { "新建" }
    }

    if (-not $DryRun) {
        [System.IO.File]::WriteAllText($path, $new, (New-Object System.Text.UTF8Encoding($false)))
    }
    return $state
}

# ---------------------------------------------------------------------------
# 3. 逐 agent 处理
# ---------------------------------------------------------------------------
$rows = @()

foreach ($a in $AGENTS) {
    $probePath = Join-Path $env:USERPROFILE $a.Probe
    $installed = Test-Path $probePath

    # -List 模式只报探测结果，不写盘
    if ($List) {
        $rows += [PSCustomObject]@{
            Agent  = $a.Name
            安装   = if ($installed) { "是" } else { "否" }
            探测   = $a.Probe
            动作   = "-"
            文件   = "-"
        }
        continue
    }

    if (-not $installed -and -not $Force) {
        $rows += [PSCustomObject]@{
            Agent = $a.Name; 安装 = "否"; 探测 = $a.Probe
            动作 = "跳过"; 文件 = "(未检测到安装)"
        }
        continue
    }

    $wrote = @()
    foreach ($t in $a.Targets) {
        $paths = Resolve-Targets $t
        if ($paths.Count -eq 0) {
            # 通配目标没匹配到（例如 WorkBuddy 的 user-* 目录还没生成）—— 正常跳过
            continue
        }
        foreach ($p in $paths) {
            $state = Write-MemoryBlock $p
            $wrote += [PSCustomObject]@{ State = $state; File = $p.Replace($env:USERPROFILE, "~") }
        }
    }

    if ($wrote.Count -eq 0) {
        $rows += [PSCustomObject]@{
            Agent = $a.Name; 安装 = "是"; 探测 = $a.Probe
            动作 = "无目标"; 文件 = "(目录在但没有可写的记忆文件)"
        }
    } else {
        foreach ($w in $wrote) {
            $rows += [PSCustomObject]@{
                Agent = $a.Name; 安装 = "是"; 探测 = $a.Probe
                动作 = $w.State; 文件 = $w.File
            }
        }
    }
}

# ---------------------------------------------------------------------------
# 4. 报告
# ---------------------------------------------------------------------------
$out = @()
$out += "源：~/.skills/preferences.md  （SYNC 块 $($body.Length) 字符）"
if ($DryRun) { $out += "模式：-DryRun（未写盘）" }
if ($Force)  { $out += "模式：-Force（未安装也写）" }
$out += ""
$out += ($rows | Format-Table -AutoSize | Out-String).TrimEnd()

$hit  = @($rows | Where-Object { $_.动作 -in @('更新','追加','新建') }).Count
$skip = @($rows | Where-Object { $_.动作 -eq '跳过' }).Count
$out += ""
$out += "写入 $hit 处，跳过 $skip 个未安装的 agent。"

if (-not $List -and -not $DryRun) {
    $out += ""
    $out += "改完偏好记得 git 提交（~/.skills 是 git 仓库），新机器也能同步到。"
}

$out -join "`n"
