"""P5 练习协议；Q=往年资料，M=原模拟题，X=原补充题。"""
PROBLEMS=[]


def add(key,name,form,code,kind,description,rtl,other='',source='',r_opcode=0):
    PROBLEMS.append(dict(id=key,name=name,format=form,encoding=list(code),kind=kind,
                         description=description,rtl=rtl.strip(),other=other,source=source,
                         r_opcode=r_opcode,original=None,stage='P5'))


def count_rtl(expression,variable='count',width=32):
    return f'''integer i;
reg [31:0] {variable};
reg [{width-1}:0] data;
data = {expression};
{variable} = 0;
for (i = 0; i < {width}; i = i + 1) {variable} = {variable} + data[i];'''


def leading_rtl(expression,bit):
    return f'''integer i;
reg [31:0] count;
reg found;
reg [31:0] data;
data = {expression}; count = 0; found = 0;
for (i = 31; i >= 0; i = i - 1) begin
    if (!found && data[i] == 1'b{bit}) count = count + 1;
    else found = 1;
end'''


ADDR="address = GRF[base] + {{16{offset[15]}}, offset};"
SCALED="address = GRF[base] + ({{16{offset[15]}}, offset} << 2);"
WORD="reg [31:0] address, word;\n"+ADDR+"\nword = DM[address[31:2]];"
SUM="reg signed [32:0] sum;\nsum = $signed({GRF[rs][31], GRF[rs]}) + $signed({GRF[rt][31], GRF[rt]});"
REL="PC + 32'd4 + ({{16{offset[15]}}, offset} << 2)"

add('Q01','cco','cco rd, rs, rt',('R',0x30),'alu','统计 rs 与 rt 按位与后结果中 1 的个数，零扩展写入 rd。',
    count_rtl('GRF[rs] & GRF[rt]')+'\nGRF[rd] <= count;',source='S01')
add('Q02','bgezall','bgezall rs, offset',('I',0x30),'branch','总是链接到 $31。rs 按有符号数解释大于等于零时执行延迟槽并相对跳转；否则清空延迟槽，从本条地址加 8 继续。',
    f"GRF[31] <= PC + 32'd8;\nif ($signed(GRF[rs]) >= 0) PC <= {REL};\nelse PC <= PC + 32'd8;",source='S01')
add('Q03','lwso','lwso offset(base)',('I',0x31),'load','读出整字，与旧 $31 按有符号数求和。没有有符号溢出时写回 $31；溢出时取消本条写回。',
    'reg signed [32:0] sum;\n'+WORD+"\nsum = $signed({GRF[31][31], GRF[31]}) + $signed({word[31], word});\nif (sum[32] == sum[31]) GRF[31] <= sum[31:0];",'编码的 rt 固定为 11111；读取旧 $31。',source='S01')
add('Q04','cmco','cmco rd, rs',('R',0x31),'alu','找出 rs 中最长的一段连续的 1，段长写入 rd，不连接最高位与最低位。',
    '''integer i;
reg [31:0] run_length, best;
run_length = 0; best = 0;
for (i = 31; i >= 0; i = i - 1) begin
    if (GRF[rs][i]) run_length = run_length + 1;
    else run_length = 0;
    if (run_length > best) best = run_length;
end
GRF[rd] <= best;''',source='S01、S02')
add('Q05','blezalc','blezalc rs, offset',('I',0x32),'branch','rs 按有符号数解释小于等于零时，相对跳转并链接到 $31；否则不链接。两条路径都执行延迟槽。',
    f"if ($signed(GRF[rs]) <= 0) begin\n    GRF[31] <= PC + 32'd8;\n    PC <= {REL};\nend else PC <= PC + 32'd8;",'失败路径在历史回忆间有差异，本练习固定延迟槽总执行。',source='S01、S02')
add('Q06','lrm','lrm rt, offset(base)',('I',0x33),'load','读出整字，最低五位作为目的寄存器编号，把旧 rt 的值写入该寄存器。',
    WORD+'\nGRF[word[4:0]] <= GRF[rt];','本题采用 2020 记载中“读数低位决定目标”的版本。',source='S01、S02')
