# Official semantics: input assertions, generated entries, and temporal truth

Owner: factorized worker; requested by the coordinator on 2026-10-29. This is a
read-only contract/code investigation. No official fixtures, Rust behavior,
calibration gold or final challenge labels were changed or consumed.

The live official repository HEAD was checked with `git ls-remote` and remained
`7c32449d878efde84aa1f38ce179778d1e2c4a48`, matching the preserved organizer
snapshot. References below name repository files and their source line numbers.

## The main distinction

There are two separate tasks, and three different enumerations:

| Concept | Meaning | Authority |
| --- | --- | --- |
| Input assertion / atom | `subject`, `attribute`, typed `value`; several atoms can belong to one input row | [Runtime contract](../../contracts/README.md), lines 9–18 |
| Eight value kinds | quantity, money, percent, date, version, duration, name, boolean | [Value schema](../../contracts/claimed_value.schema.json), lines 5–10 |
| Five value operators | eq, lt, le, gt, ge; eq is the default for input values | [Value schema](../../contracts/claimed_value.schema.json), lines 24–26 |
| Five generated entry families | fact, compare, change, at_event, relation | [Runtime contract](../../contracts/README.md), lines 38–46 and 58–72 |

The five generated families are **not a guarantee that every unlabelled input
sentence is one of five linguistic templates**. Runtime input has `id`, `text`,
`date`, `label` and its own lexicon; it has **no `form` column**. The image may
contain practice forms. This is explicit at `contracts/README.md:29`.

A neural classifier selecting a subject/attribute pair for a value is an atom
extractor. It is not yet a five-family entry interpreter, a temporal truth
evaluator, or the organizer's deterministic referee.

## Atoms and graph edges versus the `relation` family

An atom such as `(Hooly, cto, name(Bertram Gilfoil))` states that the attribute's
value is a name. In a visualization it naturally becomes a named edge. That alone
is a direct fact, not the generated `relation` operation.

A generated relation performs a temporal two-hop lookup:

```text
subject --link--> target --attribute--> value

relation(subject, link, target, attribute, value) is true when
there is a time t at which both
    subject.link(t) = target
and target.attribute(t) = value.
```

This is a formalization of [claim forms](../../contracts/claim-forms.md), line 166.
The as-of date does not control a relation. The link naming the target at one time
and the target holding the value at an unrelated time is insufficient. The two
facts must hold together. If complete hypothetical histories show no overlap,
the relation is false; if the data gives no way to determine overlap, it is not
proven by those observations.

The **text need not name the target**. It must name the source subject, contain
the link attribute's prescribed relation words, and state the value in the same
sentence (`claim-forms.md:168`). Thus “The CTO of Hooly joined on 1 July 2026” can
express a form whose target is Bertram Gilfoil. “Bertram Gilfoil joined Hooly on
1 July 2026” does not express that relation form: the relation words are absent
(`claim-forms.md:174–178`). “Chief technology officer” does not replace the
prescribed `CTO` relation words for that entry.

The link must be an attribute of the source; the second attribute belongs to the
target. The public lexicon provides names/aliases and permitted attributes, not
a general-purpose ontology with declared value kinds for each attribute. A
training-observed unit/type map is therefore an inferred prior, not the official
schema. Entry fact references must resolve against the supplied lexicon
(`contracts/README.md:70`); internal graph IDs are not valid replacements.

## What makes an input label true, false or unsure

The row is judged **on the date of its page** (`contracts/README.md:13–17`). The
published rule says false if at least one stated value is false; unsure if the
dataset itself provides no means to tell; true otherwise. A useful formalization
for rows whose atoms have determinate truth states is:

```text
any false atom                     -> false
no false atom, at least one unknown -> unsure
all stated atoms true              -> true
```

The first case takes priority: one false assertion and one unknown assertion
still include at least one false assertion. An input `form` records **what the
text asserts**, including a false stated value. It must not be overwritten with
the value the world actually holds.

Important limits:

- A false multi-atom row does not identify which atom is false. Its remaining
  atoms cannot all be negated, nor all promoted to true facts.
