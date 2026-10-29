# Architecture v2: generation provenance

User requested clearer technologies, roles and stack boundaries. Generated with
the built-in image tool, using the three original PNGs as edit targets and style
references. Source verified against code snapshot `c62c773`; presentation-only
assets. No benchmark results or runtime behavior changed.

## Image 1

Redesign the supplied VERIDYCT infographic into a much clearer second edition of the SAME team's technical architecture series. The supplied image is an EDIT TARGET and palette reference, not a layout to preserve: completely rebuild its layout as specified below. Preserve the brand VERIDYCT / TEAM JEV and warm ivory, charcoal, violet and mint color identity. Deliver one finished landscape PNG, approximately 16:9, target 2560x1440 or greater if possible. Large projector-readable English typography, very crisp spelling, precise alignment, restrained premium editorial design. Use large technology names as the visual anchors. Role labels are secondary, module paths are tertiary. Limit icons to small meaningful line symbols. Use clean flat panels, whitespace, 3 or 4 clear type sizes, no tiny paragraphs, no 3D, no glow, no decorative network. Every technology below is source-verified; do not add frameworks, vendors, GPUs, metrics or databases. Do not repeat the title as a decorative block. Footer small but legible: "JEV / Teo · Edi · Mihai  |  Code snapshot c62c773  |  Architecture v2". Make the technology stack immediately understandable without a narrator.
IMAGE 01. Title exactly "The technology stack". Subtitle exactly "What we use. Where it runs. What it does." Small upper-right series marker "01 / STACK".

Design a spacious horizontal matrix with three column headings "LAYER", "TECHNOLOGY", "RESPONSIBILITY". Technology column is widest and has the biggest typography, a series of elegant wordmark-like labels, not obscure icons. Six clean horizontal rows with enough height:
Row 1 label "BROWSER", technology "HTML · CSS · JavaScript", role "Upload CSV · inspect evidence · download results", small module "apps/web".
Row 2 label "HTTP API", technology "Rust + Axum + Tokio", role "Local HTTP / JSON service and async jobs", small module "crates/api".
Row 3 label "SOLVER", technology "Rust 1.90 / Edition 2024", role "Parsing · evidence · logic · verification · MMR", small module "crates/core + crates/cli".
Row 4 label "NEURAL INFERENCE", technology "ONNX Runtime 1.23.2", secondary tech "Rust ort binding · 3 frozen BiLSTMs", role "Convert text into typed assertion candidates", small module "crates/extractor".
Row 5 label "DATA & MEMORY", technology "CSV · JSON · Rust BTreeMap", secondary tech "serde / serde_json · in-memory evidence index", role "Input / output formats and source-linked facts".
Row 6 label "BUILD & SHIP", technology "Cargo + Docker + Debian", role "Native Linux amd64 binaries · CPU container".

Below the matrix, two compact side-by-side route ribbons, short readable arrows:
"LOCAL WEB" then "Browser → Axum API → Rust core"
"COMPETITION" then "CSV → Rust CLI + extractor → Rust core → CSV".
Put a concise caption beneath the web ribbon "Full CLI enrichment is a separate execution path."

Bottom dark band: "CPU ONLY   |   OFFLINE COMPETITION RUN   |   2 CPU / 6 GiB   |   UID 10001". One short line immediately above or inside the band "Frozen neural model for extraction; Rust algorithms for reasoning." Keep this entire image around 180 words, very legible. Do not make it a generic flowchart; it is a precise visual stack inventory.

## Image 2

Redesign the supplied VERIDYCT infographic into a much clearer second edition of the SAME team's technical architecture series. The supplied image is an EDIT TARGET and palette reference, not a layout to preserve: completely rebuild its layout as specified below. Preserve the brand VERIDYCT / TEAM JEV and warm ivory, charcoal, violet and mint color identity. Deliver one finished landscape PNG, approximately 16:9, target 2560x1440 or greater if possible. Large projector-readable English typography, very crisp spelling, precise alignment, restrained premium editorial design. Use large technology names as the visual anchors. Role labels are secondary, module paths are tertiary. Limit icons to small meaningful line symbols. Use clean flat panels, whitespace, 3 or 4 clear type sizes, no tiny paragraphs, no 3D, no glow, no decorative network. Every technology below is source-verified; do not add frameworks, vendors, GPUs, metrics or databases. Do not repeat the title as a decorative block. Footer small but legible: "JEV / Teo · Edi · Mihai  |  Code snapshot c62c773  |  Architecture v2". Make the technology stack immediately understandable without a narrator.
IMAGE 02. Title exactly "Inside the Rust engine". Subtitle exactly "Libraries do the plumbing. Models extract. Explicit logic checks evidence." Series marker "02 / ENGINE".

Top small legend with three color-coded pills: "LIBRARY", "LEARNED MODEL", "CUSTOM RUST ALGORITHM".

Main body: four large equal panels across a 2 x 2 grid, connected with clear stage numbers 01,02,03,04, not a tangle. Each panel shows an exact role title, a large technology label, one module tag, and short bullets. Keep enough whitespace.

Panel 01:
Title "READ & RESOLVE"
Large tech "regex + Unicode normalization"
Module "extraction/ · structured.rs"
Bullets "Aliases → canonical entities" / "Owner · attribute · typed value" / "Units · dates · logical scope".
At bottom small separate violet subcard:
"3 × BiLSTM / ONNX Runtime"
"word + character features → candidates"
Tag "LEARNED MODEL · crates/extractor".
Make clear these are complementary parsing paths, via a small label "Rules + native neural candidates".

