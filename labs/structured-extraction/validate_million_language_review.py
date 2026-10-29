"""Check the review receipt and exhibit a concrete non-equivalence witness.

This validates selection bookkeeping, not English semantics or all corpus labels.
Never reads the authored final challenge or calibration files.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--selected', required=True)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--notes', required=True)
    parser.add_argument('--comparison', required=True)
    parser.add_argument('--projection', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in Path(args.selected).read_text(encoding='utf-8').splitlines()]
    manifest = json.loads(Path(args.manifest).read_text(encoding='utf-8'))
    notes = json.loads(Path(args.notes).read_text(encoding='utf-8'))
    comparison = json.loads(Path(args.comparison).read_text(encoding='utf-8'))
    projection = json.loads(Path(args.projection).read_text(encoding='utf-8'))
    assert digest(args.selected) == manifest['selected_sha256']
    assert len(rows) == len({row['id'] for row in rows}) == 24
    assert [row['id'] for row in rows] == [row['id'] for row in manifest['row_ids']] == [row['id'] for row in notes['cases']]
    assert projection['sample_sha256'] == manifest['sample_sha256']
    strata = collections.Counter(row['ast_group'] + '/' + row['review_phenomenon'] for row in rows)
    assert len(strata) == 8 and set(strata.values()) == {3}
    for row, note in zip(rows, notes['cases']):
        same = row['v1']['target']['structure'] == row['v2']['target']['structure']
        assert same == (row['ast_group'] == 'same_ast') == (note['change_class'] == 'same_ast')
        assert row['v1']['target']['label'] == row['v2']['target']['label']

    # A witness for non-equivalence of one reviewed changed-AST pair.
    row = next(row for row in rows if row['id'] == 'million-20-029637')
    old, new = (row[version]['target']['structure'] for version in ['v1', 'v2'])
    assert old['type'] == new['type'] == 'any'
    assert old['children'][1] == new['children'][1]
    assert old['children'][0] == {'type': 'not', 'child': {'type': 'compare', 'op': 'gt', 'left': 'p-298', 'right': 'p-1706'}}
    new_negation = new['children'][0]
    assert new_negation['type'] == 'not' and new_negation['child']['type'] == 'any'
    new_literals = new_negation['child']['children']
    assert [node['source_id'] for node in new_literals] == ['p-298', 'p-1706']
    assert [node['value'] for node in new_literals] == [
        {'kind': 'quantity', 'unit': 'GB', 'value': 4},
        {'kind': 'quantity', 'unit': 'GB', 'value': 11}]
    actual = [row['practice_sources'][source]['form'][0]['value']['value'] for source in ['p-298', 'p-1706']]
    assert actual == [3, 10]
    other_branch = old['children'][1]
    assert other_branch['type'] == 'all'
    literal_matches = [node['value'] in [atom['value'] for atom in row['practice_sources'][node['source_id']]['form']
                                       if (atom['subject'], atom['attribute']) == (node['subject'], node['attribute'])]
                       for node in other_branch['children']]
    assert literal_matches == [False, False, False]

    def witness(maps, gmail):
        return {'maps_gb': maps, 'gmail_gb': gmail,
                'v1_result': not (maps > gmail),
                'v2_result': not (maps == 4 or gmail == 11),
                'unchanged_other_or_branch': False}

    original, counterfactual = witness(*actual), witness(4, 10)
    assert original['v1_result'] == original['v2_result'] is True
    assert counterfactual['v1_result'] is True and counterfactual['v2_result'] is False
    source_ids = {source for row in rows for source in row['practice_sources']}
    source_labels = {source['label'] for row in rows for source in row['practice_sources'].values()}
    receipt = {
        'status': 'PASS',
        'scope': 'Bookkeeping and a logical non-equivalence witness; qualitative assistant notes are not an automatically verified English gold set.',
        'sha256': {key: digest(getattr(args, key)) for key in ['selected', 'manifest', 'notes', 'comparison', 'projection']},
        'validator_sha256': digest(__file__),
        'selected_pairs': len(rows),
        'strata': dict(strata),
        'change_classes': dict(collections.Counter(note['change_class'] for note in notes['cases'])),
        'reviewed_labels': dict(collections.Counter(row['v2']['target']['label'] for row in rows)),
        'distinct_reviewed_source_ids': len(source_ids),
        'reviewed_source_labels': sorted(source_labels),
        'non_equivalence_witness': {'row_id': row['id'], 'original': original, 'counterfactual': counterfactual,
                                    'provenance': 'Assistant-created logical witness; not corpus modification or new factual evidence.'},
        'parent_full_comparison': {'counts': comparison['counts'], 'grouping': comparison['grouping'],
                                   'archive_sha256': comparison['archive_sha256'],
                                   'text_means': {version: {key: comparison[version][key] for key in
                                        ['mean_claim_words', 'mean_context_words', 'global_majority_baseline', 'family_profile_oracle_majority_baseline']}
                                        for version in ['v1', 'v2']}},
        'parent_flat_projection': {key: projection[key] for key in ['counts', 'v1', 'v2', 'paired', 'model_sha256', 'protocol', 'limitations']},
        'untouched': ['authored final challenge', 'calibration gold', 'model weights', 'training data'],
    }
    Path(args.out).write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({key: receipt[key] for key in ['status', 'selected_pairs', 'change_classes', 'reviewed_labels', 'distinct_reviewed_source_ids', 'reviewed_source_labels', 'non_equivalence_witness']}, indent=2))


if __name__ == '__main__':
    main()
