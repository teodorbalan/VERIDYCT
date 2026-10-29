"""Stream an ID-paired V1/V2 audit; preserve matched samples for CPU diagnostics."""
import argparse
import collections
import gzip
import hashlib
import itertools
import json
import pathlib
import re
import time
import zipfile


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()


def fold(key):
    n=int(hashlib.sha256(key.encode()).hexdigest()[:8],16)%10
    return 'test' if n==0 else 'dev' if n==1 else 'train'


def leaves(node):
    if isinstance(node,list):
        for value in node:yield from leaves(value)
    elif isinstance(node,dict):
        if node.get('type')=='recorded':
            yield {k:node[k] for k in ('subject','attribute','value')}
        elif node.get('type')=='assertions':
            yield from node['assertions']
        else:
            for value in node.values():
                if isinstance(value,(list,dict)):yield from leaves(value)


def node_types(node):
    if isinstance(node,list):
        for item in node:yield from node_types(item)
    elif isinstance(node,dict):
        if 'type' in node:yield node['type']
        for value in node.values():
            if isinstance(value,(list,dict)):yield from node_types(value)


def source_references(row):
    result=set(row['metadata']['source_ids'])
    for context in row['input'].get('context',[]):
        if re.fullmatch(r'p-\d+', context.get('id','')):result.add(context['id'])
    def visit(node):
        if isinstance(node,dict):
            if isinstance(node.get('source_id'),str):result.add(node['source_id'])
            for value in node.values():
                if isinstance(value,(dict,list)):visit(value)
        elif isinstance(node,list):
            for value in node:visit(value)
    visit(row['target'])
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--v1',required=True);p.add_argument('--v2',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=True)
    if (out/'comparison.json').exists():raise ValueError('Use a fresh output directory')
    started=time.monotonic();counts=collections.Counter();stats=[collections.Counter(),collections.Counter()]
    categorical=[collections.defaultdict(collections.Counter),collections.defaultdict(collections.Counter)]
    profile_labels=[collections.defaultdict(collections.Counter),collections.defaultdict(collections.Counter)]
    ids=set();cases=collections.Counter();groups=collections.Counter();source_exposure=collections.Counter()
    split_sources=collections.defaultdict(set);strict_split=collections.Counter();examples=[]
    samples=[(out/('sample-v'+str(i+1)+'.jsonl')).open('w',encoding='utf-8') for i in range(2)]
    with zipfile.ZipFile(a.v1) as z1,zipfile.ZipFile(a.v2) as z2:
        reports=[json.loads(z.read('dataset/report.json')) for z in (z1,z2)]
        with gzip.GzipFile(fileobj=z1.open('dataset/pool.jsonl.gz')) as f1,gzip.GzipFile(fileobj=z2.open('dataset/pool.jsonl.gz')) as f2:
            for line1,line2 in itertools.zip_longest(f1,f2):
                if line1 is None or line2 is None:raise ValueError('Archive row counts differ')
                rows=[json.loads(line1),json.loads(line2)];old,new=rows
                if old['id']!=new['id']:raise ValueError('ID order differs; refuse an unpaired comparison')
                row_id=old['id'];counts['rows']+=1;counts['duplicate_ids']+=row_id in ids;ids.add(row_id)
                for key in ('input','target'):
                    counts[key+'_changed']+=old[key]!=new[key]
                for key in ('label','parse_status','structure','bindings','reference_links'):
                    counts[key+'_changed']+=old['target'].get(key)!=new['target'].get(key)
                for key in ('case_key','evidence_group_key','source_ids','source_documents'):
                    counts[key+'_changed']+=old['metadata'].get(key)!=new['metadata'].get(key)
                meta=old['metadata'];cases[meta['case_key']]+=1;groups[meta['evidence_group_key']]+=1
                sources=source_references(old)|source_references(new);source_exposure.update(sources)
                counts['metadata_source_set_changed']+=set(old['metadata']['source_ids'])!=set(new['metadata']['source_ids'])
                counts['complete_source_set_changed']+=source_references(old)!=source_references(new)
                counts['source_references_beyond_metadata']+=bool(sources-set(old['metadata']['source_ids'])-set(new['metadata']['source_ids']))
                assigned=fold(meta['evidence_group_key']);split_sources[assigned].update(sources)
                source_folds={fold(s) for s in sources}
                strict_split[next(iter(source_folds)) if len(source_folds)==1 else 'mixed_sources']+=1
                sampled=int(hashlib.sha256(('paired-million-v1-v2:'+row_id).encode()).hexdigest()[:8],16)%100==0
                for i,row in enumerate(rows):
                    inputs,target,meta=row['input'],row['target'],row['metadata']
                    words=len(inputs['text'].split());context=inputs.get('context',[])
                    stats[i].update(rows=1,claim_words=words,context_turns=len(context),context_words=sum(len(x['text'].split()) for x in context),
                                    context_chars=sum(len(x['text']) for x in context),claim_chars=len(inputs['text']))
                    for key,value in [('schema',meta['task_schema']),('label',str(target['label'])),('parse_status',target['parse_status']),('family',meta.get('family','profile-'+str(meta.get('profile_id'))))]:categorical[i][key][value]+=1
                    categorical[i]['node_types'].update(node_types(target.get('structure',{})))
                    profile=meta.get('family','profile-'+str(meta.get('profile_id')))
                    profile_labels[i][profile][str(target['label'])]+=1
                    if sampled:
                        projected=list(leaves(target.get('structure',{})))
                        samples[i].write(json.dumps(dict(id=row_id,input=inputs,form=projected,target=target,metadata=meta,diagnostic_only=True),ensure_ascii=False)+'\n')
                        stats[i]['sample_rows']+=1
                if old['target'].get('structure')!=new['target'].get('structure') and len(examples)<8:
                    examples.append(dict(id=row_id,before_text=old['input']['text'],after_text=new['input']['text'],label=new['target']['label'],before_ast=old['target'].get('structure'),after_ast=new['target'].get('structure')))
                if counts['rows']%100000==0:print(json.dumps(dict(rows=counts['rows'],seconds=time.monotonic()-started)),flush=True)
    for stream in samples:stream.close()
    summary=[]
    for i in range(2):
        n=stats[i]['rows'];s=dict(stats[i]);s['mean_claim_words']=s['claim_words']/n;s['mean_context_turns']=s['context_turns']/n;s['mean_context_words']=s['context_words']/n
        s['distributions']=dict(categorical[i]);s['global_majority_baseline']=max(categorical[i]['label'].values())/n
        s['family_profile_oracle_majority_baseline']=sum(max(c.values()) for c in profile_labels[i].values())/n
        s['family_profile_labels']=dict(profile_labels[i]);summary.append(s)
    overlap={a+'__'+b:len(split_sources[a]&split_sources[b]) for a,b in [('train','dev'),('train','test'),('dev','test')]}
    checks=dict(label_changes_match_declared=counts['label_changed']==reports[1]['counts']['label_changed'],
                input_changes_match_declared=counts['input_changed']==reports[1]['counts']['input_changed'],
                target_changes_match_declared=counts['target_changed']==reports[1]['counts']['target_changed'],
                ast_changes_match_declared=counts['structure_changed']==reports[1]['counts']['ast_changed'])
    result=dict(counts=dict(counts),v1=summary[0],v2=summary[1],checks=checks,
                archive_sha256=dict(v1=digest(pathlib.Path(a.v1)),v2=digest(pathlib.Path(a.v2))),
                grouping=dict(cases=len(cases),max_case_rows=max(cases.values()),evidence_groups=len(groups),max_group_rows=max(groups.values()),
                              distinct_sources=len(source_exposure),max_source_exposure=max(source_exposure.values()),
                              evidence_group_split_source_overlap=overlap,all_sources_same_fold_counts=dict(strict_split)),
                sample_protocol='SHA256(paired-million-v1-v2:ID) first32bits mod100==0, identical IDs across versions; diagnostic development sample, not an independent test.',
                limitations=['Source IDs and source facts recur across groups.','All rows are declared train-eligible synthetic material; no pre-existing independent test.',
                             'Projected recorded/assertion atoms omit logical scope, dates, source bindings and comparisons; they are only an extractor diagnostic.',
                             'Profile-conditioned majority uses metadata and observed labels and is a shortcut warning, never an allowed model feature.'],seconds=time.monotonic()-started)
    (out/'comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    (out/'changed-examples.json').write_text(json.dumps(examples,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(dict(counts=result['counts'],checks=checks,grouping=result['grouping'],seconds=result['seconds'])),flush=True)


if __name__=='__main__':main()
