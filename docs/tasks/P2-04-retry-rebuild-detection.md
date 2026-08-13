# P2-04: Retry/rebuild detection unimplemented — utilization buckets always empty

**Priority:** P2 | **Status:** 🟢 Fixed & Verified (2026-08-13) | **Depends on:** none

## What was fixed
Added `bga/utilisation/detection.py`:
- `compute_retry_tasks(normalized_tasks)`: groups tasks by `(element_uid, task_kind, phase)`; every task in a group whose `attempt` isn't the group's max is a retry. Pure function, no I/O.
- `compute_rebuild_tasks(graph, normalized_tasks, historical_runs)`: a BUILD task is a rebuild if its element's current `cache_key` (graph/v9, Part 32.2) was already built successfully in some `historical_runs` entry - the exact signal `bga.floors.cold` (`P1-06`) already keys its historical duration lookups by, so no new ingest schema field was needed, confirming the task file's own suggestion to check for an existing representable signal before adding one.

Both return `Set[str]` of `str(task_key)` (the `element_uid|task_kind|phase|attempt` format), matching what `_build_cpu_intervals` already keys `task_intervals` by. Wired into `bga/analyzer.py::_compute_utilization`, replacing the hardcoded `retry_tasks=set()` / `rebuild_tasks=set()`.

Verified the "Out of Scope" assumption first: `bga/utilisation/__init__.py`'s `_build_cpu_intervals` already does correct `task_key in retry_tasks` / `task_key in rebuild_tasks` membership routing to `CPUBucket.WASTED_RETRY`/`WASTED_REBUILD` - no consumer-side bug found, so no scope expansion was needed.

## Spec Reference
Read only: `sed -n '1421,1475p' docs/specification.md` (Part 30 — Utilisation Axis, esp. 30.2 Buckets: `useful, idle_no_tasks, idle_underparallel, wasted_retry, wasted_rebuild, untracked`).

## Current Broken Behavior
File: `bga/analyzer.py:472-473` — `retry_tasks=set()` and `rebuild_tasks=set()` are hardcoded, unconditionally, when calling into the utilization analyzer. Comments: `# Would need retry detection` / `# Would need rebuild detection`. As a result the `wasted_retry`/`wasted_rebuild` CPU buckets can never be populated — utilization numbers are structurally incomplete regardless of any spec-nuance fixes elsewhere.

## Required Fix
1. Retry detection: a task is a retry if another task exists with the same `element_uid|task_kind|phase` but a higher `attempt` number in the task key (`element_uid|task_kind|phase|attempt` format, Part 5.2) — i.e. multiple attempts recorded for the same logical unit of work. Identify all non-final attempts as `retry_tasks` (the wasted/discarded ones), not the final successful attempt.
2. Rebuild detection: check whether the trace/graph model already carries any cache-hit/cache-miss signal (check `Element`/`TaskSpan` fields in `bga/ingest/models.py` for anything like a cache status field before assuming you need to add one) — a "rebuild" is a BUILD task that executed despite a matching `cache_key` having been available (i.e. work that could have been avoided). If no such signal exists in the data model at all, this may need a new field threaded through from ingestion — check the `graph/v9`/`trace/v9` data contracts (`sed -n '1513,1628p' docs/specification.md`, Part 32) for whether this is already representable before adding new fields.
3. Wire the resulting `retry_tasks`/`rebuild_tasks` sets into the existing utilization analyzer call, replacing the hardcoded empty sets.

## Out of Scope
- Don't change the utilization bucket *computation* itself (`bga/utilisation/__init__.py`) — it already presumably handles these sets correctly once populated; this task is about producing correct input sets, not changing how they're consumed. Verify that assumption first — if the consumer side also has bugs, log a new tracker row rather than expanding this task's scope.

## Acceptance Test
Build a fixture with: (a) a task that has two attempts for the same `element_uid|task_kind|phase` (attempt 0 and attempt 1) — assert attempt 0 lands in `retry_tasks` and contributes to the `wasted_retry` bucket; (b) if rebuild detection requires a data model field, a task whose cache-key matches a "should have been cached" scenario per whatever signal you identified in step 2 — assert it lands in `rebuild_tasks` / `wasted_rebuild`.

Run: whichever test file houses this, plus `PYTHONPATH=. python3 tests/test_e2e.py`.

## Verification Log
```
$ PYTHONPATH=. python3 -m pytest tests/ -q
112 passed   # was 100

$ PYTHONPATH=. python3 tests/test_e2e.py
Results: 7 passed, 0 failed

$ make check-clean
OK: no ignored files are tracked
```
New tests in `tests/unit/test_retry_rebuild_detection.py` (12 tests): 5 unit
tests directly on `compute_retry_tasks` (non-final attempt flagged, single
attempt not flagged, 3-attempt chain, different elements/phases don't
interfere), 4 unit tests directly on `compute_rebuild_tasks` (matching
historical cache_key flagged, changed cache_key not flagged - a genuine
cache miss, no historical_runs -> empty, non-BUILD task never flagged),
and 3 end-to-end tests through `BuildEfficiencyAnalyzer` confirming the
real `wasted_retry`/`wasted_rebuild` CPU buckets populate with the exact
expected microsecond values (and that a genuine cache miss stays in
`useful`, not `wasted_rebuild`).
