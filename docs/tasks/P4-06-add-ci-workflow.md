# P4-06: No CI configured at all - add a GitHub Actions workflow

**Priority:** P4 | **Status:** 🟢 Fixed & Verified (2026-08-14) | **Depends on:** `P4-04` (lint should exist before CI enforces it, though the test+check-clean legs don't need to wait) - done

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

## What was built
`.github/workflows/ci.yml`: triggers on push/PR to `main`, one job matrixed across Python 3.9/3.10/3.11/3.12 (`pyproject.toml`'s own classifiers), `fail-fast: false` so one version's failure doesn't hide another's. Each leg: checkout, `actions/setup-python`, `pip install -e ".[dev]"`, `make check-clean`, `make lint`, `make test`. Deliberately does not install the `bst` extra (needs the `bubblewrap` system package and is documented as optional - `docs/ingestion-pipeline.md`) - CI runs the suite in its documented "no `bst` on `PATH`" mode (skips the `bst`-gated real end-to-end tests), same as this repo's own local dev default.

## Verification Log
Full local simulation of every workflow step, from a genuinely fresh venv (matching what `actions/setup-python` + a clean checkout would produce - directly verified for Python 3.11, the version available in this environment; the other matrix legs run the identical Python-version-agnostic commands):
```
$ python3 -m venv /tmp/ci_sim_env && /tmp/ci_sim_env/bin/pip install -e ".[dev]"
... (clean install, exit 0)

$ make check-clean
OK: no ignored files are tracked

$ make lint
ruff check bga/ tools/ tests/
All checks passed!

$ make test
======================= 379 passed, 8 skipped in 13.17s ========================
```
Acceptance test 1 (red CI), both failure modes verified for real:
```
# A deliberately broken test:
$ make test
...
FAILED tests/unit/test_utilisation.py::test_deliberately_broken_for_ci_verification - assert False
================== 1 failed, 379 passed, 8 skipped in 11.22s ===================
make: *** [Makefile:21: test] Error 1
$ echo $?
2

# A deliberately re-added tracked build artifact (fresh clone + commit):
$ git add -f bga/__pycache__/fake.pyc && git commit -m "..."
$ make check-clean
ERROR: the following tracked files match .gitignore patterns:
bga/__pycache__/fake.pyc
make: *** [Makefile:52: check-clean] Error 1
$ echo $?
2
```
Both confirm a nonzero `make` exit code, which GitHub Actions surfaces as a failed step -> red check, exactly as the acceptance test requires. Both scratch changes discarded afterward (`git diff --stat` confirmed no residual changes to the real repo).

`git diff --stat`/`git status` confirmed no unintended changes to the working tree from this verification. Full suite (real repo, unmodified): 379 passed, 8 skipped (no `bst` on `PATH` in this environment - matches what CI itself will see).
