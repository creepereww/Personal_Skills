# 为什么这台机器的目录叫 `wgc`

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
| 家里的 | `WGC` | `wgc` |
| 公司的 | `WGC-WORK1-PX` | `wgc-work1-px` |

## 曾经想叫 `wgc-home`，为什么不行

改名前的试探方案是给家那台起个语义清晰的名字 `wgc-home`，但那样**永远匹配不上** ——
`wgc-home` ≠ `WGC`，机器一启动就找不到自己的档案。

三个候选方案当时的取舍：

| 方案 | 做法 | 结论 |
|---|---|---|
| A | 把家那台的主机名也改成 `WGC-HOME`，目录 `wgc-home` | 需要改系统主机名；放弃了 |
| **B** ✅ | **目录就叫 `wgc`，接受名字语义弱** | **采用** —— 零系统改动，机制最简单 |
| C | 加一层 `machine_of_host` 显式映射（`WGC` → `wgc-home`） | 多一层配置、多一个可能失配的地方；放弃了 |

**选 B 的代价**：光看目录名 `wgc` 看不出是哪台机器。所以靠这个 `NOTE.md` 和
`SKILL.md` 的标题（「wgc（家里的电脑）」）补上语义。

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
