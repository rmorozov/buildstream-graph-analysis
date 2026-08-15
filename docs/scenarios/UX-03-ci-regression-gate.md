# UX-03: No CI-friendly "fail if this build got meaningfully worse" gate

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-01` (run comparison), `UX-02` (efficiency score - the natural gating metric)

## Motivation

Filed while brainstorming `bga`'s main user scenarios. A natural extension of `UX-01`: once two runs can be compared, a CI pipeline needs a way to *act* on that comparison automatically (fail the pipeline, post a warning) rather than a human reading `bga compare`'s report every time. Confirmed against `bga/cli.py`'s exit-code contract (`docs/cli.md`'s own Exit Codes section: 0/1/2/3, all about ingestion/analysis failure, none about a *regression* in the analyzed build itself) - there is currently no way to make `bga` itself signal "this PR made the build worse" to a CI system's pass/fail gate.

## Required Fix

1. Extend `bga compare` (`UX-01`) with a gating mode - e.g. `bga compare RUN_A RUN_B --fail-on-regression [threshold]` - that exits non-zero specifically when the candidate run has regressed beyond `threshold` (a sensible default, e.g. a percentage-point drop in `efficiency_score` from `UX-02`, or an absolute/relative increase in `total_duration_us`/`t_infinity_observed` - pick one primary gating metric and document why, rather than an ambiguous multi-metric AND/OR).
2. A distinct exit code (not reusing 1/2/3, which already mean "general error"/"ingestion failure"/"analysis failure") so CI logs can distinguish "the build got worse" from "bga itself broke" - document the new code in `docs/cli.md`'s Exit Codes table alongside the existing four.
3. Respect `UX-01`'s low-confidence caveat: if the comparison itself was flagged as low-confidence/not-reliably-comparable, the gate should not fail the pipeline on a possibly-noisy signal - fail open (don't block) with a clear warning instead, and document this choice.
4. A worked CI example in `docs/cli.md`'s Example Workflows section (a GitHub Actions snippet: extract two runs, `bga compare --fail-on-regression`, let its exit code gate the job) - this is exactly the kind of workflow `.github/workflows/ci.yml` could eventually adopt for `bga`'s own examples, though wiring that up for real is a separate, later step.

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
_(append real command + output here once run, before marking 🟢)_
