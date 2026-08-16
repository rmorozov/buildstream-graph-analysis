# UX-32: Plane 2 reports a global process count and one inflated global concurrency number, not per-element achieved parallelism

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-11, UX-23 (both done - the data this needs is already captured and already element-tagged)

## Motivation

Plane 2 exists to answer one question, quoted from `docs/architecture.md`: *"inside this one element's own sandbox, is its native build system actually achieving the parallelism it should, or silently serializing?"* Its report does not answer it. Real run, `examples/06-macro-micro-optimization`, `bst --builders 4 --max-jobs 4 build all.bst` on a 4-core host:

```
Processes traced: 822 (663 matched, 159 no observed exit)
Max observed concurrency: 20 (matched processes only - see open_records_note)
Wall span: 39.060s
By binary:
  cmake  248 | sh 150 | make 99 | c++ 88 | ld 55 | cc1plus 51 | as 51 | ...
By element:
  core.bst 113 | codegen.bst 93 | lib-a.bst 88 | lib-b.bst 88 | ... | app.bst 88
```

Everything here is a count or a global. `core.bst` did more work than its siblings; the report says nothing about whether it did that work in parallel. In this project `core.bst` is pinned to `make -j1` by a one-line `notparallel: True` and takes 13.05s where it should take ~4s - that is the entire micro-level finding and it is not in the output.

It is, however, fully derivable from `processes[]`, which the tool already writes to its own JSON. Computed by an ad-hoc script over that file:

```
                baseline                             optimized/
  element     n  peak  span      compile_cpu     peak  span
  core.bst   10    1   13.05s      11.05s          4    6.03s
  codegen.bst 6    4    2.55s       7.42s          4    4.19s
  lib-a.bst   5    3    1.88s       4.12s          3    6.67s
  lib-b.bst   5    3    1.94s       4.13s          3    6.36s
  ... (lib-c..lib-f, app all peak=3)
```

(`peak` = maximum concurrently-live `cc1plus` processes owned by that element, from the element tags `UX-23` already attaches.) One element at peak 1 while every sibling reaches 3-4 is the finding, in one column, from data already on disk.

The global `Max observed concurrency: 20` is separately misleading. It counts every traced process, and most long-lived processes in a `make` tree are *waiting*: `core.bst` alone shows 99.65s of total process-lifetime inside a 14.91s span (an apparent 6.68 average concurrency) while its actual compiler concurrency never exceeded 1. On a 4-core host the headline says 20, and later 44 for the same project's optimized variant - numbers that invite the reader to conclude something about the host that is not true.

## Required Fix

Add a per-element parallelism section to `tools/bst_native_build_tracer.py`'s report. Concretely:

1. Per element, from the already-captured `start_ts`/`end_ts`/`element` fields: peak concurrency, mean concurrency (time-weighted), span, and total process-lifetime.
2. Distinguish **work processes** from **orchestration processes**. `sh`, `make`, `cmake`, and `env` wrappers spend their lives waiting on children; compilers/assemblers/linkers (`cc1`, `cc1plus`, `as`, `ld`, `collect2`, `ar`, `ranlib`) are the real work. A concurrency number over all processes is not interpretable; over work processes it is. The split must be visible and overridable, not a hidden hardcoded list - an unrecognized binary should be reported as unclassified rather than silently bucketed.
3. Where the element's own `-jN` is recoverable from the trace (it literally is - `/usr/bin/make -f Makefile -j1` appears verbatim in `processes[].cmd`), report **achieved vs. requested**: `peak_work_concurrency` against the `-jN` the element actually asked for. An element that requested `-j4` and achieved a peak of 1 is a finding regardless of why.
4. Replace or qualify the global `Max observed concurrency` line so it cannot be read as host load - either restrict it to work processes, or label it explicitly as "all traced processes including idle wrappers".

## Out of Scope

- Feeding any of this back into Plane 1's `Σattribution == H` accounting. `docs/architecture.md` is explicit that the two planes deliberately have separate horizons, and this task does not change that.
- CPU *time* per process. `LD_PRELOAD` start/end timestamps give lifetime, not CPU, and inferring one from the other under contention is exactly the error `UX-37` is about. If real CPU time is wanted that is a separate capture change (`getrusage` in the hook's destructor) and should be filed on its own.
- The static-binary coverage gap (`UX-11`'s standing disclaimer), which applies unchanged to any number computed here and must keep being printed.

## Acceptance Test

1. Against a real trace of `examples/06-macro-micro-optimization`, the report names `core.bst` as achieving peak work-concurrency 1 against a requested `-j4`, and does not flag any sibling.
2. Against the `optimized/` variant, `core.bst` reports peak 4 and is not flagged.
3. The global concurrency line no longer reports a number larger than the host core count without saying what it is counting.
4. Unclassified binaries are reported as such rather than silently counted or silently dropped. Full suite green.

## Verification Log

Filed 2026-08-16 from a real session (`docs/optimization-walkthrough-06.md`). Both traces are real `tools/bst_native_build_tracer.py run` captures of real `bst --builders 4 --max-jobs 4 build all.bst` invocations (BuildStream 2.7.0, real `bwrap` sandbox, real `gcc 13`/`cmake 3.28`, 4-core host); the per-element table was computed from those runs' own emitted `processes[]` arrays, which is the point - no new capture was needed to produce it.
