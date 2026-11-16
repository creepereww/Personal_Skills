# 10 低电压检测 LVD / 11 EEPROM 存储器

> 源：MC9959B 用户手册 V1.0.1（p.53–56）· 页码为 PDF 页序

> **阅读提示**：正文保留 PDF 版面布局。
> `LVDCR`（LVD 控制，**LVD 中断可唤醒**）；`EECR`、`EEPR`、`EEAR`、`EEDR`（EEPROM）。
> EEPROM 容量 **128 字节**、单地址写 **8ms**、擦写 **1 万次**（见 2.6）。

<!-- p.53 -->

10 低电压检测                        LVD

     芯片内置低电压检测模块                       LVD，可通过寄存器位                   LVDEN     开启，通过          LVDVS     选择电压检测阀值。当VDD                        电压降至电
压检测阀值以下时检测状态标志位                              LVDF    将被置      1，同时中断标志               LVDIF   置   1 触发     LVD   中断；因        LVD   电路的回滞特性（回
滞电压典型值为              6%），     VDD   电压需恢复至电压检测阀值                        +6%后      LVDF   才被清       0（但中断标志不会自动清                       0）。

     注：开启         LVD   或切换电压检测阀值等操作，需待电路稳定（时间＞                                             2ms   ）后     LVD   输出才有效。

LVD   控制寄存器

                      Bit[7]           Bit[6]           Bit[5]            Bit[4]           Bit[3]           Bit[2]            Bit[1]           Bit[0]

    LVDCR            LVDEN                -            LVDVS2           LVDVS1            LVDVS0                -                -              LVDF

     R/W               R/W                -              R/W               R/W              R/W                 -                -                R

    初始值                  0                -                0                 0                0                 -                -                X

BIT[7]              LVDEN     –  低电压检测           LVD  使能位
                 0 ：   关闭     LVD  ；

                 1 ：   开启     LVD  ；
BIT[5:3]            LVDVS[2:0]      – LVD   电压检测阀值选择位

                                                LVDVS[2:0]                      LVD  电压检测阀值

                                                     000                                 2.0V

                                                     001                                 2.2V

                                                     010                                 2.4V

                                                     011                                 2.6V

                                                     100                                 2.8V

                                                     101                                 3.2V

                                                     110                                 3.6V

                                                     111                                 4.0V

BIT[0]              LVDF – LVD      检测状态标志位
                 0：    VDD    电压高于电压检测阀值，或                        LVD   关闭；
                 1：    VDD    电压低于电压检测阀值；

<!-- p.54 -->

11 EEPROM       存储器

   11.1    EEPROM   概述

   芯片内置   128 字节的   EEPROM 型数据存储器，支持用户程序在带电运行中实时地读写数据。对                     EEPROM 中数据的
读写操作需通过控制寄存器         EECR、保护寄存器     EEPR、地址寄存器     EEAR和数据寄存器     EEDR 进行。

   写操作控制位     EEWRITE置  1将启动   EEPROM 写操作，EEDR    中的数据将被写入      EEAR指向的   EEPROM 地址中，完
成后 EEWRITE 自动清   0。为防止误触发     EEPROM 写操作，需先对      EEPR写  5AH再立即写    A5H，EEWRITE 才能置   1，中
间不能插入其他操作（包括         NOP 操作），否则    EEWRITE将无法置    1。在写  EEPR 前需先屏蔽中断，否则可能会因系统响

应中断而导致    EEWRITE 无法置  1。
   读操作控制位     EEREAD 置 1将启动   EEPROM 读操作，EEAR    所指  EEPROM 地址中的数据将被读出并缓存于           EEDR，
完成后  EEREAD 自动清  0。读操作需    2 个指令周期，且在      EEWRITE 为 1时无效。

   注：

   1、 EEPROM  读/写操作时，CPU     将暂停工作；
   2、 EEPROM  操作的时钟为系统高频时钟         FHOSC，因此在操作时需确保系统高频时钟源工作；
   3、 对  EECR、EEPR、EEAR  和 EEDR 的写操作，仅能通过       MOVRA 指令进行，其他指令的执行结果不确定；

   11.2    EEPROM   相关寄存器

