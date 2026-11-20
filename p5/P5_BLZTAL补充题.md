# P5 补充练习 BLZTAL

整理版，2026-11-20。Q01—Q29 是历史资料改编；M01—M10 对应旧模拟题 Q01—Q10，X01 对应旧 BLZTAL。每题 24 点。

题号在整合仓库中须加 P5 前缀，例如 P5-Q01 和 P5-M01。所有编码都是本册练习协议，不宣称是历史原编码。本包使用的基础指令为 add、sub、ori、lui、lw、sw、beq、jal、jr、nop；PC 从 0x3000 开始，IM 4096 字、DM 3072 字，GRF 和 DM 复位清零。

顶层为 mips(clk, reset)，IM、DM 在 CPU 内部。GRF 和 DM 按课程要求打印带 PC 的写入日志。GRF 表示通用寄存器，DM 用整字编号，PC 是当前指令地址；操作栏为行为定义，不限制具体流水级。所有源使用写入前的旧值，写 $0 丢弃，固定宽度结果保留低位。

控制指令的 PC 赋值表示处理延迟槽后的地址；是否清空延迟槽以中文描述为准。槽内不安排控制指令。字节按小端选择，普通字访问对齐到四字节，半字对齐到两字节，测试地址均有效。

编码按高位到低位排列。R 型字段宽度依次为 6、5、5、5、5、6 位；I 型为 6、5、5、16 位。base 占 rs 字段。

## P5-X01　blztal

编码：`100111 rs rt offset16`。

格式：`blztal rs, rt, offset`。

描述：有符号 rs 为负时相对跳转并链接，否则不链接。位移为有符号 offset 乘以 2 的 2+k 次幂，k 取旧 rt 最低两位。槽总执行。

操作：

```verilog
reg [31:0] displacement;
displacement = {{16{offset[15]}}, offset} << (2 + GRF[rt][1:0]);
if ($signed(GRF[rs]) < 0) begin
    GRF[31] <= PC + 32'd8;
    PC <= PC + 32'd4 + displacement;
end else PC <= PC + 32'd8;
```

其他：保留原 BLZTAL 补充练习的编码与 24 点；不额外推定历史年份。
