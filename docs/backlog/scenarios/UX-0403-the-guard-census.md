# UX-403: the guard census — every guard proves it can fail

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Serves:** the audit loop itself | **Topic:** guards

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

## Outcome (round 64, 2026-08-29) — 🟢 Done

### The gap, measured

The falsify ritual ran as a sample. Nothing said which *families* had
never been falsified at all, so "the unsampled majority certainly
contains more" was an argument rather than a measurement.

### After

Eleven families, one mechanism-revert mutation each, applied to the
committed tree and reverted after the run. The full scoreboard, with
the mutation and the pass/fail line for every row, is
[`docs/audits/guard-census-round-64.md`](../../audits/guard-census-round-64.md):

```text
contract inventory           RED      3 failed, 13 passed in 6.51s
docs links + commands        RED      1 failed, 35 passed in 5.77s
plane2 destinations          RED      4 failed,  8 passed in 0.48s
element join merge           RED      6 failed,  4 passed in 8.90s
chapters / ordering          RED      3 failed,  9 passed in 7.25s
tier partition               GREEN             14 passed in 0.58s
review cadence               RED      1 failed,  7 passed in 0.07s
viewer seams                 RED      1 failed, 46 passed in 0.28s
unit census                  RED      1 failed, 46 passed in 7.46s
declared quantity vs value   RED      2 failed,  8 passed in 1.01s
golden snapshot              RED      2 failed          in 0.42s
```

**Ten of eleven discriminate.** One did not, and it was fixed in this
round as the filing requires.

### The one that did not, and its fix

`test_the_tiers_are_a_partition.py` stayed green on all fourteen of its
clauses while a **fifty-second** file left the `LARGE` list. Every
clause reads the two lists against each other or against the
filesystem; `small` is the default tier, so a file that belongs in a
tier and is absent from both is "small on purpose" and nothing says
otherwise.

Fixed for the half that is legible without measuring: a file that boots
a real Chrome cannot be small and says so in its imports. **Four were
booting one from the small tier**, three of them added in this same
round:

```text
tests/unit/test_a_shapeable_population_is_drawn.py    2.2s
tests/unit/test_a_task_uid_is_not_a_label.py          1.7s
tests/unit/test_one_bucket_one_row.py                 1.9s
tests/unit/test_the_synthesis_reaches_the_page.py     2.6s
```

So the hollow guard was not only hollow — it was hollow over a live
defect, in the tier the whole edit-run loop is sized against.

The half that needs a measurement is filed as **`UX-418`**: an unlisted
file slow for any other reason is still caught only by CI's small-tier
timeout, which fails naming a budget rather than the file.

### Mutations verified red and reverted (2, on the new clauses)

The eleven census mutations are the scoreboard above. The two new
clauses have their own:

| # | mutation | reddened |
|---|---|---|
| D1 | `test_one_bucket_one_row.py` unlisted again | `test_every_browser_guard_is_listed`, naming the file; 1 failed, 15 passed |
| D2 | the detection pattern changed to match nothing | `test_the_rule_has_something_to_check`; 1 failed, 15 passed |

D2 is the clause that keeps D1 honest: a pattern that stopped matching
would empty the first clause and pass forever, which is the exact shape
this whole census exists to find.

### Deviation from the Required Fix

- **"Inventory the guards by class… the class list, not 344 files."**
  Done, at eleven families over 364 files. The families were chosen by
  reading the suite rather than derived from anything, which is a real
  limit and is written into the scoreboard's own "what this census does
  not cover" section rather than left implicit.
- **"Run the census once, as a round of its own."** It ran inside this
  round rather than as a separate one. That is a deliberate deviation
  and the cost is visible: eleven families, not the exhaustive sweep
  the filing pictures. What the round bought instead is that the one
  hollow guard it found was fixed and falsified in the same commit,
  which the filing also requires.
- **"A re-run of any scoreboard row reproduces its RED."** The driver
  is deterministic — the mutations are literal string substitutions
  against the committed tree — and row 6's GREEN was reproduced twice,
  once in the first pass and once after the three truncated rows were
  re-run.
