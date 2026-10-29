"""Read-only frozen-bundle audit on official development inputs.

Gold forms are isolated from encoder inputs and used only for aggregate scores.
This changes batch composition, not the model, parser, threshold or decoder.
"""
import argparse
import collections
import hashlib
import itertools
import json
import pathlib
import platform
import resource
import sys
import time

# Imported frozen runtime modules must not create cache files in their bundle.
sys.dont_write_bytecode = True


def digest(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bundle', required=True, type=pathlib.Path)
    parser.add_argument('--dev', required=True, type=pathlib.Path)
    parser.add_argument('--out', required=True, type=pathlib.Path)
    parser.add_argument('--threads', type=int, default=2)
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    out = args.out.resolve()
    if out == bundle or bundle in out.parents:
        raise ValueError('Audit output must be outside the frozen bundle')
    if out.exists():
        raise ValueError('Use a fresh output directory')
    source_names = ['model.onnx', 'meta.json', 'lexicon.json', 'runtime.py',
                    'prepare.py', 'grammar.py', 'grammar_robust.py']
    hashes = {name: digest(bundle / name) for name in source_names if (bundle / name).exists()}
    sys.path.insert(0, str(bundle))
    import runtime
    from grammar import canonical
    if pathlib.Path(runtime.__file__).resolve() != bundle / 'runtime.py':
        raise RuntimeError('Wrong runtime imported')

    def atom_key(atom):
        return (atom['subject'], atom['attribute'], canonical(atom['value']))

    started = time.perf_counter()
    engine = runtime.CpuExtractor(bundle, threads=args.threads)
    initialization_seconds = time.perf_counter() - started
    inputs, gold = [], {}
    with args.dev.open() as stream:
        for line in stream:
            row = json.loads(line)
            if row.get('domain') != 'official':
                continue
            if row['id'] in gold:
                raise ValueError('Duplicate official ID')
            inputs.append({'id': row['id'], 'text': row['text'],
                           'previous_text': row.get('previous_text', '')})
            gold[row['id']] = {atom_key(a) for a in row['form']}
    if len(inputs) != 390:
        raise ValueError(f'Expected exactly 390 official development rows, got {len(inputs)}')
    start = time.perf_counter()
    encoded = [runtime.encode_input(r['text'], r['previous_text'], engine.meta,
                                    engine.grammar, r['id']) for r in inputs]
    encoding_seconds = time.perf_counter() - start
    if any('form' in row or 'label' in row for row in encoded):
        raise AssertionError('Gold leaked into encoded model input')
    ordered = sorted(encoded, key=lambda row: len(row['tokens']))
    by_length = collections.defaultdict(list)
    for row in ordered:
        by_length[len(row['tokens'])].append(row)
    plans = {
        'singleton': [[row] for row in ordered],
        'sorted48_official': [ordered[i:i + 48] for i in range(0, len(ordered), 48)],
        'exact_length48': [rows[i:i + 48] for rows in by_length.values()
                           for i in range(0, len(rows), 48)],
    }
    # One shared warm-up, excluded from policy timing and evaluation output.
    engine.predict_encoded([ordered[0]])
    results, predictions, paddings = {}, {}, {}
    for policy, batches in plans.items():
        wall = time.perf_counter()
        cpu = time.process_time()
        outputs, pad_to = {}, {}
        for batch in batches:
            width = max(len(row['tokens']) for row in batch)
            for row, pred in zip(batch, engine.predict_encoded(batch)):
                outputs[row['id']] = pred
                pad_to[row['id']] = width
        elapsed_cpu, elapsed = time.process_time() - cpu, time.perf_counter() - wall
        stats = collections.Counter()
        for rid, pred in outputs.items():
            actual = {atom_key(a['atom']) for a in pred}
            stats.update(rows=1, exact=int(actual == gold[rid]), gold=len(gold[rid]),
                         predicted=len(actual), correct=len(actual & gold[rid]))
        stats['exact_rate'] = stats['exact'] / stats['rows']
        stats['f1'] = 2 * stats['correct'] / max(1, stats['gold'] + stats['predicted'])
        results[policy] = {'aggregate': dict(stats), 'batches': len(batches),
                           'prediction_wall_seconds': elapsed,
                           'prediction_process_cpu_seconds': elapsed_cpu,
                           'padded_rows': sum(pad_to[r['id']] > len(r['tokens']) for r in ordered),
                           'extra_padding_tokens': sum(pad_to[r['id']] - len(r['tokens']) for r in ordered),
                           'prediction_sha256': hashlib.sha256(json.dumps(
                               {rid: sorted(atom_key(p['atom']) for p in pred)
                                for rid, pred in sorted(outputs.items())},
                               sort_keys=True).encode()).hexdigest()}
        predictions[policy], paddings[policy] = outputs, pad_to

    comparisons = {}
    changed_ids = set()
    for left, right in itertools.combinations(plans, 2):
        changed, span_changed, score_changed, score_examples = [], [], [], []
        largest_score_delta = 0.0
        for rid in gold:
            a, b = predictions[left][rid], predictions[right][rid]
            ka, kb = {atom_key(x['atom']) for x in a}, {atom_key(x['atom']) for x in b}
            if ka != kb:
                changed.append(rid)
            sa = {(atom_key(x['atom']), tuple(x['value_span_chars'])): x['model_score'] for x in a}
            sb = {(atom_key(x['atom']), tuple(x['value_span_chars'])): x['model_score'] for x in b}
            if set(sa) != set(sb):
                span_changed.append(rid)
            delta = max((abs(sa[k] - sb[k]) for k in sa.keys() & sb.keys()), default=0.0)
            largest_score_delta = max(largest_score_delta, delta)
            if delta > 1e-5:
                score_changed.append(rid)
                largest_key = max(sa.keys() & sb.keys(), key=lambda k: abs(sa[k] - sb[k]))
                score_examples.append({'id': rid, 'absolute_score_delta': delta,
                                       'left_score': sa[largest_key], 'right_score': sb[largest_key],
                                       'left_padding_width': paddings[left][rid],
                                       'right_padding_width': paddings[right][rid],
                                       'atom_key': largest_key[0], 'value_span_chars': largest_key[1]})
        changed_ids.update(changed)
        comparisons[left + '__vs__' + right] = {
            'atom_set_difference_rows': len(changed), 'different_ids': changed,
            'atom_and_span_difference_rows': len(span_changed),
            'matched_atom_confidence_difference_rows_over_1e-5': len(score_changed),
            'confidence_difference_ids': score_changed,
            'max_matched_atom_confidence_delta': largest_score_delta,
            'largest_confidence_examples': sorted(score_examples, key=lambda r: r['absolute_score_delta'], reverse=True)[:5],
            'exact_count_delta_right_minus_left': results[right]['aggregate']['exact'] - results[left]['aggregate']['exact'],
        }
    example_rows = []
    for row in ordered:
        if row['id'] not in changed_ids:
            continue
        example_rows.append({'id': row['id'], 'token_length': len(row['tokens']),
                             'padding_width': {p: paddings[p][row['id']] for p in plans},
                             'predictions': {p: predictions[p][row['id']] for p in plans}})
    after = {name: digest(bundle / name) for name in hashes}
    if after != hashes:
        raise RuntimeError('Frozen bundle changed during audit')
    report = {
        'scope': 'Official390 development only; gold only in aggregate scores; no final evaluation',
        'policy_definition': 'Stable token-length sorting within official390 only; exact_length48 has no token padding. This is not the historical mixed8570 selection schedule.',
        'bundle': str(bundle), 'bundle_sha256': hashes,
        'bundle_unchanged': True, 'dev_sha256': digest(args.dev),
        'text_input_sha256': hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest(),
        'audit_source_sha256': digest(__file__), 'python': platform.python_version(),
        'onnxruntime': __import__('onnxruntime').__version__,
        'providers': engine.session.get_providers(), 'cpu_threads': args.threads,
        'initialization_seconds': initialization_seconds, 'encoding_seconds': encoding_seconds,
        'unique_token_lengths': len(by_length),
        'token_lengths': {'min': min(by_length), 'max': max(by_length)},
        'policies': results, 'comparisons': comparisons,
        'peak_process_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
    out.mkdir(parents=True)
    (out / 'report.json').write_text(json.dumps(report, indent=2))
    with (out / 'changed-development-predictions.jsonl').open('w') as stream:
        for row in example_rows:
            stream.write(json.dumps(row) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
