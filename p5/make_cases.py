"""生成往年题；保留原模拟题机器码、日志及周期限制。"""
from pathlib import Path
import hashlib,json,random
from problems import PROBLEMS,BY_ID
from model import reference,load_effect,signed,MASK

ROOT=Path(__file__).resolve().parent
VALUES=[0,0xffffffff,0x80000000,0x7fffffff,1,2,0xffff0000,0x0000ffff,0x80ff01e0,0x01020408,0xaaaaaaaa,0x55555555,0x10000,0x80000001,0x12345678,0x87654321,0x7fff8000,0x00ff01ff]


class Program:
    def __init__(self,spec):self.spec=spec;self.rows=[];self.labels={};self.focus=[]
    @property
    def pc(self):return 0x3000+4*len(self.rows)
    def emit(self,name,*args):self.rows.append((name,args));return self.pc-4
    def label(self,name):self.labels[name]=self.pc
    def li(self,reg,value):self.emit('lui',reg,(value&MASK)>>16);self.emit('ori',reg,reg,value&65535)
    def label_value(self,reg,label,addend=0):self.emit('labelhi',reg,label,addend);self.emit('labello',reg,label,addend)
    def nop(self,n=1):
        for _ in range(n):self.emit('nop')
    def producer(self,reg,value,mode):
        if mode==1:self.li(28,value);self.emit('sw',28,0x480,0);self.emit('lw',reg,0x480,0)
        elif mode==2:self.li(28,value);self.emit('add',reg,28,0)
        elif mode==3:self.li(reg,~value);self.li(reg,value)
        else:self.li(reg,value)
    def custom(self,*args):self.focus.append(self.pc);self.emit(self.spec['name'],*args)
    def observe(self,reg,k=0):
        if k%3==0:self.emit('add',24,reg,0)
        elif k%3==1:self.emit('sw',reg,0x800,0)
        else:
            label='observe_'+str(len(self.rows));self.emit('beq',reg,0,label)
            self.emit('ori',26,0,0x56);self.emit('ori',27,0,0x57);self.label(label)
        self.emit('sw',reg,0x804,0)
    def finish(self):
        self.nop(3);self.emit('ori',30,0,0xcafe);self.label('halt');self.emit('beq',0,0,'halt');self.nop()
    def encode(self):
        words=[];name_custom=self.spec['name'];form,code=self.spec['encoding']
        for i,(name,args) in enumerate(self.rows):
            pc=0x3000+4*i
            if name=='nop':word=0
            elif name in ('labelhi','labello'):
                dst,label,addend=args;value=(self.labels[label]+addend)&MASK
                word=(15<<26)|(dst<<16)|(value>>16) if name=='labelhi' else (13<<26)|(dst<<21)|(dst<<16)|(value&65535)
            elif name in ('add','sub'):
                rd,rs,rt=args;word=(rs<<21)|(rt<<16)|(rd<<11)|(0x20 if name=='add' else 0x22)
            elif name=='lui':word=(15<<26)|(args[0]<<16)|(args[1]&65535)
            elif name=='ori':rt,rs,imm=args;word=(13<<26)|(rs<<21)|(rt<<16)|(imm&65535)
            elif name in ('lw','sw'):rt,off,rs=args;word=((35 if name=='lw' else 43)<<26)|(rs<<21)|(rt<<16)|(off&65535)
            elif name=='beq':
                rs,rt,label=args;off=(self.labels[label]-pc-4)//4;word=(4<<26)|(rs<<21)|(rt<<16)|(off&65535)
            elif name in ('j','jal'):word=((2 if name=='j' else 3)<<26)|(self.labels[args[0]]>>2)
            elif name=='jr':word=args[0]<<21|8
            elif name==name_custom:
                if self.spec['kind']=='load':rt,off,rs=args;word=(code<<26)|(rs<<21)|(rt<<16)|(off&65535)
                elif self.spec['kind']=='branch':
                    rs,rt,label,adjust=args;off=(self.labels[label]-pc-4)//4-adjust
                    if name=='blztal':
                        assert off%(1<<adjust)==0;off//=1<<adjust
                    assert -32768<=off<=32767
                    word=(code<<26)|(rs<<21)|(rt<<16)|(off&65535)
                elif form=='R':
                    rd,rs,rt=args;word=(self.spec['r_opcode']<<26)|(rs<<21)|(rt<<16)|(rd<<11)|code
                elif name=='dsc':
                    destination,source,imm=args;word=(code<<26)|(destination<<21)|(source<<16)|(imm&65535)
                else:
                    rt,rs,imm=args;word=(code<<26)|(rs<<21)|(rt<<16)|(imm&65535)
            else:raise ValueError(name)
            words.append(word)
        return words
    def listing(self):return '\n'.join(f'{0x3000+i*4:08x}  {name} '+', '.join(map(str,args)) for i,(name,args) in enumerate(self.rows))+'\n'


