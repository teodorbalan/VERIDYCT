# Million V1/V2 schema audit and bounded paired experiment

Owner: factorized worker, 2026-10-29. Scope: the two Downloads archives, read-only
schema/provenance inspection, conservative extraction-only preparation and the
coordinator-authorized matched training experiment. No organizer file changes.
Archive Python was read as text; none of its generator/checker modules was run.

The completed matched experiment learns each archive's admitted templates almost
perfectly, but does not improve complete-row official DEV accuracy: base 331/390,
V1 augmentation 330/390, V2 augmentation 330/390. Cross-revision exactness is only
about 27%, including below 30% when the flat gold atoms are unchanged. These are
flat extraction development results, not full-program or truth-verification scores.
All three runs, CPU exports and six evaluation cells are complete; no selected V3
artifact was replaced.

## What the two archives actually contain

| Item | V1 | V2 |
| --- | --- | --- |
| File | `veridyct-million.zip` | `veridyct-million-v2.zip` |
| Archive bytes measured locally | 770,410,388 | 810,727,579 |
| ZIP members | 186 | 153 |
| Pool size, archive reports | 1,000,000 | 1,000,000 |
| Status | Unsplit, all train-eligible | Unsplit, all train-eligible |
| Large-tier schema | `provided_notes_logic_v1` | `provided_notes_logic_v2` |
| Source-preserving schema | `annotated_practice_v1` | `annotated_practice_v1` |

V1 combines 17,176 pilot examples and 982,824 compositional note queries. The
large tier reuses 457 curated practice rows, covering 51 subjects and 224 slots.
The pilot extends overall coverage to 62 subjects and 514 slots. These are one
million examples, not one million independently established facts. Both archives
retain pending human review; the V2 editorial review was by Codex, not Mihai.

V2's `dataset/report.json` records 990,101 changed inputs, 827,042 changed targets,
445,023 changed ASTs, and zero changed truth labels. It replaces 265,685 unsuitable
comparisons, changes 139,904 coarse numeric contrasts and repairs 69,606 name
substitutions; these change counts overlap. Mean claim length falls from 74.18 to
56.41 words and context turns from 8.74 to 5.03. Shorter does not establish better
extraction accuracy or greater natural-language realism.

There remain 255,012 underlying cases and up to four variants per new-tier case
(twenty for pilot cases). One atomic source appears in as many as 14,107 examples.
Case uniqueness therefore does not imply fact independence. Labels remain
493,356 true, 434,083 false, 72,164 unsure and 397 null. The null cases are twenty
`no_claim` and 377 `needs_context`, not additional unsure truth labels.

The reported profile/family label counts yield a 735,085/1,000,000 (73.5085%)
majority baseline if the generator profile/family is revealed. This is a diagnostic
of distribution imbalance, not a permitted model feature or an independent test
score. Metadata must remain excluded; template style can still provide shortcuts.

Authority for these reported whole-pool properties: each archive's `README.md`,
`dataset/report.json`, `labs/semantic-million/README.md`; V2 additionally
`labs/million-review/README.md` and `docs/handoffs/million-review-v2.md`.
Their reported independent replay is a producer result, not a replay performed
by this worker. Locally read members and their SHA-256 hashes are recorded under
ignored `artifacts/factorized-v3/million-audit/{v1,v2}/read-receipt.json`.

## Semantics differ from both competition tasks

The large-tier AST has five node forms, which are unrelated to the organizer's
five generated-entry families:

| Node | Dataset meaning | Required information |
| --- | --- | --- |
| `recorded` | Whether this supplied note records the claimed typed value | Source ID, subject, attribute, observation date, literal value |
| `compare` | Compare the values recorded by two supplied notes | Left/right source IDs and eq/lt/le/gt/ge |
| `all` | False if any child is false, otherwise unknown if any is unknown | Ordered/nested children and scope |
| `any` | True if any child is true, otherwise unknown if any is unknown | Ordered/nested children and scope |
| `not` | Swap true/false, preserve unknown | Child scope |

