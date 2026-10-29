"""Read-only semantic audit of the TWO DECLARED TRAIN worlds, never holdouts.

This script reads oracle fields to audit annotation consistency. It is deliberately
separate from inference/training and must never supply model features or evidence.
"""
import argparse
import collections
import csv
import hashlib
import io
import json
import pathlib
import zipfile
from grammar import canonical

ARCHIVE_SHA='300623a5080ffb69eeb471e7069b88878f010059f73f002afee1995e00d99bc3'
ALLOWED=['evaluation-data/realistic-v1/diagnostic-6000','evaluation-data/realistic-synthetic-20000']


def combine(labels):
    if 'false' in labels:return 'false'
    if 'unsure' in labels:return 'unsure'
    return 'true'


def compare(claim,expected):
    if claim['kind']!=expected['kind']:return None
    if any(claim.get(k)!=expected.get(k) for k in ['unit','currency','per']):return None
    op=claim.get('op','eq');a=expected['value'];b=claim['value'];kind=claim['kind']
    if kind=='date' and len(a)!=len(b):return None
    if kind=='version' and op!='eq':
        try:a=tuple(int(x) for x in a.split('.'));b=tuple(int(x) for x in b.split('.'))
        except (ValueError,AttributeError):return None
    if isinstance(a,(float,int)) and not isinstance(a,bool):a=round(a,9);b=round(b,9)
    try:answer={'eq':lambda:a==b,'gt':lambda:a>b,'ge':lambda:a>=b,'lt':lambda:a<b,'le':lambda:a<=b}[op]()
    except (KeyError,TypeError):return None
    return 'true' if answer else 'false'


def oracle(atom,date,world):
    intervals=world[(atom['subject'],atom['attribute'])]['intervals']
    found=[x for x in intervals if x['start']<=date<x['end']]
    if len(found)!=1:return None,None
    interval=found[0]
    return ('unsure' if interval['state']!='known' else compare(atom['value'],interval['value'])),interval


def slim(row):
    return {k:row.get(k) for k in ['id','date','text','form','label','visible','answerability','scope','context_row_id','validity_qualifier','assertion_verdicts']}


