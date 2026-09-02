# UX-513: two guards are red while a tier edit is uncommitted

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** `UX-476` wrote `explained_by`; `UX-336` put `tiers.py` in the shared-harness list | **Found by:** round 75, refreshing a reference entry CI had just reported | **Serves:** the round re-tiering a file, which is the one time these two guards are red for no reason of its own | **Topic:** guards

## Motivation

`explained_by(base)` answers "is there anything in this branch's diff
that could account for this file costing more?" by running
`dev_touching.select` over `git diff HEAD`. When `tests/tiers.py` is in
that diff, `select` returns the **whole suite** under the reason `"*"`,
and `explained_by` correctly refuses: a set naming every file explains
every excursion. It returns `None`.

Two guards assert the non-`None` shape on the tree they are run in:

```console
$ git status --short
 M tests/tiers.py

$ python3 -m pytest tests/unit/test_a_slow_file_says_which_file.py \
    -q -k "does_not_resolve or unexplained_message"
E   AssertionError: assert False
E    +  where False = isinstance(None, set)
2 failed, 120 deselected in 0.21s

$ git stash push -q tests/tiers.py && python3 -m pytest ... same clause
2 passed, 120 deselected in 0.40s
```

So the verdict depends on whether the edit is committed yet, and the
moment it is uncommitted is exactly the moment a round is re-tiering a
file — `tiers.py` is the file you edit to do that. Round 75 hit it
while refreshing the entry CI had just reported for
`test_a_guard_reads_only_what_a_clone_has.py`.

`UX-512` is the same shape one directory over: a guard whose answer
depends on the state of the working tree rather than on the code.
Neither is a product defect; both cost a round the time to prove the
red is not theirs.

## Required Fix

- The two clauses stand on a diff they control — a fixture repository,
  or a `base` they construct — rather than on whatever the developer
  has uncommitted.
- `explained_by`'s `"*"` refusal is **not** what changes: it is right,
  and `UX-476`'s Outcome has the run that proves it.
- Whatever it becomes, editing `tests/tiers.py` and running the file
  must be green, and a mutation removing the `"*"` refusal must still
  redden the clause that exists to hold it.

## Out of Scope

- `UX-512`, the `__pycache__` exemption. Same family, different file,
  and folding them would make one row that closes on two measurements
  neither of which is the other's.
- `dev_touching`'s shared-harness fallback. It is right for the
  question it was built for — which tests to *run*, where missing one is
  the only real failure — and `UX-336` sized it against that.

## Acceptance Test

The file green with `tests/tiers.py` edited and uncommitted, and green
with it clean, both pasted.

## Outcome

_Not started._