add('Q07','swc','swc rd, rs, rt',('R',0x32),'alu','rt 为奇数时将 rs 循环左移，为偶数时循环右移。移位量只取 rt 最低五位，结果写 rd。',
    '''reg [4:0] amount;
reg [31:0] result;
amount = GRF[rt][4:0];
if (amount == 0) result = GRF[rs];
else if (GRF[rt][0]) result = (GRF[rs] << amount) | (GRF[rs] >> (32-amount));
else result = (GRF[rs] >> amount) | (GRF[rs] << (32-amount));
GRF[rd] <= result;''','采用 S03/S05 的寄存器奇偶版本。',source='S03、S04、S05')
add('Q08','bonall','bonall rs, rt, offset',('I',0x34),'branch','总是链接到 $31。两个有符号输入的数学和为零时，执行延迟槽并相对跳转；否则清槽并顺序继续。',
    SUM+f"\nGRF[31] <= PC + 32'd8;\nif (sum == 0) PC <= {REL};\nelse PC <= PC + 32'd8;",'判断数学相反数；两个 0x80000000 不满足条件。',source='S03、S04、S05')
add('Q09','lhogez','lhogez rt, offset(base)',('I',0x35),'load','读取半字，1 的个数严格大于 8 时零扩展写入 rt；否则向 $31 写入本条指令地址加 4。',
    '''reg [31:0] address, word;
reg [15:0] halfword;
integer i, count;
'''+ADDR+'''
word = DM[address[31:2]];
halfword = address[1] ? word[31:16] : word[15:0];
count = 0;
for (i = 0; i < 16; i = i + 1) count = count + halfword[i];
if (count > 8) GRF[rt] <= {16'b0, halfword};
else GRF[31] <= PC + 32'd4;''','测试地址为偶数，保留原记载的零扩展与 PC+4。',source='S03、S04')
add('Q10','bltzalx','bltzalx rs, rt, offset',('I',0x36),'branch','总是链接并执行延迟槽。rs 为负数时，将有符号偏移加上 2 的 k 次幂，再乘 4，作为相对 PC+4 的位移；k 取 rt 的最低两位。否则顺序继续。',
    '''reg [31:0] displacement;
displacement = ({{16{offset[15]}}, offset} + (32'd1 << GRF[rt][1:0])) << 2;
GRF[31] <= PC + 32'd8;
if ($signed(GRF[rs]) < 0) PC <= PC + 32'd4 + displacement;
else PC <= PC + 32'd8;''','历史称 bltzal，本册加 x 区分标准同名指令。',source='S03')
add('Q11','addei','addei rt, rs, imm',('I',0x37),'alui','立即数高 16 位固定补 1，与 rs 作有符号加法。没有有符号溢出则写和的低 32 位；有溢出则写扩展后的立即数。',
    '''reg [31:0] extended;
reg signed [32:0] sum;
extended = {16'hffff, imm};
sum = $signed({GRF[rs][31], GRF[rs]}) + $signed({1'b1, extended});
if (sum[32] == sum[31]) GRF[rt] <= sum[31:0];
else GRF[rt] <= extended;''',source='S03、S14')
add('Q12','lbget','lbget rt, offset(base)',('I',0x38),'load','读出有效地址处字节并符号扩展。字节为负时写 base，否则写 rt。',
    '''reg [31:0] address, word;
reg [7:0] data_byte;
'''+ADDR+'''
word = DM[address[31:2]];
data_byte = word >> (address[1:0] * 8);
if (data_byte[7]) GRF[base] <= {{24{data_byte[7]}}, data_byte};
else GRF[rt] <= {24'b0, data_byte};''',source='S03、S06')
add('Q13','fz','fz rd, rs, rt',('R',0x33),'alu','从 rs 最低位向高位查找 0，依次改成 1，最多修改无符号 rt 指定的数量，结果写 rd。',
    '''reg [31:0] result, remaining;
integer i;
result = GRF[rs]; remaining = GRF[rt];
for (i = 0; i < 32; i = i + 1)
    if (!result[i] && remaining != 0) begin
        result[i] = 1; remaining = remaining - 1;
    end
GRF[rd] <= result;''','rt 使用完整 32 位，数量不足时把所有零位都置 1。',source='S07')
add('Q14','bsveall','bsveall rs, rt, offset',('I',0x39),'branch','按有符号数选两个输入的较小值。较小值为偶数时执行槽并相对跳转，否则清槽顺序继续；两种情况都链接。',
    f"reg [31:0] smaller;\nsmaller = $signed(GRF[rs]) < $signed(GRF[rt]) ? GRF[rs] : GRF[rt];\nGRF[31] <= PC + 32'd8;\nif (!smaller[0]) PC <= {REL};\nelse PC <= PC + 32'd8;",source='S07')
