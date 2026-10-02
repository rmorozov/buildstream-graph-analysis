# UX-1266: joint-saving and optimization-horizon name the same element set on macro_micro

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-163 verification of UX-1249 (2026-10-02) | **Serves:** R1 | **Topic:** analysis | **Area:** bga | **Shape:** mechanical | **Reading:** container

**Guard:** none — open, no guard named yet

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
