# Million V1/V2 schema audit and bounded paired experiment

Owner: factorized worker, 2026-10-29. Scope: the two Downloads archives, read-only
schema/provenance inspection, conservative extraction-only preparation and the
coordinator-authorized matched training experiment. No organizer file changes.
Archive Python was read as text; none of its generator/checker modules was run.

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
3. Entire context fits 96 tokens and total input fits 384; no new example silently
   loses notes or bindings. All subject/attribute pairs are already in the lexicon.
4. No source anywhere in either view intersects the protected 390 official dev
   IDs or their contiguous-date provenance blocks.

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

Report original official exact/F1, synthetic exact/F1 and matched-case atom scores
separately. Partition V1/V2 diagnostics by unchanged AST, changed literals and
changed program where relevant: the full revision changes more than wording.
Report all admission reasons and type coverage; conservative filtering can remove
many date/Boolean and reference cases and make admitted data easier.

Three preparation tests pass: context/target source protection, rejection of
disjunction/scoped negation, and rejection of repeated note-date/value positions.
Full-pool preparation counts and training receipts are recorded in the worker's
remote `v3-factorized/million-paired-data-v1` subtree and will be appended after
the controlled run completes. No selected V3 artifact is overwritten.
