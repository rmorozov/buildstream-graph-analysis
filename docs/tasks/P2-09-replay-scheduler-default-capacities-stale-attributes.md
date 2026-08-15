# P2-09: `ReplayScheduler`'s own default-capacity fallback reads nonexistent `RunContext` attributes

**Priority:** P2 | **Status:** 🟢 Done | **Depends on:** none

## Spec Reference
Part 18 (Replay): replay heuristics operate against real scheduling capacity. No spec-level requirement is violated by this bug on its own (the real `analyze` path is unaffected, see Background) - this is a "just works" API-correctness gap, not a spec-compliance gap.

## Background
Raised by an external review conducted after `P1-31`/`P1-32`/`P1-33` merged; verified directly against `bga/replay/scheduler.py` on `main` before filing.

`ReplayScheduler.__init__` (`bga/replay/scheduler.py:112-116`) builds its own fallback capacity dict:

```python
self._default_capacities = {
    'PROCESS': getattr(run_context, 'builders', 4) if run_context else 4,
    'DOWNLOAD': getattr(run_context, 'fetchers', 2) if run_context else 2,
    'UPLOAD': getattr(run_context, 'pushers', 2) if run_context else 2,
}
```

`RunContext` (`bga/ingest/models.py`) has never defined `builders`/`fetchers`/`pushers` attributes - the real field is `resource_capacities: Dict[str, int]` (e.g. `{"PROCESS": 4, "DOWNLOAD": 2, "UPLOAD": 2}`, per run-context/v9's own schema, Part 32.1). So `getattr(run_context, 'builders', 4)` always falls through to the hardcoded default `4` (and `2`/`2`), regardless of what the real run's actual capacities were - the same bug shape `P1-31` found and fixed in `bga/analyzer.py`'s `resource_capacity` construction, but in a different, independent call site that fix didn't touch.

**This does not currently corrupt `bga analyze`'s own output**: `BuildEfficiencyAnalyzer` (`bga/analyzer.py:220-222, 305`) constructs `ReplayScheduler(self.normalized_tasks, self.run_context)` but then calls `self.replay_scheduler.replay(default_caps)` with `default_caps = compute_default_capacities(self.run_context)` (a separate, correct helper) passed explicitly - `replay()`'s own `capacities` parameter overrides `self._default_capacities` (`bga/replay/scheduler.py:202`: `capacities = capacities or self._default_capacities.copy()`), so the stale fallback is never actually exercised by the main analysis pipeline today.

It **does** affect any other caller that constructs `ReplayScheduler(tasks, run_context)` and calls `.replay()` without an explicit `capacities` argument (a reasonable thing for a library consumer or a future CLI subcommand to do, given the constructor accepts `run_context` specifically "for default capacities" per its own docstring) - such a caller silently gets generic defaults instead of the run's real capacities, with no error or warning.

## Required Fix
1. `ReplayScheduler.__init__`'s `_default_capacities` construction must read `run_context.resource_capacities` (the real field), the same way `bga/analyzer.py`'s `resource_capacity` construction now does post-`P1-31` - not `getattr(run_context, 'builders'/'fetchers'/'pushers', ...)`.
2. Consider factoring this mapping (string resource name → `Resource` enum / capacity value, with the "unrecognized resource name -> skip with a warning, not raise" discipline `P1-31` established) into one shared helper reused by `bga/analyzer.py`, `bga/replay/scheduler.py`, and `compute_default_capacities` (`bga/floors/`) - three independent copies of essentially the same logic is exactly the pattern that let this specific bug (and `P1-31`'s original one) exist unnoticed in one of them while already fixed in another.
3. Keep a sensible hardcoded fallback (e.g. `PROCESS: 4`) for the case where `run_context` is `None` or has no `resource_capacities` at all - this task is about using real data when it exists, not about removing the "no run context available" degraded-but-functional path.

## Out of Scope
- Don't change `compute_default_capacities` itself (already correct, per `P1-31`'s Background) - only `ReplayScheduler`'s own independent fallback construction, and optionally, consolidating the two into one shared helper.
- Don't change `bga/analyzer.py`'s call site, which already passes explicit, correct capacities and is unaffected by this bug.

## Acceptance Test
1. `ReplayScheduler(tasks, run_context)` where `run_context.resource_capacities = {"PROCESS": 7}`, called via `.replay()` with **no** explicit `capacities` argument - the replay must use capacity `7` for `PROCESS`, not the hardcoded default `4`.
2. `ReplayScheduler(tasks, run_context=None)` - unchanged, falls back to the hardcoded defaults (no regression to the "no run context" path).
3. `bga analyze`'s own replay output is unchanged for every existing fixture (confirms this fix doesn't alter the already-correct main pipeline path, only the previously-unused fallback).
4. Full suite green.

## Verification Log
`ReplayScheduler.__init__`'s `_default_capacities` construction (`bga/replay/scheduler.py`) now calls the shared `compute_default_capacities(run_context)` helper (`bga/floors/capacity.py`) - the same one `bga/analyzer.py`'s LB computation already uses - instead of the independent `getattr(run_context, 'builders'/'fetchers'/'pushers', ...)` lookups, which always evaluated to the hardcoded defaults since `RunContext` has never defined those attributes. Notably, `compute_default_capacities`'s own docstring already documented this exact bug shape ("replay's previous separate getattr(...) lookups were dead code") - the helper existed and was correct, it just wasn't wired into `ReplayScheduler` itself.

New tests (`tests/unit/test_replay.py`, 2 new): `test_default_capacities_use_real_run_context_resource_capacities` - 5 independent tasks, `run_context.resource_capacities={"PROCESS": 5}`, no explicit `capacities` passed to `.replay()` - must fully parallelize (makespan 1000us), not silently cap at the stale hardcoded default of 4 (which would force makespan to 2000us); confirmed this fails against the pre-fix code via `git stash` (asserts `2000 == 1000`, i.e. reproduces the bug exactly). `test_default_capacities_fall_back_to_hardcoded_defaults_without_run_context` - regression guard, `run_context=None` still uses the hardcoded default unaffected.

```
$ python3 -m pytest tests/unit/test_replay.py -v
12 passed
$ python3 -m pytest -q   # full suite
422 passed, 11 skipped
$ make lint
All checks passed!
```
