# UX-1265: the graph-width finding lost the total element count and "whatever the capacity" from its title

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-163 verification of UX-1248 (2026-10-02) | **Serves:** R1 | **Topic:** analysis | **Area:** bga | **Shape:** mechanical | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

The graph-width finding lost the total element count and "whatever the capacity" from its title (UX-1248), and its detail carries only a step whose why_none the text report does not print.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`.

## Decision

Route:     graph-width gains one detail line, "{element_count:,} elements in all; no number of builders lifts this ceiling". The text report already prints detail lines, so the title stays at UX-1248's length and why_none is unchanged.
Rejected:  putting the clause back in the title: it undoes UX-1248's 28-102 char titles; printing why_none in the text report: it changes every finding's text form for one finding, and why_none already says "only its dependencies move it", which is not the capacity clause.
Files:     bga/findings.py (the graph-width finding, ~:1050), tests/unit/test_the_shape_conclusions_have_a_negative_case.py, tests/fixtures/golden/mixed_task_kinds/expected_output.json and tests/fixtures/with_timeline/analyze.json (regenerated if they carry graph-width detail)
Guard:     tests/unit/test_the_shape_conclusions_have_a_negative_case.py holds the claim that `bga analyze` text output on macro_micro prints, under the graph-width title, the element total (evidence.element_count, formatted with a comma) and the words "no number of builders".
Mutation:  drop the detail= argument from the graph-width _finding: red.
Class:     product
Split:     finding-text track, after UX-1264; writes bga/findings.py, so it runs serially with UX-1266 and UX-1271.
Question:  none

## Required Fix

The detail carries the total and the capacity clause, and the text report prints it.

## Out of Scope

Other titles (UX-1248).

## Acceptance Test

The text report states the total and the capacity clause for graph-width. Mutation: drop the detail line, and the guard reds.
