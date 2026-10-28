"""No held-out data is needed to verify schema graph isolation or gradients."""
import unittest
import torch
from model_graph import GraphExtractor, CONFIGS, schema_tensors, fold_graph_head, CandidateGraphBlock


class GraphTests(unittest.TestCase):
    def setUp(self):
        self.meta = {'vocab': {'<pad>': 0, '<unk>': 1, 'a': 2, 'b': 3,
                               'price': 4, 'count': 5},
                     'chars': {'<pad>': 0, '<unk>': 1},
                     'pairs': [['A', 'price'], ['A', 'count'], ['B', 'price']]}

    def test_edge_mean_and_none_isolation(self):
        _, (subject, attribute) = schema_tensors(self.meta)
        self.assertEqual(subject[1, 2], 1)
        self.assertEqual(attribute[1, 3], 1)
        self.assertEqual(subject[1, 3], 0)
        self.assertEqual(subject[0].sum(), 0)
        self.assertEqual(attribute[:, 0].sum(), 0)
        self.assertTrue(torch.isfinite(subject).all())

    def test_graph_runs_and_backpropagates_to_label_messages(self):
        model = GraphExtractor(self.meta, CONFIGS['graph-label'])
        words = torch.tensor([[2, 4, 5]])
        chars = torch.ones(1, 3, 24, dtype=torch.long)
        spans = torch.tensor([[[0., 1., 0.]]])
        logits = model(words, chars, spans, spans, torch.tensor([[0]]))
        self.assertEqual(tuple(logits.shape), (1, 1, 4))
        logits.square().sum().backward()
        self.assertGreater(model.blocks[0].subject.weight.grad.abs().sum(), 0)
        self.assertTrue(torch.isfinite(logits).all())

    def test_static_graph_folding_preserves_input_logits(self):
        torch.manual_seed(7)
        model = GraphExtractor(self.meta, CONFIGS['graph-label']).eval()
        folded = fold_graph_head(model, self.meta)
        for length in [3, 11]:
            words = torch.full((2, length), 2, dtype=torch.long)
            chars = torch.ones(2, length, 24, dtype=torch.long)
            spans = torch.zeros(2, 2, length)
            spans[:, 0, 1] = 1
            spans[:, 1, 2] = 1
            args = (words, chars, spans, spans, torch.tensor([[0, 1], [1, 0]]))
            with torch.no_grad():
                torch.testing.assert_close(model(*args), folded(*args), atol=1e-6, rtol=1e-5)

    def test_disconnected_candidate_cannot_change_other_clause(self):
        torch.manual_seed(11)
        block = CandidateGraphBlock(8).eval()
        features = torch.randn(1, 3, 8)
        spans = torch.eye(3)[None]
        clauses = torch.tensor([[[1., 0., 0.], [0., 1., 0.], [0., 1., 0.]]])
        with torch.no_grad():
            before = block(features, spans, clauses)
            changed = features.clone(); changed[:, 2] += 100
            after = block(changed, spans, clauses)
        torch.testing.assert_close(before[:, 0], after[:, 0], atol=0, rtol=0)
        self.assertGreater((before[:, 1] - after[:, 1]).abs().sum(), 0)


if __name__ == '__main__':
    unittest.main()
