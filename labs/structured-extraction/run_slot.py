"""Six visible terminal slots, eight persistent training processes with receipts."""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import time

SLOTS={0:[('01-cnn',0,271828)],1:[('02-bilstm-word',1,271828)],2:[('03-char-bilstm',2,271828)],3:[('04-char-bilstm-large',3,271828)],4:[('05-char-bigru',4,271828),('03-char-bilstm',6,314159)],5:[('06-char-transformer',5,271828),('04-char-bilstm-large',7,314159)]}

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--slot',type=int,choices=SLOTS,required=True);p.add_argument('--round',choices=['v1','v2'],default='v1');a=p.parse_args()
    root=pathlib.Path(a.root).resolve();ops=root/'operations';receipts=ops/(f'slot-{a.slot}.json' if a.round=='v1' else f'slot-v2-{a.slot}.json')
    source=root/('source' if a.round=='v1' else 'source-v2');data=root/('data' if a.round=='v1' else 'data-v2')
    if receipts.exists():
        jobs=json.loads(receipts.read_text());print('Existing slot; monitoring without relaunch',flush=True)
    else:
        jobs=[]
        for variant,gpu,seed in SLOTS[a.slot]:
            name=f'{variant}-s{seed}';out=root/('runs' if a.round=='v1' else 'runs-v2')/name;out.mkdir(parents=True,exist_ok=True)
            log=out/'train.log';env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES=str(gpu),OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',PYTHONUNBUFFERED='1')
            cmd=[str(root/'venv/bin/python'),str(source/'train.py'),'--data',str(data),'--out',str(out),'--variant',variant,'--seed',str(seed),'--epochs','40','--patience','8','--batch','48']
            if a.round=='v2':cmd+=['--pretrained','--lr','.0003' if variant=='06-char-transformer' else '.001']
            with log.open('a') as f:proc=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,env=env,start_new_session=True,cwd=source)
            jobs.append({'pid':proc.pid,'variant':variant,'gpu':gpu,'seed':seed,'out':str(out),'log':str(log),'command':cmd})
        receipts.write_text(json.dumps(jobs,indent=2))
    print(json.dumps(jobs,indent=2),flush=True)
    positions={j['log']:0 for j in jobs}
    while True:
        live=False
        for j in jobs:
            stat=pathlib.Path('/proc',str(j['pid']),'stat')
            try:live=live or stat.read_text().split(') ')[1].split()[0]!='Z'
            except FileNotFoundError:pass
            try:os.waitpid(j['pid'],os.WNOHANG)
            except ChildProcessError:pass
            with open(j['log']) as f:
                f.seek(positions[j['log']]);chunk=f.read();positions[j['log']]=f.tell()
            if chunk:print(f"GPU {j['gpu']} {j['variant']}\n{chunk}",flush=True)
        if not live:break
        time.sleep(10)

if __name__=='__main__':main()
