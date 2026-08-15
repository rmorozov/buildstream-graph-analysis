# UX-03: No CI-friendly "fail if this build got meaningfully worse" gate

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-01` (run comparison), `UX-02` (efficiency score - the natural gating metric)

## Motivation

Filed while brainstorming `bga`'s main user scenarios. A natural extension of `UX-01`: once two runs can be compared, a CI pipeline needs a way to *act* on that comparison automatically (fail the pipeline, post a warning) rather than a human reading `bga compare`'s report every time. Confirmed against `bga/cli.py`'s exit-code contract (`docs/cli.md`'s own Exit Codes section: 0/1/2/3, all about ingestion/analysis failure, none about a *regression* in the analyzed build itself) - there is currently no way to make `bga` itself signal "this PR made the build worse" to a CI system's pass/fail gate.

## Required Fix

1. Extend `bga compare` (`UX-01`) with a gating mode - e.g. `bga compare RUN_A RUN_B --fail-on-regression [threshold]` - that exits non-zero specifically when the candidate run has regressed beyond `threshold` (a sensible default, e.g. a percentage-point drop in `efficiency_score` from `UX-02`, or an absolute/relative increase in `total_duration_us`/`t_infinity_observed` - pick one primary gating metric and document why, rather than an ambiguous multi-metric AND/OR).
2. A distinct exit code (not reusing 1/2/3, which already mean "general error"/"ingestion failure"/"analysis failure") so CI logs can distinguish "the build got worse" from "bga itself broke" - document the new code in `docs/cli.md`'s Exit Codes table alongside the existing four.
3. Respect `UX-01`'s low-confidence caveat: if the comparison itself was flagged as low-confidence/not-reliably-comparable, the gate should not fail the pipeline on a possibly-noisy signal - fail open (don't block) with a clear warning instead, and document this choice.
4. A worked CI example in `docs/cli.md`'s Example Workflows section (a GitHub Actions snippet: extract two runs, `bga compare --fail-on-regression`, let its exit code gate the job) - this is exactly the kind of workflow `.github/workflows/ci.yml` could eventually adopt for `bga`'s own examples, though wiring that up for real is a separate, later step.

## Fix Implemented

1. **`bga compare BASELINE CANDIDATE --fail-on-regression [--regression-threshold PCT]`** - new flags on the existing `compare` subcommand.
2. **Primary gating metric**: `total_duration_us` (Part 4.3's real wall-clock duration, `UX-10`) - the same metric `compare_runs`'s own `verdict` field already gates on, at the same default 1% significance band, rather than inventing a second, parallel definition. Chosen over `efficiency_score` because it's already the number the report's own `IMPROVED`/`REGRESSED`/`NO SIGNIFICANT CHANGE` verdict is built from - `--fail-on-regression` (no threshold override) fails exactly when a human reading the report would call it a regression, never something silently different. `bga/compare.py`'s new `regression_exceeds_threshold(comparison, threshold_pct=None)` is the single function both the default path and a `--regression-threshold` override go through.
3. **Distinct exit code `4`** (`bga/cli.py`'s `EXIT_CODE_REGRESSION`) - separate from `1`/`2`/`3`, which all mean "`bga` itself failed to run"; `4` means the opposite, `bga` ran successfully and is reporting a real regression in the *analyzed build*. Documented in `docs/cli.md`'s Exit Codes table.
4. **Fail-open on low confidence**: `_compare_exit_code` in `bga/cli.py` checks `comparison.low_confidence` first and, if true, prints a warning to stderr and returns `0` unconditionally - regardless of what the verdict says - so a noisy/low-provenance comparison never blocks a pipeline.
5. **Default behavior unchanged**: without `--fail-on-regression`, `bga compare` still always exits `0` regardless of verdict, exactly as before this task (`UX-01`'s own original design note).
6. **Worked GitHub Actions example** added to `docs/cli.md`'s `bga compare` section, plus the full flag/exit-code documentation.

## Out of Scope

- Actually wiring this into `.github/workflows/ci.yml` for this repo's own example projects - a good follow-up once the gate exists and has been used manually a few times, not part of this task.
- Historical trend storage/dashboards across more than two runs - out of scope here as it was for `UX-01`.

## Acceptance Test

1. A candidate run regressed beyond the default threshold exits with the new distinct code.
2. A candidate run within tolerance (including a genuine improvement) exits 0.
3. A low-confidence comparison exits 0 with a visible warning, not the regression code, per the "fail open" rule above.
4. `docs/cli.md` documents the new flag and exit code with a real, verified example.
5. Full suite green.

## Verification Log

Done for real, 2026-08-15. New tests: `tests/unit/test_compare.py` (+6 tests, all real subprocess CLI invocations - a real high-confidence regression exits `4` with `Regression gate FAILED` on stderr; a real improvement and a within-tolerance pair both exit `0`; a real regression *without* the flag still exits `0` (default behavior unchanged); a real regression on a deliberately low-confidence pair exits `0` with the fail-open warning; a custom `--regression-threshold` can pass a small regression the default would flag). High-confidence test fixtures built by copying the checked-in golden fixture (`tests/fixtures/golden/mixed_task_kinds`, real complete `run_identity`) with `app.bst`'s duration changed - `_chain_run_dir`'s existing hand-built fixtures deliberately lack `run_identity` (used elsewhere to test the low-confidence path), so they can't exercise the real gate-fail path themselves. Full suite green (`make lint`, `pytest` - 500 passed, same 7 pre-existing environment-only failures as `main`).

Real re-verification against this task's own acceptance test, via direct CLI invocation (not just pytest): a candidate regressed by +31.2% real total duration exits `4` with `Regression gate FAILED: candidate run's total duration regressed beyond the default significance threshold (verdict: regressed).` on stderr; the same baseline against an improved candidate exits `0`; a deliberately low-confidence pair (no `run_identity`, confidence `0.75`) with a real +166.7% regression exits `0` with `Warning: --fail-on-regression not applied - at least one run's confidence is below the 'high' band...` on stderr, per the fail-open rule.