An absent required note gives an unknown leaf even if the same fact was memorized
from another training row. `any(true, unknown)` is true; `all(false, unknown)` is
false. An AST's literal value can be false; extraction must preserve it rather
than substitute the note's actual value. Source-preserving pilot examples instead
inherit whole-row practice labels, with no permission to label each atom in a
false compound as independently false.

The read-only code audit found these deliberate dataset choices:

- `oracle.py:109–126` requires originally true, exact singleton source annotations.
- `oracle.py:199–210` requires a recorded leaf's subject, attribute and date to
  match its registered source, and its value metadata to remain unchanged.
- `oracle.py:239–246` evaluates recorded values by exact typed-dictionary equality,
  with missing evidence checked first. It is not arbitrary world entailment or
  a general unit-normalizing equality operation.
- `oracle.py:161–179` converts compatible numeric comparisons, treats written
  version equality exactly, and preserves uncertainty for overlapping partial-date
  intervals. These are the dataset oracle's rules, not new organizer guarantees.
- `revision.py:142–161` replaces unsuitable comparisons with `all(true,true)` or
  `any(false,false)` leaves to preserve truth under every availability mask.
  Those replacements change the logical question, not only its wording.

All paths in this paragraph refer to archive members under
`labs/semantic-million/` or, for `revision.py`, `labs/million-review/`.
No note-date observation entails continuous world validity. These ASTs do not
implement the official historical `change`, event-time `at_event`, or temporal
two-hop `relation` operators.

## Concrete compatibility with the existing extractor

The factorized network accepts `words, chars, spans, clauses, kinds` and emits
one of 514 subject/attribute pairs or NONE for each literal candidate. Its
[runtime](runtime.py) takes one text and one previous-text string, retains the
last 96 context tokens and refuses a total above 384 tokens. It emits flat atoms;
`truth_verdict` is explicitly null.

It cannot represent recursive logical scope, source pointers, note availability,
comparison edges without literal values, separate observation dates, multiple
subject assignments for one shared value span, or parsing failure as a separate
status. Flattening all AST leaves would train positive assertions from negated
or alternative branches. A full-AST accuracy figure from that flattening would
be invalid. Gold `bindings`, `reference_links`, metadata and proof masks are
supervision/provenance, never inference input; supplied discourse text remains
legitimate input even when it explicitly names a binding.

The main repository has advanced to `e6f687c`. Its `typed.rs`, `temporal.rs` and
`knowledge.rs` already implement exact rational dimensions, explicit inclusive
validity qualifiers, provenance and negative constraints. The Rust-MVP assessment
in [the earlier forensics](OFFICIAL-SEMANTICS-FORENSICS.md) describes the worker's
historical base, not current main. Reusable typed arithmetic does not automatically
make the current solver an interpreter for this separate notes-only AST.

## Independently inspected sixty-pair sample

Read every paired record in V2 `dataset/review/before-after-60.jsonl`, checked all
IDs, case identities, label equality and reference character offsets, and inspected
their query/operator/context summaries plus representative complete targets.
This is the producer's stratified editorial sample, not a random quality estimate.
Its SHA-256 is `0c93ac74ab0192cf27b36c65a4e3c2e6d8fe4a3820f49de39b3a6eb7131033a8`.

- Forty-eight after-rows use notes-logic V2; twelve retain annotated-practice V1.
- Twenty-two ASTs changed; twelve inputs were unchanged.
- Eighteen logic rows withhold some evidence; thirteen rows contain reference links.
- Nine rows contain original practice context IDs outside `metadata.source_ids`.
  For example, `bundles-c33fbce51dad56ccd3580411` lists target sources p-914–p-919,
  but its context exposes p-909–p-913. Protecting only metadata sources leaks them.
- Three contexts exceed the existing 96-token context budget (tokenized text only).
- Reference-link fields differ: logic links use `mention` and `source_id`; the
  retained `references-3e7735ac72e1eed696613d50` link uses `text` and an explicit
  discourse-binding kind. Unicode character offsets require byte conversion in Rust.

Examples illustrating the representation issue:

