"""验证 AI 入口不会在没有仿真的情况下伪造判定，也不会把编译器崩溃当作源码 CE。"""
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import judge as engine


def call(*args):
    return subprocess.run([sys.executable,str(ROOT/'ai_judge.py'),*args],capture_output=True,
                          encoding='utf-8',errors='replace',timeout=30)


def main():
    result=call('run','bezal','missing.zip')
    assert result.returncode==2 and '--encoding' in result.stderr
    result=call('describe','bezal')
    spec=json.loads(result.stdout)
    assert spec['id']=='Q12' and spec['original']==['R',49]
    result=call('run','Q01','missing.zip','--encoding','original')
    assert result.returncode==2 and json.loads(result.stdout)['status']=='NOT_RUN'
    result=call('run','Q12','missing.zip','--encoding','original','--case','99')
    assert result.returncode==2 and json.loads(result.stdout)['status']=='NOT_RUN'
    crash=subprocess.CompletedProcess(args=[],returncode=0xc0000005,stdout='',stderr='')
    with patch.object(engine,'runtime',return_value=('iverilog','vvp',None)):
        with patch.object(engine,'run_process',return_value=crash):
            result=engine.judge('Q11',ROOT/'tools/reference_cpu.v',case_ids=['01'],save=False)
    assert result['results'][0]['status']=='RE',result
    print('Mandatory encoding / instruction lookup / invalid mode / invalid case / compiler crash: OK')


if __name__=='__main__':main()
