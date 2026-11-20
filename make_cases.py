"""固定种子生成 39 * 24 个独立复位的测试程序、期望日志与题目册。"""
from pathlib import Path
import hashlib
import json
import random
import shutil
from problems import PROBLEMS, BY_ID, BY_NAME
from model import reference, signed, ones, PRIMES

ROOT=Path(__file__).resolve().parent
MASK=0xffffffff


class Program:
    def __init__(self, spec):
        self.spec=spec;self.rows=[];self.labels={};self.focus=[]
    @property
    def pc(self): return 0x3000+4*len(self.rows)
    def emit(self,name,*args): self.rows.append((name,args));return self.pc-4
    def label(self,name): self.labels[name]=self.pc
    def li(self,reg,value):
        self.emit('lui',reg,(value&MASK)>>16);self.emit('ori',reg,reg,value&65535)
    def label_value(self,reg,name):
        self.emit('labelhi',reg,name);self.emit('labello',reg,name)
    def nop(self,n=1):
        for _ in range(n): self.emit('nop')
    def producer(self,reg,value,mode=0):
        if mode==0:self.li(reg,value)
        elif mode==1:
            self.li(28,value);self.emit('sw',28,0x480,0);self.emit('lw',reg,0x480,0)
        elif mode==2:
            self.li(28,value);self.emit('mtlo',28);self.emit('mflo',reg)
        else:
            self.li(reg,~value);self.li(reg,value) # 同一寄存器的最新生产者优先
    def custom(self,*args): self.focus.append(self.pc);self.emit(self.spec['name'],*args)
    def observe(self,reg,k=0):
        # 紧邻计算、写数据、D 级比较；三者都不依赖预设的具体数值。
        if k%3==0:self.emit('add',24,reg,0)
        elif k%3==1:self.emit('sw',reg,0x800,0)
        else:
            label='obs_'+str(len(self.rows));self.emit('beq',reg,0,label)
            self.emit('ori',26,0,0x56);self.emit('ori',27,0,0x57);self.label(label)
        self.emit('sw',reg,0x804,0)
    def finish(self):
        self.nop(3) # 标记晚于之前的 M/W 事件；允许在标记后再观察排空。
        self.emit('ori',30,0,0xcafe);self.label('halt')
        self.emit('beq',0,0,'halt');self.nop()
    def encode(self,original=False):
        words=[]
        for index,(name,args) in enumerate(self.rows):
            pc=0x3000+4*index
            if name in ('labelhi','labello'):
                dst,label=args;value=self.labels[label]
                word=(0xf<<26)|(dst<<16)|(value>>16) if name=='labelhi' else (0xd<<26)|(dst<<21)|(dst<<16)|(value&65535)
            elif name=='nop':word=0
            elif name in ('add','sub','and','or','slt','sltu'):
                rd,rs,rt=args;word=(rs<<21)|(rt<<16)|(rd<<11)|dict(add=0x20,sub=0x22,**{'and':0x24,'or':0x25},slt=0x2a,sltu=0x2b)[name]
            elif name in ('mult','multu','div','divu'):
                rs,rt=args;word=(rs<<21)|(rt<<16)|dict(mult=0x18,multu=0x19,div=0x1a,divu=0x1b)[name]
            elif name in ('mthi','mtlo','jr'):word=args[0]<<21|dict(mthi=0x11,mtlo=0x13,jr=8)[name]
            elif name in ('mfhi','mflo'):word=args[0]<<11|dict(mfhi=0x10,mflo=0x12)[name]
            elif name=='lui':word=(0xf<<26)|(args[0]<<16)|(args[1]&65535)
            elif name in ('addi','andi','ori'):
                rt,rs,imm=args;word=(dict(addi=8,andi=0xc,ori=0xd)[name]<<26)|(rs<<21)|(rt<<16)|(imm&65535)
            elif name in ('lb','lh','lw','sb','sh','sw'):
                rt,off,base=args;word=(dict(lb=0x20,lh=0x21,lw=0x23,sb=0x28,sh=0x29,sw=0x2b)[name]<<26)|(base<<21)|(rt<<16)|(off&65535)
            elif name in ('beq','bne'):
                rs,rt,label=args;off=(self.labels[label]-pc-4)//4
                word=((4 if name=='beq' else 5)<<26)|(rs<<21)|(rt<<16)|(off&65535)
            elif name=='jal':word=(3<<26)|(self.labels[args[0]]>>2)
            elif name==self.spec['name']:
                form,code=self.spec['original'] if original and self.spec['original'] else self.spec['encoding']
                if self.spec['kind'] in ('load','store'):
                    rt,off,rs=args;word=(code<<26)|(rs<<21)|(rt<<16)|(off&65535)
                elif name in ('blezalc','bparal','jabs','jmv'):
                    if name=='blezalc':rs,label=args;rt=0;extra=0
                    else:rs,rt,label,extra=args
                    off=(self.labels[label]-pc-4)//4-extra
                    off=(off+(1<<29))%(1<<30)-(1<<29)
                    if not -32768<=off<=32767:raise ValueError('分支偏移溢出')
                    word=(code<<26)|(rs<<21)|(rt<<16)|(off&65535)
                elif form=='J':word=(code<<26)|(self.labels[args[0]]>>2)
                else:
                    if name in ('clz','ctz'):rd,rs=args;rt=0
                    elif name in ('sbc','crt','bmax','bgezalr'):rd,rs,rt=args
                    elif name in ('shl','mneg'):rd=rs=rt=0
                    else:rs,rt=args;rd=0
                    word=(rs<<21)|(rt<<16)|(rd<<11)|code
            else:raise ValueError(name)
            words.append(word)
        return words
    def listing(self):
        lines=[]
        for i,(name,args) in enumerate(self.rows):
            labels=' '.join(k+':' for k,v in self.labels.items() if v==0x3000+i*4)
            lines.append(f'{0x3000+i*4:08x}  {labels} {name} '+', '.join(map(str,args)))
        return '\n'.join(lines)+'\n'


