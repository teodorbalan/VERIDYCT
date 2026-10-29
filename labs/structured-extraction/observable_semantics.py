"""Development forensic baseline: explicit public intervals, never hidden truth.

The real path consumes public CSV text/date/known labels only. Gold forms are used
in separately named component diagnostics and gold labels only in scoring.
This is an archive-specific experiment, not an organizer-equivalent referee.
"""
import argparse
import collections
import csv
import datetime as dt
import hashlib
import io
import inspect
import json
import pathlib
import re
import time
import zipfile


DATE = r'(?:\d{4}-\d{2}-\d{2}|(?:the )?\d{1,2}(?:st|nd|rd|th)?(?: of)? [A-Za-z]+ \d{4}|[A-Za-z]+ \d{1,2}, \d{4})'
INTERVAL = re.compile(r'^From ('+DATE+r') through ('+DATE+r'),\s*', re.I)
ALLOWED = ('evaluation-data/realistic-v1/diagnostic-6000',
           'evaluation-data/realistic-synthetic-20000')


def day(text):
    text = re.sub(r'^(?i:the) ', '', text)
    text = re.sub(r'(?<=\d)(?:st|nd|rd|th)\b', '', text, flags=re.I).replace(' of ', ' ')
    for fmt in ('%Y-%m-%d', '%d %B %Y', '%B %d, %Y'):
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    raise ValueError('Unsupported explicit day: '+text)


def explicit_interval(text):
    match = INTERVAL.match(text)
    if not match:
        return None
    start, last = map(day, match.groups())
    if start > last:
        raise ValueError('Reversed public interval')
    return start.isoformat(), (last+dt.timedelta(days=1)).isoformat()


def name_aliases(lexicon):
    aliases = {}
    for subject in lexicon['subjects']:
        for name in [subject['name']]+subject.get('aliases', []):
            key = name.casefold().strip()
            if key in aliases and aliases[key] != subject['name']:
                aliases[key] = None
            else:
                aliases[key] = subject['name']
    return aliases


def compare(claim, observation, aliases):
    """Conservative comparison; differing date precision is unresolved.

    Unit conversion is deliberately unsupported here: mismatched units abstain.
    This avoids importing archive hidden values or unverified conversion rules.
    """
    if claim['kind'] != observation['kind'] or observation.get('op', 'eq') != 'eq':
        return None
    if any(claim.get(k) != observation.get(k) for k in ('unit', 'currency', 'per')):
        return None
    a, b = observation['value'], claim['value']
    kind, op = claim['kind'], claim.get('op', 'eq')
    if kind == 'date' and len(a) != len(b):
        return None
    if kind == 'name':
        a, b = (aliases.get(str(x).casefold(), str(x).casefold()) for x in (a,b))
        if a is None or b is None:
            return None
    if kind in ('boolean', 'name') and op != 'eq':
        return None
    if kind == 'version' and op != 'eq':
        # Numeric component order is verified on the supplied TRAIN archive.
        # Preserve length; never equate 2.3 with 2.3.0 by zero-padding.
        if not all(re.fullmatch(r'\d+(?:\.\d+)*', str(x)) for x in (a,b)):
            return None
        a,b=(tuple(map(int,x.split('.'))) for x in (a,b))
    if isinstance(a, (int,float)) and not isinstance(a, bool):
        a, b = round(a,9), round(b,9)
    return {'eq':lambda:a==b, 'gt':lambda:a>b, 'ge':lambda:a>=b,
            'lt':lambda:a<b, 'le':lambda:a<=b}[op]()


def make_index(public, forms, interval_only):
    index = collections.defaultdict(list)
    count = 0
    for row in public:
        if row['label'] != 'true':
            continue
        interval = explicit_interval(row['text'])
        if interval_only and interval is None:
            continue
        if interval is None:
            interval = row['date'], (day(row['date'])+dt.timedelta(days=1)).isoformat()
        count += 1
        for atom in forms[row['id']]:
            if atom['value'].get('op','eq') != 'eq':
                continue
            index[(atom['subject'], atom['attribute'])].append(
                dict(start=interval[0], end=interval[1], value=atom['value'], id=row['id']))
    return index, count


def judge(row, atoms, index, aliases):
    labels = []
    evidence = set()
    for atom in atoms:
        matches = []
        for item in index.get((atom['subject'], atom['attribute']), []):
            if item['id'] == row['id'] or not (item['start'] <= row['date'] < item['end']):
                continue
            result = compare(atom['value'], item['value'], aliases)
            if result is not None:
                matches.append(result)
                evidence.add(item['id'])
        # Conflicting evidence abstains; false row labels never negate every atom.
        labels.append('true' if matches and all(matches) else
                      'false' if matches and not any(matches) else 'unsure')
    label = 'false' if 'false' in labels else 'true' if labels and all(x=='true' for x in labels) else 'unsure'
    return dict(label=label, atom_labels=labels, evidence_ids=sorted(evidence))


def infer_forms(public, engine):
    from runtime import encode_input
    encoded = []
    for i, row in enumerate(public):
        previous = ' '.join(x['text'] for x in public[max(0,i-3):i])
        encoded.append(encode_input(row['text'], previous, engine.meta, engine.grammar, row['id']))
    encoded.sort(key=lambda r:(len(r['tokens']), r['id']))
    forms = {}
    for offset in range(0,len(encoded),48):
        batch = encoded[offset:offset+48]
        for row, result in zip(batch, engine.predict_encoded(batch)):
            forms[row['id']] = [item['atom'] for item in result]
    return forms


