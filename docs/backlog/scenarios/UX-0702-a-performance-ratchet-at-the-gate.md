# UX-702: a performance ratchet at the gate

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-531 (the superlinear analyzer), UX-418 (the reference method) | **Serves:** R8 reading whether a round made `bga analyze` slower on the largest capture, which nothing today records | **Topic:** guards

## Motivation

`UX-531` measured `bga analyze` superlinear in elements; the page pays
for it. No guard reads the analyzer's wall time or memory, so the
number can move a round at a time unnoticed — the `UX-418` lesson, that
a slow file is small until CI times out, applies to the tool itself.
Every timing rule in this repository holds: nothing across machines,
consecutive runs must agree, the reference is CI's own.

## Required Fix

One CI step on the 3.11 runner: `bga analyze` and `bga view --export`
on the largest fixture, wall and peak RSS (`/usr/bin/time -v`),
recorded into `tests/ci_reference.json` beside the tier rows under the
same adoption path; a run reports when two consecutive runs exceed the
reference by an absolute margin (seconds and MB, not a ratio — `UX-420`)
and the diff touches the analyzer. Never in `make test`.

## Out of Scope

- A local benchmark — no reading taken here compares with CI's.
- Profiling or the fix for the superlinearity — `UX-531`'s.

## Acceptance Test

The reference carries `analyze_wall_s` and `analyze_rss_mb` for the
fixture; mutation: an `O(n²)` loop over elements added to
`bga/analyzer.py` on a branch — the step reports on the second run
and names the diff's file.
