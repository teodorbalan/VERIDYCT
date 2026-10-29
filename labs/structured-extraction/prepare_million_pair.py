"""Conservative, paired atom-extraction augmentation; never executes archive code.

This does not turn recursive note logic into flat truth assertions. Only recorded
leaves under conjunction are eligible, and every literal must own exactly one
existing query candidate in BOTH versions. Rejected rows are not repaired.
"""
import argparse
import collections
import csv
import gzip
import hashlib
import heapq
import io
import itertools
import json
import pathlib
import re
import shutil
import time
import zipfile
import numpy as np
from grammar import Grammar, canonical
from prepare import tokens
from runtime import encode_input


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def source_ids(value):
    """Include metadata, query, context, bindings and nested target references."""
    if isinstance(value, str):
        return set(re.findall(r'(?<![A-Za-z0-9])p-\d+(?!\d)', value))
    if isinstance(value, dict):
        return set().union(*(source_ids(x) for x in value.values())) if value else set()
    if isinstance(value, list):
        return set().union(*(source_ids(x) for x in value)) if value else set()
    return set()


def recorded_leaves(ast):
    if ast.get('type') == 'recorded':
        return [ast]
    if ast.get('type') == 'all' and ast.get('children'):
        groups = [recorded_leaves(x) for x in ast['children']]
        if all(g is not None for g in groups):
            return sum(groups, [])
    return None


def admission(row, grammar, meta):
    if row['target'].get('parse_status') != 'resolved':
        return 'unresolved_parse', None
    leaves = recorded_leaves(row['target']['structure'])
    if leaves is None:
        return 'unsupported_ast', None
    text = row['input']['text']
    previous = '\n'.join(c['text'] for c in row['input'].get('context', []))
    # The frozen runtime keeps only the final 96 context tokens. Do not silently
    # lose required notes/bindings in the new augmentation experiment.
    if len(tokens(previous)) > 96:
        return 'context_over_96', None
    if len(tokens(text)) + len(tokens(previous)) + 2 > meta['max_tokens']:
        return 'total_over_max_tokens', None
    candidates = grammar.candidates(text)
    used = set()
    aligned = []
    slots = {tuple(p) for p in meta['pairs']}
    for leaf in leaves:
        if (leaf['subject'], leaf['attribute']) not in slots:
            return 'unknown_slot', None
        matches = [i for i,c in enumerate(candidates) if canonical(c['value']) == canonical(leaf['value'])]
        if not matches:
            return 'missing_literal_candidate', None
        if len(matches) != 1:
            return 'ambiguous_literal_candidates', None
        i = matches[0]
        if i in used:
            return 'candidate_reused', None
        used.add(i)
        aligned.append(dict(index=i, atom={k:leaf[k] for k in ('subject','attribute','value')},
                            span=[candidates[i]['start'], candidates[i]['end']]))
    return 'admitted', dict(id=row['id'], text=text, previous_text=previous, alignment=aligned)


def read_pool(archive):
    with zipfile.ZipFile(archive) as z:
        with z.open('dataset/pool.jsonl.gz') as raw:
            with gzip.GzipFile(fileobj=raw) as compressed:
                for line in compressed:
                    yield json.loads(line)


