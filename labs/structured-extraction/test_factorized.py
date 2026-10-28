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


if __name__ == '__main__': unittest.main()
