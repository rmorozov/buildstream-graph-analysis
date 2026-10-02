# UX-1265: the graph-width finding lost the total element count and "whatever the capacity" from its title

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-163 verification of UX-1248 (2026-10-02) | **Serves:** R1 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** test_the_shape_conclusions_have_a_negative_case.py::test_the_text_report_states_the_total_and_claims_no_ceiling

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

## Outcome (2026-10-02)

### The gap, measured

`bga analyze tests/fixtures/macro_micro/run --plane2 .../plane2.json` at base
`b35c30e3`: the graph-width title has no detail line, and neither the total
(evidence `element_count` 11) nor a capacity clause is printed.

```text
  2 elements at most can ever build at once — the widest of 10 dependency stages
  0.0% cache hits — caches off: all 11 elements built from source, none reused
```

### The close, measured

The verifier showed the capacity clause false: the widest depth level bounds
nothing (A; B, C after A; D after B; E free: widest level 2, yet C, D, E can run
at once), so the title's "at most can ever build at once" was false too. Both
go; the title states the level and keeps the total, with no capacity clause:

```text
  The widest of 10 dependency levels holds 2 of 11 elements
  0.0% cache hits — caches off: all 11 elements built from source, none reused
```

`why_none` reads "a shape the dependency graph has"; the `dependency_stages` and
`widest_stage` schema descriptions drop "whatever the capacity" and "the ceiling".
Both committed analyses regenerated (`dev_refresh_analysis.py --write`). README
quick start 107 -> 106 lines.

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| M1 | "no number of builders lifts this ceiling" back as detail | text-report clause, 1 failed, 22 passed |
| M2 | "at most can ever build at once" back in the title | text-report clause, 1 failed, 22 passed |
| M3 | title drops the total | text-report + chain clauses, 2 failed, 21 passed |
