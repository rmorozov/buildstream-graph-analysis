# UX-1073: compare reads each side's published analysis instead of analyzing both runs again

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the snapshot and view performance audit on `39d89d4` (2026-09-28) | **Serves:** R5, R1 | **Topic:** analysis | **Area:** bga | **Shape:** judgement

## Motivation

`compare_runs` (`bga/compare.py:1320`) calls `analyze` on both runs
every time, though each snapshot published its `analyze.json` at
capture (`UX-296`). Two callers pay it on the hot path. 5,002 elements,
[the audit](../../audits/perf-snapshot-view-2026-09-28.md):

```text
snapshot tail  _compare         49.27s  peakRSS=2010MB  (2 analyze calls: 80.0 of 81.6s profiled)
bga view --export               54.93s  peakRSS=2038MB  (compare: 80.4 of 89.1s profiled)
```

At 1,202 elements: 3.44 s and 3.74 s. The view prints nothing until
it is done.

## Decomposition

Input classes: both sides published and current, one stale, neither published, a cross-mode pair (`UX-78`'s refusal). Journeys: the snapshot tail's compare and `bga view`.

## Required Fix

In `bga/compare.py` and `tools/bga_view.py`: `compare_runs` accepts a published analysis per side and uses it
only when its fingerprint equals the one this compare would analyze
under, falling back to analyzing otherwise. The fingerprint covers
every result-affecting input and option: the analyzer version, the
digest of each run-directory input, the digest of the Plane 2 report
actually passed (`--baseline-plane2`/`--candidate-plane2`), and the
normalized value of each option that changes the result (`--capacity`,
cold/history settings, and any other option the analyzer reads). Any
option not yet classified makes the analysis non-reusable rather than
reusable. `bga view --reanalyse` bypasses published analyses for the
comparison as well as for the page. The snapshot tail passes the
candidate's in-memory result with its fingerprint; `bga view` passes
both files. The analysis document's schema in `bga/schemas.py`
carries the fingerprint. The compare output is byte-identical either
way.

## Out of Scope

Making the analyzer itself faster (`UX-1074`).

## Acceptance Test

`tests/unit/test_compare_reads_published_analyses.py`: On the golden store: compare output from published analyses equals
the re-analyzed output byte for byte, and the number of `analyze`
calls is 0 with both published, 2 with neither. Each of these falls
back and analyzes: a bumped analyzer version, a changed `--capacity`, a
different Plane 2 report passed for one side, and `bga view
--reanalyse`. Mutation: ignore the published file, and the call count
reds; drop any one fingerprint term, and its case reds.
