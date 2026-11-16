---
name: local-sinocmcu-9959b-fw
description: 晟矽微（SinoMCU）MC9959B 8 位 MCU 固件工程的通用规则 —— 用 SDCC 改 C 代码、语法体检、定位报错时使用。**这些芯片不是 8051**：自研内核（movra/swapar/goto 一类指令），`sdcc -mmcs51` 只当 lint、不产可烧代码，出 bin 必须走 Sino IDE。覆盖：源文件 GBK+CRLF 的字节安全改写（禁止 UTF-8 工具）、SDCC 多行宏与续行（反斜杠）规则、开关宏必须写 0/1、关闭通道用哑元变量、8 位裸机资源复用原则、真跑 sdcc 而非靠推断、重构后用 asm diff 辅助判断结构未变、Sino IDE 工具链的无害输出清单。触发：Sino MCU 固件、9959B 固件、SDCC、mcs51、不是 8051、mc32f7092、GBK 乱码、CRLF、宏续行、multi-line comment、sdcc error、改 C 代码、裸机资源、asm diff、Sino IDE、mc32-common.h、MC9959B.h。
version: v0.1
---

# SinoMCU MC9959B 固件工程通用规则

面向 **SinoMCU 8 位 MCU + SDCC** 的裸机工程。下面每条都在真实工程里踩过或验证过，
**不要凭直觉推断**。

## ⚠ 适用前提：这些芯片不是 8051

SinoMCU 的 8 位线用**自研内核**，指令集是 `movra` / `swapar` / `swapr` / `goto` / `call` 这一套，
**与 8051 汇编不通用**。工具链的真实分工：

| 用途 | 工具 | 可信度 |
|---|---|---|
| **出可烧 bin** | Sino IDE（Build） | ✅ 唯一权威 |
| **语法体检 / 结构检查** | `sdcc -mmcs51` | ⚠️ 只是借 mcs51 后端当 lint，**不产可烧代码** |

**"编译通过" ≠ "能烧"**。sdcc 那步只证明语法与宏展开没毛病；它生成的 `.asm` 是 mcs51 指令，
跟目标芯片机器码不是一回事（`Output/*.map` 里器件名如 `mc32f7092`、链接器 `gplink` 就是证据）。
凡是"能不能烧、烧了行为对不对"的判断，只能回到 Sino IDE + 实机。

> 本文件只放**跨项目成立**的部分。PXS-FS12 / PXS-FD07 这类具体产品的代码架构、引脚分配、
> 告警清单见 `references/example-pxs-project.md`（作为参考实例，新项目别照抄业务逻辑）。

## 0. 设计基调：8 位裸机、资源紧张 —— 先想复用，再想新增

8 位裸机（无 RTOS、无动态内存，FLASH/RAM 都紧）。动手前先问"现有变量/计时器/状态机能复用吗"：

- **变量**：优先复用已有计数器（例：长按快增复用 `key_press_timer_1ms`，到阈值回填起点做分频，
  零新增变量）；确实要加才加，并选最窄类型（`u8` 够就别 `u16`）
- **状态/流程**：能挂到现有 `gWorkmode` 类分支上就别加新模式；能复用现有报警/显示路径就别新写
- **实现**：同一效果只写一次、参数化共享（例：`rgb_blink(color, times)` 一个函数服务五个报警）；
  `do{...}while(0)` 宏零调用开销（见 §3.4）
- **代价**：不用浮点、少用除法和大表（浮点库会拖进每个调用点，见 §6）；不做规格没要求的"顺手优化"
- 改完看 `sdcc` 的 CODE/RAM 增量，明显变大就回头找复用点

## 1. 【最高优先级】源文件是 GBK + CRLF，绝不能用按 UTF-8 解码的工具改写

按 UTF-8 读写会把 GBK 中文字节判为非法、替换成 `U+FFFD`（`EF BF BD`）并**写回文件**，
原注释字节永久丢失。

体检：

```bash
file *.c *.h                    # 正常应显示 ISO-8859 text（其实是 GBK）
grep -ac $'\xef\xbf\xbd' *.c    # 正常必须全为 0
```