1. `million-03-010560`: "Not all of these hold" wraps three recorded leaves;
   the launch-date leaf is false while the whole expression is true. Treating
   all three leaves as asserted true would invert its meaning.
2. `million-02-006199`: an OR contains two contradicted values and one missing
   note, so the whole query is unsure. Memorizing the absent practice note is
   prohibited by this row's `provided_notes_only` policy.
3. `million-01-000934`: the V1 launch date appears both as the note's observation
   date and as the claimed value. Matching by value alone cannot identify which
   text position owns the value; the V2 reference form avoids that duplication.
4. `comparisons-7e6277bf0d506be0c55fdd96` replaces a cross-product version comparison
   with two recorded-version statements. Equal labels do not make it a paraphrase.

A strict current-grammar alignment probe admitted zero of these sixty as a paired
conjunction-only training example: six had eligible ASTs on both sides, but all
six contained ambiguous literal positions in at least one version. This does not
estimate the eligible rate in the full million. Rejection is preferable to
inventing a span or leaf ownership. Machine-readable receipts remain in ignored
`sample-audit.json` and `alignment-probe.json` beside the read receipts.

## Split protocol and what its score can mean

Do not randomly split row IDs. Keep V1/V2 views and every variant of a case
together. Group by canonical evidence-source combination as well as case key;
distinct cases may reuse an evidence group. Check every source appearing anywhere
in metadata, input context, bindings, clauses and nested target references.

For a genuinely source-disjoint synthetic experiment, partition original source
documents before generating cases and use only combinations entirely inside one
partition. Existing 3–5-source combinations often cross partitions: a ten-percent
source holdout retains roughly `0.1^3` to `0.1^5` of randomly mixed combinations,
so a 10,000-row source-disjoint test cannot be promised. Keeping every connected
combination together can also collapse much of this small source bank into one
component. Regeneration inside partitions is the practical remedy.

The archives' `source_documents` are generator-defined contiguous blocks of equal
practice date (`revision.py:122–128`), not official page IDs. They are useful
conservative provenance groups, not proof of document reconstruction.

All original practice facts are already familiar to this team. Main's
`docs/research/evaluation-suite-results.md` at `e6f687c` also publishes earlier
archive calibration/sealed results. Neither the million pool nor that calibration
archive is a fresh team-blind final test. The separately authored final challenge
remains unread by this worker.

## Authorized bounded V1/V2 atom-only ablation

The coordinator approved a narrower experiment after this audit. It measures
whether V1 or V2 augmentation helps flat literal extraction; it does not claim
full AST parsing, notes-only truth accuracy, or independent source generalization.

[prepare_million_pair.py](prepare_million_pair.py) reads both complete pools as
data and checks paired IDs and unchanged labels. It admits a pair only when:

1. Both target structures contain only `recorded` leaves under `all` nodes and
   parsing is resolved. No `any`, `not`, `compare`, or implicit pilot conversion.
2. Every leaf's typed literal matches exactly one existing current-query candidate
   in each version, and no candidate serves two leaves. Unsupported/ambiguous
   values are rejected, never assigned by arbitrary occurrence order.
3. Entire supplied context text fits 96 tokens and total input fits 384; no new
   example truncates context text. Public context IDs/dates/roles are not serialized
   by this flat extractor, so this does not preserve every note binding. All
   subject/attribute pairs are already in the lexicon.
4. No source anywhere in either view intersects the protected 390 official dev
   IDs. The initial `--protection document` audit additionally excludes their
   contiguous-date provenance blocks. A separately named `--protection id-only`
   preparation retains neighboring blocks for the actual bounded ablation;
   this is explicitly not document-independent.
5. Neither view's normalized current text or full text/context input matches any
   of the original 8,478 development rows. A final scan checks the complete
   combined training set, including inherited base rows, for zero overlap.

The initial block-protected audit and the later ID-protected experiment are kept
in separate immutable directories. Block protection removed almost all candidate
combinations in the first audit. Moreover, the shared V3 base already contains
neighboring document rows, so stricter augmentation filtering alone could not
make the complete trained model document-blind. No score from the weaker policy
is attributed to the stronger one.

