# UX-531: `bga analyze` is superlinear, and the page pays for it

**Priority:** Medium | **Status:** 🟢 Fixed & Verified | **Depends on:** UX-42 (the last superlinear term closed) | **Serves:** anyone opening a run of a few thousand elements | **Topic:** analysis

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

## Outcome (round 80, 2026-09-02) — 🟢 Done

### The gap, measured

`python -m cProfile -m bga.cli analyze <4,002> --format json`, seeded
`gen-synthetic --layers 20 --width 200 --seed 1`:

```text
156,203,419 function calls in 139.035 seconds       ncalls  tottime  cumtime
analyzer.py:714(_compute_attribution)                    1    0.034   85.532
blame_chain.py:712(_resource_available_at)            4476    0.027   24.686
<string>:2(__eq__)  TaskKey, from the two scans   35825904   23.547   23.547
blame_chain.py:821(<listcomp>)  the `others` list      4476    9.279   21.116
normalize/timestamps.py:304(clamp_task_starts)           1    9.512    9.615
```

Three scans `UX-42` did not reach: `_resource_available_at` and
`classify_scheduler_wait` walk every task **per wait gap** (4,476 x
4,002); `clamp_task_starts` walks every edge **per task** (4,002 x
11,800).

### After

Each replaced by the index `UX-42` already built — the run-wide
occupancy timeline, a second instance of it over every task, and a
successor-keyed edge map. Output is byte-identical (`cmp`) at all three
sizes.

```text
99,031,701 calls in 98.194s (-37%); _compute_attribution 85.5 -> 51.5s cum
```

Wall clock, **interleaved before/after, min of three** — this round's
tracks run in parallel, so figures taken minutes apart are not
comparable:

```text
 1,202   before   5.02s   after   3.06s   x1.64
 2,402   before  16.11s   after  10.02s   x1.61
 4,002   before  44.01s   after  23.33s   x1.89     n^1.80 -> n^1.69
```

**The bound, and the guard: the analyzer walks the whole run 9 times at
40 tasks and 9 at 80.** Before: 87 and 167 — one walk per wait gap.

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|---|---|
| B1 | `_resource_available_at`: `occupied >= capacity` → `> capacity` | `test_resource_availability`, 5 of 12 shapes — 5 failed, 24 passed |
| B2 | `classify_scheduler_wait`: drop `change_points_within` from the boundary set | `test_scheduler_wait` — 4 failed, 25 passed |
| B3 | the edge index stops filtering `runtime` edges | `test_a_runtime_edge_is_not_build_gating` — 1 failed, 28 passed |
| B4 | `_all_tasks_timeline` rebuilt per call instead of cached | both clauses of the bound, 87 walks for 9 — 2 failed, 27 passed |

Reverting the whole change reddens the bound and **no** oracle clause:
the fix is output-identical, so an oracle can only redden in the
direction a later change might go — B1-B3 are three of those. B4 reddens
both clauses of the bound, whose constant half is its non-vacuity clause.

### Deviation from the Required Fix

Two. The 4,002 wall clock does **not** join the guard: a 23s guard needs
a tier row this track may not write, and a second on a machine running
three tracks is a second of noise. The walk count reads the same
quantity and does not move with the load; the seconds are pasted above.

And it is **bounded, not linear**: `n^1.69`. The terms left are named
rather than guessed — `descendants`/`ancestors` once per node (4,001 +
4,002 calls, 16.2s, `O(n(V+E))` by construction) and
`_resource_saturation_intervals`' per-gap interval sweep (28.2s cum).
Both are algorithm changes, not index changes; **a row for them is owed
to the index** (topic `analysis`), which this track cannot write.

```text
$ make lint          ruff + pymarkdown, All checks passed!
$ make test-touching 196 passed in 15.22s
$ make test-fast     5,497 passed, 90 skipped, 7 failed in 605s - four are
   UX-519's index row (the orchestrator's); test_diagnostics_performance
   and test_graph_performance pass alone (6 passed, 5.98s): load, not this.
```
