# Structured extraction experiments

Owner: Codex, authorized by Teodor on 2026-10-28. Human ownership unassigned.
Isolated branch: `teodorbalan/structured-extraction-training`, base `d0af169`.
Paths: this laboratory and its handoff/decision documents. The existing Rust
runtime, official data/contracts and application interfaces are unchanged.

The experiment turns text and explicitly supplied preceding text into typed
subject–attribute assertions. A text-only parser proposes values. A small
discriminative neural network assigns each candidate to one of the public
lexicon's 514 subject–attribute pairs, or rejects it. There is no LLM decoder.
False and unsure statements retain their stated values. This extractor does
not decide truth, retrieve evidence, or assert that arbitrary text is understood.

Two rounds, sixteen GPU training runs and four ensemble candidates are complete.
The selected three-model ensemble is frozen and evaluated in an offline CPU
container. See [measured results](RESULTS.md) and [numeric receipts](results.json).
The model and Docker archives are local ignored artifacts; the Rust solver has
not adopted this experimental extractor.

## Data and acceptance

The supplied v3 archive SHA256 is
`300623a5080ffb69eeb471e7069b88878f010059f73f002afee1995e00d99bc3`.
The MMR subset contains 20,000 rows selected from three synthetic worlds.
All 8,088 rows from its development world are reserved for model selection.
The first round trains on the two other worlds, removing text duplicates against
this development split, leaving 11,748 rows. Preparation and selection read no
calibration or sealed gold. Sealed gold is scored only after the final freeze.
Generator styles overlap; development accuracy is not a universal guarantee.

Only text, supplied context and public names enter the network. Label, verdict,
world identity, date, evidence selection and expected values do not. Gold clause
spans are used exclusively to align training labels to text-only candidates.
The name-value gazetteer includes names learned from the training partition;
unseen capitalized name values can also be proposed without adding subjects.
Byte offsets are converted explicitly to character offsets before token alignment.

Selection uses exact complete assertion sets and atomic precision/recall/F1,
with separate context, multiple-assertion and value-kind diagnostics. Decimal
values are compared after rounding to nine decimal places because the archive
contains binary arithmetic noise. Strict serialized JSON equality is reported
separately. Neither schema validity nor candidate coverage counts as model accuracy.

## Reproduction

Development environment: Python 3.10, PyTorch 2.8.0 CUDA 12.8, NumPy 2.2.6.
PyTorch CUDA 13.0 in an unrelated environment was incompatible with the installed
driver; the experiment uses its own virtual environment, without driver changes.

```sh
python -m unittest discover -s labs/structured-extraction -p 'test_*.py'
python labs/structured-extraction/prepare.py --archive /path/to/veridyct-evaluation-data-v3.zip --lexicon data/lexicon.json --out artifacts/training-data
python labs/structured-extraction/train.py --data artifacts/training-data --out artifacts/run-03 --variant 03-char-bilstm
```

Six configurations compare a CNN, word BiLSTM, character CNN + BiLSTM,
a larger character BiLSTM, character BiGRU, and a small encoder trained from
scratch. The latter is a discriminative classifier, not a pretrained LLM.
Two additional seeds test stability of the two BiLSTM sizes. Initial word
embeddings are learned from the training split; pretrained-vector comparisons
must be reported as separate runs if added.

Each run records code hashes, data metadata hash, seed, configuration, hardware,
parameters, epoch throughput, GPU memory, exact metrics, predictions and atomic
best/last checkpoints. A training run refuses to silently fall back from GPU to
CPU. Outputs live under ignored `artifacts/` locally and the isolated remote root.

## Limits

The candidate grammar is a measured baseline, not a full implementation of the
organizer's value grammar. Sentence/clause splitting is heuristic. One candidate
is assigned at most one pair, so shared-value ellipsis can require extension.
Long-distance context is accepted only when explicitly supplied; automatic
antecedent resolution is not implemented. The MMR training interface supplies one
previous row. The final evaluation adapter supplies the actual preceding three
public CSV rows, with no gold antecedent pointers. Context is limited to its last
96 tokens; inputs exceeding 384 total tokens are rejected explicitly. Candidate
confidence is not a calibrated truth probability. Outputs are deduplicated
assertion sets, not ordered lists preserving repeated mentions.

CPU export parity and constrained Docker measurements passed for this laboratory.
Final competition adoption still requires Rust integration, truth verification,
1,000-claim generation and the unchanged official checker for the combined system.
Lexicon-constrained labels do not ensure semantic type consistency: the frozen
model can attach a country count to an inappropriate quantity attribute. Unknown
relationships and unrelated numeric clauses are not reliably rejected.