如果某几个文件突然变成 `UTF-8 text` 且 FFFD 计数非 0、其它文件仍是 `ISO-8859` 且为 0 ——
就是被按 UTF-8 重写过。

**改这些文件只能用字节级工具**，`scripts/gbk_edit.py`：

```bash
python3 scripts/gbk_edit.py main.c --check           # 只体检
python3 scripts/gbk_edit.py main.c '旧文本' '新文本'   # 替换（自动备份到 /tmp）
```

纪律：

- **中文注释是允许的、也是惯例**，但必须以 **GBK 字节**写入，并保持 **CRLF** 行尾
- Python 里用二进制模式：`open(p,'rb')` / `open(p,'wb')`，字符串手动 `.encode('gbk')`
- 绝不用 `open(p,'r')` / `open(p,'w')`（默认文本模式会做换行翻译）
- 改完立刻 `grep -ac $'\xef\xbf\xbd'` 必须为 0
- 大段搬移代码时按行切片、字节原样搬运，配 `assert` 锚点防行号漂移

### 1.1 grep / sed 在这些文件上要加 `-a`

文件含非法 UTF-8 字节，grep 会判定为二进制，只打一行 `binary file matches` 而不给行号：

```bash
grep -an "PIN_KEY_MI" Interrupt.c     # -a 强制按文本
sed -n '1,50p' foo.c                  # 自己看没问题；接管道给 grep 时要 grep -a
```

### 1.2 按行切片时：索引是「行号 − 1」

`d.split(b'\r\n')[i]` 的 `i` 是 0-based。照抄编辑器里的行号去切会差一行甚至 `IndexError`
（这个坑踩过）。切之前用锚点断言，不要靠肉眼数：

```python
start = next(i for i, l in enumerate(L) if l.rstrip().endswith(b'if(timer_200us < 5000)'))
assert L[start + 1].rstrip().endswith(b'led_power();')      # 锚点跟着一起断言
```

细节和损坏恢复见 `references/safe-editing-gbk.md`。

## 2. 怎么编译

### 正式编译（Sino IDE，Windows）

IDE 把工具目录加进 PATH 后，在**工程目录下**用 `c <文件名>.c`：

```cmd
set PATH=D:\SinemcuIDE_<版本>\tools
c <主文件名>.c
```

单文件只做语法/代码生成检查，不链接。要出 bin 走 IDE 的 Build。

### 快速验证（SDCC，语法体检 —— 别拿它当"能烧"的证明）

改 C 代码后**必须**真跑一遍 sdcc，但记住它只是 lint（见开头「适用前提」）：

```bash
PROJ=<工程目录>                     # 例如 /mnt/d/SVN/.../02-软件版本库/<产品>
INC=<SDK 头文件目录>                # 含 mc32-common.h / MC9959B.h
rm -rf /tmp/b && mkdir /tmp/b && cd /tmp/b
cp "$PROJ"/*.c "$PROJ"/*.h .        # 复制出去编，别在工程里生成 .asm/.rel
sdcc -mmcs51 --model-small --std-c99 -I. -I"$INC" <主文件名>.c
```

（`.vscode/c_cpp_properties.json` 里那一堆 `defines` 是给 IntelliSense 模拟 SDCC 关键字的，
编译不用加。）

**关键纪律：判断"有没有语法错误"只看真实的 `error` 字样。**
不要用 `sdcc -E` 后去预处理输出里 grep 关键字来判断续行/宏是否生效 —— 宏体泄漏成文件作用域的
普通文本时关键字照样能搜到，会得出完全相反的结论。这个坑踩过两次。

有 `#if` 开关时**两种取值都要验证**。

### 重构类改动：编译通过还不够，要 diff 生成的指令流

搬代码进宏、拆头文件、合并函数这类**只挪位置、不改逻辑**的改动，"编译过了"不能证明行为没变。
要用 `sdcc -S` 出 `.asm`，归一化后**逐行 diff**：

