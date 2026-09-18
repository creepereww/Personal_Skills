# audit.ps1 —— 检查 skill 是否符合仓库规范
# 用法（PowerShell 7）：
#   pwsh .\audit.ps1                 检查 store/local + store/fork（该守规范的）
#   pwsh .\audit.ps1 -IncludeCache   附带看一眼 store/cache（只报事实，不判定对错）
#
# 判定口径：
#   local / fork —— 必须守规范，逐项判定
#   cache        —— 是上游原版，**不受本地规范约束**（缺 version、描述长、有日期都正常，
#                   改了它就等于派生）。所以对 cache 只查两件事：有没有 SKILL.md、desc 有没有超 1024
#
# 检查项：
#   1. frontmatter name 与目录名逐字符一致（opencode 强制，不符会静默加载失败）
#   2. 名称匹配 ^[a-z0-9]+(-[a-z0-9]+)*$
#   3. 有 version 字段且形如 vX.Y
#   4. description 长度：>500 提示、>1024 报错
#   5. 正文是否残留日期（规范禁止）
#   6. 是否残留 changelog 类字样
#   7. SKILL.md 是否超过 500 行
#   8. 是否有 __pycache__ 之类的垃圾文件

param([switch]$IncludeCache)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$NAME_RE = '^[a-z0-9]+(-[a-z0-9]+)*$'

$kinds = @("local", "fork")
if ($IncludeCache) { $kinds += "cache" }

$rows = @()
$problems = 0

foreach ($kind in $kinds) {
    $base = Join-Path $root "store\$kind"
    if (-not (Test-Path $base)) { continue }

    Get-ChildItem $base -Directory | ForEach-Object {
        $dir = $_.Name
        $sk = Join-Path $_.FullName "SKILL.md"
        $issues = @()
        $isRemote = ($kind -eq "cache")

        # 停用态：SKILL.md 被改名成 .disabled
        $disabled = Test-Path (Join-Path $_.FullName "SKILL.md.disabled")
        if ($disabled) {
            $rows += [PSCustomObject]@{ Kind = $kind; Name = $dir; Ver = "-"; Desc = "-"; Lines = 0; Issues = "已停用（SKILL.md.disabled）" }
            return
        }

        if (-not (Test-Path $sk)) {
            $rows += [PSCustomObject]@{ Kind = $kind; Name = $dir; Ver = "-"; Desc = "-"; Lines = 0; Issues = "没有 SKILL.md" }
            $problems++
            return
        }

        $t = [System.IO.File]::ReadAllText($sk)
        $fmMatch = [regex]::Match($t, "(?s)^---\r?\n(.*?)\r?\n---")
        $fm = if ($fmMatch.Success) { $fmMatch.Groups[1].Value } else { "" }

        $nameM = [regex]::Match($fm, "(?m)^name:\s*(\S+)")
        $verM = [regex]::Match($fm, "(?m)^version:\s*(\S+)")
        $descM = [regex]::Match($fm, "(?ms)^description:\s*(.*?)(?=\r?\n[a-zA-Z_]+:|\Z)")

        $descLen = if ($descM.Success) { $descM.Groups[1].Value.Trim().Length } else { 0 }
        $lines = ($t -split "\n").Count

        if ($isRemote) {
            # 上游原版：只报事实性硬问题，不套本地规范
            if ($descLen -eq 0) { $issues += "缺 description" }
            elseif ($descLen -gt 1024) { $issues += "desc $descLen>1024（opencode 文档上限）" }
            $rows += [PSCustomObject]@{ Kind = $kind; Name = $dir; Ver = "—"; Desc = $descLen; Lines = $lines; Issues = if ($issues.Count) { $issues -join "; " } else { "原版（不判定）" } }
            if ($issues.Count -gt 0) { $problems++ }
            return
        }

        # 1 + 2
        if (-not $nameM.Success) { $issues += "缺 name" }
        else {
            if ($nameM.Groups[1].Value -ne $dir) { $issues += "name≠目录名" }
            if ($nameM.Groups[1].Value -notmatch $NAME_RE) { $issues += "名称违规" }
        }
        # 3
        if (-not $verM.Success) { $issues += "缺 version" }
        elseif ($verM.Groups[1].Value -notmatch '^v\d+\.\d+$') { $issues += "version 格式非 vX.Y" }

        # 4
        if ($descLen -eq 0) { $issues += "缺 description" }
        elseif ($descLen -gt 1024) { $issues += "desc $descLen>1024" }
        elseif ($descLen -gt 500) { $issues += "desc $descLen>500" }

        # 5
        $dates = [regex]::Matches($t, "\b20\d{2}[-/年]\d{1,2}[-/月]\d{1,2}") | ForEach-Object { $_.Value } | Select-Object -Unique
        if ($dates) { $issues += ("正文含日期 " + (($dates | Select-Object -First 3) -join ",")) }

        # 6 —— 只看"肯定语境"：排除规则陈述（不写/禁止/那是 git log 的活）和表格行（多为知识罗列）
        $chgLines = ($t -split "\n") | Where-Object {
            $_ -match "(?i)changelog|更新记录|变更记录|修改记录" -and
            $_ -notmatch "不写|禁止|别写|不要|≠|不是|的活|归 ?git|入 ?git|进 ?git|或 ?CHANGELOG" -and
            -not $_.TrimStart().StartsWith("|")
        }
        if ($chgLines) { $issues += "疑似 changelog" }

        # 7
        if ($lines -gt 500) { $issues += "SKILL.md $lines 行" }

        # 8
        $junk = Get-ChildItem $_.FullName -Recurse -Force -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -match "__pycache__|\.pyc$|\.tmp$" }
        if ($junk) { $issues += "含垃圾文件" }

        if ($issues.Count -gt 0) { $problems++ }

        $rows += [PSCustomObject]@{
            Kind   = $kind
            Name   = $dir
            Ver    = if ($verM.Success) { $verM.Groups[1].Value } else { "✗" }
            Desc   = $descLen
            Lines  = $lines
            Issues = if ($issues.Count -gt 0) { $issues -join "; " } else { "ok" }
        }
    }
}

$out = @()
$out += ("检查范围: " + ($kinds -join ", ") + "    共 " + $rows.Count + " 个 skill")
$out += ""
$out += ("{0,-6} {1,-38} {2,-7} {3,5} {4,6}  {5}" -f "kind", "name", "ver", "desc", "lines", "issues")
$out += ("-" * 110)
foreach ($r in $rows | Sort-Object Kind, Name) {
    $out += ("{0,-6} {1,-38} {2,-7} {3,5} {4,6}  {5}" -f $r.Kind, $r.Name, $r.Ver, $r.Desc, $r.Lines, $r.Issues)
}
$out += ""
$out += if ($problems -eq 0) { "全部通过 ✅" } else { "有问题的 skill: $problems 个 ⚠️（真的没问题就 git commit --no-verify）" }
$out -join "`n"

if ($problems -gt 0) { exit 1 }
exit 0
