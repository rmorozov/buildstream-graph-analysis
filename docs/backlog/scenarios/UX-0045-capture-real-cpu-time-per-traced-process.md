# UX-45: the Plane 2 hook is two `clock_gettime` calls away from real per-process CPU time, which would retire three standing "this is not CPU" caveats

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-11 (the hook), UX-23 (element tagging), UX-36 (which established the caveats this would let us retire), UX-27 (`occupancy_ratio`, the metric that most wants a CPU denominator) | **Topic:** capture

## Motivation

`bga` has been carefully honest, across several tasks, about one thing it cannot measure: **it has never had a CPU-time measurement.** `UX-36` put it plainly, and the honesty now costs three separate pieces of report machinery:

- `bga/report/text.py:584` - `"Buckets below are task slot-time (occupancy), not CPU time:"`, because "a reader who takes them for CPU seconds draws the opposite conclusion from a real optimization".
- `bga/report/text.py:557` - the whole section renders as `"Dispatch Occupancy (no real CPU accounting in this run)"` rather than `"CPU Utilisation"`, gated on `effective_cpus_source == 'measured'`.
- `bga/report/text.py:571` - `"Reconciliation: not performed (I9 needs real CPU accounting, absent here)"`. **I9 reconciliation is disabled on every real run captured in this audit.**

And `bga/analyzer.py:419` records the same limitation upstream, where `occupancy_ratio`'s numerator "is slot *occupancy*, not CPU time (P1-33/UX-36), so it inflates" under contention - which is the single stated weakness of the metric `UX-39`'s CI gate now fires on.

Meanwhile Plane 2 already runs code **inside every traced process, at its exit**. `tools/native_trace/hook.c`:

```c
__attribute__((destructor)) static void bst_trace_end(void) {
    write_trace_line("END", monotonic_seconds());
}
```

That destructor is the one place in the entire system with access to the kernel's own accounting for that process. `getrusage(RUSAGE_SELF, &ru)` there yields `ru_utime` + `ru_stime` - real, kernel-measured user and system CPU time for the process that is about to exit - with no sampling, no estimation, and no extra syscall on any hot path. `getrusage(RUSAGE_CHILDREN, ...)` additionally yields the summed CPU of already-reaped children, which matters for `make` and `sh` wrappers.

The scale of the data available is real, not hypothetical. One `bst --builders 4 --max-jobs 4 build all.bst` of `examples/06-macro-micro-optimization` produced **822 START lines and 663 END lines** in a single capture - 663 processes that would each have carried a real CPU-time figure.

The 159-line gap between START and END is itself the honest part of this: those are processes killed by a signal or `exec`'d over, and the hook's own header already documents that they appear as unmatched STARTs. Whatever ships here inherits that limitation - CPU time will be available for the processes that exited normally, and must be reported as a covered *fraction*, never silently summed as if complete.

## Required Fix

1. **Capture it in the hook.** In `bst_trace_end`, call `getrusage(RUSAGE_SELF, ...)` and `getrusage(RUSAGE_CHILDREN, ...)` and add `utime=`, `stime=`, `cutime=`, `cstime=` fields to the END line. `<sys/resource.h>` only; no new dependency; nothing on the START path changes. `getrusage` cannot fail for `RUSAGE_SELF`/`RUSAGE_CHILDREN` with valid arguments, but a non-zero return must still emit the fields as absent rather than as zero - a zero CPU time and an unmeasured one are different claims, and conflating them is exactly the failure mode `UX-36` was written about.
2. **Parse and aggregate it** in `tools/bst_native_build_tracer.py`, alongside the existing wall-clock aggregation, keeping the existing per-element and per-binary groupings. The parser must tolerate END lines without the new fields - old traces, and any hook built before this lands.
3. **Report coverage explicitly.** "CPU time across N of M traced processes (K exited abnormally and are unmeasured)". A per-element CPU total that silently omits a third of its processes is worse than no CPU total.
4. **Then, and only then, revisit the three caveats.** This task's deliverable is the *measurement*; whether Plane 2's per-element CPU time is a legitimate input to Plane 1's `utilisation` buckets and `occupancy_ratio` is a real question with a real obstacle - Plane 2 traces one element at a time under a wrapped build, Plane 1 covers the whole run, and `I9` reconciliation would need both for the same run. **Do not weaken the caveats on the strength of partial coverage.** File the plumbing as a follow-up rather than stretching this task to cover it.

The genuinely new capability this unlocks, independent of the caveats, is a Plane 2 answer to *"is this element's build CPU-bound or waiting?"* - CPU-seconds vs. wall-seconds vs. `native_max_jobs`, per element. That is the question the micro-optimization half of the walkthrough (`docs/audits/case-study-06-macro-micro.md`) could not answer, and it needs no cross-plane plumbing at all.

## Out of Scope

- cgroup-based accounting for the whole run. A different and also-valuable source (`UX-17` already consumes a cgroup quota when present), but it measures the sandbox, not the process, and does not attribute to a binary or an element.
- Statically-linked processes, which `LD_PRELOAD` cannot see at all and which this does not change. `UX-11`'s "Risk 2" disclaimer stands verbatim.
- Any change to `I9` reconciliation itself, per point 4.

## Acceptance Test

