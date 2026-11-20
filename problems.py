"""题面与编码。每题独立添加；original 只在有平台存档时提供。"""
PROBLEMS = []


def add(key, name, form, encoding, kind, description, rtl, other='', source='', original=None, cycles=0):
    PROBLEMS.append(dict(id=key, name=name, format=form, encoding=encoding, kind=kind,
                         description=description, rtl=rtl.strip(), other=other, source=source,
                         original=original, latency=cycles))


add('Q01','blezalc','blezalc rs, offset',('I',0x30),'branch',
    '将 rs 的值按 32 位有符号数解释。小于等于零时，跳到 PC 相对目标，并把本条指令地址加 8 写入 31 号寄存器；否则不链接。两条路径均执行延迟槽。',
    """if ($signed(GRF[rs]) <= 0) begin
    GRF[31] <= PC + 32'd8;
    PC <= PC + 32'd4 + ({{16{offset[15]}}, offset} << 2);
end else begin
    PC <= PC + 32'd8;
end""",source='S01、S04')
add('Q02','multc','multc rs, rt',('R',0x30),'mdu',
    '当 rs 按有符号数解释严格大于零时，对 rs、rt 进行 32 位有符号乘法，完整的 64 位积写入 HI、LO。否则保留 HI、LO。',
    """reg signed [63:0] product;
if ($signed(GRF[rs]) > 0) begin
    product = $signed(GRF[rs]) * $signed(GRF[rt]);
    {HI, LO} <= product;
end""",'成功时占用乘除部件 5 个周期，失败时不启动运算。本题的有符号性、周期和失败处理是为本地练习补全的规则。',source='S01',cycles=5)
add('Q03','lwld','lwld rt, offset(base)',('I',0x31),'load',
    '按普通 lw 的方法读出一个字。若读出的数据按无符号数比较大于等于 0x3000，且数据的最低两位均为零，则写入 31 号寄存器；否则写入 rt。',
    """reg [31:0] address, word;
address = GRF[base] + {{16{offset[15]}}, offset};
word = DM[address[31:2]];
if (word >= 32'h00003000 && word[1:0] == 2'b00)
    GRF[31] <= word;
else
    GRF[rt] <= word;""",source='S01、S04')
add('Q04','bgezalr','bgezalr rd, rs, rt',('R',0x31),'branch',
    '无论条件是否成立，都把本条指令地址加 8 写入 rd。若 rs 按有符号数解释大于等于零，延迟槽后跳到旧 rt 的值指定的地址；否则顺序执行。',
    """reg [31:0] target;
target = GRF[rt];
GRF[rd] <= PC + 32'd8;
if ($signed(GRF[rs]) >= 0)
    PC <= target;
else
    PC <= PC + 32'd8;""",'rd 与 rt 相同时仍使用写入链接值前的目标地址。',source='S02、S03、S05')
add('Q05','msub','msub rs, rt',('R',0x32),'mdu',
    '先计算 rs 与 rt 的 64 位有符号乘积，再用旧的 HI、LO 拼接值减去这个积，结果保留低 64 位写回 HI、LO。',
    """reg signed [63:0] product;
reg [63:0] result;
product = $signed(GRF[rs]) * $signed(GRF[rt]);
result = {HI, LO} - product;
{HI, LO} <= result;""",'本地练习将运算时间规定为 5 个周期。',source='S02、S03',cycles=5)
add('Q06','lhsb','lhsb rt, offset(base)',('I',0x32),'load',
    '基址与符号扩展的偏移相加得到字节地址。只有地址为偶数时才读取该地址的一个字节，符号扩展到 32 位写入 rt；奇地址不写寄存器。',
    """reg [31:0] address, word;
reg [7:0] data_byte;
address = GRF[base] + {{16{offset[15]}}, offset};
word = DM[address[31:2]];
data_byte = word >> (address[1:0] * 8);
if (address[0] == 1'b0)
    GRF[rt] <= {{24{data_byte[7]}}, data_byte};""",'历史 lhs 回忆存在字节、半字两种说法。本题采用字节版本；半字版本为 Q08。lhsb 是练习用名。',source='S02、S03')
