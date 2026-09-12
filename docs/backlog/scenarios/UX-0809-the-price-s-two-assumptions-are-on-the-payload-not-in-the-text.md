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

## Outcome

**Gap measured.** `grep -n "pricing_assumptions" bga/findings.py
bga/cli.py` — no output, before this change; the two sentences lived
only in `advice['pricing_assumptions']` and the guide.

**Close measured.** `_max_jobs_advice_detail` (`bga/findings.py`) now
appends both sentences, verbatim from the payload, after the joint
line — gated on at least one row carrying `priced` (refusals-only or
no advice render nothing new). Round-112 probe capture, real:

```text
$ PYTHONPATH=. python3 -c "import sys; from bga.cli import main; sys.exit(main())" \
  analyze RUN/run --plane2 RUN/plane2.json | grep -A2 "Together (codegen"
    Together (codegen.bst, lib-a.bst, lib-b.bst, lib-c.bst, lib-d.bst, lib-e.bst, lib-f.bst): build 29.6 s -> at least 30.5 s (floor, +0.9 s)
    Both the baseline and the projected replay re-derive dispatch order from the graph and the builder budget by Part 18's LPT rule rather than keeping bst's own observed order, so that rule's own distance from real dispatch cancels to first order between the two figures.
    duration_floor_us is a floor, not a prediction: an element capped in isolation is assumed no slower than observed and unable to finish its measured CPU work faster than that work spread over the recommended job count at full speed, so the priced cost errs optimistic - the real build under these caps is this long or longer. The benefit of less overcommit for its neighbours is not modelled.
```

Page budgets unmoved: `test_the_page_has_a_volume_budget.py`,
`test_the_chain_folds_and_clicks_are_counted.py`,
`test_the_report_you_can_attach.py` — 76 passed, 2 skipped (none of
the committed fixtures carry Plane 2 priced advice).

**Mutation table** (`TestThePriceSTwoAssumptionsRenderWithAPricedRow`,
`tests/unit/test_the_max_jobs_price_moves_with_the_recommendation.py`).

| mutation | reddened | count |
|---|---|---|
| drop the render (revert the `if any(...priced)` block) | `test_a_priced_row_carries_both_sentences_verbatim` | 1 of 3 |

Reverted from a pristine copy of `bga/findings.py`; 11 of 11 in the
file passed after the revert.

**Deviation.** None — the Required Fix named
`_capacity_recommendation_finding`; the render sits in
`_max_jobs_advice_detail`, the helper that function already calls for
every other `max_jobs_advice` line, so the joint line and the two
sentences are built by the same function. `tools/dev_sizes.py --check`
reports `bga/findings.py` grew 2428 -> 2434 lines (not adopted, per
instruction).
