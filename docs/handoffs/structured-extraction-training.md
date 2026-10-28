# Structured extraction training handoff

Task owner: Codex. Authorized by Teodor on 2026-10-28: six concurrent training/test
terminals, all eight A100 GPUs, snapshot before releasing existing GPU workloads.
Human ownership unassigned. Base `d0af169`; isolated branch
`teodorbalan/structured-extraction-training`.

Implementation: [laboratory](../../labs/structured-extraction/README.md).
Acceptance: world-held-out exact JSON extraction, per-kind/context diagnostics,
reproducible checkpoints, CPU export and runtime measurements before adoption.
No change to the existing application/core interfaces is accepted yet.

## Operations

Remote root: `/data/tairo/veridyct-training-20261028` on BENGEE.
Connection uses the existing SSH identity and host-key alias, via its alternate
network route. Credentials are never copied to the repository.

Seven GPU containers and six GPU user services were stopped using their owning
Docker/systemd interfaces at the user's explicit request. Subsequent `nvidia-smi`
showed all eight cards at 4 MiB and no compute processes. Containers, weights,
volumes and unit files remain intact. GPU service dependency consumers may be
unavailable while these services are stopped; no automatic restoration is planned
while training owns the cards.

Protected remote restoration inventory:
`operations/before.json`, `stop-plan.json`, `stop-receipt.json`, saved unit files.
Sanitized restoration instructions: `operations/GPU-SNAPSHOT.md`.
Desktop snapshots:
`C:/Users/Teodor/Desktop/VERIDYCT-training-state-2026-10-28.md` and
`C:/Users/Teodor/Desktop/VERIDYCT-GPU-SNAPSHOT-2026-10-28.md`.

## Delivered results

- Sixteen GPU runs completed in two rounds, monitored through six Orca terminals.
- Three selected char-CNN/BiLSTM members produce a 24,850,029-byte ONNX model.
- Official grouped development exact: 336/390 (86.154%), atomic F1 92.275%.
  Synthetic development: 8,077/8,088 (99.864%).
- After freezing all selected artifacts, sealed exact: 19,127/20,000 (95.635%),
  F1 97.839%; external-sealed: 483/500 (96.600%). Excluding sealed text overlap
  with train/development gives 17,729/18,600 (95.317%). No post-sealed tuning.
- An actual offline container with 2 CPUs / 6 GiB processed the sealed 20,000 in
  113.824 seconds; process peak RSS 748,712 KiB; image 360,077,493 bytes.
- Fourteen independent parser regression tests passed locally under WSL Python 3.12.
- `cargo xtask check`, `cargo xtask test` (23 Rust tests), and Python compilation
  passed. Development input reconstruction and ONNX prediction parity passed.
- Dedicated remote PyTorch 2.8.0+cu128 reports eight CUDA devices and performed
  an actual CUDA tensor operation successfully.
- Round two uses 32,862 training examples; no normalized full text or parent ID
  is shared with its development split. There are 24 unresolved training atom
  alignments, explicitly reported. Sealed and calibration gold are excluded
  from training and selection. Synthetic values never enter the evidence store.

Details: [results](../../labs/structured-extraction/RESULTS.md) and
[numeric receipts](../../labs/structured-extraction/results.json).

## Continuation and boundaries

The frozen image is `veridyct-extractor:selected-v2`; this is an extraction CLI,
not the full competition entrypoint. The Rust solver has not changed. Integration,
temporal truth/evidence evaluation, generation and the combined official checker
remain prerequisites for adoption. No universal 99% accuracy claim is supported.

Local `artifacts/remote-results/selected-v2/` holds the model and frozen runtime.
`artifacts/remote-results/delivery/` holds a 139,008,082-byte Docker image archive
and a 23,150,070-byte build-context archive. Hashes were verified after download.
Server `runs/` and `runs-v2/` preserve all sixteen checkpoints and logs;
`selection-v2/`, `bundles/selected-v2/` and `operations/` preserve selection,
freeze, evaluation, installation and restoration receipts.

Final Desktop report: `C:/Users/Teodor/Desktop/VERIDYCT-training-results-2026-10-29.md`.
All GPUs were idle at completion. The previously stopped seven containers and six
user services remain stopped as requested; their state has not been discarded.

Future quality work should address unsupported-claim rejection, attribute/unit
consistency, antecedent resolution and natural paraphrases. Repeated tuning on
the now-opened sealed data requires a new independent final test.
