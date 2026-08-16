# UX-35: the `RESOURCE WAIT` next-step hint tells an already-oversubscribed run to raise its capacity

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-04 (done - this is a correctness fix to the hints it added), UX-12/UX-29 (the capacity facts the hint should consult)

## Motivation

`UX-04` added a static per-category "what to do about it" line under Biggest Opportunity. The hints are constant strings, chosen by attribution category alone. Real run, `examples/06-macro-micro-optimization/optimized`, `bst --builders 4 --max-jobs 4` on a **4-core** host:

```
  Biggest Opportunity: 32.7% of wall-clock time is RESOURCE WAIT (9.00s)
    -> a resource (PROCESS/DOWNLOAD/UPLOAD) was saturated - try --capacity N with a higher N,
       or `bga sweep` to find the real knee point
```

The run is already dispatching up to `builders × max-jobs = 16` concurrent processes on 4 cores. Plane 2 measured the cost of that on this exact project: `core.bst`'s eight translation units cost 11.05s of process lifetime with the host to themselves and 20.00s with five siblings compiling alongside - same source, +81%. Raising `--builders` is the wrong direction, and the report says to do it in the line explicitly labelled as the next step.

The hint's fallback advice is no better on this run: `bga sweep`'s knee point stops at the first flat step and under-reports capacity by a factor of two (`UX-30`).

The hint is not wrong *in general* - `RESOURCE WAIT` on an under-provisioned host really does mean "raise capacity". It is wrong here because it is issued without looking at any of the capacity facts the tool already has, or could have: `host_cpu_count` (auto-detected, present in this run's own run-context), `cpu_budget` (`UX-15`), `builders` (present), `native_max_jobs` (`UX-29`).

## Required Fix

Make the hints conditional on the run's own capacity picture rather than on the attribution category alone:

- `RESOURCE WAIT` **and** `builders × native_max_jobs` already at or above the governing core count → say the opposite: the dispatch queue is saturated because the host is, and more builders will make it worse; the lever is less native parallelism per element, fewer builders, or less work.
- `RESOURCE WAIT` **and** real headroom against the governing core count → the current hint, unchanged.
- Capacity facts unavailable → say the hint is unconditioned rather than asserting a direction. This is the `UX-25`/`UX-11` house pattern: name the missing input instead of guessing.

Worth reviewing the other seven category hints in the same pass for the same class of unconditional advice.

## Out of Scope

- `UX-28` (the oversubscription threshold that would supply the "is this host saturated" verdict) and `UX-29` (auto-extracting `native_max_jobs`). This hint should consume their answer; it should not grow a second, independently-derived capacity formula - the exact divergence `UX-17` was resolved to avoid.
- `UX-30`'s knee-point algorithm, which this hint links to.

## Acceptance Test

1. On the real run above, the `RESOURCE WAIT` hint no longer recommends raising capacity.
2. On a genuinely under-provisioned run (capacity well below the governing core count) it still does.
3. With no capacity data at all, the hint says so instead of picking a direction. Full suite green.

## Verification Log

Filed 2026-08-16. The hint text is pasted from a real `bga analyze -d` against a real `bst --builders 4 --max-jobs 4 build all.bst` capture of `examples/06-macro-micro-optimization/optimized` (BuildStream 2.7.0, real `bwrap` sandbox, 4-core host). The 11.05s vs 20.00s contention figures come from two real Plane 2 traces of the same project.
