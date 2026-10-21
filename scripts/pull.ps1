# pull.ps1 —— 按需拉取远程（GitHub）skill 到 store/cache/
# 用法（PowerShell 7）：
#   pwsh .\pull.ps1 -All                拉取 registry.json 里全部 remote 条目
#   pwsh .\pull.ps1 -All -DryRun        只列出会拉什么，不联网、不回写 registry（安全预演）
#   pwsh .\pull.ps1 -Id summarize       只拉一个
#   pwsh .\pull.ps1 -Id summarize -Force  已缓存也重新拉
#
# 说明：
#   - 只拉文件，单文件 >2MB 跳过
#   - 会把路径前缀剥掉，保证 store/cache/<id>/SKILL.md 在顶层，方便直接挂给 agent
#   - 拉取后把 commit / 拉取日期写进 **store/cache/_state.json**（本机状态，不进版本库）。
#     registry.json 只存跨机器通用的坐标（repo / path / branch / license / source / note / mount），
#     不再记录任何「某台机器拉没拉过」的事实
#   - 未认证 GitHub API 限流 60 次/小时；需要更多就设环境变量 GITHUB_TOKEN

param(
    [string]$Id = "",
    [switch]$All,
    [switch]$Force,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$regPath = Join-Path $root "registry.json"
$reg = Get-Content $regPath -Raw -Encoding UTF8 | ConvertFrom-Json

# 本机拉取状态（拉到哪个 commit、什么时候拉的）—— 每台机器不同，写 store/cache/_state.json。
# 整个 store/cache/ 被 .gitignore 排除，所以它天然不进版本库，各机互不干扰。
# 别再往 registry.json 写这些：那是共享文件，各机回写会互相覆盖、产生无意义 diff 和 rebase 冲突。
$statePath = Join-Path $root "store\cache\_state.json"
$state = @{}
if (Test-Path $statePath) {
    try { $state = (Get-Content $statePath -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable) } catch { $state = @{} }
}

$headers = @{ 'User-Agent' = 'skills-hub' }
if ($env:GITHUB_TOKEN) { $headers['Authorization'] = "Bearer $env:GITHUB_TOKEN" }

function Invoke-GitHubApi($path) {
    $url = "https://api.github.com" + $path
    try {
        return Invoke-RestMethod -Uri $url -Headers $headers -TimeoutSec 30
    }
    catch {
        throw "GitHub API 失败: $path —— $($_.Exception.Message)"
    }
}

function Save-TextFile($path, $content) {
    $dir = Split-Path -Parent $path
    if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    [System.IO.File]::WriteAllText($path, $content, (New-Object System.Text.UTF8Encoding($false)))
}

$targets = @($reg.remote | Where-Object { -not ($_.PSObject.Properties['_example'] -and $_._example) })
if ($Id)      { $targets = @($targets | Where-Object { $_.id -eq $Id }) }
elseif (-not $All) { throw "请指定 -Id 或 -All" }

$log = @()
$changed = $false

foreach ($t in $targets) {
    # skillhub 源的条目由 skillhub CLI 拉取/升级，这里不管 —— 否则会拿去查 GitHub 而报错
    if ($t.PSObject.Properties['source'] -and $t.source -eq 'skillhub') {
        $log += ("SKIP     {0,-14} skillhub 源，用 skillhub CLI 处理" -f $t.id)
        continue
    }

    $repo  = $t.repo
    $path  = if ($t.PSObject.Properties['path'] -and $t.path) { $t.path } else { "" }
    $cacheDir = Join-Path $root "store\cache\$($t.id)"

    # 退休/停用的条目不再拉取，否则删了缓存会被 -All 又拉回来
    $retired = ($t.PSObject.Properties['retired'] -and $t.retired) -or ($t.PSObject.Properties['disabled'] -and $t.disabled)
    if ($retired -and -not $Force) {
        $log += ("SKIP     {0,-14} retired/disabled，不拉取" -f $t.id)
        continue
    }

    # 判据只看「本机有没有这个目录」—— registry 里曾经有个 cached 字段，记的是登记那台机器
    # 有没有拉过，跟本机无关，靠它判断会得出错误结论（已移除该字段）
    if ((Test-Path $cacheDir) -and -not $Force) {
        $lc = if ($state.ContainsKey($t.id) -and $state[$t.id].commit) { $state[$t.id].commit } else { "无记录" }
        $log += ("SKIP     {0,-14} 本机已缓存 (commit {1})" -f $t.id, $lc)
        continue
    }

    $log += ("PULL     {0,-14} {1} {2}" -f $t.id, $repo, $(if ($path) { "[$path]" } else { "(整仓)" }))
    if ($DryRun) {
        $log += "         (dry-run：不联网、不下载、不回写)"
        continue
    }

    try {
        $meta   = Invoke-GitHubApi "/repos/$repo"
        $branch = if ($meta.default_branch) { $meta.default_branch } else { "main" }

        $q = "/repos/$repo/commits?sha=$branch&per_page=1"
        if ($path) { $q += "&path=$path" }
        $commits = Invoke-GitHubApi $q
        $shaFull = $commits[0].sha
        $sha     = $shaFull.Substring(0, 7)
        $log += ("         branch={0} commit={1} ({2})" -f $branch, $sha, $commits[0].commit.author.date)

        $tree = Invoke-GitHubApi "/repos/$repo/git/trees/$shaFull`?recursive=1"
        $files = @($tree.tree | Where-Object {
            $_.type -eq 'blob' -and
            $_.size -lt 2097152 -and
            $(if ($path) { $_.path.StartsWith($path + '/') -or $_.path -eq $path } else { $true })
        })

        if (-not $files -or $files.Count -eq 0) { throw "路径下没有找到文件" }
        $log += ("         files: {0}" -f $files.Count)

        if (Test-Path $cacheDir) { Remove-Item $cacheDir -Recurse -Force }
        New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null

        $ok = 0
        foreach ($f in $files) {
            $rel = $f.path
            if ($path -and $rel.StartsWith($path + '/')) { $rel = $rel.Substring($path.Length + 1) }
            $rawUrl = "https://raw.githubusercontent.com/$repo/$shaFull/$($f.path)"
            try {
                $content = Invoke-RestMethod -Uri $rawUrl -Headers $headers -TimeoutSec 30
                if ($content -isnot [string]) { $content = $content | ConvertTo-Json -Depth 20 }
                Save-TextFile (Join-Path $cacheDir $rel) $content
                $ok++
            }
            catch {
                $log += ("         WARN 下载失败: {0}" -f $rel)
            }
        }

        # 关键保护：一个文件都没下到（典型是 raw.githubusercontent.com 不通）时，
        # 回滚刚建的空目录并跳过回写 —— 不再改动 commit/cached/mount/pulled_date
        if ($ok -le 0) {
            if (Test-Path $cacheDir) { Remove-Item $cacheDir -Recurse -Force }
            $log += ("         FAIL 全部 {0} 个文件下载失败，已删除空目录，registry.json 未改动" -f $files.Count)
            continue
        }
        if ($ok -lt $files.Count) { $log += ("         WARN 部分失败：成功 {0}/{1}" -f $ok, $files.Count) }

        $state[$t.id] = @{ commit = $sha; pulled = (Get-Date).ToString("yyyy-MM-dd") }
        $changed = $true
        $log += ("         已保存到 store\cache\{0}（{1} 个文件）" -f $t.id, $ok)
    }
    catch {
        $log += ("         FAIL: {0}" -f $_.Exception.Message)
    }
}

if ($DryRun) {
    $log += ""
    $log += "dry-run 完成：未联网、未写任何文件"
}
elseif ($changed) {
    ($state | ConvertTo-Json -Depth 6) | Set-Content $statePath -Encoding UTF8
    $log += ""
    $log += "本机拉取状态已写入 store\cache\_state.json（不进版本库，各机独立）"
    $log += "registry.json 未改动 —— 它是共享文件，不记本机状态"
    $log += "提示：拉完记得挂载 —— pwsh $(Join-Path $PSScriptRoot 'link.ps1')"
}
else {
    $log += ""
    $log += "本次无任何条目被改动"
}
$log -join "`n"
