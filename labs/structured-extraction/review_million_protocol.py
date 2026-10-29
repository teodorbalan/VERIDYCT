"""Read-only audit of the bounded million experiment; CPU reconstruction only.

Reads existing TRAIN/DEV preparations and run receipts. Does not run inference,
open final/calibration fixtures, modify jobs, or change a model/data artifact.
"""
import argparse
import collections
import csv
import hashlib
import json
import os
from pathlib import Path
import sys

os.environ['CUDA_VISIBLE_DEVICES'] = ''


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def norm(text):
    return ' '.join(text.casefold().split())


def rows(path):
    with Path(path).open(encoding='utf-8') as f:
        for line in f:
            yield json.loads(line)


def hash_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', required=True, help='Remote training root')
    p.add_argument('--out', required=True)
    p.add_argument('--practice', required=True, help='Unmodified original public practice CSV')
    a = p.parse_args()
    root = Path(a.root)
    work = root / 'v3-factorized'
    source = work / 'source-million-training-v2'
    sys.path.insert(0, str(source))
    import numpy as np
    import torch
    from model_factorized import FactorizedExtractor, CONFIGS, make_schema
    from prepare import tokens
    torch.set_num_threads(2)
    data = {'base': work / 'million-paired-base-control',
            'v1': work / 'million-paired-idonly-final/v1',
            'v2': work / 'million-paired-idonly-final/v2'}
    prepared = work / 'million-paired-idonly-final'
    preparation = json.loads((prepared / 'preparation.json').read_text())
    base_meta = json.loads((root / 'data-v3/meta.json').read_text())
    original_dev = list(rows(root / 'data-v3/dev.jsonl'))
    protected = {row['id'] for row in original_dev if row.get('domain') == 'official'}
    assert len(protected) == 390
    dev_texts = {norm(row['text']) for row in original_dev}
    dev_inputs = {(norm(row['text']), norm(row.get('previous_text', ''))) for row in original_dev}
    official_texts = {norm(row['text']) for row in original_dev if row.get('domain') == 'official'}
    official_ids_by_text = collections.defaultdict(list)
    for row in original_dev:
        if row.get('domain') == 'official':
            official_ids_by_text[norm(row['text'])].append(row['id'])
    public_ids_by_text = collections.defaultdict(list)
    with Path(a.practice).open(encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            public_ids_by_text[norm(row['text'])].append(row['id'])
    case_dev = {view: list(rows(data[view] / 'paired-dev.jsonl')) for view in ('v1', 'v2')}
    assert [r['id'] for r in case_dev['v1']] == [r['id'] for r in case_dev['v2']]
    case_texts = {view: {norm(r['text']) for r in rr} for view, rr in case_dev.items()}
    case_inputs = {view: {(norm(r['text']), norm(r.get('previous_text', ''))) for r in rr} for view, rr in case_dev.items()}
    selected = list(rows(prepared / 'selected-pairs.jsonl'))
    folds = {fold: [r for r in selected if r['fold'] == fold] for fold in ('train', 'dev')}
    selected_by_id = {r['id']: r for r in selected}
    refs = {fold: set().union(*(set(r['source_ids']) for r in rr)) for fold, rr in folds.items()}
    groups = {fold: {r['group'] for r in rr} for fold, rr in folds.items()}
    cases = {fold: {r['case_key'] for r in rr} for fold, rr in folds.items()}
    complete_groups = {fold: {tuple(r['source_ids']) for r in rr} for fold, rr in folds.items()}
    assert not (refs['train'] | refs['dev']) & protected
    assert not groups['train'] & groups['dev'] and not cases['train'] & cases['dev']
    result = {'scope': 'CPU read-only preparation/protocol audit; no new inference or training.',
              'source_sha256': {name: sha(source / name) for name in ['prepare_million_pair.py', 'train_factorized.py', 'model_factorized.py', 'train.py', 'runtime.py', 'evaluate_million_pair.py', 'export_factorized.py']},
              'preparation_sha256': sha(prepared / 'preparation.json'),
              'practice_sha256': sha(a.practice),
              'paired_dev_sha256': {view: sha(path / 'paired-dev.jsonl') for view, path in data.items() if view != 'base'},
              'grouping': {'train_rows': len(folds['train']), 'dev_rows': len(folds['dev']),
                           'train_sources': len(refs['train']), 'dev_sources': len(refs['dev']),
                           'shared_sources': len(refs['train'] & refs['dev']),
                           'shared_case_keys': len(cases['train'] & cases['dev']),
                           'shared_metadata_groups': len(groups['train'] & groups['dev']),
                           'shared_complete_reference_sets': len(complete_groups['train'] & complete_groups['dev'])},
              'models': {}, 'context_overlap_caveat': 'Matching a DEV sentence inside TRAIN context is textual exposure; shared wording alone does not identify its source ID or expose its label.'}
    metas, vocabulary_train_words = {}, set()
    for view, path in data.items():
        meta = json.loads((path / 'meta.json').read_text())
        metas[view] = meta
        run = json.loads((work / f'million-factorized-{view}-s271828-r2/run.json').read_text())
        schema_rows, ids = [], []
        counts, kinds = collections.Counter(), collections.Counter()
        contexts = collections.Counter()
        added = collections.Counter()
        overlaps = {target: collections.Counter() for target in ('original', 'v1_case', 'v2_case')}
        base_prefix = hashlib.sha256()
        with (path / 'train.jsonl').open(encoding='utf-8') as f:
            for index, line in enumerate(f):
                row = json.loads(line)
                ids.append(row['id'])
                if index < 50328:
                    base_prefix.update(line.encode())
                schema_rows.append({'candidates': [{'label': c['label'], 'kind': c['kind']} for c in row['candidates']]})
                text, previous = norm(row['text']), norm(row.get('previous_text', ''))
                counts['rows'] += 1
                counts['tokens'] += len(row['tokens'])
                contexts[previous] += 1
                overlaps['original']['text'] += text in dev_texts
                overlaps['original']['full_input'] += (text, previous) in dev_inputs
                overlaps['original']['official_id'] += row['id'] in protected
                for target in ('v1', 'v2'):
                    overlaps[target + '_case']['text'] += text in case_texts[target]
                    overlaps[target + '_case']['full_input'] += (text, previous) in case_inputs[target]
                if row.get('domain') == 'million_case':
                    assert row['id'] in selected_by_id and selected_by_id[row['id']]['fold'] == 'train'
                    ct, tt = tokens(row['previous_text']), tokens(row['text'])
                    assert len(ct) <= 96 and len(ct) + len(tt) + 2 == len(row['tokens']) <= 384
                    assert row['current_offset'] == len(ct) + 2
                    vocabulary_train_words.update(w for w, _, _ in ct + tt)
                    added['rows'] += 1
                    added['tokens'] += len(row['tokens'])
                    added['max_context_tokens'] = max(added['max_context_tokens'], len(ct))
                    for atom in row['form']:
                        kinds[atom['value']['kind']] += 1
            assert counts['rows'] == run['train_rows']
        assert base_prefix.hexdigest() == sha(root / 'data-v3/train.jsonl')
        assert sha(path / 'dev.jsonl') == sha(root / 'data-v3/dev.jsonl')
        assert not any(overlaps['original'].values())
        schema = make_schema(meta, schema_rows)
        torch.manual_seed(run['arguments']['seed'])
        model = FactorizedExtractor(len(meta['vocab']), len(meta['chars']), len(meta['pairs']), CONFIGS['factorized'], schema)
        with torch.no_grad():
            model.word.weight.copy_(torch.from_numpy(np.load(path / 'vectors.npy')))
        def tensor_hash(items):
            h = hashlib.sha256()
            for name, value in items:
                h.update(name.encode()); h.update(value.detach().numpy().tobytes())
            return h.hexdigest()
        context_matches = {context: [t for t in official_texts if t and t in context] for context in contexts if context}
        matched_contexts = {context: matches for context, matches in context_matches.items() if matches}
        outcome = {'run_arguments': run['arguments'], 'gpu': run['gpu'],
                   'source_matches_run_receipt': all(run['source_sha256'].get(name) == digest for name, digest in result['source_sha256'].items()),
                   'files_sha256': {name: sha(path / name) for name in ['meta.json', 'vectors.npy', 'train.jsonl', 'dev.jsonl']},
                   'train': dict(counts), 'added': dict(added), 'added_atom_kinds': dict(kinds),
                   'overlaps': {k: dict(v) for k, v in overlaps.items()},
                   'sorted_training_ids_sha256': hash_json(sorted(ids)),
                   'schema_sha256': hash_json(schema),
                   'cpu_reconstructed_initial_parameters_sha256': tensor_hash(model.named_parameters()),
                   'cpu_reconstructed_initial_buffers_sha256': tensor_hash(model.named_buffers()),
                   'cpu_rng_after_initialization_sha256': hashlib.sha256(torch.get_rng_state().numpy().tobytes()).hexdigest(),
                   'official_dev_sentence_in_train_context': {'train_rows': sum(contexts[c] for c in matched_contexts),
                                                           'distinct_dev_texts': len(set(t for m in matched_contexts.values() for t in m))}}
        overlap_texts = sorted({t for m in matched_contexts.values() for t in m})
        outcome['context_overlap_diagnostics'] = [
            {'official_dev_ids': official_ids_by_text[t],
             'same_normalized_public_text_ids': public_ids_by_text[t],
             'train_context_rows': sum(count for context, count in contexts.items() if t in context),
             'text': t}
            for t in overlap_texts]
        for key in ['seed', 'epochs', 'patience', 'batch', 'lr', 'order_by_id', 'variant']:
            assert run['arguments'][key] == {'seed':271828, 'epochs':20, 'patience':5, 'batch':48, 'lr':.001, 'order_by_id':True, 'variant':'factorized'}[key]
        assert outcome['source_matches_run_receipt']
        result['models'][view] = outcome
        del model, schema_rows
        print(json.dumps({'checked': view, 'rows': counts['rows'], 'context_exposure': outcome['official_dev_sentence_in_train_context']}), flush=True)
    assert metas['base'] == metas['v1'] == metas['v2']
    new_vocab = set(metas['v1']['vocab']) - set(base_meta['vocab'])
    assert new_vocab <= vocabulary_train_words
    for word, index in base_meta['vocab'].items():
        assert metas['v1']['vocab'][word] == index
    for view, rr in case_dev.items():
        for row in rr:
            assert len(tokens(row['previous_text'])) <= 96
            assert len(tokens(row['text'])) + len(tokens(row['previous_text'])) + 2 == len(row['tokens']) <= 384
    first = result['models']['v1']
    for key in ['sorted_training_ids_sha256', 'schema_sha256', 'cpu_reconstructed_initial_parameters_sha256', 'cpu_reconstructed_initial_buffers_sha256', 'cpu_rng_after_initialization_sha256']:
        assert first[key] == result['models']['v2'][key]
    result['new_vocab_words_train_only'] = len(new_vocab)
    result['status'] = 'PASS'
    result['validator_sha256'] = sha(__file__)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'grouping': result['grouping'], 'new_vocab_words_train_only': len(new_vocab)}, indent=2))


if __name__ == '__main__':
    main()