```bash
sdcc -mmcs51 --model-small --std-c99 -I. -I"$INC" -S <主文件>.c     # -S 保留 .asm
norm() { grep -avE "^;|^$" "$1" | sed -E 's/[0-9]{4,5}\$/LBL/; s/_10000_[0-9]+/_10000_UID/g'; }
norm old.asm > old.code; norm new.asm > new.code; diff old.code new.code
```

判读：

- 只剩 `ljmp` → `sjmp`、标签编号平移 = **块布局变了，行为不变**，可以接受
- 出现 `lcall` 位置的挪动（例如内联判断变成 `lcall _xxx`）= 代码确实换了地方，
  要逐条确认那就是本次改动预期的那一处
- **两边配置宏必须一致**（例如 `EVT_PRIORITY` 取同一个值），否则整个主循环分支会重排，
  diff 全是噪音

已用它验证过多次重构（宏封装、`MCU_SLEEP` 合并、头文件拆分）。

**但要知道它的证明力边界**：diff 的是 **mcs51 后端**产物，只能说明"控制流与结构没变"，
**不能证明目标芯片的机器码等价** —— 因为真实内核不是 8051。所以它是"改动没跑偏"的间接证据，
最终验收仍要 Sino IDE 出 bin + 实机跑一遍。

## 3. 续行（`\`）规则 —— 这个工具链最容易翻车的地方

### 3.1 行尾 `\` 后面**不能跟任何东西**

```c
#define led_charging() Dis_Elequa10 = Elequa_persent10;\//电量数码管两位COM数据   ✗
```

注释挡在 `\` 后面 → `\` 被注释吞掉 → 续行失效 → 宏只到第一行结束，
后续语句变成游离在文件作用域的语句，报"表达式必须含有常量值"之类的怪错。

正确：续行符必须在真正的行尾，注释单独一行放在宏外面。

### 3.2 `#define` 行末尾必须有 `\`

```c
#define EVT_MITOU_HANDLE()	do { \        ✓  define 行也要有
	/* burst_flag = 1;*/ \
	...
}while(0)                                 ✓  最后一行不能有
```

漏掉 define 行的 `\` → 宏体在第一个换行处结束 → 后面的代码掉到文件作用域 →
**报错行号指向宏体内那行**，极难定位（`xxx.c:212: syntax error: token -> 'if'` 就是这么来的）。

### 3.3 宏体里不能用 `//` 注释

续行后整个宏体是一条逻辑行，`//` 会把宏体**剩余部分全部吞掉**。必须用 `/* */`。

```c
#define led_charging() do{ \
    Dis_Elequa10 = Elequa_persent10; \
    Dis_Elequa1 = Elequa_persent1; \
}while(0)
```

历史上多处在宏里用 `//` 翻过车，现在看到的 `warning: multi-line comment` 就是残留。

### 3.4 `do{}while(0)` 不增加运行时间

`while(0)` 编译期恒假，优化器整个消掉，**生成的机器码与直接写赋值完全一样，运行时间零增加**
（只有 `-O0` 调试编译会多 1~2 个周期跳转）。这是 8 位 MCU 上用宏而不是函数的理由，
不要为了"可读性"改回函数调用。

## 4. 开关宏必须定义成 0 或 1，不能留空

```c
#define SMOKE_PWM_T3C          /* ✗ 空定义 */
```

一旦空定义，下游全部崩：

| 症状 | 实际原因 |
|---|---|
| `error: operator '\|\|' has no right operand` | `#if 0 \|\| 1 \|\|` 右边空了 |
| `error: #if with no expression` | `#if SMOKE_PWM_T3C` 展开成裸 `#if` |
| `error 141: two or more data types in declaration` | 空宏名被当成了变量声明 |

写 `#define XXX 0` 或 `#define XXX 1`。

## 5. 不能用"空宏"来关闭引脚/PWM 定义

```c
#define PIN_HEAT1_CTL            /* ✗ 通道关闭时留空 */
PIN_HEAT1_CTL = 0;              /* 展开成 " = 0;" 语法错误 */
```

正确做法：通道关闭时让宏**指向一个哑元变量**，应用层写法一个字都不用改：

