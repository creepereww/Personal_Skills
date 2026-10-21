# install-hook.ps1 —— 安装 / 校验本仓库的 pre-commit hook
# 用法（PowerShell 7）：
#   pwsh .\install-hook.ps1            安装（没有就装、内容不一致就更到最新）
#   pwsh .\install-hook.ps1 -Check     只校验不写盘；缺失或过时则 exit 1（给 sync.ps1 用）
#   pwsh .\install-hook.ps1 -Force     强制覆盖（本地改过 hook 想恢复官方版时用）
#   pwsh .\install-hook.ps1 -Uninstall 摘掉 hook
#
# 为什么非得有这个脚本：
#   .git/hooks/ 是 git 的内部目录，**任何仓库都不进版本库**（git ls-files .git 永远为空）。
#   所以「提交前跑合规检查」这件事没法靠 clone 带过来：新机器 clone 完默认没有 hook，
#   audit.ps1 就永远不会被触发，违规内容一路绿灯推上去，直到某台装了 hook 的机器才炸。
#   这不是"记得装一下"就能解决的事 —— 忘的那次是静默的。故把装配动作固化成脚本，
#   并由 sync.ps1 每次同步自动调用。
#
# 另一个坑：hook 里**绝不能写死绝对路径**（如 C:/Users/xxx/.skills/...）。
#   换台机器用户名不同就指向不存在的文件，报错是"找不到脚本"，看起来像 hook 坏了，
#   实际没人知道该改哪。所以下面生成的是用 git rev-parse 现算仓库根的通用版。

param(
    [switch]$Check,
    [switch]$Force,
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "_common.ps1")
$git = Get-GitExe

# 尊重 core.hooksPath（有人会把 hook 集中管理）
$hooksPath = (& $git -C $root rev-parse --git-path hooks 2>$null | Out-String).Trim()
if (-not $hooksPath) { $hooksPath = ".git/hooks" }
if (-not [System.IO.Path]::IsPathRooted($hooksPath)) { $hooksPath = Join-Path $root $hooksPath }
$target = Join-Path $hooksPath "pre-commit"

$hookId = "skills-audit-hook/v1"

$hookLines = @(
    '#!/bin/sh'
    "# $hookId"
    '# 由 scripts/install-hook.ps1 生成 —— 别手工改这份，要改规则去改 scripts/audit.ps1。'
    '# 作用：提交前跑仓库唯一权威检查器 audit.ps1，不合规就拦下。'
    'REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)'
    'if [ -z "$REPO_ROOT" ]; then'
    '  echo "pre-commit: 取不到仓库根，跳过合规检查" >&2'
    '  exit 0'
    'fi'
    'if [ ! -f "$REPO_ROOT/scripts/audit.ps1" ]; then'
    '  echo "pre-commit: 找不到 scripts/audit.ps1，跳过合规检查" >&2'
    '  exit 0'
    'fi'
    'if ! command -v pwsh >/dev/null 2>&1; then'
    '  echo "pre-commit: 本机没有 pwsh（PowerShell 7），跳过合规检查 —— 装上后自动生效" >&2'
    '  exit 0'
    'fi'
    'pwsh -NoProfile -File "$REPO_ROOT/scripts/audit.ps1"'
    'exit $?'
)
$hookText = ($hookLines -join "`n") + "`n"

if ($Uninstall) {
    if (Test-Path $target) {
        Remove-Item $target -Force
        "UNINSTALLED  $target"
    } else {
        "NOTFOUND     本来就没有 hook，无需卸载"
    }
    exit 0
}

$current = if (Test-Path $target) { [System.IO.File]::ReadAllText($target) } else { "" }
$isOurs  = $current -match [regex]::Escape($hookId)
$upToDate = $isOurs -and ($current.TrimEnd() -eq $hookText.TrimEnd())

if ($Check) {
    if (-not (Test-Path $target)) {
        "CHECK        MISSING  $target"
        exit 1
    }
    if (-not $isOurs) {
        "CHECK        FOREIGN  hook 存在但不是本脚本生成的版本（$target）"
        exit 1
    }
    if (-not $upToDate) {
        "CHECK        STALE    hook 内容过时，需重装（$target）"
        exit 1
    }
    "CHECK        OK       hook 在位且最新"
    exit 0
}

if ($upToDate -and -not $Force) {
    "SKIP         hook 已是最新的（$target）"
    exit 0
}

if ((Test-Path $target) -and -not $isOurs -and -not $Force) {
    "REFUSED      hook 已存在但不是本脚本生成的版本，不动它。"
    "             想换成标准版：pwsh scripts/install-hook.ps1 -Force"
    "             想看现有内容：git config core.hooksPath 或 cat $target"
    exit 1
}

if (-not (Test-Path $hooksPath)) { New-Item -ItemType Directory -Path $hooksPath -Force | Out-Null }

# 必须写 LF：git 自带的 sh 遇到 CRLF 的 shebang 会报 bad interpreter
[System.IO.File]::WriteAllText($target, $hookText, (New-Object System.Text.UTF8Encoding($false)))

if (-not $IsWindows) {
    & chmod +x $target 2>$null
}

$verb = if ($current) { "UPDATED" } else { "INSTALLED" }
"$verb      $target"
"           现在提交会自动跑 scripts/audit.ps1；真要跳过用 git commit --no-verify"
