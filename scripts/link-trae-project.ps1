# link-trae-project.ps1 —— 把 _active/trae 视图接到某个项目的 .trae/skills
#
# 为什么需要单独一个脚本：VS Code 里的 Trae 插件工具权限只到工作目录，
# 读不到用户级 skills 目录（实测 `Access denied: restricted to the working directory`），
# 所以它只认项目级 <项目>/.trae/skills/。而技能实体统一在仓库 —— 于是在项目里建一条
# junction 指向 _active/trae 视图。该视图与 WSL 里 opencode 读的 _active/opencode
# 用同一份画像，因此两边内容天然同步（改 routing.json 一处即可）。
#
# 用法（PowerShell 7）：
#   pwsh .\link-trae-project.ps1 -Project D:\work\pxs-fs12
#   pwsh .\link-trae-project.ps1 -Project D:\work\pxs-fs12 -DryRun
#   pwsh .\link-trae-project.ps1 -Project D:\work\pxs-fs12 -Remove
#
# 规则：
#   - 只建 junction，不复制文件；遇到真实目录一律 CONFLICT，绝不覆盖
#   - 先跑 .\link.ps1 -Client trae-plugin 把视图刷出来，再给项目接线

param(
    [string]$Project = "",
    [switch]$Remove,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$view = Join-Path $root "_active\trae"

if (-not $Project) {
    throw "缺少 -Project。用法：pwsh .\link-trae-project.ps1 -Project D:\work\myproj"
}
if (-not (Test-Path $Project)) {
    throw "项目目录不存在：$Project"
}
$proj    = (Resolve-Path $Project).Path
$traeDir = Join-Path $proj ".trae"
$link    = Join-Path $traeDir "skills"

function Get-LinkInfo($p) {
    $it = Get-Item $p -Force
    $isLink = (($it.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)
    $t = $null
    if ($isLink) { try { $t = $it.LinkTarget } catch { $t = $null } }
    return [PSCustomObject]@{ IsLink = $isLink; Target = $t }
}

if ($Remove) {
    if (-not (Test-Path $link)) { Write-Output "SKIP     没有 $link"; return }
    $info = Get-LinkInfo $link
    if (-not $info.IsLink) {
        Write-Output "CONFLICT $link 是真实目录，不会删除；确认后自行移走"
        return
    }
    if ($info.Target -and ($info.Target.TrimEnd('\') -ne $view.TrimEnd('\'))) {
        Write-Output "SKIP     指向 $($info.Target)，不是本视图，未动"
        return
    }
    if ($DryRun) { Write-Output "WOULD    REMOVE $link"; return }
    [System.IO.Directory]::Delete($link, $false)
    Write-Output "REMOVE   $link"
    return
}

if (-not (Test-Path $view)) {
    Write-Output "MISSING  视图不存在：$view"
    Write-Output "         先跑：pwsh .\link.ps1 -Client trae-plugin"
    return
}

if (-not (Test-Path $traeDir)) {
    if ($DryRun) { Write-Output "WOULD    MKDIR $traeDir" }
    else {
        New-Item -ItemType Directory -Path $traeDir -Force | Out-Null
        Write-Output "MKDIR    $traeDir"
    }
}

if (Test-Path $link) {
    $info = Get-LinkInfo $link
    if (-not $info.IsLink) {
        $n = @(Get-ChildItem $link -Force -ErrorAction SilentlyContinue).Count
        Write-Output "CONFLICT $link 是真实目录（$n 项），未改动"
        Write-Output "         要接入视图：先把里面的技能移走/备份，再重跑本脚本"
        return
    }
    if ($info.Target -and ($info.Target.TrimEnd('\') -eq $view.TrimEnd('\'))) {
        Write-Output "LINK     $link -> 视图（unchanged）"
        return
    }
    if ($DryRun) { Write-Output "WOULD    RELINK $link（当前 $($info.Target)）-> 视图"; return }
    [System.IO.Directory]::Delete($link, $false)
    New-Item -ItemType Junction -Path $link -Target $view | Out-Null
    Write-Output "LINK     $link 已重指到视图（原 $($info.Target)）"
    return
}

if ($DryRun) { Write-Output "WOULD    LINK $link -> $view"; return }
New-Item -ItemType Junction -Path $link -Target $view | Out-Null
Write-Output "LINK     $link -> $view"
Write-Output "         提示：建议把 .trae/skills 加进项目 .gitignore（junction 里的内容不该进项目仓库）"