EEPROM 控制寄存器

            Bit[7]    Bit[6]     Bit[5]    Bit[4]    Bit[3]    Bit[2]    Bit[1]    Bit[0]

  EECR        -         -         -         -          -         -      EEREAD   EEWRITE

   R/W        -         -         -         -          -         -       R/W       R/W

  初始值         -         -         -         -          -         -        0          0

BIT[1]      EEREAD – EEPROM读操作控制位
          0： 操作未开始或已完成，写         1开始  EEPROM 读操作；
          1： EEPROM  读操作中，完成后自动清        0；

BIT[0]      EEWRITE – EEPROM写操作控制位
          0： 操作未开始或已完成，写         1开始  EEPROM 写操作；
          1： EEPROM  写操作中，完成后自动清        0；

   注：应用程序中，在写        EECR指令和下一条真正执行的指令之间，需增加至少                2个 NOP  指令，以防止时序错误。

EEPROM 保护寄存器

            Bit[7]    Bit[6]     Bit[5]    Bit[4]    Bit[3]    Bit[2]    Bit[1]    Bit[0]

  EEPR       EEP7      EEP6      EEP5      EEP4      EEP3      EEP2      EEP1      EEP0

   R/W        W         W         W         W         W         W         W         W

<!-- p.55 -->

   初始值            0            0            0            0            0            0            0            0

BIT[7:0]       EEP[7:0] – EEPROM   写操作保护控制位，需先写                5AH 再立即写      A5H，EEWRITE     才能置    1

EEPROM   地址寄存器

                Bit[7]       Bit[6]       Bit[5]       Bit[4]       Bit[3]       Bit[2]       Bit[1]       Bit[0]

   EEAR                      EEA6         EEA5         EEA4         EEA3         EEA2         EEA1         EEA0

    R/W                       R/W          R/W          R/W          R/W          R/W          R/W          R/W

   初始值                         0            0            0            0            0            0            0

BIT[7:0]       EEA[6:0] – EEPROM   读写操作的       7 位地址

EEPROM   数据寄存器

                Bit[7]       Bit[6]       Bit[5]       Bit[4]       Bit[3]       Bit[2]       Bit[1]       Bit[0]

   EEDR         EED7         EED6         EED5         EED4         EED3         EED2         EED1         EED0

    R/W          R/W          R/W          R/W          R/W          R/W          R/W          R/W          R/W

   初始值            0            0            0            0            0            0            0            0

BIT[7:0]       EED[7:0] – EEPROM   读写操作的       8 位数据

    11.3      EEPROM      操作示例

    例如，先将数据         55H  写入   EEPROM   存储器    10H  中，再读取       EEPROM   存储器    11H  地址中内容：

               MOVAI           10H
               MOVRA           EEAR                ；将    10H 写入   EEAR
               MOVAI           55H

               MOVRA           EEDR                ；将    55H 写入   EEDR
               BCLR            GIE                 ；屏蔽中断
               MOVAI           5AH

               MOVRA           EEPR                ；使能     EE 操作，第     1 步：EEPR     写 5AH
               MOVAI           A5H
               MOVRA           EEPR                ；使能     EE 操作，第     2 步：EEPR     写 A5H

               MOVAI           01H
               MOVRA           EECR                ；启动     EE 写操作，将数据         55H  写入   EEPROM   地址   10H  中
               NOP                                 ；为防止时序错误，CPU              必须先执行      2-4 个  NOP  指令

               NOP
               BSET            GIE                 ；允许中断
               JBCLR           EECR,0              ；检查     EE 写操作是否完成
               GOTO            $-1

               MOVAI           11H
               MOVRA           EEAR                ；将    11H 写入   EEAR

<!-- p.56 -->

              MOVAI         02H
              MOVRA         EECR               ；启动   EE 读操作，读取       EEPROM  地址   11H 中内容

              NOP                              ；为防止时序错误，CPU          必须先执行      2-4个  NOP  指令
              NOP
              MOVAR         EEDR               ；从  EEDR  中读取数据
