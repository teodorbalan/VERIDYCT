"""Freeze 24 paired language-review cases without using extractor predictions.

Twelve unchanged AST / twelve changed AST; three per four predeclared phenomena.
Selection is deterministic within the parent's ID-hashed matched sample.
"""
import argparse
import csv
import hashlib
import json
import pathlib

SALT = 'million-language-review-24-v1:'
PHENOMENA = ['negation', 'disjunction', 'source_omission', 'false_substitution']


def nodes(value):
    if isinstance(value, dict):
        if 'type' in value:
            yield value
        for child in value.values():
            if isinstance(child, (dict, list)):
                yield from nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from nodes(child)


def refs(row):
    result = set()

    def visit(value):
        if isinstance(value, dict):
            # observation_pair endpoints have source_id without their own type.
            if isinstance(value.get('source_id'), str):
                result.add(value['source_id'])
            if value.get('type') == 'compare':
                result.update(x for x in [value.get('left'), value.get('right')] if isinstance(x, str))
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(row['target'].get('structure'))
    return result


def key(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--sample-v1', required=True)
    p.add_argument('--sample-v2', required=True)
    p.add_argument('--practice', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    out = pathlib.Path(a.out)
    if out.exists():
        raise ValueError('Use a fresh review directory')
    out.mkdir(parents=True)
    paths = [pathlib.Path(a.sample_v1), pathlib.Path(a.sample_v2)]
    versions = [{x['id']: x for x in map(json.loads, path.open(encoding='utf-8'))} for path in paths]
    assert set(versions[0]) == set(versions[1])
    with pathlib.Path(a.practice).open(encoding='utf-8-sig', newline='') as f:
        practice = {r['id']: dict(r, form=json.loads(r['form'])) for r in csv.DictReader(f)}
    info = {}
    for row_id, old in versions[0].items():
        new = versions[1][row_id]
        status = 'same_ast' if old['target'].get('structure') == new['target'].get('structure') else 'changed_ast'
        kinds = {n['type'] for row in [old, new] for n in nodes(row['target'].get('structure'))}
        missing = {str(i + 1): sorted(refs(row) - {c['id'] for c in row['input'].get('context', []) if c.get('role') == 'evidence'})
                   for i, row in enumerate([old, new])}
        substitutions = []
        for version, row in enumerate([old, new], 1):
            for node in nodes(row['target'].get('structure')):
                if node.get('type') != 'recorded' or node.get('source_id') not in practice:
                    continue
                source = practice[node['source_id']]
                originals = [x['value'] for x in source['form'] if (x['subject'], x['attribute']) == (node['subject'], node['attribute'])]
                if originals and key(node['value']) not in {key(x) for x in originals}:
                    substitutions.append(dict(version=version, source_id=node['source_id'], subject=node['subject'],
                                              attribute=node['attribute'], asserted=node['value'], source_assertions=originals))
        eligible = dict(negation='not' in kinds, disjunction='any' in kinds,
                        source_omission=bool(missing['1'] or missing['2']),
                        false_substitution=bool(substitutions) and new['target']['label'] == 'false')
        info[row_id] = dict(status=status, eligible=eligible, missing=missing, substitutions=substitutions)
    selected, used, pools = [], set(), {}
    for status in ['same_ast', 'changed_ast']:
        for phenomenon in PHENOMENA:
            pool = sorted([row_id for row_id, x in info.items() if x['status'] == status and x['eligible'][phenomenon]],
                          key=lambda row_id: hashlib.sha256((SALT + status + ':' + phenomenon + ':' + row_id).encode()).hexdigest())
            pools[status + '/' + phenomenon] = len(pool)
            chosen = [row_id for row_id in pool if row_id not in used][:3]
            assert len(chosen) == 3
            for row_id in chosen:
                used.add(row_id)
                relevant = refs(versions[0][row_id]) | refs(versions[1][row_id])
                selected.append(dict(id=row_id, ast_group=status, review_phenomenon=phenomenon,
                                     selection_diagnostics=info[row_id], v1=versions[0][row_id], v2=versions[1][row_id],
                                     practice_sources={i: {k: practice[i][k] for k in ['text', 'date', 'label', 'form']} for i in sorted(relevant) if i in practice}))
    with (out / 'selected-pairs.jsonl').open('w', encoding='utf-8', newline='\n') as f:
        for row in selected:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    manifest = dict(protocol='Three stable-hash-ranked unused rows for each of same/changed AST x negation/disjunction/source omission/false substitution; fixed stratum order.',
                    salt=SALT, paired_sample_rows=len(info), selected_rows=len(selected), pools=pools,
                    sample_sha256={str(i + 1): hashlib.sha256(path.read_bytes()).hexdigest() for i, path in enumerate(paths)},
                    practice_sha256=hashlib.sha256(pathlib.Path(a.practice).read_bytes()).hexdigest(),
                    selected_sha256=hashlib.sha256((out / 'selected-pairs.jsonl').read_bytes()).hexdigest(),
                    row_ids=[dict(id=x['id'], ast_group=x['ast_group'], phenomenon=x['review_phenomenon']) for x in selected],
                    caveat='Purposive balanced qualitative audit, not prevalence estimate. Assistant review, not human adjudication. Source assertion differences are not truth corrections.')
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
