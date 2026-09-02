# UX-495: three browser guards swing 1.5-2.3x under parallel load, and nothing says whether that is the file or the runner

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-494` stopped it failing the build; `UX-458` is the sizing question | **Found by:** round 73, three sightings in one session | **Serves:** the round that reads a browser guard's drift reading and cannot tell an excursion from a regression | **Topic:** guards

## Motivation

Three sightings in one session, all in the Chrome-driven guards:

1. `test_the_served_page_really_unhides_a_fallback[1440-900]` in
   `test_the_handoff_box_is_measured_served.py` failed once under
   `make test` at `-n auto` and then passed 3/3 in isolation.
2. On CI run `33552128782`, three browser files read 1.5-2.3x their
   reference while two equally heavy ones did not move:

   ```text
   file                                       08490f5  3dd6e03  5705840   spread
   test_emphasis_is_a_budget.py                 15.66    15.52    36.34   x2.34
   test_a_sentence_lives_on_its_door.py         23.63    23.91    39.75   x1.68
   test_a_control_acts_on_what_it_names.py      36.32    36.99    55.77   x1.54
   test_the_page_has_geometry.py                68.57    68.87    68.29   x1.01
   test_the_two_capabilities_are_offered.py     31.38    31.32    31.97   x1.02
   ```

3. Nothing in that run's branch diff can reach the three that moved.

**A fourth run says the excursion did not repeat.** Run `33554592057`
(`3ab9e76`), the first green one after `UX-494`:

```text
test_emphasis_is_a_budget.py               15.22   (was 15.66, 15.52, 36.34)
test_the_page_has_geometry.py              67.47   (was 68.57, 68.85, 68.29)
test_the_two_capabilities_are_offered.py   30.41   (was 31.38, 31.32, 31.97)
```

So `test_emphasis_is_a_budget.py` came back to its own level, and the
2.34x reading stands as a single excursion — which is exactly what
`UX-476`'s two-run rule assumes and what `UX-494` restored the gate's
ability to say. The other two files that moved could not be read from
this run: the log tail the API returns starts partway through the
candidate document and does not reach the `test_a_*` entries, which is
`UX-491` obstructing the same measurement a second time.

That does not close this row. One file returning to level is evidence
about that file on that run, not about the family's spread, and the
row still wants the population measured rather than sampled.

The last two rows are what make this worth a row rather than a shrug:
the runner was **not** uniformly slow, so "CI was busy" does not
explain it, and the two stable files are the same weight and the same
mechanism. Something distinguishes the three that move from the two
that do not, and no instrument here can say what.

`UX-494` stopped this failing the build. It did not answer the
question, and `CI_DRIFT_FACTOR` cannot be sized (`UX-458`) while a
whole family of files has an unmeasured spread this wide.

## Required Fix

- Measure the spread of the browser family across runs, on CI, at the
  same `-n auto` the gate reads — enough runs to say whether 2.3x is
  the tail or the middle.
- Say what separates the files that swing from the files that do not.
  The obvious candidate is many short browser round-trips against one
  long render, and it is a guess until measured.
- Whatever it finds, `tests/tiers.py` and `CI_DRIFT_FACTOR` are the two
  readers: a family whose real spread exceeds the drift factor makes
  the gate an alarm nobody reads, which is `UX-418`'s own argument.

## Out of Scope

- Making the guards faster, or reducing what they assert. This row
  measures; what it finds gets filed.
- `CI_DRIFT_FACTOR`'s value, which is `UX-458` and needs this answer
  first.
- The single local flake in sighting 1, which is one observation and is
  recorded here only because it is the same family — `UX-489` is the
  precedent for a marginless assertion filed on its own evidence, and
  this row does not fold into it.

## Acceptance Test

The per-run readings for the browser family across at least five CI
runs, pasted, with the spread stated and the two populations — the
files that swing and the files that do not — named.

## Outcome

**Round 75, 2026-09-02.** Six CI runs on PR #193, read from each run's
`tier-reference` job — whose whole log is the candidate document
(`UX-457`). All nine files recorded in all six; nothing interpolated.

**Acceptance Test — raw seconds, six runs:**

```text
run           shift  emphasis  sentence  control  geometry  two_caps  vocab
33576331828   0.998    15.31     23.38    35.46     67.85     33.05   28.57
33577533944   0.891    37.28     41.32    56.73     66.91     31.87   28.79
33578729472   0.666    19.26     24.70    37.84     65.21     32.11   28.35
33579959420   1.002    24.98     28.18    45.24     67.35     31.78   29.14
33580330030   1.018    15.22     23.33    35.55     68.04     32.70   30.01
33581936314   0.994    19.67     23.38    39.45     68.03     33.78   29.05
spread                 x2.45     x1.77    x1.60     x1.04     x1.06   x1.06
```

**The two populations, named.** Swinging: `test_emphasis_is_a_budget`
(x2.45), `test_a_sentence_lives_on_its_door` (x1.77),
`test_a_control_acts_on_what_it_names` (x1.60). Stable:
`test_the_page_has_geometry` (x1.04), `test_the_two_capabilities_are_offered`
(x1.06), `test_the_vocabulary_has_the_shape` (x1.06). Three more read
for control: `test_the_mapping_is_law` x3.69,
`test_why_bga_believes_what_it_believes` x2.10,
`test_a_guard_reads_only_what_a_clone_has` x1.47.

**What separates them is not a property of the file.** The Required
Fix's candidate — many short browser round-trips against one long
render — is **falsified**: seconds per collected item is 1.02 for the
worst swinger and 1.44 for the most stable file, and `geometry` has the
most browser measurements (17 `.measure()` sites, 47 items) of any of
them. Item count, `.measure()` sites, module-scoped `Browser`, and
served-page against exported-file all fail to split the two sets:
`control` (swings) and `two_caps` (does not) are the same shape.

**What does separate them is that they move together.** Pearson
correlation of the six readings, each file against its own quietest run:

```text
              emphasis  sentence   control  geometry  two_caps     vocab
  emphasis        1.00      0.97      1.00     -0.23     -0.58     -0.21
  sentence        0.97      1.00      0.97     -0.21     -0.60     -0.18
   control        1.00      0.97      1.00     -0.16     -0.57     -0.16
