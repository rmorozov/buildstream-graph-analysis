# UX-180: the docs still assert what the disputed region broke

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-170 (the fix the docs trail), UX-138 (the glossary), UX-135 (the README budget)

## Motivation

UX-170's mechanism landed and holds (the −25% same-commit pair now
answers `WITHIN THE BASELINE SET'S OWN OBSERVED RANGE`); its
documentation trail did not keep up, and the round-19 review collected
the debris:

1. `real-project.md:784-786` still states the fixed defect in the
   present tense — "still calls the widest one `IMPROVED (-25.0%)`" —
   committed in the same push that makes that sentence false, and
   UX-170's own Required Fix ordered this claim to "become whatever is
   true after the fix".
2. The **fourth duration verdict is missing from every verdict list**:
   `cli.md:474` and README's verdict sentence both enumerate
   improved / regressed / no significant change / not comparable.
3. `bga/compare.py:818-821`'s docstring — the gate "fails exactly when
   a human reading the report would call it a regression, never a
   second, silently-different definition" — is now false twice over
   (band widening and the disputed region), and `cli.md:484` repeats
   it. UX-170's log says the divergence is documented there; it says
   the opposite.
4. The UX-176 fastest/slowest correction shipped unmarked (bare word
   swap, no annotation), against the convention its own batch applied
   one file over.
5. UX-174's `directory:` keying claim carries no provenance note —
   its acceptance required one, measured preferred.
6. **The glossary has no rows for the round's load-bearing terms**:
   blast, resource, keying (ref vs content), work (vs wall clock),
   building vs assembling. Five terms, three surfaces, zero
   definitions — the exact drift UX-138 was filed against.
7. README is at 266 lines against UX-135's ≤250: trim the four-line
   monorepo addition's neighbors or annotate the budget with the
   reason — silently exceeding a measured target is how 420 became
   "430".

## Required Fix

As numbered; the gate docstring (3) should state the two divergences
and point at UX-170's disputed-region rationale rather than promising
an equivalence that is deliberately gone.

## Out of Scope

- The band mechanics (verified holding).

## Acceptance Test

The docs-commands suite covers the corrected sentences; a grep test
pins the four-verdict list in both files; the glossary rows exist and
`make lint-docs` stays green; README ≤250 or the budget annotation
exists with the number restated.