Panel 02:
Title "COMPILE & STORE"
Large tech "ClaimProgram + BTreeMap"
Module "claim_program.rs · knowledge.rs"
Bullets "AST: AND · OR · NOT · comparisons" / "Source-linked positive / negative constraints" / "Evidence indexed in Rust memory".
At bottom small library strip:
"num-bigint + num-rational"
"Exact typed numeric comparisons".
Use a tiny illustrative typed record with readable fields "entity | attribute | value | date".

Panel 03:
Title "VERIFY & ROUTE"
Large tech "Exact logic + tree models"
Module "engine.rs · boosted.rs · kb_chain.rs"
Bullets "Three-valued logic + belief composition" / "Random Forest / frozen boosted verifier" / "Guarded temporal chain + Viterbi".
At bottom a clearly separated short line "Exact proofs and logical decisions stay protected."
Then three tasteful chips "TRUE", "FALSE", "UNSURE".
Small caption "Statistical scores are not calibrated probabilities."

Panel 04:
Title "GENERATE & SELECT"
Large tech "Templates + MMR"
Module "claims.rs"
Bullets "Explicitly known-true sources only" / "1,000 new claims" / "Token fingerprints / approximate Jaccard".
At bottom a clearly rendered formula on two lines:
"0.78 × evidence confidence"
"− 0.22 × maximum token overlap".

Connector rules: 01 flows to 02; 02 flows to 03. A SEPARATE mint source connector from panel02 to panel04 is labelled "Known-true sources". Absolutely no connector from panel03/verdicts to panel04. If connectors would cross text, use short matching mint ports labelled "KNOWN TRUE" on panels02 and04 instead of a long wire. No vague storage database icon. Footer callout "Extracting a claim and proving it are separate operations." Preserve scientific clarity rather than cramming more labels.

## Image 3

Redesign the supplied VERIDYCT infographic into a much clearer second edition of the SAME team's technical architecture series. The supplied image is an EDIT TARGET and palette reference, not a layout to preserve: completely rebuild its layout as specified below. Preserve the brand VERIDYCT / TEAM JEV and warm ivory, charcoal, violet and mint color identity. Deliver one finished landscape PNG, approximately 16:9, target 2560x1440 or greater if possible. Large projector-readable English typography, very crisp spelling, precise alignment, restrained premium editorial design. Use large technology names as the visual anchors. Role labels are secondary, module paths are tertiary. Limit icons to small meaningful line symbols. Use clean flat panels, whitespace, 3 or 4 clear type sizes, no tiny paragraphs, no 3D, no glow, no decorative network. Every technology below is source-verified; do not add frameworks, vendors, GPUs, metrics or databases. Do not repeat the title as a decorative block. Footer small but legible: "JEV / Teo · Edi · Mihai  |  Code snapshot c62c773  |  Architecture v2". Make the technology stack immediately understandable without a narrator.
IMAGE 03. Title exactly "From repository to runtime". Subtitle exactly "One codebase. A CPU submission and a local web workbench." Series marker "03 / DELIVERY".

Top full-width shallow "DEVELOPMENT & BUILD" band with four equally sized stages and labelled connecting arrows:
"Cargo" / "Rust 1.90 · locked dependencies"
"Quality checks" / "rustfmt · Clippy · tests"
"GitHub Actions" / "Windows · Linux · macOS"
"Docker build" / "Multi-stage · SHA256-checked assets".
This band represents delivery tooling, not a runtime request pipeline.

Middle two large side-by-side panels.

LEFT panel takes 60% width. Header "COMPETITION / OFFLINE".
A clear contained runtime stack with four prominent boxes in sequence:
"CSV + lexicon.json"
arrow to "veridyct CLI" / "Rust orchestration · deadlines"
arrow to "Native extractor" / "Rust + ort + ONNX Runtime"
arrow to "veridyct-core" / "Evidence · logic · verifier · guarded chain".
Then one broad output card "output.csv" / "Target verdicts + 1,000 generated claims".
Use simple arrows in a vertical or serpentine path; no crossing. Beside the extractor box place a file chip "model.onnx / frozen BiLSTM ensemble". Beside the core box place a file chip "verifier.json / frozen tree model".
At bottom inside left panel, dark runtime chips "Debian bookworm-slim", "Linux amd64", "2 CPU / 6 GiB", "UID 10001". Small line "Atomic output: complete engine result first; valid refinement replaces it."

RIGHT panel takes 40% width. Header "LOCAL WORKBENCH".
Vertically stack four broad boxes with labelled arrows:
"HTML + CSS + JavaScript" / "apps/web"
arrow labelled "HTTP / JSON" to
"Axum + Tokio" / "crates/api"
arrow to
"Shared Rust core" / "crates/core"
arrow to
"Inspect evidence + download CSV".
A clearly separate neutral caption underneath "The API calls the core directly. Full CLI enrichment and routing parity is not verified." Do not draw a connector through the native extractor for this local web path.

Bottom slim mint band "DEVELOPMENT-ONLY ML TOOLS". Exact copy "Python + scikit-learn → frozen verifier export → Rust tree inference". Second line "Training and research tools are separate from the offline application runtime."
Small footer caption "Native CPU libraries are bundled. Competition inference needs no network or GPU." Keep large readable technology names, clean module-to-runtime mapping and no fake runtime screenshots.

## Final typography correction, image 01

Repair ONLY the malformed column-heading word in the supplied VERIDYCT technology stack infographic. The middle table header must read exactly "TECHNOLOGY" (letters T E C H N O L O G Y), in clean ordinary bold sans-serif uppercase without fused or overlapping glyphs. Clear and re-typeset only that word inside the pale violet header row between "LAYER" and "RESPONSIBILITY". Preserve every other detail: all rows, exact technology labels, typography sizes, colors, paths, footer, 16:9 framing and all arrow directions. Do not redesign or add anything. Return the complete PNG.
