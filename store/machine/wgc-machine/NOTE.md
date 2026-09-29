# 为什么这台机器的目录叫 `wgc-machine`

**一句话**：目录名必须等于它的 `%COMPUTERNAME%`（小写），所以起不了语义化的名字。

## 机制

`scripts/link.ps1` 用**本机主机名**去 `store/machine/` 下找同名目录，只挂匹配到的那个：

```powershell
Get-ChildItem $machineDir -Directory | ForEach-Object {
    if ($_.Name -ieq $env:COMPUTERNAME) { ... }   # 大小写不敏感比较
}
```

所以：

| 这台机器 | `%COMPUTERNAME%` | 目录必须叫 |
|---|---|---|
| 家里的 | `WGC_MACHINE` | `wgc-machine` |
| 公司的 | `WGC-WORK1-PX` | `wgc-work1-px` |

## 目录名只能跟着主机名，不能凭语义起

想给机器起个语义清晰的名字（如 `wgc-home`）行不通 —— 目录名一旦不等于主机名，
脚本就永远匹配不上，机器一启动就找不到自己的档案。也别加显式映射表（`WGC` → `wgc-home`）：
多一层配置就多一个可能失配的地方，而主机名本身就是唯一标识，没必要再包一层。

代价是目录名不自解释（`wgc-machine` 只说它是哪台机器，不说它是什么角色）。
语义靠这个 `NOTE.md` 和 `SKILL.md` 的标题（「wgc-machine（家里的电脑）」）补上。

⚠️ **易错点**：主机名可能含**下划线**（如 `WGC_MACHINE`），而 skill 目录命名正则
`^[a-z0-9]+(-[a-z0-9]+)*$` **禁止下划线**，目录只能用 `-` 写成 `wgc-machine` ——
此时目录名**永远不可能等于主机名**，必须在 `routing.json` 的 `host_aliases` 里补一条映射
（`"WGC_MACHINE": "wgc-machine"`），否则档案静默不挂载。这条别名是**长期设施**，别当过渡条目删掉。

只有主机名本身合法（纯小写字母数字 + 连字符）时，目录名才能直接等于主机名、无需别名。
**永远以 `hostname` 实测值为准**，别靠记忆或简称。

## 大小写的坑

`%COMPUTERNAME%` **统一大写返回**，目录名按 skill 命名规范必须**全小写**
（正则 `^[a-z0-9]+(-[a-z0-9]+)*$` 禁止大写，opencode 会静默加载失败）。

所以脚本里必须用**大小写不敏感**的比较（`-ieq`，不是 `-eq`）：

```
'wgc-work1-px' vs 'WGC-WORK1-PX' : -ieq=True   -ceq(区分大小写)=False
```

用 `-eq` 的话 `WGC-WORK1-PX` 匹配不上 `wgc-work1-px`，两台机器都会挂不上档案。

## 加新机器时怎么做

1. 在那台机器上跑 `hostname` 拿到主机名（记下原文，注意大小写）
2. 建目录 `store/machine/<主机名全小写>/`
3. 里面放 `SKILL.md`，frontmatter 的 `name` **等于目录名**
4. 跑 `pwsh ~/.skills/scripts/link.ps1` —— 输出里会显示 `machine 档: 本机 <主机名> -> 挂载 [...]`

配好后**这台机器不会**挂上别的机器的档案（脚本只挂匹配的那一个），
所以在各机器的 `SKILL.md` 里可以放心写死绝对路径。
