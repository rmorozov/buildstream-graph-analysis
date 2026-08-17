# UX-59: the regression gate compares exactly two runs against a fixed 1% threshold, so the pre-commit scenario has no way to tell a real regression from run-to-run noise

**Priority:** High | **Status:** 🔴 Open | **Depends on:** `UX-55` (done — which made the two CI scenarios explicit)

## Motivation

`bga` serves two CI scenarios, now distinguished by `run_mode` (`UX-55`):

- a **nightly with caches off**, where every element builds. Durations
  are large, dominated by real work, and comparatively stable.
- a **pre-commit run with caches on**, where a handful of elements
  rebuild. Durations are small, dominated by whatever the cache happened
  to hold, and *inherently* noisy — the same commit built twice can
  differ by whichever elements a concurrent job evicted.

The gate treats both identically. `bga/compare.py` takes exactly two
runs and classifies with one constant:

```python
_SIGNIFICANCE_PCT = 1
significant = abs(delta_total_us) * 100 >= baseline_total * _SIGNIFICANCE_PCT
```

One percent of a 46-minute nightly is 28 seconds — a sensible band. One
percent of a two-minute pre-commit run is 1.2 seconds, which is less than
the variance of a single element's compile. In the scenario that runs
most often, the gate is at its most trigger-happy and its signal is at
its weakest.

There is no multi-run statistic anywhere in `bga`. The only standard
deviation in the codebase (`bga/diagnostics/analyzer.py`) is computed
*within* one run, across element durations. `--history-dir` exists but
feeds Part 15's cold structural floor, not regression comparison.

## Deferred twice, never filed

`UX-39`, which built the efficiency gate, said so in as many words:

> Multi-run baselining / trend tracking (N historical runs, statistical
> process control). A real and probably necessary follow-up for noise,
> but a much larger design, and this task should not silently become
> that.

Correct at the time. It was never filed, so "probably necessary" has sat
in an Out of Scope section for two rounds while the gate it qualifies
went on being the product's headline CI feature.

## Required Fix

Not "add statistics" — the design question is what a *baseline* means
when the candidate is incremental:

1. **A baseline is a set, not a run.** N previous runs of the same
   `run_mode` on the same targets, from which a band is derived.
2. **Choose the band deliberately.** A robust one (median ± k·MAD) beats
   mean ± k·σ on build timings, which are right-skewed by
   contention — but this should be measured on real repeated captures,
   not asserted. The capture workflow can now produce them on demand.
3. **Compare like with like.** `UX-55` already refuses to compare across
   modes; this extends it to "compare against the band for *this* mode".
4. **Say what the band was.** A gate that fires must state the band it
   fired against, or it cannot be argued with.

## Out of Scope

- Storing history. Where the N runs live is a deployment question; this
  task should accept them as inputs, the way `--history-dir` already does.
- Changing what counts as a regression *semantically* (`UX-39` settled
  that: added work is fine, added inefficiency is not).

## Acceptance Test

1. Given N runs of one mode plus a candidate, the gate reports the band
   it evaluated against, not just a verdict.
2. A candidate inside the band does not fire, at a delta that the fixed
   1% rule would have fired on.
3. Repeated captures of the *same* commit, taken with the capture
   workflow, do not fire.
4. Comparing against a band built from the other `run_mode` is refused,
   consistent with `UX-55`.

## Verification Log

Filed 2026-08-17. `_SIGNIFICANCE_PCT` and the two-run signature were read
from `bga/compare.py`; the absence of any cross-run statistic was checked
by grepping `bga/` for variance/percentile/control-limit vocabulary — the
only hit computes a standard deviation across elements within a single
run. The 46-minute and 2-minute figures are the real `freedesktop-sdk`
capture and a typical incremental rebuild of the same subgraph.
