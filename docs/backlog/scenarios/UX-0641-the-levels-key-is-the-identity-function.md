# UX-641: the levels key is the identity function

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-52 (the gating graph), UX-303 (the shape before the rows) | **Found by:** round 87, by the owner opening the Levels fold | **Serves:** anyone reading the parallelism block | **Topic:** analysis

## Motivation

`parallelism.levels` publishes `[0, 1, 2, ... n-1]`. Always. Measured
on round 87's three-plane run:

```text
levels          [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
width_at_level  [1, 2, 1, 1, 1, 1, 1, 1, 1, 1]
levels == list(range(len(width_at_level)))   True
```

It carries exactly one fact — `len(width_at_level)` — which the
sparkline's own sentence already prints. A reader who opens the fold
gets ten rows of the row number.

The schema compounds it: `schemas.py:2006` gives `levels` the
description belonging to `width_at_level` — "How many elements sit at
this level of the graph" — which is not what the key holds.

The data that would make the block worth opening is computed and
thrown away one line later:

```python
_compute_level_decomposition() -> Dict[int, Set[str]]   # analyzer.py:729 - has the uids
widths = [len(levels[l]) for l in level_nums]           # analyzer.py:363 - discards them
```

## Required Fix

`levels` stops being published as a range. The block publishes, per
level, the width and **which elements sit there** — the set
`_compute_level_decomposition` already returns.

Two traps this fix must not fall into, both measured:

- **Do not source the members from `elements.unweighted_depth`.** They
  disagree: `parallelism` runs on the *gating* graph with runtime edges
  removed (`UX-52`), `unweighted_depth` on the full graph. On the
  1,202-element synthetic run the per-level difference is
  `[0,-2,0,0,0,0,0,0,+1,0,0,0,+1,0]`.
- **Bound the cell.** 1-2 uids per level on both committed fixtures,
  but **102 in one level** at 1,202 elements. Nothing in the viewer
  bounds a *cell's* contents today — only a table's row count.
  `UX-319`'s head/tail-with-count fold is the precedent.

A published key changes shape, so this is a version bump (§3.7).

## Out of Scope

- The twin table under the width-at-level sparkline, which renders the
  same array the polyline was built from. It is redundant, but it is
  redundant *precisely* — and `style.css:1100` opens it deliberately in
  `@media print` so paper keeps the exact values. Left as it is.

## Acceptance Test

`bga analyze --format json` on both fixtures: no key equals
`list(range(n))`, every level names its members, the members match
`_compute_level_decomposition` and not `unweighted_depth`, and the
1,202-element run's 102-member level renders bounded.
