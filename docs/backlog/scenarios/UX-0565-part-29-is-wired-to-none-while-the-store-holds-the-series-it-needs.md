# UX-565: Part 29 is wired to `None` while the store holds the series it needs

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-234 (the store as a distribution), UX-92 | **Serves:** R3, the CI owner asking how stable an element's duration is | **Topic:** analysis

## Motivation

```text
bga/analyzer.py:2039-2040          historical_durations = None    # unconditionally
bga/diagnostics/analyzer.py:1027   returns empty when None
specification.md:1396-1422         Part 29, duration variability from a history
```

When the spec was written no history existed. `bga/run_store.py`
and `cache_trend.py` now hold a series of runs of the same project,
`--aggregate` already reads it per host class, and Part 29's
precondition is met on every store with two or more runs — and the
wiring still passes `None`.

## Required Fix

`analyze` on a snapshot reads the store's prior runs of the same
host class (the `UX-234` join) into `historical_durations`; Part 29's
output reaches the analysis document (an addition) and the page's
element cards, which already draw a history sparkline from the same
runs (`HISTORY_POINTS_MAX`). A guard on a planted store of three
runs.

## Out of Scope

- Cross-host histories — refused by `UX-186`'s rule, as today.

## Acceptance Test

On a store of three same-host runs the variability block is
non-empty; mutation: restore `None` — red.
