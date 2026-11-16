# 3 CPU 与存储器

> 源：MC9959B 用户手册 V1.0.1（p.14–22）· 页码为 PDF 页序

<!-- p.14 -->

3   CPU     与存储器

    3.1      指令集

    芯片的指令集为精简指令集。
    除程序跳转类指令外，其他指令均为单周期指令，即执行时间为                                1 个指令周期（CPU        时钟周期）；所有指令均为单字
指令，即指令码仅占用           1 个程序存储器地址空间。

指令汇总表

  助记符                           说明                                      操作                   周期    长度     标志

ADDAR    R  R 和 A 相加，结果存入       A                        R+A→A                                1      1   C,DC,Z

ADDRA    R  R 和 A 相加，结果存入       R                        R+A→R                                1      1   C,DC,Z

ADCAR    R  R 和 A 相加（带    C 标志），结果存入      A              R+A+C→A                              1      1   C,DC,Z

ADCRA    R  R 和 A 相加（带    C 标志），结果存入      R              R+A+C→R                              1      1   C,DC,Z

RSUBAR R    R 和 A 相减，结果存入       A                        R-A→A                                1      1   C,DC,Z

RSUBRA R    R 和 A 相减，结果存入       R                        R-A→R                                1      1   C,DC,Z

RSBCAR R    R 和 A 相减（带    C 标志），结果存入      A              R-A-/C→A                             1      1   C,DC,Z

RSBCRA R    R 和 A 相减（带    C 标志），结果存入      R              R-A-/C→R                             1      1   C,DC,Z

ASUBAR R    A 和 R 相减，结果存入       A                        A-R→A                                1      1   C,DC,Z

ASUBRA R    A 和 R 相减，结果存入       R                        A-R→R                                1      1   C,DC,Z

ASBCAR R    A 和 R 相减（带    C 标志），结果存入      A              A-R-/C→A                             1      1   C,DC,Z

ASBCRA R    A 和 R 相减（带    C 标志），结果存入      R              A-R-/C→R                             1      1   C,DC,Z

ANDAR    R  R 和 A 与操作，结果存入        A                      R and A→A                            1      1     Z

ANDRA    R  R 和 A 与操作，结果存入        R                      R and A→R                            1      1     Z

ORAR      R R 和 A 或操作，结果存入        A                      R or A→A                             1      1     Z

ORRA      R R 和 A 或操作，结果存入        R                      R or A→R                             1      1     Z

XORAR    R  R 和 A 异或操作，结果存入         A                    R xor A→A                            1      1     Z

XORRA    R  R 和 A 异或操作，结果存入         R                    R xor A→R                            1      1     Z

COMAR    R  对  R取反，结果存入       A                          R 取反→A                               1      1     Z

COMR      R 对  R取反，结果存入       R                          R 取反→R                               1      1     Z

RLA         A 循环左移（带      C标志）                           A[7]→C；A[6:0]→A[7:1]；C→A[0]          1      1     C

RLAR      R R 循环左移（带      C 标志），结果存入      A              R[7]→C；R[6:0]→A[7:1]；C→A[0]          1      1     C

RLR        R R循环左移（带      C 标志），结果存入      R              R[7]→C；R[6:0]→R[7:1]；C→R[0]          1      1     C

RRA         A 循环右移（带      C标志）                           A[0]→C；A[7:1]→A[6:0]；C→A[7]          1      1     C

RRAR      R R 循环右移（带      C 标志），结果存入      A              R[0]→C；R[7:1]→A[6:0]；C→A[7]          1      1     C

RRR        R R循环右移（带      C 标志），结果存入      R              R[0]→C；R[7:1]→R[6:0]；C→R[7]          1      1     C

SWAPAR R    交换   R的高低半字节，结果存入           A                R[7:4]→A[3:0]；R[3:0]→A[7:4]          1      1      -

<!-- p.15 -->

SWAPR    R   交换   R 的高低半字节，结果存入            R                   R[7:4]→R[3:0]；R[3:0]→R[7:4]             1      1       -

MOVRA    R   将  A 存入   R                                       A→R                                     1      1       -

MOVAR    R   将  R 存入   A                                       R→A                                     1      1      Z

MOVR      R  将  R 存入   R                                       R→R                                     1      1      Z

CLRA         将  A 清零                                           0→A                                     1      1      Z

