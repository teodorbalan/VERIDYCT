# Million V1/V2 delivery and oracle audit

Owner: `/root/graph`, 2026-10-29, in the isolated extraction-graph-v3 checkout.
Human ownership unassigned. Scope: inspect the bundled validator dependency
paths, run both complete authorized delivery checks on CPU, compare their
validation meaning, and assess compatibility with the existing extractor. No
GPU training, service changes, original archive edits or old-v3 held-out gold
reads are part of this audit.

## Exact inputs and execution boundary

| Archive | Bytes | SHA256 |
| --- | ---: | --- |
| `veridyct-million.zip` | 770,410,388 | `17194179b1e17cca148ba42c21a7c155c5556423938d352e8bda90ac0b8f852c` |
| `veridyct-million-v2.zip` | 810,727,579 | `416f95c6ab39a8b217e7aa1bad954b93134d75cb20f7f065c319cd71e4c3ecef` |

Independent hashes of the local Downloads files match these remote hashes.
The supplied archives were already present at
`/data/tairo/veridyct-training-20261028/`. They were extracted only beneath
`v3-graph/million-validation/v1/` and `v3-graph/million-validation/v2/`.
Every archive entry was checked for path traversal and symbolic links before
execution. All manifest dataset/code paths resolve inside the respective
extracted directory. Uncompressed archive members occupy 1,036,749,951 and
1,054,233,754 bytes, respectively; JSONL inside gzip remains compressed on disk.

Source inspection covered the two `check_delivery.py` entrypoints and their
actual imports: `engine`, `oracle`, `generator_values`, the pilot `verify`,
`common`, `reference_values`, and V2 `revision`. Those execution paths use the
standard library, contain no network/model calls, no shell invocation, and open
the shipped SQLite registries in read-only mode. Imported generator output
writing is behind its `__main__` entrypoint and is not invoked. The unrelated
worker/collector/build/package scripts were not run. All new logs, extraction
files and receipts stay in the assigned subtree; the archive sources are
unchanged. This is a scoped source audit, not an OS security sandbox claim.

Both READMEs request Python 3.12+, but all bundled Python files parse under the
available CPython 3.10.12. We used the existing venv interpreter with `-B`,
`PYTHONNOUSERSITE=1`, `PYTHONHASHSEED=0`; no dependency installation or code patch
was needed. The complete run results below establish compatibility for these
specific validation paths, not every optional archive script.

## What is checked

V1 checks 105 dataset-file hashes, 26 frozen generator/configuration hashes,
original lexicon/practice fingerprints, SQLite integrity, one million registry
entries, and case repetition caps. Full mode validates all 17,176 pilot audit
rows through `Checker.check` and replays all 982,824 generated rows through
`Engine.validate`, with 20 profiles and exact shard sequence/count checks. It
then streams the training pool and audit together, requiring equal ID, input
and target, correct envelope fields, total rows and label counts.

`Engine.validate` reconstructs the AST from the reserved recipe, evidence mask,
input text, note ordering, reference links and bindings. It validates source
dependencies and recomputes labels with `oracle.evaluate`. Bank construction
also checks each admitted source against its original practice row and fixed
lexicon slot; the logic bank uses only originally true, exact singleton
annotations. The pilot validator preserves whole-row labels when individual
atom truth cannot be inferred from a false multi-atom sentence.

V2 checks 62 dataset hashes, eight frozen code/configuration hashes, original
organizer fingerprints, parent-manifest hash, original compressed parent-audit
hashes, SQLite integrity/count/caps, output counts and label receipts. Its full
mode uses three CPU workers to reconstruct each output from the original parent
audit and recorded presentation nonce, then compares exact partition hashes
with the delivered pool. Every rewritten row goes through `Revision.check`,
which independently calls the unchanged oracle on the revised AST and evidence
availability. Reconstructed rows include metadata and context in the compared
hash, not only their labels.

The 9,899 retained source-preserving pilot rows return early from
`Revision.convert` without `Revision.check`. V2 alone does not independently
revalidate their original pilot semantics. Running V1 full mode as well supplies
that validation. The frozen file lists also do not include every utility in the
archive; the whole-archive hashes above pin the precise source bundle inspected.

