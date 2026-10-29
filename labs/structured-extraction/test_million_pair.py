import unittest
from prepare_million_pair import source_ids,recorded_leaves,admission
from grammar import Grammar


class MillionPairTests(unittest.TestCase):
    def test_context_and_target_sources_are_protected(self):
        row={'metadata':{'source_ids':['p-1']},'input':{'context':[{'id':'p-909'},{'id':'binding-p-20'}]},
             'target':{'structure':{'type':'compare','left':'p-33','right':'p-44'}}}
        self.assertEqual(source_ids(row),{'p-1','p-909','p-20','p-33','p-44'})

    def test_disjunction_and_scoped_negation_are_not_flat_assertions(self):
        leaf={'type':'recorded','source_id':'p-1'}
        for bad in [{'type':'any','children':[leaf]},{'type':'not','child':leaf},
                    {'type':'all','children':[leaf,{'type':'compare','left':'p-1','right':'p-2'}]}]:
            self.assertIsNone(recorded_leaves(bad))

    def test_note_date_duplicate_cannot_get_a_fabricated_value_span(self):
        grammar=Grammar({'subjects':[{'name':'Example','aliases':[],'attributes':['joined']}],'events':[]},[])
        meta={'pairs':[['Example','joined']],'max_tokens':384}
        row={'id':'x','input':{'text':'The 12 January 2026 note says Example joined on 12 January 2026.','context':[]},
             'target':{'parse_status':'resolved','structure':{'type':'recorded','subject':'Example','attribute':'joined',
                       'source_id':'p-1','date':'2026-01-12','value':{'kind':'date','value':'2026-01-12'}}}}
        self.assertEqual(admission(row,grammar,meta)[0],'ambiguous_literal_candidates')
        row['input']['text']='Example joined on 12 January 2026.'
        status,aligned=admission(row,grammar,meta)
        self.assertEqual(status,'admitted');self.assertEqual(len(aligned['alignment']),1)


if __name__=='__main__':unittest.main()
