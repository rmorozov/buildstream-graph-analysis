# UX-52: the structural plane builds its graph from *all* dependency edges, so `runtime`-only edges inflate its critical path, depth, levels and improvement ranking

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — (pre-existing; `UX-50` fixed the *durations* on this same code path, this is the *edges*) | **Topic:** analysis

## Motivation

Found in round 5, the first round to point `bga` at a **real, well-maintained BuildStream project** (`freedesktop-sdk`, 1089 elements) instead of a purpose-built example.

The cross-check sweep disagrees on a real project graph, in the same two places `UX-50` disagreed:

```text
$ bga analyze -f json <freedesktop-sdk zlib closure, 85 elements>
  structural.metrics.critical_path_length     32
  len(signals.critical_path)                  28
  structural.sensitivity.critical_path_us  32000
  floors.t_infinity_observed               28000
```

`UX-50` fixed the durations feeding this path. This is a different cause, and the numbers say exactly which:

```text
ALL edges   (502 edges): longest path = 32 elements   <- what StructuralAnalyzer uses
build-only  (475 edges): longest path = 28 elements   <- what t_infinity uses
```

**The real project has 27 `runtime` dependencies. Every fixture in this repository has zero.**

| graph | build deps | runtime deps |
|---|---|---|
| `freedesktop-sdk` (zlib closure) | 475 | **27** |
| `examples/06-macro-micro-optimization` | 34 | **0** |
| synthetic scale fixture | 3500 | **0** |

## The code already knows the rule, and one caller does not apply it

`bga/graph/edg.py::build_element_graph` takes `exclude_dependency_types`, and its docstring states the rule precisely:

> `None` (the default) includes every edge, unfiltered - the right choice for purely structural queries (reachability, blast radius, leaf/deferrability, Part 24/25), which must count a `runtime`-only edge just as much as a `build`-type one. Pass `{"runtime"}` for the *gating* chain specifically (`compute_critical_path`/`compute_slack`, Part 14.1) - a `runtime`-only edge doesn't actually constrain build scheduling **[...]** so including it there **would inflate `T∞,observed` past what Part 14.1 itself claims it certifies**.

`compute_critical_path` and `compute_slack` pass it. `bga/structural/analyzer.py::build_edg` does not:

```python
def build_edg(graph):
    """Build ElementDependencyGraph from a Graph object."""
    from bga.graph.edg import build_element_graph
    predecessors, successors = build_element_graph(graph)   # <- unfiltered
```

and that one NetworkX graph is then the input to **everything** in the structural plane:

- `_compute_critical_path_nodes` → `metrics.critical_path_length`
- `compute_structural_metrics` → `max_depth`, `avg_fanout`, `serialization_ratio`
- `_compute_level_decomposition` → `parallelism.levels`/`width_at_level` (`UX-41`)
- `analyze_bottlenecks` → `choke_points` (`UX-43`)
- `_longest_path_us`, `_compute_all_slacks` → `sensitivity`, i.e. the **improvement ranking** (`UX-44`)

So on this real project the structural plane reports a 32-element critical path where the gated one is 28 - **14% inflated** - and every graph-shape signal is computed over a graph with 27 edges that do not constrain build scheduling.

This is the same shape of defect as `UX-41`: a rule written down in the code, in detail, and not applied by one of its callers.

## Why no previous round could find it

Not for lack of scale. The synthetic 1202-element fixture has 3500 dependencies and **not one runtime edge**, because `tools/gen_synthetic_scale_run.py` emits `dependency_type: "build"` unconditionally - it was written to probe scale, and faithfully reproduced the only dependency type the repo's examples had. `examples/06` and `examples/07` are hand-written and use `type: build` throughout.

A real project mixes them as a matter of course. This is the converse of `UX-50`'s lesson about fixture *shape* over fixture *size*, and the sharper version of it: **a fixture written by the same people who wrote the analyzer will tend to contain only the cases the analyzer already handles.**

## Required Fix

`StructuralAnalyzer` needs **two** graphs, because its consumers genuinely want different ones - which is what `build_element_graph`'s docstring already says.

