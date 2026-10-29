# Semantic label graph experiment

Owner: `/root/graph`, delegated by Teodor's authorized research/training task on
2026-10-29. Human ownership unassigned. Isolated branch
`teodorbalan/extraction-graph-v3`, base `e0c2a12`. Owned files:
`model_graph.py`, `train_graph.py`, `export_graph.py`, `test_graph.py` and this
report. Existing baseline code, organizer inputs and Rust interfaces are unchanged.

## Research rationale

[Pal et al. (2020)](https://arxiv.org/abs/2003.11644) use graph-derived label
classifiers with BiLSTM text features for multi-label classification. This
motivates testing shared label structure instead of independent output rows.
[Hu et al. (2019)](https://aclanthology.org/D19-1395/) combine structural and textual
label information for relation extraction. Their evidence concerns a different
dataset and supervision setup; the scores cannot be transferred to VERIDYCT.
[Qin et al. (2021)](https://aclanthology.org/2021.emnlp-main.228/) show another graph
construction strategy, using word n-grams without a dependency parser. We do not
implement their text graph or claim to replicate any of these papers.

The tested hypothesis is narrower: public subject/attribute names and schema
neighbors may regularize the candidate-to-label classifier. A fixed label graph
does not itself resolve antecedents, distinguish irrelevant clauses or verify
world facts. Broader language coverage still depends on training examples.

## Implementation and controls

Both variants reuse the original character CNN + single-layer bidirectional LSTM,
candidate/clause pooling, attention and 256-dimensional feature layer. They add
subject-name and attribute-name embeddings, initialized through the same GloVe
word table as the text. No pretrained language model is used.

`semantic-label` has zero message-passing layers. `graph-label` adds two gated
residual message-passing layers with separate normalized adjacency matrices for
equal-subject and equal-attribute pairs. NONE is isolated from both edge sets.
There are no edges based on gold outcomes, claim values, hidden worlds or
development labels. The existing direct classifier is retained; label-semantic
scores are added as a learned residual.

`candidate-graph` is a separate, genuinely input-dependent variant. Value
candidates are nodes, and overlapping clause masks provide permitted edges.
Learned query/key attention aggregates neighboring candidate features through a
gated residual update. It uses the semantic label head without static label
message passing. Unlike the static label graph, this changes the inference
function class and cannot be eliminated by folding classifier weights.

The first controlled runs use the identical prepared `data-v2`: 32,862 training
rows and the unchanged 390 official / 8,088 synthetic development rows. They use
the original optimizer, weighted loss, candidate decoding and selection metric
through `train.py`, without changing that file. GPU 2 runs the semantic ablation;
GPU 3 runs the graph variant. Both use seed 271828, batch 48, learning rate .001,
40 maximum epochs and early stopping patience 8. Architecture initialization
consumes different random draws, so identical seeds do not prove identical
minibatch trajectories or replace repeated-seed evidence.

The coordinator subsequently prepared `data-v3` with 50,328 training examples and
the unchanged 8,478 development examples. It adds training-only distractors,
paraphrases, context gaps and unsupported claims. The candidate graph and semantic
ablation are compared on this same expanded dataset, using the same hyperparameters.
No challenge or final-test examples enter training.

Calibration-20000 and external-calibration are reserved by the coordinator for a
new final test and are not read by this experiment. Previously scored sealed
sets are not used for training either. Development scores select checkpoints;
they are not blind accuracy estimates.

## Deployment

The interface is unchanged: `(words, chars, spans, clauses, kinds)` maps to
515 candidate logits. The label graph is static after training. Both graph and
direct scores are linear in the same candidate feature, so `fold_graph_head`
combines their weights exactly into one ordinary baseline linear head. This is
an algebraic transformation, not distillation or a second training process.
The deployed model consequently has the same parameter count and inference
operations as the corresponding baseline BiLSTM. Graph-only parameters and
adjacency matrices are absent from deployment.

That folding statement applies only to `semantic-label` and `graph-label`.
`candidate-graph` retains its input-dependent graph operations in the ONNX model.

`export_graph.py` verifies the fold against the trained graph on three development
batch shapes, then invokes the existing raw-text reconstruction and ONNX parity
checks. The frozen container runtime needs no graph-specific Python or Torch.

```sh
python train_graph.py --data /path/to/data-v2 --out /new/run --variant graph-label --pretrained
python export_graph.py --checkpoint /new/run/best.pt --data /path/to/data-v2 --out /new/bundle
```

Training inherits the baseline un-packed recurrent encoder deliberately for this
head ablation. It does not claim to fix that encoder's padding dependence. The
coordinator's separate factorized experiment investigates different encoder and
schema constraints.

## Validation and artifacts

Four graph tests verify label-edge isolation, differentiable message learning,
exact folding across different sequence shapes and independence from candidates
in disconnected clauses. These and all fourteen
existing parser tests pass in the dedicated remote environment.

Remote artifacts live only in `/data/tairo/veridyct-training-20261028/v3-graph/`.
`source/` is the first training launch snapshot; `export-source/` additionally
contains the initial deployment-fold helper; `source-v3/` freezes the candidate
graph and final export helper. Checkpoints and raw predictions remain outside Git.
All five runs completed. Checkpoint selection used the original equal mean of
official and synthetic complete-row exact rates, without challenge/final scores.
Training used the assigned A100-SXM4-40GB cards with Torch 2.8.0+cu128.

| Model / data / seed | Best epoch | Official exact / 390 | Synthetic exact / 8,088 | Total train seconds |
| --- | ---: | ---: | ---: | ---: |
| Semantic / v2 / 271828 | 12 | 325 (83.33%) | 8,043 (99.44%) | 368.86 |
| Static label graph / v2 / 271828 | 16 | 328 (84.10%) | 8,055 (99.59%) | 521.52 |
| Candidate graph / v3 / 271828 | 7 | 335 (85.90%) | 8,023 (99.20%) | 430.78 |
| Semantic / v3 / 271828 | 26 | 336 (86.15%) | 8,025 (99.22%) | 946.48 |
| Candidate graph / v3 / 314159 | 24 | 337 (86.41%) | 8,037 (99.37%) | 1,153.90 |

The original v2 character-BiLSTM at seed 271828 scored 325/390 and 8,040/8,088.
The static graph's official net improvement over the semantic control is only
three rows: 24 fixes versus 21 regressions (exploratory paired exact sign-test
p=.766). This is weak evidence for a graph-specific improvement. On matched v3
seed 271828, the candidate graph loses one official and two synthetic rows to
the semantic control. The second candidate seed is slightly better, but there
is no matching second semantic seed; it does not establish architectural
superiority. The improved v3 official results also change the training data, so
they cannot be attributed to the graph alone.

All five exports pass raw-input reconstruction for all 8,478 development rows
and Torch/ONNX decoded parity at batch sizes 1, 7 and 32. Frozen bundles include
the runtime source, metadata, lexicon and file hash manifest.

| Remote bundle under `v3-graph/bundles/` | Deployment parameters | ONNX bytes | CPU seconds / 8,478 prepared rows |
| --- | ---: | ---: | ---: |
| `semantic-v2` | 1,625,603 | 6,511,026 | 5.406 |
| `graph-v2` | 1,625,603 | 6,511,026 | 5.284 |
| `candidate-v3` | 2,044,549 | 8,299,336 | 5.686 |
| `semantic-v3` | 1,715,331 | 6,869,938 | 6.328 |
| `candidate-v3-s314159` | 2,044,549 | 8,299,336 | 5.752 |

CPU measurements use ONNX Runtime with two threads on an AMD EPYC 7742 host.
They exclude raw-text preprocessing and were taken on a shared server. Differences
of fractions of a second are not controlled latency wins. Export-process RSS
includes Torch and is not standalone runtime memory. No official constrained
container run is claimed by this experiment.

The best candidate replicate checkpoint SHA256 is
`429e34c57989ed3890ca1413ae148f74d058378a5a7e769855a9a5dcca649a2e`;
its ONNX SHA256 is
`414dccc13865c7ab002a97d971e5932e67c03b127cd7391edaef7c85b5b04d7d`.
Every run's `run.json`, `result.json`, `metrics.jsonl` and each bundle's
`export-report.json` preserve the other hashes, selected scores and timing.
The common v3 metadata SHA256 is
`237579c870cc02e2964dc59f536a469be6d419b0649d4f1ab70ce538e9527e04`.

The separate [multilabel experiment](MULTILABEL-EXPERIMENT.md) explores the
one-value/two-subject output ceiling and reports an unsuccessful final-family
generalization result. The [archive semantics audit](ARCHIVE-SEMANTICS-FORENSICS.md)
shows why temporal evidence handling is a separate problem from extraction.
