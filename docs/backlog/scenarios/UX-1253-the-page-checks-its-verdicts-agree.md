# UX-1253: five sections each publish a bound, and nothing checks that they agree

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-162 view UI review on a 2,402-element two-plane page (2026-10-01), brainstorm B1, filed at Ruslan's request | **Serves:** R1, R4, R5 | **Topic:** analysis | **Area:** bga, bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** none — open, no guard named yet

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
