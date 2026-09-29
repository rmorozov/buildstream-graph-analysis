# UX-1124: `parse_timestamp` reads the wrapper's UTC stamp as local time

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** UX-1117's architect (round 151, 2026-09-29) | **Serves:** anyone reading a wrapped capture outside UTC | **Topic:** capture | **Area:** tools | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_the_wrapper_stamp_is_read_as_utc.py`

## Motivation

`tools/bst_run_wrapped.py:49` writes `datetime.now(timezone.utc)`;
`tools/bst_log_to_chrome_trace.py:292-298` (`parse_timestamp`) parses it
with a naive `strptime(...).timestamp()`, which reads it as local time.
Under `TZ=Europe/Berlin`, `02:59` to `03:00` on 2026-10-25 (the DST end)
measures **3,660,000,000 us instead of 60,000,000**; outside UTC every
absolute time is off by the TZ offset.

## Decomposition

Input classes: wrapper stamps under UTC, a positive-offset zone, a DST transition; raw-mode stamps with no wrapper line.
Journey: Plane 1 ingest in `bga analyze`, spans placed against Plane 2.

## Required Fix

`parse_timestamp` in `tools/bst_log_to_chrome_trace.py` reads the stamp as
UTC (`.replace(tzinfo=timezone.utc)`) in wrapped mode; raw mode keeps its
documented reading.

## Decision

Route: `strptime(...).replace(tzinfo=timezone.utc)` in parse_timestamp, applied unconditionally; raw mode never calls it. Rejected: a wrapped/raw branch inside parse_timestamp (raw mode never calls it). Files: tools/bst_log_to_chrome_trace.py, tests/unit/test_the_wrapper_stamp_is_read_as_utc.py; retire the autouse `_utc` fixture in tests/unit/test_the_log_reader_holds_its_properties.py. Guard/Mutation: as the Acceptance Test. Class: product.

## Out of Scope

Changing the stamp the wrapper writes.

## Acceptance Test

`tests/unit/test_the_wrapper_stamp_is_read_as_utc.py`: under
`TZ=Europe/Berlin`, `02:59:00,000` to `03:00:00,000` on 2026-10-25
measures 60,000,000 us. Mutation: revert to the naive read; the test
reddens.

## Outcome

**Gap measured.** Naive read, `TZ=Europe/Berlin`, `02:59:00,000` to `03:00:00,000` on 2026-10-25: not 60,000,000 us (the guard, mutated, reddens both tests).

**Readers of the stamp.** `parse_timestamp` has two callers, both on wrapper stamps: `_process_wrapped_line` (`bst_log_to_chrome_trace.py`) and `bst_native_build_tracer.py:5420` (matches `PREFIX_RE`). Raw mode never calls it (`process_line_raw`). No other naive read under `bga/` or `tools/`; `gen_synthetic_scale_run._stamp` writes UTC.

**Close measured.** `parse_timestamp` reads `.replace(tzinfo=timezone.utc)`. Guard: 2 passed. Under `TZ=UTC` the aware and naive reads are identical, and `tests/fixtures` is unmodified after the converter, plane-1 and analysis tests. `TZ=Europe/Berlin` converter, timestamp-resolution and start-clock tests: 54 passed.

| Mutation | Reddened | Count |
|---|---|---|
| drop `.replace(tzinfo=timezone.utc)` | both guard tests | 2 failed |
| revert | both | 2 passed |

**Fixture retired.** `_utc` (autouse TZ=UTC) removed from `test_the_log_reader_holds_its_properties.py`; that file computes no epoch expectations, so nothing needed timezone.utc.

**Re-run.** `python3 -m pytest -n 2` over the touching selection plus the converter tests (48 files): 2073 passed, 4 skipped, 0 red.
