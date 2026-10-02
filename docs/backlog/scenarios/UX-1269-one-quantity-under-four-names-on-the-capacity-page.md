# UX-1269: one wait quantity carries four names, and two glosses contradict their source

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-163 walk of the merged page (2026-10-02) | **Serves:** R1 | **Topic:** viewer | **Area:** bga, bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

On the 2,402-element two-snapshot synthetic page at 1440: the decision says "Scheduling gap 42.5 min", the time chapter "Waiting on resources 43.7 min", `#floors` "Certified headroom 9.9 s", and "Execution on the chain 3.0 min" sits beside "Chain floor T∞ 4.6 min", with nothing saying which to quote. `#utilisation` glosses "Effective CPUs 4" as "Builder slots as recorded, not host cores" while its source line reads "Detected host cores". `costliest-binary` says "Start with make" at 36.0 s of CPU, 0.3% of the 3.1 h capacity, and `by_binary`'s Wall 2.9 h for make sums its children.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`.

## Required Fix

Each of these quantities is named once in reader words with its relation to the others stated where two appear together; a gloss agrees with its source; a Plane 2 finding whose share of capacity is below Plane 1's opportunity floor carries no step to act on.

## Out of Scope

The figures themselves.

## Acceptance Test

On this page no two headings name the same wait quantity differently, the Effective CPUs gloss matches its source, and costliest-binary below the floor reads as context. Mutation: restore one name, and the guard reds.
