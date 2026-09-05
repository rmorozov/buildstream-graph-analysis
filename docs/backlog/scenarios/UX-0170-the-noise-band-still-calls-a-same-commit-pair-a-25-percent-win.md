# UX-170: the noise band still calls a same-commit pair a 25% win

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-59 (the band), UX-96 (the set that feeds it), UX-92 (which measured the spread) | **Topic:** analysis | **Area:** tools

## Motivation

The band exists because a fixed 1% significance rule called two captures
of the *same* commit a 5.8% improvement. At n=3 it worked: the band
absorbed that pair and returned `NO SIGNIFICANT CHANGE`, and the README
says so as the reason to build a baseline set at all.

At n=5 it does not. Five captures of freedesktop-sdk `953683fb`, all by
the same workflow, all with `--builders 4 --max-jobs 4`:

```text
3614.22s  3434.43s  3405.78s  3261.22s  2712.39s
```

Run against the band those same five runs define:

```text
$ bga compare 32064333551/run 32177690506/run \
      --baseline-run ...(all five)... --band-k 3.0
Verdict: IMPROVED  (total duration -901.83s, -25.0%, 3614.22s -> 2712.39s)
  Judged against a noise band from 5 baseline run(s): 2762.79s .. 4048.77s
  - median 3405.78s +/- 3x214.33s (scaled MAD)
```

2712.39s sits **below the lower edge of the band its own run helped
build**. The middle pairs behave — the −5.8% and −9.8% same-commit pairs
both come back `NO SIGNIFICANT CHANGE` — so the mechanism is not broken;
its assumption is. A scaled MAD over five points, three of which cluster
inside 210s, produces a band too narrow for a population whose real
spread is 33% of its own minimum.

The gate is not fooled in the failing direction: `--fail-on-regression`
exits 0 here, because the outlier is *fast*. The damage is to reporting
and to trust — a same-commit pair announced as a 25% win is exactly the
claim this tool exists not to make, and it will be read as one.

## What the number probably is

Not the project. GitHub's shared runners vary; UX-92's re-check found
the same 33.2% spread with a 10.5% coefficient of variation, and the
one metric that could explain a real difference — cache hit ratio — is
72% on all five runs with zero churn. Whatever moved is under the
runner, not in the build.

## Required Fix

Decide, on the data, between:

- **A wider or differently-shaped band.** MAD is chosen for outlier
  resistance, which here means it *excludes* the outlier rather than
  covering it. Percentile bounds (min..max, or 10th..90th) over a
  larger set would cover it; the cost is that a real regression inside
  the observed range stops being called.
- **A minimum band width.** A floor expressed as a fraction of the
  median, derived from the measured coefficient of variation rather
  than picked — the same discipline `UX-39` used for its default.
- **Refuse instead of verdicting.** When the baseline set's own spread
  exceeds some multiple of the delta being judged, "this environment is
  too noisy to answer" is a true statement and a more useful one than
  a verdict. `UX-78`/exit 6 already establishes refusal as a first-class
  outcome.

Whichever it is, the README's claim that the band turns a same-commit
pair into `NO SIGNIFICANT CHANGE` has to become whatever is true after
the fix. Corrected in the meantime to say what actually happens.

## Out of Scope

- The runner's variance itself (not ours to fix, and worth measuring
  before assuming it is the cause).
- `--fail-on-regression`'s behaviour, which is correct here.

## Acceptance Test

The five preserved fdsdk refs, band-compared pairwise: no same-commit
pair returns a duration verdict other than `NO SIGNIFICANT CHANGE` or an
explicit refusal. Mutation: shrinking the band back to its current shape
reddens the outlier pair. Whatever threshold or width is introduced is
derived from those runs' own measured spread and says so in the code.

## What was built

The band still uses the median and a scaled MAD - `UX-59`'s robustness
argument is unchanged, and widening the band to cover the observed
range was tried and **rejected**: it makes one contaminated baseline run
swallow a real regression (the existing test measures that at
2.67s → 19.16s of band width, at which point a +15% regression is no
longer caught). Robustness cannot distinguish a contaminated run from a
genuinely noisy environment, so the fix is not a wider band.

What the band now reports is whether it describes the set it came
from - `describes_its_own_set`, `runs_outside_band`, and the set's
observed edges - and the verdict layer withholds a duration answer in
the one region where the band and its own runs disagree:

- candidate **inside the band** → `no significant change`, as before;
- candidate **outside the band but inside the range the baselines
  themselves reached** → `within the baseline set's own observed
  range`, which is not a verdict about the build;
- candidate **outside both** → a real verdict, as before.

No constant is introduced. The disputed region is the gap between the
band and the runs that built it, which the data defines by itself; the
rule it encodes is that a duration the baseline set reached, on the
commit the set is *of*, cannot be evidence that something changed.

### Measured on the five real fdsdk refs

```text
32064333551 vs 32177690506 -> WITHIN THE BASELINE SET'S OWN OBSERVED RANGE  (-901.83s, -25.0%)
32064333551 vs 32122941503 -> NO SIGNIFICANT CHANGE  (-208.44s, -5.8%)
32064333551 vs 32223468993 -> NO SIGNIFICANT CHANGE  (-353.00s, -9.8%)
```

The pair that read `IMPROVED (-25.0%)` refuses; the two the band
already handled keep their answers. That is the acceptance, on the same
five captures that produced the finding.

### A seam left open, deliberately

`--fail-on-regression` has never consulted the band - it applies the
fixed significance percentage directly (`regression_exceeds_threshold`,
and its docstring says so). So a *regression* inside the disputed
region would be refused by the report and failed by the gate. That
divergence predates this item and changing it changes gate behaviour
for every existing pipeline, which is more than this item asked for.
Named here rather than fixed quietly.

### Guards

`tests/unit/test_band_observed_range.py`, seven of them, all on the
real fdsdk numbers. Three mutations, each red: the refusal removed;
the refusal widened to "whenever the set is inconsistent" (which
swallows the answers the band gets right); and the band no longer
reporting whether it fits its own set.
