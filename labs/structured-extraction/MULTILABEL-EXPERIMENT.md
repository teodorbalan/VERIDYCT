# Shared-value multilabel experiment

Owner: `/root/graph`, delegated phase 4 on 2026-10-29. Human ownership unassigned.
Files: `prepare_multilabel.py`, `train_multilabel.py`, `runtime_multilabel.py`,
`export_multilabel.py`, `evaluate_multilabel.py`, `test_multilabel.py` and this
report. Existing baseline and Rust files are unchanged.

**Result: keep experimental; do not promote.** A sigmoid decoder removes the
single-label output ceiling and correctly extracts many coordinated assertions.
However, it regresses on ordinary official development rows and drops sharply
on new phrase families. This experiment does not justify a broad 99% claim.

## Contract and controlled scope

The existing typed candidate parser feeds a character CNN + one-layer BiLSTM128.
The five tensors and `[batch,candidates,515]` output shape remain familiar, but
the meaning of that output changes: indices 1–514 are independent sigmoid
subject/attribute probabilities. Index zero is ignored; NONE is the all-zero
target vector. One value candidate may produce two different pairs.

Metadata explicitly requires `decoder="multilabel_sigmoid"` and stores
`selected_threshold`. Use `MultiLabelCpuExtractor`; this checkpoint must not be
silently included in the parent's softmax ensemble. Predicted scores are
uncalibrated extraction scores. They are not truth probabilities.

The model initializes encoder tensors and overlapping vocabulary entries from
the completed semantic-v3 model. Its sigmoid classifier is freshly initialized;
no static graph head is imported. Training uses AdamW, learning rate .0008,
batch 48, positive BCE weight 32, all-zero candidate weight .25, gradient clipping
1, seed 271828, maximum 30 epochs and patience 7. Padding and ambiguous original
candidate targets are ignored. The current trainer is specific to 514 pairs.

## Training material and split

Only ordinary `data-v3/train.jsonl` supplies subject compatibility and stated
values. Two subjects must share a valid attribute and the same observed typed
signature (kind, unit, currency, period). There are 77 eligible signature groups.
Values are copied as *stated claims*, without claiming they are factual world
values. New coordination samples exclude booleans and inequality values; ordinary
training retains them. No gold world timeline or held-out expected value is used.

| Split | Ordinary rows | Shared, two-subject rows | Single-subject contrast rows | Irrelevant rows | Authored phrase families |
| --- | ---: | ---: | ---: | ---: | ---: |
| Train | 50,328 | 4,000 | 2,000 | 2,000 | 12 |
| Development | 8,478 | 400 | 200 | 200 | 8 |
| Reserved final | 0 | 400 | 200 | 200 | 8 |

All three sets use different authored phrase families. There is zero exact
normalized train/development text overlap. Many examples share the same 77
attribute signatures and finite vocabulary. This is a small structural stress
test, not hundreds of independent linguistic constructions. The final drop
demonstrates the limitation of that narrow template coverage.

Original positive targets are copied only at the identical original candidate
positions and canonical values. A repeated number in another clause never
receives labels merely because its value matches. For generated text, the one
literal value interval is recorded from its formatted prefix length, avoiding
accidental matches in subject names. An independent target audit reconstructs
all 8,000 training and 800 development coordination gold sets exactly. Train
vocabulary expansion excludes development/final text. Existing GloVe vectors
are preserved; new train tokens may use the same static GloVe archive.

The 800 final rows were generated and hashed before training; they were not
evaluated until the chosen model and threshold were frozen. Their SHA256 is
`7e1d92f99889b7fa58795f80f06d9d3690b79832fa2e259c2947f2b33fdff986`.
Phase-4 metadata SHA256 is
`8dd193e22e521b532156f139fd981a435af47bab02eb5f79ee4588058bad743c`.
These files are separate from the coordinator's reserved challenge and fresh
calibration datasets, which this experiment never reads.

## Selection and actual result

Epoch selection uses .5 official exact + .25 ordinary synthetic exact + .25
coordination-development exact, at threshold .5. After choosing the checkpoint,
the fixed grid [.25,.35,.5,.65,.8] selects the final threshold on development only.
The run completed 15 epochs in 854.06 seconds on GPU 3, an A100-SXM4-40GB. Best
epoch was 8 and selected threshold .5. Only this one warm-start training run was
performed. The proposed cold control was not launched after the user's priority
shift to archive semantics; no model-quality comparison to such a run is implied.