```

0.97–1.00 inside the group, −0.16 to −0.60 across it. And on
`33577533944` — the run whose **median file was 11 % faster** — they
read 2.45x, 1.77x, 1.60x while the other three sat at 1.03, 1.00, 1.02.
So "CI was busy" is refuted a second time, with six runs instead of
three: a per-run event reaches one group of files and not their equals.

**For the two readers.**

- `tests/tiers.py`: no tier moves. Every file here is already at its
  right tier by its quiet level, and the excursions do not cross a
  floor — except `emphasis`, whose quiet 15.2s sits **on**
  `LARGE_FLOOR_S = 15.0`, so its tier is decided by which run measured
  it. That is a `UX-496` problem, not a tier problem.
- `CI_DRIFT_FACTOR = 1.5`: this group crossed it on **2 of 6 runs**
  (`33577533944`, `33579959420`) with nothing in either diff that names
  them, and **never on two consecutive runs** — 1.01, 2.45, 1.27, 1.64,
  1.00, 1.29 for `emphasis`. `CI_DRIFT_RUNS = 2` was the whole of the
  protection, and it held by one run. A factor sized to sit above this
  group would have to be x2.5, which would make the gate blind to a
  real 2x regression anywhere else.

**The conclusion this row was filed to reach:** the suite-wide shift
cannot see this, because the runs where the group is highest are runs
where the median file is *faster*. The gate needs a per-file history,
which is `UX-496`.

**Deviation from the Required Fix:** none. The candidate mechanism was
measured and rejected rather than adopted; the row asked for that.
