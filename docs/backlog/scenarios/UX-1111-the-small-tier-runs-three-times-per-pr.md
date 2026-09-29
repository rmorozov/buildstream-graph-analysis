# UX-1111: the small tier runs three times on every pull request

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** quality gates audit (`docs/audits/quality-gates-2026-09-29.md`, 2026-09-29) | **Serves:** the implementing session | **Topic:** guards | **Area:** tools | **Shape:** judgement | **Reading:** runner:test

**Guard:** none — named test_a_hang_is_caught_inside_the_one_run.py, absent from tests/

## Motivation

`test (3.12)` on a PR runs the small tier as a hang backstop (140 s median,
`ci.yml:160`), again inside the full suite (675 s), and again single-process
(250 s, `:541`, `UX-336`'s ordering check). The backstop exists to catch a
hang (`UX-421`); a per-test timeout catches a hang and names the test inside
the one run the job already makes.

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
