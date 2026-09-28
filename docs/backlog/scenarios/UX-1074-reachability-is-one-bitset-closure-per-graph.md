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

## Outcome

**Gap measured** (`step.py`-equivalent, `bga analyze` on `gen-synthetic
--store --seed 1`, this machine): 1,202 el: 2.15s / 127 MB RSS; 5,002 el:
29.72s / 1967 MB RSS - matches the audit's RSS reading.

**Close measured**, same fixtures, after the bitset closure
(`bga/graph/edg.py`): 1,202 el: 1.36s / 70 MB RSS (45% of before); 5,002 el:
13.15s / 437 MB RSS (78% under 1967 MB, against the 40% target). `bga
analyze` output byte-identical at 74/1202/5002 elements, checked once by
hand (`before_*.json`/`after_*.json` SHA-256 match, `bga.graph.edg`'s
pre-fix functions reinstalled in a subprocess); `downstream_count`'s dict
order also matched, once `ReachabilitySets` was given the old loop's own
insertion order (reversed topo-then-leftover) rather than
`graph.elements` order. The 5,002-element reading is this measurement,
not the guard test - a 184s subprocess-pair guard at that scale was cut
back per review to the fast checks below (`test_reachability_is_one_closure.py`:
8 tests, ~0.5-1.2s total), which cover the named input classes and
1,202 elements in-process against the same pre-fix reference. Verifier
found the memory clause itself unguarded (call-count alone passes a
cache wrapped around the old set algorithm); `test_the_closure_is_a_
bitset_not_a_python_set_per_element` closes it - `tracemalloc` peak of
`_build_reachability_closure` at 1,202 elements against
`_reference_reachability`'s peak on the same graph, measured at 2% of
it (900 KB / 45.9 MB), asserted under 50%.

**Mutation table**

| Guard | Mutation | Result |
|---|---|---|
| `test_one_graph_shares_one_closure_build` | `_reachability_closure`'s cache check forced to always miss (`if False and cached is not None`) | `call_count` 3 (expected 1) - red |
| `test_the_closure_is_a_bitset_not_a_python_set_per_element` | `_build_reachability_closure` computes per-element `set`s (like `_reference_reachability`) before compressing to bitmasks | bitset peak 46.4 MB against reference's 45.9 MB (101%, not under 50%) - red |

(Both re-run after the guard file was shrunk to drop the 5,002-scale
subprocess pair: same mutations, same results, <2s each instead of the
full suite.)

**Design**: `ReachabilitySets` (bga/graph/edg.py) wraps one direction's
bitset, decoding a uid's `frozenset` only on first access, with a
`.count(uid)` popcount that never decodes - `fan_in.py` and
`serialization_points.py` now call `.count()` instead of
`len(...get())`. The closure itself (`_build_reachability_closure`) is
cached on `Graph.reachability_closure_cache` (a new, non-comparable
field), so every one of the five call sites shares one build per graph.
`analyze_graph`'s `reachable_downstream`/`reachable_upstream` are now
the views themselves, not `{k: list(v) ...}` for every element -
`reachable_upstream` has no reader at all.

**Surfaces beyond `bga/graph/edg.py`**: `bga/graph/fan_in.py`,
`bga/structural/serialization_points.py` (`.count()` instead of
`len(...get())`); `bga/structural/batching.py`, `bga/sources.py`
(parameter type `dict[str, set[str]]` → `Mapping[str, set]`, no
behaviour change - `pyright`, not `ruff`, needed it); `bga/ingest/models.py`
(the cache field on `Graph`); `tests/quality_baseline.json` (one stale
`ruff C901` entry removed - `compute_reachability`'s body shrank).
