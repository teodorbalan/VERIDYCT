# Archive semantics: two training worlds

Owner: `/root/graph`, 2026-10-29. This read-only audit supports Teodor's request to
understand the supplied data before expanding the model stack. It changes no
training inputs, organizer files or inference behavior. Human ownership unassigned.

The audit independently reproduces **26,000/26,000 row labels and 34,039/34,039
atom labels**, with zero mismatch flags. This establishes internal annotation
consistency in these two worlds. It does not establish neural extraction accuracy,
real-world truth, or hidden competition behavior.

## Provenance and exact scope

Archive SHA256: `300623a5080ffb69eeb471e7069b88878f010059f73f002afee1995e00d99bc3`.
The script hard-codes these two previously declared training prefixes:

- `evaluation-data/realistic-v1/diagnostic-6000`
- `evaluation-data/realistic-synthetic-20000`

Within each prefix it reads only `public/universe.csv`, `gold/rows.jsonl`,
`gold/world.jsonl`, `gold/evidence.jsonl` and `manifest.json`. No calibration,
external-calibration, sealed, challenge-final or coordination-final file is read.
These worlds supply part of the existing extraction training set; they are not
independent evaluation sets. The audit covers their complete 6,000/20,000 rows,
not just the sampled extraction training rows.

Both manifests identify factory version `1.1.0`. Their explicit surface-profile
scope is **“Authored approximation plus elevated distractor stress, not a recovered
organizer generator.”** Their policy is exact values on half-open intervals,
explicit unknown cells and conjunction with false dominance. Every audited row
is marked `machine_validated_pending_human`. Thus this is a reconstruction of
this archive's semantics, not a claim to have reverse-engineered the organizers'
private generator. The diagnostic world has six external slots; the synthetic
world has zero. External material is transformed metadata/headlines, not an
untouched web corpus. Authored text and numeric worlds must not be treated as
official Hooly evidence outside their declared synthetic world.

World IDs: diagnostic `e082fa1d931e9897858a4b42`; synthetic
`88effeea4fbd6b1caccadd81`. The complete generated audit and individual member
hashes are preserved outside Git at
`/data/tairo/veridyct-training-20261028/v3-graph/archive-semantics-forensics.json`.

## Measured structure

| Property | Diagnostic | Synthetic |
| --- | ---: | ---: |
| Rows | 6,000 | 20,000 |
| Distinct subject/attribute pairs | 514 | 514 |
| True / false / unsure rows | 3,082 / 1,507 / 1,411 | 16,797 / 2,795 / 408 |
| Visible rows | 1,897 | 1,897 |
| Visible true / false / unsure | 1,715 / 139 / 43 | 1,709 / 152 / 36 |
| Hidden true / false / unsure | 1,367 / 1,368 / 1,368 | 15,088 / 2,643 / 372 |
| Known / unknown world intervals | 1,442 / 117 | 1,398 / 105 |
| Known intervals with visible true qualified anchor | 1,442 | 1,398 |
| Atoms | 9,483 | 24,556 |
| Equality / inequality atoms | 6,696 / 2,787 | 24,556 / 0 |
| Explicit cross-row context pointers | 120 | 953 |
| Rows containing both false and unsure atoms | 135 | 86 |
| Row verdict changes if evaluated at final date instead | 3,264 (54.4%) | 9,151 (45.755%) |

All scopes are exactly `{"operator":"and","children":[0,...,n-1]}`. There
are 1,193/3,876 multi-atom rows, including 361/10 rows with eight atoms. There is
no observed OR scope in either world. All eight typed value kinds are present.
Inequalities occur only in diagnostic; a high equality-heavy synthetic score
therefore does not establish good inequality handling. Synthetic labels are
83.985% true, which also makes aggregate verdict accuracy an incomplete metric.

The 34,039 atoms contain 2,086 explicit unknown-interval cases. An unknown cell
produces `unsure` even when the sentence is grammatically negative. A boolean
claim of `false` can itself receive label `true` if the stored boolean is false.

## Rules independently verified

For each atom, look up its subject/attribute interval at the **row's `date`**, with
`start <= date < end`. Known intervals compare the stored typed value against
the claimed threshold: e.g. a `ge` claim is true when `stored >= claimed`. The
audit checks kind, unit, currency and period, uses nine-decimal numeric
canonicalization, numeric version tuples for inequalities, and exact strings for
version equality. Unknown intervals yield `unsure`. Then combine atom verdicts:
any false gives false; otherwise any unsure gives unsure; otherwise true.

This recomputation uses world intervals rather than trusting `expected_value` or
the recorded atom label. All atom labels, intervals, expected values and row
labels agree. The evaluator additionally verifies:

- Parallel form/span/verdict arrays, exact UTF-8 byte spans, and no assertion
  overlap with annotated narrator distractors.
- Public and gold row text/date equality; public nonempty labels exactly match
  gold visibility and label. Visible does **not** mean true.
- Row evidence IDs equal the union of atom evidence IDs; all IDs exist and point
  to visible, true, same-pair/value anchors, dated no later than the query, whose
  qualifier covers the query date. Unknown atom verdicts have no evidence IDs.
