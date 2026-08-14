# P4-03: Convenience script for local development scenarios

**Priority:** P4 | **Status:** 🔴 Not Started | **Depends on:** none

## Spec Reference
Not spec-mandated - developer-experience tooling.

## Current State
`Makefile` covers `test`/`test-e2e`/`clean`/`check-clean`/`install`/`dev` (and a `lint` placeholder, see `P4-04`), but there's no single command that takes a developer from "I changed some code" to "I can see what a real report looks like" without hand-writing a run directory or digging through `tests/fixtures/`. The closest thing today is `tests/fixtures/synthetic_multi_subproject/generate_fixture.py::build_fixture`, which is only wired into `tests/test_synthetic_multi_subproject.py`, not exposed as a standalone dev command.

## Required Fix
Add a small script (e.g. `tools/dev_run.sh` or a `make dev-run` target, whichever fits the existing `Makefile`-centric convention better) that, in one command:
1. Regenerates (or reuses, if unchanged) a realistic sample run directory - reuse `tests/fixtures/golden/mixed_task_kinds/` (`P3-08`, small/instant) or `tests/fixtures/synthetic_multi_subproject/generate_fixture.py` (larger/realistic) rather than inventing a third fixture.
2. Runs `bga analyze` (full report, `--diagnostics`, text format) against it and prints the result.
3. Exits non-zero on any failure (ingestion error, analysis error, or non-zero `bga` exit code), so it's also useful as a fast local smoke test distinct from the full `pytest` suite.

Consider also folding in a `--watch` or re-run-on-change mode if a lightweight file-watcher dependency is acceptable, but the one-shot version alone is the valuable Pareto slice - don't over-build this.

## Out of Scope
- Don't replace `make test`/`pytest` - this is a fast, narrow "does the tool still basically work and what does it show me" loop, not a substitute for real test coverage.
- Don't add new fixtures - reuse what `P3-01`/`P3-08`/`P3-10` already built.

## Acceptance Test
A developer with a clean checkout can run the new command with zero setup beyond `make dev` and see a real, current analysis report within a few seconds.

## Verification Log
_(append real command + output here once run, before marking 🟢)_
