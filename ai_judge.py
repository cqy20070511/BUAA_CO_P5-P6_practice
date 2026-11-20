"""供 AI 或终端直接调用的评测入口。Python 标准库 + Icarus，无网页依赖。"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import judge as engine

ROOT=Path(__file__).resolve().parent


def emit(value):
    print(json.dumps(value,ensure_ascii=False,indent=2),flush=True)


def resolve(value):
    catalog=engine.manifest()
    result=catalog.get(value.upper())
    if result:return result
    matches=[s for s in catalog.values() if s['name'].lower()==value.lower()]
    if len(matches)==1:return matches[0]
    raise ValueError('找不到题目：'+value+'。先运行 python ai_judge.py list。')


def doctor():
    try:
        compiler,simulator,_=engine.runtime()
        tools=bool(compiler and simulator and Path(compiler).is_file() and Path(simulator).is_file())
        error=None if tools else '未同时找到 iverilog 和 vvp'
    except (ValueError,RuntimeError,OSError) as e:
        compiler=simulator=None;tools=False;error=str(e)
    return dict(ready=sys.version_info>=(3,9) and tools,python=sys.version.split()[0],
                iverilog=compiler,vvp=simulator,error=error,
                install='需要 Python 3.9+ 和 Icarus Verilog（iverilog、vvp）；Ubuntu/Debian 可安装 iverilog 包。')


def check_data(selected=None):
    from model import reference
    catalog=engine.manifest();count=originals=0
    for spec in ([resolve(selected)] if selected else catalog.values()):
        assert len(spec['cases'])==24,spec['id']
        unique=set()
        for case in spec['cases']:
            folder=ROOT/spec['path']/case['id']
            data=(folder/'code.txt').read_bytes()
            digest=hashlib.sha256(data).hexdigest()
            assert digest==case['sha256'],str(folder)+' 的 SHA-256 不匹配'
            unique.add(digest)
            lines=data.decode('ascii').splitlines()
            assert len(lines)==4096
            words=[int(line,16) for line in lines]
            assert all(len(line)==8 and 0<=word<=0xffffffff for line,word in zip(lines,words))
            expected=(folder/'expected.log').read_text(encoding='ascii').splitlines()
            result=reference(words,spec['id'])
            assert result['events']==expected,str(folder)+' 的参考日志不匹配'
            assert result['finish_pc']==case['finish_pc']
            if spec['original']:
                original=(folder/'code_original.txt').read_text(encoding='ascii').splitlines()
                assert len(original)==4096
                other=reference([int(w,16) for w in original],spec['id'],True)
                assert other['events']==expected
                originals+=1
            count+=1
        assert len(unique)==24,spec['id']+' 含重复测试程序'
    return dict(status='OK',problems=1 if selected else len(catalog),cases=count,original_cases=originals,
                checks=['SHA-256','4096-word IM','unique programs','reference logs','finish PC','original encoding'])


def build_parser():
    parser=argparse.ArgumentParser(description='P5 AI 命令行仿真评测，必须明确指定题目和编码')
    commands=parser.add_subparsers(dest='command',required=True)
    commands.add_parser('doctor',help='检查本机 Python 和 Icarus')
    commands.add_parser('list',help='列出题号、指令和编码')
    desc=commands.add_parser('describe',help='读取完整题面和测试点信息');desc.add_argument('problem')
    verify=commands.add_parser('check-data',help='核验机器码和标准答案');verify.add_argument('problem',nargs='?')
    run=commands.add_parser('run',help='真实编译和仿真用户 RTL')
    run.add_argument('problem',help='题号或指令名，例如 Q01 或 cco')
    run.add_argument('source',help='用户 RTL 源码目录、ZIP 或单个完整 .v 文件')
    run.add_argument('--encoding',required=True,choices=('practice','original'))
    run.add_argument('--case',nargs='+',dest='cases',help='只跑指定点，例如 01 02 24；默认全题 24 点')
    run.add_argument('--json',dest='json_path',help='保存结构化结果，例如 results/bezal.json')
    run.add_argument('--timeout',type=float,default=15,help='每个测试点的墙钟秒数上限')
    return parser


def main():
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    args=build_parser().parse_args()
    try:
        if args.command=='doctor':
            result=doctor();emit(result);return 0 if result['ready'] else 2
        if args.command=='list':
            emit([dict(id=s['id'],name=s['name'],format=s['format'],practice=s['encoding_bits'],
                       original=s['original_bits'],cases=len(s['cases'])) for s in engine.manifest().values()]);return 0
        if args.command=='describe':emit(resolve(args.problem));return 0
        if args.command=='check-data':emit(check_data(args.problem));return 0
        spec=resolve(args.problem)
        if args.encoding=='original' and not spec['original']:raise ValueError('本题没有已核实的原平台编码，请查看 describe 输出')
        ids=[str(c).zfill(2) for c in args.cases] if args.cases else None
        if ids and set(ids)-{c['id'] for c in spec['cases']}:raise ValueError('测试点编号须在 01 到 24 之间')
        if not 0<args.timeout<=300:raise ValueError('timeout 应大于零且不超过 300 秒')
        ready=doctor()
        if not ready['ready']:
            emit(dict(status='NOT_RUN',message='尚未执行仿真，请先准备仿真环境',environment=ready));return 2
        print(f"题目 {spec['id']} / {spec['name']}，编码 {args.encoding}，后端 Icarus native",flush=True)
        result=engine.judge(spec['id'],args.source,encoding=args.encoding,case_ids=ids,
                            on_result=engine.report,timeout=args.timeout,backend='native')
        result['instruction']=spec['name']
        result['stage']='P5'
        result['global_id']='P5-'+spec['id']
        result['selected_encoding']=spec['original_bits'] if args.encoding=='original' else spec['encoding_bits']
        if args.json_path:
            path=Path(args.json_path);path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(f"通过 {result['passed']} / {result['total']}；完整日志：{result['record']}",flush=True)
        return 0 if result['passed']==result['total'] else 1
    except (ValueError,AssertionError,OSError,RuntimeError) as e:
        emit(dict(status='NOT_RUN',message=str(e)));return 2


if __name__=='__main__':raise SystemExit(main())