The unchanged V1/V2 `oracle.py` SHA256 is
`3b0b9bc07c97904519ba8bcde8be892cef1002f922dd57c4c17786541b1a4e1d`.
It validates every AST branch before evaluating truth, including branches that
could otherwise short-circuit. Its default limits are depth 12 and 128 nodes.
The five logic node types are `recorded`, `compare`, `all`, `any`, `not`; that
does not reduce the full problem to five independent sentence classes.

## Observed verification results

**Both complete delivery checks pass with exit status 0.** V1 reports
`verified_rows=1000000`, `hashes="all matched"`, `independent_replay=true`.
V2 reports `rows=1000000`, `hashes="matched"`, unchanged parent audits and
`full_rewrite_and_oracle_replay=true`. V2 replays 22 recorded presentation
overrides. Both reproduce exactly 493,356 true, 434,083 false, 72,164 unsure
and 397 null labels. No mismatching hash, row or formal verdict was reported.

| Full check | CPU workers | Wall seconds | User + system CPU seconds | GNU time peak RSS, KiB |
| --- | ---: | ---: | ---: | ---: |
| V1 | 1 | 587.27 | 583.43 + 3.73 | 30,796 |
| V2 | 3 | 249.37 | 598.02 + 3.41 | 22,896 |

Hardware is the shared AMD EPYC 7742 server. These runs overlap in wall time;
their speed difference combines different checker implementations, V2's shorter
text and three-worker execution. It is not a controlled V1/V2 algorithm benchmark.
GNU time's V2 peak-RSS number is not the sum of all simultaneous workers. Both
checks stream the million rows rather than materializing the pool in memory.
No GPU, model API or generation tokens are used by these replays. Provider
billing costs were not measured. Roughly 2.1 GB of extracted archive files,
plus the existing 1.6 GB archives, suffice for this validation layout.

The included V1 test suite passes all 16 tests in 22.616 seconds, including
2,400 examples across all 20 profiles, 20,470 compatible operand/operator
combinations, ternary truth tables, typed comparison, reference/provenance
mutation rejection and structural limits. V2 passes all eight tests in .291
seconds, including the 60 reviewed parent rows, evidence-mask-preserving
comparison replacement, logic simplification, role-compatible false values,
deliberate corruptions and presentation nonces. These are the archive's tests,
not newly independent human annotations.

Commands from each extracted archive root, using the existing Python interpreter:

```sh
python -B labs/semantic-million/check_delivery.py --dataset dataset --full
SEMANTIC_BANK=dataset/frozen-bank.json python -B -m unittest discover -s labs/semantic-million -p 'test_*.py' -v

python -B labs/million-review/check_delivery.py --dataset dataset --full --jobs 3
REVIEW_BANK=dataset/frozen-bank.json REVIEW_SAMPLE=dataset/review/original-60.jsonl python -B -m unittest discover -s labs/million-review -p 'test_*.py' -v
```

The two `full-check.log`, `full-check.time.txt`, `full-check.launch.json`,
`source-inspection.json`, `tests.log` and `tests.time.txt` files preserve actual
commands, versions, stdout, exit codes, wall/CPU times and GNU time memory
measurements outside Git. The V1 manifest SHA256 is
`24759ece84d3f0df37e636be60bf68b67044c4ae9bcd83eefd8aebb62c97fa31`;
V2 is `2445587ad312b230c8412ef5ce54bda530e5c61250290daa0ce72155649ba85e`.

## V1/V2 changes and semantics

The coordinator independently streamed the paired million rows. Its measured
comparison is preserved at
`/data/tairo/veridyct-training-20261028/v3-root/million-comparison-v1/comparison.json`.
We read that receipt, rather than duplicating its full scan. It finds zero
duplicate IDs and zero changed labels/parse statuses. Inputs change on 990,101
rows, targets on 827,042, ASTs on 445,023, and reference links on 654,340.

