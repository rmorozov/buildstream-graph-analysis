# UX-623: a track cannot read the tree it was copied from

**Priority:** Low | **Status:** 🔴 Open | **Depends on:** UX-614 (the base instruction), UX-510 (the brief names its base) | **Found by:** round 85, measuring UX-614 | **Serves:** a track checking the base it was given | **Topic:** guards

## Motivation

`UX-614` tells a track to verify the base it actually got. Measuring
that instruction found the classifier refuses the command that would
read the other side:

```text
git reset --hard HEAD              permitted, in the worktree
git -C <main-checkout> rev-parse   refused
```

Both readings falsify a premise the brief carried. The one that
matters here is the second: a track can inspect its own branch and
`origin/*`, and cannot inspect the checkout it was branched from. So
"is my base the round's tip" is answerable only through a ref the
worktree already has — which is fine when the round's branch is
pushed, and unanswerable when it is not.

`UX-614`'s instruction is written for the answerable case. Nothing
says so, and nothing catches the other one.

## Required Fix

The brief states which refs a track can read, and the base check is
written against those. Where the round's branch is local-only, the
orchestrating session passes the base as a commit id rather than a
branch name, or pushes first — decided, not left to the track.

## Out of Scope

- The classifier itself — harness configuration, not this
  repository's to change.
- `UX-614`'s `--ff-only` instruction — right, and unchanged.

## Acceptance Test

A track launched against an unpushed round branch, reporting the base
mismatch rather than reporting a base it could not check.
