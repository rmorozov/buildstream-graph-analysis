# UX-467: the graph-shape conclusions have no negative case

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-464` (T1 is the positive case; the negative case is a fixture too) · reads `UX-460`'s registry | **Found by:** round 72, thread 2 of the audit — whether the conclusions and the representation of graph shape really support an optimization judgement | **Serves:** the reader who acts on a structural finding that would have fired on any graph | **Topic:** analysis

## Motivation

`FINDING_READERS` gives the graph-owner two findings, `mesh-graph` and
`criticality`, and the recipe-author four. From a clone, one of the
graph-owner's two and one of the recipe-author's four can be produced
at all (`UX-463`'s table). So the findings that answer "what shape is
my build, and what does that tell me to do" are the least exercised in
the tool.

The specific risk is the one `UX-120` already caught once, in the
merge candidate that "had fired only on synthetic unit-test input.
Both real captures it had ever seen produced the *negative* answer —
which is the correct answer for those projects, and is also exactly
what an inert detector produces."

Every structural finding is in that position now. There is no fixture
that is *deliberately fine* — a graph whose shape offers nothing to
optimize — so nothing distinguishes "bga looked and there was nothing"
from "bga cannot see it".

## Required Fix

1. **The answer key, extended to shape.**
   `tests/unit/test_the_journey_has_an_answer_key.py` already
   recomputes the headline's own published numbers. Extend the same
   discipline to the structural conclusions: for `mesh-graph`,
   `criticality`, `blast-radius-ranking` and
   `blast-radius-structural`, assert the published conclusion follows
   from the published numbers, on T1.
2. **The negative fixture.** A topology whose shape genuinely offers
   nothing — a flat, independent, capacity-ample set — and an
   assertion that each of the four findings either does not fire or
   fires saying so. This is the clause that turns an inert detector
   red.
3. **The judgement, stated.** For each of the four, one sentence in the
   finding's own `why` naming the decision it supports. A conclusion
   that supports no decision is `UX-321`'s question that can never
   answer, and should be filed rather than rendered.

## Out of Scope

- Changing what the findings compute. If (1) shows a conclusion does
  not follow, that is a row of its own and a bigger one than this.
- The viewer's drawing of the shape — `UX-350`'s shape channel and
  `UX-361`'s figures are separate. This item is about whether the
  *conclusion* is sound, not whether the picture is pretty.
- `cache-transfer-cost` and the other recipe-author gaps that are
  fixture-population problems: `UX-463` and `UX-464` own those.

## Acceptance Test

```bash
python3 -m pytest tests/unit/test_the_journey_has_an_answer_key.py -q
```

green with the new clauses, and each new clause reddened by a mutation
that makes its finding fire on the negative fixture — pasted in the
Outcome, per the `falsify` skill.
