"""Training-only shared-value coordination; disjoint phrase-family dev/final.

Values and compatible kind/unit signatures come only from the supplied TRAIN
partition. They are stated assertions, never factual labels or world evidence.
"""
import argparse
import collections
import hashlib
import json
import pathlib
import random
import shutil
import zipfile
import numpy as np
from grammar import Grammar, canonical
from prepare import tokens, norm
from runtime import encode_input
from prepare_mixed import render

# The pools are authored independently of any previously evaluated challenge.
# No family crosses train/development/final. Final is written and hashed only.
FAMILIES = {
 'train': {
  'shared': ["{a} and {b} have the same {attr}: {v}.", "The {attr} is {v} for both {a} and {b}.", "Both {a} and {b} report {v} as their {attr}.", "{a}, together with {b}, lists a {attr} of {v}.", "For each of {a} and {b}, {attr} is {v}.", "{a} and {b} each list {v} for {attr}."],
  'single': ["{a} lists {v} for {attr}. {b} is mentioned only as an unrelated subject.", "Only {a} reports a {attr} of {v}; nothing is reported here about {b}.", "The {attr} for {a} is {v}. The separate topic {b} has no measurement in this statement."],
  'irrelevant': ["I wrote the unrelated token {v} beside the names {a} and {b}.", "My personal note contains {v}; {a} and {b} are just topics for later.", "Someone mentioned {a} and {b}. My unrelated measurement was {v}."]},
 'dev': {
  'shared': ["An identical {attr} of {v} is recorded for {a} as well as {b}.", "The pair {a} and {b} shares this reported {attr}: {v}.", "{a} has the same {attr} as {b}, namely {v}.", "When listing {attr}, the report assigns {v} to {a} and to {b}."],
  'single': ["The stated {attr}, {v}, belongs to {a} alone. {b} appears in the discussion without a claim.", "Regarding {a}, its {attr} is {v}; regarding {b}, this sentence supplies no figure."],
  'irrelevant': ["{a} and {b} were mentioned, but {v} belongs to my private notes rather than either subject.", "I put {v} on a sticky note while reading about {a} and {b}; the note describes neither one."]},
 'final': {
  'shared': ["There is one common {attr} entry for {a} plus {b}: {v}.", "For {a}, as for {b}, the documented {attr} comes to {v}.", "Two names, {a} and {b}, are associated with the same recorded {attr} of {v}.", "The record gives {a} a {attr} of {v} and explicitly assigns that same value to {b}."],
  'single': ["{a}, unlike the unmeasured subject {b}, has a reported {attr} of {v}.", "No statement is being made about {b}; the {attr} claim of {v} concerns {a}."],
  'irrelevant': ["Between conversations about {a} and {b}, I jotted down my own unrelated value, {v}.", "My scratchpad says {v}. That entry is personal and makes no assertion about {a} or {b}."]},
}


def signature(value):
    return (value['kind'], value.get('unit'), value.get('currency'), value.get('per'))


