"""P5 独立指令级参考语义；输入仅为机器码。"""
from problems import BY_ID
MASK=0xffffffff


def signed(x,bits=32):
    x&=(1<<bits)-1
    return x-(1<<bits) if x>>(bits-1) else x


def ones(x):return bin(x&MASK).count('1')
def leading(x,bit):
    count=0
    for i in range(31,-1,-1):
        if (x>>i)&1!=bit:break
        count+=1
    return count


def load_effect(name,word,old,rt,base,lane,pc):
    half=(word>>(16*((lane>>1)&1)))&65535
    byte=(word>>(8*lane))&255
    if name=='lwso':
        total=signed(old)+signed(word)
        return (31,total&MASK) if -0x80000000<=total<=0x7fffffff else (None,0)
    if name=='lrm':return word&31,old
    if name=='lhogez':return (rt,half) if ones(half)>8 else (31,pc+4)
    if name in ('lbget','lbsel'):return (base if byte&128 else rt),signed(byte,8)&MASK
    if name=='lwrev':return word&15,rt
    if name=='lwoc':return (rt if word>>31 else word&15),word
    if name=='ccs':
        hi,lo=ones(word>>16),ones(word&65535)
        return (31 if hi>lo else hi),word^old
    if name=='lhp':
        mixed=word^old
        dst=max(0,mixed.bit_length()-1) if mixed>>16==mixed&65535 else 31
        return dst,word
    if name=='lweo':return (31 if word&1 else rt),word
    if name=='lwtxr':return max(word&31,rt),word
    if name=='lwnz':return (rt,word) if word else (None,0)
    if name=='lwgate':
        total=signed(word)+signed(old)
        return (rt,total&MASK) if -0x80000000<=total<=0x7fffffff and total&1 else (None,0)
    if name=='lwxsel':
        mixed=word^old
        return (rt if mixed>>31 else mixed&15),word
    raise ValueError(name)


