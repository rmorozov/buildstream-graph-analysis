# UX-625: reverting a mutation can discard the work

**Priority:** Low | **Status:** 🔴 Open | **Depends on:** UX-560 (the track's recovery), UX-614 (the base check) | **Found by:** round 85, by the UX-621 track paying for it | **Serves:** a track falsifying its own guard | **Topic:** guards

## Motivation

The `falsify` skill says apply the mutation, watch it redden, revert
it. It does not say **how**, and one obvious how is wrong:

```text
$ git checkout -- .github/workflows/ci.yml     # revert mutation 1
  … also discards the track's own uncommitted edit to that file
$ pytest …                                     # mutation 2
  2 failed — one of them a false red, diagnosed as a real one first
```

A track's working tree is the only copy of work that is not yet
committed, and the mutation is applied to the same file the work is
in. `git checkout --` cannot tell them apart. The UX-621 track lost
its `ci.yml` edit this way and worked around it with file copies into
the scratchpad.

The cost is not the lost edit — that is a minute. It is the false red
in the next mutation's run, which reads exactly like a guard that does
not discriminate, and is the one reading this repository takes most
seriously.

## Required Fix

Either the skill says what a safe revert is — snapshot the file first,
or apply the mutation as a patch and reverse-apply it — or a helper
does it, so the track does not have to have been bitten once to know.

Whichever, the argument is that the mutation and the work occupy the
same file, and no `git` revert command distinguishes them.

## Out of Scope

- The mutation discipline itself — right, and unchanged.
- `UX-560`'s recovery, which is about the base, not the desk.

## Acceptance Test

A mutation applied to a file the track has already edited, reverted,
and the track's own edit still present.
