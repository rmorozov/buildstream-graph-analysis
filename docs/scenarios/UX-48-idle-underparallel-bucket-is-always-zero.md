# UX-48: all idle capacity is booked to `IDLE_NO_TASKS`, so the bucket that means "raise `--builders`" is always 0.00s

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-36 (which correctly relabelled these buckets as occupancy - this is about which bucket the time lands in, not what the unit is)

## Motivation

The utilisation block splits idle capacity two ways, and the split is the whole reason the block is actionable:

- **`IDLE_NO_TASKS`** - nothing was ready to run. The graph is too narrow. The fix is *macro*: restructure dependencies.
- **`IDLE_UNDERPARALLEL`** - work was ready but nothing was scheduled to run it. The fix is one flag: `--builders`.

These point a user at opposite halves of the optimization cycle. `bga` never reports the second one. From `bga/utilisation/__init__.py::_compute_bucket_totals`:

```python
# Split idle between NO_TASKS and UNDERPARALLEL
# Simplified heuristic: if no tasks ready, it's NO_TASKS
# If tasks were ready but not scheduled, it's UNDERPARALLEL
# For now, assign all to IDLE_NO_TASKS
self.buckets[CPUBucket.IDLE_NO_TASKS] = idle_cpu_us
```

`IDLE_UNDERPARALLEL` is never assigned. It renders as `0.00s` on every run, and the number next to `Idle No Tasks` is the *total* idle regardless of cause.

Four real runs, including one built specifically to be the textbook underparallel case:

```
run-06-opt-b2j2   (--builders 2, six independent libs ready)
  Useful                  42.45s
  Idle No Tasks           72.30s
  Idle Underparallel       0.00s     <- should be most of the 72.30s

run-06-optimized  (--builders 4)
  Useful                  61.45s
  Idle No Tasks           48.55s
  Idle Underparallel       0.00s

run-06-baseline   (--builders 4, six-deep chain)
  Useful                  40.25s
  Idle No Tasks          118.03s     <- this one is genuinely NO_TASKS
  Idle Underparallel       0.00s

run-scale-1200    (the committed 1202-element fixture, 16 builders)
  Useful                5768.05s
  Idle No Tasks          138.52s
  Idle Underparallel       0.00s
```

`run-06-opt-b2j2` is `examples/06-macro-micro-optimization/optimized` - six libraries that depend only on `core.bst` and on nothing else - built with `resource_capacities: {PROCESS: 2}`. Six tasks ready, two builders. **Four tasks were ready and unscheduled for most of the run**, and the report attributes all 72.30s of idle to "no tasks were ready", which is the one thing that is definitely false about that run.

The misdirection is the damage, not the missing number. A user reading `Idle No Tasks 72.30s` is being told their dependency graph is too narrow and sent off to restructure it - when the graph is already the *optimized* one and the actual fix is `--builders 4`. `run-06-baseline` is the run where `IDLE_NO_TASKS` is genuinely correct, and the two are indistinguishable in the report.

Found by the placeholder sweep that `UX-41`/`UX-43`/`UX-44` motivated (`docs/design-directions.md`, round-2 section): same shape as those three - a few lines, a comment openly describing the unimplemented intent, a name in the default report that promises a real computation. This one is outside `bga/structural/`, which is why the sweep was worth running.

## Required Fix

Classify idle capacity by whether work was ready at that instant.

1. **Derive the ready set over time.** For each idle sub-interval, a task is *ready* if all its predecessors have finished and it has not started. That is computable from the dependency graph plus the task start/finish timestamps that already exist - no new capture. `bga/diagnostics/analyzer.py::compute_ready_queue_metrics` already builds something close to this (and carries its own `# Simplified:` caveat, worth reconciling in the same pass rather than maintaining two ready-queue notions).
2. **Attribute the split.** Idle capacity in an interval with a non-empty ready queue is `IDLE_UNDERPARALLEL`; with an empty one it is `IDLE_NO_TASKS`. Intervals that are partly one and partly the other must be split at the boundary, not rounded to whichever dominates - the sum across buckets is load-bearing for `I9`/`total_accounted_us`, which currently reconciles to 0.00% error and must continue to.
3. **Do not stop at the split.** `IDLE_UNDERPARALLEL` next to the capacity that produced it is a directly actionable recommendation ("2 builders, up to 4 tasks ready - `--builders 4` is worth trying"), and `bga sweep` already answers the follow-up question. Wiring the two is the payoff; the bucket alone just stops lying.
4. **Note the interaction with capacity provenance.** The whole idle computation is gated on `cpu_accounting_available`, and `_compute_idle_cpu_time` returns 0 without it - so on a run with no capacity at all both buckets stay 0 and that remains correct. `UX-36`'s distinction between measured and merely-detected capacity applies here unchanged: the split is only as good as the denominator.

## Out of Scope

- `UX-36`'s occupancy-vs-CPU labelling, which is correct and orthogonal - these are slot-seconds either way, and this task does not make them CPU-seconds. `UX-45` is the one that would.
- `WASTED_RETRY`/`WASTED_REBUILD`, which are separately computed and are legitimately 0 on runs with no retries or rebuilds.
- Changing `--builders` automatically, or recommending a specific value beyond what `bga sweep` already computes.

