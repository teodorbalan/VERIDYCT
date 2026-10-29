# Public practice semantics: what the supplied labels do and do not establish

Owner: research_audit. Scope: the original 1,897-row public practice and lexicon,
plus read-only inspection of the Rust verifier. No final, calibration or sealed
gold was read. Reproduce with [audit_practice_semantics.py](audit_practice_semantics.py);
the compact result is [practice-semantics-v3.json](practice-semantics-v3.json).

The Rust comparison in this document describes the original `d0af169` baseline
used by this isolated experiment. Main subsequently advanced to `e6f687c`, adding
typed normalization, explicit temporal constraints and a native neural adapter.
The baseline's limitations below must not be attributed to that newer implementation.

The `form` records **what the sentence asserts**, including its false values.
It is not a table of corrected facts. Extraction and truth judgement are separate
tasks. There are 1,581 true, 277 false and 39 unsure rows, containing 2,402 atoms.
There are 430 compound rows: 351 true, 75 false and 4 unsure. A false compound row
does not tell us which individual atom is false; assigning its label to every
atom would fabricate supervision.

All 62 subjects and 514 declared subject/attribute pairs (321 distinct attribute
names) occur, with zero
out-of-lexicon pairs. Every pair has at least one labelled-true observation.
The lexicon declares names, aliases and attributes; it does **not** declare value
types, all allowed object names, complete fact values or validity intervals.
Every pair happens to have one observed value kind in this practice sample.
That is a useful empirical prior, not a new type guarantee for arbitrary input.

| Value kind | Observed pairs | Atoms in true rows | In false rows | In unsure rows |
| --- | ---: | ---: | ---: | ---: |
| quantity | 210 | 826 | 178 | 24 |
| money | 49 | 223 | 42 | 3 |
| duration | 42 | 195 | 32 | 2 |
| name | 43 | 184 | 23 | 2 |
| percent | 43 | 169 | 29 | 3 |
| date | 60 | 144 | 19 | 2 |
| boolean | 55 | 139 | 28 | 7 |
| version | 12 | 118 | 9 | 1 |

## Evidence availability is not an independent truth oracle

The audit removes the current row from its evidence pool, uses supplied forms
as an extraction oracle, and looks only at other labelled-true observations of
the same subject/attribute. The strict comparator mirrors Rust: exact kind,
unit, currency, billing period and value; inequalities are incomparable.
One unambiguous different value triggers `false`, all supported atoms trigger
`true`, and everything else remains unresolved. These are deliberately limited
evidence rules, **not end-to-end system accuracy or organizer semantics**.

| Evidence rule | Actual label | Predict true | Predict false | Unresolved |
| --- | --- | ---: | ---: | ---: |
| Other true rows on the same page date | true | 104 | 3 | 1,474 |
| Same date | false | 0 | 21 | 256 |
| Same date | unsure | 0 | 0 | 39 |
| Latest true observation on or before page date | true | 822 | 294 | 465 |
| Latest prior | false | 23 | 186 | 68 |
| Latest prior | unsure | 8 | 2 | 29 |

Only 21/277 false rows have a contradiction under the strict same-day rule.
For 256/277 it supplies no verdict. Carrying observations forward increases
coverage but wrongly contradicts 294 true rows and supports 23 false ones.
Its extra coverage is not evidence that the persistence assumption is correct.
The full run contains additional labelled/unlabelled rows, so these figures
describe public-practice information availability, not an upper bound on the
competition's achievable performance.

Moreover, all asserted values of 128 false rows have exact true matches
somewhere else in practice; 78 false rows have such matches on or before their
page date. The corresponding counts for unsure are 18 and 8. Having once seen a
value as true is therefore insufficient to determine a row's label.

There are 88 identical-form groups spanning different labels (263 rows), and
four identical-normalized-text groups spanning different labels. Examples:

- p-108 and p-1217 both say Hooly Search has 540,000,000 monthly users. The
  February 25 row is true; the June 16 row is false.
- p-152/p-1770 state that Pixel Fold's hinge is rated for 200,000 folds and are
  true in June; the identical sentence p-608 is unsure on August 18.
