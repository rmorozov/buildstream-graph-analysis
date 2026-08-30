# UX-422: the layout-cost guard measures the runner as well as the page

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** round 66, a red `test (3.12)` on PR #183 | **Serves:** every contributor, at the point CI tells them something is wrong | **Topic:** guards

## Motivation

`test_the_browser_is_the_library.py::test_the_layout_cost_stops_tracking_the_document`
holds a real property: `content-visibility` means a reflow costs
something bounded by what is on screen rather than by the whole
document. It holds it as a **ratio**, deliberately — its own comment
says *"the number is the machine's, the property is the page's"*:

```python
assert seen["on"] < seen["off"] / 2
```

A ratio is the right instinct and this shape of it does not survive a
loaded runner. It went red on CI at 15.4 ms with `content-visibility`
against 28.6 ms without — a 1.86x saving where 2x is required — on
`macro_micro`, a fixture that had not changed. Measured on a developer
container, six runs, three idle and three under eight CPU spinners:

```text
                on      off    ratio
idle           3.0     19.6     6.53
               2.9     17.9     6.17
               2.8     18.0     6.43
loaded         2.9     18.4     6.34
               2.8     16.8     6.00
               3.0     17.8     5.93
CI, 3.12      15.4     28.6     1.86
```

**The two numbers moved by different factors**, which is the whole
finding: `on` is 5x its local value and `off` only 1.6x. That is the
signature of a *fixed additive overhead* on each measurement — a
scheduler delay between `performance.now()` and the forced reflow —
rather than of a slower machine, which would scale both. Subtract
about 12.5 ms from each of CI's figures and you get 2.9 and 16.1: the
local numbers exactly.

A ratio is invariant under a multiplicative change and not under an
additive one, and the smaller operand is the one an additive term
swamps. So the guard, whose job is to prove that `on` is small, fails
precisely when the harness makes small things unmeasurable.

Three of four interpreters passed this test on the same commit, and it
passes six times out of six locally. Nothing about the page changed.

## Required Fix

Make the measurement measure the page:

- **Subtract a floor.** The probe already forces a reflow 25 times and
  takes the median; a third measurement of a reflow that does no layout
  work at all gives the harness overhead, and both operands minus that
  floor is a ratio of layout costs. This is the smallest change and the
  one the numbers above argue for.
- **Or assert the saving, not the ratio** — `off - on` against a floor
  scaled by node count. An additive term cancels in a difference.
  Weaker as a claim, and it re-introduces a machine-dependent number,
  which is what the ratio was avoiding.
- **Or refuse to judge when the floor is high**, skipping with a reason
  that names the measured overhead. Honest, and it means the property
  goes unchecked on exactly the runs where a regression would be
  cheapest to catch.

Whichever is chosen, the test should fail on a page that genuinely lost
`content-visibility` *while the overhead is high* — that is the case
worth building, and the numbers above are the ones to replay.

## Out of Scope

- Relaxing the 2x threshold. The local ratio is 5.9-6.5x, so a page
  that lost the property would still be well under any threshold worth
  having; moving it to 1.5x would be quarantining the guard rather than
  fixing it, and would not survive the next slower runner either.
- The other browser guards in the file. They assert structure, not
  time, and are not exposed to this.

## Acceptance Test

- The clause passes with 12.5 ms of synthetic overhead added to every
  reflow measurement, on the real fixture.
- With `content-visibility` removed from the stylesheet it fails, both
  with that overhead and without it.
