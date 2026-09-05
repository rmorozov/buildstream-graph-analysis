# `host_cpu` — a run with a real CPU series, committed

One `bga snapshot` of
[`examples/06-macro-micro-optimization`](../../../examples/06-macro-micro-optimization),
taken 2026-09-05 with both planes and the ptrace spine on, kept here
because **no other committed fixture has a host CPU series at all**.

`UX-675` taught the sampler to read `/proc/stat`; `macro_micro` was
captured before that item and `golden` before `UX-378`, so both publish
`utilization_envelope.available: false` and neither can exercise a
single arithmetic step of `UX-676`. A fixture that cannot reach the code
it is named for is `UX-213`'s defect, and this is the fix.

## What was kept, and what was dropped

`run/` is verbatim: the three documents the loader reads. `sources.json`
was dropped for the reason `macro_micro` drops it - nothing in this
fixture's guards opens it. `host-samples.jsonl` is verbatim beside
`run/`, which is where `capture-layout/v1` puts it and where
`_compute_utilization_envelope` looks.

`plane2.json`, `plane2.log.gz`, `analyze.json` and `build.log` are not
here: the envelope is computed from Plane 1 and the host series, and
`plane2.log.gz` alone is 100 KB. `macro_micro` is the two-plane fixture;
this one is the CPU-series fixture, and keeping each to its own claim is
why neither is 200 KB.

## Measured

The readings the guards assert against, from the capture itself:

```text
cores                4          builders 4 x max-jobs 4 = 16 configured
capacity_cores       4          the smaller: a 4-core host cannot give 16
busy_cores p50/p95   1.884 / 3.255
underutilized_share  0.917      11 of 13 windows
overcommitted        0          load never above 4, nothing swapped
verdict              not_binding
```

The first sample of any capture carries no `cpu_busy_cores` - a rate
needs a gap, and the gap from the header's own read is under one jiffy
(`UX-675`). 14 lines in the file, 13 readings, 12 intervals.

The top under-utilized row is `core.bst` at `max_jobs 1` with 1.069
cores busy: the element is `notparallel` in the example's own
`elements/core.bst`, so three cores sit idle while it builds. That is
the case `UX-676`'s Acceptance Test names, and it is here because the
build really does it, not because the fixture was arranged for it.
