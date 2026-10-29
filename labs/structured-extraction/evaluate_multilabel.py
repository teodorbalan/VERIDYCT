"""Raw JSONL evaluation for an explicitly frozen multilabel CPU bundle."""
import argparse
import collections
import hashlib
import json
import pathlib
from runtime_multilabel import MultiLabelCpuExtractor
from evaluate_cpu import evaluate,atomkey


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle',required=True);p.add_argument('--rows',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    out=pathlib.Path(a.out)
    if out.exists():raise ValueError('Use fresh evaluation directory')
    out.mkdir(parents=True)
    rows=[json.loads(x) for x in pathlib.Path(a.rows).read_text().splitlines()]
    engine=MultiLabelCpuExtractor(a.bundle)
    report=evaluate(engine,rows,out/'predictions.jsonl')
    byid={r['id']:r for r in rows};stats=collections.defaultdict(collections.Counter)
    for record in map(json.loads,(out/'predictions.jsonl').open()):
        row=byid[record['id']];g={atomkey(x) for x in record['gold']};actual={atomkey(x['atom']) for x in record['prediction']}
        for group in [row.get('domain','all'),row.get('case','ordinary')]:stats[group].update(rows=1,exact=int(g==actual),gold=len(g),predicted=len(actual),correct=len(g&actual))
    for group in stats.values():group['exact_rate']=group['exact']/group['rows'];group['f1']=2*group['correct']/max(1,group['gold']+group['predicted'])
    report.update(case_groups=dict(stats),decoder='multilabel_sigmoid',threshold=engine.threshold,rows_sha256=hashlib.sha256(pathlib.Path(a.rows).read_bytes()).hexdigest(),model_sha256=hashlib.sha256((pathlib.Path(a.bundle)/'model.onnx').read_bytes()).hexdigest())
    (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
