"""P6 原生 Icarus 仿真评测：目录或 ZIP，默认全题 24 点，JSON/实时回调。"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import zipfile

ROOT=Path(__file__).resolve().parent
LINE=re.compile(r'^(?:\d+\s*)?@([0-9a-fxz]+):\s*([*$])\s*([0-9a-fxz]+)\s*<=\s*([0-9a-fxz]+)$',re.I)
NAMES={'AC':'ACCEPTED','WA':'WRONG ANSWER','TLE':'TIME LIMIT EXCEEDED','CE':'COMPILE ERROR','RE':'RUNTIME ERROR'}


def manifest():return json.loads((ROOT/'cases.json').read_text(encoding='utf-8'))


def parse(raw):
    m=LINE.match(raw.strip())
    if not m:return None
    pc,kind,addr,value=m.groups()
    if re.search('[xz]',pc+addr+value,re.I):return kind,'UNKNOWN '+raw.strip()
    return kind,f'@{int(pc,16):08x}: {kind}{int(addr,10) if kind=="$" else format(int(addr,16),"08x")} <= {int(value,16):08x}'


def evaluate(expected,output,returncode=0,timed_out=False):
    actual=[parse(line) for line in output.splitlines()]
    actual=[x for x in actual if x]
    # M 和 W 可以在不同周期交错；分别比较两条有序的体系结构事件流。
    # 保留每条流内部顺序和每个事件的 PC，任何错写、漏写、重复写均不能被掩盖。
    for kind in ('$', '*'):
        want=[line for line in expected if parse(line)[0]==kind]
        got=[line for k,line in actual if k==kind]
        for index,(a,b) in enumerate(zip(want,got)):
            if a!=b:return dict(status='WA',message='写入行为不一致',stream=kind,index=index+1,expected=a,actual=b)
        if len(got)>len(want):return dict(status='WA',message='出现多余写入',stream=kind,index=len(want)+1,expected='无后续写入',actual=got[len(want)])
    if 'JUDGE_UNKNOWN' in output or 'JUDGE_BAD_ADDRESS' in output:
        return dict(status='WA',message=next(line for line in output.splitlines() if 'JUDGE_UNKNOWN' in line or 'JUDGE_BAD_ADDRESS' in line))
    if timed_out:return dict(status='TLE',message='仿真进程超过墙钟时间上限')
    if returncode:return dict(status='RE',message='仿真异常退出',detail=output[-3000:])
    for kind in ('$', '*'):
        want=[line for line in expected if parse(line)[0]==kind]
        got=[line for k,line in actual if k==kind]
        if len(got)<len(want):
            # 周期到期且已有前缀正确，判 TLE；自行提前结束仿真却少日志判 WA。
            limit='JUDGE_LIMIT' in output
            return dict(status='TLE' if limit else 'WA',message='周期上限内未完成' if limit else '仿真提前结束，缺少写入',
                        stream=kind,index=len(got)+1,expected=want[len(got)],actual='未发生')
    if 'JUDGE_DONE' not in output:return dict(status='TLE' if 'JUDGE_LIMIT' in output else 'RE',message='未观察到完成标记')
    m=re.search(r'JUDGE_DONE cycles=(\d+)',output)
    return dict(status='AC',message='Accepted.',cycles=int(m.group(1)))


def runtime():
    override=os.environ.get('P6_IVERILOG')
    bundled=ROOT/'runtime'/'iverilog'
    if override:base=Path(override)
    elif (bundled/'bin'/'iverilog.exe').exists():base=bundled
    else:
        exe=shutil.which('iverilog')
        if not exe:raise RuntimeError('找不到原生 Icarus。请设置 P6_IVERILOG 为安装目录，并确保 iverilog 和 vvp 都可运行。')
        simulator=shutil.which('vvp')
        if not simulator:raise RuntimeError('找不到 vvp，请完整安装 Icarus Verilog')
        return exe,simulator,None
    return str(base/'bin'/'iverilog.exe'),str(base/'bin'/'vvp.exe'),base/'lib'/'ivl'


def extract_zip(source,dest):
    total=0
    with zipfile.ZipFile(source) as z:
        for item in z.infolist():
            relative=Path(item.filename.replace('\\','/'))
            if relative.is_absolute() or '..' in relative.parts or ':' in item.filename:raise ValueError('ZIP 路径不安全')
            if item.is_dir() or relative.suffix.lower() not in ('.v','.vh'):continue
            total+=item.file_size
            if total>20*1024*1024:raise ValueError('源码解压后超过 20MB')
            path=dest/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(z.read(item))


def prepare_sources(source,dest):
    source=Path(source).resolve()
    if source.is_file() and source.suffix.lower()=='.zip':extract_zip(source,dest)
    elif source.is_file() and source.suffix.lower()=='.v':shutil.copy2(source,dest/source.name)
    elif source.is_dir():
        paths=[p for p in source.rglob('*') if p.is_file() and p.suffix.lower() in ('.v','.vh')]
        if len(paths)>500:raise ValueError('源码文件过多，请只提交当前题的 RTL 工程')
        for p in paths:
            if any(part.startswith('.') for part in p.relative_to(source).parts):continue
            target=dest/p.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    else:raise ValueError('请选择源码目录、Verilog 文件或 ZIP')
    units=[]
    for p in dest.rglob('*.v'):
        # 忽略工程自带的 TB，不改变用户源码。
        if re.search(r'(^tb[_.]|_tb(?:_|\.)|^testbench|^mips_txt)',p.name,re.I):continue
        text=p.read_text(encoding='utf-8',errors='replace')
        # 禁止提交自带日志/提前停止/外部文件读取；本包是本地可信代码的功能工具，不是公网沙箱。
        stripped=re.sub(r'//[^\n]*|/\*.*?\*/','',text,flags=re.S)
        bad=re.search(r'\$(display|write|monitor|strobe|finish|stop|fatal|readmemh|readmemb|fopen|system)\b',stripped)
        if bad:raise ValueError(f'{p.name} 含不允许的仿真任务 ${bad.group(1)}；请移除内部存储器和打印，仅提交 P6 RTL')
        units.append(p)
    if not units:raise ValueError('没有找到 RTL .v 文件')
    if sum(bool(re.search(r'\bmodule\s+mips\b',p.read_text(errors='replace'))) for p in units)!=1:
        raise ValueError('必须且只能有一个顶层 module mips；不要把多个题的工程一起提交')
    return units


def run_process(args,cwd,timeout):
    env=os.environ.copy()
    env['PATH']=str(Path(args[0]).parent)+os.pathsep+env.get('PATH','')
    # 原生 Icarus 的旧版 Windows 临时文件接口对中文绝对路径不稳定。
    env['TEMP']=env['TMP']='.'
    return subprocess.run([str(x) for x in args],cwd=cwd,env=env,stdin=subprocess.DEVNULL,capture_output=True,encoding='utf-8',errors='replace',
                          timeout=timeout,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))


def judge(problem,source,encoding='practice',case_ids=None,on_result=None,timeout=15,save=True,defines=(),backend=None):
    spec=manifest().get(problem.upper())
    if not spec:raise ValueError('题号不存在')
    problem=spec['id']
    backend=backend or os.environ.get('P6_JUDGE_BACKEND','native')
    if backend!='native':raise ValueError('本分享版使用 native Icarus 后端')
    if encoding=='original' and not spec['original']:raise ValueError('本题没有已核实的原平台编码')
    cases=[c for c in spec['cases'] if not case_ids or c['id'] in case_ids]
    if not cases:raise ValueError('没有选中的测试点')
    root=ROOT/'runs';root.mkdir(exist_ok=True)
    record=root/(time.strftime('%Y%m%d_%H%M%S')+'_'+problem+'_'+str(time.time_ns()%1000000))
    if save:record.mkdir()
    reports=[];started=time.time()
    with tempfile.TemporaryDirectory(prefix='job_',dir=str(root)) as temp:
        work=Path(temp);sources=work/'src';sources.mkdir()
        compile_status='CE'
        try:
            units=prepare_sources(source,sources)
            iv,vvp,lib=runtime()
            args=[iv]
            if lib:args+=['-B',os.path.relpath(str(lib),str(work))]
            args+=['-g2005','-s','p6_judge_tb','-o','submission.vvp']
            for value in defines:args+=['-D'+value]
            for directory in sorted({u.parent for u in units}):args+=['-I',os.path.relpath(str(directory),str(work))]
            tb=work/'p6_judge_tb.v';shutil.copy2(ROOT/'p6_judge_tb.v',tb)
            args+=[os.path.relpath(str(u),str(work)) for u in units]+['p6_judge_tb.v']
            compiled=run_process(args,work,30)
            diagnostics=compiled.stdout+compiled.stderr
            ce=compiled.returncode!=0
            if compiled.returncode<0 or compiled.returncode>=0x80000000:compile_status='RE'
            if ce and not diagnostics.strip():diagnostics='Icarus 编译进程异常退出，退出码：'+str(compiled.returncode)
        except (ValueError,RuntimeError,OSError,subprocess.TimeoutExpired) as e:
            diagnostics=str(e);ce=True
            if isinstance(e,(OSError,RuntimeError)):compile_status='RE'
        if save:(record/'compile.log').write_text(diagnostics,encoding='utf-8')
        for case in cases:
            case_root=ROOT/spec['path']/case['id'];expected=(case_root/'expected.log').read_text().splitlines()
            if ce:result=dict(status=compile_status,message='编译器进程异常，需先检查仿真环境' if compile_status=='RE' else 'Verilog 编译或接口检查失败',detail=diagnostics[-6000:])
            else:
                shutil.copy2(case_root/('code_original.txt' if encoding=='original' else 'code.txt'),work/'code.txt')
                args=[vvp]
                if lib:args+=['-M','-','-M',os.path.relpath(str(lib),str(work))]
                args+=['submission.vvp']
                args+=['+budget='+str(case['cycles']),'+finish_pc='+format(case['finish_pc'],'x')]
                try:
                    run=run_process(args,work,timeout);output=run.stdout+run.stderr
                    result=evaluate(expected,output,run.returncode)
                except subprocess.TimeoutExpired as e:
                    output=e.stdout or ''
                    if isinstance(output,bytes):output=output.decode('utf-8',errors='replace')
                    result=evaluate(expected,output,timed_out=True)
                except OSError as e:output=str(e);result=dict(status='RE',message=str(e))
                if save:(record/(case['id']+'.log')).write_text(output,encoding='utf-8')
            result={**result,'id':case['id'],'title':case['title'],'budget':case['cycles']}
            reports.append(result)
            if on_result:on_result(result)
    summary=dict(problem=problem,encoding=encoding,backend=backend,results=reports,passed=sum(r['status']=='AC' for r in reports),
                 total=len(reports),seconds=round(time.time()-started,3),record=str(record) if save else None)
    if save:(record/'result.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    return summary


def report(item):
    print(f"测试点 {item['id']}   {item['status']} / {NAMES[item['status']]}",flush=True)
    print(item['message'],flush=True)
    if 'expected' in item:print('Expected: '+item['expected']+'\nActual:   '+item['actual'],flush=True)
    if 'detail' in item:print(item['detail'],flush=True)


def main():
    parser=argparse.ArgumentParser(description='P6 逐点仿真评测')
    parser.add_argument('problem');parser.add_argument('source')
    parser.add_argument('--encoding',choices=['practice','original'],default='practice')
    parser.add_argument('--case',nargs='+',dest='cases');parser.add_argument('--json',dest='json_path')
    parser.add_argument('--backend',choices=['native'],default='native')
    args=parser.parse_args()
    result=judge(args.problem,args.source,args.encoding,args.cases,on_result=report,backend=args.backend)
    print(f"通过 {result['passed']} / {result['total']}，记录：{result['record']}")
    if args.json_path:Path(args.json_path).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if result['passed']==result['total'] else 1


if __name__=='__main__':raise SystemExit(main())
