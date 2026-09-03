# UX-611: what-if's saving is still in build seconds

**Priority:** Low | **Status:** 🔴 Open | **Depends on:** UX-596 (which built the converter) | **Serves:** the team deciding whether a fix is worth a day | **Topic:** report

## Motivation

`UX-596` converted the headline and the plan into the team's units.
`bga whatif`'s projected saving was outside its declared surface and
still reads:

```text
the top 3 are worth 23.1s
```

One renderer, `bga/whatif.py`, left in the unit the tool measures
rather than the one a reader decides in — which is the whole of
`UX-234`'s cost-translation argument, applied everywhere but here.

## Required Fix

`bga/whatif.py` uses `bga/report/rate.py`, the same converter, so
there is one rule and not two.

## Out of Scope

- The rate's arrival via `BGA_RATE` rather than a flag — `UX-596`
  measured the `--help` budget that decides it, and this item does not
  reopen it.

## Acceptance Test

`bga whatif` under a set rate, showing the converted figure; and the
converter removed from it — red.

## Outcome

Base `d4a3d04`; not closed here — the row move and `make test` are
the batch's. Guard: `test_whatifs_saving_is_in_the_teams_units.py`.

### The gap, re-measured

`tests/fixtures/macro_micro/run`, three elements. With a rate set and
with none, the output was byte-identical:

```text
$ BGA_RATE="90 USD/machine-hour" bga whatif RUN --element core.bst ...
What if these were fixed: core.bst, lib-b.bst, lib-d.bst
  Makespan 43.200s -> 23.150s (saves 20.050s)
```

`bga analyze` under the same rate already converted it:
`the top 3 together  23.05s = 0.58 USD at 90 USD/machine-hour`.
**Half-false in one detail**: the Motivation's quoted
`the top 3 are worth 23.1s` is the `analyze` headline
(`findings.py:1172`), not anything `whatif` prints. The premise holds
on the figure, not on that string.

### The close, measured

```text
  Makespan 43.200s -> 23.150s (saves 20.050s)
  In your units: saves 20.050s = 0.50 USD at 90 USD/machine-hour
    rate: 90 USD/machine-hour - an input you supplied (BGA_RATE), ...
```

`1.5 engineer-hours/build-hour` gives `0.00502 engineer-hours at ...`;
`BGA_RATE=cheap` gives `In your units: not applied: ...`; a refusal and
the `--format json` document are untouched. With no rate, unchanged.

### Mutation table

`tests/unit/test_whatifs_saving_is_in_the_teams_units.py`, 14 clauses,
`0.23s` single-process (small tier). Each mutation applied to
`bga/whatif.py`, run, reverted, anchor grepped back; `14 passed` before
and after.

| # | mutation | reddened | run |
|---|---|---|---|
| M1 | default rate when none supplied | `..._nothing_is_added_and_nothing_is_invented` | 1 failed, 13 desel |
| M2 | seconds dropped from makespan line | `..._still_published_in_seconds` | 1 failed |
| M3 | **acceptance**: converter removed | `..._reaches_the_reader_s_unit`, `test_bga_whatif_under_a_set_rate` | 2 failed |
| M4 | figure printed without its rate | `..._travels_without_its_rate` | 1 failed |
| M5 | conversion replaces the seconds | `..._seconds_stay_beside_the_conversion` | 1 failed |
| M6 | preamble line dropped | `..._named_as_the_reader_s_input` | 1 failed |
| M7 | only `machine-hour` converts | `..._other_denominator_converts_too` | 1 failed |
| M8 | own multiplication inlined | `..._from_report_rate_and_not_a_copy`, `..._no_second_conversion` | 2 failed |
| M9 | same converter, own rounding | `..._rounding_and_vocabulary_are_the_converter_s` | 1 failed |
| M10 | malformed rate swallowed | `..._says_why_instead_of_falling_silent` | 1 failed |
| M11 | rate printed beside a refusal | `..._refused_selection_prices_nothing` | 1 failed |
| M12 | rate written into the document | `..._never_reaches_the_whatif_document` | 1 failed |

M8 is load-bearing: it swaps `report.rate.phrase` for a sentinel and
requires it in the output, catching arithmetic of `whatif`'s own.

### A clause that did not discriminate first time

`test_no_converted_figure_travels_without_its_rate` scanned every line
containing `USD` and failed on the preamble, which carries the rate but
no figure. Widening it would be `UX-596`'s heading-satisfies bug, so it
excludes the preamble by identity against `rate.preamble()`.

### Deviation from the Required Fix

None. `bga/whatif.py` calls `bga/report/rate.py` — `supplied`, `phrase`,
`preamble` — adds no conversion of its own (guarded), and no flag.
Rounding and vocabulary are asserted equal to `rate.phrase`'s rather
than restated. `sum_of_individual_us` stays in seconds: it is the
deliberately-wrong comparison figure, not a priced fix, and
`_priced_fixes` does not convert its analogue either.

Committed with `BGA_SKIP_SELECTOR=1`: `test_every_direction_names_its_reader.py`
is red at base `d4a3d04` (Directions 8/9 say `partial` over ids round 84
closed). Proven with this diff stashed; `docs/design/directions.md` is
not this track's surface. Otherwise `1 failed, 432 passed, 3 skipped`.
