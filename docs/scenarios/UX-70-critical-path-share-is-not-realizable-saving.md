# UX-70: the report ranks by share of the critical path, but 82% of one element's share is not realizable — a user optimizing it would get 3% back, not 18%

**Priority:** High | **Status:** 🟢 Done | **Depends on:** `UX-65` (which introduced the ranking this corrects)

## Motivation

Raised by the user: *"won't we force user to wait for hours of rebuilds
to find next top problems when graph from the beginning had been of
hundreds of path of almost similar length and critical path was only one
of dozens that stay after it? maybe we need some analysis on graph
density in percentages to critical path?"*

The concern is real and measurable. On the real `freedesktop-sdk`
capture, **97 of 126 elements have zero slack** — 77% of the graph sits
on *a* critical path, and the slack distribution is empty until the 9th
decile.

`UX-65` made the report rank "Elements Most Worth Optimizing First" by
share of the critical path. Testing what those shares are actually worth,
by recomputing the longest path with each element made instant:

| element | share of path | time spent | **realizable saving** | |
|---|---|---|---|---|
| `cmake-stage1.bst` | 43.5% | 1569.7s | **1569.7s** | 100% of its time |
| `doxygen.bst` | 14.2% | 513.6s | **513.6s** | 100% |
| `openssl.bst` | 18.6% | 672.1s | **522.6s** | 78% |
| **`python3.bst`** | **17.7%** | **639.8s** | **114.1s** | **18%** |

**`python3.bst` is ranked third at 17.7% of the critical path, and
eliminating it entirely would save 114 seconds of a 3610-second build —
3.2%.** The other 82% of its duration is masked by a near-tie chain that
takes over the moment it shrinks.

A user who spent a week making `python3.bst` twice as fast would recover
about a minute, having been told it was the third most valuable thing to
work on. That is the failure the user predicted, present in the current
output.

## Why the current number is not wrong, only insufficient

Share of the critical path is a correct description of *this* run's
chain. It answers "what is the chain made of". It does not answer "what
happens if I change it", because it holds the rest of the graph fixed —
and in a graph with 77% zero-slack elements, the rest of the graph does
not stay fixed.

The same reasoning as `UX-27`: a number can be arithmetically right and
answer a question the user is not asking.

## Required Fix

1. **Rank by realizable saving.** For each candidate, recompute the
   longest path with that element's duration zeroed (or halved) and
   report the delta. One longest-path recomputation per candidate — cheap
   at this graph's size, and cheap to bound for larger ones by only
   evaluating the top N by share.
2. **Say when the runner-up is close.** *"Making this instant saves 114s;
   the next chain is 3496s"* is the sentence that stops a wasted week.
3. **Publish graph density.** The share of elements with zero (or near
   zero) slack is a one-line description of whether this project's build
   is a chain or a mesh, and it changes what advice is even meaningful.
   77% here.
4. **Consider batches.** All four top elements made instant saves 2701s,
   far more than the sum of their individual savings (2720s ≈ coincidence
   here, but in a mesh the batch effect is the point). Ranking singletons
   in a dense graph systematically under-promises batches and
   over-promises individuals.

## Out of Scope

- Changing `T∞`, `LB` or any certified floor. Those are correct.
- Predicting the *cost* of making an element faster. The tool can say
  what a saving would be worth, not how hard it is to get.

## Acceptance Test

1. On the real capture, `python3.bst` is not ranked above elements with
   larger realizable savings, or is annotated with its 114s realizable
   figure.
2. The report states the graph's zero-slack share.
3. On a chain-shaped graph (`examples/06`), realizable saving and share
   of path agree, and the ranking is unchanged.
4. The recomputation cost is bounded and stated for large graphs.

## Fix Implemented

`compute_realizable_savings(graph, durations, candidates)` recomputes the
longest path with each candidate's duration zeroed. Zeroing rather than
halving is deliberate: it is the **upper bound** on what optimizing an
element can ever be worth, which is the number that stops a wasted week.

Bounded to `REALIZABLE_SAVING_CANDIDATES = 8` — each costs one
longest-path recomputation — and evaluated only for non-structural
elements with real measured duration.

On the real capture:

```
Elements Most Worth Optimizing First (by what optimizing them would
  actually save - this build is chain-bound, not scheduler-bound):
  1. components/_private/cmake-stage1.bst (1569.8s, 43.5% of the critical path)
       - making it instant would save 1569.8s (43.4% of the build)
  2. components/openssl.bst (672.1s, 18.6% of the critical path)
       - making it instant would save 522.5s (14.5% of the build)
  3. components/doxygen.bst (513.5s, 14.2% of the critical path)
       - making it instant would save 513.5s (14.2% of the build)
  Note: 77% of elements have zero slack - this graph is a mesh of
  near-equal chains, so savings on one element are often capped by the
  next chain rather than by its own duration
```

**`python3.bst` is gone from the top three**, displaced by `doxygen.bst`
— shorter in duration, worth 4.5x more.

`signals.zero_slack_share` publishes the density, stated in the report
above 50% so a reader knows chain from mesh *before* acting on any
ranking. The section heading changed with the ranking, since it said "by
share of the critical path" and would otherwise describe something the
report no longer does.

Tests: 8 (`tests/unit/test_realizable_saving.py`), including the near-tie
case in miniature and the `None`-means-not-evaluated fallback. Golden
regenerated for the additive `realizable_saving_us` key.

## Verification Log

Filed and implemented 2026-08-17. Slack distribution from `analyze.json`'s
`signals.slack` in the capture published as `5eda28a`; realizable savings
computed by recomputing the longest path over that capture's
`graph-declared.json` build edges with measured per-element durations from
its `run/trace.json`, zeroing one element at a time.
