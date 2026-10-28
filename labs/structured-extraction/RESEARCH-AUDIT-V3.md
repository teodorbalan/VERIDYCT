# Research and dataset audit — 29 October 2026

Owner: Codex research_audit, delegated by the main task with Teodor's explicit
authorization. Human ownership unassigned. Isolated branch
`teodorbalan/extraction-audit-v3`, base `e0c2a12`. Scope: literature review,
development-only audit scripts and an independently authored behavioral suite.
No model training, production interface changes or GPU allocation in this task.
Calibration releases were not read. The new final challenge remains withheld.

## Conclusion supported by measurements

The existing synthetic data is useful but insufficient to justify an
"understands any wording" claim. The small models largely saturate its generated
styles while the official development set remains much harder. More elaborate
architectures can be tested, but a classifier cannot recover typed values that
the deterministic candidate parser never proposes.

This is a targeted review of primary research across 2017–2026, not an exhaustive
search of every paper. Architecture descriptions below are research leads, not
claims that their published benchmark scores transfer to VERIDYCT.

## What the research suggests

| Method / source | Relevant idea | Applicability here |
| --- | --- | --- |
| [fastText, 2017](https://aclanthology.org/E17-2068/) | Efficient bag-of-words and n-gram classification | A cheap control can reveal lexical shortcuts; it does not resolve scope or coreference. |
| [DyGIE++, 2019](https://arxiv.org/abs/1909.03546) | Refine span representations with within- and cross-sentence graph messages | Useful inspiration for explicit antecedent/span links; its published system also uses BERT, so a GloVe-only adaptation is a new experiment. |
| [SpERT, 2019/2021](https://arxiv.org/html/1909.07755v4) | Joint span/entity/relation classification with local context and strong negatives | Particularly relevant to unrelated numbers and unconnected entity pairs; the full method uses BERT and is not the proposed deployment stack. |
| [Biaffine NER, ACL 2020](https://aclanthology.org/2020.acl-main.577/) | Score span start/end pairs jointly | Offers a path beyond fixed candidate spans. The paper's accuracy includes contextual embeddings; the scoring head alone is not a promised gain. |
| [Global Pointer, 2022](https://arxiv.org/abs/2208.03054) | Efficient span-boundary scoring with relative positions | A discriminative span detector could complement the typed parser; it must still normalize values and attach subjects/attributes. |
| [HGERE, EMNLP 2023](https://aclanthology.org/2023.emnlp-main.467/) | Span pruning plus hypergraph interaction for joint extraction | Graph reasoning can reduce pipeline errors, but adds complexity; measure against factorized heads rather than assuming it wins. |
| [GLiNER, NAACL 2024](https://aclanthology.org/2024.naacl-long.300/) | Match text spans to label representations in parallel | Label-semantic scoring is relevant. Its pretrained bidirectional encoder is not the same as a tiny network trained from static embeddings. |
| [GLiREL, 2025](https://arxiv.org/html/2501.03172v1) | Match entity-pair and relation-label representations in one pass | Uses DeBERTa-v3-large; joint label input also has sequence-length and label-order effects. It is not automatically a compliant drop-in for the current no-LLM boundary. |
| [Efficient zero-shot RE study, LREC 2026](https://aclanthology.org/2026.lrec-1.480/) | Evaluate rejection and realistic unmarked entity inputs | Directly supports measuring unrelated text and abstention. The study finds tested systems insufficiently robust under those assumptions. |

The research does not establish that every pretrained encoder is banned by the
organizer's terminology; that is a contract interpretation, not an architectural
fact. Under the project's current conservative no-LLM implementation boundary,
these pretrained-language-model systems are references, not silently adopted
dependencies. Static GloVe vectors and from-scratch discriminative encoders remain
the current comparison space.

SpERT's ablations specifically distinguish hard negative entity pairs from random
span negatives, and examine the benefit of localized context. This suggests
training the model to reject *plausible but unrelated* nearby values, rather than
only obvious out-of-domain strings. [SpERT analysis](https://arxiv.org/html/1909.07755v4)

CheckList separates minimum functionality, invariance and directional behavioral
tests. Its implication here is to test one semantic obligation at a time, such as
retaining a stated false value or ignoring an unrelated bill, while keeping these
tests separate from population-accuracy estimates. [CheckList](https://aclanthology.org/2020.acl-main.442/)

COGS demonstrates why nearly perfect in-distribution results need not imply
compositional generalization: its reported Transformer/LSTM in-distribution
results are 96–99%, versus 16–35% on systematic generalization splits. Those are
COGS results, not forecasts for this task. The useful lesson is to hold out
structures/families, not merely new numeric values. [COGS](https://aclanthology.org/2020.emnlp-main.731/)

## Measured training/development overlap

Audit source: immutable `data-v2` on BENGEE; 32,862 training rows, official390 and
synthetic8088 development rows. Text normalization folds case and whitespace.
Digit masking replaces numeric strings; entity masking additionally replaces
longest matching public subject names/aliases. Ordinary wording and punctuation
are retained. These are surface diagnostics, not a perfect syntactic parser.

| Development group | Exact text overlap | Digit-template overlap | Entity+digit-template overlap |
| --- | ---: | ---: | ---: |
| Official, 390 rows | 0 | 0 | 2 (0.51%) |
| Synthetic, 8,088 rows | 0 | 1,101 (13.61%) | 1,696 (20.97%) |

Only 742 / 8,088 synthetic development rows supply previous-row context. The MMR
interface supplies one previous row, so high scores do not test arbitrary
long-distance document reference resolution. Synthetic rows average 16.76 words
versus 9.50 official words; longer text alone does not establish semantic difficulty.

An exact TF-IDF cosine nearest-training-sentence baseline over word unigrams and
bigrams predicts *subject/attribute sets*, copying no gold development labels.
It deduplicates digit-masked training sentences, retaining 16,168 prototypes.
It obtains 3,628 / 8,088 = 44.86% pair-set exact on synthetic, and 190 / 390 =
48.72% on official. Pair F1 is 67.55% and 58.41%, respectively. These metrics
exclude typed values and therefore must not be called complete JSON accuracy.
The baseline has no compositional splitting or context resolution, and many
synthetic rows contain multiple assertions. Its limited result does **not**
support claiming that the entire synthetic test is trivial nearest-neighbor
memorization. It does support retaining such cheap controls in future experiments.

## Behavioral probes on the frozen v2 model

A seeded sample of 100 official and 100 synthetic development rows was evaluated
with unchanged gold. The original sampled exact counts were 84 and 100.

| Probe | Official prediction unchanged | Synthetic prediction unchanged |
| --- | ---: | ---: |
| Same row, batch padded by unrelated long input | 100 / 100 | 100 / 100 |
| Append a neutral sentence about an umbrella | 97 / 100 | 100 / 100 |
| Lowercase text and supplied context | 94 / 100 | 97 / 100 |
| Remove supplied context | 91 / 100 | 94 / 100 |

Padding sensitivity was not observed in this sample; an architectural suspicion
is not a measured failure. Lowercasing can change case-sensitive units, so the
rate is a diagnostic, not an unconditional invariance requirement. Removing
context changes available evidence and may genuinely make a statement ambiguous.
The neutral sentence changed two originally correct official examples to wrong.

## Independent challenge and parser ceiling

The assistant authored 224 unique examples: dev112 and final112, each with sixteen
phrase families, disjoint across splits. Categories cover paraphrases, unrelated
numbers, misleading entities, coreference, comparisons, conjunctions, Boolean
negation, unsupported-domain rejection, value preservation and version operators.
There are also ten ambiguous-context and ten type-violation cases per split,
reported separately from the primary score. A type-incompatible statement is not
declared universally invalid by the official contract; abstention is the policy
of this diagnostic. All claims are invented stated assertions, not Hooly evidence.

Baseline development results:

- Primary exact: 87 / 92 = 94.57%; atomic F1 96.13%.
- Paraphrases: 6 / 10; coreference: 9 / 10.
- Type-violation diagnostic: 8 / 10 abstentions.
- Ambiguous-context diagnostic: 10 / 10 abstentions.

Candidate coverage is 88 / 92 gold atoms, so four of five primary errors occur
before neural classification. Monthly-price wording places the billing period
before the amount; the existing parser proposes a price without `per: month`.
Only one remaining primary error is attributable to classification/context on
this fixture. This narrow suite is largely easy and highly correlated within
families. Its 112 rows are not 112 independent language phenomena.

A **development-only** follow-up probe has sixteen monthly-price phrasings,
authored after observing those parser failures. Baseline exact is 4 / 16 = 25%;
candidate coverage is also 4 / 16. The other twelve outputs are impossible for
the classifier to get right with unchanged candidate proposals. Some probe
phrasings exceed the organizer's strict generation-format grammar, so this is a
test of the user's broad-language objective, not evidence of official invalidity.
It is not a fresh blind score. Final challenge text and gold were not altered
or evaluated in response to these development findings.

## Artifacts and continuation

Scripts: [dataset audit](audit_dataset.py), [robustness probes](audit_robustness.py),
[challenge evaluator](evaluate_challenge.py), [development price probe](build_price_probe.py).
Compact receipts: [audit evidence](audit-evidence-v3.json).

Remote root: `/data/tairo/veridyct-training-20261028/v3-audit`.
Development fixture: `challenge-dev.jsonl`, SHA256
`a3448d197ba5d4e89447d12a06530205113cbe6059cd8f50f96f16abc993bef6`.
Final fixture: `challenge-final.jsonl`, SHA256
`966b5c7c5061eab4e24c61177eb3994b5e852dec3c955dff973bbd5bf7ff33a0`.
Do not open the final fixture or its builder until parent model-selection freeze.
The generator and row-level fixtures remain ignored artifacts to preserve that
boundary. The evaluator rejects final filenames/rows unless `--allow-final`.

Neither this suite nor the previous sealed release should become an unlimited
tuning target. New training examples can use independently authored negative and
context patterns; the final phrase families remain withheld. Adoption still
requires a frozen comparison on fresh held-out data and an actual CPU container.
