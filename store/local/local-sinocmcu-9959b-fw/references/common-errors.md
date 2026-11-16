# 常见报错 → 原因 → 改法

> 命令里的 `$PROJ` = 工程目录，`$SDK_INC` = SDK 头文件目录（含 `mc32-common.h` / `MC9959B.h`），按本机实际填。示例中的 `main.c` 代表工程主源文件名。

按报错信息查。绝大多数是"宏/续行/开关宏"三类问题。

---

## A. 续行与宏（占历史报错的绝大多数）

| 报错 | 根因 | 改法 |
|---|---|---|
| `main.c:212: syntax error: token -> 'if' ; column 3` | `#define X() do {` 行末**漏了 `\`**，宏体在第一个换行处结束，后续代码掉到文件作用域。报错行号指向宏体内那行，**极具误导性** | `#define X()\tdo { \` |
| `表达式必须含有常量值` / 第二行语句变成游离语句 | 行尾 `\` 后面跟了注释：`...\//电量数码管两位COM数据`，`\` 被注释吞掉，续行失效 | 续行符放真正的行尾，注释单独一行放到宏外面 |
| `expression must be a constant` 出现在 `Codedisplay[...]` 附近 | 同上，某行宏提前结束，后半段跑到了错误的作用域 | 检查那个多行宏的每一行是否都以 ` \` 结尾 |
| `warning: multi-line comment`（`user.h:166`、`Global.h:75`） | 注释掉的旧宏，每行 `//` 结尾还带 `\`，拼成多行注释 | 把注释掉的宏整块删掉，或改成 `/* */`，或去掉行尾 `\` |
| 宏体里少执行了后半段语句，无任何报错 | 宏体里有 `//` 注释，把后续语句全吞进注释了 | 宏体内一律用 `/* */` |

**判断续行是否真的生效**：不要用 `sdcc -E | grep 关键字`。
写个最小复现（两个全局量 + 宏），用**真实编译**看有没有语法错误：

```c
unsigned char g1, g2, g3;
#define F() g1 = 1;\
 g2 = 2; \
 g3 = 3;
void main(void){ F(); }
```
没有 error 才算续行生效。

---

## B. 开关宏（`#if` 相关）

| 报错 | 根因 | 改法 |
|---|---|---|
| `error: operator '\|\|' has no right operand` | 开关宏定义成**空**，展开成 `#if 0 \|\| 1 \|\|` | `#define SMOKE_PWM_T3C 1` |
| `error: #if with no expression` | 同上，`#if SMOKE_PWM_T3C` 展开成裸 `#if` | 同上 |
| `error 141: two or more data types in declaration` | 空宏名被当成变量声明（`main.c:117`） | 同上 |

---

## C. 引脚 / PWM 宏

| 报错或现象 | 根因 | 改法 |
|---|---|---|
| `PIN_HEAT1_CTL = 0;` 报语法错误 | 为了"关闭通道"把宏定义留空了 | 指向哑元变量 `smoke_dummy_pin`（`smoke.h` extern + `smoke.c` 定义） |
| 加热初始化"没生效" | `config.h` 注释标 PWM3B，`smoke.h` 的 `T_SMOKE` 却是 `T3A` | 核对 `PIN_HEATx_CTL` 注释与 `SMOKE_PWM_T3A/B/C` 开关 |
| `PWM3BEN` / `PWM3B1E` 未定义 | 新启用的通道寄存器在 `MC9959B.h` 里没有 | 补头文件定义，或不要启用该通道 |
| 某通道怎么关不掉 | `SetPwm()` / `smoke_act_stop()` 里只有 T2/T3A/T3C 分支，缺 T3B | 补上对应分支 |

---

## D. 声明与隐式声明

