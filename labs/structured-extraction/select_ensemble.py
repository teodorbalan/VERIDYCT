"""Compare completed runs and predeclared uniform top-2/3/4 ensembles on DEV only."""
import argparse
import hashlib
import json
import pathlib
import time
import numpy as np
import torch
from torch import nn
from model import Extractor,collate
from runtime import decode
from train import read_rows,key

class Ensemble(nn.Module):
    def __init__(self,models):super().__init__();self.models=nn.ModuleList(models)
    def forward(self,words,chars,spans,clauses,kinds):
        probabilities=[m(words,chars,spans,clauses,kinds).softmax(-1) for m in self.models]
        return torch.stack(probabilities).mean(0).clamp_min(1e-12).log()

def load_model(checkpoint,device):
    ck=torch.load(checkpoint,map_location='cpu',weights_only=False);meta=ck['meta'];model=Extractor(len(meta['vocab']),len(meta['chars']),len(meta['pairs']),ck['config']);model.load_state_dict(ck['model']);return model.to(device).eval(),ck

def score(rows,predictions):
    domains={}
    for r,pred in zip(rows,predictions):
        d=domains.setdefault(r.get('domain','synthetic'),dict(rows=0,exact=0,gold=0,predicted=0,correct=0));g={key(a) for a in r['form']};a={key(p['atom']) for p in pred}
        d['rows']+=1;d['exact']+=g==a;d['gold']+=len(g);d['predicted']+=len(a);d['correct']+=len(g&a)
    for d in domains.values():d['exact_rate']=d['exact']/d['rows'];d['f1']=2*d['correct']/max(1,d['gold']+d['predicted'])
    return {'domains':domains,'selection_score':sum(d['exact_rate'] for d in domains.values())/len(domains)}

def main():
    p=argparse.ArgumentParser();p.add_argument('--runs',required=True);p.add_argument('--data',required=True);p.add_argument('--out',required=True);p.add_argument('--device',default='cuda');a=p.parse_args()
    torch.set_num_threads(4);torch.set_num_interop_threads(1)
    root=pathlib.Path(a.runs);out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=True)
    paths=sorted(root.glob('*/run.json'))
    if len(paths)!=8 or any(not (p.parent/'result.json').exists() for p in paths):raise ValueError('All eight configured runs must complete before selection')
    ranked=sorted([(json.loads((p.parent/'result.json').read_text())['selection_score'],p.parent) for p in paths],reverse=True)
    rows=read_rows(pathlib.Path(a.data)/'dev.jsonl');rows.sort(key=lambda r:len(r['tokens']));batch=48
    batches=[rows[i:i+batch] for i in range(0,len(rows),batch)];models=[];records=[];metadata=None
    for previous_score,path in ranked[:4]:
        model,ck=load_model(path/'best.pt',a.device)
        if metadata is None:metadata=ck['meta']
        elif metadata!=ck['meta']:raise ValueError('Cannot ensemble incompatible metadata')
        models.append(model);records.append({'run':path.name,'checkpoint':str(path/'best.pt'),'sha256':hashlib.sha256((path/'best.pt').read_bytes()).hexdigest(),'previous_selection_score':previous_score})
    options=[];cached=[]
    with torch.inference_mode():
        for j,model in enumerate(models):
            probs=[]
            for selected in batches:
                inputs=collate(selected)[0];probs.append(model(*(x.to(a.device) for x in inputs)).softmax(-1).cpu().numpy())
            cached.append(probs)
        for count in [1,2,3,4]:
            pred=[]
            for i,selected in enumerate(batches):
                mean=sum(cached[j][i] for j in range(count))/count
                pred.extend(decode(selected,np.log(mean.clip(1e-12)),metadata['pairs']))
            result=score(rows,pred);result['members']=count;options.append(result)
            with (out/f'dev-top{count}.jsonl').open('w') as f:
                for r,prediction in zip(rows,pred):f.write(json.dumps({'id':r['id'],'domain':r['domain'],'text':r['text'],'previous_text':r['previous_text'],'gold':r['form'],'prediction':prediction,'exact':{key(x) for x in r['form']}=={key(x['atom']) for x in prediction}})+'\n')
            print(json.dumps(result),flush=True)
    winner=max(options,key=lambda x:(x['selection_score'],-x['members']))
    manifest={'policy':'uniform top-1, top-2, top-3, top-4 ranked by equal official/synthetic dev exact rate; ties prefer fewer models','options':options,'selected':winner,'members':records[:winner['members']],'all_ranked':[(s,str(p)) for s,p in ranked],'sealed_gold_read':False,'source_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()}
    (out/'selection.json').write_text(json.dumps(manifest,indent=2));print('SELECTED '+json.dumps(winner),flush=True)

if __name__=='__main__':main()
