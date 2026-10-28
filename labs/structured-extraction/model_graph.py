"""Public-schema label graphs on a discriminative character/BiLSTM encoder.

Labels carry subject and attribute names, not world facts or expected values.
The semantic-only variant is the controlled no-message-passing ablation.
"""
import math
import torch
from torch import nn
from model import Extractor as BaseExtractor
from prepare import tokens


CONFIGS = {
    'semantic-label': dict(encoder='lstm', hidden=128, layers=1, char=True,
                           label_graph_layers=0, label_width=128),
    'graph-label': dict(encoder='lstm', hidden=128, layers=1, char=True,
                        label_graph_layers=2, label_width=128),
    'candidate-graph': dict(encoder='lstm', hidden=128, layers=1, char=True,
                            label_graph_layers=0, label_width=128, candidate_graph_layers=1),
}


def schema_tensors(meta):
    pairs = [['<none>', '<none>']] + meta['pairs']
    ids = []
    for side in (0, 1):
        sequences = [[meta['vocab'].get(w, 1)
                      for w, _, _ in tokens(pair[side].replace('_', ' '))]
                     for pair in pairs]
        width = max(len(s) for s in sequences)
        table = torch.zeros(len(pairs), width, dtype=torch.long)
        for i, sequence in enumerate(sequences):
            table[i, :len(sequence)] = torch.tensor(sequence)
        ids.append(table)
    graphs = []
    for side in (0, 1):
        adjacency = torch.tensor([
            [float(i > 0 and j > 0 and i != j and a[side] == b[side])
             for j, b in enumerate(pairs)] for i, a in enumerate(pairs)])
        adjacency /= adjacency.sum(-1, keepdim=True).clamp_min(1)
        graphs.append(adjacency)
    return ids, graphs


class LabelGraphBlock(nn.Module):
    def __init__(self, width):
        super().__init__()
        self.subject = nn.Linear(width, width, bias=False)
        self.attribute = nn.Linear(width, width, bias=False)
        self.self_update = nn.Linear(width, width)
        self.norm = nn.LayerNorm(width)
        self.gates = nn.Parameter(torch.full((2,), -1.0))

    def forward(self, labels, same_subject, same_attribute):
        gates = self.gates.sigmoid()
        messages = (gates[0] * same_subject.matmul(self.subject(labels))
                    + gates[1] * same_attribute.matmul(self.attribute(labels)))
        return labels + .25 * self.norm(torch.tanh(self.self_update(labels) + messages))


class CandidateGraphBlock(nn.Module):
    """Input-dependent attention among value candidates in overlapping clauses."""
    def __init__(self, width):
        super().__init__()
        self.query = nn.Linear(width, 128, bias=False)
        self.key = nn.Linear(width, 128, bias=False)
        self.value = nn.Linear(width, width, bias=False)
        self.update = nn.Sequential(nn.Linear(width, width), nn.GELU(), nn.Dropout(.1))
        self.norm = nn.LayerNorm(width)
        self.gate = nn.Parameter(torch.tensor(-2.0))

    def forward(self, features, spans, clauses):
        valid = spans.sum(-1).gt(0)
        linked = torch.bmm(clauses, clauses.transpose(1, 2)).gt(0)
        linked = linked & valid[:, None, :]
        scores = torch.bmm(self.query(features), self.key(features).transpose(1, 2)) / math.sqrt(128)
        scores = scores.masked_fill(~linked, -10000)
        messages = torch.bmm(scores.softmax(-1), self.value(features))
        updated = features + self.gate.sigmoid() * self.update(self.norm(messages))
        return updated * valid.unsqueeze(-1)


class GraphExtractor(BaseExtractor):
    def __init__(self, meta, config):
        super().__init__(len(meta['vocab']), len(meta['chars']), len(meta['pairs']), config)
        # Retain the baseline feature encoder and direct classifier exactly.
        feature_width = self.head[-1].in_features
        direct = self.head[-1]
        self.head = nn.Sequential(*list(self.head.children())[:-1])
        self.direct = direct
        width = config['label_width']
        ids, graphs = schema_tensors(meta)
        self.register_buffer('subject_names', ids[0])
        self.register_buffer('attribute_names', ids[1])
        self.register_buffer('same_subject', graphs[0])
        self.register_buffer('same_attribute', graphs[1])
        self.label_residual = nn.Parameter(torch.empty(len(meta['pairs']) + 1, width))
        nn.init.normal_(self.label_residual, std=.05)
        self.semantic = nn.Sequential(nn.Linear(256, width), nn.Tanh(), nn.LayerNorm(width))
        self.blocks = nn.ModuleList(LabelGraphBlock(width)
                                   for _ in range(config['label_graph_layers']))
        self.candidate_project = nn.Linear(feature_width, width, bias=False)
        self.graph_scale = nn.Parameter(torch.tensor(-.7))
        self.label_width = width
        self.candidate_blocks = nn.ModuleList(CandidateGraphBlock(feature_width)
                                             for _ in range(config.get('candidate_graph_layers', 0)))

    def name_mean(self, indices):
        mask = indices.ne(0).unsqueeze(-1)
        return (self.word(indices) * mask).sum(1) / mask.sum(1).clamp_min(1)

    def label_vectors(self):
        labels = self.semantic(torch.cat([self.name_mean(self.subject_names),
                                          self.name_mean(self.attribute_names)], -1))
        labels = labels + self.label_residual
        for block in self.blocks:
            labels = block(labels, self.same_subject, self.same_attribute)
        return labels

    def forward(self, words, chars, spans, clauses, kinds):
        features = super().forward(words, chars, spans, clauses, kinds)
        for block in self.candidate_blocks:
            features = block(features, spans, clauses)
        label_logits = self.candidate_project(features).matmul(self.label_vectors().T)
        return self.direct(features) + self.graph_scale.sigmoid() * label_logits / math.sqrt(self.label_width)


def load_model(checkpoint, device='cpu'):
    ck = torch.load(checkpoint, map_location='cpu', weights_only=False)
    model = GraphExtractor(ck['meta'], ck['config'])
    model.load_state_dict(ck['model'])
    return model.to(device).eval(), ck


@torch.no_grad()
def fold_graph_head(model, meta):
    """Exactly fold static graph-label scoring into the deployment linear head.

    Both direct and graph classifiers act linearly on the same candidate feature.
    No input-dependent graph state exists, so this is an algebraic equivalence,
    not distillation, quantization, or a separately trained approximation.
    """
    model.eval()
    if len(model.candidate_blocks):
        raise ValueError('Input-dependent candidate graph cannot be folded into a static linear head')
    config = {k: model.config[k] for k in ['encoder', 'hidden', 'layers', 'char']}
    folded = BaseExtractor(len(meta['vocab']), len(meta['chars']), len(meta['pairs']), config)
    folded = folded.to(device=model.word.weight.device, dtype=model.word.weight.dtype).eval()
    state = folded.state_dict()
    for name, value in model.state_dict().items():
        if name in state:
            state[name] = value
    state['head.3.weight'] = (model.direct.weight + model.graph_scale.sigmoid()
                              * model.label_vectors().matmul(model.candidate_project.weight)
                              / math.sqrt(model.label_width))
    state['head.3.bias'] = model.direct.bias
    folded.load_state_dict(state)
    return folded
