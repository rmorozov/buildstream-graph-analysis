# UX-923: the round-dateline guard reads a document's first *commit* date, so any round squash-merged after 00:00 UTC reddens main

**Priority:** Medium | **Status:** 🟡 In Progress | **Depends on:** — | **Blocks:** every branch cut after such a merge | **Found by:** round 135 — `main` was red at `74fb2712` two minutes after `#249` merged, and the failure was not the merging branch's diff | **Serves:** every round whose branch outlives the UTC day it worked on | **Topic:** guards | **Area:** tools | **Shape:** bounded

## Motivation

`test_a_run_is_priced.py`'s
`test_a_documents_dateline_matches_its_own_first_commit` asserts a
round document's stated dateline equals the git date of the commit
that added it. On `main` at `74fb2712`, with no branch applied:

```text
E   AssertionError: round 130: docs/audits/round-130.md's own dateline
    says 2026-09-21, but it was first committed on 2026-09-22 - a
    retroactively-written document not named in DATE_MISMATCH_WAIVER
1 failed, 87 passed in 2.51s
```

Nothing was written retroactively. Round 130 ran on 2026-09-21 and
says so; `#249` was **squash**-merged at `2026-09-22T02:07:37Z`, and a
squash keeps no commit from the branch, so the only date left in the
history is the merge's:

```text
$ git log --format='%H %aI %cI' --diff-filter=A -- docs/audits/round-130.md
74fb2712 2026-09-22T05:07:37+03:00 2026-09-22T02:07:37+00:00
```

**The guard reads a proxy** (fixing guide §5): the merge date stands in
for the work date, and the two agree only while a round is merged on
the day it ran. Every round merged after 00:00 UTC reddens `main` for
every branch cut from it, and the reddening branch's own diff is
innocent. The existing `DATE_MISMATCH_WAIVER` entries are a different
cause — `UX-757` really did write four documents retroactively — so
the waiver's own reason text does not describe this case.

## Required Fix

Round 130 is waived now, with this row's id and this cause named, so
`main` is green and branches can be cut from it. That is the unblock,
not the fix.

The fix is a date the guard can read that survives a squash. Options,
none measured yet:

- The document states its own dateline, and the *round register*
  (`tools/dev_round_register.py`) derives from the committed union.
  A round whose dateline is not its merge date is only a defect if
  the dateline is *wrong*, and nothing in the history can say so
  after a squash — so the guard may be asserting something
  unknowable and should read the register instead.
- A tolerance (the merge date is the dateline, or within N days of
  it) turns a hard equality into a band, which this repository
  usually prefers to a waiver list that grows one entry per round.
- A committed field — the round document stating the merge sha it
  landed as — is a third source of truth and probably one too many.

Whichever wins, the waiver entry this row adds comes out, and the
guard's own "waived for a mismatch that no longer reproduces" clause
catches it if it does not.

## Out of Scope

`UX-914`, the round that found this. The `NO_DATELINE_WAIVER`
population, which is closed pre-register history. `UX-757`'s four
existing entries, whose cause really is retroactive authoring.
Changing how rounds are merged.

## Acceptance Test

`main` is green on
`test_a_documents_dateline_matches_its_own_first_commit` with round
130's waiver entry **removed**, on a tree where round 130's document
still states 2026-09-21 and its only commit is dated 2026-09-22.

A round document whose dateline is genuinely wrong still reddens — the
mutation is editing a round's dateline to a date neither its merge nor
its work, and watching it go red.

## Outcome

**Round 135, 2026-09-22 — 🟡 the unblock only.** `main` at `74fb2712`
was red on this guard with no branch applied, two minutes after `#249`
merged, so `UX-914` could not be committed at all (the
`selector-before-commit` hook runs `make test-touching`). Round 130 is
in `DATE_MISMATCH_WAIVER` with this row's id and the squash-merge
cause, and the guard is green:

```text
$ python -m pytest "tests/unit/test_a_run_is_priced.py::TestARegisteredRoundsDateMatchesItsDocument" -q
88 passed
```

The class is untouched: the next round merged after 00:00 UTC reddens
the same way, and this row stays 🟡 until the guard reads a date a
squash cannot destroy.
