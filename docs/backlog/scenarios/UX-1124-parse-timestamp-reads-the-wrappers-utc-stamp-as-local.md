# UX-1124: `parse_timestamp` reads the wrapper's UTC stamp as local time

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** UX-1117's architect (round 151, 2026-09-29) | **Serves:** anyone reading a wrapped capture outside UTC | **Topic:** capture | **Area:** tools | **Shape:** mechanical | **Reading:** container

**Guard:** none — named test_the_wrapper_stamp_is_read_as_utc.py, absent from tests/

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

## Out of Scope

Changing the stamp the wrapper writes.

## Acceptance Test

`tests/unit/test_the_wrapper_stamp_is_read_as_utc.py`: under
`TZ=Europe/Berlin`, `02:59:00,000` to `03:00:00,000` on 2026-10-25
measures 60,000,000 us. Mutation: revert to the naive read; the test
reddens.

## Outcome

_Not yet done._
