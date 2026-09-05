# UX-675: the host series has memory and no cores

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-378 (host-samples.jsonl), UX-437 (the host tracks on the trace) | **Serves:** R4, asking whether the cores were busy | **Topic:** capture

## Motivation

The one series the capture keeps about the host is memory:

```text
tools/bst_native_build_tracer.py:678-690   _MEMINFO_KEYS, _VMSTAT_KEYS (pgmajfault, pswpin, pswpout) — no CPU field
tools/bga_timeline.py:502-503              CONCURRENCY_COUNTER = "traced processes running", unit "processes"
bga/viewer/questions.js:518-536            concurrency-curve: the reader is told to compare it "against the machine's core count" themselves
```

Processes running is not cores busy — a process blocked on I/O or a
lock holds a slot and no core — so the CI owner's question ("were
the cores the binding resource?") has no series to be answered from.
Plane 2's rusage gives CPU *totals* per process at exit
(`hook.c:353-397`), which cannot be placed in time.

## Required Fix

The host sampler reads `/proc/stat` beside `/proc/meminfo` on the
same tick: busy cores (delta of non-idle jiffies over the interval,
divided by the tick), load average, and the core count. Three more
counter tracks on the trace beside the five memory tracks (`UX-437`'s
shape), `bga:*` units declared, and the trace dictionary row. The
sample is what `UX-676` reads.

## Out of Scope

- Per-process CPU over time — rusage is at exit by design; the host
  series is the cheap instrument, and it is the one the question
  needs.

## Acceptance Test

A capture's `host-samples.jsonl` carries `cpu_busy_cores`, `load1`
and `cores` per tick; the trace has the three tracks; mutation: drop
the `/proc/stat` read — the sampler guard reds.