def build(args):
    src = pathlib.Path(args.data); out = pathlib.Path(args.out)
    if out.exists():
        raise ValueError('Use a fresh immutable data directory')
    out.mkdir(parents=True)
    meta = json.loads((src/'meta.json').read_text())
    lex = json.loads((src/'lexicon.json').read_text())
    original = [json.loads(line) for line in (src/'train.jsonl').open()]
    dev = [json.loads(line) for line in (src/'dev.jsonl').open()]
    pair_id = {tuple(p): i+1 for i,p in enumerate(meta['pairs'])}
    observations = collections.defaultdict(lambda: collections.defaultdict(list))
    for row in original:
        for atom in row['form']:
            value = atom['value']
            if value['kind']=='boolean' or value.get('op'):
                continue
            observations[(atom['attribute'], signature(value))][atom['subject']].append(value)
    pools = [(key, subjects) for key,subjects in observations.items() if len(subjects)>=2]
    grammar = Grammar(lex,meta['extra_names'])
    occupied = {norm(r['text']) for r in original+dev}
    generated = {}; summaries = {}
    for split,total in [('train',8000),('dev',800),('final',800)]:
        rng = random.Random({'train':731,'dev':947,'final':1291}[split])
        rows = []; attempts = 0; targets = {'shared':total//2,'single':total//4,'irrelevant':total//4}
        counts = collections.Counter()
        while len(rows)<total and attempts<total*100:
            attempts += 1
            case = rng.choice([k for k in targets if counts[k]<targets[k]])
            (attr,sig),subjects = rng.choice(pools)
            a,b = rng.sample(sorted(subjects),2)
            value = dict(rng.choice(subjects[a])); surface = render(value)
            family = rng.randrange(len(FAMILIES[split][case]))
            left,right=FAMILIES[split][case][family].split('{v}',1)
            prefix=left.format(a=a,b=b,attr=attr.replace('_',' '))
            text=prefix+surface+right.format(a=a,b=b,attr=attr.replace('_',' '))
            if norm(text) in occupied:continue
            start = len(prefix); end = start+len(surface)
            matches = [c for c in grammar.candidates(text) if c['start']>=start and c['end']<=end and canonical(c['value'])==canonical(value)]
            if case!='irrelevant' and not matches:continue
            subjects_in_gold = [a,b] if case=='shared' else [a] if case=='single' else []
            form = [{'subject':s,'attribute':attr,'value':value} for s in subjects_in_gold]
            row = {'id':f'coord-{split}-{len(rows):05d}', 'text':text, 'previous_text':'', 'form':form,
                   'domain':'coordination','case':case,'family':f'{split}/{case}/{family}',
                   'value_interval':[start,end], 'provenance':'authored coordination family; compatible subjects and stated value from TRAIN only'}
            rows.append(row); counts[case]+=1; occupied.add(norm(text))
        if len(rows)!=total:raise RuntimeError((split,len(rows),attempts))
        generated[split] = rows
        summaries[split] = dict(counts,rows=len(rows),phrase_families=len({r['family'] for r in rows}))
    # Final is sealed before training. Its content never expands vocabulary.
    final = out/'reserved-final.jsonl'
    with final.open('w') as f:
        for row in generated['final']:f.write(json.dumps(row,ensure_ascii=False)+'\n')
    (out/'final-reservation.json').write_text(json.dumps({'rows':len(generated['final']), 'sha256':hashlib.sha256(final.read_bytes()).hexdigest(), 'policy':'No evaluation until phase4 model and threshold are frozen'},indent=2))
    old_vocab = dict(meta['vocab'])
    for row in generated['train']:
        for word,_,_ in tokens(row['text']):meta['vocab'].setdefault(word,len(meta['vocab']))
    for word in meta['vocab']:
        for char in word:meta['chars'].setdefault(char,len(meta['chars']))
    vectors = np.random.default_rng(29).normal(0,.15,(len(meta['vocab']),128)).astype(np.float32)
    vectors[:len(old_vocab)] = np.load(src/'vectors.npy')
    with zipfile.ZipFile(args.glove) as z:
        with z.open('glove.6B.100d.txt') as f:
            for line in f:
                word,_,tail=line.decode().partition(' ')
                if word in meta['vocab'] and word not in old_vocab:
                    vector=np.fromstring(tail,sep=' ',dtype=np.float32)
                    if len(vector)==100:vectors[meta['vocab'][word],:100]=vector
    np.save(out/'vectors.npy',vectors)
    meta.update(decoder='multilabel_sigmoid', threshold_policy='select on development only; grid .25,.35,.5,.65,.8',
                coordination_counts=summaries,source_data_meta_sha256=hashlib.sha256((src/'meta.json').read_bytes()).hexdigest())
    (out/'meta.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2));shutil.copyfile(src/'lexicon.json',out/'lexicon.json')
    for split,rows in [('train',original+generated['train']),('dev',dev+generated['dev'])]:
        with (out/(split+'.jsonl')).open('w') as f:
            for old in rows:
                fresh=encode_input(old['text'],old.get('previous_text',''),meta,grammar,old['id'])
                fresh.update(form=old['form'],domain=old.get('domain','synthetic'),case=old.get('case','ordinary'),family=old.get('family'),provenance=old.get('provenance'))
                if 'value_interval' in old:
                    lo,hi=old['value_interval']
                    for c in fresh['candidates']:
                        c['labels']=[pair_id[(a['subject'],a['attribute'])] for a in old['form'] if c['start']>=lo and c['end']<=hi and canonical(c['value'])==canonical(a['value'])]
                else:
                    if len(fresh['candidates'])!=len(old['candidates']):raise ValueError('Parser changed')
                    for c,prior in zip(fresh['candidates'],old['candidates']):
                        if (c['start'],c['end'],canonical(c['value']))!=(prior['start'],prior['end'],canonical(prior['value'])):raise ValueError('Candidate identity changed')
                        label=prior.get('label',0);c['labels']=None if label<0 else [label] if label else []
                f.write(json.dumps(fresh,ensure_ascii=False)+'\n')
    receipt={'generated':summaries,'training_rows':len(original)+8000,'development_rows':len(dev)+800,
             'compatible_attribute_signature_groups':len(pools),'final_sha256':hashlib.sha256(final.read_bytes()).hexdigest(),
             'train_dev_exact_text_overlap':len({norm(r['text']) for r in original+generated['train']} & {norm(r['text']) for r in dev+generated['dev']})}
    (out/'preparation.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--out',required=True);p.add_argument('--glove',required=True);build(p.parse_args())
