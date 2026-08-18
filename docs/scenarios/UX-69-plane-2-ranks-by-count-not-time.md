# UX-69: Plane 2 ranks binaries by invocation count, so the thing actually burning the CPU is invisible

**Priority:** High | **Status:** 🟢 Done | **Depends on:** `UX-45` (CPU time), `UX-64` (real per-element attribution)

## Motivation

Raised by the user: *"regarding our micro level captures — brainstorm
whether we really show low hanging fruits there? maybe we need additional
frequency analysis for top longest captures — spotting things like
compilation of a file with heavy c++ templates."*

Tested against the real capture, on `cmake-stage1.bst` — the element the
tool correctly identifies as 43.5% of the critical path. 11,974
processes. Here is what the report ranks, against what a user needs:

| binary | count | CPU s | wall s |
|---|---|---|---|
| **ranked by count — what the report shows today** |
| `sh` | 2262 | 29.4 | 8745.1 |
| `as` | 1918 | 397.5 | 5929.8 |
| `ninja` | 1731 | 3.4 | 470.2 |
| `gcc` | 1322 | 0.8 | 9.9 |
| `cc1` | 1034 | 252.9 | 272.4 |
| **ranked by CPU time — what a user needs** |
| **`cc1plus`** | **885** | **4352.6** | **5525.6** |
| `as` | 1918 | 397.5 | 5929.8 |
| `cc1` | 1034 | 252.9 | 272.4 |
| `dwz` | **1** | **137.0** | **138.6** |
| `ld` | 345 | 64.8 | 96.0 |

**`cc1plus` does not appear in the top five by count, and dominates by
time — 4,352 CPU seconds, ten times the next binary.** That is precisely
the heavy-C++-template signal the user asked whether the tool surfaces.
It does not.

`dwz` is the second finding and a different shape: **one process, 137 CPU
seconds, 138.6s wall.** A single serial process holding 138 seconds
inside the build's heaviest element is a textbook serialization point,
and counting cannot see it at all.

## The data is already published

Every per-process record in `native-report.json` already carries `cmd`,
`cpu_us`, `duration_s`, `element` and `max_rss_kb` — 127,627 of them in
the real capture. The table above was computed from the published report
with no new instrumentation. This is a missing *analysis*, not a missing
measurement, which is the same shape as `UX-33` and `UX-65`.

## Required Fix

1. **Rank by time, per element.** For the elements Plane 1 says matter,
   report their binaries by CPU time and by wall time, alongside count.
2. **Keep count as a separate column, not the sort key.** 30,975 `sed`
   invocations build-wide is a real signal about build-system shape; it
   is just not the same question as "where did the time go".
3. **Name the single-process serialization case.** One process holding N
   seconds of wall time inside an element is qualitatively different
   from N processes holding it, and is directly actionable.
4. **Report the heavy compilation unit where possible.** `cc1plus` is
   invoked per translation unit and the `cmd` carries the file, so "the
   5 translation units that cost the most CPU" is available from the
   same records.

## Out of Scope

- New instrumentation. Everything needed is captured.
- Attributing time to *source* constructs (templates, headers). The tool
  can say which TU is expensive, not why; that is the compiler's own
  `-ftime-report` territory.

## Acceptance Test

1. On the real capture, `cmake-stage1.bst`'s report names `cc1plus` first
   and states its CPU share.
2. `dwz` is flagged as a single-process serialization point.
3. Count-based views still exist and are labelled as counts.
4. An element with no CPU-time coverage reports that, rather than
   ranking by count silently (the `UX-45` rule).

## Fix Implemented

`compute_binary_cost(records)` ranks each element's binaries by measured
CPU time, publishing count alongside rather than as the sort key, and
naming the single-process case separately. Rendered for the three
elements carrying the most measured CPU.

```
Where the time went inside each element (by CPU time, not count):
  components/_private/cmake-stage1.bst
    cc1plus           4352.6 CPU s (81.3%)     885 process(es), 5525.6s wall
    as                 397.5 CPU s ( 7.4%)    1918 process(es), 5929.8s wall
    cc1                252.9 CPU s ( 4.7%)    1034 process(es), 272.4s wall
    dwz                137.0 CPU s ( 2.6%)       1 process(es), 138.6s wall
    NOTE: dwz is a SINGLE process holding 138.6s of wall time - a
    serialization point that more parallelism cannot help
```

**`cc1plus` at 81.3%** is the heavy-C++-template answer, absent from the
count-ranked top five entirely.

It also found something nobody was looking for: in the unresolved
bucket, **`lto1` holds 48.8% of CPU across 412 processes** — link-time
optimization as a first-order cost, invisible by count.

`UX-45`'s rule is preserved: an element with no CPU coverage says so,
rather than silently falling back to counts while looking like a cost
ranking.

Tests: 7 (`tests/unit/test_binary_cost.py`).

## Verification Log

Filed and implemented 2026-08-17. Every figure is computed from the `processes` array of
`native-report.json` in the capture published to `captures/fdsdk-latest`
as `5eda28a` (run `32064333551`), filtered to
`components/_private/cmake-stage1.bst`.