- An extractor's failure to understand a sentence is not proof that the
  organizer's label is unsure. Model abstention and dataset unknowability differ.
- Empty extraction is not proof of true by an empty conjunction. The extraction
  may have missed an assertion; the contract does not publish an empty-atom rule.
- A high extraction score is not a probability that the stated assertion is true.
- Web knowledge and model background knowledge are not Hooly evidence:
  [UPSTREAM.md](../../UPSTREAM.md), lines 9–11.

## Each generated family has a different time scope

Let `V(s,a,t)` mean the universe's value of subject `s`, attribute `a`, at time
`t`. This notation explains the contract; it is not a claim that the public
files expose the referee's complete timeline or database representation.

| Family | Truth condition / time scope | Source |
| --- | --- | --- |
| fact | `V(s,a,2026-10-29) = value` | `claim-forms.md:21` |
| compare | Compare two values on 2026-10-29, with compatible kind/unit/currency/period | `claim-forms.md:54–66` |
| change | There exist earlier/later times holding `from` and then `to`; not tied to as-of | `claim-forms.md:119–127` |
| at_event | The value holds on the date supplied by the named event's date fact | `claim-forms.md:146–148` |
| relation | Both hops hold at a common time; not tied to as-of | `claim-forms.md:166–168` |

For compare, the new value holds on the day it changes (`claim-forms.md:54`). A
change does not require the two observations to be adjacent or the `to` value to
remain current on 29 October; the stated rule only requires temporal ordering.

**Page dates are not declared validity boundaries.** A true observation on
1 March and another on 1 June do not establish that the first value persisted
until 31 May, or that the transition happened on 1 June. The public input schema
contains no `valid_from`/`valid_to` fields. Explicit validity intervals present
inside an archive generator's gold are private generator state, not a runtime
input guarantee. Intervals explicitly stated in public text may be evidence, but
must actually be interpreted and supported rather than silently imported from gold.

The contract also does not guarantee CSV ordering by page, a previous-row
antecedent, a maximum coreference distance, a closed set of sentence templates,
or that the runtime lexicon is byte-for-byte the practice lexicon. It promises
the runtime's own lexicon. A permanently fixed 514-output classifier must detect
lexicon changes; current counts are properties of the supplied practice data.

## Value semantics and strict entry restrictions

The referee is deterministic (`value-forms.md:3–5`), but its complete
implementation/base is not present in the public starter. The published
text grammar is more specific than general English semantics:

- Units convert within a dimension: 1 GB is 1,000 MB, 14 days is 2 weeks, and
  12 months is 1 year. Months/years do not convert to a fixed number of days.
  Sources: `value-forms.md:18–19,157–177`.
- Counted nouns are singularized, but two different nouns are not automatically
  interchangeable. “24 engineers” is unit `engineer`, not silently `employee`.
  Sources: `value-forms.md:58–75`.
- Prices require the same currency and billing period for comparison. EUR/USD
  exchange conversion and month/year billing conversion are not authorized.
  A missing period means a one-off price, not an unknown period.
  Sources: `claim-forms.md:66`, `value-forms.md:77–88`.
- For generated entry text/value matching, dates preserve written precision.
  A day does not state the corresponding month-valued claim. This is not an
  input truth inequality rule; see the practice evidence below. Versions compare
  as written: `2.3` is not `2.3.0`.
  Sources: `value-forms.md:121,146`.
- Input value operators have genuine semantics: “over 10,000” is a strict
  lower bound, not an exact 10,000. An exact world value of 12,000 supports that
  lower-bound statement; a lower-bound observation alone does not prove an
  exact 12,000. Source: `claimed_value.schema.json:5,24–26`.
- **Generated entry values contain no `op` at all**, even explicit `eq` is
  forbidden by `entry.schema.json:156–163`. Only the `compare` form has an op,
  limited to gt/lt/eq (`entry.schema.json:204–209`). ge/le are not compare entries.
- Approximations, ranges, ambiguous numeric separators and some invisible
  characters do not state a value under the published text reader.
  Sources: `value-forms.md:14–20,23–29`.
