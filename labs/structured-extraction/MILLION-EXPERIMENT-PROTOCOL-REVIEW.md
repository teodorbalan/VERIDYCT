# Independent review of the bounded million augmentation experiment

Owner: research_audit. Scope: read-only inspection of preparation, trainer, CPU
export/evaluation and the actual `million-factorized-{base,v1,v2}-s271828-r2`
artifacts. Existing TRAIN/DEV preparations were inspected; no training, inference,
job changes, final-challenge access or calibration access was performed. All audit
outputs are in the reviewer's own checkout and remote `v3-audit/million-protocol`.

**No concrete implementation defect was found that invalidates the narrow paired
augmentation comparison.** It can establish whether these admitted V1 or V2
examples help this flat extractor under the declared training/selection policy.
It cannot establish source-independent accuracy, arbitrary-English understanding,
full-AST competence, or an equal-compute advantage.

## Independently verified conditions

The [CPU audit](review_million_protocol.py) checked the actual frozen source against
each run's recorded hashes, reconstructed initial model state without CUDA, and
streamed the prepared training files. Its [receipt](million-protocol-review-receipt.json)
records hashes, counts and overlap diagnostics. All assertions passed.

| Condition | Verified result |
| --- | --- |
| Actual runs | All use seed 271828, factorized architecture, batch 48, learning rate 0.001, maximum 20 epochs, patience 5 and `--order-by-id` |
| Initialization | All three reconstruct identical parameter bytes, buffers and schema |
| Vocabulary/vectors | All three have identical metadata and vectors; 189 newly added vocabulary words occur in admitted TRAIN text; original vocabulary indices preserved |
| Original base | First 50,328 training rows are byte-identical to the base training file in all three variants |
| Original DEV | All three copies of the 8,478-row file are byte-identical to original DEV |
| Paired order | V1/V2 sorted training ID lists are identical; paired DEV ID order is identical |
| Protected official examples | 390 original official DEV IDs are absent from added examples' complete source references |
| Direct original-DEV overlap | Zero normalized current-text, whole text/context-input or official-row-ID overlap in any complete TRAIN set |
| Direct paired-DEV overlap | Zero normalized current-text or whole text/context-input overlap between any TRAIN set and either paired DEV view |
| Full admitted text | Every added TRAIN and paired DEV context fits 96 tokenizer tokens; context plus query and two delimiters fits 384 |
| Case separation | No shared case key, metadata evidence group or complete source-reference set across paired TRAIN/DEV |

The initial reconstructed parameter hash is
`014714c4d9519c7f8115e4da2284f636080abb4e14a5f4711f5f99795a537391`
for all three. This is a reconstruction from the recorded code, seed, schema and
vectors, not a hash of an initialization checkpoint saved during the original run.
The trainer constructs parameters on CPU before moving them to CUDA.

V1/V2 have the same row order before seeded DataLoader shuffling and the same
number of examples. The base control follows the same ordering policy, but its
shorter dataset necessarily produces different shuffled minibatches. Matching
seeds do not guarantee identical dropout masks on different input shapes, and
the trainer does not enable strictly deterministic CUDA algorithms. This is a
single-seed matched-policy experiment, not a repeated estimate of training variance.

## Admission is deliberately narrow

The preparer admits only resolved `recorded` leaves under conjunctions. Both views
must assign every typed literal to one unique query candidate, without reusing a
span. It excludes disjunctions, scoped negation, comparisons, unsupported values
and ambiguous repeated literal positions rather than fabricating supervision.
Labels supervise the literal actually claimed, including false substitutions;
source-note values and aggregate truth labels do not replace those literals.

The final ID-protected pass admits 20,729 training pairs and 2,253 case DEV pairs.
The earlier document-protected audit is a separate artifact, not the policy used
by these runs. The finalizer reuses its completed admission spool, records its
hashes, then rechecks protected sources and final normalized input overlap.
No separate `finalize_million_pair.py` is used: finalization is the preparer's
`--reuse-admission` path.

Both models see the intersection of what the existing grammar can align in both
versions. This controls admission asymmetry but creates a selected, comparatively
easy population: only 22,982 of the million pairs enter either fold. Added Boolean
atoms are zero. Good results on this population do not establish better Boolean,
negation, OR, reference ambiguity or full-million performance. There are 7,100
changed ASTs within the admitted population, so augmentation differs in some
literal targets as well as wording.

"Full context" here means **all supplied context text**. Preparation joins only
`context[*].text`; public context IDs, dates and roles are not serialized into the
model input. The 96-token check prevents text truncation, but it does not preserve
every field that could disambiguate a dated note. This is symmetric across models
and consistent with the flat extractor's interface; it limits semantic claims.

## Source overlap and context exposure

