# UX-1076: the Plane 2 report holds each element's opened paths as separate strings

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the snapshot and view performance audit on `39d89d4` (2026-09-28) | **Serves:** R5 | **Topic:** capture | **Area:** tools | **Shape:** mechanical

## Motivation

`parse_open_lines` (`tools/bst_native_build_tracer.py:2672`) keeps a
per-element `set` of path strings, one fresh `str` per line, though
the same sysroot headers repeat across every element. The report runs
right after the build, on the uncompressed log. 192,320 processes,
417 MB, [the audit](../../audits/perf-snapshot-view-2026-09-28.md):

```text
load_and_summarize  20.9s  peakRSS=714MB  (400,160 processes: 32.0s, 763MB from .gz - see UX-1079)
parse_open_lines     7.4s  RSS 552MB  3,710,972 set entries
  with sys.intern    5.5s  RSS 261MB  same entries
```

## Decomposition

Input classes: opens shared across elements, unique per element, `dropped` blocks, relative and dirfd opens. Journey: the capture's Plane 2 report.

## Required Fix

In `tools/bst_native_build_tracer.py`: Intern each path (or map it to an integer id shared across elements)
in `parse_open_lines`; the report is byte-identical.

## Out of Scope

Folding the two passes over the log into one (a judgement call on the second pass's memory, `UX-168`).

## Acceptance Test

`tests/unit/test_the_open_paths_are_interned.py`: On a scaled log (the audit's `genlog.py`, 1,202 x 160 x 50), the
opens pass peaks under 60% of today's RSS and the report is identical.
Mutation: drop the interning, and the bound reds.

## Outcome

Gap: `parse_open_lines` added each opened path as the fresh `str` the
file iterator handed it - a fixture at the audit's own scale (1,202 x
160 x 50, subprocess-measured on this machine) peaked at 559,916 KB
uninterned.

Close: `sys.intern(line)` at the one `.add()` call
(`tools/bst_native_build_tracer.py:2714`).
`python3 -m pytest tests/unit/test_the_open_paths_are_interned.py -q`:
`1 passed in 18.04s` - interned peak 261,260 KB, uninterned 560,168 KB,
ratio 0.466 (well under the 0.6 bound), report byte-identical
(3,710,425 entries, same 1,202 elements either way).

Mutation table:

| mutation | reddened | count |
|---|---|---|
| drop `sys.intern(...)`, `.add(line)` | `test_the_opens_pass_peaks_under_60_percent_of_the_uninterned_rss` | 1 failed (560,504 KB interned vs 559,916 KB uninterned, no longer under 60%) |