CLRR      R  将  R清零                                            0→R                                     1      1      Z

INCA         A 自加   1                                          A+1→A                                   1      1       -

INCR      R  R 自加   1                                          R+1→R                                   1      1      Z

INCAR    R   R 加  1，结果存入      A                                R+1→A                                   1      1      Z

DECA         A 自减   1                                          A-1→A                                   1      1       -

DECR      R  R 自减   1                                          R-1→R                                   1      1      Z

DECAR    R   R 减  1，结果存入      A                                R-1→A                                   1      1      Z

JZA          A 自加   1：结果为     0 则跳过下一条指令                       A+1→A：结果为      0 则  PC+2→PC            1/2     1       -

JZR        R R 自加   1：结果为     0 则跳过下一条指令                       R+1→R：结果为      0 则  PC+2→PC            1/2     1       -

JZAR      R  R 加1，结果存入        A：结果为     0 则跳过下一条指令             R+1→A：结果为      0 则PC+2→PC              1/2     1       -

DJZA         A 自减   1：结果为     0 则跳过下一条指令                       A-1→A：结果为      0 则 PC+2→PC             1/2     1       -

DJZR      R  R 自减   1：结果为     0 则跳过下一条指令                       R-1→R：结果为      0 则 PC+2→PC             1/2     1       -

DJZAR    R   R 减1，结果存入        A：结果为     0 则跳过下一条指令             R-1→A：结果为      0 则 PC+2→PC             1/2     1       -

BCLR      R,b 将 R的第b    位清   0                                 0→R[b]                                  1      1       -

BSET      R,b 将 R的第b    位置   1                                 1→R[b]                                  1      1       -

JBCLR    R,b 若  R的第b    位为   0，则跳过下一条指令                        若 R[b]=0，则   PC+2→PC                   1/2     1       -

JBSET    R,b 若  R的第b    位为   1，则跳过下一条指令                        若 R[b]=1，则   PC+2→PC                   1/2     1       -

ADDAI    I   I 和 A 相加，结果存入        A                            I+A→A                                   1      1    C,DC,Z

ADCAI    I   I 和 A 相加（带     C 标志），结果存入        A                I+A+C→A                                 1      1    C,DC,Z

ISUBAI I     I 和 A 相减，结果存入        A                            I-A→A                                   1      1    C,DC,Z

ISBCAI I     I 和 A 相减（带     C 标志），结果存入        A                I-A-/C→A                                1      1    C,DC,Z

ASUBAI I     A 和  I相减，结果存入        A                            A-I→A                                   1      1    C,DC,Z

ASBCAI I     A 和  I相减（带     C 标志），结果存入        A                A-I-/C→A                                1      1    C,DC,Z

ANDAI    I   I 和 A 与操作，结果存入         A                          I and A→A                               1      1      Z

ORAI      I  I 和 A 或操作，结果存入         A                          I or A→A                                1      1      Z

XORAI    I   I 和 A 异或操作，结果存入          A                        I xor A→A                               1      1      Z

MOVAI    I   将  I存入   A                                        I→A                                     1      1       -

CALL      K  子程序调用                                             PC+1→TOS；K→PC[12:0]                     2      1       -

GOTO      K  无条件跳转                                             K→PC[12:0]                              2      1       -

RETURN       从子程序返回                                            TOS→PC                                  2      1       -

<!-- p.16 -->

RETAI    I 从子程序返回，并将     I存入  A                 TOS→PC；I→A                     2     1     -

RETIE     从中断返回                                 TOS→PC；1→GIE                   2     1     -

NOP       空操作                                   空操作                            1     1     -

DAA       BCD 码加法操作后，将     A的值调整为    BCD码       A(HEX码)→A(BCD 码)               1     1    C

DSA       BCD 码减法操作后，将     A的值调整为    BCD码       A(HEX码)→A(BCD 码)               1     1     -

CLRWDT    将看门狗计数器清零                             0→WDTCNT                       1     1   TO,PD