add('Q15','lwrev','lwrev n, offset(base)',('I',0x3a),'load','读出整字，最低四位作为目的号，向该寄存器写入指令 rt 字段中直接编码的 5 位数 n。',
    WORD+"\nGRF[word[3:0]] <= {27'b0, n};",'n 是编号本身，不读取对应寄存器。',source='S07')
add('Q16','xe','xe rd, rs, rt',('R',0x34),'alu','只保留 rt 的偶数位，再与 rs 按位异或，写入 rd。最低位 bit0 是偶数位。',
    "GRF[rd] <= GRF[rs] ^ (GRF[rt] & 32'h55555555);",source='S08、S09')
add('Q17','jtl','jtl rs, rt, offset',('I',0x3b),'branch','计算普通相对分支地址和两个寄存器的 32 位和，按无符号地址比较。分支地址严格更小时执行槽并跳到它；否则清槽并跳到寄存器和。总是链接。',
    f"reg [31:0] relative, register_sum;\nrelative = {REL};\nregister_sum = GRF[rs] + GRF[rt];\nGRF[31] <= PC + 32'd8;\nif (relative < register_sum) PC <= relative;\nelse PC <= register_sum;",'地址比较的无符号性和相等处理为练习明确化。',source='S08、S09')
add('Q18','lwoc','lwoc rt, offset(base)',('I',0x3c),'load','偏移符号扩展后左移两位再加基址，读取整字。读数最高位为零时写到读数最低四位指定的寄存器，否则写到 rt。',
    'reg [31:0] address, word;\n'+SCALED+"\nword = DM[address[31:2]];\nif (!word[31]) GRF[word[3:0]] <= word;\nelse GRF[rt] <= word;",'偏移只左移两位一次；不读取旧 rt。',source='S08、S09、S10')
add('Q19','addoi','addoi rt, rs, imm',('I',0x3d),'alui','rs 加符号扩展的立即数，先保留低 32 位，再将这个补码和取相反数，并转换成 32 位原码：最高位表示负号，低 31 位表示绝对值。',
    '''reg [31:0] sum, negated, magnitude;
sum = GRF[rs] + {{16{imm[15]}}, imm};
negated = -sum;
magnitude = negated[31] ? -negated : negated;
GRF[rt] <= {negated[31], magnitude[30:0]};''','测试避开和为 0x80000000 的情况；零写为 0。位宽和极值限制为练习补充。',source='S11、S06')
add('Q20','ccc','ccc rd, rs, rt',('R',0x35),'alu','比较 rs 的前导零数与 rt 的前导一数。前者严格更大时，结果用 rs 高半字、rt 低半字；否则交换半字来源。',
    '''integer i;
integer zeros, ones;
reg stop_rs, stop_rt;
zeros = 0; ones = 0; stop_rs = 0; stop_rt = 0;
for (i = 31; i >= 0; i = i - 1) begin
    if (!stop_rs && !GRF[rs][i]) zeros = zeros + 1; else stop_rs = 1;
    if (!stop_rt && GRF[rt][i]) ones = ones + 1; else stop_rt = 1;
end
if (zeros > ones) GRF[rd] <= {GRF[rs][31:16], GRF[rt][15:0]};
else GRF[rd] <= {GRF[rt][31:16], GRF[rs][15:0]};''',source='S13')
add('Q21','cjoc','cjoc rs, rt, offset',('I',0x3e),'branch','以 offset 最低三位为起始位号，从 rs 中取向高位的 8 位无符号窗口。窗口大于 21 时向 rt 链接并执行槽、相对跳转；否则不链接且清槽。',
    f"reg [7:0] window;\nwindow = GRF[rs] >> offset[2:0];\nif (window > 8'd21) begin\n    GRF[rt] <= PC + 32'd8;\n    PC <= {REL};\nend else PC <= PC + 32'd8;",'rt 是链接目的，不读取其旧值。失败同时取消链接与槽。',source='S13')
