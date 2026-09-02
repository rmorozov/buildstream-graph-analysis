# UX-59: the regression gate compares exactly two runs against a fixed 1% threshold, so the pre-commit scenario has no way to tell a real regression from run-to-run noise

**Priority:** High | **Status:** 🟢 Done | **Depends on:** `UX-55` (done — which made the two CI scenarios explicit) | **Topic:** analysis

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
2. **Choose the band deliberately.** Measured on real repeated captures
   rather than asserted — see the correction below, where the reason
   given when this task was filed turned out not to be the real one.
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

## Fix Implemented

`compute_band(durations_us, k)` in `bga/compare.py` returns
median ± k·(1.4826·MAD) over a baseline **set**, supplied as repeatable
`--baseline-run PATH` on `bga compare` with `--band-k` (default 3). Below
`MIN_BASELINE_RUNS = 3` there is no band and the fixed rule applies
unchanged, so every existing comparison behaves exactly as before.

Two guards fall out of earlier tasks rather than being invented here:

- A baseline run whose `run_mode` differs from the candidate's is
  **refused**, not averaged in (`UX-55`). A band mixing a nightly with
  pre-commit runs is that mistake with extra arithmetic.
- A degenerate band - every baseline run identical, so MAD is 0 - is
  widened to the fixed percentage rather than collapsing to a point and
  making every subsequent delta significant.

And the gate now states the band it judged against, since one that fires
without saying what it fired against cannot be argued with.

### The measurement, and a correction to this task as filed

Seven real repeated builds of one unchanged `examples/06` commit. **The
first attempt at this measurement was wrong**, and `UX-55`'s own guard
caught it: run 1 built 11 elements while runs 2–7 built 10 and skipped 1,
because `toolchain.bst` was uncached the first time. Mixing a `full` run
into an `incremental` population inflates the spread, so the figures
below are the six same-shape runs only.

```text
26.30  26.91  27.06  27.28  27.51  27.66   (seconds)
mean 27.121   sd 0.488 = 1.8% of mean
median 27.171 scaled MAD 0.448
```

- The fixed 1% rule puts **3 of 6 identical runs outside the band**.
- `bga compare` on the fastest against the slowest — same commit,
  nothing changed — reports `REGRESSED (+5.2%)`. With a band from the
  other four runs it reports `NO SIGNIFICANT CHANGE`, and still reports
  `REGRESSED` for a real +15%.

**This task as filed asserted that build timings are "right-skewed by
contention" and used that to justify the median and MAD. The measurement
does not support it** — at this n the distribution is very nearly
symmetric ((mean−median)/sd = −0.15) and a mean±3σ band contains all six
runs just as a median±3·MAD band does. The real argument is robustness to
a *single* contaminated baseline run, which is what CI actually produces
when one runner gets a noisy neighbour:

| baseline set | mean ± 3σ | median ± 3·MAD |
|---|---|---|
| the six real runs | width 3.00s | width 3.29s |
| one replaced by a 45s outlier | width **40.64s** | width **3.29s** |
| …does it still catch a real +15%? | **no** | **yes** |

Tests: 14 new (`tests/unit/test_baseline_noise_band.py`), including the
real six-run set, the outlier contrast, the degenerate zero-MAD case, and
the contrast verdict the fixed rule produces on the same input.

Suite: 977 → 991.

## Measured on real data (round 9)

Two real `freedesktop-sdk` captures of the **same commit** now exist, and
the gate was run against them:

```text
$ bga compare round8/run round9/run
Verdict: REGRESSED  (total duration +101.22s, +2.9%, 3513.01s -> 3614.22s)
```

Same commit, same `run_mode`, nothing changed, both at confidence ~1.00
so `UX-40`'s fail-open does not save it. **Real run-to-run noise on this
build is 2.9% against a fixed 1% rule** — worse than the 1.8% this task
measured locally, as expected for a longer build on shared runners.

The band built here is not reached, because `MIN_BASELINE_RUNS` is 3 and
only two real captures exist. That floor is right — a "band" over two
points restates them — which means the **default** path is the one that
is wrong on real data, and the default is what a first user gets. A third
capture of the same commit would settle whether the band absorbs this.

## Verification Log

Filed and implemented 2026-08-17. `_SIGNIFICANCE_PCT` and the two-run signature were read
from `bga/compare.py`; the absence of any cross-run statistic was checked
by grepping `bga/` for variance/percentile/control-limit vocabulary — the
only hit computes a standard deviation across elements within a single
run. The 46-minute and 2-minute figures are the real `freedesktop-sdk`
capture and a typical incremental rebuild of the same subgraph.
