# UX-1078: a snapshot does not record what bga itself cost the build

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-1077 | **Found by:** the snapshot and view performance audit on `39d89d4` (2026-09-28) | **Serves:** R5, R8 | **Topic:** capture | **Area:** tools | **Shape:** judgement

## Motivation

The capture budget is 15-25% of time and resources (2026-09-20),
and `UX-895` measured the capture's overhead during the build
(+9.3% wall, all arms on). Nothing measures the tail after it, which
every one of several hundred review builds a day pays, and which grows
with the graph rather than with the work: an incremental build of a
5,002-element project that rebuilds nothing still pays one analysis
and a compare over the whole graph (about 104 s here, [the audit](../../audits/perf-snapshot-view-2026-09-28.md); inferred
for the cached case, not captured).

## Decomposition

Input classes: a complete tail, an interrupted one, a `--no-compare` snapshot. Journeys: `bga snapshot --list` and the store aggregate.

## Required Fix

In `tools/bga_snapshot.py`: The snapshot writes `tail.json`: wall and peak RSS per post-build
phase and the build's own wall. `bga snapshot --list` and the page
show bga's share beside the build; the store aggregate carries it, so
an agent pool's owner can read it across builds. `tail.json` is a
capture-directory document, so its schema lands in `bga/schemas.py`.

## Out of Scope

A budget that fails a build.

## Acceptance Test

`tests/unit/test_the_snapshot_records_its_tail.py`: A snapshot of the golden store writes `tail.json` with one row per
phase that `UX-1077` announces, and `--list --format json` carries the
total. Mutation: drop a phase from the file, and the guard reds.
