# P1-33: `cpu_accounting.effective_cpus` is BuildStream's builder count, not measured CPU capacity

**Priority:** P1 | **Status:** 🟢 Done | **Depends on:** none

## Spec Reference
Part 30.1: `capacity_cpu_s = effective_cpus × wall_clock`, "when CPU accounting is available" (`docs/spec/specification.md:1421-1433`) - conditional phrasing implies `effective_cpus` is real, independently-measured CPU capacity, not always present. Part 30.3's own oversubscription check is `builders × max_jobs > effective_cpus` (`docs/spec/specification.md:1449-1455`) - `builders`/`max_jobs` and `effective_cpus` are treated as **two distinct quantities being compared**, not the same number under two names. I9 (CPU Reconciliation, `docs/spec/specification.md:1801-1821`): `abs(sum(cpu_buckets) - capacity_cpu_s) <= 0.02 * capacity_cpu_s`, "when CPU accounting is available" - again conditional, implying a real "unavailable" state must exist.

## Background
Raised by an external review; independently verified against the current code before filing.

`tools/bst_extract_run.py:272` and `tools/bst_run_context.py:84` both set `run_context["cpu_accounting"] = {"effective_cpus": scheduler["builders"]}` - i.e. `effective_cpus` is populated directly from BuildStream's `--builders` scheduling parameter (a job-slot count), never from a real CPU core/thread measurement. Since `scheduler["builders"]` is always resolvable from a real BuildStream log (either the log's own "Maximum Build Tasks:" header or a hardcoded default - `tools/bst_log_to_chrome_trace.py`'s `DEFAULT_BUILDERS`), `cpu_accounting` is **always populated** by today's real ingestion pipeline - "CPU accounting is available" is never actually false, even though no real CPU measurement has ever been taken.

Compounding this, `bga/analyzer.py:721,729` explicitly estimates per-task CPU usage rather than measuring it: `# For now, assume each task uses 100% of one CPU during execution` / `'cpu_usage_us': task.dur_us`. So both sides of I9's reconciliation check are derived from the same underlying data (task wall-clock durations and the builder count) rather than independent measurements - the "reconciliation" is close to tautological as currently wired, not a genuine cross-validation.

This also breaks Part 30.3's oversubscription check in a concrete way: `builders × max_jobs > effective_cpus` becomes `builders × max_jobs > builders`, which is true essentially whenever `max_jobs > 1` (any `make -jN` build) - regardless of the real CPU core count, defeating the check's purpose (a builder task can spawn `make -jN`, so `CPU usage != 1 CPU` per builder slot, exactly the case Part 30.3 exists to flag realistically, not vacuously).

## Required Fix
1. Separate two distinct concepts, both in `bga/ingest/models.py` and the run-context/v9 extension surface: **scheduling capacity** (`builders`/`max_jobs` - already real, already correctly sourced) and **CPU accounting** (`effective_cpus`, per-task `cpu_usage_us` - must come from a real measurement source or be explicitly absent).
2. `tools/bst_extract_run.py`/`tools/bst_run_context.py` must not populate `cpu_accounting.effective_cpus` from `builders` - either omit `cpu_accounting` entirely (today's real, honest state - no CPU measurement source exists in this pipeline yet) or, if/when a real source is added (e.g. `cgroup` CPU accounting, `/proc` sampling, or a user-supplied value), populate it from that.
3. `bga/analyzer.py`'s utilisation computation must not synthesize `cpu_usage_us = task.dur_us` and report it as if it were `cpu_accounting`. If no real CPU measurement exists, the report should say so explicitly (e.g. "CPU accounting: unavailable") rather than presenting an estimate under the same field name/confidence level as a measurement - consistent with this codebase's existing "no silent correction, label what is estimated" discipline used elsewhere (cold floors, confidence bands).
4. I9's reconciliation check and Part 30.3's oversubscription check must only run when real `cpu_accounting` is present; both should report "unavailable" otherwise, not silently pass on synthetic data.
5. Task occupancy (how much wall-clock time each task held a job slot) remains valid, real, and useful data - this task is about not mislabeling it as CPU accounting, not about removing it. Keep whatever of today's "builder task occupancy" reporting is genuinely accurate under its own honest name.

## Out of Scope
- Don't attempt to build a real CPU-measurement ingestion source (cgroup/proc sampling) as part of this task - that's new instrumentation work with its own scope; this task is about not fabricating a substitute for it and mislabeling the substitute.
- Don't change how `builders`/`max_jobs` scheduling capacity is sourced or used elsewhere (capacity lower bound, replay) - those already correctly use scheduling capacity as scheduling capacity, not as a CPU-usage proxy.

## Acceptance Test
1. A real extracted run directory (via `tools/bst_extract_run.py`, no new CPU-accounting source added) reports CPU accounting as unavailable, not as a confident number derived from `builders`.
2. I9's reconciliation check and Part 30.3's oversubscription check are skipped (reported unavailable) rather than run against synthetic data, for a run with no real CPU accounting.
3. If/when a real CPU-accounting source is later wired in (test fixture with a hand-supplied, genuinely independent `cpu_accounting.effective_cpus`), I9's reconciliation check runs and is meaningful (not tautologically satisfied because both sides derive from the same task durations).
4. `builders × max_jobs > effective_cpus` is never evaluated using a `builders`-derived `effective_cpus` value.
5. Full suite green; update/verify `tests/unit/test_utilisation.py`'s existing CPU-reconciliation tests (`P3-06`) still hold under the corrected semantics.

## Verification Log
`tools/bst_extract_run.py`/`tools/bst_run_context.py` no longer populate `cpu_accounting.effective_cpus` from `scheduler["builders"]` - `cpu_accounting` is simply omitted (the honest state, since no real CPU measurement source exists in the pipeline), with a comment explaining why. `bga/utilisation/__init__.py`'s `_compute_effective_cpus` returns `None` instead of falling back to `1.0`. Added `UtilizationResult.cpu_accounting_available: bool`; `capacity_cpu_us`/`useful_pct`/`idle_pct`/`wasted_pct` are now `Optional` and gated on it. Idle-period analysis, oversubscription detection (Part 30.3), and I9 reconciliation all early-exit with `cpu_accounting_available=False` (distinct from the pre-existing wall_clock=0 case, which still yields `reconciliation_error_pct=0.0`) instead of silently running against synthetic `task.dur_us`-derived data. `to_dict()` surfaces `cpu_accounting_available`.

`tests/unit/test_utilisation.py`: 3 new tests confirming no-cpu-accounting reports unavailable (not a fabricated number), skips reconciliation/oversubscription, and that the removed `builders`-derived `effective_cpus` path is never evaluated. `tests/unit/test_bst_run_context.py`/`test_bst_extract_run.py` updated to assert `cpu_accounting` is absent from extracted output.

```
$ python3 -m pytest tests/unit/test_utilisation.py tests/unit/test_cpu_reconciliation.py tests/unit/test_bst_run_context.py tests/unit/test_bst_extract_run.py -v
62 passed, 1 skipped
$ python3 -m pytest -q   # full suite
409 passed, 11 skipped
$ make lint
All checks passed!
```