def run(public, gold, neural, aliases):
    oracle = {row_id:r['form'] for row_id,r in gold.items()}
    targets = [r for r in public if not r['label']]
    report, predictions = {}, {}
    for source_name, forms in [('oracle_forms',oracle), ('neural_forms',neural)]:
        for query_name, query_forms in [('oracle_forms',oracle), ('neural_forms',neural)]:
            for interval_only in (True,False):
                name = source_name+'__'+query_name+('__intervals' if interval_only else '__intervals_and_same_day')
                index, anchors = make_index(public,forms,interval_only)
                confusion, errors = collections.Counter(), []
                preds = {}
                for row in targets:
                    pred = judge(row,query_forms[row['id']],index,aliases)
                    expected = gold[row['id']]['label']
                    confusion[expected+'->'+pred['label']] += 1
                    preds[row['id']] = pred
                    if expected != pred['label'] and len(errors)<12:
                        errors.append(dict(id=row['id'],text=row['text'],date=row['date'],gold_label=expected,**pred))
                n=len(targets);correct=sum(confusion[x+'->'+x] for x in ('true','false','unsure'))
                per_class={x:confusion[x+'->'+x]/max(1,sum(v for k,v in confusion.items() if k.startswith(x+'->'))) for x in ('true','false','unsure')}
                report[name]=dict(rows=n,correct=correct,accuracy=correct/max(1,n),balanced_accuracy=sum(per_class.values())/3,
                                  recall=per_class,confusion=dict(confusion),known_true_rows_used=anchors,errors=errors,
                                  uses_oracle_form=source_name=='oracle_forms' or query_name=='oracle_forms')
                predictions[name]=preds
    return report, predictions


def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',required=True);p.add_argument('--bundle',required=True);p.add_argument('--out',required=True);p.add_argument('--forms-cache')
    a=p.parse_args();out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=True)
    if (out/'report.json').exists():
        raise ValueError('Reports are immutable; choose a fresh directory')
    from runtime import CpuExtractor
    engine=CpuExtractor(a.bundle);aliases=name_aliases(engine.lexicon);report={}
    inference_identity=dict(bundle={name:hashlib.sha256((pathlib.Path(a.bundle)/name).read_bytes()).hexdigest()
                                    for name in ('model.onnx','meta.json','lexicon.json')},
                            implementation={name:hashlib.sha256((pathlib.Path(__file__).parent/name).read_bytes()).hexdigest()
                                            for name in ('runtime.py','prepare.py','grammar.py','grammar_robust.py')},
                            adapter_source_sha256=hashlib.sha256(inspect.getsource(infer_forms).encode()).hexdigest(),
                            context_policy='previous3 public text; last96 tokens; batches48 sorted length,id; decode .5')
    with zipfile.ZipFile(a.archive) as archive:
        for release in ALLOWED:
            started=time.monotonic();public_bytes=archive.read(release+'/public/universe.csv')
            public=list(csv.DictReader(io.StringIO(public_bytes.decode('utf-8-sig'))))
            # Inference completes using only public fields before opening gold.
            if a.forms_cache:
                cache=pathlib.Path(a.forms_cache);receipt=json.loads((cache/'report.json').read_text())
                if receipt['protocol'].get('inference_identity')!=inference_identity:
                    raise ValueError('Cached inference implementation, metadata or context policy is absent or differs; recompute forms')
                assert receipt['protocol']['model_sha256']==hashlib.sha256((pathlib.Path(a.bundle)/'model.onnx').read_bytes()).hexdigest()
                assert receipt[release.split('/')[-1]]['public_sha256']==hashlib.sha256(public_bytes).hexdigest()
                neural=json.loads((cache/(release.split('/')[-1]+'-neural-forms.json')).read_text())
                assert set(neural)=={r['id'] for r in public}
            else:
                neural=infer_forms(public,engine)
            gold_bytes=archive.read(release+'/gold/rows.jsonl')
            gold={r['id']:r for r in map(json.loads,gold_bytes.splitlines())}
            assert all(gold[r['id']]['text']==r['text'] for r in public)
            results,predictions=run(public,gold,neural,aliases)
            key=release.split('/')[-1]
            report[key]=dict(public_sha256=hashlib.sha256(public_bytes).hexdigest(),gold_sha256=hashlib.sha256(gold_bytes).hexdigest(),
                             seconds=time.monotonic()-started,variants=results)
            (out/(key+'-predictions.json')).write_text(json.dumps(predictions),encoding='utf-8')
            (out/(key+'-neural-forms.json')).write_text(json.dumps(neural),encoding='utf-8')
            print(json.dumps({key:{k:{f:v[f] for f in ('rows','correct','accuracy','balanced_accuracy')} for k,v in results.items()}}),flush=True)
    report['protocol']=dict(scope='In-distribution TRAIN-world semantic diagnostics, NOT a held-out generalization result.',
        inference='Public text/date/known true labels, explicit text intervals, previous three public rows; no expected_value, hidden world or assertion_verdicts.',
        caveats=['Only exact full-date From/through prefixes supported.','No unit conversion or inference of persistence.',
                 'A partial extracted form may omit a false atom; extraction correctness is not guaranteed.',
                 'Gold form variants are oracle component diagnostics, never deployable accuracy.'],
        model_sha256=hashlib.sha256((pathlib.Path(a.bundle)/'model.onnx').read_bytes()).hexdigest(),inference_identity=inference_identity,fresh_final_gold_opened=False)
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


if __name__=='__main__':main()