add('Q22','ccs','ccs rt, offset(base)',('I',0x3f),'load','统计读出字高、低半字中 1 的个数。高半字计数更大时目的为 31，否则目的为高半字计数。写入值为读数与旧 rt 的异或。',
    '''reg [31:0] address, word;
integer i, high_count, low_count, destination;
'''+ADDR+'''
word = DM[address[31:2]]; high_count = 0; low_count = 0;
for (i = 0; i < 16; i = i + 1) begin
    high_count = high_count + word[i+16]; low_count = low_count + word[i];
end
destination = high_count > low_count ? 31 : high_count;
GRF[destination] <= word ^ GRF[rt];''',source='S13')
add('Q23','dsc','dsc rs, rt, imm',('I',0x10),'alui','只读取 rt。将它左移 imm 的最高五位指定的位数，再与它算术右移 imm 最低五位的结果异或，写入 rs。',
    "reg signed [31:0] arithmetic_result;\narithmetic_result = $signed(GRF[rt]) >>> imm[4:0];\nGRF[rs] <= (GRF[rt] << imm[15:11]) ^ arithmetic_result;",'中间 imm[10:5] 不参与运算，算术右移先单独求值。',source='S13')
add('Q24','bloc','bloc rs, rt, offset',('I',0x11),'branch','rs 的前导一数严格大于 rt 最低六位时相对跳转，否则顺序继续。两条路径均链接到 $31 并执行槽。',
    leading_rtl('GRF[rs]',1)+f"\nGRF[31] <= PC + 32'd8;\nif (count > GRF[rt][5:0]) PC <= {REL};\nelse PC <= PC + 32'd8;",source='S13')
add('Q25','lhp','lhp rt, offset(base)',('I',0x12),'load','以字偏移读出整字，与旧 rt 异或。异或结果高低半字相同时，目的为最高 1 的位号；否则目的为 31。写入原始读数。',
    '''reg [31:0] address, word, mixed;
integer i, destination;
'''+SCALED+'''
word = DM[address[31:2]]; mixed = word ^ GRF[rt]; destination = 0;
if (mixed[31:16] == mixed[15:0]) begin
    for (i = 0; i < 32; i = i + 1) if (mixed[i]) destination = i;
end else destination = 31;
GRF[destination] <= word;''','异或结果为零时目的为 0。',source='S13')
add('Q26','taddu','taddu rd, rs, rt',('R',0x36),'alu','两个输入相加，结果保留低 32 位写 rd，不产生溢出异常。',
    'GRF[rd] <= GRF[rs] + GRF[rt];','历史仅有补码相加简述，本练习按 32 位回绕加法补全。',source='S05')
add('Q27','blezals','blezals rs, offset',('I',0x13),'branch','总是链接并执行延迟槽。rs 按有符号数解释小于等于零时相对跳转，否则顺序继续。',
    f"GRF[31] <= PC + 32'd8;\nif ($signed(GRF[rs]) <= 0) PC <= {REL};\nelse PC <= PC + 32'd8;",'槽及地址公式为普通分支补全约定。',source='S05')
add('Q28','bovc','bovc rs, rt, offset',('I',0x15),'branch','两个输入的有符号加法溢出时相对跳转并链接到 $31，否则不链接。两条路径都执行槽。',
    SUM+f"\nif (sum[32] != sum[31]) begin\n    GRF[31] <= PC + 32'd8;\n    PC <= {REL};\nend else PC <= PC + 32'd8;",'助记符及普通延迟槽是本册补全约定。',source='S14')
add('Q29','lweo','lweo rt, offset(base)',('I',0x16),'load','读出整字，偶数写 rt，奇数写 $31；实际写回值始终是原始读数。',
    WORD+'\nif (word[0]) GRF[31] <= word;\nelse GRF[rt] <= word;','助记符为本册练习命名，原记录年份未确认。',source='S14')

add('M01','pcxor','pcxor rd, rs, rt',('R',0x38),'alu','统计两个输入异或后 1 的个数，写 rd。',count_rtl('GRF[rs] ^ GRF[rt]')+'\nGRF[rd] <= count;','原模拟题 Q01，编码和测试点不变。')
add('M02','bwin','bwin rd, rs, rt',('R',0x39),'alu','以 rt 最低五位作为起始位号，从 rs 逻辑右移后取低字节，符号扩展写 rd。超过最高位的位置补零。',
    "reg [31:0] shifted;\nshifted = GRF[rs] >> GRF[rt][4:0];\nGRF[rd] <= {{24{shifted[7]}}, shifted[7:0]};",'原模拟题 Q02。')
