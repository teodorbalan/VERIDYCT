"""Separate BCE candidate classifier, including shared-value coordination targets."""
import argparse
import collections
import hashlib
import json
import os
import pathlib
import random
import time
import numpy as np
import torch
from torch.utils.data import DataLoader
from model import Extractor,collate as collate_base
from runtime_multilabel import decode_multilabel
from train import read_rows,key


def collate_multi(rows):
    inputs=collate_base(rows)[0];count=inputs[2].shape[1]
    targets=torch.full((len(rows),count,514),-100.,dtype=torch.float32)
    for i,row in enumerate(rows):
        for j,candidate in enumerate(row['candidates']):
            if candidate['labels'] is None:continue
            targets[i,j]=0
            for label in candidate['labels']:targets[i,j,label-1]=1
    return inputs,targets,rows


def metrics(rows,predictions):
    stats=collections.defaultdict(collections.Counter)
    for row,pred in zip(rows,predictions):
        gold={key(x) for x in row['form']};actual={key(x['atom']) for x in pred}
        names=[row['domain']]
        if row.get('case','ordinary')!='ordinary':names.append('coord_'+row['case'])
        for name in names:stats[name].update(rows=1,exact=int(gold==actual),gold=len(gold),predicted=len(actual),correct=len(gold&actual))
    for group in stats.values():
        group['exact_rate']=group['exact']/group['rows'];group['f1']=2*group['correct']/max(1,group['gold']+group['predicted'])
    score=.5*stats['official']['exact_rate']+.25*stats['synthetic']['exact_rate']+.25*stats['coordination']['exact_rate']
    return {'groups':dict(stats),'selection_score':score}


@torch.inference_mode()
def evaluate(model,loader,device,pairs,thresholds=(.5,),save=None):
    model.eval();rows_all=[];outputs={t:[] for t in thresholds}
    for inputs,_,rows in loader:
        logits=model(*(x.to(device) for x in inputs)).float().cpu().numpy()
        for threshold in thresholds:outputs[threshold].extend(decode_multilabel(rows,logits,pairs,threshold))
        rows_all.extend(rows)
    scores={str(t):metrics(rows_all,outputs[t]) for t in thresholds}
    winner=max(thresholds,key=lambda t:(scores[str(t)]['selection_score'],-abs(t-.5)))
    if save:
        with pathlib.Path(save).open('w') as f:
            for row,pred in zip(rows_all,outputs[winner]):f.write(json.dumps({'id':row['id'],'domain':row['domain'],'case':row.get('case'),'text':row['text'],'previous_text':row['previous_text'],'gold':row['form'],'prediction':pred,'exact':{key(x) for x in row['form']}=={key(x['atom']) for x in pred}})+'\n')
    return dict(scores[str(winner)],threshold=winner,threshold_options=scores)