1. A real wrapped build of one `examples/06-macro-micro-optimization` element emits `utime`/`stime` on its END lines, and the summed CPU time is within a plausible band of `wall × native_max_jobs` for a known CPU-bound compile.
2. The tracer reports per-element CPU time **and** the covered fraction, and the two are consistent with the START/END counts.
3. A trace captured with the *previous* hook still parses, reporting CPU time as unavailable rather than as zero.
4. A build wrapped with the new hook produces a byte-identical artifact to one built without it - the "never break the wrapped build" requirement from `UX-11` is unchanged. Full suite green.

## Fix Implemented

All four points. `bst_trace_end` now calls `getrusage(RUSAGE_SELF)` and `getrusage(RUSAGE_CHILDREN)` and emits `utime`/`stime`/`cutime`/`cstime` on the END line; the tracer parses them, aggregates per element, and reports coverage.

### The result, from a real wrapped build

`bst --builders 4 --max-jobs 4 build all.bst` over `examples/06-macro-micro-optimization`, BuildStream 2.7.0, real `bwrap` sandbox, 4-core host, 822 traced processes:

```text
Real CPU time (getrusage): 45.56s across 663 of 822 traced processes (159 exited abnormally and are unmeasured)
  core.bst        10.70s CPU over  12.35s wall =  0.87 cores busy  [81% of processes measured]
  codegen.bst      5.90s CPU over   3.36s wall =  1.76 cores busy  [81% of processes measured]
  lib-a.bst        4.56s CPU over   2.68s wall =  1.70 cores busy  [81% of processes measured]
  lib-c.bst        4.36s CPU over   2.61s wall =  1.67 cores busy  [81% of processes measured]
  ...
  app.bst          3.13s CPU over   2.34s wall =  1.34 cores busy  [81% of processes measured]
```

**This is the capability the task was really for.** `core.bst` - the element pinned with `notparallel: True` - runs at **0.87 cores busy** while every sibling runs at ~1.7. The micro-optimization half of `docs/audits/case-study-06-macro-micro.md` could establish that `core.bst` was slow and that it asked for `-j1`; it could not say whether it was CPU-bound or waiting. It was waiting, and now the report says so in measured core-seconds. That needs no cross-plane plumbing at all, which is why it is the part that shipped.

### A real bug this introduced, found by real data

The first working version emitted the line as three `dprintf` calls (header, rusage, command). A real 822-process capture came back with **three corrupted records**, where two processes had interleaved mid-line and produced nonsense element names:

```text
element=lib-c.bstSTART
element=lib-e.bstSTART
element=lib-f.bstEND
```

The trace log is opened `O_APPEND` and written concurrently by every traced process in the build, and `O_APPEND` only guarantees atomicity **per `write()`**. The original single-`dprintf` line was atomic by accident of being one call; splitting it broke that silently. The whole record is now composed into one buffer and written once, and the re-run capture has zero corrupted lines. The comment in `hook.c` says why, because the next person to add a field will be tempted to append a second call.

### What was deliberately not done

Point 4 of the Required Fix, as filed: **the three standing caveats are not weakened.** Plane 2 traces elements under a wrapped build while Plane 1 covers the whole run, and `I9` reconciliation needs both for the same run; 19% of processes here are unmeasured. Wiring this into Plane 1's utilisation buckets is a separate task, and `bga`'s `Dispatch Occupancy` block still says exactly what it said before. The `cpu_time` block carries that statement itself rather than leaving it implicit.

`children_cpu_us` is published but **not** summed into the element total: a parent's `RUSAGE_CHILDREN` already includes CPU its reaped children reported for themselves, so adding both would double-count. Self time is the additive quantity; children time is what makes `make`/`sh` wrappers interpretable.

### Coverage, and why 19% is unmeasured

159 of 822 processes ran no destructor. Two real causes, both already documented in `hook.c`: a process killed by a signal, and - the common one here - `sh -c '<command>'` wrappers that `_exit()` or are replaced by `exec`, bypassing the normal exit path. Those are reported as *unmeasured*, never as zero, and the per-element coverage percentage is printed beside every total.

Tests: 10 new (`tests/unit/test_native_cpu_time.py`), including the two failure modes that would quietly produce wrong numbers - a partial rusage pair (a truncated write leaving `utime=` without `stime=`) must not publish half a measurement, and a pre-`UX-45` trace must report *unavailable* rather than a confident 0.00s. Backward compatibility was checked against a real 822-process capture taken with the previous hook: it parses, keeps its commands intact, and reports CPU as unavailable. Full suite 852 passed, `make lint` clean.

## Verification Log

Filed 2026-08-16 (round 2). The destructor body is quoted verbatim from `tools/native_trace/hook.c`; the three caveats are quoted verbatim from `bga/report/text.py` at the cited lines, and the `occupancy_ratio` note from `bga/analyzer.py:419`. The 822/663 START/END counts are from a real capture in this session (`bst --builders 4 --max-jobs 4 build all.bst` of `examples/06-macro-micro-optimization`, BuildStream 2.7.0, real `bwrap` sandbox), counted directly from the raw trace log. Feasibility was assessed by reading the hook's actual includes and call sites, not assumed - the destructor already performs `open`/`dprintf`/`close` per process, so two `getrusage` calls are not a new cost class. No code was written for this task; the estimate of effort is from the read, and the cross-plane plumbing is deliberately excluded from it.