| 报错 | 根因 | 改法 |
|---|---|---|
| `warning 112: function 'lcd_oil' implicit declaration` | 函数在用之前没有可见声明 | 在对应 `.h` 里加 `void lcd_oil(void);`（或用到的 `.c` 里补前向声明） |
| `error 74: function 'main' undefined` | 单文件编译一个不含 `main` 的 `.c` | 正常现象，不是错误 |
| `case MODE_X:` 后面直接跟变量声明 → `syntax error` | C51 遵循 **C89**，声明必须在代码块 `{ }` 最前面，而 `case` 标签**不创建代码块** | 声明提到 `switch` 之前，或给该 `case` 单独加一层 `{ }` |
| 文件作用域 `u8 flag = 1;` 上电后是 0 | 本工具链启动代码**只清 `.bss`，不做 `.data` 段 ROM→RAM 拷贝** | 需要非零初值的全局变量，在 `main()` 的 `while(1)` **之前显式赋值**；文件作用域的初始化器只当文档 |

---

## E. 位宽与浮点

| 报错 | 根因 | 改法 |
|---|---|---|
| `mc32_genMinus: WARNING: left operand too short for result` | `SinoDIV(CONST, u16_a - u16_b)` 的减法被扩展到 `uint32_t` 参数 | `(u32)a - b` 显式转换，或忽略（无功能影响） |
| 固件体积莫名变大 | `CONSTANT_VOLTAGE_x` 写成浮点（`3.3*512*200`），每个 `SinoDIV` 调用点都拖进浮点库 | 改整数式 `(33uL*512*TXCNT_MAX/10)` |
| `warning 158: overflow in implicit constant conversion` | 常量赋给了更窄的类型 | 既有，加后缀或显式截断 |

---

## F. 工具链层面

| 现象 | 说明 |
|---|---|
| `main.asm:NNN: Error: <o> .org in REL area` | 命令行没带 `--code-loc` / 链接脚本。只在命令行出现，**IDE 编译没有**，可忽略 |
| `internal error: sprintf truncated.`（SINO IDE，无行号） | 函数内部静态变量过多 / 位宽太宽。把静态变量提到文件作用域，或换窄类型 |
| 打断点看着成功了但程序不停 | IDE 看起来能打无限个断点，**实际数量有限**，超出的断点完全无效且无任何提示。打新断点前先全清 |
| `#include "config.h"` 之类的头找不到 | 命令行要加 `-I$SDK_INC`；IDE 已配好 |
| IntelliSense 报的东西和实际编译不一致 | `.vscode/c_cpp_properties.json` 里的 `defines` 是模拟 SDCC 关键字用的，与真实编译有偏差；以真实编译为准 |

---

## H. 低功耗与唤醒（不是编译错误，是"功能不生效"类问题）

| 现象 | 根因 | 改法 |
|---|---|---|
| 休眠后定时器不唤醒 / 唤醒间隔不对 | 定时器时钟源选了 `Fcpu`，CPU 一停就没了 | 时钟源改 `FTMR` / `FLOSC` / `FPFRC` |
| 进入 `HOLD1/2` 后待机电流 ~1.2 mA | 处理完事件没立刻 `stop()` | 立刻 `stop()`；处理时间/唤醒间隔越小功耗越低 |
| `stop()` 了定时器还在跑 | 直接 `stop()` 停不掉 | 先 `HFEN` / `LFEN` 置 0，**再** `stop()` |
| 判不出本次是不是 WDT 唤醒 | — | 读 `TO` 标志（`TO == 1` 表示 WDT 溢出） |
| 进休眠的判据散在调用点，越改越乱 | 判据和动作分家 | 把超时判断收进休眠函数本身（本工程 `MCU_SLEEP()` 内部判 `SLEEP_IDLE_TIME_1MS`，调用点直接调） |

---

## G. 编码（最隐蔽的一类）

| 现象 | 根因 | 改法 |
|---|---|---|
| 某些文件突然变 UTF-8、中文注释变 `????` | 被按 UTF-8 读写的编辑工具整文件重写过，GBK 字节被替换成 `EF BF BD` | 见 `safe-editing-gbk.md`（含从旧版本逐行还原的算法） |
| IntelliSense 报 `声明与 "int XXX()" 不兼容`，但全工程找不到该声明 | 预处理已经崩了（通常是续行失效），后面的声明对不上号 | **别追这个连带报错**，去找第一个真实语法错误 |