# 9 模拟比较器 CMP

> 源：MC9959B 用户手册 V1.0.1（p.50–52）· 页码为 PDF 页序

> **阅读提示**：正文保留 PDF 版面布局。涉及寄存器 `CMPCR0`、`CMPCR1`、`CMPCLR`。
> 本型号**无 OPA**（9959 有第 10 章 OPA，9959B 整章取消）。
> 新增：负端输入 1/2 分压（`AFCR` 的 `CMPNDIV` 位，见 `06-ADC.md`）。
> 电气参数见 `01-电气特性.md` 的 2.5。

<!-- p.50 -->

9   模拟比较器          CMP

   9.1     CMP  概述

   芯片内置   1 个模拟比较器     CMP，共模输入范围为       0~（VDD-1.4V），输入端失调电压可通过自消除寄存器进行调校，
精度为±2mV，输出无回滞且支持去抖处理。
   CMP 的正端输入可通过      CMPPS 选择外部输入电压、GND、或          VDD内部分压电压；负端输入可通过CMPNS            选择多

路外部输入电压，并支持分压选择，通过CMPNDIV              控制。
   CMP 的输出端电平可通过CMPDB         选择去抖处理，去抖后的输出信号CMP_OUT             可从端口输出且支持输出取反，并
可选择上升沿或下降沿触发CMP          中断。

   9.2     CMP  相关寄存器

比较器控制寄存器

            Bit[7]     Bit[6]    Bit[5]    Bit[4]    Bit[3]    Bit[2]    Bit[1]    Bit[0]

 CMPCR0     CMPEN    CMPDB2    CMPDB1     CMPDB0    CMPNV     CMPOE      CMPIM     CMPOF

   R/W       R/W       R/W       R/W       R/W        R/W       R/W       R/W        R

  初始值         0         0         0          0         0         0         0         X

BIT[7]      CMPEN – 比较器CMP   使能位

          0： 关闭  CMP；
          1： 开启  CMP；
BIT[6:4]    CMPDB[2:0] – CMP输出去抖时间选择位

                           CMPDB[2:0]         CMP 输出去抖时间

                              000               0（不去抖）

                              001             1个  FCPU时钟周期

                              010             2个  FCPU时钟周期

                              011             4个  FCPU时钟周期

                              100             8个  FCPU时钟周期

<!-- p.51 -->

                                   101              12 个 FCPU 时钟周期

                                   110              16 个 FCPU 时钟周期

                                   111              32 个 FCPU 时钟周期
BIT[3]       CMPNV – CMPO   端口输出取反控制位

           0：  端口输出     CMP 比较结果的正向电平；
           1：  端口对    CMP 比较结果取反后输出；
BIT[2]       CMPOE – CMPO   端口输出使能位

           0：  禁止端口输出       CMP 比较结果；
           1：  允许端口输出       CMP 比较结果；
BIT[1]       CMPIM – CMP  中断触发方式选择位

           0：  CMP  输出信号    CMP_OUT   的上升沿触发中断；
           1：  CMP  输出信号    CMP_OUT   的下降沿触发中断；
BIT[0]       CMPOF – CMP   比较结果状态标志位

           0：  CMP  比较结果为低，即比较器正端输入电压低于负端输入电压；或                           CMP  关闭；
           1：  CMP  比较结果为高，即比较器正端输入电压高于负端输入电压；

              Bit[7]      Bit[6]     Bit[5]      Bit[4]      Bit[3]     Bit[2]      Bit[1]     Bit[0]

 CMPCR1         -           -       CMPPS3      CMPPS2     CMPPS1      CMPPS0     CMPNS1      CMPNS0

   R/W          -           -         R/W         R/W        R/W         R/W        R/W         R/W

  初始值           -           -          0           0           0          0           0          0

BIT[5:2]     CMPPS[3:0] – CMP 正端输入选择位

                CMPPS[3:0]        CMP 正端输入            CMPPS[3:0]        CMP  正端输入

                   0000               GND                1000            0.40×VDD

                   0001            0.05×VDD              1001            0.45×VDD

                   0010            0.10×VDD              1010            0.50×VDD

                   0011            0.15×VDD              1011            0.55×VDD

                   0100            0.20×VDD              1100            0.60×VDD

                   0101            0.25×VDD              1101            0.65×VDD

                   0110            0.30×VDD              1110            0.70×VDD

                   0111            0.35×VDD              1111          外部   CMPP 输入

BIT[1:0]     CMPNS[1:0] – CMP  负端输入选择位

                               CMPNS[1:0]              CMP 负端输入

                                   00                外部   CMPN0  输入

                                   01                外部   CMPN1  输入

                                   10                外部   CMPN2  输入

                                   11                外部   CMPN3  输入

<!-- p.52 -->

辅助功能控制寄存器

              Bit[7]     Bit[6]     Bit[5]     Bit[4]     Bit[3]     Bit[2]     Bit[1]     Bit[0]

   AFCR                                                            CMPNDIV     ADCGS1     ADCGS0

   R/W                                                                R/W        R/W        R/W

  初始值                                                                  0          0          0

BIT[2]       CMPNDIV – CMPN  输入分压控制
           0：  不分压；

           1：  1/2分压；

比较器自消除寄存器

              Bit[7]     Bit[6]     Bit[5]     Bit[4]     Bit[3]     Bit[2]     Bit[1]     Bit[0]

 CMPCLR     CMPCLRE    CMPCLRS    CMPCLR5    CMPCLR4    CMPCLR3    CMPCLR2    CMPCLR1     CMPCLR0

   R/W        R/W        R/W        R/W         R/W        R/W        R/W        R/W        R/W

  初始值           0          0          1          0          0          0          0          0

BIT[7]       CMPCLRE – CMP  自消除模式使能位

           0：  关闭  CMP 自消除模式；
           1：  使能  CMP 自消除模式；
BIT[6]       CMPCLRS – CMP  自消除参考源选择位
           0：  CMP 自消除参考源为其负端输入；

           1：  CMP 自消除参考源为其正端输入；

   注：自消除参考源应选择电压较为稳定的一路输入端，且参考源输入端的正、负极性不影响调校效果。
BIT[5:0]     CMPCLR[5:0] – CMP自消除校准位

   9.3      CMP   失调电压调校流程

   (1) 设置  CMPCLRE=1，使能失调电压自消除模式；
   (2) 设置  CMPCLRS，选择比较器自消除参考源；
   (3) 设置  CMPCLR[5:0]=00H，等待至少      100μs 后读取标志位      CMPOF；

   (4) CMPCLR[5:0]自加   1，等待至少     100μs后重新读取     CMPOF：
          若 CMPOF  发生翻转，则表示已调校到位；
          若 CMPCLR[5:0]=3FH 而  CMPOF  仍未翻转，则表示共模输入超出范围，调校失败；

   (5) 循环执行（4），直到调校到位或调校失败；
   (6) 判断当前调校输出方向：
          若 CMPCLR[5]=1，则   CMPCLR[4:0]保持当前值不变；

          若 CMPCLR[5]=0，则   CMPCLR[4:0]减  1作为校准值；
   (7) 设置  CMPCLRE=0，关闭自消除模式；
