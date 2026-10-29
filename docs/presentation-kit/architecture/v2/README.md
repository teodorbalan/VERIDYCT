# VERIDYCT — stack, engine, runtime

**Use this edition for the presentation.** The technology names are now the
main labels, with a short responsibility and a repository module underneath.
Source snapshot: `c62c773`, 29 October 2026. These are explanatory illustrations,
not execution screenshots or benchmark results.

All three PNGs are 1672 × 941 pixels with opaque backgrounds. The final images
were visually reviewed for readable labels, module names and connector direction.
The typed record in image 02 is illustrative, not a measured extraction result.

| Image | The question it answers |
| --- | --- |
| [01 — Technology stack](01-technology-stack.png) | What technologies do we use, and for what? |
| [02 — Inside the Rust engine](02-rust-engine.png) | Which libraries, models and algorithms perform the reasoning? |
| [03 — Repository to runtime](03-build-and-runtime.png) | What gets built, what runs in the competition, and what serves the browser? |

## Pentru Edi: ordinea de prezentare

**01 — Stack, 20 secunde.** „Interfața este HTML, CSS și JavaScript. API-ul
folosește Axum și Tokio. Rust leagă parserul, dovezile și verificarea, iar
ONNX Runtime execută extractorul neural pe CPU. Datele intră și ies prin CSV
și JSON; indexul de dovezi este ținut în memoria procesului.”

**02 — Motor, 30 secunde.** „Regulile și extractorul neural identifică
afirmațiile. Parserul leagă entitatea de valoare, unitate, timp și operator.
Logica verifică aceste structuri în raport cu dovezile. Modelele de arbori și
lanțul temporal intervin condiționat. Generarea pornește din surse explicit
adevărate, apoi MMR reduce repetiția.”

**03 — Execuție, 20 secunde.** „Cargo construiește binarele, iar Docker
împachetează aplicația și modelele înghețate. Execuția de concurs este offline,
pe CPU. Browserul folosește API-ul local. Python și scikit-learn apar în
instrumentele de dezvoltare și export; inferența arborilor rulează în Rust.”

Pune PNG-ul 01 pe slide-ul principal de arhitectură. Folosește 02 pentru
explicația tehnică și 03 pentru întrebările despre reproducibilitate și
deploy. Câte o imagine pe slide, la lățime maximă, cu proporțiile păstrate.

## Stack inventory, verified in the repository

The images summarize these components. The table distinguishes a dependency
from our own algorithm and from a development tool.

