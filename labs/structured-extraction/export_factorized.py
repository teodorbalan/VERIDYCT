"""Export a selected factorized checkpoint to the existing five-input CPU runtime."""
import argparse
import hashlib
import json
import pathlib
import shutil
import time
import numpy as np
import onnx
import torch
from model import collate
from model_factorized import load_model
from runtime import INPUT_NAMES, CpuExtractor, numpy_batch, decode
from train import read_rows, key
from export_cpu import metrics
from select_ensemble import score


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--checkpoint',required=True); p.add_argument('--data',required=True)
    p.add_argument('--out',required=True); p.add_argument('--smoke',action='store_true')
    a=p.parse_args(); root=pathlib.Path(a.data); out=pathlib.Path(a.out)
    if out.exists(): raise ValueError('Use a fresh bundle directory')
    out.mkdir(parents=True)
    torch.set_num_threads(2); torch.set_num_interop_threads(1)
    model,ck=load_model(a.checkpoint);meta=ck['meta']
    (out/'meta.json').write_text(json.dumps(meta,ensure_ascii=False))
    shutil.copyfile(root/'lexicon.json',out/'lexicon.json')
    rows=read_rows(root/'dev.jsonl'); rows.sort(key=lambda r:len(r['tokens']))
    dynamic={'words':{0:'batch',1:'tokens'},'chars':{0:'batch',1:'tokens'},
             'spans':{0:'batch',1:'candidates',2:'tokens'},
             'clauses':{0:'batch',1:'candidates',2:'tokens'},
             'kinds':{0:'batch',1:'candidates'},'logits':{0:'batch',1:'candidates'}}
    with torch.no_grad():
        torch.onnx.export(model,collate(rows[-3:])[0],str(out/'model.onnx'),
                          input_names=INPUT_NAMES,output_names=['logits'],
                          dynamic_axes=dynamic,opset_version=17,dynamo=False)
    onnx.checker.check_model(str(out/'model.onnx'))
    engine=CpuExtractor(out); parity=[]
    # Deliberately interleave long and short rows to exercise dynamic sorting.
    for selected in [rows[:1],[rows[-1],rows[10],rows[-10],rows[20],rows[3],rows[-20],rows[40]],rows[-32:]]:
        with torch.no_grad(): reference=model(*collate(selected)[0]).numpy()
        feed=numpy_batch(selected);actual=engine.session.run(None,{k:v for k,v in feed.items() if k in engine.inputs})[0]
        same=all({key(y['atom']) for y in a}=={key(y['atom']) for y in b}
                 for a,b in zip(decode(selected,reference,meta['pairs']),decode(selected,actual,meta['pairs'])))
        err=float(np.max(np.abs(reference-actual)))
        parity.append(dict(batch=len(selected),max_abs_logit_error=err,decoded_parity=same))
        if not same or err>.001:raise AssertionError(parity[-1])
    report=dict(checkpoint_sha256=hashlib.sha256(pathlib.Path(a.checkpoint).read_bytes()).hexdigest(),
                model_bytes=(out/'model.onnx').stat().st_size,
                onnx_sha256=hashlib.sha256((out/'model.onnx').read_bytes()).hexdigest(),
                parameters=sum(p.numel() for p in model.parameters()),parity=parity,
                cpu_threads=2,model_family='factorized',config=ck['config'],
                source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in pathlib.Path(__file__).parent.glob('*.py')})
    if not a.smoke:
        start=time.monotonic();pred=[]
        for i in range(0,len(rows),48):pred.extend(engine.predict_encoded(rows[i:i+48]))
        report.update(cpu_seconds=time.monotonic()-start,cpu_metrics=metrics(rows,pred),cpu_domains=score(rows,pred))
        with (out/'cpu-dev-predictions.jsonl').open('w') as f:
            for row,prediction in zip(rows,pred):f.write(json.dumps({'id':row['id'],'prediction':prediction})+'\n')
    for name in ['grammar.py','prepare.py','runtime.py','evaluate_cpu.py']:
        shutil.copyfile(pathlib.Path(__file__).parent/name,out/name)
    (out/'export-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__': main()
