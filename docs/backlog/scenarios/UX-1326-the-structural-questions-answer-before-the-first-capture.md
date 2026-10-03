# UX-1326: `bga blast --no-cost` refuses without a snapshot, though `bst show` holds everything it needs

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the junction-heavy onboarding walk, 2026-10-03 (`/mnt/project-files/onboarding-walk-2026-10-03/onboarding-walk.md`) | **Serves:** R1, R3 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

On carbonOS build-meta (316 elements in `groups/core.bst`, 140 junctioned), no snapshot yet:

```text
$ bga blast pkgs/gcc.bst --no-cost
Error: @last names a snapshot and /root/walk/carbon has none yet. `bga snapshot -- bst build TARGET` takes one.
$ bga graph-from-show . groups/core.bst /tmp/carbon-graph.json
Wrote graph.json with 316 elements, 1163 dependencies   (6.6 s)
$ bga rebuild-set /tmp/carbon-graph.json --cut junctions/bootstrap.bst:pkgs/glibc.bst --count-only
216
```

The help says `--no-cost` answers "from the graph and the source inventory alone". A first capture
of such a project takes hours; this is the answer available in seconds.

## Decomposition

Input classes: no snapshot and a loadable project; no snapshot and a project that fails to load
(the `bst show` error, not the alias error); a snapshot present (today). Surfaces: `bga blast
--no-cost`; the alias error in `bga/run_store.py:398`.

## Required Fix

`bga blast --no-cost` with no snapshot builds the graph and source inventory from `bst show` on
the requested target (or the project's default target, named in the output) and answers; the
output says it read the project, not a run.

## Out of Scope

`graph`, `floors` and the other run-reading sections without a snapshot.

## Acceptance Test

On carbonOS, `bga blast junctions/bootstrap.bst:pkgs/glibc.bst --no-cost` with no snapshot answers
with element counts; a guard with a fake `bst show` asserts it. Reading taken in this container.

## Outcome