def warm_start(model,meta,path):
    ck=torch.load(path,map_location='cpu',weights_only=False)
    if ck['meta']['pairs']!=meta['pairs']:raise ValueError('Pair schemas differ')
    state=model.state_dict();copied=[]
    for name,tensor in ck['model'].items():
        if name in ['word.weight','char.weight']:
            lookup='vocab' if name=='word.weight' else 'chars'
            for item,old_index in ck['meta'][lookup].items():
                if item in meta[lookup]:state[name][meta[lookup][item]]=tensor[old_index]
            copied.append(name)
        elif name in state and state[name].shape==tensor.shape and not name.startswith('head.3'):
            state[name]=tensor;copied.append(name)
    model.load_state_dict(state)
    return {'checkpoint_sha256':hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest(),'copied_encoder_tensors':copied,'output_classifier':'fresh sigmoid head; no graph classifier imported'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--out',required=True);p.add_argument('--warm');p.add_argument('--seed',type=int,default=271828);p.add_argument('--epochs',type=int,default=30);p.add_argument('--patience',type=int,default=7);p.add_argument('--batch',type=int,default=48);p.add_argument('--lr',type=float,default=.0008);a=p.parse_args()
    torch.set_num_threads(4);torch.set_num_interop_threads(2);torch.set_float32_matmul_precision('high')
    if not torch.cuda.is_available():raise RuntimeError('CUDA required for this training run')
    random.seed(a.seed);torch.manual_seed(a.seed);device=torch.device('cuda')
    data=pathlib.Path(a.data);out=pathlib.Path(a.out)
    if out.exists():raise ValueError('Use a fresh training output')
    out.mkdir(parents=True);meta=json.loads((data/'meta.json').read_text())
    train=read_rows(data/'train.jsonl');dev=read_rows(data/'dev.jsonl');dev.sort(key=lambda r:len(r['tokens']))
    loader=DataLoader(train,batch_size=a.batch,shuffle=True,collate_fn=collate_multi,num_workers=2,persistent_workers=True)
    valid=DataLoader(dev,batch_size=a.batch,collate_fn=collate_multi,num_workers=2,persistent_workers=True)
    config=dict(encoder='lstm',hidden=128,layers=1,char=True)
    model=Extractor(len(meta['vocab']),len(meta['chars']),len(meta['pairs']),config)
    with torch.no_grad():model.word.weight.copy_(torch.from_numpy(np.load(data/'vectors.npy')));model.head[-1].bias.fill_(-4)
    warm=warm_start(model,meta,a.warm) if a.warm else None
    model=model.to(device);opt=torch.optim.AdamW(model.parameters(),lr=a.lr,weight_decay=.01)
    info={'decoder':'multilabel_sigmoid','seed':a.seed,'config':config,'parameters':sum(x.numel() for x in model.parameters()),'training_rows':len(train),'development_rows':len(dev),'meta_sha256':hashlib.sha256((data/'meta.json').read_bytes()).hexdigest(),'warm_start':warm,'gpu':torch.cuda.get_device_name(),'cuda_visible_devices':os.getenv('CUDA_VISIBLE_DEVICES'),'arguments':vars(a),'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in pathlib.Path(__file__).parent.glob('*.py')}}
    (out/'run.json').write_text(json.dumps(info,indent=2));print(json.dumps(info),flush=True)
    best=-1;stale=0;started=time.monotonic();pos_weight=torch.full((514,),32.,device=device)
    for epoch in range(1,a.epochs+1):
        model.train();loss_total=0;begin=time.monotonic()
        for inputs,target,_ in loader:
            inputs=[x.to(device) for x in inputs];target=target.to(device);mask=target[:,:,0]>=0;y=target.clamp_min(0)
            opt.zero_grad(set_to_none=True);logits=model(*inputs)[:,:,1:]
            loss=torch.nn.functional.binary_cross_entropy_with_logits(logits,y,pos_weight=pos_weight,reduction='none').mean(-1)
            weights=torch.where(y.sum(-1)>0,1.,.25)*mask;loss=(loss*weights).sum()/weights.sum().clamp_min(1)
            loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.);opt.step();loss_total+=float(loss.detach())
        score=evaluate(model,valid,device,meta['pairs']);record={'epoch':epoch,'loss':loss_total/len(loader),'train_seconds':time.monotonic()-begin,'dev':score,'elapsed_seconds':time.monotonic()-started,'gpu_peak_mib':torch.cuda.max_memory_allocated()/2**20}
        with (out/'metrics.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
        print(json.dumps(record),flush=True)
        if score['selection_score']>best:best=score['selection_score'];stale=0
        else:stale+=1
        checkpoint={'model':model.state_dict(),'config':config,'meta':meta,'epoch':epoch,'metrics':score,'decoder':'multilabel_sigmoid'}
        torch.save(checkpoint,out/'last.tmp');os.replace(out/'last.tmp',out/'last.pt')
        if stale==0:torch.save(checkpoint,out/'best.tmp');os.replace(out/'best.tmp',out/'best.pt')
        if stale>=a.patience:break
    ck=torch.load(out/'best.pt',map_location=device,weights_only=False);model.load_state_dict(ck['model'])
    final=evaluate(model,valid,device,meta['pairs'],(.25,.35,.5,.65,.8),out/'dev-predictions.jsonl')
    final.update(total_seconds=time.monotonic()-started,best_epoch=ck['epoch'],parameters=info['parameters'])
    ck['meta']['selected_threshold']=final['threshold'];ck['metrics']=final
    torch.save(ck,out/'selected.pt');(out/'result.json').write_text(json.dumps(final,indent=2));print('COMPLETE '+json.dumps(final),flush=True)


if __name__=='__main__':main()
