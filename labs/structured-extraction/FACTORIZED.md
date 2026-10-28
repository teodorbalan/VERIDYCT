# Factorized extractor experiment

Owner: factorized worker, authorized by Teodor on 2026-10-29. Human ownership
unassigned. Isolated branch `teodorbalan/extraction-factorized-v3`, base `e0c2a12`.
Only new factorized model, training/export wrappers, tests and this document are
owned by this task. The five-tensor inference interface and existing runtime stay
unchanged. Acceptance: controlled development measurements, padding invariance,
and ONNX CPU parity. Competition integration remains a separate decision.

## Research and design

[Miwa and Bansal (ACL 2016)](https://aclanthology.org/P16-1105/) demonstrated joint
entity and relation learning with LSTMs. This experiment borrows the shared
representation idea, not their dependency-tree model or entity decoding method.
[Wang et al. (ACL 2018), LEAM](https://aclanthology.org/P18-1216/) studies explicit
label/text interactions in a small attention model. The present factorized heads
share subjects and attributes across valid pair classes; this is an adaptation,
not a reproduction of either paper's architecture or published scores.

The existing BiLSTM processes trailing padding in its backward recurrence. A
character CNN can also give padding a nonzero vector through its bias. The
[PyTorch packed-sequence API](https://docs.pytorch.org/docs/stable/generated/torch.nn.utils.rnn.pack_padded_sequence.html)
provides actual sequence lengths. We explicitly sort, pack, run the BiLSTM,
unpack and undo sorting, so current-row predictions do not depend on a longer
unrelated row in the same batch. Export parity verifies this behavior rather
than assuming that a successful ONNX export is sufficient.

## Controls

- `packed-flat`: same word/character dimensions, 128-wide one-layer BiLSTM,
  global candidate attention and flat head as the previous small BiLSTM. Changes
  are packed variable lengths and zeroing character vectors for padding.
- `factorized`: same packed encoder, separate attention to current versus
  preceding tokens, a learned context gate, an expanded pooled feature vector,
  separate shared subject and attribute logits plus a residual pair head, and a
  soft train-observed value-kind prior. These are a combined architecture change;
  improvements cannot be attributed to factorization alone.
- `factorized-large`: the same combined head with a 192-wide, two-layer encoder.
- `factorized-mentions`: the small factorized model with public lexicon aliases.
  Exact token matches reject shorter overlapping spans, including aliases whose
  start differs from the longest span. Three trainable soft features score
  candidate proximity to mentions in its clause, current row and previous text.
  They reallocate subject preference while preserving its log-partition mass.
  A named value's own token span is excluded from these subject features;
  Boolean whole-clause candidates retain all mentions.
  No alias is forced to be the subject, and stated values are never changed.

The public lexicon lists valid subject/attribute pairs but supplies no authoritative
unit or value-kind schema. A type absent from training therefore receives only
a finite logit penalty, never a hard ban. Boolean true/false share a kind prior.
This is not proof that predicted values or relationships are valid.

Initial controls use the unchanged `data-v2`, seed 271828, GloVe initialization,
AdamW at 0.001, batch 48, 40 maximum epochs, patience 8, and the equal mean of
official/synthetic development exact rates. No calibration or sealed gold is
used for training or model selection. Any enhanced-data runs are separate.

Remote artifacts live under `/data/tairo/veridyct-training-20261028/v3-factorized/`.
Only GPUs 0 and 1 are assigned to this worker. Run receipts record source hashes,
configuration, data metadata hash, hardware, epoch metrics and selected checkpoint.

## Commands

```sh
python -m unittest test_factorized.py
python train_factorized.py --data /path/data-v2 --out /new/run --variant factorized
python export_factorized.py --checkpoint /new/run/best.pt --data /path/data-v2 --out /new/bundle
```

The exporter writes the existing CPU runtime and ONNX bundle, checking variable
batch lengths including unsorted input rows. The regression test changes both
the number of padded tokens and unrelated batch contents.

## Completed unchanged-data controls

| Model, seed 271828 | Official exact | Synthetic exact | Official atomic F1 |
| --- | ---: | ---: | ---: |
| Previous un-packed small BiLSTM | 325 / 390 = 83.333% | 8040 / 8088 = 99.407% | 88.681% |
| Packed flat control | 322 / 390 = 82.564% | 8014 / 8088 = 99.085% | 88.199% |
| Factorized + gated context + soft kind prior | 339 / 390 = 86.923% | 8059 / 8088 = 99.641% | 91.228% |
| Previous selected three-model ensemble | 336 / 390 = 86.154% | 8077 / 8088 = 99.864% | 92.275% |

The new factorized model is 1,790,371 parameters and 7,204,867 bytes in ONNX,
versus 24,850,029 bytes for the previous ensemble. It improves official complete
rows by three versus that ensemble, but precision falls from 95.61% to 92.08%
while recall rises from 89.16% to 90.39%. This is a tradeoff, not an unconditional
quality win, and these are model-selection development results.

Factorized training completed 28 epochs, selected epoch 20, in 881.62 seconds.
Packed-flat selected epoch 12 and stopped after 20. Both CPU exports reproduce
all development metrics. Dynamic batches 1, 7 and 32 passed decoded parity;
maximum logit differences were below 0.000054. Prepared-input CPU evaluation on
8,478 rows took 7.43 seconds for factorized and 5.80 for packed-flat, using two
threads on the same server. These are not constrained-container timings.

A post-hoc consistency check on the prior frozen ensemble found two of 390
official predictions changed when each row was paired with an unrelated
99-token row. Complete-row accuracy was 336/390 alone versus 335/390 when padded.
The padding problem is real but small in this diagnostic; it does not explain
the overall domain gap. New packed models pass explicit padding invariance.

Enhanced-data small/large controls and the alias variant run separately on
`data-v3`; their results must be added only after completion. Calibration gold
remains reserved for the root agent's final independent evaluation.
