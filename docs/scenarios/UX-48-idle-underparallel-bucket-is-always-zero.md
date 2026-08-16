# UX-48: all idle capacity is booked to `IDLE_NO_TASKS`, so the bucket that means "raise `--builders`" is always 0.00s

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-36 (which correctly relabelled these buckets as occupancy - this is about which bucket the time lands in, not what the unit is)

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

## Verification Log

Filed 2026-08-16 (round 2). The `_compute_bucket_totals` body is quoted verbatim from `bga/utilisation/__init__.py`. All four bucket blocks are pasted from real `bga utilisation`/`bga analyze -f json` runs in this session; three are real BuildStream 2.7.0 captures of `examples/06-macro-micro-optimization` under a real `bwrap` sandbox on a 4-core host, and the fourth is the committed synthetic scale fixture (`tools/gen_synthetic_scale_run.py`). `run-06-opt-b2j2`'s two-builder capacity was read from that run's own `run-context.json` (`resource_capacities: {PROCESS: 2}`), and the six-ready-tasks claim is a property of the `optimized/` project's declared graph, where every `lib-*.bst` depends only on `core.bst`. That `IDLE_UNDERPARALLEL` is never assigned anywhere was confirmed by searching the whole package, not inferred from the four zero readings.
