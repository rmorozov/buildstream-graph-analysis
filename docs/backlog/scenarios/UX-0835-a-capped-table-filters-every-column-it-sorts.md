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
