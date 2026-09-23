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