- Exact generated facts/at_event/relations must not have a second value of the
  claim's kind or an independent date/time qualifier in their claim sentence.
  Other kinds may coexist: a monthly price and a yearly price are distinct.
  Source: `claim-forms.md:14` and its fact examples.
- Generated compare text must put left subject, approved phrase, right subject
  in that order. It states no number/value/date outside protected entity names.
  Names and Booleans cannot compare, and a fact cannot compare with itself.
  Source: `claim-forms.md:54–71`.
- Boolean values are polarity; generated Boolean entries additionally require
  the attribute's literal words under the allowed spacing/hyphen/case rules.
  “SOC 2 audit” is not the required words “SOC 2 certified”.
  Sources: `claim-forms.md:15–16,43–51`, `value-forms.md:190–196`.
- Generated entries cannot borrow a subject from another sentence. This is a
  rule for output entry validity, not proof that input rows never use anaphora.
  Source: `value-forms.md:12`.

JSON schema validation is necessary but insufficient. For example, the general
entry schema permits a `tag` of false (`entry.schema.json:44–50`), but the runtime
submission contract requires every generated claim to be true
(`contracts/README.md:46–47`). A schema-valid unknown attribute can still fail
lexicon resolution. Passing `scripts/check.sh` does not execute the full text,
form and lexicon referee: the claim check only asks that `form` parses as a JSON
object, alongside basic type/text/label/confidence checks
([check_output.py](../../scripts/check_output.py), lines 53–83).

## Practice evidence that prevents overgeneralizing the output grammar

These are public practice rows already available for development, not reserved
archive evaluation labels:

| Evidence | Consequence |
| --- | --- |
| `p-1` is true with `Holdan.joined = 2026-01-12`; `p-46` is true with the same attribute valued `2026-01` | A coarse input date can be true alongside a day value. Do not mark them contradictory merely because strings/precision differ. This does not by itself establish all partial-date ordering or conflict rules. |
| `p-728`: `Live from November 2025` has `Hooly Gmail.launched = 2025-11` | Input forms can require an implicit subject. Requiring a named subject in every input sentence would reject supplied practice data. The row alone does not reveal a guaranteed antecedent algorithm. |
| `p-168`: `Hooly I/O 2026 and Gemini 2.0` includes event `date = 2026` | A title/name can contribute an input assertion although generated-entry ambiguity checks protect the numbers in required entity names. |
| `p-69` and `p-77` concern Hooly Maps Day; `p-290` concerns Hooly Maps | Substring matching must not turn the event into the product or company. `value-forms.md:12` explicitly assigns a nested name to the longer entity; the lexicon contains both Maps and Maps Day aliases. |

Source: [practice.csv](../../data/practice.csv), lines 2, 47, 70, 78, 169,
291 and 729; [lexicon.json](../../data/lexicon.json). The row IDs identify each
example independently of formatting. These observations justify explicit
handling and tests, not invention of a hidden world history.

## Twenty minimal expectations derived from the contract

These are reasoning/acceptance examples, **not executions of the unavailable
official referee**. Toy truth assumptions are explicit and are not asserted to
be facts about actual Hooly. Text-valid means the stated form can be expressed;
it does not establish the form's truth in the hidden universe.

