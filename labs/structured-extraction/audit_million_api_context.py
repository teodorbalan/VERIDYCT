"""Read-only wording/context audit of actual admitted paired million examples."""
import argparse
import collections
import csv
import gzip
import hashlib
import json
import pathlib
import re
import time


def digest(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def canon(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def leaves(node):
    if node['type'] == 'recorded':
        return [node]
    if node['type'] == 'all':
        return [leaf for child in node['children'] for leaf in leaves(child)]
    raise ValueError('Unexpected admitted target scope')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--data', required=True, type=pathlib.Path)
    p.add_argument('--pool-v2', required=True, type=pathlib.Path)
    p.add_argument('--practice', required=True, type=pathlib.Path)
    p.add_argument('--out', required=True, type=pathlib.Path)
    a = p.parse_args()
    if a.out.exists():
        raise ValueError('Use fresh audit output')
    started = time.perf_counter()
    selected = {r['id']: r for r in map(json.loads, (a.data / 'selected-pairs.jsonl').open())}
    pairs = {r['id']: r for r in map(json.loads, (a.data / 'eligible-pairs.jsonl').open())
             if r['id'] in selected}
    assert pairs.keys() == selected.keys()
    sources = {r['id']: dict(r, form=json.loads(r['form']))
               for r in csv.DictReader(a.practice.open())}
    counters = collections.defaultdict(collections.Counter)
    full_inputs = collections.defaultdict(lambda: collections.defaultdict(list))
    api_ids = set()
    marker = re.compile(r'\b(?:api|interface)\b', re.I)
    for rid, row in pairs.items():
        for view in ['v1', 'v2']:
            key = row['fold'] + '/' + view
            attrs = collections.Counter(x['atom']['attribute'] for x in row[view]['alignment'])
            counters[key]['pairs'] += 1
            counters[key]['all_aligned_atoms'] += sum(attrs.values())
            for attr in ['api_version', 'version', 'cli_version', 'stable_version', 'shipping_android']:
                if attrs[attr]:
                    counters[key][attr + '_rows'] += 1
                    counters[key][attr + '_atoms'] += attrs[attr]
            if attrs['api_version']:
                api_ids.add(rid)
                counters[key]['api_query_with_explicit_marker'] += bool(marker.search(row[view]['text']))
                counters[key]['api_context_with_explicit_marker'] += bool(marker.search(row[view]['previous_text']))
            if view == 'v2':
                inp = canon([row[view]['text'], row[view]['previous_text']])
                target = canon(sorted((x['atom'] for x in row[view]['alignment']), key=canon))
                full_inputs[inp][target].append(rid)

    # Verify the actual encoded TRAIN and paired case-dev data, not only the spool.
    prepared = {}
    for view in ['v1', 'v2']:
        seen = set()
        for name, fold in [('train.jsonl', 'train'), ('paired-dev.jsonl', 'dev')]:
            count = 0
            with (a.data / view / name).open() as f:
                for line in f:
                    row = json.loads(line)
                    if row['id'] not in pairs:
                        continue
                    rid = row['id']
                    assert rid not in seen and pairs[rid]['fold'] == fold
                    seen.add(rid)
                    expected = pairs[rid][view]
                    assert row['text'] == expected['text']
                    assert row['previous_text'] == expected['previous_text']
                    assert {canon(x) for x in row['form']} == {canon(x['atom']) for x in expected['alignment']}
                    count += 1
            prepared[view + '/' + name] = {'matched_admitted_rows': count,
                                           'sha256': digest(a.data / view / name)}
        assert seen == pairs.keys()

    # Only deserialize selected API rows from this train-eligible archive pool.
    raw_api = {}
    id_pattern = re.compile(br'^\{"id"\s*:\s*"([^"]+)"')
    with gzip.open(a.pool_v2, 'rb') as f:
        scanned = 0
        for line in f:
            scanned += 1
            m = id_pattern.match(line)
            rid = m.group(1).decode() if m else json.loads(line)['id']
            if rid in api_ids:
                assert rid not in raw_api
                raw_api[rid] = json.loads(line)
    assert raw_api.keys() == api_ids

    context_counts = collections.defaultdict(collections.Counter)
    source_counts = collections.defaultdict(collections.Counter)
    diagnostic_rows = []
    examples = {}
    for rid in sorted(api_ids):
        pair, raw = pairs[rid], raw_api[rid]
        fold = pair['fold']
        assert raw['input']['text'] == pair['v2']['text']
        assert '\n'.join(c['text'] for c in raw['input']['context']) == pair['v2']['previous_text']
        api = [leaf for leaf in leaves(raw['target']['structure']) if leaf['attribute'] == 'api_version']
        assert len(api) == 1
        leaf = api[0]
        sid, subject, date = leaf['source_id'], leaf['subject'], leaf['date']
        source_counts[fold][sid] += 1
        evidence = {c['id']: c for c in raw['input']['context'] if c['role'] == 'evidence'}
        available = {s for s in evidence if any(x['subject'] == subject and
                     x['attribute'] in ['version', 'api_version'] for x in sources[s]['form'])}
        product = {s for s in available if any(x['attribute'] == 'version' for x in sources[s]['form'])}
        same_date = {s for s in product if evidence[s]['date'] == date}
        category = ('api_note_missing' if sid not in evidence else
                    'api_and_product_same_date' if same_date else
                    'api_and_product_different_dates' if product else 'api_note_only')
        context_counts[fold][category] += 1
        context_counts[fold]['explicit_marker_in_query'] += bool(marker.search(pair['v2']['text']))
        context_counts[fold]['explicit_marker_in_context'] += bool(marker.search(pair['v2']['previous_text']))
        context_counts[fold]['same_date_product_evidence_rows'] += bool(same_date)
        context_counts[fold]['api_source_available'] += sid in evidence
        matching_dates = {s for s in available if evidence[s]['date'] == date}
        context_counts[fold]['raw_subject_date_uniquely_selects_api'] += matching_dates == {sid}
        if product:
            context_counts[fold]['any_product_note_present'] += 1
        if sid not in evidence and product:
            context_counts[fold]['missing_api_but_product_note_present'] += 1
        diagnostic = {'id': rid, 'fold': fold, 'category': category,
                      'api_source': sid, 'query_source_date': date,
                      'api_value_claimed': leaf['value'],
                      'available_product_sources': sorted(product),
                      'same_date_product_sources': sorted(same_date),
                      'available_version_note_ids': sorted(available)}
        diagnostic_rows.append(diagnostic)
        if fold == 'train' and category not in examples:
            examples[category] = dict(diagnostic, v1_text=pair['v1']['text'],
                                      v2_text=pair['v2']['text'],
                                      actual_previous_text=pair['v2']['previous_text'],
                                      raw_version_context=[evidence[s] for s in sorted(available)])

    contradictions = [groups for groups in full_inputs.values() if len(groups) > 1]
    report = {
        'scope': 'Actual selected paired TRAIN and internal case-dev only; no final challenge, no model changes',
        'data_directory': str(a.data),
        'counts': {k: dict(v) for k, v in counters.items()},
        'prepared_data_verification': prepared,
        'api_context': {k: dict(v) for k, v in context_counts.items()},
        'api_sources': {k: dict(v) for k, v in source_counts.items()},
        'api_raw_rows_verified': len(raw_api), 'pool_lines_scanned': scanned,
        'exact_v2_input_conflicting_target_groups': len(contradictions),
        'exact_v2_input_conflicting_target_rows': sum(len(ids) for g in contradictions for ids in g.values()),
        'train_examples': examples,
        'source_sha256': {'selected-pairs.jsonl': digest(a.data / 'selected-pairs.jsonl'),
                          'eligible-pairs.jsonl': digest(a.data / 'eligible-pairs.jsonl'),
                          'preparation.json': digest(a.data / 'preparation.json'),
                          'practice.csv': digest(a.practice), 'v2-pool.jsonl.gz': digest(a.pool_v2),
                          'audit_code': digest(__file__)},
        'seconds': time.perf_counter() - started,
        'interpretation': 'Omission of API does not alone prove a bad label. Raw note dates may disambiguate, but prepared previous_text retains note text only. Unique literal alignment is not a proof of unambiguous attribute semantics.',
    }
    a.out.mkdir(parents=True)
    (a.out / 'report.json').write_text(json.dumps(report, indent=2))
    with (a.out / 'api-context-cases.jsonl').open('w') as f:
        for row in diagnostic_rows:
            f.write(json.dumps(row) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'train_examples'}, indent=2))


if __name__ == '__main__':
    main()