add('M03','sathi','sathi rt, rs, imm',('I',0x30),'alui','rs 加符号扩展立即数。有符号数学和超范围时写该方向的边界，否则写和。',
    '''reg signed [32:0] sum;
sum = $signed({GRF[rs][31], GRF[rs]}) + $signed({{17{imm[15]}}, imm});
if (sum > 33'sd2147483647) GRF[rt] <= 32'h7fffffff;
else if (sum < -33'sd2147483648) GRF[rt] <= 32'h80000000;
else GRF[rt] <= sum[31:0];''','原模拟题 Q03。')
add('M04','bopz','bopz rs, rt, offset',('I',0x31),'branch','有符号数学和严格小于零时执行槽并相对跳转，否则清槽顺序继续。不写寄存器。',SUM+f"\nif (sum < 0) PC <= {REL};\nelse PC <= PC + 32'd8;",'原模拟题 Q04。')
add('M05','bmeqal','bmeqal rs, rt, offset',('I',0x32),'branch','比较两个输入低半字的无符号值。rs 小于等于 rt 时相对跳转并链接，否则不链接。槽总执行。',
    f"if (GRF[rs][15:0] <= GRF[rt][15:0]) begin\n    GRF[31] <= PC + 32'd8;\n    PC <= {REL};\nend else PC <= PC + 32'd8;",'原模拟题 Q05。')
add('M06','joddal','joddal rs, rt, offset',('I',0x33),'branch','总是链接。rs 为奇数时执行槽并相对跳转；为偶数时清槽，跳到旧 rt 加 rs 的 bit3、bit2 对应地址增量。',
    f"GRF[31] <= PC + 32'd8;\nif (GRF[rs][0]) PC <= {REL};\nelse PC <= GRF[rt] + (GRF[rs] & 32'h0000000c);",'原模拟题 Q06。')
add('M07','lwnz','lwnz rt, offset(base)',('I',0x34),'load','整字读数非零才写 rt，为零保留旧值。',WORD+'\nif (word != 0) GRF[rt] <= word;','原模拟题 Q07。')
add('M08','lbsel','lbsel rt, offset(base)',('I',0x35),'load','字节符号扩展，负数写 base，否则写 rt。',
    next(s['rtl'] for s in PROBLEMS if s['name']=='lbget'),'原模拟题 Q08。')
add('M09','lwgate','lwgate rt, offset(base)',('I',0x36),'load','整字读数与旧 rt 作有符号加法。仅当不溢出且数学和为奇数时，将和写入 rt。',
    'reg signed [32:0] sum;\n'+WORD+"\nsum = $signed({word[31], word}) + $signed({GRF[rt][31], GRF[rt]});\nif (sum[32] == sum[31] && sum[0]) GRF[rt] <= sum[31:0];",'原模拟题 Q09。')
add('M10','lwxsel','lwxsel rt, offset(base)',('I',0x37),'load','以字偏移读数，与旧 rt 异或。异或最高位为 1 时目的为 rt，否则为异或低四位。实际写回原始读数。',
    'reg [31:0] address, word, mixed;\n'+SCALED+"\nword = DM[address[31:2]]; mixed = word ^ GRF[rt];\nif (mixed[31]) GRF[rt] <= word;\nelse GRF[mixed[3:0]] <= word;",'原模拟题 Q10。')
add('X01','blztal','blztal rs, rt, offset',('I',0x27),'branch','有符号 rs 为负时相对跳转并链接，否则不链接。位移为有符号 offset 乘以 2 的 2+k 次幂，k 取旧 rt 最低两位。槽总执行。',
    '''reg [31:0] displacement;
displacement = {{16{offset[15]}}, offset} << (2 + GRF[rt][1:0]);
if ($signed(GRF[rs]) < 0) begin
    GRF[31] <= PC + 32'd8;
    PC <= PC + 32'd4 + displacement;
end else PC <= PC + 32'd8;''','保留原 BLZTAL 补充练习的编码与 24 点；不额外推定历史年份。')

BY_ID={p['id']:p for p in PROBLEMS}
BY_NAME={p['name']:p for p in PROBLEMS}