| Development slice | Semantic-v3 softmax | Selected sigmoid |
| --- | ---: | ---: |
| Ordinary official | 336 / 390 (86.15%) | 317 / 390 (81.28%) |
| Ordinary synthetic | 8,025 / 8,088 (99.22%) | 8,041 / 8,088 (99.42%) |
| Shared value, two subjects | 0 / 400 (0%) | 287 / 400 (71.75%) |
| Single-subject contrast | 179 / 200 (89.5%) | 171 / 200 (85.5%) |
| Irrelevant personal value | 33 / 200 (16.5%) | 73 / 200 (36.5%) |

The earlier three-member v2 softmax ensemble also scores 0/400 shared examples,
170/200 single and 100/200 irrelevant. The shared-value zero is structural: one
parsed value has only one subject/attribute class under that decoder. The
sigmoid improvement comes with different training and loss as well as a
different output contract; this experiment does not isolate those factors.

A genuine corrected development example is:

> Rheinhalle has the same capacity as Quayside Hall, namely 7979 seat.

The sigmoid model predicts both `Rheinhalle/capacity/7979 seat` and
`Quayside Hall/capacity/7979 seat` from the one value span, matching both gold
assertions. No second occurrence of the number is needed.

The frozen checkpoint SHA256 is
`6694a788fb5917d21907d108f02255f23e6f4a13c06362d66a87fa542eb88403`.
At `2026-10-29T00:23:34.934589+00:00`, `freeze.json` recorded that checkpoint,
ONNX hash, threshold .5, final-file hash and the decision not to promote. One
reserved-final evaluation then produced:

| Final phrase-family slice | Exact rows | Atom F1 |
| --- | ---: | ---: |
| All | 343 / 800 (42.875%) | .70446 |
| Shared value, two subjects | 181 / 400 (45.25%) | .79759 |
| Single-subject contrast | 41 / 200 (20.5%) | .52697 |
| Irrelevant personal value | 121 / 200 (60.5%) | Not meaningful: zero gold atoms |

There was no retraining, threshold change or selection using these final scores.
The single-subject contrast failure and irrelevant false positives show that
the model has not learned robust semantic ownership of every number. Positive
weight 32 and weak weighting of all-zero candidates are plausible contributors
to excess positives, but no ablation was run to establish causality. This
artifact remains separate from the ordinary extraction champion.

## CPU export and checks

The ONNX model contains 1,723,651 parameters and 6,903,218 bytes. Its SHA256 is
`0c798179c5dfcb2b2947e613d3cb1fe1782478edab29aef09dad39ab4a3c58fc`.
All 9,278 development inputs rebuild identically from raw text; Torch/ONNX decoded
outputs match at batch sizes 1, 7 and 32. Prepared-development inference takes
6.238 seconds with two ONNX CPU threads. The final 800-row run takes .986 seconds
including preprocessing, with peak RSS 103,428 KiB on an AMD EPYC 7742 host.
These are host measurements, not an official constrained Docker benchmark.

All 25 graph, multilabel, parser and archive-semantic unit tests pass in the
remote environment. The three multilabel tests specifically verify two pairs
from one candidate, all-zero NONE, and no copying across repeated-value clauses.

Artifacts live outside Git under
`/data/tairo/veridyct-training-20261028/v3-graph/phase4/`: immutable `data/`,
`runs/warm-s271828/`, frozen `bundle/`, `freeze.json`,
`coord-dev-softmax-baselines.json`, `data/target-audit.json`, and
`reserved-final-evaluation/`. The bundle includes runtime sources and a hash
manifest. No GPU job from this experiment remains active.

```sh
python prepare_multilabel.py --data /path/to/data-v3 --glove /path/to/glove.zip --out /new/phase4-data
python train_multilabel.py --data /new/phase4-data --warm /path/to/semantic-v3/best.pt --out /new/run
python export_multilabel.py --checkpoint /new/run/selected.pt --data /new/phase4-data --out /new/bundle
# Only after model and threshold freeze:
python evaluate_multilabel.py --bundle /new/bundle --rows /new/phase4-data/reserved-final.jsonl --out /new/final-evaluation
```
