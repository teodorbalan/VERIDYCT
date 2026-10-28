import argparse
import collections
import hashlib
import json
import os
import pathlib
import platform
import random
import time
import torch
import numpy as np
from torch.utils.data import DataLoader
from grammar import canonical
from model import Extractor,CONFIGS,collate

def read_rows(path):
    with open(path,encoding='utf-8') as f:return [json.loads(x) for x in f]

def key(atom):return (atom['subject'],atom['attribute'],canonical(atom['value']))

def predictions(rows,probs,pairs,threshold=.5):
    result=[]
    scores,labels=probs.max(-1)
    for i,r in enumerate(rows):
        pred=[];seen=set()
        for j,c in enumerate(r['candidates']):
            label=int(labels[i,j]);score=float(scores[i,j])
            if not label or score<threshold:continue
            s,a=pairs[label-1];atom={'subject':s,'attribute':a,'value':c['value']}
            if key(atom) in seen:continue
            seen.add(key(atom));pred.append({'atom':atom,'score':score,'span':[c['start'],c['end']]})
        result.append(pred)
    return result

@torch.inference_mode()
def evaluate(model,loader,device,pairs,save=None):
    model.eval();counts=collections.Counter();bykind=collections.defaultdict(collections.Counter);domains=collections.defaultdict(collections.Counter);examples=[]
    started=time.monotonic()
    for inputs,_,rows in loader:
        probs=model(*(x.to(device) for x in inputs)).float().softmax(-1).cpu()
        preds=predictions(rows,probs,pairs)
        for r,pred in zip(rows,preds):
            gold={key(a) for a in r['form']};actual={key(p['atom']) for p in pred};tp=len(gold&actual)
            counts.update(rows=1,gold=len(gold),predicted=len(actual),correct=tp,exact_rows=int(gold==actual))
            domains[r.get('domain','synthetic')].update(rows=1,exact=int(gold==actual),gold=len(gold),predicted=len(actual),correct=tp)
            strict_gold={json.dumps(a,sort_keys=True) for a in r['form']};strict_actual={json.dumps(p['atom'],sort_keys=True) for p in pred}
            counts['strict_json_exact_rows']+=strict_gold==strict_actual
            if r['has_context']:counts.update(context_rows=1,context_exact=int(gold==actual))
            if len(gold)>1:counts.update(multi_rows=1,multi_exact=int(gold==actual))
            for a in gold:bykind[json.loads(a[2])['kind']]['gold']+=1
            for a in actual:
                k=json.loads(a[2])['kind'];bykind[k]['predicted']+=1;bykind[k]['correct']+=a in gold
            if save:examples.append({'id':r['id'],'text':r['text'],'previous_text':r['previous_text'],'gold':r['form'],'prediction':pred,'exact':gold==actual})
    result=dict(counts);p=counts['correct']/max(1,counts['predicted']);r=counts['correct']/max(1,counts['gold'])
    result.update(precision=p,recall=r,f1=2*p*r/max(1e-9,p+r),exact=counts['exact_rows']/max(1,counts['rows']),seconds=time.monotonic()-started,by_kind=dict(bykind))
    for name,d in domains.items():d['exact_rate']=d['exact']/max(1,d['rows']);d['f1']=2*d['correct']/max(1,d['gold']+d['predicted'])
    result['domains']=dict(domains);result['selection_score']=sum(d['exact_rate'] for d in domains.values())/len(domains)
    if save:
        with open(save,'w',encoding='utf-8') as f:
            for row in examples:f.write(json.dumps(row,ensure_ascii=False)+'\n')
    return result

