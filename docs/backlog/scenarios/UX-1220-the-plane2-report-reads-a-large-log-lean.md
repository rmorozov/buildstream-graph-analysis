# UX-1220: the Plane 2 report holds a large log's opened paths as strings in sets and parses every record twice over

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** Ruslan's report from his own project (2026-10-01): a 650 MB `plane2.log.gz` holds `Analyzing the captured trace...` for about 10 minutes at about 4 GB | **Serves:** R5 | **Topic:** capture | **Area:** tools | **Shape:** bounded

**Guard:** test_the_opens_pass_holds_paths_as_ids.py

## Motivation

`load_and_summarize` (`tools/bst_native_build_tracer.py`) runs right
after the build on the uncompressed log. A field log of 650 MB gzipped
is several GB raw. Reproduced on a 1,202-element store
(`bga gen-synthetic --store --seed 1 --layers 20 --width 60`) scaled
with the audit's `genlog.py`: 400 processes per element, 60 paths each,
40 from a sysroot slice shared across elements and 20 element-local.
1.26 GB raw, 96 MB at gzip -6, 480,800 processes, 30.2M lines.

```text
stage (before)                     wall    RSS after
record pass (parse+pair)           ~26s    604 MB
opens pass  (parse_open_lines)      55s   +1,245 MB   21.4M set entries (genlog.py as published)
```

Three costs: every opened path is a regex match plus a `set` entry of
~50 bytes; a START/END line is re-sliced once per field; and with the
spine on, `merge_record_streams` copies every record (`dict(record)`)
while the input list is still alive.

## Decomposition

Input classes: opens blocks whole, cut short by START/END or a header,
malformed headers, blank and CRLF lines, orphan paths, `inv=` relabelled
at finish; record lines canonical and not (unknown key, bad value, no
`cmd=`); a hook-only and a dual-stream capture.

## Required Fix

In `tools/bst_native_build_tracer.py`: an element's opened paths are a
sorted `array('I')` of ids into one table of distinct paths
(`OpenedPaths`, `OpensReader`); a block's lines are taken whole and
checked in C, the per-line walk kept for an irregular block; a
canonical record line parses in one split, any other falls to the
general parser; `merge_record_streams(consume=True)` joins in place.
The report is byte-identical.

## Out of Scope

The record list itself (`UX-313`'s floor); parsing while the build
runs; parallel parsing; the raw log's gzip; the hook writing fewer
repeated paths.

## Acceptance Test

`tests/unit/test_the_opens_pass_holds_paths_as_ids.py`: 3,000 fuzzed
logs parse as UX-1076's set-of-strings reader does, with and without
relabels; 20,000 fuzzed record lines the fast parse accepts parse as
the general one does; a consuming merge returns the input's own dicts
with an equal answer; the opens pass peaks under 60% of the reference
at 1,202 x 40 x 50.

## Outcome (2026-10-01) — 🟢 Done

**Premise:** held — the opens pass was 55 s and +1,245 MB of a 1.28 GB
log, and a spine capture copied its whole record list in the merge.

### The gap, measured

`python3 las.py <log> <tree>` (`load_and_summarize`, wall and `VmHWM`,
sha256 of the sorted-key report), the generator in the Motivation,
4-core container, Python 3.11:

```text
hook-only  real.log   1.26 GB  480,800 proc  before  66.2s  1,092 MB  report 645bd5f4c6f65441
dual       spine.log  1.45 GB  961,600 rec   before  87.5s  1,471 MB  report 35e01b70adcb9e2c
```

`spine.log` is `real.log` with every hook START/END repeated as
`src=spine`, so every process joins in `merge_record_streams`.

### After

```text
hook-only  real.log   after  48.4s    699 MB  report 645bd5f4c6f65441
dual       spine.log  after  66.8s  1,148 MB  report 35e01b70adcb9e2c
```

Wall -27% and -24%, peak -36% and -22%, both reports byte-identical.
The opens pass on the guard's 1,202 x 40 x 50 log: 78,092 against
208,640 KB, 1.18 against 2.21 s. What remains is the record list
(`UX-313`): 952 bytes a record, measured with `tracemalloc` on 47,736.

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| A1 | fast block check drops the non-path-line test | the fuzz agreement, 1 failed |
| A2 | fast record parse skips an unknown key instead of deferring | the fast-parse agreement, 1 failed |
| A3 | `consume=True` still copies | the in-place merge, 1 failed |
| A4 | an element's paths stored as a `set` of strings | the id-array clause and the 60% bound, 2 failed |
| A5 | a cut-short block's tail is not read again | the fuzz agreement, 1 failed |

### Deviation from the Required Fix

The opens first rode the record pass, one read of the log: 68.9 s and
1,344 MB on `spine.log`, against 67.4 s and 1,149 MB as a second pass,
so it stays a second pass. `test_the_open_paths_are_interned.py` keeps
UX-1076's bound against the set-of-strings reference uninterned, since
`sys.intern` is no longer the mechanism.
