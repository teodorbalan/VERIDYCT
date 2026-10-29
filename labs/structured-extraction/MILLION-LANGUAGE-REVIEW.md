# Million V1/V2: independent language and logical-scope review

Owner: research_audit; human ownership unassigned. Scope: deterministic selection,
assistant qualitative review, a logical counterexample, and interpretation of the
coordinator's paired measurements. No model, training set, organizer file or runtime
interface changed. No GPU job or final-challenge inference was run for this audit.

**V2 is a better candidate for controlled auxiliary training, but it is not a
million independent natural-English facts or a pure paraphrase of V1.** It removes
repeated context, often names the entity and attribute directly, and replaces some
artificial one-unit numeric substitutions with more plausible contrasts. Many
questions also change. Equal final labels do not establish equivalent meaning.

## What was reviewed

The [selector](select_million_language_review.py) freezes 24 pairs from the
coordinator's 10,020-ID matched sample, without consulting extractor predictions:
12 unchanged AST and 12 changed AST, three per negation, disjunction, omitted source
and false numeric/boolean-substitution stratum. Selection uses a stable SHA256 rank
and fixed stratum order; categories overlap before selection. The original sample
uses SHA256 of `paired-million-v1-v2:` plus ID, first 32 bits modulo 100 equal to zero.
The review's separate salt is `million-language-review-24-v1:`.

The [manifest](million-language-review-manifest.json) records every selected ID and
input hash. [Per-pair notes](million-language-review-notes.json) record all 24
assessments. This is a purposive assistant review, **not human adjudication or an
estimate of the corpus error rate**. There are eight true, twelve false and four
unsure query labels. All 90 distinct referenced practice sources in this small
sample happen to have true practice labels; false-source policies are therefore
outside the evidence supplied by this review.

Under each row's `provided_notes_only` policy and canonical attribute annotations,
no unequivocal new English-versus-own-AST mismatch was identified in these 24 pairs.
One inherited lexical-scope ambiguity warrants human review. This conditional
finding does not certify the remaining 999,976 rows or real-world truth.

The graph agent separately reports full deterministic replay passing for both
archives in `MILLION-VALIDATION-AUDIT.md`, integrated by coordinator commit
`509a95d` from agent commit `37300a4`. That is a different check: this audit did not
rerun the million-row referee or count its PASS as English understanding.

## Three distinct correctness questions

1. **Text to structure:** does the English actually express the annotated operators,
   values, entities, dates and reference bindings?
2. **Structure to label:** does evaluating that AST against the supplied notes yield
   its label under the declared three-valued policy?
3. **Truth in the target world:** are the source statements themselves established
   as true, at the relevant time, under the competition's evidence contract?

Passing question 2 does not establish questions 1 or 3. A `recorded` node concerns
what a specific note says. Provenance establishes where an assertion came from;
it does not independently establish its world truth. A false query can contain
several true clauses, and a true query can contain false or unknown clauses.

Omission also has a precise scope. `million-02-032398` cites a 2.9% phone-share note
that is absent from its evidence, alongside two contradicted alternatives. Its OR
result is unsure. Knowing the omitted value from practice is not licensed evidence
under `provided_notes_only`; a citation in the question is not the note itself.
Conversely, in `million-06-023130`, a missing note does not force unsure because a
known false conjunct already determines the result.

## A checked counterexample: identical label, different question

In `million-20-029637`, the relevant branches are:

| Version | Branch meaning |
| --- | --- |
| V1 | NOT(Maps offline storage > Gmail mailbox storage) |
| V2 | NOT(Maps offline storage = 4 GB OR Gmail mailbox storage = 11 GB) |

Both versions OR this branch with the same false conjunction. The supplied notes
say Maps 3 GB and Gmail 10 GB, so both full queries are true. If only the Maps note
instead says 4 GB, V1 remains true and V2 becomes false. Thus this is not a
meaning-preserving paraphrase, even though both original labels correctly match
their respective questions.

