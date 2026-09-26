# UX-1028: "All rows" draws the whole table past any ceiling

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §3k | **Serves:** R1, R4 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** bounded

## Motivation

Measured on the 4,002-element run (`bga gen-synthetic --seed 1 --layers 20 --width 200 --store --runs 30`), exported, 1440x900, every chapter open, then every step control pressed.

```text
largest table at rest     40 rows (TABLE_OPENS_BOUNDED_ABOVE)
after "All rows"          4,002 rows (elements)
DOM, every step pressed   62,995 (8.9x rest)
```

## Decomposition

Input classes: tables at 11, 40, 41 and 4,002 rows. The journey extends reading the bounded table into walking the rest a page at a time.

## Required Fix

"All rows" in `bga/viewer/tables.js` is offered only under a ceiling the table states; past it the step replaces the mounted window with the next bound of rows, the position shown ("rows 41-80 of 4,002"), or opens table focus. It never appends.

## Out of Scope

Virtual scrolling.

## Acceptance Test

The §3k census (UX-1032) presses every step at 4,002 elements, each paging step 10 times: mounted rows stay at the bound after every press. Mutations: offer "All rows" unconditionally, or append the next page, and the census reds.

## Outcome

**Gap measured.** `ALL_ROWS_CEILING = 200` added to `tables.js`;
`structured.js`'s `interrogable` offers "All rows" only when
`total <= ALL_ROWS_CEILING`, and past it appends a `.table-pager`
(Prev/Next) that replaces `state.top` with `{n: TABLE_OPENS_BOUNDED_ABOVE,
column: null, offset}` - never appended - and shows the position
("rows 1-40 of 4,002"). `applyFilters` (`tables.js`) grew an `offset`
on the existing slice.

**Close measured.**
`pytest tests/unit/test_every_step_past_a_bound_is_bounded.py -q` (this
row's clauses): `10 passed`. The pre-existing `test_all_rows_means_all_rows.py`
(1,202-row fixture, under the new ceiling) rewritten to prove
"reachable by whichever mechanism the size earns" rather than assume
"All rows" always exists: `12 passed`.

**Mutation table:**

| mutation | reddened | count |
|---|---|---|
| gate `if (total <= ALL_ROWS_CEILING)` -> `if (true)` (offer unconditionally) | `TestEveryTableStaysBounded::test_no_table_ever_mounts_past_the_bound`, `test_all_rows_is_not_offered_past_the_ceiling` | 2 of 10 |
| pager's `state.top.n` set to `offset + TABLE_OPENS_BOUNDED_ABOVE` (append) instead of a fixed window | `test_no_table_ever_mounts_past_the_bound`, at the 5th press (200 -> 240) | 1 of 10 |

Deviation: on the merge `structured.js` crossed the viewer line ceiling; `elementSignalTable`, `presetTable` and `renderPairs` moved to `bga/viewer/pairs.js` (`4f84b16e`).
