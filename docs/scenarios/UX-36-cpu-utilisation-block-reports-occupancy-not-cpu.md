# UX-36: the report's `CPU Utilisation` block prints task-occupancy seconds under a CPU label - the code says so, the report does not

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** P1-33 (which established the honest internal meaning), UX-13 (the same report-honesty fix, already applied to the floors block)

## Motivation

Real output, `examples/06-macro-micro-optimization`, the same project built twice - once with a serialized graph, once with the identical work correctly parallelized:

```
baseline (39.57s wall)            optimized/ (27.50s wall)
CPU Utilisation:                  CPU Utilisation:
  Effective CPUs: 4.0               Effective CPUs: 4.0
  Reconciliation Error: 0.00%       Reconciliation Error: 0.00%
  Useful                  40.25s    Useful                  61.45s
  Idle No Tasks          118.03s    Idle No Tasks           48.55s
```

Read as CPU time - which is what the heading, the `Effective CPUs` line, and the units invite - this says the faster build burned 53% more CPU for identical source, identical compiler, identical flags. That is not what happened, and a user acting on it would conclude the optimization was expensive when it was free.

`Useful` is the sum of task **occupancy** (how long each task held a dispatch slot), not CPU time. It grew because tasks that used to run one after another now overlap and each one takes longer in wall-clock under contention - the `UX-09` effect, real and measurable. Occupancy is a perfectly good number; it is simply not CPU.

The codebase already knows this and says so, in `bga/utilisation/__init__.py`:

> Bucket totals - real, measured wall-clock task-occupancy time (how long each task held a job slot...). **P1-33: it was never actually a CPU-time measurement, just labeled as CPU-microseconds** - keeping it under its own honest meaning, not removing it.

and `cpu_accounting_available` is `False` on every run produced by the documented pipeline, which correctly makes `useful_pct`/`idle_pct` return `None`. The honesty stops at the module boundary: `bga/report/text.py` still renders the section as `CPU Utilisation`, still prints `Effective CPUs`, and still prints the raw bucket seconds with no note that they are occupancy and that no CPU accounting was available for this run.

This matters beyond wording. The `Useful`/`Idle No Tasks` ratio is, on these two runs, the *only* number in the whole report that moves in the right direction across a real optimization (25.4% → 55.9% of dispatch capacity used, against an `efficiency_score` that moved 1.00 → 0.83 - see `UX-27`). It is the natural basis for a work-vs-span efficiency signal and for `UX-39`'s CI gate. Building on it requires its meaning to be stated where people read it.

## Required Fix

1. Rename or qualify the section so it cannot be read as CPU time when `cpu_accounting_available` is `False` - e.g. `Dispatch Occupancy` with a one-line note, mirroring how `UX-13` added a real capacity-model caveat to the Certified Floors block rather than deleting the numbers.
2. Only print `Effective CPUs` alongside a stated `effective_cpus_source` (`UX-17` already computes it) - `4.0` sourced from `detected_host_cpu_count` means something different from `4.0` sourced from real accounting, and today they render identically.
3. State explicitly, once, that no real CPU accounting was available for this run, rather than leaving `Reconciliation Error: 0.00%` to imply that something was reconciled.
4. When real `cpu_accounting` *is* present, keep today's labels - they are then accurate.

## Out of Scope

- Acquiring real CPU accounting. `getrusage` in the Plane 2 hook's destructor would give genuine per-process CPU time and is the real fix to the underlying gap, but it is a capture change and belongs in its own task (noted under `UX-32`'s Out of Scope for the same reason).
- Changing the bucket computation itself - it is correct under its own honest meaning.

## Acceptance Test

1. A run with no `cpu_accounting` no longer presents occupancy seconds under an unqualified CPU heading.
2. `Effective CPUs` is shown with its provenance.
3. A run with real `cpu_accounting` renders as it does today.
4. `tests/fixtures/golden/` snapshots updated deliberately, not incidentally. Full suite green.

## Verification Log

Filed 2026-08-16. Both report blocks are pasted from real `bga analyze -d` runs against real `bst --builders 4 --max-jobs 4 build all.bst` captures of `examples/06-macro-micro-optimization` and its `optimized/` variant (BuildStream 2.7.0, real `bwrap` sandbox, 4-core host). The P1-33 comment is quoted verbatim from `bga/utilisation/__init__.py`.
