# UX-1075: the raw Plane 2 log is compressed at gzip level 9, 5x slower than level 6 for 3% size

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the snapshot and view performance audit on `39d89d4` (2026-09-28) | **Serves:** R5 | **Topic:** capture | **Area:** tools | **Shape:** mechanical

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

`tests/unit/test_the_raw_log_compression_level.py`: a guard reads the compressed file's header flags (XFL=0, not 2)
after `_compress_raw_log`. Mutation: drop the level, and it reds.
