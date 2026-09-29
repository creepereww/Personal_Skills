# _common.ps1 —— 各脚本共用的环境探测函数
#
# 为什么要有这个文件：
#   早期版本把「这台机器的事实」硬编码进各脚本 —— git 装在哪、哪个 agent 装了。
#   换个机器就不成立：git 可能在 PATH、也可能在 D:\Git；某个 agent 可能根本没装。
#   本文件把这两件事收敛成两个函数，各脚本统一调用。
#
# 被谁用：link.ps1 / sync.ps1 / sync-preferences.ps1

# ---------------------------------------------------------------------------
# 找 git.exe
# ---------------------------------------------------------------------------
# 优先级：环境变量显式覆盖 > PATH > 常见安装位置。
# 关键点：**PATH 优先于硬编码路径**。
#   旧写法直接找 PortableGit，理由是「本机 git 不在 PATH 里」——
#   那只是某一台机器的局部事实，换台机器就不成立。
#   装了 Git 的机器 PATH 里必然有，装哪都行；PATH 没有再兜底。
#
# 覆盖方式：$env:SKILLS_GIT = "D:\somewhere\git.exe"
function Get-GitExe {
    # 1. 显式覆盖
    if ($env:SKILLS_GIT -and (Test-Path $env:SKILLS_GIT)) {
        return $env:SKILLS_GIT
    }

    # 2. PATH
    $cmd = Get-Command git -CommandType Application -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    # 3. 常见安装位置兜底
    #    注意：**不要在这里写死某台机器的专属路径**。机器专属事实属于
    #    store/machine/<主机名>/，不该进跟随 Git 的通用脚本。
    #    真有非标准位置，用 SKILLS_GIT 环境变量覆盖（见上）。
    $candidates = @(
        (Join-Path $env:ProgramFiles "Git\cmd\git.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Git\cmd\git.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Git\cmd\git.exe")
    ) | Where-Object { $_ -and (Test-Path $_) }
    if ($candidates.Count -gt 0) { return $candidates[0] }

    # 4. 宿主自带的 PortableGit：版本号写死会随升级失效，故用通配并取最高版本
    $portable = Join-Path $env:USERPROFILE ".workbuddy\binaries\PortableGit\versions"
    if (Test-Path $portable) {
        $hit = Get-ChildItem $portable -Directory -ErrorAction SilentlyContinue |
               Sort-Object Name -Descending |
               ForEach-Object { Join-Path $_.FullName "cmd\git.exe" } |
               Where-Object { Test-Path $_ } |
               Select-Object -First 1
        if ($hit) { return $hit }
    }

    throw "找不到 git。请安装 Git（装了就会进 PATH），或设环境变量 SKILLS_GIT 指向 git.exe。"
}

# ---------------------------------------------------------------------------
# 判断某个 client（agent）这台机器上装没装
# ---------------------------------------------------------------------------
# 判据设计：**默认看 skills 目录的父目录在不在**，而不是去猜安装特征。
#
# 为什么这么判：agent 的行为是「跑起来就会建自己的配置根目录」。
#   装了的机器，父目录必然存在；没装的机器，父目录自然不存在。
#   这样不需要知道它怎么装的（npm / winget / 绿色版都无所谓）。
#
# 特例：有些 agent 的 skills 目录原生不存在（如 opencode，首次 link 时才建），
#   父目录判据会误判为「没装」。这类 client 在 routing.json 里显式写 detect。
#
# routing.json 的 client 段可写：
#   "detect":     ["%USERPROFILE%\\.zcode", ...]   自定义探测路径（支持环境变量）
#   "detect_any": true                             多个路径「任一存在」即可（默认全部存在才算）
#   "detect":     []                               跳过探测，永远视为已装
function Test-ClientInstalled($clientName, $def, $root) {
    # 显式声明空数组 -> 不探测，永远视为已装
    if ($def.PSObject.Properties['detect']) {
        $paths = @($def.detect)
        if ($paths.Count -eq 0) {
            return [PSCustomObject]@{ Installed = $true; Reason = "detect=[] 显式跳过探测" }
        }

        $results = @()
        foreach ($p in $paths) {
            $expanded = [Environment]::ExpandEnvironmentVariables($p)
            $results += [PSCustomObject]@{ Path = $p; Exists = (Test-Path $expanded) }
        }

        $any = [bool]($def.PSObject.Properties['detect_any'] -and $def.detect_any)
        $ok = if ($any) {
            [bool]($results | Where-Object { $_.Exists })
        } else {
            -not ($results | Where-Object { -not $_.Exists })
        }

        $detail = ($results | ForEach-Object { ($(if ($_.Exists) { "有" } else { "无" })) + $_.Path }) -join "  "
        return [PSCustomObject]@{
            Installed = $ok
            Reason    = "detect$(if ($any) { '-any' } else { '' }): $detail"
        }
    }

    # 默认：看 skills 目录的父目录
    $dir = [Environment]::ExpandEnvironmentVariables($def.dir)
    $parent = Split-Path -Parent $dir
    if (Test-Path $parent) {
        return [PSCustomObject]@{ Installed = $true; Reason = "父目录存在: $parent" }
    }
    # 父目录不存在，但 skills 目录自己存在 -> 也算装了（有人手工建过）
    if (Test-Path $dir) {
        return [PSCustomObject]@{ Installed = $true; Reason = "skills 目录已存在: $dir" }
    }
    return [PSCustomObject]@{ Installed = $false; Reason = "父目录不存在: $parent" }
}

# ---------------------------------------------------------------------------
# 读取 routing.json 并返回客户端的挂载决策表
# ---------------------------------------------------------------------------
# 返回每项：Name / Def / Dir / Installed / InstallReason
# 不在这里做「要不要挂」的最终判断（那由调用方结合 -Force 决定），只提供事实。
function Get-ClientPlan($root) {
    $cfgPath = Join-Path $root "routing.json"
    if (-not (Test-Path $cfgPath)) { throw "找不到 routing.json：$cfgPath" }
    $cfg = Get-Content $cfgPath -Raw -Encoding UTF8 | ConvertFrom-Json

    $plan = @()
    foreach ($prop in $cfg.clients.PSObject.Properties) {
        $name = $prop.Name
        $def  = $prop.Value
        $det  = Test-ClientInstalled $name $def $root

        $plan += [PSCustomObject]@{
            Name          = $name
            Def           = $def
            Dir           = [Environment]::ExpandEnvironmentVariables($def.dir)
            Enabled       = [bool]$def.enabled
            Mode          = $def.mode
            Installed     = $det.Installed
            InstallReason = $det.Reason
        }
    }
    return [PSCustomObject]@{ Config = $cfg; Clients = $plan }
}