STOP      进入低功耗模式                               0→WDTCNT；CPU  暂停               1     1   TO,PD

   注：

   1、  A-算术逻辑单元累加器       ALU，R-数据存储器，I-立即数，K-程序存储器地址，TOS-堆栈栈顶；
   2、  对于条件跳转类指令，若跳转条件成立，则执行时间需                   2 个指令周期，否则仅需        1 个指令周期；
   3、  禁止采用对    C,DC,Z标志有影响的指令访问寄存器           PFLAG；

   3.2     程序存储器

   芯片的程序存储器为        FLASH 型存储器，4K×16     位的地址空间范围为       0000H~0FFFH。程序存储器地址分配如下图所
示：

   程序存储器支持间接寻址，可通过寄存器               INDF3 访问地址为（FSR1×256+FSR0）的程序存储器内容，高               8 位将缓
存于寄存器    HIBYTE，低  8 位将缓存于寄存器      A。
   例如，采用间接寻址读取程序存储器             0155H 地址中内容，高      8位存入通用数据存储器         11H地址中，低     8位存入通用

数据存储器    10H 地址中：
            MOVAI        01H
            MOVRA        FSR1        ；将  01H 写入  FSR1

            MOVAI        55H
            MOVRA        FSR0        ；将  55H 写入  FSR0
            MOVAR        INDF3            ；读取（FSR1×256+FSR0）所指地址的程序存储器中内容
                                          ；高  8位缓存于    HIBYTE，低  8位缓存于    A

            MOVRA        10H              ；将  A中缓存的低     8位存入通用数据存储器        10H 地址中
            MOVAR        HIBYTE           ；读取  HIBYTE 中缓存的高    8 位
            MOVRA        11H              ；高  8位存入通用数据存储器        11H 地址中

<!-- p.17 -->

   3.3      数据存储器

   芯片的数据存储器包括通用数据存储器                 GPR（256   字节）和特殊功能寄存器           SFR，地址映射如下表所示。其中              GPR
可直接寻址或通过        INDF0/INDF2 间接寻址，SFR      可直接寻址或通过        INDF1/INDF2 间接寻址。

   数据存储器还包括掉电非易失的               EEPROM  型数据存储器（256        字节），需通过      SFR 进行读写操作，详细说明请参见
后续章节。

### 数据存储器区地址映射表（p.17）

| 地址 | 类型 | +0 | +1 | +2 | +3 | +4 | +5 | +6 | +7 |
|---|---|---|---|---|---|---|---|---|---|
| 000H–0FFH | GPR | 通用数据存储器区（256 字节） | | | | | | | |
| 100H–17FH | 保留 | | | | | | | | |
| 180H | SFR | INDF0 | INDF1 | INDF2 | HIBYTE | FSR0 | FSR1 | PCL | PFLAG |
| 188H | SFR | MCR | INDF3 | INTE0 | INTF0 | OSCMR | — | INTE1 | INTF1 |
| 190H | SFR | IOP0 | OEP0 | PUP0 | PDP0 | IOP1 | OEP1 | PUP1 | PDP1 |
| 198H | SFR | IOP2 | OEP2 | PUP2 | PDP2 | P1KBCR | — | — | — |
| 1A0H | SFR | T0CR | T0CNT | T0LOAD | — | LVDCR | CMPCR0 | CMPCR1 | CMPCLR |
| 1A8H | SFR | T1CR0 | T1CR1 | T1CNTH | T1CNTL | T1LOADH | T1LOADL | P0KBCR | P2KBCR |
| 1B0H | SFR | T2CR | T2CNT | T2LOAD | T2DATA | PWM2CR0 | — | — | AFCR |
| 1B8H | SFR | T3CR | T3CNT | T3LOAD | T3DATA | T3DATB | T3DATC | PWM3CR0 | PWM3CR1 |
| 1C0H | SFR | — | — | — | — | EECR | EEPR | EEAR | EEDR |
| 1C8H | SFR | ADCR0 | ADCR1 | ADRH | ADRL | OSADJCR | P0ADCR | P1ADCR | P2ADCR |
| 1D0H–1F7H | 保留 | | | | | | | | |
| 1F8H | SFR | — | — | — | — | — | — | DBGCR | DBGPR |

> 注：灰色部分为系统寄存器及保留区，未定义地址禁止读写。
> **与 MC9959 的差异**：无 `HIRCCAL`、无 `OPACR0/1/CLR`、无 `PWM2CR1/2`、无 `PWM3CR2/3/4`；
> 新增 `P0KBCR`、`P2KBCR`（全端口键盘中断）、`AFCR`（ADC 增益 / CMP 负端分压）、`DBGCR`、`DBGPR`（带电烧录切换）。

