# Dynamic INT8 CPU experiment

Owner: research_audit. Frozen inputs: factorized-s271828-v2 and selected-v2.
All exports and logs are isolated under remote `v3-audit/quantization`; no frozen
bundle was modified. [The receipts](quantization-results-v3.json) record hashes,
commands, timings and prediction changes. Tools: [export](quantize_cpu_models.py),
[benchmark](benchmark_quantized_cpu.py), [controller](run_quantized_bench.py).

Dynamic INT8 reduced model size, but did not establish a worthwhile speed or
accuracy improvement on the actual AMD EPYC 7742. Keep FP32 as the default.

## Protocol

ONNX Runtime 1.23.2, offline read-only Docker, UID 10001, 2 CPU quota, 6 GiB,
two intra-op threads, batch 48. The same 8,590 development rows were used in
each separate process: official 390, synthetic 8,088, challenge primary 92,
challenge diagnostic 20. Three inference passes on prepared inputs were timed;
preparation, loading and wall time are reported separately. Final challenge and
all calibration gold remained untouched. Diagnostic challenge rows are not
included in primary accuracy.

Two variants were exported: constant-weight MatMul/Gemm only, and the same plus
LSTM. Both use QInt8, `reduce_range=True`, no per-channel quantization, and
`MatMulConstBOnly=True`. The recurrent exports contain one DynamicQuantizeLSTM
for factorized and four for the old ensemble. All six models ran successfully.

These are **dynamic activation-and-weight quantization**, not pure W8A32
weight-only inference. The reduced-range setting effectively uses seven-bit
weights to reduce the documented U8S8 saturation issue on AVX2 without VNNI.
EPYC 7742 has AVX2 but no AVX512/VNNI. This follows the
[official ORT guidance](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html)
and the pinned [LSTM quantizer](https://github.com/microsoft/onnxruntime/blob/v1.23.2/onnxruntime/python/tools/quantization/operators/lstm.py).

## Results

The median times below cover all 8,590 rows once after preparation; RSS is the
peak Python process RSS, not a full container memory peak. MB is decimal.

| Model | ONNX MB | Median seconds | RSS MiB | Official /390 | Synthetic /8,088 | Challenge /92 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Factorized FP32 | 7.205 | 7.702 | 356.2 | 339 | 8,059 | 86 |
| Factorized dense INT8 | 5.493 | 7.525 | 346.7 | 339 | 8,058 | 87 |
| Factorized recurrent INT8 | 4.560 | 8.036 | 346.2 | 339 | 8,059 | 86 |
| Old ensemble FP32 | 24.850 | 21.061 | 500.3 | 336 | 8,077 | 87 |
| Old ensemble dense INT8 | 20.629 | 22.596 | 484.5 | 336 | 8,077 | 87 |
| Old ensemble recurrent INT8 | 14.412 | 21.476 | 472.1 | 335 | 8,077 | 87 |

Factorized dense INT8 changed four predictions: one primary challenge gain and
one synthetic regression offset in row-exact totals. Recurrent INT8 changed
four predictions with one synthetic gain and one regression. The old dense
variant changed no predictions but was slower. The old recurrent variant
changed four official predictions, gaining one correct row and losing two.

The 2.3% factorized dense timing difference is too small to call a robust win
from one three-pass run on a shared host. Recurrent factorized was 4.3% slower;
old dense was 7.3% slower. Model size fell 36.7%/42.0% with recurrent quantization,
but RSS fell only 2.8%/5.6%. Character-CNN and other unchanged operators, runtime
overheads and input storage still contribute cost. An architecture can become
smaller without becoming faster.

At observed batch throughput, FP32 model inference alone projects to roughly
18 seconds for 20,000 rows for factorized and 49 seconds for the old ensemble.
This is a linear throughput estimate, not a measured complete 20,000-row solve.
It excludes verifier, claim generation, I/O and any future model ensemble.
Nevertheless the measured extraction component leaves substantial room within
30 minutes and 6 GiB. Quantization is not the current bottleneck, so its minor
prediction perturbations bring little practical value. Full competition
container validation remains a separate requirement.
