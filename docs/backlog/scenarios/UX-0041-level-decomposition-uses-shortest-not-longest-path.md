# UX-41: the parallelism profile decomposes levels by *shortest* path from a root, so every element under a common base collapses into one level

**Priority:** High | **Status:** 🟢 Done | **Depends on:** —

## Motivation

Found by the round-2 scale probe (`docs/design/directions.md`'s own next-round item 3): a synthetic but realistically-shaped 1202-element run - a `toolchain.bst` import that everything depends on, twelve layers of 100 modules each with real fan-out/fan-in between adjacent layers, and an `all.bst` stack. Reproduce it with `tools/gen_synthetic_scale_run.py /tmp/run-scale-1200`.

The graph genuinely has 14 levels of width ~100. `bga` reports 3:

```text
$ bga analyze -f json /tmp/run-scale-1200 | jq .structural.parallelism
  levels:         [0, 1, 2]
  width_at_level: [1, 1200, 1]
  max_width: 1200,  min_width: 1,  mean_width: 400.7
```

against the correct longest-path decomposition, computed independently over the same `graph.json`:

```text
  correct levels: 14   widths = [1, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 1]
```

The cause, read directly from `bga/structural/analyzer.py::_compute_level_decomposition`: it is a **BFS from the roots with first-visit-wins**, which assigns each node its *shortest* distance from a root. `toolchain.bst` is a root and all 1200 modules depend on it directly, so every one of them is at BFS distance 1 and lands in level 1 - regardless of the twelve layers of dependencies between them.

Two independent numbers in the same report block therefore contradict each other about the same graph: `metrics.max_depth` is **13** (computed elsewhere, by longest path, and correct), while `parallelism.levels` says there are **3** levels.

**This is not a scale artifact - it is already wrong on the small example projects, where it reads as a plausible number.** Real `bga analyze -f json` output for `examples/06-macro-micro-optimization` (11 elements):

```text
  reported: levels = [0, 1, 2]   width_at_level = [1, 9, 1]   max_depth = 9
  correct:  levels = 10          widths = [1, 2, 1, 1, 1, 1, 1, 1, 1, 1]
```

The reported `max=9.0x` looks like a reasonable parallelism figure for that project. It is not one: the project's real maximum level width is 2.

A base/toolchain element that every other element depends on is the *normal* shape of a real BuildStream project, so this collapse is the common case, not an edge case.

## Required Fix

Compute the level decomposition by **longest path from a root** (the standard DAG level/depth decomposition, and the only one that means anything for "how wide is this build at its widest point"): topologically order the graph, then `level[v] = max(level[u] + 1 for u in preds(v))`, defaulting to 0 for roots. That is O(V+E) - the same order as the current BFS - and is already effectively what `metrics.max_depth` computes, so the two numbers would stop disagreeing.

Consumers to re-check once it changes, all in `bga/structural/analyzer.py`:

- `compute_parallelism_profile` - `max_width`/`min_width`/`mean_width`/`parallelism_efficiency` are all derived from these widths and are all currently wrong on any graph with a common base element.
- The `widths` computed at line 117-118 for the structural metrics block.
- `bga/report/text.py`'s `Parallelism Profile: min=Nx, max=Nx` line, which is the user-visible face of this.

Worth checking in the same pass whether `parallelism_efficiency`'s own formula still means what its name says once the widths are right.

## Out of Scope

- `metrics.max_depth` and the critical path, both of which are computed by longest path already and are correct.
- Whether a level-width profile is the *right* parallelism signal at all (`occupancy_ratio`, `UX-27`, is the measured one) - this task is about the existing signal being wrong, not about replacing it.

## Acceptance Test

1. The 1202-element scale fixture reports 14 levels with widths `[1, 100 × 12, 1]`, and `max_width == 100`.
2. `examples/06-macro-micro-optimization` reports 10 levels with `max_width == 2`.
3. `metrics.max_depth` and `len(parallelism.levels) - 1` agree on every fixture in `tests/fixtures/topologies.py`.
4. A graph with no common base element (e.g. `independent_branches`) is unchanged, since BFS and longest-path agree there. Full suite green.

## Fix Implemented

`_compute_level_decomposition` is now a topological longest-path pass, deliberately using the *same* recurrence `compute_structural_metrics` already used for `max_depth` - `level[v] = max(level[u] + 1 for u in preds(v))`, 0 for roots. The two numbers now agree by construction rather than by coincidence, which is the property the acceptance test pins. Still O(V+E).

The fix is four lines. What is worth recording is that `compute_structural_metrics`'s own comment, twenty lines above, already spelled out why longest-path is the correct measure and explicitly warned that a shortest-path routine "silently underestimates depth whenever a node is reachable via both a short path and a longer one" - and the level decomposition then did exactly that. The reasoning was written down and not applied.

Real results, all three from real `bga graph -f json` runs:

| run | before | after |
|---|---|---|
| 1202-element scale fixture | 3 levels, `[1, 1200, 1]`, `max_width 1200` | **14 levels**, `[1, 100 × 12, 1]`, `max_width 100` |
| `examples/06` baseline | 3 levels, `[1, 9, 1]`, `max=9.0x` | **10 levels**, `max=2.0x` |
| `examples/06` optimized | 3 levels, `max=9.0x` | **5 levels**, `max=6.0x` |

The last row is the one that matters for the tool's purpose. Baseline and `optimized/` differ by exactly the macro optimization this project exists to demonstrate - a six-deep chain replaced by a six-wide fan-out - and the metric previously reported **the same `max=9.0x` for both**, because it was reporting the element count. It now reports 2.0x and 6.0x, so the optimization is visible in the number for the first time.

Tests: 8 new (`tests/unit/test_level_decomposition.py`). Four target the defect and were confirmed to fail against the old implementation with the exact reported symptom (`width_at_level=[1, 12]`, `max_width=12`); four pin the shapes BFS already got right - chain, fan-out, diamond - so a future rewrite cannot fix the common-base case by breaking those. Full suite 774 passed (up from 766), `make lint` clean.

**Found while verifying, filed rather than folded in:** `parallelism_efficiency` is `mean_width / max_width`, which measures how *uniform* the level widths are, not how parallel the build is - a pure serial chain scores 1.000 and a fan-out scores 0.667. This doc's Required Fix asked to check whether that formula "still means what its name says once the widths are right"; it does not, and it did not before either. Correcting the widths makes it more visible (`examples/06` optimized now scores 0.367 against the baseline's 0.550 - the better graph scoring worse), but redefining a published metric belongs in its own task rather than inside this one. Filed as `UX-49`.

## Verification Log

Filed 2026-08-16 (round 2). The reported values are pasted from real `bga analyze -f json` runs against the 1202-element scale fixture and against a real `bst --builders 4 --max-jobs 4 build all.bst` capture of `examples/06-macro-micro-optimization`. The correct level decomposition was computed independently, directly over each run's own `graph.json`, by a standalone topological longest-path pass - not by a second call into `bga`. The BFS-with-first-visit-wins cause was read from `bga/structural/analyzer.py`, not inferred from the output.

Re-verified against the committed fixture. The scale run was originally synthesized ad hoc; `tools/gen_synthetic_scale_run.py` was then written so this doc's acceptance test is actually runnable, and every number above was re-measured against its output rather than carried over. The regenerated fixture has 3500 dependencies against the original's 3206 - the edge count differs, and the reported decomposition does not: still `levels [0, 1, 2]`, widths `[1, 1200, 1]`, against `max_depth: 13` in the same block. That the defect is insensitive to the exact edge count is itself worth knowing; it depends only on the common base element.
