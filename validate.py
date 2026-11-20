"""P5 全量交叉仿真、旧数据兼容及错误状态检查。"""
from pathlib import Path
import json,sys,tempfile
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from judge import judge,ROOT
from ai_judge import check_data
from problems import PROBLEMS


def numeric(key):return int(key[1:])+{'Q':0,'M':200,'X':300}[key[0]]


def main():
    result={'reference':[],'status_checks':{},'integrity':{}}
    source=ROOT/'tools/reference_cpu.v'
    def run(spec):
        return judge(spec['id'],source,defines=['P5_PROBLEM='+str(numeric(spec['id']))],save=False)
    with ThreadPoolExecutor(max_workers=3) as pool:
        for row in pool.map(run,PROBLEMS):
            result['reference'].append(row)
            print(row['problem'],row['passed'],'/',row['total'],flush=True)
            (ROOT/'验证记录.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    errors=[(r['problem'],c) for r in result['reference'] for c in r['results'] if c['status']!='AC']
    if errors:
        for item in errors[:20]:print('FAIL',item,flush=True)
        raise SystemExit(1)
    with tempfile.TemporaryDirectory(dir=str(ROOT/'runs')) as temp:
        source_text=source.read_text(encoding='utf-8');broken=Path(temp)/'mips.v'
        broken.write_text('module mips (BROKEN',encoding='ascii')
        report=judge('Q01',broken,case_ids=['01'],save=False)
        assert report['results'][0]['status']=='CE',report
        result['status_checks']['CE']='真实语法错误判 CE'
        broken.write_text(source_text.replace('1:begin destination=rd;value=pop(a&b);end','1:begin destination=rd;value=0;end'),encoding='utf-8')
        report=judge('Q01',broken,case_ids=['02'],save=False)
        assert report['results'][0]['status']=='WA',report
        result['status_checks']['WA']='真实计算错误判 WA'
        broken.write_text(source_text.replace('end else begin\n            instruction=',"end else if (1'b0) begin\n            instruction="),encoding='utf-8')
        report=judge('Q01',broken,case_ids=['01'],save=False)
        assert report['results'][0]['status']=='TLE',report
        result['status_checks']['TLE']='真实不前进 CPU 判 TLE'
    result['integrity']=check_data()
    result['integrity']['errors']=[]
    assert result['integrity']['cases']==960
    (ROOT/'验证记录.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('P5 ALL VALIDATED',flush=True)


if __name__=='__main__':main()
