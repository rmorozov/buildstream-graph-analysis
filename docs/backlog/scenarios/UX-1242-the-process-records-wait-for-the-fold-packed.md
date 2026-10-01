# UX-1242: the Plane 2 report holds every process record as a dict until the fold, 1,232 bytes each

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-1240 | **Found by:** Ruslan's report from his own project (2026-10-01): `Analyzing the captured trace...` at about 4 GB; he asked for the records' compaction in the same batch on 2026-10-01 | **Serves:** R5 | **Topic:** capture | **Area:** tools | **Shape:** bounded

**Guard:** test_the_records_are_packed.py

## Motivation

`UX-313` showed the record list must exist whole: it is sorted by start
before the spine join and the fold. It did not ask what one record
costs. Measured with `tracemalloc` on the x20 real-build log from
`UX-1241` (abseil, fmt and xz under the hook, 197,680 processes):

```text
stage                         traced       per record
records, sorted and joined    232 MB       1,232 B
the fold after them            17 MB          90 B
```

The records are the peak: 385 MB `VmHWM`, against 90 bytes a process
once folded. A record is a 21-key dict of boxed numbers and an
uninterned command line.

## Decomposition

Input classes: a record's int, float, bool, None, string and other
values, an int past 64 bits, varying key sets; a hook-only capture, a
dual-stream capture with joined, spine-only and unclaimed hook records,
equal start stamps and equidistant hook candidates. No journey
extended: the report is byte-identical by construction.

## Required Fix

In `tools/bst_native_build_tracer.py`: `PackedRecords` holds each
record's numbers as one `struct` row in a shared buffer and its strings
as interned references, by a shape per key-and-type set;
`merge_record_streams`' pairing becomes `_merge_plan` over indices, so
the store joins without a dict per record, and `merged()` yields the
fold's dicts one at a time in the old order. `load_and_summarize`
folds from it.

## Out of Scope

The opens pass, now the peak on a log the hook did not dedupe; parsing
while the build runs; a smaller int width.

## Acceptance Test

`tests/unit/test_the_records_are_packed.py`: 5,000 fuzzed records round
trip with their types and key order; 1,500 fuzzed populations merge
through the list and the store as `UX-1240`'s merge did, held as a
reference; the spine fixture agrees; the report folds from the store;
20,000 records of the real shape pack under 40% of their dicts.

## Outcome (2026-10-01) — 🟢 Done

**Premise:** held — the records were 232 of 249 MB traced at the peak.

### The close, measured

`las.py` (`load_and_summarize`, wall, `VmHWM`, sha256 of the
sorted-key report), #307's tree before (`45a6b6f7`) and after, 4-core
container, Python 3.11:

```text
log                              before            after             report
x20 real, deduped   263 MB raw   9.6-10.2s 385 MB  10.4-11.2s 135-139 MB  ed307ed9a56fd198
x20 real, full      949 MB raw   18.9s     385 MB  19.8s      135 MB      ed307ed9a56fd198
synthetic + spine  1.45 GB raw   49.1s   1,148 MB  52.9s      698 MB      35e01b70adcb9e2c
```

Peak -65% and -39%, wall +5-9%, reports byte-identical. On the
synthetic log the peak is now the opens pass, whose paths that
generator does not repeat. The guard's 20,000 records: 7,099,442
against 21,464,292 B, each command distinct.

### Mutations verified red and reverted (8)

| # | mutation | reddened |
|---|---|---|
| B1 | a bool packed as an int | the round trip, 1 failed |
| B2 | no fallback for an int past 64 bits | 2 failed |
| B3 | `merged()` not sorted by start | the store's join, 1 failed |
| B4 | an equidistant hook goes to the later candidate | the reference merge, 1 failed |
| B5 | the report bypasses the store | the fold clause, 1 failed |
| B6 | a record's strings come back reversed | 3 failed |
| B7 | the store also keeps the dict | the 40% bound, 1 failed |
| B8 | the plan not re-sorted by start | the reference merge, 1 failed |

### Deviation from the Required Fix

B4 survived until the reference merge was added: the list and the store
share `_merge_plan`, so comparing them could not see it.
