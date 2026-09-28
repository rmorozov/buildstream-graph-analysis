# UX-1074: graph reachability is materialised as sets, five times per analysis

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the snapshot and view performance audit on `39d89d4` (2026-09-28) | **Serves:** anyone opening a run of a few thousand elements | **Topic:** analysis | **Area:** bga | **Shape:** mechanical

## Motivation

`compute_reachability` (`bga/graph/edg.py:219`) builds a `set` per
element for both directions: O(V·(V+E)) time, O(V²) memory. One
`bga analyze` calls it 5 times (`edg.py:943`, `:944` via
`compute_downstream_count`, `fan_in.py:52`, `batching.py:122`,
`serialization_points.py:141`; `blast.py:234`, `cli.py:124` too);
compare's two analyses, 8. `UX-539` made the structural closure a
bitset (`bga/structural/analyzer.py:231`) and left this one. [the audit](../../audits/perf-snapshot-view-2026-09-28.md):

```text
            entries      time   RSS after (one call)
1,202     660,754      0.1s     78 MB
5,002  14,481,214      6.8s    995 MB
```

It is the step from 127 MB to 1,967 MB peak between the two sizes.

## Decomposition

Input classes: a chain, a wide layer, a diamond, a graph with a cycle or disconnected element; 1,202 and 5,002 elements. Journey: `bga analyze`.

## Required Fix

In `bga/graph/edg.py`: One closure per graph, computed once and shared by every caller, as
per-element integer bitsets (or counts where only counts are read);
`analyze_graph`'s `reachable_*` lists (`edg.py:960`) built only if a
reader needs them.

## Out of Scope

Other superlinear terms (`_compute_underparallel_idle_us`, 4.2 s at 5,002).

## Acceptance Test

`tests/unit/test_reachability_is_one_closure.py`: On `gen-synthetic --layers 40 --width 125 --seed 1`, one analysis
calls the closure once and peaks at least 40% under today's 1,967 MB; `analyze.json` is
byte-identical to today's at 74 and 1,202 elements. Mutation: call
the closure per consumer again, and the call count reds.
