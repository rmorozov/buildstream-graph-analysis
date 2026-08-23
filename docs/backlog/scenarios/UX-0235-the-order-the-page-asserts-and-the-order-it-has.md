# UX-235: the order the page asserts, and the order it has

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-207, UX-216, UX-221 (the guards it repairs) | **Serves:** the maintainers; R1 indirectly

## Motivation

Round 27's verification ran twenty-two mutations; twenty reddened.
The two that stayed green, plus one skip semantics seam:

1. **The decision panel's order guard is a tautology.** The
   acceptance said "DOM order asserted"; the harness builds the
   expected order as a hardcoded literal over three separately
   invoked renderers and never reads `boot()`'s insertion — so
   `root.prepend(decision)` mutated to `append` leaves
   `test_the_decision_comes_before_the_evidence` green. The same
   class holds for `UX-221`: "culprits above the band" is asserted
   for the *text* report and unguarded on the page.
2. **The anchor-equality probe set has an underscore gap.**
   `cssId` re-duplicated with `[^A-Za-z0-9-]+` — differing from
   `[^\w-]+` only on `_` — survives every guard, and `my_lib.bst`
   gets a link that misses its target. The probe uids simply
   contain no underscore.
3. **"Runs on a fresh clone" quietly means "plus dev extras".**
   The jsonschema-dependent guard files `importorskip` at module
   level, so a plain `pip install -e .` collapses whole files to
   "1 skipped" — CI installs `[dev]` and is covered, but the
   fresh-clone claim several logs make is one extras-flag wider
   than it sounds.

## Required Fix

Page-order guards that read the booted document's actual node
sequence (the two named sites, and the pattern documented so the
next "X above Y" claim ships with a real order assertion); an
underscore-bearing uid in the anchor probe set; and the skip made
loud — a conftest-level marker that counts module-level skips and
one canary asserting the expected number, so a vanished guard file
is a red line rather than a quieter green.

## Out of Scope

- New ordering behavior (both orders are correct today; only the
  guards are hollow).
- Making jsonschema a hard dependency (dev-only stays; the claim
  gets honest instead).

## Acceptance Test

`prepend`→`append` on the decision panel reddens; moving the
culprit strip below the band reddens; the `[^A-Za-z0-9-]`
re-duplication reddens on the underscore probe; deleting a
jsonschema-guarded test file (or its extras) fails the canary
rather than skipping silently.
