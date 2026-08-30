# UX-442: one slow sample reddens CI, and nothing asks it to repeat

**Priority:** High | **Status:** 🔴 Not Started | **Found by:** round 69, the third `test (3.11)` red on a branch whose diff could not cause any of them | **Serves:** every contributor whose PR the drift gate stops for a number that will not reproduce | **Topic:** guards

## Motivation

`test (3.11)` went red on `279900f`, a commit whose diff is one backlog
file and one index row. The suite passed:

```text
=========== 5217 passed, 140 skipped, 1 warning in 280.20s (0:04:40) ===========
```

What failed was the drift step:

```text
371 file(s) measured against ci_reference.json (…), this run x1.16 from 114 file(s) over 1s, IQR 0.37
1 file(s) slower than CI's own record of them:
  tests/unit/test_the_page_has_a_reader.py  13.9s  against 7.1s recorded, x1.67 after this run's x1.16 shift
```

**The same file across four CI runs of this branch**, read from the
`--record -` documents those runs printed:

```text
run   reader file   run's shift   run's spread max
 1        7.13            —              —
 2        7.13            —              —
 3        7.53          1.227          5.87
 4       13.85          1.18           4.872
```

Three samples at 7.1-7.5 and one at 13.9. **The outlier run was not a
contended run**: its shift was x1.18 and its spread max x4.87, both
unremarkable and both *lower* than run 3, which passed. One file
excursed; the machine did not.

Both gates tripped, and only just:

```text
ratio/shift  1.69  against CI_DRIFT_FACTOR 1.5
seconds      5.66  against CI_DRIFT_SECONDS 5.0
```

`UX-418` set two gates so a small file could not trip on a ratio and a
big one could not trip on seconds. `UX-423` then measured the run's
**dispersion**, so a globally slow runner would not be read as drift.
Both were right and neither covers this: **the shift's dispersion is
measured and a single file's excursion is not.** A file that boots a
browser can swing six seconds once in four runs, and one such swing is
a red PR.

The cost is not hypothetical. This branch has now been stopped three
times by `test (3.11)`, every one of them at this step, none of them by
a test, and none of them by anything the diff could reach. That is the
habit `UX-426`'s CI-first loop is trying to build being taxed by the
gate meant to protect it — and a gate that reddens on noise is one
people learn to re-run without reading, which is `UX-427`'s "an alarm
nobody reads" arriving from the other direction.

## Required Fix

- **Require the excursion to repeat, or to be large enough that one
  sample settles it.** Two consecutive runs over the bound, a
  best-of-two, or a second much higher factor for a single-run trip —
  the item picks one and states the arithmetic.
- **Whatever is chosen, say what it costs**: a rule needing two runs
  finds real drift one run later, and that delay is the price being
  paid for not crying wolf. Write it down where the next round reads it.
- **A guard driven by a series, not a run.** The present clauses feed
  `dev_tier_drift` one junit document; this needs a fixture of several,
  with one file excursing once and another excursing twice, asserting
  only the second reddens.
- Consider bounding by the file's own history rather than one record —
  `7.13, 7.13, 7.53` is a tight distribution and `13.9` is far outside
  it, which is a stronger statement than a ratio against a single
  number.

## Out of Scope

- **Re-recording the reference to make this green**: the file is not
  slower — three of four samples say 7.1-7.5 — and recording 13.9 would
  bake a contended sample into the document `UX-427` exists to keep
  true.
- **Making `test_the_page_has_a_reader.py` faster**: it boots a browser
  because that is what it measures, and its normal cost is already in
  the reference.
- **Both gates' constants**: `UX-418` measured them and this item adds
  a repetition rule rather than retuning either.
- **The log readability that made this hard to diagnose** — `UX-441`.

## Acceptance Test

Feed `tools/dev_tier_drift.py` a series in which one file exceeds the
bound in a single run and another exceeds it in two consecutive runs:
only the second is reported. A mutation removing the repetition rule
must redden the guard.

## Outcome

_Not started._