The admitted evidence combinations receive one deterministic 90/10 train/dev
assignment. Stable-ID hash sampling caps training at 50,000 matched pairs and
case development at 10,000, subject to availability. Whole groups cannot cross
folds; excluded variants are not recycled into training. Both views share a
training-only union vocabulary and identical GloVe initialization; base V3
training is unchanged. Metadata and truth labels are not network features.

The existing 8,478-row original development set remains unchanged for equal
official/synthetic early stopping. Paired-case evaluation is separate. The two
factorized runs use seed 271828, the same hyperparameters, at most twenty epochs
and patience five, on GPUs 0 and 1 after preparation checks pass. The older
forty-epoch base result is a reference, not an equal-budget causal control.
The optional `--order-by-id` training switch keeps the matched example order
identical before seeded shuffling; existing experiments retain their original
default of sorting training rows by length.

A third base-only control was then authorized on GPU 2. It has the same union
vocabulary, vector initialization, seed, architecture, row ordering and epoch/
patience limits, but only the original 50,328 training examples. The two augmented
views have 71,057 examples each. Optimizer steps, unpadded training tokens and wall
time are recorded; fewer base examples mean this is not an equal-compute comparison.
[evaluate_million_pair.py](evaluate_million_pair.py) compares every completed model
on both paired input views, separating easier test wording from improved training.

Report original official exact/F1, synthetic exact/F1 and matched-case atom scores
separately. Partition V1/V2 diagnostics by unchanged AST, changed literals and
changed program where relevant: the full revision changes more than wording.
Report all admission reasons and type coverage; conservative filtering can remove
many date/Boolean and reference cases and make admitted data easier.

The first complete block-protected pass rejected 532,241 pairs for protected
source IDs and another 460,486 for their provenance blocks. Schema/alignment
rejected 6,991 more, leaving 237 training and 45 case-development pairs. Eighty-four
eligible pairs have changed ASTs. These counts are exclusive first-rejection
counts, not all reasons that could fail inside one row. They belong to the strict
audit only and must not be used as the actual ID-protected training population.

The complete ID-protected pass instead admits **20,729 training pairs and 2,253
case-development pairs**, in 6,607 and 727 disjoint evidence combinations. It
rejects 532,241 protected-source pairs and 444,777 schema/alignment cases. Of the
22,982 admitted pairs, 7,100 have changed conjunction/literal ASTs. No sample cap
was reached. The vocabulary contains 7,888 words and 56 characters; both views have
identical vectors and metadata, with the base embedding prefix preserved exactly.
Normalized current-text/full-input/official-ID overlap with the 8,478 original
development examples is zero for both complete augmented training sets.

The internal case split has 329 distinct training sources and 328 development
sources, with **all 328 development sources also seen in augmentation training**.
It is emphatically not source-independent. Added atom counts are identical across
the two views: quantity 29,102; date 14,511; name 6,575; percent 6,439; money 5,829;
duration 5,319; version 5,294; **Boolean zero**. V1 adds 2,991,841 unpadded input
tokens per epoch and V2 2,180,952. The filtering therefore changes coverage and
compute substantially; it cannot establish improvement on all million examples.

Three preparation tests pass: context/target source protection, rejection of
disjunction/scoped negation, and rejection of repeated note-date/value positions.
Full-pool admission spools are preserved in the worker's remote
`v3-factorized/million-paired-data-v1` (initial strict audit) and
`v3-factorized/million-paired-idonly-v1` (ID-protected admission) subtrees. Final
training inputs and completed results are recorded below. No selected V3 artifact
is overwritten.
The strict count pass initially hit a 100-versus-128 embedding-width error during
matrix assembly. Its completed admission spool was preserved and finalized into
`million-paired-strict-final` with the established layout of 100 GloVe coordinates
plus 28 seeded coordinates. All existing base embedding rows remain unchanged;
the corrected finalizer records the cached admission hashes. Strict finalization
passes all normalized input/text/official-ID overlap checks with zero overlaps.
The final ID-protected data are in `million-paired-idonly-final`; the base control
is in `million-paired-base-control`. A first trainer startup used the newer optional
schema argument with the frozen two-argument encoder API and stopped before any
optimizer update. Both input views passed a forward smoke check after the trainer
was corrected. Only `million-factorized-{base,v1,v2}-s271828-r2` runs, all from
`source-million-training-v2`, are the actual controlled training experiment.

