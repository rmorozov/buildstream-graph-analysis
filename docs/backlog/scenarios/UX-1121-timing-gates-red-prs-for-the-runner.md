# UX-1121: timing gates red pull requests for the runner's speed

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** quality gates audit (`docs/audits/quality-gates-2026-09-29.md`, 2026-09-29); Ruslan took it on the audit thread (2026-09-29 06:09) | **Serves:** the implementing session, whose PR reds for a file it never touched | **Topic:** guards | **Area:** tools | **Shape:** mechanical | **Reading:** runner:test

**Guard:** test_a_timing_gate_reports_on_a_pr.py

## Motivation

Two steps of `test (3.12)` judge seconds, not behaviour: "Tiers match CI's
own record of them" (`ci.yml:308`) and "The analyzer's wall clock and RSS,
against CI's own record" (`ci.yml:467`). Over 400 runs the tier gate failed
14, with the adopt jobs another 15; project memory records reds on files the
branch never touched and green runs that are not evidence a cost went away.
A shared runner makes a timing verdict per PR a noise source.

## Decision

Architect, round 151 (2026-09-29):

```text
Route:     report on PRs only; push to main keeps its verdict (UX-943's adopt semantics). On PRs the raised drift step gets `&& github.event_name != 'pull_request'`, the perf step `continue-on-error: ${{ github.event_name == 'pull_request' }}`, and a PR-only step turns tier_gate.txt/perf_gate.txt into `::notice::` lines. New `.github/workflows/timing.yml` (daily cron on main + dispatch) runs `make test` with junit and the perf fixture on 3.12, then both tools with `--carry`; their UX-442 two-run carry is the two-run rule, from families of their own (`timing-tier-carry-`, `timing-perf-carry-`)
Rejected:  report-only on main (adopt jobs would adopt from a drift-red run); `schedule` on ci.yml; reading main's candidate artifacts (push cadence, not a same-sha repeat); new two-run code
Files:     .github/workflows/ci.yml; .github/workflows/timing.yml; tests/unit/test_a_timing_gate_reports_on_a_pr.py; tests/unit/test_a_run_red_for_another_reason_adopts_nothing.py (:175)
Guard:     replays both steps plus the raised step under pull_request (no failure) and push (red); timing.yml has a schedule and both tools with `--carry` from their own family
Mutation:  drop the `!= 'pull_request'`; point timing.yml's carry at `tier-carry-refs/heads/main-` - each reddens
Class:     optimization - the tier gate failed 14 of 400 runs; ~25 runner-min daily
Split:     CI track, last
```

## Required Fix

Both steps stop failing the PR: they report (a `::notice::` naming file and
ratio) and upload their candidate as today. A scheduled workflow on `main`
(daily) reads the carried readings and, when a file or the analyzer holds
over its gate on two consecutive scheduled runs, fails and names it for a
row. The PR keeps a per-test hang ceiling (`UX-1111`).

## Out of Scope

The gate's thresholds; the adopt jobs.

## Acceptance Test

`tests/unit/test_a_timing_gate_reports_on_a_pr.py` reads both steps and
asserts neither can fail a `pull_request` run, and that the scheduled
workflow runs both checks with a two-run rule. Mutation: restore the PR
failure; it reddens.

## Outcome

### The gap, measured

```text
$ python3 A-1121-gap.py <ci.yml>   (`_cell` replay of test (3.12), one gate step red)
A-ci-base.yml pull_request test (3.12) with the gate red: {'drift': 'failure', 'perf': 'failure'}
A-ci-base.yml push test (3.12) with the gate red: {'drift': 'failure', 'perf': 'failure'}
```

### The close, measured

```text
ci.yml pull_request test (3.12) with the gate red: {'drift': 'success', 'perf': 'success'}
ci.yml push test (3.12) with the gate red: {'drift': 'failure', 'perf': 'failure'}
$ the 12 named ci.yml guards + this round's five + this file + 9 workflow readers, -n 2
473 passed in 44.51s
```

On a PR the raised drift step gets `&& github.event_name != 'pull_request'`,
the perf step `continue-on-error: ${{ github.event_name == 'pull_request' }}`,
and a PR-only step prints each line of `tier_gate.txt`/`perf_gate.txt` as a
`::notice::`. New `.github/workflows/timing.yml` (cron `30 4 * * *` and
dispatch, 3.12): `make test` with junit, the perf fixture, then both tools
`--against --carry` with no `--base` (agreement alone), each carry cached under
`timing-tier-carry-`/`timing-perf-carry-`; both gate steps are
`continue-on-error` and a last step raises either. The shared engine's `_cell`
now evaluates an expression `continue-on-error` (`_continues`).

### Mutations verified red and reverted (8)

| # | mutation | reddened |
|---|---|---|
| A | drop the raised step's `!= 'pull_request'` | 2 failed: PR `[drift]`, `[both]` |
| B | drop the perf step's `continue-on-error` | 2 failed: PR `[perf]`, `[both]` |
| C | perf `continue-on-error: true` | 1 failed: push `[perf]` |
| D | notice step on `push` instead of PR | 1 failed: `test_a_pull_request_reports_both_gates_as_notices` |
| E | timing.yml tier carry -> `tier-carry-refs/heads/main-` | 1 failed: `[dev_tier_drift.py-timing-tier-carry-]` |
| F | timing.yml loses its `schedule` | 1 failed: `test_the_timing_workflow_runs_daily_and_on_demand` |
| G | timing.yml raised step `exit 0` | 2 failed: daily `[drift]`, `[perf]` |
| H | engine ignores an expression `continue-on-error` | 2 failed: PR `[perf]`, `[both]` |

Restored from a copy: 12 passed. timing.yml has not run: nothing is pushed from
a track, so its first two scheduled runs are unread.