## Acceptance Test

1. A real `--builders 2` capture of `examples/06-macro-micro-optimization/optimized` books the majority of its idle to `IDLE_UNDERPARALLEL`.
2. A real `--builders 4` capture of the **baseline** (six-deep chain) books the majority of its idle to `IDLE_NO_TASKS` - the discrimination between these two runs is the test, not either number alone.
3. `total_accounted_us` and `reconciliation_error_pct` are unchanged on every fixture: this moves time between buckets and must not create or destroy any.
4. A run with `cpu_accounting_available == False` still reports both idle buckets as 0. Full suite green.

## Fix Implemented

**No new capture was needed.** `NormalizedTask.ready_us` is already a real `max(finish(predecessors))`, computed in `bga/normalize/timestamps.py` from the dependency graph. A task is *pending* over `[ready_us, start_us)` - dependency-ready but not dispatched - which is exactly the ready-set signal this task needed, so the fix threads `ready_us` through to the utilisation analyzer rather than plumbing the graph into it or building a second ready-queue notion.

Idle capacity is then split by a boundary sweep: in each slice where at least one task is pending, free slots (`effective_cpus − running`) are `IDLE_UNDERPARALLEL`. `IDLE_NO_TASKS` is the **remainder** rather than a second independent sum, so the two always add back to exactly `idle_cpu_us` and I9 reconciliation cannot drift on rounding - confirmed at 0 unaccounted, 0.00% error on real runs.

### Real results

```
run-06-opt-b2j2  (--builders 2, six independent libraries)
  Useful                  42.45s
  Idle No Tasks           54.30s      (was 72.30s)
  Idle Underparallel      18.00s      (was 0.00s)
  -> 18.00s of that idle capacity had work ready and waiting for a builder: raising build
     concurrency is the lever here (`bga sweep` estimates the payoff).
  -> 54.30s had nothing ready to run at all - no amount of extra concurrency helps that;
     it is a dependency-graph shape problem.

run-06-baseline  (--builders 4, six-deep chain)
  Idle No Tasks          118.03s
  Idle Underparallel       0.00s      <- correctly zero: a chain never has anything waiting
```

The 18.00s is exactly right and was checked by hand against that run's own timings: `lib-c`/`lib-d` waited 5s and `lib-e`/`lib-f` waited 9s, with 2 builders busy of 4 CPUs, giving `2 free × 5s + 2 free × 4s = 18s`.

`run-06-optimized` (`--builders 4`) reports **0** underparallel even though tasks queued, and that is the discrimination that keeps this signal honest: its waiting tasks had no free capacity beside them. Four busy builders on a four-CPU host is saturation, not underparallelism, and more builders would not help. "Something was queued" alone would have been the wrong test.

Point 3 of the Required Fix - not stopping at the split - is the two `->` lines above, which name the lever rather than leaving a reader to infer it from two similar-looking numbers.

### One acceptance criterion was wrong and is corrected here

Acceptance test 1 as filed asked for the builder-starved run to book "the majority of its idle" to `IDLE_UNDERPARALLEL`. The measured answer is 18.00s of 72.30s - **25%, not a majority** - and the measurement is right, not the criterion. The remaining 54.30s is real `NO_TASKS` time: early in that build `core.bst` runs alone for 14s with genuinely nothing else ready, and that idle could not have been used by any number of builders. The criterion was written before implementing, from the assumption that a starved run is starved throughout. What the test should have asked - and what the shipped tests assert - is the *discrimination*: substantial underparallel time on the starved run, exactly zero on both the chained baseline and the saturated `optimized/` run.

Tests: 8 new (`tests/unit/test_idle_bucket_split.py`), including the saturation case above, exact reconciliation, and absent-`ready_us` data reporting 0 rather than a confident "nothing was ready". One of them pins a real bug from this implementation: an earlier draft clamped the boundary sweep to `[0, wall_clock_us]`, but real captures carry absolute epoch timestamps (~1.79e15 µs) while `wall_clock_us` is a duration (~2.5e7), so every real boundary was discarded and the sweep returned 0 on the very run this task is about. Full suite 803 passed (up from 795), `make lint` clean.

## Verification Log

Filed 2026-08-16 (round 2). The `_compute_bucket_totals` body is quoted verbatim from `bga/utilisation/__init__.py`. All four bucket blocks are pasted from real `bga utilisation`/`bga analyze -f json` runs in this session; three are real BuildStream 2.7.0 captures of `examples/06-macro-micro-optimization` under a real `bwrap` sandbox on a 4-core host, and the fourth is the committed synthetic scale fixture (`tools/gen_synthetic_scale_run.py`). `run-06-opt-b2j2`'s two-builder capacity was read from that run's own `run-context.json` (`resource_capacities: {PROCESS: 2}`), and the six-ready-tasks claim is a property of the `optimized/` project's declared graph, where every `lib-*.bst` depends only on `core.bst`. That `IDLE_UNDERPARALLEL` is never assigned anywhere was confirmed by searching the whole package, not inferred from the four zero readings.