add('Q07','clz','clz rd, rs',('R',0x33),'alu',
    '从 rs 的最高位 bit31 开始向低位检查，统计遇到第一个 1 之前连续的零位数，结果写入 rd。输入全零时结果为 32。',
    """integer i;
reg [31:0] count;
reg found;
count = 0;
found = 0;
for (i = 31; i >= 0; i = i - 1) begin
    if (!found && GRF[rs][i] == 1'b0) count = count + 1;
    if (GRF[rs][i] == 1'b1) found = 1;
end
GRF[rd] <= count;""",source='S05')
add('Q08','lhsh','lhsh rt, offset(base)',('I',0x33),'load',
    '只有有效字节地址为偶数时，才读取该地址开始的 16 位半字，符号扩展到 32 位写入 rt；奇地址不写寄存器。',
    """reg [31:0] address, word;
reg [15:0] halfword;
address = GRF[base] + {{16{offset[15]}}, offset};
word = DM[address[31:2]];
halfword = address[1] ? word[31:16] : word[15:0];
if (address[0] == 1'b0)
    GRF[rt] <= {{16{halfword[15]}}, halfword};""",'lhsh 是区分两个历史 lhs 回忆版本的练习用名。',source='S05')
add('Q09','bds','bds rs, rt',('R',0x34),'mdu',
    '把两个输入都看作 32 位无符号数，用较大的数除以较小的数。商写入 LO，余数写入 HI。',
    """reg [31:0] larger, smaller;
larger = GRF[rs] >= GRF[rt] ? GRF[rs] : GRF[rt];
smaller = GRF[rs] >= GRF[rt] ? GRF[rt] : GRF[rs];
LO <= larger / smaller;
HI <= larger % smaller;""",'测试保证两个输入均非零。本地练习将运算时间规定为 10 个周期。',source='S04',cycles=10)
add('Q10','lhonez','lhonez rt, offset(base)',('I',0x34),'load',
    '读出一个半字，统计其中 1 的个数。严格大于 8 时，把该半字符号扩展后写入 rt；否则把本条指令地址加 4 写入 31 号寄存器。',
    """reg [31:0] address, word;
reg [15:0] halfword;
integer i, count;
address = GRF[base] + {{16{offset[15]}}, offset};
word = DM[address[31:2]];
halfword = address[1] ? word[31:16] : word[15:0];
count = 0;
for (i = 0; i < 16; i = i + 1) count = count + halfword[i];
if (count > 8) GRF[rt] <= {{16{halfword[15]}}, halfword};
else GRF[31] <= PC + 32'd4;""",source='S04')
add('Q11','shl','shl',('R',0x35),'mdu',
    '交换乘除法部件中 HI、LO 的内容。两次写入同时发生，不能用已经更新的 HI 作为 LO 的新值。',
    """HI <= LO;
LO <= HI;""",'交换只需要 1 个周期。原平台编码的 funct 为 111100；本地旧练习编码为 110101，提交前务必选对。',source='S04、S09',original=('R',0x3c),cycles=1)
add('Q12','bezal','bezal rs, rt',('R',0x36),'branch',
    '当 rt 等于零时，跳到旧 rs 指定的地址，并向 31 号寄存器写入本条指令地址加 8；否则不跳转也不链接。两条路径都执行延迟槽。',
    """reg [31:0] target;
target = GRF[rs];
if (GRF[rt] == 0) begin
    GRF[31] <= PC + 32'd8;
    PC <= target;
end else PC <= PC + 32'd8;""",source='S04、S06',original=('R',0x31))
add('Q13','sbc','sbc rd, rs, rt',('R',0x37),'alu',
    '把 rs 拆成四个字节，按从最低字节到最高字节的顺序排列。统计每个字节中 1 的个数。rt 为奇数时，按计数从小到大排列；rt 为偶数时，从大到小排列。计数相同的字节保持原先顺序。排好后，第一项仍放在结果的最低字节，最后一项放在最高字节，写入 rd。',
    """reg [7:0] bytes [0:3];
integer counts [0:3];
integer i, j, k, temp_count;
reg [7:0] temp_byte;
for (i = 0; i < 4; i = i + 1) begin
    bytes[i] = GRF[rs] >> (8 * i);
    counts[i] = 0;
    for (k = 0; k < 8; k = k + 1)
        counts[i] = counts[i] + bytes[i][k];
end
for (i = 0; i < 3; i = i + 1)
    for (j = 0; j < 3 - i; j = j + 1)
        if ((GRF[rt][0] && counts[j] > counts[j+1]) ||
            (!GRF[rt][0] && counts[j] < counts[j+1])) begin
            temp_byte = bytes[j]; bytes[j] = bytes[j+1]; bytes[j+1] = temp_byte;
            temp_count = counts[j]; counts[j] = counts[j+1]; counts[j+1] = temp_count;
        end
GRF[rd] <= {bytes[3], bytes[2], bytes[1], bytes[0]};""",source='S06',original=('R',0x31))
add('Q14','lwm','lwm rt, offset(base)',('I',0x35),'load',
    '计算有效地址后清除最低两位，读出包含该地址的整字。用读出的字减去旧 rt 的值，取差的最低五位作为目的寄存器编号，再把读出的原始字写入该寄存器。',
    """reg [31:0] address, word, difference;
address = GRF[base] + {{16{offset[15]}}, offset};
word = DM[address[31:2]];
difference = word - GRF[rt];
GRF[difference[4:0]] <= word;""",source='S06',original=('I',0x2c))
add('Q15','jap','jap target',('J',0x36),'branch',
    '把本条指令地址加 8 作为一个完整字写到旧栈顶寄存器 $29 指定的地址，再将 $29 减 4。执行延迟槽后跳到 target 指定的伪直接跳转地址。',
    """reg [31:0] old_sp;
old_sp = GRF[29];
DM[old_sp[31:2]] <= PC + 32'd8;
GRF[29] <= old_sp - 32'd4;
PC <= {PC[31:28], target, 2'b00};""",'存储地址使用旧 $29，延迟槽读取 $29 时应得到减 4 后的值。',source='S04、S07',original=('J',0x36))
add('Q16','fdiv','fdiv rs, rt',('R',0x38),'mdu',
    '进行 32 位有符号除法。商向零截断并写入 LO，余数写入 HI。功能与 div 相同，运算时间缩短到 3 个周期。',
    """LO <= $signed(GRF[rs]) / $signed(GRF[rt]);
HI <= $signed(GRF[rs]) % $signed(GRF[rt]);""",source='S07',original=('R',0x2c),cycles=3)
add('Q17','lwmx','lwmx rt, offset(base)',('I',0x37),'load',
    '清除有效地址最低两位后读取整字。把读出的字与旧 rt 的值按 32 位有符号数比较。读数严格大于旧 rt 时向 5 号寄存器写入读数，否则向 4 号寄存器写入读数。',
    """reg [31:0] address, word;
address = GRF[base] + {{16{offset[15]}}, offset};
word = DM[address[31:2]];
if ($signed(word) > $signed(GRF[rt])) GRF[5] <= word;
else GRF[4] <= word;""",source='S04、S07',original=('I',0x2a))
add('Q18','jabs','jabs rs, rt, offset',('I',0x38),'branch',
    '按有符号数求 rs 与 rt 的数学差的绝对值，取低 30 位并乘 4。再加上本条指令地址加 4、符号扩展偏移左移两位，得到延迟槽后的跳转地址。不写寄存器。',
    """reg signed [32:0] difference;
reg [32:0] distance;
difference = $signed({GRF[rs][31], GRF[rs]}) -
             $signed({GRF[rt][31], GRF[rt]});
distance = difference < 0 ? -difference : difference;
PC <= PC + 32'd4 + ({{16{offset[15]}}, offset} << 2) +
      {distance[29:0], 2'b00};""",'使用 33 位差避免极端有符号输入溢出，是本地练习对回忆的明确化。',source='S09',original=('I',0x2c))