def train(a):
    torch.set_num_threads(4);torch.set_num_interop_threads(2)
    torch.set_float32_matmul_precision('high')
    random.seed(a.seed);torch.manual_seed(a.seed)
    if not torch.cuda.is_available() and a.device.startswith('cuda'):raise RuntimeError('CUDA unavailable; refusing silent CPU fallback')
    device=torch.device(a.device);root=pathlib.Path(a.data);out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=True)
    if (out/'best.pt').exists() and not a.resume:raise ValueError('Refusing to overwrite checkpoint; use a fresh out or --resume')
    meta=json.loads((root/'meta.json').read_text());trainrows=read_rows(root/'train.jsonl');devrows=read_rows(root/'dev.jsonl')
    if a.smoke:trainrows=trainrows[:128];devrows=devrows[:64]
    # Development is length-sorted below; training uses a fully shuffled sampler.
    trainrows.sort(key=lambda r:len(r['tokens']))
    loader=DataLoader(trainrows,batch_size=a.batch,shuffle=True,collate_fn=collate,num_workers=2,persistent_workers=True)
    devrows.sort(key=lambda r:len(r['tokens']))
    devloader=DataLoader(devrows,batch_size=a.batch,shuffle=False,collate_fn=collate,num_workers=2,persistent_workers=True)
    config=CONFIGS[a.variant];model=Extractor(len(meta['vocab']),len(meta['chars']),len(meta['pairs']),config).to(device)
    if a.pretrained:
        matrix=np.load(root/'vectors.npy')
        if matrix.shape!=tuple(model.word.weight.shape):raise ValueError('Pretrained vector shape mismatch')
        with torch.no_grad():model.word.weight.copy_(torch.from_numpy(matrix).to(device))
    opt=torch.optim.AdamW(model.parameters(),lr=a.lr,weight_decay=.01)
    # NONE is common; downweight it, never discard hard negative candidates.
    weights=torch.ones(len(meta['pairs'])+1,device=device);weights[0]=.25
    criterion=torch.nn.CrossEntropyLoss(weight=weights,ignore_index=-100)
    info={'variant':a.variant,'seed':a.seed,'config':config,'parameters':sum(p.numel() for p in model.parameters()),'torch':torch.__version__,'python':platform.python_version(),'gpu':torch.cuda.get_device_name() if device.type=='cuda' else None,'cuda_visible_devices':os.getenv('CUDA_VISIBLE_DEVICES'),'data_sha256':hashlib.sha256((root/'meta.json').read_bytes()).hexdigest(),'train_rows':len(trainrows),'dev_rows':len(devrows),'arguments':vars(a),'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in pathlib.Path(__file__).parent.glob('*.py')}}
    (out/'run.json').write_text(json.dumps(info,indent=2));print(json.dumps(info),flush=True)
    best=-1;start_epoch=0;stale=0;started=time.monotonic()
    if a.resume:
        ck=torch.load(out/'last.pt',map_location=device,weights_only=False);model.load_state_dict(ck['model']);opt.load_state_dict(ck['optimizer']);start_epoch=ck['epoch'];best=ck['best']
    try:
        for epoch in range(start_epoch,a.epochs):
            model.train();loss_sum=0;n=0;t0=time.monotonic()
            for step,(inputs,labels,rows) in enumerate(loader):
                inputs=[x.to(device) for x in inputs];labels=labels.to(device)
                opt.zero_grad(set_to_none=True);logits=model(*inputs);loss=criterion(logits.reshape(-1,logits.shape[-1]),labels.flatten())
                loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.0);opt.step();loss_sum+=float(loss.detach());n+=len(rows)
                if step and step%100==0:print(json.dumps({'epoch':epoch+1,'step':step,'loss':loss_sum/(step+1),'rows_per_second':n/(time.monotonic()-t0)}),flush=True)
            elapsed=time.monotonic()-t0;metrics=evaluate(model,devloader,device,meta['pairs'])
            rec={'epoch':epoch+1,'loss':loss_sum/len(loader),'train_seconds':elapsed,'rows_per_second':n/elapsed,'dev':metrics,'elapsed_seconds':time.monotonic()-started,'gpu_peak_mib':torch.cuda.max_memory_allocated()/2**20 if device.type=='cuda' else 0}
            print(json.dumps(rec),flush=True)
            with (out/'metrics.jsonl').open('a') as f:f.write(json.dumps(rec)+'\n')
            improved=metrics['selection_score']>best
            if improved:best=metrics['selection_score'];stale=0
            else:stale+=1
            checkpoint={'model':model.state_dict(),'optimizer':opt.state_dict(),'epoch':epoch+1,'best':best,'config':config,'meta':meta,'metrics':metrics}
            torch.save(checkpoint,out/'last.tmp');os.replace(out/'last.tmp',out/'last.pt')
            if improved:torch.save(checkpoint,out/'best.tmp');os.replace(out/'best.tmp',out/'best.pt')
            if stale>=a.patience:break
    except KeyboardInterrupt:
        print('Interrupted; previous epoch checkpoints retained',flush=True);return
    ck=torch.load(out/'best.pt',map_location=device,weights_only=False);model.load_state_dict(ck['model'])
    final=evaluate(model,devloader,device,meta['pairs'],out/'dev-predictions.jsonl')
    final.update(best_epoch=ck['epoch'],total_seconds=time.monotonic()-started,variant=a.variant,parameters=info['parameters'])
    (out/'result.json').write_text(json.dumps(final,indent=2));print('COMPLETE '+json.dumps(final),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--out',required=True);p.add_argument('--variant',choices=CONFIGS,required=True);p.add_argument('--device',default='cuda');p.add_argument('--epochs',type=int,default=35);p.add_argument('--patience',type=int,default=6);p.add_argument('--batch',type=int,default=48);p.add_argument('--lr',type=float,default=.002);p.add_argument('--seed',type=int,default=271828);p.add_argument('--smoke',action='store_true');p.add_argument('--resume',action='store_true');p.add_argument('--pretrained',action='store_true');train(p.parse_args())
