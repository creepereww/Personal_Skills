# 实例：PXS 系列烟具固件工程（PXS-FS12 / PXS-FD07）

> 这份是**参考实例**，不是规范。新项目可以借它的架构思路，但**不要照抄业务逻辑和引脚分配**。
> 通用规则见 `SKILL.md`。

## 1. PWM 通道与引脚的对应（必须核对）

| 引脚宏 | 注释标注的通道 |
|---|---|
| `PIN_HEAT1_CTL = P02D` | PWM3B |
| `PIN_HEAT2_CTL = P03D` | PWM3C |
| （FS12）`PIN_HEAT1_CTL = P01D` | PWM3A |

`smoke.h` 里的 `T_SMOKE` / `SMOKE_PWM_T3A|T3B|T3C` 开关要和 `config.h` 的引脚注释**对上**，
否则会出现"初始化没生效"这类问题 —— 历史上就发生过（`PIN_HEAT1_CTL` 标 PWM3B，`T_SMOKE` 却是 `T3A`）。

另外：所有通道寄存器（`PWM3BEN`、`PWM3B1E` 等）参与编译时，**必须在 `MC9959B.h` 里有定义**，
否则报未定义。`SetPwm()` / `smoke_act_stop()` 里的通道分支要和实际启用的通道集合一致。

## 2. 代码架构（改之前先看懂）

- `main()` 里 `while(1)` 死循环，先刷 `StatusTmp = INTERRUPT_STATUS`，再算 `RISING_EDGE` / `FALLING_EDGE`
- 状态机：`gWorkmode` + 下面的大 `switch`；`glastWorkmode` 记录上一次状态用于进入/退出判断
- 事件位标志：`INTERRUPT_STATUS`，用 `TRIG_xxx()` / `CLR_xxx()` 置位清零，`EVT_xxx()` 宏读状态位（`Define.h`）
- 计时：`counter_200us` 是 200µs；`sleepcount` 只在 `MODE_NONE` 累加（进休眠用）
- 休眠：`MCU_SLEEP()` **自带空闲超时判断**（`sleepcount > SLEEP_IDLE_TIME_1MS`，阈值在 `config.h`），
  到点就 `return`。调用点直接 `MCU_SLEEP()`，**不要再在外面套 `if`** —— 它的语义已不是"无条件休眠"
- `led_on_flag` / `lowv_flag` / `power_full` / `alarm_*` 是 `sys_ctl_flag` / `sys_alm_flag` 的位
- 段码显示：`Codedisplay[]` + `SEG_*` 段选；`SEG_POWER1` / `SEG_POWER10` / `oil_seg1` / `oil_seg10`
- 引脚定义全在 `config.h`（`PIN_*`），功能宏在 `led.h`（`led_*` / `dis_*`）
- 头文件分工：`config.h` 参数/开关 → `Define.h` 位标志与 `TRIG_/CLR_/EVT_` →
  `led.h`（原 `Global.h` 第 4 节：LED 与显示）→ `smoke.h` 雾化 → `system_api.h` 对外 API。
  `led.h` 被 `Global.h` `#include`，`Interrupt.c` / `adc.c` / `smoke.c` 等只包 `Global.h` 就够；
  **新增头文件要在 `PXS-FS12.Proj` 的 `<asmFile>` 列表里登记一行**，否则 IDE 里看不到

### MITOU / USB 优先级

`config.h` 里 `EVT_PRIORITY` 是唯一开关：

```c
#define EVT_PRIORITY_MITOU 0     /* 抽吸优先：插着 USB 也能吸烟 */
#define EVT_PRIORITY_USB   1     /* 充电优先：USB 在位时不响应抽吸 */
#define EVT_PRIORITY EVT_PRIORITY_MITOU   /* 只改这一行 */
```

主循环用 `#if/#else` 把两个分支**按优先级顺序排开**，谁写在前面谁优先；
分支体是 `do{...}while(0)` 宏（`EVT_MITOU_HANDLE()` 等）。改动作逻辑只改宏体，
改优先级只改 `config.h` 一行。

### 中断里的引脚采样

`int_isr()` 里 MITOU(P13D) 和 USB(P06D) 走同一个 `KBIF` 中断，按 `EVT_PRIORITY` 排优先级：
优先的那路先判，另一路整块嵌进它的 `else`（`#if/#else` 两份代码，和主循环同一套写法）。

**代价要知道**：非优先的那一路只在优先脚为「反」时才刷新。`EVT_PRIORITY_MITOU` 时
抽吸中（MITOU 恒 1）USB 状态会冻结；`EVT_PRIORITY_USB` 时同理冻结抽吸状态。
改这块前先确认主循环里读的那一路不会因此读到旧值；要真正独立采样，
就把两个 `else` 里嵌的 `if` 提成两个平级的 `if`。

## 3. 项目特有的"无害"编译输出

| 输出 | 说明 |
|---|---|
| `smoke.c:NNN: error 20: Undefined identifier 'PIN_HEAT2_CTL'` | 该产品只有一路加热 |
| `smoke.c:86/87: warning 158: overflow in implicit constant conversion` | 既有 |
| `warning: multi-line comment`（`user.h:166`、`Global.h:75`） | 见 SKILL.md §3.3，注释掉的旧宏 |

## 4. 目录、版本控制与备份（本机约定）

- `/home/cgw06/Sino_Projects/<产品>` 是符号链接，指向
  `/mnt/d/SVN/PX_DESIGN/005-货架型产品库/<编号-产品>/02-软件版本库/<产品>`
- SDK 头文件：`/home/cgw06/Sino_Projects/include/include`（`mc32-common.h`、`MC9959B.h`、`MC9989.h` 等）
- **这些工程不在 SVN 版本控制下**（`.svn/wc.db` 里查不到对应节点），**没有 pristine 备份可回滚**
  → 改之前一定自己备份
- 同目录下带 "2" 的目录（如 `PXS-FS122/`）是**另一个引脚版本**（P01/P16 vs P06/P13），
  只能当参考，不能当成同一 revision 的真相
- 编译产物目录 `Debug/`、`Output/`、`System/` 在工程内，命令行编译请复制到 `/tmp`
- 目录是**会话创建时写死的**：从符号链接路径启动 opencode 会让会话目录变成链接路径，
  建议统一 `cd /mnt/d/SVN/.../<产品> && opencode` 用真实路径

## 5. 项目级开发日记（电气/硬件/现场经验在这里）

`/home/cgw06/Sino_Projects/include/SINO_MCU_吸烟电路板_开发日记.md`（GBK + CRLF）

- 分两章：**通用问题**（编译/编码/低功耗/调试/算法习惯）+ **产品级问题**（小火箭、大火箭、
  PXAKA-510MIX、PXS-CD02、PXagb-d226、PXS-FD06、PXD-CS03 …）
- 里面是技能覆盖不到的**硬件电气与现场经验**：短路/欠压门限怎么分、LVDF 与 ADC 的灵敏度差、
  呼吸灯 PWM 粒度、数码管亮度与共阴极配比、待机电流、消抖实测值……**要查这类问题先看日记**
- **纪律：每次改动后遇到新问题（新踩的坑、新调的参数、新发现的板级差异），按对应产品追加进这份日记**，
  格式 `现象 → 原因/溯源 → 解决`，产品相关的进产品章，跨产品的进通用章，别只留在对话里。
  反过来，技能里新增的通用条目也应该在这份日记里留一条（人读的那份是主）
