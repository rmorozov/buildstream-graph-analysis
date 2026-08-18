# P1-36: `clamp_task_starts` can silently produce a negative-duration task on a genuine ordering violation

**Priority:** P1 | **Status:** 🟢 Done | **Depends on:** none (a distinct root cause from `P1-27`'s already-fixed ready-time task-kind mismatch - see Background)

## Spec Reference

Part 3.3 (Ordering Validation): "If a genuine negative ordering remains after normalization... the trace contains an ordering violation. No hidden runtime correction is performed" (`docs/spec/specification.md:259-286`). Part 3.4 (Immutable Finish Time): when a start is clamped to ready time, finish stays immutable, so `duration' = finish - start'` (`docs/spec/specification.md:289-303`). Neither section states what must happen when combining these two rules on a genuine ordering violation produces `start' > finish` - a structurally invalid interval - which is exactly the gap this task closes.

## Background

Raised by an external review; independently verified against the current code before filing.

`normalize_trace` (`bga/normalize/timestamps.py:316-348`) runs, in order: quantize timestamps → compute ready times → **validate ordering** (`validate_ordering`, recording `ordering_violation` entries into the returned `violations` list) → **clamp starts to ready times** (`clamp_task_starts`). Critically, step 4 runs unconditionally on every span, including ones step 3 already flagged as an ordering violation - `clamp_task_starts` (`bga/normalize/timestamps.py:234-313`) does `clamped_start = max(q_start, ready_us)` (line 283) with `clamped_finish = q_finish` held immutable (line 291), and constructs the resulting `NormalizedTask` (lines 303-311) with no check that `clamped_start <= clamped_finish`.

If a real ordering violation makes `ready_us` (derived from a predecessor's finish time, `compute_ready_times`) land *after* the successor's own raw finish time - a malformed or genuinely buggy input trace, not merely quantization noise (Part 3.3's own carve-out for the "small negative gap that disappears through quantization" case) - the clamp produces `clamped_start > clamped_finish`, i.e. a structurally invalid `NormalizedTask` with negative `dur_us`. Nothing downstream (occupancy sweep, attribution, critical path) is guaranteed to reject this; it can propagate silently into the rest of the pipeline.

This is a **different** root cause from `P1-27` (already fixed - "ready-time task-kind mismatch" produced negative durations via a different bug, matching the wrong predecessor task kind when computing ready time). This task is about the clamp step's own missing invariant check, independent of how `ready_us` was derived - the same negative-duration symptom can recur through this separate path even with `P1-27`'s fix in place, given a genuine ordering violation in the input.

## Required Fix

1. `clamp_task_starts` (or `normalize_trace`, whichever is the more natural boundary) must detect when clamping would produce `clamped_start > clamped_finish` and treat that task as explicitly invalid, not silently emit a negative-duration `NormalizedTask`.
2. Decide and document the precise handling: likely, a task in this state should be excluded from the normal `normalized_tasks` list and instead surfaced as a hard violation (extending the existing `ordering_violation` violation type, or a new explicit type) that the caller can act on - consistent with Part 3.3's "no hidden runtime correction" and this codebase's general "no silent correction" discipline (e.g. how `classify_resource_wait` reports `UNKNOWN`/`ambiguous` rather than fabricating a holder).
3. Add an explicit non-negativity assertion/guard at construction (or immediately after) for every `NormalizedTask`, so this invariant is enforced structurally, not just for this one code path - matching how other invariants in this codebase (e.g. I4's exact attribution identity) are checked directly rather than trusted by convention.

## Out of Scope

- Don't touch `P1-27`'s already-fixed ready-time computation - this task assumes `ready_us` can still, in principle, be wrong or reflect a genuinely malformed input, and is about making the clamp step itself robust to that, not re-deriving ready-time computation.
- Don't attempt to "fix" a genuine ordering violation by silently reordering or extending the successor's finish time - Part 3.3 explicitly forbids hidden runtime correction; the correct behavior is to surface the violation, not paper over it.

## Acceptance Test

1. Construct a fixture with a genuine ordering violation (predecessor finishes at 100us, successor's own raw start/finish is 80us/90us, both well outside quantization epsilon) and confirm: (a) it's reported in `violations` as before, and (b) no `NormalizedTask` with negative `dur_us` reaches the rest of the pipeline - either the task is excluded with a clear diagnostic, or the pipeline raises/reports a distinguishable, actionable error rather than silently computing on it.
2. Confirm the existing "small negative gap absorbed by quantization" case (already covered by existing tests, per Part 3.3's own carve-out) is unaffected - only genuine, post-quantization violations trigger the new handling.
3. Re-run the full suite, including `P1-27`'s own regression tests, to confirm no overlap/regression between the two fixes.
4. Full suite green.

## Verification Log

`clamp_task_starts` (`bga/normalize/timestamps.py`) now detects `clamped_start > clamped_finish` before constructing a `NormalizedTask`, excludes that task, and appends a new `clamp_negative_duration` violation (returned alongside the task list, threaded through `normalize_trace` into the existing `violations` list). `NormalizedTask.__post_init__` (`bga/ingest/models.py`) additionally rejects `finish_us < start_us` at construction unconditionally - a structural guard independent of this one call site.

Found and fixed a real, pre-existing bug this exposed: `tests/unit/test_dependency_type_gating.py`'s own `test_build_type_edge_still_included_in_normalized_task_dependencies` fixture had a successor whose raw span finished *before* its build-gated ready time - i.e. it was already, silently, constructing a negative-duration task and never checking `dur_us` at all. Fixed the fixture to a realistic (non-violation) scenario and added an explicit `dur_us >= 0` assertion.

```text
$ python3 -m pytest tests/unit/test_normalize.py tests/unit/test_dependency_type_gating.py -v
19 + 10 passed
$ python3 -m pytest -q   # full suite
394 passed, 11 skipped
$ make lint
All checks passed!
```