The paired split has 329 training sources and 328 DEV sources. **All 328 DEV
sources also appear in augmentation TRAIN.** Its 6,607 training and 727 DEV
evidence combinations are disjoint, as are case keys and complete reference sets.
The intended measurement is new combinations of familiar facts, not unseen-source
generalization. The original base also already contains related source facts.

Twelve normalized official DEV query strings occur as substrings in TRAIN context:
741 base rows, 1,943 V1 rows and 1,981 V2 rows. Some are short fragments such as
`20 requests a day`, `Hooly Gemini 1.0` and `€1,799.`. This diagnostic is **not proof
of protected source-ID or gold-label leakage**: new source-ID protection passes,
and shared wording can appear in another public statement. It does rule out
describing all original DEV wording as wholly unseen. The receipt includes IDs
and exact matched strings so this distinction is reviewable.

Official and synthetic DEV are also reused for checkpoint selection, with equal
weight given to their exact rates. Their final scores are development scores
after selection. Paired DEV is not used for early stopping, but is an internal
case holdout with the source overlap described above.

## How to read the six cells

`evaluate_million_pair.py` applies each of base/V1/V2 models to both fixed paired
input views, checks compatible vocabulary/characters/pairs, and uses the same
CPU runtime, threshold 0.5 and batches of 48. It scores flat typed atom sets, plus
strict JSON exactness; it does not score logical scope, source binding, observation
dates or truth labels. Gold candidate labels are not passed into the five runtime
tensors. Export first checks PyTorch/ONNX decoded parity and logit error on three
different batch shapes before writing its completion receipt.

- Compare models **within one input-view column** to assess training-data effects.
- Compare the two input views **within one model row** to assess the effect of the
  revised input/target task on that model.
- Comparing only V1-trained-on-V1 with V2-trained-on-V2 mixes both effects.

For the final report, preserve both columns, per-column paired gains/losses and
original official/synthetic results. A split by unchanged versus changed literal
targets would improve interpretation; the current six-cell evaluator aggregates
them. That missing breakdown does not invalidate its aggregate measurements.
The evaluator's report hashes models; input and source hashes must be retained
alongside it through the preparation/export receipts and this audit receipt.

## Compute and stopping confounds

| Variant | TRAIN rows | Batches/epoch | Unpadded tokens/epoch |
| --- | ---: | ---: | ---: |
| Base | 50,328 | 1,049 | 1,520,407 |
| V1 augmentation | 71,057 | 1,481 | 4,512,248 |
| V2 augmentation | 71,057 | 1,481 | 3,701,359 |

The same maximum epochs and patience do not equalize optimizer updates or compute
against base. V1/V2 have equal updates per completed epoch, but V1 processes more
tokens; each can stop at a different epoch. Report actual epochs, optimizer steps,
tokens and wall time, rather than attributing every gain to data quality at fixed
compute. The older forty-epoch base model is only a historical reference.

The training runs use A100 GPUs on the same server. The CPU evaluator sets two ORT
threads, but does not reserve two physical CPUs or isolate other jobs. Its elapsed
seconds are not a controlled Docker latency benchmark. The postprocessor waits for
each completed training result, exports its best checkpoint, then evaluates all
three; an export failure does not count as a successful cell.

## Wider language-quality evidence

The [separate main-branch million evaluation](https://github.com/teodorbalan/VERIDYCT/blob/22fa97b6fe27fcfa8d0bab7ae2e85c10c5386148/docs/research/million-v1-v2.md)
reports an important ambiguity missed by the narrow 24-pair language sample:
V2 sometimes renders an `api_version` target as an ordinary "runs version" phrase.
Its protocol-adapted evaluator's 1,879 V2 note errors all involve that attribute
distinction, including nine definitive errors. That does not mean every affected
training label is corrupt: supplied interface wording, values and dates can still
disambiguate some cases. Dropping public context dates/IDs can remove a useful
disambiguator, as noted above.

That separate evaluator's 99.5419% V1 and 99.7458% V2 truth scores are measurements
of a specialized public-protocol adapter, not results of this six-cell training
experiment. Its strict V1-to-V2 transfer is 8.0827%. Full replay passing also does
not mean every bundled test passes: legacy pilot tests retain a 20,000-versus-17,176
volume failure. These distinctions should remain visible beside any new results.

The legitimate conclusion will therefore be conditional: **under this one-seed,
bounded, flat-extraction training policy, augmentation X improves or regresses on
specified development views by measured amounts**. A claim about unseen sources,
arbitrary English or competition truth accuracy would require separate evidence.

## Reproduction

Run `review_million_protocol.py --root /data/tairo/veridyct-training-20261028
--practice <original-practice.csv> --out <own-review-output.json>` with the existing
training environment. The script forces CUDA visibility empty and reconstructs
models on CPU; it never calls their forward method. Frozen source is
`v3-factorized/source-million-training-v2`; audit output is
`v3-audit/million-protocol/protocol-review-r2.json`. Validation covers these existing
artifacts only. No result from this review should be described as a fresh model test.
