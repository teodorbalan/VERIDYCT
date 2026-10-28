import argparse
import hashlib
import json
import os
import pathlib
import resource
import shutil
import time
import numpy as np
import onnx
import onnxruntime as ort
import torch
from grammar import Grammar
from model import Extractor,collate
from runtime import INPUT_NAMES,CpuExtractor,encode_input,numpy_batch,decode
from train import read_rows,key
from select_ensemble import Ensemble,load_model,score

def metrics(rows,predictions):
    n=len(rows);correct=goldn=predn=exact=strict=contextn=contextok=multin=multiok=0
    for row,pred in zip(rows,predictions):
        g={key(a) for a in row['form']};a={key(p['atom']) for p in pred};correct+=len(g&a);goldn+=len(g);predn+=len(a);exact+=g==a
        strict+={json.dumps(x,sort_keys=True) for x in row['form']}=={json.dumps(p['atom'],sort_keys=True) for p in pred}
        if row['has_context']:contextn+=1;contextok+=g==a
        if len(g)>1:multin+=1;multiok+=g==a
    precision=correct/max(1,predn);recall=correct/max(1,goldn)
    return dict(rows=n,exact_rows=exact,exact=exact/max(1,n),strict_json_exact_rows=strict,gold_unique_atoms=goldn,predicted_unique_atoms=predn,correct_unique_atoms=correct,precision=precision,recall=recall,f1=2*precision*recall/max(1e-9,precision+recall),context_rows=contextn,context_exact=contextok,multi_rows=multin,multi_exact=multiok)

def main():
    p=argparse.ArgumentParser();group=p.add_mutually_exclusive_group(required=True);group.add_argument('--checkpoint');group.add_argument('--selection');p.add_argument('--data',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    torch.set_num_threads(2);torch.set_num_interop_threads(1);torch.backends.mha.set_fastpath_enabled(False)
    root=pathlib.Path(a.data);out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=True)
    if a.selection:
        selection=json.loads(pathlib.Path(a.selection).read_text());models=[];checkpoints=[];meta=None
        for member in selection['members']:
            if hashlib.sha256(pathlib.Path(member['checkpoint']).read_bytes()).hexdigest()!=member['sha256']:raise ValueError('Selected checkpoint changed')
            part,ck=load_model(member['checkpoint'],'cpu')
            if meta is None:meta=ck['meta']
            elif meta!=ck['meta']:raise ValueError('Incompatible member metadata')
            models.append(part);checkpoints.append(member)
        model=Ensemble(models).eval();checkpoint_hash=hashlib.sha256(pathlib.Path(a.selection).read_bytes()).hexdigest()
        shutil.copyfile(a.selection,out/'selection.json')
    else:
        ck=torch.load(a.checkpoint,map_location='cpu',weights_only=False);meta=ck['meta'];model=Extractor(len(meta['vocab']),len(meta['chars']),len(meta['pairs']),ck['config']);model.load_state_dict(ck['model']);model.eval()
        checkpoint_hash=hashlib.sha256(pathlib.Path(a.checkpoint).read_bytes()).hexdigest();checkpoints=[{'checkpoint':a.checkpoint,'epoch':ck['epoch'],'sha256':checkpoint_hash}]
    (out/'meta.json').write_text(json.dumps(meta,ensure_ascii=False));shutil.copyfile(root/'lexicon.json',out/'lexicon.json')
    rows=read_rows(root/'dev.jsonl');rows.sort(key=lambda r:len(r['tokens']))
    # Independently rebuild every input from text; exact match proves gold labels
    # are not required by the runtime preprocessing path.
    grammar=Grammar(json.loads((root/'lexicon.json').read_text()),meta['extra_names'])
    for r in rows:
        fresh=encode_input(r['text'],r['previous_text'],meta,grammar,r['id'])
        for k in ['tokens','chars','current_offset','has_context']:assert fresh[k]==r[k],(r['id'],k)
        assert fresh['candidates']==[{k:v for k,v in c.items() if k!='label'} for c in r['candidates']],r['id']
    sample=collate(rows[-3:])[0]
    dynamic={'words':{0:'batch',1:'tokens'},'chars':{0:'batch',1:'tokens'},'spans':{0:'batch',1:'candidates',2:'tokens'},'clauses':{0:'batch',1:'candidates',2:'tokens'},'kinds':{0:'batch',1:'candidates'},'logits':{0:'batch',1:'candidates'}}
    with torch.no_grad():torch.onnx.export(model,sample,str(out/'model.onnx'),input_names=INPUT_NAMES,output_names=['logits'],dynamic_axes=dynamic,opset_version=17,dynamo=False)
    onnx.checker.check_model(str(out/'model.onnx'))
    cpu=CpuExtractor(out);parity=[]
    for selected in [rows[:1],rows[100:107],rows[-32:]]:
        inp=collate(selected)[0]
        with torch.no_grad():ref=model(*inp).numpy()
        feed=numpy_batch(selected);actual=cpu.session.run(None,{k:v for k,v in feed.items() if k in cpu.inputs})[0]
        refdec=decode(selected,ref,meta['pairs']);dec=decode(selected,actual,meta['pairs'])
        same=all({key(x['atom']) for x in r}=={key(x['atom']) for x in s} for r,s in zip(refdec,dec))
        parity.append({'shape':list(ref.shape),'max_abs_logit_error':float(abs(ref-actual).max()),'decoded_parity':same})
        if not same:raise AssertionError('ONNX decode differs from PyTorch')
    started=time.monotonic();pred=[]
    for i in range(0,len(rows),48):pred.extend(cpu.predict_encoded(rows[i:i+48]))
    seconds=time.monotonic()-started;report={'checkpoint_or_selection_sha256':checkpoint_hash,'checkpoints':checkpoints,'onnx_sha256':hashlib.sha256((out/'model.onnx').read_bytes()).hexdigest(),'model_bytes':(out/'model.onnx').stat().st_size,'parameters':sum(x.numel() for x in model.parameters()),'input_rebuild_rows':len(rows),'parity':parity,'cpu_threads':2,'cpu_seconds':seconds,'cpu_rows_per_second':len(rows)/seconds,'cpu_metrics':metrics(rows,pred),'cpu_domains':score(rows,pred),'process_peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'note':'RSS includes PyTorch exporter; standalone ONNX runtime and constrained Docker benchmark follow separately.'}
    with (out/'cpu-dev-predictions.jsonl').open('w') as f:
        for r,prediction in zip(rows,pred):f.write(json.dumps({'id':r['id'],'prediction':prediction})+'\n')
    (out/'export-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':main()
