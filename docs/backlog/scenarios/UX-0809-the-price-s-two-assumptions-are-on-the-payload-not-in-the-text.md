# UX-809: the price's two assumptions are on the payload, not in the text

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-739 (the price) | **Found by:** round 112, `UX-739`'s verifier | **Serves:** R4 and R5 reading the priced advice as text | **Topic:** analysis | **Area:** bga | **Shape:** bounded

## Motivation

`UX-739`'s Required Fix asked that the figure "say what the model
assumes about queueing" and state whether it is a prediction or a
bound. The payload does: `pricing_assumptions` carries the dispatch
sentence and the floor sentence, and `docs/guides/cli.md` documents
both. The text a reader sees does not — the verifier grepped
`bga/findings.py` and `bga/cli.py` and found no reference; each priced
row ends in `(floor, +0.9 s)` and nothing says which way a floor errs
or that the benefit side is unmodelled:

```text
$ grep -n "pricing_assumptions" bga/findings.py bga/cli.py
(no output)
$ bga analyze <round-112 probe run> --plane2 plane2.json | grep -A3 "Together"
  Together (codegen.bst, lib-a.bst, …): build 29.6 s -> at least 30.5 s (floor, +0.9 s)
```

A floor without its direction reads as a prediction, which is the
false point estimate `UX-170` was filed against.

## Required Fix

`_capacity_recommendation_finding` (`bga/findings.py`) renders the two
`pricing_assumptions` sentences once, after the joint line, verbatim
from the payload — the text reads what the JSON says rather than
re-stating it. Guard: the finding's detail on a priced advice contains
both sentences; mutation: drop the render, red.

## Decomposition

Input classes the guard covers: an advice with at least one priced row
(both sentences present), one with only refusals (no price, no
sentences), and one with no advice at all; the journey it extends is
`test_the_max_jobs_price_moves_with_the_recommendation.py`'s — rows →
price → rendered line — with the assumption sentences as its last step.

## Out of Scope

- The page: the viewer draws none of this block today (`UX-739`).
- Re-wording the sentences — they are the payload's, and the guard in
  `test_the_max_jobs_price_moves_with_the_recommendation.py` reads them.

## Acceptance Test

On the round-112 probe capture, `bga analyze --plane2` text output
carries both sentences under the joint line (pasted); the page budget
guards green; the mutation reddens the new guard.
