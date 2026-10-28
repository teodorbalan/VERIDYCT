"""Semantic regression tests for the new training controls."""
import unittest
import torch
from train_robust import rdrop_kl
from prepare_robust import transfer_labels


class RobustTrainingTests(unittest.TestCase):
    def test_consistency_identical_and_masked(self):
        p = torch.tensor([[[1., 2., 3.], [5., -1., 0.]]], requires_grad=True)
        labels = torch.tensor([[1, -100]])
        self.assertEqual(float(rdrop_kl(p, p, labels)), 0.)
        q = p.detach().clone()
        q[0, 1] = torch.tensor([-20., 20., 0.])
        self.assertEqual(float(rdrop_kl(p, q, labels)), 0.)
        q[0, 0] = torch.tensor([3., 2., 1.])
        first = rdrop_kl(p, q, labels)
        self.assertGreater(float(first), 0.)
        self.assertAlmostEqual(float(first), float(rdrop_kl(q, p, labels)))
        first.backward()
        self.assertTrue(torch.isfinite(p.grad).all())

    def test_equal_distractor_value_does_not_inherit_label(self):
        value = {'kind': 'money', 'value': 20, 'currency': 'EUR'}
        source = {'candidates': [{'start': 10, 'end': 13, 'value': value, 'label': 7}]}
        encoded = {'candidates': [
            {'start': 3, 'end': 6, 'value': dict(value)},
            {'start': 30, 'end': 33, 'value': dict(value)}]}
        transfer_labels(source, encoded, shift=20)
        self.assertEqual([c['label'] for c in encoded['candidates']], [0, 7])


if __name__ == '__main__':
    unittest.main()