## Completed training and original development results

All runs use the same 1,904,339-parameter factorized model, static GloVe initialization,
seed 271828, AdamW learning rate 0.001, batch 48, weight decay 0.01, NONE-class
weight 0.25, gradient clipping 1, maximum 20 epochs and patience 5. Initialization,
metadata, vectors and source are frozen. Checkpoints maximize the equally weighted
official/synthetic exact rates on the unchanged 8,478-row development set. The
2,253 paired cases are not used for checkpoint selection. These are single-seed
runs without strictly deterministic CUDA enforcement; matching initialization is
not a measurement of seed variance.

| Training data | Official exact / 390 | Official atom F1 | Synthetic exact / 8,088 | Synthetic atom F1 | Best / completed epoch |
| --- | ---: | ---: | ---: | ---: | ---: |
| Matched base control | 331 (84.8718%) | 0.896266 | 8,072 (99.8022%) | 0.999012 | 9 / 14 |
| Base + V1 | 330 (84.6154%) | 0.896907 | 8,049 (99.5178%) | 0.996830 | 10 / 15 |
| Base + V2 | 330 (84.6154%) | 0.903826 | 8,037 (99.3694%) | 0.995925 | 17 / 20 |

V2 improves official atomic F1 by 0.7561 percentage points over this base control,
but has one fewer wholly correct row; V1 also has one fewer. Both regress on the
original synthetic exact score. One row on 390 selected development examples does
not establish a robust accuracy difference. The earlier 40-epoch V3 result of
340/390 has a different training policy and is only a historical reference.

| Training data | Optimizer steps | Unpadded training tokens | Fit plus DEV seconds |
| --- | ---: | ---: | ---: |
| Matched base control | 14,686 | 21,285,698 | 656.32 |
| Base + V1 | 22,215 | 67,683,720 | 1,357.48 |
| Base + V2 | 29,620 | 74,027,180 | 1,728.02 |

Training ran on A100 GPUs 2, 0 and 1 respectively, now released. Timings exclude
preparation and initial loading. The base has fewer examples, V1 has longer inputs,
and stopping epochs differ. No equal-compute or fixed-update advantage is claimed.

## Both input views for all three models

Every cell contains the same 2,253 case IDs, with 8,029 canonical gold atoms in each
view. Atom F1 is micro-averaged. Exact means equality of complete canonical flat
atom sets; strict JSON exact counts happen to agree in all six cells. Every row
has supplied context and multiple atoms. CPU runtime threshold is 0.5.

| Trained model | Evaluation view | Complete rows | Exact | Atom F1 |
| --- | --- | ---: | ---: | ---: |
| Base control | V1 | 104 / 2,253 | 4.6161% | 0.704365 |
| Base control | V2 | 453 / 2,253 | 20.1065% | 0.788162 |
| V1 augmented | V1 | 2,252 / 2,253 | 99.9556% | 0.999875 |
| V1 augmented | V2 | 608 / 2,253 | 26.9862% | 0.824291 |
| V2 augmented | V1 | 609 / 2,253 | 27.0306% | 0.779774 |
| V2 augmented | V2 | 2,248 / 2,253 | 99.7781% | 0.999377 |

Within each column, augmentation helps on these selected familiar-source
combinations. The diagonal also shows extremely strong template adaptation.
Cross-revision exactness remains low, so a near-perfect diagonal score is not
evidence of general language understanding. No inference of logical scope,
observation-date binding or truth labels is scored here.

The following paired transitions compare each augmented model with base on the
**same fixed input column**. A gain is a previously wrong complete row becoming
correct; a loss is the reverse. Both-wrong rows may still change atom F1.