```c
// xxx.h
extern u8 xxx_dummy_pin;
// xxx.c
u8 xxx_dummy_pin;
// config.h
#define PIN_HEAT1_CTL xxx_dummy_pin   // 通道关闭,语句自动失效
```

## 6. 工具链的「既有的、无害的」输出

出现这些不用查：

| 输出 | 说明 |
|---|---|
| `<主文件>.asm:NNN: Error: <o> .org in REL area` | 命令行没带 `--code-loc`/链接脚本，**只在命令行出现**，IDE 编译没有 |
| `warning: multi-line comment` | 见 §3.3，注释掉的旧宏（`//` 行尾带 `\` 造成的） |
| 其它 .c 文件报 `error 74: function 'main' undefined` | 单文件编译的正常现象（那些文件不含 main） |
| `mc32_genMinus: WARNING: left operand too short for result` | `SinoDIV()` 把 u16 减法扩展到 uint32_t 参数，需要时显式 `(u32)` 转换 |

**浮点陷阱**：`CONSTANT_VOLTAGE_x` 这类常量宏如果写成浮点（`3.3*512*200`），
在 8 位 MCU 上会把浮点库拖进每一个 `SinoDIV` 调用点。用整数形式：`(33uL*512*TXCNT_MAX/10)`。

## 7. 工程结构与版本控制

- Sino IDE 工程通常由 `main.c` + 若干 `.c/.h` + `<工程>.Proj`（文件清单）组成；
  **新增头文件要在 `.Proj` 里登记一行**，否则 IDE 里看不到
- 头文件分工建议：`config.h` 参数/开关 → `define.h` 位标志与宏 → 外设头 →
  对外 API 头；公共头 `#include` 聚合，`.c` 只包一个总头
- **改之前一定自己备份**：这类工程常常不在版本控制下（SVN 里查不到节点），没有 pristine 可回滚
- 编译产物目录（`Debug/`、`Output/`、`System/`）在工程内，**命令行编译请复制到 `/tmp`**，
  别污染工程
- 从符号链接路径启动编辑器/agent，会话目录可能被固化成链接路径；建议 `cd` 到真实路径再启动

## 8. 踩坑后怎么回写（别只留在对话里）

改完固件、排掉一个坑之后，按**适用范围**决定写哪：

| 坑的性质 | 写到哪里 |
|---|---|
| 编码/工具类（GBK、CRLF、grep -a、行号索引） | 本文件 §1 |
| 宏/续行/开关宏/空宏 | 本文件 §3–§5 |
| 编译、验证、asm diff | 本文件 §2 |
| 具体报错信息 → 根因 | `references/common-errors.md`（按 A~H 分类追加） |
| 只对 PXS 系列成立（业务逻辑、引脚、架构） | `references/example-pxs-project.md` |
| 纯硬件电气 / 板级参数 / 现场经验 | 项目级开发日记（见 example 第 5 节） |

两条纪律：

- **同一现象第二次出现**才值得写进 skill；只遇到一次的先记日记，别急着抽象成规则
- 写完**回读一遍 diff 再宣布完成** —— 别只信编辑器返回的成功信息；
  中文内容必须确认是 GBK 写入（`grep -ac $'\xef\xbf\xbd'` 为 0），Markdown 文件则保持 UTF-8

## 9. 参考文件

- `references/build-and-verify.md` —— 编译验证流程、报错定位、双配置验证、**asm 指令流 diff**
- `references/safe-editing-gbk.md` —— GBK 安全改写与损坏恢复、grep `-a`、行号索引陷阱
- `references/common-errors.md` —— 报错 → 根因 → 改法 对照表（A~H 八类）
- `references/example-pxs-project.md` —— **实例**：PXS-FS12 / PXS-FD07 的代码架构（状态机、
  事件位、休眠、MITOU/USB 优先级）、PWM 通道与引脚对应、项目特有告警、开发日记索引
- `scripts/gbk_edit.py` —— 字节级安全查找替换脚本（`--check` / `--dry-run`）
