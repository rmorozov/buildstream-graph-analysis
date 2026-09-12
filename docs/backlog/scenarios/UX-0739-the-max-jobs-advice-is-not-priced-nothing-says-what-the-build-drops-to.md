# UX-739: the max-jobs advice is not priced — nothing says what the build drops to

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-677 (which produces the recommendation this would price), UX-219 (what-if, the projection that exists), UX-116 | **Serves:** R4 and R5, deciding whether the recommendation is worth applying | **Topic:** analysis | **Shape:** judgement | **Area:** bga

## Motivation

`UX-677`'s Required Fix asked for a per-element `max-jobs`
recommendation **priced by replay** — "the `whatif` scheduler with
per-element job counts, so the advice says what the build drops to".
Round 102's track read `bga/whatif.py` and found the capability does
not exist:

```text
whatif.project() computes projections where selected elements become
*instant*, over this run's measured durations. That is the only mode
it has.
```

Making an element instant and re-simulating dispatch under changed
concurrency are different computations. The second needs a scheduler
that re-derives dispatch order under a new job budget, which nothing
here does. `UX-677` was split rather than widened: it now delivers
the recommendation and the constraint it satisfies, and this row
takes the price.

Unpriced advice is the weaker half. A recommendation that says
"cap `app.bst` at 4" without saying "and the build goes from 46 s to
51 s" leaves the reader to guess whether the trade is worth it —
which is the judgement the advice exists to inform.

## Required Fix

A replay that answers *what does the build become under these
per-element job counts*, and the advice states the answer beside each
recommendation.

The judgement this row owes, and it should be taken before any track
runs it: **what a replay is allowed to assume.** Dispatch order under
a changed job budget is not the order this run had, and a replay that
keeps the observed order is not a projection, it is arithmetic wearing
a scheduler's name. Either re-derive the order from the graph and the
budget — and say what the model assumes about queueing — or state
plainly that the figure is a bound rather than a prediction, and which
direction it errs in. `UX-170`'s disputed-region reasoning is the
precedent for publishing a figure with its own uncertainty rather than
a false point estimate.

## Out of Scope

- The recommendation itself. `UX-677` produces it; this row prices it.
- Writing numbers into the project. `UX-677`'s Out of Scope holds
  here too — the advice is a table and paste-able `bst` lines.

## Acceptance Test

A priced recommendation on a real two-plane capture: each recommended
`max-jobs` carries what the build becomes under it, and the figure
states whether it is a prediction or a bound. Mutation: change a
recommendation and the price must move with it — a price that does
not track its recommendation is not reading it.

## Outcome

**Gap measured.** `compute_max_jobs_advice`'s rows carried a
recommendation and no price - `UX-677`'s own Deviation named this
row as the missing half.

**Close measured.** `price_max_jobs_advice(advice, tasks, run_context,
binary_cost)` (`bga/correlate.py`) replays `ReplayScheduler(tasks,
run_context).replay(compute_default_capacities(run_context))` once for
a baseline, then once per lowered recommendation with its BUILD task's
duration overridden to `max(observed, ceil(measured_cpu_us /
recommended))` - Plane 2's `binary_cost[element]`. A raise is refused
outright; an unchanged recommendation costs 0; missing `binary_cost`
is a named refusal; an existing `UX-677` refusal stays untouched.
`priced_jointly` recomputes one replay with every priced, lowered
element's floor applied together. Called from `_finish_capacity_
recommendation` (`bga/cli.py`), where `analyzer.normalized_tasks`/
`.run_context` are already in hand. Rendered from `bga/findings.py`'s
`_capacity_recommendation_finding` - the only place `max_jobs_advice`
was already surfacing as text (`grep -rn max_jobs_advice bga/viewer`
finds nothing; the viewer draws none of this block today and is
untouched, as the judgement allows).

Round-112 capture, real: `codegen.bst` - `binary_cost.measured_cpu_us`
9,434,151 us, BUILD duration 6.0 s, floor 9.43 s (the CPU term wins),
baseline 29.6 s, projected 29.6 s, `cost_us` 0 - slack absorbs it, the
graph's real bottleneck is elsewhere. `lib-f.bst` (4->1) costs 0.9s
alone. Joint line: `Together (codegen.bst, lib-a..f.bst): build 29.6 s
-> at least 30.5 s (floor, +0.9 s)` - not the sum of the six individual
costs (five of which are 0). Both assumption sentences render as
stated in the Required Fix.

**Mutation table** (`tests/unit/test_the_max_jobs_price_moves_with_
the_recommendation.py`, synthetic tasks, no fixture).

| mutation | reddened | count |
|---|---|---|
| floor ignores CPU (`max(dur, 0)`) | mutation-test + joint-not-a-sum test | 2 of 7 |
| raise branch prices anyway (drops the `>` refusal) | raise-is-a-refusal test | 1 of 7 |
| joint sums the per-row costs | joint-not-a-sum test | 1 of 7 |

All reverted from a pristine copy of `bga/correlate.py`; 7 passed after
each revert.

**Deviation.** The Required Fix named "the text renderer in bga/cli.py
for `max_jobs_advice`"; none exists there or anywhere - the block was
JSON-only. Extended `bga/findings.py`'s `_capacity_recommendation_
finding` instead, the one place this document already narrates as
text. `docs/guides/cli.md`'s guarded key surface moved 261 -> 263
keys (`priced`/`price_refusal`; `priced_jointly`/`pricing_assumptions`
are internal shape, like `caveat`, and are documented but not counted).
`tests/unit/test_the_report_you_can_attach.py`'s golden export bound
moved 458,000 -> 462,000 (measured 457,357 -> 458,519, all contract -
golden has no Plane 2 so carries none of the priced data itself).
