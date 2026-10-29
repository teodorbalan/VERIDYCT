# API-version wording in the admitted paired data

Owner: `/root/graph`, 2026-10-29. Human ownership unassigned. Read-only audit of
`v3-factorized/million-paired-idonly-final`; no data, model or running experiment
is changed. No final challenge is read. Code: `audit_million_api_context.py`.

**V2 removes the API qualifier from all 253 admitted training API examples,
but that does not make all 253 targets wrong.** Most retain a usable interface
note in context. A smaller subset loses information needed to distinguish the
API from the product version.

The motivation is the 1,879 specialized-protocol errors documented in
`docs/research/million-v1-v2.md` at main `22fa97b`. That is a different full-pool
evaluation. Its example `million-13-022926`, containing same-date API/product
notes, is **not admitted** to this training/case-dev set. Those 1,879 errors
must not be counted as errors in the current augmentation.

## Actual admitted counts

The audit checks every selected ID against both actual prepared `train.jsonl`
and `paired-dev.jsonl`: query text, previous text and target atom sets all match
the admission spool. All 312 API rows additionally match their original V2
pool input/context/AST. Only those selected API rows are deserialized during
the raw pool scan; no model is run.

| Per view, identical counts in V1/V2 | TRAIN | Internal case-dev |
| --- | ---: | ---: |
| Admitted paired rows | 20,729 | 2,253 |
| Aligned target atoms | 73,069 | 8,029 |
| `api_version` rows / atoms | 253 / 253 | 59 / 59 |
| Ordinary `version` rows / atoms | 4,098 / 4,372 | 465 / 484 |
| API queries explicitly saying API/interface, V1 | 253 | 59 |
| API queries explicitly saying API/interface, V2 | 0 | 0 |
| API rows retaining API/interface in context, either view | 239 | 56 |

API rows are 1.22% of the admitted training additions and 2.62% of case-dev.
Every API atom concerns Hooly Gemini and derives from just two observations:
`p-1454` (2025-11-14, interface version 1) and `p-1466` (2026-08-20, interface
version 2). Their train exposures are 116/137 and case-dev exposures 26/33.
These are repeated combinations, not 312 independent source facts; case-dev
shares these source observations with train.

## What the supplied context resolves

The categories below use the original V2 context IDs/dates and independently
verified source annotations. They are mutually exclusive.

| API row category | TRAIN | Case-dev |
| --- | ---: | ---: |
| Matching API note present; no product-version note for Gemini | 229 | 52 |
| API and product-version notes present, on different source dates | 10 | 4 |
| API note missing from supplied context | 14 | 3 |
| API and product-version notes present on the same source date | 0 | 0 |

The 229/52 API-only cases have a direct contextual route to the intended
attribute despite the unqualified query. Among the 14 missing-note train
cases, one supplies a Gemini product-version note instead; the other 13 have
neither Gemini version note. All 17 missing-note rows across both folds lack
API/interface wording in both query and actual previous text. The target still
specifies `api_version` from its generation recipe, but the visible wording
does not explicitly identify that slot. Missing evidence can make truth unsure;
it does not magically supply the missing parsing distinction.

In the complete raw protocol, subject plus note date uniquely selects the API
source in all 239/56 cases where it is supplied. There are **zero same-date
competing product notes** in the admitted subset. However, preparation makes
`previous_text` by joining only `context[*].text`: it discards each context
item's ID, date and role. Thus the 10/4 cases containing both version types lose
the structured date-to-note link that would disambiguate them in the raw
protocol. The query still names dates, but the two source texts are no longer
date-tagged. This is distinct from token truncation: admission already limits
the complete previous text to 96 tokens.

Across all 22,982 admitted V2 pairs, no identical full `(query, previous_text)`
input has conflicting target atom sets. That absence of literal collisions
does not prove each target is uniquely implied by its language. The concern is
underspecified attribute ownership, not duplicate rows carrying opposite gold.

## Three TRAIN-only examples

- `million-01-000313`: V1 explicitly names Gemini's **api version**. V2 says
  “Hooly Gemini runs version 2, as reported on 20 August 2026.” Its actual previous
  text includes “Hooly Gemini speaks version 2 of the interface.” No competing
  Gemini product-version note is supplied. This is context-resolvable; removing
  “API” from the query alone does not justify declaring its label incorrect.
- `million-01-005783`: V2 says “From the note dated 20 August 2026: Hooly Gemini
  runs version 3.” The context contains only Jules notes and an unrelated aside;
  the Gemini API note is withheld. Target is still `api_version="3"`. V1 names
  the API explicitly, so its parsing target remains distinguishable even when
  the truth evidence is missing. V2 requires an unsupported slot inference.
- `million-01-009390`: V2 names Gemini version 2.3 on 25 August 2026 and version
  2 on 14 November 2025. Raw evidence has `p-35` on the former date (“Suggestions
  in Hooly Docs come from Hooly Gemini 2.2.”) and `p-1454` on the latter (“Hooly
  Gemini speaks version 1 of the interface.”). The prepared previous text keeps
  both sentences but drops their date fields. V1 separately names `version`
  and `api version`, so it does not depend on that discarded distinction.

## Cause, limits and consequence

The archived V2 renderer explicitly handles `cli_version` and `stable_version`
but renders the other version kinds through the generic “is on/runs version”
patterns. The specialized adapter at `22fa97b` then suppresses an `api_version`
proposal when the subject also has `version`. This is a documented parser
choice; its resulting full-pool errors are not proof that every omitted-API
example is semantically defective. A context-aware parser can recover many.

The paired admission code verifies conjunction-only scope and unique typed
literal positions. It does **not** verify that the surface and retained context
uniquely identify the target attribute. The 14 missing-context train cases and
10 cases with discarded date links deserve focused future review; they are
not 24 measured neural failures, and no causal augmentation damage is measured
by this data-only audit. Do not infer a rule such as integer versions mean API
and dotted versions mean product.

A future version can retain explicit “API/interface version” wording and/or
preserve publicly supplied note dates in text. Keep the current V1/V2 training
runs unchanged so their controlled comparison remains interpretable. Any such
repair needs a newly versioned dataset and subsequent evaluation, not a silent
rewrite of the running experiment.

## Receipt

Audit completed successfully in 24.36 seconds. Output:
`/data/tairo/veridyct-training-20261028/v3-graph/million-api-context-v1/results/report.json`.
It contains counts, TRAIN examples, input/code hashes and exact prepared-data
verification. `api-context-cases.jsonl` records classifications for all 312
selected API cases. The prepared train hashes match the owner's receipt:
V1 `d6d829b3a1288d97d6c408e12d10214a22e60025bcf1b1a3236841e69dce5a48`;
V2 `4bb0c619cdbba33b97613debab444c53efdf8d0d86045567c129b8bae7283c77`.
No GPU is used, and no diagnostic job remains active.
