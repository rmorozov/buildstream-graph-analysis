# UX-495: three browser guards swing 1.5-2.3x under parallel load, and nothing says whether that is the file or the runner

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-494` stopped it failing the build; `UX-458` is the sizing question | **Found by:** round 73, three sightings in one session | **Serves:** the round that reads a browser guard's drift reading and cannot tell an excursion from a regression | **Topic:** guards

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

_Not started._
