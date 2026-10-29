"""Independent paired DEV review and metadata checks; no model inference or gold archives."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import pathlib
import torch


def atom_key(atom):
    value = dict(atom['value'])
    if value.get('op') == 'eq':
        value.pop('op')
    number = value.get('value')
    if isinstance(number, (int, float)) and not isinstance(number, bool):
        number = round(number, 9)
        value['value'] = int(number) if number == int(number) else number
    return atom['subject'], atom['attribute'], json.dumps(value, sort_keys=True)


def read_predictions(path):
    result = {}
    for line in path.open():
        row = json.loads(line)
        assert row['id'] not in result
        assert row['domain'] in ['official', 'synthetic', 'challenge']
        gold = {atom_key(x) for x in row['gold']}
        prediction = {atom_key(x['atom']) for x in row['prediction']}
        assert bool(row['exact']) == (gold == prediction)
        result[row['id']] = row
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--comparison', required=True)
    p.add_argument('--model-source', required=True)
    p.add_argument('--expected-selection-sha', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    root, source, out = pathlib.Path(a.comparison), pathlib.Path(a.model_source), pathlib.Path(a.out)
    if out.exists():
        raise ValueError('Use a fresh receipt')
    selection_path = root / 'selection.json'
    digest = hashlib.sha256(selection_path.read_bytes()).hexdigest()
    assert digest == a.expected_selection_sha
    manifest = json.loads(selection_path.read_text())
    meta = json.loads((root / 'meta.json').read_text())
    selected = manifest['selected']
    best = max(manifest['options'], key=lambda x: (x['selection_score'], -x['parameters']))
    assert selected == best
    rows = {name: read_predictions(root / (name + '.jsonl'))
            for name in [selected['name'], 'previous-v2-ensemble']}
    assert set(rows[selected['name']]) == set(rows['previous-v2-ensemble'])
    paired = defaultdict(Counter)
    for row_id, row in rows[selected['name']].items():
        old = rows['previous-v2-ensemble'][row_id]
        assert all(row[k] == old[k] for k in ['gold', 'text', 'previous_text', 'domain'])
        paired[row['domain']].update(rows=1, both_correct=row['exact'] and old['exact'],
                                    gained=row['exact'] and not old['exact'],
                                    lost=old['exact'] and not row['exact'],
                                    both_wrong=not row['exact'] and not old['exact'])
    checks = []
    for name, record in manifest['models'].items():
        checkpoint = pathlib.Path(record['checkpoint'])
        assert hashlib.sha256(checkpoint.read_bytes()).hexdigest() == record['sha256']
        member = torch.load(checkpoint, weights_only=False, map_location='cpu')['meta']
        check = dict(name=name, pairs_equal=member['pairs'] == meta['pairs'],
                     max_tokens=member['max_tokens'], max_chars=member['max_chars'],
                     extra_names_not_in_master=sorted(set(member['extra_names']) - set(meta['extra_names'])))
        assert check['pairs_equal'] and check['max_tokens'] == 384 and check['max_chars'] == 24
        assert not check['extra_names_not_in_master']
        checks.append(check)
    receipt = dict(selection_sha256=digest, paired=paired, selected=selected,
                   model_count=len(manifest['models']), option_count=len(manifest['options']),
                   metadata_checks=checks, prediction_exactness_recomputed=True,
                   source_hashes={name: hashlib.sha256((source / name).read_bytes()).hexdigest()
                                  for name in ['compare_stacks.py', 'model.py', 'model_factorized.py',
                                               'model_graph.py', 'grammar.py', 'grammar_robust.py', 'runtime.py']},
                   caveat='Paired descriptive development comparison after model selection; not fresh validation or a latency measurement.')
    out.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(dict(paired=paired, model_count=len(checks), selected=selected['name']), indent=2))


if __name__ == '__main__':
    main()
