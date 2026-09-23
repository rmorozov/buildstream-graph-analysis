# UX-995: a pull request runs the suite on the newest Python only; main keeps the matrix

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-956 | **Blocks:** — | **Found by:** round 139 — Ruslan in the project thread, 2026-09-23 14:44, answering the workflow review ([doc](https://claude.ai/code/artifact/7f65768e-b4bb-405a-b3e1-90a672a249f5)) | **Serves:** every pull request waiting in the queue behind another's matrix | **Topic:** guards | **Area:** unassigned | **Shape:** mechanical

## Motivation

On 10 sampled runs the four `test` cells are 68.5% of CI's job-seconds
and the two real-bst jobs 25.8%. A public repository's minutes are free;
the cost is latency when several pull requests queue at once. The owner
chose the newest Python for pull requests on 2026-09-23 14:44.

## Required Fix

On `pull_request`, the `test` job runs the newest Python in the matrix
only; on a push to the default branch it runs all four. Every step a
pull request needs from a cell it no longer gets moves to the cell it
keeps.

## Out of Scope

The docs lane (`UX-956`), the bst jobs, the Quality workflow.

## Acceptance Test

A guard reads `ci.yml` and fails when a pull-request step is bound to a
cell pull requests no longer run, or when a push runs fewer than four.

## Decision

The `architect`'s first run, round 139 (`UX-993`), at `0b9b72cd`.

```text
Route:     the PR matrix is 3.12 alone through an expression
           (fromJSON(event == 'pull_request' && '["3.12"]' || '["3.9","3.10","3.11","3.12"]'));
           the timing role (drift gate, base/branch carries, perf gate, both candidates,
           --source derived from matrix.python-version) moves 3.11 -> 3.12 on both events;
           coverage + touch map move 3.12 -> 3.11, push only (their one reader is touch-map-adopt);
           tests/ci_reference.json re-recorded whole from the PR's own 3.12 candidate
Rejected:  PR keeps 3.11 - contradicts the owner's call
           3.12 gated against a 3.11 reference - the perf ratchet's margins are absolute (5 s / 50 MB)
           timing and coverage both on 3.12 - coverage adds 20% to every row (UX-524)
           four PR cells with steps skipped - the queued runners are the latency this removes
           matrix include: roles - an include matching no PR cell adds a cell back
Files:     .github/workflows/ci.yml (test job; the "test (3.11)" names in the four downstream jobs);
           tests/ci_reference.json; five guards that read the cells (below); the new guard
           tests/unit/test_a_pull_request_runs_the_newest_python_only.py; the prose
           "CI's full matrix gates the merge" (CLAUDE.md, rules.md, fixing guide, verify, decompose)
Guard:     push matrix == pyproject's classifiers; PR matrix == the newest of them; exactly one
           `make test` step holds per (event, cell); every step that holds on some PR cell holds
           on (pull_request, newest) unless its `if` needs a push
Mutation:  rebind "Tiers match CI's own record of them" to == '3.11'; drop one version from the
           push branch - each reddens it
Class:     process
Split:     A: ci.yml, five guard edits, new guard, prose. B, serial after A's first push: the PR
           run's tier-reference log re-records ci_reference.json into A's commit
Question:  none - a 3.9-3.11-only break is now first seen on main, which the owner's call accepts
```

The five guards that read the cells: `test_a_run_red_for_another_reason_adopts_nothing.py`,
`test_a_slow_file_says_which_file.py`, `test_the_analyzer_gate_needs_two_runs_and_a_cause.py`,
`test_the_touching_map_is_measured.py`, `test_the_floor_is_stated_where_it_is_read.py`.
`#284` edits `ci.yml` only above line 72, so no hunk overlaps.

## Outcome

### The gap, measured

Before: `python-version: ["3.9", "3.10", "3.11", "3.12"]`, one literal
list read for both `push` and `pull_request` - every queued PR ran all
four `test` cells, measured at 68.5% of a run's job-seconds (Motivation).
Two of the five guards that read the cells could not have run at all
after the route landed without their own fix: `_jobs()["test"]["strategy"]
["matrix"]["python-version"]` returned the literal four-item list they
iterated directly, which a `${{ fromJSON(...) }}` expression string
would turn into 66 one-character "cells" and an `itertools.permutations`
over them - reproduced live, killed after 120s with 0 of 7 tests
collected-and-run.

### The close, measured

```text
$ python3 -m pytest -q -n 4 $(grep -l ci.yml tests/unit/*.py)
810 passed
$ python3 -m pytest -q tests/unit/test_a_pull_request_runs_the_newest_python_only.py
4 passed
$ python3 tools/dev_touching.py --base 49a29a29 --loud
2691 passed, 5 skipped
$ make lint
clean: 575 finding(s) match tests/quality_baseline.json; ... (unchanged forced counts)
```

`push` matrix now evaluates (via the replay harness's own `fromJSON`)
to `['3.9', '3.10', '3.11', '3.12']`, equal to `pyproject.toml`'s four
classifiers; `pull_request` to `['3.12']` alone. The timing role (drift
gate, both carries, the base diff, the perf gate and its own carry, both
candidate uploads, `--source`) now reads `matrix.python-version == '3.12'`
throughout, `--source` itself now `test (${{ matrix.python-version }})`
rather than typed. Coverage and the touching map now read
`matrix.python-version == '3.11' && github.event_name == 'push'`.

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| M1 | rebind "Tiers match CI's own record of them" to `== '3.11'` | `test_every_pull_request_step_moves_to_the_cell_it_keeps` (new guard) and `test_a_run_red_only_at_the_drift_step_appends_the_ledger_alone` (pre-existing) |
| M2 | drop `"3.10"` from the push branch's list | `test_the_push_matrix_equals_pyprojects_classifiers` (new guard) alone |
| M3 | append `&& github.event_name == 'push'` to the 3.12 perf-carry restore (ci.yml:412), a step outside `PUSH_ONLY_STEPS` | `test_every_pull_request_step_moves_to_the_cell_it_keeps` (new guard) |

M3 is the round-139 verifier's hold: the clause's first draft exempted
any step whose `if:` contained the substring `event_name == 'push'`,
so this same mutation stayed green. Fixed by exempting only the three
named `PUSH_ONLY_STEPS` and computing "needed by a pull request" off
the real **push** matrix (not a hypothetical pull-request context,
which a genuine push-only condition also fails under - the mutation
and the legitimate case are indistinguishable there).

All three reverted from the pre-mutation copy and confirmed green
(`810 passed`) before commit.