1. **A gating graph** (`exclude_dependency_types={"runtime"}`) for everything that models build scheduling: critical path, `max_depth`, level decomposition, choke points, slack, and the `sensitivity` ranking. After this, `structural.sensitivity.critical_path_us` must equal `floors.t_infinity_observed` on a graph containing runtime edges, exactly as it already does on one without.
2. **The full graph** for reachability-flavoured signals that must count runtime edges: `blast_radius`, `downstream_count`, deferrability/leaf analysis. These are currently *correct by accident* - they get the unfiltered graph because nothing filters - and must stay correct deliberately.
3. **Decide `serialization_ratio` and `avg_fanout` explicitly.** They are shape descriptions rather than scheduling claims, so either graph is defensible; the point is that the choice should be stated rather than inherited.
4. **Make the fixtures able to see this.** At minimum, `tools/gen_synthetic_scale_run.py` should emit a realistic share of runtime edges, and one topology fixture should carry a runtime-only edge, so the invariant in point 1 is exercised by the suite rather than only by a real project.

## Out of Scope

- `floors.t_infinity_observed`, `compute_critical_path` and `compute_slack`, which already pass the exclusion and are correct - this task brings the structural plane into line with them, not the reverse.
- Whether `runtime` edges should appear in the *attribution* pipeline, which already gates them out at `bga/normalize/timestamps.py` (`P4-11`) and is not in question.

## Acceptance Test

1. On the `freedesktop-sdk` 85-element graph, `structural.sensitivity.critical_path_us == floors.t_infinity_observed` and `metrics.critical_path_length == len(signals.critical_path)`.
2. `blast_radius`/`downstream_count` are **unchanged** by the fix on the same graph - they must keep counting runtime edges.
3. A topology fixture with a runtime-only edge shows that edge affecting reachability and *not* affecting the critical path.
4. Every existing fixture's output is unchanged, since none contains a runtime edge. Full suite green.

## Fix Implemented

`build_edg` now builds **two** graphs, which is what `build_element_graph`'s docstring described all along:

- `edg.G` - the **gating** graph, `exclude_dependency_types={"runtime"}`. Used by everything that models build scheduling: critical path, `max_depth`, level decomposition, choke points, slack, and the `sensitivity` ranking.
- `edg.G_full` - every edge, used by `analyze_deferrability`, because "does anything depend on this element" is a reachability question and a runtime dependent still counts.

`blast_radius`/`downstream_count` needed no change: they go through `bga/graph/edg.py::compute_downstream_count`, which builds its own unfiltered adjacency and was already correct.

### Results on the real `freedesktop-sdk` graph

| | before | after |
|---|---|---|
| edges in the structural graph | 502 | **475** (27 runtime edges removed) |
| `metrics.critical_path_length` | 32 | **28** |
| `len(signals.critical_path)` | 28 | 28 |
| `sensitivity.critical_path_us` | 32000 | **28000** |
| `floors.t_infinity_observed` | 28000 | 28000 |
| `metrics.max_depth` | 31 | **27** |
| cross-checks agreeing | 1/3 | **3/3** |
| `blast_radius` | 85 entries | **unchanged, byte-identical** |

Every existing fixture's output is byte-identical before and after, verified on both real `examples/06` captures - none of them contains a runtime edge, which is the whole reason this survived.

Tests: 6 new (`tests/unit/test_runtime_edge_gating.py`). They exist as much to give the suite a shape it did not have as to pin behaviour: **before this file, no fixture in the repository contained a single `runtime` dependency.** They cover the gating/full split in both directions, the critical-path symptom in miniature (3 elements gated versus 4 unfiltered), that a graph without runtime edges yields identical graphs, and that deferrability still counts a runtime dependent.

## Verification Log

Filed 2026-08-17 (round 5). The graph is a real `bst show`-derived capture: `tools/bst_show_to_graph.py` run against a real shallow clone of `freedesktop-sdk` (commit `953683f`, BuildStream 2.7.0, `min-version: 2.5`), taking `components/zlib.bst`'s full closure - 85 elements, 502 dependencies, 9 distinct element kinds. No build was performed; every quantity quoted here is a function of the graph alone.

The two longest-path figures (32 unfiltered, 28 build-only) were computed independently with a standalone topological pass over that graph, not read out of `bga`, and they match the two numbers `bga` reports exactly - which is what identifies runtime edges as the cause rather than merely correlating with it. The dependency-type counts are from the same file.

One false start is worth recording: the mismatch first appeared with a trace whose task timeline did not respect the declared dependencies, where a disagreement between an observed-timeline critical path and a declared-graph one would have been my fixture's fault rather than a defect. Rebuilding the trace so each task starts when its last predecessor finishes reproduced the mismatch unchanged, which is what made it worth pursuing.
