# P4-06: No CI configured at all - add a GitHub Actions workflow

**Priority:** P4 | **Status:** 🔴 Not Started | **Depends on:** `P4-04` (lint should exist before CI enforces it, though the test+check-clean legs don't need to wait)

## Spec Reference
Not spec-mandated - repository/process hygiene. Brainstormed while scoping the other `P4` usability tasks (not explicitly requested, but the single highest-leverage gap found).

## Current State (confirmed)
There is no `.github/` directory at all in this repository - confirmed via a direct filesystem check. Every verification claim in `docs/fix-progress-tracker.md`'s entire history (`make test`, `make test-e2e`, `make check-clean`, full-suite pass counts) has been run manually, by hand, once, at the time each task was done. Nothing prevents a future PR from merging with a failing test, a re-introduced tracked build artifact (the exact class of bug `make check-clean` exists to catch, per its own comment referencing a real past incident in PR #9), or (once `P4-04` lands) a lint violation.

## Required Fix
Add `.github/workflows/ci.yml` (or similar) running on every push/PR to `main`:
1. `pip install -e ".[dev]"`
2. `make check-clean`
3. `make lint` (once `P4-04` lands; until then, this leg can be added as a no-op placeholder step or skipped)
4. `make test` (full suite) - consider matrix-testing across the Python versions already declared supported in `pyproject.toml` classifiers (3.9-3.12), or at minimum pin to one concrete version and note the gap if full matrix testing is deferred.

## Out of Scope
- Don't add deployment/publish/release automation - this is about catching regressions on PRs, not packaging/release workflow.
- Don't add coverage-threshold gating (`pytest-cov` is already a dev dependency, but enforcing a numeric coverage floor is a separate policy decision, not a mechanical follow-on to "run the tests").

## Acceptance Test
1. A deliberately-broken PR (failing test, or a tracked build artifact re-added) shows a red CI check.
2. A clean PR shows a green CI check, running in a reasonable time (the full suite is ~231 tests, ~15s locally as of this writing - CI overhead should stay well under a minute or two total).

## Verification Log
_(append real command + output here once run, before marking 🟢)_
