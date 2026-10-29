# VERIDYCT — three levels of architecture

Ready-to-use PNGs for Edi's slides and video. English diagram copy; Romanian
presentation notes below. Snapshot: `c62c7735998cdbd09628d9840dd8fa319e0f843f`,
29 October 2026. These illustrations explain the implemented design; they are
not screenshots, execution traces, or accuracy measurements.

Each selected PNG is 1672 × 941 pixels, with an opaque background and an
approximately 16:9 aspect ratio. All three were visually inspected; the third
was corrected so generation is sourced from known-true labels, not predictions.

| PNG | Use | What it explains |
| --- | --- | --- |
| [01 — System map](01-system-map.png) | Main architecture slide | Inputs, Rust CLI, shared core, guarded chain, claim generation, atomic output, separate browser adapter and CPU execution boundary. |
| [02 — Extraction and logic](02-extraction-and-logic.png) | Technical demo or parser slide | Semantic roles, rules and native extraction, ownership and dimensions, logical scope, unknowns and provenance. |
| [03 — Verification and generation](03-verification-and-generation.png) | Technical deep dive / jury Q&A | Typed evidence graph, exact program verification, learned estimates, temporal routing, generation from known-true sources, MMR and failure recovery. |

## Pentru Edi

Folosește primul PNG pe slide-ul principal de arhitectură. Al doilea explică
ce se întâmplă cu textul; al treilea este pentru aprofundare și întrebările
tehnice. Pune imaginile la lățimea slide-ului și păstrează proporțiile.
Pentru video, poți face zoom pe câte un bloc; nu încerca să citești toate
etichetele într-un singur cadru.

**01, aproximativ 25 secunde:** „VERIDYCT rulează local, pe CPU. Primește
universul de afirmații și lexiconul, extrage structura, verifică dovezile și
produce rezultatul CSV. Generarea afirmațiilor folosește surse cunoscute ca
adevărate. Interfața web este un adaptor separat; nu presupunem că reproduce
automat toate etapele CLI-ului.”

**02, aproximativ 30 secunde:** „Nu este suficient să recunoaștem numărul 59.
Trebuie să știm cui îi aparține, ce măsoară, moneda, perioada și data.
Parserul păstrează AND, OR și NOT în structură, astfel încât negația să nu
devină accidental o afirmație pozitivă. Exemplul din imagine este ilustrativ.”

**03, aproximativ 35 secunde:** „Separăm ce rezultă exact din dovezi de ceea
ce estimează modelele. Routerul temporal are condiții și limite și păstrează
deciziile protejate. Pentru cele 1.000 de afirmații noi, MMR combină susținerea
cu reducerea repetiției. Scriem întâi rezultatul complet al motorului, apoi
publicăm atomic rafinarea validă.”

## Reading the diagrams correctly

- Solid connectors describe logical data flow, not a promise that every module
  runs on every row. The guarded chain is conditional and enabled in the root
  competition image. Exact proofs, program decisions and missing extraction
  are protected by the current router.
- Rules and the three frozen BiLSTMs are complementary extraction paths.
  Native ONNX inference is not an LLM. Extraction alone does not prove truth.
- `unknown` is the internal three-valued logic state; `unsure` is the output
  label. Statistical confidence and belief bounds are not independently
  calibrated truth probabilities.
- Generation uses explicitly known-true observations. The MMR term uses
  candidate evidence confidence and approximate token overlap, not a semantic
  embedding similarity metric or a second truth test.
- The browser/API uses the core directly. Full parity with CLI model
  enrichment and chain routing is not established by sharing a core library.
- The root image now builds from source and downloads hash-verified frozen
  assets at build time. Runtime execution is offline and CPU-only.
- Official CSV has no document ID. Competition context is disabled rather
  than inferred across unrelated rows. The example sentence is illustrative,
  not a measured parse result or a factual claim about a real product.

## Source map

This set follows the current release, newer than the earlier presentation
text's `0dda354` snapshot.

| Area | Source |
| --- | --- |
| Unified release, checks and limitations | [Parser V3 integration](../../handoffs/parser-v3-integration.md) |
| Build and runtime | [Root Dockerfile](../../../Dockerfile) |
| CLI routing and atomic publication | [CLI](../../../crates/cli/src/main.rs) |
| CLI extraction adapter | [Parser adapter](../../../crates/cli/src/parser.rs) |
| Typed binding | [Structured parser](../../../crates/core/src/structured.rs) |
| Logical program | [Claim program](../../../crates/core/src/claim_program.rs) |
| Exact verification | [Program verification](../../../crates/core/src/program_verification.rs) |
| Hard logic and marginal bounds | [Belief composition](../../../crates/core/src/belief.rs) |
| Evidence and estimates | [Engine](../../../crates/core/src/engine.rs) |
| Router safeguards | [Chain audit](../../handoffs/chain-v3-audit.md) |
| MMR and claim construction | [Claims](../../../crates/core/src/claims.rs) |
| Browser adapter | [HTTP API](../../../crates/api/src/lib.rs) |
| Image generation provenance | [Exact prompts](GENERATION.md) |

## Delivery scope

Task: architecture-png. Requested recipient: Edi; task human owner remains
unassigned. Authorized paths: this folder and its parent index. Acceptance:
three readable PNGs, visual review against the source snapshot, valid links,
commit and publication on a separate presentation branch. No runtime interface
changes. Review focus: labels, arrow direction, text legibility and slide use.

Published separately because the stated 11:00 submission freeze has passed.
This branch adds presentation material; it does not update the submission branch.
