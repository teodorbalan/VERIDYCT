import unittest
from grammar import Grammar,canonical

class GrammarTests(unittest.TestCase):
    def setUp(self):self.g=Grammar({'subjects':[{'name':'Hooly AI Pro','aliases':['AI Pro'],'attributes':['price']}]},['Gavin Bellson'])
    def values(self,text):return [c['value'] for c in self.g.candidates(text)]
    def test_price_and_operator(self):
        self.assertIn({'kind':'money','value':79,'currency':'EUR','per':'month'},self.values('AI Pro costs €79 per month.'))
        self.assertIn({'kind':'money','value':49.99,'currency':'EUR','per':'month','op':'lt'},self.values('It costs under €49.99 a month.'))
    def test_versions_at_sentence_boundary(self):
        self.assertIn({'kind':'version','value':'0.11.5','op':'gt'},self.values('Its version is newer than 0.11.5.'))
        self.assertIn({'kind':'version','value':'20.0','op':'le'},self.values('Its version is no newer than 20.0.'))
    def test_signed_percent(self):self.assertIn({'kind':'percent','value':-26.62,'op':'ge'},self.values('Growth is at least -26.62%.'))
    def test_metres_are_not_millions(self):self.assertIn({'kind':'quantity','value':35,'unit':'m'},self.values('It reaches 35 m down.'))
    def test_teams_plural(self):self.assertIn({'kind':'quantity','value':536,'unit':'team'},self.values('It serves 536 teams.'))
    def test_named_version_without_marker(self):self.assertIn({'kind':'version','value':'2.0'},self.values('Hooly Docs 2.0'))
    def test_second_abbreviation(self):self.assertIn({'kind':'duration','value':1.9,'unit':'s'},self.values('Cold start measures 1.9 s.'))
    def test_after_is_not_duration_comparison(self):self.assertIn({'kind':'duration','value':3,'unit':'day'},self.values('It closed after 3 days.'))
    def test_counted_noun_modifiers(self):self.assertIn({'kind':'quantity','value':4,'unit':'site'},self.values('It occupies 4 data centre sites.'))
    def test_indefinite_duration(self):self.assertIn({'kind':'duration','value':1,'unit':'s','op':'lt'},self.values('It replies in under a second.'))
    def test_unseen_name_value(self):self.assertIn({'kind':'name','value':'Ringsend Forum'},self.values('Its venue is Ringsend Forum.'))
    def test_date_offset_and_operator(self):
        value={'kind':'date','value':'2025-04-25','op':'ge'}
        text='€49 was mentioned; joined no earlier than the 25th of April 2025.'
        c=next(c for c in self.g.candidates(text) if c['value']==value)
        self.assertEqual(text[c['start']:c['end']],'25th of April 2025')
    def test_numeric_equivalence_does_not_change_claim(self):
        self.assertEqual(canonical({'kind':'percent','value':24.0}),canonical({'kind':'percent','value':24}))
        self.assertEqual(canonical({'kind':'money','value':.5800000000000001}),canonical({'kind':'money','value':.58}))
        self.assertNotEqual(canonical({'kind':'money','value':.59}),canonical({'kind':'money','value':.58}))
    def test_no_truth_lookup(self):
        a=self.values('AI Pro costs €79 per month.');b=self.values('AI Pro costs €71 per month.')
        self.assertIn({'kind':'money','value':71,'currency':'EUR','per':'month'},b)
        self.assertNotIn({'kind':'money','value':79,'currency':'EUR','per':'month'},b)
        self.assertNotEqual(a,b)

if __name__=='__main__':unittest.main()
