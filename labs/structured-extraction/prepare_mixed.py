"""Second experiment: official surface forms, grouped split, typed augmentation.

Only training parents are augmented. Synthetic worlds remain extraction examples,
never Hooly evidence. Original files and prior experiment artifacts are immutable.
"""
import argparse
import collections
import csv
import hashlib
import json
import pathlib
import random
import re
import zipfile
import numpy as np
from grammar import Grammar,canonical
from prepare import norm,tokens,write_json,ARCHIVE_SHA
from runtime import encode_input

def template(text,lex):
    s=norm(text)
    names=sorted({x.casefold() for a in lex['subjects'] for x in [a['name'],*a['aliases']]},key=len,reverse=True)
    for name in names:s=re.sub(r'(?<!\w)'+re.escape(name)+r'(?!\w)',' ENTITY ',s)
    s=re.sub(r'\d+(?:[.,]\d+)*',' NUMBER ',s)
    return ' '.join(s.split())

def render(value):
    k=value['kind'];v=value['value']
    if k=='money':return {'EUR':'€','USD':'$','GBP':'£'}.get(value.get('currency'),'EUR ')+str(v)+((' per '+value['per']) if value.get('per') else '')
    if k=='percent':return str(v)+'%'
    if k in ['duration','quantity']:return str(v)+' '+value['unit']
    if k=='version':return 'v'+str(v)
    return str(v)

def augment(r,grammar,rng,n):
    if len(r['form'])!=1 or r['form'][0]['value']['kind']=='boolean':return []
    atom=r['form'][0];value=atom['value'];matches=[c for c in grammar.candidates(r['text']) if canonical(c['value'])==canonical(value)]
    if len(matches)!=1:return []
    c=matches[0];out=[]
    for i in range(n):
        v=dict(value);k=v['kind'];x=v['value']
        if k in ['money','percent','duration','quantity']:
            if isinstance(x,int) or float(x).is_integer():v['value']=rng.randint(1,max(20,int(abs(x)*1.8)+1))
            else:v['value']=round(max(.01,float(x)*rng.uniform(.4,1.8)),2)
        elif k=='version':v['value']=str(rng.randint(1,25))+'.'+str(rng.randint(0,9))
        elif k=='date':v['value']=f'2026-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}'
        else:continue
        text=r['text'][:c['start']]+render(v)+r['text'][c['end']:]
        # Roundtrip independently through the runtime parser before accepting.
        if not any(canonical(q['value'])==canonical(v) for q in grammar.candidates(text)):continue
        out.append(dict(r,id=r['id']+f':aug:{i}',text=text,form=[dict(atom,value=v)],spans=None,parent=r['id'],provenance='deterministic typed-value replacement; no truth label'))
    return out

def align(row,encoded,pair_id,lexicon):
    atoms=row['form'];text=row['text'];spans=row.get('spans');covered=set()
    aliases={s['name']:[s['name'],*s['aliases']] for s in lexicon['subjects']}
    for c in encoded['candidates']:
        eligible=[]
        for j,a in enumerate(atoms):
            if canonical(c['value'])!=canonical(a['value']):continue
            if spans:
                sp=spans[j];lo=len(text.encode()[:sp['start']].decode());hi=len(text.encode()[:sp['end']].decode())
                inside=c['start']>=lo and c['end']<=hi+2
                if c['value']['kind']=='boolean':inside=max(0,min(c['end'],hi)-max(c['start'],lo))>=.85*(hi-lo)
                if not inside:continue
            terms=set(a['attribute'].split('_'));surface=set(re.findall(r'\w+',text[c['start']:c['end']].casefold()))
            score=len(terms&surface)
            mentions=[m for alias in aliases[a['subject']] for m in re.finditer(r'(?<!\w)'+re.escape(alias)+r'(?!\w)',text,re.I)]
            if mentions:score+=1/(1+min(abs((m.start()+m.end())/2-(c['start']+c['end'])/2) for m in mentions))
            eligible.append((score,j))
        c['label']=0
        if len(eligible)==1 or (len(eligible)>1 and sorted(eligible,reverse=True)[0][0]>sorted(eligible,reverse=True)[1][0]):
            j=max(eligible)[1];a=atoms[j];c['label']=pair_id[(a['subject'],a['attribute'])];covered.add(j)
        elif eligible:c['label']=-100
    return covered