数据存储器寻址方式地址组成

     15   14  13   12   11  10   9    8    7   6    5   4    3    2   1    0        寻址方式

      /    /   /    /   /    /    /             取自指令的     9 位地址                   直接寻址方式

      /    /   /    /   /    /    /   0                  FSR0                    间接寻址方式      0

      /    /   /    /   /    /    /   1                  FSR1                    间接寻址方式      1

                    FSR1                                 FSR0                    间接寻址方式      2

   直接寻址方式，是以指令的低             9 位为数据存储器地址，通过指令访问，寻址范围                     0~1FFH。例如，采用直接寻址方式
将数据   55H 写入数据存储器       010H 地址中：
             MOVAI         55H

             MOVRA         10H               ；将   55H 写入数据存储器       10H 地址中

<!-- p.18 -->

   间接寻址方式      0，是以  FSR0 为数据存储器地址指针，通过           INDF0 访问，寻址范围      0~0FFH。例如，采用间接寻址方
式 0将数据   55H 写入数据存储器      010H 地址中：

            MOVAI        10H
            MOVRA        FSR0
            MOVAI        55H
            MOVRA        INDF0            ；将  55H 写入  FSR0 所指地址的数据存储器中

   间接寻址方式      1，是以  FSR1 为数据存储器地址指针，通过           INDF1 访问，寻址范围      100H~1FFH。例如，采用间接寻
址方式  1 将数据   55H 写入数据存储器      110H地址中：

            MOVAI        10H
            MOVRA        FSR1
            MOVAI        55H

            MOVRA        INDF1            ；将  55H 写入(FSR1+256)所指地址的数据存储器中

   间接寻址方式      2，是以[FSR1:FSR0]为数据存储器地址指针，通过            INDF2访问，寻址范围      0~FFFFH。例如，采用间接

寻址方式   2 将数据   55H写入数据存储器       0010H地址中：
            MOVAI        00H
            MOVRA        FSR1

            MOVAI        10H
            MOVRA        FSR0
            MOVAI        55H

            MOVRA        INDF2            ；将  55H 写入(FSR1×256+FSR0)所指地址的数据存储器中

   注：间接寻址方式       2 最大可寻址     FFFFH，但访问数据存储器中未定义的地址时，读出数据不确定，写入操作可能会
       更改其他地址中的内容。

   3.4     堆栈

   芯片的堆栈为      8级深度的硬件堆栈。当         CPU 响应中断或执行子程序调用指令时，会自动将下一条指令的                      PC 值压栈
保存；当   CPU 执行中断返回或子程序返回指令时，会自动将栈顶内容出栈载入                        PC。

   3.5     控制寄存器

数据指针寄存器      0

             Bit[7]     Bit[6]    Bit[5]     Bit[4]     Bit[3]    Bit[2]     Bit[1]    Bit[0]

   FSR0      FSR07     FSR06      FSR05      FSR04     FSR03      FSR02     FSR01      FSR00

   R/W        R/W       R/W        R/W       R/W        R/W        R/W       R/W        R/W

  初始值          X         X          X          X         X          X          X         X
BIT[7:0]    FSR0[7:0] – 数据指针寄存器     0

          FSR0：间接寻址方式       0的指针，或间接寻址方式          2、3 的指针低    8位。

<!-- p.19 -->

数据指针寄存器        1

                Bit[7]       Bit[6]       Bit[5]      Bit[4]       Bit[3]       Bit[2]       Bit[1]       Bit[0]

   FSR1         FSR17       FSR16        FSR15        FSR14        FSR13        FSR12        FSR11       FSR10

    R/W          R/W         R/W          R/W          R/W          R/W          R/W          R/W         R/W

   初始值            X            X            X            X           X            X            X            X

BIT[7:0]       FSR1[7:0] – 数据指针寄存器         1
             FSR1：间接寻址方式          1的指针，或间接寻址方式              2、3  的指针高      8位。

间接寻址寄存器        0

                Bit[7]       Bit[6]       Bit[5]      Bit[4]       Bit[3]       Bit[2]       Bit[1]       Bit[0]

   INDF0       INDF07       INDF06       INDF05      INDF04       INDF03       INDF02       INDF01       INDF00

    R/W          R/W         R/W          R/W          R/W          R/W          R/W          R/W         R/W

   初始值            X            X            X            X           X            X            X            X

