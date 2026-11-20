"""校验公开分享目录并打包；不包含用户提交、评测日志或工具缓存。"""
from pathlib import Path
import hashlib
import argparse
import json
import re
import zipfile
import sys

ROOT=Path(__file__).resolve().parents[1]
SKIP={'.git','__pycache__','runs','results','submissions'}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--baseline',help='可选：与原 P6 分享 ZIP 逐字节比对测试文件')
    parser.add_argument('--output',help='可选：分享 ZIP 输出位置')
    args=parser.parse_args()
    sys.path.insert(0,str(ROOT))
    from prepare_cases import ensure_cases
    ensure_cases('P5');ensure_cases('P6')
    catalog=json.loads((ROOT/'cases.json').read_text(encoding='utf-8'))
    report=json.loads((ROOT/'验证记录.json').read_text(encoding='utf-8'))
    p5=json.loads((ROOT/'p5/cases.json').read_text(encoding='utf-8'))
    p5_report=json.loads((ROOT/'p5/验证记录.json').read_text(encoding='utf-8'))
    assert len(catalog)==39 and len(report['reference'])==48
    assert all(r['passed']==24 for r in report['reference']) and not report['integrity']['errors']
    assert {'WA','TLE','CE'}<=set(report['status_checks'])
    assert len(p5)==40 and not any(key.startswith('E') for key in p5)
    assert len(p5_report['reference'])==40 and all(r['passed']==24 for r in p5_report['reference'])
    assert not p5_report['integrity']['errors']
    assert {'WA','TLE','CE'}<=set(p5_report['status_checks'])
    # 比对原 P6 包的测试文件，然后更新同一个分享 ZIP。
    output=Path(args.output).resolve() if args.output else ROOT.parent/'P6-AI-Judge_GitHub分享版.zip'
    baseline=Path(args.baseline).resolve() if args.baseline else output
    preserved=0
    if args.baseline and not baseline.is_file():raise ValueError('找不到原 P6 分享 ZIP')
    if baseline.exists():
        with zipfile.ZipFile(baseline) as previous:
            for name in previous.namelist():
                prefix=ROOT.name+'/tests/'
                if name.startswith(prefix) and not name.endswith('/'):
                    path=ROOT/name[len(ROOT.name)+1:]
                    assert path.read_bytes()==previous.read(name),'原 P6 测试内容发生改变：'+name
                    preserved+=1
    if args.baseline:assert preserved>0,'基线 ZIP 中未找到原 P6 测试文件'
    legacy=json.loads((ROOT/'p5/legacy_cases.json').read_text(encoding='utf-8'))
    legacy_count=0
    for key,rows in legacy.items():
        for case,old in zip(p5[key]['cases'],rows):
            folder=ROOT/'p5'/p5[key]['path']/case['id']
            words=[int(w,16) for w in (folder/'code.txt').read_text().splitlines()]
            assert words==old['words']+[0]*(4096-len(old['words']))
            assert (folder/'expected.log').read_text().splitlines()==old['expected']
            assert case['cycles']==old['cycles'] and case['legacy_id']==old['id']
            legacy_count+=1
    assert legacy_count==264
    combined={}
    for stage,data in [('P5',p5),('P6',catalog)]:
        for key,spec in data.items():
            gid=stage+'-'+key
            combined[gid]=dict(stage=stage,id=gid,local_id=key,name=spec['name'],format=spec['format'],
                              encoding_bits=spec['encoding_bits'],original_bits=spec['original_bits'],cases=len(spec['cases']),
                              case_index='p5/cases.json' if stage=='P5' else 'cases.json',
                              path=('p5/' if stage=='P5' else '')+spec['path'])
    (ROOT/'catalog.json').write_text(json.dumps(combined,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    bundle=dict(name='P6-AI-Judge',format_version=2,base='original P6 AI sharing package',
                cli='co_judge.py',legacy_p6_cli='ai_judge.py',problems=79,cases=1896,original_cases=216,
                stages={'P5':dict(path='p5',problems=40,cases=960),'P6':dict(path='.',problems=39,cases=936)},
                excluded_p5_teaching=True,dependencies=['Python >=3.9','iverilog','vvp'],requires_web_server=False,
                repository_case_storage='generated',prepare_cli='prepare_cases.py')
    (ROOT/'bundle.json').write_text(json.dumps(bundle,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    integration=dict(p6_test_files_unchanged=preserved,p6_baseline_bundle=baseline.name if baseline.exists() else None,p5_legacy_cases_preserved=legacy_count,
                     p5_simulation_checks=960,p6_simulation_checks=1152,problems=79,independent_cases=1896,
                     p5_teaching_included=False)
    (ROOT/'P5增补验证记录.json').write_text(json.dumps(integration,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    files=[]
    for path in sorted(ROOT.rglob('*')):
        relative=path.relative_to(ROOT)
        if not path.is_file() or SKIP.intersection(relative.parts) or path.suffix in ('.pyc','.zip'):continue
        if path.suffix in ('.py','.v','.vh','.md','.json','.txt','.log','.lst'):
            data=path.read_bytes()
            if b'\r' in data:
                data=data.replace(b'\r\n',b'\n').replace(b'\r',b'\n');path.write_bytes(data)
            text=data.decode('utf-8')
            assert not re.search(r'[A-Za-z]:[/\\]+Users[/\\]+[^\s]+',text,re.I),str(relative)+' 含本机路径'
        files.append(path)
    for base,data in [(ROOT,catalog),(ROOT/'p5',p5)]:
        for spec in data.values():
            assert len(spec['cases'])==24
            for case in spec['cases']:
                code=base/spec['path']/case['id']/'code.txt'
                assert hashlib.sha256(code.read_bytes()).hexdigest()==case['sha256']
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for path in files:z.write(path,(Path(ROOT.name)/path.relative_to(ROOT)).as_posix())
    with zipfile.ZipFile(output) as z:
        assert z.testzip() is None
        assert sum(n.endswith('/code.txt') for n in z.namelist())==1896
        assert sum(n.endswith('/code_original.txt') for n in z.namelist())==216
        assert not any(SKIP.intersection(Path(n).parts) for n in z.namelist())
    print(output.name,output.stat().st_size,'bytes; 1896 + 216 codes; CRC OK; P6 tests preserved:',preserved)


if __name__=='__main__':main()
