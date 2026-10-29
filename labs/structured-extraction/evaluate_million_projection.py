"""Same frozen extractor, paired inputs and padding, atomic projection only.

This measures extraction of literal recorded/asserted atoms. It does NOT evaluate
source/date binding, recursive AST parsing or note-grounded truth classification.
"""
import argparse
import collections
import hashlib
import json
import pathlib
import time
from grammar import canonical
from runtime import CpuExtractor, encode_input


def atom_key(atom):
    return atom['subject'],atom['attribute'],canonical(atom['value'])


def main():
    p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--bundle',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    data,out=pathlib.Path(a.data),pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
    engine=CpuExtractor(a.bundle);started=time.monotonic()
    raw=[[json.loads(x) for x in (data/('sample-v'+str(i)+'.jsonl')).open(encoding='utf-8')] for i in (1,2)]
    if len(raw[0])!=len(raw[1]):raise ValueError('Unpaired sample sizes')
    pairs=[];stats=[collections.defaultdict(collections.Counter),collections.defaultdict(collections.Counter)]
    counts=collections.Counter()
    for left,right in zip(*raw):
        if left['id']!=right['id']:raise ValueError('Unpaired sample IDs')
        counts['sample_pairs']+=1
        if not left['form'] or not right['form']:
            counts['no_literal_projection_in_at_least_one_version']+=1
            continue
        group='same_ast' if left['target'].get('structure')==right['target'].get('structure') else 'changed_ast'
        encoded=[]
        for row in (left,right):
            # Text only; source metadata and target are never encoder features.
            inputs=row['input'];previous=' '.join(c['text'] for c in inputs.get('context',[]))
            try:
                encoded.append(encode_input(inputs['text'],previous,engine.meta,engine.grammar,row['id']))
            except ValueError as exc:
                if '384 tokens' not in str(exc):raise
                encoded.append(None)
        pairs.append(dict(raw=[left,right],encoded=encoded,group=group,length=max(len(x['tokens']) if x else 0 for x in encoded)))
    pairs.sort(key=lambda x:(x['length'],x['raw'][0]['id']))
    paired=collections.defaultdict(collections.Counter)
    with (out/'predictions.jsonl').open('w',encoding='utf-8') as stream:
        for start in range(0,len(pairs),24):
            batch=pairs[start:start+24];rows=[r for item in batch for r in item['encoded'] if r is not None]
            predictions=iter(engine.predict_encoded(rows)) if rows else iter([])
            for item in batch:
                outcomes=[];outputs=[]
                for version,(rawrow,encoded) in enumerate(zip(item['raw'],item['encoded'])):
                    pred=next(predictions) if encoded else []
                    gold={atom_key(x) for x in rawrow['form']};actual={atom_key(x['atom']) for x in pred}
                    exact=encoded is not None and gold==actual;outcomes.append(exact)
                    schema='notes_logic' if rawrow['metadata']['task_schema'].startswith('provided_notes') else 'annotated_practice'
                    for name in ['all',item['group'],schema]:
                        stats[version][name].update(rows=1,gold=len(gold),predicted=len(actual),correct=len(gold&actual),exact=exact,overlength=int(encoded is None))
                    outputs.append(dict(exact=exact,overlength=encoded is None,gold=rawrow['form'],prediction=pred))
                for name in ['all',item['group']]:
                    paired[name]['both_correct' if all(outcomes) else 'v2_gain' if outcomes[1] else 'v2_loss' if outcomes[0] else 'both_wrong']+=1
                if item['raw'][0]['input']==item['raw'][1]['input']:
                    counts['identical_input_pairs']+=1
                    same={atom_key(x['atom']) for x in outputs[0]['prediction']}=={atom_key(x['atom']) for x in outputs[1]['prediction']}
                    counts['identical_input_prediction_mismatches']+=not same
                    if not same:raise AssertionError('Identical paired inputs produced different predictions')
                stream.write(json.dumps(dict(id=item['raw'][0]['id'],group=item['group'],versions=outputs),ensure_ascii=False)+'\n')
    for version in stats:
        for result in version.values():
            result['exact_rate']=result['exact']/max(1,result['rows']);result['precision']=result['correct']/max(1,result['predicted']);result['recall']=result['correct']/max(1,result['gold']);result['f1']=2*result['correct']/max(1,result['gold']+result['predicted'])
    report=dict(counts=dict(counts),v1=dict(stats[0]),v2=dict(stats[1]),paired=dict(paired),seconds=time.monotonic()-started,
                model_sha256=hashlib.sha256((pathlib.Path(a.bundle)/'model.onnx').read_bytes()).hexdigest(),
                sample_sha256={str(i):hashlib.sha256((data/('sample-v'+str(i)+'.jsonl')).read_bytes()).hexdigest() for i in (1,2)},
                protocol='Paired IDs; same model and .5 decode threshold; each pair shares one padded inference batch; last96 context tokens; >384 total rejected and counted wrong.',
                limitations=['Flat literal-atom projection only, NOT full JSON AST or truth accuracy.','Semantic scope, source IDs, dates, multiplicity and ordering not scored.',
                             'Changed-AST rows are changed tasks, not pure paraphrases.','No training on million rows for this comparison; source practice and older synthetic training can overlap.',
                             'No-literal or unresolved rows are out of scope for this metric, not counted as successes.'])
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
