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

**Gap measured** (`test_pointer_travel_is_a_budget.py`, before): `button.
copy-rows` dx 213.8-932.8px, `select.top-n` dx 70.7-806.6px across
`macro_micro`/`both_scale` at both viewports — both over the 24px bound
and read as `UNPLACED`.

**Close measured** (same guard, after): `copy-rows` and `top-n` given a
fixed slot in `.table-tools` via CSS `order` (`copy-rows` first, `top-n`
last with an auto left margin) rather than a `structured.js` DOM
reorder — the mirror pairing (`top-n` first, `copy-rows` last) passed
the same dx bound but pushed `copy-rows` past `.copy-as`/`.expand-
table`/`.density`, adding a wrapped line on 17 of 30 `.table-tools`
instances and costing `macro_micro` 61px against
`test_the_page_has_a_volume_budget.py`'s 38,200px bound; the pairing
kept wraps to 4 of 30. dx is 0.0px on every measured instance, both
classes, both viewports, `macro_micro` and `both_scale`
(`python3 -m pytest tests/unit/test_pointer_travel_is_a_budget.py`: 44
passed). `dy` is out of scope for these two classes only (`DX_ONLY`):
their block (`.table-tools`) genuinely wraps to more lines for a
narrower, nested table, moving their vertical position with it — a
property of the row's own width, not of where they sit in it; every
other `PLACEMENT` class keeps the `dy` check. J4 (table tools) lengthens
per the Decomposition (12.77→14.8 bits at 1440x900, both pages); J1-J3
are unchanged or within their existing +0.5 bit headroom.

**Mutation table**

| mutation | reddened | count |
|---|---|---|
| CSS `order`/margin removed from `.table-tools button.copy-rows`/`select.top-n` (restores today's visual order) | `test_a_control_class_sits_at_one_place[button.copy-rows-*]`, `[select.top-n-*]` | 8 of 8 (both classes, both viewports, both pages) |
| `select.top-n` dropped from `PLACEMENT` (kept out of `UNPLACED` too, the UX-1042 gap) | `test_every_control_class_a_head_or_row_holds_is_placed` | 4 of 4 (both viewports, both pages) |
