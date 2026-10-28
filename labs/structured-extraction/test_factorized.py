import unittest
import torch
from model_factorized import FactorizedExtractor, CONFIGS


class PaddingTests(unittest.TestCase):
    def test_unrelated_batch_padding_does_not_change_real_candidate(self):
        torch.set_num_threads(1); torch.manual_seed(7)
        schema = dict(current_id=3, pair_subject=[0,1], pair_attribute=[0,0],
                      subjects=['a','b'], attributes=['x'], observed_kind=[[True]*3 for _ in range(10)])
        for config in CONFIGS.values():
            model=FactorizedExtractor(20,20,2,config,schema).eval()
            words=torch.tensor([[2,3,4,5]])
            chars=torch.zeros(1,4,24,dtype=torch.long); chars[:,:,:2]=4
            spans=torch.tensor([[[0.,0.,.5,.5]]]); clauses=spans.clone(); kinds=torch.tensor([[0]])
            with torch.no_grad(): first=model(words,chars,spans,clauses,kinds)
            # Add long unrelated row and 9 padding tokens to the original row.
            w=torch.zeros(2,13,dtype=torch.long);w[0,:4]=words[0];w[1]=4;w[1,1]=3
            c=torch.zeros(2,13,24,dtype=torch.long);c[0,:4]=chars[0];c[1,:,:2]=7
            s=torch.zeros(2,1,13);s[0,:,:4]=spans[0];s[1,0,5]=1
            with torch.no_grad(): padded=model(w,c,s,s,torch.zeros(2,1,dtype=torch.long))
            torch.testing.assert_close(first[0],padded[0],rtol=1e-5,atol=1e-6)

    def test_longest_overlapping_alias_wins_without_hard_subject_decision(self):
        # IDs 4,5,6 stand for Hooly, Maps, Day. An inner Maps Day match must
        # lose to the longer Hooly Maps Day span even though their starts differ.
        schema=dict(current_id=3,pair_subject=[0,1,2,3],pair_attribute=[0]*4,
                    subjects=['Hooly','Hooly Maps','Maps Day','Hooly Maps Day'],
                    attributes=['x'],observed_kind=[[True]*5 for _ in range(10)],
                    aliases=[[4],[4,5],[5,6],[4,5,6]],alias_subject=[0,1,2,3])
        model=FactorizedExtractor(20,20,4,CONFIGS['factorized-mentions'],schema).eval()
        mentions=model.alias_mentions(torch.tensor([[2,3,4,5,6,8,4,8,4,5]]))
        self.assertEqual(mentions.nonzero().tolist(),[[0,2,3],[0,6,0],[0,8,1]])

    def test_named_object_is_not_its_own_subject_mention(self):
        schema=dict(current_id=3,pair_subject=[0,1],pair_attribute=[0,0],
                    subjects=['Company','Partner'],attributes=['x'],
                    observed_kind=[[True]*3 for _ in range(10)],
                    aliases=[[4],[5]],alias_subject=[0,1])
        model=FactorizedExtractor(20,20,2,CONFIGS['factorized-mentions'],schema).eval()
        words=torch.tensor([[2,3,4,8,5]])
        value=torch.tensor([[[0.,0.,0.,0.,1.]]]);clause=torch.ones_like(value)/5
        current=words.ne(2);previous=~current
        prior=model.mention_prior(words,value,clause,torch.tensor([[6]]),current,previous)
        self.assertGreater(prior[0,0,0].item(),0)
        self.assertEqual(prior[0,0,1].item(),0)
        boolean=model.mention_prior(words,clause,clause,torch.tensor([[8]]),current,previous)
        self.assertGreater(boolean[0,0,1].item(),0)


if __name__ == '__main__': unittest.main()
