"""Export a mixed-family, mixed-vocabulary selection to one offline CPU model."""
import argparse
import hashlib
import json
import pathlib
import shutil
import time
import numpy as np
import onnx
import torch
from compare_stacks import load_any, MappedExtractor, MixedEnsemble, evaluate_probabilities
from model import collate
from runtime import CpuExtractor, encode_input, INPUT_NAMES, numpy_batch, decode
from train import read_rows, key


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--selection', required=True)
    p.add_argument('--data', required=True)
    p.add_argument('--challenge-dev', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    selection_path, out = pathlib.Path(a.selection), pathlib.Path(a.out)
    if out.exists():
        raise ValueError('Use a fresh immutable bundle')
    out.mkdir(parents=True)
    selected = json.loads(selection_path.read_text())
    meta_path = selection_path.parent/'meta.json'
    if hashlib.sha256(meta_path.read_bytes()).hexdigest() != selected['master_meta_sha256']:
        raise ValueError('Master vocabulary changed after selection')
    meta = json.loads(meta_path.read_text())
    if selected['grammar'] == 'robust':
        meta['grammar_variant'] = 'money-period-v1'
    models = []
    for member in selected['members']:
        if hashlib.sha256(pathlib.Path(member['checkpoint']).read_bytes()).hexdigest()!=member['sha256']:
            raise ValueError('Selected checkpoint changed')
        model, ck = load_any(member['checkpoint'])
        models.append(MappedExtractor(model, meta, ck['meta']))
    model = MixedEnsemble(models).eval()
    (out/'meta.json').write_text(json.dumps(meta, ensure_ascii=False))
    shutil.copyfile(pathlib.Path(a.data)/'lexicon.json', out/'lexicon.json')
    shutil.copyfile(selection_path, out/'selection.json')
    for name in ['grammar.py','grammar_robust.py','prepare.py','runtime.py','evaluate_cpu.py']:
        shutil.copyfile(pathlib.Path(__file__).parent/name, out/name)
    from grammar import Grammar
    if meta.get('grammar_variant'):
        from grammar_robust import RobustGrammar as Grammar
    grammar = Grammar(json.loads((out/'lexicon.json').read_text()), meta['extra_names'])
    raw = read_rows(pathlib.Path(a.data)/'dev.jsonl')
    challenge = read_rows(a.challenge_dev)
    if any(r.get('split')!='dev' for r in challenge):
        raise ValueError('Only development fixtures accepted')
    raw += [dict(r,domain='challenge') for r in challenge if not r.get('ambiguous') and not r.get('diagnostic')]
    rows = []
    for r in raw:
        row=encode_input(r['text'],r.get('previous_text',''),meta,grammar,r['id'])
        row.update(form=r['form'],domain=r['domain'])
        rows.append(row)
    rows.sort(key=lambda r:(len(r['tokens']),r['id']))
    dynamic={'words':{0:'batch',1:'tokens'},'chars':{0:'batch',1:'tokens'},
             'spans':{0:'batch',1:'candidates',2:'tokens'},
             'clauses':{0:'batch',1:'candidates',2:'tokens'},
             'kinds':{0:'batch',1:'candidates'},'logits':{0:'batch',1:'candidates'}}
    with torch.no_grad():
        torch.onnx.export(model,collate(rows[-3:])[0],str(out/'model.onnx'),
                          input_names=INPUT_NAMES,output_names=['logits'],dynamic_axes=dynamic,
                          opset_version=17,dynamo=False)
    onnx.checker.check_model(str(out/'model.onnx'))
    cpu=CpuExtractor(out)
    parity=[]
    for selected_rows in [rows[:1],[rows[-1],rows[0],rows[7],rows[-20],rows[40],rows[-5],rows[100]],rows[-32:]]:
        with torch.no_grad():ref=model(*collate(selected_rows)[0]).numpy()
        feed=numpy_batch(selected_rows)
        actual=cpu.session.run(None,{k:v for k,v in feed.items() if k in cpu.inputs})[0]
        same=all({key(x['atom']) for x in left}=={key(x['atom']) for x in right}
                 for left,right in zip(decode(selected_rows,ref,meta['pairs']),decode(selected_rows,actual,meta['pairs'])))
        parity.append(dict(batch=len(selected_rows),decoded_parity=same,max_abs_logit_error=float(abs(ref-actual).max())))
        if not same:
            raise AssertionError(parity[-1])
    reference={r['id']:{key(x['atom']) for x in r['prediction']} for r in read_rows(selection_path.parent/(selected['selected']['name']+'.jsonl'))}
    offsets=np.cumsum([0]+[len(r['candidates']) for r in rows])
    probabilities=np.zeros((int(offsets[-1]),len(meta['pairs'])+1),np.float32)
    started=time.monotonic()
    for i in range(0,len(rows),48):
        batch=rows[i:i+48];feed=numpy_batch(batch)
        logits=cpu.session.run(None,{k:v for k,v in feed.items() if k in cpu.inputs})[0]
        prob=np.exp(logits-logits.max(-1,keepdims=True));prob/=prob.sum(-1,keepdims=True)
        predictions=decode(batch,logits,meta['pairs'])
        for j,(row,prediction) in enumerate(zip(batch,predictions)):
            if {key(x['atom']) for x in prediction}!=reference[row['id']]:
                raise AssertionError('Full development parity failed: '+row['id'])
            probabilities[offsets[i+j]:offsets[i+j+1]]=prob[j,:len(row['candidates'])]
    seconds=time.monotonic()-started
    report=evaluate_probabilities(rows,offsets,probabilities,meta['pairs'],out/'cpu-dev-predictions.jsonl')
    report.update(onnx_sha256=hashlib.sha256((out/'model.onnx').read_bytes()).hexdigest(),
                  model_bytes=(out/'model.onnx').stat().st_size,parameters=sum(p.numel() for p in model.parameters()),
                  cpu_threads=2,cpu_seconds=seconds,parity=parity,full_decoded_parity_rows=len(rows),
                  note='Development comparison only; fresh final evaluation remains reserved.')
    (out/'export-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    main()
