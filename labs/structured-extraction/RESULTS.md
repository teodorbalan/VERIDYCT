# Structured extraction results — 29 October 2026

Six Orca terminals ran eight GPU jobs per round, for sixteen completed training
runs. The final choice is an equal-probability ensemble of two small char-CNN +
BiLSTMs (seeds 314159 and 271828) and one larger BiLSTM (seed 314159). GloVe 6B
100D initializes ordinary word embeddings. The system has no LLM decoder.

Scope: extracting the assertions stated in text, including their numeric values,
units, comparisons and named objects. These results do not measure truth verdicts,
evidence retrieval, claim generation or competition score.

## Selection and blind evaluation

Exact means equality of complete deduplicated subject–attribute–typed-value sets.
Numbers are normalized to nine decimal places. F1 is micro F1 over unique atoms.
Strict JSON comparison preserves numeric representation; it still compares sets,
not original array order or duplicate multiplicity.

| Dataset and role | Complete rows | Exact | Atomic F1 |
| --- | ---: | ---: | ---: |
| Official practice grouped development | 336 / 390 | 86.154% | 92.275% |
| Synthetic development world | 8,077 / 8,088 | 99.864% | 99.938% |
| Sealed-20000, final frozen model | 19,127 / 20,000 | 95.635% | 97.839% |
| Sealed target rows only | 17,310 / 18,103 | 95.620% | 97.861% |
| External-sealed, final frozen model | 483 / 500 | 96.600% | 98.140% |
| External-sealed target rows only | 317 / 334 | 94.910% | 97.495% |

The 390 official rows are development data used for model selection, not a final
blind test. The MMR synthetic development rows supply their explicit previous
row; official development and final evaluations use the actual previous three
public CSV rows. No gold context pointer is supplied in the final evaluation.

The selected model, parser, metadata and selection manifest were frozen at
2026-10-28 23:04:51 UTC, before sealed evaluation. There was no retraining,
threshold change, parser change or model reselection after seeing those results.
Sealed strict JSON exact is 19,099 / 20,000 (95.495%).

A post-evaluation overlap audit found 753 sealed texts also present in training
and 647 also present in development after text normalization. Excluding both
gives **17,729 / 18,600 = 95.317%** complete rows. External-sealed has zero train
overlaps and one development overlap: excluding it gives 482 / 499 = 96.593%.
Different worlds still share generator styles; these are not a guarantee for
arbitrary English or the competition's undisclosed inputs.

With context disabled, the same frozen model scores 18,836 / 20,000 = 94.180%
on sealed. The predeclared previous-three policy remains the primary result.

## Model comparisons

The first round trained on 11,748 synthetic rows. Its best synthetic score was
99.876%, but only 36.321% on all 1,897 official texts without context. On the exact
390-row official development split and context later used by round two, it scored
134 / 390 = 34.359%. The domain gap drove a second round with official training
parents, deterministic typed-value augmentation and training-world anchors.

The second round has 32,862 training rows and 8,478 development rows. Train and
development share zero normalized full texts and zero training parent IDs.
Numbers below are selected-epoch development scores, not blind test scores.

| Round-two configuration | Seed | Official exact | Synthetic exact | Training + evaluation |
| --- | ---: | ---: | ---: | ---: |
| CNN | 271828 | 73.59% | 97.66% | 624.7 s |
| Word BiLSTM | 271828 | 80.26% | 98.85% | 269.1 s |
| Char-CNN + BiLSTM | 271828 | 83.33% | 99.41% | 481.5 s |
| Char-CNN + BiLSTM | 314159 | 83.59% | 99.26% | 621.9 s |
| Larger char BiLSTM | 271828 | 80.51% | 98.43% | 331.6 s |
| Larger char BiLSTM | 314159 | 82.56% | 99.36% | 567.6 s |
| Char BiGRU | 271828 | 81.28% | 98.38% | 739.3 s |
| Small discriminative Transformer | 271828 | 73.59% | 96.33% | 642.2 s |

