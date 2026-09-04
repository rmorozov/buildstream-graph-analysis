# UX-641: the levels key is the identity function

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-52 (the gating graph), UX-303 (the shape before the rows) | **Found by:** round 87, by the owner opening the Levels fold | **Serves:** anyone reading the parallelism block | **Topic:** analysis

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
_compute_level_decomposition() -> Dict[int, Set[str]]   # structural/analyzer.py:729
widths = [len(levels[l]) for l in level_nums]           # structural/analyzer.py:363
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

## Outcome

`parallelism.levels` is one row per level - `{level, width, elements}` -
from `_compute_level_decomposition()`, sorted. `analyze/v6`; `analyze/v5`
joins `SUPERSEDED`. Measured with `tools/dev_refresh_analysis.py` and
`bga gen-synthetic --seed 1`:

```text
                golden            with_timeline      scale (1,202)
before  levels  [0, 1, 2]         [0 … 9]            [0 … 13]
after   rows    3                 10                 14
        widest  2 uids            2 uids             102 uids (level 1)
```

**Trap one, measured.** The gating graph and the full graph disagree at
scale by `[0,-2,0,0,0,0,0,0,+1,0,0,0,+1,0]` - the task file's figure,
reproduced exactly - and **16 uids** sit on a different level in the
two. The guard's topology is `test_runtime_edge_gating.py`'s `MIXED`
plus one build edge, where `d.bst` is level 1 gating and level 3 full;
`test_the_two_graphs_really_disagree_here` reads that off the *graphs*,
not the document, so no implementation can satisfy it.

**Trap two, measured, and the first answer was wrong.** Nothing bounded
a cell: a scalar list over `TABLE_OPENS_BOUNDED_ABOVE` built a whole
interrogable table inside one `<td>`. The first fix folded that table
head-and-tail, and `test_the_page_has_a_volume_budget` refused it -
**11,068 DOM elements at 1,202 and 25,488 at xl, against 5,500** -
because a hidden row is still a row, and `test_a_filter_is_a_property
_of_a_table` refused it too: the nested 102-row table put a filter
input inside a 14-row one. So past that threshold the cell is a
*list*, not a table: `PATH_HEAD` uids, `+93 more elements (102 in all)`,
`PATH_TAIL` uids, the rest on click. Measured after: **4,876** at 1,202
and **5,168** at xl, both under 5,500. Blast radius from the
scalar-array census: **0** cells over the threshold on either committed
fixture, 12 at 1,202 elements and all 12 are this key.
`producer.contracts` (25) and `optimization_horizon[].entering` (12)
are under it and render exactly as before.

**Mutations verified red and reverted (16):** levels back to the row
number; a level naming one member; the decomposition off `G_full`; the
guard's topology losing its runtime edge; the members published
unsorted; a level dropping a member; a width one over; the width
sentence back on `levels`; the members column undeclared; the shape
changed under `analyze/v5`; the over-bound cell building a table again;
the control forgetting the population; the head growing with the
population; `ARRAY_INLINE_ITEMS` at 0; the bound reaching below the row
bound; the tail dropped from the list. **One rejected and rewritten:**
`levels=level_nums` in the profile crashed the serializer, so the guard
reddened on an `AttributeError` rather than on the claim - it publishes
`row.level` now, which is the defect exactly.

**Deviation.** Two budgets moved, each with the reading. `golden`'s
`deeper_than_three` bound 0.48 -> 0.49 (700 -> 708 leaves, 331 -> 341
deep, 0.4729 -> 0.4816): membership costs a nesting level and there is
no flatter honest shape for "which elements sit here". The contract
count sentences in `docs/README.md`, `docs/design/architecture.md`,
`CHANGELOG.md` and spec 32.5 are derived figures and moved with the
inventory. `bga/analyzer.py` is a re-export shell: the code the task
cites at `bga/structural/analyzer.py:363`/`:729` is `bga/structural/analyzer.py`.

