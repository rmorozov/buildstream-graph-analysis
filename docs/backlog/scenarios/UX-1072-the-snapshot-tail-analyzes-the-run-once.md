# UX-1072: the snapshot tail analyzes the run once, not twice

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the snapshot and view performance audit on `39d89d4` (2026-09-28) | **Serves:** R5, R1 | **Topic:** capture | **Area:** tools | **Shape:** mechanical

**Guard:** test_the_snapshot_tail_analyzes_once.py

## Motivation

After the build, `_analyze` (`tools/bga_snapshot.py:815`) runs
`BuildEfficiencyAnalyzer` over `run/`, then `write_element_slice`
(`:889`) runs it again with `section='graph'` on the same directory.
Measured with [the audit](../../audits/perf-snapshot-view-2026-09-28.md)'s `step.py`, 5,002 elements (`gen-synthetic
--layers 40 --width 125 --seed 1 --store`):

```text
analyze  35.58s  peakRSS=1967MB
slice    18.62s  peakRSS=1965MB   # a second pass over the same run
```

At 1,202 elements: 1.85 s and 0.75 s.

## Decomposition

Input classes: a published analysis and a failed publish (the plain CLI fallback); 74, 1,202 and 5,002 elements. Journey: `bga snapshot`'s tail.

## Required Fix

In `tools/bga_snapshot.py`: `write_element_slice` takes the analysis `_analyze` already holds
(the `cli.analyzed` result) instead of re-running the analyzer;
the slice's bytes stay identical.

## Out of Scope

The analyzer's own cost (`UX-1074`).

## Acceptance Test

`tests/unit/test_the_snapshot_tail_analyzes_once.py`: a guard counts `BuildEfficiencyAnalyzer.analyze` calls across
`_analyze` + `write_element_slice` on the golden run: exactly 1, and
`element-slice.json` is byte-identical to today's. Mutation: restore
the second `analyze(..., section='graph')`, and the count reds.

## Outcome

**Gap measured:** the audit's `step.py`, `gen-synthetic --layers 40
--width 125 --seed 1 --store`, 5,002 elements: `analyze` 35.58 s
(peakRSS 1967 MB), `slice` 18.62 s (peakRSS 1965 MB) - a second pass
over the same `run/`. At 1,202 elements: 1.85 s / 0.75 s.

**Close measured:** `_analyze` (`tools/bga_snapshot.py:819`) now returns
`(exit_code, result)`; `write_element_slice` (`:900`) takes that
`result` as `analysis_result` and only re-runs
`BuildEfficiencyAnalyzer().analyze` when it is `None`. `python3 -m
pytest tests/unit/test_the_snapshot_tail_analyzes_once.py -q` →
`2 passed in 0.36s`. `make test-touching` → `65 file(s) selected ...
2200 passed, 30 skipped in 108.93s`.

**Mutation table:**

| mutation | reddened | count |
|---|---|---|
| restored the unconditional `BuildEfficiencyAnalyzer().analyze(..., section='graph')` in `write_element_slice`, ignoring `analysis_result` | `test_the_tail_analyzes_the_run_once` | 1 failed, 1 passed |