| Input view | Model change | Both correct | Gains | Losses | Both wrong | Net correct |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| V1 | Base to V1 | 104 | 2,148 | 0 | 1 | +2,148 |
| V1 | Base to V2 | 73 | 536 | 31 | 1,613 | +505 |
| V2 | Base to V1 | 287 | 321 | 166 | 1,479 | +155 |
| V2 | Base to V2 | 453 | 1,795 | 0 | 5 | +1,795 |

## Unchanged versus changed flat targets

[aggregate_million_pair.py](aggregate_million_pair.py) only reads the saved six
prediction files and prepared gold. It does not load models or perform inference
or selection. It reproduces every original count before generating this breakdown.
Its canonicalizer is the original scoring function: subject, attribute and typed
value, with explicit equality normalized and numeric values rounded to nine places.

There are **1,574 pairs with identical canonical flat gold atom sets** and **679
with changed flat gold**. This is not an AST-equality split: observation dates,
bindings and conjunction structure are outside these flat sets. All comparisons
within a table column below retain the same gold for that input view.

| Trained model / input | Same flat gold: exact / 1,574 | Same atom F1 | Changed flat gold: exact / 679 | Changed atom F1 |
| --- | ---: | ---: | ---: | ---: |
| Base / V1 | 85 (5.4003%) | 0.728663 | 19 (2.7982%) | 0.651227 |
| Base / V2 | 343 (21.7916%) | 0.794092 | 110 (16.2003%) | 0.775482 |
| V1 trained / V1 | 1,573 (99.9365%) | 0.999817 | 679 (100%) | 1.000000 |
| V1 trained / V2 | 451 (28.6531%) | 0.828779 | 157 (23.1222%) | 0.814840 |
| V2 trained / V1 | 460 (29.2249%) | 0.809805 | 149 (21.9440%) | 0.714518 |
| V2 trained / V2 | 1,570 (99.7459%) | 0.999267 | 678 (99.8527%) | 0.999612 |

| Fixed input / model change | Same-target gains / losses | Changed-target gains / losses |
| --- | ---: | ---: |
| V1 / base to V1 | 1,488 / 0 | 660 / 0 |
| V1 / base to V2 | 404 / 29 | 132 / 2 |
| V2 / base to V1 | 232 / 124 | 89 / 42 |
| V2 / base to V2 | 1,227 / 0 | 568 / 0 |

Even with identical flat targets, the cross-revision models remain below 30%
exact. Conversely, the unchanged base improves from 85 to 343 correct cases when
evaluated on the V2 view of these 1,574 pairs. Thus changed literal targets cannot
explain all of the observed revision effect. Wording and supplied context also
change, so this is not a pure paraphrase experiment or a causal attribution to one
particular cleanup rule.

## Independent review and language limits

