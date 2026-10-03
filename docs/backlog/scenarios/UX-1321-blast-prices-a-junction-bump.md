# UX-1321: `bga blast` on a junction, or a path inside a junctioned project, says it rebuilds nothing

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the junction-heavy onboarding walk, 2026-10-03 (`/mnt/project-files/onboarding-walk-2026-10-03/onboarding-walk.md`) | **Serves:** R2, R3 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Reproduced on the walk's stand-in (`make-acme.sh` in that folder: three projects, local junctions two levels deep, 16 elements, `pkgs/zlib.bst` in all three) at `19f1fd73`, bst 2.8.1.

```text
$ bga blast junctions/platform.bst
  Resolved as a path (it also reads as an element; resolution order is url, path, element)
  Nothing in this run sources it. Touching it rebuilds nothing here.
$ bga blast subprojects/platform/subprojects/base/files/gen/cmake
  Nothing in this run sources it. Touching it rebuilds nothing here.
$ bga blast files/gen/cmake            # the same thing in the top project
  Sourced directly by 4 elements ... Rebuilds 5 elements ... Cost: 17.1 s
```

The truth for the junction is 13 of 16 elements. `sources.json` stores the junctioned source as
`junctions/platform.bst:junctions/base.bst:files/gen/cmake`; the path form never maps to it, and
junction elements have no entry (`bga/blast.py:429` prints the sentence).
`docs/guides/real-project.md` says "a junction bump rebuilds its whole subproject" and that blast
prices a change before you make it.

## Decomposition

Input classes: a junction element named by its element path; the same named by its file path
(`elements/junctions/x.bst`); a nested junction (`a.bst:b.bst`); a path inside a local junction's
checkout; a path inside a nested one; a path under no junction and sourced by nothing (today's
answer stays); a remote (git) junction named by its url.

## Required Fix

A junction is a source of every element behind its prefix: blasting it answers that closure plus
everything downstream, and says it read the name as a junction. A path under a local junction's
checkout maps to its junction-prefixed identity before the lookup. "Rebuilds nothing" is never
printed for a path inside a junction checkout; an unresolvable one says so.

## Out of Scope

A cost for a remote junction's ref bump beyond the elements it rebuilds.

## Acceptance Test

On the stand-in, `bga blast junctions/platform.bst` reports 13 elements rebuilt and the base
subproject path reports the four base elements it sources; a guard holds both on a fixture run
with a junction. Reading taken in this container.

## Outcome
