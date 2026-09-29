# UX-1075: the raw Plane 2 log is compressed at gzip level 9, 5x slower than level 6 for 3% size

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the snapshot and view performance audit on `39d89d4` (2026-09-28) | **Serves:** R5 | **Topic:** capture | **Area:** tools | **Shape:** mechanical

**Guard:** test_the_raw_log_compression_level.py

## Motivation

`_compress_raw_log` (`tools/bga_snapshot.py:367`) calls `gzip.open`
with its default, level 9, after every build. On a 417 MB raw log
(192,320 processes, 9.6 M open paths, [the audit](../../audits/perf-snapshot-view-2026-09-28.md)):

```text
gzip level 9  16.0s  30 MB
gzip level 6   3.1s  31 MB
gzip level 1   1.5s  42 MB
copyfile       1.6s
```

The synthetic log is more repetitive than a real one: the speed ratio
is the claim, not the sizes.

## Decomposition

Input classes: a raw log present, absent, and one whose compression fails (kept uncompressed). Journey: `bga snapshot`'s tail.

## Required Fix

In `tools/bga_snapshot.py`: Compress at level 6 (`compresslevel=6`), stated as a named constant.

## Out of Scope

Another codec (zstd is in `requirements.lock` since `UX-927`; a separate call).

## Acceptance Test

`tests/unit/test_the_raw_log_compression_level.py`: a spy on `gzip.open` asserts `_compress_raw_log` passes
`compresslevel=6` (the header's XFL byte does not tell 6 from other
middle levels), and a round-trip reads the compressed log back
byte-identical to the original. Mutation: drop the level or pass 9,
and the spy reds.

## Outcome

**Gap measured:** the audit's `step.py` on the 417 MB synthetic raw
log (192,320 processes, 9.6M open paths): level 9 (default) 16.0 s /
30 MB, level 6 3.1 s / 31 MB.

**Close measured:** `tools/bga_snapshot.py:367` now passes
`compresslevel=RAW_LOG_COMPRESSLEVEL` (= 6) to `gzip.open`.
`python3 -m pytest tests/unit/test_the_raw_log_compression_level.py -q`
→ `2 passed in 0.35s`.

**Mutation table:**

| mutation | reddened | count |
|---|---|---|
| `compresslevel=RAW_LOG_COMPRESSLEVEL` → `compresslevel=9` | `test_compress_raw_log_passes_level_six` | 1 failed, 1 passed |