The [independent protocol review](https://github.com/teodorbalan/VERIDYCT/blob/da35a40/labs/structured-extraction/MILLION-EXPERIMENT-PROTOCOL-REVIEW.md)
reconstructed identical initial parameters, buffers and schemas for all three
runs, verified base-prefix preservation, train-only added vocabulary, source
protection, separate case groups, full supplied text retention and zero normalized
current-query/full-input overlap against original and paired development.
It found no concrete implementation defect invalidating this narrow comparison.

That review also found **12 official DEV query strings inside TRAIN context**:
741 base rows, 1,943 V1 rows and 1,981 V2 rows. Some are short public fragments,
such as `20 requests a day`. This is not evidence of protected source-ID or gold
label leakage, but rules out describing all development wording as wholly unseen.
The zero-overlap assertion means IDs, current-query equality and full-input
equality only. All 328 case-dev sources occur in augmentation training. Original
official/synthetic DEV selects checkpoints; case DEV is an internal holdout of
combinations of familiar source facts.

The [independent API-context audit](https://github.com/teodorbalan/VERIDYCT/blob/ffaf4f6/labs/structured-extraction/MILLION-API-CONTEXT-AUDIT.md)
verified all 253 training and 59 case-dev API rows against the raw V2 archive and
the actual prepared files. V1 explicitly names API/interface in every query;
V2 does so in none. This does not make all those targets wrong:

| Context for API-target row | Added TRAIN | Case DEV |
| --- | ---: | ---: |
| API note present, no competing product-version note | 229 | 52 |
| Both notes present on different dates | 10 | 4 |
| API note missing | 14 | 3 |
| Both notes present on the same date | 0 | 0 |

Most cases retain an explicit interface note and are context-resolvable. In the
14+3 missing-note cases, the prepared text does not explicitly identify the API
slot. The 10+4 cases with both notes lose the public date-to-note link because
preparation joins context text without IDs/dates/roles. These are representation
and wording limitations, not 253 measured corrupt labels or measured neural
failures. No admitted V2 full input has conflicting target atom sets, which still
does not prove every label is uniquely implied by its language. The current data
remain immutable; repairs require a separately versioned follow-up.

The separate [whole-million protocol evaluation](https://github.com/teodorbalan/VERIDYCT/blob/22fa97b6fe27fcfa8d0bab7ae2e85c10c5386148/docs/research/million-v1-v2.md)
reports 99.5419% V1 and 99.7458% V2 truth accuracy using a specialized notes adapter
with declared V2 grammar adaptation; strict old-protocol transfer to V2 is 8.0827%.
Those truth scores are not outcomes of this learned atom experiment and cannot be
combined with its diagonal extraction scores. Neither is an independent-source
or arbitrary-English competition guarantee.

## Completed artifacts and verification

Paths below are relative to `/data/tairo/veridyct-training-20261028/v3-factorized`.
Checkpoints, binary models, predictions and generated receipts remain outside Git.

| Artifact | Location |
| --- | --- |
| Final immutable paired training and case DEV | `million-paired-idonly-final/{v1,v2}` |
| Matched base data | `million-paired-base-control` |
| Actual frozen training code | `source-million-training-v2` |
| Three completed runs and per-epoch/compute receipts | `million-factorized-{base,v1,v2}-s271828-r2` |
| CPU models and original DEV predictions | `bundles/million-factorized-{base,v1,v2}-s271828-r2` |
| Six-cell metrics and saved predictions | `million-paired-cross-evaluation-r2` |
| Target-stratified paired gains/losses and input hashes | `million-paired-cross-evaluation-r2/paired-aggregation.json` |
| Detached workflow completion receipt | `million-postprocess-status.json` (`phase=complete`) |

All three ONNX models contain 7,660,739 bytes. CPU export checked decoded parity
on dynamic batches 1, 7 and 32; maximum observed logit differences were
3.8147e-5 (base), 4.5776e-5 (V1), and 5.3406e-5 (V2). CPU original-development
domain counts exactly match the reported CUDA checkpoint results. With two ORT
threads, the 8,478 prepared rows took 6.95, 6.72 and 7.00 seconds respectively;
these are shared-server observations, not isolated Docker latency benchmarks.

Model SHA256 values are base
`4ad729e50f67a9f1f0699bda9028d8027d5105381d9623452f34702bf1f8474b`, V1
`6ebabdc043b914c454b40ef428ab418468b9412722588532d72f5e6e388adaef`, and V2
`b053fa8ef5929785f832b6a019233c72731e3bcd967d6e5faabc31ca894819b9`.
Shared metadata SHA256 is
`7e936df11cea5ea08dec77bf2c29684f11a6cc85272b4ef1bbf29d2a589ea0af`;
shared vectors SHA256 is
`ca45cc8029ff78d3018069ddf2d4215bb0ec7050ab7ef262c9e1b9121a05bd4f`.
The aggregate audit records hashes of both gold inputs, all six prediction files,
the original six-cell report and the exact canonicalizer, and asserts all original
row/atom counts match. No new inference was performed for that breakdown.

The experiment demonstrates template learning and a modest official atom-F1
tradeoff, without improving official complete-row accuracy under this policy.
It provides no basis for promising 99% on arbitrary claims. Before increasing
synthetic volume, the measured weaknesses motivate retaining public note bindings,
representing program structure and evaluating transfer between language families.
The authored final challenge was not read or used by this worker.
