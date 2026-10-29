"""Audit prepared expanded data without changing its fixed training protocol."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import pathlib
import zipfile


def norm(text):
    return ' '.join(text.casefold().split())


def rows(path):
    return [json.loads(x) for x in path.open()]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', required=True)
    a = p.parse_args()
    root = pathlib.Path(a.root)
    exp = root / 'v3-audit/expanded'
    base = rows(root / 'data-v3/train.jsonl')
    common_dev = rows(root / 'data-v3/dev.jsonl')
    dev_texts = {norm(x['text']) for x in common_dev}
    base_forms = defaultdict(set)
    base_parents = set()
    for x in base:
        base_forms[norm(x['text'])].add(json.dumps(x['form'], sort_keys=True))
        base_parents.add(x['parent'].split(':')[0])
    original = {}
    with zipfile.ZipFile(root / 'veridyct-evaluation-data-v3.zip') as z:
        for source in ['evaluation-data/realistic-synthetic-20000', 'evaluation-data/realistic-v1/diagnostic-6000']:
            for line in z.read(source + '/gold/rows.jsonl').splitlines():
                x = json.loads(line)
                original[x['id']] = {k: x[k] for k in ['id', 'text', 'form', 'parent_scenario', 'template_family']}
    counts, conflicts = Counter(), []
    for x in original.values():
        text = norm(x['text'])
        if text in dev_texts:
            continue
        if text in base_forms and json.dumps(x['form'], sort_keys=True) not in base_forms[text]:
            counts['same_text_different_forms'] += 1
            conflicts.append(dict(x, existing_forms=[json.loads(s) for s in sorted(base_forms[text])]))
        if x['id'] not in base_parents and text in base_forms:
            counts['new_source_id_text_duplicate'] += 1
    protocol = json.loads((exp / 'data-v1/protocol.json').read_text())
    blocked_scenarios = {x['parent_scenario'] for x in original.values() if x['template_family'] in protocol['heldout_families']}
    blocked_ids = {x['id'] for x in original.values() if x['parent_scenario'] in blocked_scenarios}
    checks = {}
    for mode in ['expanded', 'family_control']:
        data = exp / 'data-v1' / mode
        train, dev = rows(data / 'train.jsonl'), rows(data / 'dev.jsonl')
        stable = lambda x: (x['id'], x['text'], x['previous_text'], json.dumps(x['form'], sort_keys=True), x['parent'], x['domain'])
        assert list(map(stable, dev)) == list(map(stable, common_dev))
        overlap = {norm(x['text']) for x in train} & dev_texts
        assert not overlap
        blocked = [x['id'] for x in train if x['parent'].split(':')[0] in blocked_ids]
        if mode == 'family_control':
            assert not blocked
        checks[mode] = dict(rows=len(train), dev_unchanged=True, normalized_dev_text_overlap=len(overlap),
                            blocked_parent_rows=len(blocked), train_sha256=hashlib.sha256((data / 'train.jsonl').read_bytes()).hexdigest())
    result = dict(counts=counts, dedup_form_conflicts=conflicts, checks=checks,
                  note='Post-preparation audit only; one context-sensitive repeated text was excluded by the predeclared text dedup rule. No dataset or running job was changed.')
    (exp / 'lineage-audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
