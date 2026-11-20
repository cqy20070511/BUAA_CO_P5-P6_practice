"""独立的指令级参考模型。只使用编码后的指令，不解释生成器的汇编对象。"""
from problems import BY_ID

MASK = 0xffffffff
PRIMES = (2,3,5,7,11,13,17,19,23,29,31)


def signed(x, bits=32):
    x &= (1 << bits)-1
    return x-(1 << bits) if x >> (bits-1) else x


def ones(x):
    return bin(x & MASK).count('1')


def quotient(a,b):
    if b == 0: raise ValueError('除数为零')
    return (-1 if (a < 0) != (b < 0) else 1)*(abs(a)//abs(b))


def reference(words, problem, original=False, max_steps=10000):
    spec = BY_ID[problem]
    form, code = spec['original'] if original and spec['original'] else spec['encoding']
    r = [0]*32
    mem = bytearray(12288)
    hi = lo = 0
    pc, pending = 0x3000, None
    events, retired, latency = [], 0, 0
    custom_hits = 0
    histogram = {}

    def read(addr, size):
        if addr < 0 or addr+size > len(mem): raise ValueError('读地址越界 '+hex(addr))
        return int.from_bytes(mem[addr:addr+size], 'little')

    def store(addr,size,value):
        if addr < 0 or addr+size > len(mem): raise ValueError('写地址越界 '+hex(addr))
        if size>1 and addr % size: raise ValueError('普通写指令未对齐')
        mem[addr:addr+size] = (value & ((1 << (size*8))-1)).to_bytes(size,'little')
        events.append(f'@{pc:08x}: *{addr & ~3:08x} <= {read(addr & ~3,4):08x}')

    for _ in range(max_steps):
        if pc & 3 or not 0x3000 <= pc < 0x3000+4*len(words):
            raise ValueError('取指地址无效 '+hex(pc))
        ins = words[(pc-0x3000)//4]
        op, rs, rt, rd, fn = ins>>26, (ins>>21)&31, (ins>>16)&31, (ins>>11)&31, ins&63
        a,b,imm = r[rs],r[rt],signed(ins&0xffff,16)
        addr = (a+imm)&MASK
        target = None
        dst, value = 0,0
        is_custom = (op == 0 and fn == code) if form=='R' else op == code
        retired += 1
        if is_custom:
            name = spec['name']; custom_hits += 1
            histogram[name] = histogram.get(name,0)+1
            if spec['kind'] in ('load','store'):
                full = read(addr & ~3,4)
                byte = (full >> (8*(addr&3)))&255
                half = (full >> (16*((addr>>1)&1)))&65535
                dst,value = rt,full
                if name=='lwld': dst = 31 if full>=0x3000 and full&3==0 else rt
                elif name=='lhsb': dst,value = (rt if addr&1==0 else 0),signed(byte,8)
                elif name=='lhsh': dst,value = (rt if addr&1==0 else 0),signed(half,16)
                elif name=='lhonez':
                    dst,value = (rt,signed(half,16)) if ones(half)>8 else (31,pc+4)
                elif name=='lwm': dst=(full-b)&31
                elif name=='lwmx': dst=5 if signed(full)>signed(b) else 4
                elif name=='lwer': dst=(full+b)&30
                elif name=='lpx': dst=max([0]+[p for p in PRIMES if p<=full&31])
                elif name=='lbnez': dst,value=(rt if byte else 0),signed(byte,8)
                elif name=='shodd':
                    dst=0
                    if b&1: store(addr,2,b)
                elif name=='lhneg': dst,value=(31 if half&32768 else rt),signed(half,16)
                elif name=='lwxor': dst=(full^b)&31
                elif name=='lwcmp': dst=rt if full>b else rs
                elif name=='lwprime': dst=max([0]+[p for p in PRIMES if p<=((full^b)&31)])
                else: raise ValueError(name)
            elif spec['kind']=='alu':
                dst=rd
                if name=='clz': value=32-a.bit_length()
                elif name=='ctz': value=32 if not a else (a & -a).bit_length()-1
                elif name=='sbc':
                    v=[(a >> (8*i))&255 for i in range(4)]
                    v.sort(key=ones,reverse=not b&1)
                    value=sum(x << (8*i) for i,x in enumerate(v))
                elif name=='crt':
                    # 每个置位在 32 次循环右移中恰好贡献 0xffffffff。
                    x,y=signed(-ones(a)&MASK),signed(-ones(b)&MASK)
                    value=-1 if x<y else int(x>y)
                elif name=='bmax':
                    v=[(a >> (8*i))&255 for i in range(4)]
                    maximum=max(map(ones,v))
                    indices=[i for i,x in enumerate(v) if ones(x)==maximum]
                    value=signed(v[indices[-1] if b&1 else indices[0]],8)
            elif spec['kind']=='branch':
                target=pc+8
                relative=(pc+4+imm*4)&MASK
                if name=='blezalc' and signed(a)<=0: dst,value,target=31,pc+8,relative
                elif name=='bgezalr':
                    dst,value=rd,pc+8
                    if signed(a)>=0: target=b
                elif name=='bezal' and b==0: dst,value,target=31,pc+8,a
                elif name in ('jap','jsp'):
                    old_sp=r[29]
                    store(old_sp if name=='jap' else old_sp-4,4,pc+8)
                    dst,value=29,old_sp-4
                    target=(pc&0xf0000000)|((ins&0x3ffffff)<<2)
                elif name=='jabs': target=(relative+((abs(signed(a)-signed(b))&0x3fffffff)<<2))&MASK
                elif name=='jmv': target=(relative+((((a+b)&MASK)>>1 &0x3fffffff)<<2))&MASK
                elif name=='bgezalx' and signed(a)>=0: dst,value,target=31,pc+8,b
                elif name=='bparal' and ones(a^b)%2==0: dst,value,target=31,pc+8,relative
            else:
                old=(hi<<32)|lo
                result=None
                active=True
                if name=='multc':
                    active=signed(a)>0
                    if active: result=signed(a)*signed(b)
                elif name in ('msub','madd'): result=old+(-1 if name=='msub' else 1)*signed(a)*signed(b)
                elif name=='bds':
                    numerator,denominator=max(a,b),min(a,b)
                    if not denominator: raise ValueError('bds 输入为零')
                    hi,lo=numerator%denominator,numerator//denominator
                elif name=='shl': hi,lo=lo,hi
                elif name=='fdiv':
                    q=quotient(signed(a),signed(b)); hi,lo=(signed(a)-q*signed(b))&MASK,q&MASK
                elif name=='fmultu':
                    result=a*b
                    if result>>32:
                        h=result.bit_length()-1
                        z=next(i for i in range(64) if (result>>i)&1==0)
                        result ^= 1 << abs(h-z)
                elif name=='maddcu':
                    active=bool(a&1)
                    if active: result=old+a*b
                elif name=='mneg': result=-old
                elif name=='divabs': hi,lo=abs(signed(a))%abs(signed(b)),abs(signed(a))//abs(signed(b))
                elif name=='multfold':
                    result=a*b
                    if result&1: result=((result&MASK)<<32)|(result>>32)
                if result is not None: hi,lo=(result>>32)&MASK,result&MASK
                if active and spec['latency']>1: latency+=spec['latency']+1
        elif op==0:
            if ins==0: pass
            elif fn in (0x20,0x21): dst,value=rd,a+b
            elif fn in (0x22,0x23): dst,value=rd,a-b
            elif fn==0x24: dst,value=rd,a&b
            elif fn==0x25: dst,value=rd,a|b
            elif fn==0x2a: dst,value=rd,int(signed(a)<signed(b))
            elif fn==0x2b: dst,value=rd,int(a<b)
            elif fn==8: target=a
            elif fn==0x10: dst,value=rd,hi
            elif fn==0x12: dst,value=rd,lo
            elif fn==0x11: hi=a
            elif fn==0x13: lo=a
            elif fn in (0x18,0x19):
                product=signed(a)*signed(b) if fn==0x18 else a*b
                hi,lo=(product>>32)&MASK,product&MASK
                latency+=6
            elif fn in (0x1a,0x1b):
                aa,bb=(signed(a),signed(b)) if fn==0x1a else (a,b)
                q=quotient(aa,bb);hi,lo=(aa-q*bb)&MASK,q&MASK
                latency+=11
            else: raise ValueError('未识别 R 指令 '+hex(ins))
        elif op==0xf: dst,value=rt,(ins&65535)<<16
        elif op in (8,9): dst,value=rt,a+imm
        elif op==0xc: dst,value=rt,a&(ins&65535)
        elif op==0xd: dst,value=rt,a|(ins&65535)
        elif op in (0x20,0x21,0x23):
            size={0x20:1,0x21:2,0x23:4}[op]
            if addr%size: raise ValueError('普通 load 未对齐')
            dst,value=rt,signed(read(addr,size),8*size)
        elif op in (0x28,0x29,0x2b): store(addr,{0x28:1,0x29:2,0x2b:4}[op],b)
        elif op in (4,5): target=(pc+4+4*imm)&MASK if (a==b)==(op==4) else pc+8
        elif op in (2,3):
            target=(pc&0xf0000000)|((ins&0x3ffffff)<<2)
            if op==3: dst,value=31,pc+8
        else: raise ValueError('未识别指令 '+hex(ins))
        if dst:
            r[dst]=value&MASK
            events.append(f'@{pc:08x}: ${dst} <= {value&MASK:08x}')
        # 固定的最后一条写 $30=0xcafe 是完成标记，随后只会执行无副作用终止环。
        if dst==30 and value&MASK==0xcafe and ins==(0x0d<<26|30<<16|0xcafe):
            return dict(events=events, steps=retired, latency=latency, custom_hits=custom_hits,
                        histogram=histogram, registers=r, memory=mem.hex(), finish_pc=pc)
        if pending is not None:
            if target is not None: raise ValueError('控制指令位于延迟槽')
            pc,pending=pending,None
        else:
            pc=(pc+4)&MASK; pending=target
    raise ValueError('参考模型没有在步数上限内完成')