- p-1459/p-1474 state Gemini's median response is 2.1 seconds, true in November
  2025 and false in August 2026.

Text-only verdict learning cannot distinguish these identical inputs. The
verifier needs temporal/contextual evidence beyond the extractor's typed form.
An unknown validity interval should remain unknown, rather than be completed by
the last observed date or by the language model's background knowledge.

## Apparent same-day conflicts expose representation problems

There are three raw-JSON same-day multivalue groups, not three proven factual
contradictions:

- Hooly AI Pro free trial: p-55 gives 2 weeks; p-269/p-856/p-1841 give 14 days.
  These are equivalent durations. Unit conversion removes this raw difference.
- Hooly's Series A lead: p-165 and other rows use `Raviqa Capital`, while p-1088
  uses `Raviqa`. Both rows are labelled true. This is evidence of a possible
  short-name equivalence; the lexicon does not list either target as a subject,
  so an authoritative alias cannot be obtained from that file alone.
- Hooly I/O 2026 date: p-168 records year-only `2026`, while p-169 records
  `2026-03-24`. Both are true. The values differ in precision, not necessarily in
  event identity. The generation contract still requires the stated precision
  exactly; extraction should preserve it.

The latter two groups produce the three wrong same-day contradictions in the
strict leave-row-out rule: p-1088, p-168 and p-169. They explain why raw string
inequality must not automatically establish contradictory facts. Similarly,
252 pairs have multiple distinct true JSON values across dates; that count
mixes actual changes with units, names and precision changes.

## What a relation means here

A subject sharing an attribute with another subject creates a schema similarity,
not a factual relationship. A typed name assertion such as `Hooly Cloud /
reliability_lead / Holdan` is a directed named-value relation. Numeric attributes
remain facts about a subject; equal prices do not create an identity relation.

Of 209 name-valued assertions, only 40 target a name or alias present as a
lexicon subject. The other 169 target 24 distinct names outside that inventory;
there are 35 distinct object strings overall. Examples include Nimbus Cloud,
Berlin, Gavin Bellson and Raviqa Capital. Therefore subject recognition can be
closed to the public subject list while name-valued objects cannot be restricted
to that same list without losing valid supplied forms. Relations are not merely
edges among the 62 listed subjects.

The five `fact`, `compare`, `change`, `at_event`, `relation` forms describe newly
generated competition entries. They are not five mutually exclusive sentence
classes that describe every input row. Practice forms are lists of typed atoms;
one sentence can contain several. The [claim contract](../../contracts/claim-forms.md)
and [value contract](../../contracts/value-forms.md) additionally impose stricter
surface requirements on generated entries than those seen in practice.

## Existing Rust behavior and next steps

[engine.rs](../../crates/core/src/engine.rs) correctly preserves known labels and
does not promote false compounds or unlabelled model predictions to true source
evidence. It separately extracts assertions, consults true observations on or
before the query date, and uses decisive same-day evidence before its statistical
Random Forest fallback. Exact text **and date** memory is explicitly familiar
training evidence. Its scores are not independently calibrated.

Its `compatible_values` currently requires literal equality of units and name
strings and compares partial dates as strings. The raw distinct-value guard
also precedes normalization. The three cases above show why a typed comparison
layer should distinguish equivalent, incompatible, disjoint and unresolved
values. A date precision overlap or an unconfirmed alias needs uncertainty,
not a false verdict. Inference-time relation and timeline provenance should
retain row IDs, publication date, any explicit asserted time and known label.

The priority is a measured typed temporal verifier and independent label
evaluation, alongside extraction improvements. More synthetic extraction rows
alone cannot teach hidden validity intervals or identify the false atom in a
compound. No production behavior was changed by this audit.

## Reproduction

```sh
python labs/structured-extraction/audit_practice_semantics.py \
  --practice data/practice.csv --lexicon data/lexicon.json \
  --out artifacts/practice-semantics-new
```

The script emits hashes, a summary and leave-row-out evidence details for every
row. Equality counts deliberately use exact JSON; they can differ from the
older notebook's unit-normalized counts. Source files remain unchanged.