BIT[7:0]       INDF0[7:0] – 间接寻址寄存器         0
             INDF0：INDF0   不是物理寄存器，对           INDF0  操作实际是对        FSR0 所指向地址的数据存储器进行操作，从而实

             现间接寻址功能。

间接寻址寄存器        1

                Bit[7]       Bit[6]       Bit[5]      Bit[4]       Bit[3]       Bit[2]       Bit[1]       Bit[0]

   INDF1       INDF17       INDF16       INDF15      INDF14       INDF13       INDF12       INDF11       INDF10

    R/W          R/W         R/W          R/W          R/W          R/W          R/W          R/W         R/W

   初始值            X            X            X            X           X            X            X            X

BIT[7:0]       INDF1[7:0] – 间接寻址寄存器         1

             INDF1：INDF1   不是物理寄存器，对           INDF1  操作实际是对（FSR1+256）所指向地址的数据存储器进行操作，
             从而实现间接寻址功能。

间接寻址寄存器        2

                Bit[7]       Bit[6]       Bit[5]      Bit[4]       Bit[3]       Bit[2]       Bit[1]       Bit[0]

   INDF2       INDF27       INDF26       INDF25      INDF24       INDF23       INDF22       INDF21       INDF20

    R/W          R/W         R/W          R/W          R/W          R/W          R/W          R/W         R/W

   初始值            X            X            X            X           X            X            X            X

BIT[7:0]       INDF2[7:0] – 间接寻址寄存器         2

             INDF2：INDF2   不是物理寄存器，对            INDF2 操作实际是对（FSR1×256+FSR0）所指向地址的数据存储器进
             行操作，从而实现间接寻址功能。

<!-- p.20 -->

间接寻址寄存器           3

                  Bit[7]         Bit[6]        Bit[5]         Bit[4]        Bit[3]         Bit[2]        Bit[1]         Bit[0]

   INDF3         INDF37         INDF36        INDF35         INDF34        INDF33         INDF32        INDF31         INDF30

    R/W            R/W           R/W            R/W           R/W            R/W           R/W            R/W           R/W

   初始值               X             X              X             X              X             X              X             X

BIT[7:0]         INDF3[7:0] –   间接寻址寄存器           3
              INDF3：INDF3      不是物理寄存器，对              INDF3   操作实际是对（FSR1×256+FSR0）所指向地址的程序存储器进

              行操作，从而实现间接寻址功能。

    注：对寄存器          INDF3   仅可执行读取操作，且仅可使用读取指令（                            MOVAR  INDF3    ），所读程序存储器内容的高                   8 位存
         入寄存器       HIBYTE  ，低    8 位存入寄存器         A。

字操作高字节缓存器

                  Bit[7]         Bit[6]        Bit[5]         Bit[4]        Bit[3]         Bit[2]        Bit[1]         Bit[0]

   HIBYTE       HIBYTE7        HIBYTE6       HIBYTE5        HIBYTE4       HIBYTE3        HIBYTE2        HIBYTE1       HIBYTE0

    R/W            R/W           R/W            R/W           R/W            R/W           R/W            R/W           R/W

   初始值               X             X              X             X              X             X              X             X

BIT[7:0]         HIBYTE[7:0]   – 字操作高字节缓存器
              HIBYTE   ：用于缓存通过           INDF3  访问程序存储器时所读取内容的高                       8 位。

程序指针计数器低字节

                  Bit[7]         Bit[6]        Bit[5]         Bit[4]        Bit[3]         Bit[2]        Bit[1]         Bit[0]

    PCL            PC7           PC6            PC5            PC4           PC3            PC2           PC1            PC0

    R/W            R/W           R/W            R/W           R/W            R/W           R/W            R/W           R/W

   初始值               0             0              0             0              0             0              0             0

BIT[7:0]         PC[7:0]  – 程序指针计数器低             8 位
    程序指针计数器（            PC）有以下几种操作模式：
             顺序运行指令：PC = PC + 1；
             程序跳转指令          GOTO/CALL：PC =        指令码低       13 位；

             返回指令       RETIE/RETURN/RETAI：PC =           堆栈栈顶（TOS）；
    对   PCL  操作指令：
             对   PCL  操作的加法指令：            PC = (PC[12:0]+ALU[7:0])   ；

             对   PCL  操作的其他指令：            PC = (PC[12:8]:ALU[7:0](ALU     运算结果      ))；

