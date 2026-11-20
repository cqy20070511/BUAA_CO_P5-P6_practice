"""从仓库中的固定输入生成测试点；GitHub 无需保存数千份派生文件。"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
STAGES={'P5':ROOT/'p5','P6':ROOT}


def missing_files(stage):
    base=STAGES[stage];index=base/'cases.json'
    if not index.is_file():return ['cases.json']
    specs=json.loads(index.read_text(encoding='utf-8'))
    missing=[]
    for spec in specs.values():
        for case in spec['cases']:
            folder=base/spec['path']/case['id']
            names=['code.txt','expected.log','case.json','program.lst']
            if spec.get('original'):names.append('code_original.txt')
            for name in names:
                path=folder/name
                if not path.is_file():missing.append(str(path.relative_to(base)))
    return missing


def ensure_cases(stage,force=False):
    stage=stage.upper()
    if stage not in STAGES:raise ValueError('阶段须为 P5 或 P6')
    base=STAGES[stage]
    missing=missing_files(stage)
    if not missing and not force:
        return dict(stage=stage,status='existing',cases=sum(len(s['cases']) for s in json.loads((base/'cases.json').read_text(encoding='utf-8')).values()))
    if missing and (base/'tests').exists() and not force:
        raise ValueError(stage+' 测试目录不完整。保留现有文件；确认要从固定输入重建时运行 python prepare_cases.py --stage '+stage+' --force')
    process=subprocess.run([sys.executable,'-u',str(base/'make_cases.py')],cwd=base,
                           capture_output=True,encoding='utf-8',errors='replace',timeout=180)
    if process.returncode:
        raise RuntimeError(stage+' 测试点生成失败：'+(process.stderr or process.stdout)[-5000:])
    remaining=missing_files(stage)
    if remaining:raise RuntimeError(stage+' 生成后仍缺少 '+remaining[0])
    count=sum(len(s['cases']) for s in json.loads((base/'cases.json').read_text(encoding='utf-8')).values())
    print(stage+'：已从固定输入生成 '+str(count)+' 个测试点。',file=sys.stderr,flush=True)
    return dict(stage=stage,status='generated',cases=count)


def main():
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description='初始化按需生成的 P5/P6 测试点')
    parser.add_argument('--stage',type=str.upper,choices=STAGES)
    parser.add_argument('--force',action='store_true',help='明确重建全部选定阶段的派生测试点')
    args=parser.parse_args()
    try:
        results={stage:ensure_cases(stage,args.force) for stage in STAGES if not args.stage or stage==args.stage}
        print(json.dumps(dict(status='READY',stages=results),ensure_ascii=False,indent=2))
        return 0
    except (ValueError,RuntimeError,OSError,subprocess.TimeoutExpired) as e:
        print(json.dumps(dict(status='NOT_RUN',message=str(e)),ensure_ascii=False,indent=2));return 2


if __name__=='__main__':raise SystemExit(main())
