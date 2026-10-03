# UX-1330: `whatif --element pkgs/gcc-libs.bst` is refused without offering the junction-qualified element it means

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the junction-heavy onboarding walk, 2026-10-03 (`/mnt/project-files/onboarding-walk-2026-10-03/onboarding-walk.md`) | **Serves:** R1 | **Topic:** cli | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Reproduced on the walk's stand-in (`make-acme.sh` in that folder: three projects, local junctions two levels deep, 16 elements, `pkgs/zlib.bst` in all three) at `19f1fd73`, bst 2.8.1.

```text
$ bga whatif --element pkgs/gcc-libs.bst
  Refused: Not in this run's graph: pkgs/gcc-libs.bst. A subset quietly missing a member projects a different question from the one asked.
```

The run holds `junctions/platform.bst:junctions/base.bst:pkgs/gcc-libs.bst`
(`bga/whatif.py:131`). Users type the name they see in their editor.

## Decomposition

Input classes: a short name matching one junctioned element; matching several (ambiguous); matching
none. Surfaces: `whatif --element`, `blast` with an element name.

## Required Fix

The refusal names the junction-qualified element(s) whose last component equals the name given,
as "did you mean"; it still refuses rather than substituting.

## Out of Scope

Fuzzy matching.

## Acceptance Test

On the stand-in, the refusal names `junctions/platform.bst:junctions/base.bst:pkgs/gcc-libs.bst`;
a guard asserts the one-match and the ambiguous case. Reading taken in this container.

## Outcome
