# UX-107: two record streams, one process list

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-106 (the spine records), UX-105 (the census)

Direction 4, integration — see
[`design/directions.md`](../../design/directions.md).

## Motivation

Once `UX-106` lands, a dynamically-linked process is recorded **twice**
— a spine record (argv, timestamps, exit, per-process CPU, peak RSS)
and a hook record (the same lifecycle plus opens and children-rusage) —
while a static process has only the spine record. Consumed naively that
double-counts every dynamic process's CPU and concurrency, which would
corrupt every Plane 2 analysis in the name of fixing coverage. And the
report's coverage language is still the pre-spine disclaimer: a global
footnote, not a number.

## Required Fix

1. **Join and dedupe in the trace parser**: match spine and hook
   records per process on (invocation id, pid, START timestamp within
   a small tolerance — same sandbox pidns, same monotonic clock, so
   the join is exact in practice). One process, one merged entry:
   spine fields as the base, hook fields (opens, cutime/cstime) as
   enrichment. A hook record with no spine partner (spine off, or
   pre-spine captures) passes through as today — **old captures parse
   unchanged**.
2. **Provenance per process**: each merged entry carries
   `coverage: spine+hook | spine-only | hook-only`. Every analysis
   keeps working over the union; opens-dependent findings (UX-46
   declared-vs-used) compute over hook-covered processes only and say
   what share that is.
3. **Coverage becomes measured**: the report's per-element
   "(N% of this element's processes were measured)" and the global
   NOTE are recomputed from the union — with the spine on, process
   coverage is 100% by construction and the line says what remains
   partial (opens). The `UX-105` census cross-checks it: a static
   binary in the census with no spine records and no hook records is
   a *finding* (the tracer missed something), not a footnote.
4. **CPU reconciliation**: spine `utime/stime` is per-process; the
   hook's END additionally carries `cutime/cstime` (children it
   reaped). The merged model uses per-process self time only for
   sums — the double-count risk this task exists to prevent — and
   keeps the reaped-children figures as consistency evidence (the
   UX-53 pattern: a quantity computed twice is a free test; disagree
   beyond tolerance → flag the capture).

## Out of Scope

- The tracer itself (`UX-106`).
- Real-scale validation and defaults (`UX-108`).
- Chrome-trace export changes beyond passing merged entries through.

## Acceptance Test

On a dual-stream capture of `examples/06` (all-dynamic): every process
is `spine+hook`, total CPU equals the hook-only capture's total within
tolerance (nothing double-counted), and UX-46 output is unchanged. On
`examples/01` (static busybox): processes appear as `spine-only`,
per-element coverage reads 100% process / 0% opens, and declared-vs-
used correctly reports itself unmeasurable for those elements rather
than reporting "no unused dependencies". A pre-spine capture (the
retained fdsdk `native-report.json`) re-parses byte-identically.
