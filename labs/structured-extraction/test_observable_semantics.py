import unittest
from observable_semantics import compare, explicit_interval, judge, make_index


class SemanticsTests(unittest.TestCase):
    def test_inclusive_text_end_becomes_exclusive_internal_end(self):
        self.assertEqual(explicit_interval('From July 1, 2026 through October 29, 2026, X costs 5.'),('2026-07-01','2026-10-30'))
        self.assertEqual(explicit_interval('From the 1st of October 2025 through the 31st of January 2026, X costs 5.'),('2025-10-01','2026-02-01'))
        self.assertIsNone(explicit_interval('X costs 5 on 1 July 2026.'))

    def test_false_compound_cannot_supply_positive_or_negative_atom_evidence(self):
        atom=dict(subject='X',attribute='price',value=dict(kind='money',value=5,currency='EUR'))
        public=[dict(id='a',date='2026-07-01',label='false',text='From 1 July 2026 through 2 July 2026, X costs 5.')]
        index,count=make_index(public,{'a':[atom]},True)
        self.assertEqual(count,0)
        self.assertEqual(judge(dict(id='b',date='2026-07-01'),[atom],index,{})['label'],'unsure')

    def test_interval_boundary_and_false_dominates_missing_evidence(self):
        atom=dict(subject='X',attribute='count',value=dict(kind='quantity',value=5,unit='user'))
        index={('X','count'):[dict(id='a',start='2026-07-01',end='2026-07-03',value=dict(kind='quantity',value=4,unit='user'))]}
        missing=dict(atom,subject='Y')
        self.assertEqual(judge(dict(id='b',date='2026-07-02'),[atom,missing],index,{})['label'],'false')
        self.assertEqual(judge(dict(id='b',date='2026-07-03'),[atom],index,{})['label'],'unsure')

    def test_comparison_direction_precision_and_aliases(self):
        self.assertTrue(compare(dict(kind='quantity',value=5,unit='user',op='gt'),dict(kind='quantity',value=6,unit='user'),{}))
        self.assertIsNone(compare(dict(kind='date',value='2026'),dict(kind='date',value='2026-03-24'),{}))
        self.assertTrue(compare(dict(kind='name',value='Short'),dict(kind='name',value='Long'),{'short':'Long','long':'Long'}))
        self.assertTrue(compare(dict(kind='version',value='2.9.0',op='gt'),dict(kind='version',value='2.10.0'),{}))
        self.assertFalse(compare(dict(kind='version',value='2.3'),dict(kind='version',value='2.3.0'),{}))


if __name__=='__main__':unittest.main()