def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',required=True);p.add_argument('--practice',required=True);p.add_argument('--lexicon',required=True);p.add_argument('--glove',required=True);p.add_argument('--out',required=True);p.add_argument('--augment',type=int,default=12);a=p.parse_args()
    out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=True)
    if (out/'meta.json').exists():raise ValueError('Use fresh output directory')
    if hashlib.sha256(pathlib.Path(a.archive).read_bytes()).hexdigest()!=ARCHIVE_SHA:raise ValueError('Archive hash changed')
    lex=json.loads(pathlib.Path(a.lexicon).read_text());pairs=sorted((s['name'],x) for s in lex['subjects'] for x in s['attributes']);pair_id={p:i+1 for i,p in enumerate(pairs)}
    with open(a.practice,encoding='utf-8-sig',newline='') as f:official=[dict(r,form=json.loads(r['form'])) for r in csv.DictReader(f)]
    groups={r['id']:template(r['text'],lex) for r in official}
    isdev=lambda r:int(hashlib.sha256(groups[r['id']].encode()).hexdigest()[:8],16)%5==0
    train=[];dev=[]
    for i,r in enumerate(official):
        # Actual preceding text only; do not synthesize a gold antecedent for eval.
        previous=' '.join(x['text'] for x in official[max(0,i-3):i] if isdev(r) or not isdev(x))
        row=dict(r,previous_text=previous,domain='official',spans=None,parent=r['id'],provenance='organizer practice text; unlabeled preceding rows as context')
        (dev if isdev(r) else train).append(row)
    official_train=len(train);official_dev=len(dev)
    official_dev_texts={norm(r['text']) for r in dev}
    with zipfile.ZipFile(a.archive) as z:
        selected=[json.loads(x) for x in z.read('evaluation-data/realistic-training-mmr-20000/training.jsonl').splitlines()]
        synthetic_dev=[r for r in selected if r['source_release'].endswith('/development-20000')]
        dev_texts={norm(r['input']['text']) for r in synthetic_dev}|official_dev_texts
        sources=set()
        for r in selected:
            row={'id':r['id'],'text':r['input']['text'],'previous_text':(r['input'].get('previous_row') or {}).get('text',''),'form':r['target']['form'],'spans':r['target']['assertion_spans'],'domain':'synthetic','parent':r['id'],'provenance':'v3 MMR extraction; no world truths imported'}
            if r['source_release'].endswith('/development-20000'):dev.append(row)
            elif norm(row['text']) not in dev_texts:
                train.append(row);sources.add('evaluation-data/'+r['source_release'].split('evaluation-data/',1)[1])
        # Visible interval-qualified anchors from TRAIN worlds provide hard negatives
        # for dates in validity prefixes. No validation world anchors are read.
        for source in sorted(sources):
            for raw in z.read(source+'/gold/rows.jsonl').splitlines():
                r=json.loads(raw)
                if r.get('visible') and norm(r['text']) not in dev_texts:
                    train.append({'id':r['id']+':anchor','text':r['text'],'previous_text':'','form':r['form'],'spans':r['assertion_spans'],'domain':'synthetic','parent':r['id'],'provenance':'visible anchor from training world only'})
    dev_texts={norm(r['text']) for r in dev}
    train=[r for r in train if norm(r['text']) not in dev_texts]
    extras=sorted({v['value']['value'] for r in train for v in r['form'] if v['value']['kind']=='name'})
    grammar=Grammar(lex,extras);rng=random.Random(20261029)
    aug=[]
    for r in train:
        if r['domain']=='official':aug.extend(augment(r,grammar,rng,a.augment))
    train.extend(aug)
    # Repeat unchanged official originals, including Boolean and compound examples,
    # so augmentation does not make only the easy numeric task dominate.
    official_base=[r for r in train if r['domain']=='official' and ':aug:' not in r['id']]
    for repeat in range(3):train.extend(dict(r,id=r['id']+f':repeat:{repeat}') for r in official_base)
    train=[r for r in train if norm(r['text']) not in dev_texts]
    vocab={'<pad>':0,'<unk>':1,'<ctx>':2,'<current>':3}
    for r in train:
        for w,_,_ in tokens(r['text']+' '+r['previous_text']):vocab.setdefault(w,len(vocab))
    chars={'<pad>':0,'<unk>':1}
    for w in vocab:
        for c in w:chars.setdefault(c,len(chars))
    meta={'archive_sha256':ARCHIVE_SHA,'practice_sha256':hashlib.sha256(pathlib.Path(a.practice).read_bytes()).hexdigest(),'pairs':pairs,'vocab':vocab,'chars':chars,'extra_names':extras,'max_tokens':384,'max_chars':24,'split':'official templates grouped by masked entities/numbers and SHA256 modulo 5; synthetic entire development world held out','context':'actual previous up to 3 official CSV rows, with held-out rows excluded from training context; synthetic explicitly supplied previous row','official_train_parents':official_train,'official_dev_parents':official_dev,'synthetic_worlds':'two train, one dev; no calibration or sealed gold','numeric_equivalence':'nine decimal places; strict JSON equality reported separately','selection':'equal mean of official and synthetic complete-row exact rates'}
    # Static pretrained vectors only: no LM inference or factual knowledge lookup.
    vectors=np.random.default_rng(20261029).normal(0,.15,(len(vocab),128)).astype(np.float32);vectors[0]=0;hits=0
    with zipfile.ZipFile(a.glove) as z:
        with z.open('glove.6B.100d.txt') as f:
            for line in f:
                word,_,tail=line.decode().partition(' ')
                if word in vocab:
                    vector=np.fromstring(tail,sep=' ',dtype=np.float32)
                    if len(vector)==100:vectors[vocab[word],:100]=vector;hits+=1
    np.save(out/'vectors.npy',vectors);meta['vectors']={'source':'https://huggingface.co/stanfordnlp/glove','archive_sha256':hashlib.sha256(pathlib.Path(a.glove).read_bytes()).hexdigest(),'name':'glove.6B.100d','vocab_hits':hits,'vocab_total':len(vocab),'npy_sha256':hashlib.sha256((out/'vectors.npy').read_bytes()).hexdigest()}
    write_json(out/'meta.json',meta);write_json(out/'lexicon.json',lex);stats={}
    for split,rows in [('train',train),('dev',dev)]:
        counts=collections.Counter();miss=[]
        with (out/(split+'.jsonl')).open('w') as f:
            for r in rows:
                encoded=encode_input(r['text'],r['previous_text'],meta,grammar,r['id']);covered=align(r,encoded,pair_id,lex)
                encoded.update(form=r['form'],domain=r['domain'],parent=r['parent'],provenance=r['provenance'])
                counts['rows']+=1;counts[r['domain']+'_rows']+=1;counts['atoms']+=len(r['form']);counts['aligned_atoms']+=len(covered)
                if len(covered)<len(r['form']) and len(miss)<100:miss.append({'id':r['id'],'text':r['text'],'forms':r['form'],'covered':sorted(covered)})
                f.write(json.dumps(encoded,ensure_ascii=False)+'\n')
        stats[split]=dict(counts);write_json(out/(split+'-alignment-misses.json'),miss)
    write_json(out/'preparation.json',stats);write_json(out/'official-split.json',{'training_ids':[r['id'] for r in official if not isdev(r)],'development_ids':[r['id'] for r in official if isdev(r)]})
    print(json.dumps({'counts':stats,'vectors':meta['vectors']},indent=2),flush=True)

if __name__=='__main__':main()