CPU  状态寄存器

                  Bit[7]         Bit[6]        Bit[5]         Bit[4]        Bit[3]         Bit[2]        Bit[1]         Bit[0]

   PFLAG             -             -              -             -              -             Z             DC             C

<!-- p.21 -->

   R/W          -          -          -          -          -        R/W        R/W        R/W

  初始值           -          -          -          -          -         X          X          X

BIT[2]       Z – 零标志位
           0：  算术或逻辑运算的结果不为零；

           1：  算术或逻辑运算的结果为零；
BIT[1]       DC – 半字节进位/借位标志位
           0：  加法运算中半字节无进位；减法运算中半字节有借位；

           1：  加法运算中半字节有进位；减法运算中半字节无借位；
BIT[0]       C – 进位/借位标志位
           0：  加法运算中无进位；减法运算中有借位；移位操作中移出位为                        0；

           1：  加法运算中有进位；减法运算中无借位；移位操作中移出位为                        1；

杂项控制寄存器

              Bit[7]     Bit[6]     Bit[5]     Bit[4]     Bit[3]     Bit[2]     Bit[1]     Bit[0]

   MCR        GIE          -         TO         PD       INT1M1     INT1M0     INT0M1     INT0M0

   R/W        R/W          -         R          R         R/W        R/W        R/W        R/W

  初始值          0           -         0          0          0          0          0          0

BIT[7]       GIE – 中断总使能位

           0：  屏蔽所有中断；
           1：  由相应的中断使能位决定          CPU 是否响应中断源所触发的中断；
BIT[5]       TO – 看门狗溢出标志位
           0：  上电复位，或执行       CLRWDT/STOP  指令；

           1：  发生  WDT 溢出；
BIT[4]       PD – 进入低功耗模式标志位
           0：  上电复位，或执行       CLRWDT  指令；

           1：  执行  STOP 指令；
BIT[3:2]     INT1M[1:0] – 外部中断  INT1 触发方式选择位

                              INT1M[1:0]            INT1触发方式

                                  00                 上升沿触发

                                  01                 下降沿触发

                                  1X                电平变化触发

BIT[1:0]     INT0M[1:0] – 外部中断  INT0 触发方式选择位

                              INT0M[1:0]            INT0触发方式

                                  00                 上升沿触发

                                  01                 下降沿触发

                                  1X                电平变化触发

<!-- p.22 -->

## 3.6 用户配置字（p.22）

烧录时配置，上电/复位后载入寄存器，决定关键模块初始状态。

| 符号 | 功能 | 可选值 |
|---|---|---|
| FCPUS | 高频下 FCPU 分频 | FHOSC/4、/8、/16、/32、/64（**无 /2**） |
| RSTEN | RST 外部复位端口 | P17 为外部复位脚 / P17 为输入输出脚 |
| LVRMD | LVR 模式 | 始终开启 / 运行模式开启、低功耗关闭 |
| LVRVS | LVR 复位电压 | 1.8 / 2.0 / 2.4 / 2.7 / 3.0 / 3.2V（须满足 FCPU 对应工作电压） |
| WDTM | WDT 模式 | 始终关闭 / 运行开启、低功耗关闭 / 始终开启 |
| WDTT | WDT 溢出时间 | 16 / 64 / 256 / 1024 ms |
| **SMTVS** | 端口施密特阈值 | `2.0V / 0.8V` 或 `0.8VDD / 0.2VDD`（对应 2.2 节 Vih/Vil 的两档） |
| ENCR | 程序代码加密 | 加密 / 不加密 |
| DBGPIN0 | PCK0/PDT0 编程扩展 | 仅复位时作编程端口 / 可通过寄存器位切换编程或通用端口 |
| DBGPIN1 | PCK1/PDT1 编程扩展 | 同上 |

> **与 MC9959 的差异**：9959B **没有** `OSCM`（时钟模式选择）与 `HIRCFS`（高频选择，固定 32MHz）；
> 新增 `SMTVS`；`DBGPIN0/1` 的语义从"始终作编程端口"改为"可由 `DBGCR`/`DBGPR` 寄存器切换"。
