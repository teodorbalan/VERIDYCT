"""A mixed-vocabulary ensemble must preserve each member's input meaning."""
import unittest
import torch
from torch import nn
from compare_stacks import MappedExtractor, MixedEnsemble


class EchoInputs(nn.Module):
    def forward(self, words, chars, spans, clauses, kinds):
        return words, chars


class FixedLogits(nn.Module):
    def __init__(self, logits):
        super().__init__()
        self.register_buffer('logits', torch.tensor(logits))

    def forward(self, *inputs):
        return self.logits


class StackMappingTests(unittest.TestCase):
    def test_indices_are_mapped_by_token_not_position(self):
        master = dict(pairs=[['a','b']], vocab={'pad':0,'unk':1,'ctx':2,'current':3,'known':4,'new':5},
                      chars={'pad':0,'unk':1,'x':2,'y':3})
        member = dict(pairs=[['a','b']], vocab={'pad':0,'unk':1,'current':2,'ctx':3,'other':4,'known':5},
                      chars={'pad':0,'unk':1,'z':2,'x':3})
        mapped = MappedExtractor(EchoInputs(), master, member)
        words, chars = mapped(torch.tensor([[0,2,3,4,5]]), torch.tensor([[[0,2,3]]]), None, None, None)
        self.assertEqual(words.tolist(), [[0,3,2,5,1]])
        self.assertEqual(chars.tolist(), [[[0,3,1]]])
        member['pairs'] = [['different','b']]
        with self.assertRaises(ValueError):
            MappedExtractor(EchoInputs(), master, member)

    def test_ensemble_averages_probabilities_not_logits(self):
        left, right = FixedLogits([[[4.,1.,0.]]]), FixedLogits([[[0.,1.,2.]]])
        actual = MixedEnsemble([left, right])(None,None,None,None,None).softmax(-1)
        expected = (left.logits.softmax(-1)+right.logits.softmax(-1))/2
        torch.testing.assert_close(actual, expected)


if __name__ == '__main__':
    unittest.main()
