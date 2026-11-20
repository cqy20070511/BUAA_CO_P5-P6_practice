"""在原 P6 仓库上增补 P5 的统一入口，旧 ai_judge.py 仍只处理 P6。"""
import argparse,json,re,subprocess,sys
from pathlib import Path
from prepare_cases import ensure_cases

ROOT=Path(__file__).resolve().parent
STAGES={'P5':ROOT/'p5','P6':ROOT}


def emit(value):print(json.dumps(value,ensure_ascii=False,indent=2),flush=True)


def catalogs():return {stage:json.loads((path/'cases.json').read_text(encoding='utf-8')) for stage,path in STAGES.items()}


def resolve(value):
    match=re.fullmatch(r'(P5|P6)[-:](.+)',value,re.I)
    if not match:raise ValueError('请加 P5 或 P6 前缀，例如 P5-Q01、P5-pcxor、P6-bezal')
    stage,local=match.group(1).upper(),match.group(2)
    data=catalogs()[stage];spec=data.get(local.upper())
    if spec is None:
        matches=[s for s in data.values() if s['name'].lower()==local.lower()]
        if len(matches)!=1:raise ValueError('找不到该阶段的指令：'+value)
        spec=matches[0]
    return stage,spec


def run_json(stage,*args):
    command=[sys.executable,str(STAGES[stage]/'ai_judge.py'),*args]
    process=subprocess.run(command,capture_output=True,encoding='utf-8',errors='replace')
    try:data=json.loads(process.stdout)
    except ValueError:raise ValueError(stage+' 命令未返回 JSON：'+(process.stderr or process.stdout)[-2000:])
    if process.returncode:raise ValueError(stage+'：'+data.get('message',str(data)))
    return data


def main():
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description='P5/P6 统一 AI 仿真评测；保留原 P6 ai_judge.py')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor')
    ls=sub.add_parser('list');ls.add_argument('--stage',type=str.upper,choices=['P5','P6'])
    desc=sub.add_parser('describe');desc.add_argument('problem')
    check=sub.add_parser('check-data');check.add_argument('--stage',type=str.upper,choices=['P5','P6'])
    prepare=sub.add_parser('prepare');prepare.add_argument('--stage',type=str.upper,choices=['P5','P6'])
    run=sub.add_parser('run');run.add_argument('problem');run.add_argument('source')
    run.add_argument('--encoding',required=True,choices=['practice','original'])
    run.add_argument('--case',nargs='+',dest='cases');run.add_argument('--json',dest='json_path')
    run.add_argument('--timeout',type=float,default=15)
    args=parser.parse_args()
    try:
        if args.command=='doctor':emit(run_json('P6','doctor'));return 0
        if args.command=='list':
            rows=[]
            for stage,data in catalogs().items():
                if args.stage and args.stage!=stage:continue
                for s in data.values():
                    rows.append(dict(id=stage+'-'+s['id'],stage=stage,name=s['name'],format=s['format'],
                                     practice=s['encoding_bits'],original=s['original_bits'],cases=len(s['cases'])))
            emit(rows);return 0
        if args.command=='check-data':
            for stage in STAGES:
                if not args.stage or stage==args.stage:ensure_cases(stage)
            checks={stage:run_json(stage,'check-data') for stage in STAGES if not args.stage or stage==args.stage}
            emit(dict(status='OK',stages=checks,cases=sum(s['cases'] for s in checks.values()),original_cases=sum(s['original_cases'] for s in checks.values())));return 0
        if args.command=='prepare':
            emit(dict(status='READY',stages={stage:ensure_cases(stage) for stage in STAGES if not args.stage or stage==args.stage}));return 0
        stage,spec=resolve(args.problem)
        if args.command=='describe':
            emit({**spec,'stage':stage,'global_id':stage+'-'+spec['id'],'interface':'internal-memory/logging' if stage=='P5' else 'external-memory/ports'});return 0
        if args.encoding=='original' and not spec['original']:raise ValueError(stage+'-'+spec['id']+' 没有已核实的原平台编码，请使用 practice')
        ensure_cases(stage)
        print(f"阶段 {stage}，题目 {stage}-{spec['id']}，指令 {spec['name']}",flush=True)
        command=[sys.executable,'-u',str(STAGES[stage]/'ai_judge.py'),'run',spec['id'],args.source,'--encoding',args.encoding,'--timeout',str(args.timeout)]
        if args.cases:command+=['--case',*args.cases]
        if args.json_path:command+=['--json',args.json_path]
        return subprocess.run(command).returncode
    except (ValueError,OSError,RuntimeError,subprocess.TimeoutExpired) as e:
        emit(dict(status='NOT_RUN',message=str(e)));return 2


if __name__=='__main__':raise SystemExit(main())
