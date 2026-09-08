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

Gap measured (pre-fix, widened guard reverted to the old regex - both mutations pass through it silently):

```console
$ sed -i 's/perf-carry-\${{ github.ref }}-/perf-carry-global-/' .github/workflows/ci.yml
$ python -m pytest tests/unit/test_the_analyzer_gate_needs_two_runs_and_a_cause.py \
    tests/unit/test_a_slow_file_says_which_file.py -q
162 passed
```

Close measured (post-fix, `test_a_branch_reads_its_own_series` widened; both mutations red, restore green):

```console
$ sed -i 's/perf-carry-\${{ github.ref }}-/perf-carry-global-/' .github/workflows/ci.yml
$ python3 -m pytest tests/unit/test_a_slow_file_says_which_file.py::TestCiSuppliesTheMemoryTheRuleNeeds::test_a_branch_reads_its_own_series -q
FAILED ... the carry cache key 'perf-carry-global-${{ github.run_id }}' does not name the branch
$ git checkout -- .github/workflows/ci.yml   # restore
$ sed -i "337s/.*/        if: matrix.python-version == '3.11'/" .github/workflows/ci.yml
$ python3 -m pytest tests/unit/test_a_slow_file_says_which_file.py::TestCiSuppliesTheMemoryTheRuleNeeds::test_a_branch_reads_its_own_series -q
FAILED ... 'perf-carry-''s save step does not run under always(), so a red run's carry ... is never saved
$ git checkout -- .github/workflows/ci.yml   # restore
$ python3 -m pytest tests/unit/test_a_slow_file_says_which_file.py -q
140 passed in 11.26s
```

`.github/workflows/ci.yml` was found not lacking: the perf-carry save step
(line 337) already runs under `if: always() && matrix.python-version ==
'3.11'` and its key already carries `${{ github.ref }}` (lines 280, 336).
No workflow change made - only the guard was widened.

Verifier (`5873229d`) found a blind spot: the regex read only a same-line
`key: value`, so a key written `key: >-` with the value folded onto the
next line passed unseen. Reread with `yaml.safe_load` (importable:
`python3 -c "import yaml"` exits 0) walking every job's `uses:
actions/cache*` step for its own `with.key`/`if`, so a step is judged by
its own pair rather than by text proximity.

```console
$ python3 - <<'PY'   # key: >- \n  perf-carry-global-${{ github.run_id }}
...   (folds the perf-carry save step's key, dropping github.ref)
PY
$ python3 -m pytest tests/unit/test_a_slow_file_says_which_file.py::TestCiSuppliesTheMemoryTheRuleNeeds::test_a_branch_reads_its_own_series -q
FAILED ... the carry cache key 'perf-carry-global-${{ github.run_id }}' does not name the branch
$ git checkout -- .github/workflows/ci.yml   # restore
$ python3 -m pytest tests/unit/test_a_slow_file_says_which_file.py -q
140 passed
```

Mutation table:

| mutation | reddened | count |
|---|---|---|
| strip `github.ref` from the perf-carry key | `test_a_branch_reads_its_own_series`, naming `perf-carry-` | 1 failed / 140 |
| restore | — | 140 passed |
| drop `always()` from the perf-carry save step | `test_a_branch_reads_its_own_series`, naming `perf-carry-` | 1 failed / 140 |
| restore | — | 140 passed |
| fold the perf-carry save key onto a `key: >-` continuation line, dropping `github.ref` | `test_a_branch_reads_its_own_series`, naming the folded key | 1 failed / 140 |
| restore | — | 140 passed |
