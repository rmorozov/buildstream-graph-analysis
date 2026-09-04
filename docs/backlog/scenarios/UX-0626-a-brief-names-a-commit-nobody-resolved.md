# UX-626: a brief names a commit nobody resolved

**Priority:** Low | **Status:** 🔴 Open | **Depends on:** UX-510 (the brief names its base), UX-614 (the track verifies it) | **Found by:** round 85, by the UX-621 track refusing to trust it | **Serves:** a track given a base | **Topic:** guards

## Motivation

Round 85's brief for `UX-621` named its base as commit `2a7d1b8`.

```text
$ git cat-file -t 2a7d1b8
fatal: Not a valid object name 2a7d1b8
$ git log --oneline --merges -3
c57c046 Merge branch 'worktree-agent-a4bbcc3ea4301707f' …
2724972 Merge branch 'worktree-agent-a4b6a45b499adfdc3' …   ← the one described
```

The id was **written from memory rather than read**. The orchestrating
session had the merge in front of it and typed a hash it had not
copied. The track caught it, resolved the description instead of the
hash, and said so — which is `UX-614`'s check working.

The track's own reading was that the brief came from "a different
object database". That is the generous explanation and it is wrong;
recorded here because a row whose Motivation is a comfortable guess is
the shape round 84 filed six of.

`UX-510` asks that a brief name the base it will actually get. Nothing
checks that the base it names exists, and the check is one command.

## Required Fix

A brief's base is resolved before the track is launched — `git cat-file
-t` or `git rev-parse --verify` on the id, by whatever writes the
brief — or the brief names a ref rather than a hash, which resolves or
does not at the point of use.

## Out of Scope

- `UX-614`'s recovery, which handled this correctly and is closed.
- `UX-623`, which is about which refs a track can read at all.

## Acceptance Test

A brief carrying an unresolvable base, refused before a track is
launched rather than after.
