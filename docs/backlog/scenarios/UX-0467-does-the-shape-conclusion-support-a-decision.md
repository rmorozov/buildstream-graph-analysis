# UX-467: the graph-shape conclusions have no negative case

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-464` (T1 is the positive case; the negative case is a fixture too) · reads `UX-460`'s registry | **Found by:** round 72, thread 2 of the audit — whether the conclusions and the representation of graph shape really support an optimization judgement | **Serves:** the reader who acts on a structural finding that would have fired on any graph | **Topic:** analysis

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

## Outcome

**Round 72 · 2026-09-01 · Status: 🟢 Done for (1) and (2); (3) is deferred, with a reason**

### The gap, closed

`tests/unit/test_the_shape_conclusions_have_a_negative_case.py`, ten
clauses over three fixtures — the shape with a base (`shared_base_wide`,
T1), the shape with one path (`linear_chain`), and the shape with
neither (`ample_capacity`). No `bst`, 0.28s.

The census it pins, measured rather than assumed:

```text
criticality              {wide, flat}
blast-radius-ranking     {wide}
blast-radius-structural  {wide}
mesh-graph               {chain}
```

No shape finding speaks about all three, which is the property
`UX-120`'s inert detector did not have. And every one of the four is
**silent** on at least one shape, which is what tells "bga looked and
there was nothing" apart from "bga cannot see it".

### What it found on its first run

Two conclusions that do not follow from their own published numbers.
Both are filed rather than fixed, per this row's Out of Scope.

**`UX-474`** — on T1, `analyze` publishes:

```text
Elements Most Worth Optimizing First (by blast radius):
    1. mod0.bst (0 downstream elements)
    2. mod1.bst (0 downstream elements)
    3. mod2.bst (0 downstream elements)
```

The only element with reach is the base, correctly excluded as
structural, and what is left is an ordering over a constant published
at MEDIUM severity as a priority. `blast_radius_distribution` is
`None`, so the `is_flat` sentence that would have hedged it is absent
too — the finding's own caveat is switched off by the same condition
that makes it wrong.

**`UX-475`** — on a five-element linear chain:

```text
Note: 100% of elements have zero slack - this graph is a mesh of
near-equal chains, so savings on one element are often capped by the
next chain rather than by its own duration
evidence: {'zero_slack_share': 1.0}
```

`zero_slack_share` is 1.0 **by construction** on any single-path
graph, and the finding reads it as evidence of a mesh — fixing guide
§5 in a shipped conclusion. The advice is inverted where it lands: on
a chain the saving is exactly the element's own duration, which is the
opposite of what the reader is told.

### Mutations applied

| # | Mutation | Went red |
|---|---|---|
| Q1 | the all-1.0 criticality drop rule removed | the chain's silence, the census, the all-three clause |
| Q2 | structural elements no longer split out of the ranking | `..._names_only_structural_elements`, the census |
| Q3c | `compute_findings` stops branching on `chain_bound` | 4 clauses, including both negative-case ones |
| Q4 | the mesh finding renames its evidence key | the census, `..._reads_a_zero_slack_share` |

### A mutation of mine that did not discriminate, and what it exposed

**Q3 first mutated `_ranking_findings`'s own first line** — `if
chain_bound or not top_blast_radius: return []` — and every clause
stayed green. That line is **unreachable**: `compute_findings`
branches on `chain_bound` and only calls the function in the `else`,
so it can never see a true `chain_bound`. Removing it changes nothing.

So the guard was right and my reading of the mechanism was wrong, and
I had written the wrong mechanism into the clause's docstring before
checking it. Both are corrected: the clause now says the gate is at
the call site, and the dead line is recorded in `UX-474` — a reader
takes it for the gate, and the real gate is fifty lines away.

Q3 also turned up the sharper half of `UX-474`: on the chain the blast
counts genuinely vary (4, 3, 2, 1, 0) and the ranking is suppressed;
on T1 they are all zero and it is published. The shape where the
ordering would carry information is the one that does not get it.

### Deviation from the Required Fix

**Part (3) — one sentence per finding naming the decision it supports —
is not done, and the reason is (1)'s result.** You cannot write "the
decision this supports" for a ranking of zeros or for a mesh sentence
that fires on a chain; the sentence would be documenting a defect. It
is deferred until `UX-474` and `UX-475` close, and named here rather
than quietly dropped.

Parts (1) and (2) landed in a new file rather than in
`test_the_journey_has_an_answer_key.py` as the Required Fix said. That
file is bst-gated and walks a real 43.9s build; these clauses are
fixture-derived and need no `bst`, so putting them there would have
made a fast check run only where `bst` is installed.

### Tier and suite

0.28s over ten clauses — SMALL by default, no tier list moves.

```text
$ make test
5560 passed, 28 skipped, 1 warning in 299.91s (0:04:59)
$ make lint
All checks passed!
```