- Evidence-file assertions and answerability equal their row-file counterparts.
- All 2,840 known intervals have visible, true, single-atom qualified anchors;
  the observed anchor key set has zero missing and zero extra intervals.
- Every context pointer exists, refers to the immediately preceding public row,
  shares its date, and has at least one common subject.

No flags fired. The evaluator reports unknown comparison semantics separately;
there were zero unimplemented comparisons. Four unit tests check conjunction
precedence, comparison direction and units, half-open boundaries/unknowns, and
typed version/boolean/date semantics without reading any archive.

## Concrete examples

The public inputs contain `id`, `text`, `date`, `label`. The following anchors
have public label `true` and can be used without consulting their gold form:

| World / ID / date | Exact public text | Gold interval, audit only |
| --- | --- | --- |
| Diagnostic, `r-4e52ef110e521bbeb7183c`, 2026-07-01 | From July 1, 2026 through October 29, 2026, Hooly Search has indexed 42,378,803,913 images. Anyway, someone behind me was still looking for a scarf. | `[2026-07-01, 2026-10-30)` |
| Diagnostic, `r-85a9edd31541365d2a5ba8`, 2026-02-01 | From February 1, 2026 through June 30, 2026, The price of Hooly Photos Max is €21.08 per month. My coffee alone cost €3, which annoyed me more than it should. | `[2026-02-01, 2026-07-01)` |
| Synthetic, `r-e6910e63850830e58e0229`, 2026-07-01 | From the 1st of July 2026 through the 29th of October 2026, Gwartt is the lead for Hooly Chrome. Anyway, my slice of pizza was getting cold by then. | `[2026-07-01, 2026-10-30)` |

The end day in “through June 30” is inclusive prose and therefore becomes July 1
as the exclusive internal boundary. Date prefixes are validity qualifiers, not
additional assertions. Narrator coffee prices and missed calls are distractors.

**False dominates unsure.** Synthetic `r-0911ab50b940e14d3fe89d`, 2025-11-07:
“Hooly Q2 2026 Results serves 1,868 customers, and Hooly Gemini has concurrent
chats of 4 chats.” The results customer count is unknown until 2026-07-30;
Gemini's stored chat count is 3. The atom labels are `[unsure,false]`, giving
row label false. Neither majority vote nor “any unknown means unsure” works.

**Unknown is not zero or false.** Diagnostic `r-0cd856e60178d735d0e823`, 2026-06-14:
“Hooly Maps lists 123,450,701 places.” That pair is explicitly unknown during
`[2026-02-01,2026-07-01)`, so the label is unsure even though the same number
can occur in another interval. There is no evidence ID for that atom.

**Context resolves identity, not truth.** Diagnostic
`r-aeabb4d370bfb4eba208a9`, 2026-06-03: “Its version is at least 0.11.6.” The
previous row `r-1ac90591543c7d31a9471b` supplies Hooly Maps; stored version
0.12.3 satisfies the threshold. Across diagnostic context rows there are 28
false-to-true and 24 true-to-false antecedent/current label transitions. Synthetic
has 115 false-to-true and 124 true-to-false. Copying the antecedent verdict is
incorrect. These worlds test only distance-one references, providing no evidence
of long-distance coreference performance.

**Answerability metadata is not itself an evidence filter.** All 1,442/1,398
`oracle_only` rows are the visible true interval anchors, with their own IDs as
evidence. Other known-value rows are `supported_by_visible_intervals`; unknowns
are `explicit_unknown`. Treating `oracle_only` as “no visible evidence” would
discard the complete temporal anchor system.

## Implications and separation of oracle fields

The useful pipeline is text-to-typed-assertions plus a separate validity-prefix
parser, visible true interval indexing, context resolution, typed temporal
comparison, and false-dominant conjunction. Extractor F1 alone does not validate
this pipeline. It must also abstain when evidence is unavailable instead of
turning unrelated numbers into claims. Date changes alone alter 12,415/26,000
labels in the final-date counterfactual, so using only the latest value is wrong.

`form`, `assertion_verdicts`, `expected_value`, `evidence_ids`, `scope`,
`context_row_id`, `validity_qualifier`, `answerability` and the world timeline are
gold audit fields. They must not enter inference features. Visible public labels
are available inputs; hidden row labels are not. Context and qualifiers must be
inferred from public order/text. A gold-form diagnostic may isolate solver errors
but must be reported separately from an end-to-end neural extraction run.

Roughly 35% of rows contain authored narrator distractors: diagnostic
1,062/3,082 true, 500/1,507 false, 482/1,411 unsure; synthetic 5,901/16,797 true,
987/2,795 false, 149/408 unsure. Their presence is not a verdict rule. Synthetic
data remains narrow in label balance, exclusively AND scopes, equality-heavy
comparison, authored lexical families and immediate context. Millions of rows
from those same families would not prove general language understanding.

## Reproduce

```sh
python forensic_archive.py --archive /path/to/veridyct-evaluation-data-v3.zip --out /new/audit.json
python -m unittest test_forensic_archive
```

The audit refuses an unexpected archive hash and refuses to overwrite an existing
report. It reads only the allowlisted members and writes a local diagnostic
report. Model training and runtime do not import this module.