VALUES=[0,0xffffffff,0x80000000,0x7fffffff,1,2,0xffff0000,0x0000ffff,
        0x80ff01e0,0x01020408,0xaaaaaaaa,0x55555555,0x10000,0x80000001,
        0x12345678,0x87654321,0x7fff8000,0x00ff01ff]


def baseline(p):
    """第 24 点先跑齐 28 条基础指令，包含小端字节合并、转发和跳转返回。"""
    p.li(1,0x80000001);p.emit('addi',2,0,-3)
    for name,dst in [('add',3),('sub',4),('and',5),('or',6),('slt',7),('sltu',8)]:
        p.emit(name,dst,1 if name!='sub' else 0,2)
    p.emit('andi',9,2,0xff80);p.emit('sw',6,0x600,0)
    p.emit('sb',1,0x601,0);p.emit('sh',2,0x602,0)
    p.emit('lb',11,0x603,0);p.emit('lh',12,0x602,0);p.emit('lw',13,0x600,0)
    for name in ('mult','multu','div','divu'):
        p.emit(name,1,2 if name!='divu' else 4);p.emit('mfhi',14);p.emit('mflo',15)
    p.emit('mthi',1);p.emit('mtlo',2);p.emit('mfhi',14);p.emit('mflo',15)
    p.emit('beq',0,0,'base_equal');p.emit('ori',16,0,0x16);p.emit('ori',17,0,0xbad)
    p.label('base_equal');p.emit('bne',1,2,'base_different');p.emit('ori',18,0,0x18)
    p.emit('ori',19,0,0xbad);p.label('base_different')
    p.emit('jal','base_sub');p.emit('add',23,31,0)
    p.emit('beq',0,0,'base_finish');p.nop()
    p.label('base_sub');p.emit('add',24,31,0);p.emit('jr',31);p.nop();p.label('base_finish')


