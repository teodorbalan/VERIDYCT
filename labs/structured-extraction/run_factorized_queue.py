"""Start one prepared run after its assigned GPU's previous job exits."""
import argparse
import json
import os
import pathlib
import subprocess
import time


def alive(pid):
    try:
        state=pathlib.Path(f'/proc/{pid}/stat').read_text().split(') ',1)[1].split()[0]
        return state != 'Z'
    except FileNotFoundError:
        return False


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--previous-pid',type=int,required=True)
    p.add_argument('--previous-result',required=True)
    p.add_argument('--gpu',type=int,required=True)
    p.add_argument('--python',required=True)
    p.add_argument('--data',required=True);p.add_argument('--out',required=True)
    p.add_argument('--variant',required=True);a=p.parse_args()
    root=pathlib.Path(a.out).parent
    while alive(a.previous_pid):time.sleep(10)
    if not pathlib.Path(a.previous_result).exists():
        raise RuntimeError('Previous run did not finish successfully; inspect its log')
    command=[a.python,str(pathlib.Path(__file__).parent/'train_factorized.py'),
             '--data',a.data,'--out',a.out,'--variant',a.variant,'--seed','271828']
    env=dict(os.environ,CUDA_VISIBLE_DEVICES=str(a.gpu))
    print(json.dumps(dict(command=command,gpu=a.gpu)),flush=True)
    process=subprocess.Popen(command,env=env)
    (root/(pathlib.Path(a.out).name+'-receipt.json')).write_text(json.dumps(dict(pid=process.pid,gpu=a.gpu,command=command),indent=2))
    raise SystemExit(process.wait())


if __name__=='__main__':main()
