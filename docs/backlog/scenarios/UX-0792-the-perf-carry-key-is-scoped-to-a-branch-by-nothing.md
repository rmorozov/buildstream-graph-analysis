# UX-792: the perf-carry key is scoped to a branch by nothing

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-702 (the ratchet), UX-442 (the tier-carry guard this copies) | **Found by:** round 109, retro-verifying round 102 | **Serves:** the branch whose analyzer regression is confirmed by another branch's run | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

`UX-702`'s "two consecutive runs" means two runs on one branch only
because the cache key is `perf-carry-${{ github.ref }}-...`.
`tests/unit/test_a_slow_file_says_which_file.py::test_a_branch_reads_its_own_series`
holds that property for the tier carry — with the regex
`key: (tier-carry-.*)`, which cannot see this one:

```console
$ sed -i 's/perf-carry-\${{ github.ref }}-/perf-carry-global-/' .github/workflows/ci.yml
$ python -m pytest tests/unit/test_the_analyzer_gate_needs_two_runs_and_a_cause.py \
    tests/unit/test_a_slow_file_says_which_file.py -q
162 passed
```

Dropping `always()` from the carry's save step — a red run's carry
never saved — is the same silence. `UX-702` copied the mechanism and
not its guard.

## Required Fix

Widen `test_a_branch_reads_its_own_series` in
`tests/unit/test_a_slow_file_says_which_file.py` to every `*-carry-` key
in `.github/workflows/ci.yml`: each carries `github.ref`, and each save
step runs under `always()`.

## Out of Scope

- The ratchet's margins — `UX-702` set them from one orientation reading
  and its Outcome says a later round re-reads them.

## Acceptance Test

`tests/unit/test_a_slow_file_says_which_file.py` reds under both mutations
above, naming the key; green restored.

## Outcome

_Not started._
