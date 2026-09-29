# UX-1110: the width calibration runs on every pull request and gates nothing

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** quality gates audit (`docs/audits/quality-gates-2026-09-29.md`, 2026-09-29) | **Serves:** the jobserver line, whose reading keeps its schedule while PRs stop paying for it | **Topic:** capture | **Area:** tools-native_trace | **Shape:** mechanical | **Reading:** runner:bst-examples

**Guard:** test_the_calibration_runs_off_the_pr_path.py

## Motivation

`bst-examples`' step "Calibrate the runner's width and run the pinned 2x2
arm (UX-1004)" (`ci.yml:1808`) is a median **1,332 s** of the job's 2,064 s
(the ledger's spread for the job, 620-964s, predates it) and emits `::notice::` lines and a compare file; nothing reads it as a gate.
It is the largest non-gating cost in the pipeline, paid on every PR.

## Decomposition

Input classes: a `pull_request` event with and without the `jobserver` label; a push to main; a schedule; a dispatch.
Journey: the jobserver reading on `bst-examples` (`UX-1004`).

## Decision

Architect, round 151 (2026-09-29):

```text
Route:     step `if: github.event_name != 'pull_request' || contains(github.event.pull_request.labels.*.name, 'jobserver')`; no new triggers (push to main already runs it); the session creates the `jobserver` label
Rejected:  `schedule`/`workflow_dispatch` on ci.yml (every job would run); a separate workflow (the step reads `$OUT/run-auto` from the step before); `labeled` in pull_request types (any label re-runs the pipeline)
Files:     .github/workflows/ci.yml; tests/unit/test_the_calibration_runs_off_the_pr_path.py
Guard:     evaluates the step's `if:` for a PR without the label (false), with it (true), and a push to main (true)
Mutation:  drop the `if:` - reddens
Class:     optimization - 1,332 s median per PR run of bst-examples (the job's recorded spread is 620-964s)
Split:     CI track. Keep the step name exactly (test_the_runners_width_is_calibrated.py:88-94 slices by it). A re-run reuses the old payload, so adding the label needs a fresh push
```

## Required Fix

The step runs on `workflow_dispatch`, on a weekly `schedule`, on push to
main, and on a pull request only when it carries a `jobserver` label. The
`::notice::` witness is unchanged where it runs.

## Out of Scope

What the calibration measures (`UX-1004`, `UX-1014`).

## Acceptance Test

`tests/unit/test_the_calibration_runs_off_the_pr_path.py` reads the step's
`if:` and asserts a plain `pull_request` event without the label does not
satisfy it and a push to main does. Mutation: drop the `if:`; it reddens.

## Outcome

### The gap, measured

```text
$ python3 -c "_holds(step.if, github) per event"   (base 438740ac)
A-ci-base.yml if=None {'pr': True, 'pr+jobserver': True, 'push': True}
```

### The close, measured

```text
$ same, on the branch
ci.yml if="github.event_name != 'pull_request' || contains(github.event.pull_request.labels.*.name, 'jobserver')" {'pr': False, 'pr+jobserver': True, 'push': True}
$ the 12 named ci.yml guards + UX-1108/1109's + this file + newest-python, -n 2
294 passed in 20.27s
```

The shared replay engine (`test_a_run_red_for_another_reason_adopts_nothing.py`)
learned `contains()` and the `.*` object filter to read the new `if:`; its own
7 tests stay green. The step name is unchanged (`test_the_runners_width_is_calibrated.py`
slices by it: green). The session creates the `jobserver` label; adding it to
an open PR needs a fresh push (`labeled` is not a trigger type).

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|---|---|
| A | drop the `if:` | 2 failed: `[pr-without-a-label]`, `[pr-with-another-label]` |
| B | drop the label clause (push-only) | 1 failed: `[pr-with-jobserver]` |
| C | engine: `contains()` always true | 2 failed: the two unlabelled PR cases |
| D | engine: `.*` yields an empty list | 1 failed: `[pr-with-jobserver]` |

Restored from a copy: 13 passed (this file + the width guard).

**Deviation (Decision over Required Fix):** no `schedule`/`workflow_dispatch`
on `ci.yml`; push to main already runs the step. Surface outside the Decision's
Files: the shared engine in `test_a_run_red_for_another_reason_adopts_nothing.py`.
