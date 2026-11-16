# GBK 安全改写

> 示例中的 `main.c` 代表工程主源文件名，按实际替换。

## 为什么要小心

这些源文件是 **GBK 编码**。GBK 汉字占 2 字节，其中大量字节序列在 UTF-8 下是非法的。
如果某个工具按 UTF-8 解码 + 编码写回，非法字节会被替换成 `U+FFFD`（`EF BF BD`），
**原注释的字节就永久丢失了**，而且这种损坏只在被改过的文件里出现，很难和"本来就乱码"区分。

快速识别：

```bash
file *.c *.h                    # 正常的应显示 ISO-8859 text（其实是 GBK）
grep -ac $'\xef\xbf\xbd' *.c   # 正常应全为 0
```

如果某几个文件突然变成 `UTF-8 text` 且 `EF BF BD` 计数不为 0，而其它文件还是
`ISO-8859 text` 且为 0 —— 就是被按 UTF-8 重写过。

## 怎么改

### 首选：`scripts/gbk_edit.py`

```bash
python3 scripts/gbk_edit.py main.c '旧的注释' '新的注释'
python3 scripts/gbk_edit.py main.c --check          # 只体检不修改
python3 scripts/gbk_edit.py main.c '旧' '新' --dry-run
```

它会：自动备份到 `/tmp`、拒绝引入 U+FFFD、拒绝产生非法 GBK、拒绝意外改变行数。

### grep / sed 在这些文件上要加 `-a`

文件含非法 UTF-8 字节，grep 会判定为二进制，只打一行 `binary file matches` 而不给行号：

```bash
grep -an "PIN_KEY_MI" Interrupt.c        # -a 强制按文本处理
sed -n '174,220p' Interrupt.c | cat -A   # 自己看缩进/行尾时最直观
```

`sed -i` 只有在**替换串全是 ASCII** 时才安全；带中文就必须走 Python 字节替换。

### 行号 ≠ 索引

`d.split(b'\r\n')[i]` 的 `i` 是 0-based，等于「编辑器里的行号 − 1」。
照抄行号切会差一行（更糟的是 `IndexError`，文件末尾还有空串）。**用锚点断言代替数行号**：

```python
L = open(p, 'rb').read().split(b'\r\n')
start = next(i for i, l in enumerate(L) if l.rstrip().endswith(b'if(timer_200us < 5000)'))
assert L[start + 1].rstrip().endswith(b'led_power();')     # 确认锚点就是预期的那个
end   = next(i for i, l in enumerate(L) if i > start and l.strip() == b'}')
L[start:end + 1] = [L[start][:len(L[start]) - len(L[start].lstrip())] + b'led_charge_full();']
open(p, 'wb').write(b'\r\n'.join(L))
```

新建行时**沿用原块的缩进前缀**（`lstrip()` 前那截），这样 diff 里只少几行、不会整块重排。

### 手工字节级操作：Python

```python
p = 'main.c'
d = open(p, 'rb').read()                      # 二进制读
old = '旧文本'.encode('gbk')                  # 中文按 GBK 编码
new = '新文本'.encode('gbk')
assert d.count(old) == 1, d.count(old)        # 确认唯一匹配
d = d.replace(old, new, 1)
assert b'\xef\xbf\xbd' not in d               # 确认没引入损坏
open(p, 'wb').write(d)                        # 二进制写
```

### 大段重排/搬移时：按行切片再拼

重构（比如把一大段代码从函数挪进宏）时，按行号切片、字节原样搬运，能保证注释一个字不变：

```python
L = open(p, 'rb').read().split(b'\r\n')       # CRLF 文件
body = L[207:238]                             # 1-based 208..238，原样搬运
new  = L[:201] + body + L[238:]
open(p, 'wb').write(b'\r\n'.join(new))
```

配合断言锚点，防止行号漂移：

```python
assert L[205].strip() == b'static void evt_mitou_handle(void)'
```

### 绝对不要做的

- 用按 UTF-8 解码的编辑工具存盘（包括很多 IDE 的默认保存流程）
- `open(p, 'r')` / `open(p, 'w')` 默认文本模式（Python3 下还会把 `\n` 翻译成 `\r\n`）
- 在新写的注释里用中文（除非脚本明确 `.encode('gbk')`）
- `sed -i` 除非确认替换串全是 ASCII
- 往 GBK 文件里写 GBK 编不了的字符（`✓` `✗` `−` `①`…）→ `UnicodeEncodeError`。
  在 GBK 里用 `×` `√` `-`，写之前先 `s.encode('gbk')` 试一次

### 改 Markdown / 文档也要注意编码

工程里连 `.md`（开发日记）都是 **GBK + CRLF**。重写文档时同样走字节级写入：

```python
s = open('new.md', encoding='utf-8').read()            # 内容用 UTF-8 起草
data = s.replace('\n', '\r\n').encode('gbk')           # 落盘转 GBK + CRLF
assert b'\xef\xbf\xbd' not in data and data.decode('gbk')
open(p, 'wb').write(data)
```

## 已经损坏时的恢复

坏掉的字节是找不回来的，但可以**从旧版本里按行还原**，前提是有可对照的副本。

本工程没有 SVN pristine（`.svn/wc.db` 里查不到这个工程的节点），
所以恢复来源只有：自己的备份、或者 `另一引脚版本目录/` 里的另一个版本（引脚不同，只能对参考）。

### 逐行精确还原（无损）

如果原版本和当前版本的差异只是少量几行，可以对参考文件做同样的"破坏变换"，
再和损坏行逐字节比对——能对上就说明参考行就是原行：

```python
def lossy(b):                      # 模拟“按 UTF-8 有损解码再写回”
    return b.decode('utf-8', errors='replace').encode('utf-8')

ref_lines = open('ref.c','rb').read().splitlines(keepends=True)
index = {lossy(l): l for l in ref_lines}          # 变换后的字节 -> 原始行
damaged = open('cur.c','rb').read().splitlines(keepends=True)
fixed = [index.get(l, l) if b'\xef\xbf\xbd' in l else l for l in damaged]
```

### 按存活字节反推

`EF BF BD` 之外的字节是**完好**的（合法 UTF-8 的 GBK 字节对解码后会原样编码回去），
可以用它配合"重新变换必须逐字节复现"来反推，例如：

- `全` = `C8 AB`（C8 是 UTF-8 双字节头，AB 是延续字节 → 存活）
- `部` = `B2 B2`（B2 不是合法起始字节 → 两个都变 FFFD）
- `初始化` = `B3 F2` + `CABC` + `BBBA` → 表现为 `FFFD FFD` + `CABC` + `FFFD FFFD`

验证写法：

```python
assert lossy('初始化'.encode('gbk')) == b'\xef\xbf\xbd\xef\xbf\xbd' + \
       '始'.encode('gbk') + b'\xef\xbf\xbd\xef\xbf\xbd'
```

只有能在同样变换下逐字节复现的重建结果，才可以放心写回去。