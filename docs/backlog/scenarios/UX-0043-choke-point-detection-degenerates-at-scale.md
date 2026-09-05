# UX-43: "choke point" is `fan-in >= 2 and fan-out >= 2`, so 43% of a real-shaped 1200-element graph is reported as a bottleneck

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-33 (which made these names visible, and is how this became legible) | **Topic:** analysis | **Area:** bga/structural

## Motivation

Round-2 scale probe, 1202-element run:

```text
Structural Analysis:
  Elements: 1202, Edges: 3500, Max Depth: 13
  Bottlenecks Identified: 606 - layer01/mod003.bst, layer01/mod004.bst, layer01/mod007.bst,
    layer01/mod008.bst, layer01/mod009.bst, layer01/mod011.bst, layer01/mod012.bst,
    layer01/mod015.bst (+598 more, see --format json)
```

**606 of 1202 elements - 50.4% - are reported as bottlenecks.** A signal that fires on half the graph is not a signal.

The definition, read from `bga/structural/analyzer.py::compute_bottleneck_analysis`, is a pure local degree test:

```python
# Simple heuristic: high fan-in + high fan-out elements
for node in G.nodes():
    if G.in_degree(node) >= 2 and G.out_degree(node) >= 2:
        choke_points.append(node)
```

The comment two lines above it says *"Find choke points (articulation points in undirected version) / For DAGs, use dominator-based approach"* - so the intended definition is a real graph-theoretic one, and what shipped is a placeholder that never got replaced. On a small graph the placeholder happens to select few enough nodes to look plausible (`examples/06` reported 5, and those 5 really were the artificial chain). On any realistically-sized layered graph, "has two parents and two children" is simply the common case.

`UX-33` made these names visible rather than a bare count, which is what turned this from an unremarkable integer into an obviously broken list - the count `5` looked fine; `606 - layer01/mod003.bst, layer01/mod004.bst, ...` does not.

Note the threshold is not the problem and raising it is not the fix: fan-in/fan-out say nothing about whether work actually funnels through a node. `nx.descendants` is already called for every candidate to compute `choke_point_impact`, so the expensive part of a real answer is already being paid for.

## Required Fix

Replace the degree heuristic with a definition that means "work genuinely funnels through this element". Two real candidates, in increasing cost - a design decision to make when picked up:

1. **Dominators**, which the code's own comment already proposes and which `bga` already computes elsewhere (`bga/graph/edg.py`, used for the `dominator_coverage` hard gate). An element that dominates a large fraction of the graph is a real choke point in the sense a build owner means: nothing downstream of it can start until it finishes. This also gives a natural ranking (dominated-set size) instead of an unordered list.
2. **Weighted by real measured time** - dominated *duration* rather than dominated count, which is what actually determines whether removing the choke point buys anything. `blast_radius` already combines downstream count with duration this way, and the two signals should probably agree.

Whatever is chosen, it needs a bound on how many are reported and a ranking, not just a filter: on a 1200-element graph even a correct definition can select more than a report line can hold, and `UX-33`'s existing `(+N more, see --format json)` overflow line is the right shape for that.

## Out of Scope

- `blast_radius` (`bga/analyzer.py`), which is a different, already-useful signal and is correct - the scale run ranked `toolchain.bst` (1201 downstream) then `layer00/mod025.bst` (795) then `layer00/mod011.bst` (754), which is exactly right.
- `UX-33`'s rendering, which is doing its job - the list is legible, and what it makes legible is that the underlying set is wrong.

## Acceptance Test

1. The 1202-element scale fixture (`tools/gen_synthetic_scale_run.py`) reports a bottleneck set that is a small, ranked fraction of the graph rather than 50% of it.
2. `examples/06-macro-micro-optimization` still identifies its real serialized chain (`lib-a`..`lib-e`), which is the case the current heuristic gets right.
3. A graph with a genuine single funnel (`tests/fixtures/topologies.py::fan_in` / `diamond`) identifies that element and not much else.
4. `choke_point_impact` remains populated and consistent with whatever definition ships. Full suite green.

## Fix Implemented

A choke point is now an element that **nothing else can overlap with**: every other element in the build is either strictly upstream or strictly downstream, so when it runs, it runs alone. Equivalently `|ancestors| + |descendants| == N - 1`. Ranked by descendant count, so `UX-33`'s existing cap shows the ones worth reading first.

**The dominator approach this doc proposed was implemented, measured, and rejected on real data** - recorded here because the code's own comment had been pointing at it for a long time and the next person would otherwise try it again.

Dominance asks *"does every **path** to B pass through A"*, which is the right question for a control-flow graph, where exactly one path is taken at run time. BuildStream dependencies are **conjunctive** - every predecessor must finish, so all paths are taken. On the 1202-element fixture, where each module depends directly on `toolchain.bst`, the measurement is decisive:

```text
$ nx.immediate_dominators(G + virtual root)
nodes whose immediate dominator is the virtual root: 1201 of 1202
```

Nothing dominates anything, because every module is reachable from the root without passing through any other module. The signal is vacuous on exactly the graph shape this task exists to fix. Overlap is the property that actually matters for a build, and it is exact rather than heuristic.

### Real results

| run | before | after |
|---|---|---|
| 1202-element scale fixture | 606 (50.4%) | **1** - `toolchain.bst` |
| `examples/06` baseline | 5 | **9** - `toolchain`, `lib-a`..`lib-f`, `app`, `all` |
| `examples/06` optimized | 5 | **3** - `toolchain`, `app`, `all` |

The last two rows are the point. Baseline and `optimized/` differ by exactly one macro change - six chained libraries fanned out - and the new signal shows the whole chain in one and none of it in the other. The old heuristic reported 5 for both. Note it also correctly *excludes* `core.bst` in both variants, despite `core.bst` being the heaviest element: `codegen.bst` genuinely runs alongside it, so it is not a serialization point. That is what `blast_radius` is for, and it already ranks `core.bst` first.

Cost is one `descendants` + one `ancestors` sweep per node - 0.2s for all 1202 nodes of the scale fixture, measured, which is noise beside `UX-42`'s 115s.

Tests: 8 new (`tests/unit/test_choke_points.py`) - the diamond (identifies the waist, not the concurrent pair), a layered graph built to trigger the old heuristic on every node, and the baseline-vs-fanned discrimination above. Two of them caught real mistakes in my own first draft of the *test* rather than the code: I asserted `lib-a` would be a choke point in a graph where only `lib-b` declared `codegen`, and asserted `core` would remain one after fanning out - the implementation was right both times and the assertions were guesses. Full suite 795 passed (up from 787), `make lint` clean.

## Verification Log

Filed 2026-08-16 (round 2). The report block is pasted from a real `bga graph` run against the 1202-element scale fixture; the 606/1202 ratio was confirmed against the same run's `--format json` `structural.bottleneck.choke_points` array rather than counted from the text. The `fan-in >= 2 and fan-out >= 2` definition and the unimplemented dominator-based intent were both read from `bga/structural/analyzer.py` directly.

Re-verified against the committed fixture. The original ad-hoc scale run gave 520/1202 (43.3%); regenerating it reproducibly via `tools/gen_synthetic_scale_run.py` - written so this doc's acceptance test is runnable - gives 606/1202 (50.4%) on a graph with 3500 edges rather than 3206. Every number above is the re-measured one. The ratio moving with edge density is exactly what a pure degree test would do, and is further evidence the signal is tracking density rather than funnelling.