add('Q19','lwer','lwer rt, offset(base)',('I',0x39),'load',
    '清除有效地址最低两位后读出整字。读数加上旧 rt，结果与 0x0000001e 按位与，得到目的寄存器编号。把原始读数写入该偶数编号的寄存器。',
    """reg [31:0] address, word, destination;
address = GRF[base] + {{16{offset[15]}}, offset};
word = DM[address[31:2]];
destination = (word + GRF[rt]) & 32'h0000001e;
GRF[destination[4:0]] <= word;""",source='S04、S09',original=('I',0x19))
add('Q20','fmultu','fmultu rs, rt',('R',0x39),'mdu',
    '先求两个 32 位无符号数的 64 位乘积。若高 32 位为零，直接写入 HI、LO。否则在这个 64 位乘积中寻找最高的 1 的位号和最低的 0 的位号，取两位号差的绝对值，翻转乘积中该位号的位，再写入 HI、LO。位号从最低位 0 开始。',
    """reg [63:0] product;
integer i, highest_one, lowest_zero, flip;
reg found_zero;
product = {32'b0, GRF[rs]} * {32'b0, GRF[rt]};
if (product[63:32] != 0) begin
    highest_one = 0; lowest_zero = 0; found_zero = 0;
    for (i = 0; i < 64; i = i + 1) begin
        if (product[i]) highest_one = i;
        if (!found_zero && !product[i]) begin
            lowest_zero = i; found_zero = 1;
        end
    end
    flip = highest_one >= lowest_zero ? highest_one - lowest_zero :
                                         lowest_zero - highest_one;
    product = product ^ (64'b1 << flip);
end
{HI, LO} <= product;""",'运算时间为 3 个周期。',source='S10、S13',cycles=3)
add('Q21','jmv','jmv rs, rt, offset',('I',0x3a),'branch',
    '把 rs、rt 相加，和只保留低 32 位。取和的 bit30 到 bit1 组成一个 30 位无符号数，将它乘 4 后加到普通 PC 相对分支地址上。不写寄存器，执行一个延迟槽。',
    """reg [31:0] sum;
sum = GRF[rs] + GRF[rt];
PC <= PC + 32'd4 + ({{16{offset[15]}}, offset} << 2) +
      {sum[30:1], 2'b00};""",source='S11')
