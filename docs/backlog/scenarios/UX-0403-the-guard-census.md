# UX-403: the guard census — every guard proves it can fail

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** the audit loop itself | **Topic:** guards

## Motivation

The falsify ritual (mutate the mechanism, watch the guard go red,
restore) runs today as a *sample*: each audit round mutates the
handful of guards it touches. Hollow guards have been found by that
sampling in rounds 18, 19, 23, 27 and 45 — a hit rate high enough
that the unsampled majority certainly contains more. A guard that
cannot fail is worse than no guard: it spends suite time buying
false confidence.

## Required Fix

Run the census once, as a round of its own:

- Inventory the guards by class (the styleguide conformance walks,
  the contract/schema guards, the docs guards, the census-style
  guards, the browser walks) — the class list, not 344 files, is the
  unit of work.
- For each class, one representative mechanism-revert mutation per
  guard *family*, scoreboarded: guard, mutation, RED?/GREEN?. The
  house `falsify` skill is the per-guard procedure; this task is the
  sweep that applies it.
- Every guard that stays green under its mutation is fixed or
  deleted in the same round, with the scoreboard committed to the
  round's audit doc.
- The census leaves a ratchet: new guards land with their mutation
  named in the closing task's verification log (already the `verify`
  skill's habit — the census makes it retroactive).

## Out of Scope

- Mutation *testing* of the product code (mutmut-style, every
  arithmetic operator) — the census mutates mechanisms guards claim
  to hold, not every line; the yield argument is the five rounds
  above, all of which were mechanism-level.
- Automating the census into CI — one deliberate round first; a
  standing harness is its own decision once the hit rate is known.

## Acceptance Test

- The scoreboard exists, covers every guard class, and names each
  hollow guard found with its fix-or-delete commit.
- A re-run of any scoreboard row reproduces its RED.
