# Observable evidence versus extraction and hidden truth

Owner: root, isolated structured-extraction-training checkout. This is a
development forensic experiment on the two already-used TRAIN worlds, not a
competition result or an independent test. It changes no Rust production code.

The official input label describes whether the sentence is true on its page
date. Its form describes the values actually asserted, including wrong ones.
For conjunction, a false assertion makes the whole row false; otherwise an
unresolved assertion yields unsure. A parser score is not a truth probability.

The supplied archive implements a more explicit task than original practice:
known values have visible, labelled-true anchor sentences stating a validity
interval. An interval ending "through 29 October" includes that day; our
internal end is 30 October, exclusive. Neither the publication date nor CSV
position licenses indefinite persistence.

[observable_semantics.py](observable_semantics.py) builds an index from public
`text`, `date` and known `label=true` only. It parses explicit interval prefixes,
extracts typed assertions, evaluates query values at the query's date and
combines their results. False source compounds supply no individual negative
facts. Conflicting support abstains. Unit conversions and mismatched date
precision remain unsupported in this bounded baseline; this is not the newer
main Rust typed comparator.

The real inference path finishes before gold is opened. Separate oracle-form
variants replace extraction only for diagnosis; `expected_value`, world files
and assertion verdicts never enter the real predictor. Previous context is the
last three public rows, not a gold context pointer. Model is the frozen stage-1
two-member FP32 CPU stack, SHA256
`eb9fac33e5356390890550e62716fb5654c7ac28c5f1d9920eb44ca0e7fc974f`.

| Variant | Diagnostic targets /4,103 | Synthetic targets /18,103 |
| --- | ---: | ---: |
| Public explicit intervals, oracle source/query forms | 4,103 (100%) | 18,103 (100%) |
| Same index, neural query forms | 4,101 (99.951%) | 18,086 (99.906%) |
| Neural source forms and neural query forms | 4,101 (99.951%) | 18,086 (99.906%) |

These numbers explain this training generator; they do not predict competition
accuracy. The model has trained on related rows. A correct truth label can hide
an extraction error, particularly when one false conjunct already decides it.

Two ablations identify actual failure causes. Before supporting ordinal interval
dates such as "the 1st of July", only 946/1,442 diagnostic anchors were parsed;
oracle-form truth accuracy was 71.874%. Adding those dates raised it to 94.053%.
The remaining 244 diagnostic errors involved version inequalities. Numeric
component ordering (2.10 greater than 2.9), without zero-padding equality,
removed them. This ordering was checked against the TRAIN archive; no hidden
organizer implementation was recovered. Adding unqualified same-day observations
gave no further gain after interval coverage was complete.

Four regression tests in [test_observable_semantics.py](test_observable_semantics.py)
cover inclusive boundaries/ordinal dates, false compound evidence exclusion,
false dominance over unknown and typed comparison direction/precision/version
behavior. All four passed on the server. Immutable remote reports are
`v3-root/observable-semantics-v1`, `-v2`, `-v3` beneath the training root; later
variants reused public neural predictions after validating model/input hashes.

Original practice is materially different: 128 false rows assert values that
are true somewhere else in the file. Identical text can change label by date.
Moreover, year/month precision, equivalent duration units and unlisted short
names can produce different JSON for compatible facts. See the
[practice audit](PRACTICE-SEMANTICS-FORENSICS.md).

The five generated-entry types are a separate output contract. A `relation`
joins `subject.link = target` with `target.attribute = value` over an overlapping
valid time. Sharing an attribute or a numerical value does not create that
relationship. See the [official semantics audit](OFFICIAL-SEMANTICS-FORENSICS.md).

Updated main at `e6f687c` contains an independent earlier interval-engine study
and a more capable Rust temporal solver. This experiment confirms the archive
mechanism with the new neural stack; it is not a claim that this mechanism had
never been studied by the team. Previously published calibration results mean
those archive releases cannot now be described as fresh team-wide blind tests.
