# Structured extraction research and continuous experiments, 29 October 2026

Task owner: root Codex, authorized by Teodor to research primary literature,
delegate agents, train on all eight A100 cards and continue experiments. Human
ownership unassigned. Base: `e0c2a12`; main laboratory branch remains
`teodorbalan/structured-extraction-training`. Rust/application interfaces unchanged.

## Parallel ownership

| Owner / isolated worktree | Paths | GPU allocation |
| --- | --- | --- |
| Root, structured-extraction-training | robustness data, R-Drop, shared comparison/export and this handoff | initially 4–7; later 7 |
| factorized, extraction-factorized-v3 | model/train/export_factorized, tests, alias variant | 0–1; later also 6 |
| graph, extraction-graph-v3 | model/train/export_graph, tests, graph variants | 2–3 |
| research_audit, extraction-audit-v3 | literature, independent audit/challenge, normalization, quantization and expanded-data control | initially CPU; later 4–5 |

Agents commit their own files; root cherry-picks completed commits. They do not
edit a shared checkout concurrently. All original V1/V2 models, datasets,
reports and GPU restoration inventory are preserved. Remote roots are separate
`v3-root`, `v3-factorized`, `v3-graph` and `v3-audit` below
`/data/tairo/veridyct-training-20261028`.

## Measured questions and predeclared evaluation

1. Does factorizing subject/attribute scores improve extraction beyond a
   padding-corrected control? Test soft type priors, context gates and later a
   separate explicit-alias variant. The lexicon has no authoritative unit schema.
2. Do label graphs improve over semantic labels without messages? Static graph
   scores can be folded exactly into a linear head; that is a training prior,
   not input-dependent graph reasoning. A separate candidate graph tests the latter.
3. Do independently authored distractors, context gaps and paraphrases improve
   the same baseline architecture? Preserve a data-only comparison and seeds.
4. Does R-Drop consistency improve the same encoder without extra inference cost?
5. Which failures are unavoidable under the current value-candidate parser?

Each training run selects its checkpoint using the existing equally weighted
official390/synthetic8088 development exact rates. Final cross-model ranking will
use official50%, synthetic25%, primary challenge-development25%, reported
separately as well. Compare singles and uniform top-2/3/4 ensembles, including the
previous V2 ensemble as a control. Tie-break toward fewer parameters. No diagnostic
abstention group is silently merged into official extraction accuracy.

The original protocol reserved `calibration-20000` and `external-calibration`
for this run. On reading updated main at `e6f687c`, we learned that another
team experiment had already evaluated and published these releases in
`docs/research/evaluation-suite-results.md`. They are therefore **not team-blind
tests**, even though this training run has not opened their gold. A separately
authored final challenge remains
withheld, SHA256 `966b5c7c5061eab4e24c61177eb3994b5e852dec3c955dff973bbd5bf7ff33a0`.
The previous sealed results are already known and cannot become a new blind test.
If experiments continue after a new final score is opened, a subsequent claim of
independent improvement requires another reserved test.

## Training-only robustness data

`prepare_robust.py` reads only immutable data-v2 and static GloVe. It preserves
the 32,862 original training examples and adds 9,993 numeric distractor examples,
5,472 value-preserving paraphrases, 868 intervening-context cases and 1,133
unrelated/unsupported-relation negatives: 50,328 total. Labels transfer by source
span and value, so identical numbers in unrelated sentences do not inherit a
label. Incomplete alignment candidates are rejected and counted.

Development remains 8,478 rows. Normalized full-text and parent overlap remain
zero. Vocabulary/characters expand from training additions only; pair ordering,
tokenization, candidate grammar and five model-input tensors are unchanged.
New dataset meta SHA256:
`237579c870cc02e2964dc59f536a469be6d419b0649d4f1ab70ce538e9527e04`.
It has 7,699 word IDs and 54 character IDs. Mixed-version ensembles must map
vocabulary IDs per member, rather than incorrectly sharing expanded token IDs.

Templates were authored with development-time assistant assistance. Typed values
are copied from training claims and are not factual evidence. Challenge examples,
calibration and sealed rows are excluded from augmentation. Unsupported-relation
negatives target the current closed lexicon, not a universal rule about English.

## Progress and evidence

See [research and dataset audit](../../labs/structured-extraction/RESEARCH-AUDIT-V3.md),
[factorized design](../../labs/structured-extraction/FACTORIZED.md), and
[graph design](../../labs/structured-extraction/GRAPH-EXPERIMENT.md).
These are active experiments; report final results only from completed receipts.
Preserve failed configurations and CPU limits, and distinguish selected-epoch
development scores from independent final evaluation and competition verdicts.

Teodor subsequently requested parallel training on more of the supplied data,
with particular care against overfitting. The expanded-data task may read all
26,000 rows from the two already authorized training worlds (20,000 synthetic,
6,000 diagnostic), not any calibration or sealed source. It must preserve the
390 official development rows and the whole synthetic development world. A
separate two-family exclusion control selects families by stable hash after
requiring at least 100 source rows per family; every derived training parent
must be removed as well. This is a structural diagnostic, not a fresh blind
test of the whole research process, which has already seen those styles.

## Semantic reverse engineering and paired million-row revision

The user's next priority is understanding the supplied semantics, rather than
adding architectures without a measured need. Root added a public-evidence
interval baseline; agents audited the official contracts, original practice and
the two allowed TRAIN archive worlds. See [observable semantics](../../labs/structured-extraction/OBSERVABLE-SEMANTICS.md),
[practice](../../labs/structured-extraction/PRACTICE-SEMANTICS-FORENSICS.md), and
[official contract interpretation](../../labs/structured-extraction/OFFICIAL-SEMANTICS-FORENSICS.md).

The user then requested the same analysis and a comparison for Downloads
`veridyct-million-v2.zip` against `veridyct-million.zip`. These are distinct from
evaluation-data-v3: two versions of a one-million-row, unsplit, synthetic
note-grounded development pool. Root owns `compare_million_data.py`, paired
evaluation and the Downloads report. Factorized owns schema/partition review;
graph owns independent delivery-check/oracle review; research_audit finishes
the expanded-data/family exclusion experiments. Existing jobs are preserved.

Compare matching IDs with the same frozen model. Do not conflate flat assertion
extraction with recursive `all`/`any`/`not`/`recorded`/`compare` programs. Gold AST,
source bindings, provenance metadata and audit recipes are never model inputs.
Related V1/V2 examples must share a partition; group separation alone does not
remove repeated source-fact exposure. A random-row split is not external validation.