def baseline(p):
    p.li(1,0x80000001);p.li(2,0xffffffff);p.emit('add',3,1,2);p.emit('sub',4,0,2)
    p.emit('sw',3,0x600,0);p.emit('lw',5,0x600,0)
    p.emit('beq',5,3,'base_taken');p.emit('ori',6,0,0x16);p.emit('ori',7,0,0xbad);p.label('base_taken')
    p.emit('jal','base_sub');p.emit('add',8,31,0);p.emit('beq',0,0,'base_end');p.emit('ori',9,0,9)
    p.label('base_sub');p.emit('add',10,31,0);p.emit('jr',31);p.nop();p.label('base_end')


def arithmetic(spec,k):
    p=Program(spec);name=spec['name'];rng=random.Random(0x550000+int(spec['id'][1:])*100+k)
    if k==23:baseline(p)
    a=VALUES[k%18] if k<18 else rng.getrandbits(32);b=VALUES[(k*5+3)%18] if k<18 else rng.getrandbits(32)
    if name in ('cco','cmco','clo','ccc'):a=[0,MASK,0x80000000,0x7fffffff,0xf0f0f0f0,0x80000001,0x00000037,0x00001234][k%8]
    if name=='cco' and k==1:b=MASK
    if name=='ccc':b=[MASK,0,0xf0005678,0x8000ffff,0x7fffffff,0xffff0000][k%6]
    if name=='fz':b=[0,1,2,31,32,33,MASK,0x80000000][k%8]
    if name=='swc':b=[0,1,2,31,32,33,0xfffffffe,MASK][k%8]
    if name=='movz':b=0 if k%2==0 else b or 1
    rs,rt,rd=3,5,[7,3,5,0,31,7][k//4]
    if k==14:rs=rt=3;a=b
    if k==15:rs=0;a=0
    p.li(31,0x13572468)
    if rd not in (rs,rt):p.li(rd,0xdeadbeef)
    p.li(rt,b);p.producer(rs,a,k%4)
    if k%2 and rs!=rt:p.producer(rt,b,k%4)
    p.nop((k//4)%3)
    if spec['kind']=='alui':
        imm=[0,1,-1,32767,-32768,0x1234,0x8001,0xffff][k%8]
        if name=='dsc':
            imm=(([0,1,31,4,16,30][k%6])<<11)|((k*7&63)<<5)|[0,1,31,16,4,30][k%6]
            p.custom(rd,rt,imm);destination=rd # 指令 rs 字段是目的，rt 字段是源。
        else:
            if name=='addoi' and (a+signed(imm,16))&MASK==0x80000000:p.li(rs,a^1)
            p.custom(rd,rs,imm);destination=rd
    else:p.custom(rd,rs,0 if name in ('cmco','clo') else rt);destination=rd
    p.observe(destination,k)
    if k==22:
        p.emit('beq',0,0,'slot_end')
        if spec['kind']=='alui':p.custom(8,rt if name=='dsc' else rs,imm)
        else:p.custom(8,rs,0 if name in ('cmco','clo') else rt)
        p.label('slot_end');p.observe(8)
    if k==23:
        for i in range(33):
            p.li(rs,((1<<min(i,32))-1)&MASK);p.li(rt,i)
            if spec['kind']=='alui':p.custom(7,rt if name=='dsc' else rs,0x0801 if name=='dsc' else (2 if name=='addoi' and i==31 else 1))
            else:p.custom(7,rs,0 if name in ('cmco','clo') else rt)
            p.emit('add',9,7,0)
    p.finish();return p


def memory(spec,k):
    p=Program(spec);name=spec['name'];rng=random.Random(0x558000+int(spec['id'][1:])*100+k)
    if k==23:baseline(p)
    word=VALUES[k%18] if k<18 else rng.getrandbits(32)
    if name=='lhogez':
        h=[0,0xffff,0x00ff,0x01ff,0x8000,0x7fff,0x80ff,0x5555][k%8];word=(h<<16)|h
    if name in ('lbget','lbsel'):word=[0,0x80ff7f01,0xff008000,0x00807fff,MASK,0x01010101][k%6]
    if name=='ccs':word=[0,0xffff0000,0x0000ffff,0xffffffff,0x00010003,0x80000000,0x7fff0001,0x00010001][k%8]
    old=VALUES[(k*7+1)%18]
    if name=='lwso':
        word,old=[(1,0x7fffffff),(1,MASK),(MASK,0x80000000),(0,0x80000000),
                  (0x7fffffff,0x7fffffff),(0x80000000,0x80000000),(3,4),(0x80000000,1)][k%8]
    if name=='lhp':
        half=[0,1,2,0x8000,0xffff,0x10][k%6];word=half|(half<<16);old=0 if k%2 else 0x00010000
    base,rt=3,31 if name=='lwso' else 5
    if k==12 and name!='lwso':rt=0
    if k==13:rt=31
    if k==14 and name!='lwso':rt=base
    if k==15:base=0
    lane=k%4 if name in ('lbget','lbsel') else (k%2)*2 if name=='lhogez' else 0
    address=0x100+lane;off=[0,4,-4,32767,-32768,1,-1,12][k%8]
    factor=4 if name in ('lwoc','lhp','lwxsel') else 1
    base_value=(address-factor*off)&MASK
    if base==0:off=address//factor
    if rt==base:old=base_value
    if name=='lrm' and k<16:word=(word&~31)|[0,1,2,3,4,5,7,11,13,17,19,23,29,30,31,16][k]
    p.li(31,0x31415926);p.li(6,word);p.emit('sw',6,0x100,0)
    p.li(rt,old);p.producer(base,base_value,k%4)
    if k%2 and rt!=base:p.producer(rt,old,k%4)
    p.nop((k//4)%3)
    pc=p.pc;p.custom(rt,off,base)
    destination,_=load_effect(name,word,0 if rt==0 else old,rt,base,lane,pc)
    candidate=rt if destination is None else destination
    p.observe(candidate if k%4 else ((candidate+1)&31),k)
    for reg in range(32):p.emit('sw',reg,0x900+reg*4,0)
    if k==22:
        # 用独立基址避免第一次动态写回破坏第二次的地址。
        p.li(3,0x100);p.emit('beq',0,0,'slot_end');p.custom(rt,0,3);p.label('slot_end');p.observe(rt)
    if k==23:
        for i in range(32):
            val=0x76543200|i
            if name=='lhp':h=0 if i<16 else 1<<(i-16);val=(h<<16)|h
            if name=='ccs':val=(((1<<i)-1)<<16)|65535 if i<=16 else 0xffff0000
            p.li(6,val);p.emit('sw',6,0x180,0);p.li(5,0)
            target=31 if name=='lwso' else (i if name in ('lwrev','lwtxr') else 5)
            if name=='lwso':p.li(31,0)
            p.custom(target,0x180//factor,0)
            actual,_=load_effect(name,val,0,target,0,0,p.pc-4)
            p.emit('add',12,(target if actual is None else actual),0)
    p.finish();return p


def branch(spec,k):
    p=Program(spec);name=spec['name'];rs,rt=3,5
    if k==23:baseline(p)
    p.li(31,0x13572468)
    backward=k>=20 or name=='jtl' and k%3==1
    if backward:
        p.emit('beq',0,0,'launch');p.nop();p.label('taken')
        p.emit('ori',25,0,0x1111);p.emit('beq',0,0,'end');p.nop();p.label('launch')
    a=VALUES[k%18];b=VALUES[(k+3)%18]
    if name=='bonall':a,b=[(0,0),(1,MASK),(0x80000000,0x80000000),(-7,7),(MASK,0),(0x7fffffff,0x80000001)][k%6]
    if name=='bsveall':a,b=[(-2,1),(-1,2),(0,0),(0x80000000,0x7fffffff),(3,8),(4,5)][k%6]
    if name=='bloc':a,b=[(MASK,31),(MASK,32),(MASK,63),(0,0),(0xffff0000,15),(0xffff0000,16)][k%6]
    if name=='bovc':a,b=[(0x7fffffff,1),(0x80000000,MASK),(MASK,1),(0,0),(0x7fffffff,0x7fffffff),(0x80000000,1)][k%6]
    if name=='cjoc':a=[0,21<<4,22<<4,255<<4,MASK,0x80000000][k%6];rt=[5,31,3,0,5,7][k//4]
    if name=='bltzalx':b=k%4
    if name in ('bgezall','blezalc','blezals','bgtzl'):rt=0
    if k==14 and name not in ('jtl','cjoc'):rs=31
    p.li(rt,b)
    if name=='jtl':
        a=[0,4,0xfffffffc,8][k%4];p.producer(rs,a,k%4)
        p.label_value(rt,'taken' if k%3 in (1,2) else 'further',-a)
        if k%2:p.emit('sw',rt,0x440,0);p.emit('lw',rt,0x440,0)
    else:
        p.producer(rs,a,k%4)
        if rt and rt!=rs and k%2:p.producer(rt,b,k%4)
    p.nop((k//4)%3)
    adjust=(1<<(b&3)) if name=='bltzalx' else 0
    p.custom(rs,rt,'taken',adjust)
    link=rt if name=='cjoc' else 31
    if 12<=k<16:p.emit('sw',link,0xb10,0)
    elif 16<=k<20:p.emit('ori',23,link,0)
    else:p.emit('add',23,link,0)
    p.emit('ori',25,0,0x2222);p.emit('beq',0,0,'end');p.nop()
    if not backward:p.label('taken');p.emit('ori',25,0,0x1111)
    if name=='jtl':
        p.emit('beq',0,0,'end');p.nop();p.label('further');p.emit('ori',25,0,0x3333)
    p.label('end');p.emit('sw',25,0xb00,0);p.emit('sw',23,0xb04,0);p.emit('sw',31,0xb08,0)
    p.finish();return p


def bits(spec):
    form,code=spec['encoding'];name=spec['name']
    if form=='R':
        fields='rs 00000 rd' if name in ('cmco','clo') else 'rs rt rd'
        return f"{spec['r_opcode']:06b} {fields} 00000 {code:06b}"
    return f'{code:06b} '+('base 11111 offset16' if name=='lwso' else 'base n offset16' if name=='lwrev' else 'base rt offset16' if spec['kind']=='load' else 'rs 00000 offset16' if name in ('bgezall','blezalc','blezals','bgtzl') else 'rs rt offset16' if spec['kind']=='branch' else 'rs rt imm16')


def booklet(group):
    title={'Q':'P5 往年题','M':'P5 模拟题（沿用原 10 题）','X':'P5 补充练习 BLZTAL'}[group]
    text=f'# {title}\n\n整理版，2026-11-20。Q01—Q29 是历史资料改编；M01—M10 对应旧模拟题 Q01—Q10，X01 对应旧 BLZTAL。每题 24 点。\n\n'
    text+='题号在整合仓库中须加 P5 前缀，例如 P5-Q01 和 P5-M01。所有编码都是本册练习协议，不宣称是历史原编码。本包使用的基础指令为 add、sub、ori、lui、lw、sw、beq、jal、jr、nop；PC 从 0x3000 开始，IM 4096 字、DM 3072 字，GRF 和 DM 复位清零。\n\n'
    text+='顶层为 mips(clk, reset)，IM、DM 在 CPU 内部。GRF 和 DM 按课程要求打印带 PC 的写入日志。GRF 表示通用寄存器，DM 用整字编号，PC 是当前指令地址；操作栏为行为定义，不限制具体流水级。所有源使用写入前的旧值，写 $0 丢弃，固定宽度结果保留低位。\n\n'
    text+='控制指令的 PC 赋值表示处理延迟槽后的地址；是否清空延迟槽以中文描述为准。槽内不安排控制指令。字节按小端选择，普通字访问对齐到四字节，半字对齐到两字节，测试地址均有效。\n\n'
    text+='编码按高位到低位排列。R 型字段宽度依次为 6、5、5、5、5、6 位；I 型为 6、5、5、16 位。base 占 rs 字段。\n'
    for s in PROBLEMS:
        if not s['id'].startswith(group):continue
        text+=f"\n## P5-{s['id']}　{s['name']}\n\n编码：`{bits(s)}`。\n\n格式：`{s['format']}`。\n\n描述：{s['description']}\n\n操作：\n\n```verilog\n{s['rtl']}\n```\n\n其他：{s['other'] or '按公共说明执行。'}"
        if s['source']:text+=f" 题源：{s['source']}，见来源索引。"
        text+='\n'
    return text


def save_case(spec,case_id,words,expected,cycles,focus,title,legacy=None,listing=''):
    category={'Q':'往年题','M':'模拟题','X':'补充练习'}[spec['id'][0]]
    folder=ROOT/'tests'/category/spec['id']/case_id;folder.mkdir(parents=True,exist_ok=True)
    image=''.join(f'{w:08x}\n' for w in words+[0]*(4096-len(words)))
    (folder/'code.txt').write_bytes(image.encode('ascii'))
    (folder/'expected.log').write_bytes(('\n'.join(expected['events'])+'\n').encode('ascii'))
    if not listing:listing=''.join(f'{0x3000+i*4:08x}  {w:08x}\n' for i,w in enumerate(words))
    (folder/'program.lst').write_bytes(listing.encode('utf-8'))
    case=dict(id=case_id,title=title,cycles=cycles,steps=expected['steps'],finish_pc=expected['finish_pc'],focus=focus,
              sha256=hashlib.sha256(image.encode()).hexdigest(),custom_hits=expected['custom_hits'])
    if legacy:case['legacy_id']=legacy
    (folder/'case.json').write_bytes((json.dumps(case,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    return case,folder.parent


def main():
    # 旧模拟题被保留为固定输入，不依赖整理者机器的原目录。
    legacy=json.loads((ROOT/'legacy_cases.json').read_text(encoding='utf-8')) if (ROOT/'legacy_cases.json').exists() else {}
    catalog={}
    for spec in PROBLEMS:
        cases=[]
        for k in range(24):
            case_id=f'{k+1:02d}';key=spec['id']
            if key[0] in ('M','X'):
                old=legacy[key][k];words=old['words'];result=reference(words,key)
                assert result['events']==old['expected'],(key,case_id,'旧标准答案与参考模型不一致')
                case,parent=save_case(spec,case_id,words,result,old['cycles'],[],old['title'],old['id'])
            else:
                p=({'alu':arithmetic,'alui':arithmetic,'load':memory,'branch':branch}[spec['kind']])(spec,k)
                words=p.encode();result=reference(words,key)
                case,parent=save_case(spec,case_id,words,result,result['steps']*2+28,p.focus,
                                      ['功能与紧邻依赖','一条间隔与最新值','两条间隔与写回','源目的重合与零寄存器','条件与取消副作用','延迟槽、后向目标及综合回归'][k//4],listing=p.listing())
            assert result['custom_hits']>0
            cases.append(case)
        catalog[spec['id']]={**spec,'path':parent.relative_to(ROOT).as_posix(),'cases':cases,'encoding_bits':bits(spec),'original_bits':None}
        (parent/'cases.json').write_bytes((json.dumps(cases,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
        print(spec['id'],spec['name'],len(cases),flush=True)
    (ROOT/'cases.json').write_bytes((json.dumps(catalog,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    for group,name in [('Q','P5_往年题目册.md'),('M','P5_模拟题目册.md'),('X','P5_BLZTAL补充题.md')]:
        (ROOT/name).write_bytes(booklet(group).encode('utf-8'))
    print('TOTAL',sum(len(s['cases']) for s in catalog.values()))


if __name__=='__main__':main()
