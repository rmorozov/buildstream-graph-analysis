# UX-297: extraction streams, and the monolith retires

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** Direction 15, UX-298 (the trace it writes beside), UX-215 (the aggregate pattern) | **Serves:** R1, R2 | **Topic:** capture

## Motivation

Measured this round: **~95 % of the 1.5 GB monolith is dead weight
at read time.** `summarize()` embeds the entire per-process record
list into plane2.json (`tools/bst_native_build_tracer.py:3648`,
`"processes": records` — ~550 B/record, ~2.7 M records at field
size) and **no production reader consumes it**: every consumer
(`correlate`, analyze, the aggregate walk) reads only the small
per-element aggregates sitting beside it in the same file. The
capture path holds the full record list in RAM to write it (the
tracer's own measurement: 479 MB per 400 k processes), and
`bga snapshot`'s auto-compare then `json.load`s **both** runs'
monoliths with the two parses coexisting (`bga/cli.py:371-388`,
measured 1.7× a single parse — ~7-8 GB projected, on the machine
that just finished the build).

Direction 15's rules 2 and 5: events are a stream, and analysis
reads aggregates. Everything the published numbers need from
Plane 2 is a per-element reduction — the census, the join's
achieved parallelism, CPU coverage, peak RSS, dominant binary —
and reductions stream: none of them needs the event list in
memory, only running totals per element.

## Required Fix

Extraction processes the raw log as the line stream it already is,
folding events into per-element aggregates as it goes and (with
`UX-298`) appending trace packets as it goes; peak extraction RSS
becomes O(elements), not O(events). The per-element aggregates land
in a small schema-stamped JSON (the `element_join` inputs, the
census — what `correlate` actually consumes); the `"processes"`
record list is **no longer embedded** — records live in the raw log
they came from and the trace artifact `UX-298` derives, so
plane2.json collapses to the ~5 % that is actually read. The
auto-compare parses sequentially and releases (never two monoliths
coexisting). Reading stays one interface:
a legacy run's monolith is still consumed (streamed with a
line-oriented fallback or read once with a size warning), so old
stores do not die; which path served the data is stated in the
payload's provenance.

## Out of Scope

- The trace artifact's format (`UX-298`).
- Any change to what the published numbers mean — every aggregate
  must reproduce the monolith path's values exactly on the same
  input (that equality is the migration's guard).

## Acceptance Test

On the generated big-run input: extraction completes under an
argued RSS ceiling (the record list alone measured 479 MB per 400 k processes at capture today); the aggregates
byte-match the legacy path's numbers on the same small fixtures
(golden equality); no `plane2.json` is written for a new capture;
a legacy run still analyzes with identical output; mutation:
buffering the whole event list again reddens the RSS guard.
