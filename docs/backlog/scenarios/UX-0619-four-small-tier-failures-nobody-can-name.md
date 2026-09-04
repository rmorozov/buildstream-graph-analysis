# UX-619: four small-tier failures nobody can name

**Priority:** High | **Status:** 🔴 Open | **Depends on:** UX-618 (which would have named them), UX-418 (the backstop) | **Found by:** round 84, on three consecutive commits | **Serves:** every session whose PR goes red for no reason it can find | **Topic:** guards

## Motivation

Three consecutive pushes failed CI's small-tier backstop identically,
on all four interpreters, and the fourth passed with a change that
cannot affect any test outcome.

```text
097792a  4 failed, 4002 passed, 44 skipped   (3.9 and 3.11 read; 3.10, 3.12 same conclusion)
6febb53  failed, all four interpreters
069947a  failed, all four interpreters
4a24cb7  success — diff is .github/workflows/ci.yml, Makefile, one task file
```

`4a24cb7` adds `--junitxml` to the backstop and `$(PYTEST_ARGS)` to the
tier targets. Neither selects, orders or configures a test.

**Not reproducible here**, and the collection is identical, so it is
not the tree:

```text
working tree            4028 passed, 22 skipped
working tree, BGA_EXPECT_DEV=1  4028 passed, 22 skipped
full clone              4011 passed, 39 skipped
shallow clone (as CI)   4010 passed, 40 skipped
CI                      4002 passed,  4 failed, 44 skipped
```

4,050 collected in every column. Against the shallow clone CI has four
extra skips *and* four failures — eight tests behaving differently on
an input neither clone has. `origin/main` was unmoved throughout, so
the merge ref equalled the branch.

The names are unknown because the backstop wrote no junit — that is
`UX-618`, fixed in the same commit that went green, so a recurrence
will be named. This row exists because **the failure was never
diagnosed**, and three identical reds are not a flake anyone has
earned the right to call one.

## Required Fix

The four are named from the next occurrence's junit and root-caused.
If no occurrence comes, the CI-only inputs are enumerated instead and
each is either reproduced locally or ruled out by measurement — the
restored `tier_carry.json` cache is the first candidate, being the one
input a clone cannot have.

## Out of Scope

- Re-running to make it go away — declined: it already went away once,
  which is the problem.
- `UX-618`'s instrument — landed, and is what makes this closable.

## Acceptance Test

The four names, and a local reproduction of at least one.