Uniform top-1/2/3/4 ensembles were ranked by the equal mean of official and
synthetic complete-row accuracy. Three members scored 86.15% / 99.86%; four
members scored 84.87% / 99.95%. The three-member model won the predeclared score.
Both seeds matter; a larger single model did not consistently outperform a small
one. Round-one Transformer collapse is retained in the numeric receipts; it is
a failed configuration, not evidence against the entire architecture family.

## Actual offline CPU container

Host: dual AMD EPYC 7742, x86-64. Training: NVIDIA A100-SXM4-40GB, PyTorch 2.8.0
CUDA 12.8, one job per GPU. Final inference: ONNX Runtime 1.23.2, two intra-op
threads, one inter-op thread, no CUDA or PyTorch dependency in the image.

| Measurement | Result |
| --- | ---: |
| Combined parameters | 6,204,041 |
| ONNX file | 24,850,029 bytes |
| Docker image, uncompressed | 360,077,493 bytes |
| Docker image archive, gzip | 139,008,082 bytes |
| Sealed rows, including preprocessing | 20,000 |
| Container wall time | 113.824 s |
| Evaluator time, including preprocessing | 111.522 s |
| Throughput | 179.34 rows/s |
| Peak process RSS | 748,712 KiB = 731.16 MiB |
| Output files | 16,794,030 bytes |

Container restrictions actually exercised: network disabled, root filesystem
read-only, UID 10001, 2-CPU quota, 6 GiB memory, all capabilities dropped,
no-new-privileges, 128 PIDs, 128 MiB tmpfs. Output size was measured below 256 MiB;
that mount had no filesystem quota. Exit code was zero. The entire competition
runner and official checker were not run with this experimental model.

Raw-text preprocessing exactly reproduced all 8,478 development inputs. ONNX
parity passed at dynamic batch sizes 1, 7 and 32, and all development set metrics
matched. The exporter's 16.55-second prepared-input benchmark excludes parsing
and does not replace the constrained container measurement.

## Errors and next work

There are 873 incorrect sealed rows. Weaknesses include ambiguous antecedents,
unseen paraphrases, missed percentages and attaching unrelated numeric clauses
to a lexicon attribute. For example, a sentence about a personal train ticket can
be incorrectly attached to Hooly Maps Day's ticket price. A separate smoke input
about AI Pro availability in 180 countries was incorrectly assigned to
`saved_projects`; the frozen model does not enforce attribute/unit consistency.

The measured next priorities are schema/type rejection, explicit resolution of
antecedents, out-of-domain negatives and wider natural paraphrase coverage. Extra
GPU capacity alone does not resolve missing context or noisy synthetic targets.
Any future tuning must use development data and reserve a new final blind test;
these sealed scores cannot be reused as fresh evidence after tuning to them.

For competition use, port or integrate the chosen inference path into the Rust
CPU system, connect it to evidence-based temporal verdicts, measure calibration,
verify 1,000-claim generation and run the unchanged official checker. The current
container is a working extraction laboratory, not a submission-ready solver.

## Artifacts and verification

Local artifacts: `artifacts/remote-results/` in the isolated training checkout.
`selected-v2/` contains ONNX, frozen preprocessing/runtime code, metadata, lexicon,
selection and export receipts. `delivery/` contains the tested Docker image and
a smaller build-context archive. Model binaries and row-level predictions stay
out of Git. Raw checkpoints, source snapshots and logs remain on BENGEE under
`/data/tairo/veridyct-training-20261028`.

- ONNX SHA256: `98eebdb851849f689c60499a9f4b2514305d520a523816b0505e98bba4523b6f`.
- Image ID: `sha256:d5dd72b8f4a21d31f7db85581611d9394993baf8b4104bf3032ececfe0b27943`.
- Image archive SHA256: `40f44b0786e708ca7178a4eee251b4a4bfd4fe9af430c3f13ebb9cab600d9024`.
- Selection SHA256: `327764212e412efd4e1fd7517305aa670441521888f3d227064e3f1f16e06341`.

Fourteen parser regression tests, Python compilation, `cargo xtask check` and
`cargo xtask test` passed; the latter ran 23 Rust tests. Local downloaded model
and delivery archive hashes match the server. GPU 0–7 were idle after completion.
Previously stopped services remain stopped; restoration instructions are in the
Desktop GPU snapshot and protected server operations directory.