The [validator](validate_million_language_review.py) checks the actual annotated
branches and source values before evaluating this witness. The changed 4 GB note
is an assistant-created logical counterexample, **not a corpus modification or new
factual evidence**.

Among the 12 reviewed changed-AST pairs, eight replace comparisons, three change
numeric literals only, and one expands an observation pair into two dated recorded
clauses. One of the eight comparison replacements also changes a numeric literal.
Removing comparisons of unrelated quantities can improve a training curriculum;
it changes the task and must not be presented as a controlled language-only gain.

There is also a useful opposite example. In
`temporal-a27874f35315356b060f8ae1`, `observation_pair` becomes a conjunction of two
recorded market-share values at the same two dates. Under supplied-note semantics,
this preserves the proposition despite a different AST representation. AST
inequality alone is not proof of semantic inequality.

## Language limits and a lexical ambiguity

In `million-12-045963`, V2 says Gemini is hosted in the EU. Its omitted source
`p-516` says it keeps every customer's data inside the EU. The official annotation
maps that wording to `eu_hosted`, so this is not a demonstrated wrong V2 label.
However, data residency and hosting location are not universally interchangeable
English predicates. A human should confirm the intended ontology-level synonymy
before this pair is used as natural-language semantic gold.

In `million-15-024523`, source English says partner of Hooly while the inherited
canonical attribute is `integration_partner_of_flawless`. That naming mismatch
requires a learned or explicit surface-to-identifier mapping; it does not license
inventing a new entity or silently renaming the organizer's identifier.

The reviewed V2 text still contains parenthesized Boolean exercises, note-number
bindings, glossary-like attribute names and recurrent narrative asides. Explicit
parentheses make scope easier than ordinary conversational language. Many
distractors discuss kettles or napkins, which are easier to separate from the
ontology than another plausible product, price, negation or dated correction.
V2 is more readable, but these examples do not demonstrate coverage of arbitrary
paraphrases, implicit scope, discourse or domain-independent English.

## What the paired extractor results establish

The coordinator used the same frozen model and threshold on both versions; model
SHA256 is `14fccd0c69701cb090e80301e05ec5f10e4b506b2f0da56b0ccb97abe78d232e`.
The result scores only **flat literal-atom projection**, excluding operator scope,
source IDs, date bindings, ordering and multiplicity. A literal under NOT is still
scored as a literal, not as an independently positive factual assertion. Ninety
pairs without a literal projection in at least one version are excluded.

| Matched projection subset | V1 exact | V2 exact | V1 atom F1 | V2 atom F1 |
| --- | ---: | ---: | ---: | ---: |
| All 9,930 scoreable pairs | 847 / 9,930 (8.53%) | 1,976 / 9,930 (19.90%) | 0.4926 | 0.7526 |
| Same AST, 5,608 pairs | 411 / 5,608 (7.33%) | 1,091 / 5,608 (19.45%) | 0.4763 | 0.7453 |

For the same-AST subset, 904 pairs gain exactness and 224 lose it; 187 are correct
in both and 4,293 wrong in both. This is real evidence that V2 is easier for the
current flat extractor. It is not full-AST parsing accuracy or truth-label accuracy.
Even the separately reported plain-recorded-conjunction subset has only 131 versus
315 exact rows out of 1,512; simplification has not solved extraction generally.

Context truncation is a substantial confound. On the 10,020 matched inputs, the
coordinator counts 5,755 V1 contexts (57.44%) and 1,456 V2 contexts (14.53%) above
the model's 96-token context allowance. Its policy retains the last 96 context
tokens. Across the full million, mean context words fall from 93.81 to 47.94 and
mean claim words from 74.18 to 56.41. These word means are not encoder token counts.
The gain mixes clearer phrasing, changed context availability and, outside the
same-AST subset, changed questions. No controlled truncation ablation was run here
to apportion those effects. A zero count of total inputs over 384 tokens after
context truncation does not mean no context was lost.

## Corpus breadth and splitting risks

The coordinator's full corrected comparison, not the earlier metadata-only
grouping, reports:

