# Evaluation exposure and historical source scope

Updated after reading main at `e6f687c95e018a3948b0a970325007523190cb43`.

This agent's initial v3 training and quantization experiments did not open
calibration-20000, external-calibration or authored final challenge gold. That
is a statement about those runs' access, **not
team-level blindness**. Main's published
[evaluation-suite report](https://github.com/teodorbalan/VERIDYCT/blob/e6f687c95e018a3948b0a970325007523190cb43/docs/research/evaluation-suite-results.md)
shows that another teammate already evaluated the v3 calibration, sealed and
external worlds and published aggregate scores and some error categories.
Those archive worlds must now be treated as development/previously exposed
evaluation data for team decisions. A later evaluation on them is not a fresh
blind confirmation, even when this agent has never read their raw gold files.
Their scores also belong to that teammate's distinct pipeline and protocol.

The assistant-authored challenge final was withheld throughout parent model
selection. Its SHA256 is
`966b5c7c5061eab4e24c61177eb3994b5e852dec3c955dff973bbd5bf7ff33a0`.
After the stage-2 stack/decoder freeze, the parent explicitly released it for
one CPU evaluation of selected-v3 and the fixed old selected-v2 control. The
selected model hash is
`14fccd0c69701cb090e80301e05ec5f10e4b506b2f0da56b0ccb97abe78d232e`.
This review then aggregated those existing predictions: 11 primary gains and
zero primary regressions. **The authored final is now spent.** No tuning was
performed after its release, and future million-data variants cannot claim
fresh validation from it. See the [paired review](OBSERVABLE-SELECTION-REVIEW-V3.md).
Challenge DEV was repeatedly used for selection and is not independent
confirmation. No final examples or gold forms are included in this note.

The public-practice semantics audit examined the historical worktree base
`e0c2a12`; its `engine.rs` was last changed in
`86d2d7c83f16cdd50391269adb87fd8c871e5721`. Its strict same-day and latest-value
experiments are still reproducible evidence-rule diagnostics. They are **not
benchmarks of current main**. Main at the commit above already contains
`typed.rs`, `temporal.rs` and `knowledge.rs`, with typed unit conversion,
explicit validity scopes and constraint reasoning. Statements about the old
literal comparator must not be presented as missing features of current main.

The old practice numbers and the newer teammate report should not be pooled:
they use different evidence assumptions, extraction methods, splits and labels.
Likewise, a 99% synthetic interval-engine score is not an estimate of arbitrary
competition prose or of the 1,000 generated claims' correctness.
