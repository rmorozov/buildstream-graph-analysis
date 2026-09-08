# UX-786: the flake ledger's adopt is never run against a non-empty ledger

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-691 | **Found by:** round 109, retro-verifying round 102 | **Serves:** the CI adopt run that already carries three real entries | **Topic:** guards | **Area:** tools | **Shape:** mechanical

## Motivation

`tools/dev_tier_drift.py` `_adopt_flake` promises append-not-replace:

```console
$ sed -i 's/document\["entries"\] = entries + added/document["entries"] = added/' tools/dev_tier_drift.py
$ python -m pytest tests/unit/test_the_flake_ledger_grows_from_the_drift_gate.py -q
7 passed
```

Neither `test_a_candidates_rows_are_appended` nor
`test_readopting_the_same_run_adds_nothing` starts from a ledger with
a row in it. Seeded with one and adopted against the mutation, the row
is gone. `tests/flake_ledger.json` has three entries, so the next
`flake-ledger-adopt` job runs the untested path on real data.

## Required Fix

Seed the fixture ledger in
`tests/unit/test_the_flake_ledger_grows_from_the_drift_gate.py` with
one pre-existing entry and assert it survives the adopt.

## Out of Scope

- `_adopt_flake`'s logic — it is right; the guard is what is missing.

## Acceptance Test

`tests/unit/test_the_flake_ledger_grows_from_the_drift_gate.py` reds under
the mutation `entries + added` → `added` in `_adopt_flake`; green restored.

## Outcome

### The gap, measured

Before: neither clause fixtured an existing row, so `entries + added`
and `added` were indistinguishable to the suite - the Motivation's
own repro:

```console
$ sed -i 's/document\["entries"\] = entries + added/document["entries"] = added/' tools/dev_tier_drift.py
$ python3 -m pytest tests/unit/test_the_flake_ledger_grows_from_the_drift_gate.py -q
7 passed
```

### The close, measured

Both `TestAdoptFlakeAppends` clauses now seed `ledger.json` with
`_EXISTING` (`FLAKY`, the same file the run below adopts, at
`run_id="run-0"`) before calling `--adopt-flake`, and assert it is
still present after:

```console
$ python3 -m pytest tests/unit/test_the_flake_ledger_grows_from_the_drift_gate.py -q
7 passed in 0.58s
```

### Mutation table

| # | mutation | reddened | count |
|---|---|---|---|
| M1 | `entries + added` → `added` in `_adopt_flake` | `test_a_candidates_rows_are_appended`, `test_readopting_the_same_run_adds_nothing` | `2 failed, 5 passed in 0.52s` |

Reverted from the scratchpad copy; `7 passed in 0.58s` restored.
