# Original BENGEE GPU workloads restored

Owner: root Codex. Teodor explicitly requested restoring every model stopped for
VERIDYCT training. Completed and verified on 2026-10-29 at 07:34:26 UTC.
This is restoration of the original services, not deployment of a new model.

The protected original stop plan contains seven Docker containers and six user
systemd units. All thirteen were started through their existing owning managers.
Before and after startup, container Config/HostConfig and saved unit contents
matched the original snapshot. No image, weight, volume, unit, port, GPU allocation
or restart policy was replaced. Training artifacts remain preserved.

| GPU | Restored workloads |
| --- | --- |
| 0-3 | Qwen3.6-35B-A3B, tensor parallel across the original four GPUs |
| 4 | MOSS, medical avatar renderer, medical realtime |
| 5 | Harrier candidate, EmbeddingGemma2, MOSS, Parakeet STT, Qwen3 TTS |
| 6 | LightOnOCR, retrieval embedding/reranker, n8n text embeddings |
| 7 | Qwen GPU7 Eagle service |

Final checks: seven containers running, six units active/running, zero restart
counts, twelve HTTP health endpoints returning 200, and realtime WebSocket
upgrade returning 101 followed by a normal close without audio/chat input.
Authenticated checks used existing protected credentials locally; no credentials
were printed or copied. NVIDIA process UUIDs plus process ancestry confirmed
all thirteen workloads use their original GPU allocation.

These are startup/readiness checks, not a new end-to-end quality or load benchmark.
The restored services may now receive their ordinary traffic. Do not reclaim
these GPUs for another training round without a new instruction from Teodor.

Protected receipts live under
`/data/tairo/veridyct-training-20261028/operations/restore-20261029T072724Z`:
`receipt.json`, `verification-final.json`, protected pre-restoration inspection
and startup logs. The original `before.json`, `stop-plan.json`, `stop-receipt.json`
and saved units remain intact. A sanitized Romanian report is on Teodor's Desktop.
