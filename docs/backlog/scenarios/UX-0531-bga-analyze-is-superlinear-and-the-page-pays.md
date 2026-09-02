# UX-531: `bga analyze` is superlinear, and the page pays for it

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-42 (the last superlinear term closed) | **Serves:** anyone opening a run of a few thousand elements | **Topic:** analysis

## Motivation

```text
bga analyze --format json      1,202: 4.36 s   2,402: 13.51 s   4,002: 45.05 s    n^1.6-1.9
bga view --export                     4.27 s                    48.4 s
```

A run without a published `analyze.json` pays this on `bga view`.
`UX-42` closed one O(n²) term at 68 s; another has grown in since.

## Required Fix

Profile the 4,002 run (`python -m cProfile`), name the term, and
either bound it or make it linear; the seeded 4,002 run's analyze
wall clock joins the guard that holds `UX-42`.

## Out of Scope

- Caching `analyze.json` in the store — it is already written by
  `snapshot`; this is the cold path.

## Acceptance Test

Analyze at 4,002 under a stated bound with the profile's top entries
pasted before/after.
