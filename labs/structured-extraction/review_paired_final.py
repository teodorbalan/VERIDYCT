"""Aggregate existing final predictions only after explicit selection freeze."""
import argparse
from collections import Counter, defaultdict
import json
import pathlib


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--selected', required=True)
    p.add_argument('--control', required=True)
    p.add_argument('--expected-model-sha', required=True)
    p.add_argument('--expected-fixture-sha', required=True)
    p.add_argument('--final-released', action='store_true')
    p.add_argument('--out', required=True)
    a = p.parse_args()
    if not a.final_released:
        raise ValueError('Explicit post-freeze final release is required')
    out = pathlib.Path(a.out)
    if out.exists():
        raise ValueError('Use a fresh receipt')
    data, reports = {}, {}
    paths = dict(selected=pathlib.Path(a.selected), old_control=pathlib.Path(a.control))
    for name, path in paths.items():
        reports[name] = json.loads((path / 'report.json').read_text())
        assert reports[name]['fixture_sha256'] == a.expected_fixture_sha
        data[name] = {}
        for line in (path / 'predictions.jsonl').open():
            row = json.loads(line)
            assert row['split'] == 'final' and row['id'] not in data[name]
            # Do not include final text, forms or error patterns in the review.
            data[name][row['id']] = {k: row.get(k) for k in ['exact', 'ambiguous', 'diagnostic']}
    assert reports['selected']['model_sha256'] == a.expected_model_sha
    assert set(data['selected']) == set(data['old_control'])
    paired = defaultdict(Counter)
    for row_id, row in data['selected'].items():
        old = data['old_control'][row_id]
        assert row['ambiguous'] == old['ambiguous'] and row['diagnostic'] == old['diagnostic']
        group = 'ambiguous' if row['ambiguous'] else 'type_diagnostic' if row['diagnostic'] else 'primary'
        paired[group].update(rows=1, both_correct=row['exact'] and old['exact'],
                             gained=row['exact'] and not old['exact'],
                             lost=old['exact'] and not row['exact'],
                             both_wrong=not row['exact'] and not old['exact'])
    receipt = dict(paired=paired, reports=reports, paths={k: str(v) for k, v in paths.items()},
                   purpose='Post-freeze aggregation of existing CPU final predictions; no tuning, inference or newly generated data. Final is now spent.',
                   caveat='Complete frozen pipelines compared: selected uses the robust value adapter; old control retains its original grammar.')
    out.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(paired, indent=2))


if __name__ == '__main__':
    main()
