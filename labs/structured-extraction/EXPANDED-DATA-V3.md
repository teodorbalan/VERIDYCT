# Expanded supplied training data and family control

Owner: research_audit. Preparation is isolated in `v3-audit/expanded`, using
[prepare_expanded.py](prepare_expanded.py). The two GPU jobs use the existing
factorized architecture, seed 271828, batch 48, learning rate .001, at most 40
epochs and patience 8. GPU 4 runs expanded; GPU 5 runs family control.
[launch_expanded_runs.py](launch_expanded_runs.py) records the exact launches;
[finish_expanded_runs.py](finish_expanded_runs.py) exports only after completion
and evaluates the declared development data on CPU.

## Data protocol fixed before metrics

Only these archive gold inputs were opened for preparation:

- `evaluation-data/realistic-synthetic-20000`: 20,000 original rows.
- `evaluation-data/realistic-v1/diagnostic-6000`: 6,000 original rows.

The archive hash is checked against the existing pinned archive. Only original
asserted forms, assertion spans and provenance fields are selected as training
supervision. No `expected_value`, verdict, selected evidence, world identity or
gold antecedent pointer enters the five model input tensors. Newly added rows
use the preceding three **public CSV** rows as context, with the existing
96-context-token limit. Excluded dev/family rows are omitted from that fixed
window; a more distant row is not substituted.

All 50,328 base data-v3 training rows remain in expanded training. Matching
normalized development texts and development parent IDs are excluded before
additions. Deduplication retains the existing augmentation mix and adds each
new normalized original text at most once. It adds **4,962 original supplied
texts**, not newly generated assistant augmentation, for **55,290 train rows**.
Of 26,000 source rows, 20,037 were already represented/duplicates and 1,001
matched common development. No training row exceeded the supported length.

The common development set stays at 390 official + 8,088 synthetic examples.
All 19,397 official training rows and 1,133 base robustness negatives remain
in both conditions. Official held-out rows are never refitted. Vocabulary and
extra-name lists are derived from actual training rows only; static GloVe is
permitted, with no learned embeddings imported from another model.

## Held-out family diagnostic

Before looking at training metrics, eligibility was set to at least 100 original
rows per family. Eligible family counts are conversation 8,677, possessive
8,649 and recollection 8,605. The three external-title families contain only
26/26/17 rows and are ineligible for the primary family test.

Among eligible names, ascending SHA256 of `veridyct-family-holdout-v1:` followed
by the family name selects **conversation and recollection**. This selects
16,499 parent scenarios; including all rows with those parents blocks 18,106
original IDs, including cross-family derivatives. Every base synthetic parent
maps to an original source ID. Source ID closure removes all derived base
paraphrases, numeric replacements, distractions and context-gap variants from
those parents, not just raw source rows.

The control removes 20,451 base rows by parent lineage and 36 additional rows
whose known context antecedent belongs to that closure. Antecedent metadata is
used only to exclude contaminated training rows, never as an inference input.
It retains 29,841 base rows and adds 1,743 new originals = **31,584 train rows**.
The separate family diagnostic contains **13,523** unique held-out original
texts after removing duplicates and common-dev/train text overlap.

This is a harsh family generalization control: it largely trains on one large
family while testing two others, and also has fewer examples. It does not
isolate family diversity from sample size. Earlier v2/v3 experiments already
used these families, so the diagnostic is **not a fresh blind test**. Its score
is excluded from checkpoint selection; both runs use the unchanged common-dev
mean. The expanded model has training exposure to these families, so its score
on that diagnostic is descriptive rather than a comparable held-out result.

## Preparation receipts

| Condition | Train rows | Vocab | GloVe hits | Missing candidate gold values |
| --- | ---: | ---: | ---: | ---: |
| Expanded | 55,290 | 7,699 | 4,371 | 4 |
| Family control | 31,584 | 6,956 | 4,081 | 4 |

Four training gold atom values lack a grammar candidate in each condition; they
are counted, not replaced or labelled as factual corrections. Common dev and
family diagnostic have zero such missing values. Candidate alignment remains
partial supervision where necessary; the preparation reports 12 ignored
ambiguous candidates in each training condition. Raw forms are preserved.

Remote paths:

```text
v3-audit/expanded/data-v1/{expanded,family_control}
v3-audit/expanded/data-v1/protocol.json
v3-audit/expanded/launches.json
v3-audit/expanded/runs/{expanded,family_control}-s271828
v3-audit/expanded/bundles/{expanded,family_control}-s271828-v1
v3-audit/expanded/evaluations/{expanded,family_control}
```

Protocol SHA256:
`bb01f17d0e94a52774d130b40afc4915a5e2475c3c07e0e18057f318de4adc59`.
Expanded meta SHA256:
`be4e8abb019fcd29cd110e7e7a130833101fa5d41125d2ed9ed77d1c0c63cf13`.
Control meta SHA256:
`c97488b1498a2df7d3405d42d74f8516c98375eead06f858e0d84860a49e9fda`.

At this protocol commit both GPU jobs are running. Final checkpoint, CPU parity,
accuracy and family diagnostic results must be reported after their actual
completion; no claim of improvement is implied by adding more source rows.
