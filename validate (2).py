"""发行前检查：全量双模型、两种编码、状态识别、编译和篡改测试。"""
import json
from pathlib import Path
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from judge import judge, evaluate, ROOT
from model import reference
from problems import PROBLEMS


def main():
    report={'reference':[], 'status_checks':{},'integrity':{}}
    source=ROOT/'tools'/'reference_cpu.v'
    errors=[]
    tasks=[(s['id'],o) for s in PROBLEMS for o in ([False,True] if s['original'] else [False])]
    def run(task):
        key,original=task;num=int(key[1:])+(100 if key[0]=='M' else 0)
        return judge(key,source,encoding='original' if original else 'practice',
                     defines=['PROBLEM='+str(num),'ORIGINAL='+str(int(original))],save=False)
    with ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(run,tasks):
            key=result['problem']
            report['reference'].append(result)
            print(key,result['encoding'],result['passed'],'/',result['total'],flush=True)
            errors.extend((key,c) for c in result['results'] if c['status']!='AC')
            (ROOT/'验证记录.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    expected=['@00003000: $1 <= 00000001']
    assert evaluate(expected,'1@00003000: $1 <= 00000001\nJUDGE_DONE cycles=8')['status']=='AC'
    assert evaluate(expected,'1@00003000: $1 <= 00000002\nJUDGE_DONE cycles=8')['status']=='WA'
    assert evaluate(expected,'JUDGE_LIMIT cycles=8')['status']=='TLE'
    assert evaluate(expected,'',returncode=1)['status']=='RE'
    assert evaluate(expected,'1@00003000: $1 <= 00000001\n2@00003004: $2 <= 00000002\nJUDGE_DONE cycles=8')['status']=='WA'
    assert evaluate(expected,'1@00003000: $1 <= xxxxxxxx\nJUDGE_DONE cycles=8')['status']=='WA'
    report['status_checks']['log_comparison']='AC / WA / TLE / RE / extra write / X passed'
    runs=ROOT/'runs';runs.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=str(runs)) as temp:
        broken=Path(temp)/'mips.v';broken.write_text('module mips( BROKEN',encoding='ascii')
        result=judge('Q11',broken,case_ids=['01'],save=False)
        assert result['results'][0]['status']=='CE'
        report['status_checks']['CE']='真实语法错误被判 CE'
        # 改写已验证行为 CPU：冻结取指但不输出错误写入，应达到周期上限。
        text=source.read_text(encoding='utf-8')
        broken.write_text(text.replace('assign i_inst_addr=pc;','assign i_inst_addr=32\'h3000;')
                          .replace('assign w_grf_we=destination!=0;','assign w_grf_we=0;')
                          .replace('assign m_data_byteen=byteen;','assign m_data_byteen=0;'),encoding='utf-8')
        result=judge('Q11',broken,case_ids=['01'],save=False)
        assert result['results'][0]['status']=='TLE',result
        report['status_checks']['TLE']='真实冻结取指被判 TLE'
        broken.write_text(text.replace('11:begin reads_hilo=1;hilo=1;nh=lo;nl=hi;end',
                                      '11:begin reads_hilo=1;hilo=1;nh=hi;nl=lo;end'),encoding='utf-8')
        result=judge('Q11',broken,case_ids=['05'],save=False)
        assert result['results'][0]['status']=='WA',result
        report['status_checks']['WA']='真实遗漏 HI/LO 交换被判 WA'
    count=0
    for path in (ROOT/'tests').glob('*/*/*/code.txt'):
        words=path.read_text().splitlines()
        assert len(words)==4096 and all(len(w)==8 and all(c in '0123456789abcdef' for c in w) for w in words)
        count+=1
    assert count==936
    report['integrity']={'cases':count,'problems':39,'cases_per_problem':24,'im_words_per_case':4096,'errors':errors}
    (ROOT/'验证记录.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    if errors:
        for key,c in errors[:20]:print('FAIL',key,c,flush=True)
        raise SystemExit(1)
    print('ALL VALIDATED',flush=True)


if __name__=='__main__':main()