add('Q22','crt','crt rd, rs, rt',('R',0x3a),'alu',
    '对每个输入分别执行以下计算：把该 32 位输入循环右移 0 至 31 位，共得到 32 个数，将这些数相加，累加结果始终保留低 32 位。将两个累加值按有符号数比较。rs 的累加值更小写 0xffffffff，更大写 1，相等写 0。',
    """reg [31:0] rotated_rs, rotated_rt, sum_rs, sum_rt;
integer i;
rotated_rs = GRF[rs]; rotated_rt = GRF[rt];
sum_rs = 0; sum_rt = 0;
for (i = 0; i < 32; i = i + 1) begin
    sum_rs = sum_rs + rotated_rs;
    sum_rt = sum_rt + rotated_rt;
    rotated_rs = {rotated_rs[0], rotated_rs[31:1]};
    rotated_rt = {rotated_rt[0], rotated_rt[31:1]};
end
if ($signed(sum_rs) < $signed(sum_rt)) GRF[rd] <= 32'hffffffff;
else if ($signed(sum_rs) > $signed(sum_rt)) GRF[rd] <= 32'd1;
else GRF[rd] <= 32'd0;""",'累加位宽和有符号比较以来源 S11 为准。',source='S11、S12')
add('Q23','lpx','lpx rt, offset(base)',('I',0x3b),'load',
    '清除有效地址最低两位后读取整字。把读数最低五位看作 0 至 31 的整数，找出不大于它的最大质数，作为目的寄存器编号，并写入原始读数。输入为 0 或 1 时目的为 0。',
    """reg [31:0] address, word;
integer number, destination;
address = GRF[base] + {{16{offset[15]}}, offset};
word = DM[address[31:2]];
number = word[4:0];
destination = 0;
if (number >= 2) destination = 2;
if (number >= 3) destination = 3;
if (number >= 5) destination = 5;
if (number >= 7) destination = 7;
if (number >= 11) destination = 11;
if (number >= 13) destination = 13;
if (number >= 17) destination = 17;
if (number >= 19) destination = 19;
if (number >= 23) destination = 23;
if (number >= 29) destination = 29;
if (number >= 31) destination = 31;
GRF[destination] <= word;""",'lpx 是本册练习用名。rt 字段不参与运算。本题采用 S11 的直接读数版本，异或版本另见模拟题 M15。',source='S11、S12')
add('Q24','madd','madd rs, rt',('R',0x3b),'mdu',
    '先求两个 32 位有符号数的完整 64 位乘积，再加到旧 HI、LO 拼接值中，结果保留低 64 位写回 HI、LO。',
    """reg signed [63:0] product;
reg [63:0] result;
product = $signed(GRF[rs]) * $signed(GRF[rt]);
result = {HI, LO} + product;
{HI, LO} <= result;""",'题名有历史记录，完整行为由通常乘加语义重建；5 周期为本地练习规定。',source='S01、S14',cycles=5)

