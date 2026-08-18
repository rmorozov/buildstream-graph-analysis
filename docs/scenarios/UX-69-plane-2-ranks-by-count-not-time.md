# UX-69: Plane 2 ranks binaries by invocation count, so the thing actually burning the CPU is invisible

**Priority:** High | **Status:** 🔴 Open | **Depends on:** `UX-45` (CPU time), `UX-64` (real per-element attribution)

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

## Verification Log

Filed 2026-08-17. Every figure is computed from the `processes` array of
`native-report.json` in the capture published to `captures/fdsdk-latest`
as `5eda28a` (run `32064333551`), filtered to
`components/_private/cmake-stage1.bst`.
