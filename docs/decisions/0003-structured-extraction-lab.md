# Decision 0003: isolated GPU training for a CPU extractor

Status: measured laboratory, 2026-10-29; not adopted by the competition runtime.
Scope: [training task](../handoffs/structured-extraction-training.md).

Use GPU acceleration only for development experiments. Compare small
discriminative encoders with a shared typed-value candidate parser and
lexicon-constrained output labels. Numerical values are copied and normalized
from text, rather than generated. Keep truth verification separate from extraction
and keep synthetic worlds out of the official evidence store.

Choose the architecture using a whole held-out development world and grouped
official practice development rows, equally weighted after the first round
exposed a severe synthetic-to-official domain gap. Measure
complete structured output, context cases, atomic F1 and CPU cost. Never select
models using sealed gold. A measured improvement and CPU export parity are
required before changing the existing Rust competition runtime. Existing CPU
and no-LLM constraints continue to apply.

Selected result: an equal-probability three-member char-CNN/BiLSTM ensemble,
6.20 million parameters and a 24.85 MB ONNX export. Freeze preceded sealed scoring;
no adjustment followed. Complete-row sealed extraction is 95.635%, or 95.317%
after excluding normalized texts shared with train/development. An offline 2-CPU,
6-GiB laboratory container processed 20,000 rows in 113.82 seconds. See the
[results and limits](../../labs/structured-extraction/RESULTS.md).

Keep the current Rust path until integration and full-system evaluation are
complete. Lexicon-constrained output classes do not prove correct relationships,
type consistency or reliable abstention on unsupported claims.
