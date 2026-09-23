# UX-943: the adopt jobs write to the default branch from a run whose whole suite failed

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-503, UX-524, UX-691, UX-934 | **Blocks:** — | **Found by:** round 136 — the merge thread reading `98c387bc`'s checks while `UX-934` was worked | **Serves:** every branch that inherits a record the default branch adopted from a run nothing vouched for | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

All three adopt jobs are `needs: test` with `if: always() && ...`, and
`always()` overrides the `needs`. So the jobs that write to `main` run
after every test cell failed:

```text
$ GET /repos/.../commits/98c387bc.../check-runs     # UX-925 (#266)
test (3.9) failure   test (3.10) failure   test (3.11) failure   test (3.12) failure
bst-smoke skipped    bst-tests skipped     bst-examples skipped
tier-reference-adopt success   touch-map-adopt success   flake-ledger-adopt success
```

The adopt it produced, `461c9c6b` (zero check runs), took
`tests/ci_reference.json` from 569 to 579 entries and moved 102 of them,
among them `test_the_toolchain_parameters_are_read_back.py` from 3.15 s
to 46.28 s — a reading from a suite that did not pass.

The `always()` is partly deliberate: the ledger's rows *are* the runs
the drift step reddened, and `tier-reference` prints its candidate on
exactly the failing run. What it does not distinguish is a run red on
timing from one red on anything else. `UX-934`'s check catches a record
its own guards reject; it cannot catch a reading that passes them.

`461c9c6b`'s 46.28 s is the honest median of a two-mode population
(`UX-944`: 0.10 s hardlinked, 14.63 s cold) and passes every guard on
the record: a gate on the record cannot see it, a gate on the run can.
`UX-944` offers one answer to which runs may adopt — a run whose
filesystem layout differs from the window's — and leaves it to this row.

## Required Fix

Each adopt job states which failures it adopts from, and a run red for
any other reason adopts nothing — say, per job, what the condition
reads (the drift step's own outcome, not the job's).

## Out of Scope

`UX-934`'s check, which runs either way. Whether 46 s is the intended
cost of `test_the_toolchain_parameters_are_read_back.py`.

## Acceptance Test

A run whose test cells fail on a non-timing assertion leaves all three
records unwritten; a run red only on the drift step still appends the
ledger; a mutation restoring the bare `always()` reddens.

## Outcome

**Round 138, 2026-09-23** — fixed; the row move waits on review 26 (`test_the_review_has_a_cadence.py`: 26 closed against a bound of 25).

**Premise:** held — every red run adopted all three records.

### The gap, measured

`test_a_run_red_for_another_reason_adopts_nothing.py` replays `ci.yml`:
each `test` cell's steps under their own `if:`, one step made red, the
cells' outputs merged in all 24 completion orders, each adopt job's
`if:` evaluated on the result.

```text
$ python3 -m pytest -q tests/unit/test_a_run_red_for_another_reason_adopts_nothing.py  # origin/main's ci.yml
FAILED ...::test_a_run_red_for_another_reason_adopts_nothing[every-suite]
FAILED ...::test_a_run_red_for_another_reason_adopts_nothing[one-suite]
FAILED ...::test_a_run_red_for_another_reason_adopts_nothing[drift-and-perf]
FAILED ...::test_a_run_red_for_another_reason_adopts_nothing[drift-and-3.12]
FAILED ...::test_a_run_red_only_at_the_drift_step_appends_the_ledger_alone
5 failed, 2 passed in 2.27s
```

### After

| job | adopts from | its `if:` reads |
|---|---|---|
| `tier-reference-adopt` | a green run | `needs.test.result == 'success'` |
| `touch-map-adopt` | a green run | the same |
| `flake-ledger-adopt` | a green run, or one red at the drift step alone | `needs.test.outputs.clean_<cell> == 'true'`, all four cells |

The drift step is `continue-on-error` with `id: drift`; a cell's last
success-gated step writes `clean_<cell>=true`, so it holds when every step
but the drift step passed; `The drift gate's red, raised` then fails the
job on `steps.drift.outcome == 'failure'`. One key per cell, written only
as `true`: the runner skips an empty output (`actions/runner`
`JobExtension.cs` L804, "Skip output ... since it's empty"), so the merge
is order-free, and a server that did overwrite would adopt nothing.

```text
$ python3 -m pytest -q tests/unit/test_a_run_red_for_another_reason_adopts_nothing.py
7 passed in 1.39s
$ python3 -m pytest -q -n 4 $(grep -l ci.yml tests/unit/*.py)   # every guard that reads ci.yml
736 passed in 156.51s (0:02:36)
```

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| A1 | the bare `always()` restored in all three `if:` | 5 of 7: every red-elsewhere case, the drift-only case |
| A2 | the drift step without `continue-on-error` | 1 of 7: drift-only no longer appends the ledger |
| A3 | the re-raise step removed | 1 of 7: drift-only run goes green, all three adopt |
| A4 | the ledger reads `clean_311` alone | 2 of 7: `one-suite`, `drift-and-3.12` |
| A5 | origin/main's `ci.yml` whole (the gap above) | 5 of 7 |

### Deviation from the Required Fix

The ledger reads the drift step's outcome by excusing it: `continue-on-error`
makes the cell verdict "every other step", and the re-raise keeps the run
red. Side effects on a drift-red `test (3.11)`: the perf-carry restore and
the single-process small tier now run (both were skipped), and the job
goes red at the re-raise step, not the gate's own. A red from the analyzer
gate is "another reason": nothing adopts. New-file rows wait for the next
green run on `main` rather than a drift-red one.

```text
$ make lint
clean: 573 finding(s) match tests/quality_baseline.json
```
