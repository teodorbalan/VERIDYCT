"""Audit saved six-cell predictions; no model loading, inference or selection."""
import argparse
import hashlib
import json
from pathlib import Path

from grammar import canonical


def atom_set(atoms):
    return {(a['subject'], a['attribute'], canonical(a['value'])) for a in atoms}


def read_rows(path):
    with path.open(encoding='utf-8') as stream:
        rows = [json.loads(line) for line in stream]
    indexed = {r['id']: r for r in rows}
    if len(indexed) != len(rows):
        raise ValueError(f'Duplicate IDs: {path}')
    return indexed


def metrics(ids, gold, predicted):
    exact = correct = goldn = predn = 0
    for row_id in ids:
        g, p = gold[row_id], predicted[row_id]
        exact += g == p
        correct += len(g & p)
        goldn += len(g)
        predn += len(p)
    return dict(rows=len(ids), exact_rows=exact, exact=exact/max(1, len(ids)),
                gold_unique_atoms=goldn, predicted_unique_atoms=predn,
                correct_unique_atoms=correct, f1=2*correct/max(1, goldn+predn))


def changes(ids, gold, base, other):
    result = dict(both_correct=0, gain=0, loss=0, both_wrong=0)
    for row_id in ids:
        before, after = base[row_id] == gold[row_id], other[row_id] == gold[row_id]
        field = ('both_correct' if after else 'loss') if before else ('gain' if after else 'both_wrong')
        result[field] += 1
    result['net_exact_rows'] = result['gain'] - result['loss']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--evaluation', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('Use a fresh aggregation output')
    paths = {v: args.data/v/'paired-dev.jsonl' for v in ('v1', 'v2')}
    rows = {v: read_rows(path) for v, path in paths.items()}
    ids = list(rows['v1'])
    if ids != list(rows['v2']):
        raise ValueError('Paired gold IDs/order differ')
    gold = {v: {i: atom_set(row['form']) for i, row in view.items()} for v, view in rows.items()}
    groups = {'all': ids,
              'same_flat_gold': [i for i in ids if gold['v1'][i] == gold['v2'][i]],
              'changed_flat_gold': [i for i in ids if gold['v1'][i] != gold['v2'][i]]}
    predictions = {}
    for model in ('base', 'v1', 'v2'):
        for view in ('v1', 'v2'):
            path = args.evaluation/f'{model}-on-{view}.jsonl'
            paths[f'{model}-on-{view}'] = path
            saved = read_rows(path)
            if list(saved) != ids:
                raise ValueError(f'Prediction IDs/order differ: {path}')
            predictions[model, view] = {i: atom_set(p['atom'] for p in row['prediction']) for i, row in saved.items()}
    result = dict(scope='Saved flat-atom prediction aggregation only; equality is canonical flat gold sets, not AST equality.',
                  groups={k: len(v) for k, v in groups.items()}, cells=[], transitions=[])
    report_path = args.evaluation/'report.json'
    paths['original_report'] = report_path
    original = json.loads(report_path.read_text())
    original_cells = {(c['model_training_view'], c['input_view']): c['metrics'] for c in original['cells']}
    for (model, view), prediction in predictions.items():
        for group, subset in groups.items():
            scored = metrics(subset, gold[view], prediction)
            if group == 'all':
                for field in ('rows', 'exact_rows', 'gold_unique_atoms', 'predicted_unique_atoms', 'correct_unique_atoms'):
                    if scored[field] != original_cells[model, view][field]:
                        raise ValueError(f'Saved metric mismatch: {model}/{view}/{field}')
            result['cells'].append(dict(model=model, input_view=view, group=group, **scored))
    for view in ('v1', 'v2'):
        for model in ('v1', 'v2'):
            for group, subset in groups.items():
                result['transitions'].append(dict(input_view=view, comparison=f'base_to_{model}', group=group,
                    **changes(subset, gold[view], predictions['base', view], predictions[model, view])))
    result['input_sha256'] = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in paths.items()}
    result['canonicalizer_sha256'] = hashlib.sha256(Path(__file__).with_name('grammar.py').read_bytes()).hexdigest()
    result['all_original_counts_match'] = True
    args.out.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
