"""CPU 2x2 revision cross-evaluation: flat extraction only, never truth/AST scores."""
import argparse
import hashlib
import json
import pathlib
import time
from export_cpu import metrics
from runtime import CpuExtractor
from select_ensemble import score
from train import read_rows


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--data',required=True);p.add_argument('--v1-bundle',required=True)
    p.add_argument('--v2-bundle',required=True);p.add_argument('--out',required=True)
    p.add_argument('--base-bundle')
    a=p.parse_args();out=pathlib.Path(a.out)
    if out.exists():raise ValueError('Use a fresh evaluation directory')
    out.mkdir(parents=True);root=pathlib.Path(a.data)
    rows={v:read_rows(root/v/'paired-dev.jsonl') for v in ('v1','v2')}
    if [r['id'] for r in rows['v1']]!=[r['id'] for r in rows['v2']]:raise ValueError('Paired IDs/order differ')
    report={'scope':'Internal case-heldout literal atom extraction; original sources shared with training; no AST or truth-label evaluation','cells':[]}
    models=[('v1',a.v1_bundle),('v2',a.v2_bundle)]
    if a.base_bundle:models.insert(0,('base',a.base_bundle))
    for model,bundle in models:
        engine=CpuExtractor(bundle,threads=2)
        for view,data in rows.items():
            data_meta=json.loads((root/view/'meta.json').read_text())
            for key in ('vocab','chars','pairs'):
                if engine.meta[key]!=data_meta[key]:raise ValueError('Incompatible metadata')
            predictions=[];start=time.monotonic()
            for i in range(0,len(data),48):predictions.extend(engine.predict_encoded(data[i:i+48]))
            cell={'model_training_view':model,'input_view':view,'seconds':time.monotonic()-start,
                  'metrics':metrics(data,predictions),'domains':score(data,predictions),
                  'model_sha256':hashlib.sha256((pathlib.Path(bundle)/'model.onnx').read_bytes()).hexdigest()}
            report['cells'].append(cell)
            with (out/f'{model}-on-{view}.jsonl').open('w') as f:
                for row,prediction in zip(data,predictions):f.write(json.dumps({'id':row['id'],'prediction':prediction})+'\n')
            print(json.dumps(cell),flush=True)
    (out/'report.json').write_text(json.dumps(report,indent=2))


if __name__=='__main__':main()
