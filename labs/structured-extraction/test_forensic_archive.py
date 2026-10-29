"""Independent checks of the forensic evaluator; no archive or holdout reads."""
import unittest
from forensic_archive import combine, compare, oracle


class ArchiveSemanticsTests(unittest.TestCase):
    def test_false_dominates_unknown(self):
        self.assertEqual(combine(['true', 'unsure']), 'unsure')
        self.assertEqual(combine(['unsure', 'false', 'true']), 'false')
        self.assertEqual(combine(['true', 'true']), 'true')

    def test_expected_value_is_left_operand(self):
        claim = {'kind': 'quantity', 'unit': 'seat', 'op': 'ge', 'value': 3}
        self.assertEqual(compare(claim, {'kind': 'quantity', 'unit': 'seat', 'value': 4}), 'true')
        self.assertEqual(compare(claim, {'kind': 'quantity', 'unit': 'seat', 'value': 2}), 'false')
        self.assertIsNone(compare(claim, {'kind': 'quantity', 'unit': 'person', 'value': 4}))

    def test_half_open_boundary_and_explicit_unknown(self):
        value = {'kind': 'quantity', 'unit': 'seat', 'value': 3}
        atom = {'subject': 'A', 'attribute': 'seats', 'value': value}
        intervals = [
            {'start': '2026-01-01', 'end': '2026-02-01', 'state': 'known', 'value': value},
            {'start': '2026-02-01', 'end': '2026-03-01', 'state': 'unknown', 'value': None},
        ]
        world = {('A', 'seats'): {'intervals': intervals}}
        self.assertEqual(oracle(atom, '2026-01-31', world)[0], 'true')
        self.assertEqual(oracle(atom, '2026-02-01', world)[0], 'unsure')
        self.assertEqual(oracle(atom, '2026-03-01', world), (None, None))

    def test_typed_version_boolean_date_semantics(self):
        self.assertEqual(compare({'kind': 'version', 'op': 'gt', 'value': '2.9'}, {'kind': 'version', 'value': '2.10'}), 'true')
        self.assertEqual(compare({'kind': 'version', 'value': '2.3'}, {'kind': 'version', 'value': '2.3.0'}), 'false')
        self.assertEqual(compare({'kind': 'boolean', 'value': False}, {'kind': 'boolean', 'value': False}), 'true')
        self.assertIsNone(compare({'kind': 'date', 'value': '2026-03'}, {'kind': 'date', 'value': '2026-03-01'}))


if __name__ == '__main__':
    unittest.main()
