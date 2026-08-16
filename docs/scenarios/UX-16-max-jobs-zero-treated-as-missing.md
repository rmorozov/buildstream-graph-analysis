# UX-16: `native_max_jobs`/`cpu_budget`/`host_cpu_count` of `0` silently treated as "missing"

**Priority:** High | **Status:** 🟢 Done | **Depends on:** `UX-12`, `UX-15`

## Motivation

Raised by an external review of `UX-12`/`UX-13`/`UX-14`/`UX-15`'s merged code, specifically flagging that BuildStream documents `--max-jobs 0` as a real, meaningful sentinel value ("let BuildStream choose - up to the available host threads, capped at 8"), not "zero parallelism" - and asking whether `bga`'s new `native_max_jobs` field handles that value correctly anywhere it's consumed.

Checked directly against the real code, not taken on the review's word: `bga/analyzer.py`'s `_check_process_oversubscription` (`UX-12`) gates its entire check on:

```python
if not builders or not native_max_jobs or not governing_cores:
    return
```

`not 0` is `True` in Python - so a real, explicit `native_max_jobs=0` (or, less likely but symmetric, `cpu_budget=0`/`host_cpu_count=0`) is silently treated identically to "this field was never captured," and the whole oversubscription/undersubscription check is skipped - even though `0` here is not missing data, it's real, present data with a specific, documented meaning.

Reproduced directly (not hypothetical):

```python
run_context = {
    "resource_capacities": {"PROCESS": 8},
    "native_max_jobs": 0,   # BuildStream's real "auto, capped at min(host_cores, 8)"
    "host_cpu_count": 4,
}
# ... bga analyze this run ...
# violations: []   <- should have fired resource_oversubscription:
#   BuildStream would resolve native_max_jobs=0 to min(4, 8)=4 here, so real
#   demand is builders(8) x 4 = 32 vs governing_cores=4, well past the
#   default_demand=16 threshold - exactly the condition this check exists
#   to catch, silently missed because `not 0` short-circuited the whole
#   function.
```

Confirmed the loader itself is fine (`bga/ingest/loader.py`: `data.get('native_max_jobs')` correctly preserves `0`, doesn't coerce it) and `tools/bst_extract_run.py`'s capture path is fine too (`if native_max_jobs is not None:` - correctly distinguishes `0` from "not given"). The bug is isolated to `_check_process_oversubscription`'s own truthiness gate.

## Required Fix

1. Replace the truthiness gate in `_check_process_oversubscription` with explicit `is None` checks for `builders`/`native_max_jobs`/`governing_cores` (and `cpu_budget`/`host_cpu_count` wherever they're separately checked for the `cpu_budget_exceeds_host_capacity` violation).
2. Resolve `native_max_jobs == 0` to its real BuildStream-documented meaning before using it in the demand formula: `min(governing_cores, 8)` - the same formula `default_demand` already uses for BuildStream's own unconfigured behavior, since `max-jobs: 0` *is* BuildStream choosing that same behavior, not a different one. Do this resolution once, explicitly (e.g. a small `_resolve_native_max_jobs(native_max_jobs, governing_cores)` helper), not by relying on `0` happening to look "falsy but numerically small" anywhere else in the formula.
3. Audit `builders`/`resource_capacities.get('PROCESS')` for the same class of bug - `builders=0` is not a realistic real-world value (BuildStream wouldn't run with zero build slots) but the code should not rely on that assumption implicitly; an explicit `is None` check costs nothing and removes the ambiguity either way.

## Fix Implemented

`bga/analyzer.py::_check_process_oversubscription`'s truthiness gate replaced with explicit `is None` checks for `builders`/`native_max_jobs`/`governing_cores`. `native_max_jobs == 0` is resolved to `min(governing_cores, 8)` inline (BuildStream's own real "auto" behavior) *before* being used anywhere in the demand math - the resolved value, not the literal `0`, is what appears in `actual_demand`'s arithmetic. Both the `resource_oversubscription`/`resource_undersubscription` violation dicts and the log messages carry the resolved value plus a new `native_max_jobs_was_auto: bool` field, so a reader can tell the difference between "the operator declared 4" and "the operator declared 0, which resolved to 4" - `bga/report/text.py`'s violation formatting surfaces this explicitly (`"native max-jobs=4 (resolved from --max-jobs=0's own auto sentinel)"`).

## Out of Scope

- Any change to the underlying oversubscription/undersubscription math itself beyond correctly resolving the `0` sentinel - `UX-12`'s own threshold design stays as-is.

## Acceptance Test

1. A run with `native_max_jobs=0`, `resource_capacities.PROCESS` large enough that `builders * min(host_cpu_count, 8)` exceeds the default-demand threshold, produces a real `resource_oversubscription` violation (currently produces none).
2. A run that genuinely omits `native_max_jobs` (key absent, matching most run-context.json files today) still correctly produces no violation - confirms the fix distinguishes "0" from "absent" rather than just inverting the bug.
3. Full suite green.

## Verification Log

Done for real, 2026-08-16. New tests: `tests/unit/test_max_jobs_zero_sentinel.py` (6 tests) - `native_max_jobs=0` correctly resolves and fires `resource_oversubscription` for the exact scenario from this doc's own Motivation section; resolution correctly uses the governing ceiling (`cpu_budget` when present, not raw `host_cpu_count`); resolution correctly caps at 8; a genuinely fine `builders=4, native_max_jobs=0` (resolves to BuildStream's own real 4x4 defaults) is not flagged; a genuinely absent `native_max_jobs` is still correctly skipped (confirms the fix distinguishes "0" from "absent," not just inverts the bug); the text report names the auto-resolution explicitly. Full suite green (`make lint`, `pytest` - 506 passed, same 7 pre-existing environment-only failures as `main`).

Real re-verification via direct CLI invocation, exactly this doc's own cited scenario (`builders=8`, `native_max_jobs=0`, `host_cpu_count=4`): `bga analyze` now produces a real `resource_oversubscription` violation (was: zero violations before this fix) - text output: `"oversubscription: builders=8 x native max-jobs=4 (resolved from --max-jobs=0's own auto sentinel) = 32 potential concurrent processes vs a 4-core host (BuildStream's own defaults for that ceiling: 16)..."`; `--format json`'s violation entry carries `"native_max_jobs": 4, "native_max_jobs_was_auto": true, "actual_demand": 32, "default_demand": 16`.
