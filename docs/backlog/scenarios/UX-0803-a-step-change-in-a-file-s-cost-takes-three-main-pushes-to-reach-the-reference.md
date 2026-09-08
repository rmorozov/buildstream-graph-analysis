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

_Not started._
