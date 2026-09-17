---
name: local-skills-hub
description: 本机全局 skill 仓库（~/.skills）的使用规则。当需要新增/修改/删除 skill、排查 skill 没生效、或要把 skill 同步到其他电脑时使用。含一条不可违反的红线：不得直接编辑 store/ 下的文件。
version: v1.0
---

# Skills Hub

全机器的 skill 只有一份实体，放在 `~/.skills/store/`，通过 junction 挂给各个 agent。

## 结构

```
~/.skills/store/local/   纯本地 skill
~/.skills/store/fork/    从 GitHub 派生的 skill（含 .upstream 溯源）
~/.skills/store/cache/   远程 skill 缓存（不进 Git）
~/.skills/routing.json   各 agent 挂载点
~/.skills/registry.json  远程 skill 清单
~/.skills/proposals/     待审批提案
```

## 🚫 红线

**发现 skill 有问题时，不得直接编辑 `store/` 下任何文件。**

只能写 `~/.skills/proposals/<skill>.md`：

```markdown
# proposal: <skill 名>
## 症状
（哪一步失败或产出不对）
## 建议改动
（要增补/修改什么）
## 待插入位置
（在哪个章节）
```

然后告诉用户"已提交提案，等你确认"，由人批准后才会真正修改。**未经允许直接改 skill 文件 = 违反此 skill。**

## 常用操作

```powershell
pwsh C:\Users\cgw06\.skills\scripts\link.ps1            # 刷新挂载（新增/改名后必做）
pwsh C:\Users\cgw06\.skills\scripts\link.ps1 -DryRun    # 先看会做什么
pwsh C:\Users\cgw06\.skills\scripts\sync.ps1            # 拉取 + 刷新
pwsh C:\Users\cgw06\.skills\scripts\sync.ps1 -Commit "msg"   # 提交 + 同步
```

## 新增一个本地 skill

1. 在 `store/local/` 建目录 `local-<slug>/`
2. 写 `SKILL.md`，frontmatter 必须含 `name`（与目录名逐字符一致）、`description`、`version: v1.0`
3. 跑 `link.ps1` —— 四个 agent 同时就位

命名必须匹配 `^[a-z0-9]+(-[a-z0-9]+)*$`（小写字母数字 + 单连字符），**禁止** `@` `.` 大写字母 下划线 连续连字符。opencode 会强制校验，不符合就静默加载失败。

派生自 GitHub 的用 `local-<slug>-<reposlug>` 放 `store/fork/`，并在 `.upstream` 记录 `upstream_repo/path/base_commit/reason`（reason ≤3 行）。

## 版本号

`vX.Y`：局部补充 Y+1，结构重写 X+1。**不写 changelog、不写日期、不写改动原因** —— skill 正文要占上下文，能省则省。

## skill 没生效怎么查

1. 是不是 junction 没刷新 → 跑 `link.ps1`
2. 目录名与 frontmatter `name` 是否逐字符一致
3. 命名是否符合上面的正则
4. 是否被改名为 `SKILL.md.disabled`
5. 该 agent 是否认这个目录（见 local-wgc-machine skill 里的挂载表）
