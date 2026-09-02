# UX-532: the table tools read the nested tables' rows as their own

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-366 (the bound whose guard stays green), UX-318 (the folds that carry the nested tables) | **Serves:** anyone pressing "All rows" on a table whose cells fold | **Topic:** viewer

## Motivation

The user's report: `resource_blast` at Top 25 is right; "All rows"
grows a second table under the first. Measured on a cold ex06
snapshot given 60 shared resources so the table exceeds the 40-row
bound:

```text
outer tbody, before any click    624 direct <tr>   (60 published + 564 torn out of 54 nested tables)
nested tables                      0 rows          ("Blast elements · 1 level, 11 rows" opens empty)
badge                            "25 of 60"
after All rows                   624 visible · badge "624 of 60" · "Copy 624 rows"
last rows                        4lib-d.bst / 5lib-e.bst / 6lib-f.bst   — the folds' key|value rows, as 2-cell rows
```

No second `<table>` exists. The mechanism is row migration:

```js
const body = table.querySelector("tbody");        // tables.js:77   the OUTER tbody
const rows = [...body.querySelectorAll("tr")];    // tables.js:78   every <tr> at ANY depth
kept.forEach((tr, i) => { tr.hidden = i >= n; body.append(tr); });   // :131-132  moves them up
```

The same descent is in sort (`tables.js:452-471`), Top-N
(`:315-326`), the `data-element` stamp (`structured.js:564`),
`statedOnce` (`:615`), `foldTheMiddle` (`:652`), the badge and copy
count (`:840`) and the distribution strip (`shapes.js:247`). Every
table with a folded list in a cell is affected once any of those
fires: on the real cold page `serialization_point_risks` ("3 of 1")
and `run_instance.producer` ("25 of 3", contract rows appended);
with a fresh analysis also `resource_blast`, `restructuring` and
`plane2_coverage.static_census`. `UX-366`'s guard stays green
because no fixture has a bounded table with a nested table in it.

## Required Fix

- One row selector, in one place: the table's *own* rows are
  `:scope > tr` of its own tbody, and every site above uses it.
- A fixture whose bounded table has a folded list in a cell (the
  60-resource synthetic above is the recipe), and the `UX-366`
  guard extended to it: badge count equals published rows, nested
  folds open with their rows, "Copy N rows" says N.

## Out of Scope

- The fold shape itself (`FOLDED_LIST`, `ARRAY_INLINE_ITEMS = 6`) —
  §3a's design; only its rows' ownership is wrong.

## Acceptance Test

On the synthetic 60-row page: badge "25 of 60" → "60 of 60", nested
folds carry their 11 rows, copy says 60. Mutation: restore
`querySelectorAll("tr")` — red on the new fixture, and *only* on it
(so the fixture is what discriminates).

## Outcome (round 80, 2026-09-02) — 🟢 Done

### The gap, measured

`tests/pages.shared_resource_run` — `macro_micro` (11 elements) given 60
shared git repositories, the direct pair rotating so the blast sets
differ. One browser drive over the `resource_blast` table, reading the
outer tbody's **element children** rather than by selector:

```text
                     own <tr>  visible  badge        copy            nested rows
at rest                   660       25  25 of 60     Copy 25 rows    [0, 0, 0]
after "All rows"          660      660  660 of 60    Copy 660 rows   [0, 0, 0]
last 3 own rows      4|lib-d.bst · 5|lib-e.bst · 6|lib-f.bst
```

600 rows torn out of 60 nested tables and appended to the outer tbody by
`applyFilters`' opening bound. The folds open empty, the badge says
`660 of 60`, and the table's last rows are the folds' `key|value` pairs
as two-cell rows — the user's report, reproduced.

### After

Same fixture, same drive, same instrument:

```text
                     own <tr>  visible  badge        copy            nested rows
at rest                    60       25  25 of 60     Copy 25 rows    [11, 11, 11]
after "All rows"           60       60  60 rows      Copy 60 rows    [11, 11, 11]
```

`ownRows(table)` is the tbody's `<tr>` children, in `tables.js`, and the
nine sites the Motivation names read it (or `ownCells`, built on it).
`60 rows` rather than `60 of 60` is `badgeText`'s existing wording for
shown == total, unchanged.

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| M1 | `ownRows` → `ownBody(table).querySelectorAll("tr")` — the defect itself | 4 of the 5 new clauses; the 7 `UX-366` clauses stayed **green** |
| M2 | `shownRows` (`structured.js`) descends again | `…badge_and_the_copy_count…` only — `Copy 660 rows` |
| M3 | `applyFilters` descends again | the same 4 as M1 |
| M4 | `applyTopN` descends again | **nothing** — see below |
| M5 | `sortable` descends again | `…sorting_moves_no_row_between_tables` only |

**Two findings.** `applyTopN` (M4) has **no caller in the page** —
`grep -rn applyTopN bga/ tests/` finds the definition, one node harness
and a comment — so its correction is real and unexercised; the page's
bound goes through `applyFilters`' `top` pass. And `applyFilters` is the
single site that migrates rows, so the four own-rows/nested/badge/
all-rows clauses share one cause (M1 ≡ M3): they are four readings of
one migration, not four independent claims. The two clauses that do
discriminate alone are the copy count (M2) and sorting (M5).

The `data-element` stamp, `statedOnce` and the distribution strip were
corrected by the same helper and **no clause of mine reads them** — on
this fixture the inflated cell counts change no rendered text I could
assert on. They are unguarded here; the item's Acceptance Test named
badge, folds and copy, and those are covered.

### Deviation from the Required Fix

The selector is a child walk over `tbody.children`, not `:scope > tr`:
`tests/dom_shim.mjs` throws on any pseudo-class by design (`UX-264`) and
48 guard files use it, so `:scope` would have meant changing the shared
shim. Same claim, one place, no new test surface.

```text
make test-touching  →  358 passed, 2 skipped in 62.00s (23 files)
pytest tests/unit/test_all_rows_means_all_rows.py  →  12 passed in 14.60s
make lint           →  All checks passed!
```
