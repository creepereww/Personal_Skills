# pull.ps1 —— 按需拉取远程（GitHub）skill 到 store/cache/
# 用法（PowerShell 7）：
#   pwsh .\pull.ps1 -All                拉取 registry.json 里全部 remote 条目
#   pwsh .\pull.ps1 -Id summarize       只拉一个
#   pwsh .\pull.ps1 -Id summarize -Force  已缓存也重新拉
#
# 说明：
#   - 只拉文件，单文件 >2MB 跳过
#   - 会把路径前缀剥掉，保证 store/cache/<id>/SKILL.md 在顶层，方便直接挂给 agent
#   - 拉取后写回 registry.json 的 commit / cached / pulled_date
#   - 未认证 GitHub API 限流 60 次/小时；需要更多就设环境变量 GITHUB_TOKEN

param(
    [string]$Id = "",
    [switch]$All,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$regPath = Join-Path $root "registry.json"
$reg = Get-Content $regPath -Raw -Encoding UTF8 | ConvertFrom-Json

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

foreach ($t in $targets) {
    $repo  = $t.repo
    $path  = if ($t.PSObject.Properties['path'] -and $t.path) { $t.path } else { "" }
    $cacheDir = Join-Path $root "store\cache\$($t.id)"

    if ((Test-Path $cacheDir) -and $t.cached -and -not $Force) {
        $log += ("SKIP     {0,-14} 已缓存 (commit {1})" -f $t.id, $t.commit)
        continue
    }

    $log += ("PULL     {0,-14} {1} {2}" -f $t.id, $repo, $(if ($path) { "[$path]" } else { "(整仓)" }))

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

        foreach ($f in $files) {
            $rel = $f.path
            if ($path -and $rel.StartsWith($path + '/')) { $rel = $rel.Substring($path.Length + 1) }
            $rawUrl = "https://raw.githubusercontent.com/$repo/$shaFull/$($f.path)"
            try {
                $content = Invoke-RestMethod -Uri $rawUrl -Headers $headers -TimeoutSec 30
                if ($content -isnot [string]) { $content = $content | ConvertTo-Json -Depth 20 }
                Save-TextFile (Join-Path $cacheDir $rel) $content
            }
            catch {
                $log += ("         WARN 下载失败: {0}" -f $rel)
            }
        }

        $t.commit = $sha
        $t.cached = $true
        if (-not $t.PSObject.Properties['mount']) { $t | Add-Member -NotePropertyName mount -NotePropertyValue $true }
        else { $t.mount = $true }
        if (-not $t.PSObject.Properties['pulled_date']) { $t | Add-Member -NotePropertyName pulled_date -NotePropertyValue "" }
        $t.pulled_date = (Get-Date).ToString("yyyy-MM-dd")
        $log += ("         已保存到 store\cache\{0}" -f $t.id)
    }
    catch {
        $log += ("         FAIL: {0}" -f $_.Exception.Message)
    }
}

$regJson = $reg | ConvertTo-Json -Depth 20
[System.IO.File]::WriteAllText($regPath, $regJson, (New-Object System.Text.UTF8Encoding($false)))

$log += ""
$log += "提示：拉完记得挂载 —— pwsh $(Join-Path $PSScriptRoot 'link.ps1')"
$log -join "`n"
