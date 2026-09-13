# UX-831: a max-jobs advice row is four levels deep

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-677 (the advice), UX-739 (the price), UX-808 (one row per element) | **Found by:** round 115, the design review | **Serves:** R5 setting max-jobs across a large project | **Topic:** viewer | **Area:** bga-viewer | **Shape:** judgement

## Motivation

On the walk capture (3 elements) the advice is folded like every
table — and each row is a card:

```text
capacity_recommendation--max-jobs-advice   data-rows=5  data-levels=4  badge "5 rows"  569.9 px open
                                            = 114 px per row
```

`priced` and `price_refusal` (`UX-739`) are objects inside the row, so
the structured renderer nests them; at the owner's scale the section is
the several screens the owner measured, before any cap acts on the
nesting.

## Required Fix

`priced.cost_us` and `price_refusal` flatten into two columns
("Price", "Why not priced"); the row is one level; the table caps and
filters at the row cap like `elements`, ranked priced lowerings first,
refusals last.

## Decomposition

Input classes: a priced row, a refused row, an unchanged row, and a
run with no advice (Plane 1 only); the journey is R5's max-jobs question
in the answer key.

## Out of Scope

- The pricing itself — `UX-739`.
- The joint figure's sentence — `UX-809`.

## Acceptance Test

`data-levels="1"` on the advice table; ≤ 40 px per row at 1440; on a
Plane 2 run with more than the cap the badge reads `N of M` and a filter
is present; mutation: nest `priced` again — the levels guard reds.
