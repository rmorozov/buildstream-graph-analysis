# UX-250: comparison refuses on host and mode, but not on contract movement

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-249 (the stamp it reads) | **Serves:** R4 — whose gate must not report a definition change as a regression | **Topic:** contracts

## Motivation

With `UX-249`'s stamp recorded, the policy question becomes answerable,
and it is the one Direction 10 was really about: when are two runs
measured by different builds of `bga` *not* comparable?

The wrong answer is "when the package versions differ". It would refuse
every comparison across every upgrade, including the twenty-eight
rounds that changed no contract at all, and a refusal that fires
constantly gets switched off — which is how this repository lost, and
then rebuilt, several guards.

The right answer falls out of the stamp: **refuse when a contract the
comparison depends on moved between the two producers, and report
otherwise.** Two runs from `0.1.0` and `0.9.0` still compare when every
contract they touch is unchanged; two runs one patch apart refuse when
one is not.

Today neither happens, because there is nothing to read.

## Required Fix

1. `bga compare` gains contract movement as a refusal reason, reusing
   `EXIT_CODE_MISMATCHED_RUNS` (6) and the existing refusal wording —
   this is one more dimension of an existing answer, not a new one.
2. The store's aggregate and the trend, which mix many runs rather than
   two, report the contract sets present and exclude the minority the
   way `store-aggregate` already excludes a host class — a distribution
   over two definitions is not a distribution.
3. A missing stamp is **not** a refusal. Every artifact written before
   `UX-249` lacks one, and refusing them would make the feature's
   arrival delete everyone's history. It is named, and counted.

## Out of Scope

- Migration or translation between contract versions. If `analyze/v2`
  arrives, converting `v1` runs is its own decision with its own
  evidence; this item refuses honestly rather than guessing.
- Refusing on the package version. Argued out in Direction 10: it
  would refuse every comparison across every upgrade, including the
  twenty-eight rounds that moved no contract at all.

## Acceptance Test

Two synthetic runs whose stamps differ only in package version compare
normally; two whose stamps differ in a contract the comparison reads
refuse with exit 6 and name the contract; a run with no stamp compares
with the absence named. The first two cases need a fabricated `v2`
stamp, since no contract has yet moved — and that is the point of
building this before the first bump rather than after.