| Component | Technology / implementation | Responsibility | Source |
| --- | --- | --- | --- |
| Browser | HTML, CSS, vanilla JavaScript | Upload, inspect, download | [web files](../../../../apps/web) |
| HTTP API | Rust, Axum 0.8, Tokio 1 | Local routes, JSON and async task execution | [API manifest](../../../../crates/api/Cargo.toml), [API](../../../../crates/api/src/lib.rs) |
| CLI | Rust 1.90, edition 2024 | Read files, invoke enrichment, orchestrate core, deadlines and atomic output | [workspace](../../../../Cargo.toml), [CLI](../../../../crates/cli/src/main.rs) |
| Formats | csv, serde, serde_json | CSV records and structured JSON; JSON arbitrary-precision option | [core manifest](../../../../crates/core/Cargo.toml) |
| Lexicon and rules | regex, unicode-normalization; custom Rust parsing | Canonical names, aliases, typed candidates and bounded context | [extraction](../../../../crates/core/src/extraction/mod.rs), [binding](../../../../crates/core/src/structured.rs) |
| Neural extractor | Rust executable, ort 2.0.0-rc.10, ONNX Runtime 1.23.2 | Run the frozen three-BiLSTM ensemble on CPU | [extractor manifest](../../../../crates/extractor/Cargo.toml), [model provenance](../../../../tools/native_parser/provenance.json) |
| Native preprocessing | Rust, regex, fancy-regex, serde | Word/character encoding, grammar candidates, tensor pooling and decoding | [native extractor](../../../../tools/native_parser/README.md) |
| Logical representation | Custom ClaimProgram AST | AND, OR, NOT and slot comparisons with retained scope | [claim_program.rs](../../../../crates/core/src/claim_program.rs) |
| Evidence memory | Custom KnowledgeGraph backed by Rust BTreeMap | Positive/negative constraints, source records and validity scopes | [knowledge.rs](../../../../crates/core/src/knowledge.rs) |
| Exact numbers | num-bigint, num-rational | Exact decimal quantities and dimensional comparisons in the typed path | [typed.rs](../../../../crates/core/src/typed.rs) |
| Logical verification | Custom Rust three-valued logic and belief composition | Resolve programs against labelled constraints; keep hard logic distinct from soft bounds | [verification](../../../../crates/core/src/program_verification.rs), [belief](../../../../crates/core/src/belief.rs) |
| Baseline verifier | Custom Rust Random Forest | Deterministic seeded 96-tree implementation | [forest.rs](../../../../crates/core/src/forest.rs) |
| Frozen verifier | Custom Rust gradient-boosted tree inference, verifier.json | Execute the exported model where applicable | [boosted.rs](../../../../crates/core/src/boosted.rs), [engine](../../../../crates/core/src/engine.rs) |
| Temporal routing | Custom per-key chain and Viterbi | Bounded statistical refinement with protected exact/program/unknown decisions | [kb_chain.rs](../../../../crates/core/src/kb_chain.rs) |
| Claim selection | Custom templates, MMR, token fingerprints | Select 1,000 generated claims from explicit known-true sources | [claims.rs](../../../../crates/core/src/claims.rs) |
| Runtime packaging | Docker, Debian bookworm-slim, Linux amd64 | Bundle native binaries, model assets and CPU libraries; non-root runtime | [Dockerfile](../../../../Dockerfile) |
| Asset integrity | SHA256 at image build; sha2 in project code | Pin model/library assets and checksums | [Dockerfile](../../../../Dockerfile), [extractor manifest](../../../../crates/extractor/Cargo.toml) |
| Development tools | Cargo, rustfmt, Clippy, tests, cargo xtask | Build and check source, docs and contracts | [CI configuration](../../../../.github/workflows/ci.yml) |
| ML development | Python, NumPy, scikit-learn | Verifier experiments, training, export and evaluation | [training](../../../../tools/verifier_lab/train.py), [fold validation](../../../../tools/verifier_folds/run.py) |

## Boundaries to explain accurately

- **An algorithm is not a service dependency.** KnowledgeGraph, Viterbi and MMR
  are project implementations. BTreeMap is an in-memory Rust collection. The
  graph is not an external database product.
- **ONNX is the model format; ONNX Runtime executes it; ort is the Rust binding.**
  The three BiLSTMs propose structured extraction candidates. They do not
  independently establish whether an assertion is true.
- **Rust is the application language.** Native ONNX Runtime and its bundled
  support libraries remain external native dependencies. The project does not
  implement a custom C++/CUDA kernel stack.
- **Neural extraction and tree verification are different model families.**
  Tree-model inference is implemented in Rust; the verifier does not run
  through ONNX. The competition image enables the frozen boosted verifier.
- **Models do not override protected exact logic.** A diagram groups stages
  for readability; actual routing is conditional. Unknown AST outcomes and
  incomplete extraction do not automatically become a statistical verdict.
- **Exact arithmetic has a scope.** It applies to typed numeric comparisons;
  neural scores and the temporal chain also use floating-point arithmetic.
- **The browser has a different adapter.** Shared core code does not establish
  parity with the CLI's native enrichment, model configuration and KB router.
- **Build-time access and runtime access differ.** Docker fetches and verifies
  frozen assets during the build. The competition process runs offline on CPU.
- **CI names describe configured checks.** These assets do not claim a new
  application test run, new accuracy result, or calibrated model probability.

## Revision and review

Task: architecture-png, user-requested revision 2. Same isolated presentation
branch; scope remains images and documentation. Human task owner unassigned;
requested presentation recipient Edi. Runtime interfaces unchanged.

Acceptance: three readable images with explicit technology-to-role mappings,
correct model/runtime separation, reviewed connectors, working source links,
and commit/push on the presentation branch. [Generation prompts](GENERATION.md)
record the image provenance. The original edition is retained one level up.
