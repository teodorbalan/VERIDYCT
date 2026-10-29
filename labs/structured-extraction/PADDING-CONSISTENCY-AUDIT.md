# Frozen selected-v3 padding consistency

Owner: `/root/graph`, 2026-10-29. Human ownership unassigned. Scope is read-only
evaluation of the 390 official development examples. No authored final,
calibration or external final examples are read; no frozen model/runtime changes
are made. The executable audit is `audit_padding_consistency.py`.

**Decoded predictions are identical on these 390 examples across all three
batch policies. Confidence scores are not padding invariant.** Every policy
scores 346/390 complete rows (88.7179%), with 459 predicted atoms, 446 correct
atoms out of 489 gold, and atom F1 .94092827. Atom sets and selected value spans
have zero differences, so exact-score differences are also zero.

## Protocol

Frozen bundle: `/data/tairo/veridyct-training-20261028/v3-root/bundles/selected-v3`.
Model SHA256:
`14fccd0c69701cb090e80301e05ec5f10e4b506b2f0da56b0ccb97abe78d232e`.
Runtime SHA256:
`ed3f900ecca33998b7ec931885f469c8279f1e065469238e808b341f83b9eb1b`.
The ensemble contains two packed factorized members and one legacy semantic-label
BiLSTM member. This audit does not separately ablate their contributions.

Only rows marked `domain="official"` in `data-v3/dev.jsonl` are selected.
Predictions are rebuilt from their `text` and `previous_text` using the actual
frozen runtime, metadata, parser and vocabulary. No prepared candidate labels or
gold forms enter the encoded input. Gold is used only for aggregate exact/F1
scores; per-row examples below show prediction confidence, not gold judgments.
The data-file SHA256 is
`fa69eab0327110e066b7c386f3dae84539df6cb43c07aae022094fd10e52da2e`.
The stripped ID/text/context input SHA256 is
`36b3ee032c2ba19e9a4ff764038b2d4419f0507c2a539a13cffa8c814acf20b4`.

Policies are singleton inference, stable token-length sorting with batches capped
at 48, and exact-token-length grouping with batches capped at 48. The latter
has no token padding. All plans use the same 390 rows. Their encoded lengths
range from 16 to 99 across 69 distinct lengths. The sorted plan pads 356 rows
by a total of 1,738 extra tokens. This is an official-only sorted schedule,
not a reconstruction of the historical mixed 8,570-row selection schedule.

The initial measurement found confidence differences. A second run added
development IDs and detailed score examples to the receipt. Both runs reproduce
the identical discrete predictions and confidence-difference counts; no model,
threshold, policy or input changed between them. The second run is reported
below. SHA256 of canonical predictions for every policy is
`2f65b79cf4d71d0210a65986576a226847e8908dfb5fb9c63c0e8a2d950eb9fb`.

## Measured differences and cost

| Comparison | Different atom sets | Different atoms/spans | Rows with matched-atom score change > 1e-5 | Largest matched-atom score change |
| --- | ---: | ---: | ---: | ---: |
| Singleton vs sorted48 | 0 | 0 | 92 | .08141279 |
| Singleton vs exact-length48 | 0 | 0 | 0 | .000000298 |
| Sorted48 vs exact-length48 | 0 | 0 | 92 | .08141279 |

Scores are the frozen decoder's uncalibrated extraction probabilities. These
statistics compare emitted matching atoms; they are not a bound on every
candidate/class logit. The existing .5 decode threshold is unchanged.

| Policy | Batches | Exact rows | Prediction wall seconds | Process CPU seconds |
| --- | ---: | ---: | ---: | ---: |
| Singleton | 390 | 346 | 2.6780 | 5.3535 |
| Sorted48, official only | 9 | 346 | 1.4028 | 2.8063 |
| Exact-length48 | 69 | 346 | 1.3292 | 2.6562 |

Measurements use ONNX Runtime 1.23.2 with CPUExecutionProvider, two intra-op
threads and one inter-op thread on the shared AMD EPYC 7742 server. Model
initialization, text encoding and one shared warm-up are outside policy timing;
the receipt records their separate times. Peak process RSS is 170,716 KiB.
These are small development-set host measurements, not a constrained-container
throughput benchmark. The first run's times were 2.7430/1.4933/1.2018 seconds,
showing the size of ordinary host timing variation.

Selected development confidence examples:

| ID | Emitted pair/value | Singleton score | Sorted48 score | Token width, singleton to sorted |
| --- | --- | ---: | ---: | ---: |
| `p-705` | Hooly Calendar / max_guests / 1,000 guests | .5835363 | .5021235 | 20 to 28 |
| `p-411` | Hooly Workspace / storage_per_user / 100 GB | .9085985 | .8462591 | 27 to 28 |
| `p-816` | Hooly Board / independent_members / 3 members | .8615691 | .9007110 | 27 to 28 |
| `p-297` | Hooly Maps / offline_maps / false | .6938213 | .7267160 | 30 to 36 |
| `p-343` | Hooly Android / active_devices / 2,900,000,000 devices | .8171006 | .8400629 | 20 to 28 |

`p-705` remains above .5 here but is close to the threshold in the padded batch.
No claim is made that other inputs or different padding widths preserve decoded
outputs. Exact-length batching matches singleton confidences to floating-point
tolerance on this set. This observation is consistent with the known legacy
unpacked bidirectional encoder concern; it does not itself prove which member
causes each score change.

## Deployment policy and limits

Keep the frozen artifact and all previously recorded final results unchanged.
The existing one-request `extract()` API uses singleton inference and defines
the stable online reference behavior. Treat arbitrary mixed-length batching
as a different execution policy: neither scores nor thresholded outputs are
guaranteed invariant. Do not describe `.model_score` as calibrated truth
confidence or assume a downstream score threshold is independent of padding.

For a future declared batched serving policy, exact-token-length grouping avoids
token padding and matches singleton behavior in this development audit. It may
be adopted only as an explicitly versioned execution policy with its own
validation; this task does not change the default. Keep historical metrics
attached to their actual batch schedule rather than silently regenerating a
frozen final result under another schedule. Longer inputs, other examples and
downstream score consumers are outside the measured guarantee.

Earlier Torch/ONNX parity checks compare both backends on the **same** padded
shape. They do not prove consistency when the amount of padding changes.

## Reproduce and receipts

```sh
python -B audit_padding_consistency.py \
  --bundle /data/tairo/veridyct-training-20261028/v3-root/bundles/selected-v3 \
  --dev /data/tairo/veridyct-training-20261028/data-v3/dev.jsonl \
  --out /new/padding-audit
```

The script refuses existing output directories and output inside the frozen
bundle. It suppresses import bytecode writes, verifies that it imported the
bundle's own runtime, checks 390 unique official IDs and absence of gold in
encoded inputs, and confirms model/parser/runtime hashes remain unchanged.
The real audit ran successfully twice; no unrelated model tests or final-set
evaluations were rerun.

Immutable receipts and all 92 confidence-difference IDs are outside Git at
`/data/tairo/veridyct-training-20261028/v3-graph/padding-consistency-v1/results-with-ids/report.json`.
The first receipt remains at `results/report.json`. Runtime and source hashes,
provider configuration, score examples, timings and input hashes are included.
No GPU was used and no audit process remains running.
