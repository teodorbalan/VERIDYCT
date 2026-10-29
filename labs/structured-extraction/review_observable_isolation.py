"""Independent counterfactual checks of a selected observable-semantics source.

Does not open any dataset. Fixtures are deliberately invented typed assertions,
not Hooly evidence. The source path is explicit to support immutable snapshots.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import pathlib
import unittest

MODULE = None


def atom(value, attribute='price'):
    return dict(subject='Review fixture entity', attribute=attribute,
                value=dict(kind='money', currency='EUR', value=value))


class IsolationTests(unittest.TestCase):
    def setUp(self):
        self.public = [
            dict(id='anchor', text='From 1 July 2026 through 31 July 2026, Review fixture entity costs EUR 5.',
                 date='2026-07-01', label='true'),
            dict(id='query', text='Review fixture entity costs EUR 6.', date='2026-07-15', label=''),
        ]
        self.neural = {'anchor': [atom(5)], 'query': [atom(6)]}
        self.gold = {'anchor': dict(form=[atom(5)], label='true'),
                     'query': dict(form=[atom(6)], label='false')}

    def test_counterfactual_gold_changes_scoring_but_not_neural_predictions(self):
        before_public, before_neural = copy.deepcopy(self.public), copy.deepcopy(self.neural)
        first_report, first = MODULE.run(self.public, self.gold, self.neural, {})
        changed = copy.deepcopy(self.gold)
        changed['query']['form'] = [atom(5)]
        changed['query']['label'] = 'true'
        changed['query'].update(expected_value={'secret': 999}, assertion_verdicts=['false'],
                                evidence_ids=['hidden-fact'], world_id='counterfactual-hidden-world')
        second_report, second = MODULE.run(self.public, changed, self.neural, {})
        for suffix in ['__intervals', '__intervals_and_same_day']:
            name = 'neural_forms__neural_forms' + suffix
            self.assertEqual(first[name], second[name])
            self.assertEqual(first[name]['query']['label'], 'false')
            self.assertEqual(first_report[name]['correct'], 1)
            self.assertEqual(second_report[name]['correct'], 0)
            oracle = 'oracle_forms__oracle_forms' + suffix
            self.assertNotEqual(first[oracle], second[oracle])
        self.assertEqual(self.public, before_public)
        self.assertEqual(self.neural, before_neural)

    def test_hidden_metadata_never_changes_any_variant(self):
        _, first = MODULE.run(self.public, self.gold, self.neural, {})
        changed = copy.deepcopy(self.gold)
        for row in changed.values():
            row.update(expected_value='unrelated', assertion_verdicts=['unsure'],
                       context_row_id='fake-gold-pointer', validity_qualifier='hidden interval',
                       evidence_ids=['private'], world_id='fake')
        _, second = MODULE.run(self.public, changed, self.neural, {})
        self.assertEqual(first, second)

    def test_unlabelled_public_row_cannot_license_its_own_truth(self):
        self.public[0]['label'] = ''
        index, count = MODULE.make_index(self.public, self.neural, True)
        self.assertEqual(count, 0)
        self.assertEqual(MODULE.judge(self.public[1], self.neural['query'], index, {})['label'], 'unsure')

    def test_missing_false_atom_is_a_real_end_to_end_failure(self):
        # True evidence establishes price=5 and setup=10. A partial extractor
        # misses the setup=99 assertion, so a wrong true verdict is possible.
        self.neural['anchor'] = [atom(5), atom(10, 'setup')]
        self.neural['query'] = [atom(5)]
        self.gold['anchor']['form'] = copy.deepcopy(self.neural['anchor'])
        self.gold['query']['form'] = [atom(5), atom(99, 'setup')]
        report, preds = MODULE.run(self.public, self.gold, self.neural, {})
        name = 'neural_forms__neural_forms__intervals'
        self.assertEqual(preds[name]['query']['label'], 'true')
        self.assertEqual(report[name]['correct'], 0)
        self.assertEqual(preds['oracle_forms__oracle_forms__intervals']['query']['label'], 'false')

    def test_conflict_policy_is_about_predicate_results_not_distinct_values(self):
        index = {('Review fixture entity', 'price'): [
            dict(id='a', start='2026-07-01', end='2026-08-01', value=atom(5)['value']),
            dict(id='b', start='2026-07-01', end='2026-08-01', value=atom(6)['value'])]}
        row = self.public[1]
        self.assertEqual(MODULE.judge(row, [atom(5)], index, {})['label'], 'unsure')
        self.assertEqual(MODULE.judge(row, [atom(7)], index, {})['label'], 'false')


def main():
    global MODULE
    p = argparse.ArgumentParser()
    p.add_argument('--source', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    source, out = pathlib.Path(a.source), pathlib.Path(a.out)
    if out.exists():
        raise ValueError('Use a fresh review receipt')
    spec = importlib.util.spec_from_file_location('reviewed_observable_semantics', source)
    MODULE = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(MODULE)
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(IsolationTests))
    receipt = dict(source=str(source), source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                   tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                   scope='Invented counterfactual fixtures; no archive or final gold opened. Tests document both isolation and known failure modes.')
    out.write_text(json.dumps(receipt, indent=2) + '\n')
    if not result.wasSuccessful():
        raise SystemExit(1)


if __name__ == '__main__':
    main()
