/* {{TITLE}} */

void INIT_GPIO(void)
{
// IO数据位
IOP0 = {{IOP0}};   {{C_IOP0}}
IOP1 = {{IOP1}};   {{C_IOP1}}
IOP2 = {{IOP2}};   {{C_IOP2}}
// IO方向 1:out  0:in
OEP0 = {{OEP0}};  {{C_OEP0}}
OEP1 = {{OEP1}};  {{C_OEP1}}
OEP2 = {{OEP2}};  {{C_OEP2}}
// IO口上拉电阻   1:enable  0:disable
PUP0 = {{PUP0}};   {{C_PUP0}}
PUP1 = {{PUP1}};   {{C_PUP1}}
PUP2 = {{PUP2}};   {{C_PUP2}}
// IO口下拉电阻   1:enable  0:disable
PDP0 = {{PDP0}};   {{C_PDP0}}
PDP1 = {{PDP1}};   {{C_PDP1}}
PDP2 = {{PDP2}};   {{C_PDP2}}
// 推挽输出
// PMOD = 0x00;
/*  // 普通驱动
DRVCR = 0x80; */
{{IRQ_CALLS}}
}