# 模拟题只组合已有题型，不增加异常、流水线级数或多端口写回要求。
add('M01','ctz','ctz rd, rs',('R',0x30),'alu',
    '从最低位 bit0 向高位统计连续的零，遇到第一个 1 停止，计数写入 rd。全零输入写 32。',
    """integer i;
reg [31:0] count;
reg found;
count = 0; found = 0;
for (i = 0; i < 32; i = i + 1) begin
    if (!found && !GRF[rs][i]) count = count + 1;
    if (GRF[rs][i]) found = 1;
end
GRF[rd] <= count;""",'题型参考 Q07。')
add('M02','bmax','bmax rd, rs, rt',('R',0x31),'alu',
    '分别统计 rs 四个字节中 1 的个数，选择计数最大的字节并符号扩展写入 rd。并列时，rt 为偶数选较低字节，rt 为奇数选较高字节。',
    """reg [7:0] data_byte, selected;
integer i, j, count, best;
best = -1; selected = 0;
for (i = 0; i < 4; i = i + 1) begin
    data_byte = GRF[rs] >> (8 * i); count = 0;
    for (j = 0; j < 8; j = j + 1) count = count + data_byte[j];
    if (count > best || (GRF[rt][0] && count == best)) begin
        best = count; selected = data_byte;
    end
end
GRF[rd] <= {{24{selected[7]}}, selected};""",'题型参考 Q13。')
add('M03','bgezalx','bgezalx rs, rt',('R',0x32),'branch',
    'rs 按有符号数解释大于等于零时，延迟槽后跳到旧 rt 指定的地址，同时链接到 31 号寄存器；否则顺序执行且不链接。',
    """reg [31:0] target;
target = GRF[rt];
if ($signed(GRF[rs]) >= 0) begin
    GRF[31] <= PC + 32'd8;
    PC <= target;
end else PC <= PC + 32'd8;""",'题型参考 Q04、Q12。')
add('M04','bparal','bparal rs, rt, offset',('I',0x30),'branch',
    '将 rs 与 rt 按位异或。异或结果中 1 的个数为偶数时，执行 PC 相对跳转并链接到 31 号寄存器；为奇数时不跳转、不链接。两条路径均执行延迟槽。',
    """reg [31:0] difference;
difference = GRF[rs] ^ GRF[rt];
if ((^difference) == 1'b0) begin
    GRF[31] <= PC + 32'd8;
    PC <= PC + 32'd4 + ({{16{offset[15]}}, offset} << 2);
end else PC <= PC + 32'd8;""",'题型参考 Q01、Q13。')
add('M05','jsp','jsp target',('J',0x31),'branch',
    '先把旧 $29 减 4，作为新栈顶；将本条指令地址加 8 写到新栈顶地址的整字，并把新栈顶写回 $29。执行延迟槽后按伪直接跳转方式跳到 target。',
    """reg [31:0] new_sp;
new_sp = GRF[29] - 32'd4;
DM[new_sp[31:2]] <= PC + 32'd8;
GRF[29] <= new_sp;
PC <= {PC[31:28], target, 2'b00};""",'题型参考 Q15。测试保证新旧栈顶均为合法对齐地址。')
add('M06','maddcu','maddcu rs, rt',('R',0x33),'mdu',
    'rs 为奇数时，计算 rs、rt 的无符号乘积，加到旧 HI、LO 的 64 位值上，保留低 64 位写回。rs 为偶数时不启动运算，HI、LO 保持不变。',
    """reg [63:0] product;
if (GRF[rs][0]) begin
    product = {32'b0, GRF[rs]} * {32'b0, GRF[rt]};
    {HI, LO} <= {HI, LO} + product;
end""",'成功时 5 个周期。题型参考 Q02、Q24。',cycles=5)
add('M07','mneg','mneg',('R',0x34),'mdu',
    '把 HI、LO 拼成 64 位值，取该值的 64 位补码相反数，再拆回 HI、LO。只需要 1 个周期。',
    """reg [63:0] result;
result = 64'b0 - {HI, LO};
{HI, LO} <= result;""",'题型参考 Q11。',cycles=1)
add('M08','divabs','divabs rs, rt',('R',0x35),'mdu',
    '把两个输入按有符号数解释，分别求绝对值，将绝对值作为无符号数相除。商写 LO，余数写 HI。运算需要 5 个周期。',
    """reg [31:0] dividend, divisor;
dividend = GRF[rs][31] ? (~GRF[rs] + 32'd1) : GRF[rs];
divisor = GRF[rt][31] ? (~GRF[rt] + 32'd1) : GRF[rt];
LO <= dividend / divisor;
HI <= dividend % divisor;""",'测试除数非零，0x80000000 的绝对值为无符号的 0x80000000。题型参考 Q09、Q16。',cycles=5)
add('M09','multfold','multfold rs, rt',('R',0x36),'mdu',
    '先进行 32 位无符号乘法。若 64 位积的最低位为 1，交换积的高低 32 位；否则保持。最终高半写 HI，低半写 LO，运算需要 3 个周期。',
    """reg [63:0] product;
product = {32'b0, GRF[rs]} * {32'b0, GRF[rt]};
if (product[0]) {HI, LO} <= {product[31:0], product[63:32]};
else {HI, LO} <= product;""",'题型参考 Q11、Q20。',cycles=3)
add('M10','lbnez','lbnez rt, offset(base)',('I',0x32),'load',
    '读取有效地址处的一个字节。该字节非零时，将其符号扩展后写入 rt；为零时不写回。',
    """reg [31:0] address, word;
reg [7:0] data_byte;
address = GRF[base] + {{16{offset[15]}}, offset};
word = DM[address[31:2]];
data_byte = word >> (address[1:0] * 8);
if (data_byte != 0) GRF[rt] <= {{24{data_byte[7]}}, data_byte};""",'题型参考 Q06、Q08。')
add('M11','shodd','shodd rt, offset(base)',('I',0x33),'store',
    'rt 为奇数时，把 rt 的低 16 位写到有效地址指定的半字，只修改相应的两个字节；rt 为偶数时不写内存。本指令不写寄存器。',
    """reg [31:0] address;
address = GRF[base] + {{16{offset[15]}}, offset};
if (GRF[rt][0]) begin
    if (address[1]) DM[address[31:2]][31:16] <= GRF[rt][15:0];
    else DM[address[31:2]][15:0] <= GRF[rt][15:0];
end""",'测试地址为偶数。题型是条件写使能与课程 sh 字节使能的组合。')
add('M12','lhneg','lhneg rt, offset(base)',('I',0x34),'load',
    '读取一个半字并符号扩展。半字为负数时写入 31 号寄存器，否则写入 rt。',
    """reg [31:0] address, word;
reg [15:0] halfword;
address = GRF[base] + {{16{offset[15]}}, offset};
word = DM[address[31:2]];
halfword = address[1] ? word[31:16] : word[15:0];
if (halfword[15]) GRF[31] <= {{16{halfword[15]}}, halfword};
else GRF[rt] <= {16'b0, halfword};""",'题型参考 Q10。')
add('M13','lwxor','lwxor rt, offset(base)',('I',0x35),'load',
    '清除有效地址最低两位，读出整字。读数与旧 rt 按位异或，取最低五位作为目的寄存器编号，把原始读数写入该寄存器。',
    """reg [31:0] address, word, destination;
address = GRF[base] + {{16{offset[15]}}, offset};
word = DM[address[31:2]];
destination = word ^ GRF[rt];
GRF[destination[4:0]] <= word;""",'题型参考 Q14、Q19。')
add('M14','lwcmp','lwcmp rt, offset(base)',('I',0x36),'load',
    '清除有效地址最低两位，读出整字。按无符号数比较读数与旧 rt。读数严格大于旧 rt 时向 rt 写入读数，否则向 base 写入读数。',
    """reg [31:0] address, word;
address = GRF[base] + {{16{offset[15]}}, offset};
word = DM[address[31:2]];
if (word > GRF[rt]) GRF[rt] <= word;
else GRF[base] <= word;""",'rt 与 base 相同也只写一次。题型参考 Q03、Q17。')
add('M15','lwprime','lwprime rt, offset(base)',('I',0x37),'load',
    '清除有效地址最低两位，读出整字。读数与旧 rt 按位异或，取最低五位，寻找不大于它的最大质数作为目的寄存器编号，写入原始读数。最低五位为 0 或 1 时目的为 0。',
    """reg [31:0] address, word, mixed;
integer number, destination;
address = GRF[base] + {{16{offset[15]}}, offset};
word = DM[address[31:2]];
mixed = word ^ GRF[rt]; number = mixed[4:0]; destination = 0;
if (number >= 2) destination = 2;
if (number >= 3) destination = 3;
if (number >= 5) destination = 5;
if (number >= 7) destination = 7;
if (number >= 11) destination = 11;
if (number >= 13) destination = 13;
if (number >= 17) destination = 17;
if (number >= 19) destination = 19;
if (number >= 23) destination = 23;
if (number >= 29) destination = 29;
if (number >= 31) destination = 31;
GRF[destination] <= word;""",'题型参考 Q23 及其来源 S12 记录的异或版本。')

BY_ID = {p['id']:p for p in PROBLEMS}
BY_NAME = {p['name']:p for p in PROBLEMS}
