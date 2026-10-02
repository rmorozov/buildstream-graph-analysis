# UX-1266: joint-saving and optimization-horizon name the same element set on macro_micro

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-163 verification of UX-1249 (2026-10-02) | **Serves:** R1 | **Topic:** analysis | **Area:** bga | **Shape:** mechanical | **Reading:** container

**Guard:** test_the_joint_saving_is_priced_one_element_at_a_time.py::test_one_finding_carries_the_set_and_its_order

## Motivation

joint-saving and optimization-horizon (both High) name the same element set on macro_micro; making them one finding is a decision about which findings the analysis emits. Also correct the comment at `tests/unit/test_the_page_has_a_volume_budget.py` (~:385) that says +201 words where +176 was measured.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`.

## Decision

Route:     Merge them into one finding, joint-saving. The two always share a set: price_joint_saving takes horizon[:3] and HORIZON_STEPS_SHOWN is 3, so joint_saving_us == horizon[2].cumulative_saving_us. joint-saving's detail gains the "In this order: ..." line, the optimization-horizon finding id is retired, and the optimization_horizon signal stays. The +176 comment fix goes to the bookkeeping sweep (`dev_bookkeeping.py --add`) rather than this track.
Rejected:  keeping both and recording that: one number and one set said twice at High on every chain-bound run; keeping optimization-horizon instead: _priced_fixes (text.py:303) and test_a_number_has_one_carrier read joint-saving's evidence; widening _said_once to equal severity: its rule is UX-1249's and out of scope.
Files:     bga/findings.py (_outlook_findings, FINDING_READERS), bga/provenance.py (remove the optimization-horizon claim and its section link), bga/viewer/element.js (the :906 comment that names the finding), tests/unit/test_the_joint_saving_is_priced_one_element_at_a_time.py, tests/unit/test_no_two_fields_carry_the_same_elements.py (_is_narrative docstring), tests/unit/test_every_finding_reaches_a_fixture.py and tools/dev_finding_coverage.py (if they enumerate the id), tests/fixtures/golden/mixed_task_kinds/expected_output.json, tests/fixtures/with_timeline/analyze.json (regenerated)
Guard:     tests/unit/test_the_joint_saving_is_priced_one_element_at_a_time.py holds the claim that on macro_micro and golden, joint-saving's detail names the horizon's order and no other finding's elements equal joint-saving's set.
Mutation:  re-append the optimization-horizon _finding in _outlook_findings: red.
Class:     product
Split:     finding-text track, after UX-1265. Needs a schema/size re-read: the export byte and level-ratio bounds in test_the_report_you_can_attach.py and test_no_level_carries_nothing.py should only fall; if one reddens, measure it and do not raise it.
Question:  Default taken; Ruslan may reverse: joint-saving and optimization-horizon are one finding (joint-saving's id kept). The reverse is to re-emit optimization-horizon and record why there are two.

## Required Fix

Decide whether the two are one finding; correct the comment to +176.

## Out of Scope

The dedup rule (UX-1249).

## Acceptance Test

Either one finding on macro_micro, or the decision recorded with the two kept; the comment reads +176.

## Outcome (2026-10-02)

### The gap, measured

`show.py` (scratchpad, `bga analyze --format json`) at base `b35c30e3`,
`macro_micro` with its `plane2.json`: two High findings, one set.

```text
joint-saving high | 23.1 s (50.0% of the build) is what the top 3 are worth together
      D:     That is more than the 16.1 s alone: codegen.bst pays off after core.bst
optimization-horizon high | 3 fixes, in order of what each is worth, take the build to 20.1 s
      D:     In this order: core.bst (31.1 s) -> codegen.bst (24.1 s) -> lib-b.bst (20.1 s)
```

Golden the same: `joint-saving` and `optimization-horizon`, both on base.bst,
lib.bst, extra.bst.

### The close, measured

One finding (default taken; the reverse is to re-emit `optimization-horizon`):

```text
joint-saving high | 23.1 s (50.0% of the build) is what the top 3 are worth together
      D:     That is more than the 16.1 s alone: a later step pays off only once the earlier ones are done
      D:     In this order: core.bst (31.1 s) -> codegen.bst (24.1 s, pays off after the step before) -> lib-b.bst (20.1 s)
```

With the order shown, the compound relation names no element: naming them in
both lines reddened `test_no_element_is_named_twice_in_one_card[macro_micro]`
(UX-1249's once-per-card rule), and the order line marks the step instead.
Only steps in `worth_more_after` are marked; a compound set with none (the
`elements[1:]` fallback) marks no step and reads "together they compound" (verifier).

The finding id leaves `FINDING_READERS` and `provenance._CLAIMS`; the
`optimization_horizon` signal stays, and `joint-saving`'s claim cites
`optimization_horizon[0].makespan_after_us`, so `_SECTION_READERS`' R1 for it
is still derived (`test_a_reader_role_demotes`). Its `time-by-kind` link moves
to `joint-saving` (`test_every_library_query_is_reachable_from_a_finding`), and
the evidence schema's `steps` block goes (`test_no_declaration_names_a_key_no_finding_emits`).
Golden's `document_shape`: 896 -> 852 leaves, deepest 7 -> 6, deep share
0.5279 -> 0.5153; no bound in `test_no_level_carries_nothing.py` or
`test_the_report_you_can_attach.py` reddened. README quick start 111 -> 107
lines. `test_the_page_has_a_volume_budget.py` comment reads +176 words.

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| M1 | re-append an `optimization-horizon` finding in `_outlook_findings` | one-finding clause, both runs, 2 failed, 4 passed |
| M2 | drop the "In this order" detail line | one-finding clause, both runs, 2 failed, 4 passed |
| M3 | order drawn reversed | one-finding clause, both runs, 2 failed, 4 passed |
| M4 | ordered compound relation names `later` and `earlier` again | `test_no_element_is_named_twice_in_one_card[macro_micro]`, 1 failed, 7 passed |
| M5 | order marks `marked or elements[1:]` | `test_the_order_marks_only_the_steps_measured_to_pay_off_later[worth_more_after0]`, 1 failed, 7 passed |