def reference(words,problem,original=False,max_steps=10000):
    if original:raise ValueError('P5 题均为本册练习编码，没有已核实的原平台编码模式')
    spec=BY_ID[problem];form,code=spec['encoding'];name=spec['name']
    r=[0]*32;mem=[0]*3072;events=[];pc=0x3000;pending=None;hits=0
    for step in range(max_steps):
        if pc&3 or not 0x3000<=pc<0x3000+4*len(words):raise ValueError('非法取指 '+hex(pc))
        ins=words[(pc-0x3000)//4]
        op,rs,rt,rd,fn=ins>>26,(ins>>21)&31,(ins>>16)&31,(ins>>11)&31,ins&63
        a,b,imm=r[rs],r[rt],signed(ins&65535,16)
        dst,value,target,annul=None,0,None,False
        custom=(op==spec['r_opcode'] and fn==code) if form=='R' else op==code
        if custom:
            hits+=1
            if spec['kind']=='load':
                address=(a+imm*(4 if name in ('lwoc','lhp','lwxsel') else 1))&MASK
                if not 0<=address<0x3000:raise ValueError('数据地址越界 '+hex(address))
                if name not in ('lbget','lbsel','lhogez') and address&3:raise ValueError('字未对齐')
                if name=='lhogez' and address&1:raise ValueError('半字未对齐')
                old=r[31] if name=='lwso' else b
                dst,value=load_effect(name,mem[address>>2],old,rt,rs,address&3,pc)
            elif spec['kind'] in ('alu','alui'):
                dst=rd if form=='R' else rt
                if name=='cco':value=ones(a&b)
                elif name=='cmco':value=max(map(len,format(a,'032b').split('0')))
                elif name=='swc':
                    shift=b&31
                    value=a if not shift else ((a<<shift)|(a>>(32-shift)) if b&1 else (a>>shift)|(a<<(32-shift)))
                elif name=='addei':
                    extended=0xffff0000|(ins&65535);total=signed(a)+signed(extended)
                    value=total if -0x80000000<=total<=0x7fffffff else extended
                elif name=='fz':
                    value=a;remaining=b
                    for i in range(32):
                        if not value>>i&1 and remaining:value|=1<<i;remaining-=1
                elif name=='xe':value=a^(b&0x55555555)
                elif name=='addoi':
                    total=signed((a+imm)&MASK)
                    if total==-0x80000000:raise ValueError('addoi 输入不在本册定义范围')
                    neg=-total;value=abs(neg)|(0x80000000 if neg<0 else 0)
                elif name=='ccc':value=(a&0xffff0000)|(b&65535) if leading(a,0)>leading(b,1) else (b&0xffff0000)|(a&65535)
                elif name=='dsc':dst,value=rs,(b<<((ins>>11)&31))^(signed(b)>>(ins&31))
                elif name=='taddu':value=a+b
                elif name=='slt':value=int(signed(a)<signed(b))
                elif name=='clo':value=leading(a,1)
                elif name=='movz':dst,value=(rd if b==0 else None),a
                elif name=='pcxor':value=ones(a^b)
                elif name=='bwin':value=signed((a>>(b&31))&255,8)
                elif name=='sathi':value=min(0x7fffffff,max(-0x80000000,signed(a)+imm))
                else:raise ValueError(name)
            else:
                relative=(pc+4+imm*4)&MASK;total=signed(a)+signed(b)
                taken=False;link=None;link_always=False;annul_false=False
                if name=='bgezall':taken=signed(a)>=0;link=31;link_always=True;annul_false=True
                elif name=='blezalc':taken=signed(a)<=0;link=31
                elif name=='bonall':taken=total==0;link=31;link_always=True;annul_false=True
                elif name=='bltzalx':taken=signed(a)<0;relative=(relative+4*(1<<(b&3)))&MASK;link=31;link_always=True
                elif name=='bsveall':taken=min(signed(a),signed(b))%2==0;link=31;link_always=True;annul_false=True
                elif name=='jtl':taken=relative<((a+b)&MASK);link=31;link_always=True;annul_false=True
                elif name=='cjoc':taken=((a>>(ins&7))&255)>21;link=rt;annul_false=True
                elif name=='bloc':taken=leading(a,1)>(b&63);link=31;link_always=True
                elif name=='blezals':taken=signed(a)<=0;link=31;link_always=True
                elif name=='bovc':taken=not -0x80000000<=total<=0x7fffffff;link=31
                elif name=='bgtzl':taken=signed(a)>0;annul_false=True
                elif name=='bopz':taken=total<0;annul_false=True
                elif name=='bmeqal':taken=(a&65535)<=(b&65535);link=31
                elif name=='joddal':taken=bool(a&1);link=31;link_always=True;annul_false=True
                elif name=='blztal':taken=signed(a)<0;relative=(pc+4+(imm<<(2+(b&3))))&MASK;link=31
                else:raise ValueError(name)
                if link is not None and (taken or link_always):dst,value=link,pc+8
                target=relative if taken else ((a+b)&MASK if name=='jtl' else (b+(a&12))&MASK if name=='joddal' else pc+8)
                annul=not taken and annul_false
        elif ins==0:pass
        elif op==0:
            if fn in (0x20,0x21):dst,value=rd,a+b
            elif fn in (0x22,0x23):dst,value=rd,a-b
            elif fn==8:target=a
            else:raise ValueError('基础指令之外的 R 编码 '+hex(ins))
        elif op==0xf:dst,value=rt,(ins&65535)<<16
        elif op==0xd:dst,value=rt,a|(ins&65535)
        elif op in (0x23,0x2b):
            address=(a+imm)&MASK
            if address&3 or not 0<=address<0x3000:raise ValueError('基础字访存地址错误 '+hex(address))
            if op==0x23:dst,value=rt,mem[address>>2]
            else:
                mem[address>>2]=b;events.append(f'@{pc:08x}: *{address:08x} <= {b:08x}')
        elif op==4:target=(pc+4+imm*4)&MASK if a==b else pc+8
        elif op in (2,3):
            target=((pc+4)&0xf0000000)|((ins&0x3ffffff)<<2)
            if op==3:dst,value=31,pc+8
        else:raise ValueError('无法识别编码 '+hex(ins))
        if dst:
            r[dst]=value&MASK;events.append(f'@{pc:08x}: ${dst} <= {value&MASK:08x}')
        if ins==((0xd<<26)|(30<<16)|0xcafe):
            return dict(events=events,steps=step+1,finish_pc=pc,custom_hits=hits)
        if pending is not None:
            if target is not None:raise ValueError('控制指令出现在延迟槽')
            pc,pending=pending,None
        elif annul:pc=target
        else:pc=(pc+4)&MASK;pending=target
    raise ValueError('程序未结束')
