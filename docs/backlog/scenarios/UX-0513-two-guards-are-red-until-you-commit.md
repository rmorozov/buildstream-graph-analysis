# UX-513: two guards are red while a tier edit is uncommitted

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** `UX-476` wrote `explained_by`; `UX-336` put `tiers.py` in the shared-harness list | **Found by:** round 75, refreshing a reference entry CI had just reported | **Serves:** the round re-tiering a file, which is the one time these two guards are red for no reason of its own | **Topic:** guards

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

## Outcome (round 76, 2026-09-02)

### The gap, reproduced at this round's HEAD

```console
$ printf '\n# an uncommitted tier edit.\n' >> tests/tiers.py
$ git status --short
 M tests/tiers.py
$ PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
    tests/unit/test_a_slow_file_says_which_file.py -q -p no:cacheprovider \
    -k "does_not_resolve or unexplained_message"
FAILED ...::test_a_base_that_does_not_resolve_is_no_evidence_at_all
FAILED ...::test_the_unexplained_message_prints
2 failed, 123 deselected in 0.59s
```

### The close

Both clauses called `explained_by("HEAD")` and took their answer from
`git diff HEAD` in this checkout. `_pin_the_diff` replaces
`dev_touching.changed_files` with a fixed list, so each clause names the
diff its claim is about: a one-module diff for "this resolves to a set",
an empty one for "an empty diff is an empty set, not `None`".

`TestTheVerdictDoesNotDependOnTheWorkingTree` states the three input
classes side by side — a one-module diff, an empty diff, and
`tests/tiers.py` — with a fourth clause asserting the three answers are
distinct, so a change collapsing them cannot pass quietly.

```console
$ git status --short tests/tiers.py            # clean
$ python3 -m pytest tests/unit/test_a_slow_file_says_which_file.py -q -p no:cacheprovider
129 passed in 2.09s

$ printf '\n# an uncommitted tier edit.\n' >> tests/tiers.py
$ git status --short tests/tiers.py
 M tests/tiers.py
$ PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
    tests/unit/test_a_slow_file_says_which_file.py -q -p no:cacheprovider
129 passed in 1.99s
```

### Mutations

| # | mutation | result |
|---|---|---|
| M1 | the `"*"` refusal removed — `UX-494` back | 2 failed |
| M2 | an unresolvable base reads as an empty diff | 1 failed |
| M3 | `explained_by` always answers `None` | 5 failed |
| M4 | an empty diff answers `None` instead of `set()` | 3 failed |

M1 is the one the Required Fix asked for by name: the refusal is right
and the clause holding it still reddens when it goes.

### Deviation from the Required Fix

None. `explained_by`'s `"*"` refusal is untouched — the change is
entirely in what the clauses feed it. A fixture repository was the other
option and was not built: `dev_touching.changed_files` is the one seam
both clauses go through, and pinning it is smaller than a second
checkout per clause.

Tests: 125 → 129 in `tests/unit/test_a_slow_file_says_which_file.py`.
