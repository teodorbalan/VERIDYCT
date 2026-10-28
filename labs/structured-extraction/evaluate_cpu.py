"""End-to-end CPU evaluation from raw text, including preprocessing and decoding."""
import argparse
import collections
import csv
import hashlib
import io
import json
import pathlib
import resource
import time
import zipfile
from grammar import canonical
from runtime import CpuExtractor,encode_input

def atomkey(a):return (a['subject'],a['attribute'],canonical(a['value']))

def evaluate(engine,rows,out,batch=48):
    start=time.monotonic();encoded=[]
    for r in rows:
        item=encode_input(r['text'],r.get('previous_text',''),engine.meta,engine.grammar,r['id']);item['form']=r['form'];item['visible']=r.get('visible',False);encoded.append(item)
    encoded.sort(key=lambda r:len(r['tokens']));stats=collections.defaultdict(collections.Counter);bykind=collections.defaultdict(collections.Counter)
    with open(out,'w',encoding='utf-8') as f:
        for i in range(0,len(encoded),batch):
            selected=encoded[i:i+batch];preds=engine.predict_encoded(selected)
            for r,pred in zip(selected,preds):
                g={atomkey(a) for a in r['form']};a={atomkey(p['atom']) for p in pred}
                groups=['all','visible' if r['visible'] else 'targets']
                if r['has_context']:groups.append('context')
                if len(g)>1:groups.append('multiple')
                sg={json.dumps(x,sort_keys=True) for x in r['form']};sa={json.dumps(x['atom'],sort_keys=True) for x in pred}
                for group in groups:stats[group].update(rows=1,gold=len(g),predicted=len(a),correct=len(g&a),exact=int(g==a),strict_json_exact=int(sg==sa))
                for value in g:bykind[json.loads(value[2])['kind']]['gold']+=1
                for value in a:
                    k=json.loads(value[2])['kind'];bykind[k]['predicted']+=1;bykind[k]['correct']+=value in g
                f.write(json.dumps({'id':r['id'],'text':r['text'],'previous_text':r['previous_text'],'gold':r['form'],'prediction':pred,'exact':g==a},ensure_ascii=False)+'\n')
    seconds=time.monotonic()-start
    for group,c in stats.items():
        c['exact_rate']=c['exact']/max(1,c['rows']);c['precision']=c['correct']/max(1,c['predicted']);c['recall']=c['correct']/max(1,c['gold']);c['f1']=2*c['correct']/max(1,c['gold']+c['predicted'])
    return {'groups':dict(stats),'by_kind':dict(bykind),'seconds_including_preprocessing':seconds,'rows_per_second':len(rows)/seconds,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}

def main():
    p=argparse.ArgumentParser();p.add_argument('--bundle',required=True);p.add_argument('--out',required=True);p.add_argument('--csv');p.add_argument('--archive');p.add_argument('--release');p.add_argument('--context',choices=['none','annotated','previous3'],default='none');p.add_argument('--model',default='model.onnx');p.add_argument('--repeat',type=int,default=1);p.add_argument('--batch',type=int,default=48);a=p.parse_args()
    if a.repeat<1:raise ValueError('repeat must be positive')
    out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=True)
    if (out/'report.json').exists():raise ValueError('Use a fresh output directory; evaluation reports are immutable')
    engine=CpuExtractor(a.bundle,a.model)
    if a.csv:
        with open(a.csv,encoding='utf-8-sig',newline='') as f:rows=[dict(r,form=json.loads(r['form']),previous_text='') for r in csv.DictReader(f)]
        source={'csv_sha256':hashlib.sha256(pathlib.Path(a.csv).read_bytes()).hexdigest()}
    else:
        if not a.archive or not a.release:raise ValueError('Provide csv or archive+release')
        if a.release not in ['external-development','external-calibration','external-sealed','calibration-20000','sealed-20000']:raise ValueError('Unsupported evaluation release')
        name=f'evaluation-data/realistic-v1/{a.release}/gold/rows.jsonl'
        with zipfile.ZipFile(a.archive) as z:
            raw=z.read(name);rows=[json.loads(x) for x in raw.splitlines()]
            public=list(csv.DictReader(io.StringIO(z.read(f'evaluation-data/realistic-v1/{a.release}/public/universe.csv').decode())))
        gold={r['id']:r for r in rows};rows=[gold[r['id']] for r in public]
        if any(r['text']!=p['text'] for r,p in zip(rows,public)):raise ValueError('Public/gold text mismatch')
        byid={r['id']:r for r in rows}
        for r in rows:r['previous_text']=byid[r['context_row_id']]['text'] if a.context=='annotated' and r.get('context_row_id') else ''
        source={'release':a.release,'gold_sha256':hashlib.sha256(raw).hexdigest()}
    if a.context=='previous3':
        for i,r in enumerate(rows):r['previous_text']=' '.join(x['text'] for x in rows[max(0,i-3):i])
    rows=rows*a.repeat
    report=evaluate(engine,rows,out/'predictions.jsonl',a.batch)
    report.update(source=source,context_mode=a.context,repeat=a.repeat,batch=a.batch,model_sha256=hashlib.sha256((pathlib.Path(a.bundle)/a.model).read_bytes()).hexdigest(),cpu_threads=2,scope='extraction only; not truth verification; annotated context is a component diagnostic when not present in runtime input')
    (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':main()
