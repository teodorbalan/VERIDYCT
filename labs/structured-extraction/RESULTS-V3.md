# Continued extraction research: frozen V3 result

Owner: root. Source: isolated structured-extraction-training branch. This round
compared 20 completed checkpoints/control models after development-only
selection; it does not replace the native Rust solver deployed elsewhere.

The selected stack averages probabilities from factorized V2, semantic-label V3
and factorized-mentions V3. It contains 5,385,804 parameters; ONNX is 21,833,019
bytes. Static label graph scores are folded into a linear head. This is not a
runtime LLM and does not require a GPU. More elaborate candidate graphs, larger
encoders, R-Drop and more examples did not uniformly improve all measured slices.

| Exact extraction | Prior V2 control | Selected V3 |
| --- | ---: | ---: |
| Official development /390, common robust parser | 336 | 346 |
| Synthetic development /8,088 | 8,077 | 8,083 |
| Authored challenge development /92 | 89 | 90 |
| Authored final /92, each complete frozen pipeline | 76 | 87 |
| Exposed 20,000-row regression, previous3 context | 19,127 | 19,706 |

Official development atomic F1 is .94093. Final atomic F1 is .97. The final
paired comparison has 76 both-correct, 11 gains, zero regressions and five
both-wrong. Old control retains its original grammar while V3 uses the robust
billing-period adapter: this is a complete-pipeline improvement, not a claim
that architecture alone explains it. Ten ambiguity and ten invalid-type cases
are separate diagnostics; V3 has zero exact answers in both, showing that safe
rejection is unresolved. These rows are not silently included in primary accuracy.

Selection was frozen before final fixtures were opened. The final is now spent;
later million-row experiments cannot reuse it as fresh evidence. Other teammates
had already published archive calibration results, so these archives are no
longer team-blind. See [exposure inventory](EVALUATION-EXPOSURE-V3.md) and the
[independent review](OBSERVABLE-SELECTION-REVIEW-V3.md).

The selected ONNX reproduces all 8,570 common development decodes and passes
dynamic-batch parity. In the actual offline, readonly UID10001 Docker container
with 2 CPU and 6 GiB, the exposed 20,000-row regression completed successfully:
101.997 seconds including preprocessing; peak process RSS 745,716 KiB (728 MiB).
It scored 17,823/18,103 targets exactly; 19,678/20,000 are strict JSON matches.
The old run was 111.522 seconds and 748,712 KiB. These single shared-host runs
are not a repeated statistically controlled speed comparison.

The subsequent [padding audit](PADDING-CONSISTENCY-AUDIT.md) found zero decoded
atom/span differences on official390 across singleton, mixed-length batches48
and exact-length batches48. Mixed padding nevertheless changes confidence on
92 rows (maximum .0814); exact-length scores match singleton within 2.98e-7.
Parity of decoded outputs is not padding invariance of probability scores.
The frozen model and benchmark policies were not changed after final evaluation.

Quantization reduced model files but did not establish a reliable speed/RSS win;
FP32 remains selected. See [measured quantization](QUANTIZATION-V3.md).
Expanded training added 4,962 new original rows. The family-exclusion control
fell substantially on held-out phrasing; see [data experiment](EXPANDED-DATA-V3.md).
The [multilabel prototype](MULTILABEL-EXPERIMENT.md) fixes a structural shared-value
limitation but regresses ordinary extraction/rejection and was not promoted.

Hashes:

- Model: `14fccd0c69701cb090e80301e05ec5f10e4b506b2f0da56b0ccb97abe78d232e`.
- Selection: `37aebc328073f5c8026aefb8f9e675cfafd971754b5e6135412ce0a311f8bf2b`.
- Docker image: `sha256:fa5f8cb557ba4f3b93a2d548d60887c476bc46b59b43ba47d541721dd9f06323`.
- Portable CPU build ZIP: `60230cc39fd20db114c1f2cd6e371ed45c97ed56d6e148114db620ca4d1f9b49`.

Remote artifacts live below `v3-root` in the protected training directory:
`comparison-stage2`, `bundles/selected-v3`, `final-challenge-container`,
`final-challenge-v2-control`, and `sealed-regression-container`. The portable
build ZIP and receipts are copied to the user's Downloads comparison folder.
Raw checkpoints, predictions and binaries stay out of Git.

After the independent review, future caches were strengthened to include source
implementation, metadata and context-policy hashes. Stage2 used a new union
vocabulary, invalidating previous-stage caches; no stale-cache error was found.
Five counterfactual tests showed public neural predictions did not depend on
oracle forms or hidden world metadata. Earlier truth variants reused unchanged
neural predictions; their older receipts bound only model/public input bytes.

This deliverable extracts assertions. It does not produce truth confidence or
1,000 competition claims. Integrating its changed value parser into native Rust
and evaluating the complete verifier is a separate measured step.