def audit(z,prefix):
    used={}
    def read(name):
        raw=z.read(prefix+'/'+name);used[name]=hashlib.sha256(raw).hexdigest();return raw
    rows=[json.loads(x) for x in read('gold/rows.jsonl').splitlines()]
    worlds=[json.loads(x) for x in read('gold/world.jsonl').splitlines()]
    evidence=[json.loads(x) for x in read('gold/evidence.jsonl').splitlines()]
    public=list(csv.DictReader(io.StringIO(read('public/universe.csv').decode())))
    manifest=json.loads(read('manifest.json'));world={(x['subject'],x['attribute']):x for x in worlds}
    byid={r['id']:r for r in rows};pub={r['id']:r for r in public};positions={r['id']:i for i,r in enumerate(public)}
    counters=collections.defaultdict(collections.Counter);flags=collections.Counter();examples={}
    def example(name,row):
        if name not in examples:examples[name]=slim(row)
    known_intervals={(w['subject'],w['attribute'],i['start'],i['end'],canonical(i['value'])) for w in worlds for i in w['intervals'] if i['state']=='known'}
    visible_intervals=set();recomputed=0
    for w in worlds:
        for interval in w['intervals']:counters['world_interval_states'][interval['state']]+=1;counters['world_interval_provenance'][interval['provenance']]+=1
    for row in rows:
        verdicts=row['assertion_verdicts'];labels=[x['label'] for x in verdicts]
        counters['row_labels'][row['label']]+=1;counters['visible_labels'][f"{row['visible']}:{row['label']}"]+=1
        counters['answerability_label_visibility'][f"{row['answerability']}|{row['label']}|visible={row['visible']}"]+=1
        counters['scope_operator'][row['scope']['operator']]+=1;counters['assertions_per_row'][str(len(row['form']))]+=1
        counters['atom_label_set_to_row'][','.join(sorted(set(labels)))+' -> '+row['label']]+=1
        counters['genre_labels'][row['genre']+'|'+row['label']]+=1
        counters['distractor_labels'][str(bool(row['distractors']))+'|'+row['label']]+=1
        counters['review_status'][row['review_status']]+=1;counters['track'][row['track']]+=1
        if row['scope']!={'operator':'and','children':list(range(len(labels)))}:flags['nontrivial_scope']+=1;example('nontrivial_scope',row)
        if combine(labels)!=row['label']:flags['false_dominant_conjunction_mismatch']+=1;example('aggregation_mismatch',row)
        if set(labels)=={'false','unsure'} or {'false','unsure'}.issubset(labels):example('false_dominates_unsure',row)
        if 'true' in labels and 'unsure' in labels and 'false' not in labels:example('true_and_unsure',row)
        if len(row['form'])!=len(verdicts) or len(row['form'])!=len(row['assertion_spans']):flags['parallel_array_length_mismatch']+=1
        if pub[row['id']]['text']!=row['text'] or pub[row['id']]['date']!=row['date']:flags['public_text_or_date_mismatch']+=1
        public_label=pub[row['id']]['label'];counters['public_label_values'][public_label]+=1
        if bool(public_label)!=row['visible']:flags['public_visibility_mismatch']+=1
        if public_label and public_label!=row['label']:flags['public_gold_label_mismatch']+=1
        union=sorted({eid for verdict in verdicts for eid in verdict['evidence_ids']})
        if union!=sorted(row['evidence_ids']):flags['row_evidence_union_mismatch']+=1
        if row['answerability']=='oracle_only':
            counters['oracle_only_self_evidence'][str(row['id'] in row['evidence_ids'])]+=1
            if row['id'] in row['evidence_ids']:example('oracle_only_but_self_visible_evidence',row)
        context=row.get('context_row_id')
        if context:
            if context not in byid:flags['missing_context_reference']+=1
            else:
                counters['context_distance'][str(positions[row['id']]-positions[context])]+=1
                counters['context_label_pairs'][byid[context]['label']+' -> '+row['label']]+=1
                if byid[context]['date']!=row['date']:flags['context_date_differs']+=1
                if {a['subject'] for a in row['form']} & {a['subject'] for a in byid[context]['form']}==set():flags['context_no_common_subject']+=1;example('context_no_common_subject',row)
                example('cross_row_context',row)
        qual=row['validity_qualifier']
        if qual:
            counters['qualifier_visible'][str(row['visible'])]+=1
            if not qual[0]<=row['date']<qual[1]:flags['row_date_outside_qualifier']+=1
            if row['visible'] and row['label']=='true' and len(row['form'])==1:
                a=row['form'][0];visible_intervals.add((a['subject'],a['attribute'],qual[0],qual[1],canonical(a['value'])))
        expected_row=[];asof_labels=[]
        for atom,verdict,span in zip(row['form'],verdicts,row['assertion_spans']):
            counters['atom_reasons'][verdict['reason']]+=1;counters['value_kinds'][atom['value']['kind']]+=1;counters['value_ops'][atom['value'].get('op','eq')]+=1
            expected,interval=oracle(atom,row['date'],world);expected_row.append(expected)
            current,_=oracle(atom,manifest['as_of'],world);asof_labels.append(current)
            if expected is None:flags['oracle_comparison_not_implemented']+=1
            elif expected!=verdict['label']:flags['independent_atom_oracle_mismatch']+=1;example('independent_atom_oracle_mismatch',row)
            if interval:
                if verdict['interval']!=[interval['start'],interval['end']]:flags['interval_lookup_mismatch']+=1
                value=interval['value'] if interval['state']=='known' else None
                actual_value=verdict['expected_value']
                if (value is None)!=(actual_value is None) or (value is not None and canonical(value)!=canonical(actual_value)):flags['expected_value_world_mismatch']+=1
            if verdict['label']=='unsure' and verdict['evidence_ids']:flags['unsure_has_evidence_ids']+=1
            for eid in verdict['evidence_ids']:
                if eid not in byid:flags['missing_evidence_id']+=1;continue
                erow=byid[eid]
                if not erow['visible']:flags['evidence_reference_not_visible']+=1
                if erow['label']!='true':flags['evidence_reference_not_true']+=1
                if erow['date']>row['date']:flags['evidence_reference_future_dated']+=1
                evalue=verdict['expected_value']
                if not any(a['subject']==atom['subject'] and a['attribute']==atom['attribute'] and canonical(a['value'])==canonical(evalue) for a in erow['form']):flags['evidence_atom_mismatch']+=1
                if not erow['validity_qualifier'] or not erow['validity_qualifier'][0]<=row['date']<erow['validity_qualifier'][1]:flags['evidence_interval_not_covering_row_date']+=1
            raw=row['text'].encode('utf-8')[span['start']:span['end']].decode('utf-8')
            if raw!=span['text']:
                flags['assertion_span_not_exact_byte_text']+=1
                if 'span_mismatch' not in examples:examples['span_mismatch']={'id':row['id'],'start':span['start'],'end':span['end'],'recorded':span['text'],'actual_byte_slice':raw}
            for distractor in row['distractors']:
                if span['start']<distractor['end'] and span['end']>distractor['start']:flags['assertion_distractor_span_overlap']+=1;example('assertion_distractor_overlap',row)
        if all(x is not None for x in expected_row):
            recomputed+=1
            if combine(expected_row)!=row['label']:flags['independent_row_oracle_mismatch']+=1
        if all(x is not None for x in asof_labels):
            counters['row_date_vs_asof_label'][row['label']+' -> '+combine(asof_labels)]+=1
            if combine(asof_labels)!=row['label']:example('row_date_not_asof_date',row)
        if row['label']=='false' and len(row['form'])==1:example('false_stated_value_vs_expected',row)
        if row['label']=='unsure' and len(row['form'])==1:example('unknown_interval',row)
    for item in evidence:
        row=byid[item['id']]
        if item['assertions']!=row['assertion_verdicts'] or item['answerability']!=row['answerability']:flags['evidence_file_disagrees_with_rows']+=1
    return {'prefix':prefix,'rows':len(rows),'world_pairs':len(world),'known_intervals':len(known_intervals),'visible_interval_keys':len(visible_intervals),'missing_visible_known_intervals':len(known_intervals-visible_intervals),'extra_visible_interval_keys':len(visible_intervals-known_intervals),'independently_recomputed_rows':recomputed,'counters':{k:dict(v) for k,v in counters.items()},'flags':dict(flags),'examples':examples,'provenance':{k:manifest[k] for k in ['world_id','factory_version','world_policy','surface_profile','external_slot_count','review_status']},'source_sha256':used}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--archive',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    path=pathlib.Path(a.archive)
    if hashlib.sha256(path.read_bytes()).hexdigest()!=ARCHIVE_SHA:raise ValueError('Unexpected archive')
    out=pathlib.Path(a.out)
    if out.exists():raise ValueError('Use fresh report path')
    with zipfile.ZipFile(path) as z:results=[audit(z,prefix) for prefix in ALLOWED]
    report={'archive_sha256':ARCHIVE_SHA,'scope':'Only two declared training worlds; no calibration, sealed or challenge files read','worlds':results}
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2,ensure_ascii=False))
    print(json.dumps([{k:r[k] for k in ['prefix','rows','known_intervals','visible_interval_keys','missing_visible_known_intervals','independently_recomputed_rows','flags','counters']} for r in results],indent=2))
