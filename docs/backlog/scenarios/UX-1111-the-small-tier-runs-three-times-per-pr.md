# UX-1111: the small tier runs three times on every pull request

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** quality gates audit (`docs/audits/quality-gates-2026-09-29.md`, 2026-09-29) | **Serves:** the implementing session | **Topic:** guards | **Area:** tools | **Shape:** mechanical | **Reading:** runner:test

**Guard:** none — named test_a_hang_is_caught_inside_the_one_run.py, absent from tests/

## Motivation

`test (3.12)` on a PR runs the small tier as a hang backstop (140 s median,
`ci.yml:160`), again inside the full suite (675 s), and again single-process
(250 s, `:541`, `UX-336`'s ordering check). The backstop exists to catch a
hang (`UX-421`); a per-test timeout catches a hang and names the test inside
the one run the job already makes.

## Decision

Architect, round 151 (2026-09-29):

```text
Route:     `pytest-timeout` joins `dev` and requirements.lock; `timeout = 300` (signal) in pyproject's pytest ini_options (4.2x the slowest whole file, 71.6 s; no per-test data). Delete `Test (small tier, with a backstop)`; `Test (small tier, single process)` gets `if: github.event_name == 'push'`, keeps `timeout 900`. The namer reads the full run's junit
Rejected:  a smaller ceiling (60 s is under the slowest file); dropping the 1P timeout (it catches a hang in collection)
Files:     pyproject.toml; requirements.lock; .github/workflows/ci.yml; tests/tiers.py (retire SMALL_TIER_BACKSTOP_S, SMALL_TIER_CI_SLOW_S); tests/unit/test_the_tiers_are_a_partition.py; tests/unit/test_a_hang_is_caught_inside_the_one_run.py
Guard:     (a) subprocess pytest with `-o timeout=1` on a sleeping test prints "Timeout" and the node id; (b) `getini("timeout")` > 0
Mutation:  remove `timeout` from pyproject - (b) reddens; `-p no:timeout` - (a) reddens
Class:     optimization - test (3.12) sheds 140 s + 250 s of its 1,300 s median per PR
Split:     CI track, fifth; hunks meet 1121's in the `test` job
```

## Required Fix

`pytest-timeout` joins the dev extra (and `requirements.lock`) with a
per-test ceiling in `pyproject.toml`; the backstop step goes. The
single-process small tier runs on push to main, not on PRs. The junit the
namer reads (`UX-618`) comes from the full run.

## Out of Scope

The tier floors in `tests/tiers.py`; the drift gate.

## Acceptance Test

`tests/unit/test_a_hang_is_caught_inside_the_one_run.py`: a test that
sleeps past the ceiling, run in a subprocess, fails with the timeout's
message and its node id. Mutation: remove the `timeout` setting; the
subprocess hangs to the harness limit and the guard reddens. The Outcome
carries `test (3.12)`'s wall on three PR runs against 1,300 s.