| Property | V1 | V2 |
| --- | ---: | ---: |
| `annotated_practice_v1` rows | 17,176 | 9,899 |
| Supplied-note logic rows | 982,824 | 990,101 |
| True / false / unsure / null labels | 493,356 / 434,083 / 72,164 / 397 | unchanged |
| Mean claim words | 74.18 | 56.41 |
| Mean context words | 93.81 | 47.94 |
| Mean context turns | 8.74 | 5.03 |
| Comparison AST nodes | 454,950 | 189,265 |
| Recorded-value AST nodes | 3,081,856 | 3,616,458 |

V2 is materially shorter and removes many unrelated-metric comparisons. These
are sometimes replacement tasks with a different AST, not synonymous paraphrases
of the same question. For example, a fully true comparison can be replaced by
`all(true_recorded_left,true_recorded_right)`; a fully false one can become
`any(false_recorded_left,false_recorded_right)`. Both preserve the comparison's
truth for every availability mask: missing either operand yields unsure, while
both supplied operands recover the original true/false result. This is a
formal label-preserving replacement, not semantic equivalence of old/new text.

For `recorded`, the oracle checks literal typed note content, not world truth
at a later time. For `compare`, compatible dimensions may be converted using
exact rational arithmetic; partial dates retain interval uncertainty and
cross-precision version ordering is rejected. Missing supplied evidence yields
unsure, even if the global bank happens to contain the value. `all` has false
dominance, `any` true dominance, and `not(unsure)` stays unsure. The 397 null
labels instead represent 20 no-claim and 377 unresolved-reference cases; they
must not be collapsed into false or unsure.

## What passing does not establish

The oracle is separately implemented from the fast generator arithmetic, but
the text check reconstructs the same approved rendering grammar. V2 generates
text and validates it through the same revision routine. Perfect replay therefore
shows faithful generation, delivery integrity and agreement of formal semantics;
it is not an independent natural-language interpretation of each sentence.
An incorrect source annotation or misleading template can pass every replay.
Whole-archive hashes identify the received bundle; they are not an organizer
signature or an independent guarantee that the shipped manifests are truthful.

The source bank for the large tier still contains 457 rows, 51 subjects and
224 slots, including one duplicate canonical observation. The retained pilot
extends total coverage to 62 subjects/514 slots. It is one million combinations,
not one million independent facts. Source interpretations, rounded-text
precision and organizer labels remain inherited assumptions. V2's sixty-example
review is explicitly AI editorial review; Mihai's human review is pending.

The paired audit finds 255,012 cases, 254,844 evidence groups and 1,897 distinct
underlying practice source IDs across the full pool. A source appears as many
as 14,107 times. An evidence-group split still shares 1,282 source IDs between
its train and test partitions. All rows are declared train-eligible and unsplit;
random row splitting cannot be called independent generalization. The global
majority-label baseline is 49.34%, while a profile/family-conditioned majority
diagnostic reaches 73.51%. The latter uses metadata/observed labels and is a
shortcut warning, not a permitted inference feature or fair learned score.

## Architecture feasibility and next experiment boundary

The existing 515-way candidate extractor can help identify literal values,
subjects and attributes. It cannot directly express this target contract:
recursive negation/conjunction/disjunction scope, dated source-note identity,
comparison operands, availability masks and unresolved-reference status. A
flat assertion projection is only an extraction diagnostic, not AST or verdict
accuracy. The failed shared-value experiment also cautions against assuming
that extra synthetic volume alone fixes output ownership and scope.

A feasible non-LLM design separates a compact supervised parser for spans,
source bindings and constrained AST structure from deterministic typed logic
evaluation. A finite valid schema makes constrained decoding possible, but
does not guarantee correct language parsing. Distinguish the inherited-practice
and supplied-note task schemas explicitly. Feed only `input` fields to the
learner; target structures/bindings, metadata, proof availability masks and
source gold values remain supervision or audit material. Global source-ID
memorization must never override the current input's provided-notes policy.

Before a training claim, reserve source/document and language-family partitions,
quantify overlaps, and evaluate complete AST match, source binding, missing-note
behavior, typed comparisons, scope and final verdict separately. Keep genuinely
external or human-labeled evaluation apart from all practice-derived material.
The measured V2 average input is shorter, but these averages are not tokenizer
length limits; truncation coverage must be checked before reusing a 384-token
encoder. No training throughput or GPU memory estimate is presented as measured
for the million-row AST task, because no such training run was authorized here.