def arithmetic(spec,k):
    p=Program(spec);rng=random.Random(0x600000+int(spec['id'][1:])*100+k)
    if k==23:baseline(p)
    name=spec['name'];a=VALUES[k%len(VALUES)] if k<18 else rng.getrandbits(32)
    b=VALUES[(k*5+3)%len(VALUES)] if k<18 else rng.getrandbits(32)
    if name in ('sbc','bmax'):
        a=[0x80ff01e0,0x01020408,0x80808080,0xff0000ff,0x7f80ff01,0x00000000,0xffffffff,0x11224488][k%8] if k<16 else a
        b=(b&~1)|(k&1)
    rs,rt,rd=3,5,[7,3,5,0,31,7][k//4]
    if k==14:rs=rt=3;a=b
    if k==15:rs=0;a=0
    p.li(31,0x13572468)
    p.li(rt,b)
    p.producer(rs,a,k%4)
    if k%2 and rt!=rs:p.producer(rt,b,k%4)
    p.nop((k//4)%3)
    p.custom(rd,rs) if name in ('clz','ctz') else p.custom(rd,rs,rt)
    p.observe(rd,k)
    if k==22:
        # 新指令位于标准分支的延迟槽。
        p.emit('beq',0,0,'slot_end')
        p.custom(8,rs) if name in ('clz','ctz') else p.custom(8,rs,rt)
        p.label('slot_end');p.observe(8)
    if k==23:
        for i in range(32):
            p.li(rs,1<<i);p.custom(7,rs) if name in ('clz','ctz') else p.custom(7,rs,rt)
            p.emit('add',9,7,0)
    p.finish();return p


def memory(spec,k):
    p=Program(spec);rng=random.Random(0x660000+int(spec['id'][1:])*100+k)
    if k==23:baseline(p)
    name=spec['name'];word=VALUES[k%len(VALUES)] if k<18 else rng.getrandbits(32)
    if name=='lwld':word=[0,0x2ffc,0x3000,0x3001,0x3002,0x3004,0xfffffffc,0xffffffff][k%8]
    if name in ('lhonez','lhneg','lhsh'):
        h=[0,0xffff,0x00ff,0x01ff,0x8000,0x7fff,0x8001,0xaaaa,0x5555,0x80ff,0x0001,0xff00][k%12]
        word=(h<<16)|h
    if name in ('lhsb','lbnez'):word=[0,0x80ff7f01,0xff008000,0x00807fff,0xffffffff,0x01010101][k%6]
    base,rt=3,5
    if k==12:rt=0
    if k==13:rt=31
    if k==14:rt=base
    if k==15:base=0
    old=VALUES[(k*7+1)%len(VALUES)]
    if name in ('lwm','lwer','lwxor','lwprime') and k<16:
        # 定向覆盖目的 0、31、偶数、奇数；完整集合在第 24 点内覆盖。
        desired=[0,1,2,3,4,5,7,11,13,17,19,23,29,30,31,16][k]
        old=(word-desired)&MASK if name=='lwm' else ((desired-word)&MASK if name=='lwer' else word^desired)
    if name=='lwmx':old=word if k%4==0 else old
    if name=='shodd':old=[0,1,0x8000,0xffff,0x12345679,0x12345678][k%6]
    lane=k%4
    if name in ('lhonez','lhneg','shodd'):lane&=2
    if name in ('lwld',):lane=0
    address=0x100+lane
    offset=[0,4,-4,32767,-32768,1,-1,12][k%8]
    base_value=(address-offset)&MASK
    if base==0:offset=address
    if rt==base:old=base_value
    p.li(31,0x31415926);p.li(6,word);p.emit('sw',6,0x100,0)
    p.li(rt,old);p.producer(base,base_value,k%4)
    if k%2 and rt!=base:p.producer(rt,old,k%4)
    p.nop((k//4)%3)
    p.custom(rt,offset,base)
    # 这部分只负责挑选紧邻消费者，不生成参考答案。
    old_value=0 if rt==0 else old
    half=(word>>(16*(lane//2)))&65535;byte=(word>>(8*lane))&255
    actual=rt
    if name=='lwld':actual=31 if word>=0x3000 and word&3==0 else rt
    elif name in ('lhsb','lhsh'):actual=rt # 取消写入时紧接着读旧 rt，检查错误转发
    elif name=='lhonez':actual=rt if ones(half)>8 else 31
    elif name=='lwm':actual=(word-old_value)&31
    elif name=='lwmx':actual=5 if signed(word)>signed(old_value) else 4
    elif name=='lwer':actual=(word+old_value)&30
    elif name=='lpx':actual=max([0]+[n for n in PRIMES if n<=(word&31)])
    elif name=='lbnez':actual=rt # 字节为零时也要检查旧 rt 没被转发数据覆盖
    elif name=='lhneg':actual=31 if half&32768 else rt
    elif name=='lwxor':actual=(word^old_value)&31
    elif name=='lwcmp':actual=rt if word>old_value else base
    elif name=='lwprime':actual=max([0]+[n for n in PRIMES if n<=((word^old_value)&31)])
    candidate=actual if k%4 else ((actual+1)&31)
    p.observe(candidate,k)
    for reg in range(32):p.emit('sw',reg,0x900+4*reg,0)
    p.emit('lw',10,0x100,0)
    if k==22:
        p.emit('beq',0,0,'slot_end');p.custom(rt,offset,base)
        p.label('slot_end');p.emit('lw',11,0x100,0)
    if k==23:
        for i in range(32):
            val=0x76543200|i
            p.li(6,val);p.emit('sw',6,0x180,0)
            # 固定比较数为 0 使目的号覆盖可达集合。
            p.emit('ori',5,0,0);p.custom(5,0x180,0);p.emit('add',12,i,0)
    p.finish();return p


def mdu(spec,k):
    p=Program(spec);rng=random.Random(0x6d0000+int(spec['id'][1:])*100+k)
    if k==23:baseline(p)
    name=spec['name'];a=VALUES[k%len(VALUES)] if k<18 else rng.getrandbits(32)
    b=VALUES[(k*3+5)%len(VALUES)] if k<18 else rng.getrandbits(32)
    if name in ('bds','fdiv','divabs'):
        b=b or 3
        if name=='bds':a=a or 1
        if a==0x80000000 and b==0xffffffff:b=3
    if name=='fmultu':
        a,b=[(6,7),(0x10000,0x10000),(0x80000001,3),(0xffffffff,0xffffffff),
             (0x80000000,2),(0xffffffff,0x80000001),(0,0xffffffff),(0x7fffffff,0x10001)][k%8]
    hi,lo=[(0,0),(0xffffffff,0xffffffff),(0,0xffffffff),(0x80000000,0),(0x12345678,0x89abcdef),(0x7fffffff,0xffffffff)][k%6]
    p.li(20,hi);p.emit('mthi',20);p.li(21,lo);p.emit('mtlo',21)
    rs,rt=3,5
    if k==15:rs=rt=3;a=b
    p.li(rt,b);p.producer(rs,a,k%4)
    if k%2 and rs!=rt:p.producer(rt,b,k%4)
    p.nop((k//4)%3)
    if 12<=k<18:
        p.emit('multu' if k&1 else 'divu',3,5)
        # 普通指令必须能在 Busy 期间通过。
        for i in range(k%3):p.emit('ori',22,0,i+1);p.emit('sw',22,0xa00+4*i,0)
    def custom():p.custom() if name in ('shl','mneg') else p.custom(rs,rt)
    custom()
    if k%3==1:
        p.emit('ori',22,0,0x55);p.emit('sw',22,0xa20,0)
    if k%3==2:p.nop(2)
    p.emit('mfhi',7);p.emit('mflo',8);p.observe(7,k);p.observe(8,k+1)
    if k==20:
        p.emit('mthi',3);custom();p.emit('mfhi',9);p.emit('mflo',10)
    if k==21:
        custom();p.emit('mtlo',5);p.emit('mfhi',9);p.emit('mflo',10)
    if k==22:
        p.emit('beq',0,0,'slot_end');custom();p.label('slot_end')
        p.emit('mfhi',9);p.emit('mflo',10)
    if k==23:
        for _ in range(24):custom();p.emit('mfhi',9);p.emit('mflo',10)
    p.finish();return p


def branch(spec,k):
    p=Program(spec);name=spec['name'];rs,rt,rd=3,5,7
    if k==23:baseline(p)
    a=VALUES[k%len(VALUES)];b=VALUES[(k+3)%len(VALUES)]
    p.li(31,0x13572468)
    backward=k>=20
    if backward:
        p.emit('beq',0,0,'launch');p.nop();p.label('taken')
        p.emit('ori',25,0,0x1111);p.emit('beq',0,0,'end');p.nop();p.label('launch')
    if name in ('jap','jsp'):
        p.producer(29,0x200,k%4);p.nop((k//4)%3)
    elif name in ('bgezalr','bgezalx'):
        a=[0,1,0xffffffff,0x80000000,0x7fffffff,-2][k%6]
        if k==14:rt=31
        p.label_value(rt,'taken');p.producer(rs,a,k%4)
        if k%2:
            # 从内存生产目标，覆盖目标和条件的 D 级 load 冒险。
            p.emit('sw',rt,0x440,0);p.emit('lw',rt,0x440,0)
        p.nop((k//4)%3)
        if name=='bgezalr':rd=[7,rt,rs,0,31,7][k//4]
    elif name=='bezal':
        b=[0,1,0,0xffffffff,0,0x80000000][k%6]
        if k==14:rs=31
        p.label_value(rs,'taken');p.producer(rt,b,k%4)
        if k%2:p.emit('sw',rs,0x440,0);p.emit('lw',rs,0x440,0)
        p.nop((k//4)%3)
    else:
        if name=='jabs':a,b=[(0,0),(-2,3),(3,-2),(-1,1),(0x7fffffff,0x80000000),(0x80000000,0)][k%6]
        if name=='jmv':a,b=[(0,0),(5,2),(0xffffffff,1),(0x80000000,0x80000002),(0xffffffff,3),(9,7)][k%6]
        if name=='bparal':a,b=[(0,0),(0,1),(0xffffffff,0),(0xaaaaaaaa,0x55555555),(0x80000000,0),(1,2)][k%6]
        p.li(rt,b);p.producer(rs,a,k%4)
        if k%2:p.producer(rt,b,k%4)
        p.nop((k//4)%3)
    if name=='blezalc':p.custom(rs,'taken')
    elif name=='bgezalr':p.custom(rd,rs,rt)
    elif name in ('bezal','bgezalx'):p.custom(rs,rt)
    elif name in ('jap','jsp'):p.custom('taken')
    elif name in ('jabs','jmv'):
        extra=(abs((a if a<0x80000000 else a-0x100000000)-(b if b<0x80000000 else b-0x100000000))&0x3fffffff) if name=='jabs' else (((a+b)&MASK)>>1)&0x3fffffff
        p.custom(rs,rt,'taken',extra)
    elif name=='bparal':p.custom(rs,rt,'taken',0)
    # 三种延迟槽消费者：计算、内存写数据、MDU 输入。
    link=29 if name in ('jap','jsp') else (rd if name=='bgezalr' else 31)
    if 12<=k<16:p.emit('sw',link,0xb10,0)
    elif 16<=k<20:p.emit('mtlo',link)
    else:p.emit('add',23,link,0)
    p.emit('ori',25,0,0x2222);p.emit('beq',0,0,'end');p.nop()
    if not backward:p.label('taken');p.emit('ori',25,0,0x1111)
    p.label('end')
    if 16<=k<20:p.emit('mflo',23)
    p.emit('sw',25,0xb00,0);p.emit('sw',23,0xb04,0)
    p.emit('sw',31,0xb08,0)
    if name in ('jap','jsp'):p.emit('lw',11,0x200 if name=='jap' else 0x1fc,0)
    p.finish();return p


def bits(spec,original=False):
    form,n=spec['original'] if original and spec['original'] else spec['encoding']
    name=spec['name']
    if form=='J':return f'{n:06b} target26'
    if form=='I':return f'{n:06b} '+('rs 00000 offset16' if name=='blezalc' else 'base rt offset16' if spec['kind'] in ('load','store') else 'rs rt offset16')
    fields='rs rt rd' if name in ('bgezalr','sbc','crt','bmax') else 'rs 00000 rd' if name in ('clz','ctz') else '00000 00000 00000' if name in ('shl','mneg') else 'rs rt 00000'
    return '000000 '+fields+f' 00000 {n:06b}'


COMMON='''每题独立，以课程 P6 的 28 条指令为基础，只添加当前题指令。顶层和外置存储器端口保持课程要求，不能在 CPU 源码里打印日志。复位后 PC 为 0x3000，通用寄存器、HI、LO 清零。IM 为 4096 个字，DM 为 3072 个字。

编码从高位向低位书写。R 型各字段依次为：操作码 6 位、rs 5 位、rt 5 位、rd 5 位、shamt 5 位、funct 6 位。I 型依次为：操作码 6 位、rs 5 位、rt 5 位、立即数 16 位；访存题的 base 占 rs 字段。J 型依次为：操作码 6 位、target 26 位。编码中直接写出的二进制位必须保持不变。

操作栏使用常见 Verilog 表达指令行为：GRF 是 32 个通用寄存器，DM 是按字编号的外部数据存储器，PC 是当前指令地址。局部变量和循环都在操作栏中声明，不使用自定义数学缩写。操作栏用于定义功能，不要求直接粘贴进某一级流水线。

所有源值取本条指令写入之前的值。写 0 号寄存器被丢弃。32 位或 64 位赋值自然保留相应低位。字节编号采用小端方式，地址低两位为 0 时对应整字最低字节。

所有控制转移都执行一个延迟槽。操作栏对 PC 的赋值表示延迟槽执行完后继续执行的地址。寄存器跳转用旧目标值，槽里的指令可以读到新的链接值。槽内不放控制转移指令。

没有特别说明时，字访问四字节对齐，半字访问两字节对齐；允许不对齐的题会明确写出取字方式。测试地址均在合法范围内，除数非零，有符号除法不测试 0x80000000 除以 -1。

所有读取或修改 HI、LO 的指令，都必须等待先前乘除运算完成。多周期运算启动后以 Busy 表示规定周期，结果提交后才解除；普通指令在不发生数据依赖时可以继续执行。单周期的 HI、LO 操作不启动多周期计时。

每题 24 个独立复位测试点，编号 01 至 24。往年题保留现有工作区练习编码；有原平台题面存档的题同时列出原编码，评测时可以切换。模拟题编码只对本题有效。'''


def booklet(group):
    historical=group=='Q'
    title='北航计组 P6 往年题目册' if historical else 'P6 模拟上机题目册（15 题）'
    intro='收录原有的 24 道历史资料改编练习。9 道具有平台题面存档，其余来自文字回忆；补全规则在各题“其他”中说明，来源记录另附。' if historical else '以下 15 道为新编模拟题，考点限定在已有往年题和课程指令涉及的范围内，不作为历史原题。'
    text=f'# {title}\n\n版本 2.0，2026-11-20。{intro}\n\n## 公共说明\n\n{COMMON}\n'
    for s in PROBLEMS:
        if not s['id'].startswith(group):continue
        text+=f"\n## {s['id']}　{s['name']}\n\n编码（本地练习）：`{bits(s)}`。\n"
        if s['original']:text+=f"\n编码（平台存档）：`{bits(s,True)}`。\n"
        text+=f"\n格式：`{s['format']}`。\n\n描述：{s['description']}\n\n操作：\n\n```verilog\n{s['rtl']}\n```\n\n其他：{s['other'] or '按公共说明执行。'}"
        if historical:text+=f" 题源：{s['source']}，详见《P6_历年课上题_来源索引》。"
        text+='\n'
    return text


def main():
    manifest={};count=0
    for spec in PROBLEMS:
        cases=[];folder=ROOT/'tests'/('往年题' if spec['id'].startswith('Q') else '模拟题')/spec['id']
        for k in range(24):
            p=({'alu':arithmetic,'load':memory,'store':memory,'mdu':mdu,'branch':branch}[spec['kind']])(spec,k)
            words=p.encode();expected=reference(words,spec['id'])
            assert expected['custom_hits']>0
            case_id=f'{k+1:02d}';dest=folder/case_id;dest.mkdir(parents=True,exist_ok=True)
            # 完整填满 IM，ISE 的 readmemh 不会留下未知的尾部。
            code=''.join(f'{w:08x}\n' for w in words+[0]*(4096-len(words)))
            (dest/'code.txt').write_bytes(code.encode('ascii'))
            (dest/'program.lst').write_text(p.listing(),encoding='utf-8')
            (dest/'expected.log').write_bytes(('\n'.join(expected['events'])+'\n').encode('ascii'))
            if spec['original']:
                orig=p.encode(True);other=reference(orig,spec['id'],True)
                assert other['events']==expected['events']
                (dest/'code_original.txt').write_bytes(''.join(f'{w:08x}\n' for w in orig+[0]*(4096-len(orig))).encode('ascii'))
            category=['功能与源数据转发','间隔一条指令及写后读','间隔两条指令及写回','寄存器别名与最新值优先','条件路径与目的选择','组合与周期压力'][k//4]
            # 常规用例按两倍退休数留出不同合规流水线实现的余量。
            cycles=expected['steps']*2+expected['latency']+24
            if k==23 and spec['kind']=='mdu':cycles=expected['steps']+expected['latency']+26
            data=dict(id=case_id,title=category,cycles=cycles,steps=expected['steps'],custom_hits=expected['custom_hits'],
                      finish_pc=expected['finish_pc'],focus=p.focus,sha256=hashlib.sha256((dest/'code.txt').read_bytes()).hexdigest())
            (dest/'case.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            cases.append(data);count+=1
        (folder/'cases.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        manifest[spec['id']]={**spec,'path':folder.relative_to(ROOT).as_posix(),'cases':cases,'encoding_bits':bits(spec),
                              'original_bits':bits(spec,True) if spec['original'] else None}
        print(spec['id'],len(cases),flush=True)
    (ROOT/'cases.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for group,name in [('Q','P6_历年课上题_题目册.md'),('M','P6_模拟上机题目册.md')]:
        content=booklet(group);(ROOT/name).write_text(content,encoding='utf-8')
    print('TOTAL',count)


if __name__=='__main__':main()
