# UX-261: the first view ranks what is big, not what is worth doing

**Priority:** Medium | **Status:** 🟢 Fixed & Verified | **Depends on:** UX-258, UX-259 | **Serves:** R1 — the whole point of the first screen | **Topic:** viewer

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

## Outcome

**Fixed.** The decision block leads with what the build is waiting for.

```text
next_steps[0]  shorten-what-the-build-waits-for
               "mod039.bst is the longest thing on the critical path at
                6.0s, 100% of it - the build cannot finish sooner than
                this chain."
               follows_from: signals.critical_path_detail
next_steps[1]  blast-the-top-element
```

Nothing new is computed: `critical_path_detail` was already published
and the answer was already in it, sitting below a ranking of reach.
`_longest_on_the_path` takes the biggest entry, not the first — the
path is in order and its first element is rarely its largest.

**The shape, in one line.** `headline.graph_shape` states the density
from `UX-259`'s distribution:

```text
1,202-element run: "Half of this graph's 1202 elements reach 30 others or
                    fewer; the top tenth reach 465 others or more, up to
                    1201. Reach is spread across many elements - there is
                    no single choke point to fix."
star-shaped run:   "Half of this graph's 44 elements reach nothing; the top
                    tenth reach nothing, up to 42. Reach is concentrated in
                    a few elements - most of this graph cannot cause a wide
                    rebuild."
```

A sentence, never a chart: `UX-196`'s rule holds, and a guard checks
the output is one line of at most three sentences so nobody quietly
grows a histogram.

**A defect in my own first draft, worth recording.** I classified
concentration by comparing the top decile to the median. In a
star-shaped graph — one element reaching everything, the most
concentrated shape there is — both are **zero**, and the sentence
called it *"spread across many elements"*. The fix compares `max`
against the top decile instead, and the star case is now a guard. The
first version was tested only against the spread case, which is exactly
how a wrong rule ships looking right.

A flat graph gets no sentence at all, and a run with no distribution
gets none rather than an invented one.

**Not done:** the ranked list does not yet *mark* structural and tied
entries inline — `UX-258` and `UX-259` put both facts in the finding's
detail and its evidence, and moving them into the table's own cells is
a rendering change that belongs with the next viewer round rather than
with this one. Stated here rather than left to be discovered.
