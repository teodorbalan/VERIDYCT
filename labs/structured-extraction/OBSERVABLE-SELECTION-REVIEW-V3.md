# Independent observable-evidence and stage-2 selection review

Owner: research_audit. Review-only work; no production source, training data,
model weights or selected stack were changed. No GPU jobs were launched.
Existing final predictions were aggregated only after explicit parent release
following model freeze; no new final inference was performed by this review.
The [exposure note](EVALUATION-EXPOSURE-V3.md) distinguishes this run's untouched
archive calibration files from the team's already published evaluations.

## Public evidence versus oracle forms

Reviewed `observable_semantics.py` SHA256
`f47430e449dd608085a801391db8a29e7f19b24e55811011929c8a9a1df58b0b`.
The neural-to-neural path uses public text, row date, known true labels and
preceding public rows. Neural extraction is completed before gold is opened.
Gold forms are explicitly routed through separately named oracle variants;
gold row labels supply confusion counts and error reports. The inference path
does not read `expected_value`, `assertion_verdicts`, private evidence pointers,
gold context pointers or hidden world identities.

[Five independent counterfactual tests](review_observable_isolation.py) passed
on this exact source. They use invented fixtures, not archive gold:

- Changing gold forms and labels changes oracle predictions and scoring, while
  both neural-to-neural prediction variants remain identical.
- Changing hidden expected values, verdicts, context pointers, world IDs and
  validity metadata changes no variant's predictions.
- An unlabelled row cannot enter the true evidence index or establish its own
  truth.
- A deliberately omitted false atom causes an incorrect true verdict. Perfect
  interval lookup does not compensate for partial extraction.
- The conflict policy is about incompatible predicate evaluations. Two distinct
  observations 5 and 6 make an equality-to-5 query unsure, but an equality-to-7
  query false because both observations reject it. The comment "conflicting
  evidence abstains" must not be read as rejecting every distinct-value group.

This supports source-level isolation for the reviewed implementation; it is not
a formal proof or a claim of arbitrary-language semantic correctness. Prefix
`From ... through ...` scope is assigned to every extracted atom in the row.
That fits the supplied anchor template but is not a general clause-scoping
parser. Unit conversion is explicitly unsupported and different date precision
abstains. Versions use numeric components for inequalities. Report these as
archive-specific assumptions, not a reproduction of the organizer's referee.

The forms-cache check originally bound model weights and public CSV bytes but
not metadata, lexicon, parser/runtime implementation or context policy. That
allows stale predictions if these change while the weights stay fixed. The
coordinator confirms that existing reused semantic predictions came from the
same frozen model, metadata, parser and context; only the truth policy changed.
There is no observed stale-cache defect in those runs. Stronger future cache
receipts remain appropriate, and the coordinator owns that source change.

## Frozen stage-2 comparison

Selection manifest SHA256:
`37aebc328073f5c8026aefb8f9e675cfafd971754b5e6135412ce0a311f8bf2b`.
Its selected top-3 combines factorized-v2, semantic-label-v3 and
factorized-mentions-v3. The selected totals are official 346/390, synthetic
8,083/8,088 and challenge DEV 90/92, using the robust monetary-period adapter.
The 5,385,804-parameter top-3 ties top-4's weighted exact score and correctly wins
the declared fewer-parameters tie break.

The [paired review](review_stack_selection.py) rechecked checkpoint hashes,
recomputed row exactness from gold/predicted typed atoms, verified the selected
option against the declared ranking, and joined selected/prior predictions by
row ID. Raw text, context and gold forms matched between those two comparisons.

| Development group | Both correct | New correct / old wrong | New wrong / old correct | Both wrong |
| --- | ---: | ---: | ---: | ---: |
| Official, 390 rows | 328 | 18 | 8 | 36 |
| Synthetic, 8,088 rows | 8,072 | 11 | 5 | 0 |
| Challenge DEV, 92 primary rows | 87 | 3 | 2 | 0 |

