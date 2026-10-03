# UX-1327: No report section answers which junction's elements cost the most, and `junction-cost` is about variants

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the junction-heavy onboarding walk, 2026-10-03 (`/mnt/project-files/onboarding-walk-2026-10-03/onboarding-walk.md`) | **Serves:** R3, R5 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Reproduced on the walk's stand-in (`make-acme.sh` in that folder: three projects, local junctions two levels deep, 16 elements, `pkgs/zlib.bst` in all three) at `19f1fd73`, bst 2.8.1. The report has no grouping by junction prefix. A junction-heavy owner asks which project's
elements dominate the critical path, which junction's elements were built locally rather than
pulled from that project's cache, and what each junction's bump costs. `bga junction-cost @last`
answers a different question:

```text
N separate invocations against one junctioned build: 1 run
  Refused: One run is nothing to join ...
```

## Decomposition

Input classes: no junction (section absent); one junction; nested junctions (each prefix level
its own row, the deepest owning the element); a junction whose elements were all cached. Surfaces:
`analyze` text and json (a new optional key, schema version bump if required), `junction-cost`'s name.

## Required Fix

`bga analyze` prints a "By junction" section when the run has junctioned elements: per junction
prefix, elements, built vs cached, build seconds, share of the critical path, and the blast of a
bump; and one finding when a junction's cache-hit ratio is far below the top project's.
`variant-cost` is added as the command's name, `junction-cost` kept as an alias.

## Out of Scope

The page's rendering of the section.

## Acceptance Test

On the stand-in, `bga analyze @last` prints the three-row section (top project, platform, base)
with element counts 4, 5, 6 building and cached; a guard over a fixture run asserts the rows.
Reading taken in this container.

## Outcome
