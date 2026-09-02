# UX-532: the table tools read the nested tables' rows as their own

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-366 (the bound whose guard stays green), UX-318 (the folds that carry the nested tables) | **Serves:** anyone pressing "All rows" on a table whose cells fold | **Topic:** viewer

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
