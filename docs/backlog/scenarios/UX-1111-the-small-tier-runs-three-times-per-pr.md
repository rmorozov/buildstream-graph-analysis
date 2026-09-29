# UX-1111: the small tier runs three times on every pull request

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** quality gates audit (`docs/audits/quality-gates-2026-09-29.md`, 2026-09-29) | **Serves:** the implementing session | **Topic:** guards | **Area:** tools | **Shape:** mechanical | **Reading:** runner:test

**Guard:** test_a_hang_is_caught_inside_the_one_run.py

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

## Outcome

### The gap, measured

```text
$ python3 A-1111-gap.py <ci.yml>   (the `make test`/`test-small` steps whose if: holds, replay engine)
A-ci-base.yml pull_request 3.12: ['Test (small tier, with a backstop)', 'Test (with a timing report)', 'Test (small tier, single process)']
A-ci-base.yml push 3.12: ['Test (small tier, with a backstop)', 'Test (with a timing report)', 'Test (small tier, single process)']
```

### The close, measured

```text
ci.yml pull_request 3.12: ['Test (with a timing report)']
ci.yml push 3.12: ['Test (with a timing report)', 'Test (small tier, single process)']
$ uv pip compile pyproject.toml --extra dev -o requirements.lock -q; git diff --stat requirements.lock
 requirements.lock | 3 +++      (pytest-timeout==2.4.0 and its `via` line; nothing else moved)
$ the 12 named ci.yml guards + this round's four + this file + newest-python, -n 2
301 passed in 20.64s
$ the lock/pyproject readers + tier-map readers (8 files), -n 2
390 passed in 32.79s
```

`pytest-timeout==2.4.0` (latest on the index) joins `dev`; `timeout = 300`,
`timeout_method = "signal"` in `[tool.pytest.ini_options]`. The backstop step
is deleted; the single-process step is `if: github.event_name == 'push'` and
keeps `timeout 900`. `tests/tiers.py` retires `SMALL_TIER_BACKSTOP_S`,
`SMALL_TIER_CI_SLOW_S` and `SMALL_TIER_CI_FAST_S` (the parallel step's third
figure, read by nothing). `test_the_tiers_are_a_partition.py` loses the
parallel pair; its two-lines clause becomes `test_the_small_tier_runs_once_in_the_workflow`.
`test_a_pull_request_runs_the_newest_python_only.py` names the single-process
step in `PUSH_ONLY_STEPS`. `test (3.12)`'s wall on three PR runs is not read:
nothing is pushed from a track.

### Mutations verified red and reverted (7)

| # | mutation | reddened |
|---|---|---|
| A | remove `timeout = 300` from pyproject | 1 failed: `test_the_suite_declares_a_per_test_ceiling` |
| B | `-p no:timeout` in the guard's subprocess | 1 failed: the sleeper ran to the 20 s harness limit |
| C | the sleeper sleeps 0 s | 1 failed: returncode 0, no `Timeout` |
| D | a `timeout 300 make test-small` step restored in ci.yml | 1 failed: `test_the_small_tier_runs_once_in_the_workflow` |
| E | single-process step `if: always()` | 1 failed: `test_the_single_process_small_tier_runs_on_push_only` |
| F | single-process step's `if:` dropped | 1 failed: the same |
| G | single-process step `if: github.event_name == 'pull_request'` | 1 failed: the same |

Restored from a copy: 2 passed. Mutations A-C on this file, D on the tiers guard.
E survived the first draft (verifier: 23 passed) - `PUSH_ONLY_STEPS` exempts the
step by name; the push-only clause was added to
`test_a_pull_request_runs_the_newest_python_only.py` (5 passed).

**Deviation:** `SMALL_TIER_CI_FAST_S` retired beside the two the Decision
named; it described the deleted step and nothing read it.
