# UX-1055: a table's Copy rows and top-N controls sit in one place in its tool row

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-1042 | **Found by:** UX-1042's guard (round 143), styleguide §3l | **Serves:** R1, R4 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** bounded

## Motivation

UX-1042's placement clause, every chapter open, offset read against the
table wrapper (the `.table-tools` parentNode) from its left and right
edges, identical over three runs:

```text
class               page          viewport   dx spread left / right
button.copy-rows    macro_micro   1440x900   481.7 / 873.4 px
button.copy-rows    macro_micro   390x844    203.7 / 209.7 px
select.top-n        both pages    both       70.7 .. 806.6 px
bound (§3l)                                  24 px
```

Both follow a variable run of siblings in `.table-tools` (the row badge,
the preset, the pager; `structured.js:1156`), so where they sit depends
on which of those a table has. UX-1042 reads the two classes as
`UNPLACED` and holds the other four.

## Decomposition

Input classes: a table with and without a preset, a pager and a badge;
1440x900 and 390x844; golden, macro_micro and the two-plane scale page.
The journey extended is UX-1042's J4 (table tools).

## Required Fix

Give `copy-rows` and `top-n` a fixed position in the tool row (for
example, pinned to the row's right edge, or placed before the variable
siblings), so each sits within §3l's 24 px of its own class across
tables; then move both from `UNPLACED` to held in
`tests/unit/test_pointer_travel_is_a_budget.py`.

## Out of Scope

The tool row's set of tools (§3, `UX-1045`); the labels and grades of
the two controls.

## Acceptance Test

UX-1042's placement clause holds `copy-rows` and `top-n` at both
viewports on every page it reads. Mutation: restore today's order in
`structured.js` and the clause reds for both classes.

## Outcome

Not started.
