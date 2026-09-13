# UX-835: a capped table filters every column it sorts

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-392 (the filter over the preset), §3d | **Found by:** round 115, the design review | **Serves:** the owner filtering a large project's tables | **Topic:** guards | **Area:** tools | **Shape:** mechanical

## Motivation

§3d: filters appear at the row cap. Measured on the scale export:

```text
elements         25 of 1,202   filters 3   sortable 6
leaf_analysis    40 of 135     filters 1   sortable 5
every other table   under its cap, filters 0 — as §3d rules
```

The owner named four blocks without filters (`wall_clock_share_us`,
`by_binary`, `element_join_coverage`, `duration_resolution`); on the
walk capture all four are `dl.pairs`, not tables, so §3d holds there.
What no guard says is *which* columns a capped table filters: the leaf
table sorts five and filters one.

## Required Fix

A guard, `tests/unit/test_a_capped_table_filters_what_it_sorts.py`: for every table whose badge reads `N of M`, each column with
a declared quantity carries a filter, or the column declares
`filter: false` with a reason. `dev_page_census.py` (`UX-836`) is what
it reads.

## Out of Scope

- Filters under the cap — declined: §3d rules they appear at the cap, and this round measured it holding on every table under its cap.
- A filter on a name column — sorting is its tool.

## Acceptance Test

`tests/unit/test_a_capped_table_filters_what_it_sorts.py` green on the scale export once `leaf_analysis` filters its quantity columns; mutation: remove one filter — red.

## Outcome

**Gap measured**, on `scale` (`gen-synthetic --seed 1`), with `data-quantity`
added to every `<th>` (`buildTable`, this task) so a declared quantity is
readable without re-deriving `columnSpecs`, and the guard run against the
base's `elementSignalTable` (`?? "count"` still in place):

```text
$ python3 -m pytest tests/unit/test_a_capped_table_filters_what_it_sorts.py -v
FAILED ...AssertionError: a capped table sorts a declared-quantity column
with no filter (§3d): [('elements', '25 of 1,202', 'is_leaf', 'count'),
('elements', '25 of 1,202', 'element_kind', 'count'),
('elements', '25 of 1,202', 'observed_critical', 'count')]
1 failed in 3.49s
```

Not `leaf_analysis`: `leaves_detail` declares no `bga:quantity` on any of
its four fields, so its 0-of-5 was already correct. The red table is
`elements` - `elementSignalTable`'s join hint defaulted every column with
no declared or guessed quantity to `"count"` (the same shape `mapTable`'s
record branch had already learned to avoid), so three boolean/categorical
join columns were flagged as quantities with no filter.

**Close measured**, same export, `?? "count"` removed:

```text
$ python3 -m pytest tests/unit/test_a_capped_table_filters_what_it_sorts.py -v
1 passed in 3.92s
```

| mutation | result |
|---|---|
| `downstream_count`'s `th-filter` creation skipped (`spec.key === "downstream_count"` added to the gate) | reds: `[('elements', '25 of 1,202', 'downstream_count', 'count')]` |

Reverted from a saved copy (not `git checkout`) and re-run green, `1
passed in 3.92s`. Guard runtime: **3.4-3.9s** (own run, not the suite's
touching set).
