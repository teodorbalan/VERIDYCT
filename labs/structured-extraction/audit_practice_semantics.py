"""Forensic, leave-row-out audit of public organizer practice; never infer truth labels.

All candidate explanations are observations, not a reconstruction of hidden facts.
The latest-observation rule is intentionally measured as a heuristic, not assumed.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import pathlib
import re


def canonical(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def comparable(a, b):
    if a.get('op', 'eq') != 'eq' or b.get('op', 'eq') != 'eq':
        return None
    if any(a.get(k) != b.get(k) for k in ['kind', 'unit', 'currency', 'per']):
        return None
    return a['value'] == b['value']


def status(atom, observations):
    values = {canonical(o['value']) for o in observations}
    comparisons = {comparable(atom['value'], o['value']) for o in observations}
    if len(values) != 1:
        return 'conflicting_observations' if len(values) > 1 else 'no_observation'
    if True in comparisons and False not in comparisons:
        return 'supported'
    if False in comparisons and True not in comparisons:
        return 'different_value'
    return 'incomparable'


def row_decision(states):
    if 'different_value' in states:
        return 'false'
    if states and all(s == 'supported' for s in states):
        return 'true'
    return 'unresolved'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--practice', required=True)
    p.add_argument('--lexicon', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    practice, lexicon, out = pathlib.Path(a.practice), pathlib.Path(a.lexicon), pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    lex = json.loads(lexicon.read_text(encoding='utf-8-sig'))
    with practice.open(encoding='utf-8-sig', newline='') as f:
        rows = [dict(r, form=json.loads(r['form'])) for r in csv.DictReader(f)]
    pairs = {(s['name'], attr) for s in lex['subjects'] for attr in s['attributes']}
    aliases = defaultdict(set)
    for s in lex['subjects']:
        for name in [s['name'], *s['aliases']]:
            aliases[name.casefold()].add(s['name'])
    true_by_pair = defaultdict(list)
    observed_pairs = defaultdict(list)
    atoms = []
    for r in rows:
        for i, atom in enumerate(r['form']):
            item = dict(atom, id=r['id'], date=r['date'], label=r['label'], text=r['text'], atom_index=i)
            atoms.append(item)
            observed_pairs[(atom['subject'], atom['attribute'])].append(item)
            if r['label'] == 'true':
                true_by_pair[(atom['subject'], atom['attribute'])].append(item)
    metrics = {name: defaultdict(Counter) for name in ['same_day', 'latest_on_or_before', 'any_true_match']}
    atom_states = defaultdict(Counter)
    details = []
    for r in rows:
        same_states, latest_states, exact_any, exact_prior = [], [], [], []
        audit_atoms = []
        for atom in r['form']:
            others = [x for x in true_by_pair[(atom['subject'], atom['attribute'])] if x['id'] != r['id']]
            today = [x for x in others if x['date'] == r['date']]
            before = [x for x in others if x['date'] <= r['date']]
            latest_date = max((x['date'] for x in before), default=None)
            latest = [x for x in before if x['date'] == latest_date]
            same_states.append(status(atom, today)); latest_states.append(status(atom, latest))
            exact_any.append(any(canonical(atom['value']) == canonical(x['value']) for x in others))
            exact_prior.append(any(canonical(atom['value']) == canonical(x['value']) for x in before))
            atom_states[r['label']].update([same_states[-1]])
            audit_atoms.append(dict(atom=atom, same_day_status=same_states[-1], latest_status=latest_states[-1],
                                    same_day_true_ids=sorted({x['id'] for x in today}),
                                    latest_true_ids=sorted({x['id'] for x in latest}), latest_date=latest_date,
                                    exact_true_any_date=exact_any[-1], exact_true_on_or_before=exact_prior[-1]))
        same, latest = row_decision(same_states), row_decision(latest_states)
        metrics['same_day'][r['label']][same] += 1
        metrics['latest_on_or_before'][r['label']][latest] += 1
        metrics['any_true_match'][r['label']].update(rows=1, all_atoms_exact_any_date=all(exact_any),
                                                  all_atoms_exact_on_or_before=all(exact_prior))
        details.append(dict(id=r['id'], date=r['date'], label=r['label'], text=r['text'],
                            same_day_decision=same, latest_decision=latest, atoms=audit_atoms))
    conflicts = []
    for pair, observations in true_by_pair.items():
        days = defaultdict(list)
        for x in observations:
            days[x['date']].append(x)
        for day, group in days.items():
            if len({canonical(x['value']) for x in group}) > 1:
                conflicts.append(dict(subject=pair[0], attribute=pair[1], date=day, observations=group))
    names = [x for x in atoms if x['value']['kind'] == 'name']
    name_targets = defaultdict(list)
    for x in names:
        name_targets[x['value']['value']].append(x)
    multi_kind_pairs = {str(k): sorted({x['value']['kind'] for x in v}) for k, v in observed_pairs.items()
                        if len({x['value']['kind'] for x in v}) > 1}
    true_varying = [k for k, v in true_by_pair.items() if len({canonical(x['value']) for x in v}) > 1]
    missing_true = sorted(pairs - set(true_by_pair))
    kinds = defaultdict(Counter)
    for x in atoms:
        kinds[x['value']['kind']][x['label']] += 1
    form_groups = defaultdict(list)
    text_groups = defaultdict(list)
    for r in rows:
        form_groups[canonical(sorted(r['form'], key=canonical))].append(r)
        text_groups[' '.join(r['text'].casefold().split())].append(r)
    mixed_forms = [g for g in form_groups.values() if len({r['label'] for r in g}) > 1]
    mixed_texts = [g for g in text_groups.values() if len({r['label'] for r in g}) > 1]
    summary = dict(
        practice_sha256=hashlib.sha256(practice.read_bytes()).hexdigest(),
        lexicon_sha256=hashlib.sha256(lexicon.read_bytes()).hexdigest(),
        rows=len(rows), assertions=len(atoms), labels=dict(Counter(r['label'] for r in rows)),
        subjects=len(lex['subjects']), declared_pairs=len(pairs), observed_pairs=len(observed_pairs),
        distinct_attribute_names=len({attr for _, attr in pairs}),
        pairs_by_observed_kind=dict(Counter(v[0]['value']['kind'] for v in observed_pairs.values())),
        unsupported_pairs=sum((x['subject'], x['attribute']) not in pairs for x in atoms),
        lexicon_has_value_types=any('types' in s or isinstance(s['attributes'], dict) for s in lex['subjects']),
        kinds=dict(kinds), mixed_observed_kind_pairs=multi_kind_pairs,
        true_pairs=len(true_by_pair), pairs_without_true_observation=missing_true,
        true_pairs_with_multiple_observed_values=len(true_varying), same_day_true_multivalue_groups=conflicts,
        single_assertion_rows=sum(len(r['form']) == 1 for r in rows),
        multi_assertion_labels=dict(Counter(r['label'] for r in rows if len(r['form']) > 1)),
        metrics=metrics, same_day_atom_states=atom_states,
        identical_assertion_form_different_label_groups=len(mixed_forms),
        rows_in_identical_assertion_form_different_label_groups=sum(len(g) for g in mixed_forms),
        identical_normalized_text_different_label_groups=len(mixed_texts),
        identical_text_label_casebook=[[{k: r[k] for k in ['id', 'date', 'label', 'text']} for r in g] for g in mixed_texts],
        names=dict(assertions=len(names), unique_values=len(name_targets),
                   target_in_lexicon_assertions=sum(x['value']['value'].casefold() in aliases for x in names),
                   target_not_in_lexicon_assertions=sum(x['value']['value'].casefold() not in aliases for x in names),
                   unique_targets_in_lexicon=sum(v.casefold() in aliases for v in name_targets),
                   unique_targets_not_in_lexicon=sum(v.casefold() not in aliases for v in name_targets),
                   external_targets={k: len(v) for k, v in name_targets.items() if k.casefold() not in aliases}),
        semantics='Leave-row-out descriptive audit. Row true licenses all typed atoms as observations. A false compound does not identify which atom is false. Latest observations do not prove validity intervals. Different same-day values need not be logical contradictions without functional attribute and target-time assumptions.',
    )
    (out / 'summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n')
    with (out / 'rows.jsonl').open('w') as f:
        for r in details:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k not in ['same_day_true_multivalue_groups', 'names']}, indent=2))


if __name__ == '__main__':
    main()
