# 编译验证与报错定位

> 命令里的 `$PROJ` = 工程目录，`$SDK_INC` = SDK 头文件目录（含 `mc32-common.h` / `MC9959B.h`），按本机实际填。示例中的 `main.c` 代表工程主源文件名。

## 标准验证流程

```bash
SRC=$PROJ
INC=$SDK_INC

rm -rf /tmp/b && mkdir /tmp/b && cd /tmp/b
cp "$SRC"/*.c "$SRC"/*.h .
sdcc -mmcs51 --model-small --std-c99 -I. -I"$INC" main.c
```

复制到 `/tmp` 编译，不要在工程目录里编——SDCC 会生成 `.asm` / `.rel` / `.lst` / `.mem` / `.sym` / `.ihx`，
会污染 SVN 工作副本。

## 有 `#if` 配置开关时，两边都要验

```bash
for MODE in MITOU USB; do
  cp "$SRC"/main.c . && cp "$SRC"/config.h .
  python3 -c "
p='config.h'; d=open(p,'rb').read()
open(p,'wb').write(d.replace(b'#define EVT_PRIORITY EVT_PRIORITY_MITOU',
                            b'#define EVT_PRIORITY EVT_PRIORITY_$MODE'))"
  echo \"--- $MODE ---\"
  sdcc -mmcs51 --model-small --std-c99 -I. -I"$INC" main.c 2>&1 | grep -i error
done
```

## 怎么把噪音过滤掉

```bash
sdcc ... 2>&1 | grep -viE "multi-line comment|^ +[0-9]+ \||^ +\||In file included|from |^ *$|\.org in REL|^removing "
```

## 判断"有没有真错误"只看 error

**唯一可信的判据是编译器输出里的 `error`。**

不要这样判断（我踩过的坑）：

```bash
sdcc -E foo.c | grep -q HandleSmoke   # ✗ 不能用
```

`sdcc -E` 的输出里，宏体即使**续行失败泄漏成了文件作用域的普通文本**，关键字照样能搜到，
会得出"续行没问题"的完全相反的结论。写一个故意有语法错误的最小复现用例，
用**真实编译**（不是 `-E`）确认判据本身可靠，再去测别的。

## 定位一个报错的正确顺序

1. 先确认是**自己这次改动引入的**还是既有问题：
   拿一个没改过的版本（比如 `$PROJ_ALT/main.c`）用同样命令编一遍对比。
   `.org in REL area` 就是这样被确认成"命令行缺 `--code-loc`"的既有问题。
2. 看报错行号**在 `#if` 选中的分支里**，还是被排除的分支里。
3. 宏相关报错：在文件里 grep `0x5C`，确认每个宏体行（除末行）都以 `\ ` 结尾、
   且 `#define` 行也以 `\ ` 结尾。
4. 报错"声明与 X 不兼容"但全工程找不到 X → 多半是预处理已经崩了，
   导致后面的声明对不上号。去查第一个真实语法错误，别追这个连带报错。

## asm 行数用来对比代码体积

```bash
wc -l main.asm
```

改前改后比一下，确认没有代码膨胀（本工程参考值：原始 1365 行，宏版 1336/1348 行）。
注意这个数只有在**只有 main.c + 头文件**在目录里时才可比。

## 重构类改动：用指令流 diff 证明行为没变

只挪位置、不改逻辑的改动（搬代码进宏、合并函数、拆/并头文件），
"编译通过"证明不了行为没变。把改动前后各编一份 `.asm`，归一化后逐行 diff：

```bash
INC=$SDK_INC
sdcc -mmcs51 --model-small --std-c99 -I. -I"$INC" -S main.c     # -S 才会留下 .asm

norm() { grep -avE "^;|^$" "$1" | sed -E 's/[0-9]{4,5}\$/LBL/; s/_10000_[0-9]+/_10000_UID/g'; }
norm before.asm > before.code
norm after.asm  > after.code
diff before.code after.code
```

`norm` 做的事：去掉注释和空行；把跳转标签 `00133$` 归一成 `LBL`；把静态变量的 SDCC 符号后缀
`_10000_106` 归一成 `_UID`（这个后缀是编译单元内的唯一号，会因为改动而平移，与行为无关）。

**判读**

| diff 结果 | 结论 |
|---|---|
| 只剩 `ljmp`→`sjmp`、标签号平移 | 块布局变了，行为不变，可接受 |
| 某段判断消失、同位置多出 `lcall _xxx` | 代码换成了函数调用 —— 确认这就是本次预期的那一处改动 |
| 大量基本块**顺序变了** | 两边配置宏不一致（例如 `EVT_PRIORITY` 取值不同）→ 先对齐配置再 diff |
| 有 `mov a,#0xa0 / subb / #0x0f` 这类常量对 | 常量宏确实传进去了，用十进制对一下（`0x0FA0 = 4000`） |

已用它验证过：宏封装（`led_charge_full`）、函数合并（`MCU_SLEEP`）、头文件拆分（`led.h`），
三次都能证明指令流等价。