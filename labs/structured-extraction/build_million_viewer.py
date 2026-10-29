"""Build a self-contained, bounded paired example viewer; no network required."""
import argparse
import collections
import hashlib
import json
import pathlib


def main():
    p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--out',required=True);p.add_argument('--template',required=True);a=p.parse_args()
    root=pathlib.Path(a.data);rows=[{r['id']:r for r in map(json.loads,(root/('sample-v'+str(i)+'.jsonl')).read_text(encoding='utf-8').splitlines())} for i in (1,2)]
    predictions=list(map(json.loads,(root/'frozen-v3-projection/predictions.jsonl').read_text(encoding='utf-8').splitlines()));groups=collections.defaultdict(list)
    for pred in predictions:
        left,right=(x['exact'] for x in pred['versions'])
        outcome='correct' if left and right else 'gain' if right else 'loss' if left else 'wrong'
        groups[outcome].append(pred)
    cases=[]
    for outcome,items in groups.items():
        items.sort(key=lambda x:hashlib.sha256(('viewer:'+x['id']).encode()).hexdigest())
        for pred in items[:8]:
            pair=[rows[i][pred['id']] for i in range(2)]
            for row in pair:
                row.pop('form',None);row.pop('diagnostic_only',None)
                row['metadata']={k:v for k,v in row['metadata'].items() if k in ('family','task_schema','source_ids')}
            predictions_compact=[dict(exact=v['exact'],prediction=[dict(atom=p['atom']) for p in v['prediction']]) for v in pred['versions']]
            cases.append(dict(id=pred['id'],v1=pair[0],v2=pair[1],predictions=predictions_compact,outcome=outcome,
                              same_ast=pair[0]['target']['structure']==pair[1]['target']['structure'],
                              search=(pred['id']+' '+pair[0]['input']['text']+' '+pair[1]['input']['text']).lower()))
    cases.sort(key=lambda x:({'gain':0,'loss':1,'wrong':2,'correct':3}[x['outcome']],x['id']))
    report=json.loads((root/'frozen-v3-projection/report.json').read_text(encoding='utf-8'));data=dict(cases=cases,model_sha=report['model_sha256'])
    encoded=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    html=pathlib.Path(a.template).read_text(encoding='utf-8').replace('__DATA__',encoded)
    out=pathlib.Path(a.out);out.write_text(html,encoding='utf-8')
    if out.stat().st_size>=512*1024:raise ValueError('Viewer exceeds inline visual size budget')
    print(json.dumps(dict(cases=len(cases),bytes=out.stat().st_size,sha256=hashlib.sha256(out.read_bytes()).hexdigest())))


if __name__=='__main__':main()
