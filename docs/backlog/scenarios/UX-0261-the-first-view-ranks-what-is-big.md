# UX-261: the first view ranks what is big, not what is worth doing

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-258, UX-259 | **Serves:** R1 — the whole point of the first screen | **Topic:** viewer

## Motivation

`UX-258` fixes the ranking's *content*. This is what the first screen
should lead with once it is fixed, and the answer is not "the same list,
filtered".

Measured on the 1,202-element run, what the reader currently meets
first is a list of eleven near-identical blast counts led by a
structural root. What they actually need, in order:

1. **What the build is waiting for** — longest on the critical path.
   Already computed, already the honest first answer, and currently
   below a ranking that is not.
2. **What shape this graph has** — the blast radius *density*, not one
   element's count. Half the elements here reach 30 or fewer; the top
   decile reaches 465 or more. A graph where one element reaches
   everything is a different problem from one where a hundred do, and
   the reader should know which they have *before* being handed a list
   of elements.
3. **What is unusual for its kind** — the outlier. Once structural
   entries are set aside (`UX-258`) and the distribution is known
   (`UX-259`), "worth optimizing" has a definition: high for its
   population, not high in absolute terms.

## Required Fix

1. The decision block leads with the critical-path answer, and the
   blast ranking follows it rather than preceding it.
2. A one-line density statement — the shape, from `UX-259`'s
   distribution, in a sentence rather than a chart.
3. The ranked list marks entries that are structural (reported, per
   `UX-258`) and entries that share a decile (indistinguishable, per
   `UX-259`), so the reader can see which parts of the order are real.

## Out of Scope

- A new chart. `UX-196`'s rule holds: the numbers make themselves
  self-evident, and a decile histogram earns its place only if a
  sentence cannot carry the shape.
- Re-ordering sections wholesale. `UX-207` settled the first screen and
  `UX-235` guards the order; this changes what the decision block
  *says*, not where it sits.

## Acceptance Test

The first screen of the 1,202-element run names the critical-path
answer before the blast ranking, states the density in one line whose
numbers match the published distribution, and marks both the
structural entries and the ties. The order guard (`UX-235`'s pattern —
read the document's own sequence) covers the new arrangement.