def keep_priority(heap, rank, row_id, cap):
    item = (-rank, row_id)
    if len(heap) < cap:
        heapq.heappush(heap, item)
    elif item > heap[0]:
        heapq.heapreplace(heap, item)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--v1', required=True); p.add_argument('--v2', required=True)
    p.add_argument('--base', required=True); p.add_argument('--out', required=True)
    p.add_argument('--glove', required=True)
    p.add_argument('--train-cap', type=int, default=50000)
    p.add_argument('--dev-cap', type=int, default=10000)
    a = p.parse_args(); start = time.monotonic()
    out = pathlib.Path(a.out)
    if out.exists(): raise ValueError('Use a fresh immutable output directory')
    out.mkdir(parents=True)
    base = pathlib.Path(a.base)
    meta = json.loads((base/'meta.json').read_text())
    lex = json.loads((base/'lexicon.json').read_text())
    grammar = Grammar(lex, meta['extra_names'])
    protected = {r['id'] for r in map(json.loads,(base/'dev.jsonl').read_text().splitlines()) if r.get('domain') == 'official'}
    if len(protected) != 390: raise ValueError('Expected exactly 390 official development rows')
    # Reproduce only the documented grouping convention, not packaged Python.
    # These contiguous date blocks are generator provenance, not official page IDs.
    with zipfile.ZipFile(a.v2) as z:
        practice = list(csv.DictReader(io.StringIO(z.read('data/practice.csv').decode())))
    documents = {}; previous = None; block = -1
    for row in practice:
        if row['date'] != previous: block += 1; previous = row['date']
        documents[row['id']] = f'practice-document-{block:03d}'
    protected_docs = {documents[s] for s in protected}
    counts = collections.Counter(); individual = [collections.Counter(),collections.Counter()]
    heaps = {'train':[], 'dev':[]}; case_groups = {}; train_groups=set(); dev_groups=set()
    spool = out/'eligible-pairs.jsonl'
    with spool.open('w') as f:
        for old,new in itertools.zip_longest(read_pool(a.v1), read_pool(a.v2)):
            if old is None or new is None or old['id'] != new['id']:
                raise ValueError('Archives must have identical complete row order/IDs')
            counts['pairs_seen'] += 1
            if counts['pairs_seen']%100000==0: print(json.dumps(dict(counts)),flush=True)
            if old['target']['label'] != new['target']['label']:
                raise ValueError('Paired truth label changed')
            all_sources = source_ids(old) | source_ids(new)
            if not all_sources <= documents.keys(): raise ValueError('Unknown provenance source')
            if all_sources & protected:
                counts['protected_source_id'] += 1; continue
            if {documents[s] for s in all_sources} & protected_docs:
                counts['protected_document_block'] += 1; continue
            checks=[admission(r,grammar,meta) for r in (old,new)]
            for counter,(reason,_) in zip(individual,checks):counter[reason]+=1
            if any(reason != 'admitted' for reason,_ in checks):
                counts['alignment_or_schema_rejected'] += 1; continue
            m1,m2=old['metadata'],new['metadata']
            if m1['case_key'] != m2['case_key'] or set(m1['source_ids']) != set(m2['source_ids']):
                raise ValueError('Paired provenance changed')
            # All variants sharing a source combination go to the same fold,
            # including distinct case keys. Validate each case stays in one group.
            group=digest(json.dumps(sorted(m2['source_ids']),separators=(',',':')))
            case=m2['case_key']
            if case in case_groups and case_groups[case] != group:
                raise ValueError('Case crosses evidence groups; union-find split required')
            case_groups[case]=group
            fold='dev' if int(digest('million-paired-fold-v1:'+group)[:16],16)%10==0 else 'train'
            (train_groups if fold=='train' else dev_groups).add(group)
            counts['eligible_'+fold] += 1
            if old['target']['structure'] != new['target']['structure']:counts['eligible_changed_ast'] += 1
            entry=dict(id=new['id'],fold=fold,group=group,case_key=case,source_ids=sorted(all_sources),
                       v1=checks[0][1],v2=checks[1][1])
            f.write(json.dumps(entry)+'\n')
            keep_priority(heaps[fold],int(digest('million-paired-select-v1:'+new['id']),16),new['id'],a.train_cap if fold=='train' else a.dev_cap)
    if counts['pairs_seen'] != 1000000:raise ValueError('Expected one million paired rows')
    if train_groups & dev_groups:raise AssertionError('Evidence groups overlap')
    selected={fold:{i for _,i in heap} for fold,heap in heaps.items()}
    (out/'admission-counts.json').write_text(json.dumps(dict(counts=dict(counts),v1=dict(individual[0]),v2=dict(individual[1]),selected={k:len(v) for k,v in selected.items()}),indent=2))
    if not selected['train'] or not selected['dev']:
        raise ValueError('No usable matched train/dev; retain receipt/spool and do not train')
    selected_ids=selected['train']|selected['dev']
    selected_rows=[]
    with spool.open() as f:
        for line in f:
            row=json.loads(line)
            if row['id'] in selected_ids:selected_rows.append(row)
    selected_rows.sort(key=lambda r:r['id'])
    # Both views use one vocabulary built only from their admitted TRAIN inputs.
    new_words=set();new_chars=set()
    for row in selected_rows:
        if row['fold']!='train':continue
        for view in ('v1','v2'):
            for word,_,_ in tokens(row[view]['text'])+tokens(row[view]['previous_text']):
                new_words.add(word);new_chars.update(word[:24])
    for word in sorted(new_words):
        if word not in meta['vocab']:meta['vocab'][word]=len(meta['vocab'])
    for char in sorted(new_chars):
        if char not in meta['chars']:meta['chars'][char]=len(meta['chars'])
    base_vectors=np.load(base/'vectors.npy');rng=np.random.default_rng(271828)
    vectors=rng.normal(0,.05,(len(meta['vocab']),base_vectors.shape[1])).astype(np.float32)
    vectors[:len(base_vectors)]=base_vectors
    missing={w for w,i in meta['vocab'].items() if i>=len(base_vectors)};found=set()
    with zipfile.ZipFile(a.glove) as z:
        with z.open('glove.6B.100d.txt') as f:
            for line in f:
                parts=line.decode().rstrip().split(' ');word=parts[0]
                if word in missing:
                    vectors[meta['vocab'][word]]=np.asarray(parts[1:],dtype=np.float32);found.add(word)
    meta['million_pair_protocol']='conjunction-only uniquely aligned; protected official IDs/date blocks; evidence-combination hashed90/10; internal case holdout only'
    pairs={tuple(v):i+1 for i,v in enumerate(meta['pairs'])}
    manifests=[]
    for view in ('v1','v2'):
        dest=out/view;dest.mkdir()
        (dest/'meta.json').write_text(json.dumps(meta,ensure_ascii=False))
        shutil.copyfile(base/'lexicon.json',dest/'lexicon.json');np.save(dest/'vectors.npy',vectors)
        shutil.copyfile(base/'dev.jsonl',dest/'dev.jsonl')
        shutil.copyfile(base/'train.jsonl',dest/'train.jsonl')
        with (dest/'train.jsonl').open('a') as train,(dest/'paired-dev.jsonl').open('w') as dev:
            for row in selected_rows:
                item=row[view]
                encoded=encode_input(item['text'],item['previous_text'],meta,grammar,item['id'])
                for candidate in encoded['candidates']:candidate['label']=0
                for alignment in item['alignment']:
                    c=encoded['candidates'][alignment['index']];atom=alignment['atom']
                    if [c['start'],c['end']]!=alignment['span'] or canonical(c['value'])!=canonical(atom['value']):raise AssertionError('Candidate alignment changed')
                    c['label']=pairs[(atom['subject'],atom['attribute'])]
                encoded.update(form=[x['atom'] for x in item['alignment']],domain='million_case',group_id=row['group'])
                (train if row['fold']=='train' else dev).write(json.dumps(encoded,ensure_ascii=False)+'\n')
        manifests.append(dict(view=view,files={name:hashlib.sha256((dest/name).read_bytes()).hexdigest() for name in ('meta.json','vectors.npy','train.jsonl','dev.jsonl','paired-dev.jsonl')}))
    receipt=dict(arguments=vars(a),counts=dict(counts),v1_rejections=dict(individual[0]),v2_rejections=dict(individual[1]),
                 selected={k:len(v) for k,v in selected.items()},protected_ids=sorted(protected),protected_document_blocks=sorted(protected_docs),
                 selected_groups={fold:len({r['group'] for r in selected_rows if r['fold']==fold}) for fold in selected},
                 vocab=len(meta['vocab']),chars=len(meta['chars']),new_glove_found=len(found),new_random_oov=len(missing-found),
                 data_manifests=manifests,source_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
                 archive_sha256={v:hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest() for v,path in [('v1',a.v1),('v2',a.v2)]},
                 seconds=time.monotonic()-start,epoch_selection='unchanged original official/synthetic dev; paired-dev evaluated separately',
                 limitation='Case-heldout rows still share original practice source facts with base training; not independent external validation.')
    (out/'selected-pairs.jsonl').write_text(''.join(json.dumps({k:r[k] for k in ('id','fold','group','case_key','source_ids')})+'\n' for r in selected_rows))
    (out/'preparation.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2),flush=True)


if __name__=='__main__':main()
