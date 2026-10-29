# Million V1/V2: measured paired comparison

Owner: root. These are the user's `veridyct-million.zip` and
`veridyct-million-v2.zip`, not revisions of evaluation-data-v3. Both contain one
million unsplit synthetic development rows. Source annotations are inherited;
human review is pending. No metadata, target AST or oracle proof enters inference.

[compare_million_data.py](compare_million_data.py) streams every matching ID,
checks row/target/provenance changes and emits identical sampled IDs for both
versions. The final audit includes source references from metadata, context and
target structures. Original ZIPs were not changed.

| Full paired audit | Count |
| --- | ---: |
| Rows | 1,000,000 |
| Duplicate IDs | 0 |
| Changed input | 990,101 |
| Changed target | 827,042 |
| Changed AST | 445,023 |
| Changed label / parsing status / case or evidence group | 0 |
| Changed source set, including context/target references | 0 |
| Extra sources omitted by metadata.source_ids | 7,638 |

The 3,437 source-ID list changes are order changes. Document metadata was added
to the 982,824-row extension; it does not introduce new source facts. Labels
remain 493,356 true, 434,083 false, 72,164 unsure and 397 null. Null belongs to
unresolved/no-claim parsing outcomes and is not a truth label.

Both complete delivery replays and the 24 executed generator/oracle/revision
tests passed. This does not mean every legacy test in the archives passed. See the
[independent validation audit](MILLION-VALIDATION-AUDIT.md). This checks exact
recipe/AST/oracle consistency, not arbitrary-English meaning. The
[24-pair language review](MILLION-LANGUAGE-REVIEW.md) includes an executable
counterexample: preserving a label on current notes need not preserve the
question's meaning under different notes.

The concurrent main-branch [full protocol evaluation at 22fa97b](https://github.com/teodorbalan/VERIDYCT/blob/22fa97b6fe27fcfa8d0bab7ae2e85c10c5386148/docs/research/million-v1-v2.md)
reports 99.5419% V1 and 99.7458% V2 truth accuracy using an explicitly adapted
renderer-language interpreter, frozen older extractor and typed note reasoning.
Strict transfer of its V1 grammar to V2 scores only 8.0827%. These are different
systems and metrics from the learned flat-extraction experiments below.
Its full error audit identifies 1,879 V2 note failures involving `api_version`
targets and unqualified `version` wording, including nine definitive wrong
answers. Our 24-pair review did not establish absence of such wider defects.
It also reports a legacy pilot volume test failure: 20,000 expected versus
17,176 delivered (12/13 legacy tests pass), outside our 24 executed tests.

## Frozen-model diagnostic

Sample IDs use SHA256(`paired-million-v1-v2:` + ID), first 32 bits modulo 100 = 0:
10,020 pairs, of which 9,930 have literal recorded/asserted atoms in both views.
[evaluate_million_projection.py](evaluate_million_projection.py) measures their
flat projection with the frozen selected V3 model. Each pair shares a padded
batch. Identical inputs produced identical predictions in all 94 such cases.

| Flat projection | V1 | V2 |
| --- | ---: | ---: |
| Exact /9,930 | 847 (8.53%) | 1,976 (19.90%) |
| Atomic F1 | .49256 | .75260 |
| Precision | .67477 | .78679 |
| Recall | .38783 | .72127 |
| Same AST exact /5,608 | 411 | 1,091 |
| Same AST atomic F1 | .47627 | .74533 |

Paired outcomes: 317 both correct, 1,659 V2 gains, 530 V2 losses, 7,424 both
wrong. The 4,322 changed-AST examples are changed tasks, not pure paraphrases.
The 94 retained annotated-practice rows score 80/94 in both views.

These are **not full AST or truth-label scores**. Logical scope, source/date
binding, order and multiplicity are unscored. The 90 non-projectable pairs are
not counted as correct. Practice source facts are already familiar to the
extractor. The same model has not been trained on this million-row pool.

Context truncation is a material confound: 5,755/10,020 V1 inputs exceed 96
context tokens versus 1,456 V2. Both retain the last 96 context tokens. Mean
context words shrink 93.81→47.94, claim words 74.18→56.41. The paired GPU
augmentation experiment therefore admits only cases whose complete context
fits this window and whose value ownership aligns uniquely in both versions.

## Overfitting and actual paired training

There are 255,012 cases but only 1,897 distinct original sources; the extension
uses 457 curated sources and 224 slots. Splitting by evidence-group hash still
shares 1,445 original sources between train and test. A profile/family-conditioned
majority baseline is 73.51%, compared with 49.34% globally; this uses forbidden
metadata and is a shortcut diagnostic, not a proposed deployed predictor.

An 80/10/10 source-hash split keeps 370,742 all-train, 581 all-dev and 771 all-test
rows; 627,906 span source partitions. To obtain a large source-disjoint synthetic
test, regenerate within partitions. A case-held-out result is not an independent
source or language generalization claim.

The actual GPU experiment protects all 390 official held-out source IDs across
metadata/context/targets, excludes normalized development texts/full inputs,
and preserves shared case/evidence grouping across V1/V2. It admits 20,729 matched
training pairs and 2,253 case-development pairs. The stronger document-block
audit admitted only 237/45 and is kept separately. No assumption was silently
weakened inside that strict audit. Read the full
[schema/training protocol](MILLION-SCHEMA-AUDIT.md) for constraints, failed startup
receipts, and matched base/V1/V2 runs. No full recursive-program training is claimed.

## Reproduction and viewer

Run the pair audit with `--v1`, `--v2`, `--out`; then the projection evaluator
with `--data` pointing to its output, `--bundle` and a fresh `--out` directory.
Reports and model files are immutable. The audit's sample includes target data
for evaluation only; it is not a learner input format.

[build_million_viewer.py](build_million_viewer.py) fills
[million_viewer.html](million_viewer.html), a template requiring generated data.
It selects 32 illustrative cases across four outcomes, not a representative
sample for estimating accuracy. The generated 238KB standalone HTML supports
search, AST/result filtering, context/JSON inspection, keyboard navigation and
fullscreen. It was opened and visually inspected in Orca; filtering and native
fullscreen were exercised. The delivered report, HTML, JSON receipts and compact
CPU build ZIP are in the user's Downloads comparison directory.