| Full-corpus quantity | Count |
| --- | ---: |
| Paired rows | 1,000,000 |
| Input changed | 990,101 |
| AST changed | 445,023 |
| Final label changed | 0 |
| Complete source-reference set changed | 0 |
| Rows with references beyond metadata `source_ids` | 7,638 |
| Distinct practice source IDs | 1,897 |
| Source IDs shared between evidence-group train and test folds | 1,445 |

The 3,437 changed metadata `source_ids` lists change ordering, not source membership.
The 982,824 changed `source_documents` fields enrich metadata; they are not new
independent facts. More linguistic combinations of the same 1,897 source rows
can be useful training, but they do not provide a million independent observations.
Source grouping must collect references from context and target as well as metadata.

An after-the-fact majority label by generator profile reaches 73.51%, compared
with 49.34% for one global majority label. This is a descriptive shortcut warning,
not a held-out baseline or an available inference feature. Hidden profile and
source metadata must not become model inputs. Recurrent wording may nevertheless
make the corresponding shortcut learnable, so it merits a family-held-out check.

## How to use V2 for the competition

- Treat it as an auxiliary curriculum for typed values, explicit Boolean scope and
  missing-evidence reasoning. Keep the official atom/value schema and competition
  output contract separate from the million set's `recorded`/source-reference AST.
- Split source/document families and parent cases before producing variations;
  explicitly report when disjointness is infeasible or changes the data distribution.
  Use the complete reference graph and reserve template families too. Current
  evidence-group folds with 1,445 shared sources are not a source-independent test.
- Evaluate text-to-AST, AST-to-verdict and final task behavior separately. Preserve
  clause dates, source bindings, boolean values and unknown branches instead of
  training a flat list as if it represented the whole proposition.
- Add controlled minimal pairs that change one operator, one value, one antecedent
  or one available note, with a recomputed formal label. Keep genuine same-AST
  paraphrases separate from changed-question pairs; assess both positive and
  negative clauses, not only the aggregate row verdict.
- Use a human-reviewed natural-language subset for ontology synonyms and ambiguous
  scope. The assistant's 24-row audit and the already spent authored final challenge
  cannot certify future million-data variants.

## Reproduction and receipts

Remote root: `/data/tairo/veridyct-training-20261028`. Inputs:

- `v3-root/million-comparison-v1/sample-v1.jsonl` and `sample-v2.jsonl`;
- `v3-root/million-comparison-v2/comparison.json` for the corrected full comparison;
- `v3-root/million-comparison-v1/frozen-v3-projection/report.json` for flat projection;
- original practice copied unchanged into `v3-audit/million-language/practice.csv`.

Run the selector with `--sample-v1`, `--sample-v2`, `--practice` and a fresh `--out`.
Run the validator with `--selected`, `--manifest`, `--notes`, `--comparison`,
`--projection` and `--out`. Both use only the Python standard library. The selector
was replayed after correcting traversal of untyped observation-pair endpoints;
all IDs, stratum pool sizes and selected output bytes remained identical.

| Artifact | SHA256 |
| --- | --- |
| V1 archive | `17194179b1e17cca148ba42c21a7c155c5556423938d352e8bda90ac0b8f852c` |
| V2 archive | `416f95c6ab39a8b217e7aa1bad954b93134d75cb20f7f065c319cd71e4c3ecef` |
| Selected 24-pair JSONL | `f601454ca11e872ad007d38fe5ad5f82bc8a3b2ef5a7b9a25660155786318aec` |

The [validation receipt](million-language-review-receipt.json) records input hashes,
all stratum counts, source coverage, the logical witness and compact parent metrics.
Large sample/output files stay outside Git. Raw selected pairs are retained at
`v3-audit/million-language/review-v2/selected-pairs.jsonl`. The receipt's PASS checks
bookkeeping and the counterexample; it does not automatically validate the
assistant's English judgments. Acceptance checks also include Python compilation,
repository documentation/link checks and whitespace checks.
