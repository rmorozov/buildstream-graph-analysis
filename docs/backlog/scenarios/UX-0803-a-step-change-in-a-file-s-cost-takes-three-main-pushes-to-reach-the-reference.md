# UX-803: a step change in a file's cost takes three main pushes to reach the reference

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-496 (the samples), UX-503 (the adopt job), UX-442 (the two-run confirmation) | **Found by:** round 110, PR #218's three CI runs | **Serves:** R8 reading a red drift gate on a PR whose diff touched a file main had already made slower | **Topic:** guards | **Area:** tools | **Shape:** bounded

## Motivation

```console
$ # PR #218, test (3.11), the drift gate's line on three runs of two heads
run 1  4 file(s) slower ... test_the_baseline_only_shrinks.py 50.7s against 2.4s recorded, x23.15 ...
run 2  1 file(s) slower ... test_the_page_has_a_volume_budget.py 93.2s against 41.8s recorded, x2.04
rerun  4 file(s) slower ... test_a_run_is_priced.py 6.7s against 0.1s recorded, x43.93 ...
$ git log --format='%h %ad %s' --date=format:%H:%M -1 -- tests/ci_reference.json
d82cc9c1 06:18 CI: adopt the tier rows this run measured (UX-503)
$ git log origin/main --format='%h %ad %s' --date=format:%H:%M -1
c13297cf 13:54 Merge pull request #215 ...
$ python3 -c "import json;d=json.load(open('tests/ci_reference.json'));print(d['samples']['tests/unit/test_the_baseline_only_shrinks.py'])"
[2.41, 2.39, 2.41, 2.41]
```

`adopt` appends one reading per push to main and `files` is the median
of the last five (`UX-496`), so a file whose cost stepped — pyright in
`dev_baseline.py --check` (`UX-697`), a hundred parametrized rounds in
`test_a_run_is_priced.py` — keeps its old median until three main
pushes have carried the new cost. In between, any PR whose diff the
tool can blame for the file reds the gate, twice confirmed, and the
documented refresh (the `ci-reference-candidate` artifact) is the same
`adopt` result: one more reading, the median unmoved. Round 110 paid
this on eight rows, refreshed by hand from the drift line's own
numbers.

## Required Fix

`tools/dev_tier_drift.py --against` treats a file whose reading sits
past the gate on the base branch's own last run as the base's, not the
branch's: the carry (`UX-442`) records main's excursions too, and a
file main already reads slow is reported, not failed. And `--adopt`
takes a reading that is past `CI_DRIFT_SECONDS` and the ratio on two
consecutive main runs as a step: the samples restart at that reading,
stated in `adopted`.

## Out of Scope

- The pyright cost itself — `UX-802`.
- Refreshing rows by hand — the eight in round 110 stand as the record
  of what the lag cost.

## Acceptance Test

A reference whose row for a file is 2.4 s, a base run reading 50 s
and a branch run reading 50 s: `--against` reports the file as the
base's and exits 0; mutation: the base-run clause dropped — red,
naming the file as the branch's.

## Outcome

**Gap measured.** Before this fix, a single-run reading past both gates
was auto-confirmed and failed the build whenever no branch `--carry`
existed yet - including the case where the base branch's own last run
already read the same file the same way:

```console
$ # reference row 2.4s, base carry names the file, branch run 50.0s, no --carry
1 file(s) slower than CI's own record of them:
  .../test_a_slow_file_says_which_file.py  50.0s  against 2.4s recorded, x20.83 ...
exit 1
```

`adopt` took three consecutive main pushes to move a stepped file's
median (Motivation's own `test_the_baseline_only_shrinks.py`, 2.4s to
50.7s): push 1 appends into the five-wide window, push 2 still loses
the `median_low`, push 3 finally outnumbers the old readings.

**Close measured.** `--base-carry` (workflow: `tier-carry-refs/heads/
<default>-` restore-keys, main's own key already saved by the existing
per-branch save step) splits a row the base's own last run also read
past both gates into `based`, reported and not failed:

```console
$ # same case, --base-carry given
1 file(s) over both gates that the base branch's own last run also
read past them - the base's, not this branch's (UX-803):
  .../test_a_slow_file_says_which_file.py  50.0s  against 2.4s recorded, x20.83 ...
tiers ok: 182 file(s) measured against ref.json ...
exit 0
```

`adopt` now restarts a file's samples at the new reading once two
consecutive main runs clear `over_gate` (`CI_DRIFT_FACTOR` and
`CI_DRIFT_SECONDS`, shared with `against`'s own row check): push 1
still only appends (median stays 2.41, matching the old lag), push 2 -
agreeing with push 1's own contributed reading - restarts the window
to `[50.0]`, median 50.0, name in `adopted`. Two pushes, not three.

**Mutation table.**

| Guard | Mutation | Reddened | Count |
|---|---|---|---|
| `TestABaseExcursionIsReportedNotFailed` (2 of 3 tests) | base-run clause dropped (`based = []`, split removed) | file named among "slower than CI's own record" (branch's), exit 1 | 2 failed, 1 passed, 142 deselected |
| `TestAStepRestartsTheSamples` (2 of 2 tests) | `_next_sample` step check reduced to one reading (`prior` requirement dropped) | first push alone restarts to `[50.0]`, both tests' sample-list assertions wrong | 2 failed, 143 deselected |
| `TestCiSuppliesTheMemoryTheRuleNeeds::test_a_branch_reads_its_own_series` (pre-existing, exemption re-checked) | own-branch carry key's `github.ref` dropped (unrelated to the new exemption) | `does not name the branch` | 1 failed, 144 deselected |

All three reverted from the scratchpad's pre-mutation copy, `__pycache__`
cleared each time; `tests/unit/test_a_slow_file_says_which_file.py`
back to 145 passed after each revert.