| # | Input or generated example / explicit assumption | Expected result |
| --- | --- | --- |
| 1 | Input row has two atoms known true on its page date | true |
| 2 | Input row has one true and one false atom on its page date | false |
| 3 | Input row has one false atom and one undecidable atom | false |
| 4 | Input row has one true atom and another the dataset gives no means to decide | unsure |
| 5 | Toy base says exact count 12,000; input asserts `quantity(10000,customer,gt)` | true for that atom; do not change its asserted 10,000 threshold to 12,000 |
| 6 | Only a bound `count > 10,000` is known; input asserts exact 12,000, with no other evidence | insufficient to infer exact 12,000; unsure under the stipulated evidence |
| 7 | Value text `1 GB`; claimed quantity is 1000 MB | value matches after conversion |
| 8 | Value text `30 days`; claimed duration is 1 month | does not match; no fixed day/month conversion |
| 9 | Value text `v2.3`; claimed version is `2.3.0` | does not match |
| 10 | Value text `12 March 2026`; claimed date value is `2026-03` | does not state that month-precision value |
| 11 | Generated fact form is AI Pro price EUR59/month; text `Hooly AI Pro costs €59 per month.` | text-valid; true only if that value holds on 2026-10-29 |
| 12 | Same form, text `Hooly AI Pro is our plan. It costs €59 per month.` | invalid: named subject and value are in different sentences |
| 13 | Same form, text `Hooly AI Pro costs over €59 per month.` | invalid for exact entry; adding value.op is also schema-invalid |
| 14 | Same monthly form, text `Hooly AI Pro costs €59.` | invalid: text gives a one-off price |
| 15 | Compare form Workspace.price gt AIPro.price, text `Hooly Workspace costs more than Hooly AI Pro.` | text-valid; needs compatible values and actual gt on 2026-10-29 |
| 16 | Same compare, text `Hooly Workspace costs €100 more than Hooly AI Pro.` | invalid: comparison sentence states a numeric value |
| 17 | Change form AIPro.price from EUR49/month to EUR59/month; text `Hooly AI Pro went from €49 per month to €59 per month.` | text-valid; true if those values held at ordered times, even if neither is current |
| 18 | At-event form Gemini.languages=12 at I/O; text `Hooly Gemini spoke 12 languages at Hooly I/O 2026.` | text-valid; event date controls the truth query, not page/as-of date |
| 19 | Relation form Hooly/cto/Bertram Gilfoil/joined/2026-07-01; text `The CTO of Hooly joined on 1 July 2026.` | text-valid without naming Bertram; true only when the two facts overlap in time |
| 20 | Same relation text/form, but a complete toy history says the CTO link ends before the target's asserted attribute value ever holds | false semantic claim despite valid text; separate historical existence of both edges is insufficient |

## What our Rust MVP actually implements

This is team code, not organizer authority:

- Only rows labelled true enter the trusted observation pool:
  [engine.rs](../../crates/core/src/engine.rs), lines 170–181 and 235–249.
- Decisive atom support/contradiction uses unambiguous **same-day** observations;
  older observations are retained as context but not a proven interval:
  `engine.rs:281–299,351–383`.
- `compatible_values` declines decisive comparisons for non-eq operators and
  differing literal unit/currency/period fields. It does not implement the full
  public unit-converting/bound entailment semantics: `engine.rs:986–1003`.
- Without decisive evidence, the seeded Random Forest and confidence thresholds
  choose an estimate or abstention: `engine.rs:313,359–383`. This is not equivalent
  to the deterministic hidden truth base.
- The generator builds changes from ordered trusted observations, and relations
  only from matching observation dates. This avoids fabricating validity intervals
  but can miss valid relations whose real intervals overlap:
  [claims.rs](../../crates/core/src/claims.rs), lines 158–194 and 304–345.
- Its numeric conversion helper covers storage and fixed durations, but omits
  several published dimensions and month/year conversion:
  `claims.rs:523–543`. Its partial-date prefix equivalence in `same_value`
  (`claims.rs:508–516`) is a team implementation choice, not a published guarantee
  of the hidden truth comparison for every partial-date case.

The extraction laboratory's percentages therefore cannot be called truth-label
accuracy, generated-entry validity, or the competition score. The next semantic
work should separately measure atom extraction, value equivalence/bounds,
time-grounded entailment, and entry text/form validity.

## Thin spots the public contract does not resolve

The starter does not publish the full referee implementation, its hidden base,
the complete numerical scoring formula, precedence for conflicting trusted
observations, a general proof system deriving truth from arbitrary prose, exact
timeline storage/end-boundary conventions, or every partial-date ordering case.
The lexicon has no per-attribute declared unit/type schema. The supplied archive's
worlds, ground-truth validity intervals, context pointers, paraphrase families and
expected values are generator choices; none silently expands the official API.

Where those choices are useful for development, record them as assumptions and
test them independently. Do not describe an inferred rule or a team heuristic
as an organizer guarantee.
