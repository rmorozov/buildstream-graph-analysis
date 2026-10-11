# UX-1346: four test sites call `zip(strict=True)`, which Python 3.9 does not have

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-1340 | **Found by:** main's first 3.9 run after UX-1340, run 37739145637 on `685b5164` (2026-10-08) | **Serves:** R8 | **Topic:** guards | **Area:** tests | **Shape:** judgement | **Reading:** container

**Guard:** none — the 3.9 cell on push to `main` is the reader, as for `UX-1340`; `UX-1343` brings it to the pull request

## Motivation

With the dev extra installable again (`UX-1340`), main's `test (3.9)` ran
12,796 tests and reded on 1 failure and 26 setup errors, all one cause:

```text
FAILURE tests.unit.test_the_synthetic_workload_runs_hundreds_of_binaries::test_the_workload_moves_plane2_alone
        TypeError: zip() takes no keyword arguments
```

`zip(..., strict=True)` is 3.10+. Four sites, all under `tests/unit/`,
landed while the 3.9 cell could not install (2026-09-29..10-07).

## Required Fix

Each site asserts the lengths match, then zips without `strict`.

## Out of Scope

Dropping Python 3.9 (an owner's call, asked 2026-10-03).

## Acceptance Test

The three files pass under a 3.9 interpreter.

## Outcome (round 172, 2026-10-08) — 🟢 Done

**Premise:** held.

### The gap, measured

```text
$ v39/bin/python -m pytest -q -p no:xdist tests/unit/test_back_after_a_reveal_re_folds.py \
    tests/unit/test_the_synthetic_workload_runs_hundreds_of_binaries.py      # on 685b5164
1 failed, 6 passed, 7 errors
```

### After

```text
$ v39/bin/python -m pytest -q -p no:xdist tests/unit/test_filter_and_back_state_is_kept_and_told.py \
    tests/unit/test_back_after_a_reveal_re_folds.py
26 passed
$ v39/bin/python -m pytest -q -p no:xdist tests/unit/test_the_synthetic_workload_runs_hundreds_of_binaries.py
7 passed
```

`grep -rn 'zip(.*strict=' bga tools tests .claude/hooks` finds none.

### Mutations verified red and reverted (1)

| # | mutation | reddened |
|---|---|---|
| A1 | the four sites back to `strict=True` (the `685b5164` tree), under 3.9 | 1 failed, 7 errors in two of the files |

Deviation: no `tests/unit` guard; nothing below 3.10 runs on a pull request (`UX-1343`).
