"""Padding-corrected discriminative models with optional factorized label heads.

Only train-derived value-kind priors are used; the public lexicon does not define
authoritative value types. Priors remain soft, so a strong text score can override.
"""
import torch
from torch import nn
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence


CONFIGS = {
    'packed-flat': dict(hidden=128, layers=1, factorized=False, kind_prior=False),
    'factorized': dict(hidden=128, layers=1, factorized=True, kind_prior=True),
    'factorized-large': dict(hidden=192, layers=2, factorized=True, kind_prior=True),
}


def make_schema(meta, trainrows):
    subjects = sorted({s for s, _ in meta['pairs']})
    attributes = sorted({a for _, a in meta['pairs']})
    si = {s:i for i,s in enumerate(subjects)}
    ai = {a:i for i,a in enumerate(attributes)}
    observed = [[False] * (len(meta['pairs']) + 1) for _ in range(10)]
    for k in range(10): observed[k][0] = True
    for row in trainrows:
        for candidate in row['candidates']:
            if candidate['label'] > 0:
                observed[candidate['kind']][candidate['label']] = True
    # Unseen pairs are not prohibited. Boolean true/false have a shared value type.
    for label in range(1, len(meta['pairs']) + 1):
        if not any(observed[k][label] for k in range(10)):
            for k in range(10): observed[k][label] = True
        if observed[8][label] or observed[9][label]:
            observed[8][label] = observed[9][label] = True
    return dict(subjects=subjects, attributes=attributes,
                pair_subject=[si[s] for s,a in meta['pairs']],
                pair_attribute=[ai[a] for s,a in meta['pairs']],
                observed_kind=observed, current_id=meta['vocab']['<current>'])


class FactorizedExtractor(nn.Module):
    def __init__(self, vocab_size, char_size, n_pairs, config, schema):
        super().__init__()
        self.config = dict(config)
        self.current_id = schema['current_id']
        self.word = nn.Embedding(vocab_size, 128, padding_idx=0)
        self.char = nn.Embedding(char_size, 24, padding_idx=0)
        self.char_conv = nn.Conv1d(24, 48, 3, padding=1)
        h = config['hidden']; width = h * 2
        self.encoder = nn.LSTM(176, h, num_layers=config['layers'],
                               batch_first=True, bidirectional=True,
                               dropout=.15 if config['layers'] > 1 else 0)
        self.drop = nn.Dropout(.15)
        self.kind = nn.Embedding(10, 32)
        self.query = nn.Linear(width + 32, width)
        self.register_buffer('pair_subject', torch.tensor(schema['pair_subject']))
        self.register_buffer('pair_attribute', torch.tensor(schema['pair_attribute']))
        prior = torch.tensor(schema['observed_kind'], dtype=torch.float32)
        self.register_buffer('kind_prior', (1 - prior) * -3.0)
        if config['factorized']:
            self.context_gate = nn.Linear(width * 3 + 32, 1)
            self.features = nn.Sequential(nn.Linear(width * 4 + 32, 256),
                                          nn.GELU(), nn.Dropout(.15))
            self.subject_head = nn.Linear(256, len(schema['subjects']))
            self.attribute_head = nn.Linear(256, len(schema['attributes']))
            self.pair_head = nn.Linear(256, n_pairs + 1)
        else:
            self.head = nn.Sequential(nn.Linear(width * 3 + 32, 256),
                                     nn.GELU(), nn.Dropout(.15),
                                     nn.Linear(256, n_pairs + 1))

    def forward(self, words, chars, spans, clauses, kinds):
        mask = words.ne(0)
        b, t, c = chars.shape
        ch = self.char(chars).reshape(b*t, c, 24).transpose(1, 2)
        ch = self.char_conv(ch).relu().amax(-1).reshape(b, t, 48)
        # CNN biases must not create a nonzero embedding for padding tokens.
        ch = ch * mask.unsqueeze(-1)
        x = self.drop(torch.cat([self.word(words), ch], -1))
        lengths = mask.sum(-1)
        lengths_sorted, order = lengths.sort(descending=True)
        packed = pack_padded_sequence(x.index_select(0, order),
                                     lengths_sorted.cpu(), batch_first=True,
                                     enforce_sorted=True)
        packed, _ = self.encoder(packed)
        x, _ = pad_packed_sequence(packed, batch_first=True, total_length=words.shape[1])
        inverse = order.argsort()
        x = x.index_select(0, inverse) * mask.unsqueeze(-1)
        value = torch.bmm(spans, x)
        clause = torch.bmm(clauses, x)
        kind = self.kind(kinds)
        query = self.query(torch.cat([value, kind], -1))
        scores = torch.bmm(query, x.transpose(1, 2)) / (x.shape[-1] ** .5)
        if not self.config['factorized']:
            scores = scores.masked_fill(~mask[:, None, :], -10000)
            context = torch.bmm(scores.softmax(-1), x)
            return self.head(torch.cat([value, clause, context, kind], -1))
        # Derive boundaries from text-only tokens; the caller supplies context.
        is_current = words.eq(self.current_id).long().cumsum(-1).gt(0) & mask
        is_previous = ~is_current & mask
        local_scores = scores.masked_fill(~is_current[:, None, :], -10000)
        past_scores = scores.masked_fill(~is_previous[:, None, :], -10000)
        local = torch.bmm(local_scores.softmax(-1), x)
        previous = torch.bmm(past_scores.softmax(-1), x)
        gate = torch.sigmoid(self.context_gate(torch.cat([value, clause, local, kind], -1)))
        mixed = gate * previous + (1-gate) * local
        features = self.features(torch.cat([value, clause, local, mixed, kind], -1))
        pairs = self.pair_head(features)
        subjects = self.subject_head(features).index_select(-1, self.pair_subject)
        attributes = self.attribute_head(features).index_select(-1, self.pair_attribute)
        result = torch.cat([pairs[..., :1], pairs[..., 1:] + subjects + attributes], -1)
        if self.config['kind_prior']:
            result = result + self.kind_prior[kinds]
        return result


def load_model(checkpoint, device='cpu'):
    ck = torch.load(checkpoint, map_location=device, weights_only=False)
    m = ck['meta']
    model = FactorizedExtractor(len(m['vocab']), len(m['chars']), len(m['pairs']),
                                ck['config'], ck['schema']).to(device)
    model.load_state_dict(ck['model'])
    return model.eval(), ck