## Measured first round

All eight runs completed. Best synthetic selection result: two-layer char-CNN +
BiLSTM, 2,307,955 parameters; 8,078/8,088 complete rows (99.876%), atomic F1 99.926%.
Strict JSON exact: 8,066/8,088. Actual training plus evaluation took 414.14 seconds.
On the organizer's 1,897 practice rows, with no cross-row context, that same model
achieved only 689/1,897 complete rows (36.32%). This large domain gap invalidates
any interpretation of synthetic 99.88% as general accuracy.

The ONNX export is 9,242,989 bytes and reproduces the development predictions.
Independent text-only preprocessing rebuilt every one of the 8,088 inputs exactly.
Dynamic batch/sequence parity was checked for batches of 1, 7 and 32.
Two-thread CPU inference on prepared inputs took 7.685 seconds.

The standalone extraction container ran 20,000 repeated practice texts offline,
read-only, UID 10001, 2 CPUs / 6 GiB: 18.50 seconds total, 17.28 seconds inside
the evaluator including preprocessing, peak process RSS 236,264 KiB, image
344,387,962 bytes. This is a throughput experiment, not unseen accuracy or the
complete Rust competition runner. No truth verification or 1,000-claim generation
is implemented by this laboratory container.

## Mixed second round

`prepare_mixed.py` creates a new immutable dataset. Official texts are grouped
after masking entity names and numbers; SHA256 modulo five reserves 390 rows.
Only training parents receive deterministic value replacements and repetition.
Actual previous three rows provide context; held-out rows are excluded from
training context. CSV adjacency is an experimental context policy, not a proven
competition guarantee. Some fragments remain underdetermined even with this context.

32,862 training rows contain 42,411 atomic occurrences: 17,387 official-derived
rows and 15,475 synthetic rows/visible anchors. Gold clause spans supervise the
synthetic anchors, including rejection of validity-prefix dates. There are 24
unresolved training alignments; ambiguous matches are ignored, not fabricated.
All 12,833 development occurrences have value candidates; labels still require
neural prediction. Model selection equally weights official and synthetic exact
rates. The official holdout is development data, not a final blind evaluation.

GloVe 6B 100-dimensional vectors initialize the first 100 of 128 embedding
dimensions. Their [Stanford NLP mirror](https://huggingface.co/stanfordnlp/glove)
archive SHA256 is `6471382cdd837544bf3ac72497a38715e845897d265b2b424b4761832009c837`.
4,219 of 6,998 vocabulary entries match. These are static word vectors, not an LLM
or a factual evidence source. Numeric augmentation is deterministic, logged and
round-tripped through the text parser; it does not produce truth labels.

The first-round model scored 134/390 (34.36%) on the exact same official holdout
and context used by the second round. Use that matched baseline for comparison,
rather than comparing the second round's subset with all 1,897 practice rows.

## Running the CPU model

Use the source files frozen with a model bundle, so parser revisions cannot
silently change an existing model's preprocessing. `runtime.py` accepts one JSON
object per stdin line with `text` and optional `previous_text`, or `--text` and
`--previous`. It returns typed forms, character spans, named relations and
uncalibrated extraction scores. It does not return a truth verdict.

```sh
python runtime.py --bundle /path/to/bundle --text 'Hooly AI Pro costs €79 per month.'
python package_runtime.py --bundle /path/to/bundle --source /path/to/frozen-source --out /new/build-context
docker build -t veridyct-extractor:local /new/build-context
docker run --rm --network none --read-only --cpus 2 --memory 6g veridyct-extractor:local --text 'Hooly AI Pro costs €79 per month.'
```

The exact tested image is also available without rebuilding:

```sh
docker load -i artifacts/remote-results/delivery/veridyct-extractor-selected-v2.docker.tar.gz
docker run --rm --network none --read-only --cpus 2 --memory 6g veridyct-extractor:selected-v2 --text 'Hooly AI Pro costs €79 per month.'
```

For PowerShell stdin, JSON Unicode escapes avoid legacy native-pipe encoding
loss. The runtime itself reads Unicode JSON:

```powershell
'{"text":"Hooly AI Pro costs \u20ac79 per month."}' | docker run --rm -i --network none --read-only --cpus 2 --memory 6g veridyct-extractor:selected-v2
```

`previous_text` is optional in each input object and must be supplied by the
caller. It is not automatically carried over between stdin requests.
