# UX-691: a flake ledger, so an excursion is counted before it is a flake

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-442 (two-run confirmation), UX-495 (browser guards under load), UX-496 | **Serves:** the round reading a red gate on a file nobody touched | **Topic:** guards | **Area:** unassigned | **Shape:** bounded

## Motivation

```text
grep -in "flake\|excursion" tests/ tools/     39 hits, in code and comments
a ledger file                                 none (docs/audits/round-8*.md, round-9*.md: 0 hits)
```

The drift gate confirms over two runs and the browser family was
measured over six CI runs (`UX-495`), and the outcome of each
excursion lives in whichever task file happened to record it. A
file that excurses monthly and a file that excursed once look the
same to the next round.

## Required Fix

`tests/flake_ledger.json`, appended by the drift gate's CI step for
every unconfirmed excursion and every confirmed drift (file, run id,
shift, confirmed?), adopted like the tier reference; a guard that a
file with ≥ 3 excursions in the ledger has a filed robustness task or
a declared reason; the round document's Standing prints the ledger's
top three.

## Out of Scope

- Re-running to make a file quiet — the ledger counts; the task
  fixes.

## Acceptance Test

Two synthetic excursions of one file in the ledger and a third —
the guard names the file; mutation: drop the adopt step — the
ledger stops growing and the census guard reds.

## Outcome

**Gap measured**: `grep -in "flake\|excursion" tests/ tools/` — 39
hits, none of them a ledger file; `docs/audits/round-8*.md` and
`round-9*.md` — 0 hits, confirming the Motivation's count.

**Close measured**: `tests/flake_ledger.json` (`entries`, `declared`),
adopted the way `tests/ci_reference.json` is: `dev_tier_drift.py
--against --flake-ledger PATH --run-id ID` writes a per-run candidate
of `{file, run_id, shift, confirmed}` rows from the `waiting` (one run
only) and `confirmed` (agreed + a cause, `UX-476`) buckets `repeated()`
already computes — not `unexplained` or `recorded`, neither of which is
an excursion against the file's own record. `--adopt-flake CANDIDATE`
appends rows a `(file, run_id)` key does not already carry, run by a
new `flake-ledger-adopt` job (push-to-default-branch only, same shape
as `tier-reference-adopt`). `tools/dev_flake_census.py` names every
file at or past 3 ledger entries with neither a filed
`docs/backlog/scenarios/*.md` row nor a `declared` reason;
`test_a_file_with_three_excursions_has_a_filed_task.py` is the
Acceptance Test's own case (two excursions clear, a third names the
file, a filed task or a declared reason clears it again).
`test_the_flake_ledger_grows_from_the_drift_gate.py` drives the real
`--against` path (`UX-442`'s own fixture: one file over both gates
twice, a run apart) and asserts the candidate is `waiting` then
`confirmed`, and that `--adopt-flake` is idempotent per run id — the
Acceptance Test's "drop the adopt step" mutation, standing for a run
that never reaches `--adopt-flake` or reaches it twice, leaving the
ledger where it was.

**Mutation table**:

| guard file | mutation | reddened | reverted |
|---|---|---|---|
| `test_a_file_with_three_excursions_has_a_filed_task.py` | `EXCURSION_FLOOR = 3` → `30` | 2 of 6 (`test_a_third_excursion_names_the_file`, `test_only_the_named_file_is_cleared`) | 6/6 green |
| `test_the_flake_ledger_grows_from_the_drift_gate.py` | `ledger_rows`: `waiting` rows marked `True` instead of `False` | 2 of 7 (`test_a_first_excursion_is_waiting_not_confirmed`, `test_ledger_rows_splits_waiting_from_confirmed`) | 7/7 green |
| `test_the_flake_ledger_grows_from_the_drift_gate.py` | `_adopt_flake`: `seen = set()` (dedup removed) | 1 of 7 (`test_readopting_the_same_run_adds_nothing`) | 7/7 green |

`make test-touching`: `49 file(s) selected (13 census + 36 naming the
change) · 1307 passed, 3 skipped in 52.29s`. `make lint`: ruff and
PyMarkdown both clean; `dev_baseline.py --check` clean (299 findings,
unchanged).

**Deviation**: the round document's Standing section was not written —
no `docs/audits/round-N.md` exists in this worktree for the round this
batch belongs to (rounds 96-100 landed with no such file; every prior
`round-N.md` was committed by the orchestrating session, never a
track). `tools/dev_flake_census.py`'s top-three output is what the
Standing section should paste; left for the session's merge.
