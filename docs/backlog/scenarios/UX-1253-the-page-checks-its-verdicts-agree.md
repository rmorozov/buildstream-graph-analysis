# UX-1253: five sections each publish a bound, and nothing checks that they agree

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-162 view UI review on a 2,402-element two-plane page (2026-10-01), brainstorm B1, filed at Ruslan's request | **Serves:** R1, R4, R5 | **Topic:** analysis | **Area:** bga, bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_the_page_checks_its_verdicts_agree.py`

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `050d9035`, Chromium 1440x900 and 390x844 (view UI review, round 162, `view-ui-review/round-162/review.md` §B1).

The diagnosis says scheduler-bound, `#floors` says LB is the wall, `#capacity_recommendation` says CPU binds, `#utilisation` says oversubscribed and `#capacity_verdict` says capacity matched demand (UX-1244, UX-1245, UX-1246). Each is computed alone, and "What did not add up?" (`violations`) reads none. The page found its own contradictions only because a person read all five.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Decision

Architect, round 163 (2026-10-01):

```text
Route:     new bga/consistency.py: read_verdicts(result, headline) and pure disagreements(verdicts) over a PAIRS table; _add_violations (report/json.py:428) appends verdict_disagreement records at report time; text report and #violations show them. Pairs: diagnosis vs floors (lb/wall >= CAPACITY_BOUND_SHARE and lb > t∞, diagnosis not capacity_bound); potential_oversubscription vs capacity_verdict (checks_ran and not oversubscribed); binding CPU vs floors lb_cpu_binds False.
Rejected:  check inside the analyzer (headline/recommendation not yet built); own copy of 0.95.
Files:     bga/consistency.py; bga/findings.py (CAPACITY_BOUND_SHARE); bga/report/json.py; bga/report/text.py; bga/schemas.py; tests/unit/test_the_page_checks_its_verdicts_agree.py.
Guard:     stub verdict dicts, one disagreeing pair per parametrized case -> one violation naming both sides; golden and macro_micro yield none.
Mutation:  delete any PAIRS row.
Class:     product
Split:     Track A, before 1244. Before/after page reading measured in the track.
```

## Required Fix

`bga analyze` publishes a consistency check over the run's verdicts (diagnosis, binding floor, capacity binding constraint, oversubscription, capacity verdict) and reports a disagreement as a violation naming both sides; the page shows it in `#violations`.

## Out of Scope

Fixing the verdicts themselves (UX-1244..UX-1246); the check names a disagreement, it does not pick a winner.

## Acceptance Test

On this page before UX-1244..UX-1246 land, the check reports at least the diagnosis/LB and oversubscription/verdict disagreements; golden and macro_micro report none. Mutation: drop one pair from the check, and its guard reds.

## Outcome

The gap measured, at `92a48946`, the Motivation's page (`gen-synthetic --store --seed 1 --layers 40 --width 60
--workload binaries`, `capture report --json` into `20260303T091500Z`, `bga analyze @last --format json`):
`violations: []` beside `headline.diagnosis scheduler_bound`, `floors.lb 2817875000` of wall `2829756376` (99.6%),
`utilisation.potential_oversubscription true` with `capacity_verdict {oversubscribed: false, checks_ran: true}`,
`capacity_recommendation.binding_constraint "CPU"` with `floors.lb_cpu_binds false`.

The close measured, same page, `violations` (3, all `verdict_disagreement`):

```text
diagnosis_vs_floors                    headline.diagnosis reads scheduler_bound; floors.lb reads LB 99.6% of wall, at or above 95.0%
oversubscription_vs_capacity_verdict   utilisation.potential_oversubscription reads oversubscribed; capacity_verdict.oversubscribed reads not oversubscribed, checks ran
binding_constraint_vs_cpu_floor        capacity_recommendation.binding_constraint reads CPU binds; floors.lb_cpu_binds reads the CPU floor does not bind
```

Golden and macro_micro (`--plane2`): none (both `lb == t_infinity_observed`, `checks_ran: false`). Guard: 8 passed
(1.1 s); with the schema, register, key-findings, provenance, diagnosis and contract guards 1634 passed, 1 skipped.

| mutation | reddened | run printed |
|---|---|---|
| delete PAIRS row `diagnosis_vs_floors` | `test_every_pair_has_a_disagreeing_case`, `[diagnosis_vs_floors]` | 2 failed, 6 passed |
| delete PAIRS row `oversubscription_vs_capacity_verdict` | the two above for that row, `test_the_json_and_text_reports_publish_a_disagreement` | 3 failed, 5 passed |
| delete PAIRS row `binding_constraint_vs_cpu_floor` | `test_every_pair_has_a_disagreeing_case`, `[binding_constraint_vs_cpu_floor]` | 2 failed, 6 passed |
| drop `+ verdict_violations(...)` in `_add_violations` | `test_the_json_and_text_reports_publish_a_disagreement` | 1 failed, 7 passed |
| reverted | | 8 passed |

`test_the_committed_fixtures_report_none` does not discriminate under these mutations (fewer pairs report fewer
disagreements); it holds the Acceptance's "golden and macro_micro report none".

Verifier fix (after UX-1244 and UX-1246 merged): a fourth row, `capacity_bound_vs_recommendation`, flags a
capacity-bound diagnosis beside a recommendation that keeps builders (`builders_change == 0`) while its binding
row is not the `host_cores` cap. Silent cases added: capacity_bound beside LB at the wall, and beside a host-cap
keep. The page after the merge reports 0 disagreements. Guard: 11 passed.

| mutation | reddened | run printed |
|---|---|---|
| delete PAIRS row `capacity_bound_vs_recommendation` | `test_every_pair_has_a_disagreeing_case`, `[capacity_bound_vs_recommendation]` | 2 failed, 9 passed |
| drop `DIAGNOSIS_CAPACITY_BOUND` from the floors exclusion | `test_agreeing_sides_report_nothing[capacity_bound_beside_lb_at_the_wall]` | 1 failed, 10 passed |
| drop `'host_cores'` from the new row's exclusion | `test_agreeing_sides_report_nothing[capacity_bound_beside_a_host_cap_keep]` | 1 failed, 10 passed |
