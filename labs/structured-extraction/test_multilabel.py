import unittest
import numpy as np
from runtime_multilabel import decode_multilabel


class MultilabelTests(unittest.TestCase):
    def test_one_value_can_have_two_subjects(self):
        row={'text':'A and B cost 79 EUR.', 'candidates':[{'start':13,'end':19,'value':{'kind':'money','value':79,'currency':'EUR'}}]}
        pred=decode_multilabel([row],np.array([[[-9.,8.,7.]]]),[['A','price'],['B','price']])[0]
        self.assertEqual({x['atom']['subject'] for x in pred},{'A','B'})

    def test_all_negative_logits_abstain_even_if_none_logit_negative(self):
        row={'text':'79 EUR', 'candidates':[{'start':0,'end':6,'value':{'kind':'money','value':79,'currency':'EUR'}}]}
        self.assertEqual(decode_multilabel([row],np.array([[[-100.,-6.,-7.]]]),[['A','price'],['B','price']])[0],[])

    def test_equal_values_in_separate_clauses_do_not_copy_other_labels(self):
        row={'text':'A costs 79 EUR. B costs 79 EUR.', 'candidates':[{'start':8,'end':14,'value':{'kind':'money','value':79,'currency':'EUR'}},{'start':24,'end':30,'value':{'kind':'money','value':79,'currency':'EUR'}}]}
        pred=decode_multilabel([row],np.array([[[-9.,7.,-7.],[-9.,-7.,7.]]]),[['A','price'],['B','price']])[0]
        self.assertEqual([(x['atom']['subject'],x['value_span_chars']) for x in pred],[('A',[8,14]),('B',[24,30])])


if __name__=='__main__':unittest.main()