The new stack gains ten official, six synthetic and one challenge exact rows
net against the prior ensemble under the same adapter. It also regresses on
eight official rows. These are descriptive paired development results after
selection, not a fresh test of improvement.

All 20 member checkpoints have the same output-pair order, 384-token limit and
24-character limit. No member's extra name candidates are absent from the
master metadata. Word and character indices are remapped by token identity;
probabilities, rather than logits, are averaged. The robust adapter is checked
to preserve neural inputs, allowing the same cached probabilities to be used
with value-metadata normalization. No current mapping mismatch was found.

The probability-cache key originally bound checkpoint bytes and encoded inputs,
but not model implementation or master/member mapping metadata. An inference
code change can therefore invalidate that cache without changing its key.
The coordinator confirms stage 2's new master vocabulary forced new cache
files, and no model code changed between those cached runs. This review flags
a future reproducibility gap, not evidence that stage-2 scores are stale.

## Selection limits that should remain visible

There are 20 singles plus four ensemble options in this stage, after earlier
training and development choices. The official 390 and synthetic 8,088 rows
also selected training checkpoints. The final weighted score reuses those
examples and gives 25% to a small, repeatedly consulted behavioral challenge.
Thus selection score is a tuning objective, not independently calibrated
generalization accuracy.

One challenge row changes that objective about 2.12 times as much as one
official row. Repeated phrase families make the 92 challenge examples more
correlated than 92 unrelated documents. Keeping its ambiguity/type diagnostic
groups out of primary extraction accuracy is correct, but their exclusion does
not establish safe abstention. The new final challenge stayed withheld until
the stack, grammar and thresholds were fixed; the subsequent result is below.

Cached `seconds` fields include model loading, cached array access and scoring;
they are not full inference latency. Use the separate real CPU/Docker benchmarks
for runtime claims. Likewise, extraction exactness does not measure label truth
accuracy, semantic interval completeness or generated-claim validity. A fully
frozen end-to-end evaluation is still needed before claiming a competition
improvement. The old v3 calibration and external worlds are already team-exposed
and cannot supply a new blind confirmation.

## Post-freeze authored final comparison

After stage-2 selection was frozen, the parent evaluated selected-v3 and the
unchanged selected-v2 control in offline 2-CPU/6-GiB Docker. The initial control
attempt stopped on an import-path error before inference; the corrected run
and failed output were retained. This reviewer aggregated the resulting files
with [review_paired_final.py](review_paired_final.py), checking both fixture
hashes and the selected model hash. No final example was used to tune behavior.

| Frozen pipeline | Primary row exact | Atomic F1 |
| --- | ---: | ---: |
| Selected-v3 | 87/92 (94.57%) | 0.9700 |
| Old selected-v2 control | 76/92 (82.61%) | 0.9005 |

Paired primary results are 76 both correct, **11 gains, zero regressions**, and
five both wrong. Selected-v3 proposed all 102 gold value atoms as candidates,
so its remaining errors occur despite complete value-candidate coverage. This
is a comparison of complete
frozen pipelines: selected-v3 includes the robust value adapter and the old
control retains its original grammar. It does not isolate neural architecture
from grammar changes.

The ambiguity diagnostic has zero abstentions for selected-v3 and one for the
old control. The type diagnostic has zero for both; these deliberately separate
groups do not count toward primary extraction accuracy or define a universal
rule for rejecting unusual attribute/unit combinations.

This narrow, correlated suite supplies one post-selection behavioral check,
not a 94.57% guarantee on arbitrary competition prose. It is now spent and must
not validate further tuned models or new million-data variants as if fresh.
The [paired final receipt](final-paired-review-v3.json) contains aggregate metrics
and hashes only, without final text, forms or error examples.

Receipts: [observable isolation](observable-isolation-review-v3.json) and
[stage-2 paired checks](stack-selection-review-v3.json). The final fixture,
builder and gold forms are absent from all review artifacts.
